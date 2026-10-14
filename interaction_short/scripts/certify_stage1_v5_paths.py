                      
"""Certify immutable Stage-1 v5 player paths before semantic expansion.

The ordinary pass runs dedicated-server/live-client simulation only.  A
predeclared visible-wall-contact candidate additionally runs the NVIDIA
offline renderer so contact-surface samples can be projected into the actual
first-person frame.  The pass freezes the exact 384-tick physical action
schedule and authoritative trajectory for every accepted non-training
prototype.  Formal capture may add weapon buttons, but may not mutate
movement, view, jump, geometry, or the certified trajectory.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import fcntl
import functools
import gzip
import json
import os
import queue
import shutil
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_v5_manifests as v5              
import run_capture_manifest_shard as common              
import xonotic_capture as capture              
import xonotic_stage1_routes as routes              


ROOT = capture.ROOT
EXPECTED_SOURCE_COMMIT = v5.EXPECTED_SOURCE_COMMIT
OUTPUT_ROOT = v5.PATH_CERTIFICATE_ROOT
CERTIFICATE_ROOT = OUTPUT_ROOT / "certificates"
REJECT_ROOT = OUTPUT_ROOT / "rejects"
OPERATIONAL_FAILURE_ROOT = OUTPUT_ROOT / "operational_failures"
EVENTS_PATH = OUTPUT_ROOT / "manifests/events.jsonl"
INDEX_PATH = v5.PATH_CERTIFICATE_INDEX
SUMMARY_PATH = OUTPUT_ROOT / "manifests/SUMMARY.json"
RUN_LOCK_PATH = OUTPUT_ROOT / "path_certification.lock"
INDEX_FILE_LOCK_PATH = OUTPUT_ROOT / "manifests/certificates.lock"
EVENT_LOCK = threading.Lock()
INDEX_LOCK = threading.Lock()
INDEX_ROWS_BY_ID: dict[str, dict[str, Any]] | None = None
INDEX_FILE_OFFSET = 0


def relative_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(
            value, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def acquire_shared_filesystem_lock(
    handle: Any, *, timeout_seconds: float = 120.0
) -> None:
    """Acquire an AFS-visible flock, retrying transient EAGAIN responses."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(
                handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
            )
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise capture.CaptureFailure(
                    "v5_path_file_lock_timeout",
                    str(getattr(handle, "name", "unknown")),
                )
            time.sleep(0.05)


def append_row(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOCK:
        lock_path = path.with_name(f"{path.name}.lock")
        with lock_path.open("a+", encoding="utf-8") as file_lock:
            acquire_shared_filesystem_lock(file_lock)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(capture.canonical_json(value) + "\n")
                handle.flush()
                os.fsync(handle.fileno())


def append_event(
    row: dict[str, Any],
    state: str,
    *,
    attempt_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    append_row(
        EVENTS_PATH,
        {
            "schema_version": (
                "xonotic-stage1-v5-player-path-event-v1"
            ),
            "prototype_id": row["episode_id"],
            "candidate_wave": row["candidate_wave"],
            "state": state,
            "attempt_id": attempt_id,
            "detail": detail or {},
            "created_utc": capture.utc_now(),
        },
    )


def append_index_once(value: dict[str, Any]) -> None:
    global INDEX_ROWS_BY_ID, INDEX_FILE_OFFSET
    prototype_id = str(value["prototype_id"])
    with INDEX_LOCK:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        lock_path = INDEX_PATH.with_name(f"{INDEX_PATH.name}.lock")
        with lock_path.open("a+", encoding="utf-8") as file_lock:
            acquire_shared_filesystem_lock(file_lock)
            with INDEX_PATH.open("a+", encoding="utf-8") as handle:
                if INDEX_ROWS_BY_ID is None:
                    INDEX_ROWS_BY_ID = {}
                    INDEX_FILE_OFFSET = 0
                handle.seek(INDEX_FILE_OFFSET)
                while True:
                    line = handle.readline()
                    if not line:
                        break
                    row = json.loads(line)
                    existing_id = str(row.get("prototype_id", ""))
                    if not existing_id:
                        raise capture.CaptureFailure(
                            "v5_path_index_id_missing", str(INDEX_PATH)
                        )
                    prior = INDEX_ROWS_BY_ID.get(existing_id)
                    if prior is not None and prior != row:
                        raise capture.CaptureFailure(
                            "v5_path_index_conflict", existing_id
                        )
                    INDEX_ROWS_BY_ID[existing_id] = row
                INDEX_FILE_OFFSET = handle.tell()
                existing = INDEX_ROWS_BY_ID.get(prototype_id)
                if existing is not None:
                    if existing != value:
                                                                           
                                                                             
                        identity = (
                            "status",
                            "certificate_sha256",
                            "actions_sha256",
                            "states_sha256",
                            "reason",
                        )
                        if any(
                            existing.get(name) != value.get(name)
                            for name in identity
                        ):
                            raise capture.CaptureFailure(
                                "v5_path_index_conflict", prototype_id
                            )
                    return
                handle.seek(0, os.SEEK_END)
                handle.write(capture.canonical_json(value) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                INDEX_FILE_OFFSET = handle.tell()
        INDEX_ROWS_BY_ID[prototype_id] = value


def configure_journals(
    *,
    terminal_journal: Path | None,
    event_journal: Path | None,
    shard_index: int,
    shard_count: int,
    wave: str,
) -> None:
    """Select journals before any terminal reconciliation.

    A distributed run must never have multiple nodes appending one JSONL
    file.  The worker therefore supplies a run-scoped, single-writer terminal
    journal and event journal for every shard.
    """
    global EVENTS_PATH, INDEX_PATH, INDEX_FILE_LOCK_PATH
    global INDEX_ROWS_BY_ID, INDEX_FILE_OFFSET

    if shard_count > 1 and (
        terminal_journal is None or event_journal is None
    ):
        raise SystemExit(
            "distributed certification requires explicit "
            "--terminal-journal and --event-journal"
        )

    def resolve(value: Path) -> Path:
        result = value if value.is_absolute() else ROOT / value
        result = result.resolve()
        try:
            result.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise SystemExit(
                f"journal must be inside capture root: {result}"
            ) from exc
        return result

    if terminal_journal is not None:
        INDEX_PATH = resolve(terminal_journal)
        if (
            shard_count > 1
            and INDEX_PATH == v5.PATH_CERTIFICATE_INDEX.resolve()
        ):
            raise SystemExit(
                "distributed certification may not append the global index"
            )
        INDEX_FILE_LOCK_PATH = INDEX_PATH.with_name(
            f"{INDEX_PATH.name}.lock"
        )
    if event_journal is not None:
        EVENTS_PATH = resolve(event_journal)
    elif shard_count > 1:
                                                                            
                                                                             
                                         
        EVENTS_PATH = (
            OUTPUT_ROOT
            / "manifests"
            / (
                "events."
                f"shard-{shard_index:03d}-of-{shard_count:03d}."
                f"{wave}.jsonl"
            )
        )
    INDEX_ROWS_BY_ID = None
    INDEX_FILE_OFFSET = 0


def prototype_specs(
    wave: str,
) -> list[tuple[Path, Path, str]]:
    main = {
        "primary": (
            v5.PRIMARY_PROTOTYPES_PATH,
            v5.PROTOTYPE_METADATA_PATH,
            "primary",
        ),
        "replenishment": (
            v5.REPLENISHMENT_PROTOTYPES_PATH,
            v5.PROTOTYPE_METADATA_PATH,
            "replenishment",
        ),
        "certification_spare": (
            v5.CERTIFICATION_SPARE_PROTOTYPES_PATH,
            v5.CERTIFICATION_SPARE_METADATA_PATH,
            "certification_spare",
        ),
    }
    targeted = {
        "targeted_high": (
            v5.TARGETED_HIGH_PROTOTYPES_PATH,
            v5.TARGETED_METADATA_PATH,
            "high_motion",
        ),
        "targeted_collision": (
            v5.TARGETED_COLLISION_PROTOTYPES_PATH,
            v5.TARGETED_METADATA_PATH,
            "visible_collision",
        ),
        "targeted_fast": (
            v5.FAST_TRAVERSAL_PROTOTYPES_PATH,
            v5.FAST_TRAVERSAL_METADATA_PATH,
            "fast_traversal",
        ),
        "targeted_fast_tight": (
            v5.FAST_TRAVERSAL_TIGHT_PROTOTYPES_PATH,
            v5.FAST_TRAVERSAL_TIGHT_METADATA_PATH,
            "fast_traversal_tight",
        ),
        "targeted_fast_world": (
            v5.FAST_TRAVERSAL_WORLD_PROTOTYPES_PATH,
            v5.FAST_TRAVERSAL_WORLD_METADATA_PATH,
            "fast_traversal_world",
        ),
    }
    if wave in main:
        return [main[wave]]
    if wave in targeted:
        return [targeted[wave]]
    if wave == "targeted":
        return list(targeted.values())
    return [*main.values(), *targeted.values()]


def load_prototypes(wave: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    metadata_cache: dict[Path, dict[str, Any]] = {}
    for path, metadata_path, key in prototype_specs(wave):
        if not metadata_path.is_file():
            raise capture.CaptureFailure(
                "v5_prototype_metadata_missing",
                str(metadata_path),
            )
        metadata = metadata_cache.setdefault(
            metadata_path,
            json.loads(metadata_path.read_text(encoding="utf-8")),
        )
        if (
            metadata.get("source_commit") != EXPECTED_SOURCE_COMMIT
            or metadata.get("formal_collection_authorized") is not False
            or metadata.get("training_admitted") is not False
        ):
            raise capture.CaptureFailure(
                "v5_prototype_metadata_contract_failed",
                str(metadata_path),
            )
        declared = metadata[key]
        if (
            declared["path"] != relative_to_root(path)
            or declared["sha256"] != capture.sha256_file(path)
        ):
            raise capture.CaptureFailure(
                "v5_prototype_manifest_hash_mismatch", str(path)
            )
        result.extend(capture.load_jsonl(path))
    ids = [str(row["episode_id"]) for row in result]
    if len(ids) != len(set(ids)):
        raise capture.CaptureFailure(
            "v5_duplicate_prototype_id", wave
        )
    return result


def terminal_record(
    row: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    prototype_id = str(row["episode_id"])
    certificate_path = (
        CERTIFICATE_ROOT / prototype_id / "CERTIFICATE.json"
    )
    rejection_path = REJECT_ROOT / prototype_id / "REJECTION.json"
    present = [
        ("certified", certificate_path),
        ("rejected", rejection_path),
    ]
    found = [(state, path) for state, path in present if path.is_file()]
    if len(found) > 1:
        raise capture.CaptureFailure(
            "v5_path_multiple_terminal_records", prototype_id
        )
    if not found:
        return None
    state, path = found[0]
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("prototype_id") != prototype_id:
        raise capture.CaptureFailure(
            "v5_path_terminal_id_mismatch", str(path)
        )
    return state, record


def reconcile_terminal_index(rows: list[dict[str, Any]]) -> int:
    """Recover the publish-directory-before-index crash window."""
    recovered = 0
    indexed = {
        str(item.get("prototype_id", ""))
        for item in capture.load_jsonl(INDEX_PATH)
    }
    for row in rows:
        terminal = terminal_record(row)
        if terminal is None:
            continue
        state, record = terminal
        prototype_id = str(row["episode_id"])
        indexed_before = prototype_id in indexed
        if state == "certified":
            append_index_once(certificate_index_row(record))
        else:
            append_index_once(record)
        recovered += int(not indexed_before)
        indexed.add(prototype_id)
    return recovered


def certificate_index_row(
    certificate: dict[str, Any],
) -> dict[str, Any]:
    prototype_id = str(certificate["prototype_id"])
    certificate_path = (
        CERTIFICATE_ROOT / prototype_id / "CERTIFICATE.json"
    )
    return {
        "schema_version": capture.PLAYER_PATH_REFERENCE_SCHEMA,
        "prototype_id": prototype_id,
        "candidate_wave": certificate["candidate_wave"],
        "status": "certified",
        "certified": True,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "seed": int(certificate["seed"]),
        "certificate_path": relative_to_root(certificate_path),
        "certificate_sha256": capture.sha256_file(certificate_path),
        "actions_path": certificate["actions_path"],
        "actions_sha256": certificate["actions_sha256"],
        "physical_action_sha256": certificate[
            "physical_action_sha256"
        ],
        "path_contract_sha256": certificate[
            "path_contract_sha256"
        ],
        "states_path": certificate["states_path"],
        "states_sha256": certificate["states_sha256"],
        "motion": certificate["motion"],
        "movement_blockage": certificate["movement_blockage"],
        "render_evidence": certificate.get("render_evidence"),
        "created_utc": certificate["created_utc"],
    }


def terminal_index_row(
    state: str, record: dict[str, Any]
) -> dict[str, Any]:
    if state == "certified":
        return certificate_index_row(record)
    if state == "rejected":
        return record
    raise capture.CaptureFailure(
        "v5_path_terminal_state_unknown", state
    )


def reconcile_published_terminal(
    row: dict[str, Any],
    *,
    resumed: bool,
    attempt_id: str | None = None,
    triggering_exception: Exception | None = None,
) -> dict[str, Any] | None:
    """Return an already-published terminal without re-running capture.

    Publishing the immutable directory is the commit point.  Journal/event
    failures after that point are operational failures and must never be
    converted into a semantic rejection or a second capture attempt.
    """
    terminal = terminal_record(row)
    if terminal is None:
        return None
    state, record = terminal
    append_index_once(terminal_index_row(state, record))
    detail: dict[str, Any] = {}
    if triggering_exception is not None:
        detail = {
            "reconciled_after_exception": True,
            "exception_type": type(triggering_exception).__name__,
            "exception_detail": str(triggering_exception),
        }
    append_event(
        row,
        f"resumed_{state}" if resumed else f"reconciled_{state}",
        attempt_id=attempt_id or record.get("attempt_id"),
        detail=detail,
    )
    return {
        "prototype_id": row["episode_id"],
        "status": state,
        "resumed": resumed,
        "record": record,
    }


def next_attempt_index(row: dict[str, Any]) -> int:
    indexes: list[int] = []
    prototype_id = str(row["episode_id"])

    def add(raw: str) -> None:
        try:
            indexes.append(int(raw.rsplit("_a", 1)[1]))
        except (ValueError, IndexError):
            pass

    for event in capture.load_jsonl(EVENTS_PATH):
        if event.get("prototype_id") != prototype_id:
            continue
        add(str(event.get("attempt_id") or ""))
    diagnostic_root = OPERATIONAL_FAILURE_ROOT / prototype_id
    if diagnostic_root.is_dir():
        for path in diagnostic_root.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                add(path.name)
    terminal = terminal_record(row)
    if terminal is not None:
        add(str(terminal[1].get("attempt_id") or ""))
    return max(indexes, default=0)


def verify_route_support_reference(
    row: dict[str, Any],
    effective: dict[str, Any],
) -> None:
    generation = row["player_path_generation"]
    route_id = str(generation["support_route_id"])
    certificate = certified_route_index().get(route_id)
    if certificate is None:
        raise capture.CaptureFailure(
            "v5_support_route_not_certified", route_id
        )
    certificate_hash = capture.hashlib.sha256(
        capture.canonical_json(certificate).encode()
    ).hexdigest()
    checks = {
        "declared_certificate_hash": generation.get(
            "support_route_certificate_sha256"
        )
        == certificate_hash,
        "route_id": effective.get("route_id") == route_id,
        "calibration_passed": effective.get("calibration_status")
        == "passed",
        "calibration_source": effective.get(
            "calibration_source_commit"
        )
        == EXPECTED_SOURCE_COMMIT,
        "frozen_actions": effective.get("frozen_actions_sha256")
        == certificate.get("frozen_actions_sha256"),
        "calibration_states": effective.get(
            "calibration_states_sha256"
        )
        == certificate.get("calibration_states_sha256"),
        "robust_support_eligible": certificate.get(
            "robust_support_eligible"
        )
        is True,
        "zero_hidden_base_jump": int(
            certificate.get("base_jump_ticks", -1)
        )
        == 0,
        "declared_support_contract": (
            generation.get("support_route_robust_eligible") is True
            and int(
                generation.get("support_route_base_jump_ticks", -1)
            )
            == 0
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_support_route_reference_failed",
            capture.canonical_json(
                {
                    "prototype_id": row["episode_id"],
                    "route_id": route_id,
                    "checks": checks,
                }
            ),
        )


@functools.lru_cache(maxsize=1)
def certified_route_index() -> dict[str, dict[str, Any]]:
    return {
        str(item["route_id"]): item
        for item in v5.load_route_index()
    }


def prepare_scenario(row: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "split": row.get("split") == "v5_stage1_path_certification",
        "source_commit": row.get("source_commit_required")
        == EXPECTED_SOURCE_COMMIT,
        "nontraining": row.get("training_admitted") is False,
        "not_formal": row.get("formal_collection_authorized") is False,
        "path_only": (
            (row.get("action_design") or {}).get("weapon_action")
            == "none"
        ),
        "certificate_required": (
            (row.get("path_prototype") or {}).get(
                "certification_required"
            )
            is True
        ),
        "no_runtime_fallback": (
            (row.get("player_path_generation") or {}).get(
                "runtime_geometry_fallback"
            )
            is False
            and (row.get("player_path_generation") or {}).get(
                "runtime_action_fallback"
            )
            is False
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "v5_path_prototype_contract_failed",
            capture.canonical_json(
                {
                    "prototype_id": row.get("episode_id"),
                    "checks": checks,
                }
            ),
        )
    scenario = copy.deepcopy(row)
    generation = scenario["player_path_generation"]
    mode = str(generation["mode"])
    if mode in {
        "declared_route_replay",
        "declared_certified_route_support",
    }:
        route_id = str(generation["support_route_id"])
        request = scenario.get("route_request") or {}
        if request.get("route_id") != route_id:
            raise capture.CaptureFailure(
                "v5_path_route_request_mismatch",
                str(scenario["episode_id"]),
            )
        capture.locked_root_artifact(
            request["route_plan_path"],
            request["route_plan_sha256"],
            "v5_path_route_plan",
        )
        capture.locked_root_artifact(
            request["route_csv_path"],
            request["route_csv_sha256"],
            "v5_path_route_csv",
        )
        effective = routes.effective_plan(route_id)
        verify_route_support_reference(scenario, effective)
        scenario["frozen_actions_path"] = effective[
            "frozen_actions_path"
        ]
        scenario["frozen_actions_sha256"] = effective[
            "frozen_actions_sha256"
        ]
        if mode == "declared_route_replay":
            scenario["route_plan"] = effective
        else:
                                                                          
                                                                            
                                                     
            scenario.pop("route_plan", None)
    elif mode in {
        "preflight_static_or_jump_in_place",
        "declared_preflight_direct_candidate",
        "declared_visible_wall_contact_candidate",
    }:
        if scenario.get("route_request"):
            raise capture.CaptureFailure(
                "v5_direct_path_has_route_request",
                str(scenario["episode_id"]),
            )
    else:
        raise capture.CaptureFailure(
            "v5_path_generation_mode_unknown", mode
        )
    scenario["player_path_certification_run"] = True
    return scenario


def event_damage_count(events: pd.DataFrame) -> int:
    if events.empty or "event" not in events:
        return 0
    return int((events["event"] == "damage").sum())


def retryable_certification_failure(exc: Exception) -> bool:
    if (
        isinstance(exc, capture.CaptureFailure)
        and exc.reason
        == "v5_visible_collision_render_timing_failed"
    ):
        return True
    if (
        isinstance(exc, capture.CaptureFailure)
        and exc.reason == "live_precheck_failed"
    ):
        try:
            report = json.loads(str(exc.detail))
        except json.JSONDecodeError:
            return False
        checks = report.get("checks") or {}
        operational_checks = (
            "desired_action_ticks",
            "server_state_ticks",
            "authoritative_action_schedule",
            "output_begin_singleton",
            "output_end_singleton",
        )
        return any(
            checks.get(name) is False for name in operational_checks
        )
    return (
        common.retryable_failure(exc)
        if isinstance(exc, capture.CaptureFailure)
        else True
    )


PUBLICATION_INTEGRITY_REASONS = frozenset(
    {
        "v5_refuse_overwrite_path_certificate",
        "v5_refuse_overwrite_path_rejection",
        "v5_path_multiple_terminal_records",
        "v5_path_terminal_id_mismatch",
        "v5_path_index_id_missing",
        "v5_path_index_conflict",
    }
)


def publication_integrity_failure(exc: Exception) -> bool:
    return (
        isinstance(exc, capture.CaptureFailure)
        and exc.reason in PUBLICATION_INTEGRITY_REASONS
    )


def write_gzip_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as handle:
        for row in rows:
            handle.write(capture.canonical_json(row) + "\n")


def visible_collision_requested(scenario: dict[str, Any]) -> bool:
    return (
        (scenario.get("collision_design") or {}).get("intent")
        == capture.VISIBLE_COLLISION_INTENT
    )


def certify_visible_collision_render(
    stage: Path,
    scenario: dict[str, Any],
    live: dict[str, Any],
    states: pd.DataFrame,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    pd.DataFrame,
]:
    render = capture.run_render_attempt(
        stage,
        scenario,
        capture.build_root(),
        Path(live["client_user"]),
    )
    frames = pd.read_csv(render["frames_engine"])
    mapped_ticks, time_errors = (
        capture.map_frames_to_authoritative_states(frames, states)
    )
    frames["episode_server_tick"] = mapped_ticks
    frames["state_time_error_ms"] = time_errors * 1000.0
    expected_ticks = np.arange(
        capture.WARMUP_TICKS,
        capture.TOTAL_TICKS,
        dtype=np.int64,
    )
    frame_indices = pd.to_numeric(
        frames.get("frame_index"), errors="coerce"
    ).to_numpy()
    frame_pts = pd.to_numeric(
        frames.get("pts_seconds"), errors="coerce"
    ).to_numpy()
    exact_timeline = bool(
        len(frames) == capture.OUTPUT_TICKS
        and np.array_equal(
            frame_indices,
            np.arange(capture.OUTPUT_TICKS),
        )
        and np.allclose(
            frame_pts,
            np.arange(
                capture.OUTPUT_TICKS, dtype=np.float64
            )
            / capture.VIDEO_FPS,
            atol=1e-9,
            rtol=0,
        )
    )
    exact_tick_mapping = bool(
        len(mapped_ticks) == len(expected_ticks)
        and np.array_equal(mapped_ticks, expected_ticks)
    )
    time_error_passed = bool(
        len(time_errors) == capture.OUTPUT_TICKS
        and np.isfinite(time_errors).all()
        and np.all(
            time_errors
            <= capture.FRAME_STATE_TIME_TOLERANCE_SECONDS
        )
    )
    camera = capture.first_person_camera_metrics(frames, states)
    checks = {
        "render_frames_exact": len(frames)
        == capture.OUTPUT_TICKS,
        "render_timeline_exact": exact_timeline,
        "frame_tick_mapping_exact": exact_tick_mapping,
        "frame_state_time_tolerance": time_error_passed,
        "first_person_camera": camera["passed"] is True,
        "nvidia_hardware_renderer": bool(render["renderer"]),
        "minimal_hud_policy": (
            render["hud_policy"] == capture.HUD_POLICY_LINE
        ),
    }
    evidence = {
        "schema_version": (
            "xonotic-stage1-v5-visible-collision-render-evidence-v1"
        ),
        "required": True,
        "passed": all(checks.values()),
        "checks": checks,
        "renderer": render["renderer"],
        "hud_policy": render["hud_policy"],
        "render_wall_seconds": float(render["render_wall_seconds"]),
        "frame_rows": len(frames),
        "mapped_tick_first": (
            int(mapped_ticks[0]) if len(mapped_ticks) else None
        ),
        "mapped_tick_last": (
            int(mapped_ticks[-1]) if len(mapped_ticks) else None
        ),
        "max_state_time_error_ms": (
            float(np.max(time_errors) * 1000.0)
            if len(time_errors)
            and np.isfinite(time_errors).all()
            else None
        ),
        "first_person_camera": camera,
    }
    if not evidence["passed"]:
        raise capture.CaptureFailure(
            "v5_visible_collision_render_timing_failed",
            capture.canonical_json(evidence),
        )
    blockage = capture.movement_blockage_metrics(
        states,
        frames=frames,
        scenario=scenario,
    )
    return blockage, evidence, render, frames


def publish_certificate(
    row: dict[str, Any],
    scenario: dict[str, Any],
    attempt_id: str,
    stage: Path,
    live: dict[str, Any],
    states: pd.DataFrame,
    events: pd.DataFrame,
    server_rows: list[dict[str, Any]],
    precheck: dict[str, Any],
    blockage: dict[str, Any],
    motion_metrics: dict[str, Any],
    wall_seconds: float,
    render: dict[str, Any] | None = None,
    render_frames: pd.DataFrame | None = None,
    render_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prototype_id = str(row["episode_id"])
    destination = CERTIFICATE_ROOT / prototype_id
    temporary = CERTIFICATE_ROOT / (
        f".{prototype_id}.tmp.{attempt_id}.{os.getpid()}"
    )
    if destination.exists() or temporary.exists():
        raise capture.CaptureFailure(
            "v5_refuse_overwrite_path_certificate",
            str(destination),
        )
    temporary.mkdir(parents=True)
    actions_path = temporary / "physical_actions.csv"
    states_path = temporary / "states.parquet"
    events_path = temporary / "events.parquet"
    telemetry_path = temporary / "server_telemetry.jsonl.gz"
    shutil.copy2(stage / "actions_requested.csv", actions_path)
    states.to_parquet(states_path, index=False)
    events.to_parquet(events_path, index=False)
    write_gzip_jsonl(telemetry_path, server_rows)
    for name in (
        "server_console.log",
        "client_live_console.log",
        "LIVE_PRECHECK.json",
    ):
        source = stage / name
        if source.is_file():
            shutil.copy2(source, temporary / name)

    published_render_evidence: dict[str, Any] | None = None
    if render_evidence is not None:
        if render is None or render_frames is None:
            shutil.rmtree(temporary)
            raise capture.CaptureFailure(
                "v5_render_evidence_artifacts_missing",
                prototype_id,
            )
        render_frames_path = temporary / "frames_render.parquet"
        audio_events_path = temporary / "audio_events_engine.csv"
        render_frames.to_parquet(render_frames_path, index=False)
        shutil.copy2(render["audio_events_engine"], audio_events_path)
        render_log_source = stage / "client_render_console.log"
        if render_log_source.is_file():
            shutil.copy2(
                render_log_source,
                temporary / "client_render_console.log",
            )
        published_render_evidence = {
            **render_evidence,
            "frames_path": relative_to_root(
                destination / render_frames_path.name
            ),
            "frames_sha256": capture.sha256_file(
                render_frames_path
            ),
            "audio_events_path": relative_to_root(
                destination / audio_events_path.name
            ),
            "audio_events_sha256": capture.sha256_file(
                audio_events_path
            ),
        }

    final_actions = destination / actions_path.name
    final_states = destination / states_path.name
    final_events = destination / events_path.name
    final_telemetry = destination / telemetry_path.name
    action_rows = list(
        csv.DictReader(
            actions_path.read_text(encoding="utf-8").splitlines()[1:]
        )
    )
    physical_hash = capture.physical_action_sha256(action_rows)
    path_contract_hash = capture.player_path_contract_sha256(row)
    certificate = {
        "schema_version": capture.PLAYER_PATH_CERTIFICATE_SCHEMA,
        "prototype_id": prototype_id,
        "candidate_wave": row["candidate_wave"],
        "status": "certified",
        "passed": True,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "seed": int(row["seed"]),
        "input_scenario_sha256": capture.hashlib.sha256(
            capture.canonical_json(row).encode()
        ).hexdigest(),
        "runtime_scenario_sha256": capture.hashlib.sha256(
            capture.canonical_json(scenario).encode()
        ).hexdigest(),
        "actions_path": relative_to_root(final_actions),
        "actions_sha256": capture.sha256_file(actions_path),
        "physical_action_sha256": physical_hash,
        "path_contract_sha256": path_contract_hash,
        "states_path": relative_to_root(final_states),
        "states_sha256": capture.sha256_file(states_path),
        "events_path": relative_to_root(final_events),
        "events_sha256": capture.sha256_file(events_path),
        "server_telemetry_path": relative_to_root(final_telemetry),
        "server_telemetry_sha256": capture.sha256_file(telemetry_path),
        "path_generation": row["player_path_generation"],
        "map": row["map"],
        "gametype": row["gametype"],
        "dataset_role": row["dataset_role"],
        "primary_bucket": row["primary_bucket"],
        "action_design": row["action_design"],
        "collision_design": row.get("collision_design"),
        "movement_blockage": blockage,
        "render_evidence": published_render_evidence,
        "motion": motion_metrics,
        "route_trace": precheck["route_trace"],
        "enemy_path_trace": precheck["enemy_path_trace"],
        "live_precheck": precheck,
        "damage_count": event_damage_count(events),
        "state_rows": len(states),
        "event_rows": len(events),
        "attempt_id": attempt_id,
        "live_wall_seconds": float(live["live_wall_seconds"]),
        "certification_wall_seconds": wall_seconds,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "created_utc": capture.utc_now(),
    }
    checks = {
        "physical_action_path_only": all(
            int(float(item[name])) == 0
            for item in action_rows
            for name in (
                "primary",
                "secondary",
                "reload",
                "weapon_impulse",
            )
        ),
        "state_ticks_exact": (
            len(states) == capture.TOTAL_TICKS
            and list(pd.to_numeric(states["server_tick"]))
            == list(range(capture.TOTAL_TICKS))
        ),
        "live_precheck": precheck["passed"] is True,
        "collision_policy": blockage["collision_policy_passed"] is True,
        "contact_telemetry": blockage["contact_telemetry_present"] is True,
        "alive": motion_metrics["health_min"] > 0,
        "no_damage": certificate["damage_count"] == 0,
        "enemy_path": precheck["enemy_path_trace"]["passed"] is True,
        "route_nonreference_gates": (
            not precheck["route_trace"].get("expected")
            or all(
                value
                for name, value in precheck["route_trace"][
                    "gates"
                ].items()
                if name != "route_calibration_replay_match"
            )
        ),
        "full_render_when_required": (
            not visible_collision_requested(scenario)
            or (
                published_render_evidence is not None
                and published_render_evidence["passed"] is True
            )
        ),
        "visible_collision_when_required": (
            not visible_collision_requested(scenario)
            or blockage["visible_collision_qualified"] is True
        ),
    }
    certificate["checks"] = checks
    certificate["passed"] = all(checks.values())
    if not certificate["passed"]:
        shutil.rmtree(temporary)
        raise capture.CaptureFailure(
            "v5_player_path_certification_failed",
            capture.canonical_json(checks),
        )
    atomic_json(temporary / "CERTIFICATE.json", certificate)
    os.rename(temporary, destination)
    return certificate_index_row(certificate)


def publish_rejection(
    row: dict[str, Any],
    attempt_id: str,
    stage: Path,
    exc: Exception,
) -> dict[str, Any]:
    prototype_id = str(row["episode_id"])
    destination = REJECT_ROOT / prototype_id
    temporary = REJECT_ROOT / (
        f".{prototype_id}.tmp.{attempt_id}.{os.getpid()}"
    )
    if destination.exists() or temporary.exists():
        raise capture.CaptureFailure(
            "v5_refuse_overwrite_path_rejection",
            str(destination),
        )
    temporary.mkdir(parents=True)
    for name in (
        "ATTEMPT.json",
        "actions_requested.csv",
        "actions_engine.csv",
        "server_console.log",
        "client_live_console.log",
        "LIVE_PRECHECK.json",
    ):
        source = stage / name
        if source.is_file():
            shutil.copy2(source, temporary / name)
    reason = (
        exc.reason
        if isinstance(exc, capture.CaptureFailure)
        else type(exc).__name__
    )
    rejection = {
        "schema_version": (
            "xonotic-stage1-v5-player-path-rejection-v1"
        ),
        "prototype_id": prototype_id,
        "candidate_wave": row["candidate_wave"],
        "status": "rejected",
        "reason": reason,
        "detail": str(exc),
        "attempt_id": attempt_id,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "created_utc": capture.utc_now(),
    }
    atomic_json(temporary / "REJECTION.json", rejection)
    os.rename(temporary, destination)
    return rejection


def preserve_operational_failure(
    row: dict[str, Any],
    attempt_id: str,
    stage: Path,
    exc: Exception,
) -> Path:
    """Persist retry diagnostics before the node-local stage is cleaned."""
    prototype_id = str(row["episode_id"])
    prototype_root = OPERATIONAL_FAILURE_ROOT / prototype_id
    destination = prototype_root / attempt_id
    if destination.is_dir():
        return destination
    if destination.exists():
        raise capture.CaptureFailure(
            "v5_operational_diagnostic_path_conflict",
            str(destination),
        )
    prototype_root.mkdir(parents=True, exist_ok=True)
    temporary = prototype_root / (
        f".{attempt_id}.tmp.{os.getpid()}.{threading.get_ident()}"
    )
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir()
    copied: list[str] = []
    for name in (
        "ATTEMPT.json",
        "actions_requested.csv",
        "actions_engine.csv",
        "server_console.log",
        "client_live_console.log",
        "LIVE_PRECHECK.json",
    ):
        source = stage / name
        if source.is_file():
            shutil.copy2(source, temporary / name)
            copied.append(name)
    live_source = stage / "live"
    if live_source.is_dir():
        shutil.copytree(live_source, temporary / "live")
        copied.append("live/")
    reason = (
        exc.reason
        if isinstance(exc, capture.CaptureFailure)
        else type(exc).__name__
    )
    diagnostic = {
        "schema_version": (
            "xonotic-stage1-v5-operational-failure-diagnostic-v1"
        ),
        "prototype_id": prototype_id,
        "candidate_wave": row["candidate_wave"],
        "attempt_id": attempt_id,
        "status": "operational_failure",
        "reason": reason,
        "detail": str(exc),
        "evidence": sorted(copied),
        "hostname": "",
        "pid": os.getpid(),
        "live_timeout_seconds": os.environ.get(
            "XONOTIC_LIVE_TIMEOUT_SECONDS", "180"
        ),
        "engine_net_timeout_seconds": os.environ.get(
            "XONOTIC_ENGINE_NET_TIMEOUT_SECONDS", "600"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "created_utc": capture.utc_now(),
    }
    atomic_json(
        temporary / "OPERATIONAL_FAILURE.json",
        diagnostic,
    )
    try:
        os.rename(temporary, destination)
    except FileExistsError:
        shutil.rmtree(temporary)
        if not destination.is_dir():
            raise
    return destination


def certify_one(
    row: dict[str, Any],
    port_pool: queue.Queue[int],
    max_attempts: int,
) -> dict[str, Any]:
    resumed_result = reconcile_published_terminal(
        row, resumed=True
    )
    if resumed_result is not None:
        return resumed_result
    port = port_pool.get()
    try:
        first_attempt = next_attempt_index(row)
        for local_attempt in range(max_attempts):
                                                                       
                                                                  
            resumed_result = reconcile_published_terminal(
                row, resumed=True
            )
            if resumed_result is not None:
                return resumed_result
            attempt_number = first_attempt + local_attempt + 1
            attempt_id = (
                f"{row['episode_id']}_a{attempt_number:02d}"
            )
            stage = capture.TMP_ROOT / "raw" / attempt_id
            if stage.exists():
                capture.clean_stage(stage)
            stage.mkdir(parents=True)
            scenario: dict[str, Any] | None = None
            started = time.monotonic()
            append_event(
                row,
                "certifying",
                attempt_id=attempt_id,
                detail={"port": port},
            )
            try:
                scenario = prepare_scenario(row)
                (stage / "ATTEMPT.json").write_text(
                    json.dumps(
                        {
                            "attempt_id": attempt_id,
                            "scenario": scenario,
                            "build": str(capture.build_root()),
                            "started_utc": capture.utc_now(),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                with capture.live_slot(), capture.sdl_slot():
                    live = capture.run_live_attempt(
                        stage,
                        scenario,
                        capture.build_root(),
                        retry=attempt_number - 1,
                        port=port,
                    )
                precheck = capture.validate_live_precheck(
                    stage,
                    scenario,
                    live,
                    allow_new_player_path_certificate=True,
                )
                states, events, server_rows = (
                    capture.parse_server_telemetry(
                        Path(live["server_telemetry"])
                    )
                )
                motion_metrics = v5.live_motion_metrics(states)
                if event_damage_count(events):
                    raise capture.CaptureFailure(
                        "v5_player_path_damage_rejected",
                        f"count={event_damage_count(events)}",
                    )
                render: dict[str, Any] | None = None
                render_frames: pd.DataFrame | None = None
                render_evidence: dict[str, Any] | None = None
                if visible_collision_requested(scenario):
                    (
                        blockage,
                        render_evidence,
                        render,
                        render_frames,
                    ) = certify_visible_collision_render(
                        stage,
                        scenario,
                        live,
                        states,
                    )
                else:
                    blockage = capture.movement_blockage_metrics(
                        states, scenario=scenario
                    )
                if not blockage["collision_policy_passed"]:
                    raise capture.CaptureFailure(
                        "v5_player_path_collision_rejected",
                        capture.canonical_json(blockage),
                    )
                result = publish_certificate(
                    row,
                    scenario,
                    attempt_id,
                    stage,
                    live,
                    states,
                    events,
                    server_rows,
                    precheck,
                    blockage,
                    motion_metrics,
                    time.monotonic() - started,
                    render=render,
                    render_frames=render_frames,
                    render_evidence=render_evidence,
                )
                append_index_once(result)
                append_event(
                    row,
                    "certified",
                    attempt_id=attempt_id,
                    detail={
                        "path_length_3d": motion_metrics[
                            "path_length_3d"
                        ],
                        "net_displacement_3d": motion_metrics[
                            "net_displacement_3d"
                        ],
                    },
                )
                capture.clean_stage(stage)
                return {
                    "prototype_id": row["episode_id"],
                    "status": "certified",
                    "resumed": False,
                    "record": result,
                }
            except Exception as exc:
                committed_result = reconcile_published_terminal(
                    row,
                    resumed=False,
                    attempt_id=attempt_id,
                    triggering_exception=exc,
                )
                if committed_result is not None:
                    if stage.is_dir():
                        capture.clean_stage(stage)
                    return committed_result
                if publication_integrity_failure(exc):
                                                                       
                                                         
                    raise
                retryable = retryable_certification_failure(exc)
                if not retryable:
                    try:
                        rejection = publish_rejection(
                            row, attempt_id, stage, exc
                        )
                        append_index_once(rejection)
                        append_event(
                            row,
                            "rejected",
                            attempt_id=attempt_id,
                            detail={
                                "reason": rejection["reason"],
                                "detail": rejection["detail"],
                            },
                        )
                    except Exception as publication_exc:
                        committed_result = (
                            reconcile_published_terminal(
                                row,
                                resumed=False,
                                attempt_id=attempt_id,
                                triggering_exception=publication_exc,
                            )
                        )
                        if committed_result is not None:
                            if stage.is_dir():
                                capture.clean_stage(stage)
                            return committed_result
                        raise
                    if stage.is_dir():
                        capture.clean_stage(stage)
                    return {
                        "prototype_id": row["episode_id"],
                        "status": "rejected",
                        "resumed": False,
                        "record": rejection,
                    }
                diagnostic_path: Path | None = None
                diagnostic_error: str | None = None
                try:
                    diagnostic_path = preserve_operational_failure(
                        row,
                        attempt_id,
                        stage,
                        exc,
                    )
                except Exception as diagnostic_exc:
                    diagnostic_error = (
                        f"{type(diagnostic_exc).__name__}:"
                        f" {diagnostic_exc}"
                    )
                event_detail = {
                    "reason": (
                        exc.reason
                        if isinstance(
                            exc, capture.CaptureFailure
                        )
                        else type(exc).__name__
                    ),
                    "detail": str(exc),
                }
                if diagnostic_path is not None:
                    event_detail["diagnostic_path"] = relative_to_root(
                        diagnostic_path
                    )
                if diagnostic_error is not None:
                    event_detail["diagnostic_error"] = diagnostic_error
                append_event(
                    row,
                    "operational_retry",
                    attempt_id=attempt_id,
                    detail=event_detail,
                )
                if stage.is_dir():
                    capture.clean_stage(stage)
        return {
            "prototype_id": row["episode_id"],
            "status": "operational_failure",
            "resumed": False,
            "record": None,
        }
    finally:
        port_pool.put(port)


def summarize(
    rows: list[dict[str, Any]],
    run_results: list[dict[str, Any]],
    *,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    terminal = Counter()
    by_wave: dict[str, Counter[str]] = {}
    for row in rows:
        wave = str(row["candidate_wave"])
        by_wave.setdefault(wave, Counter())
        record = terminal_record(row)
        status = record[0] if record else "pending"
        terminal[status] += 1
        by_wave[wave][status] += 1
    report = {
        "schema_version": (
            "xonotic-stage1-v5-player-path-summary-v1"
        ),
        "created_utc": capture.utc_now(),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "selected_rows": len(rows),
        "current_status": dict(sorted(terminal.items())),
        "by_wave": {
            wave: dict(sorted(counts.items()))
            for wave, counts in sorted(by_wave.items())
        },
        "this_run": dict(
            sorted(Counter(row["status"] for row in run_results).items())
        ),
        "complete": terminal["pending"] == 0,
        "certificate_index_path": relative_to_root(INDEX_PATH),
    }
    atomic_json(summary_path, report)
    return report


def belongs_to_certification_shard(
    row: dict[str, Any], shard_index: int, shard_count: int
) -> bool:
    return (
        int(row["candidate_ordinal"]) - 1
    ) % shard_count == shard_index


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--wave",
        choices=(
            "primary",
            "replenishment",
            "certification_spare",
            "targeted_high",
            "targeted_collision",
            "targeted_fast",
            "targeted_fast_tight",
            "targeted_fast_world",
            "targeted",
            "all",
        ),
        default="primary",
    )
    result.add_argument("--workers", type=int, default=12)
    result.add_argument("--port-base", type=int, default=32_000)
    result.add_argument("--max-attempts", type=int, default=3)
    result.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most this many pending prototypes; 0 means all.",
    )
    result.add_argument(
        "--ordinal-start",
        type=int,
        default=1,
        help="First candidate_ordinal to consider (inclusive).",
    )
    result.add_argument(
        "--ordinal-end",
        type=int,
        default=0,
        help="Last candidate_ordinal to consider; 0 means unbounded.",
    )
    result.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Deterministic certification shard index.",
    )
    result.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Deterministic certification shard count.",
    )
    result.add_argument(
        "--terminal-journal",
        type=Path,
        help=(
            "Explicit single-writer terminal JSONL. Required when "
            "--shard-count is greater than one."
        ),
    )
    result.add_argument(
        "--event-journal",
        type=Path,
        help=(
            "Explicit single-writer event JSONL. Required when "
            "--shard-count is greater than one."
        ),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    if not 1 <= args.workers <= 32:
        raise SystemExit("--workers must be in 1..32")
    if not 1 <= args.max_attempts <= 10:
        raise SystemExit("--max-attempts must be in 1..10")
    if args.ordinal_start < 1:
        raise SystemExit("--ordinal-start must be positive")
    if args.ordinal_end and args.ordinal_end < args.ordinal_start:
        raise SystemExit(
            "--ordinal-end must be zero or >= --ordinal-start"
        )
    if args.shard_count < 1:
        raise SystemExit("--shard-count must be positive")
    if not 0 <= args.shard_index < args.shard_count:
        raise SystemExit("--shard-index must be in 0..shard-count-1")
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise SystemExit(
            f"build source mismatch: expected={EXPECTED_SOURCE_COMMIT} "
            f"actual={source_commit}"
        )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    configure_journals(
        terminal_journal=args.terminal_journal,
        event_journal=args.event_journal,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        wave=args.wave,
    )
    run_lock_path = (
        RUN_LOCK_PATH
        if args.shard_count == 1
        else EVENTS_PATH.with_name(
            f"{EVENTS_PATH.name}.run.lock"
        )
    )
    summary_path = (
        SUMMARY_PATH
        if args.shard_count == 1
        else EVENTS_PATH.with_name(
            f"{EVENTS_PATH.name}.summary.json"
        )
    )
    with run_lock_path.open("a+", encoding="utf-8") as run_lock:
        try:
            fcntl.flock(
                run_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
            )
        except BlockingIOError:
            raise SystemExit(
                "another v5 path certification run is active"
            )
        all_rows = [
            row
            for row in load_prototypes(args.wave)
            if belongs_to_certification_shard(
                row, args.shard_index, args.shard_count
            )
            and int(row["candidate_ordinal"])
            >= args.ordinal_start
            and (
                not args.ordinal_end
                or int(row["candidate_ordinal"])
                <= args.ordinal_end
            )
        ]
        reconciled_terminal_records = reconcile_terminal_index(
            all_rows
        )
        selected = [
            row
            for row in all_rows
            if terminal_record(row) is None
        ]
        if args.limit:
            selected = selected[: args.limit]
        ports: queue.Queue[int] = queue.Queue()
        for offset in range(args.workers):
            ports.put(args.port_base + offset)
        print(
            capture.canonical_json(
                {
                    "event": "v5_player_path_certification_start",
                    "wave": args.wave,
                    "selected": len(selected),
                    "workers": args.workers,
                    "port_base": args.port_base,
                    "ordinal_start": args.ordinal_start,
                    "ordinal_end": args.ordinal_end,
                    "shard_index": args.shard_index,
                    "shard_count": args.shard_count,
                    "terminal_journal": relative_to_root(INDEX_PATH),
                    "event_journal": relative_to_root(EVENTS_PATH),
                    "reconciled_terminal_records": (
                        reconciled_terminal_records
                    ),
                    "created_utc": capture.utc_now(),
                }
            ),
            flush=True,
        )
        run_results: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.workers
        ) as executor:
            futures = [
                executor.submit(
                    certify_one, row, ports, args.max_attempts
                )
                for row in selected
            ]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                run_results.append(result)
                print(
                    capture.canonical_json(
                        {
                            "prototype_id": result["prototype_id"],
                            "status": result["status"],
                            "resumed": result["resumed"],
                        }
                    ),
                    flush=True,
                )
        report = summarize(
            all_rows,
            run_results,
            summary_path=summary_path,
        )
        print(json.dumps(report, indent=2, sort_keys=True), flush=True)
        return (
            2
            if any(
                row["status"] == "operational_failure"
                for row in run_results
            )
            else 0
        )


if __name__ == "__main__":
    raise SystemExit(main())
