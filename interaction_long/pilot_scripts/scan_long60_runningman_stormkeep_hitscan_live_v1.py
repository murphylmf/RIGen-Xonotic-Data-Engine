                      
"""Live-only two-template/three-hitscan qualification for replacement DM maps."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "run_long60_ref42_v7_hitscan_live_calibration.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_runningman_stormkeep_hitscan_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import calibration module: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


SCAN_ID = "long60_runningman_stormkeep_hitscan_live12_20260828_v1"
cal.CALIBRATION_ID = SCAN_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID
SOURCE_ROWS = cal.v7.distribution_rows()
REPLACEMENTS = {
    "runningman": {
        "gametype": "dm",
        "anchor_id": "runningman_stage1_anchor_a180_scale075",
        "player_origin": [-17.8, -277.3, 216.0],
        "enemy_reference_origin": [-217.8, -277.3, 216.0],
        "trajectory_scale": 0.75,
        "environment_text": "manual live-scan placeholder",
        "prompt_provenance_sample_id": "stage1_preflight_runningman_near_wp0038_wp0041",
    },
    "stormkeep": {
        "gametype": "dm",
        "anchor_id": "stormkeep_stage1_anchor_a045_scale075",
        "player_origin": [-84.5, -470.2, -168.0],
        "enemy_reference_origin": [56.9213562373, -328.7786437627, -168.0],
        "trajectory_scale": 0.75,
        "environment_text": "manual live-scan placeholder",
        "prompt_provenance_sample_id": "stage1_preflight_stormkeep_near_wp0007_wp0020",
    },
}
cal.v7.MAPS.update(REPLACEMENTS)


def choose_rows() -> list[dict[str, Any]]:
    rows = []
    for map_name in sorted(REPLACEMENTS):
        for template in sorted(cal.v7.ORIGINAL_TEMPLATES):
            for weapon in sorted(cal.v7.WEAPONS):
                row = next(
                    dict(item)
                    for item in SOURCE_ROWS
                    if item["template"] == template
                    and item["weapon"] == weapon
                    and int(item["kill_count"]) == 0
                )
                index = len(rows)
                config = REPLACEMENTS[map_name]
                row.update(
                    {
                        "manifest_index": index,
                        "calibration_index": index,
                        "episode_id": f"l60v7repl_{map_name}_{template}_{weapon.lower()}",
                        "split": "test",
                        "map": map_name,
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
