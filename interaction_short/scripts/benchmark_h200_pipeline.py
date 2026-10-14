                      
"""Benchmark full H200 capture scaling and CPU x264 tuning."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from statistics import mean, median
from typing import Any

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_capture_manifest_shard as shard_runner              
import xonotic_capture as capture              
import xonotic_capture_v2 as v2                   
import xonotic_stage1_review as review                   


SOURCE_COMMIT = "fe8b4e847eff4b95e37f6adad31a2add6ddb746e"
TEMPLATE_IDS = (
    "v2_foundation_solo_01",
    "v2_foundation_enemy_01",
    "v2_causal_02",
    "s1polaudfix_003",
    "s1polaudfix_001",
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def load_templates() -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in (
        capture.ROOT / "configs/v2_coverage_pilot_scenarios.jsonl",
        capture.ROOT
        / "configs/v2_stage1_enemy_policy_audio_preflight_v2_scenarios.jsonl",
    ):
        for row in capture.load_jsonl(path):
            rows[row["episode_id"]] = row
    return [rows[episode_id] for episode_id in TEMPLATE_IDS]


def scenario_rows(
    templates: list[dict[str, Any]],
    label: str,
    count: int,
    waves: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ordinal in range(count * waves):
        row = copy.deepcopy(templates[ordinal % len(templates)])
        old_id = row["episode_id"]
        episode_id = f"h200bench_{label}_{ordinal + 1:03d}"
        row.update(
            {
                "episode_id": episode_id,
                "source_episode_id": old_id,
                "source_split": row["split"],
                "split": "h200_pipeline_benchmark",
                "training_stage": "pipeline_benchmark_only",
                "acceptance_policy": capture.TIERED_REVIEW_POLICY,
                "formal_collection_authorized": False,
                "human_review_required_before_training": True,
                "training_admitted": False,
                "benchmark_label": label,
            }
        )
        row["anchor_id"] = str(row["anchor_id"]).replace(
            old_id, episode_id
        )
        rows.append(row)
    return rows


class RuntimeMonitor:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.phase = "idle"
        self.samples: list[dict[str, Any]] = []
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.cgroup_root = Path("/sys/fs/cgroup")
        self.cpu_quota_cores = self._cpu_quota_cores()

    def _cpu_quota_cores(self) -> float | None:
        try:
            quota, period = (
                self.cgroup_root / "cpu.max"
            ).read_text(encoding="utf-8").split()
            if quota == "max":
                return None
            return float(quota) / float(period)
        except (OSError, ValueError):
            return None

    def _cpu_usage_seconds(self) -> float | None:
        try:
            values = dict(
                line.split()
                for line in (
                    self.cgroup_root / "cpu.stat"
                ).read_text(encoding="utf-8").splitlines()
                if len(line.split()) == 2
            )
            return float(values["usage_usec"]) / 1_000_000.0
        except (KeyError, OSError, ValueError):
            return None

    def _cpu_stat(self) -> dict[str, int]:
        try:
            return {
                key: int(value)
                for key, value in (
                    line.split()
                    for line in (
                        self.cgroup_root / "cpu.stat"
                    ).read_text(encoding="utf-8").splitlines()
                    if len(line.split()) == 2
                )
            }
        except (OSError, ValueError):
            return {}

    def _cgroup_memory(self) -> tuple[int | None, int | None]:
        try:
            current = int(
                (self.cgroup_root / "memory.current").read_text(
                    encoding="utf-8"
                )
            )
            raw_max = (
                self.cgroup_root / "memory.max"
            ).read_text(encoding="utf-8").strip()
            maximum = None if raw_max == "max" else int(raw_max)
            return current, maximum
        except (OSError, ValueError):
            return None, None

    def set_phase(self, phase: str) -> None:
        with self.lock:
            self.phase = phase

    def start(self) -> None:
        psutil.cpu_percent(interval=None)
        self.thread.start()

    def finish(self) -> None:
        self.stop.set()
        self.thread.join(timeout=10)

    def _run(self) -> None:
        previous_monotonic = time.monotonic()
        previous_cpu_usage = self._cpu_usage_seconds()
        previous_cpu_stat = self._cpu_stat()
        while not self.stop.wait(0.25):
            with self.lock:
                phase = self.phase
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            gpu = memory = power = 0.0
            if completed.returncode == 0 and completed.stdout.strip():
                fields = completed.stdout.splitlines()[0].split(",")
                gpu, memory, power = (
                    float(field.strip()) for field in fields[:3]
                )
            sampled_monotonic = time.monotonic()
            cpu_usage = self._cpu_usage_seconds()
            cpu_stat = self._cpu_stat()
            cpu_cores_used = None
            cpu_quota_percent = None
            throttle_period_fraction = None
            throttled_seconds_delta = None
            if cpu_usage is not None and previous_cpu_usage is not None:
                elapsed = sampled_monotonic - previous_monotonic
                if elapsed > 0:
                    cpu_cores_used = (
                        cpu_usage - previous_cpu_usage
                    ) / elapsed
                    if self.cpu_quota_cores:
                        cpu_quota_percent = (
                            100.0
                            * cpu_cores_used
                            / self.cpu_quota_cores
                        )
            period_delta = (
                cpu_stat.get("nr_periods", 0)
                - previous_cpu_stat.get("nr_periods", 0)
            )
            throttled_delta = (
                cpu_stat.get("nr_throttled", 0)
                - previous_cpu_stat.get("nr_throttled", 0)
            )
            if period_delta > 0:
                throttle_period_fraction = (
                    throttled_delta / period_delta
                )
            if (
                "throttled_usec" in cpu_stat
                and "throttled_usec" in previous_cpu_stat
            ):
                throttled_seconds_delta = (
                    cpu_stat["throttled_usec"]
                    - previous_cpu_stat["throttled_usec"]
                ) / 1_000_000.0
            memory_current, memory_max = self._cgroup_memory()
            self.samples.append(
                {
                    "monotonic_seconds": sampled_monotonic,
                    "phase": phase,
                    "gpu_util_percent": gpu,
                    "gpu_memory_mib": memory,
                    "gpu_power_w": power,
                    "host_cpu_percent": psutil.cpu_percent(interval=None),
                    "host_memory_percent": psutil.virtual_memory().percent,
                    "cgroup_cpu_cores_used": cpu_cores_used,
                    "cgroup_cpu_quota_cores": self.cpu_quota_cores,
                    "cgroup_cpu_quota_percent": cpu_quota_percent,
                    "cgroup_throttle_period_fraction": (
                        throttle_period_fraction
                    ),
                    "cgroup_throttled_seconds_delta": (
                        throttled_seconds_delta
                    ),
                    "cgroup_memory_current_mib": (
                        memory_current / (1024 * 1024)
                        if memory_current is not None
                        else None
                    ),
                    "cgroup_memory_max_mib": (
                        memory_max / (1024 * 1024)
                        if memory_max is not None
                        else None
                    ),
                }
            )
            previous_monotonic = sampled_monotonic
            previous_cpu_usage = cpu_usage
            previous_cpu_stat = cpu_stat


def publish_benchmark_stage(
    stage: Path,
    destination: Path,
    attempt_id: str,
) -> dict[str, Any]:
    package = stage / "package"
    episode_destination = destination / "episode"
    raw_destination = destination / "raw"
    destination.mkdir(parents=True, exist_ok=False)
    package_tmp, package_hashes, package_bytes, package_seconds = (
        shard_runner.stage_files(
            shard_runner.tree_files(package),
            episode_destination,
            attempt_id,
        )
    )
    raw_tmp, raw_hashes, raw_bytes, raw_seconds = shard_runner.stage_files(
        shard_runner.raw_files(stage), raw_destination, attempt_id
    )
    os.rename(raw_tmp, raw_destination)
    os.rename(package_tmp, episode_destination)
    return {
        "episode_path": str(episode_destination),
        "raw_path": str(raw_destination),
        "package_sha256": package_hashes,
        "raw_sha256": raw_hashes,
        "package_bytes": package_bytes,
        "raw_bytes": raw_bytes,
        "package_copy_seconds": package_seconds,
        "raw_copy_seconds": raw_seconds,
    }


def run_one(
    row: dict[str, Any],
    port: int,
    destination_root: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    result: dict[str, Any] | None = None
    attempt_failures: list[dict[str, Any]] = []
    for retry in range(2):
        try:
            result = capture.execute_attempt(
                row,
                retry=retry,
                publish=False,
                port=port,
            )
            break
        except Exception as exc:
            attempt_failures.append(
                {
                    "attempt_id": (
                        f"{row['episode_id']}_a{retry + 1:02d}"
                    ),
                    "failure_type": type(exc).__name__,
                    "reason": (
                        exc.reason
                        if isinstance(exc, capture.CaptureFailure)
                        else type(exc).__name__
                    ),
                    "detail": str(exc),
                    "retryable": shard_runner.retryable_failure(exc),
                }
            )
            stage = (
                capture.TMP_ROOT
                / "raw"
                / f"{row['episode_id']}_a{retry + 1:02d}"
            )
            if stage.is_dir():
                diagnostic = (
                    destination_root
                    / "diagnostics"
                    / f"{row['episode_id']}_a{retry + 1:02d}"
                )
                temporary, _, _, _ = shard_runner.stage_files(
                    shard_runner.raw_files(stage),
                    diagnostic,
                    f"{row['episode_id']}_a{retry + 1:02d}",
                )
                os.rename(temporary, diagnostic)
                capture.clean_stage(stage)
            if retry or not shard_runner.retryable_failure(exc):
                raise
    if result is None:
        raise AssertionError("unreachable")
    result = shard_runner.complete_v2_artifacts(result, row)
    stage = Path(result["stage"])
    qa = result["qa"]
    publication = publish_benchmark_stage(
        stage,
        destination_root / row["episode_id"],
        result["attempt_id"],
    )
    wall = time.monotonic() - started
    output = {
        "episode_id": row["episode_id"],
        "source_episode_id": row["source_episode_id"],
        "attempt_id": result["attempt_id"],
        "stage": str(stage),
        "wall_seconds": wall,
        "attempt_failures": attempt_failures,
        "qa": qa,
        "publication": publication,
    }
    atomic_json(
        destination_root / row["episode_id"] / "benchmark_result.json",
        {key: value for key, value in output.items() if key != "qa"},
    )
    return output


def run_one_with_port(
    row: dict[str, Any],
    port_pool: queue.Queue[int],
    destination_root: Path,
) -> dict[str, Any]:
    port = port_pool.get()
    try:
        return run_one(row, port, destination_root)
    finally:
        port_pool.put(port)


def summarize_batch(
    label: str,
    workers: int,
    rows: list[dict[str, Any]],
    results: list[dict[str, Any]],
    wall_seconds: float,
    live_concurrency: int,
    render_concurrency: int,
    sdl_concurrency: int,
    x264_threads: int,
    encode_concurrency: int,
) -> dict[str, Any]:
    runtimes = [row["qa"]["runtime"] for row in results]
    return {
        "schema_version": "xonotic-h200-e2e-benchmark-v1",
        "label": label,
        "workers": workers,
        "live_limit": live_concurrency,
        "renderer_limit": render_concurrency,
        "sdl_client_limit": sdl_concurrency,
        "episodes": len(results),
        "waves": len(rows) / workers,
        "x264_threads": x264_threads,
        "encode_concurrency": encode_concurrency,
        "operational_retries": sum(
            int(row["attempt_id"].rsplit("_a", 1)[1]) - 1
            for row in results
        ),
        "attempt_failures": [
            failure
            for row in results
            for failure in row.get("attempt_failures", [])
        ],
        "batch_wall_seconds": wall_seconds,
        "episodes_per_hour": len(results) * 3600.0 / wall_seconds,
        "video_seconds_per_wall_second": (
            len(results) * 5.0 / wall_seconds
        ),
        "individual_wall_seconds": [row["wall_seconds"] for row in results],
        "live_wall_seconds": [
            row["live_wall_seconds"] for row in runtimes
        ],
        "live_queue_wait_seconds": [
            row.get("live_queue_wait_seconds", 0.0)
            for row in runtimes
        ],
        "live_sdl_queue_wait_seconds": [
            row.get("live_sdl_queue_wait_seconds", 0.0)
            for row in runtimes
        ],
        "render_wall_seconds": [
            row["render_wall_seconds"] for row in runtimes
        ],
        "render_queue_wait_seconds": [
            row.get("render_queue_wait_seconds", 0.0)
            for row in runtimes
        ],
        "render_sdl_queue_wait_seconds": [
            row.get("render_sdl_queue_wait_seconds", 0.0)
            for row in runtimes
        ],
        "encode_wall_seconds": [
            row["encode_wall_seconds"] for row in runtimes
        ],
        "encode_queue_wait_seconds": [
            row.get("encode_queue_wait_seconds", 0.0) for row in runtimes
        ],
        "renderer": sorted(
            {row["renderer"] for row in runtimes}
        ),
        "hard_qa_pass": all(
            all(row["qa"]["hard_gates"].values()) for row in results
        ),
        "frames_exact": all(
            row["qa"]["video"]["frames"] == capture.OUTPUT_TICKS
            for row in results
        ),
        "audio_exact": all(
            row["qa"]["audio"]["samples_per_channel"]
            == capture.AUDIO_SAMPLES
            for row in results
        ),
        "mapping_min": min(
            row["qa"]["mapping"]["success_rate"] for row in results
        ),
        "published_bytes": sum(
            row["publication"]["package_bytes"]
            + row["publication"]["raw_bytes"]
            for row in results
        ),
    }


def run_batch(
    output_root: Path,
    monitor: RuntimeMonitor,
    templates: list[dict[str, Any]],
    label: str,
    workers: int,
    waves: int,
    live_concurrency: int,
    render_concurrency: int,
    sdl_concurrency: int,
    x264_threads: int,
    encode_concurrency: int,
    port_base: int,
    episode_count: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = scenario_rows(templates, label, workers, waves)
    if episode_count is not None:
        rows = scenario_rows(templates, label, episode_count, 1)
    destination = output_root / "full_pipeline" / label
    if destination.exists():
        raise RuntimeError(f"refuse overwrite: {destination}")
    destination.mkdir(parents=True)
    os.environ["XONOTIC_X264_THREADS"] = str(x264_threads)
    os.environ["XONOTIC_LIVE_CONCURRENCY"] = str(live_concurrency)
    os.environ["XONOTIC_RENDER_CONCURRENCY"] = str(
        render_concurrency
    )
    os.environ["XONOTIC_SDL_CONCURRENCY"] = str(sdl_concurrency)
    os.environ["XONOTIC_ENCODE_CONCURRENCY"] = str(encode_concurrency)
    monitor.set_phase(f"full:{label}")
    started = time.monotonic()
    port_pool: queue.Queue[int] = queue.Queue()
    for port in range(port_base, port_base + workers):
        port_pool.put(port)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        futures = [
            executor.submit(
                run_one_with_port,
                row,
                port_pool,
                destination,
            )
            for row in rows
        ]
        results = [future.result() for future in futures]
    wall = time.monotonic() - started
    summary = summarize_batch(
        label,
        workers,
        rows,
        results,
        wall,
        live_concurrency,
        render_concurrency,
        sdl_concurrency,
        x264_threads,
        encode_concurrency,
    )
    atomic_json(destination / "result.json", summary)
    print(
        f"full {label} workers={workers} episodes={len(results)} "
        f"eps_h={summary['episodes_per_hour']:.2f}",
        flush=True,
    )
    return summary, results


def audio_start(raw_result: dict[str, Any]) -> int:
    path = Path(raw_result["stage"]) / "render/frames_engine.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    return int(row["mixer_audio_cursor_at_frame"])


def encode_one(
    raw_result: dict[str, Any],
    output: Path,
    threads: int,
) -> float:
    raw_matches = sorted(
        Path(raw_result["stage"]).glob("client_user/data/video/*.avi")
    )
    if len(raw_matches) != 1:
        raise RuntimeError(f"raw AVI count: {len(raw_matches)}")
    raw = raw_matches[0]
    wall = capture.encode_video(
        raw,
        output,
        output.with_suffix(".log"),
        audio_start(raw_result),
        x264_threads=threads,
    )
    probe = capture.ffprobe_json(output, count_frames=True)
    contract = capture.encoded_contract(probe, output)
    contract["encoded_frames_exact"] = (
        capture.count_video_frames(probe) == capture.OUTPUT_TICKS
    )
    contract["encoded_audio_samples_exact"] = (
        capture.decode_audio_s16(output).shape[0] == capture.AUDIO_SAMPLES
    )
    if not all(contract.values()):
        raise RuntimeError(f"encode contract failed: {contract}")
    output.unlink()
    return wall


def encode_grid(
    output_root: Path,
    monitor: RuntimeMonitor,
    sources: list[dict[str, Any]],
    thread_values: list[int],
    concurrency_values: list[int],
) -> list[dict[str, Any]]:
    root = output_root / "encode_grid"
    root.mkdir(parents=True)
    results: list[dict[str, Any]] = []
    for threads in thread_values:
        for concurrency in concurrency_values:
            label = f"t{threads}_c{concurrency}"
            destination = root / label
            destination.mkdir()
            local_destination = capture.TMP_ROOT / "encode-grid" / label
            if local_destination.exists():
                raise RuntimeError(
                    f"refuse overwrite: {local_destination}"
                )
            local_destination.mkdir(parents=True)
            monitor.set_phase(f"encode:{label}")
            started = time.monotonic()
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=concurrency
            ) as executor:
                futures = [
                    executor.submit(
                        encode_one,
                        source,
                        local_destination / f"{index:03d}.mkv",
                        threads,
                    )
                    for index, source in enumerate(sources)
                ]
                walls = [future.result() for future in futures]
            batch_wall = time.monotonic() - started
            row = {
                "x264_threads": threads,
                "encode_concurrency": concurrency,
                "episodes": len(sources),
                "batch_wall_seconds": batch_wall,
                "episodes_per_hour": len(sources) * 3600.0 / batch_wall,
                "video_seconds_per_wall_second": (
                    len(sources) * 5.0 / batch_wall
                ),
                "individual_encode_wall_seconds": walls,
                "individual_median_seconds": median(walls),
                "individual_mean_seconds": mean(walls),
                "pass": True,
            }
            results.append(row)
            for log in sorted(local_destination.glob("*.log")):
                shutil.copy2(log, destination / log.name)
            atomic_json(destination / "result.json", row)
            print(
                f"encode {label} eps_h={row['episodes_per_hour']:.2f}",
                flush=True,
            )
            resolved = local_destination.resolve()
            expected_parent = (capture.TMP_ROOT / "encode-grid").resolve()
            if resolved.parent != expected_parent:
                raise RuntimeError(
                    f"unsafe encode-grid cleanup: {resolved}"
                )
            shutil.rmtree(resolved)
    atomic_json(root / "results.json", {"results": results})
    return results


def write_metrics(path: Path, samples: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not samples:
        return
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(samples[0]))
        writer.writeheader()
        writer.writerows(samples)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(capture.ROOT / "benchmarks/h200_takeover_20260727"),
    )
    parser.add_argument(
        "--tmp-root",
        default="./tmp/xonotic_capture/h200-takeover/benchmark",
    )
    parser.add_argument("--waves", type=int, default=2)
    parser.add_argument("--extend-threshold", type=float, default=0.05)
    args = parser.parse_args()

    capture.require_conda()
    output_root = Path(args.output_root).resolve()
    if output_root.exists():
        raise RuntimeError(f"refuse overwrite: {output_root}")
    output_root.mkdir(parents=True)
    capture.TMP_ROOT = Path(args.tmp_root).resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)
    build = capture.build_root()
    source_commit = (build / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if source_commit != SOURCE_COMMIT:
        raise RuntimeError(source_commit)
    gpu = shard_runner.gpu_inventory(True, 0)
    templates = load_templates()
    monitor = RuntimeMonitor()
    monitor.start()
    full_results: list[dict[str, Any]] = []
    raw_batches: dict[int, list[dict[str, Any]]] = {}
    all_attempt_results: list[dict[str, Any]] = []
    try:
        for sequence, workers in enumerate((1, 2, 4, 8)):
            summary, results = run_batch(
                output_root,
                monitor,
                templates,
                f"base_n{workers}",
                workers,
                args.waves,
                workers,
                workers,
                workers,
                0,
                workers,
                34000 + sequence * 128,
            )
            full_results.append(summary)
            raw_batches[workers] = results
            all_attempt_results.extend(results)

        gain_4_to_8 = (
            full_results[-1]["episodes_per_hour"]
            / full_results[-2]["episodes_per_hour"]
            - 1.0
        )
        if gain_4_to_8 > args.extend_threshold:
            for sequence, workers in enumerate((12, 16), 4):
                summary, results = run_batch(
                    output_root,
                    monitor,
                    templates,
                    f"base_n{workers}",
                    workers,
                    args.waves,
                    workers,
                    workers,
                    workers,
                    0,
                    workers,
                    34000 + sequence * 128,
                )
                full_results.append(summary)
                raw_batches[workers] = results
                all_attempt_results.extend(results)

        best_base = max(
            full_results, key=lambda row: row["episodes_per_hour"]
        )
        source_results = raw_batches[best_base["workers"]][
            : min(8, len(raw_batches[best_base["workers"]]))
        ]
        grid = encode_grid(
            output_root,
            monitor,
            source_results,
            [0, 2, 4, 8, 16],
            [1, 2, 4, 8],
        )
        best_encode = max(
            grid, key=lambda row: row["episodes_per_hour"]
        )
        tuned_summary, tuned_results = run_batch(
            output_root,
            monitor,
            templates,
            (
                f"tuned_n{best_base['workers']}_"
                f"t{best_encode['x264_threads']}_"
                f"c{best_encode['encode_concurrency']}"
            ),
            best_base["workers"],
            args.waves,
            best_base["workers"],
            best_base["workers"],
            best_base["workers"],
            best_encode["x264_threads"],
            best_encode["encode_concurrency"],
            35200,
        )
        raw_batches[-1] = tuned_results
        all_attempt_results.extend(tuned_results)
        full_results.append(tuned_summary)
    finally:
        monitor.set_phase("finished")
        monitor.finish()
        write_metrics(output_root / "runtime_metrics.csv", monitor.samples)

    summary = {
        "schema_version": "xonotic-h200-pipeline-benchmark-v1",
        "created_utc": capture.utc_now(),
        "source_commit": source_commit,
        "build": str(build),
        "gpu": gpu,
        "waves": args.waves,
        "full_pipeline_results": full_results,
        "renderer_extension_trigger": {
            "threshold": args.extend_threshold,
            "gain_4_to_8": gain_4_to_8,
            "tested_12_16": gain_4_to_8 > args.extend_threshold,
        },
        "encode_grid": grid,
        "best_base": best_base,
        "best_encode": best_encode,
        "tuned_result": tuned_summary,
        "recommended": {
            "renderers_per_gpu": tuned_summary["workers"],
            "x264_threads": best_encode["x264_threads"],
            "encode_concurrency": best_encode["encode_concurrency"],
            "single_gpu_episodes_per_hour": tuned_summary[
                "episodes_per_hour"
            ],
            "linear_32_gpu_episodes_per_hour": (
                tuned_summary["episodes_per_hour"] * 32
            ),
            "planning_32_gpu_episodes_per_hour_at_90pct": (
                tuned_summary["episodes_per_hour"] * 32 * 0.9
            ),
        },
    }
    atomic_json(output_root / "BENCHMARK_SUMMARY.json", summary)
    for result in all_attempt_results:
        stage = Path(result["stage"])
        if stage.is_dir():
            capture.clean_stage(stage)
    print(json.dumps(summary["recommended"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
