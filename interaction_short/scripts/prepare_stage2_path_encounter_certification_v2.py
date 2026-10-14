                      
"""Build explicit new-seed v3 path certificates with frozen view offsets."""

from __future__ import annotations

import hashlib
import json
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
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_path_encounter_certification_v2"
)
ROUTE_IDS = ("s1route_12587", "s1route_10780")


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
    rows: list[dict[str, Any]] = []
    for ordinal, route_id in enumerate(ROUTE_IDS, 1):
        record = v1.route_record(route_id)
        plan = routes.effective_plan(route_id)
        pair = record["compatible_enemy_pairs"][0]
        states = pd.read_parquet(
            record["calibration_states_path"]
        ).sort_values("server_tick")
        initial_angles = states.iloc[0]["pre.angles"]
        seed = int(
            (
                ROOT / record["frozen_actions_path"]
            ).read_text(encoding="utf-8").splitlines()[0].split(
                ",", 1
            )[1]
        )
        source_pair = {
            "map": record["map"],
            "gametype": record["gametype"],
            "episode_id": pair["source_probe"],
            "distance_bin": pair["distance_bin"],
            "player_origin": pair["player_origin"],
            "enemy_origin": pair["enemy_origin"],
        }
        episode_id = f"s2pathcertv2_{ordinal:02d}_{route_id}"
        row = bootstrap.scenario_row(
            episode_id=episode_id,
            group_id=f"s2pathcertv2_g{ordinal:02d}",
            pair=source_pair,
            appearance=appearances[(ordinal + 6) % len(appearances)],
            weapon="MachineGun",
            policy="visible_no_response",
            seed=seed,
            motion_name="stationary",
            motion_mode=0,
            motion_distance=0.0,
            assigned_shard=0,
            shard_count=1,
            source_commit=source_commit,
            candidate_kind="path_encounter_certification_v2",
            weapon_mechanism_mode_eligible=True,
        )
        target_yaw, target_pitch = causal.yaw_pitch_toward(
            row["player"]["origin"], row["enemy"]["origin"]
        )
        desired_initial_yaw = causal.wrap_angle(
            target_yaw + causal.INITIAL_YAW_OFFSET_DEG
        )
        desired_initial_pitch = (
            target_pitch + causal.INITIAL_PITCH_OFFSET_DEG
        )
        base_yaw_offset = causal.angle_delta(
            desired_initial_yaw, float(initial_angles[1])
        )
        base_pitch_offset = (
            desired_initial_pitch - float(initial_angles[0])
        )
        row.update(
            {
                "schema_version": causal.SCENARIO_SCHEMA_V3,
                "action_program": causal.ACTION_PROGRAM_V3,
                "map_region_id": record["map_region_id"],
                "route_group_id": record["route_group_id"],
                "route_plan": plan,
                "frozen_actions_path": record[
                    "frozen_actions_path"
                ],
                "frozen_actions_sha256": record[
                    "frozen_actions_sha256"
                ],
                "training_stage": (
                    "stage2_bounded_path_encounter_certification_v2_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "supersedes_cohort": (
                    "stage2_player_motion_validation_v2"
                ),
            }
        )
        row["player"]["yaw"] = round(desired_initial_yaw, 6)
        row["player"]["pitch"] = round(
            desired_initial_pitch, 6
        )
        design = row["causal_design"]
        design.update(
            {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V3,
                "base_player_program": "certified_route_replay",
                "player_motion_class": (
                    "jumping"
                    if int(record["base_jump_ticks"]) > 0
                    else "moving"
                ),
                "player_reference": (
                    "manifest_frozen_certified_route_states"
                ),
                "base_view_yaw_offset_deg": round(
                    base_yaw_offset, 6
                ),
                "base_view_pitch_offset_deg": round(
                    base_pitch_offset, 6
                ),
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
        row["policy_labels"]["player_motion_class"] = design[
            "player_motion_class"
        ]
        row["policy_labels"]["interaction_channel"] = "primary"
        row["policy_labels"]["base_view_policy"] = (
            "constant_manifest_frozen_initial_geometry_offset"
        )
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        actions = causal.causal_action_rows(row)
        if any(
            int(action["primary"]) or int(action["secondary"])
            for action in actions
        ):
            raise capture.CaptureFailure(
                "stage2_path_certificate_weapon_input_nonzero",
                episode_id,
            )
        rows.append(row)

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-path-encounter-certification-manifest-v2"
        ),
        "source_commit": source_commit,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "base_view_policy": (
            "constant manifest-frozen initial-geometry offset; "
            "no live target reads"
        ),
        "review": {
            "rows": len(rows),
            "route_ids": list(ROUTE_IDS),
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
                "route_ids": [
                    row["player_path_source"]["route_id"]
                    for row in rows
                ],
                "seeds": [row["seed"] for row in rows],
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
