#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
log_root="$workspace/logs/stage1_landed_review_20260729"
log="$log_root/build.log"

mkdir -p "$log_root"
cd "$workspace"
exec > >(tee -a "$log") 2>&1
echo "stage1_landed_review_build_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$workspace/scripts/cci_run.sh" \
  python "$workspace/scripts/build_stage1_landed_review.py" "$@"
echo "stage1_landed_review_build_finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
