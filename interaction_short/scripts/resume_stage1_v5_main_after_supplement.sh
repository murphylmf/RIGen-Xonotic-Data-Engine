#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
supplement_log=${STAGE1_V5_SUPPLEMENT_LOG:-"$root/logs/20260727T192000Z_stage1_v5_supplemental_capacity.log"}
main_pid=${STAGE1_V5_MAIN_PID:-1192047}

while pgrep -f '[c]ertify_stage1_v5_supplemental_capacity.sh' >/dev/null; do
  sleep 30
done

grep -q '^supplemental_capacity_completed_utc=' "$supplement_log" || {
  echo "supplemental capacity did not complete: $supplement_log" >&2
  exit 2
}
[[ -r "/proc/$main_pid/stat" ]] || {
  echo "main path phase process no longer exists: $main_pid" >&2
  exit 2
}
state=$(ps -o stat= -p "$main_pid" | tr -d '[:space:]')
[[ "$state" == T* ]] || {
  echo "unexpected main path phase state: pid=$main_pid state=$state" >&2
  exit 2
}
kill -CONT "$main_pid"
echo "main_path_phase_resumed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
