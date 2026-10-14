                      
"""Build a fail-closed v14r4 replenishment manifest without changing its 42k target.

The v14 runtime insists on exactly 74,200 candidate rows.  This builder moves
unused reserve capacity from the already-complete exit categories to new
always-visible reserve candidates, keeping all primary rows, all processed
candidate rows, and the accepted 90/5/5 targets unchanged.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / (
    "manifests/stage2_motion_temporal_visibility_42k_v14_near_exit_90_5_5_"
    "nocrosshair_28shard_20260820_r4"
)
CAPTURE_ROOT = ROOT / (
    "production_runs/stage2_motion_temporal_visibility_42k_v14r4_90_5_5_"
    "nocrosshair_28gpu_20260820_01"
)
OUTPUT_ROOT = ROOT / (
    "manifests/stage2_motion_temporal_visibility_42k_v14_near_exit_90_5_5_"
    "nocrosshair_28shard_20260821_r5_runtime_replenish"
)
CATEGORIES = ("always_visible", "exit_hold", "exit_reacquire")
SHARD_COUNT = 28
GLOBAL_CANDIDATE_ROWS = 74_200
GLOBAL_PRIMARY_ROWS = 42_000
SEMANTIC_REVISION = "v14_near_exit_90_5_5_nocrosshair"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL {path}:{line_number}: {exc}") from exc
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def shard_manifest(root: Path, category: str, shard: int) -> Path:
    return (
        root
        / "categories"
        / category
        / "shards-028"
        / f"shard-{shard:03d}-of-028.jsonl"
    )


def journal(root: Path, category: str, shard: int, kind: str) -> Path:
    return root / category / f"shard_{shard:02d}" / "manifests" / f"{kind}.jsonl"


def processed_keys(capture_root: Path, category: str, shard: int) -> set[str]:
    keys: set[str] = set()
    for kind in ("accepted", "rejected"):
        path = journal(capture_root, category, shard, kind)
        if not path.is_file():
            continue
        for row in load_jsonl(path):
            key = str(row.get("sample_key") or "")
            if not key:
                raise RuntimeError(f"missing sample_key in {path}")
            keys.add(key)
    return keys


def accepted_count(capture_root: Path, category: str, shard: int) -> int:
    path = journal(capture_root, category, shard, "accepted")
    return len(load_jsonl(path)) if path.is_file() else 0


def stable_key(value: str) -> str:
    return hashlib.sha256(f"v14r4-runtime-replenish:{value}".encode()).hexdigest()


def clone_always_visible_reserve(
    source: dict[str, Any], *, shard: int, local_index: int, global_index: int
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    source_key = str(source["sample_key"])
    sample_key = f"s2mtv42v14r4p_{shard:02d}_{local_index:04d}"
    ordinal = 100_000 + global_index
    active = row["active_scenario"]
    original_scenario_hash = hashlib.sha256(
        canonical_json(source["active_scenario"]).encode()
    ).hexdigest()
    active["seed"] = int(active["seed"]) + 200_000_000 + global_index
    active["enemy_policy"]["policy_seed"] = int(active["seed"]) + 1_000_000
    trace = active.get("prefrozen_trace_source")
    if trace:
        trace["scenario_seed_relation"] = "independent_replenishment_scenario_seed"
    active["reserve_transform"] = {
        "schema_version": "xonotic-stage2-v14r4-runtime-replenishment-transform-v1",
        "source_sample_key": source_key,
        "source_scenario_sha256": original_scenario_hash,
        "camera_and_player_action_program_unchanged": True,
        "independent_scenario_seed": True,
        "raw_avi_retention_disabled": True,
    }
    active.update(
        {
            "episode_id": f"{sample_key}_active",
            "anchor_id": sample_key,
            "counterfactual_group_id": sample_key,
            "target_ordinal": ordinal,
        }
    )
    active["formal_design"]["ordinal"] = ordinal
    active["formal_design"]["cohort_role"] = "reserve"
    row.update(
        {
            "candidate_role": "reserve",
            "sample_key": sample_key,
            "ordinal": ordinal,
            "raw_avi_audit": False,
            "reserve_source_sample_key": source_key,
            "reserve_source_ordinal": int(source["ordinal"]),
        }
    )
    row["budget_token"].update(
        {
            "cohort_role": "category_replenishment_reserve",
            "source_sample_key": source_key,
        }
    )
    return row


def additions_per_shard(
    source_root: Path, capture_root: Path
) -> tuple[dict[int, int], dict[int, dict[str, int]]]:
    additions: dict[int, int] = {}
    report: dict[int, dict[str, int]] = {}
    for shard in range(SHARD_COUNT):
        rows = load_jsonl(shard_manifest(source_root, "always_visible", shard))
        processed = processed_keys(capture_root, "always_visible", shard)
        accepted = accepted_count(capture_root, "always_visible", shard)
        deficit = 1_350 - accepted
        if deficit <= 0:
            additions[shard] = 0
            report[shard] = {
                "accepted": accepted,
                "deficit": 0,
                "old_pending": len({str(row["sample_key"]) for row in rows} - processed),
                "added_candidates": 0,
            }
            continue
        old_pending = len({str(row["sample_key"]) for row in rows} - processed)
                                                                              
                                                                               
        added = max(300, math.ceil(deficit / 0.60) - old_pending + 200)
        additions[shard] = added
        report[shard] = {
            "accepted": accepted,
            "deficit": deficit,
            "old_pending": old_pending,
            "added_candidates": added,
        }
    return additions, report


def build(
    source_root: Path,
    capture_root: Path,
    output_root: Path,
    source_provenance_root: Path | None = None,
) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite: {output_root}")
    metadata = load_json(source_root / "MANIFEST_METADATA.json")
    if int(metadata.get("candidate_rows", -1)) != GLOBAL_CANDIDATE_ROWS:
        raise RuntimeError("source candidate count is not 74,200")
    if metadata.get("semantic_revision") != SEMANTIC_REVISION:
        raise RuntimeError("source semantic revision mismatch")

    additions, shard_report = additions_per_shard(source_root, capture_root)
    additions_total = sum(additions.values())
    if additions_total <= 0:
        raise RuntimeError("no replenishment required")

    processed: dict[tuple[str, int], set[str]] = {
        (category, shard): processed_keys(capture_root, category, shard)
        for category in CATEGORIES
        for shard in range(SHARD_COUNT)
    }
    removable: list[tuple[str, int, str]] = []
    for category in ("exit_hold", "exit_reacquire"):
        for shard in range(SHARD_COUNT):
            for row in load_jsonl(shard_manifest(source_root, category, shard)):
                key = str(row["sample_key"])
                if row.get("candidate_role") == "reserve" and key not in processed[(category, shard)]:
                    removable.append((category, shard, key))
    removable.sort(key=lambda item: stable_key(":".join(map(str, item))))
    if len(removable) < additions_total:
        raise RuntimeError(
            f"insufficient unused exit reserves: need={additions_total} have={len(removable)}"
        )
    removed = set(removable[:additions_total])

    output_rows: dict[tuple[str, int], list[dict[str, Any]]] = {}
    global_index = 0
    added_keys: set[str] = set()
    for category in CATEGORIES:
        for shard in range(SHARD_COUNT):
            rows = load_jsonl(shard_manifest(source_root, category, shard))
            retained = [
                row
                for row in rows
                if (category, shard, str(row["sample_key"])) not in removed
            ]
            if category == "always_visible" and additions[shard]:
                sources = [row for row in rows if row.get("candidate_role") == "primary"]
                sources.sort(key=lambda row: stable_key(str(row["sample_key"])))
                if len(sources) < additions[shard]:
                    raise RuntimeError(f"not enough primary sources for shard {shard}")
                for local_index, source in enumerate(sources[: additions[shard]]):
                    new_row = clone_always_visible_reserve(
                        source,
                        shard=shard,
                        local_index=local_index,
                        global_index=global_index,
                    )
                    global_index += 1
                    key = str(new_row["sample_key"])
                    if key in added_keys:
                        raise RuntimeError(f"duplicate added key: {key}")
                    added_keys.add(key)
                    retained.append(new_row)
            retained.sort(
                key=lambda row: (
                    row.get("candidate_role") != "primary",
                    int(row["ordinal"]),
                )
            )
            output_rows[(category, shard)] = retained

    all_rows = [row for rows in output_rows.values() for row in rows]
    all_keys = [str(row["sample_key"]) for row in all_rows]
    primary_rows = sum(row.get("candidate_role") == "primary" for row in all_rows)
    processed_missing = {
        f"{category}:{shard:02d}": sorted(
            processed[(category, shard)]
            - {str(row["sample_key"]) for row in output_rows[(category, shard)]}
        )
        for category in CATEGORIES
        for shard in range(SHARD_COUNT)
    }
    processed_missing = {key: value for key, value in processed_missing.items() if value}
    checks = {
        "candidate_rows_exact_74200": len(all_rows) == GLOBAL_CANDIDATE_ROWS,
        "primary_rows_exact_42000": primary_rows == GLOBAL_PRIMARY_ROWS,
        "global_sample_keys_unique": len(all_keys) == len(set(all_keys)),
        "added_equals_removed": len(added_keys) == len(removed) == additions_total,
        "processed_rows_retained": not processed_missing,
        "added_rows_no_raw_avi": all(
            row.get("raw_avi_audit") is False
            for rows in output_rows.values()
            for row in rows
            if str(row["sample_key"]) in added_keys
        ),
        "semantic_revision_preserved": all(
            row.get("semantic_revision") == SEMANTIC_REVISION for row in all_rows
        ),
        "assigned_shards_exact": all(
            int(row.get("assigned_shard", -1)) == shard
            for (category, shard), rows in output_rows.items()
            for row in rows
        ),
        "category_exact": all(
            row["active_scenario"]["visibility_design"]["class"] == category
            for (category, _shard), rows in output_rows.items()
            for row in rows
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"replenishment checks failed: {checks}; missing={processed_missing}")

    category_specs: dict[str, Any] = {}
    for category in CATEGORIES:
        old_spec = metadata["categories"][category]
        shards: list[dict[str, Any]] = []
        for shard in range(SHARD_COUNT):
            rows = output_rows[(category, shard)]
            path = shard_manifest(output_root, category, shard)
            write_jsonl(path, rows)
            primary = sum(row.get("candidate_role") == "primary" for row in rows)
            reserve = len(rows) - primary
            shards.append(
                {
                    "shard_index": shard,
                    "path": str(path.relative_to(output_root)),
                    "rows": len(rows),
                    "primary_rows": primary,
                    "reserve_rows": reserve,
                    "target_accepted_rows": int(old_spec["target_per_shard"]),
                    "sha256": sha256_file(path),
                }
            )
        category_specs[category] = {
            "accepted_target_rows": int(old_spec["accepted_target_rows"]),
            "candidate_rows": sum(item["rows"] for item in shards),
            "target_per_shard": int(old_spec["target_per_shard"]),
            "reserve_per_shard": None,
            "shards": shards,
        }

    source_metadata_sha256 = sha256_file(source_root / "MANIFEST_METADATA.json")
    provenance_root = (source_provenance_root or source_root).resolve()
    replenishment = {
        "schema_version": "xonotic-stage2-v14r4-runtime-replenishment-v1",
        "source_manifest_root": str(provenance_root),
        "source_metadata_sha256": source_metadata_sha256,
        "capture_root": str(capture_root),
        "added_always_visible_reserves": additions_total,
        "removed_unused_exit_reserves": len(removed),
        "all_processed_rows_retained": True,
        "raw_avi_retention_for_added_rows": False,
        "per_shard": {f"{shard:02d}": shard_report[shard] for shard in range(SHARD_COUNT)},
    }
    new_metadata = copy.deepcopy(metadata)
    new_metadata["categories"] = category_specs
    new_metadata["candidate_rows"] = sum(
        spec["candidate_rows"] for spec in category_specs.values()
    )
    new_metadata["source_manifest_root"] = str(provenance_root)
    new_metadata["old_artifacts_modified"] = False
    new_metadata["operational_replenishment"] = replenishment
    new_metadata["distribution_policy"]["runtime_replenishment"] = {
        "source_category": "always_visible",
        "capacity_reallocated_from": ["exit_hold", "exit_reacquire"],
        "accepted_targets_unchanged": True,
        "primary_distribution_unchanged": True,
        "raw_avi_retention_for_added_rows": False,
    }
    new_metadata["manifest_audit"] = "MANIFEST_AUDIT.json"
    audit = {
        "schema_version": "xonotic-stage2-motion-temporal-visibility-manifest-audit-v14r4-replenishment-v1",
        "passed": all(checks.values()),
        "checks": checks,
        "primary_rows": primary_rows,
        "reserve_rows": len(all_rows) - primary_rows,
        "candidate_rows": len(all_rows),
        "accepted_visibility_target": {
            category: int(spec["accepted_target_rows"])
            for category, spec in category_specs.items()
        },
        "category_specs": category_specs,
        "replenishment": replenishment,
        "old_artifacts_modified": False,
    }
    write_json(output_root / "MANIFEST_AUDIT.json", audit)
    write_json(output_root / "MANIFEST_METADATA.json", new_metadata)
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(f"{sha256_file(path)}  {path.relative_to(output_root)}\n")
    return {"output_root": str(output_root), "checks": checks, "replenishment": replenishment}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--capture-root", type=Path, default=CAPTURE_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--source-provenance-root", type=Path)
    args = parser.parse_args()
    report = build(
        args.source_root.resolve(),
        args.capture_root.resolve(),
        args.output_root.resolve(),
        args.source_provenance_root.resolve()
        if args.source_provenance_root
        else None,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
