                      
"""Run one explicit non-training manifest shard with restartable publication."""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import functools
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_capture_v2 as v2                   
import xonotic_motion_distance_pilot as motion              
import xonotic_stage1_review as review                   
import xonotic_stage1_routes as routes              
import xonotic_stage2_causal as stage2                   


EXPECTED_SOURCE_COMMIT = "fe8b4e847eff4b95e37f6adad31a2add6ddb746e"
RETRYABLE_REASONS = {
    "capture_port_unavailable",
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
    "lock_timeout",
    "route_calibration_qa_failed",
    "route_calibration_previous_failure",
    "resident_warmup_failed",
}
LOCK_RETRY_TIMEOUT_SECONDS = 120.0
JSONL_SNAPSHOT_READ_ATTEMPTS = 8
JSONL_SNAPSHOT_RETRY_SECONDS = 0.02
_JSONL_THREAD_LOCKS_GUARD = threading.Lock()
_JSONL_THREAD_LOCKS: dict[str, threading.RLock] = {}


def retryable_failure(exc: Exception) -> bool:
    reason = (
        exc.reason
        if isinstance(exc, capture.CaptureFailure)
        else type(exc).__name__
    )
    if reason in RETRYABLE_REASONS:
        return True
    if reason == "live_precheck_failed":
        detail = str(
            exc.detail
            if isinstance(exc, capture.CaptureFailure)
            else exc
        )
        return (
            '"desired_action_ticks":false' in detail
            or '"server_state_ticks":false' in detail
            or '"route_trace_contract":false' in detail
        )
    if reason == "qa_gate_failed":
        detail = str(
            exc.detail
            if isinstance(exc, capture.CaptureFailure)
            else exc
        )
        try:
            payload = json.loads(detail)
        except json.JSONDecodeError:
            return False
        failed = set(payload.get("failed") or [])
        retryable_gates = {
            "frame_tick_mapping",
            "event_linkage",
            "resource_deltas_explained",
            "first_person_camera_continuity",
            "expected_audio_non_silent",
        }
        return bool(failed) and failed <= retryable_gates
    return False


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def flock_with_retry(
    file_descriptor: int,
    operation: int,
    *,
    timeout_seconds: float = LOCK_RETRY_TIMEOUT_SECONDS,
) -> None:
    """Tolerate transient EAGAIN from advisory locks on shared AFS."""
    deadline = time.monotonic() + timeout_seconds
    delay = 0.01
    while True:
        try:
            fcntl.flock(file_descriptor, operation)
            return
        except InterruptedError:
            continue
        except BlockingIOError as exc:
            if operation & fcntl.LOCK_NB:
                raise
            if time.monotonic() >= deadline:
                raise capture.CaptureFailure(
                    "lock_timeout",
                    f"timeout_seconds={timeout_seconds}",
                ) from exc
            time.sleep(delay)
            delay = min(delay * 2, 0.25)


def _jsonl_thread_lock(path: Path) -> threading.RLock:
    """Return one process-local lock for every canonical JSONL path.

    ``flock`` protects cooperating file descriptors, including other
    processes, while this lock also gives deterministic ordering to the
    worker's resident lane threads.  Both are required on QuarkFS: relying
    only on a writer-side ``flock`` allowed an unlocked reader to observe a
    transiently incoherent append view.
    """

    key = os.path.realpath(os.path.abspath(os.fspath(path)))
    with _JSONL_THREAD_LOCKS_GUARD:
        lock = _JSONL_THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _JSONL_THREAD_LOCKS[key] = lock
        return lock


def _read_jsonl_snapshot(path: Path) -> bytes:
    """Read one stable byte snapshot while holding a shared file lock."""

    try:
        with path.open("rb", buffering=0) as handle:
            flock_with_retry(handle.fileno(), fcntl.LOCK_SH)
            return handle.read()
    except FileNotFoundError:
        return b""


def _parse_jsonl_snapshot(path: Path, snapshot: bytes) -> list[dict[str, Any]]:
    """Strictly parse an immutable JSONL snapshot without skipping damage."""

    if snapshot and not snapshot.endswith(b"\n"):
        line_number = snapshot.count(b"\n") + 1
        raise capture.CaptureFailure(
            "invalid_jsonl",
            f"{path}:{line_number}: missing final newline",
        )
    try:
        text = snapshot.decode("utf-8")
    except UnicodeDecodeError as exc:
        line_number = snapshot[: exc.start].count(b"\n") + 1
        raise capture.CaptureFailure(
            "invalid_jsonl",
            f"{path}:{line_number}: invalid UTF-8: {exc}",
        ) from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise capture.CaptureFailure(
                "invalid_jsonl", f"{path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise capture.CaptureFailure(
                "invalid_jsonl",
                f"{path}:{line_number}: row is not an object",
            )
        rows.append(value)
    return rows


def _jsonl_retry_delay(attempt: int) -> None:
    time.sleep(
        min(
            JSONL_SNAPSHOT_RETRY_SECONDS * (2**attempt),
            0.25,
        )
    )


def load_jsonl_locked(path: Path) -> list[dict[str, Any]]:
    """Load a mutable journal from a locked, stable QuarkFS snapshot.

    A malformed snapshot is never partially accepted.  The file is closed
    and reopened a bounded number of times so a transient QuarkFS visibility
    artifact can clear; persistent corruption remains a fatal
    ``invalid_jsonl`` failure.
    """

    path = Path(path)
    lock = _jsonl_thread_lock(path)
    last_failure: capture.CaptureFailure | None = None
    for attempt in range(JSONL_SNAPSHOT_READ_ATTEMPTS):
        with lock:
            snapshot = _read_jsonl_snapshot(path)
        try:
            return _parse_jsonl_snapshot(path, snapshot)
        except capture.CaptureFailure as exc:
            if exc.reason != "invalid_jsonl":
                raise
            last_failure = exc
        if attempt + 1 < JSONL_SNAPSHOT_READ_ATTEMPTS:
            print(
                "WARN transient_jsonl_snapshot_retry "
                f"path={path} attempt={attempt + 1}/"
                f"{JSONL_SNAPSHOT_READ_ATTEMPTS} "
                f"detail={last_failure.detail}",
                file=sys.stderr,
                flush=True,
            )
            _jsonl_retry_delay(attempt)
    assert last_failure is not None
    raise last_failure


def append_locked(
    path: Path,
    row: dict[str, Any],
    *,
    unique_field: str | None = None,
) -> bool:
    """Append one complete row under process-local and cross-process locks."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _jsonl_thread_lock(path)
    payload = (capture.canonical_json(row) + "\n").encode("utf-8")
    last_failure: capture.CaptureFailure | None = None
    for attempt in range(JSONL_SNAPSHOT_READ_ATTEMPTS):
        with lock:
            with path.open("a+b", buffering=0) as handle:
                flock_with_retry(handle.fileno(), fcntl.LOCK_EX)
                if unique_field is not None:
                    handle.seek(0)
                    try:
                        existing = _parse_jsonl_snapshot(
                            path, handle.read()
                        )
                    except capture.CaptureFailure as exc:
                        if exc.reason != "invalid_jsonl":
                            raise
                        last_failure = exc
                    else:
                        wanted = row.get(unique_field)
                        if any(
                            item.get(unique_field) == wanted
                            for item in existing
                        ):
                            return False
                if last_failure is None:
                    handle.seek(0, os.SEEK_END)
                    remaining = memoryview(payload)
                    while remaining:
                        written = handle.write(remaining)
                        if written is None or written <= 0:
                            raise OSError(
                                f"short JSONL append: {path}"
                            )
                        remaining = remaining[written:]
                    os.fsync(handle.fileno())
                    return True
        if attempt + 1 < JSONL_SNAPSHOT_READ_ATTEMPTS:
            print(
                "WARN transient_jsonl_append_retry "
                f"path={path} attempt={attempt + 1}/"
                f"{JSONL_SNAPSHOT_READ_ATTEMPTS} "
                f"detail={last_failure.detail}",
                file=sys.stderr,
                flush=True,
            )
            last_failure = None
            _jsonl_retry_delay(attempt)
    assert last_failure is not None
    raise last_failure


@contextmanager
def exclusive_lock(path: Path, *, nonblocking: bool = False) -> Iterable[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        operation = fcntl.LOCK_EX
        if nonblocking:
            operation |= fcntl.LOCK_NB
        try:
            flock_with_retry(handle.fileno(), operation)
        except BlockingIOError as exc:
            raise capture.CaptureFailure(
                "shard_already_running", str(path)
            ) from exc
        yield


def shard_tag(index: int, count: int) -> str:
    return f"shard-{index:03d}-of-{count:03d}"


def shard_paths(
    output_root: Path, index: int, count: int
) -> dict[str, Path]:
    root = output_root / "manifests/shards" / shard_tag(index, count)
    return {
        "root": root,
        "accepted": root / "accepted.jsonl",
        "rejects": root / "rejects.jsonl",
        "queue": root / "queue_events.jsonl",
        "lock": root / "worker.lock",
    }


def queue_event(
    paths: dict[str, Path],
    episode_id: str,
    state: str,
    *,
    attempt_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    append_locked(
        paths["queue"],
        {
            "schema_version": "xonotic-canary-queue-event-v1",
            "episode_id": episode_id,
            "attempt_id": attempt_id,
            "state": state,
            "detail": detail or {},
            "created_utc": capture.utc_now(),
        },
    )


def gpu_inventory(require_single: bool, gpu_index: int) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise capture.CaptureFailure(
            "nvidia_smi_failed", completed.stderr.strip()
        )
    rows = [
        [field.strip() for field in line.split(",")]
        for line in completed.stdout.splitlines()
        if line.strip()
    ]
    if require_single and len(rows) != 1:
        raise capture.CaptureFailure(
            "single_visible_gpu_required", f"visible={len(rows)}"
        )
    if gpu_index < 0 or gpu_index >= len(rows):
        raise capture.CaptureFailure(
            "gpu_index_out_of_range",
            f"index={gpu_index} visible={len(rows)}",
        )
    selected = rows[gpu_index]
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    return {
        "visible_gpu_count": len(rows),
        "selected_visible_index": gpu_index,
        "nvidia_smi_index": int(selected[0]),
        "name": selected[1],
        "uuid": selected[2],
        "driver_version": selected[3],
        "memory_total_mib": int(float(selected[4])),
        "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
        "nvidia_visible_devices": os.environ.get(
            "NVIDIA_VISIBLE_DEVICES", ""
        ),
    }


def validate_manifest(
    path: Path,
    shard_index: int,
    shard_count: int,
    expected_source_commit: str | None = None,
) -> list[dict[str, Any]]:
    if not path.is_file():
        raise capture.CaptureFailure("input_manifest_missing", str(path))
    rows = capture.load_jsonl(path)
    ids = [str(row.get("episode_id", "")) for row in rows]
    if not rows or any(not episode_id for episode_id in ids):
        raise capture.CaptureFailure(
            "input_manifest_empty_or_invalid", str(path)
        )
    if len(ids) != len(set(ids)):
        raise capture.CaptureFailure("duplicate_episode_id", str(path))
    for row in rows:
        checks = {
            "known_nontraining_split": (
                row.get("split") in capture.NONTRAINING_SPLITS
            ),
            "formal_collection_forbidden": (
                row.get("formal_collection_authorized") is False
            ),
            "training_admitted_false": (
                row.get("training_admitted") is False
            ),
            "assigned_shard": (
                int(row.get("assigned_shard", -1)) == shard_index
            ),
            "shard_count": (
                int(row.get("shard_count", -1)) == shard_count
            ),
            "source_commit": (
                expected_source_commit is None
                or row.get("source_commit_required")
                == expected_source_commit
            ),
        }
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "input_manifest_policy_failed",
                capture.canonical_json(
                    {"episode_id": row.get("episode_id"), "checks": checks}
                ),
            )
    return rows


def verify_manifest_metadata(
    metadata_path: Path,
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    expected_source_commit: str,
) -> str:
    if not metadata_path.is_file():
        raise capture.CaptureFailure(
            "manifest_metadata_missing", str(metadata_path)
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    cohort = metadata.get("review") or metadata.get("canary") or {}
    checks = {
        "source_commit": metadata.get("source_commit")
        == expected_source_commit,
        "formal_collection_forbidden": (
            metadata.get("formal_collection_authorized") is False
        ),
        "training_admitted_false": (
            metadata.get("training_admitted") is False
        ),
        "shard_count": int(cohort.get("shard_count", -1))
        == shard_count,
    }
    expected = next(
        (
            row
            for row in cohort.get("shards", [])
            if int(row.get("shard_index", -1)) == shard_index
        ),
        None,
    )
    checks["shard_declared"] = expected is not None
    if expected is not None:
        checks["shard_sha256"] = expected.get("sha256") == input_sha256
        checks["shard_filename"] = (
            Path(str(expected.get("path", ""))).name
            == input_manifest.name
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "manifest_metadata_mismatch",
            capture.canonical_json(checks),
        )
    return capture.sha256_file(metadata_path)


def copy_file_once(source: Path, destination: Path) -> tuple[str, int]:
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


def stage_files(
    files: list[tuple[Path, Path]], destination: Path, attempt_id: str
) -> tuple[Path, dict[str, str], int, float]:
    if destination.exists():
        raise capture.CaptureFailure("refuse_overwrite", str(destination))
    temporary = destination.parent / (
        f".{destination.name}.tmp.{attempt_id}"
    )
    if temporary.exists():
        raise capture.CaptureFailure("stale_publish_temp", str(temporary))
    temporary.mkdir(parents=True)
    hashes: dict[str, str] = {}
    total = 0
    started = time.monotonic()
    for source, relative in files:
        digest, size = copy_file_once(source, temporary / relative)
        hashes[str(relative)] = digest
        total += size
    return temporary, hashes, total, time.monotonic() - started


def tree_files(root: Path) -> list[tuple[Path, Path]]:
    return [
        (path, path.relative_to(root))
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def first_file(stage: Path, pattern: str) -> Path | None:
    matches = sorted(stage.glob(pattern))
    return matches[0] if matches else None


def first_existing(*paths: Path | None) -> Path | None:
    return next(
        (
            path
            for path in paths
            if path is not None and path.is_file()
        ),
        None,
    )


def raw_files(stage: Path) -> list[tuple[Path, Path]]:
    candidates: list[tuple[str, Path | None]] = [
        (
            "raw_capture.avi",
            first_existing(
                stage / "raw_capture.avi",
                first_file(stage, "client_user/data/video/*.avi"),
            ),
        ),
        (
            "demo.dem",
            first_existing(
                stage / "demo.dem",
                first_file(stage, "client_user/data/demos/*.dem"),
            ),
        ),
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
        for name, path in candidates
        if path is not None and path.is_file()
    ]


def accepted_record(
    row: dict[str, Any],
    result: dict[str, Any],
    qa: dict[str, Any],
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    port: int,
    gpu: dict[str, Any],
    source_commit: str,
    raw_audit_selected: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "xonotic-h200-canary-accepted-v1",
        "episode_id": row["episode_id"],
        "source_episode_id": row.get("source_episode_id"),
        "attempt_id": result["attempt_id"],
        "split": row["split"],
        "formal_collection_authorized": False,
        "training_admitted": False,
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": input_sha256,
        "assigned_shard": shard_index,
        "shard_count": shard_count,
        "capture_port": port,
        "gpu": gpu,
        "map": row["map"],
        "gametype": row.get("gametype", "dm"),
        "dataset_role": row["dataset_role"],
        "primary_bucket": row.get("primary_bucket"),
        "category": row.get("category"),
        "canary_role": row.get("canary_role"),
        "enemy_present": bool(row.get("enemy_present", True)),
        "weapon": row["weapon"],
        "scheduler_targets": row.get("scheduler_targets"),
        "role_eligible": qa.get("role_eligible"),
        "qa": {
            "hard_gates_pass": all(qa["hard_gates"].values()),
            "frames": qa["video"]["frames"],
            "audio_samples_per_channel": qa["audio"][
                "samples_per_channel"
            ],
            "mapping_rate": qa["mapping"]["success_rate"],
            "renderer": qa["runtime"]["renderer"],
            "fire_count": qa["events"]["fire_count"],
            "audio_peak_s16": qa["audio"]["peak_s16"],
            "audio_onset_max_ms": qa["audio"]["max_onset_error_ms"],
            "requested_gametype": qa["mode"]["requested_gametype"],
            "realized_gametype": qa["mode"]["realized_gametype"],
            "hud_policy": qa["hud"],
            "route_passed": qa["route"]["passed"],
            "enemy_path_trace_passed": qa["enemy_policy"][
                "whole_path_trace"
            ]["passed"],
            "damage_count": qa["events"]["damage_count"],
            "player_collision_policy": qa["hard_gates"].get(
                "player_collision_policy"
            ),
            "player_movement_contact_telemetry": qa["hard_gates"].get(
                "player_movement_contact_telemetry"
            ),
        },
        "runtime": qa["runtime"],
        "target_relation": qa.get("target_relation"),
        "motion": qa.get("motion"),
        "stage2_causal": qa.get("stage2_causal"),
        "source_commit": source_commit,
        "raw_audit_selected": raw_audit_selected,
        "published_utc": capture.utc_now(),
    }


def complete_v2_artifacts(
    result: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    """Add realized relation/motion fields before non-training publication."""
    package = Path(result["stage"]) / "package"
    relation = v2.relation_metrics(
        package, bool(row.get("enemy_present", True))
    )
    motion_metrics = motion.motion_metrics(package)
    qa_path = package / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    motion_metrics["blockage"] = (
        (qa.get("telemetry") or {}).get("movement_blockage") or {}
    )
    qa["target_relation"] = relation
    qa["motion"] = motion_metrics
    qa["role_eligible"] = capture.stage1_role_eligible(
        row, qa, relation, motion_metrics
    )
    atomic_json(qa_path, qa)
    episode_path = package / "episode.json"
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    episode["actual_target_relation"] = relation
    episode["actual_motion"] = motion_metrics
    atomic_json(episode_path, episode)
    result["qa"] = qa
    result["target_relation"] = relation
    result["motion"] = motion_metrics
    return stage2.complete_stage2_artifacts(result, row)


def deterministic_raw_audit(
    episode_id: str, percent: int
) -> bool:
    return (
        int(hashlib.sha256(episode_id.encode()).hexdigest()[:8], 16)
        % 100
        < percent
    )


@functools.lru_cache(maxsize=1)
def route_plan_index() -> tuple[dict[str, Any], ...]:
    return tuple(capture.load_jsonl(routes.PLAN_INDEX))


def same_origin(first: Any, second: Any) -> bool:
    return (
        sum(
            (float(left) - float(right)) ** 2
            for left, right in zip(first, second)
        )
        ** 0.5
        <= 0.25
    )


def fallback_route_candidates(
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    original = str(
        (row.get("route_request") or {}).get("route_id", "")
    )
    candidates = [
        plan
        for plan in route_plan_index()
        if plan.get("map") == row.get("map")
        and str(plan.get("gametype", "")).lower()
        == str(row.get("gametype", "dm")).lower()
        and plan.get("route_id") != original
    ]
    episode_id = str(row["episode_id"])
    candidates.sort(
        key=lambda plan: (
            not same_origin(
                plan["nodes"][0]["origin"],
                row["player"]["origin"],
            ),
            not (
                routes.CALIBRATION_ROOT
                / str(plan["route_id"])
                / "CALIBRATION.json"
            ).is_file(),
            hashlib.sha256(
                f"{episode_id}:{plan['route_id']}".encode()
            ).hexdigest(),
        )
    )
    return candidates


def calibrated_plan(
    plan: dict[str, Any],
    output_root: Path,
    port: int,
) -> dict[str, Any]:
    route_id = str(plan["route_id"])
    lock_path = output_root / "route_locks" / f"{route_id}.lock"
    with exclusive_lock(lock_path):
        effective = routes.effective_plan(route_id)
        if effective.get("calibration_status") != "passed":
            routes.calibrate(route_id, port=port)
            effective = routes.effective_plan(route_id)
        if effective.get("calibration_status") != "passed":
            raise capture.CaptureFailure(
                "route_calibration_not_passed", route_id
            )
    return effective


def locomotion_camera_offset(direction: str) -> float:
    forward, strafe = capture.STAGE1_LOCOMOTION_VECTORS[
        direction
    ]
    return math.degrees(math.atan2(strafe, forward))


def prepare_route(
    row: dict[str, Any],
    output_root: Path,
    port: int,
    *,
    safety_fallback: bool = False,
) -> dict[str, Any]:
    request = row.get("route_request")
    if not request and not safety_fallback:
        return row
    if request and not safety_fallback:
        plan_path = capture.locked_root_artifact(
            request["route_plan_path"],
            request["route_plan_sha256"],
            "route_plan",
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if plan.get("route_id") != str(request["route_id"]):
            raise capture.CaptureFailure(
                "route_plan_id_mismatch", str(request["route_id"])
            )
        capture.locked_root_artifact(
            request["route_csv_path"],
            request["route_csv_sha256"],
            "route_csv",
        )
        candidates = [plan]
    else:
        candidates = fallback_route_candidates(row)[:12]
    if not candidates:
        raise capture.CaptureFailure(
            "stage1_safety_route_missing", str(row["episode_id"])
        )

    effective: dict[str, Any] | None = None
    failures: list[dict[str, str]] = []
    for plan in candidates:
        try:
            effective = calibrated_plan(plan, output_root, port)
            break
        except capture.CaptureFailure as exc:
            if not exc.reason.startswith("route_calibration_"):
                raise
            failures.append(
                {
                    "route_id": str(plan["route_id"]),
                    "reason": exc.reason,
                }
            )
    if effective is None:
        raise capture.CaptureFailure(
            "stage1_safety_route_exhausted",
            capture.canonical_json(failures),
        )

    scenario = json.loads(json.dumps(row))
    route_id = str(effective["route_id"])
    route_seed = 14_000_000 + int(route_id.split("_")[-1])
    scenario["seed"] = route_seed
    scenario["player"]["origin"] = list(
        effective["nodes"][0]["origin"]
    )
    scenario["frozen_actions_path"] = effective[
        "frozen_actions_path"
    ]
    scenario["frozen_actions_sha256"] = effective[
        "frozen_actions_sha256"
    ]
    if safety_fallback and not request:
        direction = str(
            scenario["action_design"]["locomotion_direction"]
        )
        offset = locomotion_camera_offset(direction)
        base_yaw = float((route_seed * 37) % 360) - 180.0
        scenario["player"]["yaw"] = round(
            (base_yaw + offset + 180.0) % 360.0 - 180.0,
            6,
        )
        scenario["route_view_policy"] = "look_along_route"
        scenario["stage1_safe_base_route"] = True
        scenario["stage1_locomotion_camera_offset_degrees"] = (
            offset
        )
    else:
        scenario["route_plan"] = effective
        scenario["capture_route_calibration"] = False
    if scenario.get("enemy_present"):
        review.apply_enemy_policy_geometry(scenario)
    scenario["runtime_route_support"] = {
        "schema_version": "xonotic-stage1-runtime-route-support-v1",
        "reason": (
            "deterministic_safety_fallback"
            if safety_fallback
            else "declared_route"
        ),
        "input_route_id": (
            str(request["route_id"]) if request else None
        ),
        "effective_route_id": route_id,
        "player_origin_changed": not same_origin(
            scenario["player"]["origin"], row["player"]["origin"]
        ),
        "selection_candidates_tried": len(failures) + 1,
        "calibration_failures": failures,
    }
    return scenario


def needs_safety_fallback(
    paths: dict[str, Path], episode_id: str
) -> bool:
    rows = [
        row
        for row in load_jsonl_locked(paths["rejects"])
        if row.get("episode_id") == episode_id
    ]
    if not rows:
        return False
    latest = rows[-1]
    text = f"{latest.get('reason', '')} {latest.get('detail', '')}"
    return any(
        marker in text
        for marker in (
            "route_calibration_",
            "route_trace_contract",
            "event_linkage",
            "resource_deltas_explained",
            "first_person_camera_continuity",
            "expected_audio_non_silent",
        )
    )


def automatic_safety_fallback_allowed(row: dict[str, Any]) -> bool:
    """Keep legacy review recovery, but never substitute a Stage-1 v3/v4 row.

    Stage-1 v3/v4 is a proposal/certification contract: the declared candidate
    either passes unchanged or is rejected and later replaced by a separately
    generated replenishment candidate.  Choosing another route at runtime
    would silently change the sampled distribution.
    """
    action_schema = (row.get("action_design") or {}).get(
        "schema_version"
    )
    return (
        row.get("model_action_schema_version")
        != capture.MODEL_ACTION_SCHEMA_VERSION
        and action_schema
        not in {
            "xonotic-stage1-action-design-v3",
            "xonotic-stage1-action-design-v4",
        }
    )


def publish(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
    result: dict[str, Any],
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    port: int,
    gpu: dict[str, Any],
    source_commit: str,
    raw_audit_percent: int,
) -> dict[str, Any]:
    stage = Path(result["stage"])
    package = stage / "package"
    qa = json.loads((package / "qa.json").read_text(encoding="utf-8"))
    qa["training_admitted"] = False
    atomic_json(package / "qa.json", qa)
    episode = json.loads(
        (package / "episode.json").read_text(encoding="utf-8")
    )
    episode["training_admitted"] = False
    episode["formal_collection_authorized"] = False
    atomic_json(package / "episode.json", episode)

    raw_audit_selected = deterministic_raw_audit(
        row["episode_id"], raw_audit_percent
    )
    record = accepted_record(
        row,
        result,
        qa,
        input_manifest,
        input_sha256,
        shard_index,
        shard_count,
        port,
        gpu,
        source_commit,
        raw_audit_selected,
    )
    atomic_json(package / "canary_record.json", record)
    episode_destination = output_root / "episodes" / row["episode_id"]
    raw_destination = output_root / "raw" / result["attempt_id"]
    episode_destination.parent.mkdir(parents=True, exist_ok=True)
    raw_destination.parent.mkdir(parents=True, exist_ok=True)
    (
        episode_temporary,
        package_hashes,
        package_bytes,
        package_seconds,
    ) = stage_files(
        tree_files(package), episode_destination, result["attempt_id"]
    )
    raw_sources = raw_files(stage)
    if not raw_audit_selected:
        raw_sources = [
            item
            for item in raw_sources
            if item[1].name != "raw_capture.avi"
        ]
    raw_temporary, raw_hashes, raw_bytes, raw_seconds = stage_files(
        raw_sources, raw_destination, result["attempt_id"]
    )
    os.rename(raw_temporary, raw_destination)
    os.rename(episode_temporary, episode_destination)
    manifest = {
        **record,
        "episode_path": str(episode_destination),
        "raw_path": str(raw_destination),
        "package_sha256": package_hashes,
        "raw_sha256": raw_hashes,
        "publication": {
            "strategy": "exclusive-create-hash-fsync-atomic-rename",
            "package_bytes": package_bytes,
            "raw_bytes": raw_bytes,
            "package_copy_seconds": package_seconds,
            "raw_copy_seconds": raw_seconds,
        },
    }
    if not append_locked(
        paths["accepted"], manifest, unique_field="episode_id"
    ):
        raise capture.CaptureFailure(
            "duplicate_manifest_publication", row["episode_id"]
        )
    queue_event(
        paths,
        row["episode_id"],
        "accepted",
        attempt_id=result["attempt_id"],
        detail={"episode_path": str(episode_destination)},
    )
    capture.clean_stage(stage)
    return manifest


def hash_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): capture.sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def recover_episode(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
) -> dict[str, Any] | None:
    existing = next(
        (
            item
            for item in load_jsonl_locked(paths["accepted"])
            if item.get("episode_id") == row["episode_id"]
        ),
        None,
    )
    if existing is not None:
        return existing
    episode = output_root / "episodes" / row["episode_id"]
    if not episode.exists():
        return None
    record_path = episode / "canary_record.json"
    if not record_path.is_file():
        raise capture.CaptureFailure(
            "unrecoverable_published_episode", str(episode)
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    raw = output_root / "raw" / record["attempt_id"]
    if not raw.is_dir():
        raise capture.CaptureFailure(
            "published_raw_missing", str(raw)
        )
    manifest = {
        **record,
        "episode_path": str(episode),
        "raw_path": str(raw),
        "package_sha256": hash_tree(episode),
        "raw_sha256": hash_tree(raw),
        "publication": {
            "strategy": "recovered_after_atomic_publish",
        },
        "recovered_utc": capture.utc_now(),
    }
    append_locked(paths["accepted"], manifest, unique_field="episode_id")
    queue_event(
        paths,
        row["episode_id"],
        "publication_recovered",
        attempt_id=record["attempt_id"],
    )
    return manifest


def recover_hard_terminal_reject(
    paths: dict[str, Path],
    row: dict[str, Any],
) -> dict[str, Any] | None:
    """Resume deterministic hard rejects but requeue exhausted operations."""
    matching = [
        item
        for item in load_jsonl_locked(paths["rejects"])
        if item.get("episode_id") == row["episode_id"]
        and item.get("terminal") is True
    ]
    if not matching:
        return None
    latest = matching[-1]
    return latest if latest.get("retryable") is not True else None


def next_attempt_index(
    paths: dict[str, Path], episode_id: str
) -> int:
    indexes: list[int] = []
    for source in (paths["accepted"], paths["rejects"]):
        for row in load_jsonl_locked(source):
            if row.get("episode_id") != episode_id:
                continue
            try:
                indexes.append(
                    int(str(row["attempt_id"]).rsplit("_a", 1)[1])
                )
            except (KeyError, ValueError, IndexError):
                pass
    for stage in (capture.TMP_ROOT / "raw").glob(f"{episode_id}_a*"):
        try:
            indexes.append(int(stage.name.rsplit("_a", 1)[1]))
        except (ValueError, IndexError):
            pass
    return max(indexes, default=0)


def preserve_reject(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
    attempt_id: str,
    stage: Path,
    exc: Exception,
    terminal: bool,
) -> dict[str, Any]:
    reason = (
        exc.reason
        if isinstance(exc, capture.CaptureFailure)
        else type(exc).__name__
    )
    destination = (
        output_root / "diagnostics/rejects" / attempt_id
    )
    hashes: dict[str, str] = {}
    if stage.is_dir() and not destination.exists():
        temporary, hashes, _, _ = stage_files(
            raw_files(stage), destination, attempt_id
        )
        os.rename(temporary, destination)
    rejection = {
        "schema_version": "xonotic-h200-canary-reject-v1",
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "reason": reason,
        "detail": str(exc),
        "retryable": retryable_failure(exc),
        "terminal": terminal,
        "diagnostic_path": str(destination) if destination.exists() else None,
        "diagnostic_sha256": hashes,
        "rejected_utc": capture.utc_now(),
    }
    append_locked(paths["rejects"], rejection)
    queue_event(
        paths,
        row["episode_id"],
        "hard_reject_terminal" if terminal else "operational_retry",
        attempt_id=attempt_id,
        detail={"reason": reason},
    )
    if stage.is_dir():
        capture.clean_stage(stage)
    return rejection


def capture_one(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
    local_index: int,
    port_base: int,
    max_attempts: int,
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    gpu: dict[str, Any],
    source_commit: str,
    raw_audit_percent: int,
) -> dict[str, Any]:
    episode_lock = output_root / "locks" / f"{row['episode_id']}.lock"
    with exclusive_lock(episode_lock):
        recovered = recover_episode(output_root, paths, row)
        if recovered is not None:
            print(f"resume accepted {row['episode_id']}", flush=True)
            return recovered
        hard_terminal = recover_hard_terminal_reject(paths, row)
        if hard_terminal is not None:
            print(
                f"resume hard reject {row['episode_id']} "
                f"reason={hard_terminal.get('reason')}",
                flush=True,
            )
            return hard_terminal
        start_index = next_attempt_index(paths, row["episode_id"])
        for local_attempt in range(max_attempts):
            retry_index = start_index + local_attempt
            attempt_id = f"{row['episode_id']}_a{retry_index + 1:02d}"
            stage = capture.TMP_ROOT / "raw" / attempt_id
            port = port_base + local_index
            queue_event(
                paths,
                row["episode_id"],
                "capturing",
                attempt_id=attempt_id,
                detail={"port": port},
            )
            print(
                f"capture {attempt_id} role={row.get('canary_role')} "
                f"map={row['map']} mode={row.get('gametype', 'dm')} "
                f"port={port}",
                flush=True,
            )
            try:
                scenario = prepare_route(
                    row,
                    output_root,
                    port,
                    safety_fallback=(
                        bool(row.get("force_stage1_safety_route"))
                        or (
                            automatic_safety_fallback_allowed(row)
                            and needs_safety_fallback(
                                paths, row["episode_id"]
                            )
                        )
                    ),
                )
                result = capture.execute_attempt(
                    scenario,
                    retry=retry_index,
                    publish=False,
                    port=port,
                )
                result = complete_v2_artifacts(result, row)
                manifest = publish(
                    output_root,
                    paths,
                    row,
                    result,
                    input_manifest,
                    input_sha256,
                    shard_index,
                    shard_count,
                    port,
                    gpu,
                    source_commit,
                    raw_audit_percent,
                )
                print(
                    f"accepted {row['episode_id']} "
                    f"renderer={manifest['qa']['renderer']}",
                    flush=True,
                )
                return manifest
            except Exception as exc:
                reason = (
                    exc.reason
                    if isinstance(exc, capture.CaptureFailure)
                    else type(exc).__name__
                )
                retryable = retryable_failure(exc)
                terminal = (
                    not retryable or local_attempt + 1 >= max_attempts
                )
                rejection = preserve_reject(
                    output_root,
                    paths,
                    row,
                    attempt_id,
                    stage,
                    exc,
                    terminal,
                )
                print(
                    f"reject {attempt_id} reason={reason} "
                    f"retryable={retryable} terminal={terminal}",
                    flush=True,
                )
                if terminal:
                    return rejection
    raise AssertionError("unreachable")


def command_run(args: argparse.Namespace) -> int:
    capture.require_conda()
    numeric_limits = {
        "workers": args.workers,
        "encode_concurrency": args.encode_concurrency,
        "x264_threads": args.x264_threads,
        "max_operational_attempts": args.max_operational_attempts,
    }
    for name, value in numeric_limits.items():
        minimum = 0 if name == "x264_threads" else 1
        if value < minimum:
            raise capture.CaptureFailure(
                "invalid_concurrency", f"{name}={value}"
            )
    for name, value in (
        ("live_concurrency", args.live_concurrency),
        ("render_concurrency", args.render_concurrency),
        ("sdl_concurrency", args.sdl_concurrency),
    ):
        if value is not None and value < 1:
            raise capture.CaptureFailure(
                "invalid_concurrency", f"{name}={value}"
            )
    if not 0 <= args.raw_audit_percent <= 100:
        raise capture.CaptureFailure(
            "invalid_raw_audit_percent",
            str(args.raw_audit_percent),
        )
    input_manifest = Path(args.input_manifest).resolve()
    output_root = Path(args.output_root).resolve()
    capture.TMP_ROOT = Path(args.tmp_root).resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    os.environ["XONOTIC_X264_THREADS"] = str(args.x264_threads)
    os.environ["XONOTIC_X264_CPUSET"] = args.x264_cpuset
    os.environ["XONOTIC_ENCODE_CONCURRENCY"] = str(
        args.encode_concurrency
    )
    live_concurrency = args.live_concurrency or args.workers
    render_concurrency = args.render_concurrency or args.workers
    sdl_concurrency = args.sdl_concurrency or args.workers
    os.environ["XONOTIC_LIVE_CONCURRENCY"] = str(live_concurrency)
    os.environ["XONOTIC_RENDER_CONCURRENCY"] = str(
        render_concurrency
    )
    os.environ["XONOTIC_SDL_CONCURRENCY"] = str(sdl_concurrency)
    os.environ["XONOTIC_RENDER_TIMEOUT_SECONDS"] = str(
        args.render_timeout_seconds
    )
    render_timeout_seconds = (
        capture.configured_render_timeout_seconds()
    )
    render_startup_stall_seconds = (
        capture.configured_render_startup_stall_seconds()
    )
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)

    rows = validate_manifest(
        input_manifest,
        args.shard_index,
        args.shard_count,
        args.expected_source_commit,
    )
    build = capture.build_root()
    source_commit = (build / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if source_commit != args.expected_source_commit:
        raise capture.CaptureFailure(
            "source_commit_mismatch",
            f"expected={args.expected_source_commit} "
            f"actual={source_commit}",
        )
    gpu = gpu_inventory(not args.allow_multiple_visible_gpus, args.gpu_index)
    input_sha256 = capture.sha256_file(input_manifest)
    metadata_sha256 = None
    if args.manifest_metadata:
        metadata_sha256 = verify_manifest_metadata(
            Path(args.manifest_metadata).resolve(),
            input_manifest,
            input_sha256,
            args.shard_index,
            args.shard_count,
            args.expected_source_commit,
        )
    paths = shard_paths(
        output_root, args.shard_index, args.shard_count
    )
    run_metadata = {
        "schema_version": "xonotic-h200-canary-worker-v1",
        "started_utc": capture.utc_now(),
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": input_sha256,
        "manifest_metadata": (
            str(Path(args.manifest_metadata).resolve())
            if args.manifest_metadata
            else None
        ),
        "manifest_metadata_sha256": metadata_sha256,
        "output_root": str(output_root),
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "planned_rows": len(rows),
        "workers": args.workers,
        "live_concurrency": live_concurrency,
        "render_concurrency": render_concurrency,
        "render_timeout_seconds": render_timeout_seconds,
        "render_startup_stall_seconds": (
            render_startup_stall_seconds
        ),
        "sdl_concurrency": sdl_concurrency,
        "encode_concurrency": args.encode_concurrency,
        "x264_threads": args.x264_threads,
        "x264_cpuset": capture.configured_x264_cpuset(),
        "x264_cpuset_cpu_count": (
            capture.configured_x264_cpuset_cpu_count()
        ),
        "raw_audit_percent": args.raw_audit_percent,
        "port_base": args.port_base,
        "tmp_root": str(capture.TMP_ROOT),
        "build": str(build),
        "source_commit": source_commit,
        "gpu": gpu,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(paths["lock"], nonblocking=True):
        atomic_json(paths["root"] / "RUN_METADATA.json", run_metadata)
        results: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.workers
        ) as executor:
            futures = {
                executor.submit(
                    capture_one,
                    output_root,
                    paths,
                    row,
                    local_index,
                    args.port_base,
                    args.max_operational_attempts,
                    input_manifest,
                    input_sha256,
                    args.shard_index,
                    args.shard_count,
                    gpu,
                    source_commit,
                    args.raw_audit_percent,
                ): row
                for local_index, row in enumerate(rows)
            }
            for completed, future in enumerate(
                concurrent.futures.as_completed(futures), 1
            ):
                result = future.result()
                results.append(result)
                print(
                    f"progress {completed}/{len(rows)} "
                    f"{result['episode_id']}",
                    flush=True,
                )
        accepted = [
            row for row in results if "episode_path" in row
        ]
        terminal = [
            row
            for row in results
            if row.get("terminal") is True
        ]
        finished = {
            **run_metadata,
            "finished_utc": capture.utc_now(),
            "accepted": len(accepted),
            "terminal_rejects": len(terminal),
            "pass": len(accepted) == len(rows) and not terminal,
        }
        atomic_json(paths["root"] / "RUN_RESULT.json", finished)
    print(json.dumps(finished, indent=2, sort_keys=True))
    return 0 if finished["pass"] else 2


def all_accepted(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/accepted.jsonl"
        )
    ):
        rows.extend(load_jsonl_locked(path))
    return rows


def all_rejects(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/rejects.jsonl"
        )
    ):
        rows.extend(load_jsonl_locked(path))
    return rows


def command_status(args: argparse.Namespace) -> int:
    input_rows = capture.load_jsonl(Path(args.input_manifest))
    accepted = all_accepted(Path(args.output_root))
    terminal = [
        row
        for row in all_rejects(Path(args.output_root))
        if row.get("terminal") is True
        and row.get("retryable") is not True
    ]
    accepted_ids = {row["episode_id"] for row in accepted}
    terminal_ids = {row["episode_id"] for row in terminal}
    accounted_ids = accepted_ids | terminal_ids
    result = {
        "schema_version": "xonotic-canary-status-v1",
        "input_rows": len(input_rows),
        "accepted_rows": len(accepted),
        "accepted_unique": len(accepted_ids),
        "terminal_reject_rows": len(terminal),
        "terminal_reject_unique": len(terminal_ids),
        "accounted_unique": len(accounted_ids),
        "remaining": len(
            [
                row
                for row in input_rows
                if row["episode_id"] not in accounted_ids
            ]
        ),
        "duplicate_accepted_ids": (
            len(accepted) - len(accepted_ids)
        ),
        "duplicate_terminal_ids": (
            len(terminal) - len(terminal_ids)
        ),
        "accepted_terminal_conflicts": len(
            accepted_ids & terminal_ids
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return (
        0
        if result["duplicate_accepted_ids"] == 0
        and result["duplicate_terminal_ids"] == 0
        and result["accepted_terminal_conflicts"] == 0
        else 2
    )


def command_audit(args: argparse.Namespace) -> int:
    input_manifest = Path(args.input_manifest).resolve()
    output_root = Path(args.output_root).resolve()
    planned = capture.load_jsonl(input_manifest)
    accepted = all_accepted(output_root)
    terminal = [
        row
        for row in all_rejects(output_root)
        if row.get("terminal") is True
        and row.get("retryable") is not True
    ]
    ids = [row["episode_id"] for row in accepted]
    terminal_ids = [row["episode_id"] for row in terminal]
    failures: list[str] = []
    if len(ids) != len(set(ids)):
        failures.append("duplicate_accepted_episode_id")
    if len(terminal_ids) != len(set(terminal_ids)):
        failures.append("duplicate_terminal_episode_id")
    accepted_by_id = {row["episode_id"]: row for row in accepted}
    terminal_by_id = {
        row["episode_id"]: row for row in terminal
    }
    conflicts = set(accepted_by_id) & set(terminal_by_id)
    failures.extend(
        f"{episode_id}:accepted_terminal_conflict"
        for episode_id in sorted(conflicts)
    )
    for row in planned:
        episode_id = row["episode_id"]
        manifest = accepted_by_id.get(episode_id)
        if manifest is None:
            rejection = terminal_by_id.get(episode_id)
            if rejection is None:
                failures.append(f"{episode_id}:missing")
            elif (
                not rejection.get("attempt_id")
                or not rejection.get("reason")
            ):
                failures.append(
                    f"{episode_id}:invalid_terminal_reject"
                )
            continue
        episode_path = Path(manifest["episode_path"])
        raw_path = Path(manifest["raw_path"])
        if not episode_path.is_dir() or not raw_path.is_dir():
            failures.append(f"{episode_id}:published_path_missing")
            continue
        qa = json.loads(
            (episode_path / "qa.json").read_text(encoding="utf-8")
        )
        checks = {
            "hard_gates": all(qa["hard_gates"].values()),
            "frames": qa["video"]["frames"] == capture.OUTPUT_TICKS,
            "audio": (
                qa["audio"]["samples_per_channel"]
                == capture.AUDIO_SAMPLES
            ),
            "mapping": qa["mapping"]["success_rate"] >= 0.999,
            "renderer": capture.is_nvidia_hardware_renderer(
                qa["runtime"]["renderer"]
            ),
            "gametype": (
                qa["mode"]["requested_gametype"]
                == qa["mode"]["realized_gametype"]
            ),
            "hud": (
                qa["hud"]["cl_hidewaypoints"] == 2
                and qa["hud"]["hud_panel_modicons"] == 0
                and qa["hud"]["g_ctf_flag_waypoint"] == 0
            ),
            "training_forbidden": qa.get("training_admitted") is False,
            "target_relations": (
                (episode_path / "target_relations.parquet").is_file()
                and len(
                    pd.read_parquet(
                        episode_path / "target_relations.parquet"
                    )
                )
                == capture.OUTPUT_TICKS
            ),
            "package_hashes": (
                hash_tree(episode_path) == manifest["package_sha256"]
            ),
            "raw_hashes": hash_tree(raw_path) == manifest["raw_sha256"],
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            failures.append(f"{episode_id}:{','.join(failed)}")
    audit = {
        "schema_version": "xonotic-h200-canary-audit-v1",
        "created_utc": capture.utc_now(),
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": capture.sha256_file(input_manifest),
        "planned": len(planned),
        "accepted": len(accepted),
        "terminal_rejects": len(terminal),
        "accounted": len(set(ids) | set(terminal_ids)),
        "failures": failures,
        "pass": (
            not failures
            and len(set(ids) | set(terminal_ids)) == len(planned)
        ),
    }
    atomic_json(output_root / "AUDIT.json", audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["pass"] else 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--input-manifest", required=True)
    run.add_argument("--manifest-metadata")
    run.add_argument("--output-root", required=True)
    run.add_argument("--shard-index", type=int, required=True)
    run.add_argument("--shard-count", type=int, required=True)
    run.add_argument("--workers", type=int, default=1)
    run.add_argument("--live-concurrency", type=int)
    run.add_argument("--render-concurrency", type=int)
    run.add_argument(
        "--render-timeout-seconds",
        type=float,
        default=240,
    )
    run.add_argument("--sdl-concurrency", type=int)
    run.add_argument("--encode-concurrency", type=int, default=1)
    run.add_argument("--x264-threads", type=int, default=0)
    run.add_argument("--x264-cpuset", default="")
    run.add_argument(
        "--expected-source-commit",
        default=EXPECTED_SOURCE_COMMIT,
    )
    run.add_argument(
        "--raw-audit-percent",
        type=int,
        default=100,
    )
    run.add_argument("--port-base", type=int, required=True)
    run.add_argument("--tmp-root", required=True)
    run.add_argument("--gpu-index", type=int, default=0)
    run.add_argument("--allow-multiple-visible-gpus", action="store_true")
    run.add_argument("--max-operational-attempts", type=int, default=2)
    run.set_defaults(func=command_run)
    status = sub.add_parser("status")
    status.add_argument("--input-manifest", required=True)
    status.add_argument("--output-root", required=True)
    status.set_defaults(func=command_status)
    audit = sub.add_parser("audit")
    audit.add_argument("--input-manifest", required=True)
    audit.add_argument("--output-root", required=True)
    audit.set_defaults(func=command_audit)
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
