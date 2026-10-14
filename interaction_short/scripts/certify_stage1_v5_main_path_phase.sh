#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
log_root="$root/logs"
prototype_metadata="$root/manifests/stage1_foundation_v5_certification/PROTOTYPE_METADATA.json"
mkdir -p "$log_root"
cd "$root"

path_certifier_active() {
  pgrep -f '[p]ython scripts/certify_stage1_v5_paths.py' >/dev/null
}

wait_for_path_certifier() {
  while path_certifier_active; do
    sleep 5
  done
}

run_wave() {
  local wave=$1
  local workers=${2:-12}
  local completed=false
  local retry_round timestamp wave_log command_status
  for retry_round in 1 2 3; do
    wait_for_path_certifier
    timestamp=$(date -u +%Y%m%dT%H%M%SZ)
    wave_log="$log_root/${timestamp}_stage1_v5_path_${wave}_round_${retry_round}.log"
    echo "path_wave=$wave retry_round=$retry_round log=$wave_log"
    set +e
    ./scripts/cci_run.sh \
      python scripts/certify_stage1_v5_paths.py \
      --wave "$wave" --workers "$workers" --port-base 32000 \
      --max-attempts 3 \
      2>&1 | tee "$wave_log"
    command_status=${PIPESTATUS[0]}
    set -e
    echo "path_wave=$wave retry_round=$retry_round exit_status=$command_status"
    if (( command_status == 0 )); then
      completed=true
      break
    fi
    sleep 10
  done
  if [[ "$completed" != true ]]; then
    echo "path wave $wave still has operational failures after three resumptions" >&2
    return 2
  fi
}

run_wave_range() {
  local wave=$1
  local ordinal_start=$2
  local ordinal_end=$3
  local workers=${4:-12}
  local completed=false
  local retry_round timestamp wave_log command_status
  for retry_round in 1 2 3; do
    wait_for_path_certifier
    timestamp=$(date -u +%Y%m%dT%H%M%SZ)
    wave_log="$log_root/${timestamp}_stage1_v5_path_${wave}_${ordinal_start}_${ordinal_end}_round_${retry_round}.log"
    echo "path_wave=$wave ordinal_start=$ordinal_start ordinal_end=$ordinal_end retry_round=$retry_round log=$wave_log"
    set +e
    ./scripts/cci_run.sh \
      python scripts/certify_stage1_v5_paths.py \
      --wave "$wave" --workers "$workers" --port-base 32000 \
      --max-attempts 3 --ordinal-start "$ordinal_start" \
      --ordinal-end "$ordinal_end" \
      2>&1 | tee "$wave_log"
    command_status=${PIPESTATUS[0]}
    set -e
    echo "path_wave=$wave ordinal_start=$ordinal_start ordinal_end=$ordinal_end retry_round=$retry_round exit_status=$command_status"
    if (( command_status == 0 )); then
      completed=true
      break
    fi
    sleep 10
  done
  if [[ "$completed" != true ]]; then
    echo "path wave $wave range $ordinal_start..$ordinal_end still has operational failures after three resumptions" >&2
    return 2
  fi
}

run_fast_probe() {
  local completed=false
  local retry_round timestamp probe_log command_status
  for retry_round in 1 2 3; do
    wait_for_path_certifier
    timestamp=$(date -u +%Y%m%dT%H%M%SZ)
    probe_log="$log_root/${timestamp}_stage1_v5_fast_probe_0769_0832_round_${retry_round}.log"
    echo "fast_probe=769..832 retry_round=$retry_round log=$probe_log"
    set +e
    ./scripts/cci_run.sh \
      python scripts/certify_stage1_v5_paths.py \
      --wave targeted_fast --workers 12 --port-base 32000 \
      --max-attempts 3 --ordinal-start 769 --ordinal-end 832 \
      2>&1 | tee "$probe_log"
    command_status=${PIPESTATUS[0]}
    set -e
    echo "fast_probe=769..832 retry_round=$retry_round exit_status=$command_status"
    if (( command_status == 0 )); then
      completed=true
      break
    fi
    sleep 10
  done
  if [[ "$completed" != true ]]; then
    echo "fast probe still has operational failures after three resumptions" >&2
    return 2
  fi
}

run_fast_control_pool() {
  local completed=false
  local retry_round timestamp pool_log command_status
  for retry_round in 1 2 3; do
    wait_for_path_certifier
    timestamp=$(date -u +%Y%m%dT%H%M%SZ)
    pool_log="$log_root/${timestamp}_stage1_v5_fast_control_0001_1536_round_${retry_round}.log"
    echo "fast_control_pool=1..1536 retry_round=$retry_round log=$pool_log"
    set +e
    ./scripts/cci_run.sh \
      python scripts/certify_stage1_v5_paths.py \
      --wave targeted_fast --workers 12 --port-base 32000 \
      --max-attempts 3 --ordinal-start 1 --ordinal-end 1536 \
      2>&1 | tee "$pool_log"
    command_status=${PIPESTATUS[0]}
    set -e
    echo "fast_control_pool=1..1536 retry_round=$retry_round exit_status=$command_status"
    if (( command_status == 0 )); then
      completed=true
      break
    fi
    sleep 10
  done
  if [[ "$completed" != true ]]; then
    echo "fast control pool still has operational failures after three resumptions" >&2
    return 2
  fi
}

run_semantic_matrix() {
  local timestamp matrix_log weapon mode episode_id
  local -a primary_weapons=(
    Blaster Shotgun MachineGun Mortar Electro Crylink Vortex Hagar Devastator
  )
  local -a reload_weapons=(
    Shotgun MachineGun Mortar Electro Crylink Vortex Hagar Devastator
  )
  timestamp=$(date -u +%Y%m%dT%H%M%SZ)
  matrix_log="$log_root/${timestamp}_stage1_v5_semantic_overlay_matrix.log"
  echo "semantic_overlay_matrix_log=$matrix_log"
  {
    for weapon in "${primary_weapons[@]}"; do
      mode=environmental_primary
      episode_id="v5matrix_s1v5k000001_${weapon}_primary"
      run_semantic_overlay "$weapon" "$mode" "$episode_id"
    done
    for weapon in "${reload_weapons[@]}"; do
      mode=reload
      episode_id="v5matrix_s1v5k000001_${weapon}_reload"
      run_semantic_overlay "$weapon" "$mode" "$episode_id"
    done
  } 2>&1 | tee "$matrix_log"
}

run_semantic_overlay() {
  local weapon=$1
  local mode=$2
  local episode_id=$3
  local attempt
  for attempt in 1 2 3; do
    echo "semantic_overlay weapon=$weapon mode=$mode attempt=$attempt"
    if ./scripts/cci_run.sh \
      python scripts/smoke_stage1_v5_semantic_overlay.py \
      --prototype-id s1v5k_000001 --weapon "$weapon" \
      --mode "$mode" --episode-id "$episode_id" \
      --port 34200 --live-only; then
      return 0
    fi
  done
  echo "semantic overlay failed after three identical retries: $weapon $mode" >&2
  return 2
}

echo "main_path_phase_wait_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
while [[ ! -r "$prototype_metadata" ]] || path_certifier_active; do
  sleep 30
done

run_semantic_matrix
run_fast_probe
run_fast_control_pool



run_wave_range targeted_fast_world 1 1024 12


run_wave certification_spare 12
run_wave primary 12
run_wave replenishment 12


run_wave targeted_collision 4
echo "main_path_phase_completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
