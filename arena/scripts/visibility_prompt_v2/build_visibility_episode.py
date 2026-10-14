                      
"""Join replay-camera visibility with authoritative 64 Hz duel telemetry.

This is an isolated v2 successor to the frozen duel-v10 action builder.  It
keeps the model action columns unchanged, neutralizes controls only while the
POV bot is dead or on the first respawn tick, and never rejects a row merely
because either combatant is dead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


TICK_HZ = 64
RENDER_FPS = 48
STANDARD_FPS = 20
MODEL_WINDOW_FRAMES = 81
MOVEMENT_SCALE = 400.0
VIEW_DEGREES_PER_TICK = 12.0
FLOAT_TOLERANCE = 1e-3
VISIBILITY_SCHEMA = "xonotic-duel-v11-visibility-state-64hz-v2"
MAX_BOUNDED_TICK_REPLAY_GAP_ROWS = 7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def angular_delta(current: np.ndarray, previous: np.ndarray) -> np.ndarray:
    return (current - previous + 180.0) % 360.0 - 180.0


def run_count(values: np.ndarray) -> int:
    active = values.astype(bool)
    if not len(active):
        return 0
    return int(active[0]) + int(np.logical_and(active[1:], ~active[:-1]).sum())


def json_value(value: object) -> object:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"cannot serialize {type(value)!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-qa", type=Path, required=True)
    parser.add_argument(
        "--visibility-tick-raw", "--visibility-raw", dest="visibility_tick_raw", type=Path, required=True
    )
    parser.add_argument("--visibility-render-raw", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    action_qa_path = args.action_qa.resolve()
    visibility_tick_raw_path = args.visibility_tick_raw.resolve()
    visibility_render_raw_path = args.visibility_render_raw.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    action_qa = json.loads(action_qa_path.read_text(encoding="utf-8"))
    telemetry_path = Path(action_qa["source"]["telemetry"]).resolve()
    selection_start = int(action_qa["source"]["selected_tail_frame_index_start"])
    selection_end = int(action_qa["source"]["selected_tail_frame_index_end"])
    episode_id = str(action_qa["episode_id"])
    pov_bot = str(action_qa["pov_bot"])
    duration = int(action_qa["alignment"]["duration_seconds"])
    expected_ticks = duration * TICK_HZ

    telemetry = pd.read_csv(telemetry_path, sep="\t", comment="#")
    selected = telemetry.loc[
        telemetry["frame_index"].between(selection_start, selection_end)
    ].copy()
    selected = selected.sort_values(["frame_index", "bot_name"]).reset_index(drop=True)
    if selected["frame_index"].nunique() != expected_ticks:
        raise ValueError("authoritative selection does not contain the expected ticks")
    if not (selected.groupby("frame_index").size() == 2).all():
        raise ValueError("authoritative selection does not have two bot rows per tick")

    pov = selected.loc[selected["bot_name"].astype(str) == pov_bot].copy()
    opponent = selected.loc[selected["bot_name"].astype(str) != pov_bot].copy()
    pov = pov.sort_values("frame_index").reset_index(drop=True)
    opponent = opponent.sort_values("frame_index").reset_index(drop=True)
    if len(pov) != expected_ticks or len(opponent) != expected_ticks:
        raise ValueError("POV/opponent row count mismatch")
    if not np.array_equal(pov["frame_index"].to_numpy(), opponent["frame_index"].to_numpy()):
        raise ValueError("POV/opponent frame indices are not aligned")

    visibility_tick_raw = pd.read_csv(visibility_tick_raw_path, sep="\t", comment="#")
    visibility_render_raw = pd.read_csv(visibility_render_raw_path, sep="\t", comment="#")
    required_visibility = {
        "demo_time",
        "actual_width",
        "actual_height",
        "fov_x",
        "fov_y",
        "camera_origin_x",
        "camera_origin_y",
        "camera_origin_z",
        "camera_pitch",
        "camera_yaw",
        "camera_roll",
        "player_is_dead_client",
        "enemy_entcs_present",
        "enemy_model_present",
        "enemy_model_is_dead",
        "enemy_distance",
        "enemy_screen_x_norm",
        "enemy_screen_y_norm",
        "enemy_in_frustum",
        "enemy_los_head",
        "enemy_los_chest",
        "enemy_los_pelvis",
    }
    for name, replay in (
        ("tick", visibility_tick_raw),
        ("render", visibility_render_raw),
    ):
        missing = sorted(required_visibility - set(replay.columns))
        if missing:
            raise ValueError(f"{name} visibility replay columns missing: {missing}")
    visibility_tick_raw = visibility_tick_raw.sort_values("demo_time").reset_index(drop=True)
    visibility_render_raw = visibility_render_raw.sort_values("demo_time").reset_index(drop=True)

    target_times = pd.DataFrame(
        {
            "action_tick": np.arange(expected_ticks, dtype=np.int64),
            "server_time": pov["server_time"].to_numpy(dtype=np.float64),
        }
    )
    tick_aligned = pd.merge_asof(
        target_times,
        visibility_tick_raw,
        left_on="server_time",
        right_on="demo_time",
        direction="nearest",
        tolerance=2e-5,
    )
    tick_replay_exact = tick_aligned["demo_time"].notna().to_numpy(dtype=bool)
    tick_replay_gap_indices = np.flatnonzero(~tick_replay_exact)
    if len(tick_replay_gap_indices):
        gap_splits = np.flatnonzero(np.diff(tick_replay_gap_indices) > 1) + 1
        tick_replay_gap_runs = np.split(tick_replay_gap_indices, gap_splits)
    else:
        tick_replay_gap_runs = []
    tick_replay_gap_run_count = len(tick_replay_gap_runs)
    tick_replay_max_gap_rows = max((len(run) for run in tick_replay_gap_runs), default=0)
    tick_replay_gap_is_internal = bool(
        not len(tick_replay_gap_indices)
        or (
            int(tick_replay_gap_indices[0]) > 0
            and int(tick_replay_gap_indices[-1]) < expected_ticks - 1
        )
    )
    tick_replay_gap_bounded = bool(
        tick_replay_gap_run_count <= 1
        and tick_replay_max_gap_rows <= MAX_BOUNDED_TICK_REPLAY_GAP_ROWS
        and tick_replay_gap_is_internal
    )
    if not tick_replay_gap_bounded:
        raise ValueError(
            "64 Hz replay gaps exceed the explicit audit fallback bound: "
            f"rows={len(tick_replay_gap_indices)} runs={tick_replay_gap_run_count} "
            f"max_run={tick_replay_max_gap_rows} internal={tick_replay_gap_is_internal}"
        )
    tick_alignment_error = np.full(expected_ticks, np.nan, dtype=np.float64)
    tick_alignment_error[tick_replay_exact] = np.abs(
        tick_aligned.loc[tick_replay_exact, "server_time"].to_numpy(dtype=np.float64)
        - tick_aligned.loc[tick_replay_exact, "demo_time"].to_numpy(dtype=np.float64)
    )

                                                                            
                                                                             
                                                                             
                                                                   
    expected_render_frames = duration * RENDER_FPS
    if len(visibility_render_raw) < expected_render_frames:
        raise ValueError("48 Hz replay is shorter than the accepted video")
    render_tail = visibility_render_raw.iloc[-expected_render_frames:].copy().reset_index(drop=True)
    render_tail["render_frame_index"] = np.arange(expected_render_frames, dtype=np.int64)
    render_tail["render_pts_seconds"] = (
        render_tail["render_frame_index"].to_numpy(dtype=np.float64) / RENDER_FPS
    )
    target_pts = pd.DataFrame(
        {
            "action_tick": np.arange(expected_ticks, dtype=np.int64),
            "pts_seconds": np.arange(expected_ticks, dtype=np.float64) / TICK_HZ,
        }
    )
    aligned = pd.merge_asof(
        target_pts,
        render_tail,
        left_on="pts_seconds",
        right_on="render_pts_seconds",
        direction="nearest",
        tolerance=(0.5 / RENDER_FPS + 1e-6),
    )
    if aligned["render_pts_seconds"].isna().any():
        raise ValueError("some authoritative ticks have no matching 48 Hz render frame")
    render_alignment_error = np.abs(
        aligned["pts_seconds"].to_numpy(dtype=np.float64)
        - aligned["render_pts_seconds"].to_numpy(dtype=np.float64)
    )

                                                                              
                                                                             
                                                                             
                                                                              
                                                                            
                                                                            
                                                                           
                                             
    tick_audit_columns = (
        "enemy_in_frustum",
        "enemy_screen_x_norm",
        "enemy_screen_y_norm",
        "enemy_los_head",
        "enemy_los_chest",
        "enemy_los_pelvis",
    )
    for column in tick_audit_columns:
        tick_aligned.loc[~tick_replay_exact, column] = aligned.loc[
            ~tick_replay_exact, column
        ].to_numpy()

    player_health = pov["health"].to_numpy(dtype=np.float64)
    enemy_health = opponent["health"].to_numpy(dtype=np.float64)
    player_dead = (pov["is_dead"].to_numpy(dtype=np.int64) != 0) | (player_health <= 0)
    enemy_dead = (opponent["is_dead"].to_numpy(dtype=np.int64) != 0) | (enemy_health <= 0)
    player_prev_dead = np.r_[player_dead[0], player_dead[:-1]]
    enemy_prev_dead = np.r_[enemy_dead[0], enemy_dead[:-1]]
    player_killed = np.r_[False, np.logical_and(player_dead[1:], ~player_dead[:-1])]
    enemy_killed = np.r_[False, np.logical_and(enemy_dead[1:], ~enemy_dead[:-1])]
    player_respawned = np.r_[False, np.logical_and(~player_dead[1:], player_dead[:-1])]
    enemy_respawned = np.r_[False, np.logical_and(~enemy_dead[1:], enemy_dead[:-1])]
    player_nonlethal_damage = np.r_[
        False,
        np.logical_and.reduce(
            (
                player_health[1:] < player_health[:-1] - 1e-6,
                ~player_dead[1:],
                ~player_dead[:-1],
            )
        ),
    ]
    enemy_nonlethal_damage = np.r_[
        False,
        np.logical_and.reduce(
            (
                enemy_health[1:] < enemy_health[:-1] - 1e-6,
                ~enemy_dead[1:],
                ~enemy_dead[:-1],
            )
        ),
    ]

    model_present = aligned["enemy_model_present"].to_numpy(dtype=np.int8) != 0
    entcs_present = aligned["enemy_entcs_present"].to_numpy(dtype=np.int8) != 0
    in_frustum = aligned["enemy_in_frustum"].to_numpy(dtype=np.int8) != 0
    los_head = aligned["enemy_los_head"].to_numpy(dtype=np.int8) != 0
    los_chest = aligned["enemy_los_chest"].to_numpy(dtype=np.int8) != 0
    los_pelvis = aligned["enemy_los_pelvis"].to_numpy(dtype=np.int8) != 0
    los_count = los_head.astype(np.int8) + los_chest.astype(np.int8) + los_pelvis.astype(np.int8)
    visibility_state = np.full(expected_ticks, "visible", dtype=object)
    visibility_state[~in_frustum] = "offscreen"
    visibility_state[np.logical_and(in_frustum, los_count == 0)] = "fully_occluded"
    visibility_state[np.logical_and(in_frustum, np.isin(los_count, (1, 2)))] = "partially_visible"
    visibility_state[np.logical_and(enemy_dead, ~model_present)] = "dead_or_absent"
    visibility_state[~entcs_present] = "dead_or_absent"
    enemy_render_state = np.where(
        ~entcs_present,
        "absent",
        np.where(~model_present, "not_rendered", np.where(enemy_dead, "dead_body_present", "active_body_present")),
    )

    width = aligned["actual_width"].to_numpy(dtype=np.float64)
    height = aligned["actual_height"].to_numpy(dtype=np.float64)
    screen_x_norm = aligned["enemy_screen_x_norm"].to_numpy(dtype=np.float64)
    screen_y_norm = aligned["enemy_screen_y_norm"].to_numpy(dtype=np.float64)

    movement_x = pov["movement_x"].to_numpy(dtype=np.float64)
    movement_y = pov["movement_y"].to_numpy(dtype=np.float64)
    pitch_delta = angular_delta(
        pov["view_pitch"].to_numpy(dtype=np.float64),
        pov["previous_view_pitch"].to_numpy(dtype=np.float64),
    )
    yaw_delta = angular_delta(
        pov["view_yaw"].to_numpy(dtype=np.float64),
        pov["previous_view_yaw"].to_numpy(dtype=np.float64),
    )
    left_x = movement_y / MOVEMENT_SCALE
    left_y = -movement_x / MOVEMENT_SCALE
    right_x = -yaw_delta / VIEW_DEGREES_PER_TICK
    right_y = pitch_delta / VIEW_DEGREES_PER_TICK
    jump = pov["button_jump"].to_numpy(dtype=np.int8)
    primary = pov["button_primary"].to_numpy(dtype=np.int8)
    secondary = pov["button_secondary"].to_numpy(dtype=np.int8)
    original_continuous = np.column_stack((left_x, left_y, right_x, right_y))
    original_bounded = np.isfinite(original_continuous).all(axis=1) & (
        np.abs(original_continuous) <= 1.0 + FLOAT_TOLERANCE
    ).all(axis=1)

    respawn_tick = player_respawned
    neutralize = np.logical_or(player_dead, respawn_tick)
    effective_continuous = original_continuous.copy()
    effective_jump = jump.copy()
    effective_primary = primary.copy()
    effective_secondary = secondary.copy()
    effective_continuous[neutralize] = 0.0
    effective_jump[neutralize] = 0
    effective_primary[neutralize] = 0
    effective_secondary[neutralize] = 0
    effective_bounded = np.isfinite(effective_continuous).all(axis=1) & (
        np.abs(effective_continuous) <= 1.0 + FLOAT_TOLERANCE
    ).all(axis=1)
    row_training_eligible = effective_bounded
    sanitization_reason = np.full(expected_ticks, "none", dtype=object)
    sanitization_reason[player_dead] = "dead_control_neutralized"
    sanitization_reason[respawn_tick] = "respawn_camera_reset_neutralized"
    sanitization_reason[np.logical_and(~neutralize, ~original_bounded)] = "alive_out_of_range_preserved_and_excluded"

    zeros = np.zeros(expected_ticks, dtype=np.int8)
    model_actions = pd.DataFrame(
        {
            "episode_id": episode_id,
            "frame_index": np.arange(expected_ticks, dtype=np.int64),
            "pts_seconds": np.arange(expected_ticks, dtype=np.float64) / TICK_HZ,
            "source_action_tick": np.arange(expected_ticks, dtype=np.int64),
            "south": effective_jump,
            "east": zeros.copy(),
            "west": zeros.copy(),
            "north": zeros.copy(),
            "left_shoulder": zeros.copy(),
            "right_shoulder": zeros.copy(),
            "left_trigger": effective_secondary,
            "right_trigger": effective_primary,
            "right_thumb": zeros.copy(),
            "j_left": [[float(x), float(y)] for x, y in effective_continuous[:, :2]],
            "j_right": [[float(x), float(y)] for x, y in effective_continuous[:, 2:]],
            "j_left_x": effective_continuous[:, 0].astype(np.float32),
            "j_left_y": effective_continuous[:, 1].astype(np.float32),
            "j_right_x": effective_continuous[:, 2].astype(np.float32),
            "j_right_y": effective_continuous[:, 3].astype(np.float32),
            "row_training_eligible": row_training_eligible,
            "schema_version": "ltx2-crossfps-xonotic-duel-v11-v1",
            "namespace": "authoritative_server_bot_control_64hz",
        }
    )

    visibility = pd.DataFrame(
        {
            "episode_id": episode_id,
            "action_tick": np.arange(expected_ticks, dtype=np.int64),
            "pts_seconds": np.arange(expected_ticks, dtype=np.float64) / TICK_HZ,
            "server_time": pov["server_time"].to_numpy(dtype=np.float64),
            "render_demo_time": aligned["demo_time"].to_numpy(dtype=np.float64),
            "render_frame_index": aligned["render_frame_index"].to_numpy(dtype=np.int64),
            "render_pts_seconds": aligned["render_pts_seconds"].to_numpy(dtype=np.float64),
            "render_alignment_error_seconds": render_alignment_error,
            "tick_demo_time": tick_aligned["demo_time"].to_numpy(dtype=np.float64),
            "tick_alignment_error_seconds": tick_alignment_error,
            "tick_replay_exact": tick_replay_exact,
            "tick_replay_audit_source": np.where(
                tick_replay_exact, "exact_64hz_replay", "final_48hz_replay_fallback"
            ),
            "player_is_dead": player_dead,
            "player_health": player_health.astype(np.float32),
            "player_origin_x": pov["origin_x"].to_numpy(dtype=np.float32),
            "player_origin_y": pov["origin_y"].to_numpy(dtype=np.float32),
            "player_origin_z": pov["origin_z"].to_numpy(dtype=np.float32),
            "player_velocity_x": pov["velocity_x"].to_numpy(dtype=np.float32),
            "player_velocity_y": pov["velocity_y"].to_numpy(dtype=np.float32),
            "player_velocity_z": pov["velocity_z"].to_numpy(dtype=np.float32),
            "enemy_is_dead": enemy_dead,
            "enemy_health": enemy_health.astype(np.float32),
            "enemy_origin_x": opponent["origin_x"].to_numpy(dtype=np.float32),
            "enemy_origin_y": opponent["origin_y"].to_numpy(dtype=np.float32),
            "enemy_origin_z": opponent["origin_z"].to_numpy(dtype=np.float32),
            "enemy_velocity_x": opponent["velocity_x"].to_numpy(dtype=np.float32),
            "enemy_velocity_y": opponent["velocity_y"].to_numpy(dtype=np.float32),
            "enemy_velocity_z": opponent["velocity_z"].to_numpy(dtype=np.float32),
            "enemy_in_frustum": in_frustum,
            "enemy_screen_x": screen_x_norm * width,
            "enemy_screen_y": screen_y_norm * height,
            "enemy_screen_x_norm": screen_x_norm,
            "enemy_screen_y_norm": screen_y_norm,
            "enemy_distance": aligned["enemy_distance"].to_numpy(dtype=np.float32),
            "enemy_los_head": los_head,
            "enemy_los_chest": los_chest,
            "enemy_los_pelvis": los_pelvis,
            "enemy_visibility_state": visibility_state,
            "enemy_render_state": enemy_render_state,
            "enemy_model_present": model_present,
            "enemy_model_is_dead_client": aligned["enemy_model_is_dead"].to_numpy(dtype=np.int8) != 0,
            "tick_enemy_in_frustum": tick_aligned["enemy_in_frustum"].to_numpy(dtype=np.int8) != 0,
            "tick_enemy_screen_x_norm": tick_aligned["enemy_screen_x_norm"].to_numpy(dtype=np.float64),
            "tick_enemy_screen_y_norm": tick_aligned["enemy_screen_y_norm"].to_numpy(dtype=np.float64),
            "tick_enemy_los_head": tick_aligned["enemy_los_head"].to_numpy(dtype=np.int8) != 0,
            "tick_enemy_los_chest": tick_aligned["enemy_los_chest"].to_numpy(dtype=np.int8) != 0,
            "tick_enemy_los_pelvis": tick_aligned["enemy_los_pelvis"].to_numpy(dtype=np.int8) != 0,
            "player_fired": pov["button_primary"].to_numpy(dtype=np.int8) != 0,
            "enemy_fired": opponent["button_primary"].to_numpy(dtype=np.int8) != 0,
            "enemy_jumped": opponent["button_jump"].to_numpy(dtype=np.int8) != 0,
            "player_took_nonlethal_damage": player_nonlethal_damage,
            "enemy_took_nonlethal_damage": enemy_nonlethal_damage,
            "player_killed": player_killed,
            "enemy_killed": enemy_killed,
            "player_respawned": player_respawned,
            "enemy_respawned": enemy_respawned,
            "player_wounded": np.logical_and(~player_dead, player_health < 100),
            "enemy_wounded": np.logical_and(~enemy_dead, enemy_health < 100),
            "camera_origin_x": aligned["camera_origin_x"].to_numpy(dtype=np.float32),
            "camera_origin_y": aligned["camera_origin_y"].to_numpy(dtype=np.float32),
            "camera_origin_z": aligned["camera_origin_z"].to_numpy(dtype=np.float32),
            "camera_pitch": aligned["camera_pitch"].to_numpy(dtype=np.float32),
            "camera_yaw": aligned["camera_yaw"].to_numpy(dtype=np.float32),
            "camera_roll": aligned["camera_roll"].to_numpy(dtype=np.float32),
            "fov_x": aligned["fov_x"].to_numpy(dtype=np.float32),
            "fov_y": aligned["fov_y"].to_numpy(dtype=np.float32),
            "render_width": width.astype(np.int32),
            "render_height": height.astype(np.int32),
            "action_original_bounded": original_bounded,
            "action_training_eligible": row_training_eligible,
            "action_sanitized": neutralize,
            "action_sanitization_reason": sanitization_reason,
            "schema_version": VISIBILITY_SCHEMA,
        }
    )

    standard_frames = duration * STANDARD_FPS
    standard_to_raw = np.asarray(
        [round(index * TICK_HZ / STANDARD_FPS) for index in range(standard_frames)],
        dtype=np.int64,
    )
    standard_valid = row_training_eligible[standard_to_raw]
    valid_window_starts: list[int] = []
    for start in range(standard_frames - MODEL_WINDOW_FRAMES + 1):
        raw_start = int(math.floor(start * TICK_HZ / STANDARD_FPS))
        raw_stop = min(
            int(math.ceil((start + MODEL_WINDOW_FRAMES) * TICK_HZ / STANDARD_FPS)),
            expected_ticks,
        )
        if standard_valid[start : start + MODEL_WINDOW_FRAMES].all() and row_training_eligible[
            raw_start:raw_stop
        ].all():
            valid_window_starts.append(start)

    visibility_path = output_dir / "visibility_64hz.parquet"
    model_actions_path = output_dir / "model_actions_64hz.parquet"
    visibility.to_parquet(visibility_path, index=False)
    model_actions.to_parquet(model_actions_path, index=False)

    state_counts = visibility["enemy_visibility_state"].value_counts().sort_index().to_dict()
    offscreen_mask = visibility["enemy_visibility_state"].isin(
        ["offscreen", "fully_occluded", "dead_or_absent"]
    ).to_numpy(dtype=bool)
    enemy_fire = visibility["enemy_fired"].to_numpy(dtype=bool)
    offscreen_enemy_fire_ticks = int(np.logical_and(offscreen_mask, enemy_fire).sum())
    enemy_respawn_indices = np.flatnonzero(enemy_respawned)
    respawn_starts_outside_view = bool(
        all(
            str(visibility.iloc[index]["enemy_visibility_state"])
            in {"offscreen", "fully_occluded", "dead_or_absent"}
            for index in enemy_respawn_indices
        )
    )
    qa = {
        "schema_version": "xonotic-duel-v11-visibility-action-qa-v2",
        "episode_id": episode_id,
        "pov_bot": pov_bot,
        "duration_seconds": duration,
        "tick_hz": TICK_HZ,
        "source": {
            "action_qa": str(action_qa_path),
            "action_qa_sha256": sha256(action_qa_path),
            "authoritative_telemetry": str(telemetry_path),
            "authoritative_telemetry_sha256": sha256(telemetry_path),
            "visibility_tick_replay": str(visibility_tick_raw_path),
            "visibility_tick_replay_sha256": sha256(visibility_tick_raw_path),
            "visibility_render_replay": str(visibility_render_raw_path),
            "visibility_render_replay_sha256": sha256(visibility_render_raw_path),
        },
        "artifacts": {
            "visibility_64hz": str(visibility_path),
            "visibility_64hz_sha256": sha256(visibility_path),
            "model_actions_64hz": str(model_actions_path),
            "model_actions_64hz_sha256": sha256(model_actions_path),
        },
        "camera_alignment": {
            "policy": (
                "exact 64 Hz replay join where present for auxiliary tick audit; one explicitly marked "
                "internal gap of at most 7 ticks may use the aligned final 48 Hz values for tick-audit-only "
                "fields; final training visibility always comes from the final 48 Hz replay tail"
            ),
            "tick_replay_exact_rows": int(tick_replay_exact.sum()),
            "tick_replay_fallback_rows": int((~tick_replay_exact).sum()),
            "tick_replay_gap_run_count": tick_replay_gap_run_count,
            "tick_replay_max_gap_rows": tick_replay_max_gap_rows,
            "tick_replay_gap_action_tick_indices": [
                int(value) for value in tick_replay_gap_indices.tolist()
            ],
            "tick_replay_gap_is_internal": tick_replay_gap_is_internal,
            "tick_replay_max_abs_error_seconds_present_rows": float(
                np.nanmax(tick_alignment_error)
            ),
            "tick_replay_p99_abs_error_seconds_present_rows": float(
                np.nanquantile(tick_alignment_error, 0.99)
            ),
            "render_replay_max_abs_error_seconds": float(render_alignment_error.max()),
            "render_replay_p99_abs_error_seconds": float(np.quantile(render_alignment_error, 0.99)),
            "render_fps": RENDER_FPS,
            "render_tail_frames": expected_render_frames,
            "render_width_values": sorted(int(x) for x in np.unique(width)),
            "render_height_values": sorted(int(x) for x in np.unique(height)),
            "uses_final_render_camera": True,
            "death_view_not_reconstructed_from_bot_v_angle": True,
        },
        "events": {
            "player_nonlethal_damage_ticks": int(player_nonlethal_damage.sum()),
            "enemy_nonlethal_damage_ticks": int(enemy_nonlethal_damage.sum()),
            "player_kills": int(player_killed.sum()),
            "enemy_kills": int(enemy_killed.sum()),
            "player_respawns": int(player_respawned.sum()),
            "enemy_respawns": int(enemy_respawned.sum()),
            "player_dead_ticks": int(player_dead.sum()),
            "enemy_dead_ticks": int(enemy_dead.sum()),
            "player_fire_runs": run_count(pov["button_primary"].to_numpy(dtype=np.int8)),
            "enemy_fire_runs": run_count(opponent["button_primary"].to_numpy(dtype=np.int8)),
            "offscreen_enemy_fire_ticks": offscreen_enemy_fire_ticks,
            "enemy_respawn_starts_outside_view": respawn_starts_outside_view,
        },
        "visibility_state_counts": {str(k): int(v) for k, v in state_counts.items()},
        "action_policy": {
            "model_schema_version": "ltx2-crossfps-xonotic-duel-v11-v1",
            "model_columns_unchanged": True,
            "dead_ticks": "all model action channels neutralized to zero because controls are non-actionable while dead",
            "first_respawn_tick": "all model action channels neutralized to zero because spawn camera relocation is not a player view action",
            "alive_out_of_range": "preserved for audit and marked ineligible; never clipped or interpolated",
            "sanitized_dead_ticks": int(player_dead.sum()),
            "sanitized_respawn_ticks": int(player_respawned.sum()),
            "alive_out_of_range_ticks": int(np.logical_and(~neutralize, ~original_bounded).sum()),
            "eligible_ticks": int(row_training_eligible.sum()),
            "valid_81_frame_window_starts": len(valid_window_starts),
            "total_81_frame_window_starts": standard_frames - MODEL_WINDOW_FRAMES + 1,
            "valid_81_frame_window_start_indices": valid_window_starts,
        },
        "gates": {
            "exact_authoritative_ticks": len(visibility) == expected_ticks,
            "exact_tick_replay_match_all_present_rows": bool(
                (tick_alignment_error[tick_replay_exact] <= 2e-5).all()
            ),
            "tick_replay_gap_bounded_and_explicit": tick_replay_gap_bounded,
            "tick_replay_gap_uses_only_final_render_audit_fallback": True,
            "render_camera_within_half_frame_every_tick": bool(
                (render_alignment_error <= 0.5 / RENDER_FPS + 1e-6).all()
            ),
            "actual_render_resolution_960x540": bool((width == 960).all() and (height == 540).all()),
            "three_los_rays_present": True,
            "screen_projection_finite": bool(
                np.isfinite(np.column_stack((screen_x_norm, screen_y_norm))).all()
            ),
            "death_rows_training_eligible": bool(row_training_eligible[player_dead].all()),
            "respawn_rows_training_eligible": bool(row_training_eligible[respawn_tick].all()),
            "death_not_used_as_filter": True,
            "model_action_schema_unchanged": True,
            "no_enemy_fire_while_outside_view": offscreen_enemy_fire_ticks == 0,
            "enemy_respawns_start_outside_view": respawn_starts_outside_view,
            "has_trainable_window": bool(valid_window_starts),
        },
    }
    qa["all_pass"] = bool(all(qa["gates"].values()))
    qa_path = output_dir / "episode_qa.json"
    qa_path.write_text(
        json.dumps(qa, indent=2, default=json_value) + "\n", encoding="utf-8"
    )
    print(json.dumps(qa, indent=2, default=json_value))
    return 0 if qa["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
