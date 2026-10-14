                      
"""Prepare an immutable, weapon-balanced Stage-2 non-training review.

Each weapon reuses one already accepted, collision-certified player trace.
The eight counterfactual arms share map, player trace, enemy policy, and
initial geometry.  Only the manifest-frozen aim and primary-fire programs
change.  Realized target damage is measured after capture and is never an
episode admission gate.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import math
import os
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_humanized_review_v2 as human_v2              
import prepare_stage2_stochastic_review_v1 as stochastic_v1              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_MANIFEST = (
    ROOT
    / "manifests/stage2_prefrozen_player_motion_review_v1"
    / "selected_input.jsonl"
)
SOURCE_AUDIT = (
    ROOT
    / "stage2_prefrozen_player_motion_review_v1_output"
    / "SELECTED_ARTIFACT_AUDIT.json"
)
COHORT_VERSION = os.environ.get(
    "STAGE2_WEAPON_BALANCED_COHORT_VERSION", "v1"
)
if COHORT_VERSION not in {"v1", "v2", "v3"}:
    raise RuntimeError(
        f"unsupported Stage-2 weapon-balanced cohort: {COHORT_VERSION}"
    )
COHORT_ORDINAL = int(COHORT_VERSION[1:])
OUTPUT_ROOT = (
    ROOT
    / f"manifests/stage2_weapon_balanced_review_{COHORT_VERSION}"
)
SHARD_COUNT = 4
MANIFEST_SCHEMA = (
    "xonotic-stage2-weapon-balanced-review-manifest-"
    f"{COHORT_VERSION}"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-weapon-balanced-review-design-"
    f"{COHORT_VERSION}"
)
STATIC_CERTIFICATE_SCHEMA = (
    "xonotic-stage2-weapon-balanced-static-action-certificate-"
    f"{COHORT_VERSION}"
)
SELECTION_CONTRACT_SCHEMA = (
    "xonotic-stage2-weapon-balanced-selection-contract-"
    f"{COHORT_VERSION}"
)
ARMS = causal.WEAPON_BALANCED_AIM_ARMS
WEAPONS = human_v2.WEAPONS
TARGET_HIT_RATE_BANDS = {
    "Blaster": (0.35, 0.45),
    "Shotgun": (0.45, 0.55),
    "MachineGun": (0.30, 0.40),
    "Mortar": (0.30, 0.40),
    "Electro": (0.35, 0.45),
    "Crylink": (0.40, 0.50),
    "Vortex": (0.30, 0.40),
    "Hagar": (0.30, 0.40),
    "Devastator": (0.35, 0.45),
}
ARM_PARAMETERS = {
    "stable_track": {
        "family": "humanized_target_conditioned",
        "style": "direct_smooth",
        "response": 24,
        "settle": 88,
        "scale": 0.08,
        "radius": "target_hull",
        "lead": True,
    },
    "overshoot_correct": {
        "family": "humanized_target_conditioned",
        "style": "overshoot_correct",
        "response": 20,
        "settle": 100,
        "scale": 0.10,
        "radius": "target_hull",
        "lead": True,
    },
    "predictive_track": {
        "family": "humanized_target_conditioned",
        "style": "direct_smooth",
        "response": 28,
        "settle": 88,
        "scale": 0.20,
        "radius": "target_hull",
        "lead": True,
    },
    "edge_graze": {
        "family": "humanized_target_conditioned",
        "style": "direct_smooth",
        "response": 24,
        "settle": 92,
        "scale": 0.82,
        "radius": "weapon_effective_damage",
        "lead": True,
    },
    "near_miss": {
        "family": "humanized_target_conditioned",
        "style": "direct_smooth",
        "response": 24,
        "settle": 92,
        "scale": 1.28,
        "radius": "weapon_effective_damage",
        "lead": True,
    },
    "stochastic_local": {
        "family": "stochastic_free_aim",
        "response": 24,
        "settle": 88,
        "scale": 0.0,
        "radius": "target_hull",
        "lead": False,
    },
    "stochastic_broad": {
        "family": "stochastic_free_aim",
        "response": 24,
        "settle": 88,
        "scale": 0.0,
        "radius": "target_hull",
        "lead": False,
    },
    "visible_no_fire": {
        "family": "visible_no_fire",
        "response": 24,
        "settle": 88,
        "scale": 0.0,
        "radius": "target_hull",
        "lead": False,
    },
}


def source_commit() -> str:
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT / "source/release-src-0.8.6/Xonotic"),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(
        capture.canonical_json(row) + "\n" for row in rows
    )


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = text.encode("utf-8")
    if path.exists():
        if path.read_bytes() != payload:
            raise capture.CaptureFailure(
                "refuse_overwrite_weapon_balanced_manifest_drift",
                str(path),
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def selected_sources() -> dict[str, tuple[dict[str, Any], Path]]:
    selected = capture.load_jsonl(SOURCE_MANIFEST)
    by_episode = {
        str(row["episode_id"]): row for row in selected
    }
    audit = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    if audit.get("passed") is not True:
        raise capture.CaptureFailure(
            "stage2_weapon_balanced_source_audit_failed",
            str(SOURCE_AUDIT),
        )
    artifact_by_episode = {
        str(row["episode_id"]): Path(str(row["artifact_path"]))
        for row in audit["episode_results"]
        if row.get("passed") is True
    }
    result: dict[str, tuple[dict[str, Any], Path]] = {}
    for weapon in WEAPONS:
        candidates = [
            row
            for row in selected
            if row["weapon"] == weapon
            and str(row["episode_id"]).endswith("broad_sparse")
        ]
        if len(candidates) != 1:
            raise capture.CaptureFailure(
                "stage2_weapon_balanced_source_shape",
                capture.canonical_json(
                    {"weapon": weapon, "count": len(candidates)}
                ),
            )
        row = candidates[0]
        episode_id = str(row["episode_id"])
        if by_episode.get(episode_id) != row:
            raise AssertionError(episode_id)
        package = artifact_by_episode.get(episode_id)
        if package is None or not (package / "states.parquet").is_file():
            raise capture.CaptureFailure(
                "stage2_weapon_balanced_source_artifact_missing",
                episode_id,
            )
        result[weapon] = (row, package)
    return result


def frozen_trace_action_text(source: dict[str, Any]) -> str:
    rows = copy.deepcopy(causal.causal_action_rows(source))
    for row in rows:
        row["primary"] = 0
        row["secondary"] = 0
        row["reload"] = 0
        row["weapon_impulse"] = 0
    capture.validate_model_action_source_rows(rows)
    buffer = io.StringIO(newline="")
    buffer.write(f"#seed,{source['seed']}\n")
    writer = csv.DictWriter(
        buffer, fieldnames=capture.ACTION_COLUMNS
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def random_aim_program(
    seed: int, arm: str, weapon: str
) -> dict[str, Any]:
    if arm not in {
        "stochastic_local",
        "stochastic_broad",
        "visible_no_fire",
    }:
        raise ValueError(arm)
    max_yaw, max_pitch = (
        (15.0, 8.0)
        if arm in {"stochastic_local", "visible_no_fire"}
        else (34.0, 16.0)
    )
    if COHORT_VERSION in {"v2", "v3"}:
        ticks = (
            [0, 40, 72, 96, 136, 176, 200, 240, 280, 319]
            if weapon == "Vortex"
            else [0, 40, 80, 104, 144, 184, 224, 264, 319]
        )
        fire_ticks = (
            {96, 200} if weapon == "Vortex" else {104, 184}
        )
    else:
        ticks = [0, 40, 80, 120, 160, 200, 240, 280, 319]
        fire_ticks = set()
    for candidate in range(1024):
        rng = random.Random(seed + candidate * 1_000_003)
        yaw = [0.0] + [
            round(rng.uniform(-max_yaw, max_yaw), 6)
            for _ in ticks[1:]
        ]
        pitch = [
            (
                0.0
                if index == 0
                or (
                    COHORT_VERSION in {"v2", "v3"}
                    and tick in fire_ticks
                )
                else round(
                    rng.uniform(-max_pitch, max_pitch), 6
                )
            )
            for index, tick in enumerate(ticks)
        ]
        if (
            max(yaw) - min(yaw) >= 12.0
            and max(pitch) - min(pitch) >= 5.0
            and min(yaw) < -3.0
            and max(yaw) > 3.0
            and min(pitch) < -1.5
            and max(pitch) > 1.5
        ):
            program = {
                "schema_version": causal.RANDOM_AIM_PROGRAM_SCHEMA,
                "seed": seed,
                "algorithm": (
                    "manifest_frozen_piecewise_smooth_view_v1"
                ),
                "interpolation": "smoothstep",
                "knot_output_ticks": ticks,
                "yaw_offset_deg": yaw,
                "pitch_offset_deg": pitch,
                "max_abs_yaw_offset_deg": max_yaw,
                "max_abs_pitch_offset_deg": max_pitch,
                "reads_live_enemy_state": False,
                "reads_live_player_state": False,
                "reads_camera": False,
                "reads_crosshair": False,
            }
            causal.validate_random_aim_program(program)
            return program
    raise capture.CaptureFailure(
        "stage2_weapon_balanced_random_aim_exhausted",
        f"seed={seed} arm={arm}",
    )


def aim_program(
    weapon_index: int,
    arm_index: int,
    arm: str,
    weapon: str,
) -> dict[str, Any]:
    parameters = ARM_PARAMETERS[arm]
    seed = 16_100_000 + weapon_index * 100 + arm_index + 1
    humanized = arm in causal.WEAPON_BALANCED_HUMANIZED_ARMS
    direction_rng = random.Random(
        202607300000 + weapon_index * 101 + arm_index
    )
    direction = round(direction_rng.uniform(-180.0, 180.0), 6)
    if (
        COHORT_VERSION in {"v2", "v3"}
        and arm in {"edge_graze", "near_miss"}
    ):
                                                                       
                                                                         
                                                                      
                                    
        direction = 0.0 if direction >= 0.0 else 180.0
    scale = float(parameters["scale"])
    if (
        COHORT_VERSION in {"v2", "v3"}
        and weapon in {"MachineGun", "Vortex"}
    ):
        if arm == "edge_graze":
            scale = 1.08
        elif arm == "near_miss":
            scale = 1.80
    program = {
        "schema_version": (
            causal.WEAPON_BALANCED_AIM_PROGRAM_SCHEMA
        ),
        "seed": seed,
        "arm": arm,
        "family": parameters["family"],
        "algorithm": (
            "manifest_frozen_weapon_conditioned_view_v1"
        ),
        "response_start_output_tick": parameters["response"],
        "settle_output_tick": parameters["settle"],
        "target_offset_scale": scale,
        "offset_direction_deg": direction,
        "offset_radius_kind": parameters["radius"],
        "projectile_lead": bool(parameters["lead"]),
        "motor_profile": (
            causal.humanized_aim_motor_profile(
                seed, str(parameters["style"])
            )
            if humanized
            else None
        ),
        "random_aim_program": (
            None
            if humanized
            else random_aim_program(seed, arm, weapon)
        ),
        "target_radius_model": (
            "camera_to_torso_elliptical_hull_plus_weapon_radius_v1"
        ),
        "reads_live_enemy_state": False,
        "reads_live_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
    }
    causal.validate_weapon_balanced_aim_program(program)
    return program


def fire_program(weapon: str, no_fire: bool) -> dict[str, Any]:
    if no_fire:
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
    starts = (
        [96, 200]
        if weapon == "Vortex"
        else [104, 184]
    )
    return {
        "schema_version": causal.FIRE_PROGRAM_SCHEMA,
        "name": "multi_tap",
        "weapon_fire_family": stochastic_v1.FIRE_FAMILY[weapon],
        "windows": [
            {
                "start_output_tick": start,
                "duration_ticks": 2,
            }
            for start in starts
        ],
        "expected_min_fire_events": 2,
        "expected_max_fire_events": 2,
        "requires_multiple_fire_events": True,
        "selection_uses_authoritative_events": True,
    }


def direction_reversals(values: list[float]) -> int:
    signs = [
        1 if value > 1e-5 else -1
        for value in values
        if abs(value) > 1e-5
    ]
    return sum(
        left != right for left, right in zip(signs, signs[1:])
    )


def static_action_certificate(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    actions = causal.causal_action_rows(scenario)
    output = actions[capture.WARMUP_TICKS :]
    left_x = [
        float(row["strafe"])
        / capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE
        for row in output
    ]
    left_y = [
        -float(row["forward"])
        / capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE
        for row in output
    ]
    yaw = [float(row["yaw_delta"]) for row in output]
    pitch = [float(row["pitch_delta"]) for row in output]
    primary = [bool(row["primary"]) for row in output]
    no_fire = (
        scenario["causal_design"]["aim_policy"]
        == "visible_no_fire"
    )
    last_primary = max(
        (index for index, active in enumerate(primary) if active),
        default=-1,
    )
    checks = {
        "rows_exact": len(actions) == capture.TOTAL_TICKS,
        "warmup_neutral": all(
            float(row["forward"]) == 0.0
            and float(row["strafe"]) == 0.0
            and float(row["yaw_delta"]) == 0.0
            and float(row["pitch_delta"]) == 0.0
            and int(row["jump"]) == 0
            and int(row["primary"]) == 0
            for row in actions[: capture.WARMUP_TICKS]
        ),
        "movement_present": sum(
            math.hypot(x, y) > 0.05
            for x, y in zip(left_x, left_y)
        )
        >= 192,
        "two_axis_movement": any(abs(value) > 0.05 for value in left_x)
        and any(abs(value) > 0.05 for value in left_y),
        "movement_in_model_range": max(
            abs(value) for value in left_x + left_y
        )
        <= 1.0,
        "jump_absent": not any(int(row["jump"]) for row in actions),
        "two_axis_view": any(abs(value) > 1e-5 for value in yaw)
        and any(abs(value) > 1e-5 for value in pitch),
        "view_in_model_range": max(abs(value) for value in yaw) <= 12.0
        and max(abs(value) for value in pitch) <= 12.0,
        "fire_contract": (not any(primary))
        if no_fire
        else any(primary),
        "projectile_observation_window": (
            scenario["weapon"]
            not in causal.PROJECTILE_PRIMARY_WEAPONS
            or no_fire
            or last_primary
            <= causal.LATEST_PROJECTILE_FIRE_OUTPUT_TICK
        ),
        "secondary_absent": not any(
            bool(row["secondary"]) for row in output
        ),
        "reload_absent": not any(bool(row["reload"]) for row in output),
    }
    return {
        "schema_version": STATIC_CERTIFICATE_SCHEMA,
        "checks": checks,
        "passed": all(checks.values()),
        "movement_active_frames": sum(
            math.hypot(x, y) > 0.05
            for x, y in zip(left_x, left_y)
        ),
        "maximum_abs_left_x": max(abs(value) for value in left_x),
        "maximum_abs_left_y": max(abs(value) for value in left_y),
        "left_x_direction_reversals": direction_reversals(left_x),
        "left_y_direction_reversals": direction_reversals(left_y),
        "maximum_yaw_step_deg": max(abs(value) for value in yaw),
        "maximum_pitch_step_deg": max(abs(value) for value in pitch),
        "primary_active_frames": sum(primary),
        "last_primary_active_output_tick": last_primary,
        "actions_sha256": hashlib.sha256(
            capture.canonical_json(actions).encode("utf-8")
        ).hexdigest(),
    }


def selection_contract() -> dict[str, Any]:
    return {
        "schema_version": SELECTION_CONTRACT_SCHEMA,
        "selection_unit": "weapon_arm_episode",
        "all_live_qa_gates_required": True,
        "realized_outcome_is_not_episode_admission": True,
        "target_outcome_definition": (
            "authoritative_damage_to_declared_enemy_resolved_to_fire_root"
        ),
        "projectile_negative_observation_ticks": (
            causal.PROJECTILE_OUTCOME_OBSERVATION_TICKS
        ),
        "target_hit_rate_bands": {
            weapon: {"minimum": bounds[0], "maximum": bounds[1]}
            for weapon, bounds in TARGET_HIT_RATE_BANDS.items()
        },
        "mechanism_accounting": [
            "direct",
            "splash",
            "pellet",
        ],
        "calibration_policy": (
            "if_a_weapon_misses_its_band_create_a_new_immutable_"
            "replenishment_manifest_never_outcome_filter_this_manifest"
        ),
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
    }


def materialize() -> list[dict[str, Any]]:
    commit = source_commit()
    sources = selected_sources()
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    trace_sources: dict[str, dict[str, Any]] = {}
    geometry_sources: dict[
        str, tuple[dict[str, Any], Path]
    ] = {}
    for weapon in WEAPONS:
        geometry_weapon = (
            "Mortar"
            if COHORT_VERSION == "v3"
            and weapon in causal.PROJECTILE_PRIMARY_WEAPONS
            else weapon
        )
        geometry_sources[weapon] = sources[geometry_weapon]
    for weapon, (source, package) in geometry_sources.items():
        action_text = frozen_trace_action_text(source)
        action_path = (
            OUTPUT_ROOT
            / "base_traces"
            / f"{capture.WEAPON_NETNAME[weapon]}.csv"
        )
        write_once_or_verify(action_path, action_text)
        states_path = package / "states.parquet"
        trace_sources[weapon] = {
            "schema_version": causal.PREFROZEN_TRACE_SOURCE_SCHEMA,
            "source_episode_id": source["episode_id"],
            "source_commit": commit,
            "actions_path": str(action_path.relative_to(ROOT)),
            "actions_sha256": capture.sha256_file(action_path),
            "states_path": str(states_path.relative_to(ROOT)),
            "states_sha256": capture.sha256_file(states_path),
            "position_error_p95_max": 24.0,
            "position_error_max_max": 48.0,
            "runtime_action_fallback": False,
            "runtime_geometry_fallback": False,
        }

    contract = selection_contract()
    contract_hash = hashlib.sha256(
        capture.canonical_json(contract).encode("utf-8")
    ).hexdigest()
    rows: list[dict[str, Any]] = []
    for weapon_index, weapon in enumerate(WEAPONS):
        source, _ = geometry_sources[weapon]
        weapon_template, _ = sources[weapon]
        group_id = (
            f"s2wb{COHORT_VERSION}_g{weapon_index + 1:02d}_"
            f"{capture.WEAPON_NETNAME[weapon]}"
        )
        for arm_index, arm in enumerate(ARMS):
            row_ordinal = len(rows)
            row = copy.deepcopy(source)
            for key in (
                "encounter_certificate",
                "target_motion_review_design",
                "bias_correction_design",
                "humanized_review_design",
                "stochastic_review_design",
                "prefrozen_player_motion_review_design",
                "prefrozen_player_motion_replenishment_design",
            ):
                row.pop(key, None)
            aim = aim_program(
                weapon_index, arm_index, arm, weapon
            )
            no_fire = arm == "visible_no_fire"
            fire = fire_program(weapon, no_fire)
            fire_seed = (
                16_300_000 + weapon_index * 100 + arm_index + 1
            )
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V9,
                    "action_program": causal.ACTION_PROGRAM_V9,
                    "episode_id": f"{group_id}_{arm}",
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_eight_arm",
                    "source_commit_required": commit,
                    "category": (
                        "stage2_weapon_balanced_humanized_stochastic_"
                        "primary_interaction"
                    ),
                    "candidate_kind": (
                        "stage2_weapon_balanced_review_"
                        f"{COHORT_VERSION}"
                    ),
                    "candidate_status": (
                        "static_certified_pending_live_capture_and_"
                        "authoritative_weapon_calibration"
                    ),
                    "training_stage": (
                        "stage2_weapon_balanced_review_"
                        f"{COHORT_VERSION}_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "human_review_required_before_training": True,
                    "canary_role": (
                        f"stage2_weapon_balanced_{weapon.lower()}_{arm}"
                    ),
                    "data_spec_sha256": data_spec_sha256,
                    "shard_count": SHARD_COUNT,
                    "assigned_shard": row_ordinal % SHARD_COUNT,
                    "target_ordinal": row_ordinal,
                    "split": (
                        "stage2_weapon_balanced_nontraining_review"
                    ),
                    "prefrozen_trace_source": (
                        trace_sources[weapon]
                    ),
                    "weapon": weapon,
                    "weapon_netname": capture.WEAPON_NETNAME[weapon],
                }
            )
            row["player"]["clip"] = weapon_template["player"][
                "clip"
            ]
            row["player"]["reserve"] = weapon_template["player"][
                "reserve"
            ]
            row["causal_design"] = {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V9,
                "aim_policy": arm,
                "aim_reference": (
                    "manifest_frozen_analytic_enemy_and_player_"
                    "trajectories"
                ),
                "weapon_balanced_aim_program": aim,
                "fire_seed": fire_seed,
                "fire_program": fire,
                "fire_output_ticks": [
                    int(window["start_output_tick"])
                    for window in fire["windows"]
                ],
                "fire_width_ticks": 2,
                "interaction_channel": "primary",
                "secondary_mechanism": None,
                "base_player_program": (
                    "certified_prefrozen_trace_replay"
                ),
                "player_health_policy": "player_alive",
                "actual_outcome_source": (
                    "authoritative_target_damage_parent_chain_per_shot"
                ),
                "intended_outcome_is_acceptance_gate": False,
                "reads_live_enemy_state": False,
                "reads_live_player_state": False,
                "reads_camera": False,
                "reads_crosshair": False,
            }
            row["acceptance"] = {
                "actual_outcome": None,
                "actual_outcome_rebucket_required": True,
                "fire_required": not no_fire,
                "reload_success": False,
                "player_motion_qa_required": True,
                "player_self_damage_allowed": True,
                "player_death_allowed": False,
            }
            row["policy_labels"] = {
                "aim_policy": arm,
                "aim_family": aim["family"],
                "interaction_channel": "primary",
                "initial_screen_cell": (
                    str(row["initial_screen_design"]["screen_horizontal"])
                    + "_"
                    + str(
                        row["initial_screen_design"]["screen_vertical"]
                    )
                ),
                "target_motion_name": row["enemy_policy"]["name"],
                "player_motion_class": (
                    "certified_prefrozen_trace_replay"
                ),
                "outcome_assignment": (
                    "post_capture_authoritative_target_damage_per_shot"
                ),
            }
            row["encounter_source"][
                "current_trajectory_requires_recertification"
            ] = True
            row["encounter_source"][
                "source_geometry_used_as_runtime_fallback"
            ] = False
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            certificate = static_action_certificate(row)
            if not certificate["passed"]:
                raise capture.CaptureFailure(
                    "stage2_weapon_balanced_static_action_failed",
                    capture.canonical_json(
                        {
                            "episode_id": row["episode_id"],
                            "certificate": certificate,
                        }
                    ),
                )
            row["weapon_balanced_review_design"] = {
                "schema_version": DESIGN_SCHEMA,
                "source_manifest": str(
                    SOURCE_MANIFEST.relative_to(ROOT)
                ),
                "source_audit": str(
                    SOURCE_AUDIT.relative_to(ROOT)
                ),
                "source_episode_id": source["episode_id"],
                "arm": arm,
                "arm_index": arm_index,
                "aim_seed": aim["seed"],
                "fire_seed": fire_seed,
                "enemy_policy_seed": row["enemy_policy"][
                    "policy_seed"
                ],
                "selection_contract_sha256": contract_hash,
                "target_hit_rate_band": {
                    "minimum": TARGET_HIT_RATE_BANDS[weapon][0],
                    "maximum": TARGET_HIT_RATE_BANDS[weapon][1],
                },
                "static_action_certificate": certificate,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
                "runtime_outcome_fallback": False,
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
        if len(members) != len(ARMS):
            raise capture.CaptureFailure(
                "stage2_weapon_balanced_group_shape", group_id
            )
        if {
            row["causal_design"]["aim_policy"] for row in members
        } != set(ARMS):
            raise capture.CaptureFailure(
                "stage2_weapon_balanced_group_arms", group_id
            )
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_weapon_balanced_group_exogenous_drift",
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
        "source_manifest": {
            "path": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(SOURCE_MANIFEST),
        },
        "source_audit": {
            "path": str(SOURCE_AUDIT.relative_to(ROOT)),
            "sha256": capture.sha256_file(SOURCE_AUDIT),
        },
        "source_commit": commit,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "counterfactual_groups": len(WEAPONS),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "selection_contract": contract,
        "selection_contract_sha256": contract_hash,
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "arm_distribution": dict(
            Counter(
                row["causal_design"]["aim_policy"] for row in rows
            )
        ),
        "aim_family_distribution": dict(
            Counter(
                row["causal_design"]["weapon_balanced_aim_program"][
                    "family"
                ]
                for row in rows
            )
        ),
        "firing_arms_per_weapon": 7,
        "humanized_firing_arms_per_weapon": 5,
        "stochastic_firing_arms_per_weapon": 2,
        "no_fire_arms_per_weapon": 1,
        "requested_fire_events_per_firing_arm": 2,
        "geometry_source_episode_by_weapon": {
            weapon: source["episode_id"]
            for weapon, (source, _) in geometry_sources.items()
        },
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_weapon_balanced_review_v1.py",
                *(
                    (
                        "scripts/prepare_stage2_weapon_balanced_review_v2.py",
                    )
                    if COHORT_VERSION == "v2"
                    else ()
                ),
                *(
                    (
                        "scripts/prepare_stage2_weapon_balanced_review_v3.py",
                    )
                    if COHORT_VERSION == "v3"
                    else ()
                ),
            )
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
        capture.canonical_json(
            {
                "output": str(OUTPUT_ROOT),
                "rows": len(rows),
                "groups": len(
                    {
                        row["counterfactual_group_id"]
                        for row in rows
                    }
                ),
                "source_commit": source_commit(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
