                      
"""Assemble the fail-closed 100-row Stage-2 bias review cohort.

This does not create a new capture input.  It selects 99 accepted V2 rows
plus one separately declared and accepted replenishment row, verifies the
superseded hard rejection, and materializes a read-only review view.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_stage2_causal_bundle as bundle              
import build_stage2_causal_gallery as gallery              
import prepare_stage2_bias_correction_v1 as base              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
BASE_MANIFEST_ROOT = ROOT / "manifests/stage2_bias_correction_v2"
REPLENISHMENT_MANIFEST_ROOT = (
    ROOT / "manifests/stage2_bias_correction_v2_replenishment_v1"
)
CENTER_REPLENISHMENT_MANIFEST_ROOT = (
    ROOT / "manifests/stage2_bias_correction_v2_replenishment_v2"
)
BASE_OUTPUT_ROOT = ROOT / "stage2_bias_correction_v2_output"
REPLENISHMENT_OUTPUT_ROOT = (
    ROOT / "stage2_bias_correction_v2_replenishment_v1_output"
)
CENTER_REPLENISHMENT_OUTPUT_ROOT = (
    ROOT / "stage2_bias_correction_v2_replenishment_v2_output"
)
SELECTION_ROOT = (
    ROOT / "manifests/stage2_bias_correction_v3_selected"
)
SELECTED_OUTPUT_ROOT = (
    ROOT / "stage2_bias_correction_v3_selected_output"
)
SUPERSEDED_EPISODE_ID = (
    "s2biasv2_g01_p04_track_loss_reacquire_a01"
)
REPLACEMENT_EPISODE_ID = (
    "s2biasv2r1_g01_p04_track_loss_reacquire_a02"
)
SOURCE_CENTER_GROUP_ID = "s2biasv2_g15"
REPLACEMENT_CENTER_GROUP_ID = "s2biasv2r2_g15"


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(
        f"{capture.canonical_json(row)}\n" for row in rows
    )


def unique_by_episode(
    rows: list[dict[str, Any]], label: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        episode_id = str(row.get("episode_id", ""))
        if not episode_id or episode_id in result:
            raise capture.CaptureFailure(
                "stage2_selected_duplicate_episode",
                f"source={label} episode={episode_id}",
            )
        result[episode_id] = row
    return result


def selected_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    original = capture.load_jsonl(
        BASE_MANIFEST_ROOT / "input.jsonl"
    )
    first_replacement_rows = capture.load_jsonl(
        REPLENISHMENT_MANIFEST_ROOT / "input.jsonl"
    )
    center_replacement_rows = capture.load_jsonl(
        CENTER_REPLENISHMENT_MANIFEST_ROOT / "input.jsonl"
    )
    if (
        len(original) != 100
        or len(first_replacement_rows) != 1
        or len(center_replacement_rows) != 6
    ):
        raise capture.CaptureFailure(
            "stage2_selected_source_cardinality",
            f"base={len(original)} "
            f"replenishment_v1={len(first_replacement_rows)} "
            f"replenishment_v2={len(center_replacement_rows)}",
        )
    replacement = first_replacement_rows[0]
    if replacement["episode_id"] != REPLACEMENT_EPISODE_ID:
        raise capture.CaptureFailure(
            "stage2_selected_wrong_replacement",
            str(replacement.get("episode_id")),
        )
    replacements = {
        row["replenishment_contract"]["superseded_episode_id"]: row
        for row in first_replacement_rows + center_replacement_rows
    }
    expected_superseded = {
        SUPERSEDED_EPISODE_ID,
        *{
            row["episode_id"]
            for row in original
            if row["counterfactual_group_id"]
            == SOURCE_CENTER_GROUP_ID
        },
    }
    if set(replacements) != expected_superseded:
        raise capture.CaptureFailure(
            "stage2_selected_replacement_mapping",
            capture.canonical_json(
                {
                    "expected": sorted(expected_superseded),
                    "actual": sorted(replacements),
                }
            ),
        )
    rows = [
        replacements.get(row["episode_id"], row)
        for row in original
    ]
    selected_ids = {row["episode_id"] for row in rows}
    if (
        len(rows) != 100
        or len(selected_ids) != 100
        or selected_ids & expected_superseded
        or REPLACEMENT_EPISODE_ID
        not in selected_ids
        or sum(
            row["counterfactual_group_id"]
            == REPLACEMENT_CENTER_GROUP_ID
            for row in rows
        )
        != 6
    ):
        raise capture.CaptureFailure(
            "stage2_selected_replacement_failed", "row identity"
        )
    for row in rows:
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        causal.causal_action_rows(row)
    source_audit = json.loads(
        (BASE_MANIFEST_ROOT / "DESIGN_AUDIT.json").read_text(
            encoding="utf-8"
        )
    )
    miss = [
        row
        for row in rows
        if row["causal_design"]["shot_error_schedule"]["program"]
        != "none"
    ]
    distribution = {
        "aim_policy": dict(
            Counter(
                row["causal_design"]["aim_policy"] for row in rows
            )
        ),
        "initial_screen_horizontal": dict(
            Counter(
                row["initial_screen_design"]["screen_horizontal"]
                for row in rows
            )
        ),
        "initial_screen_vertical": dict(
            Counter(
                row["initial_screen_design"]["screen_vertical"]
                for row in rows
            )
        ),
        "initial_screen_cells": dict(
            Counter(
                row["policy_labels"]["initial_screen_cell"]
                for row in rows
            )
        ),
        "miss_policy": dict(
            Counter(
                row["causal_design"]["aim_policy"] for row in miss
            )
        ),
        "miss_program": dict(
            Counter(
                row["causal_design"]["shot_error_schedule"][
                    "program"
                ]
                for row in miss
            )
        ),
        "miss_initial_screen_horizontal": dict(
            Counter(
                row["initial_screen_design"]["screen_horizontal"]
                for row in miss
            )
        ),
        "miss_initial_screen_vertical": dict(
            Counter(
                row["initial_screen_design"]["screen_vertical"]
                for row in miss
            )
        ),
    }
    distribution_checks = {
        name: observed == source_audit[name]
        for name, observed in distribution.items()
    }
    checks = {
        "rows_100_unique": len(rows) == 100,
        "superseded_absent": all(
            row["episode_id"] != SUPERSEDED_EPISODE_ID
            for row in rows
        ),
        "replacement_present_once": sum(
            row["episode_id"] == REPLACEMENT_EPISODE_ID
            for row in rows
        )
        == 1,
        "center_family_replaced_together": (
            sum(
                row["counterfactual_group_id"]
                == REPLACEMENT_CENTER_GROUP_ID
                for row in rows
            )
            == 6
            and all(
                row["counterfactual_group_id"]
                != SOURCE_CENTER_GROUP_ID
                for row in rows
            )
        ),
        "distribution_identical_to_preregistered_v2": all(
            distribution_checks.values()
        ),
        "telemetry_outcome_unassigned_at_design_time": all(
            row["acceptance"]["actual_outcome"] is None for row in rows
        ),
        "nontraining": all(
            row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
            for row in rows
        ),
        "replacements_are_not_runtime_fallbacks": all(
            row["replenishment_contract"]["runtime_fallback"]
            is False
            for row in replacements.values()
        ),
        "replacements_not_selected_by_outcome": all(
            row["replenishment_contract"][
                "outcome_observed_for_treatment_selection"
            ]
            is False
            for row in replacements.values()
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_selected_static_audit_failed",
            capture.canonical_json(checks),
        )
    return rows, {
        "distribution": distribution,
        "distribution_checks": distribution_checks,
        "checks": checks,
    }


def hard_rejection_evidence(
    replacements: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = bundle.terminal_rows(BASE_OUTPUT_ROOT)
    by_id = {
        row["episode_id"]: row
        for row in rows
    }
    expected_ids = {
        SUPERSEDED_EPISODE_ID,
        "s2biasv2_g15_p02_delayed_acquisition_a01",
        "s2biasv2_g15_p02_delayed_acquisition_a02",
    }
    if set(by_id) != expected_ids:
        raise capture.CaptureFailure(
            "stage2_selected_terminal_set",
            capture.canonical_json(
                {
                    "expected": sorted(expected_ids),
                    "actual": sorted(by_id),
                }
            ),
        )
    first_contract = next(
        row["replenishment_contract"]
        for row in replacements
        if row["episode_id"] == REPLACEMENT_EPISODE_ID
    )
    first_rejection = by_id[SUPERSEDED_EPISODE_ID]
    first_digest = hashlib.sha256(
        capture.canonical_json(first_rejection).encode("utf-8")
    ).hexdigest()
    center_contract = next(
        row["replenishment_contract"]
        for row in replacements
        if row["counterfactual_group_id"]
        == REPLACEMENT_CENTER_GROUP_ID
    )
    center_evidence_id = center_contract[
        "structural_failure_evidence_episode_id"
    ]
    center_rejection = by_id[center_evidence_id]
    center_digest = hashlib.sha256(
        capture.canonical_json(center_rejection).encode("utf-8")
    ).hexdigest()
    structural = [
        row
        for episode_id, row in by_id.items()
        if episode_id.startswith(f"{SOURCE_CENTER_GROUP_ID}_p02_")
    ]
    structural_payloads = [
        json.loads(str(row["detail"]).split(": ", 1)[1])
        for row in structural
    ]
    checks = {
        "terminal_set_exact": set(by_id) == expected_ids,
        "first_attempt_exact": first_rejection["attempt_id"]
        == first_contract["superseded_attempt_id"],
        "first_reason_exact": first_rejection["reason"]
        == first_contract["terminal_reason"],
        "first_hash_exact": first_digest
        == first_contract["terminal_rejection_sha256"],
        "center_evidence_attempt_exact": center_rejection[
            "attempt_id"
        ]
        == center_contract["structural_failure_evidence_attempt_id"],
        "center_evidence_hash_exact": center_digest
        == center_contract["structural_failure_evidence_sha256"],
        "both_center_delayed_fail_structurally": (
            len(structural) == 2
            and all(
                row["reason"] == "stage2_causal_qa_failed"
                for row in structural
            )
            and all(
                payload["failed"]
                == ["stage2_causal_policy_realized"]
                and payload["policy_checks"][
                    "acquired_after_delay"
                ]
                is False
                and payload["policy_checks"][
                    "visible_during_delay"
                ]
                is True
                for payload in structural_payloads
            )
        ),
        "all_hard_nonretryable": all(
            row.get("terminal") is True
            and row.get("retryable") is not True
            for row in rows
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_selected_terminal_evidence_failed",
            capture.canonical_json(checks),
        )
    return {
        "records": rows,
        "sha256_by_episode": {
            row["episode_id"]: hashlib.sha256(
                capture.canonical_json(row).encode("utf-8")
            ).hexdigest()
            for row in rows
        },
        "checks": checks,
    }


def verify_accepted_record(
    scenario: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, bool]:
    episode = Path(record["episode_path"])
    qa = json.loads(
        (episode / "qa.json").read_text(encoding="utf-8")
    )
    causal_qa = json.loads(
        (episode / "causal_interaction.json").read_text(
            encoding="utf-8"
        )
    )
    package_hashes = record.get("package_sha256") or {}
    checks = {
        "episode_id": record["episode_id"]
        == scenario["episode_id"]
        == causal_qa["episode_id"],
        "episode_directory": episode.is_dir(),
        "package_hashes": bool(package_hashes)
        and all(
            (episode / name).is_file()
            and capture.sha256_file(episode / name) == digest
            for name, digest in package_hashes.items()
        ),
        "all_media_and_runtime_gates": all(
            bundle.media_checks(episode, qa).values()
        ),
        "all_hard_gates": all(qa["hard_gates"].values()),
        "causal_passed": causal_qa["passed"] is True,
        "policy_exact": causal_qa["aim_policy"]
        == scenario["causal_design"]["aim_policy"],
        "exogenous_hash_exact": causal_qa[
            "exogenous_contract_sha256"
        ]
        == scenario["exogenous_contract_sha256"],
        "nontraining": (
            record["formal_collection_authorized"] is False
            and record["training_admitted"] is False
        ),
    }
    return checks


def accepted_selection(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base_records = unique_by_episode(
        bundle.accepted_rows(BASE_OUTPUT_ROOT), "base"
    )
    replacement_records = unique_by_episode(
        bundle.accepted_rows(REPLENISHMENT_OUTPUT_ROOT),
        "replenishment",
    )
    center_replacement_records = unique_by_episode(
        bundle.accepted_rows(CENTER_REPLENISHMENT_OUTPUT_ROOT),
        "center_replenishment",
    )
    selected_records: list[dict[str, Any]] = []
    episode_checks: dict[str, dict[str, bool]] = {}
    for row in rows:
        episode_id = row["episode_id"]
        source = (
            replacement_records
            if episode_id == REPLACEMENT_EPISODE_ID
            else (
                center_replacement_records
                if row["counterfactual_group_id"]
                == REPLACEMENT_CENTER_GROUP_ID
                else base_records
            )
        )
        record = source.get(episode_id)
        if record is None:
            raise capture.CaptureFailure(
                "stage2_selected_missing_acceptance", episode_id
            )
        checks = verify_accepted_record(row, record)
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "stage2_selected_accepted_artifact_failed",
                f"{episode_id}: {capture.canonical_json(checks)}",
            )
        selected_records.append(record)
        episode_checks[episode_id] = checks
    checks = {
        "selected_acceptances_100": len(selected_records) == 100,
        "all_selected_unique": len(
            {row["episode_id"] for row in selected_records}
        )
        == 100,
        "base_acceptances_exactly_97": len(base_records) == 97,
        "replacement_acceptance_exactly_1": (
            set(replacement_records) == {REPLACEMENT_EPISODE_ID}
        ),
        "center_replacement_acceptances_exactly_6": (
            len(center_replacement_records) == 6
            and set(center_replacement_records)
            == {
                row["episode_id"]
                for row in rows
                if row["counterfactual_group_id"]
                == REPLACEMENT_CENTER_GROUP_ID
            }
        ),
        "superseded_never_accepted": (
            SUPERSEDED_EPISODE_ID not in base_records
        ),
        "excluded_old_center_acceptances_exactly_4": (
            len(
                {
                    episode_id
                    for episode_id in base_records
                    if episode_id.startswith(
                        f"{SOURCE_CENTER_GROUP_ID}_"
                    )
                }
            )
            == 4
        ),
        "all_artifact_checks": all(
            all(values.values()) for values in episode_checks.values()
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_selected_acceptance_audit_failed",
            capture.canonical_json(checks),
        )
    return selected_records, {
        "checks": checks,
        "episodes": episode_checks,
    }


def verify_or_create_episode_link(
    episode_id: str, target: Path
) -> None:
    link = SELECTED_OUTPUT_ROOT / "episodes" / episode_id
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        if link.resolve() != target.resolve():
            raise capture.CaptureFailure(
                "stage2_selected_link_mismatch", str(link)
            )
        return
    if link.exists():
        raise capture.CaptureFailure(
            "stage2_selected_link_collision", str(link)
        )
    temporary = link.with_name(f".{link.name}.tmp.{os.getpid()}")
    temporary.symlink_to(target.resolve(), target_is_directory=True)
    os.replace(temporary, link)


def materialize() -> dict[str, Any]:
    rows, static = selected_rows()
    replacements = [
        row for row in rows if "replenishment_contract" in row
    ]
    rejection = hard_rejection_evidence(replacements)
    records, accepted = accepted_selection(rows)

    selection_text = canonical_lines(rows)
    selection_path = SELECTION_ROOT / "SELECTION_MANIFEST.jsonl"
    base.write_once_or_verify(selection_path, selection_text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-bias-selected-cohort-metadata-v1"
        ),
        "selection_is_capture_input": False,
        "runnable_source_manifests": [
            str(BASE_MANIFEST_ROOT / "input.jsonl"),
            str(REPLENISHMENT_MANIFEST_ROOT / "input.jsonl"),
            str(
                CENTER_REPLENISHMENT_MANIFEST_ROOT
                / "input.jsonl"
            ),
        ],
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(base.DATA_SPEC),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "rows": len(rows),
        "selection_manifest_sha256": hashlib.sha256(
            selection_text.encode("utf-8")
        ).hexdigest(),
        "superseded_episode_id": SUPERSEDED_EPISODE_ID,
        "replacement_episode_id": REPLACEMENT_EPISODE_ID,
        "source_center_group_id": SOURCE_CENTER_GROUP_ID,
        "replacement_center_group_id": (
            REPLACEMENT_CENTER_GROUP_ID
        ),
        "actual_outcome_source": "authoritative_telemetry_only",
        "runtime_fallback": False,
    }
    base.write_once_or_verify(
        SELECTION_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )

    journal = (
        SELECTED_OUTPUT_ROOT
        / "manifests/shards/shard-000-of-001/accepted.jsonl"
    )
    base.write_once_or_verify(journal, canonical_lines(records))
    for record in records:
        verify_or_create_episode_link(
            record["episode_id"], Path(record["episode_path"])
        )

    result = {
        "schema_version": (
            "xonotic-stage2-bias-selected-cohort-audit-v1"
        ),
        "pass": True,
        "selection_manifest": str(selection_path),
        "selection_manifest_sha256": capture.sha256_file(
            selection_path
        ),
        "base_manifest_sha256": capture.sha256_file(
            BASE_MANIFEST_ROOT / "input.jsonl"
        ),
        "replenishment_manifest_sha256": capture.sha256_file(
            REPLENISHMENT_MANIFEST_ROOT / "input.jsonl"
        ),
        "center_replenishment_manifest_sha256": (
            capture.sha256_file(
                CENTER_REPLENISHMENT_MANIFEST_ROOT / "input.jsonl"
            )
        ),
        "static": static,
        "terminal_rejection": rejection,
        "accepted": accepted,
    }
    base.write_once_or_verify(
        SELECTION_ROOT / "SELECTION_AUDIT.json",
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    base.write_once_or_verify(
        SELECTED_OUTPUT_ROOT
        / "manifests/shards/shard-000-of-001/RUN_RESULT.json",
        json.dumps(
            {
                "schema_version": (
                    "xonotic-stage2-derived-selection-result-v1"
                ),
                "pass": True,
                "planned_rows": 100,
                "accepted": 100,
                "terminal_rejects": 0,
                "selection_manifest": str(selection_path),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    bundle_result = bundle.audit(
        selection_path, SELECTED_OUTPUT_ROOT
    )
    if bundle_result["pass"] is not True:
        raise capture.CaptureFailure(
            "stage2_selected_bundle_audit_failed",
            capture.canonical_json(
                {
                    "accepted": bundle_result["accepted_rows"],
                    "terminal": bundle_result[
                        "terminal_reject_rows"
                    ],
                    "complete_groups": bundle_result[
                        "complete_groups"
                    ],
                }
            ),
        )
    bundle.atomic_json(
        SELECTED_OUTPUT_ROOT
        / "review/STAGE2_CAUSAL_BUNDLE_AUDIT.json",
        bundle_result,
    )
    (SELECTED_OUTPUT_ROOT / "review").mkdir(
        parents=True, exist_ok=True
    )
    (SELECTED_OUTPUT_ROOT / "review/STAGE2_CAUSAL_BUNDLE_AUDIT.md").write_text(
        bundle.markdown(bundle_result), encoding="utf-8"
    )
    gallery_path = gallery.build(SELECTED_OUTPUT_ROOT)
    result["bundle_audit_pass"] = True
    result["gallery"] = str(gallery_path)
    return result


def main() -> int:
    print(json.dumps(materialize(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
