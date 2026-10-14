                      
"""Uniformly sample 100 non-training review rows from the Stage-1 v4 plan."""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import prepare_stage1_manifests as stage1              


ROOT = capture.ROOT
SOURCE_MANIFEST = stage1.INPUT_PATH
SOURCE_METADATA = stage1.METADATA_PATH
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage1_foundation_v4_random_review_100_manifest_hash_seed"
)
OUTPUT_MANIFEST = OUTPUT_ROOT / "input.jsonl"
OUTPUT_METADATA = OUTPUT_ROOT / "MANIFEST_METADATA.json"
OUTPUT_AUDIT = OUTPUT_ROOT / "SAMPLE_AUDIT.json"
DIAGNOSTIC_SMOKE_MANIFEST = OUTPUT_ROOT / "diagnostic_smoke.jsonl"
DIAGNOSTIC_SAFETY_MANIFEST = (
    OUTPUT_ROOT / "diagnostic_safety_smoke.jsonl"
)
REVIEW_SPLIT = "v4_stage1_manifest_random_review"
DEFAULT_SEED: int | None = None
DEFAULT_SAMPLE_SIZE = 100


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_random_review_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def nested(row: dict[str, Any], *path: str) -> Any:
    value: Any = row
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


MARGINALS: dict[str, tuple[str, ...]] = {
    "dataset_role": ("dataset_role",),
    "primary_bucket": ("primary_bucket",),
    "map": ("map",),
    "gametype": ("gametype",),
    "enemy_present": ("enemy_present",),
    "weapon": ("weapon",),
    "weapon_action": ("action_design", "weapon_action"),
    "locomotion_direction": (
        "action_design",
        "locomotion_direction",
    ),
    "movement_profile": ("action_design", "movement_profile"),
    "view_direction": ("action_design", "view_direction"),
    "view_profile": ("action_design", "view_profile"),
    "action_arity": ("action_design", "action_arity"),
    "jump": ("action_design", "jump"),
    "net_displacement_bin": (
        "scheduler_targets",
        "net_displacement_bin",
    ),
    "yaw_range_bin": ("scheduler_targets", "yaw_range_bin"),
    "pitch_range_bin": ("scheduler_targets", "pitch_range_bin"),
}


def marginal_counts(
    rows: list[dict[str, Any]], path: tuple[str, ...]
) -> Counter[str]:
    result: Counter[str] = Counter()
    for row in rows:
        value = nested(row, *path)
        result[str(value)] += 1
    return result


def distribution_report(
    population: list[dict[str, Any]],
    sample: list[dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    population_size = len(population)
    sample_size = len(sample)
    for name, path in MARGINALS.items():
        full = marginal_counts(population, path)
        observed = marginal_counts(sample, path)
        values = sorted(set(full) | set(observed))
        rows = {}
        for value in values:
            full_fraction = full[value] / population_size
            sample_fraction = observed[value] / sample_size
            rows[value] = {
                "population_count": full[value],
                "population_percent": round(
                    full_fraction * 100.0, 4
                ),
                "sample_count": observed[value],
                "sample_percent": round(
                    sample_fraction * 100.0, 4
                ),
                "expected_sample_count": round(
                    full_fraction * sample_size, 4
                ),
                "absolute_percentage_point_delta": round(
                    abs(sample_fraction - full_fraction) * 100.0,
                    4,
                ),
            }
        result[name] = rows
    result["route_presence"] = {
        "population_count": sum(
            bool(row.get("route_request")) for row in population
        ),
        "sample_count": sum(
            bool(row.get("route_request")) for row in sample
        ),
    }
    return result


def generate(seed: int | None, sample_size: int) -> dict[str, Any]:
    if not SOURCE_MANIFEST.is_file() or not SOURCE_METADATA.is_file():
        raise capture.CaptureFailure(
            "stage1_v4_source_manifest_missing",
            f"{SOURCE_MANIFEST} {SOURCE_METADATA}",
        )
    population = capture.load_jsonl(SOURCE_MANIFEST)
    if sample_size < 1 or sample_size > len(population):
        raise capture.CaptureFailure(
            "invalid_random_review_sample_size", str(sample_size)
        )
    source_sha256 = capture.sha256_file(SOURCE_MANIFEST)
    metadata_sha256 = capture.sha256_file(SOURCE_METADATA)
    seed_policy = "explicit_cli_seed"
    if seed is None:
        seed = int(source_sha256[:16], 16)
        seed_policy = "first_64_bits_of_source_manifest_sha256"

                                                                              
                                                                             
                                                                                
    selected_ordinals = sorted(
        random.Random(seed).sample(range(len(population)), sample_size)
    )
    sample: list[dict[str, Any]] = []
    for sample_index, population_ordinal in enumerate(
        selected_ordinals, 1
    ):
        source = population[population_ordinal]
        row = copy.deepcopy(source)
        source_episode_id = str(source["episode_id"])
        row.update(
            {
                "episode_id": (
                    f"s1v4_review100_{sample_index:03d}_"
                    f"{source_episode_id}"
                ),
                "source_episode_id": source_episode_id,
                "source_candidate_ordinal": source[
                    "candidate_ordinal"
                ],
                "source_assigned_shard": source["assigned_shard"],
                "source_shard_count": source["shard_count"],
                "source_manifest": str(
                    SOURCE_MANIFEST.relative_to(ROOT)
                ),
                "source_manifest_sha256": source_sha256,
                "source_manifest_metadata_sha256": metadata_sha256,
                "uniform_sample_seed": seed,
                "uniform_population_ordinal_zero_based": (
                    population_ordinal
                ),
                "review_sample_index": sample_index,
                "split": REVIEW_SPLIT,
                "formal_collection_authorized": False,
                "formal_authorization_basis": (
                    "fixed_seed_uniform_random_nontraining_review"
                ),
                "training_admitted": False,
                "assigned_shard": 0,
                "shard_count": 1,
            }
        )
        sample.append(row)

    sample_text = canonical_lines(sample)
    write_once_or_verify(OUTPUT_MANIFEST, sample_text)
    sample_sha256 = capture.sha256_file(OUTPUT_MANIFEST)
    created_utc = (
        json.loads(OUTPUT_METADATA.read_text(encoding="utf-8"))[
            "created_utc"
        ]
        if OUTPUT_METADATA.is_file()
        else capture.utc_now()
    )
    metadata = {
        "schema_version": "xonotic-stage1-random-review-manifest-v1",
        "created_utc": created_utc,
        "source_commit": stage1.SOURCE_COMMIT,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "selection": {
            "algorithm": (
                "python random.Random(seed).sample over canonical "
                "population line ordinals; uniform without replacement"
            ),
            "post_stratification": False,
            "seed": seed,
            "seed_policy": seed_policy,
            "population_rows": len(population),
            "sample_rows": sample_size,
            "selected_population_ordinals_zero_based": (
                selected_ordinals
            ),
            "source_manifest": str(
                SOURCE_MANIFEST.relative_to(ROOT)
            ),
            "source_manifest_sha256": source_sha256,
            "source_metadata": str(
                SOURCE_METADATA.relative_to(ROOT)
            ),
            "source_metadata_sha256": metadata_sha256,
        },
        "review": {
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "rows": sample_size,
                    "path": str(
                        OUTPUT_MANIFEST.relative_to(ROOT)
                    ),
                    "sha256": sample_sha256,
                }
            ],
        },
    }
    metadata_text = (
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n"
    )
    write_once_or_verify(OUTPUT_METADATA, metadata_text)

    checks = {
        "population_rows": len(population) == stage1.PRIMARY_COUNT,
        "sample_rows": len(sample) == sample_size,
        "uniform_ordinals_unique": (
            len(selected_ordinals) == len(set(selected_ordinals))
        ),
        "sample_ids_unique": (
            len({row["episode_id"] for row in sample}) == sample_size
        ),
        "source_rows_exact": all(
            row["source_episode_id"]
            == population[
                row["uniform_population_ordinal_zero_based"]
            ]["episode_id"]
            for row in sample
        ),
        "nontraining_policy": all(
            row["split"] == REVIEW_SPLIT
            and row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
            and row["assigned_shard"] == 0
            and row["shard_count"] == 1
            and capture.output_split_authorized(row)
            for row in sample
        ),
        "source_commit": all(
            row["source_commit_required"] == stage1.SOURCE_COMMIT
            for row in sample
        ),
        "manifest_sha256": (
            capture.sha256_file(OUTPUT_MANIFEST) == sample_sha256
        ),
    }
    audit = {
        "schema_version": "xonotic-stage1-random-review-audit-v1",
        "created_utc": capture.utc_now(),
        "checks": checks,
        "passed": all(checks.values()),
        "selection_is_uniform_not_curated": True,
        "seed": seed,
        "seed_policy": seed_policy,
        "population_rows": len(population),
        "sample_rows": len(sample),
        "sample_manifest_sha256": sample_sha256,
        "distribution": distribution_report(population, sample),
    }
    OUTPUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_AUDIT.with_name(
        f".{OUTPUT_AUDIT.name}.tmp.{os.getpid()}"
    )
    temporary.write_text(
        json.dumps(
            audit, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, OUTPUT_AUDIT)
    if not audit["passed"]:
        raise capture.CaptureFailure(
            "stage1_random_review_audit_failed",
            capture.canonical_json(checks),
        )
    return {
        "manifest": str(OUTPUT_MANIFEST),
        "metadata": str(OUTPUT_METADATA),
        "audit": str(OUTPUT_AUDIT),
        "sample_rows": sample_size,
        "seed": seed,
        "sha256": sample_sha256,
    }


def write_diagnostic_smoke(indices: tuple[int, ...]) -> dict[str, Any]:
    """Write an explicitly labeled targeted subset without changing the sample."""
    sample = capture.load_jsonl(OUTPUT_MANIFEST)
    by_index = {
        int(row["review_sample_index"]): row for row in sample
    }
    missing = [index for index in indices if index not in by_index]
    if missing:
        raise capture.CaptureFailure(
            "diagnostic_smoke_index_missing", str(missing)
        )
    rows = [by_index[index] for index in indices]
    text = canonical_lines(rows)
    write_once_or_verify(DIAGNOSTIC_SMOKE_MANIFEST, text)
    return {
        "diagnostic_smoke_manifest": str(
            DIAGNOSTIC_SMOKE_MANIFEST
        ),
        "diagnostic_smoke_indices": list(indices),
        "diagnostic_smoke_rows": len(rows),
        "diagnostic_smoke_sha256": capture.sha256_file(
            DIAGNOSTIC_SMOKE_MANIFEST
        ),
        "diagnostic_only_not_part_of_uniform_selection": True,
    }


def write_diagnostic_safety_smoke(
    indices: tuple[int, ...],
) -> dict[str, Any]:
    sample = capture.load_jsonl(OUTPUT_MANIFEST)
    by_index = {
        int(row["review_sample_index"]): row for row in sample
    }
    missing = [index for index in indices if index not in by_index]
    if missing:
        raise capture.CaptureFailure(
            "diagnostic_safety_index_missing", str(missing)
        )
    rows: list[dict[str, Any]] = []
    for index in indices:
        row = copy.deepcopy(by_index[index])
        row["episode_id"] = (
            f"s1v4_safety_{index:03d}_{row['source_episode_id']}"
        )
        row["force_stage1_safety_route"] = True
        row["diagnostic_only"] = True
        rows.append(row)
    text = canonical_lines(rows)
    write_once_or_verify(DIAGNOSTIC_SAFETY_MANIFEST, text)
    return {
        "diagnostic_safety_manifest": str(
            DIAGNOSTIC_SAFETY_MANIFEST
        ),
        "diagnostic_safety_indices": list(indices),
        "diagnostic_safety_rows": len(rows),
        "diagnostic_safety_sha256": capture.sha256_file(
            DIAGNOSTIC_SAFETY_MANIFEST
        ),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--seed", type=int, default=DEFAULT_SEED)
    result.add_argument(
        "--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE
    )
    result.add_argument(
        "--diagnostic-smoke-indices",
        default="",
        help=(
            "Optional comma-separated review_sample_index values for a "
            "separate targeted pipeline smoke manifest."
        ),
    )
    result.add_argument(
        "--diagnostic-safety-indices",
        default="",
        help=(
            "Optional comma-separated review_sample_index values for a "
            "separate forced safety-route diagnostic manifest."
        ),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    try:
        result = generate(args.seed, args.sample_size)
        indices = tuple(
            int(value)
            for value in args.diagnostic_smoke_indices.split(",")
            if value.strip()
        )
        if indices:
            result.update(write_diagnostic_smoke(indices))
        safety_indices = tuple(
            int(value)
            for value in args.diagnostic_safety_indices.split(",")
            if value.strip()
        )
        if safety_indices:
            result.update(
                write_diagnostic_safety_smoke(safety_indices)
            )
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
