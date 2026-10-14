                      
"""Build the isolated Stage-2 v13 temporal/visibility production manifest.

This is a semantic re-plan of the accepted v12r5 42k candidate population.  It
preserves maps, weapons, appearances, player-action sources, outcome recipes,
distance tiers, and jump programs, while replacing the degenerate five-block
opposite-direction alternation with an explicit temporal grammar.  No v12
manifest, capture, or training release is modified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT
    / "manifests/stage2_motion_near5_combo_42k_v12_replenish_28shard_20260818_r5"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_motion_temporal_visibility_42k_v13_28shard_20260820_r3"
)
RUNTIME_LOCK = (
    ROOT / "locks/stage2_motion_7x4_activeonly_v13r3_resilient_runtime.sha256"
)
BUILD_TAG = "capture-ee4c0aac65db-aarch64"
SOURCE_COMMIT = "ee4c0aac65dbac689904b320c7db4e43dfd93d20"
BUILD_LOCK = ROOT / "locks" / f"{BUILD_TAG}.sha256"
SHARD_COUNT = 28
PRIMARY_PER_SHARD = 1_500
PRIMARY_ROWS = SHARD_COUNT * PRIMARY_PER_SHARD
SOURCE_RESERVE_PER_SHARD = 375
SOURCE_RESERVE_ROWS = SHARD_COUNT * SOURCE_RESERVE_PER_SHARD
SOURCE_CANDIDATE_ROWS = PRIMARY_ROWS + SOURCE_RESERVE_ROWS
RESERVE_PER_SHARD = 750
RESERVE_ROWS = SHARD_COUNT * RESERVE_PER_SHARD
CANDIDATE_ROWS = PRIMARY_ROWS + RESERVE_ROWS
MOTION_SPEED = 64.0

FAMILY_QUOTAS = {
    "stationary": 4_200,
    "single_direction": 12_600,
    "move_stop": 8_400,
    "one_direction_change": 10_500,
    "two_nonperiodic_changes": 4_200,
    "repeated_back_and_forth": 2_100,
}
VISIBILITY_QUOTAS = {
    "always_visible": 29_400,
    "exit_hold": 8_400,
    "exit_reacquire": 4_200,
}
HUMANIZED_ARMS = {
    "stable_track",
    "overshoot_correct",
    "predictive_track",
    "edge_graze",
    "near_miss",
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
OPPOSITE = {0: 0, 1: 2, 2: 1, 3: 4, 4: 3, 5: 8, 8: 5, 6: 7, 7: 6}
SAFE_CODES_BY_TIER = {
    "d1": (1, 2, 4, 7, 8),
    "d2": (1, 2, 4, 7, 8),
    "d3": (1, 2, 4, 5, 6, 7, 8),
    "d4": (1, 2, 3, 4, 5, 6, 7, 8),
    "d5": (1, 2, 3, 5, 6, 7, 8),
}


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def stable_digest(row: dict[str, Any], salt: str) -> str:
    return hashlib.sha256(
        f"stage2-v13:{salt}:{row['sample_key']}".encode()
    ).hexdigest()


def stable_index(row: dict[str, Any], salt: str, modulus: int) -> int:
    return int(stable_digest(row, salt)[:16], 16) % modulus


def distribution(
    rows: Iterable[dict[str, Any]], key: Callable[[dict[str, Any]], Any]
) -> dict[str, int]:
    return dict(sorted(Counter(str(key(row)) for row in rows).items()))


def load_source_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "shards-028").glob("shard-*-of-028.jsonl")):
        rows.extend(read_jsonl(path))
    rows.sort(key=lambda row: int(row["ordinal"]))
    if len(rows) != SOURCE_CANDIDATE_ROWS:
        raise RuntimeError(
            f"expected {SOURCE_CANDIDATE_ROWS} source candidates, found {len(rows)}"
        )
    primary = [row for row in rows if row["candidate_role"] == "primary"]
    reserve = [row for row in rows if row["candidate_role"] == "reserve"]
    if len(primary) != PRIMARY_ROWS or len(reserve) != SOURCE_RESERVE_ROWS:
        raise RuntimeError(
            f"source role counts mismatch: primary={len(primary)} reserve={len(reserve)}"
        )
    return rows


def scenario_arm(row: dict[str, Any]) -> str:
    return str(
        row["active_scenario"]["causal_design"]
        ["weapon_balanced_aim_program"]["arm"]
    )


def scenario_outcome(row: dict[str, Any]) -> str:
    return str(row["active_scenario"]["intent_outcome"])


def scenario_jump(row: dict[str, Any]) -> bool:
    return bool(row["active_scenario"]["enemy_jump_program"]["enabled"])


def old_stationary(row: dict[str, Any]) -> bool:
    return not any(
        int(value)
        for value in row["active_scenario"]["enemy_motion_program"]
        ["direction_codes"]
    )


def take_exact(
    rows: list[dict[str, Any]],
    count: int,
    salt: str,
    used: set[str],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    eligible = [
        row
        for row in rows
        if str(row["sample_key"]) not in used and predicate(row)
    ]
    eligible.sort(key=lambda row: stable_digest(row, salt))
    if len(eligible) < count:
        raise RuntimeError(
            f"selection shortage for {salt}: needed={count} eligible={len(eligible)}"
        )
    selected = eligible[:count]
    used.update(str(row["sample_key"]) for row in selected)
    return selected


def assign_primary_designs(
    rows: list[dict[str, Any]],
) -> dict[str, tuple[str, str]]:
    used: set[str] = set()
    assignment: dict[str, tuple[str, str]] = {}

    stationary = take_exact(
        rows,
        FAMILY_QUOTAS["stationary"],
        "stationary",
        used,
        lambda row: old_stationary(row) and not scenario_jump(row),
    )
    for row in stationary:
        assignment[str(row["sample_key"])] = ("stationary", "always_visible")

                                                                             
                                                                            
                                                                               
                                                 
    for outcome, count in (("miss", 2_100), ("hit_survive", 2_100)):
        selected = take_exact(
            rows,
            count,
            f"reacquire-{outcome}",
            used,
            lambda row, wanted=outcome: (
                scenario_outcome(row) == wanted
                and scenario_arm(row) in HUMANIZED_ARMS
                and not scenario_jump(row)
            ),
        )
        for row in selected:
            assignment[str(row["sample_key"])] = (
                "single_direction",
                "exit_reacquire",
            )

    for outcome, count in (("no_fire", 2_800), ("miss", 5_600)):
        selected = take_exact(
            rows,
            count,
            f"exit-hold-{outcome}",
            used,
            lambda row, wanted=outcome: (
                scenario_outcome(row) == wanted and not scenario_jump(row)
            ),
        )
        for row in selected:
            assignment[str(row["sample_key"])] = (
                "single_direction",
                "exit_hold",
            )

    remaining = [row for row in rows if str(row["sample_key"]) not in used]
    remaining.sort(key=lambda row: stable_digest(row, "remaining-family"))
    remaining_quotas = (
        ("move_stop", FAMILY_QUOTAS["move_stop"]),
        ("one_direction_change", FAMILY_QUOTAS["one_direction_change"]),
        ("two_nonperiodic_changes", FAMILY_QUOTAS["two_nonperiodic_changes"]),
        ("repeated_back_and_forth", FAMILY_QUOTAS["repeated_back_and_forth"]),
    )
    cursor = 0
    for family, count in remaining_quotas:
        selected = remaining[cursor : cursor + count]
        if len(selected) != count:
            raise RuntimeError(f"remaining family shortage: {family}")
        cursor += count
        for row in selected:
            assignment[str(row["sample_key"])] = (family, "always_visible")
    if cursor != len(remaining) or len(assignment) != PRIMARY_ROWS:
        raise RuntimeError(
            f"primary assignment mismatch: cursor={cursor} remaining={len(remaining)} "
            f"assigned={len(assignment)}"
        )
    return assignment


def first_old_code(row: dict[str, Any]) -> int:
    codes = [
        int(value)
        for value in row["active_scenario"]["enemy_motion_program"]
        ["direction_codes"]
    ]
    return next((code for code in codes if code), 0)


def safe_base_code(row: dict[str, Any], salt: str) -> int:
    old = first_old_code(row)
    tier = str(row["active_scenario"]["distance_tier"])
    safe = SAFE_CODES_BY_TIER[tier]
    if old in safe:
        return old
    return safe[stable_index(row, salt, len(safe))]


def different_safe_code(
    row: dict[str, Any], current: set[int], salt: str
) -> int:
    tier = str(row["active_scenario"]["distance_tier"])
    candidates = [code for code in SAFE_CODES_BY_TIER[tier] if code not in current]
    if not candidates:
        candidates = [code for code in range(1, 9) if code not in current]
    return candidates[stable_index(row, salt, len(candidates))]


def outward_code(row: dict[str, Any], salt: str) -> int:
    scenario = row["active_scenario"]
    horizontal = str(
        (scenario.get("initial_screen_design") or {}).get(
            "screen_horizontal", "center"
        )
    )
    if horizontal == "left":
        side = "left"
    elif horizontal == "right":
        side = "right"
    else:
        side = "left" if stable_index(row, salt + "-side", 2) == 0 else "right"
    tier = str(scenario["distance_tier"])
    if tier in {"d1", "d2"}:
        candidates = (1, 7) if side == "left" else (2, 8)
    elif tier in {"d4", "d5"}:
        candidates = (1, 5) if side == "left" else (2, 6)
    else:
        candidates = (1, 5, 7) if side == "left" else (2, 6, 8)
    return candidates[stable_index(row, salt, len(candidates))]


def build_program(
    row: dict[str, Any], family: str, visibility_class: str
) -> list[int]:
    if family == "stationary":
        return [0, 0, 0, 0, 0]
    if visibility_class in {"exit_hold", "exit_reacquire"}:
        primary = outward_code(row, "outward-code")
    else:
        primary = safe_base_code(row, "base-code")
    if family == "single_direction":
        return [primary] * 5
    if family == "move_stop":
        boundary = 1 + stable_index(row, "move-stop-boundary", 4)
        if stable_index(row, "move-stop-order", 2) == 0:
            return [primary] * boundary + [0] * (5 - boundary)
        return [0] * boundary + [primary] * (5 - boundary)
    if family == "one_direction_change":
        secondary = different_safe_code(row, {primary}, "one-change-secondary")
        boundary = 1 + stable_index(row, "one-change-boundary", 4)
        return [primary] * boundary + [secondary] * (5 - boundary)
    if family == "two_nonperiodic_changes":
        secondary = different_safe_code(row, {primary}, "two-change-secondary")
        tertiary = different_safe_code(
            row, {primary, secondary}, "two-change-tertiary"
        )
        boundaries = ((1, 3), (1, 4), (2, 3), (2, 4))
        left, right = boundaries[stable_index(row, "two-change-boundaries", 4)]
        return (
            [primary] * left
            + [secondary] * (right - left)
            + [tertiary] * (5 - right)
        )
    if family == "repeated_back_and_forth":
        return [primary, OPPOSITE[primary], primary, OPPOSITE[primary], primary]
    raise RuntimeError(f"unknown temporal family: {family}")


def primary_motion(codes: list[int]) -> str:
    code = next((value for value in codes if value), 0)
    return CODE_LABEL[code]


def direction_change_count(codes: list[int]) -> int:
    return sum(left != right for left, right in zip(codes, codes[1:]))


def transform_row(
    source: dict[str, Any],
    family: str,
    visibility_class: str,
    ordinal: int,
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    scenario = row["active_scenario"]
    codes = build_program(source, family, visibility_class)
    motion_name = primary_motion(codes)
    speed = MOTION_SPEED if any(codes) else 0.0
    new_key = f"s2mtv42v13_{ordinal:06d}"
    new_episode = f"s2mtv42v13_{ordinal:06d}_active"

    actual_program = copy.deepcopy(scenario["enemy_motion_program"])
    actual_program.update(
        {
            "schema_version": "xonotic-stage2-enemy-motion-program-v3-temporal",
            "speed_units_per_second": speed,
            "block_seconds": 0.8,
            "direction_codes": codes,
            "primary_motion": motion_name,
            "reads_camera": False,
            "reads_live_player_state": False,
        }
    )
    reference_program = copy.deepcopy(actual_program)
    if visibility_class == "exit_hold":
        reference_program.update(
            {
                "speed_units_per_second": 0.0,
                "direction_codes": [0, 0, 0, 0, 0],
                                                                        
                                                                     
                "primary_motion": motion_name,
            }
        )

    scenario.update(
        {
            "schema_version": "xonotic-stage2-motion-interaction-scenario-v13-temporal-visibility",
            "episode_id": new_episode,
            "anchor_id": new_key,
            "counterfactual_group_id": new_key,
            "candidate_kind": "stage2_motion_temporal_visibility_v13",
            "dataset_role": "causal_interaction_enemy_motion_temporal_visibility_v13",
            "target_bin": "stage2_motion_temporal_visibility_42k_v13",
            "target_ordinal": ordinal,
            "enemy_motion_program": actual_program,
            "action_reference_motion_program": reference_program,
        }
    )
    scenario["enemy"]["motion"] = 5 if any(codes) else 0
    scenario["enemy_policy"].update(
        {
            "name": "fixed_speed_prompt_block_temporal_program_v13",
            "closed_loop_decisions": False,
            "reads_camera": False,
            "reads_crosshair": False,
            "runtime_reads_player_state": False,
        }
    )
    scenario["motion_sequence_design"] = {
        "schema_version": "xonotic-stage2-motion-sequence-design-v1",
        "family": family,
        "direction_codes": codes,
        "direction_labels": [CODE_LABEL[code] for code in codes],
        "direction_change_count": direction_change_count(codes),
        "fixed_speed_units_per_second": speed,
        "prompt_control": "one_relative_direction_label_per_0p8s_block",
        "automatic_boundary_reversal": False,
    }
    scenario["visibility_design"] = {
        "schema_version": "xonotic-stage2-visibility-camera-design-v1",
        "class": visibility_class,
        "partial_edge_exit_allowed": True,
        "occlusion_allowed": False,
        "camera_action_described_in_prompt": False,
        "enemy_prompt_changes_for_reacquire": False,
        "minimum_edge_or_offscreen_run_ticks": 8,
        "final_state_window_ticks": 12,
        "camera_reference_policy": {
            "always_visible": "track_actual_enemy_program",
            "exit_hold": "hold_initial_enemy_reference",
            "exit_reacquire": "delayed_smooth_track_actual_enemy_program",
        }[visibility_class],
    }
    if visibility_class == "exit_reacquire":
        aim = scenario["causal_design"]["weapon_balanced_aim_program"]
        if str(aim["arm"]) not in HUMANIZED_ARMS:
            raise RuntimeError(
                f"reacquire row is not humanized: {source['sample_key']} {aim['arm']}"
            )
        aim["response_start_output_tick"] = 144
        aim["settle_output_tick"] = 216
        scenario["visibility_design"].update(
            {
                "reacquire_response_start_output_tick": 144,
                "reacquire_settle_output_tick": 216,
            }
        )
        scenario["camera_program"] = "delayed_smooth_reacquire_v1"
    elif visibility_class == "exit_hold":
        scenario["camera_program"] = "hold_initial_reference_v1"

    scenario["formal_design"].update(
        {
            "schema_version": "xonotic-stage2-motion-temporal-visibility-formal-design-v13",
            "cohort": "s2mtv42v13",
            "cohort_role": str(row["candidate_role"]),
            "ordinal": ordinal,
            "target_motion_name": motion_name,
            "motion_sequence_family": family,
            "visibility_class": visibility_class,
            "enemy_jumps": bool(scenario["enemy_jump_program"]["enabled"]),
        }
    )
    scenario["policy_labels"].update(
        {
            "target_motion_name": motion_name,
            "motion_sequence_family": family,
            "visibility_class": visibility_class,
        }
    )
    authorization = scenario["formal_authorization_basis"]
    authorization.update(
        {
            "v13_change_authorization": "explicit_user_request_2026-08-20",
            "v13_change_scope": [
                "replace_automatic_five_block_reversal_with_explicit_temporal_grammar",
                "fixed_enemy_speed_64_units_per_second",
                "simple_exit_hold_and_action_conditioned_reacquire",
                "relative_direction_prompt_only",
                "partial_edge_exit_allowed",
                "occlusion_rejected",
                "preserve_stage2_interaction_and_action_contract",
            ],
        }
    )

    row.update(
        {
                                                                           
                                                                           
            "schema_version": "xonotic-stage2-motion-near5-combo-production-active-v12-replenish",
            "sample_key": new_key,
            "ordinal": ordinal,
            "shard_count": SHARD_COUNT,
            "active_scenario": scenario,
            "raw_avi_audit": ordinal % 20 == 0,
            "semantic_revision": "v13_temporal_visibility",
        }
    )
    row["budget_token"].update(
        {
            "motion_sequence_family": family,
            "visibility_class": visibility_class,
        }
    )
    return row


def runtime_files() -> list[Path]:
    return [
        ROOT / "pilot_scripts/build_samples.py",
        ROOT / "pilot_scripts/build_samples_v12.py",
        ROOT / "pilot_scripts/build_samples_v13.py",
        ROOT / "production_scripts/gpu_memory_holder.py",
        ROOT / "production_scripts/launch_dlc_7x4_activeonly_v13_resilient.sh",
        ROOT / "production_scripts/prepare_stage2_motion_42k_v13_temporal_visibility_manifest.py",
        ROOT / "production_scripts/run_stage2_motion_40k_shard_v12_support.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v12r6_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v13_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v13_multigpu.py",
        ROOT / "scripts/xonotic_stage1_reusable.py",
        ROOT / "scripts/xonotic_stage2_causal_formal.py",
    ]


def write_runtime_lock() -> dict[str, str]:
    files = runtime_files()
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing v13 runtime files: {missing}")
    hashes = {str(path.relative_to(ROOT)): sha256_file(path) for path in files}
    payload = "".join(
        f"{digest}  {relative}\n" for relative, digest in hashes.items()
    )
    if RUNTIME_LOCK.exists():
        if RUNTIME_LOCK.read_text(encoding="utf-8") != payload:
            raise RuntimeError(
                f"existing runtime lock differs; use a new revision: {RUNTIME_LOCK}"
            )
    else:
        RUNTIME_LOCK.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_LOCK.write_text(payload, encoding="utf-8")
    return hashes


def make_extra_reserve_source(
    source: dict[str, Any], extra_index: int
) -> dict[str, Any]:
    """Create a deterministic independent reserve variant of one primary row."""
    row = copy.deepcopy(source)
    source_key = str(source["sample_key"])
    synthetic_key = f"s2mtv42v13r3_extra_source_{extra_index:06d}"
    scenario = row["active_scenario"]
    scenario["seed"] = int(scenario["seed"]) + 40_000_000 + extra_index
    scenario["enemy_policy"]["policy_seed"] = int(scenario["seed"]) + 1_000_000
    if scenario.get("prefrozen_trace_source"):
        scenario["prefrozen_trace_source"][
            "scenario_seed_relation"
        ] = "independent_replenishment_scenario_seed"
    scenario["reserve_transform"] = {
        "schema_version": "xonotic-stage2-temporal-extra-reserve-transform-v1",
        "source_sample_key": source_key,
        "source_scenario_sha256": hashlib.sha256(
            canonical_json(source["active_scenario"]).encode()
        ).hexdigest(),
        "motion_transform": "deterministic_alternative_temporal_program",
        "camera_and_player_action_program_unchanged": True,
        "reads_camera": False,
        "reads_live_player_state": False,
    }
    budget = copy.deepcopy(row["budget_token"])
    budget.update(
        {
            "cohort": "s2mtv42v13r3",
            "cohort_role": "replenishment_reserve",
            "source_sample_key": source_key,
        }
    )
    row.update(
        {
            "candidate_role": "reserve",
                                                                         
                                                                       
            "sample_key": synthetic_key,
            "budget_token": budget,
            "reserve_source_sample_key": source_key,
            "reserve_source_ordinal": int(source["ordinal"]),
        }
    )
    return row


def joint_distribution(
    rows: Iterable[dict[str, Any]],
    left: Callable[[dict[str, Any]], Any],
    right: Callable[[dict[str, Any]], Any],
) -> dict[str, dict[str, int]]:
    result: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        result[str(left(row))][str(right(row))] += 1
    return {
        key: dict(sorted(values.items()))
        for key, values in sorted(result.items())
    }


def write_manifest(
    source_rows: list[dict[str, Any]], output_root: Path, runtime: dict[str, str]
) -> None:
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite manifest root: {output_root}")
    primary_source = [
        row for row in source_rows if row["candidate_role"] == "primary"
    ]
    reserve_source = [
        row for row in source_rows if row["candidate_role"] == "reserve"
    ]
    assignment = assign_primary_designs(primary_source)
    primary_by_old_key = {str(row["sample_key"]): row for row in primary_source}

    transformed: list[dict[str, Any]] = []
    primary_design_by_old_key: dict[str, tuple[str, str]] = {}
    for ordinal, source in enumerate(primary_source):
        old_key = str(source["sample_key"])
        family, visibility_class = assignment[old_key]
        primary_design_by_old_key[old_key] = (family, visibility_class)
        transformed.append(
            transform_row(source, family, visibility_class, ordinal)
        )
    for reserve_index, source in enumerate(reserve_source):
        source_key = str(source.get("reserve_source_sample_key", ""))
        if source_key not in primary_by_old_key or source_key not in primary_design_by_old_key:
            raise RuntimeError(f"reserve source mapping missing: {source_key}")
        family, visibility_class = primary_design_by_old_key[source_key]
        transformed.append(
            transform_row(
                source,
                family,
                visibility_class,
                PRIMARY_ROWS + reserve_index,
            )
        )
    existing_reserve_sources = {
        str(row["reserve_source_sample_key"]) for row in reserve_source
    }
    extra_reserve_index = 0
    for shard_index in range(SHARD_COUNT):
        eligible = [
            row
            for row in primary_source
            if int(row["assigned_shard"]) == shard_index
            and str(row["sample_key"]) not in existing_reserve_sources
        ]
        eligible.sort(key=lambda row: stable_digest(row, "r3-extra-reserve"))
        selected = eligible[:SOURCE_RESERVE_PER_SHARD]
        if len(selected) != SOURCE_RESERVE_PER_SHARD:
            raise RuntimeError(
                f"extra reserve source shortage in shard {shard_index}"
            )
        for source in selected:
            source_key = str(source["sample_key"])
            family, visibility_class = primary_design_by_old_key[source_key]
            transformed.append(
                transform_row(
                    make_extra_reserve_source(source, extra_reserve_index),
                    family,
                    visibility_class,
                    SOURCE_CANDIDATE_ROWS + extra_reserve_index,
                )
            )
            extra_reserve_index += 1
    if extra_reserve_index != SOURCE_RESERVE_ROWS:
        raise RuntimeError(
            f"extra reserve count mismatch: {extra_reserve_index}"
        )
    transformed.sort(key=lambda row: int(row["ordinal"]))

    output_root.mkdir(parents=True)
    shard_root = output_root / "shards-028"
    shard_root.mkdir()
    shards: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        selected = [
            row
            for row in transformed
            if int(row["assigned_shard"]) == shard_index
        ]
        path = shard_root / f"shard-{shard_index:03d}-of-028.jsonl"
        path.write_text(
            "".join(canonical_json(row) + "\n" for row in selected),
            encoding="utf-8",
        )
        shards.append(
            {
                "shard_index": shard_index,
                "path": str(path.relative_to(output_root)),
                "rows": len(selected),
                "primary_rows": sum(
                    row["candidate_role"] == "primary" for row in selected
                ),
                "reserve_rows": sum(
                    row["candidate_role"] == "reserve" for row in selected
                ),
                "target_accepted_rows": PRIMARY_PER_SHARD,
                "sha256": sha256_file(path),
            }
        )

    primary = [row for row in transformed if row["candidate_role"] == "primary"]
    reserve = [row for row in transformed if row["candidate_role"] == "reserve"]
    family = lambda row: row["active_scenario"]["motion_sequence_design"]["family"]
    visibility = lambda row: row["active_scenario"]["visibility_design"]["class"]
    old_primary_distributions = {
        "intent_outcome": distribution(primary_source, scenario_outcome),
        "weapon": distribution(primary_source, lambda row: row["active_scenario"]["weapon"]),
        "map": distribution(primary_source, lambda row: row["active_scenario"]["map"]),
        "enemy_model": distribution(primary_source, lambda row: row["active_scenario"]["enemy_model"]),
        "distance_tier": distribution(primary_source, lambda row: row["active_scenario"]["distance_tier"]),
        "player_motion_class": distribution(primary_source, lambda row: row["budget_token"]["player_motion_class"]),
        "enemy_jumps": distribution(primary_source, scenario_jump),
    }
    new_primary_distributions = {
        "intent_outcome": distribution(primary, scenario_outcome),
        "weapon": distribution(primary, lambda row: row["active_scenario"]["weapon"]),
        "map": distribution(primary, lambda row: row["active_scenario"]["map"]),
        "enemy_model": distribution(primary, lambda row: row["active_scenario"]["enemy_model"]),
        "distance_tier": distribution(primary, lambda row: row["active_scenario"]["distance_tier"]),
        "player_motion_class": distribution(primary, lambda row: row["budget_token"]["player_motion_class"]),
        "enemy_jumps": distribution(primary, scenario_jump),
    }
    family_counts = distribution(primary, family)
    visibility_counts = distribution(primary, visibility)
    checks = {
        "primary_rows_42000": len(primary) == PRIMARY_ROWS,
        "reserve_rows_21000": len(reserve) == RESERVE_ROWS,
        "candidate_rows_63000": len(transformed) == CANDIDATE_ROWS,
        "sample_keys_unique": len({row["sample_key"] for row in transformed})
        == CANDIDATE_ROWS,
        "ordinals_complete": [int(row["ordinal"]) for row in transformed]
        == list(range(CANDIDATE_ROWS)),
        "family_quotas_exact": family_counts
        == {key: FAMILY_QUOTAS[key] for key in sorted(FAMILY_QUOTAS)},
        "visibility_quotas_exact": visibility_counts
        == {key: VISIBILITY_QUOTAS[key] for key in sorted(VISIBILITY_QUOTAS)},
        "source_marginals_preserved": old_primary_distributions
        == new_primary_distributions,
        "stationary_has_no_jump": all(
            not scenario_jump(row) for row in primary if family(row) == "stationary"
        ),
        "single_direction_is_visibility_slice": all(
            (family(row) == "single_direction")
            == (visibility(row) in {"exit_hold", "exit_reacquire"})
            for row in primary
        ),
        "reacquire_is_simple_humanized_nonjump_nonkill": all(
            scenario_arm(row) in HUMANIZED_ARMS
            and not scenario_jump(row)
            and scenario_outcome(row) in {"miss", "hit_survive"}
            for row in primary
            if visibility(row) == "exit_reacquire"
        ),
        "fixed_speed_64_for_all_moving_rows": all(
            float(row["active_scenario"]["enemy_motion_program"]["speed_units_per_second"])
            == (
                MOTION_SPEED
                if any(row["active_scenario"]["enemy_motion_program"]["direction_codes"])
                else 0.0
            )
            for row in transformed
        ),
        "no_frozen_scenario": all("frozen_scenario" not in row for row in transformed),
        "shards_exact": all(
            shard["rows"] == PRIMARY_PER_SHARD + RESERVE_PER_SHARD
            and shard["primary_rows"] == PRIMARY_PER_SHARD
            and shard["reserve_rows"] == RESERVE_PER_SHARD
            for shard in shards
        ),
        "prompt_camera_deconfounded": all(
            row["active_scenario"]["visibility_design"]
            ["camera_action_described_in_prompt"]
            is False
            and row["active_scenario"]["visibility_design"]
            ["enemy_prompt_changes_for_reacquire"]
            is False
            for row in transformed
        ),
        "occlusion_excluded": all(
            row["active_scenario"]["visibility_design"]["occlusion_allowed"]
            is False
            for row in transformed
        ),
    }
    audit = {
        "schema_version": "xonotic-stage2-motion-temporal-visibility-manifest-audit-v13",
        "passed": all(checks.values()),
        "checks": checks,
        "primary_rows": len(primary),
        "reserve_rows": len(reserve),
        "candidate_rows": len(transformed),
        "training_video_seconds": PRIMARY_ROWS * 5,
        "training_video_hours": PRIMARY_ROWS * 5 / 3600.0,
        "motion_sequence_family": family_counts,
        "visibility_class": visibility_counts,
        "preserved_primary_distributions": new_primary_distributions,
        "joint_distributions": {
            "family_x_outcome": joint_distribution(primary, family, scenario_outcome),
            "family_x_weapon": joint_distribution(
                primary, family, lambda row: row["active_scenario"]["weapon"]
            ),
            "family_x_map": joint_distribution(
                primary, family, lambda row: row["active_scenario"]["map"]
            ),
            "family_x_distance": joint_distribution(
                primary, family, lambda row: row["active_scenario"]["distance_tier"]
            ),
            "family_x_player_motion": joint_distribution(
                primary, family, lambda row: row["budget_token"]["player_motion_class"]
            ),
            "visibility_x_outcome": joint_distribution(
                primary, visibility, scenario_outcome
            ),
            "visibility_x_weapon": joint_distribution(
                primary, visibility, lambda row: row["active_scenario"]["weapon"]
            ),
        },
        "shards": shards,
        "source_manifest_root": str(SOURCE_ROOT),
        "old_artifacts_modified": False,
    }
    write_json(output_root / "MANIFEST_AUDIT.json", audit)
    metadata = {
                                                                            
                                                                            
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-metadata-v12-replenish",
        "semantic_schema_version": "xonotic-stage2-motion-temporal-visibility-manifest-v13",
        "semantic_revision": "v13_temporal_visibility",
        "capture_mode": "active_only",
        "qa_mode": "single_episode_authoritative",
        "formal_collection_authorized": True,
        "training_admitted": False,
        "manual_review_required": False,
        "primary_rows": PRIMARY_ROWS,
        "rendered_episode_rows": PRIMARY_ROWS,
        "candidate_rows": CANDIDATE_ROWS,
        "counterfactual_qa_rows": 0,
        "active_training_hours": PRIMARY_ROWS * 5 / 3600.0,
        "source_commit": SOURCE_COMMIT,
        "build_tag": BUILD_TAG,
        "build_lock": str(BUILD_LOCK),
        "build_lock_sha256": sha256_file(BUILD_LOCK),
        "runtime_lock": str(RUNTIME_LOCK),
        "runtime_lock_sha256": sha256_file(RUNTIME_LOCK),
        "runtime_files": runtime,
        "runtime_dependency_locks": json.loads(
            (SOURCE_ROOT / "MANIFEST_METADATA.json").read_text(encoding="utf-8")
        )["runtime_dependency_locks"],
        "live_time_scale": 2,
        "shard_count": SHARD_COUNT,
        "shards": shards,
        "manifest_audit": "MANIFEST_AUDIT.json",
        "distribution_policy": {
            "motion_sequence_family_quotas": FAMILY_QUOTAS,
            "visibility_class_quotas": VISIBILITY_QUOTAS,
            "fixed_enemy_speed_units_per_second": MOTION_SPEED,
            "prompt_schedule": "5x0.8s",
            "relative_direction_only": True,
            "camera_action_in_text": False,
            "reacquire_is_action_conditioned": True,
            "partial_edge_exit_allowed": True,
            "occlusion_training_allowed": False,
            "source_marginals_preserved": True,
        },
        "source_manifest_root": str(SOURCE_ROOT),
        "old_artifacts_modified": False,
    }
    write_json(output_root / "MANIFEST_METADATA.json", metadata)
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(f"{sha256_file(path)}  {path.relative_to(output_root)}\n")
    if not audit["passed"]:
        raise RuntimeError(f"v13 manifest audit failed: {checks}")
    print(json.dumps(audit, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    runtime = write_runtime_lock()
    rows = load_source_rows(args.source_root.resolve())
    write_manifest(rows, args.output_root.resolve(), runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
