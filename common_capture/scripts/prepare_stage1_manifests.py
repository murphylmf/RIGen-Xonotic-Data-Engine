                      
"""Create the Stage-1 v4 distribution plan and deterministic 32-way shards."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              
import xonotic_stage1_review as review              
import xonotic_stage1_routes as routes              


ROOT = capture.ROOT
MANIFEST_ROOT = ROOT / "manifests/stage1_foundation_v4"
INPUT_PATH = MANIFEST_ROOT / "input.jsonl"
REPLENISHMENT_PATH = MANIFEST_ROOT / "replenishment.jsonl"
ROUTE_INDEX_PATH = MANIFEST_ROOT / "FORMAL_ROUTE_INDEX.jsonl"
ENEMY_PATH_PREFLIGHT_PATH = (
    MANIFEST_ROOT / "ENEMY_PATH_PREFLIGHT.json"
)
ENEMY_PATH_PREFLIGHT_SOURCE = (
    ROOT
    / "manifests/stage1_foundation_v1/ENEMY_PATH_PREFLIGHT.json"
)
METADATA_PATH = MANIFEST_ROOT / "MANIFEST_METADATA.json"
AUDIT_PATH = MANIFEST_ROOT / "MANIFEST_AUDIT.json"
LAUNCH_GUARD_PATH = MANIFEST_ROOT / "LAUNCH_BLOCKED.txt"
SHARD_ROOT = MANIFEST_ROOT / "shards"
SOURCE_COMMIT = "b40e26fd4e33b18b2002bf24beb6a78cef5fac96"
SHARD_COUNT = 32
PRIMARY_COUNT = 60_000
REPLENISHMENT_COUNT = 12_000
ROUTE_COUNT = 4_000
ROUTE_ID_START = 10_000
ROUTE_SEED = 15_100_000
SCHEDULE_SEED = 15_200_000
EXCLUDED_MAPS = {"nexballarena"}
ENEMY_PATH_PREFLIGHT_COMPATIBLE_COMMITS = {
    "c68e111dff4c80c91d84526b27cc54053072ae52",
    SOURCE_COMMIT,
}

ROLE_COUNTS = {
    "foundation_no_enemy": 45_000,
    "foundation_enemy_distractor": 15_000,
}
BUCKET_COUNTS = {
    "node_atomic": 26_000,
    "route_action": 20_000,
    "high_motion_special": 8_000,
    "weapon_environment": 6_000,
}
BUCKET_ROLE_COUNTS = {
    "node_atomic": {
        "foundation_no_enemy": 19_500,
        "foundation_enemy_distractor": 6_500,
    },
    "route_action": {
        "foundation_no_enemy": 15_000,
        "foundation_enemy_distractor": 5_000,
    },
    "high_motion_special": {
        "foundation_no_enemy": 6_000,
        "foundation_enemy_distractor": 2_000,
    },
    "weapon_environment": {
        "foundation_no_enemy": 4_500,
        "foundation_enemy_distractor": 1_500,
    },
}
NET_COUNTS = {
    "lt64": 9_000,
    "64_256": 12_000,
    "256_512": 15_000,
    "512_1024": 15_000,
    "gt1024": 9_000,
}
YAW_COUNTS = {
    "lt15": 18_000,
    "15_45": 15_000,
    "45_90": 9_000,
    "90_180": 12_000,
    "ge180": 6_000,
}
PITCH_COUNTS = {
    "lt5": 27_000,
    "5_15": 15_000,
    "15_30": 12_000,
    "ge30": 6_000,
}
RELATION_COUNTS = {
    "offscreen_or_occluded": 3_750,
    "visible_far": 4_500,
    "near_crosshair": 3_000,
    "brief_center_pass": 2_250,
    "center_linger": 1_050,
    "nearly_continuous_center": 450,
}
DISTANCE_COUNTS = {
    "close": 3_750,
    "near": 4_500,
    "medium": 3_750,
    "far": 1_800,
    "very_far": 900,
    "extreme": 300,
}
ENEMY_POLICY_COUNTS = {
    "idle": 3_000,
    "lateral_patrol": 4_500,
    "approach_retreat": 3_750,
    "stop_and_go": 3_750,
}
VIEW_COUNTS = {
    "look_along_route": 10_000,
    "scan_while_following": 6_000,
    "junction_vertical_feature": 3_000,
    "rapid_turn_lookback_large_pitch": 1_000,
}
REPLENISHMENT_SCALE = 5
WEAPONS = tuple(v2.WEAPONS)
LOCOMOTION_DIRECTIONS = tuple(
    capture.STAGE1_LOCOMOTION_VECTORS
)
TEMPORAL_PROFILES = capture.STAGE1_TEMPORAL_PROFILES
RELOAD_WEAPONS = tuple(
    weapon for weapon in WEAPONS if weapon != "Blaster"
)
WEAPON_ACTION_COUNTS = {
    "environmental_primary": 10_000,
    "reload": 5_000,
}
WEAPON_ACTION_ROLE_COUNTS = {
    "environmental_primary": {
        "foundation_no_enemy": 7_500,
        "foundation_enemy_distractor": 2_500,
    },
    "reload": {
        "foundation_no_enemy": 3_750,
        "foundation_enemy_distractor": 1_250,
    },
}
WEAPON_ACTION_DEDICATED_ROLE_COUNTS = {
    "environmental_primary": {
        "foundation_no_enemy": 3_000,
        "foundation_enemy_distractor": 1_000,
    },
    "reload": {
        "foundation_no_enemy": 1_500,
        "foundation_enemy_distractor": 500,
    },
}
RELOAD_CAPACITY = {
    "Shotgun": 8.0,
    "MachineGun": 60.0,
    "Mortar": 16.0,
    "Electro": 24.0,
    "Crylink": 18.0,
    "Vortex": 24.0,
    "Hagar": 12.0,
    "Devastator": 16.0,
}
RELOAD_INITIAL_CLIP = {
    "Shotgun": 2.0,
    "MachineGun": 12.0,
    "Mortar": 4.0,
    "Electro": 6.0,
    "Crylink": 6.0,
    "Vortex": 6.0,
    "Hagar": 3.0,
    "Devastator": 4.0,
}
MOVEMENT_MAGNITUDE_RANGES = {
    "lt64": (0.10, 0.30),
    "64_256": (0.25, 0.50),
    "256_512": (0.45, 0.70),
    "512_1024": (0.65, 0.90),
    "gt1024": (0.85, 1.00),
}
HIGH_MOTION_MAGNITUDE_RANGE = (0.85, 1.00)
YAW_AMPLITUDE_RANGES = {
    "lt15": (0.5, 14.0),
    "15_45": (17.0, 43.0),
    "45_90": (48.0, 87.0),
    "90_180": (96.0, 175.0),
    "ge180": (185.0, 260.0),
}
PITCH_AMPLITUDE_RANGES = {
    "lt5": (0.5, 4.5),
    "5_15": (6.0, 14.0),
    "15_30": (16.0, 29.0),
    "ge30": (32.0, 60.0),
}


def scaled_by(
    values: dict[str, int], scale_factor: int
) -> dict[str, int]:
    if scale_factor < 1:
        raise AssertionError(scale_factor)
    result = {
        key: value // scale_factor
        for key, value in values.items()
    }
    if any(
        result[key] * scale_factor != value
        for key, value in values.items()
    ):
        raise AssertionError((scale_factor, values))
    return result


def scaled(values: dict[str, int]) -> dict[str, int]:
    return scaled_by(values, REPLENISHMENT_SCALE)


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_manifest_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def ensure_enemy_path_preflight() -> dict[str, Any]:
    """Materialize the compatible live preflight with truthful provenance."""
    source = (
        ENEMY_PATH_PREFLIGHT_PATH
        if ENEMY_PATH_PREFLIGHT_PATH.is_file()
        else ENEMY_PATH_PREFLIGHT_SOURCE
    )
    if not source.is_file():
        raise capture.CaptureFailure(
            "formal_enemy_path_preflight_missing", str(source)
        )
    text = source.read_text(encoding="utf-8")
    report = json.loads(text)
    checks = {
        "schema": report.get("schema_version")
        == "xonotic-stage1-enemy-path-preflight-v1",
        "source_commit": report.get("source_commit")
        in ENEMY_PATH_PREFLIGHT_COMPATIBLE_COMMITS,
        "passed": report.get("passed") is True,
        "result_count": int(report.get("result_count", -1))
        == 256,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "formal_enemy_path_preflight_invalid",
            capture.canonical_json(checks),
        )
    write_once_or_verify(ENEMY_PATH_PREFLIGHT_PATH, text)
    return report


def expand(values: dict[str, int]) -> list[str]:
    return [
        name
        for name, count in values.items()
        for _ in range(int(count))
    ]


def shuffled_counts(
    values: dict[str, int], rng: random.Random
) -> list[str]:
    result = expand(values)
    rng.shuffle(result)
    return result


def formal_maps() -> list[str]:
    report = json.loads(
        routes.PREFLIGHT_PATH.read_text(encoding="utf-8")
    )
    return sorted(
        row["map"]
        for row in report["map_summary"]
        if row["stage1_admitted"]
        and row["map"] not in EXCLUDED_MAPS
    )


def route_capable_maps() -> list[str]:
    report = json.loads(
        routes.PREFLIGHT_PATH.read_text(encoding="utf-8")
    )
    capable: list[str] = []
    for map_row in report["map_summary"]:
        map_name = map_row["map"]
        if (
            not map_row["stage1_admitted"]
            or map_name in EXCLUDED_MAPS
        ):
            continue
        graph = routes.load_graph(
            map_name, str(map_row["gametype"]).lower()
        )
        try:
            routes.choose_route(
                graph,
                routes.accepted_start_nodes(map_row),
                650.0,
                Counter(),
                Counter(),
                random.Random(ROUTE_SEED + len(capable)),
            )
        except capture.CaptureFailure:
            continue
        capable.append(map_name)
    if not capable:
        raise capture.CaptureFailure("formal_route_map_pool_empty")
    return sorted(capable)


def expected_route_ids() -> list[str]:
    return [
        f"s1route_{index:05d}"
        for index in range(
            ROUTE_ID_START, ROUTE_ID_START + ROUTE_COUNT
        )
    ]


def ensure_route_library() -> list[dict[str, Any]]:
    ids = expected_route_ids()
    existing = [
        route_id
        for route_id in ids
        if (
            routes.PLAN_ROOT / route_id / "route_plan.json"
        ).is_file()
    ]
    if existing and len(existing) != ROUTE_COUNT:
        raise capture.CaptureFailure(
            "formal_route_library_partial",
            f"present={len(existing)} expected={ROUTE_COUNT}",
        )
    if not existing:
        routes.build_plans(
            ROUTE_COUNT,
            ROUTE_SEED,
            route_capable_maps(),
            ROUTE_ID_START,
            False,
        )
    result: list[dict[str, Any]] = []
    for route_id in ids:
        path, plan = routes.load_plan(route_id)
        checks = {
            "validated_start": plan.get("start_policy")
            == "live_position_or_pair_endpoint",
            "immutable_pending_plan": plan.get("calibration_status")
            == "pending",
            "route_csv_sha256": capture.sha256_file(
                ROOT / plan["route_csv_path"]
            )
            == plan["route_csv_sha256"],
        }
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "formal_route_plan_invalid",
                capture.canonical_json(
                    {"route_id": route_id, "checks": checks}
                ),
            )
        result.append(
            {
                **plan,
                "route_plan_path": str(path.relative_to(ROOT)),
                "route_plan_sha256": capture.sha256_file(path),
            }
        )
    compatible_capacity = sum(
        7 for plan in result if plan.get("compatible_enemy_pairs")
    )
    if compatible_capacity < 7_000:
        raise capture.CaptureFailure(
            "formal_route_enemy_capacity",
            f"capacity={compatible_capacity} required=7000",
        )
    route_index = canonical_lines(
        [
            {
                "route_id": plan["route_id"],
                "route_group_id": plan["route_group_id"],
                "map": plan["map"],
                "gametype": plan["gametype"],
                "map_region_id": plan["map_region_id"],
                "route_length": plan["route_length"],
                "route_plan_path": plan["route_plan_path"],
                "route_plan_sha256": plan["route_plan_sha256"],
                "route_csv_path": plan["route_csv_path"],
                "route_csv_sha256": plan["route_csv_sha256"],
                "calibration_policy": (
                    "locked_on_demand_before_first_replay"
                ),
            }
            for plan in result
        ]
    )
    write_once_or_verify(ROUTE_INDEX_PATH, route_index)
    return result


def preflight_pools() -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    report = json.loads(
        routes.PREFLIGHT_PATH.read_text(encoding="utf-8")
    )
    positions: dict[str, list[dict[str, Any]]] = {}
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for map_row in report["map_summary"]:
        map_name = map_row["map"]
        if (
            not map_row["stage1_admitted"]
            or map_name in EXCLUDED_MAPS
        ):
            continue
        positions[map_name] = list(map_row["accepted_positions"])
        for pair in map_row["accepted_pairs"]:
            for variant, player_origin, enemy_origin in (
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
            ):
                pairs[pair["distance_bin"]].append(
                    {
                        "source_probe": pair["episode_id"],
                        "variant": variant,
                        "distance_bin": pair["distance_bin"],
                        "map": map_name,
                        "gametype": pair["gametype"],
                        "player_origin": player_origin,
                        "enemy_origin": enemy_origin,
                    }
                )
    if len(positions) != 28 or set(pairs) != set(DISTANCE_COUNTS):
        raise capture.CaptureFailure(
            "formal_preflight_pool_invalid",
            capture.canonical_json(
                {
                    "maps": len(positions),
                    "distance_bins": sorted(pairs),
                }
            ),
        )
    return positions, pairs


def enemy_pair_key(pair: dict[str, Any]) -> str:
    return f"{pair['source_probe']}::{pair['variant']}"


def load_enemy_path_safety() -> tuple[
    dict[str, Any], set[tuple[str, str]]
]:
    if not ENEMY_PATH_PREFLIGHT_PATH.is_file():
        raise capture.CaptureFailure(
            "formal_enemy_path_preflight_missing",
            str(ENEMY_PATH_PREFLIGHT_PATH),
        )
    report = json.loads(
        ENEMY_PATH_PREFLIGHT_PATH.read_text(encoding="utf-8")
    )
    checks = {
        "schema": report.get("schema_version")
        == "xonotic-stage1-enemy-path-preflight-v1",
        "source_commit": report.get("source_commit")
        in ENEMY_PATH_PREFLIGHT_COMPATIBLE_COMMITS,
        "passed": report.get("passed") is True,
        "result_count": int(report.get("result_count", -1))
        == 256,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "formal_enemy_path_preflight_invalid",
            capture.canonical_json(checks),
        )
    safe: set[tuple[str, str]] = set()
    for result in report["results"]:
        if not result.get("path_certified"):
            continue
        key = str(result["pair_key"])
        for policy in result["certifies_policies"]:
            safe.add((key, str(policy)))
    return report, safe


def _policy_group_flow(
    groups: list[tuple[tuple[str, ...], int]],
    policy_counts: dict[str, int],
) -> dict[tuple[int, str], int]:
    """Solve exact policy quotas against path-compatible slot groups."""
    policies = list(policy_counts)
    source = 0
    policy_node = {
        policy: index + 1 for index, policy in enumerate(policies)
    }
    group_offset = 1 + len(policies)
    sink = group_offset + len(groups)
    graph: list[list[list[int]]] = [
        [] for _ in range(sink + 1)
    ]

    def add_edge(start: int, end: int, capacity: int) -> list[int]:
        forward = [end, len(graph[end]), capacity, capacity]
        reverse = [start, len(graph[start]), 0, 0]
        graph[start].append(forward)
        graph[end].append(reverse)
        return forward

    for policy, count in policy_counts.items():
        add_edge(source, policy_node[policy], int(count))
    references: dict[tuple[int, str], list[int]] = {}
    for group_index, (allowed, count) in enumerate(groups):
        node = group_offset + group_index
        add_edge(node, sink, count)
        for policy in allowed:
            references[(group_index, policy)] = add_edge(
                policy_node[policy], node, count
            )

    total = 0
    while True:
        level = [-1] * len(graph)
        level[source] = 0
        queue = [source]
        for node in queue:
            for edge in graph[node]:
                if edge[2] > 0 and level[edge[0]] < 0:
                    level[edge[0]] = level[node] + 1
                    queue.append(edge[0])
        if level[sink] < 0:
            break
        cursor = [0] * len(graph)

        def send(node: int, available: int) -> int:
            if node == sink:
                return available
            while cursor[node] < len(graph[node]):
                edge = graph[node][cursor[node]]
                if (
                    edge[2] > 0
                    and level[edge[0]] == level[node] + 1
                ):
                    pushed = send(
                        edge[0], min(available, edge[2])
                    )
                    if pushed:
                        edge[2] -= pushed
                        graph[edge[0]][edge[1]][2] += pushed
                        return pushed
                cursor[node] += 1
            return 0

        while True:
            pushed = send(source, sum(policy_counts.values()))
            if not pushed:
                break
            total += pushed
    wanted = sum(policy_counts.values())
    if total != wanted:
        raise capture.CaptureFailure(
            "formal_enemy_policy_path_flow_infeasible",
            capture.canonical_json(
                {
                    "assigned": total,
                    "required": wanted,
                    "groups": [
                        {"allowed": allowed, "count": count}
                        for allowed, count in groups
                    ],
                }
            ),
        )
    return {
        (group_index, policy): edge[3] - edge[2]
        for (group_index, policy), edge in references.items()
    }


def assign_path_safe_enemy_policies(
    enemy_slots: list[dict[str, Any]],
    pairs: dict[str, list[dict[str, Any]]],
    policy_counts: dict[str, int],
    rng: random.Random,
) -> dict[str, Any]:
    report, safe = load_enemy_path_safety()
    preflight_sha256 = capture.sha256_file(
        ENEMY_PATH_PREFLIGHT_PATH
    )
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    policy_order = tuple(policy_counts)
    for slot in enemy_slots:
        distance_bin = slot["target_distance_bin"]
        candidates = (
            [
                pair
                for pair in slot["plan"].get(
                    "compatible_enemy_pairs", []
                )
                if pair["distance_bin"] == distance_bin
            ]
            if slot.get("plan")
            else list(pairs[distance_bin])
        )
        safe_by_policy: dict[str, list[dict[str, Any]]] = {}
        for policy in policy_order:
            safe_by_policy[policy] = [
                pair
                for pair in candidates
                if policy == "idle"
                or (enemy_pair_key(pair), policy) in safe
            ]
        allowed = tuple(
            policy
            for policy in policy_order
            if safe_by_policy[policy]
        )
        if not allowed:
            raise AssertionError("idle pair must remain available")
        slot["_safe_pairs_by_policy"] = safe_by_policy
        grouped[allowed].append(slot)
    groups = sorted(
        (
            (allowed, slots)
            for allowed, slots in grouped.items()
        ),
        key=lambda item: (len(item[0]), item[0]),
    )
    allocation = _policy_group_flow(
        [(allowed, len(slots)) for allowed, slots in groups],
        policy_counts,
    )
    for group_index, (allowed, slots) in enumerate(groups):
        assigned = [
            policy
            for policy in allowed
            for _ in range(
                allocation.get((group_index, policy), 0)
            )
        ]
        if len(assigned) != len(slots):
            raise AssertionError((allowed, len(assigned), len(slots)))
        rng.shuffle(assigned)
        rng.shuffle(slots)
        for slot, policy in zip(slots, assigned):
            candidate_pool = slot.pop("_safe_pairs_by_policy")[
                policy
            ]
            selected = copy.deepcopy(
                candidate_pool[rng.randrange(len(candidate_pool))]
            )
            slot["enemy_policy_name"] = policy
            slot["selected_pair"] = selected
            slot["enemy_path_certification"] = {
                "pair_key": enemy_pair_key(selected),
                "axis": (
                    "anchor"
                    if policy == "idle"
                    else (
                        "radial"
                        if policy == "approach_retreat"
                        else "lateral"
                    )
                ),
                "certified": True,
                "preflight_path": str(
                    ENEMY_PATH_PREFLIGHT_PATH.relative_to(ROOT)
                ),
                "preflight_sha256": preflight_sha256,
            }
    return report


def route_distance_counts(
    total_distance_counts: dict[str, int],
) -> dict[str, int]:
                                                                          
                                                                           
                               
    return {
        key: value // 3
        for key, value in total_distance_counts.items()
    }


def choose_high_motion(
    slots: list[dict[str, Any]],
    count: int,
    rng: random.Random,
) -> set[int]:
    ranked = list(range(len(slots)))
    random_rank = {index: rng.random() for index in ranked}
    ranked.sort(
        key=lambda index: (
            not slots[index]["has_vertical_feature"],
            random_rank[index],
        )
    )
    return set(ranked[:count])


def make_route_slots(
    plans: list[dict[str, Any]],
    *,
    route_total: int,
    route_enemy: int,
    route_bucket: int,
    high_bucket: int,
    route_enemy_bucket: int,
    high_enemy_bucket: int,
    distance_counts: dict[str, int],
    view_counts: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    slots = [
        {
            "plan": plans[index % len(plans)],
            "route_slot_ordinal": index,
            "has_vertical_feature": any(
                node.get("jump") or int(node.get("flags", 0))
                for node in plans[index % len(plans)]["nodes"]
            ),
        }
        for index in range(route_total)
    ]
    unused = set(range(len(slots)))
    rare_first = sorted(
        distance_counts,
        key=lambda name: (
            sum(
                name
                in {
                    pair["distance_bin"]
                    for pair in plan.get(
                        "compatible_enemy_pairs", []
                    )
                }
                for plan in plans
            ),
            name,
        ),
    )
    for distance_bin in rare_first:
        candidates = [
            index
            for index, slot in enumerate(slots)
            if index in unused
            and any(
                pair["distance_bin"] == distance_bin
                for pair in slot["plan"].get(
                    "compatible_enemy_pairs", []
                )
            )
        ]
        rng.shuffle(candidates)
        wanted = distance_counts[distance_bin]
        if len(candidates) < wanted:
            raise capture.CaptureFailure(
                "formal_route_distance_capacity",
                f"bin={distance_bin} have={len(candidates)} need={wanted}",
            )
        for sequence, index in enumerate(candidates[:wanted]):
            slot = slots[index]
            compatible = [
                pair
                for pair in slot["plan"].get(
                    "compatible_enemy_pairs", []
                )
                if pair["distance_bin"] == distance_bin
            ]
            slot.update(
                {
                    "dataset_role": "foundation_enemy_distractor",
                    "target_distance_bin": distance_bin,
                    "selected_pair": compatible[
                        sequence % len(compatible)
                    ],
                }
            )
            unused.remove(index)
    if sum(
        slot.get("dataset_role")
        == "foundation_enemy_distractor"
        for slot in slots
    ) != route_enemy:
        raise AssertionError("route enemy count")
    for index in unused:
        slots[index]["dataset_role"] = "foundation_no_enemy"

    enemy_slots = [
        slot
        for slot in slots
        if slot["dataset_role"]
        == "foundation_enemy_distractor"
    ]
    solo_slots = [
        slot
        for slot in slots
        if slot["dataset_role"] == "foundation_no_enemy"
    ]
    high_enemy = choose_high_motion(
        enemy_slots, high_enemy_bucket, rng
    )
    high_solo = choose_high_motion(
        solo_slots, high_bucket - high_enemy_bucket, rng
    )
    for index, slot in enumerate(enemy_slots):
        slot["primary_bucket"] = (
            "high_motion_special"
            if index in high_enemy
            else "route_action"
        )
    for index, slot in enumerate(solo_slots):
        slot["primary_bucket"] = (
            "high_motion_special"
            if index in high_solo
            else "route_action"
        )
    if Counter(slot["primary_bucket"] for slot in slots) != Counter(
        {"route_action": route_bucket, "high_motion_special": high_bucket}
    ):
        raise AssertionError("route bucket count")
    if Counter(
        slot["primary_bucket"]
        for slot in slots
        if slot["dataset_role"]
        == "foundation_enemy_distractor"
    ) != Counter(
        {
            "route_action": route_enemy_bucket,
            "high_motion_special": high_enemy_bucket,
        }
    ):
        raise AssertionError("route enemy bucket count")
    policies = shuffled_counts(view_counts, rng)
    for slot, policy in zip(slots, policies):
        slot["route_view_policy"] = policy
    return slots


def make_nonroute_slots(
    positions: dict[str, list[dict[str, Any]]],
    pairs: dict[str, list[dict[str, Any]]],
    *,
    node_solo: int,
    node_enemy: int,
    high_solo: int,
    high_enemy: int,
    weapon_solo: int,
    weapon_enemy: int,
    distance_counts: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    enemy_slots: list[dict[str, Any]] = []
    for distance_bin, count in distance_counts.items():
        pool = list(pairs[distance_bin])
        rng.shuffle(pool)
        for index in range(count):
            enemy_slots.append(
                {
                    "dataset_role": "foundation_enemy_distractor",
                    "target_distance_bin": distance_bin,
                    "selected_pair": copy.deepcopy(
                        pool[index % len(pool)]
                    ),
                }
            )
    rng.shuffle(enemy_slots)
    for index, slot in enumerate(enemy_slots):
        if index < node_enemy:
            slot["primary_bucket"] = "node_atomic"
        elif index < node_enemy + high_enemy:
            slot["primary_bucket"] = "high_motion_special"
        else:
            slot["primary_bucket"] = "weapon_environment"
    solo_slots: list[dict[str, Any]] = []
    map_names = sorted(positions)
    position_offsets: Counter[str] = Counter()
    for index in range(node_solo + high_solo + weapon_solo):
        map_name = map_names[index % len(map_names)]
        pool = positions[map_name]
        position = pool[position_offsets[map_name] % len(pool)]
        position_offsets[map_name] += 1
        solo_slots.append(
            {
                "dataset_role": "foundation_no_enemy",
                "primary_bucket": (
                    "node_atomic"
                    if index < node_solo
                    else (
                        "high_motion_special"
                        if index < node_solo + high_solo
                        else "weapon_environment"
                    )
                ),
                "selected_position": copy.deepcopy(position),
            }
        )
    result = enemy_slots + solo_slots
    rng.shuffle(result)
    return result


def assign_route_motion_targets(
    route_slots: list[dict[str, Any]],
    counts: dict[str, dict[str, int]],
    rng: random.Random,
) -> None:
    by_length = sorted(
        route_slots,
        key=lambda slot: float(slot["plan"]["route_length"]),
        reverse=True,
    )
    net = counts["net"]
    cursor = 0
    for target in ("gt1024", "512_1024", "256_512"):
        count = (
            net[target]
            if target != "256_512"
            else len(route_slots) - cursor
        )
        for slot in by_length[cursor : cursor + count]:
            slot["target_net_bin"] = target
        cursor += count

    by_view: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for slot in route_slots:
        by_view[slot["route_view_policy"]].append(slot)
    for policy_slots in by_view.values():
        rng.shuffle(policy_slots)
    for slot in by_view["scan_while_following"]:
        slot["target_yaw_bin"] = "15_45"
        slot["target_pitch_bin"] = "5_15"
    for slot in by_view["junction_vertical_feature"]:
        slot["target_yaw_bin"] = "45_90"
        slot["target_pitch_bin"] = "15_30"
    for slot in by_view["rapid_turn_lookback_large_pitch"]:
        slot["target_yaw_bin"] = "ge180"
        slot["target_pitch_bin"] = "ge30"
    along = sorted(
        by_view["look_along_route"],
        key=lambda slot: slot["target_net_bin"]
        not in {"512_1024", "gt1024"},
    )
    along_large_yaw = counts["route_along_large_yaw"]
    large_net_along = sum(
        slot["target_net_bin"] in {"512_1024", "gt1024"}
        for slot in along
    )
    if large_net_along < along_large_yaw:
        raise capture.CaptureFailure(
            "formal_joint_net_yaw_capacity",
            f"have={large_net_along} need={along_large_yaw}",
        )
    for index, slot in enumerate(along):
        slot["target_yaw_bin"] = (
            "90_180" if index < along_large_yaw else "lt15"
        )
        slot["target_pitch_bin"] = "lt5"


def assign_nonroute_motion_targets(
    slots: list[dict[str, Any]],
    remaining: dict[str, dict[str, int]],
    rng: random.Random,
) -> None:
    for field, key in (
        ("target_net_bin", "net"),
        ("target_yaw_bin", "yaw"),
        ("target_pitch_bin", "pitch"),
    ):
        values = shuffled_counts(remaining[key], rng)
        if len(values) != len(slots):
            raise AssertionError((field, len(values), len(slots)))
        for slot, value in zip(slots, values):
            slot[field] = value


def assign_stratified_marginal(
    slots: list[dict[str, Any]],
    field: str,
    counts: dict[str, int],
    rng: random.Random,
) -> None:
    """Assign an exact global marginal with near-proportional strata."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for slot in slots:
        grouped[
            (slot["dataset_role"], slot["primary_bucket"])
        ].append(slot)
    categories = tuple(counts)
    total = sum(counts.values())
    if total != len(slots):
        raise AssertionError((field, total, len(slots)))
    allocation: dict[tuple[tuple[str, str], str], int] = {}
    fractional: dict[
        tuple[tuple[str, str], str], float
    ] = {}
    row_remaining: dict[tuple[str, str], int] = {}
    category_remaining = dict(counts)
    for key, rows in grouped.items():
        assigned = 0
        for category in categories:
            ideal = len(rows) * counts[category] / total
            base = math.floor(ideal)
            allocation[(key, category)] = base
            fractional[(key, category)] = ideal - base
            category_remaining[category] -= base
            assigned += base
        row_remaining[key] = len(rows) - assigned
    tie_break = {
        (key, category): rng.random()
        for key in grouped
        for category in categories
    }
    while any(row_remaining.values()):
        candidates = [
            (key, category)
            for key in grouped
            for category in categories
            if row_remaining[key] > 0
            and category_remaining[category] > 0
        ]
        if not candidates:
            raise AssertionError(
                (field, row_remaining, category_remaining)
            )
        key, category = max(
            candidates,
            key=lambda item: (
                fractional[item]
                - max(0, allocation[item] - math.floor(
                    len(grouped[item[0]])
                    * counts[item[1]]
                    / total
                )),
                tie_break[item],
            ),
        )
        allocation[(key, category)] += 1
        row_remaining[key] -= 1
        category_remaining[category] -= 1
    if any(category_remaining.values()):
        raise AssertionError((field, category_remaining))
    for key, rows in grouped.items():
        values = [
            category
            for category in categories
            for _ in range(allocation[(key, category)])
        ]
        rng.shuffle(values)
        rng.shuffle(rows)
        for slot, value in zip(rows, values):
            slot[field] = value


def balanced_values(
    count: int, values: tuple[str, ...], rng: random.Random
) -> list[str]:
    result = [
        values[index % len(values)] for index in range(count)
    ]
    rng.shuffle(result)
    return result


def assign_balanced_field(
    slots: list[dict[str, Any]],
    field: str,
    values: tuple[str, ...],
    rng: random.Random,
    *,
    group_fields: tuple[str, ...] = (
        "dataset_role",
        "primary_bucket",
    ),
) -> None:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for slot in slots:
        grouped[
            tuple(slot[name] for name in group_fields)
        ].append(slot)
    for rows in grouped.values():
        assigned = balanced_values(len(rows), values, rng)
        rng.shuffle(rows)
        for slot, value in zip(rows, assigned):
            slot[field] = value


def assign_stratified_continuous_field(
    slots: list[dict[str, Any]],
    field: str,
    target_field: str,
    ranges: dict[str, tuple[float, float]],
    rng: random.Random,
    *,
    group_fields: tuple[str, ...] = (
        "dataset_role",
        "primary_bucket",
    ),
) -> None:
    """Spread continuous values evenly inside every target/major stratum."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for slot in slots:
        target = str(slot[target_field])
        if target not in ranges:
            raise AssertionError((target_field, target))
        grouped[
            (
                target,
                *(slot[name] for name in group_fields),
            )
        ].append(slot)
    for key, rows in grouped.items():
        low, high = ranges[str(key[0])]
        values = [
            low + (high - low) * (index + 0.5) / len(rows)
            for index in range(len(rows))
        ]
        rng.shuffle(values)
        rng.shuffle(rows)
        for slot, value in zip(rows, values):
            slot[field] = round(float(value), 6)


def assign_view_directions(
    slots: list[dict[str, Any]], rng: random.Random
) -> None:
    grouped: dict[
        tuple[str, str, bool, bool], list[dict[str, Any]]
    ] = defaultdict(list)
    for slot in slots:
        yaw_active = slot["target_yaw_bin"] != "lt15"
        pitch_active = slot["target_pitch_bin"] != "lt5"
        grouped[
            (
                slot["dataset_role"],
                slot["primary_bucket"],
                yaw_active,
                pitch_active,
            )
        ].append(slot)
    for key, rows in grouped.items():
        yaw_active, pitch_active = key[-2:]
        if yaw_active and pitch_active:
            values = (
                "yaw_left_pitch_up",
                "yaw_left_pitch_down",
                "yaw_right_pitch_up",
                "yaw_right_pitch_down",
            )
        elif yaw_active:
            values = ("yaw_left", "yaw_right")
        elif pitch_active:
            values = ("pitch_up", "pitch_down")
        else:
            values = tuple(capture.STAGE1_VIEW_SIGNS)
        assigned = balanced_values(len(rows), values, rng)
        rng.shuffle(rows)
        for slot, value in zip(rows, assigned):
            slot["view_direction"] = value


def assign_weapon_actions(
    slots: list[dict[str, Any]],
    scale_factor: int,
    rng: random.Random,
) -> None:
    for slot in slots:
        slot["weapon_action"] = "none"
    safe_relations = {
        "offscreen_or_occluded",
        "visible_far",
        "near_crosshair",
    }
    for role in ROLE_COUNTS:
        for dedicated_only in (True, False):
            pool = [
                slot
                for slot in slots
                if slot["dataset_role"] == role
                and (
                    slot["primary_bucket"]
                    == "weapon_environment"
                )
                == dedicated_only
            ]
            primary_dedicated = (
                WEAPON_ACTION_DEDICATED_ROLE_COUNTS[
                    "environmental_primary"
                ][role]
            )
            primary_needed = (
                primary_dedicated
                if dedicated_only
                else (
                    WEAPON_ACTION_ROLE_COUNTS[
                        "environmental_primary"
                    ][role]
                    - primary_dedicated
                )
            ) // scale_factor
            reload_dedicated = (
                WEAPON_ACTION_DEDICATED_ROLE_COUNTS["reload"][
                    role
                ]
            )
            reload_needed = (
                reload_dedicated
                if dedicated_only
                else (
                    WEAPON_ACTION_ROLE_COUNTS["reload"][role]
                    - reload_dedicated
                )
            ) // scale_factor
            rng.shuffle(pool)
            fire_candidates = [
                slot
                for slot in pool
                if role == "foundation_no_enemy"
                or slot.get("target_relation") in safe_relations
            ]
            rng.shuffle(fire_candidates)
            if len(fire_candidates) < primary_needed:
                raise capture.CaptureFailure(
                    "stage1_safe_environment_fire_capacity",
                    capture.canonical_json(
                        {
                            "role": role,
                            "dedicated": dedicated_only,
                            "have": len(fire_candidates),
                            "need": primary_needed,
                        }
                    ),
                )
            for slot in fire_candidates[:primary_needed]:
                slot["weapon_action"] = "environmental_primary"
            remaining = [
                slot
                for slot in pool
                if slot["weapon_action"] == "none"
            ]
            rng.shuffle(remaining)
            if len(remaining) < reload_needed:
                raise AssertionError((role, dedicated_only))
            for slot in remaining[:reload_needed]:
                slot["weapon_action"] = "reload"

    action_weapons: dict[str, tuple[str, ...]] = {
        "environmental_primary": WEAPONS,
        "reload": RELOAD_WEAPONS,
    }
    target_weapon_counts = Counter(
        balanced_values(len(slots), WEAPONS, rng)
    )
    used: Counter[str] = Counter()
    for mode, eligible in action_weapons.items():
        mode_slots = [
            slot for slot in slots if slot["weapon_action"] == mode
        ]
        values = balanced_values(len(mode_slots), eligible, rng)
        rng.shuffle(mode_slots)
        for slot, weapon in zip(mode_slots, values):
            slot["weapon"] = weapon
            used[weapon] += 1
    none_slots = [
        slot for slot in slots if slot["weapon_action"] == "none"
    ]
    residual = {
        weapon: target_weapon_counts[weapon] - used[weapon]
        for weapon in WEAPONS
    }
    if any(count < 0 for count in residual.values()):
        raise AssertionError((target_weapon_counts, used))
    none_values = expand(residual)
    if len(none_values) != len(none_slots):
        raise AssertionError((len(none_values), len(none_slots)))
    rng.shuffle(none_values)
    rng.shuffle(none_slots)
    for slot, weapon in zip(none_slots, none_values):
        slot["weapon"] = weapon


def assign_action_design(
    slots: list[dict[str, Any]],
    scale_factor: int,
    rng: random.Random,
) -> None:
    nonroute = [slot for slot in slots if not slot.get("plan")]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for slot in nonroute:
        grouped[
            (slot["dataset_role"], slot["primary_bucket"])
        ].append(slot)
    dynamic_directions = tuple(
        value
        for value in LOCOMOTION_DIRECTIONS
        if value != "idle"
    )
    for rows in grouped.values():
        idle_target = round(len(rows) / len(LOCOMOTION_DIRECTIONS))
        idle_candidates = [
            slot
            for slot in rows
            if slot["target_net_bin"] == "lt64"
        ]
        rng.shuffle(idle_candidates)
        idle_ids = {
            id(slot) for slot in idle_candidates[:idle_target]
        }
        dynamic_rows = [
            slot for slot in rows if id(slot) not in idle_ids
        ]
        directions = balanced_values(
            len(dynamic_rows), dynamic_directions, rng
        )
        rng.shuffle(dynamic_rows)
        for slot in rows:
            if id(slot) in idle_ids:
                slot["locomotion_direction"] = "idle"
        for slot, direction in zip(dynamic_rows, directions):
            slot["locomotion_direction"] = direction
    assign_balanced_field(
        [
            slot
            for slot in nonroute
            if slot["locomotion_direction"] != "idle"
        ],
        "movement_profile",
        TEMPORAL_PROFILES,
        rng,
    )
    for slot in slots:
        if slot.get("plan"):
            slot["locomotion_direction"] = "route_follow"
            slot["movement_profile"] = "route_calibrated_visible"
        elif slot["locomotion_direction"] == "idle":
            slot["movement_profile"] = "full_clip_sustained"
    assign_balanced_field(
        slots, "view_profile", TEMPORAL_PROFILES, rng
    )
    assign_view_directions(slots, rng)
    assign_weapon_actions(slots, scale_factor, rng)
    assign_stratified_continuous_field(
        slots,
        "yaw_amplitude",
        "target_yaw_bin",
        YAW_AMPLITUDE_RANGES,
        rng,
    )
    assign_stratified_continuous_field(
        slots,
        "pitch_amplitude",
        "target_pitch_bin",
        PITCH_AMPLITUDE_RANGES,
        rng,
    )
    moving_slots = [
        slot
        for slot in slots
        if slot["locomotion_direction"] != "idle"
    ]
    assign_stratified_continuous_field(
        moving_slots,
        "movement_magnitude",
        "target_net_bin",
        MOVEMENT_MAGNITUDE_RANGES,
        rng,
    )
    high_motion_slots = [
        slot
        for slot in moving_slots
        if slot["primary_bucket"] == "high_motion_special"
    ]
    assign_stratified_continuous_field(
        high_motion_slots,
        "movement_magnitude",
        "target_net_bin",
        {
            target: HIGH_MOTION_MAGNITUDE_RANGE
            for target in MOVEMENT_MAGNITUDE_RANGES
        },
        rng,
    )
    for slot in slots:
        action_fingerprint = (
            f"{slot['dataset_role']}:{slot['primary_bucket']}:"
            f"{slot.get('selected_position', slot.get('selected_pair'))}"
        )
        if slot["locomotion_direction"] == "idle":
            slot["movement_magnitude"] = 0.0
        slot["movement_speed"] = round(
            float(slot["movement_magnitude"])
            * capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
            6,
        )
        slot["jump"] = (
            slot["primary_bucket"] == "high_motion_special"
            or (
                not slot.get("plan")
                and (
                    int(hashlib.sha256(
                        action_fingerprint.encode()
                    ).hexdigest()[:8], 16)
                    % 8
                    == 0
                )
            )
        )
        active = int(
            slot["locomotion_direction"] not in {"idle"}
        )
        active += int(slot["view_direction"] != "stationary")
        active += int(slot["weapon_action"] != "none")
        active += int(slot["jump"])
        if active > 3 and slot["jump"]:
            slot["jump"] = False
            active -= 1
        slot["action_arity"] = {
            0: "idle",
            1: "atomic",
            2: "pairwise",
            3: "three_way",
        }[active]


def counter_subtract(
    total: dict[str, int], observed: Counter[str]
) -> dict[str, int]:
    result = {
        key: int(value - observed[key])
        for key, value in total.items()
    }
    if any(value < 0 for value in result.values()):
        raise AssertionError((total, observed))
    return result


def enemy_policy(
    name: str, policy_seed: int
) -> dict[str, Any]:
    return {
        "schema_version": "xonotic-stage1-enemy-policy-v1",
        "name": name,
        "policy_seed": policy_seed,
        "motion_start_tick": (
            0
            if name == "idle"
            else policy_seed % capture.WARMUP_TICKS
        ),
        "runtime_reads_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
        "fires": False,
        "jumps": False,
        "trajectory_reference": "fixed_initial_anchor_geometry",
        "movement_audio": capture.ENEMY_MOVEMENT_AUDIO_MODE,
        "step_stride_units": capture.ENEMY_STEP_STRIDE_UNITS,
    }


def relation_offset(name: str) -> float:
    return {
        "offscreen_or_occluded": -150.0,
        "visible_far": -35.0,
        "near_crosshair": -9.5,
        "brief_center_pass": 0.0,
        "center_linger": -4.0,
        "nearly_continuous_center": 0.0,
    }[name]


def nonroute_action(slot: dict[str, Any], ordinal: int) -> dict[str, Any]:
    net_bin = slot["target_net_bin"]
    duration = int(review.MOVE_DURATIONS[net_bin][0])
    world_yaw = float((ordinal * 47) % 360) - 180.0
    if slot["dataset_role"] == "foundation_enemy_distractor":
        pair = slot["selected_pair"]
        world_yaw = review.direction_yaw(
            pair["player_origin"], pair["enemy_origin"]
        ) + (90.0 if ordinal % 2 else -90.0)
    bucket = slot["primary_bucket"]
    fire_mode = "none"
    if (
        bucket == "weapon_environment"
        and slot["dataset_role"] == "foundation_no_enemy"
    ):
        modes = (
            "environmental_primary",
            "machinegun_reload",
            "held_weapon_state",
        )
        fire_mode = modes[ordinal % len(modes)]
    jump = bucket == "node_atomic" and ordinal % 4 == 0
    return {
        "world_yaw": world_yaw,
        "control_angle": (0.0, 180.0, 90.0, -90.0, 45.0)[
            ordinal % 5
        ],
        "move_duration_candidates": [duration],
        "move_start_tick": 0,
        "trajectory_policy": "formal_frozen_stratified",
        "yaw_amplitude": float(slot["yaw_amplitude"]),
        "pitch_amplitude": float(slot["pitch_amplitude"]),
        "jump": jump,
        "fire_mode": (
            "none" if fire_mode == "held_weapon_state" else fire_mode
        ),
        "weapon_state_only": fire_mode == "held_weapon_state",
        "relation": slot.get("target_relation"),
    }


def action_design(slot: dict[str, Any]) -> dict[str, Any]:
    view_direction = slot["view_direction"]
    yaw_amplitude = float(slot["yaw_amplitude"])
    pitch_amplitude = float(slot["pitch_amplitude"])
    if view_direction == "stationary":
        yaw_amplitude = 0.0
        pitch_amplitude = 0.0
    elif view_direction in {"yaw_left", "yaw_right"}:
        pitch_amplitude = 0.0
    elif view_direction in {"pitch_up", "pitch_down"}:
        yaw_amplitude = 0.0
    return {
        "schema_version": "xonotic-stage1-action-design-v4",
        "model_action_schema_version": (
            capture.MODEL_ACTION_SCHEMA_VERSION
        ),
        "locomotion_direction": slot["locomotion_direction"],
        "movement_profile": slot["movement_profile"],
        "movement_xy_magnitude": float(
            slot["movement_magnitude"]
        ),
        "movement_speed": slot["movement_speed"],
        "view_direction": view_direction,
        "view_profile": slot["view_profile"],
        "yaw_amplitude": yaw_amplitude,
        "pitch_amplitude": pitch_amplitude,
        "jump": bool(slot["jump"]),
        "weapon_action": slot["weapon_action"],
        "action_arity": slot["action_arity"],
        "zoom": False,
        "weapon_select": False,
    }


def scenario_from_slot(
    slot: dict[str, Any],
    *,
    episode_id: str,
    ordinal: int,
    wave: str,
    source_commit: str,
) -> dict[str, Any]:
    role = slot["dataset_role"]
    enemy_present = role == "foundation_enemy_distractor"
    appearance = slot.get("appearance")
    enemy_model = appearance[0] if appearance else ""
    enemy_skin = int(appearance[1]) if appearance else 0
    enemy_color = (0, 68, 204)[ordinal % 3]
    route_plan = slot.get("plan")
    if route_plan:
        selected_pair = slot.get("selected_pair")
        player_origin = list(route_plan["nodes"][0]["origin"])
        enemy_origin = (
            list(selected_pair["enemy_origin"])
            if selected_pair
            else None
        )
        seed = 14_000_000 + int(
            route_plan["route_id"].split("_")[-1]
        )
        row = v2.scenario(
            episode_id=episode_id,
            split=role,
            dataset_role=role,
            category=slot["primary_bucket"],
            map_name=route_plan["map"],
            gametype=route_plan["gametype"],
            player_origin=player_origin,
            enemy_origin=enemy_origin,
            enemy_model=enemy_model,
            enemy_skin=enemy_skin,
            enemy_color=enemy_color,
            weapon=slot["weapon"],
            action_program="preflight_idle",
            seed=seed,
            expected_relation=slot.get("target_relation"),
            expected_distance_bin=slot.get(
                "target_distance_bin"
            ),
            expects_sound=True,
        )
                                                                               
        row["player"]["yaw"] = round(
            float((seed * 37) % 360) - 180.0, 6
        )
        row["player"]["pitch"] = 0.0
        row["route_request"] = {
            "route_id": route_plan["route_id"],
            "route_plan_path": route_plan["route_plan_path"],
            "route_plan_sha256": route_plan["route_plan_sha256"],
            "route_csv_path": route_plan["route_csv_path"],
            "route_csv_sha256": route_plan["route_csv_sha256"],
            "calibration_policy": (
                "locked_on_demand_before_first_replay"
            ),
        }
        row["route_group_id"] = route_plan["route_group_id"]
        row["map_region_id"] = route_plan["map_region_id"]
        row["route_view_policy"] = slot["route_view_policy"]
    else:
        if enemy_present:
            selected_pair = slot["selected_pair"]
            map_name = selected_pair["map"]
            gametype = selected_pair["gametype"]
            player_origin = selected_pair["player_origin"]
            enemy_origin = selected_pair["enemy_origin"]
        else:
            position = slot["selected_position"]
            map_name = position["map"]
            gametype = position["gametype"]
            player_origin = position["player_origin"]
            enemy_origin = None
        row = v2.scenario(
            episode_id=episode_id,
            split=role,
            dataset_role=role,
            category=slot["primary_bucket"],
            map_name=map_name,
            gametype=gametype,
            player_origin=player_origin,
            enemy_origin=enemy_origin,
            enemy_model=enemy_model,
            enemy_skin=enemy_skin,
            enemy_color=enemy_color,
            weapon=slot["weapon"],
            action_program="stage1_review_distribution",
            seed=16_000_000 + ordinal,
            yaw_offset=(
                relation_offset(slot["target_relation"])
                if enemy_present
                else 0.0
            ),
            expected_relation=slot.get("target_relation"),
            expected_distance_bin=slot.get(
                "target_distance_bin"
            ),
            expects_sound=(
                slot["target_net_bin"] != "lt64"
                or slot["primary_bucket"] == "weapon_environment"
            ),
            fire_required=False,
            reload_success=False,
        )
        row["review_action"] = {
            "schema_version": "superseded-by-action-design-v4"
        }
        row["fixed_variant_index"] = 0
        row["map_region_id"] = (
            selected_pair["source_probe"]
            if enemy_present
            else position["episode_id"]
        )
        row["route_group_id"] = None

    row["action_design"] = action_design(slot)
    weapon_action = slot["weapon_action"]
    if weapon_action == "reload":
        row["player"]["clip"] = RELOAD_INITIAL_CLIP[
            slot["weapon"]
        ]
        row["acceptance"].update(
            {
                "reload_success": True,
                "reload_weapon": capture.WEAPON_NETNAME[
                    slot["weapon"]
                ],
                "reload_initial_clip": RELOAD_INITIAL_CLIP[
                    slot["weapon"]
                ],
                "reload_clip_capacity": RELOAD_CAPACITY[
                    slot["weapon"]
                ],
                "reload_start_server_tick": (
                    capture.WARMUP_TICKS
                    + capture.STAGE1_RELOAD_START_OUTPUT_TICK
                ),
                "reload_duration_ticks": (
                    capture.STAGE1_RELOAD_DURATION_TICKS
                ),
            }
        )
    elif weapon_action == "environmental_primary":
        row["acceptance"]["fire_required"] = True

    if enemy_present:
        policy_seed = (
            8_000_000 + ordinal * 101
            if wave == "primary"
            else 14_100_000 + ordinal * 101
        )
        policy = enemy_policy(
            slot["enemy_policy_name"],
            policy_seed,
        )
        row["enemy_policy"] = policy
        review.apply_enemy_policy_geometry(row)
        row["selected_geometry"] = {
            "source_pair": slot["selected_pair"]["source_probe"],
            "variant": slot["selected_pair"]["variant"],
        }
        row["enemy_path_certification"] = copy.deepcopy(
            slot["enemy_path_certification"]
        )
    row.update(
        {
            "data_spec_sha256": capture.sha256_file(
                ROOT / "XONOTIC_DATA_SPEC_V2.md"
            ),
            "training_stage": "stage1",
            "model_action_schema_version": (
                capture.MODEL_ACTION_SCHEMA_VERSION
            ),
            "primary_bucket": slot["primary_bucket"],
            "formal_collection_authorized": False,
            "formal_authorization_basis": (
                "manifest_distribution_validation_only_2026-07-27"
            ),
            "training_admitted": False,
            "acceptance_policy": capture.TIERED_REVIEW_POLICY,
            "candidate_wave": wave,
            "candidate_ordinal": ordinal,
            "assigned_shard": (ordinal - 1) % SHARD_COUNT,
            "shard_count": SHARD_COUNT,
            "source_commit_required": source_commit,
            "scheduler_targets": {
                "net_displacement_bin": slot["target_net_bin"],
                "yaw_range_bin": slot["target_yaw_bin"],
                "pitch_range_bin": slot["target_pitch_bin"],
                "path_length_floor": slot["path_length_floor"],
                "target_relation": slot.get("target_relation"),
                "distance_bin": slot.get("target_distance_bin"),
            },
            "appearance_id": (
                f"{enemy_model}_skin{enemy_skin}_color{enemy_color}"
                if enemy_present
                else None
            ),
            "counterfactual_group_id": (
                route_plan["route_group_id"]
                if route_plan
                else f"{row['map_region_id']}_{slot['primary_bucket']}"
            ),
        }
    )
    row["policy_labels"]["aim_overlay_reads_enemy"] = False
    row["policy_labels"]["route_policy_reads_enemy"] = False
    row["policy_labels"]["enemy_motion_reads_camera"] = False
    return row


def schedule(
    plans: list[dict[str, Any]],
    *,
    wave: str,
    scale_factor: int,
    seed_offset: int = 0,
) -> list[dict[str, Any]]:
    if scale_factor not in {1, REPLENISHMENT_SCALE, 10, 50}:
        raise AssertionError(scale_factor)
    if (
        isinstance(seed_offset, bool)
        or not isinstance(seed_offset, int)
        or not 0 <= seed_offset <= 1_000_000
    ):
        raise AssertionError(seed_offset)
    rng = random.Random(
        SCHEDULE_SEED
        + seed_offset
        + (0 if wave == "primary" else 1_000_000)
    )
    roles = (
        ROLE_COUNTS
        if scale_factor == 1
        else scaled_by(ROLE_COUNTS, scale_factor)
    )
    buckets = (
        BUCKET_COUNTS
        if scale_factor == 1
        else scaled_by(BUCKET_COUNTS, scale_factor)
    )
    bucket_roles = {
        bucket: (
            values
            if scale_factor == 1
            else scaled_by(values, scale_factor)
        )
        for bucket, values in BUCKET_ROLE_COUNTS.items()
    }
    net_counts = (
        NET_COUNTS
        if scale_factor == 1
        else scaled_by(NET_COUNTS, scale_factor)
    )
    yaw_counts = (
        YAW_COUNTS
        if scale_factor == 1
        else scaled_by(YAW_COUNTS, scale_factor)
    )
    pitch_counts = (
        PITCH_COUNTS
        if scale_factor == 1
        else scaled_by(PITCH_COUNTS, scale_factor)
    )
    relation_counts = (
        RELATION_COUNTS
        if scale_factor == 1
        else scaled_by(RELATION_COUNTS, scale_factor)
    )
    distance_counts = (
        DISTANCE_COUNTS
        if scale_factor == 1
        else scaled_by(DISTANCE_COUNTS, scale_factor)
    )
    policy_counts = (
        ENEMY_POLICY_COUNTS
        if scale_factor == 1
        else scaled_by(ENEMY_POLICY_COUNTS, scale_factor)
    )
    view_counts = (
        VIEW_COUNTS
        if scale_factor == 1
        else scaled_by(VIEW_COUNTS, scale_factor)
    )

    route_total = buckets["route_action"]
    route_enemy = bucket_roles["route_action"][
        "foundation_enemy_distractor"
    ]
    route_distances = route_distance_counts(distance_counts)
    route_slots = make_route_slots(
        plans,
        route_total=route_total,
        route_enemy=route_enemy,
        route_bucket=buckets["route_action"],
        high_bucket=0,
        route_enemy_bucket=bucket_roles["route_action"][
            "foundation_enemy_distractor"
        ],
        high_enemy_bucket=0,
        distance_counts=route_distances,
        view_counts=view_counts,
        rng=rng,
    )
    positions, pairs = preflight_pools()
    remaining_distances = {
        key: distance_counts[key] - route_distances[key]
        for key in distance_counts
    }
    nonroute_slots = make_nonroute_slots(
        positions,
        pairs,
        node_solo=bucket_roles["node_atomic"][
            "foundation_no_enemy"
        ],
        node_enemy=bucket_roles["node_atomic"][
            "foundation_enemy_distractor"
        ],
        high_solo=bucket_roles["high_motion_special"][
            "foundation_no_enemy"
        ],
        high_enemy=bucket_roles["high_motion_special"][
            "foundation_enemy_distractor"
        ],
        weapon_solo=bucket_roles["weapon_environment"][
            "foundation_no_enemy"
        ],
        weapon_enemy=bucket_roles["weapon_environment"][
            "foundation_enemy_distractor"
        ],
        distance_counts=remaining_distances,
        rng=rng,
    )

    slots = route_slots + nonroute_slots
    rng.shuffle(slots)
    assign_stratified_marginal(
        slots, "target_net_bin", net_counts, rng
    )
    assign_stratified_marginal(
        slots, "target_yaw_bin", yaw_counts, rng
    )
    assign_stratified_marginal(
        slots, "target_pitch_bin", pitch_counts, rng
    )

    enemy_slots = [
        slot
        for slot in slots
        if slot["dataset_role"]
        == "foundation_enemy_distractor"
    ]
    relations = shuffled_counts(relation_counts, rng)
    appearances = [
        (row["model"], int(row["skin"]))
        for row in v2.load_catalog()["enemy_appearances"]
    ]
    rng.shuffle(appearances)
    for index, (slot, relation) in enumerate(
        zip(enemy_slots, relations)
    ):
        slot["target_relation"] = relation
        slot["appearance"] = appearances[index % len(appearances)]
    assign_path_safe_enemy_policies(
        enemy_slots, pairs, policy_counts, rng
    )

                                                                         
                                                                         
    high_slots = [
        slot
        for slot in slots
        if slot["primary_bucket"] == "high_motion_special"
    ]
    rng.shuffle(high_slots)
    ge2000 = 6_000 // scale_factor
    for slot in slots:
        slot["path_length_floor"] = 0
    for slot in high_slots[:ge2000]:
        slot["path_length_floor"] = 2_000
    remaining_ge1000 = 18_000 // scale_factor - ge2000
    candidates = [
        slot
        for slot in route_slots
        if slot["path_length_floor"] == 0
    ]
    rng.shuffle(candidates)
    for slot in candidates[:remaining_ge1000]:
        slot["path_length_floor"] = 1_000

    assign_action_design(slots, scale_factor, rng)

    prefix = "s1f" if wave == "primary" else "s1r"
    rows = [
        scenario_from_slot(
            slot,
            episode_id=f"{prefix}_{ordinal:06d}",
            ordinal=ordinal,
            wave=wave,
            source_commit=SOURCE_COMMIT,
        )
        for ordinal, slot in enumerate(slots, 1)
    ]
    audit_rows(
        rows,
        expected_count=sum(roles.values()),
        role_counts=roles,
        bucket_counts=buckets,
        bucket_role_counts=bucket_roles,
        net_counts=net_counts,
        yaw_counts=yaw_counts,
        pitch_counts=pitch_counts,
        relation_counts=relation_counts,
        distance_counts=distance_counts,
        policy_counts=policy_counts,
        view_counts=view_counts,
    )
    return rows


def audit_rows(
    rows: list[dict[str, Any]],
    *,
    expected_count: int,
    role_counts: dict[str, int],
    bucket_counts: dict[str, int],
    bucket_role_counts: dict[str, dict[str, int]],
    net_counts: dict[str, int],
    yaw_counts: dict[str, int],
    pitch_counts: dict[str, int],
    relation_counts: dict[str, int],
    distance_counts: dict[str, int],
    policy_counts: dict[str, int],
    view_counts: dict[str, int],
) -> dict[str, Any]:
    enemy = [row for row in rows if row["enemy_present"]]
    route_rows = [row for row in rows if row.get("route_request")]
    enemy_path_preflight_sha256 = capture.sha256_file(
        ENEMY_PATH_PREFLIGHT_PATH
    )
    joint = sum(
        row["scheduler_targets"]["net_displacement_bin"]
        in {"512_1024", "gt1024"}
        and row["scheduler_targets"]["yaw_range_bin"]
        in {"90_180", "ge180"}
        for row in rows
    )
    if PRIMARY_COUNT % expected_count:
        raise AssertionError((PRIMARY_COUNT, expected_count))
    action_scale_factor = PRIMARY_COUNT // expected_count
    weapon_action_targets = {
        mode: count // action_scale_factor
        for mode, count in WEAPON_ACTION_COUNTS.items()
    }
    weapon_action_role_targets = {
        mode: {
            role: count // action_scale_factor
            for role, count in counts.items()
        }
        for mode, counts in WEAPON_ACTION_ROLE_COUNTS.items()
    }
    action_designs = [row["action_design"] for row in rows]
    nonroute_rows = [
        row for row in rows if not row.get("route_request")
    ]
    weapon_action_counts = Counter(
        design["weapon_action"] for design in action_designs
    )
    locomotion_counts = Counter(
        row["action_design"]["locomotion_direction"]
        for row in nonroute_rows
    )
    view_direction_counts = Counter(
        design["view_direction"] for design in action_designs
    )
    movement_profile_counts = Counter(
        row["action_design"]["movement_profile"]
        for row in nonroute_rows
        if row["action_design"]["locomotion_direction"] != "idle"
    )
    view_profile_counts = Counter(
        design["view_profile"] for design in action_designs
    )
    reload_rows = [
        row
        for row in rows
        if row["action_design"]["weapon_action"] == "reload"
    ]
    fire_rows = [
        row
        for row in rows
        if row["action_design"]["weapon_action"]
        == "environmental_primary"
    ]
    moving_designs = [
        row["action_design"]
        for row in nonroute_rows
        if row["action_design"]["locomotion_direction"] != "idle"
    ]
    movement_magnitudes = [
        float(design["movement_xy_magnitude"])
        for design in moving_designs
    ]
    active_yaw_amplitudes = [
        abs(float(design["yaw_amplitude"]))
        for design in action_designs
        if float(design["yaw_amplitude"]) != 0.0
    ]
    active_pitch_amplitudes = [
        abs(float(design["pitch_amplitude"]))
        for design in action_designs
        if float(design["pitch_amplitude"]) != 0.0
    ]
    checks = {
        "rows": len(rows) == expected_count,
        "unique_episode_ids": len(
            {row["episode_id"] for row in rows}
        )
        == expected_count,
        "roles": Counter(row["dataset_role"] for row in rows)
        == Counter(role_counts),
        "buckets": Counter(row["primary_bucket"] for row in rows)
        == Counter(bucket_counts),
        "bucket_roles": all(
            Counter(
                row["dataset_role"]
                for row in rows
                if row["primary_bucket"] == bucket
            )
            == Counter(counts)
            for bucket, counts in bucket_role_counts.items()
        ),
        "net": Counter(
            row["scheduler_targets"]["net_displacement_bin"]
            for row in rows
        )
        == Counter(net_counts),
        "yaw": Counter(
            row["scheduler_targets"]["yaw_range_bin"]
            for row in rows
        )
        == Counter(yaw_counts),
        "pitch": Counter(
            row["scheduler_targets"]["pitch_range_bin"]
            for row in rows
        )
        == Counter(pitch_counts),
        "relation": Counter(
            row["scheduler_targets"]["target_relation"]
            for row in enemy
        )
        == Counter(relation_counts),
        "distance": Counter(
            row["scheduler_targets"]["distance_bin"]
            for row in enemy
        )
        == Counter(distance_counts),
        "enemy_policy": Counter(
            row["enemy_policy"]["name"] for row in enemy
        )
        == Counter(policy_counts),
        "enemy_path_preflight": all(
            row["enemy_path_certification"]["certified"] is True
            and row["enemy_path_certification"][
                "preflight_sha256"
            ]
            == enemy_path_preflight_sha256
            for row in enemy
        ),
        "policy_distance_crossed": all(
            {
                row["scheduler_targets"]["distance_bin"]
                for row in enemy
                if row["enemy_policy"]["name"] == policy
            }
            == set(distance_counts)
            for policy in policy_counts
        ),
        "policy_relation_crossed": all(
            {
                row["scheduler_targets"]["target_relation"]
                for row in enemy
                if row["enemy_policy"]["name"] == policy
            }
            == set(relation_counts)
            for policy in policy_counts
        ),
        "policy_map_crossed": all(
            len(
                {
                    row["map"]
                    for row in enemy
                    if row["enemy_policy"]["name"] == policy
                }
            )
            >= 10
            for policy in policy_counts
        ),
        "view_policy": Counter(
            row["route_view_policy"] for row in route_rows
        )
        == Counter(view_counts),
        "route_rows": len(route_rows)
        == bucket_counts["route_action"],
        "high_motion_nonroute": all(
            not row.get("route_request")
            for row in rows
            if row["primary_bucket"] == "high_motion_special"
        ),
        "path_ge1000": sum(
            row["scheduler_targets"]["path_length_floor"] >= 1_000
            for row in rows
        )
        >= expected_count * 30 // 100,
        "path_ge2000": sum(
            row["scheduler_targets"]["path_length_floor"] >= 2_000
            for row in rows
        )
        >= expected_count * 10 // 100,
        "joint_net_yaw": joint >= expected_count * 10 // 100,
        "formal_not_authorized": all(
            row["formal_collection_authorized"] is False
            for row in rows
        ),
        "input_not_preadmitted": all(
            row["training_admitted"] is False for row in rows
        ),
        "shard_assignment": all(
            row["assigned_shard"]
            == (row["candidate_ordinal"] - 1) % SHARD_COUNT
            and row["shard_count"] == SHARD_COUNT
            for row in rows
        ),
        "anti_coupling": all(
            not row["enemy_policy"]["runtime_reads_player_state"]
            and not row["enemy_policy"]["reads_camera"]
            and not row["enemy_policy"]["reads_crosshair"]
            and not row["enemy_policy"]["fires"]
            for row in enemy
        ),
        "policy_seed_float_exact": all(
            int(np.float32(row["enemy_policy"]["policy_seed"]))
            == row["enemy_policy"]["policy_seed"]
            for row in enemy
        ),
        "policy_seed_unique": len(
            {
                row["enemy_policy"]["policy_seed"]
                for row in enemy
            }
        )
        == len(enemy),
        "action_design_present": len(action_designs) == expected_count,
        "model_action_schema": all(
            row.get("model_action_schema_version")
            == capture.MODEL_ACTION_SCHEMA_VERSION
            and row["action_design"].get(
                "model_action_schema_version"
            )
            == capture.MODEL_ACTION_SCHEMA_VERSION
            and row["action_design"].get("schema_version")
            == "xonotic-stage1-action-design-v4"
            for row in rows
        ),
        "movement_action_continuous_range": (
            bool(movement_magnitudes)
            and min(movement_magnitudes) > 0.0
            and max(movement_magnitudes) <= 1.0
            and len(set(movement_magnitudes)) >= 100
            and all(
                float(row["action_design"]["movement_xy_magnitude"])
                == 0.0
                for row in nonroute_rows
                if row["action_design"]["locomotion_direction"]
                == "idle"
            )
        ),
        "view_action_continuous_amplitudes": (
            len(set(active_yaw_amplitudes)) >= 100
            and len(set(active_pitch_amplitudes)) >= 100
        ),
        "weapon_action_targets": weapon_action_counts
        == Counter(
            {
                "none": expected_count
                - sum(weapon_action_targets.values()),
                **weapon_action_targets,
            }
        ),
        "weapon_action_role_ratio": all(
            Counter(
                row["dataset_role"]
                for row in rows
                if row["action_design"]["weapon_action"] == mode
            )
            == Counter(role_targets)
            for mode, role_targets in (
                weapon_action_role_targets.items()
            )
        ),
        "locomotion_direction_coverage": (
            set(LOCOMOTION_DIRECTIONS) <= set(locomotion_counts)
        ),
        "movement_profile_coverage": (
            set(TEMPORAL_PROFILES) <= set(movement_profile_counts)
        ),
        "view_direction_coverage": (
            set(capture.STAGE1_VIEW_SIGNS)
            <= set(view_direction_counts)
        ),
        "view_profile_coverage": (
            set(TEMPORAL_PROFILES) <= set(view_profile_counts)
        ),
        "action_arity_coverage": {
            "atomic",
            "pairwise",
            "three_way",
        }
        <= {
            design["action_arity"] for design in action_designs
        },
        "weapon_select_and_zoom_absent": all(
            design["weapon_select"] is False
            and design["zoom"] is False
            for design in action_designs
        ),
        "weapon_uniform_approx": (
            max(Counter(row["weapon"] for row in rows).values())
            - min(Counter(row["weapon"] for row in rows).values())
            <= 1
        ),
        "primary_weapon_coverage": {
            row["weapon"]
            for row in rows
            if row["action_design"]["weapon_action"]
            == "environmental_primary"
        }
        == set(WEAPONS),
        "secondary_action_absent": not any(
            row["action_design"]["weapon_action"]
            == "environmental_secondary"
            for row in rows
        ),
        "reload_weapon_contract": {
            row["weapon"] for row in reload_rows
        }
        == set(RELOAD_WEAPONS),
        "reload_acceptance_contract": all(
            row["acceptance"]["reload_success"] is True
            and row["acceptance"]["reload_weapon"]
            == row["weapon_netname"]
            and float(row["player"]["clip"])
            < RELOAD_CAPACITY[row["weapon"]]
            and float(
                row["acceptance"]["reload_initial_clip"]
            )
            == RELOAD_INITIAL_CLIP[row["weapon"]]
            and float(
                row["acceptance"]["reload_clip_capacity"]
            )
            == RELOAD_CAPACITY[row["weapon"]]
            and int(
                row["acceptance"]["reload_start_server_tick"]
            )
            == (
                capture.WARMUP_TICKS
                + capture.STAGE1_RELOAD_START_OUTPUT_TICK
            )
            and int(
                row["acceptance"]["reload_duration_ticks"]
            )
            == capture.STAGE1_RELOAD_DURATION_TICKS
            for row in reload_rows
        ),
        "fire_acceptance_contract": all(
            row["acceptance"]["fire_required"] is True
            for row in fire_rows
        ),
        "enemy_fire_safe_relation": all(
            row["scheduler_targets"]["target_relation"]
            in {
                "offscreen_or_occluded",
                "visible_far",
                "near_crosshair",
            }
            for row in fire_rows
            if row["enemy_present"]
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage1_manifest_audit_failed",
            capture.canonical_json(checks),
        )
    return {
        "checks": checks,
        "joint_net_yaw_count": joint,
        "weapon_action": dict(weapon_action_counts),
        "locomotion_direction": dict(locomotion_counts),
        "movement_profile": dict(movement_profile_counts),
        "view_direction": dict(view_direction_counts),
        "view_profile": dict(view_profile_counts),
        "continuous_action": {
            "movement_unique_magnitudes": len(
                set(movement_magnitudes)
            ),
            "movement_magnitude_min": min(movement_magnitudes),
            "movement_magnitude_max": max(movement_magnitudes),
            "yaw_unique_active_amplitudes": len(
                set(active_yaw_amplitudes)
            ),
            "pitch_unique_active_amplitudes": len(
                set(active_pitch_amplitudes)
            ),
        },
    }


def write_shards(
    rows: list[dict[str, Any]], wave: str
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        selected = [
            row
            for row in rows
            if row["assigned_shard"] == shard_index
        ]
        path = (
            SHARD_ROOT
            / wave
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        text = canonical_lines(selected)
        write_once_or_verify(path, text)
        result.append(
            {
                "shard_index": shard_index,
                "rows": len(selected),
                "path": str(path.relative_to(ROOT)),
                "sha256": digest_text(text),
            }
        )
    return result


def launch_guard() -> str:
    return "\n".join(
        (
            "STAGE-1 V4 FULL COLLECTION IS NOT AUTHORIZED YET.",
            "",
            "This manifest is a deterministic distribution candidate.",
            "Review the fixed-seed uniform random sample before promotion.",
            "Do not launch the 32 full shards from this directory.",
            "",
        )
    )


def materialize() -> dict[str, Any]:
    build = capture.build_root()
    source_commit = (build / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if source_commit != SOURCE_COMMIT:
        raise capture.CaptureFailure(
            "stage1_source_commit_mismatch",
            f"expected={SOURCE_COMMIT} actual={source_commit}",
        )
    enemy_path_preflight = ensure_enemy_path_preflight()
    plans = ensure_route_library()
    primary = schedule(
        plans, wave="primary", scale_factor=1
    )
    replenishment = schedule(
        plans,
        wave="replenishment",
        scale_factor=REPLENISHMENT_SCALE,
    )
    primary_text = canonical_lines(primary)
    replenishment_text = canonical_lines(replenishment)
    write_once_or_verify(INPUT_PATH, primary_text)
    write_once_or_verify(REPLENISHMENT_PATH, replenishment_text)
    primary_shards = write_shards(primary, "primary")
    replenishment_shards = write_shards(
        replenishment, "replenishment"
    )
    launch_guard_text = launch_guard()
    write_once_or_verify(LAUNCH_GUARD_PATH, launch_guard_text)
    created_utc = (
        json.loads(METADATA_PATH.read_text(encoding="utf-8"))[
            "created_utc"
        ]
        if METADATA_PATH.exists()
        else capture.utc_now()
    )
    metadata = {
        "schema_version": "xonotic-stage1-distribution-manifest-v4",
        "created_utc": created_utc,
        "source_commit": SOURCE_COMMIT,
        "build": str(build),
        "formal_collection_authorized": False,
        "formal_authorization_basis": (
            "pending_fixed_seed_uniform_random_review_2026-07-27"
        ),
        "training_admitted": False,
        "model_action_contract": capture.model_action_contract(),
        "continuous_candidate_ranges": {
            "movement_xy_magnitude": MOVEMENT_MAGNITUDE_RANGES,
            "high_motion_xy_magnitude": (
                HIGH_MOTION_MAGNITUDE_RANGE
            ),
            "yaw_amplitude_degrees": YAW_AMPLITUDE_RANGES,
            "pitch_amplitude_degrees": PITCH_AMPLITUDE_RANGES,
        },
        "shard_count": SHARD_COUNT,
        "shard_method": (
            "canonical candidate ordinal round-robin: "
            "(candidate_ordinal - 1) mod 32"
        ),
        "launch": {
            "status": "blocked_pending_uniform_random_review",
            "topology_after_authorization": (
                "32 independent one-GPU tasks"
            ),
            "launch_guard_path": str(
                LAUNCH_GUARD_PATH.relative_to(ROOT)
            ),
            "launch_guard_sha256": digest_text(launch_guard_text),
        },
        "route_library": {
            "rows": len(plans),
            "path": str(ROUTE_INDEX_PATH.relative_to(ROOT)),
            "sha256": capture.sha256_file(ROUTE_INDEX_PATH),
            "calibration_policy": (
                "one locked authoritative calibration per route, "
                "then immutable frozen replay"
            ),
        },
        "enemy_path_preflight": {
            "path": str(
                ENEMY_PATH_PREFLIGHT_PATH.relative_to(ROOT)
            ),
            "sha256": capture.sha256_file(
                ENEMY_PATH_PREFLIGHT_PATH
            ),
            "source_commit": enemy_path_preflight["source_commit"],
            "runtime_source_commit": SOURCE_COMMIT,
            "compatibility_basis": (
                "the final b40 source adds player collision telemetry and "
                "hard gates without changing the certified enemy paths; "
                "every enemy episode repeats the whole-path trace gate"
            ),
            "assignment_policy": (
                "exact policy quota max-flow over live-certified "
                "pair/path envelopes"
            ),
            "runtime_policy": (
                "repeat whole-path trace for every episode"
            ),
        },
        "primary": {
            "rows": len(primary),
            "path": str(INPUT_PATH.relative_to(ROOT)),
            "sha256": digest_text(primary_text),
            "rows_per_shard": PRIMARY_COUNT // SHARD_COUNT,
            "shards": primary_shards,
        },
        "replenishment": {
            "rows": len(replenishment),
            "path": str(REPLENISHMENT_PATH.relative_to(ROOT)),
            "sha256": digest_text(replenishment_text),
            "rows_per_shard": (
                REPLENISHMENT_COUNT // SHARD_COUNT
            ),
            "shards": replenishment_shards,
            "launch_policy": (
                "never launch wholesale; quota audit selects only "
                "deficient realized cells"
            ),
        },
        "planned_quotas": {
            "roles": ROLE_COUNTS,
            "primary_buckets": BUCKET_COUNTS,
            "bucket_roles": BUCKET_ROLE_COUNTS,
            "net_displacement": NET_COUNTS,
            "yaw_range": YAW_COUNTS,
            "pitch_range": PITCH_COUNTS,
            "target_relation": RELATION_COUNTS,
            "distance": DISTANCE_COUNTS,
            "enemy_policy": ENEMY_POLICY_COUNTS,
            "route_view_policy": VIEW_COUNTS,
            "weapon_action": {
                **WEAPON_ACTION_COUNTS,
                "environmental_secondary": 0,
            },
            "secondary_action_policy": (
                "LT remains in the model schema but is fixed to zero in "
                "Stage 1"
            ),
            "reload_action_policy": {
                "start_output_tick": (
                    capture.STAGE1_RELOAD_START_OUTPUT_TICK
                ),
                "duration_ticks": (
                    capture.STAGE1_RELOAD_DURATION_TICKS
                ),
                "acceptance": (
                    "one linked reload_start/reload_complete chain, exact "
                    "weapon and timing, clip reaches capacity, reserve drops"
                ),
            },
            "locomotion_direction_policy": (
                "approximately uniform over idle, four cardinals, "
                "and four diagonals within non-route strata"
            ),
            "movement_profile_policy": (
                "approximately uniform over eight temporal profiles"
            ),
            "view_direction_policy": (
                "sign-balanced within yaw/pitch magnitude bins"
            ),
            "view_profile_policy": (
                "approximately uniform over eight temporal profiles"
            ),
            "realized_acceptance_tolerance": (
                "up to 10% relative marginal drift before targeted "
                "replenishment"
            ),
        },
    }
    write_once_or_verify(
        METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    return metadata


def audit_persisted() -> dict[str, Any]:
    metadata = json.loads(
        METADATA_PATH.read_text(encoding="utf-8")
    )
    primary = capture.load_jsonl(INPUT_PATH)
    replenishment = capture.load_jsonl(REPLENISHMENT_PATH)
    primary_distribution = audit_rows(
        primary,
        expected_count=PRIMARY_COUNT,
        role_counts=ROLE_COUNTS,
        bucket_counts=BUCKET_COUNTS,
        bucket_role_counts=BUCKET_ROLE_COUNTS,
        net_counts=NET_COUNTS,
        yaw_counts=YAW_COUNTS,
        pitch_counts=PITCH_COUNTS,
        relation_counts=RELATION_COUNTS,
        distance_counts=DISTANCE_COUNTS,
        policy_counts=ENEMY_POLICY_COUNTS,
        view_counts=VIEW_COUNTS,
    )
    replenishment_distribution = audit_rows(
        replenishment,
        expected_count=REPLENISHMENT_COUNT,
        role_counts=scaled(ROLE_COUNTS),
        bucket_counts=scaled(BUCKET_COUNTS),
        bucket_role_counts={
            bucket: scaled(values)
            for bucket, values in BUCKET_ROLE_COUNTS.items()
        },
        net_counts=scaled(NET_COUNTS),
        yaw_counts=scaled(YAW_COUNTS),
        pitch_counts=scaled(PITCH_COUNTS),
        relation_counts=scaled(RELATION_COUNTS),
        distance_counts=scaled(DISTANCE_COUNTS),
        policy_counts=scaled(ENEMY_POLICY_COUNTS),
        view_counts=scaled(VIEW_COUNTS),
    )
    route_requests: dict[str, dict[str, Any]] = {}
    route_requests_consistent = True
    for row in primary:
        request = row.get("route_request")
        if not request:
            continue
        route_id = str(request["route_id"])
        if (
            route_id in route_requests
            and route_requests[route_id] != request
        ):
            route_requests_consistent = False
        route_requests[route_id] = request
    shard_validated_rows = 0
    shard_validated_shards = 0
    for wave in ("primary", "replenishment"):
        for shard in metadata[wave]["shards"]:
            shard_index = int(shard["shard_index"])
            shard_path = ROOT / shard["path"]
            shard_rows = capture.load_jsonl(shard_path)
            shard_sha256 = capture.sha256_file(shard_path)
            if (
                shard_sha256 != shard["sha256"]
                or len(shard_rows) != int(shard["rows"])
                or any(
                    row["candidate_wave"] != wave
                    or row["assigned_shard"] != shard_index
                    or row["shard_count"] != SHARD_COUNT
                    or row["source_commit_required"] != SOURCE_COMMIT
                    or row["formal_collection_authorized"] is not False
                    or row["training_admitted"] is not False
                    or (
                        row.get("enemy_present")
                        and row["enemy_path_certification"][
                            "preflight_sha256"
                        ]
                        != metadata["enemy_path_preflight"]["sha256"]
                    )
                    for row in shard_rows
                )
            ):
                raise capture.CaptureFailure(
                    "stage1_worker_input_validation_failed",
                    f"wave={wave} shard={shard_index}",
                )
            shard_validated_rows += len(shard_rows)
            shard_validated_shards += 1
    checks = {
        "source_commit": metadata["source_commit"] == SOURCE_COMMIT,
        "primary_sha256": capture.sha256_file(INPUT_PATH)
        == metadata["primary"]["sha256"],
        "replenishment_sha256": capture.sha256_file(
            REPLENISHMENT_PATH
        )
        == metadata["replenishment"]["sha256"],
        "route_index_sha256": capture.sha256_file(ROUTE_INDEX_PATH)
        == metadata["route_library"]["sha256"],
        "enemy_path_preflight_sha256": capture.sha256_file(
            ENEMY_PATH_PREFLIGHT_PATH
        )
        == metadata["enemy_path_preflight"]["sha256"],
        "primary_rows": len(primary) == PRIMARY_COUNT,
        "replenishment_rows": len(replenishment)
        == REPLENISHMENT_COUNT,
        "primary_shards": all(
            capture.sha256_file(ROOT / row["path"])
            == row["sha256"]
            and len(capture.load_jsonl(ROOT / row["path"]))
            == row["rows"]
            == PRIMARY_COUNT // SHARD_COUNT
            for row in metadata["primary"]["shards"]
        ),
        "replenishment_shards": all(
            capture.sha256_file(ROOT / row["path"])
            == row["sha256"]
            and len(capture.load_jsonl(ROOT / row["path"]))
            == row["rows"]
            == REPLENISHMENT_COUNT // SHARD_COUNT
            for row in metadata["replenishment"]["shards"]
        ),
        "route_locks": all(
            capture.sha256_file(
                ROOT / request["route_plan_path"]
            )
            == request["route_plan_sha256"]
            and capture.sha256_file(
                ROOT / request["route_csv_path"]
            )
            == request["route_csv_sha256"]
            for request in route_requests.values()
        )
        and route_requests_consistent
        and len(route_requests) == ROUTE_COUNT,
        "launch_blocked": (
            metadata["formal_collection_authorized"] is False
            and metadata["training_admitted"] is False
            and metadata["launch"]["status"]
            == "blocked_pending_uniform_random_review"
            and capture.sha256_file(LAUNCH_GUARD_PATH)
            == metadata["launch"]["launch_guard_sha256"]
        ),
        "shard_input_policy": shard_validated_shards
        == 2 * SHARD_COUNT
        and shard_validated_rows
        == PRIMARY_COUNT + REPLENISHMENT_COUNT,
        "primary_distribution": all(
            primary_distribution["checks"].values()
        ),
        "replenishment_distribution": all(
            replenishment_distribution["checks"].values()
        ),
    }
    report = {
        "schema_version": "xonotic-stage1-manifest-audit-v1",
        "created_utc": capture.utc_now(),
        "checks": checks,
        "passed": all(checks.values()),
        "primary_sha256": capture.sha256_file(INPUT_PATH),
        "replenishment_sha256": capture.sha256_file(
            REPLENISHMENT_PATH
        ),
        "metadata_sha256": capture.sha256_file(METADATA_PATH),
        "route_index_sha256": capture.sha256_file(ROUTE_INDEX_PATH),
        "shard_validated_shards": shard_validated_shards,
        "shard_validated_rows": shard_validated_rows,
        "distribution_audit": {
            "primary": primary_distribution,
            "replenishment": replenishment_distribution,
        },
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = AUDIT_PATH.with_name(
        f".{AUDIT_PATH.name}.tmp.{os.getpid()}"
    )
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, AUDIT_PATH)
    if not report["passed"]:
        raise capture.CaptureFailure(
            "stage1_persisted_manifest_audit_failed",
            capture.canonical_json(checks),
        )
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "command", choices=("routes", "materialize", "audit", "all")
    )
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    try:
        output: Any
        if args.command == "routes":
            plans = ensure_route_library()
            output = {
                "routes": len(plans),
                "index": str(ROUTE_INDEX_PATH),
                "sha256": capture.sha256_file(ROUTE_INDEX_PATH),
            }
        elif args.command == "materialize":
            output = materialize()
        elif args.command == "audit":
            output = audit_persisted()
        else:
            materialize()
            output = audit_persisted()
        print(json.dumps(output, indent=2, sort_keys=True))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
