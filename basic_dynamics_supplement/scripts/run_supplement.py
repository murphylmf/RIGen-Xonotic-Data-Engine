                      
"""Capture the isolated Stage-1 supplement with resident process lanes."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import errno
import fcntl
import hashlib
import json
import math
import os
import shutil
import signal
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SCRIPTS = Path("./xonotic_workspace")
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
                                                                       
                                                                      
    "XONOTIC_CAPTURE_TMP",
    "./tmp/xonotic-stage1-supplement-v1",
)
os.environ.setdefault(
    "XONOTIC_CONDA_PREFIX_REQUIRED",
    "./environment",
)
os.environ.setdefault(
    "XONOTIC_BUILD_GLOB",
    "build/capture-858ad1f142b0-qc7e8310-aarch64",
)
sys.path.insert(0, str(CANONICAL_SCRIPTS))

import run_capture_manifest_shard as common              
import run_stage1_manifest_shard as formal              
import xonotic_capture as capture              
import xonotic_stage1_reusable as reusable              


ACTION_PROGRAM = "stage1_supplement_v1"
OFFLINE_ACCELERATION_POLICY = "non_wall_impact_only_v1"
OFFLINE_ACCELERATION_EXCLUDED_CATEGORIES = ("wall_impact",)
SOURCE_COMMIT = "858ad1f142b033d0c09ded372ae53857ea3e1c21"
OFFLINE_DEMO_PATCH_SHA256 = (
    "be8a052d825cffa9b28ecd8ee384272bd16a8fbf3848cd45ba9a519f51194a3d"
)
OFFLINE_DEMO_ACCELERATION_PATCH_SHA256 = (
    "e561268d92b9378ef2075647af393be44036d3510a5ce6f747331869638b781b"
)
QC_SOURCE_COMMIT = "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
QC_SHA256 = {
    "csprogs.dat": "bee1e4be8b41237266c50aad6f59a7a87687c809064a278dc8553f1d734f7498",
    "menu.dat": "f02ae3b5396aa8d5d8f36a43c11204d33ce92c35379e5ecd32590da6677529a4",
    "progs.dat": "37909a11c5bba198d6e76f669bb9d3dda21638d29a308e8063a834821b013600",
}
RUNTIME_LOCK = ROOT / "locks/capture-858ad1f142b0-qc7e8310-aarch64.sha256"
RUNTIME_LOCK_SHA256 = (
    "31c82c460af241b45397bb0de61e8abc70f2d7bf499698799588064f57c4c934"
)
MANIFEST = ROOT / "manifests/design.jsonl"
DESIGN_AUDIT = ROOT / "manifests/DESIGN_AUDIT.json"
STOP = threading.Event()
WRITE_LOCK = threading.Lock()


class AcceleratedReusableStage1Lane(reusable.ReusableStage1Lane):
    """Enable and prove the isolated offline-demo fast path per episode."""

    def __init__(
        self,
        lane_root: Path,
        *,
        build: Path,
        port: int,
        offline_acceleration: bool = True,
    ) -> None:
        super().__init__(lane_root, build=build, port=port)
        self.offline_acceleration = offline_acceleration

    def run_render(
        self,
        stage: Path,
        scenario: dict[str, Any],
        live: dict[str, Any],
    ) -> dict[str, Any]:
        if self.render_client is None:
            raise AssertionError("render client must be running")
        start = self.render_client.offset()
        marker = f"resident_acceleration_ready_{live['resident_token']}"
        realized = "1" if self.offline_acceleration else "0"
        self.render_client.send_confirmed(
            [
                f"cl_capturevideo_offline_accelerate {realized}",
                "cl_capturevideo_realtime 0",
                "cl_capturevideo_offline_accelerate",
                "cl_capturevideo_realtime",
            ],
            marker,
            start=start,
            timeout_seconds=capture.configured_resident_control_timeout_seconds(),
        )
        for expected in (
            (
                '"cl_capturevideo_offline_accelerate" '
                f'is "{realized}"'
            ).encode(),
            b'"cl_capturevideo_realtime" is "0"',
        ):
            self.render_client.wait_for(
                expected,
                start=start,
                timeout_seconds=capture.configured_resident_control_timeout_seconds(),
            )
        preflight_log = stage / "client_render_acceleration_preflight.log"
        self.render_client.write_slice(start, preflight_log)
        result = super().run_render(stage, scenario, live)
        result["offline_demo_acceleration"] = self.offline_acceleration
        result["offline_demo_acceleration_cvar"] = (
            "cl_capturevideo_offline_accelerate"
        )
        result["offline_demo_acceleration_preflight"] = preflight_log
        return result


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical(row) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def zero_row(tick: int) -> dict[str, Any]:
    return {
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


def action_windows(mode: str, variant: int) -> list[tuple[int, int]]:
    jitter = (variant * 17) % 48
    if mode == "idle_then_action":
        return [(112 + jitter, capture.OUTPUT_TICKS)]
    if mode == "action_then_idle":
        return [(0, 160 - jitter // 2)]
    if mode == "action_idle_action":
        return [(0, 64 + jitter // 3), (240 - jitter // 3, 320)]
    return []


def window_shape(out_tick: int, windows: list[tuple[int, int]]) -> tuple[float, float]:
    for start, stop in windows:
        if start <= out_tick < stop:
            length = max(2, stop - start)
            phase = (out_tick - start) / (length - 1)
            offset = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)
            movement = math.sin(2.0 * math.pi * phase)
            return offset, movement
    return 0.0, 0.0


def idle_transition_rows(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    spec = scenario["supplement"]
    mode = str(spec["mode"])
    variant = int(spec.get("variant", 0))
    family = str(spec.get("action_family", "view"))
    windows = action_windows(mode, variant)
    yaw_amplitude = 8.0 + float((variant * 11) % 23)
    pitch_amplitude = float(((variant * 7) % 15) - 7)
    movement_amplitude = 56.0 + float((variant * 13) % 64)
    movement_angle = math.radians(float((variant * 37) % 360))
    absolute_yaw = np.zeros(capture.OUTPUT_TICKS, dtype=np.float64)
    absolute_pitch = np.zeros(capture.OUTPUT_TICKS, dtype=np.float64)
    movement_shape = np.zeros(capture.OUTPUT_TICKS, dtype=np.float64)
    for out_tick in range(capture.OUTPUT_TICKS):
        shape, motion = window_shape(out_tick, windows)
        absolute_yaw[out_tick] = yaw_amplitude * shape
        absolute_pitch[out_tick] = pitch_amplitude * shape
        movement_shape[out_tick] = motion
    yaw_delta = np.diff(np.concatenate(([0.0], absolute_yaw)))
    pitch_delta = np.diff(np.concatenate(([0.0], absolute_pitch)))
    rows = [zero_row(tick) for tick in range(capture.TOTAL_TICKS)]
    for out_tick in range(capture.OUTPUT_TICKS):
        row = rows[capture.WARMUP_TICKS + out_tick]
        if family in {"view", "view_move"}:
            row["yaw_delta"] = round(float(yaw_delta[out_tick]), 6)
            row["pitch_delta"] = round(float(pitch_delta[out_tick]), 6)
        if family in {"move", "view_move"}:
            scalar = movement_amplitude * movement_shape[out_tick]
            row["forward"] = round(scalar * math.cos(movement_angle), 6)
            row["strafe"] = round(scalar * math.sin(movement_angle), 6)
    return rows


def impact_offsets(name: str, variant: int) -> tuple[np.ndarray, np.ndarray]:
    ticks = np.arange(capture.OUTPUT_TICKS, dtype=np.float64)
    phase = ticks / float(capture.OUTPUT_TICKS - 1)
    amplitude = 5.0 + float((variant * 7) % 9)
    if name == "horizontal":
        yaw = amplitude * np.sin(2.0 * math.pi * phase)
        pitch = np.zeros_like(yaw)
    elif name == "vertical":
        yaw = np.zeros_like(phase)
        pitch = 0.65 * amplitude * np.sin(2.0 * math.pi * phase)
    elif name == "diagonal":
        yaw = amplitude * np.sin(2.0 * math.pi * phase)
        pitch = 0.55 * yaw
    elif name == "arc":
        yaw = amplitude * np.sin(2.0 * math.pi * phase)
        pitch = 0.45 * amplitude * (1.0 - np.cos(2.0 * math.pi * phase))
    elif name == "zigzag":
        yaw = 0.65 * amplitude * np.sin(4.0 * math.pi * phase)
        pitch = 0.35 * amplitude * np.sin(2.0 * math.pi * phase)
    else:
        phase_offset = math.radians(float((variant * 53) % 360))
        yaw = amplitude * (
            0.58 * np.sin(2.0 * math.pi * phase + phase_offset)
            + 0.24 * np.sin(4.0 * math.pi * phase + 0.3)
        )
        pitch = amplitude * (
            0.30 * np.sin(2.0 * math.pi * phase + 0.8)
            + 0.18 * np.sin(6.0 * math.pi * phase + phase_offset)
        )
        yaw -= yaw[0]
        pitch -= pitch[0]
    return yaw, pitch


def impact_rows(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    spec = scenario["supplement"]
    yaw, pitch = impact_offsets(
        str(spec.get("trajectory", "horizontal")),
        int(spec.get("trajectory_variant", 0)),
    )
    yaw_delta = np.diff(np.concatenate(([0.0], yaw)))
    pitch_delta = np.diff(np.concatenate(([0.0], pitch)))
    rows = [zero_row(tick) for tick in range(capture.TOTAL_TICKS)]
    starts = (48, 144, 240)
    weapon = str(scenario["weapon"])
    width = 12 if weapon == "MachineGun" else 2
    for out_tick in range(capture.OUTPUT_TICKS):
        row = rows[capture.WARMUP_TICKS + out_tick]
        row["yaw_delta"] = round(float(yaw_delta[out_tick]), 6)
        row["pitch_delta"] = round(float(pitch_delta[out_tick]), 6)
        row["primary"] = int(
            any(start <= out_tick < start + width for start in starts)
        )
    return rows


def read_base_actions(spec: dict[str, Any]) -> list[dict[str, Any]]:
    path = capture.locked_root_artifact(
        spec["base_actions_path"],
        spec["base_actions_sha256"],
        "supplement_base_actions",
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    parsed = list(csv.DictReader(lines[1:]))
    if (
        len(parsed) != capture.TOTAL_TICKS
        or [int(row["tick"]) for row in parsed]
        != list(range(capture.TOTAL_TICKS))
    ):
        raise capture.CaptureFailure("supplement_base_actions_invalid", str(path))
    return parsed


def route_overlay(spec: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    ticks = np.arange(capture.OUTPUT_TICKS, dtype=np.float64)
    phase = ticks / float(capture.OUTPUT_TICKS - 1)
    variant = int(spec.get("overlay_variant", 0))
    amplitude = 4.0 + float((variant * 5) % 9)
    mode = str(spec.get("overlay", "sweep"))
    if mode == "scan":
        yaw = amplitude * np.sin(2.0 * math.pi * phase)
        pitch = 0.25 * amplitude * np.sin(4.0 * math.pi * phase)
    elif mode == "vertical":
        yaw = 0.35 * amplitude * np.sin(2.0 * math.pi * phase)
        pitch = 0.55 * amplitude * np.sin(2.0 * math.pi * phase)
    elif mode == "figure8":
        yaw = amplitude * np.sin(2.0 * math.pi * phase)
        pitch = 0.4 * amplitude * np.sin(4.0 * math.pi * phase)
    else:
        yaw = amplitude * (0.5 - 0.5 * np.cos(2.0 * math.pi * phase))
        pitch = np.zeros_like(yaw)
    return yaw, pitch


def smooth_route_rows(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    spec = scenario["supplement"]
    base = read_base_actions(spec)
    view_scale = float(spec.get("view_scale", 0.8))
    overlay_yaw, overlay_pitch = route_overlay(spec)
    overlay_yaw_delta = np.diff(np.concatenate(([0.0], overlay_yaw)))
    overlay_pitch_delta = np.diff(np.concatenate(([0.0], overlay_pitch)))
    rows: list[dict[str, Any]] = []
    cumulative_yaw_offset = 0.0
    for tick, source in enumerate(base):
        row = {
            "tick": tick,
            "forward": float(source["forward"]),
            "strafe": float(source["strafe"]),
            "yaw_delta": float(source["yaw_delta"]),
            "pitch_delta": float(source["pitch_delta"]),
            "jump": int(float(source["jump"])),
            "primary": 0,
            "secondary": 0,
            "weapon_impulse": 0,
            "reload": 0,
        }
        if tick >= capture.WARMUP_TICKS:
            out_tick = tick - capture.WARMUP_TICKS
            base_yaw_delta = float(source["yaw_delta"])
            new_yaw_delta = (
                base_yaw_delta * view_scale
                + float(overlay_yaw_delta[out_tick])
            )
            new_pitch_delta = (
                float(source["pitch_delta"]) * view_scale
                + float(overlay_pitch_delta[out_tick])
            )
            cumulative_yaw_offset += new_yaw_delta - base_yaw_delta
            radians = math.radians(cumulative_yaw_offset)
            cosine, sine = math.cos(radians), math.sin(radians)
            base_forward = float(source["forward"])
            base_strafe = float(source["strafe"])
            row["forward"] = base_forward * cosine - base_strafe * sine
            row["strafe"] = base_strafe * cosine + base_forward * sine
            row["yaw_delta"] = new_yaw_delta
            row["pitch_delta"] = new_pitch_delta
            if not bool(spec.get("preserve_jump", False)):
                row["jump"] = 0
        row["forward"] = round(float(row["forward"]), 6)
        row["strafe"] = round(float(row["strafe"]), 6)
        row["yaw_delta"] = round(float(row["yaw_delta"]), 6)
        row["pitch_delta"] = round(float(row["pitch_delta"]), 6)
        rows.append(row)
    return rows


def supplement_action_rows(
    scenario: dict[str, Any], retry: int = 0
) -> list[dict[str, Any]]:
    del retry
    mode = str((scenario.get("supplement") or {}).get("mode", ""))
    if mode == "idle_pure":
        rows = [zero_row(tick) for tick in range(capture.TOTAL_TICKS)]
    elif mode in {"idle_then_action", "action_then_idle", "action_idle_action"}:
        rows = idle_transition_rows(scenario)
    elif mode == "wall_impact":
        rows = impact_rows(scenario)
    elif mode == "smooth_route":
        rows = smooth_route_rows(scenario)
    else:
        raise capture.CaptureFailure("supplement_mode_unknown", mode)
    capture.validate_model_action_source_rows(rows)
    max_view_delta = max(
        max(abs(float(row["yaw_delta"])), abs(float(row["pitch_delta"])))
        for row in rows[capture.WARMUP_TICKS :]
    )
    if max_view_delta > 6.0 + 1e-6:
        raise capture.CaptureFailure(
            "supplement_view_delta_over_6deg", f"max={max_view_delta}"
        )
    return rows


capture.register_action_row_provider(
    "stage1_supplement_v1", (ACTION_PROGRAM,), supplement_action_rows
)


def actual_camera_steps(package: Path) -> dict[str, float]:
    frames = pd.read_parquet(package / "frames.parquet").sort_values("frame_index")
    forward = frames[["forward_x", "forward_y", "forward_z"]].to_numpy(
        dtype=np.float64
    )
    yaw = np.unwrap(np.arctan2(forward[:, 1], forward[:, 0]))
    pitch = np.arcsin(np.clip(forward[:, 2], -1.0, 1.0))
    return {
        "yaw_max_frame_step_deg": float(
            np.max(np.abs(np.diff(np.degrees(yaw))), initial=0.0)
        ),
        "pitch_max_frame_step_deg": float(
            np.max(np.abs(np.diff(np.degrees(pitch))), initial=0.0)
        ),
    }


def custom_admission(
    scenario: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    package = Path(result["package_stage"])
    qa = result["qa"]
    actions = pd.read_parquet(package / "actions.parquet")
    states = pd.read_parquet(package / "states.parquet")
    mode = str(scenario["supplement"]["mode"])
    camera = actual_camera_steps(package)
    desired_axes = actions[
        [
            "desired_forward",
            "desired_strafe",
            "desired_yaw_delta",
            "desired_pitch_delta",
        ]
    ].to_numpy(dtype=np.float64)
    desired_buttons = actions[
        [
            "desired_jump",
            "desired_primary",
            "desired_secondary",
            "desired_weapon_impulse",
            "desired_reload",
        ]
    ].to_numpy(dtype=np.float64)
    active = np.any(np.abs(desired_axes) > 1e-8, axis=1) | np.any(
        np.abs(desired_buttons) > 1e-8, axis=1
    )
    output_active = active[capture.WARMUP_TICKS :]
    weapons = set(states["post.weapon"].astype(str))
    checks = {
        "canonical_hard_gates": all(qa["hard_gates"].values()),
        "camera_yaw_step_le_6": camera["yaw_max_frame_step_deg"] <= 6.0,
        "camera_pitch_step_le_6": camera["pitch_max_frame_step_deg"] <= 6.0,
        "no_enemy": not bool(scenario.get("enemy_present")),
        "no_damage": int(qa["events"]["damage_count"]) == 0,
        "no_weapon_switch_input": int(
            np.abs(actions["desired_weapon_impulse"].to_numpy()).sum()
        )
        == 0,
        "held_weapon_fixed": weapons == {str(scenario["weapon_netname"])},
        "pure_idle_exact": (
            not bool(output_active.any()) if mode == "idle_pure" else True
        ),
        "transition_has_idle": (
            int((~output_active).sum()) >= 64
            if mode in {"idle_then_action", "action_then_idle", "action_idle_action"}
            else True
        ),
        "transition_has_action": (
            bool(output_active.any())
            if mode in {"idle_then_action", "action_then_idle", "action_idle_action"}
            else True
        ),
        "impact_fire_observed": (
            int(qa["events"]["fire_count"]) > 0
            if mode == "wall_impact"
            else int(qa["events"]["fire_count"]) == 0
        ),
    }
    report = {
        "schema_version": "xonotic-stage1-supplement-admission-v1",
        "episode_id": scenario["episode_id"],
        "mode": mode,
        "checks": checks,
        "camera": camera,
        "active_output_frames": int(output_active.sum()),
        "idle_output_frames": int((~output_active).sum()),
        "fire_count": int(qa["events"]["fire_count"]),
        "damage_count": int(qa["events"]["damage_count"]),
        "passed": all(checks.values()),
    }
    if not report["passed"]:
        raise capture.CaptureFailure(
            "supplement_admission_failed", canonical(report)
        )
    (package / "SUPPLEMENT_ADMISSION.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def copy_once(source: Path, destination: Path) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise capture.CaptureFailure("refuse_overwrite", str(destination))
    shutil.copy2(source, destination)
    digest = sha256_file(source)
    if digest != sha256_file(destination):
        raise capture.CaptureFailure("publish_hash_mismatch", str(destination))
    return digest, destination.stat().st_size


def publish_candidate(
    output_root: Path,
    scenario: dict[str, Any],
    result: dict[str, Any],
    admission: dict[str, Any],
    port: int,
    lane_index: int,
) -> dict[str, Any]:
    stage = Path(result["stage"])
    package = Path(result["package_stage"])
    destination = output_root / "candidates" / scenario["episode_id"]
    temporary = destination.parent / f".{destination.name}.tmp.{result['attempt_id']}"
    if destination.exists() or temporary.exists():
        raise capture.CaptureFailure("refuse_overwrite", str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    hashes: dict[str, str] = {}
    total_bytes = 0
    for source in sorted(package.rglob("*")):
        if source.is_file():
            relative = source.relative_to(package)
            digest, size = copy_once(source, temporary / relative)
            hashes[str(relative)] = digest
            total_bytes += size
    provenance_sources = {
        "demo.dem": stage / "demo.dem",
        "actions_requested.csv": stage / "actions_requested.csv",
        "actions_engine.csv": Path(result["live"]["actions_engine"]),
        "server.jsonl": Path(result["live"]["server_telemetry"]),
        "frames_engine.csv": Path(result["render"]["frames_engine"]),
        "audio_events_engine.csv": Path(result["render"]["audio_events_engine"]),
        "LIVE_PRECHECK.json": stage / "LIVE_PRECHECK.json",
        "server_console.log": stage / "server_console.log",
        "client_live_console.log": stage / "client_live_console.log",
        "client_render_console.log": stage / "client_render_console.log",
        "client_render_acceleration_preflight.log": (
            stage / "client_render_acceleration_preflight.log"
        ),
        "ffmpeg_encode.log": stage / "ffmpeg_encode.log",
    }
    for name, source in provenance_sources.items():
        if source.is_file():
            relative = Path("capture_provenance") / name
            digest, size = copy_once(source, temporary / relative)
            hashes[str(relative)] = digest
            total_bytes += size
    record = {
        "schema_version": "xonotic-stage1-supplement-candidate-v1",
        "episode_id": scenario["episode_id"],
        "attempt_id": result["attempt_id"],
        "supplement_split": scenario["supplement_split"],
        "category": scenario["primary_bucket"],
        "map": scenario["map"],
        "gametype": scenario["gametype"],
        "weapon": scenario["weapon"],
        "source_episode_id": scenario["supplement_source_episode_id"],
        "source_group_id": scenario["supplement_source_group_id"],
        "scenario_sha256": hashlib.sha256(canonical(scenario).encode()).hexdigest(),
        "manifest_sha256": sha256_file(MANIFEST),
        "source_commit": SOURCE_COMMIT,
        "offline_demo_fixedstep_patch_sha256": OFFLINE_DEMO_PATCH_SHA256,
        "offline_demo_acceleration": bool(
            result["qa"]["runtime"]["offline_demo_acceleration"]
        ),
        "offline_demo_acceleration_cvar": (
            "cl_capturevideo_offline_accelerate"
        ),
        "offline_demo_acceleration_patch_sha256": (
            OFFLINE_DEMO_ACCELERATION_PATCH_SHA256
        ),
        "qc_source_commit": QC_SOURCE_COMMIT,
        "qc_sha256": QC_SHA256,
        "runtime_lock_sha256": RUNTIME_LOCK_SHA256,
        "training_admitted": False,
        "formal_collection_authorized": True,
        "quota_assignment": "pending_supplement_final_audit",
        "capture_port": port,
        "lane_index": lane_index,
        "admission": admission,
        "qa": {
            "frames": result["qa"]["video"]["frames"],
            "audio_samples": result["qa"]["audio"]["samples_per_channel"],
            "mapping_rate": result["qa"]["mapping"]["success_rate"],
            "renderer": result["qa"]["runtime"]["renderer"],
            "fire_count": result["qa"]["events"]["fire_count"],
            "damage_count": result["qa"]["events"]["damage_count"],
        },
        "runtime": result["qa"]["runtime"],
        "package_bytes": total_bytes,
        "published_utc": capture.utc_now(),
    }
    record_path = temporary / "supplement_candidate_record.json"
    record_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes["supplement_candidate_record.json"] = sha256_file(record_path)
    total_bytes += record_path.stat().st_size
    ready = temporary / "PUBLICATION_READY.json"
    ready.write_text(
        json.dumps(
            {
                "schema_version": "xonotic-stage1-publication-ready-v1",
                "kind": "supplement_candidate",
                "episode_id": scenario["episode_id"],
                "attempt_id": result["attempt_id"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    hashes["PUBLICATION_READY.json"] = sha256_file(ready)
    total_bytes += ready.stat().st_size
    os.rename(temporary, destination)
    manifest_row = {
        **record,
        "episode_path": str(destination),
        "package_sha256": hashes,
        "package_bytes": total_bytes,
    }
    append_jsonl(output_root / "manifests/accepted.jsonl", manifest_row)
    return manifest_row


def annotate_offline_replay_runtime(
    result: dict[str, Any], offline_acceleration: bool
) -> None:
    qa_path = Path(result["package_stage"]) / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa["runtime"].update(
        {
            "offline_demo_acceleration": offline_acceleration,
            "offline_demo_acceleration_cvar": (
                "cl_capturevideo_offline_accelerate"
            ),
            "offline_demo_acceleration_patch_sha256": (
                OFFLINE_DEMO_ACCELERATION_PATCH_SHA256
            ),
        }
    )
    common.atomic_json(qa_path, qa)
    result["qa"] = qa


def safe_remove(path: Path, allowed_parent: Path) -> None:
    resolved = path.resolve()
    parent = allowed_parent.resolve()
    if resolved == parent or parent not in resolved.parents:
        raise RuntimeError(f"unsafe cleanup path: {resolved}")
                                                                             
                                                                             
                                                                
    for attempt in range(12):
        try:
            shutil.rmtree(resolved)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            if exc.errno not in (errno.ENOTEMPTY, errno.EBUSY, errno.ENOENT):
                raise
            if attempt == 11:
                raise
            time.sleep(0.05 * (attempt + 1))


def cleanup_episode_files(
    lane: reusable.ReusableStage1Lane, result: dict[str, Any]
) -> None:
    live = result.get("live") or {}
    for path in (
        Path(str(live.get("demo_path", ""))),
        lane.render_user / "data/demos" / f"{live.get('demo_name', '')}.dem",
    ):
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
    token = str(live.get("resident_token", ""))
    episode_data = lane.server_user / "data/capture/resident" / token
    if token and episode_data.is_dir():
        safe_remove(episode_data, lane.server_user / "data/capture/resident")


def preserve_reject(
    output_root: Path,
    scenario: dict[str, Any],
    attempt_id: str,
    stage: Path,
    exc: Exception,
    terminal: bool,
) -> dict[str, Any]:
    reason = exc.reason if isinstance(exc, capture.CaptureFailure) else type(exc).__name__
    evidence = output_root / "rejects" / attempt_id
    evidence.mkdir(parents=True, exist_ok=True)
    for name in (
        "ATTEMPT.json",
        "LIVE_PRECHECK.json",
        "server_console.log",
        "client_live_console.log",
        "client_render_console.log",
        "ffmpeg_encode.log",
    ):
        source = stage / name
        if source.is_file():
            shutil.copy2(source, evidence / name)
    row = {
        "schema_version": "xonotic-stage1-supplement-reject-v1",
        "episode_id": scenario["episode_id"],
        "attempt_id": attempt_id,
        "category": scenario["primary_bucket"],
        "supplement_split": scenario["supplement_split"],
        "reason": reason,
        "detail": str(exc),
        "terminal": terminal,
        "evidence_path": str(evidence),
        "rejected_utc": capture.utc_now(),
    }
    append_jsonl(output_root / "manifests/rejects.jsonl", row)
    return row


def lane_plan(
    rows: list[dict[str, Any]], workers: int
) -> list[list[tuple[tuple[str, str], list[dict[str, Any]]]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["map"]), str(row["gametype"]).lower())
        grouped.setdefault(key, []).append(row)
    ideal = max(1, (len(rows) + workers - 1) // workers)
    chunks: list[tuple[tuple[str, str], list[dict[str, Any]]]] = []
    for key, values in sorted(grouped.items()):
        values.sort(key=lambda row: int(row["candidate_ordinal"]))
        count = max(1, (len(values) + ideal - 1) // ideal)
        for index in range(count):
            start = index * len(values) // count
            stop = (index + 1) * len(values) // count
            if start < stop:
                chunks.append((key, values[start:stop]))
    chunks.sort(key=lambda item: (-len(item[1]), item[0]))
    plans: list[list[tuple[tuple[str, str], list[dict[str, Any]]]]] = [
        [] for _ in range(workers)
    ]
    loads = [0] * workers
    for chunk in chunks:
        target = min(range(workers), key=lambda index: (loads[index], index))
        plans[target].append(chunk)
        loads[target] += len(chunk[1])
    return plans


def write_status(
    output_root: Path,
    started: float,
    total_rows: int,
    state: str,
    accepted_at_start: int,
) -> dict[str, Any]:
    accepted = load_jsonl(output_root / "manifests/accepted.jsonl")
    rejects = load_jsonl(output_root / "manifests/rejects.jsonl")
    elapsed = max(1e-6, time.monotonic() - started)
    accepted_this_run = max(0, len(accepted) - accepted_at_start)
    counts = Counter((row["supplement_split"], row["category"]) for row in accepted)
    status = {
        "schema_version": "xonotic-stage1-supplement-status-v1",
        "state": state,
        "pid": os.getpid(),
        "accepted": len(accepted),
        "rejected_attempts": len(rejects),
        "target_rows": total_rows,
        "remaining": max(0, total_rows - len(accepted)),
        "elapsed_seconds": elapsed,
        "accepted_at_start": accepted_at_start,
        "accepted_this_run": accepted_this_run,
        "accepted_episodes_per_hour": accepted_this_run * 3600.0 / elapsed,
        "video_hours_per_wall_hour": accepted_this_run * 5.0 / elapsed,
        "counts": {
            f"{split}/{category}": count
            for (split, category), count in sorted(counts.items())
        },
        "updated_utc": capture.utc_now(),
    }
    temporary = output_root / "STATUS.json.tmp"
    temporary.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, output_root / "STATUS.json")
    return status


def run_lane(
    lane_index: int,
    groups: list[tuple[tuple[str, str], list[dict[str, Any]]]],
    *,
    build: Path,
    output_root: Path,
    tmp_root: Path,
    port: int,
    max_attempts: int,
    started: float,
    total_rows: int,
    accepted_at_start: int,
    offline_acceleration: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for group_index, (world_group, group_rows) in enumerate(groups, 1):
        if STOP.is_set():
            break
        lane_root = (
            tmp_root
            / "resident"
            / f"lane-{lane_index:02d}-group-{group_index:03d}-{world_group[0]}"
        )
        safe_remove(lane_root, tmp_root / "resident")
        lane: AcceleratedReusableStage1Lane | None = None
        try:
            lane = AcceleratedReusableStage1Lane(
                lane_root,
                build=build,
                port=port,
                offline_acceleration=offline_acceleration,
            )
            for scenario in group_rows:
                if STOP.is_set():
                    break
                destination = output_root / "candidates" / scenario["episode_id"]
                if destination.is_dir():
                    continue
                for attempt_index in range(max_attempts):
                    attempt_id = f"{scenario['episode_id']}_a{attempt_index + 1:02d}"
                    stage = tmp_root / "raw" / attempt_id
                    if stage.exists():
                        safe_remove(stage, tmp_root / "raw")
                    try:
                        scenario = dict(scenario)
                        scenario_offline_acceleration = (
                            offline_acceleration
                            and scenario["primary_bucket"]
                            not in OFFLINE_ACCELERATION_EXCLUDED_CATEGORIES
                        )
                        lane.offline_acceleration = (
                            scenario_offline_acceleration
                        )
                        scenario.setdefault(
                            "supplement_design_source_commit_required",
                            scenario.get("source_commit_required"),
                        )
                        scenario.setdefault(
                            "supplement_design_runtime_lock_sha256",
                            scenario.get("runtime_lock_sha256"),
                        )
                        scenario["source_commit_required"] = SOURCE_COMMIT
                        scenario["runtime_lock_sha256"] = RUNTIME_LOCK_SHA256
                        scenario["supplement_runtime_revision"] = (
                            "offline_demo_acceleration_v1"
                            if scenario_offline_acceleration
                            else (
                                "offline_demo_acceleration_wall_impact_paced_v1"
                                if offline_acceleration
                                else "offline_demo_acceleration_ab_baseline_v1"
                            )
                        )
                        scenario["offline_demo_acceleration_policy"] = (
                            OFFLINE_ACCELERATION_POLICY
                            if offline_acceleration
                            else "disabled_ab_baseline"
                        )
                        scenario["audio_expectation_policy"] = capture.stage1_audio_expectation(
                            scenario
                        )
                        scenario["expects_sound"] = scenario["audio_expectation_policy"][
                            "expects_sound"
                        ]
                        result = lane.execute(stage, scenario, retry=attempt_index)
                        (stage / "ATTEMPT.json").write_text(
                            json.dumps(
                                {
                                    "attempt_id": attempt_id,
                                    "scenario": scenario,
                                    "build": str(build),
                                    "lane_index": lane_index,
                                    "port": port,
                                },
                                indent=2,
                                sort_keys=True,
                            )
                            + "\n"
                        )
                        result = formal.complete_formal_artifacts(result, scenario)
                        annotate_offline_replay_runtime(
                            result, scenario_offline_acceleration
                        )
                        admission = custom_admission(scenario, result)
                        manifest_row = publish_candidate(
                            output_root,
                            scenario,
                            result,
                            admission,
                            port,
                            lane_index,
                        )
                        results.append(manifest_row)
                                                                         
                                                                              
                                                               
                        try:
                            cleanup_episode_files(lane, result)
                            if stage.exists():
                                capture.clean_stage(stage)
                        except Exception as cleanup_exc:
                            print(
                                f"cleanup warning {scenario['episode_id']} "
                                f"reason={type(cleanup_exc).__name__}: "
                                f"{cleanup_exc}",
                                file=sys.stderr,
                                flush=True,
                            )
                        with WRITE_LOCK:
                            status = write_status(
                                output_root,
                                started,
                                total_rows,
                                "running",
                                accepted_at_start,
                            )
                            print(
                                f"accepted {scenario['episode_id']} "
                                f"category={scenario['primary_bucket']} "
                                f"total={status['accepted']}/{total_rows}",
                                flush=True,
                            )
                        break
                    except Exception as exc:
                        terminal = attempt_index + 1 >= max_attempts
                        preserve_reject(
                            output_root,
                            scenario,
                            attempt_id,
                            stage,
                            exc,
                            terminal,
                        )
                        print(
                            f"reject {attempt_id} reason="
                            f"{getattr(exc, 'reason', type(exc).__name__)} "
                            f"terminal={terminal}",
                            file=sys.stderr,
                            flush=True,
                        )
                                                                      
                                                                             
                                                                               
                                                           
                        if lane is not None:
                            lane.close()
                        if stage.exists():
                            safe_remove(stage, tmp_root / "raw")
                        safe_remove(lane_root, tmp_root / "resident")
                        if not terminal and not STOP.is_set():
                            lane = AcceleratedReusableStage1Lane(
                                lane_root,
                                build=build,
                                port=port,
                                offline_acceleration=offline_acceleration,
                            )
                            continue
                        break
        finally:
            if lane is not None:
                lane.close()
            safe_remove(lane_root, tmp_root / "resident")
    return results


def select_rows(
    rows: list[dict[str, Any]], selection: str, limit: int
) -> list[dict[str, Any]]:
    if selection == "all":
        selected = rows
    elif selection == "benchmark":
        selected = [
            row
            for row in rows
            if row["map"] == "xoylent" and row["gametype"] == "dm"
        ]
    elif selection == "smooth_route":
        selected = [
            row for row in rows if row["primary_bucket"] == "smooth_route"
        ]
    else:
        selected = [
            row for row in rows if row["primary_bucket"] == "idle_pure"
        ][:2]
        selected += [
            next(row for row in rows if row["primary_bucket"] == category)
            for category in (
                "idle_then_action",
                "action_then_idle",
                "action_idle_action",
            )
        ]
        selected += [
            next(
                row
                for row in rows
                if row["primary_bucket"] == "wall_impact" and row["map"] == map_name
            )
            for map_name in ("boil", "darkzone", "implosion", "xoylent")
        ]
        selected += [
            row for row in rows if row["primary_bucket"] == "smooth_route"
        ][:4]
    selected = sorted(selected, key=lambda row: int(row["candidate_ordinal"]))
    return selected[:limit] if limit > 0 else selected


def recover_published(output_root: Path) -> None:
    accepted_path = output_root / "manifests/accepted.jsonl"
    known = {row["episode_id"] for row in load_jsonl(accepted_path)}
    candidates = output_root / "candidates"
    if not candidates.is_dir():
        return
    for episode in sorted(candidates.iterdir()):
        if not episode.is_dir() or episode.name in known:
            continue
        record_path = episode / "supplement_candidate_record.json"
        ready_path = episode / "PUBLICATION_READY.json"
        if not record_path.is_file() or not ready_path.is_file():
            raise RuntimeError(f"incomplete published candidate: {episode}")
        record = json.loads(record_path.read_text())
        record["episode_path"] = str(episode)
        record["package_sha256"] = common.hash_tree(episode)
        record["recovered_utc"] = capture.utc_now()
        append_jsonl(accepted_path, record)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--port-base", type=int, default=27000)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument(
        "--selection",
        choices=("all", "smoke", "benchmark", "smooth_route"),
        default="all",
    )
    parser.add_argument(
        "--episode-id",
        action="append",
        default=[],
        help="Optionally restrict the selected design to exact episode IDs; repeatable.",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--x264-threads", type=int, default=8)
    parser.add_argument("--encode-concurrency", type=int, default=4)
    parser.add_argument(
        "--disable-offline-acceleration",
        action="store_true",
        help="validation-only baseline; production leaves acceleration enabled",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    offline_acceleration = not args.disable_offline_acceleration
    if not 1 <= args.workers <= 24:
        raise ValueError("workers must be in [1, 24]")
    capture.require_conda()
    if sha256_file(MANIFEST) != json.loads(DESIGN_AUDIT.read_text())[
        "manifest_sha256"
    ]:
        raise RuntimeError("design manifest hash mismatch")
    build = capture.build_root()
    if (build / "SOURCE_COMMIT").read_text().strip() != SOURCE_COMMIT:
        raise RuntimeError("runtime source commit mismatch")
    if (build / "QC_SOURCE_COMMIT").read_text().strip() != QC_SOURCE_COMMIT:
        raise RuntimeError("runtime QC source commit mismatch")
    for name, expected in QC_SHA256.items():
        if sha256_file(build / "qc" / name) != expected:
            raise RuntimeError(f"runtime QC hash mismatch: {name}")
    composition = json.loads(
        (build / "RUNTIME_COMPOSITION.json").read_text(encoding="utf-8")
    )
    if composition.get("engine_source_commit") != SOURCE_COMMIT:
        raise RuntimeError("runtime composition source commit mismatch")
    if (
        composition.get("offline_demo_fixedstep_patch_sha256")
        != OFFLINE_DEMO_PATCH_SHA256
    ):
        raise RuntimeError("runtime fixedstep patch mismatch")
    if (
        composition.get("offline_demo_acceleration_patch_sha256")
        != OFFLINE_DEMO_ACCELERATION_PATCH_SHA256
    ):
        raise RuntimeError("runtime acceleration patch mismatch")
    if (
        composition.get("offline_demo_acceleration_opt_in_cvar")
        != "cl_capturevideo_offline_accelerate"
    ):
        raise RuntimeError("runtime acceleration cvar mismatch")
    if sha256_file(RUNTIME_LOCK) != RUNTIME_LOCK_SHA256:
        raise RuntimeError("runtime lock hash mismatch")
    for line in RUNTIME_LOCK.read_text().splitlines():
        expected, relative = line.split(maxsplit=1)
        path = (ROOT / relative.strip()).resolve()
        if build.resolve() not in path.parents:
            raise RuntimeError(f"runtime lock path outside build: {path}")
        if sha256_file(path) != expected:
            raise RuntimeError(f"runtime lock entry mismatch: {path}")
    capture.validate_fixed_assets()
    os.environ["XONOTIC_X264_THREADS"] = str(args.x264_threads)
    os.environ["XONOTIC_ENCODE_CONCURRENCY"] = str(args.encode_concurrency)
    os.environ["XONOTIC_X264_CPUSET"] = ""
    os.environ["XONOTIC_RENDER_TIMEOUT_SECONDS"] = "240"
    os.environ["XONOTIC_RENDER_STARTUP_STALL_SECONDS"] = "60"
    os.environ["XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS"] = "120"
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifests").mkdir(exist_ok=True)
    tmp_root = capture.TMP_ROOT.resolve()
    (tmp_root / "raw").mkdir(parents=True, exist_ok=True)
    (tmp_root / "resident").mkdir(parents=True, exist_ok=True)
    recover_published(output_root)
    all_rows = load_jsonl(MANIFEST)
    selected = select_rows(all_rows, args.selection, args.limit)
    status_total_rows = len(selected)
    if args.episode_id:
        requested_ids = set(args.episode_id)
        known_ids = {row["episode_id"] for row in selected}
        unknown_ids = sorted(requested_ids - known_ids)
        if unknown_ids:
            raise ValueError(f"requested episode IDs are outside selection: {unknown_ids}")
        selected = [row for row in selected if row["episode_id"] in requested_ids]
    accepted_ids = {
        row["episode_id"]
        for row in load_jsonl(output_root / "manifests/accepted.jsonl")
    }
    accepted_at_start = len(accepted_ids)
    pending = [row for row in selected if row["episode_id"] not in accepted_ids]
    metadata = {
        "schema_version": "xonotic-stage1-supplement-run-v1",
        "pid": os.getpid(),
        "manifest": str(MANIFEST),
        "manifest_sha256": sha256_file(MANIFEST),
        "output_root": str(output_root),
        "tmp_root": str(tmp_root),
        "build": str(build),
        "source_commit": SOURCE_COMMIT,
        "offline_demo_fixedstep_patch_sha256": OFFLINE_DEMO_PATCH_SHA256,
        "offline_demo_acceleration": offline_acceleration,
        "offline_demo_acceleration_policy": (
            OFFLINE_ACCELERATION_POLICY
            if offline_acceleration
            else "disabled_ab_baseline"
        ),
        "offline_demo_acceleration_excluded_categories": (
            list(OFFLINE_ACCELERATION_EXCLUDED_CATEGORIES)
            if offline_acceleration
            else []
        ),
        "offline_demo_acceleration_cvar": (
            "cl_capturevideo_offline_accelerate"
        ),
        "offline_demo_acceleration_patch_sha256": (
            OFFLINE_DEMO_ACCELERATION_PATCH_SHA256
        ),
        "qc_source_commit": QC_SOURCE_COMMIT,
        "qc_sha256": QC_SHA256,
        "runtime_lock": str(RUNTIME_LOCK),
        "runtime_lock_sha256": RUNTIME_LOCK_SHA256,
        "workers": args.workers,
        "x264_threads": args.x264_threads,
        "encode_concurrency": args.encode_concurrency,
        "selection": args.selection,
        "episode_ids": sorted(args.episode_id),
        "selected_rows": len(selected),
        "status_target_rows": status_total_rows,
        "pending_rows": len(pending),
        "accepted_at_start": accepted_at_start,
        "training_admitted": False,
        "started_utc": capture.utc_now(),
    }
    run_path = output_root / "RUN.json"
    if run_path.exists():
        metadata["prior_run_metadata_sha256"] = sha256_file(run_path)
        resume_index = len(list(output_root.glob("RUN.resume-*.json"))) + 1
        run_path = output_root / f"RUN.resume-{resume_index:03d}.json"
    metadata["run_metadata_path"] = str(run_path)
    run_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    started = time.monotonic()

    def on_signal(signum: int, _frame: Any) -> None:
        print(f"received signal {signum}; draining lanes", flush=True)
        STOP.set()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    write_status(
        output_root,
        started,
        status_total_rows,
        "running",
        accepted_at_start,
    )
    plans = lane_plan(pending, min(args.workers, max(1, len(pending))))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plans)) as pool:
        futures = [
            pool.submit(
                run_lane,
                lane_index,
                groups,
                build=build,
                output_root=output_root,
                tmp_root=tmp_root,
                port=args.port_base + lane_index,
                max_attempts=args.max_attempts,
                started=started,
                total_rows=status_total_rows,
                accepted_at_start=accepted_at_start,
                offline_acceleration=offline_acceleration,
            )
            for lane_index, groups in enumerate(plans)
            if groups
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    accepted = load_jsonl(output_root / "manifests/accepted.jsonl")
    state = "stopped" if STOP.is_set() else (
        "complete" if len(accepted) >= status_total_rows else "incomplete"
    )
    status = write_status(
        output_root,
        started,
        status_total_rows,
        state,
        accepted_at_start,
    )
    print(json.dumps(status, indent=2, sort_keys=True), flush=True)
    return 0 if state in {"complete", "stopped"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
