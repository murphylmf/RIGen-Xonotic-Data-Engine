#!/usr/bin/env bash
set -uo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/.." && pwd -P)
cd "$root"
python_bin=${STAGE2_PYTHON:-./environment}
run_id=${RUN_ID:-stage2_motion_near5_combo_42k_v12_replenish_r6retryfix_28gpu_20260818_01}
manifest_root=${STAGE2_MANIFEST_ROOT:-$root/manifests/stage2_motion_near5_combo_42k_v12_replenish_28shard_20260818_r6}
output_root=${STAGE2_OUTPUT_ROOT:-$root/production_runs/$run_id}
scratch_base=${STAGE2_SCRATCH_BASE:-./tmp/xonotic-stage2-motion-activeonly-7x4}
workers=${STAGE2_WORKERS_PER_GPU:-8}
physical_world=${WORLD_SIZE:-}
physical_rank=${RANK:-}
expected_nodes=${STAGE2_EXPECTED_NODES:-7}
gpus_per_node=${STAGE2_GPUS_PER_NODE:-4}
logical_world=$((expected_nodes * gpus_per_node))
retry_base_seconds=${STAGE2_RETRY_BASE_SECONDS:-30}
retry_max_seconds=${STAGE2_RETRY_MAX_SECONDS:-300}
heartbeat_seconds=${STAGE2_HEARTBEAT_SECONDS:-60}
runtime_lock=$root/locks/stage2_motion_7x4_activeonly_v12r6_resilient_runtime.sha256
runner=production_scripts/run_stage2_motion_42k_activeonly_v12r6_multigpu.py
gpu_holder=production_scripts/gpu_memory_holder.py
gpu_holder_python=${STAGE2_GPU_HOLDER_PYTHON:-/usr/bin/python3}
gpu_holder_target_gib=${STAGE2_GPU_HOLDER_TARGET_GIB:-166.5}
gpu_holder_min_free_gib=${STAGE2_GPU_HOLDER_MIN_FREE_GIB:-96}

hold_node() {
  local reason=$1
  echo "stage2_activeonly_node_hold rank=${physical_rank:-unset} reason=$reason" >&2
  while true; do
    echo "stage2_activeonly_node_hold_heartbeat rank=${physical_rank:-unset} reason=$reason utc=$(date -u +%FT%TZ)"
    sleep "$heartbeat_seconds"
  done
}

[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || hold_node "invalid_run_id"
[[ "$expected_nodes" =~ ^[0-9]+$ && "$gpus_per_node" =~ ^[0-9]+$ ]] || hold_node "invalid_topology_config"
[[ "$physical_world" =~ ^[0-9]+$ && "$physical_rank" =~ ^[0-9]+$ ]] || hold_node "missing_dlc_rank_world"
physical_world=$((10#$physical_world))
physical_rank=$((10#$physical_rank))
expected_nodes=$((10#$expected_nodes))
gpus_per_node=$((10#$gpus_per_node))
logical_world=$((expected_nodes * gpus_per_node))
((physical_world == expected_nodes)) || hold_node "world_size_${physical_world}_expected_${expected_nodes}"
((physical_rank >= 0 && physical_rank < physical_world)) || hold_node "rank_out_of_range_${physical_rank}"
((gpus_per_node == 4)) || hold_node "gpus_per_node_${gpus_per_node}_expected_4"
[[ "$workers" =~ ^[0-9]+$ ]] || hold_node "invalid_workers_${workers}"
workers=$((10#$workers))
((workers >= 1 && workers <= 16)) || hold_node "workers_out_of_range_${workers}"
[[ -x "$python_bin" ]] || hold_node "missing_python_${python_bin}"
[[ -x "$gpu_holder_python" ]] || hold_node "missing_gpu_holder_python_${gpu_holder_python}"
[[ -s "$runtime_lock" ]] || hold_node "missing_runtime_lock"
[[ -s "$runner" ]] || hold_node "missing_runner"
[[ -s "$gpu_holder" ]] || hold_node "missing_gpu_holder"

for command in ffmpeg ffprobe flock nvidia-smi sha256sum taskset tee; do
  command -v "$command" >/dev/null 2>&1 || hold_node "missing_command_${command}"
done
if ! sha256sum -c "$runtime_lock" --quiet; then
  hold_node "runtime_lock_failed"
fi
if ! "$gpu_holder_python" -c 'import torch; assert torch.version.cuda is not None'; then
  hold_node "gpu_holder_python_torch_unavailable_${gpu_holder_python}"
fi

mapfile -t gpu_rows < <(
  nvidia-smi --query-gpu=index,uuid,name --format=csv,noheader,nounits
)
(( ${#gpu_rows[@]} == gpus_per_node )) || hold_node "visible_gpu_count_${#gpu_rows[@]}_expected_${gpus_per_node}"

declare -a gpu_uuids=()
for local_gpu in $(seq 0 $((gpus_per_node - 1))); do
  IFS=',' read -r gpu_index gpu_uuid gpu_name <<<"${gpu_rows[$local_gpu]}"
  gpu_index=${gpu_index//[[:space:]]/}
  gpu_uuid=${gpu_uuid//[[:space:]]/}
  [[ "$gpu_index" == "$local_gpu" && "$gpu_uuid" == GPU-* ]] || hold_node "unexpected_gpu_row_${local_gpu}"
  gpu_uuids[$local_gpu]=$gpu_uuid
done

mapfile -t cpu_sets < <(
  "$python_bin" - "$gpus_per_node" <<'PY'
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
(( ${#cpu_sets[@]} == gpus_per_node )) || hold_node "cpu_partition_failed"

count_tag=$(printf '%03d' "$logical_world")
metadata=$manifest_root/MANIFEST_METADATA.json
[[ -s "$metadata" ]] || hold_node "missing_manifest_metadata"
for local_gpu in $(seq 0 $((gpus_per_node - 1))); do
  logical_shard=$((physical_rank * gpus_per_node + local_gpu))
  rank_tag=$(printf '%03d' "$logical_shard")
  manifest=$manifest_root/shards-$count_tag/shard-$rank_tag-of-$count_tag.jsonl
  [[ -s "$manifest" ]] || hold_node "missing_manifest_shard_${rank_tag}"
done

node_tag=$(printf '%02d' "$physical_rank")
node_log_root=$root/logs/$run_id/node_$node_tag
mkdir -p "$node_log_root"
exec > >(tee -a "$node_log_root/node.log") 2>&1

echo "stage2_activeonly_node_start run_id=$run_id physical_rank=$physical_rank/$physical_world logical_world=$logical_world workers_per_gpu=$workers output_root=$output_root"
for local_gpu in $(seq 0 $((gpus_per_node - 1))); do
  echo "stage2_activeonly_gpu_binding node_rank=$physical_rank local_gpu=$local_gpu uuid=${gpu_uuids[$local_gpu]} cpuset=${cpu_sets[$local_gpu]}"
done

export PYTHONUNBUFFERED=1
export XONOTIC_CAPTURE_ROOT="$root"
export XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG=capture-ee4c0aac65db-aarch64
export XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT=ee4c0aac65dbac689904b320c7db4e43dfd93d20
export XONOTIC_BUILD_GLOB=build/capture-ee4c0aac65db-aarch64
export XONOTIC_OFFLINE_ACCELERATE=1
export XONOTIC_LIVE_TIME_SCALE=${XONOTIC_LIVE_TIME_SCALE:-2}
export XONOTIC_ALLOW_LIVE_TIME_SCALE_ONE_VALIDATION=0
export XONOTIC_LIVE_CONCURRENCY=${XONOTIC_LIVE_CONCURRENCY:-8}
export XONOTIC_RENDER_CONCURRENCY=${XONOTIC_RENDER_CONCURRENCY:-8}
export XONOTIC_SDL_CONCURRENCY=${XONOTIC_SDL_CONCURRENCY:-8}
export XONOTIC_ENCODE_CONCURRENCY=${XONOTIC_ENCODE_CONCURRENCY:-8}
export XONOTIC_X264_THREADS=${XONOTIC_X264_THREADS:-4}
export XONOTIC_LIVE_TIMEOUT_SECONDS=${XONOTIC_LIVE_TIMEOUT_SECONDS:-240}
export XONOTIC_RENDER_TIMEOUT_SECONDS=${XONOTIC_RENDER_TIMEOUT_SECONDS:-240}
export XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=${XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS:-240}
export XONOTIC_RENDER_STARTUP_STALL_SECONDS=${XONOTIC_RENDER_STARTUP_STALL_SECONDS:-90}
export XONOTIC_PILOT_RENDER_ATTEMPTS=${XONOTIC_PILOT_RENDER_ATTEMPTS:-1}
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

supervise_shard() {
  local local_gpu=$1
  local logical_shard=$2
  local gpu_uuid=$3
  local cpu_set=$4
  local rank_tag manifest scratch_root log_root port_base attempt delay runner_pid holder_pid rc
  rank_tag=$(printf '%03d' "$logical_shard")
  manifest=$manifest_root/shards-$count_tag/shard-$rank_tag-of-$count_tag.jsonl
  scratch_root=$scratch_base/$run_id/shard_$rank_tag
  log_root=$root/logs/$run_id/shard_$rank_tag
  port_base=$((26000 + logical_shard * 100))
  attempt=0
  runner_pid=
  holder_pid=

  start_holder() {
    (
      export CUDA_VISIBLE_DEVICES="$gpu_uuid"
      cd "$root"
      exec "$gpu_holder_python" -u "$gpu_holder" \
        --target-used-gib "$gpu_holder_target_gib" \
        --min-free-gib "$gpu_holder_min_free_gib" \
        --heartbeat-seconds "$heartbeat_seconds"
    ) >>"$log_root/gpu_memory_holder.log" 2>&1 &
    holder_pid=$!
    echo "stage2_activeonly_gpu_holder_start rank=$logical_shard pid=$holder_pid target_gib=$gpu_holder_target_gib min_free_gib=$gpu_holder_min_free_gib"
  }

  stop_supervisor() {
    if [[ -n "$runner_pid" ]] && kill -0 "$runner_pid" 2>/dev/null; then
      kill -TERM "$runner_pid" 2>/dev/null || true
      wait "$runner_pid" 2>/dev/null || true
    fi
    if [[ -n "$holder_pid" ]] && kill -0 "$holder_pid" 2>/dev/null; then
      kill -TERM "$holder_pid" 2>/dev/null || true
      wait "$holder_pid" 2>/dev/null || true
    fi
    exit 0
  }
  trap stop_supervisor TERM INT
  mkdir -p "$log_root" "$scratch_root"
  start_holder

  while true; do
    if ! kill -0 "$holder_pid" 2>/dev/null; then
      wait "$holder_pid" 2>/dev/null || true
      start_holder
    fi
    attempt=$((attempt + 1))
    echo "stage2_activeonly_shard_attempt rank=$logical_shard/$logical_world local_gpu=$local_gpu uuid=$gpu_uuid attempt=$attempt utc=$(date -u +%FT%TZ)"
    (
      export STAGE2_SELECTED_GPU_INDEX=$local_gpu
      export SDL_HINT_EGL_DEVICE=$local_gpu
      export CUDA_VISIBLE_DEVICES=$gpu_uuid
      cd "$root"
      exec taskset -c "$cpu_set" "$python_bin" -u \
        "$runner" \
        --manifest "$manifest" \
        --metadata "$metadata" \
        --output-root "$output_root" \
        --scratch-root "$scratch_root" \
        --shard-index "$logical_shard" \
        --shard-count "$logical_world" \
        --workers "$workers" \
        --live-concurrency "$XONOTIC_LIVE_CONCURRENCY" \
        --render-concurrency "$XONOTIC_RENDER_CONCURRENCY" \
        --encode-concurrency "$XONOTIC_ENCODE_CONCURRENCY" \
        --x264-threads "$XONOTIC_X264_THREADS" \
        --port-base "$port_base" \
        --max-operational-attempts 2 \
        --fail-on-incomplete
    ) >>"$log_root/run.log" 2>&1 &
    runner_pid=$!
    if wait "$runner_pid"; then rc=0; else rc=$?; fi
    runner_pid=
    if ((rc == 0)); then
      echo "stage2_activeonly_shard_idle_hold rank=$logical_shard/$logical_world local_gpu=$local_gpu reason=runner_completed utc=$(date -u +%FT%TZ)"
      while true; do
        sleep "$heartbeat_seconds" &
        runner_pid=$!
        wait "$runner_pid" || true
        runner_pid=
        echo "stage2_activeonly_shard_idle_heartbeat rank=$logical_shard/$logical_world local_gpu=$local_gpu utc=$(date -u +%FT%TZ)"
      done
    fi
    delay=$((retry_base_seconds * attempt))
    ((delay > retry_max_seconds)) && delay=$retry_max_seconds
    echo "stage2_activeonly_shard_retry rank=$logical_shard/$logical_world local_gpu=$local_gpu rc=$rc delay_seconds=$delay utc=$(date -u +%FT%TZ)"
    sleep "$delay" &
    runner_pid=$!
    wait "$runner_pid" || true
    runner_pid=
  done
}

declare -a supervisor_pids=()
start_supervisor() {
  local local_gpu=$1
  local logical_shard=$((physical_rank * gpus_per_node + local_gpu))
  supervise_shard "$local_gpu" "$logical_shard" "${gpu_uuids[$local_gpu]}" "${cpu_sets[$local_gpu]}" &
  supervisor_pids[$local_gpu]=$!
  echo "stage2_activeonly_supervisor_start local_gpu=$local_gpu logical_shard=$logical_shard pid=${supervisor_pids[$local_gpu]}"
}

stop_node() {
  echo "stage2_activeonly_node_stop rank=$physical_rank utc=$(date -u +%FT%TZ)"
  for pid in "${supervisor_pids[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
  for pid in "${supervisor_pids[@]}"; do wait "$pid" 2>/dev/null || true; done
  exit 0
}
trap stop_node TERM INT

for local_gpu in $(seq 0 $((gpus_per_node - 1))); do start_supervisor "$local_gpu"; done

while true; do
  sleep "$heartbeat_seconds" &
  heartbeat_pid=$!
  wait "$heartbeat_pid" || true
  for local_gpu in $(seq 0 $((gpus_per_node - 1))); do
    pid=${supervisor_pids[$local_gpu]}
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      echo "stage2_activeonly_supervisor_restart local_gpu=$local_gpu old_pid=$pid utc=$(date -u +%FT%TZ)"
      start_supervisor "$local_gpu"
    fi
  done
  echo "stage2_activeonly_node_heartbeat rank=$physical_rank utc=$(date -u +%FT%TZ)"
  nvidia-smi --query-gpu=index,uuid,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits || true
done
