                      
"""Isolated collision-safe, visibly active-camera successor to long60 v7.

The v7 release, short Stage-2 release, and Stage-1 pipeline remain immutable.
This overlay changes only long60 geometry, camera actions, runtime provenance,
and QA.  Enemy motion is still streamed from the manifest and the camera is
open loop: it never reads live enemy or player state.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V7_PATH = Path(__file__).with_name(
    "long60_production_ref42_v7_multimap_hitscan.py"
)
SPEC = importlib.util.spec_from_file_location("long60_ref42_v8_base", V7_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v7 module: {V7_PATH}")
v7 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v7
SPEC.loader.exec_module(v7)


RELEASE_ID = (
    "stage2_long60_multi_enemy_ref42_multimap_hitscan_"
    "collision_camera_30h_20260829_v8"
)
SCHEMA_VERSION = (
    "xonotic-stage2-long60-ref42-multimap-hitscan-"
    "collision-camera-production-manifest-v1"
)
EPISODE_PREFIX = "s2l60ref42mmhs_v8"
BUILD_TAG = "capture-3688c19201b0-aarch64"
BUILD_COMMIT = "3688c19201b01aeeace17031bd2b0c96673befbd"
CONFIG_PATH = ROOT / "configs" / "LONG60_COLLISION_CAMERA_V8.json"
CONFIG_SHA256 = "b2d7c28ac5a16e21db9f57d7b38ac25e13a9d52519f93796683964d75847d476"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if sha256(CONFIG_PATH) != CONFIG_SHA256:
    raise RuntimeError("long60 v8 collision/camera config hash mismatch")
OVERLAY = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
if OVERLAY.get("source_config_sha256") != v7.CONFIG_SHA256:
    raise RuntimeError("v8 source-config lineage mismatch")

CONFIG = json.loads(json.dumps(v7.CONFIG))
CONFIG["v8_collision_camera_overlay"] = OVERLAY
MAPS: dict[str, dict[str, Any]] = CONFIG["maps"]
WEAPONS: dict[str, dict[str, Any]] = CONFIG["weapons"]
GEOMETRY: dict[str, dict[str, dict[str, Any]]] = OVERLAY[
    "geometry_by_map_template"
]
CAMERA_CONFIG: dict[str, Any] = OVERLAY["camera_policy"]
COLLISION_CONFIG: dict[str, Any] = OVERLAY["collision_policy"]
PLAYER_MOTION_CONFIG: dict[str, Any] = OVERLAY["player_motion_policy"]
INTERACTION_AIM_CONFIG: dict[str, Any] = OVERLAY["interaction_aim_policy"]
LIFECYCLE_HEALTH_OVERRIDES: dict[str, dict[str, Any]] = OVERLAY[
    "lifecycle_health_overrides"
]
LIFECYCLE_HEALTH_CALIBRATION: dict[str, Any] = OVERLAY[
    "lifecycle_health_calibration"
]
SOURCE_CONTROLLED_RETURN_HEALTH_BY_WEAPON = {
    weapon: float(config["controlled_return_slot1_kill_health"])
    for weapon, config in WEAPONS.items()
}

for override_weapon, override_values in LIFECYCLE_HEALTH_OVERRIDES.items():
    if override_weapon not in WEAPONS:
        raise RuntimeError(f"unknown v8 health-override weapon: {override_weapon}")
    for override_key, override_value in override_values.items():
        if override_key in {
            "reason",
            "controlled_return_slot1_kill_health_by_map",
        }:
            continue
        if override_key not in WEAPONS[override_weapon]:
            raise RuntimeError(
                f"unknown v8 health override: {override_weapon}/{override_key}"
            )
        WEAPONS[override_weapon][override_key] = float(override_value)


def controlled_return_slot1_health(map_name: str, weapon_name: str) -> float:
    by_map = LIFECYCLE_HEALTH_OVERRIDES.get(weapon_name, {}).get(
        "controlled_return_slot1_kill_health_by_map"
    )
    if by_map is None:
        return SOURCE_CONTROLLED_RETURN_HEALTH_BY_WEAPON[weapon_name]
    if set(by_map) != set(MAPS):
        raise RuntimeError(
            f"incomplete v8 map-specific health override: {weapon_name}"
        )
    value = float(by_map[map_name])
    if not math.isfinite(value) or value <= 0.0:
        raise RuntimeError(
            f"invalid v8 health override: {map_name}/{weapon_name}/{value}"
        )
    return value


HEALTH_CALIBRATION_RECORDS: dict[str, dict[str, Any]] = {}
if (
    LIFECYCLE_HEALTH_CALIBRATION.get("weapon") != "MachineGun"
    or LIFECYCLE_HEALTH_CALIBRATION.get("template") != "controlled_return"
    or set(LIFECYCLE_HEALTH_CALIBRATION.get("cells") or {}) != set(MAPS)
):
    raise RuntimeError("invalid v8 lifecycle health-calibration coverage")
for calibration_map, calibration_cell in LIFECYCLE_HEALTH_CALIBRATION[
    "cells"
].items():
    calibration_path = ROOT / str(calibration_cell["report"])
    if (
        not calibration_path.is_file()
        or sha256(calibration_path) != calibration_cell["report_sha256"]
    ):
        raise RuntimeError(
            f"missing or changed v8 health calibration: {calibration_map}"
        )
    calibration_record = json.loads(
        calibration_path.read_text(encoding="utf-8")
    )
    damage_counts = [
        int(value)
        for value in calibration_record.get(
            "player_damage_events_by_encounter", []
        )
    ]
    first_hits = int(calibration_cell["first_appearance_hits"])
    return_hits = int(calibration_cell["return_total_hits"])
    return_hits_in_block = int(
        calibration_cell["return_hits_in_declared_block"]
    )
    health = controlled_return_slot1_health(calibration_map, "MachineGun")
    calibration_ok = (
        calibration_record.get("passed") is True
        and calibration_record.get("map") == calibration_map
        and calibration_record.get("template") == "controlled_return"
        and calibration_record.get("weapon") == "MachineGun"
        and calibration_record.get("runtime_build") == BUILD_TAG
        and calibration_record.get("runtime_source_commit") == BUILD_COMMIT
        and calibration_record.get("geometry_config_sha256")
        == LIFECYCLE_HEALTH_CALIBRATION["source_config_sha256"]
        and not calibration_record.get("fatal_reasons")
        and int(calibration_record.get("state_count", -1))
        == v7.base.capture.TOTAL_TICKS
        and len(damage_counts) == 5
        and damage_counts[0] == first_hits
        and damage_counts[2] == return_hits
        and 0 < return_hits_in_block <= return_hits
        and first_hits * 10.0 < health
        <= (first_hits + return_hits_in_block) * 10.0
    )
    if not calibration_ok:
        raise RuntimeError(
            f"invalid v8 health calibration: {calibration_map}"
        )
    HEALTH_CALIBRATION_RECORDS[calibration_map] = calibration_record

if set(GEOMETRY) != set(MAPS):
    raise RuntimeError("v8 geometry must cover every v7 map")
if any(set(cells) != set(v7.ORIGINAL_TEMPLATES) for cells in GEOMETRY.values()):
    raise RuntimeError("v8 geometry must cover every map/template cell")

QUALIFICATION_RECORDS: dict[tuple[str, str], dict[str, Any]] = {}
for qualification_map, qualification_cells in GEOMETRY.items():
    for qualification_template, qualification_geometry in qualification_cells.items():
        qualification_path = ROOT / str(
            qualification_geometry.get("qualification_result", "")
        )
        if (
            qualification_geometry.get("qualification")
            != "passed_step18_floor_projection_probe"
            or not qualification_path.is_file()
        ):
            raise RuntimeError(
                "unqualified v8 geometry: "
                f"{qualification_map}/{qualification_template}"
            )
        qualification_record = json.loads(
            qualification_path.read_text(encoding="utf-8")
        )
        qualification_ok = (
            qualification_record.get("passed") is True
            and qualification_record.get("fatal") is None
            and int(qualification_record.get("state_count", -1))
            == v7.base.capture.TOTAL_TICKS
            and qualification_record.get("map") == qualification_map
            and qualification_record.get("template") == qualification_template
            and float(qualification_record.get("angle_degrees"))
            == float(qualification_geometry["angle_degrees"])
            and float(qualification_record.get("trajectory_scale"))
            == float(qualification_geometry["trajectory_scale"])
        )
        if not qualification_ok:
            raise RuntimeError(
                "invalid v8 geometry qualification: "
                f"{qualification_map}/{qualification_template}"
            )
        QUALIFICATION_RECORDS[
            (qualification_map, qualification_template)
        ] = qualification_record


INTERACTION_CELLS = INTERACTION_AIM_CONFIG["cells"]
if set(INTERACTION_CELLS) != set(MAPS):
    raise RuntimeError("v8 interaction aim must cover every map")
if any(
    set(cells) != set(v7.ORIGINAL_TEMPLATES)
    for cells in INTERACTION_CELLS.values()
):
    raise RuntimeError("v8 interaction aim must cover every map/template cell")


def prompt_block_for_server_tick(server_tick: int) -> int:
    """Map a server tick to its exact 0.8 s prompt block.

    The inherited lifecycle QA truncates ``0.8 * 64`` to 51 before dividing,
    which accumulates one block of drift late in a rollout.  Keep the fix
    isolated to v8 and divide by the non-integral block duration instead.
    """

    return math.floor(
        (int(server_tick) - v7.base.capture.WARMUP_TICKS)
        / (v7.base.PROMPT_BLOCK_SECONDS * 64.0)
    )


ORIGINAL_FIRE_BLOCKS_BY_TEMPLATE: dict[str, tuple[int, ...]] = {}
for original_template, original_segments in v7.ORIGINAL_TEMPLATES.items():
    if any(len(segment.fire_blocks) != 1 for segment in original_segments):
        raise RuntimeError(
            f"v8 requires one declared fire block per encounter: {original_template}"
        )
    ORIGINAL_FIRE_BLOCKS_BY_TEMPLATE[original_template] = tuple(
        int(segment.fire_blocks[0]) for segment in original_segments
    )

for interaction_map, interaction_templates in INTERACTION_CELLS.items():
    for interaction_template, interaction_cell in interaction_templates.items():
        configured_fire_blocks = tuple(
            int(value) for value in interaction_cell["fire_blocks"]
        )
        expected_fire_blocks = ORIGINAL_FIRE_BLOCKS_BY_TEMPLATE[
            interaction_template
        ]
        if configured_fire_blocks != expected_fire_blocks:
            raise RuntimeError(
                "v8 fire blocks must preserve the original prompt/lifecycle "
                f"schedule: {interaction_map}/{interaction_template}: "
                f"{configured_fire_blocks} != {expected_fire_blocks}"
            )
        target_ticks = tuple(
            int(value) for value in interaction_cell["target_ticks"]
        )
        if len(target_ticks) != len(configured_fire_blocks):
            raise RuntimeError(
                f"v8 target/fire count mismatch: {interaction_map}/{interaction_template}"
            )
        for target_tick, fire_block in zip(
            target_ticks, configured_fire_blocks, strict=True
        ):
            block_start = v7.base.capture.WARMUP_TICKS + int(
                fire_block * v7.base.PROMPT_BLOCK_SECONDS * 64
            )
            block_end = v7.base.capture.WARMUP_TICKS + int(
                (fire_block + 1) * v7.base.PROMPT_BLOCK_SECONDS * 64
            )
            machinegun_window_end = (
                block_start
                + int(v7.base.FIRE_START_OFFSET_TICKS)
                + int(v7.base.FIRE_DURATION_TICKS)
            )
            if not (
                block_start + int(v7.base.FIRE_START_OFFSET_TICKS)
                <= target_tick
                < min(block_end, machinegun_window_end)
                and prompt_block_for_server_tick(target_tick) == fire_block
            ):
                raise RuntimeError(
                    "v8 interaction target is outside its declared prompt/fire "
                    f"block: {interaction_map}/{interaction_template}/"
                    f"block={fire_block}/tick={target_tick}"
                )

FROZEN_BEARING_TRACES: dict[
    tuple[str, str], tuple[tuple[tuple[int, float], ...], ...]
] = {}
INTERACTION_BASELINE_RECORDS: dict[tuple[str, str], dict[str, Any]] = {}
for interaction_map, interaction_templates in INTERACTION_CELLS.items():
    for interaction_template, interaction_cell in interaction_templates.items():
        baseline_path = ROOT / str(interaction_cell.get("baseline_report", ""))
        if not baseline_path.is_file():
            raise RuntimeError(
                "missing frozen interaction baseline: "
                f"{interaction_map}/{interaction_template}"
            )
        if sha256(baseline_path) != str(
            interaction_cell.get("baseline_report_sha256", "")
        ):
            raise RuntimeError(
                "frozen interaction baseline hash mismatch: "
                f"{interaction_map}/{interaction_template}"
            )
        baseline_record = json.loads(baseline_path.read_text(encoding="utf-8"))
        target_ticks = tuple(int(value) for value in interaction_cell["target_ticks"])
        fire_blocks = tuple(int(value) for value in interaction_cell["fire_blocks"])
        diagnostics = baseline_record.get("aim_diagnostics_by_encounter") or []
        baseline_ok = (
            baseline_record.get("map") == interaction_map
            and baseline_record.get("template") == interaction_template
            and baseline_record.get("passed") is True
            and int(baseline_record.get("state_count", -1))
            == v7.base.capture.TOTAL_TICKS
            and not baseline_record.get("fatal_reasons")
            and int(baseline_record.get("player_fire_events", -1)) == 0
            and int(baseline_record.get("player_damage_events", -1)) == 0
            and baseline_record.get("checks", {}).get(
                "all_enemy_samples_alive"
            )
            is True
            and baseline_record.get("checks", {}).get(
                "complete_trace_every_encounter"
            )
            is True
            and len(target_ticks) == len(fire_blocks) == len(diagnostics)
            == len(v7.ORIGINAL_TEMPLATES[interaction_template])
        )
        traces: list[tuple[tuple[int, float], ...]] = []
        if baseline_ok:
            for target_tick, diagnostic in zip(
                target_ticks, diagnostics, strict=True
            ):
                trace = tuple(
                    (int(tick), float(bearing))
                    for tick, bearing in diagnostic.get("bearing_trace", [])
                )
                trace_ticks = {tick for tick, _bearing in trace}
                if (
                    not trace
                    or target_tick not in trace_ticks
                    or any(
                        later_tick <= earlier_tick
                        for (earlier_tick, _), (later_tick, _) in zip(
                            trace, trace[1:]
                        )
                    )
                ):
                    baseline_ok = False
                    break
                traces.append(trace)
        if not baseline_ok:
            raise RuntimeError(
                "invalid frozen interaction baseline: "
                f"{interaction_map}/{interaction_template}"
            )
        FROZEN_BEARING_TRACES[(interaction_map, interaction_template)] = tuple(
            traces
        )
        INTERACTION_BASELINE_RECORDS[
            (interaction_map, interaction_template)
        ] = baseline_record


prod = v7.prod
base = v7.base
lifecycle = v7.lifecycle
_source_distribution_rows = v7.distribution_rows
_source_write_actions = v7.write_actions
_source_build_episode_scenario = v7.build_episode_scenario
_source_deep_appearance_audit = v7.deep_appearance_audit
_source_prepare = v7.prepare
_source_validate_manifest = v7.validate_manifest
_source_validate_episode = v7.validate_episode_multimap_hitscan
_source_run_attempt = v7.run_attempt


def geometry_for(row: dict[str, Any]) -> dict[str, Any]:
    return GEOMETRY[str(row["map"])][str(row["template"])]


def geometry_anchor_id(row: dict[str, Any]) -> str:
    geometry = geometry_for(row)
    return (
        f"{row['map']}_v8_{row['template']}_"
        f"a{round(float(geometry['angle_degrees'])):03d}_"
        f"s{round(float(geometry['trajectory_scale']) * 100):03d}"
    )


def camera_profile_for(row: dict[str, Any]) -> int:
    if "camera_profile" in row:
        return int(row["camera_profile"])
    key = f"{row['template']}/{row['map']}/{row['weapon']}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:8], 16) % int(
        CAMERA_CONFIG["profile_count"]
    )


def interaction_cell_for(row: dict[str, Any]) -> dict[str, Any]:
    return INTERACTION_CELLS[str(row["map"])][str(row["template"])]


def configure_geometry_and_weapon(row: dict[str, Any]) -> None:
    map_name = str(row["map"])
    weapon_name = str(row["weapon"])
    geometry = geometry_for(row)
    player = tuple(float(value) for value in geometry["player_origin"])
    angle_degrees = float(geometry["angle_degrees"])
    angle = math.radians(angle_degrees)
    enemy = (
        player[0] + 200.0 * math.cos(angle),
        player[1] + 200.0 * math.sin(angle),
        player[2],
    )
    scale = float(geometry["trajectory_scale"])
    player_motion_scale = float(PLAYER_MOTION_CONFIG["scale"])
    WEAPONS[weapon_name]["controlled_return_slot1_kill_health"] = (
        controlled_return_slot1_health(map_name, weapon_name)
    )
    base.PLAYER_ORIGIN = player
    base.BASE_ENEMY_ORIGIN = enemy
    base.BASE_ANGLE_DEGREES = angle_degrees
    base.PLAYER_MOTION_BASE_SPEED = (
        v7.ORIGINAL_PLAYER_MOTION_BASE_SPEED * player_motion_scale
    )
    base.PLAYER_MOTION_SPEED_MODULATION = (
        v7.ORIGINAL_PLAYER_MOTION_SPEED_MODULATION * player_motion_scale
    )
    base.ENVIRONMENT_TEXT = v7.environment_weapon_text(map_name, weapon_name)
    scaled = v7.scaled_templates(scale)
    configured_templates: dict[str, tuple[Any, ...]] = {}
    for template, segments in scaled.items():
        fire_blocks = tuple(
            int(value)
            for value in INTERACTION_CELLS[map_name][template]["fire_blocks"]
        )
        if len(fire_blocks) != len(segments):
            raise RuntimeError(
                f"fire-block count mismatch: {map_name}/{template}"
            )
        configured_templates[template] = tuple(
            replace(segment, fire_blocks=(fire_block,))
            for segment, fire_block in zip(segments, fire_blocks, strict=True)
        )
    prod.TEMPLATES = configured_templates


def distribution_rows() -> list[dict[str, Any]]:
    rows = _source_distribution_rows()
    for index, row in enumerate(rows):
        geometry = geometry_for(row)
        row.update(
            {
                "schema_version": SCHEMA_VERSION,
                "release_id": RELEASE_ID,
                "manifest_index": index,
                "episode_id": f"{EPISODE_PREFIX}_{index:06d}",
                "anchor_id": geometry_anchor_id(row),
                "trajectory_scale": float(geometry["trajectory_scale"]),
                "geometry_config_sha256": CONFIG_SHA256,
                "camera_profile": camera_profile_for(row),
                "collision_policy": "canonical_hull_world_sweep_ground_support_v8",
            }
        )
    return rows


def _policy_clock(seconds: float) -> float:
    return base.policy_clock(seconds, base.CAMERA_HOLD_WINDOWS)


def _merged_interaction_intervals(
    segments: tuple[Any, ...],
) -> list[tuple[float, float]]:
    before = float(CAMERA_CONFIG["interaction_protect_before_seconds"])
    after = float(CAMERA_CONFIG["interaction_protect_after_seconds"])
    intervals = sorted(
        (
            _policy_clock(max(0.0, block * base.PROMPT_BLOCK_SECONDS - before)),
            _policy_clock(
                min(base.OUTPUT_SECONDS, block * base.PROMPT_BLOCK_SECONDS + after)
            ),
        )
        for segment in segments
        for block in segment.fire_blocks
    )
    merged: list[tuple[float, float]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _camera_lobes(
    row: dict[str, Any], segments: tuple[Any, ...]
) -> list[tuple[float, float, float, float]]:
    protected = _merged_interaction_intervals(segments)
    clock_end = _policy_clock(base.OUTPUT_SECONDS)
    gaps: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in protected:
        if start - cursor >= 1.8:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if clock_end - cursor >= 1.8:
        gaps.append((cursor, clock_end))

    profile = camera_profile_for(row)
    yaw_profiles = (
        (13.5, -14.5, 12.0, -15.5, 11.5, -13.0),
        (-16.0, 14.0, -17.0, 13.0, -15.5, 16.5),
        (12.0, -15.5, 13.5, -12.5, 14.0, -11.5),
        (-15.0, 17.0, -13.5, 16.0, -17.0, 14.5),
    )
    pitch_profiles = (
        (3.2, -3.7, 3.5, -3.1, 3.8, -3.4),
        (-3.6, 3.1, -3.8, 3.5, -3.2, 3.7),
        (3.8, -3.3, 3.0, -3.7, 3.4, -3.1),
        (-3.2, 3.8, -3.5, 3.1, -3.7, 3.4),
    )
    return [
        (
            start,
            end,
            yaw_profiles[profile][index % len(yaw_profiles[profile])],
            pitch_profiles[profile][index % len(pitch_profiles[profile])],
        )
        for index, (start, end) in enumerate(gaps)
    ]


def _extra_camera_offset(
    lobes: list[tuple[float, float, float, float]], seconds: float
) -> tuple[float, float]:
    clock = _policy_clock(seconds)
    for start, end, yaw_amplitude, pitch_amplitude in lobes:
        if start <= clock <= end:
            progress = (clock - start) / (end - start)
            envelope = math.sin(math.pi * progress) ** 2
            return yaw_amplitude * envelope, pitch_amplitude * envelope
    return 0.0, 0.0


def semiautomatic_primary_ticks(row: dict[str, Any]) -> list[int]:
    return [int(value) for value in interaction_cell_for(row)["target_ticks"]]


def _trace_bearing(
    trace: tuple[tuple[int, float], ...], tick: int
) -> float:
    if tick <= trace[0][0]:
        return trace[0][1]
    if tick >= trace[-1][0]:
        return trace[-1][1]
    lower = trace[0]
    for upper in trace[1:]:
        if tick <= upper[0]:
            if tick == upper[0]:
                return upper[1]
            progress = (tick - lower[0]) / (upper[0] - lower[0])
            return lower[1] + progress * base.shortest_angle_delta(
                upper[1], lower[1]
            )
        lower = upper
    raise AssertionError("unreachable frozen bearing interpolation")


def _baseline_camera_poses(
    actions: list[dict[str, str]],
    segments: tuple[Any, ...],
    lobes: list[tuple[float, float, float, float]],
) -> tuple[list[float], list[float]]:
    yaw = float(base.BASE_ANGLE_DEGREES)
    pitch = -3.0
    max_yaw_step = float(CAMERA_CONFIG["maximum_yaw_step_degrees_per_tick"])
    max_pitch_step = float(CAMERA_CONFIG["maximum_pitch_step_degrees_per_tick"])
    yaws: list[float] = []
    pitches: list[float] = []
    for action in actions:
        tick = int(action["tick"])
        if tick < base.capture.WARMUP_TICKS:
            desired_yaw = float(base.BASE_ANGLE_DEGREES)
            desired_pitch = -3.0
        else:
            seconds = (tick - base.capture.WARMUP_TICKS) / 64.0
            yaw_offset, pitch_offset = _extra_camera_offset(lobes, seconds)
            desired_yaw = base.desired_view_yaw(segments, seconds) + yaw_offset
            desired_pitch = base.desired_view_pitch(seconds) + pitch_offset
        yaw_delta = max(
            -max_yaw_step,
            min(max_yaw_step, base.shortest_angle_delta(desired_yaw, yaw)),
        )
        pitch_delta = max(
            -max_pitch_step,
            min(max_pitch_step, desired_pitch - pitch),
        )
        yaw += yaw_delta
        pitch = max(-89.0, min(89.0, pitch + pitch_delta))
        yaws.append(yaw)
        pitches.append(pitch)
    return yaws, pitches


def _movement_reference_yaws(
    actions: list[dict[str, str]], segments: tuple[Any, ...]
) -> list[float]:
    yaw = float(base.BASE_ANGLE_DEGREES)
    max_yaw_step = float(CAMERA_CONFIG["maximum_yaw_step_degrees_per_tick"])
    yaws: list[float] = []
    for action in actions:
        tick = int(action["tick"])
        if tick < base.capture.WARMUP_TICKS:
            desired_yaw = float(base.BASE_ANGLE_DEGREES)
        else:
            seconds = (tick - base.capture.WARMUP_TICKS) / 64.0
            desired_yaw = base.desired_view_yaw(segments, seconds)
        yaw += max(
            -max_yaw_step,
            min(max_yaw_step, base.shortest_angle_delta(desired_yaw, yaw)),
        )
        yaws.append(yaw)
    return yaws


def _planned_aim_windows(
    row: dict[str, Any], baseline_yaws: list[float]
) -> list[dict[str, Any]]:
    cell = interaction_cell_for(row)
    traces = FROZEN_BEARING_TRACES[(str(row["map"]), str(row["template"]))]
    minimum = int(INTERACTION_AIM_CONFIG["minimum_approach_ticks"])
    maximum = int(INTERACTION_AIM_CONFIG["maximum_approach_ticks"])
    planned_rate = float(
        INTERACTION_AIM_CONFIG["planned_yaw_rate_degrees_per_tick"]
    )
    release_ticks = int(INTERACTION_AIM_CONFIG["release_ticks"])
    hold_ticks = max(
        8,
        int(v7.CONFIG["semiautomatic_primary_pulse_width_ticks"]),
    )
    windows: list[dict[str, Any]] = []
    for encounter_index, (target_tick, fire_block, trace) in enumerate(
        zip(cell["target_ticks"], cell["fire_blocks"], traces, strict=True)
    ):
        target_tick = int(target_tick)
        target_bearing = _trace_bearing(trace, target_tick)
        target_delta = base.shortest_angle_delta(
            target_bearing, baseline_yaws[target_tick]
        )
        target_error = abs(target_delta)
        approach_ticks = max(
            minimum,
            min(maximum, math.ceil(target_error / planned_rate) + 32),
        )
        windows.append(
            {
                "encounter_index": encounter_index,
                "fire_block": int(fire_block),
                "target_tick": target_tick,
                "target_bearing_degrees": target_bearing,
                "target_delta_from_baseline_degrees": target_delta,
                "approach_start_tick": max(
                    base.capture.WARMUP_TICKS,
                    target_tick - approach_ticks,
                ),
                "hold_end_tick": target_tick + hold_ticks,
                "release_end_tick": target_tick + hold_ticks + release_ticks,
                "trace": trace,
            }
        )
    for previous, current in zip(windows, windows[1:]):
        if int(previous["release_end_tick"]) >= int(
            current["approach_start_tick"]
        ):
            raise RuntimeError(
                "overlapping frozen aim windows: "
                f"{row['map']}/{row['template']}"
            )
    return windows


def _interaction_desired_yaw(
    tick: int,
    baseline_yaw: float,
    windows: list[dict[str, Any]],
) -> float:
    for window in windows:
        start = int(window["approach_start_tick"])
        target = int(window["target_tick"])
        hold_end = int(window["hold_end_tick"])
        release_end = int(window["release_end_tick"])
        if not start <= tick <= release_end:
            continue
        if tick < target:
            weight = (tick - start) / max(1, target - start)
            bearing_delta = float(
                window["target_delta_from_baseline_degrees"]
            )
        elif tick <= hold_end:
            weight = 1.0
            bearing_delta = base.shortest_angle_delta(
                _trace_bearing(window["trace"], tick), baseline_yaw
            )
        else:
            weight = 1.0 - (tick - hold_end) / max(
                1, release_end - hold_end
            )
            bearing_delta = base.shortest_angle_delta(
                _trace_bearing(window["trace"], tick), baseline_yaw
            )
                                                                               
                                                                            
                                                       
        target_delta = float(window["target_delta_from_baseline_degrees"])
        bearing_delta += 360.0 * round(
            (target_delta - bearing_delta) / 360.0
        )
        return baseline_yaw + weight * bearing_delta
    return baseline_yaw


def _camera_pause_tick_ranges(
    windows: list[dict[str, Any]], actions: list[dict[str, str]],
) -> list[tuple[int, int]]:
    guard = int(CAMERA_CONFIG["brief_pause_guard_from_interaction_ticks"])
    duration = int(CAMERA_CONFIG["brief_pause_ticks"])
    count = int(CAMERA_CONFIG["brief_pause_count"])
    player_guard = int(CAMERA_CONFIG["brief_pause_guard_from_player_idle_ticks"])
    player_active = [
        math.hypot(float(action["forward"]), float(action["strafe"])) >= 20.0
        for action in actions
    ]
    protected = [
        (
            int(window["approach_start_tick"]),
            int(window["release_end_tick"]) + 1,
        )
        for window in windows
    ]
    gaps: list[tuple[int, int]] = []
    cursor = base.capture.WARMUP_TICKS
    for start, end in protected:
        if cursor < start:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < base.capture.TOTAL_TICKS:
        gaps.append((cursor, base.capture.TOTAL_TICKS))
    candidates: list[tuple[int, int, int]] = []
    for start, end in gaps:
        safe_start = start + guard
        safe_end = end - guard
        if safe_end - safe_start < duration:
            continue
        center = (safe_start + safe_end - duration) // 2
        valid_starts = [
            pause_start
            for pause_start in range(safe_start, safe_end - duration + 1)
            if all(
                player_active[tick]
                for tick in range(
                    max(base.capture.WARMUP_TICKS, pause_start - player_guard),
                    min(
                        base.capture.TOTAL_TICKS,
                        pause_start + duration + player_guard,
                    ),
                )
            )
        ]
        if not valid_starts:
            continue
        pause_start = min(valid_starts, key=lambda value: abs(value - center))
        candidates.append((end - start, pause_start, pause_start + duration))
    candidates.sort(reverse=True)
    selected = sorted((start, end) for _size, start, end in candidates[:count])
    if len(selected) < count:
        raise RuntimeError(
            f"insufficient non-interaction camera gaps: {len(selected)}/{count}"
        )
    return selected


def write_actions(path: Path, row: dict[str, Any]) -> None:
    configure_geometry_and_weapon(row)
    _source_write_actions(path, row)
    segments = prod.TEMPLATES[str(row["template"])]
    lobes = _camera_lobes(row, segments)
    with path.open(newline="", encoding="utf-8") as handle:
        seed_line = handle.readline()
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        actions = list(reader)
    if not fieldnames:
        raise RuntimeError(f"actions have no header: {path}")

    baseline_yaws, baseline_pitches = _baseline_camera_poses(
        actions, segments, lobes
    )
    movement_reference_yaws = _movement_reference_yaws(actions, segments)
    aim_windows = _planned_aim_windows(row, baseline_yaws)
    camera_pause_ranges = _camera_pause_tick_ranges(aim_windows, actions)
    yaw = float(base.BASE_ANGLE_DEGREES)
    pitch = -3.0
    max_yaw_step = float(CAMERA_CONFIG["maximum_yaw_step_degrees_per_tick"])
    max_pitch_step = float(CAMERA_CONFIG["maximum_pitch_step_degrees_per_tick"])
    for action, baseline_yaw, baseline_pitch, movement_reference_yaw in zip(
        actions,
        baseline_yaws,
        baseline_pitches,
        movement_reference_yaws,
        strict=True,
    ):
        tick = int(action["tick"])
        desired_yaw = _interaction_desired_yaw(
            tick, baseline_yaw, aim_windows
        )
        desired_pitch = baseline_pitch
        if any(start <= tick < end for start, end in camera_pause_ranges):
            desired_yaw = yaw
            desired_pitch = pitch
        yaw_delta = max(
            -max_yaw_step,
            min(max_yaw_step, base.shortest_angle_delta(desired_yaw, yaw)),
        )
        pitch_delta = max(
            -max_pitch_step,
            min(max_pitch_step, desired_pitch - pitch),
        )
        yaw += yaw_delta
        pitch = max(-89.0, min(89.0, pitch + pitch_delta))
        action["yaw_delta"] = f"{yaw_delta:.9f}"
        action["pitch_delta"] = f"{pitch_delta:.9f}"
        if tick >= base.capture.WARMUP_TICKS:
            delta_radians = math.radians(
                base.shortest_angle_delta(yaw, movement_reference_yaw)
            )
            forward = float(action["forward"])
            strafe = float(action["strafe"])
            action["forward"] = f"{(
                math.cos(delta_radians) * forward
                - math.sin(delta_radians) * strafe
            ):.9f}"
            action["strafe"] = f"{(
                math.sin(delta_radians) * forward
                + math.cos(delta_radians) * strafe
            ):.9f}"

    if row["weapon"] != "MachineGun":
        pulse_starts = set(semiautomatic_primary_ticks(row))
        width = int(v7.CONFIG["semiautomatic_primary_pulse_width_ticks"])
        for action in actions:
            tick = int(action["tick"])
            action["primary"] = str(
                int(any(start <= tick < start + width for start in pulse_starts))
            )

    planned_yaw = float(base.BASE_ANGLE_DEGREES)
    target_errors: list[float] = []
    windows_by_tick = {
        int(window["target_tick"]): window for window in aim_windows
    }
    for action in actions:
        planned_yaw += float(action["yaw_delta"])
        window = windows_by_tick.get(int(action["tick"]))
        if window is not None:
            target_errors.append(
                abs(
                    base.shortest_angle_delta(
                        float(window["target_bearing_degrees"]),
                        planned_yaw,
                    )
                )
            )
    if not target_errors or max(target_errors) > 0.75:
        raise RuntimeError(
            "frozen aim did not converge at interaction target: "
            f"{row['map']}/{row['template']} errors={target_errors}"
        )

    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        handle.write(seed_line)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(actions)
    os.replace(temporary, path)


def action_camera_metrics(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(
            csv.DictReader(line for line in handle if not line.startswith("#"))
        )[base.capture.WARMUP_TICKS :]
    yaw = 0.0
    pitch = 0.0
    yaw_values: list[float] = []
    pitch_values: list[float] = []
    yaw_steps: list[float] = []
    pitch_steps: list[float] = []
    active = 0
    for row in rows:
        yaw_step = float(row["yaw_delta"])
        pitch_step = float(row["pitch_delta"])
        yaw += yaw_step
        pitch += pitch_step
        yaw_values.append(yaw)
        pitch_values.append(pitch)
        yaw_steps.append(yaw_step)
        pitch_steps.append(pitch_step)
        active += abs(yaw_step) + abs(pitch_step) >= 0.001
    yaw_acceleration = [
        abs(current - previous)
        for previous, current in zip(yaw_steps, yaw_steps[1:])
    ]
    pitch_acceleration = [
        abs(current - previous)
        for previous, current in zip(pitch_steps, pitch_steps[1:])
    ]
    return {
        "yaw_range_degrees": max(yaw_values) - min(yaw_values),
        "pitch_range_degrees": max(pitch_values) - min(pitch_values),
        "maximum_abs_yaw_step_degrees": max(map(abs, yaw_steps)),
        "maximum_abs_pitch_step_degrees": max(map(abs, pitch_steps)),
        "maximum_abs_yaw_acceleration_degrees": max(yaw_acceleration, default=0.0),
        "maximum_abs_pitch_acceleration_degrees": max(
            pitch_acceleration, default=0.0
        ),
        "motion_duty_fraction": active / len(rows),
    }


def action_interaction_metrics(
    path: Path, row: dict[str, Any]
) -> dict[str, Any]:
    configure_geometry_and_weapon(row)
    with path.open(newline="", encoding="utf-8") as handle:
        handle.readline()
        actions = list(csv.DictReader(handle))
    segments = prod.TEMPLATES[str(row["template"])]
    movement_reference_yaws = _movement_reference_yaws(actions, segments)
    yaw = float(base.BASE_ANGLE_DEGREES)
    yaw_by_tick: dict[int, float] = {}
    primary_ticks: set[int] = set()
    maximum_speed_magnitude_error = 0.0
    maximum_world_motion_vector_error = 0.0
    for action, movement_reference_yaw in zip(
        actions, movement_reference_yaws, strict=True
    ):
        tick = int(action["tick"])
        yaw += float(action["yaw_delta"])
        yaw_by_tick[tick] = yaw
        if int(action["primary"]):
            primary_ticks.add(tick)
        if tick < base.capture.WARMUP_TICKS:
            expected_forward, expected_strafe = 0.0, 0.0
        else:
            output_seconds = (tick - base.capture.WARMUP_TICKS) / 64.0
            expected_forward, expected_strafe = base.desired_player_motion(
                output_seconds
            )
        maximum_speed_magnitude_error = max(
            maximum_speed_magnitude_error,
            abs(
                math.hypot(
                    float(action["forward"]), float(action["strafe"])
                )
                - math.hypot(expected_forward, expected_strafe)
            ),
        )
        reference_radians = math.radians(movement_reference_yaw)
        actual_radians = math.radians(yaw)
        expected_world = (
            math.cos(reference_radians) * expected_forward
            + math.sin(reference_radians) * expected_strafe,
            math.sin(reference_radians) * expected_forward
            - math.cos(reference_radians) * expected_strafe,
        )
        actual_forward = float(action["forward"])
        actual_strafe = float(action["strafe"])
        actual_world = (
            math.cos(actual_radians) * actual_forward
            + math.sin(actual_radians) * actual_strafe,
            math.sin(actual_radians) * actual_forward
            - math.cos(actual_radians) * actual_strafe,
        )
        maximum_world_motion_vector_error = max(
            maximum_world_motion_vector_error,
            math.hypot(
                actual_world[0] - expected_world[0],
                actual_world[1] - expected_world[1],
            ),
        )
    traces = FROZEN_BEARING_TRACES[(str(row["map"]), str(row["template"]))]
    target_ticks = semiautomatic_primary_ticks(row)
    target_yaw_errors = [
        abs(
            base.shortest_angle_delta(
                _trace_bearing(trace, target_tick),
                yaw_by_tick[target_tick],
            )
        )
        for target_tick, trace in zip(target_ticks, traces, strict=True)
    ]
    if row["weapon"] == "MachineGun":
        primary_target_checks = [
            any(
                target_tick - 1 <= primary_tick <= target_tick + 1
                for primary_tick in primary_ticks
            )
            for target_tick in target_ticks
        ]
    else:
        primary_target_checks = [
            target_tick in primary_ticks for target_tick in target_ticks
        ]
    return {
        "target_ticks": target_ticks,
        "target_yaw_errors_degrees": target_yaw_errors,
        "maximum_target_yaw_error_degrees": max(target_yaw_errors),
        "primary_present_at_each_target": all(primary_target_checks),
        "maximum_player_speed_magnitude_error": maximum_speed_magnitude_error,
        "maximum_world_motion_vector_error": maximum_world_motion_vector_error,
        "movement_reference": "canonical_time_only_camera_without_profile_lobes",
        "movement_world_compensation_declared": bool(
            INTERACTION_AIM_CONFIG["movement_world_compensation"]
        ),
    }


def camera_metric_checks(metrics: dict[str, Any]) -> dict[str, bool]:
    return {
        "camera_yaw_range_visibly_active": float(metrics["yaw_range_degrees"])
        >= float(CAMERA_CONFIG["minimum_yaw_range_degrees"]),
        "camera_pitch_range_visibly_active": float(metrics["pitch_range_degrees"])
        >= float(CAMERA_CONFIG["minimum_pitch_range_degrees"]),
        "camera_yaw_step_bounded": float(metrics["maximum_abs_yaw_step_degrees"])
        <= float(CAMERA_CONFIG["maximum_yaw_step_degrees_per_tick"]) + 1e-9,
        "camera_pitch_step_bounded": float(
            metrics["maximum_abs_pitch_step_degrees"]
        )
        <= float(CAMERA_CONFIG["maximum_pitch_step_degrees_per_tick"]) + 1e-9,
        "camera_motion_has_brief_holds": 0.88
        <= float(metrics["motion_duty_fraction"])
        <= 0.98,
    }


def rewrite_temporal_visibility_language(
    schedule: list[dict[str, Any]], segments: tuple[Any, ...]
) -> None:
    by_block = {int(item["block_index"]): item for item in schedule}
    for segment in segments:
        first = by_block[int(segment.start_block)]
        first_prompt = str(first["prompt"])
        first_prompt = first_prompt.replace(
            "A new opponent enters from the ",
            "A new opponent appears on the ",
        ).replace(
            "The same opponent enters from the ",
            "The same opponent reappears on the ",
        )
        first["prompt"] = first_prompt
        if first.get("visibility_phase") == "enter":
            first["visibility_phase"] = "appear"

        last = by_block[int(segment.end_block) - 1]
        if last.get("visibility_phase") != "exit":
            continue
        suffix = f" and leaves the view through the {segment.exit_side}."
        replacement = (
            f" and remains active on the {segment.exit_side} side through "
            "the end of this block, then disappears."
        )
        last["prompt"] = str(last["prompt"]).replace(suffix, replacement)
        last["visibility_phase"] = "disappear_after_block"


def build_episode_scenario(
    row: dict[str, Any], manifest_root: Path, shared_actions: Path
) -> tuple[Path, Path]:
    configure_geometry_and_weapon(row)
    scenario_path, timeline = _source_build_episode_scenario(
        row, manifest_root, shared_actions
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    profile = camera_profile_for(row)
    segments = prod.TEMPLATES[str(row["template"])]
    rewrite_temporal_visibility_language(scenario["prompt_schedule"], segments)
    metrics = action_camera_metrics(shared_actions)
    interaction_metrics = action_interaction_metrics(shared_actions, row)
    scenario.update(
        {
            "schema_version": (
                "xonotic-stage2-long60-ref42-multimap-hitscan-"
                "collision-camera-production-scenario-v1"
            ),
            "release_id": RELEASE_ID,
            "anchor_id": geometry_anchor_id(row),
            "trajectory_scale": float(geometry_for(row)["trajectory_scale"]),
            "geometry_config_path": str(CONFIG_PATH),
            "geometry_config_sha256": CONFIG_SHA256,
            "runtime_build": BUILD_TAG,
            "runtime_source_commit": BUILD_COMMIT,
            "action_program": "long60_v8_open_loop_asymmetric_scan_collision_safe",
            "visibility_language_policy": (
                "temporal_side_appearance_without_strict_frustum_crossing_v8"
            ),
        }
    )
    scenario["camera_policy"] = {
        **CAMERA_CONFIG,
        "profile": profile,
        "center_yaw_degrees": float(base.BASE_ANGLE_DEGREES),
        "center_pitch_degrees": float(scenario["player"]["pitch"]),
        "hold_windows_seconds": [list(item) for item in base.CAMERA_HOLD_WINDOWS],
        "planned_interaction_windows_seconds": [
            [
                round(block * base.PROMPT_BLOCK_SECONDS, 6),
                round(block * base.PROMPT_BLOCK_SECONDS + 0.875, 6),
            ]
            for segment in segments
            for block in segment.fire_blocks
        ],
        "action_metrics": metrics,
    }
    cell = interaction_cell_for(row)
    scenario["interaction_aim_policy"] = {
        **{
            key: value
            for key, value in INTERACTION_AIM_CONFIG.items()
            if key != "cells"
        },
        "map": row["map"],
        "template": row["template"],
        "fire_blocks": [int(value) for value in cell["fire_blocks"]],
        "target_ticks": [int(value) for value in cell["target_ticks"]],
        "baseline_report": cell["baseline_report"],
        "baseline_report_sha256": cell["baseline_report_sha256"],
        "action_metrics": interaction_metrics,
    }
    scenario["collision_policy"] = {
        **COLLISION_CONFIG,
        "scope": "stage2_long60_v8_process_only",
        "runtime_fail_closed": True,
    }
    scenario.setdefault("lifecycle_policy", {}).update(
        {
            "v8_health_overrides": LIFECYCLE_HEALTH_OVERRIDES,
            "health_override_scope": "stage2_long60_v8_process_only",
            "controlled_return_slot1_kill_health_v8": (
                controlled_return_slot1_health(
                    str(row["map"]), str(row["weapon"])
                )
            ),
            "v8_health_calibration_source_config_sha256": (
                LIFECYCLE_HEALTH_CALIBRATION["source_config_sha256"]
            ),
        }
    )
    scenario["distribution"].update(
        {
            "camera_profile": profile,
            "collision_qualified_geometry": True,
        }
    )
    scenario["player_action_policy"].update(
        {
            "camera_action_program": CAMERA_CONFIG["name"],
            "camera_reads_enemy_state": False,
            "camera_reads_live_player_state": False,
            "interaction_aim_reads_live_enemy_state": False,
            "interaction_aim_reads_live_player_state": False,
            "interaction_aim_movement_world_compensation": True,
            "player_motion_scale": float(PLAYER_MOTION_CONFIG["scale"]),
            "player_motion_decoupled_from_enemy_trajectory_scale": True,
        }
    )
    if not scenario_interaction_schedule_contract(row, scenario):
        raise RuntimeError(
            "v8 prompt/action/lifecycle schedule mismatch: "
            f"{row['map']}/{row['template']}/{row['weapon']}"
        )
    prod.write_json_atomic(scenario_path, scenario)
    return scenario_path, timeline


def scenario_interaction_schedule_contract(
    row: dict[str, Any], scenario: dict[str, Any]
) -> bool:
    template = str(row["template"])
    weapon = str(row["weapon"])
    expected_blocks = ORIGINAL_FIRE_BLOCKS_BY_TEMPLATE[template]
    cell = interaction_cell_for(row)
    if tuple(int(value) for value in cell["fire_blocks"]) != expected_blocks:
        return False
    encounters = scenario.get("encounters") or []
    if len(encounters) != len(expected_blocks):
        return False
    prompt_by_block = {
        int(item["block_index"]): item
        for item in scenario.get("prompt_schedule") or []
    }
    if any(
        "enters from the" in str(item.get("prompt", ""))
        or "leaves the view through" in str(item.get("prompt", ""))
        for item in prompt_by_block.values()
    ):
        return False
    for encounter, fire_block in zip(encounters, expected_blocks, strict=True):
        if [int(value) for value in encounter.get("fire_blocks") or []] != [
            fire_block
        ]:
            return False
        prompt = prompt_by_block.get(fire_block)
        if prompt is None or f"fires the {weapon}" not in str(prompt.get("prompt", "")):
            return False
        if encounter.get("intent_outcome") == "kill":
            if (
                int(encounter.get("kill_block", -1)) != fire_block
                or prompt.get("visibility_phase") != "killed"
            ):
                return False
        elif (
            encounter.get("kill_block") is not None
            or "remains alive" not in str(prompt.get("prompt", ""))
        ):
            return False
    return all(
        prompt_block_for_server_tick(int(target_tick)) == fire_block
        for target_tick, fire_block in zip(
            cell["target_ticks"], expected_blocks, strict=True
        )
    )


def deep_appearance_audit(
    manifest_root: Path, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    report = _source_deep_appearance_audit(manifest_root, rows)
                                                                             
                                                                             
                                                                            
                                        
    errors = [
        str(error)
        for error in report.get("errors") or []
        if not str(error).endswith(":health")
    ]
    action_paths = sorted({str(row["actions_path"]) for row in rows})
    metrics = {
        path: action_camera_metrics(ROOT / path)
        for path in action_paths
    }
    metric_check_names = camera_metric_checks(next(iter(metrics.values())))
    camera_checks = {
        name: all(camera_metric_checks(item)[name] for item in metrics.values())
        for name in metric_check_names
    }
    scenario_contract = True
    health_contract = True
    interaction_contract = True
    interaction_schedule_contract = True
    geometry_cells = Counter()
    for row in rows:
        scenario = json.loads(
            (ROOT / row["scenario_path"]).read_text(encoding="utf-8")
        )
        scenario_contract = scenario_contract and (
            scenario.get("runtime_build") == BUILD_TAG
            and scenario.get("runtime_source_commit") == BUILD_COMMIT
            and scenario.get("collision_policy", {}).get("runtime_fail_closed")
            is True
            and scenario.get("camera_policy", {}).get("reads_enemy_state") is False
            and scenario.get("camera_policy", {}).get("reads_live_player_state")
            is False
            and scenario.get("visibility_language_policy")
            == "temporal_side_appearance_without_strict_frustum_crossing_v8"
            and float(
                scenario.get("player_action_policy", {}).get(
                    "player_motion_scale", -1
                )
            )
            == float(PLAYER_MOTION_CONFIG["scale"])
            and scenario.get("player_action_policy", {}).get(
                "player_motion_decoupled_from_enemy_trajectory_scale"
            )
            is True
            and scenario.get("lifecycle_policy", {}).get(
                "v8_health_overrides"
            )
            == LIFECYCLE_HEALTH_OVERRIDES
            and float(
                scenario.get("lifecycle_policy", {}).get(
                    "controlled_return_slot1_kill_health_v8", -1
                )
            )
            == controlled_return_slot1_health(
                str(row["map"]), str(row["weapon"])
            )
        )
        kill_slots = {int(value) for value in row["kill_slots"]}
        for actor in scenario["actors"]:
            slot = int(actor["slot"])
            expected_health = 999.0
            if slot in kill_slots:
                expected_health = (
                    controlled_return_slot1_health(
                        str(row["map"]), str(row["weapon"])
                    )
                    if row["template"] == "controlled_return" and slot == 1
                    else float(WEAPONS[str(row["weapon"])]["single_kill_health"])
                )
            if not math.isclose(
                float(actor["health"]), expected_health, abs_tol=1e-6
            ):
                health_contract = False
                if len(errors) < 100:
                    errors.append(
                        f"{row['episode_id']}:{actor['actor_id']}:v8_health"
                    )
        interaction_metrics = scenario.get("interaction_aim_policy", {}).get(
            "action_metrics", {}
        )
        interaction_contract = interaction_contract and (
            scenario.get("interaction_aim_policy", {}).get("name")
            == INTERACTION_AIM_CONFIG["name"]
            and scenario.get("interaction_aim_policy", {}).get(
                "reads_live_enemy_state"
            )
            is False
            and scenario.get("interaction_aim_policy", {}).get(
                "reads_live_player_state"
            )
            is False
            and scenario.get("interaction_aim_policy", {}).get(
                "movement_world_compensation"
            )
            is True
            and float(
                interaction_metrics.get(
                    "maximum_target_yaw_error_degrees", float("inf")
                )
            )
            <= 0.75
            and interaction_metrics.get("primary_present_at_each_target")
            is True
            and float(
                interaction_metrics.get(
                    "maximum_player_speed_magnitude_error", float("inf")
                )
            )
            <= 1e-6
            and float(
                interaction_metrics.get(
                    "maximum_world_motion_vector_error", float("inf")
                )
            )
            <= 1e-6
        )
        interaction_schedule_contract = (
            interaction_schedule_contract
            and scenario_interaction_schedule_contract(row, scenario)
        )
        geometry_cells[(str(row["map"]), str(row["template"]))] += 1
    report["schema_version"] = (
        "xonotic-stage2-long60-ref42-collision-camera-static-validation-v1"
    )
    report["release_id"] = RELEASE_ID
    report["errors"] = errors
    report["checks"]["weapon_specific_health_contract"] = health_contract
    report["checks"].update(camera_checks)
    report["checks"].update(
        {
            "v8_scenario_collision_camera_contract": scenario_contract,
            "v8_frozen_interaction_aim_contract": interaction_contract,
            "v8_prompt_action_lifecycle_schedule_aligned": (
                interaction_schedule_contract
            ),
            "v8_map_specific_return_health_contract": health_contract,
            "all_health_calibration_records_revalidated": (
                set(HEALTH_CALIBRATION_RECORDS) == set(MAPS)
                and all(
                    record.get("passed") is True
                    and not record.get("fatal_reasons")
                    and int(record.get("state_count", -1))
                    == base.capture.TOTAL_TICKS
                    for record in HEALTH_CALIBRATION_RECORDS.values()
                )
            ),
            "all_eight_map_template_geometry_cells": len(geometry_cells) == 8,
            "all_geometry_marked_qualified": all(
                geometry.get("qualification")
                == "passed_step18_floor_projection_probe"
                for cells in GEOMETRY.values()
                for geometry in cells.values()
            ),
            "all_geometry_qualification_records_revalidated": (
                len(QUALIFICATION_RECORDS) == 8
                and all(
                    record.get("passed") is True
                    and record.get("fatal") is None
                    and int(record.get("state_count", -1))
                    == base.capture.TOTAL_TICKS
                    for record in QUALIFICATION_RECORDS.values()
                )
            ),
            "all_frozen_interaction_baselines_revalidated": (
                len(INTERACTION_BASELINE_RECORDS) == 8
                and all(
                    record.get("passed") is True
                    and int(record.get("state_count", -1))
                    == base.capture.TOTAL_TICKS
                    and not record.get("fatal_reasons")
                    and int(record.get("player_fire_events", -1)) == 0
                    and int(record.get("player_damage_events", -1)) == 0
                    and record.get("checks", {}).get(
                        "all_enemy_samples_alive"
                    )
                    is True
                    and record.get("checks", {}).get(
                        "complete_trace_every_encounter"
                    )
                    is True
                    for record in INTERACTION_BASELINE_RECORDS.values()
                )
            ),
        }
    )
    report["camera_action_metrics"] = metrics
    report["all_pass"] = all(report["checks"].values()) and not report.get("errors")
    return report


def prepare(manifest_root: Path) -> None:
    _source_prepare(manifest_root)
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    prepared_path = manifest_root / "PREPARED.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "schema_version": (
                "xonotic-stage2-long60-ref42-collision-camera-production-metadata-v1"
            ),
            "release_id": RELEASE_ID,
            "runtime_build": BUILD_TAG,
            "runtime_source_commit": BUILD_COMMIT,
            "geometry_config_path": str(CONFIG_PATH),
            "geometry_config_sha256": CONFIG_SHA256,
            "collision_policy": {
                **COLLISION_CONFIG,
                "scope": "stage2_long60_v8_process_only",
                "runtime_fail_closed": True,
            },
            "camera_policy": CAMERA_CONFIG,
            "interaction_aim_policy": INTERACTION_AIM_CONFIG,
            "player_motion_policy": PLAYER_MOTION_CONFIG,
            "lifecycle_health_overrides": LIFECYCLE_HEALTH_OVERRIDES,
            "lifecycle_health_calibration": LIFECYCLE_HEALTH_CALIBRATION,
            "topology": {
                "nodes": 4,
                "gpus_per_node": 4,
                "lanes_per_gpu": 4,
                "total_lanes": 64,
            },
            "existing_stage1_stage2_pipelines_modified": False,
        }
    )
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared.update(
        {
            "release_id": RELEASE_ID,
            "collision_qualified": True,
            "visibly_active_camera_qualified": True,
            "frozen_interaction_aim_qualified": True,
            "shotgun_demo_gap_fix_in_runtime": True,
            "formal_topology": "4x4-whole-node-64-lanes",
        }
    )
    prod.write_json_atomic(metadata_path, metadata)
    prod.write_json_atomic(prepared_path, prepared)


def validate_manifest(
    manifest_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, metadata = _source_validate_manifest(manifest_root)
    checks = {
        "runtime_build": metadata.get("runtime_build") == BUILD_TAG,
        "runtime_commit": metadata.get("runtime_source_commit") == BUILD_COMMIT,
        "collision_fail_closed": metadata.get("collision_policy", {}).get(
            "runtime_fail_closed"
        )
        is True,
        "camera_policy": metadata.get("camera_policy", {}).get("name")
        == CAMERA_CONFIG["name"],
        "interaction_aim_policy": (
            metadata.get("interaction_aim_policy", {}).get("name")
            == INTERACTION_AIM_CONFIG["name"]
            and metadata.get("interaction_aim_policy", {}).get(
                "reads_live_enemy_state"
            )
            is False
            and metadata.get("interaction_aim_policy", {}).get(
                "reads_live_player_state"
            )
            is False
        ),
        "player_motion_policy": (
            metadata.get("player_motion_policy") == PLAYER_MOTION_CONFIG
            and PLAYER_MOTION_CONFIG.get(
                "decoupled_from_enemy_trajectory_scale"
            )
            is True
        ),
        "lifecycle_health_overrides": (
            metadata.get("lifecycle_health_overrides")
            == LIFECYCLE_HEALTH_OVERRIDES
            and all(
                controlled_return_slot1_health(map_name, "MachineGun")
                == expected
                for map_name, expected in {
                    "bromine": 130.0,
                    "courtfun": 80.0,
                    "geoplanetary": 60.0,
                    "stormkeep": 110.0,
                }.items()
            )
        ),
        "lifecycle_health_calibration": (
            metadata.get("lifecycle_health_calibration")
            == LIFECYCLE_HEALTH_CALIBRATION
            and set(HEALTH_CALIBRATION_RECORDS) == set(MAPS)
        ),
        "geometry_rows": all(
            row.get("anchor_id") == geometry_anchor_id(row)
            and float(row.get("trajectory_scale"))
            == float(geometry_for(row)["trajectory_scale"])
            for row in rows
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"v8 manifest validation failed: {checks}")
    return rows, metadata


def validate_episode(*args: Any, **kwargs: Any) -> dict[str, Any]:
    scenario = args[0] if args else kwargs["scenario"]
    live = args[2] if len(args) >= 3 else kwargs["live"]
    qa = _source_validate_episode(*args, **kwargs)
    lifecycle_qa = qa.get("lifecycle") or {}
    kill_records = list(lifecycle_qa.get("kill_records") or [])
    for kill_record in kill_records:
        kill_record["legacy_truncated_realized_kill_block"] = kill_record.get(
            "realized_kill_block"
        )
        kill_record["realized_kill_block"] = prompt_block_for_server_tick(
            int(kill_record["kill_server_tick"])
        )
    expected_kill_ids = {
        str(value) for value in lifecycle_qa.get("expected_kill_actor_ids") or []
    }
    observed_kill_ids = {str(item["actor_id"]) for item in kill_records}
    corrected_kill_alignment = (
        len(kill_records) == len(expected_kill_ids)
        and observed_kill_ids == expected_kill_ids
        and all(
            int(item["realized_kill_block"])
            == int(item["declared_kill_block"])
            for item in kill_records
        )
    )
    qa["checks"]["exact_expected_moving_kills"] = corrected_kill_alignment
    qa["checks"]["v8_exact_prompt_block_timebase"] = corrected_kill_alignment
    qa["lifecycle_block_timebase_v8"] = (
        "floor((server_tick-warmup_ticks)/(0.8_seconds*64_hz))"
    )
    metrics = action_camera_metrics(ROOT / scenario["frozen_actions_path"])
    scenario_row = {
        "map": scenario["map"],
        "template": scenario["distribution"]["template"],
        "weapon": scenario["weapon"],
    }
    interaction_metrics = action_interaction_metrics(
        ROOT / scenario["frozen_actions_path"], scenario_row
    )
    player_motion_scale = float(PLAYER_MOTION_CONFIG["scale"])
    player_motion = qa["player_motion"]
    telemetry = prod.load_jsonl(Path(live["server_telemetry"]))
    fatal_reasons = [
        str(item.get("reason"))
        for item in telemetry
        if item.get("kind") == "fatal"
    ]
    qa["checks"].pop("killed_encounters_enter_and_reach_aim_region", None)
    qa["checks"].pop("surviving_encounters_cross_expanded_view", None)
    encounter_crossings = qa.get("encounter_crossings") or []
    qa["checks"]["every_encounter_reaches_interaction_aim_region_v8"] = (
        bool(encounter_crossings)
        and all(
            (
                float(
                    item.get("minimum_relative_yaw_degrees", float("inf"))
                )
                <= 12.0
            )
            or (
                item.get("intent_outcome") == "kill"
                and str(item.get("actor_id")) in observed_kill_ids
                and float(
                    item.get("minimum_relative_yaw_degrees", float("inf"))
                )
                <= float(
                    item.get("expanded_view_half_yaw_degrees", 0.0)
                )
            )
            for item in encounter_crossings
        )
    )
    qa["interaction_region_policy_v8"] = {
        "surviving_encounter_maximum_yaw_degrees": 12.0,
        "killed_encounter_policy": (
            "realized kill while inside expanded visible region"
        ),
        "reason": (
            "a killed actor cannot continue toward the planned center point"
        ),
    }
    qa["checks"]["temporal_visibility_prompt_matches_v8_policy"] = (
        scenario.get("visibility_language_policy")
        == "temporal_side_appearance_without_strict_frustum_crossing_v8"
        and all(
            "enters from the" not in str(item.get("prompt", ""))
            and "leaves the view through" not in str(item.get("prompt", ""))
            for item in scenario.get("prompt_schedule") or []
        )
    )
    qa["checks"].update(camera_metric_checks(metrics))
    qa["checks"].update(
        {
            "visible_player_displacement": (
                float(player_motion["horizontal_path_length_units"])
                >= 2200.0 * player_motion_scale
                and float(player_motion["maximum_displacement_from_anchor_units"])
                >= 40.0 * player_motion_scale
            ),
            "player_remains_in_local_encounter_area": (
                float(player_motion["maximum_displacement_from_anchor_units"])
                <= 500.0 * player_motion_scale
            ),
            "enemy_world_collision_absent": "enemy_world_collision"
            not in fatal_reasons,
            "enemy_ground_support_missing_absent": (
                "enemy_ground_support_missing" not in fatal_reasons
            ),
            "enemy_ground_discontinuity_absent": (
                "enemy_ground_discontinuity" not in fatal_reasons
            ),
            "canonical_collision_hull_declared": (
                scenario.get("collision_policy", {}).get(
                    "canonical_player_hull_mins"
                )
                == [-16.0, -16.0, -24.0]
                and scenario.get("collision_policy", {}).get(
                    "canonical_player_hull_maxs"
                )
                == [16.0, 16.0, 45.0]
            ),
            "shotgun_render_tail_not_frozen": (
                scenario.get("weapon") != "Shotgun"
                or qa["checks"].get("render_tail_not_frozen") is True
            ),
            "frozen_interaction_aim_hits_declared_targets": (
                float(interaction_metrics["maximum_target_yaw_error_degrees"])
                <= 0.75
                and interaction_metrics["primary_present_at_each_target"]
                is True
            ),
            "player_motion_speed_preserved_during_aim": (
                float(
                    interaction_metrics[
                        "maximum_player_speed_magnitude_error"
                    ]
                )
                <= 1e-6
            ),
            "player_world_motion_preserved_during_aim": (
                float(
                    interaction_metrics[
                        "maximum_world_motion_vector_error"
                    ]
                )
                <= 1e-6
            ),
            "prompt_action_lifecycle_schedule_aligned": (
                scenario_interaction_schedule_contract(scenario_row, scenario)
            ),
        }
    )
    qa["schema_version"] = (
        "xonotic-stage2-long60-ref42-collision-camera-episode-qa-v1"
    )
    qa["camera_motion_v8"] = metrics
    qa["interaction_aim_v8"] = interaction_metrics
    qa["collision_v8"] = {
        "fatal_reasons": fatal_reasons,
        "policy": scenario.get("collision_policy"),
    }
    qa["passed"] = all(qa["checks"].values())
    return qa


def run_attempt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    row = args[1] if len(args) >= 2 else kwargs["row"]
    output_root = args[3] if len(args) >= 4 else kwargs["output_root"]
    configure_geometry_and_weapon(row)
    record = _source_run_attempt(*args, **kwargs)
    record.update(
        {
            "runtime_build": BUILD_TAG,
            "runtime_source_commit": BUILD_COMMIT,
            "anchor_id": geometry_anchor_id(row),
            "trajectory_scale": float(geometry_for(row)["trajectory_scale"]),
            "camera_profile": camera_profile_for(row),
            "collision_policy": "canonical_hull_world_sweep_ground_support_v8",
            "interaction_aim_policy": INTERACTION_AIM_CONFIG["name"],
        }
    )
    paths = prod.accepted_paths(output_root, row)
    prod.write_json_atomic(paths["record"], record)
    prod.write_json_atomic(paths["accepted"], record)
    return record


                                                                               
for module in (v7, v7.v6, v7.v6.v5, v7.v6.v5.v4, v7.v3, prod):
    module.RELEASE_ID = RELEASE_ID
    module.SCHEMA_VERSION = SCHEMA_VERSION
v7.EPISODE_PREFIX = EPISODE_PREFIX
v7.v6.EPISODE_PREFIX = EPISODE_PREFIX
v7.v6.v5.EPISODE_PREFIX = EPISODE_PREFIX
v7.CONFIG_PATH = CONFIG_PATH
v7.CONFIG_SHA256 = CONFIG_SHA256
v7.CONFIG = CONFIG
v7.MAPS = MAPS
v7.WEAPONS = WEAPONS
v7.BUILD_TAG = BUILD_TAG
v7.BUILD_COMMIT = BUILD_COMMIT
v7.configure_geometry_and_weapon = configure_geometry_and_weapon
v7.distribution_rows = distribution_rows
v7.semiautomatic_primary_ticks = semiautomatic_primary_ticks
v7.write_actions = write_actions
v7.build_episode_scenario = build_episode_scenario
v7.deep_appearance_audit = deep_appearance_audit
v7.prepare = prepare
v7.validate_manifest = validate_manifest
v7.validate_episode_multimap_hitscan = validate_episode
v7.run_attempt = run_attempt
v7.v6.configure_geometry_and_weapon = configure_geometry_and_weapon
v7.v6.MAPS = MAPS
v7.v6.WEAPONS = WEAPONS
prod.BUILD_TAG = BUILD_TAG
prod.BUILD_COMMIT = BUILD_COMMIT
prod.DEFAULT_MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
prod.DEFAULT_OUTPUT_ROOT = Path("./rigen_data") / RELEASE_ID
prod.distribution_rows = distribution_rows
prod.build_episode_scenario = build_episode_scenario
prod.prepare = prepare
prod.validate_manifest = validate_manifest
prod.run_attempt = run_attempt
prod.worker = v7.worker
prod.finalize = v7.finalize
lifecycle.lifecycle_validate_episode = validate_episode


def main() -> int:
    return prod.main()


if __name__ == "__main__":
    raise SystemExit(main())
