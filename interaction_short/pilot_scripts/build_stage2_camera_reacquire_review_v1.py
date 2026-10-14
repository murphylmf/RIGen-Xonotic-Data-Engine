                      
"""Build an isolated Stage-2 camera-reacquisition paired review.

Each pair reuses the exact same enemy world-space trajectory.  The hold arm
keeps the camera fixed after the enemy exits the tolerant frustum; the
reacquire arm waits, then smoothly pans toward the analytically known enemy
trajectory.  This makes camera-caused re-entry directly auditable without
changing or admitting any existing Stage-1/Stage-2 data.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import hashlib
import html
import json
import math
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import build_samples_v12 as base
import build_stage2_offscreen_review_v1 as offscreen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_NAME = "stage2_camera_reacquire_review_v1_20260820"
CAMERA_MODES = ("hold", "reacquire")
VISIBLE_STATES = offscreen.VISIBLE_STATES
RESPONSE_START_TICK = 112
ACQUISITION_END_TICK = 252
MAX_REVIEW_YAW_STEP_DEG = 0.85
MAX_REVIEW_YAW_ACCEL_DEG = 0.08

VARIANT_ZH = {
    "continue_then_stop": "离屏后继续同向移动，再停住",
    "stop_after_exit": "离屏后停住",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wrap_angle(value: float) -> float:
    return (float(value) + 180.0) % 360.0 - 180.0


def angle_delta(target: float, current: float) -> float:
    return wrap_angle(float(target) - float(current))


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def make_group_cells() -> list[dict[str, Any]]:
    specs = (
        ("g00", "continue_then_stop", 1, "bromine", -30.0),
        ("g01", "continue_then_stop", 2, "opium", 35.0),
        ("g02", "stop_after_exit", 1, "bromine", -30.0),
        ("g03", "stop_after_exit", 2, "opium", 35.0),
    )
    cells: list[dict[str, Any]] = []
    for index, (group_id, variant, direction, map_name, yaw_offset) in enumerate(
        specs
    ):
        program = (
            (direction, direction, direction, 0, 0)
            if variant == "continue_then_stop"
            else (direction, direction, 0, 0, 0)
        )
        model, skin = base.APPEARANCES[(index * 7 + direction) % len(base.APPEARANCES)]
        cells.append(
            {
                "index": index,
                "group_id": group_id,
                "repeat": index,
                "visibility_category": "camera_reacquire_pair",
                "motion_variant": variant,
                "motion_label": base.CODE_LABEL[direction],
                "motion_code": direction,
                "desired_outcome": "no_fire",
                "desired_model": model,
                "desired_skin": skin,
                "desired_weapon": base.WEAPONS[(index * 3 + direction) % len(base.WEAPONS)],
                "desired_map": map_name,
                "distance_tier": "d3",
                "target_initial_distance_units": 270.0,
                "view_yaw_offset_deg": yaw_offset,
                "program": program,
            }
        )
    return cells


def select_designs() -> list[dict[str, Any]]:
    return offscreen.select_designs(make_group_cells())


def build_scenario(design: dict[str, Any], camera_mode: str) -> dict[str, Any]:
    if camera_mode not in CAMERA_MODES:
        raise ValueError(camera_mode)
    scenario = base.build_scenario(design["source"], design, frozen=False)
    episode_id = f"s2camv1_{design['group_id']}_{camera_mode}"
    scenario.update(
        {
            "schema_version": "xonotic-stage2-camera-reacquire-review-scenario-v1",
            "episode_id": episode_id,
            "dataset_role": "stage2_camera_reacquire_review_only_v1",
            "camera_program": (
                "fixed_hold_after_enemy_exit_v1"
                if camera_mode == "hold"
                else "delayed_smooth_enemy_reacquire_v1"
            ),
            "camera_reacquire_program": {
                "schema_version": "xonotic-stage2-camera-reacquire-program-v1",
                "mode": camera_mode,
                "response_start_output_tick": RESPONSE_START_TICK,
                "response_start_seconds": RESPONSE_START_TICK / base.TICK_HZ,
                "acquisition_end_output_tick": ACQUISITION_END_TICK,
                "acquisition_end_seconds": ACQUISITION_END_TICK / base.TICK_HZ,
                "target_source": (
                    "none"
                    if camera_mode == "hold"
                    else "manifest_analytic_enemy_trajectory"
                ),
                "closed_loop_live_reads": False,
                "reentry_cause_expected": (
                    "none" if camera_mode == "hold" else "camera_reacquire"
                ),
            },
            "visibility_program": {
                "schema_version": "xonotic-stage2-visibility-program-v1",
                "category": (
                    "exit_and_hold_offscreen"
                    if camera_mode == "hold"
                    else "exit_then_camera_reacquire"
                ),
                "frustum_tolerance_scale": base.FRUSTUM_TOLERANCE_SCALE,
                "occlusion_allowed": False,
                "view_yaw_offset_deg": design["view_yaw_offset_deg"],
            },
            "counterfactual_group_id": f"s2camv1_{design['group_id']}",
            "camera_counterfactual_role": camera_mode,
            "motion_variant": design["motion_variant"],
            "training_admitted": False,
            "formal_collection_authorized": False,
        }
    )
    scenario["enemy"]["health"] = 999.0
    scenario["enemy"]["armor"] = 0.0

    player = scenario["player"]["origin"]
    enemy = scenario["enemy"]["origin"]
    target_bearing = math.degrees(
        math.atan2(enemy[1] - player[1], enemy[0] - player[0])
    )
    yaw_offset = float(design["view_yaw_offset_deg"])
    scenario["player"]["yaw"] = wrap_angle(target_bearing + yaw_offset)
    scenario["initial_screen_design"] = {
        "schema_version": "xonotic-stage2-camera-reacquire-initial-screen-v1",
        "expected_visible_at_output_start": True,
        "view_yaw_offset_deg": yaw_offset,
        "screen_horizontal": "not_encoded_in_prompt",
        "screen_vertical": str(
            (design["source"].get("initial_screen_design") or {}).get(
                "screen_vertical", "center"
            )
        ),
    }

    scenario["enemy_motion_program"]["direction_codes"] = list(design["program"])
    scenario["enemy_motion_program"]["primary_motion"] = str(design["motion_label"])
    if camera_mode == "reacquire":
        scenario["action_reference_motion_program"] = copy.deepcopy(
            scenario["enemy_motion_program"]
        )
    else:
        reference = copy.deepcopy(scenario["enemy_motion_program"])
        reference.update(
            {
                "speed_units_per_second": 0.0,
                "direction_codes": [0, 0, 0, 0, 0],
                "primary_motion": "stationary",
            }
        )
        scenario["action_reference_motion_program"] = reference
    return scenario


def _validated_base_rows(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    action_scenario = copy.deepcopy(scenario)
    stationary = copy.deepcopy(action_scenario["enemy_motion_program"])
    stationary.update(
        {
            "speed_units_per_second": 0.0,
            "direction_codes": [0, 0, 0, 0, 0],
            "primary_motion": "stationary",
        }
    )
    action_scenario["enemy_motion_program"] = stationary
    random_program = action_scenario["causal_design"][
        "weapon_balanced_aim_program"
    ].get("random_aim_program")
    if not isinstance(random_program, dict):
        raise RuntimeError("camera review requires a non-firing random-view source")
    rows = base.formal.causal_action_rows_v9(action_scenario)
    for tick in range(base.WARMUP_TICKS, len(rows)):
        rows[tick]["forward"] = 0.0
        rows[tick]["strafe"] = 0.0
        rows[tick]["jump"] = 0
        rows[tick]["primary"] = 0
        rows[tick]["secondary"] = 0
    return rows


def camera_action_rows(scenario: dict[str, Any]) -> list[dict[str, Any]]:
                                                                           
                                                                
    rows = _validated_base_rows(scenario)

    current_yaw = float(scenario["player"]["yaw"])
    current_pitch = float(scenario["player"].get("pitch", 0.0))
    for tick in range(base.WARMUP_TICKS):
        current_yaw = wrap_angle(current_yaw + float(rows[tick]["yaw_delta"]))
        current_pitch = min(
            89.0,
            max(-89.0, current_pitch + float(rows[tick]["pitch_delta"])),
        )
    initial_yaw = float(scenario["player"]["yaw"])
    initial_pitch = float(scenario["player"].get("pitch", 0.0))
    player = scenario["player"]["origin"]
    for tick in range(base.WARMUP_TICKS, len(rows)):
        out_tick = tick - base.WARMUP_TICKS
        if (
            scenario["camera_counterfactual_role"] == "hold"
            or out_tick <= RESPONSE_START_TICK
        ):
            desired_yaw = initial_yaw
        else:
            enemy = base.analytic_enemy_origin_at_server_tick(scenario, tick)
            target_yaw = math.degrees(
                math.atan2(enemy[1] - player[1], enemy[0] - player[0])
            )
            gate = smoothstep(
                (out_tick - RESPONSE_START_TICK)
                / max(1, ACQUISITION_END_TICK - RESPONSE_START_TICK)
            )
            desired_yaw = wrap_angle(
                initial_yaw + angle_delta(target_yaw, initial_yaw) * gate
            )
        yaw_delta = angle_delta(desired_yaw, current_yaw)
        pitch_delta = initial_pitch - current_pitch
        rows[tick]["yaw_delta"] = round(yaw_delta, 6)
        rows[tick]["pitch_delta"] = round(pitch_delta, 6)
        current_yaw = wrap_angle(current_yaw + yaw_delta)
        current_pitch = min(89.0, max(-89.0, current_pitch + pitch_delta))
    base.capture.validate_model_action_source_rows(rows)
    return rows


def write_camera_action_csv(
    path: Path, scenario: dict[str, Any], retry: int = 0
) -> None:
    del retry
    rows = camera_action_rows(scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"#seed,{scenario['seed']}\n")
        writer = csv.DictWriter(handle, fieldnames=base.capture.ACTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


                                                                                 
base.capture.write_action_csv = write_camera_action_csv


def render_prompt(
    scenario: dict[str, Any],
    visibility: pd.DataFrame,
    interaction: dict[str, Any],
) -> dict[str, Any]:
    states = visibility.iloc[: base.PROMPT_TICKS]["visibility_state"].astype(str)
    program = scenario["enemy_motion_program"]["direction_codes"]
    blocks = []
    lines = ["[ENEMY MOTION, VISIBILITY, AND OUTCOME]"]
    for block_index, code in enumerate(program):
        start = int(round(block_index * base.BLOCK_SECONDS * base.TICK_HZ))
        end = int(round((block_index + 1) * base.BLOCK_SECONDS * base.TICK_HZ))
        block_states = states.iloc[start:end].tolist()
        first_state = block_states[0]
        last_state = block_states[-1]
        label = base.CODE_LABEL[int(code)]
        movement = base.PROMPT_SENTENCE[label]
        if all(state == "offscreen" for state in block_states):
            if label == "stationary":
                sentence = "The opponent remains out of view."
            else:
                phrase = movement.removeprefix("The opponent ").rstrip(".")
                if phrase.startswith("moves "):
                    phrase = "moving " + phrase.removeprefix("moves ")
                sentence = f"The opponent remains out of view while {phrase}."
        else:
            sentence = movement
            if first_state in VISIBLE_STATES and last_state == "offscreen":
                sentence = sentence.rstrip(".") + " and moves out of view."
            elif first_state == "offscreen" and last_state in VISIBLE_STATES:
                sentence = sentence.rstrip(".") + " and becomes visible again."
            elif "offscreen" in block_states and last_state in VISIBLE_STATES:
                sentence = sentence.rstrip(".") + " and becomes visible again."
            elif "edge_tolerant_visible" in block_states:
                sentence = (
                    sentence.rstrip(".")
                    + " and becomes partly cropped by the edge of the view."
                )
        combat = base.combat_label_for_block(interaction, block_index)
        sentence = sentence + " " + base.COMBAT_SENTENCE[combat]
        start_seconds = block_index * base.BLOCK_SECONDS
        end_seconds = (block_index + 1) * base.BLOCK_SECONDS
        blocks.append(
            {
                "block_index": block_index,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "motion_label": label,
                "visibility_start": first_state,
                "visibility_end": last_state,
                "combat_outcome": combat,
                "text": sentence,
            }
        )
        lines.append(f"{start_seconds:.1f}-{end_seconds:.1f}s: {sentence}")
    mode = scenario["camera_counterfactual_role"]
    return {
        "schema_version": "xonotic-stage2-camera-reacquire-prompt-v1",
        "provenance": "rendered_from_64hz_motion_visibility_and_events",
        "desired_outcome": scenario["intent_outcome"],
        "actual_outcome": interaction["actual_outcome"],
        "camera_action_described_in_text": False,
        "reentry_cause_structured": (
            "camera_reacquire" if mode == "reacquire" else "none"
        ),
        "uses_absolute_screen_region": False,
        "uses_distance_magnitude_adjective": False,
        "uses_percentage": False,
        "blocks": blocks,
        "prompt_text": "\n".join(lines),
    }


def finalize_episode(record: dict[str, Any]) -> dict[str, Any]:
    episode = Path(record["episode_path"])
    scenario = json.loads((episode / "scenario.json").read_text())
    qa = json.loads((episode / "qa.json").read_text())
    interaction = json.loads((episode / "telemetry/interaction.json").read_text())
    visibility = pd.read_parquet(episode / "telemetry/visibility_64hz.parquet")
    metrics = offscreen.visibility_metrics(visibility)
    prompt = render_prompt(scenario, visibility, interaction)
    checks = {
        key: value
        for key, value in qa["checks"].items()
        if key != "no_true_offscreen_after_tolerance"
    }
    checks.update(
        {
            "enemy_starts_visible": metrics["initial_state"] in VISIBLE_STATES,
            "enemy_has_true_offscreen_run": metrics["longest_offscreen_run_frames"]
            >= 16,
            "no_occlusion_in_prompt_window": int(
                metrics["counts"].get("occluded", 0)
            )
            == 0,
        }
    )
    qa.update(
        {
            "schema_version": "xonotic-stage2-camera-reacquire-review-episode-qa-v1",
            "checks": checks,
            "legacy_v12_visibility_check": {
                "no_true_offscreen_after_tolerance": qa["checks"].get(
                    "no_true_offscreen_after_tolerance"
                )
            },
            "visibility_metrics": metrics,
            "review_passed_pre_pair": all(checks.values()),
            "training_admitted": False,
        }
    )
    write_json(episode / "prompt.json", prompt)
    write_json(episode / "qa.json", qa)
    record["scenario"] = scenario
    record["prompt"] = prompt
    record["qa"] = qa
    return record


def _camera_yaw_metrics(frames: pd.DataFrame) -> dict[str, Any]:
    yaw = np.rad2deg(
        np.unwrap(
            np.arctan2(
                frames.iloc[: base.PROMPT_TICKS]["forward_y"].to_numpy(float),
                frames.iloc[: base.PROMPT_TICKS]["forward_x"].to_numpy(float),
            )
        )
    )
    speed = np.diff(yaw)
    accel = np.diff(speed)
    return {
        "initial_yaw_deg": float(yaw[0]),
        "final_yaw_deg": float(yaw[-1]),
        "net_yaw_deg": float(yaw[-1] - yaw[0]),
        "maximum_abs_yaw_step_deg": float(np.max(np.abs(speed))),
        "maximum_abs_yaw_accel_deg_per_tick2": float(np.max(np.abs(accel))),
        "yaw_deg": yaw,
    }


def pair_qa(hold: dict[str, Any], reacquire: dict[str, Any]) -> dict[str, Any]:
    hold_path = Path(hold["episode_path"])
    reacquire_path = Path(reacquire["episode_path"])
    hold_visibility = pd.read_parquet(
        hold_path / "telemetry/visibility_64hz.parquet"
    ).iloc[: base.PROMPT_TICKS]
    reacquire_visibility = pd.read_parquet(
        reacquire_path / "telemetry/visibility_64hz.parquet"
    ).iloc[: base.PROMPT_TICKS]
    hold_states = pd.read_parquet(hold_path / "telemetry/states_64hz.parquet")
    reacquire_states = pd.read_parquet(
        reacquire_path / "telemetry/states_64hz.parquet"
    )
    hold_frames = pd.read_parquet(hold_path / "telemetry/frames_64hz.parquet")
    reacquire_frames = pd.read_parquet(
        reacquire_path / "telemetry/frames_64hz.parquet"
    )
    hold_actions = pd.read_parquet(
        hold_path / "telemetry/actions_requested_64hz.parquet"
    ).iloc[base.WARMUP_TICKS : base.WARMUP_TICKS + base.PROMPT_TICKS]
    reacquire_actions = pd.read_parquet(
        reacquire_path / "telemetry/actions_requested_64hz.parquet"
    ).iloc[base.WARMUP_TICKS : base.WARMUP_TICKS + base.PROMPT_TICKS]

    hold_metrics = offscreen.visibility_metrics(hold_visibility)
    reacquire_metrics = offscreen.visibility_metrics(reacquire_visibility)
    reentry = reacquire_metrics["reentry_after_offscreen_frame"]
    enemy_columns = np.asarray(
        hold_states.iloc[base.WARMUP_TICKS : base.WARMUP_TICKS + base.PROMPT_TICKS][
            "enemy.origin"
        ].tolist(),
        dtype=np.float64,
    )
    enemy_columns_reacquire = np.asarray(
        reacquire_states.iloc[
            base.WARMUP_TICKS : base.WARMUP_TICKS + base.PROMPT_TICKS
        ]["enemy.origin"].tolist(),
        dtype=np.float64,
    )
    enemy_error = np.abs(enemy_columns - enemy_columns_reacquire)
    hold_camera = _camera_yaw_metrics(hold_frames)
    reacquire_camera = _camera_yaw_metrics(reacquire_frames)
    pre_response_action_error = np.abs(
        hold_actions.iloc[: RESPONSE_START_TICK + 1][
            ["forward", "strafe", "yaw_delta", "pitch_delta", "jump"]
        ].to_numpy(float)
        - reacquire_actions.iloc[: RESPONSE_START_TICK + 1][
            ["forward", "strafe", "yaw_delta", "pitch_delta", "jump"]
        ].to_numpy(float)
    )
    camera_divergence = np.abs(
        reacquire_camera["yaw_deg"] - hold_camera["yaw_deg"]
    )
    hold_state_at_reentry = (
        str(hold_visibility.iloc[int(reentry)]["visibility_state"])
        if reentry is not None
        else None
    )
    reacquire_offscreen_run = next(
        (
            run
            for run in reacquire_metrics["offscreen_runs"]
            if reentry is not None and run["end_frame_exclusive"] == int(reentry)
        ),
        None,
    )
    checks = {
        "both_episode_pre_pair_checks_pass": bool(
            hold["qa"]["review_passed_pre_pair"]
            and reacquire["qa"]["review_passed_pre_pair"]
        ),
        "exact_same_enemy_world_trajectory": float(enemy_error.max()) <= 1e-5,
        "same_camera_actions_through_response_start": float(
            pre_response_action_error.max()
        )
        <= 1e-9,
        "hold_exits_and_never_reenters": bool(
            hold_metrics["first_offscreen_frame"] is not None
            and hold_metrics["reentry_after_offscreen_frame"] is None
            and hold_metrics["final_state"] == "offscreen"
        ),
        "reacquire_exits_then_reenters": bool(
            reacquire_metrics["first_offscreen_frame"] is not None
            and reentry is not None
            and reacquire_metrics["final_state"] in VISIBLE_STATES
        ),
        "offscreen_dwell_at_least_16_frames_before_reentry": bool(
            reacquire_offscreen_run is not None
            and reacquire_offscreen_run["frames"] >= 16
        ),
        "hold_counterfactual_still_offscreen_at_reentry": (
            hold_state_at_reentry == "offscreen"
        ),
        "camera_does_not_move_before_response": float(
            np.max(camera_divergence[: RESPONSE_START_TICK + 1])
        )
        <= 0.05,
        "camera_diverges_after_response": float(
            np.max(camera_divergence[RESPONSE_START_TICK + 1 :])
        )
        >= 5.0,
        "reacquire_camera_yaw_step_is_smooth": reacquire_camera[
            "maximum_abs_yaw_step_deg"
        ]
        <= MAX_REVIEW_YAW_STEP_DEG,
        "reacquire_camera_yaw_acceleration_is_smooth": reacquire_camera[
            "maximum_abs_yaw_accel_deg_per_tick2"
        ]
        <= MAX_REVIEW_YAW_ACCEL_DEG,
        "enemy_program_has_no_reversal": len(
            {
                int(code)
                for code in reacquire["scenario"]["enemy_motion_program"][
                    "direction_codes"
                ]
                if int(code) != 0
            }
        )
        <= 1,
    }
    report = {
        "schema_version": "xonotic-stage2-camera-reacquire-pair-qa-v1",
        "group_id": hold["scenario"]["counterfactual_group_id"],
        "hold_episode_id": hold["episode_id"],
        "reacquire_episode_id": reacquire["episode_id"],
        "passed": all(checks.values()),
        "checks": checks,
        "reentry_cause": "camera_reacquire",
        "hold_visibility_metrics": hold_metrics,
        "reacquire_visibility_metrics": reacquire_metrics,
        "hold_state_at_reacquire_reentry_frame": hold_state_at_reentry,
        "reacquire_offscreen_run_before_reentry": reacquire_offscreen_run,
        "maximum_enemy_world_trajectory_error": float(enemy_error.max()),
        "maximum_pre_response_action_error": float(
            pre_response_action_error.max()
        ),
        "maximum_camera_yaw_divergence_deg": float(camera_divergence.max()),
        "hold_camera": {
            key: value for key, value in hold_camera.items() if key != "yaw_deg"
        },
        "reacquire_camera": {
            key: value
            for key, value in reacquire_camera.items()
            if key != "yaw_deg"
        },
        "thresholds": {
            "maximum_yaw_step_deg": MAX_REVIEW_YAW_STEP_DEG,
            "maximum_yaw_accel_deg_per_tick2": MAX_REVIEW_YAW_ACCEL_DEG,
            "minimum_offscreen_dwell_frames": 16,
        },
        "training_admitted": False,
    }
    for record in (hold, reacquire):
        episode = Path(record["episode_path"])
        qa = record["qa"]
        qa["pair_qa"] = report
        qa["review_passed"] = bool(report["passed"])
        write_json(episode / "pair_qa.json", report)
        write_json(episode / "qa.json", qa)
    return report


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_review_page(rows: list[dict[str, Any]]) -> str:
    sections = []
    for row in rows:
        pair = row["pair_qa"]
        hold = row["hold"]
        reacquire = row["reacquire"]
        direction = "向左" if int(row["direction_code"]) == 1 else "向右"

        def card(record: dict[str, Any], title: str) -> str:
            episode_id = record["sample_id"]
            metrics = record["visibility_metrics"]
            prompt = record["prompt"]
            return f"""
            <article class="arm">
              <h3>{esc(title)}</h3>
              <code>{esc(episode_id)}</code>
              <video controls muted playsinline preload="metadata" src="../episodes/{esc(episode_id)}/media/review_20hz_81f.mp4"></video>
              <div class="facts">
                <span>first offscreen <b>{esc(metrics['first_offscreen_frame'])}f</b></span>
                <span>re-entry <b>{esc(metrics['reentry_after_offscreen_frame'])}f</b></span>
                <span>final <b>{esc(metrics['final_state'])}</b></span>
              </div>
              <details><summary>Prompt</summary><pre>{esc(prompt['prompt_text'])}</pre></details>
            </article>
            """

        failed = [key for key, value in pair["checks"].items() if not value]
        sections.append(
            f"""
            <section>
              <div class="section-head"><div><h2>{esc(direction)} · {esc(VARIANT_ZH[row['motion_variant']])}</h2><p>{esc(row['map'])} · program {esc(row['direction_codes'])}</p></div><strong class="{'pass' if pair['passed'] else 'check'}">{'PASS' if pair['passed'] else 'CHECK'}</strong></div>
              <div class="pair">{card(hold, 'A · 镜头保持（反事实）')}{card(reacquire, 'B · 离屏后平滑追踪')}</div>
              <div class="pair-facts">
                <span>屏外停留 <b>{esc(pair['reacquire_offscreen_run_before_reentry']['frames'] if pair['reacquire_offscreen_run_before_reentry'] else None)}f</b></span>
                <span>hold 在重入帧 <b>{esc(pair['hold_state_at_reacquire_reentry_frame'])}</b></span>
                <span>最大镜头步长 <b>{pair['reacquire_camera']['maximum_abs_yaw_step_deg']:.3f}°/tick</b></span>
                <span>敌人轨迹误差 <b>{pair['maximum_enemy_world_trajectory_error']:.6f}</b></span>
                <span>failed <b>{esc(', '.join(failed) or 'none')}</b></span>
              </div>
              <p><a href="../episodes/{esc(reacquire['sample_id'])}/pair_qa.json">pair_qa.json</a></p>
            </section>
            """
        )
    passed = sum(int(row["pair_qa"]["passed"]) for row in rows)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 camera reacquire paired review v1</title>
<style>
:root{{color-scheme:dark;--bg:#070a10;--panel:#111722;--line:#2a3548;--text:#eef5ff;--muted:#96a5bb;--cyan:#55dffc;--green:#55e6a5;--amber:#ffc05b}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 20% 0,#17243b,var(--bg) 45%);color:var(--text);font:14px/1.5 Inter,system-ui,sans-serif}}main{{width:min(1500px,calc(100% - 28px));margin:auto;padding:36px 0 72px}}h1{{font-size:clamp(30px,5vw,56px);margin:6px 0}}header>p,.section-head p{{color:var(--muted)}}.summary{{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0 34px}}.metric,.pair-facts span{{padding:10px 14px;border:1px solid var(--line);background:var(--panel);border-radius:10px}}section{{border-top:1px solid var(--line);padding-top:25px;margin-top:34px}}.section-head{{display:flex;justify-content:space-between;gap:20px}}.section-head h2{{margin:0}}.section-head p{{margin:5px 0}}.section-head strong{{height:max-content;padding:6px 12px;border-radius:99px;color:#04110b}}.pass{{background:var(--green)}}.check{{background:var(--amber)}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.arm{{background:rgba(17,23,34,.96);border:1px solid var(--line);border-radius:16px;padding:14px}}.arm h3{{margin:0 0 3px}}code,a{{color:var(--cyan)}}video{{display:block;width:100%;aspect-ratio:16/9;background:#000;border:1px solid var(--line);border-radius:9px;margin-top:10px}}.facts,.pair-facts{{display:flex;flex-wrap:wrap;gap:8px 16px;color:var(--muted);margin-top:10px}}.facts b,.pair-facts b{{color:var(--text)}}details{{margin-top:10px}}pre{{white-space:pre-wrap;background:#080c12;padding:12px;border-radius:8px}}@media(max-width:820px){{.pair{{grid-template-columns:1fr}}}}
</style></head><body><main><header><code>XONOTIC · STAGE-2 · CAMERA REACQUIRE PILOT V1</code><h1>离屏后镜头追踪 · Paired Review</h1><p>每组敌人世界轨迹完全相同。A 保持镜头；B 在离屏后等待 0.42s 以上，再以平滑 yaw 追踪。敌人不折返，camera action 不写入敌人运动 prompt；障碍遮挡继续拒绝。</p><div class="summary"><div class="metric">配对 <b>{len(rows)}</b></div><div class="metric">自动门通过 <b>{passed}/{len(rows)}</b></div><div class="metric">每对视频 <b>2</b></div><div class="metric">training_admitted <b>false</b></div><div class="metric">旧 Stage-1/2 <b>未修改</b></div></div></header>{''.join(sections)}</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--port-base", type=int, default=24200)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    if "PENDING" in base.BUILD_TAG or "PENDING" in base.SOURCE_COMMIT:
        raise RuntimeError("set Stage-2 runtime build tag and source commit")

    designs = select_designs()
    if args.dry_run:
        payload = [
            {
                "group_id": design["group_id"],
                "source": design["source"]["episode_id"],
                "map": design["desired_map"],
                "program": design["program"],
                "yaw_offset": design["view_yaw_offset_deg"],
            }
            for design in designs
        ]
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    output_root = ROOT / "outputs" / args.output_name
    if output_root.exists() and not args.resume:
        raise RuntimeError(f"refusing to overwrite output: {output_root}")
    output_root.mkdir(parents=True, exist_ok=args.resume)
    scratch_root = Path(os.environ["XONOTIC_CAPTURE_TMP"]) / args.output_name
    scratch_root.mkdir(parents=True, exist_ok=True)
    base.run_protection_check(output_root / "STAGE12_PRECHECK.txt")

    def capture_group(local_index: int, design: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for mode_index, camera_mode in enumerate(CAMERA_MODES):
            scenario = build_scenario(design, camera_mode)
            destination = output_root / "episodes" / scenario["episode_id"]
            if args.resume and (destination / "qa.json").is_file():
                record = base.load_packaged_episode(output_root, scenario["episode_id"])
            else:
                record = base.capture_episode(
                    scenario,
                    output_root,
                    scratch_root,
                    port=args.port_base + local_index * 2 + mode_index,
                    retain_raw_avi=False,
                )
            records[camera_mode] = finalize_episode(record)
        pair = pair_qa(records["hold"], records["reacquire"])
        print(
            f"completed {design['group_id']} pair passed={pair['passed']}",
            flush=True,
        )
        return records["hold"], records["reacquire"], pair

    completed: dict[int, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(capture_group, index, design): index
            for index, design in enumerate(designs)
        }
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            completed[index] = future.result()

    base.run_protection_check(output_root / "STAGE12_POSTCHECK.txt")
    rows = []
    for index, design in enumerate(designs):
        hold, reacquire, pair = completed[index]

        def episode_row(record: dict[str, Any]) -> dict[str, Any]:
            return {
                "sample_id": record["episode_id"],
                "video_path": record["review_video"],
                "prompt": record["prompt"],
                "visibility_metrics": record["qa"]["visibility_metrics"],
                "review_passed": bool(record["qa"]["review_passed"]),
            }

        rows.append(
            {
                "schema_version": "xonotic-stage2-camera-reacquire-review-row-v1",
                "group_id": design["group_id"],
                "motion_variant": design["motion_variant"],
                "direction_code": design["motion_code"],
                "direction_label": design["motion_label"],
                "direction_codes": list(design["program"]),
                "map": hold["scenario"]["map"],
                "weapon": hold["scenario"]["weapon"],
                "enemy": (
                    f"{hold['scenario']['enemy_model']}:"
                    f"skin{hold['scenario']['enemy_skin']}:"
                    f"color{hold['scenario']['enemy_color']}"
                ),
                "source_formal_episode_id": hold["scenario"][
                    "source_formal_episode_id"
                ],
                "hold": episode_row(hold),
                "reacquire": episode_row(reacquire),
                "pair_qa": pair,
                "review_passed": bool(pair["passed"]),
                "training_admitted": False,
            }
        )

    manifest = output_root / "review_manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")
    summary = {
        "schema_version": "xonotic-stage2-camera-reacquire-review-summary-v1",
        "output_root": str(output_root),
        "runtime_build_tag": base.BUILD_TAG,
        "runtime_source_commit": base.SOURCE_COMMIT,
        "pairs": len(rows),
        "episodes": len(rows) * 2,
        "pairs_passed": sum(int(row["review_passed"]) for row in rows),
        "motion_variants": dict(Counter(row["motion_variant"] for row in rows)),
        "directions": dict(Counter(row["direction_label"] for row in rows)),
        "camera_program": {
            "response_start_tick": RESPONSE_START_TICK,
            "acquisition_end_tick": ACQUISITION_END_TICK,
            "closed_loop_live_reads": False,
            "paired_hold_counterfactual": True,
        },
        "training_admitted": False,
        "stage1_stage2_protection_precheck_passed": True,
        "stage1_stage2_protection_postcheck_passed": True,
    }
    write_json(output_root / "SUMMARY.json", summary)
    review_dir = output_root / "review"
    review_dir.mkdir(exist_ok=args.resume)
    (review_dir / "index.html").write_text(
        render_review_page(rows), encoding="utf-8"
    )
    artifacts = {
        str(path.relative_to(output_root)): sha256_file(path)
        for path in sorted(output_root.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS"
    }
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for relative, digest in artifacts.items():
            handle.write(f"{digest}  {relative}\n")
    shutil.rmtree(scratch_root, ignore_errors=True)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(review_dir / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
