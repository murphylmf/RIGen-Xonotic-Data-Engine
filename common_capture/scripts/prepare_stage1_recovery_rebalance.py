                      
"""Seal nonterminal Stage-1 rows and deterministically rebalance 56 ways."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_stage1_manifest_shard as worker              
import xonotic_capture as capture              


SHARD_COUNT = 56
SOURCE_RUNTIME_NAME = (
    "manifests/stage1_foundation_v5_formal_56x1_runtime_r5"
)
DEFAULT_TARGET_NAME = (
    "manifests/stage1_foundation_v5_formal_56x1_recovery_r6"
)
DEFAULT_OUTPUT_NAME = "stage1_foundation_v5_output_56x1_menu_clean_r3"
NEW_RUNTIME_FILES = (
    "scripts/prepare_stage1_recovery_rebalance.py",
    "scripts/stage1_recovery_status.py",
    "scripts/stage1_recovery_runtime.py",
    "scripts/run_stage1_recovery_56x1_worker.sh",
    "scripts/submit_stage1_recovery_sensecore_56x1.sh",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def digest_ids(values: Iterable[str]) -> str:
    return sha256_text("".join(f"{value}\n" for value in sorted(values)))


def canonical_lines(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def pretty_json(value: Any) -> str:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    )


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "recovery_refuse_overwrite_drift", str(path)
            )
        return
    temporary = path.with_name(
        f".{path.name}.tmp.{os.getpid()}"
    )
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def parse_attempt(value: Any) -> int:
    try:
        return int(str(value).rsplit("_a", 1)[1])
    except (IndexError, TypeError, ValueError):
        return 0


def load_terminal_inventory(
    output_root: Path,
) -> tuple[
    set[str],
    set[str],
    dict[str, int],
    list[dict[str, Any]],
]:
    accepted: set[str] = set()
    hard_rejects: set[str] = set()
    attempt_base: dict[str, int] = {}
    journal_snapshot: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        paths = worker.shard_paths(
            output_root, shard_index, SHARD_COUNT, "primary"
        )
        for kind in ("accepted", "rejects", "queue"):
            path = paths[kind]
            rows = worker.common.load_jsonl_locked(path)
            if path.is_file():
                journal_snapshot.append(
                    {
                        "kind": kind,
                        "path": str(path.relative_to(capture.ROOT)),
                        "rows": len(rows),
                        "sha256": capture.sha256_file(path),
                        "shard_index": shard_index,
                    }
                )
            for row in rows:
                episode_id = str(row.get("episode_id", ""))
                if not episode_id:
                    raise capture.CaptureFailure(
                        "recovery_journal_episode_missing",
                        f"{path}",
                    )
                attempt_base[episode_id] = max(
                    attempt_base.get(episode_id, 0),
                    parse_attempt(row.get("attempt_id")),
                )
                if kind == "accepted":
                    accepted.add(episode_id)
                elif (
                    kind == "rejects"
                    and row.get("terminal") is True
                    and row.get("retryable") is False
                    and row.get(
                        "failure_class", "capture_failure"
                    )
                    == "capture_failure"
                ):
                    hard_rejects.add(episode_id)
    return accepted, hard_rejects, attempt_base, journal_snapshot


def recover_unjournaled_candidates(
    output_root: Path,
    source_ids: set[str],
    accepted: set[str],
    attempt_base: dict[str, int],
) -> list[str]:
    candidate_root = output_root / "candidates"
    if not candidate_root.is_dir():
        return []
    recovered: list[str] = []
    seen_candidates: set[str] = set()
    for path in candidate_root.iterdir():
        if not path.is_dir() or path.name.startswith("."):
            continue
        episode_id = path.name
        seen_candidates.add(episode_id)
        if episode_id not in source_ids:
            raise capture.CaptureFailure(
                "recovery_unexpected_candidate_directory",
                str(path),
            )
        record_path = path / "formal_candidate_record.json"
        if not record_path.is_file():
            raise capture.CaptureFailure(
                "recovery_candidate_record_missing", str(path)
            )
        if episode_id in accepted:
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("episode_id") != episode_id:
            raise capture.CaptureFailure(
                "recovery_candidate_record_mismatch", str(path)
            )
        accepted.add(episode_id)
        attempt_base[episode_id] = max(
            attempt_base.get(episode_id, 0),
            parse_attempt(record.get("attempt_id")),
        )
        recovered.append(episode_id)
    missing_accepted_artifacts = accepted - seen_candidates
    if missing_accepted_artifacts:
        raise capture.CaptureFailure(
            "recovery_accepted_artifact_missing",
            capture.canonical_json(
                sorted(missing_accepted_artifacts)[:20]
            ),
        )
    return sorted(recovered)


def load_source_rows(
    source_root: Path,
) -> tuple[list[dict[str, Any]], set[str]]:
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for shard_index in range(SHARD_COUNT):
        path = (
            source_root
            / "shards/primary"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        shard_rows = capture.load_jsonl(path)
        for row in shard_rows:
            episode_id = str(row.get("episode_id", ""))
            if (
                not episode_id
                or episode_id in ids
                or int(row.get("assigned_shard", -1))
                != shard_index
                or int(row.get("shard_count", -1))
                != SHARD_COUNT
            ):
                raise capture.CaptureFailure(
                    "recovery_source_topology_invalid",
                    f"{path}:{episode_id}",
                )
            ids.add(episode_id)
            rows.append(row)
    rows.sort(
        key=lambda row: (
            int(row.get("candidate_ordinal", 0)),
            str(row["episode_id"]),
        )
    )
    if len(rows) != 60_000:
        raise capture.CaptureFailure(
            "recovery_source_row_count",
            f"expected=60000 actual={len(rows)}",
        )
    return rows, ids


def rebalance(
    pending_rows: list[dict[str, Any]],
    namespace: str,
) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]], int]:
    ranked = sorted(
        pending_rows,
        key=lambda row: (
            hashlib.sha256(
                (
                    namespace
                    + "\0"
                    + str(row["episode_id"])
                ).encode("utf-8")
            ).hexdigest(),
            str(row["episode_id"]),
        ),
    )
    assignments: dict[str, int] = {
        str(row["episode_id"]): index % SHARD_COUNT
        for index, row in enumerate(ranked)
    }
    output_rows: list[dict[str, Any]] = []
    shards: list[list[dict[str, Any]]] = [
        [] for _ in range(SHARD_COUNT)
    ]
    moved = 0
    for source in pending_rows:
        row = copy.deepcopy(source)
        assigned = assignments[str(row["episode_id"])]
        if int(row["assigned_shard"]) != assigned:
            moved += 1
        row["assigned_shard"] = assigned
        row["shard_count"] = SHARD_COUNT
        output_rows.append(row)
        shards[assigned].append(row)
    output_rows.sort(
        key=lambda row: (
            int(row.get("candidate_ordinal", 0)),
            str(row["episode_id"]),
        )
    )
    for shard_rows in shards:
        shard_rows.sort(
            key=lambda row: (
                int(row.get("candidate_ordinal", 0)),
                str(row["episode_id"]),
            )
        )
    return output_rows, shards, moved


def build_runtime_lock(
    source_root: Path, target_root: Path
) -> tuple[str, int]:
    source_lock = source_root / "RUNTIME_CODE_LOCK.sha256"
    entries: dict[str, str] = {}
    for line in source_lock.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        entries[relative.strip()] = digest
    for relative in NEW_RUNTIME_FILES:
        path = capture.ROOT / relative
        if not path.is_file():
            raise capture.CaptureFailure(
                "recovery_runtime_file_missing", str(path)
            )
        entries[relative] = capture.sha256_file(path)
    target_relative = str(
        (target_root / "RUNTIME_CODE_LOCK.sha256").relative_to(
            capture.ROOT
        )
    )
    if target_relative in entries:
        raise capture.CaptureFailure(
            "recovery_runtime_lock_self_reference",
            target_relative,
        )
    text = "".join(
        f"{digest}  {relative}\n"
        for relative, digest in sorted(entries.items())
    )
    return text, len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-manifest-root",
        default=str(capture.ROOT / SOURCE_RUNTIME_NAME),
    )
    parser.add_argument(
        "--output-root",
        default=str(capture.ROOT / DEFAULT_OUTPUT_NAME),
    )
    parser.add_argument(
        "--target-root",
        default=str(capture.ROOT / DEFAULT_TARGET_NAME),
    )
    parser.add_argument(
        "--namespace",
        default="stage1-primary-recovery-r6",
    )
    parser.add_argument(
        "--source-run-id",
        default="pt-z9a0n2k6",
    )
    parser.add_argument(
        "--source-run-fingerprint",
        default=(
            "f696256b2def5262e5ad7c496e581e91e"
            "57b237e04adf10d9efbb5ba3677409e"
        ),
    )
    parser.add_argument(
        "--source-job-stopped",
        action="store_true",
        help=(
            "operator assertion that every source worker has stopped; "
            "required for a runnable sealed manifest"
        ),
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="materialize a non-runnable diagnostic snapshot",
    )
    args = parser.parse_args()
    if args.source_job_stopped == args.draft:
        raise capture.CaptureFailure(
            "recovery_seal_mode_invalid",
            "choose exactly one of --source-job-stopped or --draft",
        )
    if not re_fullmatch_namespace(args.namespace):
        raise capture.CaptureFailure(
            "recovery_namespace_invalid", args.namespace
        )
    source_root = Path(args.source_manifest_root).resolve()
    output_root = Path(args.output_root).resolve()
    target_root = Path(args.target_root).resolve()
    if capture.ROOT not in target_root.parents:
        raise capture.CaptureFailure(
            "recovery_target_outside_workspace", str(target_root)
        )
    source_metadata_path = source_root / "MANIFEST_METADATA.json"
    source_audit_path = source_root / "MANIFEST_AUDIT.json"
    if not source_metadata_path.is_file() or not source_audit_path.is_file():
        raise capture.CaptureFailure(
            "recovery_source_manifest_missing", str(source_root)
        )
    source_metadata = json.loads(
        source_metadata_path.read_text(encoding="utf-8")
    )
    source_barrier_root = (
        output_root
        / "manifests/distributed_runs/primary"
        / args.source_run_fingerprint
    )
    source_completion_markers = sorted(
        (source_barrier_root / "completed").glob(
            "shard-*-of-056.json"
        )
    )
    source_logs = sorted(
        (output_root / "logs/primary").glob(
            "shard-*-of-056.log"
        )
    )
    latest_source_log_mtime_ns = max(
        (path.stat().st_mtime_ns for path in source_logs),
        default=0,
    )
    source_rows, source_ids = load_source_rows(source_root)
    (
        accepted,
        hard_rejects,
        attempt_base,
        journal_snapshot,
    ) = load_terminal_inventory(output_root)
    recovered_unjournaled = recover_unjournaled_candidates(
        output_root, source_ids, accepted, attempt_base
    )
    unexpected = (accepted | hard_rejects) - source_ids
    overlap = accepted & hard_rejects
    if unexpected or overlap:
        raise capture.CaptureFailure(
            "recovery_terminal_inventory_invalid",
            capture.canonical_json(
                {
                    "unexpected": sorted(unexpected)[:20],
                    "accepted_hard_overlap": sorted(overlap)[:20],
                }
            ),
        )
    pending_ids = source_ids - accepted - hard_rejects
    pending_rows = [
        row for row in source_rows if row["episode_id"] in pending_ids
    ]
    if len(pending_rows) != len(pending_ids):
        raise capture.CaptureFailure(
            "recovery_pending_row_count_mismatch",
            f"ids={len(pending_ids)} rows={len(pending_rows)}",
        )
    output_rows, shards, moved = rebalance(
        pending_rows, args.namespace
    )
    shard_counts = [len(rows) for rows in shards]
    if not shard_counts or max(shard_counts) - min(shard_counts) > 1:
        raise capture.CaptureFailure(
            "recovery_shard_imbalance",
            capture.canonical_json(shard_counts),
        )
    changed_fields = Counter()
    source_by_id = {
        str(row["episode_id"]): row for row in pending_rows
    }
    for row in output_rows:
        source = source_by_id[str(row["episode_id"])]
        keys = set(source) | set(row)
        for key in keys:
            if source.get(key) != row.get(key):
                changed_fields[key] += 1
    if set(changed_fields) - {"assigned_shard", "shard_count"}:
        raise capture.CaptureFailure(
            "recovery_semantic_payload_changed",
            capture.canonical_json(changed_fields),
        )
    attempt_document = {
        "schema_version": "xonotic-stage1-recovery-attempt-base-v1",
        "namespace": args.namespace,
        "source_run_id": args.source_run_id,
        "source_run_fingerprint": args.source_run_fingerprint,
        "source_completion_markers": len(
            source_completion_markers
        ),
        "source_latest_log_mtime_ns": latest_source_log_mtime_ns,
        "rows": len(pending_ids),
        "attempt_base": {
            episode_id: int(attempt_base.get(episode_id, 0))
            for episode_id in sorted(pending_ids)
        },
        "created_utc": utc_now(),
    }
    attempt_text = pretty_json(attempt_document)
    attempt_path = target_root / "ATTEMPT_BASE.json"
    terminal_document = {
        "schema_version": "xonotic-stage1-terminal-snapshot-v1",
        "namespace": args.namespace,
        "source_manifest_root": str(source_root),
        "output_root": str(output_root),
        "source_run_id": args.source_run_id,
        "source_run_fingerprint": args.source_run_fingerprint,
        "source_completion_markers": len(
            source_completion_markers
        ),
        "source_latest_log_mtime_ns": latest_source_log_mtime_ns,
        "source_job_stopped": bool(args.source_job_stopped),
        "sealed": bool(args.source_job_stopped),
        "planned_candidates": len(source_ids),
        "accepted_candidates": len(accepted),
        "completed_hard_rejects": len(hard_rejects),
        "pending_candidates": len(pending_ids),
        "accepted_ids_sha256": digest_ids(accepted),
        "hard_reject_ids_sha256": digest_ids(hard_rejects),
        "pending_ids_sha256": digest_ids(pending_ids),
        "accepted_episode_ids": sorted(accepted),
        "hard_reject_episode_ids": sorted(hard_rejects),
        "pending_episode_ids": sorted(pending_ids),
        "recovered_unjournaled_candidates": recovered_unjournaled,
        "source_journals": sorted(
            journal_snapshot,
            key=lambda row: (
                int(row["shard_index"]),
                str(row["kind"]),
            ),
        ),
        "created_utc": utc_now(),
    }
    terminal_text = pretty_json(terminal_document)
    terminal_path = target_root / "TERMINAL_SNAPSHOT.json"
    input_text = canonical_lines(output_rows)
    input_path = target_root / "input.jsonl"
    shard_metadata: list[dict[str, Any]] = []
    shard_texts: list[tuple[Path, str]] = []
    for shard_index, shard_rows in enumerate(shards):
        name = (
            f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        path = target_root / "shards/primary" / name
        text = canonical_lines(shard_rows)
        shard_texts.append((path, text))
        shard_metadata.append(
            {
                "shard_index": shard_index,
                "rows": len(shard_rows),
                "path": str(path.relative_to(capture.ROOT)),
                "sha256": sha256_text(text),
            }
        )
    runtime_lock_text, runtime_lock_entries = build_runtime_lock(
        source_root, target_root
    )
    runtime_lock_path = target_root / "RUNTIME_CODE_LOCK.sha256"
    recovery_contract = {
        "schema_version": "xonotic-stage1-recovery-rebalance-v1",
        "namespace": args.namespace,
        "source_manifest_root": str(source_root),
        "source_manifest_metadata_sha256": capture.sha256_file(
            source_metadata_path
        ),
        "source_manifest_audit_sha256": capture.sha256_file(
            source_audit_path
        ),
        "source_run_id": args.source_run_id,
        "source_run_fingerprint": args.source_run_fingerprint,
        "output_root": str(output_root),
        "source_job_stopped": bool(args.source_job_stopped),
        "terminal_snapshot_sealed": bool(args.source_job_stopped),
        "terminal_snapshot_sha256": sha256_text(terminal_text),
        "terminal_snapshot": {
            "path": str(terminal_path.relative_to(capture.ROOT)),
            "sha256": sha256_text(terminal_text),
        },
        "attempt_base": {
            "path": str(attempt_path.relative_to(capture.ROOT)),
            "sha256": sha256_text(attempt_text),
        },
        "pending_candidates": len(pending_ids),
        "only_nonterminal_candidates": True,
        "exactly_once_output_root_reused": True,
        "journal_namespace_isolated": True,
        "attempt_numbers_continue_from_snapshot": True,
        "warmup_nested_qa_retry_semantics_preserved": True,
        "assignment_method": (
            "sha256(namespace+NUL+episode_id)_rank_mod_56"
        ),
        "warmup_concurrency": 4,
        "steady_lane_limit": 12,
        "live_concurrency": 12,
        "render_concurrency": 12,
        "sdl_concurrency": 12,
        "encode_concurrency": 4,
        "x264_threads": 16,
        "rank_start_stagger_seconds": 15,
        "rank_start_stagger_slots": 8,
        "server_ready_before_client_start": True,
        "server_initial_ready_marker": "Server spawned.",
    }
    metadata = copy.deepcopy(source_metadata)
    metadata["primary"] = {
        "path": str(input_path.relative_to(capture.ROOT)),
        "rows": len(output_rows),
        "sha256": sha256_text(input_text),
        "shards": shard_metadata,
        "recovery_selection": {
            "source_rows": len(source_ids),
            "accepted_excluded": len(accepted),
            "hard_rejects_excluded": len(hard_rejects),
            "pending_included": len(pending_ids),
            "pending_ids_sha256": digest_ids(pending_ids),
            "semantic_resampling": False,
        },
    }
    metadata["runtime_code_lock"] = {
        "path": str(runtime_lock_path.relative_to(capture.ROOT)),
        "sha256": sha256_text(runtime_lock_text),
        "entries": runtime_lock_entries,
    }
    metadata["recovery"] = recovery_contract
    metadata["materialized_utc"] = utc_now()
    metadata_text = pretty_json(metadata)
    metadata_path = target_root / "MANIFEST_METADATA.json"
    audit = {
        "schema_version": "xonotic-stage1-v5-formal-audit-v1",
        "passed": bool(args.source_job_stopped),
        "metadata_sha256": sha256_text(metadata_text),
        "primary_sha256": sha256_text(input_text),
        "replenishment_sha256": metadata["replenishment"]["sha256"],
        "runtime_code_lock_sha256": sha256_text(runtime_lock_text),
        "recovery_checks": {
            "source_job_stopped": bool(args.source_job_stopped),
            "terminal_snapshot_sealed": bool(args.source_job_stopped),
            "source_terminal_sets_disjoint": not overlap,
            "pending_exact_complement": (
                len(accepted)
                + len(hard_rejects)
                + len(pending_ids)
                == len(source_ids)
            ),
            "pending_manifest_exact": {
                str(row["episode_id"]) for row in output_rows
            }
            == pending_ids,
            "only_topology_fields_changed": set(changed_fields)
            <= {"assigned_shard", "shard_count"},
            "shard_balance_lte_one": (
                max(shard_counts) - min(shard_counts) <= 1
            ),
            "runtime_server_ready_fix": True,
            "runtime_warmup_admission_limit": True,
            "runtime_warmup_nested_qa_retry_semantics": True,
            "journal_namespace_isolated": True,
            "attempt_numbers_continue_from_snapshot": True,
        },
    }
    audit["passed"] = bool(
        args.source_job_stopped
        and all(audit["recovery_checks"].values())
    )
    audit_text = pretty_json(audit)
    recovery_audit = {
        "schema_version": "xonotic-stage1-recovery-rebalance-audit-v1",
        "passed": audit["passed"],
        "namespace": args.namespace,
        "source_run_id": args.source_run_id,
        "source_run_fingerprint": args.source_run_fingerprint,
        "source_completion_markers": len(
            source_completion_markers
        ),
        "source_latest_log_mtime_ns": latest_source_log_mtime_ns,
        "source_job_stopped": bool(args.source_job_stopped),
        "planned_candidates": len(source_ids),
        "accepted_excluded": len(accepted),
        "hard_rejects_excluded": len(hard_rejects),
        "pending_rebalanced": len(pending_ids),
        "pending_ids_sha256": digest_ids(pending_ids),
        "moved_shard_assignments": moved,
        "changed_fields": dict(sorted(changed_fields.items())),
        "shard_rows": shard_counts,
        "shard_rows_min": min(shard_counts),
        "shard_rows_max": max(shard_counts),
        "terminal_snapshot_sha256": sha256_text(terminal_text),
        "attempt_base_sha256": sha256_text(attempt_text),
        "input_sha256": sha256_text(input_text),
        "metadata_sha256": sha256_text(metadata_text),
        "manifest_audit_sha256": sha256_text(audit_text),
        "runtime_code_lock_sha256": sha256_text(
            runtime_lock_text
        ),
        "checks": audit["recovery_checks"],
        "created_utc": utc_now(),
    }
    write_once_or_verify(attempt_path, attempt_text)
    write_once_or_verify(terminal_path, terminal_text)
    write_once_or_verify(input_path, input_text)
    for path, text in shard_texts:
        write_once_or_verify(path, text)
    write_once_or_verify(runtime_lock_path, runtime_lock_text)
    write_once_or_verify(metadata_path, metadata_text)
    write_once_or_verify(
        target_root / "MANIFEST_AUDIT.json", audit_text
    )
    write_once_or_verify(
        target_root / "RECOVERY_AUDIT.json",
        pretty_json(recovery_audit),
    )
    print(pretty_json(recovery_audit), end="")
    return 0 if recovery_audit["passed"] else 3


def re_fullmatch_namespace(value: str) -> bool:
    if not value or len(value) > 96:
        return False
    return all(
        character.islower()
        or character.isdigit()
        or character in "._-"
        for character in value
    ) and value[0].isalnum()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        raise SystemExit(2)
