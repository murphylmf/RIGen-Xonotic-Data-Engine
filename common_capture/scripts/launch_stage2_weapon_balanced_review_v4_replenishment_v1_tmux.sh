#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
session=${STAGE2_WB_V4_REP1_TMUX_SESSION:-stage2_weapon_balanced_review_v4_rep1_r1}
manifest_root="${workspace}/manifests/stage2_weapon_balanced_review_v4_replenishment_v1/shards"

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  exit 17
fi

created=0
for shard_index in 0 1 2 3; do
  tag=$(printf 'shard-%03d-of-%03d' "$shard_index" 4)
  [[ -s "${manifest_root}/${tag}.jsonl" ]] || continue
  command="cd $(printf '%q' "$workspace") && "
  command+="STAGE2_WB_V4_REP1_SHARD_INDEX=${shard_index} "
  command+="exec scripts/run_stage2_weapon_balanced_review_v4_replenishment_v1.sh"
  if (( created == 0 )); then
    tmux new-session -d -s "$session" -n "shard${shard_index}" "$command"
  else
    tmux new-window -t "$session" -n "shard${shard_index}" "$command"
  fi
  created=$((created + 1))
done

if (( created == 0 )); then
  echo "no non-empty replenishment shards" >&2
  exit 3
fi
tmux set-option -t "$session" remain-on-exit on
echo "started tmux session: $session (${created} non-empty shards)"
