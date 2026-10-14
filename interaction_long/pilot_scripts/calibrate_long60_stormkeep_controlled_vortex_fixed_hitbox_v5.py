                      
"""Re-run the shared-action model matrix with canonical hitbox restoration."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "calibrate_long60_stormkeep_controlled_vortex_shared_action_models_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_stormkeep_fixed_hitbox_calibration_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import shared-action calibration: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


CALIBRATION_ID = "long60_stormkeep_ctrl_vortex_fixed_hitbox_20260828_v5"
base.CALIBRATION_ID = CALIBRATION_ID
base.cal.CALIBRATION_ID = CALIBRATION_ID
base.cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
base.cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID


if __name__ == "__main__":
    raise SystemExit(base.cal.main())
