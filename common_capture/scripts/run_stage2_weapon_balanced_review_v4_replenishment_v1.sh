#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_weapon_balanced_review_v4_replenishment_v1"
output_root=${STAGE2_WB_V4_REP1_OUTPUT_ROOT:-"${workspace}/stage2_weapon_balanced_review_v4_replenishment_v1_output"}
shard_index=${STAGE2_WB_V4_REP1_SHARD_INDEX:?set STAGE2_WB_V4_REP1_SHARD_INDEX to 0..3}
shard_count=4
source_commit=82bf40a4ddeebefefb97feb58afa85766a27f58e

[[ "$shard_index" =~ ^[0-3]$ ]] || {
  echo "STAGE2_WB_V4_REP1_SHARD_INDEX must be 0..3" >&2
  exit 64
}

tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")
input_manifest="${manifest_root}/shards/${tag}.jsonl"
run_id=${STAGE2_WB_V4_REP1_RUN_ID:-r1}
tmp_root=${STAGE2_WB_V4_REP1_TMP_ROOT:-"./tmp/xonotic-stage2-wb-v4-rep1-${run_id}/${tag}"}
port_base=$((58048 + shard_index * 128))
log_root="${workspace}/logs/stage2_weapon_balanced_review_v4_replenishment_v1/${run_id}"
mkdir -p "$log_root" "$tmp_root"

if [[ ! -s "$input_manifest" ]]; then
  echo "no replacement rows for ${tag}"
  exit 0
fi

export XONOTIC_BUILD_GLOB=build/capture-82bf40a4ddee-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export XONOTIC_LIVE_TIMEOUT_SECONDS=${STAGE2_WB_V4_REP1_LIVE_TIMEOUT_SECONDS:-360}

cd "$workspace"
exec > >(tee -a "${log_root}/${tag}.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest "$input_manifest" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index "$shard_index" \
  --shard-count "$shard_count" \
  --workers 1 \
  --live-concurrency 1 \
  --render-concurrency 1 \
  --render-timeout-seconds 240 \
  --sdl-concurrency 1 \
  --encode-concurrency 1 \
  --x264-threads 12 \
  --x264-cpuset "${STAGE2_WB_V4_REP1_X264_CPUSET:-0-95}" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 5 \
  --port-base "$port_base" \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 3
