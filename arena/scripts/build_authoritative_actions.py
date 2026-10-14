                      
"""Validate duel-v11 server telemetry and build LTX-2 action artifacts.

The source TSV is written inside SVQC after bot AI has produced controls for a
64 Hz server frame.  Unlike client-demo recovery, movement magnitudes and view
deltas are therefore authoritative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


SCHEMA_MARKER = "schema=xonotic-duel-v11-authoritative-bot-action-v1"
TICK_HZ = 64
STANDARD_FPS = 20
MODEL_WINDOW_FRAMES = 81
MOVEMENT_SCALE = 400.0
VIEW_DEGREES_PER_TICK = 12.0
FLOAT_TOLERANCE = 1e-3
DUEL_MOVEMENT_INPUT_LIMIT = 64.0
DUEL_TURN_STEP_LIMIT_DEGREES = 120.0 / TICK_HZ
DUEL_TURN_ACCEL_STEP_LIMIT_DEGREES = 480.0 / (TICK_HZ * TICK_HZ)
MOTOR_TOLERANCE_DEGREES = 2e-4

REQUIRED_COLUMNS = {
    "frame_index",
    "server_time",
    "server_frametime",
    "bot_entity",
    "player_id",
    "bot_name",
    "is_pov",
    "pov_target_matches",
    "real_client_count",
    "pov_observer_count",
    "movement_x",
    "movement_y",
    "movement_z",
    "previous_view_pitch",
    "previous_view_yaw",
    "previous_view_roll",
    "view_pitch",
    "view_yaw",
    "view_roll",
    "button_mask",
    "button_jump",
    "button_primary",
    "button_secondary",
    "button_crouch",
    "button_zoom",
    "button_hook",
    "button_use",
    "button_info",
    "button_drag",
    "button_chat",
    "button_zoomscript",
    "button_jetpack",
    "button_dodge",
    "button_minigame",
    "button_prydon",
    "button13",
    "button14",
    "button15",
    "button16",
    "impulse",
    "is_dead",
    "health",
    "origin_x",
    "origin_y",
    "origin_z",
    "velocity_x",
    "velocity_y",
    "velocity_z",
    "enemy_entity",
    "enemy_health",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def angular_delta(current: np.ndarray, previous: np.ndarray) -> np.ndarray:
    return (current - previous + 180.0) % 360.0 - 180.0


def contiguous_ranges(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    ranges: list[list[int]] = []
    start = previous = values[0]
    for value in values[1:]:
        if value != previous + 1:
            ranges.append([start, previous])
            start = value
        previous = value
    ranges.append([start, previous])
    return ranges


def run_count(values: np.ndarray) -> int:
    active = values.astype(bool)
    if not len(active):
        return 0
    return int(active[0]) + int(np.logical_and(active[1:], ~active[:-1]).sum())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--pov-bot", required=True)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--capture-start", type=float)
    args = parser.parse_args()

    telemetry_path = args.telemetry.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    first_line = telemetry_path.open("r", encoding="utf-8").readline().strip()
    if SCHEMA_MARKER not in first_line:
        raise ValueError(f"unexpected telemetry schema marker: {first_line!r}")
    telemetry = pd.read_csv(telemetry_path, sep="\t", comment="#")
    missing = sorted(REQUIRED_COLUMNS - set(telemetry.columns))
    if missing:
        raise ValueError(f"telemetry columns missing: {missing}")

    expected_frames = args.duration * TICK_HZ
    errors: list[str] = []
    bot_names = sorted(str(value) for value in telemetry["bot_name"].unique())
    if len(bot_names) != 2:
        errors.append(f"expected exactly two bots, got {bot_names}")
    raw_frame_values = pd.to_numeric(telemetry["frame_index"], errors="coerce")
    if raw_frame_values.isna().any() or not np.equal(raw_frame_values, np.floor(raw_frame_values)).all():
        errors.append("raw frame_index contains a non-integer value")
        raw_frame_indices = np.empty(0, dtype=np.int64)
    else:
        raw_frame_indices = np.sort(raw_frame_values.astype(np.int64).unique())
    if len(raw_frame_indices) < expected_frames:
        errors.append(
            f"telemetry has {len(raw_frame_indices)} frames, fewer than required {expected_frames}"
        )
    if len(raw_frame_indices) and not np.array_equal(
        raw_frame_indices, np.arange(raw_frame_indices[0], raw_frame_indices[-1] + 1)
    ):
        errors.append("raw telemetry frame_index is not contiguous")
    frame_row_counts = telemetry.groupby("frame_index", sort=False).size()
    frame_bot_counts = telemetry.groupby("frame_index", sort=False)["bot_name"].nunique()

    if errors:
        failure = {
            "schema_version": "xonotic-duel-v11-authoritative-action-rejection-v1",
            "training_admitted": False,
            "episode_id": args.episode_id,
            "pov_bot": args.pov_bot,
            "telemetry": str(telemetry_path),
            "errors": errors,
        }
        failure_path = output_dir / "action_qa_failed.json"
        failure_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure, indent=2))
        return 2

                                                                              
                                                                               
                                                                           
                                                                        
    selection_start_frame = int(raw_frame_indices[-expected_frames])
    selection_end_frame = int(raw_frame_indices[-1])
    selected = telemetry.loc[
        (raw_frame_values >= selection_start_frame)
        & (raw_frame_values <= selection_end_frame)
    ].copy()
    selected_row_counts = selected.groupby("frame_index", sort=False).size()
    selected_bot_counts = selected.groupby("frame_index", sort=False)["bot_name"].nunique()
    if len(selected_row_counts) != expected_frames or not (selected_row_counts == 2).all():
        errors.append("selected tail does not contain exactly two rows per frame")
    if len(selected_bot_counts) != expected_frames or not (selected_bot_counts == 2).all():
        errors.append("selected tail does not contain both unique bots per frame")

    pov = selected.loc[selected["bot_name"].astype(str) == args.pov_bot].copy()
    pov = pov.sort_values("frame_index").reset_index(drop=True)
    if len(pov) != expected_frames:
        errors.append(f"expected {expected_frames} POV rows, got {len(pov)}")
    expected_indices = np.arange(
        selection_start_frame, selection_start_frame + expected_frames, dtype=np.int64
    )
    indices = pd.to_numeric(pov.get("frame_index"), errors="coerce").to_numpy()
    if len(indices) != expected_frames or not np.array_equal(indices, expected_indices):
        errors.append("selected POV frame_index is not exactly contiguous")

    for column, expected in (
        ("is_pov", 1),
        ("pov_target_matches", 1),
        ("real_client_count", 1),
        ("pov_observer_count", 1),
    ):
        values = pd.to_numeric(pov.get(column), errors="coerce")
        bad = int((values != expected).sum())
        if bad:
            errors.append(f"{column} has {bad} rows different from {expected}")

    numeric_columns = sorted(REQUIRED_COLUMNS - {"bot_name"})
    numeric = pov[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=np.float64)).all():
        errors.append("POV telemetry contains non-finite numeric values")

    if len(pov):
        times = pd.to_numeric(pov["server_time"], errors="coerce").to_numpy(
            dtype=np.float64
        )
        frame_times = pd.to_numeric(
            pov["server_frametime"], errors="coerce"
        ).to_numpy(dtype=np.float64)
        expected_dt = 1.0 / TICK_HZ
        if args.capture_start is not None and abs(times[0] - args.capture_start) > expected_dt + 1e-6:
            errors.append(
                f"first server_time {times[0]:.9f} is not aligned to capture start "
                f"{args.capture_start:.9f}"
            )
        if len(times) > 1 and np.max(np.abs(np.diff(times) - expected_dt)) > 2e-5:
            errors.append("server_time cadence is not uniformly 64 Hz")
        if np.max(np.abs(frame_times - expected_dt)) > 2e-5:
            errors.append("server_frametime is not uniformly 1/64 second")
        measured_duration = times[-1] - times[0] + expected_dt
        if abs(measured_duration - args.duration) > 2e-5:
            errors.append(
                f"telemetry duration is {measured_duration:.9f}, expected {args.duration}"
            )

    movement = pov[["movement_x", "movement_y", "movement_z"]].to_numpy(
        dtype=np.float64
    )
    if len(movement) and np.max(np.abs(movement[:, :2])) > MOVEMENT_SCALE + FLOAT_TOLERANCE:
        errors.append(
            f"movement magnitude exceeds model contract: {np.max(np.abs(movement[:, :2]))}"
        )
    if len(movement) and np.max(np.abs(movement[:, 2])) > FLOAT_TOLERANCE:
        errors.append("unrepresented vertical movement was emitted")

                                                                               
                                                                             
                                                                
    both_bot_motion: dict[str, dict[str, float]] = {}
    for bot_name, bot_rows in selected.groupby("bot_name", sort=True):
        bot_rows = bot_rows.sort_values("frame_index")
        bot_movement = bot_rows[["movement_x", "movement_y"]].to_numpy(
            dtype=np.float64
        )
        bot_movement_norm = np.linalg.norm(bot_movement, axis=1)
        bot_yaw_delta = angular_delta(
            bot_rows["view_yaw"].to_numpy(dtype=np.float64),
            bot_rows["previous_view_yaw"].to_numpy(dtype=np.float64),
        )
        bot_pitch_delta = angular_delta(
            bot_rows["view_pitch"].to_numpy(dtype=np.float64),
            bot_rows["previous_view_pitch"].to_numpy(dtype=np.float64),
        )
        bot_yaw_accel_step = np.diff(bot_yaw_delta)
        bot_pitch_accel_step = np.diff(bot_pitch_delta)
        bot_velocity_xy = np.linalg.norm(
            bot_rows[["velocity_x", "velocity_y"]].to_numpy(dtype=np.float64),
            axis=1,
        )
        metrics = {
            "movement_input_norm_max": float(np.max(bot_movement_norm)),
            "horizontal_velocity_p99": float(np.quantile(bot_velocity_xy, 0.99)),
            "horizontal_velocity_max": float(np.max(bot_velocity_xy)),
            "yaw_step_abs_max_degrees": float(np.max(np.abs(bot_yaw_delta))),
            "pitch_step_abs_max_degrees": float(np.max(np.abs(bot_pitch_delta))),
            "yaw_accel_step_abs_max_degrees": float(
                np.max(np.abs(bot_yaw_accel_step)) if len(bot_yaw_accel_step) else 0.0
            ),
            "pitch_accel_step_abs_max_degrees": float(
                np.max(np.abs(bot_pitch_accel_step))
                if len(bot_pitch_accel_step)
                else 0.0
            ),
        }
        both_bot_motion[str(bot_name)] = metrics
        if metrics["movement_input_norm_max"] > DUEL_MOVEMENT_INPUT_LIMIT + FLOAT_TOLERANCE:
            errors.append(
                f"{bot_name} movement input norm exceeds {DUEL_MOVEMENT_INPUT_LIMIT}: "
                f"{metrics['movement_input_norm_max']}"
            )
        for axis in ("yaw", "pitch"):
            if (
                metrics[f"{axis}_step_abs_max_degrees"]
                > DUEL_TURN_STEP_LIMIT_DEGREES + MOTOR_TOLERANCE_DEGREES
            ):
                errors.append(
                    f"{bot_name} {axis} step bypasses final camera motor: "
                    f"{metrics[f'{axis}_step_abs_max_degrees']}"
                )
            if (
                metrics[f"{axis}_accel_step_abs_max_degrees"]
                > DUEL_TURN_ACCEL_STEP_LIMIT_DEGREES + MOTOR_TOLERANCE_DEGREES
            ):
                errors.append(
                    f"{bot_name} {axis} acceleration bypasses final camera motor: "
                    f"{metrics[f'{axis}_accel_step_abs_max_degrees']}"
                )

    unrepresented = [
        "button_secondary",
        "button_crouch",
        "button_zoom",
        "button_hook",
        "button_use",
        "button_info",
        "button_drag",
        "button_chat",
        "button_zoomscript",
        "button_jetpack",
        "button_dodge",
        "button_minigame",
        "button_prydon",
        "button13",
        "button14",
        "button15",
        "button16",
        "impulse",
    ]
    for column in unrepresented:
        active = int((pd.to_numeric(pov[column], errors="coerce") != 0).sum())
        if active:
            errors.append(f"unrepresented control {column} is active in {active} rows")
    for column in ["button_jump", "button_primary", "button_secondary"]:
        values = pd.to_numeric(pov[column], errors="coerce").to_numpy()
        if not np.isin(values, (0, 1)).all():
            errors.append(f"{column} is not binary")

    if errors:
        failure = {
            "schema_version": "xonotic-duel-v11-authoritative-action-rejection-v1",
            "training_admitted": False,
            "episode_id": args.episode_id,
            "pov_bot": args.pov_bot,
            "telemetry": str(telemetry_path),
            "errors": errors,
        }
        failure_path = output_dir / "action_qa_failed.json"
        failure_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure, indent=2))
        return 2

    movement_x = pov["movement_x"].to_numpy(dtype=np.float64)
    movement_y = pov["movement_y"].to_numpy(dtype=np.float64)
    previous_pitch = pov["previous_view_pitch"].to_numpy(dtype=np.float64)
    previous_yaw = pov["previous_view_yaw"].to_numpy(dtype=np.float64)
    view_pitch = pov["view_pitch"].to_numpy(dtype=np.float64)
    view_yaw = pov["view_yaw"].to_numpy(dtype=np.float64)
    pitch_delta = angular_delta(view_pitch, previous_pitch)
    yaw_delta = angular_delta(view_yaw, previous_yaw)

    left_x = movement_y / MOVEMENT_SCALE
    left_y = -movement_x / MOVEMENT_SCALE
    right_x = -yaw_delta / VIEW_DEGREES_PER_TICK
    right_y = pitch_delta / VIEW_DEGREES_PER_TICK
    continuous = np.column_stack((left_x, left_y, right_x, right_y))
    row_bounded = np.isfinite(continuous).all(axis=1) & (
        np.abs(continuous) <= 1.0 + FLOAT_TOLERANCE
    ).all(axis=1)
    alive = (pov["is_dead"].to_numpy(dtype=np.int64) == 0) & (
        pov["health"].to_numpy(dtype=np.float64) > 0
    )
    row_training_eligible = row_bounded & alive

    action_ticks = np.arange(expected_frames, dtype=np.int64)
    actions = pd.DataFrame(
        {
            "episode_id": args.episode_id,
            "action_tick": action_ticks,
            "server_time": pov["server_time"].to_numpy(dtype=np.float64),
            "desired_forward": movement_x.astype(np.float32),
            "desired_strafe": movement_y.astype(np.float32),
            "desired_vertical": pov["movement_z"].to_numpy(dtype=np.float32),
            "desired_yaw_delta": yaw_delta.astype(np.float32),
            "desired_pitch_delta": pitch_delta.astype(np.float32),
            "desired_jump": pov["button_jump"].to_numpy(dtype=np.int8),
            "desired_primary": pov["button_primary"].to_numpy(dtype=np.int8),
            "desired_secondary": pov["button_secondary"].to_numpy(dtype=np.int8),
            "desired_reload": np.zeros(expected_frames, dtype=np.int8),
            "source_button_mask": pov["button_mask"].to_numpy(dtype=np.int64),
            "source_view_pitch": view_pitch.astype(np.float32),
            "source_view_yaw": view_yaw.astype(np.float32),
            "source_view_roll": pov["view_roll"].to_numpy(dtype=np.float32),
            "source_origin_x": pov["origin_x"].to_numpy(dtype=np.float32),
            "source_origin_y": pov["origin_y"].to_numpy(dtype=np.float32),
            "source_origin_z": pov["origin_z"].to_numpy(dtype=np.float32),
            "source_velocity_x": pov["velocity_x"].to_numpy(dtype=np.float32),
            "source_velocity_y": pov["velocity_y"].to_numpy(dtype=np.float32),
            "source_velocity_z": pov["velocity_z"].to_numpy(dtype=np.float32),
            "source_health": pov["health"].to_numpy(dtype=np.float32),
            "source_is_dead": pov["is_dead"].to_numpy(dtype=np.int8),
            "source_enemy_entity": pov["enemy_entity"].to_numpy(dtype=np.int64),
            "source_enemy_health": pov["enemy_health"].to_numpy(dtype=np.float32),
            "row_training_eligible": row_training_eligible,
            "schema_version": "xonotic-duel-v11-engine-action-audit-v1",
            "namespace": "authoritative_server_bot_control_64hz",
        }
    )

    jump = pov["button_jump"].to_numpy(dtype=np.int8)
    primary = pov["button_primary"].to_numpy(dtype=np.int8)
    secondary = pov["button_secondary"].to_numpy(dtype=np.int8)
    combat_death_transitions = 0
    for _, bot_rows in selected.groupby("bot_name"):
        dead = (
            bot_rows.sort_values("frame_index")["is_dead"].to_numpy(dtype=np.int8)
            != 0
        )
        if len(dead):
            combat_death_transitions += int(dead[0])
            combat_death_transitions += int(
                np.logical_and(dead[1:], ~dead[:-1]).sum()
            )
    zeros = np.zeros(expected_frames, dtype=np.int8)
    model_actions = pd.DataFrame(
        {
            "episode_id": args.episode_id,
            "frame_index": action_ticks,
            "pts_seconds": action_ticks / float(TICK_HZ),
            "source_action_tick": action_ticks,
            "south": jump,
            "east": zeros.copy(),
            "west": zeros.copy(),
            "north": zeros.copy(),
            "left_shoulder": zeros.copy(),
            "right_shoulder": zeros.copy(),
            "left_trigger": secondary,
            "right_trigger": primary,
            "right_thumb": zeros.copy(),
            "j_left": [[float(x), float(y)] for x, y in zip(left_x, left_y)],
            "j_right": [[float(x), float(y)] for x, y in zip(right_x, right_y)],
            "j_left_x": left_x.astype(np.float32),
            "j_left_y": left_y.astype(np.float32),
            "j_right_x": right_x.astype(np.float32),
            "j_right_y": right_y.astype(np.float32),
            "row_training_eligible": row_training_eligible,
            "schema_version": "ltx2-crossfps-xonotic-duel-v11-v1",
            "namespace": "authoritative_server_bot_control_64hz",
        }
    )

    standard_frames = args.duration * STANDARD_FPS
    standard_to_raw = np.asarray(
        [round(index * TICK_HZ / STANDARD_FPS) for index in range(standard_frames)],
        dtype=np.int64,
    )
    standard_row_valid = row_training_eligible[standard_to_raw]
    valid_window_starts: list[int] = []
    if standard_frames >= MODEL_WINDOW_FRAMES:
        for start in range(standard_frames - MODEL_WINDOW_FRAMES + 1):
            raw_start = int(math.floor(start * TICK_HZ / STANDARD_FPS))
            raw_stop = int(
                math.ceil((start + MODEL_WINDOW_FRAMES) * TICK_HZ / STANDARD_FPS)
            )
            raw_stop = min(raw_stop, expected_frames)
            if standard_row_valid[start : start + MODEL_WINDOW_FRAMES].all() and row_training_eligible[
                raw_start:raw_stop
            ].all():
                valid_window_starts.append(start)

    actions_path = output_dir / "actions.parquet"
    model_actions_path = output_dir / "model_actions_64hz.parquet"
    actions.to_parquet(actions_path, index=False)
    model_actions.to_parquet(model_actions_path, index=False)

                                                                              
                                                                            
                                                                              
    action_artifacts_admitted = bool(valid_window_starts) and int(primary.sum()) > 0
    report = {
        "schema_version": "xonotic-duel-v11-authoritative-action-qa-v1",
        "training_admitted": False,
        "action_artifacts_admitted": action_artifacts_admitted,
        "stage1_stage2_unchanged": True,
        "episode_id": args.episode_id,
        "pov_bot": args.pov_bot,
        "source": {
            "telemetry": str(telemetry_path),
            "telemetry_sha256": sha256(telemetry_path),
            "schema_marker": first_line,
            "bot_names": bot_names,
            "raw_telemetry_frames": int(len(raw_frame_indices)),
            "raw_incomplete_observed_frames": int(
                ((frame_row_counts != 2) | (frame_bot_counts != 2)).sum()
            ),
            "selected_tail_frame_index_start": selection_start_frame,
            "selected_tail_frame_index_end": selection_end_frame,
        },
        "artifacts": {
            "actions": str(actions_path),
            "actions_sha256": sha256(actions_path),
            "model_actions_64hz": str(model_actions_path),
            "model_actions_64hz_sha256": sha256(model_actions_path),
        },
        "alignment": {
            "tick_hz": TICK_HZ,
            "observed_server_start_seconds": float(times[0]),
            "duration_seconds": args.duration,
            "selection_policy": "exact final duration*64 authoritative ticks ending at shared telemetry-disable/demo-stop boundary",
            "raw_telemetry_frames": int(len(raw_frame_indices)),
            "discarded_leading_slack_frames": selection_start_frame - int(raw_frame_indices[0]),
            "raw_action_rows": expected_frames,
            "standard_fps": STANDARD_FPS,
            "standard_action_rows": standard_frames,
            "raw_action_chunk_size": expected_frames,
            "standard_chunk_action_rows": standard_frames,
            "button_resampling": "causal_run_max",
        },
        "channel_provenance": {
            "j_left": "authoritative CS(bot).movement sampled in SVQC after bot AI",
            "j_right": "authoritative per-tick delta from SVQC v_angle_old to v_angle",
            "south_jump": "authoritative SVQC bot jump button",
            "right_trigger_primary_fire": "authoritative SVQC bot primary-fire button",
            "left_trigger_secondary_fire": "authoritative SVQC bot secondary-fire button; forced zero by clean-control contract",
            "reload_and_unused_buttons": "forced zero by locked machine-gun clean-control contract",
        },
        "metrics": {
            "both_bot_clean_motion": both_bot_motion,
            "clean_motion_limits": {
                "movement_input_norm": DUEL_MOVEMENT_INPUT_LIMIT,
                "turn_step_degrees_per_tick": DUEL_TURN_STEP_LIMIT_DEGREES,
                "turn_accel_step_degrees_per_tick": DUEL_TURN_ACCEL_STEP_LIMIT_DEGREES,
            },
            "movement_abs_max": {
                "forward": float(np.max(np.abs(movement_x))),
                "strafe": float(np.max(np.abs(movement_y))),
            },
            "view_delta_abs_max_degrees": {
                "yaw": float(np.max(np.abs(yaw_delta))),
                "pitch": float(np.max(np.abs(pitch_delta))),
            },
            "joystick_abs_max": [
                float(np.max(np.abs(continuous[:, index]))) for index in range(4)
            ],
            "primary_fire_active_ticks": int(primary.sum()),
            "primary_fire_runs": run_count(primary),
            "jump_active_ticks": int(jump.sum()),
            "jump_runs": run_count(jump),
            "combat_death_transitions": combat_death_transitions,
            "dead_ticks": int((~alive).sum()),
            "out_of_range_ticks": int((~row_bounded).sum()),
            "eligible_raw_ticks": int(row_training_eligible.sum()),
            "valid_81_frame_window_starts": len(valid_window_starts),
            "total_81_frame_window_starts": max(
                0, standard_frames - MODEL_WINDOW_FRAMES + 1
            ),
        },
        "valid_windows": {
            "standard_20hz_start_frames": valid_window_starts,
            "contiguous_start_ranges_inclusive": contiguous_ranges(valid_window_starts),
            "policy": "exclude any 81-frame window touching death, respawn camera reset, or out-of-range action",
        },
        "gates": {
            "raw_frame_indices_contiguous": True,
            "selected_two_bot_rows_per_tick": bool(
                len(selected_row_counts) == expected_frames
                and (selected_row_counts == 2).all()
                and (selected_bot_counts == 2).all()
            ),
            "pov_rows_exact": len(pov) == expected_frames,
            "server_cadence_64hz": True,
            "pov_locked_entire_window": True,
            "continuous_movement_exact": True,
            "view_delta_exact": True,
            "both_bot_clean_motion": True,
            "unrepresented_controls_zero": True,
            "selected_window_has_combat_kill": combat_death_transitions > 0,
            "selected_window_has_primary_fire": int(primary.sum()) > 0,
            "has_trainable_window": bool(valid_window_starts),
        },
    }
    report_path = output_dir / "action_qa.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if action_artifacts_admitted else 3


if __name__ == "__main__":
    raise SystemExit(main())
