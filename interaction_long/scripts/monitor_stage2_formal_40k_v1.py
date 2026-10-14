                      
"""Aggregate incremental Stage-2 formal production progress and QA."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xonotic_capture as capture              
import stage2_target_outcome_labels as target_labels              


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_journals(output_root: Path, name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            f"shard-*-of-*/{name}.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def monitor(shard_count: int, cohort: str, output_root: Path) -> dict:
    count_padded = f"{shard_count:03d}"
    manifest_root = (
        ROOT / f"manifests/stage2_formal_40k_v1/{cohort}"
    )
    planned: list[dict] = []
    shard_by_episode: dict[str, int] = {}
    for shard_index in range(shard_count):
        path = (
            manifest_root
            / f"shards-{count_padded}"
            / f"shard-{shard_index:03d}-of-{count_padded}.jsonl"
        )
        rows = capture.load_jsonl(path)
        planned.extend(rows)
        shard_by_episode.update(
            {row["episode_id"]: shard_index for row in rows}
        )
    accepted_rows = target_labels.apply_current_labels(
        output_root.resolve(), load_journals(output_root, "accepted")
    )
    reject_rows = load_journals(output_root, "rejects")
    accepted_counts = Counter(row["episode_id"] for row in accepted_rows)
    accepted = {
        row["episode_id"]: row for row in accepted_rows
    }
    terminal_rows = [
        row for row in reject_rows if row.get("terminal") is True
    ]
    terminal = {row["episode_id"]: row for row in terminal_rows}
    actual_outcomes = Counter(
        (row.get("stage2_causal") or {}).get("actual_outcome", "missing")
        for row in accepted.values()
    )
    recipe_actual: defaultdict[str, Counter[str]] = defaultdict(Counter)
    planned_by_id = {row["episode_id"]: row for row in planned}
    weapon_shots: defaultdict[str, Counter[str]] = defaultdict(Counter)
    observation_complete = 0
    right_censored = 0
    hard_qa_passed = 0
    for episode_id, row in accepted.items():
        scenario = planned_by_id.get(episode_id) or {}
        recipe = (scenario.get("formal_design") or {}).get(
            "outcome_recipe", "missing"
        )
        causal = row.get("stage2_causal") or {}
        actual = causal.get("actual_outcome", "missing")
        recipe_actual[recipe][actual] += 1
        per_shot = causal.get("per_shot") or {}
        weapon = row.get("weapon", "missing")
        weapon_shots[weapon]["fires"] += int(per_shot.get("rows", 0))
        weapon_shots[weapon]["hits"] += int(
            per_shot.get("target_hit_count", 0)
        )
        checks = per_shot.get("target_label_checks") or {}
        observation_complete += int(
            checks.get("observation_complete") is True
        )
        right_censored += int(checks.get("not_right_censored") is not True)
        hard_qa_passed += int(
            (row.get("qa") or {}).get("hard_gates_pass") is True
        )
    publish_times = [
        parse_time(row["published_utc"])
        for row in accepted.values()
        if row.get("published_utc")
    ]
    run_metadata = list(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/RUN_METADATA.json"
        )
    )
    starts = []
    for path in run_metadata:
        payload = json.loads(path.read_text())
        if payload.get("started_utc"):
            starts.append(parse_time(payload["started_utc"]))
    now = dt.datetime.now(dt.timezone.utc)
    start = min(starts) if starts else None
    elapsed_hours = (
        max((now - start).total_seconds() / 3600.0, 1e-9)
        if start
        else None
    )
    rate = (
        len(accepted) / elapsed_hours if elapsed_hours is not None else 0.0
    )
    remaining = len(planned) - len(accepted) - len(terminal)
    eta_hours = remaining / rate if rate > 0 else None
    per_rank = {}
    for shard_index in range(shard_count):
        planned_rank = sum(
            value == shard_index for value in shard_by_episode.values()
        )
        accepted_rank = sum(
            shard_by_episode.get(episode_id) == shard_index
            for episode_id in accepted
        )
        terminal_rank = sum(
            shard_by_episode.get(episode_id) == shard_index
            for episode_id in terminal
        )
        per_rank[str(shard_index)] = {
            "planned": planned_rank,
            "accepted": accepted_rank,
            "terminal": terminal_rank,
            "remaining": planned_rank - accepted_rank - terminal_rank,
        }
    result = {
        "schema_version": "xonotic-stage2-formal-incremental-audit-v1",
        "cohort": cohort,
        "shard_count": shard_count,
        "planned": len(planned),
        "accepted": len(accepted),
        "terminal": len(terminal),
        "remaining": remaining,
        "retry_attempts": len(reject_rows) - len(terminal_rows),
        "accepted_duplicates": sorted(
            episode_id
            for episode_id, value in accepted_counts.items()
            if value != 1
        ),
        "accepted_terminal_conflicts": sorted(
            set(accepted) & set(terminal)
        ),
        "actual_outcome_distribution": dict(actual_outcomes),
        "recipe_actual_matrix": {
            key: dict(value)
            for key, value in sorted(recipe_actual.items())
        },
        "weapon_per_fire": {
            weapon: {
                "fires": values["fires"],
                "hits": values["hits"],
                "hit_rate": (
                    values["hits"] / values["fires"]
                    if values["fires"]
                    else None
                ),
            }
            for weapon, values in sorted(weapon_shots.items())
        },
        "accepted_hard_qa_passed": hard_qa_passed,
        "accepted_target_observation_complete": observation_complete,
        "accepted_right_censored": right_censored,
        "elapsed_hours": elapsed_hours,
        "accepted_episodes_per_hour": rate,
        "accepted_data_hours_per_wall_hour": rate * 5.0 / 3600.0,
        "eta_hours": eta_hours,
        "per_rank": per_rank,
        "terminal_episode_ids": sorted(terminal),
        "complete": len(accepted) == len(planned)
        and not terminal
        and not (set(accepted) & set(terminal)),
    }
    atomic_json(output_root / "INCREMENTAL_AUDIT.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-count", type=int, choices=(32, 56), required=True)
    parser.add_argument(
        "--cohort", choices=("primary", "reserve"), default="primary"
    )
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    output_root = args.output_root or (
        ROOT
        / f"stage2_formal_40k_v1_output/{args.shard_count}x1/{args.cohort}"
    )
    result = monitor(
        args.shard_count, args.cohort, output_root.resolve()
    )
    print(
        capture.canonical_json(
            {
                "accepted": result["accepted"],
                "terminal": result["terminal"],
                "remaining": result["remaining"],
                "episodes_per_hour": result[
                    "accepted_episodes_per_hour"
                ],
                "eta_hours": result["eta_hours"],
                "complete": result["complete"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
