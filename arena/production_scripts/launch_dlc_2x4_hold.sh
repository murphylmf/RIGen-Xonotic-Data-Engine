#!/usr/bin/env bash
set -uo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)
run_id=${XONOTIC_DUEL_PRODUCTION_RUN_ID:-}
total_episodes=${XONOTIC_DUEL_TOTAL_EPISODES:-}
physical_world=${WORLD_SIZE:-}
physical_rank=${RANK:-}
expected_nodes=${XONOTIC_DUEL_EXPECTED_NODES:-2}
gpus_per_node=${XONOTIC_DUEL_GPUS_PER_NODE:-4}
lanes_per_gpu=${XONOTIC_DUEL_LANES_PER_GPU:-2}
heartbeat_seconds=${XONOTIC_DUEL_HEARTBEAT_SECONDS:-60}
retry_base_seconds=${XONOTIC_DUEL_RETRY_BASE_SECONDS:-30}
retry_max_seconds=${XONOTIC_DUEL_RETRY_MAX_SECONDS:-300}
production_base=${XONOTIC_DUEL_PRODUCTION_ROOT:-$duel_root/outputs/production_2x4}
scratch_base=${XONOTIC_DUEL_SCRATCH_BASE:-./tmp/xonotic-duel-v11-production}
node_preflight_only=${XONOTIC_DUEL_NODE_PREFLIGHT_ONLY:-0}

hold_node() {
  local reason=$1
  printf 'duel_v11_node_hold rank=%s reason=%s utc=%s\n' "${physical_rank:-unset}" "$reason" "$(date -u +%FT%TZ)" >&2
  while true; do
    printf 'duel_v11_node_hold_heartbeat rank=%s reason=%s utc=%s\n' "${physical_rank:-unset}" "$reason" "$(date -u +%FT%TZ)"
    sleep "$heartbeat_seconds"
  done
}

[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || hold_node invalid_run_id
for value_name in total_episodes physical_world physical_rank expected_nodes gpus_per_node lanes_per_gpu; do
  value=${!value_name}
  [[ "$value" =~ ^[0-9]+$ ]] || hold_node "invalid_${value_name}_${value:-unset}"
done
total_episodes=$((10#$total_episodes))
physical_world=$((10#$physical_world))
physical_rank=$((10#$physical_rank))
expected_nodes=$((10#$expected_nodes))
gpus_per_node=$((10#$gpus_per_node))
lanes_per_gpu=$((10#$lanes_per_gpu))
((total_episodes >= 1)) || hold_node total_episodes_must_be_positive
((expected_nodes == 2)) || hold_node "expected_nodes_${expected_nodes}_must_be_2"
((gpus_per_node == 4)) || hold_node "gpus_per_node_${gpus_per_node}_must_be_4"
((physical_world == expected_nodes)) || hold_node "world_size_${physical_world}_expected_${expected_nodes}"
((physical_rank >= 0 && physical_rank < physical_world)) || hold_node "rank_${physical_rank}_out_of_range"
case "$lanes_per_gpu" in 1|2|4|8) ;; *) hold_node "invalid_lanes_${lanes_per_gpu}" ;; esac
[[ "$production_base" == /* && "$scratch_base" == /* ]] || hold_node roots_must_be_absolute

for command in flock jq nvidia-smi python setsid sha256sum taskset tee; do
  command -v "$command" >/dev/null 2>&1 || hold_node "missing_command_${command}"
done
[[ -s "$script_dir/run_rank_production.sh" ]] || hold_node missing_rank_runner

if [[ "$node_preflight_only" == 1 && -n "${XONOTIC_DUEL_TEST_GPU_ROWS:-}" ]]; then
  mapfile -t gpu_rows < <(printf '%s\n' "$XONOTIC_DUEL_TEST_GPU_ROWS")
else
  mapfile -t gpu_rows < <(nvidia-smi --query-gpu=index,uuid,name --format=csv,noheader,nounits)
fi
(( ${#gpu_rows[@]} == gpus_per_node )) || hold_node "visible_gpu_count_${#gpu_rows[@]}_expected_${gpus_per_node}"

declare -a gpu_uuids=()
declare -a gpu_names=()
for ((local_gpu=0; local_gpu<gpus_per_node; ++local_gpu)); do
  IFS=',' read -r gpu_index gpu_uuid gpu_name <<<"${gpu_rows[$local_gpu]}"
  gpu_index=${gpu_index//[[:space:]]/}
  gpu_uuid=${gpu_uuid//[[:space:]]/}
  gpu_name=${gpu_name#${gpu_name%%[![:space:]]*}}
  [[ "$gpu_index" == "$local_gpu" && "$gpu_uuid" == GPU-* ]] || hold_node "unexpected_gpu_row_${local_gpu}"
  gpu_uuids[$local_gpu]=$gpu_uuid
  gpu_names[$local_gpu]=$gpu_name
done

mapfile -t cpu_sets < <(
  python - "$gpus_per_node" <<'PY'
import os
import sys

groups = int(sys.argv[1])
cpus = sorted(os.sched_getaffinity(0))
if len(cpus) < groups * 8:
    raise SystemExit(2)
for index in range(groups):
    print(",".join(str(cpu) for cpu in cpus[index::groups]))
PY
)
(( ${#cpu_sets[@]} == gpus_per_node )) || hold_node cpu_partition_failed

logical_world=$((expected_nodes * gpus_per_node))
job_root="$production_base/$run_id"
node_tag=$(printf '%02d' "$physical_rank")
node_root="$job_root/nodes/node_$node_tag"
mkdir -p "$node_root" "$job_root/ranks"
exec > >(tee -a "$node_root/node.log") 2>&1

printf 'duel_v11_node_start run_id=%s node=%s/%s logical_world=%s total_episodes=%s lanes_per_gpu=%s utc=%s\n' \
  "$run_id" "$physical_rank" "$physical_world" "$logical_world" "$total_episodes" "$lanes_per_gpu" "$(date -u +%FT%TZ)"
for ((local_gpu=0; local_gpu<gpus_per_node; ++local_gpu)); do
  logical_rank=$((physical_rank * gpus_per_node + local_gpu))
  printf 'duel_v11_gpu_binding node=%s local_gpu=%s global_rank=%s uuid=%s name=%s cpuset=%s\n' \
    "$physical_rank" "$local_gpu" "$logical_rank" "${gpu_uuids[$local_gpu]}" "${gpu_names[$local_gpu]}" "${cpu_sets[$local_gpu]}"
done

if [[ "$node_preflight_only" == 1 ]]; then
  jq -n \
    --arg run_id "$run_id" \
    --argjson node_rank "$physical_rank" \
    --argjson node_world "$physical_world" \
    --argjson logical_world "$logical_world" \
    --argjson total_episodes "$total_episodes" \
    --argjson lanes_per_gpu "$lanes_per_gpu" \
    '{preflight:true,run_id:$run_id,node_rank:$node_rank,node_world:$node_world,logical_world:$logical_world,total_episodes:$total_episodes,lanes_per_gpu:$lanes_per_gpu}' \
    >"$node_root/PREFLIGHT.json"
  printf 'duel_v11_node_preflight_complete path=%s\n' "$node_root/PREFLIGHT.json"
  exit 0
fi

declare -a supervisor_pids=()

supervise_rank() {
  local local_gpu=$1
  local logical_rank=$2
  local gpu_uuid=$3
  local cpu_set=$4
  local rank_tag rank_root attempt delay runner_pid runner_sid rc binding_tmp
  rank_tag=$(printf '%03d' "$logical_rank")
  rank_root="$job_root/ranks/rank_$rank_tag"
  mkdir -p "$rank_root"
  binding_tmp="$rank_root/.GPU_BINDING.$$.tmp"
  jq -n \
    --arg run_id "$run_id" \
    --arg gpu_uuid "$gpu_uuid" \
    --arg cpu_set "$cpu_set" \
    --arg created_at "$(date -u +%FT%TZ)" \
    --argjson node_rank "$physical_rank" \
    --argjson local_gpu "$local_gpu" \
    --argjson global_rank "$logical_rank" \
    --argjson global_world "$logical_world" \
    '{run_id:$run_id,created_at:$created_at,node_rank:$node_rank,local_gpu:$local_gpu,global_rank:$global_rank,global_world:$global_world,gpu_uuid:$gpu_uuid,cpu_set:$cpu_set}' \
    >"$binding_tmp"
  mv "$binding_tmp" "$rank_root/GPU_BINDING.json"
  attempt=0
  runner_pid=
  runner_sid=

  stop_supervisor() {
    local -a session_members=()
    if [[ "$runner_sid" =~ ^[0-9]+$ ]]; then
      mapfile -t session_members < <(ps -eo pid=,sid= | awk -v target="$runner_sid" '$2==target {print $1}')
      if ((${#session_members[@]})); then
        kill -TERM "${session_members[@]}" 2>/dev/null || true
      fi
    elif [[ -n "$runner_pid" ]]; then
      kill -TERM "$runner_pid" 2>/dev/null || true
    fi
    if [[ -n "$runner_pid" ]]; then
      wait "$runner_pid" 2>/dev/null || true
    fi
    exit 0
  }
  trap stop_supervisor TERM INT

  while true; do
    attempt=$((attempt + 1))
    printf 'duel_v11_rank_attempt rank=%s/%s local_gpu=%s uuid=%s attempt=%s utc=%s\n' \
      "$logical_rank" "$logical_world" "$local_gpu" "$gpu_uuid" "$attempt" "$(date -u +%FT%TZ)"
    (
      export CUDA_VISIBLE_DEVICES="$gpu_uuid"
      export SDL_HINT_EGL_DEVICE="$local_gpu"
      export SDL_VIDEODRIVER=offscreen
      export SDL_AUDIODRIVER=dummy
      export SDL_RENDER_DRIVER=opengl
      export XONOTIC_DUEL_PRODUCTION_ROOT="$production_base"
      export XONOTIC_DUEL_SCRATCH_BASE="$scratch_base"
      export XONOTIC_DUEL_LANES_PER_GPU="$lanes_per_gpu"
      cd "$duel_root"
      exec setsid taskset -c "$cpu_set" bash "$script_dir/run_rank_production.sh" \
        "$run_id" "$total_episodes" "$logical_rank" "$logical_world"
    ) >>"$rank_root/supervisor.log" 2>&1 &
    runner_pid=$!
    runner_sid=
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      runner_sid=$(ps -o sid= -p "$runner_pid" 2>/dev/null | tr -d ' ')
      [[ "$runner_sid" =~ ^[0-9]+$ ]] && break
      sleep 0.05
    done
    if wait "$runner_pid"; then rc=0; else rc=$?; fi
    runner_pid=
    runner_sid=
    if ((rc == 0)); then
      printf 'duel_v11_rank_complete_hold rank=%s/%s local_gpu=%s utc=%s\n' \
        "$logical_rank" "$logical_world" "$local_gpu" "$(date -u +%FT%TZ)"
      while true; do
        printf 'duel_v11_rank_idle_heartbeat rank=%s/%s local_gpu=%s state=complete_hold utc=%s\n' \
          "$logical_rank" "$logical_world" "$local_gpu" "$(date -u +%FT%TZ)"
        sleep "$heartbeat_seconds"
      done
    fi
    delay=$((retry_base_seconds * attempt))
    ((delay > retry_max_seconds)) && delay=$retry_max_seconds
    printf 'duel_v11_rank_retry rank=%s/%s local_gpu=%s rc=%s delay_seconds=%s utc=%s\n' \
      "$logical_rank" "$logical_world" "$local_gpu" "$rc" "$delay" "$(date -u +%FT%TZ)"
    sleep "$delay"
  done
}

start_supervisor() {
  local local_gpu=$1
  local logical_rank=$((physical_rank * gpus_per_node + local_gpu))
  supervise_rank "$local_gpu" "$logical_rank" "${gpu_uuids[$local_gpu]}" "${cpu_sets[$local_gpu]}" &
  supervisor_pids[$local_gpu]=$!
  printf 'duel_v11_supervisor_start local_gpu=%s global_rank=%s pid=%s\n' \
    "$local_gpu" "$logical_rank" "${supervisor_pids[$local_gpu]}"
}

stop_node() {
  local pid
  printf 'duel_v11_node_stop rank=%s utc=%s\n' "$physical_rank" "$(date -u +%FT%TZ)"
  for pid in "${supervisor_pids[@]:-}"; do
    [[ -n "$pid" ]] || continue
    kill -TERM "$pid" 2>/dev/null || true
  done
  for pid in "${supervisor_pids[@]:-}"; do
    [[ -n "$pid" ]] || continue
    wait "$pid" 2>/dev/null || true
  done
  exit 0
}
trap stop_node TERM INT

for ((local_gpu=0; local_gpu<gpus_per_node; ++local_gpu)); do
  start_supervisor "$local_gpu"
done

while true; do
  sleep "$heartbeat_seconds"
  for ((local_gpu=0; local_gpu<gpus_per_node; ++local_gpu)); do
    pid=${supervisor_pids[$local_gpu]}
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      printf 'duel_v11_supervisor_restart local_gpu=%s old_pid=%s utc=%s\n' "$local_gpu" "$pid" "$(date -u +%FT%TZ)"
      start_supervisor "$local_gpu"
    fi
  done
  completed_ranks=$(find "$job_root/ranks" -mindepth 2 -maxdepth 2 -name RANK_COMPLETE.json -type f | wc -l)
  printf 'duel_v11_node_heartbeat rank=%s completed_global_ranks=%s/%s state=running_or_complete_hold utc=%s\n' \
    "$physical_rank" "$completed_ranks" "$logical_world" "$(date -u +%FT%TZ)"
  nvidia-smi --query-gpu=index,uuid,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits || true
done
