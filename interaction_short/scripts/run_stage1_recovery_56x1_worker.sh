#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
shard_count=56
shard_index=
shard_index_source=
if (( $# > 0 )); then
  shard_index=$1
  shard_index_source=argument
elif [[ -n ${SHARD_INDEX:-} ]]; then
  shard_index=$SHARD_INDEX
  shard_index_source=SHARD_INDEX
elif [[ -n ${SENSECORE_PYTORCH_NODE_RANK:-} ]]; then
  shard_index=$SENSECORE_PYTORCH_NODE_RANK
  shard_index_source=SENSECORE_PYTORCH_NODE_RANK
elif [[ -n ${JOB_COMPLETION_INDEX:-} ]]; then
  shard_index=$JOB_COMPLETION_INDEX
  shard_index_source=JOB_COMPLETION_INDEX
elif [[ -n ${RANK:-} ]]; then
  shard_index=$RANK
  shard_index_source=RANK
elif [[ -n ${SENSECORE_JOB_COMPLETION_INDEX:-} ]]; then
  shard_index=$SENSECORE_JOB_COMPLETION_INDEX
  shard_index_source=SENSECORE_JOB_COMPLETION_INDEX
elif [[ -n ${SLURM_ARRAY_TASK_ID:-} ]]; then
  shard_index=$SLURM_ARRAY_TASK_ID
  shard_index_source=SLURM_ARRAY_TASK_ID
fi
[[ -n "$shard_index" && "$shard_index" =~ ^[0-9]+$ ]] || {
  echo "set a Stage-1 recovery shard index in 0..55" >&2
  exit 64
}
(( shard_index >= 0 && shard_index < shard_count )) || {
  echo "recovery shard index out of range: $shard_index" >&2
  exit 64
}
if [[ -n ${SENSECORE_ACCELERATE_DEVICE_COUNT:-} &&
      ${SENSECORE_ACCELERATE_DEVICE_COUNT} != 1 ]]; then
  echo "each recovery worker must request exactly one GPU" >&2
  exit 64
fi
if [[ "$shard_index_source" == SENSECORE_PYTORCH_NODE_RANK ||
      "$shard_index_source" == RANK ]] &&
   [[ -n ${SENSECORE_PYTORCH_NNODES:-} &&
      ${SENSECORE_PYTORCH_NNODES} != "$shard_count" ]]; then
  echo "recovery job requires 56 worker nodes" >&2
  exit 64
fi

manifest_root=${STAGE1_MANIFEST_ROOT:-"$root/manifests/stage1_foundation_v5_formal_56x1_recovery_r6"}
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v5_output_56x1_menu_clean_r3"}
metadata="$manifest_root/MANIFEST_METADATA.json"
audit="$manifest_root/MANIFEST_AUDIT.json"
recovery_audit="$manifest_root/RECOVERY_AUDIT.json"
tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")
manifest="$manifest_root/shards/primary/$tag.jsonl"
[[ -r "$manifest" && -r "$metadata" && -r "$audit" &&
   -r "$recovery_audit" ]] || {
  echo "sealed recovery manifest is incomplete: $manifest_root" >&2
  exit 66
}

read -r namespace source_job_stopped snapshot_sealed pending_rows \
  warmup_concurrency steady_lanes rank_stagger_seconds \
  rank_stagger_slots declared_output_root runtime_lock_relative \
  runtime_lock_sha runtime_lock_entries < <(
  python3 - "$metadata" "$audit" "$recovery_audit" <<'PY'
import json
import sys

metadata = json.load(open(sys.argv[1], encoding="utf-8"))
audit = json.load(open(sys.argv[2], encoding="utf-8"))
recovery_audit = json.load(open(sys.argv[3], encoding="utf-8"))
recovery = metadata.get("recovery") or {}
lock = metadata.get("runtime_code_lock") or {}
valid = (
    audit.get("passed") is True
    and recovery_audit.get("passed") is True
    and recovery.get("source_job_stopped") is True
    and recovery.get("terminal_snapshot_sealed") is True
    and recovery.get("only_nonterminal_candidates") is True
    and recovery.get("journal_namespace_isolated") is True
    and recovery.get("attempt_numbers_continue_from_snapshot") is True
    and recovery.get("server_ready_before_client_start") is True
    and metadata.get("shard_count") == 56
)
if not valid:
    raise SystemExit("recovery metadata is not sealed/runnable")
print(
    recovery["namespace"],
    int(recovery["source_job_stopped"]),
    int(recovery["terminal_snapshot_sealed"]),
    int(recovery["pending_candidates"]),
    int(recovery["warmup_concurrency"]),
    int(recovery["steady_lane_limit"]),
    int(recovery["rank_start_stagger_seconds"]),
    int(recovery["rank_start_stagger_slots"]),
    recovery["output_root"],
    lock["path"],
    lock["sha256"],
    int(lock["entries"]),
)
PY
)
[[ "$source_job_stopped" == 1 && "$snapshot_sealed" == 1 ]] || {
  echo "recovery source job is not sealed as stopped" >&2
  exit 65
}
[[ "$output_root" == "$declared_output_root" ]] || {
  echo "recovery output root mismatch: declared=$declared_output_root actual=$output_root" >&2
  exit 65
}
[[ "$namespace" =~ ^[a-z0-9][a-z0-9._-]{0,95}$ ]] || {
  echo "invalid recovery namespace: $namespace" >&2
  exit 65
}
[[ "$warmup_concurrency" == 4 && "$steady_lanes" == 12 ]] || {
  echo "unexpected recovery concurrency contract" >&2
  exit 65
}
[[ "$rank_stagger_seconds" == 15 && "$rank_stagger_slots" == 8 ]] || {
  echo "unexpected recovery rank-start stagger contract" >&2
  exit 65
}
runtime_lock="$root/$runtime_lock_relative"
[[ -r "$runtime_lock" &&
   "$runtime_lock_sha" =~ ^[0-9a-f]{64}$ &&
   "$runtime_lock_entries" =~ ^[1-9][0-9]*$ ]] || {
  echo "invalid recovery runtime lock" >&2
  exit 65
}
printf '%s  %s\n' "$runtime_lock_sha" "$runtime_lock" |
  sha256sum -c - >/dev/null
(
  cd "$root"
  sha256sum -c "$runtime_lock" >/dev/null
)
(( $(wc -l < "$runtime_lock") == runtime_lock_entries )) || {
  echo "recovery runtime lock entry count mismatch" >&2
  exit 65
}

machine_arch=${XONOTIC_BUILD_ARCH:-$(uname -m)}
case "$machine_arch" in
  amd64) machine_arch=x86_64 ;;
  arm64) machine_arch=aarch64 ;;
  x86_64|aarch64) ;;
  *)
    echo "unsupported recovery worker architecture: $machine_arch" >&2
    exit 69
    ;;
esac
build_tag=${XONOTIC_BUILD_TAG:-capture-7e8310b0d0c1-"$machine_arch"}
build_lock="$root/locks/$build_tag.sha256"
[[ -r "$build_lock" ]] || {
  echo "locked Xonotic build missing: $build_lock" >&2
  exit 66
}
verify_relocated_build_lock() {
  local digest locked_path relative
  while read -r digest locked_path; do
    relative=${locked_path#*"$build_tag"/}
    [[ "$digest" =~ ^[0-9a-f]{64}$ &&
       "$relative" != "$locked_path" &&
       "$relative" != /* &&
       "$relative" != *..* ]] || return 65
    printf '%s  %s/build/%s/%s\n' \
      "$digest" "$root" "$build_tag" "$relative"
  done < "$build_lock"
}
verify_relocated_build_lock | sha256sum -c - >/dev/null

workers=${XONOTIC_PIPELINES_PER_GPU:-12}
live_concurrency=${XONOTIC_LIVE_CONCURRENCY:-12}
render_concurrency=${XONOTIC_RENDER_CONCURRENCY:-12}
sdl_concurrency=${XONOTIC_SDL_CONCURRENCY:-12}
encode_concurrency=${XONOTIC_ENCODE_CONCURRENCY:-4}
x264_threads=${XONOTIC_X264_THREADS:-16}
render_timeout_seconds=${XONOTIC_RENDER_TIMEOUT_SECONDS:-240}
control_timeout_seconds=${XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS:-120}
[[ "$workers" == "$steady_lanes" ]] || {
  echo "recovery steady lane count is locked to $steady_lanes" >&2
  exit 64
}
[[ "${XONOTIC_RESIDENT_WARMUP_CONCURRENCY:-4}" == \
   "$warmup_concurrency" ]] || {
  echo "recovery warm-up concurrency is locked to $warmup_concurrency" >&2
  exit 64
}

select_x264_cpuset() {
  local effective_path=/sys/fs/cgroup/cpuset.cpus.effective
  [[ -r "$effective_path" ]] || return 0
  python3 - "$(tr -d '[:space:]' < "$effective_path")" <<'PY'
import sys

cpus = []
for part in sys.argv[1].split(","):
    if not part:
        continue
    if "-" in part:
        start, end = map(int, part.split("-", 1))
        cpus.extend(range(start, end + 1))
    else:
        cpus.append(int(part))
selected = sorted(set(cpus))[:16]
ranges = []
for cpu in selected:
    if not ranges or cpu != ranges[-1][1] + 1:
        ranges.append([cpu, cpu])
    else:
        ranges[-1][1] = cpu
print(",".join(
    str(start) if start == end else f"{start}-{end}"
    for start, end in ranges
))
PY
}
if [[ -v XONOTIC_X264_CPUSET ]]; then
  x264_cpuset=$XONOTIC_X264_CPUSET
else
  x264_cpuset=$(select_x264_cpuset)
fi

resume_passes=${STAGE1_RESUME_PASSES:-3}
resume_delay_seconds=${STAGE1_RESUME_DELAY_SECONDS:-5}
max_operational_attempts=${STAGE1_MAX_OPERATIONAL_ATTEMPTS:-2}
episode_limit=${STAGE1_EPISODE_LIMIT:-0}
[[ "$episode_limit" =~ ^[0-9]+$ ]] || {
  echo "invalid STAGE1_EPISODE_LIMIT: $episode_limit" >&2
  exit 64
}
barrier_timeout_seconds=${STAGE1_DISTRIBUTED_BARRIER_TIMEOUT_SECONDS:-14400}
rank0_grace_seconds=${STAGE1_DISTRIBUTED_RANK0_EXIT_GRACE_SECONDS:-30}
distributed_barrier=${STAGE1_DISTRIBUTED_BARRIER:-}
if [[ -z "$distributed_barrier" ]]; then
  if [[ ${SENSECORE_PYTORCH_NNODES:-} == "$shard_count" ]]; then
    distributed_barrier=1
  else
    distributed_barrier=0
  fi
fi
[[ "$distributed_barrier" == 0 ||
   "$distributed_barrier" == 1 ]] || {
  echo "STAGE1_DISTRIBUTED_BARRIER must be 0 or 1" >&2
  exit 64
}
run_id=${STAGE1_DISTRIBUTED_RUN_ID:-${SENSECORE_JOB_NAME:-${JOB_ID:-${SLURM_JOB_ID:-}}}}
[[ "$distributed_barrier" == 0 || -n "$run_id" ]] || {
  echo "recovery distributed run ID is required" >&2
  exit 64
}
if [[ "$distributed_barrier" == 1 ]]; then
  run_fingerprint=$(
    python3 - "$run_id" "$namespace" "$manifest_root" \
      "$output_root" "$runtime_lock_sha" <<'PY'
import hashlib
import sys
print(hashlib.sha256("\0".join(sys.argv[1:]).encode()).hexdigest())
PY
  )
  barrier_root="$output_root/manifests/distributed_recovery_runs/$namespace/$run_fingerprint"
else
  run_fingerprint=disabled
  barrier_root=
fi
port_base=${XONOTIC_STAGE1_PORT_BASE:-24000}
port_stride=${XONOTIC_STAGE1_PORT_STRIDE:-64}
task_id=${SENSECORE_JOB_NAME:-${JOB_ID:-manual}}
tmp_root=${XONOTIC_CAPTURE_TMP:-${TMPDIR:-./tmp}/xonotic-stage1-recovery/${task_id}-${tag}}
log_root="$output_root/logs/recovery_runs/$namespace"
log="$log_root/$tag.log"
min_afs_free_bytes=${STAGE1_MIN_AFS_FREE_BYTES:-2000000000000}
afs_free_bytes=$(df -PB1 "$root" | awk 'NR==2 {print $4}')
(( afs_free_bytes >= min_afs_free_bytes )) || {
  echo "insufficient AFS free space for recovery" >&2
  exit 75
}
mkdir -p "$tmp_root" "$log_root"

export XONOTIC_CAPTURE_ROOT="$root"
export XONOTIC_CAPTURE_TMP="$tmp_root"
export XONOTIC_BUILD_GLOB="build/$build_tag"
export STAGE1_RECOVERY_METADATA="$metadata"
export STAGE1_RECOVERY_NAMESPACE="$namespace"
export XONOTIC_RESIDENT_WARMUP_CONCURRENCY="$warmup_concurrency"
export XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS="$control_timeout_seconds"
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

exec > >(tee -a "$log") 2>&1
echo "stage1_recovery_worker_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "namespace=$namespace"
echo "worker_hostname=local"
echo "shard_index=$shard_index"
echo "shard_count=$shard_count"
echo "manifest=$manifest"
echo "output_root=$output_root"
echo "pending_snapshot_rows=$pending_rows"
echo "episode_limit=$episode_limit"
echo "steady_lanes=$workers"
echo "warmup_concurrency=$warmup_concurrency"
echo "server_ready_marker=Server spawned."
echo "journal_namespace_isolated=1"
echo "tmp_root=$tmp_root"
echo "runtime_code_lock_sha256=$runtime_lock_sha"
echo "distributed_run_id=$run_id"
echo "distributed_run_fingerprint=$run_fingerprint"
rank_start_delay=$(( (shard_index % rank_stagger_slots) * rank_stagger_seconds ))
echo "rank_start_stagger_seconds=$rank_start_delay"
if (( rank_start_delay > 0 )); then
  sleep "$rank_start_delay"
fi

run_shard_pass() {
  "$script_dir/cci_run.sh" \
    python "$script_dir/stage1_recovery_runtime.py" run \
    --input-manifest "$manifest" \
    --manifest-metadata "$metadata" \
    --manifest-audit "$audit" \
    --output-root "$output_root" \
    --tmp-root "$tmp_root" \
    --shard-index "$shard_index" \
    --shard-count "$shard_count" \
    --workers "$workers" \
    --execution-mode resident \
    --live-concurrency "$live_concurrency" \
    --render-concurrency "$render_concurrency" \
    --render-timeout-seconds "$render_timeout_seconds" \
    --sdl-concurrency "$sdl_concurrency" \
    --encode-concurrency "$encode_concurrency" \
    --x264-threads "$x264_threads" \
    --x264-cpuset "$x264_cpuset" \
    --limit "$episode_limit" \
    --port-base "$port_base" \
    --port-stride "$port_stride" \
    --gpu-index 0 \
    --max-operational-attempts "$max_operational_attempts" \
    --incomplete-exit-code 3
}

final_disposition=
final_resume_pass=0
for (( pass = 1; pass <= resume_passes; pass++ )); do
  echo "stage1_recovery_pass_started=$pass/$resume_passes"
  set +e
  run_shard_pass
  pass_rc=$?
  set -e
  case "$pass_rc" in
    0)
      final_disposition=complete
      final_resume_pass=$pass
      break
      ;;
    3)
      final_disposition=retryable_incomplete
      final_resume_pass=$pass
      (( pass < resume_passes )) && sleep "$resume_delay_seconds"
      ;;
    *)
      echo "stage1_recovery_fatal_exit_code=$pass_rc" >&2
      exit "$pass_rc"
      ;;
  esac
done

if [[ "$distributed_barrier" == 0 ]]; then
  echo "stage1_recovery_distributed_barrier=disabled"
  exit 0
fi

barrier_script="$script_dir/stage1_distributed_barrier.py"
"$script_dir/cci_run.sh" python "$barrier_script" mark \
  --root "$barrier_root" \
  --fingerprint "$run_fingerprint" \
  --shard-count "$shard_count" \
  --run-id "$run_id" \
  --shard-index "$shard_index" \
  --disposition "$final_disposition" \
  --resume-pass "$final_resume_pass" \
  --candidate-wave primary \
  --manifest-root "$manifest_root" \
  --output-root "$output_root"
echo "stage1_recovery_distributed_marker_written=$tag"

deadline=$(( $(date +%s) + barrier_timeout_seconds ))
result="$tmp_root/distributed_barrier_result.json"
if (( shard_index == 0 )); then
  while true; do
    set +e
    "$script_dir/cci_run.sh" python "$barrier_script" finalize \
      --root "$barrier_root" \
      --fingerprint "$run_fingerprint" \
      --shard-count "$shard_count" \
      --run-id "$run_id" > "$result"
    rc=$?
    set -e
    (( rc == 0 )) && break
    (( rc == 3 )) || {
      cat "$result" >&2
      exit "$rc"
    }
    (( $(date +%s) < deadline )) || exit 75
    sleep 10
  done
fi
while true; do
  set +e
  "$script_dir/cci_run.sh" python "$barrier_script" validate-ready \
    --root "$barrier_root" \
    --fingerprint "$run_fingerprint" \
    --shard-count "$shard_count" > "$result"
  rc=$?
  set -e
  (( rc == 0 )) && break
  (( rc == 3 )) || exit "$rc"
  (( $(date +%s) < deadline )) || exit 75
  sleep 10
done
"$script_dir/cci_run.sh" python "$barrier_script" acknowledge-ready \
  --root "$barrier_root" \
  --fingerprint "$run_fingerprint" \
  --shard-count "$shard_count" \
  --run-id "$run_id" \
  --shard-index "$shard_index" > "$result"
cat "$result"
if (( shard_index != 0 )); then
  echo "stage1_recovery_nonzero_rank_clean_exit=1"
  exit 0
fi

ack_deadline=$(( $(date +%s) + barrier_timeout_seconds ))
while true; do
  set +e
  "$script_dir/cci_run.sh" python "$barrier_script" \
    acknowledgement-status \
    --root "$barrier_root" \
    --fingerprint "$run_fingerprint" \
    --shard-count "$shard_count" > "$result"
  rc=$?
  set -e
  (( rc == 0 )) && break
  (( rc == 3 )) || exit "$rc"
  (( $(date +%s) < ack_deadline )) || exit 75
  sleep 10
done
(( rank0_grace_seconds == 0 )) || sleep "$rank0_grace_seconds"
echo "stage1_recovery_rank0_clean_exit_last=1"
