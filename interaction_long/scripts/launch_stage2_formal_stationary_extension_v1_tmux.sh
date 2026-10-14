#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
session=${STAGE2_FORMAL_STATIONARY_EXTENSION_V1_TMUX_SESSION:-stage2_formal_stationary_extension_v1_r1}

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  exit 17
fi

command="cd $(printf '%q' "$workspace") && "
command+="exec scripts/run_stage2_formal_stationary_extension_v1.sh"
tmux new-session -d -s "$session" -n canary "$command"
tmux set-option -t "$session" remain-on-exit on
echo "started tmux session: $session"
