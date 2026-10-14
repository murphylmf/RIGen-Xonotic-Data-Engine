                      
"""Independently verify the immutable 100-episode Pilot deliverable."""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = capture.ROOT
ACCEPTED = ROOT / "manifests/accepted.jsonl"
REJECTS = ROOT / "manifests/rejects.jsonl"
OUTPUT = ROOT / "qa/final_pilot_verification.json"
SOURCE_COMMIT = "52aae0d6706aedf882f2a98e7b0da6f56110523c"
FORMAL_FILES = {
    "episode.json",
    "video.mkv",
    "actions.parquet",
    "states.parquet",
    "events.parquet",
    "frames.parquet",
    "audio_events.parquet",
    "qa.json",
}
RAW_FILES = {
    "demo.dem",
    "raw_capture.avi",
    "actions_requested.csv",
    "actions_engine.csv",
    "server.jsonl",
    "frames_engine.csv",
    "audio_events_engine.csv",
    "server_console.log",
    "client_live_console.log",
    "client_render_console.log",
    "ffmpeg_encode.log",
}
HUD_POLICY = capture.HUD_POLICY_LINE


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_hashes(
    root: Path, expected: dict[str, str], label: str
) -> tuple[int, int]:
    count = 0
    size = 0
    for relative, digest in sorted(expected.items()):
        path = root / relative
        require(path.is_file(), f"{label}: missing {path}")
        actual = capture.sha256_file(path)
        require(actual == digest, f"{label}: SHA256 mismatch {path}")
        count += 1
        size += path.stat().st_size
    return count, size


def verify_reload(events: pd.DataFrame, episode_id: str) -> dict[str, Any]:
    starts = events[events["event"] == "reload_start"]
    completes = events[events["event"] == "reload_complete"]
    require(len(starts) == 1, f"{episode_id}: reload_start count {len(starts)}")
    require(
        len(completes) == 1,
        f"{episode_id}: reload_complete count {len(completes)}",
    )
    start = starts.iloc[0]
    complete = completes.iloc[0]
    require(
        int(complete["parent_event_id"]) == int(start["event_id"]),
        f"{episode_id}: reload parent mismatch",
    )
    require(float(complete["success"]) == 1.0, f"{episode_id}: reload failed")
    require(
        float(complete["post_clip"]) > float(complete["pre_clip"]),
        f"{episode_id}: clip did not increase",
    )
    require(
        float(complete["post_reserve"]) < float(complete["pre_reserve"]),
        f"{episode_id}: reserve did not decrease",
    )
    return {
        "start_tick": int(start["server_tick"]),
        "complete_tick": int(complete["server_tick"]),
        "pre_clip": float(complete["pre_clip"]),
        "post_clip": float(complete["post_clip"]),
        "pre_reserve": float(complete["pre_reserve"]),
        "post_reserve": float(complete["post_reserve"]),
    }


def verify_episode(row: dict[str, Any]) -> dict[str, Any]:
    episode_id = str(row["episode_id"])
    episode = Path(row["episode_path"])
    raw = Path(row["raw_path"])
    require(episode == ROOT / "pilot/episodes" / episode_id, f"{episode_id}: path")
    require(raw == ROOT / "pilot/raw" / episode_id, f"{episode_id}: raw path")
    require(episode.is_dir(), f"{episode_id}: episode directory missing")
    require(raw.is_dir(), f"{episode_id}: raw directory missing")
    require(
        set(row["artifacts_sha256"]) == FORMAL_FILES,
        f"{episode_id}: formal file set mismatch",
    )
    require(
        set(row["raw_artifacts_sha256"]) == RAW_FILES,
        f"{episode_id}: raw file set mismatch",
    )
    formal_hash_count, formal_bytes = verify_hashes(
        episode, row["artifacts_sha256"], episode_id
    )
    raw_hash_count, raw_bytes = verify_hashes(
        raw, row["raw_artifacts_sha256"], episode_id
    )

    metadata = json.loads((episode / "episode.json").read_text())
    qa = json.loads((episode / "qa.json").read_text())
    require(metadata["episode_id"] == episode_id, f"{episode_id}: metadata ID")
    require(metadata["split"] == "pilot", f"{episode_id}: metadata split")
    require(metadata["source_commit"] == SOURCE_COMMIT, f"{episode_id}: commit")
    require(row["split"] == "pilot", f"{episode_id}: manifest split")
    require(int(metadata["seed"]) == int(row["seed"]), f"{episode_id}: seed")
    require(qa["accepted"], f"{episode_id}: QA not accepted")
    failed_gates = [name for name, value in qa["gates"].items() if not value]
    require(not failed_gates, f"{episode_id}: failed gates {failed_gates}")
    require(
        qa["telemetry"]["authoritative_sha256"]
        == row["authoritative_sha256"],
        f"{episode_id}: authoritative hash mismatch",
    )
    require(
        capture.is_nvidia_hardware_renderer(
            qa["runtime"]["renderer"]
        ),
        f"{episode_id}: renderer {qa['runtime']['renderer']}",
    )
    render_console = (raw / "client_render_console.log").read_text(
        errors="replace"
    )
    require(HUD_POLICY in render_console, f"{episode_id}: HUD policy missing")
    require("llvmpipe" not in render_console.lower(), f"{episode_id}: llvmpipe")
    action_header = (raw / "actions_requested.csv").open(
        encoding="utf-8"
    ).readline().strip()
    require(
        action_header == f"#seed,{row['seed']}",
        f"{episode_id}: action seed header {action_header!r}",
    )

    actions = pd.read_parquet(episode / "actions.parquet")
    states = pd.read_parquet(episode / "states.parquet")
    events = pd.read_parquet(episode / "events.parquet")
    frames = pd.read_parquet(episode / "frames.parquet")
    audio_events = pd.read_parquet(episode / "audio_events.parquet")
    require(len(actions) == 384, f"{episode_id}: action rows {len(actions)}")
    require(len(states) == 384, f"{episode_id}: state rows {len(states)}")
    require(len(frames) == 320, f"{episode_id}: frame rows {len(frames)}")
    require(
        set(actions["namespace"]) == {"engine_usercmd"},
        f"{episode_id}: action namespace",
    )
    require(
        set(states["namespace"]) == {"canonical_engine_state"},
        f"{episode_id}: state namespace",
    )
    require(
        set(frames["namespace"]) == {"camera_render_state"},
        f"{episode_id}: frame namespace",
    )
    if len(audio_events):
        require(
            set(audio_events["namespace"]) == {"engine_audio_mixer_event"},
            f"{episode_id}: audio namespace",
        )
    if len(events):
        require(
            set(events["namespace"]) == {"authoritative_engine_event"},
            f"{episode_id}: event namespace",
        )

    video = episode / "video.mkv"
    probe = capture.ffprobe_json(video, count_frames=True)
    frame_count = capture.count_video_frames(probe)
    audio_samples = int(capture.decode_audio_s16(video).shape[0])
    contract = capture.encoded_contract(probe, video)
    require(frame_count == 320, f"{episode_id}: video frames {frame_count}")
    require(
        audio_samples == 240_000,
        f"{episode_id}: audio samples {audio_samples}",
    )
    require(all(contract.values()), f"{episode_id}: encode contract {contract}")

    reload_result: dict[str, Any] | None = None
    if row["target_bin"] == "machinegun_reload":
        reload_result = verify_reload(events, episode_id)

    return {
        "episode_id": episode_id,
        "formal_hash_count": formal_hash_count,
        "raw_hash_count": raw_hash_count,
        "formal_bytes": formal_bytes,
        "raw_bytes": raw_bytes,
        "video_frames": frame_count,
        "audio_samples_per_channel": audio_samples,
        "mapping_success_rate": float(qa["mapping"]["success_rate"]),
        "max_audio_onset_error_ms": float(
            qa["audio"]["max_onset_error_ms"]
        ),
        "event_linked": int(qa["events"]["linked"]),
        "event_link_required": int(qa["events"]["link_required"]),
        "resource_changes": int(qa["telemetry"]["resource_changes"]),
        "resource_changes_explained": int(
            qa["telemetry"]["resource_changes_explained"]
        ),
        "reload": reload_result,
    }


def verify_reject(row: dict[str, Any]) -> dict[str, Any]:
    attempt_id = str(row["attempt_id"])
    preserved = Path(row["preserved_path"])
    require(
        preserved == ROOT / "pilot/rejected" / attempt_id,
        f"{attempt_id}: reject path",
    )
    count, size = verify_hashes(
        preserved, row["preserved_artifacts_sha256"], attempt_id
    )
    return {
        "attempt_id": attempt_id,
        "episode_id": row["episode_id"],
        "reason": row["reason"],
        "detail": row["detail"],
        "hash_count": count,
        "bytes": size,
    }


def main() -> int:
    capture.require_conda()
    require(not OUTPUT.exists(), f"refusing to overwrite {OUTPUT}")
    started = time.monotonic()
    accepted = sorted(
        capture.load_jsonl(ACCEPTED), key=lambda row: row["episode_id"]
    )
    rejected = capture.load_jsonl(REJECTS)
    expected_ids = [f"pilot_{index:03d}" for index in range(1, 101)]
    require(len(accepted) == 100, f"accepted rows {len(accepted)}")
    require(
        [row["episode_id"] for row in accepted] == expected_ids,
        "accepted ID sequence mismatch",
    )
    require(
        Counter(row["target_bin"] for row in accepted)
        == Counter(capture.TARGET_COUNTS),
        "target distribution mismatch",
    )
    require(
        len({tuple(row["player_origin"]) for row in accepted}) == 100,
        "player origins are not unique",
    )
    require(
        len({tuple(row["enemy_origin"]) for row in accepted}) == 100,
        "enemy origins are not unique",
    )
    require(
        len(
            {
                (
                    tuple(row["player_origin"]),
                    tuple(row["enemy_origin"]),
                )
                for row in accepted
            }
        )
        == 100,
        "player/enemy position pairs are not unique",
    )
    require(
        len({str(row["anchor_id"]) for row in accepted}) == 12,
        "anchor-pair count mismatch",
    )

    episode_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(verify_episode, row): row for row in accepted}
        for completed, future in enumerate(as_completed(futures), 1):
            result = future.result()
            episode_results.append(result)
            print(
                f"verified {completed}/100 {result['episode_id']}",
                flush=True,
            )
    episode_results.sort(key=lambda row: row["episode_id"])

    reject_results = [verify_reject(row) for row in rejected]
    reloads = [row["reload"] for row in episode_results if row["reload"]]
    require(len(reloads) == 10, f"successful reload rows {len(reloads)}")
    total_linked = sum(row["event_linked"] for row in episode_results)
    total_required = sum(
        row["event_link_required"] for row in episode_results
    )
    total_resource_changes = sum(
        row["resource_changes"] for row in episode_results
    )
    total_resource_explained = sum(
        row["resource_changes_explained"] for row in episode_results
    )
    require(total_linked == total_required, "aggregate event linkage mismatch")
    require(
        total_resource_changes == total_resource_explained,
        "aggregate resource explanation mismatch",
    )

    value = {
        "schema_version": "xonotic-final-pilot-verification-v1",
        "created_utc": capture.utc_now(),
        "result": "pass",
        "wall_seconds": time.monotonic() - started,
        "source_commit": SOURCE_COMMIT,
        "accepted": 100,
        "rejected_attempts": len(rejected),
        "target_distribution": dict(
            sorted(Counter(row["target_bin"] for row in accepted).items())
        ),
        "actual_outcome_distribution": dict(
            sorted(
                Counter(
                    row["actual_outcome_bin"] for row in accepted
                ).items()
            )
        ),
        "hit_rate_bin_distribution": dict(
            sorted(Counter(row["hit_rate_bin"] for row in accepted).items())
        ),
        "position_diversity": {
            "anchor_pairs": 12,
            "unique_player_origins": 100,
            "unique_enemy_origins": 100,
            "unique_player_enemy_pairs": 100,
        },
        "formal_hashes_verified": sum(
            row["formal_hash_count"] for row in episode_results
        ),
        "raw_hashes_verified": sum(
            row["raw_hash_count"] for row in episode_results
        ),
        "formal_bytes_verified": sum(
            row["formal_bytes"] for row in episode_results
        ),
        "raw_bytes_verified": sum(
            row["raw_bytes"] for row in episode_results
        ),
        "video": {
            "frames_total": sum(
                row["video_frames"] for row in episode_results
            ),
            "frames_per_episode": 320,
            "all_encode_contracts_pass": True,
        },
        "audio": {
            "samples_per_channel_total": sum(
                row["audio_samples_per_channel"]
                for row in episode_results
            ),
            "samples_per_channel_per_episode": 240_000,
            "max_onset_error_ms": max(
                row["max_audio_onset_error_ms"]
                for row in episode_results
            ),
        },
        "mapping_success_rate": {
            "min": min(
                row["mapping_success_rate"] for row in episode_results
            ),
            "mean": mean(
                row["mapping_success_rate"] for row in episode_results
            ),
            "max": max(
                row["mapping_success_rate"] for row in episode_results
            ),
        },
        "event_linkage": {
            "linked": total_linked,
            "required": total_required,
            "rate": total_linked / total_required if total_required else 1.0,
        },
        "resource_changes": {
            "explained": total_resource_explained,
            "total": total_resource_changes,
        },
        "successful_machinegun_reloads": len(reloads),
        "reload_ranges": {
            "pre_clip": sorted({row["pre_clip"] for row in reloads}),
            "post_clip": sorted({row["post_clip"] for row in reloads}),
            "pre_reserve": sorted({row["pre_reserve"] for row in reloads}),
            "post_reserve": sorted({row["post_reserve"] for row in reloads}),
        },
        "hud": {
            "damage_text": False,
            "minimal_hud_log_gates": 100,
        },
        "namespaces": {
            "actions": "engine_usercmd",
            "states": "canonical_engine_state",
            "events": "authoritative_engine_event",
            "frames": "camera_render_state",
            "audio_events": "engine_audio_mixer_event",
        },
        "rejects": reject_results,
        "episode_results": episode_results,
    }
    require(
        value["video"]["frames_total"] == 32_000,
        "aggregate video frame count mismatch",
    )
    require(
        value["audio"]["samples_per_channel_total"] == 24_000_000,
        "aggregate audio sample count mismatch",
    )
    OUTPUT.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"verification={OUTPUT}")
    print("result=pass accepted=100")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
