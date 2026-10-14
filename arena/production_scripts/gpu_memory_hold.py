                      
"""Hold a fixed fraction of one visible GPU's memory without compute load."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone

import torch


MIB = 1024 * 1024
_running = True


def emit(event: str, **fields: object) -> None:
    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "pid": os.getpid(),
        **fields,
    }
    print(json.dumps(payload, sort_keys=True), flush=True)


def request_stop(signum: int, _frame: object) -> None:
    global _running
    _running = False
    emit("stop_requested", signal=signum)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-fraction", type=float, default=0.62)
    parser.add_argument("--chunk-mib", type=int, default=1024)
    parser.add_argument("--heartbeat-seconds", type=float, default=60.0)
    args = parser.parse_args()
    if not 0.60 < args.target_fraction <= 0.70:
        parser.error("--target-fraction must be > 0.60 and <= 0.70")
    if not 64 <= args.chunk_mib <= 4096:
        parser.error("--chunk-mib must be between 64 and 4096")
    if args.heartbeat_seconds < 5:
        parser.error("--heartbeat-seconds must be at least 5")
    return args


def gpu_snapshot(target_bytes: int) -> dict[str, object]:
    free_bytes, total_bytes = torch.cuda.mem_get_info(0)
    return {
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "device_name": torch.cuda.get_device_name(0),
        "target_mib": round(target_bytes / MIB, 1),
        "process_allocated_mib": round(torch.cuda.memory_allocated(0) / MIB, 1),
        "process_reserved_mib": round(torch.cuda.memory_reserved(0) / MIB, 1),
        "global_used_mib": round((total_bytes - free_bytes) / MIB, 1),
        "global_total_mib": round(total_bytes / MIB, 1),
        "global_used_fraction": round((total_bytes - free_bytes) / total_bytes, 5),
    }


def main() -> int:
    args = parse_args()
    if not torch.cuda.is_available():
        emit("error", reason="CUDA is not available")
        return 2

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    torch.cuda.set_device(0)
    _, total_bytes = torch.cuda.mem_get_info(0)
    target_bytes = int(total_bytes * args.target_fraction)
    chunk_bytes = args.chunk_mib * MIB
    tensors: list[torch.Tensor] = []
    held_bytes = 0

    emit(
        "allocating",
        target_fraction=args.target_fraction,
        chunk_mib=args.chunk_mib,
        **gpu_snapshot(target_bytes),
    )
    try:
        while held_bytes < target_bytes:
            allocation_bytes = min(chunk_bytes, target_bytes - held_bytes)
            tensor = torch.empty(allocation_bytes, dtype=torch.uint8, device="cuda:0")
            tensor[0] = 0
            tensors.append(tensor)
            held_bytes += allocation_bytes
        torch.cuda.synchronize(0)
    except Exception as exc:
        tensors.clear()
        torch.cuda.empty_cache()
        emit("error", reason=f"allocation failed: {type(exc).__name__}: {exc}")
        return 2

    snapshot = gpu_snapshot(target_bytes)
    if float(snapshot["process_allocated_mib"]) < (target_bytes / MIB) * 0.995:
        tensors.clear()
        torch.cuda.empty_cache()
        emit("error", reason="allocator did not reach the requested target", **snapshot)
        return 2

    emit("ready", target_fraction=args.target_fraction, **snapshot)
    while _running:
        time.sleep(args.heartbeat_seconds)
        emit("heartbeat", target_fraction=args.target_fraction, **gpu_snapshot(target_bytes))

    tensors.clear()
    torch.cuda.empty_cache()
    emit("stopped", **gpu_snapshot(target_bytes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
