                      
"""Prepare and run an 18-cell v6 map/weapon/template qualification matrix."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V6_PATH = Path(__file__).with_name(
    "long60_production_ref42_v6_multimap_hitscan.py"
)
SPEC = importlib.util.spec_from_file_location("long60_ref42_v6_pilot_base", V6_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v6 module: {V6_PATH}")
v6 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v6
SPEC.loader.exec_module(v6)


PILOT_ID = "long60_ref42_v6_multimap_hitscan_matrix18_20260828"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / PILOT_ID
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / PILOT_ID


def choose_matrix_rows() -> list[dict[str, Any]]:
    source = v6.distribution_rows()
    selected: list[dict[str, Any]] = []
    for template in ("four_distinct", "controlled_return"):
        for map_name in sorted(v6.MAPS):
            for weapon_name in sorted(v6.WEAPONS):
                if template == "four_distinct":
                    predicate = lambda row: int(row["kill_count"]) == 2
                else:
                    predicate = lambda row: 1 in {int(value) for value in row["kill_slots"]}
                row = next(
                    row
                    for row in source
                    if row["template"] == template
                    and row["map"] == map_name
                    and row["weapon"] == weapon_name
                    and predicate(row)
                )
                selected.append(dict(row))
    return selected


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    rows = choose_matrix_rows()
    actions: dict[str, Path] = {}
    for template, segments in v6.prod.TEMPLATES.items():
        representative = next(row for row in rows if row["template"] == template)
        v6.configure_geometry_and_weapon(representative)
        path = artifact_root / "template_actions" / template / "actions.csv"
        v6.base.write_actions(
            path,
            f"{PILOT_ID}_{template}",
            int(representative["engine_seed"]),
            segments,
        )
        actions[template] = path

    for pilot_index, row in enumerate(rows):
        row["pilot_index"] = pilot_index
        scenario_path, timeline = v6.build_episode_scenario(
            row, artifact_root, actions[row["template"]]
        )
        row.update(
            {
                "scenario_path": v6.prod.relative_to_root(scenario_path),
                "scenario_sha256": v6.prod.base.sha256(scenario_path),
                "actions_path": v6.prod.relative_to_root(actions[row["template"]]),
                "actions_sha256": v6.prod.base.sha256(actions[row["template"]]),
                "timeline_path": v6.prod.relative_to_root(timeline),
                "timeline_sha256": v6.prod.base.sha256(timeline),
            }
        )
    manifest = artifact_root / "pilot_manifest.jsonl"
    v6.prod.write_jsonl_atomic(manifest, rows)
    report = {
        "schema_version": "xonotic-stage2-long60-v6-matrix-pilot-prepared-v1",
        "created_utc": v6.prod.utc_now(),
        "pilot_id": PILOT_ID,
        "episode_count": len(rows),
        "manifest": str(manifest),
        "manifest_sha256": v6.prod.base.sha256(manifest),
        "geometry_config_sha256": v6.CONFIG_SHA256,
        "template_map_weapon_cells": {
            "/".join(key): value
            for key, value in sorted(
                Counter((row["template"], row["map"], row["weapon"]) for row in rows).items()
            )
        },
        "training_admitted": False,
    }
    v6.prod.write_json_atomic(artifact_root / "PREPARED.json", report)
    print(json.dumps(report, sort_keys=True), flush=True)


def worker(
    artifact_root: Path,
    output_root: Path,
    scratch_root: Path,
    lane_id: int,
    lane_count: int,
    port: int,
    max_attempts: int,
) -> None:
    rows = v6.prod.load_jsonl(artifact_root.resolve() / "pilot_manifest.jsonl")
    selected = [row for row in rows if int(row["pilot_index"]) % lane_count == lane_id]
    build = ROOT / "build" / v6.BUILD_TAG
    if (build / "SOURCE_COMMIT").read_text(encoding="utf-8").strip() != v6.BUILD_COMMIT:
        raise RuntimeError(f"runtime build mismatch: {build}")
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lane: Any | None = None
    lane_generation = 0
    failures = []
    completed = 0
    started = time.monotonic()
    try:
        for sequence, row in enumerate(selected, 1):
            scenario_path = ROOT / row["scenario_path"]
            if v6.prod.base.sha256(scenario_path) != row["scenario_sha256"]:
                raise RuntimeError(f"scenario hash mismatch: {scenario_path}")
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            last_error = ""
            for attempt in range(1, max_attempts + 1):
                if lane is None:
                    lane_generation += 1
                    lane = v6.base.reusable.ReusableStage1Lane(
                        scratch_root / f"resident-generation-{lane_generation:03d}",
                        build=build,
                        port=port,
                    )
                try:
                    record = v6.run_attempt(
                        lane, row, scenario, output_root, scratch_root, attempt
                    )
                    completed += 1
                    print(
                        "pilot_accepted "
                        f"lane={lane_id} episode={row['episode_id']} "
                        f"template={row['template']} map={row['map']} weapon={row['weapon']} "
                        f"attempt={attempt} wall={record['wall_seconds']:.3f} "
                        f"progress={sequence}/{len(selected)}",
                        flush=True,
                    )
                    break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    print(
                        f"pilot_attempt_failed lane={lane_id} episode={row['episode_id']} "
                        f"attempt={attempt} error={last_error}",
                        file=sys.stderr,
                        flush=True,
                    )
                    traceback.print_exc()
                    lane.close()
                    lane = None
            else:
                failures.append(
                    {
                        "pilot_index": row["pilot_index"],
                        "episode_id": row["episode_id"],
                        "template": row["template"],
                        "map": row["map"],
                        "weapon": row["weapon"],
                        "error": last_error,
                    }
                )
    finally:
        if lane is not None:
            lane.close()
    summary = {
        "schema_version": "xonotic-stage2-long60-v6-matrix-pilot-lane-v1",
        "created_utc": v6.prod.utc_now(),
        "lane_id": lane_id,
        "lane_count": lane_count,
        "selected": len(selected),
        "completed": completed,
        "failures": failures,
        "wall_seconds": time.monotonic() - started,
        "raw_avi_retained": False,
    }
    v6.prod.write_json_atomic(
        output_root / "status" / "lanes" / f"lane-{lane_id:02d}.json", summary
    )
    print(json.dumps(summary, sort_keys=True), flush=True)


def report(artifact_root: Path, output_root: Path) -> None:
    rows = v6.prod.load_jsonl(artifact_root.resolve() / "pilot_manifest.jsonl")
    results = []
    for row in rows:
        paths = v6.prod.accepted_paths(output_root.resolve(), row)
        qa = json.loads(paths["qa"].read_text(encoding="utf-8")) if paths["qa"].is_file() else None
        rejections = sorted(
            (output_root / "status" / "rejected").glob(f"{row['episode_id']}.attempt*.json")
        )
        results.append(
            {
                "pilot_index": row["pilot_index"],
                "episode_id": row["episode_id"],
                "template": row["template"],
                "map": row["map"],
                "weapon": row["weapon"],
                "accepted": qa is not None and qa.get("passed") is True,
                "failed_checks": [
                    key for key, value in (qa.get("checks") or {}).items() if not value
                ]
                if qa
                else [],
                "rejection_files": [str(path) for path in rejections],
                "video_path": str(paths["video"]) if paths["video"].is_file() else None,
                "qa_path": str(paths["qa"]) if paths["qa"].is_file() else None,
            }
        )
    summary = {
        "schema_version": "xonotic-stage2-long60-v6-matrix-pilot-report-v1",
        "created_utc": v6.prod.utc_now(),
        "pilot_id": PILOT_ID,
        "accepted": sum(row["accepted"] for row in results),
        "expected": len(results),
        "all_pass": all(row["accepted"] for row in results),
        "results": results,
        "training_admitted": False,
    }
    v6.prod.write_json_atomic(output_root / "PILOT_REPORT.json", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    worker_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    worker_parser.add_argument("--scratch-root", type=Path, required=True)
    worker_parser.add_argument("--lane-id", type=int, required=True)
    worker_parser.add_argument("--lane-count", type=int, default=4)
    worker_parser.add_argument("--port", type=int, required=True)
    worker_parser.add_argument("--max-attempts", type=int, default=1)
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    report_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.artifact_root)
    elif args.command == "worker":
        worker(
            args.artifact_root,
            args.output_root.resolve(),
            args.scratch_root.resolve(),
            args.lane_id,
            args.lane_count,
            args.port,
            args.max_attempts,
        )
    else:
        report(args.artifact_root, args.output_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
