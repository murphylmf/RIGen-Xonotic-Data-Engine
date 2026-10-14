                      
"""Build two matched Stage-2 groups on collision-certified player paths."""

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
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
INDEX = (
    ROOT
    / "manifests/stage1_foundation_v5_certification/"
    "ROUTE_CERTIFICATION_INDEX.jsonl"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_player_motion_validation_v1"
ROUTES = (
    ("s1route_10454", "moving"),
    ("s1route_10695", "jumping"),
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


def path_source(record: dict[str, Any]) -> dict[str, Any]:
    pair = record["compatible_enemy_pairs"][0]
    return {
        "schema_version": causal.PLAYER_PATH_SOURCE_SCHEMA,
        "route_id": record["route_id"],
        "route_index_path": str(INDEX.relative_to(ROOT)),
        "route_index_sha256": capture.sha256_file(INDEX),
        "route_record_sha256": hashlib.sha256(
            capture.canonical_json(record).encode("utf-8")
        ).hexdigest(),
        "actions_path": record["frozen_actions_path"],
        "actions_sha256": record["frozen_actions_sha256"],
        "states_path": record["calibration_states_path"],
        "states_sha256": record["calibration_states_sha256"],
        "source_commit": record["source_commit"],
        "base_jump_ticks": int(record["base_jump_ticks"]),
        "compatible_enemy_pair_source_probe": pair["source_probe"],
        "compatible_enemy_pair_variant": pair["variant"],
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
    }


def materialize() -> list[dict[str, Any]]:
    _, appearances = bootstrap.load_inputs()
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    rows: list[dict[str, Any]] = []
    for group_ordinal, (route_id, motion_class) in enumerate(
        ROUTES, 1
    ):
        record = route_record(route_id)
        pair = record["compatible_enemy_pairs"][0]
        reference_states = pd.read_parquet(
            record["calibration_states_path"]
        ).sort_values("server_tick")
        initial_angles = reference_states.iloc[0]["pre.angles"]
        actions_header = (
            (ROOT / record["frozen_actions_path"])
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        seed = int(actions_header.split(",", 1)[1])
        source_pair = {
            "map": record["map"],
            "gametype": record["gametype"],
            "episode_id": pair["source_probe"],
            "distance_bin": pair["distance_bin"],
            "player_origin": pair["player_origin"],
            "enemy_origin": pair["enemy_origin"],
        }
        group_id = f"s2playermotion_g{group_ordinal:02d}"
        for policy_ordinal, policy in enumerate(
            causal.AIM_POLICIES, 1
        ):
            row = bootstrap.scenario_row(
                episode_id=(
                    f"{group_id}_p{policy_ordinal:02d}_{policy}"
                ),
                group_id=group_id,
                pair=source_pair,
                appearance=appearances[
                    (group_ordinal - 1) % len(appearances)
                ],
                weapon="MachineGun",
                policy=policy,
                seed=seed,
                motion_name="stationary",
                motion_mode=0,
                motion_distance=0.0,
                assigned_shard=0,
                shard_count=1,
                source_commit=source_commit,
                candidate_kind="player_motion_causal_validation",
                weapon_mechanism_mode_eligible=True,
            )
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V2,
                    "action_program": causal.ACTION_PROGRAM_V2,
                    "map_region_id": record["map_region_id"],
                    "route_group_id": record["route_group_id"],
                    "player_path_source": path_source(record),
                    "training_stage": (
                        "stage2_bounded_player_motion_validation_only"
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
                    "schema_version": (
                        causal.CAUSAL_DESIGN_SCHEMA_V2
                    ),
                    "base_player_program": (
                        "certified_route_replay"
                    ),
                    "player_motion_class": motion_class,
                    "player_reference": (
                        "manifest_frozen_certified_route_states"
                    ),
                    "secondary_mechanism": None,
                }
            )
            row["policy_labels"]["player_motion_class"] = (
                motion_class
            )
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
            "xonotic-stage2-player-motion-validation-manifest-v1"
        ),
        "source_commit": source_commit,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "model_action_schema_version": (
            capture.MODEL_ACTION_SCHEMA_VERSION
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "route_index_sha256": capture.sha256_file(INDEX),
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(ROUTES),
            "motion_classes": [item[1] for item in ROUTES],
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
                "routes": [
                    row["player_path_source"]["route_id"]
                    for row in rows[:: len(causal.AIM_POLICIES)]
                ],
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
