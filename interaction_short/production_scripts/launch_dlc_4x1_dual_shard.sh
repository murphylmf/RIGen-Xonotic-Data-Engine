#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
physical_world=${WORLD_SIZE:-}
physical_rank=${RANK:-}

[[ "$physical_world" == 4 ]] || {
  echo "expected four one-GPU DLC Pods, got WORLD_SIZE=${physical_world:-unset}" >&2
  exit 78
}
[[ "$physical_rank" =~ ^[0-3]$ ]] || {
  echo "expected physical RANK in [0,3], got ${physical_rank:-unset}" >&2
  exit 64
}

for shard_offset in 0 4; do
  logical_shard=$((10#$physical_rank + shard_offset))
  echo "stage2_motion_physical_rank=$physical_rank logical_shard=$logical_shard/8"
  RANK=$logical_shard \
    WORLD_SIZE=8 \
    STAGE2_REQUIRED_SHARDS=8 \
    bash "$script_dir/launch_dlc_8x1.sh"
done
