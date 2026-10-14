                      
"""Build bounded v3 encounter certificates on frozen Stage-1 routes."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage2_causal_manifests as bootstrap              
import xonotic_capture as capture              
import xonotic_stage1_routes as routes              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
INDEX = (
    ROOT
    / "manifests/stage1_foundation_v5_certification/"
    "ROUTE_CERTIFICATION_INDEX.jsonl"
)
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_path_encounter_certification_v1"
)
ROUTE_IDS = (
    "s1route_10454",
    "s1route_11632",
    "s1route_10830",
    "s1route_13183",
    "s1route_12269",
    "s1route_12143",
    "s1route_10780",
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


def route_record(route_id: str) -> dict[str, Any]:
    matches = [
        row
        for row in capture.load_jsonl(INDEX)
        if row["route_id"] == route_id
    ]
    if len(matches) != 1:
        raise capture.CaptureFailure(
            "stage2_player_route_missing", route_id
        )
    return matches[0]


def path_source(
    *,
    record: dict[str, Any],
    plan: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    pair = record["compatible_enemy_pairs"][0]
    states = pd.read_parquet(
        record["calibration_states_path"]
    ).sort_values("server_tick")
    player_origins = np.asarray(
        states["pre.origin"].tolist(), dtype=np.float64
    )
    enemy_origins = np.asarray(
        [
            causal.enemy_origin_at_server_tick(scenario, tick)
            for tick in range(capture.TOTAL_TICKS)
        ],
        dtype=np.float64,
    )
    clearance = np.linalg.norm(
        player_origins - enemy_origins, axis=1
    )
    minimum_tick = int(np.argmin(clearance))
    minimum = float(clearance[minimum_tick])
    if minimum < causal.PLAYER_ENEMY_CLEARANCE_MINIMUM:
        raise capture.CaptureFailure(
            "stage2_player_enemy_clearance_failed",
            capture.canonical_json(
                {
                    "route_id": record["route_id"],
                    "minimum": minimum,
                    "server_tick": minimum_tick,
                }
            ),
        )
    return {
        "schema_version": causal.PLAYER_PATH_SOURCE_SCHEMA_V2,
        "route_id": record["route_id"],
        "route_index_path": str(INDEX.relative_to(ROOT)),
        "route_index_sha256": capture.sha256_file(INDEX),
        "route_record_sha256": hashlib.sha256(
            capture.canonical_json(record).encode("utf-8")
        ).hexdigest(),
        "route_plan_contract_sha256": hashlib.sha256(
            capture.canonical_json(plan).encode("utf-8")
        ).hexdigest(),
        "actions_path": record["frozen_actions_path"],
        "actions_sha256": record["frozen_actions_sha256"],
        "states_path": record["calibration_states_path"],
        "states_sha256": record["calibration_states_sha256"],
        "source_commit": record["source_commit"],
        "base_jump_ticks": int(record["base_jump_ticks"]),
        "compatible_enemy_pair_source_probe": pair["source_probe"],
        "compatible_enemy_pair_variant": pair["variant"],
        "player_enemy_clearance_metric": "3d_center_distance",
        "player_enemy_clearance_threshold": (
            causal.PLAYER_ENEMY_CLEARANCE_MINIMUM
        ),
        "minimum_player_enemy_clearance": minimum,
        "minimum_player_enemy_clearance_server_tick": minimum_tick,
        "player_enemy_clearance_passed": True,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
    }


def materialize() -> list[dict[str, Any]]:
    _, appearances = bootstrap.load_inputs()
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    rows: list[dict[str, Any]] = []
    for ordinal, route_id in enumerate(ROUTE_IDS, 1):
        record = route_record(route_id)
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
        episode_id = f"s2pathcert_{ordinal:02d}_{route_id}"
        row = bootstrap.scenario_row(
            episode_id=episode_id,
            group_id=f"s2pathcert_g{ordinal:02d}",
            pair=source_pair,
            appearance=appearances[(ordinal - 1) % len(appearances)],
            weapon="MachineGun",
            policy="visible_no_response",
            seed=seed,
            motion_name="stationary",
            motion_mode=0,
            motion_distance=0.0,
            assigned_shard=0,
            shard_count=1,
            source_commit=source_commit,
            candidate_kind="path_encounter_certification",
            weapon_mechanism_mode_eligible=True,
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
                    "stage2_bounded_path_encounter_certification_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
            }
        )
        row["player"]["yaw"] = round(
            float(initial_angles[1]), 6
        )
        row["player"]["pitch"] = round(
            float(initial_angles[0]), 6
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
                "aim_schedule": causal.default_aim_schedule(
                    "visible_no_response"
                ),
                "secondary_mechanism": None,
            }
        )
        row["player_path_source"] = path_source(
            record=record,
            plan=plan,
            scenario=row,
        )
        row["policy_labels"]["player_motion_class"] = design[
            "player_motion_class"
        ]
        row["policy_labels"]["interaction_channel"] = "primary"
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        causal.causal_action_rows(row)
        rows.append(row)

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-path-encounter-certification-manifest-v1"
        ),
        "source_commit": source_commit,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "purpose": (
            "certify full-route replay, player-enemy clearance, and "
            "authoritative LOS before materializing v3 policy groups"
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
                "moving": sum(
                    row["causal_design"]["player_motion_class"]
                    == "moving"
                    for row in rows
                ),
                "jumping": sum(
                    row["causal_design"]["player_motion_class"]
                    == "jumping"
                    for row in rows
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
