                      
"""Live-only 4-map x 3-hitscan x 2-template v7 calibration matrix."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V7_PATH = Path(__file__).with_name(
    "long60_production_ref42_v7_multimap_hitscan.py"
)
SPEC = importlib.util.spec_from_file_location("long60_v7_live_calibration_base", V7_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v7 module: {V7_PATH}")
v7 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v7
SPEC.loader.exec_module(v7)


CALIBRATION_ID = "long60_ref42_v7_hitscan_live_calibration24_20260828_r8_rifle"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID


def slug(value: str) -> str:
    return value.lower().replace("_", "-")


def choose_rows() -> list[dict[str, Any]]:
    source = v7.distribution_rows()
    selected = []
    configured_cells = sorted(
        {(row["template"], row["map"], row["weapon"]) for row in source}
    )
    for template, map_name, weapon in configured_cells:
        row = next(
            dict(item)
            for item in source
            if item["template"] == template
            and item["map"] == map_name
            and item["weapon"] == weapon
            and int(item["kill_count"]) == 0
        )
        index = len(selected)
        row.update(
            {
                "manifest_index": index,
                "calibration_index": index,
                "episode_id": (
                    f"l60v7cal_{slug(template)}_{slug(map_name)}_{slug(weapon)}"
                ),
                "split": "test",
                "kill_count": 0,
                "kill_slots": [],
                "training_admitted": False,
            }
        )
        selected.append(row)
    return selected


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    rows = choose_rows()
    for row in rows:
        actions_root = (
            artifact_root
            / "actions"
            / row["template"]
            / row["map"]
            / row["weapon"]
        )
        if row.get("calibration_variant"):
            actions_root /= str(row["calibration_variant"])
        actions = actions_root / "actions.csv"
        v7.write_actions(actions, row)
        scenario_path, timeline = v7.build_episode_scenario(row, artifact_root, actions)
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["formal_collection_authorized"] = False
        scenario["training_admitted"] = False
        scenario["live_calibration"] = {
            "calibration_id": CALIBRATION_ID,
            "live_only": True,
            "kill_count": 0,
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
    manifest = artifact_root / "calibration_manifest.jsonl"
    v7.prod.write_jsonl_atomic(manifest, rows)
    v7.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-v7-hitscan-live-calibration-prepared-v1",
            "calibration_id": CALIBRATION_ID,
            "case_count": len(rows),
            "maps": sorted(v7.MAPS),
            "weapons": sorted(v7.WEAPONS),
            "templates": sorted(v7.ORIGINAL_TEMPLATES),
            "geometry_config_sha256": v7.CONFIG_SHA256,
            "manifest_sha256": v7.base.sha256(manifest),
            "live_only": True,
            "training_admitted": False,
        },
    )


def longest_false_run(values: list[bool]) -> int:
    longest = current = 0
    for value in values:
        current = 0 if value else current + 1
        longest = max(longest, current)
    return longest


def evaluate(row: dict[str, Any], scenario: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    telemetry = v7.prod.load_jsonl(Path(live["server_telemetry"]))
    states = [item for item in telemetry if item.get("kind") == "state"]
    events = [item for item in telemetry if item.get("kind") == "event"]
    fatals = [item for item in telemetry if item.get("kind") == "fatal"]
    reset = next((item for item in telemetry if item.get("kind") == "reset"), {})
    player_entity = int(reset.get("player_entity", -1))
    enemy_entity = int(reset.get("enemy_entity", -1))
    fire_events = [
        item
        for item in events
        if item.get("event") == "fire"
        and int(item.get("actor", -1)) == player_entity
    ]
    damage_events = [
        item
        for item in events
        if item.get("event") == "damage"
        and int(item.get("attacker", -1)) == player_entity
        and int(item.get("target", -1)) == enemy_entity
    ]
    encounters = []
    for encounter in scenario["encounters"]:
        start_tick = v7.base.capture.WARMUP_TICKS + int(
            encounter["start_block"] * v7.base.PROMPT_BLOCK_SECONDS * 64
        )
        end_tick = v7.base.capture.WARMUP_TICKS + int(
            encounter["end_block"] * v7.base.PROMPT_BLOCK_SECONDS * 64
        )
        damage = [
            item
            for item in damage_events
            if start_tick <= int(item["server_tick"]) < end_tick
        ]
        fires = [
            item
            for item in fire_events
            if start_tick <= int(item["server_tick"]) < end_tick
        ]
        encounter_states = [
            item
            for item in states
            if start_tick <= int(item["server_tick"]) < end_tick
            and isinstance(item.get("enemy"), dict)
            and item["enemy"].get("actor_id") == encounter["actor_id"]
        ]
        relative_yaws: list[tuple[int, float]] = []
        for item in encounter_states:
            player = item["post"]["origin"]
            enemy = item["enemy"]["origin"]
            bearing = math.degrees(math.atan2(enemy[1] - player[1], enemy[0] - player[0]))
            relative_yaws.append(
                (
                    int(item["server_tick"]),
                    abs(
                        v7.base.shortest_angle_delta(
                            bearing, item["post"]["angles"][1]
                        )
                    ),
                )
            )
        minimum_yaw = min(relative_yaws, key=lambda value: value[1]) if relative_yaws else None
        encounters.append(
            {
                "actor_id": encounter["actor_id"],
                "returning": encounter["returning"],
                "fire_ticks": [int(item["server_tick"]) for item in fires],
                "damage_ticks": [int(item["server_tick"]) for item in damage],
                "damage_amounts": [float(item["amount"]) for item in damage],
                "total_damage": sum(float(item["amount"]) for item in damage),
                "crosses_expanded_view": bool(relative_yaws)
                and relative_yaws[0][1] >= v7.base.EXPANDED_VIEW_HALF_YAW_DEGREES
                and minimum_yaw is not None
                and minimum_yaw[1] <= 8.0
                and relative_yaws[-1][1] >= v7.base.EXPANDED_VIEW_HALF_YAW_DEGREES,
                "minimum_relative_yaw": minimum_yaw[1] if minimum_yaw else None,
                "minimum_relative_yaw_tick": minimum_yaw[0] if minimum_yaw else None,
            }
        )
    origins = [item["post"]["origin"] for item in states]
    path_length = sum(
        math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(origins, origins[1:])
    )
    output_states = states[v7.base.capture.WARMUP_TICKS :]
    moving = [
        math.hypot(item["post"]["velocity"][0], item["post"]["velocity"][1]) >= 20.0
        for item in output_states
    ]
    scale = float(row["trajectory_scale"])
    checks = {
        "state_count": len(states) == v7.base.capture.TOTAL_TICKS,
        "no_fatal": not fatals,
        "selected_weapon_fired": bool(fire_events)
        and all(
            int(item.get("weapon_id", -1))
            == int(v7.WEAPONS[str(row["weapon"])]["weapon_id"])
            for item in fire_events
        ),
        "fire_in_every_encounter": bool(encounters)
        and all(item["fire_ticks"] for item in encounters),
        "damage_in_every_encounter": bool(encounters)
        and all(item["damage_ticks"] for item in encounters),
        "no_enemy_kill": not any(int(item.get("killed", 0)) for item in damage_events),
        "all_cross_expanded_view": bool(encounters)
        and all(item["crosses_expanded_view"] for item in encounters),
        "player_path": path_length >= 2200.0 * scale,
        "player_motion_duty": 0.70 <= sum(moving) / max(1, len(moving)) <= 0.92,
        "no_long_realized_idle": longest_false_run(moving) <= int(1.5 * 64),
    }
    return {
        "schema_version": "xonotic-long60-v7-hitscan-live-calibration-result-v1",
        "calibration_id": CALIBRATION_ID,
        "episode_id": row["episode_id"],
        "template": row["template"],
        "map": row["map"],
        "weapon": row["weapon"],
        "weapon_netname": row["weapon_netname"],
        "fire_weapon_ids": sorted({int(item.get("weapon_id", -1)) for item in fire_events}),
        "trajectory_scale": scale,
        "passed": all(checks.values()),
        "checks": checks,
        "encounters": encounters,
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
    rows = v7.prod.load_jsonl(artifact_root.resolve() / "calibration_manifest.jsonl")
    selected = [row for row in rows if int(row["calibration_index"]) % lane_count == lane_id]
    build = ROOT / "build" / v7.BUILD_TAG
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lane: Any | None = None
    current_group: tuple[str, str] | None = None
    generation = 0
    results = []
    try:
        for sequence, row in enumerate(selected, 1):
            result_path = output_root / "results" / f"{row['episode_id']}.json"
            if result_path.is_file():
                results.append(json.loads(result_path.read_text(encoding="utf-8")))
                continue
            v7.configure_geometry_and_weapon(row)
            scenario = json.loads((ROOT / row["scenario_path"]).read_text(encoding="utf-8"))
            stage = scratch_root / "episodes" / row["episode_id"]
            v7.prod.safe_remove_stage(stage, scratch_root)
            requested_group = (str(row["map"]), str(row["gametype"]))
            if lane is not None and current_group != requested_group:
                lane.close()
                lane = None
                current_group = None
            if lane is None:
                generation += 1
                lane = v7.base.reusable.ReusableStage1Lane(
                    scratch_root / f"resident-generation-{generation:03d}",
                    build=build,
                    port=port,
                )
                current_group = requested_group
            try:
                v7.prod.configure_runtime(row)
                live = lane.run_live(stage, scenario, retry=0)
                result = evaluate(row, scenario, live)
                results.append(result)
                v7.prod.write_json_atomic(result_path, result)
                print(
                    f"live_calibration lane={lane_id} template={row['template']} "
                    f"map={row['map']} weapon={row['weapon']} passed={result['passed']} "
                    f"damage={[item['total_damage'] for item in result['encounters']]} "
                    f"progress={sequence}/{len(selected)}",
                    flush=True,
                )
            except Exception:
                traceback.print_exc()
                lane.close()
                lane = None
                current_group = None
            finally:
                v7.prod.safe_remove_stage(stage, scratch_root)
    finally:
        if lane is not None:
            lane.close()
    v7.prod.write_json_atomic(
        output_root / "status" / f"lane-{lane_id:02d}.json",
        {
            "schema_version": "xonotic-long60-v7-hitscan-live-calibration-lane-v1",
            "lane_id": lane_id,
            "selected": len(selected),
            "result_count": len(results),
            "passed": sum(item["passed"] for item in results),
            "raw_avi_created": False,
        },
    )


def report(artifact_root: Path, output_root: Path) -> None:
    rows = v7.prod.load_jsonl(artifact_root.resolve() / "calibration_manifest.jsonl")
    results = []
    for row in rows:
        path = output_root.resolve() / "results" / f"{row['episode_id']}.json"
        if path.is_file():
            results.append(json.loads(path.read_text(encoding="utf-8")))
    summary = {
        "schema_version": "xonotic-long60-v7-hitscan-live-calibration-report-v1",
        "calibration_id": CALIBRATION_ID,
        "expected": len(rows),
        "completed": len(results),
        "passed": sum(item["passed"] for item in results),
        "failed_cells": [
            [item["template"], item["map"], item["weapon"]]
            for item in results
            if not item["passed"]
        ],
        "cell_counts": {
            "/".join(key): value
            for key, value in sorted(
                Counter((item["template"], item["map"], item["weapon"]) for item in results).items()
            )
        },
        "raw_avi_created": False,
        "training_admitted": False,
    }
    v7.prod.write_json_atomic(output_root.resolve() / "CALIBRATION_REPORT.json", summary)
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
    worker_parser.add_argument("--lane-count", type=int, default=6)
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
