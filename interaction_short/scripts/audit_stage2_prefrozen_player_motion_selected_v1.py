                      
"""Consolidate independent QA for the selected Stage-2 motion review."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import select_stage2_prefrozen_player_motion_review_v1 as selector              
import xonotic_capture as capture              


MANIFEST = (
    ROOT
    / "manifests/stage2_prefrozen_player_motion_review_v1"
    / "selected_input.jsonl"
)
OUTPUT_ROOT = (
    ROOT / "stage2_prefrozen_player_motion_review_v1_output"
)
AUDIT_PATH = OUTPUT_ROOT / "SELECTED_ARTIFACT_AUDIT.json"
CANDIDATE_ROOTS = (
    ROOT / "stage2_prefrozen_player_motion_review_v1_output",
    ROOT
    / "stage2_prefrozen_player_motion_replenishment_v1_output",
    ROOT
    / "stage2_prefrozen_player_motion_replenishment_v2_output",
    ROOT
    / "stage2_prefrozen_player_motion_replenishment_v3_output",
)


def accepted_paths() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for root in CANDIDATE_ROOTS:
        for row in selector.published_rows(root, "accepted.jsonl"):
            episode_id = str(row["episode_id"])
            path = Path(row["episode_path"])
            if episode_id in found and found[episode_id] != path:
                raise capture.CaptureFailure(
                    "selected_audit_duplicate_accepted_episode",
                    episode_id,
                )
            found[episode_id] = path
    return found


def motion_profile(row: dict[str, Any]) -> str:
    design = (
        row.get("prefrozen_player_motion_review_design")
        or row.get("prefrozen_player_motion_replenishment_design")
        or {}
    )
    return str(design["motion_profile"])


def main() -> int:
    selected = capture.load_jsonl(MANIFEST)
    accepted = accepted_paths()
    selection = json.loads(
        (OUTPUT_ROOT / "SELECTION_AUDIT.json").read_text(
            encoding="utf-8"
        )
    )
    episode_results: list[dict[str, Any]] = []
    all_checks: list[bool] = []
    weapon_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"episodes": 0, "shots": 0, "confirmed_hits": 0}
    )
    group_profiles: dict[str, str] = {}
    group_hashes: dict[str, set[str]] = defaultdict(set)

    for row in selected:
        episode_id = str(row["episode_id"])
        path = accepted.get(episode_id)
        if path is None:
            raise capture.CaptureFailure(
                "selected_audit_artifact_missing", episode_id
            )
        episode = json.loads(
            (path / "episode.json").read_text(encoding="utf-8")
        )
        qa = json.loads(
            (path / "qa.json").read_text(encoding="utf-8")
        )
        causal = json.loads(
            (path / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        frames = pd.read_parquet(path / "frames.parquet")
        actions = pd.read_parquet(path / "actions.parquet")
        model_actions = pd.read_parquet(
            path / "model_actions.parquet"
        )
        states = pd.read_parquet(path / "states.parquet")
        relations = pd.read_parquet(
            path / "target_relations.parquet"
        )
        stats = selector.artifact_stats(path)
        player_path = causal["player_path"]
        hard_gates = qa.get("hard_gates") or {}
        checks = {
            "episode_identity": episode.get("episode_id")
            == episode_id,
            "accepted": qa.get("accepted") is True,
            "capture_valid": qa.get("capture_valid") is True,
            "all_hard_gates": bool(hard_gates)
            and all(bool(value) for value in hard_gates.values()),
            "video_320": qa.get("video", {}).get("frames")
            == capture.OUTPUT_TICKS,
            "audio_240000": qa.get("audio", {}).get(
                "samples_per_channel"
            )
            == capture.AUDIO_SAMPLES,
            "audio_non_silent": float(
                qa.get("audio", {}).get("nonzero_fraction", 0.0)
            )
            > 0.0,
            "mapping_320": qa.get("mapping", {}).get(
                "mapped_frames"
            )
            == capture.OUTPUT_TICKS,
            "mapping_tick_span": len(frames)
            == capture.OUTPUT_TICKS
            and frames["episode_server_tick"].astype(int).tolist()
            == list(
                range(
                    capture.WARMUP_TICKS,
                    capture.TOTAL_TICKS,
                )
            ),
            "frame_action_alignment": len(model_actions)
            == capture.OUTPUT_TICKS
            and np.array_equal(
                model_actions["source_action_tick"].to_numpy(
                    dtype=np.int64
                ),
                frames["episode_server_tick"].to_numpy(
                    dtype=np.int64
                ),
            ),
            "engine_rows_384": len(actions)
            == len(states)
            == capture.TOTAL_TICKS,
            "relations_320": len(relations)
            == capture.OUTPUT_TICKS,
            "model_action_contract": all(
                qa.get("gates", {}).get(name) is True
                for name in (
                    "model_action_buttons_binary",
                    "model_action_continuous_range",
                    "model_action_engine_roundtrip",
                    "model_action_frame_alignment",
                    "model_action_ltx2_schema",
                    "model_action_rows_exact",
                )
            ),
            "renderer_h200": str(
                qa.get("runtime", {}).get("renderer", "")
            ).startswith("NVIDIA H200"),
            "cpu_x264_flac": all(
                qa.get("gates", {}).get(name) is True
                for name in (
                    "encoded_flac_s16_stereo_48khz",
                    "encoded_h264_high",
                    "encoded_yuv420p",
                )
            )
            and qa.get("runtime", {}).get("x264_preset")
            == "medium",
            "hud_and_gametype": all(
                qa.get("gates", {}).get(name) is True
                for name in (
                    "minimal_hud_policy",
                    "server_objective_waypoints_disabled",
                    "gametype_exact",
                )
            ),
            "player_motion_passed": player_path.get("passed") is True
            and stats["player_motion"]["active_frames"] >= 192,
            "collision_and_fall_passed": all(
                player_path.get("checks", {}).get(name) is True
                for name in (
                    "collision_policy_passed",
                    "ordinary_movement_clear",
                    "horizontal_path_realized",
                    "horizontal_displacement_bounded",
                    "no_unintended_fall",
                )
            ),
            "enemy_hit_recomputed": stats["checks"][
                "confirmed_hits_exact"
            ],
            "outcome_not_admission": stats["checks"][
                "outcome_not_episode_admission"
            ],
            "nontraining": episode.get(
                "formal_collection_authorized"
            )
            is False
            and episode.get("training_admitted") is False,
        }
        passed = all(checks.values())
        all_checks.append(passed)
        weapon = str(row["weapon"])
        weapon_totals[weapon]["episodes"] += 1
        weapon_totals[weapon]["shots"] += int(stats["shots"])
        weapon_totals[weapon]["confirmed_hits"] += int(
            stats["confirmed_hits"]
        )
        group_id = str(row["counterfactual_group_id"])
        group_profiles[group_id] = motion_profile(row)
        group_hashes[group_id].add(
            str(row["exogenous_contract_sha256"])
        )
        episode_results.append(
            {
                "episode_id": episode_id,
                "artifact_path": str(path),
                "weapon": weapon,
                "group_id": group_id,
                "motion_profile": motion_profile(row),
                "shots": int(stats["shots"]),
                "confirmed_enemy_hits": int(
                    stats["confirmed_hits"]
                ),
                "player_motion": stats["player_motion"],
                "checks": checks,
                "passed": passed,
            }
        )

    shots = sum(
        row["confirmed_hits"] * 0 + row["shots"]
        for row in weapon_totals.values()
    )
    hits = sum(
        row["confirmed_hits"] for row in weapon_totals.values()
    )
    group_sizes = Counter(
        str(row["counterfactual_group_id"]) for row in selected
    )
    profile_counts = Counter(group_profiles.values())
    summary_checks = {
        "selection_audit_passed": selection.get("passed") is True,
        "selection_target_90_percent_met": selection.get(
            "target_90_percent_met"
        )
        is True,
        "rows_27": len(selected) == 27,
        "weapons_9x3": Counter(
            str(row["weapon"]) for row in selected
        )
        == {
            weapon: 3
            for weapon in selector.prep.stochastic_v1.human_v2.WEAPONS
        },
        "groups_9x3": len(group_sizes) == 9
        and set(group_sizes.values()) == {3},
        "profiles_5_4": sorted(profile_counts.values()) == [4, 5],
        "group_exogenous_exact": all(
            len(values) == 1 for values in group_hashes.values()
        ),
        "shots_match_selection": shots
        == int(selection["winner"]["shots"]),
        "hits_match_selection": hits
        == int(selection["winner"]["confirmed_hits"]),
        "all_episode_checks": all(all_checks),
    }
    paths = [
        float(row["player_motion"]["horizontal_path_length"])
        for row in episode_results
    ]
    displacements = [
        float(
            row["player_motion"][
                "maximum_horizontal_displacement"
            ]
        )
        for row in episode_results
    ]
    active_frames = [
        int(row["player_motion"]["active_frames"])
        for row in episode_results
    ]
    audit = {
        "schema_version": (
            "xonotic-stage2-prefrozen-player-motion-selected-audit-v1"
        ),
        "manifest": str(MANIFEST),
        "manifest_sha256": capture.sha256_file(MANIFEST),
        "selection_audit": str(
            OUTPUT_ROOT / "SELECTION_AUDIT.json"
        ),
        "selection_audit_sha256": capture.sha256_file(
            OUTPUT_ROOT / "SELECTION_AUDIT.json"
        ),
        "candidate_output_roots": [
            str(path) for path in CANDIDATE_ROOTS
        ],
        "episodes": len(selected),
        "groups": len(group_sizes),
        "shots": shots,
        "confirmed_enemy_hits": hits,
        "confirmed_enemy_hit_rate": hits / shots,
        "weapons_with_confirmed_hit": sum(
            values["confirmed_hits"] > 0
            for values in weapon_totals.values()
        ),
        "weapon_totals": dict(weapon_totals),
        "motion_profile_groups": dict(profile_counts),
        "movement_metrics": {
            "active_frames_min": min(active_frames),
            "active_frames_max": max(active_frames),
            "horizontal_path_length_min": min(paths),
            "horizontal_path_length_max": max(paths),
            "maximum_horizontal_displacement_min": min(
                displacements
            ),
            "maximum_horizontal_displacement_max": max(
                displacements
            ),
        },
        "summary_checks": summary_checks,
        "episode_results": episode_results,
        "passed": all(summary_checks.values()),
    }
    selector.atomic_json(AUDIT_PATH, audit)
    print(
        capture.canonical_json(
            {
                key: audit[key]
                for key in (
                    "episodes",
                    "groups",
                    "shots",
                    "confirmed_enemy_hits",
                    "confirmed_enemy_hit_rate",
                    "weapons_with_confirmed_hit",
                    "movement_metrics",
                    "passed",
                )
            }
        )
    )
    return 0 if audit["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
