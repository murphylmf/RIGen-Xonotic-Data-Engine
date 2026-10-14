                      
"""Freeze completed rank ledgers and balance the exact missing episode IDs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--expected-episodes", type=int, default=1800)
    parser.add_argument("--expected-ranks", type=int, default=8)
    parser.add_argument("--rebalance-name", default="rebalance_v1")
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    if run_root.name == "" or not (run_root / "ranks").is_dir():
        raise ValueError(f"invalid production run root: {run_root}")
    if args.expected_episodes < 1 or args.expected_ranks < 1:
        raise ValueError("expected episode and rank counts must be positive")

    rebalance_root = run_root / args.rebalance_name
    rebalance_root.mkdir(parents=True, exist_ok=True)
    pause_path = rebalance_root / "PAUSE"
    if not pause_path.exists():
        raise FileNotFoundError(
            f"refusing an unfrozen snapshot; create the pause marker first: {pause_path}"
        )
    ready_path = rebalance_root / "READY.json"
    if ready_path.exists() or any(rebalance_root.glob("rank_*.json")):
        raise FileExistsError(f"rebalance contracts already exist: {rebalance_root}")

    rows_by_rank: list[list[dict[str, Any]]] = []
    all_indices: list[int] = []
    for rank in range(args.expected_ranks):
        rank_root = run_root / "ranks" / f"rank_{rank:03d}"
        ledger_path = rank_root / "completed_batches.jsonl"
        rank_rows: list[dict[str, Any]] = []
        ledger_accepted = 0
        for ledger_row in jsonl(ledger_path):
            accepted = int(ledger_row["accepted_episodes"])
            shard_path = Path(ledger_row["accepted_shard"]).resolve()
            if not shard_path.is_relative_to(rank_root.resolve()):
                raise ValueError(f"accepted shard escapes rank root: {shard_path}")
            shard_rows = list(jsonl(shard_path))
            if len(shard_rows) != accepted:
                raise ValueError(
                    f"accepted shard count mismatch: {shard_path}: {len(shard_rows)} != {accepted}"
                )
            ledger_accepted += accepted
            rank_rows.extend(shard_rows)

        if len(rank_rows) != ledger_accepted:
            raise AssertionError("ledger count changed while taking rebalance snapshot")
        for row in rank_rows:
            if row.get("production_run_id") != run_root.name:
                raise ValueError(f"run ID mismatch in rank {rank}")
            if int(row.get("global_rank", -1)) != rank:
                raise ValueError(f"producer rank mismatch in rank {rank}")
            if int(row.get("global_world", -1)) != args.expected_ranks:
                raise ValueError(f"world mismatch in rank {rank}")
            if not bool(row.get("training_ready")):
                raise ValueError(f"non-ready accepted episode in rank {rank}")
            episode_index = int(row.get("global_episode_index", -1))
            if not 0 <= episode_index < args.expected_episodes:
                raise ValueError(f"episode index outside target range: {episode_index}")
            all_indices.append(episode_index)
        rows_by_rank.append(rank_rows)

    existing = sorted(all_indices)
    if len(existing) != len(set(existing)):
        raise ValueError("duplicate accepted global episode indices before rebalance")
    expected = set(range(args.expected_episodes))
    missing = sorted(expected.difference(existing))
    assignments = [missing[rank :: args.expected_ranks] for rank in range(args.expected_ranks)]
    assignment_union = sorted(index for values in assignments for index in values)

    base_counts = [len(rows) for rows in rows_by_rank]
    assignment_counts = [len(values) for values in assignments]
    targets = [base + extra for base, extra in zip(base_counts, assignment_counts)]
    gates = {
        "all_existing_indices_unique": len(existing) == len(set(existing)),
        "assignments_cover_exact_missing_indices": assignment_union == missing,
        "balanced_assignment_counts": max(assignment_counts, default=0)
        - min(assignment_counts, default=0)
        <= 1,
        "final_episode_count_exact": sum(targets) == args.expected_episodes,
    }
    if not all(gates.values()):
        raise AssertionError(f"rebalance gates failed: {gates}")

    created_at = datetime.now(timezone.utc).isoformat()
    contract_hashes: dict[str, str] = {}
    for rank, episode_indices in enumerate(assignments):
        contract_path = rebalance_root / f"rank_{rank:03d}.json"
        contract = {
            "schema_version": "xonotic-duel-v12-rebalance-rank-v1",
            "rebalance_id": args.rebalance_name,
            "created_at": created_at,
            "run_id": run_root.name,
            "rank": rank,
            "world": args.expected_ranks,
            "total_episodes": args.expected_episodes,
            "base_completed": base_counts[rank],
            "target_episodes": targets[rank],
            "episode_indices": episode_indices,
        }
        atomic_json(contract_path, contract)
        contract_hashes[f"rank_{rank:03d}"] = sha256(contract_path)

    ready = {
        "schema_version": "xonotic-duel-v12-rebalance-ready-v1",
        "rebalance_id": args.rebalance_name,
        "created_at": created_at,
        "run_id": run_root.name,
        "expected_ranks": args.expected_ranks,
        "expected_episodes": args.expected_episodes,
        "snapshot": {
            "completed_episodes": len(existing),
            "missing_episodes": len(missing),
            "base_counts": base_counts,
            "assignment_counts": assignment_counts,
            "rank_targets": targets,
        },
        "contract_sha256": contract_hashes,
        "gates": gates,
    }
    atomic_json(ready_path, ready)
    print(json.dumps(ready, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
