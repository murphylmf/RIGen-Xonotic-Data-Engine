                      
"""Test a -3 degree Vortex pitch floor with the formal camera trajectory."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "calibrate_long60_stormkeep_controlled_vortex_shared_action_tick_v2.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_stormkeep_vortex_pitch_floor_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import shared-action tick calibration: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


CALIBRATION_ID = "long60_stormkeep_ctrl_vortex_pitch_floor_20260828_v3"
PITCH_FLOOR_DEGREES = -3.0
ORIGINAL_PRIMARY_TICKS = (458, 1027, 2142, 3012, 3549)
base.CALIBRATION_ID = CALIBRATION_ID
base.CANDIDATE_TICKS = ORIGINAL_PRIMARY_TICKS
base.base.cal.CALIBRATION_ID = CALIBRATION_ID
base.base.cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
base.base.cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID


def write_pitch_floor_actions(path: Path) -> None:
    with base.base.FORMAL_ACTION.open(newline="", encoding="utf-8") as handle:
        seed_line = handle.readline()
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError("formal action CSV has no header")
    source_pitch = -3.0
    realized_pitch = -3.0
    for row in rows:
        source_pitch += float(row["pitch_delta"])
        tick = int(row["tick"])
        target_pitch = (
            source_pitch if tick < base.base.cal.v7.base.capture.WARMUP_TICKS
            else max(PITCH_FLOOR_DEGREES, source_pitch)
        )
        row["pitch_delta"] = f"{target_pitch - realized_pitch:.9f}"
        realized_pitch = target_pitch
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        handle.write(seed_line)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


base.write_candidate_actions = write_pitch_floor_actions
_prepare = base.prepare


def prepare(artifact_root: Path) -> None:
    _prepare(artifact_root)
    prepared_path = artifact_root.resolve() / "PREPARED.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared.update(
        {
            "schema_version": "xonotic-long60-v7-vortex-pitch-floor-calibration-v3",
            "pitch_floor_degrees": PITCH_FLOOR_DEGREES,
            "candidate_primary_server_ticks": list(ORIGINAL_PRIMARY_TICKS),
        }
    )
    base.base.cal.v7.prod.write_json_atomic(prepared_path, prepared)


base.base.cal.prepare = prepare


if __name__ == "__main__":
    raise SystemExit(base.base.cal.main())
