#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DETECTED_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
SOURCE_ROOT="${XONOTIC_ROOT:-${DETECTED_ROOT}}"
SOURCE_PARENT="$(dirname "${SOURCE_ROOT}")"
STAGING_ROOT="${STAGE1_AOSS_STAGING_ROOT:-${SOURCE_PARENT}/xonotic_stage1_full_archive_r2}"
TARGET_PREFIX="${STAGE1_AOSS_TARGET_PREFIX:-limengfei/xonotic_data/}"
THREADS="${THREADS:-30}"
STAGING_WORKERS="${STAGING_WORKERS:-32}"
PLAN_ONLY="${AOSS_PLAN_ONLY:-0}"
STAGE_ONLY="${AOSS_STAGE_ONLY:-0}"

if [[ -n "${AOSS_UPLOADER:-}" ]]; then
  UPLOADER="${AOSS_UPLOADER}"
elif [[ -x "${SOURCE_PARENT}/aoss_up_foraliyun.sh" ]]; then
  UPLOADER="${SOURCE_PARENT}/aoss_up_foraliyun.sh"
elif [[ -x ./limengfei/aoss_up_foraliyun.sh ]]; then
  UPLOADER=./limengfei/aoss_up_foraliyun.sh
elif [[ -x ./aoss_up_foraliyun.sh ]]; then
  UPLOADER=./aoss_up_foraliyun.sh
else
  echo "cannot locate aoss_up_foraliyun.sh" >&2
  exit 1
fi

if [[ "${TARGET_PREFIX}" != "limengfei/xonotic_data/" ]]; then
  echo "refusing unexpected target prefix: ${TARGET_PREFIX}" >&2
  exit 2
fi
if ! [[ "${THREADS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "THREADS must be a positive integer" >&2
  exit 2
fi
if ! [[ "${STAGING_WORKERS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "STAGING_WORKERS must be a positive integer" >&2
  exit 2
fi

echo "source_root=${SOURCE_ROOT}"
echo "staging_root=${STAGING_ROOT}"
echo "uploader=${UPLOADER}"
echo "target_prefix=${TARGET_PREFIX}"
echo "upload_threads=${THREADS}"

stage_args=(
  --source-root "${SOURCE_ROOT}"
  --staging-root "${STAGING_ROOT}"
  --workers "${STAGING_WORKERS}"
)
if [[ "${PLAN_ONLY}" == 1 ]]; then
  stage_args+=(--plan-only)
fi
python "${SCRIPT_DIR}/prepare_stage1_aoss_staging.py" "${stage_args[@]}"

if [[ "${PLAN_ONLY}" == 1 ]]; then
  echo "plan-only complete; no staging or upload was performed"
  exit 0
fi
if [[ "${STAGE_ONLY}" == 1 ]]; then
  echo "stage-only complete; upload was not started"
  exit 0
fi
if [[ ! -x ./gexingtong/ads-cli ]]; then
  echo "expected ads-cli missing: ./gexingtong/ads-cli" >&2
  exit 1
fi
if ! grep -q 'AOSS_COMMAND' "${UPLOADER}"; then
  echo "uploader lacks resumable AOSS_COMMAND support" >&2
  exit 1
fi

echo "starting resumable AOSS sync"
THREADS="${THREADS}" AOSS_COMMAND=sync \
  "${UPLOADER}" "${STAGING_ROOT}/" "${TARGET_PREFIX}"
echo "AOSS Stage-1 full archive sync completed"
