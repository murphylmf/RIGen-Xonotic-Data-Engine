#!/usr/bin/env bash


set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
manifest_root=${STAGE1_MANIFEST_ROOT:-"$root/manifests/stage1_foundation_v5_formal_56x1_runtime_r5"}
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v5_output_56x1_menu_clean_r3"}
legacy_menu_polluted_output="$root/stage1_foundation_v5_output_56x1"
metadata="$manifest_root/MANIFEST_METADATA.json"
audit="$manifest_root/MANIFEST_AUDIT.json"
topology_audit="$manifest_root/TOPOLOGY_RESHARD_AUDIT.json"
runtime_revision_audit="$manifest_root/RUNTIME_REVISION_AUDIT.json"
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
[[ -r "$metadata" && -r "$audit" && -r "$topology_audit" &&
   -r "$runtime_revision_audit" ]] || {
  echo "formal Stage-1 v5 56-way manifest is not ready: $manifest_root" >&2
  exit 66
}
[[ "$output_root" != "$legacy_menu_polluted_output" ]] || {
  echo "refusing menu-clean revision against quarantined legacy output: $output_root" >&2
  exit 64
}
[[ -x "$root/build/$h200_build_tag/bin/xonotic-local-sdl" &&
   -r "$root/locks/$h200_build_tag.sha256" &&
   -r "$h200_env_archive" &&
   -r "${h200_env_archive}.sha256" ]] || {
  echo "locked H200 build or environment archive is missing" >&2
  exit 66
}
python3 - "$metadata" "$audit" "$topology_audit" \
  "$runtime_revision_audit" "$manifest_root" <<'PY'
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


metadata_path = Path(sys.argv[1])
audit_path = Path(sys.argv[2])
topology_path = Path(sys.argv[3])
runtime_revision_path = Path(sys.argv[4])
root = Path(sys.argv[5])
metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
audit = json.loads(audit_path.read_text(encoding="utf-8"))
topology = json.loads(topology_path.read_text(encoding="utf-8"))
runtime_revision = json.loads(
    runtime_revision_path.read_text(encoding="utf-8")
)
checks = {
    "audit_passed": audit.get("passed") is True,
    "metadata_hash": audit.get("metadata_sha256") == sha256(metadata_path),
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
    "shard_count": metadata.get("shard_count") == 56,
    "primary_shards": len(metadata.get("primary", {}).get("shards", []))
    == 56,
    "shard_files": len(list((root / "shards/primary").glob(
        "shard-*-of-056.jsonl"
    ))) == 56,
    "topology_passed": topology.get("pass") is True,
    "topology_hash": (
        metadata.get("topology_reshard", {}).get("sha256")
        == sha256(topology_path)
        == audit.get("topology_reshard_sha256")
    ),
    "topology_only": (
        topology.get("checks", {}).get("only_topology_fields_changed")
        is True
    ),
    "episode_ids_unchanged": (
        topology.get("checks", {}).get(
            "episode_order_and_ids_unchanged"
        )
        is True
    ),
    "runtime_revision_passed": runtime_revision.get("passed") is True,
    "runtime_revision_hash": (
        metadata.get("runtime_revision", {}).get("sha256")
        == sha256(runtime_revision_path)
        == audit.get("runtime_revision_sha256")
    ),
    "input_manifests_unchanged": (
        runtime_revision.get("checks", {}).get(
            "input_manifests_byte_identical"
        )
        is True
    ),
    "synthetic_audio_fallback_absent": (
        runtime_revision.get("policy", {}).get(
            "synthetic_audio_fallback"
        )
        is False
    ),
    "resident_frontend_menu_close": (
        runtime_revision.get("checks", {}).get(
            "resident_frontend_menu_close_barrier_added"
        )
        is True
    ),
    "visual_heuristic_rejection_absent": (
        runtime_revision.get("checks", {}).get(
            "visual_content_heuristic_rejection_absent"
        )
        is True
    ),
    "mutable_journal_reads_are_locked": (
        runtime_revision.get("checks", {}).get(
            "mutable_journal_reads_are_locked"
        )
        is True
    ),
    "persistent_jsonl_corruption_remains_fatal": (
        runtime_revision.get("checks", {}).get(
            "persistent_jsonl_corruption_remains_fatal"
        )
        is True
    ),
    "warmup_evidence_resume_safe": (
        runtime_revision.get("checks", {}).get(
            "warmup_evidence_resume_safe"
        )
        is True
    ),
    "distributed_completion_barrier": (
        runtime_revision.get("checks", {}).get(
            "distributed_completion_barrier"
        )
        is True
    ),
}
if not all(checks.values()):
    raise SystemExit(f"formal 56-way manifest readiness failed: {checks}")
PY

job_name=${SENSECORE_JOB_NAME_OVERRIDE:-"xonotic-stage1-v5-resume-r5-primary-56x1-$(date -u +%Y%m%d-%H%M%S)"}
priority=${SENSECORE_JOB_PRIORITY:-NORMAL}
quota_type=${SENSECORE_QUOTA_TYPE:-reserved}
retry_times=${SENSECORE_RETRY_TIMES:-3}
task_command="bash -lc 'cd $root && STAGE1_CANDIDATE_WAVE=primary STAGE1_MANIFEST_ROOT=$manifest_root STAGE1_OUTPUT_ROOT=$output_root STAGE1_EXECUTION_MODE=resident STAGE1_MAX_OPERATIONAL_ATTEMPTS=2 STAGE1_RESUME_PASSES=3 STAGE1_GANG_NONFATAL_INCOMPLETE=1 STAGE1_DISTRIBUTED_BARRIER=1 STAGE1_DISTRIBUTED_BARRIER_TIMEOUT_SECONDS=21600 STAGE1_DISTRIBUTED_RANK0_EXIT_GRACE_SECONDS=30 STAGE1_DISTRIBUTED_RUN_ID=$job_name XONOTIC_BUILD_ARCH=x86_64 XONOTIC_BUILD_TAG=$h200_build_tag XONOTIC_ENV_ARCHIVE=$h200_env_archive XONOTIC_PIPELINES_PER_GPU=12 XONOTIC_LIVE_CONCURRENCY=12 XONOTIC_RENDER_CONCURRENCY=12 XONOTIC_RENDER_TIMEOUT_SECONDS=240 XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=120 XONOTIC_SDL_CONCURRENCY=12 XONOTIC_ENCODE_CONCURRENCY=4 XONOTIC_X264_THREADS=16 exec ./scripts/run_stage1_56x1_worker.sh'"

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
echo "worker_spec=$SENSECORE_H200_1GPU_WORKER_SPEC"
echo "task_command=$task_command"
if [[ "$dry_run" == 1 ]]; then
  printf 'dry_run_command=sco'
  printf ' %q' "${args[@]}"
  printf '\n'
  exit 0
fi
exec sco "${args[@]}"
