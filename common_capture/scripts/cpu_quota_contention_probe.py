                      
"""Generate finite, auditable CPU contention for capture robustness tests."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import signal
import time
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def burn(
    worker_index: int,
    cpu: int,
    deadline: float,
    stop: mp.synchronize.Event,
    results: mp.Queue,
) -> None:
    os.sched_setaffinity(0, {cpu})
    iterations = 0
    value = worker_index + 1
    while time.monotonic() < deadline and not stop.is_set():
        for _ in range(100_000):
            value = (value * 1_664_525 + 1_013_904_223) & 0xFFFFFFFF
        iterations += 100_000
    results.put(
        {
            "worker_index": worker_index,
            "cpu": cpu,
            "iterations": iterations,
            "checksum": value,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--cpu-start", type=int, default=0)
    args = parser.parse_args()
    if args.workers < 1 or args.duration_seconds <= 0:
        parser.error("workers and duration must be positive")

    available = sorted(os.sched_getaffinity(0))
    selected = [
        cpu for cpu in available if cpu >= args.cpu_start
    ][: args.workers]
    if len(selected) != args.workers:
        parser.error(
            f"requested {args.workers} CPUs from {args.cpu_start}, "
            f"only found {len(selected)}"
        )

    started = time.monotonic()
    deadline = started + args.duration_seconds
    stop = mp.Event()
    results: mp.Queue = mp.Queue()

    def request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    print(
        json.dumps(
            {
                "event": "cpu_contention_started",
                "created_utc": utc_now(),
                "workers": args.workers,
                "duration_seconds": args.duration_seconds,
                "cpus": selected,
                "cgroup_cpu_max": (
                    open("/sys/fs/cgroup/cpu.max", encoding="utf-8")
                    .read()
                    .strip()
                ),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    processes = [
        mp.Process(
            target=burn,
            args=(index, cpu, deadline, stop, results),
            name=f"cpu-contention-{index:02d}",
        )
        for index, cpu in enumerate(selected)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
    rows = [results.get() for _ in processes]
    print(
        json.dumps(
            {
                "event": "cpu_contention_finished",
                "created_utc": utc_now(),
                "wall_seconds": time.monotonic() - started,
                "workers": sorted(rows, key=lambda row: row["worker_index"]),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
