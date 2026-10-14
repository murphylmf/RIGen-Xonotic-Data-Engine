                      
"""Balanced multi-map, instant-hit-weapon long60 ref42 production.

This is an isolated successor to ref42 v5.  It retains the proven capture,
acceleration, lifecycle, appearance-reference, retry, and no-AVI contracts,
while balancing three calibrated flat anchors and three instant-hit weapons.
"""

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import math
import random
import sys
import csv
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V5_PATH = Path(__file__).with_name("long60_production_ref42_v5.py")
SPEC = importlib.util.spec_from_file_location("long60_production_ref42_v5_base", V5_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import ref42 v5 module: {V5_PATH}")
v5 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v5
SPEC.loader.exec_module(v5)


RELEASE_ID = "stage2_long60_multi_enemy_ref42_multimap_hitscan_30h_20260828_v6"
SCHEMA_VERSION = "xonotic-stage2-long60-ref42-multimap-hitscan-production-manifest-v1"
EPISODE_PREFIX = "s2l60ref42mmhs_v6"
BUILD_TAG = "capture-9efed7e5733b-aarch64"
BUILD_COMMIT = "9efed7e5733bf6062865044060d4be390309958a"
CONFIG_PATH = ROOT / "configs" / "LONG60_MULTIMAP_HITSCAN_V6.json"
CONFIG_SHA256 = "73876b556bf9e86b7542323336794cda31d420c4f8776e25416158b01ce3fd03"
REFERENCE_ASSET_SOURCE_RELEASE_ID = "stage2_long60_multi_enemy_ref42_30h_20260828_v5"
REFERENCE_ROOT = Path("./rigen_data/reference_assets/xonotic_enemy_ref42_clean_v1")
ORIGINAL_PLAYER_MOTION_BASE_SPEED = float(base.PLAYER_MOTION_BASE_SPEED) if "base" in globals() else 70.0
ORIGINAL_PLAYER_MOTION_SPEED_MODULATION = float(base.PLAYER_MOTION_SPEED_MODULATION) if "base" in globals() else 10.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if sha256(CONFIG_PATH) != CONFIG_SHA256:
    raise RuntimeError("long60 multimap/hitscan config hash mismatch")
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
MAPS: dict[str, dict[str, Any]] = CONFIG["maps"]
WEAPONS: dict[str, dict[str, Any]] = CONFIG["weapons"]
if len(MAPS) != 3 or len(WEAPONS) != 3:
    raise RuntimeError("v6 requires exactly three maps and three weapons")
if not all(value.get("instant_hit") is True for value in WEAPONS.values()):
    raise RuntimeError("v6 weapon set must be instant-hit only")


prod = v5.v4.v3.prod
base = prod.base
lifecycle = prod.lifecycle

_v5_distribution_rows = v5.distribution_rows
_v5_actors_for_row = v5.actors_for_row
_v5_build_episode_scenario = v5.build_episode_scenario
_v5_deep_appearance_audit = v5.deep_appearance_audit
_v5_prepare = v5.prepare
_v5_validate_manifest = v5.validate_manifest
_v5_run_attempt = v5.run_attempt
_v3_finalize = v5._v3_finalize
_lifecycle_validate_episode = lifecycle.lifecycle_validate_episode


                                                                               
for module in (v5, v5.v4, v5.v4.v3, prod):
    module.RELEASE_ID = RELEASE_ID
    module.SCHEMA_VERSION = SCHEMA_VERSION
v5.EPISODE_PREFIX = EPISODE_PREFIX
v5.v4.EPISODE_PREFIX = EPISODE_PREFIX
prod.BUILD_TAG = BUILD_TAG
prod.BUILD_COMMIT = BUILD_COMMIT
prod.DEFAULT_MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
prod.DEFAULT_OUTPUT_ROOT = Path("./rigen_data") / RELEASE_ID


def environment_weapon_text(map_name: str, weapon_name: str) -> str:
    return (
        "[ENVIRONMENT STYLE AND OBJECTS]\n"
        f"{MAPS[map_name]['environment_text']}\n"
        "[ACTIVE WEAPON]\n"
        f"The active weapon is {weapon_name}. Its appearance is described as: "
        f"{WEAPONS[weapon_name]['weapon_text']}"
    )


def configure_geometry_and_weapon(row: dict[str, Any]) -> None:
    map_config = MAPS[str(row["map"])]
    weapon_name = str(row["weapon"])
    player = tuple(float(value) for value in map_config["player_origin"])
    enemy = tuple(float(value) for value in map_config["enemy_reference_origin"])
    angle = math.degrees(math.atan2(enemy[1] - player[1], enemy[0] - player[0]))
    base.PLAYER_ORIGIN = player
    base.BASE_ENEMY_ORIGIN = enemy
    base.BASE_ANGLE_DEGREES = angle
    trajectory_scale = float(
        row.get("trajectory_scale", map_config.get("trajectory_scale", 1.0))
    )
    base.PLAYER_MOTION_BASE_SPEED = (
        ORIGINAL_PLAYER_MOTION_BASE_SPEED * trajectory_scale
    )
    base.PLAYER_MOTION_SPEED_MODULATION = (
        ORIGINAL_PLAYER_MOTION_SPEED_MODULATION * trajectory_scale
    )
    base.ENVIRONMENT_TEXT = environment_weapon_text(str(row["map"]), weapon_name)


def distribution_rows() -> list[dict[str, Any]]:
    rows = _v5_distribution_rows()
    combinations = list(itertools.product(sorted(MAPS), sorted(WEAPONS)))
    for template in sorted(prod.TEMPLATES):
        indices = [index for index, row in enumerate(rows) if row["template"] == template]
        if len(indices) != 900:
            raise RuntimeError(f"{template}: expected 900 rows, found {len(indices)}")
        assignments = combinations * 100
        random.Random(2608286601 + sum(ord(c) for c in template)).shuffle(assignments)
        for index, (map_name, weapon_name) in zip(indices, assignments, strict=True):
            row = rows[index]
            row.update(
                {
                    "map": map_name,
                    "gametype": MAPS[map_name]["gametype"],
                    "anchor_id": MAPS[map_name]["anchor_id"],
                    "weapon": weapon_name,
                    "weapon_netname": WEAPONS[weapon_name]["weapon_netname"],
                    "instant_hit_weapon": True,
                    "geometry_config_sha256": CONFIG_SHA256,
                }
            )
    for index, row in enumerate(rows):
        row["schema_version"] = SCHEMA_VERSION
        row["release_id"] = RELEASE_ID
        row["manifest_index"] = index
        row["episode_id"] = f"{EPISODE_PREFIX}_{index:06d}"
    return rows


def actors_for_row(row: dict[str, Any]) -> tuple[Any, ...]:
    actors = list(_v5_actors_for_row(row))
    kill_slots = {int(value) for value in row["kill_slots"]}
    for index, actor in enumerate(actors):
        slot = int(actor.slot)
        health = 999.0
        if slot in kill_slots:
            if row["template"] == "controlled_return" and slot == 1:
                health = float(
                    WEAPONS[str(row["weapon"])]["controlled_return_slot1_kill_health"]
                )
            else:
                health = 10.0
        actors[index] = replace(actor, health=health)
    return tuple(actors)


def rewrite_prompt_weapon(schedule: list[dict[str, Any]], weapon_name: str) -> None:
    for block in schedule:
        block["prompt"] = str(block["prompt"]).replace(
            "The player fires the MachineGun", f"The player fires the {weapon_name}"
        )


def build_episode_scenario(
    row: dict[str, Any], manifest_root: Path, shared_actions: Path
) -> tuple[Path, Path]:
    configure_geometry_and_weapon(row)
    scenario_path, timeline = _v5_build_episode_scenario(
        row, manifest_root, shared_actions
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))

                                                                              
                                                                             
                                                         
    segments = prod.TEMPLATES[str(row["template"])]
    base.write_timeline(timeline, segments)
    v5.v4.prime_timeline(timeline)
    rewrite_prompt_weapon(scenario["prompt_schedule"], str(row["weapon"]))
    map_config = MAPS[str(row["map"])]
    weapon_config = WEAPONS[str(row["weapon"])]
    scenario.update(
        {
            "schema_version": "xonotic-stage2-long60-ref42-multimap-hitscan-production-scenario-v1",
            "release_id": RELEASE_ID,
            "map": row["map"],
            "gametype": row["gametype"],
            "anchor_id": row["anchor_id"],
            "weapon": row["weapon"],
            "weapon_netname": row["weapon_netname"],
            "instant_hit_weapon": True,
            "trajectory_scale": float(row.get("trajectory_scale", 1.0)),
            "geometry_config_path": str(CONFIG_PATH),
            "geometry_config_sha256": CONFIG_SHA256,
            "enemy_timeline_sha256": prod.base.sha256(timeline),
            "environment_prompt_provenance_sample_id": map_config[
                "prompt_provenance_sample_id"
            ],
            "weapon_prompt_provenance_sample_id": weapon_config[
                "prompt_provenance_sample_id"
            ],
        }
    )
    scenario["distribution"].update(
        {
            "map": row["map"],
            "weapon": row["weapon"],
            "instant_hit_weapon": True,
            "trajectory_scale": float(row.get("trajectory_scale", 1.0)),
        }
    )
    scenario["player_action_policy"].update(
        {
            "weapon": row["weapon"],
            "fire_input_policy": "fixed_56_tick_primary_hold_per_declared_interaction",
        }
    )
    scenario.setdefault("lifecycle_policy", {}).update(
        {
            "weapon_specific_health_calibration": True,
            "controlled_return_slot1_kill_health": weapon_config[
                "controlled_return_slot1_kill_health"
            ],
            "exact_telemetry_hit_and_kill_required": True,
        }
    )
    prod.write_json_atomic(scenario_path, scenario)
    return scenario_path, timeline


def deep_appearance_audit(
    manifest_root: Path, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    report = _v5_deep_appearance_audit(manifest_root, rows)
    template_map_weapon = Counter(
        (row["template"], row["map"], row["weapon"]) for row in rows
    )
    map_weapon = Counter((row["map"], row["weapon"]) for row in rows)
    maps = Counter(row["map"] for row in rows)
    weapons = Counter(row["weapon"] for row in rows)
    scenario_contract = True
    health_contract = True
    errors = list(report.get("errors") or [])
    for row in rows:
        scenario = json.loads((ROOT / row["scenario_path"]).read_text(encoding="utf-8"))
        expected_prefix = environment_weapon_text(row["map"], row["weapon"])
        scenario_contract = scenario_contract and (
            scenario.get("map") == row["map"]
            and scenario.get("weapon") == row["weapon"]
            and scenario.get("instant_hit_weapon") is True
            and all(
                str(block["prompt"]).startswith(expected_prefix)
                and "fires the MachineGun" not in str(block["prompt"])
                if row["weapon"] != "MachineGun"
                else str(block["prompt"]).startswith(expected_prefix)
                for block in scenario["prompt_schedule"]
            )
        )
        kill_slots = {int(value) for value in row["kill_slots"]}
        for actor in scenario["actors"]:
            slot = int(actor["slot"])
            expected_health = 999.0
            if slot in kill_slots:
                expected_health = (
                    float(WEAPONS[row["weapon"]]["controlled_return_slot1_kill_health"])
                    if row["template"] == "controlled_return" and slot == 1
                    else 10.0
                )
            if not math.isclose(float(actor["health"]), expected_health, abs_tol=1e-6):
                health_contract = False
                if len(errors) < 100:
                    errors.append(f"{row['episode_id']}:{actor['actor_id']}:health")
    checks = {
        "three_maps_balanced_600_each": maps == Counter({name: 600 for name in MAPS}),
        "three_hitscan_weapons_balanced_600_each": weapons
        == Counter({name: 600 for name in WEAPONS}),
        "nine_map_weapon_cells_200_each": len(map_weapon) == 9
        and set(map_weapon.values()) == {200},
        "eighteen_template_map_weapon_cells_100_each": len(template_map_weapon) == 18
        and set(template_map_weapon.values()) == {100},
        "all_weapons_instant_hit": all(row.get("instant_hit_weapon") is True for row in rows),
        "scenario_map_weapon_prompt_contract": scenario_contract,
        "weapon_specific_health_contract": health_contract,
    }
    report["schema_version"] = "xonotic-stage2-long60-ref42-multimap-hitscan-static-validation-v1"
    report["errors"] = errors
    report["checks"].update(checks)
    report.setdefault("distribution", {}).update(
        {
            "map": dict(sorted(maps.items())),
            "weapon": dict(sorted(weapons.items())),
            "map_weapon": {"/".join(key): value for key, value in sorted(map_weapon.items())},
            "template_map_weapon": {
                "/".join(key): value for key, value in sorted(template_map_weapon.items())
            },
        }
    )
    report["all_pass"] = all(report["checks"].values()) and not errors
    return report


def prepare(manifest_root: Path) -> None:
    _v5_prepare(manifest_root)
    metadata_path = manifest_root.resolve() / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = prod.load_jsonl(manifest_root.resolve() / "manifest.jsonl")
    metadata.update(
        {
            "release_id": RELEASE_ID,
            "geometry_config_path": str(CONFIG_PATH),
            "geometry_config_sha256": CONFIG_SHA256,
            "maps": dict(Counter(row["map"] for row in rows)),
            "weapons": dict(Counter(row["weapon"] for row in rows)),
            "instant_hit_weapons_only": True,
            "map_weapon_distribution": {
                "/".join(key): value
                for key, value in sorted(Counter((row["map"], row["weapon"]) for row in rows).items())
            },
            "source_short_prompt_manifest": CONFIG["source_short_ar_manifest"],
            "source_short_prompt_manifest_sha256": CONFIG[
                "source_short_ar_manifest_sha256"
            ],
        }
    )
    prod.write_json_atomic(metadata_path, metadata)
    prepared_path = manifest_root.resolve() / "PREPARED.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared.update(
        {
            "release_id": RELEASE_ID,
            "geometry_config_sha256": CONFIG_SHA256,
            "multimap_hitscan_ready": True,
        }
    )
    prod.write_json_atomic(prepared_path, prepared)


def validate_manifest(
    manifest_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, metadata = _v5_validate_manifest(manifest_root)
    checks = {
        "release_id": metadata.get("release_id") == RELEASE_ID,
        "geometry_config": metadata.get("geometry_config_sha256") == CONFIG_SHA256,
        "instant_hit_only": metadata.get("instant_hit_weapons_only") is True,
        "episode_ids": all(
            row["episode_id"] == f"{EPISODE_PREFIX}_{index:06d}"
            for index, row in enumerate(rows)
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"v6 manifest validation failed: {checks}")
    return rows, metadata


def validate_episode_multimap_hitscan(*args: Any, **kwargs: Any) -> dict[str, Any]:
    scenario = args[0] if args else kwargs["scenario"]
    live = args[2] if len(args) >= 3 else kwargs["live"]
    render = args[3] if len(args) >= 4 else kwargs["render"]
    qa = _lifecycle_validate_episode(*args, **kwargs)
    checks = qa["checks"]
    legacy_fire_check = checks.pop("multiple_machinegun_shots_per_encounter", None)
    fire_events = int(qa["counts"].get("machinegun_fire_events", 0))
    qa["counts"]["weapon_fire_events"] = fire_events
    checks["selected_weapon_is_declared_instant_hit"] = (
        scenario.get("instant_hit_weapon") is True
        and scenario.get("weapon") in WEAPONS
    )
    checks["weapon_fired_in_every_declared_encounter"] = fire_events >= len(
        scenario["encounters"]
    )
    if scenario.get("weapon") == "MachineGun":
        checks["machinegun_multishot_contract"] = legacy_fire_check is True
    qa["weapon"] = {
        "name": scenario["weapon"],
        "netname": scenario["weapon_netname"],
        "instant_hit": True,
    }
    qa["map"] = {
        "name": scenario["map"],
        "anchor_id": scenario["anchor_id"],
        "geometry_config_sha256": CONFIG_SHA256,
        "trajectory_scale": float(scenario.get("trajectory_scale", 1.0)),
    }
    telemetry = prod.load_jsonl(Path(live["server_telemetry"]))
    reset = next((row for row in telemetry if row.get("kind") == "reset"), {})
    player_entity = int(reset.get("player_entity", -1))
    enemy_entity = int(reset.get("enemy_entity", -1))
    events = [row for row in telemetry if row.get("kind") == "event"]
    qa["weapon_timing"] = {
        "fire_server_ticks": [
            int(row["server_tick"])
            for row in events
            if row.get("event") == "fire"
            and int(row.get("actor", -1)) == player_entity
        ],
        "enemy_damage_server_ticks": [
            int(row["server_tick"])
            for row in events
            if row.get("event") == "damage"
            and int(row.get("attacker", -1)) == player_entity
            and int(row.get("target", -1)) == enemy_entity
        ],
    }
    trajectory_scale = float(scenario.get("trajectory_scale", 1.0))
    expected_enemy_speed = float(base.ENEMY_HORIZONTAL_SPEED) * trajectory_scale
    timeline_speeds: list[float] = []
    with (ROOT / scenario["enemy_timeline_path"]).open(
        newline="", encoding="utf-8"
    ) as handle:
        for row in csv.DictReader(handle):
            if row["kind"] != "tick" or int(row["actor_or_id"]) == 0:
                continue
            timeline_speeds.append(
                math.hypot(
                    float(row["vx_or_health"]),
                    float(row["vy_or_armor"]),
                )
            )
    checks["fixed_enemy_commanded_horizontal_speed"] = bool(timeline_speeds) and max(
        abs(value - expected_enemy_speed) for value in timeline_speeds
    ) <= 0.01
    kill_records = list((qa.get("lifecycle") or {}).get("kill_records") or [])
    expected_kill_count = sum(
        encounter.get("intent_outcome") == "kill"
        for encounter in scenario["encounters"]
    )
    checks["enemy_moving_immediately_before_every_kill"] = (
        expected_kill_count == 0
        or len(kill_records) == expected_kill_count
        and all(
            float(row["enemy_predeath_horizontal_speed"])
            >= expected_enemy_speed - 1.0
            for row in kill_records
        )
    )
    motion = qa["player_motion"]
    checks["visible_player_displacement"] = (
        float(motion["horizontal_path_length_units"]) >= 2200.0 * trajectory_scale
        and float(motion["maximum_displacement_from_anchor_units"])
        >= 40.0 * trajectory_scale
    )
    checks["player_remains_in_local_encounter_area"] = (
        float(motion["maximum_displacement_from_anchor_units"])
        <= 500.0 * trajectory_scale
    )
    with Path(render["frames_engine"]).open(newline="", encoding="utf-8") as handle:
        frame_rows = list(csv.DictReader(handle))
    frame_server_times = [float(row["server_time_current"]) for row in frame_rows]
    qa["render_timing_diagnostic"] = {
        "first_server_time": frame_server_times[0] if frame_server_times else None,
        "last_server_time": frame_server_times[-1] if frame_server_times else None,
        "last_64_span_seconds": (
            frame_server_times[-1] - frame_server_times[-64]
            if len(frame_server_times) >= 64
            else None
        ),
    }
    qa["passed"] = all(checks.values())
    return qa


def run_attempt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    row = args[1] if len(args) >= 2 else kwargs["row"]
    output_root = args[3] if len(args) >= 4 else kwargs["output_root"]
    configure_geometry_and_weapon(row)
    record = _v5_run_attempt(*args, **kwargs)
    record.update(
        {
            "map": row["map"],
            "gametype": row["gametype"],
            "anchor_id": row["anchor_id"],
            "weapon": row["weapon"],
            "weapon_netname": row["weapon_netname"],
            "instant_hit_weapon": True,
            "geometry_config_sha256": CONFIG_SHA256,
        }
    )
    paths = prod.accepted_paths(output_root, row)
    prod.write_json_atomic(paths["record"], record)
    prod.write_json_atomic(paths["accepted"], record)
    return record


def finalize(manifest_root: Path, output_root: Path) -> None:
                                                                             
                                                                            
                                                        
    _v3_finalize(manifest_root, output_root)
    release_path = REFERENCE_ROOT / "RELEASE.json"
    reference_release = json.loads(release_path.read_text(encoding="utf-8"))
    reference_manifest = Path(reference_release["reference_manifest_path"])
    reference_rows = prod.load_jsonl(reference_manifest)
    appearances = {row["appearance_id"] for row in reference_rows}
    checks = {
        "reference_ready": reference_release.get("reference_ready") is True,
        "reference_source_release_is_v5": reference_release.get("target_release_id")
        == REFERENCE_ASSET_SOURCE_RELEASE_ID,
        "appearance_only_reuse_is_map_weapon_independent": True,
        "appearance_count": len(appearances) == 42,
        "image_count": len(reference_rows) == 210,
        "five_views_each": all(
            sum(row["appearance_id"] == appearance for row in reference_rows) == 5
            for appearance in appearances
        ),
        "runtime_build": Path(reference_release.get("runtime_build", "")).name
        == BUILD_TAG,
        "runtime_commit": reference_release.get("runtime_source_commit") == BUILD_COMMIT,
        "manifest_hash": reference_manifest.is_file()
        and prod.base.sha256(reference_manifest)
        == reference_release.get("reference_manifest_sha256"),
        "raw_avi_absent": not any(REFERENCE_ROOT.rglob("*.avi")),
    }
    if not all(checks.values()):
        raise RuntimeError(f"v6 reference reuse validation failed: {checks}")

    accepted_path = output_root / "accepted.jsonl"
    accepted = prod.load_jsonl(accepted_path)
    bound = {
        binding["appearance_id"]
        for row in accepted
        for binding in row["actor_bindings"]
    }
    if bound != appearances:
        raise RuntimeError("v6 accepted appearances do not match reference bank")
    for row in accepted:
        row.update(
            {
                "ref_assets_ready": True,
                "reference_release_path": str(release_path),
                "reference_manifest_path": str(reference_manifest),
                "reference_manifest_sha256": reference_release[
                    "reference_manifest_sha256"
                ],
                "reference_asset_source_release_id": REFERENCE_ASSET_SOURCE_RELEASE_ID,
                "reference_asset_reuse_scope": "appearance_identity_only_map_weapon_independent",
            }
        )
    prod.write_jsonl_atomic(accepted_path, accepted)
    accepted_sha256 = prod.base.sha256(accepted_path)
    binding_report = {
        "schema_version": "xonotic-current-enemy-ref-release-binding-v2",
        "created_utc": prod.utc_now(),
        "release_id": RELEASE_ID,
        "ready": True,
        "checks": checks,
        "accepted_count": len(accepted),
        "appearance_count": len(appearances),
        "reference_image_count": len(reference_rows),
        "reference_release_path": str(release_path),
        "reference_manifest_path": str(reference_manifest),
        "reference_manifest_sha256": reference_release[
            "reference_manifest_sha256"
        ],
        "reference_asset_source_release_id": REFERENCE_ASSET_SOURCE_RELEASE_ID,
        "training_admitted": False,
    }
    prod.write_json_atomic(output_root / "REFERENCE_CONDITIONING_READY.json", binding_report)
    for name in ("COLLECTION_STATUS.json", "COLLECTION_COMPLETE.json"):
        path = output_root / name
        report = json.loads(path.read_text(encoding="utf-8"))
        report.update(
            {
                "accepted_manifest_sha256": accepted_sha256,
                "ref_assets_ready": True,
                "reference_release_path": str(release_path),
                "reference_manifest_path": str(reference_manifest),
                "reference_manifest_sha256": reference_release[
                    "reference_manifest_sha256"
                ],
                "reference_asset_source_release_id": REFERENCE_ASSET_SOURCE_RELEASE_ID,
                "geometry_config_sha256": CONFIG_SHA256,
                "maps": dict(Counter(row["map"] for row in accepted)),
                "weapons": dict(Counter(row["weapon"] for row in accepted)),
            }
        )
        prod.write_json_atomic(path, report)


lifecycle.lifecycle_validate_episode = validate_episode_multimap_hitscan
v5.v4.v3.deep_appearance_audit = deep_appearance_audit
prod.distribution_rows = distribution_rows
prod.actors_for_row = actors_for_row
prod.build_episode_scenario = build_episode_scenario
prod.prepare = prepare
prod.validate_manifest = validate_manifest
prod.run_attempt = run_attempt
prod.finalize = finalize


def main() -> int:
    return prod.main()


if __name__ == "__main__":
    raise SystemExit(main())
