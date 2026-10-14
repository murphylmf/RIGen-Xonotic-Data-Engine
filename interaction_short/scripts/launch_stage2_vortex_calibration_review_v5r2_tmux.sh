#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
session=${STAGE2_VORTEX_V5R2_TMUX_SESSION:-stage2_vortex_calibration_review_v5r2_r1}

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  exit 17
fi

for shard_index in 0 1 2 3; do
  command="cd $(printf '%q' "$workspace") && "
  command+="STAGE2_VORTEX_V5R2_SHARD_INDEX=${shard_index} "
  command+="exec scripts/run_stage2_vortex_calibration_review_v5r2.sh"
  if (( shard_index == 0 )); then
    tmux new-session -d -s "$session" -n "shard0" "$command"
  else
    tmux new-window -t "$session" -n "shard${shard_index}" "$command"
  fi
done
tmux set-option -t "$session" remain-on-exit on
echo "started tmux session: $session (4 shards)"
