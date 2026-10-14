                      
"""Live-only angle scan for DM replacements of render-unstable maps."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name("scan_long60_map_anchor_angles_live_v1.py")
SPEC = importlib.util.spec_from_file_location("long60_replacement_angle_scan_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import angle scan: {BASE_PATH}")
scan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scan
SPEC.loader.exec_module(scan)


SCAN_ID = "long60_replacement_map_angle_live_scan32_20260828_v1"
scan.SCAN_ID = SCAN_ID
scan.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
scan.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID
scan.MAP_ANCHORS = {
    "atelier": {
        "gametype": "dm",
        "player_origin": [1734.3, 486.9, 216.0],
        "trajectory_scale": 0.75,
        "environment_text": "manual live-scan placeholder",
        "prompt_provenance_sample_id": "stage1_preflight_atelier_close_wp0002_wp0019",
    },
    "boil": {
        "gametype": "dm",
        "player_origin": [180.8, 204.1, -69.2],
        "trajectory_scale": 0.5,
        "environment_text": "manual live-scan placeholder",
        "prompt_provenance_sample_id": "stage1_preflight_boil_close_wp0017_wp0046",
    },
    "runningman": {
        "gametype": "dm",
        "player_origin": [-17.8, -277.3, 216.0],
        "trajectory_scale": 0.75,
        "environment_text": "manual live-scan placeholder",
        "prompt_provenance_sample_id": "stage1_preflight_runningman_near_wp0038_wp0041",
    },
    "stormkeep": {
        "gametype": "dm",
        "player_origin": [-84.5, -470.2, -168.0],
        "trajectory_scale": 0.75,
        "environment_text": "manual live-scan placeholder",
        "prompt_provenance_sample_id": "stage1_preflight_stormkeep_near_wp0007_wp0020",
    },
}


if __name__ == "__main__":
    raise SystemExit(scan.main())
