                      
"""Create the immutable hit-preserving Stage-2 motion replenishment v2."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_prefrozen_player_motion_replenishment_v1 as repl1              
import prepare_stage2_prefrozen_player_motion_review_v1 as parent              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_stochastic_review_v1/input.jsonl"
)
PARENT_FAILED_AUDIT = (
    ROOT
    / "stage2_prefrozen_player_motion_review_v1_output"
    / "SELECTION_AUDIT.json"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_prefrozen_player_motion_replenishment_v2"
)
SHARD_COUNT = 4
TARGET_WEAPONS = (
    "Blaster",
    "Shotgun",
    "Electro",
    "Devastator",
)
MOTION_PROFILES = ("lateral_weave", "approach_retreat")
MANIFEST_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-replenishment-manifest-v2"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-replenishment-design-v2"
)


def engagement_stabilized_movement_program(
    seed: int, profile: str
) -> dict[str, Any]:
    """Move near the spawn during engagement, then traverse more visibly.

    This remains a fully open-loop, manifest-frozen action sequence.  The
    low-amplitude first half is intentionally oscillatory so it has little
    net displacement while the inherited fire program is active.  Existing
    v1 candidates retain simultaneous larger movement/fire coverage.
    """
    if profile not in MOTION_PROFILES:
        raise ValueError(profile)
    rng = random.Random(seed + 2_718_281)
    early_major = rng.uniform(0.044, 0.047)
    early_minor = rng.uniform(0.044, 0.047)
    late_major = rng.uniform(0.122, 0.130)
    late_minor = rng.uniform(0.084, 0.092)
    ticks = [0, 40, 80, 120, 160, 200, 240, 280, 319]

    alternating = [
        0.0,
        early_major,
        -early_major,
        early_major,
        -early_major,
        late_major,
        -late_major,
        late_major,
        0.0,
    ]
    staggered = [
        0.0,
        early_minor,
        early_minor,
        -early_minor,
        -early_minor,
        -late_minor,
        -late_minor,
        late_minor,
        0.0,
    ]
    if profile == "lateral_weave":
        left_x = alternating
        left_y = staggered
    else:
        left_x = staggered
        left_y = [-value for value in alternating]
    left_x = [round(value, 6) for value in left_x]
    left_y = [round(value, 6) for value in left_y]
    program = {
        "schema_version": causal.PLAYER_MOVEMENT_PROGRAM_SCHEMA,
        "seed": seed,
        "algorithm": (
            "manifest_frozen_piecewise_smooth_player_movement_v1"
        ),
        "interpolation": "smoothstep",
        "profile": profile,
        "knot_output_ticks": ticks,
        "j_left_x": left_x,
        "j_left_y": left_y,
        "max_abs_axis_value": round(
            max(abs(value) for value in left_x + left_y), 6
        ),
        "jump_enabled": False,
        "reads_live_enemy_state": False,
        "reads_live_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
    }
    causal.validate_player_movement_program(program)
    return program


def materialize() -> list[dict[str, Any]]:
    if not PARENT_FAILED_AUDIT.is_file():
        raise capture.CaptureFailure(
            "parent_failed_selection_audit_missing",
            str(PARENT_FAILED_AUDIT),
        )
    parent_audit = json.loads(
        PARENT_FAILED_AUDIT.read_text(encoding="utf-8")
    )
    if parent_audit.get("passed") is not False:
        raise capture.CaptureFailure(
            "parent_selection_did_not_fail_closed",
            capture.canonical_json(
                {"passed": parent_audit.get("passed")}
            ),
        )
    if int(parent_audit.get("additional_candidate_cohorts", -1)) != 1:
        raise capture.CaptureFailure(
            "parent_selection_missing_replenishment_v1",
            capture.canonical_json(
                {
                    "additional_candidate_cohorts": parent_audit.get(
                        "additional_candidate_cohorts"
                    )
                }
            ),
        )
    repl1.write_once_or_verify(
        OUTPUT_ROOT / "PARENT_FAILED_SELECTION_AUDIT.json",
        json.dumps(parent_audit, indent=2, sort_keys=True) + "\n",
    )

    commit = repl1.source_commit()
    sources = repl1.source_groups()
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    rows: list[dict[str, Any]] = []
    for weapon_index, weapon in enumerate(TARGET_WEAPONS):
        for profile_index, profile in enumerate(MOTION_PROFILES):
            profile_tag = "lateral" if profile == "lateral_weave" else "approach"
            group_id = (
                f"s2pmr2_g{weapon_index + 1:02d}_"
                f"{capture.WEAPON_NETNAME[weapon]}_{profile_tag}"
            )
            movement_seed = (
                16_200_000 + weapon_index * 10 + profile_index + 1
            )
            movement = engagement_stabilized_movement_program(
                movement_seed, profile
            )
            for variant in parent.stochastic_v1.VARIANTS:
                row_ordinal = len(rows)
                row = copy.deepcopy(sources[weapon][variant])
                row.pop("stochastic_review_design", None)
                row.update(
                    {
                        "schema_version": causal.SCENARIO_SCHEMA_V8,
                        "action_program": causal.ACTION_PROGRAM_V8,
                        "episode_id": f"{group_id}_{variant}",
                        "counterfactual_group_id": group_id,
                        "anchor_id": f"{group_id}_pair",
                        "source_commit_required": commit,
                        "category": (
                            "stage2_prefrozen_player_motion_"
                            "engagement_stabilized_replenishment"
                        ),
                        "candidate_kind": (
                            "stage2_prefrozen_player_motion_"
                            "replenishment_v2"
                        ),
                        "candidate_status": (
                            "static_certified_pending_live_capture_and_"
                            "combined_group_selection"
                        ),
                        "training_stage": (
                            "stage2_prefrozen_player_motion_"
                            "replenishment_v2_only"
                        ),
                        "formal_collection_authorized": False,
                        "training_admitted": False,
                        "human_review_required_before_training": True,
                        "canary_role": (
                            f"stage2_prefrozen_motion_replenishment_v2_"
                            f"{weapon.lower()}_{profile}_{variant}"
                        ),
                        "data_spec_sha256": data_spec_sha256,
                        "shard_count": SHARD_COUNT,
                        "assigned_shard": row_ordinal % SHARD_COUNT,
                        "target_ordinal": row_ordinal,
                                                                   
                                                           
                        "split": (
                            "stage2_prefrozen_player_motion_"
                            "replenishment_nontraining_review_candidates"
                        ),
                    }
                )
                design = row["causal_design"]
                design.update(
                    {
                        "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V8,
                        "base_player_program": (
                            "manifest_frozen_continuous_movement"
                        ),
                        "player_movement_program": movement,
                        "player_health_policy": "player_alive",
                    }
                )
                row["acceptance"].update(
                    {
                        "actual_outcome": None,
                        "actual_outcome_rebucket_required": True,
                        "player_motion_qa_required": True,
                        "player_self_damage_allowed": True,
                        "player_death_allowed": False,
                    }
                )
                row["policy_labels"].update(
                    {
                        "player_motion_class": (
                            "prefrozen_continuous_movement"
                        ),
                        "player_motion_profile": profile,
                        "player_motion_candidate": "replenishment_v2",
                        "player_motion_amplitude_class": (
                            "engagement_stabilized_hit_preserving"
                        ),
                    }
                )
                row["exogenous_contract_sha256"] = (
                    causal.exogenous_contract_sha256(row)
                )
                certificate = parent.static_action_certificate(row)
                if not certificate["passed"]:
                    raise capture.CaptureFailure(
                        "stage2_motion_replenishment_v2_static_action_failed",
                        capture.canonical_json(
                            {
                                "episode_id": row["episode_id"],
                                "certificate": certificate,
                            }
                        ),
                    )
                row["prefrozen_player_motion_replenishment_design"] = {
                    "schema_version": DESIGN_SCHEMA,
                    "source_manifest": str(
                        SOURCE_MANIFEST.relative_to(ROOT)
                    ),
                    "source_episode_id": sources[weapon][variant][
                        "episode_id"
                    ],
                    "parent_failed_selection_audit": str(
                        (
                            OUTPUT_ROOT
                            / "PARENT_FAILED_SELECTION_AUDIT.json"
                        ).relative_to(ROOT)
                    ),
                    "replenishment_reason": (
                        "restore_devastator_eligibility_and_reach_"
                        "preregistered_90_percent_enemy_hit_target"
                    ),
                    "motion_profile": profile,
                    "motion_amplitude_class": (
                        "engagement_stabilized_hit_preserving"
                    ),
                    "movement_seed": movement_seed,
                    "player_health_policy": "player_alive",
                    "self_damage_counts_as_enemy_hit": False,
                    "enemy_hit_source": (
                        "authoritative_enemy_target_damage_parent_graph"
                    ),
                    "movement_fire_coordination": (
                        "prefrozen_low_net_displacement_during_"
                        "engagement_then_visible_traversal"
                    ),
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
        if len(members) != len(parent.stochastic_v1.VARIANTS):
            raise capture.CaptureFailure(
                "stage2_motion_replenishment_v2_group_shape",
                group_id,
            )
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_motion_replenishment_v2_group_exogenous_drift",
                group_id,
            )

    input_text = repl1.canonical_lines(rows)
    repl1.write_once_or_verify(OUTPUT_ROOT / "input.jsonl", input_text)
    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = repl1.canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        repl1.write_once_or_verify(shard_path, shard_text)
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
        "parent_failed_selection_audit": {
            "path": str(
                (
                    OUTPUT_ROOT
                    / "PARENT_FAILED_SELECTION_AUDIT.json"
                ).relative_to(ROOT)
            ),
            "sha256": capture.sha256_file(
                OUTPUT_ROOT / "PARENT_FAILED_SELECTION_AUDIT.json"
            ),
        },
        "source_commit": commit,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "counterfactual_groups": len(TARGET_WEAPONS)
        * len(MOTION_PROFILES),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "replenishment_policy": {
            "target_weapons": list(TARGET_WEAPONS),
            "profiles_per_weapon": list(MOTION_PROFILES),
            "group_selection_unit": "whole_three_arm_group",
            "player_health_policy": "player_alive",
            "self_damage_counts_as_enemy_hit": False,
            "enemy_hit_source": (
                "authoritative_enemy_target_damage_parent_graph"
            ),
            "runtime_fallback": False,
        },
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_prefrozen_player_motion_replenishment_v2.py",
            )
        },
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "motion_profile_distribution": dict(
            Counter(
                row[
                    "prefrozen_player_motion_replenishment_design"
                ]["motion_profile"]
                for row in rows
            )
        ),
    }
    repl1.write_once_or_verify(
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
                "source_commit": repl1.source_commit(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
