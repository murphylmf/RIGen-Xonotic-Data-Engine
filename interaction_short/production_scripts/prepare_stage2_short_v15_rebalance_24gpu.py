                      
"""Freeze and split the remaining Stage-2 short v15 work into 24 lanes."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_ROOT = ROOT / (
    "manifests/stage2_short_42k_v15_random_fire_visualfix_"
    "28shard_20260824_r1"
)
LANE_SCHEMA = "xonotic-stage2-short-v15-rebalance-lane-v1"
PLAN_SCHEMA = "xonotic-stage2-short-v15-rebalance-plan-v1"
EXPECTED_CATEGORIES = ("exit_reacquire", "exit_hold", "always_visible")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"non-object JSONL row {path}:{line_number}")
            rows.append(value)
    return rows


def unique_keys(rows: Iterable[dict[str, Any]], path: Path) -> set[str]:
    keys = [str(row.get("sample_key", "")) for row in rows]
    if not all(keys) or len(keys) != len(set(keys)):
        raise RuntimeError(f"missing or duplicate sample keys: {path}")
    return set(keys)


def balance_signature(row: dict[str, Any]) -> tuple[str, ...]:
    active = row["active_scenario"]
    budget = row.get("budget_token") or {}
    motion = active.get("enemy_motion_program") or {}
    fire = (active.get("causal_design") or {}).get("fire_program") or {}
    return (
        str(row.get("candidate_role")),
        str(active.get("intent_outcome")),
        str(active.get("weapon")),
        str(active.get("distance_tier")),
        str(budget.get("player_motion_class")),
        str(fire.get("name")),
        ",".join(str(value) for value in motion.get("direction_codes", [])),
    )


def split_candidates(
    rows: list[dict[str, Any]], seed: str
) -> tuple[list[str], list[str]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        groups[balance_signature(row)].append(row)
    lanes: tuple[list[str], list[str]] = ([], [])
    for signature in sorted(groups):
        group = sorted(
            groups[signature],
            key=lambda row: hashlib.sha256(
                f"{seed}:{row['sample_key']}".encode("utf-8")
            ).hexdigest(),
        )
        start = min(range(2), key=lambda index: (len(lanes[index]), index))
        for offset, row in enumerate(group):
            lanes[(start + offset) % 2].append(str(row["sample_key"]))
    for lane in lanes:
        lane.sort()
    return lanes


def journal_snapshot(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "exists": path.is_file(),
        "rows": len(rows),
        "sha256": sha256_file(path) if path.is_file() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.is_file() else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-output-root", type=Path, required=True)
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument("--physical-lanes", type=int, default=24)
    parser.add_argument("--expected-incomplete-shards", type=int, default=12)
    parser.add_argument("--minimum-candidate-headroom", type=float, default=1.25)
    args = parser.parse_args()

    source_output = args.source_output_root.resolve()
    manifest_root = args.manifest_root.resolve()
    plan_root = args.plan_root.resolve()
    if not source_output.is_dir():
        raise RuntimeError(f"missing source output root: {source_output}")
    if not manifest_root.is_dir():
        raise RuntimeError(f"missing manifest root: {manifest_root}")
    if plan_root.exists():
        raise RuntimeError(f"refusing to overwrite rebalance plan: {plan_root}")
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (
        metadata.get("semantic_revision")
        != "v15_random_fire_visualfix_nocrosshair_nocasings"
        or int(metadata.get("shard_count", -1)) != 28
        or int(metadata.get("rendered_episode_rows", -1)) != 42_000
    ):
        raise RuntimeError("source manifest is not the audited v15 42k release")

    category_metadata = metadata.get("categories") or {}
    if set(category_metadata) != set(EXPECTED_CATEGORIES):
        raise RuntimeError(f"unexpected categories: {sorted(category_metadata)}")

    frozen_utc = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    completed_categories: dict[str, int] = {}
    source_accepted_total = 0
    incomplete: list[dict[str, Any]] = []
    source_snapshots: list[dict[str, Any]] = []

    for category in EXPECTED_CATEGORIES:
        accepted_category = 0
        declared_shards = sorted(
            category_metadata[category]["shards"],
            key=lambda value: int(value["shard_index"]),
        )
        for declared in declared_shards:
            shard = int(declared["shard_index"])
            manifest_path = (manifest_root / str(declared["path"])).resolve()
            if sha256_file(manifest_path) != str(declared["sha256"]):
                raise RuntimeError(f"manifest hash drift: {manifest_path}")
            manifest_rows = load_jsonl(manifest_path)
            manifest_keys = unique_keys(manifest_rows, manifest_path)
            shard_root = source_output / category / f"shard_{shard:02d}"
            accepted_path = shard_root / "manifests/accepted.jsonl"
            rejected_path = shard_root / "manifests/rejected.jsonl"
            accepted_rows = load_jsonl(accepted_path)
            rejected_rows = load_jsonl(rejected_path)
            accepted_keys = unique_keys(accepted_rows, accepted_path) if accepted_rows else set()
            rejected_keys = unique_keys(rejected_rows, rejected_path) if rejected_rows else set()
            if accepted_keys & rejected_keys:
                raise RuntimeError(f"accepted/rejected overlap: {category} shard={shard}")
            if not accepted_keys <= manifest_keys or not rejected_keys <= manifest_keys:
                raise RuntimeError(f"journal key outside manifest: {category} shard={shard}")
            target = int(declared["target_accepted_rows"])
            if len(accepted_keys) > target:
                raise RuntimeError(f"accepted target overshoot: {category} shard={shard}")
            accepted_category += len(accepted_keys)
            source_accepted_total += len(accepted_keys)
            source_snapshots.append(
                {
                    "category": category,
                    "shard": shard,
                    "target": target,
                    "accepted": journal_snapshot(accepted_path, accepted_rows),
                    "rejected": journal_snapshot(rejected_path, rejected_rows),
                }
            )
            remaining = target - len(accepted_keys)
            if remaining == 0:
                continue
            if category != "always_visible":
                raise RuntimeError(
                    f"only always_visible may remain: {category} shard={shard} remaining={remaining}"
                )
            pending_rows = [
                row
                for row in manifest_rows
                if str(row["sample_key"]) not in accepted_keys
                and str(row["sample_key"]) not in rejected_keys
            ]
            if len(pending_rows) < remaining:
                raise RuntimeError(
                    f"insufficient pending candidates: shard={shard} "
                    f"pending={len(pending_rows)} target={remaining}"
                )
            incomplete.append(
                {
                    "category": category,
                    "shard": shard,
                    "target": target,
                    "accepted": len(accepted_keys),
                    "rejected": len(rejected_keys),
                    "remaining": remaining,
                    "manifest": manifest_path,
                    "manifest_sha256": str(declared["sha256"]),
                    "pending_rows": pending_rows,
                }
            )
        declared_category_target = int(category_metadata[category]["accepted_target_rows"])
        if accepted_category == declared_category_target:
            completed_categories[category] = accepted_category

    if len(incomplete) != args.expected_incomplete_shards:
        raise RuntimeError(
            f"expected {args.expected_incomplete_shards} incomplete shards, got {len(incomplete)}"
        )
    if args.physical_lanes != len(incomplete) * 2:
        raise RuntimeError(
            f"two-way split requires {len(incomplete) * 2} lanes, got {args.physical_lanes}"
        )

    plan_root.mkdir(parents=True, exist_ok=False)
    lanes_root = plan_root / "lanes"
    lanes_root.mkdir()
    lane_entries: list[dict[str, Any]] = []
    lane_id = 0
    remaining_total = 0
    for item in incomplete:
        candidate_splits = split_candidates(
            item["pending_rows"],
            seed=f"v15-rebalance:{frozen_utc}:shard-{item['shard']:02d}",
        )
        first_target = item["remaining"] // 2
        targets = (first_target, item["remaining"] - first_target)
        for split_index, (keys, target) in enumerate(zip(candidate_splits, targets)):
            headroom = len(keys) / target
            if headroom < args.minimum_candidate_headroom:
                raise RuntimeError(
                    f"insufficient lane headroom: shard={item['shard']} split={split_index} "
                    f"candidates={len(keys)} target={target} ratio={headroom:.3f}"
                )
            key_digest = hashlib.sha256(
                ("\n".join(keys) + "\n").encode("utf-8")
            ).hexdigest()
            lane = {
                "schema_version": LANE_SCHEMA,
                "lane_id": lane_id,
                "split_index": split_index,
                "category": item["category"],
                "original_shard": item["shard"],
                "source_manifest": str(item["manifest"]),
                "source_manifest_sha256": item["manifest_sha256"],
                "source_output_root": str(source_output),
                "frozen_utc": frozen_utc,
                "source_shard_accepted": item["accepted"],
                "source_shard_rejected": item["rejected"],
                "source_shard_remaining_target": item["remaining"],
                "candidate_rows": len(keys),
                "target_accepted_rows": target,
                "candidate_headroom_ratio": headroom,
                "candidate_sample_keys_sha256": key_digest,
                "candidate_sample_keys": keys,
            }
            lane_path = lanes_root / f"lane_{lane_id:03d}.json"
            atomic_json(lane_path, lane)
            lane_entries.append(
                {
                    "lane_id": lane_id,
                    "split_index": split_index,
                    "category": item["category"],
                    "original_shard": item["shard"],
                    "source_manifest": str(item["manifest"]),
                    "source_manifest_sha256": item["manifest_sha256"],
                    "candidate_rows": len(keys),
                    "target_accepted_rows": target,
                    "candidate_headroom_ratio": headroom,
                    "path": str(lane_path),
                    "sha256": sha256_file(lane_path),
                }
            )
            remaining_total += target
            lane_id += 1

    if source_accepted_total + remaining_total != 42_000:
        raise RuntimeError(
            f"global target mismatch: {source_accepted_total}+{remaining_total}!=42000"
        )
    assigned_keys = [
        key
        for lane_path in sorted(lanes_root.glob("lane_*.json"))
        for key in json.loads(lane_path.read_text(encoding="utf-8"))[
            "candidate_sample_keys"
        ]
    ]
    if len(assigned_keys) != len(set(assigned_keys)):
        raise RuntimeError("candidate key assigned to more than one rebalance lane")

    plan = {
        "schema_version": PLAN_SCHEMA,
        "frozen_utc": frozen_utc,
        "manifest_root": str(manifest_root),
        "manifest_metadata": str(metadata_path.resolve()),
        "manifest_metadata_sha256": sha256_file(metadata_path),
        "source_output_root": str(source_output),
        "source_accepted_total": source_accepted_total,
        "remaining_target_total": remaining_total,
        "final_target_total": 42_000,
        "completed_categories": completed_categories,
        "incomplete_original_shards": [item["shard"] for item in incomplete],
        "physical_lanes": args.physical_lanes,
        "split_policy": "two_disjoint_stratified_candidate_sets_per_incomplete_shard",
        "minimum_candidate_headroom": args.minimum_candidate_headroom,
        "source_journal_snapshots": source_snapshots,
        "lanes": lane_entries,
    }
    plan_path = plan_root / "PLAN.json"
    atomic_json(plan_path, plan)
    print(
        json.dumps(
            {
                "plan": str(plan_path),
                "plan_sha256": sha256_file(plan_path),
                "source_accepted_total": source_accepted_total,
                "remaining_target_total": remaining_total,
                "lanes": len(lane_entries),
                "target_min": min(row["target_accepted_rows"] for row in lane_entries),
                "target_max": max(row["target_accepted_rows"] for row in lane_entries),
                "candidate_headroom_min": min(
                    row["candidate_headroom_ratio"] for row in lane_entries
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
