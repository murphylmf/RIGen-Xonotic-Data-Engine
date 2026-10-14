                      
"""Freeze a partial long60 collection into an immutable accepted-set snapshot.

The renderer may still be retrying rejected tail episodes while this script
runs.  The accepted status filenames are therefore enumerated once at startup;
only that exact set is eligible for the snapshot.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )


def distribution(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = collections.Counter(str(row.get(key)) for row in rows)
    return dict(sorted(counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-accepted", type=int, required=True)
    parser.add_argument("--expected-total", type=int, required=True)
    args = parser.parse_args()

    collection = args.collection_root.resolve()
    manifest_path = args.manifest.resolve()
    status_root = collection / "status"

                                                                            
    accepted_files = tuple(sorted((status_root / "accepted").glob("*.json")))
    if len(accepted_files) != args.expected_accepted:
        raise ValueError(
            f"expected {args.expected_accepted} accepted status files at freeze boundary, "
            f"found {len(accepted_files)}"
        )

    manifest_rows = read_jsonl(manifest_path)
    if len(manifest_rows) != args.expected_total:
        raise ValueError(f"expected {args.expected_total} manifest rows, found {len(manifest_rows)}")
    manifest_by_id = {str(row["episode_id"]): row for row in manifest_rows}
    if len(manifest_by_id) != len(manifest_rows):
        raise ValueError("duplicate episode_id in source manifest")

    accepted_rows: list[dict[str, Any]] = []
    qa_hashes: dict[str, str] = {}
    for status_path in accepted_files:
        record = read_json(status_path)
        episode_id = str(record.get("episode_id"))
        source = manifest_by_id.get(episode_id)
        if source is None:
            raise ValueError(f"{status_path}: episode absent from source manifest")
        for key in (
            "release_id",
            "manifest_index",
            "split",
            "map",
            "weapon",
            "template",
            "scenario_sha256",
            "timeline_sha256",
            "actions_sha256",
        ):
            if record.get(key) != source.get(key):
                raise ValueError(f"{episode_id}: accepted/source mismatch for {key}")

        video_path = Path(str(record["video_path"]))
        qa_path = Path(str(record["qa_path"]))
        if not video_path.is_file() or not qa_path.is_file():
            raise ValueError(f"{episode_id}: missing video or QA artifact")
        if video_path.stat().st_size != int(record["video_size_bytes"]):
            raise ValueError(f"{episode_id}: video size differs from accepted record")
        if int(record.get("video_frames", -1)) != 1201:
            raise ValueError(f"{episode_id}: expected 1201 training video frames")
        if bool(record.get("raw_avi_retained", True)):
            raise ValueError(f"{episode_id}: raw AVI unexpectedly retained")

        qa = read_json(qa_path)
        if str(qa.get("episode_id")) != episode_id:
            raise ValueError(f"{episode_id}: QA episode id mismatch")
        failed_checks = [name for name, passed in (qa.get("checks") or {}).items() if passed is not True]
        if failed_checks:
            raise ValueError(f"{episode_id}: accepted QA has failed checks: {failed_checks}")
        qa_hashes[episode_id] = sha256_file(qa_path)
        accepted_rows.append(record)

    accepted_rows.sort(key=lambda row: int(row["manifest_index"]))
    accepted_ids = [str(row["episode_id"]) for row in accepted_rows]
    accepted_indices = [int(row["manifest_index"]) for row in accepted_rows]
    if len(set(accepted_ids)) != len(accepted_ids) or len(set(accepted_indices)) != len(accepted_indices):
        raise ValueError("duplicate accepted episode id or manifest index")

    missing_rows = [row for row in manifest_rows if str(row["episode_id"]) not in set(accepted_ids)]
    if len(missing_rows) != args.expected_total - args.expected_accepted:
        raise ValueError("accepted/missing partition does not cover source manifest exactly")

    rejected_history: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for path in sorted((status_root / "rejected").glob("*.json")):
        row = read_json(path)
        rejected_history[str(row.get("episode_id"))].append(
            {
                "attempt": row.get("attempt"),
                "created_utc": row.get("created_utc"),
                "failed_checks": list(row.get("failed_checks") or []),
                "status_path": str(path),
                "status_sha256": sha256_file(path),
            }
        )

    frozen_manifest = collection / "FROZEN_ACCEPTED.jsonl"
    frozen_payload = jsonl_bytes(accepted_rows)
    frozen_sha = hashlib.sha256(frozen_payload).hexdigest()
    atomic_write(frozen_manifest, frozen_payload)

    excluded = []
    for row in sorted(missing_rows, key=lambda item: int(item["manifest_index"])):
        episode_id = str(row["episode_id"])
        excluded.append(
            {
                "episode_id": episode_id,
                "manifest_index": int(row["manifest_index"]),
                "split": row["split"],
                "map": row["map"],
                "weapon": row["weapon"],
                "template": row["template"],
                "kill_count": int(row["kill_count"]),
                "rejected_history": rejected_history.get(episode_id, []),
            }
        )

    release_ids = sorted({str(row["release_id"]) for row in accepted_rows})
    if len(release_ids) != 1:
        raise ValueError(f"accepted set spans multiple release ids: {release_ids}")
    video_bytes = sum(int(row["video_size_bytes"]) for row in accepted_rows)
    report = {
        "schema_version": "xonotic-stage2-long60-frozen-partial-collection-v1",
        "frozen": True,
        "complete": True,
        "completion_scope": "frozen_accepted_set_only",
        "partial_from_original_budget": len(excluded) > 0,
        "training_admitted": False,
        "frozen_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_release_id": release_ids[0],
        "collection_root": str(collection),
        "source_manifest": str(manifest_path),
        "source_manifest_rows": len(manifest_rows),
        "source_manifest_sha256": sha256_file(manifest_path),
        "accepted_snapshot": frozen_manifest.name,
        "accepted_snapshot_sha256": frozen_sha,
        "accepted_count": len(accepted_rows),
        "excluded_count": len(excluded),
        "excluded_episode_ids": [row["episode_id"] for row in excluded],
        "excluded": excluded,
        "accepted_video_bytes": video_bytes,
        "accepted_video_hours": len(accepted_rows) * 1201 / 20.0 / 3600.0,
        "raw_avi_count": sum(1 for path in collection.rglob("*.avi") if path.is_file()),
        "qa_sha256_by_episode": qa_hashes,
        "distribution": {
            key: distribution(accepted_rows, key)
            for key in ("split", "map", "weapon", "template", "kill_count", "trajectory_scale")
        },
        "invariants": {
            "accepted_qa_all_pass": True,
            "accepted_video_files_present": True,
            "accepted_video_sizes_match": True,
            "accepted_video_frames_1201": True,
            "accepted_raw_avi_retained_false": True,
            "accepted_source_manifest_fields_match": True,
            "accepted_and_excluded_partition_source_manifest": True,
        },
    }
    report_path = collection / "FROZEN_COLLECTION.json"
    atomic_write(report_path, json_bytes(report))

    marker = {
        "schema_version": "xonotic-stage2-long60-freeze-marker-v1",
        "frozen": True,
        "source_release_id": report["source_release_id"],
        "accepted_count": report["accepted_count"],
        "excluded_count": report["excluded_count"],
        "accepted_snapshot": str(frozen_manifest),
        "accepted_snapshot_sha256": frozen_sha,
        "frozen_collection_report": str(report_path),
        "frozen_collection_report_sha256": sha256_file(report_path),
        "frozen_utc": report["frozen_utc"],
    }
    marker_path = collection / "control" / "FROZEN.json"
    atomic_write(marker_path, json_bytes(marker))

    print(json.dumps({
        "marker": str(marker_path),
        "accepted_count": len(accepted_rows),
        "excluded_count": len(excluded),
        "accepted_snapshot_sha256": frozen_sha,
        "distribution": report["distribution"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
