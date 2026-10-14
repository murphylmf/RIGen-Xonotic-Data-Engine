                      
"""Run one immutable-manifest v15 tail lane from a frozen rebalance plan.

The audited 28-shard manifest is validated in full by the normal v15 runner.
Only afterwards is the row set narrowed to the disjoint candidate-key set in
one rebalance lane.  The normal runner then writes to a lane-private output
root and stops at the lane-specific accepted quota.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import run_stage2_short_42k_activeonly_v15_shard as v15


quota = v15.quota
pilot = v15.pilot
_validate_full_manifest = v15.validate_manifest
LANE_SCHEMA = "xonotic-stage2-short-v15-rebalance-lane-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lane() -> tuple[Path, dict[str, Any]]:
    raw_path = os.environ.get("STAGE2_REBALANCE_LANE_FILE", "")
    expected_sha256 = os.environ.get("STAGE2_REBALANCE_LANE_SHA256", "")
    expected_lane = os.environ.get("STAGE2_REBALANCE_LANE_ID", "")
    if not raw_path or not expected_sha256 or not expected_lane.isdigit():
        raise RuntimeError(
            "STAGE2_REBALANCE_LANE_FILE, STAGE2_REBALANCE_LANE_SHA256, "
            "and numeric STAGE2_REBALANCE_LANE_ID are required"
        )
    path = Path(raw_path).resolve()
    if not path.is_file():
        raise RuntimeError(f"missing rebalance lane file: {path}")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"rebalance lane hash mismatch: {actual_sha256}!={expected_sha256}"
        )
    lane = json.loads(path.read_text(encoding="utf-8"))
    if lane.get("schema_version") != LANE_SCHEMA:
        raise RuntimeError(f"unexpected rebalance lane schema: {lane.get('schema_version')}")
    if int(lane.get("lane_id", -1)) != int(expected_lane):
        raise RuntimeError(
            f"rebalance lane id mismatch: {lane.get('lane_id')}!={expected_lane}"
        )
    return path, lane


def validate_manifest(
    manifest_path: Path,
    metadata_path: Path,
    shard_index: int,
    shard_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, report = _validate_full_manifest(
        manifest_path, metadata_path, shard_index, shard_count
    )
    lane_path, lane = load_lane()
    keys = [str(value) for value in lane.get("candidate_sample_keys", [])]
    key_set = set(keys)
    target = int(lane.get("target_accepted_rows", -1))
    expected_key_digest = str(lane.get("candidate_sample_keys_sha256", ""))
    actual_key_digest = hashlib.sha256(
        ("\n".join(keys) + "\n").encode("utf-8")
    ).hexdigest()
    checks = {
        "category_always_visible": lane.get("category") == "always_visible",
        "original_shard_matches": int(lane.get("original_shard", -1))
        == shard_index,
        "source_manifest_matches": Path(str(lane.get("source_manifest", ""))).resolve()
        == manifest_path.resolve(),
        "source_manifest_hash_matches": lane.get("source_manifest_sha256")
        == sha256_file(manifest_path),
        "candidate_keys_nonempty": bool(keys),
        "candidate_keys_unique": len(keys) == len(key_set),
        "candidate_key_digest": expected_key_digest == actual_key_digest,
        "target_positive": target > 0,
        "target_within_lane_candidates": 0 < target <= len(keys),
    }
    full_rows_by_key = {str(row["sample_key"]): row for row in rows}
    checks["candidate_keys_in_source_manifest"] = key_set <= full_rows_by_key.keys()
    if not all(checks.values()):
        raise RuntimeError(f"v15 rebalance lane checks failed: {checks}")
    filtered_rows = [row for row in rows if str(row["sample_key"]) in key_set]
    if len(filtered_rows) != len(keys):
        raise RuntimeError(
            f"rebalance lane row mismatch: {len(filtered_rows)}!={len(keys)}"
        )
    report = dict(report)
    report["target_accepted_rows"] = target
    report["candidate_rows"] = len(filtered_rows)
    report["rebalance_lane"] = {
        "schema_version": LANE_SCHEMA,
        "lane_file": str(lane_path),
        "lane_file_sha256": sha256_file(lane_path),
        "lane_id": int(lane["lane_id"]),
        "original_shard": shard_index,
        "candidate_rows": len(filtered_rows),
        "target_accepted_rows": target,
        "checks": checks,
    }
    return filtered_rows, report


quota.validate_manifest = validate_manifest


def main() -> int:
    import run_stage2_motion_42k_activeonly_v13_multigpu as gpu_binding
    import sys

    gpu_binding.shard_runner = sys.modules[__name__]
    return gpu_binding.main()


if __name__ == "__main__":
    raise SystemExit(main())
