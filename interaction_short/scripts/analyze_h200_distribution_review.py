                      
"""Summarize and visualize a non-training H200 distribution review batch."""

from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

import xonotic_capture as capture


MODEL_ACTION_GATES = (
    "model_action_rows_exact",
    "model_action_ltx2_schema",
    "model_action_frame_alignment",
    "model_action_continuous_range",
    "model_action_engine_roundtrip",
    "model_action_buttons_binary",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return capture.load_jsonl(path) if path.is_file() else []


def rejection_failure_labels(
    rejection: dict[str, Any],
) -> list[str]:
    """Extract stable labels from dict, list, or plain-text reject details."""
    reason = str(rejection.get("reason") or "unknown")
    detail = str(rejection.get("detail", ""))
    payload_text = detail.partition(": ")[2]
    try:
        payload = json.loads(payload_text)
    except (json.JSONDecodeError, TypeError):
        payload = None

    labels: list[str] = []
    if isinstance(payload, dict):
        failed = payload.get("failed") or []
        if isinstance(failed, str):
            labels.append(failed)
        elif isinstance(failed, list):
            labels.extend(str(value) for value in failed)
        checks = payload.get("checks") or {}
        if isinstance(checks, dict):
            labels.extend(
                str(name)
                for name, passed in checks.items()
                if passed is not True
            )
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                labels.append(item)
            elif isinstance(item, dict):
                label = (
                    item.get("reason")
                    or item.get("label")
                    or item.get("gate")
                )
                if label:
                    labels.append(str(label))

    return list(dict.fromkeys(labels)) or [reason]


def counter(
    rows: list[dict[str, Any]],
    getter: Callable[[dict[str, Any]], Any],
) -> dict[str, int]:
    values: Counter[str] = Counter()
    for row in rows:
        value = getter(row)
        if value is not None and value != "":
            values[str(value).lower() if isinstance(value, bool) else str(value)] += 1
    return dict(
        sorted(values.items(), key=lambda item: (-item[1], item[0]))
    )


def numeric_stats(values: list[Any]) -> dict[str, float | int | None]:
    numeric = np.asarray(
        [
            float(value)
            for value in values
            if value is not None and np.isfinite(float(value))
        ],
        dtype=np.float64,
    )
    if not numeric.size:
        return {
            "count": 0,
            "min": None,
            "p10": None,
            "p50": None,
            "p90": None,
            "max": None,
        }
    return {
        "count": int(numeric.size),
        "min": float(numeric.min()),
        "p10": float(np.percentile(numeric, 10)),
        "p50": float(np.percentile(numeric, 50)),
        "p90": float(np.percentile(numeric, 90)),
        "max": float(numeric.max()),
    }


def weapon_activity_metrics(
    weapon: str, events: pd.DataFrame
) -> dict[str, int | bool | str]:
    """Separate generic engine fire events from actual shots and melee.

    Xonotic logs every weapon activation as ``event=fire``. In particular,
    Shotgun secondary is the gun-butt melee action, so counting that event as
    a gunshot makes both the review UI and the distribution summary wrong.
    """
    if events.empty or "event" not in events.columns:
        fire_events = events.iloc[0:0]
    else:
        fire_events = events[events["event"].astype(str) == "fire"]
    if "secondary" in fire_events.columns:
        secondary = (
            pd.to_numeric(fire_events["secondary"], errors="coerce")
            .fillna(0)
            .astype(int)
            == 1
        )
    else:
        secondary = pd.Series(False, index=fire_events.index)
    melee_mask = secondary if weapon.casefold() == "shotgun" else (
        pd.Series(False, index=fire_events.index)
    )
    activation_count = int(len(fire_events))
    melee_count = int(melee_mask.sum())
    shot_count = activation_count - melee_count
    return {
        "weapon_action_semantics": (
            "shotgun_secondary_melee"
            if melee_count
            else "projectile_or_hitscan_fire"
            if shot_count
            else "no_weapon_activation"
        ),
        "weapon_activation_count": activation_count,
        "shot_count": shot_count,
        "melee_count": melee_count,
        "actual_weapon_activation": activation_count > 0,
        "actual_shot": shot_count > 0,
        "actual_melee": melee_count > 0,
    }


def planned_distributions(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    getters: dict[str, Callable[[dict[str, Any]], Any]] = {
        "dataset_role": lambda row: row.get("dataset_role"),
        "primary_bucket": lambda row: row.get("primary_bucket"),
        "category": lambda row: row.get("category"),
        "enemy_present": lambda row: row.get("enemy_present"),
        "gametype": lambda row: row.get("gametype"),
        "map": lambda row: row.get("map"),
        "weapon": lambda row: row.get("weapon"),
        "weapon_action": lambda row: (
            (row.get("action_design") or {}).get("weapon_action")
        ),
        "locomotion_direction": lambda row: (
            (row.get("action_design") or {}).get(
                "locomotion_direction"
            )
        ),
        "movement_profile": lambda row: (
            (row.get("action_design") or {}).get("movement_profile")
        ),
        "view_direction": lambda row: (
            (row.get("action_design") or {}).get("view_direction")
        ),
        "view_profile": lambda row: (
            (row.get("action_design") or {}).get("view_profile")
        ),
        "action_arity": lambda row: (
            (row.get("action_design") or {}).get("action_arity")
        ),
        "jump": lambda row: (
            (row.get("action_design") or {}).get("jump")
        ),
        "fire_required": lambda row: (
            (row.get("acceptance") or {}).get("fire_required")
        ),
        "reload_required": lambda row: (
            (row.get("acceptance") or {}).get("reload_success")
        ),
        "route_present": lambda row: bool(row.get("route_request")),
        "enemy_policy": lambda row: (
            (row.get("enemy_policy") or {}).get("name")
        ),
        "net_displacement_bin": lambda row: (
            (row.get("scheduler_targets") or {}).get(
                "net_displacement_bin"
            )
        ),
        "yaw_range_bin": lambda row: (
            (row.get("scheduler_targets") or {}).get("yaw_range_bin")
        ),
        "pitch_range_bin": lambda row: (
            (row.get("scheduler_targets") or {}).get(
                "pitch_range_bin"
            )
        ),
        "target_relation": lambda row: (
            (row.get("scheduler_targets") or {}).get("target_relation")
        ),
        "distance_bin": lambda row: (
            (row.get("scheduler_targets") or {}).get("distance_bin")
        ),
    }
    return {
        name: counter(rows, getter)
        for name, getter in getters.items()
    }


def action_activity(episode_path: Path) -> dict[str, Any]:
    actions = pd.read_parquet(episode_path / "actions.parquet")
    frames = pd.read_parquet(episode_path / "frames.parquet")
    model_actions_path = episode_path / "model_actions.parquet"
    model_actions = (
        pd.read_parquet(model_actions_path)
        if model_actions_path.is_file()
        else pd.DataFrame()
    )
    visible = actions[
        (actions["action_tick"] >= capture.WARMUP_TICKS)
        & (
            actions["action_tick"]
            < capture.WARMUP_TICKS + capture.OUTPUT_TICKS
        )
    ].copy()
    move = (
        visible["desired_forward"].abs()
        + visible["desired_strafe"].abs()
    ) > 1e-6
    view = (
        visible["desired_yaw_delta"].abs()
        + visible["desired_pitch_delta"].abs()
    ) > 1e-9
    weapon = (
        visible["desired_primary"].astype(bool)
        | visible["desired_secondary"].astype(bool)
        | visible["desired_reload"].astype(bool)
    )
    tail = visible["action_tick"] >= (
        capture.WARMUP_TICKS + 3 * capture.TICK_HZ
    )

    def ticks(mask: Any) -> tuple[int | None, int | None]:
        selected = visible.loc[mask, "action_tick"]
        if selected.empty:
            return None, None
        return int(selected.iloc[0]), int(selected.iloc[-1])

    move_first, move_last = ticks(move)
    view_first, view_last = ticks(view)
    model_axes = (
        model_actions[
            ["j_left_x", "j_left_y", "j_right_x", "j_right_y"]
        ].to_numpy(dtype=np.float64)
        if {
            "j_left_x",
            "j_left_y",
            "j_right_x",
            "j_right_y",
        }
        <= set(model_actions.columns)
        else np.empty((0, 4), dtype=np.float64)
    )
    left_l2 = (
        np.linalg.norm(model_axes[:, :2], axis=1)
        if len(model_axes)
        else np.empty(0, dtype=np.float64)
    )
    right_l2 = (
        np.linalg.norm(model_axes[:, 2:], axis=1)
        if len(model_axes)
        else np.empty(0, dtype=np.float64)
    )
    model_buttons = (
        model_actions[list(capture.MODEL_ACTION_BUTTON_COLUMNS)]
        .to_numpy(dtype=np.float64)
        if set(capture.MODEL_ACTION_BUTTON_COLUMNS)
        <= set(model_actions.columns)
        else np.empty(
            (0, len(capture.MODEL_ACTION_BUTTON_COLUMNS)),
            dtype=np.float64,
        )
    )
    model_tick_exact = bool(
        len(model_actions) == len(frames) == capture.OUTPUT_TICKS
        and "source_action_tick" in model_actions
        and "episode_server_tick" in frames
        and np.array_equal(
            model_actions["source_action_tick"].to_numpy(),
            frames["episode_server_tick"].to_numpy(),
        )
    )
    return {
        "move_active_ticks": int(move.sum()),
        "view_active_ticks": int(view.sum()),
        "weapon_active_ticks": int(weapon.sum()),
        "move_first_tick": move_first,
        "move_last_tick": move_last,
        "view_first_tick": view_first,
        "view_last_tick": view_last,
        "move_tail_active_ticks": int((move & tail).sum()),
        "view_tail_active_ticks": int((view & tail).sum()),
        "move_tail_active_fraction": round(
            float((move & tail).sum()) / max(1, int(tail.sum())), 6
        ),
        "view_tail_active_fraction": round(
            float((view & tail).sum()) / max(1, int(tail.sum())), 6
        ),
        "yaw_positive_ticks": int(
            (visible["desired_yaw_delta"] > 1e-9).sum()
        ),
        "yaw_negative_ticks": int(
            (visible["desired_yaw_delta"] < -1e-9).sum()
        ),
        "pitch_positive_ticks": int(
            (visible["desired_pitch_delta"] > 1e-9).sum()
        ),
        "pitch_negative_ticks": int(
            (visible["desired_pitch_delta"] < -1e-9).sum()
        ),
        "model_action_rows": len(model_actions),
        "model_action_frame_tick_exact": model_tick_exact,
        "model_axis_abs_max": (
            float(np.abs(model_axes).max()) if model_axes.size else None
        ),
        "model_left_l2_max": (
            float(left_l2.max()) if left_l2.size else None
        ),
        "model_right_l2_max": (
            float(right_l2.max()) if right_l2.size else None
        ),
        "model_button_active_frames": (
            int((model_buttons != 0).any(axis=1).sum())
            if model_buttons.size
            else 0
        ),
        "model_buttons_binary": bool(
            model_buttons.size
            and np.isin(model_buttons, (0.0, 1.0)).all()
        ),
    }


def qa_row(
    plan: dict[str, Any], record: dict[str, Any]
) -> dict[str, Any]:
    episode_path = Path(record["episode_path"])
    qa = json.loads(
        (episode_path / "qa.json").read_text(encoding="utf-8")
    )
    motion = qa.get("motion") or {}
    relation = qa.get("target_relation") or {}
    runtime = qa.get("runtime") or {}
    hard_gates = qa.get("hard_gates") or {}
    live = qa.get("live_precheck") or {}
    hud = qa.get("hud") or {}
    design = plan.get("action_design") or {}
    acceptance = plan.get("acceptance") or {}
    expected_reload = bool(acceptance.get("reload_success"))
    event_counts = qa["events"].get("event_counts") or {}
    events = pd.read_parquet(episode_path / "events.parquet")
    reload_proof = capture.reload_event_proof(
        events,
        str(
            acceptance.get(
                "reload_weapon",
                plan.get("weapon_netname", ""),
            )
        ),
        expected_start_tick=acceptance.get(
            "reload_start_server_tick"
        ),
        expected_duration_ticks=acceptance.get(
            "reload_duration_ticks"
        ),
        expected_initial_clip=acceptance.get(
            "reload_initial_clip"
        ),
        expected_capacity=acceptance.get(
            "reload_clip_capacity"
        ),
    )
    actual_reload = bool(reload_proof["passed"])
    weapon_activity = weapon_activity_metrics(
        str(plan.get("weapon", "")), events
    )
    collision = capture.movement_blockage_metrics(
        pd.read_parquet(episode_path / "states.parquet"),
        frames=pd.read_parquet(episode_path / "frames.parquet"),
        scenario=plan,
    )
    activity = action_activity(episode_path)
    model_action = qa.get("model_action") or {}
    model_action_metrics = model_action.get("metrics") or {}
    qa_with_current_collision = {
        **qa,
        "telemetry": {
            **(qa.get("telemetry") or {}),
            "movement_blockage": collision,
        },
    }
    role_eligible_v2 = capture.stage1_role_eligible(
        plan, qa_with_current_collision, relation, motion
    )
    checks = {
        "hard_gates": bool(hard_gates)
        and all(value is True for value in hard_gates.values()),
        "frames_320": qa["video"].get("frames") == 320,
        "audio_240000": (
            qa["audio"].get("samples_per_channel") == 240_000
        ),
        "frame_tick_mapping": (
            qa["mapping"].get("success_rate") == 1
            and qa["mapping"].get("mapped_frames") == 320
            and qa["mapping"].get("episode_tick_first") == 64
            and qa["mapping"].get("episode_tick_last") == 383
        ),
        "states_384": live.get("state_rows") == 384,
        "actions_384": live.get("action_rows") == 384,
        "model_actions_320": (
            activity["model_action_rows"] == capture.OUTPUT_TICKS
        ),
        "model_action_frame_tick_exact": (
            activity["model_action_frame_tick_exact"] is True
        ),
        "model_action_schema": (
            model_action_metrics.get("schema_version")
            == capture.MODEL_ACTION_SCHEMA_VERSION
        ),
        "model_action_full_qa": all(
            qa.get("gates", {}).get(name) is True
            for name in MODEL_ACTION_GATES
        ),
        "model_action_buttons_binary": (
            activity["model_buttons_binary"] is True
        ),
        "nvidia_renderer": str(runtime.get("renderer", "")).startswith(
            "NVIDIA "
        ),
        "gametype_exact": (
            qa["mode"].get("requested_gametype")
            == qa["mode"].get("realized_gametype")
        ),
        "hud_policy": (
            hud.get("cl_hidewaypoints") == 2
            and hud.get("g_ctf_flag_waypoint") == 0
            and hud.get("hud_panel_modicons") == 0
        ),
        "route": qa["route"].get("passed") is True,
        "enemy_path": (
            qa["enemy_policy"]["whole_path_trace"].get("passed")
            is True
        ),
        "training_forbidden": (
            qa.get("training_admitted") is False
            and record.get("training_admitted") is False
            and record.get("formal_collection_authorized") is False
        ),
        "expected_audio_nonzero": (
            not bool(plan.get("expects_sound"))
            or int(qa["audio"].get("peak_s16", 0)) > 0
        ),
        "declared_fire_observed": (
            not bool(acceptance.get("fire_required"))
            or int(qa["events"].get("fire_count", 0)) > 0
        ),
        "declared_reload_observed": (
            not expected_reload
            or actual_reload
        ),
        "current_collision_policy": (
            collision["collision_policy_passed"] is True
        ),
    }
    scheduler = plan.get("scheduler_targets") or {}
    return {
        "episode_id": plan["episode_id"],
        "source_episode_id": plan.get("source_episode_id"),
        "map": plan.get("map"),
        "gametype": plan.get("gametype"),
        "dataset_role": plan.get("dataset_role"),
        "primary_bucket": plan.get("primary_bucket"),
        "category": plan.get("category"),
        "weapon": plan.get("weapon"),
        "weapon_action": design.get("weapon_action"),
        "locomotion_direction": design.get(
            "locomotion_direction"
        ),
        "movement_profile": design.get("movement_profile"),
        "view_direction": design.get("view_direction"),
        "view_profile": design.get("view_profile"),
        "action_arity": design.get("action_arity"),
        "movement_xy_magnitude": design.get(
            "movement_xy_magnitude"
        ),
        "yaw_amplitude": design.get("yaw_amplitude"),
        "pitch_amplitude": design.get("pitch_amplitude"),
        "jump": bool(design.get("jump")),
        "enemy_present": bool(plan.get("enemy_present")),
        "fire_required": bool(
            (plan.get("acceptance") or {}).get("fire_required")
        ),
                                                                           
                                                                            
                                                                       
        "actual_fire": weapon_activity["actual_shot"],
        **weapon_activity,
        "reload_required": expected_reload,
        "actual_reload": actual_reload,
        "reload_proof": reload_proof,
        "fire_count": int(qa["events"].get("fire_count", 0)),
        "damage_count": int(qa["events"].get("damage_count", 0)),
        "collision_policy_passed": collision[
            "collision_policy_passed"
        ],
        "collision_high_confidence": collision["high_confidence"],
        "collision_blocked_ticks": collision["blocked_ticks"],
        "collision_longest_blocked_ticks": collision[
            "longest_blocked_ticks"
        ],
        "collision_contact_telemetry_present": collision[
            "contact_telemetry_present"
        ],
        "visible_collision_qualified": collision[
            "visible_collision_qualified"
        ],
        "route_present": bool(plan.get("route_request")),
        "stored_role_eligible": qa.get("role_eligible"),
        "role_eligible": role_eligible_v2,
        "target_net": scheduler.get("net_displacement_bin"),
        "actual_net": motion.get("net_displacement_bin"),
        "target_yaw": scheduler.get("yaw_range_bin"),
        "actual_yaw": motion.get("yaw_range_bin"),
        "target_pitch": scheduler.get("pitch_range_bin"),
        "actual_pitch": motion.get("pitch_range_bin"),
        "target_relation": scheduler.get("target_relation"),
        "actual_relation": relation.get("actual_target_relation"),
        "target_distance": scheduler.get("distance_bin"),
        "actual_distance": relation.get("actual_distance_bin"),
        "path_length_3d": motion.get("path_length_3d"),
        "frames": qa["video"].get("frames"),
        "audio_samples": qa["audio"].get("samples_per_channel"),
        "audio_peak_s16": qa["audio"].get("peak_s16"),
        "audio_nonzero": int(qa["audio"].get("peak_s16", 0)) > 0,
        "mapping_rate": qa["mapping"].get("success_rate"),
        "tick_first": qa["mapping"].get("episode_tick_first"),
        "tick_last": qa["mapping"].get("episode_tick_last"),
        "states": live.get("state_rows"),
        "actions": live.get("action_rows"),
        "model_action_schema_version": model_action_metrics.get(
            "schema_version"
        ),
        "renderer": runtime.get("renderer"),
        "x264_threads": runtime.get("x264_threads"),
        "x264_cpuset": runtime.get("x264_cpuset"),
        "x264_cpuset_cpu_count": runtime.get(
            "x264_cpuset_cpu_count"
        ),
        "encode_concurrency": runtime.get("encode_concurrency"),
        "sdl_concurrency": runtime.get("sdl_concurrency"),
        "qa_pass": all(checks.values()),
        "failed_checks": ",".join(
            name for name, passed in checks.items() if not passed
        ),
        "episode_path": str(episode_path),
        **activity,
        "_checks": checks,
    }


def realized_distributions(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    fields = (
        "dataset_role",
        "primary_bucket",
        "category",
        "enemy_present",
        "gametype",
        "map",
        "weapon",
        "weapon_action",
        "locomotion_direction",
        "movement_profile",
        "view_direction",
        "view_profile",
        "action_arity",
        "jump",
        "fire_required",
        "actual_fire",
        "actual_weapon_activation",
        "actual_shot",
        "actual_melee",
        "weapon_action_semantics",
        "collision_policy_passed",
        "collision_high_confidence",
        "collision_contact_telemetry_present",
        "visible_collision_qualified",
        "reload_required",
        "actual_reload",
        "audio_nonzero",
        "route_present",
        "role_eligible",
        "actual_net",
        "actual_yaw",
        "actual_pitch",
        "actual_relation",
        "actual_distance",
        "renderer",
        "x264_threads",
        "x264_cpuset",
        "x264_cpuset_cpu_count",
        "encode_concurrency",
        "sdl_concurrency",
    )
    return {
        field: counter(rows, lambda row, key=field: row.get(key))
        for field in fields
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = [
        {key: value for key, value in row.items() if key != "_checks"}
        for row in rows
    ]
    fields = list(clean[0]) if clean else ["episode_id"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean)


def thumbnails(
    rows: list[dict[str, Any]], review_root: Path
) -> list[dict[str, str]]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return [{"episode_id": "*", "error": "ffmpeg_not_found"}]
    target = review_root / "thumbnails"
    target.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    for row in rows:
        output = target / f"{row['episode_id']}.jpg"
        if output.is_file():
            continue
        video = Path(row["episode_path"]) / "video.mkv"
        completed = subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(video),
                "-vf",
                "fps=3/5,scale=320:180,tile=3x1:padding=2",
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            errors.append(
                {
                    "episode_id": row["episode_id"],
                    "error": completed.stderr[-1000:],
                }
            )
    return errors


def markdown_table(
    name: str,
    planned: dict[str, int],
    realized: dict[str, int],
) -> str:
    keys = sorted(
        set(planned) | set(realized),
        key=lambda key: (-planned.get(key, 0), key),
    )
    lines = [
        f"### {name}",
        "",
        "| 值 | 计划 | 实际接受 |",
        "|---|---:|---:|",
    ]
    for key in keys:
        lines.append(
            f"| `{key}` | {planned.get(key, 0)} | "
            f"{realized.get(key, 0)} |"
        )
    return "\n".join(lines)


def write_html(
    path: Path,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    cards: list[str] = []
    for row in rows:
        episode_id = html.escape(row["episode_id"])
        classes = [
            "card",
            "qa-pass" if row["qa_pass"] else "qa-fail",
            "enemy" if row["enemy_present"] else "no-enemy",
            "shooting" if row["actual_fire"] else "no-shot",
            "melee" if row["actual_melee"] else "no-melee",
            (
                "collision-clear"
                if row["collision_policy_passed"]
                else "collision-reject"
            ),
            "reload" if row["actual_reload"] else "no-reload",
        ]
        cards.append(
            f"""
<article class="{' '.join(classes)}" data-mode="{html.escape(str(row['gametype']))}">
 <img loading="lazy" src="thumbnails/{episode_id}.jpg" alt="{episode_id}">
 <h3>{episode_id} · {html.escape(str(row['map']))} / {html.escape(str(row['gametype']))}</h3>
 <p>{html.escape(str(row['dataset_role']))} · {html.escape(str(row['primary_bucket']))} · {html.escape(str(row['weapon']))}</p>
 <p>action {html.escape(str(row['locomotion_direction']))} / {html.escape(str(row['movement_profile']))};
 view {html.escape(str(row['view_direction']))} / {html.escape(str(row['view_profile']))};
 weapon {html.escape(str(row['weapon_action']))}</p>
 <p>declared move |xy| {html.escape(str(row['movement_xy_magnitude']))};
 yaw/pitch amplitude {html.escape(str(row['yaw_amplitude']))}/{html.escape(str(row['pitch_amplitude']))} deg;
 realized model-axis |max| {html.escape(str(row['model_axis_abs_max']))}</p>
 <p>motion {html.escape(str(row['target_net']))} → {html.escape(str(row['actual_net']))};
 yaw {html.escape(str(row['target_yaw']))} → {html.escape(str(row['actual_yaw']))};
 pitch {html.escape(str(row['target_pitch']))} → {html.escape(str(row['actual_pitch']))}</p>
 <p>active ticks move/view {row['move_active_ticks']}/{row['view_active_ticks']};
 final 2s {row['move_tail_active_ticks']}/{row['view_tail_active_ticks']};
 reload {str(row['actual_reload']).lower()};
 model rows/tick {row['model_action_rows']}/{str(row['model_action_frame_tick_exact']).lower()}</p>
 <p>relation {html.escape(str(row['target_relation']))} → {html.escape(str(row['actual_relation']))};
 shot/melee/activation-events {row['shot_count']}/{row['melee_count']}/{row['fire_count']};
 semantic {html.escape(str(row['weapon_action_semantics']))};
 eligible {str(row['role_eligible']).lower()};
 QA {'PASS' if row['qa_pass'] else html.escape(row['failed_checks'])}</p>
 <p>collision policy {str(row['collision_policy_passed']).lower()};
 blocked/longest ticks {row['collision_blocked_ticks']}/{row['collision_longest_blocked_ticks']};
 authoritative contact telemetry {str(row['collision_contact_telemetry_present']).lower()}</p>
 <a href="../episodes/{episode_id}/video.mkv">打开 5 秒视频</a>
</article>"""
        )
    status = summary["status"]
    path.write_text(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>H200 Stage-1 非训练数据分布</title>
<style>
body{{font-family:system-ui,sans-serif;background:#10131a;color:#e9edf5;margin:24px}}
a{{color:#82b7ff}} .summary{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}}
.metric{{background:#1b2230;padding:12px 16px;border-radius:10px}}
button{{margin:0 6px 12px 0;padding:7px 10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}}
.card{{background:#1b2230;border:1px solid #364258;border-radius:10px;padding:10px}}
.card.qa-fail{{border-color:#ff6b6b}} .card img{{width:100%;height:auto;background:#080a0e}}
.card h3{{font-size:15px;margin:8px 0}} .card p{{font-size:12px;color:#bdc7d8;margin:5px 0}}
.hidden{{display:none}}
</style></head><body>
<h1>H200 Stage-1 非训练数据分布</h1>
<p>生成时间 {html.escape(summary['generated_utc'])}；全部 formal_collection_authorized=false、training_admitted=false。</p>
<div class="summary">
 <div class="metric">计划 <b>{status['planned']}</b></div>
 <div class="metric">接受 <b>{status['accepted']}</b></div>
 <div class="metric">QA PASS <b>{status['qa_pass']}</b></div>
 <div class="metric">动作 320/tick QA <b>{status['model_action_qa_pass']}</b></div>
 <div class="metric">含敌人 <b>{status['enemy']}</b></div>
 <div class="metric">实际开枪 <b>{status['actual_shot']}</b></div>
 <div class="metric">近战 <b>{status['actual_melee']}</b></div>
 <div class="metric">武器动作 <b>{status['actual_weapon_activation']}</b></div>
 <div class="metric">碰撞规则通过 <b>{status['collision_policy_pass']}</b></div>
 <div class="metric">碰撞硬拒绝 <b>{status['collision_policy_reject']}</b></div>
 <div class="metric">实际换弹 <b>{status['actual_reload']}</b></div>
 <div class="metric">terminal reject <b>{status['terminal_rejects']}</b></div>
</div>
<div>
 <button onclick="filterCards('all')">全部</button>
 <button onclick="filterCards('enemy')">含敌人</button>
 <button onclick="filterCards('no-enemy')">无敌人</button>
 <button onclick="filterCards('shooting')">实际开枪</button>
 <button onclick="filterCards('melee')">近战</button>
 <button onclick="filterCards('collision-reject')">碰撞硬拒绝</button>
 <button onclick="filterCards('reload')">实际换弹</button>
 <button onclick="filterCards('dm')">DM</button>
 <button onclick="filterCards('ctf')">CTF</button>
 <button onclick="filterCards('rc')">Race</button>
</div>
<div class="grid">{''.join(cards)}</div>
<script>
function filterCards(kind) {{
 document.querySelectorAll('.card').forEach(c => {{
  const show=kind==='all'||c.classList.contains(kind)||c.dataset.mode===kind;
  c.classList.toggle('hidden',!show);
 }});
}}
</script></body></html>""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--make-thumbnails", action="store_true")
    args = parser.parse_args()

    manifest = args.input_manifest.resolve()
    output_root = args.output_root.resolve()
    review_root = output_root / "review"
    review_root.mkdir(parents=True, exist_ok=True)
    plans = load_jsonl(manifest)
    plan_by_id = {row["episode_id"]: row for row in plans}
    shard_root = (
        output_root / "manifests/shards/shard-000-of-001"
    )
    accepted_records = load_jsonl(shard_root / "accepted.jsonl")
    accepted = {
        row["episode_id"]: row
        for row in accepted_records
        if row["episode_id"] in plan_by_id
    }
    rejects = [
        row
        for row in load_jsonl(shard_root / "rejects.jsonl")
        if row["episode_id"] in plan_by_id
    ]
    run_result_path = shard_root / "RUN_RESULT.json"
    run_result = (
        json.loads(run_result_path.read_text(encoding="utf-8"))
        if run_result_path.is_file()
        else {}
    )
    rows = [
        qa_row(plan_by_id[episode_id], record)
        for episode_id, record in sorted(accepted.items())
    ]
    terminal_ids = {
        row["episode_id"]
        for row in rejects
        if row.get("terminal") is True
    }
    missing = sorted(set(plan_by_id) - set(accepted) - terminal_ids)
    capture_wall_seconds = None
    capture_episodes_per_hour = None
    accepted_episodes_per_hour = None
    if run_result.get("started_utc") and run_result.get(
        "finished_utc"
    ):
        capture_wall_seconds = (
            datetime.fromisoformat(
                str(run_result["finished_utc"]).replace("Z", "+00:00")
            )
            - datetime.fromisoformat(
                str(run_result["started_utc"]).replace("Z", "+00:00")
            )
        ).total_seconds()
        accounted = len(rows) + len(terminal_ids)
        if capture_wall_seconds > 0:
            capture_episodes_per_hour = (
                accounted * 3600.0 / capture_wall_seconds
            )
            accepted_episodes_per_hour = (
                len(rows) * 3600.0 / capture_wall_seconds
            )
    planned = planned_distributions(plans)
    realized = realized_distributions(rows)
    reject_failure_labels: Counter[str] = Counter()
    terminal_reject_failure_labels: Counter[str] = Counter()
    retry_failure_labels: Counter[str] = Counter()
    for rejection in rejects:
        labels = rejection_failure_labels(rejection)
        reject_failure_labels.update(labels)
        (
            terminal_reject_failure_labels
            if rejection.get("terminal") is True
            else retry_failure_labels
        ).update(labels)
    check_counts: Counter[str] = Counter()
    for row in rows:
        check_counts.update(
            name
            for name, passed in row["_checks"].items()
            if passed
        )
    summary = {
        "schema_version": (
            "xonotic-h200-stage1-distribution-review-v1"
        ),
        "generated_utc": capture.utc_now(),
        "input_manifest": str(manifest),
        "input_manifest_sha256": capture.sha256_file(manifest),
        "output_root": str(output_root),
        "status": {
            "planned": len(plans),
            "accepted": len(rows),
            "qa_pass": sum(row["qa_pass"] for row in rows),
            "model_action_qa_pass": sum(
                row["_checks"]["model_actions_320"]
                and row["_checks"]["model_action_frame_tick_exact"]
                and row["_checks"]["model_action_schema"]
                and row["_checks"]["model_action_full_qa"]
                and row["_checks"]["model_action_buttons_binary"]
                for row in rows
            ),
            "role_eligible": sum(
                row["role_eligible"] is True for row in rows
            ),
            "enemy": sum(row["enemy_present"] for row in rows),
            "no_enemy": sum(not row["enemy_present"] for row in rows),
            "actual_fire": sum(row["actual_fire"] for row in rows),
            "actual_shot": sum(row["actual_shot"] for row in rows),
            "actual_melee": sum(row["actual_melee"] for row in rows),
            "actual_weapon_activation": sum(
                row["actual_weapon_activation"] for row in rows
            ),
            "collision_policy_pass": sum(
                row["collision_policy_passed"] for row in rows
            ),
            "collision_policy_reject": (
                terminal_reject_failure_labels[
                    "player_collision_policy"
                ]
            ),
            "actual_reload": sum(
                row["actual_reload"] for row in rows
            ),
            "terminal_rejects": len(terminal_ids),
            "reject_attempts": len(rejects),
            "missing": len(missing),
            "missing_episode_ids": missing,
            "duplicate_accepted_ids": (
                len(accepted_records)
                - len({row["episode_id"] for row in accepted_records})
            ),
            "capture_wall_seconds": capture_wall_seconds,
            "capture_episodes_per_hour": capture_episodes_per_hour,
            "accepted_episodes_per_hour": (
                accepted_episodes_per_hour
            ),
        },
        "run_result": run_result,
        "qa_check_pass_counts": dict(sorted(check_counts.items())),
        "planned_distribution": planned,
        "realized_distribution": realized,
        "continuous_action_stats": {
            "planned_movement_xy_magnitude": numeric_stats(
                [
                    (row.get("action_design") or {}).get(
                        "movement_xy_magnitude"
                    )
                    for row in plans
                ]
            ),
            "planned_yaw_amplitude_degrees": numeric_stats(
                [
                    (row.get("action_design") or {}).get(
                        "yaw_amplitude"
                    )
                    for row in plans
                ]
            ),
            "planned_pitch_amplitude_degrees": numeric_stats(
                [
                    (row.get("action_design") or {}).get(
                        "pitch_amplitude"
                    )
                    for row in plans
                ]
            ),
            "realized_episode_model_axis_abs_max": numeric_stats(
                [row.get("model_axis_abs_max") for row in rows]
            ),
            "realized_episode_left_stick_l2_max": numeric_stats(
                [row.get("model_left_l2_max") for row in rows]
            ),
            "realized_episode_right_stick_l2_max": numeric_stats(
                [row.get("model_right_l2_max") for row in rows]
            ),
        },
        "reject_reasons": counter(
            rejects, lambda row: row.get("reason")
        ),
        "terminal_reject_reasons": counter(
            [
                row for row in rejects
                if row.get("terminal") is True
            ],
            lambda row: row.get("reason"),
        ),
        "retry_reasons": counter(
            [
                row for row in rejects
                if row.get("terminal") is not True
            ],
            lambda row: row.get("reason"),
        ),
        "reject_failure_labels": dict(
            sorted(
                reject_failure_labels.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "terminal_reject_failure_labels": dict(
            sorted(
                terminal_reject_failure_labels.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "retry_failure_labels": dict(
            sorted(
                retry_failure_labels.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "qa_failures": [
            {
                "episode_id": row["episode_id"],
                "failed_checks": row["failed_checks"],
            }
            for row in rows
            if not row["qa_pass"]
        ],
    }
    thumbnail_errors = (
        thumbnails(rows, review_root)
        if args.make_thumbnails
        else []
    )
    summary["thumbnail_errors"] = thumbnail_errors

    json_path = review_root / "DISTRIBUTION_REVIEW.json"
    csv_path = review_root / "DISTRIBUTION_REVIEW_EPISODES.csv"
    rejects_path = review_root / "DISTRIBUTION_REVIEW_REJECTS.csv"
    md_path = review_root / "DISTRIBUTION_REVIEW_REPORT.md"
    html_path = review_root / "index.html"
    json_path.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(csv_path, rows)
    reject_rows = [
        {
            "episode_id": rejection["episode_id"],
            "source_episode_id": plan_by_id.get(
                rejection["episode_id"], {}
            ).get("source_episode_id"),
            "map": plan_by_id.get(rejection["episode_id"], {}).get(
                "map"
            ),
            "gametype": plan_by_id.get(
                rejection["episode_id"], {}
            ).get("gametype"),
            "dataset_role": plan_by_id.get(
                rejection["episode_id"], {}
            ).get("dataset_role"),
            "primary_bucket": plan_by_id.get(
                rejection["episode_id"], {}
            ).get("primary_bucket"),
            "reason": rejection.get("reason"),
            "retryable": rejection.get("retryable"),
            "terminal": rejection.get("terminal"),
            "attempt_id": rejection.get("attempt_id"),
            "detail": rejection.get("detail"),
            "diagnostic_path": rejection.get("diagnostic_path"),
        }
        for rejection in rejects
    ]
    write_csv(rejects_path, reject_rows)
    throughput_summary = (
        f"{capture_episodes_per_hour:.2f} / "
        f"{accepted_episodes_per_hour:.2f} episode/hour"
        if (
            capture_episodes_per_hour is not None
            and accepted_episodes_per_hour is not None
        )
        else "not available"
    )
    lines = [
        "# H200 Stage-1 非训练数据分布检查",
        "",
        f"- 计划 / 接受 / QA PASS：`{len(plans)} / "
        f"{len(rows)} / {summary['status']['qa_pass']}`",
        f"- LTX-2 动作 320 行 / tick / schema / binary 全通过："
        f"`{summary['status']['model_action_qa_pass']} / {len(rows)}`",
        f"- 含敌人 / 无敌人 / 实际开枪 / 近战 / 武器动作："
        f"`{summary['status']['enemy']} / "
        f"{summary['status']['no_enemy']} / "
        f"{summary['status']['actual_shot']} / "
        f"{summary['status']['actual_melee']} / "
        f"{summary['status']['actual_weapon_activation']}`",
        f"- 当前碰撞规则通过 / 硬拒绝："
        f"`{summary['status']['collision_policy_pass']} / "
        f"{summary['status']['collision_policy_reject']}`",
        f"- 实际成功换弹：`{summary['status']['actual_reload']}`",
        f"- terminal reject / missing："
        f"`{len(terminal_ids)} / {len(missing)}`",
        f"- QA 检查通过计数："
        f"`{json.dumps(summary['qa_check_pass_counts'], ensure_ascii=False)}`",
        f"- reject 原因："
        f"`{json.dumps(summary['reject_reasons'], ensure_ascii=False)}`",
        f"- terminal reject 原因："
        f"`{json.dumps(summary['terminal_reject_reasons'], ensure_ascii=False)}`",
        f"- 可恢复 retry 原因："
        f"`{json.dumps(summary['retry_reasons'], ensure_ascii=False)}`",
        f"- reject gate："
        f"`{json.dumps(summary['reject_failure_labels'], ensure_ascii=False)}`",
        f"- 候选处理 / 净接受吞吐："
        f"`{throughput_summary}`",
        f"- 连续动作统计："
        f"`{json.dumps(summary['continuous_action_stats'], ensure_ascii=False)}`",
        "",
        "## 分布对比",
        "",
    ]
    for dimension in (
        "dataset_role",
        "primary_bucket",
        "category",
        "enemy_present",
        "gametype",
        "map",
        "weapon",
        "weapon_action",
        "locomotion_direction",
        "movement_profile",
        "view_direction",
        "view_profile",
        "action_arity",
        "jump",
        "fire_required",
        "reload_required",
        "route_present",
        "net_displacement_bin",
        "yaw_range_bin",
        "pitch_range_bin",
        "target_relation",
        "distance_bin",
    ):
        realized_name = {
            "net_displacement_bin": "actual_net",
            "yaw_range_bin": "actual_yaw",
            "pitch_range_bin": "actual_pitch",
            "target_relation": "actual_relation",
            "distance_bin": "actual_distance",
        }.get(dimension, dimension)
        lines.extend(
            [
                markdown_table(
                    dimension,
                    planned.get(dimension, {}),
                    realized.get(realized_name, {}),
                ),
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    write_html(html_path, summary, rows)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "outputs": [
                    str(json_path),
                    str(csv_path),
                    str(rejects_path),
                    str(md_path),
                    str(html_path),
                ],
                "thumbnail_errors": thumbnail_errors,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not thumbnail_errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
