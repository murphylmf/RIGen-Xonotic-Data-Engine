                      
"""Validate single-writer shard journals and rebuild the global v5 index.

Distributed certifiers publish immutable certificate/rejection directories
and append only their own run-scoped shard journal.  Once all workers have
completed, this program verifies every scheduled prototype against its
terminal artifact and atomically replaces the derived global index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_v5_manifests as v5              
import xonotic_capture as capture              


EXPECTED_SOURCE_COMMIT = v5.EXPECTED_SOURCE_COMMIT
SCHEDULED_SPECS = (
    (
        "targeted_fast_world",
        "path_prototypes_targeted_fast_traversal_world_balanced.jsonl",
        1024,
    ),
    (
        "certification_spare",
        "path_prototypes_certification_spare.jsonl",
        0,
    ),
    ("primary", "path_prototypes_primary.jsonl", 0),
    ("replenishment", "path_prototypes_replenishment.jsonl", 0),
    (
        "targeted_collision",
        "path_prototypes_targeted_visible_collision.jsonl",
        0,
    ),
)
ATTEMPT_PATTERN = re.compile(r"_a([0-9]+)$")


class MergeFailure(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MergeFailure(f"invalid JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MergeFailure(f"JSON artifact is not an object: {path}")
    return value


def load_jsonl_strict(path: Path) -> list[dict[str, Any]]:
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise MergeFailure(f"cannot read JSONL {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    with handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise MergeFailure(
                    f"blank JSONL row: {path}:{line_number}"
                )
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MergeFailure(
                    f"invalid JSONL row: {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise MergeFailure(
                    f"JSONL row is not an object: {path}:{line_number}"
                )
            rows.append(value)
    return rows


def relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError as exc:
        raise MergeFailure(f"artifact escapes capture root: {path}") from exc


def validate_locked_artifact(
    root: Path,
    record: dict[str, Any],
    path_field: str,
    sha_field: str,
) -> None:
    raw_path = record.get(path_field)
    expected = record.get(sha_field)
    if not isinstance(raw_path, str) or not isinstance(expected, str):
        raise MergeFailure(
            f"certificate artifact fields missing: "
            f"{record.get('prototype_id')}:{path_field}"
        )
    relative = Path(raw_path)
    if relative.is_absolute():
        raise MergeFailure(
            f"certificate artifact path is absolute: {raw_path}"
        )
    path = (root / relative).resolve()
    relative_to_root(root, path)
    if not path.is_file():
        raise MergeFailure(f"certificate artifact missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise MergeFailure(
            f"certificate artifact hash mismatch: {path}: "
            f"expected={expected} actual={actual}"
        )


def certificate_index_row(
    root: Path,
    certificate_path: Path,
    certificate: dict[str, Any],
) -> dict[str, Any]:
    prototype_id = str(certificate.get("prototype_id", ""))
    checks = {
        "schema": certificate.get("schema_version")
        == capture.PLAYER_PATH_CERTIFICATE_SCHEMA,
        "id": prototype_id == certificate_path.parent.name,
        "status": certificate.get("status") == "certified",
        "passed": certificate.get("passed") is True,
        "source_commit": certificate.get("source_commit")
        == EXPECTED_SOURCE_COMMIT,
        "formal": certificate.get("formal_collection_authorized")
        is False,
        "training": certificate.get("training_admitted") is False,
    }
    if not all(checks.values()):
        raise MergeFailure(
            f"invalid certificate {certificate_path}: {checks}"
        )
    for path_field, sha_field in (
        ("actions_path", "actions_sha256"),
        ("states_path", "states_sha256"),
        ("events_path", "events_sha256"),
        ("server_telemetry_path", "server_telemetry_sha256"),
    ):
        validate_locked_artifact(
            root, certificate, path_field, sha_field
        )
    render = certificate.get("render_evidence")
    if render is not None:
        if not isinstance(render, dict):
            raise MergeFailure(
                f"invalid render evidence: {certificate_path}"
            )
        for path_field, sha_field in (
            ("frames_path", "frames_sha256"),
            ("audio_events_path", "audio_events_sha256"),
        ):
            validate_locked_artifact(
                root, render, path_field, sha_field
            )
    return {
        "schema_version": capture.PLAYER_PATH_REFERENCE_SCHEMA,
        "prototype_id": prototype_id,
        "candidate_wave": certificate["candidate_wave"],
        "status": "certified",
        "certified": True,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "seed": int(certificate["seed"]),
        "certificate_path": relative_to_root(
            root, certificate_path
        ),
        "certificate_sha256": sha256_file(certificate_path),
        "actions_path": certificate["actions_path"],
        "actions_sha256": certificate["actions_sha256"],
        "physical_action_sha256": certificate[
            "physical_action_sha256"
        ],
        "path_contract_sha256": certificate[
            "path_contract_sha256"
        ],
        "states_path": certificate["states_path"],
        "states_sha256": certificate["states_sha256"],
        "motion": certificate["motion"],
        "movement_blockage": certificate["movement_blockage"],
        "render_evidence": certificate.get("render_evidence"),
        "created_utc": certificate["created_utc"],
    }


def rejection_index_row(
    rejection_path: Path, rejection: dict[str, Any]
) -> dict[str, Any]:
    prototype_id = str(rejection.get("prototype_id", ""))
    checks = {
        "schema": rejection.get("schema_version")
        == "xonotic-stage1-v5-player-path-rejection-v1",
        "id": prototype_id == rejection_path.parent.name,
        "status": rejection.get("status") == "rejected",
        "reason": bool(rejection.get("reason")),
        "source_commit": rejection.get("source_commit")
        == EXPECTED_SOURCE_COMMIT,
        "formal": rejection.get("formal_collection_authorized")
        is False,
        "training": rejection.get("training_admitted") is False,
    }
    if not all(checks.values()):
        raise MergeFailure(
            f"invalid rejection {rejection_path}: {checks}"
        )
    return rejection


def terminal_directories(root: Path) -> tuple[Path, Path]:
    output = root / "stage1_path_certification_v5"
    return output / "certificates", output / "rejects"


def terminal_ids(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {
        path.name
        for path in directory.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }


def terminal_snapshot(root: Path) -> tuple[tuple[Any, ...], ...]:
    certificate_root, rejection_root = terminal_directories(root)
    result: list[tuple[Any, ...]] = []
    for kind, directory, filename in (
        ("certificate", certificate_root, "CERTIFICATE.json"),
        ("rejection", rejection_root, "REJECTION.json"),
    ):
        for prototype_id in sorted(terminal_ids(directory)):
            path = directory / prototype_id / filename
            try:
                stat = path.stat()
            except OSError as exc:
                raise MergeFailure(
                    f"terminal snapshot failed: {path}: {exc}"
                ) from exc
            result.append(
                (
                    kind,
                    prototype_id,
                    stat.st_size,
                    stat.st_mtime_ns,
                )
            )
    return tuple(result)


def attempt_number(value: Any) -> int:
    match = ATTEMPT_PATTERN.search(str(value or ""))
    return int(match.group(1)) if match else -1


def recover_spurious_dual_terminals(
    root: Path, quarantine_root: Path
) -> list[dict[str, Any]]:
    certificate_root, rejection_root = terminal_directories(root)
    overlaps = sorted(
        terminal_ids(certificate_root) & terminal_ids(rejection_root)
    )
    if not overlaps:
        return []
    planned: list[dict[str, Any]] = []
    for prototype_id in overlaps:
        certificate_path = (
            certificate_root / prototype_id / "CERTIFICATE.json"
        )
        rejection_path = (
            rejection_root / prototype_id / "REJECTION.json"
        )
        certificate = load_json(certificate_path)
        rejection = load_json(rejection_path)
                                                                            
                                                                           
        certificate_index_row(root, certificate_path, certificate)
        rejection_index_row(rejection_path, rejection)
        checks = {
            "certificate_id": certificate.get("prototype_id")
            == prototype_id,
            "certificate_status": certificate.get("status")
            == "certified",
            "certificate_passed": certificate.get("passed") is True,
            "rejection_id": rejection.get("prototype_id")
            == prototype_id,
            "rejection_status": rejection.get("status") == "rejected",
            "spurious_reason": rejection.get("reason")
            == "v5_refuse_overwrite_path_certificate",
            "same_source": certificate.get("source_commit")
            == rejection.get("source_commit")
            == EXPECTED_SOURCE_COMMIT,
            "later_attempt": attempt_number(rejection.get("attempt_id"))
            > attempt_number(certificate.get("attempt_id"))
            >= 0,
        }
        if not all(checks.values()):
            raise MergeFailure(
                f"dual terminal is not safely recoverable: "
                f"{prototype_id}: {checks}"
            )
        destination = quarantine_root / "rejects" / prototype_id
        if destination.exists():
            raise MergeFailure(
                f"quarantine destination already exists: {destination}"
            )
        planned.append(
            {
                "prototype_id": prototype_id,
                "certificate_attempt_id": certificate["attempt_id"],
                "certificate_sha256": sha256_file(certificate_path),
                "rejection_attempt_id": rejection["attempt_id"],
                "rejection_sha256": sha256_file(rejection_path),
                "rejection_reason": rejection["reason"],
                "source": relative_to_root(
                    root, rejection_path.parent
                ),
                "destination": relative_to_root(root, destination),
            }
        )
    recovery = {
        "schema_version": "xonotic-stage1-v5-dual-terminal-recovery-v1",
        "status": "planned",
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "created_utc": capture.utc_now(),
        "records": planned,
    }
    atomic_json(quarantine_root / "RECOVERY.json", recovery)
    for item in planned:
        source = root / item["source"]
        destination = root / item["destination"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.rename(source, destination)
    recovery["status"] = "completed"
    recovery["completed_utc"] = capture.utc_now()
    atomic_json(quarantine_root / "RECOVERY.json", recovery)
    return planned


def artifact_index(root: Path) -> dict[str, dict[str, Any]]:
    certificate_root, rejection_root = terminal_directories(root)
    certificate_ids = terminal_ids(certificate_root)
    rejection_ids = terminal_ids(rejection_root)
    overlap = sorted(certificate_ids & rejection_ids)
    if overlap:
        raise MergeFailure(
            "multiple terminal records remain: " + ",".join(overlap[:10])
        )
    result: dict[str, dict[str, Any]] = {}
    for prototype_id in sorted(certificate_ids):
        path = certificate_root / prototype_id / "CERTIFICATE.json"
        row = certificate_index_row(root, path, load_json(path))
        result[prototype_id] = row
    for prototype_id in sorted(rejection_ids):
        path = rejection_root / prototype_id / "REJECTION.json"
        row = rejection_index_row(path, load_json(path))
        if prototype_id in result:
            raise MergeFailure(
                f"duplicate terminal artifact: {prototype_id}"
            )
        result[prototype_id] = row
    return result


def scheduled_candidates(
    root: Path, shard_count: int
) -> tuple[dict[str, int], dict[str, str]]:
    candidate_root = (
        root / "manifests/stage1_foundation_v5_certification"
    )
    expected_shard: dict[str, int] = {}
    expected_wave: dict[str, str] = {}
    for wave, filename, ordinal_end in SCHEDULED_SPECS:
        for row in load_jsonl_strict(candidate_root / filename):
            ordinal = int(row["candidate_ordinal"])
            if ordinal_end and ordinal > ordinal_end:
                continue
            prototype_id = str(row["episode_id"])
            if prototype_id in expected_shard:
                raise MergeFailure(
                    f"duplicate scheduled prototype: {prototype_id}"
                )
            expected_shard[prototype_id] = (
                ordinal - 1
            ) % shard_count
            expected_wave[prototype_id] = wave
    return expected_shard, expected_wave


def validate_shard_journals(
    root: Path,
    journal_root: Path,
    shard_count: int,
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected_shard, expected_wave = scheduled_candidates(
        root, shard_count
    )
    observed: set[str] = set()
    journal_reports: list[dict[str, Any]] = []
    for shard_index in range(shard_count):
        tag = f"shard-{shard_index:03d}-of-{shard_count:03d}"
        path = journal_root / f"{tag}.jsonl"
        rows = load_jsonl_strict(path)
        local: set[str] = set()
        statuses: Counter[str] = Counter()
        waves: Counter[str] = Counter()
        for row in rows:
            prototype_id = str(row.get("prototype_id", ""))
            if not prototype_id or prototype_id in local:
                raise MergeFailure(
                    f"duplicate/missing ID in shard journal: "
                    f"{path}:{prototype_id}"
                )
            if prototype_id not in expected_shard:
                raise MergeFailure(
                    f"unexpected prototype in shard journal: "
                    f"{path}:{prototype_id}"
                )
            if expected_shard[prototype_id] != shard_index:
                raise MergeFailure(
                    f"prototype is in wrong shard journal: "
                    f"{prototype_id}: expected="
                    f"{expected_shard[prototype_id]} actual={shard_index}"
                )
            artifact = artifacts.get(prototype_id)
            if artifact is None:
                raise MergeFailure(
                    f"journal prototype has no terminal artifact: "
                    f"{prototype_id}"
                )
            if row != artifact:
                raise MergeFailure(
                    f"journal/artifact mismatch: {prototype_id}"
                )
            local.add(prototype_id)
            statuses[str(row["status"])] += 1
            waves[expected_wave[prototype_id]] += 1
        required = {
            prototype_id
            for prototype_id, owner in expected_shard.items()
            if owner == shard_index
        }
        missing = sorted(required - local)
        extra = sorted(local - required)
        if missing or extra:
            raise MergeFailure(
                f"incomplete shard journal {path}: "
                f"missing={missing[:5]} extra={extra[:5]}"
            )
        duplicate_across_shards = observed & local
        if duplicate_across_shards:
            raise MergeFailure(
                "prototype appears in multiple journals: "
                + ",".join(sorted(duplicate_across_shards)[:5])
            )
        observed.update(local)
        journal_reports.append(
            {
                "shard_index": shard_index,
                "path": relative_to_root(root, path),
                "sha256": sha256_file(path),
                "rows": len(rows),
                "statuses": dict(sorted(statuses.items())),
                "waves": dict(sorted(waves.items())),
            }
        )
    if observed != set(expected_shard):
        raise MergeFailure(
            f"distributed journal coverage mismatch: "
            f"expected={len(expected_shard)} observed={len(observed)}"
        )
    return {
        "expected_terminal_prototypes": len(expected_shard),
        "observed_terminal_prototypes": len(observed),
        "journals": journal_reports,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--root",
        type=Path,
        default=capture.ROOT,
        help="Capture workspace root.",
    )
    result.add_argument(
        "--journal-root",
        type=Path,
        help=(
            "Directory containing shard-NNN-of-NNN.jsonl. If omitted, "
            "only terminal artifacts are validated and rebuilt."
        ),
    )
    result.add_argument("--shard-count", type=int, default=32)
    result.add_argument("--run-id")
    result.add_argument("--run-fingerprint")
    result.add_argument(
        "--repair-spurious-overwrite-rejects",
        action="store_true",
        help=(
            "Quarantine only the narrowly recognized historical "
            "certificate-plus-overwrite-rejection bug."
        ),
    )
    result.add_argument("--quarantine-root", type=Path)
    result.add_argument(
        "--index-path",
        type=Path,
        help="Global derived index path.",
    )
    result.add_argument("--report", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    if args.shard_count < 1:
        raise SystemExit("--shard-count must be positive")
    if args.repair_spurious_overwrite_rejects:
        if args.quarantine_root is None:
            raise SystemExit(
                "--quarantine-root is required with recovery"
            )
        quarantine_root = (
            args.quarantine_root
            if args.quarantine_root.is_absolute()
            else root / args.quarantine_root
        ).resolve()
        try:
            quarantine_root.relative_to(root)
        except ValueError as exc:
            raise SystemExit(
                "--quarantine-root must be inside capture root"
            ) from exc
        recovered = recover_spurious_dual_terminals(
            root, quarantine_root
        )
    else:
        recovered = []

    before = terminal_snapshot(root)
    artifacts = artifact_index(root)
    distributed: dict[str, Any] | None = None
    if args.journal_root is not None:
        journal_root = (
            args.journal_root
            if args.journal_root.is_absolute()
            else root / args.journal_root
        ).resolve()
        distributed = validate_shard_journals(
            root, journal_root, args.shard_count, artifacts
        )
    after = terminal_snapshot(root)
    if before != after:
        raise MergeFailure(
            "terminal artifacts changed during merge validation"
        )

    index_path = (
        args.index_path
        if args.index_path is not None
        else root
        / "stage1_path_certification_v5/manifests/certificates.jsonl"
    )
    if not index_path.is_absolute():
        index_path = root / index_path
    index_path = index_path.resolve()
    try:
        index_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit("--index-path must be inside capture root") from exc
    rows = [artifacts[key] for key in sorted(artifacts)]
    if terminal_snapshot(root) != before:
        raise MergeFailure(
            "terminal artifacts changed before global index commit"
        )
    atomic_jsonl(index_path, rows)
    status_counts = Counter(str(row["status"]) for row in rows)
    report = {
        "schema_version": (
            "xonotic-stage1-v5-certificate-index-merge-v1"
        ),
        "passed": True,
        "created_utc": capture.utc_now(),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "run_id": args.run_id,
        "run_fingerprint": args.run_fingerprint,
        "index_path": relative_to_root(root, index_path),
        "index_sha256": sha256_file(index_path),
        "index_rows": len(rows),
        "statuses": dict(sorted(status_counts.items())),
        "distributed": distributed,
        "recovered_spurious_dual_terminals": recovered,
    }
    report_path = args.report
    if report_path is None:
        report_path = (
            root
            / "stage1_path_certification_v5/manifests/"
            "CERTIFICATE_INDEX_MERGE.json"
        )
    elif not report_path.is_absolute():
        report_path = root / report_path
    atomic_json(report_path.resolve(), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MergeFailure as exc:
        print(f"certificate index merge failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
