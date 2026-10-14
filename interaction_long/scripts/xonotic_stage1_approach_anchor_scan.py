                      
"""Find a live-validated Stage-1 approach/retreat regression anchor."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_manifests as manifests              
import run_capture_manifest_shard as common              
import xonotic_capture as capture              
import xonotic_stage1_enemy_policy_audio_preflight_v2 as audio_v2              
import xonotic_stage1_review as review              


OUTPUT = (
    capture.ROOT
    / "v2_stage1_enemy_path_trace_regression"
    / "APPROACH_ANCHOR_SCAN.json"
)


def base_scenario() -> dict[str, Any]:
    audio_v2.configure_version()
    return copy.deepcopy(
        next(
            row
            for row in audio_v2.implementation.scenario_rows()
            if row["enemy_policy"]["name"] == "approach_retreat"
            and row["audio_review_context"] == "visible_close"
        )
    )


def candidates(limit: int) -> list[dict[str, Any]]:
    _, pools = manifests.preflight_pools()
    priority = {
        "extreme": 0,
        "very_far": 1,
        "far": 2,
        "medium": 3,
        "near": 4,
        "close": 5,
    }
    pairs = sorted(
        (
            pair
            for distance_pairs in pools.values()
            for pair in distance_pairs
        ),
        key=lambda row: (
            priority[row["distance_bin"]],
            row["map"],
            row["source_probe"],
            row["variant"],
        ),
    )
                                                               
    selected: list[dict[str, Any]] = []
    used_maps: set[str] = set()
    for pass_index in (0, 1):
        for pair in pairs:
            if pass_index == 0 and pair["map"] in used_maps:
                continue
            if pass_index == 1 and pair in selected:
                continue
            selected.append(pair)
            used_maps.add(pair["map"])
            if len(selected) >= limit:
                return selected
    return selected


def scenario_for(
    template: dict[str, Any],
    pair: dict[str, Any],
    ordinal: int,
) -> dict[str, Any]:
    row = copy.deepcopy(template)
    episode_id = f"s1approachscan_{ordinal:03d}"
    row.update(
        {
            "episode_id": episode_id,
            "map": pair["map"],
            "gametype": pair["gametype"],
            "anchor_id": f"{pair['map']}_{episode_id}_pair",
            "seed": 18_100_000 + ordinal,
            "source_episode_id": template["episode_id"],
            "source_split": template["split"],
            "split": "v2_stage1_enemy_path_trace_regression",
            "training_stage": "stage1_path_trace_anchor_scan_only",
            "formal_collection_authorized": False,
            "training_admitted": False,
            "map_region_id": pair["source_probe"],
            "selected_geometry": {
                "source_pair": pair["source_probe"],
                "variant": pair["variant"],
            },
            "pair_candidates": [],
        }
    )
    row["player"]["origin"] = list(pair["player_origin"])
    row["enemy"]["origin"] = list(pair["enemy_origin"])
    row["enemy_policy"]["policy_seed"] = 13_800_000 + ordinal
    review.apply_enemy_policy_geometry(row)
    return row


def run_one(
    row: dict[str, Any],
    pair: dict[str, Any],
    port: int,
) -> dict[str, Any]:
    stage = (
        capture.TMP_ROOT
        / "raw"
        / row["episode_id"]
    )
    if stage.exists():
        capture.clean_stage(stage)
    stage.mkdir(parents=True)
    result: dict[str, Any] = {
        "episode_id": row["episode_id"],
        "map": row["map"],
        "gametype": row["gametype"],
        "source_probe": pair["source_probe"],
        "variant": pair["variant"],
        "distance_bin": pair["distance_bin"],
        "player_origin": row["player"]["origin"],
        "enemy_origin": row["enemy"]["origin"],
        "motion_vector": row["enemy"]["motion_vector"],
        "passed": False,
    }
    try:
        capture.validate_scenario_assets(row)
        live = capture.run_live_attempt(
            stage,
            row,
            capture.build_root(),
            retry=0,
            port=port,
        )
        precheck = capture.validate_live_precheck(stage, row, live)
        result.update(
            {
                "passed": True,
                "checks": precheck["checks"],
                "enemy_path_trace": precheck["enemy_path_trace"],
                "action_rows": precheck["action_rows"],
                "state_rows": precheck["state_rows"],
            }
        )
    except Exception as exc:
        result["reason"] = (
            exc.reason
            if isinstance(exc, capture.CaptureFailure)
            else type(exc).__name__
        )
        result["detail"] = str(exc)
        precheck_path = stage / "LIVE_PRECHECK.json"
        if precheck_path.is_file():
            precheck = json.loads(
                precheck_path.read_text(encoding="utf-8")
            )
            result.update(
                {
                    "checks": precheck.get("checks"),
                    "enemy_path_trace": precheck.get(
                        "enemy_path_trace"
                    ),
                    "action_rows": precheck.get("action_rows"),
                    "state_rows": precheck.get("state_rows"),
                }
            )
    finally:
        if stage.exists():
            capture.clean_stage(stage)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--port-base", type=int, default=32_100)
    args = parser.parse_args()
    capture.require_conda()
    template = base_scenario()
    pairs = candidates(args.limit)
    rows = [
        scenario_for(template, pair, ordinal)
        for ordinal, pair in enumerate(pairs, 1)
    ]
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = [
            executor.submit(
                run_one,
                row,
                pair,
                args.port_base + ordinal,
            )
            for ordinal, (row, pair) in enumerate(
                zip(rows, pairs), 1
            )
        ]
        results = [
            future.result()
            for future in concurrent.futures.as_completed(futures)
        ]
    results.sort(key=lambda row: row["episode_id"])
    report = {
        "schema_version": "xonotic-stage1-approach-anchor-scan-v1",
        "created_utc": capture.utc_now(),
        "source_commit": (
            capture.build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip(),
        "workers": args.workers,
        "candidate_count": len(results),
        "passed_count": sum(row["passed"] for row in results),
        "candidates": results,
        "formal_collection_authorized": False,
        "training_admitted": False,
    }
    common.atomic_json(OUTPUT, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
