#!/usr/bin/env bash
set -euo pipefail


workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
manifest_root="${workspace}/manifests/stage2_prefrozen_player_motion_review_v1"
output_root=${STAGE2_PM_V1_OUTPUT_ROOT:-"${workspace}/stage2_prefrozen_player_motion_review_v1_output"}
shard_index=${STAGE2_PM_V1_SHARD_INDEX:?set STAGE2_PM_V1_SHARD_INDEX to 0..3}
shard_count=4
source_commit=82bf40a4ddeebefefb97feb58afa85766a27f58e

[[ "$shard_index" =~ ^[0-3]$ ]] || {
  echo "STAGE2_PM_V1_SHARD_INDEX must be 0..3" >&2
  exit 64
}

tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")
tmp_root=${STAGE2_PM_V1_TMP_ROOT:-"./tmp/xonotic-stage2-pm-v1-r1/${tag}"}
port_base=$((48048 + shard_index * 256))
log_root="${workspace}/logs/stage2_prefrozen_player_motion_review_v1/r1"
mkdir -p "$log_root" "$tmp_root"

export XONOTIC_BUILD_GLOB=build/capture-82bf40a4ddee-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export XONOTIC_LIVE_TIMEOUT_SECONDS=${STAGE2_PM_V1_LIVE_TIMEOUT_SECONDS:-360}

cd "$workspace"
exec > >(tee -a "${log_root}/${tag}.log") 2>&1
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest \
  "${manifest_root}/shards/${tag}.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "$output_root" \
  --shard-index "$shard_index" \
  --shard-count "$shard_count" \
  --workers "${STAGE2_PM_V1_WORKERS_PER_SHARD:-2}" \
  --live-concurrency "${STAGE2_PM_V1_LIVE_PER_SHARD:-1}" \
  --render-concurrency "${STAGE2_PM_V1_RENDER_PER_SHARD:-1}" \
  --render-timeout-seconds 240 \
  --sdl-concurrency "${STAGE2_PM_V1_SDL_PER_SHARD:-1}" \
  --encode-concurrency 1 \
  --x264-threads "${STAGE2_PM_V1_X264_THREADS:-12}" \
  --x264-cpuset "${STAGE2_PM_V1_X264_CPUSET:-0-95}" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 5 \
  --port-base "$port_base" \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 2
