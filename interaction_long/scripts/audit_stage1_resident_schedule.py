                      
"""Project formal Stage-1 shard makespan from the exact resident scheduler."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_stage1_manifest_shard as stage1              
import xonotic_capture as capture              


def unsplit_lane_plans(
    rows: list[dict[str, Any]], workers: int
) -> list[list[tuple[tuple[str, str], list[dict[str, Any]]]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["map"]), str(row["gametype"]).lower())
        grouped.setdefault(key, []).append(row)
    groups = [
        (
            key,
            sorted(
                values,
                key=lambda row: (
                    int(row.get("candidate_ordinal", 0)),
                    str(row["episode_id"]),
                ),
            ),
        )
        for key, values in grouped.items()
    ]
    groups.sort(
        key=lambda item: (
            -len(item[1]),
            item[0],
            int(item[1][0].get("candidate_ordinal", 0)),
            str(item[1][0]["episode_id"]),
        )
    )
    plans: list[
        list[tuple[tuple[str, str], list[dict[str, Any]]]]
    ] = [[] for _ in range(workers)]
    loads = [0] * workers
    for group in groups:
        lane_index = min(
            range(workers), key=lambda index: (loads[index], index)
        )
        plans[lane_index].append(group)
        loads[lane_index] += len(group[1])
    return plans


def plan_metrics(
    plans: list[
        list[tuple[tuple[str, str], list[dict[str, Any]]]]
    ],
    *,
    warmup_seconds: float,
    steady_lane_episode_seconds: float,
) -> dict[str, Any]:
    lanes = []
    for lane_index, groups in enumerate(plans):
        rows = sum(len(group_rows) for _, group_rows in groups)
        group_count = len(groups)
        wall_seconds = (
            rows * steady_lane_episode_seconds
            + group_count * warmup_seconds
        )
        lanes.append(
            {
                "lane_index": lane_index,
                "rows": rows,
                "world_group_chunks": group_count,
                "projected_wall_seconds": wall_seconds,
            }
        )
    critical = max(row["projected_wall_seconds"] for row in lanes)
    return {
        "lanes": lanes,
        "lane_row_min": min(row["rows"] for row in lanes),
        "lane_row_max": max(row["rows"] for row in lanes),
        "world_group_chunks": sum(
            row["world_group_chunks"] for row in lanes
        ),
        "critical_wall_seconds": critical,
    }


def scenario_report(
    shard_rows: list[tuple[Path, list[dict[str, Any]]]],
    *,
    workers: int,
    steady_episodes_per_hour: float,
    warmup_seconds: float,
) -> dict[str, Any]:
    steady_lane_episode_seconds = (
        workers * 3600.0 / steady_episodes_per_hour
    )
    shards = []
    for path, rows in shard_rows:
        split = plan_metrics(
            stage1.resident_lane_plans(rows, workers),
            warmup_seconds=warmup_seconds,
            steady_lane_episode_seconds=steady_lane_episode_seconds,
        )
        unsplit = plan_metrics(
            unsplit_lane_plans(rows, workers),
            warmup_seconds=warmup_seconds,
            steady_lane_episode_seconds=steady_lane_episode_seconds,
        )
        split["projected_rank_episodes_per_hour"] = (
            len(rows) * 3600.0 / split["critical_wall_seconds"]
        )
        unsplit["projected_rank_episodes_per_hour"] = (
            len(rows) * 3600.0 / unsplit["critical_wall_seconds"]
        )
        shards.append(
            {
                "path": str(path),
                "rows": len(rows),
                "split_oversized_groups": split,
                "unsplit_world_groups": unsplit,
            }
        )
    total_rows = sum(row["rows"] for row in shards)
    split_fleet_wall = max(
        row["split_oversized_groups"]["critical_wall_seconds"]
        for row in shards
    )
    unsplit_fleet_wall = max(
        row["unsplit_world_groups"]["critical_wall_seconds"]
        for row in shards
    )
    split_rank_rates = [
        row["split_oversized_groups"][
            "projected_rank_episodes_per_hour"
        ]
        for row in shards
    ]
    return {
        "warmup_seconds_per_process_generation": warmup_seconds,
        "steady_episodes_per_hour": steady_episodes_per_hour,
        "steady_lane_episode_seconds": steady_lane_episode_seconds,
        "split_oversized_groups": {
            "projected_fleet_wall_hours": split_fleet_wall / 3600.0,
            "projected_fleet_episodes_per_hour": (
                total_rows * 3600.0 / split_fleet_wall
            ),
            "projected_rank_episodes_per_hour_min": min(
                split_rank_rates
            ),
            "projected_rank_episodes_per_hour_mean": statistics.mean(
                split_rank_rates
            ),
            "projected_rank_episodes_per_hour_max": max(
                split_rank_rates
            ),
            "lane_row_min": min(
                lane["rows"]
                for row in shards
                for lane in row["split_oversized_groups"]["lanes"]
            ),
            "lane_row_max": max(
                lane["rows"]
                for row in shards
                for lane in row["split_oversized_groups"]["lanes"]
            ),
            "world_group_chunks_per_rank_min": min(
                row["split_oversized_groups"]["world_group_chunks"]
                for row in shards
            ),
            "world_group_chunks_per_rank_max": max(
                row["split_oversized_groups"]["world_group_chunks"]
                for row in shards
            ),
        },
        "unsplit_world_groups": {
            "projected_fleet_wall_hours": unsplit_fleet_wall / 3600.0,
            "projected_fleet_episodes_per_hour": (
                total_rows * 3600.0 / unsplit_fleet_wall
            ),
            "lane_row_min": min(
                lane["rows"]
                for row in shards
                for lane in row["unsplit_world_groups"]["lanes"]
            ),
            "lane_row_max": max(
                lane["rows"]
                for row in shards
                for lane in row["unsplit_world_groups"]["lanes"]
            ),
            "world_groups_per_rank_min": min(
                row["unsplit_world_groups"]["world_group_chunks"]
                for row in shards
            ),
            "world_groups_per_rank_max": max(
                row["unsplit_world_groups"]["world_group_chunks"]
                for row in shards
            ),
        },
        "shards": shards,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", required=True)
    parser.add_argument(
        "--candidate-wave",
        choices=("primary", "replenishment"),
        default="primary",
    )
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument(
        "--steady-episodes-per-hour", type=float, required=True
    )
    parser.add_argument(
        "--warmup-seconds",
        type=float,
        action="append",
        required=True,
        help="Repeat for measured and conservative scenarios.",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    capture.require_conda()
    manifest_root = Path(args.manifest_root).resolve()
    paths = sorted(
        (manifest_root / "shards" / args.candidate_wave).glob(
            "shard-*-of-*.jsonl"
        )
    )
    if not paths:
        raise SystemExit("no shard manifests found")
    shard_rows = [(path, capture.load_jsonl(path)) for path in paths]
    report = {
        "schema_version": "xonotic-stage1-resident-schedule-audit-v1",
        "manifest_root": str(manifest_root),
        "candidate_wave": args.candidate_wave,
        "shard_count": len(shard_rows),
        "rows": sum(len(rows) for _, rows in shard_rows),
        "workers_per_rank": args.workers,
        "source_commit": stage1.EXPECTED_SOURCE_COMMIT,
        "scenarios": [
            scenario_report(
                shard_rows,
                workers=args.workers,
                steady_episodes_per_hour=args.steady_episodes_per_hour,
                warmup_seconds=warmup_seconds,
            )
            for warmup_seconds in args.warmup_seconds
        ],
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
