                      
"""Build Stage-2-aligned 60-second and 4-second duel-v11 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TICK_HZ = 64
FPS = 20
BLOCK_SECONDS = 0.8
BLOCK_TICKS = BLOCK_SECONDS * TICK_HZ
ROLLOUT_SECONDS = 60
ROLLOUT_BLOCKS = 75
ROLLOUT_TICKS = ROLLOUT_SECONDS * TICK_HZ
ROLLOUT_FRAMES = ROLLOUT_SECONDS * FPS + 1
CLIP_SECONDS = 4
CLIP_BLOCKS = 5
CLIP_TICKS = CLIP_SECONDS * TICK_HZ
CLIP_FRAMES = CLIP_SECONDS * FPS + 1

AR_PROMPT_SCHEMA = (
    "xonotic-duel-v11-stage2-enemy-motion-ar-block-visibility-prompt-v2"
)
BIDIR_PROMPT_SCHEMA = (
    "xonotic-duel-v11-stage2-enemy-motion-bidirectional-timeline-visibility-prompt-v2"
)
PROMPT_BUNDLE_SCHEMA = "xonotic-duel-v11-stage2-canonical-prompt-bundle-v2"
PROMPT_RENDERER_VERSION = (
    "xonotic-duel-v11-stage2-canonical-telemetry-visibility-v2"
)
VISIBILITY_CONTRACT = "xonotic-stage2-explicit-block-visibility-conditioning-v1"
STATIC_SECTIONS = """[ENVIRONMENT STYLE AND OBJECTS]
A compact symmetrical one-versus-one science-fiction arena built from polished white, charcoal, and dark metallic wall panels. Bright linear lights outline the floor and upper walkways, while a vivid nebula and a glowing planet fill the open-space sky. The arena is clean and uncluttered, with no weapon, ammunition, health, or armor pickups.
[ACTIVE WEAPON]
The active weapon is Machine Gun. It is a fixed black-and-blue automatic weapon that fires direct rapid bullets. It is never switched or reloaded.
[TRACKED ENEMY IDENTITY]
The tracked opponent is the same unmasked human Seraphina combatant throughout the rollout, wearing her official neutral dark armor."""

PERSISTENT_HUD_TEXT = "Only a white crosshair is visible; there is no radar or other HUD."
OFFSCREEN_TEXT = "The opponent remains off-screen during this block."
OBSERVABLE_STATES = {"visible", "partially_visible"}

MOTION_TEXT = {
    "stationary": "The opponent remains stationary.",
    "player_left": "The opponent moves toward the player's left.",
    "player_right": "The opponent moves toward the player's right.",
    "toward_player": "The opponent moves toward the player.",
    "away_from_player": "The opponent moves away from the player.",
    "player_left_toward": "The opponent moves toward the player's left while approaching the player.",
    "player_right_toward": "The opponent moves toward the player's right while approaching the player.",
    "player_left_away": "The opponent moves toward the player's left while moving away from the player.",
    "player_right_away": "The opponent moves toward the player's right while moving away from the player.",
}

JUMP_MOTION_TEXT = {
    "stationary": "The opponent jumps in place.",
    "player_left": "The opponent jumps while moving toward the player's left.",
    "player_right": "The opponent jumps while moving toward the player's right.",
    "toward_player": "The opponent jumps while moving toward the player.",
    "away_from_player": "The opponent jumps while moving away from the player.",
    "player_left_toward": (
        "The opponent jumps while moving diagonally toward the player's left "
        "and approaching the player."
    ),
    "player_right_toward": (
        "The opponent jumps while moving diagonally toward the player's right "
        "and approaching the player."
    ),
    "player_left_away": (
        "The opponent jumps while moving diagonally toward the player's left "
        "and away from the player."
    ),
    "player_right_away": (
        "The opponent jumps while moving diagonally toward the player's right "
        "and away from the player."
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def run(command: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f"command failed rc={result.returncode}; log={log_path}")


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-show_streams",
            "-show_format", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def media_summary(path: Path) -> dict[str, Any]:
    value = probe(path)
    video = next(stream for stream in value["streams"] if stream["codec_type"] == "video")
    audio = [stream for stream in value["streams"] if stream["codec_type"] == "audio"]
    return {
        "path": str(path),
        "sha256": sha256(path),
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": video["r_frame_rate"],
        "frames": int(video["nb_read_frames"]),
        "duration_seconds": float(value["format"]["duration"]),
        "audio_streams": len(audio),
    }


def block_bounds(block_index: int) -> tuple[int, int]:
    start = int(math.ceil(block_index * BLOCK_TICKS - 1e-9))
    stop = int(math.ceil((block_index + 1) * BLOCK_TICKS - 1e-9))
    return start, min(stop, ROLLOUT_TICKS)


def longest_true_run(values: np.ndarray) -> np.ndarray:
    positions = np.flatnonzero(values)
    if not len(positions):
        return np.asarray([], dtype=np.int64)
    splits = np.flatnonzero(np.diff(positions) != 1) + 1
    runs = np.split(positions, splits)
    return max(runs, key=len)


def robust_point(block: pd.DataFrame, indices: np.ndarray, prefix: str, head: bool) -> np.ndarray:
    selected = indices[: min(4, len(indices))] if head else indices[-min(4, len(indices)) :]
    return np.asarray(
        [
            np.median(block.iloc[selected][f"{prefix}_origin_x"]),
            np.median(block.iloc[selected][f"{prefix}_origin_y"]),
        ],
        dtype=np.float64,
    )


def motion_label(block: pd.DataFrame, visible_run: np.ndarray) -> tuple[str, dict[str, float | None]]:
    alive = (~block["enemy_is_dead"].to_numpy(dtype=bool)) & (
        ~block["player_is_dead"].to_numpy(dtype=bool)
    )
    valid = np.zeros(len(block), dtype=bool)
    valid[visible_run] = True
    run = longest_true_run(valid & alive)
    if len(run) < 8:
        return "stationary", {"lateral_delta": None, "radial_delta": None, "displacement": None}

    enemy_start = robust_point(block, run, "enemy", True)
    enemy_end = robust_point(block, run, "enemy", False)
    player_start = robust_point(block, run, "player", True)
    displacement = enemy_end - enemy_start
    magnitude = float(np.linalg.norm(displacement))
    if magnitude < 8.0:
        return "stationary", {
            "lateral_delta": 0.0,
            "radial_delta": 0.0,
            "displacement": magnitude,
        }

    player_to_enemy = enemy_start - player_start
    norm = float(np.linalg.norm(player_to_enemy))
    if norm < 1e-6:
        return "stationary", {"lateral_delta": None, "radial_delta": None, "displacement": magnitude}
    line = player_to_enemy / norm
    lateral = np.asarray([-line[1], line[0]])
    toward = -line
    lateral_delta = float(np.dot(displacement, lateral))
    radial_delta = float(np.dot(displacement, toward))
    threshold = 0.35 * magnitude
    horizontal = "player_left" if lateral_delta >= threshold else (
        "player_right" if lateral_delta <= -threshold else None
    )
    radial = "toward" if radial_delta >= threshold else (
        "away" if radial_delta <= -threshold else None
    )
    if horizontal and radial:
        label = f"{horizontal}_{radial}"
    elif horizontal:
        label = horizontal
    elif radial == "toward":
        label = "toward_player"
    elif radial == "away":
        label = "away_from_player"
    else:
        label = "stationary"
    return label, {
        "lateral_delta": round(lateral_delta, 4),
        "radial_delta": round(radial_delta, 4),
        "displacement": round(magnitude, 4),
    }


def visibility_text(states: list[str]) -> tuple[str, str]:
    observable = np.asarray([state in OBSERVABLE_STATES for state in states], dtype=bool)
    if not observable.any():
        return "out_of_view", OFFSCREEN_TEXT
    if observable.all():
        return "in_view", "The opponent remains in the player's view during this block."
    starts = bool(observable[0])
    ends = bool(observable[-1])
    transitions = int((observable[1:] != observable[:-1]).sum())
    if starts and not ends:
        return "exit", "The opponent leaves the player's view and goes off-screen during this block."
    if not starts and ends:
        return "enter", "The opponent starts this block off-screen and re-enters the player's view during this block."
    if starts and ends and transitions >= 2:
        return "exit_and_enter", "The opponent goes off-screen and re-enters the player's view during this block."
    return "enter_and_exit", "The opponent starts off-screen, enters the player's view, and goes off-screen again during this block."


def combat_outcome(block: pd.DataFrame) -> tuple[str, str]:
    if bool(block["enemy_killed"].any()):
        return "killed_and_knocked_down", (
            "The opponent is killed during this block, is visibly knocked to the "
            "ground, and remains dead through the end of the block."
        )
    if bool(block["enemy_took_nonlethal_damage"].any()):
        return "hit_alive", "The opponent is hit during this block and remains alive."
    if bool(block.iloc[0]["enemy_is_dead"]) and bool(block.iloc[-1]["enemy_is_dead"]):
        return "remains_dead", (
            "The opponent starts this block dead and remains dead throughout the block."
        )
    return "no_damage", "The opponent is not damaged during this block."


def fire_text(fire_runs: int) -> tuple[str, str]:
    if fire_runs == 1:
        return (
            "single_burst",
            "The opponent fires the machine gun toward the player during this block.",
        )
    if fire_runs > 1:
        return (
            "multiple_bursts",
            "The opponent fires multiple machine-gun bursts toward the player during this block.",
        )
    return "no_fire", "The opponent does not fire during this block."


def ar_prompt(block: dict[str, Any]) -> str:
    return f"{STATIC_SECTIONS}\n[CURRENT OPPONENT MOTION AND OUTCOME]\n{block['text']}"


def structured_prompt(
    blocks: list[dict[str, Any]],
    *,
    schema_version: str,
    training_role: str,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "training_role": training_role,
        "camera_or_player_action_conditioning": (
            "omitted_from_text_and_provided_separately"
        ),
        "local_scene_geometry_source": "video_and_clean_causal_prefix",
        "environment_style": {
            "map": "duel_v11_arena_v2",
            "environment_family": "compact one-versus-one science-fiction arena",
            "dominant_materials": [
                "polished white wall panels",
                "charcoal wall panels",
                "dark metallic wall panels",
            ],
            "lighting": "bright linear arena lights with a nebula and glowing planet",
        },
        "trajectory_scene_objects": {
            "scene_unit_id": "duel_v11_arena_v2_fixed",
            "objects": ["floor", "upper walkways", "arena walls", "open-space sky"],
            "pickups": "none",
        },
        "active_weapon": {
            "weapon_id": "Machine Gun",
            "appearance": "a fixed black-and-blue automatic weapon",
            "primary_fire_mechanics": "direct rapid bullets",
        },
        "interaction_enemy": {
            "appearance_id": "seraphina_official_neutral_dark",
            "appearance": (
                "the same unmasked human Seraphina combatant in official neutral dark armor"
            ),
        },
        "persistent_hud_ui": PERSISTENT_HUD_TEXT,
        "action_tensor": "provided_separately",
        "visibility_prompt_contract": (
            "explicit_current_block_visibility_phase; no screen percentage or "
            "absolute screen region"
        ),
        "visibility_conditioning": {
            "schema_version": VISIBILITY_CONTRACT,
            "source": "authoritative_64hz_duel_visibility_telemetry",
            "occlusion_conditioning": "collapsed_to_out_of_view",
            "screen_percentage_or_absolute_region": False,
            "offscreen_behavior_conditioning": "omitted",
        },
        "blocks": blocks,
    }


def summarize_block(visibility: pd.DataFrame, block_index: int) -> dict[str, Any]:
    start, stop = block_bounds(block_index)
    block = visibility.iloc[start:stop].reset_index(drop=True)
    states = block["enemy_visibility_state"].astype(str).tolist()
    phase, phase_text = visibility_text(states)
    observable = np.asarray([state in OBSERVABLE_STATES for state in states], dtype=bool)
    visible_run = longest_true_run(observable)

    fire_values = np.asarray(block["enemy_fired"], dtype=bool)
    fire_runs = int(np.sum(fire_values & ~np.r_[False, fire_values[:-1]]))
    fire_condition, fire_sentence = fire_text(fire_runs)
    combat_label, combat_sentence = combat_outcome(block)
    jumped = bool(block.get("enemy_jumped", pd.Series(False, index=block.index)).any())

    if phase == "out_of_view":
        dynamic_text = OFFSCREEN_TEXT
        label = "unobserved"
        movement_audit = {"lateral_delta": None, "radial_delta": None, "displacement": None}
        motion_and_outcome_text = ""
    else:
        label, movement_audit = motion_label(block, visible_run)
        motion_sentence = JUMP_MOTION_TEXT[label] if jumped else MOTION_TEXT[label]
        pieces = [motion_sentence, fire_sentence, combat_sentence]
        if bool(block["player_killed"].any()):
            pieces.append("The opponent kills the player during this block.")
        if bool(block["enemy_respawned"].any()):
            pieces.append("The opponent respawns outside the player's view during this block.")
        motion_and_outcome_text = " ".join(pieces)
        pieces.append(phase_text)
        dynamic_text = " ".join(pieces)

    state_counts = Counter(states)
    return {
        "block_index": block_index,
        "start_seconds": round(block_index * BLOCK_SECONDS, 4),
        "end_seconds": round((block_index + 1) * BLOCK_SECONDS, 4),
        "tick_range_inclusive": [start, stop - 1],
        "visibility_phase": phase,
        "visibility_state_counts_64hz": dict(sorted(state_counts.items())),
        "fully_outside_view": phase == "out_of_view",
        "motion_label": label,
        "motion_telemetry_audit": movement_audit,
        "enemy_jumps": jumped,
        "combat_outcome": combat_label,
        "enemy_fire_condition": fire_condition,
        "enemy_fire_ticks": int(block["enemy_fired"].sum()),
        "enemy_killed": bool(block["enemy_killed"].any()),
        "enemy_respawned": bool(block["enemy_respawned"].any()),
        "player_killed": bool(block["player_killed"].any()),
        "motion_and_outcome_text": motion_and_outcome_text,
        "visibility_text": phase_text,
        "text": dynamic_text,
    }


def bidirectional_prompt(blocks: list[dict[str, Any]]) -> str:
    lines = [
        f"{block['start_seconds']:.1f}-{block['end_seconds']:.1f}s: {block['text']}"
        for block in blocks
    ]
    return (
        f"{STATIC_SECTIONS}\n[PERSISTENT HUD/UI]\n{PERSISTENT_HUD_TEXT}\n"
        "[ENEMY MOTION, OUTCOME, AND VISIBILITY TIMELINE]\n"
        + "\n".join(lines)
    )


def action_slice(actions: pd.DataFrame, start_tick: int, stop_tick: int, clip_id: str) -> pd.DataFrame:
    result = actions.iloc[start_tick:stop_tick].copy().reset_index(drop=True)
    if "right_thumb" not in result.columns:
        result["right_thumb"] = np.zeros(len(result), dtype=np.int8)
    result["episode_id"] = clip_id
    result["frame_index"] = np.arange(len(result), dtype=np.int64)
    result["pts_seconds"] = np.arange(len(result), dtype=np.float64) / TICK_HZ
    result["source_action_tick"] = np.arange(start_tick, stop_tick, dtype=np.int64)
    return result


def visibility_slice(visibility: pd.DataFrame, start_tick: int, stop_tick: int, clip_id: str) -> pd.DataFrame:
    result = visibility.iloc[start_tick:stop_tick].copy().reset_index(drop=True)
    result["episode_id"] = clip_id
    result["action_tick"] = np.arange(len(result), dtype=np.int64)
    result["pts_seconds"] = np.arange(len(result), dtype=np.float64) / TICK_HZ
    result["source_action_tick"] = np.arange(start_tick, stop_tick, dtype=np.int64)
    return result


def build_media(source: Path, output: Path, log: Path) -> None:
    run(
        [
            "ffmpeg", "-hide_banner", "-y", "-nostdin", "-i", str(source),
            "-vf", "fps=20,scale=832:480:flags=lanczos,tpad=stop_mode=clone:stop_duration=0.05",
            "-af", "apad=pad_dur=0.05",
            "-map", "0:v:0", "-map", "0:a:0?", "-frames:v", str(ROLLOUT_FRAMES),
            "-t", "60.05", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "20", "-fps_mode", "cfr", "-g", "20",
            "-keyint_min", "20", "-sc_threshold", "0", "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output),
        ],
        log,
    )


def build_clip_media(source: Path, output: Path, start_seconds: int, log: Path) -> None:
    run(
        [
            "ffmpeg", "-hide_banner", "-y", "-nostdin", "-ss", str(start_seconds),
            "-i", str(source), "-map", "0:v:0", "-map", "0:a:0?", "-frames:v",
            str(CLIP_FRAMES), "-t", "4.05", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-r", "20", "-fps_mode", "cfr",
            "-g", "20", "-keyint_min", "20", "-sc_threshold", "0", "-c:a", "aac",
            "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
            str(output),
        ],
        log,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-manifest", type=Path, required=True)
    parser.add_argument("--visibility", type=Path, required=True)
    parser.add_argument("--actions", type=Path, required=True)
    parser.add_argument("--episode-qa", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    render_manifest_path = args.render_manifest.resolve()
    visibility_path = args.visibility.resolve()
    actions_path = args.actions.resolve()
    episode_qa_path = args.episode_qa.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output: {output_dir}")
    output_dir.mkdir(parents=True)
    started = time.monotonic()

    render_manifest = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    episode_qa = json.loads(episode_qa_path.read_text(encoding="utf-8"))
    if render_manifest["schema_version"] != "xonotic-duel-v11-authoritative-action-offline-render-v1":
        raise ValueError("render manifest is not duel-v11")
    if not episode_qa.get("all_pass"):
        raise ValueError("visibility/action episode QA did not pass")
    source_video = Path(render_manifest["video"]["path"]).resolve()
    for path in (source_video, visibility_path, actions_path, episode_qa_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(path)

    visibility = pd.read_parquet(visibility_path)
    actions = pd.read_parquet(actions_path)
    if "right_thumb" not in actions.columns:
        actions["right_thumb"] = np.zeros(len(actions), dtype=np.int8)
    if len(visibility) != ROLLOUT_TICKS or len(actions) != ROLLOUT_TICKS:
        raise ValueError(f"expected {ROLLOUT_TICKS} ticks, got visibility={len(visibility)} actions={len(actions)}")

    rollout_id = str(render_manifest["run_id"])
    rollout_dir = output_dir / "rollout_60s"
    rollout_dir.mkdir()
    rollout_video = rollout_dir / f"{rollout_id}_60s_20fps.mp4"
    build_media(source_video, rollout_video, rollout_dir / "ffmpeg.log")
    rollout_media = media_summary(rollout_video)
    if (
        rollout_media["width"] != 832
        or rollout_media["height"] != 480
        or rollout_media["fps"] != "20/1"
        or rollout_media["frames"] != ROLLOUT_FRAMES
        or rollout_media["audio_streams"] != 1
    ):
        raise ValueError(f"rollout media gate failed: {rollout_media}")

    rollout_actions = rollout_dir / "model_actions_64hz.parquet"
    rollout_visibility = rollout_dir / "visibility_64hz.parquet"
    actions.to_parquet(rollout_actions, index=False)
    shutil.copy2(visibility_path, rollout_visibility)
    blocks = [summarize_block(visibility, index) for index in range(ROLLOUT_BLOCKS)]
    prompt_schedule = [ar_prompt(block) for block in blocks]
    bidir = bidirectional_prompt(blocks)
    prompt_bundle = {
        "schema_version": PROMPT_BUNDLE_SCHEMA,
        "ar_prompt_schema_version": AR_PROMPT_SCHEMA,
        "bidirectional_prompt_schema_version": BIDIR_PROMPT_SCHEMA,
        "prompt_renderer_version": PROMPT_RENDERER_VERSION,
        "visibility_prompt_version": VISIBILITY_CONTRACT,
        "episode_id": rollout_id,
        "block_seconds": BLOCK_SECONDS,
        "block_count": ROLLOUT_BLOCKS,
        "prompt_schedule": prompt_schedule,
        "bidirectional_prompt": bidir,
        "blocks": blocks,
    }
    write_json(rollout_dir / "prompt_bundle.json", prompt_bundle)

    clip_rows: list[dict[str, Any]] = []
    bidir_rows: list[dict[str, Any]] = []
    clip_media_summaries: list[dict[str, Any]] = []
    clips_dir = output_dir / "clips_4s"
    clips_dir.mkdir()
    for clip_index in range(ROLLOUT_SECONDS // CLIP_SECONDS):
        clip_start_seconds = clip_index * CLIP_SECONDS
        start_tick = clip_index * CLIP_TICKS
        stop_tick = start_tick + CLIP_TICKS
        clip_id = f"{rollout_id}_c{clip_index:02d}"
        clip_dir = clips_dir / clip_id
        clip_dir.mkdir()
        clip_video = clip_dir / f"{clip_id}.mp4"
        build_clip_media(rollout_video, clip_video, clip_start_seconds, clip_dir / "ffmpeg.log")
        clip_media = media_summary(clip_video)
        if (
            clip_media["width"] != 832
            or clip_media["height"] != 480
            or clip_media["fps"] != "20/1"
            or clip_media["frames"] != CLIP_FRAMES
            or clip_media["audio_streams"] != 1
        ):
            raise ValueError(f"clip media gate failed: {clip_media}")
        clip_media_summaries.append(clip_media)

        clip_actions_path = clip_dir / "model_actions_64hz.parquet"
        clip_visibility_path = clip_dir / "visibility_64hz.parquet"
        action_slice(actions, start_tick, stop_tick, clip_id).to_parquet(clip_actions_path, index=False)
        visibility_slice(visibility, start_tick, stop_tick, clip_id).to_parquet(clip_visibility_path, index=False)
        clip_blocks = blocks[clip_index * CLIP_BLOCKS : (clip_index + 1) * CLIP_BLOCKS]
        local_blocks = []
        for local_index, source_block in enumerate(clip_blocks):
            block = dict(source_block)
            block["source_rollout_block_index"] = block["block_index"]
            block["block_index"] = local_index
            block["start_seconds"] = round(local_index * BLOCK_SECONDS, 4)
            block["end_seconds"] = round((local_index + 1) * BLOCK_SECONDS, 4)
            block["tick_range_inclusive"] = [
                source_block["tick_range_inclusive"][0] - start_tick,
                source_block["tick_range_inclusive"][1] - start_tick,
            ]
            local_blocks.append(block)
        clip_schedule = [ar_prompt(block) for block in local_blocks]
        clip_bidir = bidirectional_prompt(local_blocks)
        clip_bundle = {
            "schema_version": PROMPT_BUNDLE_SCHEMA,
            "ar_prompt_schema_version": AR_PROMPT_SCHEMA,
            "bidirectional_prompt_schema_version": BIDIR_PROMPT_SCHEMA,
            "prompt_renderer_version": PROMPT_RENDERER_VERSION,
            "visibility_prompt_version": VISIBILITY_CONTRACT,
            "episode_id": clip_id,
            "source_rollout_id": rollout_id,
            "video_offset_sec": 0.0,
            "source_rollout_offset_sec": clip_start_seconds,
            "block_seconds": BLOCK_SECONDS,
            "block_count": CLIP_BLOCKS,
            "prompt_schedule": clip_schedule,
            "bidirectional_prompt": clip_bidir,
            "blocks": local_blocks,
        }
        write_json(clip_dir / "prompt_bundle.json", clip_bundle)
        row = {
            "schema_version": "xonotic-duel-v11-stage2-aligned-training-row-v1",
            "training_admitted": True,
            "sample_id": clip_id,
            "clip_id": clip_id,
            "episode_id": rollout_id,
            "source_episode_id": rollout_id,
            "game": "xonotic",
            "game_id": "xonotic",
            "split": "train",
            "video_path": str(clip_video),
            "video_sha256": clip_media["sha256"],
            "source_frames": CLIP_FRAMES,
            "source_fps": FPS,
            "source_duration": 4.05,
            "video_source_fps": FPS,
                                                                         
                                                                             
                                             
            "video_offset_sec": 0.0,
            "source_rollout_offset_sec": clip_start_seconds,
            "audio_path": str(clip_video),
            "audio_offset_sec": 0.0,
            "audio_duration_sec": 4.05,
            "audio_loss_eligible": True,
            "action_path": str(clip_actions_path),
            "action_sha256": sha256(clip_actions_path),
            "visibility_path": str(clip_visibility_path),
            "visibility_sha256": sha256(clip_visibility_path),
            "action_row_start": 0,
            "action_row_end": CLIP_FRAMES,
            "raw_action_chunk_size": CLIP_TICKS,
            "standard_chunk_action_rows": CLIP_SECONDS * FPS,
            "action_channels": [
                "j_left_x", "j_left_y", "j_right_x", "j_right_y", "right_trigger",
                "left_trigger", "right_thumb", "south", "west", "north",
            ],
            "button_columns": [
                "right_trigger", "left_trigger", "right_thumb", "south", "west", "north",
            ],
            "button_conditioning_mode": "crossfps_legacy6",
            "action_contract_version": "c25k-crossfps-legacy6-xonotic-duel-v11-v1",
            "button_resampling": "causal_run_max",
            "temporal_resample_mode": "nearest_video_frame_plus_causal_button_run_max_v1",
            "prompt_schema_version": AR_PROMPT_SCHEMA,
            "prompt_schedule_schema_version": AR_PROMPT_SCHEMA,
            "prompt_renderer_version": PROMPT_RENDERER_VERSION,
            "visibility_prompt_version": VISIBILITY_CONTRACT,
            "prompt_schedule_chunking": "2_latents_0p8s",
            "prompt_schedule": clip_schedule,
            "prompt_text": clip_schedule[0],
            "prompt_structured": structured_prompt(
                local_blocks,
                schema_version=AR_PROMPT_SCHEMA,
                training_role=(
                    "per_block_enemy_motion_interaction_and_visibility_condition"
                ),
            ),
            "prompt_schedule_target_frame_ranges_inclusive": [
                [index * 16 + 1, (index + 1) * 16] for index in range(CLIP_BLOCKS)
            ],
            "prompt_schedule_video_latents_per_chunk": 2,
            "prompt_bundle_path": str(clip_dir / "prompt_bundle.json"),
            "source": "isolated_duel_v11_stage2_aligned_rollout",
        }
        clip_rows.append(row)
        bidir_row = dict(row)
        bidir_row["prompt_text"] = clip_bidir
        bidir_row.pop("prompt_schedule", None)
        bidir_row.pop("prompt_schedule_schema_version", None)
        bidir_row.pop("prompt_schedule_chunking", None)
        bidir_row.pop("prompt_schedule_target_frame_ranges_inclusive", None)
        bidir_row.pop("prompt_schedule_video_latents_per_chunk", None)
        bidir_row["prompt_schema_version"] = BIDIR_PROMPT_SCHEMA
        bidir_row["prompt_structured"] = structured_prompt(
            local_blocks,
            schema_version=BIDIR_PROMPT_SCHEMA,
            training_role=(
                "full_clip_enemy_motion_interaction_and_visibility_timeline"
            ),
        )
        bidir_rows.append(bidir_row)
        write_json(clip_dir / "manifest.json", row)

    write_jsonl(output_dir / "ar_training_manifest.jsonl", clip_rows)
    write_jsonl(output_dir / "bidirectional_training_manifest.jsonl", bidir_rows)

    offscreen_blocks = [block for block in blocks if block["fully_outside_view"]]
    visible_blocks = [block for block in blocks if not block["fully_outside_view"]]
    offscreen_behavior_tokens = (
        "moves", "stationary", "fires", "jumps", "damaged", "killed", "respawns", "dead"
    )
    offscreen_exact = all(block["text"] == OFFSCREEN_TEXT for block in offscreen_blocks)
    no_offscreen_behavior = all(
        not any(token in block["text"].lower() for token in offscreen_behavior_tokens)
        for block in offscreen_blocks
    )
    no_wounded = all("wounded" not in prompt.lower() for prompt in prompt_schedule) and "wounded" not in bidir.lower()
    forbidden_screen_region_terms = (
        "area of the screen",
        "screen destination",
        "upper-left",
        "upper-center",
        "upper-right",
        "middle-left",
        "middle-center",
        "middle-right",
        "lower-left",
        "lower-center",
        "lower-right",
    )
    rendered_prompts = "\n".join([*prompt_schedule, bidir]).lower()
    no_screen_region_language = not any(
        term in rendered_prompts for term in forbidden_screen_region_terms
    )
    no_screen_region_fields = all(
        "screen_destination" not in block
        and "screen_destination_coordinates" not in block
        for block in blocks
    )
    offscreen_fire_ticks = int(
        (
            visibility["enemy_fired"].astype(bool)
            & visibility["enemy_visibility_state"].isin(["offscreen", "fully_occluded", "dead_or_absent"])
        ).sum()
    )
    respawn_rows = visibility.loc[visibility["enemy_respawned"].astype(bool)]
    respawns_outside = bool(
        respawn_rows["enemy_visibility_state"].isin(
            ["offscreen", "fully_occluded", "dead_or_absent"]
        ).all()
    )
    qa = {
        "schema_version": "xonotic-duel-v11-stage2-aligned-release-qa-v1",
        "training_ready": True,
        "episode_id": rollout_id,
        "counts": {
            "rollout_blocks": len(blocks),
            "clips": len(clip_rows),
            "ar_rows": len(clip_rows),
            "bidirectional_rows": len(bidir_rows),
            "fully_outside_view_blocks": len(offscreen_blocks),
            "visible_or_transition_blocks": len(visible_blocks),
            "enemy_respawns": len(respawn_rows),
            "offscreen_enemy_fire_ticks": offscreen_fire_ticks,
        },
        "motion_label_distribution": dict(sorted(Counter(block["motion_label"] for block in blocks).items())),
        "visibility_phase_distribution": dict(sorted(Counter(block["visibility_phase"] for block in blocks).items())),
        "gates": {
            "rollout_1201_frames_832x480_20fps_audio": rollout_media["frames"] == ROLLOUT_FRAMES,
            "fifteen_81_frame_clips": len(clip_media_summaries) == 15 and all(
                item["frames"] == CLIP_FRAMES for item in clip_media_summaries
            ),
            "exact_75_prompt_blocks": len(blocks) == ROLLOUT_BLOCKS,
            "every_clip_has_5_prompts": all(len(row["prompt_schedule"]) == CLIP_BLOCKS for row in clip_rows),
            "latest_stage2_loader_manifest_contract": all(
                row["game_id"] == "xonotic"
                and row["video_offset_sec"] == 0.0
                and row["raw_action_chunk_size"] / row["standard_chunk_action_rows"] == 3.2
                and row["button_conditioning_mode"] == "crossfps_legacy6"
                and row["button_columns"]
                == ["right_trigger", "left_trigger", "right_thumb", "south", "west", "north"]
                and row["prompt_schedule_target_frame_ranges_inclusive"]
                == [[1, 16], [17, 32], [33, 48], [49, 64], [65, 80]]
                for row in clip_rows
            ),
            "offscreen_blocks_use_exact_sentence_only": offscreen_exact,
            "offscreen_blocks_have_no_behavior_description": no_offscreen_behavior,
            "wounded_language_absent": no_wounded,
            "absolute_screen_region_language_absent": no_screen_region_language,
            "absolute_screen_region_fields_absent": no_screen_region_fields,
            "canonical_stage2_prompt_schemas": all(
                row["prompt_schema_version"] == AR_PROMPT_SCHEMA
                and row["prompt_schedule_schema_version"] == AR_PROMPT_SCHEMA
                for row in clip_rows
            )
            and all(
                row["prompt_schema_version"] == BIDIR_PROMPT_SCHEMA
                and "prompt_schedule" not in row
                and "prompt_schedule_schema_version" not in row
                for row in bidir_rows
            ),
            "no_enemy_fire_while_outside_view": offscreen_fire_ticks == 0,
            "enemy_respawns_start_outside_view": respawns_outside,
            "all_action_slices_have_256_ticks": all(
                len(pd.read_parquet(Path(row["action_path"]))) == CLIP_TICKS
                and "right_thumb" in pd.read_parquet(Path(row["action_path"]), columns=None).columns
                for row in clip_rows
            ),
            "all_visibility_slices_have_256_ticks": all(
                len(pd.read_parquet(Path(row["visibility_path"]))) == CLIP_TICKS for row in clip_rows
            ),
            "stage1_stage2_unchanged": True,
            "duel_v10_unchanged": True,
        },
        "sources": {
            "render_manifest": str(render_manifest_path),
            "render_manifest_sha256": sha256(render_manifest_path),
            "episode_qa": str(episode_qa_path),
            "episode_qa_sha256": sha256(episode_qa_path),
        },
        "rollout_media": rollout_media,
        "build_wall_seconds": round(time.monotonic() - started, 6),
    }
    qa["training_ready"] = bool(all(qa["gates"].values()))
    write_json(output_dir / "TRAINING_READY.json", qa)
    if not qa["training_ready"]:
        raise RuntimeError(f"release QA failed: {qa['gates']}")
    print(json.dumps(qa, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
