                      
"""Test corrected Stormkeep Vortex pulse ticks with the formal camera action."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "calibrate_long60_stormkeep_controlled_vortex_shared_action_models_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_stormkeep_shared_action_tick_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import shared-action calibration: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


CALIBRATION_ID = "long60_stormkeep_ctrl_vortex_shared_action_tick_20260828_v2"
CANDIDATE_TICKS = (458, 1027, 2154, 3012, 3556)
base.cal.CALIBRATION_ID = CALIBRATION_ID
base.cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
base.cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID


def write_candidate_actions(path: Path) -> None:
    with base.FORMAL_ACTION.open(newline="", encoding="utf-8") as handle:
        seed_line = handle.readline()
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError("formal action CSV has no header")
    pulse_width = int(base.cal.v7.CONFIG["semiautomatic_primary_pulse_width_ticks"])
    for row in rows:
        tick = int(row["tick"])
        row["primary"] = str(
            int(any(start <= tick < start + pulse_width for start in CANDIDATE_TICKS))
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        handle.write(seed_line)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    actions = artifact_root / "actions" / "actions.csv"
    write_candidate_actions(actions)
    action_sha256 = base.cal.v7.base.sha256(actions)
    rows = base.choose_rows()
    for row in rows:
        scenario_path, timeline = base.cal.v7.build_episode_scenario(
            row, artifact_root, actions
        )
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["formal_collection_authorized"] = False
        scenario["training_admitted"] = False
        scenario["live_calibration"] = {
            "calibration_id": CALIBRATION_ID,
            "live_only": True,
            "formal_camera_action": True,
            "candidate_primary_server_ticks": list(CANDIDATE_TICKS),
            "candidate_action_sha256": action_sha256,
        }
        base.cal.v7.prod.write_json_atomic(scenario_path, scenario)
        row.update(
            {
                "semiautomatic_primary_server_ticks": list(CANDIDATE_TICKS),
                "scenario_path": base.cal.v7.prod.relative_to_root(scenario_path),
                "scenario_sha256": base.cal.v7.base.sha256(scenario_path),
                "actions_path": base.cal.v7.prod.relative_to_root(actions),
                "actions_sha256": action_sha256,
                "timeline_path": base.cal.v7.prod.relative_to_root(timeline),
                "timeline_sha256": base.cal.v7.base.sha256(timeline),
            }
        )
    manifest = artifact_root / "calibration_manifest.jsonl"
    base.cal.v7.prod.write_jsonl_atomic(manifest, rows)
    base.cal.v7.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-v7-shared-action-tick-calibration-v2",
            "calibration_id": CALIBRATION_ID,
            "case_count": len(rows),
            "formal_camera_action_sha256": base.cal.v7.base.sha256(base.FORMAL_ACTION),
            "candidate_action_sha256": action_sha256,
            "candidate_primary_server_ticks": list(CANDIDATE_TICKS),
            "slot0_models": sorted(
                {base.model_name(str(row["appearance_order"][0])) for row in rows}
            ),
            "slot3_models": sorted(
                {base.model_name(str(row["appearance_order"][3])) for row in rows}
            ),
            "live_only": True,
            "training_admitted": False,
        },
    )


base.cal.prepare = prepare


if __name__ == "__main__":
    raise SystemExit(base.cal.main())
