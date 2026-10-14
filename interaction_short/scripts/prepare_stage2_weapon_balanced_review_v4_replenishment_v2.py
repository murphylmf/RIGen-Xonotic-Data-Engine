                      
"""Create a second QA-only replacement for terminal V4 rep-v1 failures.

The logical weapon/arm/exogenous slot and left/right aim sector are preserved.
For the reproducible Shotgun left-edge snapshot gap, the within-sector angle
is moved from 180 to 165 degrees and fire windows move by another eight ticks.
No realized hit/miss outcome is read.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_weapon_balanced_review_v4 as v4              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


BASE_MANIFEST = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4"
    / "input.jsonl"
)
REP1_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v1"
)
REP1_MANIFEST = REP1_ROOT / "input.jsonl"
REP1_OUTPUT = (
    ROOT / "stage2_weapon_balanced_review_v4_replenishment_v1_output"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v2"
)
SHARD_COUNT = 4


def journal_rows(name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (REP1_OUTPUT / "manifests/shards").glob(
            f"shard-*-of-*/{name}.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def aim_sector(angle: float) -> str:
    normalized = ((float(angle) + 180.0) % 360.0) - 180.0
    if abs(normalized) >= 135.0:
        return "left"
    if abs(normalized) <= 45.0:
        return "right"
    return "vertical"


def materialize() -> list[dict[str, Any]]:
    base_by_id = {
        str(row["episode_id"]): row
        for row in capture.load_jsonl(BASE_MANIFEST)
    }
    rep1_by_id = {
        str(row["episode_id"]): row
        for row in capture.load_jsonl(REP1_MANIFEST)
    }
    accepted = {
        str(row["episode_id"])
        for row in journal_rows("accepted")
    }
    terminal = {
        str(row["episode_id"]): row
        for row in journal_rows("rejects")
        if row.get("terminal") is True
    }
    missing = set(rep1_by_id) - accepted
    if missing != set(terminal) or not missing:
        raise capture.CaptureFailure(
            "stage2_v4_replenishment_v2_terminal_accounting",
            capture.canonical_json(
                {
                    "missing": sorted(missing),
                    "terminal": sorted(terminal),
                }
            ),
        )

    rows: list[dict[str, Any]] = []
    for ordinal, rep1_id in enumerate(sorted(missing)):
        source = rep1_by_id[rep1_id]
        logical_id = str(
            source["weapon_balanced_review_design"][
                "replacement_for_episode_id"
            ]
        )
        logical = base_by_id[logical_id]
        row = copy.deepcopy(source)
        design = row["causal_design"]
        for window in design["fire_program"]["windows"]:
            window["start_output_tick"] = (
                int(window["start_output_tick"]) + 8
            )
        fire_ticks = [
            int(window["start_output_tick"])
            for window in design["fire_program"]["windows"]
        ]
        design["fire_output_ticks"] = fire_ticks
        design["fire_seed"] = 16_300_000 + ordinal + 1
        aim = design["weapon_balanced_aim_program"]
        old_direction = float(aim["offset_direction_deg"])
        new_direction = old_direction
        if str(aim["arm"]) in {"edge_graze", "near_miss"}:
            if old_direction >= 179.0:
                new_direction = 165.0
            elif old_direction <= -179.0:
                new_direction = -165.0
        aim["offset_direction_deg"] = new_direction
        aim_seed = 16_250_000 + ordinal + 1
        aim["seed"] = aim_seed
        if isinstance(aim.get("motor_profile"), dict):
            style = str(aim["motor_profile"]["style"])
            aim["motor_profile"] = (
                causal.humanized_aim_motor_profile(
                    aim_seed, style
                )
            )
        elif isinstance(aim.get("random_aim_program"), dict):
            aim["random_aim_program"] = v4.random_aim_program(
                aim_seed,
                str(aim["arm"]),
                str(row["weapon"]),
                set(fire_ticks),
            )
        causal.validate_weapon_balanced_aim_program(aim)
        if aim_sector(old_direction) != aim_sector(new_direction):
            raise capture.CaptureFailure(
                "stage2_v4_replenishment_v2_aim_sector_drift",
                logical_id,
            )

        row.update(
            {
                "episode_id": f"{logical_id}_oprep02",
                "candidate_kind": (
                    "stage2_weapon_balanced_review_v4_"
                    "operational_replenishment_v2"
                ),
                "candidate_status": (
                    "static_certified_second_operational_"
                    "replacement_pending_live_capture"
                ),
                "training_stage": (
                    "stage2_weapon_balanced_review_v4_"
                    "operational_replenishment_v2_only"
                ),
                "canary_role": (
                    f"{logical['canary_role']}_"
                    "operational_replacement_v2"
                ),
                "assigned_shard": ordinal % SHARD_COUNT,
                "target_ordinal": 21_000 + ordinal,
            }
        )
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        if (
            row["exogenous_contract_sha256"]
            != logical["exogenous_contract_sha256"]
        ):
            raise capture.CaptureFailure(
                "stage2_v4_replenishment_v2_exogenous_drift",
                logical_id,
            )
        certificate = v4.v3_builder.static_action_certificate(row)
        certificate["schema_version"] = (
            "xonotic-stage2-weapon-balanced-v4-operational-"
            "replenishment-v2-static-action-certificate-v1"
        )
        if not certificate["passed"]:
            raise capture.CaptureFailure(
                "stage2_v4_replenishment_v2_static_action_failed",
                row["episode_id"],
            )
        row["weapon_balanced_review_design"].update(
            {
                "schema_version": (
                    "xonotic-stage2-weapon-balanced-review-v4-"
                    "operational-replenishment-design-v2"
                ),
                "replacement_for_episode_id": logical_id,
                "replacement_for_operational_episode_id": rep1_id,
                "replacement_scope": "terminal_qa_failure_only",
                "rep1_row_sha256": hashlib.sha256(
                    capture.canonical_json(source).encode("utf-8")
                ).hexdigest(),
                "terminal_rejection_sha256": hashlib.sha256(
                    capture.canonical_json(
                        terminal[rep1_id]
                    ).encode("utf-8")
                ).hexdigest(),
                "technical_failure_signature": (
                    "one_server_tick_gap_immediately_after_"
                    "second_shot"
                ),
                "aim_seed": aim_seed,
                "fire_seed": design["fire_seed"],
                "additional_fire_window_shift_ticks": 8,
                "offset_direction_deg_before": old_direction,
                "offset_direction_deg_after": new_direction,
                "aim_direction_sector_preserved": True,
                "outcome_used_for_individual_admission": False,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
                "runtime_outcome_fallback": False,
                "formal_collection_authorized": False,
                "static_action_certificate": certificate,
            }
        )
        causal.validate_scenario_contract(row)
        rows.append(row)

    input_text = v4.canonical_lines(rows)
    v4.write_once_or_verify(
        OUTPUT_ROOT / "input.jsonl", input_text
    )
    shards: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = v4.canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        v4.write_once_or_verify(shard_path, shard_text)
        shards.append(
            {
                "shard_index": shard_index,
                "path": str(shard_path.relative_to(ROOT)),
                "rows": len(shard_rows),
                "sha256": hashlib.sha256(
                    shard_text.encode("utf-8")
                ).hexdigest(),
            }
        )
    rep1_metadata = json.loads(
        (REP1_ROOT / "MANIFEST_METADATA.json").read_text(
            encoding="utf-8"
        )
    )
    metadata = {
        "schema_version": (
            "xonotic-stage2-weapon-balanced-review-v4-"
            "operational-replenishment-manifest-v2"
        ),
        "source_commit": rep1_metadata["source_commit"],
        "data_spec_sha256": rep1_metadata["data_spec_sha256"],
        "rep1_manifest": {
            "path": str(REP1_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(REP1_MANIFEST),
        },
        "rows": len(rows),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "replacement_scope": "terminal_qa_failure_only",
        "realized_outcome_read_by_generator": False,
        "aim_direction_sector_preserved": True,
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shards,
        },
        "replacement_for_episode_ids": sorted(
            row["weapon_balanced_review_design"][
                "replacement_for_episode_id"
            ]
            for row in rows
        ),
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_weapon_balanced_review_v4.py",
                "scripts/prepare_stage2_weapon_balanced_review_v4_replenishment_v2.py",
            )
        },
    }
    v4.write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        capture.canonical_json(
            {
                "output": str(OUTPUT_ROOT),
                "rows": len(rows),
                "logical_slots": [
                    row["weapon_balanced_review_design"][
                        "replacement_for_episode_id"
                    ]
                    for row in rows
                ],
                "outcome_read": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
