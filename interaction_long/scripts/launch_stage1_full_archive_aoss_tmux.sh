#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
SESSION="${STAGE1_AOSS_TMUX_SESSION:-xonotic_stage1_aoss_full_r2}"
THREADS="${THREADS:-30}"
STAGING_WORKERS="${STAGING_WORKERS:-32}"
PLAN_ONLY="${AOSS_PLAN_ONLY:-0}"
STAGE_ONLY="${AOSS_STAGE_ONLY:-0}"
RUN_TAG="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${ROOT}/logs/stage1_aoss_full_${RUN_TAG}"
LOG_PATH="${LOG_DIR}/upload.log"
STATUS_PATH="${LOG_DIR}/status"

if tmux has-session -t "${SESSION}" 2>/dev/null; then
  echo "tmux session already exists: ${SESSION}" >&2
  echo "attach with: tmux attach -t ${SESSION}" >&2
  exit 1
fi
mkdir -p "${LOG_DIR}"

tmux new-session -d -s "${SESSION}" \
  "/bin/bash -c 'cd \"${ROOT}\" || exit 1
   set -o pipefail
   echo started_utc=\$(date -u +%Y-%m-%dT%H:%M:%SZ) | tee -a \"${LOG_PATH}\"
   THREADS=\"${THREADS}\" STAGING_WORKERS=\"${STAGING_WORKERS}\" \
     AOSS_PLAN_ONLY=\"${PLAN_ONLY}\" AOSS_STAGE_ONLY=\"${STAGE_ONLY}\" \
     \"${SCRIPT_DIR}/upload_stage1_full_archive_to_aoss.sh\" \
     2>&1 | tee -a \"${LOG_PATH}\"
   code=\${PIPESTATUS[0]}
   echo finished_utc=\$(date -u +%Y-%m-%dT%H:%M:%SZ) | tee -a \"${LOG_PATH}\"
   echo exit_code=\${code} | tee -a \"${LOG_PATH}\"
   if (( code == 0 )); then
     status=SUCCESS
   else
     status=FAILED
   fi
   echo upload_status=\${status} | tee -a \"${LOG_PATH}\"
   printf \"upload_status=%s\\nexit_code=%s\\n\" \
     \"\${status}\" \"\${code}\" > \"${STATUS_PATH}\"
   exit \"\${code}\"'"


tmux set-option -w -t "${SESSION}:0" remain-on-exit on

echo "tmux_session=${SESSION}"
echo "log=${LOG_PATH}"
echo "status=${STATUS_PATH}"
echo "attach=tmux attach -t ${SESSION}"
echo "follow=tail -f ${LOG_PATH}"
