                      
"""Create immutable safe-geometry Devastator motion candidates."""

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

import prepare_stage2_prefrozen_player_motion_replenishment_v1 as repl1              
import prepare_stage2_prefrozen_player_motion_review_v1 as parent              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_stochastic_review_v1/input.jsonl"
)
MOVEMENT_SOURCE_MANIFEST = (
    ROOT
    / "manifests/stage2_prefrozen_player_motion_replenishment_v1"
    / "input.jsonl"
)
PARENT_FAILED_AUDIT = (
    ROOT
    / "stage2_prefrozen_player_motion_review_v1_output"
    / "SELECTION_AUDIT.json"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_prefrozen_player_motion_replenishment_v3"
)
SHARD_COUNT = 4
GEOMETRY_SOURCES = (
    ("Hagar", "bromine_approach"),
    ("Crylink", "catharsis_approach"),
    ("Vortex", "geoplanetary_lateral"),
)
GEOMETRY_FIELDS = (
    "map",
    "gametype",
    "player",
    "enemy",
    "enemy_policy",
    "encounter_source",
    "initial_screen_design",
    "target_motion_certification_design",
)
MANIFEST_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-replenishment-manifest-v3"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-replenishment-design-v3"
)


def rows_by_weapon(
    manifest: Path,
) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for row in capture.load_jsonl(manifest):
        result.setdefault(str(row["weapon"]), {})[
            str(row["policy_labels"]["random_aim_variant"])
        ] = row
    return result


def materialize() -> list[dict[str, Any]]:
    if not PARENT_FAILED_AUDIT.is_file():
        raise capture.CaptureFailure(
            "parent_failed_selection_audit_missing",
            str(PARENT_FAILED_AUDIT),
        )
    parent_audit = json.loads(
        PARENT_FAILED_AUDIT.read_text(encoding="utf-8")
    )
    if (
        parent_audit.get("passed") is not False
        or int(parent_audit.get("additional_candidate_cohorts", -1))
        != 2
    ):
        raise capture.CaptureFailure(
            "parent_selection_missing_replenishment_v2_failure",
            capture.canonical_json(
                {
                    "passed": parent_audit.get("passed"),
                    "additional_candidate_cohorts": parent_audit.get(
                        "additional_candidate_cohorts"
                    ),
                }
            ),
        )
    eligible_weapons = {
        str(group["weapon"])
        for group in parent_audit.get("groups", [])
        if group.get("eligible") is True
    }
    if set(parent.stochastic_v1.human_v2.WEAPONS) - eligible_weapons != {
        "Devastator"
    }:
        raise capture.CaptureFailure(
            "parent_selection_not_devastator_only_gap",
            capture.canonical_json(
                {
                    "eligible_weapons": sorted(eligible_weapons),
                }
            ),
        )
    repl1.write_once_or_verify(
        OUTPUT_ROOT / "PARENT_FAILED_SELECTION_AUDIT.json",
        json.dumps(parent_audit, indent=2, sort_keys=True) + "\n",
    )

    commit = repl1.source_commit()
    sources = rows_by_weapon(SOURCE_MANIFEST)
    movement_sources = rows_by_weapon(MOVEMENT_SOURCE_MANIFEST)
    dev_sources = sources["Devastator"]
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    rows: list[dict[str, Any]] = []
    for geometry_index, (
        geometry_weapon,
        geometry_tag,
    ) in enumerate(GEOMETRY_SOURCES):
        geometry = sources[geometry_weapon][
            parent.stochastic_v1.VARIANTS[0]
        ]
        movement_source = movement_sources[geometry_weapon][
            parent.stochastic_v1.VARIANTS[0]
        ]
        movement = copy.deepcopy(
            movement_source["causal_design"][
                "player_movement_program"
            ]
        )
        profile = str(movement["profile"])
        group_id = (
            f"s2pmr3_g{geometry_index + 1:02d}_"
            f"devastator_{geometry_tag}"
        )
        for variant in parent.stochastic_v1.VARIANTS:
            row_ordinal = len(rows)
            row = copy.deepcopy(dev_sources[variant])
            row.pop("stochastic_review_design", None)
            for field in GEOMETRY_FIELDS:
                row[field] = copy.deepcopy(geometry[field])
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V8,
                    "action_program": causal.ACTION_PROGRAM_V8,
                    "episode_id": f"{group_id}_{variant}",
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "seed": 14_810_001 + geometry_index,
                    "source_commit_required": commit,
                    "category": (
                        "stage2_prefrozen_player_motion_devastator_"
                        "safe_geometry_replenishment"
                    ),
                    "candidate_kind": (
                        "stage2_prefrozen_player_motion_"
                        "replenishment_v3"
                    ),
                    "candidate_status": (
                        "static_certified_pending_live_capture_and_"
                        "combined_group_selection"
                    ),
                    "training_stage": (
                        "stage2_prefrozen_player_motion_"
                        "replenishment_v3_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "human_review_required_before_training": True,
                    "canary_role": (
                        "stage2_prefrozen_motion_replenishment_v3_"
                        f"devastator_{geometry_tag}_{variant}"
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
                    "initial_screen_cell": geometry[
                        "policy_labels"
                    ]["initial_screen_cell"],
                    "player_motion_class": (
                        "prefrozen_continuous_movement"
                    ),
                    "player_motion_profile": profile,
                    "player_motion_candidate": "replenishment_v3",
                    "player_motion_amplitude_class": (
                        "prevalidated_safe_geometry_mild"
                    ),
                }
            )
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            certificate = parent.static_action_certificate(row)
            if not certificate["passed"]:
                raise capture.CaptureFailure(
                    "stage2_motion_replenishment_v3_static_action_failed",
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
                "source_episode_id": dev_sources[variant][
                    "episode_id"
                ],
                "geometry_source_episode_id": geometry["episode_id"],
                "movement_source_episode_id": movement_source[
                    "episode_id"
                ],
                "parent_failed_selection_audit": str(
                    (
                        OUTPUT_ROOT
                        / "PARENT_FAILED_SELECTION_AUDIT.json"
                    ).relative_to(ROOT)
                ),
                "replenishment_reason": (
                    "restore_devastator_whole_group_with_"
                    "preregistered_safe_encounter_geometry"
                ),
                "geometry_tag": geometry_tag,
                "motion_profile": profile,
                "motion_amplitude_class": (
                    "prevalidated_safe_geometry_mild"
                ),
                "movement_seed": int(movement["seed"]),
                "player_health_policy": "player_alive",
                "self_damage_counts_as_enemy_hit": False,
                "enemy_hit_source": (
                    "authoritative_enemy_target_damage_parent_graph"
                ),
                "geometry_selected_before_live_capture": True,
                "source_geometry_used_as_runtime_fallback": False,
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
                "stage2_motion_replenishment_v3_group_shape",
                group_id,
            )
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_motion_replenishment_v3_group_exogenous_drift",
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
        "movement_source_manifest": {
            "path": str(MOVEMENT_SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(
                MOVEMENT_SOURCE_MANIFEST
            ),
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
        "counterfactual_groups": len(GEOMETRY_SOURCES),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "replenishment_policy": {
            "target_weapon": "Devastator",
            "geometry_sources": [
                tag for _, tag in GEOMETRY_SOURCES
            ],
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
                "scripts/prepare_stage2_prefrozen_player_motion_replenishment_v3.py",
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
        "map_distribution": dict(
            Counter(row["map"] for row in rows)
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
