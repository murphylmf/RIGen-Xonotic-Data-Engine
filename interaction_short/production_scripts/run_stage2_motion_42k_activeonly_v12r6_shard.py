                      
"""Run one restartable Stage-2 v12r6 shard to an exact accepted quota.

The shard process remains restartable forever at the launcher level, but an
individual candidate gets at most two attempts.  Deterministic semantic QA,
including prefrozen player-trace recertification, is terminal after its first
complete capture and must never destroy a healthy resident lane.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD_TAG = "capture-ee4c0aac65db-aarch64"
SOURCE_COMMIT = "ee4c0aac65dbac689904b320c7db4e43dfd93d20"
BUILD_LOCK = ROOT / "locks" / f"{BUILD_TAG}.sha256"
REQUIRED_DEPENDENCY_LOCKS = {
    "locks/stage2_weapon_balanced_review_v3_base_traces.sha256",
    "locks/stage2_prefrozen_player_motion_states.sha256",
}
FORBIDDEN_RECORD_FIELDS = {
    "counterfactual_episode_id",
    "frozen_artifact_hashes",
    "pair_qa_path",
    "pair_qa_sha256",
    "pair_checks",
}

os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault("XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG", BUILD_TAG)
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT", SOURCE_COMMIT
)
os.environ.setdefault("XONOTIC_BUILD_GLOB", f"build/{BUILD_TAG}")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "production_scripts"))

import run_stage2_motion_40k_shard_v12_support as paired              
from pilot_scripts import build_samples_v12 as pilot              
import xonotic_stage1_reusable as reusable              

paired.pilot = pilot


canonical_json = paired.canonical_json
atomic_json = paired.atomic_json
load_jsonl = paired.load_jsonl
append_jsonl = paired.append_jsonl
preflight_gpu = paired.preflight_gpu
gpu_runtime_sample = paired.gpu_runtime_sample
verify_build_lock = paired.verify_build_lock
archive_partial = paired.archive_partial
Stage2ResidentLaneController = paired.Stage2ResidentLaneController
NON_RETRYABLE_CAPTURE_QA_CHECKS = {
    "prefrozen_player_trace_runtime_recertified",
}
RETRYABLE_PRE_PAIR_QA_CHECKS = (
    paired.RETRYABLE_PRE_PAIR_QA_CHECKS
    - NON_RETRYABLE_CAPTURE_QA_CHECKS
)


def resident_lane_plans(
    rows: list[dict[str, Any]], workers: int
) -> list[list[tuple[tuple[str, str], list[dict[str, Any]]]]]:
    """Deterministically balance active-only rows without crossing worlds."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        scenario = row["active_scenario"]
        key = (
            str(scenario["map"]),
            str(scenario.get("gametype", "dm")).lower(),
        )
        grouped.setdefault(key, []).append(row)
    ideal = max(1, (len(rows) + workers - 1) // workers)
    chunks: list[tuple[tuple[str, str], list[dict[str, Any]]]] = []
    for key, values in sorted(grouped.items()):
        ordered = sorted(
            values,
            key=lambda row: (int(row["ordinal"]), str(row["sample_key"])),
        )
        chunk_count = max(1, (len(ordered) + ideal - 1) // ideal)
        for chunk_index in range(chunk_count):
            start = chunk_index * len(ordered) // chunk_count
            end = (chunk_index + 1) * len(ordered) // chunk_count
            chunks.append((key, ordered[start:end]))
    chunks.sort(
        key=lambda item: (
            -len(item[1]),
            item[0],
            int(item[1][0]["ordinal"]),
            str(item[1][0]["sample_key"]),
        )
    )
    plans: list[
        list[tuple[tuple[str, str], list[dict[str, Any]]]]
    ] = [[] for _ in range(workers)]
    loads = [0] * workers
    for chunk in chunks:
        lane_index = min(
            range(workers), key=lambda index: (loads[index], index)
        )
        plans[lane_index].append(chunk)
        loads[lane_index] += len(chunk[1])
    return plans


def validate_manifest(
    manifest_path: Path,
    metadata_path: Path,
    shard_index: int,
    shard_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    declared_locks = metadata.get("runtime_dependency_locks") or {}
    dependency_checks: dict[str, bool] = {}
    for relative, digest in declared_locks.items():
        lock = ROOT / relative
        hash_matches = lock.is_file() and pilot.sha256_file(lock) == digest
        contents_match = False
        if hash_matches:
            completed = subprocess.run(
                ["sha256sum", "-c", str(lock)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            contents_match = completed.returncode == 0
        dependency_checks[relative] = hash_matches and contents_match
    declared = next(
        (
            row
            for row in metadata.get("shards", [])
            if int(row.get("shard_index", -1)) == shard_index
        ),
        None,
    )
    runtime_files = metadata.get("runtime_files") or {}
    checks = {
        "schema_v12_activeonly": metadata.get("schema_version")
        == "xonotic-stage2-motion-near5-combo-manifest-metadata-v12-replenish",
        "capture_mode_active_only": metadata.get("capture_mode") == "active_only",
        "rendered_episode_rows_42000": int(
            metadata.get("rendered_episode_rows", -1)
        )
        == 42_000,
        "candidate_rows_52500": int(metadata.get("candidate_rows", -1))
        == 52_500,
        "counterfactual_qa_rows_zero": int(
            metadata.get("counterfactual_qa_rows", -1)
        )
        == 0,
        "formal_collection_authorized": metadata.get(
            "formal_collection_authorized"
        )
        is True,
        "training_admitted_false": metadata.get("training_admitted") is False,
        "source_commit": metadata.get("source_commit") == SOURCE_COMMIT,
        "build_tag": metadata.get("build_tag") == BUILD_TAG,
        "live_time_scale_matches_runtime": int(
            metadata.get("live_time_scale", -1)
        )
        == reusable.configured_live_time_scale(),
        "shard_count": int(metadata.get("shard_count", -1)) == shard_count,
        "shard_declared": declared is not None,
        "build_lock_hash": metadata.get("build_lock_sha256")
        == pilot.sha256_file(BUILD_LOCK),
        "runtime_files": bool(runtime_files)
        and all(
            (ROOT / relative).is_file()
            and pilot.sha256_file(ROOT / relative) == digest
            for relative, digest in runtime_files.items()
        ),
        "runtime_dependency_locks": set(declared_locks)
        == REQUIRED_DEPENDENCY_LOCKS
        and all(dependency_checks.values()),
    }
    if declared is not None:
        checks.update(
            {
                "shard_path": Path(declared["path"]).name == manifest_path.name,
                "shard_hash": declared["sha256"]
                == pilot.sha256_file(manifest_path),
                "shard_candidate_rows_1875": int(declared["rows"]) == 1_875,
                "shard_target_accepted_rows_1500": int(
                    declared["target_accepted_rows"]
                )
                == 1_500,
            }
        )
    if not all(checks.values()):
        raise RuntimeError(f"active-only manifest metadata checks failed: {checks}")
    rows = load_jsonl(manifest_path)
    keys = [str(row.get("sample_key", "")) for row in rows]
    row_checks = {
        "rows_declared": declared is not None
        and len(rows) == int(declared["rows"]),
        "row_schema_v12": all(
            row.get("schema_version")
            == "xonotic-stage2-motion-near5-combo-production-active-v12-replenish"
            for row in rows
        ),
        "capture_mode_active_only": all(
            row.get("capture_mode") == "active_only" for row in rows
        ),
        "no_frozen_scenario": all("frozen_scenario" not in row for row in rows),
        "sample_keys_present": all(keys),
        "sample_keys_unique": len(keys) == len(set(keys)),
        "assigned_shard": all(
            int(row.get("assigned_shard", -1)) == shard_index for row in rows
        ),
        "shard_count": all(
            int(row.get("shard_count", -1)) == shard_count for row in rows
        ),
        "candidate_role": all(
            row.get("candidate_role") in {"primary", "reserve"} for row in rows
        ),
        "active_authorized": all(
            row["active_scenario"].get("formal_collection_authorized") is True
            and row["active_scenario"].get("training_admitted") is False
            and row["active_scenario"].get("source_commit_required")
            == SOURCE_COMMIT
            for row in rows
        ),
        "moving_trace_recertification_declared": all(
            row["active_scenario"]
            .get("prefrozen_trace_source", {})
            .get("runtime_recertification", {})
            .get("live_fail_closed")
            is True
            for row in rows
            if row["budget_token"]["player_motion_class"]
            == "certified_prefrozen_trace_replay"
        ),
        "prefrozen_seed_relation_declared": all(
            isinstance(
                row["active_scenario"]
                .get("prefrozen_trace_source", {})
                .get("source_action_seed"),
                int,
            )
            and row["active_scenario"]
            .get("prefrozen_trace_source", {})
            .get("scenario_seed_relation")
            == (
                "matches_source_action_seed"
                if row["candidate_role"] == "primary"
                else "independent_replenishment_scenario_seed"
            )
            for row in rows
            if row["budget_token"]["player_motion_class"]
            == "certified_prefrozen_trace_replay"
        ),
        "enemy_motion_basis_no_live_reads": all(
            row["active_scenario"]
            .get("enemy_motion_basis", {})
            .get("reads_camera")
            is False
            and row["active_scenario"]
            .get("enemy_motion_basis", {})
            .get("reads_live_player_state")
            is False
            for row in rows
        ),
        "postdeath_lock_required": all(
            row["active_scenario"].get("postdeath_motion_lock_required") is True
            for row in rows
        ),
        "jump_program_is_exogenous": all(
            (row["active_scenario"].get("enemy_jump_program") or {}).get(
                "reads_camera"
            )
            is False
            and (row["active_scenario"].get("enemy_jump_program") or {}).get(
                "reads_crosshair"
            )
            is False
            and (row["active_scenario"].get("enemy_jump_program") or {}).get(
                "reads_live_player_state"
            )
            is False
            for row in rows
        ),
    }
    if not all(row_checks.values()):
        raise RuntimeError(f"active-only manifest row checks failed: {row_checks}")
    return rows, {
        "metadata_checks": checks,
        "runtime_dependency_checks": dependency_checks,
        "row_checks": row_checks,
        "target_accepted_rows": int(declared["target_accepted_rows"]),
        "candidate_rows": int(declared["rows"]),
    }


def active_artifact_hashes(episode_path: Path) -> dict[str, str]:
    paths = (
        "scenario.json",
        "prompt.json",
        "qa.json",
        "media/source_64hz.mkv",
        "media/review_20hz_81f.mp4",
        "telemetry/actions_requested_64hz.parquet",
        "telemetry/actions_engine_64hz.parquet",
        "telemetry/states_64hz.parquet",
        "telemetry/events_64hz.parquet",
        "telemetry/frames_64hz.parquet",
        "telemetry/visibility_64hz.parquet",
        "raw/source.dem",
        "raw/server.jsonl",
    )
    result: dict[str, str] = {}
    for relative in paths:
        path = episode_path / relative
        if path.is_file():
            result[relative] = pilot.sha256_file(path)
    return result


def verify_accepted_record(journal_row: dict[str, Any]) -> bool:
    record_path = Path(str(journal_row.get("record_path", "")))
    if (
        not record_path.is_file()
        or pilot.sha256_file(record_path) != journal_row.get("record_sha256")
    ):
        return False
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("schema_version") != (
        "xonotic-stage2-motion-near5-combo-captured-sample-v12-replenish"
    ):
        return False
    if FORBIDDEN_RECORD_FIELDS & set(record):
        return False
    if record.get("capture_qa_passed") is not True:
        return False
    if record.get("postdeath_motion_lock_required") is not True:
        return False
    active_path = Path(record["video_path"]).parents[1]
    hashes = record.get("active_artifact_hashes") or {}
    required = {
        "scenario.json",
        "prompt.json",
        "qa.json",
        "media/source_64hz.mkv",
        "media/review_20hz_81f.mp4",
        "telemetry/actions_requested_64hz.parquet",
        "telemetry/states_64hz.parquet",
        "telemetry/events_64hz.parquet",
        "telemetry/visibility_64hz.parquet",
        "raw/source.dem",
        "raw/server.jsonl",
    }
    if not required <= set(hashes):
        return False
    if any(not (active_path / relative).is_file() for relative in hashes):
        return False
                                                                            
                                                                           
                                                                              
    for relative in ("scenario.json", "prompt.json", "qa.json"):
        if pilot.sha256_file(active_path / relative) != hashes[relative]:
            return False
    if record.get("capture_mode") == "active_only_v12_compatible_carryover":
        audit = record.get("postdeath_motion_audit") or {}
        if record.get("actual_outcome") == "kill":
            legacy_locked = audit.get("status") == "postdeath_locked"
            v11_locked = (
                audit.get("passed") is True
                and float(audit.get("maximum_xyz_displacement_units", 1e9))
                <= 0.1
            )
            if not (legacy_locked or v11_locked):
                return False
    else:
        qa = json.loads((active_path / "qa.json").read_text(encoding="utf-8"))
        checks = qa.get("checks") or {}
        if checks.get("enemy_world_motion_locked_after_death") is not True:
            return False
        if record.get("enemy_jumps") and checks.get(
            "enemy_jump_program_realized"
        ) is not True:
            return False
    return True


def training_candidate_record(
    row: dict[str, Any], active: dict[str, Any]
) -> dict[str, Any]:
    active_path = Path(active["episode_path"])
    return {
        "schema_version": "xonotic-stage2-motion-near5-combo-captured-sample-v12-replenish",
        "capture_mode": "active_only",
        "qa_mode": "single_episode_authoritative",
        "admission_uses_pair_qa": False,
        "sample_id": active["episode_id"],
        "sample_key": row["sample_key"],
        "ordinal": int(row["ordinal"]),
        "training_admitted": False,
        "capture_qa_passed": True,
        "video_path": str(active_path / "media/review_20hz_81f.mp4"),
        "source_video_path": str(active_path / "media/source_64hz.mkv"),
        "action_path": str(active_path / "telemetry/actions_requested_64hz.parquet"),
        "state_path": str(active_path / "telemetry/states_64hz.parquet"),
        "visibility_path": str(active_path / "telemetry/visibility_64hz.parquet"),
        "prompt_path": str(active_path / "prompt.json"),
        "prompt_text": active["prompt"]["prompt_text"],
        "actual_outcome": active["qa"]["interaction"]["actual_outcome"],
        "intent_outcome": active["scenario"]["intent_outcome"],
        "outcome_recipe_is_individual_admission_gate": False,
        "weapon": active["scenario"]["weapon"],
        "map": active["scenario"]["map"],
        "enemy_model": active["scenario"]["enemy_model"],
        "enemy_skin": int(active["scenario"]["enemy_skin"]),
        "enemy_color": int(active["scenario"]["enemy_color"]),
        "player_motion_class": active["scenario"]["formal_design"][
            "player_motion_class"
        ],
        "enemy_motion": active["scenario"]["formal_design"][
            "target_motion_name"
        ],
        "enemy_jumps": bool(
            (active["scenario"].get("enemy_jump_program") or {}).get("enabled")
        ),
        "enemy_jump_program": active["scenario"].get("enemy_jump_program"),
        "postdeath_motion_lock_required": bool(
            active["scenario"].get("postdeath_motion_lock_required")
        ),
        "postdeath_motion_audit": active["qa"]["motion"]["postdeath_lock"],
        "enemy_jump_qa": active["qa"]["motion"]["jump"],
        "distance_tier": active["scenario"]["distance_tier"],
        "target_initial_distance_units": active["scenario"][
            "target_initial_distance_units"
        ],
        "actual_initial_distance_units": active["qa"]["screen_distance"][
            "initial_distance_world"
        ],
        "minimum_enemy_screen_height_pixels": active["qa"]["screen_distance"][
            "minimum_height_pixels"
        ],
        "active_artifact_hashes": active_artifact_hashes(active_path),
        "source_formal_episode_id": row["source_formal_episode_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=28)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--execution-mode",
        choices=("resident", "oneshot"),
        default=os.environ.get("XONOTIC_STAGE2_EXECUTION_MODE", "resident"),
    )
    parser.add_argument(
        "--encode-concurrency",
        type=int,
        default=int(os.environ.get("XONOTIC_ENCODE_CONCURRENCY", "8")),
    )
    parser.add_argument(
        "--render-concurrency",
        type=int,
        default=int(os.environ.get("XONOTIC_RENDER_CONCURRENCY", "8")),
    )
    parser.add_argument(
        "--live-concurrency",
        type=int,
        default=int(os.environ.get("XONOTIC_LIVE_CONCURRENCY", "8")),
    )
    parser.add_argument(
        "--x264-threads",
        type=int,
        default=int(os.environ.get("XONOTIC_X264_THREADS", "4")),
    )
    parser.add_argument(
        "--x264-cpuset", default=os.environ.get("XONOTIC_X264_CPUSET", "")
    )
    parser.add_argument(
        "--render-timeout-seconds",
        type=float,
        default=float(os.environ.get("XONOTIC_RENDER_TIMEOUT_SECONDS", "240")),
    )
    parser.add_argument(
        "--resident-control-timeout-seconds",
        type=float,
        default=float(
            os.environ.get("XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "240")
        ),
    )
    parser.add_argument("--port-base", type=int, default=26000)
    parser.add_argument("--max-operational-attempts", type=int, default=2)
    parser.add_argument("--start-sample", type=int, default=0)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--allow-partial-smoke", action="store_true")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.shard_index < args.shard_count:
        parser.error("--shard-index must be inside the shard range")
    for name in ("workers", "encode_concurrency", "render_concurrency", "live_concurrency"):
        if not 1 <= int(getattr(args, name)) <= 16:
            parser.error(f"--{name.replace('_', '-')} must be between 1 and 16")
    if not 1 <= args.x264_threads <= 64:
        parser.error("--x264-threads must be between 1 and 64")
    if not 30 <= args.render_timeout_seconds <= 3600:
        parser.error("--render-timeout-seconds must be between 30 and 3600")
    if not 30 <= args.resident_control_timeout_seconds <= 600:
        parser.error("--resident-control-timeout-seconds must be between 30 and 600")
    if not 1 <= args.max_operational_attempts <= 2:
        parser.error("--max-operational-attempts must be between 1 and 2")
    if args.max_samples is not None and (
        args.max_samples < 1 or not args.allow_partial_smoke
    ):
        parser.error("--max-samples requires --allow-partial-smoke")
    if args.start_sample < 0 or (
        args.start_sample and not args.allow_partial_smoke
    ):
        parser.error("--start-sample must be nonnegative and requires --allow-partial-smoke")

    cpu_isolation = None
    if args.execution_mode == "resident":
        cpu_isolation = reusable.configure_resident_cpu_isolation(
            args.workers, requested_x264_cpuset=args.x264_cpuset
        )
        args.x264_cpuset = os.environ["XONOTIC_X264_CPUSET"]

    manifest = args.manifest.resolve()
    metadata = args.metadata.resolve()
    output_root = args.output_root.resolve()
    scratch_root = args.scratch_root.resolve()
    shard_root = output_root / f"shard_{args.shard_index:02d}"
    shard_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lock_handle = (shard_root / "SHARD.lock").open("a+b")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError(f"shard already has an active owner: {shard_root}") from exc

    verify_build_lock()
    rows, manifest_checks = validate_manifest(
        manifest, metadata, args.shard_index, args.shard_count
    )
    target_accepted_rows = int(manifest_checks["target_accepted_rows"])
    if args.start_sample >= len(rows):
        parser.error(
            f"--start-sample {args.start_sample} is outside {len(rows)} manifest rows"
        )
    rows = rows[args.start_sample :]
    if args.max_samples is not None:
        rows = rows[: args.max_samples]
    if args.start_sample or args.max_samples is not None:
        target_accepted_rows = min(target_accepted_rows, len(rows))
    gpu = preflight_gpu()
    os.environ["XONOTIC_LIVE_CONCURRENCY"] = str(args.live_concurrency)
    os.environ["XONOTIC_RENDER_CONCURRENCY"] = str(args.render_concurrency)
    os.environ["XONOTIC_SDL_CONCURRENCY"] = str(args.workers)
    os.environ["XONOTIC_ENCODE_CONCURRENCY"] = str(args.encode_concurrency)
    os.environ["XONOTIC_X264_THREADS"] = str(args.x264_threads)
    os.environ["XONOTIC_X264_CPUSET"] = args.x264_cpuset
    os.environ["XONOTIC_RENDER_TIMEOUT_SECONDS"] = str(args.render_timeout_seconds)
    os.environ["XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS"] = str(
        args.resident_control_timeout_seconds
    )
    os.environ["XONOTIC_OFFLINE_ACCELERATE"] = "1"
    pilot.run_protection_check(shard_root / "STAGE12_PRECHECK.txt")

    accepted_journal = shard_root / "manifests/accepted.jsonl"
    rejected_journal = shard_root / "manifests/rejected.jsonl"
    accepted_rows = load_jsonl(accepted_journal)
    accepted_by_key = {str(row["sample_key"]): row for row in accepted_rows}
    if len(accepted_by_key) != len(accepted_rows):
        raise RuntimeError("accepted journal has duplicate sample_key rows")
    manifest_keys = {str(row["sample_key"]) for row in rows}
    unexpected = set(accepted_by_key) - manifest_keys
    if unexpected:
        raise RuntimeError(f"accepted rows outside manifest shard: {sorted(unexpected)[:5]}")
    for key, journal in accepted_by_key.items():
        if not verify_accepted_record(journal):
            raise RuntimeError(f"accepted active artifact integrity failed: {key}")
    rejected_rows = load_jsonl(rejected_journal)
    rejected_keys = {str(row["sample_key"]) for row in rejected_rows}
    unexpected_rejected = rejected_keys - manifest_keys
    if unexpected_rejected:
        raise RuntimeError(
            "rejected rows outside manifest shard: "
            f"{sorted(unexpected_rejected)[:5]}"
        )
    if accepted_by_key.keys() & rejected_keys:
        raise RuntimeError("sample key appears in both accepted and rejected journals")
    if len(accepted_by_key) > target_accepted_rows:
        raise RuntimeError(
            f"accepted quota overshoot: {len(accepted_by_key)} > {target_accepted_rows}"
        )
    pending_rows = [
        row
        for row in rows
        if str(row["sample_key"]) not in accepted_by_key
        and str(row["sample_key"]) not in rejected_keys
    ]
    initial_accepted_count = len(accepted_by_key)
    accepted_keys = set(accepted_by_key)
    accepted_lock = threading.Lock()
    build = pilot.capture.build_root()
    lane_plans = (
        resident_lane_plans(pending_rows, args.workers)
        if args.execution_mode == "resident"
        else None
    )
    port_queue: queue.Queue[int] = queue.Queue()
    if args.execution_mode == "oneshot":
        for offset in range(args.workers):
            port_queue.put(args.port_base + offset)

    run_metadata = {
        "schema_version": "xonotic-stage2-motion-near5-combo-dlc-shard-run-v12-replenish",
        "started_utc": pilot.capture.utc_now(),
        "capture_mode": "active_only",
        "qa_mode": "single_episode_authoritative",
        "rendered_counterfactual_required": False,
        "manifest": str(manifest),
        "manifest_sha256": pilot.sha256_file(manifest),
        "metadata": str(metadata),
        "metadata_sha256": pilot.sha256_file(metadata),
        "manifest_checks": manifest_checks,
        "output_root": str(output_root),
        "scratch_root": str(scratch_root),
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "manifest_samples": len(rows),
        "manifest_slice_start": args.start_sample,
        "target_accepted_samples": target_accepted_rows,
        "carryover_accepted": len(accepted_by_key),
        "terminal_rejected_candidates": len(rejected_keys),
        "planned_new_active_captures": len(pending_rows),
        "workers": args.workers,
        "execution_mode": args.execution_mode,
        "offline_accelerate": True,
        "global_phase_barrier": args.execution_mode == "resident",
        "live_time_scale": reusable.configured_live_time_scale(),
        "encode_concurrency": args.encode_concurrency,
        "render_concurrency": args.render_concurrency,
        "live_concurrency": args.live_concurrency,
        "x264_threads": args.x264_threads,
        "x264_cpuset": args.x264_cpuset,
        "resident_cpu_isolation": cpu_isolation,
        "render_timeout_seconds": args.render_timeout_seconds,
        "resident_control_timeout_seconds": args.resident_control_timeout_seconds,
        "port_base": args.port_base,
        "gpu": gpu,
        "build_tag": BUILD_TAG,
        "source_commit": SOURCE_COMMIT,
        "raw_avi_audit_percent_active": 5,
        "operational_retry_policy": {
            "job_level_supervision": "infinite_launcher_restart_and_idle_hold",
            "max_candidate_attempts": args.max_operational_attempts,
            "nonretryable_capture_qa_checks": sorted(
                NON_RETRYABLE_CAPTURE_QA_CHECKS
            ),
            "semantic_qa_invalidates_resident_lane": False,
        },
    }
    atomic_json(shard_root / "RUN_METADATA.json", run_metadata)
    print(canonical_json({"event": "activeonly_shard_start", **run_metadata}), flush=True)

    def accept(row: dict[str, Any], active: dict[str, Any]) -> dict[str, Any]:
        sample_key = str(row["sample_key"])
        record = training_candidate_record(row, active)
        record_path = shard_root / "records" / f"{sample_key}.json"
        atomic_json(record_path, record)
        journal = {
            "schema_version": "xonotic-stage2-motion-near5-combo-accepted-v12-replenish",
            "sample_key": sample_key,
            "ordinal": int(row["ordinal"]),
            "record_path": str(record_path),
            "record_sha256": pilot.sha256_file(record_path),
            "actual_outcome": record["actual_outcome"],
            "accepted_utc": pilot.capture.utc_now(),
            "acceptance_source": "v12_replenished_active_capture",
        }
        append_jsonl(accepted_journal, journal)
        with accepted_lock:
            accepted_keys.add(sample_key)
            accepted_by_key[sample_key] = journal
        return {
            "sample_key": sample_key,
            "status": "accepted",
            "actual_outcome": record["actual_outcome"],
        }

    def reject_active_qa(row: dict[str, Any], active: dict[str, Any]) -> dict[str, Any]:
        sample_key = str(row["sample_key"])
        append_jsonl(
            rejected_journal,
            {
                "schema_version": "xonotic-stage2-motion-near5-combo-reject-v12-replenish",
                "sample_key": sample_key,
                "ordinal": int(row["ordinal"]),
                "role": "active",
                "reason": "active_authoritative_qa_failed",
                "failed_checks": sorted(
                    key for key, passed in active["qa"]["checks"].items() if not passed
                ),
                "episode_path": active["episode_path"],
                "rejected_utc": pilot.capture.utc_now(),
                "retry_policy": "terminal_nonretryable_qa",
            },
        )
        return {"sample_key": sample_key, "status": "rejected"}

    def reject_operational(
        row: dict[str, Any], phase: str, error: Exception
    ) -> dict[str, Any]:
        sample_key = str(row["sample_key"])
        append_jsonl(
            rejected_journal,
            {
                "schema_version": "xonotic-stage2-motion-near5-combo-reject-v12-replenish",
                "sample_key": sample_key,
                "ordinal": int(row["ordinal"]),
                "role": "active",
                "reason": "operational_attempts_exhausted",
                "phase": phase,
                "error_type": type(error).__name__,
                "error": str(error),
                "rejected_utc": pilot.capture.utc_now(),
                "max_candidate_attempts": args.max_operational_attempts,
            },
        )
        return {"sample_key": sample_key, "status": "rejected"}

    def process_oneshot(row: dict[str, Any]) -> dict[str, Any]:
        sample_key = str(row["sample_key"])
        scenario = row["active_scenario"]
        episode_id = str(scenario["episode_id"])
        port = port_queue.get()
        try:
            captured: dict[str, Any] | None = None
            destination = shard_root / "episodes" / episode_id
            if destination.is_dir():
                try:
                    captured = pilot.load_packaged_episode(shard_root, episode_id)
                except Exception as exc:
                    archive_partial(
                        shard_root,
                        scratch_root,
                        episode_id,
                        0,
                        f"resume_validation_failed: {exc}",
                    )
            last_error: Exception | None = None
            for attempt in range(1, args.max_operational_attempts + 1):
                if captured is not None:
                    break
                try:
                    captured = pilot.capture_episode(
                        scenario,
                        shard_root,
                        scratch_root,
                        port=port,
                        cleanup_scratch=True,
                        retain_raw_avi=bool(row["raw_avi_audit"]),
                    )
                    failed = {
                        key
                        for key, passed in captured["qa"]["checks"].items()
                        if not passed
                    }
                    retryable = sorted(failed & RETRYABLE_PRE_PAIR_QA_CHECKS)
                    if retryable:
                        raise RuntimeError(
                            "retryable_active_qa_failed:" + ",".join(retryable)
                        )
                except Exception as exc:
                    last_error = exc
                    archive_partial(
                        shard_root,
                        scratch_root,
                        episode_id,
                        attempt,
                        f"{type(exc).__name__}: {exc}",
                    )
                    captured = None
            if captured is None:
                assert last_error is not None
                return reject_operational(row, "oneshot_capture", last_error)
            if not captured["qa"]["pre_pair_passed"]:
                return reject_active_qa(row, captured)
            return accept(row, captured)
        finally:
            port_queue.put(port)

    results: list[dict[str, Any]] = []
    progress_lock = threading.Lock()
    completed_new = 0

    def record_progress(result: dict[str, Any]) -> None:
        nonlocal completed_new
        with progress_lock:
            results.append(result)
            completed_new += 1
            runtime_gpu = (
                gpu_runtime_sample()
                if completed_new == 1 or completed_new % 25 == 0
                else None
            )
            print(
                canonical_json(
                    {
                        "event": "activeonly_progress",
                        "completed_new": completed_new,
                        "planned_new": len(pending_rows),
                        "carryover_accepted": initial_accepted_count,
                        "accepted_total": len(accepted_by_key),
                        "accepted_target": target_accepted_rows,
                        **(
                            {"gpu_runtime_sample": runtime_gpu}
                            if runtime_gpu is not None
                            else {}
                        ),
                        **result,
                    }
                ),
                flush=True,
            )

    phase_timeline = shard_root / "manifests/phase_timeline.jsonl"
    phase_sequence = 0

    def phase_event(payload: dict[str, Any]) -> None:
        nonlocal phase_sequence
        phase_sequence += 1
        append_jsonl(
            phase_timeline,
            {
                "schema_version": "xonotic-stage2-activeonly-phase-barrier-v1",
                "sequence": phase_sequence,
                "created_utc": pilot.capture.utc_now(),
                **payload,
            },
        )

    def archive_attempt(item: dict[str, Any], attempt: int, error: str) -> list[dict[str, Any]]:
        row = item["row"]
        episode_id = str(row["active_scenario"]["episode_id"])
        if not (
            (shard_root / "episodes" / episode_id).exists()
            or (scratch_root / episode_id).exists()
        ):
            return []
        return [
            archive_partial(
                shard_root, scratch_root, episode_id, attempt, error
            )
        ]

    def record_live(item: dict[str, Any], attempt: int) -> dict[str, Any]:
        row = item["row"]
        print(
            canonical_json(
                {
                    "event": "activeonly_authoritative_demo_start",
                    "batch_index": item["batch_index"],
                    "sample_key": row["sample_key"],
                    "episode_id": row["active_scenario"]["episode_id"],
                    "attempt": attempt,
                    "lane_index": item["lane_index"],
                    "resident_generation": item["controller"].generation,
                }
            ),
            flush=True,
        )
        return pilot.record_episode_live_phase(
            row["active_scenario"],
            shard_root,
            scratch_root,
            port=item["port"],
            resident_lane=item["lane"],
        )

    def replay_capture(
        item: dict[str, Any], attempt: int, prepared: dict[str, Any]
    ) -> dict[str, Any]:
        row = item["row"]
        print(
            canonical_json(
                {
                    "event": "activeonly_offline_replay_start",
                    "batch_index": item["batch_index"],
                    "sample_key": row["sample_key"],
                    "attempt": attempt,
                    "lane_index": item["lane_index"],
                }
            ),
            flush=True,
        )
        captured = pilot.capture_episode(
            row["active_scenario"],
            shard_root,
            scratch_root,
            port=item["port"],
            cleanup_scratch=True,
            retain_raw_avi=bool(row["raw_avi_audit"]),
            resident_lane=item["lane"],
            prepared_live_phase=prepared,
        )
        failed = {
            key
            for key, passed in captured["qa"]["checks"].items()
            if not passed
        }
        retryable = sorted(failed & RETRYABLE_PRE_PAIR_QA_CHECKS)
        if retryable:
            raise RuntimeError("retryable_active_qa_failed:" + ",".join(retryable))
        return captured

    def finalize(item: dict[str, Any], active: dict[str, Any]) -> dict[str, Any]:
        if not active["qa"]["pre_pair_passed"]:
            return reject_active_qa(item["row"], active)
        return accept(item["row"], active)

    def execute_microbatch(
        batch: list[dict[str, Any]],
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        pending = list(batch)
        attempts = {str(item["row"]["sample_key"]): 1 for item in pending}
        while pending:
            ready: list[dict[str, Any]] = []
            warmup_retry: list[dict[str, Any]] = []
            for item in pending:
                key = str(item["row"]["sample_key"])
                attempt = attempts[key]
                try:
                    item["lane"] = item["controller"].get_lane(
                        item["row"]["active_scenario"]
                    )
                    ready.append(item)
                except Exception as exc:
                    item["controller"].invalidate()
                    if attempt >= args.max_operational_attempts:
                        record_progress(reject_operational(item["row"], "serialized_warmup", exc))
                    else:
                        attempts[key] = attempt + 1
                        warmup_retry.append(item)

            live_success: list[tuple[dict[str, Any], dict[str, Any]]] = []
            live_retry: list[dict[str, Any]] = []
            if ready:
                keys = [str(item["row"]["sample_key"]) for item in ready]
                started = time.monotonic()
                phase_event(
                    {
                        "event": "activeonly_authoritative_batch_start",
                        "batch_index": ready[0]["batch_index"],
                        "sample_keys": keys,
                        "sample_count": len(ready),
                        "offline_replay_active": False,
                    }
                )
                futures = {
                    executor.submit(record_live, item, attempts[str(item["row"]["sample_key"])]): item
                    for item in ready
                }
                for future in concurrent.futures.as_completed(futures):
                    item = futures[future]
                    key = str(item["row"]["sample_key"])
                    attempt = attempts[key]
                    try:
                        live_success.append((item, future.result()))
                    except Exception as exc:
                        item["controller"].invalidate()
                        diagnostics = archive_attempt(
                            item, attempt, f"{type(exc).__name__}: {exc}"
                        )
                        print(
                            canonical_json(
                                {
                                    "event": "activeonly_authoritative_retry",
                                    "sample_key": key,
                                    "attempt": attempt,
                                    "error": f"{type(exc).__name__}: {exc}",
                                    "diagnostics": diagnostics,
                                }
                            ),
                            flush=True,
                        )
                        if attempt >= args.max_operational_attempts:
                            record_progress(reject_operational(item["row"], "authoritative_demo", exc))
                        else:
                            attempts[key] = attempt + 1
                            live_retry.append(item)
                phase_event(
                    {
                        "event": "activeonly_authoritative_batch_complete",
                        "batch_index": ready[0]["batch_index"],
                        "sample_keys": keys,
                        "successful_samples": len(live_success),
                        "wall_seconds": time.monotonic() - started,
                        "offline_replay_active": False,
                    }
                )

            render_retry: list[dict[str, Any]] = []
            if live_success:
                keys = [str(item["row"]["sample_key"]) for item, _ in live_success]
                started = time.monotonic()
                phase_event(
                    {
                        "event": "activeonly_global_stage_barrier_passed",
                        "batch_index": live_success[0][0]["batch_index"],
                        "sample_keys": keys,
                        "authoritative_recordings_complete": True,
                    }
                )
                futures = {
                    executor.submit(
                        replay_capture,
                        item,
                        attempts[str(item["row"]["sample_key"])],
                        prepared,
                    ): item
                    for item, prepared in live_success
                }
                for future in concurrent.futures.as_completed(futures):
                    item = futures[future]
                    key = str(item["row"]["sample_key"])
                    attempt = attempts[key]
                    try:
                        record_progress(finalize(item, future.result()))
                    except Exception as exc:
                        item["controller"].invalidate()
                        diagnostics = archive_attempt(
                            item, attempt, f"{type(exc).__name__}: {exc}"
                        )
                        print(
                            canonical_json(
                                {
                                    "event": "activeonly_offline_replay_retry",
                                    "sample_key": key,
                                    "attempt": attempt,
                                    "error": f"{type(exc).__name__}: {exc}",
                                    "diagnostics": diagnostics,
                                }
                            ),
                            flush=True,
                        )
                        if attempt >= args.max_operational_attempts:
                            record_progress(reject_operational(item["row"], "offline_replay_encode_qa", exc))
                        else:
                            attempts[key] = attempt + 1
                            render_retry.append(item)
                phase_event(
                    {
                        "event": "activeonly_offline_replay_batch_complete",
                        "batch_index": live_success[0][0]["batch_index"],
                        "sample_keys": keys,
                        "wall_seconds": time.monotonic() - started,
                        "authoritative_recording_active": False,
                    }
                )
            pending = warmup_retry + live_retry + render_retry

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        if args.execution_mode == "resident":
            if lane_plans is None:
                raise AssertionError("resident plans missing")
            sequences: list[list[dict[str, Any]]] = []
            for lane_index, groups in enumerate(lane_plans):
                sequence: list[dict[str, Any]] = []
                for group_index, (world_group, group_rows) in enumerate(groups, 1):
                    for row in group_rows:
                        sequence.append(
                            {
                                "lane_index": lane_index,
                                "group_index": group_index,
                                "world_group": world_group,
                                "row": row,
                                "port": args.port_base + lane_index,
                            }
                        )
                sequences.append(sequence)
            controllers: dict[int, Stage2ResidentLaneController] = {}
            try:
                batch_count = max((len(sequence) for sequence in sequences), default=0)
                for batch_index in range(batch_count):
                    remaining_accepts = target_accepted_rows - len(accepted_by_key)
                    if remaining_accepts <= 0:
                        break
                    batch: list[dict[str, Any]] = []
                    for lane_index, sequence in enumerate(sequences):
                                                                         
                                                                          
                                                                     
                        if len(batch) >= remaining_accepts:
                            break
                        if batch_index >= len(sequence):
                            continue
                        item = sequence[batch_index]
                        item["batch_index"] = batch_index
                        controller = controllers.get(lane_index)
                        if controller is not None and (
                            controller.group_index != item["group_index"]
                            or controller.world_group != item["world_group"]
                        ):
                            controller.close()
                            controller = None
                        if controller is None:
                            controller = Stage2ResidentLaneController(
                                lane_index=lane_index,
                                group_index=item["group_index"],
                                world_group=item["world_group"],
                                port=item["port"],
                                build=build,
                                shard_root=shard_root,
                                scratch_root=scratch_root,
                            )
                            controllers[lane_index] = controller
                        item["controller"] = controller
                        batch.append(item)
                    if batch:
                        execute_microbatch(batch, executor)
            finally:
                for controller in controllers.values():
                    controller.close()
        else:
            cursor = 0
            while (
                cursor < len(pending_rows)
                and len(accepted_by_key) < target_accepted_rows
            ):
                remaining_accepts = target_accepted_rows - len(accepted_by_key)
                batch = pending_rows[
                    cursor : cursor + min(args.workers, remaining_accepts)
                ]
                cursor += len(batch)
                futures = [executor.submit(process_oneshot, row) for row in batch]
                for future in concurrent.futures.as_completed(futures):
                    record_progress(future.result())

    pilot.run_protection_check(shard_root / "STAGE12_POSTCHECK.txt")
    accepted_final = load_jsonl(accepted_journal)
    rejected_final = load_jsonl(rejected_journal)
    unique_accepted = {str(row["sample_key"]): row for row in accepted_final}
    result = {
        **run_metadata,
        "finished_utc": pilot.capture.utc_now(),
        "accepted_samples": len(unique_accepted),
        "target_accepted_samples": target_accepted_rows,
        "newly_processed": len(results),
        "rejected_records": len(rejected_final),
        "unused_candidate_rows": len(rows)
        - len(unique_accepted)
        - len({str(row["sample_key"]) for row in rejected_final}),
        "actual_outcome_distribution": dict(
            sorted(Counter(row["actual_outcome"] for row in unique_accepted.values()).items())
        ),
        "final_gpu_runtime_sample": gpu_runtime_sample(),
        "pass": len(unique_accepted) == target_accepted_rows,
        "incomplete_is_nonfatal_for_distributed_completion": not args.fail_on_incomplete,
        "rendered_counterfactual_count": 0,
    }
    atomic_json(shard_root / "RUN_RESULT.json", result)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    if args.fail_on_incomplete and not result["pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
