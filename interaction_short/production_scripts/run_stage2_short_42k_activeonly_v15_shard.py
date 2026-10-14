                      
"""Run one isolated Stage-2 short v15 category shard."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD_TAG = "capture-8f61470a6dbc-aarch64"
SOURCE_COMMIT = "8f61470a6dbca496990b79898d5ba26cfd492bb0"
BUILD_LOCK = ROOT / "locks" / f"{BUILD_TAG}.sha256"
SEMANTIC_REVISION = "v15_random_fire_visualfix_nocrosshair_nocasings"
OVERLAY = ROOT / "configs/capture_client_stage2_v15_no_crosshair_no_casings.cfg"
CONTINUOUS_WEAPONS = {"Blaster", "MachineGun", "Electro", "Hagar"}
BURST_PROGRAMS = {"short_burst", "double_burst"}

os.environ["XONOTIC_CAPTURE_ROOT"] = str(ROOT)
os.environ["XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG"] = BUILD_TAG
os.environ["XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT"] = SOURCE_COMMIT
os.environ["XONOTIC_BUILD_GLOB"] = f"build/{BUILD_TAG}"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "production_scripts"))

import run_stage2_motion_42k_activeonly_v14_shard as v14              
from pilot_scripts import build_samples_v15 as pilot              
import xonotic_stage2_causal_formal as causal              


quota = v14.quota
quota.pilot = pilot
quota.paired.pilot = pilot
quota.BUILD_TAG = BUILD_TAG
quota.SOURCE_COMMIT = SOURCE_COMMIT
quota.BUILD_LOCK = BUILD_LOCK
quota.paired.BUILD_TAG = BUILD_TAG
quota.paired.SOURCE_COMMIT = SOURCE_COMMIT
quota.paired.BUILD_LOCK = BUILD_LOCK
v14.pilot = pilot
v14.SEMANTIC_REVISION = SEMANTIC_REVISION
v14.CROSSHAIR_OVERLAY = OVERLAY
_v14_validate_manifest = v14.validate_manifest


def validate_manifest(
    manifest_path: Path,
    metadata_path: Path,
    shard_index: int,
    shard_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, report = _v14_validate_manifest(
        manifest_path, metadata_path, shard_index, shard_count
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    checks = {
        "semantic_revision_v15": metadata.get("semantic_revision")
        == SEMANTIC_REVISION,
        "v15_build_tag": metadata.get("build_tag") == BUILD_TAG,
        "v15_source_commit": metadata.get("source_commit") == SOURCE_COMMIT,
        "raw_avi_retention_disabled": metadata.get("raw_avi_retention")
        is False,
        "frustum_tolerance_1_04": float(
            (metadata.get("distribution_policy") or {}).get(
                "frustum_tolerance_scale", -1
            )
        )
        == 1.04,
        "shell_casings_disabled": (
            metadata.get("distribution_policy") or {}
        ).get("shell_casings_visible")
        is False,
    }
    for row in rows:
        active = row["active_scenario"]
        outcome = str(active["intent_outcome"])
        weapon = str(active["weapon"])
        design = active["causal_design"]
        program = design["fire_program"]
        name = str(program["name"])
        windows = program["windows"]
        row_checks = {
            "semantic_revision": row.get("semantic_revision")
            == SEMANTIC_REVISION,
            "raw_avi_disabled": row.get("raw_avi_audit") is False,
            "source_commit": active.get("source_commit_required")
            == SOURCE_COMMIT,
            "transform_record": (
                row.get("v15_transform") or {}
            ).get("schema_version")
            == "xonotic-stage2-short-v15-transform-v1",
            "latest_fire_end": all(
                int(window["start_output_tick"])
                + int(window["duration_ticks"])
                <= 224
                for window in windows
            ),
            "no_fire_contract": outcome != "no_fire" or name == "none",
            "kill_single_contract": outcome != "kill"
            or name == "single_tap",
            "burst_scope": name not in BURST_PROGRAMS
            or (
                weapon in CONTINUOUS_WEAPONS
                and outcome in {"miss", "hit_survive"}
            ),
            "crylink_release_gated": weapon != "Crylink"
            or name not in BURST_PROGRAMS,
        }
        if not all(row_checks.values()):
            raise RuntimeError(
                f"v15 row checks failed key={row.get('sample_key')}: "
                f"{row_checks}"
            )
        validation_policy = (
            "visible_no_response"
            if name == "none"
            else "sustained_tracking"
        )
        causal.validate_fire_program(
            program, policy=validation_policy, design=design
        )
    checks["all_rows_v15_fire_contract"] = True
    if not all(checks.values()):
        raise RuntimeError(f"v15 manifest metadata checks failed: {checks}")
    report["v15_checks"] = checks
    return rows, report


quota.validate_manifest = validate_manifest


def training_candidate_record(
    row: dict[str, Any], active: dict[str, Any]
) -> dict[str, Any]:
    record = v14.training_candidate_record(row, active)
    program = row["active_scenario"]["causal_design"]["fire_program"]
    record.update(
        {
            "semantic_revision": SEMANTIC_REVISION,
            "crosshair_visible": False,
            "shell_casings_visible": False,
            "raw_avi_retained": False,
            "fire_program_name": str(program["name"]),
            "fire_program_windows": program["windows"],
        }
    )
    return record


quota.training_candidate_record = training_candidate_record


if __name__ == "__main__":
    raise SystemExit(quota.main())
