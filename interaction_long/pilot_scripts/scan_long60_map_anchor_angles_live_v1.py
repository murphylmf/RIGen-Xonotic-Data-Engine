                      
"""CPU/live-only scan for open long60 map anchors and view directions."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V6_PATH = Path(__file__).with_name("long60_production_ref42_v6_multimap_hitscan.py")
SPEC = importlib.util.spec_from_file_location("long60_anchor_angle_scan_v1_base", V6_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v6 module: {V6_PATH}")
v6 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v6
SPEC.loader.exec_module(v6)


SCAN_ID = "long60_map_anchor_angle_live_scan_v1_20260828"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID
ORIGINAL_TEMPLATES = v6.prod.TEMPLATES


MAP_ANCHORS: dict[str, dict[str, Any]] = {
    "bromine": {
        "gametype": "dm",
        "player_origin": [-40.5, 398.3, 156.4],
        "trajectory_scale": 0.75,
        "environment_text": v6.MAPS["bromine"]["environment_text"],
        "prompt_provenance_sample_id": v6.MAPS["bromine"]["prompt_provenance_sample_id"],
    },
    "catharsis": {
        "gametype": "ctf",
        "player_origin": [-455.1, -116.9, 24.0],
        "trajectory_scale": 0.75,
        "environment_text": "An industrial cavern built from concrete, brushed metal, raw rock, and glowing energy panels, with cool blue and warm red light strips, suspended walkways, stairs, jagged stone, and dark angular structures.",
        "prompt_provenance_sample_id": "s2short42v15r1_s2mtv42v14r4_000007",
    },
    "courtfun": {
        "gametype": "ctf",
        "player_origin": [-2048.0, 1984.0, 24.0],
        "trajectory_scale": 0.75,
        "environment_text": v6.MAPS["courtfun"]["environment_text"],
        "prompt_provenance_sample_id": v6.MAPS["courtfun"]["prompt_provenance_sample_id"],
    },
    "implosion": {
        "gametype": "dm",
        "player_origin": [1860.6, -2660.3, 152.0],
        "trajectory_scale": 0.75,
        "environment_text": "A space station built from brushed metal, steel plating, concrete, and glowing panels, with dark grey and metallic surfaces, red and blue lights, machinery, grid-patterned floors, and elevated platforms.",
        "prompt_provenance_sample_id": "s2short42v15r1_s2mtv42v14r4_000002",
    },
}
ANGLES = tuple(range(0, 360, 45))


def scaled_templates(scale: float) -> dict[str, tuple[Any, ...]]:
    return {
        template: tuple(
            replace(
                segment,
                lateral_start=segment.lateral_start * scale,
                lateral_end=segment.lateral_end * scale,
                distance_start=segment.distance_start * scale,
                distance_end=segment.distance_end * scale,
            )
            for segment in segments
        )
        for template, segments in ORIGINAL_TEMPLATES.items()
    }


def configure_row(row: dict[str, Any]) -> None:
    source = MAP_ANCHORS[str(row["map"])]
    angle = math.radians(float(row["angle_degrees"]))
    player = [float(value) for value in row["player_origin"]]
    map_config = {
        **source,
        "anchor_id": row["anchor_id"],
        "player_origin": player,
        "enemy_reference_origin": [
            player[0] + 200.0 * math.cos(angle),
            player[1] + 200.0 * math.sin(angle),
            player[2],
        ],
    }
    v6.MAPS = {str(row["map"]): map_config}
    v6.prod.TEMPLATES = scaled_templates(float(row["trajectory_scale"]))
    v6.configure_geometry_and_weapon(row)


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    source_rows = v6.distribution_rows()
    source = next(
        dict(row)
        for row in source_rows
        if row["template"] == "four_distinct" and int(row["kill_count"]) == 0
    )
    rows: list[dict[str, Any]] = []
    for map_name in sorted(MAP_ANCHORS):
        for angle in ANGLES:
            row = dict(source)
            index = len(rows)
            row.update(
                {
                    "manifest_index": index,
                    "scan_index": index,
                    "episode_id": f"l60scan_v1_{map_name}_a{angle:03d}",
                    "map": map_name,
                    "gametype": MAP_ANCHORS[map_name]["gametype"],
                    "anchor_id": f"{map_name}_density_anchor_a{angle:03d}_scale075",
                    "player_origin": MAP_ANCHORS[map_name]["player_origin"],
                    "trajectory_scale": MAP_ANCHORS[map_name]["trajectory_scale"],
                    "angle_degrees": angle,
                    "weapon": "MachineGun",
                    "weapon_netname": "machinegun",
                    "instant_hit_weapon": True,
                    "kill_count": 0,
                    "kill_slots": [],
                }
            )
            configure_row(row)
            actions = artifact_root / "actions" / map_name / f"a{angle:03d}.csv"
            v6.base.write_actions(
                actions,
                row["episode_id"],
                int(row["engine_seed"]),
                v6.prod.TEMPLATES["four_distinct"],
            )
            scenario_path, timeline = v6.build_episode_scenario(row, artifact_root, actions)
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            scenario["training_admitted"] = False
            scenario["anchor_angle_scan"] = {
                "scan_id": SCAN_ID,
                "angle_degrees": angle,
                "live_only": True,
            }
            v6.prod.write_json_atomic(scenario_path, scenario)
            row.update(
                {
                    "scenario_path": v6.prod.relative_to_root(scenario_path),
                    "scenario_sha256": v6.prod.base.sha256(scenario_path),
                    "actions_path": v6.prod.relative_to_root(actions),
                    "actions_sha256": v6.prod.base.sha256(actions),
                    "timeline_path": v6.prod.relative_to_root(timeline),
                    "timeline_sha256": v6.prod.base.sha256(timeline),
                }
            )
            rows.append(row)
    manifest = artifact_root / "scan_manifest.jsonl"
    v6.prod.write_jsonl_atomic(manifest, rows)
    v6.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-anchor-angle-live-scan-v1",
            "scan_id": SCAN_ID,
            "case_count": len(rows),
            "maps": sorted(MAP_ANCHORS),
            "angles": list(ANGLES),
            "live_only": True,
            "training_admitted": False,
            "manifest_sha256": v6.prod.base.sha256(manifest),
        },
    )


def longest_false_run(values: list[bool]) -> int:
    longest = current = 0
    for value in values:
        current = 0 if value else current + 1
        longest = max(longest, current)
    return longest


def evaluate(row: dict[str, Any], scenario: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    telemetry = v6.base.load_jsonl(Path(live["server_telemetry"]))
    states = [item for item in telemetry if item.get("kind") == "state"]
    events = [item for item in telemetry if item.get("kind") == "event"]
    fatals = [item for item in telemetry if item.get("kind") == "fatal"]
    reset = next((item for item in telemetry if item.get("kind") == "reset"), {})
    player_entity = int(reset.get("player_entity", -1))
    enemy_entity = int(reset.get("enemy_entity", -1))
    damage_events = [
        item
        for item in events
        if item.get("event") == "damage"
        and int(item.get("attacker", -1)) == player_entity
        and int(item.get("target", -1)) == enemy_entity
    ]
    damage_counts: list[int] = []
    damage_ticks_by_encounter: list[list[int]] = []
    crossings: list[dict[str, Any]] = []
    for encounter in scenario["encounters"]:
        start_tick = v6.base.capture.WARMUP_TICKS + int(
            encounter["start_block"] * v6.base.PROMPT_BLOCK_SECONDS * 64
        )
        end_tick = v6.base.capture.WARMUP_TICKS + int(
            encounter["end_block"] * v6.base.PROMPT_BLOCK_SECONDS * 64
        )
        encounter_damage_ticks = [
            int(item["server_tick"])
            for item in damage_events
            if start_tick <= int(item["server_tick"]) < end_tick
        ]
        damage_counts.append(len(encounter_damage_ticks))
        damage_ticks_by_encounter.append(encounter_damage_ticks)
        encounter_states = [
            item
            for item in states
            if start_tick <= int(item["server_tick"]) < end_tick
            and isinstance(item.get("enemy"), dict)
            and item["enemy"].get("actor_id") == encounter["actor_id"]
        ]
        relative_yaws = []
        for item in encounter_states:
            player = item["post"]["origin"]
            enemy = item["enemy"]["origin"]
            bearing = math.degrees(math.atan2(enemy[1] - player[1], enemy[0] - player[0]))
            relative_yaws.append(
                abs(v6.base.shortest_angle_delta(bearing, item["post"]["angles"][1]))
            )
        crossings.append(
            {
                "actor_id": encounter["actor_id"],
                "start": relative_yaws[0] if relative_yaws else None,
                "minimum": min(relative_yaws) if relative_yaws else None,
                "end": relative_yaws[-1] if relative_yaws else None,
                "crosses": bool(relative_yaws)
                and relative_yaws[0] >= v6.base.EXPANDED_VIEW_HALF_YAW_DEGREES
                and min(relative_yaws) <= 8.0
                and relative_yaws[-1] >= v6.base.EXPANDED_VIEW_HALF_YAW_DEGREES,
            }
        )
    origins = [item["post"]["origin"] for item in states]
    path_length = sum(
        math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(origins, origins[1:])
    )
    output_states = states[v6.base.capture.WARMUP_TICKS :]
    moving = [
        math.hypot(item["post"]["velocity"][0], item["post"]["velocity"][1]) >= 20.0
        for item in output_states
    ]
    scale = float(row["trajectory_scale"])
    expected_encounters = len(scenario["encounters"])
    checks = {
        "state_count": len(states) == v6.base.capture.TOTAL_TICKS,
        "no_fatal": not fatals,
        "all_encounters_damaged": len(damage_counts) == expected_encounters
        and min(damage_counts) >= 1,
        "no_enemy_kill": not any(int(item.get("killed", 0)) for item in damage_events),
        "all_cross_expanded_view": len(crossings) == expected_encounters
        and all(item["crosses"] for item in crossings),
        "player_path": path_length >= 2200.0 * scale,
        "player_motion_duty": 0.70 <= sum(moving) / max(1, len(moving)) <= 0.92,
        "no_long_realized_idle": longest_false_run(moving) <= int(1.5 * 64),
    }
    return {
        "schema_version": "xonotic-long60-anchor-angle-live-scan-result-v1",
        "scan_id": SCAN_ID,
        "episode_id": row["episode_id"],
        "map": row["map"],
        "angle_degrees": row["angle_degrees"],
        "trajectory_scale": scale,
        "passed": all(checks.values()),
        "checks": checks,
        "damage_counts": damage_counts,
        "damage_ticks_by_encounter": damage_ticks_by_encounter,
        "crossings": crossings,
        "player_path_length": path_length,
        "player_motion_duty": sum(moving) / max(1, len(moving)),
        "longest_realized_idle_seconds": longest_false_run(moving) / 64.0,
        "live_wall_seconds": live["live_wall_seconds"],
        "training_admitted": False,
    }


def worker(
    artifact_root: Path,
    output_root: Path,
    scratch_root: Path,
    lane_id: int,
    lane_count: int,
    port: int,
) -> None:
    rows = v6.prod.load_jsonl(artifact_root.resolve() / "scan_manifest.jsonl")
    selected = [row for row in rows if int(row["scan_index"]) % lane_count == lane_id]
    build = ROOT / "build" / v6.BUILD_TAG
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lane: Any | None = None
    current_group: tuple[str, str] | None = None
    generation = 0
    results: list[dict[str, Any]] = []
    try:
        for sequence, row in enumerate(selected, 1):
            result_path = output_root / "results" / f"{row['episode_id']}.json"
            if result_path.is_file():
                results.append(json.loads(result_path.read_text(encoding="utf-8")))
                continue
            configure_row(row)
            scenario_path = ROOT / row["scenario_path"]
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            stage = scratch_root / "episodes" / row["episode_id"]
            v6.prod.safe_remove_stage(stage, scratch_root)
            requested_group = (str(row["map"]), str(row["gametype"]))
            if lane is not None and current_group != requested_group:
                lane.close()
                lane = None
                current_group = None
            if lane is None:
                generation += 1
                lane = v6.base.reusable.ReusableStage1Lane(
                    scratch_root / f"resident-generation-{generation:03d}",
                    build=build,
                    port=port,
                )
                current_group = requested_group
            try:
                v6.prod.configure_runtime(row)
                live = lane.run_live(stage, scenario, retry=0)
                result = evaluate(row, scenario, live)
                results.append(result)
                v6.prod.write_json_atomic(
                    output_root / "results" / f"{row['episode_id']}.json", result
                )
                print(
                    f"live_scan lane={lane_id} map={row['map']} angle={row['angle_degrees']} "
                    f"passed={result['passed']} damage={result['damage_counts']} "
                    f"path={result['player_path_length']:.0f} "
                    f"progress={sequence}/{len(selected)}",
                    flush=True,
                )
            except Exception:
                traceback.print_exc()
                lane.close()
                lane = None
                current_group = None
            finally:
                v6.prod.safe_remove_stage(stage, scratch_root)
    finally:
        if lane is not None:
            lane.close()
    v6.prod.write_json_atomic(
        output_root / "status" / f"lane-{lane_id:02d}.json",
        {
            "schema_version": "xonotic-long60-anchor-angle-live-scan-lane-v1",
            "lane_id": lane_id,
            "selected": len(selected),
            "result_count": len(results),
            "passed": sum(item["passed"] for item in results),
            "raw_avi_created": False,
        },
    )


def report(artifact_root: Path, output_root: Path) -> None:
    rows = v6.prod.load_jsonl(artifact_root.resolve() / "scan_manifest.jsonl")
    results = []
    for row in rows:
        path = output_root.resolve() / "results" / f"{row['episode_id']}.json"
        if path.is_file():
            results.append(json.loads(path.read_text(encoding="utf-8")))
    summary = {
        "schema_version": "xonotic-long60-anchor-angle-live-scan-report-v1",
        "scan_id": SCAN_ID,
        "expected": len(rows),
        "completed": len(results),
        "passed": sum(item["passed"] for item in results),
        "passing_by_map": {
            map_name: [
                item["angle_degrees"]
                for item in results
                if item["map"] == map_name and item["passed"]
            ]
            for map_name in sorted(MAP_ANCHORS)
        },
        "training_admitted": False,
    }
    v6.prod.write_json_atomic(output_root.resolve() / "SCAN_REPORT.json", summary)
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
    worker_parser.add_argument("--lane-count", type=int, default=8)
    worker_parser.add_argument("--port", type=int, required=True)
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
        )
    else:
        report(args.artifact_root, args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
