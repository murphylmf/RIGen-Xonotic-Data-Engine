#!/usr/bin/env bash
set -euo pipefail

ROOT=./xonotic_capture
RUN_TAG="${STAGE1_POSTFILTER_RUN_TAG:-20260730_r1}"
DESTINATION="${STAGE1_POSTFILTER_DESTINATION:-${ROOT}/manifests/stage1_foundation_v5_accepted_postfiltered_r1_20260730}"
LOG_DIR="${ROOT}/logs/stage1_postfilter_manifest_${RUN_TAG}"
LOG_PATH="${LOG_DIR}/build.log"

mkdir -p "${LOG_DIR}"
cd "${ROOT}"

{
  echo "stage1_postfilter_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "destination=${DESTINATION}"
  "${ROOT}/scripts/cci_run.sh" \
    python "${ROOT}/scripts/build_stage1_postfilter_manifest.py" \
    --destination "${DESTINATION}" \
    "$@"
  status=$?
  echo "stage1_postfilter_finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "stage1_postfilter_exit_code=${status}"
  exit "${status}"
} 2>&1 | tee -a "${LOG_PATH}"
