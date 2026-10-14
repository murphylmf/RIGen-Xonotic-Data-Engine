                      
"""Run a warm-up -> A -> B -> A resident-lane isolation benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import xonotic_capture as capture
from xonotic_stage1_reusable import ReusableStage1Lane


ROOT = capture.ROOT
DEFAULT_A = (
    ROOT
    / "stage1_foundation_v4_random_review_100_output/episodes/"
    "s1v4_review100_100_s1f_059362"
)
DEFAULT_B = (
    ROOT
    / "stage1_foundation_v4_random_review_100_output/episodes/"
    "s1v4_review100_019_s1f_008564"
)
PARQUET_ARTIFACTS = (
    "actions.parquet",
    "model_actions.parquet",
    "states.parquet",
    "events.parquet",
    "frames.parquet",
    "audio_events.parquet",
    "target_relations.parquet",
    "enemy_path_trace.parquet",
)


def load_reference(path: Path) -> tuple[dict[str, Any], Path]:
    scenario_path = path / "episode.json"
    package = path
    if not scenario_path.is_file():
        raise capture.CaptureFailure(
            "resident_reference_scenario_missing", str(scenario_path)
        )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    if scenario.get("formal_collection_authorized") is not False:
        raise capture.CaptureFailure(
            "resident_reference_must_be_nontraining",
            str(scenario_path),
        )
    if scenario.get("training_admitted") is not False:
        raise capture.CaptureFailure(
            "resident_reference_training_forbidden",
            str(scenario_path),
        )
    return scenario, package


def decoded_hash(path: Path, *, stream: str) -> str:
    if stream == "video":
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-f",
            "framemd5",
            "-",
        ]
    elif stream == "audio":
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
            str(capture.AUDIO_RATE),
            "-ac",
            "2",
            "-",
        ]
    else:
        raise ValueError(stream)
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise capture.CaptureFailure(
            "resident_decode_hash_failed",
            completed.stderr.decode(errors="replace"),
        )
    return hashlib.sha256(completed.stdout).hexdigest()


def compare_frames(
    left: Path,
    right: Path,
) -> dict[str, Any]:
    compared: dict[str, Any] = {}
    passed = True
    for name in PARQUET_ARTIFACTS:
        left_path = left / name
        right_path = right / name
        if not left_path.is_file() and not right_path.is_file():
            continue
        present = left_path.is_file() and right_path.is_file()
        equal = False
        detail = ""
        if present:
            left_frame = pd.read_parquet(left_path)
            right_frame = pd.read_parquet(right_path)
            try:
                pd.testing.assert_frame_equal(
                    left_frame,
                    right_frame,
                    check_exact=True,
                    check_dtype=True,
                    check_like=False,
                )
                equal = True
            except AssertionError as exc:
                detail = str(exc)[:2000]
        compared[name] = {
            "both_present": present,
            "exact_semantic_match": equal,
            "detail": detail,
        }
        passed = passed and present and equal
    left_qa = json.loads(
        (left / "qa.json").read_text(encoding="utf-8")
    )
    right_qa = json.loads(
        (right / "qa.json").read_text(encoding="utf-8")
    )
    authoritative_equal = (
        left_qa["telemetry"]["authoritative_sha256"]
        == right_qa["telemetry"]["authoritative_sha256"]
    )
    video_equal = (
        decoded_hash(left / "video.mkv", stream="video")
        == decoded_hash(right / "video.mkv", stream="video")
    )
    audio_equal = (
        decoded_hash(left / "video.mkv", stream="audio")
        == decoded_hash(right / "video.mkv", stream="audio")
    )
    compared["authoritative_telemetry"] = {
        "exact_match": authoritative_equal,
    }
    compared["decoded_video"] = {"exact_match": video_equal}
    compared["decoded_audio"] = {"exact_match": audio_equal}
    passed = (
        passed
        and authoritative_equal
        and video_equal
        and audio_equal
    )
    return {"passed": passed, "artifacts": compared}


def _canonical_value(value: Any) -> Any:
    """Normalize Arrow/Pandas nested values without object-identity noise."""
    if isinstance(value, np.ndarray):
        return [_canonical_value(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical_value(value[key])
            for key in sorted(value)
        }
    if isinstance(value, np.generic):
        return _canonical_value(value.item())
    if isinstance(value, float) and np.isnan(value):
        return "__nan__"
    return value


def _canonical_dataframe_equal(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    excluded_columns: set[str] | None = None,
) -> tuple[bool, list[str]]:
    excluded = excluded_columns or set()
    if list(left.columns) != list(right.columns) or len(left) != len(right):
        return False, ["schema_or_row_count"]
    differing: list[str] = []
    for column in left.columns:
        if column in excluded:
            continue
        if any(
            _canonical_value(left_value)
            != _canonical_value(right_value)
            for left_value, right_value in zip(
                left[column], right[column], strict=True
            )
        ):
            differing.append(column)
    return not differing, differing


def _video_similarity(left: Path, right: Path) -> dict[str, Any]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-i",
        str(left),
        "-i",
        str(right),
        "-lavfi",
        "[0:v][1:v]psnr;[0:v][1:v]ssim",
        "-f",
        "null",
        "-",
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
    )
    psnr_match = re.search(
        r"PSNR .* average:([0-9.+-]+|inf)", completed.stdout
    )
    ssim_match = re.search(
        r"SSIM .* All:([0-9.+-]+)", completed.stdout
    )
    if (
        completed.returncode != 0
        or psnr_match is None
        or ssim_match is None
    ):
        raise capture.CaptureFailure(
            "resident_video_similarity_failed",
            completed.stdout[-4000:],
        )
    psnr = float(psnr_match.group(1))
    ssim = float(ssim_match.group(1))
    return {
        "psnr_db": psnr,
        "ssim": ssim,
        "minimum_psnr_db": 35.0,
        "minimum_ssim": 0.97,
        "passed": psnr >= 35.0 and ssim >= 0.97,
    }


def _frame_isolation(left: Path, right: Path) -> dict[str, Any]:
    left_frame = pd.read_parquet(left / "frames.parquet")
    right_frame = pd.read_parquet(right / "frames.parquet")
    if len(left_frame) != capture.OUTPUT_TICKS or len(right_frame) != len(
        left_frame
    ):
        return {
            "passed": False,
            "detail": "frame_count_or_schema_mismatch",
        }
    session_coordinates = {
        "client_time",
        "server_time_current",
        "server_time_previous",
        "server_tick",
        "interpolation",
        "camera_x",
        "camera_y",
        "camera_z",
        "forward_x",
        "forward_y",
        "forward_z",
        "left_x",
        "left_y",
        "left_z",
        "up_x",
        "up_y",
        "up_z",
        "m00",
        "m01",
        "m02",
        "m10",
        "m11",
        "m12",
        "m20",
        "m21",
        "m22",
        "m30",
        "m31",
        "m32",
    }
    core_equal, differing = _canonical_dataframe_equal(
        left_frame,
        right_frame,
        excluded_columns=session_coordinates,
    )
    translation_columns = ["camera_x", "camera_y", "camera_z"]
    translation_delta = np.asarray(
        left_frame[translation_columns], dtype=np.float64
    ) - np.asarray(right_frame[translation_columns], dtype=np.float64)
    maximum_translation_delta = float(
        np.max(np.linalg.norm(translation_delta, axis=1))
    )

    def local_translation_envelope(frame: pd.DataFrame) -> np.ndarray:
        positions = np.asarray(
            frame[translation_columns], dtype=np.float64
        )
        if len(positions) < 2:
            return np.zeros(len(positions), dtype=np.float64)
        adjacent = np.linalg.norm(np.diff(positions, axis=0), axis=1)
        envelope = np.zeros(len(positions), dtype=np.float64)
        envelope[:-1] = np.maximum(envelope[:-1], adjacent)
        envelope[1:] = np.maximum(envelope[1:], adjacent)
        return envelope

    translation_envelope = np.maximum(
        local_translation_envelope(left_frame),
        local_translation_envelope(right_frame),
    )
    left_forward = np.asarray(
        left_frame[["forward_x", "forward_y", "forward_z"]],
        dtype=np.float64,
    )
    right_forward = np.asarray(
        right_frame[["forward_x", "forward_y", "forward_z"]],
        dtype=np.float64,
    )
    forward_dot = np.sum(left_forward * right_forward, axis=1)
    forward_norm = np.linalg.norm(left_forward, axis=1) * np.linalg.norm(
        right_forward, axis=1
    )
    forward_cosine = np.clip(
        forward_dot / np.maximum(forward_norm, 1e-12), -1.0, 1.0
    )
    maximum_orientation_delta_degrees = float(
        np.max(np.degrees(np.arccos(forward_cosine)))
    )

    def local_orientation_envelope(frame: pd.DataFrame) -> np.ndarray:
        forward = np.asarray(
            frame[["forward_x", "forward_y", "forward_z"]],
            dtype=np.float64,
        )
        if len(forward) < 2:
            return np.zeros(len(forward), dtype=np.float64)
        dot = np.sum(forward[:-1] * forward[1:], axis=1)
        norm = np.linalg.norm(forward[:-1], axis=1) * np.linalg.norm(
            forward[1:], axis=1
        )
        cosine = np.clip(dot / np.maximum(norm, 1e-12), -1.0, 1.0)
        adjacent = np.degrees(np.arccos(cosine))
        envelope = np.zeros(len(forward), dtype=np.float64)
        envelope[:-1] = np.maximum(envelope[:-1], adjacent)
        envelope[1:] = np.maximum(envelope[1:], adjacent)
        return envelope

    orientation_envelope_degrees = np.maximum(
        local_orientation_envelope(left_frame),
        local_orientation_envelope(right_frame),
    )
    tick_equal = left_frame["episode_server_tick"].equals(
        right_frame["episode_server_tick"]
    )
    interpolation_left = np.asarray(
        left_frame["interpolation"], dtype=np.float64
    )
    interpolation_right = np.asarray(
        right_frame["interpolation"], dtype=np.float64
    )
    interpolation_valid = bool(
        np.all(np.isfinite(interpolation_left))
        and np.all(np.isfinite(interpolation_right))
        and np.all((interpolation_left >= 0) & (interpolation_left <= 1))
        and np.all((interpolation_right >= 0) & (interpolation_right <= 1))
    )
    maximum_interpolation_delta = float(
        np.max(np.abs(interpolation_left - interpolation_right))
    )
                                                                       
                                                                         
                                                                    
                                                                         
                                                                       
                                                                          
                                                                             
                                                                         
                                                                         
    translation_allowed = np.maximum(
        1.0, translation_envelope + 0.25
    )
    orientation_allowed_degrees = np.maximum(
        0.25, orientation_envelope_degrees + 0.05
    )
    translation_phase_bounded = bool(
        np.all(
            np.linalg.norm(translation_delta, axis=1)
            <= translation_allowed
        )
    )
    orientation_delta_degrees = np.degrees(
        np.arccos(forward_cosine)
    )
    orientation_phase_bounded = bool(
        np.all(
            orientation_delta_degrees <= orientation_allowed_degrees
        )
    )
    return {
        "passed": (
            core_equal
            and tick_equal
            and interpolation_valid
            and translation_phase_bounded
            and orientation_phase_bounded
        ),
        "core_exact": core_equal,
        "core_differing_columns": differing,
        "episode_server_tick_exact": tick_equal,
        "interpolation_fraction_valid": interpolation_valid,
        "maximum_interpolation_fraction_delta": (
            maximum_interpolation_delta
        ),
        "maximum_camera_translation_delta_units": (
            maximum_translation_delta
        ),
        "maximum_adjacent_camera_translation_units": (
            float(np.max(translation_envelope))
        ),
        "maximum_camera_translation_delta_allowed_units": (
            float(np.max(translation_allowed))
        ),
        "camera_translation_phase_bounded": translation_phase_bounded,
        "maximum_camera_orientation_delta_degrees": (
            maximum_orientation_delta_degrees
        ),
        "maximum_adjacent_camera_orientation_degrees": (
            float(np.max(orientation_envelope_degrees))
        ),
        "maximum_camera_orientation_delta_allowed_degrees": (
            float(np.max(orientation_allowed_degrees))
        ),
        "camera_orientation_phase_bounded": orientation_phase_bounded,
        "camera_phase_envelope_frames": 1,
        "camera_phase_comparison_scope": (
            "independently live-recorded deterministic episodes"
        ),
        "camera_phase_policy": (
            "same episode tick; valid interpolation fraction; pose delta "
            "within one observed output-frame motion envelope"
        ),
    }


def _interaction_audio_isolation(
    left: Path,
    right: Path,
) -> dict[str, Any]:
    columns = [
        "server_tick",
        "source_entity",
        "source_channel",
        "episode_mixer_sample_cursor",
        "sample_name",
    ]

    def interaction_rows(path: Path) -> pd.DataFrame:
        frame = pd.read_parquet(path / "audio_events.parquet")
        movement_random = frame["sample_name"].str.contains(
            r"(?:footstep|hitground)", case=False, regex=True
        )
        return frame.loc[~movement_random, columns].reset_index(drop=True)

    left_frame = interaction_rows(left)
    right_frame = interaction_rows(right)
    exact = left_frame.equals(right_frame)
    return {
        "passed": exact,
        "interaction_events_exact": exact,
        "left_interaction_event_count": len(left_frame),
        "right_interaction_event_count": len(right_frame),
        "excluded_native_random_movement_sfx": (
            "footstep and hitground variants/cadence"
        ),
    }


def _foreign_episode_references(
    stage: Path,
    foreign_episode_id: str,
) -> list[str]:
    matches: list[str] = []
    allowed_suffixes = {
        ".cfg",
        ".csv",
        ".json",
        ".jsonl",
        ".log",
        ".txt",
    }
    expected = foreign_episode_id.encode()
    for path in sorted(stage.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue
        if expected in path.read_bytes():
            matches.append(str(path.relative_to(stage)))
    return matches


def compare_isolation(
    left: Path,
    right: Path,
    *,
    left_stage: Path,
    right_stage: Path,
    foreign_episode_id: str,
) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    left_qa = json.loads((left / "qa.json").read_text(encoding="utf-8"))
    right_qa = json.loads((right / "qa.json").read_text(encoding="utf-8"))
    authoritative_equal = (
        left_qa["telemetry"]["authoritative_sha256"]
        == right_qa["telemetry"]["authoritative_sha256"]
    )
    artifacts["authoritative_telemetry"] = {
        "passed": authoritative_equal,
        "exact": authoritative_equal,
    }
    for name in (
        "model_actions.parquet",
        "states.parquet",
        "events.parquet",
        "enemy_path_trace.parquet",
    ):
        left_frame = pd.read_parquet(left / name)
        right_frame = pd.read_parquet(right / name)
        equal, differing = _canonical_dataframe_equal(
            left_frame, right_frame
        )
        artifacts[name] = {
            "passed": equal,
            "canonical_exact": equal,
            "differing_columns": differing,
        }
    left_actions = pd.read_parquet(left / "actions.parquet")
    right_actions = pd.read_parquet(right / "actions.parquet")
    action_equal, action_differing = _canonical_dataframe_equal(
        left_actions,
        right_actions,
        excluded_columns={"cmd_sequence", "cmd_time"},
    )
    action_sequences_valid = bool(
        np.all(np.diff(left_actions["cmd_sequence"]) == 1)
        and np.all(np.diff(right_actions["cmd_sequence"]) == 1)
    )
    artifacts["actions.parquet"] = {
        "passed": action_equal and action_sequences_valid,
        "engine_action_content_exact": action_equal,
        "differing_content_columns": action_differing,
        "transport_sequence_consecutive": action_sequences_valid,
        "excluded_session_transport_coordinates": [
            "cmd_sequence",
            "cmd_time",
        ],
    }
    artifacts["frames.parquet"] = _frame_isolation(left, right)
    artifacts["interaction_audio"] = _interaction_audio_isolation(
        left, right
    )
    artifacts["decoded_video_similarity"] = _video_similarity(
        left / "video.mkv", right / "video.mkv"
    )
    foreign_paths = sorted(
        set(
            _foreign_episode_references(
                left_stage, foreign_episode_id
            )
            + _foreign_episode_references(
                right_stage, foreign_episode_id
            )
        )
    )
    artifacts["foreign_episode_reference_scan"] = {
        "passed": not foreign_paths,
        "foreign_episode_id": foreign_episode_id,
        "matching_paths": foreign_paths,
    }
    artifacts["individual_existing_qa"] = {
        "passed": bool(left_qa["accepted"] and right_qa["accepted"]),
        "left_accepted": bool(left_qa["accepted"]),
        "right_accepted": bool(right_qa["accepted"]),
    }
    return {
        "passed": all(row["passed"] for row in artifacts.values()),
        "artifacts": artifacts,
    }


def runtime_row(
    label: str,
    result: dict[str, Any],
    wall_seconds: float,
) -> dict[str, Any]:
    runtime = result["qa"]["runtime"]
    return {
        "label": label,
        "episode_id": result["episode_id"],
        "wall_seconds": wall_seconds,
        "live_wall_seconds": runtime["live_wall_seconds"],
        "render_wall_seconds": runtime["render_wall_seconds"],
        "encode_wall_seconds": runtime["encode_wall_seconds"],
        "resident": runtime["resident_lane"],
    }


def command_run(args: argparse.Namespace) -> int:
    capture.require_conda()
    output = Path(args.output_root).resolve()
    if output.exists():
        raise capture.CaptureFailure(
            "resident_benchmark_output_exists", str(output)
        )
    output.mkdir(parents=True)
    build = Path(args.build).resolve()
    scenario_a, reference_a = load_reference(
        Path(args.reference_a).resolve()
    )
    scenario_b, _ = load_reference(Path(args.reference_b).resolve())
    if (
        scenario_a["map"] != scenario_b["map"]
        or scenario_a["gametype"] != scenario_b["gametype"]
    ):
        raise capture.CaptureFailure(
            "resident_benchmark_requires_same_world",
            f"A={scenario_a['map']}/{scenario_a['gametype']} "
            f"B={scenario_b['map']}/{scenario_b['gametype']}",
        )
    if scenario_a["episode_id"] == scenario_b["episode_id"]:
        raise capture.CaptureFailure(
            "resident_benchmark_requires_distinct_scenarios"
        )
    attempts = output / "attempts"
    attempts.mkdir()
    results: dict[str, dict[str, Any]] = {}
    runtime: list[dict[str, Any]] = []
    with ReusableStage1Lane(
        output / "lane",
        build=build,
        port=args.port,
    ) as lane:
        for label, scenario in (
            ("warmup_discarded", scenario_a),
            ("a_before", scenario_a),
            ("b_intervening", scenario_b),
            ("a_after", scenario_a),
        ):
            stage = attempts / label
            started_unix_seconds = time.time()
            started = time.monotonic()
            result = lane.execute(stage, scenario)
            wall_seconds = time.monotonic() - started
            finished_unix_seconds = time.time()
            results[label] = result
            row = runtime_row(label, result, wall_seconds)
            row["started_unix_seconds"] = started_unix_seconds
            row["finished_unix_seconds"] = finished_unix_seconds
            runtime.append(row)
            print(
                f"resident accepted {label} "
                f"episode={scenario['episode_id']} "
                f"wall={wall_seconds:.3f}s",
                flush=True,
            )
        startup = dict(lane.process_startup_seconds)

    a_before = Path(results["a_before"]["package_stage"])
    a_after = Path(results["a_after"]["package_stage"])
    warm_repeat = compare_frames(a_before, a_after)
    isolation_admission = compare_isolation(
        a_before,
        a_after,
        left_stage=attempts / "a_before",
        right_stage=attempts / "a_after",
        foreign_episode_id=scenario_b["episode_id"],
    )
    cold_to_before = compare_frames(reference_a, a_before)
    cold_to_after = compare_frames(reference_a, a_after)
    cold_qa = json.loads(
        (reference_a / "qa.json").read_text(encoding="utf-8")
    )
    cold_runtime = cold_qa["runtime"]
    steady = runtime[1:]
    cold_component_seconds = sum(
        float(cold_runtime[name])
        for name in (
            "live_wall_seconds",
            "render_wall_seconds",
            "encode_wall_seconds",
        )
    )
    steady_wall_mean = sum(
        float(row["wall_seconds"]) for row in steady
    ) / len(steady)
    report = {
        "schema_version": "xonotic-stage1-resident-lane-benchmark-v3",
        "created_utc": capture.utc_now(),
        "pass": isolation_admission["passed"]
        and all(row["qa"]["accepted"] for row in results.values()),
        "strict_replay_byte_identity_pass": (
            warm_repeat["passed"]
            and cold_to_before["passed"]
            and cold_to_after["passed"]
        ),
        "isolation_admission": isolation_admission,
        "formal_worker_enabled": False,
        "training_admitted": False,
        "isolation_policy": {
            "first_episode_is_nontraining_discarded_warmup": True,
            "process_cache_reused": True,
            "server_world_reset_each_episode": True,
            "same_map_reset_command": "restart",
            "live_client_disconnect_each_episode": True,
            "demo_playback_client_reset_each_episode": True,
            "unique_episode_artifact_paths": True,
            "soft_entity_reset": False,
        },
        "scenarios": {
            "a": scenario_a["episode_id"],
            "b": scenario_b["episode_id"],
            "map": scenario_a["map"],
            "gametype": scenario_a["gametype"],
        },
        "process_startup_seconds": startup,
        "runtime": runtime,
        "cold_reference": {
            "episode_id": scenario_a["episode_id"],
            "component_seconds": cold_component_seconds,
            "runtime": cold_runtime,
        },
        "steady_state": {
            "mean_end_to_end_wall_seconds": steady_wall_mean,
            "episodes_per_hour_per_lane": 3600.0 / steady_wall_mean,
            "speedup_vs_cold_components": (
                cold_component_seconds / steady_wall_mean
            ),
        },
        "comparisons": {
            "resident_a_before_vs_a_after": warm_repeat,
            "cold_a_vs_resident_a_before": cold_to_before,
            "cold_a_vs_resident_a_after": cold_to_after,
        },
    }
    (output / "RESULT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument(
        "--output-root",
        required=True,
    )
    result.add_argument(
        "--build",
        default=str(
            ROOT / "build/capture-b40e26fd4e33-x86_64"
        ),
    )
    result.add_argument("--reference-a", default=str(DEFAULT_A))
    result.add_argument("--reference-b", default=str(DEFAULT_B))
    result.add_argument("--port", type=int, default=39_200)
    result.set_defaults(func=command_run)
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    raise SystemExit(arguments.func(arguments))
