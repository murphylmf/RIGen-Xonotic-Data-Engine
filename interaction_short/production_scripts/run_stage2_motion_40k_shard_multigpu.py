                      
"""Bind the locked Stage-2 shard runner to one GPU in a multi-GPU Pod."""

from __future__ import annotations

import os
import subprocess
from typing import Any

import run_stage2_motion_40k_shard as shard_runner


def selected_gpu_index() -> int:
    raw = os.environ.get("STAGE2_SELECTED_GPU_INDEX", "")
    if not raw.isdigit():
        raise RuntimeError(
            "STAGE2_SELECTED_GPU_INDEX must be a non-negative integer"
        )
    selected = int(raw)
    egl_selected = os.environ.get("SDL_HINT_EGL_DEVICE")
    if egl_selected != raw:
        raise RuntimeError(
            "SDL_HINT_EGL_DEVICE must match STAGE2_SELECTED_GPU_INDEX: "
            f"egl={egl_selected!r} selected={raw!r}"
        )
    return selected


def query_selected_gpu(fields: str) -> list[str]:
    selected = selected_gpu_index()
    completed = subprocess.run(
        [
            "nvidia-smi",
            "-i",
            str(selected),
            f"--query-gpu={fields}",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [
        line.strip() for line in completed.stdout.splitlines() if line.strip()
    ]
    if completed.returncode != 0 or len(lines) != 1:
        raise RuntimeError(
            "selected GPU query failed: "
            f"index={selected} rc={completed.returncode} rows={lines} "
            f"error={completed.stderr.strip()}"
        )
    return [value.strip() for value in lines[0].split(",")]


def preflight_gpu() -> dict[str, Any]:
    fields = query_selected_gpu("index,name,uuid,memory.total")
    if len(fields) != 4:
        raise RuntimeError(f"unexpected selected GPU row: {fields}")
    selected = selected_gpu_index()
    if int(fields[0]) != selected:
        raise RuntimeError(
            f"nvidia-smi selected index mismatch: requested={selected} row={fields}"
        )
    return {
        "index": fields[0],
        "name": fields[1],
        "uuid": fields[2],
        "memory_total_mib": int(fields[3]),
        "egl_device_index": selected,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }


def gpu_runtime_sample() -> dict[str, Any]:
    try:
        fields = query_selected_gpu(
            "index,name,utilization.gpu,memory.used,memory.total"
        )
        if len(fields) != 5:
            raise RuntimeError(f"unexpected selected GPU sample: {fields}")
        return {
            "sampled_utc": shard_runner.pilot.capture.utc_now(),
            "available": True,
            "index": fields[0],
            "name": fields[1],
            "utilization_percent": int(fields[2]),
            "memory_used_mib": int(fields[3]),
            "memory_total_mib": int(fields[4]),
            "egl_device_index": selected_gpu_index(),
        }
    except Exception as exc:                                                
        return {
            "sampled_utc": shard_runner.pilot.capture.utc_now(),
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
                                                                     
                                                                              
    shard_runner.preflight_gpu = preflight_gpu
    shard_runner.gpu_runtime_sample = gpu_runtime_sample
    return shard_runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
