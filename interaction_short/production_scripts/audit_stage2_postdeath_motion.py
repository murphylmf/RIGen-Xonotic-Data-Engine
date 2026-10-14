                      
"""Audit accepted Stage-2 episodes for controller motion after enemy death.

This is deliberately read-only with respect to captured episodes.  It resolves
the immutable record paths from accepted journals and writes a versioned audit
that can be used to select only defective cases for recapture.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


DEFAULT_RUN_ROOT = Path(
    "./xonotic_workspace"
    "stage2_motion_near5_combo_40k_v10_activeonly_28gpu_20260818_01"
)
DEFAULT_OUTPUT_ROOT = Path(
    "./xonotic_workspace"
    "postdeath_motion_v10_stop_20260818_r2"
)
WORLD_POSITION_TOLERANCE_UNITS = 0.10
WORLD_SPEED_TOLERANCE_UNITS_PER_SECOND = 0.10


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def accepted_kill_records(run_root: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for journal in sorted(run_root.glob("shard_*/manifests/accepted.jsonl")):
        for line in journal.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            accepted = json.loads(line)
            if accepted.get("actual_outcome") != "kill":
                continue
            record = read_json(Path(accepted["record_path"]))
            selected[str(accepted["sample_key"])] = (accepted, record)
    return [selected[key] for key in sorted(selected)]


def xy_norm(vector: list[float] | None) -> float:
    if not vector:
        return 0.0
    return math.hypot(float(vector[0]), float(vector[1]))


def xyz_norm(vector: list[float] | None) -> float:
    if not vector:
        return 0.0
    return math.sqrt(sum(float(value) ** 2 for value in vector))


def audit_one(item: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    accepted, record = item
    state_path = Path(record["state_path"])
    rows = pq.read_table(
        state_path,
        columns=[
            "server_tick",
            "enemy.present",
            "enemy.origin",
            "enemy.velocity",
            "enemy.health",
        ],
    ).to_pylist()
    dead = [
        row
        for row in rows
        if int(row["server_tick"]) >= 64
        and int(row["enemy.present"] or 0) == 1
        and float(row["enemy.health"] or 0.0) <= 0.0
    ]
    if not dead:
        return {
            "sample_key": accepted["sample_key"],
            "sample_id": record["sample_id"],
            "ordinal": int(record["ordinal"]),
            "state_path": str(state_path),
            "status": "kill_without_dead_state_rows",
            "affected": True,
        }
    first = dead[0]
    origin0 = first["enemy.origin"]
    xy_displacements = [
        math.hypot(
            float(row["enemy.origin"][0]) - float(origin0[0]),
            float(row["enemy.origin"][1]) - float(origin0[1]),
        )
        for row in dead
    ]
    xyz_displacements = [
        math.dist(
            [float(value) for value in row["enemy.origin"]],
            [float(value) for value in origin0],
        )
        for row in dead
    ]
    xy_speeds = [xy_norm(row["enemy.velocity"]) for row in dead]
    xyz_speeds = [xyz_norm(row["enemy.velocity"]) for row in dead]
    affected = (
        max(xyz_displacements, default=0.0) > WORLD_POSITION_TOLERANCE_UNITS
        or max(xyz_speeds, default=0.0) > WORLD_SPEED_TOLERANCE_UNITS_PER_SECOND
    )
    return {
        "sample_key": accepted["sample_key"],
        "sample_id": record["sample_id"],
        "ordinal": int(record["ordinal"]),
        "acceptance_source": accepted.get("acceptance_source"),
        "map": record.get("map"),
        "weapon": record.get("weapon"),
        "enemy_motion": record.get("enemy_motion"),
        "player_motion_class": record.get("player_motion_class"),
        "state_path": str(state_path),
        "death_server_tick": int(first["server_tick"]),
        "postdeath_rows": len(dead),
        "maximum_postdeath_xy_displacement_units": max(xy_displacements, default=0.0),
        "maximum_postdeath_xyz_displacement_units": max(xyz_displacements, default=0.0),
        "maximum_postdeath_xy_speed_units_per_second": max(xy_speeds, default=0.0),
        "maximum_postdeath_xyz_speed_units_per_second": max(xyz_speeds, default=0.0),
        "position_tolerance_units": WORLD_POSITION_TOLERANCE_UNITS,
        "speed_tolerance_units_per_second": WORLD_SPEED_TOLERANCE_UNITS_PER_SECOND,
        "status": "postdeath_controller_motion" if affected else "postdeath_locked",
        "affected": affected,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    work = accepted_kill_records(args.run_root)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(audit_one, work))
    rows.sort(key=lambda row: int(row["ordinal"]))

    args.output_root.mkdir(parents=True, exist_ok=False)
    details_path = args.output_root / "kill_cases.jsonl"
    affected_path = args.output_root / "affected_sample_keys.txt"
    details_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    affected = [row for row in rows if row["affected"]]
    affected_path.write_text(
        "".join(str(row["sample_key"]) + "\n" for row in affected),
        encoding="utf-8",
    )
    summary = {
        "schema_version": "xonotic-stage2-postdeath-motion-audit-v1",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_run_root": str(args.run_root),
        "accepted_kill_rows": len(rows),
        "affected_rows": len(affected),
        "locked_rows": sum(row["status"] == "postdeath_locked" for row in rows),
        "other_status_rows": dict(Counter(row["status"] for row in rows)),
        "affected_by_enemy_motion": dict(
            sorted(Counter(str(row.get("enemy_motion")) for row in affected).items())
        ),
        "affected_by_acceptance_source": dict(
            sorted(Counter(str(row.get("acceptance_source")) for row in affected).items())
        ),
        "maximum_observed_postdeath_xyz_displacement_units": max(
            (float(row.get("maximum_postdeath_xyz_displacement_units", 0.0)) for row in rows),
            default=0.0,
        ),
        "maximum_observed_postdeath_xyz_speed_units_per_second": max(
            (float(row.get("maximum_postdeath_xyz_speed_units_per_second", 0.0)) for row in rows),
            default=0.0,
        ),
        "details_path": str(details_path),
        "affected_sample_keys_path": str(affected_path),
    }
    (args.output_root / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
