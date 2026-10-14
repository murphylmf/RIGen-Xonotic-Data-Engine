                      
"""Shared immutable design helpers for Stage-2 formal manifests."""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_formal_canary_v1 as canary_v1              
import prepare_stage2_stochastic_review_v1 as stochastic_v1              
import prepare_stage2_weapon_balanced_review_v4 as v4              
import xonotic_capture as capture              
import xonotic_stage2_causal_formal as formal              


PREFLIGHT_REPORT = ROOT / "preflight_v2/PREFLIGHT_REPORT.json"
CONTENT_CATALOG = ROOT / "configs/OFFICIAL_V2_CONTENT_CATALOG.json"
DATA_SPEC = ROOT / "XONOTIC_DATA_SPEC_V2.md"
WEAPONS = v4.WEAPONS
INELIGIBLE_GAMETYPES = {"nb", "rc", "race", "cts"}
FORMAL_DESIGN_SCHEMA = "xonotic-stage2-formal-design-v1"
COLORS = (0, 68, 204)
SURVIVE_HEALTH = canary_v1.SURVIVE_HEALTH
                                                                    
                                                                          
                                                                         
                                                                            
                                                                             
KILL_HEALTH_BY_WEAPON = {
    weapon: 1.0 for weapon in canary_v1.KILL_HEALTH_BY_WEAPON
}
PRECISE_ARMS = (
    "stable_track",
    "overshoot_correct",
    "predictive_track",
)
HUMANIZED_MISS_ARMS = ("edge_graze", "near_miss")
STOCHASTIC_ARMS = ("stochastic_local", "stochastic_broad")


def aim_family_bucket(arm: str) -> str:
    if arm == "visible_no_fire":
        return "visible_no_fire"
    if arm in PRECISE_ARMS:
        return "precise_tracking"
    if arm in HUMANIZED_MISS_ARMS:
        return "humanized_offset_tracking"
    if arm in STOCHASTIC_ARMS:
        return "stochastic_aim_and_fire"
    raise ValueError(arm)


@functools.lru_cache(maxsize=1)
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


@functools.lru_cache(maxsize=1)
def data_spec_sha256() -> str:
    return capture.sha256_file(DATA_SPEC)


@functools.lru_cache(maxsize=1)
def preflight_report_sha256() -> str:
    return capture.sha256_file(PREFLIGHT_REPORT)


@functools.lru_cache(maxsize=1)
def preflight_pairs() -> list[dict[str, Any]]:
    report = json.loads(PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    rows = [
        {
            "map": str(map_row["map"]),
            "gametype": str(map_row["gametype"]).lower(),
            **pair,
        }
        for map_row in report["map_summary"]
        for pair in map_row["accepted_pairs"]
        if pair.get("pass") is True
        and str(map_row["gametype"]).lower()
        not in INELIGIBLE_GAMETYPES
    ]
    if len(rows) != 63 or len({row["map"] for row in rows}) != 27:
        raise capture.CaptureFailure(
            "stage2_formal_preflight_pool_shape",
            capture.canonical_json(
                {
                    "rows": len(rows),
                    "maps": len({row["map"] for row in rows}),
                }
            ),
        )
    return sorted(
        rows,
        key=lambda row: (
            row["distance_bin"],
            row["map"],
            row["episode_id"],
        ),
    )


@functools.lru_cache(maxsize=1)
def official_appearances() -> list[dict[str, Any]]:
    rows = list(
        json.loads(CONTENT_CATALOG.read_text(encoding="utf-8"))[
            "enemy_appearances"
        ]
    )
    if len(rows) != 14:
        raise capture.CaptureFailure(
            "stage2_formal_appearance_pool_shape", str(len(rows))
        )
    return rows


@functools.lru_cache(maxsize=1)
def weapon_templates() -> dict[tuple[str, str], dict[str, Any]]:
    return canary_v1.source_rows()


def tangent_vector(
    player_origin: list[float], enemy_origin: list[float]
) -> list[float]:
    dx = float(enemy_origin[0]) - float(player_origin[0])
    dy = float(enemy_origin[1]) - float(player_origin[1])
    length = math.hypot(dx, dy)
    if length < 1.0:
        raise capture.CaptureFailure(
            "stage2_formal_pair_too_close",
            capture.canonical_json(
                {"player": player_origin, "enemy": enemy_origin}
            ),
        )
    return [
        round(-dy / length, 9),
        round(dx / length, 9),
        0.0,
    ]


def fire_program(
    weapon: str, outcome_recipe: str
) -> tuple[dict[str, Any], list[int]]:
    if outcome_recipe == "no_fire":
        return (
            {
                "schema_version": formal.FIRE_PROGRAM_SCHEMA,
                "name": "none",
                "weapon_fire_family": "none",
                "windows": [],
                "expected_min_fire_events": 0,
                "expected_max_fire_events": 0,
                "requires_multiple_fire_events": False,
                "selection_uses_authoritative_events": True,
            },
            [],
        )
    first = 96 if weapon == "Vortex" else 104
    if outcome_recipe in {"hit_survive", "kill"}:
        return (
            {
                "schema_version": formal.FIRE_PROGRAM_SCHEMA,
                "name": "single_tap",
                "weapon_fire_family": stochastic_v1.FIRE_FAMILY[weapon],
                "windows": [
                    {
                        "start_output_tick": first,
                        "duration_ticks": 2,
                    }
                ],
                "expected_min_fire_events": 1,
                "expected_max_fire_events": 1,
                "requires_multiple_fire_events": False,
                "selection_uses_authoritative_events": True,
            },
            [first],
        )
    if outcome_recipe != "miss":
        raise ValueError(outcome_recipe)
    starts = [96, 200] if weapon == "Vortex" else [104, 184]
    return (
        {
            "schema_version": formal.FIRE_PROGRAM_SCHEMA,
            "name": "multi_tap",
            "weapon_fire_family": stochastic_v1.FIRE_FAMILY[weapon],
            "windows": [
                {"start_output_tick": tick, "duration_ticks": 2}
                for tick in starts
            ],
            "expected_min_fire_events": 2,
            "expected_max_fire_events": 2,
            "requires_multiple_fire_events": True,
            "selection_uses_authoritative_events": True,
        },
        starts,
    )


def aim_program(
    *,
    weapon: str,
    arm: str,
    ordinal: int,
    fire_ticks: list[int],
) -> dict[str, Any]:
    family, style, response, settle = v4.ARM_PARAMETERS[arm]
                                                                           
                                                                       
    seed = 15_800_000 + ordinal + 1
    humanized = arm in formal.WEAPON_BALANCED_HUMANIZED_ARMS
    miss = arm in HUMANIZED_MISS_ARMS
    rng = random.Random(202_607_310_000 + ordinal)
    if miss:
        base_direction = 0.0 if ordinal % 2 == 0 else 180.0
        direction = round(
            formal.wrap_angle(
                base_direction + rng.uniform(-20.0, 20.0)
            ),
            6,
        )
        scale = round(
            min(
                2.5,
                float(v4.MISS_SCALE_BY_WEAPON[weapon][arm])
                * rng.uniform(0.90, 1.10),
            ),
            6,
        )
    else:
        direction = round(rng.uniform(-180.0, 180.0), 6)
        scale = 0.0
    program = {
        "schema_version": formal.WEAPON_BALANCED_AIM_PROGRAM_SCHEMA,
        "seed": seed,
        "arm": arm,
        "family": family,
        "algorithm": "manifest_frozen_weapon_conditioned_view_v1",
        "response_start_output_tick": response,
        "settle_output_tick": settle,
        "target_offset_scale": scale,
        "offset_direction_deg": direction,
        "offset_radius_kind": (
            "weapon_effective_damage" if miss else "target_hull"
        ),
        "projectile_lead": humanized,
        "motor_profile": (
            formal.humanized_aim_motor_profile(seed, str(style))
            if humanized
            else None
        ),
        "random_aim_program": (
            None
            if humanized
            else v4.random_aim_program(
                seed, arm, weapon, set(fire_ticks)
            )
        ),
        "target_radius_model": (
            "camera_to_torso_elliptical_hull_plus_weapon_radius_v1"
        ),
        "reads_live_enemy_state": False,
        "reads_live_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
    }
    formal.validate_weapon_balanced_aim_program(program)
    return program


def screen_cell(ordinal: int) -> tuple[str, str, float, float]:
                                                                       
    horizontal_index = ordinal % 20
    if horizontal_index == 0:
        horizontal, yaw_offset = "center", 0.0
    elif horizontal_index % 2:
        horizontal, yaw_offset = "left", -24.0
    else:
        horizontal, yaw_offset = "right", 24.0
    vertical, pitch_offset = (
        ("upper", 8.0),
        ("center", 0.0),
        ("lower", -8.0),
    )[(ordinal // 20) % 3]
    return horizontal, vertical, yaw_offset, pitch_offset


def stationary_scenario(
    *,
    cohort: str,
    ordinal: int,
    weapon: str,
    outcome_recipe: str,
    arm: str,
    pair: dict[str, Any],
    appearance: dict[str, Any],
    formal_collection: bool,
    canary_authorization: dict[str, Any] | None,
) -> dict[str, Any]:
    template = copy.deepcopy(weapon_templates()[(weapon, arm)])
    for key in (
        "prefrozen_trace_source",
        "weapon_balanced_review_design",
        "formal_canary_design",
    ):
        template.pop(key, None)
    fire, fire_ticks = fire_program(weapon, outcome_recipe)
    aim = aim_program(
        weapon=weapon,
        arm=arm,
        ordinal=ordinal,
        fire_ticks=fire_ticks,
    )
    player_origin = [
        round(float(value), 6) for value in pair["player_origin"]
    ]
    enemy_origin = [
        round(float(value), 6) for value in pair["enemy_origin"]
    ]
    target_yaw, target_pitch = formal.yaw_pitch_toward(
        player_origin, enemy_origin
    )
    enemy_yaw, _ = formal.yaw_pitch_toward(
        enemy_origin, player_origin
    )
    horizontal, vertical, yaw_offset, pitch_offset = screen_cell(ordinal)
    episode_id = f"{cohort}_{ordinal:06d}"
    source_report_sha256 = preflight_report_sha256()
    template.update(
        {
            "schema_version": formal.SCENARIO_SCHEMA_V9,
            "action_program": formal.ACTION_PROGRAM_V9,
            "episode_id": episode_id,
            "counterfactual_group_id": f"{cohort}_g{ordinal:06d}",
            "anchor_id": f"{cohort}_g{ordinal:06d}_pair",
            "seed": 10_000_000 + ordinal + 1,
            "source_commit_required": source_commit(),
            "data_spec_sha256": data_spec_sha256(),
            "map": pair["map"],
            "gametype": pair["gametype"],
            "weapon": weapon,
            "weapon_netname": capture.WEAPON_NETNAME[weapon],
            "enemy_model": appearance["model"],
            "enemy_skin": int(appearance["skin"]),
            "enemy_color": COLORS[ordinal % len(COLORS)],
            "category": "stage2_formal_primary_interaction",
            "candidate_kind": (
                "stage2_formal_v1"
                if formal_collection
                else "stage2_formal_stationary_extension_canary_v1"
            ),
            "candidate_status": (
                "formal_collection_authorized_pending_live_fail_closed_qa"
                if formal_collection
                else "static_certified_pending_live_canary_qa"
            ),
            "training_stage": (
                "stage2" if formal_collection else "stage2_formal_canary_only"
            ),
            "formal_collection_authorized": formal_collection,
            "formal_authorization_basis": (
                canary_authorization if formal_collection else None
            ),
            "training_admitted": False,
            "human_review_required_before_training": True,
            "split": (
                "causal_interaction"
                if formal_collection
                else "stage2_weapon_balanced_nontraining_review"
            ),
            "canary_role": (
                f"stage2_formal_{weapon.lower()}_{outcome_recipe}_{arm}"
            ),
            "target_ordinal": ordinal,
            "expects_sound": outcome_recipe != "no_fire",
        }
    )
    template["player"] = {
        **template["player"],
        "origin": player_origin,
        "yaw": round(formal.wrap_angle(target_yaw + yaw_offset), 6),
        "pitch": round(target_pitch + pitch_offset, 6),
        "health": 200.0,
        "armor": 0.0,
    }
    template["enemy"] = {
        "origin": enemy_origin,
        "yaw": round(enemy_yaw, 6),
        "health": (
            KILL_HEALTH_BY_WEAPON[weapon]
            if outcome_recipe == "kill"
            else SURVIVE_HEALTH
        ),
        "armor": 0.0,
        "motion": 0,
        "motion_vector": tangent_vector(player_origin, enemy_origin),
                                                                           
                                                                    
                                                                            
                                
        "motion_distance": 0.0,
        "motion_start_tick": capture.WARMUP_TICKS,
    }
    template["enemy_policy"] = {
        "schema_version": "xonotic-stage2-enemy-policy-v2",
        "name": "stationary_open_loop_v1",
        "policy_seed": 11_000_000 + ordinal + 1,
        "motion_start_tick": capture.WARMUP_TICKS,
        "runtime_reads_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
        "fires": False,
        "jumps": False,
        "closed_loop_decisions": False,
        "policy_layer": "frozen_exogenous_stationary_formal_core",
        "bot_policy_scope": "zero_amplitude_stationary_formal",
        "movement_audio": "native_surface_footsteps_v1",
        "step_stride_units": 32,
    }
    template["encounter_source"] = {
        "schema_version": "xonotic-stage2-encounter-source-v1",
        "source_report": str(PREFLIGHT_REPORT),
        "source_report_sha256": source_report_sha256,
        "source_pair_episode_id": pair["episode_id"],
        "source_pair_distance_bin": pair["distance_bin"],
        "source_pair_passed": True,
        "current_trajectory_requires_recertification": False,
        "weapon_mechanism_mode_eligible": True,
    }
    template["stationary_preflight_source"] = {
        "schema_version": formal.STATIONARY_PREFLIGHT_SOURCE_SCHEMA,
        "source_report": str(PREFLIGHT_REPORT),
        "source_report_sha256": source_report_sha256,
        "source_pair_episode_id": pair["episode_id"],
        "source_pair_distance_bin": pair["distance_bin"],
        "source_pair_passed": True,
        "player_hull_clearance_passed": bool(
            pair["checks"]["player_clear"]
            and pair["checks"]["player_ground"]
        ),
        "enemy_hull_clearance_passed": bool(
            pair["checks"]["enemy_clear"]
            and pair["checks"]["enemy_ground"]
        ),
        "los_passed": bool(pair["checks"]["line_of_sight"]),
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
    }
    template["initial_screen_design"] = {
        "schema_version": formal.INITIAL_SCREEN_DESIGN_SCHEMA,
        "screen_horizontal": horizontal,
        "screen_vertical": vertical,
        "view_yaw_offset_deg": yaw_offset,
        "view_pitch_offset_deg": pitch_offset,
        "expected_visible_at_output_start": True,
    }
    template["causal_design"] = {
        "schema_version": formal.CAUSAL_DESIGN_SCHEMA_V9,
        "aim_policy": arm,
        "aim_reference": (
            "manifest_frozen_analytic_enemy_and_player_trajectories"
        ),
        "weapon_balanced_aim_program": aim,
        "fire_seed": 13_000_000 + ordinal + 1,
        "fire_program": fire,
        "fire_output_ticks": fire_ticks,
        "fire_width_ticks": 2,
        "interaction_channel": "primary",
        "secondary_mechanism": None,
        "base_player_program": "certified_stationary_preflight_pair",
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
    template["acceptance"] = {
        "actual_outcome": None,
        "actual_outcome_rebucket_required": True,
        "fire_required": outcome_recipe != "no_fire",
        "reload_success": False,
        "player_motion_qa_required": True,
        "player_self_damage_allowed": True,
        "player_death_allowed": False,
    }
    template["policy_labels"] = {
        **template["policy_labels"],
        "aim_policy": arm,
        "aim_family": aim["family"],
        "aim_family_bucket": aim_family_bucket(arm),
        "interaction_channel": "primary",
        "outcome_recipe": outcome_recipe,
        "outcome_assignment": (
            "post_capture_authoritative_target_damage_per_shot"
        ),
        "distribution_assignment": (
            "pre_capture_weapon_outcome_aim_geometry_recipe"
        ),
        "expected_distance_bin": pair["distance_bin"],
        "player_motion_class": "certified_stationary_preflight_pair",
        "target_motion_name": "stationary_zero_amplitude_policy",
    }
    template["formal_design"] = {
        "schema_version": FORMAL_DESIGN_SCHEMA,
        "cohort": cohort,
        "ordinal": ordinal,
        "outcome_recipe": outcome_recipe,
        "outcome_recipe_is_individual_admission_gate": False,
        "aim_family": aim["family"],
        "aim_family_bucket": aim_family_bucket(arm),
        "arm": arm,
        "distance_bin": pair["distance_bin"],
        "source_pair_episode_id": pair["episode_id"],
        "player_motion_class": "certified_stationary_preflight_pair",
        "enemy_motion_class": "stationary_zero_amplitude_policy",
        "enemy_health": float(template["enemy"]["health"]),
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
    }
    template["exogenous_contract_sha256"] = (
        formal.exogenous_contract_sha256(template)
    )
    formal.validate_initial_screen_design(
        template["initial_screen_design"]
    )
    formal.validate_scenario_contract(template)
    capture.validate_scenario_assets(template)
    return template


def moving_scenario(
    *,
    cohort: str,
    ordinal: int,
    weapon: str,
    outcome_recipe: str,
    arm: str,
    appearance: dict[str, Any],
    formal_collection: bool,
    canary_authorization: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create one formal row from the accepted V4 prefrozen trace pool."""
    source = weapon_templates()[(weapon, arm)]
    row = copy.deepcopy(source)
    row.pop("weapon_balanced_review_design", None)
    row.pop("formal_canary_design", None)
    episode_id = f"{cohort}_{ordinal:06d}"
    fire, fire_ticks = fire_program(weapon, outcome_recipe)
    aim = aim_program(
        weapon=weapon,
        arm=arm,
        ordinal=ordinal,
        fire_ticks=fire_ticks,
    )
    distance_bin = str(
        (row.get("encounter_source") or {}).get(
            "source_pair_distance_bin"
        )
    )
    row.update(
        {
            "episode_id": episode_id,
            "counterfactual_group_id": f"{cohort}_g{ordinal:06d}",
            "anchor_id": f"{cohort}_g{ordinal:06d}_moving",
            "source_commit_required": source_commit(),
            "data_spec_sha256": data_spec_sha256(),
            "enemy_model": appearance["model"],
            "enemy_skin": int(appearance["skin"]),
            "enemy_color": COLORS[ordinal % len(COLORS)],
            "category": "stage2_formal_primary_interaction",
            "candidate_kind": "stage2_formal_v1",
            "candidate_status": (
                "formal_collection_authorized_pending_live_fail_closed_qa"
            ),
            "training_stage": "stage2",
            "formal_collection_authorized": formal_collection,
            "formal_authorization_basis": (
                canary_authorization if formal_collection else None
            ),
            "training_admitted": False,
            "human_review_required_before_training": True,
            "split": (
                "causal_interaction"
                if formal_collection
                else "stage2_weapon_balanced_nontraining_review"
            ),
            "canary_role": (
                f"stage2_formal_{weapon.lower()}_{outcome_recipe}_{arm}"
            ),
            "target_ordinal": ordinal,
        }
    )
    row["enemy"]["health"] = (
        KILL_HEALTH_BY_WEAPON[weapon]
        if outcome_recipe == "kill"
        else SURVIVE_HEALTH
    )
    row["enemy_policy"]["policy_seed"] = 11_000_000 + ordinal + 1
    row["causal_design"].update(
        {
            "aim_policy": arm,
            "weapon_balanced_aim_program": aim,
            "fire_seed": 13_000_000 + ordinal + 1,
            "fire_program": fire,
            "fire_output_ticks": fire_ticks,
            "intended_outcome_is_acceptance_gate": False,
        }
    )
    row["acceptance"] = {
        "actual_outcome": None,
        "actual_outcome_rebucket_required": True,
        "fire_required": outcome_recipe != "no_fire",
        "reload_success": False,
        "player_motion_qa_required": True,
        "player_self_damage_allowed": True,
        "player_death_allowed": False,
    }
    row["policy_labels"] = {
        **row["policy_labels"],
        "aim_policy": arm,
        "aim_family": aim["family"],
        "aim_family_bucket": aim_family_bucket(arm),
        "outcome_recipe": outcome_recipe,
        "outcome_assignment": (
            "post_capture_authoritative_target_damage_per_shot"
        ),
        "distribution_assignment": (
            "pre_capture_weapon_outcome_aim_geometry_recipe"
        ),
        "expected_distance_bin": distance_bin,
        "player_motion_class": "certified_prefrozen_trace_replay",
    }
    row["formal_design"] = {
        "schema_version": FORMAL_DESIGN_SCHEMA,
        "cohort": cohort,
        "ordinal": ordinal,
        "outcome_recipe": outcome_recipe,
        "outcome_recipe_is_individual_admission_gate": False,
        "aim_family": aim["family"],
        "aim_family_bucket": aim_family_bucket(arm),
        "arm": arm,
        "distance_bin": distance_bin,
        "source_pair_episode_id": (
            row["encounter_source"]["source_pair_episode_id"]
        ),
        "source_episode_id": source["episode_id"],
        "player_motion_class": "certified_prefrozen_trace_replay",
        "enemy_health": float(row["enemy"]["health"]),
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
    }
    row["exogenous_contract_sha256"] = (
        formal.exogenous_contract_sha256(row)
    )
    formal.validate_initial_screen_design(row["initial_screen_design"])
    formal.validate_scenario_contract(row)
    capture.validate_scenario_assets(row)
    return row


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
