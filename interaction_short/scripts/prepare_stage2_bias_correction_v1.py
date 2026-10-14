                      
"""Build a bounded Stage-2 screen/miss-bias correction cohort.

This is a deterministic candidate-generation design, not a hand-picked
gallery.  Initial screen placement is exogenous at counterfactual-family
level.  Shot-error programs are treatment arms; authoritative engine
telemetry remains the only outcome label.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
SOURCE = ROOT / "manifests/stage2_outcome_calibration_v1/input.jsonl"
OUTPUT_ROOT = ROOT / "manifests/stage2_bias_correction_v1"
DATA_SPEC = ROOT / "XONOTIC_DATA_SPEC_V2.md"
SHARD_COUNT = 4
ROW_COUNT = 100
GROUP_COUNT = 15

POLICY_TARGETS = {
    "visible_no_response": 15,
    "delayed_acquisition": 20,
    "pass_offset": 20,
    "track_loss_reacquire": 20,
    "sustained_tracking": 25,
}
MISS_POLICY_TARGETS = {
    "delayed_acquisition": 6,
    "pass_offset": 7,
    "track_loss_reacquire": 7,
    "sustained_tracking": 5,
}
MISS_PROGRAMS_BY_POLICY = {
    "delayed_acquisition": (
        "spatial_persistent",
        "spatial_transient",
        "timing_early_acquisition",
        "spatial_persistent",
        "spatial_transient",
        "timing_early_acquisition",
    ),
    "pass_offset": (
        "spatial_persistent",
        "timing_early_acquisition",
        "pass_cross_and_depart",
        "spatial_persistent",
        "timing_early_acquisition",
        "pass_cross_and_depart",
        "pass_cross_and_depart",
    ),
    "track_loss_reacquire": (
        "spatial_transient",
        "timing_loss_window",
        "timing_reacquisition_lag",
        "spatial_transient",
        "timing_loss_window",
        "timing_reacquisition_lag",
        "timing_loss_window",
    ),
    "sustained_tracking": (
        "spatial_transient",
        "spatial_transient",
        "spatial_transient",
        "spatial_transient",
        "spatial_transient",
    ),
}

                                                                            
                                                                             
SCREEN_CELLS = (
    ("upper_left", "left", "upper", -24.0, 8.0),
    ("upper_right", "right", "upper", 24.0, 8.0),
    ("lower_left", "left", "lower", -24.0, -8.0),
    ("lower_right", "right", "lower", 24.0, -8.0),
    ("upper_left", "left", "upper", -28.0, 10.0),
    ("upper_right", "right", "upper", 28.0, 10.0),
    ("lower_left", "left", "lower", -28.0, -10.0),
    ("lower_right", "right", "lower", 28.0, -10.0),
    ("upper_left", "left", "upper", -18.0, 7.0),
    ("upper_right", "right", "upper", 18.0, 7.0),
    ("lower_left", "left", "lower", -18.0, -7.0),
    ("lower_right", "right", "lower", 18.0, -7.0),
    ("left_center", "left", "center", -20.0, 0.0),
    ("right_center", "right", "center", 20.0, 0.0),
    ("center", "center", "center", 0.0, 0.0),
)

                                                                  
                                                                           
                                                                        
SUPPLEMENT_FAMILIES = {
    "delayed_acquisition": (0, 1, 2, 3, 14),
    "pass_offset": (4, 5, 6, 7, 12),
    "track_loss_reacquire": (8, 9, 10, 11, 13),
    "sustained_tracking": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
}

BASE_FIRE_TICKS = {
    "visible_no_response": (),
    "delayed_acquisition": (176,),
    "pass_offset": (176,),
    "track_loss_reacquire": (248,),
    "sustained_tracking": (88, 176),
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


def source_rows() -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for row in capture.load_jsonl(SOURCE):
        if (
            row["causal_design"]["aim_policy"]
            == "visible_no_response"
            and row["weapon"] not in selected
        ):
            selected[row["weapon"]] = row
    expected = {
        "Blaster",
        "Shotgun",
        "MachineGun",
        "Mortar",
        "Electro",
        "Crylink",
        "Vortex",
        "Hagar",
        "Devastator",
    }
    if set(selected) != expected:
        raise capture.CaptureFailure(
            "stage2_bias_source_weapons",
            capture.canonical_json(sorted(selected)),
        )
    return [selected[name] for name in sorted(selected)]


def treatment_slots(
    *,
    miss_assignments: dict[
        str, tuple[tuple[int, bool, str], ...]
    ]
    | None = None,
) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for family in range(GROUP_COUNT):
        for policy in causal.AIM_POLICIES:
            slots.append(
                {
                    "family": family,
                    "policy": policy,
                    "supplement": False,
                }
            )
    for policy, families in SUPPLEMENT_FAMILIES.items():
        for family in families:
            slots.append(
                {
                    "family": family,
                    "policy": policy,
                    "supplement": True,
                }
            )
    if len(slots) != ROW_COUNT:
        raise AssertionError(len(slots))

    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for slot in slots:
        by_policy[slot["policy"]].append(slot)
    if miss_assignments is None:
        for policy, count in MISS_POLICY_TARGETS.items():
            candidates = sorted(
                by_policy[policy],
                key=lambda slot: (
                    slot["family"] == GROUP_COUNT - 1,
                    hashlib.sha256(
                        (
                            f"{slot['family']}|{slot['policy']}|"
                            f"{int(slot['supplement'])}"
                        ).encode("utf-8")
                    ).hexdigest(),
                ),
            )
            programs = MISS_PROGRAMS_BY_POLICY[policy]
            if len(programs) != count:
                raise AssertionError((policy, len(programs), count))
            for slot, program in zip(candidates[:count], programs):
                slot["shot_error_program"] = program
    else:
        if set(miss_assignments) != set(MISS_POLICY_TARGETS):
            raise AssertionError(sorted(miss_assignments))
        slot_index = {
            (
                str(slot["policy"]),
                int(slot["family"]),
                bool(slot["supplement"]),
            ): slot
            for slot in slots
        }
        for policy, count in MISS_POLICY_TARGETS.items():
            assignments = miss_assignments[policy]
            if len(assignments) != count:
                raise AssertionError(
                    (policy, len(assignments), count)
                )
            seen_assignments: set[tuple[int, bool]] = set()
            for family, supplement, program in assignments:
                key = (int(family), bool(supplement))
                if key in seen_assignments:
                    raise AssertionError(
                        f"duplicate miss assignment: {policy} {key}"
                    )
                seen_assignments.add(key)
                slot_key = (policy, key[0], key[1])
                if slot_key not in slot_index:
                    raise AssertionError(
                        f"missing treatment slot: {slot_key}"
                    )
                slot_index[slot_key]["shot_error_program"] = program
    for slot in slots:
        slot.setdefault("shot_error_program", "none")
    return slots


def aim_schedule(
    policy: str,
    program: str,
    view_yaw_offset_deg: float,
) -> dict[str, Any]:
    schedule = causal.default_aim_schedule(policy)
    if policy != "pass_offset":
        return schedule
    opposite = -1.0 if view_yaw_offset_deg >= 0.0 else 1.0
    if program == "pass_cross_and_depart":
        schedule["pass_yaw_offset_deg"] = opposite * 3.0
        schedule["fire_yaw_offset_deg"] = opposite * 12.0
    else:
                                                                              
                                                                          
                                                 
        schedule["pass_yaw_offset_deg"] = opposite * 4.0
        schedule["fire_yaw_offset_deg"] = 0.0
    return schedule


def fire_ticks(policy: str, program: str) -> tuple[int, ...]:
    if program == "timing_early_acquisition":
        return (100,) if policy == "delayed_acquisition" else (64,)
    if program == "timing_loss_window":
        return (168,)
    if program == "timing_reacquisition_lag":
        return (200,)
    if program in {
        "spatial_persistent",
        "spatial_transient",
        "pass_cross_and_depart",
    }:
        return {
            "delayed_acquisition": (176,),
            "pass_offset": (176,),
            "track_loss_reacquire": (248,),
            "sustained_tracking": (176,),
        }[policy]
    return BASE_FIRE_TICKS[policy]


def error_schedule(
    *,
    policy: str,
    program: str,
    fire_tick: int | None,
    view_yaw_offset_deg: float,
    ordinal: int,
    fire_width: int,
) -> dict[str, Any]:
    if program == "none":
        return causal.shot_error_schedule("none")
    if program == "spatial_persistent":
        response = int(
            causal.default_aim_schedule(policy).get(
                "response_start_output_tick"
            )
            or 0
        )
        peak = (
            int(
                causal.default_aim_schedule(policy).get(
                    "acquisition_end_output_tick"
                )
                or causal.default_aim_schedule(policy).get(
                    "pass_end_output_tick"
                )
                or response + 48
            )
        )
        sign = 1.0 if view_yaw_offset_deg >= 0 else -1.0
        yaw = sign * (8.0 + 2.0 * (ordinal % 3))
        pitch = (0.0, 4.0, -4.0)[ordinal % 3]
        return causal.shot_error_schedule(
            program,
            yaw_offset_deg=yaw,
            pitch_offset_deg=pitch,
            start_output_tick=response,
            peak_output_tick=peak,
            minimum_error_at_fire_deg=6.0,
            expected_center_before_first_fire=False,
        )
    if program == "spatial_transient":
        if fire_tick is None:
            raise AssertionError(program)
        directions = (
            (10.0, 0.0),
            (-10.0, 0.0),
            (0.0, 8.0),
            (0.0, -8.0),
            (8.0, 6.0),
            (-8.0, -6.0),
        )
        yaw, pitch = directions[ordinal % len(directions)]
        hold = min(310, fire_tick + max(2, fire_width - 1))
        return causal.shot_error_schedule(
            program,
            yaw_offset_deg=yaw,
            pitch_offset_deg=pitch,
            start_output_tick=max(0, fire_tick - 8),
            peak_output_tick=fire_tick,
            hold_end_output_tick=hold,
            return_end_output_tick=min(319, hold + 8),
            minimum_error_at_fire_deg=6.0,
            expected_center_before_first_fire=True,
        )
    if program == "spatial_undershoot_then_acquire":
        if policy != "delayed_acquisition" or fire_tick is None:
            raise AssertionError((policy, program, fire_tick))
        sign = 1.0 if view_yaw_offset_deg >= 0 else -1.0
        directions = (
            (sign * 10.0, 0.0),
            (sign * 8.0, 5.0),
            (sign * 8.0, -5.0),
        )
        yaw, pitch = directions[ordinal % len(directions)]
        fire_end = min(303, fire_tick + max(2, fire_width - 1))
        return causal.shot_error_schedule(
            program,
            yaw_offset_deg=yaw,
            pitch_offset_deg=pitch,
            start_output_tick=int(
                causal.default_aim_schedule(policy)[
                    "response_start_output_tick"
                ]
            ),
            peak_output_tick=int(
                causal.default_aim_schedule(policy)[
                    "acquisition_end_output_tick"
                ]
            ),
            hold_end_output_tick=fire_end,
            return_end_output_tick=min(319, fire_end + 24),
            minimum_error_at_fire_deg=6.0,
            expected_center_before_first_fire=False,
            expected_acquisition_after_first_fire=True,
        )
    minimum = {
        "timing_early_acquisition": 6.0,
        "timing_loss_window": 20.0,
        "timing_reacquisition_lag": 6.0,
        "pass_cross_and_depart": 6.0,
    }[program]
    return causal.shot_error_schedule(
        program,
        minimum_error_at_fire_deg=minimum,
        expected_center_before_first_fire=(
            program != "timing_early_acquisition"
        ),
        expected_acquisition_after_first_fire=(
            True if program == "timing_early_acquisition" else None
        ),
    )


def build_rows(
    *,
    miss_assignments: dict[
        str, tuple[tuple[int, bool, str], ...]
    ]
    | None = None,
) -> list[dict[str, Any]]:
    sources = source_rows()
    slots = treatment_slots(miss_assignments=miss_assignments)
    per_family_policy = Counter(
        (slot["family"], slot["policy"]) for slot in slots
    )
    seen = Counter()
    rows: list[dict[str, Any]] = []
    for ordinal, slot in enumerate(slots):
        family = int(slot["family"])
        policy = str(slot["policy"])
        program = str(slot["shot_error_program"])
        seen[(family, policy)] += 1
        arm = seen[(family, policy)]
        source = sources[family % len(sources)]
        row = copy.deepcopy(source)
        (
            screen_cell,
            screen_horizontal,
            screen_vertical,
            view_yaw,
            view_pitch,
        ) = SCREEN_CELLS[family]
        group_id = f"s2biasv1_g{family + 1:02d}"
        seed = 16_300_000 + family + 1
        policy_ordinal = causal.AIM_POLICIES.index(policy) + 1
        episode_id = (
            f"{group_id}_p{policy_ordinal:02d}_{policy}_a{arm:02d}"
        )
        target_yaw, target_pitch = causal.yaw_pitch_toward(
            row["player"]["origin"], row["enemy"]["origin"]
        )
        fire_width = 12 if row["weapon"] == "MachineGun" else 2
        ticks = fire_ticks(policy, program)
        schedule = aim_schedule(policy, program, view_yaw)
        shot_schedule = error_schedule(
            policy=policy,
            program=program,
            fire_tick=(ticks[0] if ticks else None),
            view_yaw_offset_deg=view_yaw,
            ordinal=ordinal,
            fire_width=fire_width,
        )

        row.update(
            {
                "schema_version": causal.SCENARIO_SCHEMA_V4,
                "action_program": causal.ACTION_PROGRAM_V4,
                "episode_id": episode_id,
                "counterfactual_group_id": group_id,
                "anchor_id": f"{group_id}_pair",
                "seed": seed,
                "assigned_shard": family % SHARD_COUNT,
                "shard_count": SHARD_COUNT,
                "category": f"stage2_bias_v1_{policy}",
                "candidate_kind": (
                    "stage2_screen_miss_bias_correction_v1"
                ),
                "candidate_status": (
                    "bounded_distribution_validation_candidate"
                ),
                "training_stage": (
                    "stage2_bounded_bias_correction_v1_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "human_review_required_before_training": True,
                "data_spec_sha256": capture.sha256_file(DATA_SPEC),
                "canary_role": (
                    f"stage2_bias_v1_{screen_cell}_{policy}_{program}"
                ),
                "expects_sound": policy != "visible_no_response",
                "initial_screen_design": {
                    "schema_version": (
                        causal.INITIAL_SCREEN_DESIGN_SCHEMA
                    ),
                    "screen_horizontal": screen_horizontal,
                    "screen_vertical": screen_vertical,
                    "view_yaw_offset_deg": view_yaw,
                    "view_pitch_offset_deg": view_pitch,
                    "expected_visible_at_output_start": True,
                },
            }
        )
        row.pop("supersession_contract", None)
        row.pop("outcome_calibration_design", None)
        row["player"]["yaw"] = round(
            causal.wrap_angle(target_yaw + view_yaw), 6
        )
        row["player"]["pitch"] = round(
            min(89.0, max(-89.0, target_pitch + view_pitch)), 6
        )
        row["enemy_policy"]["policy_seed"] = seed
        design = row["causal_design"]
        design.update(
            {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V4,
                "aim_policy": policy,
                "aim_schedule": schedule,
                "shot_error_schedule": shot_schedule,
                "shot_error_is_outcome_label": False,
                "acquisition_start_output_tick": int(
                    schedule.get("response_start_output_tick") or 0
                ),
                "fire_output_ticks": list(ticks),
                "fire_width_ticks": fire_width,
                "base_player_program": "stationary",
                "interaction_channel": "primary",
                "secondary_mechanism": None,
            }
        )
        row["policy_labels"].update(
            {
                "aim_policy": policy,
                "interaction_channel": "primary",
                "initial_screen_cell": screen_cell,
                "candidate_generation_outcome_arm": (
                    "no_fire"
                    if policy == "visible_no_response"
                    else (
                        "miss_diversity"
                        if program != "none"
                        else "centered_engagement"
                    )
                ),
                "shot_error_program": program,
                "actual_outcome_assignment": (
                    "post_capture_authoritative_telemetry_rebucket"
                ),
            }
        )
        row["acceptance"]["actual_outcome"] = None
        row["acceptance"]["actual_outcome_rebucket_required"] = True
        row["bias_correction_design"] = {
            "schema_version": (
                "xonotic-stage2-bias-correction-design-v1"
            ),
            "family_ordinal": family,
            "family_policy_multiplicity": per_family_policy[
                (family, policy)
            ],
            "treatment_arm_ordinal": arm,
            "initial_screen_cell": screen_cell,
            "shot_error_program": program,
            "candidate_generation_only": True,
            "actual_outcome_used_for_acceptance": False,
            "runtime_action_fallback": False,
            "runtime_geometry_fallback": False,
        }
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        causal.causal_action_rows(row)
        rows.append(row)
    return rows


def planned_treatment_metrics(
    row: dict[str, Any],
) -> dict[str, Any]:
    """Re-derive planned angular errors without using an outcome label."""
    actions = causal.causal_action_rows(row)
    yaw = float(row["player"]["yaw"])
    pitch = float(row["player"]["pitch"])
    errors: list[float] = []
    for action in actions:
        yaw = causal.wrap_angle(yaw + float(action["yaw_delta"]))
        pitch = min(
            89.0,
            max(-89.0, pitch + float(action["pitch_delta"])),
        )
        tick = int(action["tick"])
        if tick < capture.WARMUP_TICKS:
            continue
        target_yaw, target_pitch = causal.yaw_pitch_toward(
            row["player"]["origin"],
            causal.enemy_origin_at_server_tick(row, tick),
        )
        errors.append(
            math.hypot(
                causal.angle_delta(target_yaw, yaw),
                target_pitch - pitch,
            )
        )
    fire_ticks = [
        int(value)
        for value in row["causal_design"]["fire_output_ticks"]
    ]
    first_fire = min(fire_ticks) if fire_ticks else None
    return {
        "errors": errors,
        "fire_errors": [errors[tick] for tick in fire_ticks],
        "center_before_first_fire": (
            any(value <= causal.TARGET_CENTER_THRESHOLD_DEG for value in (
                errors[:first_fire] if first_fire is not None else []
            ))
        ),
        "acquisition_after_first_fire": (
            any(value <= causal.TARGET_CENTER_THRESHOLD_DEG for value in (
                errors[first_fire + 1 :] if first_fire is not None else []
            ))
        ),
    }


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {
        row["counterfactual_group_id"] for row in rows
    }
    group_members = {
        group: [
            row
            for row in rows
            if row["counterfactual_group_id"] == group
        ]
        for group in groups
    }
    policy_counts = Counter(
        row["causal_design"]["aim_policy"] for row in rows
    )
    horizontal = Counter(
        row["initial_screen_design"]["screen_horizontal"]
        for row in rows
    )
    vertical = Counter(
        row["initial_screen_design"]["screen_vertical"]
        for row in rows
    )
    screen_cells = Counter(
        row["policy_labels"]["initial_screen_cell"]
        for row in rows
    )
    miss_rows = [
        row
        for row in rows
        if row["causal_design"]["shot_error_schedule"]["program"]
        != "none"
    ]
    miss_programs = Counter(
        row["causal_design"]["shot_error_schedule"]["program"]
        for row in miss_rows
    )
    miss_policies = Counter(
        row["causal_design"]["aim_policy"] for row in miss_rows
    )
    treatment_metrics = {
        row["episode_id"]: planned_treatment_metrics(row)
        for row in rows
    }
    planned_shot_contracts = []
    for row in rows:
        schedule = row["causal_design"]["shot_error_schedule"]
        if schedule["program"] == "none":
            continue
        metrics = treatment_metrics[row["episode_id"]]
        minimum = float(schedule["minimum_error_at_fire_deg"])
        expected_before = schedule[
            "expected_center_before_first_fire"
        ]
        expected_after = schedule[
            "expected_acquisition_after_first_fire"
        ]
        planned_shot_contracts.append(
            bool(metrics["fire_errors"])
            and min(metrics["fire_errors"]) >= minimum
            and (
                expected_before is None
                or metrics["center_before_first_fire"]
                is expected_before
            )
            and (
                expected_after is None
                or metrics["acquisition_after_first_fire"]
                is expected_after
            )
        )
    centered_pass_rows = [
        row
        for row in rows
        if row["causal_design"]["aim_policy"] == "pass_offset"
        and row["causal_design"]["shot_error_schedule"]["program"]
        == "none"
    ]
    checks = {
        "rows_100": len(rows) == ROW_COUNT,
        "groups_15": len(groups) == GROUP_COUNT,
        "policy_targets": dict(policy_counts) == POLICY_TARGETS,
        "every_family_complete": all(
            {
                row["causal_design"]["aim_policy"]
                for row in members
            }
            == set(causal.AIM_POLICIES)
            for members in group_members.values()
        ),
        "exogenous_invariant_per_family": all(
            len(
                {
                    row["exogenous_contract_sha256"]
                    for row in members
                }
            )
            == 1
            for members in group_members.values()
        ),
        "initial_left_right_balanced": horizontal["left"]
        == horizontal["right"]
        == 47,
        "initial_center_capped": horizontal["center"] == 6,
        "upper_lower_both_covered": vertical["upper"] >= 35
        and vertical["lower"] >= 35,
        "four_quadrants_covered": all(
            screen_cells[cell] >= 10
            for cell in (
                "upper_left",
                "upper_right",
                "lower_left",
                "lower_right",
            )
        ),
        "miss_generation_arm_25": len(miss_rows) == 25,
        "miss_policy_targets": dict(miss_policies)
        == MISS_POLICY_TARGETS,
        "miss_program_diversity": set(miss_programs)
        == {
            "spatial_persistent",
            "spatial_transient",
            "timing_early_acquisition",
            "timing_loss_window",
            "timing_reacquisition_lag",
            "pass_cross_and_depart",
        },
        "legacy_cross_depart_is_minor": miss_programs[
            "pass_cross_and_depart"
        ]
        <= 3,
        "planned_shot_error_contracts": all(
            planned_shot_contracts
        ),
        "nonmiss_pass_returns_to_center": all(
            treatment_metrics[row["episode_id"]]["fire_errors"]
            and max(
                treatment_metrics[row["episode_id"]][
                    "fire_errors"
                ]
            )
            <= causal.TARGET_CENTER_THRESHOLD_DEG
            for row in centered_pass_rows
        ),
        "telemetry_outcome_only": all(
            row["acceptance"]["actual_outcome"] is None
            and row["causal_design"]["shot_error_is_outcome_label"]
            is False
            for row in rows
        ),
        "formal_collection_forbidden": all(
            row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
            for row in rows
        ),
    }
    return {
        "schema_version": "xonotic-stage2-bias-correction-audit-v1",
        "pass": all(checks.values()),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "checks": checks,
        "rows": len(rows),
        "counterfactual_families": len(groups),
        "aim_policy": dict(policy_counts),
        "initial_screen_horizontal": dict(horizontal),
        "initial_screen_vertical": dict(vertical),
        "initial_screen_cells": dict(screen_cells),
        "candidate_generation_outcome_arm": dict(
            Counter(
                row["policy_labels"][
                    "candidate_generation_outcome_arm"
                ]
                for row in rows
            )
        ),
        "miss_policy": dict(miss_policies),
        "miss_program": dict(miss_programs),
        "interpretation": (
            "Shot-error arms are generation priors only. Actual no-fire, "
            "miss, hit-survive, and kill labels are assigned after capture "
            "from authoritative telemetry."
        ),
    }


def materialize(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    rows = build_rows()
    audit = audit_rows(rows)
    if audit["pass"] is not True:
        raise capture.CaptureFailure(
            "stage2_bias_design_audit_failed",
            capture.canonical_json(audit["checks"]),
        )
    text = canonical_lines(rows)
    input_path = output_root / "input.jsonl"
    write_once_or_verify(input_path, text)
    shard_rows = [
        [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard
        ]
        for shard in range(SHARD_COUNT)
    ]
    shard_paths = [
        output_root
        / "shards"
        / f"shard-{shard:03d}-of-{SHARD_COUNT:03d}.jsonl"
        for shard in range(SHARD_COUNT)
    ]
    for path, items in zip(shard_paths, shard_rows):
        write_once_or_verify(path, canonical_lines(items))
    metadata = {
        "schema_version": (
            "xonotic-stage2-bias-correction-manifest-v1"
        ),
        "source_manifest": str(SOURCE.relative_to(ROOT)),
        "source_manifest_sha256": capture.sha256_file(SOURCE),
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(DATA_SPEC),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "actual_outcome_source": "authoritative_telemetry_only",
        "review": {
            "rows": len(rows),
            "counterfactual_families": GROUP_COUNT,
            "shard_count": SHARD_COUNT,
            "shards": [
                {
                    "shard_index": index,
                    "path": str(path),
                    "rows": len(items),
                    "sha256": hashlib.sha256(
                        canonical_lines(items).encode("utf-8")
                    ).hexdigest(),
                }
                for index, (path, items) in enumerate(
                    zip(shard_paths, shard_rows)
                )
            ],
        },
    }
    write_once_or_verify(
        output_root / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    write_once_or_verify(
        output_root / "DESIGN_AUDIT.json",
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
    )
    return audit


def main() -> int:
    audit = materialize()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
