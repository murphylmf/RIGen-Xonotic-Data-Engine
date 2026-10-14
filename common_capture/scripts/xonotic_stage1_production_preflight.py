                      
"""Restartable Stage-1 production-pipeline preflight with human review.

This bounded split is intentionally not training data and is not a formal
batch launcher.  It proves the production control flow:

planned -> capture-valid candidate -> realized rebucketing -> human review

Only structural/media/telemetry failures are hard rejects.  Semantic drift is
preserved as a candidate with explicit soft flags.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import fcntl
import hashlib
import html
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              
import xonotic_motion_distance_pilot as motion              
import xonotic_stage1_review as review              


SPLIT = "v2_stage1_production_preflight"
ROOT = capture.ROOT
PREFLIGHT_ROOT = ROOT / SPLIT
SCENARIOS_PATH = ROOT / f"configs/{SPLIT}_scenarios.jsonl"
CANDIDATES_PATH = PREFLIGHT_ROOT / "manifests/candidates.jsonl"
HARD_REJECTS_PATH = PREFLIGHT_ROOT / "manifests/hard_rejects.jsonl"
QUEUE_EVENTS_PATH = PREFLIGHT_ROOT / "manifests/queue_events.jsonl"
REVIEW_DECISIONS_PATH = PREFLIGHT_ROOT / "manifests/review_decisions.jsonl"
ANNOTATIONS_PATH = PREFLIGHT_ROOT / "manifests/posthoc_annotations.jsonl"
GEOMETRY_AUDIT_PATH = PREFLIGHT_ROOT / "CAMERA_COLLISION_AUDIT.json"
SUMMARY_PATH = PREFLIGHT_ROOT / "PREFLIGHT_SUMMARY.json"
REPORT_PATH = PREFLIGHT_ROOT / "PRODUCTION_PREFLIGHT_REPORT.md"
PREVIEW_ROOT = ROOT / "previews/stage1_production_preflight"
DEFAULT_COUNT = 33

                                                                             
                                                                        
                                           
SOURCE_IDS = (
    "s1review_001",
    "s1review_003",
    "s1review_016",
    "s1review_024",
    "s1review_007",
    "s1review_015",
    "s1review_019",
    "s1review_031",
    "s1review_011",
    "s1review_026",
    "s1review_027",
    "s1review_042",
    "s1review_034",
    "s1review_044",
    "s1review_047",
    "s1review_048",
                                                                         
                                                                            
                                                              
    "s1review_002",
    "s1review_004",
    "s1review_005",
    "s1review_010",
    "s1review_012",
    "s1review_014",
    "s1review_025",
    "s1review_046",
    "s1review_028",
    "s1review_049",
    "s1review_040",
    "s1review_057",
    "s1review_006",
    "s1review_008",
    "s1review_021",
    "s1review_032",
                                                                           
                                                                              
    "s1review_038",
)

RETRYABLE_REASONS = {
    "dedicated_start_failed",
    "dedicated_health_timeout",
    "live_client_failed",
    "live_artifact_missing",
    "action_schedule_not_loaded",
    "demo_not_completed",
    "offline_render_failed",
    "raw_video_count",
    "render_artifact_missing",
    "x264_encode_failed",
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    atomic_text(
        path,
        "".join(capture.canonical_json(row) + "\n" for row in rows),
    )


def blockage_soft_flag(blockage: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": "trajectory:sustained_command_blockage",
        "expected": (
            f"<{capture.BLOCKED_MIN_CONSECUTIVE_TICKS} consecutive ticks"
        ),
        "actual": {
            "longest_ticks": blockage["longest_blocked_ticks"],
            "longest_seconds": blockage["longest_blocked_seconds"],
        },
        "disposition": "human_review",
        "note": (
            "Large movement commands made little progress along their "
            "world-space direction. This is a high-confidence wall/corner "
            "stuck inference; no contact normal is logged yet."
        ),
    }


def blockage_training_exclusion_flag(
    blockage: dict[str, Any],
) -> dict[str, Any]:
    excluded_windows = [
        {
            "start_tick": window["start_tick"],
            "end_tick": window["end_tick"],
            "ticks": window["ticks"],
            "direction_class": window["direction_class"],
            "mean_command_angle_from_forward_deg": window[
                "mean_command_angle_from_forward_deg"
            ],
            "off_forward_cone_fraction": window[
                "off_forward_cone_fraction"
            ],
        }
        for window in blockage["windows"]
        if window.get("foundation_training_excluded")
    ]
    return {
        "code": (
            "trajectory:off_forward_cone_sustained_blockage"
        ),
        "expected": (
            "No lateral/backward blockage lasting at least "
            f"{capture.BLOCKED_MIN_CONSECUTIVE_TICKS} ticks"
        ),
        "actual": excluded_windows,
        "disposition": "training_excluded",
        "note": (
            "Sustained obstruction occurred while the intended movement "
            "direction was lateral/backward or otherwise outside the "
            "+/-45 degree forward cone. The causal obstacle is ambiguous "
            "in the rendered view, so this episode is excluded from "
            "foundation-dynamics training."
        ),
    }


def annotation_signature(annotation: dict[str, Any]) -> str:
    """Stable comparison that deliberately ignores scan time."""
    return capture.canonical_json(
        {
            "episode_id": annotation["episode_id"],
            "source_package_sha256": annotation[
                "source_package_sha256"
            ],
            "camera_continuity": annotation["camera_continuity"],
            "movement_blockage": annotation["movement_blockage"],
            "hard_invalidated": annotation["hard_invalidated"],
            "hard_invalidation_reasons": annotation[
                "hard_invalidation_reasons"
            ],
            "training_excluded": annotation.get(
                "training_excluded", False
            ),
            "training_exclusion_reasons": annotation.get(
                "training_exclusion_reasons", []
            ),
            "soft_flag_codes": annotation["soft_flag_codes"],
        }
    )


def load_annotations() -> dict[str, dict[str, Any]]:
    return {
        row["episode_id"]: row
        for row in capture.load_jsonl(ANNOTATIONS_PATH)
    }


def scan_candidate_geometry(
    row: dict[str, Any],
) -> dict[str, Any]:
    episode = Path(row["episode_path"])
    frames = pd.read_parquet(episode / "frames.parquet")
    states = pd.read_parquet(episode / "states.parquet")
    camera_metrics = capture.first_person_camera_metrics(frames, states)
    blockage_metrics = capture.movement_blockage_metrics(states)
    hard_invalidated = not camera_metrics["passed"]
    training_excluded = bool(
        blockage_metrics["training_exclusion_recommended"]
    )
    exclusion_code = (
        "trajectory:off_forward_cone_sustained_blockage"
    )
    flag_codes = []
    if blockage_metrics["high_confidence"]:
        flag_codes.append("trajectory:sustained_command_blockage")
    if training_excluded:
        flag_codes.append(exclusion_code)
    return {
        "schema_version": "xonotic-posthoc-camera-collision-v1",
        "episode_id": row["episode_id"],
        "scanned_utc": capture.utc_now(),
        "source_package_sha256": {
            "frames.parquet": row["package_sha256"].get(
                "frames.parquet"
            ),
            "states.parquet": row["package_sha256"].get(
                "states.parquet"
            ),
        },
        "camera_continuity": camera_metrics,
        "movement_blockage": blockage_metrics,
        "hard_invalidated": hard_invalidated,
        "hard_invalidation_reasons": (
            ["first_person_camera_continuity"]
            if hard_invalidated
            else []
        ),
        "training_excluded": training_excluded,
        "training_exclusion_reasons": (
            [exclusion_code] if training_excluded else []
        ),
        "soft_flag_codes": flag_codes,
        "training_admitted": False,
    }


def effective_candidate_rows() -> list[dict[str, Any]]:
    """Overlay post-hoc findings without rewriting published manifests."""
    annotations = load_annotations()
    effective: list[dict[str, Any]] = []
    for base in capture.load_jsonl(CANDIDATES_PATH):
        row = copy.deepcopy(base)
        annotation = annotations.get(row["episode_id"])
        row["manifest_status"] = base["status"]
        row["capture_valid"] = True
        row["selection_eligible"] = True
        if annotation is None:
            if base["status"] == "training_excluded":
                row["selection_eligible"] = False
            effective.append(row)
            continue

        row["posthoc_annotation"] = annotation
        row["qa"]["camera_continuity"] = annotation[
            "camera_continuity"
        ]
        row["qa"]["movement_blockage"] = annotation[
            "movement_blockage"
        ]
        blockage = annotation["movement_blockage"]
        if blockage["high_confidence"]:
            codes = {
                flag["code"] for flag in row.get("soft_flags", [])
            }
            if "trajectory:sustained_command_blockage" not in codes:
                row.setdefault("soft_flags", []).append(
                    blockage_soft_flag(blockage)
                )
        if annotation["training_excluded"]:
            codes = {
                flag["code"] for flag in row.get("soft_flags", [])
            }
            exclusion_code = (
                "trajectory:off_forward_cone_sustained_blockage"
            )
            if exclusion_code not in codes:
                row.setdefault("soft_flags", []).append(
                    blockage_training_exclusion_flag(blockage)
                )

        if annotation["hard_invalidated"]:
            row["capture_valid"] = False
            row["selection_eligible"] = False
            row["status"] = "hard_invalidated"
            row["qa"]["hard_gates_pass"] = False
            row["hard_invalidation"] = {
                "reasons": annotation["hard_invalidation_reasons"],
                "disposition": "never_admit_to_training",
                "raw_retained_for_audit": True,
            }
        elif annotation["training_excluded"]:
            row["selection_eligible"] = False
            row["status"] = "training_excluded"
            row["training_exclusion"] = {
                "reasons": annotation[
                    "training_exclusion_reasons"
                ],
                "disposition": "exclude_from_foundation_training",
                "raw_retained_for_audit": True,
            }
        elif row.get("soft_flags"):
            row["status"] = "needs_review"
        else:
            row["status"] = "auto_keep_candidate"
        effective.append(row)
    return effective


def append_locked(
    path: Path,
    row: dict[str, Any],
    unique_field: str | None = None,
) -> bool:
    """Append with a filesystem lock; optionally enforce exactly-once key."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        if unique_field is not None:
            handle.seek(0)
            target = row.get(unique_field)
            for line in handle:
                if line.strip() and json.loads(line).get(unique_field) == target:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    return False
        handle.seek(0, os.SEEK_END)
        handle.write(capture.canonical_json(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def queue_event(
    episode_id: str,
    state: str,
    attempt_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    append_locked(
        QUEUE_EVENTS_PATH,
        {
            "schema_version": "xonotic-production-preflight-queue-event-v1",
            "episode_id": episode_id,
            "attempt_id": attempt_id,
            "state": state,
            "detail": detail or {},
            "created_utc": capture.utc_now(),
        },
    )


def source_scenarios() -> list[dict[str, Any]]:
    if not review.SCENARIOS_PATH.is_file():
        raise capture.CaptureFailure(
            "source_scenarios_missing", str(review.SCENARIOS_PATH)
        )
    rows = {
        row["episode_id"]: row
        for row in capture.load_jsonl(review.SCENARIOS_PATH)
    }
    missing = sorted(set(SOURCE_IDS) - set(rows))
    if missing:
        raise capture.CaptureFailure(
            "preflight_source_rows_missing", ",".join(missing)
        )
    return [rows[episode_id] for episode_id in SOURCE_IDS]


def transform_scenario(
    source: dict[str, Any], ordinal: int
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    source_episode_id = row["episode_id"]
    episode_id = f"s1prodpf_{ordinal:03d}"
    row.update(
        {
            "episode_id": episode_id,
            "source_episode_id": source_episode_id,
            "source_split": source["split"],
            "split": SPLIT,
            "training_stage": "stage1_production_preflight_review_only",
            "acceptance_policy": capture.TIERED_REVIEW_POLICY,
            "fixed_variant_index": 0,
            "formal_collection_authorized": False,
            "human_review_required_before_training": True,
            "data_spec_sha256": capture.sha256_file(
                ROOT / "XONOTIC_DATA_SPEC_V2.md"
            ),
        }
    )
    row["seed"] = 12_000_000 + ordinal
    row["anchor_id"] = str(row["anchor_id"]).replace(
        source_episode_id, episode_id
    )
    return row


def generated_scenarios(count: int) -> list[dict[str, Any]]:
    if not 1 <= count <= len(SOURCE_IDS):
        raise capture.CaptureFailure(
            "invalid_preflight_count",
            f"count={count} available={len(SOURCE_IDS)}",
        )
    rows = [
        transform_scenario(source, ordinal)
        for ordinal, source in enumerate(source_scenarios()[:count], 1)
    ]
    if len({row["episode_id"] for row in rows}) != len(rows):
        raise AssertionError("duplicate preflight episode IDs")
    return rows


def command_generate(args: argparse.Namespace) -> int:
    rows = generated_scenarios(args.count)
    if SCENARIOS_PATH.exists():
        existing = capture.load_jsonl(SCENARIOS_PATH)
        if existing == rows:
            added: list[dict[str, Any]] = []
        elif (
            len(existing) < len(rows)
            and existing == rows[: len(existing)]
        ):
            added = rows[len(existing) :]
            write_jsonl(SCENARIOS_PATH, rows)
            for row in added:
                queue_event(row["episode_id"], "planned")
        else:
            raise capture.CaptureFailure(
                "refuse_overwrite_scenario_plan", str(SCENARIOS_PATH)
            )
    else:
        write_jsonl(SCENARIOS_PATH, rows)
        added = rows
        for row in rows:
            queue_event(row["episode_id"], "planned")
    plan = {
        "schema_version": "xonotic-stage1-production-preflight-plan-v1",
        "created_utc": capture.utc_now(),
        "split": SPLIT,
        "formal_collection_authorized": False,
        "count": len(rows),
        "roles": dict(Counter(row["dataset_role"] for row in rows)),
        "buckets": dict(Counter(row["primary_bucket"] for row in rows)),
        "maps": dict(Counter(row["map"] for row in rows)),
        "weapons": dict(Counter(row["weapon"] for row in rows)),
        "source_episode_ids": [
            row["source_episode_id"] for row in rows
        ],
        "new_rows_added": len(added),
    }
    atomic_json(PREFLIGHT_ROOT / "SAMPLING_PLAN.json", plan)
    print(str(SCENARIOS_PATH))
    print(capture.canonical_json(plan))
    return 0


def add_flag(
    flags: list[dict[str, Any]],
    code: str,
    expected: Any,
    actual: Any,
    note: str,
) -> None:
    flags.append(
        {
            "code": code,
            "expected": expected,
            "actual": actual,
            "disposition": "human_review",
            "note": note,
        }
    )


def classify_semantics(
    row: dict[str, Any],
    qa: dict[str, Any],
    relation: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Rebucket from realized telemetry without deleting valid media."""
    flags: list[dict[str, Any]] = []
    for gate_name, passed in qa.get("soft_gates", {}).items():
        if not passed:
            add_flag(
                flags,
                f"soft_qa:{gate_name}",
                True,
                False,
                "Capture is structurally valid; review this research contract.",
            )

    targets = row["review_targets"]
    realized = {
        "net_displacement_bin": metrics["net_displacement_bin"],
        "yaw_range_bin": metrics["yaw_range_bin"],
        "pitch_range_bin": metrics["pitch_range_bin"],
        "target_relation": relation["actual_target_relation"],
        "distance_bin": relation.get("actual_distance_bin"),
    }
    for name in (
        "net_displacement_bin",
        "yaw_range_bin",
        "pitch_range_bin",
    ):
        expected = targets[name]
        if realized[name] != expected:
            add_flag(
                flags,
                f"rebucket:{name}",
                expected,
                realized[name],
                "Use the realized bin; do not retry only to force the target bin.",
            )
    if row["enemy_present"]:
        for name in ("target_relation", "distance_bin"):
            expected = targets[name]
            if expected and realized[name] != expected:
                add_flag(
                    flags,
                    f"rebucket:{name}",
                    expected,
                    realized[name],
                    "Enemy relation is assigned from render/state telemetry.",
                )
        if qa["events"]["fire_count"]:
            add_flag(
                flags,
                "role_conflict:distractor_fire",
                0,
                qa["events"]["fire_count"],
                "Keep for inspection but do not auto-admit as distractor dynamics.",
            )
    if qa["events"]["damage_count"]:
        add_flag(
            flags,
            "role_conflict:foundation_damage",
            0,
            qa["events"]["damage_count"],
            "Candidate may be useful elsewhere but conflicts with Stage-1 foundation role.",
        )
    if relation.get("actual_distance_bin") in {
        "contact_lt64",
        "unknown_nonfinite",
        "beyond_declared_bins",
    }:
        add_flag(
            flags,
            "distance_edge_case",
            "declared_distance_bin",
            relation.get("actual_distance_bin"),
            "Inspect geometry before deciding whether to extend the taxonomy.",
        )
    blockage = qa.get("telemetry", {}).get("movement_blockage", {})
    if blockage.get("high_confidence"):
        flags.append(blockage_soft_flag(blockage))
    if blockage.get("training_exclusion_recommended"):
        flags.append(blockage_training_exclusion_flag(blockage))
        status = "training_excluded"
    else:
        status = "needs_review" if flags else "auto_keep_candidate"
    return status, flags, realized


def update_package_semantics(
    package: Path,
    row: dict[str, Any],
    relation: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[dict[str, Any], str, list[dict[str, Any]], dict[str, Any]]:
    qa_path = package / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    status, flags, realized = classify_semantics(
        row, qa, relation, metrics
    )
    qa["target_relation"] = relation
    qa["motion"] = metrics
    qa["semantic_review"] = {
        "status": status,
        "soft_flags": flags,
        "intended_labels": row["review_targets"],
        "realized_labels": realized,
        "human_decision": "pending",
        "training_admitted": False,
    }
    qa["review_status"] = status
    qa["training_admitted"] = False
    atomic_json(qa_path, qa)

    episode_path = package / "episode.json"
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    episode.update(
        {
            "actual_target_relation": relation,
            "actual_motion": metrics,
            "realized_labels": realized,
            "semantic_soft_flags": flags,
            "review_status": status,
            "human_decision": "pending",
            "training_admitted": False,
        }
    )
    atomic_json(episode_path, episode)
    return qa, status, flags, realized


def copy_file_hashed_once(source: Path, destination: Path) -> tuple[str, int]:
    """Copy to CPFS and calculate SHA256 in the same source read."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as source_handle, destination.open("xb") as target:
        for block in iter(lambda: source_handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
            target.write(block)
            size += len(block)
        target.flush()
        os.fsync(target.fileno())
    shutil.copystat(source, destination)
    return digest.hexdigest(), size


def stage_mapping_hashed_once(
    files: list[tuple[Path, Path]], destination: Path
) -> tuple[Path, dict[str, str], int, float]:
    if destination.exists():
        raise capture.CaptureFailure("refuse_overwrite", str(destination))
    temporary = destination.parent / f".{destination.name}.tmp"
    if temporary.exists():
        raise capture.CaptureFailure("stale_publish_temp", str(temporary))
    temporary.mkdir(parents=True)
    hashes: dict[str, str] = {}
    total_bytes = 0
    started = time.monotonic()
    try:
        for source, relative in files:
            digest, size = copy_file_hashed_once(
                source, temporary / relative
            )
            hashes[str(relative)] = digest
            total_bytes += size
    except Exception:
                                                                        
                                                   
        raise
    return temporary, hashes, total_bytes, time.monotonic() - started


def copy_mapping_hashed_once(
    files: list[tuple[Path, Path]], destination: Path
) -> tuple[dict[str, str], int, float]:
    temporary, hashes, total_bytes, elapsed = (
        stage_mapping_hashed_once(files, destination)
    )
    os.rename(temporary, destination)
    return hashes, total_bytes, elapsed


def tree_files(source: Path) -> list[tuple[Path, Path]]:
    return [
        (path, path.relative_to(source))
        for path in sorted(source.rglob("*"))
        if path.is_file()
    ]


def first_file(stage: Path, pattern: str) -> Path | None:
    rows = sorted(stage.glob(pattern))
    return rows[0] if rows else None


def raw_artifacts(stage: Path) -> list[tuple[Path, Path]]:
    """Retain useful raw evidence without duplicated QC/userdir payloads."""
    mapping: list[tuple[str, Path | None]] = [
        ("raw_capture.avi", first_file(stage, "client_user/data/video/*.avi")),
        ("demo.dem", first_file(stage, "client_user/data/demos/*.dem")),
        ("actions_requested.csv", stage / "actions_requested.csv"),
        ("actions_engine.csv", stage / "live/actions_engine.csv"),
        (
            "server.jsonl",
            stage / "server_user/data/data/capture/server.jsonl",
        ),
        ("frames_engine.csv", stage / "render/frames_engine.csv"),
        (
            "audio_events_engine.csv",
            stage / "render/audio_events_engine.csv",
        ),
        ("ATTEMPT.json", stage / "ATTEMPT.json"),
        ("LIVE_PRECHECK.json", stage / "LIVE_PRECHECK.json"),
        ("server_console.log", stage / "server_console.log"),
        ("client_live_console.log", stage / "client_live_console.log"),
        ("client_render_console.log", stage / "client_render_console.log"),
        ("ffmpeg_encode.log", stage / "ffmpeg_encode.log"),
    ]
    return [
        (path, Path(name))
        for name, path in mapping
        if path is not None and path.is_file()
    ]


def base_candidate_record(
    row: dict[str, Any],
    attempt_id: str,
    qa: dict[str, Any],
    status: str,
    flags: list[dict[str, Any]],
    realized: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "xonotic-stage1-production-preflight-candidate-v1",
        "episode_id": row["episode_id"],
        "source_episode_id": row["source_episode_id"],
        "attempt_id": attempt_id,
        "split": SPLIT,
        "formal_collection_authorized": False,
        "dataset_role": row["dataset_role"],
        "primary_bucket": row["primary_bucket"],
        "category": row["category"],
        "map": row["map"],
        "weapon": row["weapon"],
        "enemy_present": row["enemy_present"],
        "enemy_model": row.get("enemy_model", ""),
        "enemy_skin": row.get("enemy_skin", 0),
        "intended_labels": row["review_targets"],
        "realized_labels": realized,
        "motion": qa["motion"],
        "target_relation": qa["target_relation"],
        "status": status,
        "soft_flags": flags,
        "human_decision": "pending",
        "training_admitted": False,
        "qa": {
            "hard_gates_pass": all(qa["hard_gates"].values()),
            "soft_gates": qa["soft_gates"],
            "renderer": qa["runtime"]["renderer"],
            "frames": qa["video"]["frames"],
            "audio_samples": qa["audio"]["samples_per_channel"],
            "mapping_rate": qa["mapping"]["success_rate"],
            "audio_onset_max_ms": qa["audio"]["max_onset_error_ms"],
            "event_linkage": qa["events"]["linkage_rate"],
            "damage_count": qa["events"]["damage_count"],
            "fire_count": qa["events"]["fire_count"],
        },
        "runtime": qa["runtime"],
        "captured_utc": capture.utc_now(),
    }


def publish_candidate(
    row: dict[str, Any],
    result: dict[str, Any],
    qa: dict[str, Any],
    status: str,
    flags: list[dict[str, Any]],
    realized: dict[str, Any],
) -> dict[str, Any]:
    stage = Path(result["stage"])
    package = stage / "package"
    attempt_id = result["attempt_id"]
    episode_destination = PREFLIGHT_ROOT / "episodes" / row["episode_id"]
    raw_destination = PREFLIGHT_ROOT / "raw" / attempt_id
    record = base_candidate_record(
        row, attempt_id, qa, status, flags, realized
    )
    atomic_json(package / "candidate_record.json", record)

    (
        package_temporary,
        package_hashes,
        package_bytes,
        package_seconds,
    ) = stage_mapping_hashed_once(
        tree_files(package), episode_destination
    )
    raw_temporary, raw_hashes, raw_bytes, raw_seconds = (
        stage_mapping_hashed_once(
            raw_artifacts(stage), raw_destination
        )
    )
                                                                          
                                                                          
                                                                             
    os.rename(raw_temporary, raw_destination)
    os.rename(package_temporary, episode_destination)
    manifest = {
        **record,
        "episode_path": str(episode_destination),
        "raw_path": str(raw_destination),
        "package_sha256": package_hashes,
        "raw_sha256": raw_hashes,
        "publication": {
            "hash_strategy": "single_pass_during_copy",
            "package_bytes": package_bytes,
            "raw_bytes": raw_bytes,
            "package_copy_seconds": package_seconds,
            "raw_copy_seconds": raw_seconds,
            "cpfs_copy_mib_s": (
                (package_bytes + raw_bytes)
                / (1024 * 1024)
                / (package_seconds + raw_seconds)
                if package_seconds + raw_seconds
                else 0.0
            ),
        },
        "published_utc": capture.utc_now(),
    }
    append_locked(
        CANDIDATES_PATH, manifest, unique_field="episode_id"
    )
    queue_event(
        row["episode_id"],
        status,
        attempt_id,
        {
            "soft_flag_codes": [flag["code"] for flag in flags],
            "episode_path": str(episode_destination),
        },
    )
    capture.clean_stage(stage)
    return manifest


def diagnostic_files(stage: Path) -> list[tuple[Path, Path]]:
    candidates = raw_artifacts(stage)
    keep_names = {
        "actions_requested.csv",
        "actions_engine.csv",
        "server.jsonl",
        "frames_engine.csv",
        "audio_events_engine.csv",
        "ATTEMPT.json",
        "LIVE_PRECHECK.json",
        "server_console.log",
        "client_live_console.log",
        "client_render_console.log",
        "ffmpeg_encode.log",
    }
    rows = [
        (source, relative)
        for source, relative in candidates
        if str(relative) in keep_names
    ]
    for relative in (
        Path("package/qa.json"),
        Path("package/episode.json"),
    ):
        source = stage / relative
        if source.is_file():
            rows.append((source, relative))
    return rows


def preserve_hard_reject(
    row: dict[str, Any],
    attempt_id: str,
    stage: Path,
    failure: Exception,
    terminal: bool,
) -> dict[str, Any]:
    reason = (
        failure.reason
        if isinstance(failure, capture.CaptureFailure)
        else type(failure).__name__
    )
    detail = (
        failure.detail
        if isinstance(failure, capture.CaptureFailure)
        else str(failure)
    )
    diagnostic_path = (
        PREFLIGHT_ROOT / "diagnostics/hard_rejects" / attempt_id
    )
    hashes: dict[str, str] = {}
    if stage.is_dir() and not diagnostic_path.exists():
        files = diagnostic_files(stage)
        if files:
            hashes, _, _ = copy_mapping_hashed_once(
                files, diagnostic_path
            )
    rejection = {
        "schema_version": "xonotic-production-preflight-hard-reject-v1",
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "reason": reason,
        "detail": detail,
        "retryable_operational_failure": reason in RETRYABLE_REASONS,
        "terminal": terminal,
        "diagnostic_path": (
            str(diagnostic_path) if diagnostic_path.exists() else None
        ),
        "diagnostic_sha256": hashes,
        "raw_retained": False,
        "rejected_utc": capture.utc_now(),
    }
    append_locked(HARD_REJECTS_PATH, rejection)
    queue_event(
        row["episode_id"],
        "hard_reject_terminal" if terminal else "hard_reject_retrying",
        attempt_id,
        {"reason": reason, "detail": detail[:1000]},
    )
    if stage.is_dir():
        capture.clean_stage(stage)
    return rejection


def existing_candidate(episode_id: str) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in capture.load_jsonl(CANDIDATES_PATH)
            if row["episode_id"] == episode_id
        ),
        None,
    )


def terminal_rejection(episode_id: str) -> dict[str, Any] | None:
    rows = [
        row
        for row in capture.load_jsonl(HARD_REJECTS_PATH)
        if row["episode_id"] == episode_id and row.get("terminal")
    ]
    return rows[-1] if rows else None


def next_attempt_index(episode_id: str) -> int:
    rows = [
        row
        for row in capture.load_jsonl(HARD_REJECTS_PATH)
        if row["episode_id"] == episode_id
    ]
    indexes = []
    for row in rows:
        try:
            indexes.append(int(row["attempt_id"].rsplit("_a", 1)[1]))
        except (KeyError, ValueError, IndexError):
            pass
    for path in (capture.TMP_ROOT / "raw").glob(f"{episode_id}_a*"):
        try:
            indexes.append(int(path.name.rsplit("_a", 1)[1]))
        except (ValueError, IndexError):
            pass
    return max(indexes, default=0)


def capture_one(
    base: dict[str, Any],
    max_operational_attempts: int,
    retry_terminal: bool = False,
) -> dict[str, Any]:
    existing = existing_candidate(base["episode_id"])
    if existing is not None:
        return existing
    terminal = terminal_rejection(base["episode_id"])
    if terminal is not None and not retry_terminal:
        return terminal
    if terminal is not None:
        queue_event(
            base["episode_id"],
            "terminal_reopened",
            terminal.get("attempt_id"),
            {
                "prior_reason": terminal.get("reason"),
                "explicit_retry": True,
            },
        )

                                                                            
                                                              
    row = review.apply_variant(base, int(base["fixed_variant_index"]))
    start_index = next_attempt_index(row["episode_id"])
    for local_attempt in range(max_operational_attempts):
        retry_index = start_index + local_attempt
        attempt_id = f"{row['episode_id']}_a{retry_index + 1:02d}"
        stage = capture.TMP_ROOT / "raw" / attempt_id
        queue_event(row["episode_id"], "capturing", attempt_id)
        print(
            f"capture {row['episode_id']} {attempt_id} "
            f"{row['map']} {row['dataset_role']} {row['primary_bucket']}",
            flush=True,
        )
        try:
            result = capture.execute_attempt(
                row, retry_index, publish=False
            )
            package = Path(result["stage"]) / "package"
            relation = v2.relation_metrics(
                package, bool(row["enemy_present"])
            )
            metrics = motion.motion_metrics(package)
            qa, status, flags, realized = update_package_semantics(
                package, row, relation, metrics
            )
            manifest = publish_candidate(
                row, result, qa, status, flags, realized
            )
            print(
                f"candidate {row['episode_id']} status={status} "
                f"flags={len(flags)} actual={realized}",
                flush=True,
            )
            return manifest
        except Exception as exc:
            reason = (
                exc.reason
                if isinstance(exc, capture.CaptureFailure)
                else type(exc).__name__
            )
            retryable = reason in RETRYABLE_REASONS
            terminal = (
                not retryable
                or local_attempt + 1 >= max_operational_attempts
            )
            rejection = preserve_hard_reject(
                row, attempt_id, stage, exc, terminal
            )
            print(
                f"hard-reject {attempt_id} reason={reason} "
                f"retryable={retryable} terminal={terminal}",
                flush=True,
            )
            if terminal:
                return rejection
    raise AssertionError("unreachable")


def command_collect(args: argparse.Namespace) -> int:
    capture.require_conda()
    if not SCENARIOS_PATH.is_file():
        command_generate(argparse.Namespace(count=DEFAULT_COUNT))
    scenarios = capture.load_jsonl(SCENARIOS_PATH)
    completed = {
        row["episode_id"] for row in capture.load_jsonl(CANDIDATES_PATH)
    }
    terminal = {
        row["episode_id"]
        for row in capture.load_jsonl(HARD_REJECTS_PATH)
        if row.get("terminal")
    }
    requested = set(args.episode or [])
    if requested:
        known = {row["episode_id"] for row in scenarios}
        unknown = sorted(requested - known)
        if unknown:
            raise capture.CaptureFailure(
                "unknown_requested_episode", ",".join(unknown)
            )
    if args.retry_terminal and not requested:
        raise capture.CaptureFailure(
            "retry_terminal_requires_explicit_episode"
        )
    excluded_terminal = set() if args.retry_terminal else terminal
    pending = [
        row
        for row in scenarios
        if row["episode_id"] not in completed | excluded_terminal
    ]
    if requested:
        pending = [
            row for row in pending if row["episode_id"] in requested
        ]
    if args.limit:
        pending = pending[: args.limit]
    print(
        f"queue planned={len(scenarios)} completed={len(completed)} "
        f"terminal={len(terminal)} pending_run={len(pending)} "
        f"workers={args.workers}",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(
                capture_one,
                row,
                args.max_operational_attempts,
                args.retry_terminal,
            ): row
            for row in pending
        }
        for index, future in enumerate(
            concurrent.futures.as_completed(futures), 1
        ):
            row = futures[future]
            result = future.result()
            print(
                f"progress {index}/{len(pending)} "
                f"{row['episode_id']} -> "
                f"{result.get('status', result.get('reason'))}",
                flush=True,
            )
    return command_status(args)


def hash_tree(path: Path) -> dict[str, str]:
    return {
        str(file.relative_to(path)): capture.sha256_file(file)
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def recover_one(episode: Path) -> bool:
    record_path = episode / "candidate_record.json"
    if not record_path.is_file():
        return False
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if existing_candidate(record["episode_id"]) is not None:
        return False
    raw = PREFLIGHT_ROOT / "raw" / record["attempt_id"]
    if not raw.is_dir():
        return False
    manifest = {
        **record,
        "episode_path": str(episode),
        "raw_path": str(raw),
        "package_sha256": hash_tree(episode),
        "raw_sha256": hash_tree(raw),
        "publication": {
            "hash_strategy": "recovered_destination_scan",
            "recovered": True,
        },
        "published_utc": capture.utc_now(),
    }
    appended = append_locked(
        CANDIDATES_PATH, manifest, unique_field="episode_id"
    )
    if appended:
        queue_event(
            record["episode_id"],
            "publication_recovered",
            record["attempt_id"],
        )
    return appended


def command_recover(_: argparse.Namespace) -> int:
    recovered = 0
    for episode in sorted((PREFLIGHT_ROOT / "episodes").glob("*")):
        if episode.is_dir() and recover_one(episode):
            recovered += 1
    print(f"recovered={recovered}")
    return 0


def command_rescan_geometry(_: argparse.Namespace) -> int:
    """Create an immutable-manifest overlay for camera and wall QA."""
    candidates = capture.load_jsonl(CANDIDATES_PATH)
    previous = load_annotations()
    annotations: list[dict[str, Any]] = []
    failures: list[str] = []
    for row in candidates:
        try:
            annotations.append(scan_candidate_geometry(row))
        except Exception as exc:
            failures.append(
                f"{row['episode_id']}:{type(exc).__name__}:{exc}"
            )
    if failures:
        raise capture.CaptureFailure(
            "camera_collision_rescan_failed",
            capture.canonical_json(failures),
        )

    write_jsonl(ANNOTATIONS_PATH, annotations)
    changed = 0
    new_queue_events = 0
    existing_state_pairs = {
        (row.get("episode_id"), row.get("state"))
        for row in capture.load_jsonl(QUEUE_EVENTS_PATH)
    }
    for annotation in annotations:
        old = previous.get(annotation["episode_id"])
        signature_unchanged = (
            old is not None
            and annotation_signature(old)
            == annotation_signature(annotation)
        )
        if annotation["hard_invalidated"]:
            state = "posthoc_hard_invalidated"
        elif annotation["training_excluded"]:
            state = "posthoc_training_excluded"
        else:
            state = "posthoc_geometry_reviewed"
        if not signature_unchanged:
            changed += 1
        if (
            signature_unchanged
            and (annotation["episode_id"], state)
            in existing_state_pairs
        ):
            continue
        new_queue_events += 1
        queue_event(
            annotation["episode_id"],
            state,
            detail={
                "hard_invalidation_reasons": annotation[
                    "hard_invalidation_reasons"
                ],
                "training_exclusion_reasons": annotation[
                    "training_exclusion_reasons"
                ],
                "soft_flag_codes": annotation["soft_flag_codes"],
                "camera_continuity": annotation[
                    "camera_continuity"
                ],
                "movement_blockage": annotation[
                    "movement_blockage"
                ],
            },
        )

    hard_invalidated = [
        row["episode_id"]
        for row in annotations
        if row["hard_invalidated"]
    ]
    training_excluded = [
        row["episode_id"]
        for row in annotations
        if row["training_excluded"] and not row["hard_invalidated"]
    ]
    blocked = [
        {
            "episode_id": row["episode_id"],
            "longest_blocked_ticks": row["movement_blockage"][
                "longest_blocked_ticks"
            ],
            "longest_blocked_seconds": row["movement_blockage"][
                "longest_blocked_seconds"
            ],
            "windows": row["movement_blockage"]["windows"],
        }
        for row in annotations
        if row["movement_blockage"]["high_confidence"]
    ]
    audit = {
        "schema_version": "xonotic-camera-collision-audit-v1",
        "created_utc": capture.utc_now(),
        "manifest_candidate_count": len(candidates),
        "capture_valid_candidate_count": len(candidates)
        - len(hard_invalidated),
        "selection_eligible_candidate_count": (
            len(candidates)
            - len(hard_invalidated)
            - len(training_excluded)
        ),
        "hard_invalidated_episode_ids": hard_invalidated,
        "foundation_training_excluded_episode_ids": (
            training_excluded
        ),
        "confirmed_rule_rejection_rate": (
            (len(hard_invalidated) + len(training_excluded))
            / len(candidates)
            if candidates
            else 0.0
        ),
        "sustained_command_blockage": blocked,
        "detector_scope": {
            "camera": (
                "Hard gate based on render-camera continuity against the "
                "authoritative player origin."
            ),
            "blockage": (
                "High-confidence inference from command direction and "
                "authoritative velocity; exact contact normal is unavailable."
            ),
            "foundation_selection": (
                "Sustained blockage outside the +/-45 degree forward cone "
                "is excluded because lateral/backward obstacle causality is "
                "ambiguous in the rendered view. Forward-cone blockage stays "
                "eligible only for a small collision review bucket."
            ),
        },
        "changed_annotations": changed,
        "new_queue_events": new_queue_events,
    }
    atomic_json(GEOMETRY_AUDIT_PATH, audit)
    print(capture.canonical_json(audit))
    return 0


def command_audit(args: argparse.Namespace) -> int:
    candidates = capture.load_jsonl(CANDIDATES_PATH)
    annotations = load_annotations()
    effective_by_id = {
        row["episode_id"]: row for row in effective_candidate_rows()
    }
    hard_rejects = capture.load_jsonl(HARD_REJECTS_PATH)
    failures: list[str] = []
    hash_jobs: list[tuple[str, Path, str]] = []
    live_prechecks = 0
    camera_verified = 0
    blockage_verified = 0
    if len(candidates) != len(
        {row["episode_id"] for row in candidates}
    ):
        failures.append("duplicate_candidate_episode_id")
    if set(annotations) != {
        row["episode_id"] for row in candidates
    }:
        failures.append("posthoc_annotation_episode_set")
    for row in candidates:
        episode = Path(row["episode_path"])
        raw = Path(row["raw_path"])
        if not episode.is_dir():
            failures.append(f"{row['episode_id']}:episode_missing")
            continue
        if not raw.is_dir():
            failures.append(f"{row['episode_id']}:raw_missing")
            continue
        package_files = {
            str(path.relative_to(episode))
            for path in episode.rglob("*")
            if path.is_file()
        }
        raw_files = {
            str(path.relative_to(raw))
            for path in raw.rglob("*")
            if path.is_file()
        }
        if package_files != set(row["package_sha256"]):
            failures.append(f"{row['episode_id']}:package_file_set")
        if raw_files != set(row["raw_sha256"]):
            failures.append(f"{row['episode_id']}:raw_file_set")
        for relative, expected in row["package_sha256"].items():
            hash_jobs.append(
                (
                    f"{row['episode_id']}:package:{relative}",
                    episode / relative,
                    expected,
                )
            )
        for relative, expected in row["raw_sha256"].items():
            hash_jobs.append(
                (
                    f"{row['episode_id']}:raw:{relative}",
                    raw / relative,
                    expected,
                )
            )
        qa = json.loads((episode / "qa.json").read_text(encoding="utf-8"))
        live_precheck_path = raw / "LIVE_PRECHECK.json"
        if live_precheck_path.is_file():
            live_prechecks += 1
            live_precheck = json.loads(
                live_precheck_path.read_text(encoding="utf-8")
            )
            if not live_precheck.get("passed"):
                failures.append(
                    f"{row['episode_id']}:live_precheck"
                )
            if qa.get("live_precheck") != live_precheck:
                failures.append(
                    f"{row['episode_id']}:live_precheck_mismatch"
                )
        if not all(qa["hard_gates"].values()):
            failures.append(f"{row['episode_id']}:hard_qa")
        if qa.get("training_admitted") is not False:
            failures.append(f"{row['episode_id']}:training_admitted")
        if row.get("training_admitted") is not False:
            failures.append(
                f"{row['episode_id']}:manifest_training_admitted"
            )
        if not capture.is_nvidia_hardware_renderer(
            qa["runtime"]["renderer"]
        ):
            failures.append(f"{row['episode_id']}:renderer")
        if row["status"] == "needs_review" and not row["soft_flags"]:
            failures.append(f"{row['episode_id']}:review_without_flag")
        if (
            row["status"] == "auto_keep_candidate"
            and row["soft_flags"]
        ):
            failures.append(f"{row['episode_id']}:auto_with_flag")

        annotation = annotations.get(row["episode_id"])
        effective = effective_by_id.get(row["episode_id"])
        if annotation is None or effective is None:
            failures.append(
                f"{row['episode_id']}:posthoc_annotation_missing"
            )
        else:
            live_annotation = scan_candidate_geometry(row)
            if (
                annotation_signature(live_annotation)
                != annotation_signature(annotation)
            ):
                failures.append(
                    f"{row['episode_id']}:posthoc_annotation_stale"
                )
            else:
                camera_verified += 1
                blockage_verified += 1
            camera_passed = bool(
                live_annotation["camera_continuity"]["passed"]
            )
            if camera_passed == bool(
                live_annotation["hard_invalidated"]
            ):
                failures.append(
                    f"{row['episode_id']}:camera_disposition"
                )
            if (
                effective["capture_valid"]
                and not camera_passed
            ):
                failures.append(
                    f"{row['episode_id']}:active_third_person_camera"
                )
            if (
                not effective["capture_valid"]
                and effective["status"] != "hard_invalidated"
            ):
                failures.append(
                    f"{row['episode_id']}:invalid_status"
                )
            should_exclude = bool(
                live_annotation["training_excluded"]
            )
            if should_exclude and (
                effective["selection_eligible"]
                or effective["status"] != "training_excluded"
            ):
                failures.append(
                    f"{row['episode_id']}:training_exclusion_disposition"
                )
            if (
                not should_exclude
                and effective["capture_valid"]
                and not effective["selection_eligible"]
            ):
                failures.append(
                    f"{row['episode_id']}:unexpected_selection_exclusion"
                )
        video = episode / "video.mkv"
        probe = capture.ffprobe_json(video, count_frames=True)
        encoded = capture.encoded_contract(probe, video)
        if capture.count_video_frames(probe) != capture.OUTPUT_TICKS:
            failures.append(f"{row['episode_id']}:decoded_frames")
        if not all(encoded.values()):
            failures.append(f"{row['episode_id']}:encoded_contract")
        if capture.decode_audio_s16(video).shape[0] != capture.AUDIO_SAMPLES:
            failures.append(f"{row['episode_id']}:decoded_audio_samples")

    def verify_hash(job: tuple[str, Path, str]) -> str | None:
        label, path, expected = job
        if not path.is_file():
            return f"{label}:missing"
        if capture.sha256_file(path) != expected:
            return f"{label}:sha256"
        return None

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.hash_workers
    ) as executor:
        for failure in executor.map(verify_hash, hash_jobs):
            if failure:
                failures.append(failure)

                                                                            
                                             
    candidate_by_id = {
        row["episode_id"]: row for row in candidates
    }
    retry_action_checks = 0
    for rejection in hard_rejects:
        candidate = candidate_by_id.get(rejection["episode_id"])
        diagnostic = rejection.get("diagnostic_path")
        if candidate is None or not diagnostic:
            continue
        first_action = Path(diagnostic) / "actions_requested.csv"
        accepted_action = (
            Path(candidate["raw_path"]) / "actions_requested.csv"
        )
        retry_action_checks += 1
        if (
            not first_action.is_file()
            or not accepted_action.is_file()
            or capture.sha256_file(first_action)
            != capture.sha256_file(accepted_action)
        ):
            failures.append(
                f"{rejection['episode_id']}:retry_action_changed"
            )

    audit = {
        "schema_version": "xonotic-production-preflight-audit-v1",
        "created_utc": capture.utc_now(),
        "passed": not failures,
        "manifest_candidate_count": len(candidates),
        "candidate_count": sum(
            row["capture_valid"]
            for row in effective_by_id.values()
        ),
        "hard_invalidated_candidate_count": sum(
            not row["capture_valid"]
            for row in effective_by_id.values()
        ),
        "semantic_training_excluded_candidate_count": sum(
            row["capture_valid"]
            and not row["selection_eligible"]
            for row in effective_by_id.values()
        ),
        "selection_eligible_candidate_count": sum(
            row["selection_eligible"]
            for row in effective_by_id.values()
        ),
        "confirmed_rule_rejection_rate": (
            sum(
                not row["selection_eligible"]
                for row in effective_by_id.values()
            )
            / len(effective_by_id)
            if effective_by_id
            else 0.0
        ),
        "sustained_blockage_flag_count": sum(
            row.get("posthoc_annotation", {})
            .get("movement_blockage", {})
            .get("high_confidence", False)
            for row in effective_by_id.values()
        ),
        "hash_jobs": len(hash_jobs),
        "hard_reject_attempts": len(hard_rejects),
        "live_prechecks_verified": live_prechecks,
        "camera_continuity_verified": camera_verified,
        "movement_blockage_verified": blockage_verified,
        "retry_action_identity_checks": retry_action_checks,
        "failures": failures,
    }
    atomic_json(PREFLIGHT_ROOT / "AUDIT.json", audit)
    print(capture.canonical_json(audit))
    if failures:
        raise capture.CaptureFailure(
            "production_preflight_audit_failed",
            capture.canonical_json(failures),
        )
    return 0


def latest_decisions() -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for row in capture.load_jsonl(REVIEW_DECISIONS_PATH):
        decisions[row["episode_id"]] = row
    return decisions


def summary() -> dict[str, Any]:
    scenarios = capture.load_jsonl(SCENARIOS_PATH)
    manifest_candidates = capture.load_jsonl(CANDIDATES_PATH)
    effective_candidates = effective_candidate_rows()
    capture_valid_candidates = [
        row for row in effective_candidates if row["capture_valid"]
    ]
    selection_candidates = [
        row for row in effective_candidates if row["selection_eligible"]
    ]
    semantic_excluded = [
        row
        for row in capture_valid_candidates
        if not row["selection_eligible"]
    ]
    hard_invalidated = [
        row for row in effective_candidates if not row["capture_valid"]
    ]
    hard_rejects = capture.load_jsonl(HARD_REJECTS_PATH)
    candidate_ids = {
        row["episode_id"] for row in manifest_candidates
    }
    decisions = latest_decisions()
    flags = Counter(
        flag["code"]
        for row in capture_valid_candidates
        for flag in row.get("soft_flags", [])
    )
    confirmed_rejected = len(hard_invalidated) + len(semantic_excluded)
    result = {
        "schema_version": "xonotic-production-preflight-summary-v1",
        "updated_utc": capture.utc_now(),
        "formal_collection_authorized": False,
        "planned": len(scenarios),
        "manifest_candidates": len(manifest_candidates),
        "capture_valid_candidates": len(capture_valid_candidates),
        "selection_eligible_candidates": len(selection_candidates),
        "semantic_training_excluded_candidates": len(
            semantic_excluded
        ),
        "semantic_training_excluded_episode_ids": [
            row["episode_id"] for row in semantic_excluded
        ],
        "hard_invalidated_candidates": len(hard_invalidated),
        "hard_invalidated_episode_ids": [
            row["episode_id"] for row in hard_invalidated
        ],
        "confirmed_rule_rejected_candidates": confirmed_rejected,
        "confirmed_rule_rejection_rate": (
            confirmed_rejected / len(manifest_candidates)
            if manifest_candidates
            else 0.0
        ),
        "capture_integrity_rejection_rate": (
            len(hard_invalidated) / len(manifest_candidates)
            if manifest_candidates
            else 0.0
        ),
        "semantic_rejection_rate_of_capture_valid": (
            len(semantic_excluded) / len(capture_valid_candidates)
            if capture_valid_candidates
            else 0.0
        ),
        "auto_keep_candidates": sum(
            row["status"] == "auto_keep_candidate"
            for row in selection_candidates
        ),
        "needs_review_candidates": sum(
            row["status"] == "needs_review"
            for row in selection_candidates
        ),
        "hard_reject_attempts": len(hard_rejects),
        "terminal_hard_rejects": sum(
            bool(row.get("terminal"))
            and row["episode_id"] not in candidate_ids
            for row in hard_rejects
        ),
        "superseded_terminal_hard_reject_attempts": sum(
            bool(row.get("terminal"))
            and row["episode_id"] in candidate_ids
            for row in hard_rejects
        ),
        "human_decisions": dict(
            Counter(row["decision"] for row in decisions.values())
        ),
        "soft_flag_counts": dict(flags),
        "roles": dict(
            Counter(
                row["dataset_role"] for row in selection_candidates
            )
        ),
        "buckets": dict(
            Counter(
                row["primary_bucket"] for row in selection_candidates
            )
        ),
        "maps": dict(
            Counter(row["map"] for row in selection_candidates)
        ),
        "weapons": dict(
            Counter(row["weapon"] for row in selection_candidates)
        ),
        "realized_net": dict(
            Counter(
                row["realized_labels"]["net_displacement_bin"]
                for row in selection_candidates
            )
        ),
        "realized_yaw": dict(
            Counter(
                row["realized_labels"]["yaw_range_bin"]
                for row in selection_candidates
            )
        ),
        "realized_pitch": dict(
            Counter(
                row["realized_labels"]["pitch_range_bin"]
                for row in selection_candidates
            )
        ),
        "realized_relation": dict(
            Counter(
                row["realized_labels"]["target_relation"]
                for row in selection_candidates
                if row["enemy_present"]
            )
        ),
        "realized_distance": dict(
            Counter(
                row["realized_labels"]["distance_bin"]
                for row in selection_candidates
                if row["enemy_present"]
            )
        ),
    }
    atomic_json(SUMMARY_PATH, result)
    return result


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(
        len(ordered) - 1,
        max(0, int(round((len(ordered) - 1) * fraction))),
    )
    return ordered[index]


def resource_metrics_summary() -> dict[str, Any]:
    paths = sorted((PREFLIGHT_ROOT / "metrics").glob("*.csv"))
    for suffix in ("_v4", "_v3", "_v2"):
        corrected = [
            path for path in paths if path.stem.endswith(suffix)
        ]
        if corrected:
            paths = corrected
            break
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))

    def values(name: str) -> list[float]:
        result: list[float] = []
        for row in rows:
            try:
                result.append(float(row[name]))
            except (KeyError, TypeError, ValueError):
                pass
        return result

    gpu = values("gpu_util_percent")
    memory = values("gpu_memory_mib")
    cpu = values("aggregate_cpu_percent")
    raw_write = values("raw_avi_write_mib_s")
    process_write = values("process_write_mib_s")
    system_write = values("system_write_mib_s")
    return {
        "files": [str(path) for path in paths],
        "samples": len(rows),
        "first_utc": rows[0].get("utc") if rows else None,
        "last_utc": rows[-1].get("utc") if rows else None,
        "wall_seconds": max(values("elapsed_s"), default=0.0),
        "gpu_util_percent": {
            "mean": sum(gpu) / len(gpu) if gpu else 0.0,
            "p95": percentile(gpu, 0.95),
            "max": max(gpu, default=0.0),
        },
        "gpu_memory_mib_max": max(memory, default=0.0),
        "aggregate_cpu_percent": {
            "mean": sum(cpu) / len(cpu) if cpu else 0.0,
            "p95": percentile(cpu, 0.95),
            "max": max(cpu, default=0.0),
        },
        "raw_avi_write_mib_s_p95": percentile(raw_write, 0.95),
        "process_write_mib_s_p95": percentile(process_write, 0.95),
        "system_write_mib_s_p95": percentile(system_write, 0.95),
    }


def command_status(_: argparse.Namespace) -> int:
    result = summary()
    print(capture.canonical_json(result))
    return 0


def make_preview(row: dict[str, Any]) -> Path:
    media = PREVIEW_ROOT / "media"
    media.mkdir(parents=True, exist_ok=True)
    source = Path(row["episode_path"]) / "video.mkv"
    destination = media / f"{row['episode_id']}.mp4"
    if destination.is_file():
        return destination
    temporary = media / f".{row['episode_id']}.tmp.mp4"
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(temporary),
        ],
        check=False,
    )
    if completed.returncode:
        temporary.unlink(missing_ok=True)
        raise capture.CaptureFailure(
            "preflight_preview_encode_failed", row["episode_id"]
        )
    os.replace(temporary, destination)
    return destination


def option_html(values: Iterable[str]) -> str:
    return "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in values
    )


def command_html(args: argparse.Namespace) -> int:
    rows = sorted(
        effective_candidate_rows(),
        key=lambda row: row["episode_id"],
    )
    if not rows:
        raise capture.CaptureFailure(
            "no_preflight_candidates", str(CANDIDATES_PATH)
        )
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.preview_workers
    ) as executor:
        list(executor.map(make_preview, rows))

    cards: list[str] = []
    for row in rows:
        flags = row.get("soft_flags", [])
        flag_codes = [flag["code"] for flag in flags]
        intended = row["intended_labels"]
        realized = row["realized_labels"]
        relation = row["target_relation"]
        metric = row["motion"]
        camera = row["qa"].get("camera_continuity", {})
        blockage = row["qa"].get("movement_blockage", {})
        hard_invalidated = row["status"] == "hard_invalidated"
        training_excluded = row["status"] == "training_excluded"
        flag_list = (
            "".join(
                "<li><code>"
                + html.escape(flag["code"])
                + "</code>: "
                + html.escape(flag["note"])
                + "</li>"
                for flag in flags
            )
            or "<li>无自动软标记；仍可人工检查画面质量。</li>"
        )
        if hard_invalidated:
            reasons = ", ".join(
                row.get("hard_invalidation", {}).get("reasons", [])
            )
            flag_list = (
                "<li class=\"hard-note\"><code>HARD INVALID</code>: "
                "检测到非第一人称镜头；此条永不进入训练，raw 仅保留作审计。"
                f" reason={html.escape(reasons)}</li>"
                + flag_list
            )
        elif training_excluded:
            reasons = ", ".join(
                row.get("training_exclusion", {}).get("reasons", [])
            )
            flag_list = (
                "<li class=\"exclude-note\"><code>TRAINING EXCLUDED</code>: "
                "横移/后退方向发生持续阻塞，画面无法清楚解释障碍因果；"
                "保留 raw 审计，但不进入基础动力学训练。"
                f" reason={html.escape(reasons)}</li>"
                + flag_list
            )
        camera_text = (
            (
                f"{'PASS' if camera.get('passed') else 'FAIL'} · "
                f"horizontal max "
                f"{float(camera.get('max_horizontal_offset', 0)):.1f}u · "
                f"violating {int(camera.get('violating_frames', 0))}/"
                f"{int(camera.get('total_frames', 0))}"
            )
            if camera
            else "未做后验扫描"
        )
        blockage_windows = blockage.get("windows", [])
        blockage_span = (
            f" · tick {blockage_windows[0]['start_tick']}"
            f"–{blockage_windows[0]['end_tick']}"
            if blockage_windows
            else ""
        )
        blockage_direction = (
            f" · direction {blockage_windows[0].get('direction_class', '-')}"
            if blockage_windows
            else ""
        )
        blockage_text = (
            (
                f"{'FLAG' if blockage.get('high_confidence') else 'clear'} · "
                f"longest {int(blockage.get('longest_blocked_ticks', 0))} "
                f"ticks / "
                f"{float(blockage.get('longest_blocked_seconds', 0)):.2f}s · "
                f"contact normal: unavailable{blockage_span}"
                f"{blockage_direction}"
            )
            if blockage
            else "未做后验扫描"
        )
        if hard_invalidated:
            decision_html = """
  <div class="hard-invalidation">
   不可留：硬失效样本。按钮已禁用，已有本地人工判断不改变此状态。
  </div>"""
        elif training_excluded:
            decision_html = """
  <div class="training-exclusion">
   基础动力学不可留：横移/后退持续阻塞的训练筛除规则已命中。
  </div>"""
        else:
            decision_html = f"""
  <div class="decision" data-episode="{html.escape(row['episode_id'])}">
   <button data-value="keep">留</button>
   <button data-value="reject">不留</button>
   <button data-value="unsure">待定</button>
   <span class="decision-state">未判断</span>
   <textarea placeholder="可选备注"></textarea>
  </div>"""
        cards.append(
            f"""
<article class="card" id="card-{html.escape(row['episode_id'])}"
 data-status="{html.escape(row['status'])}"
 data-role="{html.escape(row['dataset_role'])}"
 data-bucket="{html.escape(row['primary_bucket'])}"
 data-map="{html.escape(row['map'])}"
 data-weapon="{html.escape(row['weapon'])}"
 data-net="{html.escape(realized['net_displacement_bin'])}"
 data-yaw="{html.escape(realized['yaw_range_bin'])}"
 data-pitch="{html.escape(realized['pitch_range_bin'])}"
 data-relation="{html.escape(str(realized.get('target_relation') or 'none'))}"
 data-distance="{html.escape(str(realized.get('distance_bin') or 'none'))}"
 data-flags="{html.escape(' '.join(flag_codes) or 'none')}">
 <video controls preload="metadata" src="media/{html.escape(row['episode_id'])}.mp4"></video>
 <div class="body">
  <div class="title"><h2>{html.escape(row['episode_id'])}</h2>
   <span class="badge {html.escape(row['status'])}">{html.escape(row['status'])}</span></div>
  <p>{html.escape(row['dataset_role'])} · {html.escape(row['primary_bucket'])} · source {html.escape(row['source_episode_id'])}</p>
  <dl>
   <dt>地图 / 武器</dt><dd>{html.escape(row['map'])} / {html.escape(row['weapon'])}</dd>
   <dt>目标 motion</dt><dd>{html.escape(intended['net_displacement_bin'])} · yaw {html.escape(intended['yaw_range_bin'])} · pitch {html.escape(intended['pitch_range_bin'])}</dd>
   <dt>实际 motion</dt><dd>{html.escape(realized['net_displacement_bin'])} ({metric['net_displacement_3d']:.0f}u) · yaw {html.escape(realized['yaw_range_bin'])} ({metric['yaw_range_deg']:.1f}°) · pitch {html.escape(realized['pitch_range_bin'])} ({metric['pitch_range_deg']:.1f}°)</dd>
   <dt>目标敌人关系</dt><dd>{html.escape(str(intended.get('target_relation') or '-'))} / {html.escape(str(intended.get('distance_bin') or '-'))}</dd>
   <dt>实际敌人关系</dt><dd>{html.escape(str(realized.get('target_relation') or '-'))} / {html.escape(str(realized.get('distance_bin') or '-'))}; median {html.escape(str(round(relation.get('median_enemy_distance', 0), 1) if row['enemy_present'] else '-'))}u</dd>
   <dt>硬 QA</dt><dd>{'PASS' if row['qa']['hard_gates_pass'] else 'FAIL'} · NVIDIA · {row['qa']['frames']} frames · {row['qa']['audio_samples']} samples/ch</dd>
   <dt>第一人称连续性</dt><dd>{html.escape(camera_text)}</dd>
   <dt>贴墙/卡墙推断</dt><dd>{html.escape(blockage_text)}</dd>
   <dt>声音 / 事件</dt><dd>onset {row['qa']['audio_onset_max_ms']:.3f} ms · linkage {row['qa']['event_linkage']:.5f}</dd>
  </dl>
  <ul class="flags">{flag_list}</ul>
{decision_html}
 </div>
</article>"""
        )

    filters = {
        "status": sorted({row["status"] for row in rows}),
        "role": sorted({row["dataset_role"] for row in rows}),
        "bucket": sorted({row["primary_bucket"] for row in rows}),
        "map": sorted({row["map"] for row in rows}),
        "weapon": sorted({row["weapon"] for row in rows}),
        "net": sorted(
            {
                row["realized_labels"]["net_displacement_bin"]
                for row in rows
            }
        ),
        "yaw": sorted(
            {
                row["realized_labels"]["yaw_range_bin"]
                for row in rows
            }
        ),
        "pitch": sorted(
            {
                row["realized_labels"]["pitch_range_bin"]
                for row in rows
            }
        ),
        "relation": sorted(
            {
                str(row["realized_labels"].get("target_relation") or "none")
                for row in rows
            }
        ),
        "distance": sorted(
            {
                str(row["realized_labels"].get("distance_bin") or "none")
                for row in rows
            }
        ),
    }
    controls = "".join(
        f'<label>{name}<select id="filter-{name}" data-key="{name}">'
        f'<option value="">all</option>{option_html(values)}</select></label>'
        for name, values in filters.items()
    )
    result_summary = summary()
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xonotic Stage-1 Production Preflight Review</title>
<style>
:root{{color-scheme:dark;font-family:Inter,system-ui,sans-serif}}
body{{margin:0;background:#091018;color:#eaf2fb}}
header{{position:sticky;top:0;z-index:5;background:#111b28f3;border-bottom:1px solid #304257;padding:14px 20px}}
h1{{font-size:21px;margin:0 0 5px}}header p{{margin:4px 0;color:#b3c2d2}}
.controls{{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}}
select,button,textarea{{background:#182638;color:#f5f8fb;border:1px solid #40556f;border-radius:7px;padding:6px}}
button{{cursor:pointer}}#export{{background:#126f82}}#import-label{{border:1px solid #40556f;border-radius:7px;padding:6px;cursor:pointer}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:16px;padding:18px}}
.card{{background:#121d2a;border:1px solid #2b4056;border-radius:12px;overflow:hidden}}
.card[data-status="hard_invalidated"]{{border:2px solid #d84a4a;background:#261518}}
.card[data-status="training_excluded"]{{border:2px solid #d88338;background:#261d15}}
.card.hidden{{display:none}}video{{width:100%;aspect-ratio:16/9;background:#000;display:block}}
.body{{padding:12px 15px}}.title{{display:flex;justify-content:space-between;align-items:center}}h2{{font-size:17px;margin:0}}
.badge{{padding:3px 8px;border-radius:999px;font-size:12px}}.needs_review{{background:#6b4614}}.auto_keep_candidate{{background:#155d48}}.hard_invalidated{{background:#9f2525}}.training_excluded{{background:#94511d}}
dl{{display:grid;grid-template-columns:115px 1fr;gap:5px 9px;font-size:13px}}dt{{color:#91a7bd}}dd{{margin:0}}
.flags{{font-size:12px;color:#f0c17c;padding-left:20px}}code{{color:#ffcf85}}.hard-note{{color:#ff8d8d}}.exclude-note{{color:#ffb870}}
.decision{{display:grid;grid-template-columns:auto auto auto 1fr;gap:7px;align-items:center}}
.decision button.active{{outline:2px solid #72dbff}}.decision-state{{font-size:12px;color:#99bed0}}
.hard-invalidation{{border:1px solid #d84a4a;background:#451c22;color:#ffb4b4;border-radius:7px;padding:9px;font-size:13px}}
.training-exclusion{{border:1px solid #d88338;background:#4b311c;color:#ffd1a3;border-radius:7px;padding:9px;font-size:13px}}
textarea{{grid-column:1/-1;min-height:46px;resize:vertical}}
</style></head><body>
<header><h1>Stage-1 Production Preflight 人工 Review</h1>
<p>共 {result_summary['manifest_candidates']} 条历史卡片；capture-valid {result_summary['capture_valid_candidates']}，语义筛除 {result_summary['semantic_training_excluded_candidates']}，当前可进入后续选择 {result_summary['selection_eligible_candidates']}，硬失效 {result_summary['hard_invalidated_candidates']}，确认拒绝率 {result_summary['confirmed_rule_rejection_rate']:.1%}。这不是训练集，也未授权正式批采。</p>
<div class="controls">{controls}
<label>flag 搜索 <input id="flag-search" placeholder="rebucket / damage"></label>
<button id="export">导出 review JSON</button>
<label id="import-label">导入已有判断<input id="import" type="file" accept=".json" hidden></label>
</div></header><main>{''.join(cards)}</main>
<script>
const storageKey='xonotic-stage1-production-preflight-review-v1';
let decisions=JSON.parse(localStorage.getItem(storageKey)||'{{}}');
function renderDecision(box){{
 const id=box.dataset.episode,d=decisions[id]||{{}};
 box.querySelectorAll('button[data-value]').forEach(b=>b.classList.toggle('active',b.dataset.value===d.decision));
 box.querySelector('.decision-state').textContent=d.decision||'未判断';
 box.querySelector('textarea').value=d.note||'';
}}
document.querySelectorAll('.decision').forEach(box=>{{
 renderDecision(box);
 box.querySelectorAll('button[data-value]').forEach(button=>button.onclick=()=>{{
  const id=box.dataset.episode;
  decisions[id]={{decision:button.dataset.value,note:box.querySelector('textarea').value,updated_utc:new Date().toISOString()}};
  localStorage.setItem(storageKey,JSON.stringify(decisions));renderDecision(box);
 }});
 box.querySelector('textarea').addEventListener('change',event=>{{
  const id=box.dataset.episode,d=decisions[id]||{{decision:'unsure'}};
  d.note=event.target.value;d.updated_utc=new Date().toISOString();decisions[id]=d;
  localStorage.setItem(storageKey,JSON.stringify(decisions));renderDecision(box);
 }});
}});
function filterCards(){{
 const filters=[...document.querySelectorAll('select[data-key]')];
 const needle=document.querySelector('#flag-search').value.trim().toLowerCase();
 document.querySelectorAll('.card').forEach(card=>{{
  const match=filters.every(f=>!f.value||card.dataset[f.dataset.key]===f.value)&&(!needle||card.dataset.flags.toLowerCase().includes(needle));
  card.classList.toggle('hidden',!match);if(!match)card.querySelector('video').pause();
 }});
}}
document.querySelectorAll('select[data-key]').forEach(x=>x.onchange=filterCards);
document.querySelector('#flag-search').oninput=filterCards;
document.querySelector('#export').onclick=()=>{{
 const payload={{schema_version:'xonotic-human-review-export-v1',split:'{SPLIT}',exported_utc:new Date().toISOString(),decisions:Object.entries(decisions).map(([episode_id,value])=>({{episode_id,...value}}))}};
 const blob=new Blob([JSON.stringify(payload,null,2)],{{type:'application/json'}});
 const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='xonotic_preflight_review.json';link.click();URL.revokeObjectURL(link.href);
}};
document.querySelector('#import').onchange=async event=>{{
 const payload=JSON.parse(await event.target.files[0].text());
 (payload.decisions||[]).forEach(row=>decisions[row.episode_id]=row);
 localStorage.setItem(storageKey,JSON.stringify(decisions));
 document.querySelectorAll('.decision').forEach(renderDecision);
}};
</script></body></html>"""
    atomic_text(PREVIEW_ROOT / "index.html", document)
    print(str(PREVIEW_ROOT / "index.html"))
    return 0


def command_ingest_review(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
    if payload.get("split") != SPLIT:
        raise capture.CaptureFailure(
            "review_split_mismatch", str(payload.get("split"))
        )
    candidates = {
        row["episode_id"] for row in capture.load_jsonl(CANDIDATES_PATH)
    }
    accepted_decisions = {"keep", "reject", "unsure"}
    ingested = 0
    for row in payload.get("decisions", []):
        if row.get("episode_id") not in candidates:
            raise capture.CaptureFailure(
                "review_unknown_episode", str(row.get("episode_id"))
            )
        if row.get("decision") not in accepted_decisions:
            raise capture.CaptureFailure(
                "review_invalid_decision", str(row.get("decision"))
            )
        append_locked(
            REVIEW_DECISIONS_PATH,
            {
                "schema_version": "xonotic-human-review-decision-v1",
                "episode_id": row["episode_id"],
                "decision": row["decision"],
                "note": str(row.get("note", "")),
                "browser_updated_utc": row.get("updated_utc"),
                "ingested_utc": capture.utc_now(),
                "source_export": str(Path(args.path).resolve()),
            },
        )
        ingested += 1
    print(f"ingested={ingested}")
    return command_status(args)


def command_report(_: argparse.Namespace) -> int:
    result = summary()
    resources = resource_metrics_summary()
    candidates = capture.load_jsonl(CANDIDATES_PATH)
    total_wall = [
        row["runtime"]["live_wall_seconds"]
        + row["runtime"]["render_wall_seconds"]
        + row["runtime"]["encode_wall_seconds"]
        for row in candidates
    ]
    raw_mib = [
        row["publication"]["raw_bytes"] / (1024 * 1024)
        for row in candidates
    ]
    metric_first = resources.get("first_utc") or ""
    metric_last = resources.get("last_utc") or ""
    metric_last_inclusive = (
        datetime.fromisoformat(metric_last.replace("Z", "+00:00"))
        + timedelta(seconds=2)
        if metric_last
        else None
    )
    measured_candidates = [
        row
        for row in candidates
        if metric_first
        and metric_last_inclusive is not None
        and datetime.fromisoformat(
            str(row.get("published_utc", "")).replace("Z", "+00:00")
        )
        >= datetime.fromisoformat(metric_first.replace("Z", "+00:00"))
        and datetime.fromisoformat(
            str(row.get("published_utc", "")).replace("Z", "+00:00")
        )
        <= metric_last_inclusive
    ]
    measured_wall = float(resources.get("wall_seconds", 0.0))
    aggregate_capture_fps = (
        len(measured_candidates) * capture.OUTPUT_TICKS / measured_wall
        if measured_wall
        else 0.0
    )
    output_video_per_wall = (
        len(measured_candidates) * 5.0 / measured_wall
        if measured_wall
        else 0.0
    )
    text = f"""# Stage-1 Production Pipeline Preflight

Updated: `{result['updated_utc']}`

This is a bounded, non-training preflight. It does **not** authorize formal
Stage 1 collection.

## Current result

- Planned: {result['planned']}
- Published historical candidates: {result['manifest_candidates']}
- Capture-valid candidates: {result['capture_valid_candidates']}
- Selection-eligible candidates: {result['selection_eligible_candidates']}
- Semantic training exclusions: {result['semantic_training_excluded_candidates']} ({', '.join(result['semantic_training_excluded_episode_ids']) or 'none'})
- Post-hoc hard-invalidated candidates: {result['hard_invalidated_candidates']} ({', '.join(result['hard_invalidated_episode_ids']) or 'none'})
- Confirmed rule rejection: {result['confirmed_rule_rejected_candidates']}/{result['manifest_candidates']} = {result['confirmed_rule_rejection_rate']:.2%}
- Auto-keep candidates: {result['auto_keep_candidates']}
- Candidates needing human review: {result['needs_review_candidates']}
- Hard-reject attempts: {result['hard_reject_attempts']}
- Terminal hard rejects: {result['terminal_hard_rejects']}
- Superseded terminal QA attempts: {result['superseded_terminal_hard_reject_attempts']}
- Average live+render+encode wall time: {sum(total_wall) / len(total_wall) if total_wall else 0:.2f} s/episode
- Average selected raw retained: {sum(raw_mib) / len(raw_mib) if raw_mib else 0:.1f} MiB/episode
- Resource samples: {resources['samples']}
- GPU utilization mean / p95 / max: {resources['gpu_util_percent']['mean']:.1f}% / {resources['gpu_util_percent']['p95']:.1f}% / {resources['gpu_util_percent']['max']:.1f}%
- Maximum GPU memory: {resources['gpu_memory_mib_max']:.0f} MiB
- Aggregate process CPU mean / p95: {resources['aggregate_cpu_percent']['mean']:.1f}% / {resources['aggregate_cpu_percent']['p95']:.1f}%
- Capture-process write throughput p95: {resources['process_write_mib_s_p95']:.1f} MiB/s
- System write throughput p95: {resources['system_write_mib_s_p95']:.1f} MiB/s
- Latest measured batch candidates / wall time: {len(measured_candidates)} / {measured_wall:.1f} s
- Latest measured aggregate capture FPS: {aggregate_capture_fps:.1f}
- Latest measured output-video seconds / wall second: {output_video_per_wall:.3f}x

## Admission policy

Structural media, NVIDIA renderer, timing, authoritative telemetry, event
linkage, resource accounting, audio policy, encoded contracts, and
first-person camera continuity remain hard gates. Motion, relation, distance,
forward-cone blockage, and non-causal role conflicts are recorded from
realized telemetry and sent to review instead of triggering semantic retry
loops. Sustained lateral/backward blockage outside the +/-45 degree forward
cone is capture-valid but excluded from foundation training. The detector is a
high-confidence kinematic inference; exact surface contact normals are not
available in the current telemetry.

## Paths

- Scenarios: `{SCENARIOS_PATH}`
- Candidates: `{CANDIDATES_PATH}`
- Post-hoc camera/collision annotations: `{ANNOTATIONS_PATH}`
- Camera/collision audit: `{GEOMETRY_AUDIT_PATH}`
- Hard rejects: `{HARD_REJECTS_PATH}`
- Review decisions: `{REVIEW_DECISIONS_PATH}`
- HTML: `{PREVIEW_ROOT / 'index.html'}`
- Summary: `{SUMMARY_PATH}`

## Soft flags

```json
{json.dumps(result['soft_flag_counts'], indent=2, sort_keys=True)}
```

## What this preflight does not yet prove

- A long-lived DarkPlaces renderer process reused across episodes.
- Stable long-duration throughput at eight render workers; this bounded run
  provides one-, two-, and four-worker evidence only.
- Final Stage-1 global quota filling after human decisions.
- Formal raw-retention sampling and asynchronous checksum lock finalization.
- Exact server-side collision contact entity, point, and normal telemetry.
"""
    atomic_text(REPORT_PATH, text)
    print(str(REPORT_PATH))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--count", type=int, default=DEFAULT_COUNT)
    generate.set_defaults(func=command_generate)
    collect = sub.add_parser("collect")
    collect.add_argument("--workers", type=int, default=1)
    collect.add_argument("--limit", type=int, default=0)
    collect.add_argument(
        "--episode",
        action="append",
        help="Run only this planned episode ID; may be repeated.",
    )
    collect.add_argument(
        "--max-operational-attempts", type=int, default=2
    )
    collect.add_argument(
        "--retry-terminal",
        action="store_true",
        help=(
            "Reopen terminal failures only for explicitly supplied "
            "--episode IDs; prior rejection records remain immutable."
        ),
    )
    collect.set_defaults(func=command_collect)
    status = sub.add_parser("status")
    status.set_defaults(func=command_status)
    recover = sub.add_parser("recover")
    recover.set_defaults(func=command_recover)
    rescan = sub.add_parser("rescan-geometry")
    rescan.set_defaults(func=command_rescan_geometry)
    audit = sub.add_parser("audit")
    audit.add_argument("--hash-workers", type=int, default=4)
    audit.set_defaults(func=command_audit)
    html_parser = sub.add_parser("html")
    html_parser.add_argument("--preview-workers", type=int, default=4)
    html_parser.set_defaults(func=command_html)
    ingest = sub.add_parser("ingest-review")
    ingest.add_argument("path")
    ingest.set_defaults(func=command_ingest_review)
    report = sub.add_parser("report")
    report.set_defaults(func=command_report)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
