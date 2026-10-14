                      
"""Finalize the accepted Stage-1 supplement into an isolated training release.

The canonical Stage-1 release is never modified.  Supplement rows inherit the
canonical split of their source group so the combined release cannot introduce
train/test leakage.  Rejected design rows remain excluded and are documented.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "outputs/stage1_supplement_v1_prod_20260810"
DESIGN = ROOT / "manifests/design.jsonl"
BASE_RELEASE = Path(
    "./rigen_data/manifests/"
    "stage1_foundation_v5_ltx2_bidir_release_v3_prompted_camera_le6_20260731"
)
PROMPT_RELEASE = Path(
    "./rigen_data/manifests/"
    "stage1_foundation_v5_ltx2_bidir_release_v2_prompted_enemy_visibility_20260731"
)
DEFAULT_OUTPUT = Path(
    "./rigen_data/manifests/"
    "stage1_foundation_v5_ltx2_bidir_release_v4_supplement_20260811"
)
LTX_TRAINER_ROOT = Path("./packages/ltx-trainer/src")

ACTION_CHANNELS = [
    "j_left_x",
    "j_left_y",
    "j_right_x",
    "j_right_y",
    "right_trigger",
    "left_trigger",
    "right_thumb",
    "south",
    "west",
    "north",
]
BUTTON_COLUMNS = [
    "right_trigger",
    "left_trigger",
    "right_thumb",
    "south",
    "west",
    "north",
]
PARQUET_REQUIRED_COLUMNS = {
    "frame_index",
    "j_left",
    "j_right",
    "j_left_x",
    "j_left_y",
    "j_right_x",
    "j_right_y",
    "right_trigger",
    "left_trigger",
    "south",
    "west",
    "north",
}
CORE_FILES = (
    "PUBLICATION_READY.json",
    "SUPPLEMENT_ADMISSION.json",
    "episode.json",
    "qa.json",
    "model_actions.parquet",
    "frames.parquet",
    "video.mkv",
    "supplement_candidate_record.json",
)
PROMPT_FIELDS = (
    "prompt_text",
    "prompt_status",
    "prompt_schema_version",
    "prompt_renderer_version",
    "prompt_component_keys",
    "prompt_component_hashes",
)
GROUP_RE = re.compile(r"^s1v5f_(s1v5[a-z]+_\d+)_v(\d+)$")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def source_group(episode_id: str) -> tuple[str, int]:
    match = GROUP_RE.fullmatch(episode_id)
    if match is None:
        raise RuntimeError(f"unrecognized Stage-1 episode id: {episode_id}")
    return match.group(1), int(match.group(2))


def relative(path: Path, release_dir: Path) -> str:
    return os.path.relpath(path.resolve(), release_dir.resolve())


def verify_sha256sums(directory: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        path = directory / name.strip()
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"base release checksum mismatch: {path}")
        expected[name.strip()] = digest
    return expected


def canonical_split_map() -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    sources = (
        ("train_manifest.jsonl", "train"),
        ("test_manifest.jsonl", "test"),
        ("excluded_test_group_guard.jsonl", "test"),
    )
    for filename, split in sources:
        for row in load_jsonl(BASE_RELEASE / filename):
            episode_id = str(row.get("clip_id") or row.get("sample_id"))
            group, _ = source_group(episode_id)
            split_group_id = str(row["split_group_id"])
            prior = result.get(group)
            value = (split, split_group_id)
            if prior is not None and prior != value:
                raise RuntimeError(f"canonical split conflict for {group}: {prior} != {value}")
            result[group] = value
    return result


def prompt_pool() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    exact: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for filename in ("train_manifest.jsonl", "test_manifest.jsonl"):
        for row in load_jsonl(PROMPT_RELEASE / filename):
            episode_id = str(row["clip_id"])
            exact[episode_id] = row
            grouped[source_group(episode_id)[0]].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: source_group(str(row["clip_id"]))[1])
    return exact, grouped


def choose_prompt(
    source_episode_id: str,
    group: str,
    exact: dict[str, dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], str]:
    if source_episode_id in exact:
        return exact[source_episode_id], "exact_source_episode"
    donors = grouped.get(group) or []
    if not donors:
        raise RuntimeError(f"no prompt donor for source group {group}")
    _, source_variant = source_group(source_episode_id)
    donor = min(
        donors,
        key=lambda row: (
            abs(source_group(str(row["clip_id"]))[1] - source_variant),
            str(row["clip_id"]),
        ),
    )
    return donor, "same_source_group_static_scene"


def verify_candidate(record: dict[str, Any]) -> dict[str, Any]:
    episode_id = str(record["episode_id"])
    candidate = Path(record["episode_path"]).resolve()
    candidates_root = (PRODUCTION / "candidates").resolve()
    if candidates_root not in candidate.parents or candidate.name != episode_id:
        raise RuntimeError(f"unsafe candidate path for {episode_id}: {candidate}")
    if record.get("training_admitted") is not False:
        raise RuntimeError(f"source candidate unexpectedly admitted: {episode_id}")
    admission = record.get("admission") or {}
    qa = record.get("qa") or {}
    if admission.get("passed") is not True:
        raise RuntimeError(f"admission failed in accepted row: {episode_id}")
    if (
        int(qa.get("frames", -1)) != 320
        or int(qa.get("audio_samples", -1)) != 240000
        or abs(float(qa.get("mapping_rate", -1.0)) - 1.0) > 1e-9
        or int(qa.get("damage_count", -1)) != 0
        or "NVIDIA" not in str(qa.get("renderer", "")).upper()
    ):
        raise RuntimeError(f"accepted QA contract failed: {episode_id}")
    declared = record.get("package_sha256") or {}
    total_bytes = 0
    for name in CORE_FILES:
        path = candidate / name
        expected = declared.get(name)
        if not path.is_file() or not expected:
            raise RuntimeError(f"missing core artifact/hash: {episode_id}/{name}")
        if sha256_file(path) != expected:
            raise RuntimeError(f"core artifact hash mismatch: {episode_id}/{name}")
        total_bytes += path.stat().st_size

    action_path = candidate / "model_actions.parquet"
    parquet = pq.ParquetFile(action_path)
    columns = set(parquet.schema_arrow.names)
    if parquet.metadata.num_rows != 320 or not PARQUET_REQUIRED_COLUMNS <= columns:
        raise RuntimeError(f"model action schema mismatch: {episode_id}")
    read_columns = [
            "frame_index",
            "j_left",
            "j_right",
            "j_left_x",
            "j_left_y",
            "j_right_x",
            "j_right_y",
            "right_trigger",
            "left_trigger",
            "south",
            "west",
            "north",
    ]
    if "right_thumb" in columns:
        read_columns.append("right_thumb")
    table = pq.read_table(action_path, columns=read_columns)
    data = table.to_pydict()
                                                                               
                                                                               
                                                                              
    data.setdefault("right_thumb", [0] * 320)
    if data["frame_index"] != list(range(320)):
        raise RuntimeError(f"model action frame index mismatch: {episode_id}")
    flat_names = ("j_left_x", "j_left_y", "j_right_x", "j_right_y")
    flat_values: dict[str, np.ndarray] = {}
    for name in flat_names:
        values = np.asarray(data[name], dtype=np.float64)
        flat_values[name] = values
        if not np.isfinite(values).all() or float(np.max(np.abs(values), initial=0.0)) > 1.000001:
            raise RuntimeError(f"invalid joystick values: {episode_id}/{name}")
    for pair_name, x_name, y_name in (
        ("j_left", "j_left_x", "j_left_y"),
        ("j_right", "j_right_x", "j_right_y"),
    ):
        pairs = np.asarray(data[pair_name], dtype=np.float64)
        if pairs.shape != (320, 2) or not np.isfinite(pairs).all():
            raise RuntimeError(f"invalid joystick pair values: {episode_id}/{pair_name}")
        if float(np.max(np.abs(pairs), initial=0.0)) > 1.000001:
            raise RuntimeError(f"out-of-range joystick pair values: {episode_id}/{pair_name}")
        expected = np.stack((flat_values[x_name], flat_values[y_name]), axis=1)
        if not np.allclose(pairs, expected, rtol=0.0, atol=1e-6):
            raise RuntimeError(f"flat/pair joystick mismatch: {episode_id}/{pair_name}")
    for name in (
        "right_trigger",
        "left_trigger",
        "right_thumb",
        "south",
        "west",
        "north",
    ):
        values = set(float(value) for value in data[name])
        if not values <= {0.0, 1.0}:
            raise RuntimeError(f"non-binary button values: {episode_id}/{name}")
    fire_frames = int(sum(float(value) > 0.5 for value in data["right_trigger"]))
    if record["category"] == "wall_impact" and fire_frames <= 0:
        raise RuntimeError(f"wall impact lacks model fire input: {episode_id}")
    return {
        "episode_id": episode_id,
        "core_bytes": total_bytes,
        "fire_frames": fire_frames,
    }


def release_row(
    record: dict[str, Any],
    release_dir: Path,
    split_map: dict[str, tuple[str, str]],
    exact_prompts: dict[str, dict[str, Any]],
    grouped_prompts: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], str]:
    episode_id = str(record["episode_id"])
    source_episode_id = str(record["source_episode_id"])
    group = str(record["source_group_id"])
    if source_group(source_episode_id)[0] != group:
        raise RuntimeError(f"source group mismatch: {episode_id}")
    if group not in split_map:
        raise RuntimeError(f"source group absent from canonical release: {group}")
    split, split_group_id = split_map[group]
    prompt, prompt_policy = choose_prompt(
        source_episode_id, group, exact_prompts, grouped_prompts
    )
    candidate = Path(record["episode_path"]).resolve()
    camera = (record.get("admission") or {}).get("camera") or {}
    camera_max = max(
        float(camera.get("yaw_max_frame_step_deg", 0.0)),
        float(camera.get("pitch_max_frame_step_deg", 0.0)),
    )
    row: dict[str, Any] = {
        "schema_version": "xonotic-stage1-ltx2-bidir-release-v1",
        "sample_id": episode_id,
        "clip_id": episode_id,
        "source": "xonotic_stage1_supplement_v1",
        "game": "xonotic",
        "game_id": "xonotic",
        "split": split,
        "release_split": split,
        "split_group_id": split_group_id,
        "training_admitted": split == "train",
        "source_training_admitted": False,
        "source_release_split": str(record["supplement_split"]),
        "dataset_role": "foundation_no_enemy",
        "primary_bucket": str(record["category"]),
        "supplement_category": str(record["category"]),
        "supplement_design_split": str(record["supplement_split"]),
        "supplement_source_episode_id": source_episode_id,
        "supplement_source_group_id": group,
        "quota_assignment": "stage1_supplement_v1_final_accepted",
        "source_quota_assignment": "pending_supplement_final_audit",
        "map": str(record["map"]),
        "gametype": str(record["gametype"]),
        "weapon": str(record["weapon"]),
        "map_region_id": prompt.get("map_region_id"),
        "counterfactual_group_id": prompt.get("counterfactual_group_id"),
        "route_group_id": prompt.get("route_group_id"),
        "video_path": relative(candidate / "video.mkv", release_dir),
        "audio_path": relative(candidate / "video.mkv", release_dir),
        "action_path": relative(candidate / "model_actions.parquet", release_dir),
        "frames_path": relative(candidate / "frames.parquet", release_dir),
        "meta_path": relative(candidate / "episode.json", release_dir),
        "qa_path": relative(candidate / "qa.json", release_dir),
        "source_fps": 20.0,
        "source_frames": 100,
        "source_duration": 5.0,
        "video_source_fps": 64.0,
        "video_frame_count": 320,
        "video_offset_sec": 0.0,
        "audio_offset_sec": 0.0,
        "audio_duration_sec": 5.0,
        "audio_loss_eligible": True,
        "action_row_start": 0,
        "action_row_end": 320,
        "raw_action_chunk_size": 320,
        "standard_chunk_action_rows": 100,
        "temporal_resample_mode": "nearest_source_frame_v1",
        "temporal_index_formula": "round(target_frame_index * 64 / 20)",
        "button_resampling": "causal_run_max",
        "action_contract_version": "c25k-crossfps-legacy6-xonotic-v1",
        "action_channels": ACTION_CHANNELS,
        "button_columns": BUTTON_COLUMNS,
        "button_conditioning_mode": "crossfps_legacy6",
        "stage1_button_coverage": {
            "fire": "right_trigger",
            "jump": "south",
            "reload": "west",
        },
        "stage1_zero_filled_button_columns": [
            "left_trigger",
            "right_thumb",
            "north",
        ],
        "camera_filter_schema_version": "xonotic-stage1-prompted-camera-filtered-release-v1",
        "camera_filter_comparison": "less_than_or_equal",
        "camera_filter_threshold_deg": 6.0,
        "camera_max_frame_step_deg": camera_max,
        "prompt_source_clip_id": str(prompt["clip_id"]),
        "prompt_inheritance_policy": prompt_policy,
        "package_sha256": record["package_sha256"],
    }
    for field in PROMPT_FIELDS:
        row[field] = prompt.get(field)
    if not str(row.get("prompt_text") or "").strip():
        raise RuntimeError(f"empty prompt for {episode_id}")
    return row, prompt_policy


def choose_preflight_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("source") == "xonotic_stage1_supplement_v1":
            by_category[str(row["supplement_category"])].append(row)
    for category in sorted(by_category):
        values = sorted(by_category[category], key=lambda row: str(row["clip_id"]))
        selected.extend(values[:2])
    return selected


def loader_preflight(
    release_dir: Path,
    rows: list[dict[str, Any]],
    split: str,
) -> dict[str, Any]:
    sample_rows = choose_preflight_rows(rows)
    sample_manifest = release_dir / f"loader_preflight_{split}_samples.jsonl"
    write_jsonl(sample_manifest, sample_rows)
    sys.path.insert(0, str(LTX_TRAINER_ROOT))
    from ltx_trainer.config import ActionBindingConfig
    from ltx_trainer.datasets_online import CrossFPSAudioActionDataset

    binding = ActionBindingConfig(
        enabled=True,
        button_conditioning_mode="crossfps_legacy6",
    )
    dataset = CrossFPSAudioActionDataset(
        Path("."),
        manifest_path=sample_manifest,
        audio_loss_eligible_ids_path=None,
        target_width=832,
        target_height=480,
        target_num_frames=81,
        target_fps=20.0,
        target_audio_sample_rate=16000,
        source_name="xonotic_stage1_supplement_v1",
        random_temporal_crop=False,
        require_audio=True,
        action_binding_config=binding,
        action_binding_training=True,
    )
    details: list[dict[str, Any]] = []
    started = time.monotonic()
    wall_impact_fire_seen = False
    for index in range(len(dataset)):
        item_started = time.monotonic()
        sample = dataset[index]
        shapes = {
            "video": list(sample["video_pixels"].shape),
            "audio": list(sample["audio_waveform"].shape),
            "actions": list(sample["actions"].shape),
            "joystick": list(sample["action_joystick"].shape),
            "buttons": list(sample["action_buttons"].shape),
        }
        expected = {
            "video": [81, 3, 480, 832],
            "audio": [2, 64800],
            "actions": [81, 10],
            "joystick": [81, 4],
            "buttons": [81, 6],
        }
        if shapes != expected:
            raise RuntimeError(f"loader shape mismatch for {sample['sample_id']}: {shapes}")
        row = sample_rows[index]
        fire_frames = int((sample["action_buttons"][:, 0] > 0.5).sum().item())
        if row["supplement_category"] == "wall_impact":
            if fire_frames <= 0:
                raise RuntimeError(f"loader missed wall-impact fire pulses: {sample['sample_id']}")
            wall_impact_fire_seen = True
        details.append(
            {
                "sample_id": sample["sample_id"],
                "category": row["supplement_category"],
                "seconds": time.monotonic() - item_started,
                "fire_frames": fire_frames,
                "shapes": shapes,
            }
        )
    if any(row["supplement_category"] == "wall_impact" for row in sample_rows) and not wall_impact_fire_seen:
        raise RuntimeError("loader preflight did not exercise wall-impact fire")
    wall = time.monotonic() - started
    return {
        "schema_version": "xonotic-stage1-supplement-loader-preflight-v1",
        "split": split,
        "manifest": str(release_dir / f"{split}_manifest.jsonl"),
        "sample_manifest": str(sample_manifest),
        "samples": len(details),
        "sample_details": details,
        "wall_seconds": wall,
        "data_preflight_pass": True,
        "training_launch_ready": split == "train",
        "training_launch_blocker": None,
    }


def counts(rows: Iterable[dict[str, Any]], *keys: str) -> dict[str, int]:
    observed = Counter("/".join(str(row.get(key)) for key in keys) for row in rows)
    return dict(sorted(observed.items()))


def write_sha256sums(directory: Path) -> None:
    files = sorted(
        path for path in directory.iterdir() if path.is_file() and path.name != "SHA256SUMS"
    )
    payload = "".join(f"{sha256_file(path)}  {path.name}\n" for path in files)
    (directory / "SHA256SUMS").write_text(payload, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise RuntimeError(f"refuse to overwrite release: {output}")
    staging = output.parent / f".{output.name}.tmp.{os.getpid()}"
    if staging.exists():
        raise RuntimeError(f"staging path already exists: {staging}")

    status = json.loads((PRODUCTION / "STATUS.json").read_text())
    if status.get("state") == "running":
        raise RuntimeError("supplement production is still running")
    base_hashes = verify_sha256sums(BASE_RELEASE)
    design_rows = load_jsonl(DESIGN)
    accepted = load_jsonl(PRODUCTION / "manifests/accepted.jsonl")
    rejects = load_jsonl(PRODUCTION / "manifests/rejects.jsonl")
    accepted_ids = [str(row["episode_id"]) for row in accepted]
    if len(accepted_ids) != len(set(accepted_ids)):
        raise RuntimeError("duplicate accepted episode ids")
    design_by_id = {str(row["episode_id"]): row for row in design_rows}
    if not set(accepted_ids) <= set(design_by_id):
        raise RuntimeError("accepted rows outside frozen supplement design")
    rejected_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rejects:
        rejected_by_id[str(row["episode_id"])].append(row)
    missing = [row for row in design_rows if str(row["episode_id"]) not in set(accepted_ids)]
    for row in missing:
        history = rejected_by_id.get(str(row["episode_id"])) or []
        if not any(item.get("terminal") is True for item in history):
            raise RuntimeError(f"missing row lacks terminal rejection: {row['episode_id']}")

    print(f"verifying {len(accepted)} accepted supplement candidates", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        verified = list(pool.map(verify_candidate, accepted))
    split_map = canonical_split_map()
    exact_prompts, grouped_prompts = prompt_pool()
    supplement_rows: list[dict[str, Any]] = []
    prompt_policies = Counter()
    for record in sorted(accepted, key=lambda row: str(row["episode_id"])):
        row, policy = release_row(
            record,
            output,
            split_map,
            exact_prompts,
            grouped_prompts,
        )
        supplement_rows.append(row)
        prompt_policies[policy] += 1

    base_train = load_jsonl(BASE_RELEASE / "train_manifest.jsonl")
    base_test = load_jsonl(BASE_RELEASE / "test_manifest.jsonl")
    base_camera_excluded = load_jsonl(BASE_RELEASE / "excluded_camera_gt_threshold.jsonl")
    base_test_group_guard = load_jsonl(BASE_RELEASE / "excluded_test_group_guard.jsonl")
    supplement_train = [row for row in supplement_rows if row["split"] == "train"]
    supplement_test = [row for row in supplement_rows if row["split"] == "test"]
    train_rows = [*base_train, *supplement_train]
    test_rows = [*base_test, *supplement_test]
    train_ids = {str(row["clip_id"]) for row in train_rows}
    test_ids = {str(row["clip_id"]) for row in test_rows}
    if len(train_ids) != len(train_rows) or len(test_ids) != len(test_rows):
        raise RuntimeError("duplicate clip ids in combined release")
    if train_ids & test_ids:
        raise RuntimeError("train/test clip-id overlap")
    train_groups = {str(row["split_group_id"]) for row in train_rows}
    test_groups = {str(row["split_group_id"]) for row in test_rows}
    if train_groups & test_groups:
        raise RuntimeError("train/test split-group leakage")
    if any(not str(row.get("prompt_text") or "").strip() for row in train_rows + test_rows):
        raise RuntimeError("combined release contains empty prompts")

    staging.mkdir(parents=False)
    write_jsonl(staging / "train_manifest.jsonl", train_rows)
    write_jsonl(staging / "test_manifest.jsonl", test_rows)
    write_jsonl(staging / "supplement_manifest.jsonl", supplement_rows)
    excluded_rows = []
    for row in missing:
        episode_id = str(row["episode_id"])
        history = rejected_by_id[episode_id]
        latest = history[-1]
        terminal_history = [item for item in history if item.get("terminal") is True]
        last = terminal_history[-1]
        excluded_rows.append(
            {
                "episode_id": episode_id,
                "supplement_split": row["supplement_split"],
                "category": row["primary_bucket"],
                "map": row["map"],
                "weapon": row["weapon"],
                "attempts": len(history),
                "terminal_attempts": len(terminal_history),
                "last_reason": last["reason"],
                "last_detail_sha256": hashlib.sha256(str(last["detail"]).encode()).hexdigest(),
                "last_rejected_utc": last["rejected_utc"],
                "latest_attempt_reason": latest["reason"],
                "latest_attempt_terminal": latest.get("terminal") is True,
                "latest_attempt_rejected_utc": latest["rejected_utc"],
                "terminal": True,
            }
        )
    write_jsonl(staging / "supplement_excluded_terminal.jsonl", excluded_rows)
                                                                                
                                                                                 
    for filename in (
        "excluded_camera_gt_threshold.jsonl",
        "excluded_test_group_guard.jsonl",
        "excluded_test_group_guard_ids.txt",
    ):
        shutil.copy2(BASE_RELEASE / filename, staging / filename)
    (staging / "train_episode_ids.txt").write_text(
        "".join(str(row["clip_id"]) + "\n" for row in train_rows), encoding="utf-8"
    )
    (staging / "test_episode_ids.txt").write_text(
        "".join(str(row["clip_id"]) + "\n" for row in test_rows), encoding="utf-8"
    )
    (staging / "audio_loss_eligible_train_ids.txt").write_text(
        "".join(str(row["clip_id"]) + "\n" for row in train_rows), encoding="utf-8"
    )

    train_preflight = loader_preflight(staging, train_rows, "train")
    test_preflight = loader_preflight(staging, test_rows, "test")
    (staging / "PREFLIGHT_TRAIN.json").write_text(
        json.dumps(train_preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (staging / "PREFLIGHT_TEST.json").write_text(
        json.dumps(test_preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    design_counts = Counter(
        (str(row["supplement_split"]), str(row["primary_bucket"]))
        for row in design_rows
    )
    accepted_counts = Counter(
        (str(row["supplement_split"]), str(row["category"]))
        for row in accepted
    )
    shortfall = {
        f"{split}/{category}": design_counts[split, category] - accepted_counts[split, category]
        for split, category in sorted(design_counts)
    }
    report = {
        "schema_version": "xonotic-stage1-foundation-v5-supplement-release-v1",
        "status": "training_ready",
        "training_ready": True,
        "source": {
            "base_release": str(BASE_RELEASE),
            "base_release_sha256sums": base_hashes,
            "supplement_design": str(DESIGN),
            "supplement_design_sha256": sha256_file(DESIGN),
            "supplement_accepted_manifest": str(PRODUCTION / "manifests/accepted.jsonl"),
            "supplement_accepted_manifest_sha256": sha256_file(
                PRODUCTION / "manifests/accepted.jsonl"
            ),
            "supplement_status": status,
        },
        "counts": {
            "base_train": len(base_train),
            "base_test": len(base_test),
            "base_camera_excluded": len(base_camera_excluded),
            "base_test_group_guard_excluded": len(base_test_group_guard),
            "supplement_design": len(design_rows),
            "supplement_accepted": len(accepted),
            "supplement_terminal_excluded": len(missing),
            "supplement_release_train": len(supplement_train),
            "supplement_release_test": len(supplement_test),
            "combined_train": len(train_rows),
            "combined_test": len(test_rows),
        },
        "supplement": {
            "accepted_by_design_split_category": counts(
                accepted, "supplement_split", "category"
            ),
            "release_by_canonical_split_category": counts(
                supplement_rows, "split", "supplement_category"
            ),
            "terminal_excluded_by_design_split_category": counts(
                excluded_rows, "supplement_split", "category"
            ),
            "terminal_excluded_by_reason": counts(excluded_rows, "last_reason"),
            "design_shortfall": shortfall,
            "source_commit_counts": counts(accepted, "source_commit"),
            "offline_acceleration_counts": counts(
                accepted, "category", "offline_demo_acceleration"
            ),
            "prompt_inheritance_counts": dict(sorted(prompt_policies.items())),
            "core_artifacts_verified": len(verified),
            "core_bytes_verified": sum(int(row["core_bytes"]) for row in verified),
        },
        "split": {
            "policy": "inherit_canonical_stage1_v3_source_group_split",
            "train_test_clip_overlap": 0,
            "train_test_split_group_overlap": 0,
            "supplement_design_split_preserved_as_metadata": True,
        },
        "action": {
            "button_conditioning_mode": "crossfps_legacy6",
            "button_resampling": "causal_run_max",
            "continuous_joystick_dim": 4,
            "button_dim": 6,
            "model_action_dim": 10,
            "wall_impact_fire_pulse_loader_check": True,
        },
        "validation": {
            "all_accepted_core_hashes_verified": True,
            "all_accepted_admission_passed": True,
            "all_accepted_damage_count_zero": True,
            "all_prompts_complete": True,
            "all_paths_present": True,
            "loader_train_preflight_pass": train_preflight["data_preflight_pass"],
            "loader_test_preflight_pass": test_preflight["data_preflight_pass"],
        },
    }
    (staging / "RELEASE_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    readme = f"""# Xonotic Stage-1 foundation v5 plus supplement release

Status: **training ready**.

- Base release is unchanged: {len(base_train)} train / {len(base_test)} test.
- Accepted supplement: {len(accepted)} of {len(design_rows)} designed rows.
- Terminal QC exclusions: {len(missing)}; no QC gate was relaxed.
- Combined release: {len(train_rows)} train / {len(test_rows)} test.
- Supplement rows inherit their source group's canonical Stage-1 split.
- Train/test clip and split-group overlap are both zero.
- Every accepted supplement core package hash and action schema was verified.
- Real CrossFPS loader preflights passed at 832x480, 81 frames, 20 fps,
  16 kHz stereo audio, and 10-dimensional legacy6 actions.
- Short button pulses use `causal_run_max` so wall-impact fire labels survive
  64 Hz to 20 Hz action resampling.
"""
    (staging / "README.md").write_text(readme, encoding="utf-8")
    write_sha256sums(staging)
    os.rename(staging, output)
    print(json.dumps({"output": str(output), **report["counts"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
