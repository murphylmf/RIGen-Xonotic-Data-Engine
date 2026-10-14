#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_bias_correction_v2_replenishment_v2"
output_root=${STAGE2_REPLENISHMENT_V2_OUTPUT_ROOT:-"${workspace}/stage2_bias_correction_v2_replenishment_v2_output"}
source_commit=7e8310b0d0c135774f5cfbdb08122eec1f12c99b
tmp_root=${STAGE2_REPLENISHMENT_V2_TMP_ROOT:-"./tmp/xonotic-stage2-bias-v2-replenishment-v2"}
log_root="${workspace}/logs/stage2_bias_correction_v2"
mkdir -p "$log_root" "$tmp_root"

export XONOTIC_BUILD_GLOB=build/capture-7e8310b0d0c1-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

cd "$workspace"
exec > >(tee -a "${log_root}/replenishment-v2.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest "${manifest_root}/shards/shard-000-of-001.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index 0 \
  --shard-count 1 \
  --workers "${STAGE2_REPLENISHMENT_V2_WORKERS:-2}" \
  --live-concurrency "${STAGE2_REPLENISHMENT_V2_LIVE:-2}" \
  --render-concurrency "${STAGE2_REPLENISHMENT_V2_RENDER:-2}" \
  --render-timeout-seconds 240 \
  --sdl-concurrency "${STAGE2_REPLENISHMENT_V2_SDL:-2}" \
  --encode-concurrency 1 \
  --x264-threads 16 \
  --x264-cpuset 0-15 \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 100 \
  --port-base 44200 \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 3
