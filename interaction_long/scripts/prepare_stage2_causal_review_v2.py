                      
"""Version the 70-row review onto the unbiased Stage-2 v2 QA contract."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
SOURCE = (
    ROOT / "manifests/stage2_causal_bootstrap_v5/review/input.jsonl"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_causal_review_v2"


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_manifest_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def materialize() -> list[dict[str, Any]]:
    old_rows = capture.load_jsonl(SOURCE)
    rows: list[dict[str, Any]] = []
    group_map: dict[str, str] = {}
    for source in old_rows:
        row = copy.deepcopy(source)
        old_group = row["counterfactual_group_id"]
        if old_group not in group_map:
            group_map[old_group] = old_group.replace(
                "s2review_", "s2reviewv2_"
            )
        row.update(
            {
                "schema_version": causal.SCENARIO_SCHEMA_V2,
                "episode_id": row["episode_id"].replace(
                    "s2review_", "s2reviewv2_"
                ),
                "anchor_id": row["anchor_id"].replace(
                    "s2review_", "s2reviewv2_"
                ),
                "counterfactual_group_id": group_map[old_group],
                "action_program": causal.ACTION_PROGRAM_V2,
                "candidate_kind": "counterfactual_review_v2",
                "training_stage": (
                    "stage2_bounded_causal_review_v2_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
            }
        )
        row["causal_design"]["schema_version"] = (
            causal.CAUSAL_DESIGN_SCHEMA_V2
        )
        row["causal_design"]["secondary_mechanism"] = None
        row["policy_labels"]["interaction_channel"] = "primary"
        row["supersession_contract"] = {
            "schema_version": "xonotic-stage2-review-supersession-v1",
            "supersedes_manifest": str(SOURCE),
            "supersedes_manifest_sha256": capture.sha256_file(SOURCE),
            "reason": (
                "v1 impact-required gate rejected valid authoritative "
                "miss outcomes"
            ),
            "geometry_weapon_policy_mutated": False,
            "runtime_fallback": False,
        }
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        rows.append(row)

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": "xonotic-stage2-causal-review-manifest-v2",
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "model_action_schema_version": (
            capture.MODEL_ACTION_SCHEMA_VERSION
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "supersedes_manifest": str(SOURCE),
        "supersedes_manifest_sha256": capture.sha256_file(SOURCE),
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(group_map),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard_path),
                    "rows": len(rows),
                    "sha256": hashlib.sha256(
                        text.encode("utf-8")
                    ).hexdigest(),
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
        json.dumps(
            {
                "rows": len(rows),
                "groups": len(
                    {row["counterfactual_group_id"] for row in rows}
                ),
                "output_root": str(OUTPUT_ROOT),
                "source_manifest_sha256": capture.sha256_file(SOURCE),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
