#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
candidate_root="$root/manifests/stage1_foundation_v5_certification"
build_tag=capture-b40e26fd4e33-x86_64
env_archive="$root/env/xonotic-capture-linux-x86_64-20260727.tar.gz"
job_name=${SENSECORE_JOB_NAME_OVERRIDE:-"xonotic-stage1-v5-certify-$(date -u +%Y%m%d-%H%M%S)"}
safe_job_name=$(printf '%s' "$job_name" | LC_ALL=C tr -c 'A-Za-z0-9._-' '_')
[[ -n "$safe_job_name" ]] || safe_job_name=unknown
submission_log_root="$root/logs/stage1_v5_certification_32x1/submissions"
mkdir -p "$submission_log_root" || {
  echo "cannot create submission log directory: $submission_log_root" >&2
  exit 73
}
submission_log="$submission_log_root/$safe_job_name.log"
exec > >(tee -a "$submission_log") 2>&1
echo "submission_bootstrap_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "submission_log=$submission_log"
echo "submission_pwd=$PWD"
echo "submission_root=$root"
submission_on_exit() {
  local status=$?
  trap - EXIT
  echo "submission_finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "submission_exit_status=$status"
  exit "$status"
}
trap submission_on_exit EXIT

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

required_candidates=(
  PROTOTYPE_METADATA.json
  CERTIFICATION_SPARE_PROTOTYPE_METADATA.json
  TARGETED_PROTOTYPE_METADATA.json
  FAST_TRAVERSAL_WORLD_PROTOTYPE_METADATA.json
  path_prototypes_primary.jsonl
  path_prototypes_replenishment.jsonl
  path_prototypes_certification_spare.jsonl
  path_prototypes_targeted_visible_collision.jsonl
  path_prototypes_targeted_fast_traversal_world_balanced.jsonl
)
for name in "${required_candidates[@]}"; do
  [[ -r "$candidate_root/$name" ]] || {
    echo "Stage-1 v5 certification input missing: $name" >&2
    exit 66
  }
done
[[ -x "$root/build/$build_tag/bin/xonotic-local-sdl" &&
   -r "$root/locks/$build_tag.sha256" &&
   -r "$env_archive" &&
   -r "${env_archive}.sha256" ]] || {
  echo "locked H200 build or environment archive is missing" >&2
  exit 66
}
bash -n \
  "$root/scripts/launch_stage1_v5_certification_worker_logged.sh" \
  "$root/scripts/run_stage1_v5_certification_32x1_worker.sh" \
  "$root/scripts/finalize_stage1_v5_production_readiness.sh"
python3 -m py_compile \
  "$root/scripts/certify_stage1_v5_paths.py" \
  "$root/scripts/merge_stage1_v5_certificate_shards.py" \
  "$root/scripts/prepare_stage1_v5_manifests.py"

priority=${SENSECORE_JOB_PRIORITY:-NORMAL}
quota_type=${SENSECORE_QUOTA_TYPE:-reserved}
retry_times=${SENSECORE_RETRY_TIMES:-3}
certification_workers=${XONOTIC_CERTIFICATION_SHARD_COUNT:-32}
[[ "$certification_workers" =~ ^[1-9][0-9]*$ ]] &&
  (( certification_workers <= 999 )) || {
  echo "XONOTIC_CERTIFICATION_SHARD_COUNT must be in 1..999" >&2
  exit 64
}
task_command="bash -lc 'XONOTIC_CAPTURE_ROOT=$root XONOTIC_DISTRIBUTED_TASK_ID=$job_name XONOTIC_BUILD_ARCH=x86_64 XONOTIC_BUILD_TAG=$build_tag XONOTIC_ENV_ARCHIVE=$env_archive XONOTIC_CERTIFICATION_SHARD_COUNT=$certification_workers XONOTIC_PATH_CERT_WORKERS=1 XONOTIC_COLLISION_CERT_WORKERS=1 XONOTIC_LIVE_CONCURRENCY=1 XONOTIC_SDL_CONCURRENCY=1 XONOTIC_LIVE_TIMEOUT_SECONDS=180 XONOTIC_ENGINE_NET_TIMEOUT_SECONDS=600 XONOTIC_CAPTURE_CLIENT_OVERLAY=configs/capture_client_join_retry.cfg STAGE1_V5_OPERATIONAL_RETRY_DELAY_SECONDS=10 STAGE1_V5_DISTRIBUTED_WAIT_TIMEOUT_SECONDS=0 exec $root/scripts/launch_stage1_v5_certification_worker_logged.sh'"

args=(
  acp jobs create
  "--workspace-name=$SENSECORE_WORKSPACE_NAME"
  "--aec2-name=$SENSECORE_AEC2_NAME"
  "--job-name=$job_name"
  "--container-image-url=$SENSECORE_CONTAINER_IMAGE"
  "--training-framework=pytorch"
  "--worker-spec=$SENSECORE_H200_1GPU_WORKER_SPEC"
  "--worker-nodes=$certification_workers"
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
echo "purpose=stage1_v5_path_certification_and_formal_manifest_only"
echo "workers=$certification_workers"
echo "gpus_per_worker=1"
echo "worker_spec=$SENSECORE_H200_1GPU_WORKER_SPEC"
echo "task_command=$task_command"
echo "submission_log=$submission_log"
if [[ "$dry_run" == 1 ]]; then
  printf 'dry_run_command=sco'
  printf ' %q' "${args[@]}"
  printf '\n'
  exit 0
fi
sco "${args[@]}"
