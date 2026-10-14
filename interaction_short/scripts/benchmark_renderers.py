                      
"""Measure bounded 1/2/4/8-way offline renderer and CPU encode scaling.

This script only re-renders already accepted Pilot demos.  It has no path that
can launch the formal 15,804-episode collection.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from statistics import mean
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = Path("./xonotic_capture")
TMP_BENCHMARK_ROOT = Path("./tmp/xonotic_capture/benchmark-renderers")
OUTPUT_ROOT = ROOT / "benchmarks/renderers"
CONCURRENCIES = (1, 2, 4, 8)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_process_usage(marker: str) -> tuple[float, int, int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,pcpu=,rss=,args="],
        capture_output=True,
        text=True,
        check=True,
    )
    cpu_percent = 0.0
    rss_kib = 0
    process_count = 0
    for line in completed.stdout.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) != 4:
            continue
        _, cpu_text, rss_text, command = fields
        if marker not in command:
            continue
        if "xonotic-local-sdl" not in command and "ffmpeg" not in command:
            continue
        cpu_percent += float(cpu_text)
        rss_kib += int(rss_text)
        process_count += 1
    return cpu_percent, rss_kib, process_count


def read_gpu() -> tuple[float, float, float, float]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,utilization.memory,memory.used,power.draw",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    values = [float(item.strip()) for item in completed.stdout.splitlines()[0].split(",")]
    return values[0], values[1], values[2], values[3]


def sample_runtime(
    phase: str,
    marker: str,
    started: float,
    raw_paths: list[Path],
) -> dict[str, Any]:
    gpu, gpu_memory_util, gpu_memory_mib, power_w = read_gpu()
    cpu_percent, rss_kib, process_count = read_process_usage(marker)
    raw_bytes = sum(path.stat().st_size for path in raw_paths if path.is_file())
    return {
        "phase": phase,
        "elapsed_seconds": time.monotonic() - started,
        "gpu_util_pct": gpu,
        "gpu_memory_util_pct": gpu_memory_util,
        "gpu_memory_mib": gpu_memory_mib,
        "gpu_power_w": power_w,
        "process_cpu_pct": cpu_percent,
        "process_rss_kib": rss_kib,
        "process_count": process_count,
        "raw_bytes": raw_bytes,
    }


def run_concurrently(
    jobs: list[Callable[[], Any]],
    phase: str,
    marker: str,
    raw_paths: list[Path],
) -> tuple[list[Any], float, list[dict[str, Any]]]:
    start_event = threading.Event()

    def gated(job: Callable[[], Any]) -> Any:
        start_event.wait()
        return job()

    samples: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures: list[Future[Any]] = [pool.submit(gated, job) for job in jobs]
        started = time.monotonic()
        start_event.set()
        while not all(future.done() for future in futures):
            samples.append(sample_runtime(phase, marker, started, raw_paths))
            time.sleep(0.25)
        values = [future.result() for future in futures]
    wall_seconds = time.monotonic() - started
    samples.append(sample_runtime(phase, marker, started, raw_paths))
    return values, wall_seconds, samples


def copy_and_hash(source: Path, destination: Path) -> tuple[int, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    source_hash = capture.sha256_file(source)
    if source_hash != capture.sha256_file(destination):
        raise RuntimeError(f"CPFS upload hash mismatch: {destination}")
    return source.stat().st_size, source_hash


def benchmark_count(
    count: int,
    accepted: list[dict[str, Any]],
    scenarios: dict[str, dict[str, Any]],
    build: Path,
) -> dict[str, Any]:
    stage_root = TMP_BENCHMARK_ROOT / f"n{count}"
    output = OUTPUT_ROOT / f"n{count}"
    if stage_root.exists() or output.exists():
        raise RuntimeError(f"refusing to overwrite benchmark: {stage_root} or {output}")
    stage_root.mkdir(parents=True)
    output.mkdir(parents=True)

    jobs: list[dict[str, Any]] = []
    for row in accepted[:count]:
        episode_id = row["episode_id"]
        scenario = scenarios[episode_id]
        job_root = stage_root / episode_id
        _, client_user = capture.prepare_userdirs(job_root, build)
        demo_source = Path(row["raw_path"]) / "demo.dem"
        demo_destination = client_user / "data/demos" / f"{episode_id}.dem"
        shutil.copy2(demo_source, demo_destination)
        jobs.append(
            {
                "episode_id": episode_id,
                "scenario": scenario,
                "root": job_root,
                "client_user": client_user,
            }
        )

    raw_paths = [
        job["client_user"] / "data/video" / f"{job['episode_id']}_000.avi"
        for job in jobs
    ]
    render_calls = [
        (
            lambda job=job: capture.run_render_attempt(
                job["root"],
                job["scenario"],
                build,
                job["client_user"],
            )
        )
        for job in jobs
    ]
    renders, render_wall, render_samples = run_concurrently(
        render_calls,
        "render",
        str(stage_root),
        raw_paths,
    )

    frame_rows: dict[str, int] = {}
    raw_bytes = 0
    for job, render in zip(jobs, renders, strict=True):
        raw_path = Path(render["raw_avi"])
        raw_bytes += raw_path.stat().st_size
        with Path(render["frames_engine"]).open(newline="", encoding="utf-8") as handle:
            frame_rows[job["episode_id"]] = sum(1 for _ in csv.DictReader(handle))
        if frame_rows[job["episode_id"]] != capture.OUTPUT_TICKS:
            raise RuntimeError(
                f"{job['episode_id']} frame telemetry rows "
                f"{frame_rows[job['episode_id']]}"
            )

    encode_calls: list[Callable[[], Any]] = []
    encoded_paths: list[Path] = []
    for job, render in zip(jobs, renders, strict=True):
        encoded = job["root"] / "encoded/video.mkv"
        encoded_paths.append(encoded)
        with Path(render["frames_engine"]).open(
            newline="", encoding="utf-8"
        ) as handle:
            first_frame = next(csv.DictReader(handle))
        audio_start = int(first_frame["mixer_audio_cursor_at_frame"])
        encode_calls.append(
            lambda job=job, render=render, encoded=encoded, audio_start=audio_start: (
                capture.encode_video(
                    Path(render["raw_avi"]),
                    encoded,
                    job["root"] / "ffmpeg_encode.log",
                    audio_start,
                )
            )
        )
    encode_walls, encode_batch_wall, encode_samples = run_concurrently(
        encode_calls,
        "encode",
        str(stage_root),
        raw_paths,
    )

    av_drifts_ms: list[float] = []
    encoded_contracts: dict[str, dict[str, bool]] = {}
    for job, encoded in zip(jobs, encoded_paths, strict=True):
        probe = capture.ffprobe_json(encoded, count_frames=True)
        frames = capture.count_video_frames(probe)
        samples = int(capture.decode_audio_s16(encoded).shape[0])
        drift_ms = abs(samples / capture.AUDIO_RATE - frames / capture.VIDEO_FPS) * 1000
        av_drifts_ms.append(drift_ms)
        contract = capture.encoded_contract(probe, encoded)
        contract["encoded_frames_exact"] = frames == capture.OUTPUT_TICKS
        contract["encoded_audio_samples_exact"] = samples == capture.AUDIO_SAMPLES
        encoded_contracts[job["episode_id"]] = contract
        if not all(contract.values()):
            raise RuntimeError(
                f"{job['episode_id']} encoded contract failed: {contract}"
            )

    upload_sources: list[tuple[Path, Path]] = []
    for job, render, encoded in zip(jobs, renders, encoded_paths, strict=True):
        artifact_dir = output / "artifacts" / job["episode_id"]
        upload_sources.extend(
            [
                (Path(render["raw_avi"]), artifact_dir / "raw_capture.avi"),
                (encoded, artifact_dir / "video.mkv"),
            ]
        )
    upload_started = time.monotonic()
    with ThreadPoolExecutor(max_workers=count) as pool:
        upload_futures = [
            pool.submit(copy_and_hash, source, destination)
            for source, destination in upload_sources
        ]
        uploaded = [future.result() for future in upload_futures]
    upload_wall = time.monotonic() - upload_started
    upload_bytes = sum(size for size, _ in uploaded)

    upload_hashes: dict[str, str] = {}
    for (source, destination), (_, digest) in zip(
        upload_sources, uploaded, strict=True
    ):
        upload_hashes[str(destination.relative_to(output))] = digest
        del source
    write_json(output / "artifacts_sha256.json", upload_hashes)

    for job, render in zip(jobs, renders, strict=True):
        evidence = output / "evidence" / job["episode_id"]
        evidence.mkdir(parents=True, exist_ok=True)
        for source in (
            job["root"] / "client_render_console.log",
            job["root"] / "ffmpeg_encode.log",
            Path(render["frames_engine"]),
            Path(render["audio_events_engine"]),
        ):
            shutil.copy2(source, evidence / source.name)

    samples = render_samples + encode_samples
    with (output / "runtime_metrics.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(samples[0]))
        writer.writeheader()
        writer.writerows(samples)
    render_cpu = [row["process_cpu_pct"] for row in render_samples]
    render_gpu = [row["gpu_util_pct"] for row in render_samples]
    render_gpu_memory = [row["gpu_memory_mib"] for row in render_samples]
    render_power = [row["gpu_power_w"] for row in render_samples]
    encode_cpu = [row["process_cpu_pct"] for row in encode_samples]

    result = {
        "schema_version": "xonotic-renderer-benchmark-v1",
        "renderer_count": count,
        "episode_ids": [job["episode_id"] for job in jobs],
        "renderer": sorted({render["renderer"] for render in renders}),
        "aggregate_capture_fps": count * capture.OUTPUT_TICKS / render_wall,
        "generated_video_seconds": count * 5.0,
        "render_batch_wall_seconds": render_wall,
        "render_video_seconds_per_wall_second": count * 5.0 / render_wall,
        "render_individual_wall_seconds": [
            render["render_wall_seconds"] for render in renders
        ],
        "gpu_util_pct_mean": mean(render_gpu),
        "gpu_util_pct_max": max(render_gpu),
        "gpu_memory_mib_mean": mean(render_gpu_memory),
        "gpu_memory_mib_max": max(render_gpu_memory),
        "gpu_power_w_mean": mean(render_power),
        "gpu_power_w_max": max(render_power),
        "render_process_cpu_pct_mean": mean(render_cpu),
        "render_process_cpu_pct_max": max(render_cpu),
        "raw_bytes": raw_bytes,
        "raw_write_mib_s": raw_bytes / (1024 * 1024) / render_wall,
        "x264_individual_wall_seconds": encode_walls,
        "x264_batch_wall_seconds": encode_batch_wall,
        "x264_video_seconds_per_wall_second": count * 5.0 / encode_batch_wall,
        "x264_process_cpu_pct_mean": mean(encode_cpu),
        "x264_process_cpu_pct_max": max(encode_cpu),
        "cpfs_upload_bytes": upload_bytes,
        "cpfs_upload_wall_seconds": upload_wall,
        "cpfs_upload_mib_s": upload_bytes / (1024 * 1024) / upload_wall,
        "av_drift_ms_max": max(av_drifts_ms),
        "frame_rows": frame_rows,
        "encoded_contracts": encoded_contracts,
        "artifacts_sha256_path": str(output / "artifacts_sha256.json"),
    }
    write_json(output / "result.json", result)

    resolved = stage_root.resolve()
    if resolved.parent != TMP_BENCHMARK_ROOT.resolve():
        raise RuntimeError(f"unsafe benchmark cleanup target: {resolved}")
    shutil.rmtree(resolved)
    return result


def main() -> int:
    capture.require_conda()
    if OUTPUT_ROOT.exists() or TMP_BENCHMARK_ROOT.exists():
        raise RuntimeError(
            f"refusing to overwrite benchmark roots: "
            f"{OUTPUT_ROOT} or {TMP_BENCHMARK_ROOT}"
        )
    accepted = sorted(
        capture.load_jsonl(ROOT / "manifests/accepted.jsonl"),
        key=lambda row: row["episode_id"],
    )
    if len(accepted) != 100 or len({row["episode_id"] for row in accepted}) != 100:
        raise RuntimeError(
            f"renderer benchmark requires exactly 100 accepted Pilot rows; "
            f"found {len(accepted)}"
        )
    scenario_rows = capture.load_jsonl(ROOT / "configs/pilot_scenarios.jsonl")
    scenarios = {row["episode_id"]: row for row in scenario_rows}
    build = capture.build_root()
    TMP_BENCHMARK_ROOT.mkdir(parents=True)
    OUTPUT_ROOT.mkdir(parents=True)
    results: list[dict[str, Any]] = []
    try:
        for count in CONCURRENCIES:
            print(f"benchmark renderer_count={count}", flush=True)
            result = benchmark_count(count, accepted, scenarios, build)
            results.append(result)
            print(
                f"complete renderer_count={count} "
                f"capture_fps={result['aggregate_capture_fps']:.3f} "
                f"x264_x={result['x264_video_seconds_per_wall_second']:.3f}",
                flush=True,
            )
    finally:
        if TMP_BENCHMARK_ROOT.exists() and not any(TMP_BENCHMARK_ROOT.iterdir()):
            TMP_BENCHMARK_ROOT.rmdir()
    summary = {
        "schema_version": "xonotic-renderer-scaling-v1",
        "created_utc": capture.utc_now(),
        "source_commit": (build / "SOURCE_COMMIT").read_text().strip(),
        "build": str(build),
        "results": results,
    }
    write_json(OUTPUT_ROOT / "renderer_scaling.json", summary)
    print(f"summary={OUTPUT_ROOT / 'renderer_scaling.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
