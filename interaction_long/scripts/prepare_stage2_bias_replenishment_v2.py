                      
"""Revise the six-row center-screen family for policy compatibility.

The original exact-crosshair center geometry is structurally incompatible
with delayed_acquisition: the target is already acquired before the declared
delay.  This replacement keeps the target in the center screen cell while
placing it just outside the <=3 degree acquisition threshold.  The complete
counterfactual family is replaced together so exogenous matching is retained.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter
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
    "shard-002-of-004/rejects.jsonl"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_bias_correction_v2_replenishment_v2"
)
SOURCE_GROUP_ID = "s2biasv2_g15"
REPLACEMENT_GROUP_ID = "s2biasv2r2_g15"
OBSERVED_INCOMPATIBLE_EPISODE = (
    "s2biasv2_g15_p02_delayed_acquisition_a02"
)
NEW_VIEW_YAW_OFFSET_DEG = 3.0
NEW_VIEW_PITCH_OFFSET_DEG = 2.0


def observed_structural_rejection() -> dict[str, Any]:
    selected = [
        row
        for row in capture.load_jsonl(SOURCE_REJECTS)
        if row.get("episode_id") == OBSERVED_INCOMPATIBLE_EPISODE
        and row.get("terminal") is True
        and row.get("retryable") is not True
    ]
    if len(selected) != 1:
        raise capture.CaptureFailure(
            "stage2_center_family_terminal_evidence",
            f"episode={OBSERVED_INCOMPATIBLE_EPISODE} rows={len(selected)}",
        )
    rejection = selected[0]
    required = {
        '"acquired_after_delay":false',
        '"response_delayed":false',
    }
    if (
        rejection.get("reason") != "stage2_causal_qa_failed"
        or not all(
            token in str(rejection.get("detail"))
            for token in required
        )
    ):
        raise capture.CaptureFailure(
            "stage2_center_family_wrong_failure",
            capture.canonical_json(rejection),
        )
    return rejection


def first_planned_acquisition(
    row: dict[str, Any],
) -> tuple[float, int | None]:
    metrics = base.planned_treatment_metrics(row)
    errors = [float(value) for value in metrics["errors"]]
    first = next(
        (
            index
            for index, value in enumerate(errors)
            if value <= causal.TARGET_CENTER_THRESHOLD_DEG
        ),
        None,
    )
    return errors[0], first


def build_rows() -> list[dict[str, Any]]:
    sources = [
        row
        for row in capture.load_jsonl(SOURCE_MANIFEST)
        if row["counterfactual_group_id"] == SOURCE_GROUP_ID
    ]
    if len(sources) != 6:
        raise capture.CaptureFailure(
            "stage2_center_family_source_cardinality",
            str(len(sources)),
        )
    rejection = observed_structural_rejection()
    rejection_sha256 = hashlib.sha256(
        capture.canonical_json(rejection).encode("utf-8")
    ).hexdigest()
    rows: list[dict[str, Any]] = []
    for source in sources:
        original_initial_error, _ = first_planned_acquisition(
            source
        )
        row = copy.deepcopy(source)
        source_episode_id = str(source["episode_id"])
        row.update(
            {
                "episode_id": source_episode_id.replace(
                    SOURCE_GROUP_ID, REPLACEMENT_GROUP_ID, 1
                ),
                "counterfactual_group_id": REPLACEMENT_GROUP_ID,
                "anchor_id": f"{REPLACEMENT_GROUP_ID}_pair",
                "assigned_shard": 0,
                "shard_count": 1,
                "category": (
                    "stage2_bias_v2_center_family_policy_compatible"
                ),
                "candidate_kind": (
                    "stage2_screen_miss_bias_correction_v2_"
                    "center_family_replenishment_v2"
                ),
                "candidate_status": (
                    "bounded_structural_family_revision_candidate"
                ),
                "training_stage": (
                    "stage2_bounded_bias_correction_v2_"
                    "center_family_replenishment_only"
                ),
            }
        )
        row["initial_screen_design"].update(
            {
                "view_yaw_offset_deg": NEW_VIEW_YAW_OFFSET_DEG,
                "view_pitch_offset_deg": NEW_VIEW_PITCH_OFFSET_DEG,
            }
        )
        target_yaw, target_pitch = causal.yaw_pitch_toward(
            row["player"]["origin"], row["enemy"]["origin"]
        )
        row["player"]["yaw"] = round(
            causal.wrap_angle(
                target_yaw + NEW_VIEW_YAW_OFFSET_DEG
            ),
            6,
        )
        row["player"]["pitch"] = round(
            min(
                89.0,
                max(
                    -89.0,
                    target_pitch + NEW_VIEW_PITCH_OFFSET_DEG,
                ),
            ),
            6,
        )
        row["canary_role"] = str(row["canary_role"]).replace(
            "stage2_bias_v2_center_",
            "stage2_bias_v2_center_near_policy_compatible_",
        )
        row["policy_labels"]["center_family_revision"] = (
            "screen_center_but_outside_acquisition_threshold"
        )
        row["bias_correction_design"] = {
            **row["bias_correction_design"],
            "schema_version": (
                "xonotic-stage2-bias-correction-design-v2-"
                "center-family-replenishment-v2"
            ),
            "center_family_revision": True,
            "screen_center_cell_preserved": True,
            "initial_acquisition_intentionally_false": True,
        }
        row["replenishment_contract"] = {
            "schema_version": (
                "xonotic-stage2-center-family-replenishment-contract-v1"
            ),
            "superseded_episode_id": source_episode_id,
            "superseded_counterfactual_group_id": SOURCE_GROUP_ID,
            "replacement_counterfactual_group_id": (
                REPLACEMENT_GROUP_ID
            ),
            "structural_failure_evidence_episode_id": (
                OBSERVED_INCOMPATIBLE_EPISODE
            ),
            "structural_failure_evidence_attempt_id": rejection[
                "attempt_id"
            ],
            "structural_failure_evidence_sha256": (
                rejection_sha256
            ),
            "revision_reason": (
                "exact_crosshair_initial_geometry_is_incompatible_"
                "with_delayed_acquisition"
            ),
            "changes": [
                "episode_and_group_identity",
                "candidate_metadata",
                "initial_screen_design.view_offsets",
                "player.initial_view",
                "shard_assignment",
            ],
            "screen_stratum_changed": False,
            "world_geometry_changed": False,
            "enemy_trajectory_changed": False,
            "outcome_observed_for_treatment_selection": False,
            "runtime_fallback": False,
        }
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        causal.causal_action_rows(row)
        new_initial_error, first_acquisition = (
            first_planned_acquisition(row)
        )
        acquisition_start = int(
            row["causal_design"]["acquisition_start_output_tick"]
        )
        is_delayed = (
            row["causal_design"]["aim_policy"]
            == "delayed_acquisition"
        )
        static_checks = {
            "source_was_initially_acquired": (
                original_initial_error
                <= causal.TARGET_CENTER_THRESHOLD_DEG
            ),
            "replacement_is_not_initially_acquired": (
                new_initial_error
                > causal.TARGET_CENTER_THRESHOLD_DEG + 0.5
            ),
            "replacement_remains_center_screen_design": (
                row["initial_screen_design"]["screen_horizontal"]
                == "center"
                and row["initial_screen_design"]["screen_vertical"]
                == "center"
            ),
            "delayed_first_acquisition_after_declared_delay": (
                not is_delayed
                or (
                    first_acquisition is not None
                    and first_acquisition >= acquisition_start
                )
            ),
            "outcome_unassigned": (
                row["acceptance"]["actual_outcome"] is None
            ),
            "nontraining": (
                row["formal_collection_authorized"] is False
                and row["training_admitted"] is False
            ),
        }
        if not all(static_checks.values()):
            raise capture.CaptureFailure(
                "stage2_center_family_static_audit",
                f"{row['episode_id']}: "
                f"{capture.canonical_json(static_checks)} "
                f"old={original_initial_error} "
                f"new={new_initial_error} first={first_acquisition}",
            )
        row["replenishment_contract"]["static_checks"] = (
            static_checks
        )
        row["replenishment_contract"][
            "source_initial_angular_error_deg"
        ] = original_initial_error
        row["replenishment_contract"][
            "replacement_initial_angular_error_deg"
        ] = new_initial_error
        row["replenishment_contract"][
            "planned_first_acquisition_output_tick"
        ] = first_acquisition
        rows.append(row)

    checks = {
        "rows_6": len(rows) == 6,
        "policies": Counter(
            row["causal_design"]["aim_policy"] for row in rows
        )
        == Counter(
            {
                "visible_no_response": 1,
                "delayed_acquisition": 2,
                "pass_offset": 1,
                "track_loss_reacquire": 1,
                "sustained_tracking": 1,
            }
        ),
        "single_exogenous_contract": len(
            {row["exogenous_contract_sha256"] for row in rows}
        )
        == 1,
        "screen_labels_preserved": all(
            row["initial_screen_design"]["screen_horizontal"]
            == "center"
            and row["initial_screen_design"]["screen_vertical"]
            == "center"
            and row["policy_labels"]["initial_screen_cell"]
            == "center"
            for row in rows
        ),
        "finite_center_offset": math.isclose(
            math.hypot(
                NEW_VIEW_YAW_OFFSET_DEG,
                NEW_VIEW_PITCH_OFFSET_DEG,
            ),
            math.sqrt(13.0),
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_center_family_group_audit",
            capture.canonical_json(checks),
        )
    return rows


def materialize() -> dict[str, Any]:
    rows = build_rows()
    text = base.canonical_lines(rows)
    shard = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    base.write_once_or_verify(OUTPUT_ROOT / "input.jsonl", text)
    base.write_once_or_verify(shard, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-center-family-replenishment-manifest-v1"
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
            "rows": len(rows),
            "counterfactual_families": 1,
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard),
                    "rows": len(rows),
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
            "xonotic-stage2-center-family-replenishment-audit-v1"
        ),
        "pass": True,
        "source_counterfactual_group_id": SOURCE_GROUP_ID,
        "replacement_counterfactual_group_id": (
            REPLACEMENT_GROUP_ID
        ),
        "rows": len(rows),
        "aim_policy": dict(
            Counter(
                row["causal_design"]["aim_policy"] for row in rows
            )
        ),
        "initial_screen_horizontal": {"center": len(rows)},
        "initial_screen_vertical": {"center": len(rows)},
        "view_yaw_offset_deg": NEW_VIEW_YAW_OFFSET_DEG,
        "view_pitch_offset_deg": NEW_VIEW_PITCH_OFFSET_DEG,
        "initial_angular_error_deg": math.hypot(
            NEW_VIEW_YAW_OFFSET_DEG,
            NEW_VIEW_PITCH_OFFSET_DEG,
        ),
        "single_exogenous_contract": len(
            {row["exogenous_contract_sha256"] for row in rows}
        )
        == 1,
        "exogenous_contract_sha256": rows[0][
            "exogenous_contract_sha256"
        ],
        "observed_structural_rejection": (
            observed_structural_rejection()
        ),
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
