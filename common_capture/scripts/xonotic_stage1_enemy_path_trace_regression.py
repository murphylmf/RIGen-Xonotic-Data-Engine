                      
"""Run one full H200 regression for each Stage-1 distractor policy."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              
import xonotic_stage1_enemy_policy_audio_preflight_v2 as audio_v2              
import xonotic_stage1_review as review              


ROOT = capture.ROOT
SPLIT = "v2_stage1_enemy_path_trace_regression"
OUTPUT_ROOT = ROOT / SPLIT
REPORT_PATH = OUTPUT_ROOT / "ENEMY_PATH_TRACE_REGRESSION.json"
POLICIES = (
    "idle",
    "lateral_patrol",
    "approach_retreat",
    "stop_and_go",
)
APPROACH_PAIR = {
    "map": "techassault",
    "gametype": "as",
    "source_probe": (
        "preflight_pair_techassault_extreme_r0_wp0032_wp0033"
    ),
    "variant": "forward",
    "player_origin": [1984.0, 960.0, 24.1],
    "enemy_origin": [1984.0, -960.0, 24.1],
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def scenarios() -> list[dict[str, Any]]:
    audio_v2.configure_version()
    source_rows = audio_v2.implementation.scenario_rows()
    selected: list[dict[str, Any]] = []
    for ordinal, policy in enumerate(POLICIES, 1):
                                                                      
                                                                            
                                                                           
                                                                            
                                                            
        context = (
            "visible_close"
            if policy == "approach_retreat"
            else "distribution"
        )
        source = next(
            row
            for row in source_rows
            if row["enemy_policy"]["name"] == policy
            and row["audio_review_context"] == context
        )
        row = copy.deepcopy(source)
        old_id = row["episode_id"]
        episode_id = f"s1pathtrace_{ordinal:03d}"
        row.update(
            {
                "episode_id": episode_id,
                "source_episode_id": old_id,
                "source_split": row["split"],
                "split": SPLIT,
                "training_stage": "stage1_path_trace_regression_only",
                "formal_collection_authorized": False,
                "training_admitted": False,
            }
        )
        row["anchor_id"] = str(row["anchor_id"]).replace(
            old_id, episode_id
        )
        if policy == "approach_retreat":
            row.update(
                {
                    "map": APPROACH_PAIR["map"],
                    "gametype": APPROACH_PAIR["gametype"],
                    "anchor_id": (
                        f"{APPROACH_PAIR['map']}_{episode_id}_pair"
                    ),
                    "map_region_id": APPROACH_PAIR["source_probe"],
                    "selected_geometry": {
                        "source_pair": APPROACH_PAIR[
                            "source_probe"
                        ],
                        "variant": APPROACH_PAIR["variant"],
                    },
                    "pair_candidates": [],
                }
            )
            row["player"]["origin"] = list(
                APPROACH_PAIR["player_origin"]
            )
            row["enemy"]["origin"] = list(
                APPROACH_PAIR["enemy_origin"]
            )
            review.apply_enemy_policy_geometry(row)
        selected.append(row)
    return selected


def run_one(row: dict[str, Any]) -> dict[str, Any]:
    result = v2.run_full_attempt(
        row, retry=0, destination_root=OUTPUT_ROOT / "attempts"
    )
    qa = result["qa"]
    trace = qa["enemy_policy"]["whole_path_trace"]
    movement_audio = qa["enemy_policy"]["movement_audio"]
    return {
        "episode_id": row["episode_id"],
        "policy": row["enemy_policy"]["name"],
        "map": row["map"],
        "gametype": row["gametype"],
        "renderer": qa["runtime"]["renderer"],
        "hard_gates_pass": all(qa["hard_gates"].values()),
        "video_frames": qa["video"]["frames"],
        "audio_samples_per_channel": qa["audio"][
            "samples_per_channel"
        ],
        "frame_tick_mapping_rate": qa["mapping"]["success_rate"],
        "whole_path_trace": trace,
        "movement_audio": movement_audio,
        "persistent_stage": result["persistent_stage"],
        "persistent_sha256_count": len(result["persistent_sha256"]),
    }


def main() -> int:
    capture.require_conda()
    rows = scenarios()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=len(rows)
    ) as executor:
        results = list(executor.map(run_one, rows))
    report = {
        "schema_version": (
            "xonotic-stage1-enemy-path-trace-regression-v1"
        ),
        "created_utc": capture.utc_now(),
        "source_commit": (
            capture.build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip(),
        "episodes": results,
        "passed": (
            len(results) == len(POLICIES)
            and all(row["hard_gates_pass"] for row in results)
            and all(
                row["whole_path_trace"]["passed"] for row in results
            )
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
    }
    atomic_json(REPORT_PATH, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
