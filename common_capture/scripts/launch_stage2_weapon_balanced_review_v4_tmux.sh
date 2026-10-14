#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
session=${STAGE2_WB_V4_TMUX_SESSION:-stage2_weapon_balanced_review_v4_r1}

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  exit 17
fi

for shard_index in 0 1 2 3; do
  command="cd $(printf '%q' "$workspace") && "
  command+="STAGE2_WB_V4_SHARD_INDEX=${shard_index} "
  command+="exec scripts/run_stage2_weapon_balanced_review_v4.sh"
  if (( shard_index == 0 )); then
    tmux new-session -d -s "$session" -n "shard${shard_index}" "$command"
  else
    tmux new-window -t "$session" -n "shard${shard_index}" "$command"
  fi
done

tmux set-option -t "$session" remain-on-exit on
echo "started tmux session: $session"
