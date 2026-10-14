                      
"""Replay the same demo around a foreign demo in one resident renderer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import xonotic_capture as capture
from benchmark_stage1_reusable_lane import load_reference
from xonotic_stage1_reusable import ReusableStage1Lane


def _render_once(
    lane: ReusableStage1Lane,
    root: Path,
    *,
    label: str,
    demo: Path,
    scenario: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    stage = root / label
    stage.mkdir()
    lane.sequence = sequence
    return lane.run_render(
        stage,
        scenario,
        {
            "demo_name": f"resident_probe_{label}",
            "demo_path": demo,
            "resident_token": label,
        },
    )


def _compare_frames(left_path: Path, right_path: Path) -> dict[str, Any]:
    left = pd.read_csv(left_path)
    right = pd.read_csv(right_path)
    same_schema = list(left.columns) == list(right.columns)
    same_rows = len(left) == len(right)
    differing_columns: list[str] = []
    if same_schema and same_rows:
        differing_columns = [
            column
            for column in left.columns
            if not left[column].equals(right[column])
        ]
    camera_columns = [
        "camera_x",
        "camera_y",
        "camera_z",
        "forward_x",
        "forward_y",
        "forward_z",
    ]
    presentation_float_columns = [
        column
        for column in left.columns
        if column.startswith(("camera_", "forward_", "left_", "up_"))
        or (
            len(column) == 3
            and column[0] == "m"
            and column[1:].isdigit()
        )
    ]
    camera_exact = False
    maximum_camera_position_delta = None
    differing_camera_frames: list[int] = []
    if same_schema and same_rows:
        left_camera = left[camera_columns].to_numpy(dtype=np.float64)
        right_camera = right[camera_columns].to_numpy(dtype=np.float64)
        camera_exact = bool(np.array_equal(left_camera, right_camera))
        position_delta = np.linalg.norm(
            left_camera[:, :3] - right_camera[:, :3],
            axis=1,
        )
        maximum_camera_position_delta = float(np.max(position_delta))
        differing_camera_frames = np.flatnonzero(
            position_delta != 0
        ).astype(int).tolist()
    tick_exact = bool(
        same_schema
        and same_rows
        and left["server_tick"].equals(right["server_tick"])
    )
    presentation_maximum_float32_ulp_distance = None
    presentation_float32_ulp_bounded = False
    nonpresentation_differing_columns: list[str] = []
    if same_schema and same_rows:
        nonpresentation_differing_columns = [
            column
            for column in differing_columns
            if column not in presentation_float_columns
        ]
        left_values = left[presentation_float_columns].to_numpy(
            dtype=np.float32
        )
        right_values = right[presentation_float_columns].to_numpy(
            dtype=np.float32
        )

        def ordered_float32(values: np.ndarray) -> np.ndarray:
            bits = values.view(np.uint32).astype(np.uint64)
            magnitude = bits & np.uint64(0x7FFFFFFF)
            negative = (bits & np.uint64(0x80000000)) != 0
            return np.where(
                negative,
                np.uint64(0x80000000) - magnitude,
                np.uint64(0x80000000) + magnitude,
            )

        left_ordered = ordered_float32(left_values)
        right_ordered = ordered_float32(right_values)
        ulp_distance = np.maximum(
            left_ordered,
            right_ordered,
        ) - np.minimum(left_ordered, right_ordered)
        presentation_maximum_float32_ulp_distance = int(
            np.max(ulp_distance)
        )
        presentation_float32_ulp_bounded = bool(
            presentation_maximum_float32_ulp_distance <= 1
        )
    expected_tick_count = bool(
        tick_exact
        and len(left) == capture.OUTPUT_TICKS
        and np.all(np.diff(left["server_tick"].to_numpy()) == 1)
    )
    return {
        "passed": (
            same_schema
            and same_rows
            and not nonpresentation_differing_columns
            and presentation_float32_ulp_bounded
            and expected_tick_count
        ),
        "same_schema": same_schema,
        "same_rows": same_rows,
        "row_count": len(left),
        "differing_columns": differing_columns,
        "nonpresentation_differing_columns": (
            nonpresentation_differing_columns
        ),
        "camera_exact": camera_exact,
        "presentation_maximum_float32_ulp_distance": (
            presentation_maximum_float32_ulp_distance
        ),
        "presentation_float32_ulp_limit": 1,
        "presentation_float32_ulp_bounded": (
            presentation_float32_ulp_bounded
        ),
        "maximum_camera_position_delta_units": (
            maximum_camera_position_delta
        ),
        "differing_camera_frames": differing_camera_frames,
        "server_tick_exact": tick_exact,
        "server_tick_contiguous_320": expected_tick_count,
        "first_tick": int(left["server_tick"].iloc[0]),
        "last_tick": int(left["server_tick"].iloc[-1]),
    }


def command_run(args: argparse.Namespace) -> int:
    capture.require_conda()
    output = Path(args.output_root).resolve()
    if output.exists():
        raise capture.CaptureFailure(
            "resident_render_probe_output_exists",
            str(output),
        )
    output.mkdir(parents=True)
    demo_a = Path(args.demo_a).resolve()
    demo_b = Path(args.demo_b).resolve()
    for demo in (demo_a, demo_b):
        if not demo.is_file():
            raise capture.CaptureFailure(
                "resident_render_probe_demo_missing",
                str(demo),
            )
    scenario_a, _ = load_reference(Path(args.reference_a).resolve())
    scenario_b, _ = load_reference(Path(args.reference_b).resolve())
    build = Path(args.build).resolve()
    rendered: dict[str, dict[str, Any]] = {}
    with ReusableStage1Lane(
        output / "lane",
        build=build,
        port=args.port,
    ) as lane:
        lane._start_clients()
        for sequence, (label, demo, scenario) in enumerate(
            (
                ("a_before", demo_a, scenario_a),
                ("b_intervening", demo_b, scenario_b),
                ("a_after", demo_a, scenario_a),
            ),
            start=1,
        ):
            rendered[label] = _render_once(
                lane,
                output,
                label=label,
                demo=demo,
                scenario=scenario,
                sequence=sequence,
            )
            print(
                f"resident render accepted {label} "
                f"episode={scenario['episode_id']}",
                flush=True,
            )
        renderer = lane.renderer

    comparison = _compare_frames(
        Path(rendered["a_before"]["frames_engine"]),
        Path(rendered["a_after"]["frames_engine"]),
    )
    report = {
        "schema_version": "xonotic-resident-render-isolation-probe-v2",
        "created_utc": capture.utc_now(),
        "pass": comparison["passed"],
        "training_admitted": False,
        "renderer": renderer,
        "build": str(build),
        "source_demos": {
            "a": {
                "path": str(demo_a),
                "sha256": capture.sha256_file(demo_a),
            },
            "b": {
                "path": str(demo_b),
                "sha256": capture.sha256_file(demo_b),
            },
        },
        "sequence": ["a_before", "b_intervening", "a_after"],
        "comparison": comparison,
        "rendered": {
            label: {
                key: str(value) if isinstance(value, Path) else value
                for key, value in result.items()
            }
            for label, result in rendered.items()
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
    result.add_argument("--output-root", required=True)
    result.add_argument("--demo-a", required=True)
    result.add_argument("--demo-b", required=True)
    result.add_argument("--reference-a", required=True)
    result.add_argument("--reference-b", required=True)
    result.add_argument("--build", required=True)
    result.add_argument("--port", type=int, default=40_900)
    result.set_defaults(func=command_run)
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    raise SystemExit(arguments.func(arguments))
