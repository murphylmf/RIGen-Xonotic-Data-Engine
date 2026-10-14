                      
"""Bind the Stage-2 bias design to the final fixed-step H200 runtime."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import prepare_stage2_bias_correction_v1 as base
import xonotic_capture as capture
import xonotic_stage2_causal as causal


ROOT = base.ROOT
OUTPUT_ROOT = ROOT / "manifests/stage2_bias_correction_v2"
SOURCE_RUNTIME_COMMIT = "b40e26fd4e33b18b2002bf24beb6a78cef5fac96"
RUNTIME_SOURCE_COMMIT = "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
COMPATIBILITY_AUDIT = (
    ROOT
    / "stage1_path_certification_v5/compatibility/"
    "b40e26fd4e33_to_7e8310b0d0c1/AUDIT.json"
)

                                                  
                                                                         
                                                                         
MISS_ASSIGNMENTS = {
    "delayed_acquisition": (
        (0, False, "spatial_undershoot_then_acquire"),
        (1, False, "spatial_undershoot_then_acquire"),
        (2, False, "timing_early_acquisition"),
        (3, False, "spatial_transient"),
        (14, False, "spatial_transient"),
        (0, True, "timing_early_acquisition"),
    ),
    "pass_offset": (
        (4, False, "spatial_persistent"),
        (5, False, "spatial_persistent"),
        (6, False, "timing_early_acquisition"),
        (7, False, "timing_early_acquisition"),
        (10, False, "pass_cross_and_depart"),
        (9, False, "pass_cross_and_depart"),
        (11, False, "pass_cross_and_depart"),
    ),
    "track_loss_reacquire": (
        (0, False, "timing_loss_window"),
        (1, False, "timing_loss_window"),
        (2, False, "timing_loss_window"),
        (3, False, "timing_loss_window"),
        (6, False, "timing_reacquisition_lag"),
        (10, False, "timing_reacquisition_lag"),
        (9, False, "timing_reacquisition_lag"),
    ),
    "sustained_tracking": (
        (0, False, "spatial_transient"),
        (1, False, "spatial_transient"),
        (6, False, "spatial_transient"),
        (3, False, "spatial_transient"),
        (5, False, "spatial_transient"),
    ),
}

EXPECTED_MISS_PROGRAMS = {
    "pass_cross_and_depart",
    "spatial_persistent",
    "spatial_transient",
    "spatial_undershoot_then_acquire",
    "timing_early_acquisition",
    "timing_loss_window",
    "timing_reacquisition_lag",
}


def build_rows() -> list[dict[str, Any]]:
    rows = base.build_rows(miss_assignments=MISS_ASSIGNMENTS)
    compatibility_sha = capture.sha256_file(COMPATIBILITY_AUDIT)
    for row in rows:
        for field in ("episode_id", "counterfactual_group_id", "anchor_id"):
            row[field] = str(row[field]).replace(
                "s2biasv1", "s2biasv2"
            )
        row["source_commit_required"] = RUNTIME_SOURCE_COMMIT
        row["candidate_kind"] = (
            "stage2_screen_miss_bias_correction_v2"
        )
        row["training_stage"] = (
            "stage2_bounded_bias_correction_v2_only"
        )
        row["canary_role"] = str(row["canary_role"]).replace(
            "stage2_bias_v1", "stage2_bias_v2"
        )
        row["runtime_transition_contract"] = {
            "schema_version": (
                "xonotic-stage2-runtime-transition-contract-v1"
            ),
            "source_runtime_commit": SOURCE_RUNTIME_COMMIT,
            "target_runtime_commit": RUNTIME_SOURCE_COMMIT,
            "engine_diff_evidence_path": str(
                COMPATIBILITY_AUDIT.relative_to(ROOT)
            ),
            "engine_diff_evidence_sha256": compatibility_sha,
            "engine_diff_scope": (
                "offline_demo_fixedstep_presentation_and_telemetry_only"
            ),
            "server_physics_changed": False,
            "collision_changed": False,
            "gamecode_changed": False,
            "stage1_certificate_authority_inherited": False,
            "stage2_live_render_recertification_required": True,
            "runtime_fallback": False,
        }
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        causal.causal_action_rows(row)
    return rows


def materialize() -> dict[str, Any]:
    rows = build_rows()
    audit = base.audit_rows(rows)
    miss_rows = [
        row
        for row in rows
        if row["causal_design"]["shot_error_schedule"]["program"]
        != "none"
    ]
    miss_programs = {
        row["causal_design"]["shot_error_schedule"]["program"]
        for row in miss_rows
    }
    miss_horizontal = {
        value: sum(
            row["initial_screen_design"]["screen_horizontal"] == value
            for row in miss_rows
        )
        for value in ("left", "right", "center")
    }
    miss_vertical = {
        value: sum(
            row["initial_screen_design"]["screen_vertical"] == value
            for row in miss_rows
        )
        for value in ("upper", "lower", "center")
    }
    miss_policy_sides = {
        policy: {
            side: sum(
                row["causal_design"]["aim_policy"] == policy
                and row["initial_screen_design"][
                    "screen_horizontal"
                ]
                == side
                for row in miss_rows
            )
            for side in ("left", "right")
        }
        for policy in base.MISS_POLICY_TARGETS
    }
    audit["miss_program"] = dict(
        sorted(
            {
                program: sum(
                    row["causal_design"]["shot_error_schedule"][
                        "program"
                    ]
                    == program
                    for row in miss_rows
                )
                for program in miss_programs
            }.items()
        )
    )
    audit["miss_initial_screen_horizontal"] = miss_horizontal
    audit["miss_initial_screen_vertical"] = miss_vertical
    audit["miss_policy_horizontal"] = miss_policy_sides
    audit["checks"]["miss_program_diversity"] = (
        miss_programs == EXPECTED_MISS_PROGRAMS
    )
    audit["checks"].update(
        {
            "miss_initial_left_right_stratified": (
                miss_horizontal
                == {"left": 12, "right": 12, "center": 1}
            ),
            "miss_initial_upper_lower_stratified": (
                miss_vertical
                == {"upper": 12, "lower": 12, "center": 1}
            ),
            "every_miss_policy_has_both_sides": all(
                counts["left"] >= 2 and counts["right"] >= 2
                for counts in miss_policy_sides.values()
            ),
            "no_single_miss_program_dominates": max(
                audit["miss_program"].values()
            )
            <= 7,
            "undershoot_is_not_center_then_depart": all(
                row["causal_design"]["shot_error_schedule"][
                    "expected_center_before_first_fire"
                ]
                is False
                and row["causal_design"]["shot_error_schedule"][
                    "expected_acquisition_after_first_fire"
                ]
                is True
                for row in miss_rows
                if row["causal_design"]["shot_error_schedule"][
                    "program"
                ]
                == "spatial_undershoot_then_acquire"
            ),
        }
    )
    audit.update(
        {
            "schema_version": (
                "xonotic-stage2-bias-correction-audit-v2"
            ),
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
            "source_runtime_commit": SOURCE_RUNTIME_COMMIT,
            "runtime_transition_evidence": {
                "path": str(COMPATIBILITY_AUDIT.relative_to(ROOT)),
                "sha256": capture.sha256_file(COMPATIBILITY_AUDIT),
            },
        }
    )
    audit["checks"].update(
        {
            "runtime_commit_exact": all(
                row["source_commit_required"]
                == RUNTIME_SOURCE_COMMIT
                for row in rows
            ),
            "runtime_transition_explicit": all(
                row["runtime_transition_contract"][
                    "stage2_live_render_recertification_required"
                ]
                is True
                and row["runtime_transition_contract"][
                    "stage1_certificate_authority_inherited"
                ]
                is False
                and row["runtime_transition_contract"][
                    "runtime_fallback"
                ]
                is False
                for row in rows
            ),
        }
    )
    audit["pass"] = all(audit["checks"].values())
    if audit["pass"] is not True:
        raise capture.CaptureFailure(
            "stage2_bias_v2_design_audit_failed",
            capture.canonical_json(audit["checks"]),
        )

    text = base.canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    base.write_once_or_verify(input_path, text)
    shard_rows = [
        [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard
        ]
        for shard in range(base.SHARD_COUNT)
    ]
    shard_paths = [
        OUTPUT_ROOT
        / "shards"
        / f"shard-{shard:03d}-of-{base.SHARD_COUNT:03d}.jsonl"
        for shard in range(base.SHARD_COUNT)
    ]
    for path, items in zip(shard_paths, shard_rows):
        base.write_once_or_verify(path, base.canonical_lines(items))
    metadata = {
        "schema_version": (
            "xonotic-stage2-bias-correction-manifest-v2"
        ),
        "source_manifest": str(base.SOURCE.relative_to(ROOT)),
        "source_manifest_sha256": capture.sha256_file(base.SOURCE),
        "source_runtime_commit": SOURCE_RUNTIME_COMMIT,
        "source_commit": RUNTIME_SOURCE_COMMIT,
        "runtime_transition_evidence_path": str(
            COMPATIBILITY_AUDIT.relative_to(ROOT)
        ),
        "runtime_transition_evidence_sha256": capture.sha256_file(
            COMPATIBILITY_AUDIT
        ),
        "data_spec_sha256": capture.sha256_file(base.DATA_SPEC),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "actual_outcome_source": "authoritative_telemetry_only",
        "review": {
            "rows": len(rows),
            "counterfactual_families": base.GROUP_COUNT,
            "shard_count": base.SHARD_COUNT,
            "shards": [
                {
                    "shard_index": index,
                    "path": str(path),
                    "rows": len(items),
                    "sha256": hashlib.sha256(
                        base.canonical_lines(items).encode("utf-8")
                    ).hexdigest(),
                }
                for index, (path, items) in enumerate(
                    zip(shard_paths, shard_rows)
                )
            ],
        },
    }
    base.write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
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
