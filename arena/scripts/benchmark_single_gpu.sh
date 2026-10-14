#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)
output_root=${XONOTIC_DUEL_OUTPUT_ROOT:-$duel_root/outputs}
benchmark_id=${1:-duel_v11_single_gpu_benchmark_$(date -u +%Y%m%dT%H%M%SZ)}
[[ "$benchmark_id" =~ ^[A-Za-z0-9._-]+$ ]] || {
  printf 'benchmark id contains unsupported characters: %s\n' "$benchmark_id" >&2
  exit 64
}

benchmark_root="$output_root/benchmarks/$benchmark_id"
[[ ! -e "$benchmark_root" ]] || {
  printf 'refusing to overwrite benchmark: %s\n' "$benchmark_root" >&2
  exit 73
}
mkdir -p "$benchmark_root"

compute_processes=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | sed '/^[[:space:]]*$/d')
if [[ -n "$compute_processes" ]]; then
  printf 'clean benchmark requires zero pre-existing GPU compute processes; found:\n%s\n' "$compute_processes" >&2
  exit 75
fi
nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader \
  > "$benchmark_root/gpu_before.csv"

demo_id="${benchmark_id}_demo"
render_id="${benchmark_id}_render"
demo="$output_root/demos/$demo_id/$demo_id.dem"
action_qa="$output_root/demos/$demo_id/actions/processed/action_qa.json"
render_manifest="$output_root/renders/$render_id/manifest.json"
visibility_64="$output_root/visibility/${render_id}_64hz"
visibility_48="$output_root/visibility/${render_id}_48hz"
processed="$output_root/visibility/${render_id}_processed"
release="$output_root/releases/$render_id"

now_ns() { date +%s%N; }
seconds_between() {
  awk -v start="$1" -v stop="$2" 'BEGIN {printf "%.6f", (stop-start)/1000000000}'
}

total_start=$(now_ns)
stage_start=$total_start
"$script_dir/record_demo_only.sh" 60 "$demo_id" 4 5 AggressiveClose \
  > "$benchmark_root/01_record.log"
stage_stop=$(now_ns)
record_seconds=$(seconds_between "$stage_start" "$stage_stop")

stage_start=$(now_ns)
"$script_dir/render_demo_clean_offline.sh" "$demo" "$render_id" 60 \
  > "$benchmark_root/02_render.log"
stage_stop=$(now_ns)
render_seconds=$(seconds_between "$stage_start" "$stage_stop")

stage_start=$(now_ns)
"$script_dir/visibility_prompt_v2/replay_visibility_labels.sh" "$demo" "$visibility_64" 64 \
  > "$benchmark_root/03_visibility_64hz.log"
stage_stop=$(now_ns)
visibility_64_seconds=$(seconds_between "$stage_start" "$stage_stop")

stage_start=$(now_ns)
"$script_dir/visibility_prompt_v2/replay_visibility_labels.sh" "$demo" "$visibility_48" 48 \
  > "$benchmark_root/04_visibility_48hz.log"
stage_stop=$(now_ns)
visibility_48_seconds=$(seconds_between "$stage_start" "$stage_stop")

stage_start=$(now_ns)
python "$script_dir/visibility_prompt_v2/build_visibility_episode.py" \
  --action-qa "$action_qa" \
  --visibility-tick-raw "$visibility_64/visibility_raw_64hz.tsv" \
  --visibility-render-raw "$visibility_48/visibility_raw_48hz.tsv" \
  --output-dir "$processed" \
  > "$benchmark_root/05_build_visibility.log"
stage_stop=$(now_ns)
build_visibility_seconds=$(seconds_between "$stage_start" "$stage_stop")

stage_start=$(now_ns)
python "$script_dir/visibility_prompt_v2/build_rollout_release.py" \
  --render-manifest "$render_manifest" \
  --visibility "$processed/visibility_64hz.parquet" \
  --actions "$processed/model_actions_64hz.parquet" \
  --episode-qa "$processed/episode_qa.json" \
  --output-dir "$release" \
  > "$benchmark_root/06_build_release.log"
stage_stop=$(now_ns)
build_release_seconds=$(seconds_between "$stage_start" "$stage_stop")
total_stop=$stage_stop
total_seconds=$(seconds_between "$total_start" "$total_stop")

jq -e '.all_pass' "$processed/episode_qa.json" >/dev/null
jq -e '.training_ready and (.gates | all)' "$release/TRAINING_READY.json" >/dev/null
processing_seconds=$(awk -v a="$render_seconds" -v b="$visibility_64_seconds" \
  -v c="$visibility_48_seconds" -v d="$build_visibility_seconds" \
  -v e="$build_release_seconds" 'BEGIN {printf "%.6f", a+b+c+d+e}')
throughput=$(awk -v total="$total_seconds" 'BEGIN {printf "%.6f", 60/total}')
data_minutes_per_hour=$(awk -v total="$total_seconds" 'BEGIN {printf "%.6f", 3600/total}')
eta_per_data_hour=$(awk -v total="$total_seconds" 'BEGIN {printf "%.6f", total/60}')
rollouts_per_hour=$(awk -v total="$total_seconds" 'BEGIN {printf "%.6f", 3600/total}')
overlap_projection=$(awk -v record="$record_seconds" -v process="$processing_seconds" \
  'BEGIN {b=(record>process?record:process); printf "%.6f", 60/b}')

nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader \
  > "$benchmark_root/gpu_after.csv"
jq -n \
  --arg benchmark_id "$benchmark_id" \
  --arg demo "$demo" \
  --arg release "$release" \
  --arg gpu "$(head -n 1 "$benchmark_root/gpu_before.csv")" \
  --arg record "$record_seconds" \
  --arg render "$render_seconds" \
  --arg visibility64 "$visibility_64_seconds" \
  --arg visibility48 "$visibility_48_seconds" \
  --arg build_visibility "$build_visibility_seconds" \
  --arg build_release "$build_release_seconds" \
  --arg processing "$processing_seconds" \
  --arg total "$total_seconds" \
  --arg throughput "$throughput" \
  --arg data_minutes_per_hour "$data_minutes_per_hour" \
  --arg eta_per_data_hour "$eta_per_data_hour" \
  --arg rollouts_per_hour "$rollouts_per_hour" \
  --arg overlap_projection "$overlap_projection" \
  '{
    schema_version: "xonotic-duel-v11-clean-single-gpu-benchmark-v1",
    benchmark_id: $benchmark_id,
    clean_precondition: {preexisting_gpu_compute_processes: 0, gpu: $gpu},
    artifact: {demo: $demo, release: $release, unique_data_seconds: 60},
    wall_seconds: {
      record_and_action_qa: ($record|tonumber),
      offline_render_and_encode: ($render|tonumber),
      visibility_replay_64hz: ($visibility64|tonumber),
      visibility_replay_48hz: ($visibility48|tonumber),
      build_visibility: ($build_visibility|tonumber),
      build_rollout_and_15_clips: ($build_release|tonumber),
      processing_after_record: ($processing|tonumber),
      sequential_end_to_end: ($total|tonumber)
    },
    measured_sequential: {
      video_hours_per_wall_hour: ($throughput|tonumber),
      data_minutes_per_wall_hour: ($data_minutes_per_hour|tonumber),
      sixty_second_rollouts_per_wall_hour: ($rollouts_per_hour|tonumber),
      eta_wall_hours_per_data_hour: ($eta_per_data_hour|tonumber)
    },
    projected_two_stage_overlap: {
      policy: "one recorder overlapped with one render-label-package worker; not an independent measured concurrency result",
      video_hours_per_wall_hour: ($overlap_projection|tonumber)
    },
    gates: {episode_visibility_all_pass: true, release_training_ready: true}
  }' > "$benchmark_root/BENCHMARK.json"

jq . "$benchmark_root/BENCHMARK.json"
