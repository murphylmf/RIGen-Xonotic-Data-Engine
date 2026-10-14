                      
"""Audit the non-training stochastic Stage-2 review from published artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xonotic_capture as capture              


DEFAULT_MANIFEST = (
    ROOT / "manifests/stage2_stochastic_review_v1/input.jsonl"
)
DEFAULT_OUTPUT = ROOT / "stage2_stochastic_review_v1_output"


def published_rows(
    output_root: Path, filename: str
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            f"shard-*-of-*/{filename}"
        )
    ):
        result.extend(capture.load_jsonl(path))
    return result


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def audit(
    manifest_path: Path, output_root: Path
) -> dict[str, Any]:
    planned = capture.load_jsonl(manifest_path)
    planned_ids = {str(row["episode_id"]) for row in planned}
    accepted = published_rows(output_root, "accepted.jsonl")
    rejects = published_rows(output_root, "rejects.jsonl")
    accepted_by_id = {
        str(row["episode_id"]): row for row in accepted
    }
    reject_counts = Counter(
        str(row.get("failure_kind", "unknown"))
        for row in rejects
    )
    outcomes: Counter[str] = Counter()
    weapons: Counter[str] = Counter()
    variants: Counter[str] = Counter()
    fire_counts: Counter[int] = Counter()
    enemy_segments: Counter[int] = Counter()
    total_hits = 0
    total_misses = 0
    total_shots = 0
    hard_failures: dict[str, list[str]] = defaultdict(list)
    rows: list[dict[str, Any]] = []
    for episode_id, manifest in sorted(accepted_by_id.items()):
        episode_path = Path(manifest["episode_path"])
        qa = json.loads(
            (episode_path / "qa.json").read_text(encoding="utf-8")
        )
        episode = json.loads(
            (episode_path / "episode.json").read_text(
                encoding="utf-8"
            )
        )
        causal = json.loads(
            (episode_path / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        shots = pd.read_parquet(
            episode_path / "shot_outcomes.parquet"
        )
        hit_count = int(shots["hit"].astype(bool).sum())
        miss_count = int((~shots["hit"].astype(bool)).sum())
        total_hits += hit_count
        total_misses += miss_count
        total_shots += len(shots)
        outcome = str(causal["actual_outcome"])
        weapon = str(episode["weapon"])
        variant = str(
            episode["stochastic_review_design"][
                "random_aim_variant"
            ]
        )
        enemy = causal["enemy_random_policy"]
        outcomes[outcome] += 1
        weapons[weapon] += 1
        variants[variant] += 1
        fire_counts[len(shots)] += 1
        enemy_segments[int(enemy["segment_count"])] += 1
        checks = {
            "accepted": qa.get("accepted") is True,
            "stage2_passed": causal.get("passed") is True,
            "video_frames": qa.get("video", {}).get("frames")
            == capture.OUTPUT_TICKS,
            "audio_samples": qa.get("audio", {}).get(
                "samples_per_channel"
            )
            == capture.AUDIO_SAMPLES,
            "mapping": qa.get("mapping", {}).get("mapped_frames")
            == capture.OUTPUT_TICKS,
            "per_shot_rows": len(shots)
            == int(qa["events"]["fire_count"]),
            "per_shot_hits": hit_count
            == int(qa["events"]["hit_fire_count"]),
            "enemy_path": enemy.get("passed") is True,
            "outcome_not_admission": (
                episode["acceptance"]["actual_outcome"] is None
            ),
        }
        for name, passed in checks.items():
            if not passed:
                hard_failures[name].append(episode_id)
        rows.append(
            {
                "episode_id": episode_id,
                "weapon": weapon,
                "variant": variant,
                "outcome": outcome,
                "shots": len(shots),
                "hits": hit_count,
                "misses": miss_count,
                "hit_rate": (
                    hit_count / len(shots) if len(shots) else 0.0
                ),
                "visible_frames": causal["visible_frames"],
                "centered_frames": causal["centered_frames"],
                "enemy_segments": enemy["segment_count"],
                "enemy_hold_frames": enemy["hold_frames"],
                "enemy_hop_frames": enemy["hop_frames"],
                "checks": checks,
            }
        )
    missing = sorted(planned_ids - set(accepted_by_id))
    unexpected = sorted(set(accepted_by_id) - planned_ids)
    report = {
        "schema_version": (
            "xonotic-stage2-stochastic-review-audit-v1"
        ),
        "manifest": str(manifest_path),
        "manifest_sha256": capture.sha256_file(manifest_path),
        "output_root": str(output_root),
        "planned": len(planned),
        "accepted": len(accepted_by_id),
        "missing": missing,
        "unexpected": unexpected,
        "reject_attempts": len(rejects),
        "reject_failure_distribution": dict(reject_counts),
        "outcome_distribution": dict(outcomes),
        "weapon_distribution": dict(weapons),
        "variant_distribution": dict(variants),
        "fire_count_distribution": {
            str(key): value
            for key, value in sorted(fire_counts.items())
        },
        "enemy_segment_distribution": {
            str(key): value
            for key, value in sorted(enemy_segments.items())
        },
        "per_shot": {
            "shots": total_shots,
            "hits": total_hits,
            "misses": total_misses,
            "hit_rate": (
                total_hits / total_shots if total_shots else 0.0
            ),
        },
        "hard_failures": dict(hard_failures),
        "rows": rows,
        "passed": (
            len(accepted_by_id) == len(planned)
            and not missing
            and not unexpected
            and not hard_failures
        ),
    }
    atomic_json(output_root / "AUDIT.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST
    )
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT
    )
    args = parser.parse_args()
    report = audit(
        args.manifest.resolve(), args.output_root.resolve()
    )
    print(
        capture.canonical_json(
            {
                key: report[key]
                for key in (
                    "planned",
                    "accepted",
                    "reject_attempts",
                    "outcome_distribution",
                    "per_shot",
                    "passed",
                )
            }
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
