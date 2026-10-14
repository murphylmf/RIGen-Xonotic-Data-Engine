                      
"""Materialize the bounded, non-training Stage-2 humanized-aim review.

This review deliberately reuses already validated map/anchor and target-motion
primitives.  It does not inherit an encounter certificate after changing the
initial camera.  Every action row is generated and statically certified before
the immutable manifest is written; there is no runtime action or geometry
fallback.
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
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
MOTION_SOURCE = (
    ROOT / "manifests/stage2_target_motion_review_v1/input.jsonl"
)
STATIC_SOURCE = (
    ROOT
    / "manifests/stage2_bias_correction_v3_selected/"
    "SELECTION_MANIFEST.jsonl"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_humanized_review_v1"
GROUP_PREFIX = "s2humanv1"
SOURCE_COMMIT = "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
SHARD_COUNT = 4
MANIFEST_SCHEMA = "xonotic-stage2-humanized-review-manifest-v1"
DESIGN_SCHEMA = "xonotic-stage2-humanized-review-design-v1"
STATIC_CERTIFICATE_SCHEMA = (
    "xonotic-stage2-humanized-static-action-certificate-v1"
)
SELECTION_RULE = (
    "fixed_source_groups_fixed_initial_screen_cells_then_"
    "deterministic_same_style_motor_candidate_certification_v1"
)
FIRE_TICKS = {
    "visible_no_response": [],
    "delayed_acquisition": [200],
    "pass_offset": [256],
    "track_loss_reacquire": [272],
    "sustained_tracking": [272],
}
MOVING_INITIAL_CELLS = (
    ("upper_left", -24.0, 8.0),
    ("upper_right", 24.0, 8.0),
    ("lower_left", -24.0, -8.0),
    ("lower_right", 24.0, -8.0),
    ("left_center", -20.0, 0.0),
    ("right_center", 20.0, 0.0),
)
STATIC_GROUPS = (
    "s2biasv2_g01",
    "s2biasv2_g02",
    "s2biasv2_g03",
    "s2biasv2_g04",
    "s2biasv2r2_g15",
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


def initial_screen_design(
    cell: str, yaw_offset: float, pitch_offset: float
) -> dict[str, Any]:
    horizontal, vertical = {
        "upper_left": ("left", "upper"),
        "upper_right": ("right", "upper"),
        "lower_left": ("left", "lower"),
        "lower_right": ("right", "lower"),
        "left_center": ("left", "center"),
        "right_center": ("right", "center"),
        "center": ("center", "center"),
    }[cell]
    return {
        "schema_version": causal.INITIAL_SCREEN_DESIGN_SCHEMA,
        "view_yaw_offset_deg": float(yaw_offset),
        "view_pitch_offset_deg": float(pitch_offset),
        "screen_horizontal": horizontal,
        "screen_vertical": vertical,
        "expected_visible_at_output_start": True,
    }


def shot_schedule(policy: str) -> dict[str, Any]:
    if policy == "pass_offset":
        return causal.shot_error_schedule(
            "pass_cross_and_depart",
            minimum_error_at_fire_deg=6.0,
            expected_center_before_first_fire=True,
        )
    return causal.shot_error_schedule("none")


def angular_error_deg(
    camera_yaw: float,
    camera_pitch: float,
    target_yaw: float,
    target_pitch: float,
) -> float:
                                                                           
                                                                            
    def direction(yaw: float, pitch: float) -> tuple[float, float, float]:
        yaw_r = math.radians(yaw)
        pitch_r = math.radians(pitch)
        cosine = math.cos(pitch_r)
        return (
            cosine * math.cos(yaw_r),
            cosine * math.sin(yaw_r),
            -math.sin(pitch_r),
        )

    camera = direction(camera_yaw, camera_pitch)
    target = direction(target_yaw, target_pitch)
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(camera, target))))
    return math.degrees(math.acos(dot))


def static_action_certificate(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Certify policy shape and motor bounds without reading live outcomes."""
    causal.validate_scenario_contract(scenario)
    capture.validate_scenario_assets(scenario)
    actions = causal.causal_action_rows(scenario)
    design = scenario["causal_design"]
    schedule = design["aim_schedule"]
    policy = str(design["aim_policy"])
    profile = design["aim_motor_profile"]
    current_yaw = float(scenario["player"]["yaw"])
    current_pitch = float(scenario["player"].get("pitch", 0.0))
    errors: list[float] = []
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
            angular_error_deg(
                current_yaw,
                current_pitch,
                target_yaw,
                target_pitch,
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
        ]
    exact_lock_frames = sum(
        value <= float(profile["exact_lock_error_threshold_deg"])
        for value in support
    )
    exact_lock_fraction = (
        exact_lock_frames / len(support) if support else 0.0
    )

    fire_ticks = [int(value) for value in design["fire_output_ticks"]]
    fire_errors = [errors[tick] for tick in fire_ticks]
    policy_checks: dict[str, bool]
    details: dict[str, Any] = {}
    if policy == "visible_no_response":
        policy_checks = {
            "no_view_treatment": all(
                abs(float(action["yaw_delta"])) <= 1e-9
                and abs(float(action["pitch_delta"])) <= 1e-9
                for action in output_actions
            ),
            "no_fire": not fire_ticks,
        }
    elif policy == "delayed_acquisition":
        first_centered = next(
            (index for index, value in enumerate(errors) if value <= 3.0),
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
            "fire_after_acquisition": bool(fire_ticks)
            and first_centered is not None
            and min(fire_ticks) > first_centered,
        }
        details["first_centered_output_tick"] = first_centered
    elif policy == "pass_offset":
        policy_checks = {
            "target_passed": min(errors) <= 4.0,
            "departed_before_fire": bool(fire_errors)
            and min(fire_errors) >= 6.0,
        }
        details["post_pass_error_probe"] = {
            str(tick): errors[tick]
            for tick in (176, 196, 216, 236, 256, 276, 296)
        }
    elif policy == "track_loss_reacquire":
        acquisition_end = int(schedule["acquisition_end_output_tick"])
        pause_start = int(
            schedule["centered_hold_end_output_tick"]
        )
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
            >= int(
                schedule[
                    "minimum_centered_before_pause_frames"
                ]
            ),
            "natural_loss_during_pause": loss_frames
            >= int(schedule["minimum_loss_frames"]),
            "reacquired_after_pause": bool(reacquired_ticks),
            "fire_after_reacquisition": bool(fire_ticks)
            and bool(reacquired_ticks)
            and min(fire_ticks) > min(reacquired_ticks),
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
        tracking = errors[
            int(schedule["acquisition_end_output_tick"]) :
        ]
        centered_fraction = sum(
            value <= float(schedule["tracking_error_threshold_deg"])
            for value in tracking
        ) / len(tracking)
        policy_checks = {
            "sustained_centering": centered_fraction
            >= float(
                schedule[
                    "minimum_centered_given_visible_fraction"
                ]
            ),
            "fire_after_acquisition_window": bool(fire_ticks)
            and min(fire_ticks)
            > int(schedule["acquisition_end_output_tick"]),
        }
        details["centered_tracking_fraction"] = centered_fraction
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
    passed = all(policy_checks.values()) and all(motor_checks.values())
    return {
        "schema_version": STATIC_CERTIFICATE_SCHEMA,
        "policy": policy,
        "motor_style": profile["style"],
        "motor_seed": profile["seed"],
        "policy_checks": policy_checks,
        "motor_checks": motor_checks,
        "details": details,
        "minimum_angular_error_deg": min(errors),
        "fire_angular_error_deg": fire_errors,
        "maximum_yaw_speed_deg_per_tick": maximum_yaw_speed,
        "maximum_pitch_speed_deg_per_tick": maximum_pitch_speed,
        "maximum_yaw_accel_deg_per_tick2": maximum_yaw_accel,
        "maximum_pitch_accel_deg_per_tick2": maximum_pitch_accel,
        "exact_lock_support_frames": len(support),
        "exact_lock_frames": exact_lock_frames,
        "exact_lock_fraction": exact_lock_fraction,
        "passed": passed,
    }


def source_rows() -> list[dict[str, Any]]:
    motion_rows = capture.load_jsonl(MOTION_SOURCE)
    moving: list[dict[str, Any]] = []
    for group_id in sorted(
        {row["counterfactual_group_id"] for row in motion_rows}
    ):
        matches = [
            row
            for row in motion_rows
            if row["counterfactual_group_id"] == group_id
            and row["causal_design"]["aim_policy"]
            == "visible_no_response"
        ]
        if len(matches) != 1:
            raise capture.CaptureFailure(
                "stage2_humanized_moving_source_missing", group_id
            )
        moving.append(matches[0])

    static_rows = capture.load_jsonl(STATIC_SOURCE)
    stationary: list[dict[str, Any]] = []
    for group_id in STATIC_GROUPS:
        matches = [
            row
            for row in static_rows
            if row["counterfactual_group_id"] == group_id
            and row["causal_design"]["aim_policy"]
            == "visible_no_response"
        ]
        if len(matches) != 1:
            raise capture.CaptureFailure(
                "stage2_humanized_static_source_missing", group_id
            )
        stationary.append(matches[0])
    return moving + stationary


def planned_specs() -> list[dict[str, Any]]:
    sources = source_rows()
    specs: list[dict[str, Any]] = []
    for source_ordinal, source in enumerate(sources, 1):
        moving = int(source["enemy"]["motion"]) != 0
        policies = [
            policy
            for policy in causal.AIM_POLICIES
            if (
                moving
                and (
                    policy != "track_loss_reacquire"
                    or source["enemy_policy"]["name"]
                    != "approach_retreat"
                )
            )
            or (
                not moving
                and policy != "track_loss_reacquire"
            )
        ]
        for policy in policies:
            specs.append(
                {
                    "source": source,
                    "source_ordinal": source_ordinal,
                    "moving": moving,
                    "policy": policy,
                }
            )
    active = [
        spec
        for spec in specs
        if spec["policy"] != "visible_no_response"
    ]
    styles = (
        ["direct_smooth"] * 13
        + ["overshoot_correct"] * 15
        + ["undershoot_correct"] * 9
    )
    if len(active) != len(styles):
        raise capture.CaptureFailure(
            "stage2_humanized_style_allocation_shape",
            f"active={len(active)} styles={len(styles)}",
        )
    random.Random(20260730).shuffle(styles)
    for spec, style in zip(active, styles):
        spec["motor_style"] = style
    for spec in specs:
        spec.setdefault("motor_style", "direct_smooth")
    return specs


def materialize() -> list[dict[str, Any]]:
    specs = planned_specs()
    static_rows = capture.load_jsonl(STATIC_SOURCE)
    runtime_transition = copy.deepcopy(
        static_rows[0]["runtime_transition_contract"]
    )
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    rows: list[dict[str, Any]] = []
    rejected_candidates: Counter[str] = Counter()
    group_ids: dict[int, str] = {}
    for row_ordinal, spec in enumerate(specs):
        source = spec["source"]
        source_ordinal = int(spec["source_ordinal"])
        moving = bool(spec["moving"])
        policy = str(spec["policy"])
        group_id = group_ids.setdefault(
            source_ordinal,
            (
                f"{GROUP_PREFIX}_g{source_ordinal:02d}_"
                f"{'moving' if moving else 'stationary'}"
            ),
        )
        row = copy.deepcopy(source)
        row.pop("encounter_certificate", None)
        row.pop("target_motion_review_design", None)
        row.pop("bias_correction_design", None)
        row.update(
            {
                "schema_version": causal.SCENARIO_SCHEMA_V5,
                "action_program": causal.ACTION_PROGRAM_V5,
                "episode_id": (
                    f"{group_id}_{policy}"
                ),
                "counterfactual_group_id": group_id,
                "anchor_id": f"{group_id}_pair",
                "category": f"stage2_humanized_review_{policy}",
                "candidate_kind": "stage2_humanized_review_v1",
                "candidate_status": (
                    "static_certified_pending_live_capture"
                ),
                "training_stage": (
                    "stage2_humanized_review_v1_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "human_review_required_before_training": True,
                "canary_role": f"stage2_humanized_review_{policy}",
                "source_commit_required": SOURCE_COMMIT,
                "data_spec_sha256": data_spec_sha256,
                "shard_count": SHARD_COUNT,
                "assigned_shard": row_ordinal % SHARD_COUNT,
                "target_ordinal": row_ordinal,
                "split": "stage2_humanized_nontraining_review",
                "expects_sound": bool(
                    moving or policy in causal.FIRING_POLICIES
                ),
                "runtime_transition_contract": copy.deepcopy(
                    runtime_transition
                ),
            }
        )
        row["enemy"]["health"] = 5000.0
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
        if moving:
            cell, yaw_offset, pitch_offset = MOVING_INITIAL_CELLS[
                source_ordinal - 1
            ]
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
            row["initial_screen_design"] = initial_screen_design(
                cell, yaw_offset, pitch_offset
            )
        else:
            cell = str(
                row["bias_correction_design"][
                    "initial_screen_cell"
                ]
                if "bias_correction_design" in row
                else row["policy_labels"]["initial_screen_cell"]
            )

        schedule = causal.default_aim_schedule_v5(policy)
        design = row["causal_design"]
        design.update(
            {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V5,
                "aim_policy": policy,
                "aim_schedule": schedule,
                "acquisition_start_output_tick": int(
                    schedule.get("response_start_output_tick") or 0
                ),
                "fire_output_ticks": list(FIRE_TICKS[policy]),
                "fire_width_ticks": 2,
                "interaction_channel": "primary",
                "secondary_mechanism": None,
                "base_player_program": "stationary",
                "base_view_yaw_offset_deg": 0.0,
                "base_view_pitch_offset_deg": 0.0,
                "shot_error_schedule": shot_schedule(policy),
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
        for attempt in range(128):
            motor_seed = 17600000 + row_ordinal * 256 + attempt + 1
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
            }.items():
                if not passed:
                    rejected_candidates[name] += 1
        if selected_certificate is None or selected_attempt is None:
            raise capture.CaptureFailure(
                "stage2_humanized_no_static_candidate",
                (
                    f"{row['episode_id']} style={spec['motor_style']} "
                    f"last={capture.canonical_json(certificate)}"
                ),
            )
        row["humanized_review_design"] = {
            "schema_version": DESIGN_SCHEMA,
            "selection_rule": SELECTION_RULE,
            "source_manifest": str(
                (MOTION_SOURCE if moving else STATIC_SOURCE).relative_to(
                    ROOT
                )
            ),
            "source_episode_id": source["episode_id"],
            "initial_screen_cell": cell,
            "target_motion_class": row["enemy_policy"]["name"],
            "motor_style": spec["motor_style"],
            "motor_candidate_attempt": selected_attempt,
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
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_humanized_group_exogenous_drift", group_id
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
                "path": str(MOTION_SOURCE.relative_to(ROOT)),
                "sha256": capture.sha256_file(MOTION_SOURCE),
            },
            {
                "path": str(STATIC_SOURCE.relative_to(ROOT)),
                "sha256": capture.sha256_file(STATIC_SOURCE),
            },
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
        "rejected_static_motor_candidates": dict(
            rejected_candidates
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
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
                "policy": dict(
                    Counter(
                        row["causal_design"]["aim_policy"]
                        for row in rows
                    )
                ),
                "motion": dict(
                    Counter(row["enemy_policy"]["name"] for row in rows)
                ),
                "motor_style_active": dict(
                    Counter(
                        row["causal_design"]["aim_motor_profile"][
                            "style"
                        ]
                        for row in rows
                        if row["causal_design"]["aim_policy"]
                        != "visible_no_response"
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
