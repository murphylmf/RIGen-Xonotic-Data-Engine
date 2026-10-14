#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
session=${STAGE2_WB_V4_REP3_TMUX_SESSION:-stage2_weapon_balanced_review_v4_rep3_r1}

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  exit 17
fi
command="cd $(printf '%q' "$workspace") && "
command+="exec scripts/run_stage2_weapon_balanced_review_v4_replenishment_v3.sh"
tmux new-session -d -s "$session" -n shard0 "$command"
tmux set-option -t "$session" remain-on-exit on
echo "started tmux session: $session"
