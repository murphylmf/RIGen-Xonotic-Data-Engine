                      
"""Live-only 2-template x 3-hitscan qualification for a Boil DM anchor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "run_long60_ref42_v7_hitscan_live_calibration.py"
)
SPEC = importlib.util.spec_from_file_location("long60_boil_scale050_scan_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import calibration module: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


SCAN_ID = "long60_boil_scale050_hitscan_live6_20260828_v1"
cal.CALIBRATION_ID = SCAN_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID
SOURCE_ROWS = cal.v7.distribution_rows()
cal.v7.MAPS["boil"] = {
    "gametype": "dm",
    "anchor_id": "boil_stage1_pair_midpoint_scale050",
    "player_origin": [702.5, -675.2, 228.8],
    "enemy_reference_origin": [699.3, -483.2, 228.8],
    "trajectory_scale": 0.5,
    "environment_text": (
        "A compact futuristic arena built from dark brushed metal, grey concrete, "
        "black grating, and angular wall panels. Bright red illuminated trim, red "
        "door frames, white utility lights, stairs, balconies, and narrow corridors "
        "give the space a clean high-contrast industrial look."
    ),
    "prompt_provenance_sample_id": "manual_visual_boil_duel_rollout_v1_20260828",
}


def choose_rows() -> list[dict[str, Any]]:
    rows = []
    for template in sorted(cal.v7.ORIGINAL_TEMPLATES):
        for weapon in sorted(cal.v7.WEAPONS):
            row = next(
                dict(item)
                for item in SOURCE_ROWS
                if item["template"] == template
                and item["map"] == "catharsis"
                and item["weapon"] == weapon
                and int(item["kill_count"]) == 0
            )
            index = len(rows)
            config = cal.v7.MAPS["boil"]
            row.update(
                {
                    "manifest_index": index,
                    "calibration_index": index,
                    "episode_id": f"l60v7boil_{template}_{weapon.lower()}",
                    "split": "test",
                    "map": "boil",
                    "gametype": "dm",
                    "anchor_id": config["anchor_id"],
                    "trajectory_scale": config["trajectory_scale"],
                    "kill_count": 0,
                    "kill_slots": [],
                    "training_admitted": False,
                }
            )
            rows.append(row)
    return rows


cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.main())
