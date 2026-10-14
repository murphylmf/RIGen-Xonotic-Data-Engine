#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export LONG60_RELEASE_ID=stage2_long60_multi_enemy_ref42_30h_20260828_v4
export LONG60_PRODUCTION_SCRIPT=pilot_scripts/long60_production_ref42_v4.py
export LONG60_BUILD_TAG=capture-e219ab01ae71-aarch64
export LONG60_DLC_JOB_NAME=${LONG60_DLC_JOB_NAME:-xonotic_long60_ref42_v4_30h_2x4_hold_0828}
exec "$script_dir/submit_long60_production_dlc_2x4.sh"
