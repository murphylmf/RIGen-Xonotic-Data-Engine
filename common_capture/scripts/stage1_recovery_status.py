                      
"""Audit a sealed Stage-1 recovery run against the original 60k plan."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_capture_manifest_shard as common              
import xonotic_capture as capture              


SHARD_COUNT = 56


def recovery_paths(
    output_root: Path,
    namespace: str,
    shard_index: int,
) -> dict[str, Path]:
    root = (
        output_root
        / "manifests/recovery_runs"
        / namespace
        / "shards/primary"
        / common.shard_tag(shard_index, SHARD_COUNT)
    )
    return {
        "root": root,
        "accepted": root / "accepted_candidates.jsonl",
        "rejects": root / "rejects.jsonl",
        "queue": root / "queue_events.jsonl",
    }


def valid_candidate(output_root: Path, episode_id: str) -> bool:
    record_path = (
        output_root
        / "candidates"
        / episode_id
        / "formal_candidate_record.json"
    )
    if not record_path.is_file():
        return False
    record = json.loads(record_path.read_text(encoding="utf-8"))
    return record.get("episode_id") == episode_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-root",
        default=str(
            capture.ROOT
            / "manifests/stage1_foundation_v5_formal_56x1_recovery_r6"
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(
            capture.ROOT
            / "stage1_foundation_v5_output_56x1_menu_clean_r3"
        ),
    )
    args = parser.parse_args()
    manifest_root = Path(args.manifest_root).resolve()
    output_root = Path(args.output_root).resolve()
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )
    recovery = metadata.get("recovery") or {}
    namespace = str(recovery["namespace"])
    snapshot_reference = recovery["terminal_snapshot"]
    snapshot_path = capture.locked_root_artifact(
        snapshot_reference["path"],
        snapshot_reference["sha256"],
        "stage1_recovery_terminal_snapshot",
    )
    snapshot = json.loads(
        snapshot_path.read_text(encoding="utf-8")
    )
    snapshot_accepted = set(snapshot["accepted_episode_ids"])
    snapshot_hard = set(snapshot["hard_reject_episode_ids"])
    pending_snapshot = set(snapshot["pending_episode_ids"])
    if snapshot_accepted & snapshot_hard:
        raise capture.CaptureFailure(
            "recovery_snapshot_terminal_overlap",
            namespace,
        )
    planned_ids = (
        snapshot_accepted | snapshot_hard | pending_snapshot
    )
    recovery_accepted: set[str] = set()
    recovery_hard: set[str] = set()
    recovery_accepted_occurrences: list[str] = []
    recovery_hard_occurrences: list[str] = []
    shard_reports: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        manifest_path = (
            manifest_root
            / "shards/primary"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        rows = capture.load_jsonl(manifest_path)
        shard_ids = {str(row["episode_id"]) for row in rows}
        paths = recovery_paths(
            output_root, namespace, shard_index
        )
        accepted_rows = common.load_jsonl_locked(paths["accepted"])
        reject_rows = common.load_jsonl_locked(paths["rejects"])
        accepted_ids = {
            str(row["episode_id"]) for row in accepted_rows
        }
        hard_ids = {
            str(row["episode_id"])
            for row in reject_rows
            if row.get("terminal") is True
            and row.get("retryable") is False
            and row.get("failure_class", "capture_failure")
            == "capture_failure"
        }
        for episode_id in shard_ids - accepted_ids - hard_ids:
            if valid_candidate(output_root, episode_id):
                accepted_ids.add(episode_id)
        recovery_accepted.update(accepted_ids)
        recovery_hard.update(hard_ids)
        recovery_accepted_occurrences.extend(accepted_ids)
        recovery_hard_occurrences.extend(hard_ids)
        complete_ids = accepted_ids | hard_ids
        missing = shard_ids - complete_ids
        unexpected = complete_ids - shard_ids
        result_path = paths["root"] / "RUN_RESULT.json"
        run_result = (
            json.loads(result_path.read_text(encoding="utf-8"))
            if result_path.is_file()
            else None
        )
        shard_reports.append(
            {
                "shard_index": shard_index,
                "planned_candidates": len(shard_ids),
                "accepted_candidates": len(accepted_ids),
                "completed_hard_rejects": len(hard_ids),
                "missing_terminal_candidates": len(missing),
                "unexpected_terminal_candidates": len(unexpected),
                "duplicate_terminal_candidates": len(
                    accepted_ids & hard_ids
                ),
                "reject_attempts": len(reject_rows),
                "run_result": (
                    str(result_path)
                    if result_path.is_file()
                    else None
                ),
                "complete": bool(
                    run_result
                    and run_result.get("complete") is True
                    and not missing
                    and not unexpected
                    and not (accepted_ids & hard_ids)
                ),
            }
        )
    terminal_overlap = (
        snapshot_accepted | recovery_accepted
    ) & (snapshot_hard | recovery_hard)
    unexpected_recovery = (
        recovery_accepted | recovery_hard
    ) - pending_snapshot
    missing = pending_snapshot - recovery_accepted - recovery_hard
    accepted_all = snapshot_accepted | recovery_accepted
    hard_all = snapshot_hard | recovery_hard
    report = {
        "schema_version": "xonotic-stage1-recovery-status-v1",
        "created_utc": capture.utc_now(),
        "namespace": namespace,
        "manifest_root": str(manifest_root),
        "output_root": str(output_root),
        "shard_count": SHARD_COUNT,
        "planned_candidates": len(planned_ids),
        "snapshot_accepted_candidates": len(snapshot_accepted),
        "snapshot_completed_hard_rejects": len(snapshot_hard),
        "snapshot_pending_candidates": len(pending_snapshot),
        "recovery_accepted_candidates": len(recovery_accepted),
        "recovery_completed_hard_rejects": len(recovery_hard),
        "accepted_candidates": len(accepted_all),
        "completed_hard_rejects": len(hard_all),
        "missing_terminal_candidates": len(missing),
        "unexpected_recovery_candidates": len(
            unexpected_recovery
        ),
        "accepted_hard_reject_overlap": len(terminal_overlap),
        "duplicate_recovery_accepted_candidates": (
            len(recovery_accepted_occurrences)
            - len(set(recovery_accepted_occurrences))
        ),
        "duplicate_recovery_hard_reject_candidates": (
            len(recovery_hard_occurrences)
            - len(set(recovery_hard_occurrences))
        ),
        "complete_shards": sum(
            int(row["complete"]) for row in shard_reports
        ),
        "shards": shard_reports,
    }
    report["complete"] = bool(
        report["planned_candidates"] == 60_000
        and report["complete_shards"] == SHARD_COUNT
        and report["missing_terminal_candidates"] == 0
        and report["unexpected_recovery_candidates"] == 0
        and report["accepted_hard_reject_overlap"] == 0
        and report[
            "duplicate_recovery_accepted_candidates"
        ]
        == 0
        and report[
            "duplicate_recovery_hard_reject_candidates"
        ]
        == 0
        and len(accepted_all) + len(hard_all) == 60_000
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        raise SystemExit(2)
