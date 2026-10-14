                      
"""Plan, calibrate, freeze, and replay Stage-1 waypoint routes.

The planner consumes only the pinned official waypoint graph.  Calibration is
an authoritative 64 Hz server run whose closed-loop usercmds are frozen before
the independent full render replay.
"""

from __future__ import annotations

import argparse
import csv
import functools
import json
import math
import os
import random
import re
import shutil
import sys
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              


ROOT = capture.ROOT
ROUTE_ROOT = ROOT / "stage1_routes"
PLAN_ROOT = ROUTE_ROOT / "plans"
CALIBRATION_ROOT = ROUTE_ROOT / "calibration"
REGRESSION_ROOT = ROUTE_ROOT / "regression"
PLAN_INDEX = ROUTE_ROOT / "ROUTE_PLAN_INDEX.jsonl"
REPORT_PATH = ROUTE_ROOT / "STAGE1_ROUTE_REPORT.json"
PREFLIGHT_PATH = ROOT / "preflight_v2/PREFLIGHT_REPORT.json"
MAP_ARCHIVE = (
    ROOT
    / "assets/release-0.8.6/Xonotic/data/xonotic-20230620-maps.pk3"
)
MAP_ARCHIVE_SHA256 = (
    "d10e5a8eac468a4a5b6d80f9603d95949971c6b10f86bec65a79e19f0d424f54"
)
VECTOR_RE = re.compile(
    r"^\s*'?\s*(-?[0-9]+(?:\.[0-9]+)?)\s+"
    r"(-?[0-9]+(?:\.[0-9]+)?)\s+"
    r"(-?[0-9]+(?:\.[0-9]+)?)\s*'?\s*$"
)
EDGE_RE = re.compile(r"^\s*'([^']+)'\*'([^']+)'\s*$")
WAYPOINT_ID_RE = re.compile(r"_wp([0-9]{4})$")
PAIR_WAYPOINT_ID_RE = re.compile(
    r"_wp([0-9]{4})_wp([0-9]{4})$"
)
EXCLUDED_MAPS = {"nexballarena"}


@dataclass(frozen=True)
class WaypointGraph:
    map_name: str
    gametype: str
    waypoint_member: str
    cache_member: str
    nodes: tuple[tuple[float, float, float], ...]
    flags: tuple[int, ...]
    adjacency: tuple[tuple[int, ...], ...]
    edge_count: int
    unmatched_edges: int
    waypoint_sha256: str
    cache_sha256: str


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def relative_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def vector(text: str) -> tuple[float, float, float]:
    match = VECTOR_RE.match(text)
    if not match:
        raise capture.CaptureFailure("invalid_waypoint_vector", text)
    return tuple(float(match.group(index)) for index in range(1, 4))


def coordinate_key(
    value: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(round(component, 3) for component in value)


def graph_members(
    archive: zipfile.ZipFile, map_name: str, gametype: str
) -> tuple[str, str]:
    waypoint_extension = (
        "race" if gametype in {"race", "rc"} else gametype
    )
    specific = f"maps/{map_name}.{waypoint_extension}.waypoints"
    generic = f"maps/{map_name}.waypoints"
    names = set(archive.namelist())
    waypoint = specific if specific in names else generic
    cache = f"{waypoint}.cache"
    if waypoint not in names or cache not in names:
        raise capture.CaptureFailure(
            "official_waypoint_graph_missing",
            f"map={map_name} gametype={gametype}",
        )
    return waypoint, cache


@functools.lru_cache(maxsize=1)
def verify_map_archive() -> None:
    observed = capture.sha256_file(MAP_ARCHIVE)
    if observed != MAP_ARCHIVE_SHA256:
        raise capture.CaptureFailure(
            "official_map_archive_sha256_mismatch",
            f"expected={MAP_ARCHIVE_SHA256} actual={observed}",
        )


def load_graph(map_name: str, gametype: str) -> WaypointGraph:
    verify_map_archive()
    with zipfile.ZipFile(MAP_ARCHIVE) as archive:
        waypoint_member, cache_member = graph_members(
            archive, map_name, gametype
        )
        waypoint_bytes = archive.read(waypoint_member)
        cache_bytes = archive.read(cache_member)
    waypoint_lines = [
        line.strip()
        for line in waypoint_bytes.decode(
            "utf-8", errors="strict"
        ).splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]
    if len(waypoint_lines) % 3:
        raise capture.CaptureFailure(
            "invalid_waypoint_triplets", waypoint_member
        )
    nodes: list[tuple[float, float, float]] = []
    flags: list[int] = []
    for offset in range(0, len(waypoint_lines), 3):
        minimum = vector(waypoint_lines[offset])
        maximum = vector(waypoint_lines[offset + 1])
                                                                       
                                                                           
        origin = tuple(
            (minimum[axis] + maximum[axis]) / 2.0
            for axis in range(3)
        )
        nodes.append(origin)
        flags.append(int(waypoint_lines[offset + 2]))

    by_coordinate = {
        coordinate_key(origin): index
        for index, origin in enumerate(nodes)
    }
    adjacency: list[set[int]] = [set() for _ in nodes]
    unmatched = 0
    for raw_line in cache_bytes.decode(
        "utf-8", errors="strict"
    ).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        match = EDGE_RE.match(line)
        if not match:
            unmatched += 1
            continue
        source = by_coordinate.get(coordinate_key(vector(match.group(1))))
        target = by_coordinate.get(coordinate_key(vector(match.group(2))))
        if source is None or target is None or source == target:
            unmatched += 1
            continue
        adjacency[source].add(target)
    edge_count = sum(len(values) for values in adjacency)
    if not nodes or not edge_count:
        raise capture.CaptureFailure(
            "official_waypoint_graph_empty", map_name
        )
    return WaypointGraph(
        map_name=map_name,
        gametype=gametype,
        waypoint_member=waypoint_member,
        cache_member=cache_member,
        nodes=tuple(nodes),
        flags=tuple(flags),
        adjacency=tuple(tuple(sorted(values)) for values in adjacency),
        edge_count=edge_count,
        unmatched_edges=unmatched,
        waypoint_sha256=capture.hashlib.sha256(
            waypoint_bytes
        ).hexdigest(),
        cache_sha256=capture.hashlib.sha256(cache_bytes).hexdigest(),
    )


def distance(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    return math.sqrt(
        sum((first[index] - second[index]) ** 2 for index in range(3))
    )


def accepted_start_nodes(
    map_row: dict[str, Any], *, pair_only: bool = False
) -> list[int]:
    result: list[int] = []
    if not pair_only:
        for row in map_row["accepted_positions"]:
            match = WAYPOINT_ID_RE.search(str(row["episode_id"]))
            if match:
                result.append(int(match.group(1)))
    for row in map_row["accepted_pairs"]:
        match = PAIR_WAYPOINT_ID_RE.search(str(row["episode_id"]))
        if match:
            result.extend((int(match.group(1)), int(match.group(2))))
    if not result:
        raise capture.CaptureFailure(
            "accepted_waypoint_start_missing", map_row["map"]
        )
    return sorted(set(result))


def choose_route(
    graph: WaypointGraph,
    starts: list[int],
    target_length: float,
    usage: Counter[tuple[int, int]],
    start_usage: Counter[int],
    rng: random.Random,
) -> list[int]:
    tie_break = {start: rng.random() for start in starts}
    ordered_starts = sorted(
        starts,
        key=lambda start: (
            start_usage[start],
            tie_break[start],
            start,
        ),
    )
    for attempt in range(256):
        start = ordered_starts[attempt % len(ordered_starts)]
        route = [start]
        visited = {start}
        length = 0.0
        while len(route) < 32 and length < target_length:
            current = route[-1]
            candidates: list[tuple[tuple[Any, ...], int, float]] = []
            for target in graph.adjacency[current]:
                segment = distance(
                    graph.nodes[current], graph.nodes[target]
                )
                vertical = abs(
                    graph.nodes[target][2] - graph.nodes[current][2]
                )
                if segment < 16 or segment > 512 or vertical > 80:
                    continue
                if length + segment > 1400 and length >= 500:
                    continue
                if len(route) >= 2:
                    previous = graph.nodes[route[-2]]
                    origin = graph.nodes[current]
                    destination = graph.nodes[target]
                    incoming = np.asarray(origin) - np.asarray(previous)
                    outgoing = (
                        np.asarray(destination) - np.asarray(origin)
                    )
                    denominator = float(
                        np.linalg.norm(incoming)
                        * np.linalg.norm(outgoing)
                    )
                    turn_cosine = (
                        float(incoming @ outgoing) / denominator
                        if denominator
                        else -1.0
                    )
                                                                             
                                                                      
                    if turn_cosine < -0.25:
                        continue
                score = (
                    target in visited,
                    usage[(current, target)],
                    abs((length + segment) - target_length)
                    if length + segment >= 500
                    else 0.0,
                    vertical > 32,
                    rng.random(),
                    target,
                )
                candidates.append((score, target, segment))
            if not candidates:
                break
            _, target, segment = min(candidates)
            route.append(target)
            visited.add(target)
            length += segment
            if length >= target_length:
                break
        if 500 <= length <= 1400:
            start_usage[start] += 1
            for source, target in zip(route, route[1:]):
                usage[(source, target)] += 1
            return route
    raise capture.CaptureFailure(
        "route_selection_exhausted",
        f"map={graph.map_name} target_length={target_length:.3f}",
    )


def write_route_csv(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"#route,{plan['route_id']}\n")
        writer = csv.DictWriter(
            handle, fieldnames=["index", "x", "y", "z", "jump"]
        )
        writer.writeheader()
        for node in plan["nodes"]:
            writer.writerow(
                {
                    "index": node["index"],
                    "x": f"{node['origin'][0]:.6f}",
                    "y": f"{node['origin'][1]:.6f}",
                    "z": f"{node['origin'][2]:.6f}",
                    "jump": int(node["jump"]),
                }
            )
    os.replace(temporary, path)


def build_plans(
    count: int,
    seed: int,
    maps: list[str],
    id_start: int | None = None,
    pair_starts_only: bool = False,
) -> list[dict[str, Any]]:
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    map_rows = {
        row["map"]: row
        for row in preflight["map_summary"]
        if row["stage1_admitted"] and row["map"] not in EXCLUDED_MAPS
    }
    selected_maps = maps or sorted(map_rows)
    missing = sorted(set(selected_maps) - set(map_rows))
    if missing:
        raise capture.CaptureFailure(
            "route_map_not_admitted", ",".join(missing)
        )
    graphs = {
        map_name: load_graph(
            map_name, str(map_rows[map_name]["gametype"]).lower()
        )
        for map_name in selected_maps
    }
    rng = random.Random(seed)
    existing_ids = [
        int(path.parent.name.split("_")[-1])
        for path in PLAN_ROOT.glob("s1route_*/route_plan.json")
        if path.parent.name.split("_")[-1].isdigit()
    ]
    first_id = (
        id_start
        if id_start is not None
        else max(existing_ids, default=0) + 1
    )
    usage_by_map: dict[str, Counter[tuple[int, int]]] = defaultdict(
        Counter
    )
    start_usage_by_map: dict[str, Counter[int]] = defaultdict(Counter)
    plans: list[dict[str, Any]] = []
    for index in range(count):
        map_name = selected_maps[index % len(selected_maps)]
        map_row = map_rows[map_name]
        graph = graphs[map_name]
        target_length = 650.0 + rng.random() * 500.0
        route_indices = choose_route(
            graph,
            accepted_start_nodes(
                map_row, pair_only=pair_starts_only
            ),
            target_length,
            usage_by_map[map_name],
            start_usage_by_map[map_name],
            rng,
        )
        route_id = f"s1route_{first_id + index:05d}"
        nodes = []
        route_length = 0.0
        for node_index, waypoint_index in enumerate(route_indices):
            origin = graph.nodes[waypoint_index]
            jump = False
            if node_index:
                previous = graph.nodes[route_indices[node_index - 1]]
                route_length += distance(previous, origin)
                jump = origin[2] - previous[2] > 32
            nodes.append(
                {
                    "index": node_index,
                    "waypoint_index": waypoint_index,
                    "origin": [
                        round(component, 6) for component in origin
                    ],
                    "flags": graph.flags[waypoint_index],
                    "jump": jump,
                }
            )
        route_group_digest = capture.hashlib.sha256(
            capture.canonical_json(
                [map_name, route_indices]
            ).encode()
        ).hexdigest()[:16]
        plan_dir = PLAN_ROOT / route_id
        route_csv = plan_dir / "route.csv"
        plan_path = plan_dir / "route_plan.json"
        plan = {
            "schema_version": "xonotic-stage1-route-plan-v1",
            "route_id": route_id,
            "route_group_id": f"{map_name}_{route_group_digest}",
            "map_region_id": (
                f"{map_name}_wp{route_indices[0]:04d}"
            ),
            "map": map_name,
            "gametype": str(map_row["gametype"]).lower(),
            "selection_seed": seed + index,
            "selection_policy": "coverage_driven_directed_edges_v1",
            "start_policy": (
                "live_pair_endpoint"
                if pair_starts_only
                else "live_position_or_pair_endpoint"
            ),
            "controller": "lookahead_world_velocity_v1",
            "waypoint_member": graph.waypoint_member,
            "waypoint_sha256": graph.waypoint_sha256,
            "cache_member": graph.cache_member,
            "cache_sha256": graph.cache_sha256,
            "graph_node_count": len(graph.nodes),
            "graph_edge_count": graph.edge_count,
            "graph_unmatched_edge_rows": graph.unmatched_edges,
            "nodes": nodes,
            "route_length": round(route_length, 6),
            "route_csv_path": relative_to_root(route_csv),
            "calibration_status": "pending",
        }
        start_origin = nodes[0]["origin"]
        compatible_pairs: list[dict[str, Any]] = []
        for pair in map_row["accepted_pairs"]:
            variants = (
                (
                    "forward",
                    pair["player_origin"],
                    pair["enemy_origin"],
                ),
                (
                    "reverse",
                    pair["enemy_origin"],
                    pair["player_origin"],
                ),
            )
            for variant, player_origin, enemy_origin in variants:
                if np.linalg.norm(
                    np.asarray(player_origin, dtype=np.float64)
                    - np.asarray(start_origin, dtype=np.float64)
                ) > 0.2:
                    continue
                compatible_pairs.append(
                    {
                        "source_probe": pair["episode_id"],
                        "variant": variant,
                        "distance_bin": pair["distance_bin"],
                        "player_origin": player_origin,
                        "enemy_origin": enemy_origin,
                        "gametype": pair["gametype"],
                    }
                )
        if pair_starts_only and not compatible_pairs:
            raise capture.CaptureFailure(
                "route_pair_start_evidence_missing", route_id
            )
        if compatible_pairs:
            plan["compatible_enemy_pairs"] = compatible_pairs
        if plan_path.exists() or route_csv.exists():
            raise capture.CaptureFailure(
                "refuse_overwrite_route_plan", str(plan_dir)
            )
        write_route_csv(route_csv, plan)
        plan["route_csv_sha256"] = capture.sha256_file(route_csv)
        atomic_json(plan_path, plan)
        plan["route_plan_path"] = relative_to_root(plan_path)
        plan["route_plan_sha256"] = capture.sha256_file(plan_path)
        plans.append(plan)
    indexed: list[dict[str, Any]] = []
    for path in sorted(PLAN_ROOT.glob("s1route_*/route_plan.json")):
        plan = json.loads(path.read_text(encoding="utf-8"))
        indexed.append(
            {
                **plan,
                "route_plan_path": relative_to_root(path),
                "route_plan_sha256": capture.sha256_file(path),
            }
        )
    atomic_text(
        PLAN_INDEX,
        "".join(capture.canonical_json(plan) + "\n" for plan in indexed),
    )
    return plans


def load_plan(route_id: str) -> tuple[Path, dict[str, Any]]:
    path = PLAN_ROOT / route_id / "route_plan.json"
    if not path.is_file():
        raise capture.CaptureFailure("route_plan_missing", str(path))
    return path, json.loads(path.read_text(encoding="utf-8"))


def current_source_commit() -> str:
    return (capture.build_root() / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()


def effective_plan(route_id: str) -> dict[str, Any]:
    """Merge immutable route selection with a separate calibration record."""
    _, plan = load_plan(route_id)
    source_commit = current_source_commit()
    required_keys = {
        "frozen_actions_path",
        "frozen_actions_sha256",
        "calibration_states_path",
        "calibration_states_sha256",
        "calibration_route_trace_path",
        "calibration_route_trace_sha256",
    }
    if (
        plan.get("calibration_status") == "passed"
        and required_keys <= set(plan)
        and plan.get("calibration_source_commit") == source_commit
    ):
        return plan
    record_path = CALIBRATION_ROOT / route_id / "CALIBRATION.json"
    if not record_path.is_file():
        return plan
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if (
        record.get("route_id") != route_id
        or not record.get("metrics", {}).get("passed")
        or record.get("source_commit") != source_commit
    ):
        return plan
    merged = dict(plan)
    merged.update(
        {
            "calibration_status": "passed",
            "calibration_build": record["build"],
            "calibration_source_commit": record["source_commit"],
            "calibration_metrics": record["metrics"],
            **{
                key: record[key]
                for key in required_keys
            },
        }
    )
    return merged


def route_scenario(
    plan: dict[str, Any], *, calibration: bool
) -> dict[str, Any]:
    scenario = v2.scenario(
        episode_id=(
            f"{plan['route_id']}_cal"
            if calibration
            else f"{plan['route_id']}_replay"
        ),
        split=(
            "v2_stage1_route_calibration"
            if calibration
            else "v2_stage1_route_regression"
        ),
        dataset_role="foundation_no_enemy",
        category=(
            "route_calibration"
            if calibration
            else "route_frozen_replay"
        ),
        map_name=plan["map"],
        gametype=plan["gametype"],
        player_origin=plan["nodes"][0]["origin"],
        weapon="MachineGun",
        action_program="preflight_idle",
        seed=14_000_000 + int(plan["route_id"].split("_")[-1]),
        expects_sound=True,
    )
    scenario.update(
        {
            "acceptance_policy": capture.TIERED_REVIEW_POLICY,
            "formal_collection_authorized": False,
            "training_admitted": False,
            "capture_route_calibration": calibration,
            "route_plan": plan,
            "route_group_id": plan["route_group_id"],
            "map_region_id": plan["map_region_id"],
        }
    )
    if not calibration:
        scenario["frozen_actions_path"] = plan[
            "frozen_actions_path"
        ]
        scenario["frozen_actions_sha256"] = plan[
            "frozen_actions_sha256"
        ]
    return scenario


def calibration_metrics(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    traces = [
        row for row in rows if row.get("kind") == "route_trace"
    ]
    policies = [
        row for row in rows if row.get("kind") == "route_policy"
    ]
    cross_track = np.asarray(
        [float(row["cross_track_error"]) for row in traces],
        dtype=np.float64,
    )
    max_progress = max(
        (float(row["max_progress_fraction"]) for row in traces),
        default=-1.0,
    )
    reach_rate = max(
        (float(row["waypoint_reach_rate"]) for row in traces),
        default=-1.0,
    )
    no_progress = max(
        (
            int(row["no_progress_ticks"])
            for row in traces
            if float(row["max_progress_fraction"]) < 0.85
        ),
        default=0,
    )
    p95 = (
        float(np.quantile(cross_track, 0.95))
        if len(cross_track)
        else math.inf
    )
    gates = {
        "policy_singleton_calibration": (
            len(policies) == 1
            and bool(policies[0].get("calibration"))
        ),
        "trace_ticks_exact": (
            len(traces) == capture.TOTAL_TICKS
            and [int(row["server_tick"]) for row in traces]
            == list(range(capture.TOTAL_TICKS))
        ),
        "progress_gte_85pct": max_progress >= 0.85,
        "waypoint_reach_gte_90pct": reach_rate >= 0.90,
        "cross_track_p95_lte_96": p95 <= 96,
        "no_progress_lte_half_second": (
            no_progress <= capture.TICK_HZ // 2
        ),
        "alive_no_teleport": (
            len(traces) == capture.TOTAL_TICKS
            and all(bool(row.get("alive")) for row in traces)
            and not any(
                bool(row.get("unexpected_teleport"))
                for row in traces
            )
        ),
    }
    return {
        "trace_rows": len(traces),
        "max_progress_fraction": max_progress,
        "waypoint_reach_rate": reach_rate,
        "cross_track_error_p95": p95,
        "max_no_progress_ticks": no_progress,
        "gates": gates,
        "passed": all(gates.values()),
    }


def frozen_action_rows(
    states: pd.DataFrame, scenario: dict[str, Any]
) -> list[dict[str, Any]]:
    if len(states) != capture.TOTAL_TICKS:
        raise capture.CaptureFailure(
            "route_calibration_state_count", str(len(states))
        )
    previous_yaw = float(scenario["player"]["yaw"])
    previous_pitch = float(scenario["player"].get("pitch", 0.0))
    result: list[dict[str, Any]] = []
    for _, state in states.sort_values("server_tick").iterrows():
        tick = int(state["server_tick"])
        yaw = float(state["applied_action.yaw"])
        pitch = float(state["applied_action.pitch"])
        yaw_delta = (yaw - previous_yaw + 180.0) % 360.0 - 180.0
        pitch_delta = pitch - previous_pitch
        impulse = int(round(float(state["applied_action.impulse"])))
        result.append(
            {
                "tick": tick,
                "forward": round(
                    float(state["applied_action.forward"]), 6
                ),
                "strafe": round(
                    float(state["applied_action.strafe"]), 6
                ),
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": int(bool(state["applied_action.jump"])),
                "primary": int(bool(state["applied_action.primary"])),
                "secondary": int(
                    bool(state["applied_action.secondary"])
                ),
                "weapon_impulse": 0 if impulse == 20 else impulse,
                "reload": int(impulse == 20),
            }
        )
        previous_yaw = yaw
        previous_pitch = pitch
    if [row["tick"] for row in result] != list(
        range(capture.TOTAL_TICKS)
    ):
        raise capture.CaptureFailure(
            "route_calibration_ticks_noncontiguous"
        )
    return result


def write_frozen_actions(
    path: Path, scenario: dict[str, Any], rows: list[dict[str, Any]]
) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"#seed,{scenario['seed']}\n")
        writer = csv.DictWriter(
            handle, fieldnames=capture.ACTION_COLUMNS
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def calibrate(route_id: str, port: int | None = None) -> dict[str, Any]:
    _, plan = load_plan(route_id)
    effective = effective_plan(route_id)
    if effective.get("calibration_status") == "passed":
        required = [
            capture.locked_root_artifact(
                effective[key], effective[sha_key], key
            )
            for key, sha_key in (
                ("frozen_actions_path", "frozen_actions_sha256"),
                (
                    "calibration_states_path",
                    "calibration_states_sha256",
                ),
                (
                    "calibration_route_trace_path",
                    "calibration_route_trace_sha256",
                ),
            )
        ]
        return {
            "route_id": route_id,
            "resumed": True,
            "artifacts": [str(path) for path in required],
        }
    calibration_dir = CALIBRATION_ROOT / route_id
    existing_record = calibration_dir / "CALIBRATION.json"
    if existing_record.exists():
        record = json.loads(existing_record.read_text(encoding="utf-8"))
        if record.get("source_commit") != current_source_commit():
            quarantine = (
                CALIBRATION_ROOT
                / "stale_source_commit"
                / (
                    f"{route_id}."
                    f"{str(record.get('source_commit', 'unknown'))[:12]}."
                    f"{time.time_ns()}"
                )
            )
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            os.rename(calibration_dir, quarantine)
        else:
            raise capture.CaptureFailure(
                "route_calibration_previous_failure",
                capture.canonical_json(
                    {
                        "route_id": route_id,
                        "record": relative_to_root(existing_record),
                        "metrics": record.get("metrics"),
                    }
                ),
            )
    if calibration_dir.exists():
                                                                            
                                                                             
                                   
        quarantine = (
            CALIBRATION_ROOT
            / "recovery_quarantine"
            / f"{route_id}.{time.time_ns()}"
        )
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        os.rename(calibration_dir, quarantine)
    scenario = route_scenario(plan, calibration=True)
    attempt_id = f"{scenario['episode_id']}_a01"
    stage = capture.TMP_ROOT / "raw" / attempt_id
    if stage.exists():
        capture.clean_stage(stage)
    stage.mkdir(parents=True)
    (stage / "ATTEMPT.json").write_text(
        json.dumps(
            {
                "attempt_id": attempt_id,
                "scenario": scenario,
                "build": str(capture.build_root()),
                "started_utc": capture.utc_now(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    live = capture.run_live_attempt(
        stage,
        scenario,
        capture.build_root(),
        retry=0,
        port=port,
    )
    states, _, server_rows = capture.parse_server_telemetry(
        Path(live["server_telemetry"])
    )
    metrics = calibration_metrics(server_rows)
    calibration_dir.mkdir(parents=True, exist_ok=True)
    states_path = calibration_dir / "calibration_states.parquet"
    traces_path = calibration_dir / "calibration_route_trace.parquet"
    actions_path = calibration_dir / "frozen_actions.csv"
    states.to_parquet(states_path, index=False)
    pd.json_normalize(
        [
            row
            for row in server_rows
            if row.get("kind") == "route_trace"
        ]
    ).to_parquet(traces_path, index=False)
    write_frozen_actions(
        actions_path, scenario, frozen_action_rows(states, scenario)
    )
    raw_dir = calibration_dir / "raw"
    if raw_dir.exists():
        raise capture.CaptureFailure(
            "refuse_overwrite_route_calibration_raw", str(raw_dir)
        )
    raw_dir.mkdir()
    raw_sources = {
        "server.jsonl": Path(live["server_telemetry"]),
        "server_console.log": stage / "server_console.log",
        "client_live_console.log": stage / "client_live_console.log",
        "actions_requested.csv": stage / "actions_requested.csv",
        "actions_engine.csv": Path(live["actions_engine"]),
        "demo.dem": Path(live["demo_path"]),
    }
    raw_hashes: dict[str, str] = {}
    for name, source in raw_sources.items():
        shutil.copy2(source, raw_dir / name)
        raw_hashes[name] = capture.sha256_file(raw_dir / name)

    result = {
        "schema_version": "xonotic-stage1-route-calibration-v1",
        "route_id": route_id,
        "scenario": scenario,
        "build": str(capture.build_root()),
        "source_commit": (
            capture.build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip(),
        "metrics": metrics,
        "frozen_actions_path": relative_to_root(actions_path),
        "frozen_actions_sha256": capture.sha256_file(actions_path),
        "calibration_states_path": relative_to_root(states_path),
        "calibration_states_sha256": capture.sha256_file(states_path),
        "calibration_route_trace_path": relative_to_root(traces_path),
        "calibration_route_trace_sha256": capture.sha256_file(
            traces_path
        ),
        "raw_path": relative_to_root(raw_dir),
        "raw_sha256": raw_hashes,
        "created_utc": capture.utc_now(),
    }
    atomic_json(calibration_dir / "CALIBRATION.json", result)
    if not metrics["passed"]:
        raise capture.CaptureFailure(
            "route_calibration_qa_failed",
            capture.canonical_json(metrics),
        )
    return result


def replay(
    route_id: str, view_policy: str = "look_along_route"
) -> dict[str, Any]:
    plan = effective_plan(route_id)
    if plan.get("calibration_status") != "passed":
        raise capture.CaptureFailure(
            "route_not_calibrated", route_id
        )
    scenario = route_scenario(plan, calibration=False)
    scenario["route_view_policy"] = view_policy
    if view_policy != "look_along_route":
        scenario["episode_id"] = (
            f"{route_id}_replay_{view_policy}"
        )
        scenario["anchor_id"] = (
            f"{plan['map']}_{scenario['episode_id']}_solo"
        )
    result = v2.run_full_attempt(
        scenario, retry=0, destination_root=REGRESSION_ROOT
    )
    qa = result["qa"]
    evidence = {
        "schema_version": "xonotic-stage1-route-replay-v1",
        "route_id": route_id,
        "episode_id": scenario["episode_id"],
        "route_view_policy": view_policy,
        "stage": result["persistent_stage"],
        "route": qa["route"],
        "hard_gates_pass": all(qa["hard_gates"].values()),
        "video_frames": qa["video"]["frames"],
        "audio_samples": qa["audio"]["samples_per_channel"],
        "frame_tick_mapping": qa["mapping"],
        "renderer": qa["runtime"]["renderer"],
        "created_utc": capture.utc_now(),
    }
    atomic_json(
        REGRESSION_ROOT
        / (
            f"{route_id}_REPLAY.json"
            if view_policy == "look_along_route"
            else f"{route_id}_{view_policy}_REPLAY.json"
        ),
        evidence,
    )
    return evidence


def audit() -> dict[str, Any]:
    plans = []
    for path in sorted(PLAN_ROOT.glob("*/route_plan.json")):
        plans.append(effective_plan(path.parent.name))
    replays = []
    for path in sorted(REGRESSION_ROOT.glob("*_REPLAY.json")):
        replays.append(json.loads(path.read_text(encoding="utf-8")))
    report = {
        "schema_version": "xonotic-stage1-route-report-v1",
        "created_utc": capture.utc_now(),
        "map_archive": str(MAP_ARCHIVE),
        "map_archive_sha256": capture.sha256_file(MAP_ARCHIVE),
        "plans": len(plans),
        "calibrated": sum(
            plan.get("calibration_status") == "passed"
            for plan in plans
        ),
        "replayed": len(replays),
        "replay_hard_qa_pass": sum(
            bool(row["hard_gates_pass"]) for row in replays
        ),
        "maps": dict(Counter(plan["map"] for plan in plans)),
        "route_length": {
            "min": min(
                (plan["route_length"] for plan in plans), default=None
            ),
            "max": max(
                (plan["route_length"] for plan in plans), default=None
            ),
            "mean": (
                float(np.mean([plan["route_length"] for plan in plans]))
                if plans
                else None
            ),
        },
        "formal_collection_authorized": False,
    }
    atomic_json(REPORT_PATH, report)
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--count", type=int, default=8)
    plan.add_argument("--seed", type=int, default=15_000_001)
    plan.add_argument("--maps", nargs="*", default=[])
    plan.add_argument("--id-start", type=int)
    plan.add_argument("--pair-starts-only", action="store_true")
    calibrate_parser = commands.add_parser("calibrate")
    calibrate_parser.add_argument("route_ids", nargs="+")
    calibrate_parser.add_argument("--port", type=int)
    replay_parser = commands.add_parser("replay")
    replay_parser.add_argument("route_ids", nargs="+")
    replay_parser.add_argument(
        "--view-policy",
        choices=(
            "look_along_route",
            "scan_while_following",
            "junction_vertical_feature",
            "rapid_turn_lookback_large_pitch",
        ),
        default="look_along_route",
    )
    commands.add_parser("audit")
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    try:
        if args.command == "plan":
            rows = build_plans(
                args.count,
                args.seed,
                args.maps,
                args.id_start,
                args.pair_starts_only,
            )
            print(json.dumps(rows, indent=2, sort_keys=True))
        elif args.command == "calibrate":
            for offset, route_id in enumerate(args.route_ids):
                port = args.port + offset if args.port else None
                print(
                    json.dumps(
                        calibrate(route_id, port=port),
                        indent=2,
                        sort_keys=True,
                    )
                )
        elif args.command == "replay":
            for route_id in args.route_ids:
                print(
                    json.dumps(
                        replay(route_id, args.view_policy),
                        indent=2,
                        sort_keys=True,
                    )
                )
        else:
            print(json.dumps(audit(), indent=2, sort_keys=True))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
