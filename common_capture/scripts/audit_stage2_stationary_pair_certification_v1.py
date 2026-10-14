                      
"""Audit the bounded Stage-2 stationary-pair live certification."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xonotic_capture as capture              


MANIFEST = (
    ROOT / "manifests/stage2_stationary_pair_certification_v1/input.jsonl"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT / "stage2_stationary_pair_certification_v1_r2_output"
)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def journals(output_root: Path, name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            f"shard-*-of-*/{name}.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def audit(output_root: Path, require_complete: bool) -> dict[str, Any]:
    planned = capture.load_jsonl(MANIFEST)
    planned_by_id = {row["episode_id"]: row for row in planned}
    accepted_rows = journals(output_root, "accepted")
    reject_rows = journals(output_root, "rejects")
    accepted_counts = Counter(row["episode_id"] for row in accepted_rows)
    terminal = [row for row in reject_rows if row.get("terminal") is True]
    terminal_counts = Counter(row["episode_id"] for row in terminal)
    accepted_by_id = {row["episode_id"]: row for row in accepted_rows}
    terminal_by_id = {row["episode_id"]: row for row in terminal}
    results: list[dict[str, Any]] = []
    certified_pairs: list[str] = []
    for episode_id in sorted(accepted_by_id):
        scenario = planned_by_id[episode_id]
        accepted = accepted_by_id[episode_id]
        package = Path(accepted["episode_path"])
        qa = json.loads((package / "qa.json").read_text())
        causal = json.loads(
            (package / "causal_interaction.json").read_text()
        )
        frames = pd.read_parquet(package / "frames.parquet")
        actions = pd.read_parquet(package / "model_actions.parquet")
        states = pd.read_parquet(package / "states.parquet")
        shots = pd.read_parquet(package / "shot_outcomes.parquet")
        player_checks = causal["player_path"]["checks"]
        enemy_checks = causal["enemy_random_policy"]["checks"]
        gates = qa.get("gates") or {}
        checks = {
            "identity": qa.get("episode_id") == episode_id,
            "accepted": qa.get("accepted") is True,
            "all_hard_gates": bool(qa.get("hard_gates"))
            and all(qa["hard_gates"].values()),
            "video_320": len(frames) == 320
            and qa["video"]["frames"] == 320,
            "audio_240000": qa["audio"]["samples_per_channel"]
            == 240_000,
            "mapping_exact": qa["mapping"]["mapped_frames"] == 320
            and frames["episode_server_tick"].astype(int).tolist()
            == list(range(64, 384)),
            "actions_320_states_384": len(actions) == 320
            and len(states) == 384,
            "renderer_h200": str(
                qa["runtime"].get("renderer", "")
            ).startswith("NVIDIA H200"),
            "x264_medium_16_flac": qa["runtime"].get("x264_preset")
            == "medium"
            and int(qa["runtime"].get("x264_threads", -1)) == 16
            and gates.get("encoded_flac_s16_stereo_48khz") is True,
            "hud_gametype": all(
                gates.get(name) is True
                for name in (
                    "minimal_hud_policy",
                    "server_objective_waypoints_disabled",
                    "gametype_exact",
                )
            ),
            "causal_passed": causal.get("passed") is True,
            "stationary_player_safe": all(player_checks.values()),
            "stationary_enemy_safe": all(enemy_checks.values()),
            "no_fire": causal.get("actual_outcome") == "no_fire"
            and len(shots) == 0,
            "target_observed": causal.get("visible_frames", 0) >= 8,
        }
        passed = all(checks.values())
        if passed:
            certified_pairs.append(
                scenario["formal_design"]["source_pair_episode_id"]
            )
        results.append(
            {
                "episode_id": episode_id,
                "source_pair_episode_id": scenario["formal_design"][
                    "source_pair_episode_id"
                ],
                "map": scenario["map"],
                "gametype": scenario["gametype"],
                "distance_bin": scenario["formal_design"]["distance_bin"],
                "checks": checks,
                "passed": passed,
            }
        )
    completed_ids = set(accepted_by_id) | set(terminal_by_id)
    certified_scenarios = [
        planned_by_id[result["episode_id"]]
        for result in results
        if result["passed"]
    ]
    distance_counts = Counter(
        row["formal_design"]["distance_bin"]
        for row in certified_scenarios
    )
    map_count = len({row["map"] for row in certified_scenarios})
    checks = {
        "planned_63": len(planned) == 63,
        "complete": len(completed_ids) == len(planned),
        "exactly_once": all(value == 1 for value in accepted_counts.values())
        and all(value == 1 for value in terminal_counts.values())
        and not (set(accepted_by_id) & set(terminal_by_id))
        and completed_ids <= set(planned_by_id),
        "all_accepted_artifacts_pass": len(results)
        == len(accepted_by_id)
        and all(result["passed"] for result in results),
        "bounded_pool_large_enough": len(certified_pairs) >= 45,
        "map_coverage": map_count >= 24,
        "all_distance_bins": set(distance_counts)
        == {"close", "near", "medium", "far", "very_far", "extreme"},
        "outcome_not_used_for_certification": all(
            row["acceptance"]["actual_outcome"] is None
            and row["formal_design"][
                "outcome_recipe_is_individual_admission_gate"
            ]
            is False
            for row in planned
        ),
    }
    result = {
        "schema_version": (
            "xonotic-stage2-stationary-pair-certification-audit-v1"
        ),
        "manifest": str(MANIFEST),
        "manifest_sha256": capture.sha256_file(MANIFEST),
        "planned_pairs": len(planned),
        "certified_pairs": len(certified_pairs),
        "terminal_rejects": len(terminal_by_id),
        "certified_maps": map_count,
        "certified_distance_distribution": dict(distance_counts),
        "certified_source_pair_episode_ids": sorted(certified_pairs),
        "terminal_pair_rejects": [
            {
                "episode_id": episode_id,
                "source_pair_episode_id": planned_by_id[episode_id][
                    "formal_design"
                ]["source_pair_episode_id"],
                "reason": terminal_by_id[episode_id].get("reason"),
                "detail": terminal_by_id[episode_id].get("detail"),
            }
            for episode_id in sorted(terminal_by_id)
        ],
        "episode_results": results,
        "checks": checks,
        "complete": checks["complete"],
        "passed": all(checks.values()),
    }
    path = output_root / "STATIONARY_PAIR_CERTIFICATION_AUDIT.json"
    atomic_json(path, result)
    if require_complete and not result["passed"]:
        raise capture.CaptureFailure(
            "stage2_stationary_pair_certification_audit_failed",
            capture.canonical_json(checks),
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.output_root.resolve(), args.require_complete)
    print(
        capture.canonical_json(
            {
                "planned": result["planned_pairs"],
                "certified": result["certified_pairs"],
                "terminal": result["terminal_rejects"],
                "maps": result["certified_maps"],
                "complete": result["complete"],
                "passed": result["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
