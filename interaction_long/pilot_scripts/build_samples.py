                      
"""Build an isolated Stage-2 controlled-motion plus interaction pilot."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

                                                                             
                                                                              
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np
import pandas as pd


PILOT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path("./xonotic_workspace")
PROTECTION_MANIFEST = Path(
    "./xonotic_workspace"
    "protected/STAGE12_BEFORE.sha256"
)
BUILD_TAG = os.environ.get(
    "XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG", "BUILD_TAG_PENDING"
)
SOURCE_COMMIT = os.environ.get(
    "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT",
    "SOURCE_COMMIT_PENDING",
)
SPEED_UNITS_PER_SECOND = 96.0
BLOCK_SECONDS = 0.8
PROMPT_CLIP_SECONDS = 4.05
PROMPT_CLIP_FRAMES = 81
FRUSTUM_TOLERANCE_SCALE = 1.12
MIN_ENEMY_SCREEN_HEIGHT_NORM = 0.045
CAMERA_TRACE_MAXIMUM_TOLERANCE = 0.003
CAMERA_TRACE_MAXIMUM_OUTLIER_FRACTION = 0.02
INDEPENDENT_RADIAL_DELTA_THRESHOLD = 20.0
TICK_HZ = 64
WARMUP_TICKS = 64
OUTPUT_TICKS = 320
PROMPT_TICKS = 256

DESIGN_MANIFEST = (
    CANONICAL_ROOT
    / "manifests/stage2_formal_40k_v1/primary/design.jsonl"
)
CORRECTED_LABELS = Path(
    "./xonotic_data/xonotic_stage_2/"
    "stage2_formal_40k_v1_output/56x1/primary/label-corrections/"
    "target-outcome-v1-20260803/labels.jsonl"
)

APPEARANCES = (
    ("erebus", 0),
    ("erebus", 1),
    ("gakmasked", 0),
    ("gakmasked", 1),
    ("ignis", 0),
    ("ignis", 1),
    ("nyx", 0),
    ("nyx", 1),
    ("pyria", 0),
    ("pyria", 1),
    ("seraphina", 0),
    ("seraphina", 1),
    ("umbra", 0),
    ("umbra", 1),
)
WEAPONS = (
    "MachineGun",
    "Shotgun",
    "Vortex",
    "Blaster",
    "Mortar",
    "Electro",
    "Crylink",
    "Hagar",
    "Devastator",
)
MOTION_LABELS = (
    "stationary",
    "player_left",
    "player_right",
    "toward_player",
    "away_from_player",
    "player_left_toward",
    "player_right_toward",
    "player_left_away",
    "player_right_away",
)
DESIRED_OUTCOMES = ("no_fire", "miss", "hit_survive", "kill")
PREFERRED_MAPS = (
    "geoplanetary",
    "catharsis",
    "courtfun",
    "implosion",
    "bromine",
)

OPPOSITE_MOTION_CODE = {
    0: 0,
    1: 2,
    2: 1,
    3: 4,
    4: 3,
    5: 8,
    6: 7,
    7: 6,
    8: 5,
}

CODE_LABEL = {
    0: "stationary",
    1: "player_left",
    2: "player_right",
    3: "toward_player",
    4: "away_from_player",
    5: "player_left_toward",
    6: "player_right_toward",
    7: "player_left_away",
    8: "player_right_away",
}

DISTANCE_TIERS = (
    {"tier": "d1", "target_units": 160.0},
    {"tier": "d2", "target_units": 215.0},
    {"tier": "d3", "target_units": 270.0},
    {"tier": "d4", "target_units": 325.0},
    {"tier": "d5", "target_units": 380.0},
)

                                                                          
                                                                
DISTANCE_TIER_SEQUENCE = {
                                                                            
    "stationary": (1, 0, 2, 0, 1, 2, 0),
    "player_left": (2, 1, 3, 1, 2, 4, 1),
    "player_right": (3, 2, 1, 2, 4, 1, 2),
    "toward_player": (4, 3, 4, 3, 4, 3, 3),
    "away_from_player": (0, 1, 2, 0, 1, 2, 0),
    "player_left_toward": (3, 4, 3, 4, 3, 4, 4),
    "player_right_toward": (4, 3, 4, 3, 4, 3),
    "player_left_away": (1, 0, 2, 0, 1, 0),
    "player_right_away": (2, 0, 1, 0, 2, 0),
}

PROMPT_SENTENCE = {
    "stationary": "The opponent remains stationary.",
    "player_left": "The opponent moves toward the player's left.",
    "player_right": "The opponent moves toward the player's right.",
    "toward_player": "The opponent moves toward the player.",
    "away_from_player": "The opponent moves away from the player.",
    "player_left_toward": (
        "The opponent moves toward the player's left while approaching the player."
    ),
    "player_right_toward": (
        "The opponent moves toward the player's right while approaching the player."
    ),
    "player_left_away": (
        "The opponent moves toward the player's left while moving away from the player."
    ),
    "player_right_away": (
        "The opponent moves toward the player's right while moving away from the player."
    ),
}

COMBAT_SENTENCE = {
    "no_damage": "The opponent is not damaged during this block.",
    "hit_alive": "The opponent is hit during this block and remains alive.",
    "killed_and_knocked_down": (
        "The opponent is killed while moving during this block, is visibly "
        "knocked to the ground, and remains dead through the end of the block."
    ),
    "killed_and_knocked_down_stationary": (
        "The opponent is killed during this block, is visibly knocked to the "
        "ground, and remains dead through the end of the block."
    ),
    "remains_dead": (
        "The opponent starts this block dead and remains dead throughout the block."
    ),
}

ONE_V_ONE_SPEED_REFERENCE = {
    "source": "120 accepted duel-v10 arena rollouts",
    "alive_ticks": 392361,
    "moving_ticks": 354780,
    "moving_speed_median_units_per_second": 361.579,
    "moving_speed_p90_units_per_second": 435.498,
}


os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(PILOT_ROOT))
os.environ.setdefault(
    "XONOTIC_CAPTURE_TMP", "./tmp/xonotic_stage2_enemy_motion_pilot_v1"
)
os.environ.setdefault("XONOTIC_BUILD_GLOB", f"build/{BUILD_TAG}")
os.environ.setdefault(
    "XONOTIC_CONDA_PREFIX_REQUIRED",
    "./environment",
)
os.environ.setdefault("XONOTIC_LIVE_TIMEOUT_SECONDS", "180")
os.environ.setdefault("XONOTIC_RENDER_TIMEOUT_SECONDS", "240")
os.environ.setdefault("XONOTIC_RENDER_STARTUP_STALL_SECONDS", "120")
os.environ.setdefault("XONOTIC_X264_THREADS", "12")
                                                                          
                                                                          
sys.path.insert(0, str(PILOT_ROOT / "scripts"))

import xonotic_capture as capture              
import xonotic_stage2_causal_formal as formal              


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_protection_check(output: Path) -> None:
    completed = subprocess.run(
        ["sha256sum", "-c", str(PROTECTION_MANIFEST)],
        cwd=CANONICAL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output.write_text(
        completed.stdout + completed.stderr, encoding="utf-8"
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"protected Stage-1/Stage-2 hash check failed: {output}"
        )


def corrected_outcomes() -> dict[str, str]:
    result: dict[str, str] = {}
    with CORRECTED_LABELS.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            result[str(row["episode_id"])] = str(
                row["corrected_actual_outcome"]
            )
    return result


def pilot_cells(sample_count: int) -> list[dict[str, Any]]:
    if not 1 <= sample_count <= 60:
        raise ValueError("sample_count must be between 1 and 60")
    cells: list[dict[str, Any]] = []
    for index in range(sample_count):
        repeat = index // (len(MOTION_LABELS) * len(DESIRED_OUTCOMES))
        motion_index = index % len(MOTION_LABELS)
        motion_ordinal = index // len(MOTION_LABELS)
        outcome_index = (motion_ordinal + motion_index) % len(DESIRED_OUTCOMES)
        motion_label = MOTION_LABELS[motion_index]
        motion_code = next(
            code for code, label in CODE_LABEL.items() if label == motion_label
        )
        desired_outcome = DESIRED_OUTCOMES[outcome_index]
        tier_sequence = DISTANCE_TIER_SEQUENCE[motion_label]
        tier_index = tier_sequence[motion_ordinal % len(tier_sequence)]
        if motion_label == "toward_player" and desired_outcome == "kill":
            tier_index = len(DISTANCE_TIERS) - 1
        distance_tier = DISTANCE_TIERS[tier_index]
        model, skin = APPEARANCES[(index * 5 + repeat) % len(APPEARANCES)]
        weapon = WEAPONS[(index * 4 + motion_index + repeat) % len(WEAPONS)]
        cells.append(
            {
                "index": index,
                "group_id": f"j{index + 1:03d}",
                "repeat": repeat,
                "motion_label": motion_label,
                "motion_code": motion_code,
                "desired_outcome": desired_outcome,
                "desired_model": model,
                "desired_skin": skin,
                "desired_weapon": weapon,
                "distance_tier": str(distance_tier["tier"]),
                "target_initial_distance_units": float(
                    distance_tier["target_units"]
                ),
                                                                         
                                                                           
                                                                       
                "program": (
                    (
                        motion_code,
                        OPPOSITE_MOTION_CODE[motion_code],
                        motion_code,
                        OPPOSITE_MOTION_CODE[motion_code],
                        motion_code,
                    )
                    if motion_code
                    else (0, 0, 0, 0, 0)
                ),
            }
        )
    return cells


def distance_is_suitable(cell: dict[str, Any], source: dict[str, Any]) -> bool:
    del cell
    distance_bin = str((source.get("formal_design") or {}).get("distance_bin"))
                                                                             
                                                                   
    return distance_bin == "near"


def aim_policy_rank(source: dict[str, Any]) -> int:
    outcome = str((source.get("formal_design") or {}).get("outcome_recipe"))
    policy = str((source.get("causal_design") or {}).get("aim_policy"))
    preferred = {
        "no_fire": ("visible_no_fire",),
        "miss": ("near_miss", "edge_graze", "stochastic_local", "stochastic_broad"),
        "hit_survive": (
            "stable_track",
            "predictive_track",
            "overshoot_correct",
            "near_miss",
            "edge_graze",
            "stochastic_local",
            "stochastic_broad",
        ),
        "kill": ("stable_track", "predictive_track", "overshoot_correct"),
    }.get(outcome, ())
    return preferred.index(policy) if policy in preferred else len(preferred)


def select_designs(sample_count: int) -> list[dict[str, Any]]:
    outcomes = corrected_outcomes()
    candidates: list[tuple[dict[str, Any], int]] = []
    with DESIGN_MANIFEST.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            source = json.loads(line)
            episode_id = str(source.get("episode_id", ""))
            desired = str((source.get("formal_design") or {}).get("outcome_recipe"))
            if (
                outcomes.get(episode_id) != desired
                or desired not in DESIRED_OUTCOMES
                or (source.get("formal_design") or {}).get("player_motion_class")
                != "certified_stationary_preflight_pair"
                or int((source.get("enemy") or {}).get("motion", -1)) != 0
            ):
                continue
            candidates.append((source, line_number))

    used: set[str] = set()
    selected: list[dict[str, Any]] = []
    map_rank = {name: index for index, name in enumerate(PREFERRED_MAPS)}
    for cell in pilot_cells(sample_count):
        exact = [
            (source, line_number)
            for source, line_number in candidates
            if source["episode_id"] not in used
            and (source["formal_design"] or {})["outcome_recipe"]
            == cell["desired_outcome"]
            and source["map"] in map_rank
            and distance_is_suitable(cell, source)
        ]
        if not exact:
            raise RuntimeError(f"no formal source for pilot cell: {cell}")
        motion_index = MOTION_LABELS.index(cell["motion_label"])
        preferred_index = (
            motion_index
            if motion_index < 5
            else motion_index - 5
        ) % len(PREFERRED_MAPS)
        exact.sort(
            key=lambda item: (
                aim_policy_rank(item[0]),
                0 if item[0]["map"] in map_rank else 1,
                (
                    (map_rank[item[0]["map"]] - preferred_index)
                    % len(PREFERRED_MAPS)
                    if item[0]["map"] in map_rank
                    else 0
                ),
                0 if item[0]["weapon"] == cell["desired_weapon"] else 1,
                item[0]["episode_id"],
            )
        )
        source, line_number = exact[0]
        used.add(str(source["episode_id"]))
        selected.append(
            {
                **cell,
                "source": source,
                "source_line_number": line_number,
            }
        )
    return selected


def motion_direction_from_axes(
    code: int, lateral: np.ndarray, radial: np.ndarray
) -> np.ndarray:
    zero = np.zeros(3, dtype=np.float64)
    raw = {
        0: zero,
        1: lateral,
        2: -lateral,
        3: radial,
        4: -radial,
        5: lateral + radial,
        6: -lateral + radial,
        7: lateral - radial,
        8: -lateral - radial,
    }[int(code)]
    norm = float(np.linalg.norm(raw))
    return raw / norm if norm > 1e-12 else zero


def prompt_motion_direction(
    scenario: dict[str, Any], code: int
) -> np.ndarray:
    enemy_origin = np.asarray(scenario["enemy"]["origin"], dtype=np.float64)
    player_origin = np.asarray(scenario["player"]["origin"], dtype=np.float64)
    lateral = np.asarray(
        scenario["enemy"]["motion_vector"], dtype=np.float64
    )
    lateral[2] = 0.0
    lateral /= max(float(np.linalg.norm(lateral)), 1e-12)
    radial = player_origin - enemy_origin
    radial[2] = 0.0
    radial /= max(float(np.linalg.norm(radial)), 1e-12)
    return motion_direction_from_axes(int(code), lateral, radial)


_formal_enemy_origin_at_server_tick = formal.enemy_origin_at_server_tick


def analytic_enemy_origin_at_server_tick(
    scenario: dict[str, Any], server_tick: int
) -> list[float]:
    program = scenario.get("enemy_motion_program")
    if not program or int((scenario.get("enemy") or {}).get("motion", 0)) != 5:
        return _formal_enemy_origin_at_server_tick(scenario, server_tick)
    origin = np.asarray(scenario["enemy"]["origin"], dtype=np.float64)
    start_tick = int(scenario["enemy"].get("motion_start_tick", WARMUP_TICKS))
    elapsed = max(0.0, (int(server_tick) - start_tick) / TICK_HZ)
    block_seconds = float(program["block_seconds"])
    speed = float(program["speed_units_per_second"])
    offset = np.zeros(3, dtype=np.float64)
    for block_index, code in enumerate(program["direction_codes"]):
        duration = min(
            block_seconds,
            max(0.0, elapsed - block_index * block_seconds),
        )
        offset += prompt_motion_direction(scenario, int(code)) * speed * duration
    return (origin + offset).tolist()


formal.enemy_origin_at_server_tick = analytic_enemy_origin_at_server_tick


def write_pilot_action_csv(
    path: Path, scenario: dict[str, Any], retry: int = 0
) -> None:
    del retry
    action_scenario = copy.deepcopy(scenario)
    reference_program = copy.deepcopy(
        scenario["action_reference_motion_program"]
    )
    action_scenario["enemy_motion_program"] = reference_program
    action_scenario["enemy"]["motion"] = (
        5 if any(int(code) for code in reference_program["direction_codes"]) else 0
    )
    rows = formal.causal_action_rows_v9(action_scenario)
    capture.validate_model_action_source_rows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"#seed,{scenario['seed']}\n")
        writer = csv.DictWriter(handle, fieldnames=capture.ACTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


_base_server_cvars = capture.server_cvars


def pilot_server_cvars(
    scenario: dict[str, Any], port: int
) -> dict[str, Any]:
    values = _base_server_cvars(scenario, port)
    program = scenario["enemy_motion_program"]
    values.update(
        {
            "capture_enemy_motion_speed": program[
                "speed_units_per_second"
            ],
            "capture_enemy_motion_block_seconds": program[
                "block_seconds"
            ],
        }
    )
    for index, code in enumerate(program["direction_codes"]):
        values[f"capture_enemy_motion_block_{index}"] = int(code)
    return values


capture.write_action_csv = write_pilot_action_csv
capture.server_cvars = pilot_server_cvars


def build_scenario(
    source: dict[str, Any], design: dict[str, Any], frozen: bool
) -> dict[str, Any]:
    group_id = str(design["group_id"])
    role = "frozen_qa" if frozen else "active"
    scenario = copy.deepcopy(source)
    source_enemy_origin = np.asarray(
        source["enemy"]["origin"], dtype=np.float64
    )
    player_origin = np.asarray(source["player"]["origin"], dtype=np.float64)
    source_ray = source_enemy_origin - player_origin
    source_distance = float(np.linalg.norm(source_ray))
    target_distance = float(design["target_initial_distance_units"])
    if source_distance + 1e-6 < target_distance:
        raise RuntimeError(
            f"distance tier {target_distance} extends beyond certified "
            f"source ray {source_distance}"
        )
    transformed_enemy_origin = (
        player_origin + source_ray / source_distance * target_distance
    )
    horizontal_ray = transformed_enemy_origin - player_origin
    horizontal_ray[2] = 0.0
    horizontal_distance = float(np.linalg.norm(horizontal_ray))
    if horizontal_distance <= 1e-12:
        raise RuntimeError("enemy/player horizontal ray is degenerate")
    horizontal_ray /= horizontal_distance
                                                                             
                                                                           
                                                                       
    initial_los_left = np.asarray(
        [-horizontal_ray[1], horizontal_ray[0], 0.0],
        dtype=np.float64,
    )
    source_motion_vector = copy.deepcopy(
        (source.get("enemy") or {}).get("motion_vector")
    )
    scenario.update(
        {
            "schema_version": "xonotic-stage2-motion-interaction-pilot-scenario-v3",
            "episode_id": (
                f"s2miv3_{group_id}_{design['distance_tier']}_"
                f"{design['desired_model']}s{design['desired_skin']}_"
                f"{source['map']}_{role}"
            ),
            "split": "pilot_review_only",
            "training_stage": "stage2",
            "training_admitted": False,
            "formal_collection_authorized": False,
            "dataset_role": "stage2_motion_interaction_near5_combo_pilot_v3",
            "target_bin": "motion_interaction_near5_combo_review",
            "target_ordinal": int(design["index"]),
            "intent_outcome": str(design["desired_outcome"]),
            "outcome_recipe_is_individual_admission_gate": False,
            "interaction_role": role,
            "counterfactual_group_id": f"s2miv3_{group_id}",
            "camera_program": str(
                (source.get("causal_design") or {}).get("aim_policy", "unknown")
            ),
            "source_formal_episode_id": source["episode_id"],
            "source_formal_scenario_sha256": hashlib.sha256(
                canonical_json(source).encode()
            ).hexdigest(),
            "source_commit_required": SOURCE_COMMIT,
            "distance_tier": str(design["distance_tier"]),
            "target_initial_distance_units": target_distance,
            "source_initial_distance_units": source_distance,
            "distance_geometry_transform": {
                "method": "interpolate_inward_on_certified_near_los_v1",
                "source_distance_bin": str(
                    (source.get("formal_design") or {}).get("distance_bin")
                ),
                "source_enemy_origin": source_enemy_origin.tolist(),
                "transformed_enemy_origin": transformed_enemy_origin.tolist(),
                "requires_live_visibility_and_screen_size_qa": True,
            },
        }
    )
    scenario["enemy"]["origin"] = transformed_enemy_origin.tolist()
    scenario["enemy"]["motion_vector"] = initial_los_left.tolist()
    scenario["enemy_motion_basis"] = {
        "schema_version": "xonotic-stage2-enemy-motion-basis-v1",
        "method": "manifest_frozen_initial_line_of_sight_left_tangent_v1",
        "player_origin": player_origin.tolist(),
        "enemy_origin": transformed_enemy_origin.tolist(),
        "initial_los_left": initial_los_left.tolist(),
        "legacy_source_motion_vector_not_used": source_motion_vector,
        "reads_camera": False,
        "reads_live_player_state": False,
    }
    if scenario.get("encounter_source"):
        scenario["encounter_source"][
            "current_trajectory_requires_recertification"
        ] = True
    active_program = {
        "schema_version": "xonotic-stage2-enemy-motion-program-v2",
        "speed_units_per_second": (
            SPEED_UNITS_PER_SECOND if int(design["motion_code"]) else 0.0
        ),
        "block_seconds": BLOCK_SECONDS,
        "direction_codes": list(design["program"]),
        "code_meanings": CODE_LABEL,
        "primary_motion": str(design["motion_label"]),
        "reads_camera": False,
        "reads_live_player_state": False,
    }
    scenario["action_reference_motion_program"] = copy.deepcopy(active_program)
    scenario["enemy_motion_program"] = copy.deepcopy(active_program)
    if frozen:
        scenario["enemy_motion_program"].update(
            {
                "speed_units_per_second": 0.0,
                "direction_codes": [0, 0, 0, 0, 0],
                "primary_motion": "stationary",
            }
        )
    scenario["enemy"].update(
        {
            "motion": (
                5 if frozen or int(design["motion_code"]) else 0
            ),
            "motion_start_tick": WARMUP_TICKS,
            "motion_distance": 0.0,
            "health": (
                max(9999.0, float(source["enemy"]["health"]))
                if frozen
                else float(source["enemy"]["health"])
            ),
            "armor": 0.0,
        }
    )
    scenario["enemy_policy"] = {
        "schema_version": "xonotic-stage2-enemy-policy-v4-pilot",
        "name": (
            "frozen_enemy_counterfactual_v1"
            if frozen
            else "fixed_speed_single_motion_interaction_v2"
        ),
        "policy_seed": int((source.get("enemy_policy") or {}).get("policy_seed", 1)),
        "motion_start_tick": WARMUP_TICKS,
        "movement_audio": "native_surface_footsteps_v1",
        "step_stride_units": 32.0,
        "closed_loop_decisions": False,
        "fires": False,
        "jumps": False,
        "reads_camera": False,
        "reads_crosshair": False,
        "runtime_reads_player_state": False,
    }
    scenario["enemy_model"] = str(design["desired_model"])
    scenario["enemy_skin"] = int(design["desired_skin"])
    return scenario


def direction_from_telemetry(
    mean_velocity: np.ndarray,
    lateral: np.ndarray,
    radial: np.ndarray,
) -> str:
    speed = float(np.linalg.norm(mean_velocity[:2]))
    if speed < 1.0:
        return "stationary"
    velocity = mean_velocity / max(
        float(np.linalg.norm(mean_velocity)), 1e-12
    )
    candidates = {
        CODE_LABEL[code]: motion_direction_from_axes(code, lateral, radial)
        for code in range(1, 9)
    }
    return max(
        candidates,
        key=lambda label: float(np.dot(velocity, candidates[label])),
    )


def project_visibility(
    states: pd.DataFrame, frames: pd.DataFrame
) -> pd.DataFrame:
    state_by_tick = {
        int(row["server_tick"]): row for _, row in states.iterrows()
    }
    rows: list[dict[str, Any]] = []
    for _, frame in frames.iloc[:PROMPT_TICKS].iterrows():
        tick = int(frame["episode_server_tick"])
        state = state_by_tick[tick]
        origin = np.asarray(state["enemy.origin"], dtype=np.float64)
        camera = np.asarray(
            [frame.camera_x, frame.camera_y, frame.camera_z],
            dtype=np.float64,
        )
        forward = np.asarray(
            [frame.forward_x, frame.forward_y, frame.forward_z],
            dtype=np.float64,
        )
        left = np.asarray(
            [frame.left_x, frame.left_y, frame.left_z],
            dtype=np.float64,
        )
        up = np.asarray(
            [frame.up_x, frame.up_y, frame.up_z], dtype=np.float64
        )
        point_rows = []
        for height in (8.0, 24.0, 44.0):
            relative = origin + np.asarray([0.0, 0.0, height]) - camera
            depth = float(np.dot(relative, forward))
            horizontal = float(np.dot(relative, left))
            vertical = float(np.dot(relative, up))
            ratio_x = horizontal / max(depth, 1e-12)
            ratio_y = vertical / max(depth, 1e-12)
            exact = (
                depth > 0
                and abs(ratio_x) <= float(frame.frustum_x)
                and abs(ratio_y) <= float(frame.frustum_y)
            )
            tolerant = (
                depth > 0
                and abs(ratio_x)
                <= float(frame.frustum_x) * FRUSTUM_TOLERANCE_SCALE
                and abs(ratio_y)
                <= float(frame.frustum_y) * FRUSTUM_TOLERANCE_SCALE
            )
            point_rows.append((depth, ratio_x, ratio_y, exact, tolerant))
        torso = point_rows[1]
        los = float(state["enemy.los_fraction"])
        enemy_present = bool(int(state["enemy.present"]))
        enemy_health = float(state["enemy.health"])
        exact_count = sum(int(row[3]) for row in point_rows)
        tolerant_count = sum(int(row[4]) for row in point_rows)
        if not enemy_present or enemy_health <= 0.0:
            visibility_state = "dead"
        elif los < 0.999999:
            visibility_state = "occluded"
        elif tolerant_count == 0:
            visibility_state = "offscreen"
        elif exact_count < len(point_rows):
            visibility_state = "edge_tolerant_visible"
        else:
            visibility_state = "visible"
        rows.append(
            {
                "frame_index": int(frame["frame_index"]),
                "server_tick": tick,
                "pts_seconds": int(frame["frame_index"]) / TICK_HZ,
                "enemy_screen_x_norm": 0.5
                - torso[1] / (2.0 * float(frame.frustum_x)),
                "enemy_screen_y_norm": 0.5
                - torso[2] / (2.0 * float(frame.frustum_y)),
                "enemy_screen_height_norm": abs(
                    point_rows[2][2] - point_rows[0][2]
                )
                / (2.0 * float(frame.frustum_y)),
                "enemy_camera_depth": torso[0],
                "enemy_distance_world": float(state["enemy.distance"]),
                "enemy_present": enemy_present,
                "enemy_health": enemy_health,
                "body_points_exact_in_frustum": exact_count,
                "body_points_tolerant_in_frustum": tolerant_count,
                "los_fraction": los,
                "visibility_state": visibility_state,
                "frustum_tolerance_scale": FRUSTUM_TOLERANCE_SCALE,
            }
        )
    return pd.DataFrame(rows)


def enemy_screen_distance_metrics(
    scenario: dict[str, Any], visibility: pd.DataFrame
) -> dict[str, Any]:
    alive = visibility[
        visibility["enemy_present"].astype(bool)
        & (pd.to_numeric(visibility["enemy_health"], errors="coerce") > 0)
    ]
    if alive.empty:
        return {
            "alive_rows": 0,
            "initial_distance_world": None,
            "target_initial_distance_world": float(
                scenario["target_initial_distance_units"]
            ),
            "initial_distance_error_world": None,
            "minimum_height_norm": None,
            "median_height_norm": None,
            "maximum_height_norm": None,
            "minimum_height_pixels": None,
            "minimum_height_threshold_norm": MIN_ENEMY_SCREEN_HEIGHT_NORM,
            "minimum_height_threshold_pixels": (
                MIN_ENEMY_SCREEN_HEIGHT_NORM
                * float(scenario["video"]["height"])
            ),
        }
    height = alive["enemy_screen_height_norm"].to_numpy(dtype=np.float64)
    initial_distance = float(alive.iloc[0]["enemy_distance_world"])
    target_distance = float(scenario["target_initial_distance_units"])
    return {
        "alive_rows": int(len(alive)),
        "initial_distance_world": initial_distance,
        "target_initial_distance_world": target_distance,
        "initial_distance_error_world": abs(initial_distance - target_distance),
        "minimum_height_norm": float(np.min(height)),
        "median_height_norm": float(np.median(height)),
        "maximum_height_norm": float(np.max(height)),
        "minimum_height_pixels": float(
            np.min(height) * float(scenario["video"]["height"])
        ),
        "minimum_height_threshold_norm": MIN_ENEMY_SCREEN_HEIGHT_NORM,
        "minimum_height_threshold_pixels": (
            MIN_ENEMY_SCREEN_HEIGHT_NORM
            * float(scenario["video"]["height"])
        ),
    }


def motion_qa(
    scenario: dict[str, Any],
    states: pd.DataFrame,
    events: pd.DataFrame,
    enemy_entity: int,
) -> dict[str, Any]:
    output = states[
        (states["server_tick"] >= WARMUP_TICKS)
        & (states["server_tick"] < WARMUP_TICKS + PROMPT_TICKS)
    ].sort_values("server_tick")
    if len(output) != PROMPT_TICKS:
        raise RuntimeError(
            f"prompt state rows mismatch: {len(output)}"
        )
    enemy_origin = np.asarray(
        scenario["enemy"]["origin"], dtype=np.float64
    )
    player_origin = np.asarray(
        scenario["player"]["origin"], dtype=np.float64
    )
    lateral = np.asarray(
        scenario["enemy"]["motion_vector"], dtype=np.float64
    )
    lateral = lateral / np.linalg.norm(lateral)
    radial = player_origin - enemy_origin
    radial[2] = 0.0
    radial = radial / np.linalg.norm(radial)
    blocks: list[dict[str, Any]] = []
    realized_labels: list[str] = []
    expected_codes = scenario["enemy_motion_program"]["direction_codes"]
    if events.empty or not {"event", "target", "killed"} <= set(events.columns):
        killed = pd.DataFrame()
    else:
        killed = events[
            (events["event"] == "damage")
            & (
                pd.to_numeric(events["target"], errors="coerce")
                == enemy_entity
            )
            & (pd.to_numeric(events["killed"], errors="coerce") == 1)
        ]
    death_tick = (
        int(pd.to_numeric(killed["server_tick"], errors="raise").min())
        if not killed.empty
        else None
    )
    for block_index in range(5):
        start = block_index * BLOCK_SECONDS
        end = (block_index + 1) * BLOCK_SECONDS
        relative_time = (
            output["server_tick"].to_numpy(dtype=np.float64)
            - WARMUP_TICKS
        ) / TICK_HZ
        selected = output[(relative_time >= start) & (relative_time < end)]
        alive = selected[
            (pd.to_numeric(selected["enemy.present"], errors="coerce") == 1)
            & (pd.to_numeric(selected["enemy.health"], errors="coerce") > 0)
        ]
        qa_required = len(alive) >= 8
        if alive.empty:
            velocities = np.zeros((0, 3), dtype=np.float64)
            speeds = np.zeros(0, dtype=np.float64)
            mean_velocity = np.zeros(3, dtype=np.float64)
            median_velocity = np.zeros(3, dtype=np.float64)
            realized_label = "dead"
        else:
            velocities = np.asarray(
                alive["enemy.velocity"].tolist(), dtype=np.float64
            )
            speeds = np.linalg.norm(velocities[:, :2], axis=1)
            mean_velocity = velocities.mean(axis=0)
            median_velocity = np.median(velocities, axis=0)
            realized_label = direction_from_telemetry(
                median_velocity, lateral, radial
            )
        realized_labels.append(realized_label)
        expected_label = CODE_LABEL[int(expected_codes[block_index])]
        label_matches = (
            realized_label == expected_label if qa_required else True
        )
        blocks.append(
            {
                "block_index": block_index,
                "start_seconds": start,
                "end_seconds": end,
                "expected_label": expected_label,
                "realized_label": realized_label,
                "label_matches": label_matches,
                "qa_required": qa_required,
                "rows": int(len(selected)),
                "alive_rows": int(len(alive)),
                "median_speed_units_per_second": float(
                    np.median(speeds) if len(speeds) else 0.0
                ),
                "p95_speed_units_per_second": float(
                    np.quantile(speeds, 0.95) if len(speeds) else 0.0
                ),
                "mean_velocity": mean_velocity.tolist(),
                "median_velocity": median_velocity.tolist(),
            }
        )
    moving_speeds = [
        row["median_speed_units_per_second"]
        for row in blocks
        if row["qa_required"] and row["expected_label"] != "stationary"
    ]
    speed_target = float(
        scenario["enemy_motion_program"]["speed_units_per_second"]
    )
    fixed_speed_error = max(
        (abs(value - speed_target) for value in moving_speeds),
        default=0.0,
    )
    return {
        "schema_version": "xonotic-stage2-enemy-motion-telemetry-qa-v1",
        "blocks": blocks,
        "realized_labels": realized_labels,
        "all_labels_match": all(row["label_matches"] for row in blocks),
        "fixed_speed_target_units_per_second": speed_target,
        "moving_block_median_speed_units_per_second": (
            float(np.median(moving_speeds)) if moving_speeds else 0.0
        ),
        "maximum_moving_block_speed_error": fixed_speed_error,
        "speed_is_fixed": fixed_speed_error <= 0.01,
        "motion_blocks_qa_count": sum(
            int(row["qa_required"] and row["expected_label"] != "stationary")
            for row in blocks
        ),
        "death_server_tick": death_tick,
    }


def interaction_metrics(
    events: pd.DataFrame, player_entity: int, enemy_entity: int
) -> dict[str, Any]:
    if events.empty or "event" not in events.columns:
        return {
            "schema_version": "xonotic-stage2-motion-interaction-outcome-v1",
            "actual_outcome": "no_fire",
            "fire_count": 0,
            "damage_count": 0,
            "kill_count": 0,
            "fire_server_ticks": [],
            "damage_server_ticks": [],
            "kill_server_ticks": [],
            "player_entity": player_entity,
            "enemy_entity": enemy_entity,
        }
    normalized = events.copy()
    for column in ("actor", "target", "attacker", "killed", "server_tick"):
        if column not in normalized.columns:
            normalized[column] = np.nan
    fire = normalized[
        (normalized["event"] == "fire")
        & (
            pd.to_numeric(normalized["actor"], errors="coerce")
            == player_entity
        )
    ]
    damage = normalized[
        (normalized["event"] == "damage")
        & (
            pd.to_numeric(normalized["target"], errors="coerce")
            == enemy_entity
        )
        & (
            pd.to_numeric(normalized["attacker"], errors="coerce")
            == player_entity
        )
    ]
    killed = damage[
        pd.to_numeric(damage["killed"], errors="coerce") == 1
    ]
    if fire.empty:
        outcome = "no_fire"
    elif not killed.empty:
        outcome = "kill"
    elif not damage.empty:
        outcome = "hit_survive"
    else:
        outcome = "miss"
    return {
        "schema_version": "xonotic-stage2-motion-interaction-outcome-v1",
        "actual_outcome": outcome,
        "fire_count": int(len(fire)),
        "damage_count": int(len(damage)),
        "kill_count": int(len(killed)),
        "fire_server_ticks": [int(value) for value in fire["server_tick"].tolist()],
        "damage_server_ticks": [
            int(value) for value in damage["server_tick"].tolist()
        ],
        "kill_server_ticks": [
            int(value) for value in killed["server_tick"].tolist()
        ],
        "player_entity": player_entity,
        "enemy_entity": enemy_entity,
    }


def interaction_semantic_checks(
    scenario: dict[str, Any], interaction: dict[str, Any]
) -> dict[str, bool]:
    prompt_end_tick = WARMUP_TICKS + PROMPT_TICKS
    observed_ticks = (
        interaction["fire_server_ticks"]
        + interaction["damage_server_ticks"]
        + interaction["kill_server_ticks"]
    )
    events_inside_prompt = all(
        WARMUP_TICKS <= int(tick) < prompt_end_tick
        for tick in observed_ticks
    )
    kill_motion_valid = True
    program = scenario["enemy_motion_program"]["direction_codes"]

    def moving_at_tick(tick: int) -> bool:
        block_index = int(
            math.floor(
                (int(tick) - WARMUP_TICKS)
                / (BLOCK_SECONDS * TICK_HZ)
            )
        )
        return (
            0 <= block_index < len(program)
            and int(program[block_index]) != 0
        )

    if interaction["kill_server_ticks"]:
        kill_tick = int(interaction["kill_server_ticks"][0])
        block_index = int(
            math.floor(
                (kill_tick - WARMUP_TICKS)
                / (BLOCK_SECONDS * TICK_HZ)
            )
        )
        if not 0 <= block_index < len(program):
            kill_motion_valid = False
        elif (
            scenario["action_reference_motion_program"]["primary_motion"]
            != "stationary"
        ):
            kill_motion_valid = int(program[block_index]) != 0
    primary_motion = scenario["action_reference_motion_program"][
        "primary_motion"
    ]
    if (
        primary_motion == "stationary"
        or interaction["actual_outcome"] == "no_fire"
    ):
        interaction_while_moving = True
    else:
        relevant_ticks = {
            "no_fire": [],
            "miss": interaction["fire_server_ticks"],
            "hit_survive": interaction["damage_server_ticks"],
            "kill": interaction["kill_server_ticks"],
        }[interaction["actual_outcome"]]
        interaction_while_moving = any(
            moving_at_tick(int(tick)) for tick in relevant_ticks
        )
    return {
        "interaction_events_inside_prompt_window": events_inside_prompt,
        "moving_kill_occurs_in_moving_block": kill_motion_valid,
        "interaction_observed_while_enemy_moving": interaction_while_moving,
    }


def outcome_recipe_is_admission_gate(scenario: dict[str, Any]) -> bool:
    """Pilot rows may gate intent; formal rows follow the Stage-2 batch rule."""
    return bool(
        scenario.get("outcome_recipe_is_individual_admission_gate", True)
    )


def player_trace_runtime_recertification_qa(
    scenario: dict[str, Any], states: pd.DataFrame
) -> dict[str, Any]:
    source = scenario.get("prefrozen_trace_source") or {}
    if not source:
        return {
            "required": False,
            "passed": True,
            "checks": {"not_required": True},
        }
    reference_path = capture.locked_root_artifact(
        str(source.get("states_path", "")),
        str(source.get("states_sha256", "")),
        "stage2_motion_player_trace_recertification_states",
    )
    reference = pd.read_parquet(reference_path).sort_values("server_tick")
    actual = states.sort_values("server_tick")
    reference = reference[
        pd.to_numeric(reference["server_tick"], errors="raise").astype(int)
        >= WARMUP_TICKS
    ]
    actual = actual[
        pd.to_numeric(actual["server_tick"], errors="raise").astype(int)
        >= WARMUP_TICKS
    ]
    rows_exact = len(reference) == len(actual) == OUTPUT_TICKS
    p95_error: float | None = None
    maximum_error: float | None = None
    if rows_exact:
        reference_origins = np.asarray(
            reference["post.origin"].tolist(), dtype=np.float64
        )
        actual_origins = np.asarray(
            actual["post.origin"].tolist(), dtype=np.float64
        )
        errors = np.linalg.norm(actual_origins - reference_origins, axis=1)
        p95_error = float(np.percentile(errors, 95))
        maximum_error = float(np.max(errors))
    recertification = source.get("runtime_recertification") or {}
    p95_limit = float(source.get("position_error_p95_max", math.nan))
    maximum_limit = float(source.get("position_error_max_max", math.nan))
    checks = {
        "rows_exact_320": rows_exact,
        "runtime_commit_rebound": source.get("source_commit")
        == SOURCE_COMMIT,
        "original_commit_preserved": bool(
            recertification.get("original_source_commit")
        ),
        "target_commit_exact": recertification.get(
            "runtime_source_commit"
        )
        == SOURCE_COMMIT,
        "live_fail_closed": recertification.get("live_fail_closed") is True,
        "no_runtime_fallback": (
            source.get("runtime_action_fallback") is False
            and source.get("runtime_geometry_fallback") is False
        ),
        "position_error_p95_within_declared_limit": bool(
            p95_error is not None and p95_error <= p95_limit
        ),
        "position_error_max_within_declared_limit": bool(
            maximum_error is not None and maximum_error <= maximum_limit
        ),
    }
    return {
        "required": True,
        "passed": all(checks.values()),
        "checks": checks,
        "reference_states_path": str(reference_path),
        "reference_states_sha256": source.get("states_sha256"),
        "position_error_p95": p95_error,
        "position_error_max": maximum_error,
        "position_error_p95_limit": p95_limit,
        "position_error_max_limit": maximum_limit,
        "runtime_recertification": recertification,
    }


def combat_label_for_block(
    interaction: dict[str, Any], block_index: int
) -> str:
    start_tick = WARMUP_TICKS + block_index * BLOCK_SECONDS * TICK_HZ
    end_tick = WARMUP_TICKS + (block_index + 1) * BLOCK_SECONDS * TICK_HZ
    kill_ticks = interaction["kill_server_ticks"]
    damage_ticks = interaction["damage_server_ticks"]
    if kill_ticks and kill_ticks[0] < start_tick:
        return "remains_dead"
    if any(start_tick <= tick < end_tick for tick in kill_ticks):
        return "killed_and_knocked_down"
    if any(start_tick <= tick < end_tick for tick in damage_ticks):
        return "hit_alive"
    return "no_damage"


def render_prompt(
    scenario: dict[str, Any], motion: dict[str, Any], interaction: dict[str, Any]
) -> dict[str, Any]:
    blocks = []
    lines = ["[ENEMY MOTION AND OUTCOME]"]
    for index, motion_block in enumerate(motion["blocks"]):
        start = index * BLOCK_SECONDS
        end = (index + 1) * BLOCK_SECONDS
        combat_label = combat_label_for_block(interaction, index)
        if combat_label == "remains_dead":
            sentence = COMBAT_SENTENCE[combat_label]
            prompt_motion_label = "dead"
        elif combat_label == "killed_and_knocked_down":
            expected_motion = motion_block["expected_label"]
            sentence = (
                PROMPT_SENTENCE[expected_motion]
                + " "
                + COMBAT_SENTENCE[
                    (
                        "killed_and_knocked_down_stationary"
                        if expected_motion == "stationary"
                        else combat_label
                    )
                ]
            )
            prompt_motion_label = expected_motion
        else:
            expected_motion = motion_block["expected_label"]
            sentence = (
                PROMPT_SENTENCE[expected_motion]
                + " "
                + COMBAT_SENTENCE[combat_label]
            )
            prompt_motion_label = expected_motion
        blocks.append(
            {
                "block_index": index,
                "start_seconds": start,
                "end_seconds": end,
                "motion_label": prompt_motion_label,
                "combat_outcome": combat_label,
                "text": sentence,
            }
        )
        lines.append(f"{start:.1f}-{end:.1f}s: {sentence}")
    return {
        "schema_version": "xonotic-stage2-motion-interaction-prompt-v2",
        "provenance": "rendered_from_64hz_motion_and_authoritative_events",
        "desired_outcome": scenario["intent_outcome"],
        "actual_outcome": interaction["actual_outcome"],
        "camera_action_described_in_text": False,
        "uses_absolute_screen_region": False,
        "uses_distance_magnitude_adjective": False,
        "uses_percentage": False,
        "blocks": blocks,
        "prompt_text": "\n".join(lines),
    }


def encode_review_video(source: Path, output: Path) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-nostdin",
        "-i",
        str(source),
        "-t",
        str(PROMPT_CLIP_SECONDS),
        "-vf",
        "fps=20",
        "-frames:v",
        str(PROMPT_CLIP_FRAMES),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-af",
        f"atrim=duration={PROMPT_CLIP_SECONDS},asetpts=PTS-STARTPTS",
        "-movflags",
        "+faststart",
        str(output),
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)


def ffprobe_summary(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-count_frames",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    payload = json.loads(completed.stdout)
    video = next(
        row for row in payload["streams"] if row["codec_type"] == "video"
    )
    audio = next(
        row for row in payload["streams"] if row["codec_type"] == "audio"
    )
    return {
        "path": str(path),
        "duration_seconds": float(payload["format"]["duration"]),
        "video_codec": video["codec_name"],
        "width": int(video["width"]),
        "height": int(video["height"]),
        "frames": int(video.get("nb_read_frames") or video["nb_frames"]),
        "frame_rate": video["avg_frame_rate"],
        "audio_codec": audio["codec_name"],
        "audio_sample_rate": int(audio["sample_rate"]),
        "audio_channels": int(audio["channels"]),
    }


def configured_pilot_render_attempts() -> int:
    raw = os.environ.get("XONOTIC_PILOT_RENDER_ATTEMPTS", "2")
    try:
        attempts = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"invalid XONOTIC_PILOT_RENDER_ATTEMPTS: {raw}"
        ) from exc
    if not 1 <= attempts <= 4:
        raise RuntimeError(
            "XONOTIC_PILOT_RENDER_ATTEMPTS must be between 1 and 4"
        )
    return attempts


def record_episode_live_phase(
    scenario: dict[str, Any],
    output_root: Path,
    scratch_root: Path,
    *,
    port: int | None = None,
    resident_lane: Any | None = None,
) -> dict[str, Any]:
    """Record one authoritative demo without starting an offline renderer.

    This is the Stage-2 equivalent of duel-v8 ``record_demo_only.sh``.  The
    returned stage is deliberately left intact so an orchestrator can wait for
    every live worker before it starts any replay/render/encode work.
    """
    episode_id = scenario["episode_id"]
    destination = output_root / "episodes" / episode_id
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite episode: {destination}")
    stage = scratch_root / episode_id
    if stage.exists():
        shutil.rmtree(stage)
    build = capture.build_root()
    if resident_lane is None:
        stage.mkdir(parents=True)
                                                                            
                                                                           
                                                                           
                                                                           
        with capture.live_slot() as live_queue_wait_seconds:
            with capture.sdl_slot() as live_sdl_queue_wait_seconds:
                live = capture.run_live_attempt(
                    stage, scenario, build, retry=0, port=port
                )
    else:
        live_sdl_queue_wait_seconds = 0.0
                                                                           
                                                                            
                                                                             
                                        
        with capture.live_slot() as live_queue_wait_seconds:
            try:
                live = resident_lane.run_live(stage, scenario, retry=0)
            except Exception:
                resident_lane.snapshot_failure_logs(stage)
                raise
    live["live_queue_wait_seconds"] = live_queue_wait_seconds
    live["live_sdl_queue_wait_seconds"] = live_sdl_queue_wait_seconds
    return {
        "schema_version": "xonotic-stage2-authoritative-live-phase-v1",
        "episode_id": episode_id,
        "stage": stage,
        "live": live,
        "resident_lane": resident_lane,
    }


def capture_episode(
    scenario: dict[str, Any],
    output_root: Path,
    scratch_root: Path,
    *,
    port: int | None = None,
    cleanup_scratch: bool = True,
    retain_raw_avi: bool = True,
    resident_lane: Any | None = None,
    prepared_live_phase: dict[str, Any] | None = None,
) -> dict[str, Any]:
    episode_id = scenario["episode_id"]
    destination = output_root / "episodes" / episode_id
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite episode: {destination}")
    if prepared_live_phase is None:
        prepared_live_phase = record_episode_live_phase(
            scenario,
            output_root,
            scratch_root,
            port=port,
            resident_lane=resident_lane,
        )
    else:
        prepared_episode_id = str(prepared_live_phase.get("episode_id", ""))
        if prepared_episode_id != str(episode_id):
            raise RuntimeError(
                "prepared live phase episode mismatch: "
                f"expected={episode_id} actual={prepared_episode_id}"
            )
        prepared_lane = prepared_live_phase.get("resident_lane")
        if prepared_lane is not resident_lane:
            raise RuntimeError("prepared live phase resident lane mismatch")
    stage = Path(prepared_live_phase["stage"])
    expected_stage = scratch_root / episode_id
    if stage.resolve() != expected_stage.resolve() or not stage.is_dir():
        raise RuntimeError(
            "prepared live phase stage mismatch: "
            f"expected={expected_stage} actual={stage}"
        )
    live = prepared_live_phase["live"]
    build = capture.build_root()
    render_attempt_errors: list[str] = []
    render: dict[str, Any] | None = None
                                                                             
                                                                          
                                                                            
                                                        
    render_attempts = (
        1 if resident_lane is not None else configured_pilot_render_attempts()
    )
    for render_attempt in range(1, render_attempts + 1):
        try:
            if resident_lane is None:
                with capture.render_slot() as render_queue_wait_seconds:
                    with capture.sdl_slot() as render_sdl_queue_wait_seconds:
                        render = capture.run_render_attempt(
                            stage,
                            scenario,
                            build,
                            Path(live["client_user"]),
                        )
            else:
                render_sdl_queue_wait_seconds = 0.0
                                                                            
                                                                            
                                                                        
                                                                 
                with capture.render_slot() as render_queue_wait_seconds:
                    render = resident_lane.run_render(stage, scenario, live)
            render["render_queue_wait_seconds"] = (
                render_queue_wait_seconds
            )
            render["render_sdl_queue_wait_seconds"] = (
                render_sdl_queue_wait_seconds
            )
            render["attempt_count"] = render_attempt
            render["prior_attempt_errors"] = render_attempt_errors
            break
        except Exception as exc:
            if resident_lane is not None:
                resident_lane.snapshot_failure_logs(stage)
            render_attempt_errors.append(f"{type(exc).__name__}: {exc}")
            if render_attempt == render_attempts:
                raise
            render_log = stage / "client_render_console.log"
            if render_log.is_file():
                os.replace(
                    render_log,
                    stage
                    / f"client_render_console_attempt_{render_attempt:02d}.log",
                )
            render_dir = stage / "render"
            if render_dir.exists():
                shutil.rmtree(render_dir)
    assert render is not None
    states, events, server_rows = capture.parse_server_telemetry(
        Path(live["server_telemetry"])
    )
    frames = pd.read_csv(render["frames_engine"])
    mapped_ticks, state_time_errors = (
        capture.map_frames_to_authoritative_states(frames, states)
    )
    frames["episode_server_tick"] = mapped_ticks
    frames["state_time_error_ms"] = state_time_errors * 1000.0
    expected_ticks = np.arange(
        WARMUP_TICKS, WARMUP_TICKS + OUTPUT_TICKS, dtype=np.int64
    )
    raw_frame_ticks = pd.to_numeric(
        frames["server_tick"], errors="raise"
    ).to_numpy(dtype=np.int64)
    frame_mapping = {
        "exact_episode_tick_span": bool(
            np.array_equal(mapped_ticks, expected_ticks)
        ),
        "maximum_state_time_error_ms": float(
            np.max(state_time_errors) * 1000.0
        ),
        "raw_server_ticks_strictly_consecutive": bool(
            len(raw_frame_ticks) == OUTPUT_TICKS
            and np.array_equal(
                np.diff(raw_frame_ticks),
                np.ones(OUTPUT_TICKS - 1, dtype=np.int64),
            )
        ),
    }
    presentation_phase = capture.fixed_demo_presentation_phase_metrics(
        frames
    )
    actions_requested = pd.read_csv(
        stage / "actions_requested.csv", comment="#"
    )
    actions_engine = pd.read_csv(live["actions_engine"])
    audio_events = pd.read_csv(render["audio_events_engine"])
    program_rows = [
        row
        for row in server_rows
        if row.get("kind") == "enemy_motion_program"
    ]
    reset_rows = [row for row in server_rows if row.get("kind") == "reset"]
    if len(reset_rows) != 1:
        raise RuntimeError(f"reset telemetry row mismatch: {len(reset_rows)}")
    player_entity = int(reset_rows[0]["player_entity"])
    enemy_entity = int(reset_rows[0]["enemy_entity"])
    if player_entity == enemy_entity:
        raise RuntimeError("player and enemy entity ids must differ")
    active_role = scenario["interaction_role"] == "active"
    engine_motion_active = int(scenario["enemy"]["motion"]) == 5
    expected_program_rows = 1 if engine_motion_active else 0
    if len(program_rows) != expected_program_rows:
        raise RuntimeError(
            f"enemy motion program row mismatch: {len(program_rows)}"
        )
    interaction = interaction_metrics(events, player_entity, enemy_entity)
    motion = motion_qa(scenario, states, events, enemy_entity)
    player_trace_recertification = player_trace_runtime_recertification_qa(
        scenario, states
    )
    visibility = project_visibility(states, frames)
    prompt = render_prompt(scenario, motion, interaction)

    destination.mkdir(parents=True)
    (destination / "raw").mkdir()
    (destination / "telemetry").mkdir()
    (destination / "media").mkdir()
    shutil.copy2(
        live["server_telemetry"], destination / "raw/server.jsonl"
    )
    shutil.copy2(
        stage / "actions_requested.csv",
        destination / "raw/actions_requested.csv",
    )
    shutil.copy2(
        live["actions_engine"], destination / "raw/actions_engine.csv"
    )
    shutil.copy2(
        render["frames_engine"], destination / "raw/frames_engine.csv"
    )
    shutil.copy2(
        render["audio_events_engine"],
        destination / "raw/audio_events_engine.csv",
    )
    shutil.copy2(live["demo_path"], destination / "raw/source.dem")
    if retain_raw_avi:
        shutil.copy2(render["raw_avi"], destination / "raw/source.avi")
    shutil.copy2(stage / "server_console.log", destination / "raw/")
    shutil.copy2(stage / "client_live_console.log", destination / "raw/")
    shutil.copy2(stage / "client_render_console.log", destination / "raw/")
    for prior_render_log in sorted(
        stage.glob("client_render_console_attempt_*.log")
    ):
        shutil.copy2(prior_render_log, destination / "raw/")

    states.to_parquet(destination / "telemetry/states_64hz.parquet")
    events.to_parquet(destination / "telemetry/events_64hz.parquet")
    frames.to_parquet(destination / "telemetry/frames_64hz.parquet")
    actions_requested.to_parquet(
        destination / "telemetry/actions_requested_64hz.parquet"
    )
    actions_engine.to_parquet(
        destination / "telemetry/actions_engine_64hz.parquet"
    )
    audio_events.to_parquet(
        destination / "telemetry/audio_events_64hz.parquet"
    )
    visibility.to_parquet(
        destination / "telemetry/visibility_64hz.parquet"
    )
    write_json(destination / "telemetry/interaction.json", interaction)

    audio_start_sample = int(
        frames.iloc[0]["mixer_audio_cursor_at_frame"]
    )
    full_video = destination / "media/source_64hz.mkv"
    capture.encode_video(
        Path(render["raw_avi"]),
        full_video,
        destination / "raw/ffmpeg_encode.log",
        audio_start_sample,
    )
    source_probe = ffprobe_summary(full_video)
    if source_probe["frames"] != OUTPUT_TICKS:
        raise RuntimeError(
            "source frame count mismatch after encode: "
            f"{source_probe['frames']}"
        )
    review_video = destination / "media/review_20hz_81f.mp4"
    encode_review_video(full_video, review_video)
    review_probe = ffprobe_summary(review_video)
    if review_probe["frames"] != PROMPT_CLIP_FRAMES:
        raise RuntimeError(
            f"review frame count mismatch: {review_probe['frames']}"
        )

    visibility_counts = {
        str(key): int(value)
        for key, value in visibility["visibility_state"]
        .value_counts()
        .to_dict()
        .items()
    }
    screen_distance = enemy_screen_distance_metrics(scenario, visibility)
    alive_states = states[
        (pd.to_numeric(states["enemy.present"], errors="coerce") == 1)
        & (pd.to_numeric(states["enemy.health"], errors="coerce") > 0)
    ]
    appearance_matches = bool(
        not alive_states.empty
        and set(alive_states["enemy.model"].astype(str))
        == {str(scenario["enemy_model"])}
        and set(pd.to_numeric(alive_states["enemy.skin"], errors="raise").astype(int))
        == {int(scenario["enemy_skin"])}
        and set(pd.to_numeric(alive_states["enemy.color"], errors="raise").astype(int))
        == {int(scenario["enemy_color"])}
    )
    desired_outcome_matches = (
        interaction["actual_outcome"] == scenario["intent_outcome"]
    )
    moving_program = any(
        int(code)
        for code in scenario["enemy_motion_program"]["direction_codes"]
    )
    semantic_checks = {
        key: value if active_role else True
        for key, value in interaction_semantic_checks(
            scenario, interaction
        ).items()
    }
    checks = {
        "server_state_rows_384": len(states) == 384,
        "render_frame_rows_320": len(frames) == OUTPUT_TICKS,
        "exact_episode_tick_span_64_through_383": frame_mapping[
            "exact_episode_tick_span"
        ],
        "zero_error_frame_state_mapping": frame_mapping[
            "maximum_state_time_error_ms"
        ]
        <= 1e-9,
        "raw_server_ticks_strictly_consecutive": frame_mapping[
            "raw_server_ticks_strictly_consecutive"
        ],
        "fixed_demo_presentation_phase": presentation_phase["passed"],
        "requested_action_rows_384": len(actions_requested) == 384,
        "engine_action_rows_384": len(actions_engine) == 384,
        "review_video_81_frames": review_probe["frames"]
        == PROMPT_CLIP_FRAMES,
        "realized_prompt_labels_match_program": motion[
            "all_labels_match"
        ],
        "fixed_speed_exact": (
            motion["speed_is_fixed"] if engine_motion_active else True
        ),
        "moving_program_has_motion_qa_before_death": (
            motion["motion_blocks_qa_count"] >= 1
            if moving_program
            else True
        ),
        "prefrozen_player_trace_runtime_recertified": (
            player_trace_recertification["passed"]
        ),
        "desired_interaction_outcome_realized": (
            desired_outcome_matches
            if active_role and outcome_recipe_is_admission_gate(scenario)
            else True
        ),
        **semantic_checks,
        "enemy_appearance_matches_scenario": appearance_matches,
        "no_occlusion": (
            visibility_counts.get("occluded", 0) == 0
            if active_role
            else True
        ),
        "no_true_offscreen_after_tolerance": visibility_counts.get(
            "offscreen", 0
        )
        == 0
        if active_role
        else True,
        "initial_distance_matches_tier": bool(
            screen_distance["initial_distance_error_world"] is not None
            and screen_distance["initial_distance_error_world"] <= 1.0
        ),
        "enemy_never_too_small_in_pixels": bool(
            screen_distance["minimum_height_norm"] is not None
            and screen_distance["minimum_height_norm"]
            >= MIN_ENEMY_SCREEN_HEIGHT_NORM
        )
        if active_role
        else True,
        "camera_action_not_in_prompt": not prompt[
            "camera_action_described_in_text"
        ],
    }
    qa = {
        "schema_version": "xonotic-stage2-motion-interaction-pilot-episode-qa-v3",
        "episode_id": episode_id,
        "role": "active" if active_role else "frozen_counterfactual",
        "checks": checks,
        "pre_pair_passed": all(checks.values()),
        "training_admitted": False,
        "motion": motion,
        "player_trace_runtime_recertification": (
            player_trace_recertification
        ),
        "interaction": interaction,
        "visibility_counts": visibility_counts,
        "screen_distance": screen_distance,
        "frustum_tolerance_scale": FRUSTUM_TOLERANCE_SCALE,
        "frame_mapping": frame_mapping,
        "presentation_phase": presentation_phase,
        "review_media": review_probe,
        "source_media": source_probe,
        "raw_avi_retained": retain_raw_avi,
        "live_wall_seconds": live["live_wall_seconds"],
        "render_wall_seconds": render["render_wall_seconds"],
        "render_attempt_count": render["attempt_count"],
        "render_prior_attempt_errors": render["prior_attempt_errors"],
        "renderer": render["renderer"],
        "runtime": {
            "execution_mode": (
                "resident_accelerated"
                if resident_lane is not None
                else "oneshot"
            ),
            "offline_accelerate": bool(
                render.get("offline_accelerate", False)
            ),
            "capturevideo_realtime": render.get(
                "capturevideo_realtime"
            ),
            "render_local_slowmo": render.get(
                "render_local_slowmo"
            ),
            "effective_demo_timescale": render.get(
                "effective_demo_timescale"
            ),
            "x264_threads": capture.configured_x264_threads(),
            "x264_cpuset": capture.configured_x264_cpuset(),
            "x264_cpuset_cpu_count": (
                capture.configured_x264_cpuset_cpu_count()
            ),
            "live_time_scale": live.get("live_time_scale", 1),
            "live_server_ticrate": live.get("live_server_ticrate"),
            "live_netfps": live.get("live_netfps"),
            "live_maxfps": live.get("live_maxfps"),
            "live_capture_geometry": render.get(
                "live_capture_geometry"
            ),
            "resident_lane": {
                "enabled": resident_lane is not None,
                "sequence": live.get("resident_sequence"),
                "process_reused": live.get(
                    "resident_process_reused", False
                ),
                "server_reset": live.get("resident_server_reset"),
                "token": live.get("resident_token"),
                "server_idle_ticrate": live.get(
                    "resident_server_idle_ticrate"
                ),
                "server_idle_slowmo": live.get(
                    "resident_server_idle_slowmo"
                ),
                "server_idle_throttle_verified": live.get(
                    "resident_server_idle_throttle_verified", False
                ),
                "server_idle_throttle_wall_seconds": live.get(
                    "resident_server_idle_throttle_wall_seconds"
                ),
                "cpu_isolation_enabled": live.get(
                    "resident_cpu_isolation_enabled", False
                ),
                "live_cpu_slot": live.get("resident_live_cpu_slot"),
                "reserved_live_cpus": live.get(
                    "resident_reserved_live_cpus", []
                ),
                "background_cpus": live.get(
                    "resident_background_cpus", []
                ),
                "server_cpu_scheduling": live.get(
                    "resident_server_cpu_scheduling"
                ),
                "live_client_cpu_scheduling": live.get(
                    "resident_live_client_cpu_scheduling"
                ),
                "render_client_cpu_scheduling": render.get(
                    "render_client_cpu_scheduling"
                ),
                "render_generation": render.get("render_generation"),
                "render_process_recycled_after_episode": render.get(
                    "render_process_recycled_after_episode", False
                ),
                "render_process_recycle_wall_seconds": render.get(
                    "render_process_recycle_wall_seconds", 0.0
                ),
                "process_startup_seconds": (
                    dict(resident_lane.process_startup_seconds)
                    if resident_lane is not None
                    else {}
                ),
            },
        },
    }
    write_json(destination / "scenario.json", scenario)
    write_json(destination / "prompt.json", prompt)
    write_json(destination / "qa.json", qa)
    if resident_lane is not None:
                                                                           
                                                                    
        Path(live["demo_path"]).unlink(missing_ok=True)
    if cleanup_scratch:
        shutil.rmtree(stage)
    return {
        "episode_id": episode_id,
        "role": qa["role"],
        "episode_path": str(destination),
        "scenario": scenario,
        "prompt": prompt,
        "qa": qa,
        "review_video": str(review_video),
    }


def load_packaged_episode(output_root: Path, episode_id: str) -> dict[str, Any]:
    destination = output_root / "episodes" / episode_id
    required = [
        destination / "scenario.json",
        destination / "prompt.json",
        destination / "qa.json",
        destination / "media/review_20hz_81f.mp4",
        destination / "telemetry/frames_64hz.parquet",
        destination / "telemetry/states_64hz.parquet",
        destination / "telemetry/events_64hz.parquet",
        destination / "telemetry/visibility_64hz.parquet",
        destination / "raw/server.jsonl",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(
            f"incomplete packaged episode cannot resume: {missing}"
        )
    scenario = json.loads(
        (destination / "scenario.json").read_text(encoding="utf-8")
    )
    prompt = json.loads(
        (destination / "prompt.json").read_text(encoding="utf-8")
    )
    qa = json.loads(
        (destination / "qa.json").read_text(encoding="utf-8")
    )
    states = pd.read_parquet(destination / "telemetry/states_64hz.parquet")
    events = pd.read_parquet(destination / "telemetry/events_64hz.parquet")
    visibility = pd.read_parquet(
        destination / "telemetry/visibility_64hz.parquet"
    )
    _, _, server_rows = capture.parse_server_telemetry(
        destination / "raw/server.jsonl"
    )
    reset_rows = [row for row in server_rows if row.get("kind") == "reset"]
    if len(reset_rows) != 1:
        raise RuntimeError(f"reset telemetry row mismatch: {len(reset_rows)}")
    player_entity = int(reset_rows[0]["player_entity"])
    enemy_entity = int(reset_rows[0]["enemy_entity"])
    interaction = interaction_metrics(events, player_entity, enemy_entity)
    motion = motion_qa(scenario, states, events, enemy_entity)
    prompt = render_prompt(scenario, motion, interaction)
    visibility_counts = {
        str(key): int(value)
        for key, value in visibility["visibility_state"]
        .value_counts()
        .to_dict()
        .items()
    }
    screen_distance = enemy_screen_distance_metrics(scenario, visibility)
    alive_states = states[
        (pd.to_numeric(states["enemy.present"], errors="coerce") == 1)
        & (pd.to_numeric(states["enemy.health"], errors="coerce") > 0)
    ]
    appearance_matches = bool(
        not alive_states.empty
        and set(alive_states["enemy.model"].astype(str))
        == {str(scenario["enemy_model"])}
        and set(
            pd.to_numeric(alive_states["enemy.skin"], errors="raise").astype(int)
        )
        == {int(scenario["enemy_skin"])}
        and set(
            pd.to_numeric(alive_states["enemy.color"], errors="raise").astype(int)
        )
        == {int(scenario["enemy_color"])}
    )
    active_role = scenario["interaction_role"] == "active"
    engine_motion_active = int(scenario["enemy"]["motion"]) == 5
    moving_program = any(
        int(code)
        for code in scenario["enemy_motion_program"]["direction_codes"]
    )
    semantic_checks = {
        key: value if active_role else True
        for key, value in interaction_semantic_checks(
            scenario, interaction
        ).items()
    }
    qa["schema_version"] = (
        "xonotic-stage2-motion-interaction-pilot-episode-qa-v3"
    )
    qa["motion"] = motion
    qa["interaction"] = interaction
    qa["visibility_counts"] = visibility_counts
    qa["screen_distance"] = screen_distance
    qa["checks"].update(
        {
            "realized_prompt_labels_match_program": motion[
                "all_labels_match"
            ],
            "fixed_speed_exact": (
                motion["speed_is_fixed"] if engine_motion_active else True
            ),
            "moving_program_has_motion_qa_before_death": (
                motion["motion_blocks_qa_count"] >= 1
                if moving_program
                else True
            ),
            "desired_interaction_outcome_realized": (
                interaction["actual_outcome"] == scenario["intent_outcome"]
                if active_role
                and outcome_recipe_is_admission_gate(scenario)
                else True
            ),
            **semantic_checks,
            "enemy_appearance_matches_scenario": appearance_matches,
            "no_occlusion": (
                visibility_counts.get("occluded", 0) == 0
                if active_role
                else True
            ),
            "no_true_offscreen_after_tolerance": (
                visibility_counts.get("offscreen", 0) == 0
                if active_role
                else True
            ),
            "initial_distance_matches_tier": bool(
                screen_distance["initial_distance_error_world"] is not None
                and screen_distance["initial_distance_error_world"] <= 1.0
            ),
            "enemy_never_too_small_in_pixels": bool(
                screen_distance["minimum_height_norm"] is not None
                and screen_distance["minimum_height_norm"]
                >= MIN_ENEMY_SCREEN_HEIGHT_NORM
            )
            if active_role
            else True,
            "camera_action_not_in_prompt": not prompt[
                "camera_action_described_in_text"
            ],
        }
    )
    qa["pre_pair_passed"] = all(qa["checks"].values())
    write_json(destination / "telemetry/interaction.json", interaction)
    write_json(destination / "prompt.json", prompt)
    write_json(destination / "qa.json", qa)
    return {
        "episode_id": episode_id,
        "role": qa["role"],
        "episode_path": str(destination),
        "scenario": scenario,
        "prompt": prompt,
        "qa": qa,
        "review_video": str(
            destination / "media/review_20hz_81f.mp4"
        ),
    }


def camera_matrix(frames: pd.DataFrame) -> np.ndarray:
    columns = [
        "camera_x",
        "camera_y",
        "camera_z",
        "forward_x",
        "forward_y",
        "forward_z",
        "left_x",
        "left_y",
        "left_z",
        "up_x",
        "up_y",
        "up_z",
        "frustum_x",
        "frustum_y",
    ]
    return frames.iloc[:PROMPT_TICKS][columns].to_numpy(dtype=np.float64)


def pair_qa(active: dict[str, Any], frozen: dict[str, Any]) -> dict[str, Any]:
    active_path = Path(active["episode_path"])
    frozen_path = Path(frozen["episode_path"])
    active_frames = pd.read_parquet(
        active_path / "telemetry/frames_64hz.parquet"
    )
    frozen_frames = pd.read_parquet(
        frozen_path / "telemetry/frames_64hz.parquet"
    )
    active_visibility = pd.read_parquet(
        active_path / "telemetry/visibility_64hz.parquet"
    )
    frozen_visibility = pd.read_parquet(
        frozen_path / "telemetry/visibility_64hz.parquet"
    )
    active_actions = pd.read_parquet(
        active_path / "telemetry/actions_requested_64hz.parquet"
    )
    frozen_actions = pd.read_parquet(
        frozen_path / "telemetry/actions_requested_64hz.parquet"
    )
    active_states = pd.read_parquet(
        active_path / "telemetry/states_64hz.parquet"
    )
    frozen_states = pd.read_parquet(
        frozen_path / "telemetry/states_64hz.parquet"
    )
    camera_error = np.abs(
        camera_matrix(active_frames) - camera_matrix(frozen_frames)
    )
    camera_bad_rows = np.any(camera_error > 1e-5, axis=1)
    action_columns = [
        column
        for column in capture.ACTION_COLUMNS
        if column in active_actions.columns and column in frozen_actions.columns
    ]
    action_error = np.abs(
        active_actions[action_columns].to_numpy(dtype=np.float64)
        - frozen_actions[action_columns].to_numpy(dtype=np.float64)
    )
    screen_residual = active_visibility[
        ["enemy_screen_x_norm", "enemy_screen_y_norm"]
    ].to_numpy() - frozen_visibility[
        ["enemy_screen_x_norm", "enemy_screen_y_norm"]
    ].to_numpy()
    distance_residual = (
        active_visibility["enemy_distance_world"].to_numpy(dtype=np.float64)
        - frozen_visibility["enemy_distance_world"].to_numpy(dtype=np.float64)
    )
    active_output_states = active_states[
        (active_states["server_tick"] >= WARMUP_TICKS)
        & (
            active_states["server_tick"]
            < WARMUP_TICKS + PROMPT_TICKS
        )
    ].sort_values("server_tick")
    frozen_output_states = frozen_states[
        (frozen_states["server_tick"] >= WARMUP_TICKS)
        & (
            frozen_states["server_tick"]
            < WARMUP_TICKS + PROMPT_TICKS
        )
    ].sort_values("server_tick")
    if (
        len(active_output_states) != PROMPT_TICKS
        or len(frozen_output_states) != PROMPT_TICKS
    ):
        raise RuntimeError("pair QA requires exact 320-row state traces")
    enemy_origin_residual = np.asarray(
        active_output_states["enemy.origin"].tolist(), dtype=np.float64
    ) - np.asarray(
        frozen_output_states["enemy.origin"].tolist(), dtype=np.float64
    )
    scenario = active["scenario"]
    lateral_axis = np.asarray(
        scenario["enemy"]["motion_vector"], dtype=np.float64
    )
    lateral_axis[2] = 0.0
    lateral_axis /= max(float(np.linalg.norm(lateral_axis)), 1e-12)
    radial_axis = np.asarray(
        scenario["player"]["origin"], dtype=np.float64
    ) - np.asarray(scenario["enemy"]["origin"], dtype=np.float64)
    radial_axis[2] = 0.0
    radial_axis /= max(float(np.linalg.norm(radial_axis)), 1e-12)
    block_residuals = []
    for block_index in range(5):
        start = int(round(block_index * BLOCK_SECONDS * TICK_HZ))
        end = int(round((block_index + 1) * BLOCK_SECONDS * TICK_HZ))
        values = screen_residual[start:end]
        block_residuals.append(
            {
                "block_index": block_index,
                "mean_x": float(values[:, 0].mean()),
                "mean_y": float(values[:, 1].mean()),
                "end_x": float(values[-1, 0]),
                "end_y": float(values[-1, 1]),
            }
        )
    primary_motion = str(
        active["scenario"]["action_reference_motion_program"]["primary_motion"]
    )
    candidate_blocks = [
        row["block_index"]
        for row in active["qa"]["motion"]["blocks"]
        if row["qa_required"] and row["expected_label"] == primary_motion
    ]
    if not candidate_blocks:
        independent = {
            "block_index": None,
            "screen_delta_x": None,
            "observed_world_distance_delta": None,
            "enemy_lateral_displacement_delta": None,
            "enemy_radial_displacement_delta": None,
            "realized_label": "unobservable",
        }
    else:
        block_index = int(candidate_blocks[0])
        start = int(round(block_index * BLOCK_SECONDS * TICK_HZ))
        end = int(round((block_index + 1) * BLOCK_SECONDS * TICK_HZ))
        active_block = active_visibility.iloc[start:end]
        frozen_block = frozen_visibility.iloc[start:end]
        valid = (
            active_block["enemy_present"].astype(bool).to_numpy()
            & (active_block["enemy_health"].to_numpy(dtype=np.float64) > 0)
            & frozen_block["enemy_present"].astype(bool).to_numpy()
            & (frozen_block["enemy_health"].to_numpy(dtype=np.float64) > 0)
        )
        positions = np.flatnonzero(valid)
        if len(positions) < 8:
            independent = {
                "block_index": block_index,
                "screen_delta_x": None,
                "observed_world_distance_delta": None,
                "enemy_lateral_displacement_delta": None,
                "enemy_radial_displacement_delta": None,
                "realized_label": "unobservable",
            }
        else:
            head = positions[: min(4, len(positions))]
            tail = positions[-min(4, len(positions)) :]
            screen_delta_x = float(
                np.median(screen_residual[start:end][tail, 0])
                - np.median(screen_residual[start:end][head, 0])
            )
            world_distance_delta = float(
                np.median(distance_residual[start:end][tail])
                - np.median(distance_residual[start:end][head])
            )
            enemy_displacement_delta = (
                np.median(
                    enemy_origin_residual[start:end][tail], axis=0
                )
                - np.median(
                    enemy_origin_residual[start:end][head], axis=0
                )
            )
            enemy_lateral_displacement_delta = float(
                np.dot(enemy_displacement_delta, lateral_axis)
            )
            enemy_radial_displacement_delta = float(
                np.dot(enemy_displacement_delta, radial_axis)
            )
            horizontal_label = None
            radial_label = None
            if abs(screen_delta_x) >= 0.03:
                horizontal_label = (
                    "player_left" if screen_delta_x < 0 else "player_right"
                )
            if (
                enemy_radial_displacement_delta
                >= INDEPENDENT_RADIAL_DELTA_THRESHOLD
            ):
                radial_label = "toward"
            elif (
                enemy_radial_displacement_delta
                <= -INDEPENDENT_RADIAL_DELTA_THRESHOLD
            ):
                radial_label = "away"
            if horizontal_label and radial_label:
                realized_label = f"{horizontal_label}_{radial_label}"
            elif horizontal_label:
                realized_label = horizontal_label
            elif radial_label == "toward":
                realized_label = "toward_player"
            elif radial_label == "away":
                realized_label = "away_from_player"
            else:
                realized_label = "stationary"
            independent = {
                "block_index": block_index,
                "screen_delta_x": screen_delta_x,
                "observed_world_distance_delta": world_distance_delta,
                "enemy_lateral_displacement_delta": (
                    enemy_lateral_displacement_delta
                ),
                "enemy_radial_displacement_delta": (
                    enemy_radial_displacement_delta
                ),
                "realized_label": realized_label,
            }
    checks = {
        "same_requested_action_trace": float(action_error.max()) <= 1e-9,
                                                                             
                                                                        
        "same_camera_trace": bool(
            int(camera_bad_rows.sum())
            <= math.ceil(
                CAMERA_TRACE_MAXIMUM_OUTLIER_FRACTION * PROMPT_TICKS
            )
            and float(camera_error.max()) <= CAMERA_TRACE_MAXIMUM_TOLERANCE
        ),
        "active_pre_pair_passed": bool(active["qa"]["pre_pair_passed"]),
        "frozen_pre_pair_passed": bool(frozen["qa"]["pre_pair_passed"]),
        "frozen_motion_is_stationary": all(
            label == "stationary"
            for label in frozen["qa"]["motion"]["realized_labels"]
        ),
        "independent_screen_space_direction_matches": (
            independent["realized_label"] == primary_motion
        ),
    }
    report = {
        "schema_version": "xonotic-stage2-motion-interaction-pair-qa-v4",
        "group_id": active["scenario"]["episode_id"].split("_")[1],
        "active_episode_id": active["episode_id"],
        "frozen_episode_id": frozen["episode_id"],
        "checks": checks,
        "passed": all(checks.values()),
        "maximum_camera_trace_error": float(camera_error.max()),
        "camera_trace_rows_over_1e_5": int(camera_bad_rows.sum()),
        "camera_trace_maximum_outlier_fraction": (
            CAMERA_TRACE_MAXIMUM_OUTLIER_FRACTION
        ),
        "camera_trace_maximum_tolerance": CAMERA_TRACE_MAXIMUM_TOLERANCE,
        "maximum_requested_action_trace_error": float(action_error.max()),
        "primary_motion": primary_motion,
        "independent_thresholds": {
            "absolute_screen_delta_x": 0.03,
            "absolute_enemy_radial_displacement_delta": (
                INDEPENDENT_RADIAL_DELTA_THRESHOLD
            ),
        },
        "radial_deconfounding_method": (
            "active_minus_frozen_enemy_displacement_projected_on_"
            "manifest_frozen_initial_radial_axis_v1"
        ),
        "independent_screen_space_motion": independent,
        "screen_residual_active_minus_frozen": block_residuals,
    }
    write_json(active_path / "pair_qa.json", report)
    write_json(frozen_path / "pair_qa.json", report)
    return report


def artifact_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-name", default="stage2_motion_interaction_pilot_v2"
    )
    parser.add_argument("--samples", type=int, default=60)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--port-base", type=int, default=23000)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse complete packaged episodes in an existing output",
    )
    parser.add_argument(
        "--sample-index",
        action="append",
        type=int,
        help="capture only this 1-based sample index; may be repeated",
    )
    args = parser.parse_args()
    if not 1 <= args.samples <= 60:
        parser.error("--samples must be between 1 and 60")
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    if not 1024 <= args.port_base <= 65535 - args.samples:
        parser.error("--port-base leaves the valid UDP port range")
    if args.sample_index and any(
        index < 1 or index > args.samples for index in args.sample_index
    ):
        parser.error("--sample-index must be within 1..--samples")
    if "PENDING" in BUILD_TAG or "PENDING" in SOURCE_COMMIT:
        raise RuntimeError(
            "set XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG and "
            "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT"
        )
    all_designs = select_designs(args.samples)
    requested_indices = set(args.sample_index or [])
    designs = [
        row
        for row in all_designs
        if not requested_indices or row["index"] + 1 in requested_indices
    ]
    output_root = PILOT_ROOT / "outputs" / args.output_name
    if output_root.exists() and not args.resume:
        raise RuntimeError(f"refusing to overwrite output: {output_root}")
    output_root.mkdir(parents=True, exist_ok=args.resume)
    scratch_root = Path(os.environ["XONOTIC_CAPTURE_TMP"]) / args.output_name
    scratch_root.mkdir(parents=True, exist_ok=True)
    run_protection_check(output_root / "STAGE12_PRECHECK.txt")
    source_records = []
    for design in all_designs:
        source = design["source"]
        source_records.append(
            {
                "episode_id": source["episode_id"],
                "manifest_path": str(DESIGN_MANIFEST),
                "line_number": design["source_line_number"],
                "scenario_sha256": hashlib.sha256(
                    canonical_json(source).encode()
                ).hexdigest(),
                "pilot_group_id": design["group_id"],
                "primary_motion": design["motion_label"],
                "desired_outcome": design["desired_outcome"],
                "enemy_model": source["enemy_model"],
                "enemy_skin": int(source["enemy_skin"]),
                "weapon": source["weapon"],
                "map": source["map"],
                "source_distance_bin": str(
                    (source.get("formal_design") or {}).get("distance_bin")
                ),
                "distance_tier": design["distance_tier"],
                "target_initial_distance_units": design[
                    "target_initial_distance_units"
                ],
            }
        )
    write_json(output_root / "source_records.json", source_records)

    def capture_design(
        design: dict[str, Any], local_index: int
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source = design["source"]
        active_scenario = build_scenario(source, design, frozen=False)
        frozen_scenario = build_scenario(source, design, frozen=True)
        port = args.port_base + local_index
        active_destination = (
            output_root / "episodes" / active_scenario["episode_id"]
        )
        if args.resume and active_destination.is_dir():
            print(f"reuse {active_scenario['episode_id']}", flush=True)
            active = load_packaged_episode(
                output_root, active_scenario["episode_id"]
            )
        else:
            print(f"capture {active_scenario['episode_id']}", flush=True)
            active = capture_episode(
                active_scenario,
                output_root,
                scratch_root,
                port=port,
            )
        frozen_destination = (
            output_root / "episodes" / frozen_scenario["episode_id"]
        )
        if args.resume and frozen_destination.is_dir():
            print(f"reuse {frozen_scenario['episode_id']}", flush=True)
            frozen = load_packaged_episode(
                output_root, frozen_scenario["episode_id"]
            )
        else:
            print(f"capture {frozen_scenario['episode_id']}", flush=True)
            frozen = capture_episode(
                frozen_scenario,
                output_root,
                scratch_root,
                port=port,
            )
        report = pair_qa(active, frozen)
        return [active, frozen], report

    completed_by_index: dict[
        int, tuple[list[dict[str, Any]], dict[str, Any]]
    ] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(capture_design, design, local_index): local_index
            for local_index, design in enumerate(designs)
        }
        for future in concurrent.futures.as_completed(futures):
            local_index = futures[future]
            completed_by_index[local_index] = future.result()
    episodes: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    for local_index in range(len(designs)):
        captured, report = completed_by_index[local_index]
        episodes.extend(captured)
        pairs.append(report)

    run_protection_check(output_root / "STAGE12_POSTCHECK.txt")
    active_rows = [row for row in episodes if row["role"] == "active"]
    release_rows = []
    for row in active_rows:
        pair = next(
            pair
            for pair in pairs
            if pair["active_episode_id"] == row["episode_id"]
        )
        admitted = bool(row["qa"]["pre_pair_passed"] and pair["passed"])
        release_rows.append(
            {
                "schema_version": "xonotic-stage2-motion-interaction-pilot-sample-v3",
                "sample_id": row["episode_id"],
                "training_admitted": False,
                "review_admitted": admitted,
                "video_path": row["review_video"],
                "source_video_path": str(
                    Path(row["episode_path"]) / "media/source_64hz.mkv"
                ),
                "action_path": str(
                    Path(row["episode_path"])
                    / "telemetry/actions_requested_64hz.parquet"
                ),
                "state_path": str(
                    Path(row["episode_path"])
                    / "telemetry/states_64hz.parquet"
                ),
                "visibility_path": str(
                    Path(row["episode_path"])
                    / "telemetry/visibility_64hz.parquet"
                ),
                "prompt_path": str(
                    Path(row["episode_path"]) / "prompt.json"
                ),
                "prompt_text": row["prompt"]["prompt_text"],
                "map": row["scenario"]["map"],
                "distance_tier": row["scenario"]["distance_tier"],
                "target_initial_distance_units": row["scenario"][
                    "target_initial_distance_units"
                ],
                "actual_initial_distance_units": row["qa"][
                    "screen_distance"
                ]["initial_distance_world"],
                "minimum_enemy_screen_height_norm": row["qa"][
                    "screen_distance"
                ]["minimum_height_norm"],
                "minimum_enemy_screen_height_pixels": row["qa"][
                    "screen_distance"
                ]["minimum_height_pixels"],
                "weapon": row["scenario"]["weapon"],
                "enemy_model": row["scenario"]["enemy_model"],
                "enemy_skin": int(row["scenario"]["enemy_skin"]),
                "enemy_color": int(row["scenario"]["enemy_color"]),
                "camera_program": row["scenario"]["camera_program"],
                "primary_motion": row["scenario"][
                    "action_reference_motion_program"
                ]["primary_motion"],
                "motion_labels": row["qa"]["motion"][
                    "realized_labels"
                ],
                "desired_outcome": row["scenario"]["intent_outcome"],
                "actual_outcome": row["qa"]["interaction"][
                    "actual_outcome"
                ],
                "source_formal_episode_id": row["scenario"][
                    "source_formal_episode_id"
                ],
                "speed_units_per_second": row["scenario"][
                    "action_reference_motion_program"
                ]["speed_units_per_second"],
                "counterfactual_episode_id": pair["frozen_episode_id"],
                "pair_qa_path": str(
                    Path(row["episode_path"]) / "pair_qa.json"
                ),
            }
        )
    manifest_path = output_root / "review_manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in release_rows:
            handle.write(canonical_json(row) + "\n")
    summary = {
        "schema_version": "xonotic-stage2-motion-interaction-pilot-summary-v3",
        "output_root": str(output_root),
        "runtime_build": str(capture.build_root()),
        "runtime_source_commit": SOURCE_COMMIT,
        "formal_stage1_stage2_runtime_modified": False,
        "stage1_stage2_protection_precheck_passed": True,
        "stage1_stage2_protection_postcheck_passed": True,
        "active_samples": len(active_rows),
        "counterfactual_samples": len(episodes) - len(active_rows),
        "review_admitted_samples": sum(
            int(row["review_admitted"]) for row in release_rows
        ),
        "desired_outcome_matches": sum(
            int(row["desired_outcome"] == row["actual_outcome"])
            for row in release_rows
        ),
        "primary_motion_distribution": dict(
            sorted(Counter(row["primary_motion"] for row in release_rows).items())
        ),
        "desired_outcome_distribution": dict(
            sorted(Counter(row["desired_outcome"] for row in release_rows).items())
        ),
        "actual_outcome_distribution": dict(
            sorted(Counter(row["actual_outcome"] for row in release_rows).items())
        ),
        "enemy_appearance_distribution": dict(
            sorted(
                Counter(
                    f"{row['enemy_model']}:skin{row['enemy_skin']}"
                    for row in release_rows
                ).items()
            )
        ),
        "weapon_distribution": dict(
            sorted(Counter(row["weapon"] for row in release_rows).items())
        ),
        "map_distribution": dict(
            sorted(Counter(row["map"] for row in release_rows).items())
        ),
        "distance_tier_distribution": dict(
            sorted(
                Counter(row["distance_tier"] for row in release_rows).items()
            )
        ),
        "distance_policy": {
            "source_distance_bin": "near_only",
            "removed_original_bins": [
                "medium",
                "far",
                "very_far",
                "extreme",
            ],
            "tiers": list(DISTANCE_TIERS),
            "tier_assignment_is_prompt_metadata_only": True,
            "minimum_projected_screen_height_norm": (
                MIN_ENEMY_SCREEN_HEIGHT_NORM
            ),
            "minimum_projected_screen_height_pixels_at_720p": (
                MIN_ENEMY_SCREEN_HEIGHT_NORM * 720.0
            ),
            "maximum_target_initial_distance_units": max(
                row["target_initial_distance_units"] for row in release_rows
            ),
        },
        "combination_motion_labels": [
            "player_left_toward",
            "player_right_toward",
            "player_left_away",
            "player_right_away",
        ],
        "fixed_speed_units_per_second": SPEED_UNITS_PER_SECOND,
        "one_v_one_speed_reference": ONE_V_ONE_SPEED_REFERENCE,
        "speed_ratio_to_one_v_one_moving_median": (
            SPEED_UNITS_PER_SECOND
            / ONE_V_ONE_SPEED_REFERENCE[
                "moving_speed_median_units_per_second"
            ]
        ),
        "prompt_schedule": "5 x 0.8 seconds",
        "prompt_rules": {
            "relative_direction_only": True,
            "absolute_screen_region": False,
            "short_medium_long": False,
            "percentage_distance": False,
            "distance_tier_in_text": False,
            "camera_action_in_text": False,
            "interaction_outcome_in_text": True,
        },
        "occlusion_policy": "reject_from_review_admitted_release",
        "visibility_policy": {
            "partial_edge_crop_allowed": True,
            "full_offscreen_rejected": True,
            "occlusion_rejected": True,
            "frustum_tolerance_scale": FRUSTUM_TOLERANCE_SCALE,
        },
        "frustum_tolerance_scale": FRUSTUM_TOLERANCE_SCALE,
        "pairs": pairs,
    }
    write_json(output_root / "SUMMARY.json", summary)
    hashes = artifact_hashes(output_root)
    with (output_root / "SHA256SUMS").open(
        "w", encoding="utf-8"
    ) as handle:
        for relative, digest in hashes.items():
            if relative == "SHA256SUMS":
                continue
            handle.write(f"{digest}  {relative}\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
