                      
"""Prepare the certified-path Stage-1 v5 proposal and formal manifests.

The v5 workflow is deliberately two phase:

1. materialize immutable, non-training player-path prototypes;
2. admit only prototypes with authoritative path certificates, then expand
   them into deterministic semantic variants and 32 formal shards.

No capture-time geometry or action fallback is permitted.
"""

from __future__ import annotations

import argparse
import copy
import heapq
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_manifests as v4              
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              
import xonotic_motion_distance_pilot as motion              
import xonotic_stage1_review as review              
import xonotic_stage1_routes as routes              


ROOT = capture.ROOT
                                                                             
                                                    
EXPECTED_SOURCE_COMMIT = "b40e26fd4e33b18b2002bf24beb6a78cef5fac96"
RUNTIME_SOURCE_COMMIT = "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
CERT_ROOT = ROOT / "manifests/stage1_foundation_v5_certification"
ROUTE_INDEX_PATH = CERT_ROOT / "ROUTE_CERTIFICATION_INDEX.jsonl"
ROUTE_AUDIT_PATH = CERT_ROOT / "ROUTE_CERTIFICATION_AUDIT.json"
PRIMARY_PROTOTYPES_PATH = CERT_ROOT / "path_prototypes_primary.jsonl"
REPLENISHMENT_PROTOTYPES_PATH = (
    CERT_ROOT / "path_prototypes_replenishment.jsonl"
)
PROTOTYPE_METADATA_PATH = CERT_ROOT / "PROTOTYPE_METADATA.json"
CERTIFICATION_SPARE_PROTOTYPES_PATH = (
    CERT_ROOT / "path_prototypes_certification_spare.jsonl"
)
CERTIFICATION_SPARE_METADATA_PATH = (
    CERT_ROOT / "CERTIFICATION_SPARE_PROTOTYPE_METADATA.json"
)
TARGETED_HIGH_PROTOTYPES_PATH = (
    CERT_ROOT / "path_prototypes_targeted_high_motion.jsonl"
)
TARGETED_COLLISION_PROTOTYPES_PATH = (
    CERT_ROOT / "path_prototypes_targeted_visible_collision.jsonl"
)
TARGETED_METADATA_PATH = CERT_ROOT / "TARGETED_PROTOTYPE_METADATA.json"
FAST_TRAVERSAL_PROTOTYPES_PATH = (
    CERT_ROOT / "path_prototypes_targeted_fast_traversal.jsonl"
)
FAST_TRAVERSAL_METADATA_PATH = (
    CERT_ROOT / "FAST_TRAVERSAL_PROTOTYPE_METADATA.json"
)
FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH = (
    CERT_ROOT / "path_prototypes_targeted_fast_traversal_tight.jsonl"
)
FAST_TRAVERSAL_TIGHT_METADATA_PATH = (
    CERT_ROOT / "FAST_TRAVERSAL_TIGHT_PROTOTYPE_METADATA.json"
)
FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH = (
    CERT_ROOT
    / "path_prototypes_targeted_fast_traversal_world_balanced.jsonl"
)
FAST_TRAVERSAL_WORLD_METADATA_PATH = (
    CERT_ROOT / "FAST_TRAVERSAL_WORLD_PROTOTYPE_METADATA.json"
)
PATH_CERTIFICATE_ROOT = ROOT / "stage1_path_certification_v5"
PATH_CERTIFICATE_INDEX = (
    PATH_CERTIFICATE_ROOT / "manifests/certificates.jsonl"
)
PATH_RUNTIME_COMPATIBILITY_AUDIT = (
    PATH_CERTIFICATE_ROOT
    / "compatibility"
    / (
        f"{EXPECTED_SOURCE_COMMIT[:12]}_to_"
        f"{RUNTIME_SOURCE_COMMIT[:12]}"
    )
    / "AUDIT.json"
)
REPLENISHMENT_FEASIBILITY_AUDIT = (
    PATH_CERTIFICATE_ROOT
    / "feasibility"
    / "REPLENISHMENT_CONSTRAINT_GROUP_AUDIT.json"
)
SEMANTIC_WEIGHT_FEASIBILITY_AUDIT = (
    PATH_CERTIFICATE_ROOT
    / "feasibility"
    / "SEMANTIC_WEIGHT_CONSTRAINT_AUDIT.json"
)
FORMAL_ROOT = ROOT / "manifests/stage1_foundation_v5_formal"
FORMAL_INPUT_PATH = FORMAL_ROOT / "input.jsonl"
FORMAL_REPLENISHMENT_PATH = FORMAL_ROOT / "replenishment.jsonl"
FORMAL_METADATA_PATH = FORMAL_ROOT / "MANIFEST_METADATA.json"
FORMAL_AUDIT_PATH = FORMAL_ROOT / "MANIFEST_AUDIT.json"
FORMAL_RUNTIME_LOCK_PATH = FORMAL_ROOT / "RUNTIME_CODE_LOCK.sha256"
FORMAL_SHARD_ROOT = FORMAL_ROOT / "shards/primary"
FORMAL_REPLENISHMENT_SHARD_ROOT = (
    FORMAL_ROOT / "shards/replenishment"
)
PRIMARY_PROTOTYPE_SCALE = 10
REPLENISHMENT_PROTOTYPE_SCALE = 50
PRIMARY_PROTOTYPE_COUNT = 6_000
REPLENISHMENT_PROTOTYPE_COUNT = 1_200
CERTIFICATION_SPARE_PROTOTYPE_COUNT = 1_200
SEMANTIC_VARIANTS_PER_PROTOTYPE = 10
PROTOTYPE_SCHEDULE_SEED_OFFSETS = {
    "primary": 0,
    "replenishment": 10,
}
CERTIFICATION_SPARE_SEED_OFFSET = 20
ROUTE_PLAN_FIRST = 10_000
ROUTE_PLAN_COUNT = 4_000
SHARD_COUNT = 32
PROTOTYPE_SEED = 15_500_000
TARGETED_HIGH_COUNT = 8_000
TARGETED_COLLISION_COUNT = 256
FAST_TRAVERSAL_COUNT = 4_096
FAST_TRAVERSAL_CONTROL_COUNT = 1_536
FAST_TRAVERSAL_TIGHT_COUNT = 4_096
FAST_TRAVERSAL_WORLD_COUNT = 4_096
ROUTE_REPLAY_PLAYER_ENEMY_CLEARANCE_UNITS = 96.0
RUNTIME_LOCK_RELATIVE_PATHS = (
    "XONOTIC_DATA_SPEC_V2.md",
    "STAGE1_PRODUCTION_PREFLIGHT_POLICY.md",
    "STAGE1_AUDIO_EXPECTATION_AND_GANG_RECOVERY_POLICY.md",
    "assets/OFFICIAL_ASSET_ALLOWLIST.json",
    "configs/OFFICIAL_MAP_ANCHORS.json",
    "configs/OFFICIAL_V2_CONTENT_CATALOG.json",
    "configs/PILOT_SCHEMA.json",
    "configs/capture_client.cfg",
    "configs/capture_server.cfg",
    "scripts/cci_node_bootstrap.sh",
    "scripts/cci_run.sh",
    "scripts/certify_stage1_v5_paths.py",
    "scripts/certify_stage1_v5_routes.py",
    "scripts/audit_stage1_v5_replenishment_feasibility.py",
    "scripts/audit_stage1_v5_runtime_compatibility.py",
    "scripts/audit_stage1_v5_semantic_weight_feasibility.py",
    "scripts/audit_stage1_audio_expectation_revision.py",
    "scripts/finalize_v2_pilot.py",
    "scripts/prepare_stage1_manifests.py",
    "scripts/prepare_stage1_v5_manifests.py",
    "scripts/revise_stage1_formal_runtime.py",
    "scripts/run_capture_manifest_shard.py",
    "scripts/run_stage1_32x1_worker.sh",
    "scripts/run_stage1_manifest_shard.py",
    "scripts/stage1_32x1_status.py",
    "scripts/xonotic_capture.py",
    "scripts/xonotic_capture_v2.py",
    "scripts/xonotic_motion_distance_pilot.py",
    "scripts/xonotic_stage1_review.py",
    "scripts/xonotic_stage1_reusable.py",
    "scripts/xonotic_stage1_routes.py",
)
PHYSICAL_MARGINAL_BASELINE: dict[str, dict[Any, int]] = {
    "locomotion_direction": {
        "right": 4_445,
        "forward": 4_447,
        "backward_left": 4_442,
        "forward_right": 4_442,
        "forward_left": 4_445,
        "left": 4_445,
        "backward_right": 4_442,
        "backward": 4_447,
        "route_follow": 20_000,
        "idle": 4_445,
    },
    "movement_profile": {
        "stop_and_go": 4_442,
        "late_onset_hold": 4_445,
        "full_clip_sustained": 8_892,
        "middle_window": 4_445,
        "two_pulse": 4_445,
        "early_hold_release": 4_447,
        "eased_variable_rate": 4_442,
        "route_calibrated_visible": 20_000,
        "reversal": 4_442,
    },
    "view_direction": {
        "pitch_up": 5_846,
        "yaw_left_pitch_down": 6_681,
        "yaw_right": 10_343,
        "yaw_right_pitch_up": 6_678,
        "yaw_left": 10_348,
        "yaw_right_pitch_down": 6_674,
        "yaw_left_pitch_up": 6_683,
        "pitch_down": 5_842,
        "stationary": 905,
    },
    "view_profile": {
        "reversal": 7_498,
        "middle_window": 7_502,
        "two_pulse": 7_498,
        "early_hold_release": 7_502,
        "late_onset_hold": 7_502,
        "full_clip_sustained": 7_502,
        "eased_variable_rate": 7_498,
        "stop_and_go": 7_498,
    },
    "jump": {
        False: 49_500,
        True: 10_500,
    },
}
PHYSICAL_MARGINAL_TOLERANCE = 0.15
REALIZED_MARGINAL_TOLERANCE = 0.15
PATH_GE1000_MIN_FRACTION = 0.25
PATH_GE2000_MIN_FRACTION = 0.09
JOINT_NET512_YAW90_MIN_FRACTION = 0.10
FORMAL_SEMANTIC_MARGINAL_TOLERANCE = 0.20
FORMAL_SEMANTIC_PLANNED_TOLERANCE = 0.15
FORMAL_SEMANTIC_PATH_GE1000_MIN_FRACTION = 0.245
FORMAL_SEMANTIC_PATH_GE2000_MIN_FRACTION = 0.09
FORMAL_SEMANTIC_JOINT_MIN_FRACTION = 0.09
FORMAL_SEMANTIC_VARIANTS_MIN = 9
FORMAL_SEMANTIC_VARIANTS_MAX = 13
FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX = 0.50
REPLENISHMENT_FIXED_CELL_PATH_COUNTS: dict[
    tuple[str, str], int
] = {
    ("foundation_no_enemy", "node_atomic"): 393,
    ("foundation_enemy_distractor", "node_atomic"): 127,
    ("foundation_no_enemy", "route_action"): 300,
    ("foundation_enemy_distractor", "route_action"): 100,
    ("foundation_no_enemy", "high_motion_special"): 127,
    ("foundation_enemy_distractor", "high_motion_special"): 33,
    ("foundation_no_enemy", "weapon_environment"): 90,
    ("foundation_enemy_distractor", "weapon_environment"): 30,
}
REPLENISHMENT_FIXED_PLANNED_TARGETS: dict[
    str, dict[str, int]
] = {
    "target_relation": {
        "offscreen_or_occluded": 72,
        "visible_far": 87,
        "near_crosshair": 58,
        "brief_center_pass": 44,
        "center_linger": 20,
        "nearly_continuous_center": 9,
    },
    "distance": {
        "close": 40,
        "near": 96,
        "medium": 94,
        "far": 36,
        "very_far": 18,
        "extreme": 6,
    },
    "enemy_policy": {
        "idle": 58,
        "lateral_patrol": 87,
        "approach_retreat": 73,
        "stop_and_go": 72,
    },
}
REPLENISHMENT_FIXED_NET_TARGETS = {
    "lt64": 180,
    "64_256": 1,
    "256_512": 222,
    "512_1024": 594,
    "gt1024": 203,
}
REPLENISHMENT_FIXED_PHYSICAL_TARGETS: dict[
    str, dict[Any, int]
] = {
    "locomotion_direction": {
        "right": 89,
        "forward": 89,
        "backward_left": 89,
        "forward_right": 89,
        "forward_left": 89,
        "left": 89,
        "backward_right": 89,
        "backward": 89,
        "route_follow": 400,
        "idle": 88,
    },
    "movement_profile": {
        "stop_and_go": 53,
        "late_onset_hold": 53,
        "full_clip_sustained": 382,
        "middle_window": 89,
        "two_pulse": 53,
        "early_hold_release": 74,
        "eased_variable_rate": 48,
        "route_calibrated_visible": 400,
        "reversal": 48,
    },
    "view_direction": {
        "pitch_up": 70,
        "yaw_left_pitch_down": 130,
        "yaw_right": 147,
        "yaw_right_pitch_up": 329,
        "yaw_left": 175,
        "yaw_right_pitch_down": 133,
        "yaw_left_pitch_up": 122,
        "pitch_down": 76,
        "stationary": 18,
    },
    "view_profile": {
        "reversal": 112,
        "middle_window": 117,
        "two_pulse": 117,
        "early_hold_release": 380,
        "late_onset_hold": 108,
        "full_clip_sustained": 97,
        "eased_variable_rate": 119,
        "stop_and_go": 150,
    },
    "jump": {
        False: 995,
        True: 205,
    },
}
REPLENISHMENT_PLANNED_TOLERANCE = 0.05
if (
    sum(REPLENISHMENT_FIXED_CELL_PATH_COUNTS.values())
    != REPLENISHMENT_PROTOTYPE_COUNT
    or any(
        sum(targets.values()) != 290
        for targets in REPLENISHMENT_FIXED_PLANNED_TARGETS.values()
    )
    or sum(REPLENISHMENT_FIXED_NET_TARGETS.values())
    != REPLENISHMENT_PROTOTYPE_COUNT
    or set(REPLENISHMENT_FIXED_PHYSICAL_TARGETS)
    != set(PHYSICAL_MARGINAL_BASELINE)
    or any(
        set(REPLENISHMENT_FIXED_PHYSICAL_TARGETS[field])
        != set(PHYSICAL_MARGINAL_BASELINE[field])
        or sum(REPLENISHMENT_FIXED_PHYSICAL_TARGETS[field].values())
        != REPLENISHMENT_PROTOTYPE_COUNT
        for field in PHYSICAL_MARGINAL_BASELINE
    )
):
    raise AssertionError("invalid fixed v5 replenishment reserve policy")
if any(
    sum(counts.values()) != 60_000
    for counts in PHYSICAL_MARGINAL_BASELINE.values()
):
    raise AssertionError("Stage-1 physical marginal baseline must sum to 60k")

                                                                        
                                                                            
PRIMARY_ACTION_CELL_COUNTS: dict[
    tuple[str, str], dict[str, int]
] = {
    ("foundation_no_enemy", "node_atomic"): {
        "environmental_primary": 2_120,
        "reload": 1_070,
    },
    ("foundation_no_enemy", "route_action"): {
        "environmental_primary": 1_740,
        "reload": 860,
    },
    ("foundation_no_enemy", "high_motion_special"): {
        "environmental_primary": 640,
        "reload": 320,
    },
    ("foundation_no_enemy", "weapon_environment"): {
        "environmental_primary": 3_000,
        "reload": 1_500,
    },
    ("foundation_enemy_distractor", "node_atomic"): {
        "environmental_primary": 770,
        "reload": 340,
    },
    ("foundation_enemy_distractor", "route_action"): {
        "environmental_primary": 510,
        "reload": 320,
    },
    (
        "foundation_enemy_distractor",
        "high_motion_special",
    ): {
        "environmental_primary": 220,
        "reload": 90,
    },
    (
        "foundation_enemy_distractor",
        "weapon_environment",
    ): {
        "environmental_primary": 1_000,
        "reload": 450,
    },
}
REPLENISHMENT_FIXED_ACTION_CELL_COUNTS: dict[
    tuple[str, str], dict[str, int]
] = {
    ("foundation_no_enemy", "node_atomic"): {
        "environmental_primary": 427,
        "reload": 216,
        "none": 3_287,
    },
    ("foundation_enemy_distractor", "node_atomic"): {
        "environmental_primary": 150,
        "reload": 66,
        "none": 1_054,
    },
    ("foundation_no_enemy", "route_action"): {
        "environmental_primary": 348,
        "reload": 172,
        "none": 2_480,
    },
    ("foundation_enemy_distractor", "route_action"): {
        "environmental_primary": 102,
        "reload": 64,
        "none": 834,
    },
    ("foundation_no_enemy", "high_motion_special"): {
        "environmental_primary": 135,
        "reload": 68,
        "none": 1_067,
    },
    ("foundation_enemy_distractor", "high_motion_special"): {
        "environmental_primary": 36,
        "reload": 15,
        "none": 279,
    },
    ("foundation_no_enemy", "weapon_environment"): {
        "environmental_primary": 600,
        "reload": 300,
        "none": 0,
    },
    ("foundation_enemy_distractor", "weapon_environment"): {
        "environmental_primary": 180,
        "reload": 100,
        "none": 20,
    },
}
if (
    set(REPLENISHMENT_FIXED_ACTION_CELL_COUNTS)
    != set(REPLENISHMENT_FIXED_CELL_PATH_COUNTS)
    or any(
        sum(REPLENISHMENT_FIXED_ACTION_CELL_COUNTS[cell].values())
        != (
            REPLENISHMENT_FIXED_CELL_PATH_COUNTS[cell]
            * SEMANTIC_VARIANTS_PER_PROTOTYPE
        )
        for cell in REPLENISHMENT_FIXED_CELL_PATH_COUNTS
    )
):
    raise AssertionError("invalid fixed replenishment action-cell policy")
SAFE_PRIMARY_FIRE_RELATIONS = frozenset(
    {
        "offscreen_or_occluded",
        "visible_far",
        "near_crosshair",
    }
)


def semantic_action_cell_targets(
    cell: tuple[str, str],
    target_rows: int,
    *,
    replenishment: bool = False,
) -> dict[str, int]:
    """Scale the fixed v2 action mix to an admitted path-cell size.

    The certified replenishment reserve intentionally has a slightly
    different no-enemy/enemy cell mix from the primary wave.  Preserve the
    declared action proportions inside each cell instead of silently
    pretending that the residual pool has the original cell cardinality.
    Integer half-up rounding is deterministic; `none` absorbs the remainder.
    """

    if replenishment:
        expected_rows = (
            REPLENISHMENT_FIXED_CELL_PATH_COUNTS[cell]
            * SEMANTIC_VARIANTS_PER_PROTOTYPE
        )
        if target_rows != expected_rows:
            raise AssertionError((cell, target_rows, expected_rows))
        return dict(REPLENISHMENT_FIXED_ACTION_CELL_COUNTS[cell])

    role, bucket = cell
    nominal_rows = v4.BUCKET_ROLE_COUNTS[bucket][role]
    nominal = PRIMARY_ACTION_CELL_COUNTS[cell]

    def scaled(mode: str) -> int:
        numerator = target_rows * nominal[mode]
        return (numerator + nominal_rows // 2) // nominal_rows

    primary = scaled("environmental_primary")
    reload_count = scaled("reload")
    none = target_rows - primary - reload_count
    if min(primary, reload_count, none) < 0:
        raise AssertionError((cell, target_rows, primary, reload_count))
    return {
        "environmental_primary": primary,
        "reload": reload_count,
        "none": none,
    }


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(
        path,
        json.dumps(
            value, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_v5_manifest_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def created_utc_for(path: Path) -> str:
    """Keep immutable manifest metadata byte-identical across resumptions."""
    if path.is_file():
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get(
                "created_utc"
            )
        except (OSError, json.JSONDecodeError):
            value = None
        if isinstance(value, str) and value:
            return value
    return capture.utc_now()


def runtime_code_lock_text() -> str:
    rows: list[str] = []
    for relative in RUNTIME_LOCK_RELATIVE_PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise capture.CaptureFailure(
                "v5_runtime_code_artifact_missing", relative
            )
        rows.append(f"{capture.sha256_file(path)}  {relative}\n")
    return "".join(rows)


def angle_wrap(value: float) -> float:
    return (float(value) + 180.0) % 360.0 - 180.0


def live_motion_metrics(states: pd.DataFrame) -> dict[str, Any]:
    output = states[
        (states["server_tick"] >= capture.WARMUP_TICKS)
        & (states["server_tick"] < capture.TOTAL_TICKS)
    ].sort_values("server_tick")
    if len(output) != capture.OUTPUT_TICKS:
        raise capture.CaptureFailure(
            "v5_route_state_count",
            f"actual={len(output)} expected={capture.OUTPUT_TICKS}",
        )
    positions = np.asarray(
        output["post.origin"].tolist(), dtype=np.float64
    )
    velocities = np.asarray(
        output["post.velocity"].tolist(), dtype=np.float64
    )
    yaw = np.degrees(
        np.unwrap(
            np.radians(
                pd.to_numeric(
                    output["applied_action.yaw"], errors="raise"
                ).to_numpy(dtype=np.float64)
            )
        )
    )
    pitch = pd.to_numeric(
        output["applied_action.pitch"], errors="raise"
    ).to_numpy(dtype=np.float64)
    yaw_deltas = np.diff(yaw)
    pitch_deltas = np.diff(pitch)
    steps_3d = np.linalg.norm(np.diff(positions, axis=0), axis=1)
    steps_xy = np.linalg.norm(
        np.diff(positions[:, :2], axis=0), axis=1
    )
    from_start = np.linalg.norm(positions - positions[0], axis=1)
    speeds = np.linalg.norm(velocities, axis=1)
    result = {
        "path_length_3d": float(steps_3d.sum()),
        "path_length_xy": float(steps_xy.sum()),
        "net_displacement_3d": float(
            np.linalg.norm(positions[-1] - positions[0])
        ),
        "maximum_displacement_from_start": float(from_start.max()),
        "vertical_range": float(np.ptp(positions[:, 2])),
        "speed_p95": float(np.percentile(speeds, 95)),
        "speed_max": float(speeds.max()),
        "yaw_total_variation_deg": float(np.abs(yaw_deltas).sum()),
        "yaw_range_deg": float(np.ptp(yaw)),
        "yaw_net_change_deg": float(abs(yaw[-1] - yaw[0])),
        "pitch_total_variation_deg": float(
            np.abs(pitch_deltas).sum()
        ),
        "pitch_range_deg": float(np.ptp(pitch)),
        "health_min": float(
            pd.to_numeric(
                output["post.health"], errors="raise"
            ).min()
        ),
    }
    result.update(
        {
            "net_displacement_bin": motion.displacement_bin(
                result["net_displacement_3d"]
            ),
            "yaw_range_bin": motion.yaw_range_bin(
                result["yaw_range_deg"]
            ),
            "pitch_range_bin": motion.pitch_range_bin(
                result["pitch_range_deg"]
            ),
        }
    )
    return result


def route_plan_ids() -> list[str]:
    return [
        f"s1route_{index:05d}"
        for index in range(
            ROUTE_PLAN_FIRST, ROUTE_PLAN_FIRST + ROUTE_PLAN_COUNT
        )
    ]


def calibration_record(route_id: str) -> dict[str, Any] | None:
    path = routes.CALIBRATION_ROOT / route_id / "CALIBRATION.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def route_status(route_id: str) -> str:
    record = calibration_record(route_id)
    if record is None:
        return "pending"
    if record.get("source_commit") != EXPECTED_SOURCE_COMMIT:
        return "stale"
    return (
        "passed"
        if record.get("metrics", {}).get("passed") is True
        else "failed"
    )


def route_plan_with_locks(route_id: str) -> dict[str, Any]:
    path, plan = routes.load_plan(route_id)
    result = copy.deepcopy(plan)
    result.update(
        {
            "route_plan_path": str(path.relative_to(ROOT)),
            "route_plan_sha256": capture.sha256_file(path),
        }
    )
    return result


def route_support_audit_checks(
    *,
    route_ids: list[str],
    status: Counter[str],
    rows: list[dict[str, Any]],
    planned_maps: set[str],
) -> dict[str, bool]:
    """Audit the boundary between route calibration and support admission.

    A route-calibration pass proves that the immutable controller can follow
    its declared route. Collision/contact telemetry is evaluated afterwards
    and may exclude that route from the robust support pool. A calibration
    pass that is correctly marked ineligible must not invalidate the whole
    route library; prototype selection is allowed to use only robust rows.
    """
    robust_rows = [
        row for row in rows if row["robust_support_eligible"]
    ]
    zero_jump_robust_rows = [
        row for row in robust_rows if int(row["base_jump_ticks"]) == 0
    ]
    robust_maps = {str(row["map"]) for row in robust_rows}
    zero_jump_robust_maps = {
        str(row["map"]) for row in zero_jump_robust_rows
    }
    return {
        "all_routes_terminal": (
            status["pending"] == 0 and status["stale"] == 0
        ),
        "route_index_matches_calibration_passes": (
            len(rows) == status["passed"]
        ),
        "route_library_complete": len(route_ids) == ROUTE_PLAN_COUNT,
        "robust_support_nonempty": bool(robust_rows),
        "robust_support_map_coverage": planned_maps <= robust_maps,
        "zero_jump_robust_support_nonempty": bool(
            zero_jump_robust_rows
        ),
        "zero_jump_robust_support_map_coverage": (
            planned_maps <= zero_jump_robust_maps
        ),
        "all_robust_support_collision_clear": all(
            row["movement_blockage"]["collision_policy_passed"]
            is True
            for row in robust_rows
        ),
        "all_robust_support_contact_free": all(
            int(row["contact_probe_hit_ticks"]) == 0
            for row in robust_rows
        ),
        "all_robust_support_has_contact_telemetry": all(
            row["movement_blockage"]["contact_telemetry_present"]
            is True
            for row in robust_rows
        ),
        "all_robust_support_alive": all(
            float(row["motion"]["health_min"]) > 0
            for row in robust_rows
        ),
        "all_actions_hash_locked": all(
            row["action_sha256_verified"] for row in rows
        ),
    }


def audit_routes() -> dict[str, Any]:
    ids = route_plan_ids()
    status = Counter(route_status(route_id) for route_id in ids)
    planned_maps = {
        str(routes.load_plan(route_id)[1]["map"]) for route_id in ids
    }
    rows: list[dict[str, Any]] = []
    for route_id in ids:
        if route_status(route_id) != "passed":
            continue
        record = calibration_record(route_id)
        if record is None:
            raise AssertionError(route_id)
        plan = route_plan_with_locks(route_id)
        state_path = capture.locked_root_artifact(
            record["calibration_states_path"],
            record["calibration_states_sha256"],
            "v5_route_calibration_states",
        )
        action_path = capture.locked_root_artifact(
            record["frozen_actions_path"],
            record["frozen_actions_sha256"],
            "v5_route_frozen_actions",
        )
        states = pd.read_parquet(state_path)
        blockage = capture.movement_blockage_metrics(
            states, scenario=record["scenario"]
        )
        output = states[
            (states["server_tick"] >= capture.WARMUP_TICKS)
            & (states["server_tick"] < capture.TOTAL_TICKS)
        ]
        contact_hits = int(
            pd.to_numeric(
                output["movement_contact.hit"], errors="coerce"
            )
            .fillna(0)
            .sum()
        )
        jump_ticks = int(
            pd.to_numeric(
                output["applied_action.jump"], errors="coerce"
            )
            .fillna(0)
            .astype(bool)
            .sum()
        )
        metrics = live_motion_metrics(states)
        robust = bool(
            blockage["collision_policy_passed"]
            and blockage["contact_telemetry_present"]
            and contact_hits == 0
            and metrics["health_min"] > 0
        )
        rows.append(
            {
                "schema_version": (
                    "xonotic-stage1-v5-route-certificate-v1"
                ),
                "route_id": route_id,
                "map": plan["map"],
                "gametype": plan["gametype"],
                "map_region_id": plan["map_region_id"],
                "route_group_id": plan["route_group_id"],
                "route_length": float(plan["route_length"]),
                "route_plan_path": plan["route_plan_path"],
                "route_plan_sha256": plan["route_plan_sha256"],
                "route_csv_path": plan["route_csv_path"],
                "route_csv_sha256": plan["route_csv_sha256"],
                "frozen_actions_path": record["frozen_actions_path"],
                "frozen_actions_sha256": record[
                    "frozen_actions_sha256"
                ],
                "calibration_states_path": record[
                    "calibration_states_path"
                ],
                "calibration_states_sha256": record[
                    "calibration_states_sha256"
                ],
                "source_commit": EXPECTED_SOURCE_COMMIT,
                "route_qa": record["metrics"],
                "movement_blockage": blockage,
                "motion": metrics,
                "contact_probe_hit_ticks": contact_hits,
                "base_jump_ticks": jump_ticks,
                "robust_support_eligible": robust,
                "compatible_enemy_pairs": plan.get(
                    "compatible_enemy_pairs", []
                ),
                "action_sha256_verified": capture.sha256_file(
                    action_path
                )
                == record["frozen_actions_sha256"],
            }
        )
    atomic_text(ROUTE_INDEX_PATH, canonical_lines(rows))
    by_map = Counter(row["map"] for row in rows)
    robust_by_map = Counter(
        row["map"] for row in rows if row["robust_support_eligible"]
    )
    support_exclusions = {
        "collision_policy_failed": sum(
            row["movement_blockage"]["collision_policy_passed"]
            is not True
            for row in rows
        ),
        "contact_hits_positive": sum(
            int(row["contact_probe_hit_ticks"]) > 0 for row in rows
        ),
        "contact_telemetry_missing": sum(
            row["movement_blockage"]["contact_telemetry_present"]
            is not True
            for row in rows
        ),
        "health_nonpositive": sum(
            float(row["motion"]["health_min"]) <= 0 for row in rows
        ),
    }
    report = {
        "schema_version": "xonotic-stage1-v5-route-audit-v1",
        "created_utc": created_utc_for(ROUTE_AUDIT_PATH),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "route_count": len(ids),
        "status": dict(sorted(status.items())),
        "passed_rows": len(rows),
        "robust_support_rows": sum(
            row["robust_support_eligible"] for row in rows
        ),
        "zero_jump_robust_support_rows": sum(
            row["robust_support_eligible"]
            and int(row["base_jump_ticks"]) == 0
            for row in rows
        ),
        "maps": dict(sorted(by_map.items())),
        "robust_maps": dict(sorted(robust_by_map.items())),
        "support_exclusions": support_exclusions,
        "path_ge1000": sum(
            row["motion"]["path_length_3d"] >= 1_000 for row in rows
        ),
        "path_ge2000": sum(
            row["motion"]["path_length_3d"] >= 2_000 for row in rows
        ),
        "checks": route_support_audit_checks(
            route_ids=ids,
            status=status,
            rows=rows,
            planned_maps=planned_maps,
        ),
        "route_index_path": str(ROUTE_INDEX_PATH.relative_to(ROOT)),
        "route_index_sha256": capture.sha256_file(ROUTE_INDEX_PATH),
    }
    report["passed"] = all(report["checks"].values())
    atomic_json(ROUTE_AUDIT_PATH, report)
    return report


def load_route_index(
    *, require_complete: bool = True
) -> list[dict[str, Any]]:
    if not ROUTE_INDEX_PATH.is_file() or not ROUTE_AUDIT_PATH.is_file():
        raise capture.CaptureFailure(
            "v5_route_audit_missing", str(ROUTE_AUDIT_PATH)
        )
    audit = json.loads(ROUTE_AUDIT_PATH.read_text(encoding="utf-8"))
    if require_complete and not audit.get("passed"):
        raise capture.CaptureFailure(
            "v5_route_audit_incomplete",
            capture.canonical_json(audit.get("status", {})),
        )
    return capture.load_jsonl(ROUTE_INDEX_PATH)


@lru_cache(maxsize=None)
def cached_support_plan(route_id: str) -> dict[str, Any]:
    """Load each immutable route plan once during prototype materialization."""
    _, plan = routes.load_plan(route_id)
    return plan


def support_plan_from_certificate(
    certificate: dict[str, Any]
) -> dict[str, Any]:
    plan = cached_support_plan(str(certificate["route_id"]))
    return {
        **copy.deepcopy(plan),
        "route_plan_path": certificate["route_plan_path"],
        "route_plan_sha256": certificate["route_plan_sha256"],
    }


def locomotion_offset(direction: str) -> float:
    forward, strafe = capture.STAGE1_LOCOMOTION_VECTORS[direction]
    return math.degrees(math.atan2(strafe, forward))


def command_world_heading(camera_yaw: float, direction: str) -> float:
    """Return the DarkPlaces XY usercmd heading in world coordinates.

    Positive sidemove is the clockwise camera-right vector, so the command
    heading is camera yaw minus atan2(strafe, forward).
    """
    return angle_wrap(float(camera_yaw) - locomotion_offset(direction))


def route_support_eligible(certificate: dict[str, Any]) -> bool:
    """Only contact-free routes without hidden jump input are scaffolds."""
    return bool(
        certificate["robust_support_eligible"]
        and int(certificate["base_jump_ticks"]) == 0
    )


@lru_cache(maxsize=None)
def route_replay_static_clearance_xy(
    route_id: str,
    calibration_states_path: str,
    calibration_states_sha256: str,
    enemy_origin: tuple[float, float, float],
) -> float:
    """Return the locked calibration path's closest XY approach to an anchor."""
    del route_id                                                      
    state_path = capture.locked_root_artifact(
        calibration_states_path,
        calibration_states_sha256,
        "v5_route_replay_clearance_states",
    )
    states = pd.read_parquet(
        state_path, columns=["server_tick", "post.origin"]
    )
    output = states[
        (states["server_tick"] >= capture.WARMUP_TICKS)
        & (states["server_tick"] < capture.TOTAL_TICKS)
    ]
    if len(output) != capture.OUTPUT_TICKS:
        raise capture.CaptureFailure(
            "v5_route_replay_clearance_state_ticks",
            f"path={state_path} rows={len(output)}",
        )
    player_origins = np.stack(
        output["post.origin"].to_numpy()
    ).astype(np.float64)
    anchor = np.asarray(enemy_origin, dtype=np.float64)
    return float(
        np.linalg.norm(
            player_origins[:, :2] - anchor[None, :2], axis=1
        ).min()
    )


def route_replay_clearance_metrics(
    certificate: dict[str, Any],
    pair: dict[str, Any],
    motion_amplitude_units: float,
) -> dict[str, Any]:
    static_minimum = route_replay_static_clearance_xy(
        str(certificate["route_id"]),
        str(certificate["calibration_states_path"]),
        str(certificate["calibration_states_sha256"]),
        tuple(float(value) for value in pair["enemy_origin"]),
    )
    amplitude = max(0.0, float(motion_amplitude_units))
    conservative_minimum = static_minimum - amplitude
    return {
        "schema_version": (
            "xonotic-stage1-v5-route-replay-clearance-v1"
        ),
        "calibration_states_sha256": certificate[
            "calibration_states_sha256"
        ],
        "static_minimum_xy_units": round(static_minimum, 6),
        "enemy_motion_amplitude_units": round(amplitude, 6),
        "conservative_minimum_xy_units": round(
            conservative_minimum, 6
        ),
        "required_minimum_xy_units": (
            ROUTE_REPLAY_PLAYER_ENEMY_CLEARANCE_UNITS
        ),
        "passed": (
            conservative_minimum
            >= ROUTE_REPLAY_PLAYER_ENEMY_CLEARANCE_UNITS
        ),
    }


def action_arity(design: dict[str, Any]) -> str:
    active = int(design["locomotion_direction"] != "idle")
    active += int(design["view_direction"] != "stationary")
    active += int(bool(design.get("jump")))
    return {
        0: "idle",
        1: "atomic",
        2: "pairwise",
        3: "three_way",
    }[active]


def select_support(
    row: dict[str, Any],
    route_rows: list[dict[str, Any]],
    safe_enemy_paths: set[tuple[str, str]],
    reuse: Counter[str],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    design = row["action_design"]
    wants_jump = bool(design.get("jump"))
    enemy = bool(row["enemy_present"])
    policy = (
        str(row["enemy_policy"]["name"]) if enemy else None
    )
    distance_bin = row["scheduler_targets"].get("distance_bin")
    candidates: list[
        tuple[tuple[Any, ...], dict[str, Any], list[dict[str, Any]]]
    ] = []
    for certificate in route_rows:
        if not route_support_eligible(certificate):
            continue
        certificate_start = np.asarray(
            cached_support_plan(str(certificate["route_id"]))[
                "nodes"
            ][0]["origin"],
            dtype=np.float64,
        )
        pairs: list[dict[str, Any]] = []
        if enemy:
            for pair in certificate["compatible_enemy_pairs"]:
                if pair["distance_bin"] != distance_bin:
                    continue
                if not np.allclose(
                    np.asarray(
                        pair["player_origin"], dtype=np.float64
                    ),
                    certificate_start,
                    atol=0.2,
                    rtol=0.0,
                ):
                    continue
                key = v4.enemy_pair_key(pair)
                if policy != "idle" and (key, policy) not in safe_enemy_paths:
                    continue
                pairs.append(pair)
            if not pairs:
                continue
        score = (
            certificate["map"] != row["map"],
            reuse[str(certificate["route_id"])],
            -float(certificate["route_length"])
            if row["primary_bucket"] == "high_motion_special"
            else float(certificate["route_length"]),
            hashlib.sha256(
                (
                    f"{row['episode_id']}:{certificate['route_id']}"
                ).encode()
            ).hexdigest(),
        )
        candidates.append((score, certificate, pairs))
    if not candidates:
        raise capture.CaptureFailure(
            "v5_support_route_capacity",
            capture.canonical_json(
                {
                    "episode_id": row["episode_id"],
                    "enemy": enemy,
                    "policy": policy,
                    "distance": distance_bin,
                    "jump": wants_jump,
                }
            ),
        )
    _, certificate, pairs = min(candidates, key=lambda item: item[0])
    reuse[str(certificate["route_id"])] += 1
    selected_pair = None
    if pairs:
        desired_relation_yaw = v4.relation_offset(
            row["scheduler_targets"]["target_relation"]
        )
        plan = support_plan_from_certificate(certificate)
        base_yaw = round(
            float(
                (
                    14_000_000
                    + int(str(plan["route_id"]).split("_")[-1])
                )
                * 37
                % 360
            )
            - 180.0,
            6,
        )
        camera_yaw = base_yaw + locomotion_offset(
            design["locomotion_direction"]
        )

        def relation_error(pair: dict[str, Any]) -> tuple[float, str]:
            bearing = review.direction_yaw(
                pair["player_origin"], pair["enemy_origin"]
            )
            error = abs(
                angle_wrap(
                    camera_yaw - (bearing + desired_relation_yaw)
                )
            )
            tie = hashlib.sha256(
                (
                    f"{row['episode_id']}:{v4.enemy_pair_key(pair)}"
                ).encode()
            ).hexdigest()
            return error, tie

        selected_pair = copy.deepcopy(
            min(pairs, key=relation_error)
        )
    return certificate, selected_pair


def select_route_replay_support(
    row: dict[str, Any],
    route_rows: list[dict[str, Any]],
    safe_enemy_paths: set[tuple[str, str]],
    reuse: Counter[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    policy = str(row["enemy_policy"]["name"])
    distance_bin = str(row["scheduler_targets"]["distance_bin"])
    motion_amplitude = float(
        row["enemy_policy"].get("motion_amplitude_units", 0.0)
    )
    desired_relation_yaw = v4.relation_offset(
        row["scheduler_targets"]["target_relation"]
    )
    candidates: list[
        tuple[
            tuple[Any, ...],
            dict[str, Any],
            dict[str, Any],
            dict[str, Any],
        ]
    ] = []
    for certificate in route_rows:
        if not route_support_eligible(certificate):
            continue
        plan = cached_support_plan(str(certificate["route_id"]))
        certificate_start = np.asarray(
            plan["nodes"][0]["origin"], dtype=np.float64
        )
        route_seed = 14_000_000 + int(
            str(certificate["route_id"]).split("_")[-1]
        )
        camera_yaw = float((route_seed * 37) % 360) - 180.0
        for pair in certificate["compatible_enemy_pairs"]:
            if pair["distance_bin"] != distance_bin:
                continue
            if not np.allclose(
                np.asarray(pair["player_origin"], dtype=np.float64),
                certificate_start,
                atol=0.2,
                rtol=0.0,
            ):
                continue
            pair_key = v4.enemy_pair_key(pair)
            if (
                policy != "idle"
                and (pair_key, policy) not in safe_enemy_paths
            ):
                continue
            clearance = route_replay_clearance_metrics(
                certificate, pair, motion_amplitude
            )
            if not clearance["passed"]:
                continue
            bearing = review.direction_yaw(
                pair["player_origin"], pair["enemy_origin"]
            )
            relation_error = abs(
                angle_wrap(
                    camera_yaw - (bearing + desired_relation_yaw)
                )
            )
            score = (
                certificate["map"] != row["map"],
                certificate["motion"]["net_displacement_bin"]
                != row["scheduler_targets"]["net_displacement_bin"],
                reuse[str(certificate["route_id"])],
                relation_error,
                hashlib.sha256(
                    (
                        f"{row['episode_id']}:"
                        f"{certificate['route_id']}:{pair_key}"
                    ).encode()
                ).hexdigest(),
            )
            candidates.append(
                (score, certificate, pair, clearance)
            )
    if not candidates:
        raise capture.CaptureFailure(
            "v5_route_replay_enemy_clearance_capacity",
            capture.canonical_json(
                {
                    "episode_id": row["episode_id"],
                    "distance": distance_bin,
                    "policy": policy,
                    "motion_amplitude_units": motion_amplitude,
                    "required_clearance_units": (
                        ROUTE_REPLAY_PLAYER_ENEMY_CLEARANCE_UNITS
                    ),
                }
            ),
        )
    _, certificate, pair, clearance = min(
        candidates, key=lambda item: item[0]
    )
    reuse[str(certificate["route_id"])] += 1
    return (
        certificate,
        copy.deepcopy(pair),
        copy.deepcopy(clearance),
    )


def bind_route_replay(
    row: dict[str, Any],
    certificate: dict[str, Any],
    selected_pair: dict[str, Any] | None,
    clearance: dict[str, Any] | None,
) -> None:
    if not route_support_eligible(certificate):
        raise capture.CaptureFailure(
            "v5_replay_route_not_eligible",
            str(certificate["route_id"]),
        )
    plan = support_plan_from_certificate(certificate)
    route_id = str(plan["route_id"])
    route_seed = 14_000_000 + int(route_id.split("_")[-1])
    row["map"] = plan["map"]
    row["gametype"] = plan["gametype"]
    row["player"]["origin"] = list(plan["nodes"][0]["origin"])
    row["player"]["yaw"] = round(
        float((route_seed * 37) % 360) - 180.0, 6
    )
    row["player"]["pitch"] = 0.0
    row["seed"] = route_seed
    row["map_region_id"] = plan["map_region_id"]
    row["route_group_id"] = plan["route_group_id"]
    row["counterfactual_group_id"] = plan["route_group_id"]
    row["route_request"] = {
        "route_id": route_id,
        "route_plan_path": plan["route_plan_path"],
        "route_plan_sha256": plan["route_plan_sha256"],
        "route_csv_path": plan["route_csv_path"],
        "route_csv_sha256": plan["route_csv_sha256"],
        "calibration_policy": "precertified_before_manifest_promotion",
    }
    row["player_path_generation"] = {
        "schema_version": "xonotic-stage1-v5-path-generation-v1",
        "mode": "declared_route_replay",
        "support_route_id": route_id,
        "support_route_certificate_sha256": hashlib.sha256(
            capture.canonical_json(certificate).encode()
        ).hexdigest(),
        "support_route_robust_eligible": True,
        "support_route_base_jump_ticks": 0,
        "jump_binding_policy": "no_hidden_base_jump",
        "runtime_geometry_fallback": False,
        "runtime_action_fallback": False,
    }
    if not row["enemy_present"]:
        if selected_pair is not None or clearance is not None:
            raise AssertionError(row["episode_id"])
        return
    if (
        selected_pair is None
        or clearance is None
        or clearance.get("passed") is not True
    ):
        raise capture.CaptureFailure(
            "v5_route_replay_enemy_clearance_missing",
            str(row["episode_id"]),
        )
    row["player"]["origin"] = list(selected_pair["player_origin"])
    row["enemy"]["origin"] = list(selected_pair["enemy_origin"])
    enemy_yaw, _ = v2.yaw_pitch_toward(
        row["enemy"]["origin"], row["player"]["origin"]
    )
    row["enemy"]["yaw"] = round(enemy_yaw, 6)
    review.apply_enemy_policy_geometry(row)
    row["selected_geometry"] = {
        "source_pair": selected_pair["source_probe"],
        "variant": selected_pair["variant"],
        "route_replay_clearance": clearance,
    }
    policy = str(row["enemy_policy"]["name"])
    row["enemy_path_certification"] = {
        "pair_key": v4.enemy_pair_key(selected_pair),
        "axis": (
            "anchor"
            if policy == "idle"
            else ("radial" if policy == "approach_retreat" else "lateral")
        ),
        "certified": True,
        "preflight_path": str(
            v4.ENEMY_PATH_PREFLIGHT_PATH.relative_to(ROOT)
        ),
        "preflight_sha256": capture.sha256_file(
            v4.ENEMY_PATH_PREFLIGHT_PATH
        ),
    }


def bind_support_route(
    row: dict[str, Any],
    certificate: dict[str, Any],
    selected_pair: dict[str, Any] | None,
) -> None:
    if not route_support_eligible(certificate):
        raise capture.CaptureFailure(
            "v5_support_route_not_eligible",
            str(certificate["route_id"]),
        )
    plan = support_plan_from_certificate(certificate)
    route_id = str(plan["route_id"])
    route_seed = 14_000_000 + int(route_id.split("_")[-1])
    direction = str(row["action_design"]["locomotion_direction"])
    offset = locomotion_offset(direction)
    base_yaw = float((route_seed * 37) % 360) - 180.0
    row["map"] = plan["map"]
    row["gametype"] = plan["gametype"]
    row["player"]["origin"] = list(plan["nodes"][0]["origin"])
    row["player"]["yaw"] = round(angle_wrap(base_yaw + offset), 6)
    row["player"]["pitch"] = 0.0
    row["seed"] = route_seed
    row["map_region_id"] = plan["map_region_id"]
    row["route_group_id"] = plan["route_group_id"]
    row["counterfactual_group_id"] = plan["route_group_id"]
    row["route_request"] = {
        "route_id": route_id,
        "route_plan_path": plan["route_plan_path"],
        "route_plan_sha256": plan["route_plan_sha256"],
        "route_csv_path": plan["route_csv_path"],
        "route_csv_sha256": plan["route_csv_sha256"],
        "calibration_policy": "precertified_before_manifest_promotion",
    }
    row["route_view_policy"] = "look_along_route"
    row["stage1_safe_base_route"] = True
    row["stage1_route_command_scale"] = float(
        row["action_design"]["movement_xy_magnitude"]
    )
    row["stage1_locomotion_camera_offset_degrees"] = round(
        offset, 6
    )
                                                                        
                                                                           
                                                 
    row["stage1_preserve_certified_base_jump"] = False
    row["player_path_generation"] = {
        "schema_version": "xonotic-stage1-v5-path-generation-v1",
        "mode": "declared_certified_route_support",
        "support_route_id": route_id,
        "support_route_certificate_sha256": hashlib.sha256(
            capture.canonical_json(certificate).encode()
        ).hexdigest(),
        "support_route_robust_eligible": True,
        "support_route_base_jump_ticks": 0,
        "jump_binding_policy": (
            "declared_action_overlay_before_path_certification"
        ),
        "runtime_geometry_fallback": False,
        "runtime_action_fallback": False,
    }
    if row["enemy_present"]:
        if selected_pair is None:
            raise AssertionError(row["episode_id"])
        start_origin = np.asarray(
            plan["nodes"][0]["origin"], dtype=np.float64
        )
        pair_origin = np.asarray(
            selected_pair["player_origin"], dtype=np.float64
        )
        if not np.allclose(
            start_origin, pair_origin, atol=0.2, rtol=0.0
        ):
            raise capture.CaptureFailure(
                "v5_enemy_pair_route_start_mismatch",
                capture.canonical_json(
                    {
                        "episode_id": row["episode_id"],
                        "route_id": route_id,
                        "route_start": start_origin.tolist(),
                        "pair_player_origin": pair_origin.tolist(),
                    }
                ),
            )
        row["player"]["origin"] = list(
            selected_pair["player_origin"]
        )
        row["enemy"]["origin"] = list(selected_pair["enemy_origin"])
        enemy_yaw, _ = v2.yaw_pitch_toward(
            row["enemy"]["origin"], row["player"]["origin"]
        )
        row["enemy"]["yaw"] = round(enemy_yaw, 6)
        review.apply_enemy_policy_geometry(row)
        row["selected_geometry"] = {
            "source_pair": selected_pair["source_probe"],
            "variant": selected_pair["variant"],
        }
        row["enemy_path_certification"] = {
            "pair_key": v4.enemy_pair_key(selected_pair),
            "axis": (
                "anchor"
                if row["enemy_policy"]["name"] == "idle"
                else (
                    "radial"
                    if row["enemy_policy"]["name"]
                    == "approach_retreat"
                    else "lateral"
                )
            ),
            "certified": True,
            "preflight_path": str(
                v4.ENEMY_PATH_PREFLIGHT_PATH.relative_to(ROOT)
            ),
            "preflight_sha256": capture.sha256_file(
                v4.ENEMY_PATH_PREFLIGHT_PATH
            ),
        }


def normalize_prototype(
    row: dict[str, Any],
    *,
    episode_id: str,
    ordinal: int,
    wave: str,
) -> None:
    planned_weapon_action = str(
        row["action_design"]["weapon_action"]
    )
    row["episode_id"] = episode_id
    row["anchor_id"] = (
        f"{row['map']}_{episode_id}_pair"
        if row["enemy_present"]
        else f"{row['map']}_{episode_id}_solo"
    )
    row["split"] = "v5_stage1_path_certification"
    row["category"] = row["primary_bucket"]
    row["target_bin"] = row["dataset_role"]
    row["candidate_wave"] = wave
    row["candidate_ordinal"] = ordinal
    row["assigned_shard"] = (ordinal - 1) % SHARD_COUNT
    row["shard_count"] = SHARD_COUNT
    row["formal_collection_authorized"] = False
    row["formal_authorization_basis"] = (
        "nontraining_player_path_certification_only"
    )
    row["training_admitted"] = False
    row["data_spec_sha256"] = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    row["source_commit_required"] = EXPECTED_SOURCE_COMMIT
    row["weapon"] = "MachineGun"
    row["weapon_netname"] = capture.WEAPON_NETNAME["MachineGun"]
    row["player"]["clip"] = 60.0
    row["action_design"]["weapon_action"] = "none"
    row["action_design"]["action_arity"] = action_arity(
        row["action_design"]
    )
    row["acceptance"] = {
        "actual_outcome": None,
        "fire_required": False,
        "reload_success": False,
    }
    row["path_prototype"] = {
        "schema_version": "xonotic-stage1-v5-path-prototype-v1",
        "prototype_id": episode_id,
        "semantic_variant_capacity": SEMANTIC_VARIANTS_PER_PROTOTYPE,
        "certification_required": True,
        "training_data": False,
        "planned_semantic_action": planned_weapon_action,
    }


def build_prototype_wave(
    *,
    wave: str,
    scale_factor: int,
    route_rows: list[dict[str, Any]],
    schedule_wave: str | None = None,
    seed_offset: int | None = None,
    episode_prefix: str | None = None,
) -> list[dict[str, Any]]:
    eligible_route_rows = [
        row for row in route_rows if route_support_eligible(row)
    ]
    schedule_plans = [
        support_plan_from_certificate(row) for row in eligible_route_rows
    ]
    source_rows = v4.schedule(
        schedule_plans,
        wave=(
            schedule_wave
            if schedule_wave is not None
            else ("primary" if wave == "primary" else "replenishment")
        ),
        scale_factor=scale_factor,
        seed_offset=(
            seed_offset
            if seed_offset is not None
            else PROTOTYPE_SCHEDULE_SEED_OFFSETS[wave]
        ),
    )
    safe_report, safe_enemy_paths = v4.load_enemy_path_safety()
    del safe_report
    reuse: Counter[str] = Counter()
    route_replay_reuse: Counter[str] = Counter()
    result: list[dict[str, Any]] = []
    prefix = (
        episode_prefix
        if episode_prefix is not None
        else ("s1v5p" if wave == "primary" else "s1v5r")
    )
    for ordinal, source in enumerate(source_rows, 1):
        row = copy.deepcopy(source)
        episode_id = f"{prefix}_{ordinal:06d}"
        moving_nonroute = (
            not row.get("route_request")
            and row["action_design"]["locomotion_direction"] != "idle"
        )
        if moving_nonroute:
            certificate, selected_pair = select_support(
                row, eligible_route_rows, safe_enemy_paths, reuse
            )
            bind_support_route(row, certificate, selected_pair)
        elif row.get("route_request"):
            if row["enemy_present"]:
                certificate, selected_pair, clearance = (
                    select_route_replay_support(
                        row,
                        eligible_route_rows,
                        safe_enemy_paths,
                        route_replay_reuse,
                    )
                )
            else:
                route_id = str(row["route_request"]["route_id"])
                certificate = next(
                    item
                    for item in eligible_route_rows
                    if item["route_id"] == route_id
                )
                if not route_support_eligible(certificate):
                    raise capture.CaptureFailure(
                        "v5_replay_route_not_eligible", route_id
                    )
                row["player_path_generation"] = {
                    "schema_version": (
                        "xonotic-stage1-v5-path-generation-v1"
                    ),
                    "mode": "declared_route_replay",
                    "support_route_id": route_id,
                    "support_route_certificate_sha256": hashlib.sha256(
                        capture.canonical_json(certificate).encode()
                    ).hexdigest(),
                    "support_route_robust_eligible": True,
                    "support_route_base_jump_ticks": 0,
                    "jump_binding_policy": "no_hidden_base_jump",
                    "runtime_geometry_fallback": False,
                    "runtime_action_fallback": False,
                }
            if row["enemy_present"]:
                bind_route_replay(
                    row, certificate, selected_pair, clearance
                )
        else:
            row["player_path_generation"] = {
                "schema_version": (
                    "xonotic-stage1-v5-path-generation-v1"
                ),
                "mode": "preflight_static_or_jump_in_place",
                "support_route_id": None,
                "runtime_geometry_fallback": False,
                "runtime_action_fallback": False,
            }
        normalize_prototype(
            row,
            episode_id=episode_id,
            ordinal=ordinal,
            wave=wave,
        )
                                                                 
        row["anchor_id"] = (
            f"{row['map']}_{episode_id}_pair"
            if row["enemy_present"]
            else f"{row['map']}_{episode_id}_solo"
        )
        result.append(row)
    return result


def audit_prototypes(
    rows: list[dict[str, Any]], expected: int
) -> dict[str, Any]:
    action = Counter(
        row["action_design"]["weapon_action"] for row in rows
    )
    checks = {
        "rows": len(rows) == expected,
        "ids_unique": len({row["episode_id"] for row in rows})
        == expected,
        "nontraining": all(
            row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
            for row in rows
        ),
        "path_only_no_weapon_buttons": action == Counter({"none": expected}),
        "no_runtime_fallback": all(
            not row["player_path_generation"][
                "runtime_geometry_fallback"
            ]
            and not row["player_path_generation"][
                "runtime_action_fallback"
            ]
            for row in rows
        ),
        "continuous_contract": all(
            0.0
            <= float(
                row["action_design"]["movement_xy_magnitude"]
            )
            <= 1.0
            for row in rows
        ),
        "secondary_absent": all(
            row["action_design"]["weapon_action"]
            != "environmental_secondary"
            for row in rows
        ),
        "route_support_contract": all(
            (
                row["player_path_generation"]["mode"]
                not in {
                    "declared_route_replay",
                    "declared_certified_route_support",
                }
            )
            or (
                row["player_path_generation"].get(
                    "support_route_robust_eligible"
                )
                is True
                and int(
                    row["player_path_generation"].get(
                        "support_route_base_jump_ticks", -1
                    )
                )
                == 0
            )
            for row in rows
        ),
        "route_replay_enemy_clearance": all(
            (
                row["player_path_generation"]["mode"]
                != "declared_route_replay"
                or not row["enemy_present"]
            )
            or (
                (
                    row.get("selected_geometry") or {}
                ).get("route_replay_clearance", {}).get("passed")
                is True
                and float(
                    row["selected_geometry"][
                        "route_replay_clearance"
                    ]["conservative_minimum_xy_units"]
                )
                >= ROUTE_REPLAY_PLAYER_ENEMY_CLEARANCE_UNITS
            )
            for row in rows
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_prototype_audit_failed",
            capture.canonical_json(checks),
        )
    return {
        "checks": checks,
        "roles": dict(Counter(row["dataset_role"] for row in rows)),
        "buckets": dict(Counter(row["primary_bucket"] for row in rows)),
        "locomotion": dict(
            Counter(
                row["action_design"]["locomotion_direction"]
                for row in rows
            )
        ),
        "movement_profile": dict(
            Counter(
                row["action_design"]["movement_profile"]
                for row in rows
            )
        ),
        "view_direction": dict(
            Counter(
                row["action_design"]["view_direction"] for row in rows
            )
        ),
        "view_profile": dict(
            Counter(
                row["action_design"]["view_profile"] for row in rows
            )
        ),
        "path_generation": dict(
            Counter(
                row["player_path_generation"]["mode"] for row in rows
            )
        ),
    }


def materialize_prototypes() -> dict[str, Any]:
    route_audit = json.loads(
        ROUTE_AUDIT_PATH.read_text(encoding="utf-8")
    )
    if not route_audit.get("passed"):
        raise capture.CaptureFailure(
            "v5_route_audit_not_complete",
            capture.canonical_json(route_audit.get("status", {})),
        )
    route_rows = load_route_index()
    primary = build_prototype_wave(
        wave="primary",
        scale_factor=PRIMARY_PROTOTYPE_SCALE,
        route_rows=route_rows,
    )
    replenishment = build_prototype_wave(
        wave="replenishment",
        scale_factor=REPLENISHMENT_PROTOTYPE_SCALE,
        route_rows=route_rows,
    )
    primary_audit = audit_prototypes(
        primary, PRIMARY_PROTOTYPE_COUNT
    )
    replenishment_audit = audit_prototypes(
        replenishment, REPLENISHMENT_PROTOTYPE_COUNT
    )
    primary_text = canonical_lines(primary)
    replenishment_text = canonical_lines(replenishment)
    write_once_or_verify(PRIMARY_PROTOTYPES_PATH, primary_text)
    write_once_or_verify(
        REPLENISHMENT_PROTOTYPES_PATH, replenishment_text
    )
    metadata = {
        "schema_version": "xonotic-stage1-v5-prototype-manifest-v1",
        "created_utc": created_utc_for(PROTOTYPE_METADATA_PATH),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "purpose": "nontraining_authoritative_player_path_certification",
        "primary": {
            "rows": len(primary),
            "path": str(PRIMARY_PROTOTYPES_PATH.relative_to(ROOT)),
            "sha256": hashlib.sha256(primary_text.encode()).hexdigest(),
            "audit": primary_audit,
        },
        "replenishment": {
            "rows": len(replenishment),
            "path": str(
                REPLENISHMENT_PROTOTYPES_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(
                replenishment_text.encode()
            ).hexdigest(),
            "audit": replenishment_audit,
        },
        "route_index": {
            "path": str(ROUTE_INDEX_PATH.relative_to(ROOT)),
            "sha256": capture.sha256_file(ROUTE_INDEX_PATH),
            "audit_path": str(ROUTE_AUDIT_PATH.relative_to(ROOT)),
            "audit_sha256": capture.sha256_file(ROUTE_AUDIT_PATH),
        },
        "expansion_policy": {
            "semantic_variants_per_certified_path": (
                SEMANTIC_VARIANTS_PER_PROTOTYPE
            ),
            "physical_schedule_mutation_after_certification": False,
            "runtime_geometry_fallback": False,
            "runtime_action_fallback": False,
            "prototype_schedule_seed_offsets": (
                PROTOTYPE_SCHEDULE_SEED_OFFSETS
            ),
            "jump_binding_policy": (
                "manifest-declared overlay on zero-jump robust route, "
                "then authoritative full-path certification"
            ),
            "route_replay_enemy_clearance_policy": {
                "metric": (
                    "locked calibration minimum XY distance minus "
                    "declared enemy motion amplitude"
                ),
                "minimum_units": (
                    ROUTE_REPLAY_PLAYER_ENEMY_CLEARANCE_UNITS
                ),
                "final_authority": "live route and path certification",
            },
        },
    }
    write_once_or_verify(
        PROTOTYPE_METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    return metadata


def materialize_certification_spare_prototypes() -> dict[str, Any]:
    route_audit = json.loads(
        ROUTE_AUDIT_PATH.read_text(encoding="utf-8")
    )
    if not route_audit.get("passed"):
        raise capture.CaptureFailure(
            "v5_route_audit_not_complete",
            capture.canonical_json(route_audit.get("status", {})),
        )
    rows = build_prototype_wave(
        wave="certification_spare",
        scale_factor=REPLENISHMENT_PROTOTYPE_SCALE,
        route_rows=load_route_index(),
        schedule_wave="replenishment",
        seed_offset=CERTIFICATION_SPARE_SEED_OFFSET,
        episode_prefix="s1v5s",
    )
    audit = audit_prototypes(
        rows, CERTIFICATION_SPARE_PROTOTYPE_COUNT
    )
    text = canonical_lines(rows)
    write_once_or_verify(CERTIFICATION_SPARE_PROTOTYPES_PATH, text)
    metadata = {
        "schema_version": (
            "xonotic-stage1-v5-certification-spare-"
            "prototype-manifest-v1"
        ),
        "created_utc": created_utc_for(
            CERTIFICATION_SPARE_METADATA_PATH
        ),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "candidate_policy": (
            "predeclared deterministic path-level reserve covering every "
            "role-by-bucket cell; authoritative certification only; no "
            "relabel or runtime fallback"
        ),
        "schedule": {
            "wave": "replenishment",
            "scale_factor": REPLENISHMENT_PROTOTYPE_SCALE,
            "seed_offset": CERTIFICATION_SPARE_SEED_OFFSET,
        },
        "certification_spare": {
            "rows": len(rows),
            "path": str(
                CERTIFICATION_SPARE_PROTOTYPES_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "audit": audit,
        },
    }
    write_once_or_verify(
        CERTIFICATION_SPARE_METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    return metadata


def _targeted_path_generation(mode: str) -> dict[str, Any]:
    return {
        "schema_version": "xonotic-stage1-v5-path-generation-v1",
        "mode": mode,
        "support_route_id": None,
        "runtime_geometry_fallback": False,
        "runtime_action_fallback": False,
    }


def build_targeted_high_motion_prototypes() -> list[dict[str, Any]]:
    source_path = v4.INPUT_PATH
    if not source_path.is_file():
        raise capture.CaptureFailure(
            "v5_targeted_source_manifest_missing", str(source_path)
        )
    candidates = [
        row
        for row in capture.load_jsonl(source_path)
        if row["primary_bucket"] == "high_motion_special"
        and not row.get("route_request")
    ]
    if len(candidates) != TARGETED_HIGH_COUNT:
        raise capture.CaptureFailure(
            "v5_targeted_high_source_count",
            f"actual={len(candidates)} expected={TARGETED_HIGH_COUNT}",
        )
    z_by_map: dict[str, list[float]] = defaultdict(list)
    for row in candidates:
        z_by_map[row["map"]].append(
            float(row["player"]["origin"][2])
        )

    def priority(row: dict[str, Any]) -> tuple[Any, ...]:
        values = z_by_map[row["map"]]
        span = max(values) - min(values)
        relative_z = (
            (float(row["player"]["origin"][2]) - min(values)) / span
            if span > 0
            else 0.0
        )
        return (
            row["dataset_role"] != "foundation_no_enemy",
            -relative_z,
            row["action_design"]["movement_profile"]
            != "full_clip_sustained",
            -float(
                row["action_design"]["movement_xy_magnitude"]
            ),
            int(row["candidate_ordinal"]),
        )

    candidates.sort(key=priority)
    result: list[dict[str, Any]] = []
    for ordinal, source in enumerate(candidates, 1):
        row = copy.deepcopy(source)
        source_episode_id = str(row["episode_id"])
        row.pop("source_episode_id", None)
        row.pop("source_manifest", None)
        row["player_path_generation"] = _targeted_path_generation(
            "declared_preflight_direct_candidate"
        )
        normalize_prototype(
            row,
            episode_id=f"s1v5h_{ordinal:06d}",
            ordinal=ordinal,
            wave="targeted",
        )
        row["targeted_candidate"] = {
            "schema_version": (
                "xonotic-stage1-v5-targeted-candidate-v1"
            ),
            "purpose": "realized_high_motion_quota_replenishment",
            "source_episode_id": source_episode_id,
            "priority_ordinal": ordinal,
            "selection_uses_realized_telemetry_only": True,
        }
        row["anchor_id"] = (
            f"{row['map']}_{row['episode_id']}_pair"
            if row["enemy_present"]
            else f"{row['map']}_{row['episode_id']}_solo"
        )
        result.append(row)
    return result


def build_targeted_collision_prototypes() -> list[dict[str, Any]]:
    source_rows = {
        row["episode_id"]: row
        for row in capture.load_jsonl(v4.INPUT_PATH)
    }
    base_ids = (
        "s1f_000354",
        "s1f_044882",
        "s1f_048357",
        "s1f_050451",
    )
    missing = sorted(set(base_ids) - set(source_rows))
    if missing:
        raise capture.CaptureFailure(
            "v5_collision_base_missing", ",".join(missing)
        )
    result: list[dict[str, Any]] = []
    ordinal = 0
    for base_index, source_id in enumerate(base_ids):
        for variant in range(TARGETED_COLLISION_COUNT // len(base_ids)):
            ordinal += 1
            row = copy.deepcopy(source_rows[source_id])
            base_magnitude = float(
                row["action_design"]["movement_xy_magnitude"]
            )
            factor = 0.94 + 0.12 * (
                (variant + 0.5)
                / (TARGETED_COLLISION_COUNT // len(base_ids))
            )
            magnitude = round(
                min(1.0, base_magnitude * factor), 6
            )
            row["action_design"]["movement_xy_magnitude"] = magnitude
            row["action_design"]["movement_speed"] = round(
                magnitude
                * capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
                6,
            )
            if source_id == "s1f_000354":
                row["action_design"][
                    "movement_profile"
                ] = "early_hold_release"
            row["player_path_generation"] = _targeted_path_generation(
                "declared_visible_wall_contact_candidate"
            )
            row["collision_design"] = {
                "schema_version": (
                    "xonotic-stage1-collision-design-v1"
                ),
                "intent": capture.VISIBLE_COLLISION_INTENT,
                "source_positive_control": source_id,
                "candidate_declared_before_capture": True,
            }
            normalize_prototype(
                row,
                episode_id=f"s1v5c_{ordinal:06d}",
                ordinal=ordinal,
                wave="targeted",
            )
            row["targeted_candidate"] = {
                "schema_version": (
                    "xonotic-stage1-v5-targeted-candidate-v1"
                ),
                "purpose": "visible_wall_contact_small_bucket",
                "source_episode_id": source_id,
                "base_index": base_index,
                "variant": variant,
                "selection_uses_realized_telemetry_only": True,
            }
            row["anchor_id"] = (
                f"{row['map']}_{row['episode_id']}_pair"
                if row["enemy_present"]
                else f"{row['map']}_{row['episode_id']}_solo"
            )
            result.append(row)
    if len(result) != TARGETED_COLLISION_COUNT:
        raise AssertionError(len(result))
    return result


def materialize_targeted_prototypes() -> dict[str, Any]:
    high = build_targeted_high_motion_prototypes()
    collision = build_targeted_collision_prototypes()
    high_audit = audit_prototypes(high, TARGETED_HIGH_COUNT)
    collision_audit = audit_prototypes(
        collision, TARGETED_COLLISION_COUNT
    )
    high_text = canonical_lines(high)
    collision_text = canonical_lines(collision)
    write_once_or_verify(TARGETED_HIGH_PROTOTYPES_PATH, high_text)
    write_once_or_verify(
        TARGETED_COLLISION_PROTOTYPES_PATH, collision_text
    )
    metadata = {
        "schema_version": (
            "xonotic-stage1-v5-targeted-prototype-manifest-v1"
        ),
        "created_utc": created_utc_for(TARGETED_METADATA_PATH),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "candidate_policy": (
            "predeclared deterministic candidates; authoritative "
            "certification admits or rejects without relabel/fallback"
        ),
        "high_motion": {
            "rows": len(high),
            "path": str(
                TARGETED_HIGH_PROTOTYPES_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(high_text.encode()).hexdigest(),
            "audit": high_audit,
        },
        "visible_collision": {
            "rows": len(collision),
            "path": str(
                TARGETED_COLLISION_PROTOTYPES_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(
                collision_text.encode()
            ).hexdigest(),
            "audit": collision_audit,
            "full_render_certification_required": True,
        },
    }
    write_once_or_verify(
        TARGETED_METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    return metadata


def _fast_traversal_positive_control() -> dict[str, Any]:
    path = (
        ROOT
        / "stage1_foundation_v4_random_review_100_output"
        / "manifests/shards/shard-000-of-001/accepted.jsonl"
    )
    if not path.is_file():
        raise capture.CaptureFailure(
            "v5_fast_traversal_positive_control_missing",
            str(path),
        )
    matching = [
        row
        for row in capture.load_jsonl(path)
        if row.get("source_episode_id") == "s1f_017862"
    ]
    checks = {
        "singleton": len(matching) == 1,
        "nontraining": bool(matching)
        and matching[0].get("training_admitted") is False,
        "source_commit": bool(matching)
        and matching[0].get("source_commit")
        == EXPECTED_SOURCE_COMMIT,
        "collision_clear": bool(matching)
        and (matching[0].get("motion") or {})
        .get("blockage", {})
        .get("collision_policy_passed")
        is True,
        "path_ge2000": bool(matching)
        and float(
            (matching[0].get("motion") or {}).get(
                "path_length_3d", 0.0
            )
        )
        >= 2_000,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_fast_traversal_positive_control_failed",
            capture.canonical_json(checks),
        )
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": capture.sha256_file(path),
        "source_episode_id": "s1f_017862",
        "path_length_3d": matching[0]["motion"][
            "path_length_3d"
        ],
        "checks": checks,
    }


def _direct_fast_row(
    template: dict[str, Any],
    *,
    ordinal: int,
    family: str,
    origin: list[float],
    map_name: str,
    gametype: str,
    map_region_id: str,
    yaw: float,
    direction: str,
    magnitude: float,
    movement_profile: str,
    view_direction: str,
    view_profile: str,
    yaw_amplitude: float,
    pitch_amplitude: float,
    jump: bool,
    episode_prefix: str = "s1v5k",
    candidate_wave: str = "targeted_fast",
    seed_base: int = 16_800_000,
    purpose: str = "realized_path_ge2000_quota_replenishment",
) -> dict[str, Any]:
    row = copy.deepcopy(template)
    row["map"] = map_name
    row["gametype"] = gametype
    row["player"]["origin"] = [round(float(x), 6) for x in origin]
    row["player"]["yaw"] = round(angle_wrap(yaw), 6)
    row["player"]["pitch"] = 0.0
    row["seed"] = seed_base + ordinal
    row["map_region_id"] = map_region_id
    row["route_group_id"] = None
    row["counterfactual_group_id"] = (
        f"v5_fast_{map_region_id}_{family}"
    )
    row["route_request"] = None
    row["dataset_role"] = "foundation_no_enemy"
    row["primary_bucket"] = "node_atomic"
    row["enemy_present"] = False
    row["enemy"] = None
    row["enemy_model"] = ""
    row["enemy_policy"] = None
    row["enemy_path_certification"] = None
    row["scheduler_targets"] = {
        "distance_bin": None,
        "net_displacement_bin": "gt1024",
        "path_length_floor": 2_000,
        "pitch_range_bin": (
            "lt5" if pitch_amplitude < 5 else "5_15"
        ),
        "target_relation": None,
        "yaw_range_bin": (
            "lt15" if yaw_amplitude < 15 else "15_45"
        ),
    }
    design = row["action_design"]
    design.update(
        {
            "locomotion_direction": direction,
            "movement_profile": movement_profile,
            "movement_xy_magnitude": round(magnitude, 6),
            "movement_speed": round(
                magnitude
                * capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE,
                6,
            ),
            "view_direction": view_direction,
            "view_profile": view_profile,
            "yaw_amplitude": round(yaw_amplitude, 6),
            "pitch_amplitude": round(pitch_amplitude, 6),
            "jump": jump,
            "weapon_action": "none",
            "weapon_select": False,
            "zoom": False,
        }
    )
    row["player_path_generation"] = _targeted_path_generation(
        "declared_preflight_direct_candidate"
    )
    episode_id = f"{episode_prefix}_{ordinal:06d}"
    normalize_prototype(
        row,
        episode_id=episode_id,
        ordinal=ordinal,
        wave=candidate_wave,
    )
    row["anchor_id"] = f"{map_name}_{episode_id}_solo"
    row["targeted_candidate"] = {
        "schema_version": (
            "xonotic-stage1-v5-targeted-candidate-v1"
        ),
        "purpose": purpose,
        "family": family,
        "source_positive_control": "s1f_017862",
        "candidate_declared_before_capture": True,
        "selection_uses_realized_telemetry_only": True,
    }
    return row


def build_fast_traversal_prototypes() -> list[dict[str, Any]]:
    source_rows = {
        row["episode_id"]: row
        for row in capture.load_jsonl(v4.INPUT_PATH)
    }
    if "s1f_017862" not in source_rows:
        raise capture.CaptureFailure(
            "v5_fast_traversal_source_missing",
            "s1f_017862",
        )
    template = source_rows["s1f_017862"]
    result: list[dict[str, Any]] = []

                                                                    
                                                                       
                                                                      
    for index in range(FAST_TRAVERSAL_CONTROL_COUNT):
        magnitude_index = index % 96
        heading_index = (index // 96) % 16
        magnitude = 0.74 + 0.10 * (
            (magnitude_index + 0.5) / 96
        )
        yaw = -87.5 + 3.0 * (
            (heading_index + 0.5) / 16
        )
        result.append(
            _direct_fast_row(
                template,
                ordinal=len(result) + 1,
                family="go_wp0114_positive_neighborhood",
                origin=[1503.1, 2814.2, 1304.0],
                map_name="go",
                gametype="ctf",
                map_region_id="preflight_pos_go_wp0114",
                yaw=yaw,
                direction="backward",
                magnitude=magnitude,
                movement_profile="full_clip_sustained",
                view_direction="yaw_right_pitch_up",
                view_profile="early_hold_release",
                yaw_amplitude=3.5
                + 3.5 * ((index % 31) / 30),
                pitch_amplitude=2.0
                + 2.0 * ((index % 23) / 22),
                jump=False,
            )
        )

    catalog = v2.load_catalog()["maps"]
    scout_maps = ("go", "leave_em_behind")
    scout_directions = (
        "forward",
        "backward",
        "left",
        "right",
        "forward_left",
        "forward_right",
        "backward_left",
        "backward_right",
    )
    scout_view_directions = (
        "stationary",
        "yaw_left",
        "yaw_right",
        "yaw_left_pitch_up",
        "yaw_right_pitch_down",
    )
    scout_profiles = (
        "full_clip_sustained",
        "full_clip_sustained",
        "full_clip_sustained",
        "early_hold_release",
    )
    remaining = FAST_TRAVERSAL_COUNT - len(result)
    per_map = remaining // len(scout_maps)
    for map_index, map_name in enumerate(scout_maps):
        positions = catalog[map_name]["position_candidates"]
        gametype = catalog[map_name]["preflight_gametype"]
        count = (
            per_map
            if map_index < len(scout_maps) - 1
            else FAST_TRAVERSAL_COUNT - len(result)
        )
        for local_index in range(count):
            position = positions[local_index % len(positions)]
            direction = scout_directions[
                (local_index // len(positions))
                % len(scout_directions)
            ]
            heading_bin = (
                local_index
                // (len(positions) * len(scout_directions))
            ) % 16
            world_heading = -180.0 + 22.5 * heading_bin
            yaw = world_heading - locomotion_offset(direction)
            magnitude = 0.75 + 0.25 * (
                (
                    (
                        local_index * 104_729
                        + map_index * 15_485_863
                    )
                    % 1_000_003
                )
                + 0.5
            ) / 1_000_003
            view_direction = scout_view_directions[
                (local_index // 7) % len(scout_view_directions)
            ]
            has_yaw = "yaw_" in view_direction
            has_pitch = "pitch_" in view_direction
            result.append(
                _direct_fast_row(
                    template,
                    ordinal=len(result) + 1,
                    family=f"{map_name}_broad_scout",
                    origin=position["origin"],
                    map_name=map_name,
                    gametype=gametype,
                    map_region_id=(
                        f"preflight_pos_{map_name}_"
                        f"{position['candidate_id']}"
                    ),
                    yaw=yaw,
                    direction=direction,
                    magnitude=magnitude,
                    movement_profile=scout_profiles[
                        local_index % len(scout_profiles)
                    ],
                    view_direction=view_direction,
                    view_profile=(
                        "middle_window"
                        if local_index % 2
                        else "early_hold_release"
                    ),
                    yaw_amplitude=(
                        4.0 + (local_index % 17) * 1.25
                        if has_yaw
                        else 0.0
                    ),
                    pitch_amplitude=(
                        2.0 + (local_index % 9)
                        if has_pitch
                        else 0.0
                    ),
                    jump=local_index % 4 == 0,
                )
            )
    if len(result) != FAST_TRAVERSAL_COUNT:
        raise AssertionError(len(result))
    return result


def materialize_fast_traversal_prototypes() -> dict[str, Any]:
    positive_control = _fast_traversal_positive_control()
    rows = build_fast_traversal_prototypes()
    audit = audit_prototypes(rows, FAST_TRAVERSAL_COUNT)
    text = canonical_lines(rows)
    write_once_or_verify(FAST_TRAVERSAL_PROTOTYPES_PATH, text)
    metadata = {
        "schema_version": (
            "xonotic-stage1-v5-fast-traversal-prototype-manifest-v1"
        ),
        "created_utc": created_utc_for(
            FAST_TRAVERSAL_METADATA_PATH
        ),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "candidate_policy": (
            "predeclared positive-control neighborhood plus broad "
            "map scouts; authoritative realized certification only"
        ),
        "positive_control": positive_control,
        "fast_traversal": {
            "rows": len(rows),
            "path": str(
                FAST_TRAVERSAL_PROTOTYPES_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "audit": audit,
        },
    }
    write_once_or_verify(
        FAST_TRAVERSAL_METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    return metadata


def build_fast_traversal_tight_prototypes() -> list[dict[str, Any]]:
    """Return the immutable first tight-neighborhood diagnostic wave.

    This wave was declared before its certification probe.  The probe exposed
    a camera-right sign error in its attempted direction transform.  It stays
    immutable for provenance and is not rewritten after observing outcomes.
    The corrected, separately declared wave is built below.
    """
    source_rows = {
        row["episode_id"]: row
        for row in capture.load_jsonl(v4.INPUT_PATH)
    }
    if "s1f_017862" not in source_rows:
        raise capture.CaptureFailure(
            "v5_fast_traversal_tight_source_missing",
            "s1f_017862",
        )
    template = source_rows["s1f_017862"]
    directions = (
        "forward",
        "backward",
        "left",
        "right",
        "forward_left",
        "forward_right",
        "backward_left",
        "backward_right",
    )
    source_design = template["action_design"]
    source_world_heading = angle_wrap(
        float(template["player"]["yaw"])
        + locomotion_offset(
            str(source_design["locomotion_direction"])
        )
    )
    source_magnitude = float(
        source_design["movement_xy_magnitude"]
    )
    source_yaw_amplitude = float(source_design["yaw_amplitude"])
    source_pitch_amplitude = float(
        source_design["pitch_amplitude"]
    )
    result: list[dict[str, Any]] = []
    variants_per_direction = (
        FAST_TRAVERSAL_TIGHT_COUNT // len(directions)
    )
    if variants_per_direction * len(directions) != (
        FAST_TRAVERSAL_TIGHT_COUNT
    ):
        raise AssertionError(FAST_TRAVERSAL_TIGHT_COUNT)

    for index in range(FAST_TRAVERSAL_TIGHT_COUNT):
        direction_index = index % len(directions)
        variant = index // len(directions)
        direction = directions[direction_index]
                                                                           
                                                                 
        magnitude_unit = (
            ((variant * 251 + direction_index * 17) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        heading_unit = (
            ((variant * 241 + direction_index * 29) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        yaw_unit = (
            ((variant * 239 + direction_index * 43) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        pitch_unit = (
            ((variant * 233 + direction_index * 59) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        magnitude = source_magnitude + 0.027 * (
            magnitude_unit - 0.5
        )
        heading = source_world_heading + 0.24 * (
            heading_unit - 0.5
        )
        yaw = heading - locomotion_offset(direction)
        yaw_amplitude = source_yaw_amplitude + 1.10 * (
            yaw_unit - 0.5
        )
        pitch_amplitude = source_pitch_amplitude + 1.20 * (
            pitch_unit - 0.5
        )
        result.append(
            _direct_fast_row(
                template,
                ordinal=index + 1,
                family="go_wp0114_tight_balanced_neighborhood",
                origin=[1503.1, 2814.2, 1304.0],
                map_name="go",
                gametype="ctf",
                map_region_id="preflight_pos_go_wp0114",
                yaw=yaw,
                direction=direction,
                magnitude=magnitude,
                movement_profile="full_clip_sustained",
                view_direction="yaw_right_pitch_up",
                view_profile="early_hold_release",
                yaw_amplitude=yaw_amplitude,
                pitch_amplitude=pitch_amplitude,
                jump=False,
                episode_prefix="s1v5t",
                candidate_wave="targeted_fast_tight",
                seed_base=16_900_000,
                purpose=(
                    "realized_path_ge2000_quota_capacity_replenishment"
                ),
            )
        )
    return result


def materialize_fast_traversal_tight_prototypes() -> dict[str, Any]:
    positive_control = _fast_traversal_positive_control()
    rows = build_fast_traversal_tight_prototypes()
    audit = audit_prototypes(rows, FAST_TRAVERSAL_TIGHT_COUNT)
    text = canonical_lines(rows)
    write_once_or_verify(FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH, text)
    metadata = {
        "schema_version": (
            "xonotic-stage1-v5-fast-traversal-tight-"
            "prototype-manifest-v1"
        ),
        "created_utc": created_utc_for(
            FAST_TRAVERSAL_TIGHT_METADATA_PATH
        ),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "candidate_policy": (
            "predeclared balanced tight neighborhood around an external "
            "nontraining positive control; sequential prefixes balance "
            "locomotion directions; authoritative certification only; "
            "no relabel or runtime fallback"
        ),
        "positive_control": positive_control,
        "fast_traversal_tight": {
            "rows": len(rows),
            "path": str(
                FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "audit": audit,
        },
    }
    write_once_or_verify(
        FAST_TRAVERSAL_TIGHT_METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    return metadata


def build_fast_traversal_world_prototypes() -> list[dict[str, Any]]:
    """Declare a direction-balanced neighborhood in world-command space.

    The complete candidate set is generated before certification.  Every
    eight-row prefix cycle holds the same local world-space travel corridor
    while exposing each of the eight camera-relative model actions.
    """
    source_rows = {
        row["episode_id"]: row
        for row in capture.load_jsonl(v4.INPUT_PATH)
    }
    if "s1f_017862" not in source_rows:
        raise capture.CaptureFailure(
            "v5_fast_traversal_world_source_missing",
            "s1f_017862",
        )
    template = source_rows["s1f_017862"]
    directions = (
        "forward",
        "backward",
        "left",
        "right",
        "forward_left",
        "forward_right",
        "backward_left",
        "backward_right",
    )
    source_design = template["action_design"]
    source_world_heading = command_world_heading(
        float(template["player"]["yaw"]),
        str(source_design["locomotion_direction"]),
    )
    source_magnitude = float(
        source_design["movement_xy_magnitude"]
    )
    source_yaw_amplitude = float(source_design["yaw_amplitude"])
    source_pitch_amplitude = float(
        source_design["pitch_amplitude"]
    )
    result: list[dict[str, Any]] = []
    variants_per_direction = (
        FAST_TRAVERSAL_WORLD_COUNT // len(directions)
    )
    if variants_per_direction * len(directions) != (
        FAST_TRAVERSAL_WORLD_COUNT
    ):
        raise AssertionError(FAST_TRAVERSAL_WORLD_COUNT)

    for index in range(FAST_TRAVERSAL_WORLD_COUNT):
        direction_index = index % len(directions)
        variant = index // len(directions)
        direction = directions[direction_index]
        magnitude_unit = (
            ((variant * 251 + direction_index * 17) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        heading_unit = (
            ((variant * 241 + direction_index * 29) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        yaw_unit = (
            ((variant * 239 + direction_index * 43) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        pitch_unit = (
            ((variant * 233 + direction_index * 59) %
             variants_per_direction)
            + 0.5
        ) / variants_per_direction
        magnitude = source_magnitude + 0.027 * (
            magnitude_unit - 0.5
        )
        world_heading = source_world_heading + 0.24 * (
            heading_unit - 0.5
        )
                                                              
        yaw = world_heading + locomotion_offset(direction)
        yaw_amplitude = source_yaw_amplitude + 1.10 * (
            yaw_unit - 0.5
        )
        pitch_amplitude = source_pitch_amplitude + 1.20 * (
            pitch_unit - 0.5
        )
        result.append(
            _direct_fast_row(
                template,
                ordinal=index + 1,
                family="go_wp0114_world_command_balanced_neighborhood",
                origin=[1503.1, 2814.2, 1304.0],
                map_name="go",
                gametype="ctf",
                map_region_id="preflight_pos_go_wp0114",
                yaw=yaw,
                direction=direction,
                magnitude=magnitude,
                movement_profile="full_clip_sustained",
                view_direction="yaw_right_pitch_up",
                view_profile="early_hold_release",
                yaw_amplitude=yaw_amplitude,
                pitch_amplitude=pitch_amplitude,
                jump=False,
                episode_prefix="s1v5w",
                candidate_wave="targeted_fast_world",
                seed_base=17_000_000,
                purpose=(
                    "realized_path_ge2000_direction_balanced_capacity"
                ),
            )
        )
    return result


def materialize_fast_traversal_world_prototypes() -> dict[str, Any]:
    positive_control = _fast_traversal_positive_control()
    rows = build_fast_traversal_world_prototypes()
    audit = audit_prototypes(rows, FAST_TRAVERSAL_WORLD_COUNT)
    text = canonical_lines(rows)
    write_once_or_verify(FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH, text)
    metadata = {
        "schema_version": (
            "xonotic-stage1-v5-fast-traversal-world-"
            "prototype-manifest-v1"
        ),
        "created_utc": created_utc_for(
            FAST_TRAVERSAL_WORLD_METADATA_PATH
        ),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "candidate_policy": (
            "predeclared direction-balanced tight neighborhood preserving "
            "DarkPlaces world-command heading; authoritative certification "
            "only; no relabel or runtime fallback"
        ),
        "world_command_transform": {
            "formula": (
                "world_heading = camera_yaw - "
                "atan2(strafe, forward)"
            ),
            "source_positive_control": "s1f_017862",
        },
        "positive_control": positive_control,
        "fast_traversal_world": {
            "rows": len(rows),
            "path": str(
                FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH.relative_to(
                    ROOT
                )
            ),
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "audit": audit,
        },
    }
    write_once_or_verify(
        FAST_TRAVERSAL_WORLD_METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    return metadata


def load_prototype_catalog() -> dict[str, dict[str, Any]]:
    if not PROTOTYPE_METADATA_PATH.is_file():
        raise capture.CaptureFailure(
            "v5_prototype_metadata_missing",
            str(PROTOTYPE_METADATA_PATH),
        )
    metadata = json.loads(
        PROTOTYPE_METADATA_PATH.read_text(encoding="utf-8")
    )
    result: dict[str, dict[str, Any]] = {}
    for name, path in (
        ("primary", PRIMARY_PROTOTYPES_PATH),
        ("replenishment", REPLENISHMENT_PROTOTYPES_PATH),
    ):
        declared = metadata[name]
        if (
            declared["path"] != str(path.relative_to(ROOT))
            or declared["sha256"] != capture.sha256_file(path)
        ):
            raise capture.CaptureFailure(
                "v5_prototype_catalog_hash_mismatch", str(path)
            )
        for row in capture.load_jsonl(path):
            prototype_id = str(row["episode_id"])
            if prototype_id in result:
                raise capture.CaptureFailure(
                    "v5_duplicate_prototype_id", prototype_id
                )
            result[prototype_id] = row
    if CERTIFICATION_SPARE_METADATA_PATH.is_file():
        spare = json.loads(
            CERTIFICATION_SPARE_METADATA_PATH.read_text(
                encoding="utf-8"
            )
        )
        declared = spare["certification_spare"]
        if (
            declared["path"]
            != str(
                CERTIFICATION_SPARE_PROTOTYPES_PATH.relative_to(ROOT)
            )
            or declared["sha256"]
            != capture.sha256_file(
                CERTIFICATION_SPARE_PROTOTYPES_PATH
            )
        ):
            raise capture.CaptureFailure(
                "v5_certification_spare_catalog_hash_mismatch",
                str(CERTIFICATION_SPARE_PROTOTYPES_PATH),
            )
        for row in capture.load_jsonl(
            CERTIFICATION_SPARE_PROTOTYPES_PATH
        ):
            prototype_id = str(row["episode_id"])
            if prototype_id in result:
                raise capture.CaptureFailure(
                    "v5_duplicate_prototype_id", prototype_id
                )
            result[prototype_id] = row
    if TARGETED_METADATA_PATH.is_file():
        targeted = json.loads(
            TARGETED_METADATA_PATH.read_text(encoding="utf-8")
        )
        for name, path in (
            ("high_motion", TARGETED_HIGH_PROTOTYPES_PATH),
            ("visible_collision", TARGETED_COLLISION_PROTOTYPES_PATH),
        ):
            declared = targeted[name]
            if (
                declared["path"] != str(path.relative_to(ROOT))
                or declared["sha256"] != capture.sha256_file(path)
            ):
                raise capture.CaptureFailure(
                    "v5_targeted_catalog_hash_mismatch", str(path)
                )
            for row in capture.load_jsonl(path):
                prototype_id = str(row["episode_id"])
                if prototype_id in result:
                    raise capture.CaptureFailure(
                        "v5_duplicate_prototype_id", prototype_id
                    )
                result[prototype_id] = row
    if FAST_TRAVERSAL_METADATA_PATH.is_file():
        fast = json.loads(
            FAST_TRAVERSAL_METADATA_PATH.read_text(
                encoding="utf-8"
            )
        )
        declared = fast["fast_traversal"]
        if (
            declared["path"]
            != str(FAST_TRAVERSAL_PROTOTYPES_PATH.relative_to(ROOT))
            or declared["sha256"]
            != capture.sha256_file(FAST_TRAVERSAL_PROTOTYPES_PATH)
        ):
            raise capture.CaptureFailure(
                "v5_fast_traversal_catalog_hash_mismatch",
                str(FAST_TRAVERSAL_PROTOTYPES_PATH),
            )
        for row in capture.load_jsonl(
            FAST_TRAVERSAL_PROTOTYPES_PATH
        ):
            prototype_id = str(row["episode_id"])
            if prototype_id in result:
                raise capture.CaptureFailure(
                    "v5_duplicate_prototype_id", prototype_id
                )
            result[prototype_id] = row
    if FAST_TRAVERSAL_TIGHT_METADATA_PATH.is_file():
        tight = json.loads(
            FAST_TRAVERSAL_TIGHT_METADATA_PATH.read_text(
                encoding="utf-8"
            )
        )
        declared = tight["fast_traversal_tight"]
        if (
            declared["path"]
            != str(
                FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH.relative_to(
                    ROOT
                )
            )
            or declared["sha256"]
            != capture.sha256_file(
                FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH
            )
        ):
            raise capture.CaptureFailure(
                "v5_fast_traversal_tight_catalog_hash_mismatch",
                str(FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH),
            )
        for row in capture.load_jsonl(
            FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH
        ):
            prototype_id = str(row["episode_id"])
            if prototype_id in result:
                raise capture.CaptureFailure(
                    "v5_duplicate_prototype_id", prototype_id
                )
            result[prototype_id] = row
    if FAST_TRAVERSAL_WORLD_METADATA_PATH.is_file():
        world = json.loads(
            FAST_TRAVERSAL_WORLD_METADATA_PATH.read_text(
                encoding="utf-8"
            )
        )
        declared = world["fast_traversal_world"]
        if (
            declared["path"]
            != str(
                FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH.relative_to(
                    ROOT
                )
            )
            or declared["sha256"]
            != capture.sha256_file(
                FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH
            )
        ):
            raise capture.CaptureFailure(
                "v5_fast_traversal_world_catalog_hash_mismatch",
                str(FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH),
            )
        for row in capture.load_jsonl(
            FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH
        ):
            prototype_id = str(row["episode_id"])
            if prototype_id in result:
                raise capture.CaptureFailure(
                    "v5_duplicate_prototype_id", prototype_id
                )
            result[prototype_id] = row
    return result


def load_certified_pool() -> list[dict[str, Any]]:
    prototypes = load_prototype_catalog()
    active_source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    compatibility = (
        player_path_runtime_compatibility_reference()
        if active_source_commit != EXPECTED_SOURCE_COMMIT
        else None
    )
    indexed: dict[str, dict[str, Any]] = {}
    for row in capture.load_jsonl(PATH_CERTIFICATE_INDEX):
        prototype_id = str(row.get("prototype_id", ""))
        if not prototype_id:
            raise capture.CaptureFailure(
                "v5_path_index_id_missing",
                str(PATH_CERTIFICATE_INDEX),
            )
        prior = indexed.get(prototype_id)
        if prior is not None and prior != row:
            raise capture.CaptureFailure(
                "v5_path_index_conflict", prototype_id
            )
        indexed[prototype_id] = row
    result: list[dict[str, Any]] = []
    for prototype_id, reference in sorted(indexed.items()):
        if reference.get("status") != "certified":
            continue
        prototype = prototypes.get(prototype_id)
        if prototype is None:
            raise capture.CaptureFailure(
                "v5_certificate_prototype_missing", prototype_id
            )
        scenario = copy.deepcopy(prototype)
        scenario["player_path_certificate"] = reference
        if compatibility is not None:
            scenario["player_path_runtime_compatibility"] = (
                copy.deepcopy(compatibility)
            )
        certificate = capture.load_player_path_certificate(scenario)
        if certificate is None:
            raise AssertionError(prototype_id)
        if (
            reference.get("motion") != certificate.get("motion")
            or reference.get("movement_blockage")
            != certificate.get("movement_blockage")
        ):
            raise capture.CaptureFailure(
                "v5_path_index_metric_drift", prototype_id
            )
        combined = copy.deepcopy(prototype)
        combined["_player_path_certificate"] = reference
        combined["_certified_motion"] = certificate["motion"]
        combined["_certified_blockage"] = certificate[
            "movement_blockage"
        ]
        result.append(combined)
    return result


@lru_cache(maxsize=1)
def player_path_runtime_compatibility_reference(
) -> dict[str, Any]:
    if not PATH_RUNTIME_COMPATIBILITY_AUDIT.is_file():
        raise capture.CaptureFailure(
            "v5_runtime_compatibility_audit_missing",
            str(PATH_RUNTIME_COMPATIBILITY_AUDIT),
        )
    audit = json.loads(
        PATH_RUNTIME_COMPATIBILITY_AUDIT.read_text(encoding="utf-8")
    )
    scope = audit.get("authorization_scope") or {}
    checks = {
        "schema": audit.get("schema_version")
        == capture.PLAYER_PATH_RUNTIME_COMPATIBILITY_SCHEMA,
        "passed": audit.get("passed") is True,
        "certificate_source_commit": scope.get(
            "certificate_source_commit"
        )
        == EXPECTED_SOURCE_COMMIT,
        "runtime_source_commit": scope.get(
            "runtime_source_commit"
        )
        == RUNTIME_SOURCE_COMMIT,
        "certificate_index_path": scope.get(
            "certificate_index_path"
        )
        == str(PATH_CERTIFICATE_INDEX.relative_to(ROOT)),
        "certificate_index_sha256": scope.get(
            "certificate_index_sha256"
        )
        == capture.sha256_file(PATH_CERTIFICATE_INDEX),
        "exact_scope": scope.get("kind")
        == "exact_commit_pair_and_certificate_index",
        "no_generic_descendants": scope.get(
            "generic_descendant_commits_allowed"
        )
        is False,
        "no_runtime_fallback": scope.get(
            "runtime_fallback_allowed"
        )
        is False,
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_runtime_compatibility_audit_contract_failed",
            capture.canonical_json(checks),
        )
    return {
        "schema_version": (
            capture.PLAYER_PATH_RUNTIME_COMPATIBILITY_REFERENCE_SCHEMA
        ),
        "audit_path": str(
            PATH_RUNTIME_COMPATIBILITY_AUDIT.relative_to(ROOT)
        ),
        "audit_sha256": capture.sha256_file(
            PATH_RUNTIME_COMPATIBILITY_AUDIT
        ),
        "certificate_source_commit": EXPECTED_SOURCE_COMMIT,
        "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
        "certificate_index_path": str(
            PATH_CERTIFICATE_INDEX.relative_to(ROOT)
        ),
        "certificate_index_sha256": capture.sha256_file(
            PATH_CERTIFICATE_INDEX
        ),
    }


@lru_cache(maxsize=1)
def semantic_weight_feasibility_reference() -> dict[str, Any]:
    if not SEMANTIC_WEIGHT_FEASIBILITY_AUDIT.is_file():
        raise capture.CaptureFailure(
            "v5_semantic_weight_feasibility_audit_missing",
            str(SEMANTIC_WEIGHT_FEASIBILITY_AUDIT),
        )
    audit = json.loads(
        SEMANTIC_WEIGHT_FEASIBILITY_AUDIT.read_text(
            encoding="utf-8"
        )
    )
    tests = audit.get("tests") or []
    tested_bounds = [float(row.get("bound")) for row in tests]
    chosen = next(
        (
            row
            for row in tests
            if math.isclose(
                float(row.get("bound", math.inf)),
                FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX,
            )
        ),
        {},
    )
    lower = [
        row
        for row in tests
        if float(row.get("bound", math.inf))
        < FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
    ]
    implementation = audit.get("implementation_sha256") or {}
    checks = {
        "schema": audit.get("schema_version")
        == "xonotic-stage1-v5-semantic-weight-feasibility-v1",
        "passed": audit.get("passed") is True,
        "no_capacity_clamping": audit.get("capacity_clamping")
        is False,
        "certificate_index": audit.get(
            "certificate_index_sha256"
        )
        == capture.sha256_file(PATH_CERTIFICATE_INDEX),
        "distribution_constraint_count": audit.get(
            "distribution_constraint_count"
        )
        == 71,
        "first_audited_feasible_bound": math.isclose(
            float(audit.get("first_feasible_bound", math.inf)),
            FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX,
        ),
        "chosen_bound_tested_and_feasible": (
            chosen.get("feasible") is True
            and chosen.get("distribution_constraints_passed") is True
            and float(
                chosen.get(
                    "mean_absolute_deviation_from_ten", math.inf
                )
            )
            <= FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
        ),
        "all_declared_lower_bounds_audited_unsuccessful": (
            tested_bounds
            == sorted(tested_bounds)
            and len(lower) > 0
            and all(row.get("feasible") is False for row in lower)
        ),
        "generator_implementation": implementation.get(
            "prepare_stage1_v5_manifests.py"
        )
        == capture.sha256_file(Path(__file__).resolve()),
        "audit_implementation": implementation.get(
            "audit_stage1_v5_semantic_weight_feasibility.py"
        )
        == capture.sha256_file(
            ROOT
            / "scripts"
            / "audit_stage1_v5_semantic_weight_feasibility.py"
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_semantic_weight_feasibility_audit_contract_failed",
            capture.canonical_json(checks),
        )
    return {
        "schema_version": (
            "xonotic-stage1-v5-semantic-weight-feasibility-reference-v1"
        ),
        "audit_path": str(
            SEMANTIC_WEIGHT_FEASIBILITY_AUDIT.relative_to(ROOT)
        ),
        "audit_sha256": capture.sha256_file(
            SEMANTIC_WEIGHT_FEASIBILITY_AUDIT
        ),
        "certificate_index_sha256": capture.sha256_file(
            PATH_CERTIFICATE_INDEX
        ),
        "primary_selection_sha256": audit[
            "primary_selection_sha256"
        ],
        "mean_absolute_deviation_maximum": (
            FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
        ),
        "capacity_clamping": False,
        "lower_bound_results": [
            {
                "bound": float(row["bound"]),
                "reason": row.get("reason"),
                "detail": row.get("detail"),
            }
            for row in lower
        ],
    }


@lru_cache(maxsize=1)
def replenishment_feasibility_reference() -> dict[str, Any]:
    if not REPLENISHMENT_FEASIBILITY_AUDIT.is_file():
        raise capture.CaptureFailure(
            "v5_replenishment_feasibility_audit_missing",
            str(REPLENISHMENT_FEASIBILITY_AUDIT),
        )
    audit = json.loads(
        REPLENISHMENT_FEASIBILITY_AUDIT.read_text(encoding="utf-8")
    )
    optimized = audit.get("recommended_policy_optimization") or {}
    fixed_policy = audit.get("fixed_policy") or {}
    selected = optimized.get("selected_distribution") or {}
    physical = optimized.get("selected_physical_marginals") or {}
    primary_semantic = audit.get(
        "primary_semantic_allocation"
    ) or {}
    replenishment_semantic = optimized.get(
        "semantic_allocation"
    ) or {}
    semantic_constraints = {
        str(constraint.get("name")): constraint
        for constraint in (
            (audit.get("constraint_groups") or {}).get(
                "semantic_capacity", []
            )
        )
        if str(constraint.get("name", "")).startswith(
            "semantic_variant_weight_capacity:"
        )
    }
    normalized_physical = {
        field: {
            str(value): count
            for value, count in targets.items()
        }
        for field, targets in REPLENISHMENT_FIXED_PHYSICAL_TARGETS.items()
    }
    expected_semantic_constraints = {
        f"semantic_variant_weight_capacity:{role}:{bucket}": {
            "lower": math.ceil(
                target
                / (
                    FORMAL_SEMANTIC_VARIANTS_MAX
                    - FORMAL_SEMANTIC_VARIANTS_MIN
                )
            ),
            "upper": target,
        }
        for (role, bucket), target in sorted(
            REPLENISHMENT_FIXED_CELL_PATH_COUNTS.items()
        )
    }
    checks = {
        "schema": audit.get("schema_version")
        == "xonotic-stage1-v5-replenishment-constraint-audit-v1",
        "no_capacity_clamping": audit.get("capacity_clamping") is False,
        "audit_passed": audit.get("passed") is True,
        "certificate_index": audit.get("certificate_index_sha256")
        == capture.sha256_file(PATH_CERTIFICATE_INDEX),
        "primary_rows": audit.get("primary_rows")
        == PRIMARY_PROTOTYPE_COUNT,
        "primary_semantic_allocation_feasible": (
            primary_semantic.get("feasible") is True
            and float(
                primary_semantic.get(
                    "mean_absolute_deviation_from_ten",
                    math.inf,
                )
            )
            <= FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
        ),
        "residual_rows": audit.get("residual_rows") == 3_598,
        "optimized_feasible": optimized.get("feasible") is True,
        "optimized_solver_feasible": optimized.get(
            "solver_feasible"
        )
        is True,
        "optimized_semantic_allocation_feasible": optimized.get(
            "semantic_allocation_feasible"
        )
        is True,
        "optimized_semantic_weight_deviation": float(
            replenishment_semantic.get(
                "mean_absolute_deviation_from_ten", math.inf
            )
        )
        <= FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX,
        "optimized_semantic_allocation_cells": (
            len(
                (
                    optimized.get("semantic_allocation") or {}
                ).get("cells", [])
            )
            == len(REPLENISHMENT_FIXED_CELL_PATH_COUNTS)
            and (
                optimized.get("semantic_allocation") or {}
            ).get("capacity_clamping")
            is False
        ),
        "optimized_no_capacity_clamping": optimized.get(
            "capacity_clamping"
        )
        is False,
        "semantic_capacity_hard": "semantic_capacity"
        in (optimized.get("hard_groups") or []),
        "fixed_action_cells": fixed_policy.get(
            "action_cell_targets"
        )
        == {
            f"{role}:{bucket}": targets
            for (role, bucket), targets in sorted(
                REPLENISHMENT_FIXED_ACTION_CELL_COUNTS.items()
            )
        },
        "fixed_net_policy": fixed_policy.get("net_targets")
        == REPLENISHMENT_FIXED_NET_TARGETS,
        "fixed_physical_policy": fixed_policy.get(
            "physical_targets"
        )
        == normalized_physical,
        "semantic_variant_weight_bounds": fixed_policy.get(
            "semantic_variant_weight_bounds"
        )
        == {
            "minimum": FORMAL_SEMANTIC_VARIANTS_MIN,
            "maximum": FORMAL_SEMANTIC_VARIANTS_MAX,
            "mean_absolute_deviation_maximum": (
                FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
            ),
        },
        "semantic_variant_weight_constraints": (
            set(semantic_constraints)
            == set(expected_semantic_constraints)
            and all(
                int(semantic_constraints[name].get("lower", -1))
                == bounds["lower"]
                and int(semantic_constraints[name].get("upper", -1))
                == bounds["upper"]
                and int(semantic_constraints[name].get("capacity", -1))
                >= bounds["lower"]
                for name, bounds in (
                    expected_semantic_constraints.items()
                )
            )
        ),
        "optimized_net": selected.get("net")
        == REPLENISHMENT_FIXED_NET_TARGETS,
        "optimized_physical": physical == normalized_physical,
        "long_path_floor": selected.get("path_ge1000")
        >= math.ceil(
            REPLENISHMENT_PROTOTYPE_COUNT
            * PATH_GE1000_MIN_FRACTION
        ),
        "very_long_path_floor": selected.get("path_ge2000")
        >= math.ceil(
            REPLENISHMENT_PROTOTYPE_COUNT
            * PATH_GE2000_MIN_FRACTION
        ),
        "joint_floor": selected.get("joint_net512_yaw90")
        >= math.ceil(
            REPLENISHMENT_PROTOTYPE_COUNT
            * JOINT_NET512_YAW90_MIN_FRACTION
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_replenishment_feasibility_audit_contract_failed",
            capture.canonical_json(checks),
        )
    return {
        "schema_version": (
            "xonotic-stage1-v5-replenishment-feasibility-reference-v1"
        ),
        "audit_path": str(
            REPLENISHMENT_FEASIBILITY_AUDIT.relative_to(ROOT)
        ),
        "audit_sha256": capture.sha256_file(
            REPLENISHMENT_FEASIBILITY_AUDIT
        ),
        "certificate_index_sha256": capture.sha256_file(
            PATH_CERTIFICATE_INDEX
        ),
        "capacity_clamping": False,
        "planned_tolerance_fraction": (
            REPLENISHMENT_PLANNED_TOLERANCE
        ),
        "fixed_net_targets": REPLENISHMENT_FIXED_NET_TARGETS,
        "fixed_physical_targets": (
            REPLENISHMENT_FIXED_PHYSICAL_TARGETS
        ),
        "fixed_action_cell_targets": {
            f"{role}:{bucket}": targets
            for (role, bucket), targets in sorted(
                REPLENISHMENT_FIXED_ACTION_CELL_COUNTS.items()
            )
        },
    }


def selection_capacity_report(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "roles": dict(Counter(row["dataset_role"] for row in rows)),
        "bucket_roles": {
            f"{role}:{bucket}": count
            for (role, bucket), count in sorted(
                Counter(
                    (row["dataset_role"], row["primary_bucket"])
                    for row in rows
                ).items()
            )
        },
        "net": dict(
            Counter(
                row["_certified_motion"]["net_displacement_bin"]
                for row in rows
            )
        ),
        "yaw": dict(
            Counter(
                row["_certified_motion"]["yaw_range_bin"]
                for row in rows
            )
        ),
        "pitch": dict(
            Counter(
                row["_certified_motion"]["pitch_range_bin"]
                for row in rows
            )
        ),
        "planned_relation": dict(
            Counter(
                row["scheduler_targets"]["target_relation"]
                for row in rows
                if row["enemy_present"]
            )
        ),
        "planned_distance": dict(
            Counter(
                row["scheduler_targets"]["distance_bin"]
                for row in rows
                if row["enemy_present"]
            )
        ),
        "planned_enemy_policy": dict(
            Counter(
                row["enemy_policy"]["name"]
                for row in rows
                if row["enemy_present"]
            )
        ),
        "path_ge1000": sum(
            row["_certified_motion"]["path_length_3d"] >= 1_000
            for row in rows
        ),
        "path_ge2000": sum(
            row["_certified_motion"]["path_length_3d"] >= 2_000
            for row in rows
        ),
        "joint_net512_yaw90": sum(
            row["_certified_motion"]["net_displacement_3d"] >= 512
            and row["_certified_motion"]["yaw_range_deg"] >= 90
            for row in rows
        ),
        "visible_wall_contact": sum(
            row["_certified_blockage"].get(
                "visible_collision_qualified"
            )
            is True
            for row in rows
        ),
        "maps": dict(Counter(row["map"] for row in rows)),
    }


def select_certified_paths(
    rows: list[dict[str, Any]],
    *,
    count: int,
    quota_scale: int,
    label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if label == "replenishment":
        replenishment_feasibility_reference()
    if len(rows) < count:
        raise capture.CaptureFailure(
            "v5_certified_path_pool_too_small",
            capture.canonical_json(
                {
                    "label": label,
                    "have": len(rows),
                    "need": count,
                    "capacity": selection_capacity_report(rows),
                }
            ),
        )
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError as exc:
        raise capture.CaptureFailure(
            "v5_manifest_milp_dependency_missing", str(exc)
        ) from exc

    vectors: list[np.ndarray] = []
    lower: list[float] = []
    upper: list[float] = []
    names: list[str] = []

    def constrain(
        name: str,
        predicate: Any,
        minimum: int,
        maximum: int,
    ) -> None:
        vectors.append(
            np.fromiter(
                (1.0 if predicate(row) else 0.0 for row in rows),
                dtype=np.float64,
                count=len(rows),
            )
        )
        lower.append(float(minimum))
        upper.append(float(maximum))
        names.append(name)

    constrain("total", lambda _: True, count, count)
    for bucket, role_counts in v4.BUCKET_ROLE_COUNTS.items():
        for role, full_count in role_counts.items():
            cell = (role, bucket)
            target = (
                REPLENISHMENT_FIXED_CELL_PATH_COUNTS[
                    cell
                ]
                if label == "replenishment"
                else full_count // quota_scale
            )
            constrain(
                f"cell:{role}:{bucket}",
                lambda row, role=role, bucket=bucket: (
                    row["dataset_role"] == role
                    and row["primary_bucket"] == bucket
                ),
                target,
                target,
            )
            semantic_targets = semantic_action_cell_targets(
                cell,
                target * SEMANTIC_VARIANTS_PER_PROTOTYPE,
                replenishment=(label == "replenishment"),
            )
            constrain(
                f"semantic_primary_capacity:{role}:{bucket}",
                lambda row, role=role, bucket=bucket: (
                    row["dataset_role"] == role
                    and row["primary_bucket"] == bucket
                    and physical_arity(row) <= 2
                    and not row["_certified_blockage"].get(
                        "visible_collision_qualified", False
                    )
                    and (
                        not row["enemy_present"]
                        or row["scheduler_targets"]["target_relation"]
                        in SAFE_PRIMARY_FIRE_RELATIONS
                    )
                ),
                math.ceil(
                    semantic_targets["environmental_primary"]
                    / len(v4.WEAPONS)
                ),
                target,
            )
            constrain(
                f"semantic_reload_capacity:{role}:{bucket}",
                lambda row, role=role, bucket=bucket: (
                    row["dataset_role"] == role
                    and row["primary_bucket"] == bucket
                    and physical_arity(row) <= 2
                ),
                math.ceil(
                    semantic_targets["reload"]
                    / len(v4.RELOAD_WEAPONS)
                ),
                target,
            )
            constrain(
                f"semantic_variant_weight_capacity:{role}:{bucket}",
                lambda row, role=role, bucket=bucket: (
                    row["dataset_role"] == role
                    and row["primary_bucket"] == bucket
                    and physical_arity(row) <= 2
                ),
                math.ceil(
                    target
                    / (
                        FORMAL_SEMANTIC_VARIANTS_MAX
                        - FORMAL_SEMANTIC_VARIANTS_MIN
                    )
                ),
                target,
            )

    planned_enemy_targets = (
        (
            "target_relation",
            v4.RELATION_COUNTS,
            lambda row: (
                row.get("scheduler_targets") or {}
            ).get("target_relation"),
        ),
        (
            "distance",
            v4.DISTANCE_COUNTS,
            lambda row: (
                row.get("scheduler_targets") or {}
            ).get("distance_bin"),
        ),
        (
            "enemy_policy",
            v4.ENEMY_POLICY_COUNTS,
            lambda row: (
                row.get("enemy_policy") or {}
            ).get("name"),
        ),
    )
    for axis, targets, value_for in planned_enemy_targets:
        for value, full_count in targets.items():
            target = (
                REPLENISHMENT_FIXED_PLANNED_TARGETS[axis][
                    value
                ]
                if label == "replenishment"
                else full_count // quota_scale
            )
            tolerance = (
                math.ceil(
                    target * REPLENISHMENT_PLANNED_TOLERANCE
                )
                if label == "replenishment"
                else 0
            )
            constrain(
                f"planned:{axis}:{value}",
                lambda row, value=value, value_for=value_for: (
                    value_for(row) == value
                ),
                max(0, target - tolerance),
                target + tolerance,
            )

    for field, baseline in PHYSICAL_MARGINAL_BASELINE.items():
        for value, full_count in baseline.items():
            target = (
                REPLENISHMENT_FIXED_PHYSICAL_TARGETS[field][value]
                if label == "replenishment"
                else round(full_count / quota_scale)
            )
            tolerance = max(
                1,
                math.ceil(
                    target
                    * FORMAL_SEMANTIC_MARGINAL_TOLERANCE
                ),
            )
            constrain(
                f"physical:{field}:{value}",
                lambda row, field=field, value=value: (
                    row["action_design"].get(field) == value
                ),
                max(0, target - tolerance),
                target + tolerance,
            )

    realized_targets = (
        ("net", v4.NET_COUNTS, "net_displacement_bin"),
        ("yaw", v4.YAW_COUNTS, "yaw_range_bin"),
        ("pitch", v4.PITCH_COUNTS, "pitch_range_bin"),
    )
    realized_quota_policy: list[dict[str, Any]] = []
    for axis, targets, metric_name in realized_targets:
        for bin_name, full_count in targets.items():
            target = (
                REPLENISHMENT_FIXED_NET_TARGETS[bin_name]
                if label == "replenishment" and axis == "net"
                else full_count // quota_scale
            )
                                                                            
                                                                         
                                                                             
                                                                             
                                                                 
            tolerance = math.ceil(
                target * REALIZED_MARGINAL_TOLERANCE
            )
            if label == "replenishment" and axis == "net":
                tolerance = 0
            minimum = max(0, target - tolerance)
            maximum = target + tolerance
            constrain(
                f"{axis}:{bin_name}",
                lambda row, metric_name=metric_name, bin_name=bin_name: (
                    row["_certified_motion"][metric_name] == bin_name
                ),
                minimum,
                maximum,
            )
            realized_quota_policy.append(
                {
                    "axis": axis,
                    "bin": bin_name,
                    "target": target,
                    "tolerance_fraction": (
                        REALIZED_MARGINAL_TOLERANCE
                    ),
                    "tolerance_rows": tolerance,
                    "lower": minimum,
                    "upper": maximum,
                }
            )

    constrain(
        "path_ge1000",
        lambda row: row["_certified_motion"]["path_length_3d"]
        >= 1_000,
                                                                         
                                                                        
                                                                          
                                                                   
                                        
        math.ceil(count * PATH_GE1000_MIN_FRACTION),
        count,
    )
    constrain(
        "path_ge2000",
        lambda row: row["_certified_motion"]["path_length_3d"]
        >= 2_000,
        math.ceil(count * PATH_GE2000_MIN_FRACTION),
        count,
    )
    constrain(
        "joint_net512_yaw90",
        lambda row: (
            row["_certified_motion"]["net_displacement_3d"] >= 512
            and row["_certified_motion"]["yaw_range_deg"] >= 90
        ),
        math.ceil(count * JOINT_NET512_YAW90_MIN_FRACTION),
        count,
    )
    constrain(
        "visible_wall_contact_1_to_3pct",
        lambda row: (
            row["_certified_blockage"].get(
                "visible_collision_qualified"
            )
            is True
            and physical_arity(row) <= 2
        ),
        math.ceil(count * 0.01),
        math.floor(count * 0.03),
    )
    constrain(
        "visible_wall_contact_arity_gt2_excluded",
        lambda row: (
            row["_certified_blockage"].get(
                "visible_collision_qualified"
            )
            is True
            and physical_arity(row) > 2
        ),
        0,
        0,
    )
    for map_name in sorted({str(row["map"]) for row in rows}):
        constrain(
            f"map:{map_name}",
            lambda row, map_name=map_name: row["map"] == map_name,
            1,
            count,
        )

    matrix = np.vstack(vectors)
    constraint = LinearConstraint(
        matrix, np.asarray(lower), np.asarray(upper)
    )
    primary_rank = {
        "primary": 0.0,
        "replenishment": 1.0,
    }
    objective = np.asarray(
        [
            primary_rank.get(str(row["candidate_wave"]), 2.0)
            + (
                int(
                    hashlib.sha256(
                        f"{label}:{row['episode_id']}".encode()
                    ).hexdigest()[:12],
                    16,
                )
                / float(16**12)
            )
            * 1e-3
            for row in rows
        ],
        dtype=np.float64,
    )
    solved = milp(
        objective,
        integrality=np.ones(len(rows), dtype=np.int8),
        bounds=Bounds(
            np.zeros(len(rows)), np.ones(len(rows))
        ),
        constraints=constraint,
        options={"time_limit": 120.0, "mip_rel_gap": 0.0},
    )
    if not solved.success or solved.x is None:
        raise capture.CaptureFailure(
            "v5_certified_path_quota_infeasible",
            capture.canonical_json(
                {
                    "label": label,
                    "solver_status": int(solved.status),
                    "solver_message": str(solved.message),
                    "capacity": selection_capacity_report(rows),
                    "realized_quota_policy": {
                        "kind": (
                            "fixed_symmetric_approximate_distribution"
                        ),
                        "capacity_clamping": False,
                        "tolerance_fraction": (
                            REALIZED_MARGINAL_TOLERANCE
                        ),
                        "bounds": realized_quota_policy,
                    },
                    "long_path_quota_policy": {
                        "kind": "fixed_approximate_distribution",
                        "capacity_clamping": False,
                        "path_ge1000_min_fraction": (
                            PATH_GE1000_MIN_FRACTION
                        ),
                        "path_ge2000_min_fraction": (
                            PATH_GE2000_MIN_FRACTION
                        ),
                        "joint_net512_yaw90_min_fraction": (
                            JOINT_NET512_YAW90_MIN_FRACTION
                        ),
                    },
                    "constraints": [
                        {
                            "name": name,
                            "lower": low,
                            "upper": high,
                            "capacity": int(vector.sum()),
                        }
                        for name, low, high, vector in zip(
                            names, lower, upper, vectors
                        )
                    ],
                }
            ),
        )
    selected = [
        row
        for row, value in zip(rows, solved.x)
        if float(value) >= 0.5
    ]
    if len(selected) != count:
        raise AssertionError((label, len(selected), count))
    selected.sort(key=lambda row: str(row["episode_id"]))
    audit = {
        "label": label,
        "rows": len(selected),
        "source_wave": dict(
            Counter(row["candidate_wave"] for row in selected)
        ),
        "selection_capacity": selection_capacity_report(rows),
        "selected_distribution": selection_capacity_report(selected),
        "solver": {
            "status": int(solved.status),
            "message": str(solved.message),
            "objective": float(solved.fun),
        },
        "realized_quota_policy": {
            "kind": "fixed_symmetric_approximate_distribution",
            "capacity_clamping": False,
            "tolerance_fraction": REALIZED_MARGINAL_TOLERANCE,
            "bounds": realized_quota_policy,
        },
        "planned_quota_policy": {
            "kind": (
                "fixed_symmetric_approximate_distribution"
                if label == "replenishment"
                else "exact_primary_schedule"
            ),
            "capacity_clamping": False,
            "tolerance_fraction": (
                REPLENISHMENT_PLANNED_TOLERANCE
                if label == "replenishment"
                else 0.0
            ),
        },
        "long_path_quota_policy": {
            "kind": "fixed_approximate_distribution",
            "capacity_clamping": False,
            "path_ge1000_min_fraction": (
                PATH_GE1000_MIN_FRACTION
            ),
            "path_ge2000_min_fraction": (
                PATH_GE2000_MIN_FRACTION
            ),
            "joint_net512_yaw90_min_fraction": (
                JOINT_NET512_YAW90_MIN_FRACTION
            ),
            "conditioned_path_ge1000_maximum_rows": (
                1_543 if count == PRIMARY_PROTOTYPE_COUNT else None
            ),
            "conditioned_path_ge1000_maximum_fraction": (
                1_543 / PRIMARY_PROTOTYPE_COUNT
                if count == PRIMARY_PROTOTYPE_COUNT
                else None
            ),
            "conditioned_path_ge2000_maximum_rows": (
                573 if count == PRIMARY_PROTOTYPE_COUNT else None
            ),
        },
        "replenishment_reserve_policy": (
            {
                "kind": (
                    "fixed_post_primary_residual_reserve_v1"
                ),
                "capacity_clamping": False,
                "launch": (
                    "only deficit-targeted rows after the primary "
                    "global realized audit"
                ),
                "cell_path_counts": {
                    f"{role}:{bucket}": value
                    for (role, bucket), value in sorted(
                        REPLENISHMENT_FIXED_CELL_PATH_COUNTS.items()
                    )
                },
                "planned_targets": (
                    REPLENISHMENT_FIXED_PLANNED_TARGETS
                ),
                "net_targets": REPLENISHMENT_FIXED_NET_TARGETS,
                "physical_targets": (
                    REPLENISHMENT_FIXED_PHYSICAL_TARGETS
                ),
                "action_cell_targets": (
                    {
                        f"{role}:{bucket}": targets
                        for (role, bucket), targets in sorted(
                            REPLENISHMENT_FIXED_ACTION_CELL_COUNTS.items()
                        )
                    }
                ),
                "feasibility_audit": (
                    replenishment_feasibility_reference()
                ),
            }
            if label == "replenishment"
            else None
        ),
    }
    return selected, audit


def physical_arity(row: dict[str, Any]) -> int:
    design = row["action_design"]
    return (
        int(design["locomotion_direction"] != "idle")
        + int(design["view_direction"] != "stationary")
        + int(bool(design.get("jump")))
    )


def _balanced_group_mode_counts(
    groups: list[dict[str, Any]],
    *,
    mode: str,
    total: int,
    cap: int,
    eligible: Any,
    seed: int,
) -> None:
    candidates = [
        group for group in groups if eligible(group["prototype"])
    ]
    if total > len(candidates) * cap:
        raise capture.CaptureFailure(
            "v5_semantic_action_capacity",
            capture.canonical_json(
                {
                    "mode": mode,
                    "need": total,
                    "groups": len(candidates),
                    "cap": cap,
                }
            ),
        )
    heap: list[tuple[int, int, str, int]] = []
    for index, group in enumerate(candidates):
        tie = hashlib.sha256(
            (
                f"{seed}:{mode}:"
                f"{group['prototype']['episode_id']}"
            ).encode()
        ).hexdigest()
        heap.append(
            (
                sum(group["counts"].values()),
                int(group["counts"].get(mode, 0)),
                tie,
                index,
            )
        )
    heapq.heapify(heap)
    for _ in range(total):
        if not heap:
            raise capture.CaptureFailure(
                "v5_semantic_action_heap_exhausted", mode
            )
        _, _, tie, index = heapq.heappop(heap)
        group = candidates[index]
        group["counts"][mode] = (
            int(group["counts"].get(mode, 0)) + 1
        )
        if group["counts"][mode] < cap:
            heapq.heappush(
                heap,
                (
                    sum(group["counts"].values()),
                    group["counts"][mode],
                    tie,
                    index,
                ),
            )


def _allocate_none_counts(
    groups: list[dict[str, Any]],
    total: int,
    seed: int,
) -> None:
    assigned = 0
    maximum_by_index: dict[int, int] = {}
    for index, group in enumerate(groups):
        action_count = sum(group["counts"].values())
        visible_collision = group["prototype"][
            "_certified_blockage"
        ].get("visible_collision_qualified", False)
        if visible_collision:
            minimum = 10 - action_count
            maximum = minimum
        else:
                                                                            
                                                                             
                                                                             
                                                                       
                              
            minimum = max(0, 9 - action_count)
            maximum = min(
                len(v4.WEAPONS),
                FORMAL_SEMANTIC_VARIANTS_MAX - action_count,
            )
        if (
            minimum < 0
            or maximum < minimum
            or maximum > len(v4.WEAPONS)
        ):
            raise capture.CaptureFailure(
                "v5_semantic_none_group_capacity",
                capture.canonical_json(
                    {
                        "prototype_id": group["prototype"][
                            "episode_id"
                        ],
                        "minimum": minimum,
                        "maximum": maximum,
                        "action_count": action_count,
                    }
                ),
            )
        group["counts"]["none"] = minimum
        maximum_by_index[index] = maximum
        assigned += minimum
    if assigned > total:
        raise capture.CaptureFailure(
            "v5_semantic_none_minimum_exceeds_target",
            f"minimum={assigned} target={total}",
        )
    heap: list[tuple[int, int, str, int]] = []
    for index, group in enumerate(groups):
        count = int(group["counts"]["none"])
        maximum = maximum_by_index[index]
        if count >= maximum:
            continue
        tie = hashlib.sha256(
            (
                f"{seed}:none:"
                f"{group['prototype']['episode_id']}"
            ).encode()
        ).hexdigest()
        heap.append(
            (
                sum(group["counts"].values()),
                count,
                tie,
                index,
            )
        )
    heapq.heapify(heap)
    for _ in range(total - assigned):
        if not heap:
            raise capture.CaptureFailure(
                "v5_semantic_none_capacity",
                f"need={total} assigned={assigned}",
            )
        _, _, tie, index = heapq.heappop(heap)
        group = groups[index]
        group["counts"]["none"] += 1
        if group["counts"]["none"] < maximum_by_index[index]:
            heapq.heappush(
                heap,
                (
                    sum(group["counts"].values()),
                    group["counts"]["none"],
                    tie,
                    index,
                ),
            )


def _allocate_semantic_counts(
    groups: list[dict[str, Any]],
    *,
    primary_target: int | None = None,
    reload_target: int | None = None,
    none_target: int | None = None,
    cell_targets: dict[
        tuple[str, str], dict[str, int]
    ] | None = None,
    distribution_constraints: list[
        tuple[str, Any, int, int]
    ] | None = None,
    mean_absolute_deviation_maximum: float | None = None,
    seed: int,
) -> dict[str, Any]:
    """Jointly allocate unique action modes and bounded path weights.

    Fire and reload eligibility overlap only partially.  Allocating them in
    separate greedy passes can concentrate both modes on the same paths even
    when the cell has a valid joint solution.  This integer program is the
    admission rule: it never changes a target and it either finds the exact
    declared counts or fails closed.
    """
    if not groups:
        raise capture.CaptureFailure(
            "v5_semantic_joint_allocation_empty_cell"
        )
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    size = len(groups)
    variable_count = size * 4
    fire_offset = 0
    reload_offset = size
    none_offset = size * 2
    deviation_offset = size * 3
    lower_bounds = np.zeros(variable_count, dtype=np.float64)
    upper_bounds = np.zeros(variable_count, dtype=np.float64)
    objective = np.zeros(variable_count, dtype=np.float64)
    integrality = np.zeros(variable_count, dtype=np.int8)
    integrality[: none_offset + size] = 1
    group_cells = [
        (
            str(group["prototype"]["dataset_role"]),
            str(group["prototype"]["primary_bucket"]),
        )
        for group in groups
    ]
    if cell_targets is None:
        unique_cells = set(group_cells)
        if (
            len(unique_cells) != 1
            or primary_target is None
            or reload_target is None
            or none_target is None
        ):
            raise AssertionError("invalid single-cell semantic allocation")
        only_cell = next(iter(unique_cells))
        targets_by_cell = {
            only_cell: {
                "environmental_primary": int(primary_target),
                "reload": int(reload_target),
                "none": int(none_target),
            }
        }
    else:
        targets_by_cell = {
            (str(cell[0]), str(cell[1])): {
                mode: int(targets[mode])
                for mode in (
                    "environmental_primary",
                    "reload",
                    "none",
                )
            }
            for cell, targets in cell_targets.items()
        }
        if set(group_cells) != set(targets_by_cell):
            raise AssertionError("semantic allocation cell mismatch")
    distribution_constraints = distribution_constraints or []
    deviation_maximum = (
        FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
        if mean_absolute_deviation_maximum is None
        else float(mean_absolute_deviation_maximum)
    )
    if deviation_maximum < 0:
        raise ValueError("negative semantic weight deviation maximum")

    for index, group in enumerate(groups):
        prototype = group["prototype"]
        low_arity = physical_arity(prototype) <= 2
        collision = bool(
            prototype["_certified_blockage"].get(
                "visible_collision_qualified", False
            )
        )
        safe_primary = (
            low_arity
            and not collision
            and (
                not prototype["enemy_present"]
                or prototype["scheduler_targets"]["target_relation"]
                in SAFE_PRIMARY_FIRE_RELATIONS
            )
        )
        upper_bounds[fire_offset + index] = (
            len(v4.WEAPONS) if safe_primary else 0
        )
        upper_bounds[reload_offset + index] = (
            len(v4.RELOAD_WEAPONS) if low_arity else 0
        )
        if collision:
            lower_bounds[reload_offset + index] = 1
        upper_bounds[none_offset + index] = len(v4.WEAPONS)
        upper_bounds[deviation_offset + index] = (
            FORMAL_SEMANTIC_VARIANTS_MAX
            - FORMAL_SEMANTIC_VARIANTS_MIN
        )
                                                                            
                                                                            
                                                                            
        objective[deviation_offset + index] = 1.0
        for mode_offset, mode in (
            (fire_offset, "environmental_primary"),
            (reload_offset, "reload"),
            (none_offset, "none"),
        ):
            objective[mode_offset + index] = (
                int(
                    hashlib.sha256(
                        (
                            f"{seed}:{mode}:"
                            f"{prototype['episode_id']}"
                        ).encode()
                    ).hexdigest()[:12],
                    16,
                )
                / float(16**12)
                * 1e-9
            )

    matrix_rows: list[int] = []
    matrix_columns: list[int] = []
    matrix_values: list[float] = []
    constraint_lower: list[float] = []
    constraint_upper: list[float] = []

    def add_constraint(
        coefficients: list[tuple[int, float]],
        lower: float,
        upper: float,
    ) -> None:
        row_index = len(constraint_lower)
        for column, value in coefficients:
            matrix_rows.append(row_index)
            matrix_columns.append(column)
            matrix_values.append(value)
        constraint_lower.append(lower)
        constraint_upper.append(upper)

    for cell, targets in sorted(targets_by_cell.items()):
        cell_indexes = [
            index
            for index, group_cell in enumerate(group_cells)
            if group_cell == cell
        ]
        for offset, mode in (
            (fire_offset, "environmental_primary"),
            (reload_offset, "reload"),
            (none_offset, "none"),
        ):
            target = targets[mode]
            add_constraint(
                [
                    (offset + index, 1.0)
                    for index in cell_indexes
                ],
                float(target),
                float(target),
            )

    for index, group in enumerate(groups):
        weight_columns = [
            (fire_offset + index, 1.0),
            (reload_offset + index, 1.0),
            (none_offset + index, 1.0),
        ]
        collision = bool(
            group["prototype"]["_certified_blockage"].get(
                "visible_collision_qualified", False
            )
        )
        minimum_weight = (
            SEMANTIC_VARIANTS_PER_PROTOTYPE
            if collision
            else FORMAL_SEMANTIC_VARIANTS_MIN
        )
        maximum_weight = (
            SEMANTIC_VARIANTS_PER_PROTOTYPE
            if collision
            else FORMAL_SEMANTIC_VARIANTS_MAX
        )
        add_constraint(
            weight_columns,
            float(minimum_weight),
            float(maximum_weight),
        )
                                  
        add_constraint(
            [
                *weight_columns,
                (deviation_offset + index, -1.0),
            ],
            -np.inf,
            float(SEMANTIC_VARIANTS_PER_PROTOTYPE),
        )
                                  
        add_constraint(
            [
                *weight_columns,
                (deviation_offset + index, 1.0),
            ],
            float(SEMANTIC_VARIANTS_PER_PROTOTYPE),
            np.inf,
        )

    feasibility_only = len(targets_by_cell) > 1
    if feasibility_only:
        add_constraint(
            [
                (deviation_offset + index, 1.0)
                for index in range(size)
            ],
            0.0,
            float(
                math.ceil(
                    size
                    * deviation_maximum
                )
            ),
        )

    for _, predicate, lower, upper in distribution_constraints:
        coefficients: list[tuple[int, float]] = []
        for index, group in enumerate(groups):
            if not predicate(group["prototype"]):
                continue
            coefficients.extend(
                (
                    (fire_offset + index, 1.0),
                    (reload_offset + index, 1.0),
                    (none_offset + index, 1.0),
                )
            )
        add_constraint(
            coefficients, float(lower), float(upper)
        )

    matrix = coo_matrix(
        (
            np.asarray(matrix_values, dtype=np.float64),
            (
                np.asarray(matrix_rows, dtype=np.int32),
                np.asarray(matrix_columns, dtype=np.int32),
            ),
        ),
        shape=(len(constraint_lower), variable_count),
    ).tocsr()
    if feasibility_only:
                                                                            
                                                                           
                                                                           
                                                            
        objective.fill(0.0)
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(
            matrix,
            np.asarray(constraint_lower, dtype=np.float64),
            np.asarray(constraint_upper, dtype=np.float64),
        ),
        options={
            "time_limit": (
                120.0 if len(targets_by_cell) > 1 else 30.0
            ),
            "mip_rel_gap": 0.0,
        },
    )
    if not result.success or result.x is None:
        raise capture.CaptureFailure(
            "v5_semantic_joint_allocation_infeasible",
            capture.canonical_json(
                {
                    "cells": [
                        list(cell) for cell in sorted(targets_by_cell)
                    ],
                    "paths": size,
                    "targets": {
                        f"{cell[0]}:{cell[1]}": targets
                        for cell, targets in sorted(
                            targets_by_cell.items()
                        )
                    },
                    "solver_status": int(result.status),
                    "solver_message": str(result.message),
                }
            ),
        )

    values = np.rint(result.x[: none_offset + size]).astype(int)
    fire = values[fire_offset:reload_offset]
    reloads = values[reload_offset:none_offset]
    none = values[none_offset:none_offset + size]
    for cell, targets in targets_by_cell.items():
        indexes = [
            index
            for index, group_cell in enumerate(group_cells)
            if group_cell == cell
        ]
        observed = {
            "environmental_primary": int(fire[indexes].sum()),
            "reload": int(reloads[indexes].sum()),
            "none": int(none[indexes].sum()),
        }
        if observed != targets:
            raise capture.CaptureFailure(
                "v5_semantic_joint_allocation_rounding",
                capture.canonical_json(
                    {
                        "cell": cell,
                        "expected": targets,
                        "observed": observed,
                    }
                ),
            )
    weights: list[int] = []
    for index, group in enumerate(groups):
        counts = {
            "environmental_primary": int(fire[index]),
            "reload": int(reloads[index]),
            "none": int(none[index]),
        }
        group["counts"] = {
            mode: count for mode, count in counts.items() if count
        }
        weight = sum(counts.values())
        collision = bool(
            group["prototype"]["_certified_blockage"].get(
                "visible_collision_qualified", False
            )
        )
        if (
            counts["environmental_primary"] > len(v4.WEAPONS)
            or counts["reload"] > len(v4.RELOAD_WEAPONS)
            or counts["none"] > len(v4.WEAPONS)
            or (collision and weight != SEMANTIC_VARIANTS_PER_PROTOTYPE)
            or (
                not collision
                and not (
                    FORMAL_SEMANTIC_VARIANTS_MIN
                    <= weight
                    <= FORMAL_SEMANTIC_VARIANTS_MAX
                )
            )
        ):
            raise capture.CaptureFailure(
                "v5_semantic_joint_allocation_contract",
                group["prototype"]["episode_id"],
            )
        weights.append(weight)
    cell_reports = []
    for cell, targets in sorted(targets_by_cell.items()):
        indexes = [
            index
            for index, group_cell in enumerate(group_cells)
            if group_cell == cell
        ]
        cell_weights = [weights[index] for index in indexes]
        cell_reports.append(
            {
                "cell": list(cell),
                "paths": len(indexes),
                "targets": targets,
                "weight_counts": {
                    str(weight): count
                    for weight, count in sorted(
                        Counter(cell_weights).items()
                    )
                },
                "minimum_weight": min(cell_weights),
                "maximum_weight": max(cell_weights),
                "absolute_deviation_from_ten": sum(
                    abs(
                        weight
                        - SEMANTIC_VARIANTS_PER_PROTOTYPE
                    )
                    for weight in cell_weights
                ),
            }
        )
    distribution_report = []
    for name, predicate, lower, upper in distribution_constraints:
        observed = sum(
            weights[index]
            for index, group in enumerate(groups)
            if predicate(group["prototype"])
        )
        distribution_report.append(
            {
                "name": name,
                "lower": lower,
                "upper": upper,
                "observed": observed,
                "passed": lower <= observed <= upper,
            }
        )
    report = {
        "paths": size,
        "passed": True,
        "cells": cell_reports,
        "weight_counts": {
            str(weight): count
            for weight, count in sorted(Counter(weights).items())
        },
        "minimum_weight": min(weights),
        "maximum_weight": max(weights),
        "absolute_deviation_from_ten": sum(
            abs(weight - SEMANTIC_VARIANTS_PER_PROTOTYPE)
            for weight in weights
        ),
        "solver_status": int(result.status),
        "solver_message": str(result.message),
        "solver_objective": (
            "feasibility_only"
            if feasibility_only
            else "minimum_absolute_deviation_from_ten"
        ),
        "mean_absolute_deviation_from_ten": (
            sum(
                abs(
                    weight
                    - SEMANTIC_VARIANTS_PER_PROTOTYPE
                )
                for weight in weights
            )
            / size
        ),
        "mean_absolute_deviation_maximum": (
            deviation_maximum
            if feasibility_only
            else None
        ),
        "distribution_constraints": distribution_report,
    }
    if len(cell_reports) == 1:
        report.update(cell_reports[0])
    return report


def _balanced_weapon_targets(
    total: int,
    weapons: tuple[str, ...],
    seed: int,
) -> Counter[str]:
    rng = random.Random(seed)
    values = v4.balanced_values(total, weapons, rng)
    return Counter(values)


def _assign_mode_weapons(
    groups: list[dict[str, Any]],
    *,
    mode: str,
    role: str,
    targets: Counter[str],
    eligible_weapons: tuple[str, ...],
    seed: int,
) -> None:
    selected = [
        group
        for group in groups
        if group["prototype"]["dataset_role"] == role
        and int(group["counts"].get(mode, 0)) > 0
    ]
    degree_total = sum(
        int(group["counts"][mode]) for group in selected
    )
    if degree_total != sum(targets.values()):
        raise AssertionError((mode, role, degree_total, targets))
    if any(
        targets[weapon] > len(selected) for weapon in eligible_weapons
    ):
        raise capture.CaptureFailure(
            "v5_semantic_weapon_group_capacity",
            capture.canonical_json(
                {
                    "mode": mode,
                    "role": role,
                    "groups": len(selected),
                    "targets": dict(targets),
                }
            ),
        )
    remaining = Counter(targets)
    selected.sort(
        key=lambda group: (
            -int(group["counts"][mode]),
            hashlib.sha256(
                (
                    f"{seed}:{mode}:{role}:"
                    f"{group['prototype']['episode_id']}"
                ).encode()
            ).hexdigest(),
        )
    )
    for group in selected:
        wanted = int(group["counts"][mode])
        ordered = sorted(
            eligible_weapons,
            key=lambda weapon: (
                -remaining[weapon],
                hashlib.sha256(
                    (
                        f"{seed}:{mode}:{role}:"
                        f"{group['prototype']['episode_id']}:"
                        f"{weapon}"
                    ).encode()
                ).hexdigest(),
            ),
        )
        chosen = [
            weapon for weapon in ordered if remaining[weapon] > 0
        ][:wanted]
        if len(chosen) != wanted:
            raise capture.CaptureFailure(
                "v5_semantic_weapon_assignment_infeasible",
                capture.canonical_json(
                    {
                        "mode": mode,
                        "role": role,
                        "prototype_id": group["prototype"][
                            "episode_id"
                        ],
                        "wanted": wanted,
                        "remaining": dict(remaining),
                    }
                ),
            )
        group["weapons"][mode] = chosen
        remaining.subtract(chosen)
    if any(remaining.values()):
        raise capture.CaptureFailure(
            "v5_semantic_weapon_assignment_residual",
            capture.canonical_json(
                {
                    "mode": mode,
                    "role": role,
                    "remaining": dict(remaining),
                }
            ),
        )


def _apply_semantic_variant(
    prototype: dict[str, Any],
    reference: dict[str, Any],
    *,
    mode: str,
    weapon: str,
    episode_id: str,
    ordinal: int,
    wave: str,
    variant_index: int,
) -> dict[str, Any]:
    row = copy.deepcopy(prototype)
    prototype_data_spec_sha256 = str(
        row.get("data_spec_sha256", "")
    )
    if (
        len(prototype_data_spec_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in prototype_data_spec_sha256
        )
    ):
        raise capture.CaptureFailure(
            "v5_path_prototype_data_spec_reference_invalid",
            prototype["episode_id"],
        )
    row.pop("_player_path_certificate", None)
    row.pop("_certified_motion", None)
    row.pop("_certified_blockage", None)
    row["source_prototype_id"] = prototype["episode_id"]
    row["episode_id"] = episode_id
    row["anchor_id"] = (
        f"{row['map']}_{episode_id}_pair"
        if row["enemy_present"]
        else f"{row['map']}_{episode_id}_solo"
    )
    row["split"] = row["dataset_role"]
    row["category"] = row["primary_bucket"]
    row["target_bin"] = row["dataset_role"]
    row["candidate_wave"] = wave
    row["candidate_ordinal"] = ordinal
    row["assigned_shard"] = (ordinal - 1) % SHARD_COUNT
    row["shard_count"] = SHARD_COUNT
    row["formal_collection_authorized"] = True
    row["formal_authorization_basis"] = (
        "v5_authoritative_player_path_certificate_exact_runtime_"
        "compatibility_and_quota_milp"
    )
    row["training_admitted"] = False
    row["path_prototype_data_spec_sha256"] = (
        prototype_data_spec_sha256
    )
    row["data_spec_sha256"] = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    row["source_commit_required"] = RUNTIME_SOURCE_COMMIT
    row["weapon"] = weapon
    row["weapon_netname"] = capture.WEAPON_NETNAME[weapon]
    row["player"]["clip"] = 60.0
    row["action_design"]["weapon_action"] = mode
    arity = physical_arity(row) + int(mode != "none")
    if arity > 3:
        raise capture.CaptureFailure(
            "v5_semantic_action_arity_exceeded",
            f"prototype={prototype['episode_id']} arity={arity}",
        )
    row["action_design"]["action_arity"] = {
        0: "idle",
        1: "atomic",
        2: "pairwise",
        3: "three_way",
    }[arity]
    row["acceptance"] = {
        "actual_outcome": None,
        "fire_required": mode == "environmental_primary",
        "reload_success": mode == "reload",
    }
    if mode == "reload":
        row["player"]["clip"] = v4.RELOAD_INITIAL_CLIP[weapon]
        row["acceptance"].update(
            {
                "reload_weapon": capture.WEAPON_NETNAME[weapon],
                "reload_initial_clip": v4.RELOAD_INITIAL_CLIP[
                    weapon
                ],
                "reload_clip_capacity": v4.RELOAD_CAPACITY[weapon],
                "reload_start_server_tick": (
                    capture.WARMUP_TICKS
                    + capture.STAGE1_RELOAD_START_OUTPUT_TICK
                ),
                "reload_duration_ticks": (
                    capture.STAGE1_RELOAD_DURATION_TICKS
                ),
            }
        )
    if mode != "none":
        row["expects_sound"] = True
    row["player_path_certificate"] = copy.deepcopy(reference)
    row["player_path_runtime_compatibility"] = (
        copy.deepcopy(player_path_runtime_compatibility_reference())
    )
    row["semantic_variant"] = {
        "schema_version": "xonotic-stage1-v5-semantic-variant-v1",
        "source_prototype_id": prototype["episode_id"],
        "variant_index": variant_index,
        "weapon": weapon,
        "weapon_action": mode,
        "physical_schedule_mutated": False,
    }
    row["certified_realized_motion"] = copy.deepcopy(
        prototype["_certified_motion"]
    )
    row["certified_collision"] = copy.deepcopy(
        prototype["_certified_blockage"]
    )
    audio_expectation = capture.stage1_audio_expectation(row)
    row["expects_sound"] = audio_expectation["expects_sound"]
    row["audio_expectation_policy"] = audio_expectation
    row["counterfactual_group_id"] = prototype["episode_id"]
    return row


def _semantic_distribution_constraints(
    selected: list[dict[str, Any]],
    *,
    action_scale: int,
) -> list[tuple[str, Any, int, int]]:
    """Return the fixed row-level distribution envelope for one wave."""
    replenishment = action_scale == v4.REPLENISHMENT_SCALE
    expected = v4.PRIMARY_COUNT // action_scale
    constraints: list[tuple[str, Any, int, int]] = []

    def add(
        name: str,
        predicate: Any,
        target: int,
        tolerance: float,
        *,
        minimum_slack: int = 0,
    ) -> None:
        slack = max(
            minimum_slack, math.ceil(target * tolerance)
        )
        constraints.append(
            (
                name,
                predicate,
                max(0, target - slack),
                target + slack,
            )
        )

    expected_physical = (
        {
            field: {
                value: count * SEMANTIC_VARIANTS_PER_PROTOTYPE
                for value, count in targets.items()
            }
            for field, targets in (
                REPLENISHMENT_FIXED_PHYSICAL_TARGETS.items()
            )
        }
        if replenishment
        else PHYSICAL_MARGINAL_BASELINE
    )
    for field, targets in expected_physical.items():
        for value, target in targets.items():
            add(
                f"physical:{field}:{value}",
                lambda row, field=field, value=value: (
                    row["action_design"].get(field) == value
                ),
                target,
                FORMAL_SEMANTIC_MARGINAL_TOLERANCE,
                minimum_slack=1,
            )

    expected_planned = (
        {
            axis: {
                value: count * SEMANTIC_VARIANTS_PER_PROTOTYPE
                for value, count in targets.items()
            }
            for axis, targets in (
                REPLENISHMENT_FIXED_PLANNED_TARGETS.items()
            )
        }
        if replenishment
        else {
            "target_relation": dict(v4.RELATION_COUNTS),
            "distance": dict(v4.DISTANCE_COUNTS),
            "enemy_policy": dict(v4.ENEMY_POLICY_COUNTS),
        }
    )
    planned_getters = {
        "target_relation": lambda row: (
            row.get("scheduler_targets") or {}
        ).get("target_relation"),
        "distance": lambda row: (
            row.get("scheduler_targets") or {}
        ).get("distance_bin"),
        "enemy_policy": lambda row: (
            row.get("enemy_policy") or {}
        ).get("name"),
    }
    for axis, targets in expected_planned.items():
        getter = planned_getters[axis]
        for value, target in targets.items():
            add(
                f"planned:{axis}:{value}",
                lambda row, getter=getter, value=value: (
                    row.get("enemy_present") is True
                    and getter(row) == value
                ),
                target,
                FORMAL_SEMANTIC_PLANNED_TOLERANCE,
                minimum_slack=10,
            )

    expected_realized = {
        "net_displacement_bin": (
            {
                value: count * SEMANTIC_VARIANTS_PER_PROTOTYPE
                for value, count in (
                    REPLENISHMENT_FIXED_NET_TARGETS.items()
                )
            }
            if replenishment
            else dict(v4.NET_COUNTS)
        ),
        "yaw_range_bin": {
            value: count // action_scale
            for value, count in v4.YAW_COUNTS.items()
        },
        "pitch_range_bin": {
            value: count // action_scale
            for value, count in v4.PITCH_COUNTS.items()
        },
    }
    for metric, targets in expected_realized.items():
        for value, target in targets.items():
            add(
                f"realized:{metric}:{value}",
                lambda row, metric=metric, value=value: (
                    row["_certified_motion"][metric] == value
                ),
                target,
                FORMAL_SEMANTIC_MARGINAL_TOLERANCE,
            )

    constraints.extend(
        (
            (
                "floor:path_ge1000",
                lambda row: row["_certified_motion"][
                    "path_length_3d"
                ]
                >= 1_000,
                math.ceil(
                    expected
                    * FORMAL_SEMANTIC_PATH_GE1000_MIN_FRACTION
                ),
                expected,
            ),
            (
                "floor:path_ge2000",
                lambda row: row["_certified_motion"][
                    "path_length_3d"
                ]
                >= 2_000,
                math.ceil(
                    expected
                    * FORMAL_SEMANTIC_PATH_GE2000_MIN_FRACTION
                ),
                expected,
            ),
            (
                "floor:joint_net512_yaw90",
                lambda row: (
                    row["_certified_motion"][
                        "net_displacement_3d"
                    ]
                    >= 512
                    and row["_certified_motion"]["yaw_range_deg"]
                    >= 90
                ),
                math.ceil(
                    expected
                    * FORMAL_SEMANTIC_JOINT_MIN_FRACTION
                ),
                expected,
            ),
        )
    )
    return constraints


def expand_semantic_variants(
    selected: list[dict[str, Any]],
    *,
    wave: str,
    action_scale: int,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups = [
        {
            "prototype": row,
            "counts": {},
            "weapons": {},
        }
        for row in selected
    ]
    by_cell: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for group in groups:
        prototype = group["prototype"]
        by_cell[
            (
                prototype["dataset_role"],
                prototype["primary_bucket"],
            )
        ].append(group)
    targets_by_cell: dict[
        tuple[str, str], dict[str, int]
    ] = {}
    for cell, cell_groups in sorted(by_cell.items()):
        target_rows = len(cell_groups) * SEMANTIC_VARIANTS_PER_PROTOTYPE
        targets = semantic_action_cell_targets(
            cell,
            target_rows,
            replenishment=(wave == "replenishment"),
        )
        targets_by_cell[cell] = targets
    allocation_audit = _allocate_semantic_counts(
        groups,
        cell_targets=targets_by_cell,
        distribution_constraints=_semantic_distribution_constraints(
            selected, action_scale=action_scale
        ),
        seed=seed,
    )
    for cell, cell_groups in sorted(by_cell.items()):
        target_rows = len(cell_groups) * SEMANTIC_VARIANTS_PER_PROTOTYPE
        if (
            sum(sum(group["counts"].values()) for group in cell_groups)
            != target_rows
        ):
            raise AssertionError(cell)

    for role_index, role in enumerate(v4.ROLE_COUNTS):
        role_groups = [
            group
            for group in groups
            if group["prototype"]["dataset_role"] == role
        ]
        for mode_index, (mode, weapons) in enumerate(
            (
                ("none", v4.WEAPONS),
                ("environmental_primary", v4.WEAPONS),
                ("reload", v4.RELOAD_WEAPONS),
            )
        ):
            total = sum(
                int(group["counts"].get(mode, 0))
                for group in role_groups
            )
            targets = _balanced_weapon_targets(
                total,
                tuple(weapons),
                seed + role_index * 100 + mode_index,
            )
            _assign_mode_weapons(
                groups,
                mode=mode,
                role=role,
                targets=targets,
                eligible_weapons=tuple(weapons),
                seed=seed + role_index * 100 + mode_index,
            )

    rows: list[dict[str, Any]] = []
    prefix = "s1v5f" if wave == "primary" else "s1v5x"
    ordinal = 0
    for group in sorted(
        groups, key=lambda item: item["prototype"]["episode_id"]
    ):
        prototype = group["prototype"]
        variants = [
            (mode, weapon)
            for mode in (
                "none",
                "environmental_primary",
                "reload",
            )
            for weapon in group["weapons"].get(mode, [])
        ]
        if len(variants) != sum(group["counts"].values()):
            raise AssertionError(prototype["episode_id"])
        variants.sort(
            key=lambda value: hashlib.sha256(
                (
                    f"{seed}:{prototype['episode_id']}:"
                    f"{value[0]}:{value[1]}"
                ).encode()
            ).hexdigest()
        )
        if len(variants) != len(set(variants)):
            raise capture.CaptureFailure(
                "v5_duplicate_semantic_variant",
                prototype["episode_id"],
            )
        for variant_index, (mode, weapon) in enumerate(variants):
            ordinal += 1
            episode_id = (
                f"{prefix}_{prototype['episode_id']}_v"
                f"{variant_index:02d}"
            )
            rows.append(
                _apply_semantic_variant(
                    prototype,
                    prototype["_player_path_certificate"],
                    mode=mode,
                    weapon=weapon,
                    episode_id=episode_id,
                    ordinal=ordinal,
                    wave=wave,
                    variant_index=variant_index,
                )
            )
    expected = v4.PRIMARY_COUNT // action_scale
    if len(rows) != expected:
        raise AssertionError((wave, len(rows), expected))
    audit = audit_formal_rows(rows, expected, action_scale)
    audit["semantic_count_allocation"] = {
        "method": "joint_integer_allocation",
        "capacity_clamping": False,
        **allocation_audit,
    }
    return rows, audit


def audit_formal_rows(
    rows: list[dict[str, Any]],
    expected: int,
    action_scale: int,
) -> dict[str, Any]:
    replenishment = action_scale == v4.REPLENISHMENT_SCALE
    expected_runtime_compatibility = (
        player_path_runtime_compatibility_reference()
    )
    counts = Counter(
        row["action_design"]["weapon_action"] for row in rows
    )
    actual_net = Counter(
        row["certified_realized_motion"]["net_displacement_bin"]
        for row in rows
    )
    actual_yaw = Counter(
        row["certified_realized_motion"]["yaw_range_bin"]
        for row in rows
    )
    actual_pitch = Counter(
        row["certified_realized_motion"]["pitch_range_bin"]
        for row in rows
    )
    planned_relation = Counter(
        row["scheduler_targets"]["target_relation"]
        for row in rows
        if row["enemy_present"]
    )
    planned_distance = Counter(
        row["scheduler_targets"]["distance_bin"]
        for row in rows
        if row["enemy_present"]
    )
    planned_enemy_policy = Counter(
        row["enemy_policy"]["name"]
        for row in rows
        if row["enemy_present"]
    )
    held = Counter(row["weapon"] for row in rows)
    maps = Counter(row["map"] for row in rows)
    gametypes = Counter(row["gametype"] for row in rows)
    primary = Counter(
        row["weapon"]
        for row in rows
        if row["action_design"]["weapon_action"]
        == "environmental_primary"
    )
    reloads = Counter(
        row["weapon"]
        for row in rows
        if row["action_design"]["weapon_action"] == "reload"
    )
    action_cells = Counter(
        (
            row["dataset_role"],
            row["primary_bucket"],
            row["action_design"]["weapon_action"],
        )
        for row in rows
    )
    expected_action_cells: Counter[
        tuple[str, str, str]
    ] = Counter()
    expected_cell_rows: dict[tuple[str, str], int] = {}
    for role, bucket in PRIMARY_ACTION_CELL_COUNTS:
        cell = (role, bucket)
        total = (
            REPLENISHMENT_FIXED_CELL_PATH_COUNTS[cell]
            * SEMANTIC_VARIANTS_PER_PROTOTYPE
            if replenishment
            else v4.BUCKET_ROLE_COUNTS[bucket][role]
        )
        expected_cell_rows[cell] = total
        targets = semantic_action_cell_targets(
            cell, total, replenishment=replenishment
        )
        for mode, count in targets.items():
            expected_action_cells[(role, bucket, mode)] = count
    expected_role_counts = Counter()
    expected_bucket_counts = Counter()
    for (role, bucket), count in expected_cell_rows.items():
        expected_role_counts[role] += count
        expected_bucket_counts[bucket] += count
    expected_weapon_action_counts = Counter()
    for (_, _, mode), count in expected_action_cells.items():
        expected_weapon_action_counts[mode] += count
    expected_planned_targets = {
        axis: {
            name: count * SEMANTIC_VARIANTS_PER_PROTOTYPE
            for name, count in targets.items()
        }
        for axis, targets in REPLENISHMENT_FIXED_PLANNED_TARGETS.items()
    } if replenishment else {
        "target_relation": dict(v4.RELATION_COUNTS),
        "distance": dict(v4.DISTANCE_COUNTS),
        "enemy_policy": dict(v4.ENEMY_POLICY_COUNTS),
    }
    expected_realized_targets = {
        "net": (
            {
                name: count * SEMANTIC_VARIANTS_PER_PROTOTYPE
                for name, count in REPLENISHMENT_FIXED_NET_TARGETS.items()
            }
            if replenishment
            else dict(v4.NET_COUNTS)
        ),
        "yaw": {
            name: count // action_scale
            for name, count in v4.YAW_COUNTS.items()
        },
        "pitch": {
            name: count // action_scale
            for name, count in v4.PITCH_COUNTS.items()
        },
    }
    expected_physical_targets = (
        {
            field: {
                value: count * SEMANTIC_VARIANTS_PER_PROTOTYPE
                for value, count in targets.items()
            }
            for field, targets in (
                REPLENISHMENT_FIXED_PHYSICAL_TARGETS.items()
            )
        }
        if replenishment
        else PHYSICAL_MARGINAL_BASELINE
    )
    physical_marginals = {
        field: Counter(
            row["action_design"].get(field) for row in rows
        )
        for field in PHYSICAL_MARGINAL_BASELINE
    }

    def within_realized(
        observed: Counter[str],
        target: dict[str, int],
        tolerance_fraction: float = (
            FORMAL_SEMANTIC_MARGINAL_TOLERANCE
        ),
    ) -> bool:
        return all(
            abs(observed[name] - value)
            <= math.ceil(value * tolerance_fraction)
            for name, value in target.items()
        )

    def within_planned_enemy(
        observed: Counter[str],
        target: dict[str, int],
        tolerance_fraction: float,
    ) -> bool:
        if set(observed) != set(target):
            return False
        return all(
            abs(observed[name] - value)
            <= max(
                10,
                math.ceil(value * tolerance_fraction),
            )
            for name, value in target.items()
        )

    def within_physical_marginal(
        field: str,
    ) -> bool:
        observed = physical_marginals[field]
        return all(
            abs(observed[value] - target)
            <= max(
                1,
                math.ceil(
                    target * FORMAL_SEMANTIC_MARGINAL_TOLERANCE
                ),
            )
            for value, target in (
                expected_physical_targets[field].items()
            )
        )

    duplicate_pairs = Counter(
        (
            row["source_prototype_id"],
            row["weapon"],
            row["action_design"]["weapon_action"],
        )
        for row in rows
    )
    visible_collision_variant_counts = Counter(
        row["source_prototype_id"]
        for row in rows
        if row["certified_collision"].get(
            "visible_collision_qualified"
        )
        is True
    )
    semantic_variant_counts = Counter(
        row["source_prototype_id"] for row in rows
    )
    current_data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    checks = {
        "rows": len(rows) == expected,
        "ids_unique": len({row["episode_id"] for row in rows})
        == expected,
        "formal_authorized_not_preadmitted": all(
            row["formal_collection_authorized"] is True
            and row["training_admitted"] is False
            for row in rows
        ),
        "formal_data_spec_reference": all(
            row.get("data_spec_sha256")
            == current_data_spec_sha256
            for row in rows
        ),
        "path_prototype_data_spec_reference_preserved": all(
            isinstance(
                row.get("path_prototype_data_spec_sha256"), str
            )
            and len(row["path_prototype_data_spec_sha256"]) == 64
            and all(
                character in "0123456789abcdef"
                for character in row[
                    "path_prototype_data_spec_sha256"
                ]
            )
            for row in rows
        ),
        "all_admitted_maps_covered": (
            set(maps) == set(v4.formal_maps())
        ),
        "role_counts": Counter(
            row["dataset_role"] for row in rows
        )
        == expected_role_counts,
        "bucket_counts": Counter(
            row["primary_bucket"] for row in rows
        )
        == expected_bucket_counts,
        "weapon_action_counts": counts == expected_weapon_action_counts,
        "weapon_action_role_bucket_cells": (
            action_cells == expected_action_cells
        ),
        "secondary_absent": all(
            row["action_design"]["weapon_action"]
            != "environmental_secondary"
            for row in rows
        ),
        "action_arity_lte_three": all(
            row["action_design"]["action_arity"]
            in {"idle", "atomic", "pairwise", "three_way"}
            for row in rows
        ),
        "semantic_variants_unique_per_path": max(
            duplicate_pairs.values(), default=0
        )
        == 1,
        "semantic_variant_weight_within_fixed_bounds": (
            min(semantic_variant_counts.values(), default=0)
            >= FORMAL_SEMANTIC_VARIANTS_MIN
            and max(semantic_variant_counts.values(), default=0)
            <= FORMAL_SEMANTIC_VARIANTS_MAX
        ),
        "semantic_variant_mean_absolute_deviation": (
            sum(
                abs(
                    count - SEMANTIC_VARIANTS_PER_PROTOTYPE
                )
                for count in semantic_variant_counts.values()
            )
            <= math.ceil(
                len(semantic_variant_counts)
                * FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
            )
        ),
        "primary_safe_enemy_relation": all(
            not row["enemy_present"]
            or row["scheduler_targets"]["target_relation"]
            in {
                "offscreen_or_occluded",
                "visible_far",
                "near_crosshair",
            }
            for row in rows
            if row["action_design"]["weapon_action"]
            == "environmental_primary"
        ),
        "primary_avoids_visible_wall_contact": all(
            not row["certified_collision"].get(
                "visible_collision_qualified", False
            )
            for row in rows
            if row["action_design"]["weapon_action"]
            == "environmental_primary"
        ),
        "reload_weapon_contract": set(reloads)
        == set(v4.RELOAD_WEAPONS),
        "primary_weapon_contract": set(primary) == set(v4.WEAPONS),
        "held_weapon_approx_uniform": (
            max(held.values()) - min(held.values())
            <= math.ceil(expected / len(v4.WEAPONS) * 0.10)
        ),
        "primary_weapon_approx_uniform": (
            max(primary.values()) - min(primary.values()) <= 2
        ),
        "reload_weapon_uniform": (
            max(reloads.values()) - min(reloads.values()) <= 2
        ),
        "planned_relation_within_semantic_envelope": within_planned_enemy(
            planned_relation,
            expected_planned_targets["target_relation"],
            FORMAL_SEMANTIC_PLANNED_TOLERANCE,
        ),
        "planned_distance_within_semantic_envelope": within_planned_enemy(
            planned_distance,
            expected_planned_targets["distance"],
            FORMAL_SEMANTIC_PLANNED_TOLERANCE,
        ),
        "planned_enemy_policy_within_semantic_envelope": (
            within_planned_enemy(
                planned_enemy_policy,
                expected_planned_targets["enemy_policy"],
                FORMAL_SEMANTIC_PLANNED_TOLERANCE,
            )
        ),
        "actual_net_within_semantic_envelope": within_realized(
            actual_net,
            expected_realized_targets["net"],
        ),
        "actual_yaw_within_semantic_envelope": within_realized(
            actual_yaw, expected_realized_targets["yaw"]
        ),
        "actual_pitch_within_semantic_envelope": within_realized(
            actual_pitch, expected_realized_targets["pitch"]
        ),
        "physical_marginals_within_semantic_envelope": all(
            within_physical_marginal(field)
            for field in PHYSICAL_MARGINAL_BASELINE
        ),
        "physical_direction_categories_covered": all(
            physical_marginals[field][value] > 0
            for field in (
                "locomotion_direction",
                "view_direction",
            )
            for value in PHYSICAL_MARGINAL_BASELINE[field]
        ),
        "path_ge1000": sum(
            row["certified_realized_motion"]["path_length_3d"]
            >= 1_000
            for row in rows
        )
        >= math.ceil(
            expected * FORMAL_SEMANTIC_PATH_GE1000_MIN_FRACTION
        ),
        "path_ge2000": sum(
            row["certified_realized_motion"]["path_length_3d"]
            >= 2_000
            for row in rows
        )
        >= math.ceil(
            expected * FORMAL_SEMANTIC_PATH_GE2000_MIN_FRACTION
        ),
        "joint_net512_yaw90": sum(
            row["certified_realized_motion"][
                "net_displacement_3d"
            ]
            >= 512
            and row["certified_realized_motion"]["yaw_range_deg"]
            >= 90
            for row in rows
        )
        >= math.ceil(
            expected * FORMAL_SEMANTIC_JOINT_MIN_FRACTION
        ),
        "visible_wall_contact_1_to_3pct": (
            math.ceil(expected * 0.01)
            <= sum(
                row["certified_collision"].get(
                    "visible_collision_qualified"
                )
                is True
                for row in rows
            )
            <= math.floor(expected * 0.03)
        ),
        "visible_wall_contact_exact_ten_variants": all(
            count == SEMANTIC_VARIANTS_PER_PROTOTYPE
            for count in visible_collision_variant_counts.values()
        ),
        "certificate_reference": all(
            row["player_path_certificate"]["certified"] is True
            and row["player_path_certificate"]["source_commit"]
            == EXPECTED_SOURCE_COMMIT
            for row in rows
        ),
        "runtime_source_and_compatibility": all(
            row["source_commit_required"] == RUNTIME_SOURCE_COMMIT
            and row.get("player_path_runtime_compatibility")
            == expected_runtime_compatibility
            for row in rows
        ),
        "no_runtime_fallback": all(
            row["player_path_generation"][
                "runtime_geometry_fallback"
            ]
            is False
            and row["player_path_generation"][
                "runtime_action_fallback"
            ]
            is False
            for row in rows
        ),
        "shards": all(
            row["assigned_shard"]
            == (row["candidate_ordinal"] - 1) % SHARD_COUNT
            and row["shard_count"] == SHARD_COUNT
            for row in rows
        ),
    }
    report = {
        "checks": checks,
        "distribution_policy": {
            "wave": (
                "replenishment_residual_reserve"
                if replenishment
                else "primary"
            ),
            "capacity_clamping": False,
            "expected_cell_rows": {
                f"{role}:{bucket}": count
                for (role, bucket), count in sorted(
                    expected_cell_rows.items()
                )
            },
            "expected_planned_targets": expected_planned_targets,
            "expected_realized_targets": expected_realized_targets,
            "expected_physical_targets": {
                field: {
                    str(value): count
                    for value, count in targets.items()
                }
                for field, targets in expected_physical_targets.items()
            },
            "prototype_selection_marginal_tolerance_fraction": (
                REALIZED_MARGINAL_TOLERANCE
            ),
            "semantic_row_marginal_tolerance_fraction": (
                FORMAL_SEMANTIC_MARGINAL_TOLERANCE
            ),
            "semantic_row_planned_tolerance_fraction": (
                FORMAL_SEMANTIC_PLANNED_TOLERANCE
            ),
            "semantic_row_path_ge1000_min_fraction": (
                FORMAL_SEMANTIC_PATH_GE1000_MIN_FRACTION
            ),
            "semantic_row_path_ge2000_min_fraction": (
                FORMAL_SEMANTIC_PATH_GE2000_MIN_FRACTION
            ),
            "semantic_row_joint_min_fraction": (
                FORMAL_SEMANTIC_JOINT_MIN_FRACTION
            ),
            "semantic_variants_per_prototype": {
                "minimum": FORMAL_SEMANTIC_VARIANTS_MIN,
                "maximum": FORMAL_SEMANTIC_VARIANTS_MAX,
                "mean_absolute_deviation_maximum": (
                    FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
                ),
            },
        },
        "data_spec_sha256": current_data_spec_sha256,
        "path_prototype_data_spec_sha256": dict(
            Counter(
                row["path_prototype_data_spec_sha256"]
                for row in rows
            )
        ),
        "weapon_action": dict(counts),
        "expected_weapon_action": dict(
            expected_weapon_action_counts
        ),
        "held_weapon": dict(held),
        "maps": dict(maps),
        "gametypes": dict(gametypes),
        "primary_weapon": dict(primary),
        "reload_weapon": dict(reloads),
        "weapon_action_role_bucket_cells": {
            f"{role}:{bucket}:{mode}": count
            for (role, bucket, mode), count in sorted(
                action_cells.items()
            )
        },
        "planned_relation": dict(planned_relation),
        "planned_distance": dict(planned_distance),
        "planned_enemy_policy": dict(planned_enemy_policy),
        "actual_net": dict(actual_net),
        "actual_yaw": dict(actual_yaw),
        "actual_pitch": dict(actual_pitch),
        "physical_marginals": {
            field: dict(counts)
            for field, counts in physical_marginals.items()
        },
        "path_ge1000": sum(
            row["certified_realized_motion"]["path_length_3d"]
            >= 1_000
            for row in rows
        ),
        "path_ge2000": sum(
            row["certified_realized_motion"]["path_length_3d"]
            >= 2_000
            for row in rows
        ),
        "joint_net512_yaw90": sum(
            row["certified_realized_motion"][
                "net_displacement_3d"
            ]
            >= 512
            and row["certified_realized_motion"]["yaw_range_deg"]
            >= 90
            for row in rows
        ),
        "semantic_variants_per_prototype": {
            "minimum": min(
                semantic_variant_counts.values(), default=0
            ),
            "maximum": max(
                semantic_variant_counts.values(), default=0
            ),
            "counts": dict(
                Counter(semantic_variant_counts.values())
            ),
            "mean_absolute_deviation_from_ten": (
                sum(
                    abs(
                        count
                        - SEMANTIC_VARIANTS_PER_PROTOTYPE
                    )
                    for count in semantic_variant_counts.values()
                )
                / max(1, len(semantic_variant_counts))
            ),
        },
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_formal_semantic_audit_failed",
            capture.canonical_json(report),
        )
    return report


def write_formal_shards(
    rows: list[dict[str, Any]], wave: str
) -> list[dict[str, Any]]:
    shard_root = (
        FORMAL_SHARD_ROOT
        if wave == "primary"
        else FORMAL_REPLENISHMENT_SHARD_ROOT
    )
    result: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        selected = [
            row
            for row in rows
            if row["assigned_shard"] == shard_index
        ]
        path = (
            shard_root
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        text = canonical_lines(selected)
        write_once_or_verify(path, text)
        result.append(
            {
                "shard_index": shard_index,
                "rows": len(selected),
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    return result


def materialize_formal() -> dict[str, Any]:
    pool = load_certified_pool()
    primary_selected, primary_selection = select_certified_paths(
        pool,
        count=PRIMARY_PROTOTYPE_COUNT,
        quota_scale=PRIMARY_PROTOTYPE_SCALE,
        label="primary",
    )
    semantic_weight_feasibility = (
        semantic_weight_feasibility_reference()
    )
    primary_selection_sha256 = hashlib.sha256(
        canonical_lines(
            {
                "episode_id": row["episode_id"],
                "certificate_sha256": row[
                    "_player_path_certificate"
                ]["certificate_sha256"],
            }
            for row in primary_selected
        ).encode()
    ).hexdigest()
    if (
        primary_selection_sha256
        != semantic_weight_feasibility["primary_selection_sha256"]
    ):
        raise capture.CaptureFailure(
            "v5_semantic_weight_audit_primary_selection_drift",
            capture.canonical_json(
                {
                    "expected": semantic_weight_feasibility[
                        "primary_selection_sha256"
                    ],
                    "actual": primary_selection_sha256,
                }
            ),
        )
    selected_ids = {
        str(row["episode_id"]) for row in primary_selected
    }
    remaining = [
        row for row in pool if row["episode_id"] not in selected_ids
    ]
    replenishment_selected, replenishment_selection = (
        select_certified_paths(
            remaining,
            count=REPLENISHMENT_PROTOTYPE_COUNT,
            quota_scale=REPLENISHMENT_PROTOTYPE_SCALE,
            label="replenishment",
        )
    )
    primary, primary_audit = expand_semantic_variants(
        primary_selected,
        wave="primary",
        action_scale=1,
        seed=PROTOTYPE_SEED + 2_000_000,
    )
    replenishment, replenishment_audit = (
        expand_semantic_variants(
            replenishment_selected,
            wave="replenishment",
            action_scale=v4.REPLENISHMENT_SCALE,
            seed=PROTOTYPE_SEED + 3_000_000,
        )
    )
    primary_text = canonical_lines(primary)
    replenishment_text = canonical_lines(replenishment)
    write_once_or_verify(FORMAL_INPUT_PATH, primary_text)
    write_once_or_verify(
        FORMAL_REPLENISHMENT_PATH, replenishment_text
    )
    primary_shards = write_formal_shards(primary, "primary")
    replenishment_shards = write_formal_shards(
        replenishment, "replenishment"
    )
    runtime_lock_text = runtime_code_lock_text()
    write_once_or_verify(
        FORMAL_RUNTIME_LOCK_PATH, runtime_lock_text
    )
    enemy_preflight = json.loads(
        v4.ENEMY_PATH_PREFLIGHT_PATH.read_text(encoding="utf-8")
    )
    created_utc = (
        json.loads(
            FORMAL_METADATA_PATH.read_text(encoding="utf-8")
        )["created_utc"]
        if FORMAL_METADATA_PATH.is_file()
        else capture.utc_now()
    )
    metadata = {
        "schema_version": "xonotic-stage1-formal-manifest-v2",
        "created_utc": created_utc,
        "source_commit": RUNTIME_SOURCE_COMMIT,
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": True,
        "training_admitted": False,
        "authorization_basis": (
            "authoritative_player_path_certification_plus_exact_runtime_"
            "compatibility_audit_plus_realized_quota_milp_plus_fixed_"
            "semantic_weight_feasibility_audit"
        ),
        "shard_count": SHARD_COUNT,
        "shard_method": (
            "canonical formal ordinal round-robin: "
            "(candidate_ordinal - 1) mod 32"
        ),
        "topology": "32 independent one-GPU workers",
        "runtime_code_lock": {
            "path": str(
                FORMAL_RUNTIME_LOCK_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(
                runtime_lock_text.encode()
            ).hexdigest(),
            "entries": len(RUNTIME_LOCK_RELATIVE_PATHS),
        },
        "path_certification": {
            "index_path": str(
                PATH_CERTIFICATE_INDEX.relative_to(ROOT)
            ),
            "index_sha256": capture.sha256_file(
                PATH_CERTIFICATE_INDEX
            ),
            "certificate_source_commit": EXPECTED_SOURCE_COMMIT,
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
            "runtime_compatibility": (
                player_path_runtime_compatibility_reference()
            ),
            "runtime_policy": (
                "exact frozen physical actions plus per-tick certified "
                "trajectory replay under one exact audited commit pair; "
                "no geometry/action fallback and no source fallback"
            ),
        },
        "semantic_weight_feasibility": (
            semantic_weight_feasibility
        ),
        "enemy_path_preflight": {
            "path": str(
                v4.ENEMY_PATH_PREFLIGHT_PATH.relative_to(ROOT)
            ),
            "sha256": capture.sha256_file(
                v4.ENEMY_PATH_PREFLIGHT_PATH
            ),
            "source_commit": enemy_preflight["source_commit"],
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
        },
        "primary": {
            "rows": len(primary),
            "path": str(FORMAL_INPUT_PATH.relative_to(ROOT)),
            "sha256": hashlib.sha256(primary_text.encode()).hexdigest(),
            "shards": primary_shards,
            "selection": primary_selection,
            "audit": primary_audit,
        },
        "replenishment": {
            "rows": len(replenishment),
            "path": str(
                FORMAL_REPLENISHMENT_PATH.relative_to(ROOT)
            ),
            "sha256": hashlib.sha256(
                replenishment_text.encode()
            ).hexdigest(),
            "shards": replenishment_shards,
            "selection": replenishment_selection,
            "audit": replenishment_audit,
            "feasibility": replenishment_feasibility_reference(),
            "launch_policy": (
                "launch only after realized quota audit identifies a deficit"
            ),
        },
        "launch": {
            "status": "authorized_primary_60k",
            "initial_wave": "primary",
            "formal_training_admission": (
                "post-collection global realized quota audit only"
            ),
        },
    }
    write_once_or_verify(
        FORMAL_METADATA_PATH,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    audit = {
        "schema_version": "xonotic-stage1-v5-formal-audit-v1",
        "created_utc": created_utc_for(FORMAL_AUDIT_PATH),
        "passed": True,
        "primary": primary_audit,
        "replenishment": replenishment_audit,
        "metadata_sha256": capture.sha256_file(
            FORMAL_METADATA_PATH
        ),
        "primary_sha256": capture.sha256_file(FORMAL_INPUT_PATH),
        "replenishment_sha256": capture.sha256_file(
            FORMAL_REPLENISHMENT_PATH
        ),
        "runtime_code_lock_sha256": capture.sha256_file(
            FORMAL_RUNTIME_LOCK_PATH
        ),
    }
    atomic_json(FORMAL_AUDIT_PATH, audit)
    return metadata


def status() -> dict[str, Any]:
    route_audit = (
        json.loads(ROUTE_AUDIT_PATH.read_text(encoding="utf-8"))
        if ROUTE_AUDIT_PATH.is_file()
        else None
    )
    certificates = capture.load_jsonl(PATH_CERTIFICATE_INDEX)
    certificate_status = Counter(
        str(row.get("status")) for row in certificates
    )
    return {
        "schema_version": "xonotic-stage1-v5-preparation-status-v1",
        "created_utc": capture.utc_now(),
        "route_audit": route_audit,
        "prototype_metadata_exists": PROTOTYPE_METADATA_PATH.is_file(),
        "certification_spare_metadata_exists": (
            CERTIFICATION_SPARE_METADATA_PATH.is_file()
        ),
        "targeted_metadata_exists": TARGETED_METADATA_PATH.is_file(),
        "fast_traversal_metadata_exists": (
            FAST_TRAVERSAL_METADATA_PATH.is_file()
        ),
        "fast_traversal_tight_metadata_exists": (
            FAST_TRAVERSAL_TIGHT_METADATA_PATH.is_file()
        ),
        "fast_traversal_world_metadata_exists": (
            FAST_TRAVERSAL_WORLD_METADATA_PATH.is_file()
        ),
        "path_certificates": dict(sorted(certificate_status.items())),
        "formal_manifest_exists": FORMAL_METADATA_PATH.is_file(),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "command",
        choices=(
            "routes",
            "prototypes",
            "spares",
            "targets",
            "fast",
            "fast-tight",
            "fast-world",
            "formal",
            "status",
        ),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    try:
        if args.command == "routes":
            output = audit_routes()
        elif args.command == "prototypes":
            output = materialize_prototypes()
        elif args.command == "spares":
            output = materialize_certification_spare_prototypes()
        elif args.command == "targets":
            output = materialize_targeted_prototypes()
        elif args.command == "fast":
            output = materialize_fast_traversal_prototypes()
        elif args.command == "fast-tight":
            output = materialize_fast_traversal_tight_prototypes()
        elif args.command == "fast-world":
            output = materialize_fast_traversal_world_prototypes()
        elif args.command == "formal":
            output = materialize_formal()
        else:
            output = status()
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
