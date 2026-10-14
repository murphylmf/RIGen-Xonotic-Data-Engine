                      
"""Shared resident-lane support for the isolated Stage-2 v12 runner."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import fcntl
import json
import os
import queue
import re
import shutil
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

                                                                           
                                                                       
                                                                              
RETRYABLE_PRE_PAIR_QA_CHECKS = {
    "server_state_rows_384",
    "render_frame_rows_320",
    "exact_episode_tick_span_64_through_383",
    "zero_error_frame_state_mapping",
    "raw_server_ticks_strictly_consecutive",
    "fixed_demo_presentation_phase",
    "requested_action_rows_384",
    "engine_action_rows_384",
    "review_video_81_frames",
    "prefrozen_player_trace_runtime_recertified",
}

os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG", BUILD_TAG
)
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT", SOURCE_COMMIT
)
os.environ.setdefault("XONOTIC_BUILD_GLOB", f"build/{BUILD_TAG}")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from pilot_scripts import build_samples as pilot              
import xonotic_stage1_reusable as reusable              


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(canonical_json(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def validate_manifest(
    manifest_path: Path,
    metadata_path: Path,
    shard_index: int,
    shard_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    declared_dependency_locks = metadata.get("runtime_dependency_locks") or {}
    dependency_checks: dict[str, bool] = {}
    for relative, digest in declared_dependency_locks.items():
        lock = ROOT / relative
        hash_matches = (
            lock.is_file() and pilot.sha256_file(lock) == digest
        )
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
    checks = {
        "formal_collection_authorized": metadata.get(
            "formal_collection_authorized"
        )
        is True,
        "training_admitted_false": metadata.get("training_admitted") is False,
        "source_commit": metadata.get("source_commit") == SOURCE_COMMIT,
        "build_tag": metadata.get("build_tag") == BUILD_TAG,
        "shard_count": int(metadata.get("shard_count", -1)) == shard_count,
        "shard_declared": declared is not None,
        "build_lock_hash": metadata.get("build_lock_sha256")
        == pilot.sha256_file(BUILD_LOCK),
        "runtime_files": all(
            (ROOT / relative).is_file()
            and pilot.sha256_file(ROOT / relative) == digest
            for relative, digest in (metadata.get("runtime_files") or {}).items()
        )
        and set((metadata.get("runtime_files") or {}))
        == {
            "pilot_scripts/build_samples.py",
            "production_scripts/prepare_stage2_motion_40k_manifest.py",
            "production_scripts/run_stage2_motion_40k_shard.py",
            "production_scripts/launch_dlc_8x1.sh",
            "production_scripts/launch_dlc_12x1.sh",
            "scripts/xonotic_stage1_reusable.py",
        },
        "manifest_schema_v9": metadata.get("schema_version")
        == "xonotic-stage2-motion-near5-combo-manifest-metadata-v9",
        "runtime_dependency_locks": set(declared_dependency_locks)
        == REQUIRED_DEPENDENCY_LOCKS
        and all(dependency_checks.values()),
    }
    if declared is not None:
        checks.update(
            {
                "shard_path": Path(declared["path"]).name
                == manifest_path.name,
                "shard_hash": declared["sha256"]
                == pilot.sha256_file(manifest_path),
            }
        )
    if not all(checks.values()):
        raise RuntimeError(f"manifest metadata checks failed: {checks}")
    rows = load_jsonl(manifest_path)
    ids = [str(row.get("pair_id", "")) for row in rows]
    row_checks = {
        "rows_declared": declared is not None
        and len(rows) == int(declared["rows"]),
        "row_schema_v9": all(
            row.get("schema_version")
            == "xonotic-stage2-motion-near5-combo-production-pair-v9"
            for row in rows
        ),
        "pair_ids_present": all(ids),
        "pair_ids_unique": len(ids) == len(set(ids)),
        "assigned_shard": all(
            int(row.get("assigned_shard", -1)) == shard_index for row in rows
        ),
        "shard_count": all(
            int(row.get("shard_count", -1)) == shard_count for row in rows
        ),
        "active_authorized": all(
            row["active_scenario"].get("formal_collection_authorized") is True
            and row["active_scenario"].get("training_admitted") is False
            and row["active_scenario"].get("source_commit_required")
            == SOURCE_COMMIT
            for row in rows
        ),
        "frozen_qa_only": all(
            row["frozen_scenario"].get("formal_collection_authorized") is False
            and row["frozen_scenario"].get("training_admitted") is False
            and row["frozen_scenario"].get("interaction_role") == "frozen_qa"
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
        "enemy_motion_basis_frozen_no_live_reads": all(
            row["active_scenario"]
            .get("enemy_motion_basis", {})
            .get("method")
            == "manifest_frozen_initial_line_of_sight_left_tangent_v1"
            and row["active_scenario"]
            .get("enemy_motion_basis", {})
            .get("reads_camera")
            is False
            and row["active_scenario"]
            .get("enemy_motion_basis", {})
            .get("reads_live_player_state")
            is False
            for row in rows
        ),
    }
    if not all(row_checks.values()):
        raise RuntimeError(f"manifest row checks failed: {row_checks}")
    return rows, {
        "metadata_checks": checks,
        "runtime_dependency_checks": dependency_checks,
        "row_checks": row_checks,
    }


def preflight_gpu() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0 or len(lines) != 1:
        raise RuntimeError(
            "exactly one visible GPU is required: "
            f"rc={completed.returncode} rows={lines} error={completed.stderr}"
        )
    fields = [value.strip() for value in lines[0].split(",", 3)]
    return {
        "index": fields[0],
        "name": fields[1],
        "uuid": fields[2],
        "memory_total_mib": int(fields[3]),
    }


def gpu_runtime_sample() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0 or len(lines) != 1:
        return {
            "sampled_utc": pilot.capture.utc_now(),
            "available": False,
            "returncode": completed.returncode,
            "stderr": completed.stderr.strip(),
        }
    fields = [value.strip() for value in lines[0].split(",", 4)]
    return {
        "sampled_utc": pilot.capture.utc_now(),
        "available": True,
        "index": fields[0],
        "name": fields[1],
        "utilization_percent": int(fields[2]),
        "memory_used_mib": int(fields[3]),
        "memory_total_mib": int(fields[4]),
    }


def verify_build_lock() -> None:
    completed = subprocess.run(
        ["sha256sum", "-c", str(BUILD_LOCK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"runtime build lock failed: {completed.stdout}{completed.stderr}"
        )
    commit = (ROOT / "build" / BUILD_TAG / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if commit != SOURCE_COMMIT:
        raise RuntimeError(
            f"runtime source mismatch: expected={SOURCE_COMMIT} actual={commit}"
        )


def essential_hashes(episode_path: Path) -> dict[str, str]:
    paths = (
        "scenario.json",
        "prompt.json",
        "qa.json",
        "pair_qa.json",
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
    active_path = Path(record["video_path"]).parents[1]
    frozen_path = active_path.parent / record["counterfactual_episode_id"]
    for root, hashes in (
        (active_path, record["active_artifact_hashes"]),
        (frozen_path, record["frozen_artifact_hashes"]),
    ):
        for relative, digest in hashes.items():
            path = root / relative
            if not path.is_file() or pilot.sha256_file(path) != digest:
                return False
    return True


def archive_partial(
    shard_root: Path,
    scratch_root: Path,
    episode_id: str,
    attempt: int,
    error: str,
) -> dict[str, Any]:
    destination = (
        shard_root
        / "diagnostics/rejects"
        / f"{episode_id}_attempt{attempt:02d}"
    )
    destination.mkdir(parents=True, exist_ok=False)
    packaged = shard_root / "episodes" / episode_id
    packaged_destination = destination / "partial_package"
    if packaged.exists():
        os.replace(packaged, packaged_destination)
    stage = scratch_root / episode_id
    copied: list[str] = []
    if stage.is_dir():
        logs = destination / "scratch_logs"
        logs.mkdir()
        for name in (
            "server_console.log",
            "client_live_console.log",
            "client_render_console.log",
            "actions_requested.csv",
        ):
            source = stage / name
            if source.is_file():
                shutil.copy2(source, logs / name)
                copied.append(name)
        shutil.rmtree(stage)
    atomic_json(
        destination / "ERROR.json",
        {
            "episode_id": episode_id,
            "attempt": attempt,
            "error": error,
            "packaged_partial_preserved": packaged_destination.exists(),
            "scratch_logs_preserved": copied,
        },
    )
    return {
        "diagnostic_path": str(destination),
        "packaged_partial_preserved": packaged_destination.exists(),
        "scratch_logs_preserved": copied,
    }


def _safe_remove_scratch_tree(path: Path, scratch_root: Path) -> None:
    """Remove only a resolved descendant of this worker's scratch root."""
    if not path.exists():
        return
    resolved = path.resolve()
    allowed = scratch_root.resolve()
    if resolved == allowed or allowed not in resolved.parents:
        raise RuntimeError(
            f"refusing scratch cleanup outside worker root: {resolved}"
        )
    shutil.rmtree(resolved)


class Stage2ResidentLaneController:
    """Own one fail-closed resident triplet for one exact world group.

    Process resources are reused, but every episode still receives a fresh
    server world, network connection, demo, playback reset and artifact path.
    A failure invalidates all three processes before the operational retry.
    """

    def __init__(
        self,
        *,
        lane_index: int,
        group_index: int,
        world_group: tuple[str, str],
        port: int,
        build: Path,
        shard_root: Path,
        scratch_root: Path,
    ) -> None:
        self.lane_index = lane_index
        self.group_index = group_index
        self.world_group = world_group
        self.port = port
        self.build = build
        self.shard_root = shard_root
        self.scratch_root = scratch_root
        self.generation = 0
        self.lane: reusable.ReusableStage1Lane | None = None
        self.lane_root: Path | None = None
        self.warmed = False

    def _start(self) -> reusable.ReusableStage1Lane:
        self.generation += 1
        map_name, gametype = self.world_group
        safe_world = re.sub(
            r"[^A-Za-z0-9_.-]+", "_", f"{map_name}__{gametype}"
        )
        token = (
            f"lane-{self.lane_index:02d}"
            f"-group-{self.group_index:03d}"
            f"-gen-{self.generation:03d}-{safe_world}"
        )
        self.lane_root = self.scratch_root / "_resident_lanes" / token
        _safe_remove_scratch_tree(self.lane_root, self.scratch_root)
        self.lane_root.parent.mkdir(parents=True, exist_ok=True)
        self.lane = reusable.ReusableStage1Lane(
            self.lane_root,
            build=self.build,
            port=self.port,
            live_cpu_slot=self.lane_index,
        )
        self.warmed = False
        return self.lane

    def _allocate_warmup_evidence(self) -> tuple[str, Path]:
        map_name, gametype = self.world_group
        safe_world = re.sub(
            r"[^A-Za-z0-9_.-]+", "_", f"{map_name}__{gametype}"
        )
        base = (
            f"resident_warmup_l{self.lane_index:02d}"
            f"_g{self.group_index:03d}"
            f"_r{self.generation:03d}_p{os.getpid()}"
        )
        parent = self.shard_root / "resident_warmups" / safe_world
        parent.mkdir(parents=True, exist_ok=True)
        for sequence in range(1_000_000):
            warmup_id = base if sequence == 0 else f"{base}_u{sequence:06d}"
            evidence = parent / warmup_id
            try:
                evidence.mkdir(exist_ok=False)
                return warmup_id, evidence
            except FileExistsError:
                continue
        raise RuntimeError(f"warmup evidence namespace exhausted: {base}")

    def _warmup(
        self,
        lane: reusable.ReusableStage1Lane,
        scenario: dict[str, Any],
    ) -> None:
        allow_realtime_validation_baseline = (
            os.environ.get(
                "XONOTIC_ALLOW_LIVE_TIME_SCALE_ONE_VALIDATION", "0"
            )
            == "1"
        )
        warmup_id, evidence = self._allocate_warmup_evidence()
        warmup_scenario = copy.deepcopy(scenario)
        warmup_scenario["episode_id"] = warmup_id
        warmup_scenario["formal_collection_authorized"] = False
        warmup_scenario["training_admitted"] = False
        warmup_scenario["formal_authorization_basis"] = (
            "discarded_resident_process_full_qa_warmup"
        )
        warmup_output = (
            self.scratch_root / "_resident_warmup_outputs" / warmup_id
        )
        warmup_stage_root = self.scratch_root / "_resident_warmup_stages"
        warmup_stage = warmup_stage_root / warmup_id
        _safe_remove_scratch_tree(warmup_output, self.scratch_root)
        _safe_remove_scratch_tree(warmup_stage, self.scratch_root)
        started = time.monotonic()
        atomic_json(
            evidence / "ALLOCATION.json",
            {
                "schema_version": "xonotic-stage2-resident-warmup-allocation-v1",
                "episode_id": warmup_id,
                "source_episode_id": scenario["episode_id"],
                "lane_index": self.lane_index,
                "group_index": self.group_index,
                "generation": self.generation,
                "map": self.world_group[0],
                "gametype": self.world_group[1],
                "formal_collection_authorized": False,
                "training_admitted": False,
                "created_utc": pilot.capture.utc_now(),
            },
        )
        try:
            result = pilot.capture_episode(
                warmup_scenario,
                warmup_output,
                warmup_stage_root,
                port=self.port,
                cleanup_scratch=True,
                retain_raw_avi=False,
                resident_lane=lane,
            )
            qa = result["qa"]
            runtime = qa.get("runtime") or {}
            resident = runtime.get("resident_lane") or {}
            reserved_cpus = set(resident.get("reserved_live_cpus") or [])
            background_cpus = set(resident.get("background_cpus") or [])
            server_scheduling = resident.get("server_cpu_scheduling") or {}
            live_scheduling = resident.get(
                "live_client_cpu_scheduling"
            ) or {}
            render_scheduling = resident.get(
                "render_client_cpu_scheduling"
            ) or {}
            reserved_cpu_list = sorted(reserved_cpus)
            server_cpu_index = self.lane_index * 2
            live_cpu_index = server_cpu_index + 1
            server_cpu = (
                [reserved_cpu_list[server_cpu_index]]
                if server_cpu_index < len(reserved_cpu_list)
                else []
            )
            live_cpu = (
                [reserved_cpu_list[live_cpu_index]]
                if live_cpu_index < len(reserved_cpu_list)
                else []
            )
            x264_cpus = pilot.capture.parse_cpu_list(
                str(runtime.get("x264_cpuset", ""))
            )
                                                                              
                                                                           
                                                                        
                                                                             
            semantic_qa_observation = {
                "pre_pair_passed": qa["pre_pair_passed"] is True,
                "failed_checks": sorted(
                    key for key, passed in qa["checks"].items() if not passed
                ),
            }
            checks = {
                "frame_contract": (
                    qa["checks"]["render_frame_rows_320"] is True
                    and qa["checks"][
                        "exact_episode_tick_span_64_through_383"
                    ]
                    is True
                    and qa["checks"]["fixed_demo_presentation_phase"] is True
                ),
                "action_contract": (
                    qa["checks"]["requested_action_rows_384"] is True
                    and qa["checks"]["engine_action_rows_384"] is True
                ),
                "resident_execution": (
                    runtime.get("execution_mode") == "resident_accelerated"
                ),
                "offline_acceleration_realized": (
                    runtime.get("offline_accelerate") is True
                    and runtime.get("capturevideo_realtime") is False
                    and abs(
                        float(runtime.get("effective_demo_timescale")) - 1.0
                    )
                    <= 1e-12
                ),
                "accelerated_live_simulation_realized": (
                    runtime.get("live_time_scale")
                    == reusable.configured_live_time_scale()
                    and (
                        runtime.get("live_time_scale", 1) > 1
                        or allow_realtime_validation_baseline
                    )
                    and abs(
                        float(runtime.get("live_server_ticrate"))
                        - 1.0
                        / (
                            reusable.AUTHORITATIVE_TICKS_PER_SECOND
                            * reusable.configured_live_time_scale()
                        )
                    )
                    <= 1e-12
                ),
                "isolated_render_generation_realized": (
                    (
                        (runtime.get("resident_lane") or {}).get(
                            "render_generation"
                        )
                        is not None
                        and (runtime.get("resident_lane") or {}).get(
                            "render_process_recycled_after_episode"
                        )
                        is True
                    )
                    if runtime.get("live_time_scale", 1) > 1
                    else allow_realtime_validation_baseline
                ),
                "low_cost_live_pass_realized": (
                    (runtime.get("live_capture_geometry") or {}).get("width")
                    == reusable.LIVE_CAPTURE_WIDTH
                    and (runtime.get("live_capture_geometry") or {}).get(
                        "height"
                    )
                    == reusable.LIVE_CAPTURE_HEIGHT
                    and (runtime.get("live_capture_geometry") or {}).get(
                        "r_renderview"
                    )
                    is False
                    and (runtime.get("live_capture_geometry") or {}).get(
                        "scr_refresh"
                    )
                    is False
                ),
                "resident_server_idle_throttle_realized": (
                    (runtime.get("resident_lane") or {}).get(
                        "server_idle_throttle_verified"
                    )
                    is True
                    and (runtime.get("resident_lane") or {}).get(
                        "server_idle_ticrate"
                    )
                    is not None
                    and abs(
                        float(
                            (runtime.get("resident_lane") or {}).get(
                                "server_idle_ticrate"
                            )
                        )
                        - reusable.IDLE_SERVER_TICRATE
                    )
                    <= 1e-12
                    and (runtime.get("resident_lane") or {}).get(
                        "server_idle_slowmo"
                    )
                    is not None
                    and float(
                        (runtime.get("resident_lane") or {}).get(
                            "server_idle_slowmo"
                        )
                    )
                    == reusable.IDLE_SERVER_SLOWMO
                ),
                "resident_cpu_isolation_realized": (
                    resident.get("cpu_isolation_enabled") is True
                    and resident.get("live_cpu_slot") == self.lane_index
                    and len(reserved_cpus) > live_cpu_index
                    and bool(background_cpus)
                    and not reserved_cpus & background_cpus
                    and server_scheduling.get("all_threads_match") is True
                    and live_scheduling.get("all_threads_match") is True
                    and render_scheduling.get("all_threads_match") is True
                    and server_scheduling.get("expected_cpu_affinity")
                    == server_cpu
                    and live_scheduling.get("expected_cpu_affinity")
                    == live_cpu
                    and render_scheduling.get("expected_cpu_affinity")
                    == sorted(background_cpus)
                    and bool(x264_cpus)
                    and x264_cpus <= background_cpus
                    and not x264_cpus & reserved_cpus
                ),
                "training_excluded": (
                    warmup_scenario["formal_collection_authorized"] is False
                    and warmup_scenario["training_admitted"] is False
                    and qa["training_admitted"] is False
                ),
            }
            episode_path = Path(result["episode_path"])
            for relative in (
                "scenario.json",
                "prompt.json",
                "qa.json",
                "raw/server_console.log",
                "raw/client_live_console.log",
                "raw/client_render_console.log",
                                                                     
                                                                         
                                                                          
                                                                  
                "raw/server.jsonl",
                "raw/frames_engine.csv",
            ):
                source = episode_path / relative
                if source.is_file():
                    destination = evidence / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            record = {
                "schema_version": "xonotic-stage2-resident-warmup-v1",
                "episode_id": warmup_id,
                "source_episode_id": scenario["episode_id"],
                "lane_index": self.lane_index,
                "group_index": self.group_index,
                "generation": self.generation,
                "map": self.world_group[0],
                "gametype": self.world_group[1],
                "passed": all(checks.values()),
                "checks": checks,
                "semantic_qa_observation": semantic_qa_observation,
                "qa_sha256": pilot.sha256_file(episode_path / "qa.json"),
                "wall_seconds": time.monotonic() - started,
                "formal_collection_authorized": False,
                "training_admitted": False,
                "created_utc": pilot.capture.utc_now(),
            }
            atomic_json(evidence / "RESULT.json", record)
            if not record["passed"]:
                raise RuntimeError(f"resident warmup QA failed: {checks}")
            self.warmed = True
        except Exception as exc:
                                                                             
                                                     
            for source in (
                warmup_stage / "server_console.log",
                warmup_stage / "client_live_console.log",
                warmup_stage / "client_render_console.log",
            ):
                if source.is_file():
                    destination = evidence / "failure_logs" / source.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            atomic_json(
                evidence / "FAILURE.json",
                {
                    "schema_version": "xonotic-stage2-resident-warmup-failure-v1",
                    "episode_id": warmup_id,
                    "source_episode_id": scenario["episode_id"],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "wall_seconds": time.monotonic() - started,
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "created_utc": pilot.capture.utc_now(),
                },
            )
                                                                          
                                                                            
                                                                           
                                   
            self.invalidate()
            raise RuntimeError(
                f"resident warmup failed; evidence={evidence}: {exc}"
            ) from exc
        finally:
            _safe_remove_scratch_tree(warmup_output, self.scratch_root)
            _safe_remove_scratch_tree(warmup_stage, self.scratch_root)

    def get_lane(
        self, scenario: dict[str, Any]
    ) -> reusable.ReusableStage1Lane:
        requested = (
            str(scenario["map"]),
            str(scenario.get("gametype", "dm")).lower(),
        )
        if requested != self.world_group:
            raise RuntimeError(
                "resident scheduler world-group mismatch: "
                f"expected={self.world_group} actual={requested}"
            )
        lane = self.lane if self.lane is not None else self._start()
        if not self.warmed:
            self._warmup(lane, scenario)
        return lane

    def invalidate(self) -> None:
        lane = self.lane
        self.lane = None
        if lane is not None:
            try:
                lane.close()
            except Exception as exc:
                print(
                    canonical_json(
                        {
                            "event": "resident_lane_cleanup_warning",
                            "lane_index": self.lane_index,
                            "group_index": self.group_index,
                            "generation": self.generation,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    ),
                    file=sys.stderr,
                    flush=True,
                )
        try:
            if self.lane_root is not None:
                _safe_remove_scratch_tree(
                    self.lane_root, self.scratch_root
                )
        finally:
            self.lane_root = None
            self.warmed = False

    def close(self) -> None:
        self.invalidate()


def resident_lane_plans(
    rows: list[dict[str, Any]], workers: int
) -> list[list[tuple[tuple[str, str], list[dict[str, Any]]]]]:
    """Deterministic LPT balance without reuse across world boundaries."""
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
            key=lambda row: (int(row["ordinal"]), str(row["pair_id"])),
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
            str(item[1][0]["pair_id"]),
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


def training_candidate_record(
    row: dict[str, Any],
    active: dict[str, Any],
    frozen: dict[str, Any],
    pair: dict[str, Any],
) -> dict[str, Any]:
    active_path = Path(active["episode_path"])
    frozen_path = Path(frozen["episode_path"])
    return {
        "schema_version": "xonotic-stage2-motion-near5-combo-captured-sample-v9",
        "sample_id": active["episode_id"],
        "pair_id": row["pair_id"],
        "ordinal": int(row["ordinal"]),
        "training_admitted": False,
        "capture_qa_passed": True,
        "video_path": str(active_path / "media/review_20hz_81f.mp4"),
        "source_video_path": str(active_path / "media/source_64hz.mkv"),
        "action_path": str(
            active_path / "telemetry/actions_requested_64hz.parquet"
        ),
        "state_path": str(active_path / "telemetry/states_64hz.parquet"),
        "visibility_path": str(
            active_path / "telemetry/visibility_64hz.parquet"
        ),
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
        "distance_tier": active["scenario"]["distance_tier"],
        "target_initial_distance_units": active["scenario"][
            "target_initial_distance_units"
        ],
        "actual_initial_distance_units": active["qa"]["screen_distance"][
            "initial_distance_world"
        ],
        "minimum_enemy_screen_height_pixels": active["qa"][
            "screen_distance"
        ]["minimum_height_pixels"],
        "counterfactual_episode_id": frozen["episode_id"],
        "pair_qa_path": str(active_path / "pair_qa.json"),
        "active_artifact_hashes": essential_hashes(active_path),
        "frozen_artifact_hashes": essential_hashes(frozen_path),
        "pair_qa_sha256": pilot.sha256_file(active_path / "pair_qa.json"),
        "source_formal_episode_id": row["source_formal_episode_id"],
        "pair_checks": pair["checks"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=8)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--execution-mode",
        choices=("resident", "oneshot"),
        default=os.environ.get(
            "XONOTIC_STAGE2_EXECUTION_MODE", "resident"
        ),
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
        "--x264-cpuset",
        default=os.environ.get("XONOTIC_X264_CPUSET", ""),
    )
    parser.add_argument(
        "--render-timeout-seconds",
        type=float,
        default=float(
            os.environ.get("XONOTIC_RENDER_TIMEOUT_SECONDS", "240")
        ),
    )
    parser.add_argument(
        "--resident-control-timeout-seconds",
        type=float,
        default=float(
            os.environ.get(
                "XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "240"
            )
        ),
    )
    parser.add_argument("--port-base", type=int, default=26000)
    parser.add_argument("--max-operational-attempts", type=int, default=4)
    parser.add_argument("--max-pairs", type=int)
    parser.add_argument("--allow-partial-smoke", action="store_true")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.shard_index < args.shard_count:
        parser.error("--shard-index must be inside the shard range")
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    if not 1 <= args.encode_concurrency <= 16:
        parser.error("--encode-concurrency must be between 1 and 16")
    if not 1 <= args.render_concurrency <= 16:
        parser.error("--render-concurrency must be between 1 and 16")
    if not 1 <= args.live_concurrency <= 16:
        parser.error("--live-concurrency must be between 1 and 16")
    if not 1 <= args.x264_threads <= 64:
        parser.error("--x264-threads must be between 1 and 64")
    if not 30 <= args.render_timeout_seconds <= 3600:
        parser.error("--render-timeout-seconds must be between 30 and 3600")
    if not 30 <= args.resident_control_timeout_seconds <= 600:
        parser.error(
            "--resident-control-timeout-seconds must be between 30 and 600"
        )
    if not 1 <= args.max_operational_attempts <= 4:
        parser.error("--max-operational-attempts must be between 1 and 4")
    if args.max_pairs is not None and (
        args.max_pairs < 1 or not args.allow_partial_smoke
    ):
        parser.error("--max-pairs requires --allow-partial-smoke")

    cpu_isolation = None
    if args.execution_mode == "resident":
        cpu_isolation = reusable.configure_resident_cpu_isolation(
            args.workers,
            requested_x264_cpuset=args.x264_cpuset,
        )
        args.x264_cpuset = os.environ["XONOTIC_X264_CPUSET"]

    manifest = args.manifest.resolve()
    metadata = args.metadata.resolve()
    output_root = args.output_root.resolve()
    scratch_root = args.scratch_root.resolve()
    shard_root = output_root / f"shard_{args.shard_index:02d}"
    shard_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lock_path = shard_root / "SHARD.lock"
    lock_handle = lock_path.open("a+b")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError(f"shard already has an active owner: {lock_path}") from exc

    verify_build_lock()
    rows, manifest_checks = validate_manifest(
        manifest, metadata, args.shard_index, args.shard_count
    )
    if args.max_pairs is not None:
        rows = rows[: args.max_pairs]
    gpu = preflight_gpu()
    os.environ["XONOTIC_LIVE_CONCURRENCY"] = str(args.live_concurrency)
    os.environ["XONOTIC_RENDER_CONCURRENCY"] = str(
        args.render_concurrency
    )
    os.environ["XONOTIC_SDL_CONCURRENCY"] = str(args.workers)
    os.environ["XONOTIC_ENCODE_CONCURRENCY"] = str(
        args.encode_concurrency
    )
    os.environ["XONOTIC_X264_THREADS"] = str(args.x264_threads)
    os.environ["XONOTIC_X264_CPUSET"] = args.x264_cpuset
    os.environ["XONOTIC_RENDER_TIMEOUT_SECONDS"] = str(
        args.render_timeout_seconds
    )
    os.environ["XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS"] = str(
        args.resident_control_timeout_seconds
    )
    os.environ["XONOTIC_OFFLINE_ACCELERATE"] = "1"
    pilot.run_protection_check(shard_root / "STAGE12_PRECHECK.txt")

    accepted_journal = shard_root / "manifests/accepted.jsonl"
    rejected_journal = shard_root / "manifests/rejected.jsonl"
    accepted_rows = load_jsonl(accepted_journal)
    accepted_by_id = {str(row["pair_id"]): row for row in accepted_rows}
    accepted_ids = set(accepted_by_id)
    accepted_lock = threading.Lock()
    build = pilot.capture.build_root()
    lane_plans = (
        resident_lane_plans(rows, args.workers)
        if args.execution_mode == "resident"
        else None
    )
    port_queue: queue.Queue[int] = queue.Queue()
    if args.execution_mode == "oneshot":
        for offset in range(args.workers):
            port_queue.put(args.port_base + offset)

    resident_schedule = (
        [
            {
                "lane_index": lane_index,
                "port": args.port_base + lane_index,
                "pairs": sum(len(group_rows) for _, group_rows in groups),
                "groups": [
                    {
                        "map": world_group[0],
                        "gametype": world_group[1],
                        "pairs": len(group_rows),
                        "first_ordinal": int(group_rows[0]["ordinal"]),
                        "last_ordinal": int(group_rows[-1]["ordinal"]),
                        "first_pair_id": str(group_rows[0]["pair_id"]),
                        "last_pair_id": str(group_rows[-1]["pair_id"]),
                    }
                    for world_group, group_rows in groups
                ],
            }
            for lane_index, groups in enumerate(lane_plans or [])
        ]
        if lane_plans is not None
        else None
    )

    run_metadata = {
        "schema_version": "xonotic-stage2-motion-near5-combo-dlc-shard-run-v9",
        "started_utc": pilot.capture.utc_now(),
        "manifest": str(manifest),
        "manifest_sha256": pilot.sha256_file(manifest),
        "metadata": str(metadata),
        "metadata_sha256": pilot.sha256_file(metadata),
        "manifest_checks": manifest_checks,
        "output_root": str(output_root),
        "scratch_root": str(scratch_root),
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "planned_pairs": len(rows),
        "workers": args.workers,
        "execution_mode": args.execution_mode,
        "resident_reuse_policy": (
            "exact_map_gametype_group_only; discarded nontraining "
            "full-Stage2-QA warmup per process generation; fresh server "
            "world, connection and demo per episode; accelerated playback "
            "uses a fresh render-process generation; duel-v8 global "
            "record-all/barrier/replay-render-encode-QA-all microbatches; "
            "serialized warmups never overlap authoritative recording; "
            "destroy full lane on any operational failure or group change"
            if args.execution_mode == "resident"
            else None
        ),
        "resident_schedule_policy": (
            "deterministic_lpt_over_isolated_world_group_chunks; "
            "one pair per lane per globally phase-separated microbatch"
            if args.execution_mode == "resident"
            else None
        ),
        "global_phase_barrier": args.execution_mode == "resident",
        "acceleration_reference": (
            str(
                Path(
                    "./xonotic_workspace"
                    "scripts/benchmark_concurrency.sh"
                )
            )
            if args.execution_mode == "resident"
            else None
        ),
        "resident_schedule": resident_schedule,
        "offline_accelerate": True,
        "live_time_scale": reusable.configured_live_time_scale(),
        "live_server_ticrate": 1.0
        / (
            reusable.AUTHORITATIVE_TICKS_PER_SECOND
            * reusable.configured_live_time_scale()
        ),
        "live_capture_geometry": {
            "width": reusable.LIVE_CAPTURE_WIDTH,
            "height": reusable.LIVE_CAPTURE_HEIGHT,
            "r_renderview": False,
            "scr_refresh": False,
        },
        "render_capture_geometry": {
            "width": pilot.capture.WIDTH,
            "height": pilot.capture.HEIGHT,
            "r_renderview": True,
            "scr_refresh": True,
        },
        "encode_concurrency": args.encode_concurrency,
        "render_concurrency": args.render_concurrency,
        "live_concurrency": args.live_concurrency,
        "x264_threads": args.x264_threads,
        "x264_cpuset": args.x264_cpuset,
        "resident_cpu_isolation": cpu_isolation,
        "render_timeout_seconds": args.render_timeout_seconds,
        "resident_control_timeout_seconds": (
            args.resident_control_timeout_seconds
        ),
        "port_base": args.port_base,
        "gpu": gpu,
        "build_tag": BUILD_TAG,
        "source_commit": SOURCE_COMMIT,
        "raw_avi_audit_percent_active": 5,
        "raw_avi_counterfactual_retained": False,
    }
    atomic_json(shard_root / "RUN_METADATA.json", run_metadata)
    print(canonical_json({"event": "shard_start", **run_metadata}), flush=True)

    def process_pair(
        row: dict[str, Any],
        *,
        assigned_port: int | None = None,
        resident_controller: Stage2ResidentLaneController | None = None,
    ) -> dict[str, Any]:
        pair_id = str(row["pair_id"])
        with accepted_lock:
            if pair_id in accepted_ids:
                if not verify_accepted_record(accepted_by_id[pair_id]):
                    raise RuntimeError(
                        f"accepted artifact integrity failed: {pair_id}"
                    )
                return {"pair_id": pair_id, "status": "accepted_resume"}
        owns_port = assigned_port is None
        port = port_queue.get() if owns_port else assigned_port
        assert port is not None
        try:
            active_scenario = row["active_scenario"]
            frozen_scenario = row["frozen_scenario"]
            active: dict[str, Any] | None = None
            frozen: dict[str, Any] | None = None
            for role, scenario in (
                ("active", active_scenario),
                ("frozen_qa", frozen_scenario),
            ):
                episode_id = str(scenario["episode_id"])
                destination = shard_root / "episodes" / episode_id
                captured: dict[str, Any] | None = None
                if destination.is_dir():
                    try:
                        captured = pilot.load_packaged_episode(
                            shard_root, episode_id
                        )
                    except Exception as exc:
                        archive_partial(
                            shard_root,
                            scratch_root,
                            episode_id,
                            0,
                            f"resume_validation_failed: {exc}",
                        )
                if captured is None:
                    last_error: Exception | None = None
                    for attempt in range(1, args.max_operational_attempts + 1):
                        try:
                            print(
                                canonical_json(
                                    {
                                        "event": "capture_start",
                                        "pair_id": pair_id,
                                        "role": role,
                                        "episode_id": episode_id,
                                        "attempt": attempt,
                                        "port": port,
                                        "execution_mode": (
                                            "resident"
                                            if resident_controller is not None
                                            else "oneshot"
                                        ),
                                        "resident_generation": (
                                            resident_controller.generation
                                            if resident_controller is not None
                                            else None
                                        ),
                                    }
                                ),
                                flush=True,
                            )
                            resident_lane = (
                                resident_controller.get_lane(scenario)
                                if resident_controller is not None
                                else None
                            )
                            captured = pilot.capture_episode(
                                scenario,
                                shard_root,
                                scratch_root,
                                port=port,
                                cleanup_scratch=True,
                                retain_raw_avi=(
                                    bool(row["raw_avi_audit"])
                                    if role == "active"
                                    else False
                                ),
                                resident_lane=resident_lane,
                            )
                            failed_checks = {
                                key
                                for key, passed in captured["qa"][
                                    "checks"
                                ].items()
                                if not passed
                            }
                            retryable_failed_checks = sorted(
                                failed_checks & RETRYABLE_PRE_PAIR_QA_CHECKS
                            )
                            if retryable_failed_checks:
                                raise RuntimeError(
                                    "retryable_pre_pair_qa_failed:"
                                    + ",".join(retryable_failed_checks)
                                )
                            break
                        except Exception as exc:
                            last_error = exc
                            if resident_controller is not None:
                                resident_controller.invalidate()
                            diagnostic = archive_partial(
                                shard_root,
                                scratch_root,
                                episode_id,
                                attempt,
                                f"{type(exc).__name__}: {exc}",
                            )
                                                                          
                                                                             
                                                                           
                                                                            
                                                                       
                                                                            
                                                       
                            captured = None
                            print(
                                canonical_json(
                                    {
                                        "event": "capture_retry",
                                        "pair_id": pair_id,
                                        "role": role,
                                        "attempt": attempt,
                                        "error": f"{type(exc).__name__}: {exc}",
                                        **diagnostic,
                                    }
                                ),
                                flush=True,
                            )
                    if captured is None:
                        assert last_error is not None
                        rejection = {
                            "schema_version": "xonotic-stage2-motion-near5-combo-reject-v9",
                            "pair_id": pair_id,
                            "ordinal": int(row["ordinal"]),
                            "role": role,
                            "reason": "operational_attempts_exhausted",
                            "error_type": type(last_error).__name__,
                            "error": str(last_error),
                            "traceback": traceback.format_exc(),
                            "rejected_utc": pilot.capture.utc_now(),
                        }
                        append_jsonl(rejected_journal, rejection)
                        return {"pair_id": pair_id, "status": "rejected"}
                if role == "active":
                    active = captured
                    if not active["qa"]["pre_pair_passed"]:
                        rejection = {
                            "schema_version": "xonotic-stage2-motion-near5-combo-reject-v9",
                            "pair_id": pair_id,
                            "ordinal": int(row["ordinal"]),
                            "role": role,
                            "reason": "active_pre_pair_qa_failed",
                            "failed_checks": sorted(
                                key
                                for key, passed in active["qa"]["checks"].items()
                                if not passed
                            ),
                            "episode_path": active["episode_path"],
                            "rejected_utc": pilot.capture.utc_now(),
                        }
                        append_jsonl(rejected_journal, rejection)
                        return {"pair_id": pair_id, "status": "rejected"}
                else:
                    frozen = captured
            assert active is not None and frozen is not None
            pair = pilot.pair_qa(active, frozen)
            if not pair["passed"]:
                rejection = {
                    "schema_version": "xonotic-stage2-motion-near5-combo-reject-v9",
                    "pair_id": pair_id,
                    "ordinal": int(row["ordinal"]),
                    "role": "pair",
                    "reason": "counterfactual_pair_qa_failed",
                    "failed_checks": sorted(
                        key for key, passed in pair["checks"].items() if not passed
                    ),
                    "active_episode_path": active["episode_path"],
                    "frozen_episode_path": frozen["episode_path"],
                    "rejected_utc": pilot.capture.utc_now(),
                }
                append_jsonl(rejected_journal, rejection)
                return {"pair_id": pair_id, "status": "rejected"}
            record = training_candidate_record(row, active, frozen, pair)
            record_path = shard_root / "records" / f"{pair_id}.json"
            atomic_json(record_path, record)
            journal_row = {
                "pair_id": pair_id,
                "ordinal": int(row["ordinal"]),
                "record_path": str(record_path),
                "record_sha256": pilot.sha256_file(record_path),
                "actual_outcome": record["actual_outcome"],
                "accepted_utc": pilot.capture.utc_now(),
            }
            append_jsonl(accepted_journal, journal_row)
            with accepted_lock:
                accepted_ids.add(pair_id)
                accepted_by_id[pair_id] = journal_row
            return {
                "pair_id": pair_id,
                "status": "accepted",
                "actual_outcome": record["actual_outcome"],
            }
        finally:
            if owns_port:
                port_queue.put(port)

    results: list[dict[str, Any]] = []
    progress_lock = threading.Lock()
    completed_pairs = 0

    def record_progress(result: dict[str, Any]) -> None:
        nonlocal completed_pairs
        with progress_lock:
            results.append(result)
            completed_pairs += 1
            runtime_gpu = (
                gpu_runtime_sample()
                if completed_pairs == 1 or completed_pairs % 25 == 0
                else None
            )
            print(
                canonical_json(
                    {
                        "event": "progress",
                        "completed": completed_pairs,
                        "planned": len(rows),
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

    def append_phase_event(payload: dict[str, Any]) -> None:
        nonlocal phase_sequence
        phase_sequence += 1
        append_jsonl(
            phase_timeline,
            {
                "schema_version": "xonotic-stage2-duel-v8-phase-barrier-v1",
                "sequence": phase_sequence,
                "created_utc": pilot.capture.utc_now(),
                **payload,
            },
        )

    def resident_resume_result(
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        pair_id = str(row["pair_id"])
        with accepted_lock:
            if pair_id not in accepted_ids:
                return None
            if not verify_accepted_record(accepted_by_id[pair_id]):
                raise RuntimeError(
                    f"accepted artifact integrity failed: {pair_id}"
                )
        return {"pair_id": pair_id, "status": "accepted_resume"}

    def archive_resident_pair_attempt(
        item: dict[str, Any], attempt: int, error: str
    ) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        row = item["row"]
        for role, scenario in (
            ("active", row["active_scenario"]),
            ("frozen_qa", row["frozen_scenario"]),
        ):
            episode_id = str(scenario["episode_id"])
            if not (
                (shard_root / "episodes" / episode_id).exists()
                or (scratch_root / episode_id).exists()
            ):
                continue
            diagnostic = archive_partial(
                shard_root,
                scratch_root,
                episode_id,
                attempt,
                error,
            )
            diagnostics.append({"role": role, **diagnostic})
        return diagnostics

    def reject_operational_exhaustion(
        item: dict[str, Any], phase: str, error: Exception
    ) -> dict[str, Any]:
        row = item["row"]
        pair_id = str(row["pair_id"])
        append_jsonl(
            rejected_journal,
            {
                "schema_version": (
                    "xonotic-stage2-motion-near5-combo-reject-v9"
                ),
                "pair_id": pair_id,
                "ordinal": int(row["ordinal"]),
                "role": "pair",
                "reason": "operational_attempts_exhausted",
                "phase": phase,
                "error_type": type(error).__name__,
                "error": str(error),
                "rejected_utc": pilot.capture.utc_now(),
            },
        )
        return {"pair_id": pair_id, "status": "rejected"}

    def record_resident_pair_live_phase(
        item: dict[str, Any], attempt: int
    ) -> dict[str, Any]:
        row = item["row"]
        lane = item["lane"]
        prepared: dict[str, dict[str, Any]] = {}
        for role, scenario in (
            ("active", row["active_scenario"]),
            ("frozen_qa", row["frozen_scenario"]),
        ):
            print(
                canonical_json(
                    {
                        "event": "authoritative_demo_start",
                        "batch_index": item["batch_index"],
                        "pair_id": row["pair_id"],
                        "role": role,
                        "attempt": attempt,
                        "lane_index": item["lane_index"],
                        "resident_generation": item["controller"].generation,
                    }
                ),
                flush=True,
            )
            prepared[role] = pilot.record_episode_live_phase(
                scenario,
                shard_root,
                scratch_root,
                port=item["port"],
                resident_lane=lane,
            )
        return prepared

    def finish_resident_pair_replay_phase(
        item: dict[str, Any],
        attempt: int,
        prepared: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        row = item["row"]
        lane = item["lane"]
        captured: dict[str, dict[str, Any]] = {}
        for role, scenario in (
            ("active", row["active_scenario"]),
            ("frozen_qa", row["frozen_scenario"]),
        ):
            print(
                canonical_json(
                    {
                        "event": "offline_replay_start",
                        "batch_index": item["batch_index"],
                        "pair_id": row["pair_id"],
                        "role": role,
                        "attempt": attempt,
                        "lane_index": item["lane_index"],
                    }
                ),
                flush=True,
            )
            captured[role] = pilot.capture_episode(
                scenario,
                shard_root,
                scratch_root,
                port=item["port"],
                cleanup_scratch=True,
                retain_raw_avi=(
                    bool(row["raw_avi_audit"])
                    if role == "active"
                    else False
                ),
                resident_lane=lane,
                prepared_live_phase=prepared[role],
            )
            failed_checks = {
                key
                for key, passed in captured[role]["qa"]["checks"].items()
                if not passed
            }
            retryable = sorted(
                failed_checks & RETRYABLE_PRE_PAIR_QA_CHECKS
            )
            if retryable:
                raise RuntimeError(
                    "retryable_pre_pair_qa_failed:" + ",".join(retryable)
                )
        return captured

    def finalize_resident_pair(
        item: dict[str, Any], captured: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        row = item["row"]
        pair_id = str(row["pair_id"])
        active = captured["active"]
        frozen = captured["frozen_qa"]
        if not active["qa"]["pre_pair_passed"]:
            append_jsonl(
                rejected_journal,
                {
                    "schema_version": (
                        "xonotic-stage2-motion-near5-combo-reject-v9"
                    ),
                    "pair_id": pair_id,
                    "ordinal": int(row["ordinal"]),
                    "role": "active",
                    "reason": "active_pre_pair_qa_failed",
                    "failed_checks": sorted(
                        key
                        for key, passed in active["qa"]["checks"].items()
                        if not passed
                    ),
                    "episode_path": active["episode_path"],
                    "rejected_utc": pilot.capture.utc_now(),
                },
            )
            return {"pair_id": pair_id, "status": "rejected"}
        pair = pilot.pair_qa(active, frozen)
        if not pair["passed"]:
            append_jsonl(
                rejected_journal,
                {
                    "schema_version": (
                        "xonotic-stage2-motion-near5-combo-reject-v9"
                    ),
                    "pair_id": pair_id,
                    "ordinal": int(row["ordinal"]),
                    "role": "pair",
                    "reason": "counterfactual_pair_qa_failed",
                    "failed_checks": sorted(
                        key
                        for key, passed in pair["checks"].items()
                        if not passed
                    ),
                    "active_episode_path": active["episode_path"],
                    "frozen_episode_path": frozen["episode_path"],
                    "rejected_utc": pilot.capture.utc_now(),
                },
            )
            return {"pair_id": pair_id, "status": "rejected"}
        record = training_candidate_record(row, active, frozen, pair)
        record_path = shard_root / "records" / f"{pair_id}.json"
        atomic_json(record_path, record)
        journal_row = {
            "pair_id": pair_id,
            "ordinal": int(row["ordinal"]),
            "record_path": str(record_path),
            "record_sha256": pilot.sha256_file(record_path),
            "actual_outcome": record["actual_outcome"],
            "accepted_utc": pilot.capture.utc_now(),
        }
        append_jsonl(accepted_journal, journal_row)
        with accepted_lock:
            accepted_ids.add(pair_id)
            accepted_by_id[pair_id] = journal_row
        return {
            "pair_id": pair_id,
            "status": "accepted",
            "actual_outcome": record["actual_outcome"],
        }

    def execute_resident_microbatch(
        batch: list[dict[str, Any]],
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        """Run duel-v8's record-all/barrier/replay-all contract."""
        pending = list(batch)
        attempt_by_pair = {
            str(item["row"]["pair_id"]): 1 for item in pending
        }
        while pending:
            ready: list[dict[str, Any]] = []
            warmup_retry: list[dict[str, Any]] = []
            for item in pending:
                pair_id = str(item["row"]["pair_id"])
                attempt = attempt_by_pair[pair_id]
                try:
                                                                          
                                                                         
                                                                           
                    item["lane"] = item["controller"].get_lane(
                        item["row"]["active_scenario"]
                    )
                    ready.append(item)
                except Exception as exc:
                    item["controller"].invalidate()
                    if attempt >= args.max_operational_attempts:
                        record_progress(
                            reject_operational_exhaustion(
                                item, "serialized_warmup", exc
                            )
                        )
                    else:
                        attempt_by_pair[pair_id] = attempt + 1
                        warmup_retry.append(item)

            live_success: list[tuple[dict[str, Any], dict[str, Any]]] = []
            live_retry: list[dict[str, Any]] = []
            if ready:
                pair_ids = [str(item["row"]["pair_id"]) for item in ready]
                phase_started = time.monotonic()
                append_phase_event(
                    {
                        "event": "authoritative_demo_batch_start",
                        "batch_index": ready[0]["batch_index"],
                        "pair_ids": pair_ids,
                        "pair_count": len(ready),
                        "offline_replay_active": False,
                    }
                )
                future_items = {
                    executor.submit(
                        record_resident_pair_live_phase,
                        item,
                        attempt_by_pair[str(item["row"]["pair_id"])],
                    ): item
                    for item in ready
                }
                for future in concurrent.futures.as_completed(future_items):
                    item = future_items[future]
                    pair_id = str(item["row"]["pair_id"])
                    attempt = attempt_by_pair[pair_id]
                    try:
                        live_success.append((item, future.result()))
                    except Exception as exc:
                        item["controller"].invalidate()
                        diagnostics = archive_resident_pair_attempt(
                            item,
                            attempt,
                            f"{type(exc).__name__}: {exc}",
                        )
                        print(
                            canonical_json(
                                {
                                    "event": "authoritative_demo_retry",
                                    "pair_id": pair_id,
                                    "attempt": attempt,
                                    "error": f"{type(exc).__name__}: {exc}",
                                    "diagnostics": diagnostics,
                                }
                            ),
                            flush=True,
                        )
                        if attempt >= args.max_operational_attempts:
                            record_progress(
                                reject_operational_exhaustion(
                                    item, "authoritative_demo", exc
                                )
                            )
                        else:
                            attempt_by_pair[pair_id] = attempt + 1
                            live_retry.append(item)
                append_phase_event(
                    {
                        "event": "authoritative_demo_batch_complete",
                        "batch_index": ready[0]["batch_index"],
                        "pair_ids": pair_ids,
                        "pair_count": len(ready),
                        "successful_pairs": len(live_success),
                        "wall_seconds": time.monotonic() - phase_started,
                        "offline_replay_active": False,
                    }
                )

            render_retry: list[dict[str, Any]] = []
            if live_success:
                phase_started = time.monotonic()
                pair_ids = [
                    str(item["row"]["pair_id"])
                    for item, _ in live_success
                ]
                append_phase_event(
                    {
                        "event": "global_stage_barrier_passed",
                        "batch_index": live_success[0][0]["batch_index"],
                        "pair_ids": pair_ids,
                        "authoritative_recordings_complete": True,
                    }
                )
                append_phase_event(
                    {
                        "event": "offline_replay_batch_start",
                        "batch_index": live_success[0][0]["batch_index"],
                        "pair_ids": pair_ids,
                        "pair_count": len(live_success),
                        "authoritative_recording_active": False,
                    }
                )
                future_items = {
                    executor.submit(
                        finish_resident_pair_replay_phase,
                        item,
                        attempt_by_pair[str(item["row"]["pair_id"])],
                        prepared,
                    ): item
                    for item, prepared in live_success
                }
                for future in concurrent.futures.as_completed(future_items):
                    item = future_items[future]
                    pair_id = str(item["row"]["pair_id"])
                    attempt = attempt_by_pair[pair_id]
                    try:
                        result = finalize_resident_pair(item, future.result())
                        record_progress(result)
                    except Exception as exc:
                        item["controller"].invalidate()
                        diagnostics = archive_resident_pair_attempt(
                            item,
                            attempt,
                            f"{type(exc).__name__}: {exc}",
                        )
                        print(
                            canonical_json(
                                {
                                    "event": "offline_replay_retry",
                                    "pair_id": pair_id,
                                    "attempt": attempt,
                                    "error": f"{type(exc).__name__}: {exc}",
                                    "diagnostics": diagnostics,
                                }
                            ),
                            flush=True,
                        )
                        if attempt >= args.max_operational_attempts:
                            record_progress(
                                reject_operational_exhaustion(
                                    item, "offline_replay_encode_qa", exc
                                )
                            )
                        else:
                            attempt_by_pair[pair_id] = attempt + 1
                            render_retry.append(item)
                append_phase_event(
                    {
                        "event": "offline_replay_batch_complete",
                        "batch_index": live_success[0][0]["batch_index"],
                        "pair_ids": pair_ids,
                        "pair_count": len(live_success),
                        "wall_seconds": time.monotonic() - phase_started,
                        "authoritative_recording_active": False,
                    }
                )
            pending = warmup_retry + live_retry + render_retry

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        if args.execution_mode == "resident":
            if lane_plans is None:
                raise AssertionError("resident plans missing")
            lane_sequences: list[list[dict[str, Any]]] = []
            for lane_index, groups in enumerate(lane_plans):
                sequence: list[dict[str, Any]] = []
                for group_index, (world_group, group_rows) in enumerate(
                    groups, 1
                ):
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
                lane_sequences.append(sequence)
            controllers: dict[int, Stage2ResidentLaneController] = {}
            try:
                batch_count = max(
                    (len(sequence) for sequence in lane_sequences), default=0
                )
                for batch_index in range(batch_count):
                    batch: list[dict[str, Any]] = []
                    for lane_index, sequence in enumerate(lane_sequences):
                        if batch_index >= len(sequence):
                            continue
                        item = sequence[batch_index]
                        item["batch_index"] = batch_index
                        resumed = resident_resume_result(item["row"])
                        if resumed is not None:
                            record_progress(resumed)
                            continue
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
                        execute_resident_microbatch(batch, executor)
            finally:
                for controller in controllers.values():
                    controller.close()
        else:
            futures = [executor.submit(process_pair, row) for row in rows]
            for future in concurrent.futures.as_completed(futures):
                record_progress(future.result())

    pilot.run_protection_check(shard_root / "STAGE12_POSTCHECK.txt")
    accepted = load_jsonl(accepted_journal)
    rejected = load_jsonl(rejected_journal)
    result = {
        **run_metadata,
        "finished_utc": pilot.capture.utc_now(),
        "accepted_pairs": len({row["pair_id"] for row in accepted}),
        "rejected_records": len(rejected),
        "actual_outcome_distribution": dict(
            sorted(Counter(row["actual_outcome"] for row in accepted).items())
        ),
        "final_gpu_runtime_sample": gpu_runtime_sample(),
        "pass": len({row["pair_id"] for row in accepted}) == len(rows)
        and not rejected,
        "incomplete_is_nonfatal_for_distributed_completion": (
            not args.fail_on_incomplete
        ),
    }
    atomic_json(shard_root / "RUN_RESULT.json", result)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    if args.fail_on_incomplete and not result["pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
