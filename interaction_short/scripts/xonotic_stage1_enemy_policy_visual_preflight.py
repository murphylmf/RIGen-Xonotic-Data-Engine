                      
"""Visible, close/near four-policy review supplement.

This is intentionally separate from the trajectory-distribution policy
preflight. Its fixed low-motion camera makes each policy legible to a human;
the rows are review-only and must not be used as the Stage 1 training
distribution.
"""

from __future__ import annotations

import copy
from typing import Any

import xonotic_capture as capture
import xonotic_stage1_enemy_policy_preflight as base
import xonotic_stage1_review as review


SPLIT = "v2_stage1_enemy_policy_visual_preflight"
PREFLIGHT_ROOT = capture.ROOT / SPLIT
SCENARIOS_PATH = (
    capture.ROOT / f"configs/{SPLIT}_scenarios.jsonl"
)
CANDIDATES_PATH = PREFLIGHT_ROOT / "manifests/candidates.jsonl"
REJECTS_PATH = PREFLIGHT_ROOT / "manifests/rejects.jsonl"
AUDIT_PATH = PREFLIGHT_ROOT / "POLICY_PREFLIGHT_AUDIT.json"
REPORT_PATH = PREFLIGHT_ROOT / "POLICY_PREFLIGHT_REPORT.md"
PREVIEW_ROOT = (
    capture.ROOT / "previews/stage1_enemy_policy_visual_preflight"
)

VISUAL_SOURCES = (
    ("idle", "s1review_034", "near_crosshair", -9.5),
    ("lateral_patrol", "s1review_044", "near_crosshair", -9.5),
    ("approach_retreat", "s1review_047", "center_linger", -4.0),
    ("stop_and_go", "s1review_043", "near_crosshair", -9.5),
)


def configure_base() -> None:
    base.SPLIT = SPLIT
    base.PREFLIGHT_ROOT = PREFLIGHT_ROOT
    base.SCENARIOS_PATH = SCENARIOS_PATH
    base.CANDIDATES_PATH = CANDIDATES_PATH
    base.REJECTS_PATH = REJECTS_PATH
    base.AUDIT_PATH = AUDIT_PATH
    base.REPORT_PATH = REPORT_PATH
    base.PREVIEW_ROOT = PREVIEW_ROOT
    base.PROFILE_NAME = "visible_close_policy_review"
    base.REQUIRE_VISIBILITY = True
    base.POLICY_SOURCES = tuple(
        (name, source_id)
        for name, source_id, _, _ in VISUAL_SOURCES
    )


def scenario_rows() -> list[dict[str, Any]]:
    source = {
        row["episode_id"]: row for row in review.build_scenarios()
    }
    rows: list[dict[str, Any]] = []
    for ordinal, (
        policy_name,
        source_id,
        relation,
        yaw_offset,
    ) in enumerate(VISUAL_SOURCES, 1):
        row = copy.deepcopy(source[source_id])
        if row["enemy_policy"]["name"] != policy_name:
            raise capture.CaptureFailure(
                "enemy_policy_visual_source_drift",
                f"{source_id}:{row['enemy_policy']['name']}!={policy_name}",
            )
        old_id = row["episode_id"]
        episode_id = f"s1polvis_{ordinal:03d}"
        row.update(
            {
                "episode_id": episode_id,
                "source_episode_id": old_id,
                "source_split": row["split"],
                "split": SPLIT,
                "seed": 13_300_000 + ordinal,
                "training_stage": (
                    "stage1_enemy_policy_visual_preflight_only"
                ),
                "acceptance_policy": capture.TIERED_REVIEW_POLICY,
                "fixed_variant_index": 0,
                "formal_collection_authorized": False,
                "human_review_required_before_training": True,
                "initial_yaw_offset": yaw_offset,
                "expects_sound": False,
            }
        )
        row["review_targets"].update(
            {
                "target_relation": relation,
                "net_displacement_bin": "lt64",
                "yaw_range_bin": "lt15",
                "pitch_range_bin": "lt5",
            }
        )
        row["review_action"].update(
            {
                "relation": relation,
                "move_duration_candidates": [0],
                "move_start_tick": 0,
                "yaw_amplitude": 0.0,
                "pitch_amplitude": 0.0,
                "jump": False,
                "fire_mode": "none",
                "trajectory_policy": "policy_visual_fixed_camera",
            }
        )
        row["policy_visual_review"] = {
            "distribution_representative": False,
            "required_visible_fraction": (
                base.MIN_VISUAL_VISIBLE_FRACTION
            ),
            "required_within_15_deg_fraction": (
                base.MIN_VISUAL_WITHIN_15_DEG_FRACTION
            ),
            "camera_policy": "fixed_nonreactive",
        }
        row["anchor_id"] = str(row["anchor_id"]).replace(
            old_id, episode_id
        )
        policy_seed = 13_400_000 + ordinal
        row["enemy_policy"]["policy_seed"] = policy_seed
        row["enemy_policy"]["motion_start_tick"] = (
            0
            if policy_name == "idle"
            else policy_seed % capture.WARMUP_TICKS
        )
        row = review.apply_variant(row, 0)
        if not review.stage1_render_map_allowed(row["map"]):
            raise capture.CaptureFailure(
                "enemy_policy_visual_map_excluded", row["map"]
            )
        rows.append(row)
    return rows


def main() -> int:
    configure_base()
    base.scenario_rows = scenario_rows
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
