#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_weapon_balanced_review_v4_replenishment_v2"
output_root=${STAGE2_WB_V4_REP2_OUTPUT_ROOT:-"${workspace}/stage2_weapon_balanced_review_v4_replenishment_v2_output"}
source_commit=82bf40a4ddeebefefb97feb58afa85766a27f58e
run_id=${STAGE2_WB_V4_REP2_RUN_ID:-r1}
tag=shard-000-of-004
tmp_root=${STAGE2_WB_V4_REP2_TMP_ROOT:-"./tmp/xonotic-stage2-wb-v4-rep2-${run_id}/${tag}"}
log_root="${workspace}/logs/stage2_weapon_balanced_review_v4_replenishment_v2/${run_id}"
mkdir -p "$log_root" "$tmp_root"

export XONOTIC_BUILD_GLOB=build/capture-82bf40a4ddee-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export XONOTIC_LIVE_TIMEOUT_SECONDS=${STAGE2_WB_V4_REP2_LIVE_TIMEOUT_SECONDS:-360}

cd "$workspace"
exec > >(tee -a "${log_root}/${tag}.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest "${manifest_root}/shards/${tag}.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index 0 \
  --shard-count 4 \
  --workers 1 \
  --live-concurrency 1 \
  --render-concurrency 1 \
  --render-timeout-seconds 240 \
  --sdl-concurrency 1 \
  --encode-concurrency 1 \
  --x264-threads 12 \
  --x264-cpuset "${STAGE2_WB_V4_REP2_X264_CPUSET:-0-95}" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 5 \
  --port-base 60160 \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 3
