#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export STAGE2_REQUIRED_SHARDS=${STAGE2_REQUIRED_SHARDS:-12}
exec "$script_dir/launch_dlc_8x1.sh"
