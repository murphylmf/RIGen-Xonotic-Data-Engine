                      
"""Create a deterministic non-training review slice from formal Stage-1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import xonotic_capture as capture


DEFAULT_SOURCE_COMMIT = "63bfb795faca21ad3db6dff7632171a13223cd76"


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def transform(
    source: dict[str, Any],
    ordinal: int,
    source_shard: int,
    source_commit: str,
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    source_id = str(row["episode_id"])
    episode_id = f"s1dist63_{ordinal:06d}"
    row.update(
        {
            "episode_id": episode_id,
            "source_episode_id": source_id,
            "source_split": source.get("split"),
            "source_candidate_wave": source.get("candidate_wave"),
            "source_assigned_shard": source_shard,
            "source_shard_count": source.get("shard_count"),
            "source_source_commit_required": source.get(
                "source_commit_required"
            ),
            "split": "v2_stage1_review_fov90",
            "training_stage": "distribution_review_only",
            "acceptance_policy": capture.TIERED_REVIEW_POLICY,
            "formal_collection_authorized": False,
            "training_admitted": False,
            "human_review_required_before_training": True,
            "canary_role": "stage1_distribution_review",
            "candidate_wave": "nontraining_distribution_review",
            "source_commit_required": source_commit,
            "assigned_shard": 0,
            "shard_count": 1,
        }
    )
    row.pop("formal_authorization_basis", None)
    if row.get("anchor_id"):
        row["anchor_id"] = str(row["anchor_id"]).replace(
            source_id, episode_id
        )
    return row


def counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    values = Counter(str(row.get(field)) for row in rows)
    return dict(sorted(values.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("manifests/stage1_foundation_v1"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(
            "manifests/stage1_distribution_review_63bfb795"
        ),
    )
    parser.add_argument("--source-shards", type=int, default=32)
    parser.add_argument(
        "--source-shard-count", type=int, default=32
    )
    parser.add_argument(
        "--episodes-per-source-shard", type=int, default=4
    )
    parser.add_argument(
        "--source-commit", default=DEFAULT_SOURCE_COMMIT
    )
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise RuntimeError(f"refuse overwrite: {output_root}")
    if (
        args.source_shards <= 0
        or args.source_shard_count <= 0
        or args.source_shards > args.source_shard_count
        or args.episodes_per_source_shard <= 0
    ):
        raise RuntimeError("selection sizes must be positive")

    rows: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for source_shard in range(args.source_shards):
        tag = (
            f"shard-{source_shard:03d}-of-"
            f"{args.source_shard_count:03d}.jsonl"
        )
        path = source_root / "shards/primary" / tag
        source_rows = capture.load_jsonl(path)
        if len(source_rows) < args.episodes_per_source_shard:
            raise RuntimeError(f"source shard too short: {path}")
        source_hashes[str(path)] = capture.sha256_file(path)
        for source in source_rows[: args.episodes_per_source_shard]:
            rows.append(
                transform(
                    source,
                    len(rows) + 1,
                    source_shard,
                    args.source_commit,
                )
            )

    manifest = output_root / "shard-000-of-001.jsonl"
    manifest_text = "".join(
        capture.canonical_json(row) + "\n" for row in rows
    )
    write_once(manifest, manifest_text)
    manifest_sha256 = hashlib.sha256(
        manifest_text.encode()
    ).hexdigest()
    metadata = {
        "schema_version": (
            "xonotic-stage1-nontraining-distribution-review-manifest-v1"
        ),
        "created_utc": capture.utc_now(),
        "source_commit": args.source_commit,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "selection": {
            "source_root": str(source_root),
            "selected_source_shards": args.source_shards,
            "source_shard_count": args.source_shard_count,
            "episodes_per_source_shard": (
                args.episodes_per_source_shard
            ),
            "rows": len(rows),
            "source_manifest_sha256": source_hashes,
        },
        "planned_distribution": {
            "dataset_role": counts(rows, "dataset_role"),
            "primary_bucket": counts(rows, "primary_bucket"),
            "gametype": counts(rows, "gametype"),
            "enemy_present": counts(rows, "enemy_present"),
            "map": counts(rows, "map"),
            "weapon": counts(rows, "weapon"),
            "fire_required": {
                "true": sum(
                    bool((row.get("acceptance") or {}).get("fire_required"))
                    for row in rows
                ),
                "false": sum(
                    not bool(
                        (row.get("acceptance") or {}).get("fire_required")
                    )
                    for row in rows
                ),
            },
        },
        "canary": {
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(manifest),
                    "rows": len(rows),
                    "sha256": manifest_sha256,
                }
            ],
        },
    }
    write_once(
        output_root / "MANIFEST_METADATA.json",
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
    )
    print(
        json.dumps(
            {
                "manifest": str(manifest),
                "metadata": str(
                    output_root / "MANIFEST_METADATA.json"
                ),
                "rows": len(rows),
                "sha256": manifest_sha256,
                "planned_distribution": metadata[
                    "planned_distribution"
                ],
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
