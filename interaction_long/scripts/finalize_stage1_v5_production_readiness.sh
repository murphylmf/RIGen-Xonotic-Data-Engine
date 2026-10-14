#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
log_root="$root/logs"
main_phase_log=${STAGE1_V5_MAIN_PHASE_LOG:-"$log_root/20260727T151000Z_stage1_v5_main_path_phase.log"}
distributed_completion_root=${STAGE1_V5_DISTRIBUTED_COMPLETION_ROOT:-}
distributed_run_fingerprint=${STAGE1_V5_DISTRIBUTED_RUN_FINGERPRINT:-}
distributed_index_merge_report=${STAGE1_V5_DISTRIBUTED_INDEX_MERGE_REPORT:-}
distributed_shard_count=${STAGE1_V5_DISTRIBUTED_SHARD_COUNT:-32}
formal_root="$root/manifests/stage1_foundation_v5_formal"
runtime_build_tag=capture-7e8310b0d0c1-x86_64
compatibility_audit="$root/stage1_path_certification_v5/compatibility/b40e26fd4e33_to_7e8310b0d0c1/AUDIT.json"
mkdir -p "$log_root"
cd "$root"
export XONOTIC_BUILD_GLOB="build/$runtime_build_tag"

[[ -r "$compatibility_audit" ]] || {
  echo "final runtime compatibility audit is missing: $compatibility_audit" >&2
  exit 66
}
python3 - "$compatibility_audit" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf-8"))
scope = audit.get("authorization_scope") or {}
checks = {
    "passed": audit.get("passed") is True,
    "certificate_source": scope.get("certificate_source_commit")
    == "b40e26fd4e33b18b2002bf24beb6a78cef5fac96",
    "runtime_source": scope.get("runtime_source_commit")
    == "7e8310b0d0c135774f5cfbdb08122eec1f12c99b",
    "exact_scope": scope.get("kind")
    == "exact_commit_pair_and_certificate_index",
}
if not all(checks.values()):
    raise SystemExit(f"runtime compatibility audit failed: {checks}")
PY

[[ "$distributed_shard_count" =~ ^[1-9][0-9]*$ ]] &&
  (( distributed_shard_count <= 999 )) || {
  echo "STAGE1_V5_DISTRIBUTED_SHARD_COUNT must be in 1..999" >&2
  exit 64
}

main_phase_active() {
  pgrep -f '[c]ertify_stage1_v5_main_path_phase.sh' >/dev/null
}

path_certifier_active() {
  pgrep -f '[p]ython scripts/certify_stage1_v5_paths.py' >/dev/null
}

echo "readiness_finalize_wait_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [[ -n "$distributed_completion_root" ]]; then
  [[ -n "$distributed_run_fingerprint" ]] || {
    echo "distributed run fingerprint is missing" >&2
    exit 64
  }
  python3 - "$distributed_completion_root" \
    "$distributed_run_fingerprint" "$distributed_shard_count" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
fingerprint = sys.argv[2]
shard_count = int(sys.argv[3])
rows = []
for index in range(shard_count):
    path = root / f"shard-{index:03d}-of-{shard_count:03d}.json"
    if not path.is_file():
        raise SystemExit(f"distributed completion marker missing: {path}")
    row = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "schema": row.get("schema_version")
        == "xonotic-stage1-v5-distributed-certification-worker-v1",
        "fingerprint": row.get("run_fingerprint") == fingerprint,
        "shard_index": row.get("shard_index") == index,
        "shard_count": row.get("shard_count") == shard_count,
        "terminal": row.get("expected_terminal_prototypes", 0) > 0,
    }
    if not all(checks.values()):
        raise SystemExit(f"invalid distributed marker {path}: {checks}")
    rows.append(row)
print(
    "distributed_certification_markers=pass "
    f"workers={len(rows)} "
    f"terminal={sum(row['expected_terminal_prototypes'] for row in rows)}"
)
PY
  if path_certifier_active; then
    echo "path certifier still active after distributed barrier" >&2
    exit 2
  fi
  [[ -r "$distributed_index_merge_report" ]] || {
    echo "distributed certificate-index merge report is missing" >&2
    exit 2
  }
  python3 - "$distributed_index_merge_report" \
    "$distributed_run_fingerprint" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
fingerprint = sys.argv[2]
report = json.loads(report_path.read_text(encoding="utf-8"))
root = Path.cwd()
index_path = root / report["index_path"]
checks = {
    "schema": report.get("schema_version")
    == "xonotic-stage1-v5-certificate-index-merge-v1",
    "passed": report.get("passed") is True,
    "fingerprint": report.get("run_fingerprint") == fingerprint,
    "distributed": isinstance(report.get("distributed"), dict),
    "coverage": (
        (report.get("distributed") or {}).get(
            "expected_terminal_prototypes"
        )
        == (report.get("distributed") or {}).get(
            "observed_terminal_prototypes"
        )
    ),
    "index_exists": index_path.is_file(),
}
if index_path.is_file():
    checks["index_hash"] = (
        hashlib.sha256(index_path.read_bytes()).hexdigest()
        == report.get("index_sha256")
    )
if not all(checks.values()):
    raise SystemExit(
        f"invalid distributed certificate-index merge: {checks}"
    )
print(
    "distributed_certificate_index_merge=pass "
    f"rows={report['index_rows']}"
)
PY
else
  while main_phase_active || path_certifier_active; do
    sleep 30
  done

  if [[ ! -r "$main_phase_log" ]] ||
     ! grep -q '^main_path_phase_completed_utc=' "$main_phase_log"; then
    echo "Stage-1 v5 main path phase did not complete successfully: $main_phase_log" >&2
    exit 2
  fi
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
formal_log="$log_root/${timestamp}_stage1_v5_formal_manifest.log"
./scripts/cci_run.sh \
  python scripts/prepare_stage1_v5_manifests.py formal \
  2>&1 | tee "$formal_log"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
resume_log="$log_root/${timestamp}_stage1_v5_formal_resume_verification.log"
./scripts/cci_run.sh \
  python scripts/prepare_stage1_v5_manifests.py formal \
  2>&1 | tee "$resume_log"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
integrity_log="$log_root/${timestamp}_stage1_v5_formal_integrity.log"
./scripts/cci_run.sh python - "$formal_root" <<'PY' 2>&1 | tee "$integrity_log"
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
metadata_path = root / "MANIFEST_METADATA.json"
audit_path = root / "MANIFEST_AUDIT.json"
metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
audit = json.loads(audit_path.read_text(encoding="utf-8"))

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()

checks = {
    "audit_passed": audit.get("passed") is True,
    "primary_rows": metadata["primary"]["rows"] == 60_000,
    "replenishment_rows": metadata["replenishment"]["rows"] == 12_000,
    "shard_count": metadata["shard_count"] == 32,
    "primary_shards": len(metadata["primary"]["shards"]) == 32,
    "replenishment_shards": len(metadata["replenishment"]["shards"]) == 32,
    "primary_hash": digest(root / "input.jsonl")
    == metadata["primary"]["sha256"],
    "replenishment_hash": digest(root / "replenishment.jsonl")
    == metadata["replenishment"]["sha256"],
    "runtime_lock_hash": digest(root / "RUNTIME_CODE_LOCK.sha256")
    == metadata["runtime_code_lock"]["sha256"],
}
for wave in ("primary", "replenishment"):
    for shard in metadata[wave]["shards"]:
        path = Path.cwd() / shard["path"]
        checks[f"{wave}_shard_{shard['shard_index']:03d}"] = (
            digest(path) == shard["sha256"]
        )
report = {
    "schema_version": "xonotic-stage1-v5-final-integrity-v1",
    "passed": all(checks.values()),
    "checks": checks,
    "metadata_sha256": digest(metadata_path),
    "audit_sha256": digest(audit_path),
}
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if report["passed"] else 2)
PY

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
tests_log="$log_root/${timestamp}_stage1_v5_final_tests.log"
./scripts/cci_run.sh \
  pytest -q \
  tests/test_stage1_production_preflight.py \
  tests/test_h200_takeover.py \
  tests/test_stage1_reusable.py \
  2>&1 | tee "$tests_log"

bash -n \
  scripts/cci_node_bootstrap.sh \
  scripts/cci_node_preflight.sh \
  scripts/run_stage1_32x1_worker.sh \
  scripts/finalize_stage1_v5_route_phase.sh \
  scripts/certify_stage1_v5_main_path_phase.sh \
  scripts/certify_stage1_v5_supplemental_capacity.sh \
  scripts/resume_stage1_v5_main_after_supplement.sh \
  scripts/launch_stage1_v5_certification_worker_logged.sh \
  scripts/run_stage1_v5_certification_32x1_worker.sh \
  scripts/submit_stage1_v5_certification_sensecore_32x1.sh \
  scripts/submit_stage1_sensecore_32x1.sh \
  scripts/finalize_stage1_v5_production_readiness.sh
./scripts/cci_run.sh \
  python -m py_compile \
  scripts/certify_stage1_v5_paths.py \
  scripts/certify_stage1_v5_routes.py \
  scripts/merge_stage1_v5_certificate_shards.py \
  scripts/audit_stage1_v5_runtime_compatibility.py \
  scripts/prepare_stage1_v5_manifests.py \
  scripts/run_stage1_manifest_shard.py \
  scripts/stage1_32x1_status.py

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
preflight_log="$log_root/${timestamp}_stage1_v5_node_preflight.log"
./scripts/cci_node_preflight.sh 2>&1 | tee "$preflight_log"

echo "readiness_finalize_completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
