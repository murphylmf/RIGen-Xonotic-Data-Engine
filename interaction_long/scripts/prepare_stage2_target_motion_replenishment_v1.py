                      
"""Build a fresh complete group for the incomplete close-approach review."""

from __future__ import annotations

import json

import prepare_stage2_target_motion_review_v1 as base


SOURCE_MANIFEST = (
    base.ROOT / "manifests/stage2_target_motion_review_v1/input.jsonl"
)
SOURCE_REJECTS = (
    base.ROOT
    / "stage2_target_motion_review_v1_output/manifests/shards/"
    "shard-000-of-001/rejects.jsonl"
)
base.OUTPUT_ROOT = (
    base.ROOT / "manifests/stage2_target_motion_replenishment_v1"
)
base.GROUP_PREFIX = "s2targetrepl1"
base.CANDIDATE_KIND = (
    "stage2_certified_target_motion_replenishment_v1"
)
base.TRAINING_STAGE = (
    "stage2_bounded_target_motion_replenishment_v1_only"
)
base.MANIFEST_SCHEMA = (
    "xonotic-stage2-target-motion-replenishment-manifest-v1"
)
base.SELECTION_RULE = (
    "fixed_alternative_certified_close_approach_geometry_"
    "after_terminal_policy_semantics_rejection"
)
base.DISTANCES = ("close",)
base.MOTIONS = ("approach_retreat",)
base.SELECTED_SOURCE_EPISODES = {
    ("close", "approach_retreat"): (
        "s2targetcertv1_p03_m2_approach_retreat"
    )
}
base.REPLACEMENT_CONTRACT = {
    "schema_version": (
        "xonotic-stage2-target-motion-replacement-contract-v1"
    ),
    "source_manifest": (
        "manifests/stage2_target_motion_review_v1/input.jsonl"
    ),
    "source_manifest_sha256": base.capture.sha256_file(
        SOURCE_MANIFEST
    ),
    "source_reject_manifest": str(
        SOURCE_REJECTS.relative_to(base.ROOT)
    ),
    "source_reject_manifest_sha256": base.capture.sha256_file(
        SOURCE_REJECTS
    ),
    "source_incomplete_group_id": (
        "s2targetreviewv1_g02_close_approach_retreat"
    ),
    "source_terminal_episode_id": (
        "s2targetreviewv1_g02_close_approach_retreat_"
        "p05_sustained_tracking"
    ),
    "source_terminal_reason": "stage2_causal_qa_failed",
    "replacement_reason": (
        "post_interaction_knockback_is_outcome_not_aim_"
        "treatment_failure"
    ),
    "source_candidates_immutable": True,
    "whole_counterfactual_group_replaced": True,
    "geometry_weapon_policy_mutated": False,
    "runtime_geometry_fallback": False,
    "runtime_action_fallback": False,
    "treatment_reference": (
        "manifest_frozen_analytic_enemy_trajectory"
    ),
}


def validate_source_terminal() -> None:
    terminal = [
        row
        for row in base.capture.load_jsonl(SOURCE_REJECTS)
        if row.get("terminal") is True
    ]
    expected_id = base.REPLACEMENT_CONTRACT[
        "source_terminal_episode_id"
    ]
    matches = [
        row for row in terminal if row["episode_id"] == expected_id
    ]
    if (
        len(matches) != 1
        or matches[0]["reason"]
        != base.REPLACEMENT_CONTRACT[
            "source_terminal_reason"
        ]
    ):
        raise base.capture.CaptureFailure(
            "stage2_target_motion_replacement_terminal_drift",
            base.capture.canonical_json(terminal),
        )


def main() -> int:
    validate_source_terminal()
    rows = base.materialize()
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
                "seeds": sorted({row["seed"] for row in rows}),
                "source_certificates": sorted(
                    {
                        row["encounter_certificate"][
                            "certificate_id"
                        ]
                        for row in rows
                    }
                ),
                "output_root": str(base.OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
