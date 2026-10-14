                      
"""Live-only Stormkeep/Vortex tick calibration for the first encounter."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "scan_long60_runningman_stormkeep_hitscan_live_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_stormkeep_vortex_tick_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import replacement calibration: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


CALIBRATION_ID = "long60_stormkeep_vortex_tick_live4_20260828_v2"
cal.CALIBRATION_ID = CALIBRATION_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID
cal.cal.CALIBRATION_ID = CALIBRATION_ID
cal.cal.DEFAULT_ARTIFACT_ROOT = cal.DEFAULT_ARTIFACT_ROOT
cal.cal.DEFAULT_OUTPUT_ROOT = cal.DEFAULT_OUTPUT_ROOT


def choose_rows() -> list[dict[str, Any]]:
    source = cal.SOURCE_ROWS
    rows = []
    for first_tick in (534, 541, 554, 560):
        row = next(
            dict(item)
            for item in source
            if item["template"] == "four_distinct"
            and item["weapon"] == "Vortex"
            and int(item["kill_count"]) == 0
        )
        index = len(rows)
        row.update(
            {
                "manifest_index": index,
                "calibration_index": index,
                "episode_id": f"l60v7_stormkeep_vortex_firsttick_{first_tick}",
                "calibration_variant": f"firsttick_{first_tick}",
                "split": "test",
                "map": "stormkeep",
                "gametype": "dm",
                "anchor_id": cal.REPLACEMENTS["stormkeep"]["anchor_id"],
                "trajectory_scale": 0.75,
                "kill_count": 0,
                "kill_slots": [],
                "semiautomatic_primary_server_ticks": [
                    first_tick,
                    1527,
                    2602,
                    3517,
                ],
                "training_admitted": False,
            }
        )
        rows.append(row)
    return rows


cal.cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.cal.main())
