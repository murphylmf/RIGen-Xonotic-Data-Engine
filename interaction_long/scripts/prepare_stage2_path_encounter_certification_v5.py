                      
"""Build the new-seed jump-overlay certificate with a 32-unit bound."""

from __future__ import annotations

import json

import prepare_stage2_path_encounter_certification_v4 as base
import xonotic_stage2_causal as causal


base.SEED = 14_611_563
base.POSITION_TOLERANCE = causal.JUMP_VIEW_OVERLAY_REPLAY_TOLERANCE
base.EPISODE_PREFIX = "s2pathcertv5"
base.GROUP_ID = "s2pathcertv5_g01"
base.CANDIDATE_KIND = "path_encounter_certification_v5"
base.TRAINING_STAGE = (
    "stage2_bounded_path_encounter_certification_v5_only"
)
base.MANIFEST_SCHEMA = (
    "xonotic-stage2-path-encounter-certification-manifest-v5"
)
base.PLAYER_PATH_SOURCE_SCHEMA = causal.PLAYER_PATH_SOURCE_SCHEMA_V4
base.OVERLAY_REPLAY_TOLERANCE_BASIS = (
    causal.JUMP_VIEW_OVERLAY_TOLERANCE_BASIS
)
base.SUPERSEDES_COHORT = "stage2_path_encounter_certification_v4"
base.SUPERSESSION_REASON = (
    "new_seed_with_preregistered_one_player_hull_jump_overlay_bound"
)
base.OUTPUT_ROOT = (
    base.ROOT / "manifests/stage2_path_encounter_certification_v5"
)
base.DERIVED_ACTIONS = (
    base.ROOT
    / "stage2_routes/derived/"
    f"{base.ROUTE_ID}_seed{base.SEED}/frozen_actions.csv"
)


def main() -> int:
    rows = base.materialize()
    print(
        json.dumps(
            {
                "rows": len(rows),
                "episode_id": rows[0]["episode_id"],
                "seed": rows[0]["seed"],
                "position_tolerance": base.POSITION_TOLERANCE,
                "tolerance_basis": (
                    base.OVERLAY_REPLAY_TOLERANCE_BASIS
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
