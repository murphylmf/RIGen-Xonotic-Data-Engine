                      
"""Build a fail-closed replacement for one deterministic V2 policy reject."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import prepare_stage2_bias_correction_v1 as base
import prepare_stage2_bias_correction_v2 as v2
import xonotic_capture as capture
import xonotic_stage2_causal as causal


ROOT = capture.ROOT
SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_bias_correction_v2/input.jsonl"
)
SOURCE_REJECTS = (
    ROOT
    / "stage2_bias_correction_v2_output/manifests/shards/"
    "shard-000-of-004/rejects.jsonl"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_bias_correction_v2_replenishment_v1"
)
SOURCE_EPISODE_ID = (
    "s2biasv2_g01_p04_track_loss_reacquire_a01"
)
REPLACEMENT_EPISODE_ID = (
    "s2biasv2r1_g01_p04_track_loss_reacquire_a02"
)


def hard_rejection() -> dict[str, Any]:
    selected = [
        row
        for row in capture.load_jsonl(SOURCE_REJECTS)
        if row.get("episode_id") == SOURCE_EPISODE_ID
        and row.get("terminal") is True
        and row.get("retryable") is not True
    ]
    if len(selected) != 1:
        raise capture.CaptureFailure(
            "stage2_replenishment_terminal_evidence",
            f"episode={SOURCE_EPISODE_ID} rows={len(selected)}",
        )
    rejection = selected[0]
    if (
        rejection.get("reason") != "stage2_causal_qa_failed"
        or '"reacquired":false' not in str(rejection.get("detail"))
    ):
        raise capture.CaptureFailure(
            "stage2_replenishment_wrong_failure",
            capture.canonical_json(rejection),
        )
    return rejection


def build_row() -> dict[str, Any]:
    source = next(
        row
        for row in capture.load_jsonl(SOURCE_MANIFEST)
        if row["episode_id"] == SOURCE_EPISODE_ID
    )
    rejection = hard_rejection()
    row = copy.deepcopy(source)
    original_exogenous_sha256 = row[
        "exogenous_contract_sha256"
    ]
    row.update(
        {
            "episode_id": REPLACEMENT_EPISODE_ID,
            "assigned_shard": 0,
            "shard_count": 1,
            "category": (
                "stage2_bias_v2_replenishment_track_loss_reacquire"
            ),
            "candidate_kind": (
                "stage2_screen_miss_bias_correction_v2_replenishment_v1"
            ),
            "candidate_status": (
                "bounded_terminal_reject_replenishment_candidate"
            ),
            "training_stage": (
                "stage2_bounded_bias_correction_v2_replenishment_v1_only"
            ),
            "canary_role": (
                "stage2_bias_v2_replenishment_upper_left_"
                "track_loss_timing_window_opposite_direction"
            ),
        }
    )
    row["causal_design"]["aim_schedule"][
        "loss_yaw_offset_deg"
    ] = -38.0
    row["policy_labels"]["replenishment_reason"] = (
        "opposite_loss_direction_after_authoritative_self_knockback_"
        "prevented_reacquisition"
    )
    row["bias_correction_design"] = {
        **row["bias_correction_design"],
        "schema_version": (
            "xonotic-stage2-bias-correction-design-v2-"
            "replenishment-v1"
        ),
        "replenishment_arm": True,
        "loss_direction_deg": -38.0,
    }
    rejection_sha256 = hashlib.sha256(
        capture.canonical_json(rejection).encode("utf-8")
    ).hexdigest()
    row["replenishment_contract"] = {
        "schema_version": (
            "xonotic-stage2-terminal-replenishment-contract-v1"
        ),
        "superseded_episode_id": SOURCE_EPISODE_ID,
        "superseded_attempt_id": rejection["attempt_id"],
        "terminal_reason": rejection["reason"],
        "terminal_rejection_sha256": rejection_sha256,
        "diagnostic_path": rejection["diagnostic_path"],
        "changes": [
            "episode_id",
            "candidate_metadata",
            "aim_schedule.loss_yaw_offset_deg",
            "shard_assignment",
        ],
        "exogenous_geometry_changed": False,
        "outcome_observed_for_treatment_selection": False,
        "failure_gate_observed_for_replenishment": (
            "policy_reacquisition_only"
        ),
        "runtime_fallback": False,
    }
    row["exogenous_contract_sha256"] = (
        causal.exogenous_contract_sha256(row)
    )
    checks = {
        "same_counterfactual_group": (
            row["counterfactual_group_id"]
            == source["counterfactual_group_id"]
        ),
        "exogenous_contract_unchanged": (
            row["exogenous_contract_sha256"]
            == original_exogenous_sha256
        ),
        "opposite_loss_direction": (
            float(
                source["causal_design"]["aim_schedule"][
                    "loss_yaw_offset_deg"
                ]
            )
            == 38.0
            and float(
                row["causal_design"]["aim_schedule"][
                    "loss_yaw_offset_deg"
                ]
            )
            == -38.0
        ),
        "outcome_unassigned": (
            row["acceptance"]["actual_outcome"] is None
        ),
        "nontraining": (
            row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
        ),
    }
    causal.validate_scenario_contract(row)
    capture.validate_scenario_assets(row)
    causal.causal_action_rows(row)
    metrics = base.planned_treatment_metrics(row)
    checks.update(
        {
            "planned_center_before_fire": (
                metrics["center_before_first_fire"] is True
            ),
            "planned_reacquisition_after_fire": (
                metrics["acquisition_after_first_fire"] is True
            ),
            "planned_fire_error": (
                bool(metrics["fire_errors"])
                and min(metrics["fire_errors"]) >= 20.0
            ),
        }
    )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_replenishment_static_audit",
            capture.canonical_json(checks),
        )
    row["replenishment_contract"]["static_checks"] = checks
    return row


def materialize() -> dict[str, Any]:
    row = build_row()
    text = base.canonical_lines([row])
    shard = (
        OUTPUT_ROOT
        / "shards"
        / "shard-000-of-001.jsonl"
    )
    base.write_once_or_verify(OUTPUT_ROOT / "input.jsonl", text)
    base.write_once_or_verify(shard, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-bias-replenishment-manifest-v1"
        ),
        "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "source_manifest_sha256": capture.sha256_file(
            SOURCE_MANIFEST
        ),
        "source_commit": v2.RUNTIME_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(base.DATA_SPEC),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "actual_outcome_source": "authoritative_telemetry_only",
        "review": {
            "rows": 1,
            "counterfactual_families": 1,
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard),
                    "rows": 1,
                    "sha256": hashlib.sha256(
                        text.encode("utf-8")
                    ).hexdigest(),
                }
            ],
        },
    }
    base.write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    audit = {
        "schema_version": (
            "xonotic-stage2-bias-replenishment-audit-v1"
        ),
        "pass": True,
        "episode_id": row["episode_id"],
        "counterfactual_group_id": row[
            "counterfactual_group_id"
        ],
        "exogenous_contract_sha256": row[
            "exogenous_contract_sha256"
        ],
        "shot_error_program": row["causal_design"][
            "shot_error_schedule"
        ]["program"],
        "loss_yaw_offset_deg": row["causal_design"][
            "aim_schedule"
        ]["loss_yaw_offset_deg"],
        "replenishment_contract": row["replenishment_contract"],
    }
    base.write_once_or_verify(
        OUTPUT_ROOT / "DESIGN_AUDIT.json",
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
    )
    return audit


def main() -> int:
    print(json.dumps(materialize(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
