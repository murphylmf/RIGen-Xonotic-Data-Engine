                      
"""Independently re-decode and verify the final H200 representative set."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_capture_manifest_shard as shard_runner              
import xonotic_capture as capture              


ROOT = capture.ROOT
DATASET = ROOT / "h200_representative_final"
INPUT = ROOT / "manifests/h200_representative_final/input.jsonl"


def atomic_text(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def verify_episode(path: Path) -> dict[str, Any]:
    qa = json.loads((path / "qa.json").read_text(encoding="utf-8"))
    episode = json.loads(
        (path / "episode.json").read_text(encoding="utf-8")
    )
    video = path / "video.mkv"
    probe = capture.ffprobe_json(video, count_frames=True)
    decoded_frames = capture.count_video_frames(probe)
    decoded_audio = capture.decode_audio_s16(video)
    frames = pd.read_parquet(path / "frames.parquet")
    relations = pd.read_parquet(path / "target_relations.parquet")
    expected_ticks = np.arange(
        capture.WARMUP_TICKS,
        capture.WARMUP_TICKS + capture.OUTPUT_TICKS,
    )
    contract = capture.encoded_contract(probe, video)
    role = episode["canary_role"]
    checks = {
        "all_hard_qa": all(qa["hard_gates"].values()),
        "all_soft_qa": all(qa["soft_gates"].values()),
        "decoded_video_frames_320": (
            decoded_frames == capture.OUTPUT_TICKS
        ),
        "decoded_audio_samples_240000": (
            decoded_audio.shape == (capture.AUDIO_SAMPLES, 2)
        ),
        "samples_per_frame_750": (
            decoded_audio.shape[0]
            == decoded_frames * capture.SAMPLES_PER_FRAME
        ),
        "frame_rows_320": len(frames) == capture.OUTPUT_TICKS,
        "target_relation_rows_320": (
            len(relations) == capture.OUTPUT_TICKS
        ),
        "frame_tick_mapping_exact": np.array_equal(
            frames["episode_server_tick"].to_numpy(), expected_ticks
        ),
        "mapping_rate_one": qa["mapping"]["success_rate"] == 1.0,
        "audio_non_silent": qa["audio"]["peak_s16"] > 0,
        "audio_onset_within_2ms": (
            qa["audio"]["max_onset_error_ms"] <= 2.0
        ),
        "hud_policy": (
            qa["hud"]["cl_hidewaypoints"] == 2
            and qa["hud"]["hud_panel_modicons"] == 0
            and qa["hud"]["g_ctf_flag_waypoint"] == 0
        ),
        "gametype_exact": (
            qa["mode"]["requested_gametype"]
            == qa["mode"]["realized_gametype"]
            and not qa["mode"]["fallback_detected"]
        ),
        "renderer_hardware_nvidia": (
            capture.is_nvidia_hardware_renderer(
                qa["runtime"]["renderer"]
            )
        ),
        "source_commit": (
            episode["source_commit"]
            == shard_runner.EXPECTED_SOURCE_COMMIT
        ),
        "training_forbidden": (
            episode["formal_collection_authorized"] is False
            and episode["training_admitted"] is False
            and qa["training_admitted"] is False
        ),
        "shooting_observed": (
            role != "dm_enemy_shooting"
            or qa["events"]["fire_count"] > 0
        ),
        "enemy_role_exact": (
            bool(episode["enemy_present"])
            == bool(relations["enemy_present"].all())
        ),
        **contract,
    }
    return {
        "episode_id": episode["episode_id"],
        "canary_role": role,
        "map": episode["map"],
        "gametype": qa["mode"]["realized_gametype"],
        "enemy_present": bool(episode["enemy_present"]),
        "fire_count": qa["events"]["fire_count"],
        "damage_count": qa["events"]["damage_count"],
        "decoded_frames": decoded_frames,
        "decoded_audio_samples_per_channel": int(
            decoded_audio.shape[0]
        ),
        "mapping_rate": qa["mapping"]["success_rate"],
        "audio_peak_s16": qa["audio"]["peak_s16"],
        "audio_onset_max_ms": qa["audio"]["max_onset_error_ms"],
        "renderer": qa["runtime"]["renderer"],
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> int:
    capture.require_conda()
    rows = [
        verify_episode(path)
        for path in sorted((DATASET / "episodes").iterdir())
        if path.is_dir()
    ]
    roles = {row["canary_role"] for row in rows}
    modes = {row["gametype"] for row in rows}
    aggregate_checks = {
        "five_unique_episodes": (
            len(rows) == 5
            and len({row["episode_id"] for row in rows}) == 5
        ),
        "required_roles": roles
        == {
            "dm_no_enemy",
            "dm_enemy",
            "dm_enemy_shooting",
            "ctf_enemy",
            "race_enemy",
        },
        "required_modes": modes == {"dm", "ctf", "rc"},
        "every_episode_pass": all(row["pass"] for row in rows),
        "published_audit_pass": json.loads(
            (DATASET / "AUDIT.json").read_text(encoding="utf-8")
        )["pass"],
    }
    result = {
        "schema_version": "xonotic-h200-representative-independent-qa-v1",
        "created_utc": capture.utc_now(),
        "input_manifest": str(INPUT),
        "input_manifest_sha256": capture.sha256_file(INPUT),
        "episodes": rows,
        "aggregate": {
            "decoded_frames": sum(row["decoded_frames"] for row in rows),
            "decoded_audio_samples_per_channel": sum(
                row["decoded_audio_samples_per_channel"] for row in rows
            ),
            "roles": sorted(roles),
            "modes": sorted(modes),
            "checks": aggregate_checks,
        },
        "pass": all(aggregate_checks.values()),
    }
    atomic_text(
        DATASET / "INDEPENDENT_QA.json",
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    lines = [
        "# H200 representative independent QA",
        "",
        f"Overall: **{'PASS' if result['pass'] else 'FAIL'}**",
        "",
        "| Episode | Role | Map | Mode | Enemy | Fire | Frames | Audio samples/ch | Mapping | Audio peak | Result |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['episode_id']}` | `{row['canary_role']}` | "
            f"`{row['map']}` | `{row['gametype']}` | "
            f"{int(row['enemy_present'])} | {row['fire_count']} | "
            f"{row['decoded_frames']} | "
            f"{row['decoded_audio_samples_per_channel']} | "
            f"{row['mapping_rate']:.6f} | {row['audio_peak_s16']} | "
            f"{'PASS' if row['pass'] else 'FAIL'} |"
        )
    lines += [
        "",
        f"- Total decoded frames: {result['aggregate']['decoded_frames']}",
        "- Total decoded audio samples/channel: "
        f"{result['aggregate']['decoded_audio_samples_per_channel']}",
        "- Every episode contains 320 target-relation rows and maps exactly "
        "to authoritative ticks 64..383.",
        "- Every hard and soft QA gate passed.",
        "- All outputs remain non-training and training_admitted=false.",
    ]
    atomic_text(DATASET / "INDEPENDENT_QA.md", "\n".join(lines) + "\n")
    print(json.dumps(result["aggregate"], indent=2, sort_keys=True))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
