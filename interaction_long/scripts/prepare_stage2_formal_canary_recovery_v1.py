                      
"""Build the immutable 8-lane recovery tail for the 96-row formal canary."""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage2_formal_design as design              
import xonotic_capture as capture              
import xonotic_stage2_causal_formal as formal              


MOVING_MANIFEST = ROOT / "manifests/stage2_formal_canary_v1/input.jsonl"
MOVING_REJECTS = (
    ROOT
    / "stage2_formal_canary_v1_output/manifests/shards"
    / "shard-000-of-001/rejects.jsonl"
)
EXTENSION_MANIFEST = (
    ROOT / "manifests/stage2_formal_stationary_extension_v1/input.jsonl"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_formal_canary_recovery_v1"
SCHEMA = "xonotic-stage2-formal-canary-recovery-manifest-v1"


def write_once_or_verify(path: Path, text: str) -> None:
    payload = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise capture.CaptureFailure(
                "immutable_manifest_conflict", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def terminal_ids() -> list[str]:
    rows = capture.load_jsonl(MOVING_REJECTS)
    ids = sorted(
        {
            str(row["episode_id"])
            for row in rows
            if row.get("terminal") is True
        }
    )
    if not ids:
        raise capture.CaptureFailure(
            "formal_canary_recovery_has_no_terminal_slots",
            str(MOVING_REJECTS),
        )
    return ids


def materialize() -> list[dict]:
    source_by_id = {
        str(row["episode_id"]): row
        for row in capture.load_jsonl(MOVING_MANIFEST)
    }
    replacements: list[dict] = []
    for old_id in terminal_ids():
        if old_id not in source_by_id:
            raise capture.CaptureFailure(
                "formal_canary_terminal_not_in_manifest", old_id
            )
        row = copy.deepcopy(source_by_id[old_id])
        new_id = f"{old_id}_technical_replacement_v1"
        row["episode_id"] = new_id
        row["operational_replacement"] = {
            "schema_version": "xonotic-operational-replacement-v1",
            "replacement_for": old_id,
            "reason": "terminal_live_client_timeout_at_12_lanes",
            "preserves_action_program": True,
            "preserves_geometry": True,
            "preserves_outcome_recipe": True,
            "outcome_used_for_replacement": False,
        }
        row["assigned_shard"] = 0
        row["shard_count"] = 1
        formal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        replacements.append(row)

    extension = capture.load_jsonl(EXTENSION_MANIFEST)
    rows = replacements + extension
    if len({str(row["episode_id"]) for row in rows}) != len(rows):
        raise capture.CaptureFailure(
            "formal_canary_recovery_duplicate_ids", str(len(rows))
        )
    input_text = design.canonical_lines(rows)
    input_sha256 = design.sha256_text(input_text)
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", input_text)
    write_once_or_verify(shard_path, input_text)
    metadata = {
        "schema_version": SCHEMA,
        "source_commit": design.source_commit(),
        "data_spec_sha256": capture.sha256_file(design.DATA_SPEC),
        "rows": len(rows),
        "shard_count": 1,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "nontraining_formal_shaped_canary": True,
        "logical_canary_total": 96,
        "twelve_lane_failed": True,
        "recovery_lanes": 8,
        "technical_replacement_rows": len(replacements),
        "stationary_extension_rows": len(extension),
        "outcome_recipe_is_individual_admission_gate": False,
        "planned_outcome_distribution": dict(
            Counter(
                (
                    row.get("formal_canary_design")
                    or row.get("formal_design")
                    or {}
                ).get("outcome_recipe")
                for row in rows
            )
        ),
        "input_sha256": input_sha256,
        "review": {
            "rows": len(rows),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "rows": len(rows),
                    "path": str(shard_path.relative_to(ROOT)),
                    "sha256": input_sha256,
                }
            ],
        },
    }
    write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        capture.canonical_json(
            {
                "manifest": str(OUTPUT_ROOT / "input.jsonl"),
                "rows": len(rows),
                "technical_replacements": sum(
                    "operational_replacement" in row for row in rows
                ),
                "stationary_extension": sum(
                    "stationary_preflight_source" in row for row in rows
                ),
                "lanes": 8,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
