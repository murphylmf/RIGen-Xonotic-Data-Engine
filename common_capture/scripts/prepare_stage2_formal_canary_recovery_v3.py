                      
"""Retry only V2 slots blocked by the sparse-event runtime schema bug."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage2_formal_design as design              
import xonotic_capture as capture              


SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_formal_canary_recovery_v2/input.jsonl"
)
SOURCE_REJECTS = (
    ROOT
    / "stage2_formal_canary_recovery_v2_output/manifests/shards"
    / "shard-000-of-001/rejects.jsonl"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_formal_canary_recovery_v3"
SCHEMA = "xonotic-stage2-formal-canary-recovery-manifest-v3"
FORMAL_RUNTIME = ROOT / "scripts/xonotic_stage2_causal_formal.py"


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


def frozen_action_geometry(row: dict) -> dict:
    return {
        key: row[key]
        for key in (
            "map",
            "gametype",
            "weapon",
            "enemy_model",
            "enemy_skin",
            "enemy_color",
            "player",
            "enemy",
            "enemy_policy",
            "initial_screen_design",
            "causal_design",
        )
    }


def materialize() -> list[dict]:
    source_by_id = {
        row["episode_id"]: row
        for row in capture.load_jsonl(SOURCE_MANIFEST)
    }
    rejects = [
        row
        for row in capture.load_jsonl(SOURCE_REJECTS)
        if row.get("terminal") is True
    ]
    if len(rejects) != 3 or any(
        row.get("reason") != "KeyError"
        or str(row.get("detail")) != "'target'"
        for row in rejects
    ):
        raise capture.CaptureFailure(
            "stage2_formal_recovery_v3_unexpected_terminal_set",
            capture.canonical_json(
                [
                    {
                        "episode_id": row.get("episode_id"),
                        "reason": row.get("reason"),
                        "detail": row.get("detail"),
                    }
                    for row in rejects
                ]
            ),
        )
    pair_by_id = {
        row["episode_id"]: row for row in design.preflight_pairs()
    }
    rows: list[dict] = []
    for rejected in sorted(rejects, key=lambda row: row["episode_id"]):
        source = source_by_id[rejected["episode_id"]]
        source_design = source["formal_design"]
        pair = pair_by_id[source_design["source_pair_episode_id"]]
        replacement = design.stationary_scenario(
            cohort="s2fcv1x3",
            ordinal=int(source_design["ordinal"]),
            weapon=source["weapon"],
            outcome_recipe=source_design["outcome_recipe"],
            arm=source_design["arm"],
            pair=pair,
            appearance={
                "model": source["enemy_model"],
                "skin": source["enemy_skin"],
            },
            formal_collection=False,
            canary_authorization=None,
        )
        if frozen_action_geometry(replacement) != frozen_action_geometry(
            source
        ):
            raise capture.CaptureFailure(
                "stage2_formal_recovery_v3_action_geometry_changed",
                source["episode_id"],
            )
        logical_id = source["operational_replacement"]["replacement_for"]
        replacement["operational_replacement"] = {
            "schema_version": "xonotic-operational-replacement-v1",
            "replacement_for": logical_id,
            "previous_failed_artifact": source["episode_id"],
            "reason": "formal_runtime_sparse_event_union_schema_fix",
            "source_pair_certification_required": True,
            "source_pair_changed": source["operational_replacement"][
                "source_pair_changed"
            ],
            "outcome_used_for_replacement": False,
            "runtime_action_fallback": False,
            "runtime_geometry_fallback": False,
            "action_geometry_identical_to_previous_attempt": True,
        }
        replacement["assigned_shard"] = 0
        replacement["shard_count"] = 1
        rows.append(replacement)
    text = design.canonical_lines(rows)
    digest = design.sha256_text(text)
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": SCHEMA,
        "source_commit": design.source_commit(),
        "data_spec_sha256": design.data_spec_sha256(),
        "rows": len(rows),
        "shard_count": 1,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "logical_canary_total": 96,
        "recovery_lanes": 8,
        "formal_runtime": str(FORMAL_RUNTIME.relative_to(ROOT)),
        "formal_runtime_sha256": capture.sha256_file(FORMAL_RUNTIME),
        "outcome_used_for_replacement": False,
        "action_geometry_changed": False,
        "planned_outcome_distribution": dict(
            Counter(
                row["formal_design"]["outcome_recipe"] for row in rows
            )
        ),
        "input_sha256": digest,
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
                "outcomes": dict(
                    Counter(
                        row["formal_design"]["outcome_recipe"]
                        for row in rows
                    )
                ),
                "formal_runtime_sha256": capture.sha256_file(
                    FORMAL_RUNTIME
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
