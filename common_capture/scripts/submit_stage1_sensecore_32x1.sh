#!/usr/bin/env bash


set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
manifest_root=${STAGE1_MANIFEST_ROOT:-"$root/manifests/stage1_foundation_v5_formal"}
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v5_output"}
metadata="$manifest_root/MANIFEST_METADATA.json"
audit="$manifest_root/MANIFEST_AUDIT.json"
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
if [[ "$SENSECORE_AEC2_NAME" == public ]]; then
  require_setting SENSECORE_VPC_ID
  require_setting SENSECORE_AZ
fi
if [[ "$dry_run" != 1 ]]; then
  command -v sco >/dev/null || {
    echo "SenseCore CLI not found: sco" >&2
    exit 69
  }
fi
[[ -r "$metadata" && -r "$audit" ]] || {
  echo "formal Stage-1 v5 manifest is not ready: $manifest_root" >&2
  exit 66
}
[[ -x "$root/build/$h200_build_tag/bin/xonotic-local-sdl" &&
   -r "$root/locks/$h200_build_tag.sha256" &&
   -r "$h200_env_archive" &&
   -r "${h200_env_archive}.sha256" ]] || {
  echo "locked H200 build or environment archive is missing" >&2
  exit 66
}
python3 - "$metadata" "$audit" "$manifest_root" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
audit_path = Path(sys.argv[2])
root = Path(sys.argv[3])
metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
audit = json.loads(audit_path.read_text(encoding="utf-8"))
checks = {
    "audit_passed": audit.get("passed") is True,
    "runtime_source_commit": metadata.get("source_commit")
    == "7e8310b0d0c135774f5cfbdb08122eec1f12c99b",
    "runtime_compatibility": (
        metadata.get("path_certification", {})
        .get("runtime_compatibility", {})
        .get("runtime_source_commit")
        == "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
    ),
    "primary_rows": metadata.get("primary", {}).get("rows") == 60_000,
    "semantic_weight_feasibility": (
        metadata.get("semantic_weight_feasibility", {})
        .get("mean_absolute_deviation_maximum")
        == 0.50
    ),
    "shard_count": metadata.get("shard_count") == 32,
    "primary_shards": len(metadata.get("primary", {}).get("shards", []))
    == 32,
    "shard_files": len(list((root / "shards/primary").glob(
        "shard-*-of-032.jsonl"
    ))) == 32,
}
if not all(checks.values()):
    raise SystemExit(f"formal manifest readiness failed: {checks}")
PY

job_name=${SENSECORE_JOB_NAME_OVERRIDE:-"xonotic-stage1-v5-primary-$(date -u +%Y%m%d-%H%M%S)"}
priority=${SENSECORE_JOB_PRIORITY:-NORMAL}
quota_type=${SENSECORE_QUOTA_TYPE:-reserved}
retry_times=${SENSECORE_RETRY_TIMES:-3}
task_command="bash -lc 'cd $root && STAGE1_CANDIDATE_WAVE=primary STAGE1_MANIFEST_ROOT=$manifest_root STAGE1_OUTPUT_ROOT=$output_root STAGE1_EXECUTION_MODE=resident STAGE1_MAX_OPERATIONAL_ATTEMPTS=2 XONOTIC_BUILD_ARCH=x86_64 XONOTIC_BUILD_TAG=$h200_build_tag XONOTIC_ENV_ARCHIVE=$h200_env_archive XONOTIC_PIPELINES_PER_GPU=12 XONOTIC_LIVE_CONCURRENCY=12 XONOTIC_RENDER_CONCURRENCY=12 XONOTIC_RENDER_TIMEOUT_SECONDS=240 XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=120 XONOTIC_SDL_CONCURRENCY=12 XONOTIC_ENCODE_CONCURRENCY=4 XONOTIC_X264_THREADS=16 exec ./scripts/run_stage1_32x1_worker.sh'"

args=(
  acp jobs create
  "--workspace-name=$SENSECORE_WORKSPACE_NAME"
  "--aec2-name=$SENSECORE_AEC2_NAME"
  "--job-name=$job_name"
  "--container-image-url=$SENSECORE_CONTAINER_IMAGE"
  "--training-framework=pytorch"
  "--worker-spec=$SENSECORE_H200_1GPU_WORKER_SPEC"
  "--worker-nodes=32"
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
echo "workers=32"
echo "gpus_per_worker=1"
echo "worker_spec=$SENSECORE_H200_1GPU_WORKER_SPEC"
echo "task_command=$task_command"
if [[ "$dry_run" == 1 ]]; then
  printf 'dry_run_command=sco'
  printf ' %q' "${args[@]}"
  printf '\n'
  exit 0
fi
exec sco "${args[@]}"
