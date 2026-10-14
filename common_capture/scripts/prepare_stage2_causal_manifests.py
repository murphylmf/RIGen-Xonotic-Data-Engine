                      
"""Prepare bounded Stage-2 causal review and encounter-certification manifests."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
DEFAULT_OUTPUT_ROOT = ROOT / "manifests/stage2_causal_bootstrap_v5"
PREFLIGHT_REPORT = ROOT / "preflight_v2/PREFLIGHT_REPORT.json"
CONTENT_CATALOG = ROOT / "configs/OFFICIAL_V2_CONTENT_CATALOG.json"
DATA_SPEC = ROOT / "XONOTIC_DATA_SPEC_V2.md"
SPLIT = "stage2_causal_preflight"
ENCOUNTER_SHARDS = 32
                                                                            
                                                                           
                                           
WEAPON_MECHANISM_INELIGIBLE_GAMETYPES = frozenset(
    {"nb", "rc", "race", "cts"}
)
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
WEAPON_DISTANCE = {
    "Blaster": "close",
    "Shotgun": "close",
    "MachineGun": "near",
    "Mortar": "near",
    "Electro": "near",
    "Crylink": "near",
    "Vortex": "medium",
    "Hagar": "near",
    "Devastator": "medium",
}
MOTION_SPECS = (
    ("stationary", 0, 0.0),
    ("lateral_patrol", 1, 48.0),
    ("approach_retreat", 2, 32.0),
    ("stop_and_go", 3, 48.0),
)
FIRE_PROGRAMS = {
    "visible_no_response": (0, ()),
    "delayed_acquisition": (80, (176, 256)),
    "pass_offset": (40, (176, 256)),
    "track_loss_reacquire": (16, (248, 296)),
    "sustained_tracking": (8, (88, 176, 264)),
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def load_inputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    report = json.loads(PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    pairs = [
        {
            "map": map_row["map"],
            "gametype": map_row["gametype"],
            **pair,
        }
        for map_row in report["map_summary"]
        for pair in map_row["accepted_pairs"]
        if pair.get("pass") is True
    ]
    catalog = json.loads(CONTENT_CATALOG.read_text(encoding="utf-8"))
    appearances = list(catalog["enemy_appearances"])
    checks = {
        "preflight_pass": report.get("pass") is True,
        "accepted_pairs_69": len(pairs) == 69,
        "stage2_maps_29": len({row["map"] for row in pairs}) == 29,
        "appearances_14": len(appearances) == 14,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_bootstrap_source_contract_failed",
            capture.canonical_json(checks),
        )
    return pairs, appearances


def tangent_vector(
    player_origin: list[float], enemy_origin: list[float]
) -> list[float]:
    dx = float(enemy_origin[0]) - float(player_origin[0])
    dy = float(enemy_origin[1]) - float(player_origin[1])
    length = math.hypot(dx, dy)
    if length < 1.0:
        raise capture.CaptureFailure(
            "stage2_pair_too_close",
            capture.canonical_json(
                {"player": player_origin, "enemy": enemy_origin}
            ),
        )
    return [
        round(-dy / length, 9),
        round(dx / length, 9),
        0.0,
    ]


def policy_design(policy: str, weapon: str) -> dict[str, Any]:
    acquisition_start, fire_ticks = FIRE_PROGRAMS[policy]
    return {
        "schema_version": causal.CAUSAL_DESIGN_SCHEMA,
        "aim_policy": policy,
        "aim_reference": (
            "manifest_frozen_analytic_enemy_trajectory"
        ),
        "reads_live_enemy_state": False,
        "reads_live_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
        "base_player_program": "stationary",
        "interaction_channel": "primary",
        "fire_output_ticks": list(fire_ticks),
        "fire_width_ticks": 12 if weapon == "MachineGun" else 2,
        "acquisition_start_output_tick": acquisition_start,
        "actual_outcome_source": "authoritative_telemetry_only",
        "intended_outcome_is_acceptance_gate": False,
    }


def scenario_row(
    *,
    episode_id: str,
    group_id: str,
    pair: dict[str, Any],
    appearance: dict[str, Any],
    weapon: str,
    policy: str,
    seed: int,
    motion_name: str,
    motion_mode: int,
    motion_distance: float,
    assigned_shard: int,
    shard_count: int,
    source_commit: str,
    candidate_kind: str,
    weapon_mechanism_mode_eligible: bool,
) -> dict[str, Any]:
    if not 0 < seed < 2**24:
        raise capture.CaptureFailure(
            "stage2_seed_not_exact_in_quakec_float32", str(seed)
        )
    player_origin = [
        round(float(value), 6) for value in pair["player_origin"]
    ]
    enemy_origin = [
        round(float(value), 6) for value in pair["enemy_origin"]
    ]
    target_yaw, target_pitch = causal.yaw_pitch_toward(
        player_origin, enemy_origin
    )
    motion_vector = tangent_vector(player_origin, enemy_origin)
    enemy_yaw, _ = causal.yaw_pitch_toward(
        enemy_origin, player_origin
    )
    design = policy_design(policy, weapon)
    row: dict[str, Any] = {
        "schema_version": causal.SCENARIO_SCHEMA,
        "episode_id": episode_id,
        "split": SPLIT,
        "dataset_role": "causal_interaction",
        "training_stage": "stage2_bootstrap_preflight_only",
        "candidate_kind": candidate_kind,
        "candidate_status": "uncertified",
        "formal_collection_authorized": False,
        "training_admitted": False,
        "human_review_required_before_training": True,
        "source_commit_required": source_commit,
        "data_spec_sha256": capture.sha256_file(DATA_SPEC),
        "model_action_schema_version": (
            capture.MODEL_ACTION_SCHEMA_VERSION
        ),
        "assigned_shard": assigned_shard,
        "shard_count": shard_count,
        "seed": seed,
        "map": pair["map"],
        "gametype": str(pair["gametype"]).lower(),
        "anchor_id": f"{group_id}_pair",
        "encounter_source": {
            "schema_version": "xonotic-stage2-encounter-source-v1",
            "source_report": str(PREFLIGHT_REPORT),
            "source_report_sha256": capture.sha256_file(
                PREFLIGHT_REPORT
            ),
            "source_pair_episode_id": pair["episode_id"],
            "source_pair_distance_bin": pair["distance_bin"],
            "source_pair_passed": True,
            "current_trajectory_requires_recertification": True,
            "weapon_mechanism_mode_eligible": (
                weapon_mechanism_mode_eligible
            ),
        },
        "counterfactual_group_id": group_id,
        "target_bin": "causal_interaction",
        "target_ordinal": 0,
        "category": f"stage2_{policy}",
        "intent_outcome": "telemetry_rebucket_only",
        "outcome_label_source": "authoritative_telemetry_only",
        "action_program": causal.ACTION_PROGRAM,
        "causal_design": design,
        "enemy_present": True,
        "enemy_model": appearance["model"],
        "enemy_skin": int(appearance["skin"]),
        "enemy_color": (0, 68, 204)[seed % 3],
        "weapon": weapon,
        "weapon_netname": capture.WEAPON_NETNAME[weapon],
        "warmup_ticks": capture.WARMUP_TICKS,
        "output_ticks": capture.OUTPUT_TICKS,
        "tick_hz": capture.TICK_HZ,
        "video": {
            "width": capture.WIDTH,
            "height": capture.HEIGHT,
            "fps": capture.VIDEO_FPS,
            "frames": capture.OUTPUT_TICKS,
        },
        "audio": {
            "sample_rate": capture.AUDIO_RATE,
            "channels": 2,
            "sample_format": "s16",
            "samples_per_channel": capture.AUDIO_SAMPLES,
            "samples_per_frame": capture.SAMPLES_PER_FRAME,
        },
        "player": {
            "origin": player_origin,
            "yaw": round(
                causal.wrap_angle(
                    target_yaw + causal.INITIAL_YAW_OFFSET_DEG
                ),
                6,
            ),
            "pitch": round(
                target_pitch + causal.INITIAL_PITCH_OFFSET_DEG, 6
            ),
            "health": 200.0,
            "armor": 0.0,
            "clip": 60.0,
            "reserve": 180.0,
        },
        "enemy": {
            "origin": enemy_origin,
            "yaw": round(enemy_yaw, 6),
            "health": 5000.0,
            "armor": 0.0,
            "motion": motion_mode,
            "motion_vector": motion_vector,
            "motion_distance": motion_distance,
            "motion_start_tick": capture.WARMUP_TICKS,
        },
        "enemy_policy": {
            "schema_version": "xonotic-stage2-enemy-policy-v1",
            "name": motion_name,
            "policy_seed": seed,
            "motion_start_tick": capture.WARMUP_TICKS,
            "runtime_reads_player_state": False,
            "reads_camera": False,
            "reads_crosshair": False,
            "fires": False,
            "jumps": False,
            "movement_audio": capture.ENEMY_MOVEMENT_AUDIO_MODE,
            "step_stride_units": capture.ENEMY_STEP_STRIDE_UNITS,
        },
        "policy_labels": {
            "aim_policy": policy,
            "aim_overlay_reads_enemy": True,
            "aim_overlay_reads_live_enemy": False,
            "aim_overlay_source": (
                "manifest_frozen_analytic_enemy_trajectory"
            ),
            "enemy_motion_reads_camera": False,
            "enemy_motion_reads_crosshair": False,
            "enemy_motion_reads_live_player_state": False,
            "expected_distance_bin": pair["distance_bin"],
        },
        "acceptance": {
            "actual_outcome": None,
            "fire_required": False,
            "reload_success": False,
            "actual_outcome_rebucket_required": True,
        },
        "expects_sound": (
            policy != "visible_no_response" or motion_mode != 0
        ),
        "asset_policy": "official-xonotic-0.8.6-only",
        "canary_role": f"stage2_{candidate_kind}_{policy}",
    }
    row["exogenous_contract_sha256"] = (
        causal.exogenous_contract_sha256(row)
    )
    causal.validate_scenario_contract(row)
    capture.validate_scenario_assets(row)
    return row


def choose_pair(
    pairs: list[dict[str, Any]],
    distance: str,
    ordinal: int,
    *,
    require_weapon_mechanism: bool = False,
) -> dict[str, Any]:
    candidates = [
        row
        for row in pairs
        if row["distance_bin"] == distance
        and (
            not require_weapon_mechanism
            or str(row["gametype"]).lower()
            not in WEAPON_MECHANISM_INELIGIBLE_GAMETYPES
        )
    ]
    if not candidates:
        raise capture.CaptureFailure(
            "stage2_distance_pair_missing", distance
        )
    candidates.sort(key=lambda row: (row["map"], row["episode_id"]))
    return candidates[ordinal % len(candidates)]


def review_rows(
    pairs: list[dict[str, Any]],
    appearances: list[dict[str, Any]],
    source_commit: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group_ordinal, appearance in enumerate(appearances, 1):
        weapon = WEAPONS[(group_ordinal - 1) % len(WEAPONS)]
        pair = choose_pair(
            pairs,
            WEAPON_DISTANCE[weapon],
            group_ordinal - 1,
            require_weapon_mechanism=True,
        )
        group_id = f"s2review_g{group_ordinal:03d}"
        seed = 15_100_000 + group_ordinal
        for policy_ordinal, policy in enumerate(causal.AIM_POLICIES, 1):
            rows.append(
                scenario_row(
                    episode_id=(
                        f"{group_id}_p{policy_ordinal:02d}_{policy}"
                    ),
                    group_id=group_id,
                    pair=pair,
                    appearance=appearance,
                    weapon=weapon,
                    policy=policy,
                    seed=seed,
                    motion_name="stationary",
                    motion_mode=0,
                    motion_distance=0.0,
                    assigned_shard=0,
                    shard_count=1,
                    source_commit=source_commit,
                    candidate_kind="counterfactual_review",
                    weapon_mechanism_mode_eligible=True,
                )
            )
    return rows


def encounter_rows(
    pairs: list[dict[str, Any]],
    appearances: list[dict[str, Any]],
    source_commit: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for pair_index, pair in enumerate(pairs):
        for motion_name, motion_mode, motion_distance in MOTION_SPECS:
            shard = ordinal % ENCOUNTER_SHARDS
            group_id = (
                f"s2enc_{pair_index + 1:03d}_m{motion_mode}"
            )
            rows.append(
                scenario_row(
                    episode_id=f"{group_id}_cert",
                    group_id=group_id,
                    pair=pair,
                    appearance=appearances[
                        ordinal % len(appearances)
                    ],
                    weapon="Blaster",
                    policy="visible_no_response",
                    seed=15_200_000 + ordinal,
                    motion_name=motion_name,
                    motion_mode=motion_mode,
                    motion_distance=motion_distance,
                    assigned_shard=shard,
                    shard_count=ENCOUNTER_SHARDS,
                    source_commit=source_commit,
                    candidate_kind="encounter_prototype_certification",
                    weapon_mechanism_mode_eligible=(
                        str(pair["gametype"]).lower()
                        not in WEAPON_MECHANISM_INELIGIBLE_GAMETYPES
                    ),
                )
            )
            ordinal += 1
    return rows


def metadata(
    *,
    name: str,
    rows: list[dict[str, Any]],
    shard_rows: list[list[dict[str, Any]]],
    shard_paths: list[Path],
    source_commit: str,
) -> dict[str, Any]:
    return {
        "schema_version": "xonotic-stage2-causal-manifest-v1",
        "name": name,
        "source_commit": source_commit,
        "data_spec_sha256": capture.sha256_file(DATA_SPEC),
        "model_action_schema_version": capture.MODEL_ACTION_SCHEMA_VERSION,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "outcome_label_source": "authoritative_telemetry_only",
        "review": {
            "rows": len(rows),
            "shard_count": len(shard_rows),
            "shards": [
                {
                    "shard_index": index,
                    "path": str(path),
                    "rows": len(items),
                    "sha256": sha256_text(canonical_lines(items)),
                }
                for index, (path, items) in enumerate(
                    zip(shard_paths, shard_rows)
                )
            ],
        },
    }


def materialize(
    output_root: Path, source_commit: str
) -> dict[str, Any]:
    pairs, appearances = load_inputs()
    review = review_rows(pairs, appearances, source_commit)
    smoke_group = review[0]["counterfactual_group_id"]
    smoke = [
        copy.deepcopy(row)
        for row in review
        if row["counterfactual_group_id"] == smoke_group
    ]
    encounters = encounter_rows(pairs, appearances, source_commit)

    cohorts = {
        "smoke": (smoke, 1),
        "review": (review, 1),
        "encounter_certification": (
            encounters,
            ENCOUNTER_SHARDS,
        ),
    }
    cohort_metadata: dict[str, Any] = {}
    for name, (rows, shard_count) in cohorts.items():
        cohort_root = output_root / name
        master_text = canonical_lines(rows)
        write_once_or_verify(cohort_root / "input.jsonl", master_text)
        shards = [
            [
                row
                for row in rows
                if int(row["assigned_shard"]) == shard
            ]
            for shard in range(shard_count)
        ]
        paths = [
            cohort_root
            / "shards"
            / f"shard-{shard:03d}-of-{shard_count:03d}.jsonl"
            for shard in range(shard_count)
        ]
        for path, items in zip(paths, shards):
            write_once_or_verify(path, canonical_lines(items))
        payload = metadata(
            name=name,
            rows=rows,
            shard_rows=shards,
            shard_paths=paths,
            source_commit=source_commit,
        )
        write_once_or_verify(
            cohort_root / "MANIFEST_METADATA.json",
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
        cohort_metadata[name] = payload

    review_groups = {
        row["counterfactual_group_id"] for row in review
    }
    audit = {
        "schema_version": "xonotic-stage2-causal-design-audit-v1",
        "source_commit": source_commit,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "review": {
            "rows": len(review),
            "groups": len(review_groups),
            "group_size_counts": dict(
                Counter(
                    sum(
                        row["counterfactual_group_id"] == group
                        for row in review
                    )
                    for group in review_groups
                )
            ),
            "aim_policies": dict(
                Counter(
                    row["causal_design"]["aim_policy"]
                    for row in review
                )
            ),
            "weapons": dict(Counter(row["weapon"] for row in review)),
            "appearances": dict(
                Counter(
                    f"{row['enemy_model']}:{row['enemy_skin']}"
                    for row in review
                )
            ),
            "distance_bins": dict(
                Counter(
                    row["policy_labels"]["expected_distance_bin"]
                    for row in review
                )
            ),
            "gametypes": dict(
                Counter(row["gametype"] for row in review)
            ),
            "weapon_mechanism_mode_eligible": all(
                row["encounter_source"][
                    "weapon_mechanism_mode_eligible"
                ]
                for row in review
            ),
            "exogenous_invariant_per_group": all(
                len(
                    {
                        row["exogenous_contract_sha256"]
                        for row in review
                        if row["counterfactual_group_id"] == group
                    }
                )
                == 1
                for group in review_groups
            ),
        },
        "encounter_certification": {
            "rows": len(encounters),
            "source_pairs": len(pairs),
            "maps": len({row["map"] for row in encounters}),
            "motion_policies": dict(
                Counter(
                    row["enemy_policy"]["name"] for row in encounters
                )
            ),
            "distance_bins": dict(
                Counter(
                    row["policy_labels"]["expected_distance_bin"]
                    for row in encounters
                )
            ),
            "shards": ENCOUNTER_SHARDS,
        },
        "production_gate": {
            "formal_40000_manifest_materialized": False,
            "reason": (
                "requires current encounter certificates, complete "
                "counterfactual bundle QA, and weapon-specific secondary "
                "mechanism certification"
            ),
        },
        "cohorts": cohort_metadata,
    }
    write_once_or_verify(
        output_root / "DESIGN_AUDIT.json",
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
    )
    report = (
        "# Stage-2 causal bootstrap design\n\n"
        f"- Review: {len(review)} rows / {len(review_groups)} complete "
        "five-policy counterfactual groups\n"
        f"- Encounter certification: {len(encounters)} candidates from "
        f"{len(pairs)} visible pairs across 29 maps and four motion policies\n"
        "- Outcomes: authoritative telemetry re-bucketing only\n"
        "- Interaction channel: primary fire only in this bootstrap\n"
        "- Firing groups: ordinary weapon-mechanism modes only; special "
        "modes remain in encounter certification\n"
        f"- Data spec SHA256: `{capture.sha256_file(DATA_SPEC)}`\n"
        f"- Model action schema: `{capture.MODEL_ACTION_SCHEMA_VERSION}`\n"
        "- Training admission: false\n"
        "- Formal 40k manifest: deliberately not materialized until encounter, "
        "bundle, and per-weapon secondary-mechanism gates pass\n"
    )
    write_once_or_verify(output_root / "DESIGN_AUDIT.md", report)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument("--source-commit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_commit = args.source_commit or (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    audit = materialize(args.output_root.resolve(), source_commit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
