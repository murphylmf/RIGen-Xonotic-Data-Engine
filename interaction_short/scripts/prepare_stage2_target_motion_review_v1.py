                      
"""Build six complete policy groups from certified target trajectories."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_target_motion_certification_v1/input.jsonl"
)
CERTIFICATE_INDEX = (
    ROOT
    / "stage2_target_motion_certification_v1_output/"
    "review/TARGET_MOTION_CERTIFICATES.jsonl"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_target_motion_review_v1"
GROUP_PREFIX = "s2targetreviewv1"
CANDIDATE_KIND = "stage2_certified_target_motion_review_v1"
TRAINING_STAGE = "stage2_bounded_target_motion_review_v1_only"
MANIFEST_SCHEMA = "xonotic-stage2-target-motion-review-manifest-v1"
SELECTION_RULE = (
    "fixed_pre_capture_six_map_covering_selection_"
    "one_certificate_per_distance_motion_cell"
)
REPLACEMENT_CONTRACT: dict[str, Any] | None = None
DISTANCES = ("close", "near")
MOTIONS = (
    "lateral_patrol",
    "approach_retreat",
    "stop_and_go",
)
SELECTED_SOURCE_EPISODES = {
    ("close", "lateral_patrol"): (
        "s2targetcertv1_p01_m1_lateral_patrol"
    ),
    ("close", "approach_retreat"): (
        "s2targetcertv1_p02_m2_approach_retreat"
    ),
    ("close", "stop_and_go"): (
        "s2targetcertv1_p03_m3_stop_and_go"
    ),
    ("near", "lateral_patrol"): (
        "s2targetcertv1_p05_m1_lateral_patrol"
    ),
    ("near", "approach_retreat"): (
        "s2targetcertv1_p06_m2_approach_retreat"
    ),
    ("near", "stop_and_go"): (
        "s2targetcertv1_p04_m3_stop_and_go"
    ),
}
FIRE_TICKS = {
    "visible_no_response": [],
    "delayed_acquisition": [176, 256],
    "pass_offset": [176, 256],
    "track_loss_reacquire": [248, 296],
    "sustained_tracking": [88, 176, 264],
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


def selected_certificates() -> list[dict[str, Any]]:
    certificates = capture.load_jsonl(CERTIFICATE_INDEX)
    selected: list[dict[str, Any]] = []
    for distance in DISTANCES:
        for motion in MOTIONS:
            source_episode_id = SELECTED_SOURCE_EPISODES[
                (distance, motion)
            ]
            candidates = [
                row
                for row in certificates
                if row["distance"]["reset_bin"] == distance
                and row["target_motion"]["name"] == motion
                and row["source_episode_id"] == source_episode_id
                and row.get("passed") is True
            ]
            if len(candidates) != 1:
                raise capture.CaptureFailure(
                    "stage2_target_motion_review_cell_missing",
                    (
                        f"{distance}:{motion}:{source_episode_id}:"
                        f"{len(candidates)}"
                    ),
                )
            selected.append(candidates[0])
    return selected


def materialize() -> list[dict[str, Any]]:
    source_by_id = {
        row["episode_id"]: row
        for row in capture.load_jsonl(SOURCE_MANIFEST)
    }
    certificates = selected_certificates()
    index_sha256 = capture.sha256_file(CERTIFICATE_INDEX)
    rows: list[dict[str, Any]] = []
    for group_ordinal, certificate in enumerate(certificates, 1):
        source = source_by_id[certificate["source_episode_id"]]
        distance = certificate["distance"]["reset_bin"]
        motion = certificate["target_motion"]["name"]
        group_id = (
            f"{GROUP_PREFIX}_g{group_ordinal:02d}_"
            f"{distance}_{motion}"
        )
        certificate_reference = {
            "schema_version": (
                "xonotic-stage2-encounter-certificate-reference-v1"
            ),
            "index_path": str(
                CERTIFICATE_INDEX.relative_to(ROOT)
            ),
            "index_sha256": index_sha256,
            "certificate_id": certificate["certificate_id"],
            "record_sha256": hashlib.sha256(
                capture.canonical_json(certificate).encode("utf-8")
            ).hexdigest(),
        }
        for policy_ordinal, policy in enumerate(
            causal.AIM_POLICIES, 1
        ):
            row = copy.deepcopy(source)
            schedule = causal.default_aim_schedule(policy)
            row.update(
                {
                    "episode_id": (
                        f"{group_id}_p{policy_ordinal:02d}_{policy}"
                    ),
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "category": (
                        f"stage2_target_motion_review_{policy}"
                    ),
                    "candidate_kind": (
                        CANDIDATE_KIND
                    ),
                    "candidate_status": (
                        "certified_complete_policy_group_candidate"
                    ),
                    "training_stage": (
                        TRAINING_STAGE
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "encounter_certificate": certificate_reference,
                    "canary_role": (
                        f"stage2_target_motion_review_{motion}_{policy}"
                    ),
                    "expects_sound": True,
                }
            )
            row["encounter_source"].update(
                {
                    "current_trajectory_requires_recertification": (
                        False
                    ),
                    "target_motion_certificate_id": certificate[
                        "certificate_id"
                    ],
                }
            )
            design = row["causal_design"]
            design.update(
                {
                    "schema_version": (
                        causal.CAUSAL_DESIGN_SCHEMA_V3
                    ),
                    "aim_policy": policy,
                    "aim_schedule": schedule,
                    "acquisition_start_output_tick": int(
                        schedule.get("response_start_output_tick")
                        or 0
                    ),
                    "fire_output_ticks": list(FIRE_TICKS[policy]),
                    "interaction_channel": "primary",
                    "secondary_mechanism": None,
                    "base_player_program": "stationary",
                    "actual_outcome_source": (
                        "authoritative_telemetry_only"
                    ),
                    "intended_outcome_is_acceptance_gate": False,
                }
            )
            row["policy_labels"].update(
                {
                    "aim_policy": policy,
                    "interaction_channel": "primary",
                    "target_motion_name": motion,
                    "target_motion_certificate_id": certificate[
                        "certificate_id"
                    ],
                    "outcome_assignment": (
                        "post_capture_authoritative_telemetry_rebucket"
                    ),
                }
            )
            row["acceptance"]["actual_outcome"] = None
            row["acceptance"][
                "actual_outcome_rebucket_required"
            ] = True
            row["target_motion_review_design"] = {
                "schema_version": (
                    "xonotic-stage2-target-motion-review-design-v1"
                ),
                "selection_rule": (
                    SELECTION_RULE
                ),
                "selection_rule_declared_before_review_capture": True,
                "certificate_id": certificate["certificate_id"],
                "certificate_index_sha256": index_sha256,
                "distance_cell": distance,
                "motion_cell": motion,
                "whole_counterfactual_group_materialized": True,
                "runtime_geometry_fallback": False,
                "runtime_action_fallback": False,
                "actual_outcome_used_for_acceptance": False,
            }
            if REPLACEMENT_CONTRACT is not None:
                row["replacement_contract"] = {
                    **copy.deepcopy(REPLACEMENT_CONTRACT),
                    "source_episode_id": source["episode_id"],
                    "new_episode_id": row["episode_id"],
                    "new_group_id": group_id,
                    "new_seed": row["seed"],
                    "new_enemy_policy_seed": row["enemy_policy"][
                        "policy_seed"
                    ],
                }
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            causal.validate_scenario_contract(row)
            capture.validate_scenario_assets(row)
            actions = causal.causal_action_rows(row)
            if (
                policy == "visible_no_response"
                and any(action["primary"] for action in actions)
            ) or (
                policy != "visible_no_response"
                and not any(action["primary"] for action in actions)
            ):
                raise capture.CaptureFailure(
                    "stage2_target_motion_review_fire_contract",
                    row["episode_id"],
                )
            rows.append(row)

    for group_id in {
        row["counterfactual_group_id"] for row in rows
    }:
        members = [
            row
            for row in rows
            if row["counterfactual_group_id"] == group_id
        ]
        if (
            len(members) != len(causal.AIM_POLICIES)
            or {
                row["causal_design"]["aim_policy"]
                for row in members
            }
            != set(causal.AIM_POLICIES)
            or len(
                {
                    row["exogenous_contract_sha256"]
                    for row in members
                }
            )
            != 1
        ):
            raise capture.CaptureFailure(
                "stage2_target_motion_review_group_contract",
                group_id,
            )

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": MANIFEST_SCHEMA,
        "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "source_manifest_sha256": capture.sha256_file(
            SOURCE_MANIFEST
        ),
        "certificate_index": str(
            CERTIFICATE_INDEX.relative_to(ROOT)
        ),
        "certificate_index_sha256": index_sha256,
        "selection_rule": SELECTION_RULE,
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "actual_outcome_used_for_episode_acceptance": False,
        "actual_outcome_source": "authoritative_telemetry_only",
        "selected_certificates": [
            {
                "certificate_id": row["certificate_id"],
                "source_episode_id": row["source_episode_id"],
                "distance": row["distance"]["reset_bin"],
                "motion": row["target_motion"]["name"],
            }
            for row in certificates
        ],
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(certificates),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard_path.relative_to(ROOT)),
                    "rows": len(rows),
                    "sha256": hashlib.sha256(
                        text.encode("utf-8")
                    ).hexdigest(),
                }
            ],
        },
    }
    if REPLACEMENT_CONTRACT is not None:
        metadata["replacement_contract"] = (
            REPLACEMENT_CONTRACT
        )
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
                "rows": len(rows),
                "groups": len(
                    {
                        row["counterfactual_group_id"]
                        for row in rows
                    }
                ),
                "distance_motion_cells": sorted(
                    {
                        (
                            row["policy_labels"][
                                "expected_distance_bin"
                            ],
                            row["enemy_policy"]["name"],
                        )
                        for row in rows
                    }
                ),
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
