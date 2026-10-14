                      
"""Run a manifest shard with the versioned Stage-2 formal runtime.

The historical V4 runtime remains byte-for-byte pinned.  Importing this module
after the base shard runner replaces only the Stage-2 action/artifact provider
with the separately hashed formal runtime.
"""

from __future__ import annotations

import json
from pathlib import Path

import run_capture_manifest_shard as base
import xonotic_stage2_causal_formal as formal_stage2


base.stage2 = formal_stage2
capture = base.capture
_base_output_split_authorized = capture.output_split_authorized


def output_split_authorized(scenario: dict) -> bool:
    if scenario.get("formal_collection_authorized") is not True:
        return _base_output_split_authorized(scenario)
    return (
        scenario.get("split") == "causal_interaction"
        and scenario.get("dataset_role") == "causal_interaction"
        and scenario.get("training_stage") == "stage2"
        and scenario.get("training_admitted") is False
        and bool(scenario.get("formal_authorization_basis"))
        and scenario.get("source_commit_required")
        == (
            capture.build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip()
    )


def validate_manifest(
    path: Path,
    shard_index: int,
    shard_count: int,
    expected_source_commit: str | None = None,
) -> list[dict]:
    rows = capture.load_jsonl(path)
    ids = [str(row.get("episode_id", "")) for row in rows]
    if not rows or any(not episode_id for episode_id in ids):
        raise capture.CaptureFailure(
            "input_manifest_empty_or_invalid", str(path)
        )
    if len(ids) != len(set(ids)):
        raise capture.CaptureFailure("duplicate_episode_id", str(path))
    for row in rows:
        formal = row.get("formal_collection_authorized") is True
        checks = {
            "collection_policy": (
                row.get("split") in capture.NONTRAINING_SPLITS
                and row.get("formal_collection_authorized") is False
                if not formal
                else output_split_authorized(row)
            ),
            "training_admitted_false": row.get("training_admitted") is False,
            "assigned_shard": int(row.get("assigned_shard", -1))
            == shard_index,
            "shard_count": int(row.get("shard_count", -1))
            == shard_count,
            "source_commit": expected_source_commit is None
            or row.get("source_commit_required")
            == expected_source_commit,
        }
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "input_manifest_policy_failed",
                capture.canonical_json(
                    {"episode_id": row.get("episode_id"), "checks": checks}
                ),
            )
    return rows


def verify_manifest_metadata(
    metadata_path: Path,
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    expected_source_commit: str,
) -> str:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("formal_collection_authorized") is not True:
        return base._ORIGINAL_VERIFY_MANIFEST_METADATA(
            metadata_path,
            input_manifest,
            input_sha256,
            shard_index,
            shard_count,
            expected_source_commit,
        )
    shard_set = (metadata.get("shard_sets") or {}).get(str(shard_count)) or {}
    expected = next(
        (
            row
            for row in shard_set.get("shards", [])
            if int(row.get("shard_index", -1)) == shard_index
        ),
        None,
    )
    checks = {
        "source_commit": metadata.get("source_commit")
        == expected_source_commit,
        "formal_collection_authorized": metadata.get(
            "formal_collection_authorized"
        )
        is True,
        "training_admitted_false": metadata.get("training_admitted") is False,
        "shard_count": int(shard_set.get("shard_count", -1))
        == shard_count,
        "shard_declared": expected is not None,
    }
    if expected is not None:
        checks["shard_sha256"] = expected.get("sha256") == input_sha256
        checks["shard_filename"] = (
            Path(str(expected.get("path", ""))).name
            == input_manifest.name
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "manifest_metadata_mismatch",
            capture.canonical_json(checks),
        )
    return capture.sha256_file(metadata_path)


capture.output_split_authorized = output_split_authorized
base._ORIGINAL_VERIFY_MANIFEST_METADATA = base.verify_manifest_metadata
base.validate_manifest = validate_manifest
base.verify_manifest_metadata = verify_manifest_metadata


if __name__ == "__main__":
    raise SystemExit(base.main())
