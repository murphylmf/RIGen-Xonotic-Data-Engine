                      
"""Focused live-only qualification of Bromine at the alternate 315-degree view."""

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
SPEC = importlib.util.spec_from_file_location("long60_bromine_a315_scan_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import calibration module: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


SCAN_ID = "long60_bromine_a315_hitscan_live6_20260828_v1"
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
    rows = [row for row in cal.choose_rows_original() if row["map"] == "bromine"]
    for index, row in enumerate(rows):
        row["manifest_index"] = index
        row["calibration_index"] = index
        row["anchor_id"] = cal.v7.MAPS["bromine"]["anchor_id"]
        row.pop("aim_pitch_bias_degrees", None)
    return rows


cal.choose_rows_original = cal.choose_rows
cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.main())
