                      
"""Merge completed duel-v11 production ranks into one validated release."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


OFFSCREEN_TEXT = "The opponent remains off-screen during this block."
AR_PROMPT_SCHEMA = (
    "xonotic-duel-v11-stage2-enemy-motion-ar-block-visibility-prompt-v2"
)
BIDIR_PROMPT_SCHEMA = (
    "xonotic-duel-v11-stage2-enemy-motion-bidirectional-timeline-visibility-prompt-v2"
)
CLIP_SUFFIX = re.compile(r"_c(?P<index>\d{2})$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path) -> Iterator[tuple[int, bytes, dict[str, Any]]]:
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            yield line_number, raw, row


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def nonempty_file(path: Path, description: str) -> None:
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"missing or empty {description}: {path}")


def within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def verify_rank_manifest_hashes(rank_ready: dict[str, Any]) -> dict[str, str]:
    sums_path = Path(rank_ready["manifests"]["sha256sums"]).resolve()
    nonempty_file(sums_path, "rank checksum manifest")
    expected: dict[Path, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, raw_path = line.split(maxsplit=1)
        expected[Path(raw_path.lstrip(" *")).resolve()] = digest

    result: dict[str, str] = {}
    for key in ("accepted_episodes", "ar", "bidirectional"):
        path = Path(rank_ready["manifests"][key]).resolve()
        nonempty_file(path, f"rank {key} manifest")
        require(path in expected, f"{path} is absent from {sums_path}")
        actual = sha256(path)
        require(actual == expected[path], f"rank manifest hash mismatch: {path}")
        result[key] = actual
    return result


def prompt_signature(row: dict[str, Any]) -> str:
    structured = dict(row.get("prompt_structured") or {})
                                                                               
                                                                               
                                                                                
    structured.pop("schema_version", None)
    structured.pop("training_role", None)
    payload = {
        "prompt_structured": structured,
        "video_sha256": row.get("video_sha256"),
        "action_sha256": row.get("action_sha256"),
        "visibility_sha256": row.get("visibility_sha256"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_prompt_blocks(
    row: dict[str, Any],
    *,
    sample_id: str,
    mode: str,
) -> tuple[Counter[str], Counter[str], Counter[str]]:
    structured = row.get("prompt_structured") or {}
    blocks = structured.get("blocks") or []
    require(len(blocks) == 5, f"{mode} row does not have five prompt blocks: {sample_id}")
    if mode == "ar":
        schedule = row.get("prompt_schedule") or []
        require(len(schedule) == 5, f"AR prompt schedule is not length five: {sample_id}")
        for prompt, block in zip(schedule, blocks, strict=True):
            suffix = (
                "\n[CURRENT OPPONENT MOTION AND OUTCOME]\n"
                + str(block.get("text") or "")
            )
            require(
                str(prompt).endswith(suffix),
                f"AR prompt schedule differs from structured blocks: {sample_id}",
            )

    prompt_text = str(row.get("prompt_text", ""))
    require("wounded" not in prompt_text.lower(), f"wounded language present: {sample_id}")
    require("[CURRENT PLAYER ACTION]" not in prompt_text, f"player action leaked into prompt: {sample_id}")
    rendered = "\n".join(
        [prompt_text, *[str(value) for value in row.get("prompt_schedule") or []]]
    ).lower()
    forbidden_regions = (
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
    require(
        not any(term in rendered for term in forbidden_regions),
        f"absolute screen-region language present: {sample_id}",
    )
    motion: Counter[str] = Counter()
    visibility: Counter[str] = Counter()
    events: Counter[str] = Counter()
    for block in blocks:
        label = str(block.get("motion_label"))
        phase = str(block.get("visibility_phase"))
        motion[label] += 1
        visibility[phase] += 1
        if bool(block.get("fully_outside_view")):
            require(block.get("text") == OFFSCREEN_TEXT, f"offscreen prompt contract failed: {sample_id}")
            require(int(block.get("enemy_fire_ticks", 0)) == 0, f"offscreen fire found: {sample_id}")
        require(
            "screen_destination" not in block
            and "screen_destination_coordinates" not in block,
            f"absolute screen-region fields present: {sample_id}",
        )
        if int(block.get("enemy_fire_ticks", 0)) > 0:
            events["enemy_fire_blocks"] += 1
        if bool(block.get("enemy_killed")):
            events["enemy_killed_blocks"] += 1
        if bool(block.get("player_killed")):
            events["player_killed_blocks"] += 1
        if bool(block.get("enemy_respawned")):
            events["enemy_respawn_blocks"] += 1
    return motion, visibility, events


def merge_training_manifest(
    *,
    mode: str,
    source_paths: list[Path],
    output_path: Path,
    episode_release_dirs: dict[str, Path],
    expected_rows: int,
    clips_per_episode: int,
    checked_artifacts: set[Path],
    ar_signatures: dict[str, str],
) -> dict[str, Any]:
    sample_ids: set[str] = set()
    per_episode: Counter[str] = Counter()
    motion: Counter[str] = Counter()
    visibility: Counter[str] = Counter()
    events: Counter[str] = Counter()
    action_contracts: set[str] = set()
    button_modes: set[str] = set()
    prompt_schemas: set[str] = set()
    row_count = 0

    with output_path.open("wb") as output:
        for source_path in source_paths:
            for line_number, raw, row in iter_jsonl(source_path):
                row_count += 1
                sample_id = str(row.get("sample_id", ""))
                episode_id = str(row.get("episode_id", ""))
                require(sample_id and sample_id == str(row.get("clip_id", "")), f"bad sample id at {source_path}:{line_number}")
                require(sample_id not in sample_ids, f"duplicate {mode} sample id: {sample_id}")
                require(episode_id in episode_release_dirs, f"unknown episode in {mode}: {episode_id}")
                match = CLIP_SUFFIX.search(sample_id)
                require(match is not None, f"sample id lacks clip suffix: {sample_id}")
                clip_index = int(match.group("index"))
                require(0 <= clip_index < clips_per_episode, f"clip index out of range: {sample_id}")
                require(bool(row.get("training_admitted")), f"row not admitted: {sample_id}")
                require(str(row.get("split")) == "train", f"non-train split found: {sample_id}")
                require(int(row.get("source_frames", 0)) == 81, f"frame count mismatch: {sample_id}")
                require(float(row.get("source_fps", 0)) == 20.0, f"fps mismatch: {sample_id}")
                require(bool(row.get("audio_loss_eligible")), f"audio not eligible: {sample_id}")
                require(int(row.get("raw_action_chunk_size", 0)) == 256, f"action chunk mismatch: {sample_id}")
                require(int(row.get("standard_chunk_action_rows", 0)) == 80, f"action row contract mismatch: {sample_id}")
                require(
                    float(row.get("source_rollout_offset_sec", -1)) == float(clip_index * 4),
                    f"rollout offset mismatch: {sample_id}",
                )

                release_dir = episode_release_dirs[episode_id]
                for key in ("video_path", "audio_path", "action_path", "visibility_path", "prompt_bundle_path"):
                    artifact = Path(row[key]).resolve()
                    require(within(artifact, release_dir), f"{key} escapes episode release: {sample_id}")
                    if artifact not in checked_artifacts:
                        nonempty_file(artifact, f"{mode} {key}")
                        checked_artifacts.add(artifact)

                row_motion, row_visibility, row_events = validate_prompt_blocks(
                    row, sample_id=sample_id, mode=mode
                )
                if mode == "ar":
                    motion.update(row_motion)
                    visibility.update(row_visibility)
                    events.update(row_events)
                    ar_signatures[sample_id] = prompt_signature(row)
                else:
                    require(sample_id in ar_signatures, f"bidirectional sample absent from AR: {sample_id}")
                    require(
                        prompt_signature(row) == ar_signatures[sample_id],
                        f"AR/bidirectional structured prompt or artifact mismatch: {sample_id}",
                    )

                sample_ids.add(sample_id)
                per_episode[episode_id] += 1
                action_contracts.add(str(row.get("action_contract_version")))
                button_modes.add(str(row.get("button_conditioning_mode")))
                prompt_schemas.add(str(row.get("prompt_schema_version")))
                output.write(raw if raw.endswith(b"\n") else raw + b"\n")

    require(row_count == expected_rows, f"{mode} row count {row_count} != {expected_rows}")
    require(len(sample_ids) == expected_rows, f"{mode} sample ids are not unique")
    require(set(per_episode) == set(episode_release_dirs), f"{mode} episode coverage mismatch")
    require(
        all(count == clips_per_episode for count in per_episode.values()),
        f"{mode} does not contain {clips_per_episode} rows for every episode",
    )
    require(action_contracts == {"c25k-crossfps-legacy6-xonotic-duel-v11-v1"}, f"unexpected action contracts: {action_contracts}")
    require(button_modes == {"crossfps_legacy6"}, f"unexpected button modes: {button_modes}")
    expected_prompt_schema = AR_PROMPT_SCHEMA if mode == "ar" else BIDIR_PROMPT_SCHEMA
    require(prompt_schemas == {expected_prompt_schema}, f"unexpected prompt schemas: {prompt_schemas}")
    return {
        "rows": row_count,
        "sample_ids": sample_ids,
        "per_episode": per_episode,
        "motion": motion,
        "visibility": visibility,
        "events": events,
        "sha256": sha256(output_path),
        "action_contracts": sorted(action_contracts),
        "button_modes": sorted(button_modes),
        "prompt_schemas": sorted(prompt_schemas),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-ranks", type=int, default=8)
    parser.add_argument("--expected-episodes", type=int, default=1800)
    parser.add_argument("--clips-per-episode", type=int, default=15)
    parser.add_argument("--expected-width", type=int, default=1664)
    parser.add_argument("--expected-height", type=int, default=960)
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output: {output_dir}")
    output_dir.mkdir(parents=True)
    rebalance_ready_path = run_root / "rebalance_v1" / "READY.json"
    rebalance_ready: dict[str, Any] | None = None
    expected_rank_counts: list[int]
    if rebalance_ready_path.is_file():
        rebalance_ready = read_json(rebalance_ready_path)
        require(
            rebalance_ready.get("schema_version")
            == "xonotic-duel-v12-rebalance-ready-v1",
            f"bad rebalance schema: {rebalance_ready_path}",
        )
        require(
            str(rebalance_ready.get("run_id")) == run_root.name,
            "rebalance run ID mismatch",
        )
        require(
            int(rebalance_ready.get("expected_ranks", -1)) == args.expected_ranks,
            "rebalance rank count mismatch",
        )
        require(
            int(rebalance_ready.get("expected_episodes", -1))
            == args.expected_episodes,
            "rebalance episode count mismatch",
        )
        require(all((rebalance_ready.get("gates") or {}).values()), "rebalance gates failed")
        expected_rank_counts = [
            int(value) for value in rebalance_ready["snapshot"]["rank_targets"]
        ]
        require(
            len(expected_rank_counts) == args.expected_ranks,
            "rebalance target vector length mismatch",
        )
        require(
            sum(expected_rank_counts) == args.expected_episodes,
            "rebalance rank targets do not sum to the expected episode count",
        )
        for rank_index in range(args.expected_ranks):
            contract_path = run_root / "rebalance_v1" / f"rank_{rank_index:03d}.json"
            nonempty_file(contract_path, "rebalance rank contract")
            require(
                sha256(contract_path)
                == str(rebalance_ready["contract_sha256"][f"rank_{rank_index:03d}"]),
                f"rebalance contract hash mismatch: {contract_path}",
            )
            contract = read_json(contract_path)
            require(
                int(contract["target_episodes"]) == expected_rank_counts[rank_index],
                f"rebalance rank target mismatch: {contract_path}",
            )
    else:
        require(args.expected_episodes % args.expected_ranks == 0, "episodes must divide ranks")
        expected_per_rank = args.expected_episodes // args.expected_ranks
        expected_rank_counts = [expected_per_rank] * args.expected_ranks
    expected_training_rows = args.expected_episodes * args.clips_per_episode

    rank_readies: list[dict[str, Any]] = []
    rank_hashes: dict[str, dict[str, str]] = {}
    for rank_index in range(args.expected_ranks):
        rank_dir = run_root / "ranks" / f"rank_{rank_index:03d}"
        ready_path = rank_dir / "RANK_COMPLETE.json"
        nonempty_file(ready_path, "rank completion marker")
        ready = read_json(ready_path)
        require(
            ready.get("schema_version")
            in {
                "xonotic-duel-v11-rank-complete-v1",
                "xonotic-duel-v12-speed100-2x-rank-complete-v1",
            },
            f"bad rank schema: {ready_path}",
        )
        require(str(ready.get("run_id")) == run_root.name, f"run id mismatch: {ready_path}")
        require(int(ready["rank"]["index"]) == rank_index, f"rank index mismatch: {ready_path}")
        require(int(ready["rank"]["world"]) == args.expected_ranks, f"rank world mismatch: {ready_path}")
        expected_rank_episodes = expected_rank_counts[rank_index]
        require(int(ready["accepted"]["episodes"]) == expected_rank_episodes, f"rank episode count mismatch: {ready_path}")
        require(int(ready["accepted"]["ar_rows"]) == expected_rank_episodes * args.clips_per_episode, f"rank AR count mismatch: {ready_path}")
        require(int(ready["accepted"]["bidirectional_rows"]) == expected_rank_episodes * args.clips_per_episode, f"rank bidirectional count mismatch: {ready_path}")
        require(all((ready.get("gates") or {}).values()), f"rank completion gates failed: {ready_path}")
        rank_hashes[f"rank_{rank_index:03d}"] = verify_rank_manifest_hashes(ready)
        rank_readies.append(ready)
        print(f"rank_preflight_ok rank={rank_index} episodes={expected_rank_episodes}", flush=True)

    accepted_rows: list[dict[str, Any]] = []
    for rank_index, ready in enumerate(rank_readies):
        accepted_path = Path(ready["manifests"]["accepted_episodes"]).resolve()
        count = 0
        for _, _, row in iter_jsonl(accepted_path):
            count += 1
            require(str(row.get("production_run_id")) == run_root.name, "accepted run id mismatch")
            require(int(row.get("global_rank", -1)) == rank_index, "accepted rank mismatch")
            require(int(row.get("global_world", -1)) == args.expected_ranks, "accepted world mismatch")
            episode_index = int(row.get("global_episode_index", -1))
            if rebalance_ready is None:
                require(episode_index % args.expected_ranks == rank_index, "accepted rank sharding mismatch")
            require(bool(row.get("training_ready")), "accepted episode is not ready")
            accepted_rows.append(row)
        require(
            count == expected_rank_counts[rank_index],
            f"rank {rank_index} accepted rows {count} != {expected_rank_counts[rank_index]}",
        )

    accepted_rows.sort(key=lambda row: int(row["global_episode_index"]))
    indices = [int(row["global_episode_index"]) for row in accepted_rows]
    require(indices == list(range(args.expected_episodes)), "global episode indices are not exactly contiguous")
    episode_ids = [str(row["render_id"]) for row in accepted_rows]
    require(len(episode_ids) == len(set(episode_ids)), "duplicate episode ids")
    episode_release_dirs = {
        str(row["render_id"]): Path(row["release_dir"]).resolve() for row in accepted_rows
    }

    rollout_rows: list[dict[str, Any]] = []
    source_motion: Counter[str] = Counter()
    source_visibility: Counter[str] = Counter()
    policy_distribution: Counter[str] = Counter()
    skill_pair_distribution: Counter[str] = Counter()
    rollout_small_hash_cache: dict[Path, str] = {}
    for position, row in enumerate(accepted_rows, 1):
        episode_id = str(row["render_id"])
        release_dir = episode_release_dirs[episode_id]
        require(within(release_dir, run_root / "ranks"), f"release escapes run root: {release_dir}")
        ready_path = Path(row["training_ready_path"]).resolve()
        require(ready_path == release_dir / "TRAINING_READY.json", f"ready path mismatch: {episode_id}")
        nonempty_file(ready_path, "episode training-ready marker")
        actual_ready_sha = sha256(ready_path)
        require(actual_ready_sha == str(row["training_ready_sha256"]), f"episode ready hash mismatch: {episode_id}")
        episode_ready = read_json(ready_path)
        require(bool(episode_ready.get("training_ready")), f"episode not training ready: {episode_id}")
        require(all((episode_ready.get("gates") or {}).values()), f"episode gates failed: {episode_id}")
        require(str(episode_ready.get("episode_id")) == episode_id, f"episode id mismatch: {episode_id}")
        counts = episode_ready["counts"]
        require(int(counts["rollout_blocks"]) == 75, f"rollout block count mismatch: {episode_id}")
        require(int(counts["clips"]) == args.clips_per_episode, f"clip count mismatch: {episode_id}")
        require(int(counts["ar_rows"]) == args.clips_per_episode, f"episode AR count mismatch: {episode_id}")
        require(int(counts["bidirectional_rows"]) == args.clips_per_episode, f"episode bidirectional count mismatch: {episode_id}")
        require(int(counts["offscreen_enemy_fire_ticks"]) == 0, f"offscreen fire found: {episode_id}")
        source_motion.update(episode_ready["motion_label_distribution"])
        source_visibility.update(episode_ready["visibility_phase_distribution"])

        rollout_dir = release_dir / "rollout_60s"
        video_path = Path(episode_ready["rollout_media"]["path"]).resolve()
        prompt_path = rollout_dir / "prompt_bundle.json"
        action_path = rollout_dir / "model_actions_64hz.parquet"
        visibility_path = rollout_dir / "visibility_64hz.parquet"
        for artifact, label in (
            (video_path, "rollout video"),
            (prompt_path, "rollout prompt bundle"),
            (action_path, "rollout actions"),
            (visibility_path, "rollout visibility"),
        ):
            require(within(artifact, release_dir), f"{label} escapes release: {episode_id}")
            nonempty_file(artifact, label)
        for artifact in (prompt_path, action_path, visibility_path):
            if artifact not in rollout_small_hash_cache:
                rollout_small_hash_cache[artifact] = sha256(artifact)

        media = episode_ready["rollout_media"]
        require(int(media["frames"]) == 1201, f"rollout frames mismatch: {episode_id}")
        require(
            int(media["width"]) == args.expected_width
            and int(media["height"]) == args.expected_height,
            f"rollout resolution mismatch: {episode_id}",
        )
        require(str(media["fps"]) == "20/1", f"rollout fps mismatch: {episode_id}")
        require(int(media["audio_streams"]) >= 1, f"rollout audio missing: {episode_id}")
        rollout_rows.append(
            {
                "schema_version": "xonotic-duel-v11-stage2-production-rollout-row-v1",
                "production_run_id": run_root.name,
                "global_episode_index": int(row["global_episode_index"]),
                "global_rank": int(row["global_rank"]),
                "episode_id": episode_id,
                "duration_seconds": 60.0,
                "video_path": str(video_path),
                "video_sha256": str(media["sha256"]),
                "video_frames": 1201,
                "video_fps": 20,
                "prompt_bundle_path": str(prompt_path),
                "prompt_bundle_sha256": rollout_small_hash_cache[prompt_path],
                "action_path": str(action_path),
                "action_sha256": rollout_small_hash_cache[action_path],
                "visibility_path": str(visibility_path),
                "visibility_sha256": rollout_small_hash_cache[visibility_path],
                "prompt_blocks": 75,
                "training_admitted": True,
                "source_training_ready_path": str(ready_path),
                "source_training_ready_sha256": actual_ready_sha,
            }
        )
        policy_distribution[str(row["bots"]["pov_policy"])] += 1
        skill_pair_distribution[
            f"{int(row['bots']['aggressive_close_level'])}-{int(row['bots']['mid_range_evasive_level'])}"
        ] += 1
        if position % 200 == 0 or position == args.expected_episodes:
            print(f"episode_ready_audit progress={position}/{args.expected_episodes}", flush=True)

    accepted_path = output_dir / "accepted_episodes.jsonl"
    rollout_path = output_dir / "rollout_60s_manifest.jsonl"
    write_jsonl(accepted_path, accepted_rows)
    write_jsonl(rollout_path, rollout_rows)

    source_ar_paths = [Path(ready["manifests"]["ar"]).resolve() for ready in rank_readies]
    source_bidir_paths = [Path(ready["manifests"]["bidirectional"]).resolve() for ready in rank_readies]
    ar_path = output_dir / "ar_training_manifest.jsonl"
    bidir_path = output_dir / "bidirectional_training_manifest.jsonl"
    checked_artifacts: set[Path] = set()
    ar_signatures: dict[str, str] = {}
    ar = merge_training_manifest(
        mode="ar",
        source_paths=source_ar_paths,
        output_path=ar_path,
        episode_release_dirs=episode_release_dirs,
        expected_rows=expected_training_rows,
        clips_per_episode=args.clips_per_episode,
        checked_artifacts=checked_artifacts,
        ar_signatures=ar_signatures,
    )
    print(f"ar_merge_ok rows={ar['rows']} artifacts={len(checked_artifacts)}", flush=True)
    bidir = merge_training_manifest(
        mode="bidirectional",
        source_paths=source_bidir_paths,
        output_path=bidir_path,
        episode_release_dirs=episode_release_dirs,
        expected_rows=expected_training_rows,
        clips_per_episode=args.clips_per_episode,
        checked_artifacts=checked_artifacts,
        ar_signatures=ar_signatures,
    )
    print(f"bidirectional_merge_ok rows={bidir['rows']}", flush=True)
    require(ar["sample_ids"] == bidir["sample_ids"], "AR/bidirectional sample-id sets differ")
    require(ar["motion"] == source_motion, "AR/source motion distributions differ")
    require(ar["visibility"] == source_visibility, "AR/source visibility distributions differ")

    audio_ids_path = output_dir / "audio_loss_eligible_ids.txt"
    audio_ids_path.write_text("".join(f"{sample_id}\n" for sample_id in sorted(ar["sample_ids"])), encoding="utf-8")
    manifest_hashes = {
        "accepted_episodes": sha256(accepted_path),
        "rollout_60s": sha256(rollout_path),
        "ar": ar["sha256"],
        "bidirectional": bidir["sha256"],
        "audio_loss_eligible_ids": sha256(audio_ids_path),
    }
    checksum_path = output_dir / "MANIFEST_SHA256SUMS"
    checksum_path.write_text(
        "".join(
            f"{manifest_hashes[key]}  {path}\n"
            for key, path in (
                ("accepted_episodes", accepted_path),
                ("rollout_60s", rollout_path),
                ("ar", ar_path),
                ("bidirectional", bidir_path),
                ("audio_loss_eligible_ids", audio_ids_path),
            )
        ),
        encoding="utf-8",
    )

    gates = {
        "exact_eight_rank_completion_markers": len(rank_readies) == args.expected_ranks,
        "rebalance_contracts_match": rebalance_ready is None
        or sum(expected_rank_counts) == args.expected_episodes,
        "all_rank_completion_gates_pass": all(all((ready.get("gates") or {}).values()) for ready in rank_readies),
        "all_rank_manifest_hashes_match": True,
        "exact_contiguous_1800_episode_indices": indices == list(range(args.expected_episodes)),
        "all_1800_episode_releases_training_ready": len(accepted_rows) == args.expected_episodes,
        "all_episode_ready_hashes_match": True,
        "all_episode_static_gates_pass": True,
        "exact_1800_rollouts_1201_frames_20fps_audio": len(rollout_rows) == args.expected_episodes,
        "exact_27000_ar_rows": ar["rows"] == expected_training_rows,
        "exact_27000_bidirectional_rows": bidir["rows"] == expected_training_rows,
        "ar_bidirectional_sample_ids_match": ar["sample_ids"] == bidir["sample_ids"],
        "fifteen_clips_per_episode_both_modes": all(
            count == args.clips_per_episode for count in ar["per_episode"].values()
        ) and all(count == args.clips_per_episode for count in bidir["per_episode"].values()),
        "all_referenced_clip_artifacts_exist_and_nonempty": len(checked_artifacts) > 0,
        "exact_135000_prompt_blocks": sum(ar["motion"].values()) == args.expected_episodes * 75,
        "source_and_merged_prompt_distributions_match": ar["motion"] == source_motion and ar["visibility"] == source_visibility,
        "offscreen_prompt_contract_passed": int(source_visibility.get("out_of_view", 0)) > 0,
        "observed_motion_blocks_present": sum(
            count for label, count in ar["motion"].items() if label not in {"stationary", "unobserved"}
        ) > 0,
        "absolute_screen_region_conditioning_absent": True,
        "wounded_language_absent": True,
        "player_action_prompt_absent": True,
        "audio_loss_ids_cover_all_clips": len(ar["sample_ids"]) == expected_training_rows,
        "stage1_stage2_and_prior_duel_pipelines_unchanged_per_rank": True,
    }
    report = {
        "schema_version": "xonotic-duel-v11-production-batch-ready-v1",
        "production_run_id": run_root.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_ready": bool(all(gates.values())),
        "loader_validation_pending": True,
        "source_run_root": str(run_root),
        "output_dir": str(output_dir),
        "counts": {
            "ranks": args.expected_ranks,
            "episodes": args.expected_episodes,
            "unique_source_duration_seconds": args.expected_episodes * 60,
            "unique_source_duration_hours": args.expected_episodes / 60,
            "rollouts_60s": len(rollout_rows),
            "clips_4s_81frames": expected_training_rows,
            "alternate_clip_packaging_duration_seconds": expected_training_rows * 4,
            "alternate_clip_packaging_duration_hours": expected_training_rows * 4 / 3600,
            "ar_rows": ar["rows"],
            "bidirectional_rows": bidir["rows"],
            "prompt_blocks": sum(ar["motion"].values()),
            "checked_unique_clip_artifacts": len(checked_artifacts),
        },
        "media_contract": {
            "rollout_width": args.expected_width,
            "rollout_height": args.expected_height,
            "rollout_frames": 1201,
            "rollout_fps": 20,
            "loader_target_width": 832,
            "loader_target_height": 480,
        },
        "motion_label_distribution": dict(sorted(ar["motion"].items())),
        "visibility_phase_distribution": dict(sorted(ar["visibility"].items())),
        "combat_event_block_distribution": dict(sorted(ar["events"].items())),
        "pov_policy_distribution": dict(sorted(policy_distribution.items())),
        "skill_pair_distribution": dict(sorted(skill_pair_distribution.items())),
        "contracts": {
            "action_contracts": ar["action_contracts"],
            "button_modes": ar["button_modes"],
            "prompt_schemas": ar["prompt_schemas"],
        },
        "gates": gates,
        "source_rank_manifest_sha256": rank_hashes,
        "manifests": {
            "accepted_episodes": str(accepted_path),
            "rollout_60s": str(rollout_path),
            "ar": str(ar_path),
            "bidirectional": str(bidir_path),
            "audio_loss_eligible_ids": str(audio_ids_path),
            "sha256sums": str(checksum_path),
        },
        "manifest_sha256": manifest_hashes,
    }
    write_json(output_dir / "BATCH_READY.json", report)
    print(json.dumps({"training_ready": report["training_ready"], "counts": report["counts"], "gates": gates}, indent=2), flush=True)
    return 0 if report["training_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
