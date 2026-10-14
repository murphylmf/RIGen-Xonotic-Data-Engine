#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_formal_stationary_extension_v1"
output_root=${STAGE2_FORMAL_STATIONARY_EXTENSION_V1_OUTPUT_ROOT:-"${workspace}/stage2_formal_stationary_extension_v1_output"}
run_id=${STAGE2_FORMAL_STATIONARY_EXTENSION_V1_RUN_ID:-r1}
lanes=${STAGE2_FORMAL_STATIONARY_EXTENSION_V1_LANES:-12}
tmp_root=${STAGE2_FORMAL_STATIONARY_EXTENSION_V1_TMP_ROOT:-"./tmp/xonotic-stage2-formal-stationary-extension-v1-${run_id}"}
log_root="${workspace}/logs/stage2_formal_stationary_extension_v1/${run_id}"
source_commit=82bf40a4ddeebefefb97feb58afa85766a27f58e

mkdir -p "$log_root" "$tmp_root"
export XONOTIC_BUILD_GLOB=build/capture-82bf40a4ddee-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export XONOTIC_LIVE_TIMEOUT_SECONDS=${STAGE2_FORMAL_STATIONARY_EXTENSION_V1_LIVE_TIMEOUT_SECONDS:-360}

cd "$workspace"
exec > >(tee -a "${log_root}/run.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard_formal.py run \
  --input-manifest "${manifest_root}/shards/shard-000-of-001.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index 0 \
  --shard-count 1 \
  --workers "$lanes" \
  --live-concurrency "$lanes" \
  --render-concurrency "$lanes" \
  --render-timeout-seconds 240 \
  --sdl-concurrency "$lanes" \
  --encode-concurrency 4 \
  --x264-threads 16 \
  --x264-cpuset "${STAGE2_FORMAL_STATIONARY_EXTENSION_V1_X264_CPUSET:-0-191}" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 100 \
  --port-base 61200 \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 3
