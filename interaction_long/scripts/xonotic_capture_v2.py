                      
"""Bounded v2 preflight and category-visible coverage Pilot.

This program deliberately has no formal 60k/40k collection command.  It
reuses the proven 64 Hz live/demo/offline-render/CPU-x264 path, adds optional
enemy scenarios, and publishes only ``split=v2_coverage_pilot`` artifacts.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import html
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = capture.ROOT
CATALOG_PATH = ROOT / "configs/OFFICIAL_V2_CONTENT_CATALOG.json"
PREFLIGHT_ROOT = ROOT / "preflight_v2"
PREFLIGHT_RESULTS = PREFLIGHT_ROOT / "results.jsonl"
PREFLIGHT_REPORT = PREFLIGHT_ROOT / "PREFLIGHT_REPORT.json"
PREFLIGHT_REPORT_MD = PREFLIGHT_ROOT / "PREFLIGHT_REPORT.md"
PILOT_ROOT = ROOT / "v2_coverage_pilot"
SCENARIOS_PATH = ROOT / "configs/v2_coverage_pilot_scenarios.jsonl"
ACCEPTED_PATH = PILOT_ROOT / "manifests/accepted.jsonl"
REJECTS_PATH = PILOT_ROOT / "manifests/rejects.jsonl"
PREVIEW_ROOT = ROOT / "previews/v2"

WEAPONS = (
    "Blaster",
    "Shotgun",
    "MachineGun",
    "Mortar",
    "Electro",
    "Crylink",
    "Vortex",
    "Hagar",
    "Devastator",
)
RELATIONS = (
    "offscreen_or_occluded",
    "visible_far",
    "near_crosshair",
    "brief_center_pass",
    "center_linger",
    "nearly_continuous_center",
)
AIM_POLICIES = (
    "visible_no_response",
    "delayed_acquisition",
    "pass_offset",
    "track_loss_reacquire",
    "sustained_tracking",
)
DISTANCE_BINS = {
    "close": (64.0, 256.0),
    "near": (256.0, 512.0),
    "medium": (512.0, 768.0),
    "far": (768.0, 1024.0),
    "very_far": (1024.0, 1536.0),
    "extreme": (1536.0, math.inf),
}
WRITE_LOCK = threading.Lock()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        raise capture.CaptureFailure("v2_catalog_missing", str(CATALOG_PATH))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if catalog.get("counts") != {
        "maps": 29,
        "weapons": 9,
        "enemy_models": 7,
        "enemy_appearances": 14,
        "waypoints": 3241,
    }:
        raise capture.CaptureFailure(
            "v2_catalog_count_gate", capture.canonical_json(catalog.get("counts"))
        )
    return catalog


def pulse(tick: int, starts: Iterable[int], width: int = 1) -> int:
    return int(any(start <= tick < start + width for start in starts))


def fire_controls(
    weapon: str, out_tick: int, starts: tuple[int, ...]
) -> tuple[int, int]:
    primary = 0
    secondary = 0
    if weapon == "MachineGun":
        primary = pulse(out_tick, starts, 14)
    else:
        primary = pulse(out_tick, starts, 2)
    return primary, secondary


def v2_action_rows(
    scenario: dict[str, Any], retry: int = 0
) -> list[dict[str, Any]]:
    """Create the frozen 384-tick engine-usercmd program.

    No function here reads live enemy or camera state.  Target-aware programs
    use only scenario geometry frozen before the episode.
    """
    if not str(scenario.get("schema_version", "")).startswith("xonotic-v2-"):
        return ORIGINAL_ACTION_ROWS(scenario, retry=retry)
    program = scenario["action_program"]
    weapon = scenario["weapon"]
    rows: list[dict[str, Any]] = []
    for tick in range(capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        forward = strafe = yaw_delta = pitch_delta = 0.0
        jump = primary = secondary = reload_button = 0
        if out_tick >= 0:
            phase = 2.0 * math.pi * out_tick / 64.0
            if program in {"preflight_idle", "relation_continuous"}:
                pass
            elif program == "atomic_forward":
                forward = 260.0 if out_tick < 160 else -220.0
            elif program == "atomic_strafe":
                strafe = 250.0 if out_tick < 160 else -250.0
            elif program == "atomic_view":
                yaw_delta = 0.55 * math.sin(out_tick / 19.0)
                pitch_delta = 0.16 * math.sin(out_tick / 27.0)
            elif program == "atomic_jump":
                jump = pulse(out_tick, (24, 176), 2)
                forward = 80.0 * math.sin(phase)
            elif program == "route_combo":
                forward = 210.0 * math.sin(phase)
                strafe = 150.0 * math.cos(phase)
                yaw_delta = 0.24 * math.sin(out_tick / 22.0)
                pitch_delta = 0.06 * math.sin(out_tick / 31.0)
                jump = pulse(out_tick, (32, 192), 2)
            elif program == "high_motion":
                forward = 260.0 * math.sin(phase)
                strafe = 210.0 * math.cos(phase)
                yaw_delta = 1.15 * math.sin(out_tick / 11.0)
                pitch_delta = 0.22 * math.sin(out_tick / 17.0)
                jump = pulse(out_tick, (20, 116, 212), 2)
            elif program == "motion_forward_long":
                forward = 400.0
            elif program == "motion_strafe_long":
                strafe = 400.0
            elif program == "motion_diagonal_long":
                forward = 320.0
                strafe = 240.0
            elif program == "motion_turn90":
                forward = 400.0
                if out_tick < 160:
                    yaw_delta = 90.0 / 160.0
            elif program == "motion_turn180":
                forward = 400.0
                if out_tick < 256:
                    yaw_delta = 180.0 / 256.0
            elif program == "motion_lookback180":
                forward = 400.0
                if 112 <= out_tick < 176:
                    yaw_delta = 180.0 / 64.0
            elif program == "camera_yaw90_smooth":
                if out_tick < 128:
                    yaw_delta = 90.0 / 128.0
            elif program == "camera_yaw180_smooth":
                if out_tick < 192:
                    yaw_delta = 180.0 / 192.0
            elif program == "camera_yaw360_smooth":
                yaw_delta = 360.0 / capture.OUTPUT_TICKS
            elif program == "camera_yaw90_snap":
                if 48 <= out_tick < 64:
                    yaw_delta = 90.0 / 16.0
            elif program == "camera_pitch60_scan":
                if out_tick < 80:
                    pitch_delta = 30.0 / 80.0
                elif out_tick < 240:
                    pitch_delta = -60.0 / 160.0
                else:
                    pitch_delta = 30.0 / 80.0
            elif program == "camera_yaw180_pitch60":
                if out_tick < 192:
                    yaw_delta = 180.0 / 192.0
                if out_tick < 80:
                    pitch_delta = 30.0 / 80.0
                elif out_tick < 240:
                    pitch_delta = -60.0 / 160.0
                else:
                    pitch_delta = 30.0 / 80.0
            elif program == "environmental_primary":
                if out_tick < 32:
                    pitch_delta = -18.0 / 32.0
                primary, secondary = fire_controls(
                    weapon, out_tick, (64, 176, 272)
                )
                strafe = 70.0 * math.sin(phase)
            elif program == "environmental_secondary":
                                                                         
                                                                            
                                                                              
                primary = pulse(out_tick, (48, 160, 272), 2)
                secondary = pulse(out_tick, (80, 192, 304), 2)
                strafe = 45.0 * math.sin(phase)
            elif program == "machinegun_reload":
                primary = pulse(out_tick, (24,), 16)
                reload_button = pulse(out_tick, (72,), 1)
            elif program == "relation_offscreen":
                forward = 120.0 * math.sin(phase)
                jump = pulse(out_tick, (80, 224), 2)
            elif program == "relation_far":
                strafe = 100.0 * math.sin(phase)
                jump = pulse(out_tick, (80, 224), 2)
            elif program == "relation_near":
                forward = 80.0 * math.sin(phase)
                jump = pulse(out_tick, (120,), 2)
            elif program == "relation_brief":
                if out_tick < 96:
                    yaw_delta = 24.0 / 96.0
                strafe = 60.0 * math.sin(phase)
                jump = pulse(out_tick, (160,), 2)
            elif program == "relation_linger":
                yaw_delta = 8.0 / capture.OUTPUT_TICKS
                jump = pulse(out_tick, (144,), 2)
            elif program == "causal_visible_no_response":
                strafe = 70.0 * math.sin(phase)
            elif program == "causal_turn90_no_fire":
                if out_tick < 128:
                    yaw_delta = 90.0 / 128.0
            elif program == "causal_turn180_miss":
                if out_tick < 192:
                    yaw_delta = 180.0 / 192.0
                if out_tick >= 208:
                    primary, secondary = fire_controls(
                        weapon, out_tick, (208, 272)
                    )
            elif program == "causal_delayed":
                if 64 <= out_tick < 128:
                    yaw_delta = 18.0 / 64.0
                if out_tick >= 160:
                    primary, secondary = fire_controls(
                        weapon, out_tick, (160, 240)
                    )
            elif program == "causal_pass":
                if 32 <= out_tick < 112:
                    yaw_delta = (34.0 + retry * 4.0) / 80.0
                if out_tick >= 144:
                    primary, secondary = fire_controls(
                        weapon, out_tick, (144, 240)
                    )
                forward = 60.0 * math.sin(phase)
            elif program == "causal_reacquire":
                if 48 <= out_tick < 88:
                    yaw_delta = 10.0 / 40.0
                elif 112 <= out_tick < 152:
                    yaw_delta = -10.0 / 40.0
                if out_tick >= 176:
                    primary, secondary = fire_controls(
                        weapon, out_tick, (176, 256)
                    )
                jump = pulse(out_tick, (96,), 2)
            elif program == "causal_sustained":
                primary, secondary = fire_controls(
                    weapon, out_tick, (80, 176, 272)
                )
            else:
                raise ValueError(f"unknown v2 action program {program}")
        rows.append(
            {
                "tick": tick,
                "forward": round(forward, 6),
                "strafe": round(strafe, 6),
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": jump,
                "primary": primary,
                "secondary": secondary,
                "weapon_impulse": 0,
                "reload": reload_button,
            }
        )
    return rows


ORIGINAL_ACTION_ROWS = capture.CANONICAL_ACTION_ROWS
V2_ACTION_PROGRAMS = (
    "preflight_idle",
    "relation_continuous",
    "atomic_forward",
    "atomic_strafe",
    "atomic_view",
    "atomic_jump",
    "route_combo",
    "high_motion",
    "motion_forward_long",
    "motion_strafe_long",
    "motion_diagonal_long",
    "motion_turn90",
    "motion_turn180",
    "motion_lookback180",
    "camera_yaw90_smooth",
    "camera_yaw180_smooth",
    "camera_yaw360_smooth",
    "camera_yaw90_snap",
    "camera_pitch60_scan",
    "camera_yaw180_pitch60",
    "environmental_primary",
    "environmental_secondary",
    "machinegun_reload",
    "relation_offscreen",
    "relation_far",
    "relation_near",
    "relation_brief",
    "relation_linger",
    "causal_visible_no_response",
    "causal_turn90_no_fire",
    "causal_turn180_miss",
    "causal_delayed",
    "causal_pass",
    "causal_reacquire",
    "causal_sustained",
)
capture.register_action_row_provider(
    "xonotic_capture_v2",
    V2_ACTION_PROGRAMS,
    v2_action_rows,
)


def yaw_pitch_toward(
    player_origin: list[float], enemy_origin: list[float]
) -> tuple[float, float]:
    dx = enemy_origin[0] - player_origin[0]
    dy = enemy_origin[1] - player_origin[1]
                                                                            
                                   
    dz = (enemy_origin[2] + 24.0) - (player_origin[2] + 27.0)
    horizontal = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, horizontal))
    return yaw, pitch


def scenario(
    *,
    episode_id: str,
    split: str,
    dataset_role: str,
    category: str,
    map_name: str,
    gametype: str,
    player_origin: list[float],
    weapon: str,
    action_program: str,
    seed: int,
    enemy_origin: list[float] | None = None,
    enemy_model: str = "",
    enemy_skin: int = 0,
    enemy_color: int = 0,
    yaw_offset: float = 0.0,
    pitch_offset: float = 0.0,
    enemy_health: float = 500.0,
    expected_relation: str | None = None,
    aim_policy: str | None = None,
    expected_outcome: str | None = None,
    expected_distance_bin: str | None = None,
    expects_sound: bool = True,
    fire_required: bool = False,
    reload_success: bool = False,
) -> dict[str, Any]:
    enemy_present = enemy_origin is not None
    if enemy_present:
        base_yaw, base_pitch = yaw_pitch_toward(player_origin, enemy_origin)
        enemy_yaw, _ = yaw_pitch_toward(enemy_origin, player_origin)
    else:
        base_yaw = float((seed * 37) % 360) - 180.0
        base_pitch = 0.0
        enemy_yaw = 0.0
    clip = 12.0 if reload_success else 60.0
    result = {
        "schema_version": "xonotic-v2-scenario-v1",
        "episode_id": episode_id,
        "split": split,
        "dataset_role": dataset_role,
        "category": category,
        "target_bin": dataset_role,
        "target_ordinal": 0,
        "intent_outcome": expected_outcome or "none",
        "seed": seed,
        "map": map_name,
        "gametype": gametype,
        "anchor_id": (
            f"{map_name}_{episode_id}_pair"
            if enemy_present
            else f"{map_name}_{episode_id}_solo"
        ),
        "enemy_present": enemy_present,
        "enemy_model": enemy_model if enemy_present else "",
        "enemy_skin": enemy_skin if enemy_present else 0,
        "enemy_color": enemy_color if enemy_present else 0,
        "weapon": weapon,
        "weapon_netname": capture.WEAPON_NETNAME[weapon],
        "action_program": action_program,
        "warmup_ticks": capture.WARMUP_TICKS,
        "output_ticks": capture.OUTPUT_TICKS,
        "tick_hz": capture.TICK_HZ,
        "video": {
            "width": capture.WIDTH,
            "height": capture.HEIGHT,
            "fps": capture.VIDEO_FPS,
            "frames": capture.OUTPUT_TICKS,
        },
        "audio": {
            "sample_rate": capture.AUDIO_RATE,
            "channels": 2,
            "sample_format": "s16",
            "samples_per_channel": capture.AUDIO_SAMPLES,
            "samples_per_frame": capture.SAMPLES_PER_FRAME,
        },
        "player": {
            "origin": [round(float(value), 6) for value in player_origin],
            "yaw": round(base_yaw + yaw_offset, 6),
            "pitch": round(base_pitch + pitch_offset, 6),
            "health": 200.0,
            "armor": 0.0,
            "clip": clip,
            "reserve": 180.0,
        },
        "enemy": (
            {
                "origin": [
                    round(float(value), 6) for value in enemy_origin
                ],
                "yaw": round(enemy_yaw, 6),
                "health": enemy_health,
                "armor": 0.0,
                "motion": 0,
                "motion_vector": [0.0, 0.0, 0.0],
                "motion_distance": 0.0,
            }
            if enemy_present
            else None
        ),
        "policy_labels": {
            "expected_target_relation": expected_relation,
            "aim_policy": aim_policy,
            "expected_distance_bin": expected_distance_bin,
            "route_policy_reads_enemy": False,
            "enemy_motion_reads_camera": False,
            "aim_overlay_reads_enemy": dataset_role == "causal_interaction",
        },
        "acceptance": {
            "actual_outcome": expected_outcome,
            "fire_required": fire_required,
            "reload_success": reload_success,
        },
        "expects_sound": expects_sound,
        "asset_policy": "official-xonotic-0.8.6-only",
    }
    return result


def scenario_for_position_probe(
    map_name: str, map_spec: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    return scenario(
        episode_id=f"preflight_pos_{map_name}_{candidate['candidate_id']}",
        split="preflight",
        dataset_role="foundation_no_enemy",
        category="map_position_probe",
        map_name=map_name,
        gametype=map_spec["preflight_gametype"],
        player_origin=candidate["origin"],
        weapon="Blaster",
        action_program="preflight_idle",
        seed=2_000_000 + int(candidate["waypoint_index"]),
        expects_sound=False,
    )


def scenario_for_pair_probe(
    map_name: str, map_spec: dict[str, Any], pair: dict[str, Any]
) -> dict[str, Any]:
    return scenario(
        episode_id=f"preflight_pair_{map_name}_{pair['pair_id']}",
        split="preflight",
        dataset_role="foundation_enemy_distractor",
        category="enemy_pair_probe",
        map_name=map_name,
        gametype=map_spec["preflight_gametype"],
        player_origin=pair["player_origin"],
        enemy_origin=pair["enemy_origin"],
        enemy_model="ignis",
        enemy_skin=0,
        enemy_color=68,
        weapon="Blaster",
        action_program="preflight_idle",
        seed=2_100_000
        + int(pair["player_waypoint_index"]) * 4099
        + int(pair["enemy_waypoint_index"]),
        expected_distance_bin=pair["distance_bin"],
        expects_sound=False,
    )


def persist_probe_stage(stage: Path, destination: Path) -> dict[str, str]:
    if destination.exists():
        raise capture.CaptureFailure("refuse_overwrite", str(destination))
    destination.mkdir(parents=True)
    sources = {
        "scenario.json": stage / "scenario.json",
        "actions_requested.csv": stage / "actions_requested.csv",
        "server_console.log": stage / "server_console.log",
        "client_live_console.log": stage / "client_live_console.log",
        "server.jsonl": stage / "server_user/data/data/capture/server.jsonl",
        "actions_engine.csv": stage / "live/actions_engine.csv",
    }
    demos = list((stage / "client_user/data/demos").glob("*.dem"))
    if demos:
        sources[demos[0].name] = demos[0]
    hashes: dict[str, str] = {}
    for name, source in sources.items():
        if source.is_file():
            target = destination / name
            shutil.copy2(source, target)
            hashes[name] = capture.sha256_file(target)
    return hashes


def run_live_probe(
    probe_kind: str, probe_scenario: dict[str, Any], build: Path
) -> dict[str, Any]:
    episode_id = probe_scenario["episode_id"]
    destination = PREFLIGHT_ROOT / "probes" / probe_kind / episode_id
    result_path = destination / "result.json"
    if result_path.is_file():
        return json.loads(result_path.read_text(encoding="utf-8"))
                                                                             
                                                                
    stage = capture.TMP_ROOT / "raw" / episode_id
    if stage.exists():
        capture.clean_stage(stage)
    stage.mkdir(parents=True)
    atomic_json(stage / "scenario.json", probe_scenario)
    started = capture.utc_now()
    try:
        live = capture.run_live_attempt(stage, probe_scenario, build, retry=0)
        states, events, rows = capture.parse_server_telemetry(
            Path(live["server_telemetry"])
        )
        reset_rows = [row for row in rows if row.get("kind") == "reset"]
        reset = reset_rows[0] if len(reset_rows) == 1 else {}
        anchor = reset.get("anchor", {})
        enemy_present = bool(probe_scenario["enemy_present"])
        checks = {
            "reset_singleton": len(reset_rows) == 1,
            "state_ticks_exact": len(states) == capture.TOTAL_TICKS,
            "output_begin": sum(
                row.get("kind") == "output_begin" for row in rows
            )
            == 1,
            "output_end": sum(row.get("kind") == "output_end" for row in rows)
            == 1,
            "enemy_presence": (
                bool(reset.get("enemy_present", 1)) == enemy_present
            ),
            "player_clear": bool(anchor.get("player_clear", 0)),
            "player_ground": bool(anchor.get("player_ground", 0)),
            "enemy_clear": (
                not enemy_present or bool(anchor.get("enemy_clear", 0))
            ),
            "enemy_ground": (
                not enemy_present or bool(anchor.get("enemy_ground", 0))
            ),
            "line_of_sight": (
                not enemy_present
                or float(anchor.get("los_fraction", -1)) >= 0.999999
            ),
        }
        result = {
            "schema_version": "xonotic-v2-live-probe-v1",
            "probe_kind": probe_kind,
            "episode_id": episode_id,
            "map": probe_scenario["map"],
            "gametype": probe_scenario["gametype"],
            "player_origin": probe_scenario["player"]["origin"],
            "enemy_origin": (
                probe_scenario["enemy"]["origin"] if enemy_present else None
            ),
            "distance_bin": probe_scenario["policy_labels"].get(
                "expected_distance_bin"
            ),
            "checks": checks,
            "pass": all(checks.values()),
            "reset": reset,
            "event_count": len(events),
            "started_utc": started,
            "finished_utc": capture.utc_now(),
        }
    except Exception as exc:
        result = {
            "schema_version": "xonotic-v2-live-probe-v1",
            "probe_kind": probe_kind,
            "episode_id": episode_id,
            "map": probe_scenario["map"],
            "gametype": probe_scenario["gametype"],
            "player_origin": probe_scenario["player"]["origin"],
            "enemy_origin": (
                probe_scenario["enemy"]["origin"]
                if probe_scenario["enemy_present"]
                else None
            ),
            "distance_bin": probe_scenario["policy_labels"].get(
                "expected_distance_bin"
            ),
            "pass": False,
            "error": f"{type(exc).__name__}:{exc}",
            "traceback": traceback.format_exc(),
            "started_utc": started,
            "finished_utc": capture.utc_now(),
        }
    try:
        hashes = persist_probe_stage(stage, destination)
        result["artifacts_path"] = str(destination)
        result["artifact_sha256"] = hashes
        atomic_json(result_path, result)
    finally:
        if stage.exists():
            capture.clean_stage(stage)
    with WRITE_LOCK:
        capture.append_jsonl(PREFLIGHT_RESULTS, result)
    return result


def run_probe_batch(
    kind: str,
    scenarios: list[dict[str, Any]],
    build: Path,
    workers: int,
) -> list[dict[str, Any]]:
    print(f"probe_batch kind={kind} count={len(scenarios)} workers={workers}")
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_live_probe, kind, row, build): row
            for row in scenarios
        }
        for index, future in enumerate(
            concurrent.futures.as_completed(futures), 1
        ):
            result = future.result()
            results.append(result)
            print(
                f"probe {kind} {index}/{len(futures)} "
                f"map={result['map']} pass={result['pass']} "
                f"id={result['episode_id']}",
                flush=True,
            )
    return results


def target_relation_table(
    package: Path, enemy_present: bool
) -> pd.DataFrame:
    """Derive per-frame target geometry from canonical state and camera data."""
    frames = pd.read_parquet(package / "frames.parquet")
    states = pd.read_parquet(package / "states.parquet").set_index("server_tick")
    rows: list[dict[str, Any]] = []
    for _, frame in frames.iterrows():
        tick = int(frame["episode_server_tick"])
        base = {
            "episode_id": str(frame["episode_id"]),
            "frame_index": int(frame["frame_index"]),
            "pts_seconds": float(frame["pts_seconds"]),
            "server_tick": tick,
            "enemy_present": bool(enemy_present),
            "visibility_method": (
                "authoritative_los_plus_camera_frustum"
                if enemy_present
                else "enemy_entity_absent"
            ),
            "namespace": "derived_target_relation",
        }
        if not enemy_present:
            rows.append(
                {
                    **base,
                    "enemy_x": np.nan,
                    "enemy_y": np.nan,
                    "enemy_z": np.nan,
                    "distance_3d": np.nan,
                    "horizontal_distance": np.nan,
                    "vertical_delta": np.nan,
                    "los_fraction": 0.0,
                    "camera_depth": np.nan,
                    "camera_lateral": np.nan,
                    "camera_vertical": np.nan,
                    "screen_x_normalized": np.nan,
                    "screen_y_normalized": np.nan,
                    "in_camera_frustum": False,
                    "render_visible_proxy": False,
                    "angular_error_deg": np.nan,
                    "centered_3deg": False,
                    "frame_relation": "enemy_absent",
                }
            )
            continue
        state = states.loc[tick]
        origin = np.asarray(state["enemy.origin"], dtype=np.float64)
        target = origin + np.asarray([0.0, 0.0, 24.0])
        camera = np.asarray(
            [frame["camera_x"], frame["camera_y"], frame["camera_z"]],
            dtype=np.float64,
        )
        relative = target - camera
        forward = np.asarray(
            [frame["forward_x"], frame["forward_y"], frame["forward_z"]],
            dtype=np.float64,
        )
        left = np.asarray(
            [frame["left_x"], frame["left_y"], frame["left_z"]],
            dtype=np.float64,
        )
        up = np.asarray(
            [frame["up_x"], frame["up_y"], frame["up_z"]],
            dtype=np.float64,
        )
        depth = float(relative @ forward)
        lateral = float(relative @ left)
        vertical = float(relative @ up)
        angular = math.degrees(
            math.atan2(math.hypot(lateral, vertical), max(depth, 1e-12))
        )
        in_frustum = (
            depth > 0
            and abs(lateral / depth) <= float(frame["frustum_x"])
            and abs(vertical / depth) <= float(frame["frustum_y"])
        )
        los = float(state["enemy.los_fraction"]) >= 0.999999
        is_visible = bool(in_frustum and los)
        is_centered = bool(is_visible and angular <= 3.0)
        if is_centered:
            frame_relation = "centered"
        elif is_visible and angular <= 10.0:
            frame_relation = "near_crosshair"
        elif is_visible:
            frame_relation = "visible_far"
        else:
            frame_relation = "offscreen_or_occluded"
        horizontal = float(np.linalg.norm((target - camera)[:2]))
        rows.append(
            {
                **base,
                "enemy_x": float(origin[0]),
                "enemy_y": float(origin[1]),
                "enemy_z": float(origin[2]),
                "distance_3d": float(state["enemy.distance"]),
                "horizontal_distance": horizontal,
                "vertical_delta": float(target[2] - camera[2]),
                "los_fraction": float(state["enemy.los_fraction"]),
                "camera_depth": depth,
                "camera_lateral": lateral,
                "camera_vertical": vertical,
                "screen_x_normalized": (
                    lateral / (depth * float(frame["frustum_x"]))
                    if depth > 0
                    else np.nan
                ),
                "screen_y_normalized": (
                    vertical / (depth * float(frame["frustum_y"]))
                    if depth > 0
                    else np.nan
                ),
                "in_camera_frustum": bool(in_frustum),
                "render_visible_proxy": is_visible,
                "angular_error_deg": angular,
                "centered_3deg": is_centered,
                "frame_relation": frame_relation,
            }
        )
    return pd.DataFrame(rows)


def relation_metrics(package: Path, enemy_present: bool) -> dict[str, Any]:
    relations = target_relation_table(package, enemy_present)
    relations.to_parquet(
        package / "target_relations.parquet",
        index=False,
        compression="zstd",
    )
    if not enemy_present:
        return {
            "actual_target_relation": "enemy_absent",
            "visibility_method": "enemy_entity_absent",
            "visible_frames": 0,
            "centered_frames": 0,
            "centered_fraction": 0.0,
            "minimum_angular_error_deg": None,
        }
    visible = relations["render_visible_proxy"].astype(bool)
    centered = relations["centered_3deg"].astype(bool)
    visible_errors = relations.loc[visible, "angular_error_deg"]
    centered_count = int(centered.sum())
    fraction = centered_count / len(relations)
    if visible_errors.empty:
        relation = "offscreen_or_occluded"
    elif fraction >= 0.8:
        relation = "nearly_continuous_center"
    elif fraction >= 0.2:
        relation = "center_linger"
    elif centered_count:
        relation = "brief_center_pass"
    elif float(visible_errors.min()) <= 10.0:
        relation = "near_crosshair"
    else:
        relation = "visible_far"
    median_distance = float(relations["distance_3d"].median())
    if not math.isfinite(median_distance):
        distance_bin = "unknown_nonfinite"
    elif median_distance < min(lower for lower, _ in DISTANCE_BINS.values()):
                                                                             
                                                                          
                                                       
        distance_bin = "contact_lt64"
    else:
        distance_bin = next(
            (
                name
                for name, (lower, upper) in DISTANCE_BINS.items()
                if lower <= median_distance < upper
            ),
            "beyond_declared_bins",
        )
    return {
        "actual_target_relation": relation,
        "visibility_method": "authoritative_los_plus_camera_frustum",
        "visible_frames": int(visible.sum()),
        "centered_frames": int(centered_count),
        "centered_fraction": fraction,
        "minimum_angular_error_deg": (
            float(visible_errors.min()) if not visible_errors.empty else None
        ),
        "median_enemy_distance": median_distance,
        "actual_distance_bin": distance_bin,
    }


def copytree_verified(source: Path, destination: Path) -> dict[str, str]:
    if destination.exists():
        raise capture.CaptureFailure("refuse_overwrite", str(destination))
    temporary = destination.parent / f".{destination.name}.tmp"
    if temporary.exists():
        raise capture.CaptureFailure("refuse_overwrite", str(temporary))
    shutil.copytree(source, temporary)
    hashes: dict[str, str] = {}
    for source_file in sorted(path for path in source.rglob("*") if path.is_file()):
        relative = source_file.relative_to(source)
        copied = temporary / relative
        source_hash = capture.sha256_file(source_file)
        if source_hash != capture.sha256_file(copied):
            raise capture.CaptureFailure("copy_hash_mismatch", str(copied))
        hashes[str(relative)] = source_hash
    os.rename(temporary, destination)
    return hashes


def run_full_attempt(
    row: dict[str, Any],
    retry: int,
    destination_root: Path,
) -> dict[str, Any]:
    attempt_id = f"{row['episode_id']}_a{retry + 1:02d}"
    destination = destination_root / attempt_id
    if destination.exists():
        attempt_path = destination / "ATTEMPT.json"
        package = destination / "package"
        qa_path = package / "qa.json"
        episode_path = package / "episode.json"
        required = (attempt_path, qa_path, episode_path)
        if not all(path.is_file() for path in required):
            raise capture.CaptureFailure(
                "incomplete_persistent_attempt", str(destination)
            )
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        if attempt.get("scenario") != row:
            raise capture.CaptureFailure(
                "persistent_scenario_mismatch", str(destination)
            )
        current_build = str(capture.build_root())
        if attempt.get("build") != current_build:
            raise capture.CaptureFailure(
                "persistent_build_mismatch",
                f"saved={attempt.get('build')} current={current_build}",
            )
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        metrics = qa.get("target_relation")
        if not isinstance(metrics, dict):
            metrics = relation_metrics(package, bool(row["enemy_present"]))
            qa["target_relation"] = metrics
            atomic_json(qa_path, qa)
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        if episode.get("actual_target_relation") != metrics:
            episode["actual_target_relation"] = metrics
            atomic_json(episode_path, episode)
        hashes = {
            str(path.relative_to(destination)): capture.sha256_file(path)
            for path in sorted(destination.rglob("*"))
            if path.is_file()
        }
        return {
            "episode_id": row["episode_id"],
            "attempt_id": attempt_id,
            "stage": str(destination),
            "qa": qa,
            "target_relation": metrics,
            "persistent_stage": str(destination),
            "persistent_sha256": hashes,
            "resumed": True,
        }

    result = capture.execute_attempt(row, retry=retry, publish=False)
    stage = Path(result["stage"])
    package = stage / "package"
    metrics = relation_metrics(package, bool(row["enemy_present"]))
    qa_path = package / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa["target_relation"] = metrics
    atomic_json(qa_path, qa)
    episode_path = package / "episode.json"
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    episode["actual_target_relation"] = metrics
    atomic_json(episode_path, episode)
    hashes = copytree_verified(stage, destination)
    output = {
        **result,
        "qa": qa,
        "target_relation": metrics,
        "persistent_stage": str(destination),
        "persistent_sha256": hashes,
    }
    capture.clean_stage(stage)
    return output


def known_pair_scenario(
    episode_id: str,
    weapon: str,
    model: str,
    skin: int,
    *,
    expected_outcome: str = "hit_survive",
) -> dict[str, Any]:
    anchors = json.loads(
        capture.ANCHOR_CATALOG_PATH.read_text(encoding="utf-8")
    )
    anchor = anchors["maps"]["stormkeep"]["anchors"][0]
    player_origin = anchor["player_origin"]
    enemy_origin = [
        player_origin[axis]
        + 0.25 * (anchor["enemy_origin"][axis] - player_origin[axis])
        for axis in range(3)
    ]
    return scenario(
        episode_id=episode_id,
        split="preflight",
        dataset_role="causal_interaction",
        category="full_chain_weapon_probe",
        map_name="stormkeep",
        gametype="dm",
        player_origin=player_origin,
        enemy_origin=enemy_origin,
        enemy_model=model,
        enemy_skin=skin,
        enemy_color=68,
        weapon=weapon,
        action_program="causal_sustained",
        seed=2_200_000 + WEAPONS.index(weapon),
        enemy_health=1.0 if expected_outcome == "kill" else 1000.0,
        aim_policy="sustained_tracking",
        expected_outcome=expected_outcome,
        expected_distance_bin="close",
        fire_required=True,
    )


def weapon_probe_checks(row: dict[str, Any]) -> dict[str, Any]:
    stage = Path(row["persistent_stage"])
    events = pd.read_parquet(stage / "package/events.parquet")
    qa = row["qa"]
    counts = Counter(events["event"]) if len(events) else Counter()
    projectile_weapon = row["episode_id"].split("_")[-1]
    return {
        "full_qa_accepted": bool(qa["accepted"]),
        "fire_logged": counts["fire"] >= 1,
        "damage_logged": counts["damage"] >= 1,
        "renderer_nvidia_hardware": capture.is_nvidia_hardware_renderer(
            qa["runtime"]["renderer"]
        ),
        "audio_non_silent": qa["audio"]["peak_s16"] > 0,
        "episode_id_weapon_suffix": bool(projectile_weapon),
    }


def command_preflight(args: argparse.Namespace) -> int:
    capture.require_conda()
    catalog = load_catalog()
    capture.validate_fixed_assets()
    asset_evidence = capture.verify_asset_hashes()
    build = capture.build_root()
    PREFLIGHT_ROOT.mkdir(parents=True, exist_ok=True)

    position_scenarios: list[dict[str, Any]] = []
    for map_name, map_spec in catalog["maps"].items():
        for candidate in map_spec["position_candidates"][:6]:
            position_scenarios.append(
                scenario_for_position_probe(map_name, map_spec, candidate)
            )
    position_results = run_probe_batch(
        "map_position", position_scenarios, build, args.workers
    )
    passing_by_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in position_results:
        if result["pass"]:
            passing_by_map[result["map"]].append(result)
    fallback_scenarios: list[dict[str, Any]] = []
    for map_name, map_spec in catalog["maps"].items():
        if len(passing_by_map[map_name]) >= 4:
            continue
        for candidate in map_spec["position_candidates"][6:]:
            fallback_scenarios.append(
                scenario_for_position_probe(map_name, map_spec, candidate)
            )
    if fallback_scenarios:
        fallback = run_probe_batch(
            "map_position", fallback_scenarios, build, args.workers
        )
        position_results.extend(fallback)
        for result in fallback:
            if result["pass"]:
                passing_by_map[result["map"]].append(result)

    pair_scenarios: list[dict[str, Any]] = []
    for map_name, map_spec in catalog["maps"].items():
        for pair in map_spec["enemy_pair_candidates"]:
            if int(pair["rank"]) == 0:
                pair_scenarios.append(
                    scenario_for_pair_probe(map_name, map_spec, pair)
                )
    pair_results = run_probe_batch(
        "enemy_pair", pair_scenarios, build, args.workers
    )
    pair_pass_by_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in pair_results:
        if result["pass"]:
            pair_pass_by_map[result["map"]].append(result)
    pair_fallback: list[dict[str, Any]] = []
    for map_name, map_spec in catalog["maps"].items():
        if pair_pass_by_map[map_name]:
            continue
        for pair in map_spec["enemy_pair_candidates"]:
            if int(pair["rank"]) == 1:
                pair_fallback.append(
                    scenario_for_pair_probe(map_name, map_spec, pair)
                )
    if pair_fallback:
        fallback = run_probe_batch(
            "enemy_pair", pair_fallback, build, args.workers
        )
        pair_results.extend(fallback)
        for result in fallback:
            if result["pass"]:
                pair_pass_by_map[result["map"]].append(result)

                                                                              
                                                                               
                                                          
    required_distance_bins = set(DISTANCE_BINS)
    dm_distance_bins = {
        result["distance_bin"]
        for result in pair_results
        if result["pass"]
        and catalog["maps"][result["map"]]["preflight_gametype"] == "dm"
    }
    attempted_pair_ids = {result["episode_id"] for result in pair_results}
    targeted_dm_pairs: list[dict[str, Any]] = []
    for distance_bin in sorted(required_distance_bins - dm_distance_bins):
        for map_name, map_spec in catalog["maps"].items():
            if map_spec["preflight_gametype"] != "dm":
                continue
            for pair in map_spec["enemy_pair_candidates"]:
                if (
                    int(pair["rank"]) == 1
                    and pair["distance_bin"] == distance_bin
                ):
                    candidate = scenario_for_pair_probe(
                        map_name, map_spec, pair
                    )
                    if candidate["episode_id"] not in attempted_pair_ids:
                        targeted_dm_pairs.append(candidate)
                        attempted_pair_ids.add(candidate["episode_id"])
    if targeted_dm_pairs:
        targeted = run_probe_batch(
            "enemy_pair", targeted_dm_pairs, build, args.workers
        )
        pair_results.extend(targeted)
        for result in targeted:
            if result["pass"]:
                pair_pass_by_map[result["map"]].append(result)
        dm_distance_bins.update(
            result["distance_bin"]
            for result in targeted
            if result["pass"]
        )

    appearances = catalog["enemy_appearances"]
    weapon_results: list[dict[str, Any]] = []
    for index, weapon in enumerate(WEAPONS):
        appearance = appearances[index % len(appearances)]
        probe = known_pair_scenario(
            f"preflight_weapon_{weapon.lower()}",
            weapon,
            appearance["model"],
            int(appearance["skin"]),
        )
        print(f"full_chain weapon={weapon}", flush=True)
        try:
            result = run_full_attempt(
                probe, 0, PREFLIGHT_ROOT / "full_chain/weapon"
            )
            checks = weapon_probe_checks(result)
            weapon_results.append(
                {
                    "weapon": weapon,
                    "episode_id": probe["episode_id"],
                    "checks": checks,
                    "pass": all(checks.values()),
                    "result": result,
                }
            )
        except Exception as exc:
            stage = (
                capture.TMP_ROOT
                / "raw"
                / f"{probe['episode_id']}_a01"
            )
            failed_path = (
                PREFLIGHT_ROOT
                / "full_chain/weapon_failed"
                / f"{probe['episode_id']}_a01"
            )
            hashes: dict[str, str] = {}
            if stage.exists() and not failed_path.exists():
                hashes = copytree_verified(stage, failed_path)
                capture.clean_stage(stage)
            weapon_results.append(
                {
                    "weapon": weapon,
                    "episode_id": probe["episode_id"],
                    "checks": {"full_qa_accepted": False},
                    "pass": False,
                    "error": f"{type(exc).__name__}:{exc}",
                    "failed_path": (
                        str(failed_path) if failed_path.exists() else None
                    ),
                    "failed_sha256": hashes,
                }
            )

                                                                               
                                                                             
                                                                           
                                                                
    determinism_anchor = json.loads(
        capture.ANCHOR_CATALOG_PATH.read_text(encoding="utf-8")
    )["maps"]["stormkeep"]["anchors"][0]
    determinism_scenario = scenario(
        episode_id="preflight_determinism_no_enemy",
        split="preflight",
        dataset_role="foundation_no_enemy",
        category="determinism",
        map_name="stormkeep",
        gametype="dm",
        player_origin=determinism_anchor["player_origin"],
        weapon="MachineGun",
        action_program="route_combo",
        seed=2_300_001,
        expects_sound=True,
    )
    determinism_runs = [
        run_full_attempt(
            determinism_scenario,
            retry,
            PREFLIGHT_ROOT / "full_chain/determinism",
        )
        for retry in (0, 1)
    ]
    determinism_hashes = [
        row["qa"]["telemetry"]["authoritative_sha256"]
        for row in determinism_runs
    ]
    determinism_pass = len(set(determinism_hashes)) == 1

    map_rows: list[dict[str, Any]] = []
    for map_name, map_spec in catalog["maps"].items():
        passed_positions = sorted(
            passing_by_map[map_name], key=lambda row: row["episode_id"]
        )
        passed_pairs = sorted(
            pair_pass_by_map[map_name], key=lambda row: row["episode_id"]
        )
        map_rows.append(
            {
                "map": map_name,
                "gametype": map_spec["preflight_gametype"],
                "position_attempts": sum(
                    row["map"] == map_name for row in position_results
                ),
                "position_passes": len(passed_positions),
                "stage1_admitted": len(passed_positions) >= 4,
                "accepted_positions": passed_positions,
                "pair_attempts": sum(
                    row["map"] == map_name for row in pair_results
                ),
                "pair_passes": len(passed_pairs),
                "stage2_admitted": bool(passed_pairs),
                "accepted_pairs": passed_pairs,
            }
        )
                                                                            
                                                                          
    audit_rows = sorted(
        position_results + pair_results,
        key=lambda row: (row["probe_kind"], row["episode_id"]),
    )
    atomic_text(
        PREFLIGHT_RESULTS,
        "".join(capture.canonical_json(row) + "\n" for row in audit_rows),
    )

    hard_gates = {
        "official_asset_hashes": bool(asset_evidence["pass"]),
        "catalog_29_maps": catalog["counts"]["maps"] == 29,
        "catalog_9_weapons": catalog["counts"]["weapons"] == 9,
        "catalog_14_appearances": (
            catalog["counts"]["enemy_appearances"] == 14
        ),
        "at_least_one_stage1_map": any(
            row["stage1_admitted"] for row in map_rows
        ),
        "dm_all_distance_bins": (
            dm_distance_bins == required_distance_bins
        ),
        "all_weapon_full_chains": all(row["pass"] for row in weapon_results),
        "hardware_renderer": bool(weapon_results)
        and all(
            capture.is_nvidia_hardware_renderer(
                row.get("result", {})
                .get("qa", {})
                .get("runtime", {})
                .get("renderer", "")
            )
            for row in weapon_results
        ),
        "effective_audio": bool(weapon_results)
        and all(
            row.get("result", {})
            .get("qa", {})
            .get("audio", {})
            .get("peak_s16", 0)
            > 0
            for row in weapon_results
        ),
        "determinism": determinism_pass,
    }
    report = {
        "schema_version": "xonotic-v2-preflight-report-v1",
        "created_utc": capture.utc_now(),
        "build": str(build),
        "source_commit": (build / "SOURCE_COMMIT").read_text().strip(),
        "catalog": str(CATALOG_PATH),
        "catalog_sha256": capture.sha256_file(CATALOG_PATH),
        "hard_gates": hard_gates,
        "pass": all(hard_gates.values()),
        "map_summary": map_rows,
        "stage1_admitted_maps": [
            row["map"] for row in map_rows if row["stage1_admitted"]
        ],
        "stage2_admitted_maps": [
            row["map"] for row in map_rows if row["stage2_admitted"]
        ],
        "dm_distance_bins": sorted(dm_distance_bins),
        "weapon_full_chain": weapon_results,
        "determinism": {
            "episode_id": determinism_scenario["episode_id"],
            "hashes": determinism_hashes,
            "pass": determinism_pass,
            "runs": determinism_runs,
        },
        "notes": [
            "Maps that fail admission remain explicit exclusions.",
            (
                "Enemy screen relation is re-bucketed from authoritative LOS "
                "and the logged camera frustum; a production raster-visibility "
                "hook remains a later hardening item."
            ),
        ],
    }
    atomic_json(PREFLIGHT_REPORT, report)
    lines = [
        "# Xonotic v2 preflight",
        "",
        f"Created UTC: {report['created_utc']}",
        "",
        f"Overall: **{'PASS' if report['pass'] else 'FAIL'}**",
        "",
        f"- Stage 1 admitted maps: {len(report['stage1_admitted_maps'])}/29",
        f"- Stage 2 admitted maps: {len(report['stage2_admitted_maps'])}/29",
        f"- Weapon full chains: {sum(row['pass'] for row in weapon_results)}/9",
        f"- Determinism: {'PASS' if determinism_pass else 'FAIL'}",
        "",
        "| Map | mode | position pass/attempt | Stage 1 | pair pass/attempt | Stage 2 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in map_rows:
        lines.append(
            f"| {row['map']} | {row['gametype']} | "
            f"{row['position_passes']}/{row['position_attempts']} | "
            f"{'yes' if row['stage1_admitted'] else 'no'} | "
            f"{row['pair_passes']}/{row['pair_attempts']} | "
            f"{'yes' if row['stage2_admitted'] else 'no'} |"
        )
    atomic_text(PREFLIGHT_REPORT_MD, "\n".join(lines) + "\n")
    print(f"preflight_report={PREFLIGHT_REPORT}")
    print(f"preflight_pass={report['pass']}")
    return 0 if report["pass"] else 2


def command_smoke(_: argparse.Namespace) -> int:
    """Run one complete enemy-absent chain before the wider preflight."""
    capture.require_conda()
    anchors = json.loads(
        capture.ANCHOR_CATALOG_PATH.read_text(encoding="utf-8")
    )
    origin = anchors["maps"]["stormkeep"]["anchors"][0]["player_origin"]
    row = scenario(
        episode_id="preflight_smoke_enemy_absent",
        split="preflight",
        dataset_role="foundation_no_enemy",
        category="enemy_absent_full_chain_smoke",
        map_name="stormkeep",
        gametype="dm",
        player_origin=origin,
        weapon="MachineGun",
        action_program="route_combo",
        seed=2_000_001,
        expects_sound=True,
    )
    result = run_full_attempt(row, 0, PREFLIGHT_ROOT / "smoke")
    evidence = {
        "schema_version": "xonotic-v2-enemy-absent-smoke-v1",
        "created_utc": capture.utc_now(),
        "pass": bool(result["qa"]["accepted"]),
        "result": result,
    }
    output = PREFLIGHT_ROOT / "SMOKE_ENEMY_ABSENT.json"
    atomic_json(output, evidence)
    print(f"smoke={output}")
    print(f"renderer={result['qa']['runtime']['renderer']}")
    print(f"audio_peak={result['qa']['audio']['peak_s16']}")
    return 0


def select_evenly(rows: list[Any], count: int) -> list[Any]:
    if len(rows) < count:
        raise capture.CaptureFailure(
            "insufficient_preflight_coverage",
            f"available={len(rows)} required={count}",
        )
    indices = np.linspace(0, len(rows) - 1, count, dtype=int)
    return [rows[int(index)] for index in indices]


def build_pilot_scenarios(report: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = load_catalog()
    appearances = [
        (row["model"], int(row["skin"]))
        for row in catalog["enemy_appearances"]
    ]
    colors = (0, 68, 204)
    admitted = [
        row for row in report["map_summary"] if row["stage1_admitted"]
    ]
    selected_maps = select_evenly(admitted, 9)
    no_enemy_programs = (
        ("atomic_forward", "atomic_move_forward", True),
        ("atomic_strafe", "atomic_move_strafe", True),
        ("atomic_view", "atomic_view", False),
        ("atomic_jump", "atomic_jump", True),
        ("route_combo", "route_action_combo", True),
        ("high_motion", "high_motion", True),
        ("environmental_primary", "environmental_primary", True),
        ("environmental_secondary", "environmental_secondary", True),
        ("machinegun_reload", "machinegun_reload_success", True),
    )
    no_enemy_weapons = (
        "Blaster",
        "Shotgun",
        "Mortar",
        "Electro",
        "Crylink",
        "Hagar",
        "Vortex",
        "Devastator",
        "MachineGun",
    )
    route_safe_origin = json.loads(
        capture.ANCHOR_CATALOG_PATH.read_text(encoding="utf-8")
    )["maps"]["stormkeep"]["anchors"][0]["player_origin"]
    scenarios: list[dict[str, Any]] = []
    for index, (map_row, program_spec, weapon) in enumerate(
        zip(selected_maps, no_enemy_programs, no_enemy_weapons), 1
    ):
        program, category, expects_sound = program_spec
        position = map_row["accepted_positions"][
            (index - 1) % len(map_row["accepted_positions"])
        ]
                                                                               
                                                                           
                                                        
        if program == "route_combo":
            map_row = next(row for row in admitted if row["map"] == "stormkeep")
            position = {"player_origin": route_safe_origin}
        scenarios.append(
            scenario(
                episode_id=f"v2_foundation_solo_{index:02d}",
                split="v2_coverage_pilot",
                dataset_role="foundation_no_enemy",
                category=category,
                map_name=map_row["map"],
                gametype=map_row["gametype"],
                player_origin=position["player_origin"],
                weapon=weapon,
                action_program=program,
                seed=3_000_000 + index,
                expects_sound=expects_sound,
                fire_required=category
                in {"environmental_primary", "environmental_secondary"},
                reload_success=category == "machinegun_reload_success",
            )
        )

    pair_rows = [
        pair
        for map_row in report["map_summary"]
        for pair in map_row["accepted_pairs"]
    ]
    if len(pair_rows) < 6:
        raise capture.CaptureFailure(
            "insufficient_enemy_pairs", f"available={len(pair_rows)}"
        )
    distractor_pairs = select_evenly(
        sorted(pair_rows, key=lambda row: (row["map"], row["episode_id"])),
        6,
    )
                                                                              
                                                                           
                                                                    
    distractor_replacements = {
        3: ("implosion", "medium"),
        4: ("glowplant", "very_far"),
    }
    for index, (map_name, distance_bin) in distractor_replacements.items():
        distractor_pairs[index] = next(
            pair
            for pair in pair_rows
            if pair["map"] == map_name
            and pair.get("distance_bin") == distance_bin
        )
    relation_specs = (
        ("offscreen_or_occluded", "relation_offscreen", 150.0),
        ("visible_far", "relation_far", 24.0),
        ("near_crosshair", "relation_near", 7.0),
        ("brief_center_pass", "relation_brief", -12.0),
        ("center_linger", "relation_linger", -4.0),
        ("nearly_continuous_center", "relation_continuous", 0.0),
    )
    for index, (pair, relation_spec) in enumerate(
        zip(distractor_pairs, relation_specs), 1
    ):
        relation, program, yaw_offset = relation_spec
        model, skin = appearances[index - 1]
        scenarios.append(
            scenario(
                episode_id=f"v2_foundation_enemy_{index:02d}",
                split="v2_coverage_pilot",
                dataset_role="foundation_enemy_distractor",
                category=f"enemy_relation_{relation}",
                map_name=pair["map"],
                gametype=pair["gametype"],
                player_origin=pair["player_origin"],
                enemy_origin=pair["enemy_origin"],
                enemy_model=model,
                enemy_skin=skin,
                enemy_color=colors[(index - 1) % len(colors)],
                weapon=WEAPONS[(index + 2) % len(WEAPONS)],
                action_program=program,
                seed=3_100_000 + index,
                yaw_offset=yaw_offset,
                expected_relation=relation,
                expected_distance_bin=pair.get("distance_bin"),
                expects_sound=program != "relation_continuous",
            )
        )

    dm_pairs = [
        pair
        for map_row in report["map_summary"]
        if "dm" in load_catalog()["maps"][map_row["map"]]["gametypes"]
        for pair in map_row["accepted_pairs"]
    ]
    by_distance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in dm_pairs:
        if pair.get("distance_bin"):
            by_distance[pair["distance_bin"]].append(pair)
    missing_bins = [name for name in DISTANCE_BINS if not by_distance[name]]
    if missing_bins:
        raise capture.CaptureFailure(
            "distance_bin_preflight_missing", ",".join(missing_bins)
        )
    causal_specs = (
        ("visible_no_response", "causal_visible_no_response", "no_fire", "close"),
        ("delayed_acquisition", "causal_delayed", "hit_survive", "near"),
        ("pass_offset", "causal_pass", "miss", "medium"),
        ("track_loss_reacquire", "causal_reacquire", "kill", "far"),
        ("sustained_tracking", "causal_sustained", "hit_survive", "very_far"),
        ("delayed_acquisition", "causal_delayed", "kill", "extreme"),
        ("pass_offset", "causal_pass", "miss", "close"),
        ("track_loss_reacquire", "causal_reacquire", "hit_survive", "medium"),
        ("sustained_tracking", "causal_sustained", "kill", "far"),
    )
                                                                       
                                                                            
                                                                        
    causal_weapons = (
        "Blaster",
        "Shotgun",
        "Mortar",
        "MachineGun",
        "Devastator",
        "Vortex",
        "Electro",
        "Hagar",
        "Crylink",
    )
    for index, (spec, weapon) in enumerate(zip(causal_specs, causal_weapons), 1):
        aim_policy, program, outcome, distance_bin = spec
        candidates = sorted(
            by_distance[distance_bin],
            key=lambda row: (
                abs(
                    row["enemy_origin"][2] - row["player_origin"][2]
                ),
                row["map"],
                row["episode_id"],
            ),
        )
                                                                                
                                                                            
                                                                                
                                                                               
                                                                          
        if weapon == "Crylink" and distance_bin == "far":
            pair = candidates[0]
        else:
            pair = candidates[(index - 1) % len(candidates)]
        model, skin = appearances[6 + ((index - 1) % 8)]
        yaw_offset = {
            "visible_no_response": 6.0,
            "delayed_acquisition": -18.0,
            "pass_offset": -17.0,
            "track_loss_reacquire": 0.0,
            "sustained_tracking": 0.0,
        }[aim_policy]
        scenarios.append(
            scenario(
                episode_id=f"v2_causal_{index:02d}",
                split="v2_coverage_pilot",
                dataset_role="causal_interaction",
                category=f"aim_{aim_policy}__outcome_{outcome}",
                map_name=pair["map"],
                gametype="dm",
                player_origin=pair["player_origin"],
                enemy_origin=pair["enemy_origin"],
                enemy_model=model,
                enemy_skin=skin,
                enemy_color=colors[(index + 1) % len(colors)],
                weapon=weapon,
                action_program=program,
                seed=3_200_000 + index,
                yaw_offset=yaw_offset,
                enemy_health=1.0 if outcome == "kill" else 1000.0,
                expected_relation=None,
                aim_policy=aim_policy,
                expected_outcome=outcome,
                expected_distance_bin=distance_bin,
                expects_sound=outcome != "no_fire",
                fire_required=outcome != "no_fire",
            )
        )
    if len(scenarios) != 24:
        raise AssertionError(len(scenarios))
    if {row["weapon"] for row in scenarios} != set(WEAPONS):
        raise AssertionError("weapon coverage")
    enemy_appearances = {
        (row["enemy_model"], row["enemy_skin"])
        for row in scenarios
        if row["enemy_present"]
    }
    if enemy_appearances != set(appearances):
        raise AssertionError(
            f"appearance coverage expected={appearances} actual={enemy_appearances}"
        )
    return scenarios


def write_scenarios(rows: list[dict[str, Any]]) -> None:
    text = "".join(capture.canonical_json(row) + "\n" for row in rows)
    atomic_text(SCENARIOS_PATH, text)


def validate_post_bucket(
    row: dict[str, Any], qa: dict[str, Any]
) -> None:
    metrics = qa["target_relation"]
    expected_relation = row["policy_labels"].get("expected_target_relation")
    if expected_relation and metrics["actual_target_relation"] != expected_relation:
        raise capture.CaptureFailure(
            "target_relation_mismatch",
            f"expected={expected_relation} "
            f"actual={metrics['actual_target_relation']}",
        )
    expected_distance = row["policy_labels"].get("expected_distance_bin")
    if (
        row["enemy_present"]
        and expected_distance
        and metrics["actual_distance_bin"] != expected_distance
    ):
        raise capture.CaptureFailure(
            "distance_bin_mismatch",
            f"expected={expected_distance} "
            f"actual={metrics['actual_distance_bin']}",
        )


def semantic_outcome(
    row: dict[str, Any], qa: dict[str, Any]
) -> str:
    """Return the training-facing outcome without discarding engine detail."""
    if row["dataset_role"] != "causal_interaction":
        return "not_applicable"
    events = qa["events"]
    if events["fire_count"] == 0:
        return "no_fire"
    if events["death_count"] > 0:
        return "kill"
    if events["damage_count"] > 0:
        return "hit_survive"
    return "miss"


def publish_pilot_attempt(
    row: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    stage = Path(result["stage"])
    attempt_id = result["attempt_id"]
    package = stage / "package"
    episode_destination = PILOT_ROOT / "episodes" / row["episode_id"]
    raw_destination = PILOT_ROOT / "raw" / attempt_id
    package_hashes = copytree_verified(package, episode_destination)
    raw_hashes = copytree_verified(stage, raw_destination)
    qa = json.loads(
        (episode_destination / "qa.json").read_text(encoding="utf-8")
    )
    manifest = {
        "schema_version": "xonotic-v2-coverage-pilot-manifest-v2",
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "split": row["split"],
        "dataset_role": row["dataset_role"],
        "category": row["category"],
        "map": row["map"],
        "gametype": row["gametype"],
        "player_origin": row["player"]["origin"],
        "enemy_present": row["enemy_present"],
        "enemy_origin": (
            row["enemy"]["origin"] if row["enemy_present"] else None
        ),
        "enemy_model": row["enemy_model"],
        "enemy_skin": row["enemy_skin"],
        "enemy_color": row["enemy_color"],
        "weapon": row["weapon"],
        "aim_policy": row["policy_labels"].get("aim_policy"),
        "expected_target_relation": row["policy_labels"].get(
            "expected_target_relation"
        ),
        "actual_target_relation": qa["target_relation"][
            "actual_target_relation"
        ],
        "expected_distance_bin": row["policy_labels"].get(
            "expected_distance_bin"
        ),
        "actual_distance_bin": qa["target_relation"].get(
            "actual_distance_bin"
        ),
        "expected_outcome": row["acceptance"].get("actual_outcome"),
        "intent_outcome": row["acceptance"].get("actual_outcome"),
        "actual_outcome": semantic_outcome(row, qa),
        "semantic_outcome": semantic_outcome(row, qa),
        "engine_outcome_bin": qa["events"]["actual_outcome_bin"],
        "hit_rate": qa["events"]["hit_rate"],
        "episode_path": str(episode_destination),
        "raw_path": str(raw_destination),
        "package_sha256": package_hashes,
        "raw_sha256": raw_hashes,
        "qa": {
            "renderer": qa["runtime"]["renderer"],
            "frames": qa["video"]["frames"],
            "audio_samples": qa["audio"]["samples_per_channel"],
            "frame_tick_mapping": qa["mapping"]["success_rate"],
            "audio_onset_max_ms": qa["audio"]["max_onset_error_ms"],
            "event_linkage": qa["events"]["linkage_rate"],
            "authoritative_sha256": qa["telemetry"][
                "authoritative_sha256"
            ],
        },
        "accepted_utc": capture.utc_now(),
    }
    capture.append_jsonl(ACCEPTED_PATH, manifest)
    capture.clean_stage(stage)
    return manifest


def reject_pilot_attempt(
    row: dict[str, Any],
    retry: int,
    failure: Exception,
    stage: Path,
) -> dict[str, Any]:
    attempt_id = f"{row['episode_id']}_a{retry + 1:02d}"
    destination = PILOT_ROOT / "rejected" / attempt_id
    hashes: dict[str, str] = {}
    if stage.exists() and not destination.exists():
        hashes = copytree_verified(stage, destination)
        capture.clean_stage(stage)
    result = {
        "schema_version": "xonotic-v2-coverage-pilot-reject-v1",
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "split": row["split"],
        "dataset_role": row["dataset_role"],
        "category": row["category"],
        "reason": (
            failure.reason
            if isinstance(failure, capture.CaptureFailure)
            else type(failure).__name__
        ),
        "detail": (
            failure.detail
            if isinstance(failure, capture.CaptureFailure)
            else str(failure)
        ),
        "preserved_path": str(destination) if destination.exists() else None,
        "preserved_sha256": hashes,
        "rejected_utc": capture.utc_now(),
    }
    capture.append_jsonl(REJECTS_PATH, result)
    return result


def command_generate(_: argparse.Namespace) -> int:
    capture.require_conda()
    if not PREFLIGHT_REPORT.is_file():
        raise capture.CaptureFailure("preflight_report_missing")
    report = json.loads(PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    if not report.get("pass"):
        raise capture.CaptureFailure("preflight_not_passed")
    rows = build_pilot_scenarios(report)
    write_scenarios(rows)
    print(f"scenarios={SCENARIOS_PATH}")
    print(f"count={len(rows)}")
    print(f"roles={dict(Counter(row['dataset_role'] for row in rows))}")
    return 0


def load_pilot_scenarios() -> list[dict[str, Any]]:
    if not SCENARIOS_PATH.is_file():
        raise capture.CaptureFailure("v2_scenarios_missing")
    return capture.load_jsonl(SCENARIOS_PATH)


def command_pilot(args: argparse.Namespace) -> int:
    capture.require_conda()
    report = json.loads(PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    if not report.get("pass"):
        raise capture.CaptureFailure("preflight_not_passed")
    rows = load_pilot_scenarios()
    existing = {
        row["episode_id"]: row
        for row in capture.load_jsonl(ACCEPTED_PATH)
    }
    prior_rejects = capture.load_jsonl(REJECTS_PATH)
    for ordinal, row in enumerate(rows, 1):
        if row["episode_id"] in existing:
            print(f"skip accepted {row['episode_id']}", flush=True)
            continue
        accepted = False
        attempt_prefix = f"{row['episode_id']}_a"
        prior_attempt_numbers = [
            int(str(reject["attempt_id"]).removeprefix(attempt_prefix))
            for reject in prior_rejects
            if str(reject.get("attempt_id", "")).startswith(attempt_prefix)
            and str(reject["attempt_id"]).removeprefix(attempt_prefix).isdigit()
        ]
        retry_base = max(prior_attempt_numbers, default=0)
        for retry in range(retry_base, retry_base + args.max_retries):
            stage = (
                capture.TMP_ROOT
                / "raw"
                / f"{row['episode_id']}_a{retry + 1:02d}"
            )
            print(
                f"capture {ordinal}/{len(rows)} id={row['episode_id']} "
                f"role={row['dataset_role']} category={row['category']} "
                f"attempt={retry + 1} "
                f"try={retry - retry_base + 1}/{args.max_retries}",
                flush=True,
            )
            try:
                result = capture.execute_attempt(row, retry, publish=False)
                package = Path(result["stage"]) / "package"
                metrics = relation_metrics(
                    package, bool(row["enemy_present"])
                )
                qa_path = package / "qa.json"
                qa = json.loads(qa_path.read_text(encoding="utf-8"))
                qa["target_relation"] = metrics
                validate_post_bucket(row, qa)
                atomic_json(qa_path, qa)
                episode_path = package / "episode.json"
                episode = json.loads(
                    episode_path.read_text(encoding="utf-8")
                )
                episode["actual_target_relation"] = metrics
                atomic_json(episode_path, episode)
                manifest = publish_pilot_attempt(row, result)
                existing[row["episode_id"]] = manifest
                accepted = True
                print(
                    f"accepted {row['episode_id']} "
                    f"relation={manifest['actual_target_relation']} "
                    f"outcome={manifest['actual_outcome']}",
                    flush=True,
                )
                break
            except Exception as exc:
                rejection = reject_pilot_attempt(
                    row, retry, exc, stage
                )
                prior_rejects.append(rejection)
                print(
                    f"reject {row['episode_id']} "
                    f"reason={rejection['reason']} "
                    f"detail={rejection['detail']}",
                    flush=True,
                )
        if not accepted:
            raise capture.CaptureFailure(
                "v2_pilot_retry_exhausted", row["episode_id"]
            )
    manifests = capture.load_jsonl(ACCEPTED_PATH)
    expected_ids = {row["episode_id"] for row in rows}
    actual_ids = {row["episode_id"] for row in manifests}
    checks = {
        "exact_24": len(manifests) == 24 == len(actual_ids),
        "scenario_ids_exact": actual_ids == expected_ids,
        "split_exact": all(
            row["split"] == "v2_coverage_pilot" for row in manifests
        ),
        "roles": Counter(row["dataset_role"] for row in manifests)
        == Counter(
            {
                "foundation_no_enemy": 9,
                "foundation_enemy_distractor": 6,
                "causal_interaction": 9,
            }
        ),
        "relations": set(
            row["actual_target_relation"]
            for row in manifests
            if row["dataset_role"] == "foundation_enemy_distractor"
        )
        == set(RELATIONS),
        "aim_policies": set(
            row["aim_policy"]
            for row in manifests
            if row["dataset_role"] == "causal_interaction"
        )
        == set(AIM_POLICIES),
        "distance_bins": set(
            row["actual_distance_bin"]
            for row in manifests
            if row["dataset_role"] == "causal_interaction"
        )
        == set(DISTANCE_BINS),
        "weapons": {row["weapon"] for row in manifests} == set(WEAPONS),
        "appearances": len(
            {
                (row["enemy_model"], row["enemy_skin"])
                for row in manifests
                if row["enemy_present"]
            }
        )
        == 14,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v2_pilot_final_gate", capture.canonical_json(checks)
        )
    summary = {
        "schema_version": "xonotic-v2-coverage-pilot-summary-v1",
        "created_utc": capture.utc_now(),
        "checks": checks,
        "accepted": len(manifests),
        "rejected_attempts": len(capture.load_jsonl(REJECTS_PATH)),
        "roles": dict(Counter(row["dataset_role"] for row in manifests)),
        "categories": dict(Counter(row["category"] for row in manifests)),
        "maps": dict(Counter(row["map"] for row in manifests)),
        "weapons": dict(Counter(row["weapon"] for row in manifests)),
        "manifest": str(ACCEPTED_PATH),
    }
    atomic_json(PILOT_ROOT / "PILOT_SUMMARY.json", summary)
    print(f"v2_coverage_pilot_complete accepted={len(manifests)}")
    return 0


def make_preview(manifest: dict[str, Any]) -> Path:
    source = Path(manifest["episode_path"]) / "video.mkv"
    media = PREVIEW_ROOT / "media"
    media.mkdir(parents=True, exist_ok=True)
    destination = media / f"{manifest['episode_id']}.mp4"
    if destination.is_file():
        return destination
    temporary = media / f".{manifest['episode_id']}.tmp.mp4"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        temporary.unlink(missing_ok=True)
        raise capture.CaptureFailure(
            "preview_encode_failed",
            f"episode={manifest['episode_id']} rc={completed.returncode}",
        )
    os.replace(temporary, destination)
    return destination


def command_html(_: argparse.Namespace) -> int:
    capture.require_conda()
    rows = capture.load_jsonl(ACCEPTED_PATH)
    if len(rows) != 24:
        raise capture.CaptureFailure(
            "preview_requires_complete_pilot", f"accepted={len(rows)}"
        )
    for index, row in enumerate(rows, 1):
        path = make_preview(row)
        print(f"preview {index}/{len(rows)} {path}", flush=True)
    role_options = sorted({row["dataset_role"] for row in rows})
    category_options = sorted({row["category"] for row in rows})
    cards: list[str] = []
    for row in rows:
        relation = row.get("actual_target_relation") or "-"
        aim = row.get("aim_policy") or "-"
        distance = row.get("actual_distance_bin") or "-"
        outcome = (
            row.get("semantic_outcome")
            or row.get("actual_outcome")
            or "-"
        )
        engine_outcome = row.get("engine_outcome_bin") or "-"
        appearance = (
            f"{row['enemy_model']} / skin {row['enemy_skin']}"
            if row["enemy_present"]
            else "enemy absent"
        )
        cards.append(
            f"""
<article class="card" data-role="{html.escape(row['dataset_role'])}"
 data-category="{html.escape(row['category'])}">
  <video controls preload="metadata" src="media/{html.escape(row['episode_id'])}.mp4"></video>
  <h2>{html.escape(row['episode_id'])}</h2>
  <p class="role">{html.escape(row['dataset_role'])}</p>
  <dl>
    <dt>Category</dt><dd>{html.escape(row['category'])}</dd>
    <dt>Map / mode</dt><dd>{html.escape(row['map'])} / {html.escape(row['gametype'])}</dd>
    <dt>Weapon</dt><dd>{html.escape(row['weapon'])}</dd>
    <dt>Enemy</dt><dd>{html.escape(appearance)}</dd>
    <dt>Target relation</dt><dd>{html.escape(str(relation))}</dd>
    <dt>Aim policy</dt><dd>{html.escape(str(aim))}</dd>
    <dt>Distance</dt><dd>{html.escape(str(distance))}</dd>
    <dt>Semantic outcome</dt><dd>{html.escape(str(outcome))}</dd>
    <dt>Engine outcome bin</dt><dd>{html.escape(str(engine_outcome))}</dd>
  </dl>
</article>"""
        )
    role_buttons = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in role_options
    )
    category_buttons = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in category_options
    )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xonotic v2 分类小样本</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, system-ui, sans-serif; }}
body {{ margin:0; background:#0c0f14; color:#e8edf4; }}
header {{ position:sticky; top:0; z-index:2; padding:18px 24px;
  background:#111722ee; backdrop-filter:blur(12px); border-bottom:1px solid #293244; }}
h1 {{ margin:0 0 8px; font-size:22px; }}
.controls {{ display:flex; gap:12px; flex-wrap:wrap; }}
select {{ background:#1b2330; color:#fff; border:1px solid #3b465a;
  border-radius:7px; padding:7px 10px; }}
main {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr));
  gap:18px; padding:22px; }}
.card {{ background:#141a24; border:1px solid #293244; border-radius:12px;
  overflow:hidden; box-shadow:0 8px 24px #0005; }}
video {{ display:block; width:100%; aspect-ratio:16/9; background:#000; }}
h2,.role,dl {{ margin-left:16px; margin-right:16px; }}
h2 {{ margin-bottom:4px; font-size:17px; }}
.role {{ color:#7ed0ff; margin-top:0; font-size:13px; }}
dl {{ display:grid; grid-template-columns:118px 1fr; gap:5px 10px; font-size:13px; }}
dt {{ color:#91a0b6; }} dd {{ margin:0; overflow-wrap:anywhere; }}
.hidden {{ display:none; }}
</style>
</head>
<body>
<header>
<h1>Xonotic v2 coverage pilot — 24 条分类预览</h1>
<div class="controls">
<label>Dataset role <select id="role"><option value="">全部</option>{role_buttons}</select></label>
<label>Category <select id="category"><option value="">全部</option>{category_buttons}</select></label>
</div>
</header>
<main>{''.join(cards)}</main>
<script>
const role=document.querySelector('#role'), category=document.querySelector('#category');
function filterCards(){{
 document.querySelectorAll('.card').forEach(card=>{{
  const visible=(!role.value||card.dataset.role===role.value)&&
   (!category.value||card.dataset.category===category.value);
  card.classList.toggle('hidden',!visible);
  if(!visible) card.querySelector('video').pause();
 }});
}}
role.addEventListener('change',filterCards);
category.addEventListener('change',filterCards);
</script>
</body>
</html>
"""
    atomic_text(PREVIEW_ROOT / "index.html", document)
    print(f"html={PREVIEW_ROOT / 'index.html'}")
    return 0


def command_report(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(ACCEPTED_PATH)
    rejects = capture.load_jsonl(REJECTS_PATH)
    qa_rows = [
        json.loads(
            (Path(row["episode_path"]) / "qa.json").read_text(
                encoding="utf-8"
            )
        )
        for row in rows
    ]
    lines = [
        "# Xonotic v2 coverage Pilot report",
        "",
        f"Created UTC: {capture.utc_now()}",
        "",
        f"- Accepted: {len(rows)}",
        f"- Rejected attempts: {len(rejects)}",
        f"- Manifest: `{ACCEPTED_PATH}`",
        f"- HTML: `{PREVIEW_ROOT / 'index.html'}`",
        (
            "- Renderer: `"
            + (
                qa_rows[0]["runtime"]["renderer"]
                if qa_rows
                else "not available"
            )
            + "`"
        ),
        "",
        "## Coverage",
        "",
        "| Role | Count |",
        "|---|---:|",
    ]
    for role, count in Counter(row["dataset_role"] for row in rows).items():
        lines.append(f"| {role} | {count} |")
    lines += [
        "",
        "## QA extrema",
        "",
        (
            f"- Frame-to-tick minimum mapping rate: "
            f"{min((qa['mapping']['success_rate'] for qa in qa_rows), default=0):.6f}"
        ),
        (
            f"- Maximum audio onset error: "
            f"{max((qa['audio']['max_onset_error_ms'] for qa in qa_rows), default=0):.6f} ms"
        ),
        (
            f"- Minimum event linkage: "
            f"{min((qa['events']['linkage_rate'] for qa in qa_rows), default=0):.6f}"
        ),
        "",
        "This bounded Pilot is not part of either formal training split.",
    ]
    output = PILOT_ROOT / "V2_COVERAGE_PILOT_REPORT.md"
    atomic_text(output, "\n".join(lines) + "\n")
    print(f"report={output}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--workers", type=int, default=6)
    preflight.set_defaults(func=command_preflight)
    smoke = subparsers.add_parser("smoke")
    smoke.set_defaults(func=command_smoke)
    generate = subparsers.add_parser("generate")
    generate.set_defaults(func=command_generate)
    pilot = subparsers.add_parser("pilot")
    pilot.add_argument("--max-retries", type=int, default=3)
    pilot.set_defaults(func=command_pilot)
    html_parser = subparsers.add_parser("html")
    html_parser.set_defaults(func=command_html)
    report = subparsers.add_parser("report")
    report.set_defaults(func=command_report)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
