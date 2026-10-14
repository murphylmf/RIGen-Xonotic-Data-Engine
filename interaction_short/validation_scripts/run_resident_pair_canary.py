                      
"""Run one isolated Stage-2 pair through the full resident acceleration path."""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD_TAG = "capture-e1b6fef45bc3-aarch64"
SOURCE_COMMIT = "e1b6fef45bc370d36b1f5e3ba04cd1de1d211403"
os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG", BUILD_TAG
)
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT", SOURCE_COMMIT
)
os.environ.setdefault("XONOTIC_BUILD_GLOB", f"build/{BUILD_TAG}")
os.environ.setdefault("XONOTIC_OFFLINE_ACCELERATE", "1")
os.environ.setdefault("XONOTIC_LIVE_TIME_SCALE", "4")
os.environ.setdefault("XONOTIC_ENCODE_CONCURRENCY", "1")
os.environ.setdefault("XONOTIC_X264_THREADS", "6")
os.environ.setdefault("XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "120")
os.environ.setdefault("SDL_VIDEODRIVER", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "opengl")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "production_scripts"))

from pilot_scripts import build_samples as pilot              
import run_stage2_motion_40k_shard as worker              


def load_row(path: Path, row_index: int) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index == row_index:
                return json.loads(line)
    raise RuntimeError(f"row index outside manifest: {row_index}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--row-index", type=int, default=0)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=29500)
    args = parser.parse_args()
    cpu_isolation = worker.reusable.configure_resident_cpu_isolation(
        1,
        requested_x264_cpuset=os.environ.get("XONOTIC_X264_CPUSET", ""),
    )
    output_root = args.output_root.resolve()
    scratch_root = args.scratch_root.resolve()
    if output_root.exists():
        raise RuntimeError(f"refusing to overwrite canary: {output_root}")
    output_root.mkdir(parents=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    row = copy.deepcopy(load_row(args.input_jsonl.resolve(), args.row_index))
    for scenario in (row["active_scenario"], row["frozen_scenario"]):
        trace = scenario.get("prefrozen_trace_source") or None
        if trace is not None:
            original_source_commit = str(trace.get("source_commit", ""))
            trace["source_commit"] = SOURCE_COMMIT
            trace["runtime_recertification"] = {
                "schema_version": (
                    "xonotic-stage2-prefrozen-trace-runtime-"
                    "recertification-v1"
                ),
                "original_source_commit": original_source_commit,
                "runtime_source_commit": SOURCE_COMMIT,
                "method": (
                    "replay_immutable_actions_and_fail_closed_compare_live_"
                    "player_positions_to_immutable_reference_states"
                ),
                "live_fail_closed": True,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
            }
            scenario["prefrozen_trace_runtime_recertification"] = (
                copy.deepcopy(trace["runtime_recertification"])
            )
        scenario["source_commit_required"] = SOURCE_COMMIT
        scenario["training_admitted"] = False
    active_scenario = row["active_scenario"]
    world_group = (
        str(active_scenario["map"]),
        str(active_scenario.get("gametype", "dm")).lower(),
    )
    pilot.run_protection_check(output_root / "STAGE12_PRECHECK.txt")
    controller = worker.Stage2ResidentLaneController(
        lane_index=0,
        group_index=1,
        world_group=world_group,
        port=args.port,
        build=pilot.capture.build_root(),
        shard_root=output_root,
        scratch_root=scratch_root,
    )
    started = time.monotonic()
    try:
        active = pilot.capture_episode(
            active_scenario,
            output_root,
            scratch_root,
            port=args.port,
            cleanup_scratch=True,
            retain_raw_avi=bool(row.get("raw_avi_audit", False)),
            resident_lane=controller.get_lane(active_scenario),
        )
        frozen_scenario = row["frozen_scenario"]
        frozen = pilot.capture_episode(
            frozen_scenario,
            output_root,
            scratch_root,
            port=args.port,
            cleanup_scratch=True,
            retain_raw_avi=False,
            resident_lane=controller.get_lane(frozen_scenario),
        )
        pair = pilot.pair_qa(active, frozen)
        wall_seconds = time.monotonic() - started
        summary = {
            "schema_version": "xonotic-stage2-resident-accel-canary-v1",
            "input_jsonl": str(args.input_jsonl.resolve()),
            "row_index": args.row_index,
            "pair_id": row["pair_id"],
            "world_group": list(world_group),
            "passed": (
                active["qa"]["pre_pair_passed"]
                and frozen["qa"]["pre_pair_passed"]
                and pair["passed"]
            ),
            "active_pre_pair_passed": active["qa"]["pre_pair_passed"],
            "frozen_pre_pair_passed": frozen["qa"]["pre_pair_passed"],
            "pair_qa_passed": pair["passed"],
            "active_failed_checks": sorted(
                key
                for key, value in active["qa"]["checks"].items()
                if not value
            ),
            "frozen_failed_checks": sorted(
                key
                for key, value in frozen["qa"]["checks"].items()
                if not value
            ),
            "pair_failed_checks": sorted(
                key for key, value in pair["checks"].items() if not value
            ),
            "active_runtime": active["qa"]["runtime"],
            "frozen_runtime": frozen["qa"]["runtime"],
            "active_live_wall_seconds": active["qa"]["live_wall_seconds"],
            "active_render_wall_seconds": active["qa"][
                "render_wall_seconds"
            ],
            "frozen_live_wall_seconds": frozen["qa"]["live_wall_seconds"],
            "frozen_render_wall_seconds": frozen["qa"][
                "render_wall_seconds"
            ],
            "total_wall_seconds_including_discarded_warmup": wall_seconds,
            "build_tag": BUILD_TAG,
            "source_commit": SOURCE_COMMIT,
            "resident_cpu_isolation": cpu_isolation,
            "created_utc": pilot.capture.utc_now(),
        }
        worker.atomic_json(output_root / "SUMMARY.json", summary)
    finally:
        controller.close()
    pilot.run_protection_check(output_root / "STAGE12_POSTCHECK.txt")
    if scratch_root.exists() and not any(scratch_root.iterdir()):
        scratch_root.rmdir()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
