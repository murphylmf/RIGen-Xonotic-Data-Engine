#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)
output_root=${XONOTIC_DUEL_OUTPUT_ROOT:-$duel_root/outputs}
concurrency=${1:-8}
benchmark_id=${2:-duel_v11_c${concurrency}_fullchain_$(date -u +%Y%m%dT%H%M%SZ)}
duration=60

case "$concurrency" in
  1|2|4|8) ;;
  *) printf 'concurrency must be one of 1, 2, 4, or 8\n' >&2; exit 64 ;;
esac
[[ "$benchmark_id" =~ ^[A-Za-z0-9._-]+$ ]] || {
  printf 'benchmark id contains unsupported characters: %s\n' "$benchmark_id" >&2
  exit 64
}

benchmark_root="$output_root/benchmarks/$benchmark_id"
[[ ! -e "$benchmark_root" ]] || {
  printf 'refusing to overwrite benchmark: %s\n' "$benchmark_root" >&2
  exit 73
}
mkdir -p "$benchmark_root/logs"

compute_processes=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | sed '/^[[:space:]]*$/d')
if [[ -n "$compute_processes" ]]; then
  printf 'clean benchmark requires zero pre-existing GPU compute processes; found:\n%s\n' "$compute_processes" >&2
  exit 75
fi

scratch_root=${XONOTIC_DUEL_SCRATCH_ROOT:-$duel_root/scratch}
mkdir -p "$scratch_root"
scratch_root=$(cd -- "$scratch_root" && pwd -P)
[[ -w "$scratch_root" ]] || { printf 'scratch root is not writable: %s\n' "$scratch_root" >&2; exit 66; }

nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader \
  > "$benchmark_root/gpu_before.csv"
df -Pk "$scratch_root" > "$benchmark_root/scratch_before.txt"
nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw \
  --format=csv,noheader,nounits -l 1 > "$benchmark_root/gpu_samples.csv" 2>&1 &
gpu_monitor_pid=$!
cleanup_monitor() {
  if [[ -n "${gpu_monitor_pid:-}" ]]; then
    kill "$gpu_monitor_pid" 2>/dev/null || true
    wait "$gpu_monitor_pid" 2>/dev/null || true
    gpu_monitor_pid=""
  fi
}
trap cleanup_monitor EXIT

skills_a=(3 4 5 6 3 6 4 5)
skills_b=(4 5 6 3 6 4 6 3)
pov_policies=(
  AggressiveClose LongRangeEvasive AggressiveClose LongRangeEvasive
  AggressiveClose LongRangeEvasive AggressiveClose LongRangeEvasive
)
demo_ids=()
render_ids=()
release_paths=()

record_start_ns=$(date +%s%N)
record_pids=()
for ((index=0; index<concurrency; ++index)); do
  demo_id="${benchmark_id}_c${concurrency}_e${index}_demo"
  render_id="${benchmark_id}_c${concurrency}_e${index}_render"
  demo_ids+=("$demo_id")
  render_ids+=("$render_id")
  release_paths+=("$output_root/releases/$render_id")
  XONOTIC_DUEL_SETUP_SECONDS=20 \
    "$script_dir/record_demo_only.sh" "$duration" "$demo_id" \
      "${skills_a[$index]}" "${skills_b[$index]}" "${pov_policies[$index]}" \
      > "$benchmark_root/logs/${demo_id}.log" 2>&1 &
  record_pids+=("$!")
done

failed=0
for pid in "${record_pids[@]}"; do
  if ! wait "$pid"; then failed=1; fi
done
record_stop_ns=$(date +%s%N)
if ((failed)); then
  printf 'one or more concurrent record workers failed\n' >&2
  exit 70
fi

process_start_ns=$(date +%s%N)
process_pids=()
for ((index=0; index<concurrency; ++index)); do
  XONOTIC_DUEL_SCRATCH_ROOT="$scratch_root" \
  XONOTIC_DUEL_VISIBILITY_SCRATCH_ROOT="$scratch_root" \
    bash "$script_dir/process_recorded_episode.sh" \
      "${demo_ids[$index]}" "${render_ids[$index]}" \
      > "$benchmark_root/logs/${render_ids[$index]}.log" 2>&1 &
  process_pids+=("$!")
done

failed=0
for pid in "${process_pids[@]}"; do
  if ! wait "$pid"; then failed=1; fi
done
process_stop_ns=$(date +%s%N)
cleanup_monitor
if ((failed)); then
  printf 'one or more concurrent full-chain processing workers failed\n' >&2
  exit 70
fi

for release in "${release_paths[@]}"; do
  jq -e '.training_ready and (.gates | all)' "$release/TRAINING_READY.json" >/dev/null
done

seconds_between() {
  awk -v start="$1" -v stop="$2" 'BEGIN {printf "%.6f", (stop-start)/1000000000}'
}
record_seconds=$(seconds_between "$record_start_ns" "$record_stop_ns")
process_seconds=$(seconds_between "$process_start_ns" "$process_stop_ns")
total_seconds=$(seconds_between "$record_start_ns" "$process_stop_ns")
accepted_seconds=$((concurrency * duration))
record_rate=$(awk -v data="$accepted_seconds" -v wall="$record_seconds" 'BEGIN {printf "%.6f", data/wall}')
process_rate=$(awk -v data="$accepted_seconds" -v wall="$process_seconds" 'BEGIN {printf "%.6f", data/wall}')
sequential_rate=$(awk -v data="$accepted_seconds" -v wall="$total_seconds" 'BEGIN {printf "%.6f", data/wall}')
steady_state_rate=$(awk -v data="$accepted_seconds" -v a="$record_seconds" -v b="$process_seconds" \
  'BEGIN {wall=(a>b?a:b); printf "%.6f", data/wall}')
sequential_eta=$(awk -v rate="$sequential_rate" 'BEGIN {printf "%.6f", 1/rate}')
steady_state_eta=$(awk -v rate="$steady_state_rate" 'BEGIN {printf "%.6f", 1/rate}')

read -r gpu_samples gpu_util_mean gpu_util_max gpu_memory_mean gpu_memory_max gpu_power_mean gpu_power_max < <(
  awk -F, '
    /^[[:space:]]*[0-9]/ {
      for(i=1;i<=3;i++) gsub(/[[:space:]]/, "", $i)
      u=$1+0; m=$2+0; p=$3+0
      n++; su+=u; sm+=m; sp+=p
      if(u>mu)mu=u; if(m>mm)mm=m; if(p>mp)mp=p
    }
    END {
      if(n) printf "%d %.6f %.6f %.6f %.6f %.6f %.6f\n", n, su/n, mu, sm/n, mm, sp/n, mp
      else printf "0 0 0 0 0 0 0\n"
    }
  ' "$benchmark_root/gpu_samples.csv"
)

releases_json=$(printf '%s\n' "${release_paths[@]}" | jq -R . | jq -s .)
motion_json=$(jq -s '[.[].motion_label_distribution | to_entries[]] | group_by(.key) | map({key:.[0].key,value:(map(.value)|add)}) | from_entries' \
  "${release_paths[@]/%//TRAINING_READY.json}")
visibility_json=$(jq -s '[.[].visibility_phase_distribution | to_entries[]] | group_by(.key) | map({key:.[0].key,value:(map(.value)|add)}) | from_entries' \
  "${release_paths[@]/%//TRAINING_READY.json}")

df -Pk "$scratch_root" > "$benchmark_root/scratch_after.txt"
nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader \
  > "$benchmark_root/gpu_after.csv"

jq -n \
  --arg benchmark_id "$benchmark_id" \
  --arg gpu "$(head -n 1 "$benchmark_root/gpu_before.csv")" \
  --arg scratch_root "$scratch_root" \
  --arg record "$record_seconds" \
  --arg process "$process_seconds" \
  --arg total "$total_seconds" \
  --arg record_rate "$record_rate" \
  --arg process_rate "$process_rate" \
  --arg sequential_rate "$sequential_rate" \
  --arg steady_state_rate "$steady_state_rate" \
  --arg sequential_eta "$sequential_eta" \
  --arg steady_state_eta "$steady_state_eta" \
  --argjson concurrency "$concurrency" \
  --argjson duration "$duration" \
  --argjson accepted_seconds "$accepted_seconds" \
  --argjson gpu_samples "$gpu_samples" \
  --arg gpu_util_mean "$gpu_util_mean" \
  --arg gpu_util_max "$gpu_util_max" \
  --arg gpu_memory_mean "$gpu_memory_mean" \
  --arg gpu_memory_max "$gpu_memory_max" \
  --arg gpu_power_mean "$gpu_power_mean" \
  --arg gpu_power_max "$gpu_power_max" \
  --argjson releases "$releases_json" \
  --argjson motion "$motion_json" \
  --argjson visibility "$visibility_json" \
  '{
    schema_version: "xonotic-duel-v11-concurrent-fullchain-benchmark-v1",
    benchmark_id: $benchmark_id,
    clean_precondition: {preexisting_gpu_compute_processes: 0, gpu: $gpu},
    topology: {
      concurrency: $concurrency,
      episode_duration_seconds: $duration,
      stages: "concurrent record batch, then concurrent render plus 64/48 Hz visibility plus prompt and clip packaging batch",
      scratch_root: $scratch_root
    },
    accepted: {
      episodes: $concurrency,
      unique_video_seconds: $accepted_seconds,
      all_releases_training_ready: true,
      releases: $releases
    },
    wall_seconds: {
      concurrent_record_batch: ($record|tonumber),
      concurrent_full_processing_batch: ($process|tonumber),
      observed_sequential_stages_total: ($total|tonumber)
    },
    measured_video_hours_per_wall_hour: {
      record_stage_capacity: ($record_rate|tonumber),
      processing_stage_capacity: ($process_rate|tonumber),
      observed_end_to_end_sequential_stages: ($sequential_rate|tonumber)
    },
    eta_wall_hours_per_data_hour: {
      observed_end_to_end_sequential_stages: ($sequential_eta|tonumber)
    },
    projected_cross_batch_overlap: {
      policy: "record batch N+1 overlaps processing batch N; derived from independently measured concurrent stage walls, not separately timed overlap",
      video_hours_per_wall_hour: ($steady_state_rate|tonumber),
      eta_wall_hours_per_data_hour: ($steady_state_eta|tonumber)
    },
    gpu: {
      samples: $gpu_samples,
      utilization_percent_mean: ($gpu_util_mean|tonumber),
      utilization_percent_max: ($gpu_util_max|tonumber),
      memory_used_mib_mean: ($gpu_memory_mean|tonumber),
      memory_used_mib_max: ($gpu_memory_max|tonumber),
      power_w_mean: ($gpu_power_mean|tonumber),
      power_w_max: ($gpu_power_max|tonumber)
    },
    prompt_distribution: {motion: $motion, visibility: $visibility},
    gates: {
      all_eight_rollouts_training_ready: ($concurrency == 8),
      sixty_second_rollouts: true,
      fifteen_clips_per_rollout: true,
      stage1_stage2_preservation_checks: true
    }
  }' > "$benchmark_root/BENCHMARK.json"

sha256sum -c "$duel_root/protected/STAGE12_BEFORE.sha256" > "$benchmark_root/stage12_final_check.txt"
sha256sum -c "$duel_root/protected/EXISTING_PIPELINES_BEFORE.sha256" > "$benchmark_root/existing_pipelines_final_check.txt"
sha256sum -c "$duel_root/protected/DUEL_V5_V6_V7_BEFORE.sha256" > "$benchmark_root/prior_duel_final_check.txt"
sha256sum "$benchmark_root/BENCHMARK.json" > "$benchmark_root/SHA256SUMS"

jq . "$benchmark_root/BENCHMARK.json"
