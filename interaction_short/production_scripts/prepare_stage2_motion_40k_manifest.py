                      
"""Build the immutable 40k Stage-2 motion/interaction production manifest."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path("./xonotic_workspace")
SOURCE_MANIFEST = (
    CANONICAL_ROOT
    / "manifests/stage2_formal_40k_v1/primary/design.jsonl"
)
BUILD_TAG = "capture-e1b6fef45bc3-aarch64"
SOURCE_COMMIT = "e1b6fef45bc370d36b1f5e3ba04cd1de1d211403"
BUILD_LOCK = ROOT / "locks" / f"{BUILD_TAG}.sha256"
SMOKE_SUMMARY = (
    ROOT
    / "outputs/stage2_motion_accel_v1_validation_20260817/SUMMARY.json"
)
DEFAULT_OUTPUT = (
    ROOT / "manifests/stage2_motion_near5_combo_40k_v9_accel_20260817"
)
DEPENDENCY_LOCKS = (
    ROOT / "locks/stage2_weapon_balanced_review_v3_base_traces.sha256",
    ROOT / "locks/stage2_prefrozen_player_motion_states.sha256",
)
SHARD_COUNT = 12
PRIMARY_ROWS = 40_000
MOVING_PLAYER_ROWS = 12_000

os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG", BUILD_TAG
)
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT", SOURCE_COMMIT
)
os.environ.setdefault("XONOTIC_BUILD_GLOB", f"build/{BUILD_TAG}")
sys.path.insert(0, str(ROOT))

from pilot_scripts import build_samples as pilot              


FAMILY_RECIPE_COUNTS = {
    ("visible_no_fire", "no_fire"): 6_000,
    ("precise_tracking", "hit_survive"): 8_000,
    ("precise_tracking", "kill"): 4_000,
    ("humanized_offset_tracking", "miss"): 8_000,
    ("humanized_offset_tracking", "hit_survive"): 4_000,
    ("stochastic_aim_and_fire", "miss"): 8_000,
    ("stochastic_aim_and_fire", "hit_survive"): 2_000,
}
ARM_WEIGHTS = {
    weapon: {
        "visible_no_fire": (("visible_no_fire", 1),),
        "precise_tracking": (
            ("stable_track", 1),
            ("overshoot_correct", 1),
            ("predictive_track", 1),
        ),
        "humanized_offset_tracking": (
            (("edge_graze", 2), ("near_miss", 1))
            if weapon == "Shotgun"
            else (
                (("edge_graze", 1), ("near_miss", 4))
                if weapon == "Vortex"
                else (("edge_graze", 1), ("near_miss", 1))
            )
        ),
        "stochastic_aim_and_fire": (
            ("stochastic_local", 1),
        ),
    }
    for weapon in pilot.WEAPONS
}
PLAYER_STATIONARY = "certified_stationary_preflight_pair"
PLAYER_MOVING = "certified_prefrozen_trace_replay"
COLORS = (0, 68, 204)
SOURCE_MAPS = pilot.PREFERRED_MAPS


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_runtime_dependencies() -> dict[str, str]:
    result: dict[str, str] = {}
    for lock in DEPENDENCY_LOCKS:
        if not lock.is_file():
            raise RuntimeError(f"missing runtime dependency lock: {lock}")
        completed = subprocess.run(
            ["sha256sum", "-c", str(lock)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "runtime dependency lock failed: "
                f"{completed.stdout}{completed.stderr}"
            )
        result[str(lock.relative_to(ROOT))] = sha256_file(lock)
    return result


def balanced_values(values: Iterable[Any], count: int, seed: int) -> list[Any]:
    values = tuple(values)
    result = [values[index % len(values)] for index in range(count)]
    random.Random(seed).shuffle(result)
    return result


def weighted_values(
    weighted: tuple[tuple[str, int], ...], count: int, seed: int
) -> list[str]:
    cycle = [value for value, weight in weighted for _ in range(weight)]
    return balanced_values(cycle, count, seed)


def build_budget_tokens() -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    seed = 202_608_170_401
    for stratum_index, ((family, outcome), count) in enumerate(
        FAMILY_RECIPE_COUNTS.items()
    ):
        weapons = balanced_values(
            pilot.WEAPONS, count, seed + stratum_index
        )
        positions: defaultdict[str, list[int]] = defaultdict(list)
        for index, weapon in enumerate(weapons):
            positions[weapon].append(index)
        arms: dict[int, str] = {}
        for weapon_index, weapon in enumerate(pilot.WEAPONS):
            selected = weighted_values(
                ARM_WEIGHTS[weapon][family],
                len(positions[weapon]),
                seed + 1000 + 100 * stratum_index + weapon_index,
            )
            arms.update(zip(positions[weapon], selected, strict=True))
        for index, weapon in enumerate(weapons):
            tokens.append(
                {
                    "aim_family_bucket": family,
                    "outcome_recipe": outcome,
                    "weapon": weapon,
                    "requested_arm": arms[index],
                }
            )
    random.Random(seed + 9999).shuffle(tokens)
    if len(tokens) != PRIMARY_ROWS:
        raise RuntimeError(f"budget row mismatch: {len(tokens)}")

    non_shotgun = [
        index
        for index, token in enumerate(tokens)
        if token["weapon"] != "Shotgun"
    ]
    random.Random(seed + 20_000).shuffle(non_shotgun)
    moving = set(non_shotgun[:MOVING_PLAYER_ROWS])
    for index, token in enumerate(tokens):
        token["player_motion_class"] = (
            PLAYER_MOVING if index in moving else PLAYER_STATIONARY
        )
    return tokens


def motion_and_tier_plan() -> tuple[list[str], list[str]]:
    motions = balanced_values(
        pilot.MOTION_LABELS, PRIMARY_ROWS, 202_608_170_501
    )
    categories = {
        "approach": {
            "toward_player",
            "player_left_toward",
            "player_right_toward",
        },
        "lateral": {"player_left", "player_right"},
        "away_or_stationary": {
            "stationary",
            "away_from_player",
            "player_left_away",
            "player_right_away",
        },
    }
    tier_pools = {
        "approach": ["d4"] * 6_666 + ["d5"] * 6_667,
        "lateral": (
            ["d2"] * 3_000
            + ["d3"] * 3_223
            + ["d4"] * 1_334
            + ["d5"] * 1_333
        ),
        "away_or_stationary": (
            ["d1"] * 8_000
            + ["d2"] * 5_000
            + ["d3"] * 4_777
        ),
    }
    for offset, pool in enumerate(tier_pools.values()):
        random.Random(202_608_170_600 + offset).shuffle(pool)
    offsets = Counter()
    tiers: list[str] = []
    for motion in motions:
        category = next(
            name for name, labels in categories.items() if motion in labels
        )
        index = offsets[category]
        tiers.append(tier_pools[category][index])
        offsets[category] += 1
    if offsets != Counter({name: len(pool) for name, pool in tier_pools.items()}):
        raise RuntimeError(f"motion/tier category mismatch: {offsets}")
    if Counter(tiers) != Counter({f"d{i}": 8_000 for i in range(1, 6)}):
        raise RuntimeError(f"distance tier mismatch: {Counter(tiers)}")
    return motions, tiers


def source_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with SOURCE_MANIFEST.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            distance = math.dist(
                row["player"]["origin"], row["enemy"]["origin"]
            )
            if row["map"] in SOURCE_MAPS and distance >= 380.0:
                rows.append(row)
    if len(rows) < 10_000:
        raise RuntimeError(f"insufficient source candidate pool: {len(rows)}")
    return rows


def source_indexes(
    rows: list[dict[str, Any]],
) -> tuple[dict[tuple[str, ...], list[dict[str, Any]]], dict[tuple[str, ...], list[dict[str, Any]]]]:
    exact: defaultdict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    relaxed: defaultdict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        formal = row["formal_design"]
        base = (
            str(formal["aim_family_bucket"]),
            str(formal["outcome_recipe"]),
            str(row["weapon"]),
            str(formal["player_motion_class"]),
        )
        exact[(*base, str(formal["arm"]))].append(row)
        relaxed[base].append(row)
    return dict(exact), dict(relaxed)


def select_source(
    token: dict[str, Any],
    motion: str,
    ordinal: int,
    exact: dict[tuple[str, ...], list[dict[str, Any]]],
    relaxed: dict[tuple[str, ...], list[dict[str, Any]]],
    source_usage: Counter[str],
    map_usage: Counter[str],
) -> tuple[dict[str, Any], bool, bool]:
    base = (
        token["aim_family_bucket"],
        token["outcome_recipe"],
        token["weapon"],
        token["player_motion_class"],
    )
    candidates = exact.get((*base, token["requested_arm"]), [])
    arm_fallback = False
    if not candidates:
        candidates = relaxed.get(base, [])
        arm_fallback = True
    if not candidates:
        raise RuntimeError(f"no source candidates for {base}")
    if motion.startswith("player_left"):
        preferred_horizontal = {"right", "center"}
    elif motion.startswith("player_right"):
        preferred_horizontal = {"left", "center"}
    else:
        preferred_horizontal = {"left", "center", "right"}
    screen_safe_candidates = [
        row
        for row in candidates
        if str((row.get("initial_screen_design") or {}).get(
            "screen_horizontal"
        ))
        in preferred_horizontal
    ]
    screen_fallback = not bool(screen_safe_candidates)
    if screen_safe_candidates:
        candidates = screen_safe_candidates
    source = min(
        candidates,
        key=lambda row: (
            map_usage[row["map"]],
            source_usage[row["episode_id"]],
            (
                int(row["formal_design"]["ordinal"]) - ordinal
            )
            % PRIMARY_ROWS,
            row["episode_id"],
        ),
    )
    source_usage[source["episode_id"]] += 1
    map_usage[source["map"]] += 1
    return source, arm_fallback, screen_fallback


def constrain_stochastic_view_for_visibility(
    scenario: dict[str, Any],
) -> None:
    """Keep free-aim diversity while preventing deterministic full exits.

    Stage-2 still contains independent two-axis camera motion, but the broad
    legacy ±50 degree arm is inappropriate after adding independent enemy
    motion at the nearest distance tiers.  Normalize every stochastic view
    schedule to a deterministic ±6 degree yaw / ±2.5 degree pitch envelope;
    the declared contract remains 12 by 6 degrees and continues to pass the
    canonical two-axis random-aim validator.
    """
    program = (
        (scenario.get("causal_design") or {})
        .get("weapon_balanced_aim_program")
    ) or {}
    if str(program.get("arm")) not in {
        "stochastic_local",
        "stochastic_broad",
        "visible_no_fire",
    }:
        return
    random_program = program.get("random_aim_program") or {}
    yaw = [float(value) for value in random_program["yaw_offset_deg"]]
    pitch = [float(value) for value in random_program["pitch_offset_deg"]]
    if len(yaw) < 3 or len(pitch) != len(yaw):
        raise RuntimeError("stochastic program is too short to normalize")

    seed = int(random_program["seed"])
    extrema = list(range(1, len(yaw)))
    rng = random.Random(seed ^ 0x5A17E2)
    rng.shuffle(extrema)
    yaw_scale = 5.5 / max(max(abs(value) for value in yaw), 1e-9)
    pitch_scale = 2.25 / max(max(abs(value) for value in pitch), 1e-9)
    normalized_yaw = [
        round(max(-5.5, min(5.5, value * yaw_scale)), 6)
        for value in yaw
    ]
    normalized_pitch = [
        round(max(-2.25, min(2.25, value * pitch_scale)), 6)
        for value in pitch
    ]
    normalized_yaw[0] = 0.0
    normalized_pitch[0] = 0.0
    normalized_yaw[extrema[0]] = 6.0
    normalized_yaw[extrema[1]] = -6.0
    normalized_pitch[extrema[0]] = (
        2.5 if seed % 2 else -2.5
    )
    normalized_pitch[extrema[1]] = -normalized_pitch[extrema[0]]
    random_program.update(
        {
            "yaw_offset_deg": normalized_yaw,
            "pitch_offset_deg": normalized_pitch,
            "max_abs_yaw_offset_deg": 12.0,
            "max_abs_pitch_offset_deg": 6.0,
        }
    )
    program["arm"] = (
        "visible_no_fire"
        if str(program.get("arm")) == "visible_no_fire"
        else "stochastic_local"
    )
    scenario["stochastic_view_visibility_envelope"] = {
        "schema_version": "xonotic-stage2-stochastic-view-envelope-v1",
        "method": "manifest_frozen_two_axis_normalization_v1",
        "maximum_realized_yaw_offset_deg": 6.0,
        "maximum_realized_pitch_offset_deg": 2.5,
        "reads_camera": False,
        "reads_live_enemy_state": False,
        "reads_live_player_state": False,
    }


def formalize_scenario(
    scenario: dict[str, Any],
    *,
    ordinal: int,
    token: dict[str, Any],
    appearance: tuple[str, int],
    color: int,
    authorization: dict[str, Any],
    role: str,
) -> dict[str, Any]:
    scenario = copy.deepcopy(scenario)
    constrain_stochastic_view_for_visibility(scenario)
    trace = scenario.get("prefrozen_trace_source") or None
    if trace is not None:
        original_source_commit = str(trace.get("source_commit", ""))
        trace["source_commit"] = SOURCE_COMMIT
        trace["runtime_recertification"] = {
            "schema_version": (
                "xonotic-stage2-prefrozen-trace-runtime-recertification-v1"
            ),
            "original_source_commit": original_source_commit,
            "runtime_source_commit": SOURCE_COMMIT,
            "method": (
                "replay_immutable_actions_and_fail_closed_compare_live_"
                "player_positions_to_immutable_reference_states"
            ),
            "live_fail_closed": True,
            "runtime_action_fallback": False,
            "runtime_geometry_fallback": False,
        }
    pair_id = f"s2mn5c40v9_g{ordinal:06d}"
    scenario.update(
        {
            "schema_version": "xonotic-stage2-motion-near5-combo-formal-scenario-v9",
            "episode_id": f"s2mn5c40v9_{ordinal:06d}_{role}",
            "anchor_id": pair_id,
            "counterfactual_group_id": pair_id,
            "split": (
                "causal_interaction"
                if role == "active"
                else "paired_counterfactual_qa"
            ),
            "training_stage": "stage2",
            "training_admitted": False,
            "formal_collection_authorized": role == "active",
            "dataset_role": (
                "causal_interaction_enemy_motion_near5_combo_v9"
                if role == "active"
                else "enemy_motion_camera_counterfactual_qa_v9"
            ),
            "target_bin": "stage2_motion_near5_combo_40k_v9",
            "target_ordinal": ordinal,
            "candidate_kind": "stage2_motion_near5_combo_formal_v9",
            "candidate_status": "formal_collection_authorized_pending_live_fail_closed_qa",
            "human_review_required_before_training": False,
            "intent_outcome": token["outcome_recipe"],
            "outcome_recipe_is_individual_admission_gate": False,
            "outcome_label_source": "authoritative_telemetry_only",
            "formal_authorization_basis": authorization,
            "source_commit_required": SOURCE_COMMIT,
            "prefrozen_trace_runtime_recertification": (
                copy.deepcopy(trace.get("runtime_recertification"))
                if trace is not None
                else None
            ),
            "enemy_model": appearance[0],
            "enemy_skin": int(appearance[1]),
            "enemy_color": int(color),
            "appearance_id": f"{appearance[0]}:skin{appearance[1]}",
        }
    )
    formal = copy.deepcopy(scenario.get("formal_design") or {})
    formal.update(
        {
            "schema_version": "xonotic-stage2-motion-near5-combo-formal-design-v9",
            "ordinal": ordinal,
            "cohort": "s2mn5c40v9",
            "cohort_role": "primary",
            "aim_family_bucket": token["aim_family_bucket"],
            "arm": str((scenario.get("causal_design") or {}).get("aim_policy")),
            "outcome_recipe": token["outcome_recipe"],
            "outcome_recipe_is_individual_admission_gate": False,
            "player_motion_class": token["player_motion_class"],
            "distance_bin": "near5_internal_tier",
            "distance_tier": scenario["distance_tier"],
            "target_initial_distance_units": scenario[
                "target_initial_distance_units"
            ],
            "target_motion_name": scenario[
                "action_reference_motion_program"
            ]["primary_motion"],
        }
    )
    scenario["formal_design"] = formal
    labels = copy.deepcopy(scenario.get("policy_labels") or {})
    labels.update(
        {
            "aim_family_bucket": token["aim_family_bucket"],
            "aim_policy": formal["arm"],
            "outcome_recipe": token["outcome_recipe"],
            "outcome_assignment": "post_capture_authoritative_target_damage_per_shot",
            "expected_distance_bin": "near5_internal_tier",
            "expected_distance_tier": scenario["distance_tier"],
            "player_motion_class": token["player_motion_class"],
            "target_motion_name": formal["target_motion_name"],
        }
    )
    scenario["policy_labels"] = labels
    return scenario


def verify_smoke() -> dict[str, Any]:
    summary = json.loads(SMOKE_SUMMARY.read_text(encoding="utf-8"))
    equivalence_path = Path(str(summary.get("equivalence_path", "")))
    if not equivalence_path.is_file():
        raise RuntimeError(
            f"missing full-acceleration equivalence evidence: {equivalence_path}"
        )
    equivalence = json.loads(equivalence_path.read_text(encoding="utf-8"))
    acceleration_checks = summary.get("acceleration_checks") or {}
    checks = {
        "full_acceleration_schema": summary.get("schema_version")
        == "xonotic-stage2-full-acceleration-validation-v1",
        "full_acceleration_gate": summary.get(
            "full_acceleration_gate_passed"
        )
        is True,
        "all_acceleration_checks": bool(acceleration_checks)
        and all(acceleration_checks.values()),
        "runtime_build_tag": summary.get("build_tag") == BUILD_TAG,
        "runtime_source_commit": summary.get("runtime_source_commit")
        == SOURCE_COMMIT,
        "equivalence_schema": equivalence.get("schema_version")
        == "xonotic-stage2-full-accel-equivalence-v2",
        "equivalence_passed": equivalence.get("passed") is True,
        "equivalence_hash": summary.get("equivalence_sha256")
        == sha256_file(equivalence_path),
        "active_samples": summary.get("active_samples") == 9,
        "counterfactual_samples": summary.get("counterfactual_samples") == 9,
        "all_auto_admitted": summary.get("review_admitted_samples") == 9,
        "all_motion_classes": set(
            summary.get("primary_motion_distribution", {})
        )
        == set(pilot.MOTION_LABELS),
        "stage12_precheck": summary.get(
            "stage1_stage2_protection_precheck_passed"
        )
        is True,
        "stage12_postcheck": summary.get(
            "stage1_stage2_protection_postcheck_passed"
        )
        is True,
        "eight_lane_stress": summary.get("workers") == 8
        and summary.get("lane_plan_count") == 8,
        "duel_v8_live_concurrency_eight": (
            summary.get("live_concurrency") == 8
        ),
        "duel_v8_render_concurrency_eight": (
            summary.get("render_concurrency") == 8
        ),
        "duel_v8_global_phase_barrier": acceleration_checks.get(
            "duel_v8_global_phase_barrier"
        )
        is True,
    }
    if not all(checks.values()):
        raise RuntimeError(f"automated smoke gate failed: {checks}")
    return {"checks": checks, "sha256": sha256_file(SMOKE_SUMMARY)}


def main() -> int:
    global SHARD_COUNT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    args = parser.parse_args()
    if not 1 <= args.shard_count <= 64:
        parser.error("--shard-count must be in [1,64]")
    SHARD_COUNT = args.shard_count
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise RuntimeError(f"refusing to overwrite manifest: {output_root}")
    if pilot.SOURCE_COMMIT != SOURCE_COMMIT or pilot.BUILD_TAG != BUILD_TAG:
        raise RuntimeError("production runtime environment does not match lock")
    if not BUILD_LOCK.is_file():
        raise RuntimeError(f"missing build lock: {BUILD_LOCK}")
    smoke = verify_smoke()
    runtime_dependency_locks = verify_runtime_dependencies()

    output_root.mkdir(parents=True)
    shard_root = output_root / f"shards-{SHARD_COUNT:03d}"
    shard_root.mkdir()
    shard_paths = [
        shard_root
        / f"shard-{index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        for index in range(SHARD_COUNT)
    ]
    handles = [path.open("w", encoding="utf-8") for path in shard_paths]

    tokens = build_budget_tokens()
    motions, tiers = motion_and_tier_plan()
    appearances = balanced_values(
        pilot.APPEARANCES, PRIMARY_ROWS, 202_608_170_701
    )
    colors = balanced_values(COLORS, PRIMARY_ROWS, 202_608_170_702)
    tier_targets = {
        row["tier"]: float(row["target_units"])
        for row in pilot.DISTANCE_TIERS
    }
    candidates = source_candidates()
    exact, relaxed = source_indexes(candidates)
    source_usage: Counter[str] = Counter()
    map_usage: Counter[str] = Counter()
    counters: defaultdict[str, Counter[Any]] = defaultdict(Counter)
    arm_fallbacks = 0
    authorization = {
        "schema_version": "xonotic-stage2-motion-near5-combo-formal-authorization-v9",
        "authorization": "explicit_user_request_2026-08-17",
        "manual_review_required": False,
        "automated_smoke_summary": str(SMOKE_SUMMARY),
        "automated_smoke_summary_sha256": smoke["sha256"],
        "automated_smoke_checks": smoke["checks"],
        "source_manifest": str(SOURCE_MANIFEST),
        "source_manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "runtime_build_tag": BUILD_TAG,
        "runtime_source_commit": SOURCE_COMMIT,
        "runtime_lock": str(BUILD_LOCK),
        "runtime_lock_sha256": sha256_file(BUILD_LOCK),
        "runtime_dependency_locks": runtime_dependency_locks,
        "prefrozen_trace_runtime_recertification": (
            "live_fail_closed_against_immutable_reference_states"
        ),
    }
    try:
        for ordinal, token in enumerate(tokens):
            motion = motions[ordinal]
            source, arm_fallback, screen_fallback = select_source(
                token,
                motion,
                ordinal,
                exact,
                relaxed,
                source_usage,
                map_usage,
            )
            arm_fallbacks += int(arm_fallback)
            counters["screen_safe_source_fallback"][
                str(screen_fallback).lower()
            ] += 1
            tier = tiers[ordinal]
            motion_code = next(
                code
                for code, label in pilot.CODE_LABEL.items()
                if label == motion
            )
            design = {
                "index": ordinal,
                "group_id": f"p{ordinal:06d}",
                "motion_label": motion,
                "motion_code": motion_code,
                "desired_outcome": token["outcome_recipe"],
                "desired_model": source["enemy_model"],
                "desired_skin": int(source["enemy_skin"]),
                "desired_weapon": token["weapon"],
                "distance_tier": tier,
                "target_initial_distance_units": tier_targets[tier],
                "program": (
                    (
                        motion_code,
                        pilot.OPPOSITE_MOTION_CODE[motion_code],
                        motion_code,
                        pilot.OPPOSITE_MOTION_CODE[motion_code],
                        motion_code,
                    )
                    if motion_code
                    else (0, 0, 0, 0, 0)
                ),
            }
            active = formalize_scenario(
                pilot.build_scenario(source, design, frozen=False),
                ordinal=ordinal,
                token=token,
                appearance=appearances[ordinal],
                color=colors[ordinal],
                authorization=authorization,
                role="active",
            )
            frozen = formalize_scenario(
                pilot.build_scenario(source, design, frozen=True),
                ordinal=ordinal,
                token=token,
                appearance=appearances[ordinal],
                color=colors[ordinal],
                authorization=authorization,
                role="frozen_qa",
            )
            row = {
                "schema_version": "xonotic-stage2-motion-near5-combo-production-pair-v9",
                "ordinal": ordinal,
                "pair_id": active["counterfactual_group_id"],
                "assigned_shard": ordinal % SHARD_COUNT,
                "shard_count": SHARD_COUNT,
                "source_formal_episode_id": source["episode_id"],
                "source_formal_scenario_sha256": hashlib.sha256(
                    canonical_json(source).encode()
                ).hexdigest(),
                "budget_token": token,
                "requested_arm": token["requested_arm"],
                "realized_manifest_arm": active["formal_design"]["arm"],
                "arm_fallback": arm_fallback,
                "active_scenario": active,
                "frozen_scenario": frozen,
                "raw_avi_audit": ordinal % 20 == 0,
            }
            handles[row["assigned_shard"]].write(canonical_json(row) + "\n")
            counters["outcome"][token["outcome_recipe"]] += 1
            counters["aim_family"][token["aim_family_bucket"]] += 1
            counters["weapon"][token["weapon"]] += 1
            counters["player_motion"][token["player_motion_class"]] += 1
            counters["enemy_motion"][motion] += 1
            counters["distance_tier"][tier] += 1
            counters["appearance"][active["appearance_id"]] += 1
            counters["color"][int(active["enemy_color"])] += 1
            counters["map"][active["map"]] += 1
            counters["source_distance_bin"][
                active["distance_geometry_transform"]["source_distance_bin"]
            ] += 1
            counters["manifest_arm"][active["formal_design"]["arm"]] += 1
            if active.get("stochastic_view_visibility_envelope"):
                counters["stochastic_view_envelope"][
                    "bounded_two_axis_manifest_frozen"
                ] += 1
            basis = active.get("enemy_motion_basis") or {}
            if (
                basis.get("method")
                == "manifest_frozen_initial_line_of_sight_left_tangent_v1"
                and basis.get("reads_camera") is False
                and basis.get("reads_live_player_state") is False
            ):
                counters["enemy_motion_basis"][
                    "frozen_initial_los_left_no_live_reads"
                ] += 1
            if token["player_motion_class"] == PLAYER_MOVING:
                trace = active.get("prefrozen_trace_source") or {}
                recertification = trace.get("runtime_recertification") or {}
                if (
                    trace.get("source_commit") == SOURCE_COMMIT
                    and recertification.get("runtime_source_commit")
                    == SOURCE_COMMIT
                    and recertification.get("live_fail_closed") is True
                    and bool(recertification.get("original_source_commit"))
                ):
                    counters["player_trace_recertification"][
                        "runtime_rebound_live_fail_closed"
                    ] += 1
    finally:
        for handle in handles:
            handle.close()

    shard_records = [
        {
            "shard_index": index,
            "path": str(path.relative_to(output_root)),
            "rows": sum(1 for _ in path.open(encoding="utf-8")),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for index, path in enumerate(shard_paths)
    ]
    expected = {
        "outcome": Counter(
            {
                "no_fire": 6_000,
                "miss": 16_000,
                "hit_survive": 14_000,
                "kill": 4_000,
            }
        ),
        "aim_family": Counter(
            {
                "visible_no_fire": 6_000,
                "precise_tracking": 12_000,
                "humanized_offset_tracking": 12_000,
                "stochastic_aim_and_fire": 10_000,
            }
        ),
        "player_motion": Counter(
            {PLAYER_STATIONARY: 28_000, PLAYER_MOVING: 12_000}
        ),
        "distance_tier": Counter({f"d{i}": 8_000 for i in range(1, 6)}),
    }
    checks = {
        "rows_40000": sum(row["rows"] for row in shard_records)
        == PRIMARY_ROWS,
        "shards_balanced_and_complete": (
            len(shard_records) == SHARD_COUNT
            and sum(row["rows"] for row in shard_records) == PRIMARY_ROWS
            and max(row["rows"] for row in shard_records)
            - min(row["rows"] for row in shard_records)
            <= 1
        ),
        "outcome_budget_exact": counters["outcome"] == expected["outcome"],
        "aim_family_budget_exact": counters["aim_family"]
        == expected["aim_family"],
        "player_motion_budget_exact": counters["player_motion"]
        == expected["player_motion"],
        "distance_tiers_exact": counters["distance_tier"]
        == expected["distance_tier"],
        "all_nine_enemy_motion_classes": set(counters["enemy_motion"])
        == set(pilot.MOTION_LABELS),
        "enemy_motion_balance_max_minus_min_one": (
            max(counters["enemy_motion"].values())
            - min(counters["enemy_motion"].values())
            <= 1
        ),
        "all_nine_weapons": set(counters["weapon"]) == set(pilot.WEAPONS),
        "all_fourteen_appearances": set(counters["appearance"])
        == {f"{model}:skin{skin}" for model, skin in pilot.APPEARANCES},
        "appearance_balance_max_minus_min_one": (
            max(counters["appearance"].values())
            - min(counters["appearance"].values())
            <= 1
        ),
        "all_locked_colors": set(counters["color"]) == set(COLORS),
        "all_selected_maps_present": set(counters["map"]) == set(SOURCE_MAPS),
        "source_pool_large": len(candidates) >= 10_000,
        "source_reuse_bounded": max(source_usage.values()) <= 128,
        "arm_fallback_bounded": arm_fallbacks <= 100,
        "screen_safe_source_fallback_bounded": counters[
            "screen_safe_source_fallback"
        ]["true"]
        <= PRIMARY_ROWS // 10,
        "all_stochastic_views_bounded": counters[
            "stochastic_view_envelope"
        ]["bounded_two_axis_manifest_frozen"]
        == 16_000,
        "all_moving_player_rows_runtime_recertified": counters[
            "player_trace_recertification"
        ]["runtime_rebound_live_fail_closed"]
        == MOVING_PLAYER_ROWS,
        "all_enemy_motion_bases_geometry_derived": counters[
            "enemy_motion_basis"
        ]["frozen_initial_los_left_no_live_reads"]
        == PRIMARY_ROWS,
        "automated_smoke_passed": all(smoke["checks"].values()),
        "runtime_dependency_locks_verified": bool(
            runtime_dependency_locks
        )
        and set(runtime_dependency_locks)
        == {str(path.relative_to(ROOT)) for path in DEPENDENCY_LOCKS},
        "maximum_target_distance_380": max(tier_targets.values()) == 380.0,
        "outcome_not_individual_gate": True,
        "occlusion_excluded_by_live_qa": True,
    }
    audit = {
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-audit-v9",
        "passed": all(checks.values()),
        "checks": checks,
        "rows": PRIMARY_ROWS,
        "training_video_seconds": PRIMARY_ROWS * 5,
        "training_video_hours": PRIMARY_ROWS * 5 / 3600.0,
        "counterfactual_qa_pairs": PRIMARY_ROWS,
        "counterfactual_render_seconds": PRIMARY_ROWS * 5,
        "distributions": {
            name: dict(sorted(values.items(), key=lambda item: str(item[0])))
            for name, values in sorted(counters.items())
        },
        "source_candidate_rows": len(candidates),
        "unique_source_rows_used": len(source_usage),
        "maximum_source_reuse": max(source_usage.values()),
        "arm_fallbacks": arm_fallbacks,
        "shards": shard_records,
    }
    audit_path = output_root / "MANIFEST_AUDIT.json"
    write_json(audit_path, audit)
    metadata = {
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-metadata-v9",
        "formal_collection_authorized": True,
        "training_admitted": False,
        "manual_review_required": False,
        "primary_rows": PRIMARY_ROWS,
        "active_training_hours": PRIMARY_ROWS * 5 / 3600.0,
        "counterfactual_qa_rows": PRIMARY_ROWS,
        "source_commit": SOURCE_COMMIT,
        "build_tag": BUILD_TAG,
        "build_lock": str(BUILD_LOCK),
        "build_lock_sha256": sha256_file(BUILD_LOCK),
        "source_manifest": str(SOURCE_MANIFEST),
        "source_manifest_sha256": authorization["source_manifest_sha256"],
        "automated_smoke_summary": str(SMOKE_SUMMARY),
        "automated_smoke_summary_sha256": smoke["sha256"],
        "runtime_dependency_locks": runtime_dependency_locks,
        "runtime_files": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (
                ROOT / "pilot_scripts/build_samples.py",
                ROOT / "production_scripts/prepare_stage2_motion_40k_manifest.py",
                ROOT / "production_scripts/run_stage2_motion_40k_shard.py",
                ROOT / "production_scripts/launch_dlc_8x1.sh",
                ROOT / "production_scripts/launch_dlc_12x1.sh",
                ROOT / "scripts/xonotic_stage1_reusable.py",
            )
        },
        "shard_count": SHARD_COUNT,
        "shards": shard_records,
        "manifest_audit": str(audit_path.relative_to(output_root)),
        "manifest_audit_sha256": sha256_file(audit_path),
        "distribution_policy": {
            "outcome_recipe_is_individual_admission_gate": False,
            "actual_outcome_source": "authoritative_telemetry_only",
            "occlusion_training_allowed": False,
            "partial_edge_crop_allowed": True,
            "full_offscreen_allowed": False,
            "stochastic_view_envelope_degrees": {
                "yaw_realized": 6.0,
                "pitch_realized": 2.5,
            },
            "lateral_screen_source_preference": (
                "opposite_or_center_when_exact_source_stratum_available;"
                "otherwise_live_visibility_fail_closed"
            ),
            "distance_tier_in_prompt": False,
            "prompt_schedule": "5x0.8s",
            "fixed_enemy_speed_units_per_second": pilot.SPEED_UNITS_PER_SECOND,
            "enemy_motion_basis": (
                "manifest_frozen_initial_line_of_sight_left_tangent_v1"
            ),
            "enemy_motion_reads_live_camera_or_player": False,
            "radial_deconfounding": (
                "active_minus_frozen_enemy_displacement_projected_on_"
                "manifest_frozen_initial_radial_axis_v1"
            ),
        },
    }
    metadata_path = output_root / "MANIFEST_METADATA.json"
    write_json(metadata_path, metadata)
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(
                    f"{sha256_file(path)}  {path.relative_to(output_root)}\n"
                )
    if not audit["passed"]:
        raise RuntimeError(f"manifest audit failed: {checks}")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
