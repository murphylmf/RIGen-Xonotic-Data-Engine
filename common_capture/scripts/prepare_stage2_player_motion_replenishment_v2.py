                      
"""Build a fresh complete jump-policy group from the v5 certificate."""

from __future__ import annotations

import json

import prepare_stage2_player_motion_replenishment as base


base.GROUP_PREFIX = "s2playermotion_repl2"
base.CANDIDATE_KIND = "player_motion_causal_replenishment_v2"
base.TRAINING_STAGE = (
    "stage2_bounded_player_motion_replenishment_v2_only"
)
base.SUPERSEDES_COHORT = "stage2_player_motion_replenishment_v1"
base.SUPERSESSION_REASON = (
    "new_seed_after_terminal_jump_overlay_bound_rejection"
)
base.MANIFEST_SCHEMA = (
    "xonotic-stage2-player-motion-replenishment-manifest-v2"
)
base.OUTPUT_ROOT = (
    base.ROOT / "manifests/stage2_player_motion_replenishment_v2"
)
base.SOURCES = (
    {
        "motion_class": "jumping",
        "manifest": (
            base.ROOT
            / "manifests/stage2_path_encounter_certification_v5/"
            "input.jsonl"
        ),
        "episode_id": "s2pathcertv5_01_s1route_11563",
        "certificate_index": (
            base.ROOT
            / "stage2_path_encounter_certification_v5_output/"
            "review/PATH_ENCOUNTER_CERTIFICATES.jsonl"
        ),
    },
)


def main() -> int:
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
                "output_root": str(base.OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
