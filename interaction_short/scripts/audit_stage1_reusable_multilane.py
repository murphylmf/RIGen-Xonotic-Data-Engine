                      
"""Independently audit every QA and raw frame trace in a multilane benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def gpu_profile(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    utilization: list[float] = []
    memory: list[float] = []
    power: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            utilization.append(
                float(row[" utilization.gpu [%]"].replace("%", ""))
            )
            memory.append(
                float(row[" memory.used [MiB]"].replace("MiB", ""))
            )
            power.append(float(row[" power.draw [W]"].replace("W", "")))
    return {
        "path": str(path),
        "samples": len(utilization),
        "mean_utilization_percent": (
            sum(utilization) / len(utilization) if utilization else 0.0
        ),
        "maximum_utilization_percent": max(utilization, default=0.0),
        "fraction_samples_at_least_90_percent": (
            sum(value >= 90 for value in utilization) / len(utilization)
            if utilization
            else 0.0
        ),
        "maximum_memory_mib": max(memory, default=0.0),
        "maximum_power_watts": max(power, default=0.0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", required=True)
    parser.add_argument("--gpu-log")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.benchmark_root).resolve()
    result = load_json(root / "RESULT.json")
    lane_result_paths = [
        Path(path) for path in result.get("lane_result_paths", [])
    ]
    qa_paths = sorted(root.glob("lane-*/attempts/*/package/qa.json"))
    frame_paths = sorted(root.glob("lane-*/attempts/*/render/frames_engine.csv"))
    failures: list[dict[str, Any]] = []

    def require(condition: bool, check: str, detail: Any = None) -> None:
        if not condition:
            failures.append({"check": check, "detail": detail})

    lanes = int(result["lanes"])
    expected_attempts = lanes * 4
    require(result.get("pass") is True, "batch_pass", result.get("pass"))
    require(
        len(lane_result_paths) == lanes,
        "lane_result_count",
        len(lane_result_paths),
    )
    missing_lane_results = [
        str(path) for path in lane_result_paths if not path.is_file()
    ]
    require(
        not missing_lane_results,
        "lane_result_files_exist",
        missing_lane_results,
    )
    lane_results = [
        load_json(path) for path in lane_result_paths if path.is_file()
    ]
    require(
        len(lane_results) == lanes
        and all(row.get("pass") is True for row in lane_results),
        "all_lane_results_pass",
    )
    require(
        len(qa_paths) == expected_attempts,
        "qa_file_count",
        len(qa_paths),
    )
    require(
        len(frame_paths) == expected_attempts,
        "raw_frame_file_count",
        len(frame_paths),
    )

    renderers: set[str] = set()
    tick_ranges: set[tuple[int, int]] = set()
    video_frames: set[int] = set()
    audio_samples: set[int] = set()
    mapping_rates: set[float] = set()
    maximum_interpolation = 0.0
    maximum_client_previous_error = 0.0
    frame_discontinuities = 0
    for qa_path in qa_paths:
        qa = load_json(qa_path)
        video = qa.get("video", {})
        audio = qa.get("audio", {})
        mapping = qa.get("mapping", {})
        phase = mapping.get("presentation_phase", {})
        mode = qa.get("mode", {})
        hud = qa.get("hud", {})
        runtime = qa.get("runtime", {})
        checks = {
            "accepted": qa.get("accepted") is True,
            "capture_valid": qa.get("capture_valid") is True,
            "hard_failures_empty": qa.get("hard_failures") == [],
            "all_hard_gates": bool(qa.get("hard_gates"))
            and all(qa["hard_gates"].values()),
            "video_frames": video.get("frames") == 320,
            "video_fps": video.get("fps") == 64,
            "audio_samples": audio.get("samples_per_channel") == 240_000,
            "audio_format": audio.get("sample_rate") == 48_000
            and audio.get("channels") == 2,
            "mapping": mapping.get("mapped_frames") == 320
            and mapping.get("total_frames") == 320
            and mapping.get("success_rate") == 1.0,
            "presentation_phase": phase.get("passed") is True,
            "mode": mode.get("requested_gametype")
            == mode.get("realized_gametype")
            and mode.get("fallback_detected") is False,
            "renderer": str(runtime.get("renderer", "")).startswith(
                "NVIDIA "
            ),
            "hud": hud.get("cl_hidewaypoints") == 2
            and hud.get("g_ctf_flag_waypoint") == 0
            and hud.get("hud_panel_modicons") == 0,
            "x264": runtime.get("x264_preset") == "medium"
            and runtime.get("x264_threads") == 16
            and runtime.get("x264_cpuset") == "0-15",
            "not_training": qa.get("training_admitted") is False,
        }
        require(
            all(checks.values()),
            "qa_contract",
            {
                "path": str(qa_path),
                "failed": [
                    name for name, passed in checks.items() if not passed
                ],
            },
        )
        renderers.add(str(runtime.get("renderer")))
        tick_ranges.add(
            (
                int(mapping.get("episode_tick_first", -1)),
                int(mapping.get("episode_tick_last", -1)),
            )
        )
        video_frames.add(int(video.get("frames", -1)))
        audio_samples.add(int(audio.get("samples_per_channel", -1)))
        mapping_rates.add(float(mapping.get("success_rate", -1.0)))
        maximum_interpolation = max(
            maximum_interpolation,
            abs(float(phase.get("max_abs_interpolation", 0.0))),
        )
        maximum_client_previous_error = max(
            maximum_client_previous_error,
            abs(
                float(
                    phase.get(
                        "max_client_previous_error_seconds", 0.0
                    )
                )
            ),
        )

    raw_frame_rows_exact = 0
    raw_presentation_failures = 0
    for path in frame_paths:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) == 320:
            raw_frame_rows_exact += 1
        else:
            require(
                False,
                "raw_frame_rows",
                {"path": str(path), "rows": len(rows)},
            )
        ticks = [int(row["server_tick"]) for row in rows]
        discontinuities = sum(
            current != previous + 1
            for previous, current in zip(ticks, ticks[1:])
        )
        frame_discontinuities += discontinuities
        phase_failed = any(
            abs(float(row["interpolation"])) > 1e-6
            or abs(
                float(row["client_time"])
                - float(row["server_time_previous"])
            )
            > 1e-6
            or float(row["server_time_current"])
            <= float(row["server_time_previous"])
            for row in rows
        )
        raw_presentation_failures += int(phase_failed)
    require(
        frame_discontinuities == 0,
        "raw_frame_tick_continuity",
        frame_discontinuities,
    )
    require(
        raw_presentation_failures == 0,
        "raw_frame_presentation_phase",
        raw_presentation_failures,
    )

    report = {
        "schema_version": "xonotic-stage1-resident-multilane-qa-audit-v1",
        "pass": not failures,
        "training_admitted": False,
        "benchmark_root": str(root),
        "source_commit": result.get("source_commit"),
        "build": result.get("build"),
        "lanes": lanes,
        "discarded_warmup_episodes": lanes,
        "steady_state_episodes": int(
            result.get("steady_window", {}).get("episodes", 0)
        ),
        "steady_state_wall_seconds": result.get("steady_window", {}).get(
            "wall_seconds"
        ),
        "steady_state_episodes_per_hour": result.get(
            "steady_window", {}
        ).get("episodes_per_hour"),
        "batch_wall_seconds": result.get("batch_wall_seconds"),
        "qa_files": len(qa_paths),
        "qa_hard_gate_failures": sum(
            1
            for path in qa_paths
            if not all(load_json(path).get("hard_gates", {}).values())
        ),
        "raw_frame_csv_files": len(frame_paths),
        "raw_frame_csv_rows_exact_320": raw_frame_rows_exact,
        "raw_frame_tick_discontinuities": frame_discontinuities,
        "raw_frame_presentation_phase_failures": raw_presentation_failures,
        "video_frame_counts": sorted(video_frames),
        "audio_samples_per_channel": sorted(audio_samples),
        "episode_tick_ranges": [list(value) for value in sorted(tick_ranges)],
        "frame_tick_mapping_rates": sorted(mapping_rates),
        "maximum_interpolation": maximum_interpolation,
        "maximum_client_previous_time_error_seconds": (
            maximum_client_previous_error
        ),
        "renderers": sorted(renderers),
        "configuration": result.get("configuration"),
        "cgroup_cpu": result.get("cgroup_cpu"),
        "gpu_profile": gpu_profile(
            Path(args.gpu_log).resolve() if args.gpu_log else None
        ),
        "failures": failures,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
