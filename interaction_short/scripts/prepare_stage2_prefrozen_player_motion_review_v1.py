                      
"""Create immutable Stage-2 player-motion candidates over the v1 review.

The existing 27 stationary episodes remain the control cohort.  This script
creates two independently pre-frozen movement groups per weapon, with all
three stochastic aim/fire arms sharing exactly the same player movement and
enemy trajectory inside a group.  Selection happens only after every
candidate has completed fail-closed live QA.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_stochastic_review_v1 as stochastic_v1              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_stochastic_review_v1/input.jsonl"
)
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_prefrozen_player_motion_review_v1"
)
SHARD_COUNT = 4
MOTION_PROFILES = causal.PLAYER_MOVEMENT_PROGRAM_PROFILES
MANIFEST_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-review-manifest-v1"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-review-design-v1"
)
SELECTION_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-selection-contract-v1"
)
BASELINE_HITS = 35
BASELINE_SHOTS = 113
BASELINE_WEAPONS_WITH_HIT = 8
HARD_PRESERVATION_FRACTION = 0.80
TARGET_PRESERVATION_FRACTION = 0.90
HARD_MINIMUM_HITS = math.ceil(
    BASELINE_HITS * HARD_PRESERVATION_FRACTION
)
TARGET_MINIMUM_HITS = math.ceil(
    BASELINE_HITS * TARGET_PRESERVATION_FRACTION
)
HARD_MINIMUM_HIT_RATE = (
    BASELINE_HITS
    / BASELINE_SHOTS
    * HARD_PRESERVATION_FRACTION
)
TARGET_MINIMUM_HIT_RATE = (
    BASELINE_HITS
    / BASELINE_SHOTS
    * TARGET_PRESERVATION_FRACTION
)
HARD_MINIMUM_WEAPONS_WITH_HIT = 7


def source_commit() -> str:
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT / "source/release-src-0.8.6/Xonotic"),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(
        capture.canonical_json(row) + "\n" for row in rows
    )


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_prefrozen_motion_manifest_drift",
                str(path),
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def player_movement_program(
    seed: int, profile: str
) -> dict[str, Any]:
    """Return one mild, cancelling, manifest-frozen movement schedule."""
    if profile not in MOTION_PROFILES:
        raise ValueError(profile)
    rng = random.Random(seed)
    ticks = [0, 40, 80, 120, 160, 200, 240, 280, 319]
    major = rng.uniform(0.20, 0.28)
    minor = rng.uniform(0.10, 0.17)
    jitter = [rng.uniform(0.88, 1.0) for _ in range(7)]
    if profile == "lateral_weave":
        x_pattern = [1.0, 0.65, -0.8, -1.0, 0.7, 1.0, -0.55]
        y_pattern = [-0.8, -0.35, 0.75, 1.0, 0.4, -0.9, 0.65]
        x_scale, y_scale = major, minor
    else:
        x_pattern = [0.75, -0.8, -0.35, 0.9, 0.45, -1.0, 0.7]
        y_pattern = [-1.0, -0.7, 0.45, 1.0, 0.55, -0.9, 0.65]
        x_scale, y_scale = minor, major
    left_x = [0.0] + [
        round(value * x_scale * jitter[index], 6)
        for index, value in enumerate(x_pattern)
    ] + [0.0]
    left_y = [0.0] + [
        round(value * y_scale * jitter[-1 - index], 6)
        for index, value in enumerate(y_pattern)
    ] + [0.0]
    bound = round(max(abs(value) for value in left_x + left_y), 6)
    program = {
        "schema_version": causal.PLAYER_MOVEMENT_PROGRAM_SCHEMA,
        "seed": seed,
        "algorithm": (
            "manifest_frozen_piecewise_smooth_player_movement_v1"
        ),
        "interpolation": "smoothstep",
        "profile": profile,
        "knot_output_ticks": ticks,
        "j_left_x": left_x,
        "j_left_y": left_y,
        "max_abs_axis_value": bound,
        "jump_enabled": False,
        "reads_live_enemy_state": False,
        "reads_live_player_state": False,
        "reads_camera": False,
        "reads_crosshair": False,
    }
    causal.validate_player_movement_program(program)
    return program


def direction_reversals(values: list[float]) -> int:
    signs = [
        1 if value > 1e-5 else -1
        for value in values
        if abs(value) > 1e-5
    ]
    return sum(
        left != right for left, right in zip(signs, signs[1:])
    )


def static_action_certificate(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    actions = causal.causal_action_rows(scenario)
    warmup = actions[: capture.WARMUP_TICKS]
    output = actions[capture.WARMUP_TICKS :]
    left_x = [
        float(row["strafe"])
        / capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE
        for row in output
    ]
    left_y = [
        -float(row["forward"])
        / capture.MODEL_ACTION_MOVEMENT_USERCMD_SCALE
        for row in output
    ]
    yaw = [float(row["yaw_delta"]) for row in output]
    pitch = [float(row["pitch_delta"]) for row in output]
    primary = [bool(row["primary"]) for row in output]
    checks = {
        "rows_exact": len(actions) == capture.TOTAL_TICKS,
        "warmup_neutral": all(
            float(row["forward"]) == 0.0
            and float(row["strafe"]) == 0.0
            and float(row["yaw_delta"]) == 0.0
            and float(row["pitch_delta"]) == 0.0
            and int(row["jump"]) == 0
            and int(row["primary"]) == 0
            for row in warmup
        ),
        "movement_present": sum(
            math.hypot(x, y) > 0.05
            for x, y in zip(left_x, left_y)
        )
        >= 192,
        "two_axis_movement": any(abs(value) > 0.05 for value in left_x)
        and any(abs(value) > 0.05 for value in left_y),
        "movement_reversal": direction_reversals(left_x) >= 1
        and direction_reversals(left_y) >= 1,
        "movement_in_model_range": max(
            abs(value) for value in left_x + left_y
        )
        <= 1.0,
        "jump_absent": not any(int(row["jump"]) for row in actions),
        "two_axis_view": any(abs(value) > 1e-5 for value in yaw)
        and any(abs(value) > 1e-5 for value in pitch),
        "view_in_model_range": max(abs(value) for value in yaw) <= 12.0
        and max(abs(value) for value in pitch) <= 12.0,
        "fire_present": any(primary),
        "secondary_absent": not any(
            bool(row["secondary"]) for row in output
        ),
    }
    return {
        "schema_version": (
            "xonotic-stage2-prefrozen-player-motion-static-action-"
            "certificate-v1"
        ),
        "checks": checks,
        "passed": all(checks.values()),
        "movement_active_frames": sum(
            math.hypot(x, y) > 0.05
            for x, y in zip(left_x, left_y)
        ),
        "maximum_abs_left_x": max(abs(value) for value in left_x),
        "maximum_abs_left_y": max(abs(value) for value in left_y),
        "left_x_direction_reversals": direction_reversals(left_x),
        "left_y_direction_reversals": direction_reversals(left_y),
        "actions_sha256": hashlib.sha256(
            capture.canonical_json(actions).encode("utf-8")
        ).hexdigest(),
    }


def selection_contract() -> dict[str, Any]:
    return {
        "schema_version": SELECTION_SCHEMA,
        "selection_unit": (
            "whole_three_arm_counterfactual_group_per_weapon"
        ),
        "candidate_groups_per_weapon": 2,
        "selected_groups_per_weapon": 1,
        "candidate_outcomes_are_never_episode_acceptance_gates": True,
        "all_candidate_artifacts_retained": True,
        "eligible_group_requires_all_three_episodes_accepted": True,
        "eligible_group_requires_all_live_player_motion_qa": True,
        "profile_balance": {
            "lateral_weave_selected_weapon_groups": [4, 5],
            "approach_retreat_selected_weapon_groups": [4, 5],
        },
        "baseline": {
            "manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "output_root": "stage2_stochastic_review_v1_output",
            "episodes": 27,
            "shots": BASELINE_SHOTS,
            "confirmed_hits": BASELINE_HITS,
            "confirmed_hit_rate": BASELINE_HITS / BASELINE_SHOTS,
            "weapons_with_confirmed_hit": BASELINE_WEAPONS_WITH_HIT,
        },
        "hard_floor": {
            "preservation_fraction": HARD_PRESERVATION_FRACTION,
            "minimum_confirmed_hits": HARD_MINIMUM_HITS,
            "minimum_confirmed_hit_rate": HARD_MINIMUM_HIT_RATE,
            "minimum_weapons_with_confirmed_hit": (
                HARD_MINIMUM_WEAPONS_WITH_HIT
            ),
        },
        "target": {
            "preservation_fraction": TARGET_PRESERVATION_FRACTION,
            "minimum_confirmed_hits": TARGET_MINIMUM_HITS,
            "minimum_confirmed_hit_rate": TARGET_MINIMUM_HIT_RATE,
        },
        "optimization_order": [
            "maximize_weapons_with_confirmed_hit",
            "maximize_total_confirmed_hits",
            "maximize_confirmed_hit_rate",
            "lexicographic_counterfactual_group_ids",
        ],
        "failure_policy": (
            "fail_closed_and_create_new_immutable_replenishment_cohort"
        ),
        "runtime_aim_fallback": False,
        "runtime_movement_fallback": False,
        "runtime_outcome_fallback": False,
    }


def source_groups() -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in capture.load_jsonl(SOURCE_MANIFEST):
        result[str(row["weapon"])].append(row)
    expected_variants = set(stochastic_v1.VARIANTS)
    for weapon, rows in result.items():
        variants = {
            row["stochastic_review_design"]["random_aim_variant"]
            for row in rows
        }
        if len(rows) != 3 or variants != expected_variants:
            raise capture.CaptureFailure(
                "stage2_prefrozen_motion_source_group_shape",
                capture.canonical_json(
                    {
                        "weapon": weapon,
                        "rows": len(rows),
                        "variants": sorted(variants),
                    }
                ),
            )
    if set(result) != set(stochastic_v1.human_v2.WEAPONS):
        raise capture.CaptureFailure(
            "stage2_prefrozen_motion_source_weapons",
            capture.canonical_json(sorted(result)),
        )
    return result


def materialize() -> list[dict[str, Any]]:
    commit = source_commit()
    sources = source_groups()
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    contract = selection_contract()
    rows: list[dict[str, Any]] = []
    for weapon_index, weapon in enumerate(
        stochastic_v1.human_v2.WEAPONS
    ):
        source_by_variant = {
            row["stochastic_review_design"]["random_aim_variant"]: row
            for row in sources[weapon]
        }
        for candidate_index, profile in enumerate(MOTION_PROFILES):
            candidate_label = chr(ord("a") + candidate_index)
            group_id = (
                f"s2pmv1_g{weapon_index + 1:02d}{candidate_label}_"
                f"{capture.WEAPON_NETNAME[weapon]}"
            )
            movement_seed = (
                15_700_000 + weapon_index * 10 + candidate_index + 1
            )
            movement = player_movement_program(
                movement_seed, profile
            )
            for variant in stochastic_v1.VARIANTS:
                row_ordinal = len(rows)
                row = copy.deepcopy(source_by_variant[variant])
                row.pop("stochastic_review_design", None)
                row.update(
                    {
                        "schema_version": causal.SCENARIO_SCHEMA_V8,
                        "action_program": causal.ACTION_PROGRAM_V8,
                        "episode_id": f"{group_id}_{variant}",
                        "counterfactual_group_id": group_id,
                        "anchor_id": f"{group_id}_pair",
                        "source_commit_required": commit,
                        "category": (
                            "stage2_prefrozen_player_motion_random_aim_"
                            "fire_enemy"
                        ),
                        "candidate_kind": (
                            "stage2_prefrozen_player_motion_review_v1"
                        ),
                        "candidate_status": (
                            "static_certified_pending_live_capture_and_"
                            "preregistered_group_selection"
                        ),
                        "training_stage": (
                            "stage2_prefrozen_player_motion_review_v1_only"
                        ),
                        "formal_collection_authorized": False,
                        "training_admitted": False,
                        "human_review_required_before_training": True,
                        "canary_role": (
                            f"stage2_prefrozen_motion_{weapon.lower()}_"
                            f"{profile}_{variant}"
                        ),
                        "data_spec_sha256": data_spec_sha256,
                        "shard_count": SHARD_COUNT,
                        "assigned_shard": row_ordinal % SHARD_COUNT,
                        "target_ordinal": row_ordinal,
                        "split": (
                            "stage2_prefrozen_player_motion_nontraining_"
                            "review_candidates"
                        ),
                    }
                )
                design = row["causal_design"]
                design.update(
                    {
                        "schema_version": (
                            causal.CAUSAL_DESIGN_SCHEMA_V8
                        ),
                        "base_player_program": (
                            "manifest_frozen_continuous_movement"
                        ),
                        "player_movement_program": movement,
                    }
                )
                row["acceptance"].update(
                    {
                        "actual_outcome": None,
                        "actual_outcome_rebucket_required": True,
                        "player_motion_qa_required": True,
                    }
                )
                row["policy_labels"].update(
                    {
                        "player_motion_class": (
                            "prefrozen_continuous_movement"
                        ),
                        "player_motion_profile": profile,
                        "player_motion_candidate": candidate_label,
                    }
                )
                row["exogenous_contract_sha256"] = (
                    causal.exogenous_contract_sha256(row)
                )
                certificate = static_action_certificate(row)
                if not certificate["passed"]:
                    raise capture.CaptureFailure(
                        "stage2_prefrozen_motion_static_action_failed",
                        capture.canonical_json(
                            {
                                "episode_id": row["episode_id"],
                                "certificate": certificate,
                            }
                        ),
                    )
                row["prefrozen_player_motion_review_design"] = {
                    "schema_version": DESIGN_SCHEMA,
                    "source_manifest": str(
                        SOURCE_MANIFEST.relative_to(ROOT)
                    ),
                    "source_episode_id": source_by_variant[variant][
                        "episode_id"
                    ],
                    "motion_candidate_index": candidate_index,
                    "motion_candidate_label": candidate_label,
                    "motion_profile": profile,
                    "movement_seed": movement_seed,
                    "movement_seed_independent": movement_seed
                    not in {
                        int(design["random_aim_program"]["seed"]),
                        int(design["fire_seed"]),
                        int(row["enemy_policy"]["policy_seed"]),
                    },
                    "counterfactual_group_selection_unit": True,
                    "selection_contract_sha256": hashlib.sha256(
                        capture.canonical_json(contract).encode(
                            "utf-8"
                        )
                    ).hexdigest(),
                    "static_action_certificate": certificate,
                    "runtime_action_fallback": False,
                    "runtime_geometry_fallback": False,
                    "runtime_outcome_fallback": False,
                    "formal_collection_authorized": False,
                }
                causal.validate_scenario_contract(row)
                rows.append(row)

    for group_id in sorted(
        {row["counterfactual_group_id"] for row in rows}
    ):
        members = [
            row
            for row in rows
            if row["counterfactual_group_id"] == group_id
        ]
        if len(members) != len(stochastic_v1.VARIANTS):
            raise capture.CaptureFailure(
                "stage2_prefrozen_motion_group_shape", group_id
            )
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_prefrozen_motion_group_exogenous_drift",
                group_id,
            )

    input_text = canonical_lines(rows)
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", input_text)
    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        write_once_or_verify(shard_path, shard_text)
        shard_metadata.append(
            {
                "shard_index": shard_index,
                "path": str(shard_path.relative_to(ROOT)),
                "rows": len(shard_rows),
                "sha256": hashlib.sha256(
                    shard_text.encode("utf-8")
                ).hexdigest(),
            }
        )
    metadata = {
        "schema_version": MANIFEST_SCHEMA,
        "source_manifest": {
            "path": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(SOURCE_MANIFEST),
        },
        "source_commit": commit,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "candidate_counterfactual_groups": len(
            stochastic_v1.human_v2.WEAPONS
        )
        * len(MOTION_PROFILES),
        "selected_counterfactual_groups": len(
            stochastic_v1.human_v2.WEAPONS
        ),
        "selected_rows": len(stochastic_v1.human_v2.WEAPONS)
        * len(stochastic_v1.VARIANTS),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "selection_contract": contract,
        "selection_contract_sha256": hashlib.sha256(
            capture.canonical_json(contract).encode("utf-8")
        ).hexdigest(),
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_prefrozen_player_motion_review_v1.py",
            )
        },
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "motion_profile_distribution": dict(
            Counter(
                row["prefrozen_player_motion_review_design"][
                    "motion_profile"
                ]
                for row in rows
            )
        ),
        "variant_distribution": dict(
            Counter(
                row["policy_labels"]["random_aim_variant"]
                for row in rows
            )
        ),
    }
    write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        capture.canonical_json(
            {
                "output": str(OUTPUT_ROOT),
                "rows": len(rows),
                "candidate_groups": len(
                    {
                        row["counterfactual_group_id"]
                        for row in rows
                    }
                ),
                "source_commit": source_commit(),
                "hard_minimum_hits": HARD_MINIMUM_HITS,
                "target_minimum_hits": TARGET_MINIMUM_HITS,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
