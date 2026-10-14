#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
release_id=${LONG60_RELEASE_ID:-stage2_long60_multi_enemy_lifecycle_30h_20260824_v2}
production_script=${LONG60_PRODUCTION_SCRIPT:-pilot_scripts/long60_production_v1.py}
build_tag=${LONG60_BUILD_TAG:-capture-65a48cd4a2c6-aarch64}
manifest_root=${LONG60_MANIFEST_ROOT:-"$root/manifests/$release_id"}
output_root=${LONG60_OUTPUT_ROOT:-"./rigen_data/$release_id"}
run_id=${LONG60_RUN_ID:-${JOB_ID:-${DLC_JOB_ID:-long60-manual}}}
node_count=${LONG60_NODE_COUNT:-2}
gpus_per_node=4
lanes_per_gpu=4
lanes_per_node=$((gpus_per_node * lanes_per_gpu))
total_lanes=$((node_count * lanes_per_node))
max_node_passes=${LONG60_MAX_NODE_PASSES:-8}





abnormal_hold_marker="$output_root/control/HOLD_ON_ABNORMAL_EXIT"
hold_retry_seconds=${LONG60_HOLD_RETRY_SECONDS:-30}
if [[ -f "$abnormal_hold_marker" && ${LONG60_HOLD_SUPERVISOR_CHILD:-0} != 1 ]]; then
  supervised_pid=""
  long60_hold_supervisor_signal() {
    local signal_name=$1
    echo "long60_hold_supervisor_signal_ignored utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) signal=$signal_name child_pid=${supervised_pid:-none} marker=$abnormal_hold_marker" >&2
  }
  trap 'long60_hold_supervisor_signal HUP' HUP
  trap 'long60_hold_supervisor_signal INT' INT
  trap 'long60_hold_supervisor_signal TERM' TERM
  set +e
  echo "LONG60_ABNORMAL_EXIT_SUPERVISOR_ENABLED marker=$abnormal_hold_marker" >&2
  while :; do
    LONG60_HOLD_SUPERVISOR_CHILD=1 \
      bash "$script_dir/run_long60_production_2x4_node.sh" &
    supervised_pid=$!
    while :; do
      wait "$supervised_pid"
      supervised_status=$?
      if kill -0 "$supervised_pid" 2>/dev/null; then

        continue
      fi
      break
    done
    echo "long60_supervised_child_exited utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) status=$supervised_status retry_seconds=$hold_retry_seconds marker=$abnormal_hold_marker" >&2
    supervised_pid=""
    sleep "$hold_retry_seconds"
  done
fi

resolve_node_rank() {
  local candidate name
  for candidate in \
    "${NODE_RANK:-}" \
    "${PET_NODE_RANK:-}" \
    "${RANK:-}" \
    "${WORKER_RANK:-}" \
    "${SENSECORE_PYTORCH_NODE_RANK:-}"; do
    if [[ "$candidate" =~ ^[0-9]+$ ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  name=${POD_NAME:-}
  if [[ "$name" =~ -master-([0-9]+)$ ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "$name" =~ -worker-([0-9]+)$ ]]; then
    printf '%s\n' "$((BASH_REMATCH[1] + 1))"
    return 0
  fi
  return 1
}

node_rank=$(resolve_node_rank) || {
  echo "unable to resolve DLC node rank from environment or pod name" >&2
  env | sort | grep -E '(^|_)(RANK|WORLD_SIZE|POD_NAME|HOSTNAME|JOB_ID)=' >&2 || true
  exit 64
}
[[ "$node_rank" =~ ^[0-9]+$ ]] &&
  (( node_rank >= 0 && node_rank < node_count )) || {
  echo "node rank out of range: rank=$node_rank node_count=$node_count" >&2
  exit 64
}
(( node_count == 2 || node_count == 4 )) || {
  echo "formal topology requires two or four whole nodes; got $node_count" >&2
  exit 64
}
visible_gpus=$(nvidia-smi -L | wc -l)
(( visible_gpus == gpus_per_node )) || {
  echo "formal whole-node topology requires 4 visible GPUs; got $visible_gpus" >&2
  exit 69
}
[[ -r "$manifest_root/PREPARED.json" &&
   -r "$manifest_root/MANIFEST_METADATA.json" &&
   -r "$manifest_root/manifest.jsonl" ]] || {
  echo "prepared long60 manifest missing: $manifest_root" >&2
  exit 66
}
[[ -x "$root/build/$build_tag/bin/xonotic-local-sdl" ]] || {
  echo "locked ARM64 long60 build missing: $build_tag" >&2
  exit 66
}

mkdir -p "$output_root/logs/$run_id" "$output_root/control/$run_id"
node_scratch=$(mktemp -d "./tmp/xonotic-long60-${node_rank}.XXXXXXXX")
node_log="$output_root/logs/$run_id/node-${node_rank}.log"
exec > >(tee -a "$node_log") 2>&1

echo "long60_node_start utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) run_id=$run_id node_rank=$node_rank node_count=$node_count visible_gpus=$visible_gpus total_lanes=$total_lanes scratch=$node_scratch"
[[ -r "$root/$production_script" ]] || {
  echo "long60 production script missing: $root/$production_script" >&2
  exit 66
}
for gpu in 0 1 2 3; do
  echo "long60_egl_preflight_start gpu=$gpu"
  SDL_HINT_EGL_DEVICE=$gpu \
  SDL_VIDEODRIVER=offscreen \
  SDL_AUDIODRIVER=dummy \
    "$root/build/$build_tag/bin/cci-sdl-offscreen-probe" \
    | grep -E '^(video_driver_current|gl_vendor|gl_renderer|center_pixel_.*)='
  echo "long60_egl_preflight_pass gpu=$gpu"
done
./environment \
  "$root/$production_script" audit \
  --manifest-root "$manifest_root" \
  --output-root "$output_root"

node_complete=0
for pass_index in $(seq 1 "$max_node_passes"); do
  echo "long60_node_pass_start pass=$pass_index/$max_node_passes"
  pids=()
  lane_ids=()
  for gpu in 0 1 2 3; do
    for sublane in 0 1 2 3; do
      local_lane=$((gpu * lanes_per_gpu + sublane))
      global_lane=$((node_rank * lanes_per_node + local_lane))
      lane_scratch="$node_scratch/lane-${local_lane}-pass-${pass_index}"
      lane_log="$output_root/logs/$run_id/lane-${global_lane}.log"
      port=$((31000 + local_lane * 16))
      (
        set -o pipefail
        CUDA_VISIBLE_DEVICES=$gpu \
        XONOTIC_CAPTURE_ROOT="$root" \
        XONOTIC_BUILD_GLOB="build/$build_tag" \
        XONOTIC_CAPTURE_TMP="$lane_scratch/runtime" \
        XONOTIC_LONG60_X264_THREADS=8 \
        XONOTIC_LIVE_TIME_SCALE=2 \
        XONOTIC_OFFLINE_ACCELERATE=1 \
        XONOTIC_LIVE_TIMEOUT_SECONDS=240 \
        XONOTIC_RENDER_TIMEOUT_SECONDS=600 \
        XONOTIC_ENGINE_NET_TIMEOUT_SECONDS=660 \
        XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS=120 \
        SDL_HINT_EGL_DEVICE=$gpu \
        SDL_VIDEODRIVER=offscreen \
        SDL_AUDIODRIVER=dummy \
        SDL_RENDER_DRIVER=opengl \
        ./environment -u \
          "$root/$production_script" worker \
          --manifest-root "$manifest_root" \
          --output-root "$output_root" \
          --scratch-root "$lane_scratch" \
          --lane-id "$global_lane" \
          --lane-count "$total_lanes" \
          --port "$port" \
          --max-attempts 3 2>&1 | tee -a "$lane_log"
      ) &
      pids+=("$!")
      lane_ids+=("$global_lane")
    done
  done

  failed_lanes=()
  set +e
  for index in "${!pids[@]}"; do
    wait "${pids[$index]}"
    status=$?
    if (( status != 0 )); then
      failed_lanes+=("${lane_ids[$index]}:$status")
    fi
  done
  set -e
  if (( ${#failed_lanes[@]} == 0 )); then
    node_complete=1
    echo "long60_node_pass_complete pass=$pass_index"
    break
  fi
  echo "long60_node_pass_incomplete pass=$pass_index failed=${failed_lanes[*]}"
  sleep 10
done

(( node_complete == 1 )) || {
  echo "long60_node_exhausted_recovery_passes node_rank=$node_rank" >&2
  exit 75
}
if find "$node_scratch" -type f -name '*.avi' -print -quit | grep -q .; then
  echo "raw AVI remains in node-local scratch after node completion" >&2
  find "$node_scratch" -type f -name '*.avi' -print | head -n 20 >&2
  exit 74
fi

node_marker="$output_root/control/$run_id/node-${node_rank}.done"
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$node_marker"
echo "long60_node_local_complete marker=$node_marker"

complete_marker="$output_root/control/$run_id/PRODUCTION_COMPLETE"
if (( node_rank == 0 )); then
  deadline=$((SECONDS + 172800))
  while :; do
    ready=1
    for rank in $(seq 0 $((node_count - 1))); do
      [[ -f "$output_root/control/$run_id/node-${rank}.done" ]] || ready=0
    done
    (( ready == 1 )) && break
    (( SECONDS < deadline )) || {
      echo "timed out waiting for whole-node completion barrier" >&2
      exit 75
    }
    sleep 20
  done
  ./environment \
    "$root/$production_script" finalize \
    --manifest-root "$manifest_root" \
    --output-root "$output_root"
  printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$complete_marker"
else
  deadline=$((SECONDS + 172800))
  while [[ ! -f "$complete_marker" ]]; do
    (( SECONDS < deadline )) || {
      echo "timed out waiting for production completion marker" >&2
      exit 75
    }
    sleep 20
  done
fi

echo "LONG60_PRODUCTION_COMPLETE_HOLDING_GPUS run_id=$run_id node_rank=$node_rank marker=$complete_marker"
while :; do
  echo "long60_completion_hold_heartbeat utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) run_id=$run_id node_rank=$node_rank"
  sleep 300
done
