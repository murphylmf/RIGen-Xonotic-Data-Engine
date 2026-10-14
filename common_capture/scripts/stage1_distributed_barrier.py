                      
"""Coordinate clean completion of one distributed Stage-1 gang run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_MARKER = "xonotic-stage1-distributed-worker-marker-v1"
SCHEMA_READY = "xonotic-stage1-distributed-ready-v1"
SCHEMA_ACKNOWLEDGEMENT = (
    "xonotic-stage1-distributed-ready-acknowledgement-v1"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}"
    )
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(canonical_json(value))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def validate_fingerprint(value: str) -> str:
    if (
        len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("fingerprint must be 64 lowercase hex characters")
    return value


def marker_path(root: Path, shard_index: int, shard_count: int) -> Path:
    return (
        root
        / "completed"
        / f"shard-{shard_index:03d}-of-{shard_count:03d}.json"
    )


def acknowledgement_path(
    root: Path,
    shard_index: int,
    shard_count: int,
) -> Path:
    return (
        root
        / "acknowledged"
        / f"shard-{shard_index:03d}-of-{shard_count:03d}.json"
    )


def load_valid_markers(
    root: Path,
    fingerprint: str,
    shard_count: int,
) -> tuple[dict[int, dict[str, Any]], dict[int, str]]:
    valid: dict[int, dict[str, Any]] = {}
    invalid: dict[int, str] = {}
    for shard_index in range(shard_count):
        path = marker_path(root, shard_index, shard_count)
        if not path.is_file():
            continue
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            invalid[shard_index] = f"unreadable:{exc}"
            continue
        checks = {
            "schema": row.get("schema_version") == SCHEMA_MARKER,
            "fingerprint": row.get("run_fingerprint") == fingerprint,
            "shard_index": row.get("shard_index") == shard_index,
            "shard_count": row.get("shard_count") == shard_count,
            "disposition": row.get("disposition")
            in {"complete", "retryable_incomplete"},
        }
        if not all(checks.values()):
            invalid[shard_index] = canonical_json(checks).strip()
            continue
        valid[shard_index] = row
    return valid, invalid


def status_payload(
    root: Path,
    fingerprint: str,
    shard_count: int,
) -> dict[str, Any]:
    valid, invalid = load_valid_markers(
        root, fingerprint, shard_count
    )
    counts = Counter(
        str(row["disposition"]) for row in valid.values()
    )
    return {
        "schema_version": "xonotic-stage1-distributed-status-v1",
        "run_fingerprint": fingerprint,
        "shard_count": shard_count,
        "valid_markers": len(valid),
        "missing_shards": [
            index for index in range(shard_count) if index not in valid
        ],
        "invalid_shards": invalid,
        "dispositions": dict(sorted(counts.items())),
        "ready": len(valid) == shard_count and not invalid,
    }


def ready_payload(
    root: Path,
    fingerprint: str,
    shard_count: int,
) -> tuple[dict[str, Any] | None, dict[str, bool]]:
    path = root / "READY.json"
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, {"readable": False}
    checks = {
        "schema": row.get("schema_version") == SCHEMA_READY,
        "fingerprint": row.get("run_fingerprint") == fingerprint,
        "shard_count": row.get("shard_count") == shard_count,
        "valid_markers": row.get("valid_markers") == shard_count,
    }
    return row, checks


def acknowledgement_status_payload(
    root: Path,
    fingerprint: str,
    shard_count: int,
) -> dict[str, Any]:
    valid: dict[int, dict[str, Any]] = {}
    invalid: dict[int, str] = {}
    for shard_index in range(shard_count):
        path = acknowledgement_path(root, shard_index, shard_count)
        if not path.is_file():
            continue
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            invalid[shard_index] = f"unreadable:{exc}"
            continue
        checks = {
            "schema": (
                row.get("schema_version") == SCHEMA_ACKNOWLEDGEMENT
            ),
            "fingerprint": row.get("run_fingerprint") == fingerprint,
            "shard_index": row.get("shard_index") == shard_index,
            "shard_count": row.get("shard_count") == shard_count,
        }
        if not all(checks.values()):
            invalid[shard_index] = canonical_json(checks).strip()
            continue
        valid[shard_index] = row
    return {
        "schema_version": (
            "xonotic-stage1-distributed-acknowledgement-status-v1"
        ),
        "run_fingerprint": fingerprint,
        "shard_count": shard_count,
        "valid_acknowledgements": len(valid),
        "missing_shards": [
            index for index in range(shard_count) if index not in valid
        ],
        "invalid_shards": invalid,
        "ready": len(valid) == shard_count and not invalid,
    }


def command_mark(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    fingerprint = validate_fingerprint(args.fingerprint)
    marker = marker_path(root, args.shard_index, args.shard_count)
    payload = {
        "schema_version": SCHEMA_MARKER,
        "run_id": args.run_id,
        "run_fingerprint": fingerprint,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "candidate_wave": args.candidate_wave,
        "manifest_root": args.manifest_root,
        "output_root": args.output_root,
        "disposition": args.disposition,
        "resume_pass": args.resume_pass,
        "created_utc": utc_now(),
    }
    atomic_json(marker, payload)
    print(canonical_json(payload), end="")
    return 0


def command_status(args: argparse.Namespace) -> int:
    payload = status_payload(
        Path(args.root).resolve(),
        validate_fingerprint(args.fingerprint),
        args.shard_count,
    )
    print(canonical_json(payload), end="")
    return 0 if payload["ready"] else 3


def command_finalize(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    fingerprint = validate_fingerprint(args.fingerprint)
    status = status_payload(root, fingerprint, args.shard_count)
    if not status["ready"]:
        print(canonical_json(status), end="")
        return 3
    ready = {
        "schema_version": SCHEMA_READY,
        "run_id": args.run_id,
        "run_fingerprint": fingerprint,
        "shard_count": args.shard_count,
        "valid_markers": status["valid_markers"],
        "dispositions": status["dispositions"],
        "created_utc": utc_now(),
    }
    atomic_json(root / "READY.json", ready)
    print(canonical_json(ready), end="")
    return 0


def command_validate_ready(args: argparse.Namespace) -> int:
    row, checks = ready_payload(
        Path(args.root).resolve(),
        validate_fingerprint(args.fingerprint),
        args.shard_count,
    )
    if not all(checks.values()):
        print(canonical_json(checks), end="")
        return 3
    assert row is not None
    print(canonical_json(row), end="")
    return 0


def command_acknowledge_ready(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    fingerprint = validate_fingerprint(args.fingerprint)
    ready, checks = ready_payload(
        root,
        fingerprint,
        args.shard_count,
    )
    if not all(checks.values()):
        print(canonical_json(checks), end="")
        return 3
    assert ready is not None
    payload = {
        "schema_version": SCHEMA_ACKNOWLEDGEMENT,
        "run_id": args.run_id,
        "run_fingerprint": fingerprint,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "ready_created_utc": ready["created_utc"],
        "created_utc": utc_now(),
    }
    atomic_json(
        acknowledgement_path(
            root,
            args.shard_index,
            args.shard_count,
        ),
        payload,
    )
    print(canonical_json(payload), end="")
    return 0


def command_acknowledgement_status(args: argparse.Namespace) -> int:
    payload = acknowledgement_status_payload(
        Path(args.root).resolve(),
        validate_fingerprint(args.fingerprint),
        args.shard_count,
    )
    print(canonical_json(payload), end="")
    return 0 if payload["ready"] else 3


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)

    def common(command: argparse.ArgumentParser) -> None:
        command.add_argument("--root", required=True)
        command.add_argument("--fingerprint", required=True)
        command.add_argument("--shard-count", required=True, type=int)

    mark = commands.add_parser("mark")
    common(mark)
    mark.add_argument("--run-id", required=True)
    mark.add_argument("--shard-index", required=True, type=int)
    mark.add_argument(
        "--disposition",
        required=True,
        choices=("complete", "retryable_incomplete"),
    )
    mark.add_argument("--resume-pass", required=True, type=int)
    mark.add_argument("--candidate-wave", required=True)
    mark.add_argument("--manifest-root", required=True)
    mark.add_argument("--output-root", required=True)
    mark.set_defaults(func=command_mark)

    status = commands.add_parser("status")
    common(status)
    status.set_defaults(func=command_status)

    finalize = commands.add_parser("finalize")
    common(finalize)
    finalize.add_argument("--run-id", required=True)
    finalize.set_defaults(func=command_finalize)

    ready = commands.add_parser("validate-ready")
    common(ready)
    ready.set_defaults(func=command_validate_ready)

    acknowledge = commands.add_parser("acknowledge-ready")
    common(acknowledge)
    acknowledge.add_argument("--run-id", required=True)
    acknowledge.add_argument("--shard-index", required=True, type=int)
    acknowledge.set_defaults(func=command_acknowledge_ready)

    acknowledgement_status = commands.add_parser(
        "acknowledgement-status"
    )
    common(acknowledgement_status)
    acknowledgement_status.set_defaults(
        func=command_acknowledgement_status
    )
    return result


def main() -> int:
    args = parser().parse_args()
    if args.shard_count <= 0:
        raise SystemExit("shard-count must be positive")
    if hasattr(args, "shard_index") and not (
        0 <= args.shard_index < args.shard_count
    ):
        raise SystemExit("shard-index is outside shard-count")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
