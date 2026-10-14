                      
"""Live-only timing sweep for Bromine angle-315 four-distinct Vortex."""

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
    "long60_bromine_a315_vortex_tick_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import calibration module: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


SCAN_ID = "long60_bromine_a315_vortex_tick_live6_20260828_v1"
FIRST_FIRE_TICKS = (550, 554, 558, 562, 566, 570)
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
    prototype = next(
        dict(row)
        for row in cal.v7.distribution_rows()
        if row["template"] == "four_distinct"
        and row["map"] == "bromine"
        and row["weapon"] == "Vortex"
        and int(row["kill_count"]) == 0
    )
    base_ticks = cal.v7.semiautomatic_primary_ticks(prototype)
    rows = []
    for index, first_tick in enumerate(FIRST_FIRE_TICKS):
        row = dict(prototype)
        row.update(
            {
                "manifest_index": index,
                "calibration_index": index,
                "episode_id": f"l60v7a315tick_four-distinct_t{first_tick}",
                "split": "test",
                "kill_count": 0,
                "kill_slots": [],
                "anchor_id": cal.v7.MAPS["bromine"]["anchor_id"],
                "semiautomatic_primary_server_ticks": [first_tick, *base_ticks[1:]],
                "calibration_variant": f"t{first_tick}",
                "training_admitted": False,
            }
        )
        rows.append(row)
    return rows


cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.main())
