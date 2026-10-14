                      
"""Ref42 long60 production with runtime-locked actor appearance identity.

The previous runtime let normal per-frame bot maintenance overwrite timeline
model changes.  V4 requires the patched capture build that locks the reusable
timeline entity's model/skin/color.  It also primes actor 0 during unpublished
warmup and despawns it at the published-video boundary, keeping the original
60 s prompt/action schedule unchanged.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V3_PATH = Path(__file__).with_name("long60_production_ref42_v3.py")
SPEC = importlib.util.spec_from_file_location("long60_production_ref42_v3_base", V3_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import ref42 v3 module: {V3_PATH}")
v3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v3
SPEC.loader.exec_module(v3)


RELEASE_ID = "stage2_long60_multi_enemy_ref42_30h_20260828_v4"
SCHEMA_VERSION = "xonotic-stage2-long60-ref42-production-manifest-v2"
EPISODE_PREFIX = "s2l60ref42_v4"
SPAWN_POLICY = "warmup_prime_output_boundary_despawn_v1"
BUILD_TAG = "capture-e219ab01ae71-aarch64"
BUILD_COMMIT = "e219ab01ae713ad7be9404278ad1f5f377d173dc"
KILLED_AIM_REGION_MAX_DEGREES = 12.0

_v3_distribution_rows = v3.distribution_rows
_v3_build_episode_scenario = v3.build_episode_scenario
_v3_deep_appearance_audit = v3.deep_appearance_audit
_v3_prepare = v3.prepare
_v3_validate_manifest = v3.validate_manifest
_v3_run_attempt = v3.run_attempt

                                                                           
v3.RELEASE_ID = RELEASE_ID
v3.SCHEMA_VERSION = SCHEMA_VERSION
v3.prod.RELEASE_ID = RELEASE_ID
v3.prod.SCHEMA_VERSION = SCHEMA_VERSION
v3.prod.BUILD_TAG = BUILD_TAG
v3.prod.BUILD_COMMIT = BUILD_COMMIT
v3.prod.DEFAULT_MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
v3.prod.DEFAULT_OUTPUT_ROOT = Path("./rigen_data") / RELEASE_ID


def distribution_rows() -> list[dict[str, Any]]:
    rows = _v3_distribution_rows()
    for index, row in enumerate(rows):
        row["schema_version"] = SCHEMA_VERSION
        row["release_id"] = RELEASE_ID
        row["episode_id"] = f"{EPISODE_PREFIX}_{index:06d}"
        row["first_actor_spawn_policy"] = SPAWN_POLICY
    return rows


def prime_timeline(timeline: Path) -> None:
    """Prime actor 0 in warmup, then despawn it at output frame zero."""
    with timeline.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError(f"timeline has no header: {timeline}")

    warmup_ticks = int(v3.prod.base.capture.WARMUP_TICKS)
    ticks = [row for row in rows if row["kind"] == "tick"]
    if len(ticks) != int(v3.prod.base.capture.TOTAL_TICKS):
        raise RuntimeError(f"unexpected timeline tick count: {timeline}")
    by_tick = {int(row["tick_or_slot"]): row for row in ticks}
    output_start = by_tick[warmup_ticks]
    if output_start["actor_or_id"] != "0":
        raise RuntimeError(
            f"first output tick must have no enemy before priming: {timeline}"
        )
    prototype = next(
        row
        for row in ticks
        if int(row["tick_or_slot"]) > warmup_ticks
        and row["actor_or_id"] == "1"
    )
    for tick in range(warmup_ticks):
        row = by_tick[tick]
        row.update(
            {
                "actor_or_id": "1",
                "x_or_model": prototype["x_or_model"],
                "y_or_skin": prototype["y_or_skin"],
                "z_or_color": prototype["z_or_color"],
                                                                           
                                                                          
                                                                            
                "vx_or_health": prototype["vx_or_health"],
                "vy_or_armor": prototype["vy_or_armor"],
                "vz": "0.0",
                "yaw": prototype["yaw"],
                "jump": "0",
            }
        )

    temporary = timeline.with_name(f".{timeline.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        for row in rows:
            values = [row.get(field) for field in fieldnames]
                                                                            
                                                                             
                                                                          
            if row["kind"] == "actor":
                values = values[:8]
            writer.writerow(values)
    os.replace(temporary, timeline)


def timeline_is_primed(timeline: Path) -> bool:
    with timeline.open(newline="", encoding="utf-8") as handle:
        all_rows = list(csv.DictReader(handle))
    actor_rows = [row for row in all_rows if row["kind"] == "actor"]
    rows = [row for row in all_rows if row["kind"] == "tick"]
    warmup_ticks = int(v3.prod.base.capture.WARMUP_TICKS)
    by_tick = {int(row["tick_or_slot"]): row for row in rows}
    return (
        bool(actor_rows)
        and all(
            row["vz"] is None and row["yaw"] is None and row["jump"] is None
            for row in actor_rows
        )
        and len(rows) == int(v3.prod.base.capture.TOTAL_TICKS)
        and all(by_tick[tick]["actor_or_id"] == "1" for tick in range(warmup_ticks))
        and by_tick[warmup_ticks]["actor_or_id"] == "0"
        and any(
            int(row["tick_or_slot"]) > warmup_ticks
            and row["actor_or_id"] == "1"
            for row in rows
        )
    )


def materialize_episode_timeline(
    source_timeline: Path,
    destination: Path,
    scenario: dict[str, Any],
) -> Path:
    """Bind the scenario's four appearances into its own runtime timeline."""
    with source_timeline.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError(f"timeline has no header: {source_timeline}")
    actors = {int(actor["slot"]): actor for actor in scenario["actors"]}
    actor_rows = [row for row in rows if row["kind"] == "actor"]
    if set(actors) != {
        int(row["tick_or_slot"]) for row in actor_rows
    }:
        raise RuntimeError(
            f"timeline actor slots do not match scenario: {source_timeline}"
        )
    for row in actor_rows:
        actor = actors[int(row["tick_or_slot"])]
        row.update(
            {
                "actor_or_id": actor["actor_id"],
                "x_or_model": actor["model"],
                "y_or_skin": str(actor["skin"]),
                "z_or_color": str(actor["color"]),
                "vx_or_health": str(actor["health"]),
                "vy_or_armor": str(actor["armor"]),
            }
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        for row in rows:
            values = [row.get(field) for field in fieldnames]
            if row["kind"] == "actor":
                values = values[:8]
            writer.writerow(values)
    os.replace(temporary, destination)
    prime_timeline(destination)
    return destination


def timeline_actors_match_scenario(
    timeline: Path, scenario: dict[str, Any]
) -> bool:
    with timeline.open(newline="", encoding="utf-8") as handle:
        actor_rows = [
            row for row in csv.DictReader(handle) if row["kind"] == "actor"
        ]
    expected = {int(actor["slot"]): actor for actor in scenario["actors"]}
    if set(expected) != {
        int(row["tick_or_slot"]) for row in actor_rows
    }:
        return False
    for row in actor_rows:
        actor = expected[int(row["tick_or_slot"])]
        if not (
            row["actor_or_id"] == actor["actor_id"]
            and row["x_or_model"] == actor["model"]
            and int(row["y_or_skin"]) == int(actor["skin"])
            and int(row["z_or_color"]) == int(actor["color"])
            and abs(float(row["vx_or_health"]) - float(actor["health"])) < 1e-6
            and abs(float(row["vy_or_armor"]) - float(actor["armor"])) < 1e-6
            and row["vz"] is None
            and row["yaw"] is None
            and row["jump"] is None
        ):
            return False
    return True


def build_episode_scenario(
    row: dict[str, Any], manifest_root: Path, shared_actions: Path
) -> tuple[Path, Path]:
    scenario_path, source_timeline = _v3_build_episode_scenario(
        row, manifest_root, shared_actions
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    timeline = materialize_episode_timeline(
        source_timeline,
        manifest_root / "episode_timelines" / f"{row['episode_id']}.csv",
        scenario,
    )
    scenario.update(
        {
            "schema_version": "xonotic-stage2-long60-ref42-production-scenario-v2",
            "release_id": RELEASE_ID,
            "enemy_timeline_sha256": v3.prod.base.sha256(timeline),
            "first_actor_spawn_calibration": {
                "schema_version": "xonotic-first-actor-spawn-calibration-v1",
                "policy": SPAWN_POLICY,
                "primed_actor_id": row["actor_order"][0],
                "primed_actor_slot": 1,
                "warmup_ticks": int(v3.prod.base.capture.WARMUP_TICKS),
                "published_output_start_tick": int(v3.prod.base.capture.WARMUP_TICKS),
                "output_starts_with_enemy_absent": True,
                "first_encounter_requires_respawn": True,
            },
        }
    )
                                                                              
                                                                             
                                                                            
                                                     
    scenario.setdefault("lifecycle_policy", {}).update(
        {
            "killed_aim_region_max_degrees": KILLED_AIM_REGION_MAX_DEGREES,
            "appearance_aware_aim_tolerance": True,
        }
    )
    scenario["enemy_timeline_path"] = v3.prod.relative_to_root(timeline)
    scenario["reference_conditioning_contract"].update(
        {
            "first_actor_spawn_policy": SPAWN_POLICY,
            "all_actor_appearances_require_respawn_realization": True,
        }
    )
    v3.prod.write_json_atomic(scenario_path, scenario)
    return scenario_path, timeline


def deep_appearance_audit(
    manifest_root: Path, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    report = _v3_deep_appearance_audit(manifest_root, rows)
    timeline_results: dict[str, bool] = {}
    timeline_actor_results: dict[str, bool] = {}
    scenario_ok = True
    errors = list(report.get("errors") or [])
    for row in rows:
        scenario_path = ROOT / row["scenario_path"]
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        calibration = scenario.get("first_actor_spawn_calibration") or {}
        if not (
            calibration.get("policy") == SPAWN_POLICY
            and calibration.get("primed_actor_id") == row["actor_order"][0]
            and calibration.get("output_starts_with_enemy_absent") is True
        ):
            scenario_ok = False
            if len(errors) < 100:
                errors.append(f"{row['episode_id']}:first_actor_spawn_calibration")
        timeline_path = ROOT / row["timeline_path"]
        key = str(timeline_path)
        if key not in timeline_results:
            timeline_results[key] = timeline_is_primed(timeline_path)
            timeline_actor_results[key] = timeline_actors_match_scenario(
                timeline_path, scenario
            )
    report["schema_version"] = "xonotic-stage2-long60-ref42-static-validation-v2"
    report["errors"] = errors
    report["checks"].update(
        {
            "all_scenarios_have_first_actor_spawn_calibration": scenario_ok,
            "all_unique_timelines_warmup_primed": all(timeline_results.values()),
            "output_frame_zero_has_no_enemy": all(timeline_results.values()),
            "all_timeline_actor_rows_match_scenarios": all(
                timeline_actor_results.values()
            ),
        }
    )
    report["unique_timeline_count"] = len(timeline_results)
    report["first_actor_spawn_policy"] = SPAWN_POLICY
    report["all_pass"] = all(report["checks"].values()) and not errors
    return report


def prepare(manifest_root: Path) -> None:
    _v3_prepare(manifest_root)
    metadata_path = manifest_root.resolve() / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "release_id": RELEASE_ID,
            "first_actor_spawn_policy": SPAWN_POLICY,
            "first_actor_spawn_calibrated": True,
            "v3_capture_reuse_allowed": False,
            "killed_aim_region_max_degrees": KILLED_AIM_REGION_MAX_DEGREES,
            "killed_aim_region_tolerance_scope": "ref42_v4_only",
        }
    )
    v3.prod.write_json_atomic(metadata_path, metadata)
    prepared_path = manifest_root.resolve() / "PREPARED.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared.update(
        {
            "release_id": RELEASE_ID,
            "first_actor_spawn_policy": SPAWN_POLICY,
            "first_actor_spawn_calibrated": True,
        }
    )
    v3.prod.write_json_atomic(prepared_path, prepared)


def validate_manifest(
    manifest_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, metadata = _v3_validate_manifest(manifest_root)
    checks = {
        "release_id": metadata.get("release_id") == RELEASE_ID,
        "spawn_policy": metadata.get("first_actor_spawn_policy") == SPAWN_POLICY,
        "spawn_calibrated": metadata.get("first_actor_spawn_calibrated") is True,
        "episode_ids": all(
            row["episode_id"] == f"{EPISODE_PREFIX}_{index:06d}"
            for index, row in enumerate(rows)
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"v4 manifest validation failed: {checks}")
    return rows, metadata


def run_attempt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    row = args[1] if len(args) >= 2 else kwargs["row"]
    output_root = args[3] if len(args) >= 4 else kwargs["output_root"]
    record = _v3_run_attempt(*args, **kwargs)
    record.update(
        {
            "first_actor_spawn_policy": SPAWN_POLICY,
            "first_actor_spawn_calibrated": True,
        }
    )
    paths = v3.prod.accepted_paths(output_root, row)
    v3.prod.write_json_atomic(paths["record"], record)
    v3.prod.write_json_atomic(paths["accepted"], record)
    return record


v3.deep_appearance_audit = deep_appearance_audit
v3.prod.distribution_rows = distribution_rows
v3.prod.build_episode_scenario = build_episode_scenario
v3.prod.prepare = prepare
v3.prod.validate_manifest = validate_manifest
v3.prod.run_attempt = run_attempt


def main() -> int:
    return v3.prod.main()


if __name__ == "__main__":
    raise SystemExit(main())
