#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_bias_correction_v2_replenishment_v1"
output_root=${STAGE2_REPLENISHMENT_OUTPUT_ROOT:-"${workspace}/stage2_bias_correction_v2_replenishment_v1_output"}
source_commit=7e8310b0d0c135774f5cfbdb08122eec1f12c99b
tmp_root=${STAGE2_REPLENISHMENT_TMP_ROOT:-"./tmp/xonotic-stage2-bias-v2-replenishment-v1"}
log_root="${workspace}/logs/stage2_bias_correction_v2"
mkdir -p "$log_root" "$tmp_root"

export XONOTIC_BUILD_GLOB=build/capture-7e8310b0d0c1-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

cd "$workspace"
exec > >(tee -a "${log_root}/replenishment-v1.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest "${manifest_root}/shards/shard-000-of-001.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index 0 \
  --shard-count 1 \
  --workers 1 \
  --live-concurrency 1 \
  --render-concurrency 1 \
  --render-timeout-seconds 240 \
  --sdl-concurrency 1 \
  --encode-concurrency 1 \
  --x264-threads 16 \
  --x264-cpuset 0-15 \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 100 \
  --port-base 44000 \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 3
