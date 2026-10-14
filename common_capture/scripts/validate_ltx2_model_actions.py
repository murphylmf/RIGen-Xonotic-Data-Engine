                      
"""Validate packaged Xonotic actions through the actual LTX-2 loader."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
import torch


SCHEMA_VERSION = "ltx2-crossfps-xonotic-v1"
BUTTON_COLUMNS = (
    "south",
    "east",
    "west",
    "north",
    "left_shoulder",
    "right_shoulder",
    "left_trigger",
    "right_trigger",
)
MODEL_GATES = (
    "model_action_rows_exact",
    "model_action_ltx2_schema",
    "model_action_frame_alignment",
    "model_action_continuous_range",
    "model_action_engine_roundtrip",
    "model_action_buttons_binary",
)
ENGINE_SCALE = np.asarray([400.0, 400.0, 12.0, 12.0])
ROUNDTRIP_TOLERANCE = 1e-3


def load_rows(path: Path) -> list[dict[str, Any]]:
    return pq.read_table(path).to_pylist()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_episode(
    episode: Path,
    loader: Any,
    phase_strategy: Any,
) -> dict[str, Any]:
    model_path = episode / "model_actions.parquet"
    frames_path = episode / "frames.parquet"
    actions_path = episode / "actions.parquet"
    qa_path = episode / "qa.json"
    required = (model_path, frames_path, actions_path, qa_path)
    if not all(path.is_file() for path in required):
        return {
            "episode_id": episode.name,
            "passed": False,
            "failures": [
                f"missing:{path.name}" for path in required if not path.is_file()
            ],
        }

    model_rows = load_rows(model_path)
    frame_rows = load_rows(frames_path)
    action_rows = load_rows(actions_path)
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    indices = torch.arange(len(model_rows), dtype=torch.int64)
    actions, joystick, buttons = loader._load_crossfps_actions(
        {
            "action_path": str(model_path),
            "sample_id": episode.name,
        },
        indices,
    )
    phase_windows = []
    for start in range(8):
        window_joystick = joystick[start : start + 313].unsqueeze(0)
        window_buttons = buttons[start : start + 313].unsqueeze(0)
        phase_outputs = phase_strategy._prepare_action_tokens(
            {
                "action_joystick": window_joystick,
                "action_buttons": window_buttons,
            },
            latent_frames=40,
            height=1,
            width=1,
            batch_size=1,
            device=torch.device("cpu"),
            dtype=torch.float32,
        )
        phase_windows.append(
            [
                None if value is None else list(value.shape)
                for value in phase_outputs
            ]
        )

    source_by_tick = {
        int(row["action_tick"]): row for row in action_rows
    }
    ticks = np.asarray(
        [int(row["source_action_tick"]) for row in model_rows],
        dtype=np.int64,
    )
    frame_ticks = np.asarray(
        [int(row["episode_server_tick"]) for row in frame_rows],
        dtype=np.int64,
    )
    source = [source_by_tick.get(int(tick)) for tick in ticks]
    source_complete = all(row is not None for row in source)
    roundtrip_error = math.inf
    button_source_match = False
    if source_complete:
        source_engine = np.asarray(
            [
                [
                    row["desired_forward"],
                    row["desired_strafe"],
                    row["desired_yaw_delta"],
                    row["desired_pitch_delta"],
                ]
                for row in source
            ],
            dtype=np.float64,
        )
        loaded = joystick.detach().cpu().numpy().astype(np.float64)
        decoded_engine = np.column_stack(
            (
                -loaded[:, 1] * ENGINE_SCALE[0],
                loaded[:, 0] * ENGINE_SCALE[1],
                -loaded[:, 2] * ENGINE_SCALE[2],
                loaded[:, 3] * ENGINE_SCALE[3],
            )
        )
        roundtrip_error = float(
            np.max(
                np.abs(decoded_engine - source_engine),
                initial=0.0,
            )
        )
        expected_buttons = np.asarray(
            [
                [
                    row["desired_jump"],
                    0,
                    row["desired_reload"],
                    0,
                    0,
                    0,
                    row["desired_secondary"],
                    row["desired_primary"],
                ]
                for row in source
            ],
            dtype=np.float32,
        )
        button_source_match = bool(
            np.array_equal(
                buttons.detach().cpu().numpy(), expected_buttons
            )
        )

    joystick_numpy = joystick.detach().cpu().numpy()
    buttons_numpy = buttons.detach().cpu().numpy()
    checks = {
        "rows_320": len(model_rows) == len(frame_rows) == 320,
        "ltx_loader_shape": (
            tuple(actions.shape) == (320, 12)
            and tuple(joystick.shape) == (320, 4)
            and tuple(buttons.shape) == (320, 8)
        ),
        "phase_aware_all_313_frame_windows": all(
            shapes
            == [[1, 40, 32], [1, 313, 9], [1, 313, 8]]
            for shapes in phase_windows
        ),
        "schema_version": all(
            row.get("schema_version") == SCHEMA_VERSION
            for row in model_rows
        ),
        "frame_tick_exact": (
            len(ticks) == len(frame_ticks)
            and np.array_equal(ticks, frame_ticks)
        ),
        "joystick_finite_range": (
            bool(np.isfinite(joystick_numpy).all())
            and bool((joystick_numpy >= -1.0).all())
            and bool((joystick_numpy <= 1.0).all())
        ),
        "buttons_binary": bool(
            np.isin(buttons_numpy, (0.0, 1.0)).all()
        ),
        "source_ticks_complete": source_complete,
        "engine_roundtrip": (
            roundtrip_error <= ROUNDTRIP_TOLERANCE
        ),
        "button_source_match": button_source_match,
        "packaged_qa_gates": all(
            qa.get("gates", {}).get(name) is True
            for name in MODEL_GATES
        ),
    }
    return {
        "episode_id": episode.name,
        "passed": all(checks.values()),
        "checks": checks,
        "rows": len(model_rows),
        "actions_shape": list(actions.shape),
        "phase_aware_313_frame_windows_checked": len(phase_windows),
        "joystick_min": float(joystick_numpy.min()),
        "joystick_max": float(joystick_numpy.max()),
        "button_active_frames": int(
            (buttons_numpy != 0).any(axis=1).sum()
        ),
        "button_sums": {
            name: int(buttons_numpy[:, index].sum())
            for index, name in enumerate(BUTTON_COLUMNS)
        },
        "engine_roundtrip_max_error": roundtrip_error,
    }


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(
            value,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def full_loader_smoke(
    dataset_type: Any,
    action_binding_config_type: Any,
    episodes: list[Path],
    limit: int,
) -> list[dict[str, Any]]:
    selected = episodes[: max(0, min(limit, len(episodes)))]
    if not selected:
        return []
    entries = [
        {
            "sample_id": episode.name,
            "video_path": str(episode / "video.mkv"),
            "audio_path": str(episode / "video.mkv"),
            "action_path": str(
                episode / "model_actions.parquet"
            ),
            "prompt_text": "first-person Xonotic gameplay",
            "game_id": "xonotic",
            "source_fps": 64.0,
            "source_frames": 320,
            "source_duration": 5.0,
            "video_source_fps": 64.0,
            "button_meanings": {
                "A": {"meaning": "jump", "aliases": []},
                "X": {"meaning": "reload", "aliases": []},
                "LT": {
                    "meaning": "secondary fire",
                    "aliases": [],
                },
                "RT": {
                    "meaning": "primary fire",
                    "aliases": [],
                },
            },
        }
        for episode in selected
    ]
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(
        prefix="xonotic-ltx2-full-loader-"
    ) as temporary:
        manifest = Path(temporary) / "manifest.jsonl"
        manifest.write_text(
            "".join(
                json.dumps(entry, sort_keys=True) + "\n"
                for entry in entries
            ),
            encoding="utf-8",
        )
        dataset = dataset_type(
            data_root=selected[0].parent,
            manifest_path=manifest,
            target_width=320,
            target_height=180,
            target_num_frames=313,
            target_fps=64.0,
            target_audio_sample_rate=48_000,
            random_temporal_crop=False,
            require_audio=True,
            action_binding_config=action_binding_config_type(
                enabled=True,
                schema_path=None,
                use_scene_prompt=True,
                use_control_prompt=True,
            ),
            action_binding_training=False,
        )
        for index, episode in enumerate(selected):
            sample = dataset[index]
            shapes = {
                name: list(sample[name].shape)
                for name in (
                    "video_pixels",
                    "audio_waveform",
                    "actions",
                    "action_joystick",
                    "action_buttons",
                )
            }
            checks = {
                "video_313x3x180x320": (
                    shapes["video_pixels"] == [313, 3, 180, 320]
                ),
                "audio_2x234750": (
                    shapes["audio_waveform"] == [2, 234_750]
                ),
                "actions_313x12": (
                    shapes["actions"] == [313, 12]
                ),
                "joystick_313x4": (
                    shapes["action_joystick"] == [313, 4]
                ),
                "buttons_313x8": (
                    shapes["action_buttons"] == [313, 8]
                ),
                "fps_64": float(sample["fps"]) == 64.0,
                "audio_rate_48000": (
                    int(sample["audio_sample_rate"]) == 48_000
                ),
                "canonical_channel_order": (
                    sample["crossfps_action_channels"]
                    == [
                        "j_left_x",
                        "j_left_y",
                        "j_right_x",
                        "j_right_y",
                        "A",
                        "B",
                        "X",
                        "Y",
                        "LB",
                        "RB",
                        "LT",
                        "RT",
                    ]
                ),
                "button_meanings_exact": (
                    sample.get("button_meaning_texts")
                    == {
                        "A": "jump",
                        "X": "reload",
                        "LT": "secondary fire",
                        "RT": "primary fire",
                    }
                ),
                "control_binding_text_exact": (
                    sample.get("control_binding_text")
                    == (
                        "Controls: A means jump. X means reload. "
                        "LT means secondary fire. RT means primary fire."
                    )
                ),
                "game_id_xonotic": sample.get("scene_id") == "xonotic",
            }
            results.append(
                {
                    "episode_id": episode.name,
                    "passed": all(checks.values()),
                    "checks": checks,
                    "shapes": shapes,
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--ltx2-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--full-loader-smoke",
        type=int,
        default=0,
        help=(
            "Decode this many episodes through the complete LTX-2 "
            "CrossFPS video/audio/action dataset path using a 313-frame "
            "64-fps model-compatible crop."
        ),
    )
    args = parser.parse_args()

    package = (
        args.ltx2_root.resolve()
        / "packages/ltx-trainer/src"
    )
    if not package.is_dir():
        raise SystemExit(f"LTX-2 trainer package missing: {package}")
    sys.path.insert(0, str(package))
    from ltx_trainer.datasets_online import (                 
        CrossFPSAudioActionDataset,
    )
    from ltx_trainer.config import (                 
        ActionBindingConfig,
    )
    from ltx_trainer.training_strategies.phase_aware import (                 
        PhaseAwareStrategy,
    )

    output_root = args.output_root.resolve()
    episodes_root = output_root / "episodes"
    episodes = sorted(
        path for path in episodes_root.iterdir() if path.is_dir()
    )
    if not episodes:
        raise SystemExit(f"No packaged episodes under {episodes_root}")
    loader = CrossFPSAudioActionDataset.__new__(
        CrossFPSAudioActionDataset
    )
    phase_strategy = PhaseAwareStrategy.__new__(PhaseAwareStrategy)
    phase_strategy._action_binding_config = None
    rows = [
        validate_episode(episode, loader, phase_strategy)
        for episode in episodes
    ]
    full_loader_results = full_loader_smoke(
        CrossFPSAudioActionDataset,
        ActionBindingConfig,
        episodes,
        args.full_loader_smoke,
    )
    all_rows_passed = all(row["passed"] for row in rows)
    all_full_loader_passed = all(
        row["passed"] for row in full_loader_results
    )
    report = {
        "schema_version": "xonotic-ltx2-action-validation-v1",
        "output_root": str(output_root),
        "ltx2_root": str(args.ltx2_root.resolve()),
        "ltx2_definition_sha256": {
            str(path.relative_to(args.ltx2_root.resolve())): (
                sha256_file(path)
            )
            for path in (
                package / "ltx_trainer/datasets_online.py",
                package / "ltx_trainer/action_binding.py",
                package
                / "ltx_trainer/training_strategies/phase_aware.py",
            )
        },
        "episodes": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "full_loader_smoke": full_loader_results,
        "all_passed": (
            all_rows_passed and all_full_loader_passed
        ),
        "results": rows,
    }
    report_path = (
        args.report.resolve()
        if args.report
        else output_root
        / "review/LTX2_MODEL_ACTION_VALIDATION.json"
    )
    atomic_json(report_path, report)
    print(
        json.dumps(
            {
                "episodes": report["episodes"],
                "passed": report["passed"],
                "failed": report["failed"],
                "full_loader_smoke": len(full_loader_results),
                "full_loader_smoke_passed": sum(
                    row["passed"] for row in full_loader_results
                ),
                "report": str(report_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
