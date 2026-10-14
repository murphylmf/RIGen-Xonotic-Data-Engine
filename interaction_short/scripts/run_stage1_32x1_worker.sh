#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
shard_count=32
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
candidate_wave=${STAGE1_CANDIDATE_WAVE:-primary}

[[ -n "$shard_index" ]] || {
  echo "pass shard index 0..31, or set SHARD_INDEX/JOB_COMPLETION_INDEX/SENSECORE_PYTORCH_NODE_RANK" >&2
  exit 64
}
[[ "$shard_index" =~ ^[0-9]+$ ]] || {
  echo "invalid shard index: $shard_index" >&2
  exit 64
}
(( shard_index >= 0 && shard_index < shard_count )) || {
  echo "shard index out of range: $shard_index" >&2
  exit 64
}
[[ "$candidate_wave" == primary || "$candidate_wave" == replenishment ]] || {
  echo "invalid STAGE1_CANDIDATE_WAVE: $candidate_wave" >&2
  exit 64
}
if [[ -n ${SENSECORE_ACCELERATE_DEVICE_COUNT:-} &&
      ${SENSECORE_ACCELERATE_DEVICE_COUNT} != 1 ]]; then
  echo "SenseCore worker must request exactly one GPU; got SENSECORE_ACCELERATE_DEVICE_COUNT=${SENSECORE_ACCELERATE_DEVICE_COUNT}" >&2
  exit 64
fi
if [[ "$shard_index_source" == SENSECORE_PYTORCH_NODE_RANK ||
      "$shard_index_source" == RANK ]] &&
   [[ -n ${SENSECORE_PYTORCH_NNODES:-} &&
      ${SENSECORE_PYTORCH_NNODES} != "$shard_count" ]]; then
  echo "SenseCore job must have ${shard_count} workers; got SENSECORE_PYTORCH_NNODES=${SENSECORE_PYTORCH_NNODES}" >&2
  exit 64
fi

tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")


manifest_root=${STAGE1_MANIFEST_ROOT:-"$root/manifests/stage1_foundation_v5_formal"}
manifest="$manifest_root/shards/$candidate_wave/$tag.jsonl"
metadata="$manifest_root/MANIFEST_METADATA.json"
audit="$manifest_root/MANIFEST_AUDIT.json"
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v5_output"}
workers=${XONOTIC_PIPELINES_PER_GPU:-${XONOTIC_RENDERERS_PER_GPU:-12}}
execution_mode=${STAGE1_EXECUTION_MODE:-resident}
[[ "$execution_mode" == resident || "$execution_mode" == oneshot ]] || {
  echo "invalid STAGE1_EXECUTION_MODE: $execution_mode" >&2
  exit 64
}
live_concurrency=${XONOTIC_LIVE_CONCURRENCY:-$workers}
render_concurrency=${XONOTIC_RENDER_CONCURRENCY:-$workers}
render_timeout_seconds=${XONOTIC_RENDER_TIMEOUT_SECONDS:-240}
sdl_concurrency=${XONOTIC_SDL_CONCURRENCY:-$workers}
encode_concurrency=${XONOTIC_ENCODE_CONCURRENCY:-4}
x264_threads=${XONOTIC_X264_THREADS:-16}
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
        start, end = (int(value) for value in part.split("-", 1))
        cpus.extend(range(start, end + 1))
    else:
        cpus.append(int(part))
selected = sorted(set(cpus))[:16]
ranges = []
for cpu in selected:
    if not ranges or cpu != ranges[-1][-1] + 1:
        ranges.append([cpu, cpu])
    else:
        ranges[-1][-1] = cpu
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
max_operational_attempts=${STAGE1_MAX_OPERATIONAL_ATTEMPTS:-2}
episode_limit=${STAGE1_EPISODE_LIMIT:-0}
port_base=${XONOTIC_STAGE1_PORT_BASE:-24000}
port_stride=${XONOTIC_STAGE1_PORT_STRIDE:-64}
task_id=${SENSECORE_JOB_NAME:-${JOB_ID:-${SLURM_JOB_ID:-manual}}}
tmp_root=${XONOTIC_CAPTURE_TMP:-${TMPDIR:-./tmp}/xonotic-stage1/${task_id}-${tag}}
log_root="$output_root/logs/$candidate_wave"
log="$log_root/$tag.log"
machine_arch=${XONOTIC_BUILD_ARCH:-$(uname -m)}
case "$machine_arch" in
  amd64) machine_arch=x86_64 ;;
  arm64) machine_arch=aarch64 ;;
  x86_64|aarch64) ;;
  *)
    echo "unsupported worker architecture: $machine_arch" >&2
    exit 69
    ;;
esac
build_tag=${XONOTIC_BUILD_TAG:-capture-7e8310b0d0c1-"$machine_arch"}
build_lock="$root/locks/$build_tag.sha256"
min_afs_free_bytes=${STAGE1_MIN_AFS_FREE_BYTES:-2000000000000}

verify_relocated_build_lock() {
  local digest locked_path relative
  while read -r digest locked_path; do
    [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || {
      echo "invalid digest in build lock" >&2
      return 65
    }
    relative=${locked_path#*"$build_tag"/}
    [[ "$relative" != "$locked_path" &&
       "$relative" != /* &&
       "$relative" != *..* ]] || {
      echo "invalid path in build lock: $locked_path" >&2
      return 65
    }
    printf '%s  %s/build/%s/%s\n' \
      "$digest" "$root" "$build_tag" "$relative"
  done < "$build_lock"
}

[[ -r "$manifest" && -r "$metadata" && -r "$audit" &&
   -r "$build_lock" ]] || {
  echo "Stage-1 manifest, metadata, audit, or build lock missing" >&2
  exit 66
}
read -r runtime_lock_relative runtime_lock_sha runtime_lock_entries < <(
  python3 - "$metadata" <<'PY'
import json
import sys

metadata = json.loads(open(sys.argv[1], encoding="utf-8").read())
lock = metadata.get("runtime_code_lock") or {}
print(lock.get("path", ""), lock.get("sha256", ""), lock.get("entries", 0))
PY
)
[[ -n "$runtime_lock_relative" &&
   "$runtime_lock_relative" != /* &&
   "$runtime_lock_relative" != *..* &&
   "$runtime_lock_sha" =~ ^[0-9a-f]{64}$ &&
   "$runtime_lock_entries" =~ ^[1-9][0-9]*$ ]] || {
  echo "invalid or missing runtime code lock in formal metadata" >&2
  exit 65
}
runtime_lock="$root/$runtime_lock_relative"
[[ -r "$runtime_lock" ]] || {
  echo "runtime code lock missing: $runtime_lock" >&2
  exit 66
}
[[ "$min_afs_free_bytes" =~ ^[0-9]+$ ]] || {
  echo "invalid STAGE1_MIN_AFS_FREE_BYTES: $min_afs_free_bytes" >&2
  exit 64
}
afs_free_bytes=$(df -PB1 "$root" | awk 'NR==2 {print $4}')
[[ "$afs_free_bytes" =~ ^[0-9]+$ ]] || {
  echo "unable to determine AFS free space for $root" >&2
  exit 74
}
(( afs_free_bytes >= min_afs_free_bytes )) || {
  echo "insufficient AFS free space: have=$afs_free_bytes require=$min_afs_free_bytes" >&2
  exit 75
}
mkdir -p "$log_root" "$tmp_root"
export XONOTIC_CAPTURE_ROOT="$root"
export XONOTIC_CAPTURE_TMP="$tmp_root"
export XONOTIC_BUILD_GLOB="build/$build_tag"
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

exec > >(tee -a "$log") 2>&1
echo "stage1_worker_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "shard_index=$shard_index"
echo "shard_index_source=$shard_index_source"
echo "shard_count=$shard_count"
echo "candidate_wave=$candidate_wave"
echo "manifest=$manifest"
echo "manifest_audit=$audit"
echo "output_root=$output_root"
echo "tmp_root=$tmp_root"
echo "workers=$workers"
echo "execution_mode=$execution_mode"
echo "live_concurrency=$live_concurrency"
echo "render_concurrency=$render_concurrency"
echo "render_timeout_seconds=$render_timeout_seconds"
echo "sdl_concurrency=$sdl_concurrency"
echo "encode_concurrency=$encode_concurrency"
echo "x264_threads=$x264_threads"
echo "x264_cpuset=${x264_cpuset:-unbound}"
echo "max_operational_attempts=$max_operational_attempts"
echo "episode_limit=$episode_limit"
echo "effective_port_base=$((port_base + shard_index * port_stride))"
echo "scheduler_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
echo "scheduler_nvidia_visible_devices=${NVIDIA_VISIBLE_DEVICES:-unset}"
echo "afs_free_bytes_at_start=$afs_free_bytes"
echo "afs_minimum_free_bytes=$min_afs_free_bytes"
verify_relocated_build_lock | sha256sum -c - >/dev/null
echo "build_integrity=pass"
printf '%s  %s\n' "$runtime_lock_sha" "$runtime_lock" |
  sha256sum -c - >/dev/null
(
  cd "$root"
  sha256sum -c "$runtime_lock" >/dev/null
)
actual_runtime_lock_entries=$(wc -l < "$runtime_lock")
(( actual_runtime_lock_entries == runtime_lock_entries )) || {
  echo "runtime code lock entry count mismatch" >&2
  exit 65
}
echo "runtime_code_integrity=pass"
echo "runtime_code_lock=$runtime_lock"
echo "runtime_code_lock_sha256=$runtime_lock_sha"

exec "$script_dir/cci_run.sh" \
  python "$script_dir/run_stage1_manifest_shard.py" run \
  --input-manifest "$manifest" \
  --manifest-metadata "$metadata" \
  --manifest-audit "$audit" \
  --output-root "$output_root" \
  --tmp-root "$tmp_root" \
  --shard-index "$shard_index" \
  --shard-count "$shard_count" \
  --workers "$workers" \
  --execution-mode "$execution_mode" \
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
  --max-operational-attempts "$max_operational_attempts"
