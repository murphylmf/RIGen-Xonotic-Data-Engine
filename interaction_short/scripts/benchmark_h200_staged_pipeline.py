                      
"""Benchmark decoupled live, EGL render, and x264 scheduling on one H200."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import traceback
from pathlib import Path
from typing import Any

import benchmark_h200_pipeline as benchmark
import run_capture_manifest_shard as shard_runner
import xonotic_capture as capture


EXPECTED_SOURCE_COMMIT = "63bfb795faca21ad3db6dff7632171a13223cd76"


def numeric_summary(
    samples: list[dict[str, Any]], key: str
) -> dict[str, float | None]:
    values = sorted(
        float(row[key])
        for row in samples
        if row.get(key) is not None
    )
    if not values:
        return {"mean": None, "p95": None, "max": None}
    p95_index = min(int(0.95 * len(values)), len(values) - 1)
    return {
        "mean": statistics.fmean(values),
        "p95": values[p95_index],
        "max": values[-1],
    }


def resource_summary(
    samples: list[dict[str, Any]],
) -> dict[str, dict[str, float | None] | int]:
    return {
        "samples": len(samples),
        "gpu_util_percent": numeric_summary(
            samples, "gpu_util_percent"
        ),
        "gpu_memory_mib": numeric_summary(samples, "gpu_memory_mib"),
        "gpu_power_w": numeric_summary(samples, "gpu_power_w"),
        "cgroup_cpu_cores_used": numeric_summary(
            samples, "cgroup_cpu_cores_used"
        ),
        "cgroup_cpu_quota_percent": numeric_summary(
            samples, "cgroup_cpu_quota_percent"
        ),
        "cgroup_throttle_period_fraction": numeric_summary(
            samples, "cgroup_throttle_period_fraction"
        ),
        "cgroup_throttled_seconds_delta": numeric_summary(
            samples, "cgroup_throttled_seconds_delta"
        ),
        "cgroup_memory_current_mib": numeric_summary(
            samples, "cgroup_memory_current_mib"
        ),
    }


def remove_heavy_raw_payloads(root: Path) -> int:
    """Keep QA/logs/telemetry while removing benchmark-only raw AVI copies."""
    removed_bytes = 0
    for path in root.rglob("raw_capture.avi"):
        if path.is_file():
            removed_bytes += path.stat().st_size
            path.unlink()
    return removed_bytes


def compact_finished_results(
    output_root: Path,
    label: str,
    results: list[dict[str, Any]],
) -> int:
    destination = output_root / "full_pipeline" / label
    for result in results:
        episode_root = destination / result["episode_id"]
        benchmark.atomic_json(
            episode_root / "qa_snapshot.json", result["qa"]
        )
    removed_bytes = remove_heavy_raw_payloads(destination)
    for result in results:
        stage = Path(result["stage"])
        if stage.is_dir():
            capture.clean_stage(stage)
    return removed_bytes


def compact_failed_config(
    output_root: Path,
    label: str,
) -> int:
    destination = output_root / "full_pipeline" / label
    removed_bytes = (
        remove_heavy_raw_payloads(destination)
        if destination.is_dir()
        else 0
    )
    raw_root = capture.TMP_ROOT / "raw"
    for stage in raw_root.glob(f"h200bench_{label}_*_a*"):
        if stage.is_dir():
            capture.clean_stage(stage)
    return removed_bytes


def read_cgroup_allocation() -> dict[str, Any]:
    cgroup = Path("/sys/fs/cgroup")
    cpu_max = (cgroup / "cpu.max").read_text(
        encoding="utf-8"
    ).strip()
    quota, period = cpu_max.split()
    memory_max = (cgroup / "memory.max").read_text(
        encoding="utf-8"
    ).strip()
    return {
        "cpu_max": cpu_max,
        "quota_cpu_cores": (
            None if quota == "max" else int(quota) / int(period)
        ),
        "memory_max_bytes": (
            None if memory_max == "max" else int(memory_max)
        ),
        "cpuset_cpus_effective": (
            cgroup / "cpuset.cpus.effective"
        ).read_text(encoding="utf-8").strip(),
    }


def config(
    label: str,
    pipelines: int,
    live: int,
    render: int,
    sdl: int,
    encode: int,
    threads: int,
    cpuset: str = "",
) -> dict[str, int | str]:
    return {
        "label": label,
        "pipelines": pipelines,
        "live_concurrency": live,
        "render_concurrency": render,
        "sdl_concurrency": sdl,
        "encode_concurrency": encode,
        "x264_threads": threads,
        "x264_cpuset": cpuset,
    }


def load_formal_representative_templates() -> list[dict[str, Any]]:
    """Use c68 scenarios already accepted plus one no-enemy race row."""
    ordered_ids = (
        "s1f_000002",                
        "s1f_000101",             
        "s1f_000065",                     
        "s1f_000001",                               
        "s1f_000769",                  
    )
    wanted = set(ordered_ids)
    rows: dict[str, dict[str, Any]] = {}
    manifest_root = (
        capture.ROOT
        / "manifests/stage1_foundation_v1/shards/primary"
    )
    for path in sorted(manifest_root.glob("*.jsonl")):
        for row in capture.load_jsonl(path):
            if row["episode_id"] in wanted:
                rows[row["episode_id"]] = row
        if len(rows) == len(wanted):
            break
    missing = wanted - set(rows)
    if missing:
        raise RuntimeError(
            f"formal representative rows missing: {sorted(missing)}"
        )
    return [rows[episode_id] for episode_id in ordered_ids]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(
            capture.ROOT / "benchmarks/h200_staged_20260727"
        ),
    )
    parser.add_argument(
        "--tmp-root",
        default="./tmp/xonotic_capture/h200-staged-20260727",
    )
    parser.add_argument("--episodes-per-config", type=int, default=16)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume from MATRIX_PROGRESS.json and skip completed labels",
    )
    args = parser.parse_args()

    capture.require_conda()
    if args.episodes_per_config < 12:
        raise RuntimeError("episodes-per-config must be at least 12")
    output_root = Path(args.output_root).resolve()
    progress_path = output_root / "MATRIX_PROGRESS.json"
    if output_root.exists() and not args.resume:
        raise RuntimeError(f"refuse overwrite: {output_root}")
    if args.resume and not progress_path.is_file():
        raise RuntimeError(
            f"resume requires existing progress file: {progress_path}"
        )
    output_root.mkdir(parents=True, exist_ok=args.resume)
    capture.TMP_ROOT = Path(args.tmp_root).resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)

    build = capture.build_root()
    source_commit = (build / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError(
            f"unexpected build source commit: {source_commit}"
        )
    gpu = shard_runner.gpu_inventory(True, 0)
    templates = load_formal_representative_templates()
    allocation = read_cgroup_allocation()
    monitor = benchmark.RuntimeMonitor()
    monitor.start()
    if args.resume:
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if progress.get("source_commit") != source_commit:
            raise RuntimeError(
                "resume source commit mismatch: "
                f"{progress.get('source_commit')} != {source_commit}"
            )
        if int(progress.get("episodes_per_config", -1)) != int(
            args.episodes_per_config
        ):
            raise RuntimeError(
                "resume episodes-per-config mismatch: "
                f"{progress.get('episodes_per_config')} != "
                f"{args.episodes_per_config}"
            )
        results: list[dict[str, Any]] = list(progress["results"])
    else:
        results = []
    result_labels = {str(row["label"]) for row in results}

    def annotate_cpu_budget(row: dict[str, Any]) -> dict[str, Any]:
        current = row.get("config") or {}
        raw_thread_budget = int(
            current.get("encode_concurrency", 0)
        ) * int(
            current.get("x264_threads", 0)
        )
        cpuset_cpu_count = len(
            capture.parse_cpu_list(
                str(current.get("x264_cpuset", ""))
            )
        )
        thread_budget = (
            min(raw_thread_budget, cpuset_cpu_count)
            if cpuset_cpu_count
            else raw_thread_budget
        )
        row["x264_raw_thread_budget"] = raw_thread_budget
        row["x264_cpuset_cpu_count"] = cpuset_cpu_count
        quota = allocation.get("quota_cpu_cores")
        row["x264_thread_budget"] = thread_budget
        row["cpu_thread_budget_qualified"] = (
            quota is not None
            and thread_budget > 0
            and thread_budget <= float(quota)
        )
        return row

    for existing_result in results:
        annotate_cpu_budget(existing_result)

    initial = [
        config("baseline_p4_l4_r4_s4_e4_t16", 4, 4, 4, 4, 4, 16),
        config("overlap_p8_l4_r4_s4_e4_t16", 8, 4, 4, 4, 4, 16),
        config("overlap_p8_l4_r4_s5_e4_t16", 8, 4, 4, 5, 4, 16),
        config("overlap_p8_l4_r4_s6_e4_t16", 8, 4, 4, 6, 4, 16),
        config("overlap_p8_l4_r4_s7_e4_t16", 8, 4, 4, 7, 4, 16),
    ]

    def persist() -> None:
        benchmark.atomic_json(
            progress_path,
            {
                "schema_version": "xonotic-h200-staged-matrix-v1",
                "updated_utc": capture.utc_now(),
                "source_commit": source_commit,
                "build": str(build),
                "gpu": gpu,
                "allocation": allocation,
                "episodes_per_config": args.episodes_per_config,
                "results": results,
            },
        )

    def run(current: dict[str, Any], sequence: int) -> dict[str, Any]:
        label = str(current["label"])
        sample_start = len(monitor.samples)
        started = time.monotonic()
        print(
            f"matrix_start label={label} config="
            f"{json.dumps(current, sort_keys=True)}",
            flush=True,
        )
        batch_results: list[dict[str, Any]] = []
        try:
            os.environ["XONOTIC_X264_CPUSET"] = str(
                current.get("x264_cpuset", "")
            )
            summary, batch_results = benchmark.run_batch(
                output_root,
                monitor,
                templates,
                label,
                int(current["pipelines"]),
                1,
                int(current["live_concurrency"]),
                int(current["render_concurrency"]),
                int(current["sdl_concurrency"]),
                int(current["x264_threads"]),
                int(current["encode_concurrency"]),
                36_000 + sequence * 128,
                episode_count=args.episodes_per_config,
            )
            monitor.set_phase("between-configs")
            time.sleep(0.3)
            summary.update(
                {
                    "completed": True,
                    "stable": summary["operational_retries"] == 0,
                    "config": current,
                    "resources": resource_summary(
                        monitor.samples[sample_start:]
                    ),
                    "heavy_raw_bytes_removed_after_measurement": (
                        compact_finished_results(
                            output_root, label, batch_results
                        )
                    ),
                }
            )
            annotate_cpu_budget(summary)
            benchmark.atomic_json(
                output_root
                / "full_pipeline"
                / label
                / "result.json",
                summary,
            )
            print(
                f"matrix_done label={label} "
                f"eps_h={summary['episodes_per_hour']:.2f} "
                f"retries={summary['operational_retries']} "
                f"stable={summary['stable']}",
                flush=True,
            )
            return summary
        except Exception as exc:
            monitor.set_phase("between-configs")
            failure = {
                "label": label,
                "config": current,
                "stable": False,
                "pass": False,
                "batch_wall_seconds": time.monotonic() - started,
                "failure_type": type(exc).__name__,
                "failure_reason": (
                    exc.reason
                    if isinstance(exc, capture.CaptureFailure)
                    else None
                ),
                "failure_detail": str(exc),
                "traceback": traceback.format_exc(),
                "resources": resource_summary(
                    monitor.samples[sample_start:]
                ),
                "heavy_raw_bytes_removed_after_measurement": (
                    compact_failed_config(output_root, label)
                ),
            }
            annotate_cpu_budget(failure)
            print(
                f"matrix_failed label={label} "
                f"type={type(exc).__name__} detail={exc}",
                flush=True,
            )
            return failure

    def lower_sdl_mapping_failure(
        current: dict[str, Any],
    ) -> dict[str, Any] | None:
        current_sdl = int(current["sdl_concurrency"])
        candidates = [
            row
            for row in results
            if int(row.get("config", {}).get("sdl_concurrency", 0))
            < current_sdl
            and "frame_tick_mapping"
            in str(row.get("failure_detail", ""))
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda row: int(
                row["config"]["sdl_concurrency"]
            ),
        )

    def execute_or_skip(
        current: dict[str, Any],
        sequence: int,
        *,
        skip_after_lower_sdl_failure: bool = False,
    ) -> None:
        label = str(current["label"])
        if label in result_labels:
            print(f"matrix_resume_existing label={label}", flush=True)
            return
        if skip_after_lower_sdl_failure:
            lower_failure = lower_sdl_mapping_failure(current)
            if lower_failure is not None:
                row = {
                    "label": label,
                    "config": current,
                    "completed": False,
                    "stable": False,
                    "pass": False,
                    "skipped": True,
                    "skip_reason": (
                        "higher_shared_sdl_limit_after_lower_limit_"
                        "frame_tick_mapping_failure"
                    ),
                    "lower_failure_label": lower_failure["label"],
                }
                annotate_cpu_budget(row)
                results.append(row)
                result_labels.add(label)
                persist()
                print(
                    f"matrix_skipped label={label} "
                    f"lower_failure={lower_failure['label']}",
                    flush=True,
                )
                return
        row = run(current, sequence)
        results.append(row)
        result_labels.add(label)
        persist()

    try:
        sequence = 0
        for current in initial:
            execute_or_skip(
                current,
                sequence,
                skip_after_lower_sdl_failure=(
                    int(current["sdl_concurrency"]) > 5
                ),
            )
            sequence += 1

        tuning_completed = [
            row
            for row in results
            if str(row["label"]).startswith("overlap_p8_")
            and row.get("completed") is True
            and row.get("hard_qa_pass") is True
        ]
        if not tuning_completed:
            raise RuntimeError("no completed p8 tuning configuration")
        tuning_stable = [
            row
            for row in tuning_completed
            if row.get("stable") is True
        ]
        if not tuning_stable:
            raise RuntimeError("no stable p8 tuning configuration")
        best_tuning = max(
            tuning_stable,
            key=lambda row: row["episodes_per_hour"],
        )
        best_config = best_tuning["config"]
        threads = int(best_config["x264_threads"])
        encode = int(best_config["encode_concurrency"])
        sdl = int(best_config["sdl_concurrency"])
        encode_tuning = [
            config(
                f"encode_p8_s{sdl}_e2_t8",
                8,
                4,
                4,
                sdl,
                2,
                8,
            ),
            config(
                f"encode_p8_s{sdl}_e4_t8",
                8,
                4,
                4,
                sdl,
                4,
                8,
            ),
            config(
                f"encode_p8_s{sdl}_e4_t4",
                8,
                4,
                4,
                sdl,
                4,
                4,
            ),
            config(
                f"encode_p8_s{sdl}_e3_t6",
                8,
                4,
                4,
                sdl,
                3,
                6,
            ),
            config(
                f"encode_p8_s{sdl}_e4_t16_c16",
                8,
                4,
                4,
                sdl,
                4,
                16,
                "0-15",
            ),
        ]
        for current in encode_tuning:
            execute_or_skip(current, sequence)
            sequence += 1
        tuning_completed = [
            row
            for row in results
            if (
                str(row["label"]).startswith("overlap_p8_")
                or str(row["label"]).startswith("encode_p8_")
            )
            and row.get("completed") is True
            and row.get("hard_qa_pass") is True
        ]
        tuning_stable = [
            row
            for row in tuning_completed
            if row.get("stable") is True
            and row.get("cpu_thread_budget_qualified") is True
        ]
        if not tuning_stable:
            raise RuntimeError(
                "no stable encode configuration within CPU quota"
            )
        best_tuning = max(
            tuning_stable,
            key=lambda row: row["episodes_per_hour"],
        )
        best_config = best_tuning["config"]
        threads = int(best_config["x264_threads"])
        encode = int(best_config["encode_concurrency"])
        sdl = int(best_config["sdl_concurrency"])
        cpuset = str(best_config.get("x264_cpuset", ""))
        cap_label = (
            f"_c{len(capture.parse_cpu_list(cpuset))}"
            if cpuset
            else ""
        )
        capacity = [
            config(
                f"buffer_p12_l4_r4_s{sdl}_e{encode}_t"
                f"{threads}{cap_label}",
                12,
                4,
                4,
                sdl,
                encode,
                threads,
                cpuset,
            ),
        ]
        for current in capacity:
            execute_or_skip(current, sequence)
            sequence += 1

        completed = [
            row
            for row in results
            if row.get("completed") is True
            and row.get("hard_qa_pass") is True
        ]
        stable = [
            row
            for row in completed
            if row.get("stable") is True
            and row.get("cpu_thread_budget_qualified") is True
        ]
        if not stable:
            raise RuntimeError("no stable CPU-budget-qualified result")
        best = max(stable, key=lambda row: row["episodes_per_hour"])
        if (
            int(best["config"]["pipelines"]) == 12
            and best["episodes_per_hour"]
            > best_tuning["episodes_per_hour"] * 1.05
        ):
            current = config(
                f"extended_p16_l8_r8_s{sdl}_e{encode}_t"
                f"{threads}{cap_label}",
                16,
                8,
                8,
                sdl,
                encode,
                threads,
                cpuset,
            )
            execute_or_skip(current, sequence)

        completed = [
            row
            for row in results
            if row.get("completed") is True
            and row.get("hard_qa_pass") is True
        ]
        stable = [
            row
            for row in completed
            if row.get("stable") is True
            and row.get("cpu_thread_budget_qualified") is True
        ]
        if not stable:
            raise RuntimeError("no stable CPU-budget-qualified result")
        recommended = max(
            stable, key=lambda row: row["episodes_per_hour"]
        )
        final = {
            "schema_version": "xonotic-h200-staged-benchmark-v1",
            "created_utc": capture.utc_now(),
            "source_commit": source_commit,
            "build": str(build),
            "gpu": gpu,
            "allocation": allocation,
            "episodes_per_config": args.episodes_per_config,
            "results": results,
            "recommended": {
                **recommended["config"],
                "single_gpu_episodes_per_hour": recommended[
                    "episodes_per_hour"
                ],
                "linear_32_gpu_episodes_per_hour": (
                    recommended["episodes_per_hour"] * 32
                ),
                "planning_32_gpu_episodes_per_hour_at_90pct": (
                    recommended["episodes_per_hour"] * 32 * 0.9
                ),
                "stability_qualified": recommended["stable"],
                "source_result_label": recommended["label"],
            },
        }
        benchmark.atomic_json(
            output_root / "BENCHMARK_SUMMARY.json", final
        )
        print(
            "recommended="
            + json.dumps(final["recommended"], sort_keys=True),
            flush=True,
        )
    finally:
        monitor.set_phase("finished")
        monitor.finish()
        metrics_path = output_root / "runtime_metrics.csv"
        if metrics_path.exists():
            for index in range(1, 1000):
                candidate = (
                    output_root
                    / f"runtime_metrics_resume_{index:02d}.csv"
                )
                if not candidate.exists():
                    metrics_path = candidate
                    break
            else:
                raise RuntimeError("no free resume metrics filename")
        benchmark.write_metrics(
            metrics_path, monitor.samples
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
