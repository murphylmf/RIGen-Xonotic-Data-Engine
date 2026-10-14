#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
manifest_root=${STAGE1_MANIFEST_ROOT:-"$root/manifests/stage1_foundation_v5_formal_56x1_recovery_r6"}
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v5_output_56x1_menu_clean_r3"}
metadata="$manifest_root/MANIFEST_METADATA.json"
audit="$manifest_root/MANIFEST_AUDIT.json"
recovery_audit="$manifest_root/RECOVERY_AUDIT.json"
h200_build_tag=capture-7e8310b0d0c1-x86_64
h200_env_archive="$root/env/xonotic-capture-linux-x86_64-20260727.tar.gz"

require_setting() {
  local name=$1
  [[ -n ${!name:-} ]] || {
    echo "required setting is empty: $name" >&2
    exit 64
  }
}
require_setting SENSECORE_WORKSPACE_NAME
require_setting SENSECORE_AEC2_NAME
require_setting SENSECORE_CONTAINER_IMAGE
require_setting SENSECORE_H200_1GPU_WORKER_SPEC

dry_run=${SENSECORE_DRY_RUN:-0}
[[ "$dry_run" == 0 || "$dry_run" == 1 ]] || {
  echo "SENSECORE_DRY_RUN must be 0 or 1" >&2
  exit 64
}
if [[ "$dry_run" == 0 ]]; then
  command -v sco >/dev/null || {
    echo "SenseCore CLI not found: sco" >&2
    exit 69
  }
fi
if [[ "$SENSECORE_AEC2_NAME" == public ]]; then
  require_setting SENSECORE_VPC_ID
  require_setting SENSECORE_AZ
fi
[[ -r "$metadata" && -r "$audit" && -r "$recovery_audit" &&
   -r "$h200_env_archive" && -r "${h200_env_archive}.sha256" ]] || {
  echo "sealed r6 recovery artifacts are missing" >&2
  exit 66
}
read -r namespace pending_rows snapshot_sha < <(
  python3 - "$metadata" "$audit" "$recovery_audit" \
    "$output_root" <<'PY'
import json
import sys

metadata = json.load(open(sys.argv[1], encoding="utf-8"))
audit = json.load(open(sys.argv[2], encoding="utf-8"))
recovery_audit = json.load(open(sys.argv[3], encoding="utf-8"))
recovery = metadata.get("recovery") or {}
checks = {
    "manifest_audit": audit.get("passed") is True,
    "recovery_audit": recovery_audit.get("passed") is True,
    "source_stopped": recovery.get("source_job_stopped") is True,
    "snapshot_sealed": recovery.get("terminal_snapshot_sealed") is True,
    "nonterminal_only": recovery.get("only_nonterminal_candidates") is True,
    "namespace_isolated": recovery.get("journal_namespace_isolated") is True,
    "output_root": recovery.get("output_root") == sys.argv[4],
    "attempt_continuity": recovery.get(
        "attempt_numbers_continue_from_snapshot"
    ) is True,
    "server_ready": recovery.get(
        "server_ready_before_client_start"
    ) is True,
    "warmup_concurrency": recovery.get("warmup_concurrency") == 4,
    "steady_lanes": recovery.get("steady_lane_limit") == 12,
    "rank_start_stagger": (
        recovery.get("rank_start_stagger_seconds") == 15
        and recovery.get("rank_start_stagger_slots") == 8
    ),
    "shard_count": metadata.get("shard_count") == 56,
    "shards": len(metadata.get("primary", {}).get("shards", [])) == 56,
}
if not all(checks.values()):
    raise SystemExit(f"recovery readiness failed: {checks}")
print(
    recovery["namespace"],
    recovery["pending_candidates"],
    recovery["terminal_snapshot_sha256"],
)
PY
)

job_name=${SENSECORE_JOB_NAME_OVERRIDE:-"xonotic-stage1-primary-recovery-r6-56x1-$(date -u +%Y%m%d-%H%M%S)"}
priority=${SENSECORE_JOB_PRIORITY:-NORMAL}
quota_type=${SENSECORE_QUOTA_TYPE:-reserved}
retry_times=${SENSECORE_RETRY_TIMES:-3}
task_command="bash -lc 'cd $root && STAGE1_MANIFEST_ROOT=$manifest_root STAGE1_OUTPUT_ROOT=$output_root STAGE1_EXECUTION_MODE=resident STAGE1_MAX_OPERATIONAL_ATTEMPTS=2 STAGE1_RESUME_PASSES=3 STAGE1_DISTRIBUTED_BARRIER=1 STAGE1_DISTRIBUTED_BARRIER_TIMEOUT_SECONDS=14400 STAGE1_DISTRIBUTED_RANK0_EXIT_GRACE_SECONDS=30 STAGE1_DISTRIBUTED_RUN_ID=$job_name XONOTIC_BUILD_ARCH=x86_64 XONOTIC_BUILD_TAG=$h200_build_tag XONOTIC_ENV_ARCHIVE=$h200_env_archive XONOTIC_PIPELINES_PER_GPU=12 XONOTIC_RESIDENT_WARMUP_CONCURRENCY=4 XONOTIC_LIVE_CONCURRENCY=12 XONOTIC_RENDER_CONCURRENCY=12 XONOTIC_RENDER_TIMEOUT_SECONDS=240 XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=120 XONOTIC_SDL_CONCURRENCY=12 XONOTIC_ENCODE_CONCURRENCY=4 XONOTIC_X264_THREADS=16 exec ./scripts/run_stage1_recovery_56x1_worker.sh'"

args=(
  acp jobs create
  "--workspace-name=$SENSECORE_WORKSPACE_NAME"
  "--aec2-name=$SENSECORE_AEC2_NAME"
  "--job-name=$job_name"
  "--container-image-url=$SENSECORE_CONTAINER_IMAGE"
  "--training-framework=pytorch"
  "--worker-spec=$SENSECORE_H200_1GPU_WORKER_SPEC"
  "--worker-nodes=56"
  "--priority=$priority"
  "--command=$task_command"
  "--enable-fault-tolerance"
  "--retry-times=$retry_times"
  "--quota-type=$quota_type"
  "--wait"
)
if [[ -n ${SENSECORE_STORAGE_MOUNT:-} ]]; then
  args+=("--storage-mount=$SENSECORE_STORAGE_MOUNT")
fi
if [[ "$SENSECORE_AEC2_NAME" == public ]]; then
  args+=("--vpc-id=$SENSECORE_VPC_ID" "--az=$SENSECORE_AZ")
fi

echo "submitting_job=$job_name"
echo "workers=56"
echo "gpus_per_worker=1"
echo "recovery_namespace=$namespace"
echo "pending_rows=$pending_rows"
echo "terminal_snapshot_sha256=$snapshot_sha"
echo "task_command=$task_command"
if [[ "$dry_run" == 1 ]]; then
  printf 'dry_run_command=sco'
  printf ' %q' "${args[@]}"
  printf '\n'
  exit 0
fi
exec sco "${args[@]}"
