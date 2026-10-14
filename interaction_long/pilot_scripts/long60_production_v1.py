                      
"""Prepare, run, and finalize the isolated 30 h long60 production release.

The formal unit is one 60.05 s episode.  Each operating-system worker owns one
resident Xonotic lane and processes a deterministic modulo shard.  Raw AVI and
demo files exist only below a caller-supplied node-local scratch root and are
removed after every attempt; only an accepted MP4, QA, and compact metadata are
published to shared storage.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import random
import shutil
import sys
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pilot_scripts"))
import run_long60_moving_kill_lifecycle_pilot as lifecycle              


base = lifecycle.base
RELEASE_ID = "stage2_long60_multi_enemy_lifecycle_30h_20260824_v2"
SCHEMA_VERSION = "xonotic-stage2-long60-production-manifest-v1"
EPISODE_COUNT = 1800
EXPECTED_VIDEO_SECONDS = 60.05
EXPECTED_VIDEO_HOURS = EPISODE_COUNT * EXPECTED_VIDEO_SECONDS / 3600.0
BUILD_TAG = "capture-65a48cd4a2c6-aarch64"
BUILD_COMMIT = "65a48cd4a2c614d206d62ff0c598b0b7cff1cb47"
DEFAULT_MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
DEFAULT_OUTPUT_ROOT = Path("./rigen_data") / RELEASE_ID
TEMPLATES = lifecycle.ORIGINAL_VARIANTS
TEMPLATE_ENGINE_SEEDS = {
    "four_distinct": 26082301,
    "controlled_return": 26082302,
}
KILL_BLOCK_BY_TEMPLATE_SLOT = {
    "four_distinct": {1: 9, 2: 28, 3: 49, 4: 67},
    "controlled_return": {1: 40, 2: 18, 3: 57, 4: 68},
}
                                                                              
                                                                              
                                                                              
                                                                          
                                                           
KILLABLE_SLOTS_BY_TEMPLATE = {
    "four_distinct": (1, 2, 3),
    "controlled_return": (1, 2),
}
SPLIT_COUNTS = {"train": 1500, "validation": 150, "test": 150}
KILL_COUNT_COUNTS = {0: 720, 1: 720, 2: 360}


APPEARANCE_CATALOG = {
    actor.actor_id: actor for actor in lifecycle.LIFECYCLE_ACTORS
}
ACTOR_IDS = tuple(APPEARANCE_CATALOG)


def utc_now() -> str:
    return base.utc_now()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    os.replace(temporary, path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def relative_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def actors_for_row(row: dict[str, Any]) -> tuple[Any, ...]:
    kill_slots = set(int(value) for value in row["kill_slots"])
    result = []
    for slot, actor_id in enumerate(row["actor_order"], 1):
        appearance = APPEARANCE_CATALOG[actor_id]
        health = 999.0
        if slot in kill_slots:
                                                                              
                                                                              
                                                      
            if row["template"] == "controlled_return" and slot == 1:
                health = 60.0
            elif row["template"] == "controlled_return" and slot == 2:
                                                                             
                                                                         
                health = 25.0
            else:
                health = 15.0
        result.append(
            base.Actor(
                slot,
                appearance.actor_id,
                appearance.model,
                appearance.skin,
                appearance.color,
                health,
                appearance.armor,
                appearance.description,
            )
        )
    return tuple(result)


def kill_block_by_slot(row: dict[str, Any]) -> dict[int, int]:
    declared = KILL_BLOCK_BY_TEMPLATE_SLOT[row["template"]]
    return {int(slot): declared[int(slot)] for slot in row["kill_slots"]}


def configure_runtime(row: dict[str, Any]) -> tuple[Any, ...]:
    actors = actors_for_row(row)
    expected = kill_block_by_slot(row)
    base.ACTORS = actors
    lifecycle.LIFECYCLE_ACTORS = actors
    lifecycle.KILL_BLOCK_BY_SLOT = expected
    lifecycle.EXPECTED_KILL_ACTOR_IDS = {
        actors[slot - 1].actor_id for slot in expected
    }
    return actors


def distribution_rows() -> list[dict[str, Any]]:
    rng = random.Random(2608241301)
    templates = ["four_distinct"] * 900 + ["controlled_return"] * 900
    kill_counts = [
        count
        for count, cardinality in sorted(KILL_COUNT_COUNTS.items())
        for _ in range(cardinality)
    ]
    splits = [
        split
        for split, cardinality in SPLIT_COUNTS.items()
        for _ in range(cardinality)
    ]
    rng.shuffle(templates)
    rng.shuffle(kill_counts)
    rng.shuffle(splits)
    permutations = list(itertools.permutations(ACTOR_IDS))
    rng.shuffle(permutations)
    subset_counters: Counter[tuple[str, int]] = Counter()
    rows: list[dict[str, Any]] = []
    for index, (template, kill_count, split) in enumerate(
        zip(templates, kill_counts, splits, strict=True)
    ):
        subsets = list(
            itertools.combinations(
                KILLABLE_SLOTS_BY_TEMPLATE[template], kill_count
            )
        )
        subset_index = subset_counters[(template, kill_count)] % len(subsets)
        subset_counters[(template, kill_count)] += 1
        kill_slots = subsets[subset_index]
        actor_order = permutations[(index * 7 + index // 24) % len(permutations)]
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "release_id": RELEASE_ID,
                "manifest_index": index,
                "episode_id": f"s2l60m_v2_{index:06d}",
                "split": split,
                "template": template,
                "engine_seed": TEMPLATE_ENGINE_SEEDS[template],
                "distribution_seed": 2608241301 + index,
                "actor_order": list(actor_order),
                "kill_slots": list(kill_slots),
                "kill_count": kill_count,
                "returning_identity": template == "controlled_return",
                "enemy_jump_count": 1,
                "raw_avi_retained": False,
            }
        )

                                                                          
    canary_signatures = [
        ("four_distinct", (1, 2)),
        ("four_distinct", (3,)),
        ("controlled_return", (1, 2)),
        ("controlled_return", (2,)),
    ]
    for target_index, signature in enumerate(canary_signatures):
        source_index = next(
            index
            for index in range(target_index, len(rows))
            if (
                rows[index]["template"],
                tuple(rows[index]["kill_slots"]),
            )
            == signature
        )
        rows[target_index], rows[source_index] = rows[source_index], rows[target_index]
    for index, row in enumerate(rows):
        row["manifest_index"] = index
        row["episode_id"] = f"s2l60m_v2_{index:06d}"
    return rows


def build_episode_scenario(
    row: dict[str, Any], manifest_root: Path, shared_actions: Path,
) -> tuple[Path, Path]:
    actors = configure_runtime(row)
    segments = TEMPLATES[row["template"]]
    configuration_payload = json.dumps(
        {
            "template": row["template"],
            "actor_order": row["actor_order"],
            "kill_slots": row["kill_slots"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    configuration_hash = hashlib.sha256(configuration_payload).hexdigest()[:20]
    timeline = manifest_root / "timeline_configs" / f"{configuration_hash}.csv"
    if not timeline.exists():
        base.write_timeline(timeline, segments)
    prompts = lifecycle.lifecycle_prompt_schedule(segments)
    scenario = lifecycle.lifecycle_build_scenario(
        row["episode_id"],
        int(row["engine_seed"]),
        shared_actions,
        timeline,
        prompts,
        segments,
    )
    scenario.update(
        {
            "schema_version": "xonotic-stage2-long60-production-scenario-v1",
            "release_id": RELEASE_ID,
            "manifest_index": row["manifest_index"],
            "split": row["split"],
            "dataset_role": "stage2_long_horizon_multi_enemy_production",
            "formal_collection_authorized": True,
            "training_admitted": False,
            "distribution": {
                "template": row["template"],
                "actor_order": row["actor_order"],
                "kill_slots": row["kill_slots"],
                "kill_count": row["kill_count"],
                "returning_identity": row["returning_identity"],
                "enemy_jump_count": row["enemy_jump_count"],
                "player_action_profile": "humanlike_bursty_v4_frozen",
            },
            "storage_policy": {
                "raw_avi_retained": False,
                "demo_retained": False,
                "accepted_mp4_retained": True,
            },
            "runtime_build_required": BUILD_TAG,
            "runtime_source_commit_required": BUILD_COMMIT,
            "actors": [actor.__dict__ for actor in actors],
        }
    )
    expected_by_slot = kill_block_by_slot(row)
    for encounter, segment in zip(
        scenario["encounters"], segments, strict=True
    ):
        declared_kill_block = expected_by_slot.get(segment.slot)
        is_killing_encounter = (
            declared_kill_block is not None
            and segment.start_block <= declared_kill_block < segment.end_block
        )
        encounter["intent_outcome"] = (
            "kill" if is_killing_encounter else "hit_survive"
        )
        encounter["kill_block"] = (
            declared_kill_block if is_killing_encounter else None
        )
        encounter["despawn_block"] = (
            segment.end_block if is_killing_encounter else None
        )
    scenario_path = (
        manifest_root / "episodes" / row["episode_id"] / "scenario.json"
    )
    write_json_atomic(scenario_path, scenario)
    return scenario_path, timeline


def prepare(manifest_root: Path) -> None:
    manifest_root = manifest_root.resolve()
    if manifest_root.exists():
        raise RuntimeError(f"manifest root already exists: {manifest_root}")
    manifest_root.mkdir(parents=True)
    actions_by_template: dict[str, Path] = {}
    for template, segments in TEMPLATES.items():
        path = manifest_root / "template_actions" / template / "actions.csv"
        base.write_actions(
            path,
            f"{RELEASE_ID}_{template}",
            TEMPLATE_ENGINE_SEEDS[template],
            segments,
        )
        actions_by_template[template] = path

    rows = distribution_rows()
    for index, row in enumerate(rows):
        scenario_path, timeline = build_episode_scenario(
            row, manifest_root, actions_by_template[row["template"]]
        )
        row["scenario_path"] = relative_to_root(scenario_path)
        row["scenario_sha256"] = base.sha256(scenario_path)
        row["actions_path"] = relative_to_root(
            actions_by_template[row["template"]]
        )
        row["actions_sha256"] = base.sha256(
            actions_by_template[row["template"]]
        )
        row["timeline_path"] = relative_to_root(timeline)
        row["timeline_sha256"] = base.sha256(timeline)
        if index and index % 100 == 0:
            print(f"prepared={index}/{len(rows)}", flush=True)

    manifest = manifest_root / "manifest.jsonl"
    write_jsonl_atomic(manifest, rows)
    metadata = {
        "schema_version": "xonotic-stage2-long60-production-metadata-v1",
        "release_id": RELEASE_ID,
        "created_utc": utc_now(),
        "manifest_path": relative_to_root(manifest),
        "manifest_sha256": base.sha256(manifest),
        "episode_count": len(rows),
        "episode_seconds": EXPECTED_VIDEO_SECONDS,
        "target_video_hours": 30.0,
        "expected_video_hours": EXPECTED_VIDEO_HOURS,
        "split_counts": dict(Counter(row["split"] for row in rows)),
        "template_counts": dict(Counter(row["template"] for row in rows)),
        "kill_count_counts": {
            str(key): value
            for key, value in sorted(
                Counter(row["kill_count"] for row in rows).items()
            )
        },
        "returning_identity_episodes": sum(
            row["returning_identity"] for row in rows
        ),
        "enemy_jump_episodes": sum(row["enemy_jump_count"] > 0 for row in rows),
        "runtime_build": BUILD_TAG,
        "runtime_source_commit": BUILD_COMMIT,
        "topology": {
            "nodes": 2,
            "gpus_per_node": 4,
            "lanes_per_gpu": 4,
            "total_lanes": 32,
        },
        "storage_policy": {
            "raw_avi_path_class": "node-local scratch only",
            "raw_avi_retained": False,
            "demo_retained": False,
            "shared_outputs": ["mp4", "qa.json", "record.json"],
        },
        "formal_collection_authorized": True,
        "training_admitted": False,
        "existing_stage1_stage2_pipelines_modified": False,
        "canary_manifest_indices": [0, 1, 2, 3],
    }
    write_json_atomic(manifest_root / "MANIFEST_METADATA.json", metadata)
    write_json_atomic(
        manifest_root / "PREPARED.json",
        {
            "ready": True,
            "created_utc": utc_now(),
            "manifest_sha256": metadata["manifest_sha256"],
            "episode_count": len(rows),
        },
    )
    print(json.dumps(metadata, sort_keys=True), flush=True)


def validate_manifest(manifest_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    prepared_path = manifest_root / "PREPARED.json"
    manifest = manifest_root / "manifest.jsonl"
    if not metadata_path.is_file() or not prepared_path.is_file() or not manifest.is_file():
        raise RuntimeError(f"incomplete prepared manifest: {manifest_root}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    rows = load_jsonl(manifest)
    checks = {
        "prepared": prepared.get("ready") is True,
        "release_id": metadata.get("release_id") == RELEASE_ID,
        "manifest_hash": base.sha256(manifest) == metadata.get("manifest_sha256"),
        "episode_count": len(rows) == EPISODE_COUNT == metadata.get("episode_count"),
        "unique_episode_ids": len({row["episode_id"] for row in rows}) == len(rows),
        "contiguous_indices": [row["manifest_index"] for row in rows]
        == list(range(len(rows))),
        "split_counts": Counter(row["split"] for row in rows) == SPLIT_COUNTS,
        "kill_counts": Counter(row["kill_count"] for row in rows)
        == KILL_COUNT_COUNTS,
        "no_raw_avi_policy": all(row["raw_avi_retained"] is False for row in rows),
        "runtime_build": metadata.get("runtime_build") == BUILD_TAG,
        "runtime_commit": metadata.get("runtime_source_commit") == BUILD_COMMIT,
    }
    if not all(checks.values()):
        raise RuntimeError(f"manifest validation failed: {checks}")
    return rows, metadata


def safe_remove_stage(stage: Path, scratch_root: Path) -> None:
    stage_resolved = stage.resolve()
    scratch_resolved = scratch_root.resolve()
    if not str(scratch_resolved).startswith(("./tmp/", "./tmp/")):
        raise RuntimeError(f"refusing non-local scratch cleanup: {scratch_resolved}")
    if not stage_resolved.is_relative_to(scratch_resolved):
        raise RuntimeError(
            f"refusing out-of-scratch cleanup: {stage_resolved} not under {scratch_resolved}"
        )
    if stage.exists():
        shutil.rmtree(stage)


def copy_video_atomic(source: Path, destination: Path) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.partial.{os.getpid()}"
    )
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as input_handle, temporary.open("wb") as output_handle:
        for chunk in iter(lambda: input_handle.read(8 * 1024 * 1024), b""):
            output_handle.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        output_handle.flush()
        os.fsync(output_handle.fileno())
    os.replace(temporary, destination)
    return digest.hexdigest(), size


def accepted_paths(output_root: Path, row: dict[str, Any]) -> dict[str, Path]:
    episode_root = output_root / "episodes" / row["split"] / row["episode_id"]
    return {
        "episode_root": episode_root,
        "video": episode_root / "video.mp4",
        "qa": episode_root / "qa.json",
        "record": episode_root / "record.json",
        "accepted": output_root / "status" / "accepted" / f"{row['episode_id']}.json",
    }


def already_accepted(output_root: Path, row: dict[str, Any]) -> bool:
    paths = accepted_paths(output_root, row)
    if not all(paths[key].is_file() for key in ("video", "qa", "record", "accepted")):
        return False
    try:
        qa = json.loads(paths["qa"].read_text(encoding="utf-8"))
        record = json.loads(paths["record"].read_text(encoding="utf-8"))
        return (
            qa.get("passed") is True
            and record.get("episode_id") == row["episode_id"]
            and paths["video"].stat().st_size == record.get("video_size_bytes")
            and record.get("raw_avi_retained") is False
        )
    except (OSError, ValueError, TypeError):
        return False


def run_attempt(
    lane: Any,
    row: dict[str, Any],
    scenario: dict[str, Any],
    output_root: Path,
    scratch_root: Path,
    attempt: int,
) -> dict[str, Any]:
    configure_runtime(row)
    stage = scratch_root / "episodes" / f"{row['episode_id']}.attempt{attempt:02d}"
    safe_remove_stage(stage, scratch_root)
    started = time.monotonic()
    live: dict[str, Any] | None = None
    render: dict[str, Any] | None = None
    try:
        live = lane.run_live(stage, scenario, retry=attempt - 1)
        render = lane.run_render(stage, scenario, live)
        raw_avi = Path(render["raw_avi"])
        if not raw_avi.is_relative_to(scratch_root.resolve()):
            raise RuntimeError(f"raw AVI escaped node-local scratch: {raw_avi}")
        local_video = stage / "accepted_candidate.mp4"
        encode_wall = base.encode_video(raw_avi, local_video)
        qa = lifecycle.lifecycle_validate_episode(
            scenario, stage, live, render, local_video, encode_wall
        )
        raw_avi.unlink(missing_ok=True)
        if not qa["passed"]:
            rejection = {
                "schema_version": "xonotic-stage2-long60-rejection-v1",
                "created_utc": utc_now(),
                "episode_id": row["episode_id"],
                "attempt": attempt,
                "failed_checks": sorted(
                    key for key, value in qa["checks"].items() if not value
                ),
                "qa": qa,
            }
            write_json_atomic(
                output_root
                / "status"
                / "rejected"
                / f"{row['episode_id']}.attempt{attempt:02d}.json",
                rejection,
            )
            raise RuntimeError(
                "semantic QA failed: "
                + ",".join(rejection["failed_checks"])
            )

        paths = accepted_paths(output_root, row)
        video_sha256, video_size = copy_video_atomic(local_video, paths["video"])
        if video_sha256 != qa["video"]["sha256"]:
            raise RuntimeError(
                f"published video hash mismatch: {video_sha256} "
                f"!= {qa['video']['sha256']}"
            )
        qa["video"].update(
            {
                "path": str(paths["video"]),
                "sha256": video_sha256,
                "size_bytes": video_size,
            }
        )
        write_json_atomic(paths["qa"], qa)
        record = {
            "schema_version": "xonotic-stage2-long60-accepted-record-v1",
            "created_utc": utc_now(),
            "release_id": RELEASE_ID,
            "manifest_index": row["manifest_index"],
            "episode_id": row["episode_id"],
            "split": row["split"],
            "template": row["template"],
            "kill_count": row["kill_count"],
            "kill_slots": row["kill_slots"],
            "actor_order": row["actor_order"],
            "scenario_path": row["scenario_path"],
            "scenario_sha256": row["scenario_sha256"],
            "actions_path": row["actions_path"],
            "actions_sha256": row["actions_sha256"],
            "timeline_path": row["timeline_path"],
            "timeline_sha256": row["timeline_sha256"],
            "video_path": str(paths["video"]),
            "video_sha256": video_sha256,
            "video_size_bytes": video_size,
            "video_duration_seconds": qa["video"]["duration_seconds"],
            "video_frames": base.OUTPUT_FRAMES,
            "qa_path": str(paths["qa"]),
            "raw_avi_retained": False,
            "demo_retained": False,
            "attempt": attempt,
            "wall_seconds": time.monotonic() - started,
            "runtime_build": BUILD_TAG,
            "runtime_source_commit": BUILD_COMMIT,
        }
        write_json_atomic(paths["record"], record)
        write_json_atomic(paths["accepted"], record)
        return record
    finally:
        if render and render.get("raw_avi"):
            Path(render["raw_avi"]).unlink(missing_ok=True)
        safe_remove_stage(stage, scratch_root)


def worker(
    manifest_root: Path,
    output_root: Path,
    scratch_root: Path,
    lane_id: int,
    lane_count: int,
    port: int,
    max_attempts: int,
    episode_indices: set[int] | None,
) -> None:
    if not 0 <= lane_id < lane_count:
        raise ValueError(f"lane_id must be in 0..{lane_count - 1}")
    if not 1 <= max_attempts <= 10:
        raise ValueError("max_attempts must be in 1..10")
    rows, _ = validate_manifest(manifest_root)
    selected = [
        row
        for row in rows
        if (
            row["manifest_index"] in episode_indices
            if episode_indices is not None
            else row["manifest_index"] % lane_count == lane_id
        )
    ]
    build = ROOT / "build" / BUILD_TAG
    if (build / "SOURCE_COMMIT").read_text(encoding="utf-8").strip() != BUILD_COMMIT:
        raise RuntimeError(f"runtime build commit mismatch: {build}")
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lane: Any | None = None
    generation = 0
    failures: list[dict[str, Any]] = []
    completed = 0
    started = time.monotonic()
    try:
        for sequence, row in enumerate(selected, 1):
            if already_accepted(output_root, row):
                completed += 1
                print(
                    f"episode_skip_accepted lane={lane_id} "
                    f"episode={row['episode_id']} progress={sequence}/{len(selected)}",
                    flush=True,
                )
                continue
            scenario_path = ROOT / row["scenario_path"]
            if base.sha256(scenario_path) != row["scenario_sha256"]:
                raise RuntimeError(f"scenario hash mismatch: {scenario_path}")
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            last_error = ""
            for attempt in range(1, max_attempts + 1):
                if lane is None:
                    generation += 1
                    lane_path = scratch_root / f"resident-generation-{generation:03d}"
                    lane = base.reusable.ReusableStage1Lane(
                        lane_path, build=build, port=port
                    )
                try:
                    record = run_attempt(
                        lane,
                        row,
                        scenario,
                        output_root,
                        scratch_root,
                        attempt,
                    )
                    completed += 1
                    print(
                        "episode_accepted "
                        f"lane={lane_id} episode={row['episode_id']} "
                        f"attempt={attempt} wall={record['wall_seconds']:.3f} "
                        f"progress={sequence}/{len(selected)}",
                        flush=True,
                    )
                    break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    print(
                        "episode_attempt_failed "
                        f"lane={lane_id} episode={row['episode_id']} "
                        f"attempt={attempt} error={json.dumps(last_error)}",
                        file=sys.stderr,
                        flush=True,
                    )
                    traceback.print_exc()
                    lane.close()
                    lane = None
                    time.sleep(min(2.0 * attempt, 10.0))
            else:
                failures.append(
                    {
                        "manifest_index": row["manifest_index"],
                        "episode_id": row["episode_id"],
                        "error": last_error,
                    }
                )
    finally:
        if lane is not None:
            lane.close()
    summary = {
        "schema_version": "xonotic-stage2-long60-lane-summary-v1",
        "created_utc": utc_now(),
        "lane_id": lane_id,
        "lane_count": lane_count,
        "selected": len(selected),
        "completed_or_preexisting": completed,
        "failures": failures,
        "wall_seconds": time.monotonic() - started,
        "raw_avi_retained": False,
    }
    write_json_atomic(
        output_root / "status" / "lanes" / f"lane-{lane_id:03d}.json",
        summary,
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    if failures:
        raise RuntimeError(
            f"lane {lane_id} left {len(failures)} episode(s) incomplete"
        )


def finalize(manifest_root: Path, output_root: Path) -> None:
    rows, metadata = validate_manifest(manifest_root)
    accepted: list[dict[str, Any]] = []
    missing: list[str] = []
    invalid: list[str] = []
    for row in rows:
        paths = accepted_paths(output_root, row)
        if not already_accepted(output_root, row):
            missing.append(row["episode_id"])
            continue
        record = json.loads(paths["record"].read_text(encoding="utf-8"))
        qa = json.loads(paths["qa"].read_text(encoding="utf-8"))
        if (
            qa.get("passed") is not True
            or record.get("scenario_sha256") != row["scenario_sha256"]
            or record.get("video_duration_seconds") != EXPECTED_VIDEO_SECONDS
            or record.get("raw_avi_retained") is not False
        ):
            invalid.append(row["episode_id"])
            continue
        scenario = json.loads((ROOT / row["scenario_path"]).read_text(encoding="utf-8"))
        accepted.append(
            {
                **record,
                "prompt_schedule": scenario["prompt_schedule"],
                "actors": scenario["actors"],
                "encounters": scenario["encounters"],
                "training_admitted": False,
            }
        )
    avi_paths = sorted(str(path) for path in output_root.rglob("*.avi"))
    checks = {
        "accepted_count": len(accepted) == EPISODE_COUNT,
        "missing_empty": not missing,
        "invalid_empty": not invalid,
        "raw_avi_absent": not avi_paths,
        "unique_episode_ids": len({row["episode_id"] for row in accepted})
        == len(accepted),
        "video_hours": math.isclose(
            sum(row["video_duration_seconds"] for row in accepted) / 3600.0,
            EXPECTED_VIDEO_HOURS,
            rel_tol=0,
            abs_tol=1e-9,
        ),
    }
    report = {
        "schema_version": "xonotic-stage2-long60-collection-complete-v1",
        "created_utc": utc_now(),
        "release_id": RELEASE_ID,
        "complete": all(checks.values()),
        "checks": checks,
        "accepted_count": len(accepted),
        "expected_count": EPISODE_COUNT,
        "accepted_video_hours": sum(
            row["video_duration_seconds"] for row in accepted
        )
        / 3600.0,
        "missing_episode_ids": missing[:100],
        "invalid_episode_ids": invalid[:100],
        "raw_avi_paths": avi_paths[:20],
        "manifest_sha256": metadata["manifest_sha256"],
        "runtime_build": BUILD_TAG,
        "runtime_source_commit": BUILD_COMMIT,
        "training_admitted": False,
        "note": "Collection complete; long-context loader/release admission is a separate postprocess gate.",
    }
    write_json_atomic(output_root / "COLLECTION_STATUS.json", report)
    if not report["complete"]:
        raise RuntimeError(
            f"collection incomplete: accepted={len(accepted)} "
            f"missing={len(missing)} invalid={len(invalid)} avi={len(avi_paths)}"
        )
    write_jsonl_atomic(output_root / "accepted.jsonl", accepted)
    write_json_atomic(output_root / "COLLECTION_COMPLETE.json", report)
    print(json.dumps(report, sort_keys=True), flush=True)


def audit(manifest_root: Path, output_root: Path) -> None:
    rows, metadata = validate_manifest(manifest_root)
    accepted_count = sum(already_accepted(output_root, row) for row in rows)
    result = {
        "manifest_ready": True,
        "manifest_episode_count": len(rows),
        "manifest_sha256": metadata["manifest_sha256"],
        "accepted_count": accepted_count,
        "remaining_count": len(rows) - accepted_count,
        "raw_avi_count": sum(1 for _ in output_root.rglob("*.avi"))
        if output_root.exists()
        else 0,
    }
    print(json.dumps(result, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument(
        "--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT
    )
    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument(
        "--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT
    )
    worker_parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    worker_parser.add_argument("--scratch-root", type=Path, required=True)
    worker_parser.add_argument("--lane-id", type=int, required=True)
    worker_parser.add_argument("--lane-count", type=int, default=32)
    worker_parser.add_argument("--port", type=int, required=True)
    worker_parser.add_argument("--max-attempts", type=int, default=3)
    worker_parser.add_argument(
        "--episode-index", type=int, action="append", default=None
    )
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument(
        "--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT
    )
    finalize_parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument(
        "--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT
    )
    audit_parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.manifest_root)
    elif args.command == "worker":
        worker(
            args.manifest_root.resolve(),
            args.output_root.resolve(),
            args.scratch_root.resolve(),
            args.lane_id,
            args.lane_count,
            args.port,
            args.max_attempts,
            set(args.episode_index) if args.episode_index is not None else None,
        )
    elif args.command == "finalize":
        finalize(args.manifest_root.resolve(), args.output_root.resolve())
    elif args.command == "audit":
        audit(args.manifest_root.resolve(), args.output_root.resolve())
    else:
        raise AssertionError(args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
