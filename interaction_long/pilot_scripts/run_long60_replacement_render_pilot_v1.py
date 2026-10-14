                      
"""Render-only 60 s qualification for the Runningman/Stormkeep replacements."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "scan_long60_runningman_stormkeep_hitscan_live_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_replacement_render_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import replacement calibration: {BASE_PATH}")
repl = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = repl
SPEC.loader.exec_module(repl)
v7 = repl.cal.v7


PILOT_ID = "long60_ref42_v7_replacement_render2_20260828_v1"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / PILOT_ID
DEFAULT_OUTPUT_ROOT = Path(
    "./rigen_data/stage2_long60_ref42_v7_replacement_render_pilot2_20260828"
)


def choose_rows() -> list[dict[str, Any]]:
    requested = (
        ("runningman", "four_distinct", "Shotgun", None),
        ("stormkeep", "four_distinct", "Vortex", [534, 1527, 2602, 3517]),
    )
    rows = []
    for index, (map_name, template, weapon, pulse_ticks) in enumerate(requested):
        row = next(
            dict(item)
            for item in repl.SOURCE_ROWS
            if item["template"] == template
            and item["weapon"] == weapon
            and int(item["kill_count"]) == 2
        )
        config = repl.REPLACEMENTS[map_name]
        row.update(
            {
                "manifest_index": index,
                "pilot_index": index,
                "episode_id": f"l60v7_replacement_render_{map_name}_{weapon.lower()}",
                "split": "test",
                "map": map_name,
                "gametype": "dm",
                "anchor_id": config["anchor_id"],
                "trajectory_scale": config["trajectory_scale"],
                "training_admitted": False,
            }
        )
        if pulse_ticks is not None:
            row["semiautomatic_primary_server_ticks"] = pulse_ticks
        rows.append(row)
    return rows


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    rows = choose_rows()
    for row in rows:
        actions = (
            artifact_root
            / "actions"
            / str(row["map"])
            / str(row["weapon"])
            / "actions.csv"
        )
        v7.write_actions(actions, row)
        scenario_path, timeline = v7.build_episode_scenario(row, artifact_root, actions)
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["formal_collection_authorized"] = False
        scenario["training_admitted"] = False
        scenario["render_qualification"] = {
            "pilot_id": PILOT_ID,
            "render_only": True,
        }
        v7.prod.write_json_atomic(scenario_path, scenario)
        row.update(
            {
                "scenario_path": v7.prod.relative_to_root(scenario_path),
                "scenario_sha256": v7.base.sha256(scenario_path),
                "actions_path": v7.prod.relative_to_root(actions),
                "actions_sha256": v7.base.sha256(actions),
                "timeline_path": v7.prod.relative_to_root(timeline),
                "timeline_sha256": v7.base.sha256(timeline),
            }
        )
    manifest = artifact_root / "pilot_manifest.jsonl"
    v7.prod.write_jsonl_atomic(manifest, rows)
    v7.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-v7-replacement-render-prepared-v1",
            "pilot_id": PILOT_ID,
            "episode_count": len(rows),
            "manifest_sha256": v7.base.sha256(manifest),
            "raw_avi_retained": False,
            "training_admitted": False,
        },
    )


def run(
    artifact_root: Path,
    output_root: Path,
    scratch_root: Path,
    port: int,
    max_attempts: int,
    map_only: str | None,
) -> None:
    rows = v7.prod.load_jsonl(artifact_root.resolve() / "pilot_manifest.jsonl")
    if map_only is not None:
        rows = [row for row in rows if row["map"] == map_only]
        if not rows:
            raise RuntimeError(f"no pilot row for map: {map_only}")
    build = ROOT / "build" / v7.BUILD_TAG
    lane: Any | None = None
    current_map = None
    generation = 0
    results = []
    try:
        for row in rows:
            scenario_path = ROOT / row["scenario_path"]
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            if lane is not None and current_map != row["map"]:
                lane.close()
                lane = None
            for attempt in range(1, max_attempts + 1):
                if lane is None:
                    generation += 1
                    lane = v7.base.reusable.ReusableStage1Lane(
                        scratch_root
                        / f"resident-{row['map']}-{generation:03d}",
                        build=build,
                        port=port,
                    )
                    current_map = row["map"]
                try:
                    record = v7.run_attempt(
                        lane, row, scenario, output_root, scratch_root, attempt
                    )
                    results.append(
                        {
                            "episode_id": row["episode_id"],
                            "map": row["map"],
                            "weapon": row["weapon"],
                            "accepted": True,
                            "attempt": attempt,
                            "wall_seconds": record["wall_seconds"],
                            "video_path": str(
                                v7.prod.accepted_paths(output_root, row)["video"]
                            ),
                        }
                    )
                    break
                except Exception as exc:
                    traceback.print_exc()
                    if lane is not None:
                        lane.close()
                    lane = None
                    current_map = None
                    if attempt == max_attempts:
                        results.append(
                            {
                                "episode_id": row["episode_id"],
                                "map": row["map"],
                                "weapon": row["weapon"],
                                "accepted": False,
                                "attempt": attempt,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
    finally:
        if lane is not None:
            lane.close()
    report = {
        "schema_version": "xonotic-long60-v7-replacement-render-report-v1",
        "pilot_id": PILOT_ID,
        "expected": len(rows),
        "accepted": sum(item["accepted"] for item in results),
        "all_pass": all(item["accepted"] for item in results),
        "results": results,
        "raw_avi_retained": False,
        "training_admitted": False,
    }
    v7.prod.write_json_atomic(output_root / "PILOT_REPORT.json", report)
    print(json.dumps(report, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    run_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run_parser.add_argument("--scratch-root", type=Path, required=True)
    run_parser.add_argument("--port", type=int, default=39800)
    run_parser.add_argument("--max-attempts", type=int, default=2)
    run_parser.add_argument("--map-only", choices=("runningman", "stormkeep"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.artifact_root)
    else:
        run(
            args.artifact_root,
            args.output_root.resolve(),
            args.scratch_root.resolve(),
            args.port,
            args.max_attempts,
            args.map_only,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
