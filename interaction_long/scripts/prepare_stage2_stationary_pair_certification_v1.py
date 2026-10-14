                      
"""Prepare a bounded live certification of the 63 accepted preflight pairs."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage2_formal_design as design              
import xonotic_capture as capture              


OUTPUT_ROOT = ROOT / "manifests/stage2_stationary_pair_certification_v1"
SCHEMA = "xonotic-stage2-stationary-pair-certification-manifest-v1"


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


def materialize() -> list[dict]:
    appearances = design.official_appearances()
    rows: list[dict] = []
    for ordinal, pair in enumerate(design.preflight_pairs()):
        weapon = design.WEAPONS[ordinal % len(design.WEAPONS)]
        row = design.stationary_scenario(
            cohort="s2spcv1",
            ordinal=ordinal,
            weapon=weapon,
            outcome_recipe="no_fire",
            arm="visible_no_fire",
            pair=pair,
            appearance=appearances[ordinal % len(appearances)],
            formal_collection=False,
            canary_authorization=None,
        )
        row["candidate_kind"] = "stage2_stationary_pair_certification_v1"
        row["candidate_status"] = "pending_live_fail_closed_pair_qa"
        row["training_stage"] = "stage2_pair_certification_only"
        row["split"] = "stage2_weapon_balanced_nontraining_review"
        row["assigned_shard"] = 0
        row["shard_count"] = 1
        rows.append(row)
    text = design.canonical_lines(rows)
    digest = design.sha256_text(text)
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": SCHEMA,
        "source_commit": design.source_commit(),
        "data_spec_sha256": capture.sha256_file(design.DATA_SPEC),
        "rows": len(rows),
        "shard_count": 1,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "purpose": (
            "bounded live safety certification after stationary canary "
            "proved anchor-only preflight insufficient"
        ),
        "outcome_used_for_admission": False,
        "input_sha256": digest,
        "distance_distribution": dict(
            Counter(row["formal_design"]["distance_bin"] for row in rows)
        ),
        "map_distribution": dict(Counter(row["map"] for row in rows)),
        "review": {
            "rows": len(rows),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "rows": len(rows),
                    "path": str(shard_path.relative_to(ROOT)),
                    "sha256": digest,
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
                "maps": len({row["map"] for row in rows}),
                "distances": dict(
                    Counter(
                        row["formal_design"]["distance_bin"]
                        for row in rows
                    )
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
