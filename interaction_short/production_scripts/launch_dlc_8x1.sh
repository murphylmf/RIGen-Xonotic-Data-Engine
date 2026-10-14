#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/.." && pwd -P)
run_id=${RUN_ID:-stage2_motion_near5_combo_40k_v9_accel_20260817}
shard_count=${WORLD_SIZE:-}
shard_index=${RANK:-}
required_shards=${STAGE2_REQUIRED_SHARDS:-8}
manifest_root=${STAGE2_MANIFEST_ROOT:-$root/manifests/stage2_motion_near5_combo_40k_v9_accel_20260817}
output_root=${STAGE2_OUTPUT_ROOT:-$root/production_runs/$run_id}
scratch_base=${STAGE2_SCRATCH_BASE:-./tmp/xonotic-stage2-motion-near5-combo}
workers=${STAGE2_WORKERS_PER_GPU:-8}
python_bin=${STAGE2_PYTHON:-./environment}

[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || {
  echo "RUN_ID contains unsupported characters" >&2
  exit 64
}
[[ "$shard_index" =~ ^[0-9]+$ && "$shard_count" =~ ^[0-9]+$ ]] || {
  echo "DLC must inject integer RANK and WORLD_SIZE" >&2
  exit 64
}
shard_index=$((10#$shard_index))
shard_count=$((10#$shard_count))
required_shards=$((10#$required_shards))
((shard_count == required_shards)) || {
  echo "expected WORLD_SIZE=$required_shards, got $shard_count" >&2
  exit 78
}
((shard_index >= 0 && shard_index < shard_count)) || {
  echo "RANK=$shard_index is outside the shard range" >&2
  exit 64
}
[[ "${NPROC_PER_NODE:-1}" == 1 ]] || {
  echo "use one process and one GPU per DLC Pod" >&2
  exit 78
}
[[ "$workers" =~ ^[0-9]+$ ]] && ((10#$workers >= 1 && 10#$workers <= 16)) || {
  echo "STAGE2_WORKERS_PER_GPU must be in [1,16]" >&2
  exit 64
}
workers=$((10#$workers))
[[ -x "$python_bin" ]] || {
  echo "missing production Python: $python_bin" >&2
  exit 66
}

rank_tag=$(printf '%03d' "$shard_index")
count_tag=$(printf '%03d' "$shard_count")
manifest="$manifest_root/shards-$count_tag/shard-$rank_tag-of-$count_tag.jsonl"
metadata="$manifest_root/MANIFEST_METADATA.json"
scratch_root="$scratch_base/$run_id/shard_$rank_tag"
log_root="$root/logs/$run_id/shard_$rank_tag"
port_base=$((26000 + shard_index * 100))

[[ -s "$manifest" && -s "$metadata" ]] || {
  echo "immutable manifest is missing: $manifest $metadata" >&2
  exit 66
}
for command in ffmpeg ffprobe flock nvidia-smi sha256sum tee; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "missing required command: $command" >&2
    exit 69
  }
done
visible_gpus=$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l)
((visible_gpus == 1)) || {
  echo "exactly one GPU must be visible, found $visible_gpus" >&2
  exit 78
}

mkdir -p "$log_root" "$scratch_root"
exec > >(tee -a "$log_root/run.log") 2>&1
echo "stage2_motion_shard_start run_id=$run_id rank=$shard_index/$shard_count workers=$workers manifest=$manifest"

export PYTHONUNBUFFERED=1
export XONOTIC_CAPTURE_ROOT="$root"
export XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG=capture-e1b6fef45bc3-aarch64
export XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT=e1b6fef45bc370d36b1f5e3ba04cd1de1d211403
export XONOTIC_BUILD_GLOB=build/capture-e1b6fef45bc3-aarch64
export XONOTIC_OFFLINE_ACCELERATE=1
export XONOTIC_LIVE_TIME_SCALE=${XONOTIC_LIVE_TIME_SCALE:-1}
export XONOTIC_ALLOW_LIVE_TIME_SCALE_ONE_VALIDATION=1
export XONOTIC_LIVE_CONCURRENCY=${XONOTIC_LIVE_CONCURRENCY:-8}
export XONOTIC_RENDER_CONCURRENCY=${XONOTIC_RENDER_CONCURRENCY:-8}
export XONOTIC_SDL_CONCURRENCY=${XONOTIC_SDL_CONCURRENCY:-8}
export XONOTIC_ENCODE_CONCURRENCY=${XONOTIC_ENCODE_CONCURRENCY:-8}
export XONOTIC_X264_THREADS=${XONOTIC_X264_THREADS:-4}
export XONOTIC_LIVE_TIMEOUT_SECONDS=${XONOTIC_LIVE_TIMEOUT_SECONDS:-240}
export XONOTIC_RENDER_TIMEOUT_SECONDS=${XONOTIC_RENDER_TIMEOUT_SECONDS:-240}
export XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=${XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS:-240}
export XONOTIC_RENDER_STARTUP_STALL_SECONDS=${XONOTIC_RENDER_STARTUP_STALL_SECONDS:-90}
export XONOTIC_PILOT_RENDER_ATTEMPTS=${XONOTIC_PILOT_RENDER_ATTEMPTS:-1}
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

cd "$root"
exec "$python_bin" -u production_scripts/run_stage2_motion_40k_shard.py \
  --manifest "$manifest" \
  --metadata "$metadata" \
  --output-root "$output_root" \
  --scratch-root "$scratch_root" \
  --shard-index "$shard_index" \
  --shard-count "$shard_count" \
  --workers "$workers" \
  --live-concurrency "$XONOTIC_LIVE_CONCURRENCY" \
  --render-concurrency "$XONOTIC_RENDER_CONCURRENCY" \
  --encode-concurrency "$XONOTIC_ENCODE_CONCURRENCY" \
  --x264-threads "$XONOTIC_X264_THREADS" \
  --port-base "$port_base" \
  --max-operational-attempts 4
