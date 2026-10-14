                      
"""Cross-model tick sweep for Stormkeep controlled-return Vortex encounter 5."""

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
    "long60_stormkeep_controlled_vortex_models_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import final calibration: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


CALIBRATION_ID = "long60_stormkeep_controlled_vortex_models35_20260828_v1"
cal.CALIBRATION_ID = CALIBRATION_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID
LAST_TICKS = (3543, 3549, 3556, 3562, 3568)
MODEL_NAMES = (
    "erebus",
    "gakmasked",
    "ignis",
    "nyx",
    "pyria",
    "seraphina",
    "umbra",
)


def choose_rows() -> list[dict[str, Any]]:
    source = [
        dict(row)
        for row in cal.v7.distribution_rows()
        if row["template"] == "controlled_return"
        and row["map"] == "stormkeep"
        and row["weapon"] == "Vortex"
        and int(row["kill_count"]) == 0
    ]
    representative: dict[str, dict[str, Any]] = {}
    for row in source:
        actor4 = str(row["appearance_order"][3])
        model = actor4.split("_skin", 1)[0]
        representative.setdefault(model, row)
    missing = sorted(set(MODEL_NAMES) - set(representative))
    if missing:
        raise RuntimeError(f"no actor4 representatives for models: {missing}")

    rows = []
    for model in MODEL_NAMES:
        for last_tick in LAST_TICKS:
            row = dict(representative[model])
            index = len(rows)
            row.update(
                {
                    "manifest_index": index,
                    "calibration_index": index,
                    "episode_id": (
                        f"l60v7_stormkeep_ctrl_vortex_{model}_tick{last_tick}"
                    ),
                    "split": "test",
                    "kill_count": 0,
                    "kill_slots": [],
                    "semiautomatic_primary_server_ticks": [
                        458,
                        1027,
                        2142,
                        3012,
                        last_tick,
                    ],
                    "calibration_variant": f"{model}_tick{last_tick}",
                    "training_admitted": False,
                }
            )
            rows.append(row)
    return rows


cal.choose_rows = choose_rows


if __name__ == "__main__":
    raise SystemExit(cal.main())
