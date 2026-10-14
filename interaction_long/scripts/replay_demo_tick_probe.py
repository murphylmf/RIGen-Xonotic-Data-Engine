                      
"""Replay one existing demo in isolation and audit its server-tick sequence."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

import pandas as pd

import xonotic_capture as capture
from benchmark_stage1_reusable_lane import load_reference


def command_run(args: argparse.Namespace) -> int:
    capture.require_conda()
    output = Path(args.output_root).resolve()
    if output.exists():
        raise capture.CaptureFailure(
            "demo_tick_probe_output_exists", str(output)
        )
    output.mkdir(parents=True)
    demo = Path(args.demo).resolve()
    if not demo.is_file():
        raise capture.CaptureFailure("demo_tick_probe_missing", str(demo))
    build = Path(args.build).resolve()
    scenario, _ = load_reference(Path(args.reference).resolve())
    _, client_user = capture.prepare_userdirs(
        output / "userdirs", build
    )
    replay_demo = (
        client_user
        / "data/demos"
        / f"{scenario['episode_id']}.dem"
    )
    shutil.copy2(demo, replay_demo)
    stage = output / "render"
    stage.mkdir()
    render = capture.run_render_attempt(
        stage, scenario, build, client_user
    )
    with Path(render["frames_engine"]).open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    ticks = [int(row["server_tick"]) for row in rows]
    presentation_phase = capture.fixed_demo_presentation_phase_metrics(
        pd.DataFrame(rows)
    )
    expected_first_tick = None
    telemetry = None
    if args.telemetry:
        telemetry = Path(args.telemetry).resolve()
        reset = None
        with telemetry.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("kind") == "reset":
                    reset = record
                    break
        if reset is None:
            raise capture.CaptureFailure(
                "demo_tick_probe_reset_missing", str(telemetry)
            )
        expected_first_tick = (
            round(float(reset["server_time"]) * capture.TICK_HZ)
            + capture.WARMUP_TICKS
        )
    discontinuities = [
        {
            "left_frame": index - 1,
            "left_tick": ticks[index - 1],
            "right_frame": index,
            "right_tick": ticks[index],
            "delta": ticks[index] - ticks[index - 1],
        }
        for index in range(1, len(ticks))
        if ticks[index] != ticks[index - 1] + 1
    ]
    report = {
        "schema_version": "xonotic-demo-tick-probe-v1",
        "created_utc": capture.utc_now(),
        "pass": (
            len(ticks) == capture.OUTPUT_TICKS
            and not discontinuities
            and presentation_phase["passed"]
            and (
                expected_first_tick is None
                or (
                    ticks
                    and ticks[0] == expected_first_tick
                    and ticks[-1]
                    == expected_first_tick + capture.OUTPUT_TICKS - 1
                )
            )
        ),
        "training_admitted": False,
        "source_demo": str(demo),
        "source_demo_sha256": capture.sha256_file(demo),
        "reference": str(Path(args.reference).resolve()),
        "telemetry": str(telemetry) if telemetry else None,
        "episode_id": scenario["episode_id"],
        "renderer": render["renderer"],
        "frames": len(ticks),
        "first_tick": ticks[0] if ticks else None,
        "last_tick": ticks[-1] if ticks else None,
        "expected_first_tick": expected_first_tick,
        "expected_last_tick": (
            expected_first_tick + capture.OUTPUT_TICKS - 1
            if expected_first_tick is not None
            else None
        ),
        "discontinuities": discontinuities,
        "presentation_phase": presentation_phase,
        "render": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in render.items()
        },
    }
    (output / "RESULT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--demo", required=True)
    result.add_argument("--reference", required=True)
    result.add_argument("--telemetry")
    result.add_argument("--output-root", required=True)
    result.add_argument(
        "--build",
        default=str(
            capture.ROOT
            / "build/capture-b40e26fd4e33-x86_64"
        ),
    )
    result.set_defaults(func=command_run)
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    raise SystemExit(arguments.func(arguments))
