                      
"""Materialize the bounded stock-secondary Stage-2 mechanism cohort.

Blaster LT is last-weapon selection and Vortex LT is FOV zoom in the locked
stock balance, so both remain released under the v2 data spec.  The other
seven core weapons receive an explicit, weapon-specific treatment recipe.
"""

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
OUTPUT_ROOT = ROOT / "manifests/stage2_causal_secondary_validation_v1"


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
    source_rows = capture.load_jsonl(SOURCE)
    rows: list[dict[str, Any]] = []
    for ordinal, (weapon, mechanism) in enumerate(
        causal.SECONDARY_MECHANISMS.items(), 1
    ):
        matches = [
            row
            for row in source_rows
            if row["weapon"] == weapon
            and row["causal_design"]["aim_policy"]
            == "sustained_tracking"
        ]
        if not matches:
            raise capture.CaptureFailure(
                "stage2_secondary_source_missing", weapon
            )
        row = copy.deepcopy(matches[0])
        slug = weapon.lower()
        row.update(
            {
                "schema_version": causal.SCENARIO_SCHEMA_V2,
                "episode_id": f"s2secondary_{ordinal:02d}_{slug}",
                "anchor_id": f"s2secondary_{ordinal:02d}_{slug}_pair",
                "counterfactual_group_id": (
                    f"s2secondary_{ordinal:02d}_{slug}"
                ),
                "seed": 15_400_000 + ordinal,
                "action_program": causal.ACTION_PROGRAM_V2,
                "candidate_kind": (
                    "secondary_weapon_mechanism_smoke"
                ),
                "category": f"stage2_secondary_{slug}",
                "canary_role": f"stage2_secondary_{slug}",
                "training_stage": (
                    "stage2_bounded_secondary_validation_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "validation_ordinal": ordinal - 1,
            }
        )
        row["enemy_policy"]["policy_seed"] = row["seed"]
        design = row["causal_design"]
        design.update(
            {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V2,
                "interaction_channel": "secondary",
                "secondary_mechanism": mechanism,
                "fire_width_ticks": (
                    40 if mechanism == "hagar_load_release" else 2
                ),
                "secondary_launch_lead_ticks": (
                    32
                    if mechanism == "devastator_remote_detonation"
                    else None
                ),
            }
        )
        row["policy_labels"]["interaction_channel"] = "secondary"
        row["policy_labels"]["secondary_mechanism"] = mechanism
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
        "schema_version": (
            "xonotic-stage2-secondary-validation-manifest-v1"
        ),
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "model_action_schema_version": (
            capture.MODEL_ACTION_SCHEMA_VERSION
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "excluded_stock_secondary": causal.SECONDARY_EXCLUDED,
        "mechanisms": causal.SECONDARY_MECHANISMS,
        "review": {
            "rows": len(rows),
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
                "weapons": [row["weapon"] for row in rows],
                "excluded_stock_secondary": causal.SECONDARY_EXCLUDED,
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
