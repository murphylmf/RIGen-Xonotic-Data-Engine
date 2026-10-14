                      
"""Sample a capture supervisor and its descendants into a durable CSV."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import subprocess
import time
from pathlib import Path

import psutil


GPU_QUERY = (
    "utilization.gpu,memory.used,power.draw,temperature.gpu,"
    "clocks.current.graphics"
)


def gpu_values() -> list[str]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            f"--query-gpu={GPU_QUERY}",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        return [""] * 5
    return [value.strip() for value in completed.stdout.split(",")]


def raw_sizes(root: Path) -> dict[str, int]:
    return {
        str(path): path.stat().st_size
        for path in root.rglob("*.avi")
        if path.is_file()
    }


def processes(root: psutil.Process) -> list[psutil.Process]:
    result = [root]
    try:
        result.extend(root.children(recursive=True))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    root = psutil.Process(args.pid)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    disk_previous = psutil.disk_io_counters()
    raw_previous = raw_sizes(args.raw_root)
    process_write_previous: dict[int, int] = {}
    sampled_previous = time.monotonic()
    known: dict[int, psutil.Process] = {}
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "utc",
                "elapsed_s",
                "process_count",
                "aggregate_cpu_percent",
                "aggregate_rss_mib",
                "gpu_util_percent",
                "gpu_memory_mib",
                "gpu_power_w",
                "gpu_temperature_c",
                "gpu_graphics_clock_mhz",
                "system_write_mib_s",
                "process_write_mib_s",
                "raw_avi_write_mib_s",
                "raw_avi_bytes",
            ]
        )
        started = time.monotonic()
        while root.is_running():
            rows = processes(root)
            cpu = 0.0
            rss = 0
            alive = 0
            process_write_growth = 0
            for process in rows:
                try:
                    cached = known.get(process.pid)
                    if cached is None:
                        cached = process
                        cached.cpu_percent(None)
                        known[process.pid] = cached
                    else:
                        cpu += cached.cpu_percent(None)
                    rss += cached.memory_info().rss
                    current_write = cached.io_counters().write_bytes
                    process_write_growth += max(
                        current_write
                        - process_write_previous.get(
                            process.pid, current_write
                        ),
                        0,
                    )
                    process_write_previous[process.pid] = current_write
                    alive += 1
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    AttributeError,
                ):
                    known.pop(process.pid, None)
                    continue
            now = time.monotonic()
            elapsed = max(now - sampled_previous, 1e-9)
            disk_current = psutil.disk_io_counters()
            current_raw = raw_sizes(args.raw_root)
            raw_growth = sum(
                max(size - raw_previous.get(path, 0), 0)
                for path, size in current_raw.items()
            )
            gpu = gpu_values()
            writer.writerow(
                [
                    dt.datetime.now(dt.timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.%fZ"
                    ),
                    f"{now - started:.3f}",
                    alive,
                    f"{cpu:.3f}",
                    f"{rss / (1024 * 1024):.3f}",
                    *gpu,
                    f"{(disk_current.write_bytes - disk_previous.write_bytes) / (1024 * 1024) / elapsed:.3f}",
                    f"{process_write_growth / (1024 * 1024) / elapsed:.3f}",
                    f"{raw_growth / (1024 * 1024) / elapsed:.3f}",
                    sum(current_raw.values()),
                ]
            )
            handle.flush()
            disk_previous = disk_current
            raw_previous = current_raw
            sampled_previous = now
            try:
                root.wait(timeout=args.interval)
                break
            except psutil.TimeoutExpired:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
