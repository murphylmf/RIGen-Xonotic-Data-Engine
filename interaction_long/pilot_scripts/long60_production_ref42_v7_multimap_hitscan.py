                      
"""Four-map, three-hitscan-weapon long60 ref42 production.

This successor is isolated from v5/v6.  It keeps the proven ref42 lifecycle,
accelerated render, and no-AVI publication contracts, but makes map and weapon
variation real in both runtime inputs and prompts.  Each map has its own
calibrated geometry/actions; semi-automatic hitscan weapons fire at calibrated
crosshair-crossing ticks instead of inheriting the MachineGun hold onset.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import itertools
import json
import math
import os
import random
import sys
import time
import traceback
import zipfile
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V6_PATH = Path(__file__).with_name(
    "long60_production_ref42_v6_multimap_hitscan.py"
)
SPEC = importlib.util.spec_from_file_location("long60_ref42_v7_base", V6_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v6 module: {V6_PATH}")
v6 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v6
SPEC.loader.exec_module(v6)


RELEASE_ID = "stage2_long60_multi_enemy_ref42_multimap_hitscan_30h_20260828_v7"
SCHEMA_VERSION = "xonotic-stage2-long60-ref42-multimap-hitscan-production-manifest-v3"
EPISODE_PREFIX = "s2l60ref42mmhs_v7"
BUILD_TAG = "capture-9efed7e5733b-aarch64"
BUILD_COMMIT = "9efed7e5733bf6062865044060d4be390309958a"
CONFIG_PATH = ROOT / "configs" / "LONG60_MULTIMAP_HITSCAN_V7.json"
CONFIG_SHA256 = "5f00b7c6b2f09bd15b5fb5a5d878028ac1d4e3e64fd0344b2f3c08fd62118484"
REFERENCE_ASSET_SOURCE_RELEASE_ID = "stage2_long60_multi_enemy_ref42_30h_20260828_v5"
REFERENCE_ROOT = Path("./rigen_data/reference_assets/xonotic_enemy_ref42_clean_v1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if sha256(CONFIG_PATH) != CONFIG_SHA256:
    raise RuntimeError("long60 v7 multimap/hitscan config hash mismatch")
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
MAPS: dict[str, dict[str, Any]] = CONFIG["maps"]
WEAPONS: dict[str, dict[str, Any]] = CONFIG["weapons"]
if len(MAPS) != 4 or len(WEAPONS) != 3:
    raise RuntimeError("v7 requires exactly four maps and three weapons")
if not all(item.get("instant_hit") is True for item in WEAPONS.values()):
    raise RuntimeError("v7 weapon set must be instant-hit only")


prod = v6.prod
base = v6.base
lifecycle = v6.lifecycle
v3 = v6.v5.v4.v3
ORIGINAL_TEMPLATES = {
    name: tuple(segments) for name, segments in prod.TEMPLATES.items()
}
ORIGINAL_PLAYER_MOTION_BASE_SPEED = float(base.PLAYER_MOTION_BASE_SPEED)
ORIGINAL_PLAYER_MOTION_SPEED_MODULATION = float(
    base.PLAYER_MOTION_SPEED_MODULATION
)

_source_distribution_rows = v6._v5_distribution_rows
_source_actors_for_row = v6._v5_actors_for_row
_source_build_episode_scenario = v6._v5_build_episode_scenario
_appearance_audit = v6.v5._v4_deep_appearance_audit
_source_run_attempt = v6._v5_run_attempt
_source_finalize = v6.finalize
_source_write_server_mode_config = base.capture.write_server_mode_config
_source_write_server_episode_config = base.capture.write_server_episode_config
_source_resident_run_live = base.reusable.ReusableStage1Lane.run_live
_source_validate_scenario_assets = base.capture.validate_scenario_assets


MATCH_LIMIT_CVARS = (
    "timelimit",
    "fraglimit",
    "capturelimit",
    "leadlimit",
)

OFFICIAL_RIFLE_PACKAGE = (
    ROOT / "assets" / "release-0.8.6" / "Xonotic" / "data"
    / "xonotic-20230620-data.pk3"
)
OFFICIAL_RIFLE_MEMBERS = {
    "models/weapons/v_campingrifle.md3",
    "models/weapons/h_campingrifle.iqm",
    "sound/weapons/campingrifle_fire.ogg",
}


def validate_scenario_assets_v7(scenario: dict[str, Any]) -> None:
    """Narrowly admit Xonotic's bundled Rifle for this isolated v7 process."""
    if scenario.get("weapon") != "Rifle":
        _source_validate_scenario_assets(scenario)
        return
    if scenario.get("weapon_netname") != "rifle":
        raise base.capture.CaptureFailure(
            "v7_rifle_identity_mismatch", str(scenario.get("weapon_netname"))
        )
                                                                              
                                                                           
    proxy = dict(scenario)
    proxy["weapon"] = "MachineGun"
    proxy["weapon_netname"] = "machinegun"
    _source_validate_scenario_assets(proxy)
    if not OFFICIAL_RIFLE_PACKAGE.is_file():
        raise base.capture.CaptureFailure(
            "v7_official_rifle_package_missing", str(OFFICIAL_RIFLE_PACKAGE)
        )
    with zipfile.ZipFile(OFFICIAL_RIFLE_PACKAGE) as archive:
        missing = sorted(OFFICIAL_RIFLE_MEMBERS - set(archive.namelist()))
    if missing:
        raise base.capture.CaptureFailure(
            "v7_official_rifle_assets_missing", ",".join(missing)
        )


def write_server_mode_config_v7(path: Path, gametype: str) -> str:
    """Apply unlimited-match overrides before map defaults are resolved."""
    selected = _source_write_server_mode_config(path, gametype)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("// Long60 v7: a 60 s rollout must not enter intermission.\n")
        for name in MATCH_LIMIT_CVARS:
            handle.write(f"set {name}_override 0\n")
    return selected


def write_server_episode_config_v7(
    path: Path, values: dict[str, Any], expected_gametype: str
) -> None:
    """Reassert and query unlimited limits after the map has loaded."""
    _source_write_server_episode_config(path, values, expected_gametype)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("// Long60 v7 post-map match-limit barrier.\n")
        for name in MATCH_LIMIT_CVARS:
            handle.write(f"set {name}_override 0\n")
            handle.write(f"set {name} 0\n")
        for name in MATCH_LIMIT_CVARS:
            handle.write(f"{name}_override\n")
            handle.write(f"{name}\n")


def resident_run_live_v7(
    lane: Any, stage: Path, scenario: dict[str, Any], retry: int = 0
) -> dict[str, Any]:
    live = _source_resident_run_live(lane, stage, scenario, retry=retry)
    console_path = stage / "server_console.log"
    console = console_path.read_text(errors="replace")
    realized: dict[str, str | None] = {}
    for name in MATCH_LIMIT_CVARS:
        realized[name] = base.capture.logged_cvar_value(console, name)
        realized[f"{name}_override"] = base.capture.logged_cvar_value(
            console, f"{name}_override"
        )
    if any(value != "0" for value in realized.values()):
        raise base.capture.CaptureFailure(
            "long60_match_limits_not_unlimited",
            f"realized={realized} log={console_path}",
        )
    live["long60_match_limits"] = realized
    live["long60_match_limits_unlimited"] = True
    return live


                                                                          
                                                    
base.capture.write_server_mode_config = write_server_mode_config_v7
base.capture.write_server_episode_config = write_server_episode_config_v7
base.capture.validate_scenario_assets = validate_scenario_assets_v7
base.reusable.ReusableStage1Lane.run_live = resident_run_live_v7


                                                                
for module in (v6, v6.v5, v6.v5.v4, v3, prod):
    module.RELEASE_ID = RELEASE_ID
    module.SCHEMA_VERSION = SCHEMA_VERSION
v6.EPISODE_PREFIX = EPISODE_PREFIX
v6.v5.EPISODE_PREFIX = EPISODE_PREFIX
v6.CONFIG_PATH = CONFIG_PATH
v6.CONFIG_SHA256 = CONFIG_SHA256
v6.MAPS = MAPS
v6.WEAPONS = WEAPONS
prod.BUILD_TAG = BUILD_TAG
prod.BUILD_COMMIT = BUILD_COMMIT
prod.DEFAULT_MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
prod.DEFAULT_OUTPUT_ROOT = Path("./rigen_data") / RELEASE_ID


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


def environment_weapon_text(map_name: str, weapon_name: str) -> str:
    return (
        "[ENVIRONMENT STYLE AND OBJECTS]\n"
        f"{MAPS[map_name]['environment_text']}\n"
        "[ACTIVE WEAPON]\n"
        f"The active weapon is {weapon_name}. Its appearance is described as: "
        f"{WEAPONS[weapon_name]['weapon_text']}"
    )


def aim_pitch_bias_degrees(row: dict[str, Any]) -> float:
    if "aim_pitch_bias_degrees" in row:
        return float(row["aim_pitch_bias_degrees"])
    return float(
        CONFIG.get("aim_pitch_bias_degrees_by_map_weapon", {})
        .get(str(row["map"]), {})
        .get(str(row["weapon"]), 0.0)
    )


def configure_geometry_and_weapon(row: dict[str, Any]) -> None:
    map_name = str(row["map"])
    weapon_name = str(row["weapon"])
    map_config = MAPS[map_name]
    player = tuple(float(value) for value in map_config["player_origin"])
    enemy = tuple(
        float(value) for value in map_config["enemy_reference_origin"]
    )
    angle = math.degrees(math.atan2(enemy[1] - player[1], enemy[0] - player[0]))
    scale = float(map_config["trajectory_scale"])
    base.PLAYER_ORIGIN = player
    base.BASE_ENEMY_ORIGIN = enemy
    base.BASE_ANGLE_DEGREES = angle
    base.PLAYER_MOTION_BASE_SPEED = ORIGINAL_PLAYER_MOTION_BASE_SPEED * scale
    base.PLAYER_MOTION_SPEED_MODULATION = (
        ORIGINAL_PLAYER_MOTION_SPEED_MODULATION * scale
    )
    base.ENVIRONMENT_TEXT = environment_weapon_text(map_name, weapon_name)
    prod.TEMPLATES = scaled_templates(scale)


def configured_cell_split_counts(
    template: str, map_name: str, weapon_name: str
) -> dict[str, int]:
    distribution = CONFIG["distribution"]
    counts = dict(distribution["default_template_map_weapon_split_counts"])
    override = (
        distribution.get("template_map_weapon_split_count_overrides", {})
        .get(template, {})
        .get(map_name, {})
        .get(weapon_name)
    )
    if override is not None:
        counts = dict(override)
    expected_splits = {"train", "validation", "test"}
    if set(counts) != expected_splits or any(int(value) < 0 for value in counts.values()):
        raise RuntimeError(
            f"invalid split counts for {template}/{map_name}/{weapon_name}: {counts}"
        )
    return {key: int(value) for key, value in counts.items()}


def expected_cell_split_counter() -> Counter[tuple[str, str, str, str]]:
    expected: Counter[tuple[str, str, str, str]] = Counter()
    for template in sorted(ORIGINAL_TEMPLATES):
        for map_name in sorted(MAPS):
            for weapon_name in sorted(WEAPONS):
                for split, count in configured_cell_split_counts(
                    template, map_name, weapon_name
                ).items():
                    if count:
                        expected[(template, map_name, weapon_name, split)] = count
    return expected


def distribution_rows() -> list[dict[str, Any]]:
    rows = _source_distribution_rows()
    combinations = list(itertools.product(sorted(MAPS), sorted(WEAPONS)))
    for template in sorted(ORIGINAL_TEMPLATES):
        indices = [index for index, row in enumerate(rows) if row["template"] == template]
        assignments: list[tuple[str, str, str]] = []
        for map_name, weapon_name in combinations:
            split_repeats = configured_cell_split_counts(
                template, map_name, weapon_name
            )
            for split in ("train", "validation", "test"):
                assignments.extend(
                    [(map_name, weapon_name, split)] * int(split_repeats[split])
                )
        if len(indices) != 900 or len(assignments) != len(indices):
            raise RuntimeError(
                f"{template}: expected 900 rows/assignments, got "
                f"{len(indices)}/{len(assignments)}"
            )
        random.Random(2608287701 + sum(map(ord, template))).shuffle(assignments)
        for index, (map_name, weapon_name, split) in zip(
            indices, assignments, strict=True
        ):
            map_config = MAPS[map_name]
            weapon_config = WEAPONS[weapon_name]
            rows[index].update(
                {
                    "split": split,
                    "map": map_name,
                    "gametype": map_config["gametype"],
                    "anchor_id": map_config["anchor_id"],
                    "trajectory_scale": float(map_config["trajectory_scale"]),
                    "weapon": weapon_name,
                    "weapon_netname": weapon_config["weapon_netname"],
                    "instant_hit_weapon": True,
                    "weapon_fire_policy": weapon_config["fire_policy"],
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
    actors = list(_source_actors_for_row(row))
    weapon = WEAPONS[str(row["weapon"])]
    kill_slots = {int(value) for value in row["kill_slots"]}
    for index, actor in enumerate(actors):
        health = 999.0
        if int(actor.slot) in kill_slots:
            if row["template"] == "controlled_return" and int(actor.slot) == 1:
                health = float(weapon["controlled_return_slot1_kill_health"])
            else:
                health = float(weapon["single_kill_health"])
        actors[index] = replace(actor, health=health)
    return tuple(actors)


def semiautomatic_primary_ticks(row: dict[str, Any]) -> list[int]:
    if "semiautomatic_primary_server_ticks" in row:
        return [
            int(value) for value in row["semiautomatic_primary_server_ticks"]
        ]
    map_weapon_overrides = CONFIG.get(
        "semiautomatic_primary_server_ticks_by_map_weapon", {}
    )
    weapon_override = (
        map_weapon_overrides.get(str(row["map"]), {})
        .get(str(row["weapon"]), {})
        .get(str(row["template"]))
    )
    if weapon_override is not None:
        return [int(value) for value in weapon_override]
    map_overrides = CONFIG.get("semiautomatic_primary_server_ticks_by_map", {})
    return [
        int(value)
        for value in map_overrides.get(str(row["map"]), {}).get(
            str(row["template"]),
            CONFIG["semiautomatic_primary_server_ticks"][str(row["template"])],
        )
    ]


def write_actions(path: Path, row: dict[str, Any]) -> None:
    configure_geometry_and_weapon(row)
    segments = prod.TEMPLATES[str(row["template"])]
    base.write_actions(path, row["episode_id"], int(row["engine_seed"]), segments)
    if row["weapon"] == "MachineGun":
        return
    pulse_starts = set(semiautomatic_primary_ticks(row))
    width = int(CONFIG["semiautomatic_primary_pulse_width_ticks"])
    with path.open(newline="", encoding="utf-8") as handle:
        seed_line = handle.readline()
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError(f"actions have no header: {path}")
    for action in rows:
        tick = int(action["tick"])
        action["primary"] = str(
            int(any(start <= tick < start + width for start in pulse_starts))
        )
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        handle.write(seed_line)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def rewrite_prompt_weapon(schedule: list[dict[str, Any]], weapon_name: str) -> None:
    for block in schedule:
        block["prompt"] = str(block["prompt"]).replace(
            "The player fires the MachineGun", f"The player fires the {weapon_name}"
        )


def build_episode_scenario(
    row: dict[str, Any], manifest_root: Path, shared_actions: Path
) -> tuple[Path, Path]:
    configure_geometry_and_weapon(row)
    scenario_path, timeline = _source_build_episode_scenario(
        row, manifest_root, shared_actions
    )

                                                                             
                                                                              
                                                            
    base.write_timeline(timeline, prod.TEMPLATES[str(row["template"])])
    v6.v5.v4.prime_timeline(timeline)

    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    rewrite_prompt_weapon(scenario["prompt_schedule"], str(row["weapon"]))
    map_config = MAPS[str(row["map"])]
    weapon_config = WEAPONS[str(row["weapon"])]
    pitch_bias = aim_pitch_bias_degrees(row)
    scenario["player"]["pitch"] = float(scenario["player"]["pitch"]) + pitch_bias
    scenario["camera_policy"]["center_pitch_degrees"] = (
        float(scenario["camera_policy"]["center_pitch_degrees"]) + pitch_bias
    )
    scenario.update(
        {
            "schema_version": "xonotic-stage2-long60-ref42-multimap-hitscan-production-scenario-v3",
            "release_id": RELEASE_ID,
            "map": row["map"],
            "gametype": row["gametype"],
            "anchor_id": row["anchor_id"],
            "weapon": row["weapon"],
            "weapon_netname": row["weapon_netname"],
            "instant_hit_weapon": True,
            "aim_pitch_bias_degrees": pitch_bias,
            "trajectory_scale": float(row["trajectory_scale"]),
            "geometry_config_path": str(CONFIG_PATH),
            "geometry_config_sha256": CONFIG_SHA256,
            "enemy_timeline_sha256": base.sha256(timeline),
            "enemy_horizontal_speed_units_per_second": float(
                base.ENEMY_HORIZONTAL_SPEED
            )
            * float(row["trajectory_scale"]),
            "environment_prompt_provenance_sample_id": map_config[
                "prompt_provenance_sample_id"
            ],
            "weapon_prompt_provenance_sample_id": weapon_config[
                "prompt_provenance_sample_id"
            ],
            "match_limit_policy": {
                "mode": "unlimited_for_complete_60s_rollout",
                "cvars": {
                    name: 0 for name in MATCH_LIMIT_CVARS
                },
                "override_cvars": {
                    f"{name}_override": 0 for name in MATCH_LIMIT_CVARS
                },
                "scope": "stage2_long60_v7_process_only",
            },
        }
    )
    scenario["distribution"].update(
        {
            "map": row["map"],
            "weapon": row["weapon"],
            "instant_hit_weapon": True,
            "trajectory_scale": float(row["trajectory_scale"]),
        }
    )
    scenario["player_action_policy"].update(
        {
            "weapon": row["weapon"],
            "fire_input_policy": weapon_config["fire_policy"],
            "semiautomatic_primary_server_ticks": (
                semiautomatic_primary_ticks(row)
                if row["weapon"] != "MachineGun"
                else None
            ),
            "semiautomatic_primary_pulse_width_ticks": (
                int(CONFIG["semiautomatic_primary_pulse_width_ticks"])
                if row["weapon"] != "MachineGun"
                else None
            ),
        }
    )
    scenario.setdefault("lifecycle_policy", {}).update(
        {
            "weapon_specific_health_calibration": True,
            "single_kill_health": weapon_config["single_kill_health"],
            "controlled_return_slot1_kill_health": weapon_config[
                "controlled_return_slot1_kill_health"
            ],
            "exact_telemetry_hit_and_kill_required": True,
        }
    )
    prod.write_json_atomic(scenario_path, scenario)
    return scenario_path, timeline


def action_primary_ticks(path: Path) -> list[int]:
    with path.open(newline="", encoding="utf-8") as handle:
        handle.readline()
        return [
            int(row["tick"])
            for row in csv.DictReader(handle)
            if int(row["primary"]) != 0
        ]


def deep_appearance_audit(
    manifest_root: Path, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    report = _appearance_audit(manifest_root, rows)
    maps = Counter(row["map"] for row in rows)
    weapons = Counter(row["weapon"] for row in rows)
    map_weapon = Counter((row["map"], row["weapon"]) for row in rows)
    template_map_weapon = Counter(
        (row["template"], row["map"], row["weapon"]) for row in rows
    )
    split_cells = Counter(
        (row["template"], row["map"], row["weapon"], row["split"])
        for row in rows
    )
    errors = list(report.get("errors") or [])
    scenario_contract = True
    match_limit_contract = True
    health_contract = True
    action_paths: dict[str, tuple[str, str, str]] = {}
    for row in rows:
        scenario = json.loads((ROOT / row["scenario_path"]).read_text(encoding="utf-8"))
        expected_prefix = environment_weapon_text(row["map"], row["weapon"])
        scenario_contract = scenario_contract and (
            scenario.get("map") == row["map"]
            and scenario.get("weapon") == row["weapon"]
            and scenario.get("trajectory_scale") == row["trajectory_scale"]
            and scenario.get("instant_hit_weapon") is True
            and all(
                str(block["prompt"]).startswith(expected_prefix)
                and (
                    row["weapon"] == "MachineGun"
                    or "fires the MachineGun" not in str(block["prompt"])
                )
                for block in scenario["prompt_schedule"]
            )
        )
        match_limit_contract = match_limit_contract and (
            scenario.get("match_limit_policy", {}).get("mode")
            == "unlimited_for_complete_60s_rollout"
            and scenario.get("match_limit_policy", {}).get("cvars")
            == {name: 0 for name in MATCH_LIMIT_CVARS}
            and scenario.get("match_limit_policy", {}).get("override_cvars")
            == {f"{name}_override": 0 for name in MATCH_LIMIT_CVARS}
        )
        kill_slots = {int(value) for value in row["kill_slots"]}
        weapon = WEAPONS[row["weapon"]]
        for actor in scenario["actors"]:
            expected_health = 999.0
            slot = int(actor["slot"])
            if slot in kill_slots:
                expected_health = (
                    float(weapon["controlled_return_slot1_kill_health"])
                    if row["template"] == "controlled_return" and slot == 1
                    else float(weapon["single_kill_health"])
                )
            if not math.isclose(float(actor["health"]), expected_health, abs_tol=1e-6):
                health_contract = False
                if len(errors) < 100:
                    errors.append(f"{row['episode_id']}:{actor['actor_id']}:health")
        action_paths[row["actions_path"]] = (
            row["template"],
            row["map"],
            row["weapon"],
        )

    expected_split_cells = expected_cell_split_counter()
    expected_template_map_weapon = Counter()
    expected_map_weapon = Counter()
    expected_maps = Counter()
    expected_weapons = Counter()
    for (template, map_name, weapon, _split), count in expected_split_cells.items():
        expected_template_map_weapon[(template, map_name, weapon)] += count
        expected_map_weapon[(map_name, weapon)] += count
        expected_maps[map_name] += count
        expected_weapons[weapon] += count

    expected_action_cells = {
        (template, map_name, weapon)
        for template, map_name, weapon in expected_template_map_weapon
    }
    actions_contract = len(action_paths) == len(expected_action_cells)
    for relative_path, (template, map_name, weapon) in action_paths.items():
        ticks = action_primary_ticks(ROOT / relative_path)
        if weapon == "MachineGun":
            actions_contract = actions_contract and len(ticks) == (
                len(ORIGINAL_TEMPLATES[template]) * int(base.FIRE_DURATION_TICKS)
            )
        else:
            starts = semiautomatic_primary_ticks(
                {"template": template, "map": map_name, "weapon": weapon}
            )
            width = int(CONFIG["semiautomatic_primary_pulse_width_ticks"])
            expected = [tick for start in starts for tick in range(start, start + width)]
            actions_contract = actions_contract and ticks == expected

    checks = {
        "four_maps_balanced_450_each": maps == expected_maps
        == Counter(
            {
                name: int(CONFIG["distribution"]["map_count_each"])
                for name in MAPS
            }
        ),
        "three_hitscan_weapons_balanced_600_each": weapons
        == expected_weapons
        == Counter({name: 600 for name in WEAPONS}),
        "map_weapon_distribution_matches_config": map_weapon == expected_map_weapon,
        "template_map_weapon_distribution_matches_config": template_map_weapon
        == expected_template_map_weapon,
        "cell_split_distribution_matches_config": split_cells == expected_split_cells,
        "complete_24_cell_cross_product": len(template_map_weapon) == (
            len(ORIGINAL_TEMPLATES) * len(MAPS) * len(WEAPONS)
        )
        and all(value == 75 for value in template_map_weapon.values()),
        "all_weapons_instant_hit": all(row["instant_hit_weapon"] is True for row in rows),
        "scenario_map_weapon_prompt_contract": scenario_contract,
        "scenario_match_limits_unlimited_contract": match_limit_contract,
        "weapon_specific_health_contract": health_contract,
        "all_configured_map_template_weapon_action_programs": actions_contract,
    }
    report["schema_version"] = "xonotic-stage2-long60-ref42-multimap-hitscan-static-validation-v3"
    report["release_id"] = RELEASE_ID
    report["errors"] = errors
    report["checks"].update(checks)
    report["distribution"] = {
        "map": dict(sorted(maps.items())),
        "weapon": dict(sorted(weapons.items())),
        "map_weapon": {"/".join(key): value for key, value in sorted(map_weapon.items())},
        "template_map_weapon": {
            "/".join(key): value for key, value in sorted(template_map_weapon.items())
        },
    }
    report["all_pass"] = all(report["checks"].values()) and not errors
    return report


def prepare(manifest_root: Path) -> None:
    manifest_root = manifest_root.resolve()
    manifest = manifest_root / "manifest.jsonl"
    resume_partial = (
        manifest_root.is_dir()
        and manifest.is_file()
        and not (manifest_root / "MANIFEST_METADATA.json").exists()
        and not (manifest_root / "PREPARED.json").exists()
    )
    if manifest_root.exists() and not resume_partial:
        raise RuntimeError(f"manifest root already exists: {manifest_root}")
    if resume_partial:
        rows = prod.load_jsonl(manifest)
        if len(rows) != prod.EPISODE_COUNT:
            raise RuntimeError(
                f"partial manifest has {len(rows)} rows, expected {prod.EPISODE_COUNT}"
            )
        print(f"resuming_prepared_rows={len(rows)}", flush=True)
    else:
        manifest_root.mkdir(parents=True)
        rows = distribution_rows()
        actions: dict[tuple[str, str, str], Path] = {}
        configured_cells = sorted(
            {(row["template"], row["map"], row["weapon"]) for row in rows}
        )
        for template, map_name, weapon in configured_cells:
            representative = next(
                row
                for row in rows
                if row["template"] == template
                and row["map"] == map_name
                and row["weapon"] == weapon
            )
            path = (
                manifest_root
                / "action_programs"
                / template
                / map_name
                / weapon
                / "actions.csv"
            )
            write_actions(path, representative)
            actions[(template, map_name, weapon)] = path

        for index, row in enumerate(rows):
            action_path = actions[(row["template"], row["map"], row["weapon"])]
            scenario_path, timeline = build_episode_scenario(
                row, manifest_root, action_path
            )
            row.update(
                {
                    "scenario_path": prod.relative_to_root(scenario_path),
                    "scenario_sha256": base.sha256(scenario_path),
                    "actions_path": prod.relative_to_root(action_path),
                    "actions_sha256": base.sha256(action_path),
                    "timeline_path": prod.relative_to_root(timeline),
                    "timeline_sha256": base.sha256(timeline),
                }
            )
            if index and index % 100 == 0:
                print(f"prepared={index}/{len(rows)}", flush=True)

        prod.write_jsonl_atomic(manifest, rows)
    registry_path = manifest_root / "appearance_registry.jsonl"
    prod.write_jsonl_atomic(registry_path, v3.identity_registry_rows())
    validation = deep_appearance_audit(manifest_root, rows)
    validation_path = manifest_root / "STATIC_VALIDATION.json"
    prod.write_json_atomic(validation_path, validation)
    if not validation["all_pass"]:
        raise RuntimeError(f"v7 static validation failed: {validation['checks']}")

    metadata = {
        "schema_version": "xonotic-stage2-long60-ref42-multimap-hitscan-production-metadata-v3",
        "release_id": RELEASE_ID,
        "created_utc": prod.utc_now(),
        "manifest_path": prod.relative_to_root(manifest),
        "manifest_sha256": base.sha256(manifest),
        "episode_count": len(rows),
        "episode_seconds": prod.EXPECTED_VIDEO_SECONDS,
        "target_video_hours": 30.0,
        "expected_video_hours": prod.EXPECTED_VIDEO_HOURS,
        "split_counts": dict(Counter(row["split"] for row in rows)),
        "template_counts": dict(Counter(row["template"] for row in rows)),
        "kill_count_counts": {
            str(key): value for key, value in sorted(Counter(row["kill_count"] for row in rows).items())
        },
        "maps": dict(Counter(row["map"] for row in rows)),
        "weapons": dict(Counter(row["weapon"] for row in rows)),
        "instant_hit_weapons_only": True,
        "match_limit_policy": {
            "mode": "unlimited_for_complete_60s_rollout",
            "cvars": {name: 0 for name in MATCH_LIMIT_CVARS},
            "override_cvars": {
                f"{name}_override": 0 for name in MATCH_LIMIT_CVARS
            },
            "runtime_fail_closed": True,
            "scope": "stage2_long60_v7_process_only",
        },
        "geometry_config_path": str(CONFIG_PATH),
        "geometry_config_sha256": CONFIG_SHA256,
        "runtime_build": BUILD_TAG,
        "runtime_source_commit": BUILD_COMMIT,
        "appearance_count": 42,
        "appearance_assignment_seed": v3.ASSIGNMENT_SEED,
        "appearance_library_path": str(v3.IDENTITY_LIBRARY),
        "appearance_library_sha256": v3.IDENTITY_LIBRARY_SHA256,
        "appearance_registry_path": prod.relative_to_root(registry_path),
        "appearance_registry_sha256": base.sha256(registry_path),
        "static_validation_path": prod.relative_to_root(validation_path),
        "static_validation_sha256": base.sha256(validation_path),
        "reference_conditioning": {
            "mode": "blockwise_current_actor",
            "ref_asset_release_id": v3.REF_ASSET_RELEASE_ID,
            "required_views": list(v3.REF_VIEWS),
            "ref_assets_ready": False,
            "appearance_text_in_prompt": False,
            "training_ready": False,
        },
        "topology": {"nodes": 2, "gpus_per_node": 4, "lanes_per_gpu": 4, "total_lanes": 32},
        "storage_policy": {
            "raw_avi_path_class": "node-local scratch only",
            "raw_avi_retained": False,
            "demo_retained": False,
            "shared_outputs": ["mp4", "qa.json", "record.json"],
        },
        "training_action_alignment_contract": {
            "source_action_rows": 3908,
            "source_warmup_ticks": 64,
            "published_video_origin_source_tick": 64,
            "training_action_rows_after_rebase": 3844,
            "postprocess": "remove the first 64 action rows before writing parquet",
            "manifest_action_row_offsets_changed": False,
            "joystick_renormalized": False,
            "required_semantic_gates": [
                "decoded_video_fire_pulse_alignment",
                "decoded_video_camera_turn_alignment",
            ],
        },
        "formal_collection_authorized": True,
        "training_admitted": False,
        "existing_stage1_stage2_pipelines_modified": False,
    }
    prod.write_json_atomic(manifest_root / "MANIFEST_METADATA.json", metadata)
    prod.write_json_atomic(
        manifest_root / "PREPARED.json",
        {
            "ready": True,
            "capture_ready": True,
            "training_ready": False,
            "created_utc": prod.utc_now(),
            "release_id": RELEASE_ID,
            "manifest_sha256": metadata["manifest_sha256"],
            "episode_count": len(rows),
            "static_validation_sha256": metadata["static_validation_sha256"],
            "multimap_hitscan_ready": True,
            "training_action_rebase_required": True,
            "training_action_warmup_rows_to_remove": 64,
        },
    )
    print(json.dumps(metadata, sort_keys=True), flush=True)


def validate_manifest(manifest_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_root = manifest_root.resolve()
    manifest = manifest_root / "manifest.jsonl"
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    prepared_path = manifest_root / "PREPARED.json"
    if not all(path.is_file() for path in (manifest, metadata_path, prepared_path)):
        raise RuntimeError(f"incomplete prepared manifest: {manifest_root}")
    rows = prod.load_jsonl(manifest)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    validation_path = ROOT / metadata.get("static_validation_path", "")
    validation = (
        json.loads(validation_path.read_text(encoding="utf-8"))
        if validation_path.is_file()
        else {}
    )
    checks = {
        "prepared": prepared.get("capture_ready") is True,
        "release_id": metadata.get("release_id") == RELEASE_ID,
        "manifest_hash": base.sha256(manifest) == metadata.get("manifest_sha256"),
        "episode_count": len(rows) == prod.EPISODE_COUNT == metadata.get("episode_count"),
        "unique_episode_ids": len({row["episode_id"] for row in rows}) == len(rows),
        "contiguous_indices": [row["manifest_index"] for row in rows] == list(range(len(rows))),
        "split_counts": Counter(row["split"] for row in rows) == prod.SPLIT_COUNTS,
        "kill_counts": Counter(row["kill_count"] for row in rows) == prod.KILL_COUNT_COUNTS,
        "runtime_build": metadata.get("runtime_build") == BUILD_TAG,
        "runtime_commit": metadata.get("runtime_source_commit") == BUILD_COMMIT,
        "geometry_config": metadata.get("geometry_config_sha256") == CONFIG_SHA256,
        "static_validation_hash": validation_path.is_file()
        and base.sha256(validation_path) == metadata.get("static_validation_sha256"),
        "static_validation_pass": validation.get("all_pass") is True,
        "episode_ids": all(
            row["episode_id"] == f"{EPISODE_PREFIX}_{index:06d}"
            for index, row in enumerate(rows)
        ),
        "no_raw_avi_policy": all(row["raw_avi_retained"] is False for row in rows),
    }
    if not all(checks.values()):
        raise RuntimeError(f"v7 manifest validation failed: {checks}")
    return rows, metadata


def validate_episode_multimap_hitscan(*args: Any, **kwargs: Any) -> dict[str, Any]:
    scenario = args[0] if args else kwargs["scenario"]
    live = args[2] if len(args) >= 3 else kwargs["live"]
    qa = v6.validate_episode_multimap_hitscan(*args, **kwargs)
    checks = qa["checks"]
    checks["long60_match_limits_unlimited"] = (
        live.get("long60_match_limits_unlimited") is True
        and all(
            value == "0"
            for value in (live.get("long60_match_limits") or {}).values()
        )
    )
    qa["match_limit_policy"] = {
        "mode": "unlimited_for_complete_60s_rollout",
        "realized": live.get("long60_match_limits"),
        "scope": "stage2_long60_v7_process_only",
    }
    weapon_name = str(scenario["weapon"])
    telemetry = prod.load_jsonl(Path(live["server_telemetry"]))
    reset = next((row for row in telemetry if row.get("kind") == "reset"), {})
    player_entity = int(reset.get("player_entity", -1))
    fire_events = [
        row
        for row in telemetry
        if row.get("kind") == "event"
        and row.get("event") == "fire"
        and int(row.get("actor", -1)) == player_entity
    ]
    fire_by_encounter = []
    for encounter in scenario["encounters"]:
        start = base.capture.WARMUP_TICKS + int(
            encounter["start_block"] * base.PROMPT_BLOCK_SECONDS * 64
        )
        end = base.capture.WARMUP_TICKS + int(
            encounter["end_block"] * base.PROMPT_BLOCK_SECONDS * 64
        )
        fire_by_encounter.append(
            sum(start <= int(event["server_tick"]) < end for event in fire_events)
        )
    checks["weapon_fired_in_every_declared_encounter"] = bool(fire_by_encounter) and min(fire_by_encounter) >= 1
    checks["fire_events_match_selected_weapon"] = bool(fire_events) and all(
        int(event.get("weapon_id", -1))
        == int(WEAPONS[weapon_name]["weapon_id"])
        for event in fire_events
    )
    if weapon_name == "MachineGun":
        checks["machinegun_multishot_contract"] = min(fire_by_encounter) >= 5
    else:
        checks.pop("requested_sustained_fire", None)
        checks.pop("applied_sustained_fire", None)
        checks.pop("machinegun_multishot_contract", None)
        expected_primary = len(scenario["encounters"]) * int(
            CONFIG["semiautomatic_primary_pulse_width_ticks"]
        )
        checks["requested_calibrated_primary_pulses"] = (
            int(qa["counts"]["requested_primary_ticks"]) == expected_primary
        )
        checks["applied_calibrated_primary_pulses"] = (
            int(qa["counts"]["applied_primary_ticks"]) == expected_primary
        )
    qa["counts"]["weapon_fire_events_by_encounter"] = fire_by_encounter
    qa["passed"] = all(checks.values())
    return qa


def run_attempt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    row = args[1] if len(args) >= 2 else kwargs["row"]
    output_root = args[3] if len(args) >= 4 else kwargs["output_root"]
    configure_geometry_and_weapon(row)
    record = _source_run_attempt(*args, **kwargs)
    record.update(
        {
            "map": row["map"],
            "gametype": row["gametype"],
            "anchor_id": row["anchor_id"],
            "trajectory_scale": row["trajectory_scale"],
            "weapon": row["weapon"],
            "weapon_netname": row["weapon_netname"],
            "weapon_fire_policy": row["weapon_fire_policy"],
            "instant_hit_weapon": True,
            "geometry_config_sha256": CONFIG_SHA256,
        }
    )
    paths = prod.accepted_paths(output_root, row)
    prod.write_json_atomic(paths["record"], record)
    prod.write_json_atomic(paths["accepted"], record)
    return record


def worker(
    manifest_root: Path,
    output_root: Path,
    scratch_root: Path,
    lane_id: int,
    lane_count: int,
    port: int,
    max_attempts: int,
    episode_indices: set[int] | None,
) -> None:
    rows, _ = validate_manifest(manifest_root)
    selected = [
        row
        for row in rows
        if (
            row["manifest_index"] in episode_indices
            if episode_indices is not None
            else row["manifest_index"] % lane_count == lane_id
        )
    ]
                                                                              
                                                                              
                                
    selected.sort(key=lambda row: (str(row["map"]), int(row["manifest_index"])))
    build = ROOT / "build" / BUILD_TAG
    if (build / "SOURCE_COMMIT").read_text(encoding="utf-8").strip() != BUILD_COMMIT:
        raise RuntimeError(f"runtime build mismatch: {build}")
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lane: Any | None = None
    lane_group: tuple[str, str] | None = None
    generation = 0
    completed = 0
    failures: list[dict[str, Any]] = []
    started = time.monotonic()
    try:
        for sequence, row in enumerate(selected, 1):
            if prod.already_accepted(output_root, row):
                completed += 1
                continue
            scenario_path = ROOT / row["scenario_path"]
            if base.sha256(scenario_path) != row["scenario_sha256"]:
                raise RuntimeError(f"scenario hash mismatch: {scenario_path}")
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            requested_group = (str(row["map"]), str(row["gametype"]))
            if lane is not None and lane_group != requested_group:
                lane.close()
                lane = None
                lane_group = None
            last_error = ""
            for attempt in range(1, max_attempts + 1):
                if lane is None:
                    generation += 1
                    lane = base.reusable.ReusableStage1Lane(
                        scratch_root / f"resident-generation-{generation:03d}",
                        build=build,
                        port=port,
                    )
                    lane_group = requested_group
                try:
                    run_attempt(lane, row, scenario, output_root, scratch_root, attempt)
                    completed += 1
                    print(
                        f"episode_accepted lane={lane_id} episode={row['episode_id']} "
                        f"map={row['map']} weapon={row['weapon']} "
                        f"progress={sequence}/{len(selected)}",
                        flush=True,
                    )
                    break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    traceback.print_exc()
                    lane.close()
                    lane = None
                    lane_group = None
            else:
                failures.append(
                    {
                        "manifest_index": row["manifest_index"],
                        "episode_id": row["episode_id"],
                        "error": last_error,
                    }
                )
    finally:
        if lane is not None:
            lane.close()
    summary = {
        "schema_version": "xonotic-stage2-long60-v7-lane-summary-v1",
        "created_utc": prod.utc_now(),
        "lane_id": lane_id,
        "lane_count": lane_count,
        "selected": len(selected),
        "completed_or_preexisting": completed,
        "failures": failures,
        "wall_seconds": time.monotonic() - started,
        "raw_avi_retained": False,
        "resident_lane_restarted_on_map_change": True,
        "selected_rows_grouped_by_map": True,
    }
    prod.write_json_atomic(
        output_root / "status" / "lanes" / f"lane-{lane_id:03d}.json", summary
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    if failures:
        raise RuntimeError(f"lane {lane_id} left {len(failures)} incomplete")


def finalize(manifest_root: Path, output_root: Path) -> None:
    _source_finalize(manifest_root, output_root)


lifecycle.lifecycle_validate_episode = validate_episode_multimap_hitscan
v6.configure_geometry_and_weapon = configure_geometry_and_weapon
v6.MAPS = MAPS
v6.WEAPONS = WEAPONS
prod.distribution_rows = distribution_rows
prod.actors_for_row = actors_for_row
prod.build_episode_scenario = build_episode_scenario
prod.prepare = prepare
prod.validate_manifest = validate_manifest
prod.run_attempt = run_attempt
prod.worker = worker
prod.finalize = finalize


def main() -> int:
    return prod.main()


if __name__ == "__main__":
    raise SystemExit(main())
