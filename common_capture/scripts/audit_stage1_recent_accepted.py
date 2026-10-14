                      
"""Audit a fixed-seed sample accepted after one Stage-1 run start."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_stage1_landed_review as review              
import run_capture_manifest_shard as journal              


def load_recent(
    output_root: Path,
    shard_count: int,
    since_utc: str,
) -> dict[str, dict[str, Any]]:
    accepted: dict[str, dict[str, Any]] = {}
    for shard_index in range(shard_count):
        tag = f"shard-{shard_index:03d}-of-{shard_count:03d}"
        path = (
            output_root
            / "manifests/shards/primary"
            / tag
            / "accepted_candidates.jsonl"
        )
        if not path.is_file():
            continue
        for row in journal.load_jsonl_locked(path):
            if str(row.get("published_utc", "")) < since_utc:
                continue
            episode_id = str(row["episode_id"])
            if episode_id in accepted:
                raise RuntimeError(
                    f"duplicate accepted episode ID: {episode_id}"
                )
            accepted[episode_id] = row
    return accepted


def sample_key(seed: str, episode_id: str) -> str:
    return hashlib.sha256(
        f"{seed}\0{episode_id}".encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--since-utc", required=True)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument(
        "--seed",
        default="stage1-r5-recent-accepted-review-20260730-v1",
    )
    parser.add_argument("--shard-count", type=int, default=56)
    parser.add_argument("--verify-workers", type=int, default=8)
    args = parser.parse_args()

    manifest_root = args.manifest_root.resolve()
    output_root = args.output_root.resolve()
    review_root = args.review_root.resolve()
    if review_root.exists():
        raise RuntimeError(f"review root already exists: {review_root}")
    if args.sample_size <= 0:
        raise RuntimeError("sample-size must be positive")

    accepted = load_recent(
        output_root,
        args.shard_count,
        args.since_utc,
    )
    if len(accepted) < args.sample_size:
        raise RuntimeError(
            f"sample {args.sample_size} exceeds recent accepted "
            f"{len(accepted)}"
        )
    episode_ids = sorted(accepted)
    population_sha256 = hashlib.sha256(
        ("\n".join(episode_ids) + "\n").encode()
    ).hexdigest()
    selected = sorted(
        (sample_key(args.seed, episode_id), episode_id)
        for episode_id in episode_ids
    )[: args.sample_size]
    selected_ids = {episode_id for _, episode_id in selected}

    recent_rows: list[dict[str, Any]] = []
    selected_by_id: dict[str, dict[str, Any]] = {}
    joined: set[str] = set()
    for plan in review.stream_jsonl(manifest_root / "input.jsonl"):
        episode_id = str(plan["episode_id"])
        accepted_row = accepted.get(episode_id)
        if accepted_row is None:
            continue
        projected = review.project(plan, accepted_row)
        recent_rows.append(projected)
        joined.add(episode_id)
        if episode_id in selected_ids:
            selected_by_id[episode_id] = projected
    if joined != set(accepted):
        raise RuntimeError(
            "recent accepted/manifest join incomplete: "
            f"{len(joined)}/{len(accepted)}"
        )

    review_root.mkdir(parents=True)
    (review_root / "thumbnails").mkdir()
    sample_rows = [
        {
            **selected_by_id[episode_id],
            "sample_index": sample_index,
            "selection_key": key,
        }
        for sample_index, (key, episode_id) in enumerate(selected, 1)
    ]
    verified_by_id: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.verify_workers
    ) as executor:
        futures = {
            executor.submit(
                review.verify_one,
                row,
                accepted[row["episode_id"]],
                review_root,
            ): row["episode_id"]
            for row in sample_rows
        }
        for future in concurrent.futures.as_completed(futures):
            episode_id = futures[future]
            verified_by_id[episode_id] = future.result()
            print(
                f"verified {len(verified_by_id)}/{len(sample_rows)} "
                f"episode={episode_id} "
                f"passed={verified_by_id[episode_id]['passed']}",
                flush=True,
            )
    verified = [
        verified_by_id[row["episode_id"]] for row in sample_rows
    ]
    failed = [row for row in verified if not row["passed"]]
    recent_distribution = review.counters(recent_rows)
    sample_distribution = review.counters(verified)
    published = sorted(
        str(row.get("published_utc", "")) for row in accepted.values()
    )
    snapshot = {
        "schema_version": "xonotic-stage1-recent-accepted-review-v1",
        "created_utc": review.utc_now(),
        "since_utc": args.since_utc,
        "seed": args.seed,
        "selection_method": (
            "sort recent accepted episode IDs by "
            "sha256(seed + NUL + episode_id); take first N"
        ),
        "population_sha256": population_sha256,
        "accepted_population": len(accepted),
        "accepted_data_hours": len(accepted) * 5 / 3600,
        "published_utc_first": published[0],
        "published_utc_last": published[-1],
        "sample_size": len(verified),
        "manifest_root": str(manifest_root),
        "output_root": str(output_root),
        "landed_distribution": recent_distribution,
        "sample_distribution": sample_distribution,
        "verification": {
            "passed": len(verified) - len(failed),
            "failed": len(failed),
            "failures": [
                {
                    "episode_id": row["episode_id"],
                    "failed_checks": row["failed_checks"],
                    "failed_hard_gates": row["failed_hard_gates"],
                    "hash_mismatches": row["hash_mismatches"],
                    "errors": row["errors"],
                }
                for row in failed
            ],
            "full_package_sha256_checked": True,
            "ffprobe_checked": True,
            "thumbnail_checked": True,
        },
        "sample": verified,
    }
    review.atomic_text(
        review_root / "REVIEW.json",
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
    )
    review.atomic_text(
        review_root / "SAMPLE_MANIFEST.jsonl",
        "".join(
            json.dumps(
                {
                    "sample_index": row["sample_index"],
                    "selection_key": row["selection_key"],
                    "episode_id": row["episode_id"],
                    "episode_path": row["episode_path"],
                    "passed": row["passed"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for row in verified
        ),
    )
    review.write_csv(review_root / "SAMPLE_EPISODES.csv", verified)
    report = [
        "# Stage-1 r5 本轮新增 accepted 固定种子随机抽检",
        "",
        f"- since UTC：`{args.since_utc}`",
        f"- snapshot：`{snapshot['created_utc']}`",
        f"- 本轮 accepted population：`{len(accepted)}`",
        f"- 固定随机样本：`{len(verified)}`",
        f"- 全项通过：`{len(verified) - len(failed)}`",
        f"- 失败：`{len(failed)}`",
        f"- population SHA256：`{population_sha256}`",
        "",
        "每条均重算完整 package SHA256，并检查 ffprobe、320 帧、"
        "240000 音频采样、frame-tick mapping、HUD、gametype、"
        "NVIDIA renderer 与全部 hard gates。",
        "",
        "详细分布见 `REVIEW.json`；视频与三帧缩略图见 `index.html`。",
        "",
    ]
    review.atomic_text(review_root / "REPORT.md", "\n".join(report))
    review.write_html(review_root / "index.html", snapshot, verified)
    index_path = review_root / "index.html"
    relative_candidates = Path(
        os.path.relpath(output_root / "candidates", review_root)
    ).as_posix()
    index_text = index_path.read_text(encoding="utf-8").replace(
        "../stage1_foundation_v5_output_56x1/candidates/",
        f"{relative_candidates}/",
    )
    index_text = index_text.replace(
        "固定种子均匀随机 100 条",
        f"r5 本轮新增固定种子随机 {len(verified)} 条",
    )
    review.atomic_text(index_path, index_text)

    print(
        json.dumps(
            {
                "review_root": str(review_root),
                "recent_accepted_population": len(accepted),
                "sample_size": len(verified),
                "passed": len(verified) - len(failed),
                "failed": len(failed),
                "population_sha256": population_sha256,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
