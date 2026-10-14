                      
"""Prepare the immutable, naturally weapon-balanced Stage-2 review v4.

V3 measures every aim arm once per weapon.  V4 turns that calibration design
into a distribution: every weapon receives ten firing slots and two no-fire
slots.  The number of precise target-conditioned slots is weapon-specific,
while every weapon still covers every aim arm.  Realized damage is audited
after capture and is never used to admit or replace an individual episode.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_weapon_balanced_review_v1 as v3_builder              
import prepare_stage2_stochastic_review_v1 as stochastic_v1              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_ROOT = ROOT / "manifests/stage2_weapon_balanced_review_v3"
SOURCE_MANIFEST = SOURCE_ROOT / "input.jsonl"
SOURCE_METADATA = SOURCE_ROOT / "MANIFEST_METADATA.json"
OUTPUT_ROOT = ROOT / "manifests/stage2_weapon_balanced_review_v4"
SHARD_COUNT = 4
MANIFEST_SCHEMA = "xonotic-stage2-weapon-balanced-review-manifest-v4"
DESIGN_SCHEMA = "xonotic-stage2-weapon-balanced-review-design-v4"
STATIC_CERTIFICATE_SCHEMA = (
    "xonotic-stage2-weapon-balanced-static-action-certificate-v4"
)
SELECTION_CONTRACT_SCHEMA = (
    "xonotic-stage2-weapon-balanced-selection-contract-v4"
)
WEAPONS = v3_builder.WEAPONS
TARGET_HIT_RATE_BANDS = v3_builder.TARGET_HIT_RATE_BANDS

                                                                        
                                                                            
                                                                           
                                                                            
                                                
LOW_RECIPE = (
    "stable_track",
    "overshoot_correct",
    "predictive_track",
    "edge_graze",
    "edge_graze",
    "near_miss",
    "near_miss",
    "stochastic_local",
    "stochastic_broad",
    "stochastic_broad",
)
MID_RECIPE = (
    "stable_track",
    "stable_track",
    "overshoot_correct",
    "predictive_track",
    "edge_graze",
    "edge_graze",
    "near_miss",
    "stochastic_local",
    "stochastic_broad",
    "stochastic_broad",
)
HIGH_RECIPE = (
    "stable_track",
    "stable_track",
    "overshoot_correct",
    "overshoot_correct",
    "predictive_track",
    "edge_graze",
    "near_miss",
    "stochastic_local",
    "stochastic_broad",
    "stochastic_broad",
)
FIRING_RECIPE_BY_WEAPON = {
                                                                              
                                                                          
                                                                             
                                                                          
    "Blaster": LOW_RECIPE,
    "Shotgun": MID_RECIPE,
    "MachineGun": LOW_RECIPE,
    "Mortar": LOW_RECIPE,
    "Electro": LOW_RECIPE,
    "Crylink": LOW_RECIPE,
    "Vortex": LOW_RECIPE,
    "Hagar": LOW_RECIPE,
    "Devastator": LOW_RECIPE,
}

                                                                         
                                                                            
                                                                            
MISS_SCALE_BY_WEAPON = {
    "Blaster": {"edge_graze": 0.82, "near_miss": 1.28},
    "Shotgun": {"edge_graze": 2.00, "near_miss": 2.50},
    "MachineGun": {"edge_graze": 2.00, "near_miss": 2.50},
    "Mortar": {"edge_graze": 1.25, "near_miss": 1.60},
    "Electro": {"edge_graze": 1.05, "near_miss": 1.55},
    "Crylink": {"edge_graze": 1.35, "near_miss": 1.75},
    "Vortex": {"edge_graze": 2.00, "near_miss": 2.50},
    "Hagar": {"edge_graze": 1.15, "near_miss": 1.60},
    "Devastator": {"edge_graze": 1.25, "near_miss": 1.65},
}

ARM_PARAMETERS = {
    "stable_track": ("humanized_target_conditioned", "direct_smooth", 24, 88),
    "overshoot_correct": (
        "humanized_target_conditioned",
        "overshoot_correct",
        20,
        100,
    ),
    "predictive_track": (
        "humanized_target_conditioned",
        "direct_smooth",
        28,
        88,
    ),
    "edge_graze": ("humanized_target_conditioned", "direct_smooth", 24, 92),
    "near_miss": ("humanized_target_conditioned", "direct_smooth", 24, 92),
    "stochastic_local": ("stochastic_free_aim", None, 24, 88),
    "stochastic_broad": ("stochastic_free_aim", None, 24, 88),
    "visible_no_fire": ("visible_no_fire", None, 24, 88),
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
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = text.encode("utf-8")
    if path.exists():
        if path.read_bytes() != payload:
            raise capture.CaptureFailure(
                "refuse_overwrite_weapon_balanced_v4_manifest_drift",
                str(path),
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def template_by_weapon() -> dict[str, dict[str, Any]]:
    rows = capture.load_jsonl(SOURCE_MANIFEST)
    result: dict[str, dict[str, Any]] = {}
    for weapon in WEAPONS:
        matches = [
            row
            for row in rows
            if row["weapon"] == weapon
            and row["causal_design"]["aim_policy"] == "stable_track"
        ]
        if len(matches) != 1:
            raise capture.CaptureFailure(
                "stage2_weapon_balanced_v4_source_shape",
                capture.canonical_json(
                    {"weapon": weapon, "matches": len(matches)}
                ),
            )
        result[weapon] = matches[0]
    return result


def stochastic_bounds(weapon: str, arm: str) -> tuple[float, float]:
    if arm == "stochastic_broad":
        return 50.0, 20.0
    if arm == "stochastic_local":
        if weapon == "Shotgun":
            return 40.0, 16.0
        if weapon == "Crylink":
            return 30.0, 14.0
        return 20.0, 10.0
    return 15.0, 8.0


def random_aim_program(
    seed: int,
    arm: str,
    weapon: str,
    fire_ticks: set[int],
) -> dict[str, Any]:
    ticks = (
        [0, 40, 72, 96, 136, 176, 200, 240, 280, 319]
        if weapon == "Vortex"
        else [0, 40, 80, 104, 144, 184, 224, 264, 319]
    )
    max_yaw, max_pitch = stochastic_bounds(weapon, arm)
    for candidate in range(4096):
        rng = random.Random(seed + candidate * 1_000_003)
        yaw = [0.0] + [
            round(rng.uniform(-max_yaw, max_yaw), 6)
            for _ in ticks[1:]
        ]
        pitch = [
            (
                0.0
                if index == 0 or tick in fire_ticks
                else round(rng.uniform(-max_pitch, max_pitch), 6)
            )
            for index, tick in enumerate(ticks)
        ]
        fire_yaw = [
            yaw[index] for index, tick in enumerate(ticks) if tick in fire_ticks
        ]
        checks = {
            "yaw_span": max(yaw) - min(yaw) >= 12.0,
            "pitch_span": max(pitch) - min(pitch) >= 5.0,
            "yaw_two_sided": min(yaw) < -3.0 and max(yaw) > 3.0,
            "pitch_two_sided": min(pitch) < -1.5 and max(pitch) > 1.5,
                                                                              
            "fire_yaw_varies": (
                len(fire_yaw) < 2
                or abs(fire_yaw[0] - fire_yaw[1]) >= 4.0
            ),
        }
        if not all(checks.values()):
            continue
        program = {
            "schema_version": causal.RANDOM_AIM_PROGRAM_SCHEMA,
            "seed": seed,
            "algorithm": "manifest_frozen_piecewise_smooth_view_v1",
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
        "stage2_weapon_balanced_v4_random_aim_exhausted",
        f"seed={seed} arm={arm} weapon={weapon}",
    )


def aim_program(
    weapon: str,
    weapon_index: int,
    slot_index: int,
    arm: str,
    replica: int,
    fire_ticks: list[int],
) -> dict[str, Any]:
    family, style, response, settle = ARM_PARAMETERS[arm]
    seed = 15_500_000 + weapon_index * 1000 + slot_index + 1
    humanized = arm in causal.WEAPON_BALANCED_HUMANIZED_ARMS
    miss = arm in {"edge_graze", "near_miss"}
    scale = MISS_SCALE_BY_WEAPON[weapon].get(arm, 0.0)
    direction = (
        (0.0 if (weapon_index + replica) % 2 == 0 else 180.0)
        if miss
        else round(
            random.Random(seed + 20_260_730).uniform(-180.0, 180.0),
            6,
        )
    )
    program = {
        "schema_version": causal.WEAPON_BALANCED_AIM_PROGRAM_SCHEMA,
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
            causal.humanized_aim_motor_profile(seed, str(style))
            if humanized
            else None
        ),
        "random_aim_program": (
            None
            if humanized
            else random_aim_program(seed, arm, weapon, set(fire_ticks))
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
    starts = [96, 200] if weapon == "Vortex" else [104, 184]
    return {
        "schema_version": causal.FIRE_PROGRAM_SCHEMA,
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
    }


def selection_contract() -> dict[str, Any]:
    return {
        "schema_version": SELECTION_CONTRACT_SCHEMA,
        "distribution_unit": "pre_capture_weapon_aim_slot",
        "episodes_per_weapon": 12,
        "firing_episodes_per_weapon": 10,
        "no_fire_episodes_per_weapon": 2,
        "fire_events_per_firing_episode": 2,
        "humanized_firing_fraction": 0.70,
        "stochastic_firing_fraction": 0.30,
        "all_aim_arms_present_per_weapon": True,
        "target_hit_rate_bands": {
            weapon: {"minimum": bounds[0], "maximum": bounds[1]}
            for weapon, bounds in TARGET_HIT_RATE_BANDS.items()
        },
        "realized_outcome_is_not_episode_admission": True,
        "operational_replacement_requires_new_episode_id": True,
        "operational_replacement_preserves_weapon_and_slot": True,
        "rate_correction_policy": (
            "change_future_manifest_arm_weights_or_frozen_parameters_at_"
            "weapon_stratum_only_never_select_individual_realized_outcomes"
        ),
        "target_outcome_definition": (
            "authoritative_damage_to_declared_enemy_resolved_to_fire_root"
        ),
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
    }


def materialize() -> list[dict[str, Any]]:
    commit = source_commit()
    source_metadata = json.loads(
        SOURCE_METADATA.read_text(encoding="utf-8")
    )
    if source_metadata.get("source_commit") != commit:
        raise capture.CaptureFailure(
            "stage2_weapon_balanced_v4_source_commit",
            capture.canonical_json(
                {
                    "expected": commit,
                    "actual": source_metadata.get("source_commit"),
                }
            ),
        )
    templates = template_by_weapon()
    contract = selection_contract()
    contract_hash = hashlib.sha256(
        capture.canonical_json(contract).encode("utf-8")
    ).hexdigest()
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    rows: list[dict[str, Any]] = []
    for weapon_index, weapon in enumerate(WEAPONS):
        group_id = (
            f"s2wbv4_g{weapon_index + 1:02d}_"
            f"{capture.WEAPON_NETNAME[weapon]}"
        )
        arms = (*FIRING_RECIPE_BY_WEAPON[weapon], "visible_no_fire", "visible_no_fire")
        replicas: Counter[str] = Counter()
        for slot_index, arm in enumerate(arms):
            replica = replicas[arm]
            replicas[arm] += 1
            no_fire = arm == "visible_no_fire"
            fire = fire_program(weapon, no_fire)
            fire_ticks = [
                int(window["start_output_tick"])
                for window in fire["windows"]
            ]
            aim = aim_program(
                weapon,
                weapon_index,
                slot_index,
                arm,
                replica,
                fire_ticks,
            )
            row_ordinal = len(rows)
            row = copy.deepcopy(templates[weapon])
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V9,
                    "action_program": causal.ACTION_PROGRAM_V9,
                    "episode_id": (
                        f"{group_id}_{arm}_r{replica + 1:02d}"
                    ),
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_twelve_slot",
                    "source_commit_required": commit,
                    "category": (
                        "stage2_naturally_weapon_balanced_primary_interaction"
                    ),
                    "candidate_kind": "stage2_weapon_balanced_review_v4",
                    "candidate_status": (
                        "static_certified_pending_live_capture_and_"
                        "aggregate_weapon_rate_audit"
                    ),
                    "training_stage": (
                        "stage2_weapon_balanced_review_v4_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "human_review_required_before_training": True,
                    "canary_role": (
                        f"stage2_weapon_balanced_v4_{weapon.lower()}_"
                        f"{arm}_r{replica + 1:02d}"
                    ),
                    "data_spec_sha256": data_spec_sha256,
                    "shard_count": SHARD_COUNT,
                    "assigned_shard": row_ordinal % SHARD_COUNT,
                    "target_ordinal": row_ordinal,
                    "split": (
                        "stage2_weapon_balanced_nontraining_review"
                    ),
                }
            )
            row["causal_design"] = {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V9,
                "aim_policy": arm,
                "aim_reference": (
                    "manifest_frozen_analytic_enemy_and_player_trajectories"
                ),
                "weapon_balanced_aim_program": aim,
                "fire_seed": (
                    15_700_000
                    + weapon_index * 1000
                    + slot_index
                    + 1
                ),
                "fire_program": fire,
                "fire_output_ticks": fire_ticks,
                "fire_width_ticks": 2,
                "interaction_channel": "primary",
                "secondary_mechanism": None,
                "base_player_program": "certified_prefrozen_trace_replay",
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
                **row["policy_labels"],
                "aim_policy": arm,
                "aim_family": aim["family"],
                "interaction_channel": "primary",
                "outcome_assignment": (
                    "post_capture_authoritative_target_damage_per_shot"
                ),
                "distribution_assignment": (
                    "pre_capture_weapon_conditioned_arm_recipe"
                ),
            }
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            certificate = v3_builder.static_action_certificate(row)
            certificate["schema_version"] = STATIC_CERTIFICATE_SCHEMA
            if not certificate["passed"]:
                raise capture.CaptureFailure(
                    "stage2_weapon_balanced_v4_static_action_failed",
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
                "source_metadata": str(
                    SOURCE_METADATA.relative_to(ROOT)
                ),
                "source_episode_id": templates[weapon]["episode_id"],
                "slot_index": slot_index,
                "arm": arm,
                "arm_replica": replica + 1,
                "aim_seed": aim["seed"],
                "fire_seed": row["causal_design"]["fire_seed"],
                "enemy_policy_seed": row["enemy_policy"]["policy_seed"],
                "selection_contract_sha256": contract_hash,
                "target_hit_rate_band": {
                    "minimum": TARGET_HIT_RATE_BANDS[weapon][0],
                    "maximum": TARGET_HIT_RATE_BANDS[weapon][1],
                },
                "static_action_certificate": certificate,
                "outcome_used_for_individual_admission": False,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
                "runtime_outcome_fallback": False,
                "formal_collection_authorized": False,
            }
            causal.validate_scenario_contract(row)
            rows.append(row)

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
        "source_metadata": {
            "path": str(SOURCE_METADATA.relative_to(ROOT)),
            "sha256": capture.sha256_file(SOURCE_METADATA),
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
        "arm_distribution_by_weapon": {
            weapon: dict(
                Counter(
                    row["causal_design"]["aim_policy"]
                    for row in rows
                    if row["weapon"] == weapon
                )
            )
            for weapon in WEAPONS
        },
        "firing_episodes_per_weapon": 10,
        "humanized_firing_episodes_per_weapon": 7,
        "stochastic_firing_episodes_per_weapon": 3,
        "no_fire_episodes_per_weapon": 2,
        "requested_fire_events_per_firing_episode": 2,
        "miss_scale_by_weapon": MISS_SCALE_BY_WEAPON,
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_weapon_balanced_review_v4.py",
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
