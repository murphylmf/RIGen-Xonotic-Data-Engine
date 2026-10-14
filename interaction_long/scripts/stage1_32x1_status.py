                      
"""Summarize all 32 formal Stage-1 worker shards."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_stage1_manifest_shard as worker              
import xonotic_capture as capture              


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(
            capture.ROOT / "stage1_foundation_v5_output"
        ),
    )
    parser.add_argument("--shard-count", type=int, default=32)
    parser.add_argument(
        "--manifest-root",
        default=str(
            capture.ROOT / "manifests/stage1_foundation_v5_formal"
        ),
    )
    parser.add_argument(
        "--candidate-wave",
        choices=("primary", "replenishment"),
        default="primary",
    )
    args = parser.parse_args()
    output_root = Path(args.output_root).resolve()
    manifest_root = Path(args.manifest_root).resolve()
    shards = []
    planned_ids: list[str] = []
    accepted_ids: list[str] = []
    terminal_ids: list[str] = []
    missing_ids: list[str] = []
    unexpected_ids: list[str] = []
    for shard_index in range(args.shard_count):
        paths = worker.shard_paths(
            output_root,
            shard_index,
            args.shard_count,
            args.candidate_wave,
        )
        tag = f"shard-{shard_index:03d}-of-{args.shard_count:03d}"
        input_manifest = (
            manifest_root
            / "shards"
            / args.candidate_wave
            / f"{tag}.jsonl"
        )
        planned = capture.load_jsonl(input_manifest)
        accepted = [
            row
            for row in worker.common.load_jsonl_locked(
                paths["accepted"]
            )
            if row.get("candidate_wave") == args.candidate_wave
        ]
        rejects = [
            row
            for row in worker.common.load_jsonl_locked(
                paths["rejects"]
            )
            if row.get("candidate_wave") == args.candidate_wave
        ]
        hard_terminal = [
            row
            for row in rejects
            if row.get("terminal") is True
            and row.get("retryable") is False
            and row.get("failure_class", "capture_failure")
            == "capture_failure"
        ]
        result_path = paths["root"] / "RUN_RESULT.json"
        run_result = (
            json.loads(result_path.read_text(encoding="utf-8"))
            if result_path.is_file()
            else None
        )
        planned_unique = {
            str(row["episode_id"]) for row in planned
        }
        accepted_unique = {
            str(row["episode_id"]) for row in accepted
        }
        terminal_unique = {
            str(row["episode_id"]) for row in hard_terminal
        }
        completed_unique = accepted_unique | terminal_unique
        missing_unique = planned_unique - completed_unique
        unexpected_unique = completed_unique - planned_unique
        planned_ids.extend(str(row["episode_id"]) for row in planned)
        accepted_ids.extend(accepted_unique)
        terminal_ids.extend(terminal_unique)
        missing_ids.extend(missing_unique)
        unexpected_ids.extend(unexpected_unique)
        shard_complete = bool(
            run_result
            and run_result.get("candidate_wave")
            == args.candidate_wave
            and run_result.get("complete")
            and not missing_unique
            and not unexpected_unique
            and not (accepted_unique & terminal_unique)
        )
        shards.append(
            {
                "shard_index": shard_index,
                "input_manifest": str(input_manifest),
                "planned_candidates": len(planned_unique),
                "accepted_candidates": len(accepted_unique),
                "completed_hard_rejects": len(
                    terminal_unique
                ),
                "reject_attempts": len(rejects),
                "missing_terminal_candidates": len(
                    missing_unique
                ),
                "unexpected_terminal_candidates": len(
                    unexpected_unique
                ),
                "duplicate_terminal_candidates": len(
                    accepted_unique & terminal_unique
                ),
                "complete": shard_complete,
                "run_result": (
                    str(result_path)
                    if result_path.is_file()
                    else None
                ),
            }
        )
    all_terminal = accepted_ids + terminal_ids
    planned_counts = Counter(planned_ids)
    report = {
        "schema_version": "xonotic-stage1-32x1-status-v2",
        "created_utc": capture.utc_now(),
        "output_root": str(output_root),
        "manifest_root": str(manifest_root),
        "candidate_wave": args.candidate_wave,
        "shard_count": args.shard_count,
        "complete_shards": sum(row["complete"] for row in shards),
        "planned_candidates": len(set(planned_ids)),
        "accepted_candidates": len(set(accepted_ids)),
        "completed_hard_rejects": len(set(terminal_ids)),
        "missing_terminal_candidates": len(set(missing_ids)),
        "unexpected_terminal_candidates": len(
            set(unexpected_ids)
        ),
        "duplicate_planned_episode_ids": sum(
            count - 1 for count in planned_counts.values()
        ),
        "duplicate_terminal_episode_ids": len(all_terminal)
        - len(set(all_terminal)),
        "quota_state": "pending_global_realized_quota_audit",
        "shards": shards,
    }
    report["complete"] = bool(
        report["complete_shards"] == args.shard_count
        and report["missing_terminal_candidates"] == 0
        and report["unexpected_terminal_candidates"] == 0
        and report["duplicate_planned_episode_ids"] == 0
        and report["duplicate_terminal_episode_ids"] == 0
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
