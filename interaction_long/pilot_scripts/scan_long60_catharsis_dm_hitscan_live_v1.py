                      
"""Live-only qualification of Catharsis in DM to avoid CTF match endings."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "run_long60_ref42_v7_hitscan_live_calibration.py"
)
SPEC = importlib.util.spec_from_file_location("long60_catharsis_dm_scan_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import calibration module: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


SCAN_ID = "long60_catharsis_dm_hitscan_live6_20260828_v1"
cal.CALIBRATION_ID = SCAN_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID
cal.v7.MAPS["catharsis"]["gametype"] = "dm"


def choose_rows() -> list[dict[str, Any]]:
    rows = [row for row in cal.choose_rows_original() if row["map"] == "catharsis"]
    for index, row in enumerate(rows):
        row.update(
            {
                "manifest_index": index,
                "calibration_index": index,
                "episode_id": row["episode_id"].replace("l60v7cal", "l60v7cathdm"),
                "gametype": "dm",
                "training_admitted": False,
            }
        )
    return rows


cal.choose_rows_original = cal.choose_rows
cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.main())
