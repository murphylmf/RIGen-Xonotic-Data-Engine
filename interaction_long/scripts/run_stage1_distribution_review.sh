#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
output_root=${STAGE1_OUTPUT_ROOT:-"$root/stage1_foundation_v1_output"}
candidate_wave=${STAGE1_CANDIDATE_WAVE:-primary}
episodes_per_shard=${STAGE1_REVIEW_EPISODES_PER_SHARD:-4}
shard_start=${STAGE1_REVIEW_SHARD_START:-0}
shard_end=${STAGE1_REVIEW_SHARD_END:-31}
coordinator_log=${STAGE1_REVIEW_LOG:-"$root/logs/stage1_distribution_review_20260727.log"}

for value in "$episodes_per_shard" "$shard_start" "$shard_end"; do
  [[ "$value" =~ ^[0-9]+$ ]] || {
    echo "review limits must be non-negative integers: $value" >&2
    exit 64
  }
done
(( episodes_per_shard > 0 )) || {
  echo "STAGE1_REVIEW_EPISODES_PER_SHARD must be positive" >&2
  exit 64
}
(( shard_start <= shard_end && shard_end < 32 )) || {
  echo "invalid review shard range: ${shard_start}..${shard_end}" >&2
  exit 64
}
[[ "$candidate_wave" == primary || "$candidate_wave" == replenishment ]] || {
  echo "invalid STAGE1_CANDIDATE_WAVE: $candidate_wave" >&2
  exit 64
}

mkdir -p "$(dirname -- "$coordinator_log")"
exec > >(tee -a "$coordinator_log") 2>&1

echo "stage1_distribution_review_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "output_root=$output_root"
echo "candidate_wave=$candidate_wave"
echo "episodes_per_shard=$episodes_per_shard"
echo "shard_range=${shard_start}..${shard_end}"

for shard_index in $(seq "$shard_start" "$shard_end"); do
  echo "__STAGE1_REVIEW_SHARD_START__:${shard_index}:$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if SHARD_INDEX="$shard_index" \
    STAGE1_EPISODE_LIMIT="$episodes_per_shard" \
    STAGE1_CANDIDATE_WAVE="$candidate_wave" \
    STAGE1_OUTPUT_ROOT="$output_root" \
    "$script_dir/run_stage1_32x1_worker.sh"; then
    worker_rc=0
  else
    worker_rc=$?
  fi
  echo "__STAGE1_REVIEW_SHARD_DONE__:${shard_index}:${worker_rc}:$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if (( worker_rc != 0 )); then
    echo "__STAGE1_DISTRIBUTION_REVIEW_CAPTURE_DONE__:${worker_rc}"
    exit "$worker_rc"
  fi
done

echo "__STAGE1_DISTRIBUTION_REVIEW_CAPTURE_DONE__:0"
echo "stage1_distribution_review_finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
