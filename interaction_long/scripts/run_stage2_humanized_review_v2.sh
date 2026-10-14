#!/usr/bin/env bash
set -euo pipefail



workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_humanized_review_v2"
output_root=${STAGE2_HUMAN_V2_OUTPUT_ROOT:-"${workspace}/stage2_humanized_review_v2_output"}
shard_index=${STAGE2_HUMAN_V2_SHARD_INDEX:?set STAGE2_HUMAN_V2_SHARD_INDEX to 0..3}
shard_count=4
source_commit=7e8310b0d0c135774f5cfbdb08122eec1f12c99b

[[ "$shard_index" =~ ^[0-3]$ ]] || {
  echo "STAGE2_HUMAN_V2_SHARD_INDEX must be 0..3" >&2
  exit 64
}

tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")
tmp_root=${STAGE2_HUMAN_V2_TMP_ROOT:-"./tmp/xonotic-stage2-human-v2/${tag}"}
port_base=$((46000 + shard_index * 256))
log_root="${workspace}/logs/stage2_humanized_review_v2"
mkdir -p "$log_root" "$tmp_root"

export XONOTIC_BUILD_GLOB=build/capture-7e8310b0d0c1-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl



export XONOTIC_LIVE_TIMEOUT_SECONDS=${STAGE2_HUMAN_V2_LIVE_TIMEOUT_SECONDS:-360}

cd "$workspace"
exec > >(tee -a "${log_root}/${tag}.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest \
  "${manifest_root}/shards/${tag}.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index "$shard_index" \
  --shard-count "$shard_count" \
  --workers "${STAGE2_HUMAN_V2_WORKERS_PER_SHARD:-2}" \
  --live-concurrency "${STAGE2_HUMAN_V2_LIVE_PER_SHARD:-1}" \
  --render-concurrency "${STAGE2_HUMAN_V2_RENDER_PER_SHARD:-1}" \
  --render-timeout-seconds 240 \
  --sdl-concurrency "${STAGE2_HUMAN_V2_SDL_PER_SHARD:-1}" \
  --encode-concurrency 1 \
  --x264-threads "${STAGE2_HUMAN_V2_X264_THREADS:-12}" \
  --x264-cpuset "${STAGE2_HUMAN_V2_X264_CPUSET:-0-95}" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 5 \
  --port-base "$port_base" \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 2
