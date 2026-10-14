                      
"""Build a fixed-seed uniform review from landed Stage-2 accepted data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_stage2_causal_gallery as gallery


ROOT = Path("./xonotic_capture")
DEFAULT_OUTPUT_ROOT = (
    ROOT / "stage2_formal_40k_v1_output/56x1/primary"
)
DEFAULT_SEED = "stage2-formal-landed-uniform-review-20260731-v1"
DEFAULT_REVIEW_DIRECTORY = "review-random100-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def selection_key(seed: str, episode_id: str) -> str:
    return hashlib.sha256(
        f"{seed}\0{episode_id}".encode("utf-8")
    ).hexdigest()


def count(values: list[Any]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(str(value) for value in values).items(),
            key=lambda item: (-item[1], item[0]),
        )
    )


def load_episode_summary(row: dict[str, Any]) -> dict[str, Any]:
    episode = Path(str(row["episode_path"]))
    causal = json.loads(
        (episode / "causal_interaction.json").read_text(
            encoding="utf-8"
        )
    )
    record = json.loads(
        (episode / "episode.json").read_text(encoding="utf-8")
    )
    qa = json.loads((episode / "qa.json").read_text(encoding="utf-8"))
    per_shot = causal.get("per_shot") or {}
    target_labels = per_shot.get("target_label_checks") or {}
    package = row.get("package_sha256") or {}
    required_package = {
        "actions.parquet",
        "audio_events.parquet",
        "causal_interaction.json",
        "episode.json",
        "events.parquet",
        "frames.parquet",
        "model_actions.parquet",
        "qa.json",
        "shot_outcomes.parquet",
        "states.parquet",
        "target_relations.parquet",
        "video.mkv",
    }
    checks = {
        "accepted": qa.get("accepted") is True,
        "capture_valid": qa.get("capture_valid") is True,
        "hard_gates_pass": (
            (row.get("qa") or {}).get("hard_gates_pass") is True
        ),
        "frames_320": (row.get("qa") or {}).get("frames") == 320,
        "audio_samples_240000": (
            (row.get("qa") or {}).get("audio_samples_per_channel")
            == 240000
        ),
        "frame_tick_mapping_exact": (
            (row.get("qa") or {}).get("mapping_rate") == 1.0
        ),
        "target_observation_complete": (
            target_labels.get("observation_complete") is True
        ),
        "not_right_censored": (
            target_labels.get("not_right_censored") is True
        ),
        "causal_passed": causal.get("passed") is True,
        "package_complete": required_package <= set(package),
    }
    return {
        "episode_id": str(row["episode_id"]),
        "episode_path": str(episode),
        "map": row.get("map"),
        "gametype": row.get("gametype"),
        "weapon": row.get("weapon") or record.get("weapon"),
        "aim_policy": causal.get("aim_policy"),
        "planned_role": row.get("canary_role"),
        "actual_outcome": causal.get("actual_outcome"),
        "fire_count": (
            (causal.get("event_counts") or {}).get("fire_count")
        ),
        "target_hit_count": per_shot.get("target_hit_count"),
        "target_miss_count": per_shot.get("target_miss_count"),
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument(
        "--review-directory", default=DEFAULT_REVIEW_DIRECTORY
    )
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    rows = gallery.accepted_rows(output_root)
    by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for row in rows:
        episode_id = str(row["episode_id"])
        if episode_id in by_id:
            duplicates.append(episode_id)
        by_id[episode_id] = row
    if duplicates:
        raise RuntimeError(
            "duplicate accepted episode IDs: "
            + ", ".join(sorted(set(duplicates))[:20])
        )
    if args.sample_size <= 0:
        raise RuntimeError("sample size must be positive")
    if len(by_id) < args.sample_size:
        raise RuntimeError(
            f"sample {args.sample_size} exceeds landed accepted "
            f"{len(by_id)}"
        )

    ordered = sorted(
        by_id.values(),
        key=lambda row: (
            selection_key(args.seed, str(row["episode_id"])),
            str(row["episode_id"]),
        ),
    )
    selected = ordered[: args.sample_size]
    summaries = [load_episode_summary(row) for row in selected]
    review_root = output_root / args.review_directory
    manifest_path = review_root / "sample_manifest.jsonl"
    atomic_text(
        manifest_path,
        "".join(
            json.dumps(
                {
                    "episode_id": summary["episode_id"],
                    "selection_key": selection_key(
                        args.seed, summary["episode_id"]
                    ),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for summary in summaries
        ),
    )

    index = gallery.build(
        output_root,
        episode_manifest=manifest_path,
        review_directory=args.review_directory,
    )
    audit = {
        "schema_version": "xonotic-stage2-landed-uniform-review-v1",
        "created_utc": utc_now(),
        "output_root": str(output_root),
        "review_directory": args.review_directory,
        "selection": {
            "population": "landed accepted rows at snapshot time",
            "eligible_accepted_count": len(by_id),
            "sample_size": args.sample_size,
            "seed": args.seed,
            "algorithm": "ascending sha256(seed + NUL + episode_id)",
            "outcome_blind": True,
            "visual_content_blind": True,
        },
        "sample_manifest": str(manifest_path),
        "index": str(index),
        "selected_episode_ids": [
            summary["episode_id"] for summary in summaries
        ],
        "distribution": {
            "map": count([summary["map"] for summary in summaries]),
            "gametype": count(
                [summary["gametype"] for summary in summaries]
            ),
            "weapon": count(
                [summary["weapon"] for summary in summaries]
            ),
            "aim_policy": count(
                [summary["aim_policy"] for summary in summaries]
            ),
            "planned_role": count(
                [summary["planned_role"] for summary in summaries]
            ),
            "actual_outcome": count(
                [summary["actual_outcome"] for summary in summaries]
            ),
        },
        "qa": {
            "passed_count": sum(
                summary["passed"] for summary in summaries
            ),
            "failed_count": sum(
                not summary["passed"] for summary in summaries
            ),
            "failed": [
                summary
                for summary in summaries
                if not summary["passed"]
            ],
        },
        "episodes": summaries,
        "passed": all(summary["passed"] for summary in summaries),
    }
    atomic_text(
        review_root / "REVIEW_AUDIT.json",
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
    )
    if not audit["passed"]:
        raise RuntimeError("selected review QA failed")
    print(index)
    print(review_root / "REVIEW_AUDIT.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
