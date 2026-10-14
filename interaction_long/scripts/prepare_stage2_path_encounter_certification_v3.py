                      
"""Build one fresh-seed jumping certificate with a peripheral base view."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage2_causal_manifests as bootstrap              
import prepare_stage2_path_encounter_certification as v1              
import xonotic_capture as capture              
import xonotic_stage1_routes as routes              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
ROUTE_ID = "s1route_11563"
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_path_encounter_certification_v3"
)


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
    _, appearances = bootstrap.load_inputs()
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    record = v1.route_record(ROUTE_ID)
    plan = routes.effective_plan(ROUTE_ID)
    pair = record["compatible_enemy_pairs"][0]
    states = pd.read_parquet(
        record["calibration_states_path"]
    ).sort_values("server_tick")
    initial_angles = states.iloc[0]["pre.angles"]
    seed = int(
        (
            ROOT / record["frozen_actions_path"]
        ).read_text(encoding="utf-8").splitlines()[0].split(",", 1)[1]
    )
    source_pair = {
        "map": record["map"],
        "gametype": record["gametype"],
        "episode_id": pair["source_probe"],
        "distance_bin": pair["distance_bin"],
        "player_origin": pair["player_origin"],
        "enemy_origin": pair["enemy_origin"],
    }
    row = bootstrap.scenario_row(
        episode_id=f"s2pathcertv3_01_{ROUTE_ID}",
        group_id="s2pathcertv3_g01",
        pair=source_pair,
        appearance=appearances[9],
        weapon="MachineGun",
        policy="visible_no_response",
        seed=seed,
        motion_name="stationary",
        motion_mode=0,
        motion_distance=0.0,
        assigned_shard=0,
        shard_count=1,
        source_commit=source_commit,
        candidate_kind="path_encounter_certification_v3",
        weapon_mechanism_mode_eligible=True,
    )
    target_yaw, _ = causal.yaw_pitch_toward(
        row["player"]["origin"], row["enemy"]["origin"]
    )
    original_target_delta = causal.angle_delta(
        target_yaw, float(initial_angles[1])
    )
    desired_screen_error = math.copysign(
        40.0, original_target_delta
    )
    desired_initial_yaw = causal.wrap_angle(
        target_yaw - desired_screen_error
    )
    base_yaw_offset = causal.angle_delta(
        desired_initial_yaw, float(initial_angles[1])
    )
    row.update(
        {
            "schema_version": causal.SCENARIO_SCHEMA_V3,
            "action_program": causal.ACTION_PROGRAM_V3,
            "map_region_id": record["map_region_id"],
            "route_group_id": record["route_group_id"],
            "route_plan": plan,
            "frozen_actions_path": record["frozen_actions_path"],
            "frozen_actions_sha256": record[
                "frozen_actions_sha256"
            ],
            "training_stage": (
                "stage2_bounded_path_encounter_certification_v3_only"
            ),
            "formal_collection_authorized": False,
            "training_admitted": False,
            "supersedes_cohort": (
                "stage2_path_encounter_certification_v2"
            ),
        }
    )
    row["player"]["yaw"] = round(desired_initial_yaw, 6)
    row["player"]["pitch"] = round(float(initial_angles[0]), 6)
    design = row["causal_design"]
    design.update(
        {
            "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V3,
            "base_player_program": "certified_route_replay",
            "player_motion_class": "jumping",
            "player_reference": (
                "manifest_frozen_certified_route_states"
            ),
            "base_view_yaw_offset_deg": round(
                base_yaw_offset, 6
            ),
            "base_view_pitch_offset_deg": 0.0,
            "aim_schedule": causal.default_aim_schedule(
                "visible_no_response"
            ),
            "secondary_mechanism": None,
        }
    )
    row["player_path_source"] = v1.path_source(
        record=record,
        plan=plan,
        scenario=row,
    )
    row["policy_labels"].update(
        {
            "player_motion_class": "jumping",
            "interaction_channel": "primary",
            "base_view_policy": (
                "constant_manifest_frozen_peripheral_40deg"
            ),
            "initial_target_screen_error_deg": (
                desired_screen_error
            ),
        }
    )
    row["exogenous_contract_sha256"] = (
        causal.exogenous_contract_sha256(row)
    )
    causal.validate_scenario_contract(row)
    capture.validate_scenario_assets(row)
    causal.causal_action_rows(row)
    rows = [row]
    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-path-encounter-certification-manifest-v3"
        ),
        "source_commit": source_commit,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "route_id": ROUTE_ID,
        "seed": seed,
        "base_view_yaw_offset_deg": base_yaw_offset,
        "review": {
            "rows": 1,
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard_path),
                    "rows": 1,
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
                "episode_id": rows[0]["episode_id"],
                "seed": rows[0]["seed"],
                "base_view_yaw_offset_deg": rows[0][
                    "causal_design"
                ]["base_view_yaw_offset_deg"],
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
