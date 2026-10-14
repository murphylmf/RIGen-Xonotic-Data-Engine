                      
"""Live-only pitch-bias sweep for the two remaining Bromine/Vortex misses."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "run_long60_ref42_v7_hitscan_live_calibration.py"
)
SPEC = importlib.util.spec_from_file_location("long60_bromine_vortex_pitch_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import calibration module: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


SCAN_ID = "long60_bromine_vortex_pitch_live12_20260828_v1"
PITCH_BIASES = (-3.0, -2.0, -1.0, 1.0, 2.0, 3.0)
cal.CALIBRATION_ID = SCAN_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID


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
            label = f"m{abs(int(bias))}" if bias < 0 else f"p{int(bias)}"
            row.update(
                {
                    "manifest_index": index,
                    "calibration_index": index,
                    "episode_id": f"l60v7pitch_{template}_{label}",
                    "split": "test",
                    "kill_count": 0,
                    "kill_slots": [],
                    "aim_pitch_bias_degrees": bias,
                    "training_admitted": False,
                }
            )
            rows.append(row)
    return rows


cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.main())
