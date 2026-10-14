#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
session=${STAGE2_PMR_V2_TMUX_SESSION:-stage2_prefrozen_player_motion_replenishment_v2}

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  exit 64
fi

for shard_index in 0 1 2 3; do
  window=$(printf 'shard%02d' "$shard_index")
  command=(
    env
    "XONOTIC_CAPTURE_ROOT=${workspace}"
    "STAGE2_PMR_V2_SHARD_INDEX=${shard_index}"
    "${workspace}/scripts/run_stage2_prefrozen_player_motion_replenishment_v2.sh"
  )
  if [[ "$shard_index" == 0 ]]; then
    tmux new-session -d -s "$session" -n "$window" "${command[@]}"
    tmux set-option -t "$session" remain-on-exit on
  else
    tmux new-window -t "$session" -n "$window" "${command[@]}"
  fi
done

echo "started tmux session: $session"
echo "attach: tmux attach -t $session"
