#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
shard_count=32
shard_index=${SHARD_INDEX:-${JOB_COMPLETION_INDEX:-${SLURM_ARRAY_TASK_ID:-}}}

[[ -n "$shard_index" ]] || {
  echo "set SHARD_INDEX, JOB_COMPLETION_INDEX, or SLURM_ARRAY_TASK_ID" >&2
  exit 64
}
[[ "$shard_index" =~ ^[0-9]+$ ]] || {
  echo "invalid shard index: $shard_index" >&2
  exit 64
}
(( shard_index >= 0 && shard_index < shard_count )) || {
  echo "shard index out of range: $shard_index" >&2
  exit 64
}

tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")
manifest="$root/manifests/h200_pipeline_canary_v2/shards/$tag.jsonl"
metadata="$root/manifests/h200_pipeline_canary_v2/MANIFEST_METADATA.json"
output_root=${XONOTIC_CANARY_OUTPUT_ROOT:-"$root/h200_pipeline_canary"}
workers=${XONOTIC_RENDERERS_PER_GPU:-4}
encode_concurrency=${XONOTIC_ENCODE_CONCURRENCY:-4}
x264_threads=${XONOTIC_X264_THREADS:-16}
port_base=$((30000 + shard_index * 64))
task_id=${SLURM_JOB_ID:-${JOB_ID:-manual}}
tmp_root=${XONOTIC_CAPTURE_TMP:-${TMPDIR:-./tmp}/xonotic_capture/canary/${task_id}-${tag}}
log_root="$root/logs/h200_32_single_gpu_canary"
log="$log_root/$tag.log"

mkdir -p "$log_root" "$tmp_root"
export XONOTIC_CAPTURE_ROOT="$root"
export XONOTIC_CAPTURE_TMP="$tmp_root"
export CUDA_VISIBLE_DEVICES=0

exec > >(tee -a "$log") 2>&1
echo "canary_worker_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "shard_index=$shard_index"
echo "shard_count=$shard_count"
echo "manifest=$manifest"
echo "output_root=$output_root"
echo "tmp_root=$tmp_root"
echo "workers=$workers"
echo "encode_concurrency=$encode_concurrency"
echo "x264_threads=$x264_threads"
echo "port_base=$port_base"

exec "$script_dir/cci_run.sh" \
  python "$script_dir/run_capture_manifest_shard.py" run \
  --input-manifest "$manifest" \
  --manifest-metadata "$metadata" \
  --output-root "$output_root" \
  --shard-index "$shard_index" \
  --shard-count "$shard_count" \
  --workers "$workers" \
  --encode-concurrency "$encode_concurrency" \
  --x264-threads "$x264_threads" \
  --port-base "$port_base" \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 2
