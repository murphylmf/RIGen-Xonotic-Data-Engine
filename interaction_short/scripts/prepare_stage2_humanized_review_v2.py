                      
"""Build the bounded Stage-2 burst/miss-distribution review v2.

The cohort is intentionally non-training.  It reuses certified moving-target
geometry, freezes every open-loop action candidate in the manifest, and
rejects candidates that fail static policy, motor, fire-window, or miss-vector
checks.  Runtime telemetry remains authoritative for realized fire counts,
miss direction, hit/miss/kill outcome, and final admission.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage2_humanized_review_v1 as review_v1              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
OUTPUT_ROOT = ROOT / "manifests/stage2_humanized_review_v2"
GROUP_PREFIX = "s2humanv2"
SOURCE_COMMIT = "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
SHARD_COUNT = 4
MANIFEST_SCHEMA = "xonotic-stage2-humanized-review-manifest-v2"
DESIGN_SCHEMA = "xonotic-stage2-humanized-review-design-v2"
STATIC_CERTIFICATE_SCHEMA = (
    "xonotic-stage2-humanized-static-action-certificate-v2"
)
SELECTION_RULE = (
    "nine_weapon_fixed_geometry_groups_preregistered_fire_and_2d_miss_"
    "distribution_then_deterministic_static_candidate_certification_v2"
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
                                                                            
                                                                           
                                                                         
                                                                            
WEAPON_FIRE_FAMILY = {
    "Blaster": "repeat_hold",
    "Shotgun": "spaced_tap",
    "MachineGun": "rapid_auto",
    "Mortar": "spaced_tap",
    "Electro": "repeat_hold",
    "Crylink": "repeat_hold",
    "Vortex": "spaced_tap",
    "Hagar": "rapid_auto",
    "Devastator": "spaced_tap",
}
                                                                        
PRIMARY_REFIRE_TICKS = {
    "Blaster": 45,
    "Shotgun": 48,
    "MachineGun": 7,
    "Mortar": 52,
    "Electro": 39,
    "Crylink": 45,
    "Vortex": 96,
    "Hagar": 11,
    "Devastator": 71,
}
SOURCE_INDICES = (0, 2, 3, 5, 0, 2, 3, 5, 0)
INITIAL_CELLS = (
    ("upper_left", -24.0, 8.0),
    ("upper_right", 24.0, 8.0),
    ("lower_left", -24.0, -8.0),
    ("lower_right", 24.0, -8.0),
    ("left_center", -20.0, 0.0),
    ("right_center", 20.0, 0.0),
    ("upper_left", -20.0, 7.0),
    ("lower_right", 20.0, -7.0),
    ("left_center", -22.0, 0.0),
)
ARM_SPECS = (
    ("visible_no_response", "control"),
    ("delayed_acquisition", "main"),
    ("pass_offset", "a"),
    ("pass_offset", "b"),
    ("sustained_tracking", "main"),
    ("track_loss_reacquire", "main"),
)
FIRE_START = {
    ("delayed_acquisition", "main"): 184,
    ("pass_offset", "a"): 176,
    ("pass_offset", "b"): 192,
    ("sustained_tracking", "main"): 168,
    ("track_loss_reacquire", "main"): 264,
}
FIRING_CATEGORY_TARGET = {
    "single": 20,
    "short": 16,
    "complex": 9,
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


def screen_vector(
    sector: str, magnitude: float, angle_jitter_deg: float
) -> tuple[float, float]:
    """Return engine yaw/pitch for a screen-relative crosshair vector."""
    sector_index = causal.MISS_DIRECTION_SECTORS.index(sector)
    angle = math.radians(sector_index * 45.0 + angle_jitter_deg)
    screen_horizontal = magnitude * math.cos(angle)
    screen_vertical = magnitude * math.sin(angle)
                                                                              
    return -screen_horizontal, screen_vertical


def miss_treatment_specs() -> list[dict[str, Any]]:
    rng = random.Random(2026073002)
    sectors = list(causal.MISS_DIRECTION_SECTORS) * 2 + [
        "right",
        "left",
    ]
    magnitude_bins = (
        ["near_edge"] * 6 + ["medium"] * 6 + ["large"] * 6
    )
    styles = (
        ["persistent_bias"] * 5
        + ["near_miss_drift"] * 5
        + ["cross_and_settle"] * 4
        + ["arc_depart"] * 4
    )
    rng.shuffle(sectors)
    rng.shuffle(magnitude_bins)
    rng.shuffle(styles)
    magnitude_ranges = {
        "near_edge": (4.2, 5.6),
        "medium": (7.2, 10.8),
        "large": (13.0, 16.5),
    }
    result: list[dict[str, Any]] = []
    for sector, magnitude_bin, style in zip(
        sectors, magnitude_bins, styles
    ):
        magnitude = rng.uniform(*magnitude_ranges[magnitude_bin])
        jitter = rng.uniform(-11.0, 11.0)
        fire_yaw, fire_pitch = screen_vector(
            sector, magnitude, jitter
        )
        final_screen_angle = (
            causal.MISS_DIRECTION_SECTORS.index(sector) * 45.0
            + jitter
        )
        if style == "persistent_bias":
            pass_yaw, pass_pitch = fire_yaw, fire_pitch
            requires_target_pass = False
        elif style == "near_miss_drift":
            pass_yaw, pass_pitch = screen_vector(
                sector,
                rng.uniform(3.55, 3.95),
                jitter + rng.uniform(-10.0, 10.0),
            )
            requires_target_pass = False
        elif style == "cross_and_settle":
            pass_yaw, pass_pitch = screen_vector(
                sector,
                rng.uniform(2.8, 3.6),
                jitter + 180.0,
            )
            requires_target_pass = True
        elif style == "arc_depart":
            arc_sign = -1.0 if rng.random() < 0.5 else 1.0
            pass_angle = final_screen_angle + arc_sign * rng.uniform(
                65.0, 95.0
            )
            pass_sector = causal.MISS_DIRECTION_SECTORS[
                int(round(pass_angle / 45.0)) % 8
            ]
            pass_jitter = pass_angle - (
                causal.MISS_DIRECTION_SECTORS.index(pass_sector) * 45.0
            )
            pass_yaw, pass_pitch = screen_vector(
                pass_sector,
                rng.uniform(4.0, 5.8),
                pass_jitter,
            )
            requires_target_pass = False
        else:
            raise AssertionError(style)
        result.append(
            {
                "sector": sector,
                "magnitude_bin": magnitude_bin,
                "trajectory_style": style,
                "fire_yaw_offset_deg": round(fire_yaw, 6),
                "fire_pitch_offset_deg": round(fire_pitch, 6),
                "pass_yaw_offset_deg": round(pass_yaw, 6),
                "pass_pitch_offset_deg": round(pass_pitch, 6),
                "minimum_fire_error_deg": round(
                    max(3.25, min(6.0, magnitude * 0.55)), 6
                ),
                "requires_target_pass": requires_target_pass,
            }
        )
    return result


def aim_schedule(
    policy: str, miss_spec: dict[str, Any] | None
) -> dict[str, Any]:
    schedule = causal.default_aim_schedule_v6(policy)
    if policy != "pass_offset":
        if miss_spec is not None:
            raise AssertionError((policy, miss_spec))
        return schedule
    if miss_spec is None:
        raise AssertionError("pass_offset requires a miss treatment")
    schedule.update(
        {
            "pass_yaw_offset_deg": miss_spec[
                "pass_yaw_offset_deg"
            ],
            "pass_pitch_offset_deg": miss_spec[
                "pass_pitch_offset_deg"
            ],
            "fire_yaw_offset_deg": miss_spec[
                "fire_yaw_offset_deg"
            ],
            "fire_pitch_offset_deg": miss_spec[
                "fire_pitch_offset_deg"
            ],
            "miss_trajectory_style": miss_spec["trajectory_style"],
            "miss_direction_sector": miss_spec["sector"],
            "miss_magnitude_bin": miss_spec["magnitude_bin"],
            "minimum_fire_error_deg": miss_spec[
                "minimum_fire_error_deg"
            ],
            "requires_target_pass": miss_spec[
                "requires_target_pass"
            ],
        }
    )
    causal.validate_aim_schedule_v6(policy, schedule)
    return schedule


def firing_category_plan() -> dict[tuple[int, str, str], str]:
    result: dict[tuple[int, str, str], str] = {}
    rng = random.Random(2026073003)
    firing_arms = list(ARM_SPECS[1:])
    for weapon_index, weapon in enumerate(WEAPONS):
        categories = (
            ["single"] * 3 + ["short"] + ["complex"]
            if weapon_index < 2
            else ["single"] * 2 + ["short"] * 2 + ["complex"]
        )
        rng.shuffle(categories)
        family = WEAPON_FIRE_FAMILY[weapon]
        if family == "spaced_tap":
            track_index = firing_arms.index(
                ("track_loss_reacquire", "main")
            )
            if categories[track_index] != "single":
                swap_index = categories.index("single")
                categories[track_index], categories[swap_index] = (
                    categories[swap_index],
                    categories[track_index],
                )
        for (policy, variant), category in zip(
            firing_arms, categories
        ):
            result[(weapon_index, policy, variant)] = category
    if Counter(result.values()) != FIRING_CATEGORY_TARGET:
        raise capture.CaptureFailure(
            "stage2_humanized_v2_fire_category_allocation",
            capture.canonical_json(Counter(result.values())),
        )
    return result


def fire_program(
    *,
    weapon: str,
    policy: str,
    variant: str,
    category: str | None,
    complex_ordinal: int,
) -> dict[str, Any]:
    if policy == "visible_no_response":
        if category is not None:
            raise AssertionError(category)
        return {
            "schema_version": causal.FIRE_PROGRAM_SCHEMA,
            "name": "none",
            "weapon_fire_family": "none",
            "windows": [],
            "expected_min_fire_events": 0,
            "expected_max_fire_events": 0,
            "requires_multiple_fire_events": False,
            "selection_uses_authoritative_events": True,
        }
    if category not in FIRING_CATEGORY_TARGET:
        raise AssertionError(category)
    start = FIRE_START[(policy, variant)]
    family = WEAPON_FIRE_FAMILY[weapon]
    refire = PRIMARY_REFIRE_TICKS[weapon]
    if category == "single":
        name = "single_tap"
        windows = [{"start_output_tick": start, "duration_ticks": 2}]
        minimum, maximum = 1, 1
    elif family == "rapid_auto":
        if category == "short":
            name = "short_burst"
            windows = [
                {"start_output_tick": start, "duration_ticks": 28}
            ]
            minimum, maximum = 2, 12
        elif complex_ordinal % 2:
            name = "long_burst"
            duration = min(64, capture.OUTPUT_TICKS - start)
            windows = [
                {
                    "start_output_tick": start,
                    "duration_ticks": duration,
                }
            ]
            minimum, maximum = 3, 24
        else:
            name = "double_burst"
            second_start = min(start + 40, 288)
            windows = [
                {"start_output_tick": start, "duration_ticks": 20},
                {
                    "start_output_tick": second_start,
                    "duration_ticks": min(
                        20, capture.OUTPUT_TICKS - second_start
                    ),
                },
            ]
            minimum, maximum = 3, 24
    elif family == "repeat_hold":
        if category == "short":
            name = "short_burst"
            duration = min(
                refire + 10, capture.OUTPUT_TICKS - start
            )
            windows = [
                {
                    "start_output_tick": start,
                    "duration_ticks": duration,
                }
            ]
            minimum, maximum = 2, 8
        elif complex_ordinal % 2:
            name = "long_burst"
            duration = min(
                refire * 2 + 18, capture.OUTPUT_TICKS - start
            )
            windows = [
                {
                    "start_output_tick": start,
                    "duration_ticks": duration,
                }
            ]
            minimum, maximum = 3, 10
        else:
            name = "double_burst"
            first_duration = min(
                refire + 8, capture.OUTPUT_TICKS - start
            )
            second_start = start + first_duration + 16
            second_duration = min(
                refire + 8, capture.OUTPUT_TICKS - second_start
            )
            windows = [
                {
                    "start_output_tick": start,
                    "duration_ticks": first_duration,
                },
                {
                    "start_output_tick": second_start,
                    "duration_ticks": second_duration,
                },
            ]
            minimum, maximum = 3, 12
    elif family == "spaced_tap":
        gap = refire + 5
        if category == "short":
            starts = [start, start + gap]
            name = "multi_tap"
        else:
            third = start + gap * 2
            starts = (
                [start, start + gap, third]
                if third < capture.OUTPUT_TICKS - 1
                else [start, start + gap]
            )
            name = "multi_tap" if len(starts) > 2 else "double_burst"
        if starts[-1] >= capture.OUTPUT_TICKS - 1:
            raise capture.CaptureFailure(
                "stage2_humanized_v2_spaced_tap_does_not_fit",
                f"{weapon} {policy} {variant} {starts}",
            )
        windows = [
            {"start_output_tick": value, "duration_ticks": 2}
            for value in starts
        ]
        minimum = len(starts)
        maximum = len(starts)
    else:
        raise AssertionError(family)
    return {
        "schema_version": causal.FIRE_PROGRAM_SCHEMA,
        "name": name,
        "weapon_fire_family": family,
        "windows": windows,
        "expected_min_fire_events": minimum,
        "expected_max_fire_events": maximum,
        "requires_multiple_fire_events": category != "single",
        "selection_uses_authoritative_events": True,
    }


def static_action_certificate(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Certify open-loop action shape without reading live game state."""
    causal.validate_scenario_contract(scenario)
    capture.validate_scenario_assets(scenario)
    actions = causal.causal_action_rows(scenario)
    design = scenario["causal_design"]
    schedule = design["aim_schedule"]
    fire = design["fire_program"]
    policy = str(design["aim_policy"])
    profile = design["aim_motor_profile"]
    current_yaw = float(scenario["player"]["yaw"])
    current_pitch = float(scenario["player"].get("pitch", 0.0))
    errors: list[float] = []
    signed_vectors: list[tuple[float, float]] = []
    output_actions: list[dict[str, Any]] = []
    for tick, action in enumerate(actions):
        current_yaw = causal.wrap_angle(
            current_yaw + float(action["yaw_delta"])
        )
        current_pitch = max(
            -89.0,
            min(89.0, current_pitch + float(action["pitch_delta"])),
        )
        if tick < capture.WARMUP_TICKS:
            continue
        target_yaw, target_pitch = causal.yaw_pitch_toward(
            list(scenario["player"]["origin"]),
            causal.enemy_origin_at_server_tick(scenario, tick),
        )
        errors.append(
            review_v1.angular_error_deg(
                current_yaw,
                current_pitch,
                target_yaw,
                target_pitch,
            )
        )
        signed_vectors.append(
            (
                -causal.angle_delta(current_yaw, target_yaw),
                current_pitch - target_pitch,
            )
        )
        output_actions.append(action)

    response_start = schedule.get("response_start_output_tick")
    active_start = (
        capture.OUTPUT_TICKS
        if response_start is None
        else int(response_start) + 1
    )
    yaw_steps = [
        float(action["yaw_delta"])
        for action in output_actions[active_start:]
    ]
    pitch_steps = [
        float(action["pitch_delta"])
        for action in output_actions[active_start:]
    ]
    yaw_accels = [
        current - previous
        for previous, current in zip(yaw_steps, yaw_steps[1:])
    ]
    pitch_accels = [
        current - previous
        for previous, current in zip(pitch_steps, pitch_steps[1:])
    ]
    maximum_yaw_speed = max(map(abs, yaw_steps), default=0.0)
    maximum_pitch_speed = max(map(abs, pitch_steps), default=0.0)
    maximum_yaw_accel = max(map(abs, yaw_accels), default=0.0)
    maximum_pitch_accel = max(map(abs, pitch_accels), default=0.0)

    support: list[float] = []
    if policy == "delayed_acquisition":
        support = errors[int(schedule["settle_end_output_tick"]) :]
    elif policy == "pass_offset":
        support = errors[
            int(schedule["response_start_output_tick"]) :
        ]
    elif policy == "track_loss_reacquire":
        support = (
            errors[
                int(schedule["acquisition_end_output_tick"]) :
                int(schedule["centered_hold_end_output_tick"])
            ]
            + errors[
                int(schedule["reacquisition_end_output_tick"]) :
            ]
        )
    elif policy == "sustained_tracking":
        support = errors[
            int(schedule["acquisition_end_output_tick"]) :
            int(schedule["pre_fire_tracking_end_output_tick"])
        ]
    exact_lock_frames = sum(
        value <= float(profile["exact_lock_error_threshold_deg"])
        for value in support
    )
    exact_lock_fraction = (
        exact_lock_frames / len(support) if support else 0.0
    )

    expected_primary = [
        causal.fire_program_active(fire, tick)
        for tick in range(capture.OUTPUT_TICKS)
    ]
    actual_primary = [
        int(action["primary"]) for action in output_actions
    ]
    actual_secondary = [
        int(action["secondary"]) for action in output_actions
    ]
    rising_edges = sum(
        bool(
            value
            and (index == 0 or not actual_primary[index - 1])
        )
        for index, value in enumerate(actual_primary)
    )
    requested_fire_ticks = [
        index for index, value in enumerate(actual_primary) if value
    ]
    fire_program_checks = {
        "primary_mask_exact": actual_primary == expected_primary,
        "secondary_released": not any(actual_secondary),
        "rising_edges_exact": rising_edges == len(fire["windows"]),
        "control_has_no_fire": (
            policy != "visible_no_response"
            or not requested_fire_ticks
        ),
        "treatment_has_fire": (
            policy == "visible_no_response"
            or bool(requested_fire_ticks)
        ),
    }

    policy_checks: dict[str, bool]
    details: dict[str, Any] = {}
    if policy == "visible_no_response":
        policy_checks = {
            "no_view_treatment": all(
                abs(float(action["yaw_delta"])) <= 1e-9
                and abs(float(action["pitch_delta"])) <= 1e-9
                for action in output_actions
            ),
            "no_fire": not requested_fire_ticks,
        }
    elif policy == "delayed_acquisition":
        first_centered = next(
            (
                index
                for index, value in enumerate(errors)
                if value <= 3.0
            ),
            None,
        )
        policy_checks = {
            "not_centered_before_response": not any(
                value <= 3.0
                for value in errors[: int(response_start)]
            ),
            "acquired_after_delay": first_centered is not None
            and first_centered >= int(response_start),
            "settled_without_deliberate_departure": max(support) <= 6.0,
            "fire_after_acquisition": bool(requested_fire_ticks)
            and first_centered is not None
            and min(requested_fire_ticks) > first_centered,
        }
        details["first_centered_output_tick"] = first_centered
    elif policy == "pass_offset":
        fire_errors = [
            errors[tick] for tick in requested_fire_ticks
        ]
        first_horizontal, first_vertical = signed_vectors[
            requested_fire_ticks[0]
        ]
        realized_angle = math.degrees(
            math.atan2(first_vertical, first_horizontal)
        )
        planned_angle = math.degrees(
            math.atan2(
                float(schedule["fire_pitch_offset_deg"]),
                -float(schedule["fire_yaw_offset_deg"]),
            )
        )
        direction_error = abs(
            causal.angle_delta(planned_angle, realized_angle)
        )
        policy_checks = {
            "declared_pass_geometry": (
                not schedule["requires_target_pass"]
                or min(errors) <= 4.0
            ),
            "all_requested_fire_ticks_offset": bool(fire_errors)
            and min(fire_errors)
            >= float(schedule["minimum_fire_error_deg"]),
            "realized_direction_near_declared": (
                direction_error <= 45.0
            ),
        }
        details.update(
            {
                "requested_fire_error_min_deg": min(fire_errors),
                "first_requested_fire_screen_vector_deg": {
                    "horizontal": first_horizontal,
                    "vertical": first_vertical,
                    "direction_sector": causal.miss_direction_sector(
                        -first_horizontal, first_vertical
                    ),
                    "direction_error_deg": direction_error,
                },
            }
        )
    elif policy == "track_loss_reacquire":
        acquisition_end = int(schedule["acquisition_end_output_tick"])
        pause_start = int(schedule["centered_hold_end_output_tick"])
        pause_end = int(schedule["tracking_pause_end_output_tick"])
        reacquisition_end = int(
            schedule["reacquisition_end_output_tick"]
        )
        acquired_frames = sum(
            value <= 3.0
            for value in errors[acquisition_end:pause_start]
        )
        loss_frames = sum(
            value > 3.0 for value in errors[pause_start:pause_end]
        )
        reacquired_ticks = [
            tick
            for tick, value in enumerate(
                errors[pause_end : reacquisition_end + 24],
                pause_end,
            )
            if value <= 3.0
        ]
        policy_checks = {
            "acquired_before_pause": acquired_frames
            >= int(schedule["minimum_centered_before_pause_frames"]),
            "natural_loss_during_pause": loss_frames
            >= int(schedule["minimum_loss_frames"]),
            "reacquired_after_pause": bool(reacquired_ticks),
            "fire_after_reacquisition": bool(requested_fire_ticks)
            and bool(reacquired_ticks)
            and min(requested_fire_ticks) > min(reacquired_ticks),
            "no_authored_departure_offset": (
                "loss_yaw_offset_deg" not in schedule
            ),
        }
        details.update(
            {
                "acquired_frames_before_pause": acquired_frames,
                "natural_loss_frames": loss_frames,
                "first_reacquisition_output_tick": (
                    min(reacquired_ticks) if reacquired_ticks else None
                ),
            }
        )
    elif policy == "sustained_tracking":
        tracking = support
        centered_fraction = sum(
            value <= float(schedule["tracking_error_threshold_deg"])
            for value in tracking
        ) / len(tracking)
        policy_checks = {
            "sustained_centering_before_fire": centered_fraction
            >= float(
                schedule["minimum_centered_given_visible_fraction"]
            ),
            "fire_after_prefire_tracking": bool(requested_fire_ticks)
            and min(requested_fire_ticks)
            > int(schedule["pre_fire_tracking_end_output_tick"]),
        }
        details["centered_prefire_tracking_fraction"] = (
            centered_fraction
        )
    else:
        raise AssertionError(policy)

    tolerance = 2e-5
    motor_checks = {
        "yaw_speed_bounded": maximum_yaw_speed
        <= float(profile["max_yaw_speed_deg_per_tick"]) + tolerance,
        "pitch_speed_bounded": maximum_pitch_speed
        <= float(profile["max_pitch_speed_deg_per_tick"]) + tolerance,
        "yaw_acceleration_bounded": maximum_yaw_accel
        <= float(profile["max_yaw_accel_deg_per_tick2"]) + tolerance,
        "pitch_acceleration_bounded": maximum_pitch_accel
        <= float(profile["max_pitch_accel_deg_per_tick2"]) + tolerance,
        "exact_lock_fraction_bounded": not support
        or exact_lock_fraction
        <= float(profile["maximum_exact_lock_fraction"]),
    }
    passed = (
        all(policy_checks.values())
        and all(motor_checks.values())
        and all(fire_program_checks.values())
    )
    return {
        "schema_version": STATIC_CERTIFICATE_SCHEMA,
        "policy": policy,
        "motor_style": profile["style"],
        "motor_seed": profile["seed"],
        "fire_program_name": fire["name"],
        "fire_program_checks": fire_program_checks,
        "policy_checks": policy_checks,
        "motor_checks": motor_checks,
        "details": details,
        "minimum_angular_error_deg": min(errors),
        "maximum_yaw_speed_deg_per_tick": maximum_yaw_speed,
        "maximum_pitch_speed_deg_per_tick": maximum_pitch_speed,
        "maximum_yaw_accel_deg_per_tick2": maximum_yaw_accel,
        "maximum_pitch_accel_deg_per_tick2": maximum_pitch_accel,
        "exact_lock_support_frames": len(support),
        "exact_lock_frames": exact_lock_frames,
        "exact_lock_fraction": exact_lock_fraction,
        "passed": passed,
    }


def planned_specs() -> list[dict[str, Any]]:
    sources = review_v1.source_rows()[:6]
    selected_sources = [sources[index] for index in SOURCE_INDICES]
    categories = firing_category_plan()
    misses = iter(miss_treatment_specs())
    active_styles = (
        ["direct_smooth"] * 16
        + ["overshoot_correct"] * 18
        + ["undershoot_correct"] * 11
    )
    random.Random(2026073004).shuffle(active_styles)
    style_iter = iter(active_styles)
    specs: list[dict[str, Any]] = []
    complex_ordinal = 0
    for weapon_index, (weapon, source) in enumerate(
        zip(WEAPONS, selected_sources)
    ):
        for policy, variant in ARM_SPECS:
            category = categories.get(
                (weapon_index, policy, variant)
            )
            miss_spec = next(misses) if policy == "pass_offset" else None
            if category == "complex":
                complex_ordinal += 1
            specs.append(
                {
                    "weapon_index": weapon_index,
                    "weapon": weapon,
                    "source": source,
                    "policy": policy,
                    "variant": variant,
                    "firing_category": category,
                    "miss_spec": miss_spec,
                    "motor_style": (
                        "direct_smooth"
                        if policy == "visible_no_response"
                        else next(style_iter)
                    ),
                    "complex_ordinal": complex_ordinal,
                }
            )
    try:
        next(style_iter)
        raise AssertionError("unused motor style")
    except StopIteration:
        pass
    try:
        next(misses)
        raise AssertionError("unused miss treatment")
    except StopIteration:
        pass
    return specs


def materialize() -> list[dict[str, Any]]:
    specs = planned_specs()
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    rows: list[dict[str, Any]] = []
    rejected_candidates: Counter[str] = Counter()
    for row_ordinal, spec in enumerate(specs):
        weapon_index = int(spec["weapon_index"])
        weapon = str(spec["weapon"])
        source = spec["source"]
        policy = str(spec["policy"])
        variant = str(spec["variant"])
        group_id = (
            f"{GROUP_PREFIX}_g{weapon_index + 1:02d}_"
            f"{capture.WEAPON_NETNAME[weapon]}"
        )
        arm_suffix = (
            policy if variant == "main" else f"{policy}_{variant}"
        )
        if variant == "control":
            arm_suffix = policy
        row = copy.deepcopy(source)
        for key in (
            "encounter_certificate",
            "target_motion_review_design",
            "bias_correction_design",
            "humanized_review_design",
        ):
            row.pop(key, None)
        row.update(
            {
                "schema_version": causal.SCENARIO_SCHEMA_V6,
                "action_program": causal.ACTION_PROGRAM_V6,
                "episode_id": f"{group_id}_{arm_suffix}",
                "counterfactual_group_id": group_id,
                "anchor_id": f"{group_id}_pair",
                "seed": 16_700_000 + weapon_index + 1,
                "weapon": weapon,
                "weapon_netname": capture.WEAPON_NETNAME[weapon],
                "category": (
                    f"stage2_humanized_review_v2_{policy}"
                ),
                "candidate_kind": (
                    "stage2_humanized_burst_miss_review_v2"
                ),
                "candidate_status": (
                    "static_certified_pending_live_capture"
                ),
                "training_stage": (
                    "stage2_humanized_review_v2_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "human_review_required_before_training": True,
                "canary_role": (
                    f"stage2_humanized_v2_{weapon.lower()}_"
                    f"{arm_suffix}"
                ),
                "source_commit_required": SOURCE_COMMIT,
                "data_spec_sha256": data_spec_sha256,
                "shard_count": SHARD_COUNT,
                "assigned_shard": row_ordinal % SHARD_COUNT,
                "target_ordinal": row_ordinal,
                "split": "stage2_humanized_nontraining_review",
                "expects_sound": True,
            }
        )
        row["enemy"]["health"] = 5000.0
        row["enemy"]["armor"] = 0.0
        row["enemy_policy"].update(
            {
                "policy_layer": (
                    "frozen_exogenous_counterfactual_core"
                ),
                "bot_policy_scope": (
                    "review_motion_primitive_only"
                ),
                "closed_loop_decisions": False,
            }
        )
        row["encounter_source"][
            "current_trajectory_requires_recertification"
        ] = True
        row["encounter_source"][
            "source_geometry_used_as_runtime_fallback"
        ] = False
        cell, yaw_offset, pitch_offset = INITIAL_CELLS[weapon_index]
        target_yaw, target_pitch = causal.yaw_pitch_toward(
            list(row["player"]["origin"]),
            list(row["enemy"]["origin"]),
        )
        row["player"]["yaw"] = causal.wrap_angle(
            target_yaw + yaw_offset
        )
        row["player"]["pitch"] = max(
            -89.0, min(89.0, target_pitch + pitch_offset)
        )
        row["initial_screen_design"] = review_v1.initial_screen_design(
            cell, yaw_offset, pitch_offset
        )

        schedule = aim_schedule(policy, spec["miss_spec"])
        program = fire_program(
            weapon=weapon,
            policy=policy,
            variant=variant,
            category=spec["firing_category"],
            complex_ordinal=int(spec["complex_ordinal"]),
        )
        design = row["causal_design"]
        design.update(
            {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V6,
                "aim_policy": policy,
                "aim_schedule": schedule,
                "aim_motor_profile": {},
                "acquisition_start_output_tick": int(
                    schedule.get("response_start_output_tick") or 0
                ),
                "fire_program": program,
                "fire_output_ticks": [
                    int(window["start_output_tick"])
                    for window in program["windows"]
                ],
                "fire_width_ticks": 2,
                "interaction_channel": "primary",
                "secondary_mechanism": None,
                "base_player_program": "stationary",
                "base_view_yaw_offset_deg": 0.0,
                "base_view_pitch_offset_deg": 0.0,
                "shot_error_schedule": causal.shot_error_schedule(
                    "none"
                ),
                "shot_error_is_outcome_label": False,
                "actual_outcome_source": (
                    "authoritative_telemetry_only"
                ),
                "intended_outcome_is_acceptance_gate": False,
                "certified_occlusion_driven_track_loss": False,
            }
        )
        row["policy_labels"].update(
            {
                "aim_policy": policy,
                "interaction_channel": "primary",
                "initial_screen_cell": cell,
                "target_motion_name": row["enemy_policy"]["name"],
                "aim_motor_style": spec["motor_style"],
                "fire_program_category": spec["firing_category"]
                or "none",
                "miss_direction_sector": (
                    spec["miss_spec"]["sector"]
                    if spec["miss_spec"]
                    else "not_applicable"
                ),
                "miss_magnitude_bin": (
                    spec["miss_spec"]["magnitude_bin"]
                    if spec["miss_spec"]
                    else "not_applicable"
                ),
                "miss_trajectory_style": (
                    spec["miss_spec"]["trajectory_style"]
                    if spec["miss_spec"]
                    else "not_applicable"
                ),
                "outcome_assignment": (
                    "post_capture_authoritative_telemetry_rebucket"
                ),
            }
        )
        row["acceptance"].update(
            {
                "actual_outcome": None,
                "actual_outcome_rebucket_required": True,
                "fire_required": policy in causal.FIRING_POLICIES,
            }
        )

        selected_certificate: dict[str, Any] | None = None
        selected_attempt: int | None = None
        for attempt in range(256):
            motor_seed = 17_700_000 + row_ordinal * 512 + attempt + 1
            design["aim_motor_profile"] = (
                causal.humanized_aim_motor_profile(
                    motor_seed, str(spec["motor_style"])
                )
            )
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            certificate = static_action_certificate(row)
            if certificate["passed"]:
                selected_certificate = certificate
                selected_attempt = attempt
                break
            for name, passed in {
                **certificate["policy_checks"],
                **certificate["motor_checks"],
                **certificate["fire_program_checks"],
            }.items():
                if not passed:
                    rejected_candidates[name] += 1
        if selected_certificate is None or selected_attempt is None:
            raise capture.CaptureFailure(
                "stage2_humanized_v2_no_static_candidate",
                (
                    f"{row['episode_id']} style={spec['motor_style']} "
                    f"last={capture.canonical_json(certificate)}"
                ),
            )
        row["humanized_review_design"] = {
            "schema_version": DESIGN_SCHEMA,
            "selection_rule": SELECTION_RULE,
            "source_manifest": str(
                review_v1.MOTION_SOURCE.relative_to(ROOT)
            ),
            "source_episode_id": source["episode_id"],
            "initial_screen_cell": cell,
            "target_motion_class": row["enemy_policy"]["name"],
            "motor_style": spec["motor_style"],
            "motor_candidate_attempt": selected_attempt,
            "firing_program_category": spec["firing_category"]
            or "none",
            "miss_treatment": spec["miss_spec"],
            "static_action_certificate": selected_certificate,
            "runtime_action_fallback": False,
            "runtime_geometry_fallback": False,
            "live_state_used_during_action_generation": False,
            "formal_collection_authorized": False,
        }
        causal.validate_scenario_contract(row)
        rows.append(row)

    for group_id in sorted(
        {row["counterfactual_group_id"] for row in rows}
    ):
        members = [
            row
            for row in rows
            if row["counterfactual_group_id"] == group_id
        ]
        if len(members) != len(ARM_SPECS):
            raise capture.CaptureFailure(
                "stage2_humanized_v2_group_shape", group_id
            )
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_humanized_v2_group_exogenous_drift",
                group_id,
            )

    input_text = canonical_lines(rows)
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", input_text)
    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        write_once_or_verify(shard_path, shard_text)
        shard_metadata.append(
            {
                "shard_index": shard_index,
                "path": str(shard_path.relative_to(ROOT)),
                "rows": len(shard_rows),
                "sha256": hashlib.sha256(
                    shard_text.encode("utf-8")
                ).hexdigest(),
            }
        )
    metadata = {
        "schema_version": MANIFEST_SCHEMA,
        "selection_rule": SELECTION_RULE,
        "source_manifests": [
            {
                "path": str(review_v1.MOTION_SOURCE.relative_to(ROOT)),
                "sha256": capture.sha256_file(review_v1.MOTION_SOURCE),
            }
        ],
        "source_commit": SOURCE_COMMIT,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "counterfactual_groups": len(
            {row["counterfactual_group_id"] for row in rows}
        ),
        "shard_count": SHARD_COUNT,
        "shards": shard_metadata,
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(
                {row["counterfactual_group_id"] for row in rows}
            ),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "policy_distribution": dict(
            Counter(
                row["causal_design"]["aim_policy"] for row in rows
            )
        ),
        "target_motion_distribution": dict(
            Counter(row["enemy_policy"]["name"] for row in rows)
        ),
        "initial_screen_distribution": dict(
            Counter(
                row["policy_labels"]["initial_screen_cell"]
                for row in rows
            )
        ),
        "active_motor_style_distribution": dict(
            Counter(
                row["causal_design"]["aim_motor_profile"]["style"]
                for row in rows
                if row["causal_design"]["aim_policy"]
                != "visible_no_response"
            )
        ),
        "firing_category_distribution": dict(
            Counter(
                row["humanized_review_design"][
                    "firing_program_category"
                ]
                for row in rows
                if row["causal_design"]["aim_policy"]
                != "visible_no_response"
            )
        ),
        "fire_program_distribution": dict(
            Counter(
                row["causal_design"]["fire_program"]["name"]
                for row in rows
            )
        ),
        "miss_direction_distribution": dict(
            Counter(
                row["causal_design"]["aim_schedule"][
                    "miss_direction_sector"
                ]
                for row in rows
                if row["causal_design"]["aim_policy"] == "pass_offset"
            )
        ),
        "miss_magnitude_distribution": dict(
            Counter(
                row["causal_design"]["aim_schedule"][
                    "miss_magnitude_bin"
                ]
                for row in rows
                if row["causal_design"]["aim_policy"] == "pass_offset"
            )
        ),
        "miss_trajectory_distribution": dict(
            Counter(
                row["causal_design"]["aim_schedule"][
                    "miss_trajectory_style"
                ]
                for row in rows
                if row["causal_design"]["aim_policy"] == "pass_offset"
            )
        ),
        "rejected_static_candidates": dict(rejected_candidates),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "authoritative_fire_event_rebucket_required": True,
        "realized_miss_vector_rebucket_required": True,
        "track_loss_requires_natural_target_motion_or_occlusion": True,
        "stationary_track_loss_rows": 0,
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
                "output_root": str(OUTPUT_ROOT),
                "rows": len(rows),
                "groups": len(
                    {row["counterfactual_group_id"] for row in rows}
                ),
                "weapons": dict(Counter(row["weapon"] for row in rows)),
                "fire_categories": dict(
                    Counter(
                        row["humanized_review_design"][
                            "firing_program_category"
                        ]
                        for row in rows
                        if row["causal_design"]["aim_policy"]
                        != "visible_no_response"
                    )
                ),
                "miss_directions": dict(
                    Counter(
                        row["causal_design"]["aim_schedule"][
                            "miss_direction_sector"
                        ]
                        for row in rows
                        if row["causal_design"]["aim_policy"]
                        == "pass_offset"
                    )
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
