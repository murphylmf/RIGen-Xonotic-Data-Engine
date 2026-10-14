                      
"""Build and measure isolated 60 s Stage-2 multi-enemy capture pilots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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

sys.path.insert(0, str(ROOT / "scripts"))
import xonotic_capture as capture              
import xonotic_stage1_reusable as reusable              


OUTPUT_SECONDS = 60.0
OUTPUT_FRAMES = 1201
PROMPT_BLOCK_SECONDS = 0.8
PROMPT_BLOCKS = 75
ENEMY_HORIZONTAL_SPEED = 80.0
FIRE_START_OFFSET_TICKS = 4
FIRE_DURATION_TICKS = 56
                                                                             
                                                                       
                                                                           
       
FRUSTUM_TOLERANCE_SCALE = 1.04
HORIZONTAL_HALF_FOV_DEGREES = math.degrees(math.atan(4.0 / 3.0))
EXPANDED_VIEW_HALF_YAW_DEGREES = math.degrees(
    math.atan((4.0 / 3.0) * FRUSTUM_TOLERANCE_SCALE)
)
PLAYER_ORIGIN = (608.4, 1429.2, -104.0)
BASE_ENEMY_ORIGIN = (874.9525038849215, 1472.2088673726576, -104.0)
BASE_ANGLE_DEGREES = math.degrees(
    math.atan2(
        BASE_ENEMY_ORIGIN[1] - PLAYER_ORIGIN[1],
        BASE_ENEMY_ORIGIN[0] - PLAYER_ORIGIN[0],
    )
)

PLAYER_MOTION_BASE_SPEED = 70.0
PLAYER_MOTION_SPEED_MODULATION = 10.0
PLAYER_MOTION_ORBIT_PERIOD_SECONDS = 8.0
PLAYER_MOTION_PHASE_PERIOD_SECONDS = 19.0

                                                                             
                                                                           
                                                                              
                                                                             
                
PLAYER_IDLE_WINDOWS = (
    (2.80, 3.35),
    (6.10, 6.95),
    (9.70, 10.20),
    (12.90, 14.00),
    (17.20, 17.85),
    (20.40, 21.65),
    (24.00, 24.50),
    (27.10, 28.00),
    (31.00, 31.65),
    (34.20, 35.35),
    (38.30, 38.80),
    (41.40, 42.35),
    (45.30, 45.90),
    (48.60, 49.80),
    (53.00, 53.70),
    (56.20, 57.10),
    (59.00, 59.45),
)

                                                                           
                                                                           
                                              
CAMERA_HOLD_WINDOWS = (
    (3.00, 3.25),
    (8.10, 8.30),
    (13.35, 13.75),
    (20.85, 21.25),
    (27.45, 27.75),
    (34.70, 35.05),
    (41.80, 42.15),
    (49.10, 49.50),
    (52.00, 52.25),
    (56.50, 56.85),
)

ENVIRONMENT_TEXT = """[ENVIRONMENT STYLE AND OBJECTS]
A sci-fi space station environment built from textured concrete, glowing digital grid panels, and metallic structural beams. Its minimalist digital-industrial design uses dark grey, deep space blue, and vibrant digital green. Lighting is low-key night lighting with ambient starlight and artificial neon accents, creating an isolated, cold, and technological atmosphere. Common scene structures and materials include a blue line along a barrier top, flat dark ground, a low green-textured barrier, and a multi-level blocky structure.
[ACTIVE WEAPON]
The active weapon is MachineGun. Its appearance is described as: A long narrow rifle with a dark angular receiver, perforated honeycomb barrel shroud, slim top strip, metallic edges, and small colored accents that vary between renders. Its primary fire is fully automatic hitscan gunfire, dealing direct bullet damage without an explosion."""


@dataclass(frozen=True)
class Actor:
    slot: int
    actor_id: str
    model: str
    skin: int
    color: int
    health: float
    armor: float
    description: str


@dataclass(frozen=True)
class Segment:
    start_block: int
    end_block: int
    slot: int
    lateral_start: float
    lateral_end: float
    distance_start: float
    distance_end: float
    motion_text: str
    entry_side: str
    exit_side: str
    returning: bool = False
    jump_block: int | None = None
    fire_blocks: tuple[int, ...] = ()


ACTORS = (
    Actor(
        1,
        "enemy_ignis_red",
        "ignis",
        1,
        68,
        999.0,
        0.0,
        "A tall broad-shouldered human male in vivid red and black matte fitted armor, with an uncovered head, close dark hair, a short beard, and small glowing eyes.",
    ),
    Actor(
        2,
        "enemy_nyx_yellow",
        "nyx",
        1,
        204,
        999.0,
        0.0,
        "A lean armored humanoid with bright yellow and black matte segmented plates, rounded shoulders, long fitted leg panels, and a smooth dark helmet with three pale circular lights.",
    ),
    Actor(
        3,
        "enemy_pyria_white",
        "pyria",
        1,
        0,
        999.0,
        0.0,
        "A slim human woman in white, light-gray, and black matte close-fitting segmented armor, with narrow shoulders, long leg panels, and an uncovered face framed by short dark hair.",
    ),
    Actor(
        4,
        "enemy_umbra_yellow",
        "umbra",
        1,
        204,
        999.0,
        0.0,
        "A slim armored humanoid in bright yellow and black matte panels, with narrow shoulders, a high collar, long clean limb sections, and a ridged dark helmet with two small pale-violet eye lights.",
    ),
)


VARIANTS: dict[str, tuple[Segment, ...]] = {
    "four_distinct": (
        Segment(4, 18, 1, 308.0, -588.0, 220, 220, "moves toward the player's right", "left", "right", fire_blocks=(9,)),
        Segment(23, 37, 2, -447.553, 447.553, 230, 190, "moves toward the player's left while approaching", "right", "left", jump_block=30, fire_blocks=(28,)),
        Segment(42, 57, 3, 464.349, -494.349, 230, 180, "moves toward the player's right while approaching", "left", "right", fire_blocks=(49,)),
        Segment(62, 75, 4, -415.519, 415.519, 190, 230, "moves toward the player's left while moving away", "right", "left", fire_blocks=(67,)),
    ),
    "controlled_return": (
        Segment(2, 13, 1, 287.074, -416.688, 146.714, 128.403, "moves toward the player's right while approaching", "left", "right", fire_blocks=(7,)),
        Segment(14, 30, 2, -506.417, 513.776, 132.979, 221.190, "moves toward the player's left while moving away", "right", "left", jump_block=22, fire_blocks=(18,)),
        Segment(32, 43, 1, -580.000, 123.981, 161.678, 166.817, "moves toward the player's left", "right", "left", returning=True, fire_blocks=(40,)),
        Segment(48, 62, 3, 414.600, -480.000, 180, 230, "moves toward the player's right while moving away", "left", "right", fire_blocks=(57,)),
        Segment(62, 75, 4, -479.803, 347.577, 197.542, 109.989, "moves toward the player's left while approaching", "right", "left", fire_blocks=(68,)),
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def camera_schedule_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(
            line for line in handle if not line.startswith("#")
        )
        for row in reader:
            digest.update(
                (
                    f"{row['tick']},{row['yaw_delta']},"
                    f"{row['pitch_delta']}\n"
                ).encode("ascii")
            )
    return digest.hexdigest()


def player_motion_schedule_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(
            line for line in handle if not line.startswith("#")
        )
        for row in reader:
            digest.update(
                (
                    f"{row['tick']},{row['forward']},"
                    f"{row['strafe']}\n"
                ).encode("ascii")
            )
    return digest.hexdigest()


def longest_false_run(flags: list[bool]) -> int:
    longest = 0
    current = 0
    for flag in flags:
        if flag:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def false_run_lengths(flags: list[bool]) -> list[int]:
    runs: list[int] = []
    current = 0
    for flag in flags:
        if flag:
            if current:
                runs.append(current)
                current = 0
        else:
            current += 1
    if current:
        runs.append(current)
    return runs


def policy_clock(
    output_seconds: float, hold_windows: tuple[tuple[float, float], ...]
) -> float:
    """Return elapsed policy time with deterministic hold windows removed."""
    held_seconds = sum(
        max(0.0, min(output_seconds, end) - start)
        for start, end in hold_windows
        if output_seconds > start
    )
    return output_seconds - held_seconds


def in_policy_hold(
    output_seconds: float, hold_windows: tuple[tuple[float, float], ...]
) -> bool:
    return any(start <= output_seconds < end for start, end in hold_windows)


def shortest_angle_delta(target: float, current: float) -> float:
    return (target - current + 180.0) % 360.0 - 180.0


def segment_for_time(
    segments: tuple[Segment, ...], output_seconds: float
) -> Segment | None:
    block_position = output_seconds / PROMPT_BLOCK_SECONDS
    for segment in segments:
        if segment.start_block <= block_position < segment.end_block:
            return segment
    if output_seconds >= OUTPUT_SECONDS:
        last = segments[-1]
        if last.end_block == PROMPT_BLOCKS:
            return last
    return None


def actor_position(segment: Segment, output_seconds: float) -> tuple[float, float, float, float, float, float]:
    start = segment.start_block * PROMPT_BLOCK_SECONDS
    end = segment.end_block * PROMPT_BLOCK_SECONDS
    progress = min(1.0, max(0.0, (output_seconds - start) / (end - start)))
    lateral = segment.lateral_start + progress * (
        segment.lateral_end - segment.lateral_start
    )
    distance = segment.distance_start + progress * (
        segment.distance_end - segment.distance_start
    )
    angle = math.radians(BASE_ANGLE_DEGREES)
    radial = (math.cos(angle), math.sin(angle))
    left = (-math.sin(angle), math.cos(angle))
    x = PLAYER_ORIGIN[0] + radial[0] * distance + left[0] * lateral
    y = PLAYER_ORIGIN[1] + radial[1] * distance + left[1] * lateral
    z = PLAYER_ORIGIN[2]
    jump_velocity = 0.0
    jump_active = 0.0
    if segment.jump_block is not None:
        jump_start = segment.jump_block * PROMPT_BLOCK_SECONDS + 0.08
        jump_duration = 0.72
        jump_progress = (output_seconds - jump_start) / jump_duration
        if 0.0 <= jump_progress <= 1.0:
            jump_height = 42.0
            z += 4.0 * jump_height * jump_progress * (1.0 - jump_progress)
            jump_velocity = (
                4.0 * jump_height / jump_duration * (1.0 - 2.0 * jump_progress)
            )
            jump_active = 1.0
    duration = end - start
    lateral_velocity = (segment.lateral_end - segment.lateral_start) / duration
    radial_velocity = (segment.distance_end - segment.distance_start) / duration
    vx = radial[0] * radial_velocity + left[0] * lateral_velocity
    vy = radial[1] * radial_velocity + left[1] * lateral_velocity
    return x, y, z, vx, vy, jump_velocity if jump_active else 0.0


def desired_view_yaw(
    segments: tuple[Segment, ...], output_seconds: float
) -> float:
    del segments
                                                                            
                                                                          
                                                                          
    camera_seconds = policy_clock(output_seconds, CAMERA_HOLD_WINDOWS)
    return (
        BASE_ANGLE_DEGREES
        + 6.0 * math.sin(2.0 * math.pi * camera_seconds / 14.5)
        + 2.0 * math.sin(2.0 * math.pi * camera_seconds / 5.2)
    )


def desired_view_pitch(output_seconds: float) -> float:
                                                                            
                                                                           
                         
    camera_seconds = policy_clock(output_seconds, CAMERA_HOLD_WINDOWS)
    return (
        -3.0
        + 1.4 * math.sin(2.0 * math.pi * camera_seconds / 11.0)
        + 0.35 * math.sin(2.0 * math.pi * camera_seconds / 4.3)
    )


def desired_player_motion(output_seconds: float) -> tuple[float, float]:
                                                                           
                                                                              
                                                     
    if in_policy_hold(output_seconds, PLAYER_IDLE_WINDOWS):
        return 0.0, 0.0
    motion_seconds = policy_clock(output_seconds, PLAYER_IDLE_WINDOWS)
    speed = PLAYER_MOTION_BASE_SPEED + PLAYER_MOTION_SPEED_MODULATION * math.sin(
        2.0 * math.pi * motion_seconds / 17.0
    )
    phase = (
        2.0 * math.pi * motion_seconds / PLAYER_MOTION_ORBIT_PERIOD_SECONDS
        + 0.22
        * math.sin(2.0 * math.pi * motion_seconds / PLAYER_MOTION_PHASE_PERIOD_SECONDS)
    )
    return speed * math.cos(phase), speed * math.sin(phase)


def write_actions(
    path: Path, episode_id: str, seed: int, segments: tuple[Segment, ...]
) -> None:
    yaw = BASE_ANGLE_DEGREES
    pitch = -3.0
    fire_ticks: set[int] = set()
    for segment in segments:
        for block in segment.fire_blocks:
            start = capture.WARMUP_TICKS + int(block * PROMPT_BLOCK_SECONDS * 64)
            fire_ticks.update(
                range(
                    start + FIRE_START_OFFSET_TICKS,
                    start + FIRE_START_OFFSET_TICKS + FIRE_DURATION_TICKS,
                )
            )
    rows: list[dict[str, Any]] = []
    for tick in range(capture.TOTAL_TICKS):
        if tick < capture.WARMUP_TICKS:
            desired_yaw = BASE_ANGLE_DEGREES
            desired_pitch = -3.0
            forward = 0.0
            strafe = 0.0
        else:
            output_seconds = (tick - capture.WARMUP_TICKS) / 64.0
            desired_yaw = desired_view_yaw(segments, output_seconds)
            desired_pitch = desired_view_pitch(output_seconds)
            forward, strafe = desired_player_motion(output_seconds)
        yaw_delta = max(-1.35, min(1.35, shortest_angle_delta(desired_yaw, yaw)))
        pitch_delta = max(-0.45, min(0.45, desired_pitch - pitch))
        yaw += yaw_delta
        pitch = max(-89.0, min(89.0, pitch + pitch_delta))
        rows.append(
            {
                "tick": tick,
                "forward": forward,
                "strafe": strafe,
                "yaw_delta": round(yaw_delta, 9),
                "pitch_delta": round(pitch_delta, 9),
                "jump": 0,
                "primary": int(tick in fire_ticks),
                "secondary": 0,
                "weapon_impulse": 0,
                "reload": 0,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"#seed,{seed}\n")
        writer = csv.DictWriter(handle, fieldnames=capture.ACTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_timeline(path: Path, segments: tuple[Segment, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["kind", "tick_or_slot", "actor_or_id", "x_or_model", "y_or_skin", "z_or_color", "vx_or_health", "vy_or_armor", "vz", "yaw", "jump"]
        )
        for actor in ACTORS:
            writer.writerow(
                [
                    "actor",
                    actor.slot,
                    actor.actor_id,
                    actor.model,
                    actor.skin,
                    actor.color,
                    actor.health,
                    actor.armor,
                ]
            )
        for tick in range(capture.TOTAL_TICKS):
            if tick < capture.WARMUP_TICKS:
                writer.writerow(["tick", tick, 0, 0, 0, 0, 0, 0, 0, 0, 0])
                continue
            output_seconds = (tick - capture.WARMUP_TICKS) / 64.0
            segment = segment_for_time(segments, output_seconds)
            if segment is None:
                writer.writerow(["tick", tick, 0, 0, 0, 0, 0, 0, 0, 0, 0])
                continue
            x, y, z, vx, vy, vz = actor_position(segment, output_seconds)
            yaw = math.degrees(
                math.atan2(PLAYER_ORIGIN[1] - y, PLAYER_ORIGIN[0] - x)
            )
            writer.writerow(
                [
                    "tick",
                    tick,
                    segment.slot,
                    f"{x:.9f}",
                    f"{y:.9f}",
                    f"{z:.9f}",
                    f"{vx:.9f}",
                    f"{vy:.9f}",
                    f"{vz:.9f}",
                    f"{yaw:.9f}",
                    int(abs(z - PLAYER_ORIGIN[2]) > 0.01),
                ]
            )


def prompt_schedule(segments: tuple[Segment, ...]) -> list[dict[str, Any]]:
    actor_by_slot = {actor.slot: actor for actor in ACTORS}
    rows: list[dict[str, Any]] = []
    for block in range(PROMPT_BLOCKS):
        segment = next(
            (
                item
                for item in segments
                if item.start_block <= block < item.end_block
            ),
            None,
        )
        if segment is None:
            identity = "No opponent is active during this block."
            motion = "No enemy is visible during this block."
            actor_id = None
            phase = "no_enemy"
        else:
            actor = actor_by_slot[segment.slot]
            actor_id = actor.actor_id
            identity = (
                "The active opponent has this appearance: "
                f"{actor.description}"
            )
            first = block == segment.start_block
            last = block == segment.end_block - 1
            if first:
                qualifier = "The same" if segment.returning else "A new"
                motion = (
                    f"{qualifier} opponent enters from the {segment.entry_side} "
                    f"and {segment.motion_text}."
                )
                phase = "enter"
            elif last:
                motion = (
                    f"The opponent {segment.motion_text} and leaves the view "
                    f"through the {segment.exit_side}."
                )
                phase = "exit"
            else:
                motion = f"The opponent {segment.motion_text}."
                phase = "in_view"
            if segment.jump_block == block:
                motion += " The opponent jumps once while preserving that horizontal motion."
            if block in segment.fire_blocks:
                motion += " The player fires the MachineGun at the opponent during this block."
        text = (
            f"{ENVIRONMENT_TEXT}\n"
            "[ACTIVE OPPONENT IDENTITY]\n"
            f"{identity}\n"
            "[CURRENT OPPONENT MOTION, VISIBILITY, AND INTERACTION]\n"
            f"{motion}"
        )
        rows.append(
            {
                "block_index": block,
                "start_seconds": round(block * PROMPT_BLOCK_SECONDS, 1),
                "end_seconds": round((block + 1) * PROMPT_BLOCK_SECONDS, 1),
                "actor_id": actor_id,
                "visibility_phase": phase,
                "prompt": text,
            }
        )
    return rows


def build_scenario(
    episode_id: str,
    seed: int,
    actions: Path,
    timeline: Path,
    prompts: list[dict[str, Any]],
    segments: tuple[Segment, ...],
) -> dict[str, Any]:
    return {
        "schema_version": "xonotic-stage2-long60-multi-enemy-pilot-v4",
        "episode_id": episode_id,
        "split": "pilot",
        "dataset_role": "stage2_long_horizon_multi_enemy",
        "training_stage": "stage2",
        "training_admitted": False,
        "formal_collection_authorized": False,
        "asset_policy": "official-xonotic-0.8.6-only",
        "map": "geoplanetary",
        "gametype": "ctf",
        "seed": seed,
        "anchor_id": "geoplanetary_long60_multi_pilot",
        "weapon": "MachineGun",
        "weapon_netname": "machinegun",
        "enemy_present": True,
        "enemy_actor_count": len(ACTORS),
        "physical_enemy_entity_count": 1,
        "enemy_model": ACTORS[0].model,
        "enemy_skin": ACTORS[0].skin,
        "enemy_color": ACTORS[0].color,
        "enemy_timeline_path": str(timeline.relative_to(ROOT)),
        "enemy_timeline_sha256": sha256(timeline),
        "enemy_horizontal_speed_units_per_second": ENEMY_HORIZONTAL_SPEED,
        "camera_policy": {
            "name": "independent_scan_with_brief_aim_holds_v3",
            "reads_enemy_state": False,
            "center_yaw_degrees": BASE_ANGLE_DEGREES,
            "yaw_components": [
                {"amplitude_degrees": 6.0, "period_seconds": 14.5},
                {"amplitude_degrees": 2.0, "period_seconds": 5.2},
            ],
            "center_pitch_degrees": -3.0,
            "pitch_components": [
                {"amplitude_degrees": 1.4, "period_seconds": 11.0},
                {"amplitude_degrees": 0.35, "period_seconds": 4.3},
            ],
            "hold_windows_seconds": [list(window) for window in CAMERA_HOLD_WINDOWS],
            "longest_hold_seconds": max(
                end - start for start, end in CAMERA_HOLD_WINDOWS
            ),
        },
        "player_action_policy": {
            "name": "open_loop_bursty_orbit_and_sustained_fire_v4",
            "reads_enemy_state": False,
            "reads_live_player_state": False,
            "movement_duty_cycle_target": 1.0
            - sum(end - start for start, end in PLAYER_IDLE_WINDOWS)
            / OUTPUT_SECONDS,
            "movement_kind": "modulated_orbit_with_irregular_short_pauses",
            "base_speed": PLAYER_MOTION_BASE_SPEED,
            "speed_modulation": PLAYER_MOTION_SPEED_MODULATION,
            "orbit_period_seconds": PLAYER_MOTION_ORBIT_PERIOD_SECONDS,
            "phase_modulation_period_seconds": PLAYER_MOTION_PHASE_PERIOD_SECONDS,
            "idle_windows_seconds": [list(window) for window in PLAYER_IDLE_WINDOWS],
            "idle_window_count": len(PLAYER_IDLE_WINDOWS),
            "longest_idle_seconds": max(
                end - start for start, end in PLAYER_IDLE_WINDOWS
            ),
            "fire_start_offset_ticks": FIRE_START_OFFSET_TICKS,
            "fire_duration_ticks_per_declared_block": FIRE_DURATION_TICKS,
        },
        "encounters": [
            {
                "start_block": segment.start_block,
                "end_block": segment.end_block,
                "actor_id": ACTORS[segment.slot - 1].actor_id,
                "entry_side": segment.entry_side,
                "exit_side": segment.exit_side,
                "returning": segment.returning,
                "fire_blocks": list(segment.fire_blocks),
            }
            for segment in segments
        ],
        "enemy": {
            "origin": list(BASE_ENEMY_ORIGIN),
            "yaw": BASE_ANGLE_DEGREES + 180.0,
            "motion": 5,
            "motion_vector": [
                -math.sin(math.radians(BASE_ANGLE_DEGREES)),
                math.cos(math.radians(BASE_ANGLE_DEGREES)),
                0.0,
            ],
            "motion_distance": 0.0,
            "motion_start_tick": capture.WARMUP_TICKS,
            "health": ACTORS[0].health,
            "armor": ACTORS[0].armor,
        },
        "enemy_policy": {
            "name": "manifest_streamed_multi_actor_timeline_v1",
            "policy_seed": seed + 1000,
            "movement_audio": capture.ENEMY_MOVEMENT_AUDIO_MODE,
            "step_stride_units": 32.0,
            "fires": False,
            "reads_camera": False,
            "reads_live_player_state": False,
        },
        "player": {
            "origin": list(PLAYER_ORIGIN),
            "yaw": BASE_ANGLE_DEGREES,
            "pitch": -3.0,
            "health": 5000.0,
            "armor": 0.0,
            "clip": 60.0,
            "reserve": 600.0,
        },
        "frozen_actions_path": str(actions.relative_to(ROOT)),
        "frozen_actions_sha256": sha256(actions),
        "camera_schedule_sha256": camera_schedule_sha256(actions),
        "player_motion_schedule_sha256": player_motion_schedule_sha256(actions),
        "action_program": "long60_open_loop_bursty_locomotion_camera_and_sustained_fire_v4",
        "prompt_schedule_schema_version": "xonotic-stage2-long60-75x0p8-v1",
        "prompt_schedule": prompts,
        "warmup_ticks": capture.WARMUP_TICKS,
        "output_ticks": capture.OUTPUT_TICKS,
        "video": {"width": 1280, "height": 720, "fps": 64, "frames": capture.OUTPUT_TICKS},
        "actors": [actor.__dict__ for actor in ACTORS],
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def ffprobe(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    return json.loads(completed.stdout)


def encode_video(raw: Path, output: Path) -> float:
    output.parent.mkdir(parents=True, exist_ok=True)
    x264_threads = int(os.environ.get("XONOTIC_LONG60_X264_THREADS", "16"))
    if not 1 <= x264_threads <= 64:
        raise ValueError(
            "XONOTIC_LONG60_X264_THREADS must be in 1..64, "
            f"got {x264_threads}"
        )
    started = time.monotonic()
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-nostdin",
            "-i",
            str(raw),
            "-t",
            "60.05",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-vf",
            "fps=20",
            "-frames:v",
            str(OUTPUT_FRAMES),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-threads",
            str(x264_threads),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-af",
            "atrim=duration=60.05,asetpts=PTS-STARTPTS",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    return time.monotonic() - started


def validate_episode(
    scenario: dict[str, Any],
    stage: Path,
    live: dict[str, Any],
    render: dict[str, Any],
    video: Path,
    encode_wall: float,
) -> dict[str, Any]:
    telemetry = load_jsonl(Path(live["server_telemetry"]))
    states = [row for row in telemetry if row.get("kind") == "state"]
    switches = [row for row in telemetry if row.get("kind") == "actor_switch"]
    events = [row for row in telemetry if row.get("kind") == "event"]
    fatals = [row for row in telemetry if row.get("kind") == "fatal"]
    reset = next((row for row in telemetry if row.get("kind") == "reset"), {})
    player_entity = int(reset.get("player_entity", -1))
    enemy_entity = int(reset.get("enemy_entity", -1))
    state_ticks = [int(row["server_tick"]) for row in states]
    action_rows = sum(
        1
        for line in Path(live["actions_engine"]).read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    )
    with (ROOT / scenario["frozen_actions_path"]).open(
        newline="", encoding="utf-8"
    ) as handle:
        requested_actions = list(
            csv.DictReader(line for line in handle if not line.startswith("#"))
        )
    requested_motion_ticks = sum(
        abs(float(row["forward"])) > 1e-6
        or abs(float(row["strafe"])) > 1e-6
        for row in requested_actions
    )
    requested_output_actions = requested_actions[capture.WARMUP_TICKS :]
    requested_motion_active = [
        math.hypot(float(row["forward"]), float(row["strafe"])) >= 20.0
        for row in requested_output_actions
    ]
    requested_camera_active = [
        abs(float(row["yaw_delta"])) + abs(float(row["pitch_delta"]))
        >= 0.001
        for row in requested_output_actions
    ]
    requested_joint_active = [
        motion or camera
        for motion, camera in zip(
            requested_motion_active, requested_camera_active
        )
    ]
    requested_player_idle_runs = false_run_lengths(requested_motion_active)
    requested_full_idle_runs = false_run_lengths(requested_joint_active)
    requested_primary_ticks = sum(
        int(row["primary"]) != 0 for row in requested_actions
    )
    applied_motion_ticks = sum(
        abs(float(row["applied_action"]["forward"])) > 1e-6
        or abs(float(row["applied_action"]["strafe"])) > 1e-6
        for row in states
    )
    applied_primary_ticks = sum(
        int(row["applied_action"]["primary"]) != 0 for row in states
    )
    player_origins = [row["post"]["origin"] for row in states]
    output_states = states[capture.WARMUP_TICKS :]
    realized_player_motion_active = [
        math.hypot(
            float(row["post"]["velocity"][0]),
            float(row["post"]["velocity"][1]),
        )
        >= 20.0
        for row in output_states
    ]
    realized_camera_active = [
        abs(float(row["applied_action"]["yaw"]) - float(previous["applied_action"]["yaw"]))
        + abs(float(row["applied_action"]["pitch"]) - float(previous["applied_action"]["pitch"]))
        >= 0.001
        for previous, row in zip(output_states, output_states[1:])
    ]
    player_path_length = sum(
        math.hypot(
            current[0] - previous[0], current[1] - previous[1]
        )
        for previous, current in zip(player_origins, player_origins[1:])
    )
    maximum_player_displacement = max(
        (
            math.hypot(
                origin[0] - PLAYER_ORIGIN[0],
                origin[1] - PLAYER_ORIGIN[1],
            )
            for origin in player_origins
        ),
        default=0.0,
    )
    fire_events = [
        row
        for row in events
        if row.get("event") == "fire"
        and int(row.get("actor", -1)) == player_entity
    ]
    impact_events = [
        row
        for row in events
        if row.get("event") == "impact"
        and int(row.get("target", -1)) == enemy_entity
    ]
    damage_events = [
        row
        for row in events
        if row.get("event") == "damage"
        and int(row.get("attacker", -1)) == player_entity
        and int(row.get("target", -1)) == enemy_entity
    ]
    kill_events = [row for row in damage_events if int(row.get("killed", 0))]
    damage_by_encounter: list[dict[str, Any]] = []
    for encounter in scenario["encounters"]:
        start_tick = capture.WARMUP_TICKS + int(
            encounter["start_block"] * PROMPT_BLOCK_SECONDS * 64
        )
        end_tick = capture.WARMUP_TICKS + int(
            encounter["end_block"] * PROMPT_BLOCK_SECONDS * 64
        )
        encounter_damage = [
            row
            for row in damage_events
            if start_tick <= int(row["server_tick"]) < end_tick
        ]
        damage_by_encounter.append(
            {
                "actor_id": encounter["actor_id"],
                "start_block": encounter["start_block"],
                "returning": encounter["returning"],
                "damage_event_count": len(encounter_damage),
                "total_damage": sum(
                    float(row["amount"]) for row in encounter_damage
                ),
            }
        )
    with Path(render["frames_engine"]).open(
        newline="", encoding="utf-8"
    ) as handle:
        frame_records = list(csv.DictReader(handle))
    frame_rows = len(frame_records)
    frame_server_times = [
        float(row["server_time_current"]) for row in frame_records
    ]
    output_begin = next(
        (row for row in telemetry if row.get("kind") == "output_begin"),
        None,
    )
    raw_probe = ffprobe(Path(render["raw_avi"]))
    video_probe = ffprobe(video)
    raw_video_stream = next(
        row for row in raw_probe["streams"] if row.get("codec_type") == "video"
    )
    output_video_stream = next(
        row for row in video_probe["streams"] if row.get("codec_type") == "video"
    )
    raw_frames = int(
        raw_video_stream.get("nb_read_frames") or raw_video_stream.get("nb_frames")
    )
    output_video_frames = int(
        output_video_stream.get("nb_read_frames") or output_video_stream.get("nb_frames")
    )
    active_ids = sorted(
        {
            row["enemy"]["actor_id"]
            for row in states
            if isinstance(row.get("enemy"), dict)
        }
    )
    encounter_crossings: list[dict[str, Any]] = []
    realized_horizontal_speed_errors: list[float] = []
    for encounter in scenario["encounters"]:
        start_seconds = encounter["start_block"] * PROMPT_BLOCK_SECONDS
        end_seconds = encounter["end_block"] * PROMPT_BLOCK_SECONDS
        encounter_states = [
            row
            for row in states
            if isinstance(row.get("enemy"), dict)
            and row["enemy"].get("actor_id") == encounter["actor_id"]
            and start_seconds
            <= (int(row["server_tick"]) - capture.WARMUP_TICKS) / 64.0
            < end_seconds
        ]
        relative_yaws: list[float] = []
        for row in encounter_states:
            player_origin = row["post"]["origin"]
            enemy_origin = row["enemy"]["origin"]
            bearing = math.degrees(
                math.atan2(
                    enemy_origin[1] - player_origin[1],
                    enemy_origin[0] - player_origin[0],
                )
            )
            relative_yaws.append(
                abs(shortest_angle_delta(bearing, row["post"]["angles"][1]))
            )
            velocity = row["enemy"]["velocity"]
            realized_horizontal_speed_errors.append(
                abs(math.hypot(velocity[0], velocity[1]) - ENEMY_HORIZONTAL_SPEED)
            )
        encounter_crossings.append(
            {
                **encounter,
                "state_count": len(encounter_states),
                "start_relative_yaw_degrees": relative_yaws[0]
                if relative_yaws
                else None,
                "minimum_relative_yaw_degrees": min(relative_yaws)
                if relative_yaws
                else None,
                "end_relative_yaw_degrees": relative_yaws[-1]
                if relative_yaws
                else None,
                "crosses_expanded_view": bool(relative_yaws)
                and relative_yaws[0] >= EXPANDED_VIEW_HALF_YAW_DEGREES
                and min(relative_yaws) <= 8.0
                and relative_yaws[-1] >= EXPANDED_VIEW_HALF_YAW_DEGREES,
                "expanded_view_half_yaw_degrees": (
                    EXPANDED_VIEW_HALF_YAW_DEGREES
                ),
                "frustum_tolerance_scale": FRUSTUM_TOLERANCE_SCALE,
            }
        )
    commanded_horizontal_speed_errors: list[float] = []
    timeline_path = ROOT / scenario["enemy_timeline_path"]
    with timeline_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["kind"] != "tick" or int(row["actor_or_id"]) == 0:
                continue
            commanded_horizontal_speed_errors.append(
                abs(
                    math.hypot(
                        float(row["vx_or_health"]),
                        float(row["vy_or_armor"]),
                    )
                    - ENEMY_HORIZONTAL_SPEED
                )
            )
    render_server_time_span = (
        frame_server_times[-1] - frame_server_times[0]
        if frame_server_times
        else 0.0
    )
    render_tail_server_time_span = (
        frame_server_times[-1] - frame_server_times[-64]
        if len(frame_server_times) >= 64
        else 0.0
    )
    checks = {
        "no_fatal_telemetry": not fatals,
        "state_count": len(states) == capture.TOTAL_TICKS,
        "state_ticks_contiguous": state_ticks == list(range(capture.TOTAL_TICKS)),
        "engine_action_count": action_rows == capture.TOTAL_TICKS,
        "raw_frame_log_count": frame_rows == capture.OUTPUT_TICKS,
        "raw_video_frame_count": raw_frames == capture.OUTPUT_TICKS,
        "training_video_frame_count": output_video_frames == OUTPUT_FRAMES,
        "all_four_actor_identities_realized": active_ids
        == sorted(actor.actor_id for actor in ACTORS),
        "actor_switches_realized": len(switches) >= 7,
        "prompt_block_count": len(scenario["prompt_schedule"]) == PROMPT_BLOCKS,
        "hardware_renderer": bool(render.get("renderer")),
        "live_time_scale_two": int(live.get("live_time_scale", 0)) == 2,
        "offline_acceleration": render.get("offline_accelerate") is True,
        "effective_demo_timescale_one": abs(
            float(render.get("effective_demo_timescale", 0.0)) - 1.0
        )
        < 1e-9,
        "camera_motion_decoupled_from_enemy": scenario["camera_policy"][
            "reads_enemy_state"
        ]
        is False
        and camera_schedule_sha256(
            ROOT / scenario["frozen_actions_path"]
        )
        == scenario["camera_schedule_sha256"],
        "player_action_schedule_decoupled_from_enemy_state": scenario[
            "player_action_policy"
        ]["reads_enemy_state"]
        is False
        and scenario["player_action_policy"]["reads_live_player_state"]
        is False
        and player_motion_schedule_sha256(
            ROOT / scenario["frozen_actions_path"]
        )
        == scenario["player_motion_schedule_sha256"],
        "requested_player_locomotion_duty_in_humanlike_band": int(
            capture.OUTPUT_TICKS * 0.70
        )
        <= sum(requested_motion_active)
        <= int(capture.OUTPUT_TICKS * 0.85),
        "requested_short_idle_is_distributed": len(requested_player_idle_runs)
        >= 12
        and max(requested_player_idle_runs, default=0) <= int(1.35 * 64)
        and max(requested_player_idle_runs, default=0) >= int(0.40 * 64),
        "applied_player_locomotion": applied_motion_ticks
        == requested_motion_ticks,
        "visible_player_displacement": maximum_player_displacement >= 40.0
        and player_path_length >= 2200.0,
        "player_remains_in_local_encounter_area": maximum_player_displacement
        <= 500.0,
        "requested_camera_motion_duty": int(capture.OUTPUT_TICKS * 0.88)
        <= sum(requested_camera_active)
        <= int(capture.OUTPUT_TICKS * 0.98),
        "realized_player_motion_duty": sum(realized_player_motion_active)
        >= int(capture.OUTPUT_TICKS * 0.70)
        and sum(realized_player_motion_active)
        <= int(capture.OUTPUT_TICKS * 0.92),
        "realized_camera_motion_duty": sum(realized_camera_active)
        >= int((capture.OUTPUT_TICKS - 1) * 0.88)
        and sum(realized_camera_active)
        <= int((capture.OUTPUT_TICKS - 1) * 0.98),
        "no_long_requested_full_idle": longest_false_run(
            requested_joint_active
        )
        <= int(0.50 * 64),
        "no_long_realized_player_idle": longest_false_run(
            realized_player_motion_active
        )
        <= int(1.50 * 64),
        "requested_sustained_fire": requested_primary_ticks
        >= len(scenario["encounters"]) * FIRE_DURATION_TICKS,
        "applied_sustained_fire": applied_primary_ticks
        == requested_primary_ticks,
        "multiple_machinegun_shots_per_encounter": len(fire_events)
        >= len(scenario["encounters"]) * 5,
        "enemy_damaged_in_every_declared_fire_encounter": bool(
            damage_by_encounter
        )
        and all(row["damage_event_count"] >= 1 for row in damage_by_encounter),
        "enemy_not_killed": not kill_events,
        "every_encounter_crosses_expanded_view": bool(encounter_crossings)
        and all(row["crosses_expanded_view"] for row in encounter_crossings),
        "fixed_enemy_commanded_horizontal_speed": bool(
            commanded_horizontal_speed_errors
        )
        and max(commanded_horizontal_speed_errors) <= 0.01,
        "one_physical_enemy_entity": scenario[
            "physical_enemy_entity_count"
        ]
        == 1,
        "render_server_time_span_complete": render_server_time_span
        >= OUTPUT_SECONDS,
        "render_output_starts_at_authoritative_boundary": bool(
            frame_server_times and output_begin
        )
        and abs(
            frame_server_times[0] - float(output_begin["server_time"])
        )
        <= 0.1,
        "render_tail_not_frozen": render_tail_server_time_span >= 0.9,
    }
    return {
        "schema_version": "xonotic-stage2-long60-multi-enemy-pilot-qa-v4",
        "episode_id": scenario["episode_id"],
        "passed": all(checks.values()),
        "checks": checks,
        "counts": {
            "server_states": len(states),
            "engine_actions": action_rows,
            "raw_frame_log": frame_rows,
            "raw_video_frames": raw_frames,
            "training_video_frames": output_video_frames,
            "actor_switches": len(switches),
            "active_actor_ids": active_ids,
            "fatal_rows": len(fatals),
            "requested_player_motion_ticks": requested_motion_ticks,
            "applied_player_motion_ticks": applied_motion_ticks,
            "requested_primary_ticks": requested_primary_ticks,
            "applied_primary_ticks": applied_primary_ticks,
            "machinegun_fire_events": len(fire_events),
            "enemy_impact_events": len(impact_events),
            "enemy_damage_events": len(damage_events),
            "enemy_kill_events": len(kill_events),
        },
        "player_motion": {
            "horizontal_path_length_units": player_path_length,
            "maximum_displacement_from_anchor_units": maximum_player_displacement,
            "requested_motion_duty_fraction": sum(requested_motion_active)
            / len(requested_motion_active),
            "requested_camera_motion_duty_fraction": sum(
                requested_camera_active
            )
            / len(requested_camera_active),
            "realized_player_motion_duty_fraction": sum(
                realized_player_motion_active
            )
            / len(realized_player_motion_active),
            "realized_camera_motion_duty_fraction": sum(
                realized_camera_active
            )
            / len(realized_camera_active),
            "longest_requested_full_idle_seconds": longest_false_run(
                requested_joint_active
            )
            / 64.0,
            "longest_requested_player_idle_seconds": longest_false_run(
                requested_motion_active
            )
            / 64.0,
            "requested_player_idle_run_count": len(requested_player_idle_runs),
            "requested_full_idle_run_count": len(requested_full_idle_runs),
            "longest_realized_player_idle_seconds": longest_false_run(
                realized_player_motion_active
            )
            / 64.0,
        },
        "interaction": {
            "damage_by_encounter": damage_by_encounter,
            "total_enemy_damage": sum(
                float(row["amount"]) for row in damage_events
            ),
        },
        "timing": {
            "live_wall_seconds": float(live["live_wall_seconds"]),
            "render_wall_seconds": float(render["render_wall_seconds"]),
            "render_recycle_wall_seconds": float(
                render.get("render_process_recycle_wall_seconds", 0.0)
            ),
            "encode_wall_seconds": encode_wall,
            "end_to_end_wall_seconds": float(live["live_wall_seconds"])
            + float(render["render_wall_seconds"])
            + float(render.get("render_process_recycle_wall_seconds", 0.0))
            + encode_wall,
        },
        "renderer": render.get("renderer"),
        "encounter_crossings": encounter_crossings,
        "maximum_commanded_horizontal_speed_error": max(
            commanded_horizontal_speed_errors
        )
        if commanded_horizontal_speed_errors
        else None,
        "maximum_realized_horizontal_speed_error_after_interactions": max(
            realized_horizontal_speed_errors
        )
        if realized_horizontal_speed_errors
        else None,
        "render_server_time_span_seconds": render_server_time_span,
        "render_tail_server_time_span_seconds": render_tail_server_time_span,
        "video": {
            "path": str(video),
            "sha256": sha256(video),
            "size_bytes": video.stat().st_size,
            "duration_seconds": float(video_probe["format"]["duration"]),
            "width": int(output_video_stream["width"]),
            "height": int(output_video_stream["height"]),
            "fps": output_video_stream["r_frame_rate"],
        },
    }


def write_review(output_root: Path, results: list[dict[str, Any]]) -> Path:
    cards: list[str] = []
    for result in results:
        scenario = result["scenario"]
        qa = result["qa"]
        video_name = Path(qa["video"]["path"]).name
        video_url = f"{video_name}?sha={qa['video']['sha256'][:12]}"
        prompt_rows = "".join(
            "<tr>"
            f"<td>{row['block_index']:02d}</td>"
            f"<td>{row['start_seconds']:.1f}-{row['end_seconds']:.1f}s</td>"
            f"<td>{html.escape(str(row['actor_id'] or 'none'))}</td>"
            f"<td>{html.escape(row['visibility_phase'])}</td>"
            f"<td>{html.escape(row['prompt'].split('[CURRENT OPPONENT MOTION, VISIBILITY, AND INTERACTION]\n', 1)[1])}</td>"
            "</tr>"
            for row in scenario["prompt_schedule"]
        )
        timing = qa["timing"]
        motion = qa["player_motion"]
        interaction = qa["interaction"]
        cards.append(
            f"""
            <section class="card">
              <h2>{html.escape(scenario['episode_id'])}</h2>
              <video controls preload="metadata" src="{html.escape(video_url)}"></video>
              <p class="metrics">QA: <b>{'PASS' if qa['passed'] else 'FAIL'}</b> · movement duty {motion['realized_player_motion_duty_fraction']:.1%} / camera duty {motion['realized_camera_motion_duty_fraction']:.1%} / {motion['requested_player_idle_run_count']} short movement pauses / longest requested {motion['longest_requested_player_idle_seconds']:.2f}s / realized {motion['longest_realized_player_idle_seconds']:.2f}s · player path {motion['horizontal_path_length_units']:.0f}u / max displacement {motion['maximum_displacement_from_anchor_units']:.0f}u · {qa['counts']['machinegun_fire_events']} shots / {qa['counts']['enemy_damage_events']} hits / {interaction['total_enemy_damage']:.0f} damage · {qa['counts']['actor_switches']} actor switches · total capture {timing['end_to_end_wall_seconds']:.1f}s</p>
              <details><summary>75 × 0.8s prompt timeline</summary>
                <table><thead><tr><th>#</th><th>time</th><th>actor</th><th>phase</th><th>instruction</th></tr></thead><tbody>{prompt_rows}</tbody></table>
              </details>
            </section>
            """
        )
    document = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 60s multi-enemy pilot</title>
<style>
body{{margin:0;background:#0a0d12;color:#e8edf5;font:15px/1.45 system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:24px}}h1{{font-size:26px}}.card{{background:#121822;border:1px solid #263244;border-radius:14px;padding:18px;margin:18px 0}}video{{display:block;width:100%;max-height:70vh;background:#000;border-radius:8px}}.metrics{{color:#b9c7da}}details{{margin-top:14px}}table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}}th,td{{border-bottom:1px solid #263244;padding:7px;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#121822}}
</style></head><body><main><h1>Stage-2 · 60s controlled multi-enemy interaction pilot</h1><p>The player uses open-loop, human-like movement bursts with distributed short pauses, while the camera keeps scanning with occasional brief aim holds. MachineGun interactions remain verified. Four persistent logical opponent identities reuse one physical bot entity, with at most one active at each tick. 1201 training frames at 20fps; prompt schedule is 75 causal blocks of 0.8s.</p>{''.join(cards)}</main></body></html>"""
    page = output_root / "index.html"
    page.write_text(document, encoding="utf-8")
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=2, choices=(1, 2))
    parser.add_argument(
        "--variant", choices=("all", *VARIANTS), default="all"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "outputs" / "long60_multi_pilot_20260823_v1",
    )
    parser.add_argument(
        "--scratch-root", type=Path, default=Path("./tmp/xonotic-long60-multi-pilot-v1")
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / "manifests" / "long60_multi_pilot_20260823_v1",
    )
    parser.add_argument("--port", type=int, default=29871)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise ValueError(f"port out of range: {args.port}")
    args.output_root = args.output_root.resolve()
    args.scratch_root = args.scratch_root.resolve()
    args.artifact_root = args.artifact_root.resolve()
    if args.output_root.exists():
        raise RuntimeError(f"output root already exists: {args.output_root}")
    if args.scratch_root.exists():
        raise RuntimeError(f"scratch root already exists: {args.scratch_root}")
    args.output_root.mkdir(parents=True)
    args.scratch_root.mkdir(parents=True)
    artifact_root = args.artifact_root
    if artifact_root.exists():
        raise RuntimeError(f"artifact root already exists: {artifact_root}")
    artifact_root.mkdir(parents=True)
    build = capture.build_root()
    variant_names = (
        list(VARIANTS)[: args.episodes]
        if args.variant == "all"
        else [args.variant]
    )
    prepared: list[tuple[str, dict[str, Any]]] = []
    for variant_name in variant_names:
        ordinal = list(VARIANTS).index(variant_name)
        episode_id = f"s2long60_{variant_name}_p{ordinal:02d}"
        episode_artifacts = artifact_root / episode_id
        actions = episode_artifacts / "actions.csv"
        timeline = episode_artifacts / "enemy_timeline.csv"
        segments = VARIANTS[variant_name]
        seed = 26082301 + ordinal
        write_actions(actions, episode_id, seed, segments)
        write_timeline(timeline, segments)
        prompts = prompt_schedule(segments)
        scenario = build_scenario(
            episode_id, seed, actions, timeline, prompts, segments
        )
        scenario_path = episode_artifacts / "scenario.json"
        scenario_path.write_text(
            json.dumps(scenario, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        prepared.append((variant_name, scenario))
    results: list[dict[str, Any]] = []
    lane_root = args.scratch_root / "lane"
    with reusable.ReusableStage1Lane(
        lane_root, build=build, port=args.port
    ) as lane:
        for variant_name, scenario in prepared:
            stage = args.scratch_root / "episodes" / scenario["episode_id"]
            live = lane.run_live(stage, scenario)
            render = lane.run_render(stage, scenario, live)
            video = args.output_root / f"{scenario['episode_id']}.mp4"
            encode_wall = encode_video(Path(render["raw_avi"]), video)
            qa = validate_episode(
                scenario, stage, live, render, video, encode_wall
            )
            qa_path = args.output_root / f"{scenario['episode_id']}.qa.json"
            qa_path.write_text(
                json.dumps(qa, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            Path(render["raw_avi"]).unlink(missing_ok=True)
                                                                           
                                                                         
                                                                      
                                                                          
                                     
            if qa["passed"]:
                Path(live["demo_path"]).unlink(missing_ok=True)
                Path(live["staged_demo_path"]).unlink(missing_ok=True)
            result = {
                "variant": variant_name,
                "scenario": scenario,
                "qa": qa,
            }
            results.append(result)
            print(
                json.dumps(
                    {
                        "episode_id": scenario["episode_id"],
                        "passed": qa["passed"],
                        "timing": qa["timing"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            if not qa["passed"]:
                raise RuntimeError(f"QA failed: {qa_path}")
    steady = results[-1]["qa"]["timing"]["end_to_end_wall_seconds"]
    serial_hours = 1800 * steady / 3600.0
    camera_hashes = sorted(
        {row["scenario"]["camera_schedule_sha256"] for row in results}
    )
    player_motion_hashes = sorted(
        {
            row["scenario"]["player_motion_schedule_sha256"]
            for row in results
        }
    )
    cross_episode_checks = {
        "camera_schedule_identical_across_enemy_variants": len(camera_hashes)
        == 1,
        "player_motion_schedule_identical_across_enemy_variants": len(
            player_motion_hashes
        )
        == 1,
    }
    summary = {
        "schema_version": "xonotic-stage2-long60-multi-enemy-pilot-summary-v4",
        "created_utc": utc_now(),
        "passed": all(row["qa"]["passed"] for row in results)
        and all(cross_episode_checks.values()),
        "runtime_build": str(build),
        "runtime_source_commit": (build / "SOURCE_COMMIT").read_text().strip(),
        "episodes": [
            {
                "episode_id": row["scenario"]["episode_id"],
                "variant": row["variant"],
                "camera_schedule_sha256": row["scenario"][
                    "camera_schedule_sha256"
                ],
                "player_motion_schedule_sha256": row["scenario"][
                    "player_motion_schedule_sha256"
                ],
                "qa": row["qa"],
            }
            for row in results
        ],
        "cross_episode_checks": cross_episode_checks,
        "throughput": {
            "steady_state_episode_wall_seconds_single_lane": steady,
            "accepted_video_hours_per_wall_hour_single_lane": 3600.0 / steady / 60.0,
            "estimated_single_lane_wall_hours_for_30h": serial_hours,
            "target_episodes": 1800,
            "target_video_hours": 30.0,
            "eta_formula": "1800 * steady_state_episode_wall_seconds / lanes / 3600",
        },
        "storage_policy": {
            "raw_avi_retained": False,
            "demo_retained": False,
            "final_mp4_and_qa_retained": True,
        },
        "existing_stage1_stage2_pipelines_modified": False,
    }
    summary_path = args.output_root / "SUMMARY.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    page = write_review(args.output_root, results)
    print(
        json.dumps(
            {
                "summary": str(summary_path),
                "review": str(page),
                "throughput": summary["throughput"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
