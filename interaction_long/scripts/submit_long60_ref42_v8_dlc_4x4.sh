#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export LONG60_RELEASE_ID=stage2_long60_multi_enemy_ref42_multimap_hitscan_collision_camera_30h_20260829_v8
export LONG60_PRODUCTION_SCRIPT=pilot_scripts/long60_production_ref42_v8_collision_camera.py
export LONG60_BUILD_TAG=capture-3688c19201b0-aarch64
export LONG60_DLC_NODE_COUNT=4
export LONG60_DLC_JOB_NAME=${LONG60_DLC_JOB_NAME:-xonotic_long60_ref42_v8_collision_camera_30h_4x4_hold_0829}
exec "$script_dir/submit_long60_production_dlc_2x4.sh"
