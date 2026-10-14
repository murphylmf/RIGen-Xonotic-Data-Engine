#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
port=${STAGE1_LANDED_REVIEW_PORT:-18084}
log_root="$workspace/logs/stage1_landed_review_20260729"
log="$log_root/server-$port.log"

mkdir -p "$log_root"
cd "$workspace"
exec > >(tee -a "$log") 2>&1
echo "stage1_landed_review_server_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "stage1_landed_review_url=http://127.0.0.1:$port/stage1_landed_review_100_20260729/"
exec python -m http.server "$port" \
  --bind 0.0.0.0 \
  --directory "$workspace"
