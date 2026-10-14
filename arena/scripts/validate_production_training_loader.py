                      
"""Run stratified real-loader validation for a merged duel-v11 production release."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from validate_training_loader import DEFAULT_REFERENCE_CONFIG, sha256, validate_manifest


RANK_PATTERN = re.compile(r"_r(?P<rank>\d{3})_")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc


def stable_score(sample_id: str) -> int:
    return int(hashlib.sha256(sample_id.encode("utf-8")).hexdigest(), 16)


def row_rank(row: dict[str, Any]) -> int:
    match = RANK_PATTERN.search(str(row["episode_id"]))
    if match is None:
        raise ValueError(f"cannot parse rank from {row['episode_id']}")
    return int(match.group("rank"))


def row_categories(row: dict[str, Any]) -> set[str]:
    blocks = ((row.get("prompt_structured") or {}).get("blocks") or [])
    outside = sum(bool(block.get("fully_outside_view")) for block in blocks)
    phases = {str(block.get("visibility_phase")) for block in blocks}
    labels = {str(block.get("motion_label")) for block in blocks}
    categories: set[str] = set()
    if outside == 0:
        categories.add("fully_observed_clip")
    elif outside == len(blocks):
        categories.add("fully_outside_clip")
    else:
        categories.add("mixed_visibility_clip")
    if phases.intersection({"enter", "exit", "enter_and_exit", "exit_and_enter"}):
        categories.add("visibility_transition")
    if any(int(block.get("enemy_fire_ticks", 0)) > 0 for block in blocks):
        categories.add("enemy_fire")
    if any(bool(block.get("enemy_killed")) for block in blocks):
        categories.add("enemy_killed")
    if any(bool(block.get("player_killed")) for block in blocks):
        categories.add("player_killed")
    if any(bool(block.get("enemy_respawned")) for block in blocks):
        categories.add("enemy_respawn")
    if labels.difference({"stationary", "unobserved"}):
        categories.add("observed_motion")
    return categories


def choose_rows(
    manifest_path: Path,
    *,
    sample_count: int,
    expected_ranks: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    require(sample_count >= expected_ranks, "sample count must cover every rank")
    best_by_rank: dict[int, tuple[int, dict[str, Any], set[str]]] = {}
    best_by_bucket: dict[tuple[int, str], tuple[int, dict[str, Any], set[str]]] = {}
    overall: list[tuple[int, str, dict[str, Any], set[str]]] = []
    all_categories: Counter[str] = Counter()
    total_rows = 0

    for row in iter_jsonl(manifest_path):
        total_rows += 1
        sample_id = str(row["sample_id"])
        rank = row_rank(row)
        require(0 <= rank < expected_ranks, f"rank out of range for {sample_id}")
        categories = row_categories(row)
        score = stable_score(sample_id)
        all_categories.update(categories)
        current = best_by_rank.get(rank)
        if current is None or score < current[0]:
            best_by_rank[rank] = (score, row, categories)
        for category in categories:
            key = (rank, category)
            current = best_by_bucket.get(key)
            if current is None or score < current[0]:
                best_by_bucket[key] = (score, row, categories)
        heap_item = (-score, sample_id, row, categories)
        if len(overall) < sample_count:
            heapq.heappush(overall, heap_item)
        elif score < -overall[0][0]:
            heapq.heapreplace(overall, heap_item)

    require(set(best_by_rank) == set(range(expected_ranks)), "not every production rank is represented")
    candidates: dict[str, tuple[int, dict[str, Any], set[str]]] = {}
    for score, row, categories in best_by_rank.values():
        candidates[str(row["sample_id"])] = (score, row, categories)
    for score, row, categories in best_by_bucket.values():
        candidates[str(row["sample_id"])] = (score, row, categories)
    for neg_score, sample_id, row, categories in overall:
        candidates[sample_id] = (-neg_score, row, categories)

    selected: dict[str, tuple[int, dict[str, Any], set[str]]] = {}
    rank_coverage: Counter[int] = Counter()
    category_coverage: Counter[str] = Counter()

    def add(candidate: tuple[int, dict[str, Any], set[str]]) -> None:
        score, row, categories = candidate
        sample_id = str(row["sample_id"])
        if sample_id in selected:
            return
        selected[sample_id] = (score, row, categories)
        rank_coverage[row_rank(row)] += 1
        category_coverage.update(categories)

    for rank in range(expected_ranks):
        add(best_by_rank[rank])
    for category in sorted(all_categories):
        matching = [
            candidate for (rank, name), candidate in best_by_bucket.items() if name == category
        ]
        for candidate in sorted(matching, key=lambda item: item[0]):
            if str(candidate[1]["sample_id"]) not in selected:
                add(candidate)
                break

    remaining = sorted(
        (candidate for sample_id, candidate in candidates.items() if sample_id not in selected),
        key=lambda candidate: (
            rank_coverage[row_rank(candidate[1])],
            min((category_coverage[name] for name in candidate[2]), default=0),
            candidate[0],
        ),
    )
    for candidate in remaining:
        if len(selected) >= sample_count:
            break
        add(candidate)

    require(len(selected) == sample_count, f"selected {len(selected)}/{sample_count} loader rows")
    rows = [selected[sample_id][1] for sample_id in sorted(selected)]
    selected_categories = Counter()
    selected_ranks = Counter()
    selection_rows: list[dict[str, Any]] = []
    for row in rows:
        categories = row_categories(row)
        rank = row_rank(row)
        selected_categories.update(categories)
        selected_ranks[rank] += 1
        selection_rows.append(
            {
                "sample_id": row["sample_id"],
                "episode_id": row["episode_id"],
                "rank": rank,
                "categories": sorted(categories),
            }
        )
    report = {
        "source_manifest_rows": total_rows,
        "selected_rows": len(rows),
        "available_category_distribution": dict(sorted(all_categories.items())),
        "selected_category_distribution": dict(sorted(selected_categories.items())),
        "selected_rank_distribution": {str(key): value for key, value in sorted(selected_ranks.items())},
        "selection": selection_rows,
    }
    return rows, report


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=32)
    parser.add_argument("--expected-ranks", type=int, default=8)
    parser.add_argument("--reference-config", type=Path, default=DEFAULT_REFERENCE_CONFIG)
    args = parser.parse_args()

    release_dir = args.release_dir.resolve()
    batch_ready_path = release_dir / "BATCH_READY.json"
    training_ready_path = release_dir / "TRAINING_READY.json"
    loader_dir = release_dir / "loader_validation"
    if training_ready_path.exists():
        raise FileExistsError(f"refusing to overwrite existing readiness marker: {training_ready_path}")
    batch_ready = json.loads(batch_ready_path.read_text(encoding="utf-8"))
    require(bool(batch_ready.get("training_ready")), "batch static readiness is false")
    require(all((batch_ready.get("gates") or {}).values()), "one or more batch static gates failed")
    manifests = batch_ready["manifests"]
    manifest_hashes = batch_ready["manifest_sha256"]
    ar_manifest = Path(manifests["ar"]).resolve()
    bidir_manifest = Path(manifests["bidirectional"]).resolve()
    require(sha256(ar_manifest) == manifest_hashes["ar"], "merged AR manifest hash mismatch")
    require(sha256(bidir_manifest) == manifest_hashes["bidirectional"], "merged bidirectional manifest hash mismatch")

    reference_config = args.reference_config.resolve()
    loader_report_path = loader_dir / "LOADER_VALIDATION.json"
    selection_path = loader_dir / "SELECTION.json"
    if loader_dir.exists():
        require(loader_report_path.is_file(), f"incomplete loader validation: {loader_report_path}")
        require(selection_path.is_file(), f"missing loader selection: {selection_path}")
        loader_report = json.loads(loader_report_path.read_text(encoding="utf-8"))
        selection_report = json.loads(selection_path.read_text(encoding="utf-8"))
        ar_report = loader_report["ar"]
        bidir_report = loader_report["bidirectional"]
        require(bool(loader_report.get("all_pass")), "existing loader validation did not pass")
        require(
            str(loader_report.get("reference_config")) == str(reference_config),
            "existing loader validation used a different reference config",
        )
        require(
            str(ar_report.get("manifest_sha256")) == manifest_hashes["ar"],
            "existing AR loader validation is stale",
        )
        require(
            str(bidir_report.get("manifest_sha256")) == manifest_hashes["bidirectional"],
            "existing bidirectional loader validation is stale",
        )
        print(f"existing_real_loader_validation_reused samples={args.sample_count}", flush=True)
    else:
        selected_ar, selection_report = choose_rows(
            ar_manifest,
            sample_count=args.sample_count,
            expected_ranks=args.expected_ranks,
        )
        wanted = {str(row["sample_id"]) for row in selected_ar}
        selected_bidir = [
            row for row in iter_jsonl(bidir_manifest) if str(row["sample_id"]) in wanted
        ]
        require(len(selected_bidir) == args.sample_count, "bidirectional loader subset is incomplete")
        require(
            {str(row["sample_id"]) for row in selected_bidir} == wanted,
            "loader subset ids differ",
        )
        loader_dir.mkdir(parents=True)
        write_json(selection_path, selection_report)
        ar_report = validate_manifest(
            ar_manifest, selected_ar, loader_dir, reference_config, ar_mode=True
        )
        print(f"ar_real_loader_ok samples={args.sample_count}", flush=True)
        bidir_report = validate_manifest(
            bidir_manifest, selected_bidir, loader_dir, reference_config, ar_mode=False
        )
        print(f"bidirectional_real_loader_ok samples={args.sample_count}", flush=True)
        loader_report = {
            "schema_version": "xonotic-duel-v11-production-real-loader-validation-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reference_config": str(reference_config),
            "reference_config_sha256": sha256(reference_config),
            "selection": selection_report,
            "ar": ar_report,
            "bidirectional": bidir_report,
            "all_pass": bool(ar_report["all_pass"] and bidir_report["all_pass"]),
        }
        write_json(loader_report_path, loader_report)

    available_categories = set(selection_report["available_category_distribution"])
    selected_categories = set(selection_report["selected_category_distribution"])
    gates = {
        "batch_static_gates_all_pass": bool(batch_ready.get("training_ready"))
        and all((batch_ready.get("gates") or {}).values()),
        "merged_manifest_hashes_match": True,
        "stratified_selection_covers_all_eight_ranks": set(
            selection_report["selected_rank_distribution"]
        ) == {str(index) for index in range(args.expected_ranks)},
        "stratified_selection_covers_all_observed_categories": selected_categories
        == available_categories,
        "real_loader_ar_all_pass": bool(ar_report["all_pass"])
        and int(ar_report["dataset_rows"]) == args.sample_count,
        "real_loader_bidirectional_all_pass": bool(bidir_report["all_pass"])
        and int(bidir_report["dataset_rows"]) == args.sample_count,
        "real_loader_ar_bidirectional_sample_ids_match": {
            result["sample_id"] for result in ar_report["results"]
        }
        == {result["sample_id"] for result in bidir_report["results"]},
    }
    final_ready = {
        "schema_version": "xonotic-duel-v11-production-training-ready-v1",
        "production_run_id": batch_ready["production_run_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_ready": bool(all(gates.values())),
        "counts": batch_ready["counts"],
        "gates": gates,
        "batch_ready": {
            "path": str(batch_ready_path),
            "sha256": sha256(batch_ready_path),
        },
        "loader_validation": {
            "path": str(loader_report_path),
            "sha256": sha256(loader_report_path),
            "ar_samples": args.sample_count,
            "bidirectional_samples": args.sample_count,
        },
        "manifests": manifests,
        "manifest_sha256": manifest_hashes,
    }
    write_json(training_ready_path, final_ready)
    print(json.dumps(final_ready, indent=2, ensure_ascii=False), flush=True)
    return 0 if final_ready["training_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
