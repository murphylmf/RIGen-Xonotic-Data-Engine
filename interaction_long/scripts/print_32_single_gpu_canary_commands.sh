#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
workers=${XONOTIC_RENDERERS_PER_GPU:-4}
encode_concurrency=${XONOTIC_ENCODE_CONCURRENCY:-4}
x264_threads=${XONOTIC_X264_THREADS:-16}
output_root=${XONOTIC_CANARY_OUTPUT_ROOT:-"$root/h200_pipeline_canary"}

for shard_index in $(seq 0 31); do
  printf \
    'SHARD_INDEX=%d CUDA_VISIBLE_DEVICES=0 XONOTIC_RENDERERS_PER_GPU=%q XONOTIC_ENCODE_CONCURRENCY=%q XONOTIC_X264_THREADS=%q XONOTIC_CANARY_OUTPUT_ROOT=%q %q\n' \
    "$shard_index" \
    "$workers" \
    "$encode_concurrency" \
    "$x264_threads" \
    "$output_root" \
    "$root/scripts/run_32_single_gpu_canary_worker.sh"
done
