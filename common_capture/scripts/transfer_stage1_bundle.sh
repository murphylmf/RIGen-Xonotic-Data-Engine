#!/usr/bin/env bash
set -euo pipefail

if (( $# < 2 || $# > 4 )); then
  echo "usage: $0 SOURCE_ROOT DESTINATION_ROOT [core|full] [JOBS]" >&2
  exit 2
fi

SOURCE_ROOT="${1%/}"
DESTINATION_ROOT="${2%/}"
PROFILE="${3:-core}"
JOBS="${4:-8}"
BUNDLE_REL="manifests/stage1_foundation_v5_transfer_bundle_r2_20260730"
BUNDLE="${SOURCE_ROOT}/${BUNDLE_REL}"
RUN_TAG="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_ROOT="${SOURCE_ROOT}/logs/stage1_transfer_${RUN_TAG}"

if [[ "${PROFILE}" != core && "${PROFILE}" != full ]]; then
  echo "profile must be core or full" >&2
  exit 2
fi
if ! [[ "${JOBS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "jobs must be a positive integer" >&2
  exit 2
fi
if [[ ! -f "${BUNDLE}/TRANSFER_REPORT.json" ]]; then
  echo "transfer bundle not found: ${BUNDLE}" >&2
  exit 1
fi

mkdir -p "${DESTINATION_ROOT}" "${LOG_ROOT}"

echo "Copying transfer control bundle"
rsync -a --partial \
  "${BUNDLE}/" \
  "${DESTINATION_ROOT}/${BUNDLE_REL}/"

echo "Copying Stage-1 metadata"
rsync -a --partial --partial-dir=.stage1-rsync-partial \
  --files-from="${BUNDLE}/metadata_files.txt" \
  "${SOURCE_ROOT}/" "${DESTINATION_ROOT}/" \
  >"${LOG_ROOT}/metadata.log" 2>&1

echo "Copying referenced Stage-1 path certificates"
rsync -a --partial --partial-dir=.stage1-rsync-partial \
  --files-from="${BUNDLE}/certificate_files.txt" \
  "${SOURCE_ROOT}/" "${DESTINATION_ROOT}/" \
  >"${LOG_ROOT}/certificates.log" 2>&1

export SOURCE_ROOT DESTINATION_ROOT LOG_ROOT
run_profile() {
  local profile="$1"
  export profile
  find "${BUNDLE}/shards/${profile}" \
    -maxdepth 1 -type f -name 'shard-*.txt' -print0 \
    | sort -z \
    | xargs -0 -r -n 1 -P "${JOBS}" bash -c '
        list="$1"
        name="$(basename "${list}" .txt)"
        rsync -a --partial --partial-dir=.stage1-rsync-partial \
          --files-from="${list}" \
          "${SOURCE_ROOT}/" "${DESTINATION_ROOT}/" \
          >"${LOG_ROOT}/${profile}_${name}.log" 2>&1
      ' _
}

echo "Copying Stage-1 core with ${JOBS} parallel rsync workers"
run_profile core

if [[ "${PROFILE}" == full ]]; then
  echo "Copying optional Stage-1 provenance with ${JOBS} workers"
  run_profile provenance
fi

echo "Stage-1 ${PROFILE} transfer completed"
echo "logs=${LOG_ROOT}"
