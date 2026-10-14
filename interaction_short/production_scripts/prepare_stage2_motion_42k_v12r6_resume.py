                      
"""Prepare an isolated v12r6 resume without replaying known terminal QA rejects."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SHARD_COUNT = 28
TARGET_PER_SHARD = 1_500
SOURCE_MANIFEST = (
    ROOT
    / "manifests/stage2_motion_near5_combo_42k_v12_replenish_28shard_20260818_r5"
)
OLD_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_42k_v12_replenish_28gpu_20260818_01"
)
CURRENT_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_42k_v12_replenish_r5fix_28gpu_20260818_01"
)
OUTPUT_MANIFEST = (
    ROOT
    / "manifests/stage2_motion_near5_combo_42k_v12_replenish_28shard_20260818_r6"
)
OUTPUT_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_42k_v12_replenish_r6retryfix_28gpu_20260818_01"
)
RUNTIME_LOCK = (
    ROOT / "locks/stage2_motion_7x4_activeonly_v12r6_resilient_runtime.sha256"
)
PREFROZEN_CHECK = "prefrozen_player_trace_runtime_recertified"
RUNTIME_FILES = (
    "pilot_scripts/build_samples.py",
    "pilot_scripts/build_samples_v12.py",
    "production_scripts/gpu_memory_holder.py",
    "production_scripts/launch_dlc_7x4_activeonly_v12r6_resilient.sh",
    "production_scripts/prepare_stage2_motion_42k_v12r6_resume.py",
    "production_scripts/run_stage2_motion_40k_shard_v12_support.py",
    "production_scripts/run_stage2_motion_42k_activeonly_v12r6_multigpu.py",
    "production_scripts/run_stage2_motion_42k_activeonly_v12r6_shard.py",
    "scripts/xonotic_stage1_reusable.py",
    "scripts/xonotic_stage2_causal_formal.py",
)

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "production_scripts"))
import run_stage2_motion_42k_activeonly_v12r6_shard as resume_runner              


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def journal_snapshot(run_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(run_root.glob("shard_*/manifests/*.jsonl")):
        relative = str(path.relative_to(run_root))
        result[relative] = sha256_file(path)
    return result


def terminal_qa_reject(row: dict[str, Any]) -> bool:
    if row.get("reason") in {
        "active_authoritative_qa_failed",
        "carried_terminal_qa_reject",
    }:
        return True
    error = str(row.get("error") or "")
    return error.startswith(f"retryable_active_qa_failed:{PREFROZEN_CHECK}")


def reject_class(row: dict[str, Any]) -> str:
    if row.get("reason") in {
        "active_authoritative_qa_failed",
        "carried_terminal_qa_reject",
    }:
        return "semantic_qa"
    if terminal_qa_reject(row):
        return "prefrozen_trace_recertification"
    return "retryable_operational"


def load_manifest_keys(manifest_root: Path) -> tuple[dict[str, int], list[Path]]:
    paths = [
        manifest_root / "shards-028" / f"shard-{index:03d}-of-028.jsonl"
        for index in range(SHARD_COUNT)
    ]
    key_to_shard: dict[str, int] = {}
    for index, path in enumerate(paths):
        rows = read_jsonl(path)
        if len(rows) != 1_875:
            raise RuntimeError(f"unexpected shard rows: shard={index} rows={len(rows)}")
        for row in rows:
            key = str(row["sample_key"])
            if key in key_to_shard:
                raise RuntimeError(f"duplicate manifest key: {key}")
            if int(row["assigned_shard"]) != index:
                raise RuntimeError(f"manifest shard mismatch: {key}")
            key_to_shard[key] = index
    if len(key_to_shard) != 52_500:
        raise RuntimeError(f"unexpected manifest keys: {len(key_to_shard)}")
    return key_to_shard, paths


def load_current_accepted(
    run_root: Path,
    key_to_shard: dict[str, int],
    *,
    verify_records: bool,
) -> dict[str, dict[str, Any]]:
    accepted: dict[str, dict[str, Any]] = {}
    for index in range(SHARD_COUNT):
        path = run_root / f"shard_{index:02d}/manifests/accepted.jsonl"
        for row in read_jsonl(path):
            key = str(row["sample_key"])
            if key in accepted:
                raise RuntimeError(f"duplicate accepted key: {key}")
            if key_to_shard.get(key) != index:
                raise RuntimeError(f"accepted key outside shard: {key}")
            accepted[key] = row
    if verify_records:
        failures: list[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=64) as executor:
            futures = {
                executor.submit(resume_runner.verify_accepted_record, row): key
                for key, row in accepted.items()
            }
            for future in concurrent.futures.as_completed(futures):
                key = futures[future]
                try:
                    passed = future.result()
                except Exception as exc:
                    raise RuntimeError(
                        f"accepted artifact verification crashed: {key}: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                if not passed:
                    failures.append(key)
        if failures:
            raise RuntimeError(
                "accepted artifact integrity failed: "
                + ",".join(sorted(failures)[:20])
            )
    return accepted


def load_terminal_rejects(
    runs: list[tuple[str, Path]],
    key_to_shard: dict[str, int],
    accepted_keys: set[str],
) -> dict[str, dict[str, Any]]:
    terminal: dict[str, dict[str, Any]] = {}
    for source_label, run_root in runs:
        for index in range(SHARD_COUNT):
            path = run_root / f"shard_{index:02d}/manifests/rejected.jsonl"
            for row in read_jsonl(path):
                key = str(row["sample_key"])
                if key in accepted_keys or not terminal_qa_reject(row):
                    continue
                if key_to_shard.get(key) != index:
                    raise RuntimeError(f"rejected key outside shard: {key}")
                terminal[key] = {
                    "schema_version": (
                        "xonotic-stage2-motion-near5-combo-reject-v12-replenish"
                    ),
                    "sample_key": key,
                    "ordinal": int(row["ordinal"]),
                    "role": "active",
                    "reason": "carried_terminal_qa_reject",
                    "failed_checks": (
                        list(row.get("failed_checks") or [])
                        or [PREFROZEN_CHECK]
                    ),
                    "rejected_utc": str(row.get("rejected_utc") or utc_now()),
                    "source_reject_class": reject_class(row),
                    "source_reason": row.get("reason"),
                    "source_error": row.get("error"),
                    "source_run": source_label,
                    "carryover_policy": (
                        "skip_known_semantic_and_prefrozen_qa_retry_operational_v1"
                    ),
                }
    return terminal


def capacity_report(
    accepted: dict[str, dict[str, Any]],
    terminal: dict[str, dict[str, Any]],
    key_to_shard: dict[str, int],
) -> list[dict[str, Any]]:
    result = []
    for index in range(SHARD_COUNT):
        accepted_count = sum(key_to_shard[key] == index for key in accepted)
        terminal_count = sum(key_to_shard[key] == index for key in terminal)
        pending = 1_875 - accepted_count - terminal_count
        possible = accepted_count + pending
        if possible < TARGET_PER_SHARD:
            raise RuntimeError(
                f"shard cannot reach quota after terminal carryover: "
                f"shard={index} possible={possible}"
            )
        result.append(
            {
                "shard_index": index,
                "accepted": accepted_count,
                "terminal_qa_rejected": terminal_count,
                "pending_candidates": pending,
                "accepts_needed": TARGET_PER_SHARD - accepted_count,
                "maximum_possible_accepted": possible,
            }
        )
    return result


def runtime_hashes() -> dict[str, str]:
    missing = [relative for relative in RUNTIME_FILES if not (ROOT / relative).is_file()]
    if missing:
        raise RuntimeError(f"missing v12r6 runtime files: {missing}")
    return {relative: sha256_file(ROOT / relative) for relative in RUNTIME_FILES}


def write_runtime_lock(path: Path, hashes: dict[str, str]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite runtime lock: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in hashes.items()),
        encoding="utf-8",
    )


def prepare_manifest(
    source_root: Path,
    staging_root: Path,
    runtime: dict[str, str],
) -> None:
    source_metadata_path = source_root / "MANIFEST_METADATA.json"
    metadata = json.loads(source_metadata_path.read_text(encoding="utf-8"))
    if int(metadata.get("candidate_rows", -1)) != 52_500:
        raise RuntimeError("source manifest candidate budget mismatch")
    staging_root.mkdir(parents=True)
    shutil.copytree(source_root / "shards-028", staging_root / "shards-028")
    shutil.copy2(source_root / "MANIFEST_AUDIT.json", staging_root / "MANIFEST_AUDIT.json")
    for shard in metadata["shards"]:
        path = staging_root / str(shard["path"])
        if sha256_file(path) != shard["sha256"]:
            raise RuntimeError(f"copied shard hash mismatch: {path}")
    metadata = copy.deepcopy(metadata)
    metadata["runtime_files"] = runtime
    metadata["operational_revision"] = "v12r6_retry_efficiency_fix"
    metadata["resume_policy"] = {
        "job_level_supervision": "infinite_launcher_restart_and_idle_hold",
        "max_candidate_attempts": 2,
        "carry_accepted": True,
        "carry_terminal_semantic_qa_rejects": True,
        "carry_terminal_prefrozen_trace_rejects": True,
        "retry_old_operational_failures": True,
        "semantic_qa_invalidates_resident_lane": False,
    }
    write_json(staging_root / "MANIFEST_METADATA.json", metadata)
    with (staging_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(staging_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(
                    f"{sha256_file(path)}  {path.relative_to(staging_root)}\n"
                )


def prepare_run(
    staging_root: Path,
    final_root: Path,
    accepted: dict[str, dict[str, Any]],
    terminal: dict[str, dict[str, Any]],
    key_to_shard: dict[str, int],
    capacity: list[dict[str, Any]],
    source_snapshots: dict[str, dict[str, str]],
) -> None:
    staging_root.mkdir(parents=True)
    carried_utc = utc_now()
    for index in range(SHARD_COUNT):
        shard_root = staging_root / f"shard_{index:02d}"
        manifests_root = shard_root / "manifests"
        manifests_root.mkdir(parents=True)
        accepted_rows = []
        for key, source in sorted(
            accepted.items(), key=lambda item: int(item[1]["ordinal"])
        ):
            if key_to_shard[key] != index:
                continue
            accepted_rows.append(
                {
                    **source,
                    "acceptance_source": "v12r6_verified_carryover",
                    "source_acceptance_source": source.get("acceptance_source"),
                    "carried_utc": carried_utc,
                    "carryover_storage": "zero_copy_immutable_source_reference",
                }
            )
        rejected_rows = [
            row
            for key, row in sorted(
                terminal.items(), key=lambda item: int(item[1]["ordinal"])
            )
            if key_to_shard[key] == index
        ]
        write_jsonl(manifests_root / "accepted.jsonl", accepted_rows)
        write_jsonl(manifests_root / "rejected.jsonl", rejected_rows)
    outcome_counts = Counter(
        str(row.get("actual_outcome")) for row in accepted.values()
    )
    reject_counts = Counter(
        str(row["source_reject_class"]) for row in terminal.values()
    )
    summary = {
        "schema_version": "xonotic-stage2-motion-v12r6-resume-v1",
        "created_utc": carried_utc,
        "source_runs": {
            "old_v12": str(OLD_RUN),
            "current_r5fix": str(CURRENT_RUN),
        },
        "source_journal_snapshots": source_snapshots,
        "output_run_root": str(final_root),
        "carried_accepted_records": len(accepted),
        "carried_terminal_qa_rejects": len(terminal),
        "retryable_operational_rejects_not_carried": True,
        "accepted_actual_outcome_distribution": dict(sorted(outcome_counts.items())),
        "terminal_reject_distribution": dict(sorted(reject_counts.items())),
        "per_shard_capacity": capacity,
        "policy": {
            "job_level_supervision": "infinite_launcher_restart_and_idle_hold",
            "max_candidate_attempts": 2,
            "prefrozen_trace_recertification_retryable": False,
            "semantic_qa_invalidates_resident_lane": False,
        },
        "old_artifacts_modified": False,
    }
    write_json(staging_root / "CARRYOVER_SUMMARY.json", summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest-root", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--old-run-root", type=Path, default=OLD_RUN)
    parser.add_argument("--current-run-root", type=Path, default=CURRENT_RUN)
    parser.add_argument("--output-manifest-root", type=Path, default=OUTPUT_MANIFEST)
    parser.add_argument("--output-run-root", type=Path, default=OUTPUT_RUN)
    parser.add_argument("--runtime-lock", type=Path, default=RUNTIME_LOCK)
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    key_to_shard, _ = load_manifest_keys(args.source_manifest_root)
    accepted = load_current_accepted(
        args.current_run_root,
        key_to_shard,
        verify_records=not args.plan_only,
    )
    terminal = load_terminal_rejects(
        [("old_v12", args.old_run_root), ("current_r5fix", args.current_run_root)],
        key_to_shard,
        set(accepted),
    )
    capacity = capacity_report(accepted, terminal, key_to_shard)
    report = {
        "accepted": len(accepted),
        "terminal_qa_rejected": len(terminal),
        "pending": 52_500 - len(accepted) - len(terminal),
        "accepts_needed": 42_000 - len(accepted),
        "minimum_shard_capacity_margin": min(
            row["maximum_possible_accepted"] - TARGET_PER_SHARD
            for row in capacity
        ),
    }
    if args.plan_only:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    for path in (args.output_manifest_root, args.output_run_root, args.runtime_lock):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite output: {path}")
    snapshots_before = {
        "old_v12": journal_snapshot(args.old_run_root),
        "current_r5fix": journal_snapshot(args.current_run_root),
    }
    runtime = runtime_hashes()
    manifest_staging = args.output_manifest_root.with_name(
        f".{args.output_manifest_root.name}.tmp.{os.getpid()}"
    )
    run_staging = args.output_run_root.with_name(
        f".{args.output_run_root.name}.tmp.{os.getpid()}"
    )
    for path in (manifest_staging, run_staging):
        if path.exists():
            raise FileExistsError(f"staging path exists: {path}")
    try:
        prepare_manifest(args.source_manifest_root, manifest_staging, runtime)
        prepare_run(
            run_staging,
            args.output_run_root,
            accepted,
            terminal,
            key_to_shard,
            capacity,
            snapshots_before,
        )
        snapshots_after = {
            "old_v12": journal_snapshot(args.old_run_root),
            "current_r5fix": journal_snapshot(args.current_run_root),
        }
        if snapshots_after != snapshots_before:
            raise RuntimeError("source journals changed while preparing resume")
        write_runtime_lock(args.runtime_lock, runtime)
        os.replace(manifest_staging, args.output_manifest_root)
        os.replace(run_staging, args.output_run_root)
    except Exception:
        shutil.rmtree(manifest_staging, ignore_errors=True)
        shutil.rmtree(run_staging, ignore_errors=True)
        raise
    print(json.dumps({**report, "pass": True}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
