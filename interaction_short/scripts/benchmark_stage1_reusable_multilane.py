                      
"""Benchmark several isolated resident Stage-1 lanes on one GPU."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import xonotic_capture as capture
from benchmark_stage1_reusable_lane import DEFAULT_A, DEFAULT_B


def cgroup_cpu_snapshot() -> dict[str, Any]:
    stat_path = Path("/sys/fs/cgroup/cpu.stat")
    values: dict[str, int] = {}
    if stat_path.is_file():
        for line in stat_path.read_text(encoding="utf-8").splitlines():
            key, raw_value = line.split()
            values[key] = int(raw_value)
    return values


def command_run(args: argparse.Namespace) -> int:
    capture.require_conda()
    if args.lanes <= 0:
        raise capture.CaptureFailure(
            "resident_multilane_count_invalid", str(args.lanes)
        )
    output = Path(args.output_root).resolve()
    if output.exists():
        raise capture.CaptureFailure(
            "resident_multilane_output_exists", str(output)
        )
    output.mkdir(parents=True)
    shared_encode_slots = (
        capture.TMP_ROOT
        / f"stage1-resident-encode-slots-{os.getpid()}"
    )
    shared_encode_slots.mkdir(parents=True, exist_ok=False)
    process_environment = capture.process_environment()
    process_environment["XONOTIC_ENCODE_SLOT_DIRECTORY"] = str(
        shared_encode_slots
    )
    script = capture.ROOT / "scripts/benchmark_stage1_reusable_lane.py"
    processes: list[dict[str, Any]] = []
    batch_cpu_started = cgroup_cpu_snapshot()
    batch_started = time.time()
    try:
        for lane_index in range(args.lanes):
            lane_name = f"lane-{lane_index:02d}"
            lane_output = output / lane_name
            log_path = output / f"{lane_name}.log"
            log_handle = log_path.open("xb")
            command = [
                sys.executable,
                str(script),
                "--output-root",
                str(lane_output),
                "--build",
                str(Path(args.build).resolve()),
                "--reference-a",
                str(Path(args.reference_a).resolve()),
                "--reference-b",
                str(Path(args.reference_b).resolve()),
                "--port",
                str(args.base_port + lane_index * 8),
            ]
            process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                env=process_environment,
                start_new_session=True,
            )
            processes.append(
                {
                    "lane_index": lane_index,
                    "lane_name": lane_name,
                    "output": lane_output,
                    "log_path": log_path,
                    "log_handle": log_handle,
                    "command": command,
                    "process": process,
                }
            )
        unfinished = set(range(args.lanes))
        while unfinished:
            for lane_index in tuple(unfinished):
                process = processes[lane_index]["process"]
                if process.poll() is not None:
                    unfinished.remove(lane_index)
                    print(
                        f"lane_complete index={lane_index} "
                        f"returncode={process.returncode}",
                        flush=True,
                    )
            if unfinished:
                time.sleep(1)
    finally:
        for row in processes:
            process = row["process"]
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            row["log_handle"].close()
    batch_finished = time.time()
    batch_cpu_finished = cgroup_cpu_snapshot()

    lane_reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in processes:
        result_path = row["output"] / "RESULT.json"
        if not result_path.is_file():
            failures.append(
                {
                    "lane_index": row["lane_index"],
                    "returncode": row["process"].returncode,
                    "reason": "RESULT.json missing",
                    "log_path": str(row["log_path"]),
                }
            )
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        lane_reports.append(result)
        if row["process"].returncode != 0 or not result.get("pass"):
            failures.append(
                {
                    "lane_index": row["lane_index"],
                    "returncode": row["process"].returncode,
                    "reason": "lane isolation admission failed",
                    "log_path": str(row["log_path"]),
                    "result_path": str(result_path),
                }
            )

    steady_rows = [
        runtime
        for report in lane_reports
        for runtime in report["runtime"]
        if runtime["label"] != "warmup_discarded"
    ]
    steady_start = min(
        (
            float(row["started_unix_seconds"])
            for row in steady_rows
        ),
        default=batch_finished,
    )
    steady_finish = max(
        (
            float(row["finished_unix_seconds"])
            for row in steady_rows
        ),
        default=batch_finished,
    )
    steady_wall = max(0.0, steady_finish - steady_start)
    report = {
        "schema_version": "xonotic-stage1-resident-multilane-benchmark-v1",
        "created_utc": capture.utc_now(),
        "pass": not failures and len(lane_reports) == args.lanes,
        "training_admitted": False,
        "formal_worker_enabled": False,
        "lanes": args.lanes,
        "build": str(Path(args.build).resolve()),
        "source_commit": (
            Path(args.build).resolve() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip(),
        "reference_a": str(Path(args.reference_a).resolve()),
        "reference_b": str(Path(args.reference_b).resolve()),
        "batch_wall_seconds": batch_finished - batch_started,
        "cgroup_cpu": {
            "cpu_max": (
                Path("/sys/fs/cgroup/cpu.max")
                .read_text(encoding="utf-8")
                .strip()
                if Path("/sys/fs/cgroup/cpu.max").is_file()
                else None
            ),
            "started": batch_cpu_started,
            "finished": batch_cpu_finished,
            "delta": {
                key: batch_cpu_finished.get(key, 0)
                - batch_cpu_started.get(key, 0)
                for key in sorted(
                    set(batch_cpu_started) | set(batch_cpu_finished)
                )
            },
        },
        "steady_window": {
            "episodes": len(steady_rows),
            "wall_seconds": steady_wall,
            "episodes_per_hour": (
                len(steady_rows) * 3600.0 / steady_wall
                if steady_wall > 0
                else 0.0
            ),
        },
        "configuration": {
            "active_sdl_processes": args.lanes,
            "resident_sdl_processes": args.lanes * 2,
            "resident_dedicated_servers": args.lanes,
            "idle_client_maxfps": 8,
            "resident_control_timeout_seconds": (
                capture.configured_resident_control_timeout_seconds()
            ),
            "x264_threads": capture.configured_x264_threads(),
            "x264_cpuset": capture.configured_x264_cpuset(),
            "encode_concurrency": capture.configured_encode_concurrency(),
            "encode_concurrency_scope": (
                "process_shared_file_slots"
            ),
            "encode_slot_directory": str(shared_encode_slots),
        },
        "lane_steady_state": [
            report["steady_state"] for report in lane_reports
        ],
        "failures": failures,
        "lane_result_paths": [
            str(row["output"] / "RESULT.json") for row in processes
        ],
        "lane_log_paths": [
            str(row["log_path"]) for row in processes
        ],
    }
    (output / "RESULT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    return 0 if report["pass"] else 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--output-root", required=True)
    result.add_argument("--lanes", type=int, required=True)
    result.add_argument(
        "--build",
        default=str(
            capture.ROOT / "build/capture-b40e26fd4e33-x86_64"
        ),
    )
    result.add_argument("--reference-a", default=str(DEFAULT_A))
    result.add_argument("--reference-b", default=str(DEFAULT_B))
    result.add_argument("--base-port", type=int, default=39_200)
    result.set_defaults(func=command_run)
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    raise SystemExit(arguments.func(arguments))
