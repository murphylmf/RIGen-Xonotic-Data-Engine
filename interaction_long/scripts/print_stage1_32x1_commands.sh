#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
manifest_root=${STAGE1_MANIFEST_ROOT:-"$root/manifests/stage1_foundation_v5_formal"}
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v5_output"}
candidate_wave=${STAGE1_CANDIDATE_WAVE:-primary}

for shard_index in $(seq 0 31); do
  printf \
    'SHARD_INDEX=%d STAGE1_CANDIDATE_WAVE=%q STAGE1_MANIFEST_ROOT=%q STAGE1_OUTPUT_ROOT=%q STAGE1_EXECUTION_MODE=resident STAGE1_MAX_OPERATIONAL_ATTEMPTS=2 XONOTIC_BUILD_ARCH=x86_64 XONOTIC_BUILD_TAG=capture-7e8310b0d0c1-x86_64 XONOTIC_PIPELINES_PER_GPU=12 XONOTIC_LIVE_CONCURRENCY=12 XONOTIC_RENDER_CONCURRENCY=12 XONOTIC_RENDER_TIMEOUT_SECONDS=240 XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=120 XONOTIC_SDL_CONCURRENCY=12 XONOTIC_ENCODE_CONCURRENCY=4 XONOTIC_X264_THREADS=16 %q\n' \
    "$shard_index" \
    "$candidate_wave" \
    "$manifest_root" \
    "$output_root" \
    "$root/scripts/run_stage1_32x1_worker.sh"
done
