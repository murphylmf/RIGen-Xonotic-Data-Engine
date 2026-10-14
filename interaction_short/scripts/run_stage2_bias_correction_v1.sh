#!/usr/bin/env bash
set -euo pipefail



workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_bias_correction_v1"
output_root=${STAGE2_BIAS_OUTPUT_ROOT:-"${workspace}/stage2_bias_correction_v1_output"}
shard_index=${STAGE2_BIAS_SHARD_INDEX:?set STAGE2_BIAS_SHARD_INDEX to 0..3}
shard_count=4
source_commit=b40e26fd4e33b18b2002bf24beb6a78cef5fac96

[[ "$shard_index" =~ ^[0-3]$ ]] || {
  echo "STAGE2_BIAS_SHARD_INDEX must be 0..3" >&2
  exit 64
}

tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")
tmp_root=${STAGE2_BIAS_TMP_ROOT:-"./tmp/xonotic-stage2-bias-v1/${tag}"}
port_base=$((38000 + shard_index * 256))
log_root="${workspace}/logs/stage2_bias_correction_v1"
mkdir -p "$log_root" "$tmp_root"

export XONOTIC_BUILD_GLOB=build/capture-b40e26fd4e33-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

cd "$workspace"
exec > >(tee -a "${log_root}/${tag}.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest \
  "${manifest_root}/shards/${tag}.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index "$shard_index" \
  --shard-count "$shard_count" \
  --workers "${STAGE2_BIAS_WORKERS_PER_SHARD:-3}" \
  --live-concurrency "${STAGE2_BIAS_LIVE_PER_SHARD:-3}" \
  --render-concurrency "${STAGE2_BIAS_RENDER_PER_SHARD:-3}" \
  --render-timeout-seconds 240 \
  --sdl-concurrency "${STAGE2_BIAS_SDL_PER_SHARD:-3}" \
  --encode-concurrency "${STAGE2_BIAS_ENCODE_PER_SHARD:-1}" \
  --x264-threads "${STAGE2_BIAS_X264_THREADS:-4}" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 5 \
  --port-base "$port_base" \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 2
