                      
"""Collect no-fire, all-alive bearing traces for long60 v8.

This artifact is calibration-only and never training-admitted.  Suppressing
primary input and selecting zero-kill rows prevents a corpse or killed actor
from contaminating a later encounter's frozen bearing trace.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault("XONOTIC_LIVE_TIME_SCALE", "2")
os.environ.setdefault("XONOTIC_LIVE_TIMEOUT_SECONDS", "240")

V8_PATH = Path(__file__).with_name(
    "long60_production_ref42_v8_collision_camera.py"
)
SPEC = importlib.util.spec_from_file_location("long60_v8_bearing_calibration", V8_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v8 runtime: {V8_PATH}")
v8 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v8
SPEC.loader.exec_module(v8)


CALIBRATION_ID = "long60_v8_canonical_world_motion_nofire_alive8_20260829"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID


def choose_rows() -> list[dict[str, Any]]:
    source = v8.distribution_rows()
    rows: list[dict[str, Any]] = []
    for map_name in sorted(v8.MAPS):
        for template in sorted(v8.v7.ORIGINAL_TEMPLATES):
            candidates = [
                dict(row)
                for row in source
                if row["map"] == map_name
                and row["template"] == template
                and row["weapon"] == "MachineGun"
                and int(row["kill_count"]) == 0
                and not row["kill_slots"]
            ]
            candidates.sort(key=lambda row: int(row["manifest_index"]))
            if not candidates:
                raise RuntimeError(f"no zero-kill calibration row: {map_name}/{template}")
            row = candidates[0]
            index = len(rows)
            row.update(
                {
                    "manifest_index": index,
                    "calibration_index": index,
                    "episode_id": f"l60v8_cal_{index:02d}_{map_name}_{template}",
                    "training_admitted": False,
                    "formal_collection_authorized": False,
                    "calibration_only": True,
                    "geometry_config_sha256": v8.CONFIG_SHA256,
                    "anchor_id": v8.geometry_anchor_id(row),
                    "trajectory_scale": float(v8.geometry_for(row)["trajectory_scale"]),
                }
            )
            rows.append(row)
    return rows


def suppress_primary(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        seed_line = handle.readline()
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError(f"actions have no header: {path}")
    for row in rows:
        row["primary"] = "0"
        row["secondary"] = "0"
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        handle.write(seed_line)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def prepare(artifact_root: Path, keep_fire: bool = False) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    rows = choose_rows()
    for row in rows:
        actions = artifact_root / "actions" / f"{row['map']}_{row['template']}.csv"
        v8.write_actions(actions, row)
        if not keep_fire:
            suppress_primary(actions)
        scenario_path, timeline = v8.build_episode_scenario(
            row, artifact_root, actions
        )
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        if any(float(actor["health"]) != 999.0 for actor in scenario["actors"]):
            raise RuntimeError(f"non-neutral calibration actor health: {row['episode_id']}")
        scenario.update(
            {
                "calibration_only": True,
                "calibration_id": CALIBRATION_ID,
                "calibration_fire_suppressed": not keep_fire,
                "training_admitted": False,
                "formal_collection_authorized": False,
            }
        )
        v8.prod.write_json_atomic(scenario_path, scenario)
        row.update(
            {
                "scenario_path": v8.prod.relative_to_root(scenario_path),
                "scenario_sha256": v8.base.sha256(scenario_path),
                "actions_path": v8.prod.relative_to_root(actions),
                "actions_sha256": v8.base.sha256(actions),
                "timeline_path": v8.prod.relative_to_root(timeline),
                "timeline_sha256": v8.base.sha256(timeline),
            }
        )
    manifest = artifact_root / "calibration_manifest.jsonl"
    v8.prod.write_jsonl_atomic(manifest, rows)
    v8.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-v8-bearing-calibration-prepared-v1",
            "calibration_id": CALIBRATION_ID,
            "episode_count": len(rows),
            "manifest_sha256": v8.base.sha256(manifest),
            "runtime_build": v8.BUILD_TAG,
            "runtime_source_commit": v8.BUILD_COMMIT,
            "geometry_config_sha256": v8.CONFIG_SHA256,
            "fire_suppressed": not keep_fire,
            "all_actor_health": 999.0,
            "training_admitted": False,
        },
    )
    print(json.dumps({"prepared": len(rows), "root": str(artifact_root)}))


def live_probe(
    artifact_root: Path,
    scratch_root: Path,
    port: int,
    map_name: str,
    template: str,
    report_path: Path,
    expect_fire: bool = False,
) -> None:
    rows = v8.prod.load_jsonl(
        artifact_root.resolve() / "calibration_manifest.jsonl"
    )
    row = next(
        item
        for item in rows
        if item["map"] == map_name and item["template"] == template
    )
    scenario = json.loads((ROOT / row["scenario_path"]).read_text(encoding="utf-8"))
    build = ROOT / "build" / v8.BUILD_TAG
    with v8.base.reusable.ReusableStage1Lane(
        scratch_root.resolve() / "resident", build=build, port=port
    ) as lane:
        live = lane.run_live(scratch_root.resolve() / "episode", scenario, retry=0)
    telemetry = v8.prod.load_jsonl(Path(live["server_telemetry"]))
    states = [item for item in telemetry if item.get("kind") == "state"]
    events = [item for item in telemetry if item.get("kind") == "event"]
    fatals = [item for item in telemetry if item.get("kind") == "fatal"]
    reset = next(item for item in telemetry if item.get("kind") == "reset")
    player_entity = int(reset["player_entity"])
    enemy_entity = int(reset["enemy_entity"])
    origins = [item["post"]["origin"] for item in states]
    path_length = sum(
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(origins, origins[1:])
    )
    anchor = scenario["player"]["origin"]
    maximum_displacement = max(
        math.hypot(origin[0] - anchor[0], origin[1] - anchor[1])
        for origin in origins
    )
    diagnostics = []
    complete_trace_checks = []
    damage_by_encounter = []
    all_enemy_samples_alive = True
    for encounter in scenario["encounters"]:
        start = v8.base.capture.WARMUP_TICKS + int(
            encounter["start_block"] * v8.base.PROMPT_BLOCK_SECONDS * 64
        )
        end = v8.base.capture.WARMUP_TICKS + int(
            encounter["end_block"] * v8.base.PROMPT_BLOCK_SECONDS * 64
        )
        actor_states = [
            item
            for item in states
            if start <= int(item["server_tick"]) < end
            and isinstance(item.get("enemy"), dict)
            and item["enemy"].get("actor_id") == encounter["actor_id"]
        ]
        trace = []
        for item in actor_states:
            player_origin = item["post"]["origin"]
            enemy_origin = item["enemy"]["origin"]
            trace.append(
                [
                    int(item["server_tick"]),
                    round(
                        math.degrees(
                            math.atan2(
                                enemy_origin[1] - player_origin[1],
                                enemy_origin[0] - player_origin[0],
                            )
                        ),
                        6,
                    ),
                ]
            )
            all_enemy_samples_alive = all_enemy_samples_alive and float(
                item["enemy"]["health"]
            ) > 0.0
        complete = (
            len(trace) >= end - start - 2
            and bool(trace)
            and trace[0][0] <= start + 1
            and trace[-1][0] >= end - 1
        )
        complete_trace_checks.append(complete)
        damage_by_encounter.append(
            sum(
                start <= int(item["server_tick"]) < end
                for item in events
                if item.get("event") == "damage"
                and int(item.get("attacker", -1)) == player_entity
                and int(item.get("target", -1)) == enemy_entity
            )
        )
        diagnostics.append(
            {
                "actor_id": encounter["actor_id"],
                "start_tick": start,
                "end_tick": end,
                "bearing_trace": trace,
            }
        )
    player_fires = [
        item
        for item in events
        if item.get("event") == "fire"
        and int(item.get("actor", -1)) == player_entity
    ]
    player_damage = [
        item
        for item in events
        if item.get("event") == "damage"
        and int(item.get("attacker", -1)) == player_entity
        and int(item.get("target", -1)) == enemy_entity
    ]
    killed_events = [item for item in player_damage if int(item.get("killed", 0))]
    scale = float(v8.PLAYER_MOTION_CONFIG["scale"])
    checks = {
        "no_fatal": not fatals,
        "state_count": len(states) == v8.base.capture.TOTAL_TICKS,
        "fire_event_contract": bool(player_fires) is expect_fire,
        "damage_event_contract": (
            bool(damage_by_encounter)
            and min(damage_by_encounter) >= 1
            if expect_fire
            else not player_damage
        ),
        "zero_kill_events": not killed_events,
        "all_enemy_samples_alive": all_enemy_samples_alive,
        "complete_trace_every_encounter": all(complete_trace_checks),
        "player_path": path_length >= 2200.0 * scale,
        "player_displacement_min": maximum_displacement >= 40.0 * scale,
        "player_displacement_max": maximum_displacement <= 500.0 * scale,
    }
    report = {
        "schema_version": "xonotic-long60-v8-nofire-bearing-calibration-v1",
        "calibration_id": CALIBRATION_ID,
        "episode_id": row["episode_id"],
        "map": map_name,
        "template": template,
        "weapon": row["weapon"],
        "checks": checks,
        "passed": all(checks.values()),
        "state_count": len(states),
        "fatal_reasons": [item.get("reason") for item in fatals],
        "player_fire_events": len(player_fires),
        "player_damage_events": len(player_damage),
        "player_damage_events_by_encounter": damage_by_encounter,
        "player_kill_events": len(killed_events),
        "player_path_length_units": path_length,
        "player_maximum_displacement_units": maximum_displacement,
        "aim_diagnostics_by_encounter": diagnostics,
        "runtime_build": v8.BUILD_TAG,
        "runtime_source_commit": v8.BUILD_COMMIT,
        "geometry_config_sha256": v8.CONFIG_SHA256,
        "live_wall_seconds": live["live_wall_seconds"],
        "training_admitted": False,
    }
    v8.prod.write_json_atomic(report_path.resolve(), report)
    print(json.dumps({key: value for key, value in report.items() if key != "aim_diagnostics_by_encounter"}, sort_keys=True))
    if not report["passed"]:
        raise RuntimeError(f"bearing calibration failed: {map_name}/{template}: {checks}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument(
        "--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT
    )
    prepare_parser.add_argument("--keep-fire", action="store_true")
    live_parser = sub.add_parser("live-probe")
    live_parser.add_argument(
        "--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT
    )
    live_parser.add_argument("--scratch-root", type=Path, required=True)
    live_parser.add_argument("--port", type=int, required=True)
    live_parser.add_argument("--map", choices=tuple(sorted(v8.MAPS)), required=True)
    live_parser.add_argument(
        "--template",
        choices=tuple(sorted(v8.v7.ORIGINAL_TEMPLATES)),
        required=True,
    )
    live_parser.add_argument("--report", type=Path, required=True)
    live_parser.add_argument("--expect-fire", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.artifact_root, args.keep_fire)
    else:
        live_probe(
            args.artifact_root,
            args.scratch_root,
            args.port,
            args.map,
            args.template,
            args.report,
            args.expect_fire,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
