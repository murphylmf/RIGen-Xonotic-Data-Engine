                      
"""Render one retained demo with a selected capture build.

This is intentionally render-only: it never mutates the original demo or
scenario and it does not run a new live episode.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_CAPTURE_CLIENT_OVERLAY",
    "configs/capture_client_stage2_v14_no_crosshair.cfg",
)
os.environ.setdefault("XONOTIC_LIVE_TIME_SCALE", "2")
os.environ.setdefault("XONOTIC_OFFLINE_ACCELERATE", "1")
os.environ.setdefault("XONOTIC_RENDER_TIMEOUT_SECONDS", "600")
os.environ.setdefault("XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "120")

sys.path.insert(0, str(ROOT / "scripts"))
import xonotic_stage1_reusable as reusable              


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--demo", required=True, type=Path)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--port", type=int, default=40930)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build = args.build.resolve(strict=True)
    demo = args.demo.resolve(strict=True)
    scenario_path = args.scenario.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to reuse output: {output}")

    scenario = json.loads(scenario_path.read_text())
    demo_name = demo.stem
    live = {
        "demo_name": demo_name,
        "demo_path": demo,
        "resident_token": f"rerender_{scenario['episode_id']}",
    }
    lane_root = output / "lane"
    stage = output / "stage"
    with reusable.ReusableStage1Lane(
        lane_root,
        build=build,
        port=args.port,
    ) as lane:
        try:
            result = lane.run_render(stage, scenario, live)
        except Exception:
            lane.snapshot_failure_logs(stage)
            raise

    printable = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in result.items()
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
