                      
"""Build a bounded primary-fire telemetry outcome calibration matrix."""

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
SOURCE = ROOT / "manifests/stage2_causal_review_v2/input.jsonl"
OUTPUT_ROOT = ROOT / "manifests/stage2_outcome_calibration_v1"
POLICIES = (
    "visible_no_response",
    "pass_offset",
    "delayed_acquisition",
    "sustained_tracking",
)
FIRE_TICKS = {
    "visible_no_response": [],
    "pass_offset": [176, 256],
    "delayed_acquisition": [176],
    "sustained_tracking": [88, 176, 264],
}
                                                                           
                                                                          
                                                                              
ENEMY_HEALTH_PRIOR = {
    "Blaster": 50,
    "Shotgun": 100,
    "MachineGun": 40,
    "Mortar": 120,
    "Electro": 150,
    "Crylink": 120,
    "Vortex": 160,
    "Hagar": 120,
    "Devastator": 160,
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


def source_rows_by_weapon() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in capture.load_jsonl(SOURCE):
        if (
            row["causal_design"]["aim_policy"]
            == "sustained_tracking"
            and row["weapon"] not in result
        ):
            result[row["weapon"]] = row
    if set(result) != set(ENEMY_HEALTH_PRIOR):
        raise capture.CaptureFailure(
            "stage2_outcome_calibration_weapon_sources",
            capture.canonical_json(
                {
                    "expected": sorted(ENEMY_HEALTH_PRIOR),
                    "actual": sorted(result),
                }
            ),
        )
    return result


def materialize() -> list[dict[str, Any]]:
    sources = source_rows_by_weapon()
    rows: list[dict[str, Any]] = []
    for weapon_ordinal, weapon in enumerate(
        ENEMY_HEALTH_PRIOR, 1
    ):
        source = sources[weapon]
        group_id = f"s2outcomev1_g{weapon_ordinal:02d}_{weapon.lower()}"
        seed = 16_000_000 + weapon_ordinal
        for policy_ordinal, policy in enumerate(POLICIES, 1):
            row = copy.deepcopy(source)
            schedule = causal.default_aim_schedule(policy)
            if policy == "pass_offset":
                schedule["fire_yaw_offset_deg"] = 20.0
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V3,
                    "action_program": causal.ACTION_PROGRAM_V3,
                    "episode_id": (
                        f"{group_id}_p{policy_ordinal:02d}_{policy}"
                    ),
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "seed": seed,
                    "category": f"stage2_outcome_calibration_{policy}",
                    "candidate_kind": (
                        "stage2_primary_outcome_calibration_v1"
                    ),
                    "candidate_status": (
                        "bounded_telemetry_rebucket_candidate"
                    ),
                    "training_stage": (
                        "stage2_bounded_outcome_calibration_v1_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "canary_role": (
                        f"stage2_outcome_calibration_{weapon.lower()}_"
                        f"{policy}"
                    ),
                    "expects_sound": policy
                    != "visible_no_response",
                }
            )
            row["enemy"]["health"] = ENEMY_HEALTH_PRIOR[weapon]
            row["enemy"]["armor"] = 0
            design = row["causal_design"]
            design.update(
                {
                    "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V3,
                    "aim_policy": policy,
                    "aim_schedule": schedule,
                    "acquisition_start_output_tick": int(
                        schedule.get("response_start_output_tick")
                        or 0
                    ),
                    "fire_output_ticks": list(FIRE_TICKS[policy]),
                    "interaction_channel": "primary",
                    "secondary_mechanism": None,
                    "base_player_program": "stationary",
                    "actual_outcome_source": (
                        "authoritative_telemetry_only"
                    ),
                    "intended_outcome_is_acceptance_gate": False,
                }
            )
            row["policy_labels"].update(
                {
                    "aim_policy": policy,
                    "interaction_channel": "primary",
                    "outcome_assignment": (
                        "post_capture_authoritative_telemetry_rebucket"
                    ),
                }
            )
            row["acceptance"]["actual_outcome"] = None
            row["acceptance"]["actual_outcome_rebucket_required"] = True
            row["outcome_calibration_design"] = {
                "schema_version": (
                    "xonotic-stage2-outcome-calibration-design-v1"
                ),
                "candidate_generation_health_prior": (
                    ENEMY_HEALTH_PRIOR[weapon]
                ),
                "candidate_generation_arm": policy,
                "actual_outcome_used_for_episode_acceptance": False,
                "actual_outcome_source": "authoritative_telemetry_only",
                "post_capture_rebucket_required": True,
            }
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            causal.validate_scenario_contract(row)
            capture.validate_scenario_assets(row)
            actions = causal.causal_action_rows(row)
            expected_fire = policy != "visible_no_response"
            if bool(sum(action["primary"] for action in actions)) != (
                expected_fire
            ):
                raise capture.CaptureFailure(
                    "stage2_outcome_calibration_fire_contract",
                    row["episode_id"],
                )
            rows.append(row)

    for group_id in {
        row["counterfactual_group_id"] for row in rows
    }:
        members = [
            row
            for row in rows
            if row["counterfactual_group_id"] == group_id
        ]
        if (
            len(members) != len(POLICIES)
            or len(
                {
                    row["exogenous_contract_sha256"]
                    for row in members
                }
            )
            != 1
        ):
            raise capture.CaptureFailure(
                "stage2_outcome_calibration_group_contract",
                group_id,
            )

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-outcome-calibration-manifest-v1"
        ),
        "source_manifest": str(SOURCE.relative_to(ROOT)),
        "source_manifest_sha256": capture.sha256_file(SOURCE),
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "actual_outcome_used_for_episode_acceptance": False,
        "actual_outcome_source": "authoritative_telemetry_only",
        "candidate_generation_health_priors": ENEMY_HEALTH_PRIOR,
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(ENEMY_HEALTH_PRIOR),
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
                    {
                        row["counterfactual_group_id"]
                        for row in rows
                    }
                ),
                "weapons": sorted({row["weapon"] for row in rows}),
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
