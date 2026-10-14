#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
manifest_root=${STAGE1_MANIFEST_ROOT:-"$root/manifests/stage1_foundation_v5_formal_56x1_runtime_r5"}
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v5_output_56x1_menu_clean_r3"}
candidate_wave=${STAGE1_CANDIDATE_WAVE:-primary}
env_archive="$root/env/xonotic-capture-linux-x86_64-20260727.tar.gz"

for shard_index in $(seq 0 55); do
  printf \
    'SHARD_INDEX=%d STAGE1_CANDIDATE_WAVE=%q STAGE1_MANIFEST_ROOT=%q STAGE1_OUTPUT_ROOT=%q STAGE1_EXECUTION_MODE=resident STAGE1_MAX_OPERATIONAL_ATTEMPTS=2 STAGE1_RESUME_PASSES=3 STAGE1_GANG_NONFATAL_INCOMPLETE=1 STAGE1_DISTRIBUTED_BARRIER=0 XONOTIC_BUILD_ARCH=x86_64 XONOTIC_BUILD_TAG=capture-7e8310b0d0c1-x86_64 XONOTIC_ENV_ARCHIVE=%q XONOTIC_PIPELINES_PER_GPU=12 XONOTIC_LIVE_CONCURRENCY=12 XONOTIC_RENDER_CONCURRENCY=12 XONOTIC_RENDER_TIMEOUT_SECONDS=240 XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=120 XONOTIC_SDL_CONCURRENCY=12 XONOTIC_ENCODE_CONCURRENCY=4 XONOTIC_X264_THREADS=16 %q\n' \
    "$shard_index" \
    "$candidate_wave" \
    "$manifest_root" \
    "$output_root" \
    "$env_archive" \
    "$root/scripts/run_stage1_56x1_worker.sh"
done
