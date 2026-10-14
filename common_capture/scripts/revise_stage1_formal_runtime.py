                      
"""Create an immutable Stage-1 formal runtime revision without changing rows."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


GENERATED_FILES = frozenset(
    {
        "MANIFEST_METADATA.json",
        "MANIFEST_AUDIT.json",
        "RUNTIME_CODE_LOCK.sha256",
        "RUNTIME_REVISION_AUDIT.json",
    }
)
ADDITIONAL_RUNTIME_PATHS = (
    "STAGE1_AUDIO_EXPECTATION_AND_GANG_RECOVERY_POLICY.md",
    "scripts/audit_stage1_audio_expectation_revision.py",
    "scripts/revise_stage1_formal_runtime.py",
    "scripts/submit_stage1_sensecore_56x1.sh",
    "scripts/print_stage1_56x1_commands.sh",
    "STAGE1_RESIDENT_CLEANUP_GANG_FIX_REPORT.md",
    "STAGE1_MENU_OVERLAY_FIX_REPORT.md",
    "STAGE1_JSONL_CONCURRENCY_FIX_REPORT.md",
    "tests/test_stage1_jsonl_concurrency.py",
    "STAGE1_WARMUP_RESUME_NAMESPACE_FIX_REPORT.md",
    "scripts/stage1_distributed_barrier.py",
    "tests/test_stage1_distributed_barrier.py",
    "tests/test_stage1_reusable.py",
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def relative_to_workspace(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(capture.ROOT.resolve()))
    except ValueError as exc:
        raise capture.CaptureFailure(
            "runtime_revision_path_outside_workspace", str(path)
        ) from exc


def load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise capture.CaptureFailure(
            "runtime_revision_artifact_missing", str(path)
        )
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise capture.CaptureFailure(
            "runtime_revision_json_not_object", str(path)
        )
    return value


def runtime_paths(lock_path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    paths: list[str] = []
    mismatches: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        lock_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split()
        if (
            len(parts) != 2
            or len(parts[0]) != 64
            or any(char not in "0123456789abcdef" for char in parts[0])
        ):
            raise capture.CaptureFailure(
                "runtime_revision_source_lock_invalid",
                f"{lock_path}:{line_number}",
            )
        expected, relative = parts
        relative_path = Path(relative)
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative in paths
        ):
            raise capture.CaptureFailure(
                "runtime_revision_source_lock_path_invalid", relative
            )
        artifact = capture.ROOT / relative_path
        actual = (
            capture.sha256_file(artifact)
            if artifact.is_file()
            else None
        )
        if actual != expected:
            mismatches.append(
                {
                    "path": relative,
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                }
            )
        paths.append(relative)
    if not paths:
        raise capture.CaptureFailure(
            "runtime_revision_source_lock_empty", str(lock_path)
        )
    return paths, mismatches


def runtime_lock_text(paths: list[str]) -> str:
    ordered = list(paths)
    for relative in ADDITIONAL_RUNTIME_PATHS:
        if relative not in ordered:
            ordered.append(relative)
    rows = []
    for relative in ordered:
        artifact = capture.ROOT / relative
        if not artifact.is_file():
            raise capture.CaptureFailure(
                "runtime_revision_code_artifact_missing", relative
            )
        rows.append(f"{capture.sha256_file(artifact)}  {relative}\n")
    return "".join(rows)


def verify_source(
    source_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[dict[str, Any]]]:
    metadata_path = source_root / "MANIFEST_METADATA.json"
    audit_path = source_root / "MANIFEST_AUDIT.json"
    lock_path = source_root / "RUNTIME_CODE_LOCK.sha256"
    metadata = load_object(metadata_path)
    audit = load_object(audit_path)
    checks = {
        "metadata_schema": metadata.get("schema_version")
        == "xonotic-stage1-formal-manifest-v2",
        "formal_authorized": metadata.get(
            "formal_collection_authorized"
        )
        is True,
        "not_training_admitted": metadata.get("training_admitted")
        is False,
        "shard_count_56": int(metadata.get("shard_count", -1)) == 56,
        "audit_passed": audit.get("passed") is True,
        "metadata_sha256": audit.get("metadata_sha256")
        == capture.sha256_file(metadata_path),
        "primary_sha256": audit.get("primary_sha256")
        == (metadata.get("primary") or {}).get("sha256"),
        "replenishment_sha256": audit.get("replenishment_sha256")
        == (metadata.get("replenishment") or {}).get("sha256"),
        "runtime_lock_sha256": (
            (metadata.get("runtime_code_lock") or {}).get("sha256")
            == audit.get("runtime_code_lock_sha256")
            == capture.sha256_file(lock_path)
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "runtime_revision_source_audit_failed",
            capture.canonical_json(checks),
        )

    for wave, filename, expected_rows in (
        ("primary", "input.jsonl", 60_000),
        ("replenishment", "replenishment.jsonl", 12_000),
    ):
        declared = metadata[wave]
        full_path = source_root / filename
        if (
            int(declared.get("rows", -1)) != expected_rows
            or capture.sha256_file(full_path) != declared.get("sha256")
            or len(declared.get("shards") or []) != 56
        ):
            raise capture.CaptureFailure(
                "runtime_revision_source_wave_failed", wave
            )
        for shard in declared["shards"]:
            shard_path = source_root / "shards" / wave / Path(
                str(shard["path"])
            ).name
            if (
                not shard_path.is_file()
                or capture.sha256_file(shard_path)
                != shard.get("sha256")
            ):
                raise capture.CaptureFailure(
                    "runtime_revision_source_shard_failed",
                    str(shard_path),
                )
    paths, mismatches = runtime_paths(lock_path)
    return metadata, audit, paths, mismatches


def link_immutable_tree(source_root: Path, stage_root: Path) -> None:
    for source in sorted(source_root.rglob("*")):
        relative = source.relative_to(source_root)
        destination = stage_root / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if not source.is_file() or str(relative) in GENERATED_FILES:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(source, destination)
        except OSError as exc:
            raise capture.CaptureFailure(
                "runtime_revision_hardlink_failed",
                f"source={source} destination={destination} error={exc}",
            ) from exc


def rewrite_wave_paths(
    metadata: dict[str, Any],
    target_root: Path,
    wave: str,
    filename: str,
) -> None:
    declared = metadata[wave]
    declared["path"] = relative_to_workspace(target_root / filename)
    for shard in declared["shards"]:
        basename = Path(str(shard["path"])).name
        shard["path"] = relative_to_workspace(
            target_root / "shards" / wave / basename
        )


def verify_existing(target_root: Path) -> dict[str, Any]:
    audit_path = target_root / "RUNTIME_REVISION_AUDIT.json"
    revision = load_object(audit_path)
    metadata = load_object(target_root / "MANIFEST_METADATA.json")
    formal_audit = load_object(target_root / "MANIFEST_AUDIT.json")
    lock_path = target_root / "RUNTIME_CODE_LOCK.sha256"
    checks = {
        "revision_passed": revision.get("passed") is True,
        "metadata_sha256": formal_audit.get("metadata_sha256")
        == capture.sha256_file(target_root / "MANIFEST_METADATA.json"),
        "revision_sha256": formal_audit.get(
            "runtime_revision_sha256"
        )
        == capture.sha256_file(audit_path),
        "runtime_lock_sha256": (
            formal_audit.get("runtime_code_lock_sha256")
            == (metadata.get("runtime_code_lock") or {}).get("sha256")
            == capture.sha256_file(lock_path)
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "runtime_revision_existing_failed",
            capture.canonical_json(checks),
        )
    _, mismatches = runtime_paths(lock_path)
    if mismatches:
        raise capture.CaptureFailure(
            "runtime_revision_existing_code_drift",
            capture.canonical_json(mismatches),
        )
    return {
        "pass": True,
        "existing": True,
        "target_root": str(target_root),
        "runtime_revision_sha256": capture.sha256_file(audit_path),
        "runtime_code_lock_sha256": capture.sha256_file(lock_path),
    }


def create_revision(source_root: Path, target_root: Path) -> dict[str, Any]:
    if source_root.resolve() == target_root.resolve():
        raise capture.CaptureFailure(
            "runtime_revision_target_equals_source", str(target_root)
        )
    if target_root.exists():
        return verify_existing(target_root)

    metadata, source_audit, paths, old_mismatches = verify_source(
        source_root
    )
    stage_root = target_root.with_name(
        f".{target_root.name}.tmp.{os.getpid()}"
    )
    if stage_root.exists():
        raise capture.CaptureFailure(
            "runtime_revision_stage_exists", str(stage_root)
        )
    stage_root.mkdir(parents=True)
    link_immutable_tree(source_root, stage_root)

    lock_text = runtime_lock_text(paths)
    lock_sha256 = capture.hashlib.sha256(lock_text.encode()).hexdigest()
    atomic_text(stage_root / "RUNTIME_CODE_LOCK.sha256", lock_text)
    created_utc = capture.utc_now()
    policy_path = (
        capture.ROOT
        / "STAGE1_AUDIO_EXPECTATION_AND_GANG_RECOVERY_POLICY.md"
    )
    menu_fix_report_path = (
        capture.ROOT / "STAGE1_MENU_OVERLAY_FIX_REPORT.md"
    )
    journal_fix_report_path = (
        capture.ROOT / "STAGE1_JSONL_CONCURRENCY_FIX_REPORT.md"
    )
    journal_validation_root = (
        capture.ROOT / "logs/stage1_jsonl_lock_fix_20260729"
    )
    journal_stress_path = (
        journal_validation_root / "quarkfs_12lane_stress.log"
    )
    journal_status_path = (
        journal_validation_root / "current_56_status.json"
    )
    journal_status = load_object(journal_status_path)
    journal_common_source = (
        capture.ROOT / "scripts/run_capture_manifest_shard.py"
    ).read_text(encoding="utf-8")
    journal_formal_source = (
        capture.ROOT / "scripts/run_stage1_manifest_shard.py"
    ).read_text(encoding="utf-8")
    journal_stress_text = journal_stress_path.read_text(
        encoding="utf-8"
    )
    journal_validation_checks = {
        "quarkfs_12lane_stress_passed": "5 passed" in journal_stress_text,
        "planned_candidates_60000": (
            journal_status.get("planned_candidates") == 60_000
        ),
        "accepted_candidates_44093": (
            journal_status.get("accepted_candidates") == 44_093
        ),
        "no_unexpected_terminal_candidates": (
            journal_status.get("unexpected_terminal_candidates") == 0
        ),
        "no_duplicate_terminal_episode_ids": (
            journal_status.get("duplicate_terminal_episode_ids") == 0
        ),
        "shared_reader_lock_present": (
            "fcntl.LOCK_SH" in journal_common_source
            and "def load_jsonl_locked(" in journal_common_source
        ),
        "exclusive_writer_lock_present": (
            "fcntl.LOCK_EX" in journal_common_source
            and "def append_locked(" in journal_common_source
        ),
        "bounded_snapshot_reopen_present": (
            "JSONL_SNAPSHOT_READ_ATTEMPTS = 8"
            in journal_common_source
        ),
        "formal_mutable_journals_use_locked_reader": (
            journal_formal_source.count("common.load_jsonl_locked(") >= 5
            and "capture.load_jsonl(paths[\"accepted\"]"
            not in journal_formal_source
            and "capture.load_jsonl(paths[\"rejects\"]"
            not in journal_formal_source
        ),
    }
    if not all(journal_validation_checks.values()):
        raise capture.CaptureFailure(
            "runtime_revision_journal_fix_validation_failed",
            capture.canonical_json(journal_validation_checks),
        )
    warmup_fix_report_path = (
        capture.ROOT
        / "STAGE1_WARMUP_RESUME_NAMESPACE_FIX_REPORT.md"
    )
    warmup_validation_root = (
        capture.ROOT / "logs/stage1_warmup_resume_fix_20260730"
    )
    warmup_test_log_path = (
        warmup_validation_root / "quarkfs_targeted_final.log"
    )
    full_test_log_path = (
        warmup_validation_root / "full_pytest_r5_scoped.log"
    )
    r4_status_path = (
        warmup_validation_root / "current_r4_status.json"
    )
    r4_status = load_object(r4_status_path)
    warmup_test_text = warmup_test_log_path.read_text(
        encoding="utf-8"
    )
    full_test_text = full_test_log_path.read_text(encoding="utf-8")
    formal_worker_source = (
        capture.ROOT / "scripts/run_stage1_manifest_shard.py"
    ).read_text(encoding="utf-8")
    gang_worker_source = (
        capture.ROOT / "scripts/run_stage1_56x1_worker.sh"
    ).read_text(encoding="utf-8")
    barrier_source = (
        capture.ROOT / "scripts/stage1_distributed_barrier.py"
    ).read_text(encoding="utf-8")
    warmup_validation_checks = {
        "quarkfs_targeted_49_passed": (
            "49 passed" in warmup_test_text
        ),
        "scoped_full_suite_196_passed": (
            "1 failed, 196 passed" in full_test_text
        ),
        "only_known_offline_generator_audit_failure": (
            full_test_text.count("\nFAILED ") == 1
            and (
                "FAILED tests/test_h200_takeover.py::"
                "test_stage1_v5_semantic_path_weight_bound_"
                "is_fixed_and_audited"
            )
            in full_test_text
            and '"generator_implementation":false'
            in full_test_text
        ),
        "r4_planned_candidates_60000": (
            r4_status.get("planned_candidates") == 60_000
        ),
        "r4_accepted_candidates_48010": (
            r4_status.get("accepted_candidates") == 48_010
        ),
        "r4_completed_hard_rejects_1958": (
            r4_status.get("completed_hard_rejects") == 1_958
        ),
        "r4_missing_candidates_10032": (
            r4_status.get("missing_terminal_candidates") == 10_032
        ),
        "r4_no_unexpected_terminal_ids": (
            r4_status.get("unexpected_terminal_candidates") == 0
        ),
        "r4_no_duplicate_terminal_ids": (
            r4_status.get("duplicate_terminal_episode_ids") == 0
        ),
        "atomic_warmup_evidence_allocator": (
            "def _allocate_warmup_evidence("
            in formal_worker_source
            and "evidence.mkdir(exist_ok=False)"
            in formal_worker_source
        ),
        "monotonic_resume_suffix": (
            'f"{base_id}_u{sequence:06d}"'
            in formal_worker_source
        ),
        "old_evidence_not_deleted": (
            "atomic_mkdir_legacy_base_then_monotonic_suffix"
            in formal_worker_source
        ),
        "rank0_completion_barrier_enabled": (
            "stage1_distributed_barrier.py" in gang_worker_source
            and "stage1_distributed_barrier_finalized=1"
            in gang_worker_source
            and "stage1_distributed_all_ranks_acknowledged=1"
            in gang_worker_source
            and "stage1_distributed_rank0_clean_exit_last=1"
            in gang_worker_source
            and "STAGE1_DISTRIBUTED_BARRIER_TIMEOUT_SECONDS"
            in gang_worker_source
        ),
        "barrier_fingerprint_is_fail_closed": (
            "def validate_fingerprint(" in barrier_source
            and "load_valid_markers(" in barrier_source
            and "validate-ready" in barrier_source
            and "acknowledge-ready" in barrier_source
            and "acknowledgement-status" in barrier_source
        ),
    }
    if not all(warmup_validation_checks.values()):
        raise capture.CaptureFailure(
            "runtime_revision_warmup_resume_validation_failed",
            capture.canonical_json(warmup_validation_checks),
        )
    menu_validation_root = (
        capture.ROOT / "stage1_menu_fix_h200_validation_20260729"
    )
    menu_validation_result_path = menu_validation_root / "RESULT.json"
    menu_validation_result = load_object(menu_validation_result_path)
    menu_validation_qa_paths = [
        menu_validation_root / "attempts" / label / "package/qa.json"
        for label in (
            "warmup_discarded",
            "a_before",
            "b_intervening",
            "a_after",
        )
    ]
    menu_validation_qas = [
        load_object(path) for path in menu_validation_qa_paths
    ]
    menu_validation_checks = {
        "resident_benchmark_passed": (
            menu_validation_result.get("pass") is True
        ),
        "four_resident_sequences": (
            len(menu_validation_result.get("runtime") or []) == 4
        ),
        "all_existing_hard_gates_pass": all(
            qa.get("accepted") is True
            and all((qa.get("hard_gates") or {}).values())
            for qa in menu_validation_qas
        ),
        "menu_close_barrier_hard_gate": all(
            (qa.get("hard_gates") or {}).get(
                "resident_frontend_menu_close_barrier"
            )
            is True
            for qa in menu_validation_qas
        ),
        "frames_320": all(
            (qa.get("video") or {}).get("frames") == 320
            for qa in menu_validation_qas
        ),
        "audio_240000": all(
            (qa.get("audio") or {}).get("samples_per_channel")
            == 240_000
            for qa in menu_validation_qas
        ),
        "mapping_exact": all(
            (qa.get("mapping") or {}).get("success_rate") == 1.0
            for qa in menu_validation_qas
        ),
        "hardware_renderer": all(
            capture.is_nvidia_hardware_renderer(
                str((qa.get("runtime") or {}).get("renderer", ""))
            )
            for qa in menu_validation_qas
        ),
    }
    if not all(menu_validation_checks.values()):
        raise capture.CaptureFailure(
            "runtime_revision_menu_fix_validation_failed",
            capture.canonical_json(menu_validation_checks),
        )
    revision = {
        "schema_version": "xonotic-stage1-formal-runtime-revision-v1",
        "created_utc": created_utc,
        "passed": True,
        "formal_collection_authorized": True,
        "training_admitted": False,
        "source_root": relative_to_workspace(source_root),
        "target_root": relative_to_workspace(target_root),
        "source_metadata_sha256": capture.sha256_file(
            source_root / "MANIFEST_METADATA.json"
        ),
        "source_manifest_audit_sha256": capture.sha256_file(
            source_root / "MANIFEST_AUDIT.json"
        ),
        "source_runtime_code_lock_sha256": capture.sha256_file(
            source_root / "RUNTIME_CODE_LOCK.sha256"
        ),
        "source_workspace_code_mismatches_at_revision": old_mismatches,
        "runtime_code_lock_sha256": lock_sha256,
        "runtime_code_lock_entries": len(lock_text.splitlines()),
        "policy": {
            "schema_version": (
                capture.STAGE1_AUDIO_EXPECTATION_POLICY_SCHEMA
            ),
            "path": relative_to_workspace(policy_path),
            "sha256": capture.sha256_file(policy_path),
            "player_footstep_speed_threshold": (
                capture.STAGE1_PLAYER_FOOTSTEP_SPEED_THRESHOLD
            ),
            "synthetic_audio_fallback": False,
        },
        "gang_recovery": {
            "clean_incomplete_exit_code": 3,
            "fatal_exit_code": 2,
            "rank_local_resume_passes_default": 3,
            "gang_nonfatal_incomplete_default": True,
            "global_status_remains_authoritative": True,
            "non_cleanup_unhandled_exceptions_remain_fatal": True,
        },
        "resident_cleanup": {
            "process_close_idempotent": True,
            "lane_ownership_cleared_before_cleanup": True,
            "controller_ownership_cleared_before_cleanup": True,
            "sigkill_reap_timeout_is_diagnostic": True,
            "cleanup_exception_cannot_mask_episode_failure": True,
            "qa_and_admission_unchanged": True,
        },
        "journal_concurrency_fix": {
            "filesystem": "fuse.quarkfs_client",
            "process_local_canonical_path_lock": True,
            "reader_flock": "LOCK_SH",
            "writer_flock": "LOCK_EX",
            "stable_byte_snapshot": True,
            "bounded_snapshot_read_attempts": 8,
            "invalid_rows_skipped": False,
            "persistent_corruption_remains_fatal": True,
            "exactly_once_semantics_unchanged": True,
            "validation_checks": journal_validation_checks,
            "stress_log_path": relative_to_workspace(
                journal_stress_path
            ),
            "stress_log_sha256": capture.sha256_file(
                journal_stress_path
            ),
            "resume_status_path": relative_to_workspace(
                journal_status_path
            ),
            "resume_status_sha256": capture.sha256_file(
                journal_status_path
            ),
            "report_path": relative_to_workspace(
                journal_fix_report_path
            ),
            "report_sha256": capture.sha256_file(
                journal_fix_report_path
            ),
        },
        "warmup_resume_namespace_fix": {
            "legacy_id_is_base_only": True,
            "allocation": (
                "atomic_mkdir_legacy_base_then_monotonic_suffix"
            ),
            "maximum_names_per_base": 1_000_000,
            "old_evidence_deleted": False,
            "old_evidence_overwritten": False,
            "allocation_record": "ALLOCATION.json",
            "training_admitted": False,
            "candidate_semantics_unchanged": True,
            "validation_checks": warmup_validation_checks,
            "test_log_path": relative_to_workspace(
                warmup_test_log_path
            ),
            "test_log_sha256": capture.sha256_file(
                warmup_test_log_path
            ),
            "full_test_log_path": relative_to_workspace(
                full_test_log_path
            ),
            "full_test_log_sha256": capture.sha256_file(
                full_test_log_path
            ),
            "r4_status_path": relative_to_workspace(
                r4_status_path
            ),
            "r4_status_sha256": capture.sha256_file(
                r4_status_path
            ),
            "report_path": relative_to_workspace(
                warmup_fix_report_path
            ),
            "report_sha256": capture.sha256_file(
                warmup_fix_report_path
            ),
        },
        "distributed_completion_barrier": {
            "worker_markers": 56,
            "marker_publication": "atomic_replace",
            "run_fingerprint_required": True,
            "rank0_waits_for_all_markers": True,
            "all_ranks_wait_for_ready": True,
            "all_ranks_acknowledge_ready": True,
            "rank0_waits_for_all_acknowledgements": True,
            "rank0_exit_grace_seconds": 30,
            "rank0_exits_last": True,
            "stale_marker_satisfies_barrier": False,
            "default_timeout_seconds": 21_600,
            "fatal_worker_writes_success_marker": False,
            "independent_single_worker_jobs_disable_barrier": True,
        },
        "frontend_menu_fix": {
            "command_policy": [
                "scr_menuforcewhiledisconnected 0",
                "togglemenu 0",
            ],
            "control_barrier_before_each_playdemo": True,
            "content_based_visual_rejection": False,
            "validation_result_path": relative_to_workspace(
                menu_validation_result_path
            ),
            "validation_result_sha256": capture.sha256_file(
                menu_validation_result_path
            ),
            "validation_checks": menu_validation_checks,
            "report_path": relative_to_workspace(
                menu_fix_report_path
            ),
            "report_sha256": capture.sha256_file(
                menu_fix_report_path
            ),
            "legacy_output_quarantined": (
                "stage1_foundation_v5_output_56x1"
            ),
            "clean_output": (
                "stage1_foundation_v5_output_56x1_menu_clean_r3"
            ),
        },
        "input_identity": {
            wave: {
                "rows": metadata[wave]["rows"],
                "sha256": metadata[wave]["sha256"],
                "shards": len(metadata[wave]["shards"]),
            }
            for wave in ("primary", "replenishment")
        },
        "checks": {
            "source_formal_audit_valid": True,
            "input_manifests_byte_identical": True,
            "shards_byte_identical": True,
            "episode_ids_actions_certificates_unchanged": True,
            "existing_candidates_not_rewritten": True,
            "new_runtime_lock_matches_workspace": True,
            "qa_not_weakened_for_expected_sound": True,
            "synthetic_audio_fallback_absent": True,
            "resident_cleanup_idempotent": True,
            "sample_retry_semantics_unchanged": True,
            "formal_admission_gates_not_weakened": True,
            "resident_frontend_menu_close_barrier_added": True,
            "visual_content_heuristic_rejection_absent": True,
            "mutable_journal_reads_are_locked": True,
            "transient_jsonl_snapshot_retry_is_bounded": True,
            "persistent_jsonl_corruption_remains_fatal": True,
            "journal_fix_does_not_change_candidate_rows": True,
            "warmup_evidence_resume_safe": True,
            "old_warmup_evidence_is_immutable": True,
            "distributed_completion_barrier": True,
            "rank0_cannot_finish_before_other_ranks": True,
            "warmup_fix_does_not_change_candidate_rows": True,
        },
    }
    revision_text = canonical_json(revision)
    revision_sha256 = capture.hashlib.sha256(
        revision_text.encode()
    ).hexdigest()
    atomic_text(
        stage_root / "RUNTIME_REVISION_AUDIT.json", revision_text
    )

    revised_metadata = json.loads(json.dumps(metadata))
    rewrite_wave_paths(
        revised_metadata, target_root, "primary", "input.jsonl"
    )
    rewrite_wave_paths(
        revised_metadata,
        target_root,
        "replenishment",
        "replenishment.jsonl",
    )
    topology = revised_metadata.get("topology_reshard") or {}
    topology["path"] = relative_to_workspace(
        target_root / "TOPOLOGY_RESHARD_AUDIT.json"
    )
    revised_metadata["runtime_code_lock"] = {
        "path": relative_to_workspace(
            target_root / "RUNTIME_CODE_LOCK.sha256"
        ),
        "sha256": lock_sha256,
        "entries": len(lock_text.splitlines()),
    }
    revised_metadata["runtime_revision"] = {
        "schema_version": revision["schema_version"],
        "created_utc": created_utc,
        "path": relative_to_workspace(
            target_root / "RUNTIME_REVISION_AUDIT.json"
        ),
        "sha256": revision_sha256,
        "source_root": relative_to_workspace(source_root),
        "input_manifest_policy": (
            "byte-identical; runtime expectation, cleanup, and "
            "frontend presentation and journal synchronization "
            "plus warm-up evidence namespace and distributed "
            "completion corrections only"
        ),
    }
    revised_metadata["launch"] = {
        **(revised_metadata.get("launch") or {}),
        "status": (
            "authorized_primary_60k_warmup_resume_barrier_runtime_revision"
        ),
    }
    metadata_text = canonical_json(revised_metadata)
    metadata_sha256 = capture.hashlib.sha256(
        metadata_text.encode()
    ).hexdigest()
    atomic_text(stage_root / "MANIFEST_METADATA.json", metadata_text)

    revised_audit = json.loads(json.dumps(source_audit))
    revised_audit.update(
        {
            "created_utc": created_utc,
            "metadata_sha256": metadata_sha256,
            "runtime_code_lock_sha256": lock_sha256,
            "runtime_revision_sha256": revision_sha256,
            "source_manifest_audit_sha256": capture.sha256_file(
                source_root / "MANIFEST_AUDIT.json"
            ),
            "passed": True,
        }
    )
    formal_audit_text = canonical_json(revised_audit)
    atomic_text(stage_root / "MANIFEST_AUDIT.json", formal_audit_text)

    checks = {
        "metadata": capture.sha256_file(
            stage_root / "MANIFEST_METADATA.json"
        )
        == metadata_sha256,
        "runtime_lock": capture.sha256_file(
            stage_root / "RUNTIME_CODE_LOCK.sha256"
        )
        == lock_sha256,
        "revision": capture.sha256_file(
            stage_root / "RUNTIME_REVISION_AUDIT.json"
        )
        == revision_sha256,
        "primary": capture.sha256_file(stage_root / "input.jsonl")
        == metadata["primary"]["sha256"],
        "replenishment": capture.sha256_file(
            stage_root / "replenishment.jsonl"
        )
        == metadata["replenishment"]["sha256"],
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "runtime_revision_final_check_failed",
            capture.canonical_json(checks),
        )
    os.rename(stage_root, target_root)
    return {
        "pass": True,
        "existing": False,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "metadata_sha256": metadata_sha256,
        "manifest_audit_sha256": capture.sha256_file(
            target_root / "MANIFEST_AUDIT.json"
        ),
        "runtime_revision_sha256": revision_sha256,
        "runtime_code_lock_sha256": lock_sha256,
        "source_workspace_code_mismatches_at_revision": len(
            old_mismatches
        ),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--source-root",
        default=str(
            capture.ROOT
            / (
                "manifests/"
                "stage1_foundation_v5_formal_56x1_runtime_r4"
            )
        ),
    )
    result.add_argument(
        "--target-root",
        default=str(
            capture.ROOT
            / (
                "manifests/"
                "stage1_foundation_v5_formal_56x1_runtime_r5"
            )
        ),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        report = create_revision(
            Path(args.source_root).resolve(),
            Path(args.target_root).resolve(),
        )
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2
    print(canonical_json(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
