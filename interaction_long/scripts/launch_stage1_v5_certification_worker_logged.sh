#!/usr/bin/env bash

set -uo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}

rank_hint=
if (( $# > 0 )); then
  rank_hint=$1
elif [[ -n ${SHARD_INDEX:-} ]]; then
  rank_hint=$SHARD_INDEX
elif [[ -n ${SENSECORE_PYTORCH_NODE_RANK:-} ]]; then
  rank_hint=$SENSECORE_PYTORCH_NODE_RANK
elif [[ -n ${JOB_COMPLETION_INDEX:-} ]]; then
  rank_hint=$JOB_COMPLETION_INDEX
elif [[ -n ${RANK:-} ]]; then
  rank_hint=$RANK
else
  rank_hint=unknown-host-$$
fi
task_id=${XONOTIC_DISTRIBUTED_TASK_ID:-${SENSECORE_JOB_NAME:-${JOB_ID:-manual}}}
safe_task_id=$(printf '%s' "$task_id" | LC_ALL=C tr -c 'A-Za-z0-9._-' '_')
safe_rank_hint=$(printf '%s' "$rank_hint" | LC_ALL=C tr -c 'A-Za-z0-9._-' '_')
[[ -n "$safe_task_id" ]] || safe_task_id=manual
[[ -n "$safe_rank_hint" ]] || safe_rank_hint=unknown

log_root="$root/logs/stage1_v5_certification_32x1/submit-bootstrap/$safe_task_id"
mkdir -p "$log_root" || {
  echo "cannot create persistent launcher log directory: $log_root" >&2
  exit 73
}
log="$log_root/rank-${safe_rank_hint}.log"
exec > >(tee -a "$log") 2>&1

echo "stage1_v5_launcher_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "launcher_log=$log"
echo "hostname=local"
echo "pid=$$"
echo "uid_gid=$(id -u):$(id -g)"
echo "pwd=$PWD"
echo "root=$root"
echo "rank_hint=$rank_hint"
echo "distributed_task_id=$task_id"
echo "sensecore_job_name=${SENSECORE_JOB_NAME:-unset}"
echo "sensecore_pytorch_node_rank=${SENSECORE_PYTORCH_NODE_RANK:-unset}"
echo "sensecore_pytorch_nnodes=${SENSECORE_PYTORCH_NNODES:-unset}"
echo "sensecore_accelerate_device_count=${SENSECORE_ACCELERATE_DEVICE_COUNT:-unset}"
echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"

cd "$root" || {
  echo "cannot enter capture root: $root" >&2
  exit 66
}
echo "worker_pwd=$PWD"
status=0
"$root/scripts/run_stage1_v5_certification_32x1_worker.sh" "$@" || status=$?
echo "stage1_v5_launcher_finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "worker_exit_status=$status"
exit "$status"
