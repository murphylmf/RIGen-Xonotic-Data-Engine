#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)
output_root=${XONOTIC_DUEL_OUTPUT_ROOT:-$duel_root/outputs}

if (($# != 2)); then
  printf 'usage: %s DEMO_RUN_ID RENDER_RUN_ID\n' "$0" >&2
  exit 64
fi
demo_run_id=$1
render_run_id=$2
for value in "$demo_run_id" "$render_run_id"; do
  [[ "$value" =~ ^[A-Za-z0-9._-]+$ ]] || {
    printf 'run id contains unsupported characters: %s\n' "$value" >&2
    exit 64
  }
done

demo="$output_root/demos/$demo_run_id/$demo_run_id.dem"
action_qa="$output_root/demos/$demo_run_id/actions/processed/action_qa.json"
render_manifest="$output_root/renders/$render_run_id/manifest.json"
visibility_64="$output_root/visibility/${render_run_id}_64hz"
visibility_48="$output_root/visibility/${render_run_id}_48hz"
processed="$output_root/visibility/${render_run_id}_processed"
release="$output_root/releases/$render_run_id"

mkdir -p "$output_root/visibility" "$output_root/releases"

[[ -s "$demo" ]] || { printf 'missing demo: %s\n' "$demo" >&2; exit 66; }
[[ -s "$action_qa" ]] || { printf 'missing action QA: %s\n' "$action_qa" >&2; exit 66; }

"$script_dir/render_demo_clean_offline.sh" "$demo" "$render_run_id" 60
"$script_dir/visibility_prompt_v2/replay_visibility_labels.sh" \
  "$demo" "$visibility_64" 64
"$script_dir/visibility_prompt_v2/replay_visibility_labels.sh" \
  "$demo" "$visibility_48" 48

python "$script_dir/visibility_prompt_v2/build_visibility_episode.py" \
  --action-qa "$action_qa" \
  --visibility-tick-raw "$visibility_64/visibility_raw_64hz.tsv" \
  --visibility-render-raw "$visibility_48/visibility_raw_48hz.tsv" \
  --output-dir "$processed" \
  > "$processed.build.log"

jq '{all_pass, events, visibility_state_counts, gates}' \
  "$processed/episode_qa.json"

python "$script_dir/visibility_prompt_v2/build_rollout_release.py" \
  --render-manifest "$render_manifest" \
  --visibility "$processed/visibility_64hz.parquet" \
  --actions "$processed/model_actions_64hz.parquet" \
  --episode-qa "$processed/episode_qa.json" \
  --output-dir "$release" \
  > "$release.build.log"

jq '{training_ready, episode_id, counts, motion_label_distribution, visibility_phase_distribution, gates, build_wall_seconds}' \
  "$release/TRAINING_READY.json"
