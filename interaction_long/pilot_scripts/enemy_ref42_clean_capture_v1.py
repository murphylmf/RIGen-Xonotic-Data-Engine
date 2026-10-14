                      
"""Capture a clean, exact 42-appearance Xonotic enemy reference bank.

The target Stage-2 rollouts address references by ``appearance_id`` and
``ref_set_id``.  This utility materializes those reference sets with the same
official Xonotic runtime used by target capture.  One physical enemy entity is
shown on a fixed map, at a fixed distance and camera pose, with five explicit
body yaws.  All first-person weapon and HUD layers are disabled by an isolated
client overlay.  Raw AVI and demos stay on node-local scratch and are deleted
after PNG extraction.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_SCRIPT = Path(__file__).resolve()
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_CAPTURE_CLIENT_OVERLAY",
    "configs/capture_client_ref42_clean.cfg",
)
os.environ.setdefault("XONOTIC_LIVE_TIME_SCALE", "2")
os.environ.setdefault("XONOTIC_OFFLINE_ACCELERATE", "1")
os.environ.setdefault("XONOTIC_LIVE_TIMEOUT_SECONDS", "480")
os.environ.setdefault("XONOTIC_RENDER_TIMEOUT_SECONDS", "600")
os.environ.setdefault("XONOTIC_ENGINE_NET_TIMEOUT_SECONDS", "660")
os.environ.setdefault("XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "120")

sys.path.insert(0, str(ROOT / "scripts"))
import xonotic_capture as capture              
import xonotic_stage1_reusable as reusable              


RELEASE_ID = "xonotic_enemy_ref42_clean_v1"
REF_SET_SCHEMA = "xonotic-enemy-reference-set-v1"
MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
OUTPUT_ROOT = Path("./rigen_data/reference_assets") / RELEASE_ID
APPEARANCE_SOURCE = Path(
    "./configs/"
    "xonotic_stage2_enemy_motion_appearance_manual_v2.jsonl"
)
BASE_SCENARIO = ROOT / (
    "manifests/stage2_long60_multi_enemy_ref42_30h_20260828_v5/"
    "episodes/s2l60ref42_v5_000023/scenario.json"
)
BUILD_GLOB = "build/capture-9efed7e5733b-aarch64"
BUILD_COMMIT = "9efed7e5733bf6062865044060d4be390309958a"

PLAYER_ORIGIN = (608.4, 1429.2, -104.0)
BASE_ENEMY_ORIGIN = (874.9525038849215, 1472.2088673726576, -104.0)
REFERENCE_DISTANCE = 200.0
CROP_SIZE = 320
CROP_Y = 270
OUTPUT_SIZE = 512
VIEWS = (
    ("front", 0.0),
    ("left_3q", -45.0),
    ("right_3q", 45.0),
    ("side", 90.0),
    ("back_3q", 135.0),
)
REFERENCE_PRIME_TICKS = capture.VIDEO_FPS
REFERENCE_GAP_TICKS = capture.VIDEO_FPS
REFERENCE_ACTIVE_START = REFERENCE_PRIME_TICKS + REFERENCE_GAP_TICKS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial.{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(temporary, path)


def root_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def load_appearances() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with APPEARANCE_SOURCE.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            source = json.loads(line)
            if source.get("unit_type") != "enemy_visual":
                continue
            appearance_id = str(source["unit_id"])
            model, skin_text, color_text = appearance_id.rsplit("_", 2)
            if not skin_text.startswith("skin") or not color_text.startswith("color"):
                raise ValueError(f"invalid appearance id: {appearance_id}")
            rows.append(
                {
                    "appearance_id": appearance_id,
                    "model": model,
                    "skin": int(skin_text.removeprefix("skin")),
                    "color": int(color_text.removeprefix("color")),
                    "description": source["result"]["appearance_phrase"],
                    "ref_set_id": f"{appearance_id}_refset_v1",
                }
            )
    rows.sort(key=lambda row: row["appearance_id"])
    if len(rows) != 42:
        raise RuntimeError(f"expected 42 enemy appearances, got {len(rows)}")
    models = {row["model"] for row in rows}
    skins = {row["skin"] for row in rows}
    colors = {row["color"] for row in rows}
    if len(models) != 7 or skins != {0, 1} or colors != {0, 68, 204}:
        raise RuntimeError(
            f"unexpected appearance cartesian product: "
            f"models={sorted(models)} skins={sorted(skins)} colors={sorted(colors)}"
        )
    return rows


def reference_enemy_origin() -> tuple[float, float, float]:
    dx = BASE_ENEMY_ORIGIN[0] - PLAYER_ORIGIN[0]
    dy = BASE_ENEMY_ORIGIN[1] - PLAYER_ORIGIN[1]
    norm = math.hypot(dx, dy)
    return (
        PLAYER_ORIGIN[0] + REFERENCE_DISTANCE * dx / norm,
        PLAYER_ORIGIN[1] + REFERENCE_DISTANCE * dy / norm,
        PLAYER_ORIGIN[2],
    )


def camera_yaw(enemy_origin: tuple[float, float, float]) -> float:
    return math.degrees(
        math.atan2(
            enemy_origin[1] - PLAYER_ORIGIN[1],
            enemy_origin[0] - PLAYER_ORIGIN[0],
        )
    )


def front_facing_yaw(enemy_origin: tuple[float, float, float]) -> float:
    return math.degrees(
        math.atan2(
            PLAYER_ORIGIN[1] - enemy_origin[1],
            PLAYER_ORIGIN[0] - enemy_origin[0],
        )
    )


def write_actions(path: Path, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"#seed,{seed}\n")
        writer = csv.DictWriter(handle, fieldnames=capture.ACTION_COLUMNS)
        writer.writeheader()
        for tick in range(capture.TOTAL_TICKS):
            writer.writerow(
                {
                    "tick": tick,
                    "forward": 0.0,
                    "strafe": 0.0,
                    "yaw_delta": 0.0,
                    "pitch_delta": 0.0,
                    "jump": 0,
                    "primary": 0,
                    "secondary": 0,
                    "weapon_impulse": 0,
                    "reload": 0,
                }
            )


def sample_frames() -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    active_ticks = capture.OUTPUT_TICKS - REFERENCE_ACTIVE_START
    for view_index, (view_name, yaw_offset) in enumerate(VIEWS):
        lower = (
            REFERENCE_ACTIVE_START
            + view_index * active_ticks // len(VIEWS)
        )
        upper = (
            REFERENCE_ACTIVE_START
            + (view_index + 1) * active_ticks // len(VIEWS)
        )
        frame_index = (lower + upper) // 2
        samples.append(
            {
                "slot_index": 1,
                "view_index": view_index,
                "view": view_name,
                "yaw_offset_degrees": yaw_offset,
                "frame_index": frame_index,
                "seconds": frame_index / capture.VIDEO_FPS,
            }
        )
    return samples


def write_timeline(
    path: Path,
    actors: list[dict[str, Any]],
    enemy_origin: tuple[float, float, float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    facing = front_facing_yaw(enemy_origin)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "kind",
                "tick_or_slot",
                "actor_or_id",
                "x_or_model",
                "y_or_skin",
                "z_or_color",
                "vx_or_health",
                "vy_or_armor",
                "vz",
                "yaw",
                "jump",
            ]
        )
        for slot, actor in enumerate(actors, 1):
            writer.writerow(
                [
                    "actor",
                    slot,
                    f"enemy_{slot - 1}",
                    actor["model"],
                    actor["skin"],
                    actor["color"],
                    999.0,
                    0.0,
                ]
            )
        for tick in range(capture.TOTAL_TICKS):
            if tick < capture.WARMUP_TICKS:
                writer.writerow(["tick", tick, 0, 0, 0, 0, 0, 0, 0, 0, 0])
                continue
            output_tick = tick - capture.WARMUP_TICKS
            if output_tick < REFERENCE_PRIME_TICKS:
                slot_index = 0
                view_index = 0
            elif output_tick < REFERENCE_ACTIVE_START:
                writer.writerow(["tick", tick, 0, 0, 0, 0, 0, 0, 0, 0, 0])
                continue
            else:
                slot_index = 1
                active_ticks = capture.OUTPUT_TICKS - REFERENCE_ACTIVE_START
                active_tick = output_tick - REFERENCE_ACTIVE_START
                view_index = min(
                    len(VIEWS) - 1,
                    active_tick * len(VIEWS) // active_ticks,
                )
            yaw = facing + VIEWS[view_index][1]
            writer.writerow(
                [
                    "tick",
                    tick,
                    slot_index + 1,
                    f"{enemy_origin[0]:.9f}",
                    f"{enemy_origin[1]:.9f}",
                    f"{enemy_origin[2]:.9f}",
                    "0.0",
                    "0.0",
                    "0.0",
                    f"{yaw:.9f}",
                    0,
                ]
            )


def build_scenario(
    template: dict[str, Any],
    episode_id: str,
    seed: int,
    actors: list[dict[str, Any]],
    actions: Path,
    timeline: Path,
    enemy_origin: tuple[float, float, float],
) -> dict[str, Any]:
    scenario = copy.deepcopy(template)
    scenario.update(
        {
            "schema_version": "xonotic-enemy-reference-capture-scenario-v1",
            "release_id": RELEASE_ID,
            "episode_id": episode_id,
            "split": "reference",
            "dataset_role": "enemy_reference_asset_capture",
            "training_admitted": False,
            "formal_collection_authorized": False,
            "runtime_build_required": BUILD_GLOB.removeprefix("build/"),
            "runtime_source_commit_required": BUILD_COMMIT,
            "seed": seed,
            "anchor_id": "geoplanetary_enemy_ref42_clean_v1",
            "enemy_actor_count": len(actors),
            "physical_enemy_entity_count": 1,
            "enemy_model": actors[0]["model"],
            "enemy_skin": actors[0]["skin"],
            "enemy_color": actors[0]["color"],
            "frozen_actions_path": root_relative(actions),
            "frozen_actions_sha256": sha256(actions),
            "enemy_timeline_path": root_relative(timeline),
            "enemy_timeline_sha256": sha256(timeline),
            "action_program": "fixed_camera_no_input_reference_capture_v1",
            "appearance_order": [row["appearance_id"] for row in actors],
            "actor_order": [f"enemy_{index}" for index in range(len(actors))],
            "actors": [
                {
                    "slot": index + 1,
                    "actor_id": f"enemy_{index}",
                    "appearance_id": actor["appearance_id"],
                    "ref_set_id": actor["ref_set_id"],
                    "model": actor["model"],
                    "skin": actor["skin"],
                    "color": actor["color"],
                    "health": 999.0,
                    "armor": 0.0,
                    "description": actor["description"],
                }
                for index, actor in enumerate(actors)
            ],
            "actor_bindings": [
                {
                    "actor_id": f"enemy_{index}",
                    "appearance_id": actor["appearance_id"],
                    "ref_set_id": actor["ref_set_id"],
                }
                for index, actor in enumerate(actors)
            ],
            "enemy_horizontal_speed_units_per_second": 0.0,
            "camera_policy": {
                "name": "fixed_reference_camera_v1",
                "reads_enemy_state": False,
                "yaw_degrees": camera_yaw(enemy_origin),
                "pitch_degrees": -1.0,
            },
            "player_action_policy": {
                "name": "fully_idle_reference_capture_v1",
                "reads_enemy_state": False,
                "reads_live_player_state": False,
            },
            "reference_capture": {
                "schema_version": REF_SET_SCHEMA,
                "ref_asset_release_id": RELEASE_ID,
                "views": [name for name, _ in VIEWS],
                "yaw_offsets_degrees": [offset for _, offset in VIEWS],
                "distance_units": REFERENCE_DISTANCE,
                "source_width": capture.WIDTH,
                "source_height": capture.HEIGHT,
                "crop_x": (capture.WIDTH - CROP_SIZE) // 2,
                "crop_y": CROP_Y,
                "crop_size": CROP_SIZE,
                "output_size": OUTPUT_SIZE,
                "first_person_weapon_visible": False,
                "hud_visible": False,
                "raw_avi_retained": False,
                "forced_respawn_before_sampling": True,
                "prime_ticks": REFERENCE_PRIME_TICKS,
                "despawn_gap_ticks": REFERENCE_GAP_TICKS,
            },
            "storage_policy": {
                "raw_avi_retained": False,
                "demo_retained": False,
                "published_media": "five_png_views_per_appearance",
            },
        }
    )
    scenario["player"].update(
        {
            "origin": list(PLAYER_ORIGIN),
            "yaw": camera_yaw(enemy_origin),
            "pitch": -1.0,
            "health": 5000.0,
            "armor": 0.0,
            "clip": 60.0,
            "reserve": 600.0,
        }
    )
    scenario["enemy"] = {
        "origin": list(enemy_origin),
        "yaw": front_facing_yaw(enemy_origin),
        "motion": 0,
        "motion_start_tick": capture.WARMUP_TICKS,
        "motion_distance": 0.0,
        "motion_vector": [0.0, 0.0, 0.0],
        "health": 999.0,
        "armor": 0.0,
    }
    scenario["enemy_policy"] = {
        "name": "timeline_fixed_pose_reference_v1",
        "reads_camera": False,
        "reads_crosshair": False,
        "reads_player": False,
        "movement_audio": "off",
    }
    scenario["encounters"] = []
    scenario["prompt_schedule"] = []
    scenario["active_ref_schedule"] = []
    scenario["lifecycle_policy"] = {
        "expected_kill_count": 0,
        "reference_capture_only": True,
    }
    scenario["camera_schedule_sha256"] = sha256(actions)
    scenario["player_motion_schedule_sha256"] = sha256(actions)
    return scenario


def prepare() -> None:
    appearances = load_appearances()
    template = json.loads(BASE_SCENARIO.read_text(encoding="utf-8"))
    enemy_origin = reference_enemy_origin()
    rows: list[dict[str, Any]] = []
                                                                          
                                                                     
                                                                             
                                                                             
                                              
    for episode_index, appearance in enumerate(appearances):
        actors = [appearance, appearance]
        episode_id = f"ref42clean_v1_{episode_index:03d}"
        seed = 2608285100 + episode_index
        episode_root = MANIFEST_ROOT / "episodes" / episode_id
        actions = episode_root / "actions.csv"
        timeline = episode_root / "enemy_timeline.csv"
        scenario_path = episode_root / "scenario.json"
        write_actions(actions, seed)
        write_timeline(timeline, actors, enemy_origin)
        scenario = build_scenario(
            template,
            episode_id,
            seed,
            actors,
            actions,
            timeline,
            enemy_origin,
        )
        atomic_json(scenario_path, scenario)
        rows.append(
            {
                "schema_version": "xonotic-enemy-reference-capture-manifest-v1",
                "release_id": RELEASE_ID,
                "episode_index": episode_index,
                "episode_id": episode_id,
                "seed": seed,
                "appearance_order": [appearance["appearance_id"]],
                "ref_set_ids": [appearance["ref_set_id"]],
                "scenario_path": root_relative(scenario_path),
                "scenario_sha256": sha256(scenario_path),
                "sample_frames": sample_frames(),
                "raw_avi_retained": False,
            }
        )
    manifest = MANIFEST_ROOT / "manifest.jsonl"
    atomic_jsonl(manifest, rows)
    atomic_json(
        MANIFEST_ROOT / "PREPARED.json",
        {
            "schema_version": "xonotic-enemy-reference-prepared-v1",
            "created_utc": utc_now(),
            "release_id": RELEASE_ID,
            "episodes": len(rows),
            "appearances": len(appearances),
            "views_per_appearance": len(VIEWS),
            "images_expected": len(appearances) * len(VIEWS),
            "manifest_path": root_relative(manifest),
            "manifest_sha256": sha256(manifest),
            "appearance_source": str(APPEARANCE_SOURCE),
            "appearance_source_sha256": sha256(APPEARANCE_SOURCE),
            "client_overlay": "configs/capture_client_ref42_clean.cfg",
            "client_overlay_sha256": sha256(
                ROOT / "configs/capture_client_ref42_clean.cfg"
            ),
            "capture_script": root_relative(CAPTURE_SCRIPT),
            "capture_script_sha256": sha256(CAPTURE_SCRIPT),
            "runtime_build": BUILD_GLOB,
            "runtime_source_commit": BUILD_COMMIT,
            "raw_avi_retained": False,
        },
    )
    print(
        json.dumps(
            {
                "prepared": True,
                "episodes": len(rows),
                "appearances": len(appearances),
                "images_expected": len(appearances) * len(VIEWS),
                "manifest_sha256": sha256(manifest),
            },
            sort_keys=True,
        ),
        flush=True,
    )


def load_manifest() -> list[dict[str, Any]]:
    prepared = json.loads(
        (MANIFEST_ROOT / "PREPARED.json").read_text(encoding="utf-8")
    )
    manifest = MANIFEST_ROOT / "manifest.jsonl"
    if sha256(manifest) != prepared["manifest_sha256"]:
        raise RuntimeError("reference capture manifest hash mismatch")
    with manifest.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if len(rows) != 42:
        raise RuntimeError(f"expected 42 capture episodes, got {len(rows)}")
    return rows


def record_path(row: dict[str, Any]) -> Path:
    return OUTPUT_ROOT / "records" / f"{row['episode_id']}.json"


def row_complete(row: dict[str, Any]) -> bool:
    record = record_path(row)
    if not record.is_file():
        return False
    try:
        value = json.loads(record.read_text(encoding="utf-8"))
        images = value["images"]
        if len(images) != len(row["appearance_order"]) * len(VIEWS):
            return False
        return all(
            Path(item["path"]).is_file()
            and sha256(Path(item["path"])) == item["sha256"]
            for item in images
        )
    except (OSError, KeyError, TypeError, ValueError):
        return False


def probe_image(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def extract_images(
    raw_avi: Path,
    stage: Path,
    row: dict[str, Any],
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    samples = row["sample_frames"]
    extracted = stage / "extracted"
    extracted.mkdir()
    selection = "+".join(
        f"eq(n\\,{int(sample['frame_index'])})" for sample in samples
    )
    crop_x = (capture.WIDTH - CROP_SIZE) // 2
    crop_y = CROP_Y
    video_filter = (
        f"select={selection},"
        f"crop={CROP_SIZE}:{CROP_SIZE}:{crop_x}:{crop_y},"
        f"scale={OUTPUT_SIZE}:{OUTPUT_SIZE}:flags=lanczos"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(raw_avi),
            "-vf",
            video_filter,
            "-vsync",
            "0",
            str(extracted / "frame-%03d.png"),
        ],
        check=True,
    )
    frames = sorted(extracted.glob("frame-*.png"))
    if len(frames) != len(samples):
        raise RuntimeError(
            f"extracted frame count mismatch: expected={len(samples)} "
            f"actual={len(frames)}"
        )
    images: list[dict[str, Any]] = []
    if len(row["appearance_order"]) != 1:
        raise RuntimeError(
            f"expected one unique appearance, got {row['appearance_order']}"
        )
    appearance_id = row["appearance_order"][0]
    for source, sample in zip(frames, samples, strict=True):
        actor = next(
            item
            for item in scenario["actors"]
            if item["appearance_id"] == appearance_id
        )
        destination = (
            OUTPUT_ROOT
            / "ref_sets"
            / appearance_id
            / f"{sample['view']}.png"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.partial.{os.getpid()}"
        )
        shutil.copy2(source, temporary)
        if probe_image(temporary) != (OUTPUT_SIZE, OUTPUT_SIZE):
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"invalid extracted image geometry: {temporary}")
        os.replace(temporary, destination)
        images.append(
            {
                "schema_version": REF_SET_SCHEMA,
                "release_id": RELEASE_ID,
                "ref_set_id": actor["ref_set_id"],
                "appearance_id": appearance_id,
                "model": actor["model"],
                "skin": actor["skin"],
                "color": actor["color"],
                "view": sample["view"],
                "yaw_offset_degrees": sample["yaw_offset_degrees"],
                "source_episode_id": row["episode_id"],
                "source_frame_index": sample["frame_index"],
                "source_seconds": sample["seconds"],
                "path": str(destination),
                "sha256": sha256(destination),
                "width": OUTPUT_SIZE,
                "height": OUTPUT_SIZE,
                "first_person_weapon_visible": False,
                "hud_visible": False,
                "raw_avi_retained": False,
            }
        )
    return images


def worker(
    lane_id: int,
    lane_count: int,
    scratch_root: Path,
    port: int,
    episode_indices: list[int],
) -> None:
    rows = load_manifest()
    selected = (
        [rows[index] for index in episode_indices]
        if episode_indices
        else [row for row in rows if row["episode_index"] % lane_count == lane_id]
    )
    scratch_root.mkdir(parents=True, exist_ok=True)
    build = ROOT / BUILD_GLOB
    if not (build / "bin/xonotic-local-sdl").is_file():
        raise RuntimeError(f"locked reference capture build missing: {build}")
    lane: reusable.ReusableStage1Lane | None = None
    failures: list[dict[str, Any]] = []
    completed = 0
    started = time.monotonic()
    try:
        for sequence, row in enumerate(selected, 1):
            if row_complete(row):
                completed += 1
                print(
                    f"ref_episode_skip lane={lane_id} episode={row['episode_id']} "
                    f"progress={sequence}/{len(selected)}",
                    flush=True,
                )
                continue
            scenario_path = ROOT / row["scenario_path"]
            if sha256(scenario_path) != row["scenario_sha256"]:
                raise RuntimeError(f"scenario hash mismatch: {scenario_path}")
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            stage = scratch_root / "episodes" / row["episode_id"]
            if stage.exists():
                shutil.rmtree(stage)
            raw_avi: Path | None = None
            try:
                if lane is None:
                    lane = reusable.ReusableStage1Lane(
                        scratch_root / "resident",
                        build=build,
                        port=port,
                    )
                live = lane.run_live(stage, scenario)
                render = lane.run_render(stage, scenario, live)
                raw_avi = Path(render["raw_avi"])
                if not raw_avi.resolve().is_relative_to(scratch_root.resolve()):
                    raise RuntimeError(f"raw AVI escaped local scratch: {raw_avi}")
                images = extract_images(raw_avi, stage, row, scenario)
                record = {
                    "schema_version": "xonotic-enemy-reference-capture-record-v1",
                    "created_utc": utc_now(),
                    "release_id": RELEASE_ID,
                    "episode_id": row["episode_id"],
                    "episode_index": row["episode_index"],
                    "scenario_path": row["scenario_path"],
                    "scenario_sha256": row["scenario_sha256"],
                    "runtime_build": BUILD_GLOB,
                    "runtime_source_commit": BUILD_COMMIT,
                    "live_wall_seconds": live["live_wall_seconds"],
                    "render_wall_seconds": render["render_wall_seconds"],
                    "offline_accelerate": render["offline_accelerate"],
                    "images": images,
                    "raw_avi_retained": False,
                    "demo_retained": False,
                }
                atomic_json(record_path(row), record)
                completed += 1
                print(
                    f"ref_episode_accepted lane={lane_id} "
                    f"episode={row['episode_id']} images={len(images)} "
                    f"progress={sequence}/{len(selected)}",
                    flush=True,
                )
            except Exception as exc:
                failures.append(
                    {
                        "episode_id": row["episode_id"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                print(
                    f"ref_episode_failed lane={lane_id} episode={row['episode_id']} "
                    f"error={json.dumps(failures[-1]['error'])}",
                    file=sys.stderr,
                    flush=True,
                )
                traceback.print_exc()
                if lane is not None:
                    lane.close()
                    lane = None
            finally:
                if raw_avi is not None:
                    raw_avi.unlink(missing_ok=True)
                if stage.exists():
                    shutil.rmtree(stage)
    finally:
        if lane is not None:
            lane.close()
    summary = {
        "schema_version": "xonotic-enemy-reference-lane-summary-v1",
        "created_utc": utc_now(),
        "lane_id": lane_id,
        "lane_count": lane_count,
        "selected": len(selected),
        "completed": completed,
        "failures": failures,
        "wall_seconds": time.monotonic() - started,
        "raw_avi_retained": False,
    }
    atomic_json(OUTPUT_ROOT / "status" / f"lane-{lane_id:03d}.json", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    if failures:
        raise RuntimeError(f"reference lane {lane_id} had {len(failures)} failures")


def finalize() -> None:
    rows = load_manifest()
    if not all(row_complete(row) for row in rows):
        missing = [row["episode_id"] for row in rows if not row_complete(row)]
        raise RuntimeError(f"reference capture incomplete: {missing}")
    records = [
        json.loads(record_path(row).read_text(encoding="utf-8")) for row in rows
    ]
    images = [image for record in records for image in record["images"]]
    appearances = load_appearances()
    expected = {
        (row["appearance_id"], view)
        for row in appearances
        for view, _ in VIEWS
    }
    actual = {(row["appearance_id"], row["view"]) for row in images}
    duplicate_count = len(images) - len(actual)
    if actual != expected or duplicate_count:
        raise RuntimeError(
            f"reference coverage mismatch: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)} duplicates={duplicate_count}"
        )
    if any(Path(row["path"]).suffix.lower() != ".png" for row in images):
        raise RuntimeError("reference bank contains non-PNG image")
    if any(not Path(row["path"]).is_file() for row in images):
        raise RuntimeError("reference bank has missing image")
    if any(sha256(Path(row["path"])) != row["sha256"] for row in images):
        raise RuntimeError("reference bank image hash mismatch")
    manifest = OUTPUT_ROOT / "reference_manifest.jsonl"
    atomic_jsonl(manifest, sorted(images, key=lambda row: (row["appearance_id"], row["view"])))
    release = {
        "schema_version": "xonotic-enemy-reference-release-v1",
        "created_utc": utc_now(),
        "release_id": RELEASE_ID,
        "reference_ready": True,
        "appearances": len(appearances),
        "views_per_appearance": len(VIEWS),
        "images": len(images),
        "models": sorted({row["model"] for row in images}),
        "skins": sorted({row["skin"] for row in images}),
        "colors": sorted({row["color"] for row in images}),
        "views": [name for name, _ in VIEWS],
        "reference_manifest_path": str(manifest),
        "reference_manifest_sha256": sha256(manifest),
        "appearance_source": str(APPEARANCE_SOURCE),
        "appearance_source_sha256": sha256(APPEARANCE_SOURCE),
        "client_overlay": str(ROOT / "configs/capture_client_ref42_clean.cfg"),
        "client_overlay_sha256": sha256(ROOT / "configs/capture_client_ref42_clean.cfg"),
        "capture_script": str(CAPTURE_SCRIPT),
        "capture_script_sha256": sha256(CAPTURE_SCRIPT),
        "runtime_build": BUILD_GLOB,
        "runtime_source_commit": BUILD_COMMIT,
        "first_person_weapon_visible": False,
        "hud_visible": False,
        "raw_avi_retained": False,
        "target_release_id": "stage2_long60_multi_enemy_ref42_30h_20260828_v5",
    }
    atomic_json(OUTPUT_ROOT / "RELEASE.json", release)
    sums = [
        f"{row['sha256']}  {Path(row['path']).relative_to(OUTPUT_ROOT)}"
        for row in sorted(images, key=lambda value: value["path"])
    ]
    sums.extend(
        [
            f"{sha256(manifest)}  {manifest.relative_to(OUTPUT_ROOT)}",
            f"{sha256(OUTPUT_ROOT / 'RELEASE.json')}  RELEASE.json",
        ]
    )
    (OUTPUT_ROOT / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(json.dumps(release, sort_keys=True), flush=True)


def audit() -> None:
    rows = load_manifest()
    complete = sum(row_complete(row) for row in rows)
    pngs = list((OUTPUT_ROOT / "ref_sets").glob("*/*.png"))
    avis = list(OUTPUT_ROOT.rglob("*.avi")) if OUTPUT_ROOT.exists() else []
    result = {
        "release_id": RELEASE_ID,
        "episodes": len(rows),
        "completed_episodes": complete,
        "png_images": len(pngs),
        "expected_images": 42 * len(VIEWS),
        "raw_avi_count": len(avis),
        "reference_ready": (OUTPUT_ROOT / "RELEASE.json").is_file(),
    }
    print(json.dumps(result, sort_keys=True), flush=True)
    if avis:
        raise RuntimeError("raw AVI found in shared reference release")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("audit")
    sub.add_parser("finalize")
    worker_parser = sub.add_parser("worker")
    worker_parser.add_argument("--lane-id", type=int, required=True)
    worker_parser.add_argument("--lane-count", type=int, required=True)
    worker_parser.add_argument("--scratch-root", type=Path, required=True)
    worker_parser.add_argument("--port", type=int, required=True)
    worker_parser.add_argument("--episode-index", type=int, action="append", default=[])
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "audit":
        audit()
    elif args.command == "finalize":
        finalize()
    elif args.command == "worker":
        if args.lane_count < 1 or not 0 <= args.lane_id < args.lane_count:
            raise ValueError("invalid lane configuration")
        worker(
            args.lane_id,
            args.lane_count,
            args.scratch_root,
            args.port,
            args.episode_index,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
