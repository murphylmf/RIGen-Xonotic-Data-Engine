                      
"""Deterministic Xonotic 0.8.6 Pilot capture orchestrator.

The only supported output split is ``pilot``.  This program deliberately has
no production-batch command.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import fcntl
import hashlib
import json
import math
import os
import platform
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import Any, Callable, Iterable

import jsonschema
import numpy as np
import pandas as pd


ROOT = Path(
    os.environ.get(
        "XONOTIC_CAPTURE_ROOT",
        str(Path(__file__).resolve().parents[1]),
    )
)
TMP_ROOT = Path(os.environ.get("XONOTIC_CAPTURE_TMP", "./tmp/xonotic_capture"))
BASEDIR = ROOT / "assets/release-0.8.6/Xonotic"
ASSET_ALLOWLIST = ROOT / "assets/OFFICIAL_ASSET_ALLOWLIST.json"
ANCHOR_CATALOG_PATH = ROOT / "configs/OFFICIAL_MAP_ANCHORS.json"
CONDA_PREFIX_REQUIRED = Path(
    os.environ.get(
        "XONOTIC_CONDA_PREFIX_REQUIRED",
        str(ROOT.parent / "miniconda3/envs/xonotic-capture"),
    )
)
TICK_HZ = 64
WARMUP_TICKS = 64
OUTPUT_TICKS = 320
TOTAL_TICKS = WARMUP_TICKS + OUTPUT_TICKS
VIDEO_FPS = 64
AUDIO_RATE = 48_000
AUDIO_SAMPLES = 240_000
SAMPLES_PER_FRAME = 750
WIDTH = 1280
HEIGHT = 720
SERVER_MAX_PHYSICS_FRAMES_PER_HOST_FRAME = 1
RENDER_DEMO_PREROLL_FIXEDSTEP = 1
MODEL_ACTION_SCHEMA_VERSION = "ltx2-crossfps-xonotic-v1"
MODEL_ACTION_JOYSTICK_CHANNELS = (
    "j_left_x",
    "j_left_y",
    "j_right_x",
    "j_right_y",
)
MODEL_ACTION_CANONICAL_BUTTONS = (
    "A",
    "B",
    "X",
    "Y",
    "LB",
    "RB",
    "LT",
    "RT",
)
MODEL_ACTION_BUTTON_COLUMNS = (
    "south",
    "east",
    "west",
    "north",
    "left_shoulder",
    "right_shoulder",
    "left_trigger",
    "right_trigger",
)
MODEL_ACTION_BUTTON_MEANINGS = {
    "A": {
        "meaning": "jump",
        "aliases": ["jump"],
    },
    "B": {
        "meaning": "",
        "aliases": [],
    },
    "X": {
        "meaning": "reload",
        "aliases": ["reload the held weapon"],
    },
    "Y": {
        "meaning": "",
        "aliases": [],
    },
    "LB": {
        "meaning": "",
        "aliases": [],
    },
    "RB": {
        "meaning": "",
        "aliases": [],
    },
    "LT": {
        "meaning": "secondary fire",
        "aliases": ["alternate weapon action"],
    },
    "RT": {
        "meaning": "primary fire",
        "aliases": ["fire the held weapon"],
    },
}
                                                                     
                                                                              
                                                                           
                                                                           
                                                   
MODEL_ACTION_MOVEMENT_USERCMD_SCALE = 400.0
MODEL_ACTION_VIEW_DEGREES_PER_TICK = 12.0
MODEL_ACTION_SOURCE_TOLERANCE = 1e-3
CAMERA_BASE_FOV_4X3_DEG = 90.0
CAMERA_FRUSTUM_X = 4.0 / 3.0
CAMERA_FRUSTUM_Y = 3.0 / 4.0
CAMERA_FRUSTUM_TOLERANCE = 1e-5
FIRST_PERSON_MAX_HORIZONTAL_OFFSET = 32.0
FIRST_PERSON_MAX_TOTAL_OFFSET = 80.0
                                                                            
                                                                          
                                                          
BLOCKED_COMMAND_MIN_SPEED = 32.0
BLOCKED_PROGRESS_MIN_SPEED = 8.0
BLOCKED_PROGRESS_MIN_RATIO = 0.20
BLOCKED_MIN_CONSECUTIVE_TICKS = 16
BLOCKED_FORWARD_CONE_HALF_ANGLE_DEG = 45.0
BLOCKED_OFF_FORWARD_MIN_FRACTION = 0.5
VISIBLE_COLLISION_INTENT = "visible_wall_contact"
VISIBLE_COLLISION_MIN_CONTACT_FRACTION = 0.5
VISIBLE_COLLISION_MIN_VISIBLE_FRACTION = 0.5
VISIBLE_COLLISION_MIN_VISIBLE_TICKS = 8
VISIBLE_COLLISION_MIN_RECOVERY_TICKS = 16
VISIBLE_COLLISION_MAX_ABS_NDC_X = 0.85
VISIBLE_COLLISION_MAX_ABS_NDC_Y = 0.80
VISIBLE_COLLISION_MAX_ABS_SURFACE_NORMAL_Z = 0.50
TMP_MIN_FREE_BYTES = 2 * 1024**3
FRAME_STATE_TIME_TOLERANCE_SECONDS = 0.0001
FIXED_DEMO_PRESENTATION_TOLERANCE_SECONDS = 0.000001
FIXED_DEMO_INTERPOLATION_TOLERANCE = 0.000001
TIERED_REVIEW_POLICY = "tiered_review_v1"
PLAYER_PATH_CERTIFICATE_SCHEMA = (
    "xonotic-stage1-v5-player-path-certificate-v1"
)
PLAYER_PATH_REFERENCE_SCHEMA = (
    "xonotic-stage1-v5-player-path-reference-v1"
)
PLAYER_PATH_RUNTIME_COMPATIBILITY_SCHEMA = (
    "xonotic-stage1-v5-player-path-runtime-compatibility-v1"
)
PLAYER_PATH_RUNTIME_COMPATIBILITY_REFERENCE_SCHEMA = (
    "xonotic-stage1-v5-player-path-runtime-compatibility-reference-v1"
)
_PLAYER_PATH_RUNTIME_COMPATIBILITY_CACHE: dict[
    tuple[str, str, str, str], dict[str, Any]
] = {}
_PLAYER_PATH_RUNTIME_COMPATIBILITY_CACHE_LOCK = Lock()
PLAYER_PATH_ORIGIN_TOLERANCE = 0.01
PLAYER_PATH_VELOCITY_TOLERANCE = 0.01
PLAYER_PATH_ANGLE_TOLERANCE = 0.01
ENEMY_MOVEMENT_AUDIO_MODE = "native_surface_footsteps_v1"
ENEMY_STEP_STRIDE_UNITS = 32.0
ENEMY_AUDIO_TRANSPORT_TICKS = 1
                                                                    
                                                                           
                                                                             
                                                                     
                            
STAGE1_AUDIO_EXPECTATION_POLICY_SCHEMA = (
    "xonotic-stage1-audio-expectation-v2"
)
STAGE1_PLAYER_MAXSPEED = 360.0
STAGE1_PLAYER_FOOTSTEP_SPEED_FRACTION = 0.60
STAGE1_PLAYER_FOOTSTEP_SPEED_THRESHOLD = (
    STAGE1_PLAYER_MAXSPEED
    * STAGE1_PLAYER_FOOTSTEP_SPEED_FRACTION
)
ENEMY_PATH_TRACE_FRACTION_MIN = 0.999999
ENEMY_PATH_GROUND_NORMAL_Z_MIN = 0.7
ENEMY_PATH_GROUND_DISTANCE_MAX = 48.0
SOFTWARE_RENDERER_RE = re.compile(
    r"(?:llvmpipe|softpipe|swrast|software rasterizer)",
    re.IGNORECASE,
)
NONTRAINING_SPLITS = {
    "pilot",
    "preflight",
    "v2_coverage_pilot",
    "v2_motion_distance_pilot",
    "v2_stage1_review_fov90",
    "v2_stage1_production_preflight",
    "v2_stage1_enemy_policy_preflight",
    "v2_stage1_enemy_policy_preflight_v2",
    "v2_stage1_enemy_policy_visual_preflight",
    "v2_stage1_enemy_policy_audio_preflight",
    "v2_stage1_enemy_policy_audio_preflight_v2",
    "v2_stage1_enemy_path_trace_regression",
    "v2_stage1_route_calibration",
    "v2_stage1_route_regression",
    "v2_stage1_manifest_random_review",
    "v3_stage1_manifest_random_review",
    "v4_stage1_manifest_random_review",
    "v4_stage1_reload_validation",
    "stage2_causal_preflight",
    "stage2_humanized_nontraining_review",
    "stage2_stochastic_nontraining_review",
    "stage2_prefrozen_player_motion_nontraining_review_candidates",
    "stage2_prefrozen_player_motion_replenishment_nontraining_review_candidates",
    "stage2_weapon_balanced_nontraining_review",
    "h200_pipeline_canary",
    "h200_pipeline_benchmark",
}
FORMAL_STAGE1_SPLITS = {
    "foundation_no_enemy",
    "foundation_enemy_distractor",
}
_ENCODE_SEMAPHORE_LOCK = Lock()
_ENCODE_SEMAPHORE_LIMIT: int | None = None
_ENCODE_SEMAPHORE: BoundedSemaphore | None = None
_LIVE_SEMAPHORE_LOCK = Lock()
_LIVE_SEMAPHORE_LIMIT: int | None = None
_LIVE_SEMAPHORE: BoundedSemaphore | None = None
_RENDER_SEMAPHORE_LOCK = Lock()
_RENDER_SEMAPHORE_LIMIT: int | None = None
_RENDER_SEMAPHORE: BoundedSemaphore | None = None
_SDL_SEMAPHORE_LOCK = Lock()
_SDL_SEMAPHORE_LIMIT: int | None = None
_SDL_SEMAPHORE: BoundedSemaphore | None = None

FORBIDDEN_AUDIO_PATTERNS = (
    "announcer/",
    "cdtracks/",
    "music/",
    "misc/itemrespawncountdown.wav",
    "misc/talk",
)

TARGET_COUNTS = {
    "atomic_dynamics": 20,
    "mixed_dynamics": 20,
    "combat_outcome": 30,
    "mobile_fire": 20,
    "machinegun_reload": 10,
}

WEAPON_NETNAME = {
    "Blaster": "blaster",
    "Shotgun": "shotgun",
    "MachineGun": "machinegun",
    "Mortar": "mortar",
    "Electro": "electro",
    "Crylink": "crylink",
    "Vortex": "vortex",
    "Hagar": "hagar",
    "Devastator": "devastator",
}

ACTION_COLUMNS = [
    "tick",
    "forward",
    "strafe",
    "yaw_delta",
    "pitch_delta",
    "jump",
    "primary",
    "secondary",
    "weapon_impulse",
    "reload",
]


class CaptureFailure(RuntimeError):
    """An attempt failed a closed capture or QA gate."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


MAP_MODE_FALLBACK_RE = re.compile(
    r"can't play the selected map in the given game mode "
    r"\(([^)]+)\)\. Falling back to a supported mode \(([^)]+)\)\."
)
HUD_POLICY_LINE = (
    "capture: hud policy cl_damagetext=0 "
    "crosshair_hitindication=0 hud_healtharmor=0 hud_ammo=0 "
    "cl_hidewaypoints=2 hud_modicons=0"
)
GAMETYPE_CVARS = {
    "as": "g_assault",
    "ca": "g_ca",
    "ctf": "g_ctf",
    "cts": "g_cts",
    "dm": "g_dm",
    "dom": "g_domination",
    "duel": "g_duel",
    "ft": "g_freezetag",
    "inv": "g_invasion",
    "ka": "g_keepaway",
    "kh": "g_keyhunt",
    "lms": "g_lms",
    "mayhem": "g_mayhem",
    "nb": "g_nexball",
    "ons": "g_onslaught",
    "rc": "g_race",
    "surv": "g_survival",
    "tdm": "g_tdm",
    "tka": "g_tka",
    "tmayhem": "g_tmayhem",
}


def logged_cvar_value(console: str, name: str) -> str | None:
    matches = re.findall(
        rf'"{re.escape(name)}" is "([^"]*)"',
        console,
    )
    return matches[-1] if matches else None


def validate_realized_gametype(
    console: str,
    expected: str,
    log_path: Path | str,
) -> str:
    fallbacks = MAP_MODE_FALLBACK_RE.findall(console)
    if fallbacks:
        raise CaptureFailure(
            "gametype_fallback_forbidden",
            canonical_json(
                {
                    "expected": expected,
                    "fallbacks": [
                        {"requested": source, "realized": destination}
                        for source, destination in fallbacks
                    ],
                    "log": str(log_path),
                }
            ),
        )
    realized = logged_cvar_value(console, "gamecfg")
    if realized is None:
        raise CaptureFailure(
            "realized_gametype_unverified", str(log_path)
        )
    if realized.lower() != expected.lower():
        raise CaptureFailure(
            "realized_gametype_mismatch",
            f"expected={expected} realized={realized} log={log_path}",
        )
    return realized.lower()


def uses_tiered_review_policy(scenario: dict[str, Any]) -> bool:
    """Return whether semantic drift is reviewable instead of destructive.

    This is deliberately opt-in. Existing Pilot and strict calibration
    scenarios retain their original fail-closed behavior.
    """
    return scenario.get("acceptance_policy") == TIERED_REVIEW_POLICY


def output_split_authorized(scenario: dict[str, Any]) -> bool:
    if scenario.get("split") in NONTRAINING_SPLITS:
        return scenario.get("formal_collection_authorized") is not True
    split = str(scenario.get("split", ""))
    return (
        split in FORMAL_STAGE1_SPLITS
        and scenario.get("dataset_role") == split
        and scenario.get("training_stage") == "stage1"
        and scenario.get("formal_collection_authorized") is True
        and bool(scenario.get("formal_authorization_basis"))
        and scenario.get("training_admitted") is False
        and scenario.get("source_commit_required")
        == (
            build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip()
    )


def stage1_role_eligible(
    scenario: dict[str, Any],
    qa: dict[str, Any],
    relation: dict[str, Any],
    motion: dict[str, Any],
) -> bool:
    """Apply the v2 foundation role contract to realized telemetry."""
    role = scenario.get("dataset_role")
    events = qa.get("events") or {}
    fire_count = int(events.get("fire_count", 0))
    damage_count = int(events.get("damage_count", 0))
    declared_fire = bool(
        (scenario.get("acceptance") or {}).get("fire_required")
    )
    actual_relation = relation.get("actual_target_relation")
    enemy_environmental_fire_safe = (
        role != "foundation_enemy_distractor"
        or fire_count == 0
        or (
            declared_fire
            and actual_relation
            in {
                "offscreen_or_occluded",
                "visible_far",
                "near_crosshair",
            }
            and (
                relation.get("minimum_angular_error_deg") is None
                or float(relation["minimum_angular_error_deg"]) > 3.0
            )
        )
    )
    fire_intent_safe = fire_count == 0 or declared_fire
    blockage_metrics = (
        (qa.get("telemetry") or {}).get("movement_blockage")
        or motion.get("blockage")
        or {}
    )
    collision_policy_passed = bool(
        blockage_metrics.get(
            "collision_policy_passed",
            not bool(
                blockage_metrics.get(
                    "training_exclusion_recommended", False
                )
            ),
        )
    )
    enemy_trace_passed = (
        (qa.get("enemy_policy") or {})
        .get("whole_path_trace", {})
        .get("passed")
        is True
    )
    route_passed = (qa.get("route") or {}).get("passed") is True
    return (
        damage_count == 0
        and fire_intent_safe
        and enemy_environmental_fire_safe
        and collision_policy_passed
        and enemy_trace_passed
        and route_passed
    )


@dataclasses.dataclass
class ProcessResult:
    command: list[str]
    returncode: int
    wall_seconds: float
    log_path: Path
    timed_out: bool = False
    abort_pattern: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def authoritative_hash_value(value: Any) -> Any:
    """Remove wall/start-time coordinates while preserving simulation truth."""
    if isinstance(value, dict):
        return {
            key: authoritative_hash_value(item)
            for key, item in value.items()
            if key != "server_time"
        }
    if isinstance(value, list):
        return [authoritative_hash_value(item) for item in value]
    return value


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(row))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise CaptureFailure(
                    "invalid_jsonl", f"{path}:{line_number}: {exc}"
                ) from exc
    return rows


def stage1_audio_expectation(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Derive the formal Stage-1 non-silence expectation deterministically.

    Natural silence is valid when the certified player trajectory never
    crosses Xonotic's native footstep speed threshold and no declared jump,
    weapon action, or moving-enemy audio source exists.  This function only
    controls whether non-silence is required; it never removes naturally
    occurring audio and never synthesizes a fallback waveform.

    If certified speed evidence is absent, preserve a true manifest
    declaration as a fail-closed compatibility path.  Formal v5 rows always
    carry certified evidence, so that branch is not used in production.
    """

    action_design = scenario.get("action_design") or {}
    weapon_action = str(
        action_design.get("weapon_action", "none")
    ).strip().lower()
    weapon_sound_expected = weapon_action not in {"", "none"}
    jump_sound_expected = bool(action_design.get("jump", False))

    enemy_present = bool(scenario.get("enemy_present", False))
    enemy = scenario.get("enemy") or {}
    enemy_policy = scenario.get("enemy_policy") or {}
    enemy_motion_mode = int(
        enemy.get(
            "motion",
            enemy_policy.get("motion_mode", 0),
        )
    )
    enemy_audio_mode = str(
        enemy_policy.get(
            "movement_audio", ENEMY_MOVEMENT_AUDIO_MODE
        )
    )
    enemy_movement_sound_expected = bool(
        enemy_present
        and enemy_motion_mode != 0
        and enemy_audio_mode == ENEMY_MOVEMENT_AUDIO_MODE
    )

    speed_source = None
    speed_max: float | None = None
    for source_name, motion in (
        (
            "certified_realized_motion",
            scenario.get("certified_realized_motion") or {},
        ),
        (
            "player_path_certificate.motion",
            (
                scenario.get("player_path_certificate") or {}
            ).get("motion")
            or {},
        ),
    ):
        raw_speed = motion.get("speed_max")
        if raw_speed is None:
            continue
        try:
            candidate = float(raw_speed)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(candidate) or candidate < 0:
            continue
        speed_source = source_name
        speed_max = candidate
        break

    declared = bool(scenario.get("expects_sound", False))
    certified_speed_available = speed_max is not None
    if certified_speed_available:
        player_footstep_sound_expected = bool(
            speed_max > STAGE1_PLAYER_FOOTSTEP_SPEED_THRESHOLD
        )
        speed_policy = "certified_realized_speed"
    else:
                                                                          
                         
        player_footstep_sound_expected = bool(
            declared
            and not (
                weapon_sound_expected
                or jump_sound_expected
                or enemy_movement_sound_expected
            )
        )
        speed_policy = "manifest_true_fail_closed"

    reasons = []
    if weapon_sound_expected:
        reasons.append(f"weapon_action:{weapon_action}")
    if jump_sound_expected:
        reasons.append("declared_jump")
    if enemy_movement_sound_expected:
        reasons.append("moving_enemy_native_footsteps")
    if player_footstep_sound_expected:
        reasons.append(
            (
                "certified_player_speed_above_native_footstep_threshold"
                if certified_speed_available
                else "legacy_manifest_true_without_certified_speed"
            )
        )
    expects_sound = bool(reasons)
    return {
        "schema_version": STAGE1_AUDIO_EXPECTATION_POLICY_SCHEMA,
        "expects_sound": expects_sound,
        "manifest_declared_expects_sound": declared,
        "manifest_value_changed": expects_sound != declared,
        "reasons": reasons,
        "weapon_action": weapon_action,
        "jump_declared": jump_sound_expected,
        "enemy_present": enemy_present,
        "enemy_motion_mode": enemy_motion_mode,
        "enemy_movement_audio_mode": enemy_audio_mode,
        "certified_speed_available": certified_speed_available,
        "certified_speed_source": speed_source,
        "certified_speed_max": speed_max,
        "player_footstep_speed_policy": speed_policy,
        "player_footstep_speed_threshold": (
            STAGE1_PLAYER_FOOTSTEP_SPEED_THRESHOLD
        ),
        "native_contract": (
            "Xonotic 0.8.6 PM_Footsteps: emit only when "
            "velocity > sv_maxspeed * 0.6; locked sv_maxspeed=360"
        ),
        "silence_allowed": not expects_sound,
        "synthetic_audio_fallback": False,
    }


def require_conda() -> None:
    prefix = Path(os.environ.get("CONDA_PREFIX", ""))
    if prefix.resolve() != CONDA_PREFIX_REQUIRED.resolve():
        raise CaptureFailure(
            "wrong_conda_environment",
            f"CONDA_PREFIX={prefix}; required={CONDA_PREFIX_REQUIRED}",
        )


def configured_x264_threads() -> int:
    raw = os.environ.get("XONOTIC_X264_THREADS", "0")
    try:
        threads = int(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_x264_threads", raw) from exc
    if threads < 0 or threads > 256:
        raise CaptureFailure("invalid_x264_threads", raw)
    return threads


def parse_cpu_list(value: str) -> set[int]:
    cpus: set[int] = set()
    if not value:
        return cpus
    for part in value.split(","):
        if re.fullmatch(r"\d+", part):
            cpus.add(int(part))
            continue
        match = re.fullmatch(r"(\d+)-(\d+)", part)
        if match is None:
            raise CaptureFailure("invalid_x264_cpuset", value)
        start, end = (int(item) for item in match.groups())
        if start > end:
            raise CaptureFailure("invalid_x264_cpuset", value)
        cpus.update(range(start, end + 1))
    return cpus


def configured_x264_cpuset() -> str:
    value = os.environ.get("XONOTIC_X264_CPUSET", "").strip()
    requested = parse_cpu_list(value)
    if not requested:
        return ""
    effective_path = Path("/sys/fs/cgroup/cpuset.cpus.effective")
    if effective_path.is_file():
        effective = parse_cpu_list(
            effective_path.read_text(encoding="utf-8").strip()
        )
        if not requested <= effective:
            raise CaptureFailure(
                "x264_cpuset_outside_effective",
                f"requested={value} "
                f"effective={effective_path.read_text().strip()}",
            )
    return value


def configured_x264_cpuset_cpu_count() -> int:
    return len(parse_cpu_list(configured_x264_cpuset()))


def configured_encode_concurrency() -> int:
    raw = os.environ.get("XONOTIC_ENCODE_CONCURRENCY", "0")
    try:
        workers = int(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_encode_concurrency", raw) from exc
    if workers < 0 or workers > 256:
        raise CaptureFailure("invalid_encode_concurrency", raw)
    return workers


def configured_encode_slot_directory() -> Path | None:
    raw = os.environ.get("XONOTIC_ENCODE_SLOT_DIRECTORY", "").strip()
    return Path(raw).resolve() if raw else None


def configured_live_concurrency() -> int:
    raw = os.environ.get("XONOTIC_LIVE_CONCURRENCY", "0")
    try:
        workers = int(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_live_concurrency", raw) from exc
    if workers < 0 or workers > 256:
        raise CaptureFailure("invalid_live_concurrency", raw)
    return workers


def configured_render_concurrency() -> int:
    raw = os.environ.get("XONOTIC_RENDER_CONCURRENCY", "0")
    try:
        workers = int(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_render_concurrency", raw) from exc
    if workers < 0 or workers > 256:
        raise CaptureFailure("invalid_render_concurrency", raw)
    return workers


def configured_live_timeout_seconds() -> float:
    raw = os.environ.get("XONOTIC_LIVE_TIMEOUT_SECONDS", "180")
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_live_timeout_seconds", raw) from exc
    if not math.isfinite(timeout) or timeout < 30 or timeout > 3600:
        raise CaptureFailure("invalid_live_timeout_seconds", raw)
    return timeout


def configured_engine_net_timeout_seconds() -> float:
    """Keep the engine's network watchdog outside the capture watchdog."""
    raw = os.environ.get("XONOTIC_ENGINE_NET_TIMEOUT_SECONDS", "600")
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_engine_net_timeout_seconds", raw) from exc
    if not math.isfinite(timeout) or timeout < 60 or timeout > 7200:
        raise CaptureFailure("invalid_engine_net_timeout_seconds", raw)
    live_timeout = configured_live_timeout_seconds()
    if timeout <= live_timeout:
        raise CaptureFailure(
            "engine_net_timeout_not_above_live_timeout",
            f"engine={timeout} live={live_timeout}",
        )
    return timeout


def configured_render_timeout_seconds() -> float:
    raw = os.environ.get("XONOTIC_RENDER_TIMEOUT_SECONDS", "240")
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_render_timeout_seconds", raw) from exc
    if not math.isfinite(timeout) or timeout < 30 or timeout > 3600:
        raise CaptureFailure("invalid_render_timeout_seconds", raw)
    return timeout


def configured_render_startup_stall_seconds() -> float:
    """Grace after demo sign-on before the offline output window must begin."""
    raw = os.environ.get(
        "XONOTIC_RENDER_STARTUP_STALL_SECONDS", "45"
    )
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise CaptureFailure(
            "invalid_render_startup_stall_seconds", raw
        ) from exc
    if not math.isfinite(timeout) or timeout < 10 or timeout > 300:
        raise CaptureFailure(
            "invalid_render_startup_stall_seconds", raw
        )
    return timeout


def configured_resident_control_timeout_seconds() -> float:
    """Bound one resident console/control-plane state transition."""
    raw = os.environ.get(
        "XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "60"
    )
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise CaptureFailure(
            "invalid_resident_control_timeout_seconds", raw
        ) from exc
    if not math.isfinite(timeout) or timeout < 30 or timeout > 600:
        raise CaptureFailure(
            "invalid_resident_control_timeout_seconds", raw
        )
    return timeout


def configured_sdl_concurrency() -> int:
    raw = os.environ.get("XONOTIC_SDL_CONCURRENCY", "0")
    try:
        workers = int(raw)
    except ValueError as exc:
        raise CaptureFailure("invalid_sdl_concurrency", raw) from exc
    if workers < 0 or workers > 256:
        raise CaptureFailure("invalid_sdl_concurrency", raw)
    return workers


@contextmanager
def live_slot() -> Iterable[float]:
    """Limit concurrent dedicated-server/live-client pairs."""
    global _LIVE_SEMAPHORE_LIMIT, _LIVE_SEMAPHORE
    limit = configured_live_concurrency()
    with _LIVE_SEMAPHORE_LOCK:
        if _LIVE_SEMAPHORE_LIMIT != limit:
            _LIVE_SEMAPHORE_LIMIT = limit
            _LIVE_SEMAPHORE = BoundedSemaphore(limit) if limit else None
        semaphore = _LIVE_SEMAPHORE
    started = time.monotonic()
    if semaphore is not None:
        semaphore.acquire()
    waited = time.monotonic() - started
    try:
        yield waited
    finally:
        if semaphore is not None:
            semaphore.release()


@contextmanager
def render_slot() -> Iterable[float]:
    """Limit concurrent SDL offscreen/EGL replay render clients."""
    global _RENDER_SEMAPHORE_LIMIT, _RENDER_SEMAPHORE
    limit = configured_render_concurrency()
    with _RENDER_SEMAPHORE_LOCK:
        if _RENDER_SEMAPHORE_LIMIT != limit:
            _RENDER_SEMAPHORE_LIMIT = limit
            _RENDER_SEMAPHORE = (
                BoundedSemaphore(limit) if limit else None
            )
        semaphore = _RENDER_SEMAPHORE
    started = time.monotonic()
    if semaphore is not None:
        semaphore.acquire()
    waited = time.monotonic() - started
    try:
        yield waited
    finally:
        if semaphore is not None:
            semaphore.release()


@contextmanager
def sdl_slot() -> Iterable[float]:
    """Limit total live plus offline SDL clients sharing this GPU."""
    global _SDL_SEMAPHORE_LIMIT, _SDL_SEMAPHORE
    limit = configured_sdl_concurrency()
    with _SDL_SEMAPHORE_LOCK:
        if _SDL_SEMAPHORE_LIMIT != limit:
            _SDL_SEMAPHORE_LIMIT = limit
            _SDL_SEMAPHORE = BoundedSemaphore(limit) if limit else None
        semaphore = _SDL_SEMAPHORE
    started = time.monotonic()
    if semaphore is not None:
        semaphore.acquire()
    waited = time.monotonic() - started
    try:
        yield waited
    finally:
        if semaphore is not None:
            semaphore.release()


@contextmanager
def encode_slot() -> Iterable[float]:
    """Limit concurrent CPU encoders while leaving render workers independent."""
    global _ENCODE_SEMAPHORE_LIMIT, _ENCODE_SEMAPHORE
    limit = configured_encode_concurrency()
    shared_directory = configured_encode_slot_directory()
    if limit and shared_directory is not None:
        try:
            shared_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CaptureFailure(
                "encode_slot_directory_failed",
                str(shared_directory),
            ) from exc
        started = time.monotonic()
        handle = None
        while handle is None:
            for slot_index in range(limit):
                candidate = (
                    shared_directory / f"encode-slot-{slot_index:03d}.lock"
                ).open("a+b")
                try:
                    fcntl.flock(
                        candidate.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                except BlockingIOError:
                    candidate.close()
                    continue
                handle = candidate
                break
            if handle is None:
                time.sleep(0.01)
        waited = time.monotonic() - started
        try:
            yield waited
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        return
    with _ENCODE_SEMAPHORE_LOCK:
        if _ENCODE_SEMAPHORE_LIMIT != limit:
            _ENCODE_SEMAPHORE_LIMIT = limit
            _ENCODE_SEMAPHORE = (
                BoundedSemaphore(limit) if limit else None
            )
        semaphore = _ENCODE_SEMAPHORE
    started = time.monotonic()
    if semaphore is not None:
        semaphore.acquire()
    waited = time.monotonic() - started
    try:
        yield waited
    finally:
        if semaphore is not None:
            semaphore.release()


def is_nvidia_hardware_renderer(renderer: str, console: str = "") -> bool:
    """Accept NVIDIA hardware independent of the deployed GPU generation."""
    combined = f"{renderer}\n{console}"
    return (
        "NVIDIA" in renderer.upper()
        and SOFTWARE_RENDERER_RE.search(combined) is None
    )


def build_root() -> Path:
    build_glob = os.environ.get(
        "XONOTIC_BUILD_GLOB", f"build/capture-*-{platform.machine()}"
    )
    candidates = sorted(
        ROOT.glob(build_glob),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if (
            (candidate / "bin/xonotic-local-sdl").is_file()
            and (candidate / "bin/xonotic-local-dedicated").is_file()
            and (candidate / "qc/progs.dat").is_file()
        ):
            return candidate
    raise CaptureFailure("capture_build_missing", str(ROOT / "build"))


def validate_fixed_assets() -> None:
    if not ASSET_ALLOWLIST.is_file():
        raise CaptureFailure("asset_allowlist_missing", str(ASSET_ALLOWLIST))
    allowlist = json.loads(ASSET_ALLOWLIST.read_text(encoding="utf-8"))
    expected = {
        row["filename"]: int(row["size_bytes"])
        for row in allowlist["packages"]
    }
    actual = {
        path.name: path.stat().st_size
        for path in (BASEDIR / "data").glob("*.pk3")
        if path.is_file()
    }
    if actual != expected:
        raise CaptureFailure(
            "official_asset_set_mismatch",
            canonical_json({"expected": expected, "actual": actual}),
        )
    forbidden = list((BASEDIR / "data").glob("*dlcache*")) + list(
        (BASEDIR / "data").glob("*.pk3dir")
    )
    if forbidden:
        raise CaptureFailure(
            "forbidden_asset_cache", ",".join(str(path) for path in forbidden)
        )


def validate_scenario_assets(scenario: dict[str, Any]) -> None:
    allowlist = json.loads(ASSET_ALLOWLIST.read_text(encoding="utf-8"))
    enemy_present = bool(scenario.get("enemy_present", True))
    appearance = allowlist.get("enemy_appearances", {})
    checks = {
        "map": scenario["map"] in allowlist["maps"],
        "enemy_model": (
            not enemy_present
            or scenario.get("enemy_model") in allowlist["enemy_models"]
        ),
        "enemy_skin": (
            not enemy_present
            or int(scenario.get("enemy_skin", 0))
            in appearance.get("skins", [0])
        ),
        "enemy_color": (
            not enemy_present
            or int(scenario.get("enemy_color", 0))
            in appearance.get("color_palette", [0])
        ),
        "weapon": scenario["weapon"] in allowlist["weapons"],
        "policy": scenario["asset_policy"] == allowlist["asset_policy"],
    }
    if not all(checks.values()):
        raise CaptureFailure("scenario_asset_not_allowlisted", canonical_json(checks))


def verify_asset_hashes() -> dict[str, Any]:
    allowlist = json.loads(ASSET_ALLOWLIST.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for expected in allowlist["packages"]:
        path = BASEDIR / "data" / expected["filename"]
        observed = sha256_file(path)
        row = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "expected_sha256": expected["sha256"],
            "observed_sha256": observed,
            "pass": observed == expected["sha256"],
        }
        results.append(row)
    evidence = {
        "schema_version": "xonotic-asset-verification-v1",
        "verified_utc": utc_now(),
        "allowlist": str(ASSET_ALLOWLIST),
        "packages": results,
        "pass": all(row["pass"] for row in results),
    }
    output = ROOT / "qa/asset_verification.json"
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not evidence["pass"]:
        raise CaptureFailure("official_asset_hash_mismatch", str(output))
    return evidence


def parse_official_bsp_spawns(payload: bytes) -> list[list[float]]:
    if payload[:4] != b"IBSP" or struct.unpack_from("<i", payload, 4)[0] != 46:
        raise CaptureFailure("anchor_bsp_format", repr(payload[:8]))
    entity_offset, entity_length = struct.unpack_from("<ii", payload, 8)
    entity_text = payload[
        entity_offset : entity_offset + entity_length
    ].rstrip(b"\0").decode("utf-8", errors="strict")
    spawns: list[list[float]] = []
    for block in re.findall(r"\{([^}]*)\}", entity_text, re.DOTALL):
        values = dict(
            re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', block)
        )
        if values.get("classname") != "info_player_deathmatch":
            continue
        origin = [float(value) for value in values["origin"].split()]
        if len(origin) != 3:
            raise CaptureFailure("anchor_bsp_origin", values["origin"])
        spawns.append(origin)
    return spawns


def verify_anchor_catalog() -> dict[str, Any]:
    catalog = json.loads(ANCHOR_CATALOG_PATH.read_text(encoding="utf-8"))
    source = catalog["source"]
    archive = Path(source["archive"])
    archive_hash = sha256_file(archive)
    checks: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive) as package:
        for map_name, map_spec in catalog["maps"].items():
            payload = package.read(map_spec["bsp_path"])
            bsp_hash = hashlib.sha256(payload).hexdigest()
            spawns = parse_official_bsp_spawns(payload)
            map_hash_ok = bsp_hash == source["bsp_sha256"][map_name]
            for anchor in map_spec["anchors"]:
                player_index = int(anchor["player_spawn_index"])
                enemy_index = int(anchor["enemy_spawn_index"])
                observed_player = spawns[player_index]
                observed_enemy = spawns[enemy_index]
                player_ok = np.allclose(
                    observed_player, anchor["player_origin"], atol=1e-6
                )
                enemy_ok = np.allclose(
                    observed_enemy, anchor["enemy_origin"], atol=1e-6
                )
                checks.append(
                    {
                        "map": map_name,
                        "anchor_id": anchor["anchor_id"],
                        "bsp_sha256": bsp_hash,
                        "bsp_sha256_match": map_hash_ok,
                        "player_spawn_index": player_index,
                        "player_origin_match": bool(player_ok),
                        "enemy_spawn_index": enemy_index,
                        "enemy_origin_match": bool(enemy_ok),
                        "pass": bool(map_hash_ok and player_ok and enemy_ok),
                    }
                )
    evidence = {
        "schema_version": "xonotic-anchor-catalog-verification-v1",
        "verified_utc": utc_now(),
        "catalog": str(ANCHOR_CATALOG_PATH),
        "archive": str(archive),
        "archive_expected_sha256": source["archive_sha256"],
        "archive_observed_sha256": archive_hash,
        "archive_sha256_match": archive_hash == source["archive_sha256"],
        "anchors": checks,
        "pass": (
            archive_hash == source["archive_sha256"]
            and len(checks) == 12
            and all(row["pass"] for row in checks)
        ),
    }
    output = ROOT / "qa/anchor_catalog_verification.json"
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not evidence["pass"]:
        raise CaptureFailure("anchor_catalog_verification_failed", str(output))
    return catalog


def yaw_toward(source: list[float], target: list[float]) -> float:
    return math.degrees(math.atan2(target[1] - source[1], target[0] - source[0]))


def deterministic_xy_jitter(seed: int, salt: int) -> list[float]:
    policy = json.loads(
        ANCHOR_CATALOG_PATH.read_text(encoding="utf-8")
    )["deterministic_xy_jitter"]
    modulus = int(policy["modulus"])
    maximum = float(policy["maximum_absolute_offset"])
    grid_step = float(policy["grid_step"])
    expected_modulus = int(round(maximum * 2 / grid_step)) + 1
    if (
        grid_step <= 0
        or modulus != expected_modulus
        or not math.isclose(
            (modulus - 1) * grid_step,
            maximum * 2,
            abs_tol=1e-9,
        )
    ):
        raise CaptureFailure("anchor_jitter_policy_invalid", canonical_json(policy))
    return [
        round(
            float((seed * 37 + salt * 17) % modulus) * grid_step - maximum,
            6,
        ),
        round(
            float((seed * 61 + salt * 29) % modulus) * grid_step - maximum,
            6,
        ),
    ]


def scenario_for(index: int, target_bin: str, ordinal: int) -> dict[str, Any]:
    catalog = json.loads(ANCHOR_CATALOG_PATH.read_text(encoding="utf-8"))
    maps = ["stormkeep", "solarium", "xoylent"]
    models = ["ignis", "nyx", "seraphina"]
    weapons = ["MachineGun", "Shotgun", "Vortex", "Devastator"]
    map_name = maps[(index - 1) % len(maps)]
    model = models[((index - 1) // len(maps)) % len(models)]
    anchors = catalog["maps"][map_name]["anchors"]
    anchor = anchors[((index - 1) // len(maps)) % len(anchors)]
    seed = 860_000 + index
    player_jitter = deterministic_xy_jitter(seed, 1)
    enemy_jitter = deterministic_xy_jitter(seed, 2)
    weapon = weapons[(index - 1) % len(weapons)]
    intent = "none"
    atomic_kind = ""
    enemy_motion = 0
    enemy_health = 200.0
    clip = 60.0
    reserve = 180.0
    expects_sound = True

    if target_bin == "atomic_dynamics":
        atomic_kind = ["forward", "strafe", "view", "jump"][ordinal % 4]
        weapon = weapons[ordinal % 4]
        expects_sound = atomic_kind != "view"
    elif target_bin == "mixed_dynamics":
        enemy_motion = (ordinal % 3) + 1
        weapon = weapons[ordinal % 4]
    elif target_bin == "combat_outcome":
        weapon = weapons[ordinal % 4]
        intent_by_weapon = {
            "MachineGun": ["hit", "direct", "kill", "miss"],
            "Shotgun": ["hit", "pellet", "kill", "miss"],
            "Vortex": ["hit", "direct", "kill", "miss"],
            "Devastator": ["hit", "splash", "kill", "miss"],
        }
        intent = intent_by_weapon[weapon][(ordinal // 4) % 4]
        if intent == "kill":
            if weapon == "MachineGun":
                enemy_health = 12.0
            elif weapon == "Shotgun" and map_name == "xoylent":
                                                                          
                                                                             
                                                                              
                enemy_health = 8.0
            else:
                enemy_health = 20.0
        elif intent == "miss":
            enemy_health = 200.0
        elif weapon == "Devastator":
            enemy_health = 250.0
        enemy_motion = ordinal % 4
    elif target_bin == "mobile_fire":
        weapon = weapons[ordinal % 4]
        intent = ["hit", "tracking", "jump_fire", "moving_fire"][ordinal % 4]
                                                                       
                                                                            
                                                                              
                                                                           
                                                                
        enemy_motion = (
            0
            if (
                weapon == "Devastator"
                or (map_name == "xoylent" and weapon == "Vortex")
            )
            else (ordinal % 3) + 1
        )
        enemy_health = 250.0
    elif target_bin == "machinegun_reload":
        weapon = "MachineGun"
        intent = "reload_success"
        enemy_motion = ordinal % 4
        clip = 12.0
        reserve = 90.0
    else:
        raise ValueError(target_bin)

    player_origin = [
        float(anchor["player_origin"][0]) + float(player_jitter[0]),
        float(anchor["player_origin"][1]) + float(player_jitter[1]),
        float(anchor["player_origin"][2]),
    ]
    enemy_origin = [
        float(anchor["enemy_origin"][0]) + float(enemy_jitter[0]),
        float(anchor["enemy_origin"][1]) + float(enemy_jitter[1]),
        float(anchor["enemy_origin"][2]),
    ]
    player_yaw = yaw_toward(player_origin, enemy_origin)
    enemy_yaw = yaw_toward(enemy_origin, player_origin)
    radial_x = enemy_origin[0] - player_origin[0]
    radial_y = enemy_origin[1] - player_origin[1]
    radial_length = math.hypot(radial_x, radial_y)
    if radial_length < 1:
        raise CaptureFailure("anchor_pair_too_close", anchor["anchor_id"])
    motion_vector = [-radial_y / radial_length, radial_x / radial_length, 0.0]
    return {
        "schema_version": "xonotic-pilot-scenario-v1",
        "episode_id": f"pilot_{index:03d}",
        "split": "pilot",
        "seed": seed,
        "target_bin": target_bin,
        "target_ordinal": ordinal,
        "intent_outcome": intent,
        "atomic_kind": atomic_kind,
        "map": map_name,
        "anchor_id": anchor["anchor_id"],
        "anchor": {
            "catalog": str(ANCHOR_CATALOG_PATH),
            "player_spawn_index": anchor["player_spawn_index"],
            "enemy_spawn_index": anchor["enemy_spawn_index"],
            "player_xy_jitter": list(player_jitter),
            "enemy_xy_jitter": list(enemy_jitter),
        },
        "enemy_model": model,
        "weapon": weapon,
        "weapon_netname": WEAPON_NETNAME[weapon],
        "warmup_ticks": WARMUP_TICKS,
        "output_ticks": OUTPUT_TICKS,
        "tick_hz": TICK_HZ,
        "video": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": VIDEO_FPS,
            "frames": OUTPUT_TICKS,
        },
        "audio": {
            "sample_rate": AUDIO_RATE,
            "channels": 2,
            "sample_format": "s16",
            "samples_per_channel": AUDIO_SAMPLES,
            "samples_per_frame": SAMPLES_PER_FRAME,
        },
        "player": {
            "origin": player_origin,
            "yaw": player_yaw,
            "health": 200.0,
            "armor": 0.0,
            "clip": clip,
            "reserve": reserve,
        },
        "enemy": {
            "origin": enemy_origin,
            "yaw": enemy_yaw,
            "health": enemy_health,
            "armor": 0.0,
            "motion": enemy_motion,
            "motion_vector": [round(value, 9) for value in motion_vector],
            "motion_distance": 64.0 if enemy_motion else 0.0,
        },
        "expects_sound": expects_sound,
        "asset_policy": "official-xonotic-0.8.6-only",
    }


def generate_scenarios() -> list[dict[str, Any]]:
    schema_path = ROOT / "configs/PILOT_SCHEMA.json"
    with schema_path.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    scenarios: list[dict[str, Any]] = []
    index = 1
    for target_bin, count in TARGET_COUNTS.items():
        for ordinal in range(count):
            scenario = scenario_for(index, target_bin, ordinal)
            jsonschema.validate(scenario, schema)
            scenarios.append(scenario)
            index += 1
    if len(scenarios) != 100:
        raise AssertionError(len(scenarios))
    if Counter(row["target_bin"] for row in scenarios) != Counter(TARGET_COUNTS):
        raise AssertionError("target distribution mismatch")
    return scenarios


def pulse(tick: int, starts: Iterable[int], width: int = 1) -> int:
    return int(any(start <= tick < start + width for start in starts))


def model_action_contract() -> dict[str, Any]:
    """Return the immutable LTX-2-compatible action representation."""
    return {
        "schema_version": MODEL_ACTION_SCHEMA_VERSION,
        "model_input_family": "LTX-2 CrossFPS action conditioning",
        "joystick_channel_order": list(MODEL_ACTION_JOYSTICK_CHANNELS),
        "joystick_range": [-1.0, 1.0],
        "axis_convention": {
            "j_left_x": "positive moves right",
            "j_left_y": "positive moves backward; negative moves forward",
            "j_right_x": (
                "positive turns camera right; negative turns camera left"
            ),
            "j_right_y": (
                "positive looks down; negative looks up"
            ),
        },
        "engine_decode": {
            "forward": (
                f"-j_left_y * {MODEL_ACTION_MOVEMENT_USERCMD_SCALE:g}"
            ),
            "strafe": (
                f"j_left_x * {MODEL_ACTION_MOVEMENT_USERCMD_SCALE:g}"
            ),
            "yaw_delta_degrees": (
                f"-j_right_x * {MODEL_ACTION_VIEW_DEGREES_PER_TICK:g}"
            ),
            "pitch_delta_degrees": (
                f"j_right_y * {MODEL_ACTION_VIEW_DEGREES_PER_TICK:g}"
            ),
        },
        "button_channel_order": list(
            MODEL_ACTION_CANONICAL_BUTTONS
        ),
        "button_columns": list(MODEL_ACTION_BUTTON_COLUMNS),
        "button_range": [0, 1],
        "button_meanings": MODEL_ACTION_BUTTON_MEANINGS,
        "frame_alignment": (
            "one row per rendered output frame; source_action_tick equals "
            "frames.parquet episode_server_tick"
        ),
        "warmup_rows_in_model_input": 0,
    }


def build_model_actions(
    actions: pd.DataFrame,
    frames: pd.DataFrame,
) -> pd.DataFrame:
    """Build one drop-in CrossFPS action row per rendered output frame.

    ``actions.parquet`` remains the complete 384-tick engine audit.  This
    table is deliberately separate: it contains the 320 frame-aligned,
    normalized model inputs expected by the LTX-2 CrossFPS loader.
    """
    required_actions = {
        "episode_id",
        "action_tick",
        "desired_forward",
        "desired_strafe",
        "desired_yaw_delta",
        "desired_pitch_delta",
        "desired_jump",
        "desired_primary",
        "desired_secondary",
        "desired_reload",
    }
    required_frames = {
        "episode_id",
        "frame_index",
        "pts_seconds",
        "episode_server_tick",
    }
    missing_actions = sorted(required_actions - set(actions.columns))
    missing_frames = sorted(required_frames - set(frames.columns))
    if missing_actions or missing_frames:
        raise CaptureFailure(
            "model_action_source_columns_missing",
            canonical_json(
                {
                    "actions": missing_actions,
                    "frames": missing_frames,
                }
            ),
        )

    action_ticks = pd.to_numeric(
        actions["action_tick"], errors="raise"
    ).astype(np.int64)
    if action_ticks.duplicated().any():
        raise CaptureFailure(
            "model_action_source_tick_duplicate",
            str(
                sorted(
                    set(
                        action_ticks[
                            action_ticks.duplicated(keep=False)
                        ].tolist()
                    )
                )[:10]
            ),
        )
    source = actions.copy()
    source["action_tick"] = action_ticks
    source = source.set_index("action_tick", drop=False)

    frame_ticks = pd.to_numeric(
        frames["episode_server_tick"], errors="raise"
    ).astype(np.int64)
    missing_ticks = sorted(set(frame_ticks) - set(action_ticks))
    if missing_ticks:
        raise CaptureFailure(
            "model_action_frame_tick_missing",
            str(missing_ticks[:10]),
        )
    aligned = source.loc[frame_ticks.to_numpy()].reset_index(drop=True)

    forward = pd.to_numeric(
        aligned["desired_forward"], errors="raise"
    ).to_numpy(dtype=np.float64)
    strafe = pd.to_numeric(
        aligned["desired_strafe"], errors="raise"
    ).to_numpy(dtype=np.float64)
    yaw_delta = pd.to_numeric(
        aligned["desired_yaw_delta"], errors="raise"
    ).to_numpy(dtype=np.float64)
    pitch_delta = pd.to_numeric(
        aligned["desired_pitch_delta"], errors="raise"
    ).to_numpy(dtype=np.float64)

    source_continuous = np.column_stack(
        (forward, strafe, yaw_delta, pitch_delta)
    )
    source_limits = np.asarray(
        [
            MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
            MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
            MODEL_ACTION_VIEW_DEGREES_PER_TICK,
            MODEL_ACTION_VIEW_DEGREES_PER_TICK,
        ],
        dtype=np.float64,
    )
    invalid_source = (
        ~np.isfinite(source_continuous)
        | (
            np.abs(source_continuous)
            > source_limits + MODEL_ACTION_SOURCE_TOLERANCE
        )
    )
    if invalid_source.any():
        row_indices, column_indices = np.nonzero(invalid_source)
        names = ("forward", "strafe", "yaw_delta", "pitch_delta")
        failures = [
            {
                "source_action_tick": int(
                    frame_ticks.iloc[int(row_index)]
                ),
                "axis": names[int(column_index)],
                "value": float(
                    source_continuous[row_index, column_index]
                ),
                "limit": float(source_limits[column_index]),
            }
            for row_index, column_index in zip(
                row_indices[:10], column_indices[:10]
            )
        ]
        raise CaptureFailure(
            "model_action_source_continuous_out_of_range",
            canonical_json(failures),
        )

                                                                      
                                                                            
    left_x = np.clip(
        strafe / MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
        -1.0,
        1.0,
    )
    left_y = np.clip(
        -forward / MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
        -1.0,
        1.0,
    )
    right_x = np.clip(
        -yaw_delta / MODEL_ACTION_VIEW_DEGREES_PER_TICK,
        -1.0,
        1.0,
    )
    right_y = np.clip(
        pitch_delta / MODEL_ACTION_VIEW_DEGREES_PER_TICK,
        -1.0,
        1.0,
    )

    def binary(column: str) -> np.ndarray:
        values = pd.to_numeric(
            aligned[column], errors="raise"
        ).to_numpy(dtype=np.float64)
        if not np.isin(values, (0.0, 1.0)).all():
            raise CaptureFailure(
                "model_action_source_button_nonbinary",
                column,
            )
        return values.astype(np.int8)

    jump = binary("desired_jump")
    primary = binary("desired_primary")
    secondary = binary("desired_secondary")
    reload_button = binary("desired_reload")
    zeros = np.zeros(len(frames), dtype=np.int8)

    result = pd.DataFrame(
        {
            "episode_id": frames["episode_id"].astype(str).to_numpy(),
            "frame_index": pd.to_numeric(
                frames["frame_index"], errors="raise"
            ).astype(np.int64),
            "pts_seconds": pd.to_numeric(
                frames["pts_seconds"], errors="raise"
            ).astype(np.float64),
            "source_action_tick": frame_ticks.to_numpy(),
            "south": jump,
            "east": zeros.copy(),
            "west": reload_button,
            "north": zeros.copy(),
            "left_shoulder": zeros.copy(),
            "right_shoulder": zeros.copy(),
            "left_trigger": secondary,
            "right_trigger": primary,
            "j_left": [
                [float(x), float(y)]
                for x, y in zip(left_x, left_y)
            ],
            "j_right": [
                [float(x), float(y)]
                for x, y in zip(right_x, right_y)
            ],
            "j_left_x": left_x.astype(np.float32),
            "j_left_y": left_y.astype(np.float32),
            "j_right_x": right_x.astype(np.float32),
            "j_right_y": right_y.astype(np.float32),
            "schema_version": MODEL_ACTION_SCHEMA_VERSION,
            "namespace": "model_input_ltx2_crossfps",
        }
    )
    return result


def model_action_metrics(
    model_actions: pd.DataFrame,
    actions: pd.DataFrame,
    frames: pd.DataFrame,
) -> dict[str, Any]:
    """Validate range, frame linkage, and lossless engine/button mapping."""
    required_model_columns = {
        "j_left",
        "j_right",
        *MODEL_ACTION_BUTTON_COLUMNS,
        *MODEL_ACTION_JOYSTICK_CHANNELS,
        "frame_index",
        "source_action_tick",
        "schema_version",
    }
    schema_columns_present = (
        required_model_columns <= set(model_actions.columns)
    )
    continuous = (
        model_actions[list(MODEL_ACTION_JOYSTICK_CHANNELS)]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(dtype=np.float64)
        if schema_columns_present
        else np.empty((0, 4), dtype=np.float64)
    )
    continuous_finite = bool(
        len(continuous) and np.isfinite(continuous).all()
    )
    continuous_in_range = bool(
        continuous_finite
        and (continuous >= -1.0).all()
        and (continuous <= 1.0).all()
    )
    joystick_pairs_valid = False
    joystick_pairs_match_flat = False
    if schema_columns_present:
        try:
            left_pairs = np.asarray(
                [list(value) for value in model_actions["j_left"]],
                dtype=np.float64,
            )
            right_pairs = np.asarray(
                [list(value) for value in model_actions["j_right"]],
                dtype=np.float64,
            )
            joystick_pairs_valid = bool(
                left_pairs.shape == (len(model_actions), 2)
                and right_pairs.shape == (len(model_actions), 2)
                and np.isfinite(left_pairs).all()
                and np.isfinite(right_pairs).all()
            )
            joystick_pairs_match_flat = bool(
                joystick_pairs_valid
                and np.allclose(
                    np.column_stack((left_pairs, right_pairs)),
                    continuous,
                    atol=1e-7,
                    rtol=0,
                )
            )
        except (TypeError, ValueError):
            pass
    button_values = (
        model_actions[list(MODEL_ACTION_BUTTON_COLUMNS)]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(dtype=np.float64)
        if schema_columns_present
        else np.empty((0, len(MODEL_ACTION_BUTTON_COLUMNS)))
    )
    buttons_binary = bool(
        len(button_values)
        and np.isfinite(button_values).all()
        and np.isin(button_values, (0.0, 1.0)).all()
    )

    expected_ticks = pd.to_numeric(
        frames.get("episode_server_tick"), errors="coerce"
    ).to_numpy(dtype=np.float64)
    observed_ticks = pd.to_numeric(
        model_actions.get("source_action_tick"), errors="coerce"
    ).to_numpy(dtype=np.float64)
    frame_indices = pd.to_numeric(
        model_actions.get("frame_index"), errors="coerce"
    ).to_numpy(dtype=np.float64)
    frame_alignment_exact = bool(
        len(model_actions) == OUTPUT_TICKS == len(frames)
        and np.array_equal(
            frame_indices,
            np.arange(OUTPUT_TICKS, dtype=np.float64),
        )
        and np.array_equal(observed_ticks, expected_ticks)
    )

    engine_roundtrip_max_error = math.inf
    button_source_match = False
    source_continuous_within_range = False
    if frame_alignment_exact and schema_columns_present:
        source = actions.copy()
        source["action_tick"] = pd.to_numeric(
            source["action_tick"], errors="raise"
        ).astype(np.int64)
        source = source.set_index("action_tick", drop=False)
        aligned = source.loc[
            observed_ticks.astype(np.int64)
        ].reset_index(drop=True)
        expected_engine = np.column_stack(
            (
                pd.to_numeric(
                    aligned["desired_forward"], errors="raise"
                ).to_numpy(dtype=np.float64),
                pd.to_numeric(
                    aligned["desired_strafe"], errors="raise"
                ).to_numpy(dtype=np.float64),
                pd.to_numeric(
                    aligned["desired_yaw_delta"], errors="raise"
                ).to_numpy(dtype=np.float64),
                pd.to_numeric(
                    aligned["desired_pitch_delta"], errors="raise"
                ).to_numpy(dtype=np.float64),
            )
        )
        source_limits = np.asarray(
            [
                MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
                MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
                MODEL_ACTION_VIEW_DEGREES_PER_TICK,
                MODEL_ACTION_VIEW_DEGREES_PER_TICK,
            ],
            dtype=np.float64,
        )
        source_continuous_within_range = bool(
            np.isfinite(expected_engine).all()
            and (
                np.abs(expected_engine)
                <= source_limits + MODEL_ACTION_SOURCE_TOLERANCE
            ).all()
        )
        decoded_engine = np.column_stack(
            (
                -continuous[:, 1]
                * MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
                continuous[:, 0]
                * MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
                -continuous[:, 2]
                * MODEL_ACTION_VIEW_DEGREES_PER_TICK,
                continuous[:, 3]
                * MODEL_ACTION_VIEW_DEGREES_PER_TICK,
            )
        )
        engine_roundtrip_max_error = float(
            np.max(np.abs(decoded_engine - expected_engine), initial=0.0)
        )
        expected_buttons = np.column_stack(
            (
                pd.to_numeric(
                    aligned["desired_jump"], errors="raise"
                ).to_numpy(dtype=np.int8),
                np.zeros(len(aligned), dtype=np.int8),
                pd.to_numeric(
                    aligned["desired_reload"], errors="raise"
                ).to_numpy(dtype=np.int8),
                np.zeros(len(aligned), dtype=np.int8),
                np.zeros(len(aligned), dtype=np.int8),
                np.zeros(len(aligned), dtype=np.int8),
                pd.to_numeric(
                    aligned["desired_secondary"], errors="raise"
                ).to_numpy(dtype=np.int8),
                pd.to_numeric(
                    aligned["desired_primary"], errors="raise"
                ).to_numpy(dtype=np.int8),
            )
        )
        button_source_match = bool(
            np.array_equal(button_values.astype(np.int8), expected_buttons)
        )

    return {
        "schema_version": MODEL_ACTION_SCHEMA_VERSION,
        "rows": len(model_actions),
        "expected_rows": OUTPUT_TICKS,
        "schema_columns_present": schema_columns_present,
        "frame_alignment_exact": frame_alignment_exact,
        "continuous_finite": continuous_finite,
        "continuous_in_range": continuous_in_range,
        "joystick_pairs_valid": joystick_pairs_valid,
        "joystick_pairs_match_flat": joystick_pairs_match_flat,
        "source_continuous_within_range": (
            source_continuous_within_range
        ),
        "engine_roundtrip_max_error": engine_roundtrip_max_error,
        "engine_roundtrip_exact": (
            engine_roundtrip_max_error
            <= MODEL_ACTION_SOURCE_TOLERANCE
        ),
        "buttons_binary": buttons_binary,
        "button_source_match": button_source_match,
        "joystick_min": (
            float(continuous.min()) if continuous.size else None
        ),
        "joystick_max": (
            float(continuous.max()) if continuous.size else None
        ),
        "button_active_frames": {
            column: (
                int(button_values[:, index].sum())
                if button_values.size
                else 0
            )
            for index, column in enumerate(
                MODEL_ACTION_BUTTON_COLUMNS
            )
        },
    }


def validate_model_action_source_rows(
    rows: Iterable[dict[str, Any]],
) -> None:
    """Reject schedules that cannot be represented by the locked model axes."""
    failures: list[dict[str, Any]] = []
    for row in rows:
        tick = int(row["tick"])
        if tick < WARMUP_TICKS:
            continue
        values = {
            "forward": float(row["forward"]),
            "strafe": float(row["strafe"]),
            "yaw_delta": float(row["yaw_delta"]),
            "pitch_delta": float(row["pitch_delta"]),
        }
        limits = {
            "forward": MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
            "strafe": MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
            "yaw_delta": MODEL_ACTION_VIEW_DEGREES_PER_TICK,
            "pitch_delta": MODEL_ACTION_VIEW_DEGREES_PER_TICK,
        }
        invalid_axes = {
            name: value
            for name, value in values.items()
            if (
                not math.isfinite(value)
                or abs(value) > limits[name] + MODEL_ACTION_SOURCE_TOLERANCE
            )
        }
        invalid_buttons = {
            name: row[name]
            for name in ("jump", "primary", "secondary", "reload")
            if float(row[name]) not in (0.0, 1.0)
        }
        if (
            invalid_axes
            or invalid_buttons
            or float(row["weapon_impulse"]) != 0.0
        ):
            failures.append(
                {
                    "tick": tick,
                    "axes": invalid_axes,
                    "buttons": invalid_buttons,
                    "weapon_impulse": row["weapon_impulse"],
                }
            )
    if failures:
        raise CaptureFailure(
            "model_action_source_contract_invalid",
            canonical_json(failures[:10]),
        )


def action_rows(scenario: dict[str, Any], retry: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if scenario.get("capture_route_calibration"):
        return [
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
            for tick in range(TOTAL_TICKS)
        ]
    target_bin = scenario["target_bin"]
    ordinal = int(scenario["target_ordinal"])
    intent = scenario["intent_outcome"]
    weapon = scenario["weapon"]
    for tick in range(TOTAL_TICKS):
        out_tick = tick - WARMUP_TICKS
        forward = 0.0
        strafe = 0.0
        yaw_delta = 0.0
        pitch_delta = 0.0
        jump = 0
        primary = 0
        secondary = 0
        reload_button = 0
        if out_tick >= 0:
            if target_bin == "atomic_dynamics":
                kind = scenario["atomic_kind"]
                if kind == "forward":
                    forward = 320.0 if out_tick < 224 else -180.0
                elif kind == "strafe":
                    strafe = 300.0 if out_tick < 160 else -300.0
                elif kind == "view":
                    yaw_delta = 0.30 * math.sin(out_tick / 24.0)
                    pitch_delta = 0.08 * math.sin(out_tick / 31.0)
                elif kind == "jump":
                    jump = pulse(out_tick, [24, 176], 2)
            elif target_bin == "mixed_dynamics":
                                                                        
                                                                          
                                                                            
                                 
                movement_phase = 2.0 * math.pi * out_tick / 64.0
                forward = 220.0 * math.sin(movement_phase)
                strafe = 160.0 * math.cos(movement_phase)
                yaw_delta = 0.20 * math.sin(out_tick / 27.0)
                pitch_delta = 0.05 * math.sin(out_tick / 39.0)
                jump = pulse(out_tick, [32, 184], 2)
            elif target_bin in {"combat_outcome", "mobile_fire"}:
                if target_bin == "mobile_fire":
                                                                       
                                                                         
                                                                           
                                                                           
                    movement_scale = (
                        0.30 if scenario["map"] == "xoylent" else 1.0
                    )
                    movement_phase = 2.0 * math.pi * out_tick / 64.0
                    forward = (
                        180.0 * movement_scale * math.sin(movement_phase)
                    )
                    strafe = (
                        140.0 * movement_scale * math.cos(movement_phase)
                    )
                                                                        
                                                                     
                                                                           
                                                                            
                                             
                    if not (
                        scenario["map"] == "xoylent"
                        and weapon == "Vortex"
                    ):
                        yaw_delta = 0.10 * math.sin(out_tick / 18.0)
                    jump = pulse(out_tick, [44, 196], 2)
                if intent == "miss":
                                                                                 
                                                                             
                    if out_tick < 32:
                        yaw_delta = (8.0 + retry * 2.0) / 32.0
                elif intent == "splash":
                    if out_tick < 32:
                                                                       
                                                                            
                                                                            
                                                                            
                                                      
                        yaw_delta = 5.0 / 32.0
                if weapon == "MachineGun":
                    primary = pulse(out_tick, [48, 136, 224], 24)
                elif weapon == "Shotgun":
                    primary = pulse(out_tick, [56, 144, 232], 2)
                elif weapon == "Vortex":
                    primary = pulse(out_tick, [64, 176, 272], 2)
                elif weapon == "Devastator":
                    primary_starts = (
                        [16, 144]
                        if target_bin == "mobile_fire"
                        else [48, 176]
                    )
                    primary = pulse(out_tick, primary_starts, 2)
                    secondary = pulse(
                        out_tick,
                        (
                            [64, 192]
                            if target_bin == "mobile_fire"
                            else (
                                [94, 222]
                                if intent == "splash"
                                else [112, 240]
                            )
                        ),
                        2,
                    )
            elif target_bin == "machinegun_reload":
                primary = pulse(out_tick, [24], 16)
                reload_button = pulse(out_tick, [72], 1)
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


                                                                           
                                                                               
                                                                             
CANONICAL_ACTION_ROWS = action_rows


ACTION_ROW_PROVIDERS: dict[
    str,
    tuple[str, Callable[[dict[str, Any], int], list[dict[str, Any]]]],
] = {}


def registered_action_rows(
    scenario: dict[str, Any], retry: int = 0
) -> list[dict[str, Any]]:
    """Dispatch an extension action program without import-order coupling."""
    program = str(scenario.get("action_program", ""))
    registration = ACTION_ROW_PROVIDERS.get(program)
    if registration is None:
        return CANONICAL_ACTION_ROWS(scenario, retry=retry)
    _, provider = registration
    return provider(scenario, retry=retry)


def register_action_row_provider(
    provider_name: str,
    programs: Iterable[str],
    provider: Callable[
        [dict[str, Any], int], list[dict[str, Any]]
    ],
) -> None:
    """Register exact action-program ownership and install one dispatcher."""
    for program_raw in programs:
        program = str(program_raw)
        existing = ACTION_ROW_PROVIDERS.get(program)
        if existing is not None and existing[0] != provider_name:
            raise RuntimeError(
                "action row provider conflict: "
                f"{program} owned by {existing[0]} and {provider_name}"
            )
        ACTION_ROW_PROVIDERS[program] = (provider_name, provider)
    globals()["action_rows"] = registered_action_rows


def physical_action_sha256(rows: Iterable[dict[str, Any]]) -> str:
    """Hash only the player-path controls, excluding semantic weapon input."""
    normalized = [
        {
            "tick": int(row["tick"]),
            "forward": round(float(row["forward"]), 6),
            "strafe": round(float(row["strafe"]), 6),
            "yaw_delta": round(float(row["yaw_delta"]), 6),
            "pitch_delta": round(float(row["pitch_delta"]), 6),
            "jump": int(bool(int(float(row["jump"])))),
        }
        for row in rows
    ]
    return hashlib.sha256(canonical_json(normalized).encode()).hexdigest()


def player_path_contract_sha256(
    scenario: dict[str, Any],
) -> str:
    """Hash every manifest field allowed to affect the certified path."""
    design = scenario.get("action_design") or {}
    physical_design = {
        name: design.get(name)
        for name in (
            "schema_version",
            "model_action_schema_version",
            "locomotion_direction",
            "movement_profile",
            "movement_xy_magnitude",
            "movement_speed",
            "view_direction",
            "view_profile",
            "yaw_amplitude",
            "pitch_amplitude",
            "jump",
        )
    }
    player = scenario.get("player") or {}
    enemy = scenario.get("enemy") or {}
    contract = {
        "map": scenario.get("map"),
        "gametype": scenario.get("gametype"),
        "seed": scenario.get("seed"),
        "player": {
            "origin": player.get("origin"),
            "yaw": player.get("yaw"),
            "pitch": player.get("pitch"),
            "health": player.get("health"),
            "armor": player.get("armor"),
        },
        "enemy_present": bool(scenario.get("enemy_present")),
        "enemy_origin": (
            enemy.get("origin")
            if scenario.get("enemy_present")
            else None
        ),
        "enemy_policy": (
            scenario.get("enemy_policy")
            if scenario.get("enemy_present")
            else None
        ),
        "route_request": scenario.get("route_request"),
        "route_view_policy": scenario.get("route_view_policy"),
        "player_path_generation": scenario.get(
            "player_path_generation"
        ),
        "stage1_safe_base_route": scenario.get(
            "stage1_safe_base_route"
        ),
        "stage1_route_command_scale": scenario.get(
            "stage1_route_command_scale"
        ),
        "stage1_locomotion_camera_offset_degrees": scenario.get(
            "stage1_locomotion_camera_offset_degrees"
        ),
        "stage1_preserve_certified_base_jump": scenario.get(
            "stage1_preserve_certified_base_jump"
        ),
        "collision_design": scenario.get("collision_design"),
        "physical_action_design": physical_design,
    }
    return hashlib.sha256(canonical_json(contract).encode()).hexdigest()


def validate_player_path_runtime_compatibility(
    compatibility: dict[str, Any],
    *,
    certificate_source_commit: str,
    runtime_source_commit: str,
    episode_id: str,
) -> dict[str, Any]:
    """Validate and cache one immutable exact commit-pair audit."""
    cache_key = (
        str(ROOT.resolve()),
        canonical_json(compatibility),
        certificate_source_commit,
        runtime_source_commit,
    )
    with _PLAYER_PATH_RUNTIME_COMPATIBILITY_CACHE_LOCK:
        cached = _PLAYER_PATH_RUNTIME_COMPATIBILITY_CACHE.get(
            cache_key
        )
    if cached is not None:
        return cached
    audit_path = locked_root_artifact(
        compatibility.get("audit_path", ""),
        compatibility.get("audit_sha256"),
        "player_path_runtime_compatibility_audit",
    )
    try:
        audit = json.loads(
            audit_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise CaptureFailure(
            "player_path_runtime_compatibility_invalid_json",
            str(audit_path),
        ) from exc
    scope = audit.get("authorization_scope") or {}
    checks = {
        "reference_schema": compatibility.get("schema_version")
        == PLAYER_PATH_RUNTIME_COMPATIBILITY_REFERENCE_SCHEMA,
        "audit_schema": audit.get("schema_version")
        == PLAYER_PATH_RUNTIME_COMPATIBILITY_SCHEMA,
        "audit_passed": audit.get("passed") is True,
        "certificate_source_commit": (
            compatibility.get("certificate_source_commit")
            == scope.get("certificate_source_commit")
            == certificate_source_commit
        ),
        "runtime_source_commit": (
            compatibility.get("runtime_source_commit")
            == scope.get("runtime_source_commit")
            == runtime_source_commit
        ),
        "certificate_index_path": (
            compatibility.get("certificate_index_path")
            == scope.get("certificate_index_path")
        ),
        "certificate_index_sha256": (
            compatibility.get("certificate_index_sha256")
            == scope.get("certificate_index_sha256")
        ),
        "exact_scope": scope.get("kind")
        == "exact_commit_pair_and_certificate_index",
        "no_generic_descendants": scope.get(
            "generic_descendant_commits_allowed"
        )
        is False,
        "no_runtime_fallback": scope.get(
            "runtime_fallback_allowed"
        )
        is False,
        "certificates_immutable": scope.get(
            "certificates_mutated"
        )
        is False,
    }
    if not all(checks.values()):
        raise CaptureFailure(
            "player_path_runtime_compatibility_failed",
            canonical_json(
                {"episode_id": episode_id, "checks": checks}
            ),
        )
    locked_root_artifact(
        compatibility["certificate_index_path"],
        compatibility["certificate_index_sha256"],
        "player_path_runtime_compatibility_index",
    )
    result = {
        "audit_path": str(audit_path),
        "checks": checks,
    }
    with _PLAYER_PATH_RUNTIME_COMPATIBILITY_CACHE_LOCK:
        _PLAYER_PATH_RUNTIME_COMPATIBILITY_CACHE[
            cache_key
        ] = result
    return result


def load_player_path_certificate(
    scenario: dict[str, Any],
) -> dict[str, Any] | None:
    reference = scenario.get("player_path_certificate")
    if not reference:
        return None
    certificate_path = locked_root_artifact(
        reference.get("certificate_path", ""),
        reference.get("certificate_sha256"),
        "player_path_certificate",
    )
    try:
        certificate = json.loads(
            certificate_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise CaptureFailure(
            "player_path_certificate_invalid_json",
            str(certificate_path),
        ) from exc
    runtime_source_commit = (
        build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    certificate_source_commit = str(
        certificate.get("source_commit", "")
    )
    source_compatibility: dict[str, Any] | None = None
    if certificate_source_commit != runtime_source_commit:
        compatibility = scenario.get(
            "player_path_runtime_compatibility"
        ) or {}
        source_compatibility = (
            validate_player_path_runtime_compatibility(
                compatibility,
                certificate_source_commit=certificate_source_commit,
                runtime_source_commit=runtime_source_commit,
                episode_id=str(scenario.get("episode_id", "")),
            )
        )
    checks = {
        "reference_schema": reference.get("schema_version")
        == PLAYER_PATH_REFERENCE_SCHEMA,
        "certificate_schema": certificate.get("schema_version")
        == PLAYER_PATH_CERTIFICATE_SCHEMA,
        "certified": reference.get("certified") is True
        and certificate.get("status") == "certified",
        "checks_passed": certificate.get("passed") is True,
        "prototype_id": reference.get("prototype_id")
        == certificate.get("prototype_id"),
        "source_commit": (
            reference.get("source_commit")
            == certificate.get("source_commit")
            and (
                certificate_source_commit == runtime_source_commit
                or source_compatibility is not None
            )
        ),
        "scenario_prototype": reference.get("prototype_id")
        == (
            (scenario.get("path_prototype") or {}).get("prototype_id")
            or scenario.get("source_prototype_id")
        ),
        "actions_path": reference.get("actions_path")
        == certificate.get("actions_path"),
        "actions_sha256": reference.get("actions_sha256")
        == certificate.get("actions_sha256"),
        "states_path": reference.get("states_path")
        == certificate.get("states_path"),
        "states_sha256": reference.get("states_sha256")
        == certificate.get("states_sha256"),
        "physical_action_sha256": reference.get(
            "physical_action_sha256"
        )
        == certificate.get("physical_action_sha256"),
        "path_contract_sha256": reference.get(
            "path_contract_sha256"
        )
        == certificate.get("path_contract_sha256")
        == player_path_contract_sha256(scenario),
        "seed": int(reference.get("seed", -1))
        == int(certificate.get("seed", -2))
        == int(scenario.get("seed", -3)),
    }
    if not all(checks.values()):
        raise CaptureFailure(
            "player_path_certificate_contract_failed",
            canonical_json(
                {
                    "episode_id": scenario.get("episode_id"),
                    "checks": checks,
                }
            ),
        )
    locked_root_artifact(
        certificate["actions_path"],
        certificate["actions_sha256"],
        "player_path_certificate_actions",
    )
    locked_root_artifact(
        certificate["states_path"],
        certificate["states_sha256"],
        "player_path_certificate_states",
    )
    return certificate


def _write_certified_path_with_weapon_overlay(
    path: Path,
    scenario: dict[str, Any],
    parsed: list[dict[str, Any]],
    expected_header: str,
    certificate: dict[str, Any],
) -> None:
    base_physical_hash = physical_action_sha256(parsed)
    forbidden_base_buttons = any(
        int(float(row[name])) != 0
        for row in parsed
        for name in ("primary", "secondary", "reload", "weapon_impulse")
    )
    checks = {
        "physical_action_sha256": base_physical_hash
        == certificate["physical_action_sha256"],
        "path_schedule_has_no_weapon_input": not forbidden_base_buttons,
        "frozen_actions_path": str(
            locked_root_artifact(
                scenario["frozen_actions_path"],
                scenario.get("frozen_actions_sha256"),
                "frozen_actions",
            )
        )
        == str(
            locked_root_artifact(
                certificate["actions_path"],
                certificate["actions_sha256"],
                "player_path_certificate_actions",
            )
        ),
    }
    if not all(checks.values()):
        raise CaptureFailure(
            "certified_player_path_action_contract_failed",
            canonical_json(checks),
        )
    design = scenario.get("action_design") or {}
    final_rows: list[dict[str, Any]] = []
    for source in parsed:
        row = dict(source)
        out_tick = int(row["tick"]) - WARMUP_TICKS
        primary, secondary, reload_button = stage1_weapon_controls(
            design, str(scenario["weapon"]), out_tick
        )
        row["primary"] = primary
        row["secondary"] = secondary
        row["reload"] = reload_button
        row["weapon_impulse"] = 0
        final_rows.append(row)
    if physical_action_sha256(final_rows) != base_physical_hash:
        raise CaptureFailure(
            "certified_player_path_physical_mutation",
            str(scenario.get("episode_id")),
        )
    validate_model_action_source_rows(final_rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(expected_header + "\n")
        writer = csv.DictWriter(handle, fieldnames=ACTION_COLUMNS)
        writer.writeheader()
        writer.writerows(final_rows)


def write_action_csv(
    path: Path, scenario: dict[str, Any], retry: int = 0
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frozen_path = scenario.get("frozen_actions_path")
                                                                    
                                                                           
                                                                          
                                                                      
    explicit_causal_composition = (
        scenario.get("dataset_role") == "causal_interaction"
        and str(scenario.get("action_program", "")).startswith(
            "stage2_causal_counterfactual_v"
        )
    )
    if frozen_path and not explicit_causal_composition:
        source = locked_root_artifact(
            frozen_path,
            scenario.get("frozen_actions_sha256"),
            "frozen_actions",
        )
        lines = source.read_text(encoding="utf-8").splitlines()
        expected_header = f"#seed,{scenario['seed']}"
        if not lines or lines[0] != expected_header:
            raise CaptureFailure(
                "frozen_action_seed_mismatch",
                f"expected={expected_header!r} path={source}",
            )
        parsed = list(csv.DictReader(lines[1:]))
        if (
            len(parsed) != TOTAL_TICKS
            or list(parsed[0]) != ACTION_COLUMNS
            or [int(row["tick"]) for row in parsed]
            != list(range(TOTAL_TICKS))
        ):
            raise CaptureFailure(
                "frozen_action_contract_invalid", str(source)
            )
        certificate = load_player_path_certificate(scenario)
        if certificate is not None:
            _write_certified_path_with_weapon_overlay(
                path,
                scenario,
                parsed,
                expected_header,
                certificate,
            )
            return
        if scenario.get("stage1_safe_base_route"):
            parsed = stage1_safe_base_route_rows(parsed, scenario)
        view_policy = scenario.get("route_view_policy")
        if not view_policy:
            validate_model_action_source_rows(parsed)
            shutil.copy2(source, path)
            return
        overlays = route_view_overlay_rows(scenario)
        action_design = scenario.get("action_design", {})
        final_rows: list[dict[str, Any]] = []
        for base, overlay in zip(parsed, overlays):
            yaw_offset = math.radians(
                float(overlay["yaw_offset"])
                + float(
                    scenario.get(
                        "stage1_locomotion_camera_offset_degrees",
                        0.0,
                    )
                )
            )
            cosine = math.cos(yaw_offset)
            sine = math.sin(yaw_offset)
            base_forward = float(base["forward"])
            base_strafe = float(base["strafe"])
            row = dict(base)
                                                                             
                                                                              
                                                                            
            row["forward"] = round(
                base_forward * cosine - base_strafe * sine, 6
            )
            row["strafe"] = round(
                base_strafe * cosine + base_forward * sine, 6
            )
            row["yaw_delta"] = round(
                float(base["yaw_delta"])
                + float(overlay["yaw_delta"]),
                6,
            )
            row["pitch_delta"] = round(
                float(base["pitch_delta"])
                + float(overlay["pitch_delta"]),
                6,
            )
            out_tick = int(base["tick"]) - WARMUP_TICKS
            primary, secondary, reload_button = (
                stage1_weapon_controls(
                    action_design,
                    str(scenario["weapon"]),
                    out_tick,
                )
            )
            row["primary"] = max(
                int(base["primary"]), primary
            )
            row["secondary"] = max(
                int(base["secondary"]), secondary
            )
            row["reload"] = max(
                int(base["reload"]), reload_button
            )
            if (
                action_design.get("jump")
                and out_tick >= 0
                and not scenario.get(
                    "stage1_preserve_certified_base_jump", False
                )
            ):
                row["jump"] = max(
                    int(base["jump"]),
                    pulse(out_tick, (48, 208), 2),
                )
            final_rows.append(row)
        validate_model_action_source_rows(final_rows)
        with path.open("w", newline="", encoding="utf-8") as handle:
            handle.write(expected_header + "\n")
            writer = csv.DictWriter(
                handle, fieldnames=ACTION_COLUMNS
            )
            writer.writeheader()
            writer.writerows(final_rows)
        return
    rows = action_rows(scenario, retry=retry)
    validate_model_action_source_rows(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"#seed,{scenario['seed']}\n")
        writer = csv.DictWriter(handle, fieldnames=ACTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


STAGE1_TEMPORAL_PROFILES = (
    "full_clip_sustained",
    "early_hold_release",
    "middle_window",
    "late_onset_hold",
    "two_pulse",
    "stop_and_go",
    "reversal",
    "eased_variable_rate",
)

STAGE1_LOCOMOTION_VECTORS = {
    "idle": (0.0, 0.0),
    "forward": (1.0, 0.0),
    "backward": (-1.0, 0.0),
    "left": (0.0, -1.0),
    "right": (0.0, 1.0),
    "forward_left": (math.sqrt(0.5), -math.sqrt(0.5)),
    "forward_right": (math.sqrt(0.5), math.sqrt(0.5)),
    "backward_left": (-math.sqrt(0.5), -math.sqrt(0.5)),
    "backward_right": (-math.sqrt(0.5), math.sqrt(0.5)),
}

STAGE1_VIEW_SIGNS = {
    "stationary": (0.0, 0.0),
    "yaw_left": (1.0, 0.0),
    "yaw_right": (-1.0, 0.0),
    "pitch_up": (0.0, -1.0),
    "pitch_down": (0.0, 1.0),
    "yaw_left_pitch_up": (1.0, -1.0),
    "yaw_left_pitch_down": (1.0, 1.0),
    "yaw_right_pitch_up": (-1.0, -1.0),
    "yaw_right_pitch_down": (-1.0, 1.0),
}

STAGE1_RELOAD_START_OUTPUT_TICK = 16
STAGE1_RELOAD_DURATION_TICKS = 2 * TICK_HZ


def stage1_weapon_controls(
    design: dict[str, Any], weapon: str, out_tick: int
) -> tuple[int, int, int]:
    if not 0 <= out_tick < OUTPUT_TICKS:
        return 0, 0, 0
    mode = str(design.get("weapon_action", "none"))
    if mode == "none":
        return 0, 0, 0
    if mode == "reload":
        return (
            0,
            0,
            pulse(
                out_tick,
                (STAGE1_RELOAD_START_OUTPUT_TICK,),
                1,
            ),
        )
    if mode == "environmental_primary":
        width = 12 if weapon == "MachineGun" else 2
        return pulse(out_tick, (64, 176, 272), width), 0, 0
    if mode != "environmental_secondary":
        raise CaptureFailure("stage1_weapon_action_unknown", mode)
    if weapon == "Devastator":
        return (
            pulse(out_tick, (64, 192), 2),
            pulse(out_tick, (96, 224), 2),
            0,
        )
    width = 32 if weapon == "Hagar" else (
        12 if weapon == "MachineGun" else 2
    )
    return 0, pulse(out_tick, (64, 176, 272), width), 0


def stage1_temporal_scalar(profile: str, out_tick: int) -> float:
    """Return the signed locomotion envelope for one visible output tick."""
    if not 0 <= out_tick < OUTPUT_TICKS:
        return 0.0
    if profile not in STAGE1_TEMPORAL_PROFILES:
        raise CaptureFailure("stage1_temporal_profile_unknown", profile)
    if profile == "full_clip_sustained":
        return 1.0
    if profile == "early_hold_release":
        return 1.0 if out_tick < 160 else 0.0
    if profile == "middle_window":
        return 1.0 if 80 <= out_tick < 240 else 0.0
    if profile == "late_onset_hold":
        return 1.0 if out_tick >= 160 else 0.0
    if profile == "two_pulse":
        return 1.0 if (
            out_tick < 80 or 192 <= out_tick < 272
        ) else 0.0
    if profile == "stop_and_go":
        return 1.0 if any(
            start <= out_tick < stop
            for start, stop in (
                (0, 64),
                (96, 160),
                (192, 256),
                (288, 320),
            )
        ) else 0.0
    if profile == "reversal":
        return 1.0 if out_tick < 160 else -1.0
    phase = (out_tick + 0.5) / OUTPUT_TICKS
    return 0.25 + 0.75 * math.sin(math.pi * phase)


def stage1_safe_base_route_rows(
    parsed: list[dict[str, Any]],
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    """Time-warp a calibrated route without skipping unsafe path segments."""
    profile = str(
        (scenario.get("action_design") or {}).get(
            "movement_profile", "full_clip_sustained"
        )
    )
    command_scale = float(
        scenario.get("stage1_route_command_scale", 1.0)
    )
    if not math.isfinite(command_scale) or not 0.0 < command_scale <= 1.0:
        raise CaptureFailure(
            "stage1_route_command_scale_invalid",
            str(command_scale),
        )
    numeric = {
        column: np.asarray(
            [float(row[column]) for row in parsed],
            dtype=np.float64,
        )
        for column in (
            "forward",
            "strafe",
            "yaw_delta",
            "pitch_delta",
        )
    }
    yaw_absolute = np.cumsum(numeric["yaw_delta"])
    pitch_absolute = np.cumsum(numeric["pitch_delta"])
    result = [dict(row) for row in parsed[:WARMUP_TICKS]]
    progress = 0.0
    previous_yaw = float(yaw_absolute[WARMUP_TICKS - 1])
    previous_pitch = float(pitch_absolute[WARMUP_TICKS - 1])

    def interpolate(values: np.ndarray, position: float) -> float:
        lower = int(math.floor(position))
        upper = min(lower + 1, OUTPUT_TICKS - 1)
        fraction = position - lower
        return float(
            values[WARMUP_TICKS + lower] * (1.0 - fraction)
            + values[WARMUP_TICKS + upper] * fraction
        )

    for out_tick in range(OUTPUT_TICKS):
        scalar = stage1_temporal_scalar(profile, out_tick)
        position = min(
            float(OUTPUT_TICKS - 1), max(0.0, progress)
        )
        source_index = WARMUP_TICKS + int(
            min(OUTPUT_TICKS - 1, math.floor(position))
        )
        base = dict(parsed[source_index])
        selected_yaw = interpolate(yaw_absolute, position)
        selected_pitch = interpolate(pitch_absolute, position)
        base.update(
            {
                "tick": WARMUP_TICKS + out_tick,
                "forward": round(
                    interpolate(numeric["forward"], position)
                    * scalar
                    * command_scale,
                    6,
                ),
                "strafe": round(
                    interpolate(numeric["strafe"], position)
                    * scalar
                    * command_scale,
                    6,
                ),
                "yaw_delta": round(
                    selected_yaw - previous_yaw, 6
                ),
                "pitch_delta": round(
                    selected_pitch - previous_pitch, 6
                ),
                "jump": (
                    int(parsed[source_index]["jump"])
                    if scalar > 0
                    else 0
                ),
                "primary": 0,
                "secondary": 0,
                "weapon_impulse": 0,
                "reload": 0,
            }
        )
        result.append(base)
        previous_yaw = selected_yaw
        previous_pitch = selected_pitch
        progress = min(
            float(OUTPUT_TICKS - 1),
            max(0.0, progress + scalar * command_scale),
        )
    if len(result) != TOTAL_TICKS:
        raise AssertionError(len(result))
    return result


def _stage1_camera_shape(profile: str) -> np.ndarray:
    """Return a deterministic unit-range camera offset trajectory."""
    if profile not in STAGE1_TEMPORAL_PROFILES:
        raise CaptureFailure("stage1_temporal_profile_unknown", profile)
    ticks = np.arange(OUTPUT_TICKS, dtype=np.float64)
    last = float(OUTPUT_TICKS - 1)
    if profile == "full_clip_sustained":
        return ticks / last
    if profile == "early_hold_release":
        return np.interp(
            ticks, [0, 80, 160, last], [0.0, 1.0, 0.0, 0.0]
        )
    if profile == "middle_window":
        return np.interp(
            ticks,
            [0, 64, 144, 224, last],
            [0.0, 0.0, 1.0, 0.0, 0.0],
        )
    if profile == "late_onset_hold":
        return np.interp(
            ticks, [0, 160, 256, last], [0.0, 0.0, 1.0, 1.0]
        )
    if profile == "two_pulse":
        return np.interp(
            ticks,
            [0, 48, 96, 176, 224, 272, last],
            [0.0, 0.5, 0.0, 0.0, -0.5, 0.0, 0.0],
        )
    if profile == "stop_and_go":
        return np.interp(
            ticks,
            [0, 48, 80, 128, 160, 208, 240, last],
            [0.0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1.0],
        )
    if profile == "reversal":
        return np.interp(
            ticks,
            [0, 96, 208, last],
            [0.0, 0.5, -0.5, 0.0],
        )
    phase = ticks / last
    return phase * phase * (3.0 - 2.0 * phase)


def stage1_camera_offsets(
    design: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    direction = str(design.get("view_direction", "stationary"))
    if direction not in STAGE1_VIEW_SIGNS:
        raise CaptureFailure("stage1_view_direction_unknown", direction)
    profile = str(
        design.get("view_profile", "full_clip_sustained")
    )
    shape = _stage1_camera_shape(profile)
    yaw_sign, pitch_sign = STAGE1_VIEW_SIGNS[direction]
    yaw = (
        shape
        * float(design.get("yaw_amplitude", 0.0))
        * yaw_sign
    )
    pitch = (
        shape
        * float(design.get("pitch_amplitude", 0.0))
        * pitch_sign
    )
    return yaw, pitch


def route_view_overlay_rows(
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return a frozen camera overlay that never reads live/enemy state."""
    policy = str(
        scenario.get("route_view_policy", "look_along_route")
    )
    supported = {
        "look_along_route",
        "scan_while_following",
        "junction_vertical_feature",
        "rapid_turn_lookback_large_pitch",
    }
    if policy not in supported:
        raise CaptureFailure("route_view_policy_unknown", policy)
    yaw_offsets = np.zeros(TOTAL_TICKS, dtype=np.float64)
    pitch_offsets = np.zeros(TOTAL_TICKS, dtype=np.float64)
    output = np.arange(OUTPUT_TICKS, dtype=np.float64)
    output_slice = slice(WARMUP_TICKS, TOTAL_TICKS)
    design = scenario.get("action_design")
    if design:
        output_yaw, output_pitch = stage1_camera_offsets(design)
        yaw_offsets[output_slice] = output_yaw
        pitch_offsets[output_slice] = output_pitch
    elif policy == "scan_while_following":
        yaw_offsets[output_slice] = 15.0 * np.sin(
            2.0 * np.pi * output / 160.0
        )
        pitch_offsets[output_slice] = 5.0 * np.sin(
            2.0 * np.pi * output / 256.0
        )
    elif policy == "junction_vertical_feature":
        yaw_offsets[output_slice] = np.interp(
            output,
            [0, 96, 224, OUTPUT_TICKS - 1],
            [0.0, 65.0, -20.0, 0.0],
        )
        pitch_offsets[output_slice] = np.interp(
            output,
            [0, 80, 200, OUTPUT_TICKS - 1],
            [0.0, -11.0, 11.0, 0.0],
        )
    elif policy == "rapid_turn_lookback_large_pitch":
        yaw_offsets[output_slice] = np.interp(
            output,
            [0, 48, 112, 240, OUTPUT_TICKS - 1],
            [0.0, 0.0, 180.0, 180.0, 0.0],
        )
        pitch_offsets[output_slice] = np.interp(
            output,
            [0, 64, 128, 224, OUTPUT_TICKS - 1],
            [0.0, -22.5, 22.5, 0.0, 0.0],
        )
    yaw_delta = np.diff(
        np.concatenate(([0.0], yaw_offsets))
    )
    pitch_delta = np.diff(
        np.concatenate(([0.0], pitch_offsets))
    )
    return [
        {
            "server_tick": tick,
            "yaw_offset": round(float(yaw_offsets[tick]), 9),
            "pitch_offset": round(float(pitch_offsets[tick]), 9),
            "yaw_delta": round(float(yaw_delta[tick]), 9),
            "pitch_delta": round(float(pitch_delta[tick]), 9),
            "reads_enemy": False,
            "policy": policy,
        }
        for tick in range(TOTAL_TICKS)
    ]


def frozen_base_actions(
    scenario: dict[str, Any],
) -> pd.DataFrame:
    source = locked_root_artifact(
        scenario["frozen_actions_path"],
        scenario.get("frozen_actions_sha256"),
        "frozen_actions",
    )
    lines = source.read_text(encoding="utf-8").splitlines()
    parsed = list(csv.DictReader(lines[1:]))
    frame = pd.DataFrame(parsed)
    for column in ACTION_COLUMNS:
        frame[column] = pd.to_numeric(frame[column])
    frame["namespace"] = "privileged_frozen_route_base_action"
    return frame


def locked_root_artifact(
    raw_path: str | os.PathLike[str],
    expected_sha256: str | None,
    label: str,
) -> Path:
    """Resolve and hash-lock a manifest artifact below the capture root."""
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve()
    root_resolved = ROOT.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise CaptureFailure(
            f"{label}_outside_capture_root", str(resolved)
        )
    if not resolved.is_file():
        raise CaptureFailure(f"{label}_missing", str(resolved))
    if not expected_sha256 or not re.fullmatch(
        r"[0-9a-f]{64}", str(expected_sha256)
    ):
        raise CaptureFailure(f"{label}_sha256_missing", str(resolved))
    actual = sha256_file(resolved)
    if actual != expected_sha256:
        raise CaptureFailure(
            f"{label}_sha256_mismatch",
            f"expected={expected_sha256} actual={actual} path={resolved}",
        )
    return resolved


def command_generate(_: argparse.Namespace) -> int:
    require_conda()
    validate_fixed_assets()
    verify_anchor_catalog()
    scenarios = generate_scenarios()
    scenarios_path = ROOT / "configs/pilot_scenarios.jsonl"
    coverage_path = ROOT / "configs/pilot_coverage.csv"
    actions_dir = ROOT / "configs/actions"
    scenarios_path.parent.mkdir(parents=True, exist_ok=True)
    with scenarios_path.open("w", encoding="utf-8") as handle:
        for scenario in scenarios:
            handle.write(canonical_json(scenario) + "\n")
    coverage_rows = [
        {
            "episode_id": row["episode_id"],
            "split": row["split"],
            "target_bin": row["target_bin"],
            "target_ordinal": row["target_ordinal"],
            "map": row["map"],
            "anchor_id": row["anchor_id"],
            "player_origin": canonical_json(row["player"]["origin"]),
            "enemy_origin": canonical_json(row["enemy"]["origin"]),
            "enemy_model": row["enemy_model"],
            "weapon": row["weapon"],
            "intent_outcome": row["intent_outcome"],
            "seed": row["seed"],
        }
        for row in scenarios
    ]
    pd.DataFrame(coverage_rows).to_csv(coverage_path, index=False)
    for scenario in scenarios:
        write_action_csv(actions_dir / f"{scenario['episode_id']}.csv", scenario)
    print(f"scenarios={scenarios_path}")
    print(f"coverage={coverage_path}")
    print(f"actions={actions_dir}")
    print(f"count={len(scenarios)}")
    print(f"distribution={dict(Counter(row['target_bin'] for row in scenarios))}")
    return 0


def command_base(binary: Path, userdir: Path) -> list[str]:
    return [
        str(binary),
        "-xonotic",
        "-nocdaudio",
        "-basedir",
        str(BASEDIR),
        "-userdir",
        str(userdir),
    ]


def cvar_args(values: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for name, value in values.items():
        args.extend([f"+{name}", str(value)])
    return args


def cvar_set_args(values: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for name, value in values.items():
        args.extend(["+set", name, str(value)])
    return args


def process_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "SDL_VIDEODRIVER": "offscreen",
            "SDL_AUDIODRIVER": "dummy",
            "SDL_RENDER_DRIVER": "opengl",
            "LC_ALL": "C",
        }
    )
    return env


def run_logged_process(
    command: list[str],
    log_path: Path,
    timeout_seconds: float,
    env: dict[str, str] | None = None,
    abort_log_patterns: tuple[bytes, ...] = (),
    progress_watchdog: tuple[bytes, bytes, float] | None = None,
) -> ProcessResult:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    abort_pattern: str | None = None
    terminated_returncode: int | None = None
    with log_path.open("wb") as log_handle:
        log_handle.write(
            (
                f"started_utc={utc_now()}\n"
                f"command={json.dumps(command, ensure_ascii=False)}\n"
            ).encode()
        )
        log_handle.flush()
        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

        def terminate_process_group() -> int:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                return process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return process.wait(timeout=10)

        deadline = started + timeout_seconds
        scan_offset = 0
        scan_tail = b""
        watchdog_trigger = (
            progress_watchdog[0] if progress_watchdog else None
        )
        watchdog_progress = (
            progress_watchdog[1] if progress_watchdog else None
        )
        watchdog_grace = (
            float(progress_watchdog[2]) if progress_watchdog else None
        )
        if watchdog_grace is not None and watchdog_grace <= 0:
            raise ValueError("progress watchdog grace must be positive")
        scan_patterns = abort_log_patterns + tuple(
            pattern
            for pattern in (watchdog_trigger, watchdog_progress)
            if pattern is not None
        )
        maximum_pattern = max(
            (len(row) for row in scan_patterns), default=0
        )
        watchdog_triggered_at: float | None = None
        watchdog_completed = False
        returncode: int
        while True:
            polled = process.poll()
            if polled is not None:
                returncode = polled
                break
            now = time.monotonic()
            if now >= deadline:
                timed_out = True
                terminated_returncode = terminate_process_group()
                returncode = 124
                log_handle.write(
                    (
                        f"timeout_seconds={timeout_seconds}\n"
                        f"terminated_returncode={terminated_returncode}\n"
                    ).encode()
                )
                break
            if scan_patterns:
                with log_path.open("rb") as scan_handle:
                    scan_handle.seek(scan_offset)
                    chunk = scan_handle.read()
                scan_offset += len(chunk)
                searchable = scan_tail + chunk
                if (
                    watchdog_progress is not None
                    and watchdog_progress in searchable
                ):
                    watchdog_completed = True
                if (
                    not watchdog_completed
                    and watchdog_triggered_at is None
                    and watchdog_trigger is not None
                    and watchdog_trigger in searchable
                ):
                    watchdog_triggered_at = now
                matched = next(
                    (
                        pattern
                        for pattern in abort_log_patterns
                        if pattern in searchable
                    ),
                    None,
                )
                if matched is not None:
                    abort_pattern = matched.decode(errors="replace").strip()
                    terminated_returncode = terminate_process_group()
                    returncode = 125
                    log_handle.write(
                        (
                            f"abort_pattern={json.dumps(abort_pattern)}\n"
                            f"terminated_returncode={terminated_returncode}\n"
                        ).encode()
                    )
                    break
                if (
                    not watchdog_completed
                    and watchdog_triggered_at is not None
                    and watchdog_grace is not None
                    and now - watchdog_triggered_at >= watchdog_grace
                ):
                    abort_pattern = (
                        "progress_watchdog_stalled:"
                        f"trigger={watchdog_trigger!r}:"
                        f"progress={watchdog_progress!r}:"
                        f"grace_seconds={watchdog_grace}"
                    )
                    terminated_returncode = terminate_process_group()
                    returncode = 126
                    log_handle.write(
                        (
                            f"abort_pattern={json.dumps(abort_pattern)}\n"
                            f"terminated_returncode="
                            f"{terminated_returncode}\n"
                        ).encode()
                    )
                    break
                if maximum_pattern > 1:
                    scan_tail = searchable[-(maximum_pattern - 1) :]
            time.sleep(min(0.1, max(0.0, deadline - now)))

        if timed_out:
                                                                           
                                                                           
                                               
            assert returncode == 124
        wall_seconds = time.monotonic() - started
        log_handle.write(
            (
                f"timed_out={str(timed_out).lower()}\n"
                f"aborted={str(abort_pattern is not None).lower()}\n"
                f"returncode={returncode}\n"
                f"wall_seconds={wall_seconds:.6f}\n"
                f"finished_utc={utc_now()}\n"
            ).encode()
        )
    return ProcessResult(
        command,
        returncode,
        wall_seconds,
        log_path,
        timed_out=timed_out,
        abort_pattern=abort_pattern,
    )


def prepare_userdirs(stage: Path, build: Path) -> tuple[Path, Path]:
    server_user = stage / "server_user"
    client_user = stage / "client_user"
    for userdir in (server_user, client_user):
        data = userdir / "data"
        (data / "capture").mkdir(parents=True, exist_ok=True)
        (data / "data/capture").mkdir(parents=True, exist_ok=True)
        (data / "demos").mkdir(parents=True, exist_ok=True)
        (data / "video").mkdir(parents=True, exist_ok=True)
        for qc_name in ("progs.dat", "csprogs.dat", "menu.dat"):
            shutil.copy2(build / "qc" / qc_name, data / qc_name)
    shutil.copy2(
        ROOT / "configs/capture_server.cfg",
        server_user / "data/capture_server.cfg",
    )
    shutil.copy2(
        ROOT / "configs/capture_client.cfg",
        client_user / "data/capture_client.cfg",
    )
    client_overlay = os.environ.get(
        "XONOTIC_CAPTURE_CLIENT_OVERLAY", ""
    ).strip()
    if client_overlay:
        overlay_path = Path(client_overlay)
        if not overlay_path.is_absolute():
            overlay_path = ROOT / overlay_path
        if not overlay_path.is_file():
            raise CaptureFailure(
                "capture_client_overlay_missing", str(overlay_path)
            )
        with (
            overlay_path.open("rb") as source,
            (client_user / "data/capture_client.cfg").open("ab") as target,
        ):
            target.write(b"\n")
            shutil.copyfileobj(source, target)
    return server_user, client_user


def choose_port(preferred: int | None = None) -> int:
    if preferred is not None:
        if preferred < 1024 or preferred > 65535:
            raise CaptureFailure("invalid_capture_port", str(preferred))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            try:
                sock.bind(("127.0.0.1", preferred))
            except OSError as exc:
                raise CaptureFailure(
                    "capture_port_unavailable",
                    f"port={preferred} error={exc}",
                ) from exc
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(log_path: Path, process: subprocess.Popen[Any]) -> None:
    deadline = time.monotonic() + 30
    patterns = ("Server listening", "Server: ", "IP address", "Loaded maps/")
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise CaptureFailure(
                "dedicated_start_failed", f"returncode={process.returncode}"
            )
        if log_path.exists():
            text = log_path.read_text(errors="replace")
            if any(pattern in text for pattern in patterns):
                return
        time.sleep(0.1)
    raise CaptureFailure("dedicated_health_timeout", str(log_path))


def server_cvars(scenario: dict[str, Any], port: int) -> dict[str, Any]:
    player = scenario["player"]
    enemy_present = bool(scenario.get("enemy_present", True))
    enemy = scenario.get("enemy") or {}
    enemy_policy = scenario.get("enemy_policy") or {}
    legacy_policy_names = {
        0: "idle",
        1: "lateral_patrol",
        2: "approach_retreat",
        3: "stop_and_go",
    }
    enemy_motion = int(enemy.get("motion", 0))
    enemy_audio_mode = enemy_policy.get(
        "movement_audio", ENEMY_MOVEMENT_AUDIO_MODE
    )
    enemy_audio_enabled = (
        enemy_present
        and enemy_motion != 0
        and enemy_audio_mode == ENEMY_MOVEMENT_AUDIO_MODE
    )
    route_plan = scenario.get("route_plan") or {}
    route_enabled = bool(route_plan)
    vector = lambda values: " ".join(str(value) for value in values)
    return {
        "exec": "capture_server.cfg",
        "port": port,
        "capture_server_enable": 1,
        "capture_episode_id": scenario["episode_id"],
        "capture_anchor_id": scenario["anchor_id"],
        "capture_server_log": "capture/server.jsonl",
        "capture_server_action_file": "capture/actions.csv",
        "capture_route_enable": int(route_enabled),
        "capture_route_calibration": int(
            route_enabled
            and bool(scenario.get("capture_route_calibration", False))
        ),
        "capture_route_file": "capture/route.csv",
        "capture_enemy_present": int(enemy_present),
        "capture_player_origin": vector(player["origin"]),
        "capture_enemy_origin": vector(enemy.get("origin", [0, 0, 0])),
        "capture_enemy_motion_vector": vector(
            enemy.get("motion_vector", [0, 0, 0])
        ),
        "capture_player_pitch": player.get("pitch", 0),
        "capture_player_yaw": player["yaw"],
        "capture_enemy_yaw": enemy.get("yaw", 0),
        "capture_enemy_motion": enemy_motion,
        "capture_enemy_motion_distance": enemy.get("motion_distance", 0),
        "capture_enemy_motion_start_tick": int(
            enemy.get(
                "motion_start_tick",
                enemy_policy.get("motion_start_tick", 0),
            )
        ),
        "capture_enemy_policy": enemy_policy.get(
            "name", legacy_policy_names.get(enemy_motion, "unknown")
        ),
        "capture_enemy_policy_seed": int(
            enemy_policy.get("policy_seed", scenario["seed"])
        ),
        "capture_enemy_movement_audio": int(enemy_audio_enabled),
        "capture_enemy_step_stride": float(
            enemy_policy.get(
                "step_stride_units", ENEMY_STEP_STRIDE_UNITS
            )
        ),
        "capture_enemy_model": scenario.get("enemy_model", ""),
        "capture_enemy_skin": int(scenario.get("enemy_skin", 0)),
        "capture_enemy_color": int(scenario.get("enemy_color", 0)),
        "capture_weapon": scenario["weapon_netname"],
        "capture_player_health": player["health"],
        "capture_player_armor": player["armor"],
        "capture_enemy_health": enemy.get("health", 0),
        "capture_enemy_armor": enemy.get("armor", 0),
        "capture_clip": player["clip"],
        "capture_reserve": player["reserve"],
        "map": scenario["map"],
    }


def write_server_episode_config(
    path: Path,
    values: dict[str, Any],
    expected_gametype: str,
) -> None:
    mode_cvar = GAMETYPE_CVARS.get(expected_gametype.lower())
    if mode_cvar is None:
        raise CaptureFailure(
            "unsupported_capture_gametype", expected_gametype
        )
    lines = [
        "// Generated per-attempt after-map capture configuration.",
        "capture_server_enable 0",
    ]
    for name, raw_value in values.items():
        if not name.startswith("capture_") or name == "capture_server_enable":
            continue
        value = str(raw_value).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{name} "{value}"')
    lines += [
        "capture_server_enable 1",
        "capture_server_enable",
        "capture_episode_id",
        "capture_server_action_file",
        "gamecfg",
        mode_cvar,
        "g_ctf_flag_waypoint",
        "cl_maxphysicsframesperserverframe",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_server_mode_config(path: Path, gametype: str) -> str:
    normalized = gametype.lower()
    selected_cvar = GAMETYPE_CVARS.get(normalized)
    if selected_cvar is None:
        raise CaptureFailure(
            "unsupported_capture_gametype", gametype
        )
    lines = [
        "// Generated pre-map mutually exclusive gametype configuration.",
        f'set gamecfg "{normalized}"',
    ]
    lines.extend(
        f"set {cvar} {int(cvar == selected_cvar)}"
        for cvar in GAMETYPE_CVARS.values()
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return selected_cvar


def run_live_attempt(
    stage: Path,
    scenario: dict[str, Any],
    build: Path,
    retry: int,
    port: int | None = None,
) -> dict[str, Any]:
    engine_net_timeout = configured_engine_net_timeout_seconds()
    server_user, client_user = prepare_userdirs(stage, build)
    live_dir = stage / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    action_path = stage / "actions_requested.csv"
    write_action_csv(action_path, scenario, retry=retry)
    shutil.copy2(action_path, server_user / "data/capture/actions.csv")
    route_source: Path | None = None
    route_plan = scenario.get("route_plan") or {}
    if route_plan:
        route_source = locked_root_artifact(
            route_plan.get("route_csv_path", ""),
            route_plan.get("route_csv_sha256"),
            "route_csv",
        )
        shutil.copy2(
            route_source, server_user / "data/capture/route.csv"
        )
    port = choose_port(port)
    server_log = stage / "server_console.log"
    client_log = stage / "client_live_console.log"
    dedicated = build / "bin/xonotic-local-dedicated"
    client = build / "bin/xonotic-local-sdl"
    values = server_cvars(scenario, port)
    exec_name = str(values.pop("exec"))
    map_name = str(values.pop("map"))
    expected_gametype = str(scenario.get("gametype", "dm")).lower()
    mode_cvar = write_server_mode_config(
        server_user / "data/capture_mode.cfg",
        expected_gametype,
    )
    write_server_episode_config(
        server_user / "data/capture_episode.cfg",
        values,
        expected_gametype,
    )
    server_command = (
        command_base(dedicated, server_user)
        + ["+exec", exec_name]
        + ["+exec", "capture_mode.cfg"]
        + cvar_set_args(
            {
                "net_connecttimeout": engine_net_timeout,
                "net_messagetimeout": engine_net_timeout,
            }
        )
        + ["+set", "port", str(port)]
        + ["+set", "sv_random_seed", str(scenario["seed"])]
        + [
            "+set",
            "bot_number",
            "1",
        ]
        + ["+map", map_name]
        + ["+exec", "capture_episode.cfg"]
    )
    server_handle = server_log.open("wb")
    server_handle.write(
        (
            f"started_utc={utc_now()}\n"
            f"command={json.dumps(server_command, ensure_ascii=False)}\n"
        ).encode()
    )
    server_handle.flush()
    server = subprocess.Popen(
        server_command,
        stdin=subprocess.PIPE,
        stdout=server_handle,
        stderr=subprocess.STDOUT,
        env=process_environment(),
        start_new_session=True,
    )
    try:
        wait_for_server(server_log, server)
        client_values = {
            "exec": "capture_client.cfg",
                                                                          
                                                                          
                                                                          
                                                                          
            "net_connecttimeout": engine_net_timeout,
            "net_messagetimeout": engine_net_timeout,
                                                                       
                                                                       
                                                     
            "cl_maxfps": 128,
            "cl_netfps": 64,
            "cl_damagetext": 0,
            "capture_enable": 1,
            "capture_mode": 0,
            "capture_action_file": action_path,
            "capture_log_dir": live_dir,
            "capture_initial_yaw": scenario["player"]["yaw"],
            "capture_initial_pitch": scenario["player"].get("pitch", 0),
            "capture_expected_frames": OUTPUT_TICKS,
            "capture_quit_on_end": 1,
            "cl_capturevideo_nameformat": f"{scenario['episode_id']}_",
            "record": f"demos/{scenario['episode_id']}",
            "connect": f"127.0.0.1:{port}",
        }
        client_command = (
            command_base(client, client_user)
            + ["-window", "-width", str(WIDTH), "-height", str(HEIGHT)]
            + ["-sndspeed", str(AUDIO_RATE), "-sndbits", "16", "-sndstereo"]
            + cvar_args(client_values)
        )
        client_result = run_logged_process(
            client_command,
            client_log,
            timeout_seconds=configured_live_timeout_seconds(),
            env=process_environment(),
            abort_log_patterns=(b"Connection timed out\n",),
        )
        if client_result.returncode != 0:
            raise CaptureFailure(
                "live_client_failed", f"returncode={client_result.returncode}"
            )
    finally:
        if server.poll() is None and server.stdin:
            try:
                server.stdin.write(b"quit\n")
                server.stdin.flush()
                server.wait(timeout=10)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                if server.poll() is None:
                    os.killpg(server.pid, signal.SIGTERM)
                    try:
                        server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(server.pid, signal.SIGKILL)
                        server.wait(timeout=5)
        server_handle.write(
            (
                f"returncode={server.returncode}\n"
                f"finished_utc={utc_now()}\n"
            ).encode()
        )
        server_handle.close()
    server_console = server_log.read_text(errors="replace")
    realized_gametype = validate_realized_gametype(
        server_console,
        expected_gametype,
        server_log,
    )
    active_mode = logged_cvar_value(server_console, mode_cvar)
    if active_mode != "1":
        raise CaptureFailure(
            "realized_gametype_cvar_inactive",
            f"gametype={expected_gametype} {mode_cvar}={active_mode!r} "
            f"log={server_log}",
        )
    flag_waypoint = logged_cvar_value(
        server_console, "g_ctf_flag_waypoint"
    )
    if flag_waypoint != "0":
        raise CaptureFailure(
            "server_objective_waypoint_policy_failed",
            f"g_ctf_flag_waypoint={flag_waypoint!r} log={server_log}",
        )
    max_physics_frames = logged_cvar_value(
        server_console, "cl_maxphysicsframesperserverframe"
    )
    if max_physics_frames != str(
        SERVER_MAX_PHYSICS_FRAMES_PER_HOST_FRAME
    ):
        raise CaptureFailure(
            "server_snapshot_tick_delivery_policy_failed",
            "cl_maxphysicsframesperserverframe="
            f"{max_physics_frames!r} log={server_log}",
        )
    demo_path = client_user / "data/demos" / f"{scenario['episode_id']}.dem"
    telemetry_path = server_user / "data/data/capture/server.jsonl"
    actions_engine = live_dir / "actions_engine.csv"
    for required in (demo_path, telemetry_path, actions_engine):
        if not required.is_file() or required.stat().st_size == 0:
            raise CaptureFailure("live_artifact_missing", str(required))
    console = client_log.read_text(errors="replace")
    if "loaded 384 actions" not in console:
        raise CaptureFailure("action_schedule_not_loaded", str(client_log))
    if "Completed demo" not in console:
        raise CaptureFailure("demo_not_completed", str(client_log))
    return {
        "server_user": server_user,
        "client_user": client_user,
        "demo_path": demo_path,
        "server_telemetry": telemetry_path,
        "actions_engine": actions_engine,
        "live_wall_seconds": client_result.wall_seconds,
        "port": port,
        "realized_gametype": realized_gametype,
        "realized_gametype_cvar": mode_cvar,
        "realized_gametype_cvar_value": int(active_mode),
        "g_ctf_flag_waypoint": int(flag_waypoint),
        "server_max_physics_frames_per_host_frame": int(
            max_physics_frames
        ),
        "route_source": str(route_source) if route_source else None,
    }


def run_render_attempt(
    stage: Path,
    scenario: dict[str, Any],
    build: Path,
    client_user: Path,
) -> dict[str, Any]:
    render_dir = stage / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    video_dir = client_user / "data/video"
    for old in video_dir.glob("*.avi"):
        old.unlink()
    client = build / "bin/xonotic-local-sdl"
    values = {
        "exec": "capture_client.cfg",
                                                                        
                                                                        
                                                                
        "cl_maxfps": 64,
        "cl_damagetext": 0,
        "capture_enable": 1,
        "capture_mode": 1,
        "capture_demo_fixedstep": RENDER_DEMO_PREROLL_FIXEDSTEP,
        "capture_log_dir": render_dir,
        "capture_expected_frames": OUTPUT_TICKS,
        "capture_quit_on_end": 1,
        "cl_capturevideo_nameformat": f"{scenario['episode_id']}_",
        "playdemo": f"demos/{scenario['episode_id']}",
    }
    command = (
        command_base(client, client_user)
        + ["-window", "-width", str(WIDTH), "-height", str(HEIGHT)]
        + ["-sndspeed", str(AUDIO_RATE), "-sndbits", "16", "-sndstereo"]
        + cvar_args(values)
    )
    render_timeout_seconds = configured_render_timeout_seconds()
    render_startup_stall_seconds = (
        configured_render_startup_stall_seconds()
    )
    result = run_logged_process(
        command,
        stage / "client_render_console.log",
        timeout_seconds=render_timeout_seconds,
        env=process_environment(),
        progress_watchdog=(
            b" connected",
            b"capture: output begin",
            render_startup_stall_seconds,
        ),
    )
    if result.returncode != 0:
        raise CaptureFailure(
            "offline_render_failed", f"returncode={result.returncode}"
        )
    avis = sorted(video_dir.glob(f"{scenario['episode_id']}_*.avi"))
    if len(avis) != 1:
        raise CaptureFailure(
            "raw_video_count", f"expected=1 actual={len(avis)} path={video_dir}"
        )
    for required in (
        render_dir / "frames_engine.csv",
        render_dir / "audio_events_engine.csv",
    ):
        if not required.is_file() or required.stat().st_size == 0:
            raise CaptureFailure("render_artifact_missing", str(required))
    console = result.log_path.read_text(errors="replace")
    renderer_match = re.search(r"GL_RENDERER:?\s*(.+)", console)
    renderer = renderer_match.group(1).strip() if renderer_match else ""
    if not is_nvidia_hardware_renderer(renderer, console):
        raise CaptureFailure("hardware_renderer_gate", renderer or "not logged")
    if HUD_POLICY_LINE not in console:
        raise CaptureFailure(
            "minimal_hud_policy_failed",
            f"expected={HUD_POLICY_LINE!r} log={result.log_path}",
        )
    fixedstep_marker = (
        f"capture: episode reset id={scenario['episode_id']} "
        "mode=1 demo=1 demo_fixedstep=1"
    )
    if fixedstep_marker not in console:
        raise CaptureFailure(
            "render_demo_preroll_fixedstep_failed",
            f"expected={fixedstep_marker!r} log={result.log_path}",
        )
    return {
        "raw_avi": avis[0],
        "frames_engine": render_dir / "frames_engine.csv",
        "audio_events_engine": render_dir / "audio_events_engine.csv",
        "render_wall_seconds": result.wall_seconds,
        "render_timeout_seconds": render_timeout_seconds,
        "render_startup_stall_seconds": (
            render_startup_stall_seconds
        ),
        "renderer": renderer,
        "hud_policy": HUD_POLICY_LINE,
        "demo_preroll_fixedstep": RENDER_DEMO_PREROLL_FIXEDSTEP,
    }


def ffprobe_json(path: Path, count_frames: bool = False) -> dict[str, Any]:
    command = ["ffprobe", "-v", "error"]
    if count_frames:
        command.append("-count_frames")
    command += ["-show_streams", "-show_format", "-of", "json", str(path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise CaptureFailure("ffprobe_failed", completed.stderr.strip())
    return json.loads(completed.stdout)


def decode_audio_s16(path: Path) -> np.ndarray:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(AUDIO_RATE),
        "-ac",
        "2",
        "-",
    ]
    completed = subprocess.run(command, capture_output=True, check=False)
    if completed.returncode != 0:
        raise CaptureFailure(
            "audio_decode_failed", completed.stderr.decode(errors="replace")
        )
    samples = np.frombuffer(completed.stdout, dtype="<i2")
    if samples.size % 2:
        raise CaptureFailure("audio_interleave_invalid", str(samples.size))
    return samples.reshape((-1, 2))


def count_video_frames(probe: dict[str, Any]) -> int:
    streams = probe.get("streams", [])
    video = next((row for row in streams if row.get("codec_type") == "video"), None)
    if not video:
        raise CaptureFailure("video_stream_missing")
    value = video.get("nb_read_frames") or video.get("nb_frames")
    if value in (None, "N/A"):
        raise CaptureFailure("video_frame_count_unavailable")
    return int(value)


def parse_server_telemetry(
    path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    rows = load_jsonl(path)
    states = [row for row in rows if row.get("kind") == "state"]
    events = [row for row in rows if row.get("kind") == "event"]
    fatals = [row for row in rows if row.get("kind") == "fatal"]
    if fatals:
        raise CaptureFailure("server_telemetry_fatal", canonical_json(fatals[0]))
    return pd.json_normalize(states), pd.json_normalize(events), rows


def enemy_path_trace_metrics(
    server_rows: list[dict[str, Any]],
    states: pd.DataFrame,
    events: pd.DataFrame,
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Validate the exogenous target path until player-caused interaction.

    Damage, knockback, and death are intended endogenous Stage-2 outcomes.
    Once a linked player-to-target damage event occurs, realized enemy state
    may diverge from the no-interaction analytic trajectory.  The declared
    trajectory itself must remain structurally safe for all ticks, and every
    realized deviation before the first such damage remains a hard failure.
    """
    enemy_present = bool(scenario.get("enemy_present", True))
    rows = [
        row for row in server_rows
        if row.get("kind") == "enemy_path_trace"
    ]
    expected_ticks = (
        list(range(1, TOTAL_TICKS)) if enemy_present else []
    )
    expected_count = len(expected_ticks)
    ticks: list[int] = []
    failed_ticks: list[int] = []
    structural_failed_ticks: list[int] = []
    pre_interaction_mismatch_ticks: list[int] = []
    endogenous_deviation_ticks: list[int] = []
    malformed_ticks: list[int] = []
    max_target_state_error = 0.0
    max_pre_interaction_target_state_error = 0.0
    max_post_interaction_target_state_error = 0.0
    reset_rows = [
        row for row in server_rows if row.get("kind") == "reset"
    ]
    reset = reset_rows[0] if len(reset_rows) == 1 else {}
    player_entity = int(reset.get("player_entity", -1))
    enemy_entity = int(reset.get("enemy_entity", -2))
    damage_ticks: list[int] = []
    if (
        enemy_present
        and not events.empty
        and "event" in events
        and "server_tick" in events
    ):
        damage = events[events["event"] == "damage"]
        for _, event in damage.iterrows():
            target = event.get("target")
            attacker = event.get("attacker")
            if (
                pd.notna(target)
                and pd.notna(attacker)
                and int(target) == enemy_entity
                and int(attacker) == player_entity
            ):
                damage_ticks.append(int(event["server_tick"]))
    first_player_damage_tick = (
        min(damage_ticks) if damage_ticks else None
    )
    states_by_tick: dict[int, np.ndarray] = {}
    if enemy_present and not states.empty and "server_tick" in states:
        for _, state in states.iterrows():
            origin = state.get("enemy.origin")
            if origin is None:
                continue
            try:
                values = np.asarray(origin, dtype=np.float64)
            except (TypeError, ValueError):
                continue
            if values.shape == (3,) and np.isfinite(values).all():
                states_by_tick[int(state["server_tick"])] = values

    for row in rows:
        tick = int(row.get("server_tick", -1))
        ticks.append(tick)
        sweep = row.get("sweep")
        ground = row.get("ground")
        target = row.get("target")
        try:
            target_values = np.asarray(target, dtype=np.float64)
            sweep_normal = np.asarray(
                sweep.get("surface_normal"), dtype=np.float64
            )
            ground_normal = np.asarray(
                ground.get("surface_normal"), dtype=np.float64
            )
            schema_valid = (
                isinstance(sweep, dict)
                and isinstance(ground, dict)
                and target_values.shape == (3,)
                and sweep_normal.shape == (3,)
                and ground_normal.shape == (3,)
                and np.isfinite(target_values).all()
                and np.isfinite(sweep_normal).all()
                and np.isfinite(ground_normal).all()
                and "contact_entity" in sweep
                and "contact_point" in sweep
                and "surface_flags" in sweep
                and "contact_entity" in ground
                and "contact_point" in ground
                and "surface_flags" in ground
            )
        except (AttributeError, TypeError, ValueError):
            schema_valid = False
            target_values = np.full(3, np.nan)
            ground_normal = np.full(3, np.nan)
        if not schema_valid:
            malformed_ticks.append(tick)
            structural_failed_ticks.append(tick)
            failed_ticks.append(tick)
            continue
        sweep_clear = (
            not bool(sweep.get("startsolid"))
            and not bool(sweep.get("allsolid"))
            and float(sweep.get("fraction", -1))
            >= ENEMY_PATH_TRACE_FRACTION_MIN
        )
        ground_safe = (
            not bool(ground.get("startsolid"))
            and not bool(ground.get("allsolid"))
            and 0 <= float(ground.get("fraction", -1)) < 1
            and float(ground_normal[2])
            >= ENEMY_PATH_GROUND_NORMAL_Z_MIN
            and -1
            <= float(ground.get("distance", math.inf))
            <= ENEMY_PATH_GROUND_DISTANCE_MAX
        )
        structural_trace_passed = (
            bool(row.get("passed"))
            and sweep_clear
            and ground_safe
            and not bool(row.get("trigger_hurt"))
        )
        state_origin = states_by_tick.get(tick)
        if state_origin is None:
            target_state_error = math.inf
        else:
            target_state_error = float(
                np.linalg.norm(target_values - state_origin)
            )
            max_target_state_error = max(
                max_target_state_error, target_state_error
            )
        state_matches = target_state_error <= 1e-5
        post_interaction = (
            first_player_damage_tick is not None
            and tick >= first_player_damage_tick
        )
        if post_interaction:
            if math.isfinite(target_state_error):
                max_post_interaction_target_state_error = max(
                    max_post_interaction_target_state_error,
                    target_state_error,
                )
            if not state_matches:
                endogenous_deviation_ticks.append(tick)
        else:
            if math.isfinite(target_state_error):
                max_pre_interaction_target_state_error = max(
                    max_pre_interaction_target_state_error,
                    target_state_error,
                )
            if not state_matches:
                pre_interaction_mismatch_ticks.append(tick)
        trace_passed = (
            structural_trace_passed
            and (state_matches or post_interaction)
        )
        if not structural_trace_passed:
            structural_failed_ticks.append(tick)
        if not trace_passed:
            failed_ticks.append(tick)

    exact_ticks = ticks == expected_ticks
    passed = (
        len(rows) == expected_count
        and exact_ticks
        and not failed_ticks
        and not malformed_ticks
    )
    return {
        "expected": enemy_present,
        "expected_rows": expected_count,
        "rows": len(rows),
        "exact_tick_span": exact_ticks,
        "failed_tick_count": len(set(failed_ticks)),
        "failed_ticks": sorted(set(failed_ticks))[:32],
        "structural_failed_tick_count": len(
            set(structural_failed_ticks)
        ),
        "structural_failed_ticks": sorted(
            set(structural_failed_ticks)
        )[:32],
        "pre_interaction_mismatch_tick_count": len(
            set(pre_interaction_mismatch_ticks)
        ),
        "pre_interaction_mismatch_ticks": sorted(
            set(pre_interaction_mismatch_ticks)
        )[:32],
        "endogenous_deviation_tick_count": len(
            set(endogenous_deviation_ticks)
        ),
        "endogenous_deviation_ticks": sorted(
            set(endogenous_deviation_ticks)
        )[:32],
        "first_player_damage_tick": first_player_damage_tick,
        "player_damage_event_count": len(damage_ticks),
        "malformed_tick_count": len(set(malformed_ticks)),
        "max_target_state_error": (
            max_target_state_error if enemy_present else 0.0
        ),
        "max_pre_interaction_target_state_error": (
            max_pre_interaction_target_state_error
            if enemy_present
            else 0.0
        ),
        "max_post_interaction_target_state_error": (
            max_post_interaction_target_state_error
            if enemy_present
            else 0.0
        ),
        "post_damage_state_divergence_is_endogenous": True,
        "sweep_fraction_min": ENEMY_PATH_TRACE_FRACTION_MIN,
        "ground_normal_z_min": ENEMY_PATH_GROUND_NORMAL_Z_MIN,
        "ground_distance_max": ENEMY_PATH_GROUND_DISTANCE_MAX,
        "passed": passed,
    }


def player_path_certificate_metrics(
    states: pd.DataFrame,
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Compare a formal replay with its immutable certified physical path."""
    if not scenario.get("player_path_certificate"):
        return {
            "expected": False,
            "passed": True,
            "reference_kind": None,
        }
    certificate = load_player_path_certificate(scenario)
    if certificate is None:
        raise AssertionError("certificate reference disappeared")
    reference_path = locked_root_artifact(
        certificate["states_path"],
        certificate["states_sha256"],
        "player_path_certificate_states",
    )
    reference = pd.read_parquet(reference_path).sort_values(
        "server_tick"
    )
    observed = states.sort_values("server_tick")
    expected_ticks = list(range(TOTAL_TICKS))
    ticks_exact = (
        len(reference) == TOTAL_TICKS
        and len(observed) == TOTAL_TICKS
        and list(pd.to_numeric(reference["server_tick"]))
        == expected_ticks
        and list(pd.to_numeric(observed["server_tick"]))
        == expected_ticks
    )
    origin_max_error = velocity_max_error = math.inf
    yaw_max_error = pitch_max_error = math.inf
    health_max_error = math.inf
    jump_exact = ground_exact = False
    if ticks_exact:
        expected_origins = np.stack(
            reference["post.origin"].map(
                lambda value: np.asarray(value, dtype=np.float64)
            )
        )
        observed_origins = np.stack(
            observed["post.origin"].map(
                lambda value: np.asarray(value, dtype=np.float64)
            )
        )
        expected_velocities = np.stack(
            reference["post.velocity"].map(
                lambda value: np.asarray(value, dtype=np.float64)
            )
        )
        observed_velocities = np.stack(
            observed["post.velocity"].map(
                lambda value: np.asarray(value, dtype=np.float64)
            )
        )
        origin_max_error = float(
            np.linalg.norm(
                expected_origins - observed_origins, axis=1
            ).max()
        )
        velocity_max_error = float(
            np.linalg.norm(
                expected_velocities - observed_velocities, axis=1
            ).max()
        )
        expected_yaw = pd.to_numeric(
            reference["applied_action.yaw"], errors="raise"
        ).to_numpy(dtype=np.float64)
        observed_yaw = pd.to_numeric(
            observed["applied_action.yaw"], errors="raise"
        ).to_numpy(dtype=np.float64)
        yaw_errors = np.abs(
            (expected_yaw - observed_yaw + 180.0) % 360.0
            - 180.0
        )
        yaw_max_error = float(yaw_errors.max())
        expected_pitch = pd.to_numeric(
            reference["applied_action.pitch"], errors="raise"
        ).to_numpy(dtype=np.float64)
        observed_pitch = pd.to_numeric(
            observed["applied_action.pitch"], errors="raise"
        ).to_numpy(dtype=np.float64)
        pitch_max_error = float(
            np.abs(expected_pitch - observed_pitch).max()
        )
        expected_health = pd.to_numeric(
            reference["post.health"], errors="raise"
        ).to_numpy(dtype=np.float64)
        observed_health = pd.to_numeric(
            observed["post.health"], errors="raise"
        ).to_numpy(dtype=np.float64)
        health_max_error = float(
            np.abs(expected_health - observed_health).max()
        )
        jump_exact = bool(
            np.array_equal(
                pd.to_numeric(
                    reference["applied_action.jump"], errors="raise"
                ).to_numpy(dtype=np.int8),
                pd.to_numeric(
                    observed["applied_action.jump"], errors="raise"
                ).to_numpy(dtype=np.int8),
            )
        )
        ground_exact = bool(
            np.array_equal(
                pd.to_numeric(
                    reference["post.onground"], errors="raise"
                ).to_numpy(dtype=np.int8),
                pd.to_numeric(
                    observed["post.onground"], errors="raise"
                ).to_numpy(dtype=np.int8),
            )
        )
    checks = {
        "ticks_exact": ticks_exact,
        "origin_match": (
            origin_max_error <= PLAYER_PATH_ORIGIN_TOLERANCE
        ),
        "velocity_match": (
            velocity_max_error <= PLAYER_PATH_VELOCITY_TOLERANCE
        ),
        "yaw_match": yaw_max_error <= PLAYER_PATH_ANGLE_TOLERANCE,
        "pitch_match": (
            pitch_max_error <= PLAYER_PATH_ANGLE_TOLERANCE
        ),
        "health_match": health_max_error <= 1e-6,
        "jump_match": jump_exact,
        "ground_contact_match": ground_exact,
        "alive": (
            ticks_exact
            and bool(
                (
                    pd.to_numeric(
                        observed["post.health"], errors="raise"
                    )
                    > 0
                ).all()
            )
        ),
    }
    return {
        "expected": True,
        "reference_kind": "certified_player_path_v1",
        "prototype_id": certificate["prototype_id"],
        "states_path": certificate["states_path"],
        "states_sha256": certificate["states_sha256"],
        "origin_max_error": origin_max_error,
        "velocity_max_error": velocity_max_error,
        "yaw_max_error": yaw_max_error,
        "pitch_max_error": pitch_max_error,
        "health_max_error": health_max_error,
        "checks": checks,
        "passed": all(checks.values()),
    }


def route_trace_metrics(
    server_rows: list[dict[str, Any]],
    states: pd.DataFrame,
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a frozen route replay against its calibration trajectory."""
    route_plan = scenario.get("route_plan") or {}
    expected = bool(route_plan)
    rows = [
        row for row in server_rows if row.get("kind") == "route_trace"
    ]
    policies = [
        row for row in server_rows if row.get("kind") == "route_policy"
    ]
    if not expected:
        passed = not rows and not policies
        return {
            "expected": False,
            "rows": len(rows),
            "policy_rows": len(policies),
            "passed": passed,
        }

    ticks = [int(row.get("server_tick", -1)) for row in rows]
    exact_ticks = ticks == list(range(TOTAL_TICKS))
    policy = policies[0] if len(policies) == 1 else {}
    cross_track = np.asarray(
        [float(row.get("cross_track_error", math.inf)) for row in rows],
        dtype=np.float64,
    )
    max_progress = max(
        (
            float(row.get("max_progress_fraction", -1))
            for row in rows
        ),
        default=-1.0,
    )
    reach_rate = max(
        (
            float(row.get("waypoint_reach_rate", -1))
            for row in rows
        ),
        default=-1.0,
    )
    no_progress_before_acceptance = [
        int(row.get("no_progress_ticks", TOTAL_TICKS + 1))
        for row in rows
        if float(row.get("max_progress_fraction", -1)) < 0.85
    ]
    max_no_progress_ticks = max(
        no_progress_before_acceptance, default=0
    )
    p95_cross_track = (
        float(np.quantile(cross_track, 0.95))
        if len(cross_track) and np.isfinite(cross_track).all()
        else math.inf
    )
    node_count = len(route_plan.get("nodes", []))
    expected_length = float(route_plan.get("route_length", -1))
    policy_matches = (
        len(policies) == 1
        and int(policy.get("node_count", -1)) == node_count
        and math.isclose(
            float(policy.get("route_length", -2)),
            expected_length,
            abs_tol=1e-3,
        )
        and float(policy.get("start_distance", math.inf)) <= 96
        and not bool(policy.get("calibration"))
        and policy.get("controller") == "lookahead_world_velocity_v1"
    )
    safe_states = (
        len(rows) == TOTAL_TICKS
        and all(bool(row.get("alive")) for row in rows)
        and not any(bool(row.get("unexpected_teleport")) for row in rows)
        and all(
            0 <= int(row.get("segment_index", -1))
            < max(1, node_count - 1)
            for row in rows
        )
    )

    certificate = (
        load_player_path_certificate(scenario)
        if scenario.get("player_path_certificate")
        else None
    )
    reference_kind = (
        "certified_player_path_v1"
        if certificate is not None
        else "route_calibration_v1"
    )
    calibration_path = (
        certificate["states_path"]
        if certificate is not None
        else route_plan.get("calibration_states_path")
    )
    calibration_sha = (
        certificate["states_sha256"]
        if certificate is not None
        else route_plan.get("calibration_states_sha256")
    )
    replay_max_origin_error = math.inf
    calibration_match = False
    replay_origin_tolerance = float(
        scenario.get("route_replay_origin_tolerance", 0.01)
    )
    path_source = scenario.get("player_path_source") or {}
    default_replay_tolerance = math.isclose(
        replay_origin_tolerance, 0.01, abs_tol=1e-12
    )
    stage2_overlay_tolerance = (
        scenario.get("schema_version")
        == "xonotic-v2-stage2-causal-scenario-v3"
        and path_source.get("schema_version")
        in {
            "xonotic-stage2-player-path-source-v3",
            "xonotic-stage2-player-path-source-v4",
        }
        and (
            abs(
                float(
                    (scenario.get("causal_design") or {}).get(
                        "base_view_yaw_offset_deg", 0.0
                    )
                )
            )
            > 1e-6
            or abs(
                float(
                    (scenario.get("causal_design") or {}).get(
                        "base_view_pitch_offset_deg", 0.0
                    )
                )
            )
            > 1e-6
        )
        and math.isfinite(replay_origin_tolerance)
        and 0.01 < replay_origin_tolerance <= 32.0
        and math.isclose(
            replay_origin_tolerance,
            float(
                path_source.get(
                    "player_path_position_error_max_max",
                    math.nan,
                )
            ),
            abs_tol=1e-9,
        )
    )
    replay_tolerance_contract = (
        default_replay_tolerance or stage2_overlay_tolerance
    )
    effective_replay_origin_tolerance = (
        replay_origin_tolerance
        if replay_tolerance_contract
        else 0.01
    )
    if calibration_path and calibration_sha:
        reference_path = locked_root_artifact(
            calibration_path,
            calibration_sha,
            "route_calibration_states",
        )
        reference = pd.read_parquet(reference_path)
        if (
            len(reference) == TOTAL_TICKS
            and len(states) == TOTAL_TICKS
            and "server_tick" in reference
            and "post.origin" in reference
            and list(pd.to_numeric(reference["server_tick"]))
            == list(range(TOTAL_TICKS))
        ):
            expected_origins = np.stack(
                reference["post.origin"].map(
                    lambda value: np.asarray(value, dtype=np.float64)
                )
            )
            observed_origins = np.stack(
                states["post.origin"].map(
                    lambda value: np.asarray(value, dtype=np.float64)
                )
            )
            errors = np.linalg.norm(
                expected_origins - observed_origins, axis=1
            )
            replay_max_origin_error = float(errors.max())
            calibration_match = (
                replay_max_origin_error
                <= effective_replay_origin_tolerance
            )

    gates = {
        "route_replay_tolerance_contract": (
            replay_tolerance_contract
        ),
        "route_policy_matches": policy_matches,
        "route_trace_ticks_exact": (
            len(rows) == TOTAL_TICKS and exact_ticks
        ),
        "route_progress_gte_85pct": max_progress >= 0.85,
        "route_waypoint_reach_gte_90pct": reach_rate >= 0.90,
        "route_cross_track_p95_lte_96": p95_cross_track <= 96,
        "route_no_progress_lte_half_second": (
            max_no_progress_ticks <= TICK_HZ // 2
        ),
        "route_states_safe_and_mapped": safe_states,
        "route_calibration_replay_match": calibration_match,
    }
    return {
        "expected": True,
        "rows": len(rows),
        "policy_rows": len(policies),
        "exact_tick_span": exact_ticks,
        "node_count": node_count,
        "route_length": expected_length,
        "max_progress_fraction": max_progress,
        "waypoint_reach_rate": reach_rate,
        "cross_track_error_p95": p95_cross_track,
        "max_no_progress_ticks": max_no_progress_ticks,
        "max_no_progress_seconds": max_no_progress_ticks / TICK_HZ,
        "calibration_replay_max_origin_error": (
            replay_max_origin_error
        ),
        "calibration_replay_origin_tolerance": (
            effective_replay_origin_tolerance
        ),
        "calibration_replay_tolerance_kind": (
            "stage2_manifest_frozen_view_overlay"
            if stage2_overlay_tolerance
            else "exact_frozen_route"
        ),
        "replay_reference_kind": reference_kind,
        "gates": gates,
        "passed": all(gates.values()),
    }


def event_linkage(events: pd.DataFrame) -> tuple[int, int, float]:
    if events.empty:
        return 0, 0, 1.0
    ids = set(int(value) for value in events["event_id"].dropna())
                                                                         
                                                                              
                                                                             
                                                                           
                                                          
    environmental_impact_ids: set[int] = set()
    damage_rows = events[events["event"] == "damage"]
    for _, row in damage_rows.iterrows():
        attacker = row.get("attacker")
        parent = row.get("parent_event_id")
        if (
            pd.notna(attacker)
            and int(attacker) == 0
            and pd.notna(parent)
            and int(parent) in ids
        ):
            environmental_impact_ids.add(int(parent))
    required = events[
        events["event"].isin(
            ["projectile", "impact", "damage", "death", "reload_complete"]
        )
    ]
    linked = 0
    for _, row in required.iterrows():
        parent = row.get("parent_event_id")
        if pd.notna(parent) and int(parent) in ids:
            linked += 1
        elif (
            row.get("event") == "impact"
            and pd.notna(row.get("event_id"))
            and int(row["event_id"]) in environmental_impact_ids
            and (pd.isna(parent) or int(parent) == 0)
        ):
            linked += 1
    total = len(required)
    return linked, total, linked / total if total else 1.0


def enemy_movement_audio_metrics(
    events: pd.DataFrame,
    audio_events: pd.DataFrame,
    reset_row: dict[str, Any],
    scenario: dict[str, Any],
    audio_window_start: int,
    audio_window_end: int,
) -> dict[str, Any]:
    """Link authoritative enemy footsteps to actual mixer and waveform onsets."""
    expected_cvars = server_cvars(scenario, 0)
    expected = bool(expected_cvars["capture_enemy_movement_audio"])
    enemy_entity = int(reset_row.get("enemy_entity", 0))

    if not events.empty and "event" in events:
        footsteps = events[events["event"] == "enemy_footstep"].copy()
    else:
        footsteps = pd.DataFrame()
    if not footsteps.empty:
        output_footsteps = footsteps[
            (pd.to_numeric(footsteps["server_tick"]) >= WARMUP_TICKS)
            & (pd.to_numeric(footsteps["server_tick"]) < TOTAL_TICKS)
        ].copy()
    else:
        output_footsteps = footsteps

    if (
        not audio_events.empty
        and "sample_name" in audio_events
        and "source_entity" in audio_events
    ):
        sample_names = audio_events["sample_name"].fillna("").astype(str)
        footstep_sample = sample_names.str.contains(
            r"(?:^|/)(?:metal)?footstep0[1-6]\.wav$",
            regex=True,
        )
        enemy_source = (
            pd.to_numeric(
                audio_events["source_entity"], errors="coerce"
            ).fillna(-1)
            == enemy_entity
        )
        inside_window = (
            pd.to_numeric(
                audio_events["mixer_sample_cursor"], errors="coerce"
            ).fillna(-1)
            >= audio_window_start
        ) & (
            pd.to_numeric(
                audio_events["mixer_sample_cursor"], errors="coerce"
            ).fillna(audio_window_end)
            < audio_window_end
        )
        mixer_footsteps = audio_events[
            footstep_sample & enemy_source & inside_window
        ].copy()
    else:
        mixer_footsteps = pd.DataFrame()

    used_audio_indices: set[int] = set()
    mixer_matches = 0
    onset_matches = 0
    transport_latencies_ms: list[float] = []
    transport_jitter_ms: list[float] = []
    onset_errors_ms: list[float] = []
    unmatched_event_ids: list[int] = []
    expected_transport_seconds = (
        ENEMY_AUDIO_TRANSPORT_TICKS / TICK_HZ
    )
    ordered_footsteps = (
        output_footsteps.sort_values("server_time")
        if not output_footsteps.empty
        else output_footsteps
    )
    for _, event in ordered_footsteps.iterrows():
        event_time = float(event["server_time"])
        event_sample = str(event.get("sample", ""))
        best: tuple[float, int, pd.Series[Any], float] | None = None
        for audio_index, audio in mixer_footsteps.iterrows():
            if int(audio_index) in used_audio_indices:
                continue
            if str(audio.get("sample_name", "")) != event_sample:
                continue
            latency = float(audio["server_time"]) - event_time
            jitter = abs(latency - expected_transport_seconds)
            if jitter > 0.002:
                continue
            if best is None or jitter < best[0]:
                best = (jitter, int(audio_index), audio, latency)
        if best is None:
            unmatched_event_ids.append(int(event["event_id"]))
            continue
        jitter, audio_index, audio, latency = best
        used_audio_indices.add(audio_index)
        mixer_matches += 1
        transport_latencies_ms.append(latency * 1000.0)
        transport_jitter_ms.append(jitter * 1000.0)
        mixer_cursor = int(audio["mixer_sample_cursor"])
        onset_cursor = int(audio["waveform_onset_cursor"])
        if onset_cursor >= 0:
            onset_error_ms = (
                abs(onset_cursor - mixer_cursor) * 1000.0 / AUDIO_RATE
            )
            onset_errors_ms.append(onset_error_ms)
            if onset_error_ms <= 2.0:
                onset_matches += 1

    output_count = len(output_footsteps)
    return {
        "mode": ENEMY_MOVEMENT_AUDIO_MODE,
        "expected": expected,
        "enemy_entity": enemy_entity,
        "step_stride_units": float(
            expected_cvars["capture_enemy_step_stride"]
        ),
        "authoritative_event_count_total": int(len(footsteps)),
        "authoritative_event_count_output": int(output_count),
        "mixer_event_count_output": int(len(mixer_footsteps)),
        "mixer_matched_count": int(mixer_matches),
        "waveform_onset_matched_count": int(onset_matches),
        "event_mixer_linkage_rate": (
            mixer_matches / output_count if output_count else 1.0
        ),
        "event_waveform_linkage_rate": (
            onset_matches / output_count if output_count else 1.0
        ),
        "expected_event_mixer_transport_ticks": (
            ENEMY_AUDIO_TRANSPORT_TICKS
        ),
        "median_event_mixer_transport_latency_ms": (
            float(np.median(transport_latencies_ms))
            if transport_latencies_ms
            else 0.0
        ),
        "max_event_mixer_transport_jitter_ms": (
            max(transport_jitter_ms) if transport_jitter_ms else 0.0
        ),
        "max_waveform_onset_error_ms": (
            max(onset_errors_ms) if onset_errors_ms else 0.0
        ),
        "sample_names": sorted(
            str(value)
            for value in mixer_footsteps.get(
                "sample_name", pd.Series(dtype=str)
            ).dropna().unique()
        ),
        "unmatched_authoritative_event_ids": unmatched_event_ids,
    }


def explain_resource_changes(
    states: pd.DataFrame,
    events: pd.DataFrame,
    enemy_present: bool = True,
    scenario: dict[str, Any] | None = None,
) -> tuple[int, int, list[dict[str, Any]]]:
    """Require every logged health/armor/ammo delta to have a causal event."""
    scenario = scenario or {}
    event_types_by_tick: dict[int, set[str]] = {}
    if not events.empty:
        for tick, rows in events.groupby("server_tick"):
            event_types_by_tick[int(tick)] = set(str(value) for value in rows["event"])

                                                                           
                                                                            
                                                                          
                                                                             
                                                                      
                                                                            
                                  
    design = scenario.get("causal_design") or {}
    hagar_load_contract = (
        scenario.get("schema_version")
        == "xonotic-v2-stage2-causal-scenario-v2"
        and scenario.get("weapon") == "Hagar"
        and design.get("interaction_channel") == "secondary"
        and design.get("secondary_mechanism")
        == "hagar_load_release"
    )
    if hagar_load_contract and not events.empty:
        secondary_fire_ticks = sorted(
            int(value)
            for value in events.loc[
                (events["event"] == "fire")
                & (
                    pd.to_numeric(
                        events.get(
                            "secondary",
                            pd.Series(
                                np.zeros(len(events)),
                                index=events.index,
                            ),
                        ),
                        errors="coerce",
                    ).fillna(0)
                    == 1
                ),
                "server_tick",
            ].tolist()
        )
        for _, row in states.iterrows():
            tick = int(row["server_tick"])
            clip_delta = float(row["post.clip"]) - float(
                row["pre.clip"]
            )
            applied_secondary = bool(
                int(float(row["applied_action.secondary"]))
            )
            linked_release = any(
                tick <= fire_tick <= tick + TICK_HZ
                for fire_tick in secondary_fire_ticks
            )
            if (
                math.isclose(clip_delta, -1.0, abs_tol=1e-6)
                and applied_secondary
                and linked_release
            ):
                event_types_by_tick.setdefault(tick, set()).add(
                    "hagar_secondary_load"
                )

    changes: list[tuple[tuple[int, ...], str, float, float, set[str]]] = []
    player_rules = {
        "health": {"damage", "death"},
        "armor": {"damage", "death"},
        "clip": {"fire", "reload_start", "reload_complete"},
        "reserve": {"fire", "reload_complete"},
    }
    if hagar_load_contract:
        player_rules["clip"].add("hagar_secondary_load")
        player_rules["reserve"].add("hagar_secondary_load")
    for _, row in states.iterrows():
        tick = int(row["server_tick"])
        for resource, expected in player_rules.items():
            before = float(row[f"pre.{resource}"])
            after = float(row[f"post.{resource}"])
            if not math.isclose(before, after, abs_tol=1e-6):
                                                                             
                                                                           
                                                                            
                                                              
                event_ticks = (
                    (tick - 1, tick)
                    if resource in {"health", "armor"}
                    else (tick,)
                )
                changes.append(
                    (
                        event_ticks,
                        f"player.{resource}",
                        before,
                        after,
                        expected,
                    )
                )

    if enemy_present:
        enemy_rules = {
            "health": {"damage", "death"},
            "armor": {"damage", "death"},
        }
        for index in range(1, len(states)):
            previous = states.iloc[index - 1]
            current = states.iloc[index]
            tick = int(current["server_tick"])
            for resource, expected in enemy_rules.items():
                before = float(previous[f"enemy.{resource}"])
                after = float(current[f"enemy.{resource}"])
                if not math.isclose(before, after, abs_tol=1e-6):
                                                                       
                                                                        
                                                                        
                                                                           
                    changes.append(
                        (
                            (int(previous["server_tick"]), tick),
                            f"enemy.{resource}",
                            before,
                            after,
                            expected,
                        )
                    )

    unexplained: list[dict[str, Any]] = []
    for event_ticks, resource, before, after, expected in changes:
        observed: set[str] = set()
        for event_tick in event_ticks:
            observed.update(event_types_by_tick.get(event_tick, set()))
        if not observed.intersection(expected):
            unexplained.append(
                {
                    "server_tick": event_ticks[-1],
                    "acceptable_event_ticks": list(event_ticks),
                    "resource": resource,
                    "pre": before,
                    "post": after,
                    "expected_event": sorted(expected),
                    "observed_event": sorted(observed),
                }
            )
    return len(changes), len(changes) - len(unexplained), unexplained


def map_frames_to_authoritative_states(
    frames: pd.DataFrame, states: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """Map each rendered frame to the nearest authoritative state timestamp."""
    state_times = pd.to_numeric(states["server_time"], errors="coerce").to_numpy()
    state_ticks = pd.to_numeric(states["server_tick"], errors="coerce").to_numpy()
    frame_times = pd.to_numeric(
        frames["server_time_current"], errors="coerce"
    ).to_numpy()
    mapped_ticks = np.full(len(frame_times), -1, dtype=np.int64)
    errors = np.full(len(frame_times), np.inf, dtype=np.float64)
    if not len(state_times) or np.isnan(state_times).any():
        return mapped_ticks, errors
    for index, frame_time in enumerate(frame_times):
        if not np.isfinite(frame_time):
            continue
        insertion = int(np.searchsorted(state_times, frame_time))
        candidates = [
            candidate
            for candidate in (insertion - 1, insertion)
            if 0 <= candidate < len(state_times)
        ]
        nearest = min(candidates, key=lambda candidate: abs(state_times[candidate] - frame_time))
        mapped_ticks[index] = int(state_ticks[nearest])
        errors[index] = abs(float(state_times[nearest]) - float(frame_time))
    return mapped_ticks, errors


def fixed_demo_presentation_phase_metrics(
    frames: pd.DataFrame,
) -> dict[str, Any]:
    """Verify the established one-snapshot render interpolation phase."""
    required = {
        "client_time",
        "server_time_current",
        "server_time_previous",
        "interpolation",
    }
    missing = sorted(required - set(frames.columns))
    if missing:
        return {
            "passed": False,
            "rows": len(frames),
            "missing_columns": missing,
            "max_client_previous_error_seconds": None,
            "max_abs_interpolation": None,
            "strictly_advancing_network_time": False,
        }
    client_time = pd.to_numeric(
        frames["client_time"], errors="coerce"
    ).to_numpy(dtype=np.float64)
    current_time = pd.to_numeric(
        frames["server_time_current"], errors="coerce"
    ).to_numpy(dtype=np.float64)
    previous_time = pd.to_numeric(
        frames["server_time_previous"], errors="coerce"
    ).to_numpy(dtype=np.float64)
    interpolation = pd.to_numeric(
        frames["interpolation"], errors="coerce"
    ).to_numpy(dtype=np.float64)
    finite = bool(
        np.isfinite(client_time).all()
        and np.isfinite(current_time).all()
        and np.isfinite(previous_time).all()
        and np.isfinite(interpolation).all()
    )
    client_previous_error = np.abs(client_time - previous_time)
    max_client_previous_error = (
        float(client_previous_error.max())
        if len(client_previous_error) and finite
        else math.inf
    )
    max_abs_interpolation = (
        float(np.abs(interpolation).max())
        if len(interpolation) and finite
        else math.inf
    )
    strictly_advancing = bool(
        len(current_time) == OUTPUT_TICKS
        and finite
        and np.all(current_time > previous_time)
    )
    passed = bool(
        len(frames) == OUTPUT_TICKS
        and finite
        and strictly_advancing
        and max_client_previous_error
        <= FIXED_DEMO_PRESENTATION_TOLERANCE_SECONDS
        and max_abs_interpolation
        <= FIXED_DEMO_INTERPOLATION_TOLERANCE
    )
    return {
        "passed": passed,
        "rows": len(frames),
        "missing_columns": [],
        "max_client_previous_error_seconds": (
            max_client_previous_error if math.isfinite(
                max_client_previous_error
            ) else None
        ),
        "max_abs_interpolation": (
            max_abs_interpolation if math.isfinite(
                max_abs_interpolation
            ) else None
        ),
        "strictly_advancing_network_time": strictly_advancing,
        "client_previous_tolerance_seconds": (
            FIXED_DEMO_PRESENTATION_TOLERANCE_SECONDS
        ),
        "interpolation_tolerance": (
            FIXED_DEMO_INTERPOLATION_TOLERANCE
        ),
    }


def first_person_camera_metrics(
    frames: pd.DataFrame,
    states: pd.DataFrame,
) -> dict[str, Any]:
    """Measure render-camera continuity against the authoritative player.

    A normal first-person camera differs from player origin mostly by eye
    height and small view-bob interpolation. Chase/spectator cameras introduce
    a much larger horizontal or total offset. This catches both an explicitly
    enabled chase camera and a gametype mismatch that leaves the client
    observing another entity.
    """
    origins = {
        int(row["server_tick"]): np.asarray(
            row["post.origin"], dtype=np.float64
        )
        for _, row in states.iterrows()
    }
    horizontal: list[float] = []
    total: list[float] = []
    for _, frame in frames.iterrows():
        tick_value = frame.get("episode_server_tick")
        if pd.isna(tick_value):
            continue
        origin = origins.get(int(tick_value))
        if origin is None:
            continue
        camera = np.asarray(
            [
                frame.get("camera_x"),
                frame.get("camera_y"),
                frame.get("camera_z"),
            ],
            dtype=np.float64,
        )
        if not np.isfinite(camera).all() or not np.isfinite(origin).all():
            continue
        delta = camera - origin
        horizontal.append(float(np.linalg.norm(delta[:2])))
        total.append(float(np.linalg.norm(delta)))
    horizontal_array = np.asarray(horizontal, dtype=np.float64)
    total_array = np.asarray(total, dtype=np.float64)
    violating = (
        (horizontal_array > FIRST_PERSON_MAX_HORIZONTAL_OFFSET)
        | (total_array > FIRST_PERSON_MAX_TOTAL_OFFSET)
    )
    aligned = len(horizontal)
    return {
        "aligned_frames": aligned,
        "total_frames": len(frames),
        "max_horizontal_offset": (
            float(horizontal_array.max()) if aligned else None
        ),
        "p99_horizontal_offset": (
            float(np.quantile(horizontal_array, 0.99))
            if aligned
            else None
        ),
        "max_total_offset": (
            float(total_array.max()) if aligned else None
        ),
        "p99_total_offset": (
            float(np.quantile(total_array, 0.99)) if aligned else None
        ),
        "horizontal_threshold": FIRST_PERSON_MAX_HORIZONTAL_OFFSET,
        "total_threshold": FIRST_PERSON_MAX_TOTAL_OFFSET,
        "violating_frames": int(violating.sum()) if aligned else len(frames),
        "passed": aligned == len(frames) and not bool(violating.any()),
    }


def _true_windows(mask: np.ndarray, ticks: np.ndarray) -> list[dict[str, int]]:
    windows: list[dict[str, int]] = []
    start: int | None = None
    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(mask) - 1):
            end = index if value and index == len(mask) - 1 else index - 1
            windows.append(
                {
                    "start_tick": int(ticks[start]),
                    "end_tick": int(ticks[end]),
                    "ticks": int(end - start + 1),
                }
            )
            start = None
    return windows


def movement_blockage_metrics(
    states: pd.DataFrame,
    frames: pd.DataFrame | None = None,
    scenario: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Certify ordinary movement or a predeclared visible collision.

    A kinematic progress deficit finds sustained obstruction over the full
    Stage-1 continuous-stick range. New capture builds also log a short
    authoritative player-hull trace in the commanded direction on every
    server tick. The trace proves the contacted surface; frame telemetry then
    proves that the contact point is clearly inside the rendered first-person
    view. Direction labels are diagnostic only and never substitute for the
    visibility proof.
    """
    scenario = scenario or {}
    collision_design = scenario.get("collision_design") or {}
    collision_intent = str(collision_design.get("intent", "none"))
    planned_visible_collision = (
        collision_intent == VISIBLE_COLLISION_INTENT
    )
    output = states[
        (states["server_tick"] >= WARMUP_TICKS)
        & (states["server_tick"] < TOTAL_TICKS)
    ].sort_values("server_tick")
    if output.empty:
        return {
            "high_confidence": False,
            "off_forward_cone_sustained_blockage": False,
            "training_exclusion_recommended": planned_visible_collision,
            "collision_policy_passed": not planned_visible_collision,
            "ordinary_movement_clear": True,
            "planned_visible_collision": planned_visible_collision,
            "visible_collision_qualified": False,
            "contact_telemetry_present": False,
            "commanded_ticks": 0,
            "blocked_ticks": 0,
            "longest_blocked_ticks": 0,
            "longest_blocked_seconds": 0.0,
            "blocked_fraction_of_commanded": 0.0,
            "windows": [],
            "has_contact_normal": False,
        }
    yaw = np.deg2rad(
        pd.to_numeric(
            output["applied_action.yaw"], errors="coerce"
        ).to_numpy(dtype=np.float64)
    )
    forward = pd.to_numeric(
        output["applied_action.forward"], errors="coerce"
    ).to_numpy(dtype=np.float64)
    strafe = pd.to_numeric(
        output["applied_action.strafe"], errors="coerce"
    ).to_numpy(dtype=np.float64)
                                                                           
    command = np.column_stack(
        (
            np.cos(yaw) * forward + np.sin(yaw) * strafe,
            np.sin(yaw) * forward - np.cos(yaw) * strafe,
        )
    )
    command_magnitude = np.linalg.norm(command, axis=1)
    command_unit = np.divide(
        command,
        command_magnitude[:, None],
        out=np.zeros_like(command),
        where=command_magnitude[:, None] > 0,
    )
    velocity = np.stack(
        output["post.velocity"].map(
            lambda value: np.asarray(value, dtype=np.float64)
        )
    )[:, :2]
    progress_speed = np.sum(velocity * command_unit, axis=1)
    commanded = command_magnitude >= BLOCKED_COMMAND_MIN_SPEED
    progress_threshold = np.maximum(
        BLOCKED_PROGRESS_MIN_SPEED,
        command_magnitude * BLOCKED_PROGRESS_MIN_RATIO,
    )
    blocked = commanded & (progress_speed < progress_threshold)
    ticks = pd.to_numeric(
        output["server_tick"], errors="coerce"
    ).to_numpy(dtype=np.int64)
    windows = _true_windows(blocked, ticks)

    contact_columns = {
        "probe_active": "movement_contact.probe_active",
        "hit": "movement_contact.hit",
        "fraction": "movement_contact.fraction",
        "startsolid": "movement_contact.startsolid",
        "allsolid": "movement_contact.allsolid",
        "contact_point": "movement_contact.contact_point",
        "surface_normal": "movement_contact.surface_normal",
        "surface_samples": "movement_contact.surface_samples",
        "view_los_clear": "movement_contact.view_los_clear",
    }
    contact_telemetry_present = all(
        column in output.columns for column in contact_columns.values()
    )
    contact_hit = np.zeros(len(output), dtype=bool)
    contact_visible = np.zeros(len(output), dtype=bool)
    contact_depth = np.full(len(output), np.nan, dtype=np.float64)
    contact_ndc_x = np.full(len(output), np.nan, dtype=np.float64)
    contact_ndc_y = np.full(len(output), np.nan, dtype=np.float64)
    contact_normals = np.zeros((len(output), 3), dtype=np.float64)
    wall_contact = np.zeros(len(output), dtype=bool)
    surface_proof = np.zeros(len(output), dtype=bool)
    if contact_telemetry_present:
        probe_active = pd.to_numeric(
            output[contact_columns["probe_active"]], errors="coerce"
        ).fillna(0).to_numpy(dtype=np.int64)
        logged_hit = pd.to_numeric(
            output[contact_columns["hit"]], errors="coerce"
        ).fillna(0).to_numpy(dtype=np.int64)
        startsolid = pd.to_numeric(
            output[contact_columns["startsolid"]], errors="coerce"
        ).fillna(1).to_numpy(dtype=np.int64)
        allsolid = pd.to_numeric(
            output[contact_columns["allsolid"]], errors="coerce"
        ).fillna(1).to_numpy(dtype=np.int64)
        contact_hit = (
            (probe_active == 1)
            & (logged_hit == 1)
            & (startsolid == 0)
            & (allsolid == 0)
        )
        contact_points = np.stack(
            output[contact_columns["contact_point"]].map(
                lambda value: np.asarray(value, dtype=np.float64)
            )
        )
        contact_normals = np.stack(
            output[contact_columns["surface_normal"]].map(
                lambda value: np.asarray(value, dtype=np.float64)
            )
        )
        wall_contact = (
            contact_hit
            & (
                np.abs(contact_normals[:, 2])
                <= VISIBLE_COLLISION_MAX_ABS_SURFACE_NORMAL_Z
            )
        )
        if frames is not None and not frames.empty:
            frame_by_tick = {
                int(row["episode_server_tick"]): row
                for _, row in frames.iterrows()
                if not pd.isna(row.get("episode_server_tick"))
            }
            for index, tick in enumerate(ticks):
                if not wall_contact[index]:
                    continue
                frame = frame_by_tick.get(int(tick))
                if frame is None:
                    continue
                camera = np.asarray(
                    [
                        frame.get("camera_x"),
                        frame.get("camera_y"),
                        frame.get("camera_z"),
                    ],
                    dtype=np.float64,
                )
                forward_axis = np.asarray(
                    [
                        frame.get("forward_x"),
                        frame.get("forward_y"),
                        frame.get("forward_z"),
                    ],
                    dtype=np.float64,
                )
                                                                             
                right_axis = -np.asarray(
                    [
                        frame.get("left_x"),
                        frame.get("left_y"),
                        frame.get("left_z"),
                    ],
                    dtype=np.float64,
                )
                up_axis = np.asarray(
                    [
                        frame.get("up_x"),
                        frame.get("up_y"),
                        frame.get("up_z"),
                    ],
                    dtype=np.float64,
                )
                values = np.concatenate(
                    (
                        camera,
                        forward_axis,
                        right_axis,
                        up_axis,
                    )
                )
                if not np.isfinite(values).all():
                    continue
                nearclip = float(frame.get("nearclip", 1.0))
                frustum_x = float(frame.get("frustum_x", math.nan))
                frustum_y = float(frame.get("frustum_y", math.nan))
                if (
                    not math.isfinite(frustum_x)
                    or not math.isfinite(frustum_y)
                    or frustum_x <= 0
                    or frustum_y <= 0
                ):
                    continue
                raw_samples = output.iloc[index][
                    contact_columns["surface_samples"]
                ]
                if not isinstance(raw_samples, (list, tuple, np.ndarray)):
                    continue
                projected: list[tuple[float, float, float]] = []
                for sample in raw_samples:
                    if (
                        not isinstance(sample, dict)
                        or not bool(sample.get("confirmed"))
                    ):
                        continue
                    point = np.asarray(
                        sample.get("point"), dtype=np.float64
                    )
                    if point.shape != (3,) or not np.isfinite(point).all():
                        continue
                    surface_proof[index] = True
                    delta = point - camera
                    depth = float(delta @ forward_axis)
                    if depth <= max(nearclip, 1e-6):
                        continue
                    ndc_x = float(delta @ right_axis) / (
                        depth * frustum_x
                    )
                    ndc_y = float(delta @ up_axis) / (
                        depth * frustum_y
                    )
                    projected.append((depth, ndc_x, ndc_y))
                if not projected:
                    continue
                                                                            
                                                                         
                                                                   
                best_depth, best_x, best_y = min(
                    projected,
                    key=lambda value: max(
                        abs(value[1]) / VISIBLE_COLLISION_MAX_ABS_NDC_X,
                        abs(value[2]) / VISIBLE_COLLISION_MAX_ABS_NDC_Y,
                    ),
                )
                contact_depth[index] = best_depth
                contact_ndc_x[index] = best_x
                contact_ndc_y[index] = best_y
                contact_visible[index] = any(
                    abs(ndc_x) <= VISIBLE_COLLISION_MAX_ABS_NDC_X
                    and abs(ndc_y) <= VISIBLE_COLLISION_MAX_ABS_NDC_Y
                    for _, ndc_x, ndc_y in projected
                )

                                                                            
                                                                             
                                                              
    command_angle_from_forward = np.degrees(
        np.arctan2(np.abs(strafe), forward)
    )
    off_forward = (
        command_angle_from_forward
        > BLOCKED_FORWARD_CONE_HALF_ANGLE_DEG
    )
    backward = forward < 0
    lateral_dominant = np.abs(strafe) > np.abs(forward)
    classified_windows: list[dict[str, Any]] = []
    for window in windows:
        in_window = (
            (ticks >= window["start_tick"])
            & (ticks <= window["end_tick"])
        )
        window_ticks = int(in_window.sum())
        off_fraction = (
            float(off_forward[in_window].mean())
            if window_ticks
            else 0.0
        )
        backward_fraction = (
            float(backward[in_window].mean())
            if window_ticks
            else 0.0
        )
        lateral_fraction = (
            float(lateral_dominant[in_window].mean())
            if window_ticks
            else 0.0
        )
        contact_ticks = int(contact_hit[in_window].sum())
        wall_contact_ticks = int(wall_contact[in_window].sum())
        surface_proof_ticks = int(surface_proof[in_window].sum())
        visible_ticks = int(contact_visible[in_window].sum())
        contact_fraction = (
            contact_ticks / window_ticks if window_ticks else 0.0
        )
        wall_contact_fraction = (
            wall_contact_ticks / window_ticks if window_ticks else 0.0
        )
        surface_proof_fraction = (
            surface_proof_ticks / wall_contact_ticks
            if wall_contact_ticks
            else 0.0
        )
        visible_fraction = (
            visible_ticks / wall_contact_ticks
            if wall_contact_ticks
            else 0.0
        )
        contact_confirmed = (
            window_ticks >= BLOCKED_MIN_CONSECUTIVE_TICKS
            and contact_fraction
            >= VISIBLE_COLLISION_MIN_CONTACT_FRACTION
        )
        wall_contact_confirmed = (
            contact_confirmed
            and wall_contact_fraction
            >= VISIBLE_COLLISION_MIN_CONTACT_FRACTION
        )
        clearly_visible = (
            wall_contact_confirmed
            and visible_ticks >= VISIBLE_COLLISION_MIN_VISIBLE_TICKS
            and visible_fraction
            >= VISIBLE_COLLISION_MIN_VISIBLE_FRACTION
        )
        window_end_index = int(np.flatnonzero(in_window)[-1])
        recovery_mask = (
            (~commanded)
            | (
                commanded
                & (progress_speed >= progress_threshold)
                & (~contact_hit)
            )
        )
        recovery_tail = recovery_mask[window_end_index + 1 :]
        recovery_ticks = max(
            (
                row["ticks"]
                for row in _true_windows(
                    recovery_tail,
                    ticks[window_end_index + 1 :],
                )
            ),
            default=0,
        )
        recovery_passed = (
            recovery_ticks >= VISIBLE_COLLISION_MIN_RECOVERY_TICKS
        )
        if backward_fraction >= BLOCKED_OFF_FORWARD_MIN_FRACTION:
            direction_class = "backward_or_backward_strafe"
        elif lateral_fraction >= BLOCKED_OFF_FORWARD_MIN_FRACTION:
            direction_class = "lateral"
        elif off_fraction >= BLOCKED_OFF_FORWARD_MIN_FRACTION:
            direction_class = "forward_diagonal_outside_cone"
        else:
            direction_class = "forward_cone"
        classified_windows.append(
            {
                **window,
                "mean_command_angle_from_forward_deg": float(
                    command_angle_from_forward[in_window].mean()
                ),
                "off_forward_cone_ticks": int(
                    off_forward[in_window].sum()
                ),
                "off_forward_cone_fraction": off_fraction,
                "backward_ticks": int(backward[in_window].sum()),
                "backward_fraction": backward_fraction,
                "lateral_dominant_ticks": int(
                    lateral_dominant[in_window].sum()
                ),
                "lateral_dominant_fraction": lateral_fraction,
                "direction_class": direction_class,
                "contact_confirmed_ticks": contact_ticks,
                "contact_confirmed_fraction": contact_fraction,
                "wall_contact_ticks": wall_contact_ticks,
                "wall_contact_fraction": wall_contact_fraction,
                "wall_contact_confirmed": wall_contact_confirmed,
                "surface_proof_ticks": surface_proof_ticks,
                "surface_proof_fraction": surface_proof_fraction,
                "contact_clearly_visible_ticks": visible_ticks,
                "contact_clearly_visible_fraction": visible_fraction,
                "contact_confirmed": contact_confirmed,
                "contact_clearly_visible": clearly_visible,
                "recovery_ticks": recovery_ticks,
                "recovery_passed": recovery_passed,
                "contact_depth_min": (
                    float(np.nanmin(contact_depth[in_window]))
                    if np.isfinite(contact_depth[in_window]).any()
                    else None
                ),
                "contact_ndc_abs_x_max": (
                    float(np.nanmax(np.abs(contact_ndc_x[in_window])))
                    if np.isfinite(contact_ndc_x[in_window]).any()
                    else None
                ),
                "contact_ndc_abs_y_max": (
                    float(np.nanmax(np.abs(contact_ndc_y[in_window])))
                    if np.isfinite(contact_ndc_y[in_window]).any()
                    else None
                ),
                "foundation_training_excluded": (
                    window_ticks >= BLOCKED_MIN_CONSECUTIVE_TICKS
                    and not (
                        planned_visible_collision
                        and contact_confirmed
                        and wall_contact_confirmed
                        and clearly_visible
                        and recovery_passed
                    )
                ),
            }
        )
    longest = max((row["ticks"] for row in windows), default=0)
    commanded_count = int(commanded.sum())
    blocked_count = int(blocked.sum())
    sustained_windows = [
        row
        for row in classified_windows
        if row["ticks"] >= BLOCKED_MIN_CONSECUTIVE_TICKS
    ]
    high_confidence = bool(sustained_windows)
    off_forward_blockage = any(
        row["ticks"] >= BLOCKED_MIN_CONSECUTIVE_TICKS
        and row["off_forward_cone_fraction"]
        >= BLOCKED_OFF_FORWARD_MIN_FRACTION
        for row in sustained_windows
    )
    visible_collision_qualified = (
        planned_visible_collision
        and contact_telemetry_present
        and bool(sustained_windows)
        and all(
            row["contact_confirmed"]
            and row["wall_contact_confirmed"]
            and row["contact_clearly_visible"]
            and row["recovery_passed"]
            for row in sustained_windows
        )
    )
    collision_policy_passed = (
        visible_collision_qualified
        if planned_visible_collision
        else not high_confidence
    )
    normal_magnitudes = np.linalg.norm(contact_normals, axis=1)
    return {
        "high_confidence": high_confidence,
        "off_forward_cone_sustained_blockage": off_forward_blockage,
        "training_exclusion_recommended": not collision_policy_passed,
        "collision_policy_passed": collision_policy_passed,
        "ordinary_movement_clear": not high_confidence,
        "collision_intent": collision_intent,
        "planned_visible_collision": planned_visible_collision,
        "visible_collision_qualified": visible_collision_qualified,
        "contact_telemetry_present": contact_telemetry_present,
        "command_speed_threshold": BLOCKED_COMMAND_MIN_SPEED,
        "progress_speed_minimum": BLOCKED_PROGRESS_MIN_SPEED,
        "progress_speed_ratio": BLOCKED_PROGRESS_MIN_RATIO,
        "minimum_consecutive_ticks": BLOCKED_MIN_CONSECUTIVE_TICKS,
        "forward_cone_half_angle_deg": (
            BLOCKED_FORWARD_CONE_HALF_ANGLE_DEG
        ),
        "off_forward_min_fraction": (
            BLOCKED_OFF_FORWARD_MIN_FRACTION
        ),
        "commanded_ticks": commanded_count,
        "blocked_ticks": blocked_count,
        "longest_blocked_ticks": longest,
        "longest_blocked_seconds": longest / TICK_HZ,
        "blocked_fraction_of_commanded": (
            blocked_count / commanded_count if commanded_count else 0.0
        ),
        "windows": sorted(
            classified_windows,
            key=lambda row: row["ticks"],
            reverse=True,
        )[:10],
        "has_contact_normal": bool(
            contact_telemetry_present
            and np.isfinite(contact_normals).all()
            and (normal_magnitudes[contact_hit] > 0.5).any()
        ),
        "visible_collision_thresholds": {
            "minimum_contact_fraction": (
                VISIBLE_COLLISION_MIN_CONTACT_FRACTION
            ),
            "minimum_visible_fraction": (
                VISIBLE_COLLISION_MIN_VISIBLE_FRACTION
            ),
            "minimum_visible_ticks": VISIBLE_COLLISION_MIN_VISIBLE_TICKS,
            "minimum_recovery_ticks": VISIBLE_COLLISION_MIN_RECOVERY_TICKS,
            "maximum_abs_ndc_x": VISIBLE_COLLISION_MAX_ABS_NDC_X,
            "maximum_abs_ndc_y": VISIBLE_COLLISION_MAX_ABS_NDC_Y,
            "maximum_abs_surface_normal_z": (
                VISIBLE_COLLISION_MAX_ABS_SURFACE_NORMAL_Z
            ),
        },
    }


def authoritative_action_match(
    scenario: dict[str, Any], actions: pd.DataFrame, states: pd.DataFrame
) -> tuple[bool, float]:
    """Compare requested -> engine-sent -> server-applied actions.

    DarkPlaces accumulates scheduled view deltas in ``float`` fields.  Recreate
    that float32 arithmetic here instead of accumulating Python float64 values;
    otherwise a long view schedule produces a false QA failure even when the
    client-sent and authoritative server angles are identical.
    """
    if len(actions) != TOTAL_TICKS or len(states) != TOTAL_TICKS:
        return False, math.inf
    expected_yaw = np.float32(scenario["player"]["yaw"])
    expected_pitch = np.float32(scenario["player"].get("pitch", 0.0))
    max_error = 0.0
    for index in range(TOTAL_TICKS):
        action = actions.iloc[index]
        state = states.iloc[index]
        if int(action["action_tick"]) != index or int(state["server_tick"]) != index:
            return False, math.inf
        expected_yaw = np.float32(
            expected_yaw + np.float32(action["desired_yaw_delta"])
        )
        expected_pitch = np.float32(
            min(
                89.0,
                max(
                    -89.0,
                    float(
                        np.float32(
                            expected_pitch
                            + np.float32(action["desired_pitch_delta"])
                        )
                    ),
                ),
            )
        )
        expected_buttons = (
            int(bool(action["desired_primary"]))
            | (int(bool(action["desired_jump"])) << 1)
            | (int(bool(action["desired_secondary"])) << 2)
        )
        expected_impulse = (
            20.0
            if int(action["desired_reload"])
            else float(action["desired_weapon_impulse"])
        )
        sent_forward = float(action["sent_forward"])
        sent_strafe = float(action["sent_strafe"])
        sent_pitch = float(action["sent_pitch"])
        sent_yaw = float(action["sent_yaw"])
        sent_buttons = float(action["sent_buttons"])
        sent_impulse = float(action["sent_impulse"])
        comparisons = (
                                                                        
            (float(action["desired_forward"]), sent_forward),
            (float(action["desired_strafe"]), sent_strafe),
            (float(expected_yaw), sent_yaw),
            (float(expected_pitch), sent_pitch),
            (float(expected_buttons), sent_buttons),
            (expected_impulse, sent_impulse),
                                                                                
            (sent_forward, float(state["applied_action.forward"])),
            (sent_strafe, float(state["applied_action.strafe"])),
            (sent_yaw, float(state["applied_action.yaw"])),
            (sent_pitch, float(state["applied_action.pitch"])),
            (
                float(bool(int(sent_buttons) & 2)),
                float(state["applied_action.jump"]),
            ),
            (
                float(bool(int(sent_buttons) & 1)),
                float(state["applied_action.primary"]),
            ),
            (
                float(bool(int(sent_buttons) & 4)),
                float(state["applied_action.secondary"]),
            ),
            (sent_impulse, float(state["applied_action.impulse"])),
        )
        max_error = max(
            max_error,
            max(abs(expected - observed) for expected, observed in comparisons),
        )
    return max_error <= 1e-5, max_error


def encoded_contract(probe: dict[str, Any], path: Path) -> dict[str, bool]:
    streams = probe.get("streams", [])
    video = next((row for row in streams if row.get("codec_type") == "video"), {})
    audio = next((row for row in streams if row.get("codec_type") == "audio"), {})
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_frames",
        "-show_entries",
        "frame=key_frame,coded_picture_number",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    keyframes: list[int] = []
    if completed.returncode == 0:
        for frame in json.loads(completed.stdout).get("frames", []):
            if int(frame.get("key_frame", 0)) == 1:
                keyframes.append(int(frame.get("coded_picture_number", -1)))
    duration = float(probe.get("format", {}).get("duration", -1))
    return {
        "encoded_h264_high": (
            video.get("codec_name") == "h264" and video.get("profile") == "High"
        ),
        "encoded_yuv420p": video.get("pix_fmt") == "yuv420p",
        "encoded_cfr64": (
            video.get("r_frame_rate") == "64/1"
            and video.get("avg_frame_rate") == "64/1"
        ),
        "encoded_gop64": keyframes == [0, 64, 128, 192, 256],
        "encoded_flac_s16_stereo_48khz": (
            audio.get("codec_name") == "flac"
            and audio.get("sample_fmt") == "s16"
            and int(audio.get("sample_rate", 0)) == AUDIO_RATE
            and int(audio.get("channels", 0)) == 2
            and int(audio.get("bits_per_raw_sample", 0)) == 16
        ),
        "encoded_duration_5s": math.isclose(duration, 5.0, abs_tol=1e-6),
    }


def derive_outcome(events: pd.DataFrame, scenario: dict[str, Any]) -> dict[str, Any]:
    if events.empty:
        event_counts: Counter[str] = Counter()
    else:
        event_counts = Counter(str(value) for value in events["event"])
    fires = event_counts["fire"]
    impacts = event_counts["impact"]
    damages = event_counts["damage"]
    deaths = event_counts["death"]
    direct = 0
    splash = 0
    pellet = 0
    hit_fire_ids: set[int] = set()
    if not events.empty:
        impacts_df = events[events["event"] == "impact"]
        if "direct" in impacts_df:
            direct = int(pd.to_numeric(impacts_df["direct"], errors="coerce").fillna(0).sum())
        if "splash" in impacts_df:
            splash = int(pd.to_numeric(impacts_df["splash"], errors="coerce").fillna(0).sum())
        if "pellet" in impacts_df:
            pellet = int(
                pd.to_numeric(
                    impacts_df["pellet"], errors="coerce"
                ).fillna(0).sum()
            )
        rows_by_id = {
            int(row["event_id"]): row
            for _, row in events.dropna(subset=["event_id"]).iterrows()
        }
        for _, damage in events[events["event"] == "damage"].iterrows():
            parent = damage.get("parent_event_id")
            visited: set[int] = set()
            while pd.notna(parent):
                event_id = int(parent)
                if event_id in visited or event_id not in rows_by_id:
                    break
                visited.add(event_id)
                ancestor = rows_by_id[event_id]
                if ancestor["event"] == "fire":
                    hit_fire_ids.add(event_id)
                    break
                parent = ancestor.get("parent_event_id")
    hit_rate = len(hit_fire_ids) / fires if fires else 0.0
    if not fires:
        hit_rate_bin = "no_fire"
    elif hit_rate == 0:
        hit_rate_bin = "zero"
    elif hit_rate < 0.5:
        hit_rate_bin = "low"
    elif hit_rate < 1.0:
        hit_rate_bin = "partial"
    else:
        hit_rate_bin = "full"
    if deaths:
        outcome_bin = "kill"
    elif splash:
        outcome_bin = "splash_hit"
    elif pellet:
        outcome_bin = "pellet_hit"
    elif damages:
        outcome_bin = "direct_hit"
    elif fires:
        outcome_bin = "miss"
    elif event_counts["reload_complete"]:
        outcome_bin = "reload"
    else:
        outcome_bin = "dynamics"
    return {
        "actual_outcome_bin": outcome_bin,
        "fire_count": fires,
        "hit_fire_count": len(hit_fire_ids),
        "impact_count": impacts,
        "damage_count": damages,
        "death_count": deaths,
        "direct_count": direct,
        "splash_count": splash,
        "pellet_count": pellet,
        "hit_rate": hit_rate,
        "hit_rate_bin": hit_rate_bin,
        "event_counts": dict(event_counts),
    }


SHOT_OUTCOME_COLUMNS = [
    "shot_index",
    "fire_event_id",
    "server_tick",
    "frame_index",
    "weapon",
    "weapon_netname",
    "weapon_id",
    "secondary",
    "hit",
    "outcome",
    "impact_count",
    "damage_count",
    "death_count",
    "damage_amount",
    "direct_count",
    "splash_count",
    "pellet_count",
    "killed",
    "first_impact_server_tick",
    "first_damage_server_tick",
    "first_target_entity",
    "target_entity",
    "target_hit",
    "target_outcome",
    "target_damage_count",
    "target_damage_amount",
    "target_killed",
    "target_direct",
    "target_splash",
    "target_pellet",
    "target_first_damage_server_tick",
    "target_observation_complete",
    "right_censored",
    "namespace",
]

TARGET_OUTCOME_PROJECTILE_WEAPONS = frozenset(
    {
        "Blaster",
        "Mortar",
        "Electro",
        "Crylink",
        "Hagar",
        "Devastator",
    }
)
TARGET_OUTCOME_OBSERVATION_TICKS = 96


def derive_shot_outcomes(
    events: pd.DataFrame,
    scenario: dict[str, Any],
    *,
    target_entity: int | None = None,
) -> pd.DataFrame:
    """Attribute every authoritative descendant event to its root fire.

    The linkage is purely event-graph based.  It does not infer hits from
    pixels, aim error, proximity, or the requested outcome, so the resulting
    rows are safe to use later when constructing hit/miss prompts.
    """
    if events.empty or "event" not in events.columns:
        return pd.DataFrame(columns=SHOT_OUTCOME_COLUMNS)
    indexed_rows: dict[int, dict[str, Any]] = {}
    for _, row in events.dropna(subset=["event_id"]).iterrows():
        indexed_rows[int(row["event_id"])] = row.to_dict()

    root_cache: dict[int, int | None] = {}

    def root_fire_id(event_id: int) -> int | None:
        if event_id in root_cache:
            return root_cache[event_id]
        current = event_id
        visited: set[int] = set()
        while current in indexed_rows and current not in visited:
            visited.add(current)
            row = indexed_rows[current]
            if str(row.get("event")) == "fire":
                root = current
                break
            parent = row.get("parent_event_id")
            if pd.isna(parent):
                root = None
                break
            current = int(parent)
        else:
            root = None
        for visited_id in visited:
            root_cache[visited_id] = root
        return root

    descendants: dict[int, list[dict[str, Any]]] = {}
    for event_id, row in indexed_rows.items():
        root = root_fire_id(event_id)
        if root is not None and event_id != root:
            descendants.setdefault(root, []).append(row)

    def mechanisms_for_damage(
        damage: dict[str, Any],
    ) -> set[str]:
        mechanisms: set[str] = set()
        current = int(damage["event_id"])
        visited: set[int] = set()
        while current in indexed_rows and current not in visited:
            visited.add(current)
            row = indexed_rows[current]
            if str(row.get("event")) == "impact":
                for name in ("direct", "splash", "pellet"):
                    value = row.get(name)
                    if pd.notna(value) and bool(int(value)):
                        mechanisms.add(name)
            parent = row.get("parent_event_id")
            if pd.isna(parent):
                break
            current = int(parent)
        return mechanisms

    fire_rows = sorted(
        (
            row
            for row in indexed_rows.values()
            if str(row.get("event")) == "fire"
        ),
        key=lambda row: (
            int(row.get("server_tick", -1)),
            int(row["event_id"]),
        ),
    )
    result: list[dict[str, Any]] = []
    for shot_index, fire in enumerate(fire_rows):
        fire_id = int(fire["event_id"])
        linked = descendants.get(fire_id, [])
        impacts = [
            row for row in linked if str(row.get("event")) == "impact"
        ]
        damages = [
            row for row in linked if str(row.get("event")) == "damage"
        ]
        deaths = [
            row for row in linked if str(row.get("event")) == "death"
        ]
        server_tick = int(fire["server_tick"])
        first_impact_tick = min(
            (int(row["server_tick"]) for row in impacts), default=None
        )
        first_damage_tick = min(
            (int(row["server_tick"]) for row in damages), default=None
        )
        first_target = next(
            (
                int(row["target"])
                for row in sorted(
                    damages,
                    key=lambda row: (
                        int(row.get("server_tick", -1)),
                        int(row.get("event_id", -1)),
                    ),
                )
                if pd.notna(row.get("target"))
            ),
            None,
        )
        killed = bool(deaths) or any(
            bool(int(row.get("killed", 0) or 0)) for row in damages
        )
        hit = bool(damages)
        declared_target = (
            int(target_entity)
            if target_entity is not None and int(target_entity) > 0
            else None
        )
        target_damages = (
            [
                row
                for row in damages
                if pd.notna(row.get("target"))
                and int(row["target"]) == declared_target
            ]
            if declared_target is not None
            else []
        )
        target_hit = bool(target_damages)
        target_killed = target_hit and any(
            bool(int(row.get("killed", 0) or 0))
            for row in target_damages
        )
        target_mechanisms: set[str] = set()
        for damage in target_damages:
            target_mechanisms.update(mechanisms_for_damage(damage))
        target_first_damage_tick = min(
            (
                int(row["server_tick"])
                for row in target_damages
            ),
            default=None,
        )
        target_tail_complete = (
            target_hit
            or str(scenario.get("weapon"))
            not in TARGET_OUTCOME_PROJECTILE_WEAPONS
            or TOTAL_TICKS - 1 - server_tick
            >= TARGET_OUTCOME_OBSERVATION_TICKS
        )
        target_observation_complete = (
            target_tail_complete
            if declared_target is not None
            else None
        )
        right_censored = (
            not target_tail_complete
            if declared_target is not None
            else None
        )
        target_outcome = (
            (
                "kill"
                if target_killed
                else "hit"
                if target_hit
                else "right_censored"
                if right_censored
                else "miss"
            )
            if declared_target is not None
            else None
        )
        result.append(
            {
                "shot_index": shot_index,
                "fire_event_id": fire_id,
                "server_tick": server_tick,
                "frame_index": (
                    server_tick - WARMUP_TICKS
                    if WARMUP_TICKS <= server_tick < TOTAL_TICKS
                    else None
                ),
                "weapon": scenario.get("weapon"),
                "weapon_netname": scenario.get("weapon_netname"),
                "weapon_id": (
                    int(fire["weapon_id"])
                    if pd.notna(fire.get("weapon_id"))
                    else None
                ),
                "secondary": (
                    int(fire["secondary"])
                    if pd.notna(fire.get("secondary"))
                    else None
                ),
                "hit": hit,
                "outcome": "kill" if killed else "hit" if hit else "miss",
                "impact_count": len(impacts),
                "damage_count": len(damages),
                "death_count": len(deaths),
                "damage_amount": float(
                    sum(
                        float(row.get("amount", 0) or 0)
                        for row in damages
                    )
                ),
                "direct_count": int(
                    sum(
                        int(row.get("direct", 0) or 0)
                        for row in impacts
                    )
                ),
                "splash_count": int(
                    sum(
                        int(row.get("splash", 0) or 0)
                        for row in impacts
                    )
                ),
                "pellet_count": int(
                    sum(
                        int(row.get("pellet", 0) or 0)
                        for row in impacts
                    )
                ),
                "killed": killed,
                "first_impact_server_tick": first_impact_tick,
                "first_damage_server_tick": first_damage_tick,
                "first_target_entity": first_target,
                "target_entity": declared_target,
                "target_hit": (
                    target_hit if declared_target is not None else None
                ),
                "target_outcome": target_outcome,
                "target_damage_count": (
                    len(target_damages)
                    if declared_target is not None
                    else None
                ),
                "target_damage_amount": (
                    float(
                        sum(
                            float(row.get("amount", 0) or 0)
                            for row in target_damages
                        )
                    )
                    if declared_target is not None
                    else None
                ),
                "target_killed": (
                    target_killed
                    if declared_target is not None
                    else None
                ),
                "target_direct": (
                    "direct" in target_mechanisms
                    if declared_target is not None
                    else None
                ),
                "target_splash": (
                    "splash" in target_mechanisms
                    if declared_target is not None
                    else None
                ),
                "target_pellet": (
                    "pellet" in target_mechanisms
                    if declared_target is not None
                    else None
                ),
                "target_first_damage_server_tick": (
                    target_first_damage_tick
                ),
                "target_observation_complete": (
                    target_observation_complete
                ),
                "right_censored": right_censored,
                "namespace": "authoritative_per_shot_outcome",
            }
        )
    return pd.DataFrame(result, columns=SHOT_OUTCOME_COLUMNS)


def reload_event_proof(
    events: pd.DataFrame,
    expected_weapon: str,
    *,
    expected_start_tick: int | None = None,
    expected_duration_ticks: int | None = None,
    expected_initial_clip: float | None = None,
    expected_capacity: float | None = None,
) -> dict[str, Any]:
    if "event" not in events.columns:
        return {
            "reload_start_count": 0,
            "reload_complete_count": 0,
            "expected_weapon": expected_weapon,
            "checks": {
                "reload_start_singleton": False,
                "reload_complete_singleton": False,
            },
            "passed": False,
        }
    starts = events[events["event"] == "reload_start"]
    completes = events[events["event"] == "reload_complete"]
    proof: dict[str, Any] = {
        "reload_start_count": len(starts),
        "reload_complete_count": len(completes),
        "expected_weapon": expected_weapon,
        "checks": {
            "reload_start_singleton": len(starts) == 1,
            "reload_complete_singleton": len(completes) == 1,
        },
    }
    if len(starts) != 1 or len(completes) != 1:
        proof["passed"] = False
        return proof

    start = starts.iloc[0]
    complete = completes.iloc[0]
    start_tick = int(start["server_tick"])
    complete_tick = int(complete["server_tick"])
    start_event_id = int(start["event_id"])
    parent_event_id = int(complete["parent_event_id"])
    start_actor = int(start["actor"])
    complete_actor = int(complete["actor"])
    pre_clip = float(complete["pre_clip"])
    post_clip = float(complete["post_clip"])
    pre_reserve = float(complete["pre_reserve"])
    post_reserve = float(complete["post_reserve"])
    checks = {
        **proof["checks"],
        "start_weapon_match": str(start.get("weapon", ""))
        == expected_weapon,
        "complete_weapon_match": str(complete.get("weapon", ""))
        == expected_weapon,
        "parent_link_exact": parent_event_id == start_event_id,
        "actor_match": complete_actor == start_actor,
        "completion_after_start": complete_tick > start_tick,
        "start_and_complete_in_output_window": (
            WARMUP_TICKS <= start_tick < TOTAL_TICKS
            and WARMUP_TICKS <= complete_tick < TOTAL_TICKS
        ),
        "success": int(complete.get("success", 0)) == 1,
        "start_complete_pre_clip_match": math.isclose(
            float(start["pre_clip"]), pre_clip, abs_tol=1e-6
        ),
        "start_complete_pre_reserve_match": math.isclose(
            float(start["pre_reserve"]),
            pre_reserve,
            abs_tol=1e-6,
        ),
        "clip_increased": post_clip > pre_clip,
        "reserve_decreased": post_reserve < pre_reserve,
    }
    if expected_start_tick is not None:
        checks["start_tick_exact"] = start_tick == expected_start_tick
    if expected_duration_ticks is not None:
        checks["duration_ticks_exact"] = (
            complete_tick - start_tick == expected_duration_ticks
        )
    if expected_initial_clip is not None:
        checks["initial_clip_exact"] = math.isclose(
            pre_clip, expected_initial_clip, abs_tol=1e-6
        )
    if expected_capacity is not None:
        checks["capacity_reached"] = math.isclose(
            post_clip, expected_capacity, abs_tol=1e-6
        )
    proof.update(
        {
            "start_event_id": start_event_id,
            "complete_event_id": int(complete["event_id"]),
            "start_tick": start_tick,
            "complete_tick": complete_tick,
            "duration_ticks": complete_tick - start_tick,
            "pre_clip": pre_clip,
            "post_clip": post_clip,
            "pre_reserve": pre_reserve,
            "post_reserve": post_reserve,
            "checks": checks,
            "passed": all(checks.values()),
        }
    )
    return proof


def validate_intent(
    scenario: dict[str, Any], outcome: dict[str, Any], events: pd.DataFrame
) -> dict[str, Any] | None:
    if str(scenario.get("schema_version", "")).startswith(
        "xonotic-v2-"
    ):
        acceptance = scenario.get("acceptance", {})
        role = scenario.get("dataset_role")
        expected = acceptance.get("actual_outcome")
        tiered_foundation_review = (
            uses_tiered_review_policy(scenario)
            and role
            in {
                "foundation_no_enemy",
                "foundation_enemy_distractor",
            }
        )
        if role in {
            "foundation_no_enemy",
            "foundation_enemy_distractor",
        } and outcome["damage_count"] and not tiered_foundation_review:
            raise CaptureFailure(
                "foundation_damage_forbidden",
                f"damage_count={outcome['damage_count']}",
            )
        if (
            acceptance.get("fire_required")
            and outcome["fire_count"] < 1
            and not tiered_foundation_review
        ):
            raise CaptureFailure("expected_fire_missing")
        if expected == "no_fire" and outcome["fire_count"] != 0:
            raise CaptureFailure(
                "actual_bin_mismatch", "expected=no_fire actual=fire"
            )
        if expected == "miss":
            if outcome["fire_count"] < 1 or outcome["damage_count"] != 0:
                raise CaptureFailure(
                    "actual_bin_mismatch",
                    f"expected=miss actual={outcome['actual_outcome_bin']}",
                )
        if expected == "hit_survive":
            if outcome["damage_count"] < 1 or outcome["death_count"] != 0:
                raise CaptureFailure(
                    "actual_bin_mismatch",
                    "expected=hit_survive actual="
                    f"{outcome['actual_outcome_bin']}",
                )
        if expected == "kill" and outcome["death_count"] < 1:
            raise CaptureFailure(
                "actual_bin_mismatch",
                f"expected=kill actual={outcome['actual_outcome_bin']}",
            )
        if acceptance.get("reload_success"):
            expected_weapon = str(
                acceptance.get(
                    "reload_weapon",
                    scenario.get("weapon_netname", ""),
                )
            )
            proof = reload_event_proof(
                events,
                expected_weapon,
                expected_start_tick=acceptance.get(
                    "reload_start_server_tick"
                ),
                expected_duration_ticks=acceptance.get(
                    "reload_duration_ticks"
                ),
                expected_initial_clip=acceptance.get(
                    "reload_initial_clip"
                ),
                expected_capacity=acceptance.get(
                    "reload_clip_capacity"
                ),
            )
            if proof["reload_start_count"] != 1:
                raise CaptureFailure(
                    "reload_start_count",
                    "expected=1 actual="
                    f"{proof['reload_start_count']}",
                )
            if proof["reload_complete_count"] != 1:
                raise CaptureFailure(
                    "reload_complete_count",
                    "expected=1 actual="
                    f"{proof['reload_complete_count']}",
                )
            if not proof["passed"]:
                raise CaptureFailure(
                    "reload_not_proven", canonical_json(proof)
                )
            return proof
        return None

    intent = scenario["intent_outcome"]
    if scenario["target_bin"] in {"combat_outcome", "mobile_fire"}:
        if outcome["fire_count"] < 1:
            raise CaptureFailure("expected_fire_missing")
        if intent == "miss" and outcome["damage_count"] != 0:
            raise CaptureFailure("actual_bin_mismatch", "intent=miss actual=hit")
        if intent in {"hit", "direct", "pellet", "tracking", "jump_fire", "moving_fire"}:
            if outcome["damage_count"] < 1:
                raise CaptureFailure("actual_bin_mismatch", f"intent={intent} actual=miss")
        if intent == "kill" and outcome["death_count"] < 1:
            raise CaptureFailure("actual_bin_mismatch", "intent=kill actual=no_kill")
        if intent == "direct" and outcome["direct_count"] < 1:
            raise CaptureFailure(
                "actual_bin_mismatch", "intent=direct actual=no_direct"
            )
        if intent == "splash" and outcome["splash_count"] < 1:
            raise CaptureFailure("actual_bin_mismatch", "intent=splash actual=no_splash")
        if intent == "pellet" and outcome["pellet_count"] < 1:
            raise CaptureFailure("actual_bin_mismatch", "intent=pellet actual=no_pellet")
    if scenario["target_bin"] == "machinegun_reload":
        proof = reload_event_proof(
            events,
            str(scenario.get("weapon_netname", "machinegun")),
        )
        if proof["reload_start_count"] != 1:
            raise CaptureFailure(
                "reload_start_count",
                f"expected=1 actual={proof['reload_start_count']}",
            )
        if proof["reload_complete_count"] != 1:
            raise CaptureFailure(
                "reload_complete_count",
                f"expected=1 actual={proof['reload_complete_count']}",
            )
        if not proof["passed"]:
            raise CaptureFailure(
                "reload_not_proven", canonical_json(proof)
            )
        return proof
    return None


def encode_video(
    raw_avi: Path,
    output: Path,
    log_path: Path,
    audio_start_sample: int,
    x264_threads: int | None = None,
) -> float:
    output.parent.mkdir(parents=True, exist_ok=True)
    threads = (
        configured_x264_threads()
        if x264_threads is None
        else int(x264_threads)
    )
    if threads < 0 or threads > 256:
        raise CaptureFailure("invalid_x264_threads", str(threads))
    cpuset = configured_x264_cpuset()
    command = (
        ["taskset", "--cpu-list", cpuset] if cpuset else []
    ) + [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-nostdin",
        "-i",
        str(raw_avi),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-profile:v",
        "high",
        "-crf",
        "16",
    ]
    if threads:
        command += ["-threads:v", str(threads)]
    command += [
        "-pix_fmt",
        "yuv420p",
        "-r",
        "64",
        "-vsync",
        "cfr",
        "-g",
        "64",
        "-keyint_min",
        "64",
        "-sc_threshold",
        "0",
        "-c:a",
        "flac",
        "-af",
        (
            f"atrim=start_sample={audio_start_sample}:"
            f"end_sample={audio_start_sample + AUDIO_SAMPLES},"
            "asetpts=PTS-STARTPTS"
        ),
        "-ar",
        "48000",
        "-ac",
        "2",
        str(output),
    ]
    result = run_logged_process(command, log_path, timeout_seconds=600)
    if result.returncode != 0:
        raise CaptureFailure("x264_encode_failed", f"returncode={result.returncode}")
    return result.wall_seconds


def qa_and_package(
    stage: Path,
    scenario: dict[str, Any],
    live: dict[str, Any],
    render: dict[str, Any],
    attempt_id: str,
) -> tuple[dict[str, Any], Path]:
    raw_avi = Path(render["raw_avi"])
    raw_probe = ffprobe_json(raw_avi, count_frames=True)
    frame_count = count_video_frames(raw_probe)
    raw_audio_stream = next(
        (
            row
            for row in raw_probe.get("streams", [])
            if row.get("codec_type") == "audio"
        ),
        {},
    )
    pcm = decode_audio_s16(raw_avi)
    samples_per_channel = int(pcm.shape[0])

    actions = pd.read_csv(live["actions_engine"])
    frames = pd.read_csv(render["frames_engine"])
    audio_events = pd.read_csv(render["audio_events_engine"])
    states, events, server_rows = parse_server_telemetry(live["server_telemetry"])
    reset_rows = [row for row in server_rows if row.get("kind") == "reset"]
    enemy_policy_rows = [
        row for row in server_rows if row.get("kind") == "enemy_policy"
    ]
    enemy_path_trace_rows = [
        row for row in server_rows
        if row.get("kind") == "enemy_path_trace"
    ]
    route_trace_rows = [
        row for row in server_rows if row.get("kind") == "route_trace"
    ]
    enemy_policy_row = (
        enemy_policy_rows[0] if len(enemy_policy_rows) == 1 else {}
    )
    reset_row = reset_rows[0] if len(reset_rows) == 1 else {}
    anchor_telemetry = reset_row.get("anchor", {})
    enemy_present = bool(scenario.get("enemy_present", True))
    expected_enemy_cvars = server_cvars(scenario, 0)
    expected_enemy_policy = scenario.get("enemy_policy") or {}
    expected_enemy_fires = bool(
        expected_enemy_policy.get("fires", False)
    )
    expected_enemy_jumps = bool(
        expected_enemy_policy.get("jumps", False)
    )
    expected_enemy_controller = (
        "seeded_piecewise_smooth_wander_v1"
        if int(expected_enemy_cvars["capture_enemy_motion"]) == 4
        else "analytic_motion_primitive_v1"
    )
    enemy_path_trace = enemy_path_trace_metrics(
        server_rows, states, events, scenario
    )
    route_trace = route_trace_metrics(server_rows, states, scenario)
    player_path = player_path_certificate_metrics(states, scenario)
    action_seed_header = (
        (stage / "actions_requested.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    expected_action_seed_header = f"#seed,{scenario['seed']}"
    anchor_checks = {
        "anchor_reset_singleton": len(reset_rows) == 1,
        "capture_seed_matches": (
            action_seed_header == expected_action_seed_header
            and bool(reset_row.get("seed_header_seen", 0))
        ),
        "capture_rng_seed_logged": (
            0
            < float(reset_row.get("seed_crc", -1))
            == float(reset_row.get("weapon_rng_seed", -2))
            < 65536
        ),
        "anchor_id_matches": (
            anchor_telemetry.get("id") == scenario["anchor_id"]
        ),
        "anchor_player_clear": bool(anchor_telemetry.get("player_clear", 0)),
        "enemy_presence_matches": (
            bool(reset_row.get("enemy_present", 1)) == enemy_present
        ),
        "anchor_enemy_clear": (
            not enemy_present
            or bool(anchor_telemetry.get("enemy_clear", 0))
        ),
        "anchor_player_ground": bool(
            anchor_telemetry.get("player_ground", 0)
        ),
        "anchor_enemy_ground": (
            not enemy_present
            or bool(anchor_telemetry.get("enemy_ground", 0))
        ),
        "anchor_line_of_sight": (
            not enemy_present
            or float(anchor_telemetry.get("los_fraction", -1)) >= 0.999999
        ),
        "enemy_policy_logged": (
            len(enemy_policy_rows) == (1 if enemy_present else 0)
        ),
        "enemy_policy_matches_scenario": (
            not enemy_present
            or (
                enemy_policy_row.get("policy")
                == expected_enemy_cvars["capture_enemy_policy"]
                and int(enemy_policy_row.get("policy_seed", -1))
                == expected_enemy_cvars["capture_enemy_policy_seed"]
                and int(enemy_policy_row.get("motion_mode", -1))
                == expected_enemy_cvars["capture_enemy_motion"]
                and int(
                    enemy_policy_row.get("motion_start_tick", -1)
                )
                == expected_enemy_cvars[
                    "capture_enemy_motion_start_tick"
                ]
            )
        ),
        "enemy_policy_no_live_coupling": (
            not enemy_present
            or (
                enemy_policy_row.get("reads_camera") is False
                and enemy_policy_row.get("reads_crosshair") is False
                and enemy_policy_row.get(
                    "reads_live_player_state"
                )
                is False
                and enemy_policy_row.get("fires")
                is expected_enemy_fires
                and enemy_policy_row.get("jumps")
                is expected_enemy_jumps
                and enemy_policy_row.get("controller")
                == expected_enemy_controller
            )
        ),
        "enemy_movement_audio_contract": (
            not enemy_present
            or (
                enemy_policy_row.get("movement_audio")
                == ENEMY_MOVEMENT_AUDIO_MODE
                and bool(
                    enemy_policy_row.get(
                        "movement_audio_enabled", False
                    )
                )
                == bool(
                    expected_enemy_cvars[
                        "capture_enemy_movement_audio"
                    ]
                )
                and math.isclose(
                    float(enemy_policy_row.get("step_stride", -1)),
                    float(
                        expected_enemy_cvars[
                            "capture_enemy_step_stride"
                        ]
                    ),
                    abs_tol=1e-6,
                )
            )
        ),
        "enemy_whole_path_hull_trace": enemy_path_trace["passed"],
        "route_trace_contract": route_trace["passed"],
        "certified_player_path_replay": player_path["passed"],
    }
    audio_window_start = int(frames.iloc[0]["mixer_audio_cursor_at_frame"])
    audio_window_end = audio_window_start + AUDIO_SAMPLES
    enemy_audio = enemy_movement_audio_metrics(
        events,
        audio_events,
        reset_row,
        scenario,
        audio_window_start,
        audio_window_end,
    )
    pcm_window = pcm[audio_window_start:audio_window_end]
    peak = int(np.abs(pcm_window.astype(np.int32)).max()) if pcm_window.size else 0
    rms = (
        float(np.sqrt(np.mean(pcm_window.astype(np.float64) ** 2)))
        if pcm_window.size
        else 0.0
    )
    nonzero_fraction = (
        float(np.count_nonzero(pcm_window) / pcm_window.size)
        if pcm_window.size
        else 0.0
    )

    linked, link_total, linkage = event_linkage(events)
    outcome = derive_outcome(events, scenario)
    declared_target_entity = (
        int(reset_row.get("enemy_entity", 0))
        if enemy_present
        else None
    )
    shot_outcomes = derive_shot_outcomes(
        events,
        scenario,
        target_entity=declared_target_entity,
    )
    shot_outcome_contract = {
        "rows_match_fire_count": len(shot_outcomes)
        == int(outcome["fire_count"]),
        "hit_rows_match_hit_fire_count": int(
            shot_outcomes["hit"].sum()
        )
        == int(outcome["hit_fire_count"]),
        "fire_event_ids_unique": bool(
            shot_outcomes["fire_event_id"].is_unique
        ),
        "all_fire_ticks_in_output": bool(
            shot_outcomes["frame_index"].notna().all()
        ),
        "target_entity_exact": (
            bool(
                (
                    pd.to_numeric(
                        shot_outcomes["target_entity"],
                        errors="raise",
                    ).astype(int)
                    == declared_target_entity
                ).all()
            )
            if declared_target_entity is not None
            else bool(shot_outcomes["target_entity"].isna().all())
        ),
        "target_hit_implies_generic_hit": bool(
            (
                ~shot_outcomes["target_hit"].fillna(False).astype(bool)
                | shot_outcomes["hit"].astype(bool)
            ).all()
        ),
        "v9_target_observation_complete": (
            bool(
                shot_outcomes["target_observation_complete"]
                .fillna(False)
                .astype(bool)
                .all()
                and not shot_outcomes["right_censored"]
                .fillna(False)
                .astype(bool)
                .any()
            )
            if scenario.get("action_program")
            == "stage2_causal_counterfactual_v9"
            else True
        ),
    }
    intent_proof = validate_intent(scenario, outcome, events)
    resource_changes, resource_explained, resource_unexplained = (
        explain_resource_changes(
            states,
            events,
            enemy_present=enemy_present,
            scenario=scenario,
        )
    )
    action_schedule_matches, action_schedule_max_error = (
        authoritative_action_match(scenario, actions, states)
    )

    onset_valid = audio_events[
        (audio_events["waveform_onset_cursor"] >= 0)
        & (audio_events["mixer_sample_cursor"] >= 0)
        & (audio_events["mixer_sample_cursor"] < audio_window_end)
        & (audio_events["waveform_onset_cursor"] >= audio_window_start)
    ].copy()
    if len(onset_valid):
        onset_valid["onset_error_samples"] = (
            onset_valid["waveform_onset_cursor"]
            - onset_valid["mixer_sample_cursor"]
        ).abs()
        max_onset_error_samples = int(onset_valid["onset_error_samples"].max())
    else:
        max_onset_error_samples = 0
    max_onset_error_ms = max_onset_error_samples * 1000.0 / AUDIO_RATE

    mapped_ticks, state_time_errors = map_frames_to_authoritative_states(
        frames, states
    )
    frames["episode_server_tick"] = mapped_ticks
    frames["state_time_error_ms"] = state_time_errors * 1000.0
    mapping_mask = (
        state_time_errors <= FRAME_STATE_TIME_TOLERANCE_SECONDS
    )
    server_tick_mapped = int(mapping_mask.sum())
    mapping_rate = server_tick_mapped / len(frames) if len(frames) else 0.0
    expected_output_ticks = np.arange(WARMUP_TICKS, TOTAL_TICKS, dtype=np.int64)
    exact_output_tick_span = (
        len(mapped_ticks) == len(expected_output_ticks)
        and np.array_equal(mapped_ticks, expected_output_ticks)
    )
    presentation_phase = fixed_demo_presentation_phase_metrics(frames)
    max_state_time_error_ms = (
        float(np.max(state_time_errors[mapping_mask]))
        if mapping_mask.any()
        else math.inf
    )
    camera_continuity = first_person_camera_metrics(frames, states)
    movement_blockage = movement_blockage_metrics(
        states, frames=frames, scenario=scenario
    )
    frame_indices = pd.to_numeric(
        frames.get("frame_index"), errors="coerce"
    ).to_numpy()
    frame_pts = pd.to_numeric(
        frames.get("pts_seconds"), errors="coerce"
    ).to_numpy()
    exact_frame_timeline = (
        len(frames) == OUTPUT_TICKS
        and np.array_equal(frame_indices, np.arange(OUTPUT_TICKS))
        and np.allclose(
            frame_pts,
            np.arange(OUTPUT_TICKS, dtype=np.float64) / VIDEO_FPS,
            atol=1e-9,
            rtol=0,
        )
    )
    expected_audio_cursors = np.arange(
        OUTPUT_TICKS, dtype=np.int64
    ) * SAMPLES_PER_FRAME
    logged_expected_audio_cursors = pd.to_numeric(
        frames.get("expected_audio_cursor"), errors="coerce"
    ).to_numpy()
    mixer_audio_cursors = pd.to_numeric(
        frames.get("mixer_audio_cursor_at_frame"), errors="coerce"
    ).to_numpy()
    exact_frame_audio_alignment = (
        len(frames) == OUTPUT_TICKS
        and np.array_equal(
            logged_expected_audio_cursors, expected_audio_cursors
        )
        and np.array_equal(
            mixer_audio_cursors - mixer_audio_cursors[0],
            expected_audio_cursors,
        )
    )
    forbidden_audio_samples = sorted(
        {
            str(sample)
            for sample in audio_events.get(
                "sample_name", pd.Series(dtype=str)
            ).dropna()
            if any(
                pattern in str(sample).lower()
                for pattern in FORBIDDEN_AUDIO_PATTERNS
            )
        }
    )
    frustum_x_values = pd.to_numeric(
        frames.get("frustum_x"), errors="coerce"
    ).to_numpy(dtype=np.float64)
    frustum_y_values = pd.to_numeric(
        frames.get("frustum_y"), errors="coerce"
    ).to_numpy(dtype=np.float64)
    camera_intrinsics_fixed = (
        len(frustum_x_values) == OUTPUT_TICKS
        and len(frustum_y_values) == OUTPUT_TICKS
        and np.isfinite(frustum_x_values).all()
        and np.isfinite(frustum_y_values).all()
        and np.allclose(
            frustum_x_values,
            CAMERA_FRUSTUM_X,
            atol=CAMERA_FRUSTUM_TOLERANCE,
            rtol=0,
        )
        and np.allclose(
            frustum_y_values,
            CAMERA_FRUSTUM_Y,
            atol=CAMERA_FRUSTUM_TOLERANCE,
            rtol=0,
        )
    )
    observed_frustum_x = (
        float(np.median(frustum_x_values))
        if len(frustum_x_values)
        else math.nan
    )
    observed_frustum_y = (
        float(np.median(frustum_y_values))
        if len(frustum_y_values)
        else math.nan
    )
    model_actions = build_model_actions(actions, frames)
    model_actions_metrics = model_action_metrics(
        model_actions, actions, frames
    )

    foundation_role = scenario.get("dataset_role") in {
        "foundation_no_enemy",
        "foundation_enemy_distractor",
    }
    gates = {
        "video_frames_exact": frame_count == OUTPUT_TICKS == len(frames),
        "frame_timeline_exact": exact_frame_timeline,
        "audio_window_available": samples_per_channel >= audio_window_end,
        "raw_audio_s16_stereo_48khz": (
            raw_audio_stream.get("codec_name") == "pcm_s16le"
            and raw_audio_stream.get("sample_fmt") == "s16"
            and int(raw_audio_stream.get("sample_rate", 0)) == AUDIO_RATE
            and int(raw_audio_stream.get("channels", 0)) == 2
        ),
        "samples_per_frame_exact": AUDIO_SAMPLES
        == frame_count * SAMPLES_PER_FRAME,
        "frame_audio_alignment_exact": exact_frame_audio_alignment,
        "frame_tick_mapping": (
            mapping_rate >= 0.999 and exact_output_tick_span
        ),
        "render_snapshot_presentation_phase": (
            presentation_phase["passed"]
        ),
        "expected_audio_non_silent": (not scenario["expects_sound"]) or peak > 0,
        "expected_audio_event_measured": (
            not scenario["expects_sound"] or len(onset_valid) > 0
        ),
        "audio_onset_within_2ms": max_onset_error_ms <= 2.0,
        "audio_policy": not forbidden_audio_samples,
        "enemy_movement_audio_events": (
            enemy_audio["authoritative_event_count_output"] > 0
            if enemy_audio["expected"]
            else enemy_audio["authoritative_event_count_total"] == 0
        ),
        "enemy_movement_audio_mixer_linkage": (
            enemy_audio["event_mixer_linkage_rate"] >= 0.999
            and enemy_audio["mixer_event_count_output"] > 0
            if enemy_audio["expected"]
            else enemy_audio["mixer_event_count_output"] == 0
        ),
        "enemy_movement_audio_waveform_onset": (
            enemy_audio["event_waveform_linkage_rate"] >= 0.999
            and enemy_audio["max_waveform_onset_error_ms"] <= 2.0
            if enemy_audio["expected"]
            else True
        ),
        "event_linkage": linkage >= 0.999,
        "per_shot_outcome_graph_exact": all(
            shot_outcome_contract.values()
        ),
        "resource_deltas_explained": not resource_unexplained,
        "server_state_ticks": len(states) == TOTAL_TICKS,
        "desired_action_ticks": len(actions) == TOTAL_TICKS,
        "authoritative_action_schedule": action_schedule_matches,
        "model_action_rows_exact": (
            model_actions_metrics["rows"] == OUTPUT_TICKS
        ),
        "model_action_ltx2_schema": (
            model_actions_metrics["schema_columns_present"]
            and model_actions_metrics["joystick_pairs_valid"]
            and model_actions_metrics["joystick_pairs_match_flat"]
        ),
        "model_action_frame_alignment": (
            model_actions_metrics["frame_alignment_exact"]
        ),
        "model_action_continuous_range": (
            model_actions_metrics["continuous_in_range"]
            and model_actions_metrics[
                "source_continuous_within_range"
            ]
        ),
        "model_action_engine_roundtrip": (
            model_actions_metrics["engine_roundtrip_exact"]
        ),
        "model_action_buttons_binary": (
            model_actions_metrics["buttons_binary"]
            and model_actions_metrics["button_source_match"]
        ),
        **anchor_checks,
        "minimal_hud_policy": bool(render.get("hud_policy")),
        "resident_frontend_menu_close_barrier": (
            render.get("resident_sequence") is None
            or render.get("frontend_menu_close_barrier") is True
        ),
        "gametype_exact": live.get("realized_gametype")
        == str(scenario.get("gametype", "dm")).lower(),
        "gametype_cvar_active": (
            live.get("realized_gametype_cvar_value") == 1
        ),
        "server_objective_waypoints_disabled": (
            live.get("g_ctf_flag_waypoint") == 0
        ),
        "server_snapshot_every_physics_tick": (
            live.get(
                "server_max_physics_frames_per_host_frame"
            )
            == SERVER_MAX_PHYSICS_FRAMES_PER_HOST_FRAME
        ),
        "render_demo_preroll_fixedstep": (
            render.get("demo_preroll_fixedstep")
            == RENDER_DEMO_PREROLL_FIXEDSTEP
        ),
        "hardware_renderer": is_nvidia_hardware_renderer(
            render["renderer"]
        ),
        "camera_intrinsics_fov90_fixed": camera_intrinsics_fixed,
        "first_person_camera_continuity": camera_continuity["passed"],
        "player_movement_contact_telemetry": (
            not foundation_role
            or movement_blockage["contact_telemetry_present"]
        ),
        "player_collision_policy": (
            not foundation_role
            or movement_blockage["collision_policy_passed"]
        ),
        "foundation_no_damage": (
            not foundation_role or outcome["damage_count"] == 0
        ),
        "intended_fire_observed": (
            not scenario.get("acceptance", {}).get("fire_required")
            or outcome["fire_count"] > 0
        ),
        "output_split_authorized": output_split_authorized(scenario),
    }
    tiered_review = uses_tiered_review_policy(scenario)
    soft_gate_names = {
        "expected_audio_event_measured",
        "anchor_line_of_sight",
        "foundation_no_damage",
        "intended_fire_observed",
    }
    soft_gates = (
        {
            name: passed
            for name, passed in gates.items()
            if name in soft_gate_names
        }
        if tiered_review
        else {}
    )
    hard_gates = {
        name: passed
        for name, passed in gates.items()
        if name not in soft_gates
    }
    failed = [
        name for name, passed in hard_gates.items() if not passed
    ]
    if failed:
        raise CaptureFailure(
            "qa_gate_failed",
            canonical_json(
                {
                    "failed": failed,
                    "frame_count": frame_count,
                    "frames_rows": len(frames),
                    "samples_per_channel": samples_per_channel,
                    "states": len(states),
                    "actions": len(actions),
                    "mapping_rate": mapping_rate,
                    "mapped_ticks_first_last": (
                        [int(mapped_ticks[0]), int(mapped_ticks[-1])]
                        if len(mapped_ticks)
                        else []
                    ),
                    "max_state_time_error_ms": max_state_time_error_ms,
                    "presentation_phase": presentation_phase,
                    "peak": peak,
                    "onset_ms": max_onset_error_ms,
                    "forbidden_audio_samples": forbidden_audio_samples,
                    "linkage": linkage,
                    "intent_proof": intent_proof,
                    "resource_unexplained": resource_unexplained[:10],
                    "action_schedule_max_error": action_schedule_max_error,
                    "model_action": model_actions_metrics,
                    "anchor_telemetry": anchor_telemetry,
                    "enemy_path_trace": enemy_path_trace,
                    "route_trace": route_trace,
                    "observed_frustum": [
                        observed_frustum_x,
                        observed_frustum_y,
                    ],
                    "camera_continuity": camera_continuity,
                    "movement_blockage": movement_blockage,
                }
            ),
        )

    package_stage = stage / "package"
    package_stage.mkdir(parents=True, exist_ok=True)
    encoded = package_stage / "video.mkv"
    with encode_slot() as encode_queue_wait_seconds:
        encode_seconds = encode_video(
            raw_avi,
            encoded,
            stage / "ffmpeg_encode.log",
            audio_window_start,
        )
    encoded_probe = ffprobe_json(encoded, count_frames=True)
    encoded_frames = count_video_frames(encoded_probe)
    encoded_pcm = decode_audio_s16(encoded)
    encoded_gates = encoded_contract(encoded_probe, encoded)
    encoded_gates["encoded_frames_exact"] = encoded_frames == OUTPUT_TICKS
    encoded_gates["encoded_audio_samples_exact"] = (
        encoded_pcm.shape[0] == AUDIO_SAMPLES
    )
    if not all(encoded_gates.values()):
        raise CaptureFailure(
            "encoded_contract_failed",
            canonical_json(
                {
                    "gates": encoded_gates,
                    "frames": encoded_frames,
                    "samples": encoded_pcm.shape[0],
                }
            ),
        )
    gates.update(encoded_gates)
    hard_gates.update(encoded_gates)

    actions["namespace"] = "engine_usercmd"
    states["namespace"] = "canonical_engine_state"
    events["namespace"] = "authoritative_engine_event"
    frames["namespace"] = "camera_render_state"
    audio_events["episode_mixer_sample_cursor"] = (
        audio_events["mixer_sample_cursor"] - audio_window_start
    )
    audio_events["episode_waveform_onset_cursor"] = (
        audio_events["waveform_onset_cursor"] - audio_window_start
    )
    audio_events["inside_episode_audio_window"] = (
        (audio_events["episode_mixer_sample_cursor"] >= 0)
        & (audio_events["episode_mixer_sample_cursor"] < AUDIO_SAMPLES)
    )
    audio_events["namespace"] = "engine_audio_mixer_event"
    enemy_path_traces = pd.json_normalize(enemy_path_trace_rows)
    enemy_path_traces["namespace"] = (
        "authoritative_enemy_path_clearance"
    )
    actions.to_parquet(package_stage / "actions.parquet", index=False)
    model_actions.to_parquet(
        package_stage / "model_actions.parquet", index=False
    )
    states.to_parquet(package_stage / "states.parquet", index=False)
    events.to_parquet(package_stage / "events.parquet", index=False)
    shot_outcomes.to_parquet(
        package_stage / "shot_outcomes.parquet", index=False
    )
    frames.to_parquet(package_stage / "frames.parquet", index=False)
    audio_events.to_parquet(package_stage / "audio_events.parquet", index=False)
    enemy_path_traces.to_parquet(
        package_stage / "enemy_path_trace.parquet", index=False
    )
    if scenario.get("route_plan"):
        route_traces = pd.json_normalize(route_trace_rows)
        route_traces["namespace"] = (
            "privileged_authoritative_route_trace"
        )
        route_traces.to_parquet(
            package_stage / "route_trace.parquet", index=False
        )
        base_actions = frozen_base_actions(scenario)
        base_actions.to_parquet(
            package_stage / "base_actions.parquet", index=False
        )
        aim_overlay = pd.DataFrame(
            route_view_overlay_rows(scenario)
        )
        aim_overlay["namespace"] = (
            "privileged_frozen_route_view_overlay"
        )
        aim_overlay.to_parquet(
            package_stage / "aim_overlay.parquet", index=False
        )
        (package_stage / "route_plan.json").write_text(
            json.dumps(
                scenario["route_plan"], indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )

    telemetry_hash_rows = [
        row
        for row in server_rows
        if row.get("kind")
        in {
            "state",
            "event",
            "enemy_policy",
            "enemy_path_trace",
            "route_policy",
            "route_trace",
            "output_begin",
            "output_end",
        }
    ]
    authoritative_hash = hashlib.sha256(
        "\n".join(
            canonical_json(authoritative_hash_value(row))
            for row in telemetry_hash_rows
        ).encode()
    ).hexdigest()
    qa = {
        "schema_version": (
            "xonotic-v2-qa-v1"
            if str(scenario.get("schema_version", "")).startswith(
                "xonotic-v2-"
            )
            else "xonotic-pilot-qa-v1"
        ),
        "episode_id": scenario["episode_id"],
        "attempt_id": attempt_id,
        "accepted": True,
        "acceptance_policy": (
            TIERED_REVIEW_POLICY if tiered_review else "strict"
        ),
        "capture_valid": True,
        "training_admitted": False if tiered_review else True,
        "review_status": (
            "reviewable"
            if tiered_review and not all(soft_gates.values())
            else "auto_keep_candidate"
            if tiered_review
            else "strict_accepted"
        ),
        "gates": gates,
        "hard_gates": hard_gates,
        "soft_gates": soft_gates,
        "hard_failures": [],
        "soft_flags": [
            name for name, passed in soft_gates.items() if not passed
        ],
        "video": {
            "frames": frame_count,
            "fps": VIDEO_FPS,
            "width": WIDTH,
            "height": HEIGHT,
            "raw_bytes": raw_avi.stat().st_size,
            "encoded_bytes": encoded.stat().st_size,
        },
        "audio": {
            "raw_samples_per_channel": samples_per_channel,
            "episode_window_start_sample": audio_window_start,
            "episode_window_end_sample": audio_window_end,
            "samples_per_channel": AUDIO_SAMPLES,
            "sample_rate": AUDIO_RATE,
            "channels": 2,
            "peak_s16": peak,
            "rms_s16": rms,
            "nonzero_fraction": nonzero_fraction,
            "logged_events": len(audio_events),
            "onset_events_measured": len(onset_valid),
            "max_onset_error_samples": max_onset_error_samples,
            "max_onset_error_ms": max_onset_error_ms,
            "forbidden_samples": forbidden_audio_samples,
            "enemy_movement": enemy_audio,
        },
        "mapping": {
            "mapped_frames": server_tick_mapped,
            "total_frames": len(frames),
            "success_rate": mapping_rate,
            "episode_tick_first": (
                int(mapped_ticks[0]) if len(mapped_ticks) else None
            ),
            "episode_tick_last": (
                int(mapped_ticks[-1]) if len(mapped_ticks) else None
            ),
            "max_state_time_error_ms": max_state_time_error_ms,
            "presentation_phase": presentation_phase,
        },
        "camera": {
            "projection": "rectilinear",
            "base_fov_4x3_deg": CAMERA_BASE_FOV_4X3_DEG,
            "expected_frustum_x": CAMERA_FRUSTUM_X,
            "expected_frustum_y": CAMERA_FRUSTUM_Y,
            "observed_frustum_x": observed_frustum_x,
            "observed_frustum_y": observed_frustum_y,
            "horizontal_fov_deg": math.degrees(
                2.0 * math.atan(observed_frustum_x)
            ),
            "vertical_fov_deg": math.degrees(
                2.0 * math.atan(observed_frustum_y)
            ),
            "fixed_all_frames": camera_intrinsics_fixed,
            "first_person_continuity": camera_continuity,
        },
        "anchor": {
            "anchor_id": scenario["anchor_id"],
            "player_origin": scenario["player"]["origin"],
            "enemy_origin": (
                (scenario.get("enemy") or {}).get("origin")
                if enemy_present
                else None
            ),
            "telemetry": anchor_telemetry,
        },
        "enemy_policy": {
            "scenario": scenario.get("enemy_policy"),
            "authoritative_log": (
                enemy_policy_row if enemy_present else None
            ),
            "runtime_reads_camera": False,
            "runtime_reads_crosshair": False,
            "runtime_reads_player_state": False,
            "movement_audio": enemy_audio,
            "whole_path_trace": enemy_path_trace,
        },
        "route": route_trace,
        "player_path_certificate": player_path,
        "events": {
            "linked": linked,
            "link_required": link_total,
            "linkage_rate": linkage,
            "intent_proof": intent_proof,
            "per_shot_contract": shot_outcome_contract,
            "per_shot_rows": len(shot_outcomes),
            **outcome,
        },
        "telemetry": {
            "state_rows": len(states),
            "action_rows": len(actions),
            "authoritative_sha256": authoritative_hash,
            "action_schedule_max_error": action_schedule_max_error,
            "resource_changes": resource_changes,
            "resource_changes_explained": resource_explained,
            "resource_changes_unexplained": resource_unexplained,
            "movement_blockage": movement_blockage,
        },
        "model_action": {
            "contract": model_action_contract(),
            "metrics": model_actions_metrics,
        },
        "live_precheck": live.get("precheck"),
        "mode": {
            "requested_gametype": str(
                scenario.get("gametype", "dm")
            ).lower(),
            "realized_gametype": live.get("realized_gametype"),
            "realized_gametype_cvar": live.get(
                "realized_gametype_cvar"
            ),
            "realized_gametype_cvar_value": live.get(
                "realized_gametype_cvar_value"
            ),
            "fallback_detected": False,
        },
        "hud": {
            "policy_log": render.get("hud_policy"),
            "cl_hidewaypoints": 2,
            "hud_panel_modicons": 0,
            "g_ctf_flag_waypoint": live.get(
                "g_ctf_flag_waypoint"
            ),
        },
        "runtime": {
            "live_wall_seconds": live["live_wall_seconds"],
            "live_queue_wait_seconds": live.get(
                "live_queue_wait_seconds", 0.0
            ),
            "live_sdl_queue_wait_seconds": live.get(
                "live_sdl_queue_wait_seconds", 0.0
            ),
            "render_wall_seconds": render["render_wall_seconds"],
            "render_timeout_seconds": render.get(
                "render_timeout_seconds",
                configured_render_timeout_seconds(),
            ),
            "render_startup_stall_seconds": render.get(
                "render_startup_stall_seconds",
                configured_render_startup_stall_seconds(),
            ),
            "render_queue_wait_seconds": render.get(
                "render_queue_wait_seconds", 0.0
            ),
            "render_sdl_queue_wait_seconds": render.get(
                "render_sdl_queue_wait_seconds", 0.0
            ),
            "encode_wall_seconds": encode_seconds,
            "render_video_seconds_per_wall_second": 5.0
            / render["render_wall_seconds"],
            "x264_video_seconds_per_wall_second": 5.0 / encode_seconds,
            "x264_threads": configured_x264_threads(),
            "x264_cpuset": configured_x264_cpuset(),
            "x264_cpuset_cpu_count": (
                configured_x264_cpuset_cpu_count()
            ),
            "x264_preset": "medium",
            "live_concurrency": configured_live_concurrency(),
            "render_concurrency": configured_render_concurrency(),
            "sdl_concurrency": configured_sdl_concurrency(),
            "encode_concurrency": configured_encode_concurrency(),
            "encode_concurrency_scope": (
                "process_shared_file_slots"
                if configured_encode_slot_directory() is not None
                else "process_local_threads"
            ),
            "encode_queue_wait_seconds": encode_queue_wait_seconds,
            "renderer": render["renderer"],
            "server_max_physics_frames_per_host_frame": live.get(
                "server_max_physics_frames_per_host_frame"
            ),
            "render_demo_preroll_fixedstep": render.get(
                "demo_preroll_fixedstep"
            ),
        },
    }
    with (package_stage / "qa.json").open("w", encoding="utf-8") as handle:
        json.dump(qa, handle, indent=2, sort_keys=True)
        handle.write("\n")

    episode = {
        **scenario,
        "attempt_id": attempt_id,
        "actual_outcome": outcome,
        "namespaces": {
            "actions.parquet": "engine_usercmd; not raw HID",
            "model_actions.parquet": (
                "frame-aligned normalized LTX-2 CrossFPS model input"
            ),
            "states.parquet": "canonical authoritative engine state",
            "events.parquet": "authoritative engine event graph",
            "shot_outcomes.parquet": (
                "authoritative event-graph-derived per-shot hit/miss"
            ),
            "frames.parquet": "camera and renderer state",
            "audio_events.parquet": "engine mixer events",
            "model_derived_action": "model_actions.parquet",
        },
        "model_action_contract": model_action_contract(),
        "renderer": render["renderer"],
        "requested_gametype": str(
            scenario.get("gametype", "dm")
        ).lower(),
        "realized_gametype": live.get("realized_gametype"),
        "realized_gametype_cvar": live.get(
            "realized_gametype_cvar"
        ),
        "hud_policy": {
            "cl_hidewaypoints": 2,
            "hud_panel_modicons": 0,
            "g_ctf_flag_waypoint": live.get(
                "g_ctf_flag_waypoint"
            ),
        },
        "source_commit": (build_root() / "SOURCE_COMMIT").read_text().strip(),
        "created_utc": utc_now(),
    }
    with (package_stage / "episode.json").open("w", encoding="utf-8") as handle:
        json.dump(episode, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return qa, package_stage


def copy_verified(source: Path, destination: Path) -> tuple[float, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    shutil.copy2(source, destination)
    elapsed = time.monotonic() - started
    source_hash = sha256_file(source)
    if source_hash != sha256_file(destination):
        raise CaptureFailure("cpfs_copy_hash_mismatch", str(destination))
    return elapsed, source_hash


def publish_attempt(
    stage: Path,
    scenario: dict[str, Any],
    attempt_id: str,
    package_stage: Path,
    qa: dict[str, Any],
    live: dict[str, Any],
    render: dict[str, Any],
) -> dict[str, Any]:
    episode_id = scenario["episode_id"]
    final_episode = ROOT / "pilot/episodes" / episode_id
    final_raw = ROOT / "pilot/raw" / episode_id
    if final_episode.exists() or final_raw.exists():
        raise CaptureFailure("refuse_overwrite", f"{final_episode} or {final_raw}")
    episode_tmp = ROOT / "pilot/episodes" / f".{episode_id}.tmp"
    raw_tmp = ROOT / "pilot/raw" / f".{episode_id}.tmp"
    if episode_tmp.exists() or raw_tmp.exists():
        raise CaptureFailure("stale_publish_temp", f"{episode_tmp} {raw_tmp}")
    shutil.copytree(package_stage, episode_tmp)
    raw_tmp.mkdir(parents=True)
    raw_sources = {
        "demo.dem": Path(live["demo_path"]),
        "raw_capture.avi": Path(render["raw_avi"]),
        "actions_requested.csv": stage / "actions_requested.csv",
        "actions_engine.csv": Path(live["actions_engine"]),
        "server.jsonl": Path(live["server_telemetry"]),
        "frames_engine.csv": Path(render["frames_engine"]),
        "audio_events_engine.csv": Path(render["audio_events_engine"]),
        "server_console.log": stage / "server_console.log",
        "client_live_console.log": stage / "client_live_console.log",
        "client_render_console.log": stage / "client_render_console.log",
        "ffmpeg_encode.log": stage / "ffmpeg_encode.log",
    }
    copy_started = time.monotonic()
    copied_bytes = 0
    raw_hashes: dict[str, str] = {}
    for name, source in raw_sources.items():
        if source.is_file():
            _, raw_hashes[name] = copy_verified(source, raw_tmp / name)
            copied_bytes += source.stat().st_size
    copy_seconds = time.monotonic() - copy_started
    os.rename(episode_tmp, final_episode)
    os.rename(raw_tmp, final_raw)

    formal_files = sorted(path for path in final_episode.iterdir() if path.is_file())
    hashes = {path.name: sha256_file(path) for path in formal_files}
    row = {
        "schema_version": "xonotic-pilot-manifest-v1",
        "episode_id": episode_id,
        "attempt_id": attempt_id,
        "split": "pilot",
        "target_bin": scenario["target_bin"],
        "actual_outcome_bin": qa["events"]["actual_outcome_bin"],
        "hit_rate": qa["events"]["hit_rate"],
        "hit_rate_bin": qa["events"]["hit_rate_bin"],
        "fire_count": qa["events"]["fire_count"],
        "hit_fire_count": qa["events"]["hit_fire_count"],
        "map": scenario["map"],
        "anchor_id": scenario["anchor_id"],
        "player_origin": scenario["player"]["origin"],
        "enemy_origin": scenario["enemy"]["origin"],
        "enemy_model": scenario["enemy_model"],
        "weapon": scenario["weapon"],
        "seed": scenario["seed"],
        "episode_path": str(final_episode),
        "raw_path": str(final_raw),
        "artifacts_sha256": hashes,
        "raw_artifacts_sha256": raw_hashes,
        "authoritative_sha256": qa["telemetry"]["authoritative_sha256"],
        "cpfs_copy_bytes": copied_bytes,
        "cpfs_copy_seconds": copy_seconds,
        "cpfs_copy_mib_s": (
            copied_bytes / (1024 * 1024) / copy_seconds if copy_seconds else 0.0
        ),
        "accepted_utc": utc_now(),
    }
    append_jsonl(ROOT / "manifests/accepted.jsonl", row)
    return row


def clean_stage(stage: Path) -> None:
    resolved = stage.resolve()
    allowed_parent = (TMP_ROOT / "raw").resolve()
    if resolved.parent != allowed_parent:
        raise CaptureFailure("unsafe_stage_cleanup", str(resolved))
    shutil.rmtree(resolved)


def find_scenario(episode_id: str) -> dict[str, Any]:
    scenarios_path = ROOT / "configs/pilot_scenarios.jsonl"
    if not scenarios_path.is_file():
        command_generate(argparse.Namespace())
    rows = load_jsonl(scenarios_path)
    for row in rows:
        if row["episode_id"] == episode_id:
            return row
    raise CaptureFailure("scenario_not_found", episode_id)


def next_retry_index(episode_id: str) -> int:
    """Return the next zero-based retry without reusing an audit attempt ID."""
    highest_attempt = 0
    pattern = re.compile(rf"^{re.escape(episode_id)}_a([0-9]+)$")
    for row in load_jsonl(ROOT / "manifests/rejects.jsonl"):
        match = pattern.match(str(row.get("attempt_id", "")))
        if match:
            highest_attempt = max(highest_attempt, int(match.group(1)))
    audit_roots = (
        TMP_ROOT / "raw",
        ROOT / "pilot/preflight",
        ROOT / "pilot/rejected",
        ROOT / "pilot/raw",
    )
    for audit_root in audit_roots:
        for stage in audit_root.glob(f"{episode_id}_a*"):
            match = pattern.match(stage.name)
            if match:
                highest_attempt = max(
                    highest_attempt, int(match.group(1))
                )
    for row in load_jsonl(ROOT / "manifests/accepted.jsonl"):
        match = pattern.match(str(row.get("attempt_id", "")))
        if match:
            highest_attempt = max(highest_attempt, int(match.group(1)))
    return highest_attempt


def validate_live_precheck(
    stage: Path,
    scenario: dict[str, Any],
    live: dict[str, Any],
    *,
    allow_new_player_path_certificate: bool = False,
) -> dict[str, Any]:
    """Fail structural live-simulation errors before GPU render and x264."""
    actions = pd.read_csv(live["actions_engine"])
    states, events, server_rows = parse_server_telemetry(
        live["server_telemetry"]
    )
    reset_rows = [row for row in server_rows if row.get("kind") == "reset"]
    output_begin = [
        row for row in server_rows if row.get("kind") == "output_begin"
    ]
    output_end = [
        row for row in server_rows if row.get("kind") == "output_end"
    ]
    enemy_policy_rows = [
        row for row in server_rows if row.get("kind") == "enemy_policy"
    ]
    reset = reset_rows[0] if len(reset_rows) == 1 else {}
    enemy_policy_row = (
        enemy_policy_rows[0] if len(enemy_policy_rows) == 1 else {}
    )
    anchor = reset.get("anchor", {})
    enemy_present = bool(scenario.get("enemy_present", True))
    expected_enemy_cvars = server_cvars(scenario, 0)
    expected_enemy_policy = scenario.get("enemy_policy") or {}
    expected_enemy_fires = bool(
        expected_enemy_policy.get("fires", False)
    )
    expected_enemy_jumps = bool(
        expected_enemy_policy.get("jumps", False)
    )
    expected_enemy_controller = (
        "seeded_piecewise_smooth_wander_v1"
        if int(expected_enemy_cvars["capture_enemy_motion"]) == 4
        else "analytic_motion_primitive_v1"
    )
    enemy_path_trace = enemy_path_trace_metrics(
        server_rows, states, events, scenario
    )
    route_trace = route_trace_metrics(server_rows, states, scenario)
    player_path = player_path_certificate_metrics(states, scenario)
    certification_candidate = bool(
        allow_new_player_path_certificate
        and not scenario.get("player_path_certificate")
        and scenario.get("split")
        == "v5_stage1_path_certification"
        and (scenario.get("path_prototype") or {}).get(
            "certification_required"
        )
        is True
    )
    route_candidate_gates = (
        route_trace.get("gates") or {}
    )
    route_candidate_passed = bool(
        route_trace.get("expected")
        and route_candidate_gates
        and all(
            value
            for name, value in route_candidate_gates.items()
            if name != "route_calibration_replay_match"
        )
    )
    route_contract_passed = bool(
        route_trace["passed"]
        or (certification_candidate and route_candidate_passed)
    )
    action_matches, action_max_error = authoritative_action_match(
        scenario, actions, states
    )
    checks = {
        "reset_singleton": len(reset_rows) == 1,
        "output_begin_singleton": len(output_begin) == 1,
        "output_end_singleton": len(output_end) == 1,
        "server_state_ticks": len(states) == TOTAL_TICKS,
        "desired_action_ticks": len(actions) == TOTAL_TICKS,
        "authoritative_action_schedule": action_matches,
        "episode_id_matches": reset.get("episode_id")
        == scenario["episode_id"],
        "anchor_id_matches": anchor.get("id") == scenario["anchor_id"],
        "player_hull_clear": bool(anchor.get("player_clear", 0)),
        "player_grounded": bool(anchor.get("player_ground", 0)),
        "enemy_presence_matches": (
            bool(reset.get("enemy_present", 1)) == enemy_present
        ),
        "reset_loadout_identity_matches": (
            reset.get("weapon")
            == expected_enemy_cvars["capture_weapon"]
            and (
                not enemy_present
                or (
                    reset.get("enemy_model")
                    == expected_enemy_cvars["capture_enemy_model"]
                    and int(reset.get("enemy_skin", -1))
                    == expected_enemy_cvars["capture_enemy_skin"]
                    and int(reset.get("enemy_color", -1))
                    == expected_enemy_cvars["capture_enemy_color"]
                )
            )
        ),
        "enemy_hull_clear": (
            not enemy_present or bool(anchor.get("enemy_clear", 0))
        ),
        "enemy_grounded": (
            not enemy_present or bool(anchor.get("enemy_ground", 0))
        ),
        "enemy_policy_row_count": (
            len(enemy_policy_rows) == (1 if enemy_present else 0)
        ),
        "enemy_policy_name": (
            not enemy_present
            or enemy_policy_row.get("policy")
            == expected_enemy_cvars["capture_enemy_policy"]
        ),
        "enemy_policy_seed": (
            not enemy_present
            or int(enemy_policy_row.get("policy_seed", -1))
            == expected_enemy_cvars["capture_enemy_policy_seed"]
        ),
        "enemy_policy_motion_contract": (
            not enemy_present
            or (
                int(enemy_policy_row.get("motion_mode", -1))
                == expected_enemy_cvars["capture_enemy_motion"]
                and int(
                    enemy_policy_row.get("motion_start_tick", -1)
                )
                == expected_enemy_cvars[
                    "capture_enemy_motion_start_tick"
                ]
                and math.isclose(
                    float(
                        enemy_policy_row.get("motion_distance", -1)
                    ),
                    float(
                        expected_enemy_cvars[
                            "capture_enemy_motion_distance"
                        ]
                    ),
                    abs_tol=1e-6,
                )
            )
        ),
        "enemy_policy_no_live_coupling": (
            not enemy_present
            or (
                enemy_policy_row.get("reads_camera") is False
                and enemy_policy_row.get("reads_crosshair") is False
                and enemy_policy_row.get(
                    "reads_live_player_state"
                )
                is False
                and enemy_policy_row.get("fires")
                is expected_enemy_fires
                and enemy_policy_row.get("jumps")
                is expected_enemy_jumps
                and enemy_policy_row.get("controller")
                == expected_enemy_controller
            )
        ),
        "enemy_movement_audio_contract": (
            not enemy_present
            or (
                enemy_policy_row.get("movement_audio")
                == ENEMY_MOVEMENT_AUDIO_MODE
                and bool(
                    enemy_policy_row.get(
                        "movement_audio_enabled", False
                    )
                )
                == bool(
                    expected_enemy_cvars[
                        "capture_enemy_movement_audio"
                    ]
                )
                and math.isclose(
                    float(enemy_policy_row.get("step_stride", -1)),
                    float(
                        expected_enemy_cvars[
                            "capture_enemy_step_stride"
                        ]
                    ),
                    abs_tol=1e-6,
                )
            )
        ),
        "enemy_whole_path_hull_trace": enemy_path_trace["passed"],
        "route_trace_contract": route_contract_passed,
        "certified_player_path_replay": player_path["passed"],
        "seed_logged": (
            bool(reset.get("seed_header_seen", 0))
            and 0
            < float(reset.get("seed_crc", -1))
            == float(reset.get("weapon_rng_seed", -2))
            < 65536
        ),
    }
    report = {
        "schema_version": "xonotic-live-precheck-v1",
        "episode_id": scenario["episode_id"],
        "checks": checks,
        "passed": all(checks.values()),
        "state_rows": len(states),
        "action_rows": len(actions),
        "event_rows": len(events),
        "action_schedule_max_error": action_max_error,
        "enemy_policy": enemy_policy_row or None,
        "enemy_path_trace": enemy_path_trace,
        "route_trace": route_trace,
        "player_path_certificate": player_path,
        "new_player_path_certificate_candidate": {
            "enabled": certification_candidate,
            "route_base_reference_may_be_replaced": bool(
                certification_candidate and route_candidate_passed
            ),
            "route_non_reference_gates_passed": (
                route_candidate_passed
            ),
        },
        "created_utc": utc_now(),
    }
    (stage / "LIVE_PRECHECK.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not report["passed"]:
        raise CaptureFailure(
            "live_precheck_failed", canonical_json(report)
        )
    return report


def execute_attempt(
    scenario: dict[str, Any],
    retry: int,
    publish: bool,
    port: int | None = None,
) -> dict[str, Any]:
    validate_fixed_assets()
    validate_scenario_assets(scenario)
    tmp_free = shutil.disk_usage(TMP_ROOT).free
    if tmp_free < TMP_MIN_FREE_BYTES:
        raise CaptureFailure(
            "tmp_capacity_gate",
            f"free_bytes={tmp_free} required={TMP_MIN_FREE_BYTES}",
        )
    build = build_root()
    attempt_id = f"{scenario['episode_id']}_a{retry + 1:02d}"
    stage = TMP_ROOT / "raw" / attempt_id
    if stage.exists():
        clean_stage(stage)
    stage.mkdir(parents=True)
    (stage / "ATTEMPT.json").write_text(
        json.dumps(
            {
                "attempt_id": attempt_id,
                "scenario": scenario,
                "started_utc": utc_now(),
                "build": str(build),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with live_slot() as live_queue_wait_seconds:
        with sdl_slot() as live_sdl_queue_wait_seconds:
            live = run_live_attempt(
                stage, scenario, build, retry, port=port
            )
    live["live_queue_wait_seconds"] = live_queue_wait_seconds
    live["live_sdl_queue_wait_seconds"] = (
        live_sdl_queue_wait_seconds
    )
    live["precheck"] = validate_live_precheck(
        stage, scenario, live
    )
    with render_slot() as render_queue_wait_seconds:
        with sdl_slot() as render_sdl_queue_wait_seconds:
            render = run_render_attempt(
                stage, scenario, build, Path(live["client_user"])
            )
    render["render_queue_wait_seconds"] = render_queue_wait_seconds
    render["render_sdl_queue_wait_seconds"] = (
        render_sdl_queue_wait_seconds
    )
    qa, package_stage = qa_and_package(
        stage, scenario, live, render, attempt_id
    )
    if publish:
        manifest_row = publish_attempt(
            stage, scenario, attempt_id, package_stage, qa, live, render
        )
    else:
        manifest_row = {
            "episode_id": scenario["episode_id"],
            "attempt_id": attempt_id,
            "stage": str(stage),
            "qa": qa,
        }
    return manifest_row


def preserve_rejected_stage(
    stage: Path, attempt_id: str
) -> tuple[str | None, dict[str, str], str | None]:
    if not stage.is_dir():
        return None, {}, None
    rejected_root = ROOT / "pilot/rejected"
    destination = rejected_root / attempt_id
    temporary = rejected_root / f".{attempt_id}.tmp"
    if destination.exists() or temporary.exists():
        return None, {}, f"refuse_overwrite:{destination}"
    try:
        rejected_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, temporary)
        hashes: dict[str, str] = {}
        for source in sorted(path for path in stage.rglob("*") if path.is_file()):
            relative = source.relative_to(stage)
            copied = temporary / relative
            source_hash = sha256_file(source)
            if source_hash != sha256_file(copied):
                raise CaptureFailure(
                    "reject_copy_hash_mismatch", str(copied)
                )
            hashes[str(relative)] = source_hash
        os.rename(temporary, destination)
        return str(destination), hashes, None
    except Exception as exc:
        return None, {}, f"{type(exc).__name__}:{exc}"


def record_reject(
    scenario: dict[str, Any],
    retry: int,
    failure: CaptureFailure,
    stage: Path,
) -> dict[str, Any]:
    attempt_id = f"{scenario['episode_id']}_a{retry + 1:02d}"
    preserved_path, hashes, preservation_error = preserve_rejected_stage(
        stage, attempt_id
    )
    row = {
        "schema_version": "xonotic-pilot-reject-v1",
        "attempt_id": attempt_id,
        "episode_id": scenario["episode_id"],
        "split": "pilot",
        "target_bin": scenario["target_bin"],
        "reason": failure.reason,
        "detail": failure.detail,
        "stage_path": str(stage),
        "preserved_path": preserved_path,
        "preserved_artifacts_sha256": hashes,
        "preservation_error": preservation_error,
        "rejected_utc": utc_now(),
    }
    append_jsonl(ROOT / "manifests/rejects.jsonl", row)
    return row


def command_attempt(args: argparse.Namespace) -> int:
    require_conda()
    scenario = find_scenario(args.episode_id)
    try:
        row = execute_attempt(scenario, args.retry, publish=args.publish)
    except CaptureFailure as exc:
        stage = TMP_ROOT / "raw" / f"{scenario['episode_id']}_a{args.retry + 1:02d}"
        record_reject(scenario, args.retry, exc, stage)
        print(f"REJECT reason={exc.reason} detail={exc.detail}", file=sys.stderr)
        return 2
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    require_conda()
    results: list[dict[str, Any]] = []
    for episode_id in args.episode_ids:
        scenario = find_scenario(episode_id)
        retry = next_retry_index(episode_id)
        stage = TMP_ROOT / "raw" / f"{episode_id}_a{retry + 1:02d}"
        print(
            f"validate {episode_id} map={scenario['map']} "
            f"weapon={scenario['weapon']} attempt={stage.name}",
            flush=True,
        )
        try:
            row = execute_attempt(scenario, retry, publish=False)
        except CaptureFailure as exc:
            record_reject(scenario, retry, exc, stage)
            print(
                f"reject {episode_id} reason={exc.reason} detail={exc.detail}",
                flush=True,
            )
            return 2
        results.append(
            {
                "episode_id": episode_id,
                "attempt_id": row["attempt_id"],
                "stage": row["stage"],
                "map": scenario["map"],
                "weapon": scenario["weapon"],
                "target_bin": scenario["target_bin"],
                "intent_outcome": scenario["intent_outcome"],
                "actual_outcome_bin": row["qa"]["events"][
                    "actual_outcome_bin"
                ],
                "qa": row["qa"],
            }
        )
        print(
            f"pass {episode_id} actual="
            f"{row['qa']['events']['actual_outcome_bin']}",
            flush=True,
        )
    evidence = {
        "schema_version": "xonotic-representative-validation-v1",
        "created_utc": utc_now(),
        "build": str(build_root()),
        "results": results,
    }
    if not re.fullmatch(r"[a-z0-9_]+\.json", args.evidence_name):
        raise CaptureFailure(
            "invalid_evidence_name", str(args.evidence_name)
        )
    output = ROOT / "qa" / args.evidence_name
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"evidence={output}")
    return 0


def command_determinism(args: argparse.Namespace) -> int:
    require_conda()
    scenario = find_scenario(args.episode_id)
    first_retry = next_retry_index(args.episode_id)
    repeats: list[dict[str, Any]] = []
    for offset in range(2):
        retry = first_retry + offset
        stage = (
            TMP_ROOT
            / "raw"
            / f"{args.episode_id}_a{retry + 1:02d}"
        )
        print(f"determinism attempt={stage.name}", flush=True)
        try:
            row = execute_attempt(scenario, retry, publish=False)
        except CaptureFailure as exc:
            record_reject(scenario, retry, exc, stage)
            print(
                f"reject {args.episode_id} reason={exc.reason} "
                f"detail={exc.detail}",
                flush=True,
            )
            return 2
        repeats.append(
            {
                "attempt_id": row["attempt_id"],
                "qa_path": str(stage / "package/qa.json"),
                "authoritative_sha256": row["qa"]["telemetry"][
                    "authoritative_sha256"
                ],
            }
        )
    hashes = [row["authoritative_sha256"] for row in repeats]
    passed = len(set(hashes)) == 1
    build = build_root()
    evidence = {
        "schema_version": "xonotic-authoritative-determinism-v1",
        "created_utc": utc_now(),
        "episode_id": args.episode_id,
        "method": (
            "Two independent live dedicated-server/client/demo/render/encode "
            "attempts with the same scenario seed and requested action "
            "schedule; the hash excludes only server wall/start-time "
            "coordinates."
        ),
        "build": str(build),
        "source_commit": (build / "SOURCE_COMMIT").read_text().strip(),
        "repeats": repeats,
        "authoritative_sha256": hashes[0] if passed else None,
        "result": "pass" if passed else "fail",
    }
    output = ROOT / "qa/determinism.json"
    if output.exists():
        previous = json.loads(output.read_text())
        previous_commit = str(previous.get("source_commit", "unknown"))[:12]
        history = ROOT / "qa/determinism_history"
        history.mkdir(parents=True, exist_ok=True)
        archived = history / f"determinism_{previous_commit}.json"
        if not archived.exists():
            shutil.copy2(output, archived)
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"evidence={output}")
    print(f"result={evidence['result']} hash={hashes}")
    return 0 if passed else 2


def command_pilot(args: argparse.Namespace) -> int:
    require_conda()
    verify_asset_hashes()
    scenarios = generate_scenarios()
    accepted_path = ROOT / "manifests/accepted.jsonl"
    existing = {row["episode_id"]: row for row in load_jsonl(accepted_path)}
    for scenario in scenarios:
        episode_id = scenario["episode_id"]
        if episode_id in existing:
            print(f"skip accepted {episode_id}", flush=True)
            continue
        accepted = False
        first_retry = next_retry_index(episode_id)
        for retry in range(first_retry, first_retry + args.max_retries):
            stage = TMP_ROOT / "raw" / f"{episode_id}_a{retry + 1:02d}"
            print(
                f"capture {episode_id} bin={scenario['target_bin']} "
                f"attempt_id={stage.name} "
                f"try={retry - first_retry + 1}/{args.max_retries}",
                flush=True,
            )
            try:
                row = execute_attempt(scenario, retry, publish=True)
            except CaptureFailure as exc:
                rejection = record_reject(scenario, retry, exc, stage)
                print(
                    f"reject {episode_id} reason={exc.reason} detail={exc.detail}",
                    flush=True,
                )
                if rejection["preserved_path"] and stage.exists():
                    clean_stage(stage)
                continue
            existing[episode_id] = row
            accepted = True
            print(
                f"accepted {episode_id} actual={row['actual_outcome_bin']}",
                flush=True,
            )
            if stage.exists():
                clean_stage(stage)
            break
        if not accepted:
            raise CaptureFailure(
                "pilot_retry_exhausted",
                f"{episode_id} after {args.max_retries} attempts",
            )
    accepted_rows = load_jsonl(accepted_path)
    ids = [row["episode_id"] for row in accepted_rows]
    distribution = Counter(row["target_bin"] for row in accepted_rows)
    if len(accepted_rows) != 100 or len(set(ids)) != 100:
        raise CaptureFailure(
            "accepted_count_gate",
            f"rows={len(accepted_rows)} unique={len(set(ids))}",
        )
    if distribution != Counter(TARGET_COUNTS):
        raise CaptureFailure(
            "accepted_distribution_gate", canonical_json(dict(distribution))
        )
    print("pilot_complete accepted=100")
    print(f"distribution={dict(distribution)}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.set_defaults(func=command_generate)
    attempt = subparsers.add_parser("attempt")
    attempt.add_argument("episode_id")
    attempt.add_argument("--retry", type=int, default=0)
    attempt.add_argument("--publish", action="store_true")
    attempt.set_defaults(func=command_attempt)
    validate = subparsers.add_parser("validate")
    validate.add_argument(
        "episode_ids",
        nargs="*",
        default=[
            "pilot_041",
            "pilot_042",
            "pilot_043",
            "pilot_044",
            "pilot_091",
        ],
    )
    validate.add_argument(
        "--evidence-name",
        default="representative_validation.json",
    )
    validate.set_defaults(func=command_validate)
    determinism = subparsers.add_parser("determinism")
    determinism.add_argument("episode_id", nargs="?", default="pilot_001")
    determinism.set_defaults(func=command_determinism)
    pilot = subparsers.add_parser("pilot")
    pilot.add_argument("--max-retries", type=int, default=5)
    pilot.set_defaults(func=command_pilot)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except CaptureFailure as exc:
        print(f"FATAL reason={exc.reason} detail={exc.detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
