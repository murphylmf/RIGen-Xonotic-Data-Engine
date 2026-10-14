                      
"""Live-certify radial and lateral hull envelopes for every Stage-1 pair."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_manifests as manifests              
import run_capture_manifest_shard as common              
import xonotic_capture as capture              
import xonotic_stage1_enemy_policy_audio_preflight_v2 as audio_v2              
import xonotic_stage1_review as review              


OUTPUT_ROOT = capture.ROOT / "stage1_enemy_path_preflight"
RESULT_ROOT = OUTPUT_ROOT / "results"
REPORT_PATH = (
    capture.ROOT
    / "manifests/stage1_foundation_v1"
    / "ENEMY_PATH_PREFLIGHT.json"
)
AXES = {
    "radial": "approach_retreat",
                                                                            
                                                              
    "lateral": "lateral_patrol",
}


def templates() -> dict[str, dict[str, Any]]:
    audio_v2.configure_version()
    rows = audio_v2.implementation.scenario_rows()
    return {
        axis: copy.deepcopy(
            next(
                row
                for row in rows
                if row["enemy_policy"]["name"] == policy
                and row["audio_review_context"] == "visible_close"
            )
        )
        for axis, policy in AXES.items()
    }


def all_pairs() -> list[dict[str, Any]]:
    _, pools = manifests.preflight_pools()
    return sorted(
        (
            copy.deepcopy(pair)
            for distance_pairs in pools.values()
            for pair in distance_pairs
        ),
        key=lambda row: (
            row["distance_bin"],
            row["map"],
            row["source_probe"],
            row["variant"],
        ),
    )


def pair_key(pair: dict[str, Any]) -> str:
    return f"{pair['source_probe']}::{pair['variant']}"


def result_path(axis: str, pair: dict[str, Any]) -> Path:
    digest = hashlib.sha256(pair_key(pair).encode()).hexdigest()[:16]
    return RESULT_ROOT / axis / f"{digest}.json"


def scenario_for(
    template: dict[str, Any],
    pair: dict[str, Any],
    axis: str,
    ordinal: int,
) -> dict[str, Any]:
    row = copy.deepcopy(template)
    episode_id = f"s1pathpf_{axis}_{ordinal:03d}"
    row.update(
        {
            "episode_id": episode_id,
            "map": pair["map"],
            "gametype": pair["gametype"],
            "anchor_id": f"{pair['map']}_{episode_id}_pair",
            "seed": 12_500_000 + ordinal,
            "source_episode_id": template["episode_id"],
            "source_split": template["split"],
            "split": "v2_stage1_enemy_path_trace_regression",
            "training_stage": "stage1_enemy_path_preflight_only",
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
    row["enemy_policy"]["policy_seed"] = (
        13_000_000 + ordinal
    )
    row["enemy_policy"]["motion_start_tick"] = 0
    review.apply_enemy_policy_geometry(row)
    return row


def load_precheck(stage: Path) -> dict[str, Any] | None:
    path = stage / "LIVE_PRECHECK.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_one(
    row: dict[str, Any],
    pair: dict[str, Any],
    axis: str,
    port: int,
    max_attempts: int,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        stage = capture.TMP_ROOT / "raw" / row["episode_id"]
        if stage.exists():
            capture.clean_stage(stage)
        stage.mkdir(parents=True)
        precheck: dict[str, Any] | None = None
        try:
            capture.validate_scenario_assets(row)
            live = capture.run_live_attempt(
                stage,
                row,
                capture.build_root(),
                retry=attempt,
                port=port,
            )
            try:
                precheck = capture.validate_live_precheck(
                    stage, row, live
                )
            except capture.CaptureFailure:
                precheck = load_precheck(stage)
            trace = (precheck or {}).get("enemy_path_trace") or {}
            checks = (precheck or {}).get("checks") or {}
            path_certified = (
                trace.get("passed") is True
                and checks.get("enemy_hull_clear") is True
                and checks.get("enemy_grounded") is True
                and checks.get("enemy_presence_matches") is True
                and checks.get("enemy_policy_motion_contract") is True
                and int((precheck or {}).get("state_rows", -1))
                == capture.TOTAL_TICKS
            )
            result = {
                "schema_version": (
                    "xonotic-stage1-enemy-path-pair-result-v1"
                ),
                "created_utc": capture.utc_now(),
                "source_commit": (
                    capture.build_root() / "SOURCE_COMMIT"
                ).read_text(encoding="utf-8").strip(),
                "axis": axis,
                "certifies_policies": (
                    ["approach_retreat"]
                    if axis == "radial"
                    else ["lateral_patrol", "stop_and_go"]
                ),
                "pair_key": pair_key(pair),
                "pair": pair,
                "episode_id": row["episode_id"],
                "motion_vector": row["enemy"]["motion_vector"],
                "motion_amplitude_units": row["enemy"][
                    "motion_distance"
                ],
                "path_certified": path_certified,
                "enemy_path_trace": trace,
                "checks": checks,
                "state_rows": (precheck or {}).get("state_rows"),
                "action_rows": (precheck or {}).get("action_rows"),
                "attempts": attempt + 1,
                "formal_collection_authorized": False,
                "training_admitted": False,
            }
            capture.clean_stage(stage)
            return result
        except Exception as exc:
            last_error = exc
            if stage.exists():
                capture.clean_stage(stage)
            if not common.retryable_failure(exc):
                break
    return {
        "schema_version": "xonotic-stage1-enemy-path-pair-result-v1",
        "created_utc": capture.utc_now(),
        "source_commit": (
            capture.build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip(),
        "axis": axis,
        "certifies_policies": (
            ["approach_retreat"]
            if axis == "radial"
            else ["lateral_patrol", "stop_and_go"]
        ),
        "pair_key": pair_key(pair),
        "pair": pair,
        "episode_id": row["episode_id"],
        "motion_vector": row["enemy"]["motion_vector"],
        "motion_amplitude_units": row["enemy"]["motion_distance"],
        "path_certified": False,
        "operational_failure": True,
        "reason": (
            last_error.reason
            if isinstance(last_error, capture.CaptureFailure)
            else type(last_error).__name__
        ),
        "detail": str(last_error),
        "attempts": max_attempts,
        "formal_collection_authorized": False,
        "training_admitted": False,
    }


def valid_existing(
    path: Path,
    axis: str,
    pair: dict[str, Any],
    source_commit: str,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    row = json.loads(path.read_text(encoding="utf-8"))
    if (
        row.get("axis") == axis
        and row.get("pair_key") == pair_key(pair)
        and row.get("source_commit") == source_commit
        and not row.get("operational_failure")
    ):
        return row
    return None


def summarize(
    results: list[dict[str, Any]],
    expected: int,
    source_commit: str,
    workers: int,
) -> dict[str, Any]:
    coverage: dict[str, Counter[str]] = defaultdict(Counter)
    maps: dict[str, set[str]] = defaultdict(set)
    for row in results:
        if row.get("path_certified"):
            coverage[row["axis"]][row["pair"]["distance_bin"]] += 1
            maps[row["axis"]].add(row["pair"]["map"])
    required_bins = set(manifests.DISTANCE_COUNTS)
    checks = {
        "complete": len(results) == expected,
        "unique_axis_pair": len(
            {(row["axis"], row["pair_key"]) for row in results}
        )
        == expected,
        "no_operational_failures": not any(
            row.get("operational_failure") for row in results
        ),
        "radial_all_distance_bins": set(coverage["radial"])
        == required_bins,
        "lateral_all_distance_bins": set(coverage["lateral"])
        == required_bins,
    }
    return {
        "schema_version": "xonotic-stage1-enemy-path-preflight-v1",
        "created_utc": capture.utc_now(),
        "source_commit": source_commit,
        "workers": workers,
        "expected_results": expected,
        "result_count": len(results),
        "certified_count": sum(
            row.get("path_certified") is True for row in results
        ),
        "certified_by_axis_distance": {
            axis: dict(sorted(counts.items()))
            for axis, counts in sorted(coverage.items())
        },
        "certified_map_count_by_axis": {
            axis: len(names)
            for axis, names in sorted(maps.items())
        },
        "checks": checks,
        "passed": all(checks.values()),
        "results": results,
        "formal_collection_authorized": False,
        "training_admitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--port-base", type=int, default=33_000)
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()
    capture.require_conda()
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    template_by_axis = templates()
    pairs = all_pairs()
    work: list[
        tuple[str, dict[str, Any], dict[str, Any], Path, int]
    ] = []
    completed: list[dict[str, Any]] = []
    ordinal = 0
    for axis in AXES:
        for pair in pairs:
            ordinal += 1
            path = result_path(axis, pair)
            existing = valid_existing(
                path, axis, pair, source_commit
            )
            if existing is not None:
                completed.append(existing)
                continue
            row = scenario_for(
                template_by_axis[axis], pair, axis, ordinal
            )
            work.append((axis, pair, row, path, ordinal))
    print(
        f"enemy_path_preflight existing={len(completed)} "
        f"pending={len(work)} workers={args.workers}",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(
                run_one,
                row,
                pair,
                axis,
                args.port_base + ordinal,
                args.max_attempts,
            ): (axis, pair, path)
            for axis, pair, row, path, ordinal in work
        }
        for index, future in enumerate(
            concurrent.futures.as_completed(futures), 1
        ):
            axis, pair, path = futures[future]
            result = future.result()
            common.atomic_json(path, result)
            completed.append(result)
            print(
                f"progress {len(completed)}/{len(AXES) * len(pairs)} "
                f"axis={axis} pair={pair_key(pair)} "
                f"certified={result['path_certified']}",
                flush=True,
            )
    completed.sort(
        key=lambda row: (row["axis"], row["pair_key"])
    )
    report = summarize(
        completed,
        len(AXES) * len(pairs),
        source_commit,
        args.workers,
    )
    if REPORT_PATH.is_file():
        existing_report = json.loads(
            REPORT_PATH.read_text(encoding="utf-8")
        )
        if existing_report.get("passed") is True:
            report["created_utc"] = existing_report["created_utc"]
            report["workers"] = existing_report["workers"]
            if capture.canonical_json(report) != capture.canonical_json(
                existing_report
            ):
                raise capture.CaptureFailure(
                    "refuse_overwrite_enemy_path_preflight_drift",
                    str(REPORT_PATH),
                )
        else:
            common.atomic_json(REPORT_PATH, report)
    else:
        common.atomic_json(REPORT_PATH, report)
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key != "results"
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
