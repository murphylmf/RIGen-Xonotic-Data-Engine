                      
"""Create a third QA-only replacement for the recurrent Shotgun edge gap."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path


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
REP2_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v2"
)
REP2_MANIFEST = REP2_ROOT / "input.jsonl"
REP2_OUTPUT = (
    ROOT / "stage2_weapon_balanced_review_v4_replenishment_v2_output"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v3"
)
SHARD_COUNT = 4


def materialize() -> list[dict]:
    source_rows = capture.load_jsonl(REP2_MANIFEST)
    if len(source_rows) != 1:
        raise capture.CaptureFailure(
            "stage2_v4_replenishment_v3_source_shape",
            str(len(source_rows)),
        )
    source = source_rows[0]
    source_id = str(source["episode_id"])
    terminal = [
        row
        for path in sorted(
            (REP2_OUTPUT / "manifests/shards").glob(
                "shard-*-of-*/rejects.jsonl"
            )
        )
        for row in capture.load_jsonl(path)
        if row.get("terminal") is True
    ]
    if (
        len(terminal) != 1
        or str(terminal[0]["episode_id"]) != source_id
    ):
        raise capture.CaptureFailure(
            "stage2_v4_replenishment_v3_terminal_accounting",
            capture.canonical_json(terminal),
        )
    logical_id = str(
        source["weapon_balanced_review_design"][
            "replacement_for_episode_id"
        ]
    )
    logical = {
        str(row["episode_id"]): row
        for row in capture.load_jsonl(BASE_MANIFEST)
    }[logical_id]
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
    design["fire_seed"] = 16_450_001
    aim = design["weapon_balanced_aim_program"]
    old_direction = float(aim["offset_direction_deg"])
    aim["offset_direction_deg"] = 90.0
    aim_seed = 16_400_001
    aim["seed"] = aim_seed
    style = str(aim["motor_profile"]["style"])
    aim["motor_profile"] = causal.humanized_aim_motor_profile(
        aim_seed, style
    )
    causal.validate_weapon_balanced_aim_program(aim)
    row.update(
        {
            "episode_id": f"{logical_id}_oprep03",
            "candidate_kind": (
                "stage2_weapon_balanced_review_v4_"
                "operational_replenishment_v3"
            ),
            "candidate_status": (
                "static_certified_third_operational_replacement_"
                "pending_live_capture"
            ),
            "training_stage": (
                "stage2_weapon_balanced_review_v4_"
                "operational_replenishment_v3_only"
            ),
            "canary_role": (
                f"{logical['canary_role']}_"
                "operational_replacement_v3"
            ),
            "assigned_shard": 0,
            "target_ordinal": 22_000,
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
            "stage2_v4_replenishment_v3_exogenous_drift",
            logical_id,
        )
    certificate = v4.v3_builder.static_action_certificate(row)
    certificate["schema_version"] = (
        "xonotic-stage2-weapon-balanced-v4-operational-"
        "replenishment-v3-static-action-certificate-v1"
    )
    if not certificate["passed"]:
        raise capture.CaptureFailure(
            "stage2_v4_replenishment_v3_static_action_failed",
            row["episode_id"],
        )
    row["weapon_balanced_review_design"].update(
        {
            "schema_version": (
                "xonotic-stage2-weapon-balanced-review-v4-"
                "operational-replenishment-design-v3"
            ),
            "replacement_for_episode_id": logical_id,
            "replacement_for_operational_episode_id": source_id,
            "replacement_scope": "terminal_qa_failure_only",
            "rep2_row_sha256": hashlib.sha256(
                capture.canonical_json(source).encode("utf-8")
            ).hexdigest(),
            "terminal_rejection_sha256": hashlib.sha256(
                capture.canonical_json(terminal[0]).encode("utf-8")
            ).hexdigest(),
            "technical_failure_signature": (
                "one_server_tick_gap_immediately_after_second_"
                "shot_for_left_edge_event_path"
            ),
            "aim_seed": aim_seed,
            "fire_seed": design["fire_seed"],
            "additional_fire_window_shift_ticks": 8,
            "offset_direction_deg_before": old_direction,
            "offset_direction_deg_after": 90.0,
            "aim_arm_preserved": True,
            "aim_direction_changed_for_technical_qa": True,
            "direction_change_outcome_conditioned": False,
            "outcome_used_for_individual_admission": False,
            "runtime_action_fallback": False,
            "runtime_geometry_fallback": False,
            "runtime_outcome_fallback": False,
            "formal_collection_authorized": False,
            "static_action_certificate": certificate,
        }
    )
    causal.validate_scenario_contract(row)
    rows = [row]

    input_text = v4.canonical_lines(rows)
    v4.write_once_or_verify(
        OUTPUT_ROOT / "input.jsonl", input_text
    )
    shards = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = rows if shard_index == 0 else []
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
    rep2_metadata = json.loads(
        (REP2_ROOT / "MANIFEST_METADATA.json").read_text(
            encoding="utf-8"
        )
    )
    metadata = {
        "schema_version": (
            "xonotic-stage2-weapon-balanced-review-v4-"
            "operational-replenishment-manifest-v3"
        ),
        "source_commit": rep2_metadata["source_commit"],
        "data_spec_sha256": rep2_metadata["data_spec_sha256"],
        "rep2_manifest": {
            "path": str(REP2_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(REP2_MANIFEST),
        },
        "rows": 1,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "replacement_scope": "terminal_qa_failure_only",
        "realized_outcome_read_by_generator": False,
        "aim_arm_preserved": True,
        "aim_direction_changed_for_technical_qa": True,
        "review": {
            "rows": 1,
            "shard_count": SHARD_COUNT,
            "shards": shards,
        },
        "replacement_for_episode_ids": [logical_id],
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_weapon_balanced_review_v4.py",
                "scripts/prepare_stage2_weapon_balanced_review_v4_replenishment_v3.py",
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
                "logical_slot": rows[0][
                    "weapon_balanced_review_design"
                ]["replacement_for_episode_id"],
                "arm": rows[0]["causal_design"]["aim_policy"],
                "direction_deg": rows[0]["causal_design"][
                    "weapon_balanced_aim_program"
                ]["offset_direction_deg"],
                "outcome_read": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
