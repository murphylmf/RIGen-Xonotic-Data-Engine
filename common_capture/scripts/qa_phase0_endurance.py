                      
"""Validate and summarize a completed Phase 0 endurance artifact."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np


(
    encoded_text,
    expected_frames_text,
    expected_samples_text,
    started_text,
    finished_text,
    metrics_text,
    audio_csv_text,
    output_text,
    run_id,
) = sys.argv[1:]
encoded = Path(encoded_text)
expected_frames = int(expected_frames_text)
expected_samples = int(expected_samples_text)
output = Path(output_text)


def command_json(command: list[str]) -> dict:
    completed = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    return json.loads(completed.stdout)


probe = command_json(
    [
        "ffprobe",
        "-v",
        "error",
        "-count_frames",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(encoded),
    ]
)
video = next(row for row in probe["streams"] if row["codec_type"] == "video")
audio = next(row for row in probe["streams"] if row["codec_type"] == "audio")
frames_probe = command_json(
    [
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
        str(encoded),
    ]
)
keyframes = [
    int(frame["coded_picture_number"])
    for frame in frames_probe["frames"]
    if int(frame.get("key_frame", 0)) == 1
]
pcm = subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-i",
        str(encoded),
        "-map",
        "0:a:0",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-",
    ],
    capture_output=True,
    check=True,
).stdout
samples = len(pcm) // 4
pcm_s16 = np.frombuffer(pcm, dtype="<i2")
peak_s16 = int(np.abs(pcm_s16.astype(np.int32)).max()) if pcm_s16.size else 0
rms_s16 = (
    float(np.sqrt(np.mean(pcm_s16.astype(np.float64) ** 2)))
    if pcm_s16.size
    else 0.0
)
nonzero_fraction = (
    float(np.count_nonzero(pcm_s16) / pcm_s16.size)
    if pcm_s16.size
    else 0.0
)

with Path(metrics_text).open(encoding="utf-8") as handle:
    metrics_rows = list(csv.DictReader(handle))
raw_sizes = [
    int(float(row["raw_bytes"]))
    for row in metrics_rows
    if row.get("raw_bytes")
]
gpu_values = [
    float(row["gpu_util_pct"])
    for row in metrics_rows
    if row.get("gpu_util_pct")
]
cpu_values = [
    float(row["engine_cpu_pct"])
    for row in metrics_rows
    if row.get("engine_cpu_pct")
]

with Path(audio_csv_text).open(encoding="utf-8") as handle:
    audio_rows = list(csv.DictReader(handle))
forbidden_patterns = (
    "announcer/",
    "cdtracks/",
    "music/",
    "misc/itemrespawncountdown.wav",
    "misc/talk",
)
forbidden = sorted(
    {
        row["sample_name"]
        for row in audio_rows
        if any(
            pattern in row["sample_name"].lower()
            for pattern in forbidden_patterns
        )
    }
)
onset_errors = [
    abs(
        int(row["waveform_onset_cursor"])
        - int(row["mixer_sample_cursor"])
    )
    for row in audio_rows
    if int(row["waveform_onset_cursor"]) >= 0
]

wall = float(finished_text) - float(started_text)
duration = expected_frames / 64.0
audio_duration = samples / 48000.0
expected_keyframes = list(range(0, expected_frames, 64))
positive_raw_rows = [value for value in raw_sizes if value > 0]
raw_write_seconds = max(1, len(positive_raw_rows) - 1)
raw_write_mib_s = (
    (max(positive_raw_rows) - min(positive_raw_rows))
    / (1024 * 1024)
    / raw_write_seconds
    if positive_raw_rows
    else 0.0
)
qa = {
    "schema_version": "xonotic-phase0-endurance-v1",
    "run_id": run_id,
    "renderer_required": "NVIDIA hardware (exact device recorded at runtime)",
    "video_frames": int(video["nb_read_frames"]),
    "video_fps": video["avg_frame_rate"],
    "video_duration_seconds": duration,
    "audio_samples_per_channel": samples,
    "audio_duration_seconds": audio_duration,
    "audio_peak_s16": peak_s16,
    "audio_rms_s16": rms_s16,
    "audio_nonzero_fraction": nonzero_fraction,
    "av_drift_ms": abs(duration - audio_duration) * 1000.0,
    "encoded": {
        "video_codec": video["codec_name"],
        "profile": video["profile"],
        "pixel_format": video["pix_fmt"],
        "audio_codec": audio["codec_name"],
        "audio_sample_format": audio["sample_fmt"],
        "audio_sample_rate": int(audio["sample_rate"]),
        "audio_channels": int(audio["channels"]),
        "keyframes": keyframes,
    },
    "audio_events": len(audio_rows),
    "audio_onset_events_measured": len(onset_errors),
    "max_audio_onset_error_samples": max(onset_errors, default=0),
    "max_audio_onset_error_ms": max(onset_errors, default=0)
    * 1000.0
    / 48000.0,
    "forbidden_audio_samples": forbidden,
    "raw_bytes_final": max(raw_sizes) if raw_sizes else 0,
    "raw_write_mib_s": raw_write_mib_s,
    "gpu_util_pct_mean": (
        float(np.mean(gpu_values)) if gpu_values else None
    ),
    "gpu_util_pct_max": max(gpu_values, default=None),
    "engine_cpu_pct_mean": (
        float(np.mean(cpu_values)) if cpu_values else None
    ),
    "engine_cpu_pct_max": max(cpu_values, default=None),
    "x264_wall_seconds": wall,
    "x264_video_seconds_per_wall_second": duration / wall,
    "gates": {
        "frames_exact": int(video["nb_read_frames"]) == expected_frames,
        "audio_samples_exact": samples == expected_samples,
        "samples_per_frame_exact": (
            samples == int(video["nb_read_frames"]) * 750
        ),
        "av_drift_zero": math.isclose(
            duration, audio_duration, abs_tol=1e-9
        ),
        "h264_high_yuv420p_cfr64": (
            video["codec_name"] == "h264"
            and video["profile"] == "High"
            and video["pix_fmt"] == "yuv420p"
            and video["avg_frame_rate"] == "64/1"
        ),
        "gop64": keyframes == expected_keyframes,
        "flac_s16_stereo_48khz": (
            audio["codec_name"] == "flac"
            and audio["sample_fmt"] == "s16"
            and int(audio["sample_rate"]) == 48000
            and int(audio["channels"]) == 2
        ),
        "audio_policy": not forbidden,
        "interactive_audio_non_silent": (
            peak_s16 > 0 and len(audio_rows) > 0
        ),
        "audio_onset_within_2ms": (
            bool(onset_errors) and max(onset_errors) <= 96
        ),
    },
}
output.write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n")
print(json.dumps(qa, indent=2, sort_keys=True))
if not all(qa["gates"].values()):
    raise SystemExit("endurance QA failed: " + str(output))
