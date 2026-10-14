                      
"""Prepare portable Stage-1 transfer indexes, file lists, and checksums."""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("./xonotic_capture")
DEFAULT_INPUT_MANIFEST = (
    ROOT
    / "manifests/stage1_foundation_v5_accepted_postfiltered_r1_20260730"
    / "accepted_filtered.jsonl"
)
DEFAULT_DESTINATION = (
    ROOT
    / "manifests/stage1_foundation_v5_transfer_bundle_r2_20260730"
)
DEFAULT_SHARD_COUNT = 32
DEFAULT_WORKERS = 32
EPISODE_SECONDS = 5

REQUIRED_EPISODE_FILES = {
    "episode.json",
    "video.mkv",
    "actions.parquet",
    "model_actions.parquet",
    "states.parquet",
    "events.parquet",
    "frames.parquet",
    "audio_events.parquet",
    "target_relations.parquet",
    "qa.json",
}
REQUIRED_ROUTE_FILES = {
    "route_plan.json",
    "route_trace.parquet",
    "base_actions.parquet",
    "aim_overlay.parquet",
}
PORTABLE_INDEX_HASH_FILES = (
    "video.mkv",
    "model_actions.parquet",
    "frames.parquet",
    "episode.json",
    "qa.json",
)
METADATA_RELATIVE_PATHS = (
    "XONOTIC_DATA_SPEC_V2.md",
    "LTX2_ACTION_ALIGNMENT_REPORT.md",
    "WAYPOINT_HUD_FIX_REPORT.md",
    "STAGE1_COLLISION_CERTIFICATION_REPORT.md",
    "STAGE1_MENU_OVERLAY_FIX_REPORT.md",
    "STAGE1_V4_RELOAD_AND_RANDOM100_REPORT.md",
    "STAGE1_V5_56X1_PRODUCTION_REPORT.md",
    "STAGE1_RECOVERY_REBALANCE_R6_REPORT.md",
    (
        "manifests/"
        "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
        "accepted_filtered.jsonl"
    ),
    (
        "manifests/"
        "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
        "accepted_episode_ids.txt"
    ),
    (
        "manifests/"
        "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
        "excluded.jsonl"
    ),
    (
        "manifests/"
        "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
        "excluded_episode_ids.txt"
    ),
    (
        "manifests/"
        "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
        "FILTER_REPORT.json"
    ),
    (
        "manifests/"
        "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
        "README.md"
    ),
    (
        "manifests/"
        "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
        "SHA256SUMS"
    ),
    "scripts/build_stage1_postfilter_manifest.py",
    "scripts/run_stage1_postfilter_manifest.sh",
    "scripts/prepare_stage1_transfer_bundle.py",
    "scripts/transfer_stage1_bundle.sh",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stream_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"{path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise RuntimeError(
                    f"{path}:{line_number}: expected object"
                )
            yield value


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(
            f"path is outside source root: {path}"
        ) from exc


def episode_shard(episode_id: str, shard_count: int) -> int:
    digest = hashlib.sha256(episode_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % shard_count


def human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def compact_episode(
    row: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    episode_id = str(row["episode_id"])
    screening = row.get("post_collection_screening") or {}
    if screening.get("decision") != "keep":
        raise RuntimeError(
            f"{episode_id}: input manifest contains non-kept record"
        )
    episode_path = Path(str(row["episode_path"]))
    episode_relpath = relative_to_root(episode_path, root)
    expected_prefix = (
        "stage1_foundation_v5_output_56x1_menu_clean_r3/candidates/"
    )
    if episode_relpath != expected_prefix + episode_id:
        raise RuntimeError(
            f"{episode_id}: unexpected relative package path "
            f"{episode_relpath}"
        )
    hashes = row.get("package_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise RuntimeError(f"{episode_id}: package hash map missing")
    missing = REQUIRED_EPISODE_FILES - hashes.keys()
    if missing:
        raise RuntimeError(
            f"{episode_id}: required files missing from package hash: "
            + ", ".join(sorted(missing))
        )
    route = "route_plan.json" in hashes
    if route and not REQUIRED_ROUTE_FILES <= hashes.keys():
        raise RuntimeError(
            f"{episode_id}: incomplete route artifact set"
        )
    for relative, digest in hashes.items():
        if (
            not isinstance(relative, str)
            or relative.startswith("/")
            or ".." in Path(relative).parts
        ):
            raise RuntimeError(
                f"{episode_id}: unsafe package path {relative!r}"
            )
        if not isinstance(digest, str) or len(digest) != 64:
            raise RuntimeError(
                f"{episode_id}: invalid SHA-256 for {relative}"
            )
    published_bytes = int(
        (row.get("publication") or {}).get("package_bytes") or 0
    )
    if published_bytes <= 0:
        raise RuntimeError(
            f"{episode_id}: invalid published package byte count"
        )
    certificate = row.get("player_path_certificate") or {}
    certificate_hashes: dict[str, str] = {}
    for path_key, hash_key in (
        ("actions_path", "actions_sha256"),
        ("certificate_path", "certificate_sha256"),
        ("states_path", "states_sha256"),
    ):
        relative = certificate.get(path_key)
        digest = certificate.get(hash_key)
        if not isinstance(relative, str) or not relative:
            raise RuntimeError(
                f"{episode_id}: missing certificate {path_key}"
            )
        if (
            relative.startswith("/")
            or ".." in Path(relative).parts
            or not relative.startswith(
                "stage1_path_certification_v5/certificates/"
            )
        ):
            raise RuntimeError(
                f"{episode_id}: unsafe certificate path {relative}"
            )
        if not isinstance(digest, str) or len(digest) != 64:
            raise RuntimeError(
                f"{episode_id}: invalid certificate hash {hash_key}"
            )
        certificate_hashes[relative] = digest

    return {
        "episode_id": episode_id,
        "episode_relpath": episode_relpath,
        "package_sha256": hashes,
        "published_package_bytes": published_bytes,
        "dataset_role": row.get("dataset_role"),
        "split": row.get("split"),
        "map": row.get("map"),
        "gametype": row.get("gametype"),
        "weapon": row.get("weapon"),
        "enemy_present": bool(row.get("enemy_present")),
        "source_prototype_id": row.get("source_prototype_id"),
        "route": route,
        "screening_ruleset_sha256": screening.get("ruleset_sha256"),
        "certificate_sha256": certificate_hashes,
    }


def inspect_episode(
    episode: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    core: list[tuple[str, str, int, str]] = []
    provenance: list[tuple[str, str, int, str]] = []
    package_bytes = 0
    episode_prefix = str(episode["episode_relpath"])
    for package_relative, digest in sorted(
        episode["package_sha256"].items()
    ):
        relative = f"{episode_prefix}/{package_relative}"
        absolute = root / relative
        try:
            size = absolute.stat().st_size
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"{episode['episode_id']}: missing package file {relative}"
            ) from exc
        package_bytes += size
        entry = (relative, digest, size, package_relative)
        if package_relative.startswith("capture_provenance/"):
            provenance.append(entry)
        else:
            core.append(entry)
    if package_bytes != episode["published_package_bytes"]:
        raise RuntimeError(
            f"{episode['episode_id']}: published byte mismatch "
            f"{package_bytes} != {episode['published_package_bytes']}"
        )
    return {
        "episode": episode,
        "core": core,
        "provenance": provenance,
        "core_bytes": sum(value[2] for value in core),
        "provenance_bytes": sum(
            value[2] for value in provenance
        ),
    }


def metadata_entries(
    root: Path,
) -> list[tuple[str, str, int]]:
    result: list[tuple[str, str, int]] = []
    for relative in METADATA_RELATIVE_PATHS:
        absolute = root / relative
        if not absolute.is_file():
            raise RuntimeError(f"metadata file missing: {absolute}")
        result.append(
            (relative, sha256_file(absolute), absolute.stat().st_size)
        )
    return result


def open_shards(
    root: Path,
    profile: str,
    shard_count: int,
) -> list[Any]:
    directory = root / "shards" / profile
    directory.mkdir(parents=True)
    return [
        (
            directory
            / f"shard-{index:03d}-of-{shard_count:03d}.txt"
        ).open("x", encoding="utf-8")
        for index in range(shard_count)
    ]


def close_handles(handles: Iterable[Any]) -> None:
    for handle in handles:
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()


def report_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    sizes = report["sizes"]
    paths = report["paths"]
    return f"""# Stage-1 transfer bundle

Created: `{report["created_utc"]}`

This bundle covers only the `{counts["episodes"]}` kept Stage-1 episodes in
the post-filter manifest. It excludes unfinished, hard-rejected,
post-filter-excluded, and all Stage-2 episodes.

## Recommended transfer

Transfer the `core` profile first:

- episodes: **{counts["episodes"]}**
- duration: **{report["duration"]["hours"]:.4f} hours**
- episode files: **{counts["core_episode_files"]}**
- path-certificate files: **{counts["certificate_files"]}**
- metadata files: **{counts["metadata_files"]}**
- bytes: **{sizes["core_with_metadata_human"]}**

`core` includes every data-spec episode artifact, embedded FLAC audio,
frame-aligned LTX-2 actions, camera/frame-tick truth, state/event/target
truth, QA, route extras, referenced player-path certificates, and dataset
metadata.

The optional `provenance` profile adds **{sizes["provenance_human"]}** of
engine demos, requested/applied CSV logs, and console/encoder logs. It is not
read by the default trainer.

## Portable paths

`TRANSFER_INDEX.jsonl` uses paths relative to the transfer root. Do not use
the source machine's absolute `episode_path` field after moving the data.

Source episode prefix:

`{paths["episode_prefix"]}`

## Transfer command

For a mounted/local destination:

```bash
cd {ROOT}
./scripts/transfer_stage1_bundle.sh \\
  {ROOT} /path/to/destination core 8
```

Use profile `full` to transfer core plus provenance. The 32 deterministic
episode shards are independently resumable. The script never deletes
destination files.

## Destination checksum verification

Core:

```bash
gzip -dc {paths["bundle_relpath"]}/core_sha256sums.txt.gz | \\
  (cd /path/to/destination && sha256sum -c -)
```

Provenance, if transferred:

```bash
gzip -dc {paths["bundle_relpath"]}/provenance_sha256sums.txt.gz | \\
  (cd /path/to/destination && sha256sum -c -)
```

Checking every media SHA-256 reads the full dataset. The transfer script uses
rsync's size/mtime checks for resume; run the checksum command when end-to-end
content verification is required.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
    )
    parser.add_argument(
        "--input-manifest",
        default=str(DEFAULT_INPUT_MANIFEST),
    )
    parser.add_argument(
        "--destination",
        default=str(DEFAULT_DESTINATION),
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        default=DEFAULT_SHARD_COUNT,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
    )
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    input_manifest = Path(args.input_manifest).resolve()
    destination = Path(args.destination).resolve()
    if args.shard_count <= 0 or args.workers <= 0:
        raise RuntimeError("shard count and workers must be positive")
    if destination.exists():
        raise RuntimeError(f"destination exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.tmp.{os.getpid()}"
    )
    if temporary.exists():
        raise RuntimeError(f"temporary path exists: {temporary}")
    temporary.mkdir()

    try:
        print(f"loading {input_manifest}", flush=True)
        episodes: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in stream_jsonl(input_manifest):
            episode = compact_episode(row, source_root)
            episode_id = str(episode["episode_id"])
            if episode_id in seen:
                raise RuntimeError(
                    f"duplicate input episode: {episode_id}"
                )
            seen.add(episode_id)
            episodes.append(episode)
        episodes.sort(key=lambda value: value["episode_id"])
        if len(episodes) != 51_436:
            raise RuntimeError(
                f"unexpected kept episode count: {len(episodes)}"
            )

        print("hashing transfer metadata", flush=True)
        metadata = metadata_entries(source_root)
        certificate_hashes: dict[str, str] = {}
        for episode in episodes:
            for relative, digest in episode[
                "certificate_sha256"
            ].items():
                previous = certificate_hashes.setdefault(
                    relative,
                    digest,
                )
                if previous != digest:
                    raise RuntimeError(
                        f"certificate hash conflict: {relative}"
                    )
        certificate_entries: list[tuple[str, str, int]] = []
        for relative, digest in sorted(certificate_hashes.items()):
            absolute = source_root / relative
            if not absolute.is_file():
                raise RuntimeError(
                    f"certificate file missing: {absolute}"
                )
            certificate_entries.append(
                (relative, digest, absolute.stat().st_size)
            )
        metadata_file = (
            temporary / "metadata_files.txt"
        ).open("x", encoding="utf-8")
        certificate_file = (
            temporary / "certificate_files.txt"
        ).open("x", encoding="utf-8")
        core_checksums = gzip.open(
            temporary / "core_sha256sums.txt.gz",
            "wt",
            encoding="utf-8",
            compresslevel=6,
        )
        provenance_checksums = gzip.open(
            temporary / "provenance_sha256sums.txt.gz",
            "wt",
            encoding="utf-8",
            compresslevel=6,
        )
        for relative, digest, _ in metadata:
            metadata_file.write(relative + "\n")
            core_checksums.write(f"{digest}  {relative}\n")
        metadata_file.flush()
        os.fsync(metadata_file.fileno())
        metadata_file.close()
        for relative, digest, _ in certificate_entries:
            certificate_file.write(relative + "\n")
            core_checksums.write(f"{digest}  {relative}\n")
        certificate_file.flush()
        os.fsync(certificate_file.fileno())
        certificate_file.close()

        core_shards = open_shards(
            temporary,
            "core",
            args.shard_count,
        )
        provenance_shards = open_shards(
            temporary,
            "provenance",
            args.shard_count,
        )
        index_handle = (
            temporary / "TRANSFER_INDEX.jsonl"
        ).open("x", encoding="utf-8")

        core_bytes = 0
        provenance_bytes = 0
        core_files = 0
        provenance_files = 0
        route_episodes = 0
        artifact_counts: Counter[str] = Counter()
        artifact_bytes: Counter[str] = Counter()
        shard_counts: dict[str, Counter[int]] = {
            "core": Counter(),
            "provenance": Counter(),
        }
        shard_bytes: dict[str, Counter[int]] = {
            "core": Counter(),
            "provenance": Counter(),
        }
        distributions: dict[str, Counter[str]] = defaultdict(Counter)

        print(
            f"inspecting {len(episodes)} packages "
            f"with workers={args.workers}",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.workers
        ) as executor:
            inspected = executor.map(
                lambda value: inspect_episode(value, source_root),
                episodes,
            )
            for ordinal, result in enumerate(inspected, 1):
                episode = result["episode"]
                episode_id = str(episode["episode_id"])
                shard = episode_shard(
                    episode_id,
                    args.shard_count,
                )
                route_episodes += int(episode["route"])
                for field in (
                    "dataset_role",
                    "split",
                    "map",
                    "gametype",
                    "weapon",
                    "enemy_present",
                ):
                    distributions[field][
                        str(episode.get(field))
                    ] += 1

                for (
                    relative,
                    digest,
                    size,
                    package_relative,
                ) in result["core"]:
                    core_shards[shard].write(relative + "\n")
                    core_checksums.write(
                        f"{digest}  {relative}\n"
                    )
                    core_files += 1
                    core_bytes += size
                    shard_counts["core"][shard] += 1
                    shard_bytes["core"][shard] += size
                    artifact_counts[package_relative] += 1
                    artifact_bytes[package_relative] += size

                for (
                    relative,
                    digest,
                    size,
                    package_relative,
                ) in result["provenance"]:
                    provenance_shards[shard].write(relative + "\n")
                    provenance_checksums.write(
                        f"{digest}  {relative}\n"
                    )
                    provenance_files += 1
                    provenance_bytes += size
                    shard_counts["provenance"][shard] += 1
                    shard_bytes["provenance"][shard] += size
                    artifact_counts[package_relative] += 1
                    artifact_bytes[package_relative] += size

                prefix = str(episode["episode_relpath"])
                hashes = episode["package_sha256"]
                index_row = {
                    "schema_version": (
                        "xonotic-stage1-portable-transfer-index-v1"
                    ),
                    "episode_id": episode_id,
                    "episode_relpath": prefix,
                    "duration_seconds": EPISODE_SECONDS,
                    "video_relpath": f"{prefix}/video.mkv",
                    "model_actions_relpath": (
                        f"{prefix}/model_actions.parquet"
                    ),
                    "frames_relpath": f"{prefix}/frames.parquet",
                    "episode_metadata_relpath": (
                        f"{prefix}/episode.json"
                    ),
                    "qa_relpath": f"{prefix}/qa.json",
                    "core_file_count": len(result["core"]),
                    "core_bytes": result["core_bytes"],
                    "provenance_file_count": len(
                        result["provenance"]
                    ),
                    "provenance_bytes": result[
                        "provenance_bytes"
                    ],
                    "transfer_shard": shard,
                    "dataset_role": episode["dataset_role"],
                    "split": episode["split"],
                    "map": episode["map"],
                    "gametype": episode["gametype"],
                    "weapon": episode["weapon"],
                    "enemy_present": episode["enemy_present"],
                    "source_prototype_id": episode[
                        "source_prototype_id"
                    ],
                    "route_episode": episode["route"],
                    "screening_ruleset_sha256": episode[
                        "screening_ruleset_sha256"
                    ],
                    "player_path_certificate_sha256": episode[
                        "certificate_sha256"
                    ],
                    "training_artifact_sha256": {
                        name: hashes[name]
                        for name in PORTABLE_INDEX_HASH_FILES
                    },
                }
                index_handle.write(canonical_json(index_row) + "\n")

                if ordinal % 2_000 == 0:
                    print(
                        f"packages inspected={ordinal}/"
                        f"{len(episodes)}",
                        flush=True,
                    )

        close_handles(core_shards)
        close_handles(provenance_shards)
        core_checksums.close()
        provenance_checksums.close()
        index_handle.flush()
        os.fsync(index_handle.fileno())
        index_handle.close()

        metadata_bytes = sum(value[2] for value in metadata)
        certificate_bytes = sum(
            value[2] for value in certificate_entries
        )
        total_package_bytes = core_bytes + provenance_bytes
        published_package_bytes = sum(
            int(value["published_package_bytes"])
            for value in episodes
        )
        if total_package_bytes != published_package_bytes:
            raise RuntimeError(
                "global published package byte mismatch: "
                f"{total_package_bytes} != {published_package_bytes}"
            )
        if core_files != 736_112:
            raise RuntimeError(
                f"unexpected core episode file count: {core_files}"
            )
        if provenance_files != 514_360:
            raise RuntimeError(
                "unexpected provenance file count: "
                f"{provenance_files}"
            )
        if route_episodes != 16_861:
            raise RuntimeError(
                f"unexpected route episode count: {route_episodes}"
            )

        shard_report = {}
        for profile in ("core", "provenance"):
            shard_report[profile] = [
                {
                    "shard_index": index,
                    "files": shard_counts[profile][index],
                    "bytes": shard_bytes[profile][index],
                    "bytes_human": human_bytes(
                        shard_bytes[profile][index]
                    ),
                }
                for index in range(args.shard_count)
            ]
        bundle_relpath = relative_to_root(
            destination,
            source_root,
        )
        report = {
            "schema_version": "xonotic-stage1-transfer-bundle-v1",
            "created_utc": utc_now(),
            "source_root": str(source_root),
            "input_manifest": str(input_manifest),
            "input_manifest_sha256": sha256_file(input_manifest),
            "profile_contract": {
                "core": (
                    "all published package files except "
                    "capture_provenance/, referenced player-path "
                    "certificates, plus Stage-1 metadata"
                ),
                "provenance": (
                    "capture_provenance/ engine demos, CSVs, and logs"
                ),
                "full": "core plus provenance",
            },
            "counts": {
                "episodes": len(episodes),
                "route_episodes": route_episodes,
                "core_episode_files": core_files,
                "certificate_files": len(certificate_entries),
                "provenance_files": provenance_files,
                "metadata_files": len(metadata),
                "full_episode_files": (
                    core_files + provenance_files
                ),
                "unfinished_ignored": 773,
                "postfilter_excluded_ignored": 5_316,
            },
            "duration": {
                "seconds": len(episodes) * EPISODE_SECONDS,
                "hours": (
                    len(episodes) * EPISODE_SECONDS / 3600
                ),
            },
            "sizes": {
                "core_episode_bytes": core_bytes,
                "certificate_bytes": certificate_bytes,
                "metadata_bytes": metadata_bytes,
                "core_with_metadata_bytes": (
                    core_bytes + certificate_bytes + metadata_bytes
                ),
                "provenance_bytes": provenance_bytes,
                "full_with_metadata_bytes": (
                    core_bytes
                    + certificate_bytes
                    + provenance_bytes
                    + metadata_bytes
                ),
                "core_episode_human": human_bytes(core_bytes),
                "certificate_human": human_bytes(
                    certificate_bytes
                ),
                "metadata_human": human_bytes(metadata_bytes),
                "core_with_metadata_human": human_bytes(
                    core_bytes + certificate_bytes + metadata_bytes
                ),
                "provenance_human": human_bytes(provenance_bytes),
                "full_with_metadata_human": human_bytes(
                    core_bytes
                    + certificate_bytes
                    + provenance_bytes
                    + metadata_bytes
                ),
            },
            "paths": {
                "bundle_relpath": bundle_relpath,
                "episode_prefix": (
                    "stage1_foundation_v5_output_56x1_menu_clean_r3/"
                    "candidates/"
                ),
                "portable_index": "TRANSFER_INDEX.jsonl",
                "metadata_files": "metadata_files.txt",
                "certificate_files": "certificate_files.txt",
                "core_shards": "shards/core/",
                "provenance_shards": "shards/provenance/",
                "core_checksums": "core_sha256sums.txt.gz",
                "provenance_checksums": (
                    "provenance_sha256sums.txt.gz"
                ),
            },
            "shard_count": args.shard_count,
            "shards": shard_report,
            "artifact_counts": dict(sorted(artifact_counts.items())),
            "artifact_bytes": dict(sorted(artifact_bytes.items())),
            "artifact_bytes_human": {
                name: human_bytes(value)
                for name, value in sorted(artifact_bytes.items())
            },
            "distribution": {
                field: dict(
                    sorted(
                        values.items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                )
                for field, values in distributions.items()
            },
            "integrity": {
                "unique_episode_ids": (
                    len(episodes) == len(seen)
                ),
                "all_input_decisions_keep": True,
                "all_spec_required_files_present": True,
                "all_referenced_certificates_present": True,
                "unique_referenced_certificates": len(
                    certificate_entries
                ),
                "all_published_file_sizes_match": True,
                "stage2_episode_paths": 0,
                "source_files_hashed_by_publication": (
                    core_files + provenance_files
                ),
            },
        }
        (temporary / "TRANSFER_REPORT.json").write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (temporary / "README.md").write_text(
            report_markdown(report),
            encoding="utf-8",
        )

        control_files = sorted(
            path.relative_to(temporary).as_posix()
            for path in temporary.rglob("*")
            if path.is_file()
            and path.name != "CONTROL_SHA256SUMS"
        )
        (temporary / "CONTROL_SHA256SUMS").write_text(
            "".join(
                f"{sha256_file(temporary / relative)}  {relative}\n"
                for relative in control_files
            ),
            encoding="utf-8",
        )
        os.rename(temporary, destination)
        print(f"destination={destination}", flush=True)
        print(
            "core_with_metadata="
            f"{human_bytes(core_bytes + certificate_bytes + metadata_bytes)}",
            flush=True,
        )
        print(
            f"provenance={human_bytes(provenance_bytes)}",
            flush=True,
        )
        print(
            "full_with_metadata="
            f"{human_bytes(core_bytes + certificate_bytes + provenance_bytes + metadata_bytes)}",
            flush=True,
        )
        return 0
    except BaseException:
        if temporary.is_dir():
            shutil.rmtree(temporary)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
