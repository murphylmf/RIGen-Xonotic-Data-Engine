                      
"""Prepare an immutable Vortex-only Stage-2 calibration review V5.

V4's complete Vortex stratum was above its aggregate target-hit band.  V5
changes the future Vortex stratum recipe as a whole.  It neither reads nor
selects any individual V4 episode outcome.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_weapon_balanced_review_v4 as v4              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_AUDIT = (
    ROOT
    / "stage2_weapon_balanced_review_v4_output"
    / "WEAPON_BALANCED_AUDIT.json"
)
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_vortex_calibration_review_v5"
)
SHARD_COUNT = 4
WEAPON = "Vortex"
MANIFEST_SCHEMA = (
    "xonotic-stage2-vortex-calibration-review-manifest-v5"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-vortex-calibration-review-design-v5"
)
STATIC_CERTIFICATE_SCHEMA = (
    "xonotic-stage2-vortex-calibration-static-action-certificate-v5"
)

                                                                           
                                                                      
                                                                          
FIRING_RECIPE = (
    "stable_track",
    "overshoot_correct",
    "predictive_track",
    "edge_graze",
    "near_miss",
    "near_miss",
    "near_miss",
    "near_miss",
    "stochastic_local",
    "stochastic_broad",
)
ALL_ARMS = (*FIRING_RECIPE, "visible_no_fire", "visible_no_fire")


def aim_program(
    slot_index: int,
    arm: str,
    replica: int,
    fire_ticks: list[int],
) -> dict[str, Any]:
    family, style, response, settle = v4.ARM_PARAMETERS[arm]
    seed = 16_100_000 + slot_index + 1
    humanized = arm in causal.WEAPON_BALANCED_HUMANIZED_ARMS
    miss = arm in {"edge_graze", "near_miss"}
    scale = v4.MISS_SCALE_BY_WEAPON[WEAPON].get(arm, 0.0)
    direction = (
        (0.0 if replica % 2 == 0 else 180.0)
        if miss
        else float(
            ((seed * 104729) % 360_000_000) / 1_000_000
            - 180.0
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
        "offset_direction_deg": round(direction, 6),
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
            else v4.random_aim_program(
                seed, arm, WEAPON, set(fire_ticks)
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
    causal.validate_weapon_balanced_aim_program(program)
    return program


def aggregate_calibration_evidence() -> dict[str, Any]:
    audit = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    vortex = audit["weapon_summary"][WEAPON]
    evidence = {
        "source_audit": str(SOURCE_AUDIT.relative_to(ROOT)),
        "source_audit_sha256": capture.sha256_file(SOURCE_AUDIT),
        "source_schema_version": audit["schema_version"],
        "weapon": WEAPON,
        "episodes": int(vortex["episodes"]),
        "fire_events": int(vortex["fire_events"]),
        "target_hit_fire_events": int(
            vortex["target_hit_fire_events"]
        ),
        "target_hit_rate": float(vortex["target_hit_rate"]),
        "target_band_minimum": float(
            vortex["target_band_minimum"]
        ),
        "target_band_maximum": float(
            vortex["target_band_maximum"]
        ),
        "approximate_band_passed": bool(
            vortex["approximate_band_passed"]
        ),
        "individual_episode_results_read": False,
    }
    if (
        evidence["episodes"] != 12
        or evidence["fire_events"] != 20
        or evidence["approximate_band_passed"] is not False
    ):
        raise capture.CaptureFailure(
            "stage2_vortex_v5_aggregate_evidence_invalid",
            capture.canonical_json(evidence),
        )
    return evidence


def materialize() -> list[dict[str, Any]]:
    evidence = aggregate_calibration_evidence()
    commit = v4.source_commit()
    template = v4.template_by_weapon()[WEAPON]
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    lower, upper = v4.TARGET_HIT_RATE_BANDS[WEAPON]
    contract = {
        "schema_version": (
            "xonotic-stage2-vortex-calibration-selection-contract-v5"
        ),
        "distribution_unit": "pre_capture_whole_weapon_stratum",
        "weapon": WEAPON,
        "episodes": 12,
        "firing_episodes": 10,
        "no_fire_episodes": 2,
        "fire_events_per_firing_episode": 2,
        "all_aim_arms_present": True,
        "firing_recipe": list(FIRING_RECIPE),
        "target_hit_rate_band": {
            "minimum": lower,
            "maximum": upper,
            "allowed_sampling_deviation": 0.05,
        },
        "source_aggregate_only": True,
        "individual_v4_outcome_used_for_admission": False,
        "v5_outcome_used_for_admission": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
    }
    contract_hash = hashlib.sha256(
        capture.canonical_json(contract).encode("utf-8")
    ).hexdigest()
    group_id = "s2v5_g07_vortex"
    rows: list[dict[str, Any]] = []
    replicas: Counter[str] = Counter()
    for slot_index, arm in enumerate(ALL_ARMS):
        replica = replicas[arm]
        replicas[arm] += 1
        no_fire = arm == "visible_no_fire"
        fire = v4.fire_program(WEAPON, no_fire)
        fire_ticks = [
            int(window["start_output_tick"])
            for window in fire["windows"]
        ]
        aim = aim_program(
            slot_index, arm, replica, fire_ticks
        )
        row = copy.deepcopy(template)
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
                    "stage2_vortex_whole_stratum_rate_calibration"
                ),
                "candidate_kind": (
                    "stage2_vortex_calibration_review_v5"
                ),
                "candidate_status": (
                    "static_certified_pending_live_capture_and_"
                    "aggregate_weapon_rate_audit"
                ),
                "training_stage": (
                    "stage2_vortex_calibration_review_v5_only"
                ),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "human_review_required_before_training": True,
                "canary_role": (
                    f"stage2_vortex_calibration_v5_{arm}_"
                    f"r{replica + 1:02d}"
                ),
                "data_spec_sha256": data_spec_sha256,
                "shard_count": SHARD_COUNT,
                "assigned_shard": slot_index % SHARD_COUNT,
                "target_ordinal": 30_000 + slot_index,
                "split": (
                    "stage2_vortex_calibration_nontraining_review"
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
            "fire_seed": 16_200_000 + slot_index + 1,
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
                "pre_capture_whole_vortex_stratum_v5_recipe"
            ),
        }
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        certificate = v4.v3_builder.static_action_certificate(row)
        certificate["schema_version"] = STATIC_CERTIFICATE_SCHEMA
        if not certificate["passed"]:
            raise capture.CaptureFailure(
                "stage2_vortex_v5_static_action_failed",
                row["episode_id"],
            )
        row["weapon_balanced_review_design"] = {
            "schema_version": DESIGN_SCHEMA,
            "source_manifest": str(
                v4.OUTPUT_ROOT.joinpath(
                    "input.jsonl"
                ).relative_to(ROOT)
            ),
            "source_audit": evidence["source_audit"],
            "source_audit_sha256": evidence[
                "source_audit_sha256"
            ],
            "source_aggregate_weapon": WEAPON,
            "source_aggregate_hit_rate": evidence[
                "target_hit_rate"
            ],
            "individual_source_episode_outcomes_read": False,
            "slot_index": slot_index,
            "arm": arm,
            "arm_replica": replica + 1,
            "aim_seed": aim["seed"],
            "fire_seed": row["causal_design"]["fire_seed"],
            "enemy_policy_seed": row["enemy_policy"]["policy_seed"],
            "selection_contract_sha256": contract_hash,
            "target_hit_rate_band": {
                "minimum": lower,
                "maximum": upper,
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

    input_text = v4.canonical_lines(rows)
    v4.write_once_or_verify(
        OUTPUT_ROOT / "input.jsonl", input_text
    )
    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = v4.canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        v4.write_once_or_verify(shard_path, shard_text)
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
        "source_commit": commit,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "aggregate_calibration_evidence": evidence,
        "selection_contract": contract,
        "selection_contract_sha256": contract_hash,
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": {WEAPON: len(rows)},
        "arm_distribution": dict(
            Counter(
                row["causal_design"]["aim_policy"]
                for row in rows
            )
        ),
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_weapon_balanced_review_v4.py",
                "scripts/prepare_stage2_vortex_calibration_review_v5.py",
            )
        },
    }
    v4.write_once_or_verify(
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
                "weapon": WEAPON,
                "recipe": list(FIRING_RECIPE),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
