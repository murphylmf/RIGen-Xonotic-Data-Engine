                      
"""Prepare and render an isolated 12-cell review of long60 v8.

This pilot is review-only.  It covers every map/weapon pair, alternates both
motion templates, exercises one declared kill, and never admits its outputs to
training.  Raw AVI files live only in local scratch and are removed by the
normal acceptance path (or by the failure cleanup below).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_CAPTURE_CLIENT_OVERLAY",
    "configs/capture_client_stage2_v14_no_crosshair.cfg",
)
os.environ.setdefault("XONOTIC_LIVE_TIME_SCALE", "2")
os.environ.setdefault("XONOTIC_OFFLINE_ACCELERATE", "1")
os.environ.setdefault("XONOTIC_LIVE_TIMEOUT_SECONDS", "240")
os.environ.setdefault("XONOTIC_RENDER_TIMEOUT_SECONDS", "600")
os.environ.setdefault("XONOTIC_ENGINE_NET_TIMEOUT_SECONDS", "660")
os.environ.setdefault("XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "120")
os.environ.setdefault("SDL_VIDEODRIVER", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "opengl")

V8_PATH = Path(__file__).with_name(
    "long60_production_ref42_v8_collision_camera.py"
)
SPEC = importlib.util.spec_from_file_location("long60_v8_review_runtime", V8_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v8 runtime: {V8_PATH}")
v8 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v8
SPEC.loader.exec_module(v8)


PILOT_ID = "stage2_long60_v8_collision_camera_review12_v11_20260829"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / PILOT_ID
DEFAULT_OUTPUT_ROOT = Path("./rigen_data/reviews") / PILOT_ID


def choose_rows() -> list[dict[str, Any]]:
    source = v8.distribution_rows()
    templates = sorted(v8.v7.ORIGINAL_TEMPLATES)
    rows: list[dict[str, Any]] = []
    for map_index, map_name in enumerate(sorted(v8.MAPS)):
        for weapon_index, weapon_name in enumerate(sorted(v8.WEAPONS)):
            if weapon_name == "MachineGun":
                                                                            
                                                                              
                                                        
                template = "controlled_return"
            elif weapon_name == "Rifle":
                template = "four_distinct"
            else:
                template = templates[map_index % len(templates)]
            candidates = [
                dict(row)
                for row in source
                if row["map"] == map_name
                and row["weapon"] == weapon_name
                and row["template"] == template
                and int(row["kill_count"]) == 1
                and (
                    weapon_name != "MachineGun"
                    or [int(value) for value in row["kill_slots"]] == [1]
                )
            ]
            candidates.sort(key=lambda row: int(row["manifest_index"]))
            if not candidates:
                raise RuntimeError(
                    f"no review candidate for {map_name}/{weapon_name}/{template}"
                )
            review_index = len(rows)
            row = candidates[(review_index * 3) % len(candidates)]
            row.update(
                {
                    "manifest_index": review_index,
                    "pilot_index": review_index,
                    "episode_id": (
                        f"l60v8_review_{review_index:02d}_{map_name}_"
                        f"{weapon_name.lower()}"
                    ),
                    "split": "train",
                    "release_id": v8.RELEASE_ID,
                    "schema_version": v8.SCHEMA_VERSION,
                    "training_admitted": False,
                    "formal_collection_authorized": False,
                    "anchor_id": v8.geometry_anchor_id(row),
                    "trajectory_scale": float(
                        v8.geometry_for(row)["trajectory_scale"]
                    ),
                    "geometry_config_sha256": v8.CONFIG_SHA256,
                    "camera_profile": v8.camera_profile_for(row),
                    "collision_policy": (
                        "canonical_hull_world_sweep_ground_support_v8"
                    ),
                }
            )
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
            / str(row["template"])
            / "actions.csv"
        )
        v8.write_actions(actions, row)
        scenario_path, timeline = v8.build_episode_scenario(
            row, artifact_root, actions
        )
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["formal_collection_authorized"] = False
        scenario["training_admitted"] = False
        scenario["review_qualification"] = {
            "pilot_id": PILOT_ID,
            "review_only": True,
            "training_admitted": False,
        }
        v8.prod.write_json_atomic(scenario_path, scenario)
        row.update(
            {
                "scenario_path": v8.prod.relative_to_root(scenario_path),
                "scenario_sha256": v8.base.sha256(scenario_path),
                "actions_path": v8.prod.relative_to_root(actions),
                "actions_sha256": v8.base.sha256(actions),
                "timeline_path": v8.prod.relative_to_root(timeline),
                "timeline_sha256": v8.base.sha256(timeline),
                "raw_avi_retained": False,
            }
        )
    manifest = artifact_root / "pilot_manifest.jsonl"
    v8.prod.write_jsonl_atomic(manifest, rows)
    v8.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-v8-review-prepared-v1",
            "pilot_id": PILOT_ID,
            "episode_count": len(rows),
            "manifest_sha256": v8.base.sha256(manifest),
            "runtime_build": v8.BUILD_TAG,
            "runtime_source_commit": v8.BUILD_COMMIT,
            "geometry_config_sha256": v8.CONFIG_SHA256,
            "raw_avi_retained": False,
            "training_admitted": False,
            "formal_collection_authorized": False,
        },
    )
    print(json.dumps({"prepared": len(rows), "root": str(artifact_root)}))


def remove_transient_avis(scratch_root: Path) -> None:
    scratch = scratch_root.resolve()
    if not str(scratch).startswith(("./tmp/", "./tmp/")):
        raise RuntimeError(f"refusing AVI cleanup outside local scratch: {scratch}")
    for path in scratch.rglob("*.avi"):
        path.unlink(missing_ok=True)


def live_probe(
    artifact_root: Path,
    scratch_root: Path,
    port: int,
    map_only: str,
    template_only: str | None,
    weapon_only: str | None,
    report_path: Path,
) -> None:
    rows = v8.prod.load_jsonl(artifact_root.resolve() / "pilot_manifest.jsonl")
    candidates = [
        item
        for item in rows
        if item["map"] == map_only
        and (template_only is None or item["template"] == template_only)
        and (weapon_only is None or item["weapon"] == weapon_only)
    ]
    candidates.sort(
        key=lambda item: (
            item["weapon"] != "MachineGun",
            int(item["pilot_index"]),
        )
    )
    if not candidates:
        raise RuntimeError(
            "no live-probe row for "
            f"{map_only}/{template_only or 'default'}/"
            f"{weapon_only or 'default'}"
        )
    row = candidates[0]
    scenario = json.loads((ROOT / row["scenario_path"]).read_text())
    build = ROOT / "build" / v8.BUILD_TAG
    stage = scratch_root.resolve() / "episode"
    with v8.base.reusable.ReusableStage1Lane(
        scratch_root.resolve() / "resident", build=build, port=port
    ) as lane:
        live = lane.run_live(stage, scenario, retry=0)
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
    output_states = states[v8.base.capture.WARMUP_TICKS :]
    motion_duty = sum(
        math.hypot(*item["post"]["velocity"][:2]) >= 20.0
        for item in output_states
    ) / len(output_states)
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
    damage_by_encounter = []
    aim_diagnostics_by_encounter = []
    for encounter in scenario["encounters"]:
        start = v8.base.capture.WARMUP_TICKS + int(
            encounter["start_block"] * v8.base.PROMPT_BLOCK_SECONDS * 64
        )
        end = v8.base.capture.WARMUP_TICKS + int(
            encounter["end_block"] * v8.base.PROMPT_BLOCK_SECONDS * 64
        )
        damage_by_encounter.append(
            sum(start <= int(item["server_tick"]) < end for item in damage_events)
        )
        actor_states = [
            item
            for item in states
            if start <= int(item["server_tick"]) < end
            and isinstance(item.get("enemy"), dict)
            and item["enemy"].get("actor_id") == encounter["actor_id"]
        ]
        yaw_samples = []
        for item in actor_states:
            player_origin = item["post"]["origin"]
            enemy_origin = item["enemy"]["origin"]
            bearing = math.degrees(
                math.atan2(
                    enemy_origin[1] - player_origin[1],
                    enemy_origin[0] - player_origin[0],
                )
            )
            view_yaw = float(item["post"]["angles"][1])
            yaw_samples.append(
                {
                    "server_tick": int(item["server_tick"]),
                    "absolute_yaw_error_degrees": abs(
                        v8.base.shortest_angle_delta(bearing, view_yaw)
                    ),
                    "bearing_degrees": bearing,
                    "view_yaw_degrees": view_yaw,
                    "horizontal_distance_units": math.hypot(
                        enemy_origin[0] - player_origin[0],
                        enemy_origin[1] - player_origin[1],
                    ),
                    "enemy_minus_player_z_units": (
                        enemy_origin[2] - player_origin[2]
                    ),
                }
            )
        yaw_samples.sort(
            key=lambda sample: (
                float(sample["absolute_yaw_error_degrees"]),
                int(sample["server_tick"]),
            )
        )
        aim_diagnostics_by_encounter.append(
            {
                "actor_id": encounter["actor_id"],
                "start_tick": start,
                "end_tick": end,
                "best_yaw_samples": yaw_samples[:12],
                "bearing_trace": [
                    [
                        int(sample["server_tick"]),
                        round(float(sample["bearing_degrees"]), 6),
                    ]
                    for sample in sorted(
                        yaw_samples,
                        key=lambda sample: int(sample["server_tick"]),
                    )
                ],
            }
        )
    kill_events = [item for item in damage_events if int(item.get("killed", 0))]
    player_scale = float(v8.PLAYER_MOTION_CONFIG["scale"])
    checks = {
        "no_fatal": not fatals,
        "state_count": len(states) == v8.base.capture.TOTAL_TICKS,
        "player_path": path_length >= 2200.0 * player_scale,
        "player_displacement_min": maximum_displacement >= 40.0 * player_scale,
        "player_displacement_max": maximum_displacement <= 500.0 * player_scale,
        "player_motion_duty": 0.70 <= motion_duty <= 0.92,
        "fired_every_encounter": len(fire_events) >= len(scenario["encounters"]),
        "damaged_every_encounter": bool(damage_by_encounter)
        and min(damage_by_encounter) >= 1,
        "exact_kill_count": len(kill_events) == int(row["kill_count"]),
    }
    report = {
        "schema_version": "xonotic-long60-v8-live-probe-v1",
        "episode_id": row["episode_id"],
        "map": map_only,
        "weapon": row["weapon"],
        "template": row["template"],
        "checks": checks,
        "passed": all(checks.values()),
        "state_count": len(states),
        "fatal_reasons": [item.get("reason") for item in fatals],
        "player_path_length_units": path_length,
        "player_maximum_displacement_units": maximum_displacement,
        "player_motion_duty_fraction": motion_duty,
        "fire_events": len(fire_events),
        "damage_events": len(damage_events),
        "damage_events_by_encounter": damage_by_encounter,
        "aim_diagnostics_by_encounter": aim_diagnostics_by_encounter,
        "kill_events": len(kill_events),
        "live_wall_seconds": live["live_wall_seconds"],
    }
    v8.prod.write_json_atomic(report_path.resolve(), report)
    print(json.dumps(report, sort_keys=True), flush=True)
    if not report["passed"]:
        raise RuntimeError(f"live probe failed: {map_only}: {checks}")


def run(
    artifact_root: Path,
    output_root: Path,
    scratch_root: Path,
    port: int,
    max_attempts: int,
    map_only: str | None,
) -> None:
    rows = v8.prod.load_jsonl(artifact_root.resolve() / "pilot_manifest.jsonl")
    if map_only is not None:
        rows = [row for row in rows if row["map"] == map_only]
        if not rows:
            raise RuntimeError(f"no review rows for map: {map_only}")
    rows.sort(key=lambda row: (str(row["map"]), int(row["pilot_index"])))
    build = ROOT / "build" / v8.BUILD_TAG
    if (build / "SOURCE_COMMIT").read_text(encoding="utf-8").strip() != v8.BUILD_COMMIT:
        raise RuntimeError(f"runtime build mismatch: {build}")
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lane: Any | None = None
    current_map: str | None = None
    generation = 0
    results: list[dict[str, Any]] = []
    try:
        for row in rows:
            scenario_path = ROOT / row["scenario_path"]
            if v8.base.sha256(scenario_path) != row["scenario_sha256"]:
                raise RuntimeError(f"scenario hash mismatch: {scenario_path}")
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            if lane is not None and current_map != row["map"]:
                lane.close()
                lane = None
                current_map = None
            accepted = False
            last_error = ""
            for attempt in range(1, max_attempts + 1):
                if lane is None:
                    generation += 1
                    lane = v8.base.reusable.ReusableStage1Lane(
                        scratch_root / f"resident-generation-{generation:03d}",
                        build=build,
                        port=port,
                    )
                    current_map = str(row["map"])
                try:
                    record = v8.run_attempt(
                        lane, row, scenario, output_root, scratch_root, attempt
                    )
                    paths = v8.prod.accepted_paths(output_root, row)
                    qa = json.loads(paths["qa"].read_text(encoding="utf-8"))
                    results.append(
                        {
                            "episode_id": row["episode_id"],
                            "map": row["map"],
                            "weapon": row["weapon"],
                            "template": row["template"],
                            "accepted": True,
                            "attempt": attempt,
                            "wall_seconds": record["wall_seconds"],
                            "camera_motion_v8": qa["camera_motion_v8"],
                            "render_tail_server_time_span_seconds": qa[
                                "render_tail_server_time_span_seconds"
                            ],
                        }
                    )
                    accepted = True
                    print(
                        json.dumps(
                            {
                                "progress": f"{len(results)}/{len(rows)}",
                                **results[-1],
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                    break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    traceback.print_exc()
                    if lane is not None:
                        lane.close()
                    lane = None
                    current_map = None
                    remove_transient_avis(scratch_root)
            if not accepted:
                results.append(
                    {
                        "episode_id": row["episode_id"],
                        "map": row["map"],
                        "weapon": row["weapon"],
                        "template": row["template"],
                        "accepted": False,
                        "attempt": max_attempts,
                        "error": last_error,
                    }
                )
    finally:
        if lane is not None:
            lane.close()
        remove_transient_avis(scratch_root)
    report = {
        "schema_version": "xonotic-long60-v8-review-report-v1",
        "pilot_id": PILOT_ID,
        "expected": len(rows),
        "accepted": sum(item["accepted"] for item in results),
        "all_pass": bool(results) and all(item["accepted"] for item in results),
        "results": results,
        "runtime_build": v8.BUILD_TAG,
        "runtime_source_commit": v8.BUILD_COMMIT,
        "raw_avi_retained": False,
        "training_admitted": False,
    }
    report_name = f"PILOT_REPORT.{map_only}.json" if map_only else "PILOT_REPORT.json"
    v8.prod.write_json_atomic(output_root / report_name, report)
    print(json.dumps(report, sort_keys=True), flush=True)
    if not report["all_pass"]:
        raise RuntimeError(
            f"review incomplete: {report['accepted']}/{report['expected']} accepted"
        )


def aggregate(output_root: Path) -> None:
    reports = [
        json.loads((output_root / f"PILOT_REPORT.{map_name}.json").read_text())
        for map_name in sorted(v8.MAPS)
    ]
    results = [item for report in reports for item in report["results"]]
    aggregate_report = {
        "schema_version": "xonotic-long60-v8-review-report-v1",
        "pilot_id": PILOT_ID,
        "expected": 12,
        "accepted": sum(item["accepted"] for item in results),
        "all_pass": len(results) == 12 and all(item["accepted"] for item in results),
        "results": results,
        "runtime_build": v8.BUILD_TAG,
        "runtime_source_commit": v8.BUILD_COMMIT,
        "raw_avi_retained": False,
        "training_admitted": False,
        "map_reports": [f"PILOT_REPORT.{name}.json" for name in sorted(v8.MAPS)],
    }
    v8.prod.write_json_atomic(output_root / "PILOT_REPORT.json", aggregate_report)
    print(json.dumps(aggregate_report, sort_keys=True))
    if not aggregate_report["all_pass"]:
        raise RuntimeError(
            "review aggregate incomplete: "
            f"{aggregate_report['accepted']}/{aggregate_report['expected']} accepted"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    r = sub.add_parser("run")
    r.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    r.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    r.add_argument("--scratch-root", type=Path, required=True)
    r.add_argument("--port", type=int, default=41800)
    r.add_argument("--max-attempts", type=int, default=2)
    r.add_argument("--map-only", choices=tuple(sorted(v8.MAPS)))
    a = sub.add_parser("aggregate")
    a.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    lp = sub.add_parser("live-probe")
    lp.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    lp.add_argument("--scratch-root", type=Path, required=True)
    lp.add_argument("--port", type=int, required=True)
    lp.add_argument("--map-only", choices=tuple(sorted(v8.MAPS)), required=True)
    lp.add_argument(
        "--template-only",
        choices=tuple(sorted(v8.v7.ORIGINAL_TEMPLATES)),
    )
    lp.add_argument("--weapon-only", choices=tuple(sorted(v8.WEAPONS)))
    lp.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.artifact_root)
    elif args.command == "run":
        run(
            args.artifact_root,
            args.output_root.resolve(),
            args.scratch_root.resolve(),
            args.port,
            args.max_attempts,
            args.map_only,
        )
    elif args.command == "aggregate":
        aggregate(args.output_root.resolve())
    else:
        live_probe(
            args.artifact_root,
            args.scratch_root,
            args.port,
            args.map_only,
            args.template_only,
            args.weapon_only,
            args.report,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
