                      
"""Scan Stormkeep Vortex pitch bias across all slot-0/slot-3 models."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "calibrate_long60_stormkeep_controlled_vortex_shared_action_models_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_stormkeep_vortex_pitch_bias_models_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import shared-action calibration: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


CALIBRATION_ID = "long60_stormkeep_ctrl_vortex_pitch_bias_models_20260828_v4"
PITCH_BIASES = (1.0, 2.0, 3.0)
base.CALIBRATION_ID = CALIBRATION_ID
base.cal.CALIBRATION_ID = CALIBRATION_ID
base.cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
base.cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID
_shared_rows = base.choose_rows


def choose_rows() -> list[dict[str, Any]]:
    rows = []
    for prototype_index, prototype in enumerate(_shared_rows()):
        for bias in PITCH_BIASES:
            row = dict(prototype)
            index = len(rows)
            row.update(
                {
                    "manifest_index": index,
                    "calibration_index": index,
                    "episode_id": (
                        f"l60v7_pitch_bias_model_{prototype_index:02d}_p{int(bias)}"
                    ),
                    "aim_pitch_bias_degrees": bias,
                    "split": "test",
                    "kill_count": 0,
                    "kill_slots": [],
                    "training_admitted": False,
                }
            )
            rows.append(row)
    return rows


base.choose_rows = choose_rows
base.cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(base.cal.main())
