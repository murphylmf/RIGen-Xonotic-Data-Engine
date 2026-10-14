                      
"""Resilient 7-node x 4-GPU launcher for Stage-2 short v15."""

from __future__ import annotations

import os
from pathlib import Path

import launch_dlc_7x4_activeonly_v14_resilient as base


ROOT = Path(__file__).resolve().parents[1]
BUILD_TAG = "capture-8f61470a6dbc-aarch64"
SOURCE_COMMIT = "8f61470a6dbca496990b79898d5ba26cfd492bb0"
RUNNER = ROOT / "production_scripts/run_stage2_short_42k_activeonly_v15_multigpu.py"
RUNTIME_LOCK = ROOT / "locks/stage2_short_7x4_activeonly_v15r1_runtime.sha256"
OVERLAY = ROOT / "configs/capture_client_stage2_v15_no_crosshair_no_casings.cfg"
MANIFEST_ROOT = ROOT / (
    "manifests/stage2_short_42k_v15_random_fire_visualfix_"
    "28shard_20260824_r1"
)
DEFAULT_RUN_ID = "stage2_short_42k_v15_random_fire_visualfix_28gpu_20260824_01"

base.RUNNER = RUNNER
base.RUNTIME_LOCK = RUNTIME_LOCK
base.CROSSHAIR_OVERLAY = OVERLAY
_base_common_runner_environment = base.common_runner_environment


def common_runner_environment(
    local_gpu: int, gpu_uuid: str
) -> dict[str, str]:
    environment = _base_common_runner_environment(local_gpu, gpu_uuid)
    environment.update(
        {
            "XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG": BUILD_TAG,
            "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT": SOURCE_COMMIT,
            "XONOTIC_BUILD_GLOB": f"build/{BUILD_TAG}",
            "XONOTIC_CAPTURE_CLIENT_OVERLAY": str(OVERLAY),
        }
    )
    return environment


base.common_runner_environment = common_runner_environment


def main() -> int:
    os.environ.setdefault("RUN_ID", DEFAULT_RUN_ID)
    os.environ.setdefault("STAGE2_MANIFEST_ROOT", str(MANIFEST_ROOT))
    os.environ.setdefault(
        "STAGE2_SCRATCH_BASE", "./tmp/xonotic-stage2-short-v15-7x4"
    )
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"stage2_short_v15_node_fatal {type(exc).__name__}: {exc}", flush=True)
        while not base.STOP.wait(60):
            print(
                f"stage2_short_v15_node_hold {type(exc).__name__}: {exc}",
                flush=True,
            )
