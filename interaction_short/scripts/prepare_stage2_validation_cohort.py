                      
"""Select a bounded motion + nine-weapon Stage-2 validation cohort."""

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
SOURCE_ROOT = ROOT / "manifests/stage2_causal_bootstrap_v5"
OUTPUT_ROOT = ROOT / "manifests/stage2_causal_validation_v2"
WEAPONS = (
    "Blaster",
    "Shotgun",
    "MachineGun",
    "Mortar",
    "Electro",
    "Crylink",
    "Vortex",
    "Hagar",
    "Devastator",
)
MOTION_SOURCE_PAIR = {
    "stationary": "preflight_pair_afterslime_close_r0_wp0086_wp0101",
    "lateral_patrol": (
        "preflight_pair_afterslime_close_r0_wp0086_wp0101"
    ),
    "approach_retreat": (
        "preflight_pair_techassault_extreme_r0_wp0032_wp0033"
    ),
    "stop_and_go": "preflight_pair_afterslime_close_r0_wp0086_wp0101",
}


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
    encounters = capture.load_jsonl(
        SOURCE_ROOT / "encounter_certification/input.jsonl"
    )
    review = capture.load_jsonl(SOURCE_ROOT / "review/input.jsonl")

    motion = []
    for policy_name, source_pair_id in MOTION_SOURCE_PAIR.items():
        candidates = [
            row
            for row in encounters
            if row["encounter_source"]["source_pair_episode_id"]
            == source_pair_id
            and row["enemy_policy"]["name"] == policy_name
        ]
        if len(candidates) != 1:
            raise capture.CaptureFailure(
                "stage2_motion_smoke_source_invalid",
                f"{policy_name}:{source_pair_id}:{len(candidates)}",
            )
        motion.append(copy.deepcopy(candidates[0]))
    if len(motion) != 4:
        raise capture.CaptureFailure(
            "stage2_motion_smoke_source_invalid", str(len(motion))
        )

    weapon = []
    for weapon_name in WEAPONS:
        candidates = [
            row
            for row in review
            if row["weapon"] == weapon_name
            and row["causal_design"]["aim_policy"]
            == "sustained_tracking"
        ]
        if not candidates:
            raise capture.CaptureFailure(
                "stage2_weapon_smoke_source_missing", weapon_name
            )
        selected = copy.deepcopy(candidates[0])
        selected["candidate_kind"] = "primary_weapon_mechanism_smoke"
        selected["canary_role"] = (
            f"stage2_primary_weapon_smoke_{weapon_name.lower()}"
        )
        weapon.append(selected)

    rows = motion + weapon
    for index, row in enumerate(rows):
        row["assigned_shard"] = 0
        row["shard_count"] = 1
        row["validation_ordinal"] = index
        row["training_stage"] = "stage2_bounded_validation_only"
        row["formal_collection_authorized"] = False
        row["training_admitted"] = False
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = (
        OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    )
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    source_commit = rows[0]["source_commit_required"]
    metadata = {
        "schema_version": "xonotic-stage2-validation-manifest-v2",
        "source_commit": source_commit,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "model_action_schema_version": (
            capture.MODEL_ACTION_SCHEMA_VERSION
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "validation": {
            "rows": len(rows),
            "motion_rows": len(motion),
            "weapon_rows": len(weapon),
        },
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
                "motion_rows": sum(
                    row["candidate_kind"]
                    == "encounter_prototype_certification"
                    for row in rows
                ),
                "weapons": sorted(
                    {
                        row["weapon"]
                        for row in rows
                        if row["candidate_kind"]
                        == "primary_weapon_mechanism_smoke"
                    }
                ),
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
