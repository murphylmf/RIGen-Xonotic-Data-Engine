                      
"""Run live-only long60 probes and report world-collision fatals."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V7_PATH = Path(__file__).with_name(
    "long60_production_ref42_v7_multimap_hitscan.py"
)
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_CAPTURE_CLIENT_OVERLAY",
    "configs/capture_client_stage2_v14_no_crosshair.cfg",
)
os.environ.setdefault("XONOTIC_LIVE_TIME_SCALE", "2")
os.environ.setdefault("XONOTIC_LIVE_TIMEOUT_SECONDS", "240")
os.environ.setdefault("XONOTIC_ENGINE_NET_TIMEOUT_SECONDS", "660")
os.environ.setdefault("XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "120")


def load_v7() -> Any:
    spec = importlib.util.spec_from_file_location("long60_collision_probe_v7", V7_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {V7_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--port", type=int, default=40940)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    manifest_root = args.manifest_root.resolve(strict=True)
    build = args.build.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to reuse output: {output}")
    output.mkdir(parents=True)

    v7 = load_v7()
    rows = v7.prod.load_jsonl(manifest_root / "manifest.jsonl")
    selected = []
    for map_name in sorted(v7.MAPS):
        for template in sorted(v7.ORIGINAL_TEMPLATES):
            selected.append(
                next(
                    row
                    for row in rows
                    if row["map"] == map_name
                    and row["template"] == template
                    and row["weapon"] == "MachineGun"
                )
            )
    if args.limit is not None:
        selected = selected[: args.limit]

    reports: list[dict[str, Any]] = []
    lane = None
    active_map = None
    generation = 0
    try:
        for index, row in enumerate(selected):
            if lane is not None and row["map"] != active_map:
                lane.close()
                lane = None
            if lane is None:
                generation += 1
                lane = v7.base.reusable.ReusableStage1Lane(
                    output / f"lane-{generation:02d}",
                    build=build,
                    port=args.port + generation,
                )
                active_map = row["map"]
            v7.configure_geometry_and_weapon(row)
            scenario_path = ROOT / row["scenario_path"]
            scenario = json.loads(scenario_path.read_text())
            stage = output / "episodes" / row["episode_id"]
            error = None
            live = None
            try:
                live = lane.run_live(stage, scenario, retry=0)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                lane.snapshot_failure_logs(stage)
            telemetry_paths = (
                [Path(live["server_telemetry"])]
                if live is not None
                else sorted(lane.lane_root.rglob("server.jsonl"))
            )
            telemetry = load_jsonl(telemetry_paths[-1]) if telemetry_paths else []
            fatals = [item for item in telemetry if item.get("kind") == "fatal"]
            report = {
                "episode_id": row["episode_id"],
                "map": row["map"],
                "template": row["template"],
                "error": error,
                "fatal": fatals[-1] if fatals else None,
                "state_count": sum(item.get("kind") == "state" for item in telemetry),
                "completed": live is not None and not fatals,
            }
            reports.append(report)
            print(json.dumps(report, sort_keys=True), flush=True)
            if error is not None:
                lane.close()
                lane = None
                active_map = None
    finally:
        if lane is not None:
            lane.close()

    summary = {
        "probe_count": len(reports),
        "passed": sum(item["completed"] for item in reports),
        "failed": sum(not item["completed"] for item in reports),
        "reports": reports,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
