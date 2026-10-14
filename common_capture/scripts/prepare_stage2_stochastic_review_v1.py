                      
"""Create a non-training review for independent random aim/fire and enemy motion."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_humanized_review_v2 as human_v2              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_humanized_review_v2/input.jsonl"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_stochastic_review_v1"
SHARD_COUNT = 4
VARIANTS = ("broad_sparse", "local_bursty", "mixed_reverse")
MANIFEST_SCHEMA = "xonotic-stage2-stochastic-review-manifest-v1"
DESIGN_SCHEMA = "xonotic-stage2-stochastic-review-design-v1"
SELECTION_RULE = (
    "nine_weapon_three_arm_manifest_frozen_independent_random_aim_fire_"
    "with_seeded_piecewise_smooth_enemy_wander_v1"
)
FIRE_FAMILY = {
    **human_v2.WEAPON_FIRE_FAMILY,
    "Crylink": "spaced_tap",
}


def source_commit() -> str:
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(
                ROOT
                / "source/release-src-0.8.6/Xonotic"
            ),
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
                "refuse_overwrite_stochastic_manifest_drift",
                str(path),
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def random_aim_program(seed: int, variant: str) -> dict[str, Any]:
    limits = {
        "broad_sparse": (42.0, 18.0, 0.08),
        "local_bursty": (24.0, 12.0, 0.18),
        "mixed_reverse": (34.0, 16.0, 0.14),
    }
    max_yaw, max_pitch, hold_probability = limits[variant]
    ticks = [0, 40, 80, 120, 160, 200, 240, 280, 319]
    for candidate in range(512):
        rng = random.Random(seed + candidate * 1_000_003)
        yaw = [0.0]
        pitch = [0.0]
        for index in range(1, len(ticks)):
            if index > 1 and rng.random() < hold_probability:
                yaw.append(yaw[-1])
                pitch.append(pitch[-1])
                continue
            yaw.append(round(rng.uniform(-max_yaw, max_yaw), 6))
            pitch.append(
                round(rng.uniform(-max_pitch, max_pitch), 6)
            )
        if (
            max(yaw) - min(yaw) >= 18.0
            and max(pitch) - min(pitch) >= 8.0
            and any(value < -4.0 for value in yaw)
            and any(value > 4.0 for value in yaw)
            and any(value < -2.0 for value in pitch)
            and any(value > 2.0 for value in pitch)
        ):
            program = {
                "schema_version": causal.RANDOM_AIM_PROGRAM_SCHEMA,
                "seed": seed,
                "algorithm": (
                    "manifest_frozen_piecewise_smooth_view_v1"
                ),
                "interpolation": "smoothstep",
                "knot_output_ticks": ticks,
                "yaw_offset_deg": yaw,
                "pitch_offset_deg": pitch,
                "max_abs_yaw_offset_deg": max_yaw,
                "max_abs_pitch_offset_deg": max_pitch,
                "reads_live_enemy_state": False,
                "reads_live_player_state": False,
                "reads_camera": False,
                "reads_crosshair": False,
            }
            causal.validate_random_aim_program(program)
            return program
    raise capture.CaptureFailure(
        "stage2_stochastic_random_aim_candidate_exhausted",
        f"seed={seed} variant={variant}",
    )


def random_fire_program(
    weapon: str, seed: int, variant_index: int
) -> dict[str, Any]:
    rng = random.Random(seed)
    family = FIRE_FAMILY[weapon]
    refire = int(human_v2.PRIMARY_REFIRE_TICKS[weapon])
    windows: list[dict[str, int]] = []
    if family == "spaced_tap":
        count = 2 if variant_index == 0 else 3
        gap = refire + rng.randint(8, 18)
        latest_first = (
            capture.OUTPUT_TICKS - 3 - gap * (count - 1)
        )
        start = rng.randint(24, max(24, min(72, latest_first)))
        starts = [start + gap * index for index in range(count)]
        windows = [
            {"start_output_tick": value, "duration_ticks": 2}
            for value in starts
        ]
        name = "multi_tap"
        minimum = maximum = count
    else:
        count = 2 if variant_index < 2 else 3
        cursor = rng.randint(24, 48)
        for _ in range(count):
            if family == "rapid_auto":
                duration = rng.randint(16, 34)
            else:
                duration = refire + rng.randint(8, 16)
            windows.append(
                {
                    "start_output_tick": cursor,
                    "duration_ticks": duration,
                }
            )
            cursor += duration + rng.randint(18, 34)
        if windows[-1]["start_output_tick"] + windows[-1][
            "duration_ticks"
        ] > capture.OUTPUT_TICKS:
            shift = (
                windows[-1]["start_output_tick"]
                + windows[-1]["duration_ticks"]
                - capture.OUTPUT_TICKS
            )
            for window in windows:
                window["start_output_tick"] -= shift
        name = "double_burst" if count == 2 else "multi_tap"
        minimum = count
        maximum = 48 if family == "rapid_auto" else 16
    program = {
        "schema_version": causal.FIRE_PROGRAM_SCHEMA,
        "name": name,
        "weapon_fire_family": family,
        "windows": windows,
        "expected_min_fire_events": minimum,
        "expected_max_fire_events": maximum,
        "requires_multiple_fire_events": True,
        "selection_uses_authoritative_events": True,
    }
    return program


def static_action_certificate(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    actions = causal.causal_action_rows(scenario)
    output = actions[capture.WARMUP_TICKS :]
    yaw = [float(row["yaw_delta"]) for row in output]
    pitch = [float(row["pitch_delta"]) for row in output]
    primary = [bool(row["primary"]) for row in output]
    checks = {
        "rows_exact": len(actions) == capture.TOTAL_TICKS,
        "warmup_neutral": all(
            float(row["yaw_delta"]) == 0.0
            and float(row["pitch_delta"]) == 0.0
            and int(row["primary"]) == 0
            for row in actions[: capture.WARMUP_TICKS]
        ),
        "two_axis_motion": any(abs(value) > 1e-5 for value in yaw)
        and any(abs(value) > 1e-5 for value in pitch),
        "model_range": max(abs(value) for value in yaw) <= 12.0
        and max(abs(value) for value in pitch) <= 12.0,
        "fire_present": any(primary),
        "secondary_absent": not any(
            bool(row["secondary"]) for row in output
        ),
        "movement_absent": all(
            float(row["forward"]) == 0.0
            and float(row["strafe"]) == 0.0
            and int(row["jump"]) == 0
            for row in actions
        ),
    }
    return {
        "schema_version": (
            "xonotic-stage2-stochastic-static-action-certificate-v1"
        ),
        "checks": checks,
        "passed": all(checks.values()),
        "maximum_yaw_step_deg": max(abs(value) for value in yaw),
        "maximum_pitch_step_deg": max(
            abs(value) for value in pitch
        ),
        "primary_active_frames": sum(primary),
        "actions_sha256": hashlib.sha256(
            capture.canonical_json(actions).encode("utf-8")
        ).hexdigest(),
    }


def base_sources() -> dict[str, dict[str, Any]]:
    rows = capture.load_jsonl(SOURCE_MANIFEST)
    result = {
        str(row["weapon"]): row
        for row in rows
        if row["causal_design"]["aim_policy"]
        == "visible_no_response"
    }
    if set(result) != set(human_v2.WEAPONS):
        raise capture.CaptureFailure(
            "stage2_stochastic_source_weapon_shape",
            capture.canonical_json(sorted(result)),
        )
    return result


def materialize() -> list[dict[str, Any]]:
    commit = source_commit()
    sources = base_sources()
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    rows: list[dict[str, Any]] = []
    for weapon_index, weapon in enumerate(human_v2.WEAPONS):
        group_id = (
            f"s2stochv1_g{weapon_index + 1:02d}_"
            f"{capture.WEAPON_NETNAME[weapon]}"
        )
                                                                         
                                                                             
        enemy_seed = 11_700_000 + weapon_index + 1
        axis_rng = random.Random(enemy_seed)
        angle = axis_rng.uniform(-math.pi, math.pi)
        for variant_index, variant in enumerate(VARIANTS):
            row_ordinal = len(rows)
            row = copy.deepcopy(sources[weapon])
            for key in (
                "encounter_certificate",
                "target_motion_review_design",
                "bias_correction_design",
                "humanized_review_design",
            ):
                row.pop(key, None)
            aim_seed = (
                12_700_000
                + weapon_index * 100
                + variant_index
                + 1
            )
            fire_seed = (
                13_700_000
                + weapon_index * 100
                + variant_index
                + 1
            )
            aim = random_aim_program(aim_seed, variant)
            fire = random_fire_program(
                weapon, fire_seed, variant_index
            )
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V7,
                    "action_program": causal.ACTION_PROGRAM_V7,
                    "episode_id": f"{group_id}_{variant}",
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "seed": 14_700_000 + weapon_index + 1,
                    "source_commit_required": commit,
                    "category": (
                        "stage2_stochastic_random_aim_fire_enemy"
                    ),
                    "candidate_kind": (
                        "stage2_stochastic_review_v1"
                    ),
                    "candidate_status": (
                        "static_certified_pending_live_capture"
                    ),
                    "training_stage": (
                        "stage2_stochastic_review_v1_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "human_review_required_before_training": True,
                    "canary_role": (
                        f"stage2_stochastic_{weapon.lower()}_{variant}"
                    ),
                    "data_spec_sha256": data_spec_sha256,
                    "shard_count": SHARD_COUNT,
                    "assigned_shard": row_ordinal % SHARD_COUNT,
                    "target_ordinal": row_ordinal,
                    "split": (
                        "stage2_stochastic_nontraining_review"
                    ),
                    "expects_sound": True,
                }
            )
            row["enemy"].update(
                {
                    "health": 5000.0,
                    "armor": 0.0,
                    "motion": 4,
                    "motion_distance": 48.0,
                    "motion_start_tick": capture.WARMUP_TICKS,
                    "motion_vector": [
                        round(math.cos(angle), 9),
                        round(math.sin(angle), 9),
                        0.0,
                    ],
                }
            )
            row["enemy_policy"] = {
                "schema_version": (
                    "xonotic-stage2-enemy-policy-v2"
                ),
                "name": "seeded_piecewise_smooth_wander_v1",
                "policy_seed": enemy_seed,
                "motion_start_tick": capture.WARMUP_TICKS,
                "movement_audio": capture.ENEMY_MOVEMENT_AUDIO_MODE,
                "step_stride_units": capture.ENEMY_STEP_STRIDE_UNITS,
                "policy_layer": (
                    "frozen_exogenous_counterfactual_core"
                ),
                "bot_policy_scope": (
                    "time_correlated_random_wander_review"
                ),
                "closed_loop_decisions": False,
                "reads_camera": False,
                "reads_crosshair": False,
                "runtime_reads_player_state": False,
                "fires": False,
                "jumps": True,
            }
            row["causal_design"] = {
                "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V7,
                "aim_policy": causal.STOCHASTIC_AIM_POLICY,
                "aim_reference": (
                    "manifest_frozen_random_view_program"
                ),
                "random_aim_program": aim,
                "fire_seed": fire_seed,
                "fire_program": fire,
                "fire_output_ticks": [
                    int(window["start_output_tick"])
                    for window in fire["windows"]
                ],
                "fire_width_ticks": 2,
                "interaction_channel": "primary",
                "secondary_mechanism": None,
                "base_player_program": "stationary",
                "actual_outcome_source": (
                    "authoritative_event_parent_chain_per_shot"
                ),
                "intended_outcome_is_acceptance_gate": False,
                "reads_live_enemy_state": False,
                "reads_live_player_state": False,
                "reads_camera": False,
                "reads_crosshair": False,
            }
            row["acceptance"] = {
                "actual_outcome": None,
                "actual_outcome_rebucket_required": True,
                "fire_required": True,
                "reload_success": False,
            }
            row["policy_labels"] = {
                "aim_policy": causal.STOCHASTIC_AIM_POLICY,
                "interaction_channel": "primary",
                "initial_screen_cell": (
                    row.get("initial_screen_design") or {}
                ).get("screen_horizontal", "unknown")
                + "_"
                + (
                    row.get("initial_screen_design") or {}
                ).get("screen_vertical", "unknown"),
                "target_motion_name": (
                    "seeded_piecewise_smooth_wander_v1"
                ),
                "random_aim_variant": variant,
                "outcome_assignment": (
                    "post_capture_authoritative_per_shot_telemetry"
                ),
            }
            row["encounter_source"][
                "current_trajectory_requires_recertification"
            ] = True
            row["encounter_source"][
                "source_geometry_used_as_runtime_fallback"
            ] = False
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            certificate = static_action_certificate(row)
            if not certificate["passed"]:
                raise capture.CaptureFailure(
                    "stage2_stochastic_static_action_failed",
                    capture.canonical_json(
                        {
                            "episode_id": row["episode_id"],
                            "certificate": certificate,
                        }
                    ),
                )
            row["stochastic_review_design"] = {
                "schema_version": DESIGN_SCHEMA,
                "selection_rule": SELECTION_RULE,
                "source_manifest": str(
                    SOURCE_MANIFEST.relative_to(ROOT)
                ),
                "source_episode_id": sources[weapon]["episode_id"],
                "random_aim_variant": variant,
                "aim_seed": aim_seed,
                "fire_seed": fire_seed,
                "enemy_policy_seed": enemy_seed,
                "independent_action_seeds": len(
                    {aim_seed, fire_seed, enemy_seed}
                )
                == 3,
                "static_action_certificate": certificate,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
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
        if len(members) != len(VARIANTS):
            raise capture.CaptureFailure(
                "stage2_stochastic_group_shape", group_id
            )
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_stochastic_group_exogenous_drift",
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
        "selection_rule": SELECTION_RULE,
        "source_manifest": {
            "path": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(SOURCE_MANIFEST),
        },
        "source_commit": commit,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "counterfactual_groups": len(human_v2.WEAPONS),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(human_v2.WEAPONS),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "variant_distribution": dict(
            Counter(
                row["stochastic_review_design"][
                    "random_aim_variant"
                ]
                for row in rows
            )
        ),
        "fire_program_distribution": dict(
            Counter(
                row["causal_design"]["fire_program"]["name"]
                for row in rows
            )
        ),
        "enemy_policy_distribution": dict(
            Counter(row["enemy_policy"]["name"] for row in rows)
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
                "groups": len(
                    {
                        row["counterfactual_group_id"]
                        for row in rows
                    }
                ),
                "source_commit": source_commit(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
