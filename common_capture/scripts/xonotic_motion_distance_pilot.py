                      
"""Bounded large-motion and near-distance Xonotic v2 supplement Pilot."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import html
import json
import math
import os
import shutil
import subprocess
import sys
import threading
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finalize_v2_pilot as final_audit              
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              


ROOT = capture.ROOT
PILOT_ROOT = ROOT / "v2_motion_distance_pilot"
SCENARIOS_PATH = (
    ROOT / "configs/v2_motion_distance_pilot_scenarios.jsonl"
)
ACCEPTED_PATH = PILOT_ROOT / "manifests/accepted.jsonl"
REJECTS_PATH = PILOT_ROOT / "manifests/rejects.jsonl"
SUMMARY_PATH = PILOT_ROOT / "PILOT_SUMMARY.json"
AUDIT_PATH = PILOT_ROOT / "FINAL_AUDIT.json"
REPORT_PATH = PILOT_ROOT / "MOTION_DISTANCE_PILOT_REPORT.md"
PREVIEW_ROOT = ROOT / "previews/v2_motion_distance"
LOCK = threading.Lock()
EXPECTED_ROLES = {
    "foundation_no_enemy": 12,
    "foundation_enemy_distractor": 8,
    "causal_interaction": 4,
}
EXPECTED_ENEMY_DISTANCES = {
    "close": 6,
    "near": 5,
    "far": 1,
}
REQUIRED_FILES = {
    "episode.json",
    "video.mkv",
    "actions.parquet",
    "states.parquet",
    "events.parquet",
    "frames.parquet",
    "audio_events.parquet",
    "target_relations.parquet",
    "qa.json",
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_text(
        path,
        "".join(capture.canonical_json(row) + "\n" for row in rows),
    )


def largest_monotonic_turn(deltas: np.ndarray) -> float:
    maximum = current = 0.0
    sign = 0
    for value in deltas:
        if abs(value) < 1e-6:
            continue
        next_sign = 1 if value > 0 else -1
        if next_sign == sign:
            current += abs(float(value))
        else:
            current = abs(float(value))
            sign = next_sign
        maximum = max(maximum, current)
    return maximum


def displacement_bin(value: float) -> str:
    if value < 64:
        return "lt64"
    if value < 256:
        return "64_256"
    if value < 512:
        return "256_512"
    if value < 1024:
        return "512_1024"
    return "gt1024"


def yaw_range_bin(value: float) -> str:
    if value < 15:
        return "lt15"
    if value < 45:
        return "15_45"
    if value < 90:
        return "45_90"
    if value < 180:
        return "90_180"
    return "ge180"


def pitch_range_bin(value: float) -> str:
    if value < 5:
        return "lt5"
    if value < 15:
        return "5_15"
    if value < 30:
        return "15_30"
    return "ge30"


def motion_metrics(package: Path) -> dict[str, Any]:
    states = pd.read_parquet(package / "states.parquet")
    states = states[
        (states["server_tick"] >= capture.WARMUP_TICKS)
        & (
            states["server_tick"]
            < capture.WARMUP_TICKS + capture.OUTPUT_TICKS
        )
    ].sort_values("server_tick")
    positions = np.asarray(states["post.origin"].tolist(), dtype=np.float64)
    velocities = np.asarray(
        states["post.velocity"].tolist(), dtype=np.float64
    )
    frames = pd.read_parquet(package / "frames.parquet").sort_values(
        "frame_index"
    )
    forward = frames[
        ["forward_x", "forward_y", "forward_z"]
    ].to_numpy(dtype=np.float64)
    yaw = np.unwrap(np.arctan2(forward[:, 1], forward[:, 0]))
    yaw = np.degrees(yaw)
    pitch = np.degrees(np.arcsin(np.clip(forward[:, 2], -1.0, 1.0)))
    yaw_deltas = np.diff(yaw)
    pitch_deltas = np.diff(pitch)
    steps_3d = np.linalg.norm(np.diff(positions, axis=0), axis=1)
    steps_xy = np.linalg.norm(
        np.diff(positions[:, :2], axis=0), axis=1
    )
    from_start = np.linalg.norm(positions - positions[0], axis=1)
    speeds = np.linalg.norm(velocities, axis=1)
    metrics = {
        "path_length_3d": float(steps_3d.sum()),
        "path_length_xy": float(steps_xy.sum()),
        "net_displacement_3d": float(
            np.linalg.norm(positions[-1] - positions[0])
        ),
        "maximum_displacement_from_start": float(from_start.max()),
        "vertical_range": float(np.ptp(positions[:, 2])),
        "speed_p95": float(np.percentile(speeds, 95)),
        "speed_max": float(speeds.max()),
        "yaw_total_variation_deg": float(np.abs(yaw_deltas).sum()),
        "yaw_range_deg": float(np.ptp(yaw)),
        "yaw_net_change_deg": float(abs(yaw[-1] - yaw[0])),
        "yaw_largest_monotonic_turn_deg": float(
            largest_monotonic_turn(yaw_deltas)
        ),
        "yaw_max_frame_step_deg": float(
            np.abs(yaw_deltas).max(initial=0.0)
        ),
        "pitch_total_variation_deg": float(
            np.abs(pitch_deltas).sum()
        ),
        "pitch_range_deg": float(np.ptp(pitch)),
        "pitch_max_frame_step_deg": float(
            np.abs(pitch_deltas).max(initial=0.0)
        ),
    }
    metrics.update(
        {
            "net_displacement_bin": displacement_bin(
                metrics["net_displacement_3d"]
            ),
            "maximum_displacement_bin": displacement_bin(
                metrics["maximum_displacement_from_start"]
            ),
            "yaw_range_bin": yaw_range_bin(metrics["yaw_range_deg"]),
            "pitch_range_bin": pitch_range_bin(
                metrics["pitch_range_deg"]
            ),
        }
    )
    return metrics


def validate_motion(
    row: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, bool]:
    acceptance = row.get("motion_acceptance", {})
    mapping = {
        "min_path_length": "path_length_3d",
        "min_net_displacement": "net_displacement_3d",
        "min_maximum_displacement": "maximum_displacement_from_start",
        "min_yaw_range": "yaw_range_deg",
        "min_monotonic_yaw": "yaw_largest_monotonic_turn_deg",
        "min_yaw_frame_step": "yaw_max_frame_step_deg",
        "min_pitch_range": "pitch_range_deg",
    }
    maximum_mapping = {
        "max_net_displacement": "net_displacement_3d",
        "max_maximum_displacement": "maximum_displacement_from_start",
        "max_yaw_range": "yaw_range_deg",
        "max_yaw_frame_step": "yaw_max_frame_step_deg",
    }
    gates: dict[str, bool] = {}
    for threshold, metric in mapping.items():
        if threshold in acceptance:
            gates[threshold] = (
                float(metrics[metric]) >= float(acceptance[threshold])
            )
    for threshold, metric in maximum_mapping.items():
        if threshold in acceptance:
            gates[threshold] = (
                float(metrics[metric]) <= float(acceptance[threshold])
            )
    return gates


def direction_yaw(
    player_origin: list[float], target_origin: list[float]
) -> float:
    return math.degrees(
        math.atan2(
            target_origin[1] - player_origin[1],
            target_origin[0] - player_origin[0],
        )
    )


def geometry_candidates(
    pairs: list[dict[str, Any]], yaw_adjustments: tuple[float, ...]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for pair in pairs:
        base_yaw = direction_yaw(
            pair["player_origin"], pair["enemy_origin"]
        )
        for adjustment in yaw_adjustments:
            result.append(
                {
                    "map": pair["map"],
                    "gametype": pair["gametype"],
                    "player_origin": pair["player_origin"],
                    "player_yaw": base_yaw + adjustment,
                    "source_pair": pair["episode_id"],
                }
            )
    return result


def apply_variant(row: dict[str, Any], retry: int) -> dict[str, Any]:
    variant = copy.deepcopy(row)
    geometries = variant.get("geometry_candidates")
    if geometries:
        geometry = geometries[retry % len(geometries)]
        variant["map"] = geometry["map"]
        variant["gametype"] = geometry["gametype"]
        variant["player"]["origin"] = geometry["player_origin"]
        variant["player"]["yaw"] = round(
            float(geometry["player_yaw"]), 6
        )
        variant["anchor_id"] = (
            f"{variant['map']}_{variant['episode_id']}_solo"
        )
        variant["selected_geometry"] = geometry
    pairs = variant.get("pair_candidates")
    if pairs:
        pair = pairs[retry % len(pairs)]
        variant["map"] = pair["map"]
        variant["gametype"] = pair["gametype"]
        variant["player"]["origin"] = pair["player_origin"]
        variant["enemy"]["origin"] = pair["enemy_origin"]
        base_yaw, base_pitch = v2.yaw_pitch_toward(
            pair["player_origin"], pair["enemy_origin"]
        )
        variant["player"]["yaw"] = round(
            base_yaw + float(variant["initial_yaw_offset"]), 6
        )
        variant["player"]["pitch"] = round(base_pitch, 6)
        enemy_yaw, _ = v2.yaw_pitch_toward(
            pair["enemy_origin"], pair["player_origin"]
        )
        variant["enemy"]["yaw"] = round(enemy_yaw, 6)
        variant["anchor_id"] = (
            f"{variant['map']}_{variant['episode_id']}_pair"
        )
        variant["selected_pair"] = pair["episode_id"]
    return variant


def base_row(
    *,
    episode_id: str,
    role: str,
    category: str,
    map_name: str,
    gametype: str,
    player_origin: list[float],
    weapon: str,
    action_program: str,
    seed: int,
    expects_sound: bool,
    motion_acceptance: dict[str, float],
    enemy_origin: list[float] | None = None,
    enemy_model: str = "",
    enemy_skin: int = 0,
    enemy_color: int = 0,
    yaw_offset: float = 0.0,
    expected_outcome: str | None = None,
    expected_distance_bin: str | None = None,
    enemy_health: float = 500.0,
) -> dict[str, Any]:
    row = v2.scenario(
        episode_id=episode_id,
        split="v2_motion_distance_pilot",
        dataset_role=role,
        category=category,
        map_name=map_name,
        gametype=gametype,
        player_origin=player_origin,
        weapon=weapon,
        action_program=action_program,
        seed=seed,
        enemy_origin=enemy_origin,
        enemy_model=enemy_model,
        enemy_skin=enemy_skin,
        enemy_color=enemy_color,
        yaw_offset=yaw_offset,
        expected_outcome=expected_outcome,
        expected_distance_bin=expected_distance_bin,
        enemy_health=enemy_health,
        expects_sound=expects_sound,
        fire_required=expected_outcome in {"miss", "hit_survive", "kill"},
    )
    row["motion_acceptance"] = motion_acceptance
    row["data_spec_sha256"] = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    return row


def build_scenarios() -> list[dict[str, Any]]:
    report = json.loads(
        v2.PREFLIGHT_REPORT.read_text(encoding="utf-8")
    )
    catalog = v2.load_catalog()
    appearances = [
        (item["model"], int(item["skin"]))
        for item in catalog["enemy_appearances"]
    ]
    dm_pairs = [
        pair
        for map_row in report["map_summary"]
        if "dm" in catalog["maps"][map_row["map"]]["gametypes"]
        for pair in map_row["accepted_pairs"]
    ]
    long_pairs = sorted(
        (
            pair
            for pair in dm_pairs
            if pair["distance_bin"]
            in {"medium", "far", "very_far", "extreme"}
            and abs(
                pair["enemy_origin"][2] - pair["player_origin"][2]
            )
            <= 96
        ),
        key=lambda pair: (
            {
                "extreme": 0,
                "very_far": 1,
                "far": 2,
                "medium": 3,
            }[pair["distance_bin"]],
            abs(
                pair["enemy_origin"][2] - pair["player_origin"][2]
            ),
            pair["map"],
        ),
    )
    extreme_pairs = [
        pair for pair in long_pairs if pair["distance_bin"] == "extreme"
    ]
    if len(long_pairs) < 6 or len(extreme_pairs) < 2:
        raise capture.CaptureFailure("motion_geometry_pool_too_small")
    motion_defs = [
        (
            "motion_forward_long",
            "translation_large_forward",
            {"min_path_length": 700, "min_net_displacement": 512},
            (0.0,),
            long_pairs,
        ),
        (
            "motion_forward_long",
            "translation_very_large_forward",
            {"min_path_length": 1200, "min_net_displacement": 1024},
            (0.0,),
            extreme_pairs,
        ),
        (
            "motion_strafe_long",
            "translation_large_strafe",
            {
                "min_path_length": 700,
                "min_maximum_displacement": 512,
            },
            (90.0, -90.0),
            long_pairs,
        ),
        (
            "motion_diagonal_long",
            "translation_large_diagonal",
            {
                "min_path_length": 700,
                "min_maximum_displacement": 512,
            },
            (36.869898, -36.869898),
            long_pairs,
        ),
        (
            "motion_turn90",
            "joint_large_move_yaw90",
            {
                "min_path_length": 650,
                "min_maximum_displacement": 400,
                "min_yaw_range": 85,
                "min_monotonic_yaw": 85,
            },
            (-45.0, 0.0, 45.0),
            long_pairs,
        ),
        (
            "motion_turn180",
            "joint_large_move_yaw180",
            {
                "min_path_length": 650,
                "min_maximum_displacement": 350,
                "min_yaw_range": 170,
                "min_monotonic_yaw": 170,
            },
            (-90.0, 0.0, 90.0),
            long_pairs,
        ),
        (
            "motion_lookback180",
            "joint_move_lookback180",
            {
                "min_path_length": 750,
                "min_maximum_displacement": 350,
                "min_yaw_range": 170,
                "min_monotonic_yaw": 170,
            },
            (0.0, 90.0, -90.0),
            long_pairs,
        ),
    ]
    scenarios: list[dict[str, Any]] = []
    weapons = list(v2.WEAPONS)
    for index, (
        program,
        category,
        acceptance,
        yaw_adjustments,
        pool,
    ) in enumerate(motion_defs, 1):
        rotated = pool[index - 1 :] + pool[: index - 1]
        geometries = geometry_candidates(rotated, yaw_adjustments)
        geometry = geometries[0]
        row = base_row(
            episode_id=f"md_foundation_solo_{index:02d}",
            role="foundation_no_enemy",
            category=category,
            map_name=geometry["map"],
            gametype=geometry["gametype"],
            player_origin=geometry["player_origin"],
            weapon=weapons[(index - 1) % len(weapons)],
            action_program=program,
            seed=4_000_000 + index,
            expects_sound=True,
            motion_acceptance=acceptance,
        )
        row["player"]["yaw"] = round(geometry["player_yaw"], 6)
        row["geometry_candidates"] = geometries
        scenarios.append(row)
    camera_defs = [
        (
            "camera_yaw90_smooth",
            "camera_yaw90_smooth",
            {
                "min_yaw_range": 85,
                "max_yaw_range": 100,
                "min_monotonic_yaw": 85,
                "max_yaw_frame_step": 2,
                "max_maximum_displacement": 64,
            },
        ),
        (
            "camera_yaw180_smooth",
            "camera_yaw180_smooth",
            {
                "min_yaw_range": 170,
                "max_yaw_range": 195,
                "min_monotonic_yaw": 170,
                "max_yaw_frame_step": 2,
                "max_maximum_displacement": 64,
            },
        ),
        (
            "camera_yaw360_smooth",
            "camera_yaw360_smooth",
            {
                "min_yaw_range": 345,
                "min_monotonic_yaw": 345,
                "max_yaw_frame_step": 2,
                "max_maximum_displacement": 64,
            },
        ),
        (
            "camera_yaw90_snap",
            "camera_yaw90_snap",
            {
                "min_yaw_range": 85,
                "max_yaw_range": 100,
                "min_monotonic_yaw": 85,
                "min_yaw_frame_step": 5,
                "max_maximum_displacement": 64,
            },
        ),
        (
            "camera_pitch60_scan",
            "camera_pitch60_scan",
            {
                "min_pitch_range": 55,
                "max_maximum_displacement": 64,
            },
        ),
    ]
    dm_maps = [
        item
        for item in report["map_summary"]
        if "dm" in catalog["maps"][item["map"]]["gametypes"]
        and item["accepted_positions"]
    ]
    for offset, (program, category, acceptance) in enumerate(
        camera_defs, 8
    ):
        map_row = dm_maps[(offset * 3) % len(dm_maps)]
        position = map_row["accepted_positions"][
            offset % len(map_row["accepted_positions"])
        ]["player_origin"]
        scenarios.append(
            base_row(
                episode_id=f"md_foundation_solo_{offset:02d}",
                role="foundation_no_enemy",
                category=category,
                map_name=map_row["map"],
                gametype=map_row["gametype"],
                player_origin=position,
                weapon=weapons[(offset - 1) % len(weapons)],
                action_program=program,
                seed=4_000_000 + offset,
                expects_sound=False,
                motion_acceptance=acceptance,
            )
        )
    by_distance: dict[str, list[dict[str, Any]]] = {
        name: sorted(
            (
                pair
                for pair in dm_pairs
                if pair["distance_bin"] == name
                and abs(
                    pair["enemy_origin"][2]
                    - pair["player_origin"][2]
                )
                <= 96
            ),
            key=lambda pair: (
                abs(
                    pair["enemy_origin"][2]
                    - pair["player_origin"][2]
                ),
                pair["map"],
            ),
        )
        for name in ("close", "near", "far")
    }
    if any(not rows for rows in by_distance.values()):
        raise capture.CaptureFailure("enemy_distance_pool_missing")
    distractor_defs = [
        ("close", "camera_yaw90_smooth", 0.0, "close_exit_fov_yaw90"),
        ("close", "camera_yaw90_snap", -45.0, "close_center_pass_snap"),
        ("close", "camera_pitch60_scan", 8.0, "close_pitch_scan"),
        ("close", "camera_yaw180_smooth", -90.0, "close_enter_exit_yaw180"),
        ("near", "camera_yaw90_smooth", -45.0, "near_center_pass_yaw90"),
        ("near", "camera_yaw180_pitch60", -90.0, "near_yaw_pitch_scan"),
        ("near", "camera_yaw90_snap", 0.0, "near_exit_fov_snap"),
        ("far", "camera_yaw90_smooth", 24.0, "far_retained_minority"),
    ]
    for index, (distance, program, yaw_offset, category) in enumerate(
        distractor_defs, 1
    ):
        pool = by_distance[distance]
        pool = pool[(index - 1) % len(pool) :] + pool[
            : (index - 1) % len(pool)
        ]
        pair = pool[0]
        model, skin = appearances[(index - 1) % len(appearances)]
        acceptance: dict[str, float]
        if program == "camera_yaw90_snap":
            acceptance = {
                "min_yaw_range": 85,
                "min_yaw_frame_step": 5,
            }
        elif program == "camera_pitch60_scan":
            acceptance = {"min_pitch_range": 55}
        elif program == "camera_yaw180_smooth":
            acceptance = {"min_yaw_range": 170}
        elif program == "camera_yaw180_pitch60":
            acceptance = {
                "min_yaw_range": 170,
                "min_pitch_range": 55,
            }
        else:
            acceptance = {"min_yaw_range": 85}
        row = base_row(
            episode_id=f"md_foundation_enemy_{index:02d}",
            role="foundation_enemy_distractor",
            category=category,
            map_name=pair["map"],
            gametype=pair["gametype"],
            player_origin=pair["player_origin"],
            enemy_origin=pair["enemy_origin"],
            enemy_model=model,
            enemy_skin=skin,
            enemy_color=(0, 68, 204)[(index - 1) % 3],
            weapon=weapons[(index + 2) % len(weapons)],
            action_program=program,
            seed=4_100_000 + index,
            yaw_offset=yaw_offset,
            expected_distance_bin=distance,
            expects_sound=False,
            motion_acceptance=acceptance,
        )
        row["initial_yaw_offset"] = yaw_offset
        row["pair_candidates"] = pool
        scenarios.append(row)
    causal_defs = [
        (
            "close",
            "causal_turn90_no_fire",
            0.0,
            "no_fire",
            "Blaster",
            500.0,
            "close_turn90_no_response",
            {"min_yaw_range": 85},
        ),
        (
            "close",
            "causal_turn180_miss",
            0.0,
            "miss",
            "Vortex",
            500.0,
            "close_turn180_then_miss",
            {"min_yaw_range": 170},
        ),
        (
            "near",
            "causal_delayed",
            -18.0,
            "hit_survive",
            "Shotgun",
            999.0,
            "near_delayed_hit_survive",
            {},
        ),
        (
            "near",
            "causal_reacquire",
            0.0,
            "kill",
            "MachineGun",
            1.0,
            "near_reacquire_kill",
            {},
        ),
    ]
    for index, (
        distance,
        program,
        yaw_offset,
        outcome,
        weapon,
        health,
        category,
        acceptance,
    ) in enumerate(causal_defs, 1):
        pool = by_distance[distance]
        pool = pool[(index + 3) % len(pool) :] + pool[
            : (index + 3) % len(pool)
        ]
        pair = pool[0]
        model, skin = appearances[8 + index - 1]
        row = base_row(
            episode_id=f"md_causal_{index:02d}",
            role="causal_interaction",
            category=category,
            map_name=pair["map"],
            gametype=pair["gametype"],
            player_origin=pair["player_origin"],
            enemy_origin=pair["enemy_origin"],
            enemy_model=model,
            enemy_skin=skin,
            enemy_color=(0, 68, 204)[index % 3],
            weapon=weapon,
            action_program=program,
            seed=4_200_000 + index,
            yaw_offset=yaw_offset,
            expected_outcome=outcome,
            expected_distance_bin=distance,
            enemy_health=health,
            expects_sound=outcome != "no_fire",
            motion_acceptance=acceptance,
        )
        row["initial_yaw_offset"] = yaw_offset
        row["pair_candidates"] = pool
        scenarios.append(row)
    if len(scenarios) != 24:
        raise AssertionError(len(scenarios))
    return scenarios


def command_generate(_: argparse.Namespace) -> int:
    capture.require_conda()
    report = json.loads(
        v2.PREFLIGHT_REPORT.read_text(encoding="utf-8")
    )
    if not report.get("pass"):
        raise capture.CaptureFailure("preflight_not_passed")
    rows = build_scenarios()
    write_jsonl(SCENARIOS_PATH, rows)
    print(f"scenarios={SCENARIOS_PATH}")
    print(f"roles={dict(Counter(row['dataset_role'] for row in rows))}")
    print(
        "enemy_distance_intent="
        + str(
            dict(
                Counter(
                    row["policy_labels"]["expected_distance_bin"]
                    for row in rows
                    if row["enemy_present"]
                )
            )
        )
    )
    return 0


def publish_attempt(
    row: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    stage = Path(result["stage"])
    package = stage / "package"
    attempt_id = result["attempt_id"]
    episode_destination = PILOT_ROOT / "episodes" / row["episode_id"]
    raw_destination = PILOT_ROOT / "raw" / attempt_id
    package_hashes = v2.copytree_verified(
        package, episode_destination
    )
    raw_hashes = v2.copytree_verified(stage, raw_destination)
    qa = json.loads(
        (episode_destination / "qa.json").read_text(encoding="utf-8")
    )
    semantic = v2.semantic_outcome(row, qa)
    manifest = {
        "schema_version": (
            "xonotic-v2-motion-distance-pilot-manifest-v1"
        ),
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "split": row["split"],
        "dataset_role": row["dataset_role"],
        "category": row["category"],
        "map": row["map"],
        "gametype": row["gametype"],
        "weapon": row["weapon"],
        "enemy_present": row["enemy_present"],
        "enemy_model": row["enemy_model"],
        "enemy_skin": row["enemy_skin"],
        "enemy_color": row["enemy_color"],
        "expected_distance_bin": row["policy_labels"].get(
            "expected_distance_bin"
        ),
        "actual_distance_bin": qa["target_relation"].get(
            "actual_distance_bin"
        ),
        "actual_target_relation": qa["target_relation"][
            "actual_target_relation"
        ],
        "intent_outcome": row["acceptance"].get("actual_outcome"),
        "semantic_outcome": semantic,
        "engine_outcome_bin": qa["events"]["actual_outcome_bin"],
        "hit_rate": qa["events"]["hit_rate"],
        "motion": qa["motion"],
        "episode_path": str(episode_destination),
        "raw_path": str(raw_destination),
        "package_sha256": package_hashes,
        "raw_sha256": raw_hashes,
        "qa": {
            "renderer": qa["runtime"]["renderer"],
            "frames": qa["video"]["frames"],
            "audio_samples": qa["audio"]["samples_per_channel"],
            "mapping": qa["mapping"]["success_rate"],
            "audio_onset_max_ms": qa["audio"]["max_onset_error_ms"],
            "event_linkage": qa["events"]["linkage_rate"],
        },
        "accepted_utc": capture.utc_now(),
    }
    with LOCK:
        capture.append_jsonl(ACCEPTED_PATH, manifest)
    capture.clean_stage(stage)
    return manifest


def reject_attempt(
    row: dict[str, Any],
    retry: int,
    failure: Exception,
    stage: Path,
) -> dict[str, Any]:
    attempt_id = f"{row['episode_id']}_a{retry + 1:02d}"
    destination = PILOT_ROOT / "rejected" / attempt_id
    hashes: dict[str, str] = {}
    if stage.exists() and not destination.exists():
        hashes = v2.copytree_verified(stage, destination)
        capture.clean_stage(stage)
    rejection = {
        "schema_version": (
            "xonotic-v2-motion-distance-pilot-reject-v1"
        ),
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "dataset_role": row["dataset_role"],
        "category": row["category"],
        "map": row["map"],
        "reason": (
            failure.reason
            if isinstance(failure, capture.CaptureFailure)
            else type(failure).__name__
        ),
        "detail": (
            failure.detail
            if isinstance(failure, capture.CaptureFailure)
            else str(failure)
        ),
        "preserved_path": str(destination) if destination.exists() else None,
        "preserved_sha256": hashes,
        "rejected_utc": capture.utc_now(),
    }
    with LOCK:
        capture.append_jsonl(REJECTS_PATH, rejection)
    return rejection


def capture_one(
    base: dict[str, Any], max_retries: int
) -> dict[str, Any]:
    existing = {
        row["episode_id"]: row
        for row in capture.load_jsonl(ACCEPTED_PATH)
    }
    if base["episode_id"] in existing:
        return existing[base["episode_id"]]
    prior = [
        row
        for row in capture.load_jsonl(REJECTS_PATH)
        if row["episode_id"] == base["episode_id"]
    ]
    retry_base = max(
        (
            int(row["attempt_id"].rsplit("_a", 1)[1]) for row in prior
        ),
        default=0,
    )
    for retry in range(retry_base, retry_base + max_retries):
        row = apply_variant(base, retry)
        stage = (
            capture.TMP_ROOT
            / "raw"
            / f"{row['episode_id']}_a{retry + 1:02d}"
        )
        print(
            f"capture id={row['episode_id']} attempt={retry + 1} "
            f"map={row['map']} category={row['category']}",
            flush=True,
        )
        try:
            result = capture.execute_attempt(row, retry, publish=False)
            package = Path(result["stage"]) / "package"
            relation = v2.relation_metrics(
                package, bool(row["enemy_present"])
            )
            qa_path = package / "qa.json"
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            qa["target_relation"] = relation
            metrics = motion_metrics(package)
            motion_gates = validate_motion(row, metrics)
            qa["motion"] = metrics
            qa["motion_gates"] = motion_gates
            qa["gates"].update(
                {
                    f"motion_{name}": passed
                    for name, passed in motion_gates.items()
                }
            )
            atomic_json(qa_path, qa)
            episode_path = package / "episode.json"
            episode = json.loads(
                episode_path.read_text(encoding="utf-8")
            )
            episode["actual_target_relation"] = relation
            episode["actual_motion"] = metrics
            atomic_json(episode_path, episode)
            v2.validate_post_bucket(row, qa)
            if not all(motion_gates.values()):
                raise capture.CaptureFailure(
                    "motion_bucket_mismatch",
                    capture.canonical_json(
                        {
                            "gates": motion_gates,
                            "motion": metrics,
                            "acceptance": row["motion_acceptance"],
                        }
                    ),
                )
            manifest = publish_attempt(row, result)
            print(
                f"accepted id={row['episode_id']} "
                f"net={metrics['net_displacement_3d']:.1f} "
                f"maxdisp={metrics['maximum_displacement_from_start']:.1f} "
                f"yaw={metrics['yaw_range_deg']:.1f} "
                f"pitch={metrics['pitch_range_deg']:.1f} "
                f"distance={manifest['actual_distance_bin']}",
                flush=True,
            )
            return manifest
        except Exception as exc:
            rejection = reject_attempt(row, retry, exc, stage)
            print(
                f"reject id={row['episode_id']} "
                f"reason={rejection['reason']} "
                f"detail={rejection['detail'][:400]}",
                flush=True,
            )
    raise capture.CaptureFailure(
        "motion_distance_retry_exhausted", base["episode_id"]
    )


def command_pilot(args: argparse.Namespace) -> int:
    capture.require_conda()
    if not SCENARIOS_PATH.is_file():
        command_generate(args)
    rows = capture.load_jsonl(SCENARIOS_PATH)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(capture_one, row, args.max_retries): row
            for row in rows
        }
        for index, future in enumerate(
            concurrent.futures.as_completed(futures), 1
        ):
            row = futures[future]
            future.result()
            print(
                f"progress {index}/{len(rows)} {row['episode_id']}",
                flush=True,
            )
    manifests = capture.load_jsonl(ACCEPTED_PATH)
    role_counts = Counter(row["dataset_role"] for row in manifests)
    distance_counts = Counter(
        row["actual_distance_bin"]
        for row in manifests
        if row["enemy_present"]
    )
    checks = {
        "exact_24_unique": len(manifests)
        == len({row["episode_id"] for row in manifests})
        == 24,
        "roles": role_counts == Counter(EXPECTED_ROLES),
        "enemy_distances": distance_counts
        == Counter(EXPECTED_ENEMY_DISTANCES),
        "near_priority": (
            distance_counts["close"] + distance_counts["near"]
        )
        / sum(distance_counts.values())
        >= 0.8,
        "far_plus_cap": (
            distance_counts["far"]
            + distance_counts["very_far"]
            + distance_counts["extreme"]
        )
        / sum(distance_counts.values())
        <= 0.2,
        "large_displacement": sum(
            row["motion"]["maximum_displacement_from_start"] >= 512
            for row in manifests
        )
        >= 4,
        "yaw_90": sum(
            row["motion"]["yaw_range_deg"] >= 85 for row in manifests
        )
        >= 14,
        "yaw_180": sum(
            row["motion"]["yaw_range_deg"] >= 170 for row in manifests
        )
        >= 7,
        "yaw_360": sum(
            row["motion"]["yaw_range_deg"] >= 345 for row in manifests
        )
        >= 1,
        "pitch_55": sum(
            row["motion"]["pitch_range_deg"] >= 55 for row in manifests
        )
        >= 3,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "motion_distance_final_gate",
            capture.canonical_json(checks),
        )
    summary = {
        "schema_version": "xonotic-v2-motion-distance-summary-v1",
        "created_utc": capture.utc_now(),
        "checks": checks,
        "accepted": len(manifests),
        "rejected_attempts": len(capture.load_jsonl(REJECTS_PATH)),
        "roles": dict(role_counts),
        "distance_bins": dict(distance_counts),
        "categories": dict(
            Counter(row["category"] for row in manifests)
        ),
    }
    atomic_json(SUMMARY_PATH, summary)
    print(f"complete accepted={len(manifests)}")
    return 0


def make_preview(row: dict[str, Any]) -> Path:
    media = PREVIEW_ROOT / "media"
    media.mkdir(parents=True, exist_ok=True)
    source = Path(row["episode_path"]) / "video.mkv"
    destination = media / f"{row['episode_id']}.mp4"
    if destination.is_file():
        return destination
    temporary = media / f".{row['episode_id']}.tmp.mp4"
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(temporary),
        ],
        check=False,
    )
    if completed.returncode:
        temporary.unlink(missing_ok=True)
        raise capture.CaptureFailure(
            "preview_encode_failed", row["episode_id"]
        )
    os.replace(temporary, destination)
    return destination


def command_html(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(ACCEPTED_PATH)
    if len(rows) != 24:
        raise capture.CaptureFailure(
            "html_requires_complete_pilot", f"accepted={len(rows)}"
        )
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for index, path in enumerate(
            executor.map(make_preview, rows), 1
        ):
            print(f"preview {index}/24 {path}", flush=True)
    cards: list[str] = []
    for row in rows:
        motion = row["motion"]
        enemy = (
            f"{row['enemy_model']} / skin {row['enemy_skin']}"
            if row["enemy_present"]
            else "absent"
        )
        cards.append(
            f"""
<article class="card" data-role="{html.escape(row['dataset_role'])}"
 data-distance="{html.escape(str(row.get('actual_distance_bin') or 'none'))}">
 <video controls preload="metadata" src="media/{html.escape(row['episode_id'])}.mp4"></video>
 <h2>{html.escape(row['episode_id'])}</h2>
 <p class="role">{html.escape(row['dataset_role'])}</p>
 <dl>
  <dt>Category</dt><dd>{html.escape(row['category'])}</dd>
  <dt>Map / weapon</dt><dd>{html.escape(row['map'])} / {html.escape(row['weapon'])}</dd>
  <dt>Enemy</dt><dd>{html.escape(enemy)}</dd>
  <dt>Distance</dt><dd>{html.escape(str(row.get('actual_distance_bin') or '-'))}</dd>
  <dt>Relation</dt><dd>{html.escape(row['actual_target_relation'])}</dd>
  <dt>Outcome</dt><dd>{html.escape(row['semantic_outcome'])}</dd>
  <dt>Path / net / max</dt><dd>{motion['path_length_3d']:.0f} / {motion['net_displacement_3d']:.0f} / {motion['maximum_displacement_from_start']:.0f} units</dd>
  <dt>Yaw range</dt><dd>{motion['yaw_range_deg']:.1f} deg ({html.escape(motion['yaw_range_bin'])})</dd>
  <dt>Pitch range</dt><dd>{motion['pitch_range_deg']:.1f} deg ({html.escape(motion['pitch_range_bin'])})</dd>
 </dl>
</article>"""
        )
    roles = sorted({row["dataset_role"] for row in rows})
    distances = ["close", "near", "far", "none"]
    role_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in roles
    )
    distance_options = "".join(
        f'<option value="{value}">{value}</option>' for value in distances
    )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xonotic 大运动与近距敌人补采</title>
<style>
:root {{ color-scheme:dark;font-family:Inter,system-ui,sans-serif }}
body {{ margin:0;background:#0b1017;color:#edf3fa }}
header {{ position:sticky;top:0;z-index:2;padding:18px 24px;background:#111a26ee;border-bottom:1px solid #2b3a4c }}
h1 {{ margin:0 0 8px;font-size:22px }}
.controls {{ display:flex;gap:12px;flex-wrap:wrap }}
select {{ background:#1c2837;color:#fff;border:1px solid #41536a;border-radius:7px;padding:7px 10px }}
main {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px;padding:22px }}
.card {{ background:#141d29;border:1px solid #2c3a4d;border-radius:12px;overflow:hidden }}
video {{ display:block;width:100%;aspect-ratio:16/9;background:#000 }}
h2,.role,dl {{ margin-left:16px;margin-right:16px }}
h2 {{ margin-bottom:4px;font-size:17px }} .role {{ margin-top:0;color:#75d4ff }}
dl {{ display:grid;grid-template-columns:125px 1fr;gap:5px 10px;font-size:13px }}
dt {{ color:#94a8be }} dd {{ margin:0;overflow-wrap:anywhere }} .hidden {{ display:none }}
</style></head><body><header>
<h1>Xonotic v2 — 大运动与近距敌人补采（24 条）</h1>
<div class="controls">
<label>Role <select id="role"><option value="">全部</option>{role_options}</select></label>
<label>Distance <select id="distance"><option value="">全部</option>{distance_options}</select></label>
</div></header><main>{''.join(cards)}</main>
<script>
const role=document.querySelector('#role'),distance=document.querySelector('#distance');
function filterCards(){{
 document.querySelectorAll('.card').forEach(card=>{{
  const show=(!role.value||card.dataset.role===role.value)&&
   (!distance.value||card.dataset.distance===distance.value);
  card.classList.toggle('hidden',!show);if(!show)card.querySelector('video').pause();
 }});
}}
role.addEventListener('change',filterCards);distance.addEventListener('change',filterCards);
</script></body></html>
"""
    atomic_text(PREVIEW_ROOT / "index.html", document)
    print(f"html={PREVIEW_ROOT / 'index.html'}")
    return 0


def command_audit(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(ACCEPTED_PATH)
    rejects = capture.load_jsonl(REJECTS_PATH)
    if len(rows) != 24:
        raise capture.CaptureFailure(
            "audit_requires_complete_pilot", f"accepted={len(rows)}"
        )
    failures: list[str] = []
    qa_rows: list[dict[str, Any]] = []
    hash_jobs: list[tuple[str, Path, str]] = []
    probes: dict[str, Any] = {}
    for row in rows:
        episode = Path(row["episode_path"])
        files = {
            path.name for path in episode.iterdir() if path.is_file()
        }
        if files != REQUIRED_FILES:
            failures.append(f"{row['episode_id']}:files")
        qa = json.loads(
            (episode / "qa.json").read_text(encoding="utf-8")
        )
        qa_rows.append(qa)
        if not all(qa["gates"].values()):
            failures.append(f"{row['episode_id']}:qa_gates")
        for relative, expected in row["package_sha256"].items():
            hash_jobs.append(
                (
                    f"formal:{row['episode_id']}:{relative}",
                    episode / relative,
                    expected,
                )
            )
        raw = Path(row["raw_path"])
        for relative, expected in row["raw_sha256"].items():
            hash_jobs.append(
                (
                    f"raw:{row['attempt_id']}:{relative}",
                    raw / relative,
                    expected,
                )
            )
    for reject in rejects:
        root = Path(reject["preserved_path"])
        for relative, expected in reject["preserved_sha256"].items():
            hash_jobs.append(
                (
                    f"reject:{reject['attempt_id']}:{relative}",
                    root / relative,
                    expected,
                )
            )
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        hash_results = list(executor.map(final_audit.sha_job, hash_jobs))
    hash_failures = [
        {"label": label, "actual": actual}
        for label, passed, actual in hash_results
        if not passed
    ]
    if hash_failures:
        failures.append(f"hash_mismatch:{len(hash_failures)}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(
                final_audit.ffprobe_episode,
                Path(row["episode_path"]) / "video.mkv",
            ): row["episode_id"]
            for row in rows
        }
        for future in concurrent.futures.as_completed(futures):
            probes[futures[future]] = future.result()
    for episode_id, probe in probes.items():
        if not (
            probe["decoded_frames"] == 320
            and probe["decoded_audio_samples_per_channel"] == 240000
            and probe["video_codec"] == "h264"
            and probe["video_profile"] == "High"
            and probe["audio_codec"] == "flac"
        ):
            failures.append(f"{episode_id}:media")
    distance_counts = Counter(
        row["actual_distance_bin"] for row in rows if row["enemy_present"]
    )
    checks = {
        "exact_24": len(rows)
        == len({row["episode_id"] for row in rows})
        == 24,
        "roles": Counter(row["dataset_role"] for row in rows)
        == Counter(EXPECTED_ROLES),
        "distance_mix": distance_counts
        == Counter(EXPECTED_ENEMY_DISTANCES),
        "all_motion_gates": all(
            all(qa["motion_gates"].values()) for qa in qa_rows
        ),
        "all_base_qa_gates": all(
            all(qa["gates"].values()) for qa in qa_rows
        ),
        "hashes": not hash_failures,
        "media": not any(":media" in item for item in failures),
    }
    if not all(checks.values()):
        failures.append(capture.canonical_json(checks))
    audit = {
        "schema_version": "xonotic-v2-motion-distance-audit-v1",
        "created_utc": capture.utc_now(),
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "accepted": len(rows),
        "rejected_attempts": len(rejects),
        "distance_bins": dict(distance_counts),
        "near_share": (
            distance_counts["close"] + distance_counts["near"]
        )
        / sum(distance_counts.values()),
        "motion": {
            "net_ge512": sum(
                row["motion"]["net_displacement_3d"] >= 512
                for row in rows
            ),
            "max_displacement_ge512": sum(
                row["motion"]["maximum_displacement_from_start"] >= 512
                for row in rows
            ),
            "yaw_ge90": sum(
                row["motion"]["yaw_range_deg"] >= 85 for row in rows
            ),
            "yaw_ge180": sum(
                row["motion"]["yaw_range_deg"] >= 170 for row in rows
            ),
            "yaw_ge360": sum(
                row["motion"]["yaw_range_deg"] >= 345 for row in rows
            ),
            "pitch_ge55": sum(
                row["motion"]["pitch_range_deg"] >= 55 for row in rows
            ),
        },
        "qa": {
            "frames_total": sum(
                probe["decoded_frames"] for probe in probes.values()
            ),
            "audio_samples_total": sum(
                probe["decoded_audio_samples_per_channel"]
                for probe in probes.values()
            ),
            "mapping_min": min(
                qa["mapping"]["success_rate"] for qa in qa_rows
            ),
            "onset_max_ms": max(
                qa["audio"]["max_onset_error_ms"] for qa in qa_rows
            ),
            "linkage_min": min(
                qa["events"]["linkage_rate"] for qa in qa_rows
            ),
            "renderer": sorted(
                {qa["runtime"]["renderer"] for qa in qa_rows}
            ),
        },
        "hashes": {
            "files_checked": len(hash_jobs),
            "mismatches": hash_failures,
        },
        "performance": {
            "live_wall_mean": mean(
                qa["runtime"]["live_wall_seconds"] for qa in qa_rows
            ),
            "render_wall_mean": mean(
                qa["runtime"]["render_wall_seconds"] for qa in qa_rows
            ),
            "x264_mean": mean(
                qa["runtime"]["x264_video_seconds_per_wall_second"]
                for qa in qa_rows
            ),
        },
    }
    atomic_json(AUDIT_PATH, audit)
    if failures:
        raise capture.CaptureFailure(
            "motion_distance_audit_failed",
            capture.canonical_json(failures),
        )
    print(f"audit={AUDIT_PATH}")
    return 0


def command_report(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(ACCEPTED_PATH)
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    lines = [
        "# Xonotic v2 large-motion and near-distance Pilot",
        "",
        f"Generated UTC: `{capture.utc_now()}`",
        "",
        "**PASS for this bounded supplement; formal collection remains stopped.**",
        "",
        f"- Accepted: {len(rows)}",
        f"- Rejected attempts: {audit['rejected_attempts']}",
        f"- HTML: `{PREVIEW_ROOT / 'index.html'}`",
        f"- Manifest: `{ACCEPTED_PATH}`",
        (
            "- Enemy distance mix: "
            + ", ".join(
                f"`{key}`={value}"
                for key, value in audit["distance_bins"].items()
            )
            + f"; close+near={audit['near_share']:.1%}."
        ),
        (
            f"- Large motion: max displacement >=512 in "
            f"{audit['motion']['max_displacement_ge512']} episodes; "
            f"yaw >=90/180/360 in {audit['motion']['yaw_ge90']}/"
            f"{audit['motion']['yaw_ge180']}/"
            f"{audit['motion']['yaw_ge360']} episodes; pitch >=55 in "
            f"{audit['motion']['pitch_ge55']} episodes."
        ),
        (
            f"- Independent QA: {audit['qa']['frames_total']} decoded "
            f"frames, {audit['qa']['audio_samples_total']} samples/channel, "
            f"{audit['hashes']['files_checked']} SHA256 checks, 0 mismatch."
        ),
        "",
        "| Episode | Role | Category | Map | Distance | Path | Net | Max displacement | Yaw range | Pitch range | Outcome |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        motion = row["motion"]
        lines.append(
            f"| `{row['episode_id']}` | `{row['dataset_role']}` | "
            f"`{row['category']}` | `{row['map']}` | "
            f"`{row.get('actual_distance_bin') or '-'}` | "
            f"{motion['path_length_3d']:.1f} | "
            f"{motion['net_displacement_3d']:.1f} | "
            f"{motion['maximum_displacement_from_start']:.1f} | "
            f"{motion['yaw_range_deg']:.1f} | "
            f"{motion['pitch_range_deg']:.1f} | "
            f"`{row['semantic_outcome']}` |"
        )
    lines += [
        "",
        "This supplement is `split=v2_motion_distance_pilot` and is excluded "
        "from Stage 1 and Stage 2 training.",
        "",
    ]
    atomic_text(REPORT_PATH, "\n".join(lines))
    print(f"report={REPORT_PATH}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.set_defaults(func=command_generate)
    pilot = sub.add_parser("pilot")
    pilot.add_argument("--workers", type=int, default=2)
    pilot.add_argument("--max-retries", type=int, default=10)
    pilot.set_defaults(func=command_pilot)
    html_parser = sub.add_parser("html")
    html_parser.set_defaults(func=command_html)
    audit = sub.add_parser("audit")
    audit.set_defaults(func=command_audit)
    report = sub.add_parser("report")
    report.set_defaults(func=command_report)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
