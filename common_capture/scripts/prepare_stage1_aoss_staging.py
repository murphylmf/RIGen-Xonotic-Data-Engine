                      
"""Materialize the exact Stage-1 full archive as a hard-link staging tree."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BUNDLE_RELATIVE = Path(
    "manifests/stage1_foundation_v5_transfer_bundle_r2_20260730"
)
EXTRA_ARCHIVE_FILES = (
    "STAGE1_AOSS_FULL_ARCHIVE_RUNBOOK.md",
    "scripts/prepare_stage1_aoss_staging.py",
    "scripts/upload_stage1_full_archive_to_aoss.sh",
    "scripts/launch_stage1_full_archive_aoss_tmux.sh",
)
TARGET_PREFIX = "limengfei/xonotic_data/"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def safe_relative(value: str) -> str:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "stage2" in value.lower()
    ):
        raise RuntimeError(f"unsafe/non-Stage-1 archive path: {value!r}")
    return path.as_posix()


def verify_control_bundle(bundle: Path) -> None:
    checksum_path = bundle / "CONTROL_SHA256SUMS"
    seen: set[str] = set()
    with checksum_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            digest, separator, relative = line.rstrip("\n").partition("  ")
            if (
                not separator
                or len(digest) != 64
                or relative in seen
            ):
                raise RuntimeError(
                    f"invalid control checksum line {line_number}"
                )
            seen.add(relative)
            path = bundle / safe_relative(relative)
            if not path.is_file():
                raise RuntimeError(f"bundle control file missing: {path}")
            if sha256_file(path) != digest:
                raise RuntimeError(
                    f"bundle control checksum mismatch: {relative}"
                )


def list_files(bundle: Path) -> list[Path]:
    result = [
        bundle / "metadata_files.txt",
        bundle / "certificate_files.txt",
    ]
    result.extend(sorted((bundle / "shards/core").glob("shard-*.txt")))
    result.extend(
        sorted((bundle / "shards/provenance").glob("shard-*.txt"))
    )
    if len(result) != 66:
        raise RuntimeError(
            f"expected 66 transfer lists, observed {len(result)}"
        )
    return result


def stream_list(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            value = line.rstrip("\n")
            if not value:
                raise RuntimeError(f"blank path: {path}:{line_number}")
            yield safe_relative(value)


def bundle_relative_files(
    source_root: Path,
    bundle: Path,
) -> list[str]:
    return [
        path.relative_to(source_root).as_posix()
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    ]


class Progress:
    def __init__(self, expected: int) -> None:
        self.expected = expected
        self.count = 0
        self.bytes = 0
        self.created = 0
        self.reused = 0
        self.lock = threading.Lock()

    def add(self, size: int, created: bool) -> None:
        with self.lock:
            self.count += 1
            self.bytes += size
            self.created += int(created)
            self.reused += int(not created)
            if self.count % 25_000 == 0:
                print(
                    f"staged={self.count}/{self.expected} "
                    f"created={self.created} reused={self.reused}",
                    flush=True,
                )


def ensure_hardlink(
    source: Path,
    destination: Path,
) -> bool:
    if not source.is_file():
        raise RuntimeError(f"archive source file missing: {source}")
    try:
        os.link(source, destination)
        return True
    except FileExistsError:
        if not destination.is_file():
            raise RuntimeError(
                f"staging path exists and is not a file: {destination}"
            )
        if not os.path.samefile(source, destination):
            raise RuntimeError(
                "staging path is not the expected hard link: "
                f"{destination}"
            )
        return False


def stage_values(
    values: Iterable[str],
    source_root: Path,
    staging_root: Path,
    progress: Progress,
) -> tuple[int, int]:
    count = 0
    total_bytes = 0
    last_parent: Path | None = None
    for relative in values:
        source = source_root / relative
        destination = staging_root / relative
        if destination.parent != last_parent:
            destination.parent.mkdir(parents=True, exist_ok=True)
            last_parent = destination.parent
        created = ensure_hardlink(source, destination)
        size = source.stat().st_size
        count += 1
        total_bytes += size
        progress.add(size, created)
    return count, total_bytes


def stage_list(
    list_path: Path,
    source_root: Path,
    staging_root: Path,
    progress: Progress,
) -> tuple[int, int]:
    return stage_values(
        stream_list(list_path),
        source_root,
        staging_root,
        progress,
    )


def write_ready_marker(
    path: Path,
    value: dict[str, Any],
) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--staging-root", required=True)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    staging_root = Path(args.staging_root).resolve()
    bundle = source_root / BUNDLE_RELATIVE
    if args.workers <= 0:
        raise RuntimeError("workers must be positive")
    if not bundle.is_dir():
        raise RuntimeError(f"transfer bundle missing: {bundle}")
    report = load_json(bundle / "TRANSFER_REPORT.json")
    counts = report["counts"]
    sizes = report["sizes"]
    expected_listed_files = (
        int(counts["core_episode_files"])
        + int(counts["provenance_files"])
        + int(counts["certificate_files"])
        + int(counts["metadata_files"])
    )
    if expected_listed_files != 1_266_640:
        raise RuntimeError(
            f"unexpected listed file count: {expected_listed_files}"
        )

    print("verifying transfer control bundle", flush=True)
    verify_control_bundle(bundle)
    bundle_files = bundle_relative_files(source_root, bundle)
    extra_files = [safe_relative(value) for value in EXTRA_ARCHIVE_FILES]
    for relative in extra_files:
        if not (source_root / relative).is_file():
            raise RuntimeError(f"archive helper missing: {relative}")
    expected_hardlinks = (
        expected_listed_files + len(bundle_files) + len(extra_files)
    )
    bundle_bytes = sum(
        (source_root / relative).stat().st_size
        for relative in bundle_files
    )
    extra_bytes = sum(
        (source_root / relative).stat().st_size
        for relative in extra_files
    )
    expected_hardlink_bytes = (
        int(sizes["full_with_metadata_bytes"])
        + bundle_bytes
        + extra_bytes
    )
    plan = {
        "schema_version": "xonotic-stage1-aoss-archive-plan-v1",
        "created_utc": utc_now(),
        "source_root": str(source_root),
        "staging_root": str(staging_root),
        "target_prefix": TARGET_PREFIX,
        "episodes": int(counts["episodes"]),
        "duration_hours": float(report["duration"]["hours"]),
        "listed_dataset_files": expected_listed_files,
        "transfer_bundle_files": len(bundle_files),
        "helper_script_files": len(extra_files),
        "expected_hardlinks": expected_hardlinks,
        "dataset_and_metadata_bytes": int(
            sizes["full_with_metadata_bytes"]
        ),
        "transfer_bundle_bytes": bundle_bytes,
        "helper_script_bytes": extra_bytes,
        "expected_hardlink_bytes": expected_hardlink_bytes,
        "input_manifest_sha256": report["input_manifest_sha256"],
        "transfer_control_sha256": sha256_file(
            bundle / "CONTROL_SHA256SUMS"
        ),
        "method": "hardlinks_same_filesystem_no_data_block_copy",
        "excluded": {
            "stage2": True,
            "postfilter_excluded": int(
                counts["postfilter_excluded_ignored"]
            ),
            "unfinished": int(counts["unfinished_ignored"]),
        },
    }
    print(json.dumps(plan, indent=2, sort_keys=True), flush=True)
    if args.plan_only:
        return 0

    staging_root.parent.mkdir(parents=True, exist_ok=True)
    if source_root.stat().st_dev != staging_root.parent.stat().st_dev:
        raise RuntimeError(
            "source and staging parent are on different filesystems; "
            "hard-link staging is unavailable"
        )
    staging_root.mkdir(exist_ok=True)
    probe_source = bundle / "TRANSFER_REPORT.json"
    probe_destination = staging_root / ".hardlink_probe"
    try:
        created = ensure_hardlink(probe_source, probe_destination)
        if not os.path.samefile(probe_source, probe_destination):
            raise RuntimeError("hard-link probe failed")
    finally:
        if probe_destination.exists():
            probe_destination.unlink()
    print(f"hard-link probe passed created={created}", flush=True)

    lists = list_files(bundle)
    progress = Progress(expected_hardlinks)
    results: list[tuple[int, int]] = []
    print(
        f"materializing staging with workers={args.workers}",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(args.workers, len(lists) + 2)
    ) as executor:
        futures = [
            executor.submit(
                stage_list,
                list_path,
                source_root,
                staging_root,
                progress,
            )
            for list_path in lists
        ]
        futures.append(
            executor.submit(
                stage_values,
                bundle_files,
                source_root,
                staging_root,
                progress,
            )
        )
        futures.append(
            executor.submit(
                stage_values,
                extra_files,
                source_root,
                staging_root,
                progress,
            )
        )
        for future in futures:
            results.append(future.result())

    observed_count = sum(value[0] for value in results)
    observed_bytes = sum(value[1] for value in results)
    if observed_count != expected_hardlinks:
        raise RuntimeError(
            f"staging count mismatch: {observed_count} "
            f"!= {expected_hardlinks}"
        )
    if observed_bytes != expected_hardlink_bytes:
        raise RuntimeError(
            f"staging byte mismatch: {observed_bytes} "
            f"!= {expected_hardlink_bytes}"
        )
    ready = {
        **plan,
        "status": "ready",
        "ready_utc": utc_now(),
        "observed_hardlinks": observed_count,
        "observed_hardlink_bytes": observed_bytes,
        "hardlinks_created_this_run": progress.created,
        "hardlinks_reused_this_run": progress.reused,
        "upload_source": str(staging_root) + "/",
    }
    write_ready_marker(
        staging_root / "AOSS_UPLOAD_READY.json",
        ready,
    )
    print(
        f"READY staging={staging_root} "
        f"files={observed_count + 1}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
