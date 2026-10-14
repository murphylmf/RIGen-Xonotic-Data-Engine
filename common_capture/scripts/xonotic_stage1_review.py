                      
"""Collect a bounded, Stage-1-only FOV90 distribution review set.

This is deliberately a non-training split.  It samples the declared Stage 1
marginals over all admitted official maps, then accepts rows only after the
real authoritative motion, camera, target-relation, and distance bins match.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import html
import json
import math
import os
import subprocess
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finalize_v2_pilot as final_audit              
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              
import xonotic_motion_distance_pilot as motion              


ROOT = capture.ROOT
SPLIT = "v2_stage1_review_fov90"
REVIEW_ROOT = ROOT / SPLIT
SCENARIOS_PATH = ROOT / f"configs/{SPLIT}_scenarios.jsonl"
ACCEPTED_PATH = REVIEW_ROOT / "manifests/accepted.jsonl"
REJECTS_PATH = REVIEW_ROOT / "manifests/rejects.jsonl"
SUMMARY_PATH = REVIEW_ROOT / "REVIEW_SUMMARY.json"
PREFLIGHT_PATH = REVIEW_ROOT / "FOV90_PREFLIGHT.json"
AUDIT_PATH = REVIEW_ROOT / "FINAL_AUDIT.json"
REPORT_PATH = REVIEW_ROOT / "STAGE1_REVIEW_REPORT.md"
PREVIEW_ROOT = ROOT / "previews/stage1_review_fov90"
WRITE_LOCK = threading.Lock()
SEED = 9_001_337
EXPECTED_COUNT = 60
                                                                             
                                                                            
                                                                            
                   
STAGE1_RENDER_EXCLUDED_MAPS = {"nexballarena"}

ROLE_COUNTS = {
    "foundation_no_enemy": 45,
    "foundation_enemy_distractor": 15,
}
BUCKET_COUNTS = {
    "node_atomic": 26,
    "mixed_action": 20,
    "high_motion_special": 8,
    "weapon_environment": 6,
}
NET_COUNTS = {
    "lt64": 9,
    "64_256": 12,
    "256_512": 15,
    "512_1024": 15,
    "gt1024": 9,
}
YAW_COUNTS = {
    "lt15": 18,
    "15_45": 15,
    "45_90": 9,
    "90_180": 12,
    "ge180": 6,
}
PITCH_COUNTS = {
    "lt5": 27,
    "5_15": 15,
    "15_30": 12,
    "ge30": 6,
}
DISTANCE_COUNTS = {
    "close": 4,
    "near": 5,
    "medium": 3,
    "far": 2,
    "very_far": 1,
}
RELATION_COUNTS = {
    "offscreen_or_occluded": 4,
    "visible_far": 5,
    "near_crosshair": 3,
    "brief_center_pass": 2,
    "center_linger": 1,
}

ENEMY_POLICY_COUNTS = {
    "idle": 3,
    "lateral_patrol": 4,
    "approach_retreat": 4,
    "stop_and_go": 4,
}
ENEMY_POLICY_SEQUENCE = (
    "idle",
    "lateral_patrol",
    "approach_retreat",
    "stop_and_go",
    "lateral_patrol",
    "approach_retreat",
    "stop_and_go",
    "idle",
    "lateral_patrol",
    "approach_retreat",
    "stop_and_go",
    "lateral_patrol",
    "approach_retreat",
    "stop_and_go",
    "idle",
)
ENEMY_POLICY_MOTION_MODE = {
    "idle": 0,
    "lateral_patrol": 1,
    "approach_retreat": 2,
    "stop_and_go": 3,
}
ENEMY_POLICY_BASE_AMPLITUDE = {
    "idle": 0.0,
    "lateral_patrol": 48.0,
    "approach_retreat": 48.0,
    "stop_and_go": 48.0,
}


def capture_gametype_for_map(map_name: str) -> str:
    map_spec = v2.load_catalog()["maps"].get(map_name)
    if map_spec is None:
        raise capture.CaptureFailure(
            "stage1_map_missing_from_official_catalog", map_name
        )
    gametype = str(map_spec.get("preflight_gametype", "")).lower()
    if not gametype:
        raise capture.CaptureFailure(
            "stage1_map_gametype_missing", map_name
        )
    if gametype not in map_spec.get("gametypes", []):
        raise capture.CaptureFailure(
            "stage1_map_gametype_not_supported",
            f"map={map_name} gametype={gametype}",
        )
    return gametype


BUCKET_NET = {
    "node_atomic": {
        "lt64": 6,
        "64_256": 6,
        "256_512": 6,
        "512_1024": 5,
        "gt1024": 3,
    },
    "mixed_action": {
        "lt64": 0,
        "64_256": 3,
        "256_512": 9,
        "512_1024": 6,
        "gt1024": 2,
    },
    "high_motion_special": {
        "lt64": 0,
        "64_256": 0,
        "256_512": 0,
        "512_1024": 4,
        "gt1024": 4,
    },
    "weapon_environment": {
        "lt64": 3,
        "64_256": 3,
        "256_512": 0,
        "512_1024": 0,
        "gt1024": 0,
    },
}
BUCKET_YAW = {
    "node_atomic": {
        "lt15": 12,
        "15_45": 7,
        "45_90": 3,
        "90_180": 3,
        "ge180": 1,
    },
    "mixed_action": {
        "lt15": 2,
        "15_45": 6,
        "45_90": 5,
        "90_180": 5,
        "ge180": 2,
    },
    "high_motion_special": {
        "lt15": 0,
        "15_45": 0,
        "45_90": 1,
        "90_180": 4,
        "ge180": 3,
    },
    "weapon_environment": {
        "lt15": 4,
        "15_45": 2,
        "45_90": 0,
        "90_180": 0,
        "ge180": 0,
    },
}
BUCKET_PITCH = {
    "node_atomic": {
        "lt5": 16,
        "5_15": 5,
        "15_30": 4,
        "ge30": 1,
    },
    "mixed_action": {
        "lt5": 5,
        "5_15": 7,
        "15_30": 5,
        "ge30": 3,
    },
    "high_motion_special": {
        "lt5": 1,
        "5_15": 2,
        "15_30": 3,
        "ge30": 2,
    },
    "weapon_environment": {
        "lt5": 5,
        "5_15": 1,
        "15_30": 0,
        "ge30": 0,
    },
}

NET_RANK = {
    "lt64": 0,
    "64_256": 1,
    "256_512": 2,
    "512_1024": 3,
    "gt1024": 4,
}
DISTANCE_RANK = {
    "close": 1,
    "near": 2,
    "medium": 3,
    "far": 4,
    "very_far": 5,
    "extreme": 6,
}
NET_REQUIRED_PAIR_RANK = {
    "lt64": 1,
    "64_256": 1,
    "256_512": 2,
    "512_1024": 3,
    "gt1024": 5,
}
YAW_AMPLITUDE = {
    "lt15": 8.0,
    "15_45": 30.0,
    "45_90": 65.0,
    "90_180": 120.0,
    "ge180": 220.0,
}
PITCH_AMPLITUDE = {
    "lt5": 0.0,
    "5_15": 10.0,
    "15_30": 22.0,
    "ge30": 45.0,
}
MOVE_DURATIONS = {
    "lt64": (0,),
    "64_256": (28, 36, 44, 52),
    "256_512": (80, 96, 112, 128),
    "512_1024": (144, 168, 192, 216),
    "gt1024": (240, 264, 288, 312),
}
LEGACY_REQUIRED_FILES = {
    "episode.json",
    "video.mkv",
    "actions.parquet",
    "states.parquet",
    "events.parquet",
    "frames.parquet",
    "audio_events.parquet",
    "target_relations.parquet",
    "qa.json",
}
REQUIRED_FILES = LEGACY_REQUIRED_FILES | {"model_actions.parquet"}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_text(
        path,
        "".join(capture.canonical_json(row) + "\n" for row in rows),
    )


def expand_counts(counts: dict[str, int]) -> list[str]:
    return [
        name
        for name, count in counts.items()
        for _ in range(int(count))
    ]


def direction_yaw(start: list[float], end: list[float]) -> float:
    return math.degrees(
        math.atan2(end[1] - start[1], end[0] - start[0])
    )


def pair_variants(pair: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **pair,
            "player_origin": list(pair["player_origin"]),
            "enemy_origin": list(pair["enemy_origin"]),
            "variant": "forward",
        },
        {
            **pair,
            "player_origin": list(pair["enemy_origin"]),
            "enemy_origin": list(pair["player_origin"]),
            "variant": "reverse",
        },
    ]


def slot_rows(rng: np.random.Generator) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for bucket, count in BUCKET_COUNTS.items():
        nets = expand_counts(BUCKET_NET[bucket])
        yaws = expand_counts(BUCKET_YAW[bucket])
        pitches = expand_counts(BUCKET_PITCH[bucket])
        if not (len(nets) == len(yaws) == len(pitches) == count):
            raise AssertionError(bucket)
        rng.shuffle(nets)
        rng.shuffle(yaws)
        rng.shuffle(pitches)
        slots.extend(
            {
                "primary_bucket": bucket,
                "target_net_bin": net,
                "target_yaw_bin": yaw,
                "target_pitch_bin": pitch,
            }
            for net, yaw, pitch in zip(nets, yaws, pitches)
        )
    rng.shuffle(slots)
    if sum(
        NET_RANK[row["target_net_bin"]] >= NET_RANK["512_1024"]
        and row["target_yaw_bin"] in {"90_180", "ge180"}
        for row in slots
    ) < 6:
        return slot_rows(rng)
    return slots


def enemy_relation_requirements() -> list[dict[str, str]]:
    return [
        {"relation": "offscreen_or_occluded", "yaw": "lt15"},
        {"relation": "offscreen_or_occluded", "yaw": "15_45"},
        {"relation": "offscreen_or_occluded", "yaw": "45_90"},
        {"relation": "offscreen_or_occluded", "yaw": "90_180"},
        {"relation": "visible_far", "yaw": "lt15"},
        {"relation": "visible_far", "yaw": "15_45"},
        {"relation": "visible_far", "yaw": "45_90"},
        {"relation": "visible_far", "yaw": "90_180"},
        {"relation": "visible_far", "yaw": "ge180"},
        {"relation": "near_crosshair", "yaw": "lt15"},
        {"relation": "near_crosshair", "yaw": "15_45"},
        {"relation": "near_crosshair", "yaw": "45_90"},
        {"relation": "brief_center_pass", "yaw": "15_45"},
        {"relation": "brief_center_pass", "yaw": "15_45"},
        {"relation": "center_linger", "yaw": "lt15"},
    ]


def select_enemy_slots(
    slots: list[dict[str, Any]], rng: np.random.Generator
) -> list[tuple[int, dict[str, str]]]:
    net_targets = expand_counts(
        {
            "lt64": 3,
            "64_256": 4,
            "256_512": 5,
            "512_1024": 3,
            "gt1024": 0,
        }
    )
    requirements = enemy_relation_requirements()
    for _ in range(20_000):
        rng.shuffle(net_targets)
        order = list(range(len(requirements)))
        rng.shuffle(order)
        chosen: dict[int, int] = {}
        used: set[int] = set()
        passed = True
        for requirement_index in order:
            requirement = requirements[requirement_index]
            target_net = net_targets[requirement_index]
            candidates = [
                index
                for index, slot in enumerate(slots)
                if index not in used
                and slot["primary_bucket"] != "weapon_environment"
                and slot["target_yaw_bin"] == requirement["yaw"]
                and slot["target_net_bin"] == target_net
            ]
            if not candidates:
                passed = False
                break
            selected = int(rng.choice(candidates))
            used.add(selected)
            chosen[requirement_index] = selected
        if passed:
            return [
                (chosen[index], requirement)
                for index, requirement in enumerate(requirements)
            ]
    raise capture.CaptureFailure(
        "stage1_enemy_slot_matching_failed",
        "could not satisfy role-conditioned net/yaw review marginals",
    )


def map_pair_pool(
    report: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    maps = {
        row["map"]: row
        for row in report["map_summary"]
        if row["stage1_admitted"]
    }
    by_distance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in maps.values():
        for pair in row["accepted_pairs"]:
            by_distance[pair["distance_bin"]].append(pair)
    return maps, by_distance


def stage1_render_map_allowed(map_name: str) -> bool:
    """Production admission, separate from the frozen legacy review plan."""
    return map_name not in STAGE1_RENDER_EXCLUDED_MAPS


def choose_enemy_maps(
    slots: list[dict[str, Any]],
    enemy_assignments: list[tuple[int, dict[str, str]]],
    maps: dict[str, dict[str, Any]],
    by_distance: dict[str, list[dict[str, Any]]],
    capacities: dict[str, int],
    rng: np.random.Generator,
) -> None:
    distances = expand_counts(DISTANCE_COUNTS)
    distances.sort(key=lambda value: DISTANCE_RANK[value], reverse=True)
    assignments = sorted(
        enemy_assignments,
        key=lambda item: NET_RANK[slots[item[0]]["target_net_bin"]],
        reverse=True,
    )
    used_maps: set[str] = set()
    random_order = {
        name: rank
        for rank, name in enumerate(rng.permutation(sorted(maps)))
    }
    for (slot_index, requirement), distance in zip(assignments, distances):
        candidates = [
            pair
            for pair in by_distance[distance]
            if capacities.get(pair["map"], 0) > 0
        ]
        if not candidates:
            raise capture.CaptureFailure(
                "stage1_distance_pair_missing", distance
            )
        candidates.sort(
            key=lambda pair: (
                pair["map"] in used_maps,
                -capacities[pair["map"]],
                random_order[pair["map"]],
                pair["episode_id"],
            )
        )
        selected = candidates[0]
        map_name = selected["map"]
        same_cell = [
            variant
            for pair in by_distance[distance]
            if pair["map"] == map_name
            for variant in pair_variants(pair)
        ]
        slots[slot_index].update(
            {
                "dataset_role": "foundation_enemy_distractor",
                "target_relation": requirement["relation"],
                "target_distance_bin": distance,
                "map": map_name,
                "pair_candidates": same_cell,
            }
        )
        capacities[map_name] -= 1
        used_maps.add(map_name)


def map_max_pair_rank(map_row: dict[str, Any]) -> int:
    return max(
        DISTANCE_RANK[pair["distance_bin"]]
        for pair in map_row["accepted_pairs"]
    )


def choose_no_enemy_maps(
    slots: list[dict[str, Any]],
    maps: dict[str, dict[str, Any]],
    capacities: dict[str, int],
    rng: np.random.Generator,
) -> None:
    candidates = [
        (index, slot)
        for index, slot in enumerate(slots)
        if "dataset_role" not in slot
    ]
    candidates.sort(
        key=lambda item: NET_RANK[item[1]["target_net_bin"]],
        reverse=True,
    )
    random_order = {
        name: rank
        for rank, name in enumerate(rng.permutation(sorted(maps)))
    }
    for index, slot in candidates:
        required = NET_REQUIRED_PAIR_RANK[slot["target_net_bin"]]
        available = [
            name
            for name, capacity in capacities.items()
            if capacity > 0 and map_max_pair_rank(maps[name]) >= required
        ]
        if not available:
            available = [
                name for name, capacity in capacities.items() if capacity > 0
            ]
        available.sort(
            key=lambda name: (
                abs(map_max_pair_rank(maps[name]) - required),
                -capacities[name],
                random_order[name],
            )
        )
        map_name = available[0]
        map_row = maps[map_name]
        pairs = sorted(
            map_row["accepted_pairs"],
            key=lambda pair: (
                abs(DISTANCE_RANK[pair["distance_bin"]] - required),
                pair["episode_id"],
            ),
        )
        geometries = [
            {
                "player_origin": variant["player_origin"],
                "world_yaw": direction_yaw(
                    variant["player_origin"], variant["enemy_origin"]
                ),
                "source_pair": variant["episode_id"],
                "variant": variant["variant"],
            }
            for pair in pairs
            for variant in pair_variants(pair)
        ]
        slot.update(
            {
                "dataset_role": "foundation_no_enemy",
                "map": map_name,
                "geometry_candidates": geometries,
            }
        )
        capacities[map_name] -= 1
    if any(capacities.values()):
        raise AssertionError(capacities)


def apply_map_safety_adjustments(
    slots: list[dict[str, Any]],
    maps: dict[str, dict[str, Any]],
    by_distance: dict[str, list[dict[str, Any]]],
) -> None:
    """Keep exposed space maps in coverage without inventing safe routes.

    Static LOS separation is not evidence that a long straight usercmd is
    walkable or that both endpoints avoid hazards.  Exchange dangerous
    assignments while preserving every declared marginal and each map's
    episode count.
    """
    risky = next(
        slot
        for slot in slots
        if slot.get("map") == "space-elevator"
        and slot.get("dataset_role") == "foundation_enemy_distractor"
        and slot.get("target_distance_bin") == "very_far"
    )
    donor = next(
        (
            slot
            for slot in slots
            if slot.get("map") == "techassault"
            and slot.get("dataset_role") == "foundation_no_enemy"
            and slot["target_net_bin"] == "lt64"
        ),
        None,
    )
    if donor is None:
        donor = next(
            slot
            for slot in slots
            if slot.get("map") == "techassault"
            and slot.get("dataset_role")
            == "foundation_enemy_distractor"
            and NET_RANK[slot["target_net_bin"]]
            <= NET_RANK["64_256"]
        )

    risky["map"] = "techassault"
    risky["pair_candidates"] = [
        variant
        for pair in by_distance["very_far"]
        if pair["map"] == "techassault"
        for variant in pair_variants(pair)
    ]

    close_pairs = sorted(
        maps["space-elevator"]["accepted_pairs"],
        key=lambda pair: (
            abs(DISTANCE_RANK[pair["distance_bin"]] - 1),
            pair["episode_id"],
        ),
    )
    donor["map"] = "space-elevator"
    if donor["dataset_role"] == "foundation_enemy_distractor":
        donor["pair_candidates"] = [
            variant
            for pair in close_pairs
            if pair["distance_bin"] == donor["target_distance_bin"]
            for variant in pair_variants(pair)
        ]
    else:
        donor["geometry_candidates"] = [
            {
                "player_origin": variant["player_origin"],
                "world_yaw": direction_yaw(
                    variant["player_origin"], variant["enemy_origin"]
                ),
                "source_pair": variant["episode_id"],
                "variant": variant["variant"],
            }
            for pair in close_pairs
            for variant in pair_variants(pair)
        ]

    hazardous_enemy = next(
        slot
        for slot in slots
        if slot.get("map") == "afterslime"
        and slot.get("dataset_role") == "foundation_enemy_distractor"
        and slot.get("target_distance_bin") == "near"
    )
    safe_donor = next(
        slot
        for slot in slots
        if slot.get("map") == "boil"
        and slot.get("dataset_role") == "foundation_no_enemy"
        and slot["target_net_bin"] == "256_512"
    )

    hazardous_enemy["map"] = "boil"
    hazardous_enemy["pair_candidates"] = [
        variant
        for pair in by_distance["near"]
        if pair["map"] == "boil"
        for variant in pair_variants(pair)
    ]

    afterslime_pairs = sorted(
        maps["afterslime"]["accepted_pairs"],
        key=lambda pair: (
            abs(DISTANCE_RANK[pair["distance_bin"]] - 2),
            pair["episode_id"],
        ),
    )
    safe_donor["map"] = "afterslime"
    safe_donor["geometry_candidates"] = [
        {
            "player_origin": variant["player_origin"],
            "world_yaw": direction_yaw(
                variant["player_origin"], variant["enemy_origin"]
            ),
            "source_pair": variant["episode_id"],
            "variant": variant["variant"],
        }
        for pair in afterslime_pairs
        for variant in pair_variants(pair)
    ]


def assign_weapons(slots: list[dict[str, Any]], rng: np.random.Generator) -> None:
    target = {
        weapon: 7 if index < 6 else 6
        for index, weapon in enumerate(v2.WEAPONS)
    }
    environment = [
        index
        for index, slot in enumerate(slots)
        if slot["primary_bucket"] == "weapon_environment"
    ]
    environment.sort()
    fixed = [
        ("MachineGun", "machinegun_reload"),
        ("Devastator", "environmental_secondary"),
        ("Blaster", "environmental_primary"),
        ("Shotgun", "environmental_primary"),
        ("Mortar", "environmental_primary"),
        ("Electro", "environmental_primary"),
    ]
    for index, (weapon, fire_mode) in zip(environment, fixed):
        slots[index]["weapon"] = weapon
        slots[index]["fire_mode"] = fire_mode
        target[weapon] -= 1
    pool = expand_counts(target)
    rng.shuffle(pool)
    remaining = [
        index for index, slot in enumerate(slots) if "weapon" not in slot
    ]
    for index, weapon in zip(remaining, pool):
        slots[index]["weapon"] = weapon
        slots[index]["fire_mode"] = "none"


def relation_offset(relation: str) -> float:
    return {
        "offscreen_or_occluded": -150.0,
        "visible_far": -35.0,
        "near_crosshair": -9.5,
        "brief_center_pass": 0.0,
        "center_linger": -4.0,
    }[relation]


def apply_enemy_policy_geometry(row: dict[str, Any]) -> None:
    """Bind a named policy to fixed reset geometry, never live camera/aim."""
    policy = row["enemy_policy"]
    name = policy["name"]
    player_origin = row["player"]["origin"]
    enemy_origin = row["enemy"]["origin"]
    toward_yaw, _ = v2.yaw_pitch_toward(
        enemy_origin, player_origin
    )
    side = 1.0 if int(policy["policy_seed"]) % 2 else -1.0
    if name in {"lateral_patrol", "stop_and_go"}:
        heading_yaw = toward_yaw + side * 90.0
    else:
        heading_yaw = toward_yaw
    heading = math.radians(heading_yaw)
    vector = [
        round(math.cos(heading), 6),
        round(math.sin(heading), 6),
        0.0,
    ]
    distance = float(
        np.linalg.norm(
            np.asarray(player_origin, dtype=np.float64)
            - np.asarray(enemy_origin, dtype=np.float64)
        )
    )
    amplitude = ENEMY_POLICY_BASE_AMPLITUDE[name]
    if name == "approach_retreat":
                                                                           
                                                    
        amplitude = min(amplitude, max(0.0, distance - 96.0))
    if name == "idle":
        vector = [0.0, 0.0, 0.0]
    policy.update(
        {
            "motion_mode": ENEMY_POLICY_MOTION_MODE[name],
            "motion_vector": vector,
            "motion_amplitude_units": round(amplitude, 6),
            "initial_player_distance": round(distance, 6),
            "heading_yaw": round(heading_yaw, 6),
        }
    )
    row["enemy"]["motion"] = policy["motion_mode"]
    row["enemy"]["motion_vector"] = vector
    row["enemy"]["motion_distance"] = policy[
        "motion_amplitude_units"
    ]
    row["enemy"]["motion_start_tick"] = policy[
        "motion_start_tick"
    ]


def enemy_policy_contract(
    enemy_index: int,
    episode_seed: int,
) -> dict[str, Any]:
    name = ENEMY_POLICY_SEQUENCE[enemy_index]
    policy_seed = episode_seed * 17 + enemy_index * 101
    return {
        "schema_version": "xonotic-stage1-enemy-policy-v1",
        "name": name,
        "policy_seed": policy_seed,
        "motion_start_tick": (
            0 if name == "idle" else policy_seed % capture.WARMUP_TICKS
        ),
        "runtime_reads_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
        "fires": False,
        "jumps": False,
        "trajectory_reference": "fixed_initial_anchor_geometry",
    }


def action_category(slot: dict[str, Any], ordinal: int) -> str:
    if slot["primary_bucket"] == "weapon_environment":
        return str(slot["fire_mode"])
    controls = ("forward", "backward", "strafe_left", "strafe_right", "diagonal")
    control = controls[ordinal % len(controls)]
    if slot["primary_bucket"] == "node_atomic":
        return f"node_atomic_{control}"
    if slot["primary_bucket"] == "mixed_action":
        return f"mixed_move_view_jump_{control}"
    return f"high_motion_{control}"


def build_scenarios() -> list[dict[str, Any]]:
    report = json.loads(v2.PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    maps, by_distance = map_pair_pool(report)
    if len(maps) != 29:
        raise capture.CaptureFailure(
            "stage1_map_pool_not_29",
            f"maps={len(maps)}",
        )
    for generation in range(200):
        rng = np.random.default_rng(SEED + generation)
        slots = slot_rows(rng)
        try:
            enemy_assignments = select_enemy_slots(slots, rng)
            break
        except capture.CaptureFailure:
            continue
    else:
        raise capture.CaptureFailure("stage1_slot_generation_failed")

    map_targets = {name: 2 for name in maps}
    map_targets["bromine"] += 1
    map_targets["space-elevator"] += 1
    capacities = dict(map_targets)
    choose_enemy_maps(
        slots,
        enemy_assignments,
        maps,
        by_distance,
        capacities,
        rng,
    )
    choose_no_enemy_maps(slots, maps, capacities, rng)
    apply_map_safety_adjustments(slots, maps, by_distance)
    assign_weapons(slots, rng)

                                                                          
                                                                            
                                                                      
                                                                          
                                  
    courtfun_brief = slots[29]
    dance_visible = slots[31]
    if not (
        courtfun_brief["map"] == "courtfun"
        and courtfun_brief["target_relation"] == "brief_center_pass"
        and dance_visible["map"] == "dance"
        and dance_visible["target_relation"] == "visible_far"
    ):
        raise capture.CaptureFailure("stage1_calibration_slot_drift")
    (
        courtfun_brief["target_net_bin"],
        dance_visible["target_net_bin"],
    ) = (
        dance_visible["target_net_bin"],
        courtfun_brief["target_net_bin"],
    )

                                                                      
                                                                           
                                                                            
                                                       
    techassault_limited = slots[32]
    finalrage_open = slots[34]
    stormkeep_middle = slots[36]
    if not (
        techassault_limited["map"] == "techassault"
        and techassault_limited["target_net_bin"] == "gt1024"
        and finalrage_open["map"] == "finalrage"
        and finalrage_open["target_net_bin"] == "512_1024"
        and stormkeep_middle["map"] == "stormkeep"
        and stormkeep_middle["target_net_bin"] == "256_512"
    ):
        raise capture.CaptureFailure("stage1_node_calibration_slot_drift")
    (
        techassault_limited["target_net_bin"],
        finalrage_open["target_net_bin"],
        stormkeep_middle["target_net_bin"],
    ) = (
        stormkeep_middle["target_net_bin"],
        techassault_limited["target_net_bin"],
        finalrage_open["target_net_bin"],
    )

    appearances = [
        (row["model"], int(row["skin"]))
        for row in v2.load_catalog()["enemy_appearances"]
    ]
    appearance_pool = appearances + [appearances[0]]
    rng.shuffle(appearance_pool)
    enemy_indices = [
        index
        for index, slot in enumerate(slots)
        if slot["dataset_role"] == "foundation_enemy_distractor"
    ]
    enemy_indices.sort()
    for index, appearance in zip(enemy_indices, appearance_pool):
        slots[index]["enemy_model"], slots[index]["enemy_skin"] = appearance

    control_angles = (0.0, 180.0, 90.0, -90.0, 45.0, -45.0)
    rows: list[dict[str, Any]] = []
    enemy_policy_index = 0
    for ordinal, slot in enumerate(slots, 1):
        role = slot["dataset_role"]
        enemy_present = role == "foundation_enemy_distractor"
        if enemy_present:
            first_pair = slot["pair_candidates"][0]
            player_origin = first_pair["player_origin"]
            enemy_origin = first_pair["enemy_origin"]
            yaw_offset = relation_offset(slot["target_relation"])
            if ordinal in {41, 43, 48}:
                                                                       
                                                                        
                                                                           
                yaw_offset = 35.0
            base_yaw, _ = v2.yaw_pitch_toward(
                player_origin, enemy_origin
            )
            world_yaw = base_yaw + (90.0 if ordinal % 2 else -90.0)
        else:
            first_geometry = slot["geometry_candidates"][0]
            player_origin = first_geometry["player_origin"]
            enemy_origin = None
            yaw_offset = 0.0
            world_yaw = first_geometry["world_yaw"]

        control_angle = control_angles[(ordinal - 1) % len(control_angles)]
        calibrated_lateral_traverse = bool(
            enemy_present
            and slot.get("target_relation") == "offscreen_or_occluded"
            and slot.get("target_distance_bin") == "very_far"
        )
        low_near_offscreen = bool(
            enemy_present
            and slot.get("target_relation") == "offscreen_or_occluded"
            and slot.get("target_distance_bin") == "near"
            and slot["target_net_bin"] == "64_256"
        )
        jump_enabled = (
            slot["primary_bucket"] in {"mixed_action", "high_motion_special"}
            or (
                slot["primary_bucket"] == "node_atomic"
                and ordinal % 4 == 0
            )
        ) and not low_near_offscreen
        if ordinal == 36:
                                                                          
                                                                          
            jump_enabled = False
        category = action_category(slot, ordinal)
        if not jump_enabled:
            category = category.replace("_view_jump_", "_view_")
        move_duration_candidates = list(
            MOVE_DURATIONS[slot["target_net_bin"]]
        )
        calibration_policy: str | None = None
        if ordinal == 30:
            move_duration_candidates = [144]
            calibration_policy = "courtfun_far_brief_measured"
        elif ordinal == 32:
            move_duration_candidates = [80]
            calibration_policy = "dance_visible_far_measured"
        elif ordinal == 33:
            move_duration_candidates = [240]
            calibration_policy = "techassault_geometry_limited_measured"
        elif ordinal == 35:
            move_duration_candidates = [144]
            calibration_policy = "finalrage_jump_amplified_measured"
        move_start_tick = 0
        if calibrated_lateral_traverse:
                                                                             
                                                                          
                                                                    
            move_duration_candidates = [96, 112, 128, 144]
        move_duration = move_duration_candidates[0]
        expects_sound = bool(
            move_duration > 0
            or jump_enabled
            or slot["fire_mode"] != "none"
        )
        row = v2.scenario(
            episode_id=f"s1review_{ordinal:03d}",
            split=SPLIT,
            dataset_role=role,
            category=category,
            map_name=slot["map"],
            gametype=capture_gametype_for_map(slot["map"]),
            player_origin=player_origin,
            weapon=slot["weapon"],
            action_program="stage1_review_distribution",
            seed=9_100_000 + ordinal,
            enemy_origin=enemy_origin,
            enemy_model=slot.get("enemy_model", ""),
            enemy_skin=int(slot.get("enemy_skin", 0)),
            enemy_color=(0, 68, 204)[ordinal % 3],
            yaw_offset=yaw_offset,
            expected_relation=slot.get("target_relation"),
            expected_distance_bin=slot.get("target_distance_bin"),
            expects_sound=expects_sound,
            fire_required=slot["fire_mode"]
            in {"environmental_primary", "environmental_secondary"},
            reload_success=slot["fire_mode"] == "machinegun_reload",
        )
        row["data_spec_sha256"] = capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        )
        row["training_stage"] = "stage1_review_only"
        row["primary_bucket"] = slot["primary_bucket"]
        row["review_targets"] = {
            "net_displacement_bin": slot["target_net_bin"],
            "yaw_range_bin": slot["target_yaw_bin"],
            "pitch_range_bin": slot["target_pitch_bin"],
            "target_relation": slot.get("target_relation"),
            "distance_bin": slot.get("target_distance_bin"),
        }
        row["review_action"] = {
            "world_yaw": world_yaw,
            "control_angle": control_angle,
            "move_duration_candidates": move_duration_candidates,
            "move_start_tick": move_start_tick,
            "trajectory_policy": (
                calibration_policy
                or (
                    "calibrated_lateral"
                    if calibrated_lateral_traverse
                    else "stratified_straight"
                )
            ),
            "yaw_amplitude": YAW_AMPLITUDE[slot["target_yaw_bin"]],
            "pitch_amplitude": PITCH_AMPLITUDE[
                slot["target_pitch_bin"]
            ],
            "jump": jump_enabled,
            "fire_mode": slot["fire_mode"],
            "relation": slot.get("target_relation"),
        }
        if enemy_present:
            row["initial_yaw_offset"] = yaw_offset
            row["pair_candidates"] = slot["pair_candidates"]
            row["enemy_policy"] = enemy_policy_contract(
                enemy_policy_index, int(row["seed"])
            )
            apply_enemy_policy_geometry(row)
            enemy_policy_index += 1
        else:
            row["geometry_candidates"] = slot["geometry_candidates"]
            row["move_control_angle"] = control_angle
        rows.append(row)

    rows.sort(key=lambda row: row["episode_id"])
    validate_scenario_matrix(rows, map_targets)
    return rows


def validate_scenario_matrix(
    rows: list[dict[str, Any]], map_targets: dict[str, int]
) -> None:
    checks = {
        "count": len(rows) == EXPECTED_COUNT,
        "roles": Counter(row["dataset_role"] for row in rows)
        == Counter(ROLE_COUNTS),
        "buckets": Counter(row["primary_bucket"] for row in rows)
        == Counter(BUCKET_COUNTS),
        "net": Counter(
            row["review_targets"]["net_displacement_bin"] for row in rows
        )
        == Counter(NET_COUNTS),
        "yaw": Counter(
            row["review_targets"]["yaw_range_bin"] for row in rows
        )
        == Counter(YAW_COUNTS),
        "pitch": Counter(
            row["review_targets"]["pitch_range_bin"] for row in rows
        )
        == Counter(PITCH_COUNTS),
        "distance": Counter(
            row["review_targets"]["distance_bin"]
            for row in rows
            if row["enemy_present"]
        )
        == Counter(DISTANCE_COUNTS),
        "relation": Counter(
            row["review_targets"]["target_relation"]
            for row in rows
            if row["enemy_present"]
        )
        == Counter(RELATION_COUNTS),
        "maps": Counter(row["map"] for row in rows)
        == Counter(map_targets),
        "weapons": (
            min(Counter(row["weapon"] for row in rows).values()) == 6
            and max(Counter(row["weapon"] for row in rows).values()) == 7
            and len({row["weapon"] for row in rows}) == 9
        ),
        "stage1_only": {
            row["dataset_role"] for row in rows
        }
        <= set(ROLE_COUNTS),
        "enemy_never_fires": all(
            row["review_action"]["fire_mode"] == "none"
            for row in rows
            if row["enemy_present"]
        ),
        "enemy_policy_counts": Counter(
            row["enemy_policy"]["name"]
            for row in rows
            if row["enemy_present"]
        )
        == Counter(ENEMY_POLICY_COUNTS),
        "enemy_policy_no_live_coupling": all(
            not row["enemy_policy"]["runtime_reads_player_state"]
            and not row["enemy_policy"]["reads_camera"]
            and not row["enemy_policy"]["reads_crosshair"]
            and not row["enemy_policy"]["fires"]
            for row in rows
            if row["enemy_present"]
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage1_scenario_matrix_invalid",
            capture.canonical_json(checks),
        )


BASE_ACTION_ROWS = capture.CANONICAL_ACTION_ROWS


def review_action_rows(
    scenario: dict[str, Any], retry: int = 0
) -> list[dict[str, Any]]:
    if scenario.get("action_program") != "stage1_review_distribution":
        return BASE_ACTION_ROWS(scenario, retry=retry)
    design = scenario.get("action_design")
    if design:
        direction = str(
            design.get("locomotion_direction", "idle")
        )
        if direction not in capture.STAGE1_LOCOMOTION_VECTORS:
            raise capture.CaptureFailure(
                "stage1_locomotion_direction_unknown", direction
            )
        movement_profile = str(
            design.get(
                "movement_profile", "full_clip_sustained"
            )
        )
        speed = float(design.get("movement_speed", 0.0))
        direction_forward, direction_strafe = (
            capture.STAGE1_LOCOMOTION_VECTORS[direction]
        )
        yaw_offsets, pitch_offsets = capture.stage1_camera_offsets(
            design
        )
        yaw_delta = np.diff(
            np.concatenate(([0.0], yaw_offsets))
        )
        pitch_delta = np.diff(
            np.concatenate(([0.0], pitch_offsets))
        )
        rows: list[dict[str, Any]] = []
        for tick in range(capture.TOTAL_TICKS):
            out_tick = tick - capture.WARMUP_TICKS
            forward = strafe = 0.0
            view_yaw = view_pitch = 0.0
            jump = primary = secondary = reload_button = 0
            if out_tick >= 0:
                scalar = capture.stage1_temporal_scalar(
                    movement_profile, out_tick
                )
                forward = speed * direction_forward * scalar
                strafe = speed * direction_strafe * scalar
                view_yaw = float(yaw_delta[out_tick])
                view_pitch = float(pitch_delta[out_tick])
                if design.get("jump"):
                    jump = v2.pulse(out_tick, (48, 208), 2)
                primary, secondary, reload_button = (
                    capture.stage1_weapon_controls(
                        design,
                        str(scenario["weapon"]),
                        out_tick,
                    )
                )
            rows.append(
                {
                    "tick": tick,
                    "forward": round(forward, 6),
                    "strafe": round(strafe, 6),
                    "yaw_delta": round(view_yaw, 6),
                    "pitch_delta": round(view_pitch, 6),
                    "jump": jump,
                    "primary": primary,
                    "secondary": secondary,
                    "weapon_impulse": 0,
                    "reload": reload_button,
                }
            )
        return rows
    profile = scenario["review_action"]
                                                                           
                                                                            
                                                            
    retry = int(scenario.get("fixed_variant_index", retry))
    relation = profile.get("relation")
    duration_options = profile["move_duration_candidates"]
    move_duration = int(duration_options[retry % len(duration_options)])
    move_start = int(profile.get("move_start_tick", 0))
    yaw_amplitude = float(profile["yaw_amplitude"])
    pitch_amplitude = float(profile["pitch_amplitude"])
    if relation == "brief_center_pass":
                                                                         
                                                                        
                                                              
        yaw_start, yaw_length = 8, 32
    elif relation == "near_crosshair":
                                                                            
                                                                  
        yaw_start, yaw_length = 0, 64
    elif relation == "center_linger":
        yaw_start, yaw_length = 0, capture.OUTPUT_TICKS
    else:
        yaw_start, yaw_length = 64, 240
    yaw_per_tick = yaw_amplitude / yaw_length if yaw_length else 0.0
    output_yaw_delta = np.zeros(capture.OUTPUT_TICKS, dtype=np.float64)
    output_yaw_delta[yaw_start : yaw_start + yaw_length] = yaw_per_tick
    yaw_before = np.concatenate(
        ([0.0], np.cumsum(output_yaw_delta[:-1]))
    )
    rows: list[dict[str, Any]] = []
    for tick in range(capture.TOTAL_TICKS):
        out_tick = tick - capture.WARMUP_TICKS
        forward = strafe = yaw_delta = pitch_delta = 0.0
        jump = primary = secondary = reload_button = 0
        if out_tick >= 0:
            yaw_delta = float(output_yaw_delta[out_tick])
            if (
                move_duration > 0
                and move_start <= out_tick < move_start + move_duration
            ):
                current_camera_yaw = (
                    float(scenario["player"]["yaw"])
                    + float(yaw_before[out_tick])
                )
                world_delta = math.radians(
                    float(profile["world_yaw"]) - current_camera_yaw
                )
                forward = 400.0 * math.cos(world_delta)
                strafe = -400.0 * math.sin(world_delta)
            if pitch_amplitude:
                if out_tick < 80:
                    pitch_delta = (pitch_amplitude / 2.0) / 80.0
                elif out_tick < 240:
                    pitch_delta = -pitch_amplitude / 160.0
                else:
                    pitch_delta = (pitch_amplitude / 2.0) / 80.0
            if profile["jump"]:
                jump = v2.pulse(out_tick, (24, 152, 264), 2)
            fire_mode = profile["fire_mode"]
            if fire_mode == "machinegun_reload":
                primary = v2.pulse(out_tick, (24,), 16)
                reload_button = v2.pulse(out_tick, (72,), 1)
            elif fire_mode == "environmental_primary":
                primary, secondary = v2.fire_controls(
                    scenario["weapon"], out_tick, (64, 176, 272)
                )
            elif fire_mode == "environmental_secondary":
                primary = v2.pulse(out_tick, (48, 160, 272), 2)
                secondary = v2.pulse(out_tick, (80, 192, 304), 2)
        rows.append(
            {
                "tick": tick,
                "forward": round(forward, 6),
                "strafe": round(strafe, 6),
                "yaw_delta": round(yaw_delta, 6),
                "pitch_delta": round(pitch_delta, 6),
                "jump": jump,
                "primary": primary,
                "secondary": secondary,
                "weapon_impulse": 0,
                "reload": reload_button,
            }
        )
    return rows


capture.register_action_row_provider(
    "xonotic_stage1_review",
    ("stage1_review_distribution",),
    review_action_rows,
)


def apply_variant(base: dict[str, Any], retry: int) -> dict[str, Any]:
    row = copy.deepcopy(base)
    requested_gametype = str(row.get("gametype", "")).lower()
    resolved_gametype = capture_gametype_for_map(row["map"])
    row["gametype"] = resolved_gametype
    row["gametype_policy"] = "official_catalog_preflight_gametype"
    if requested_gametype != resolved_gametype:
        row["gametype_resolution"] = {
            "input_gametype": requested_gametype,
            "resolved_gametype": resolved_gametype,
            "reason": "map_native_mode_contract",
        }
    if row["enemy_present"]:
        candidates = row["pair_candidates"]
        measured_pair_policy = row["review_action"].get(
            "trajectory_policy"
        ) in {
            "courtfun_far_brief_measured",
            "dance_visible_far_measured",
        }
        calibrated_lateral = bool(
            row["review_action"].get("trajectory_policy")
            == "calibrated_lateral"
        )
        if calibrated_lateral or measured_pair_policy:
            pair = next(
                candidate
                for candidate in candidates
                if candidate["variant"] == "reverse"
            ) if calibrated_lateral else next(
                candidate
                for candidate in candidates
                if candidate["variant"] == "forward"
            )
        else:
            pair = candidates[retry % len(candidates)]
        pair_gametype = str(pair.get("gametype", "")).lower()
        if pair_gametype and pair_gametype != resolved_gametype:
            raise capture.CaptureFailure(
                "stage1_pair_gametype_drift",
                f"map={row['map']} pair={pair_gametype} "
                f"catalog={resolved_gametype}",
            )
        row["player"]["origin"] = pair["player_origin"]
        row["enemy"]["origin"] = pair["enemy_origin"]
        base_yaw, base_pitch = v2.yaw_pitch_toward(
            pair["player_origin"], pair["enemy_origin"]
        )
        row["player"]["yaw"] = round(
            base_yaw + float(row["initial_yaw_offset"]), 6
        )
        row["player"]["pitch"] = round(base_pitch, 6)
        enemy_yaw, _ = v2.yaw_pitch_toward(
            pair["enemy_origin"], pair["player_origin"]
        )
        row["enemy"]["yaw"] = round(enemy_yaw, 6)
        movement_side = (
            -90.0
            if measured_pair_policy
            else 90.0 if (retry // len(candidates)) % 2 else -90.0
        )
        relation = row["review_action"].get("relation")
        if relation == "center_linger":
                                                                              
                                                                    
            world_yaw = base_yaw
        elif relation == "brief_center_pass":
                                                                            
                                                                     
            brief_angle = 67.5
            world_yaw = base_yaw + math.copysign(brief_angle, movement_side)
        elif (
            relation == "near_crosshair"
            or row["review_targets"]["distance_bin"] == "near"
        ):
                                                                             
                                                                               
            world_yaw = base_yaw + math.copysign(55.0, movement_side)
        elif (
            relation == "offscreen_or_occluded"
            and row["review_targets"]["distance_bin"] == "very_far"
        ):
                                                                        
                                                                               
            world_yaw = base_yaw - 90.0
        else:
            world_yaw = base_yaw + movement_side
        row["review_action"]["world_yaw"] = world_yaw
        if "enemy_policy" in row:
            apply_enemy_policy_geometry(row)
        else:
                                                                   
            vector_yaw = math.radians(world_yaw)
            row["enemy"]["motion_vector"] = [
                round(math.cos(vector_yaw), 6),
                round(math.sin(vector_yaw), 6),
                0.0,
            ]
        row["anchor_id"] = f"{row['map']}_{row['episode_id']}_pair"
        row["selected_geometry"] = {
            "source_pair": pair["episode_id"],
            "variant": pair["variant"],
        }
    else:
        candidates = row["geometry_candidates"]
        measured_geometry_policy = row["review_action"].get(
            "trajectory_policy"
        ) in {
            "techassault_geometry_limited_measured",
            "finalrage_jump_amplified_measured",
        }
        geometry = (
            candidates[0]
            if measured_geometry_policy
            else candidates[retry % len(candidates)]
        )
        row["player"]["origin"] = geometry["player_origin"]
        world_yaw = float(geometry["world_yaw"])
        control_angle = float(row["move_control_angle"])
        row["player"]["yaw"] = round(world_yaw - control_angle, 6)
        row["player"]["pitch"] = 0.0
        row["review_action"]["world_yaw"] = world_yaw
        row["anchor_id"] = f"{row['map']}_{row['episode_id']}_solo"
        row["selected_geometry"] = geometry
    return row


def motion_gates(
    row: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, bool]:
    targets = row["review_targets"]
    return {
        "net_bin": metrics["net_displacement_bin"]
        == targets["net_displacement_bin"],
        "yaw_bin": metrics["yaw_range_bin"] == targets["yaw_range_bin"],
        "pitch_bin": metrics["pitch_range_bin"]
        == targets["pitch_range_bin"],
    }


def publish_attempt(
    row: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    stage = Path(result["stage"])
    package = stage / "package"
    attempt_id = result["attempt_id"]
    episode_destination = REVIEW_ROOT / "episodes" / row["episode_id"]
    raw_destination = REVIEW_ROOT / "raw" / attempt_id
    package_hashes = v2.copytree_verified(package, episode_destination)
    raw_hashes = v2.copytree_verified(stage, raw_destination)
    qa = json.loads(
        (episode_destination / "qa.json").read_text(encoding="utf-8")
    )
    manifest = {
        "schema_version": "xonotic-v2-stage1-review-manifest-v1",
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "split": row["split"],
        "dataset_role": row["dataset_role"],
        "primary_bucket": row["primary_bucket"],
        "category": row["category"],
        "map": row["map"],
        "gametype": row["gametype"],
        "weapon": row["weapon"],
        "enemy_present": row["enemy_present"],
        "enemy_model": row["enemy_model"],
        "enemy_skin": row["enemy_skin"],
        "expected_distance_bin": row["review_targets"]["distance_bin"],
        "actual_distance_bin": qa["target_relation"].get(
            "actual_distance_bin"
        ),
        "expected_target_relation": row["review_targets"][
            "target_relation"
        ],
        "actual_target_relation": qa["target_relation"][
            "actual_target_relation"
        ],
        "review_targets": row["review_targets"],
        "motion": qa["motion"],
        "camera": qa["camera"],
        "episode_path": str(episode_destination),
        "raw_path": str(raw_destination),
        "package_sha256": package_hashes,
        "raw_sha256": raw_hashes,
        "qa": {
            "renderer": qa["runtime"]["renderer"],
            "frames": qa["video"]["frames"],
            "audio_samples": qa["audio"]["samples_per_channel"],
            "mapping": qa["mapping"]["success_rate"],
            "audio_onset_max_ms": qa["audio"]["max_onset_error_ms"],
            "event_linkage": qa["events"]["linkage_rate"],
            "damage_count": qa["events"]["damage_count"],
            "fire_count": qa["events"]["fire_count"],
        },
        "accepted_utc": capture.utc_now(),
    }
    with WRITE_LOCK:
        capture.append_jsonl(ACCEPTED_PATH, manifest)
    capture.clean_stage(stage)
    return manifest


def reject_attempt(
    row: dict[str, Any],
    retry: int,
    failure: Exception,
    stage: Path,
) -> dict[str, Any]:
    attempt_id = f"{row['episode_id']}_a{retry + 1:02d}"
    destination = REVIEW_ROOT / "rejected" / attempt_id
    hashes: dict[str, str] = {}
    if stage.exists() and not destination.exists():
        hashes = v2.copytree_verified(stage, destination)
        capture.clean_stage(stage)
    rejection = {
        "schema_version": "xonotic-v2-stage1-review-reject-v1",
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "dataset_role": row["dataset_role"],
        "primary_bucket": row["primary_bucket"],
        "map": row["map"],
        "review_targets": row["review_targets"],
        "reason": (
            failure.reason
            if isinstance(failure, capture.CaptureFailure)
            else type(failure).__name__
        ),
        "detail": (
            failure.detail
            if isinstance(failure, capture.CaptureFailure)
            else str(failure)
        ),
        "preserved_path": str(destination) if destination.exists() else None,
        "preserved_sha256": hashes,
        "rejected_utc": capture.utc_now(),
    }
    with WRITE_LOCK:
        capture.append_jsonl(REJECTS_PATH, rejection)
    return rejection


def capture_one(
    base: dict[str, Any], max_retries: int
) -> dict[str, Any]:
    accepted = {
        row["episode_id"]: row
        for row in capture.load_jsonl(ACCEPTED_PATH)
    }
    if base["episode_id"] in accepted:
        return accepted[base["episode_id"]]
    prior = [
        row
        for row in capture.load_jsonl(REJECTS_PATH)
        if row["episode_id"] == base["episode_id"]
    ]
    retry_base = max(
        (
            int(row["attempt_id"].rsplit("_a", 1)[1])
            for row in prior
        ),
        default=0,
    )
    for retry in range(retry_base, retry_base + max_retries):
        row = apply_variant(base, retry)
        stage = (
            capture.TMP_ROOT
            / "raw"
            / f"{row['episode_id']}_a{retry + 1:02d}"
        )
        print(
            f"capture id={row['episode_id']} attempt={retry + 1} "
            f"map={row['map']} role={row['dataset_role']} "
            f"target={row['review_targets']}",
            flush=True,
        )
        try:
            result = capture.execute_attempt(row, retry, publish=False)
            package = Path(result["stage"]) / "package"
            relation = v2.relation_metrics(
                package, bool(row["enemy_present"])
            )
            qa_path = package / "qa.json"
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            qa["target_relation"] = relation
            metrics = motion.motion_metrics(package)
            gates = motion_gates(row, metrics)
            qa["motion"] = metrics
            qa["review_motion_gates"] = gates
            qa["gates"].update(
                {f"review_{name}": passed for name, passed in gates.items()}
            )
            atomic_json(qa_path, qa)
            episode_path = package / "episode.json"
            episode = json.loads(
                episode_path.read_text(encoding="utf-8")
            )
            episode["actual_target_relation"] = relation
            episode["actual_motion"] = metrics
            atomic_json(episode_path, episode)
            v2.validate_post_bucket(row, qa)
            if row["enemy_present"] and qa["events"]["fire_count"]:
                raise capture.CaptureFailure(
                    "stage1_distractor_fire_forbidden",
                    f"fire_count={qa['events']['fire_count']}",
                )
            if not all(gates.values()):
                raise capture.CaptureFailure(
                    "review_motion_bucket_mismatch",
                    capture.canonical_json(
                        {
                            "gates": gates,
                            "target": row["review_targets"],
                            "actual": metrics,
                        }
                    ),
                )
            manifest = publish_attempt(row, result)
            print(
                f"accepted id={row['episode_id']} "
                f"net={metrics['net_displacement_3d']:.1f}/"
                f"{metrics['net_displacement_bin']} "
                f"yaw={metrics['yaw_range_deg']:.1f}/"
                f"{metrics['yaw_range_bin']} "
                f"pitch={metrics['pitch_range_deg']:.1f}/"
                f"{metrics['pitch_range_bin']} "
                f"distance={manifest['actual_distance_bin']}",
                flush=True,
            )
            return manifest
        except Exception as exc:
            rejection = reject_attempt(row, retry, exc, stage)
            print(
                f"reject id={row['episode_id']} "
                f"reason={rejection['reason']} "
                f"detail={rejection['detail'][:500]}",
                flush=True,
            )
    raise capture.CaptureFailure(
        "stage1_review_retry_exhausted", base["episode_id"]
    )


def distribution_checks(rows: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "exact_60_unique": len(rows)
        == len({row["episode_id"] for row in rows})
        == EXPECTED_COUNT,
        "roles": Counter(row["dataset_role"] for row in rows)
        == Counter(ROLE_COUNTS),
        "buckets": Counter(row["primary_bucket"] for row in rows)
        == Counter(BUCKET_COUNTS),
        "actual_net": Counter(
            row["motion"]["net_displacement_bin"] for row in rows
        )
        == Counter(NET_COUNTS),
        "actual_yaw": Counter(
            row["motion"]["yaw_range_bin"] for row in rows
        )
        == Counter(YAW_COUNTS),
        "actual_pitch": Counter(
            row["motion"]["pitch_range_bin"] for row in rows
        )
        == Counter(PITCH_COUNTS),
        "actual_distance": Counter(
            row["actual_distance_bin"]
            for row in rows
            if row["enemy_present"]
        )
        == Counter(DISTANCE_COUNTS),
        "actual_relation": Counter(
            row["actual_target_relation"]
            for row in rows
            if row["enemy_present"]
        )
        == Counter(RELATION_COUNTS),
        "all_29_maps": len({row["map"] for row in rows}) == 29,
        "map_frequency_2_or_3": set(
            Counter(row["map"] for row in rows).values()
        )
        == {2, 3},
        "all_9_weapons": len({row["weapon"] for row in rows}) == 9,
        "weapon_frequency_6_or_7": set(
            Counter(row["weapon"] for row in rows).values()
        )
        == {6, 7},
        "stage1_only": {
            row["dataset_role"] for row in rows
        }
        <= set(ROLE_COUNTS),
        "no_enemy_damage": all(
            row["qa"]["damage_count"] == 0 for row in rows
        ),
        "fov90": all(
            row["camera"]["fixed_all_frames"]
            and abs(row["camera"]["observed_frustum_x"] - 4.0 / 3.0)
            <= capture.CAMERA_FRUSTUM_TOLERANCE
            and abs(row["camera"]["observed_frustum_y"] - 3.0 / 4.0)
            <= capture.CAMERA_FRUSTUM_TOLERANCE
            for row in rows
        ),
    }


def command_generate(_: argparse.Namespace) -> int:
    capture.require_conda()
    rows = build_scenarios()
    write_jsonl(SCENARIOS_PATH, rows)
    summary = {
        "schema_version": "xonotic-v2-stage1-review-plan-v1",
        "created_utc": capture.utc_now(),
        "seed": SEED,
        "split": SPLIT,
        "count": len(rows),
        "roles": dict(Counter(row["dataset_role"] for row in rows)),
        "buckets": dict(Counter(row["primary_bucket"] for row in rows)),
        "target_net": dict(
            Counter(
                row["review_targets"]["net_displacement_bin"]
                for row in rows
            )
        ),
        "target_yaw": dict(
            Counter(
                row["review_targets"]["yaw_range_bin"] for row in rows
            )
        ),
        "target_pitch": dict(
            Counter(
                row["review_targets"]["pitch_range_bin"]
                for row in rows
            )
        ),
        "maps": dict(Counter(row["map"] for row in rows)),
        "weapons": dict(Counter(row["weapon"] for row in rows)),
        "distance": dict(
            Counter(
                row["review_targets"]["distance_bin"]
                for row in rows
                if row["enemy_present"]
            )
        ),
        "relation": dict(
            Counter(
                row["review_targets"]["target_relation"]
                for row in rows
                if row["enemy_present"]
            )
        ),
    }
    atomic_json(REVIEW_ROOT / "SAMPLING_PLAN.json", summary)
    print(f"scenarios={SCENARIOS_PATH}")
    print(capture.canonical_json(summary))
    return 0


def command_pilot(args: argparse.Namespace) -> int:
    capture.require_conda()
    if not SCENARIOS_PATH.is_file():
        command_generate(args)
    scenarios = capture.load_jsonl(SCENARIOS_PATH)
    accepted_ids = {
        row["episode_id"] for row in capture.load_jsonl(ACCEPTED_PATH)
    }
    pending = [
        row for row in scenarios if row["episode_id"] not in accepted_ids
    ]
    if args.limit:
        pending = pending[: args.limit]
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(capture_one, row, args.max_retries): row
            for row in pending
        }
        for index, future in enumerate(
            concurrent.futures.as_completed(futures), 1
        ):
            row = futures[future]
            future.result()
            print(
                f"progress {index}/{len(pending)} {row['episode_id']}",
                flush=True,
            )
    rows = capture.load_jsonl(ACCEPTED_PATH)
    if len(rows) < EXPECTED_COUNT:
        print(f"partial accepted={len(rows)}/{EXPECTED_COUNT}")
        return 0
    checks = distribution_checks(rows)
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage1_review_final_distribution_gate",
            capture.canonical_json(checks),
        )
    summary = {
        "schema_version": "xonotic-v2-stage1-review-summary-v1",
        "created_utc": capture.utc_now(),
        "accepted": len(rows),
        "rejected_attempts": len(capture.load_jsonl(REJECTS_PATH)),
        "checks": checks,
        "roles": dict(Counter(row["dataset_role"] for row in rows)),
        "buckets": dict(Counter(row["primary_bucket"] for row in rows)),
        "maps": dict(Counter(row["map"] for row in rows)),
        "weapons": dict(Counter(row["weapon"] for row in rows)),
        "actual_net": dict(
            Counter(row["motion"]["net_displacement_bin"] for row in rows)
        ),
        "actual_yaw": dict(
            Counter(row["motion"]["yaw_range_bin"] for row in rows)
        ),
        "actual_pitch": dict(
            Counter(row["motion"]["pitch_range_bin"] for row in rows)
        ),
        "actual_distance": dict(
            Counter(
                row["actual_distance_bin"]
                for row in rows
                if row["enemy_present"]
            )
        ),
        "actual_relation": dict(
            Counter(
                row["actual_target_relation"]
                for row in rows
                if row["enemy_present"]
            )
        ),
    }
    atomic_json(SUMMARY_PATH, summary)
    print(f"complete accepted={len(rows)}")
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    capture.require_conda()
    if not SCENARIOS_PATH.is_file():
        command_generate(args)
    scenarios = capture.load_jsonl(SCENARIOS_PATH)
    candidate = next(
        row
        for row in scenarios
        if row["dataset_role"] == "foundation_no_enemy"
        and row["primary_bucket"] == "node_atomic"
        and row["review_targets"]["net_displacement_bin"] == "lt64"
        and row["review_targets"]["yaw_range_bin"] == "lt15"
        and row["review_targets"]["pitch_range_bin"] == "lt5"
    )
    manifest = capture_one(candidate, args.max_retries)
    evidence = {
        "schema_version": "xonotic-v2-fov90-preflight-v1",
        "created_utc": capture.utc_now(),
        "pass": bool(manifest["camera"]["fixed_all_frames"]),
        "episode_id": manifest["episode_id"],
        "camera": manifest["camera"],
        "renderer": manifest["qa"]["renderer"],
        "episode_path": manifest["episode_path"],
    }
    atomic_json(PREFLIGHT_PATH, evidence)
    if not evidence["pass"]:
        raise capture.CaptureFailure(
            "fov90_preflight_failed", capture.canonical_json(evidence)
        )
    print(f"preflight={PREFLIGHT_PATH}")
    print(capture.canonical_json(evidence))
    return 0


def make_preview(row: dict[str, Any]) -> Path:
    media = PREVIEW_ROOT / "media"
    media.mkdir(parents=True, exist_ok=True)
    source = Path(row["episode_path"]) / "video.mkv"
    destination = media / f"{row['episode_id']}.mp4"
    if destination.is_file():
        return destination
    temporary = media / f".{row['episode_id']}.tmp.mp4"
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(temporary),
        ],
        check=False,
    )
    if completed.returncode:
        temporary.unlink(missing_ok=True)
        raise capture.CaptureFailure(
            "stage1_preview_encode_failed", row["episode_id"]
        )
    os.replace(temporary, destination)
    return destination


def options(values: list[str]) -> str:
    return "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in values
    )


def command_html(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(ACCEPTED_PATH)
    if len(rows) != EXPECTED_COUNT:
        raise capture.CaptureFailure(
            "stage1_html_requires_60", f"accepted={len(rows)}"
        )
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for index, path in enumerate(executor.map(make_preview, rows), 1):
            print(f"preview {index}/{EXPECTED_COUNT} {path}", flush=True)
    cards: list[str] = []
    for row in rows:
        metric = row["motion"]
        enemy = (
            f"{row['enemy_model']} skin {row['enemy_skin']}"
            if row["enemy_present"]
            else "absent"
        )
        cards.append(
            f"""
<article class="card" data-role="{html.escape(row['dataset_role'])}"
 data-bucket="{html.escape(row['primary_bucket'])}"
 data-map="{html.escape(row['map'])}"
 data-weapon="{html.escape(row['weapon'])}"
 data-net="{html.escape(metric['net_displacement_bin'])}"
 data-yaw="{html.escape(metric['yaw_range_bin'])}"
 data-pitch="{html.escape(metric['pitch_range_bin'])}"
 data-distance="{html.escape(str(row.get('actual_distance_bin') or 'none'))}">
 <video controls preload="metadata" src="media/{html.escape(row['episode_id'])}.mp4"></video>
 <h2>{html.escape(row['episode_id'])}</h2>
 <p class="role">{html.escape(row['dataset_role'])} / {html.escape(row['primary_bucket'])}</p>
 <dl>
  <dt>Map / weapon</dt><dd>{html.escape(row['map'])} / {html.escape(row['weapon'])}</dd>
  <dt>Category</dt><dd>{html.escape(row['category'])}</dd>
  <dt>Enemy</dt><dd>{html.escape(enemy)}</dd>
  <dt>Relation / distance</dt><dd>{html.escape(row['actual_target_relation'])} / {html.escape(str(row.get('actual_distance_bin') or '-'))}</dd>
  <dt>Path / net / max</dt><dd>{metric['path_length_3d']:.0f} / {metric['net_displacement_3d']:.0f} / {metric['maximum_displacement_from_start']:.0f}</dd>
  <dt>Net bin</dt><dd>{html.escape(metric['net_displacement_bin'])}</dd>
  <dt>Yaw</dt><dd>{metric['yaw_range_deg']:.1f} deg / {html.escape(metric['yaw_range_bin'])}</dd>
  <dt>Pitch</dt><dd>{metric['pitch_range_deg']:.1f} deg / {html.escape(metric['pitch_range_bin'])}</dd>
  <dt>Camera</dt><dd>FOV90 base; {row['camera']['horizontal_fov_deg']:.2f} x {row['camera']['vertical_fov_deg']:.2f} deg</dd>
 </dl>
</article>"""
        )
    filters = {
        "role": sorted({row["dataset_role"] for row in rows}),
        "bucket": sorted({row["primary_bucket"] for row in rows}),
        "map": sorted({row["map"] for row in rows}),
        "weapon": sorted({row["weapon"] for row in rows}),
        "net": list(NET_COUNTS),
        "yaw": list(YAW_COUNTS),
        "pitch": list(PITCH_COUNTS),
        "distance": ["close", "near", "medium", "far", "very_far", "none"],
    }
    controls = "".join(
        f'<label>{name}<select id="{name}"><option value="">all</option>{options(values)}</select></label>'
        for name, values in filters.items()
    )
    selectors = ",".join(f"#{name}" for name in filters)
    conditions = "&&".join(
        f"(!document.querySelector('#{name}').value||card.dataset.{name}===document.querySelector('#{name}').value)"
        for name in filters
    )
    document = f"""<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xonotic Stage 1 FOV90 分布 Review</title><style>
:root{{color-scheme:dark;font-family:Inter,system-ui,sans-serif}}body{{margin:0;background:#0b1017;color:#edf3fa}}
header{{position:sticky;top:0;z-index:2;padding:16px 22px;background:#111a26ee;border-bottom:1px solid #2b3a4c}}
h1{{margin:0 0 8px;font-size:21px}}.controls{{display:flex;gap:8px;flex-wrap:wrap}}
select{{background:#1c2837;color:#fff;border:1px solid #41536a;border-radius:7px;padding:6px}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:16px;padding:20px}}
.card{{background:#141d29;border:1px solid #2c3a4d;border-radius:12px;overflow:hidden}}
video{{display:block;width:100%;aspect-ratio:16/9;background:#000}}h2,.role,dl{{margin-left:15px;margin-right:15px}}
h2{{font-size:16px;margin-bottom:3px}}.role{{color:#75d4ff;margin-top:0}}
dl{{display:grid;grid-template-columns:125px 1fr;gap:4px 9px;font-size:13px}}
dt{{color:#94a8be}}dd{{margin:0;overflow-wrap:anywhere}}.hidden{{display:none}}
</style></head><body><header><h1>Stage 1 FOV90 真实分布 Review（60 条）</h1>
<div class="controls">{controls}</div></header><main>{''.join(cards)}</main>
<script>
const controls=document.querySelectorAll('{selectors}');
function filterCards(){{document.querySelectorAll('.card').forEach(card=>{{
const show={conditions};card.classList.toggle('hidden',!show);if(!show)card.querySelector('video').pause();
}})}}controls.forEach(control=>control.addEventListener('change',filterCards));
</script></body></html>"""
    atomic_text(PREVIEW_ROOT / "index.html", document)
    print(f"html={PREVIEW_ROOT / 'index.html'}")
    return 0


def command_audit(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(ACCEPTED_PATH)
    rejects = capture.load_jsonl(REJECTS_PATH)
    if len(rows) != EXPECTED_COUNT:
        raise capture.CaptureFailure(
            "stage1_audit_requires_60", f"accepted={len(rows)}"
        )
    failures: list[str] = []
    hash_jobs: list[tuple[str, Path, str]] = []
    probes: dict[str, Any] = {}
    qa_rows: list[dict[str, Any]] = []
    for row in rows:
        episode = Path(row["episode_path"])
        files = {path.name for path in episode.iterdir() if path.is_file()}
        episode_metadata = json.loads(
            (episode / "episode.json").read_text(encoding="utf-8")
        )
        expected_files = (
            REQUIRED_FILES
            if episode_metadata.get("model_action_contract")
            else LEGACY_REQUIRED_FILES
        )
        if files != expected_files:
            failures.append(f"{row['episode_id']}:files")
        qa = json.loads((episode / "qa.json").read_text(encoding="utf-8"))
        qa_rows.append(qa)
        if not all(qa["gates"].values()):
            failures.append(f"{row['episode_id']}:qa")
        for relative, expected in row["package_sha256"].items():
            hash_jobs.append(
                (
                    f"episode:{row['episode_id']}:{relative}",
                    episode / relative,
                    expected,
                )
            )
        raw = Path(row["raw_path"])
        for relative, expected in row["raw_sha256"].items():
            hash_jobs.append(
                (
                    f"raw:{row['attempt_id']}:{relative}",
                    raw / relative,
                    expected,
                )
            )
    for reject in rejects:
        if not reject["preserved_path"]:
            continue
        root = Path(reject["preserved_path"])
        for relative, expected in reject["preserved_sha256"].items():
            hash_jobs.append(
                (
                    f"reject:{reject['attempt_id']}:{relative}",
                    root / relative,
                    expected,
                )
            )
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        hash_results = list(executor.map(final_audit.sha_job, hash_jobs))
    hash_failures = [
        {"label": label, "actual": actual}
        for label, passed, actual in hash_results
        if not passed
    ]
    if hash_failures:
        failures.append(f"hash_mismatch:{len(hash_failures)}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(
                final_audit.ffprobe_episode,
                Path(row["episode_path"]) / "video.mkv",
            ): row["episode_id"]
            for row in rows
        }
        for future in concurrent.futures.as_completed(futures):
            probes[futures[future]] = future.result()
    for episode_id, probe in probes.items():
        if not (
            probe["decoded_frames"] == 320
            and probe["decoded_audio_samples_per_channel"] == 240000
            and probe["video_codec"] == "h264"
            and probe["video_profile"] == "High"
            and probe["audio_codec"] == "flac"
        ):
            failures.append(f"{episode_id}:media")
    checks = distribution_checks(rows)
    checks.update(
        {
            "all_base_qa": all(
                all(qa["gates"].values()) for qa in qa_rows
            ),
            "hashes": not hash_failures,
            "media": not any(":media" in item for item in failures),
        }
    )
    if not all(checks.values()):
        failures.append(capture.canonical_json(checks))
    audit = {
        "schema_version": "xonotic-v2-stage1-review-audit-v1",
        "created_utc": capture.utc_now(),
        "pass": not failures,
        "accepted": len(rows),
        "rejected_attempts": len(rejects),
        "checks": checks,
        "failures": failures,
        "distributions": {
            "roles": dict(Counter(row["dataset_role"] for row in rows)),
            "buckets": dict(Counter(row["primary_bucket"] for row in rows)),
            "maps": dict(Counter(row["map"] for row in rows)),
            "weapons": dict(Counter(row["weapon"] for row in rows)),
            "net": dict(
                Counter(
                    row["motion"]["net_displacement_bin"] for row in rows
                )
            ),
            "yaw": dict(
                Counter(row["motion"]["yaw_range_bin"] for row in rows)
            ),
            "pitch": dict(
                Counter(row["motion"]["pitch_range_bin"] for row in rows)
            ),
            "distance": dict(
                Counter(
                    row["actual_distance_bin"]
                    for row in rows
                    if row["enemy_present"]
                )
            ),
            "relation": dict(
                Counter(
                    row["actual_target_relation"]
                    for row in rows
                    if row["enemy_present"]
                )
            ),
        },
        "qa": {
            "frames_total": sum(
                probe["decoded_frames"] for probe in probes.values()
            ),
            "audio_samples_total": sum(
                probe["decoded_audio_samples_per_channel"]
                for probe in probes.values()
            ),
            "mapping_min": min(
                qa["mapping"]["success_rate"] for qa in qa_rows
            ),
            "onset_max_ms": max(
                qa["audio"]["max_onset_error_ms"] for qa in qa_rows
            ),
            "linkage_min": min(
                qa["events"]["linkage_rate"] for qa in qa_rows
            ),
            "renderer": sorted(
                {qa["runtime"]["renderer"] for qa in qa_rows}
            ),
            "horizontal_fov": sorted(
                {
                    round(qa["camera"]["horizontal_fov_deg"], 6)
                    for qa in qa_rows
                }
            ),
            "vertical_fov": sorted(
                {
                    round(qa["camera"]["vertical_fov_deg"], 6)
                    for qa in qa_rows
                }
            ),
        },
        "hashes": {
            "files_checked": len(hash_jobs),
            "mismatches": hash_failures,
        },
        "performance": {
            "live_wall_mean": mean(
                qa["runtime"]["live_wall_seconds"] for qa in qa_rows
            ),
            "render_wall_mean": mean(
                qa["runtime"]["render_wall_seconds"] for qa in qa_rows
            ),
            "x264_mean": mean(
                qa["runtime"]["x264_video_seconds_per_wall_second"]
                for qa in qa_rows
            ),
        },
    }
    atomic_json(AUDIT_PATH, audit)
    if failures:
        raise capture.CaptureFailure(
            "stage1_review_audit_failed",
            capture.canonical_json(failures),
        )
    print(f"audit={AUDIT_PATH}")
    return 0


def command_report(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(ACCEPTED_PATH)
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    lines = [
        "# Xonotic Stage 1 FOV90 distribution review",
        "",
        f"Generated UTC: `{capture.utc_now()}`",
        "",
        "**PASS for this bounded review split; no formal collection was started.**",
        "",
        f"- Accepted: `{len(rows)}`.",
        f"- Rejected attempts: `{audit['rejected_attempts']}`.",
        f"- HTML: `{PREVIEW_ROOT / 'index.html'}`.",
        f"- Manifest: `{ACCEPTED_PATH}`.",
        (
            "- Camera: fixed rectilinear FOV90 base, measured "
            f"{audit['qa']['horizontal_fov'][0]:.6f} x "
            f"{audit['qa']['vertical_fov'][0]:.6f} degrees."
        ),
        "- Only Stage 1 foundation roles are present; causal interaction is absent.",
        "",
        "## Realized distributions",
        "",
    ]
    for name, values in audit["distributions"].items():
        lines.append(
            f"- {name}: "
            + ", ".join(
                f"`{key}`={value}" for key, value in sorted(values.items())
            )
        )
    lines += [
        "",
        "## QA",
        "",
        f"- Decoded frames: `{audit['qa']['frames_total']}`.",
        (
            "- Decoded audio samples/channel: "
            f"`{audit['qa']['audio_samples_total']}`."
        ),
        f"- SHA256 files checked: `{audit['hashes']['files_checked']}`.",
        f"- Minimum frame/tick mapping: `{audit['qa']['mapping_min']:.6f}`.",
        f"- Maximum audio onset error: `{audit['qa']['onset_max_ms']:.6f} ms`.",
        "",
        "This split is permanently excluded from training. It validates the "
        "FOV90 camera and Stage 1 sampling marginals; it does not replace the "
        "remaining bounded waypoint-route controller gate.",
        "",
    ]
    atomic_text(REPORT_PATH, "\n".join(lines))
    print(f"report={REPORT_PATH}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.set_defaults(func=command_generate)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--max-retries", type=int, default=12)
    preflight.set_defaults(func=command_preflight)
    pilot = sub.add_parser("pilot")
    pilot.add_argument("--workers", type=int, default=2)
    pilot.add_argument("--max-retries", type=int, default=16)
    pilot.add_argument("--limit", type=int, default=0)
    pilot.set_defaults(func=command_pilot)
    html_parser = sub.add_parser("html")
    html_parser.set_defaults(func=command_html)
    audit = sub.add_parser("audit")
    audit.set_defaults(func=command_audit)
    report = sub.add_parser("report")
    report.set_defaults(func=command_report)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
