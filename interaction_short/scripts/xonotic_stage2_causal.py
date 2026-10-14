                      
"""Stage-2 causal-interaction action programs and fail-closed QA.

The policy consumes only manifest-frozen initial geometry and the declared
analytic enemy trajectory.  It never reads live camera, crosshair, player, or
enemy state.  Actual outcomes are derived from authoritative telemetry.
"""

from __future__ import annotations

import csv
import binascii
import functools
import hashlib
import json
import math
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import xonotic_capture as capture


ACTION_PROGRAM = "stage2_causal_counterfactual_v1"
SCENARIO_SCHEMA = "xonotic-v2-stage2-causal-scenario-v1"
CAUSAL_DESIGN_SCHEMA = "xonotic-stage2-causal-design-v1"
EXOGENOUS_SCHEMA = "xonotic-stage2-exogenous-contract-v1"
ACTION_PROGRAM_V2 = "stage2_causal_counterfactual_v2"
SCENARIO_SCHEMA_V2 = "xonotic-v2-stage2-causal-scenario-v2"
CAUSAL_DESIGN_SCHEMA_V2 = "xonotic-stage2-causal-design-v2"
EXOGENOUS_SCHEMA_V2 = "xonotic-stage2-exogenous-contract-v2"
ACTION_PROGRAM_V3 = "stage2_causal_counterfactual_v3"
SCENARIO_SCHEMA_V3 = "xonotic-v2-stage2-causal-scenario-v3"
CAUSAL_DESIGN_SCHEMA_V3 = "xonotic-stage2-causal-design-v3"
EXOGENOUS_SCHEMA_V3 = "xonotic-stage2-exogenous-contract-v3"
ACTION_PROGRAM_V4 = "stage2_causal_counterfactual_v4"
SCENARIO_SCHEMA_V4 = "xonotic-v2-stage2-causal-scenario-v4"
CAUSAL_DESIGN_SCHEMA_V4 = "xonotic-stage2-causal-design-v4"
EXOGENOUS_SCHEMA_V4 = "xonotic-stage2-exogenous-contract-v4"
ACTION_PROGRAM_V5 = "stage2_causal_counterfactual_v5"
SCENARIO_SCHEMA_V5 = "xonotic-v2-stage2-causal-scenario-v5"
CAUSAL_DESIGN_SCHEMA_V5 = "xonotic-stage2-causal-design-v5"
EXOGENOUS_SCHEMA_V5 = "xonotic-stage2-exogenous-contract-v5"
ACTION_PROGRAM_V6 = "stage2_causal_counterfactual_v6"
SCENARIO_SCHEMA_V6 = "xonotic-v2-stage2-causal-scenario-v6"
CAUSAL_DESIGN_SCHEMA_V6 = "xonotic-stage2-causal-design-v6"
EXOGENOUS_SCHEMA_V6 = "xonotic-stage2-exogenous-contract-v6"
ACTION_PROGRAM_V7 = "stage2_causal_counterfactual_v7"
SCENARIO_SCHEMA_V7 = "xonotic-v2-stage2-causal-scenario-v7"
CAUSAL_DESIGN_SCHEMA_V7 = "xonotic-stage2-causal-design-v7"
EXOGENOUS_SCHEMA_V7 = "xonotic-stage2-exogenous-contract-v7"
ACTION_PROGRAM_V8 = "stage2_causal_counterfactual_v8"
SCENARIO_SCHEMA_V8 = "xonotic-v2-stage2-causal-scenario-v8"
CAUSAL_DESIGN_SCHEMA_V8 = "xonotic-stage2-causal-design-v8"
EXOGENOUS_SCHEMA_V8 = "xonotic-stage2-exogenous-contract-v8"
ACTION_PROGRAM_V9 = "stage2_causal_counterfactual_v9"
SCENARIO_SCHEMA_V9 = "xonotic-v2-stage2-causal-scenario-v9"
CAUSAL_DESIGN_SCHEMA_V9 = "xonotic-stage2-causal-design-v9"
EXOGENOUS_SCHEMA_V9 = "xonotic-stage2-exogenous-contract-v9"
ACTION_PROGRAMS = (
    ACTION_PROGRAM,
    ACTION_PROGRAM_V2,
    ACTION_PROGRAM_V3,
    ACTION_PROGRAM_V4,
    ACTION_PROGRAM_V5,
    ACTION_PROGRAM_V6,
    ACTION_PROGRAM_V7,
    ACTION_PROGRAM_V8,
    ACTION_PROGRAM_V9,
)
INTERACTION_CHANNELS = ("primary", "secondary")
SECONDARY_MECHANISMS = {
    "Shotgun": "direct_secondary",
    "MachineGun": "direct_secondary",
    "Mortar": "direct_secondary",
    "Electro": "direct_secondary",
    "Crylink": "direct_secondary",
    "Hagar": "hagar_load_release",
    "Devastator": "devastator_remote_detonation",
}
                                                                            
                                                                         
                             
SECONDARY_EXCLUDED = {
    "Blaster": "stock_secondary_is_weapon_switch",
    "Vortex": "stock_secondary_is_fov_zoom",
}
PLAYER_PATH_SOURCE_SCHEMA = "xonotic-stage2-player-path-source-v1"
PLAYER_PATH_SOURCE_SCHEMA_V2 = (
    "xonotic-stage2-player-path-source-v2"
)
PLAYER_PATH_SOURCE_SCHEMA_V3 = (
    "xonotic-stage2-player-path-source-v3"
)
PLAYER_PATH_SOURCE_SCHEMA_V4 = (
    "xonotic-stage2-player-path-source-v4"
)
JUMP_VIEW_OVERLAY_REPLAY_TOLERANCE = 32.0
JUMP_VIEW_OVERLAY_TOLERANCE_BASIS = (
    "one_player_hull_diameter_float_sensitive_jump_v1"
)
AIM_SCHEDULE_SCHEMA = "xonotic-stage2-aim-schedule-v1"
AIM_SCHEDULE_SCHEMA_V2 = "xonotic-stage2-aim-schedule-v2"
AIM_SCHEDULE_SCHEMA_V3 = "xonotic-stage2-aim-schedule-v3"
AIM_OVERLAY_SCHEMA = "xonotic-stage2-aim-overlay-v1"
AIM_OVERLAY_SCHEMA_V2 = "xonotic-stage2-aim-overlay-v2"
AIM_OVERLAY_SCHEMA_V3 = "xonotic-stage2-aim-overlay-v3"
AIM_OVERLAY_SCHEMA_V4 = "xonotic-stage2-aim-overlay-v4"
AimMotorProfile = dict[str, Any]
AIM_MOTOR_PROFILE_SCHEMA = "xonotic-stage2-aim-motor-profile-v1"
AIM_MOTOR_STYLES = (
    "direct_smooth",
    "overshoot_correct",
    "undershoot_correct",
)
SHOT_ERROR_SCHEDULE_SCHEMA = "xonotic-stage2-shot-error-schedule-v1"
FIRE_PROGRAM_SCHEMA = "xonotic-stage2-fire-program-v1"
MISS_TRAJECTORY_STYLES = (
    "persistent_bias",
    "near_miss_drift",
    "cross_and_settle",
    "arc_depart",
)
MISS_DIRECTION_SECTORS = (
    "right",
    "lower_right",
    "lower",
    "lower_left",
    "left",
    "upper_left",
    "upper",
    "upper_right",
)
MISS_MAGNITUDE_BOUNDS = {
    "near_edge": (3.5, 6.0),
    "medium": (6.0, 12.0),
    "large": (12.0, 18.000001),
}
FIRE_PROGRAM_NAMES = (
    "none",
    "single_tap",
    "short_burst",
    "long_burst",
    "double_burst",
    "multi_tap",
)
STOCHASTIC_AIM_POLICY = "stochastic_free_aim_fire"
RANDOM_AIM_PROGRAM_SCHEMA = "xonotic-stage2-random-aim-program-v1"
PLAYER_MOVEMENT_PROGRAM_SCHEMA = (
    "xonotic-stage2-frozen-player-movement-program-v1"
)
PLAYER_MOVEMENT_PROGRAM_PROFILES = (
    "lateral_weave",
    "approach_retreat",
)
WEAPON_BALANCED_AIM_PROGRAM_SCHEMA = (
    "xonotic-stage2-weapon-balanced-aim-program-v1"
)
PREFROZEN_TRACE_SOURCE_SCHEMA = (
    "xonotic-stage2-prefrozen-trace-source-v1"
)
WEAPON_BALANCED_AIM_ARMS = (
    "stable_track",
    "overshoot_correct",
    "predictive_track",
    "edge_graze",
    "near_miss",
    "stochastic_local",
    "stochastic_broad",
    "visible_no_fire",
)
WEAPON_BALANCED_HUMANIZED_ARMS = frozenset(
    {
        "stable_track",
        "overshoot_correct",
        "predictive_track",
        "edge_graze",
        "near_miss",
    }
)
WEAPON_BALANCED_STOCHASTIC_ARMS = frozenset(
    {"stochastic_local", "stochastic_broad", "visible_no_fire"}
)
HITSCAN_PRIMARY_WEAPONS = frozenset(
    {"Shotgun", "MachineGun", "Vortex"}
)
PROJECTILE_PRIMARY_WEAPONS = frozenset(
    {
        "Blaster",
        "Mortar",
        "Electro",
        "Crylink",
        "Hagar",
        "Devastator",
    }
)
PROJECTILE_OUTCOME_OBSERVATION_TICKS = 96
LATEST_PROJECTILE_FIRE_OUTPUT_TICK = (
    capture.OUTPUT_TICKS - 1 - PROJECTILE_OUTCOME_OBSERVATION_TICKS
)
INITIAL_SCREEN_DESIGN_SCHEMA = "xonotic-stage2-initial-screen-design-v1"
ENCOUNTER_CERTIFICATE_SCHEMA = (
    "xonotic-stage2-path-encounter-certificate-v1"
)
PLAYER_ENEMY_CLEARANCE_MINIMUM = 96.0
AIM_POLICIES = (
    "visible_no_response",
    "delayed_acquisition",
    "pass_offset",
    "track_loss_reacquire",
    "sustained_tracking",
)
FIRING_POLICIES = (
    set(AIM_POLICIES) - {"visible_no_response"}
) | {STOCHASTIC_AIM_POLICY}
INITIAL_YAW_OFFSET_DEG = 28.0
INITIAL_PITCH_OFFSET_DEG = 4.0
TARGET_CENTER_THRESHOLD_DEG = 3.0
SHOT_ERROR_PROGRAMS = (
    "none",
    "spatial_persistent",
    "spatial_transient",
    "spatial_undershoot_then_acquire",
    "timing_early_acquisition",
    "timing_loss_window",
    "timing_reacquisition_lag",
    "pass_cross_and_depart",
)
SHOT_ERROR_PROGRAM_POLICIES = {
    "none": frozenset(AIM_POLICIES),
    "spatial_persistent": frozenset(
        {"delayed_acquisition", "pass_offset"}
    ),
    "spatial_transient": frozenset(
        {
            "delayed_acquisition",
            "track_loss_reacquire",
            "sustained_tracking",
        }
    ),
    "spatial_undershoot_then_acquire": frozenset(
        {"delayed_acquisition"}
    ),
    "timing_early_acquisition": frozenset(
        {"delayed_acquisition", "pass_offset"}
    ),
    "timing_loss_window": frozenset({"track_loss_reacquire"}),
    "timing_reacquisition_lag": frozenset(
        {"track_loss_reacquire"}
    ),
    "pass_cross_and_depart": frozenset({"pass_offset"}),
}

BASE_ACTION_ROWS = capture.CANONICAL_ACTION_ROWS


@functools.lru_cache(maxsize=128)
def _locked_route_record(
    index_path_raw: str,
    index_sha256: str,
    route_id: str,
) -> dict[str, Any]:
    index_path = capture.locked_root_artifact(
        index_path_raw,
        index_sha256,
        "stage2_player_path_index",
    )
    matches = [
        row
        for row in capture.load_jsonl(index_path)
        if row.get("route_id") == route_id
    ]
    if len(matches) != 1:
        raise capture.CaptureFailure(
            "stage2_player_path_route_record_missing",
            f"route_id={route_id} count={len(matches)}",
        )
    return matches[0]


@functools.lru_cache(maxsize=128)
def _locked_base_actions(
    path_raw: str, expected_sha256: str
) -> tuple[dict[str, Any], ...]:
    path = capture.locked_root_artifact(
        path_raw,
        expected_sha256,
        "stage2_player_path_actions",
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or not lines[0].startswith("#seed,"):
        raise capture.CaptureFailure(
            "stage2_player_path_actions_header", str(path)
        )
    parsed = list(csv.DictReader(lines[1:]))
    if (
        len(parsed) != capture.TOTAL_TICKS
        or list(parsed[0]) != capture.ACTION_COLUMNS
        or [int(row["tick"]) for row in parsed]
        != list(range(capture.TOTAL_TICKS))
    ):
        raise capture.CaptureFailure(
            "stage2_player_path_actions_shape", str(path)
        )
    result: list[dict[str, Any]] = []
    for source in parsed:
        row: dict[str, Any] = {"tick": int(source["tick"])}
        for name in ("forward", "strafe", "yaw_delta", "pitch_delta"):
            row[name] = float(source[name])
        for name in (
            "jump",
            "primary",
            "secondary",
            "weapon_impulse",
            "reload",
        ):
            row[name] = int(float(source[name]))
        result.append(row)
    result[0]["_seed"] = int(lines[0].split(",", 1)[1])
    return tuple(result)


@functools.lru_cache(maxsize=128)
def _locked_base_states(
    path_raw: str, expected_sha256: str
) -> pd.DataFrame:
    path = capture.locked_root_artifact(
        path_raw,
        expected_sha256,
        "stage2_player_path_states",
    )
    states = pd.read_parquet(path).sort_values("server_tick")
    required = {
        "server_tick",
        "pre.origin",
        "pre.angles",
        "post.origin",
        "post.onground",
    }
    if (
        not required <= set(states.columns)
        or len(states) != capture.TOTAL_TICKS
        or states["server_tick"].astype(int).tolist()
        != list(range(capture.TOTAL_TICKS))
    ):
        raise capture.CaptureFailure(
            "stage2_player_path_states_shape", str(path)
        )
    return states


def prefrozen_trace_artifacts(
    scenario: dict[str, Any],
) -> tuple[tuple[dict[str, Any], ...], pd.DataFrame]:
    """Load one immutable, already-captured player trace for v9 replay.

    The trace supplies only an open-loop movement path and its reference
    camera yaw.  V9 rotates the same movement vector into each newly frozen
    aim trajectory; it never reads the live player, camera, or enemy.
    """
    source = scenario.get("prefrozen_trace_source") or {}
    actions = _locked_base_actions(
        str(source.get("actions_path", "")),
        str(source.get("actions_sha256", "")),
    )
    states = _locked_base_states(
        str(source.get("states_path", "")),
        str(source.get("states_sha256", "")),
    )
    reference_origin = np.asarray(
        states.iloc[0]["pre.origin"], dtype=np.float64
    )
    player_origin = np.asarray(
        scenario["player"]["origin"], dtype=np.float64
    )
    checks = {
        "schema": source.get("schema_version")
        == PREFROZEN_TRACE_SOURCE_SCHEMA,
        "source_episode": bool(source.get("source_episode_id")),
        "source_commit": source.get("source_commit")
        == scenario.get("source_commit_required"),
        "initial_origin": bool(
            np.allclose(
                reference_origin,
                player_origin,
                atol=0.15,
                rtol=0,
            )
        ),
        "action_seed": int(actions[0].get("_seed", -1))
        == int(scenario.get("seed", -2)),
        "weapon_inputs_zero": not any(
            int(row[name])
            for row in actions
            for name in (
                "primary",
                "secondary",
                "reload",
                "weapon_impulse",
            )
        ),
        "trace_has_motion": any(
            abs(float(row["forward"])) > 1e-6
            or abs(float(row["strafe"])) > 1e-6
            for row in actions[capture.WARMUP_TICKS :]
        ),
        "jump_absent": not any(int(row["jump"]) for row in actions),
        "declared_tolerance": (
            8.0
            <= float(source.get("position_error_p95_max", math.nan))
            <= float(source.get("position_error_max_max", math.nan))
            <= 48.0
        ),
        "no_runtime_fallback": (
            source.get("runtime_action_fallback") is False
            and source.get("runtime_geometry_fallback") is False
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_v9_prefrozen_trace_contract_failed",
            capture.canonical_json(checks),
        )
    return actions, states


def player_path_artifacts(
    scenario: dict[str, Any],
) -> tuple[
    tuple[dict[str, Any], ...], pd.DataFrame, dict[str, Any]
]:
    source = scenario.get("player_path_source") or {}
    record = _locked_route_record(
        str(source.get("route_index_path", "")),
        str(source.get("route_index_sha256", "")),
        str(source.get("route_id", "")),
    )
    actions = _locked_base_actions(
        str(source.get("actions_path", "")),
        str(source.get("actions_sha256", "")),
    )
    states = _locked_base_states(
        str(source.get("states_path", "")),
        str(source.get("states_sha256", "")),
    )
    pair_matches = [
        pair
        for pair in record.get("compatible_enemy_pairs", [])
        if pair.get("source_probe")
        == source.get("compatible_enemy_pair_source_probe")
        and pair.get("variant")
        == source.get("compatible_enemy_pair_variant")
    ]
    reference_origin = np.asarray(
        states.iloc[0]["pre.origin"], dtype=np.float64
    )
    player_origin = np.asarray(
        scenario["player"]["origin"], dtype=np.float64
    )
    pair = pair_matches[0] if len(pair_matches) == 1 else {}
    source_schema = source.get("schema_version")
    is_v2_source = source_schema in {
        PLAYER_PATH_SOURCE_SCHEMA_V2,
        PLAYER_PATH_SOURCE_SCHEMA_V3,
        PLAYER_PATH_SOURCE_SCHEMA_V4,
    }
    is_derived_source = source_schema in {
        PLAYER_PATH_SOURCE_SCHEMA_V3,
        PLAYER_PATH_SOURCE_SCHEMA_V4,
    }
    route_plan = scenario.get("route_plan") or {}
    route_plan_hash = hashlib.sha256(
        capture.canonical_json(route_plan).encode("utf-8")
    ).hexdigest()
    reference_player_origins = np.asarray(
        states["pre.origin"].tolist(), dtype=np.float64
    )
    analytic_enemy_origins = np.asarray(
        [
            enemy_origin_at_server_tick(scenario, tick)
            for tick in range(capture.TOTAL_TICKS)
        ],
        dtype=np.float64,
    )
    player_enemy_distances = np.linalg.norm(
        reference_player_origins - analytic_enemy_origins,
        axis=1,
    )
    minimum_clearance_tick = int(
        np.argmin(player_enemy_distances)
    )
    minimum_clearance = float(
        player_enemy_distances[minimum_clearance_tick]
    )
    checks = {
        "source_schema": source_schema
        in {
            PLAYER_PATH_SOURCE_SCHEMA,
            PLAYER_PATH_SOURCE_SCHEMA_V2,
            PLAYER_PATH_SOURCE_SCHEMA_V3,
            PLAYER_PATH_SOURCE_SCHEMA_V4,
        },
        "route_record_hash": source.get("route_record_sha256")
        == hashlib.sha256(
            capture.canonical_json(record).encode("utf-8")
        ).hexdigest(),
        "source_commit": source.get("source_commit")
        == record.get("source_commit")
        == scenario.get("source_commit_required"),
        "route_identity": (
            source.get("route_id") == record.get("route_id")
            and (
                (
                    is_derived_source
                    and source.get("derived_from_actions_path")
                    == record.get("frozen_actions_path")
                    and source.get("derived_from_actions_sha256")
                    == record.get("frozen_actions_sha256")
                )
                or (
                    not is_derived_source
                    and source.get("actions_path")
                    == record.get("frozen_actions_path")
                    and source.get("actions_sha256")
                    == record.get("frozen_actions_sha256")
                )
            )
            and source.get("states_path")
            == record.get("calibration_states_path")
            and source.get("states_sha256")
            == record.get("calibration_states_sha256")
        ),
        "map_mode": (
            scenario.get("map") == record.get("map")
            and str(scenario.get("gametype", "")).lower()
            == str(record.get("gametype", "")).lower()
        ),
        "route_qa": (
            record.get("robust_support_eligible") is True
            and (record.get("route_qa") or {}).get("passed") is True
        ),
        "collision_qa": (
            (record.get("movement_blockage") or {}).get(
                "collision_policy_passed"
            )
            is True
            and (record.get("movement_blockage") or {}).get(
                "ordinary_movement_clear"
            )
            is True
        ),
        "pair_unique": len(pair_matches) == 1,
        "pair_geometry": bool(pair)
        and np.allclose(
            np.asarray(pair["player_origin"], dtype=np.float64),
            player_origin,
            atol=0.15,
        )
        and np.allclose(
            np.asarray(pair["enemy_origin"], dtype=np.float64),
            np.asarray(
                scenario["enemy"]["origin"], dtype=np.float64
            ),
            atol=0.15,
        ),
        "reference_origin": np.allclose(
            reference_origin, player_origin, atol=0.15
        ),
        "seed": int(actions[0]["_seed"])
        == int(scenario.get("seed", -1)),
        "base_weapon_inputs_zero": not any(
            int(row[name])
            for row in actions
            for name in (
                "primary",
                "secondary",
                "reload",
                "weapon_impulse",
            )
        ),
        "jump_contract": int(source.get("base_jump_ticks", -1))
        == int(record.get("base_jump_ticks", -2))
        == sum(int(row["jump"]) for row in actions),
    }
    if is_v2_source:
        design = scenario.get("causal_design") or {}
        initial_reference_angles = states.iloc[0]["pre.angles"]
        expected_initial_yaw = wrap_angle(
            float(initial_reference_angles[1])
            + float(
                design.get("base_view_yaw_offset_deg", 0.0)
            )
        )
        expected_initial_pitch = float(
            initial_reference_angles[0]
        ) + float(
            design.get("base_view_pitch_offset_deg", 0.0)
        )
        checks.update(
            {
                "route_plan_present": bool(route_plan),
                "route_plan_hash": source.get(
                    "route_plan_contract_sha256"
                )
                == route_plan_hash,
                "route_plan_identity": (
                    route_plan.get("route_id") == record.get("route_id")
                    and route_plan.get("route_group_id")
                    == record.get("route_group_id")
                    and route_plan.get("map_region_id")
                    == record.get("map_region_id")
                    and route_plan.get("route_csv_path")
                    == record.get("route_csv_path")
                    and route_plan.get("route_csv_sha256")
                    == record.get("route_csv_sha256")
                    and route_plan.get("frozen_actions_path")
                    == record.get("frozen_actions_path")
                    and route_plan.get("frozen_actions_sha256")
                    == record.get("frozen_actions_sha256")
                    and route_plan.get("calibration_states_path")
                    == record.get("calibration_states_path")
                    and route_plan.get("calibration_states_sha256")
                    == record.get("calibration_states_sha256")
                ),
                "scenario_frozen_actions": (
                    scenario.get("frozen_actions_path")
                    == source.get("actions_path")
                    and scenario.get("frozen_actions_sha256")
                    == source.get("actions_sha256")
                ),
                "base_view_initial_angles": (
                    math.isclose(
                        angle_delta(
                            float(scenario["player"]["yaw"]),
                            expected_initial_yaw,
                        ),
                        0.0,
                        abs_tol=1e-6,
                    )
                    and math.isclose(
                        float(
                            scenario["player"].get("pitch", 0.0)
                        ),
                        expected_initial_pitch,
                        abs_tol=1e-6,
                    )
                ),
                "clearance_metric": source.get(
                    "player_enemy_clearance_metric"
                )
                == "3d_center_distance",
                "clearance_threshold": math.isclose(
                    float(
                        source.get(
                            "player_enemy_clearance_threshold",
                            math.nan,
                        )
                    ),
                    PLAYER_ENEMY_CLEARANCE_MINIMUM,
                    abs_tol=1e-9,
                ),
                "clearance_value": math.isclose(
                    float(
                        source.get(
                            "minimum_player_enemy_clearance",
                            math.nan,
                        )
                    ),
                    minimum_clearance,
                    abs_tol=1e-6,
                ),
                "clearance_tick": int(
                    source.get(
                        "minimum_player_enemy_clearance_server_tick",
                        -1,
                    )
                )
                == minimum_clearance_tick,
                "clearance_passed": (
                    source.get("player_enemy_clearance_passed")
                    is True
                    and minimum_clearance
                    >= PLAYER_ENEMY_CLEARANCE_MINIMUM
                ),
            }
        )
        if is_derived_source:
            original_actions = _locked_base_actions(
                str(record.get("frozen_actions_path", "")),
                str(record.get("frozen_actions_sha256", "")),
            )
            derived_physical_hash = capture.physical_action_sha256(
                actions
            )
            original_physical_hash = (
                capture.physical_action_sha256(original_actions)
            )
            p95_limit = float(
                source.get(
                    "player_path_position_error_p95_max",
                    math.nan,
                )
            )
            max_limit = float(
                source.get(
                    "player_path_position_error_max_max",
                    math.nan,
                )
            )
            route_limit = float(
                scenario.get(
                    "route_replay_origin_tolerance",
                    math.nan,
                )
            )
            if source_schema == PLAYER_PATH_SOURCE_SCHEMA_V3:
                tolerance_contract = (
                    math.isfinite(p95_limit)
                    and math.isfinite(max_limit)
                    and 8.0 < p95_limit <= 16.0
                    and p95_limit <= max_limit <= 32.0
                    and math.isclose(
                        route_limit,
                        max_limit,
                        abs_tol=1e-9,
                    )
                )
            else:
                tolerance_contract = (
                    int(source.get("base_jump_ticks", 0)) > 0
                    and design.get("player_motion_class") == "jumping"
                    and source.get("overlay_replay_tolerance_basis")
                    == JUMP_VIEW_OVERLAY_TOLERANCE_BASIS
                    and math.isclose(
                        p95_limit,
                        JUMP_VIEW_OVERLAY_REPLAY_TOLERANCE,
                        abs_tol=1e-9,
                    )
                    and math.isclose(
                        max_limit,
                        JUMP_VIEW_OVERLAY_REPLAY_TOLERANCE,
                        abs_tol=1e-9,
                    )
                    and math.isclose(
                        route_limit,
                        JUMP_VIEW_OVERLAY_REPLAY_TOLERANCE,
                        abs_tol=1e-9,
                    )
                )
            checks.update(
                {
                    "derived_physical_action_hash": (
                        source.get("physical_action_sha256")
                        == derived_physical_hash
                        == original_physical_hash
                    ),
                    "derived_seed_is_new": (
                        int(actions[0]["_seed"])
                        != int(original_actions[0]["_seed"])
                    ),
                    "declared_path_tolerances": tolerance_contract,
                    "nonzero_base_view_offset": (
                        abs(
                            float(
                                design.get(
                                    "base_view_yaw_offset_deg",
                                    0.0,
                                )
                            )
                        )
                        > 1e-6
                        or abs(
                            float(
                                design.get(
                                    "base_view_pitch_offset_deg",
                                    0.0,
                                )
                            )
                        )
                        > 1e-6
                    ),
                }
            )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_player_path_contract_failed",
            capture.canonical_json(checks),
        )
    return actions, states, record


def _smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def _transition(
    tick: int, start_tick: int, end_tick: int, start: float, end: float
) -> float:
    if tick <= start_tick:
        return start
    if tick >= end_tick:
        return end
    progress = _smoothstep((tick - start_tick) / (end_tick - start_tick))
    return start + (end - start) * progress


def wrap_angle(angle: float) -> float:
    while angle > 180.0:
        angle -= 360.0
    while angle <= -180.0:
        angle += 360.0
    return angle


def angle_delta(target: float, current: float) -> float:
    return wrap_angle(target - current)


def yaw_pitch_toward(
    player_origin: list[float], enemy_origin: list[float]
) -> tuple[float, float]:
    dx = enemy_origin[0] - player_origin[0]
    dy = enemy_origin[1] - player_origin[1]
                                                                          
                                                                      
    dz = (enemy_origin[2] + 24.0) - (player_origin[2] + 35.0)
    horizontal = math.hypot(dx, dy)
    return (
        math.degrees(math.atan2(dy, dx)),
        -math.degrees(math.atan2(dz, max(horizontal, 1e-9))),
    )


def enemy_policy_unit(seed: int, segment_index: int, channel: int) -> float:
    """Exact Python mirror of ``Capture_EnemyPolicyUnit`` in QuakeC."""
    key = f"{int(seed)}:{int(segment_index)}:{int(channel)}"
    return (
        binascii.crc_hqx(key.encode("ascii"), 0xFFFF) / 65536.0
    )


def enemy_policy_state_at_server_tick(
    scenario: dict[str, Any], server_tick: int
) -> dict[str, Any]:
    """Return the frozen mode-4 segment explanation for one server tick."""
    enemy = scenario["enemy"]
    start_tick = int(
        enemy.get(
            "motion_start_tick",
            (scenario.get("enemy_policy") or {}).get(
                "motion_start_tick", 0
            ),
        )
    )
    policy_tick = int(server_tick) - start_tick
    if int(enemy.get("motion", 0)) != 4 or policy_tick < 0:
        return {
            "segment": -1,
            "progress": 0.0,
            "hold": False,
            "hop": False,
        }
    policy_seed = int(
        (scenario.get("enemy_policy") or {}).get(
            "policy_seed", scenario["seed"]
        )
    )
    segment_start_tick = 0
    for segment in range(32):
        duration = 32 + math.floor(
            enemy_policy_unit(policy_seed, segment, 0) * 48
        )
        hold = enemy_policy_unit(policy_seed, segment, 1) < 0.18
        if policy_tick < segment_start_tick + duration:
            progress = min(
                1.0,
                max(
                    0.0,
                    (policy_tick - segment_start_tick)
                    / max(1, duration),
                ),
            )
            return {
                "segment": segment,
                "progress": progress,
                "hold": hold,
                "hop": (
                    not hold
                    and enemy_policy_unit(
                        policy_seed, segment, 4
                    )
                    < 0.22
                ),
            }
        segment_start_tick += duration
    raise capture.CaptureFailure(
        "stage2_enemy_policy_segment_exhausted",
        f"server_tick={server_tick} policy_tick={policy_tick}",
    )


def enemy_origin_at_server_tick(
    scenario: dict[str, Any], server_tick: int
) -> list[float]:
    """Mirror ``Capture_MoveEnemy`` for a frozen analytic trajectory."""
    enemy = scenario["enemy"]
    origin = np.asarray(enemy["origin"], dtype=np.float64)
    mode = int(enemy.get("motion", 0))
    distance = float(enemy.get("motion_distance", 0.0))
    start_tick = int(
        enemy.get(
            "motion_start_tick",
            (scenario.get("enemy_policy") or {}).get("motion_start_tick", 0),
        )
    )
    policy_tick = server_tick - start_tick
    if mode == 0 or policy_tick < 0:
        return origin.tolist()
    t = max(0, policy_tick) / 64.0
    vector = np.asarray(
        enemy.get("motion_vector", [0.0, 0.0, 0.0]),
        dtype=np.float64,
    )
    if mode == 1:
        offset = vector * (math.sin(t * math.pi * 0.8) * distance)
    elif mode == 2:
        radial = (
            np.asarray(scenario["player"]["origin"], dtype=np.float64)
            - origin
        )
        norm = float(np.linalg.norm(radial))
        radial = radial / norm if norm > 1e-9 else np.zeros(3)
        offset = radial * (math.sin(t * math.pi * 0.4) * distance)
    elif mode == 3:
        phase = t - math.floor(t / 3.0) * 3.0
        if phase < 0.5:
            scalar = math.sin(phase * math.pi)
        elif phase < 1.0:
            scalar = 1.0
        elif phase < 2.0:
            scalar = math.cos((phase - 1.0) * math.pi)
        elif phase < 2.5:
            scalar = -1.0
        else:
            scalar = -math.cos((phase - 2.5) * math.pi)
        offset = vector * (scalar * distance)
    elif mode == 4:
        axis = vector.copy()
        axis[2] = 0.0
        axis_norm = float(np.linalg.norm(axis))
        axis = (
            axis / axis_norm
            if axis_norm >= 0.001
            else np.asarray([1.0, 0.0, 0.0])
        )
        side = np.asarray([-axis[1], axis[0], 0.0])
        policy_seed = int(
            (scenario.get("enemy_policy") or {}).get(
                "policy_seed", scenario["seed"]
            )
        )
        segment_start = np.zeros(3, dtype=np.float64)
        segment_end = np.zeros(3, dtype=np.float64)
        segment_start_tick = 0
        segment_duration = 1
        segment_index = -1
        segment_hold = False
        for segment in range(32):
            segment_duration = 32 + math.floor(
                enemy_policy_unit(policy_seed, segment, 0) * 48
            )
            segment_hold = (
                enemy_policy_unit(policy_seed, segment, 1) < 0.18
            )
            if segment_hold:
                segment_end = segment_start.copy()
            else:
                angle = (
                    enemy_policy_unit(policy_seed, segment, 2)
                    * 2.0
                    * math.pi
                )
                radius = (
                    0.25
                    + 0.75
                    * math.sqrt(
                        enemy_policy_unit(policy_seed, segment, 3)
                    )
                ) * distance
                segment_end = (
                    axis * math.cos(angle) + side * math.sin(angle)
                ) * radius
            if policy_tick < segment_start_tick + segment_duration:
                segment_index = segment
                break
            segment_start_tick += segment_duration
            segment_start = segment_end.copy()
        progress = min(
            1.0,
            max(
                0.0,
                (policy_tick - segment_start_tick)
                / max(1, segment_duration),
            ),
        )
        smooth = progress * progress * (3.0 - 2.0 * progress)
        offset = segment_start + (segment_end - segment_start) * smooth
        policy_hop = (
            not segment_hold
            and enemy_policy_unit(policy_seed, segment_index, 4) < 0.22
        )
        if policy_hop:
            hop_height = 6.0 + (
                enemy_policy_unit(policy_seed, segment_index, 5) * 12.0
            )
            offset[2] = math.sin(progress * math.pi) * hop_height
    else:
        raise capture.CaptureFailure(
            "stage2_enemy_motion_mode_unknown", str(mode)
        )
    return (origin + offset).tolist()


def policy_offsets(policy: str, out_tick: int) -> tuple[float, float]:
    """Return the declared yaw/pitch offset from the frozen target bearing."""
    if policy == "visible_no_response":
        return INITIAL_YAW_OFFSET_DEG, INITIAL_PITCH_OFFSET_DEG
    if policy == "delayed_acquisition":
        return (
            _transition(
                out_tick, 80, 144, INITIAL_YAW_OFFSET_DEG, 0.0
            ),
            _transition(
                out_tick, 80, 144, INITIAL_PITCH_OFFSET_DEG, 0.0
            ),
        )
    if policy == "pass_offset":
        if out_tick < 40:
            yaw = INITIAL_YAW_OFFSET_DEG
        elif out_tick < 112:
            yaw = _transition(
                out_tick, 40, 112, INITIAL_YAW_OFFSET_DEG, -3.0
            )
        elif out_tick < 152:
            yaw = _transition(out_tick, 112, 152, -3.0, 10.0)
        else:
            yaw = 10.0
        pitch = _transition(
            out_tick, 40, 104, INITIAL_PITCH_OFFSET_DEG, 0.0
        )
        return yaw, pitch
    if policy == "track_loss_reacquire":
        if out_tick < 16:
            yaw = INITIAL_YAW_OFFSET_DEG
        elif out_tick < 64:
            yaw = _transition(
                out_tick, 16, 64, INITIAL_YAW_OFFSET_DEG, 0.0
            )
        elif out_tick < 120:
            yaw = 0.0
        elif out_tick < 152:
            yaw = _transition(out_tick, 120, 152, 0.0, 38.0)
        elif out_tick < 184:
            yaw = 38.0
        elif out_tick < 232:
            yaw = _transition(out_tick, 184, 232, 38.0, 0.0)
        else:
            yaw = 0.0
        pitch = _transition(
            out_tick, 16, 64, INITIAL_PITCH_OFFSET_DEG, 0.0
        )
        return yaw, pitch
    if policy == "sustained_tracking":
        return (
            _transition(
                out_tick, 8, 56, INITIAL_YAW_OFFSET_DEG, 0.0
            ),
            _transition(
                out_tick, 8, 56, INITIAL_PITCH_OFFSET_DEG, 0.0
            ),
        )
    raise capture.CaptureFailure("stage2_aim_policy_unknown", policy)


def default_aim_schedule(policy: str) -> dict[str, Any]:
    """Return the manifest-frozen v3 timing contract for one aim policy."""
    common = {
        "schema_version": AIM_SCHEDULE_SCHEMA,
        "policy": policy,
    }
    if policy == "visible_no_response":
        return {
            **common,
            "response_start_output_tick": None,
        }
    if policy == "delayed_acquisition":
        return {
            **common,
            "response_start_output_tick": 80,
            "acquisition_end_output_tick": 144,
        }
    if policy == "pass_offset":
        return {
            **common,
            "response_start_output_tick": 40,
            "pass_end_output_tick": 112,
            "depart_end_output_tick": 152,
            "pass_yaw_offset_deg": -3.0,
            "fire_yaw_offset_deg": 10.0,
        }
    if policy == "track_loss_reacquire":
        return {
            **common,
            "response_start_output_tick": 16,
            "acquisition_end_output_tick": 64,
            "centered_hold_end_output_tick": 120,
            "loss_end_output_tick": 152,
            "lost_hold_end_output_tick": 184,
            "reacquisition_end_output_tick": 232,
            "loss_yaw_offset_deg": 38.0,
        }
    if policy == "sustained_tracking":
        return {
            **common,
            "response_start_output_tick": 8,
            "acquisition_end_output_tick": 56,
            "minimum_visible_tracking_frames": 64,
            "minimum_centered_given_visible_fraction": 0.90,
        }
    raise capture.CaptureFailure("stage2_aim_policy_unknown", policy)


def default_aim_schedule_v5(policy: str) -> dict[str, Any]:
    """Return the humanized v5 timing contract for one aim policy.

    Unlike v3/v4, track loss is a tracking pause while the independently
    moving target continues.  The camera is never commanded to depart by a
    fixed angular offset.
    """
    common = {
        "schema_version": AIM_SCHEDULE_SCHEMA_V2,
        "policy": policy,
    }
    if policy == "visible_no_response":
        return {
            **common,
            "response_start_output_tick": None,
        }
    if policy == "delayed_acquisition":
        return {
            **common,
            "response_start_output_tick": 72,
            "acquisition_end_output_tick": 144,
            "settle_end_output_tick": 176,
        }
    if policy == "pass_offset":
        return {
            **common,
            "response_start_output_tick": 32,
            "pass_end_output_tick": 104,
            "depart_end_output_tick": 156,
            "pass_yaw_offset_deg": -2.0,
            "fire_yaw_offset_deg": 8.0,
        }
    if policy == "track_loss_reacquire":
        return {
            **common,
            "response_start_output_tick": 16,
            "acquisition_end_output_tick": 72,
            "centered_hold_end_output_tick": 128,
            "tracking_pause_end_output_tick": 192,
            "reacquisition_end_output_tick": 248,
            "minimum_centered_before_pause_frames": 8,
            "minimum_loss_frames": 8,
            "loss_mechanism": (
                "tracking_pause_target_motion_or_occlusion"
            ),
        }
    if policy == "sustained_tracking":
        return {
            **common,
            "response_start_output_tick": 8,
            "acquisition_end_output_tick": 56,
            "minimum_visible_tracking_frames": 64,
            "tracking_error_threshold_deg": 6.0,
            "minimum_centered_given_visible_fraction": 0.75,
        }
    raise capture.CaptureFailure("stage2_aim_policy_unknown", policy)


def validate_aim_schedule_v5(
    policy: str, schedule: dict[str, Any]
) -> None:
    expected = set(default_aim_schedule_v5(policy))
    checks = {
        "mapping": isinstance(schedule, dict),
        "schema": schedule.get("schema_version")
        == AIM_SCHEDULE_SCHEMA_V2,
        "policy": schedule.get("policy") == policy,
        "exact_fields": set(schedule) == expected,
    }
    tick_fields = {
        "visible_no_response": ("response_start_output_tick",),
        "delayed_acquisition": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
            "settle_end_output_tick",
        ),
        "pass_offset": (
            "response_start_output_tick",
            "pass_end_output_tick",
            "depart_end_output_tick",
        ),
        "track_loss_reacquire": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
            "centered_hold_end_output_tick",
            "tracking_pause_end_output_tick",
            "reacquisition_end_output_tick",
        ),
        "sustained_tracking": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
        ),
    }[policy]
    ticks = [
        schedule.get(name)
        for name in tick_fields
        if schedule.get(name) is not None
    ]
    checks["tick_values"] = all(
        isinstance(value, int)
        and 0 <= value < capture.OUTPUT_TICKS
        for value in ticks
    )
    checks["tick_order"] = ticks == sorted(ticks) and len(ticks) == len(
        set(ticks)
    )
    if policy == "track_loss_reacquire":
        checks["natural_loss"] = (
            schedule.get("loss_mechanism")
            == "tracking_pause_target_motion_or_occlusion"
            and isinstance(
                schedule.get(
                    "minimum_centered_before_pause_frames"
                ),
                int,
            )
            and 1
            <= int(
                schedule["minimum_centered_before_pause_frames"]
            )
            <= 64
            and isinstance(schedule.get("minimum_loss_frames"), int)
            and 1 <= int(schedule["minimum_loss_frames"]) <= 64
            and "loss_yaw_offset_deg" not in schedule
        )
    if policy == "sustained_tracking":
        checks["tracking_thresholds"] = (
            isinstance(
                schedule.get("minimum_visible_tracking_frames"), int
            )
            and 1
            <= int(schedule["minimum_visible_tracking_frames"])
            <= capture.OUTPUT_TICKS
            and 3.0
            <= float(schedule["tracking_error_threshold_deg"])
            <= 8.0
            and 0.5
            <= float(
                schedule[
                    "minimum_centered_given_visible_fraction"
                ]
            )
            <= 1.0
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_v5_aim_schedule_contract_failed",
            capture.canonical_json(checks),
        )


def default_aim_schedule_v6(policy: str) -> dict[str, Any]:
    """Return the v6 schedule with two-dimensional miss treatments."""
    common = {
        "schema_version": AIM_SCHEDULE_SCHEMA_V3,
        "policy": policy,
    }
    if policy == "visible_no_response":
        return {
            **common,
            "response_start_output_tick": None,
        }
    if policy == "delayed_acquisition":
        return {
            **common,
            "response_start_output_tick": 72,
            "acquisition_end_output_tick": 144,
            "settle_end_output_tick": 176,
        }
    if policy == "pass_offset":
        return {
            **common,
            "response_start_output_tick": 32,
            "pass_end_output_tick": 104,
            "depart_end_output_tick": 156,
            "pass_yaw_offset_deg": 8.0,
            "pass_pitch_offset_deg": 0.0,
            "fire_yaw_offset_deg": 8.0,
            "fire_pitch_offset_deg": 0.0,
            "miss_trajectory_style": "persistent_bias",
            "miss_direction_sector": "right",
            "miss_magnitude_bin": "medium",
            "minimum_fire_error_deg": 3.25,
            "requires_target_pass": False,
        }
    if policy == "track_loss_reacquire":
        schedule = default_aim_schedule_v5(policy)
        schedule["schema_version"] = AIM_SCHEDULE_SCHEMA_V3
        return schedule
    if policy == "sustained_tracking":
        return {
            **common,
            "response_start_output_tick": 8,
            "acquisition_end_output_tick": 56,
            "pre_fire_tracking_end_output_tick": 160,
            "minimum_visible_tracking_frames": 64,
            "tracking_error_threshold_deg": 6.0,
            "minimum_centered_given_visible_fraction": 0.75,
        }
    raise capture.CaptureFailure("stage2_aim_policy_unknown", policy)


def miss_direction_sector(yaw: float, pitch: float) -> str:
    """Classify a controller offset by its on-screen crosshair direction.

    Positive engine yaw moves the crosshair left of the target, while
    positive engine pitch moves it below the target.
    """
    if not math.isfinite(yaw) or not math.isfinite(pitch):
        raise capture.CaptureFailure(
            "stage2_v6_miss_vector_nonfinite",
            f"yaw={yaw} pitch={pitch}",
        )
    angle = math.degrees(math.atan2(pitch, -yaw))
    return MISS_DIRECTION_SECTORS[int(round(angle / 45.0)) % 8]


def realized_miss_magnitude_bin(magnitude: float) -> str:
    if magnitude < MISS_MAGNITUDE_BOUNDS["near_edge"][0]:
        return "inside_near_edge"
    for name, (lower, upper) in MISS_MAGNITUDE_BOUNDS.items():
        if lower <= magnitude < upper:
            return name
    return "beyond_large"


def validate_aim_schedule_v6(
    policy: str, schedule: dict[str, Any]
) -> None:
    expected = set(default_aim_schedule_v6(policy))
    checks: dict[str, bool] = {
        "mapping": isinstance(schedule, dict),
        "schema": schedule.get("schema_version")
        == AIM_SCHEDULE_SCHEMA_V3,
        "policy": schedule.get("policy") == policy,
        "exact_fields": set(schedule) == expected,
    }
    tick_fields = {
        "visible_no_response": ("response_start_output_tick",),
        "delayed_acquisition": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
            "settle_end_output_tick",
        ),
        "pass_offset": (
            "response_start_output_tick",
            "pass_end_output_tick",
            "depart_end_output_tick",
        ),
        "track_loss_reacquire": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
            "centered_hold_end_output_tick",
            "tracking_pause_end_output_tick",
            "reacquisition_end_output_tick",
        ),
        "sustained_tracking": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
            "pre_fire_tracking_end_output_tick",
        ),
    }[policy]
    ticks = [
        schedule.get(name)
        for name in tick_fields
        if schedule.get(name) is not None
    ]
    checks["tick_values"] = all(
        isinstance(value, int)
        and 0 <= value < capture.OUTPUT_TICKS
        for value in ticks
    )
    checks["tick_order"] = ticks == sorted(ticks) and len(ticks) == len(
        set(ticks)
    )
    if policy == "pass_offset":
        vector_names = (
            "pass_yaw_offset_deg",
            "pass_pitch_offset_deg",
            "fire_yaw_offset_deg",
            "fire_pitch_offset_deg",
            "minimum_fire_error_deg",
        )
        vectors = {
            name: float(schedule.get(name, math.nan))
            for name in vector_names
        }
        fire_yaw = vectors["fire_yaw_offset_deg"]
        fire_pitch = vectors["fire_pitch_offset_deg"]
        fire_magnitude = math.hypot(fire_yaw, fire_pitch)
        pass_magnitude = math.hypot(
            vectors["pass_yaw_offset_deg"],
            vectors["pass_pitch_offset_deg"],
        )
        magnitude_bin = str(schedule.get("miss_magnitude_bin", ""))
        bounds = MISS_MAGNITUDE_BOUNDS.get(magnitude_bin)
        checks.update(
            {
                "finite_miss_vectors": all(
                    math.isfinite(value) for value in vectors.values()
                ),
                "bounded_miss_vectors": pass_magnitude <= 18.0
                and fire_magnitude <= 18.0,
                "trajectory_style": schedule.get(
                    "miss_trajectory_style"
                )
                in MISS_TRAJECTORY_STYLES,
                "direction_sector": schedule.get(
                    "miss_direction_sector"
                )
                in MISS_DIRECTION_SECTORS
                and schedule.get("miss_direction_sector")
                == miss_direction_sector(fire_yaw, fire_pitch),
                "magnitude_bin": bounds is not None
                and bounds[0] <= fire_magnitude < bounds[1],
                "minimum_fire_error": 3.0
                <= vectors["minimum_fire_error_deg"]
                <= fire_magnitude,
                "requires_target_pass_boolean": isinstance(
                    schedule.get("requires_target_pass"), bool
                ),
                "pass_geometry": (
                    not schedule.get("requires_target_pass")
                    or pass_magnitude <= 4.0
                ),
            }
        )
    if policy == "track_loss_reacquire":
        checks["natural_loss"] = (
            schedule.get("loss_mechanism")
            == "tracking_pause_target_motion_or_occlusion"
            and isinstance(
                schedule.get("minimum_centered_before_pause_frames"),
                int,
            )
            and 1
            <= int(schedule["minimum_centered_before_pause_frames"])
            <= 64
            and isinstance(schedule.get("minimum_loss_frames"), int)
            and 1 <= int(schedule["minimum_loss_frames"]) <= 64
            and "loss_yaw_offset_deg" not in schedule
        )
    if policy == "sustained_tracking":
        checks["tracking_thresholds"] = (
            isinstance(
                schedule.get("minimum_visible_tracking_frames"), int
            )
            and 1
            <= int(schedule["minimum_visible_tracking_frames"])
            <= capture.OUTPUT_TICKS
            and 3.0
            <= float(schedule["tracking_error_threshold_deg"])
            <= 8.0
            and 0.5
            <= float(
                schedule[
                    "minimum_centered_given_visible_fraction"
                ]
            )
            <= 1.0
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_v6_aim_schedule_contract_failed",
            capture.canonical_json(checks),
        )


def validate_fire_program(
    program: dict[str, Any],
    *,
    policy: str,
    design: dict[str, Any],
) -> None:
    if not isinstance(program, dict):
        raise capture.CaptureFailure(
            "stage2_v6_fire_program_contract_failed",
            capture.canonical_json({"mapping": False}),
        )
    expected_fields = {
        "schema_version",
        "name",
        "weapon_fire_family",
        "windows",
        "expected_min_fire_events",
        "expected_max_fire_events",
        "requires_multiple_fire_events",
        "selection_uses_authoritative_events",
    }
    windows = program.get("windows")
    parsed: list[tuple[int, int]] = []
    windows_shape = isinstance(windows, list)
    if windows_shape:
        for window in windows:
            if (
                not isinstance(window, dict)
                or set(window)
                != {"start_output_tick", "duration_ticks"}
                or not isinstance(window.get("start_output_tick"), int)
                or not isinstance(window.get("duration_ticks"), int)
            ):
                windows_shape = False
                break
            start = int(window["start_output_tick"])
            duration = int(window["duration_ticks"])
            parsed.append((start, duration))
    name = str(program.get("name", ""))
    raw_minimum = program.get("expected_min_fire_events")
    raw_maximum = program.get("expected_max_fire_events")
    event_bounds_shape = (
        isinstance(raw_minimum, int)
        and not isinstance(raw_minimum, bool)
        and isinstance(raw_maximum, int)
        and not isinstance(raw_maximum, bool)
    )
    minimum = int(raw_minimum) if event_bounds_shape else -1
    maximum = int(raw_maximum) if event_bounds_shape else -1
    starts = [start for start, _ in parsed]
    nonoverlap = all(
        left_start + left_duration <= right_start
        for (left_start, left_duration), (
            right_start,
            _,
        ) in zip(parsed, parsed[1:])
    )
    expected_window_count = {
        "none": 0,
        "single_tap": 1,
        "short_burst": 1,
        "long_burst": 1,
        "double_burst": 2,
    }.get(name)
    window_count_valid = (
        len(parsed) >= 2
        if name == "multi_tap"
        else expected_window_count == len(parsed)
    )
    checks = {
        "mapping": isinstance(program, dict),
        "exact_fields": set(program) == expected_fields,
        "schema": program.get("schema_version")
        == FIRE_PROGRAM_SCHEMA,
        "name": name in FIRE_PROGRAM_NAMES,
        "family": program.get("weapon_fire_family")
        in {"none", "rapid_auto", "repeat_hold", "spaced_tap"},
        "family_matches_program": (
            name == "none"
            and program.get("weapon_fire_family") == "none"
        )
        or (
            name != "none"
            and program.get("weapon_fire_family")
            in {"rapid_auto", "repeat_hold", "spaced_tap"}
        ),
        "windows_shape": windows_shape,
        "windows_in_output": all(
            0 <= start < capture.OUTPUT_TICKS
            and 1 <= duration <= 144
            and start + duration <= capture.OUTPUT_TICKS
            for start, duration in parsed
        ),
        "windows_sorted_nonoverlap": starts == sorted(starts)
        and len(starts) == len(set(starts))
        and nonoverlap,
        "window_count": window_count_valid,
        "event_bounds": event_bounds_shape
        and 0 <= minimum <= maximum <= 64,
        "multiple_contract": (
            program.get("requires_multiple_fire_events")
            is (name not in {"none", "single_tap"})
            and (
                name in {"none", "single_tap"}
                or minimum >= 2
            )
        ),
        "authoritative_selection": program.get(
            "selection_uses_authoritative_events"
        )
        is True,
        "policy_fire": (
            policy == "visible_no_response"
            and name == "none"
            and not parsed
            and minimum == maximum == 0
        )
        or (
            policy in FIRING_POLICIES
            and name != "none"
            and bool(parsed)
            and minimum >= 1
        ),
        "legacy_starts_match": design.get("fire_output_ticks") == starts,
        "legacy_width_not_authoritative": design.get(
            "fire_width_ticks"
        )
        == 2,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_v6_fire_program_contract_failed",
            capture.canonical_json(checks),
        )


def validate_random_aim_program(program: dict[str, Any]) -> None:
    expected_fields = {
        "schema_version",
        "seed",
        "algorithm",
        "interpolation",
        "knot_output_ticks",
        "yaw_offset_deg",
        "pitch_offset_deg",
        "max_abs_yaw_offset_deg",
        "max_abs_pitch_offset_deg",
        "reads_live_enemy_state",
        "reads_live_player_state",
        "reads_camera",
        "reads_crosshair",
    }
    ticks = program.get("knot_output_ticks")
    yaw = program.get("yaw_offset_deg")
    pitch = program.get("pitch_offset_deg")
    sequence_shape = (
        isinstance(ticks, list)
        and isinstance(yaw, list)
        and isinstance(pitch, list)
        and len(ticks) == len(yaw) == len(pitch)
        and 6 <= len(ticks) <= 16
    )
    parsed_ticks = (
        [int(value) for value in ticks]
        if sequence_shape
        and all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in ticks
        )
        else []
    )
    parsed_yaw = (
        [float(value) for value in yaw] if sequence_shape else []
    )
    parsed_pitch = (
        [float(value) for value in pitch] if sequence_shape else []
    )
    gaps = [
        right - left
        for left, right in zip(parsed_ticks, parsed_ticks[1:])
    ]
    max_yaw = float(program.get("max_abs_yaw_offset_deg", math.nan))
    max_pitch = float(
        program.get("max_abs_pitch_offset_deg", math.nan)
    )
    checks = {
        "mapping": isinstance(program, dict),
        "exact_fields": set(program) == expected_fields,
        "schema": program.get("schema_version")
        == RANDOM_AIM_PROGRAM_SCHEMA,
        "seed": isinstance(program.get("seed"), int)
        and not isinstance(program.get("seed"), bool)
        and 0 < int(program["seed"]) < 2**31,
        "algorithm": program.get("algorithm")
        == "manifest_frozen_piecewise_smooth_view_v1",
        "interpolation": program.get("interpolation") == "smoothstep",
        "sequence_shape": sequence_shape and bool(parsed_ticks),
        "tick_span": bool(parsed_ticks)
        and parsed_ticks[0] == 0
        and parsed_ticks[-1] == capture.OUTPUT_TICKS - 1,
        "ticks_strict": parsed_ticks == sorted(set(parsed_ticks)),
        "bounded_segment_duration": bool(gaps)
        and all(24 <= gap <= 80 for gap in gaps),
        "finite_values": all(
            math.isfinite(value)
            for value in parsed_yaw + parsed_pitch
        ),
        "starts_at_baseline": bool(parsed_yaw)
        and math.isclose(parsed_yaw[0], 0.0, abs_tol=1e-9)
        and math.isclose(parsed_pitch[0], 0.0, abs_tol=1e-9),
        "declared_bounds": 12.0 <= max_yaw <= 50.0
        and 6.0 <= max_pitch <= 25.0,
        "values_in_bounds": bool(parsed_yaw)
        and max(abs(value) for value in parsed_yaw) <= max_yaw
        and max(abs(value) for value in parsed_pitch) <= max_pitch,
        "two_axis_variation": bool(parsed_yaw)
        and max(parsed_yaw) - min(parsed_yaw) >= 12.0
        and max(parsed_pitch) - min(parsed_pitch) >= 5.0,
        "no_live_reads": all(
            program.get(name) is False
            for name in (
                "reads_live_enemy_state",
                "reads_live_player_state",
                "reads_camera",
                "reads_crosshair",
            )
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_v7_random_aim_program_contract_failed",
            capture.canonical_json(checks),
        )


def validate_weapon_balanced_aim_program(
    program: dict[str, Any],
) -> None:
    expected_fields = {
        "schema_version",
        "seed",
        "arm",
        "family",
        "algorithm",
        "response_start_output_tick",
        "settle_output_tick",
        "target_offset_scale",
        "offset_direction_deg",
        "offset_radius_kind",
        "projectile_lead",
        "motor_profile",
        "random_aim_program",
        "target_radius_model",
        "reads_live_enemy_state",
        "reads_live_player_state",
        "reads_camera",
        "reads_crosshair",
    }
    arm = str(program.get("arm", ""))
    family = str(program.get("family", ""))
    humanized = arm in WEAPON_BALANCED_HUMANIZED_ARMS
    stochastic = arm in WEAPON_BALANCED_STOCHASTIC_ARMS
    motor_profile = program.get("motor_profile")
    random_program = program.get("random_aim_program")
    if humanized and isinstance(motor_profile, dict):
        validate_aim_motor_profile(motor_profile)
    if stochastic and isinstance(random_program, dict):
        validate_random_aim_program(random_program)
    response = program.get("response_start_output_tick")
    settle = program.get("settle_output_tick")
    offset_scale = program.get("target_offset_scale")
    offset_direction = program.get("offset_direction_deg")
    checks = {
        "mapping": isinstance(program, dict),
        "exact_fields": set(program) == expected_fields,
        "schema": program.get("schema_version")
        == WEAPON_BALANCED_AIM_PROGRAM_SCHEMA,
        "arm": arm in WEAPON_BALANCED_AIM_ARMS,
        "family": (
            family == "humanized_target_conditioned"
            if humanized
            else family
            in {"stochastic_free_aim", "visible_no_fire"}
        ),
        "algorithm": program.get("algorithm")
        == "manifest_frozen_weapon_conditioned_view_v1",
        "seed": isinstance(program.get("seed"), int)
        and not isinstance(program.get("seed"), bool)
        and 0 < int(program["seed"]) < 2**24,
        "timing": isinstance(response, int)
        and isinstance(settle, int)
        and 0 <= int(response) < int(settle) < capture.OUTPUT_TICKS,
        "offset": isinstance(offset_scale, (int, float))
        and not isinstance(offset_scale, bool)
        and math.isfinite(float(offset_scale))
        and 0.0 <= float(offset_scale) <= 2.5
        and isinstance(offset_direction, (int, float))
        and not isinstance(offset_direction, bool)
        and math.isfinite(float(offset_direction))
        and -180.0 <= float(offset_direction) <= 180.0,
        "offset_radius_kind": program.get("offset_radius_kind")
        in {"target_hull", "weapon_effective_damage"},
        "lead": isinstance(program.get("projectile_lead"), bool),
        "arm_program": (
            isinstance(motor_profile, dict)
            and random_program is None
            if humanized
            else motor_profile is None
            and isinstance(random_program, dict)
        ),
        "radius_model": program.get("target_radius_model")
        == "camera_to_torso_elliptical_hull_plus_weapon_radius_v1",
        "frozen": all(
            program.get(name) is False
            for name in (
                "reads_live_enemy_state",
                "reads_live_player_state",
                "reads_camera",
                "reads_crosshair",
            )
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_v9_weapon_balanced_aim_program_failed",
            capture.canonical_json(checks),
        )


def validate_player_movement_program(
    program: dict[str, Any],
) -> None:
    """Validate a manifest-frozen, open-loop continuous movement program."""
    expected_fields = {
        "schema_version",
        "seed",
        "algorithm",
        "interpolation",
        "profile",
        "knot_output_ticks",
        "j_left_x",
        "j_left_y",
        "max_abs_axis_value",
        "jump_enabled",
        "reads_live_enemy_state",
        "reads_live_player_state",
        "reads_camera",
        "reads_crosshair",
    }
    ticks = program.get("knot_output_ticks")
    left_x = program.get("j_left_x")
    left_y = program.get("j_left_y")
    sequence_shape = (
        isinstance(ticks, list)
        and isinstance(left_x, list)
        and isinstance(left_y, list)
        and len(ticks) == len(left_x) == len(left_y)
        and 6 <= len(ticks) <= 16
    )
    parsed_ticks = (
        [int(value) for value in ticks]
        if sequence_shape
        and all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in ticks
        )
        else []
    )
    parsed_x = (
        [float(value) for value in left_x] if sequence_shape else []
    )
    parsed_y = (
        [float(value) for value in left_y] if sequence_shape else []
    )
    gaps = [
        right - left
        for left, right in zip(parsed_ticks, parsed_ticks[1:])
    ]
    bound = float(program.get("max_abs_axis_value", math.nan))

    def direction_reversals(values: list[float]) -> int:
        signs = [
            1 if value > 1e-4 else -1
            for value in values
            if abs(value) > 1e-4
        ]
        return sum(
            left != right
            for left, right in zip(signs, signs[1:])
        )

    checks = {
        "mapping": isinstance(program, dict),
        "exact_fields": set(program) == expected_fields,
        "schema": program.get("schema_version")
        == PLAYER_MOVEMENT_PROGRAM_SCHEMA,
                                                           
        "seed": isinstance(program.get("seed"), int)
        and not isinstance(program.get("seed"), bool)
        and 0 < int(program["seed"]) < 2**24,
        "algorithm": program.get("algorithm")
        == "manifest_frozen_piecewise_smooth_player_movement_v1",
        "interpolation": program.get("interpolation") == "smoothstep",
        "profile": program.get("profile")
        in PLAYER_MOVEMENT_PROGRAM_PROFILES,
        "sequence_shape": sequence_shape and bool(parsed_ticks),
        "tick_span": bool(parsed_ticks)
        and parsed_ticks[0] == 0
        and parsed_ticks[-1] == capture.OUTPUT_TICKS - 1,
        "ticks_strict": parsed_ticks == sorted(set(parsed_ticks)),
        "bounded_segment_duration": bool(gaps)
        and all(24 <= gap <= 80 for gap in gaps),
        "finite_values": all(
            math.isfinite(value) for value in parsed_x + parsed_y
        ),
        "neutral_endpoints": bool(parsed_x)
        and all(
            math.isclose(value, 0.0, abs_tol=1e-9)
            for value in (
                parsed_x[0],
                parsed_y[0],
                parsed_x[-1],
                parsed_y[-1],
            )
        ),
        "declared_bound": 0.12 <= bound <= 0.35,
        "values_in_bounds": bool(parsed_x)
        and max(
            abs(value) for value in parsed_x + parsed_y
        )
        <= bound + 1e-9,
        "continuous_two_axis_motion": bool(parsed_x)
        and max(parsed_x) - min(parsed_x) >= 0.12
        and max(parsed_y) - min(parsed_y) >= 0.12,
        "direction_reversal": bool(parsed_x)
        and (
            direction_reversals(parsed_x) >= 1
            or direction_reversals(parsed_y) >= 1
        ),
        "jump_disabled": program.get("jump_enabled") is False,
        "no_live_reads": all(
            program.get(name) is False
            for name in (
                "reads_live_enemy_state",
                "reads_live_player_state",
                "reads_camera",
                "reads_crosshair",
            )
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_v8_player_movement_program_contract_failed",
            capture.canonical_json(checks),
        )


def fire_program_active(program: dict[str, Any], out_tick: int) -> int:
    return int(
        any(
            int(window["start_output_tick"])
            <= out_tick
            < int(window["start_output_tick"])
            + int(window["duration_ticks"])
            for window in program["windows"]
        )
    )


def humanized_aim_motor_profile(
    seed: int, style: str | None = None
) -> AimMotorProfile:
    """Create a deterministic, manifest-frozen human aim motor profile."""
    if not 0 < int(seed) < 2**31:
        raise capture.CaptureFailure(
            "stage2_aim_motor_seed_invalid", str(seed)
        )
    rng = random.Random(int(seed))
    if style is None:
        draw = rng.random()
        style = (
            "direct_smooth"
            if draw < 0.35
            else (
                "overshoot_correct"
                if draw < 0.75
                else "undershoot_correct"
            )
        )
    if style not in AIM_MOTOR_STYLES:
        raise capture.CaptureFailure(
            "stage2_aim_motor_style_unknown", str(style)
        )
    knot_ticks = [0, 40, 80, 120, 160, 200, 240, 280, 319]
    yaw_knots = [0.0] + [
        round(rng.uniform(-0.55, 0.55), 6)
        for _ in knot_ticks[1:]
    ]
    pitch_knots = [0.0] + [
        round(rng.uniform(-0.35, 0.35), 6)
        for _ in knot_ticks[1:]
    ]
    if style == "direct_smooth":
        yaw_offset = pitch_offset = 0.0
        damping_yaw = rng.uniform(0.58, 0.72)
        damping_pitch = rng.uniform(0.55, 0.70)
    else:
        yaw_offset = rng.uniform(1.4, 3.2)
        pitch_offset = rng.uniform(-0.8, 0.8)
        if style == "overshoot_correct":
            damping_yaw = rng.uniform(0.30, 0.43)
            damping_pitch = rng.uniform(0.32, 0.46)
        else:
            damping_yaw = rng.uniform(0.58, 0.75)
            damping_pitch = rng.uniform(0.56, 0.73)
    profile: AimMotorProfile = {
        "schema_version": AIM_MOTOR_PROFILE_SCHEMA,
        "algorithm": "bounded_second_order_open_loop_v1",
        "seed": int(seed),
        "style": style,
        "max_yaw_speed_deg_per_tick": round(
            rng.uniform(1.5, 2.6), 6
        ),
        "max_pitch_speed_deg_per_tick": round(
            rng.uniform(0.9, 1.7), 6
        ),
        "max_yaw_accel_deg_per_tick2": round(
            rng.uniform(0.10, 0.22), 6
        ),
        "max_pitch_accel_deg_per_tick2": round(
            rng.uniform(0.07, 0.16), 6
        ),
        "proportional_gain_yaw": round(
            rng.uniform(0.10, 0.17), 6
        ),
        "proportional_gain_pitch": round(
            rng.uniform(0.10, 0.18), 6
        ),
        "damping_gain_yaw": round(damping_yaw, 6),
        "damping_gain_pitch": round(damping_pitch, 6),
        "tracking_lag_ticks": rng.randint(2, 6),
        "acquisition_offset_yaw_deg": round(yaw_offset, 6),
        "acquisition_offset_pitch_deg": round(pitch_offset, 6),
        "correction_duration_ticks": rng.randint(18, 34),
        "residual_bias_yaw_deg": round(
            rng.uniform(-0.45, 0.45), 6
        ),
        "residual_bias_pitch_deg": round(
            rng.uniform(-0.28, 0.28), 6
        ),
        "micro_correction_knot_ticks": knot_ticks,
        "micro_correction_yaw_deg": yaw_knots,
        "micro_correction_pitch_deg": pitch_knots,
        "exact_lock_error_threshold_deg": 0.1,
        "maximum_exact_lock_fraction": 0.15,
        "reads_live_enemy_state": False,
        "reads_live_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
    }
    validate_aim_motor_profile(profile)
    return profile


def validate_aim_motor_profile(profile: AimMotorProfile) -> None:
    expected_fields = {
        "schema_version",
        "algorithm",
        "seed",
        "style",
        "max_yaw_speed_deg_per_tick",
        "max_pitch_speed_deg_per_tick",
        "max_yaw_accel_deg_per_tick2",
        "max_pitch_accel_deg_per_tick2",
        "proportional_gain_yaw",
        "proportional_gain_pitch",
        "damping_gain_yaw",
        "damping_gain_pitch",
        "tracking_lag_ticks",
        "acquisition_offset_yaw_deg",
        "acquisition_offset_pitch_deg",
        "correction_duration_ticks",
        "residual_bias_yaw_deg",
        "residual_bias_pitch_deg",
        "micro_correction_knot_ticks",
        "micro_correction_yaw_deg",
        "micro_correction_pitch_deg",
        "exact_lock_error_threshold_deg",
        "maximum_exact_lock_fraction",
        "reads_live_enemy_state",
        "reads_live_player_state",
        "reads_camera",
        "reads_crosshair",
    }
    ticks = profile.get("micro_correction_knot_ticks") or []
    yaw = profile.get("micro_correction_yaw_deg") or []
    pitch = profile.get("micro_correction_pitch_deg") or []
    finite_names = (
        "max_yaw_speed_deg_per_tick",
        "max_pitch_speed_deg_per_tick",
        "max_yaw_accel_deg_per_tick2",
        "max_pitch_accel_deg_per_tick2",
        "proportional_gain_yaw",
        "proportional_gain_pitch",
        "damping_gain_yaw",
        "damping_gain_pitch",
        "acquisition_offset_yaw_deg",
        "acquisition_offset_pitch_deg",
        "residual_bias_yaw_deg",
        "residual_bias_pitch_deg",
        "exact_lock_error_threshold_deg",
        "maximum_exact_lock_fraction",
    )
    finite = {
        name: float(profile.get(name, math.nan))
        for name in finite_names
    }
    checks = {
        "mapping": isinstance(profile, dict),
        "exact_fields": set(profile) == expected_fields,
        "schema": profile.get("schema_version")
        == AIM_MOTOR_PROFILE_SCHEMA,
        "algorithm": profile.get("algorithm")
        == "bounded_second_order_open_loop_v1",
        "style": profile.get("style") in AIM_MOTOR_STYLES,
        "seed": isinstance(profile.get("seed"), int)
        and 0 < int(profile["seed"]) < 2**31,
        "finite": all(math.isfinite(value) for value in finite.values()),
        "speed": 0.25
        <= finite["max_yaw_speed_deg_per_tick"]
        <= capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
        and 0.25
        <= finite["max_pitch_speed_deg_per_tick"]
        <= capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK,
        "acceleration": 0.01
        <= finite["max_yaw_accel_deg_per_tick2"]
        <= 2.0
        and 0.01
        <= finite["max_pitch_accel_deg_per_tick2"]
        <= 2.0,
        "controller_gains": 0.01
        <= finite["proportional_gain_yaw"]
        <= 1.0
        and 0.01
        <= finite["proportional_gain_pitch"]
        <= 1.0
        and 0.01 <= finite["damping_gain_yaw"] <= 2.0
        and 0.01 <= finite["damping_gain_pitch"] <= 2.0,
        "lag": isinstance(profile.get("tracking_lag_ticks"), int)
        and 0 <= int(profile["tracking_lag_ticks"]) <= 12,
        "correction": isinstance(
            profile.get("correction_duration_ticks"), int
        )
        and 1 <= int(profile["correction_duration_ticks"]) <= 64,
        "knots": (
            isinstance(ticks, list)
            and isinstance(yaw, list)
            and isinstance(pitch, list)
            and len(ticks) == len(yaw) == len(pitch) >= 4
            and ticks[0] == 0
            and ticks[-1] == capture.OUTPUT_TICKS - 1
            and all(
                isinstance(value, int)
                and 0 <= value < capture.OUTPUT_TICKS
                for value in ticks
            )
            and ticks == sorted(set(ticks))
            and all(
                math.isfinite(float(value)) and abs(float(value)) <= 1.25
                for value in yaw
            )
            and all(
                math.isfinite(float(value)) and abs(float(value)) <= 0.8
                for value in pitch
            )
        ),
        "lock_gate": (
            math.isclose(
                finite["exact_lock_error_threshold_deg"],
                0.1,
                abs_tol=1e-9,
            )
            and 0.05
            <= finite["maximum_exact_lock_fraction"]
            <= 0.25
        ),
        "no_live_reads": all(
            profile.get(name) is False
            for name in (
                "reads_live_enemy_state",
                "reads_live_player_state",
                "reads_camera",
                "reads_crosshair",
            )
        ),
        "style_offset": (
            (
                profile.get("style") == "direct_smooth"
                and abs(finite["acquisition_offset_yaw_deg"]) < 1e-9
                and abs(finite["acquisition_offset_pitch_deg"]) < 1e-9
            )
            or (
                profile.get("style")
                in {"overshoot_correct", "undershoot_correct"}
                and 1.0
                <= abs(finite["acquisition_offset_yaw_deg"])
                <= 4.0
                and abs(
                    finite["acquisition_offset_pitch_deg"]
                )
                <= 1.5
            )
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_aim_motor_profile_contract_failed",
            capture.canonical_json(checks),
        )


def validate_aim_schedule(
    policy: str, schedule: dict[str, Any]
) -> None:
    """Fail closed on malformed or silently changed v3 timing windows."""
    expected_keys = set(default_aim_schedule(policy))
    checks = {
        "mapping": isinstance(schedule, dict),
        "schema": schedule.get("schema_version")
        == AIM_SCHEDULE_SCHEMA,
        "policy": schedule.get("policy") == policy,
        "exact_fields": set(schedule) == expected_keys,
    }
    ordered_tick_fields = {
        "visible_no_response": ("response_start_output_tick",),
        "delayed_acquisition": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
        ),
        "pass_offset": (
            "response_start_output_tick",
            "pass_end_output_tick",
            "depart_end_output_tick",
        ),
        "track_loss_reacquire": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
            "centered_hold_end_output_tick",
            "loss_end_output_tick",
            "lost_hold_end_output_tick",
            "reacquisition_end_output_tick",
        ),
        "sustained_tracking": (
            "response_start_output_tick",
            "acquisition_end_output_tick",
        ),
    }[policy]
    numeric_values = [
        schedule.get(name)
        for name in ordered_tick_fields
        if schedule.get(name) is not None
    ]
    checks["tick_values"] = all(
        isinstance(value, int)
        and 0 <= value < capture.OUTPUT_TICKS
        for value in numeric_values
    )
    checks["tick_order"] = numeric_values == sorted(numeric_values)
    if policy == "sustained_tracking":
        checks["tracking_thresholds"] = (
            isinstance(
                schedule.get("minimum_visible_tracking_frames"), int
            )
            and 1
            <= int(schedule["minimum_visible_tracking_frames"])
            <= capture.OUTPUT_TICKS
            and 0.0
            < float(
                schedule[
                    "minimum_centered_given_visible_fraction"
                ]
            )
            <= 1.0
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_aim_schedule_contract_failed",
            capture.canonical_json(checks),
        )


def shot_error_schedule(
    program: str,
    *,
    yaw_offset_deg: float = 0.0,
    pitch_offset_deg: float = 0.0,
    start_output_tick: int | None = None,
    peak_output_tick: int | None = None,
    hold_end_output_tick: int | None = None,
    return_end_output_tick: int | None = None,
    minimum_error_at_fire_deg: float = 0.0,
    expected_center_before_first_fire: bool | None = None,
    expected_acquisition_after_first_fire: bool | None = None,
) -> dict[str, Any]:
    """Build one explicit, manifest-frozen shot-error treatment.

    The program is a candidate-generation arm, never an outcome label.
    Authoritative telemetry still decides miss, damage, and death.
    """
    schedule = {
        "schema_version": SHOT_ERROR_SCHEDULE_SCHEMA,
        "program": program,
        "yaw_offset_deg": float(yaw_offset_deg),
        "pitch_offset_deg": float(pitch_offset_deg),
        "start_output_tick": start_output_tick,
        "peak_output_tick": peak_output_tick,
        "hold_end_output_tick": hold_end_output_tick,
        "return_end_output_tick": return_end_output_tick,
        "minimum_error_at_fire_deg": float(
            minimum_error_at_fire_deg
        ),
        "expected_center_before_first_fire": (
            expected_center_before_first_fire
        ),
        "expected_acquisition_after_first_fire": (
            expected_acquisition_after_first_fire
        ),
    }
    validate_shot_error_schedule(schedule)
    return schedule


def validate_shot_error_schedule(
    schedule: dict[str, Any],
    *,
    policy: str | None = None,
) -> None:
    expected_fields = {
        "schema_version",
        "program",
        "yaw_offset_deg",
        "pitch_offset_deg",
        "start_output_tick",
        "peak_output_tick",
        "hold_end_output_tick",
        "return_end_output_tick",
        "minimum_error_at_fire_deg",
        "expected_center_before_first_fire",
        "expected_acquisition_after_first_fire",
    }
    program = str(schedule.get("program", ""))
    yaw = float(schedule.get("yaw_offset_deg", math.nan))
    pitch = float(schedule.get("pitch_offset_deg", math.nan))
    minimum = float(
        schedule.get("minimum_error_at_fire_deg", math.nan)
    )
    tick_names = (
        "start_output_tick",
        "peak_output_tick",
        "hold_end_output_tick",
        "return_end_output_tick",
    )
    ticks = [schedule.get(name) for name in tick_names]
    optional_booleans = (
        schedule.get("expected_center_before_first_fire"),
        schedule.get("expected_acquisition_after_first_fire"),
    )
    checks = {
        "mapping": isinstance(schedule, dict),
        "schema": schedule.get("schema_version")
        == SHOT_ERROR_SCHEDULE_SCHEMA,
        "exact_fields": set(schedule) == expected_fields,
        "program": program in SHOT_ERROR_PROGRAMS,
        "policy": (
            policy is None
            or (
                program in SHOT_ERROR_PROGRAM_POLICIES
                and policy in SHOT_ERROR_PROGRAM_POLICIES[program]
            )
        ),
        "finite_offsets": math.isfinite(yaw)
        and math.isfinite(pitch)
        and abs(yaw) <= 45.0
        and abs(pitch) <= 30.0,
        "minimum_error": math.isfinite(minimum)
        and 0.0 <= minimum <= 90.0,
        "ticks": all(
            value is None
            or (
                isinstance(value, int)
                and 0 <= value < capture.OUTPUT_TICKS
            )
            for value in ticks
        ),
        "optional_booleans": all(
            value is None or isinstance(value, bool)
            for value in optional_booleans
        ),
    }
    if program == "none":
        checks["shape"] = (
            all(value is None for value in ticks)
            and abs(yaw) <= 1e-12
            and abs(pitch) <= 1e-12
            and minimum == 0.0
            and all(value is None for value in optional_booleans)
        )
    elif program == "spatial_persistent":
        checks["shape"] = (
            isinstance(ticks[0], int)
            and isinstance(ticks[1], int)
            and int(ticks[0]) < int(ticks[1])
            and ticks[2] is None
            and ticks[3] is None
            and math.hypot(yaw, pitch) >= minimum >= 3.0
            and schedule.get("expected_center_before_first_fire")
            is False
        )
    elif program in {
        "spatial_transient",
        "spatial_undershoot_then_acquire",
    }:
        checks["shape"] = (
            all(isinstance(value, int) for value in ticks)
            and [int(value) for value in ticks]
            == sorted(int(value) for value in ticks)
            and int(ticks[0]) < int(ticks[1])
            and int(ticks[1]) <= int(ticks[2])
            and int(ticks[2]) < int(ticks[3])
            and math.hypot(yaw, pitch) >= minimum >= 3.0
            and schedule.get("expected_center_before_first_fire")
            is (
                False
                if program == "spatial_undershoot_then_acquire"
                else True
            )
            and schedule.get(
                "expected_acquisition_after_first_fire"
            )
            is (
                True
                if program == "spatial_undershoot_then_acquire"
                else None
            )
        )
    else:
        expected_after = (
            True if program == "timing_early_acquisition" else None
        )
        expected_before = (
            False
            if program == "timing_early_acquisition"
            else True
        )
        checks["shape"] = (
            all(value is None for value in ticks)
            and abs(yaw) <= 1e-12
            and abs(pitch) <= 1e-12
            and minimum >= 3.0
            and schedule.get("expected_center_before_first_fire")
            is expected_before
            and schedule.get(
                "expected_acquisition_after_first_fire"
            )
            is expected_after
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_shot_error_schedule_contract_failed",
            capture.canonical_json(checks),
        )


def shot_error_offsets(
    schedule: dict[str, Any], out_tick: int
) -> tuple[float, float]:
    """Return the declared additive view error for one output tick."""
    program = str(schedule["program"])
    if program not in {
        "spatial_persistent",
        "spatial_transient",
        "spatial_undershoot_then_acquire",
    }:
        return 0.0, 0.0
    start = int(schedule["start_output_tick"])
    peak = int(schedule["peak_output_tick"])
    if out_tick <= start:
        scale = 0.0
    elif out_tick < peak:
        scale = _smoothstep((out_tick - start) / (peak - start))
    elif program == "spatial_persistent":
        scale = 1.0
    else:
        hold_end = int(schedule["hold_end_output_tick"])
        return_end = int(schedule["return_end_output_tick"])
        if out_tick <= hold_end:
            scale = 1.0
        elif out_tick < return_end:
            scale = 1.0 - _smoothstep(
                (out_tick - hold_end) / (return_end - hold_end)
            )
        else:
            scale = 0.0
    return (
        float(schedule["yaw_offset_deg"]) * scale,
        float(schedule["pitch_offset_deg"]) * scale,
    )


def exogenous_contract_payload(scenario: dict[str, Any]) -> dict[str, Any]:
    """Fields that must remain invariant inside a counterfactual group."""
    payload = {
        "schema_version": EXOGENOUS_SCHEMA,
        "counterfactual_group_id": scenario.get(
            "counterfactual_group_id"
        ),
        "map": scenario.get("map"),
        "gametype": scenario.get("gametype"),
        "seed": scenario.get("seed"),
        "anchor_id": scenario.get("anchor_id"),
        "player": scenario.get("player"),
        "enemy": scenario.get("enemy"),
        "enemy_model": scenario.get("enemy_model"),
        "enemy_skin": scenario.get("enemy_skin"),
        "enemy_color": scenario.get("enemy_color"),
        "enemy_policy": scenario.get("enemy_policy"),
        "weapon": scenario.get("weapon"),
        "weapon_netname": scenario.get("weapon_netname"),
        "base_player_program": (
            (scenario.get("causal_design") or {}).get(
                "base_player_program"
            )
        ),
        "encounter_source": scenario.get("encounter_source"),
    }
    if scenario.get("schema_version") in {
        SCENARIO_SCHEMA_V2,
        SCENARIO_SCHEMA_V3,
        SCENARIO_SCHEMA_V4,
        SCENARIO_SCHEMA_V5,
        SCENARIO_SCHEMA_V6,
        SCENARIO_SCHEMA_V7,
        SCENARIO_SCHEMA_V8,
        SCENARIO_SCHEMA_V9,
    }:
        design = scenario.get("causal_design") or {}
        payload.update(
            {
                "schema_version": (
                    EXOGENOUS_SCHEMA_V9
                    if scenario.get("schema_version")
                    == SCENARIO_SCHEMA_V9
                    else (
                        EXOGENOUS_SCHEMA_V8
                        if scenario.get("schema_version")
                        == SCENARIO_SCHEMA_V8
                        else (
                            EXOGENOUS_SCHEMA_V7
                            if scenario.get("schema_version")
                            == SCENARIO_SCHEMA_V7
                            else (
                                EXOGENOUS_SCHEMA_V6
                                if scenario.get("schema_version")
                                == SCENARIO_SCHEMA_V6
                                else (
                                    EXOGENOUS_SCHEMA_V5
                                    if scenario.get("schema_version")
                                    == SCENARIO_SCHEMA_V5
                                    else (
                                        EXOGENOUS_SCHEMA_V4
                                        if scenario.get(
                                            "schema_version"
                                        )
                                        == SCENARIO_SCHEMA_V4
                                        else (
                                            EXOGENOUS_SCHEMA_V3
                                            if scenario.get(
                                                "schema_version"
                                            )
                                            == SCENARIO_SCHEMA_V3
                                            else EXOGENOUS_SCHEMA_V2
                                        )
                                    )
                                )
                            )
                        )
                    )
                ),
                "interaction_channel": design.get(
                    "interaction_channel"
                ),
                "secondary_mechanism": design.get(
                    "secondary_mechanism"
                ),
                "player_path_source": scenario.get(
                    "player_path_source"
                ),
            }
        )
        if scenario.get("schema_version") in {
            SCENARIO_SCHEMA_V3,
            SCENARIO_SCHEMA_V4,
            SCENARIO_SCHEMA_V5,
            SCENARIO_SCHEMA_V6,
            SCENARIO_SCHEMA_V7,
            SCENARIO_SCHEMA_V8,
            SCENARIO_SCHEMA_V9,
        }:
            if "base_view_yaw_offset_deg" in design:
                payload["base_view_yaw_offset_deg"] = design.get(
                    "base_view_yaw_offset_deg"
                )
                payload["base_view_pitch_offset_deg"] = design.get(
                    "base_view_pitch_offset_deg"
                )
            if scenario.get("encounter_certificate"):
                payload["encounter_certificate"] = scenario.get(
                    "encounter_certificate"
                )
        if scenario.get("schema_version") in {
            SCENARIO_SCHEMA_V4,
            SCENARIO_SCHEMA_V5,
            SCENARIO_SCHEMA_V6,
            SCENARIO_SCHEMA_V7,
            SCENARIO_SCHEMA_V8,
            SCENARIO_SCHEMA_V9,
        }:
            payload["initial_screen_design"] = scenario.get(
                "initial_screen_design"
            )
        if scenario.get("schema_version") == SCENARIO_SCHEMA_V8:
            payload["player_movement_program"] = design.get(
                "player_movement_program"
            )
            if "player_health_policy" in design:
                payload["player_health_policy"] = design.get(
                    "player_health_policy"
                )
        if scenario.get("schema_version") == SCENARIO_SCHEMA_V9:
            payload["prefrozen_trace_source"] = scenario.get(
                "prefrozen_trace_source"
            )
            if "player_health_policy" in design:
                payload["player_health_policy"] = design.get(
                    "player_health_policy"
                )
    return payload


def exogenous_contract_sha256(scenario: dict[str, Any]) -> str:
    payload = exogenous_contract_payload(scenario)
    return hashlib.sha256(
        capture.canonical_json(payload).encode("utf-8")
    ).hexdigest()


def encounter_contract_payload(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Return policy-independent geometry/mechanism fields for certification."""
    design = scenario.get("causal_design") or {}
    source = scenario.get("player_path_source") or {}
    return {
        "schema_version": "xonotic-stage2-encounter-contract-v1",
        "source_commit_required": scenario.get(
            "source_commit_required"
        ),
        "map": scenario.get("map"),
        "gametype": scenario.get("gametype"),
        "seed": scenario.get("seed"),
        "player": scenario.get("player"),
        "enemy": scenario.get("enemy"),
        "enemy_model": scenario.get("enemy_model"),
        "enemy_skin": scenario.get("enemy_skin"),
        "enemy_color": scenario.get("enemy_color"),
        "enemy_policy": scenario.get("enemy_policy"),
        "weapon": scenario.get("weapon"),
        "weapon_netname": scenario.get("weapon_netname"),
        "base_player_program": design.get("base_player_program"),
        "player_motion_class": design.get("player_motion_class"),
        "base_view_yaw_offset_deg": design.get(
            "base_view_yaw_offset_deg", 0.0
        ),
        "base_view_pitch_offset_deg": design.get(
            "base_view_pitch_offset_deg", 0.0
        ),
        "player_path_source_schema": source.get("schema_version"),
        "route_id": source.get("route_id"),
        "route_record_sha256": source.get("route_record_sha256"),
        "route_plan_contract_sha256": source.get(
            "route_plan_contract_sha256"
        ),
        "actions_sha256": source.get("actions_sha256"),
        "states_sha256": source.get("states_sha256"),
        "enemy_clearance": {
            "metric": source.get("player_enemy_clearance_metric"),
            "threshold": source.get(
                "player_enemy_clearance_threshold"
            ),
            "minimum": source.get(
                "minimum_player_enemy_clearance"
            ),
            "minimum_server_tick": source.get(
                "minimum_player_enemy_clearance_server_tick"
            ),
        },
    }


def encounter_contract_sha256(scenario: dict[str, Any]) -> str:
    return hashlib.sha256(
        capture.canonical_json(
            encounter_contract_payload(scenario)
        ).encode("utf-8")
    ).hexdigest()


@functools.lru_cache(maxsize=128)
def _locked_encounter_certificate(
    index_path_raw: str,
    index_sha256: str,
    certificate_id: str,
) -> dict[str, Any]:
    index_path = capture.locked_root_artifact(
        index_path_raw,
        index_sha256,
        "stage2_encounter_certificate_index",
    )
    matches = [
        row
        for row in capture.load_jsonl(index_path)
        if row.get("certificate_id") == certificate_id
    ]
    if len(matches) != 1:
        raise capture.CaptureFailure(
            "stage2_encounter_certificate_missing",
            f"certificate_id={certificate_id} count={len(matches)}",
        )
    return matches[0]


def validate_encounter_certificate(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    reference = scenario.get("encounter_certificate") or {}
    record = _locked_encounter_certificate(
        str(reference.get("index_path", "")),
        str(reference.get("index_sha256", "")),
        str(reference.get("certificate_id", "")),
    )
    record_hash = hashlib.sha256(
        capture.canonical_json(record).encode("utf-8")
    ).hexdigest()
    checks = {
        "schema": record.get("schema_version")
        == ENCOUNTER_CERTIFICATE_SCHEMA,
        "record_hash": reference.get("record_sha256")
        == record_hash,
        "passed": record.get("passed") is True,
        "encounter_hash": (
            record.get("encounter_contract_sha256")
            == encounter_contract_sha256(scenario)
        ),
        "route": record.get("route_id")
        == (scenario.get("player_path_source") or {}).get(
            "route_id"
        ),
        "source_commit": record.get("source_commit")
        == scenario.get("source_commit_required"),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_encounter_certificate_contract_failed",
            capture.canonical_json(checks),
        )
    return record


def validate_initial_screen_design(design: dict[str, Any]) -> None:
    expected_fields = {
        "schema_version",
        "screen_horizontal",
        "screen_vertical",
        "view_yaw_offset_deg",
        "view_pitch_offset_deg",
        "expected_visible_at_output_start",
    }
    horizontal = str(design.get("screen_horizontal", ""))
    vertical = str(design.get("screen_vertical", ""))
    yaw = float(design.get("view_yaw_offset_deg", math.nan))
    pitch = float(design.get("view_pitch_offset_deg", math.nan))
    horizontal_geometry = {
        "left": yaw <= -5.0,
        "center": abs(yaw) <= 3.0,
        "right": yaw >= 5.0,
    }.get(horizontal, False)
    vertical_geometry = {
        "upper": pitch >= 3.0,
        "center": abs(pitch) <= 2.0,
        "lower": pitch <= -3.0,
    }.get(vertical, False)
    checks = {
        "mapping": isinstance(design, dict),
        "schema": design.get("schema_version")
        == INITIAL_SCREEN_DESIGN_SCHEMA,
        "exact_fields": set(design) == expected_fields,
        "horizontal": horizontal
        in {"left", "center", "right"},
        "vertical": vertical in {"upper", "center", "lower"},
        "finite_offsets": math.isfinite(yaw)
        and math.isfinite(pitch)
        and abs(yaw) <= 45.0
        and abs(pitch) <= 30.0,
        "horizontal_geometry": horizontal_geometry,
        "vertical_geometry": vertical_geometry,
        "visible_boolean": isinstance(
            design.get("expected_visible_at_output_start"), bool
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_initial_screen_design_contract_failed",
            capture.canonical_json(checks),
        )


def validate_scenario_contract(scenario: dict[str, Any]) -> None:
    design = scenario.get("causal_design") or {}
    is_v1 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA
        and scenario.get("action_program") == ACTION_PROGRAM
    )
    is_v2 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V2
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V2
        and scenario.get("action_program") == ACTION_PROGRAM_V2
    )
    is_v3 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V3
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V3
        and scenario.get("action_program") == ACTION_PROGRAM_V3
    )
    is_v4 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V4
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V4
        and scenario.get("action_program") == ACTION_PROGRAM_V4
    )
    is_v5 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V5
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V5
        and scenario.get("action_program") == ACTION_PROGRAM_V5
    )
    is_v6 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V6
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V6
        and scenario.get("action_program") == ACTION_PROGRAM_V6
    )
    is_v7 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V7
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V7
        and scenario.get("action_program") == ACTION_PROGRAM_V7
    )
    is_v8 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V8
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V8
        and scenario.get("action_program") == ACTION_PROGRAM_V8
    )
    is_v9 = (
        scenario.get("schema_version") == SCENARIO_SCHEMA_V9
        and design.get("schema_version") == CAUSAL_DESIGN_SCHEMA_V9
        and scenario.get("action_program") == ACTION_PROGRAM_V9
    )
    channel = str(design.get("interaction_channel", ""))
    weapon = str(scenario.get("weapon", ""))
    secondary_contract = (
        channel != "secondary"
        or (
            weapon in SECONDARY_MECHANISMS
            and design.get("secondary_mechanism")
            == SECONDARY_MECHANISMS[weapon]
        )
    )
    player_program = str(design.get("base_player_program", ""))
    player_program_contract = (
        player_program == "stationary"
        or (
            (is_v2 or is_v3 or is_v4 or is_v5 or is_v6)
            and player_program == "certified_route_replay"
            and bool(scenario.get("player_path_source"))
        )
        or (
            is_v8
            and player_program
            == "manifest_frozen_continuous_movement"
            and bool(design.get("player_movement_program"))
        )
        or (
            is_v9
            and player_program
            == "certified_prefrozen_trace_replay"
            and bool(scenario.get("prefrozen_trace_source"))
        )
    )
    checks = {
        "version_tuple": (
            is_v1
            or is_v2
            or is_v3
            or is_v4
            or is_v5
            or is_v6
            or is_v7
            or is_v8
            or is_v9
        ),
        "dataset_role": scenario.get("dataset_role")
        == "causal_interaction",
        "enemy_present": scenario.get("enemy_present") is True,
        "policy": (
            design.get("aim_policy")
            in WEAPON_BALANCED_AIM_ARMS
            if is_v9
            else (
            design.get("aim_policy") == STOCHASTIC_AIM_POLICY
            if is_v7 or is_v8
            else design.get("aim_policy") in AIM_POLICIES
            )
        ),
        "interaction_channel": (
            channel == "primary"
            if is_v1 or is_v7 or is_v8 or is_v9
            else channel in INTERACTION_CHANNELS
        ),
        "secondary_mechanism": secondary_contract,
        "weapon_mechanism_mode": (
            design.get("aim_policy") not in FIRING_POLICIES
            or (scenario.get("encounter_source") or {}).get(
                "weapon_mechanism_mode_eligible"
            )
            is True
        ),
        "player_program": player_program_contract,
        "no_live_target_reads": (
            design.get("aim_reference")
            == (
                (
                    "manifest_frozen_analytic_enemy_and_player_"
                    "trajectories"
                )
                if is_v9
                else (
                    "manifest_frozen_random_view_program"
                    if is_v7 or is_v8
                    else "manifest_frozen_analytic_enemy_trajectory"
                )
            )
            and design.get("reads_live_enemy_state") is False
            and design.get("reads_live_player_state") is False
            and design.get("reads_camera") is False
            and design.get("reads_crosshair") is False
        ),
        "counterfactual_group": bool(
            scenario.get("counterfactual_group_id")
        ),
        "exogenous_hash": scenario.get(
            "exogenous_contract_sha256"
        )
        == exogenous_contract_sha256(scenario),
        "actual_outcome_not_acceptance_label": (
            (scenario.get("acceptance") or {}).get("actual_outcome")
            is None
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_causal_scenario_contract_failed",
            capture.canonical_json(checks),
        )
    if is_v7 or is_v8:
        validate_random_aim_program(
            design.get("random_aim_program") or {}
        )
        if is_v8:
            validate_player_movement_program(
                design.get("player_movement_program") or {}
            )
        validate_fire_program(
            design.get("fire_program") or {},
            policy=STOCHASTIC_AIM_POLICY,
            design=design,
        )
        aim_seed = (design.get("random_aim_program") or {}).get(
            "seed"
        )
        fire_seed = design.get("fire_seed")
        movement_seed = (
            (design.get("player_movement_program") or {}).get(
                "seed"
            )
            if is_v8
            else None
        )
        enemy_policy = scenario.get("enemy_policy") or {}
        enemy = scenario.get("enemy") or {}
        v7_checks = {
            "player_program": (
                player_program
                == "manifest_frozen_continuous_movement"
                if is_v8
                else player_program == "stationary"
            ),
            "primary_only": channel == "primary"
            and design.get("secondary_mechanism") is None,
            "independent_fire_seed": isinstance(fire_seed, int)
            and not isinstance(fire_seed, bool)
            and 0 < int(fire_seed) < 2**31
            and int(fire_seed) != int(aim_seed),
            "independent_movement_seed": (
                isinstance(movement_seed, int)
                and not isinstance(movement_seed, bool)
                and 0 < int(movement_seed) < 2**24
                and len(
                    {
                        int(movement_seed),
                        int(aim_seed),
                        int(fire_seed),
                        int(enemy_policy.get("policy_seed", -1)),
                    }
                )
                == 4
                if is_v8
                else movement_seed is None
            ),
            "player_health_policy": (
                design.get(
                    "player_health_policy", "not_reduced"
                )
                in {"not_reduced", "player_alive"}
                if is_v8
                else "player_health_policy" not in design
            ),
            "player_health_acceptance": (
                (
                    (scenario.get("acceptance") or {}).get(
                        "player_self_damage_allowed"
                    )
                    is True
                    and (scenario.get("acceptance") or {}).get(
                        "player_death_allowed"
                    )
                    is False
                )
                if is_v8
                and design.get("player_health_policy")
                == "player_alive"
                else True
            ),
            "enemy_random_motion_mode": int(enemy.get("motion", -1))
            == 4,
            "enemy_random_policy": enemy_policy.get("name")
            == "seeded_piecewise_smooth_wander_v1",
            "enemy_exogenous": (
                enemy_policy.get("closed_loop_decisions") is False
                and enemy_policy.get("reads_camera") is False
                and enemy_policy.get("reads_crosshair") is False
                and enemy_policy.get("runtime_reads_player_state")
                is False
                and enemy_policy.get("fires") is False
                and enemy_policy.get("jumps") is True
            ),
            "fire_required": (
                (scenario.get("acceptance") or {}).get(
                    "fire_required"
                )
                is True
            ),
            "outcome_rebucket_only": (
                (scenario.get("acceptance") or {}).get(
                    "actual_outcome_rebucket_required"
                )
                is True
            ),
            "nontraining": scenario.get(
                "formal_collection_authorized"
            )
            is False
            and scenario.get("training_admitted") is False,
        }
        if not all(v7_checks.values()):
            raise capture.CaptureFailure(
                (
                    "stage2_v8_scenario_contract_failed"
                    if is_v8
                    else "stage2_v7_scenario_contract_failed"
                ),
                capture.canonical_json(v7_checks),
            )
    if is_v9:
        aim_program = design.get("weapon_balanced_aim_program") or {}
        validate_weapon_balanced_aim_program(aim_program)
        arm = str(design.get("aim_policy"))
        no_fire = arm == "visible_no_fire"
        validate_fire_program(
            design.get("fire_program") or {},
            policy=(
                "visible_no_response"
                if no_fire
                else STOCHASTIC_AIM_POLICY
            ),
            design=design,
        )
        fire_program = design["fire_program"]
        last_active = max(
            (
                int(window["start_output_tick"])
                + int(window["duration_ticks"])
                - 1
                for window in fire_program["windows"]
            ),
            default=-1,
        )
        aim_seed = int(aim_program["seed"])
        fire_seed = design.get("fire_seed")
        enemy_policy = scenario.get("enemy_policy") or {}
        enemy = scenario.get("enemy") or {}
        v9_checks = {
            "player_program": player_program
            == "certified_prefrozen_trace_replay",
            "trace_contract": bool(
                prefrozen_trace_artifacts(scenario)
            ),
            "primary_only": channel == "primary"
            and design.get("secondary_mechanism") is None,
            "independent_seeds": isinstance(fire_seed, int)
            and not isinstance(fire_seed, bool)
            and 0 < int(fire_seed) < 2**24
            and len(
                {
                    int(fire_seed),
                    aim_seed,
                    int(enemy_policy.get("policy_seed", -1)),
                }
            )
            == 3,
            "player_health_policy": design.get(
                "player_health_policy"
            )
            == "player_alive",
            "player_health_acceptance": (
                (scenario.get("acceptance") or {}).get(
                    "player_self_damage_allowed"
                )
                is True
                and (scenario.get("acceptance") or {}).get(
                    "player_death_allowed"
                )
                is False
            ),
            "enemy_random_motion_mode": int(enemy.get("motion", -1))
            == 4,
            "enemy_random_policy": enemy_policy.get("name")
            == "seeded_piecewise_smooth_wander_v1",
            "enemy_exogenous": (
                enemy_policy.get("closed_loop_decisions") is False
                and enemy_policy.get("reads_camera") is False
                and enemy_policy.get("reads_crosshair") is False
                and enemy_policy.get("runtime_reads_player_state")
                is False
                and enemy_policy.get("fires") is False
            ),
            "fire_requirement": (
                (scenario.get("acceptance") or {}).get(
                    "fire_required"
                )
                is (not no_fire)
            ),
            "no_fire_program": (
                fire_program["name"] == "none"
                if no_fire
                else fire_program["name"] != "none"
            ),
            "projectile_observation_window": (
                weapon not in PROJECTILE_PRIMARY_WEAPONS
                or no_fire
                or last_active <= LATEST_PROJECTILE_FIRE_OUTPUT_TICK
            ),
            "outcome_rebucket_only": (
                (scenario.get("acceptance") or {}).get(
                    "actual_outcome_rebucket_required"
                )
                is True
            ),
            "nontraining": scenario.get(
                "formal_collection_authorized"
            )
            is False
            and scenario.get("training_admitted") is False,
        }
        if not all(v9_checks.values()):
            raise capture.CaptureFailure(
                "stage2_v9_scenario_contract_failed",
                capture.canonical_json(v9_checks),
            )
    if is_v3 or is_v4 or is_v5 or is_v6:
        schedule = design.get("aim_schedule") or {}
        if is_v6:
            validate_aim_schedule_v6(
                str(design.get("aim_policy")),
                schedule,
            )
            validate_aim_motor_profile(
                design.get("aim_motor_profile") or {}
            )
            validate_fire_program(
                design.get("fire_program") or {},
                policy=str(design.get("aim_policy")),
                design=design,
            )
        elif is_v5:
            validate_aim_schedule_v5(
                str(design.get("aim_policy")),
                schedule,
            )
            validate_aim_motor_profile(
                design.get("aim_motor_profile") or {}
            )
        else:
            validate_aim_schedule(
                str(design.get("aim_policy")),
                schedule,
            )
        response_start = schedule.get(
            "response_start_output_tick"
        )
        fire_ticks = design.get("fire_output_ticks") or []
        timing_checks = {
            "acquisition_start_matches_schedule": int(
                design.get("acquisition_start_output_tick", -1)
            )
            == int(response_start or 0),
            "fire_ticks_in_output": all(
                isinstance(tick, int)
                and 0 <= tick < capture.OUTPUT_TICKS
                for tick in fire_ticks
            ),
            "no_response_has_no_fire": (
                str(design.get("aim_policy"))
                != "visible_no_response"
                or not fire_ticks
            ),
        }
        if not all(timing_checks.values()):
            raise capture.CaptureFailure(
                "stage2_v3_timing_contract_failed",
                capture.canonical_json(timing_checks),
            )
        view_offsets = {
            "yaw": float(
                design.get("base_view_yaw_offset_deg", 0.0)
            ),
            "pitch": float(
                design.get("base_view_pitch_offset_deg", 0.0)
            ),
        }
        if (
            not all(math.isfinite(value) for value in view_offsets.values())
            or abs(view_offsets["yaw"]) > 180.0
            or abs(view_offsets["pitch"]) > 89.0
        ):
            raise capture.CaptureFailure(
                "stage2_v3_base_view_offset_invalid",
                capture.canonical_json(view_offsets),
            )
        if is_v4 or is_v5 or is_v6:
            shot_schedule = design.get("shot_error_schedule") or {}
            validate_shot_error_schedule(
                shot_schedule,
                policy=str(design.get("aim_policy")),
            )
            validate_initial_screen_design(
                scenario.get("initial_screen_design") or {}
            )
            firing = str(design.get("aim_policy")) in FIRING_POLICIES
            shot_program = str(shot_schedule.get("program"))
            shot_checks = {
                "no_response_has_no_shot_error": (
                    firing or shot_program == "none"
                ),
                "error_program_has_fire": (
                    shot_program == "none" or bool(fire_ticks)
                ),
                "candidate_generation_only": (
                    design.get("shot_error_is_outcome_label")
                    is False
                ),
            }
            if not all(shot_checks.values()):
                raise capture.CaptureFailure(
                    "stage2_v4_shot_error_contract_failed",
                    capture.canonical_json(shot_checks),
                )
        if is_v5 or is_v6:
            policy = str(design.get("aim_policy"))
            natural_loss_checks = {
                "track_loss_requires_exogenous_change": (
                    policy != "track_loss_reacquire"
                    or int((scenario.get("enemy") or {}).get("motion", 0))
                    != 0
                    or bool(
                        design.get(
                            "certified_occlusion_driven_track_loss",
                            False,
                        )
                    )
                ),
                "no_delayed_post_lock_transient": (
                    policy != "delayed_acquisition"
                    or str(shot_schedule.get("program"))
                    != "spatial_transient"
                ),
                "humanized_open_loop_only": (
                    design.get("aim_motor_profile", {}).get(
                        "algorithm"
                    )
                    == "bounded_second_order_open_loop_v1"
                ),
                "v6_fire_program_present": (
                    not is_v6
                    or design.get("fire_program", {}).get(
                        "schema_version"
                    )
                    == FIRE_PROGRAM_SCHEMA
                ),
                "v6_primary_fire_only": (
                    not is_v6 or channel == "primary"
                ),
            }
            if not all(natural_loss_checks.values()):
                raise capture.CaptureFailure(
                    "stage2_v5_natural_interaction_contract_failed",
                    capture.canonical_json(natural_loss_checks),
                )
        if (
            player_program == "certified_route_replay"
            and (scenario.get("player_path_source") or {}).get(
                "schema_version"
            )
            not in {
                PLAYER_PATH_SOURCE_SCHEMA_V2,
                PLAYER_PATH_SOURCE_SCHEMA_V3,
                PLAYER_PATH_SOURCE_SCHEMA_V4,
            }
        ):
            raise capture.CaptureFailure(
                "stage2_v3_player_path_source_required",
                str(
                    (scenario.get("player_path_source") or {}).get(
                        "schema_version"
                    )
                ),
            )
    if player_program == "certified_route_replay":
        player_path_artifacts(scenario)
    if scenario.get("encounter_certificate"):
        validate_encounter_certificate(scenario)


def _blend_angle(
    start: float, target: float, fraction: float
) -> float:
    return wrap_angle(start + angle_delta(target, start) * fraction)


def _motor_knot_value(
    ticks: list[int], values: list[float], out_tick: int
) -> float:
    if out_tick <= ticks[0]:
        return float(values[0])
    if out_tick >= ticks[-1]:
        return float(values[-1])
    for index in range(len(ticks) - 1):
        start = int(ticks[index])
        end = int(ticks[index + 1])
        if start <= out_tick <= end:
            fraction = _smoothstep(
                (out_tick - start) / max(1, end - start)
            )
            return float(values[index]) + (
                float(values[index + 1]) - float(values[index])
            ) * fraction
    raise AssertionError(out_tick)


def _v5_style_offsets(
    *,
    profile: AimMotorProfile,
    schedule: dict[str, Any],
    policy: str,
    out_tick: int,
    initial_yaw_side: float,
) -> tuple[float, float]:
    style = str(profile["style"])
    if style == "direct_smooth":
        return 0.0, 0.0
    centers = [
        int(
            schedule[
                "pass_end_output_tick"
                if policy == "pass_offset"
                else "acquisition_end_output_tick"
            ]
        )
    ]
    if policy == "track_loss_reacquire":
        centers.append(int(schedule["reacquisition_end_output_tick"]))
    duration = int(profile["correction_duration_ticks"])
    scale = 0.0
    for center in centers:
        start = max(0, center - 12)
        peak = min(capture.OUTPUT_TICKS - 1, center + 4)
        end = min(capture.OUTPUT_TICKS - 1, peak + duration)
        if start < out_tick < peak:
            local = _smoothstep(
                (out_tick - start) / max(1, peak - start)
            )
        elif peak <= out_tick < end:
            local = 1.0 - _smoothstep(
                (out_tick - peak) / max(1, end - peak)
            )
        else:
            local = 0.0
        scale = max(scale, local)
    direction = 1.0 if initial_yaw_side >= 0.0 else -1.0
    if style == "overshoot_correct":
        direction *= -1.0
    return (
        direction
        * float(profile["acquisition_offset_yaw_deg"])
        * scale,
        float(profile["acquisition_offset_pitch_deg"]) * scale,
    )


def _v5_command_angles(
    *,
    policy: str,
    out_tick: int,
    baseline_yaw: float,
    baseline_pitch: float,
    target_yaw: float,
    target_pitch: float,
    paused_target_yaw: float | None,
    paused_target_pitch: float | None,
    schedule: dict[str, Any],
) -> tuple[float, float]:
    response_start = schedule.get("response_start_output_tick")
    if response_start is None or out_tick <= int(response_start):
        return baseline_yaw, baseline_pitch

    def acquire(end_key: str) -> tuple[float, float]:
        end = int(schedule[end_key])
        fraction = _smoothstep(
            (out_tick - int(response_start))
            / max(1, end - int(response_start))
        )
        return (
            _blend_angle(baseline_yaw, target_yaw, fraction),
            baseline_pitch
            + (target_pitch - baseline_pitch) * fraction,
        )

    if policy == "delayed_acquisition":
        if out_tick < int(schedule["acquisition_end_output_tick"]):
            return acquire("acquisition_end_output_tick")
        return target_yaw, target_pitch
    if policy == "pass_offset":
        pass_end = int(schedule["pass_end_output_tick"])
        pass_offset = float(schedule["pass_yaw_offset_deg"])
        fire_offset = float(schedule["fire_yaw_offset_deg"])
        if out_tick < pass_end:
            end = max(1, pass_end - int(response_start))
            fraction = _smoothstep(
                (out_tick - int(response_start)) / end
            )
            return (
                _blend_angle(
                    baseline_yaw,
                    wrap_angle(target_yaw + pass_offset),
                    fraction,
                ),
                baseline_pitch
                + (target_pitch - baseline_pitch) * fraction,
            )
        depart_end = int(schedule["depart_end_output_tick"])
        offset = _transition(
            out_tick,
            pass_end,
            depart_end,
            pass_offset,
            fire_offset,
        )
        return wrap_angle(target_yaw + offset), target_pitch
    if policy == "track_loss_reacquire":
        acquisition_end = int(
            schedule["acquisition_end_output_tick"]
        )
        if out_tick < acquisition_end:
            return acquire("acquisition_end_output_tick")
        pause_start = int(
            schedule["centered_hold_end_output_tick"]
        )
        if out_tick < pause_start:
            return target_yaw, target_pitch
        pause_end = int(schedule["tracking_pause_end_output_tick"])
        if out_tick < pause_end:
            if paused_target_yaw is None or paused_target_pitch is None:
                raise capture.CaptureFailure(
                    "stage2_v5_tracking_pause_reference_missing"
                )
            return paused_target_yaw, paused_target_pitch
        return target_yaw, target_pitch
    if policy == "sustained_tracking":
        if out_tick < int(schedule["acquisition_end_output_tick"]):
            return acquire("acquisition_end_output_tick")
        return target_yaw, target_pitch
    raise capture.CaptureFailure("stage2_aim_policy_unknown", policy)


def _v6_command_angles(
    *,
    policy: str,
    out_tick: int,
    baseline_yaw: float,
    baseline_pitch: float,
    target_yaw: float,
    target_pitch: float,
    paused_target_yaw: float | None,
    paused_target_pitch: float | None,
    schedule: dict[str, Any],
) -> tuple[float, float]:
    if policy != "pass_offset":
        return _v5_command_angles(
            policy=policy,
            out_tick=out_tick,
            baseline_yaw=baseline_yaw,
            baseline_pitch=baseline_pitch,
            target_yaw=target_yaw,
            target_pitch=target_pitch,
            paused_target_yaw=paused_target_yaw,
            paused_target_pitch=paused_target_pitch,
            schedule=schedule,
        )
    response_start = int(schedule["response_start_output_tick"])
    if out_tick <= response_start:
        return baseline_yaw, baseline_pitch
    pass_end = int(schedule["pass_end_output_tick"])
    pass_yaw = float(schedule["pass_yaw_offset_deg"])
    pass_pitch = float(schedule["pass_pitch_offset_deg"])
    if out_tick < pass_end:
        fraction = _smoothstep(
            (out_tick - response_start)
            / max(1, pass_end - response_start)
        )
        return (
            _blend_angle(
                baseline_yaw,
                wrap_angle(target_yaw + pass_yaw),
                fraction,
            ),
            baseline_pitch
            + (
                target_pitch
                + pass_pitch
                - baseline_pitch
            )
            * fraction,
        )
    depart_end = int(schedule["depart_end_output_tick"])
    fire_yaw = float(schedule["fire_yaw_offset_deg"])
    fire_pitch = float(schedule["fire_pitch_offset_deg"])
    return (
        wrap_angle(
            target_yaw
            + _transition(
                out_tick,
                pass_end,
                depart_end,
                pass_yaw,
                fire_yaw,
            )
        ),
        min(
            89.0,
            max(
                -89.0,
                target_pitch
                + _transition(
                    out_tick,
                    pass_end,
                    depart_end,
                    pass_pitch,
                    fire_pitch,
                ),
            ),
        ),
    )


def causal_action_rows_v5(
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build deterministic humanized open-loop Stage-2 actions."""
    design = scenario["causal_design"]
    policy = str(design["aim_policy"])
    schedule = design["aim_schedule"]
    profile = design["aim_motor_profile"]
    is_v6 = scenario.get("action_program") == ACTION_PROGRAM_V6
    if is_v6:
        validate_aim_schedule_v6(policy, schedule)
        validate_fire_program(
            design["fire_program"],
            policy=policy,
            design=design,
        )
    else:
        validate_aim_schedule_v5(policy, schedule)
    validate_aim_motor_profile(profile)
    channel = str(design["interaction_channel"])
    secondary_mechanism = design.get("secondary_mechanism")
    player_program = str(design["base_player_program"])
    base_actions: tuple[dict[str, Any], ...] | None = None
    base_states: pd.DataFrame | None = None
    if player_program == "certified_route_replay":
        base_actions, base_states, _ = player_path_artifacts(scenario)

    baseline_yaw: list[float] = []
    baseline_pitch: list[float] = []
    route_yaw: list[float] = []
    aim_player_origins: list[list[float]] = []
    target_yaw: list[float] = []
    target_pitch: list[float] = []
    for out_tick in range(capture.OUTPUT_TICKS):
        tick = capture.WARMUP_TICKS + out_tick
        if base_states is None:
            route_yaw_value = float(scenario["player"]["yaw"])
            route_pitch_value = float(
                scenario["player"].get("pitch", 0.0)
            )
            origin = list(scenario["player"]["origin"])
        else:
            base = base_actions[tick]
            angles = base_states.iloc[tick]["pre.angles"]
            route_yaw_value = wrap_angle(
                float(angles[1]) + float(base["yaw_delta"])
            )
            route_pitch_value = min(
                89.0,
                max(
                    -89.0,
                    float(angles[0]) + float(base["pitch_delta"]),
                ),
            )
            origin = list(base_states.iloc[tick]["pre.origin"])
        baseline_yaw.append(
            wrap_angle(
                route_yaw_value
                + float(design.get("base_view_yaw_offset_deg", 0.0))
            )
        )
        baseline_pitch.append(
            min(
                89.0,
                max(
                    -89.0,
                    route_pitch_value
                    + float(
                        design.get(
                            "base_view_pitch_offset_deg", 0.0
                        )
                    ),
                ),
            )
        )
        route_yaw.append(route_yaw_value)
        aim_player_origins.append(origin)
        enemy_origin = enemy_origin_at_server_tick(scenario, tick)
        yaw, pitch = yaw_pitch_toward(origin, enemy_origin)
        target_yaw.append(yaw)
        target_pitch.append(pitch)

    lag = int(profile["tracking_lag_ticks"])
    lagged_target_yaw = [
        target_yaw[max(0, index - lag)]
        for index in range(capture.OUTPUT_TICKS)
    ]
    lagged_target_pitch = [
        target_pitch[max(0, index - lag)]
        for index in range(capture.OUTPUT_TICKS)
    ]
    pause_reference_index = (
        int(schedule["centered_hold_end_output_tick"]) - 1
        if policy == "track_loss_reacquire"
        else None
    )
    paused_target_yaw = (
        lagged_target_yaw[pause_reference_index]
        if pause_reference_index is not None
        else None
    )
    paused_target_pitch = (
        lagged_target_pitch[pause_reference_index]
        if pause_reference_index is not None
        else None
    )
    initial_yaw_side = angle_delta(
        baseline_yaw[0], target_yaw[0]
    )

    fire_starts = tuple(
        int(value) for value in design["fire_output_ticks"]
    )
    fire_width = int(design["fire_width_ticks"])
    current_yaw = float(scenario["player"]["yaw"])
    current_pitch = float(scenario["player"].get("pitch", 0.0))
    yaw_velocity = 0.0
    pitch_velocity = 0.0
    rows: list[dict[str, Any]] = []
    response_start = schedule.get("response_start_output_tick")
    for tick in range(capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        if base_actions is None:
            base = {
                "forward": 0.0,
                "strafe": 0.0,
                "yaw_delta": 0.0,
                "pitch_delta": 0.0,
                "jump": 0,
            }
            current_route_yaw = float(scenario["player"]["yaw"])
        else:
            base = base_actions[tick]
            current_route_yaw = (
                route_yaw[out_tick]
                if out_tick >= 0
                else wrap_angle(
                    current_yaw + float(base["yaw_delta"])
                )
            )
        forward = float(base["forward"])
        strafe = float(base["strafe"])
        jump = int(base["jump"])
        yaw_delta = float(base["yaw_delta"])
        pitch_delta = float(base["pitch_delta"])
        primary = secondary = 0
        treatment_active = (
            out_tick >= 0
            and policy != "visible_no_response"
            and response_start is not None
            and out_tick > int(response_start)
        )

        if not treatment_active:
            current_yaw = wrap_angle(current_yaw + yaw_delta)
            current_pitch = min(
                89.0, max(-89.0, current_pitch + pitch_delta)
            )
            yaw_velocity = yaw_delta
            pitch_velocity = pitch_delta
        else:
            index = out_tick
            command_angles = (
                _v6_command_angles if is_v6 else _v5_command_angles
            )
            desired_yaw, desired_pitch = command_angles(
                policy=policy,
                out_tick=out_tick,
                baseline_yaw=baseline_yaw[index],
                baseline_pitch=baseline_pitch[index],
                target_yaw=lagged_target_yaw[index],
                target_pitch=lagged_target_pitch[index],
                paused_target_yaw=paused_target_yaw,
                paused_target_pitch=paused_target_pitch,
                schedule=schedule,
            )
            style_yaw, style_pitch = _v5_style_offsets(
                profile=profile,
                schedule=schedule,
                policy=policy,
                out_tick=out_tick,
                initial_yaw_side=initial_yaw_side,
            )
            gate = _smoothstep(
                (out_tick - int(response_start)) / 16.0
            )
            knots = profile["micro_correction_knot_ticks"]
            micro_yaw = _motor_knot_value(
                knots,
                profile["micro_correction_yaw_deg"],
                out_tick,
            )
            micro_pitch = _motor_knot_value(
                knots,
                profile["micro_correction_pitch_deg"],
                out_tick,
            )
            desired_yaw = wrap_angle(
                desired_yaw
                + style_yaw
                + gate
                * (
                    float(profile["residual_bias_yaw_deg"])
                    + micro_yaw
                )
            )
            desired_pitch = min(
                89.0,
                max(
                    -89.0,
                    desired_pitch
                    + style_pitch
                    + gate
                    * (
                        float(profile["residual_bias_pitch_deg"])
                        + micro_pitch
                    ),
                ),
            )
            error_yaw, error_pitch = shot_error_offsets(
                design["shot_error_schedule"], out_tick
            )
            desired_yaw = wrap_angle(desired_yaw + error_yaw)
            desired_pitch = min(
                89.0,
                max(-89.0, desired_pitch + error_pitch),
            )

            yaw_accel = (
                float(profile["proportional_gain_yaw"])
                * angle_delta(desired_yaw, current_yaw)
                - float(profile["damping_gain_yaw"])
                * yaw_velocity
            )
            pitch_accel = (
                float(profile["proportional_gain_pitch"])
                * (desired_pitch - current_pitch)
                - float(profile["damping_gain_pitch"])
                * pitch_velocity
            )
            yaw_accel = max(
                -float(profile["max_yaw_accel_deg_per_tick2"]),
                min(
                    float(
                        profile["max_yaw_accel_deg_per_tick2"]
                    ),
                    yaw_accel,
                ),
            )
            pitch_accel = max(
                -float(
                    profile["max_pitch_accel_deg_per_tick2"]
                ),
                min(
                    float(
                        profile["max_pitch_accel_deg_per_tick2"]
                    ),
                    pitch_accel,
                ),
            )
            yaw_velocity = max(
                -float(profile["max_yaw_speed_deg_per_tick"]),
                min(
                    float(profile["max_yaw_speed_deg_per_tick"]),
                    yaw_velocity + yaw_accel,
                ),
            )
            pitch_velocity = max(
                -float(profile["max_pitch_speed_deg_per_tick"]),
                min(
                    float(profile["max_pitch_speed_deg_per_tick"]),
                    pitch_velocity + pitch_accel,
                ),
            )
            yaw_delta = yaw_velocity
            pitch_delta = pitch_velocity
            current_yaw = wrap_angle(current_yaw + yaw_delta)
            current_pitch = min(
                89.0, max(-89.0, current_pitch + pitch_delta)
            )
            if base_states is not None:
                view_offset = math.radians(
                    angle_delta(current_yaw, current_route_yaw)
                )
                cosine = math.cos(view_offset)
                sine = math.sin(view_offset)
                base_forward = forward
                base_strafe = strafe
                forward = (
                    base_forward * cosine - base_strafe * sine
                )
                strafe = (
                    base_strafe * cosine + base_forward * sine
                )
            if is_v6:
                if channel != "primary":
                    raise capture.CaptureFailure(
                        "stage2_v6_primary_fire_only", channel
                    )
                primary = fire_program_active(
                    design["fire_program"], out_tick
                )
                secondary = 0
            else:
                primary, secondary = _v3_interaction_buttons(
                    out_tick=out_tick,
                    policy=policy,
                    channel=channel,
                    secondary_mechanism=secondary_mechanism,
                    fire_starts=fire_starts,
                    fire_width=fire_width,
                    design=design,
                )

        rows.append(
            {
                "tick": tick,
                "forward": round(forward, 6),
                "strafe": round(strafe, 6),
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": jump,
                "primary": primary,
                "secondary": secondary,
                "weapon_impulse": 0,
                "reload": 0,
            }
        )
    capture.validate_model_action_source_rows(rows)
    return rows


def causal_action_rows_v7(
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build frozen random-view and independently frozen fire actions."""
    design = scenario["causal_design"]
    program = design["random_aim_program"]
    validate_random_aim_program(program)
    validate_fire_program(
        design["fire_program"],
        policy=STOCHASTIC_AIM_POLICY,
        design=design,
    )
    ticks = [int(value) for value in program["knot_output_ticks"]]
    yaw_offsets = [
        float(value) for value in program["yaw_offset_deg"]
    ]
    pitch_offsets = [
        float(value) for value in program["pitch_offset_deg"]
    ]
    initial_yaw = float(scenario["player"]["yaw"])
    initial_pitch = float(scenario["player"].get("pitch", 0.0))
    current_yaw = initial_yaw
    current_pitch = initial_pitch
    rows: list[dict[str, Any]] = []
    for tick in range(capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        yaw_delta = 0.0
        pitch_delta = 0.0
        primary = 0
        if out_tick >= 0:
            desired_yaw = wrap_angle(
                initial_yaw
                + _motor_knot_value(ticks, yaw_offsets, out_tick)
            )
            desired_pitch = min(
                89.0,
                max(
                    -89.0,
                    initial_pitch
                    + _motor_knot_value(
                        ticks, pitch_offsets, out_tick
                    ),
                ),
            )
            yaw_delta = angle_delta(desired_yaw, current_yaw)
            pitch_delta = desired_pitch - current_pitch
            current_yaw = wrap_angle(current_yaw + yaw_delta)
            current_pitch = min(
                89.0, max(-89.0, current_pitch + pitch_delta)
            )
            primary = fire_program_active(
                design["fire_program"], out_tick
            )
        rows.append(
            {
                "tick": tick,
                "forward": 0.0,
                "strafe": 0.0,
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": 0,
                "primary": primary,
                "secondary": 0,
                "weapon_impulse": 0,
                "reload": 0,
            }
        )
    capture.validate_model_action_source_rows(rows)
    return rows


def causal_action_rows_v8(
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    """Add a manifest-frozen continuous player program to v7 actions."""
    rows = causal_action_rows_v7(scenario)
    program = scenario["causal_design"]["player_movement_program"]
    validate_player_movement_program(program)
    ticks = [int(value) for value in program["knot_output_ticks"]]
    left_x = [float(value) for value in program["j_left_x"]]
    left_y = [float(value) for value in program["j_left_y"]]
    for tick in range(capture.WARMUP_TICKS, capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        model_left_x = _motor_knot_value(ticks, left_x, out_tick)
        model_left_y = _motor_knot_value(ticks, left_y, out_tick)
        rows[tick]["strafe"] = round(
            model_left_x
            * capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
            6,
        )
        rows[tick]["forward"] = round(
            -model_left_y
            * capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
            6,
        )
    capture.validate_model_action_source_rows(rows)
    return rows


_V9_PROJECTILE_SPEED = {
    "Blaster": 6000.0,
    "Mortar": 1900.0,
    "Electro": 2500.0,
    "Crylink": 2000.0,
    "Hagar": 2200.0,
    "Devastator": 1000.0,
}
_V9_PROJECTILE_ACCELERATION = {"Devastator": 1300.0}
_V9_PRIMARY_DAMAGE_RADIUS = {
    "Blaster": 60.0,
    "Shotgun": 0.0,
    "MachineGun": 0.0,
    "Mortar": 120.0,
    "Electro": 100.0,
    "Crylink": 80.0,
    "Vortex": 0.0,
    "Hagar": 65.0,
    "Devastator": 110.0,
}


def _v9_lead_ticks(
    weapon: str, distance: float
) -> int:
    if weapon not in PROJECTILE_PRIMARY_WEAPONS:
        return 0
    speed = _V9_PROJECTILE_SPEED[weapon]
    acceleration = _V9_PROJECTILE_ACCELERATION.get(weapon, 0.0)
    if acceleration > 0.0:
        seconds = (
            -speed
            + math.sqrt(speed * speed + 2.0 * acceleration * distance)
        ) / acceleration
    else:
        seconds = distance / speed
    return max(0, min(48, int(math.ceil(seconds * 64.0))))


def _v9_target_angles(
    scenario: dict[str, Any],
    states: pd.DataFrame,
    out_tick: int,
    program: dict[str, Any],
) -> tuple[float, float, float, float]:
    server_tick = capture.WARMUP_TICKS + out_tick
    player_origin = list(states.iloc[server_tick]["pre.origin"])
    enemy_origin = enemy_origin_at_server_tick(scenario, server_tick)
    distance = float(
        np.linalg.norm(
            np.asarray(enemy_origin, dtype=np.float64)
            - np.asarray(player_origin, dtype=np.float64)
        )
    )
    if bool(program["projectile_lead"]):
        lead_ticks = _v9_lead_ticks(str(scenario["weapon"]), distance)
        enemy_origin = enemy_origin_at_server_tick(
            scenario,
            min(capture.TOTAL_TICKS - 1, server_tick + lead_ticks),
        )
        distance = float(
            np.linalg.norm(
                np.asarray(enemy_origin, dtype=np.float64)
                - np.asarray(player_origin, dtype=np.float64)
            )
        )
    target_yaw, target_pitch = yaw_pitch_toward(
        player_origin, enemy_origin
    )
    horizontal = max(
        1.0,
        math.hypot(
            enemy_origin[0] - player_origin[0],
            enemy_origin[1] - player_origin[1],
        ),
    )
    extra_radius = 0.0
    if program["offset_radius_kind"] == "weapon_effective_damage":
        extra_radius = _V9_PRIMARY_DAMAGE_RADIUS[str(scenario["weapon"])]
        if scenario["weapon"] == "Shotgun":
            extra_radius = max(extra_radius, horizontal * 0.12)
    yaw_radius = math.degrees(
        math.atan2(16.0 + extra_radius, horizontal)
    )
    pitch_radius = math.degrees(
        math.atan2(28.0 + extra_radius, horizontal)
    )
    direction = math.radians(float(program["offset_direction_deg"]))
    scale = float(program["target_offset_scale"])
    target_yaw = wrap_angle(
        target_yaw + scale * yaw_radius * math.cos(direction)
    )
    target_pitch = min(
        89.0,
        max(
            -89.0,
            target_pitch + scale * pitch_radius * math.sin(direction),
        ),
    )
    return target_yaw, target_pitch, yaw_radius, pitch_radius


def causal_action_rows_v9(
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    """Replay a certified moving trace under weapon-conditioned frozen aim."""
    design = scenario["causal_design"]
    program = design["weapon_balanced_aim_program"]
    validate_weapon_balanced_aim_program(program)
    base_actions, base_states = prefrozen_trace_artifacts(scenario)
    arm = str(program["arm"])
    humanized = arm in WEAPON_BALANCED_HUMANIZED_ARMS
    profile = program.get("motor_profile")
    random_program = program.get("random_aim_program")
    if humanized:
        assert isinstance(profile, dict)
    else:
        assert isinstance(random_program, dict)
        random_ticks = [
            int(value)
            for value in random_program["knot_output_ticks"]
        ]
        random_yaw = [
            float(value) for value in random_program["yaw_offset_deg"]
        ]
        random_pitch = [
            float(value) for value in random_program["pitch_offset_deg"]
        ]

    response_start = int(program["response_start_output_tick"])
    settle_tick = int(program["settle_output_tick"])
    current_yaw = float(scenario["player"]["yaw"])
    current_pitch = float(scenario["player"].get("pitch", 0.0))
    initial_yaw = current_yaw
    initial_pitch = current_pitch
    yaw_velocity = 0.0
    pitch_velocity = 0.0
    rows: list[dict[str, Any]] = []
    for tick in range(capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        base = base_actions[tick]
        forward = float(base["forward"])
        strafe = float(base["strafe"])
        jump = int(base["jump"])
        yaw_delta = float(base["yaw_delta"])
        pitch_delta = float(base["pitch_delta"])
        primary = 0
        if out_tick < 0:
            current_yaw = wrap_angle(current_yaw + yaw_delta)
            current_pitch = min(
                89.0, max(-89.0, current_pitch + pitch_delta)
            )
            yaw_velocity = yaw_delta
            pitch_velocity = pitch_delta
        else:
            reference_angles = base_states.iloc[tick]["pre.angles"]
            reference_yaw = wrap_angle(
                float(reference_angles[1])
                + float(base["yaw_delta"])
            )
            if humanized:
                target_yaw, target_pitch, _, _ = _v9_target_angles(
                    scenario, base_states, out_tick, program
                )
                if out_tick <= response_start:
                    desired_yaw = reference_yaw
                    desired_pitch = min(
                        89.0,
                        max(
                            -89.0,
                            float(reference_angles[0])
                            + float(base["pitch_delta"]),
                        ),
                    )
                    gate = 0.0
                else:
                    gate = _smoothstep(
                        (out_tick - response_start)
                        / max(1, settle_tick - response_start)
                    )
                    desired_yaw = _blend_angle(
                        reference_yaw, target_yaw, gate
                    )
                    desired_pitch = (
                        float(reference_angles[0])
                        + (
                            target_pitch
                            - float(reference_angles[0])
                        )
                        * gate
                    )
                overshoot_yaw = 0.0
                overshoot_pitch = 0.0
                if arm == "overshoot_correct" and 0.0 < gate < 1.0:
                    pulse = math.sin(math.pi * gate)
                    overshoot_yaw = (
                        float(profile["acquisition_offset_yaw_deg"])
                        * pulse
                    )
                    overshoot_pitch = (
                        float(profile["acquisition_offset_pitch_deg"])
                        * pulse
                    )
                knots = profile["micro_correction_knot_ticks"]
                micro_yaw = _motor_knot_value(
                    knots,
                    profile["micro_correction_yaw_deg"],
                    out_tick,
                )
                micro_pitch = _motor_knot_value(
                    knots,
                    profile["micro_correction_pitch_deg"],
                    out_tick,
                )
                desired_yaw = wrap_angle(
                    desired_yaw
                    + overshoot_yaw
                    + gate
                    * (
                        float(profile["residual_bias_yaw_deg"])
                        + micro_yaw
                    )
                )
                desired_pitch = min(
                    89.0,
                    max(
                        -89.0,
                        desired_pitch
                        + overshoot_pitch
                        + gate
                        * (
                            float(profile["residual_bias_pitch_deg"])
                            + micro_pitch
                        ),
                    ),
                )
                yaw_accel = (
                    float(profile["proportional_gain_yaw"])
                    * angle_delta(desired_yaw, current_yaw)
                    - float(profile["damping_gain_yaw"])
                    * yaw_velocity
                )
                pitch_accel = (
                    float(profile["proportional_gain_pitch"])
                    * (desired_pitch - current_pitch)
                    - float(profile["damping_gain_pitch"])
                    * pitch_velocity
                )
                yaw_accel = max(
                    -float(profile["max_yaw_accel_deg_per_tick2"]),
                    min(
                        float(profile["max_yaw_accel_deg_per_tick2"]),
                        yaw_accel,
                    ),
                )
                pitch_accel = max(
                    -float(profile["max_pitch_accel_deg_per_tick2"]),
                    min(
                        float(profile["max_pitch_accel_deg_per_tick2"]),
                        pitch_accel,
                    ),
                )
                yaw_velocity = max(
                    -float(profile["max_yaw_speed_deg_per_tick"]),
                    min(
                        float(profile["max_yaw_speed_deg_per_tick"]),
                        yaw_velocity + yaw_accel,
                    ),
                )
                pitch_velocity = max(
                    -float(profile["max_pitch_speed_deg_per_tick"]),
                    min(
                        float(profile["max_pitch_speed_deg_per_tick"]),
                        pitch_velocity + pitch_accel,
                    ),
                )
                yaw_delta = yaw_velocity
                pitch_delta = pitch_velocity
            else:
                desired_yaw = wrap_angle(
                    initial_yaw
                    + _motor_knot_value(
                        random_ticks, random_yaw, out_tick
                    )
                )
                desired_pitch = min(
                    89.0,
                    max(
                        -89.0,
                        initial_pitch
                        + _motor_knot_value(
                            random_ticks, random_pitch, out_tick
                        ),
                    ),
                )
                yaw_delta = angle_delta(desired_yaw, current_yaw)
                pitch_delta = desired_pitch - current_pitch
                yaw_velocity = yaw_delta
                pitch_velocity = pitch_delta

            current_yaw = wrap_angle(current_yaw + yaw_delta)
            current_pitch = min(
                89.0, max(-89.0, current_pitch + pitch_delta)
            )
            view_offset = math.radians(
                angle_delta(current_yaw, reference_yaw)
            )
            cosine = math.cos(view_offset)
            sine = math.sin(view_offset)
            base_forward = forward
            base_strafe = strafe
            forward = (
                base_forward * cosine - base_strafe * sine
            )
            strafe = (
                base_strafe * cosine + base_forward * sine
            )
            primary = fire_program_active(
                design["fire_program"], out_tick
            )

        rows.append(
            {
                "tick": tick,
                "forward": round(forward, 6),
                "strafe": round(strafe, 6),
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": jump,
                "primary": primary,
                "secondary": 0,
                "weapon_impulse": 0,
                "reload": 0,
            }
        )
    capture.validate_model_action_source_rows(rows)
    return rows


def _v3_desired_angles(
    *,
    policy: str,
    out_tick: int,
    baseline_yaw: float,
    baseline_pitch: float,
    target_yaw: float,
    target_pitch: float,
    schedule: dict[str, Any],
) -> tuple[float, float]:
    """Return a v3 post-usercmd view from frozen baseline and geometry."""
    response_start = schedule.get("response_start_output_tick")
    if response_start is None or out_tick <= int(response_start):
        return baseline_yaw, baseline_pitch

    def acquire(end_key: str, yaw_offset: float = 0.0) -> tuple[float, float]:
        end = int(schedule[end_key])
        fraction = _smoothstep(
            (out_tick - int(response_start))
            / max(1, end - int(response_start))
        )
        return (
            _blend_angle(
                baseline_yaw,
                wrap_angle(target_yaw + yaw_offset),
                fraction,
            ),
            baseline_pitch
            + (target_pitch - baseline_pitch) * fraction,
        )

    if policy == "delayed_acquisition":
        if out_tick < int(
            schedule["acquisition_end_output_tick"]
        ):
            return acquire("acquisition_end_output_tick")
        return target_yaw, target_pitch
    if policy == "pass_offset":
        pass_end = int(schedule["pass_end_output_tick"])
        pass_offset = float(schedule["pass_yaw_offset_deg"])
        fire_offset = float(schedule["fire_yaw_offset_deg"])
        if out_tick < pass_end:
            return acquire(
                "pass_end_output_tick", yaw_offset=pass_offset
            )
        depart_end = int(schedule["depart_end_output_tick"])
        offset = _transition(
            out_tick,
            pass_end,
            depart_end,
            pass_offset,
            fire_offset,
        )
        return wrap_angle(target_yaw + offset), target_pitch
    if policy == "track_loss_reacquire":
        acquisition_end = int(
            schedule["acquisition_end_output_tick"]
        )
        if out_tick < acquisition_end:
            return acquire("acquisition_end_output_tick")
        centered_hold_end = int(
            schedule["centered_hold_end_output_tick"]
        )
        if out_tick < centered_hold_end:
            return target_yaw, target_pitch
        loss_end = int(schedule["loss_end_output_tick"])
        loss_offset = float(schedule["loss_yaw_offset_deg"])
        if out_tick < loss_end:
            offset = _transition(
                out_tick,
                centered_hold_end,
                loss_end,
                0.0,
                loss_offset,
            )
            return wrap_angle(target_yaw + offset), target_pitch
        lost_hold_end = int(
            schedule["lost_hold_end_output_tick"]
        )
        if out_tick < lost_hold_end:
            return wrap_angle(target_yaw + loss_offset), target_pitch
        reacquisition_end = int(
            schedule["reacquisition_end_output_tick"]
        )
        offset = _transition(
            out_tick,
            lost_hold_end,
            reacquisition_end,
            loss_offset,
            0.0,
        )
        return wrap_angle(target_yaw + offset), target_pitch
    if policy == "sustained_tracking":
        if out_tick < int(
            schedule["acquisition_end_output_tick"]
        ):
            return acquire("acquisition_end_output_tick")
        return target_yaw, target_pitch
    raise capture.CaptureFailure("stage2_aim_policy_unknown", policy)


def _v3_interaction_buttons(
    *,
    out_tick: int,
    policy: str,
    channel: str,
    secondary_mechanism: str | None,
    fire_starts: tuple[int, ...],
    fire_width: int,
    design: dict[str, Any],
) -> tuple[int, int]:
    primary = secondary = 0
    if policy not in FIRING_POLICIES:
        return primary, secondary
    if channel == "primary":
        primary = capture.pulse(out_tick, fire_starts, fire_width)
    elif secondary_mechanism == "direct_secondary":
        secondary = capture.pulse(out_tick, fire_starts, fire_width)
    elif secondary_mechanism == "hagar_load_release":
        secondary = int(
            any(
                start - fire_width <= out_tick < start
                for start in fire_starts
            )
        )
    elif secondary_mechanism == "devastator_remote_detonation":
        launch_lead = int(
            design.get("secondary_launch_lead_ticks", 24)
        )
        primary = capture.pulse(
            out_tick,
            tuple(start - launch_lead for start in fire_starts),
            2,
        )
        secondary = capture.pulse(out_tick, fire_starts, 2)
    else:
        raise capture.CaptureFailure(
            "stage2_secondary_mechanism_unknown",
            str(secondary_mechanism),
        )
    return primary, secondary


def causal_action_rows_v3(
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build v3/v4 actions as a frozen baseline plus aim treatments."""
    design = scenario["causal_design"]
    policy = str(design["aim_policy"])
    schedule = design["aim_schedule"]
    channel = str(design["interaction_channel"])
    secondary_mechanism = design.get("secondary_mechanism")
    player_program = str(design["base_player_program"])
    base_actions: tuple[dict[str, Any], ...] | None = None
    base_states: pd.DataFrame | None = None
    if player_program == "certified_route_replay":
        base_actions, base_states, _ = player_path_artifacts(scenario)

    fire_starts = tuple(
        int(value) for value in design["fire_output_ticks"]
    )
    fire_width = int(design["fire_width_ticks"])
    base_view_yaw_offset = float(
        design.get("base_view_yaw_offset_deg", 0.0)
    )
    base_view_pitch_offset = float(
        design.get("base_view_pitch_offset_deg", 0.0)
    )
    current_yaw = float(scenario["player"]["yaw"])
    current_pitch = float(scenario["player"].get("pitch", 0.0))
    rows: list[dict[str, Any]] = []
    for tick in range(capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        if base_actions is None:
            base = {
                "forward": 0.0,
                "strafe": 0.0,
                "yaw_delta": 0.0,
                "pitch_delta": 0.0,
                "jump": 0,
            }
            baseline_yaw = float(scenario["player"]["yaw"])
            baseline_pitch = float(
                scenario["player"].get("pitch", 0.0)
            )
            route_yaw = baseline_yaw
        else:
            base = base_actions[tick]
            base_angles = base_states.iloc[tick]["pre.angles"]
            route_yaw = wrap_angle(
                float(base_angles[1]) + float(base["yaw_delta"])
            )
            route_pitch = min(
                89.0,
                max(
                    -89.0,
                    float(base_angles[0])
                    + float(base["pitch_delta"]),
                ),
            )
            baseline_yaw = wrap_angle(
                route_yaw + base_view_yaw_offset
            )
            baseline_pitch = min(
                89.0,
                max(
                    -89.0,
                    route_pitch + base_view_pitch_offset,
                ),
            )

        forward = float(base["forward"])
        strafe = float(base["strafe"])
        jump = int(base["jump"])
        yaw_delta = float(base["yaw_delta"])
        pitch_delta = float(base["pitch_delta"])
        primary = secondary = 0

        if out_tick < 0:
            current_yaw = wrap_angle(current_yaw + yaw_delta)
            current_pitch = min(
                89.0, max(-89.0, current_pitch + pitch_delta)
            )
            if base_states is not None:
                view_offset = math.radians(
                    angle_delta(current_yaw, route_yaw)
                )
                cosine = math.cos(view_offset)
                sine = math.sin(view_offset)
                base_forward = forward
                base_strafe = strafe
                forward = (
                    base_forward * cosine - base_strafe * sine
                )
                strafe = (
                    base_strafe * cosine + base_forward * sine
                )
        else:
            enemy_origin = enemy_origin_at_server_tick(
                scenario, tick
            )
            aim_player_origin = (
                list(base_states.iloc[tick]["pre.origin"])
                if base_states is not None
                else list(scenario["player"]["origin"])
            )
            target_yaw, target_pitch = yaw_pitch_toward(
                aim_player_origin, enemy_origin
            )
            desired_yaw, desired_pitch = _v3_desired_angles(
                policy=policy,
                out_tick=out_tick,
                baseline_yaw=baseline_yaw,
                baseline_pitch=baseline_pitch,
                target_yaw=target_yaw,
                target_pitch=target_pitch,
                schedule=schedule,
            )
            if scenario.get("schema_version") == SCENARIO_SCHEMA_V4:
                error_yaw, error_pitch = shot_error_offsets(
                    design["shot_error_schedule"], out_tick
                )
                desired_yaw = wrap_angle(desired_yaw + error_yaw)
                desired_pitch = min(
                    89.0,
                    max(-89.0, desired_pitch + error_pitch),
                )
            yaw_delta = angle_delta(desired_yaw, current_yaw)
            pitch_delta = desired_pitch - current_pitch
            current_yaw = wrap_angle(current_yaw + yaw_delta)
            current_pitch = min(
                89.0, max(-89.0, current_pitch + pitch_delta)
            )
            if base_states is not None:
                view_offset = math.radians(
                    angle_delta(current_yaw, route_yaw)
                )
                cosine = math.cos(view_offset)
                sine = math.sin(view_offset)
                base_forward = forward
                base_strafe = strafe
                forward = (
                    base_forward * cosine - base_strafe * sine
                )
                strafe = (
                    base_strafe * cosine + base_forward * sine
                )
            primary, secondary = _v3_interaction_buttons(
                out_tick=out_tick,
                policy=policy,
                channel=channel,
                secondary_mechanism=secondary_mechanism,
                fire_starts=fire_starts,
                fire_width=fire_width,
                design=design,
            )

        rows.append(
            {
                "tick": tick,
                "forward": round(forward, 6),
                "strafe": round(strafe, 6),
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": jump,
                "primary": primary,
                "secondary": secondary,
                "weapon_impulse": 0,
                "reload": 0,
            }
        )
    capture.validate_model_action_source_rows(rows)
    return rows


def causal_action_rows(
    scenario: dict[str, Any], retry: int = 0
) -> list[dict[str, Any]]:
    if scenario.get("action_program") not in ACTION_PROGRAMS:
        return BASE_ACTION_ROWS(scenario, retry=retry)
    del retry
    validate_scenario_contract(scenario)
    if scenario.get("action_program") == ACTION_PROGRAM_V9:
        return causal_action_rows_v9(scenario)
    if scenario.get("action_program") == ACTION_PROGRAM_V8:
        return causal_action_rows_v8(scenario)
    if scenario.get("action_program") == ACTION_PROGRAM_V7:
        return causal_action_rows_v7(scenario)
    if scenario.get("action_program") in {
        ACTION_PROGRAM_V5,
        ACTION_PROGRAM_V6,
    }:
        return causal_action_rows_v5(scenario)
    if scenario.get("action_program") in {
        ACTION_PROGRAM_V3,
        ACTION_PROGRAM_V4,
    }:
        return causal_action_rows_v3(scenario)
    design = scenario["causal_design"]
    policy = str(design["aim_policy"])
    channel = str(design["interaction_channel"])
    secondary_mechanism = design.get("secondary_mechanism")
    player_program = str(design["base_player_program"])
    base_actions: tuple[dict[str, Any], ...] | None = None
    base_states: pd.DataFrame | None = None
    if player_program == "certified_route_replay":
        base_actions, base_states, _ = player_path_artifacts(scenario)
    player_origin = list(scenario["player"]["origin"])
    desired_angles: list[tuple[float, float]] = []
    for out_tick in range(capture.OUTPUT_TICKS):
        if policy == "visible_no_response":
            if base_states is not None:
                base_angles = base_states.iloc[
                    capture.WARMUP_TICKS + out_tick
                ]["pre.angles"]
                desired_angles.append(
                    (float(base_angles[1]), float(base_angles[0]))
                )
                continue
            desired_angles.append(
                (
                    float(scenario["player"]["yaw"]),
                    float(scenario["player"].get("pitch", 0.0)),
                )
            )
            continue
        enemy_origin = enemy_origin_at_server_tick(
            scenario, capture.WARMUP_TICKS + out_tick
        )
        aim_player_origin = (
            list(
                base_states.iloc[
                    capture.WARMUP_TICKS + out_tick
                ]["pre.origin"]
            )
            if base_states is not None
            else player_origin
        )
        target_yaw, target_pitch = yaw_pitch_toward(
            aim_player_origin, enemy_origin
        )
        yaw_offset, pitch_offset = policy_offsets(policy, out_tick)
        desired_angles.append(
            (
                wrap_angle(target_yaw + yaw_offset),
                min(89.0, max(-89.0, target_pitch + pitch_offset)),
            )
        )

    fire_starts = tuple(int(value) for value in design["fire_output_ticks"])
    fire_width = int(design["fire_width_ticks"])
    rows: list[dict[str, Any]] = []
    current_yaw = float(scenario["player"]["yaw"])
    current_pitch = float(scenario["player"].get("pitch", 0.0))
    for tick in range(capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        yaw_delta = pitch_delta = 0.0
        forward = strafe = 0.0
        jump = 0
        primary = secondary = 0
        if base_actions is not None:
            base = base_actions[tick]
            forward = float(base["forward"])
            strafe = float(base["strafe"])
            jump = int(base["jump"])
            if out_tick < 0 or policy == "visible_no_response":
                yaw_delta = float(base["yaw_delta"])
                pitch_delta = float(base["pitch_delta"])
                current_yaw = wrap_angle(current_yaw + yaw_delta)
                current_pitch = min(
                    89.0, max(-89.0, current_pitch + pitch_delta)
                )
        if out_tick >= 0:
            if not (
                base_actions is not None
                and policy == "visible_no_response"
            ):
                target_yaw, target_pitch = desired_angles[out_tick]
                yaw_delta = angle_delta(target_yaw, current_yaw)
                pitch_delta = target_pitch - current_pitch
                current_yaw = wrap_angle(current_yaw + yaw_delta)
                current_pitch = min(
                    89.0, max(-89.0, current_pitch + pitch_delta)
                )
                if base_states is not None:
                    base_angles = base_states.iloc[tick]["pre.angles"]
                    base_yaw_after = wrap_angle(
                        float(base_angles[1])
                        + float(base_actions[tick]["yaw_delta"])
                    )
                    view_offset = math.radians(
                        angle_delta(current_yaw, base_yaw_after)
                    )
                    cosine = math.cos(view_offset)
                    sine = math.sin(view_offset)
                    base_forward = forward
                    base_strafe = strafe
                    forward = (
                        base_forward * cosine
                        - base_strafe * sine
                    )
                    strafe = (
                        base_strafe * cosine
                        + base_forward * sine
                    )
            if policy in FIRING_POLICIES:
                if channel == "primary":
                    primary = capture.pulse(
                        out_tick, fire_starts, fire_width
                    )
                elif secondary_mechanism == "direct_secondary":
                    secondary = capture.pulse(
                        out_tick, fire_starts, fire_width
                    )
                elif secondary_mechanism == "hagar_load_release":
                    secondary = int(
                        any(
                            start - fire_width
                            <= out_tick
                            < start
                            for start in fire_starts
                        )
                    )
                elif (
                    secondary_mechanism
                    == "devastator_remote_detonation"
                ):
                    launch_lead = int(
                        design.get("secondary_launch_lead_ticks", 24)
                    )
                    primary = capture.pulse(
                        out_tick,
                        tuple(start - launch_lead for start in fire_starts),
                        2,
                    )
                    secondary = capture.pulse(
                        out_tick, fire_starts, 2
                    )
                else:
                    raise capture.CaptureFailure(
                        "stage2_secondary_mechanism_unknown",
                        str(secondary_mechanism),
                    )
        rows.append(
            {
                "tick": tick,
                "forward": round(forward, 6),
                "strafe": round(strafe, 6),
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": jump,
                "primary": primary,
                "secondary": secondary,
                "weapon_impulse": 0,
                "reload": 0,
            }
        )
    capture.validate_model_action_source_rows(rows)
    return rows


def actual_outcome_bin(qa: dict[str, Any]) -> str:
    events = qa["events"]
    if int(events.get("fire_count", 0)) == 0:
        return "no_fire"
    if int(events.get("death_count", 0)) > 0:
        return "kill"
    if int(events.get("damage_count", 0)) > 0:
        return "hit_survive"
    return "miss"


def target_damage_fire_ids(
    events: pd.DataFrame, target_entity: int
) -> set[int]:
    """Resolve fire roots that caused authoritative damage to one target."""
    if events.empty or "event" not in events.columns:
        return set()
    indexed = {
        int(row["event_id"]): row.to_dict()
        for _, row in events.dropna(subset=["event_id"]).iterrows()
    }
    result: set[int] = set()
    for _, damage in events[events["event"] == "damage"].iterrows():
        target = damage.get("target")
        if pd.isna(target) or int(target) != int(target_entity):
            continue
        parent = damage.get("parent_event_id")
        visited: set[int] = set()
        while pd.notna(parent):
            event_id = int(parent)
            if event_id in visited or event_id not in indexed:
                break
            visited.add(event_id)
            ancestor = indexed[event_id]
            if str(ancestor.get("event")) == "fire":
                result.add(event_id)
                break
            parent = ancestor.get("parent_event_id")
    return result


def distance_bin(distance: float | None) -> str | None:
    if distance is None or not math.isfinite(distance):
        return None
    for name, upper in (
        ("close", 256.0),
        ("near", 512.0),
        ("medium", 768.0),
        ("far", 1024.0),
        ("very_far", 1536.0),
    ):
        if distance < upper:
            return name
    return "extreme"


def _first_index(mask: np.ndarray, minimum: int = 0) -> int | None:
    indices = np.flatnonzero(mask & (np.arange(len(mask)) >= minimum))
    return int(indices[0]) if len(indices) else None


def prescribed_treatment_relations(
    package: Path,
    scenario: dict[str, Any],
    realized_relations: pd.DataFrame,
) -> dict[str, Any]:
    """Measure camera alignment to the frozen no-interaction target path.

    Stage-2 aim actions are generated from the manifest-frozen analytic
    trajectory.  Damage, knockback, and death are downstream outcomes and may
    move the realized target away from that path.  Policy fidelity therefore
    uses this prescribed reference, while the ordinary target-relations table
    remains the authoritative realized observation.
    """
    frames = pd.read_parquet(package / "frames.parquet").sort_values(
        "frame_index"
    )
    if (
        len(frames) != capture.OUTPUT_TICKS
        or frames["frame_index"].astype(int).tolist()
        != list(range(capture.OUTPUT_TICKS))
    ):
        raise capture.CaptureFailure(
            "stage2_treatment_reference_frame_shape",
            str(package),
        )
    ticks = pd.to_numeric(
        frames["episode_server_tick"], errors="raise"
    ).astype(np.int64).to_numpy()
    if ticks.tolist() != list(
        range(capture.WARMUP_TICKS, capture.TOTAL_TICKS)
    ):
        raise capture.CaptureFailure(
            "stage2_treatment_reference_tick_span",
            str(package),
        )

    los = (
        pd.to_numeric(
            realized_relations["los_fraction"], errors="coerce"
        )
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
        >= 0.999999
    )
    los_reference = "realized_target_relation"
    if scenario.get("encounter_certificate"):
        certificate = validate_encounter_certificate(scenario)
        artifact_hashes = certificate.get("artifacts_sha256") or {}
        expected_sha256 = artifact_hashes.get(
            "target_relations.parquet"
        )
        source_episode_path = certificate.get(
            "source_episode_path"
        )
        if not expected_sha256 or not source_episode_path:
            raise capture.CaptureFailure(
                "stage2_treatment_reference_certificate_artifact"
            )
        source_path = capture.locked_root_artifact(
            str(
                Path(str(source_episode_path))
                / "target_relations.parquet"
            ),
            str(expected_sha256),
            "stage2_treatment_reference_relations",
        )
        source_relations = pd.read_parquet(source_path).sort_values(
            "frame_index"
        )
        source_ticks = pd.to_numeric(
            source_relations["server_tick"], errors="raise"
        ).astype(np.int64).to_numpy()
        if (
            len(source_relations) != capture.OUTPUT_TICKS
            or not np.array_equal(source_ticks, ticks)
        ):
            raise capture.CaptureFailure(
                "stage2_treatment_reference_certificate_shape",
                str(source_path),
            )
        los = (
            pd.to_numeric(
                source_relations["los_fraction"], errors="coerce"
            )
            .fillna(0.0)
            .to_numpy(dtype=np.float64)
            >= 0.999999
        )
        los_reference = (
            "certified_no_interaction_authoritative_los"
        )

    camera = frames[
        ["camera_x", "camera_y", "camera_z"]
    ].to_numpy(dtype=np.float64)
    forward = frames[
        ["forward_x", "forward_y", "forward_z"]
    ].to_numpy(dtype=np.float64)
    left = frames[
        ["left_x", "left_y", "left_z"]
    ].to_numpy(dtype=np.float64)
    up = frames[
        ["up_x", "up_y", "up_z"]
    ].to_numpy(dtype=np.float64)
    frustum_x = pd.to_numeric(
        frames["frustum_x"], errors="raise"
    ).to_numpy(dtype=np.float64)
    frustum_y = pd.to_numeric(
        frames["frustum_y"], errors="raise"
    ).to_numpy(dtype=np.float64)
    target = np.asarray(
        [
            np.asarray(
                enemy_origin_at_server_tick(scenario, int(tick)),
                dtype=np.float64,
            )
            + np.asarray([0.0, 0.0, 24.0])
            for tick in ticks
        ],
        dtype=np.float64,
    )
    values = np.concatenate(
        (
            camera,
            forward,
            left,
            up,
            frustum_x[:, None],
            frustum_y[:, None],
            target,
        ),
        axis=1,
    )
    if not np.isfinite(values).all():
        raise capture.CaptureFailure(
            "stage2_treatment_reference_nonfinite",
            str(package),
        )
    relative = target - camera
    depth = np.sum(relative * forward, axis=1)
    lateral = np.sum(relative * left, axis=1)
    vertical = np.sum(relative * up, axis=1)
    angular_error = np.degrees(
        np.arctan2(
            np.hypot(lateral, vertical),
            np.maximum(depth, 1e-12),
        )
    )
    in_frustum = (
        (depth > 0)
        & (np.abs(lateral / np.maximum(depth, 1e-12)) <= frustum_x)
        & (np.abs(vertical / np.maximum(depth, 1e-12)) <= frustum_y)
    )
    visible = in_frustum & los
    centered = (
        visible
        & np.isfinite(angular_error)
        & (angular_error <= TARGET_CENTER_THRESHOLD_DEG)
    )
    return {
        "reference_kind": (
            "manifest_frozen_analytic_enemy_trajectory"
        ),
        "los_reference": los_reference,
        "visible": visible,
        "angular_error_deg": angular_error,
        "centered": centered,
    }


def causal_metrics_v7(
    package: Path, scenario: dict[str, Any], qa: dict[str, Any]
) -> dict[str, Any]:
    """Fail-closed QA for frozen stochastic/balanced programs (v7-v9)."""
    is_v8 = scenario.get("schema_version") == SCENARIO_SCHEMA_V8
    is_v9 = scenario.get("schema_version") == SCENARIO_SCHEMA_V9
    design = scenario["causal_design"]
    relations = pd.read_parquet(
        package / "target_relations.parquet"
    ).sort_values("frame_index")
    actions = pd.read_parquet(
        package / "model_actions.parquet"
    ).sort_values("frame_index")
    events = pd.read_parquet(package / "events.parquet")
    shots = pd.read_parquet(package / "shot_outcomes.parquet")
    enemy_trace = pd.read_parquet(
        package / "enemy_path_trace.parquet"
    ).sort_values("server_tick")
    states = pd.read_parquet(package / "states.parquet").sort_values(
        "server_tick"
    )
    expected_source = (
        causal_action_rows_v9(scenario)
        if is_v9
        else (
            causal_action_rows_v8(scenario)
            if is_v8
            else causal_action_rows_v7(scenario)
        )
    )[
        capture.WARMUP_TICKS :
    ]
    expected_yaw = np.asarray(
        [float(row["yaw_delta"]) for row in expected_source],
        dtype=np.float64,
    )
    expected_pitch = np.asarray(
        [float(row["pitch_delta"]) for row in expected_source],
        dtype=np.float64,
    )
    expected_primary = np.asarray(
        [bool(row["primary"]) for row in expected_source],
        dtype=bool,
    )
    expected_left_x = np.asarray(
        [
            float(row["strafe"])
            / capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE
            for row in expected_source
        ],
        dtype=np.float64,
    )
    expected_left_y = np.asarray(
        [
            -float(row["forward"])
            / capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE
            for row in expected_source
        ],
        dtype=np.float64,
    )
    actual_right_x = pd.to_numeric(
        actions["j_right_x"], errors="raise"
    ).to_numpy(np.float64)
    actual_right_y = pd.to_numeric(
        actions["j_right_y"], errors="raise"
    ).to_numpy(np.float64)
    actual_primary = (
        pd.to_numeric(actions["right_trigger"], errors="raise")
        .to_numpy(np.float64)
        > 0.5
    )
    actual_secondary = (
        pd.to_numeric(actions["left_trigger"], errors="raise")
        .to_numpy(np.float64)
        > 0.5
    )
    actual_left_x = pd.to_numeric(
        actions["j_left_x"], errors="raise"
    ).to_numpy(np.float64)
    actual_left_y = pd.to_numeric(
        actions["j_left_y"], errors="raise"
    ).to_numpy(np.float64)
    movement = np.hypot(actual_left_x, actual_left_y)
    jump = (
        pd.to_numeric(actions["south"], errors="raise")
        .to_numpy(np.float64)
        > 0.5
    )
    unused = actions[
        [
            "east",
            "north",
            "left_shoulder",
            "right_shoulder",
            "west",
        ]
    ].to_numpy(np.float64)

    event_names = events["event"].astype(str)
    fire_events = events[event_names == "fire"].sort_values(
        ["server_tick", "event_id"]
    )
    fire_frames = [
        int(value) - capture.WARMUP_TICKS
        for value in fire_events["server_tick"].tolist()
    ]
    program = design["fire_program"]
    windows = program["windows"]
    minimum = int(program["expected_min_fire_events"])
    maximum = int(program["expected_max_fire_events"])
    rising_edges = int(
        sum(
            bool(
                actual_primary[index]
                and (
                    index == 0
                    or not actual_primary[index - 1]
                )
            )
            for index in range(len(actual_primary))
        )
    )
    last_window_end = max(
        (
            int(window["start_output_tick"])
            + int(window["duration_ticks"])
            for window in windows
        ),
        default=-1,
    )
    fire_checks = {
        "requested_windows_exact": bool(
            np.array_equal(actual_primary, expected_primary)
        ),
        "rising_edges_exact": rising_edges == len(windows),
        "secondary_released": not actual_secondary.any(),
        "authoritative_count_in_bounds": minimum
        <= len(fire_events)
        <= maximum,
        "all_fire_events_in_output": all(
            0 <= frame < capture.OUTPUT_TICKS
            for frame in fire_frames
        ),
        "events_within_refire_grace": (
            not fire_frames
            or max(fire_frames)
            <= min(
                capture.OUTPUT_TICKS - 1,
                last_window_end + 96,
            )
        ),
        "qa_fire_count_exact": int(
            qa["events"].get("fire_count", -1)
        )
        == len(fire_events),
    }

    shot_hits = shots["hit"].astype(bool)
    enemy_entity = int(
        ((qa.get("enemy_policy") or {}).get("movement_audio") or {}).get(
            "enemy_entity", -1
        )
    )
    target_hit_ids = target_damage_fire_ids(events, enemy_entity)
    fire_tick_by_id = {
        int(row["event_id"]): int(row["server_tick"])
        for _, row in fire_events.iterrows()
    }
    target_negative_fire_ids = (
        set(fire_tick_by_id) - target_hit_ids
    )
    unresolved_target_fire_ids = {
        fire_id
        for fire_id in target_negative_fire_ids
        if str(scenario["weapon"]) in PROJECTILE_PRIMARY_WEAPONS
        and (
            capture.TOTAL_TICKS
            - 1
            - int(fire_tick_by_id[fire_id])
            < PROJECTILE_OUTCOME_OBSERVATION_TICKS
        )
    }
    target_label_columns = {
        "target_entity",
        "target_hit",
        "target_outcome",
        "target_observation_complete",
        "right_censored",
    }
    target_columns_present = target_label_columns <= set(shots.columns)
    target_label_checks = {
        "columns_present": target_columns_present,
        "entity_exact": False,
        "hit_ids_exact": False,
        "outcomes_valid": False,
        "observation_complete": False,
        "not_right_censored": False,
    }
    if target_columns_present:
        target_label_checks.update(
            {
                "entity_exact": bool(
                    len(shots) == 0
                    or (
                        pd.to_numeric(
                            shots["target_entity"], errors="raise"
                        ).astype(int)
                        == enemy_entity
                    ).all()
                ),
                "hit_ids_exact": set(
                    pd.to_numeric(
                        shots.loc[
                            shots["target_hit"].astype(bool),
                            "fire_event_id",
                        ],
                        errors="raise",
                    ).astype(int)
                )
                == target_hit_ids,
                "outcomes_valid": set(
                    shots["target_outcome"].astype(str)
                )
                <= {"miss", "hit", "kill"},
                "observation_complete": bool(
                    shots["target_observation_complete"]
                    .astype(bool)
                    .all()
                ),
                "not_right_censored": bool(
                    not shots["right_censored"].astype(bool).any()
                ),
            }
        )
    shot_checks = {
        "one_row_per_fire": len(shots) == len(fire_events),
        "fire_ids_unique": bool(shots["fire_event_id"].is_unique),
        "fire_ids_exact": set(
            pd.to_numeric(
                shots["fire_event_id"], errors="raise"
            ).astype(int)
        )
        == set(
            pd.to_numeric(
                fire_events["event_id"], errors="raise"
            ).astype(int)
        ),
        "hit_count_exact": int(shot_hits.sum())
        == int(qa["events"].get("hit_fire_count", -1)),
        "outcomes_valid": set(shots["outcome"].astype(str))
        <= {"miss", "hit", "kill"},
        "target_entity_valid": enemy_entity > 0,
        "target_hit_ids_are_fires": target_hit_ids
        <= set(fire_tick_by_id),
        "target_negative_observation_complete": not (
            unresolved_target_fire_ids
        ),
        "target_labels_exact": (
            all(target_label_checks.values()) if is_v9 else True
        ),
        "not_an_acceptance_gate": (
            (scenario.get("acceptance") or {}).get(
                "actual_outcome"
            )
            is None
        ),
    }

    visible = (
        relations["render_visible_proxy"].fillna(False).to_numpy(bool)
    )
    angular_error = pd.to_numeric(
        relations["angular_error_deg"], errors="coerce"
    ).to_numpy(np.float64)
    fire_error = [
        float(angular_error[frame])
        if 0 <= frame < len(angular_error)
        and math.isfinite(float(angular_error[frame]))
        else None
        for frame in fire_frames
    ]
    yaw_step = -actual_right_x * (
        capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
    )
    pitch_step = actual_right_y * (
        capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
    )

    def direction_reversals(values: np.ndarray) -> int:
        signs = np.sign(values[np.abs(values) > 1e-4])
        return (
            int((signs[1:] != signs[:-1]).sum())
            if len(signs) > 1
            else 0
        )

    output_trace = enemy_trace[
        pd.to_numeric(
            enemy_trace["server_tick"], errors="raise"
        ).astype(int)
        >= capture.WARMUP_TICKS
    ]
    output_server_ticks = (
        pd.to_numeric(
            output_trace["server_tick"], errors="raise"
        )
        .astype(int)
        .tolist()
    )
    expected_policy_states = [
        enemy_policy_state_at_server_tick(scenario, tick)
        for tick in output_server_ticks
    ]
    actual_policy_segments = pd.to_numeric(
        output_trace["policy_segment"], errors="raise"
    ).to_numpy(np.int64)
    actual_policy_progress = pd.to_numeric(
        output_trace["policy_progress"], errors="raise"
    ).to_numpy(np.float64)
    actual_policy_hold = (
        pd.to_numeric(
            output_trace["policy_hold"], errors="raise"
        ).to_numpy(np.float64)
        > 0.5
    )
    actual_policy_hop = (
        pd.to_numeric(
            output_trace["policy_hop"], errors="raise"
        ).to_numpy(np.float64)
        > 0.5
    )
    expected_policy_segments = np.asarray(
        [state["segment"] for state in expected_policy_states],
        dtype=np.int64,
    )
    expected_policy_progress = np.asarray(
        [state["progress"] for state in expected_policy_states],
        dtype=np.float64,
    )
    expected_policy_hold = np.asarray(
        [state["hold"] for state in expected_policy_states],
        dtype=bool,
    )
    expected_policy_hop = np.asarray(
        [state["hop"] for state in expected_policy_states],
        dtype=bool,
    )
    policy_progress_max_error = float(
        np.max(
            np.abs(
                actual_policy_progress - expected_policy_progress
            )
        )
    )
    policy_explanation_checks = {
        "segment_exact": bool(
            np.array_equal(
                actual_policy_segments, expected_policy_segments
            )
        ),
        "progress_exact": bool(
            np.allclose(
                actual_policy_progress,
                expected_policy_progress,
                atol=1e-6,
                rtol=0,
            )
        ),
        "hold_exact": bool(
            np.array_equal(
                actual_policy_hold, expected_policy_hold
            )
        ),
        "hop_exact": bool(
            np.array_equal(actual_policy_hop, expected_policy_hop)
        ),
    }
    segment_values = pd.to_numeric(
        output_trace["policy_segment"], errors="coerce"
    ).dropna()
    segment_count = int(segment_values.nunique())
    hold_frames = int(
        pd.to_numeric(
            output_trace["policy_hold"], errors="coerce"
        ).fillna(0).astype(bool).sum()
    )
    hop_frames = int(
        pd.to_numeric(
            output_trace["policy_hop"], errors="coerce"
        ).fillna(0).astype(bool).sum()
    )
    commanded_velocity = np.asarray(
        output_trace["commanded_velocity"].tolist(),
        dtype=np.float64,
    )
    horizontal_speed = np.linalg.norm(
        commanded_velocity[:, :2], axis=1
    )
    enemy_checks = {
        "motion_mode_exact": int(
            (scenario.get("enemy") or {}).get("motion", -1)
        )
        == 4,
        "trace_rows_exact": len(enemy_trace)
        == capture.TOTAL_TICKS - 1,
        "output_segments_diverse": segment_count >= 4,
        "moving_frames_present": int(
            (horizontal_speed > 1.0).sum()
        )
        >= 32,
        "speed_time_varying": float(np.std(horizontal_speed)) > 1.0,
        "policy_explanation_exact": all(
            policy_explanation_checks.values()
        ),
        "whole_path_safe": (
            (qa.get("enemy_policy") or {})
            .get("whole_path_trace", {})
            .get("passed")
            is True
        ),
        "no_live_coupling": (
            (qa.get("enemy_policy") or {}).get(
                "runtime_reads_camera"
            )
            is False
            and (qa.get("enemy_policy") or {}).get(
                "runtime_reads_crosshair"
            )
            is False
            and (qa.get("enemy_policy") or {}).get(
                "runtime_reads_player_state"
            )
            is False
        ),
    }
    output_states = states[
        pd.to_numeric(states["server_tick"], errors="raise").astype(int)
        >= capture.WARMUP_TICKS
    ]
    state_origins = np.asarray(
        output_states["post.origin"].tolist(), dtype=np.float64
    )
    state_horizontal_steps = (
        np.linalg.norm(np.diff(state_origins[:, :2], axis=0), axis=1)
        if len(state_origins) > 1
        else np.asarray([], dtype=np.float64)
    )
    initial_origin = state_origins[0]
    horizontal_displacements = np.linalg.norm(
        state_origins[:, :2] - initial_origin[:2], axis=1
    )
    onground = (
        pd.to_numeric(
            output_states["post.onground"], errors="raise"
        ).to_numpy(np.float64)
        > 0.5
    )
    longest_ungrounded = 0
    maximum_airborne_drop = 0.0
    run_start: int | None = None
    for index, grounded in enumerate(onground):
        if not grounded and run_start is None:
            run_start = index
        if grounded and run_start is not None:
            segment = state_origins[run_start:index, 2]
            longest_ungrounded = max(
                longest_ungrounded, index - run_start
            )
            if len(segment):
                maximum_airborne_drop = max(
                    maximum_airborne_drop,
                    float(np.max(segment) - np.min(segment)),
                )
            run_start = None
    if run_start is not None:
        segment = state_origins[run_start:, 2]
        longest_ungrounded = max(
            longest_ungrounded, len(onground) - run_start
        )
        if len(segment):
            maximum_airborne_drop = max(
                maximum_airborne_drop,
                float(np.max(segment) - np.min(segment)),
            )
    health = pd.to_numeric(
        output_states["post.health"], errors="raise"
    ).to_numpy(np.float64)
    blockage = (
        (qa.get("telemetry") or {}).get("movement_blockage") or {}
    )
    player_health_policy = design.get(
        "player_health_policy", "not_reduced"
    )
    player_health_check = (
        bool(len(health) and float(np.min(health)) > 0.0)
        if player_health_policy == "player_alive"
        else bool(
            len(health)
            and float(np.min(health))
            >= float(health[0]) - 0.1
        )
    )
    player_motion_checks = {
        "state_rows_exact": len(output_states) == capture.OUTPUT_TICKS,
        "program_exact_x": bool(
            np.allclose(
                actual_left_x,
                expected_left_x,
                atol=1e-7,
                rtol=0,
            )
        ),
        "program_exact_y": bool(
            np.allclose(
                actual_left_y,
                expected_left_y,
                atol=1e-7,
                rtol=0,
            )
        ),
        "movement_active": int((movement > 0.05).sum()) >= 192,
        "two_axis_movement": bool(
            (np.abs(actual_left_x) > 0.05).any()
            and (np.abs(actual_left_y) > 0.05).any()
        ),
        "jump_absent": not jump.any(),
        "contact_telemetry_present": blockage.get(
            "contact_telemetry_present"
        )
        is True,
        "collision_policy_passed": blockage.get(
            "collision_policy_passed"
        )
        is True,
        "ordinary_movement_clear": blockage.get(
            "ordinary_movement_clear"
        )
        is True,
        "horizontal_path_realized": (
            float(state_horizontal_steps.sum()) >= 48.0
            and float(state_horizontal_steps.sum()) <= 640.0
        ),
        "horizontal_displacement_bounded": (
            float(np.max(horizontal_displacements)) >= 16.0
            and float(np.max(horizontal_displacements)) <= 384.0
            and float(horizontal_displacements[-1]) <= 256.0
        ),
        "no_unintended_fall": not (
            longest_ungrounded >= 12
            and maximum_airborne_drop >= 48.0
        ),
        (
            "player_alive"
            if player_health_policy == "player_alive"
            else "player_health_not_reduced"
        ): player_health_check,
    }
    trace_replay_metrics: dict[str, Any] | None = None
    if is_v9:
        _, reference_states = prefrozen_trace_artifacts(scenario)
        reference_output = reference_states[
            pd.to_numeric(
                reference_states["server_tick"], errors="raise"
            ).astype(int)
            >= capture.WARMUP_TICKS
        ]
        reference_origins = np.asarray(
            reference_output["post.origin"].tolist(),
            dtype=np.float64,
        )
        position_error = np.linalg.norm(
            state_origins - reference_origins, axis=1
        )
        p95_error = float(np.percentile(position_error, 95))
        maximum_error = float(np.max(position_error))
        trace_source = scenario["prefrozen_trace_source"]
        player_motion_checks.update(
            {
                "trace_rows_exact": len(reference_origins)
                == len(state_origins)
                == capture.OUTPUT_TICKS,
                "trace_position_error_p95": p95_error
                <= float(trace_source["position_error_p95_max"]),
                "trace_position_error_max": maximum_error
                <= float(trace_source["position_error_max_max"]),
            }
        )
        trace_replay_metrics = {
            "source_episode_id": trace_source["source_episode_id"],
            "position_error_p95": p95_error,
            "position_error_max": maximum_error,
            "position_error_p95_limit": float(
                trace_source["position_error_p95_max"]
            ),
            "position_error_max_limit": float(
                trace_source["position_error_max_max"]
            ),
        }
    action_checks = {
        "rows_exact": len(actions)
        == len(relations)
        == capture.OUTPUT_TICKS,
        "yaw_program_exact": bool(
            np.allclose(
                actual_right_x,
                -expected_yaw
                / capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK,
                atol=1e-7,
                rtol=0,
            )
        ),
        "pitch_program_exact": bool(
            np.allclose(
                actual_right_y,
                expected_pitch
                / capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK,
                atol=1e-7,
                rtol=0,
            )
        ),
        (
            "certified_prefrozen_trace_replay"
            if is_v9
            else (
                "prefrozen_player_movement"
                if is_v8
                else "stationary_player"
            )
        ): (
            all(player_motion_checks.values())
            if is_v8 or is_v9
            else not (movement > 1e-6).any() and not jump.any()
        ),
        "unused_buttons_zero": not np.asarray(unused).any(),
        "two_axis_view_motion": bool(
            (np.abs(yaw_step) > 1e-4).any()
            and (np.abs(pitch_step) > 1e-4).any()
        ),
        "view_within_model_range": float(
            np.max(np.abs(yaw_step))
        )
        <= capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
        and float(np.max(np.abs(pitch_step)))
        <= capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK,
    }
    gate_prefix = (
        "stage2_v9"
        if is_v9
        else "stage2_v8" if is_v8 else "stage2_v7"
    )
    hard_gates = {
        f"{gate_prefix}_exogenous_contract": (
            scenario["exogenous_contract_sha256"]
            == exogenous_contract_sha256(scenario)
        ),
        f"{gate_prefix}_action_program_exact": all(
            action_checks.values()
        ),
        f"{gate_prefix}_fire_program_realized": all(
            fire_checks.values()
        ),
        f"{gate_prefix}_per_shot_labels_exact": all(
            shot_checks.values()
        ),
        f"{gate_prefix}_initial_target_visible": bool(visible[0]),
        f"{gate_prefix}_target_observed": int(visible.sum()) >= 8,
        f"{gate_prefix}_enemy_random_policy_realized": all(
            enemy_checks.values()
        ),
        f"{gate_prefix}_outcome_telemetry_valid": actual_outcome_bin(qa)
        in {"no_fire", "miss", "hit_survive", "kill"},
    }
    if is_v8 or is_v9:
        hard_gates[
            (
                "stage2_v9_player_trace_safe_and_realized"
                if is_v9
                else "stage2_v8_player_motion_safe_and_realized"
            )
        ] = all(player_motion_checks.values())
    reference_frame = fire_frames[0] if fire_frames else 0
    reference_distance = None
    if 0 <= reference_frame < len(relations):
        value = float(relations.iloc[reference_frame]["distance_3d"])
        reference_distance = value if math.isfinite(value) else None
    centered = (
        visible
        & np.isfinite(angular_error)
        & (angular_error <= TARGET_CENTER_THRESHOLD_DEG)
    )
    return {
        "schema_version": (
            "xonotic-stage2-causal-qa-v9"
            if is_v9
            else (
                "xonotic-stage2-causal-qa-v8"
                if is_v8
                else "xonotic-stage2-causal-qa-v7"
            )
        ),
        "episode_id": scenario["episode_id"],
        "counterfactual_group_id": scenario[
            "counterfactual_group_id"
        ],
        "exogenous_contract_sha256": scenario[
            "exogenous_contract_sha256"
        ],
        "aim_policy": (
            str(design["aim_policy"])
            if is_v9
            else STOCHASTIC_AIM_POLICY
        ),
        "interaction_channel": "primary",
        "secondary_mechanism": None,
        "shot_error_program": (
            "weapon_conditioned_humanized_and_stochastic"
            if is_v9
            else "random_view_independent_fire"
        ),
        "shot_error_checks": {
            "outcome_not_used_for_admission": True
        },
        "initial_screen": {
            "planned": scenario.get("initial_screen_design"),
            "actual": {
                "render_visible": bool(visible[0]),
                "screen_x_normalized": float(
                    relations.iloc[0]["screen_x_normalized"]
                ),
                "screen_y_normalized": float(
                    relations.iloc[0]["screen_y_normalized"]
                ),
            },
            "checks": {"initial_visible": bool(visible[0])},
        },
        "actual_outcome": actual_outcome_bin(qa),
        "actual_distance_bin": distance_bin(reference_distance),
        "reference_frame": reference_frame,
        "reference_distance": reference_distance,
        "visible_frames": int(visible.sum()),
        "centered_frames": int(centered.sum()),
        "fire_frames": fire_frames,
        "angular_error_at_fire_deg": fire_error,
        "random_aim": {
            "program": (
                design["weapon_balanced_aim_program"]
                if is_v9
                else design["random_aim_program"]
            ),
            "maximum_yaw_step_deg": float(
                np.max(np.abs(yaw_step))
            ),
            "maximum_pitch_step_deg": float(
                np.max(np.abs(pitch_step))
            ),
            "yaw_direction_reversals": direction_reversals(
                yaw_step
            ),
            "pitch_direction_reversals": direction_reversals(
                pitch_step
            ),
            "checks": action_checks,
        },
        "fire_program": {
            "program": program,
            "input_active_frames": int(actual_primary.sum()),
            "input_rising_edges": rising_edges,
            "authoritative_fire_frames": fire_frames,
            "authoritative_fire_event_count": len(fire_events),
            "checks": fire_checks,
            "passed": all(fire_checks.values()),
        },
        "per_shot": {
            "rows": len(shots),
            "hit_count": int(shot_hits.sum()),
            "miss_count": int((~shot_hits).sum()),
            "target_entity": enemy_entity,
            "target_hit_count": len(target_hit_ids),
            "target_miss_count": len(target_negative_fire_ids),
            "target_hit_fire_event_ids": sorted(target_hit_ids),
            "unresolved_target_fire_event_ids": sorted(
                unresolved_target_fire_ids
            ),
            "outcome_observation_ticks": (
                PROJECTILE_OUTCOME_OBSERVATION_TICKS
                if str(scenario["weapon"])
                in PROJECTILE_PRIMARY_WEAPONS
                else 0
            ),
            "checks": shot_checks,
            "target_label_checks": target_label_checks,
            "passed": all(shot_checks.values()),
        },
        "enemy_random_policy": {
            "segment_count": segment_count,
            "hold_frames": hold_frames,
            "hop_frames": hop_frames,
            "moving_frames": int((horizontal_speed > 1.0).sum()),
            "horizontal_speed_std": float(
                np.std(horizontal_speed)
            ),
            "policy_explanation_checks": (
                policy_explanation_checks
            ),
            "policy_progress_max_error": (
                policy_progress_max_error
            ),
            "checks": enemy_checks,
            "passed": all(enemy_checks.values()),
        },
        "player_path": {
            "program": (
                scenario.get("prefrozen_trace_source")
                if is_v9
                else (
                    design.get("player_movement_program")
                    if is_v8
                    else "stationary"
                )
            ),
            "motion_class": (
                "certified_prefrozen_trace_replay"
                if is_v9
                else (
                    "prefrozen_continuous_movement"
                    if is_v8
                    else "stationary"
                )
            ),
            "active_frames": int((movement > 0.05).sum()),
            "horizontal_path_length": float(
                state_horizontal_steps.sum()
            ),
            "maximum_horizontal_displacement": float(
                np.max(horizontal_displacements)
            ),
            "final_horizontal_displacement": float(
                horizontal_displacements[-1]
            ),
            "longest_ungrounded_ticks": longest_ungrounded,
            "maximum_airborne_drop": maximum_airborne_drop,
            "player_health_policy": player_health_policy,
            "minimum_player_health": float(np.min(health)),
            "movement_blockage": blockage,
            "trace_replay": trace_replay_metrics,
            "checks": (
                player_motion_checks
                if is_v8 or is_v9
                else {
                    "stationary_player": not (
                        movement > 1e-6
                    ).any()
                    and not jump.any()
                }
            ),
            "passed": (
                all(player_motion_checks.values())
                if is_v8 or is_v9
                else not (movement > 1e-6).any()
                and not jump.any()
            ),
        },
        "event_counts": {
            name: int(qa["events"].get(name, 0))
            for name in (
                "fire_count",
                "impact_count",
                "damage_count",
                "death_count",
                "direct_count",
                "splash_count",
                "pellet_count",
            )
        },
        "hard_gates": hard_gates,
        "passed": all(hard_gates.values()),
    }


def causal_metrics(
    package: Path, scenario: dict[str, Any], qa: dict[str, Any]
) -> dict[str, Any]:
    validate_scenario_contract(scenario)
    if scenario.get("schema_version") in {
        SCENARIO_SCHEMA_V7,
        SCENARIO_SCHEMA_V8,
        SCENARIO_SCHEMA_V9,
    }:
        return causal_metrics_v7(package, scenario, qa)
    design = scenario["causal_design"]
    policy = str(design["aim_policy"])
    relations = pd.read_parquet(
        package / "target_relations.parquet"
    ).sort_values("frame_index")
    actions = pd.read_parquet(
        package / "model_actions.parquet"
    ).sort_values("frame_index")
    events = pd.read_parquet(package / "events.parquet")
    states = pd.read_parquet(package / "states.parquet").sort_values(
        "server_tick"
    )

    visible = (
        relations["render_visible_proxy"].fillna(False).to_numpy(bool)
    )
    angular_error = pd.to_numeric(
        relations["angular_error_deg"], errors="coerce"
    ).to_numpy(np.float64)
    centered = visible & np.isfinite(angular_error) & (
        angular_error <= TARGET_CENTER_THRESHOLD_DEG
    )
    is_v3 = scenario.get("schema_version") == SCENARIO_SCHEMA_V3
    is_v4 = scenario.get("schema_version") == SCENARIO_SCHEMA_V4
    is_v5 = scenario.get("schema_version") == SCENARIO_SCHEMA_V5
    is_v6 = scenario.get("schema_version") == SCENARIO_SCHEMA_V6
    is_v3_plus = is_v3 or is_v4 or is_v5 or is_v6
    is_v4_plus = is_v4 or is_v5 or is_v6
    treatment_relations = (
        prescribed_treatment_relations(
            package, scenario, relations
        )
        if is_v3_plus
        else {
            "reference_kind": "realized_target_relation",
            "los_reference": "realized_target_relation",
            "visible": visible,
            "angular_error_deg": angular_error,
            "centered": centered,
        }
    )
    policy_visible = np.asarray(
        treatment_relations["visible"], dtype=bool
    )
    policy_angular_error = np.asarray(
        treatment_relations["angular_error_deg"],
        dtype=np.float64,
    )
    policy_centered = np.asarray(
        treatment_relations["centered"], dtype=bool
    )
    right_x = pd.to_numeric(
        actions["j_right_x"], errors="coerce"
    ).to_numpy(np.float64)
    right_y = pd.to_numeric(
        actions["j_right_y"], errors="coerce"
    ).to_numpy(np.float64)
    absolute_right_active = np.hypot(right_x, right_y) > 1e-6
    base_right_x = np.zeros(len(actions), dtype=np.float64)
    base_right_y = np.zeros(len(actions), dtype=np.float64)
    if (
        is_v3_plus
        and str(design["base_player_program"])
        == "certified_route_replay"
    ):
        base_rows, _, _ = player_path_artifacts(scenario)
        source_ticks = pd.to_numeric(
            actions["source_action_tick"], errors="raise"
        ).astype(np.int64)
        base_right_x = np.asarray(
            [
                -float(base_rows[int(tick)]["yaw_delta"])
                / capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
                for tick in source_ticks
            ],
            dtype=np.float64,
        )
        base_right_y = np.asarray(
            [
                float(base_rows[int(tick)]["pitch_delta"])
                / capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
                for tick in source_ticks
            ],
            dtype=np.float64,
        )
    aim_overlay_x = right_x - base_right_x
    aim_overlay_y = right_y - base_right_y
    right_active = (
        np.hypot(aim_overlay_x, aim_overlay_y) > 1e-5
        if is_v3_plus
        else absolute_right_active
    )
    primary_active = (
        pd.to_numeric(actions["right_trigger"], errors="coerce")
        .to_numpy(np.float64)
        > 0.5
    )
    secondary_active = (
        pd.to_numeric(actions["left_trigger"], errors="coerce")
        .to_numpy(np.float64)
        > 0.5
    )
    left_x = pd.to_numeric(
        actions["j_left_x"], errors="coerce"
    ).to_numpy(np.float64)
    left_y = pd.to_numeric(
        actions["j_left_y"], errors="coerce"
    ).to_numpy(np.float64)
    left_active = np.hypot(left_x, left_y) > 1e-6
    jump_active = (
        pd.to_numeric(actions["south"], errors="coerce")
        .to_numpy(np.float64)
        > 0.5
    )
    unused_buttons = actions[
        [
            "east",
            "north",
            "left_shoulder",
            "right_shoulder",
            "west",
        ]
    ].to_numpy(np.float64)

    event_names = (
        events["event"].astype(str)
        if "event" in events
        else pd.Series(dtype=str)
    )
    fire_events = events[event_names == "fire"]
    fire_secondary = pd.to_numeric(
        fire_events.get(
            "secondary",
            pd.Series(np.zeros(len(fire_events)), index=fire_events.index),
        ),
        errors="coerce",
    ).fillna(-1).to_numpy(np.int64)
    fire_ticks = sorted(
        int(value)
        for value in fire_events.get(
            "server_tick", pd.Series(dtype=np.int64)
        ).tolist()
    )
    fire_frames = [
        tick - capture.WARMUP_TICKS
        for tick in fire_ticks
        if capture.WARMUP_TICKS <= tick < capture.TOTAL_TICKS
    ]
    at_fire_errors = [
        float(angular_error[index])
        for index in fire_frames
        if 0 <= index < len(angular_error)
        and math.isfinite(float(angular_error[index]))
    ]
    treatment_at_fire_errors = [
        float(policy_angular_error[index])
        for index in fire_frames
        if 0 <= index < len(policy_angular_error)
        and math.isfinite(float(policy_angular_error[index]))
    ]
    realized_miss_vectors_at_fire: list[dict[str, Any]] = []
    for index in fire_frames:
        if not 0 <= index < len(relations):
            continue
        relation = relations.iloc[index]
        depth = float(relation["camera_depth"])
        lateral = float(relation["camera_lateral"])
        vertical = float(relation["camera_vertical"])
        if not all(
            math.isfinite(value)
            for value in (depth, lateral, vertical)
        ):
            continue
        safe_depth = max(depth, 1e-12)
        horizontal = math.degrees(math.atan2(lateral, safe_depth))
        vertical_angle = math.degrees(
            math.atan2(vertical, safe_depth)
        )
        magnitude = math.hypot(horizontal, vertical_angle)
        realized_miss_vectors_at_fire.append(
            {
                "frame_index": int(index),
                "horizontal_deg": float(horizontal),
                "vertical_deg": float(vertical_angle),
                "magnitude_deg": float(magnitude),
                "direction_sector": miss_direction_sector(
                    -horizontal, vertical_angle
                ),
                "magnitude_bin": realized_miss_magnitude_bin(
                    magnitude
                ),
            }
        )
    first_response = _first_index(right_active)
    first_acquisition = _first_index(centered)
    first_treatment_acquisition = _first_index(policy_centered)
    schedule = design.get("aim_schedule") or {}
    if (is_v5 or is_v6) and policy == "track_loss_reacquire":
        reacquisition_minimum = int(
            schedule["tracking_pause_end_output_tick"]
        )
    elif is_v3_plus and policy == "track_loss_reacquire":
        reacquisition_minimum = int(
            schedule["lost_hold_end_output_tick"]
        )
    else:
        reacquisition_minimum = 200
    first_reacquisition = _first_index(
        centered, minimum=reacquisition_minimum
    )
    first_treatment_reacquisition = _first_index(
        policy_centered, minimum=reacquisition_minimum
    )
    first_fire = min(fire_frames) if fire_frames else None
    acquisition_start = int(design["acquisition_start_output_tick"])
    shot_schedule = (
        design["shot_error_schedule"]
        if is_v4_plus
        else shot_error_schedule("none")
    )
    shot_program = str(shot_schedule["program"])

    if policy == "visible_no_response":
        policy_checks = {
            "visible_before_intervention": int(
                policy_visible[:96].sum()
            )
            >= 16,
            "no_aim_response": first_response is None,
            "no_model_fire": not primary_active.any()
            and not secondary_active.any(),
            "no_authoritative_fire": not fire_ticks,
        }
    elif policy == "delayed_acquisition":
        fire_before_acquisition_programs = {
            "timing_early_acquisition",
            "spatial_undershoot_then_acquire",
        }
        fire_timing_check = (
            first_fire is not None
            and first_treatment_acquisition is not None
            and (
                (
                    shot_program in fire_before_acquisition_programs
                    and first_fire < first_treatment_acquisition
                )
                or (
                    shot_program not in fire_before_acquisition_programs
                    and first_fire > first_treatment_acquisition
                )
            )
        )
        policy_checks = {
            "visible_during_delay": int(
                policy_visible[:acquisition_start].sum()
            )
            >= 16,
            "response_delayed": first_response is not None
            and first_response >= acquisition_start,
            "acquired_after_delay": (
                first_treatment_acquisition is not None
                and first_treatment_acquisition
                >= acquisition_start
            ),
            "declared_fire_timing": fire_timing_check,
        }
    elif policy == "pass_offset":
        target_passed = bool(
            np.isfinite(policy_angular_error).any()
            and np.nanmin(policy_angular_error) <= 4.0
        )
        if is_v6:
            requires_target_pass = bool(
                schedule["requires_target_pass"]
            )
            planned_screen_angle = math.degrees(
                math.atan2(
                    float(schedule["fire_pitch_offset_deg"]),
                    -float(schedule["fire_yaw_offset_deg"]),
                )
            )
            realized_screen_angle = (
                math.degrees(
                    math.atan2(
                        float(
                            realized_miss_vectors_at_fire[0][
                                "vertical_deg"
                            ]
                        ),
                        float(
                            realized_miss_vectors_at_fire[0][
                                "horizontal_deg"
                            ]
                        ),
                    )
                )
                if realized_miss_vectors_at_fire
                else None
            )
            direction_error = (
                abs(
                    angle_delta(
                        planned_screen_angle,
                        realized_screen_angle,
                    )
                )
                if realized_screen_angle is not None
                else None
            )
            policy_checks = {
                "declared_pass_geometry": (
                    target_passed if requires_target_pass else True
                ),
                "two_dimensional_fire_offset": bool(
                    treatment_at_fire_errors
                )
                and min(treatment_at_fire_errors)
                >= float(schedule["minimum_fire_error_deg"]),
                "realized_direction_near_declared": (
                    direction_error is not None
                    and direction_error <= 45.0
                ),
                "authoritative_fire": bool(fire_ticks),
            }
        elif is_v4_plus and shot_program == "none":
            policy_checks = {
                "target_passed": target_passed,
                "centered_fire_after_pass": bool(
                    treatment_at_fire_errors
                )
                and max(treatment_at_fire_errors) <= 3.0,
                "authoritative_fire": bool(fire_ticks),
            }
        elif is_v4_plus and shot_program in {
            "spatial_persistent",
            "timing_early_acquisition",
        }:
            policy_checks = {
                "offset_or_early_pass_treatment": True,
                "authoritative_fire": bool(fire_ticks),
            }
        else:
            policy_checks = {
                "target_passed": target_passed,
                "fire_offset": bool(treatment_at_fire_errors)
                and min(treatment_at_fire_errors) >= 6.0,
                "authoritative_fire": bool(fire_ticks),
            }
    elif policy == "track_loss_reacquire":
        if is_v5 or is_v6:
            acquisition_end = int(
                schedule["acquisition_end_output_tick"]
            )
            centered_hold_end = int(
                schedule["centered_hold_end_output_tick"]
            )
            pause_end = int(
                schedule["tracking_pause_end_output_tick"]
            )
            reacquisition_end = int(
                schedule["reacquisition_end_output_tick"]
            )
            acquired_before_loss = bool(
                int(
                    policy_centered[
                        acquisition_end:centered_hold_end
                    ].sum()
                )
                >= int(
                    schedule[
                        "minimum_centered_before_pause_frames"
                    ]
                )
            )
            loss_frames = int(
                (
                    ~policy_centered[
                        centered_hold_end:pause_end
                    ]
                ).sum()
            )
            lost_after_acquisition = (
                loss_frames >= int(schedule["minimum_loss_frames"])
            )
        elif is_v3_plus:
            acquisition_end = int(
                schedule["acquisition_end_output_tick"]
            )
            centered_hold_end = int(
                schedule["centered_hold_end_output_tick"]
            )
            loss_end = int(schedule["loss_end_output_tick"])
            lost_hold_end = int(
                schedule["lost_hold_end_output_tick"]
            )
            acquired_before_loss = bool(
                policy_centered[
                    acquisition_end:centered_hold_end
                ].any()
            )
            lost_after_acquisition = bool(
                (
                    ~policy_centered[
                        loss_end:lost_hold_end
                    ]
                ).all()
            )
        else:
            acquired_before_loss = bool(
                policy_centered[48:120].any()
            )
            lost_after_acquisition = bool(
                (~policy_centered[140:200]).any()
            )
        if is_v4 and shot_program == "timing_loss_window":
            declared_fire_phase = (
                first_fire is not None
                and loss_end <= first_fire < lost_hold_end
            )
        elif (
            is_v4
            and shot_program == "timing_reacquisition_lag"
        ):
            declared_fire_phase = (
                first_fire is not None
                and lost_hold_end
                <= first_fire
                < int(schedule["reacquisition_end_output_tick"])
            )
        else:
            declared_fire_phase = (
                first_fire is not None
                and first_treatment_reacquisition is not None
                and first_fire > first_treatment_reacquisition
            )
        policy_checks = {
            "acquired_before_loss": acquired_before_loss,
            "lost_after_acquisition": lost_after_acquisition,
            "reacquired": (
                first_treatment_reacquisition is not None
                and (
                    not (is_v5 or is_v6)
                    or first_treatment_reacquisition
                    <= reacquisition_end + 24
                )
            ),
            "declared_fire_phase": declared_fire_phase,
        }
    elif policy == "sustained_tracking":
        if is_v3_plus:
            tracking_start = int(
                schedule["acquisition_end_output_tick"]
            )
            tracking_end = (
                int(schedule["pre_fire_tracking_end_output_tick"])
                if is_v6
                else len(policy_visible)
            )
            visible_tracking = policy_visible[
                tracking_start:tracking_end
            ]
            if is_v5 or is_v6:
                centered_tracking = (
                    policy_visible
                    & np.isfinite(policy_angular_error)
                    & (
                        policy_angular_error
                        <= float(
                            schedule[
                                "tracking_error_threshold_deg"
                            ]
                        )
                    )
                )[tracking_start:tracking_end]
            else:
                centered_tracking = policy_centered[tracking_start:]
            visible_count = int(visible_tracking.sum())
            centered_given_visible = (
                float(
                    centered_tracking[visible_tracking].mean()
                )
                if visible_count
                else 0.0
            )
            policy_checks = {
                "early_acquisition": (
                    first_treatment_acquisition is not None
                )
                and first_treatment_acquisition
                <= int(schedule["acquisition_end_output_tick"]) + 24,
                "visible_tracking_support": visible_count
                >= int(
                    schedule["minimum_visible_tracking_frames"]
                ),
                "sustained_centering_given_visible": (
                    centered_given_visible
                    >= float(
                        schedule[
                            "minimum_centered_given_visible_fraction"
                        ]
                    )
                ),
                "fire_after_acquisition": first_fire is not None
                and first_treatment_acquisition is not None
                and first_fire > first_treatment_acquisition,
            }
        else:
            tracking_window = policy_centered[64:]
            policy_checks = {
                "early_acquisition": (
                    first_treatment_acquisition is not None
                )
                and first_treatment_acquisition <= 80,
                "sustained_centering": bool(len(tracking_window))
                and float(tracking_window.mean()) >= 0.75,
                "fire_after_acquisition": first_fire is not None
                and first_treatment_acquisition is not None
                and first_fire > first_treatment_acquisition,
            }
    else:
        raise AssertionError(policy)

    if is_v4_plus:
        minimum_fire_error = float(
            shot_schedule["minimum_error_at_fire_deg"]
        )
        expected_center_before = shot_schedule[
            "expected_center_before_first_fire"
        ]
        expected_acquisition_after = shot_schedule[
            "expected_acquisition_after_first_fire"
        ]
        center_before = (
            bool(policy_centered[:first_fire].any())
            if first_fire is not None
            else False
        )
        acquisition_after = (
            bool(policy_centered[first_fire + 1 :].any())
            if first_fire is not None
            else False
        )
        shot_error_checks = {
            "program_declared": shot_program
            in SHOT_ERROR_PROGRAMS,
            "fire_error": (
                shot_program == "none"
                or (
                    bool(treatment_at_fire_errors)
                    and min(treatment_at_fire_errors)
                    >= minimum_fire_error
                )
            ),
            "center_before_fire": (
                expected_center_before is None
                or center_before is expected_center_before
            ),
            "acquisition_after_fire": (
                expected_acquisition_after is None
                or acquisition_after is expected_acquisition_after
            ),
        }
        screen_design = scenario["initial_screen_design"]
        initial = relations.iloc[0]
        initial_x = float(initial["screen_x_normalized"])
        initial_y = float(initial["screen_y_normalized"])
        initial_visible = bool(initial["render_visible_proxy"])
        horizontal = str(screen_design["screen_horizontal"])
        vertical = str(screen_design["screen_vertical"])
        horizontal_match = {
            "left": initial_x >= 0.08,
            "center": abs(initial_x) <= 0.08,
            "right": initial_x <= -0.08,
        }[horizontal]
        vertical_match = {
            "upper": initial_y >= 0.04,
            "center": abs(initial_y) <= 0.07,
            "lower": initial_y <= -0.04,
        }[vertical]
        initial_screen_checks = {
            "visibility": initial_visible
            is bool(
                screen_design["expected_visible_at_output_start"]
            ),
            "horizontal": horizontal_match,
            "vertical": vertical_match,
        }
    else:
        shot_error_checks = {"legacy_contract": True}
        initial_x = float(relations.iloc[0]["screen_x_normalized"])
        initial_y = float(relations.iloc[0]["screen_y_normalized"])
        initial_visible = bool(
            relations.iloc[0]["render_visible_proxy"]
        )
        initial_screen_checks = {"legacy_contract": True}

    event_metrics = qa["events"]
    declared_firing = policy in FIRING_POLICIES
    is_v2 = scenario.get("schema_version") in {
        SCENARIO_SCHEMA_V2,
        SCENARIO_SCHEMA_V3,
        SCENARIO_SCHEMA_V4,
        SCENARIO_SCHEMA_V5,
        SCENARIO_SCHEMA_V6,
    }
    if declared_firing:
                                                                         
                                                                               
                                                            
        event_chain = int(event_metrics.get("fire_count", 0)) >= 1
        if not is_v2:
            event_chain = (
                event_chain
                and int(event_metrics.get("impact_count", 0)) >= 1
            )
    else:
        event_chain = int(event_metrics.get("fire_count", 0)) == 0

    channel = str(design["interaction_channel"])
    secondary_mechanism = design.get("secondary_mechanism")
    if not declared_firing:
        channel_checks = {
            "no_primary_input": not primary_active.any(),
            "no_secondary_input": not secondary_active.any(),
        }
    elif channel == "primary":
        channel_checks = {
            "primary_input": bool(primary_active.any()),
            "secondary_released": not secondary_active.any(),
            "primary_fire_event": bool(len(fire_secondary))
            and bool((fire_secondary == 0).any()),
        }
    elif secondary_mechanism == "devastator_remote_detonation":
        channel_checks = {
            "launch_primary_input": bool(primary_active.any()),
            "remote_secondary_input": bool(secondary_active.any()),
            "primary_launch_event": bool(len(fire_secondary))
            and bool((fire_secondary == 0).any()),
        }
    elif scenario.get("weapon") == "MachineGun":
                                                                          
                                                                           
                                                                             
                                                                
        requested_bursts = sum(
            bool(
                secondary_active[index]
                and (
                    index == 0
                    or not secondary_active[index - 1]
                )
            )
            for index in range(len(secondary_active))
        )
        channel_checks = {
            "primary_released": not primary_active.any(),
            "secondary_burst_input": bool(secondary_active.any()),
            "stock_burst_primary_deathtype": (
                bool(len(fire_secondary))
                and bool((fire_secondary == 0).all())
            ),
            "three_fire_events_per_burst": (
                len(fire_secondary) == requested_bursts * 3
            ),
        }
    else:
        channel_checks = {
            "primary_released": not primary_active.any(),
            "secondary_input": bool(secondary_active.any()),
            "secondary_fire_event": bool(len(fire_secondary))
            and bool((fire_secondary == 1).any()),
        }
    if is_v6:
        fire_program = design["fire_program"]
        expected_primary = np.asarray(
            [
                bool(fire_program_active(fire_program, tick))
                for tick in range(capture.OUTPUT_TICKS)
            ],
            dtype=bool,
        )
        windows = fire_program["windows"]
        input_rising_edges = int(
            sum(
                bool(
                    primary_active[index]
                    and (
                        index == 0
                        or not primary_active[index - 1]
                    )
                )
                for index in range(len(primary_active))
            )
        )
        actual_fire_events = len(fire_frames)
        minimum_fire_events = int(
            fire_program["expected_min_fire_events"]
        )
        maximum_fire_events = int(
            fire_program["expected_max_fire_events"]
        )
        first_window_start = (
            int(windows[0]["start_output_tick"])
            if windows
            else None
        )
        last_window_end = (
            int(windows[-1]["start_output_tick"])
            + int(windows[-1]["duration_ticks"])
            if windows
            else None
        )
        fire_program_checks = {
            "requested_primary_windows_exact": bool(
                np.array_equal(primary_active, expected_primary)
            ),
            "secondary_released": not secondary_active.any(),
            "input_rising_edges_exact": input_rising_edges
            == len(windows),
            "authoritative_event_count_in_bounds": (
                minimum_fire_events
                <= actual_fire_events
                <= maximum_fire_events
            ),
            "multiple_fire_events_realized": (
                not fire_program["requires_multiple_fire_events"]
                or actual_fire_events >= 2
            ),
            "qa_event_count_matches_rows": int(
                event_metrics.get("fire_count", -1)
            )
            == actual_fire_events,
            "events_not_before_program": (
                not fire_frames
                or (
                    first_window_start is not None
                    and min(fire_frames) >= first_window_start
                )
            ),
            "events_within_refire_grace": (
                not fire_frames
                or (
                    last_window_end is not None
                    and max(fire_frames)
                    <= min(
                        capture.OUTPUT_TICKS - 1,
                        last_window_end + 96,
                    )
                )
            ),
        }
        fire_program_metrics = {
            "program": fire_program,
            "input_active_frames": int(primary_active.sum()),
            "input_rising_edges": input_rising_edges,
            "authoritative_fire_frames": fire_frames,
            "authoritative_fire_event_count": actual_fire_events,
            "checks": fire_program_checks,
            "passed": all(fire_program_checks.values()),
        }
    else:
        fire_program_metrics = {
            "program": None,
            "checks": {"legacy_contract": True},
            "passed": True,
        }
    reference_frame = (
        first_fire
        if first_fire is not None
        else _first_index(visible)
    )
    reference_distance = None
    if reference_frame is not None:
        value = float(
            pd.to_numeric(
                relations.iloc[reference_frame]["distance_3d"],
                errors="coerce",
            )
        )
        reference_distance = value if math.isfinite(value) else None

    player_program = str(design["base_player_program"])
    player_path_metrics: dict[str, Any]
    if player_program == "certified_route_replay":
        _, reference_states, route_record = player_path_artifacts(
            scenario
        )
        reference_output = reference_states[
            reference_states["server_tick"].astype(int)
            >= capture.WARMUP_TICKS
        ].sort_values("server_tick")
        actual_output = states[
            states["server_tick"].astype(int)
            >= capture.WARMUP_TICKS
        ].sort_values("server_tick")
        reference_origins = np.asarray(
            reference_output["pre.origin"].tolist(),
            dtype=np.float64,
        )
        actual_origins = np.asarray(
            actual_output["pre.origin"].tolist(),
            dtype=np.float64,
        )
        position_error = np.linalg.norm(
            actual_origins - reference_origins, axis=1
        )
        displacement = np.linalg.norm(
            actual_origins - actual_origins[0], axis=1
        )
        path_source = scenario.get("player_path_source") or {}
        position_error_p95_limit = float(
            path_source.get(
                "player_path_position_error_p95_max", 8.0
            )
        )
        position_error_max_limit = float(
            path_source.get(
                "player_path_position_error_max_max", 32.0
            )
        )
        player_path_metrics = {
            "program": player_program,
            "motion_class": design.get("player_motion_class"),
            "route_id": route_record["route_id"],
            "reference_rows": len(reference_origins),
            "actual_rows": len(actual_origins),
            "position_error_p95": float(
                np.quantile(position_error, 0.95)
            ),
            "position_error_max": float(position_error.max()),
            "position_error_p95_limit": (
                position_error_p95_limit
            ),
            "position_error_max_limit": position_error_max_limit,
            "maximum_displacement": float(displacement.max()),
            "model_movement_frames": int(left_active.sum()),
            "model_jump_frames": int(jump_active.sum()),
            "passed": (
                len(reference_origins)
                == len(actual_origins)
                == capture.OUTPUT_TICKS
                and float(np.quantile(position_error, 0.95))
                <= position_error_p95_limit
                and float(position_error.max())
                <= position_error_max_limit
                and float(displacement.max()) >= 64.0
                and bool(left_active.any())
                and (
                    int(
                        (scenario.get("player_path_source") or {}).get(
                            "base_jump_ticks", 0
                        )
                    )
                    == 0
                    or bool(jump_active.any())
                )
            ),
        }
    else:
        player_path_metrics = {
            "program": player_program,
            "motion_class": "stationary",
            "model_movement_frames": int(left_active.sum()),
            "model_jump_frames": int(jump_active.sum()),
            "passed": not left_active.any() and not jump_active.any(),
        }

    if is_v5 or is_v6:
        profile = design["aim_motor_profile"]
        output_ticks = np.arange(len(actions), dtype=np.int64)
        response_start = schedule.get("response_start_output_tick")
        motor_active = (
            np.zeros(len(actions), dtype=bool)
            if response_start is None
            else output_ticks > int(response_start)
        )
        yaw_step = (
            -right_x
            * capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
        )
        pitch_step = (
            right_y
            * capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
        )
        active_indices = np.flatnonzero(motor_active)
        if len(active_indices):
            active_yaw_step = yaw_step[active_indices]
            active_pitch_step = pitch_step[active_indices]
            maximum_yaw_speed = float(
                np.max(np.abs(active_yaw_step))
            )
            maximum_pitch_speed = float(
                np.max(np.abs(active_pitch_step))
            )
            maximum_yaw_accel = float(
                np.max(np.abs(np.diff(active_yaw_step)))
            )
            maximum_pitch_accel = float(
                np.max(np.abs(np.diff(active_pitch_step)))
            )
        else:
            maximum_yaw_speed = maximum_pitch_speed = 0.0
            maximum_yaw_accel = maximum_pitch_accel = 0.0

        tracking_support = np.zeros(len(actions), dtype=bool)
        if policy == "delayed_acquisition":
            tracking_support[
                int(schedule["settle_end_output_tick"]) :
            ] = True
        elif policy == "pass_offset":
            tracking_support[
                int(schedule["response_start_output_tick"]) :
            ] = True
        elif policy == "track_loss_reacquire":
            tracking_support[
                int(schedule["acquisition_end_output_tick"]) :
                int(schedule["centered_hold_end_output_tick"])
            ] = True
            tracking_support[
                int(schedule["reacquisition_end_output_tick"]) :
            ] = True
        elif policy == "sustained_tracking":
            tracking_support[
                int(schedule["acquisition_end_output_tick"]) :
            ] = True
        exact_lock_support = (
            tracking_support
            & policy_visible
            & np.isfinite(policy_angular_error)
        )
        exact_lock_frames = int(
            (
                exact_lock_support
                & (
                    policy_angular_error
                    <= float(
                        profile[
                            "exact_lock_error_threshold_deg"
                        ]
                    )
                )
            ).sum()
        )
        exact_lock_support_frames = int(exact_lock_support.sum())
        exact_lock_fraction = (
            float(exact_lock_frames / exact_lock_support_frames)
            if exact_lock_support_frames
            else 0.0
        )
        tolerance = 2e-5
        motor_checks = {
            "yaw_speed_bounded": maximum_yaw_speed
            <= float(profile["max_yaw_speed_deg_per_tick"])
            + tolerance,
            "pitch_speed_bounded": maximum_pitch_speed
            <= float(profile["max_pitch_speed_deg_per_tick"])
            + tolerance,
            "yaw_acceleration_bounded": maximum_yaw_accel
            <= float(profile["max_yaw_accel_deg_per_tick2"])
            + tolerance,
            "pitch_acceleration_bounded": maximum_pitch_accel
            <= float(profile["max_pitch_accel_deg_per_tick2"])
            + tolerance,
            "exact_lock_fraction_bounded": (
                not exact_lock_support_frames
                or exact_lock_fraction
                <= float(profile["maximum_exact_lock_fraction"])
            ),
        }
        motor_metrics = {
            "profile": profile,
            "active_frames": int(motor_active.sum()),
            "maximum_yaw_speed_deg_per_tick": maximum_yaw_speed,
            "maximum_pitch_speed_deg_per_tick": maximum_pitch_speed,
            "maximum_yaw_accel_deg_per_tick2": maximum_yaw_accel,
            "maximum_pitch_accel_deg_per_tick2": maximum_pitch_accel,
            "exact_lock_support_frames": exact_lock_support_frames,
            "exact_lock_frames": exact_lock_frames,
            "exact_lock_fraction": exact_lock_fraction,
            "checks": motor_checks,
            "passed": all(motor_checks.values()),
        }
    else:
        motor_metrics = {
            "profile": None,
            "checks": {"legacy_contract": True},
            "passed": True,
        }

    hard_gates = {
        "stage2_causal_rows_exact": len(relations)
        == len(actions)
        == capture.OUTPUT_TICKS,
        "stage2_causal_exogenous_contract": (
            scenario["exogenous_contract_sha256"]
            == exogenous_contract_sha256(scenario)
        ),
        "stage2_causal_action_namespace": (
            not np.asarray(unused_buttons).any()
        ),
        "stage2_causal_player_path": player_path_metrics["passed"],
        "stage2_causal_interaction_channel": all(
            channel_checks.values()
        ),
        "stage2_causal_target_visible": int(visible.sum()) >= 16,
        "stage2_causal_policy_realized": all(policy_checks.values()),
        "stage2_causal_shot_error_realized": all(
            shot_error_checks.values()
        ),
        "stage2_causal_initial_screen_realized": all(
            initial_screen_checks.values()
        ),
        "stage2_causal_aim_motor_realized": motor_metrics[
            "passed"
        ],
        "stage2_causal_fire_program_realized": (
            fire_program_metrics["passed"]
        ),
        "stage2_causal_treatment_realized": (
            bool(fire_ticks) == declared_firing
        ),
        "stage2_causal_event_chain": event_chain,
        "stage2_causal_actual_outcome_telemetry": (
            actual_outcome_bin(qa)
            in {"no_fire", "miss", "hit_survive", "kill"}
        ),
    }
    return {
        "schema_version": (
            "xonotic-stage2-causal-qa-v6"
            if is_v6
            else (
                "xonotic-stage2-causal-qa-v5"
                if is_v5
                else (
                    "xonotic-stage2-causal-qa-v4"
                    if is_v4
                    else (
                        "xonotic-stage2-causal-qa-v3"
                        if is_v3
                        else "xonotic-stage2-causal-qa-v1"
                    )
                )
            )
        ),
        "episode_id": scenario["episode_id"],
        "counterfactual_group_id": scenario[
            "counterfactual_group_id"
        ],
        "exogenous_contract_sha256": scenario[
            "exogenous_contract_sha256"
        ],
        "aim_policy": policy,
        "interaction_channel": design["interaction_channel"],
        "secondary_mechanism": secondary_mechanism,
        "shot_error_program": shot_program,
        "shot_error_checks": shot_error_checks,
        "initial_screen": {
            "planned": (
                scenario.get("initial_screen_design")
                if is_v4_plus
                else None
            ),
            "actual": {
                "render_visible": initial_visible,
                "screen_x_normalized": initial_x,
                "screen_y_normalized": initial_y,
            },
            "checks": initial_screen_checks,
        },
        "actual_outcome": actual_outcome_bin(qa),
        "actual_distance_bin": distance_bin(reference_distance),
        "reference_frame": reference_frame,
        "reference_distance": reference_distance,
        "visible_frames": int(visible.sum()),
        "centered_frames": int(centered.sum()),
        "centered_fraction": float(centered.mean()),
        "minimum_angular_error_deg": (
            float(np.nanmin(angular_error))
            if np.isfinite(angular_error).any()
            else None
        ),
        "first_aim_response_frame": first_response,
        "first_absolute_view_action_frame": _first_index(
            absolute_right_active
        ),
        "aim_overlay_active_frames": int(right_active.sum()),
        "aim_overlay_max_norm": float(
            np.hypot(aim_overlay_x, aim_overlay_y).max()
        ),
        "first_acquisition_frame": first_acquisition,
        "first_reacquisition_frame": first_reacquisition,
        "treatment_reference_kind": treatment_relations[
            "reference_kind"
        ],
        "treatment_los_reference": treatment_relations[
            "los_reference"
        ],
        "treatment_visible_frames": int(policy_visible.sum()),
        "treatment_centered_frames": int(
            policy_centered.sum()
        ),
        "treatment_centered_fraction": float(
            policy_centered.mean()
        ),
        "first_treatment_acquisition_frame": (
            first_treatment_acquisition
        ),
        "first_treatment_reacquisition_frame": (
            first_treatment_reacquisition
        ),
        "fire_frames": fire_frames,
        "angular_error_at_fire_deg": at_fire_errors,
        "treatment_angular_error_at_fire_deg": (
            treatment_at_fire_errors
        ),
        "realized_miss_vectors_at_fire": (
            realized_miss_vectors_at_fire
        ),
        "policy_checks": policy_checks,
        "channel_checks": channel_checks,
        "fire_program": fire_program_metrics,
        "aim_motor": motor_metrics,
        "player_path": player_path_metrics,
        "event_counts": {
            name: int(event_metrics.get(name, 0))
            for name in (
                "fire_count",
                "impact_count",
                "damage_count",
                "death_count",
                "direct_count",
                "splash_count",
                "pellet_count",
            )
        },
        "hard_gates": hard_gates,
        "passed": all(hard_gates.values()),
    }


def atomic_json(path: Path, payload: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_v3_aim_overlay(
    package: Path, scenario: dict[str, Any]
) -> dict[str, Any] | None:
    if scenario.get("schema_version") not in {
        SCENARIO_SCHEMA_V3,
        SCENARIO_SCHEMA_V4,
        SCENARIO_SCHEMA_V5,
        SCENARIO_SCHEMA_V6,
    }:
        return None
    actions = pd.read_parquet(
        package / "model_actions.parquet"
    ).sort_values("frame_index")
    source_ticks = pd.to_numeric(
        actions["source_action_tick"], errors="raise"
    ).astype(np.int64)
    base_right_x = np.zeros(len(actions), dtype=np.float64)
    base_right_y = np.zeros(len(actions), dtype=np.float64)
    if (
        str(scenario["causal_design"]["base_player_program"])
        == "certified_route_replay"
    ):
        base_rows, _, _ = player_path_artifacts(scenario)
        base_right_x = np.asarray(
            [
                -float(base_rows[int(tick)]["yaw_delta"])
                / capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
                for tick in source_ticks
            ],
            dtype=np.float64,
        )
        base_right_y = np.asarray(
            [
                float(base_rows[int(tick)]["pitch_delta"])
                / capture.MODEL_ACTION_VIEW_DEGREES_PER_TICK
                for tick in source_ticks
            ],
            dtype=np.float64,
        )
    applied_x = pd.to_numeric(
        actions["j_right_x"], errors="raise"
    ).to_numpy(np.float64)
    applied_y = pd.to_numeric(
        actions["j_right_y"], errors="raise"
    ).to_numpy(np.float64)
    overlay_x = applied_x - base_right_x
    overlay_y = applied_y - base_right_y
    schedule = scenario["causal_design"]["aim_schedule"]
    overlay_schema = (
        AIM_OVERLAY_SCHEMA_V4
        if scenario.get("schema_version") == SCENARIO_SCHEMA_V6
        else (
            AIM_OVERLAY_SCHEMA_V3
            if scenario.get("schema_version") == SCENARIO_SCHEMA_V5
            else (
                AIM_OVERLAY_SCHEMA_V2
                if scenario.get("schema_version") == SCENARIO_SCHEMA_V4
                else AIM_OVERLAY_SCHEMA
            )
        )
    )
    response_start = schedule.get("response_start_output_tick")
    output_ticks = source_ticks.to_numpy() - capture.WARMUP_TICKS
    shot_schedule = scenario["causal_design"].get(
        "shot_error_schedule"
    )
    declared_shot_error = (
        np.asarray(
            [
                shot_error_offsets(shot_schedule, int(tick))
                for tick in output_ticks
            ],
            dtype=np.float64,
        )
        if shot_schedule
        else np.zeros((len(actions), 2), dtype=np.float64)
    )
    window_active = (
        np.zeros(len(actions), dtype=bool)
        if response_start is None
        else output_ticks >= int(response_start)
    )
    frame = pd.DataFrame(
        {
            "schema_version": overlay_schema,
            "episode_id": scenario["episode_id"],
            "frame_index": pd.to_numeric(
                actions["frame_index"], errors="raise"
            ).astype(np.int64),
            "source_action_tick": source_ticks,
            "aim_policy": scenario["causal_design"]["aim_policy"],
            "base_view_yaw_offset_deg": float(
                scenario["causal_design"].get(
                    "base_view_yaw_offset_deg", 0.0
                )
            ),
            "base_view_pitch_offset_deg": float(
                scenario["causal_design"].get(
                    "base_view_pitch_offset_deg", 0.0
                )
            ),
            "aim_window_active": window_active,
            "reads_manifest_frozen_enemy_trajectory": (
                window_active
                & (
                    scenario["causal_design"]["aim_policy"]
                    != "visible_no_response"
                )
            ),
            "reads_live_enemy_state": False,
            "reads_live_player_state": False,
            "base_j_right_x": base_right_x,
            "base_j_right_y": base_right_y,
            "applied_j_right_x": applied_x,
            "applied_j_right_y": applied_y,
            "overlay_j_right_x": overlay_x,
            "overlay_j_right_y": overlay_y,
            "overlay_norm": np.hypot(overlay_x, overlay_y),
            "shot_error_program": (
                str(shot_schedule["program"])
                if shot_schedule
                else "legacy_v3"
            ),
            "aim_motor_profile_schema": (
                str(
                    scenario["causal_design"]
                    .get("aim_motor_profile", {})
                    .get("schema_version", "legacy")
                )
            ),
            "aim_motor_style": (
                str(
                    scenario["causal_design"]
                    .get("aim_motor_profile", {})
                    .get("style", "legacy")
                )
            ),
            "aim_motor_seed": int(
                scenario["causal_design"]
                .get("aim_motor_profile", {})
                .get("seed", -1)
            ),
            "declared_shot_error_yaw_deg": (
                declared_shot_error[:, 0]
            ),
            "declared_shot_error_pitch_deg": (
                declared_shot_error[:, 1]
            ),
            "namespace": "privileged_frozen_stage2_aim_overlay",
        }
    )
    temporary = package / (
        f".aim_overlay.parquet.tmp.{os.getpid()}"
    )
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, package / "aim_overlay.parquet")
    return {
        "schema_version": overlay_schema,
        "rows": len(frame),
        "sha256": capture.sha256_file(
            package / "aim_overlay.parquet"
        ),
        "active_frames": int(
            (frame["overlay_norm"] > 1e-5).sum()
        ),
        "live_reads": False,
    }


def complete_stage2_artifacts(
    result: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    if scenario.get("action_program") not in ACTION_PROGRAMS:
        return result
    package = Path(result["stage"]) / "package"
    qa_path = package / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    aim_overlay_artifact = write_v3_aim_overlay(
        package, scenario
    )
    metrics = causal_metrics(package, scenario, qa)
    if aim_overlay_artifact is not None:
        metrics["aim_overlay_artifact"] = aim_overlay_artifact
    qa["stage2_causal"] = metrics
    qa.setdefault("hard_gates", {}).update(metrics["hard_gates"])
    qa.setdefault("gates", {}).update(metrics["hard_gates"])
    qa["role_eligible"] = metrics["passed"]
    atomic_json(qa_path, qa)

    episode_path = package / "episode.json"
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    episode["stage2_causal"] = {
        "counterfactual_group_id": metrics[
            "counterfactual_group_id"
        ],
        "exogenous_contract_sha256": metrics[
            "exogenous_contract_sha256"
        ],
        "aim_policy": metrics["aim_policy"],
        "shot_error_program": metrics["shot_error_program"],
        "fire_program": metrics["fire_program"],
        "initial_screen": metrics["initial_screen"],
        "actual_outcome": metrics["actual_outcome"],
        "actual_distance_bin": metrics["actual_distance_bin"],
        "player_motion_class": metrics["player_path"].get(
            "motion_class"
        ),
    }
    atomic_json(episode_path, episode)
    atomic_json(package / "causal_interaction.json", metrics)
    result["qa"] = qa
    result["stage2_causal"] = metrics
    if not metrics["passed"]:
        failed = [
            name
            for name, passed in metrics["hard_gates"].items()
            if not passed
        ]
        raise capture.CaptureFailure(
            "stage2_causal_qa_failed",
            capture.canonical_json(
                {
                    "episode_id": scenario["episode_id"],
                    "failed": failed,
                    "policy_checks": metrics.get(
                        "policy_checks",
                        (metrics.get("player_path") or {}).get(
                            "checks", {}
                        ),
                    ),
                }
            ),
        )
    return result


capture.register_action_row_provider(
    "xonotic_stage2_causal",
    ACTION_PROGRAMS,
    causal_action_rows,
)
