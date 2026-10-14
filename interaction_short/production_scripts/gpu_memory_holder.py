                      
"""Hold a bounded amount of otherwise idle GPU memory without doing compute."""

from __future__ import annotations

import argparse
import json
import os
import signal
import time

import torch


GIB = 1024**3
MIB = 1024**2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-used-gib", type=float, default=64.0)
    parser.add_argument("--min-free-gib", type=float, default=192.0)
    parser.add_argument("--chunk-mib", type=int, default=1024)
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    return parser.parse_args()


def emit(event: str, **fields: object) -> None:
    print(
        json.dumps(
            {
                "event": event,
                "pid": os.getpid(),
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **fields,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def main() -> int:
    args = parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError(
            "holder requires exactly one CUDA-visible GPU: "
            f"available={torch.cuda.is_available()} count={torch.cuda.device_count()}"
        )
    if args.target_used_gib <= 0 or args.min_free_gib <= 0:
        raise ValueError("memory targets must be positive")
    if args.chunk_mib <= 0 or args.heartbeat_seconds <= 0:
        raise ValueError("chunk and heartbeat values must be positive")

    torch.cuda.set_device(0)
    free_before, total = torch.cuda.mem_get_info(0)
    used_before = total - free_before
    target_used = int(args.target_used_gib * GIB)
    min_free = int(args.min_free_gib * GIB)
    allocation_goal = max(
        0,
        min(target_used - used_before, free_before - min_free),
    )
    chunk_bytes = args.chunk_mib * MIB
    held: list[torch.Tensor] = []
    held_bytes = 0

    emit(
        "holder_start",
        cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
        device_name=torch.cuda.get_device_name(0),
        total_mib=total // MIB,
        used_before_mib=used_before // MIB,
        free_before_mib=free_before // MIB,
        target_used_mib=target_used // MIB,
        min_free_mib=min_free // MIB,
        allocation_goal_mib=allocation_goal // MIB,
    )

    while held_bytes < allocation_goal:
        request = min(chunk_bytes, allocation_goal - held_bytes)
                                                                             
                                                                                
                          
        try:
            held.append(torch.empty(request, dtype=torch.uint8, device="cuda:0"))
        except torch.cuda.OutOfMemoryError as exc:
            emit(
                "holder_allocation_stopped",
                held_mib=held_bytes // MIB,
                error=f"{type(exc).__name__}: {exc}",
            )
            break
        held_bytes += request

    free_after, _ = torch.cuda.mem_get_info(0)
    emit(
        "holder_ready",
        tensor_count=len(held),
        held_mib=held_bytes // MIB,
        used_after_mib=(total - free_after) // MIB,
        free_after_mib=free_after // MIB,
    )

    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        time.sleep(args.heartbeat_seconds)
        free_now, _ = torch.cuda.mem_get_info(0)
        emit(
            "holder_heartbeat",
            tensor_count=len(held),
            held_mib=held_bytes // MIB,
            used_now_mib=(total - free_now) // MIB,
            free_now_mib=free_now // MIB,
        )
    emit("holder_stop", held_mib=held_bytes // MIB)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
