                      
"""Verify live 128 fps headroom and offline 64 fps exact tick mapping."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import benchmark_h200_pipeline as benchmark
import benchmark_h200_staged_pipeline as staged
import xonotic_capture as capture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--tmp-root", required=True)
    args = parser.parse_args()

    capture.require_conda()
    output_root = Path(args.output_root).resolve()
    if output_root.exists():
        raise RuntimeError(f"refuse overwrite: {output_root}")
    output_root.mkdir(parents=True)
    capture.TMP_ROOT = Path(args.tmp_root).resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    if source_commit != staged.EXPECTED_SOURCE_COMMIT:
        raise RuntimeError(source_commit)

    monitor = benchmark.RuntimeMonitor()
    monitor.start()
    results: list[dict] = []
    try:
        summary, results = benchmark.run_batch(
            output_root,
            monitor,
            staged.load_formal_representative_templates()[:1],
            "rate_split_smoke",
            1,
            1,
            1,
            1,
            1,
            16,
            1,
            38_000,
            episode_count=1,
        )
        qa = results[0]["qa"]
        checks = {
            "hard_qa_pass": all(qa["hard_gates"].values()),
            "frames_320": qa["video"]["frames"] == 320,
            "audio_samples_240000": (
                qa["audio"]["samples_per_channel"] == 240_000
            ),
            "mapping_rate_1": qa["mapping"]["success_rate"] == 1.0,
            "mapping_ticks_64_383": (
                qa["mapping"]["episode_tick_first"] == 64
                and qa["mapping"]["episode_tick_last"] == 383
            ),
            "actions_384": qa["telemetry"]["action_rows"] == 384,
        }
        report = {
            "schema_version": "xonotic-h200-rate-split-smoke-v1",
            "source_commit": source_commit,
            "checks": checks,
            "pass": all(checks.values()),
            "mapping": qa["mapping"],
            "runtime": qa["runtime"],
            "batch": summary,
        }
        benchmark.atomic_json(output_root / "RESULT.json", report)
        staged.compact_finished_results(
            output_root, "rate_split_smoke", results
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else 2
    finally:
        monitor.set_phase("finished")
        monitor.finish()
        benchmark.write_metrics(
            output_root / "runtime_metrics.csv", monitor.samples
        )
        for result in results:
            stage = Path(result["stage"])
            if stage.is_dir():
                capture.clean_stage(stage)


if __name__ == "__main__":
    raise SystemExit(main())
