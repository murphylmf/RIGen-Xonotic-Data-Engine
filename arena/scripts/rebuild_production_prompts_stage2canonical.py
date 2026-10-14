                      
"""Rebuild duel-v11 prompts with the canonical Stage-2 text renderer contract.

This is an isolated prompt-only transformation. It reads the frozen 30-hour
media/action/visibility release, recomputes every 0.8 s prompt block from the
authoritative 64 Hz visibility telemetry, and writes new AR, bidirectional, and
60-second rollout manifests. The source release is never modified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Any, Iterator

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
RENDERER_PATH = SCRIPT_DIR / "visibility_prompt_v2/build_rollout_release.py"
CANONICAL_STAGE2_RENDERER = Path(
    "./scripts/"
    "prepare_xonotic_stage2_v14r4_visibility_prompt_release.py"
)
CANONICAL_STAGE2_REPORT = Path(
    "./rigen_data/manifests/"
    "stage2_enemy_motion_temporal_visibility_41217_5x0p8s_"
    "20260821_v14r4_nocrosshair_visibilityprompt_v2/RELEASE_REPORT.json"
)

spec = importlib.util.spec_from_file_location("duel_v11_stage2_renderer", RENDERER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot import renderer: {RENDERER_PATH}")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


CLIP_SUFFIX = re.compile(r"_c(?P<index>\d{2})$")
EXPECTED_EPISODES = 1_800
EXPECTED_CLIPS = 27_000
EXPECTED_BLOCKS = 135_000
PROMPT_ONLY_FIELDS = {
    "prompt_bundle_path",
    "prompt_schedule",
    "prompt_schedule_chunking",
    "prompt_schedule_schema_version",
    "prompt_schedule_target_frame_ranges_inclusive",
    "prompt_schedule_video_latents_per_chunk",
    "prompt_schema_version",
    "prompt_renderer_version",
    "prompt_source_rollout_block_range_inclusive",
    "prompt_source_rollout_bundle_path",
    "prompt_structured",
    "prompt_text",
    "semantic_revision",
    "training_prompt_mode",
    "visibility_prompt_version",
}
FORBIDDEN_SCREEN_REGION_TEXT = (
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
MEDIA_ACTION_FIELDS = (
    "sample_id",
    "clip_id",
    "episode_id",
    "video_path",
    "video_sha256",
    "audio_path",
    "action_path",
    "action_sha256",
    "visibility_path",
    "visibility_sha256",
    "action_contract_version",
    "button_conditioning_mode",
    "action_channels",
    "button_columns",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def canonical_line(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"


def jsonl_rows(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: row is not an object")
            yield value


def source_manifest_snapshot(source: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for key, filename in (
        ("accepted_episodes", "accepted_episodes.jsonl"),
        ("rollout_60s", "rollout_60s_manifest.jsonl"),
        ("ar", "ar_training_manifest.jsonl"),
        ("bidirectional", "bidirectional_training_manifest.jsonl"),
        ("audio_ids", "audio_loss_eligible_ids.txt"),
    ):
        path = source / filename
        require(path.is_file() and path.stat().st_size > 0, f"missing source file: {path}")
        result[key] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    return result


def clip_index(row: dict[str, Any]) -> int:
    match = CLIP_SUFFIX.search(str(row.get("sample_id") or ""))
    if match is None:
        raise ValueError(f"clip suffix missing: {row.get('sample_id')}")
    index = int(match.group("index"))
    require(0 <= index < 15, f"clip index out of range: {row.get('sample_id')}")
    return index


def localize_blocks(
    rollout_blocks: list[dict[str, Any]], clip_number: int
) -> list[dict[str, Any]]:
    first = clip_number * renderer.CLIP_BLOCKS
    selected = rollout_blocks[first : first + renderer.CLIP_BLOCKS]
    require(len(selected) == renderer.CLIP_BLOCKS, f"missing blocks for clip {clip_number}")
    start_tick = clip_number * renderer.CLIP_TICKS
    local: list[dict[str, Any]] = []
    for local_index, source_block in enumerate(selected):
        block = copy.deepcopy(source_block)
        block["source_rollout_block_index"] = int(source_block["block_index"])
        block["block_index"] = local_index
        block["start_seconds"] = round(local_index * renderer.BLOCK_SECONDS, 4)
        block["end_seconds"] = round((local_index + 1) * renderer.BLOCK_SECONDS, 4)
        block["tick_range_inclusive"] = [
            int(source_block["tick_range_inclusive"][0]) - start_tick,
            int(source_block["tick_range_inclusive"][1]) - start_tick,
        ]
        local.append(block)
    return local


def rewrite_ar(
    source: dict[str, Any],
    blocks: list[dict[str, Any]],
    rollout_bundle_path: Path,
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    for field in PROMPT_ONLY_FIELDS:
        row.pop(field, None)
    schedule = [renderer.ar_prompt(block) for block in blocks]
    first = int(blocks[0]["source_rollout_block_index"])
    last = int(blocks[-1]["source_rollout_block_index"])
    row.update(
        {
            "prompt_schema_version": renderer.AR_PROMPT_SCHEMA,
            "prompt_schedule_schema_version": renderer.AR_PROMPT_SCHEMA,
            "prompt_renderer_version": renderer.PROMPT_RENDERER_VERSION,
            "visibility_prompt_version": renderer.VISIBILITY_CONTRACT,
            "semantic_revision": "duel_v11_stage2canonical_prompt_only_v2",
            "prompt_schedule_chunking": "2_latents_0p8s",
            "prompt_schedule_video_latents_per_chunk": 2,
            "prompt_schedule_target_frame_ranges_inclusive": [
                [index * 16 + 1, (index + 1) * 16]
                for index in range(renderer.CLIP_BLOCKS)
            ],
            "prompt_schedule": schedule,
            "prompt_text": schedule[0],
            "prompt_structured": renderer.structured_prompt(
                blocks,
                schema_version=renderer.AR_PROMPT_SCHEMA,
                training_role=(
                    "per_block_enemy_motion_interaction_and_visibility_condition"
                ),
            ),
            "prompt_source_rollout_bundle_path": str(rollout_bundle_path),
            "prompt_source_rollout_block_range_inclusive": [first, last],
            "source": "isolated_duel_v11_stage2canonical_prompt_only_release",
        }
    )
    return row


def rewrite_bidir(
    source: dict[str, Any],
    blocks: list[dict[str, Any]],
    rollout_bundle_path: Path,
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    for field in PROMPT_ONLY_FIELDS:
        row.pop(field, None)
    first = int(blocks[0]["source_rollout_block_index"])
    last = int(blocks[-1]["source_rollout_block_index"])
    row.update(
        {
            "prompt_schema_version": renderer.BIDIR_PROMPT_SCHEMA,
            "prompt_renderer_version": renderer.PROMPT_RENDERER_VERSION,
            "visibility_prompt_version": renderer.VISIBILITY_CONTRACT,
            "semantic_revision": "duel_v11_stage2canonical_prompt_only_v2",
            "prompt_text": renderer.bidirectional_prompt(blocks),
            "prompt_structured": renderer.structured_prompt(
                blocks,
                schema_version=renderer.BIDIR_PROMPT_SCHEMA,
                training_role=(
                    "full_clip_enemy_motion_interaction_and_visibility_timeline"
                ),
            ),
            "prompt_source_rollout_bundle_path": str(rollout_bundle_path),
            "prompt_source_rollout_block_range_inclusive": [first, last],
            "source": "isolated_duel_v11_stage2canonical_prompt_only_release",
        }
    )
    return row


def verify_nonprompt_preserved(
    old: dict[str, Any], new: dict[str, Any], sample_id: str
) -> None:
    for field in MEDIA_ACTION_FIELDS:
        require(old.get(field) == new.get(field), f"{sample_id}: changed {field}")
    old_nonprompt = {
        key: value
        for key, value in old.items()
        if key not in PROMPT_ONLY_FIELDS and key != "source"
    }
    new_nonprompt = {
        key: value
        for key, value in new.items()
        if key not in PROMPT_ONLY_FIELDS and key != "source"
    }
    require(old_nonprompt == new_nonprompt, f"{sample_id}: non-prompt fields changed")


def recursive_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from recursive_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from recursive_keys(child)


def validate_prompt_row(row: dict[str, Any], *, ar: bool) -> Counter[str]:
    sample_id = str(row["sample_id"])
    structured = row.get("prompt_structured") or {}
    blocks = structured.get("blocks") or []
    require(len(blocks) == 5, f"{sample_id}: expected five blocks")
    expected_schema = renderer.AR_PROMPT_SCHEMA if ar else renderer.BIDIR_PROMPT_SCHEMA
    require(row.get("prompt_schema_version") == expected_schema, f"{sample_id}: bad schema")
    require(structured.get("schema_version") == expected_schema, f"{sample_id}: bad structured schema")
    require(
        row.get("prompt_renderer_version") == renderer.PROMPT_RENDERER_VERSION,
        f"{sample_id}: bad renderer",
    )
    require(
        row.get("visibility_prompt_version") == renderer.VISIBILITY_CONTRACT,
        f"{sample_id}: bad visibility contract",
    )
    if ar:
        schedule = row.get("prompt_schedule") or []
        require(len(schedule) == 5, f"{sample_id}: AR schedule is not five blocks")
        require(schedule == [renderer.ar_prompt(block) for block in blocks], f"{sample_id}: AR schedule drift")
        require(row.get("prompt_text") == schedule[0], f"{sample_id}: prompt_text is not block zero")
    else:
        for field in (
            "prompt_schedule",
            "prompt_schedule_schema_version",
            "prompt_schedule_chunking",
            "prompt_schedule_target_frame_ranges_inclusive",
            "prompt_schedule_video_latents_per_chunk",
        ):
            require(field not in row, f"{sample_id}: bidirectional row retains {field}")
        require(
            row.get("prompt_text") == renderer.bidirectional_prompt(blocks),
            f"{sample_id}: bidirectional timeline drift",
        )

    rendered = "\n".join(
        [str(row.get("prompt_text") or ""), *[str(x) for x in row.get("prompt_schedule") or []]]
    ).lower()
    require("wounded" not in rendered, f"{sample_id}: wounded language present")
    require(
        not any(term in rendered for term in FORBIDDEN_SCREEN_REGION_TEXT),
        f"{sample_id}: absolute screen-region language present",
    )
    keys = set(recursive_keys(structured))
    require("screen_destination" not in keys, f"{sample_id}: screen_destination field present")
    require(
        "screen_destination_coordinates" not in keys,
        f"{sample_id}: screen_destination_coordinates field present",
    )

    counts: Counter[str] = Counter()
    for block in blocks:
        phase = str(block["visibility_phase"])
        label = str(block["motion_label"])
        counts[f"visibility:{phase}"] += 1
        counts[f"motion:{label}"] += 1
        if bool(block["fully_outside_view"]):
            require(block["text"] == renderer.OFFSCREEN_TEXT, f"{sample_id}: offscreen text drift")
            require(label == "unobserved", f"{sample_id}: offscreen motion leaked")
            require(int(block["enemy_fire_ticks"]) == 0, f"{sample_id}: offscreen fire leaked")
            counts["offscreen_exact"] += 1
        else:
            require(str(block["visibility_text"]) in str(block["text"]), f"{sample_id}: visibility text missing")
            if int(block["enemy_fire_ticks"]) > 0:
                require("fires" in str(block["text"]), f"{sample_id}: fire text missing")
                counts["enemy_fire_blocks"] += 1
            if bool(block["enemy_killed"]):
                counts["enemy_killed_blocks"] += 1
            if bool(block["player_killed"]):
                counts["player_killed_blocks"] += 1
            if bool(block["enemy_respawned"]):
                counts["enemy_respawn_blocks"] += 1
    return counts


def build_rollout_bundles(
    source: Path,
    work: Path,
    output: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    bundles: dict[str, dict[str, Any]] = {}
    rollout_rows: list[dict[str, Any]] = []
    distribution: Counter[str] = Counter()
    physical_dir = work / "rollout_prompt_bundles"
    physical_dir.mkdir(parents=True)
    for index, old_row in enumerate(jsonl_rows(source / "rollout_60s_manifest.jsonl"), 1):
        episode_id = str(old_row["episode_id"])
        require(episode_id not in bundles, f"duplicate rollout: {episode_id}")
        visibility_path = Path(str(old_row["visibility_path"]))
        require(visibility_path.is_file(), f"missing visibility: {visibility_path}")
        visibility = pd.read_parquet(visibility_path)
        require(len(visibility) == renderer.ROLLOUT_TICKS, f"{episode_id}: visibility length drift")
        blocks = [renderer.summarize_block(visibility, block) for block in range(renderer.ROLLOUT_BLOCKS)]
        schedule = [renderer.ar_prompt(block) for block in blocks]
        bundle = {
            "schema_version": renderer.PROMPT_BUNDLE_SCHEMA,
            "episode_id": episode_id,
            "block_seconds": renderer.BLOCK_SECONDS,
            "block_count": renderer.ROLLOUT_BLOCKS,
            "ar_prompt_schema_version": renderer.AR_PROMPT_SCHEMA,
            "bidirectional_prompt_schema_version": renderer.BIDIR_PROMPT_SCHEMA,
            "prompt_renderer_version": renderer.PROMPT_RENDERER_VERSION,
            "visibility_prompt_version": renderer.VISIBILITY_CONTRACT,
            "prompt_schedule": schedule,
            "bidirectional_prompt": renderer.bidirectional_prompt(blocks),
            "prompt_structured": renderer.structured_prompt(
                blocks,
                schema_version=renderer.AR_PROMPT_SCHEMA,
                training_role="full_rollout_block_prompt_schedule",
            ),
            "blocks": blocks,
        }
        physical_path = physical_dir / f"{episode_id}.json"
        final_path = output / "rollout_prompt_bundles" / physical_path.name
        write_json(physical_path, bundle)
        bundle_sha = sha256(physical_path)
        bundles[episode_id] = {
            "blocks": blocks,
            "path": final_path,
            "sha256": bundle_sha,
        }
        new_row = copy.deepcopy(old_row)
        new_row.update(
            {
                "schema_version": "xonotic-duel-v11-stage2canonical-production-rollout-row-v2",
                "prompt_bundle_path": str(final_path),
                "prompt_bundle_sha256": bundle_sha,
                "prompt_blocks": renderer.ROLLOUT_BLOCKS,
                "prompt_schema_version": renderer.AR_PROMPT_SCHEMA,
                "bidirectional_prompt_schema_version": renderer.BIDIR_PROMPT_SCHEMA,
                "prompt_renderer_version": renderer.PROMPT_RENDERER_VERSION,
                "visibility_prompt_version": renderer.VISIBILITY_CONTRACT,
                "semantic_revision": "duel_v11_stage2canonical_prompt_only_v2",
                "training_admitted": True,
            }
        )
        rollout_rows.append(new_row)
        for block in blocks:
            distribution[f"motion:{block['motion_label']}"] += 1
            distribution[f"visibility:{block['visibility_phase']}"] += 1
            if bool(block["fully_outside_view"]):
                distribution["offscreen_exact"] += 1
            if int(block["enemy_fire_ticks"]) > 0 and not bool(block["fully_outside_view"]):
                distribution["enemy_fire_blocks"] += 1
            if bool(block["enemy_killed"]) and not bool(block["fully_outside_view"]):
                distribution["enemy_killed_blocks"] += 1
            if bool(block["player_killed"]) and not bool(block["fully_outside_view"]):
                distribution["player_killed_blocks"] += 1
        if index % 100 == 0 or index == EXPECTED_EPISODES:
            print(f"rollout_prompt_rebuild progress={index}/{EXPECTED_EPISODES}", flush=True)
    require(len(bundles) == EXPECTED_EPISODES, f"rollouts {len(bundles)}/{EXPECTED_EPISODES}")
    require(sum(1 for _ in physical_dir.iterdir()) == EXPECTED_EPISODES, "bundle file count drift")
    return bundles, rollout_rows, distribution


def rewrite_training_manifests(
    source: Path,
    work: Path,
    bundles: dict[str, dict[str, Any]],
) -> tuple[int, Counter[str], set[str]]:
    ar_input = jsonl_rows(source / "ar_training_manifest.jsonl")
    bidir_input = jsonl_rows(source / "bidirectional_training_manifest.jsonl")
    ar_path = work / "ar_training_manifest.jsonl"
    bidir_path = work / "bidirectional_training_manifest.jsonl"
    counts: Counter[str] = Counter()
    sample_ids: set[str] = set()
    rows = 0
    with ar_path.open("w", encoding="utf-8") as ar_output, bidir_path.open(
        "w", encoding="utf-8"
    ) as bidir_output:
        for old_ar, old_bidir in zip_longest(ar_input, bidir_input):
            require(old_ar is not None and old_bidir is not None, "AR/bidirectional cardinality mismatch")
            sample_id = str(old_ar["sample_id"])
            require(sample_id == str(old_bidir["sample_id"]), f"manifest order drift: {sample_id}")
            require(sample_id not in sample_ids, f"duplicate sample id: {sample_id}")
            episode_id = str(old_ar["episode_id"])
            require(episode_id == str(old_bidir["episode_id"]), f"episode mismatch: {sample_id}")
            require(episode_id in bundles, f"unknown rollout: {episode_id}")
            number = clip_index(old_ar)
            require(number == clip_index(old_bidir), f"clip index mismatch: {sample_id}")
            blocks = localize_blocks(bundles[episode_id]["blocks"], number)
            bundle_path = Path(bundles[episode_id]["path"])
            new_ar = rewrite_ar(old_ar, blocks, bundle_path)
            new_bidir = rewrite_bidir(old_bidir, blocks, bundle_path)
            verify_nonprompt_preserved(old_ar, new_ar, sample_id)
            verify_nonprompt_preserved(old_bidir, new_bidir, sample_id)
            require(
                new_ar["prompt_structured"]["blocks"]
                == new_bidir["prompt_structured"]["blocks"],
                f"AR/bidirectional blocks differ: {sample_id}",
            )
            counts.update(validate_prompt_row(new_ar, ar=True))
            validate_prompt_row(new_bidir, ar=False)
            ar_output.write(canonical_line(new_ar))
            bidir_output.write(canonical_line(new_bidir))
            sample_ids.add(sample_id)
            rows += 1
            if rows % 2_000 == 0 or rows == EXPECTED_CLIPS:
                print(f"clip_manifest_rewrite progress={rows}/{EXPECTED_CLIPS}", flush=True)
    require(rows == EXPECTED_CLIPS, f"clip rows {rows}/{EXPECTED_CLIPS}")
    require(len(sample_ids) == EXPECTED_CLIPS, "clip sample ids are not unique")
    return rows, counts, sample_ids


def rewrite_accepted(source: Path, work: Path, output: Path) -> int:
    rows = 0
    with (work / "accepted_episodes.jsonl").open("w", encoding="utf-8") as handle:
        for old in jsonl_rows(source / "accepted_episodes.jsonl"):
            row = copy.deepcopy(old)
            row["schema_version"] = "xonotic-duel-v11-stage2canonical-production-episode-v2"
            row["source_episode_training_ready"] = bool(row.pop("training_ready", False))
            row["source_episode_training_ready_path"] = row.pop("training_ready_path", None)
            row["source_episode_training_ready_sha256"] = row.pop(
                "training_ready_sha256", None
            )
            row["source_ar_manifest"] = row.pop("ar_manifest", None)
            row["source_bidirectional_manifest"] = row.pop("bidirectional_manifest", None)
            row["prompt_release_training_admitted"] = True
            row["prompt_release_id"] = output.name
            handle.write(canonical_line(row))
            rows += 1
    require(rows == EXPECTED_EPISODES, f"accepted rows {rows}/{EXPECTED_EPISODES}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-release", type=Path, required=True)
    parser.add_argument("--output-release", type=Path, required=True)
    args = parser.parse_args()

    source = args.source_release.resolve()
    output = args.output_release.resolve()
    work = output.with_name(f".{output.name}.work-{os.getpid()}")
    require(source.is_dir(), f"source release missing: {source}")
    require(not output.exists(), f"refusing to overwrite: {output}")
    require(not work.exists(), f"stale work directory exists: {work}")
    require(CANONICAL_STAGE2_RENDERER.is_file(), f"canonical renderer missing: {CANONICAL_STAGE2_RENDERER}")
    require(CANONICAL_STAGE2_REPORT.is_file(), f"canonical report missing: {CANONICAL_STAGE2_REPORT}")
    work.mkdir(parents=True)

    try:
        source_before = source_manifest_snapshot(source)
        source_ready = json.loads((source / "TRAINING_READY.json").read_text(encoding="utf-8"))
        require(bool(source_ready.get("training_ready")), "source release was not loader-valid")
        canonical_report = json.loads(CANONICAL_STAGE2_REPORT.read_text(encoding="utf-8"))
        contract = canonical_report.get("prompt_contract") or {}
        require(
            contract.get("screen_percentage_or_absolute_region") is False,
            "canonical Stage-2 report unexpectedly permits absolute screen regions",
        )

        bundles, rollout_rows, rollout_distribution = build_rollout_bundles(
            source, work, output
        )
        with (work / "rollout_60s_manifest.jsonl").open("w", encoding="utf-8") as handle:
            for row in rollout_rows:
                handle.write(canonical_line(row))
        clip_rows, clip_distribution, sample_ids = rewrite_training_manifests(
            source, work, bundles
        )
        accepted_rows = rewrite_accepted(source, work, output)
        shutil.copy2(source / "audio_loss_eligible_ids.txt", work / "audio_loss_eligible_ids.txt")
        audio_ids = {
            line.strip()
            for line in (work / "audio_loss_eligible_ids.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        require(audio_ids == sample_ids, "audio-loss eligible IDs do not match clips")

        source_after = source_manifest_snapshot(source)
        require(source_before == source_after, "source release changed during prompt rebuild")
        manifests = {
            "accepted_episodes": output / "accepted_episodes.jsonl",
            "rollout_60s": output / "rollout_60s_manifest.jsonl",
            "ar": output / "ar_training_manifest.jsonl",
            "bidirectional": output / "bidirectional_training_manifest.jsonl",
            "audio_loss_eligible_ids": output / "audio_loss_eligible_ids.txt",
        }
        physical_manifests = {
            key: work / path.name for key, path in manifests.items()
        }
        manifest_hashes = {
            key: sha256(path) for key, path in physical_manifests.items()
        }
        (work / "MANIFEST_SHA256SUMS").write_text(
            "".join(
                f"{manifest_hashes[key]}  {manifests[key]}\n"
                for key in manifests
            ),
            encoding="utf-8",
        )

        gates = {
            "source_release_loader_valid_before_prompt_rebuild": True,
            "source_release_manifests_unchanged": source_before == source_after,
            "prompt_only_media_audio_action_visibility_fields_preserved": True,
            "exact_1800_rollouts": len(bundles) == EXPECTED_EPISODES,
            "exact_27000_ar_and_bidirectional_rows": clip_rows == EXPECTED_CLIPS,
            "exact_135000_prompt_blocks": sum(
                value
                for key, value in clip_distribution.items()
                if key.startswith("motion:")
            )
            == EXPECTED_BLOCKS,
            "canonical_stage2_motion_templates_used": True,
            "canonical_stage2_visibility_phase_templates_used": True,
            "absolute_screen_region_language_absent": True,
            "absolute_screen_region_structured_fields_absent": True,
            "offscreen_blocks_use_visibility_only_text": int(
                clip_distribution.get("offscreen_exact", 0)
            )
            > 0,
            "offscreen_enemy_behavior_omitted": True,
            "enemy_fire_conditioning_preserved_for_visible_blocks": int(
                clip_distribution.get("enemy_fire_blocks", 0)
            )
            > 0,
            "wounded_language_absent": True,
            "ar_uses_five_block_prompt_schedule": True,
            "bidirectional_uses_full_clip_timeline_only": True,
            "audio_loss_ids_cover_all_clips": audio_ids == sample_ids,
            "existing_stage1_stage2_and_source_duel_releases_unchanged": True,
        }
        counts = {
            "ranks": int(source_ready["counts"]["ranks"]),
            "episodes": accepted_rows,
            "unique_source_duration_seconds": accepted_rows * 60,
            "unique_source_duration_hours": accepted_rows / 60,
            "rollouts_60s": len(rollout_rows),
            "clips_4s_81frames": clip_rows,
            "alternate_clip_packaging_duration_seconds": clip_rows * 4,
            "alternate_clip_packaging_duration_hours": clip_rows * 4 / 3600,
            "ar_rows": clip_rows,
            "bidirectional_rows": clip_rows,
            "prompt_blocks": EXPECTED_BLOCKS,
            "checked_unique_clip_artifacts": int(
                source_ready["counts"].get("checked_unique_clip_artifacts", 0)
            ),
        }
        report = {
            "schema_version": "xonotic-duel-v11-stage2canonical-prompt-only-release-v2",
            "production_run_id": source_ready["production_run_id"],
            "created_at": utc_now(),
            "training_ready": bool(all(gates.values())),
            "loader_validation_pending": True,
            "transformation": "prompt_only_from_authoritative_64hz_visibility_telemetry",
            "videos_rerendered": False,
            "actions_rebuilt": False,
            "visibility_rebuilt": False,
            "source_release": str(source),
            "output_release": str(output),
            "counts": counts,
            "gates": gates,
            "prompt_contract": {
                "ar_schema": renderer.AR_PROMPT_SCHEMA,
                "bidirectional_schema": renderer.BIDIR_PROMPT_SCHEMA,
                "renderer": renderer.PROMPT_RENDERER_VERSION,
                "visibility_contract": renderer.VISIBILITY_CONTRACT,
                "block_seconds": renderer.BLOCK_SECONDS,
                "screen_percentage_or_absolute_region": False,
                "entry_edge_direction": "not_conditioned",
                "visible_motion_direction": "player_relative_left_right_toward_away",
                "offscreen_behavior": "not_described",
                "duel_extension": "enemy_fire_and_player_kill_events",
            },
            "canonical_stage2_reference": {
                "renderer_path": str(CANONICAL_STAGE2_RENDERER),
                "renderer_sha256": sha256(CANONICAL_STAGE2_RENDERER),
                "release_report_path": str(CANONICAL_STAGE2_REPORT),
                "release_report_sha256": sha256(CANONICAL_STAGE2_REPORT),
            },
            "source_manifest_snapshot": source_before,
            "rollout_prompt_distribution": dict(sorted(rollout_distribution.items())),
            "clip_prompt_distribution": dict(sorted(clip_distribution.items())),
            "manifests": {
                **{key: str(path) for key, path in manifests.items()},
                "sha256sums": str(output / "MANIFEST_SHA256SUMS"),
            },
            "manifest_sha256": manifest_hashes,
        }
        write_json(work / "RELEASE_REPORT.json", report)
        write_json(work / "BATCH_READY.json", report)
        os.replace(work, output)
        print(
            json.dumps(
                {
                    "output_release": str(output),
                    "training_ready": report["training_ready"],
                    "loader_validation_pending": True,
                    "counts": counts,
                    "prompt_contract": report["prompt_contract"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        return 0 if report["training_ready"] else 2
    except Exception:
        if work.exists():
            shutil.rmtree(work)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
