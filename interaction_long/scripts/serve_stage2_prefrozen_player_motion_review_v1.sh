#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
port=${STAGE2_PM_V1_REVIEW_PORT:-18090}
log_root="${workspace}/logs/stage2_prefrozen_player_motion_review_v1"

cd "$workspace"
mkdir -p "$log_root"
exec > >(tee -a "${log_root}/gallery-${port}.log") 2>&1
exec python -u -m http.server "$port" \
  --bind 0.0.0.0 \
  --directory "$workspace"
