                      
"""Finish x264 tuning after the measured eight-renderer stability failure."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark_h200_pipeline as benchmark              
import run_capture_manifest_shard as shard_runner              
import xonotic_capture as capture              


def load_batch(root: Path, name: str) -> dict[str, Any]:
    result_path = root / "full_pipeline" / name / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    qa_paths = sorted(result_path.parent.glob("*/episode/qa.json"))
    result["soft_qa_pass"] = bool(qa_paths) and all(
        all(
            json.loads(path.read_text(encoding="utf-8"))[
                "soft_gates"
            ].values()
        )
        for path in qa_paths
    )
    result["published_episode_count"] = len(qa_paths)
    return result


def load_sources(root: Path, name: str) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for path in sorted(
        (root / "full_pipeline" / name).glob(
            "*/benchmark_result.json"
        )
    ):
        result = json.loads(path.read_text(encoding="utf-8"))
        episode_path = Path(result["publication"]["episode_path"])
        result["qa"] = json.loads(
            (episode_path / "qa.json").read_text(encoding="utf-8")
        )
        stage = Path(result["stage"])
        if not stage.is_dir():
            raise RuntimeError(f"source stage missing: {stage}")
        sources.append(result)
    return sources


def cpu_quota() -> dict[str, Any]:
    path = Path("/sys/fs/cgroup/cpu.max")
    if not path.is_file():
        return {"cpu_max": None, "quota_vcpu": None}
    raw = path.read_text(encoding="utf-8").strip()
    quota, period = raw.split()
    return {
        "cpu_max": raw,
        "quota_vcpu": (
            None if quota == "max" else int(quota) / int(period)
        ),
    }


def n8_failure(root: Path) -> dict[str, Any]:
    batch = root / "full_pipeline/base_n8"
    completed = sorted(batch.glob("*/benchmark_result.json"))
    diagnostics = batch / "diagnostics"
    action_rows: dict[str, int] = {}
    for name in (
        "h200bench_base_n8_008_a01",
        "h200bench_base_n8_008_a02",
    ):
        precheck = json.loads(
            (diagnostics / name / "LIVE_PRECHECK.json").read_text(
                encoding="utf-8"
            )
        )
        action_rows[name] = int(precheck["action_rows"])
    first_render_log = (
        diagnostics
        / "h200bench_base_n8_013_a01/client_render_console.log"
    ).read_text(encoding="utf-8", errors="replace")
    result = {
        "schema_version": "xonotic-h200-renderer-stability-failure-v1",
        "label": "base_n8",
        "workers": 8,
        "planned_episodes": 16,
        "published_episodes": len(completed),
        "stable": False,
        "episodes_per_hour": None,
        "failed_source_template": "v2_causal_02",
        "failures": [
            {
                "episode_id": "h200bench_base_n8_008",
                "attempts": 2,
                "reason": "incomplete_live_action_ticks",
                "expected_action_rows": 384,
                "observed_action_rows": action_rows,
            },
            {
                "episode_id": "h200bench_base_n8_013",
                "reason": "offline_render_timeout",
                "timeout_seconds": 120,
                "first_attempt_timeout_recorded": (
                    "timeout_seconds=120" in first_render_log
                ),
                "second_attempt_stopped_with_unstable_batch": True,
            },
        ],
        "diagnostic_root": str(diagnostics),
        "extension_decision": {
            "tested_12_16": False,
            "reason": (
                "eight renderers did not complete two stable waves; "
                "unstable configurations are not throughput gains"
            ),
        },
    }
    benchmark.atomic_json(root / "N8_STABILITY_FAILURE.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(
            capture.ROOT / "benchmarks/h200_takeover_20260727_v2"
        ),
    )
    parser.add_argument(
        "--tmp-root",
        default=(
            "./tmp/xonotic_capture/h200-takeover/"
            "benchmark-v2-continuation"
        ),
    )
    parser.add_argument("--tuned-waves", type=int, default=4)
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="audit an already-written summary without rerunning work",
    )
    args = parser.parse_args()

    capture.require_conda()
    root = Path(args.output_root).resolve()
    if not root.is_dir():
        raise RuntimeError(f"benchmark root missing: {root}")
    summary_path = root / "BENCHMARK_SUMMARY.json"
    if args.verify_existing:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        tuned = summary["tuned_result"]
        tuned_root = (
            root / "full_pipeline" / tuned["label"]
        )
        qa_paths = sorted(tuned_root.glob("*/episode/qa.json"))
        checks = {
            "source_commit": (
                summary["source_commit"] == benchmark.SOURCE_COMMIT
            ),
            "renderer_count": (
                summary["recommended"]["renderers_per_gpu"] == 4
            ),
            "tuned_episode_count": len(qa_paths) == 16,
            "tuned_result_count": (
                len(
                    list(tuned_root.glob("*/benchmark_result.json"))
                )
                == 16
            ),
            "all_hard_soft_qa": bool(qa_paths)
            and all(
                all(qa["hard_gates"].values())
                and all(qa["soft_gates"].values())
                for qa in (
                    json.loads(path.read_text(encoding="utf-8"))
                    for path in qa_paths
                )
            ),
            "media_and_mapping": bool(qa_paths)
            and all(
                qa["video"]["frames"] == capture.OUTPUT_TICKS
                and qa["audio"]["samples_per_channel"]
                == capture.AUDIO_SAMPLES
                and qa["mapping"]["success_rate"] == 1.0
                for qa in (
                    json.loads(path.read_text(encoding="utf-8"))
                    for path in qa_paths
                )
            ),
            "n8_failure_recorded": (
                summary["unstable_n8"]["stable"] is False
                and summary["unstable_n8"]["published_episodes"] == 14
            ),
        }
        audit = {
            "schema_version": (
                "xonotic-h200-pipeline-benchmark-audit-v1"
            ),
            "created_utc": capture.utc_now(),
            "summary": str(summary_path),
            "checks": checks,
            "pass": all(checks.values()),
        }
        benchmark.atomic_json(root / "BENCHMARK_AUDIT.json", audit)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["pass"] else 2
    if summary_path.exists():
        raise RuntimeError("refuse overwrite: BENCHMARK_SUMMARY.json")
    capture.TMP_ROOT = Path(args.tmp_root).resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)

    build = capture.build_root()
    source_commit = (build / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if source_commit != benchmark.SOURCE_COMMIT:
        raise RuntimeError(f"source commit mismatch: {source_commit}")
    gpu = shard_runner.gpu_inventory(True, 0)
    base_results = [
        load_batch(root, name)
        for name in ("base_n1", "base_n2", "base_n4")
    ]
    if not all(
        row["hard_qa_pass"]
        and row["soft_qa_pass"]
        and row["frames_exact"]
        and row["audio_exact"]
        and row["mapping_min"] == 1.0
        for row in base_results
    ):
        raise RuntimeError("stable base result QA failed")
    sources = load_sources(root, "base_n4")
    if len(sources) != 8:
        raise RuntimeError(f"expected 8 n4 sources, found {len(sources)}")
    instability = n8_failure(root)

    monitor = benchmark.RuntimeMonitor()
    monitor.start()
    tuned_results: list[dict[str, Any]] = []
    try:
        grid = benchmark.encode_grid(
            root,
            monitor,
            sources,
            [0, 2, 4, 8, 16],
            [1, 2, 4, 8],
        )
        eligible_grid = [
            row
            for row in grid
            if row["encode_concurrency"] <= 4
        ]
        best_encode = max(
            eligible_grid, key=lambda row: row["episodes_per_hour"]
        )
        label = (
            f"tuned_n4_t{best_encode['x264_threads']}_"
            f"c{best_encode['encode_concurrency']}"
        )
        tuned, tuned_results = benchmark.run_batch(
            root,
            monitor,
            benchmark.load_templates(),
            label,
            4,
            args.tuned_waves,
            best_encode["x264_threads"],
            best_encode["encode_concurrency"],
            35200,
        )
    finally:
        monitor.set_phase("finished")
        monitor.finish()
        benchmark.write_metrics(
            root / "continuation_runtime_metrics.csv",
            monitor.samples,
        )

    tuned["soft_qa_pass"] = all(
        all(row["qa"]["soft_gates"].values())
        for row in tuned_results
    )
    tuned["individual_wall_cv"] = (
        statistics.pstdev(tuned["individual_wall_seconds"])
        / statistics.mean(tuned["individual_wall_seconds"])
    )
    if not (
        tuned["hard_qa_pass"]
        and tuned["soft_qa_pass"]
        and tuned["frames_exact"]
        and tuned["audio_exact"]
        and tuned["mapping_min"] == 1.0
    ):
        raise RuntimeError("tuned end-to-end validation failed")

    best_grid_unbounded = max(
        grid, key=lambda row: row["episodes_per_hour"]
    )
    single = tuned["episodes_per_hour"]
    summary = {
        "schema_version": "xonotic-h200-pipeline-benchmark-v2",
        "created_utc": capture.utc_now(),
        "source_commit": source_commit,
        "build": str(build),
        "gpu": gpu,
        "cpu_allocation": cpu_quota(),
        "method": {
            "base_waves": 2,
            "tuned_waves": args.tuned_waves,
            "throughput_boundary": (
                "live capture through hashed atomic AFS publication"
            ),
            "stable_selection": (
                "all planned episodes, all hard and soft QA, "
                "two complete waves required"
            ),
        },
        "stable_base_results": base_results,
        "unstable_n8": instability,
        "renderer_extension": {
            "tested_12_16": False,
            "reason": instability["extension_decision"]["reason"],
        },
        "encode_grid": grid,
        "best_encode_unbounded": best_grid_unbounded,
        "best_encode_for_four_renderers": best_encode,
        "tuned_result": tuned,
        "recommended": {
            "renderers_per_gpu": 4,
            "x264_preset": "medium",
            "x264_threads": best_encode["x264_threads"],
            "encode_concurrency": best_encode[
                "encode_concurrency"
            ],
            "single_gpu_episodes_per_hour": single,
            "linear_32_gpu_episodes_per_hour": single * 32,
            "planning_32_gpu_episodes_per_hour_at_90pct": (
                single * 32 * 0.9
            ),
        },
    }
    benchmark.atomic_json(root / "BENCHMARK_SUMMARY.json", summary)

    for result in tuned_results:
        stage = Path(result["stage"])
        if stage.is_dir():
            capture.clean_stage(stage)

    print(
        json.dumps(summary["recommended"], indent=2, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
