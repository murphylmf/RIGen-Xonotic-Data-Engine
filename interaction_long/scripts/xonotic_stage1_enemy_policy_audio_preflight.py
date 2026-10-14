                      
"""Eight-row enemy-policy and native movement-audio review batch."""

from __future__ import annotations

import copy
from typing import Any

import xonotic_capture as capture
import xonotic_stage1_enemy_policy_preflight as base
import xonotic_stage1_review as review


SPLIT = "v2_stage1_enemy_policy_audio_preflight"
PREFLIGHT_ROOT = capture.ROOT / SPLIT
SCENARIOS_PATH = capture.ROOT / f"configs/{SPLIT}_scenarios.jsonl"
CANDIDATES_PATH = PREFLIGHT_ROOT / "manifests/candidates.jsonl"
REJECTS_PATH = PREFLIGHT_ROOT / "manifests/rejects.jsonl"
AUDIT_PATH = PREFLIGHT_ROOT / "POLICY_PREFLIGHT_AUDIT.json"
REPORT_PATH = PREFLIGHT_ROOT / "POLICY_PREFLIGHT_REPORT.md"
PREVIEW_ROOT = capture.ROOT / "previews/stage1_enemy_policy_audio_preflight"
EPISODE_PREFIX = "s1polaud"

                                                                              
                                                                             
                            
AUDIO_SOURCES = (
    ("idle", "s1review_053", "distribution", None),
    ("lateral_patrol", "s1review_021", "distribution", None),
    ("approach_retreat", "s1review_030", "distribution", None),
    ("stop_and_go", "s1review_032", "distribution", None),
    ("idle", "s1review_034", "visible_close", -9.5),
    ("lateral_patrol", "s1review_044", "visible_close", -9.5),
    ("approach_retreat", "s1review_047", "visible_close", -4.0),
    ("stop_and_go", "s1review_043", "visible_close", -9.5),
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
    base.PROFILE_NAME = "mixed_distribution_and_visible_audio_review"
    base.REQUIRE_VISIBILITY = False
    base.REQUIRE_ENEMY_AUDIO = True
    base.POLICY_SOURCES = tuple(
        (name, source_id)
        for name, source_id, _, _ in AUDIO_SOURCES
    )


def scenario_rows() -> list[dict[str, Any]]:
    source = {
        row["episode_id"]: row for row in review.build_scenarios()
    }
    rows: list[dict[str, Any]] = []
    for ordinal, (
        policy_name,
        source_id,
        context,
        yaw_offset,
    ) in enumerate(AUDIO_SOURCES, 1):
        row = copy.deepcopy(source[source_id])
        if row["enemy_policy"]["name"] != policy_name:
            raise capture.CaptureFailure(
                "enemy_policy_audio_source_drift",
                f"{source_id}:{row['enemy_policy']['name']}!={policy_name}",
            )
        old_id = row["episode_id"]
        episode_id = f"{EPISODE_PREFIX}_{ordinal:03d}"
        row.update(
            {
                "episode_id": episode_id,
                "source_episode_id": old_id,
                "source_split": row["split"],
                "split": SPLIT,
                "seed": 13_500_000 + ordinal,
                "training_stage": (
                    "stage1_enemy_policy_audio_preflight_only"
                ),
                "acceptance_policy": capture.TIERED_REVIEW_POLICY,
                "fixed_variant_index": 0,
                "formal_collection_authorized": False,
                "human_review_required_before_training": True,
                "audio_review_context": context,
                "expects_sound": policy_name != "idle",
            }
        )
        row["anchor_id"] = str(row["anchor_id"]).replace(
            old_id, episode_id
        )
        policy_seed = 13_600_000 + ordinal
        row["enemy_policy"].update(
            {
                "policy_seed": policy_seed,
                "motion_start_tick": (
                    0
                    if policy_name == "idle"
                    else policy_seed % capture.WARMUP_TICKS
                ),
                "movement_audio": capture.ENEMY_MOVEMENT_AUDIO_MODE,
                "step_stride_units": capture.ENEMY_STEP_STRIDE_UNITS,
            }
        )
        if context == "visible_close":
            row["initial_yaw_offset"] = yaw_offset
            row["review_targets"].update(
                {
                    "target_relation": (
                        "center_linger"
                        if policy_name == "approach_retreat"
                        else "near_crosshair"
                    ),
                    "net_displacement_bin": "lt64",
                    "yaw_range_bin": "lt15",
                    "pitch_range_bin": "lt5",
                }
            )
            row["review_action"].update(
                {
                    "relation": row["review_targets"][
                        "target_relation"
                    ],
                    "move_duration_candidates": [0],
                    "move_start_tick": 0,
                    "yaw_amplitude": 0.0,
                    "pitch_amplitude": 0.0,
                    "jump": False,
                    "fire_mode": "none",
                    "trajectory_policy": (
                        "policy_audio_visual_fixed_camera"
                    ),
                }
            )
            row["policy_visual_review"] = {
                "distribution_representative": False,
                "camera_policy": "fixed_nonreactive",
            }
        row = review.apply_variant(row, 0)
        if not review.stage1_render_map_allowed(row["map"]):
            raise capture.CaptureFailure(
                "enemy_policy_audio_map_excluded", row["map"]
            )
        rows.append(row)
    return rows


def main() -> int:
    configure_base()
    base.scenario_rows = scenario_rows
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
