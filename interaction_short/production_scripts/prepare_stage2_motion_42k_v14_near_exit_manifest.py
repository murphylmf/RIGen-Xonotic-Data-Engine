                      
"""Build the isolated v14 Stage-2 manifest with near-only exit quotas.

The final accepted visibility distribution is enforced by three independent
per-shard quota pools: 90% always-visible, 5% exit-hold, and 5% reacquire.
Exit programs use only d1/d2 geometry and five prompt-controlled pure-lateral
blocks.  The isolated render overlay removes the crosshair.  All 42,000 source
primary rows are retained exactly once, so aggregate source marginals remain
unchanged.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "production_scripts"))

import prepare_stage2_motion_42k_v13_temporal_visibility_manifest as v13              


SOURCE_ROOT = (
    ROOT
    / "manifests/stage2_motion_near5_combo_42k_v12_replenish_28shard_20260818_r5"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_motion_temporal_visibility_42k_v14_near_exit_90_5_5_nocrosshair_28shard_20260820_r4"
)
RUNTIME_LOCK = (
    ROOT / "locks/stage2_motion_7x4_activeonly_v14r4_resilient_runtime.sha256"
)
CROSSHAIR_OVERLAY = ROOT / "configs/capture_client_stage2_v14_no_crosshair.cfg"
BUILD_TAG = v13.BUILD_TAG
SOURCE_COMMIT = v13.SOURCE_COMMIT
BUILD_LOCK = v13.BUILD_LOCK
SHARD_COUNT = 28
PRIMARY_PER_SHARD = 1_500
PRIMARY_ROWS = SHARD_COUNT * PRIMARY_PER_SHARD
MOTION_SPEED = 64.0
SEMANTIC_REVISION = "v14_near_exit_90_5_5_nocrosshair"
SAMPLE_PREFIX = "s2mtv42v14r4"

CATEGORY_PLAN = {
    "always_visible": {
        "target_per_shard": 1_350,
        "reserve_per_shard": 400,
    },
    "exit_hold": {
        "target_per_shard": 75,
        "reserve_per_shard": 525,
    },
    "exit_reacquire": {
        "target_per_shard": 75,
        "reserve_per_shard": 225,
    },
}
FAMILY_QUOTAS = dict(v13.FAMILY_QUOTAS)
HUMANIZED_ARMS = set(v13.HUMANIZED_ARMS)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    return v13.sha256_file(path)


def write_json(path: Path, value: Any) -> None:
    v13.write_json(path, value)


def stable_digest(row: dict[str, Any], salt: str) -> str:
    return hashlib.sha256(
        f"stage2-v14:{salt}:{row['sample_key']}".encode()
    ).hexdigest()


def stable_index(row: dict[str, Any], salt: str, modulus: int) -> int:
    return int(stable_digest(row, salt)[:16], 16) % modulus


                                                                           
                                                                            
                                                                           
v13.stable_digest = stable_digest
v13.stable_index = stable_index


def outward_code(row: dict[str, Any], salt: str) -> int:
    horizontal = str(
        (row["active_scenario"].get("initial_screen_design") or {}).get(
            "screen_horizontal", "center"
        )
    )
    if horizontal == "left":
        return 1
    if horizontal == "right":
        return 2
    return 1 if stable_index(row, salt + "-side", 2) == 0 else 2


v13.outward_code = outward_code


def scenario(row: dict[str, Any]) -> dict[str, Any]:
    return row["active_scenario"]


def outcome(row: dict[str, Any]) -> str:
    return str(scenario(row)["intent_outcome"])


def arm(row: dict[str, Any]) -> str:
    return str(
        scenario(row)["causal_design"]["weapon_balanced_aim_program"]["arm"]
    )


def jump(row: dict[str, Any]) -> bool:
    return bool(scenario(row)["enemy_jump_program"]["enabled"])


def tier(row: dict[str, Any]) -> str:
    return str(scenario(row)["distance_tier"])


def take_exact(
    rows: Iterable[dict[str, Any]],
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
            f"selection shortage {salt}: need={count} eligible={len(eligible)}"
        )
    selected = eligible[:count]
    used.update(str(row["sample_key"]) for row in selected)
    return selected


def assign_primary_designs(
    primary: list[dict[str, Any]],
) -> dict[str, tuple[str, str]]:
    used: set[str] = set()
    assigned: dict[str, tuple[str, str]] = {}

    stationary = take_exact(
        primary,
        FAMILY_QUOTAS["stationary"],
        "stationary",
        used,
        lambda row: v13.old_stationary(row) and not jump(row),
    )
    for row in stationary:
        assigned[str(row["sample_key"])] = ("stationary", "always_visible")

                                                                            
                                                                           
               
    for shard_index in range(SHARD_COUNT):
        local = [
            row
            for row in primary
            if int(row["assigned_shard"]) == shard_index
        ]
        if shard_index % 2 == 0:
            reacquire_cells = (
                ("d1", "miss", 19),
                ("d1", "hit_survive", 19),
                ("d2", "miss", 19),
                ("d2", "hit_survive", 18),
            )
        else:
            reacquire_cells = (
                ("d1", "miss", 18),
                ("d1", "hit_survive", 19),
                ("d2", "miss", 19),
                ("d2", "hit_survive", 19),
            )
        for wanted_tier, wanted_outcome, count in reacquire_cells:
            selected = take_exact(
                local,
                count,
                f"reacquire-s{shard_index}-{wanted_tier}-{wanted_outcome}",
                used,
                lambda row, wt=wanted_tier, wo=wanted_outcome: (
                    tier(row) == wt
                    and outcome(row) == wo
                    and arm(row) in HUMANIZED_ARMS
                    and not jump(row)
                    and not v13.old_stationary(row)
                ),
            )
            for row in selected:
                assigned[str(row["sample_key"])] = (
                    "single_direction",
                    "exit_reacquire",
                )

        hold_cells: tuple[tuple[str, str, int], ...] = (
            ("d1", "miss", 25),
            ("d2", "miss", 25),
            ("d1", "no_fire", 13 if shard_index % 2 == 0 else 12),
            ("d2", "no_fire", 12 if shard_index % 2 == 0 else 13),
        )
        for wanted_tier, wanted_outcome, count in hold_cells:
            selected = take_exact(
                local,
                count,
                f"exit-hold-s{shard_index}-{wanted_tier}-{wanted_outcome}",
                used,
                lambda row, wt=wanted_tier, wo=wanted_outcome: (
                    tier(row) == wt
                    and outcome(row) == wo
                    and not jump(row)
                    and not v13.old_stationary(row)
                ),
            )
            for row in selected:
                assigned[str(row["sample_key"])] = (
                    "single_direction",
                    "exit_hold",
                )

                                                                          
                                                                            
                                                                            
    for wanted_tier in ("d3", "d4", "d5"):
        selected = take_exact(
            primary,
            2_800,
            f"always-single-{wanted_tier}",
            used,
            lambda row, wt=wanted_tier: tier(row) == wt,
        )
        for row in selected:
            assigned[str(row["sample_key"])] = (
                "single_direction",
                "always_visible",
            )

    remaining = [
        row for row in primary if str(row["sample_key"]) not in used
    ]
    remaining.sort(key=lambda row: stable_digest(row, "remaining-family"))
    cursor = 0
    for family in (
        "move_stop",
        "one_direction_change",
        "two_nonperiodic_changes",
        "repeated_back_and_forth",
    ):
        already_assigned = sum(
            assigned_family == family
            for assigned_family, _ in assigned.values()
        )
        count = FAMILY_QUOTAS[family] - already_assigned
        if count < 0:
            raise RuntimeError(
                f"preassigned family exceeds quota: {family} "
                f"{already_assigned}>{FAMILY_QUOTAS[family]}"
            )
        selected = remaining[cursor : cursor + count]
        if len(selected) != count:
            raise RuntimeError(f"remaining family shortage: {family}")
        cursor += count
        for row in selected:
            assigned[str(row["sample_key"])] = (family, "always_visible")
    if cursor != len(remaining) or len(assigned) != PRIMARY_ROWS:
        raise RuntimeError(
            f"assignment mismatch cursor={cursor} remaining={len(remaining)} "
            f"assigned={len(assigned)}"
        )
    return assigned


def transform_row(
    source: dict[str, Any],
    family: str,
    visibility_class: str,
    ordinal: int,
) -> dict[str, Any]:
    row = v13.transform_row(source, family, visibility_class, ordinal)
    sample_key = f"{SAMPLE_PREFIX}_{ordinal:06d}"
    episode_id = f"{sample_key}_active"
    row["sample_key"] = sample_key
    row["semantic_revision"] = SEMANTIC_REVISION
    row["ordinal"] = ordinal
    row["raw_avi_audit"] = ordinal % 20 == 0
    active = row["active_scenario"]
    active.update(
        {
            "schema_version": "xonotic-stage2-motion-interaction-scenario-v14-near-exit-balanced",
            "episode_id": episode_id,
            "anchor_id": sample_key,
            "counterfactual_group_id": sample_key,
            "candidate_kind": "stage2_motion_temporal_visibility_v14_near_exit",
            "dataset_role": "causal_interaction_enemy_motion_temporal_visibility_v14",
            "target_bin": "stage2_motion_temporal_visibility_42k_v14_near_exit_90_5_5_nocrosshair",
            "target_ordinal": ordinal,
        }
    )
    active["enemy_policy"]["name"] = (
        "fixed_speed_prompt_block_temporal_program_v14_near_exit"
    )
    active["formal_design"].update(
        {
            "schema_version": "xonotic-stage2-motion-temporal-visibility-formal-design-v14",
            "cohort": SAMPLE_PREFIX,
            "ordinal": ordinal,
            "accepted_visibility_target": visibility_class,
        }
    )
    authorization = active["formal_authorization_basis"]
    authorization.pop("v13_change_authorization", None)
    authorization.pop("v13_change_scope", None)
    authorization.update(
        {
            "v14_change_authorization": "explicit_user_request_2026-08-20",
            "v14_change_scope": [
                "accepted_visibility_distribution_90_5_5",
                "exit_classes_near_only_d1_d2",
                "exit_motion_pure_lateral_only",
                "exit_hold_five_same_direction_blocks",
                "far_single_direction_always_visible",
                "crosshair_disabled_by_isolated_client_overlay",
                "category_isolated_quota_replenishment",
                "preserve_source_marginals_and_interaction_contract",
            ],
        }
    )
    row["budget_token"].update(
        {
            "cohort": SAMPLE_PREFIX,
            "accepted_visibility_target": visibility_class,
        }
    )
    return row


def make_reserve_source(
    source: dict[str, Any], reserve_index: int
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    source_key = str(source["sample_key"])
    active = row["active_scenario"]
    active["seed"] = int(active["seed"]) + 50_000_000 + reserve_index
    active["enemy_policy"]["policy_seed"] = int(active["seed"]) + 1_000_000
    if active.get("prefrozen_trace_source"):
        active["prefrozen_trace_source"]["scenario_seed_relation"] = (
            "independent_replenishment_scenario_seed"
        )
    active["reserve_transform"] = {
        "schema_version": "xonotic-stage2-v14-near-exit-reserve-transform-v1",
        "source_sample_key": source_key,
        "source_scenario_sha256": hashlib.sha256(
            canonical_json(source["active_scenario"]).encode()
        ).hexdigest(),
        "camera_and_player_action_program_unchanged": True,
        "independent_scenario_seed": True,
    }
    row.update(
        {
            "candidate_role": "reserve",
            "sample_key": f"{SAMPLE_PREFIX}r_source_{reserve_index:06d}",
            "reserve_source_sample_key": source_key,
            "reserve_source_ordinal": int(source["ordinal"]),
        }
    )
    row["budget_token"].update(
        {
            "cohort": SAMPLE_PREFIX,
            "cohort_role": "category_replenishment_reserve",
            "source_sample_key": source_key,
        }
    )
    return row


def distribution(
    rows: Iterable[dict[str, Any]], key: Callable[[dict[str, Any]], Any]
) -> dict[str, int]:
    return dict(sorted(Counter(str(key(row)) for row in rows).items()))


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


def runtime_files() -> list[Path]:
    return [
        ROOT / "pilot_scripts/build_samples.py",
        ROOT / "pilot_scripts/build_samples_v12.py",
        ROOT / "pilot_scripts/build_samples_v13.py",
        CROSSHAIR_OVERLAY,
        ROOT / "production_scripts/gpu_memory_holder.py",
        ROOT / "production_scripts/prepare_stage2_motion_42k_v13_temporal_visibility_manifest.py",
        ROOT / "production_scripts/prepare_stage2_motion_42k_v14_near_exit_manifest.py",
        ROOT / "production_scripts/run_stage2_motion_40k_shard_v12_support.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v12r6_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v14_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v14_multigpu.py",
        ROOT / "production_scripts/launch_dlc_7x4_activeonly_v14_resilient.py",
        ROOT / "production_scripts/launch_dlc_7x4_activeonly_v14_resilient.sh",
        ROOT / "scripts/xonotic_stage1_reusable.py",
        ROOT / "scripts/xonotic_stage2_causal_formal.py",
    ]


def write_runtime_lock() -> dict[str, str]:
    files = runtime_files()
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing v14 runtime files: {missing}")
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


def write_manifest(
    source_rows: list[dict[str, Any]],
    output_root: Path,
    runtime: dict[str, str],
) -> None:
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite manifest root: {output_root}")
    primary_source = [
        row for row in source_rows if row["candidate_role"] == "primary"
    ]
    assignment = assign_primary_designs(primary_source)
    primary_transformed: list[dict[str, Any]] = []
    primary_source_by_new_key: dict[str, dict[str, Any]] = {}
    design_by_new_key: dict[str, tuple[str, str]] = {}
    for ordinal, source in enumerate(primary_source):
        family, visibility_class = assignment[str(source["sample_key"])]
        transformed = transform_row(source, family, visibility_class, ordinal)
        primary_transformed.append(transformed)
        primary_source_by_new_key[transformed["sample_key"]] = source
        design_by_new_key[transformed["sample_key"]] = (family, visibility_class)

    transformed = list(primary_transformed)
    reserve_index = 0
    ordinal = PRIMARY_ROWS
    for shard_index in range(SHARD_COUNT):
        for visibility_class, plan in CATEGORY_PLAN.items():
            local = [
                row
                for row in primary_transformed
                if int(row["assigned_shard"]) == shard_index
                and scenario(row)["visibility_design"]["class"]
                == visibility_class
            ]
            local.sort(key=lambda row: stable_digest(row, "reserve-source"))
            expected_primary = int(plan["target_per_shard"])
            if len(local) != expected_primary:
                raise RuntimeError(
                    f"primary category mismatch shard={shard_index} "
                    f"class={visibility_class} found={len(local)} "
                    f"expected={expected_primary}"
                )
            for offset in range(int(plan["reserve_per_shard"])):
                primary_row = local[offset % len(local)]
                source = primary_source_by_new_key[primary_row["sample_key"]]
                family, declared_visibility = design_by_new_key[
                    primary_row["sample_key"]
                ]
                reserve_source = make_reserve_source(source, reserve_index)
                transformed.append(
                    transform_row(
                        reserve_source,
                        family,
                        declared_visibility,
                        ordinal,
                    )
                )
                reserve_index += 1
                ordinal += 1

    transformed.sort(key=lambda row: int(row["ordinal"]))
    candidate_rows = len(transformed)
    expected_candidates = SHARD_COUNT * sum(
        int(plan["target_per_shard"]) + int(plan["reserve_per_shard"])
        for plan in CATEGORY_PLAN.values()
    )
    if candidate_rows != expected_candidates:
        raise RuntimeError(
            f"candidate count mismatch {candidate_rows} != {expected_candidates}"
        )

    output_root.mkdir(parents=True)
    category_specs: dict[str, Any] = {}
    for visibility_class, plan in CATEGORY_PLAN.items():
        category_root = output_root / "categories" / visibility_class
        shard_root = category_root / "shards-028"
        shard_root.mkdir(parents=True)
        shards: list[dict[str, Any]] = []
        for shard_index in range(SHARD_COUNT):
            selected = [
                row
                for row in transformed
                if int(row["assigned_shard"]) == shard_index
                and scenario(row)["visibility_design"]["class"]
                == visibility_class
            ]
            selected.sort(
                key=lambda row: (
                    row["candidate_role"] != "primary",
                    int(row["ordinal"]),
                )
            )
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
                    "target_accepted_rows": int(plan["target_per_shard"]),
                    "sha256": sha256_file(path),
                }
            )
        category_specs[visibility_class] = {
            "accepted_target_rows": SHARD_COUNT
            * int(plan["target_per_shard"]),
            "candidate_rows": sum(shard["rows"] for shard in shards),
            "target_per_shard": int(plan["target_per_shard"]),
            "reserve_per_shard": int(plan["reserve_per_shard"]),
            "shards": shards,
        }

    primary = [row for row in transformed if row["candidate_role"] == "primary"]
    reserve = [row for row in transformed if row["candidate_role"] == "reserve"]
    family = lambda row: scenario(row)["motion_sequence_design"]["family"]
    visibility = lambda row: scenario(row)["visibility_design"]["class"]
    distance = lambda row: scenario(row)["distance_tier"]
    source_marginal_keys = {
        "intent_outcome": lambda row: scenario(row)["intent_outcome"],
        "weapon": lambda row: scenario(row)["weapon"],
        "map": lambda row: scenario(row)["map"],
        "enemy_model": lambda row: scenario(row)["enemy_model"],
        "distance_tier": distance,
        "player_motion_class": lambda row: row["budget_token"][
            "player_motion_class"
        ],
        "enemy_jumps": lambda row: scenario(row)["enemy_jump_program"][
            "enabled"
        ],
    }
    source_primary_distributions = {
        key: distribution(primary_source, fn)
        for key, fn in source_marginal_keys.items()
    }
    new_primary_distributions = {
        key: distribution(primary, fn) for key, fn in source_marginal_keys.items()
    }
    visibility_counts = distribution(primary, visibility)
    family_counts = distribution(primary, family)
    accepted_visibility_targets = {
        key: SHARD_COUNT * int(plan["target_per_shard"])
        for key, plan in CATEGORY_PLAN.items()
    }
    checks = {
        "primary_rows_42000": len(primary) == PRIMARY_ROWS,
        "candidate_rows_74200": candidate_rows == 74_200,
        "sample_keys_unique": len({row["sample_key"] for row in transformed})
        == candidate_rows,
        "ordinals_complete": [int(row["ordinal"]) for row in transformed]
        == list(range(candidate_rows)),
        "accepted_visibility_targets_90_5_5": accepted_visibility_targets
        == {
            "always_visible": 37_800,
            "exit_hold": 2_100,
            "exit_reacquire": 2_100,
        },
        "primary_visibility_counts_match_targets": visibility_counts
        == accepted_visibility_targets,
        "family_quotas_preserved": family_counts
        == {key: FAMILY_QUOTAS[key] for key in sorted(FAMILY_QUOTAS)},
        "source_marginals_preserved": source_primary_distributions
        == new_primary_distributions,
        "exit_near_only": all(
            distance(row) in {"d1", "d2"}
            for row in transformed
            if visibility(row) in {"exit_hold", "exit_reacquire"}
        ),
        "exit_pure_lateral_only": all(
            set(scenario(row)["enemy_motion_program"]["direction_codes"])
            <= {1, 2}
            for row in transformed
            if visibility(row) in {"exit_hold", "exit_reacquire"}
        ),
        "exit_hold_five_same_direction_blocks": all(
            len(scenario(row)["enemy_motion_program"]["direction_codes"]) == 5
            and len(set(scenario(row)["enemy_motion_program"]["direction_codes"]))
            == 1
            and scenario(row)["enemy_motion_program"]["direction_codes"][0]
            in {1, 2}
            for row in transformed
            if visibility(row) == "exit_hold"
        ),
        "far_single_direction_always_visible": all(
            visibility(row) == "always_visible"
            for row in transformed
            if family(row) == "single_direction"
            and distance(row) in {"d3", "d4", "d5"}
        ),
        "category_shards_exact": all(
            shard["primary_rows"] == spec["target_per_shard"]
            and shard["reserve_rows"] == spec["reserve_per_shard"]
            and shard["target_accepted_rows"] == spec["target_per_shard"]
            for spec in category_specs.values()
            for shard in spec["shards"]
        ),
        "no_frozen_scenario": all(
            "frozen_scenario" not in row for row in transformed
        ),
        "occlusion_excluded": all(
            scenario(row)["visibility_design"]["occlusion_allowed"] is False
            for row in transformed
        ),
        "crosshair_overlay_runtime_locked": runtime.get(
            str(CROSSHAIR_OVERLAY.relative_to(ROOT))
        )
        == sha256_file(CROSSHAIR_OVERLAY),
    }
    audit = {
        "schema_version": "xonotic-stage2-motion-temporal-visibility-manifest-audit-v14",
        "passed": all(checks.values()),
        "checks": checks,
        "primary_rows": len(primary),
        "reserve_rows": len(reserve),
        "candidate_rows": candidate_rows,
        "accepted_visibility_target": accepted_visibility_targets,
        "primary_visibility_class": visibility_counts,
        "motion_sequence_family": family_counts,
        "preserved_primary_distributions": new_primary_distributions,
        "joint_distributions": {
            "visibility_x_distance": joint_distribution(
                primary, visibility, distance
            ),
            "visibility_x_outcome": joint_distribution(
                primary, visibility, lambda row: scenario(row)["intent_outcome"]
            ),
            "family_x_distance": joint_distribution(primary, family, distance),
        },
        "category_specs": category_specs,
        "source_manifest_root": str(SOURCE_ROOT),
        "old_artifacts_modified": False,
    }
    write_json(output_root / "MANIFEST_AUDIT.json", audit)
    metadata = {
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-metadata-v12-replenish",
        "semantic_schema_version": "xonotic-stage2-motion-temporal-visibility-manifest-v14",
        "semantic_revision": SEMANTIC_REVISION,
        "capture_mode": "active_only",
        "qa_mode": "single_episode_authoritative",
        "formal_collection_authorized": True,
        "training_admitted": False,
        "manual_review_required": False,
        "primary_rows": PRIMARY_ROWS,
        "rendered_episode_rows": PRIMARY_ROWS,
        "candidate_rows": candidate_rows,
        "counterfactual_qa_rows": 0,
        "source_commit": SOURCE_COMMIT,
        "build_tag": BUILD_TAG,
        "build_lock": str(BUILD_LOCK),
        "build_lock_sha256": sha256_file(BUILD_LOCK),
        "runtime_lock": str(RUNTIME_LOCK),
        "runtime_lock_sha256": sha256_file(RUNTIME_LOCK),
        "runtime_files": runtime,
        "capture_client_overlay": str(CROSSHAIR_OVERLAY),
        "capture_client_overlay_sha256": sha256_file(CROSSHAIR_OVERLAY),
        "runtime_dependency_locks": json.loads(
            (SOURCE_ROOT / "MANIFEST_METADATA.json").read_text(encoding="utf-8")
        )["runtime_dependency_locks"],
        "live_time_scale": 2,
        "shard_count": SHARD_COUNT,
        "categories": category_specs,
        "manifest_audit": "MANIFEST_AUDIT.json",
        "distribution_policy": {
            "accepted_visibility_class_quotas": accepted_visibility_targets,
            "motion_sequence_family_quotas": FAMILY_QUOTAS,
            "exit_distance_tiers": ["d1", "d2"],
            "exit_direction_codes": [1, 2],
            "exit_hold_program": "five_same_outward_direction_blocks",
            "far_exit_required": False,
            "fixed_enemy_speed_units_per_second": MOTION_SPEED,
            "prompt_schedule": "5x0.8s",
            "relative_direction_only": True,
            "category_isolated_quota_replenishment": True,
            "occlusion_training_allowed": False,
            "crosshair_visible": False,
            "source_marginals_preserved": True,
        },
        "source_manifest_root": str(SOURCE_ROOT),
        "old_artifacts_modified": False,
    }
    write_json(output_root / "MANIFEST_METADATA.json", metadata)
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(
                    f"{sha256_file(path)}  {path.relative_to(output_root)}\n"
                )
    if not audit["passed"]:
        raise RuntimeError(f"v14 manifest audit failed: {checks}")
    print(json.dumps(audit, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    source_rows = v13.load_source_rows(args.source_root.resolve())
    runtime = write_runtime_lock()
    write_manifest(source_rows, args.output_root.resolve(), runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
