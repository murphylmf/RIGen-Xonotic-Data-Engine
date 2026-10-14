                      
"""Validate the formal Stormkeep/controlled-return/Vortex shared action.

Unlike the earlier tick sweep, every case here uses the exact same action CSV
from the formal manifest.  The selected cases vary only the actor appearances,
which makes this a valid test of whether model/skin variation changes hits.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name(
    "run_long60_ref42_v7_hitscan_live_calibration.py"
)
SPEC = importlib.util.spec_from_file_location(
    "long60_stormkeep_shared_action_models_base", BASE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import live calibration: {BASE_PATH}")
cal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cal
SPEC.loader.exec_module(cal)


CALIBRATION_ID = "long60_stormkeep_ctrl_vortex_shared_action_models_20260828_v1"
cal.CALIBRATION_ID = CALIBRATION_ID
cal.DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
cal.DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID
FORMAL_ROOT = (
    ROOT
    / "manifests"
    / "stage2_long60_multi_enemy_ref42_multimap_hitscan_30h_20260828_v7"
)
FORMAL_ACTION = (
    FORMAL_ROOT
    / "action_programs"
    / "controlled_return"
    / "stormkeep"
    / "Vortex"
    / "actions.csv"
)
MODEL_NAMES = {
    "erebus",
    "gakmasked",
    "ignis",
    "nyx",
    "pyria",
    "seraphina",
    "umbra",
}


def model_name(appearance_id: str) -> str:
    return appearance_id.split("_skin", 1)[0]


def choose_rows() -> list[dict[str, Any]]:
    rows = [
        dict(row)
        for row in cal.v7.prod.load_jsonl(FORMAL_ROOT / "manifest.jsonl")
        if row["template"] == "controlled_return"
        and row["map"] == "stormkeep"
        and row["weapon"] == "Vortex"
        and int(row["kill_count"]) == 0
    ]
                                                                              
                                                                             
    uncovered = {(slot, model) for slot in (0, 3) for model in MODEL_NAMES}
    selected: list[dict[str, Any]] = []
    remaining = list(rows)
    while uncovered:
        scored = []
        for row in remaining:
            coverage = {
                (slot, model_name(str(row["appearance_order"][slot])))
                for slot in (0, 3)
            } & uncovered
            scored.append((len(coverage), -int(row["manifest_index"]), row, coverage))
        score, _negative_index, row, coverage = max(
            scored, key=lambda item: (item[0], item[1])
        )
        if score == 0:
            raise RuntimeError(f"could not cover appearance models: {sorted(uncovered)}")
        selected.append(row)
        uncovered -= coverage
        remaining.remove(row)

    for index, row in enumerate(selected):
        row.update(
            {
                "manifest_index": index,
                "calibration_index": index,
                "episode_id": f"l60v7_shared_action_models_{index:02d}",
                "split": "test",
                "kill_count": 0,
                "kill_slots": [],
                "training_admitted": False,
            }
        )
    return selected


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    rows = choose_rows()
    if not FORMAL_ACTION.is_file():
        raise FileNotFoundError(FORMAL_ACTION)
    formal_action_sha256 = cal.v7.base.sha256(FORMAL_ACTION)
    for row in rows:
        scenario_path, timeline = cal.v7.build_episode_scenario(
            row, artifact_root, FORMAL_ACTION
        )
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["formal_collection_authorized"] = False
        scenario["training_admitted"] = False
        scenario["live_calibration"] = {
            "calibration_id": CALIBRATION_ID,
            "live_only": True,
            "shared_formal_action": True,
            "formal_action_sha256": formal_action_sha256,
        }
        cal.v7.prod.write_json_atomic(scenario_path, scenario)
        row.update(
            {
                "scenario_path": cal.v7.prod.relative_to_root(scenario_path),
                "scenario_sha256": cal.v7.base.sha256(scenario_path),
                "actions_path": cal.v7.prod.relative_to_root(FORMAL_ACTION),
                "actions_sha256": formal_action_sha256,
                "timeline_path": cal.v7.prod.relative_to_root(timeline),
                "timeline_sha256": cal.v7.base.sha256(timeline),
            }
        )
    manifest = artifact_root / "calibration_manifest.jsonl"
    cal.v7.prod.write_jsonl_atomic(manifest, rows)
    cal.v7.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-v7-shared-action-model-calibration-v1",
            "calibration_id": CALIBRATION_ID,
            "case_count": len(rows),
            "formal_action_path": cal.v7.prod.relative_to_root(FORMAL_ACTION),
            "formal_action_sha256": formal_action_sha256,
            "slot0_models": sorted(
                {model_name(str(row["appearance_order"][0])) for row in rows}
            ),
            "slot3_models": sorted(
                {model_name(str(row["appearance_order"][3])) for row in rows}
            ),
            "live_only": True,
            "training_admitted": False,
        },
    )


cal.choose_rows = choose_rows
cal.prepare = prepare


if __name__ == "__main__":
    raise SystemExit(cal.main())
