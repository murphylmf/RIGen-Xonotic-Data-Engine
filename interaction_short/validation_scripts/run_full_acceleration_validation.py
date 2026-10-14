                      
"""Validate the isolated Stage-2 full-acceleration production path.

The gate combines two independent tests:

* the already-certified duel-v8 offline-replay equivalence evidence;
* one active/frozen pair for every formal enemy-motion label through eight
  concurrent resident lanes using the same global record/replay barrier,
  including each lane's discarded full-QA warmup.

No episode produced here is training-admitted.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

                                                                             
                                                                            
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BUILD_TAG = "capture-e1b6fef45bc3-aarch64"
SOURCE_COMMIT = "e1b6fef45bc370d36b1f5e3ba04cd1de1d211403"
ACCELERATION_REFERENCE_BUILD_TAG = "capture-f5f692350abd-aarch64"
ACCELERATION_REFERENCE_SOURCE_COMMIT = (
    "f5f692350abd24bf592013a89b4545b755eed9ff"
)
DEFAULT_INPUT = Path(
    "./xonotic_workspace"
    "manifests/stage2_motion_near5_combo_40k_v8_20260817/"
    "shards-008/shard-000-of-008.jsonl"
)
DEFAULT_OUTPUT = ROOT / "outputs/stage2_motion_accel_v1_validation_20260817"
DEFAULT_SCRATCH = Path(
    "./tmp/xonotic_stage2_motion_accel_v1/"
    "stage2_motion_accel_v1_validation_20260817"
)
K1_ROOT = (
    ROOT
    / "outputs/resident_pair_equivalence_seeded_final_k1_20260817/episodes"
)
K4_ROOT = (
    ROOT
    / "outputs/resident_pair_equivalence_seeded_final_k4_a_20260817/episodes"
)
K4_REPEAT_ROOTS = (
    ROOT
    / "outputs/resident_pair_equivalence_seeded_final_k4_b_20260817/episodes",
    ROOT
    / "outputs/resident_pair_equivalence_seeded_final_k4_c_20260817/episodes",
)
EQUIVALENCE_EPISODES = (
    "s2mn5c40v8_000008_active",
    "s2mn5c40v8_000008_frozen_qa",
)
EXACT_EQUIVALENCE_FILES = (
    "scenario.json",
    "prompt.json",
    "raw/actions_requested.csv",
    "raw/server.jsonl",
    "raw/frames_engine.csv",
    "telemetry/actions_requested_64hz.parquet",
    "telemetry/events_64hz.parquet",
    "telemetry/frames_64hz.parquet",
    "telemetry/interaction.json",
    "telemetry/states_64hz.parquet",
    "telemetry/visibility_64hz.parquet",
)


os.environ.setdefault("XONOTIC_CAPTURE_ROOT", str(ROOT))
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG", BUILD_TAG
)
os.environ.setdefault(
    "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT", SOURCE_COMMIT
)
os.environ.setdefault("XONOTIC_BUILD_GLOB", f"build/{BUILD_TAG}")
os.environ.setdefault("XONOTIC_OFFLINE_ACCELERATE", "1")
os.environ.setdefault("XONOTIC_LIVE_TIME_SCALE", "1")
os.environ.setdefault("XONOTIC_ALLOW_LIVE_TIME_SCALE_ONE_VALIDATION", "1")
os.environ.setdefault("XONOTIC_LIVE_CONCURRENCY", "8")
os.environ.setdefault("XONOTIC_RENDER_CONCURRENCY", "8")
os.environ.setdefault("XONOTIC_ENCODE_CONCURRENCY", "8")
os.environ.setdefault("XONOTIC_X264_THREADS", "4")
os.environ.setdefault("XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "240")
os.environ.setdefault("XONOTIC_RENDER_TIMEOUT_SECONDS", "300")
os.environ.setdefault("SDL_VIDEODRIVER", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "opengl")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "production_scripts"))

from pilot_scripts import build_samples as pilot              
import run_stage2_motion_40k_shard as worker              
import xonotic_stage1_reusable as reusable              


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def semantic_csv_equal(
    left: Path, right: Path, ignored_columns: set[str]
) -> bool:
    def normalized(path: Path) -> tuple[tuple[str, ...], list[tuple[str, ...]]]:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise RuntimeError(f"CSV has no header: {path}")
            fields = tuple(
                field for field in reader.fieldnames if field not in ignored_columns
            )
            rows = [tuple(row[field] for field in fields) for row in reader]
        return fields, rows

    return normalized(left) == normalized(right)


def media_video_metrics(left: Path, right: Path) -> dict[str, float]:
    metrics: dict[str, float] = {}
    commands = {
        "psnr_average_db": (
            "psnr",
            re.compile(r"PSNR .* average:([0-9.]+)"),
        ),
        "ssim_all": (
            "ssim",
            re.compile(r"SSIM .* All:([0-9.]+)"),
        ),
    }
    for name, (filter_name, pattern) in commands.items():
        completed = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "info",
                "-i",
                str(left),
                "-i",
                str(right),
                "-lavfi",
                f"[0:v:0][1:v:0]{filter_name}",
                "-an",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        match = pattern.search(completed.stdout + completed.stderr)
        if match is None:
            raise RuntimeError(f"missing {filter_name} result")
        metrics[name] = float(match.group(1))
    return metrics


def decode_audio(path: Path) -> np.ndarray:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(completed.stdout, dtype="<i2").astype(np.float64)


def media_audio_metrics(left: Path, right: Path) -> dict[str, float | int]:
    x = decode_audio(left)
    y = decode_audio(right)
    sample_count_delta = abs(len(x) - len(y))
    sample_count = min(len(x), len(y))
    x = x[:sample_count]
    y = y[:sample_count]
    delta = x - y
    signal = float(np.mean(x * x))
    noise = float(np.mean(delta * delta))
    return {
        "sample_count": sample_count,
        "sample_count_delta": sample_count_delta,
        "maximum_absolute_delta": int(np.max(np.abs(delta))),
        "rms_delta": float(np.sqrt(noise)),
        "snr_db": float(10.0 * np.log10(signal / noise)) if noise else 999.0,
        "correlation": float(np.corrcoef(x, y)[0, 1]),
    }


def compare_episode_roots(left_root: Path, right_root: Path) -> dict[str, Any]:
    episodes: dict[str, Any] = {}
    for episode_id in EQUIVALENCE_EPISODES:
        left = left_root / episode_id
        right = right_root / episode_id
        exact = {
            relative: (
                sha256_file(left / relative) == sha256_file(right / relative)
            )
            for relative in EXACT_EQUIVALENCE_FILES
        }
        source_left = left / "media/source_64hz.mkv"
        source_right = right / "media/source_64hz.mkv"
        episodes[episode_id] = {
            "exact_files": exact,
            "exact_files_passed": all(exact.values()),
            "actions_engine_semantic_equal": semantic_csv_equal(
                left / "raw/actions_engine.csv",
                right / "raw/actions_engine.csv",
                {"cmd_sequence", "cmd_time"},
            ),
            "audio_events_semantic_equal": semantic_csv_equal(
                left / "raw/audio_events_engine.csv",
                right / "raw/audio_events_engine.csv",
                {"source_entity"},
            ),
            "video": media_video_metrics(source_left, source_right),
            "audio": media_audio_metrics(source_left, source_right),
        }
    return {"episodes": episodes}


def equivalence_gate() -> dict[str, Any]:
    evidence_roots = (K1_ROOT, K4_ROOT, *K4_REPEAT_ROOTS)
    evidence_summaries: dict[str, Any] = {}
    for root in evidence_roots:
        if not root.is_dir():
            raise RuntimeError(f"missing equivalence evidence root: {root}")
        summary_path = root.parent / "SUMMARY.json"
        if not summary_path.is_file():
            raise RuntimeError(
                f"missing equivalence evidence summary: {summary_path}"
            )
        evidence_summaries[root.parent.name] = json.loads(
            summary_path.read_text()
        )
    accelerated = compare_episode_roots(K1_ROOT, K4_ROOT)
    repeats = {
        root.parent.name: compare_episode_roots(K4_ROOT, root)
        for root in K4_REPEAT_ROOTS
    }
    checks: dict[str, bool] = {}
    for evidence_name, summary in evidence_summaries.items():
        checks[f"{evidence_name}:canary_passed"] = summary.get("passed") is True
        checks[f"{evidence_name}:build_tag"] = (
            summary.get("build_tag") == ACCELERATION_REFERENCE_BUILD_TAG
        )
        checks[f"{evidence_name}:source_commit"] = (
            summary.get("source_commit")
            == ACCELERATION_REFERENCE_SOURCE_COMMIT
        )
    drift_envelope: dict[str, Any] = {}
    for episode_id in EQUIVALENCE_EPISODES:
        actual = accelerated["episodes"][episode_id]
        controls = [
            repeat["episodes"][episode_id] for repeat in repeats.values()
        ]
        minimum_repeat_ssim = min(
            control["video"]["ssim_all"] for control in controls
        )
        minimum_repeat_psnr = min(
            control["video"]["psnr_average_db"] for control in controls
        )
        minimum_repeat_audio_correlation = min(
            control["audio"]["correlation"] for control in controls
        )
        drift_envelope[episode_id] = {
            "minimum_repeat_video_ssim": minimum_repeat_ssim,
            "minimum_repeat_video_psnr_db": minimum_repeat_psnr,
            "minimum_repeat_audio_correlation": (
                minimum_repeat_audio_correlation
            ),
            "repeat_count": len(controls),
        }
        checks[f"{episode_id}:authoritative_exact"] = actual[
            "exact_files_passed"
        ]
        checks[f"{episode_id}:actions_semantic_exact"] = actual[
            "actions_engine_semantic_equal"
        ]
        checks[f"{episode_id}:audio_events_semantic_exact"] = actual[
            "audio_events_semantic_equal"
        ]
        checks[f"{episode_id}:video_ssim_within_repeat_drift"] = (
            actual["video"]["ssim_all"]
            >= minimum_repeat_ssim - 0.002
            and actual["video"]["ssim_all"] >= 0.98
        )
        checks[f"{episode_id}:video_psnr_within_repeat_drift"] = (
            actual["video"]["psnr_average_db"]
            >= minimum_repeat_psnr - 1.25
            and actual["video"]["psnr_average_db"] >= 39.0
        )
        checks[f"{episode_id}:audio_within_repeat_drift"] = (
            actual["audio"]["correlation"]
            >= minimum_repeat_audio_correlation - 0.002
            and actual["audio"]["correlation"] >= 0.985
        )
        for repeat_name, repeat in repeats.items():
            control = repeat["episodes"][episode_id]
            prefix = f"{episode_id}:{repeat_name}"
            checks[f"{prefix}:authoritative_exact"] = control[
                "exact_files_passed"
            ]
            checks[f"{prefix}:actions_semantic_exact"] = control[
                "actions_engine_semantic_equal"
            ]
            checks[f"{prefix}:audio_events_semantic_exact"] = control[
                "audio_events_semantic_equal"
            ]
    return {
        "schema_version": "xonotic-stage2-full-accel-equivalence-v2",
        "k1_root": str(K1_ROOT),
        "k4_root": str(K4_ROOT),
        "k4_repeat_roots": [str(root) for root in K4_REPEAT_ROOTS],
        "evidence_summaries": evidence_summaries,
        "ignored_ephemeral_fields": {
            "actions_engine.csv": ["cmd_sequence", "cmd_time"],
            "audio_events_engine.csv": ["source_entity"],
        },
        "accelerated_vs_realtime": accelerated,
        "accelerated_repeat_controls": repeats,
        "repeat_drift_envelope": drift_envelope,
        "checks": checks,
        "passed": all(checks.values()),
    }


def select_motion_rows(path: Path) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            motion = row["active_scenario"]["formal_design"][
                "target_motion_name"
            ]
            if motion in pilot.MOTION_LABELS and motion not in selected:
                selected[motion] = row
            if set(selected) == set(pilot.MOTION_LABELS):
                break
    if set(selected) != set(pilot.MOTION_LABELS):
        raise RuntimeError(
            "input does not cover all motion labels: "
            f"missing={sorted(set(pilot.MOTION_LABELS) - set(selected))}"
        )
    rows = [copy.deepcopy(selected[motion]) for motion in pilot.MOTION_LABELS]
    for row in rows:
        for scenario in (row["active_scenario"], row["frozen_scenario"]):
            trace = scenario.get("prefrozen_trace_source") or None
            if trace is not None:
                original_source_commit = str(trace.get("source_commit", ""))
                trace["source_commit"] = SOURCE_COMMIT
                trace["runtime_recertification"] = {
                    "schema_version": (
                        "xonotic-stage2-prefrozen-trace-runtime-"
                        "recertification-v1"
                    ),
                    "original_source_commit": original_source_commit,
                    "runtime_source_commit": SOURCE_COMMIT,
                    "method": (
                        "replay_immutable_actions_and_fail_closed_compare_"
                        "live_player_positions_to_immutable_reference_states"
                    ),
                    "live_fail_closed": True,
                    "runtime_action_fallback": False,
                    "runtime_geometry_fallback": False,
                }
                scenario["prefrozen_trace_runtime_recertification"] = (
                    copy.deepcopy(trace["runtime_recertification"])
                )
            scenario["source_commit_required"] = SOURCE_COMMIT
            scenario["formal_collection_authorized"] = False
            scenario["formal_authorization_basis"] = (
                "isolated_full_acceleration_validation_only"
            )
            scenario["training_admitted"] = False
    return rows


def eight_lane_plans(
    rows: list[dict[str, Any]], workers: int
) -> list[list[tuple[tuple[str, str], list[dict[str, Any]]]]]:
    plans: list[list[tuple[tuple[str, str], list[dict[str, Any]]]]] = [
        [] for _ in range(workers)
    ]
    for index, row in enumerate(rows):
        scenario = row["active_scenario"]
        group = (
            str(scenario["map"]),
            str(scenario.get("gametype", "dm")).lower(),
        )
        plans[index % workers].append((group, [row]))
    return plans


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--port-base", type=int, default=29700)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be in [1,16]")
    if reusable.configured_live_time_scale() != 1:
        raise RuntimeError(
            "duel-v8 acceleration validation requires native 1x demo time"
        )
    cpu_isolation = reusable.configure_resident_cpu_isolation(
        args.workers,
        requested_x264_cpuset=os.environ.get("XONOTIC_X264_CPUSET", ""),
    )
    output_root = args.output_root.resolve()
    scratch_root = args.scratch_root.resolve()
    if output_root.exists():
        raise RuntimeError(f"refusing to overwrite validation: {output_root}")
    output_root.mkdir(parents=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    rows = select_motion_rows(args.input_jsonl.resolve())
    workers = min(args.workers, len(rows))
    plans = eight_lane_plans(rows, workers)
    pilot.run_protection_check(output_root / "STAGE12_PRECHECK.txt")
    equivalence = equivalence_gate()
    worker.atomic_json(output_root / "EQUIVALENCE.json", equivalence)
    started = time.monotonic()

    lane_sequences: list[list[dict[str, Any]]] = []
    for lane_index, groups in enumerate(plans):
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
        lane_sequences.append(sequence)

    phase_timeline: list[dict[str, Any]] = []

    def record_batch_item(item: dict[str, Any]) -> dict[str, Any]:
        row = item["row"]
        prepared: dict[str, dict[str, Any]] = {}
        for role, scenario in (
            ("active", row["active_scenario"]),
            ("frozen", row["frozen_scenario"]),
        ):
            prepared[role] = pilot.record_episode_live_phase(
                scenario,
                output_root,
                scratch_root,
                port=item["port"],
                resident_lane=item["lane"],
            )
        return prepared

    def replay_batch_item(
        item: dict[str, Any], prepared: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        row = item["row"]
        captured: dict[str, dict[str, Any]] = {}
        attempt_records: list[dict[str, Any]] = []
        for role, scenario in (
            ("active", row["active_scenario"]),
            ("frozen", row["frozen_scenario"]),
        ):
            captured[role] = pilot.capture_episode(
                scenario,
                output_root,
                scratch_root,
                port=item["port"],
                cleanup_scratch=True,
                retain_raw_avi=False,
                resident_lane=item["lane"],
                prepared_live_phase=prepared[role],
            )
            failed_checks = sorted(
                key
                for key, passed in captured[role]["qa"]["checks"].items()
                if not passed
            )
            if failed_checks:
                raise RuntimeError(
                    "pre_pair_qa_failed:" + ",".join(failed_checks)
                )
            attempt_records.append(
                {
                    "role": role,
                    "episode_id": str(scenario["episode_id"]),
                    "attempt": 1,
                    "status": "accepted",
                    "lane_index": item["lane_index"],
                    "group_index": item["group_index"],
                    "resident_generation": item["controller"].generation,
                }
            )
        pair = pilot.pair_qa(captured["active"], captured["frozen"])
        return {
            "pair_id": row["pair_id"],
            "ordinal": int(row["ordinal"]),
            "motion": row["active_scenario"]["formal_design"][
                "target_motion_name"
            ],
            "active": captured["active"],
            "frozen": captured["frozen"],
            "pair": pair,
            "attempt_records": attempt_records,
        }

    completed: list[dict[str, Any]] = []
    controllers: dict[int, worker.Stage2ResidentLaneController] = {}
    try:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=workers
        ) as executor:
            batch_count = max(
                (len(sequence) for sequence in lane_sequences), default=0
            )
            for batch_index in range(batch_count):
                batch: list[dict[str, Any]] = []
                                                                             
                                                                               
                                                                          
                for lane_index, sequence in enumerate(lane_sequences):
                    if batch_index >= len(sequence):
                        continue
                    item = sequence[batch_index]
                    controller = controllers.get(lane_index)
                    if controller is not None and (
                        controller.group_index != item["group_index"]
                        or controller.world_group != item["world_group"]
                    ):
                        controller.close()
                        controller = None
                    if controller is None:
                        controller = worker.Stage2ResidentLaneController(
                            lane_index=lane_index,
                            group_index=item["group_index"],
                            world_group=item["world_group"],
                            port=item["port"],
                            build=pilot.capture.build_root(),
                            shard_root=output_root,
                            scratch_root=scratch_root,
                        )
                        controllers[lane_index] = controller
                    item["controller"] = controller
                    item["lane"] = controller.get_lane(
                        item["row"]["active_scenario"]
                    )
                    batch.append(item)

                live_started = time.monotonic()
                phase_timeline.append(
                    {
                        "batch_index": batch_index,
                        "phase": "authoritative_demo_batch",
                        "event": "start",
                        "monotonic_seconds": live_started,
                        "pair_ids": [item["row"]["pair_id"] for item in batch],
                    }
                )
                live_futures = {
                    executor.submit(record_batch_item, item): item
                    for item in batch
                }
                prepared_by_pair: dict[str, dict[str, dict[str, Any]]] = {}
                for future in concurrent.futures.as_completed(live_futures):
                    item = live_futures[future]
                    prepared_by_pair[str(item["row"]["pair_id"])] = (
                        future.result()
                    )
                live_finished = time.monotonic()
                phase_timeline.append(
                    {
                        "batch_index": batch_index,
                        "phase": "authoritative_demo_batch",
                        "event": "complete",
                        "monotonic_seconds": live_finished,
                        "wall_seconds": live_finished - live_started,
                        "pair_ids": [item["row"]["pair_id"] for item in batch],
                    }
                )
                phase_timeline.append(
                    {
                        "batch_index": batch_index,
                        "phase": "global_barrier",
                        "event": "passed",
                        "monotonic_seconds": time.monotonic(),
                        "all_authoritative_recordings_complete": True,
                    }
                )

                replay_started = time.monotonic()
                phase_timeline.append(
                    {
                        "batch_index": batch_index,
                        "phase": "offline_replay_encode_qa_batch",
                        "event": "start",
                        "monotonic_seconds": replay_started,
                        "pair_ids": [item["row"]["pair_id"] for item in batch],
                    }
                )
                replay_futures = {
                    executor.submit(
                        replay_batch_item,
                        item,
                        prepared_by_pair[str(item["row"]["pair_id"])],
                    ): item
                    for item in batch
                }
                for future in concurrent.futures.as_completed(replay_futures):
                    completed.append(future.result())
                replay_finished = time.monotonic()
                phase_timeline.append(
                    {
                        "batch_index": batch_index,
                        "phase": "offline_replay_encode_qa_batch",
                        "event": "complete",
                        "monotonic_seconds": replay_finished,
                        "wall_seconds": replay_finished - replay_started,
                        "pair_ids": [item["row"]["pair_id"] for item in batch],
                    }
                )
    finally:
        for controller in controllers.values():
            controller.close()
    worker.atomic_json(output_root / "PHASE_TIMELINE.json", phase_timeline)
    wall_seconds = time.monotonic() - started
    pilot.run_protection_check(output_root / "STAGE12_POSTCHECK.txt")
    completed.sort(key=lambda row: row["ordinal"])
    warmups = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((output_root / "resident_warmups").rglob("RESULT.json"))
    ]
    warmup_failures = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(
            (output_root / "resident_warmups").rglob("FAILURE.json")
        )
    ]
    successful_warmup_keys = {
        (
            int(row["lane_index"]),
            int(row["group_index"]),
            int(row["generation"]),
        )
        for row in warmups
        if row["passed"] is True
    }
    admitted_generation_keys = {
        (
            int(attempt["lane_index"]),
            int(attempt["group_index"]),
            int(attempt["resident_generation"]),
        )
        for row in completed
        for attempt in row["attempt_records"]
        if attempt["status"] == "accepted"
    }
    episode_checks: dict[str, bool] = {}
    for row in completed:
        for role in ("active", "frozen"):
            qa = row[role]["qa"]
            runtime = qa["runtime"]
            resident = runtime["resident_lane"]
            prefix = f"{row['pair_id']}:{role}"
            episode_checks[f"{prefix}:full_qa"] = qa["pre_pair_passed"] is True
            episode_checks[f"{prefix}:offline_render"] = (
                runtime["offline_accelerate"] is True
                and runtime["capturevideo_realtime"] is False
                and abs(float(runtime["effective_demo_timescale"]) - 1.0)
                <= 1e-12
            )
            episode_checks[f"{prefix}:duel_v8_authoritative_clock"] = (
                runtime["live_time_scale"] == 1
                and abs(float(runtime["live_server_ticrate"]) - 1.0 / 64.0)
                <= 1e-12
                and runtime["live_netfps"] == 64
            )
            episode_checks[f"{prefix}:low_cost_live"] = (
                runtime["live_capture_geometry"]
                == {
                    "width": 160,
                    "height": 90,
                    "r_renderview": False,
                    "scr_refresh": False,
                }
            )
            episode_checks[f"{prefix}:isolated_render_generation"] = (
                resident["render_process_recycled_after_episode"] is True
                and resident["render_generation"] is not None
            )
            episode_checks[f"{prefix}:idle_server_throttled"] = (
                resident["server_idle_throttle_verified"] is True
                and abs(
                    float(resident["server_idle_ticrate"])
                    - reusable.IDLE_SERVER_TICRATE
                )
                <= 1e-12
                and float(resident["server_idle_slowmo"])
                == reusable.IDLE_SERVER_SLOWMO
            )
            reserved_cpus = set(resident["reserved_live_cpus"])
            background_cpus = set(resident["background_cpus"])
            server_scheduling = resident["server_cpu_scheduling"]
            live_scheduling = resident["live_client_cpu_scheduling"]
            render_scheduling = resident[
                "render_client_cpu_scheduling"
            ]
            lane_index = int(resident["live_cpu_slot"])
            reserved_cpu_list = sorted(reserved_cpus)
            expected_server_cpu = [reserved_cpu_list[lane_index * 2]]
            expected_live_cpu = [reserved_cpu_list[lane_index * 2 + 1]]
            x264_cpus = pilot.capture.parse_cpu_list(
                str(runtime["x264_cpuset"])
            )
            episode_checks[f"{prefix}:cpu_isolation"] = (
                resident["cpu_isolation_enabled"] is True
                and lane_index * 2 + 1 < len(reserved_cpus)
                and bool(background_cpus)
                and not reserved_cpus & background_cpus
                and server_scheduling["all_threads_match"] is True
                and live_scheduling["all_threads_match"] is True
                and render_scheduling["all_threads_match"] is True
                and server_scheduling["expected_cpu_affinity"]
                == expected_server_cpu
                and live_scheduling["expected_cpu_affinity"]
                == expected_live_cpu
                and render_scheduling["expected_cpu_affinity"]
                == sorted(background_cpus)
                and bool(x264_cpus)
                and x264_cpus <= background_cpus
                and not x264_cpus & reserved_cpus
            )
        episode_checks[f"{row['pair_id']}:pair_qa"] = row["pair"][
            "passed"
        ] is True
    motion_distribution = Counter(row["motion"] for row in completed)
    phase_barrier_checks: dict[str, bool] = {}
    batch_indexes = sorted(
        {
            int(event["batch_index"])
            for event in phase_timeline
            if "batch_index" in event
        }
    )
    for batch_index in batch_indexes:
        events = [
            event
            for event in phase_timeline
            if event.get("batch_index") == batch_index
        ]
        live_complete = next(
            event
            for event in events
            if event.get("phase") == "authoritative_demo_batch"
            and event.get("event") == "complete"
        )
        barrier = next(
            event
            for event in events
            if event.get("phase") == "global_barrier"
            and event.get("event") == "passed"
        )
        replay_start = next(
            event
            for event in events
            if event.get("phase") == "offline_replay_encode_qa_batch"
            and event.get("event") == "start"
        )
        phase_barrier_checks[f"batch_{batch_index:03d}"] = (
            bool(barrier["all_authoritative_recordings_complete"])
            and float(live_complete["monotonic_seconds"])
            <= float(barrier["monotonic_seconds"])
            <= float(replay_start["monotonic_seconds"])
        )
    acceleration_checks = {
        "equivalence_passed": equivalence["passed"] is True,
        "all_episode_and_pair_checks": all(episode_checks.values()),
        "all_motion_classes": set(motion_distribution)
        == set(pilot.MOTION_LABELS),
        "nine_active_pairs": len(completed) == 9,
        "eight_lane_stress": workers == 8,
        "duel_v8_global_phase_barrier": bool(phase_barrier_checks)
        and all(phase_barrier_checks.values()),
        "warmup_recovery_within_operational_budget": (
            len(successful_warmup_keys) >= len(rows)
            and admitted_generation_keys <= successful_warmup_keys
            and all(
                any(
                    attempt["status"] == "accepted"
                    for attempt in row["attempt_records"]
                )
                for row in completed
            )
        ),
        "zero_discarded_warmup_failures": len(warmup_failures) == 0,
        "zero_operational_retries": all(
            len(row["attempt_records"]) == 2
            and all(
                attempt["status"] == "accepted"
                and attempt["attempt"] == 1
                for attempt in row["attempt_records"]
            )
            for row in completed
        ),
        "resident_cpu_partition_configured": (
            cpu_isolation["enabled"] is True
            and len(cpu_isolation["reserved_live_cpus"]) == workers * 2
            and cpu_isolation["background_threads_verified"] is True
        ),
        "source_build_locked": pilot.BUILD_TAG == BUILD_TAG
        and pilot.SOURCE_COMMIT == SOURCE_COMMIT,
    }
    summary = {
        "schema_version": "xonotic-stage2-full-acceleration-validation-v1",
        "output_root": str(output_root),
        "input_jsonl": str(args.input_jsonl.resolve()),
        "runtime_build": str(pilot.capture.build_root()),
        "runtime_source_commit": SOURCE_COMMIT,
        "build_tag": BUILD_TAG,
        "acceleration_reference_build_tag": (
            ACCELERATION_REFERENCE_BUILD_TAG
        ),
        "acceleration_reference_source_commit": (
            ACCELERATION_REFERENCE_SOURCE_COMMIT
        ),
        "formal_stage1_stage2_runtime_modified": False,
        "stage1_stage2_protection_precheck_passed": True,
        "stage1_stage2_protection_postcheck_passed": True,
        "active_samples": len(completed),
        "counterfactual_samples": len(completed),
        "review_admitted_samples": sum(
            int(
                row["active"]["qa"]["pre_pair_passed"]
                and row["frozen"]["qa"]["pre_pair_passed"]
                and row["pair"]["passed"]
            )
            for row in completed
        ),
        "primary_motion_distribution": dict(sorted(motion_distribution.items())),
        "workers": workers,
        "live_concurrency": pilot.capture.configured_live_concurrency(),
        "render_concurrency": pilot.capture.configured_render_concurrency(),
        "resident_cpu_isolation": cpu_isolation,
        "lane_plan_count": sum(bool(groups) for groups in plans),
        "discarded_warmup_result_count": len(warmups),
        "discarded_warmup_failure_count": len(warmup_failures),
        "warmups": warmups,
        "warmup_failures": warmup_failures,
        "attempt_records": {
            row["pair_id"]: row["attempt_records"] for row in completed
        },
        "phase_timeline_path": str(output_root / "PHASE_TIMELINE.json"),
        "phase_timeline_sha256": sha256_file(
            output_root / "PHASE_TIMELINE.json"
        ),
        "phase_barrier_checks": phase_barrier_checks,
        "authoritative_demo_batch_wall_seconds": sum(
            float(event["wall_seconds"])
            for event in phase_timeline
            if event.get("phase") == "authoritative_demo_batch"
            and event.get("event") == "complete"
        ),
        "offline_replay_encode_qa_batch_wall_seconds": sum(
            float(event["wall_seconds"])
            for event in phase_timeline
            if event.get("phase") == "offline_replay_encode_qa_batch"
            and event.get("event") == "complete"
        ),
        "episode_checks": episode_checks,
        "acceleration_checks": acceleration_checks,
        "full_acceleration_gate_passed": all(acceleration_checks.values()),
        "equivalence_path": str(output_root / "EQUIVALENCE.json"),
        "equivalence_sha256": sha256_file(output_root / "EQUIVALENCE.json"),
        "wall_seconds_including_discarded_warmups": wall_seconds,
        "accepted_pairs_per_card_hour_cold_smoke": (
            len(completed) * 3600.0 / wall_seconds
        ),
        "active_video_hours_per_wall_hour_cold_smoke": (
            len(completed) * 5.0 / wall_seconds
        ),
        "created_utc": pilot.capture.utc_now(),
    }
    worker.atomic_json(output_root / "SUMMARY.json", summary)
    if scratch_root.exists() and not any(scratch_root.iterdir()):
        scratch_root.rmdir()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["full_acceleration_gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
