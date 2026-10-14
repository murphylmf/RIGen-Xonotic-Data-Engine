                      
"""Find collision-clean long60 angle/scale geometry with live-only probes."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
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

OPEN_PLAYER_ORIGINS = {
                                                                            
                                                                            
                                                                            
                                                                            
                                                                          
                    
    "bromine": [-40.5, 398.3, 156.4],
    "courtfun": [-2038.1, 4295.2, 88.0],
    "geoplanetary": [608.4, 1429.2, -104.0],
    "stormkeep": [-400.0, 528.0, -8.0],
}


def load_v7() -> Any:
    spec = importlib.util.spec_from_file_location("long60_collision_scan_v7", V7_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {V7_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def candidate_map_config(
    source: dict[str, Any],
    angle_degrees: float,
    scale: float,
    anchor_candidate_id: str | None = None,
) -> dict[str, Any]:
    player = [float(value) for value in source["player_origin"]]
    angle = math.radians(angle_degrees)
    return {
        **source,
        "anchor_id": (
            f"{anchor_candidate_id or source['anchor_id'].split('_')[0]}_collision_scan_"
            f"a{round(angle_degrees):03d}_scale{round(scale * 100):03d}"
        ),
        "trajectory_scale": scale,
        "enemy_reference_origin": [
            player[0] + 200.0 * math.cos(angle),
            player[1] + 200.0 * math.sin(angle),
            player[2],
        ],
    }


def configure(v7: Any, row: dict[str, Any]) -> None:
    source = dict(
        row.get("map_config") or v7.CONFIG["maps"][str(row["map"])]
    )
    if "player_origin" in row:
        source["player_origin"] = [
            float(value) for value in row["player_origin"]
        ]
    v7.MAPS[str(row["map"])] = candidate_map_config(
        source,
        float(row["angle_degrees"]),
        float(row["trajectory_scale"]),
        str(row["anchor_candidate_id"])
        if row.get("anchor_candidate_id")
        else None,
    )
    v7.configure_geometry_and_weapon(row)


def prepare(
    v7: Any,
    root: Path,
    source_manifest: Path,
    scales: list[float],
    angles: list[int],
    anchor_set: str,
    anchor_file: Path | None,
    map_config_file: Path | None,
    map_names: list[str] | None,
    template_names: list[str] | None,
) -> None:
    if root.exists():
        raise FileExistsError(root)
    root.mkdir(parents=True)
    source_rows = jsonl(source_manifest)
    representatives = {
        template: next(
            dict(row)
            for row in source_rows
            if row["template"] == template
            and row["weapon"] == "MachineGun"
            and int(row["kill_count"]) == 0
        )
        for template in sorted(v7.ORIGINAL_TEMPLATES)
        if template_names is None or template in template_names
    }
    available_map_configs = {
        name: dict(config) for name, config in v7.CONFIG["maps"].items()
    }
    if map_config_file is not None:
        raw_map_configs = json.loads(map_config_file.read_text())
        if not isinstance(raw_map_configs, dict):
            raise ValueError("map config file must be a map-to-config JSON object")
        available_map_configs.update(
            {str(name): dict(config) for name, config in raw_map_configs.items()}
        )
    selected_maps = [
        name
        for name in sorted(available_map_configs)
        if map_names is None or name in map_names
    ]
    if not representatives or not selected_maps:
        raise ValueError("map/template filters selected no scan cells")
    explicit_anchors: dict[str, list[dict[str, Any]]] = {}
    if anchor_file is not None:
        raw_anchors = json.loads(anchor_file.read_text())
        if not isinstance(raw_anchors, dict):
            raise ValueError("anchor file must be a map-to-anchor-list JSON object")
        for map_name, entries in raw_anchors.items():
            if not isinstance(entries, list) or not entries:
                raise ValueError(f"anchor file has no entries for {map_name}")
            explicit_anchors[str(map_name)] = [dict(entry) for entry in entries]

    rows: list[dict[str, Any]] = []
    for map_name in selected_maps:
        source_map_config = available_map_configs[map_name]
        for template in sorted(representatives):
            if map_name in explicit_anchors:
                anchors = explicit_anchors[map_name]
            else:
                anchors = [
                    {
                        "id": anchor_set,
                        "origin": (
                            OPEN_PLAYER_ORIGINS[map_name]
                            if anchor_set == "open_v2"
                            else source_map_config["player_origin"]
                        ),
                    }
                ]
            for anchor in anchors:
                anchor_candidate_id = str(anchor["id"])
                player_origin = [float(value) for value in anchor["origin"]]
                for scale in scales:
                    for angle in angles:
                        row = dict(representatives[template])
                        index = len(rows)
                        row.update(
                            {
                            "scan_index": index,
                            "manifest_index": index,
                            "episode_id": (
                                f"l60colv8_{map_name}_{anchor_candidate_id}_{template}_"
                                f"s{round(scale * 100):03d}_a{angle:03d}"
                            ),
                            "map": map_name,
                            "gametype": source_map_config["gametype"],
                            "weapon": "MachineGun",
                            "weapon_netname": "machinegun",
                            "kill_count": 0,
                            "kill_slots": [],
                            "trajectory_scale": scale,
                            "angle_degrees": angle,
                            "player_origin": player_origin,
                            "anchor_candidate_id": anchor_candidate_id,
                            "map_config": source_map_config,
                        }
                    )
                        configure(v7, row)
                        row["anchor_id"] = v7.MAPS[map_name]["anchor_id"]
                        actions = root / "actions" / row["episode_id"] / "actions.csv"
                        v7.write_actions(actions, row)
                        scenario_path, timeline = v7.build_episode_scenario(
                            row, root, actions
                        )
                        scenario = json.loads(scenario_path.read_text())
                        scenario["training_admitted"] = False
                        scenario["collision_geometry_probe"] = {
                            "angle_degrees": angle,
                            "trajectory_scale": scale,
                            "anchor_candidate_id": anchor_candidate_id,
                            "live_only": True,
                        }
                        v7.prod.write_json_atomic(scenario_path, scenario)
                        row.update(
                            {
                                "scenario_path": v7.prod.relative_to_root(scenario_path),
                                "timeline_path": v7.prod.relative_to_root(timeline),
                                "actions_path": v7.prod.relative_to_root(actions),
                            }
                        )
                        rows.append(row)
    v7.prod.write_jsonl_atomic(root / "scan_manifest.jsonl", rows)
    v7.prod.write_json_atomic(
        root / "PREPARED.json",
        {
            "case_count": len(rows),
            "angles": angles,
            "scales": scales,
            "maps": selected_maps,
            "templates": sorted(representatives),
            "anchor_set": anchor_set,
            "anchor_file": str(anchor_file) if anchor_file is not None else None,
            "map_config_file": (
                str(map_config_file) if map_config_file is not None else None
            ),
            "live_only": True,
            "training_admitted": False,
        },
    )
    print(json.dumps({"prepared": len(rows), "root": str(root)}))


def worker(
    v7: Any,
    root: Path,
    output: Path,
    scratch: Path,
    build: Path,
    lane_id: int,
    lane_count: int,
    port: int,
) -> None:
    selected = [
        row
        for row in jsonl(root / "scan_manifest.jsonl")
        if int(row["scan_index"]) % lane_count == lane_id
    ]
    selected.sort(key=lambda row: (str(row["map"]), int(row["scan_index"])))
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    lane = None
    active_map = None
    generation = 0
    try:
        for sequence, row in enumerate(selected, 1):
            result_path = output / "results" / f"{row['episode_id']}.json"
            if result_path.is_file():
                continue
            configure(v7, row)
            if lane is not None and active_map != row["map"]:
                lane.close()
                lane = None
            if lane is None:
                generation += 1
                lane = v7.base.reusable.ReusableStage1Lane(
                    scratch / f"generation-{generation:02d}",
                    build=build,
                    port=port,
                )
                active_map = row["map"]
            scenario = json.loads((ROOT / row["scenario_path"]).read_text())
            stage = scratch / "episodes" / row["episode_id"]
            live = lane.run_live(stage, scenario, retry=0)
            telemetry = jsonl(Path(live["server_telemetry"]))
            fatals = [item for item in telemetry if item.get("kind") == "fatal"]
            states = [item for item in telemetry if item.get("kind") == "state"]
            reset = next((item for item in telemetry if item.get("kind") == "reset"), {})
            result = {
                "episode_id": row["episode_id"],
                "map": row["map"],
                "template": row["template"],
                "angle_degrees": row["angle_degrees"],
                "trajectory_scale": row["trajectory_scale"],
                "passed": not fatals
                and len(states) == v7.base.capture.TOTAL_TICKS,
                "state_count": len(states),
                "fatal": fatals[-1] if fatals else None,
                "anchor": reset.get("anchor"),
                "live_wall_seconds": live["live_wall_seconds"],
            }
            v7.prod.write_json_atomic(result_path, result)
            print(
                json.dumps(
                    {
                        "lane": lane_id,
                        "progress": f"{sequence}/{len(selected)}",
                        **result,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    finally:
        if lane is not None:
            lane.close()


def report(v7: Any, root: Path, output: Path) -> None:
    expected = jsonl(root / "scan_manifest.jsonl")
    results = []
    for path in sorted((output / "results").glob("*.json")):
        results.append(json.loads(path.read_text()))
    passed = [item for item in results if item["passed"]]
    summary = {
        "expected": len(expected),
        "completed": len(results),
        "passed": len(passed),
        "passing_geometry": passed,
    }
    v7.prod.write_json_atomic(output / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--source-manifest", required=True, type=Path)
    p.add_argument("--scales", default="0.45")
    p.add_argument("--angles", default="0,45,90,135,180,225,270,315")
    p.add_argument(
        "--anchor-set", choices=("default", "open_v2"), default="default"
    )
    p.add_argument(
        "--anchor-file",
        type=Path,
        help="optional JSON map-to-anchor-list override for scanning many origins",
    )
    p.add_argument(
        "--map-config-file",
        type=Path,
        help="optional JSON map-to-config additions for replacement candidates",
    )
    p.add_argument(
        "--maps",
        help="comma-separated map subset; default scans every configured map",
    )
    p.add_argument(
        "--templates",
        help="comma-separated template subset; default scans every template",
    )
    w = sub.add_parser("worker")
    w.add_argument("--root", required=True, type=Path)
    w.add_argument("--output", required=True, type=Path)
    w.add_argument("--scratch", required=True, type=Path)
    w.add_argument("--build", required=True, type=Path)
    w.add_argument("--lane-id", required=True, type=int)
    w.add_argument("--lane-count", required=True, type=int)
    w.add_argument("--port", required=True, type=int)
    r = sub.add_parser("report")
    r.add_argument("--root", required=True, type=Path)
    r.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    v7 = load_v7()
    if args.command == "prepare":
        prepare(
            v7,
            args.root.resolve(),
            args.source_manifest.resolve(strict=True),
            [float(value) for value in args.scales.split(",")],
            [int(value) for value in args.angles.split(",")],
            args.anchor_set,
            args.anchor_file.resolve(strict=True) if args.anchor_file else None,
            args.map_config_file.resolve(strict=True)
            if args.map_config_file
            else None,
            args.maps.split(",") if args.maps else None,
            args.templates.split(",") if args.templates else None,
        )
    elif args.command == "worker":
        worker(
            v7,
            args.root.resolve(strict=True),
            args.output.resolve(),
            args.scratch.resolve(),
            args.build.resolve(strict=True),
            args.lane_id,
            args.lane_count,
            args.port,
        )
    else:
        report(v7, args.root.resolve(strict=True), args.output.resolve())


if __name__ == "__main__":
    main()
