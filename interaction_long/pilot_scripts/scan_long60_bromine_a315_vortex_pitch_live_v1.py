                      
"""Focused Bromine angle-315 Vortex pitch qualification.

This is live-only and never admits rows to training.  It tests whether the
alternate legal anchor removes the last geometry-dependent Vortex miss for
both long-video templates.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "run_long60_ref42_v7_hitscan_live_calibration.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_bromine_a315_vortex_pitch_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import calibration module: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


SCAN_ID = "long60_bromine_a315_vortex_pitch_live6_20260828_v1"
PITCH_BIASES = (1.0, 2.0, 3.0)
cal.CALIBRATION_ID = SCAN_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID

player = cal.v7.MAPS["bromine"]["player_origin"]
angle = math.radians(315.0)
cal.v7.MAPS["bromine"].update(
    {
        "anchor_id": "bromine_selected_a315_scale075",
        "enemy_reference_origin": [
            float(player[0]) + 200.0 * math.cos(angle),
            float(player[1]) + 200.0 * math.sin(angle),
            float(player[2]),
        ],
        "trajectory_scale": 0.75,
    }
)


def choose_rows() -> list[dict[str, Any]]:
    source = cal.v7.distribution_rows()
    rows = []
    for template in sorted(cal.v7.ORIGINAL_TEMPLATES):
        prototype = next(
            dict(row)
            for row in source
            if row["template"] == template
            and row["map"] == "bromine"
            and row["weapon"] == "Vortex"
            and int(row["kill_count"]) == 0
        )
        for bias in PITCH_BIASES:
            row = dict(prototype)
            index = len(rows)
            row.update(
                {
                    "manifest_index": index,
                    "calibration_index": index,
                    "episode_id": f"l60v7a315pitch_{template}_p{int(bias)}",
                    "split": "test",
                    "kill_count": 0,
                    "kill_slots": [],
                    "aim_pitch_bias_degrees": bias,
                    "anchor_id": cal.v7.MAPS["bromine"]["anchor_id"],
                    "training_admitted": False,
                }
            )
            rows.append(row)
    return rows


cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.main())
