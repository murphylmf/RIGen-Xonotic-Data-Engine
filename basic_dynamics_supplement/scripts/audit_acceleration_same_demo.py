                      
"""Replay identical Stage-1 demos with pacing off/on and compare outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_CAPTURE_TMP", "./tmp/xonotic-stage1-supplement-v1"
)
os.environ.setdefault(
    "XONOTIC_CONDA_PREFIX_REQUIRED",
    "./environment",
)
os.environ.setdefault(
    "XONOTIC_BUILD_GLOB",
    "build/capture-858ad1f142b0-qc7e8310-aarch64",
)
sys.path.insert(0, str(ROOT / "scripts"))

import run_supplement as supplement              


DEFAULT_SOURCE = (
    ROOT / "outputs/acceleration_ab_baseline_v1/candidates"
)
DEFAULT_EPISODES = (
    "s1sup_tr_idle_000001",
    "s1sup_tr_a2i_003251",
    "s1sup_tr_imp_004217",
)
RENDER_VARIANTS = (
    ("paced_a", False),
    ("accelerated", True),
    ("paced_b", False),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decoded_video(path: Path) -> dict[str, Any]:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    if process.stdout is None:
        raise RuntimeError("ffmpeg video stdout unavailable")
    digest = hashlib.sha256()
    byte_count = 0
    for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
        digest.update(chunk)
        byte_count += len(chunk)
    if process.wait() != 0:
        raise RuntimeError(f"decoded video failed: {path}")
    bytes_per_frame = supplement.capture.WIDTH * supplement.capture.HEIGHT * 3
    if byte_count % bytes_per_frame:
        raise RuntimeError(f"partial decoded video frame: {path}")
    return {
        "sha256_rgb24": digest.hexdigest(),
        "decoded_bytes": byte_count,
        "frames": byte_count // bytes_per_frame,
    }


def decoded_audio(
    path: Path, window_start: int
) -> tuple[dict[str, Any], np.ndarray]:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "pipe:1",
    ]
    payload = subprocess.check_output(command)
    samples = np.frombuffer(payload, dtype="<i2").copy()
    channels = 2
    if samples.size % channels:
        raise RuntimeError(f"partial decoded audio sample: {path}")
    samples = samples.reshape(-1, channels)
    window_end = window_start + supplement.capture.AUDIO_SAMPLES
    if samples.shape[0] < window_end:
        raise RuntimeError(
            f"canonical audio window unavailable: {path} "
            f"samples={samples.shape[0]} end={window_end}"
        )
    window = samples[window_start:window_end].copy()
    return (
        {
            "raw_sha256_s16le": hashlib.sha256(payload).hexdigest(),
            "raw_decoded_bytes": len(payload),
            "channels": channels,
            "raw_samples_per_channel": int(samples.shape[0]),
            "canonical_window_start_sample": window_start,
            "canonical_samples_per_channel": int(window.shape[0]),
            "canonical_sha256_s16le": hashlib.sha256(
                window.astype("<i2", copy=False).tobytes()
            ).hexdigest(),
        },
        window.reshape(-1),
    )


def first_frame_audio_cursor(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    return int(float(row["mixer_audio_cursor_at_frame"]))


def semantic_audio_events_sha256(path: Path) -> str:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
                                                                         
                                                                           
                                                                     
        if row.get("source_channel") == "-4":
            row["source_entity"] = "temporary_effect"
    payload = json.dumps(
        rows, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def audio_metrics(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    if left.shape != right.shape:
        return {
            "same_shape": False,
            "left_samples": int(left.size),
            "right_samples": int(right.size),
        }
    delta = left.astype(np.float64) - right.astype(np.float64)
    rmse = float(np.sqrt(np.mean(np.square(delta))))
    signal_rms = float(
        np.sqrt(np.mean(np.square(left.astype(np.float64))))
    )
    peak = 32768.0
    psnr = 999.0 if rmse == 0.0 else 20.0 * math.log10(peak / rmse)
    if rmse == 0.0:
        snr = 999.0
    elif signal_rms == 0.0:
        snr = -999.0
    else:
        snr = 20.0 * math.log10(signal_rms / rmse)
    return {
        "same_shape": True,
        "exact": bool(np.array_equal(left, right)),
        "max_abs_sample_delta": int(np.max(np.abs(delta), initial=0.0)),
        "rmse": rmse,
        "psnr_db": psnr,
        "reference_signal_rms": signal_rms,
        "snr_db": snr,
    }


def video_ssim(left: Path, right: Path) -> float:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(left),
        "-i",
        str(right),
        "-lavfi",
        "[0:v][1:v]ssim",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    matches = re.findall(r"All:([0-9.]+)", result.stderr)
    if not matches:
        raise RuntimeError("ffmpeg SSIM result missing")
    return float(matches[-1])


def compare_pair(
    left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    left_path = Path(left["raw_avi"])
    right_path = Path(right["raw_avi"])
    return {
        "decoded_video_exact": (
            left["video"]["sha256_rgb24"]
            == right["video"]["sha256_rgb24"]
        ),
        "video_ssim_all": video_ssim(left_path, right_path),
        "decoded_audio": audio_metrics(
            left["audio_samples"], right["audio_samples"]
        ),
        "frames_engine_exact": (
            left["frames_engine_sha256"]
            == right["frames_engine_sha256"]
        ),
        "audio_events_engine_exact": (
            left["audio_events_engine_sha256"]
            == right["audio_events_engine_sha256"]
        ),
        "audio_events_engine_semantic_exact": (
            left["audio_events_engine_semantic_sha256"]
            == right["audio_events_engine_semantic_sha256"]
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--port", type=int, default=29700)
    parser.add_argument(
        "--episodes", nargs="+", default=list(DEFAULT_EPISODES)
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    source_root = args.source_root.resolve()
    output_root.mkdir(parents=True, exist_ok=False)
    lane_root = output_root / "resident_lane"
    build = supplement.capture.build_root()
    started = time.monotonic()
    report: dict[str, Any] = {
        "schema_version": "xonotic-stage1-acceleration-same-demo-audit-v2",
        "source_root": str(source_root),
        "output_root": str(output_root),
        "runtime": str(build),
        "source_commit": supplement.SOURCE_COMMIT,
        "runtime_lock_sha256": supplement.RUNTIME_LOCK_SHA256,
        "acceleration_patch_sha256": (
            supplement.OFFLINE_DEMO_ACCELERATION_PATCH_SHA256
        ),
        "render_order": [name for name, _ in RENDER_VARIANTS],
        "episodes": {},
        "training_admitted": False,
    }
    lane = supplement.AcceleratedReusableStage1Lane(
        lane_root,
        build=build,
        port=args.port,
        offline_acceleration=False,
    )
    try:
        lane._start_clients()
        lane.sequence = 1
        for episode_id in args.episodes:
            source = source_root / episode_id
            scenario_path = source / "episode.json"
            demo_path = source / "capture_provenance/demo.dem"
            if not scenario_path.is_file() or not demo_path.is_file():
                raise FileNotFoundError(f"missing source episode: {source}")
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            if scenario.get("episode_id") != episode_id:
                raise RuntimeError(f"episode id mismatch: {scenario_path}")
            case_root = output_root / "cases" / episode_id
            case_root.mkdir(parents=True)
            variants: dict[str, dict[str, Any]] = {}
            for label, enabled in RENDER_VARIANTS:
                stage = case_root / label
                stage.mkdir()
                lane.offline_acceleration = enabled
                live = {
                    "demo_name": f"audit_{episode_id}_{label}",
                    "demo_path": demo_path,
                    "resident_token": f"audit_{episode_id}_{label}",
                }
                rendered = lane.run_render(stage, scenario, live)
                preflight = Path(
                    rendered["offline_demo_acceleration_preflight"]
                )
                realized = "1" if enabled else "0"
                preflight_text = preflight.read_text(errors="replace")
                cvar_proved = (
                    f'"cl_capturevideo_offline_accelerate" is "{realized}"'
                    in preflight_text
                    and '"cl_capturevideo_realtime" is "0"'
                    in preflight_text
                )
                raw_avi = Path(rendered["raw_avi"])
                video = decoded_video(raw_avi)
                frames_engine = Path(rendered["frames_engine"])
                audio_events_engine = Path(rendered["audio_events_engine"])
                audio, samples = decoded_audio(
                    raw_avi, first_frame_audio_cursor(frames_engine)
                )
                variants[label] = {
                    "offline_acceleration": enabled,
                    "cvar_proved": cvar_proved,
                    "raw_avi": str(raw_avi),
                    "raw_avi_sha256": sha256_file(raw_avi),
                    "render_wall_seconds": rendered["render_wall_seconds"],
                    "video": video,
                    "audio": audio,
                    "audio_samples": samples,
                    "frames_engine_sha256": sha256_file(frames_engine),
                    "audio_events_engine_sha256": sha256_file(
                        audio_events_engine
                    ),
                    "audio_events_engine_semantic_sha256": (
                        semantic_audio_events_sha256(
                            audio_events_engine
                        )
                    ),
                }
            comparisons = {
                "paced_a_vs_accelerated": compare_pair(
                    variants["paced_a"], variants["accelerated"]
                ),
                "paced_b_vs_accelerated": compare_pair(
                    variants["paced_b"], variants["accelerated"]
                ),
                "paced_repeat": compare_pair(
                    variants["paced_a"], variants["paced_b"]
                ),
            }
            serializable_variants: dict[str, dict[str, Any]] = {}
            for label, variant in variants.items():
                serializable_variants[label] = {
                    key: value
                    for key, value in variant.items()
                    if key != "audio_samples"
                }
            report["episodes"][episode_id] = {
                "category": scenario.get("primary_bucket"),
                "map": scenario.get("map"),
                "weapon": scenario.get("weapon"),
                "source_demo_sha256": sha256_file(demo_path),
                "variants": serializable_variants,
                "comparisons": comparisons,
            }
            print(
                f"audited {episode_id} "
                f"ssim={comparisons['paced_a_vs_accelerated']['video_ssim_all']:.6f}",
                flush=True,
            )
    finally:
        lane.close()

    episodes = list(report["episodes"].values())
    all_variants = [
        variant
        for episode in episodes
        for variant in episode["variants"].values()
    ]
    accelerated_pairs = [
        episode["comparisons"][name]
        for episode in episodes
        for name in (
            "paced_a_vs_accelerated",
            "paced_b_vs_accelerated",
        )
    ]
    report["summary"] = {
        "episode_count": len(episodes),
        "render_count": len(all_variants),
        "all_cvars_proved": all(
            variant["cvar_proved"] for variant in all_variants
        ),
        "all_frame_counts_exact": all(
            variant["video"]["frames"] == supplement.capture.OUTPUT_TICKS
            for variant in all_variants
        ),
        "all_canonical_audio_sample_counts_exact": all(
            variant["audio"]["canonical_samples_per_channel"]
            == supplement.capture.AUDIO_SAMPLES
            for variant in all_variants
        ),
        "all_raw_audio_windows_cover_canonical": all(
            variant["audio"]["raw_samples_per_channel"]
            >= (
                variant["audio"]["canonical_window_start_sample"]
                + supplement.capture.AUDIO_SAMPLES
            )
            for variant in all_variants
        ),
        "all_engine_frame_tables_exact": all(
            pair["frames_engine_exact"] for pair in accelerated_pairs
        ),
        "all_engine_audio_event_semantics_exact": all(
            pair["audio_events_engine_semantic_exact"]
            for pair in accelerated_pairs
        ),
        "minimum_accelerated_pair_ssim": min(
            pair["video_ssim_all"] for pair in accelerated_pairs
        ),
        "minimum_accelerated_pair_audio_psnr_db": min(
            pair["decoded_audio"]["psnr_db"] for pair in accelerated_pairs
        ),
        "elapsed_seconds": time.monotonic() - started,
        "semantic_validation_passed": all(
            (
                pair["frames_engine_exact"]
                and pair["audio_events_engine_semantic_exact"]
                and pair["video_ssim_all"] >= 0.99
                and pair["decoded_audio"]["same_shape"]
                and pair["decoded_audio"]["psnr_db"] >= 50.0
            )
            for pair in accelerated_pairs
        ),
    }
    report_path = output_root / "REPORT.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0 if report["summary"]["semantic_validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
