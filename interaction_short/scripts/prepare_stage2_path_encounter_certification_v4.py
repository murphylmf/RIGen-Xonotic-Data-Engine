                      
"""Build a new-seed jumping certificate with declared overlay tolerance."""

from __future__ import annotations

import csv
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
SEED = 14_511_563
POSITION_TOLERANCE = 16.0
EPISODE_PREFIX = "s2pathcertv4"
GROUP_ID = "s2pathcertv4_g01"
CANDIDATE_KIND = "path_encounter_certification_v4"
TRAINING_STAGE = (
    "stage2_bounded_path_encounter_certification_v4_only"
)
MANIFEST_SCHEMA = (
    "xonotic-stage2-path-encounter-certification-manifest-v4"
)
PLAYER_PATH_SOURCE_SCHEMA = causal.PLAYER_PATH_SOURCE_SCHEMA_V3
OVERLAY_REPLAY_TOLERANCE_BASIS: str | None = None
SUPERSEDES_COHORT = "stage2_path_encounter_certification_v3"
SUPERSESSION_REASON: str | None = None
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_path_encounter_certification_v4"
)
DERIVED_ACTIONS = (
    ROOT
    / "stage2_routes/derived/"
    f"{ROUTE_ID}_seed{SEED}/frozen_actions.csv"
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


def derived_actions(record: dict[str, Any]) -> tuple[str, str]:
    source = ROOT / record["frozen_actions_path"]
    lines = source.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("#seed,"):
        raise capture.CaptureFailure(
            "stage2_derived_action_source_invalid", str(source)
        )
    text = "\n".join([f"#seed,{SEED}", *lines[1:]]) + "\n"
    write_once_or_verify(DERIVED_ACTIONS, text)
    original = list(csv.DictReader(lines[1:]))
    derived = list(csv.DictReader(text.splitlines()[1:]))
    if (
        capture.physical_action_sha256(original)
        != capture.physical_action_sha256(derived)
    ):
        raise capture.CaptureFailure(
            "stage2_derived_physical_action_drift"
        )
    return (
        str(DERIVED_ACTIONS.relative_to(ROOT)),
        capture.sha256_file(DERIVED_ACTIONS),
    )


def materialize() -> list[dict[str, Any]]:
    _, appearances = bootstrap.load_inputs()
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    record = v1.route_record(ROUTE_ID)
    plan = routes.effective_plan(ROUTE_ID)
    action_path, action_sha = derived_actions(record)
    pair = record["compatible_enemy_pairs"][0]
    states = pd.read_parquet(
        record["calibration_states_path"]
    ).sort_values("server_tick")
    initial_angles = states.iloc[0]["pre.angles"]
    source_pair = {
        "map": record["map"],
        "gametype": record["gametype"],
        "episode_id": pair["source_probe"],
        "distance_bin": pair["distance_bin"],
        "player_origin": pair["player_origin"],
        "enemy_origin": pair["enemy_origin"],
    }
    row = bootstrap.scenario_row(
        episode_id=f"{EPISODE_PREFIX}_01_{ROUTE_ID}",
        group_id=GROUP_ID,
        pair=source_pair,
        appearance=appearances[11],
        weapon="MachineGun",
        policy="visible_no_response",
        seed=SEED,
        motion_name="stationary",
        motion_mode=0,
        motion_distance=0.0,
        assigned_shard=0,
        shard_count=1,
        source_commit=source_commit,
        candidate_kind=CANDIDATE_KIND,
        weapon_mechanism_mode_eligible=True,
    )
    target_yaw, _ = causal.yaw_pitch_toward(
        row["player"]["origin"], row["enemy"]["origin"]
    )
    target_delta = causal.angle_delta(
        target_yaw, float(initial_angles[1])
    )
    desired_screen_error = math.copysign(40.0, target_delta)
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
            "frozen_actions_path": action_path,
            "frozen_actions_sha256": action_sha,
            "route_replay_origin_tolerance": POSITION_TOLERANCE,
            "training_stage": TRAINING_STAGE,
            "formal_collection_authorized": False,
            "training_admitted": False,
            "supersedes_cohort": SUPERSEDES_COHORT,
        }
    )
    if SUPERSESSION_REASON is not None:
        row["supersession_reason"] = SUPERSESSION_REASON
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
    source = v1.path_source(
        record=record,
        plan=plan,
        scenario=row,
    )
    source.update(
        {
            "schema_version": PLAYER_PATH_SOURCE_SCHEMA,
            "actions_path": action_path,
            "actions_sha256": action_sha,
            "derived_from_actions_path": record[
                "frozen_actions_path"
            ],
            "derived_from_actions_sha256": record[
                "frozen_actions_sha256"
            ],
            "physical_action_sha256": (
                capture.physical_action_sha256(
                    causal._locked_base_actions(
                        action_path, action_sha
                    )
                )
            ),
            "player_path_position_error_p95_max": (
                POSITION_TOLERANCE
            ),
            "player_path_position_error_max_max": (
                POSITION_TOLERANCE
            ),
            "derived_seed": SEED,
            "seed_derivation_policy": (
                "explicit_new_seed_same_physical_route_actions_v1"
            ),
        }
    )
    if OVERLAY_REPLAY_TOLERANCE_BASIS is not None:
        source["overlay_replay_tolerance_basis"] = (
            OVERLAY_REPLAY_TOLERANCE_BASIS
        )
    row["player_path_source"] = source
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
            "route_replay_origin_tolerance": POSITION_TOLERANCE,
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
        "schema_version": MANIFEST_SCHEMA,
        "source_commit": source_commit,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "route_id": ROUTE_ID,
        "seed": SEED,
        "derived_actions_path": action_path,
        "derived_actions_sha256": action_sha,
        "position_tolerance": POSITION_TOLERANCE,
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
    if OVERLAY_REPLAY_TOLERANCE_BASIS is not None:
        metadata["overlay_replay_tolerance_basis"] = (
            OVERLAY_REPLAY_TOLERANCE_BASIS
        )
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
                "position_tolerance": POSITION_TOLERANCE,
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
