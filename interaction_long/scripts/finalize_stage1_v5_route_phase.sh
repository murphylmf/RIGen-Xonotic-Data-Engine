#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
log_root="$root/logs"
summary="$root/manifests/stage1_foundation_v5_certification/ROUTE_CERTIFICATION_SUMMARY.json"
mkdir -p "$log_root"
cd "$root"

route_certifier_active() {
  pgrep -f '[p]ython scripts/certify_stage1_v5_routes.py' >/dev/null
}

route_phase_complete() {
  [[ -r "$summary" ]] || return 1
  python3 - "$summary" <<'PY'
import json
import sys

report = json.loads(open(sys.argv[1], encoding="utf-8").read())
raise SystemExit(0 if report.get("complete") is True else 1)
PY
}

echo "route_finalize_wait_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
while route_certifier_active; do
  sleep 30
done




for retry_round in 1 2 3; do
  if route_phase_complete; then
    break
  fi
  timestamp=$(date -u +%Y%m%dT%H%M%SZ)
  retry_log="$log_root/${timestamp}_stage1_v5_route_operational_retry_${retry_round}.log"
  echo "route_retry_round=$retry_round log=$retry_log"
  set +e
  ./scripts/cci_run.sh \
    python scripts/certify_stage1_v5_routes.py --workers 12 \
    2>&1 | tee "$retry_log"
  command_status=${PIPESTATUS[0]}
  set -e
  echo "route_retry_round=$retry_round exit_status=$command_status"
done

if ! route_phase_complete; then
  echo "route phase still has pending/stale records after three operational retries" >&2
  exit 2
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
routes_log="$log_root/${timestamp}_stage1_v5_route_audit.log"
./scripts/cci_run.sh \
  python scripts/prepare_stage1_v5_manifests.py routes \
  2>&1 | tee "$routes_log"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
prototypes_log="$log_root/${timestamp}_stage1_v5_path_prototypes.log"
./scripts/cci_run.sh \
  python scripts/prepare_stage1_v5_manifests.py prototypes \
  2>&1 | tee "$prototypes_log"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
spares_log="$log_root/${timestamp}_stage1_v5_path_certification_spares.log"
./scripts/cci_run.sh \
  python scripts/prepare_stage1_v5_manifests.py spares \
  2>&1 | tee "$spares_log"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
fast_world_log="$log_root/${timestamp}_stage1_v5_fast_world_candidates.log"
./scripts/cci_run.sh \
  python scripts/prepare_stage1_v5_manifests.py fast-world \
  2>&1 | tee "$fast_world_log"

echo "route_finalize_completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
