#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
log_root="$root/logs"
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
  local ordinal_start=$2
  local ordinal_end=$3
  local workers=${4:-12}
  local completed=false
  local retry_round timestamp wave_log command_status
  for retry_round in 1 2 3; do
    wait_for_path_certifier
    timestamp=$(date -u +%Y%m%dT%H%M%SZ)
    wave_log="$log_root/${timestamp}_stage1_v5_supplement_${wave}_${ordinal_start}_${ordinal_end}_round_${retry_round}.log"
    echo "supplement_wave=$wave ordinal_start=$ordinal_start ordinal_end=$ordinal_end retry_round=$retry_round log=$wave_log"
    set +e
    ./scripts/cci_run.sh \
      python scripts/certify_stage1_v5_paths.py \
      --wave "$wave" --workers "$workers" --port-base 32000 \
      --max-attempts 3 --ordinal-start "$ordinal_start" \
      --ordinal-end "$ordinal_end" \
      2>&1 | tee "$wave_log"
    command_status=${PIPESTATUS[0]}
    set -e
    echo "supplement_wave=$wave ordinal_start=$ordinal_start ordinal_end=$ordinal_end retry_round=$retry_round exit_status=$command_status"
    if (( command_status == 0 )); then
      completed=true
      break
    fi
    sleep 10
  done
  if [[ "$completed" != true ]]; then
    echo "supplement wave $wave range $ordinal_start..$ordinal_end still has operational failures after three exact resumptions" >&2
    return 2
  fi
}

echo "supplemental_capacity_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
run_wave targeted_fast_world 1 1024 12
run_wave certification_spare 1 1200 12
echo "supplemental_capacity_completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
