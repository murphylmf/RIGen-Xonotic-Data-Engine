                      
"""Resilient 7-node x 4-GPU launcher for v14 category quotas."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(
    os.environ.get(
        "STAGE2_PYTHON",
        "./environment",
    )
)
HOLDER_PYTHON = Path(
    os.environ.get("STAGE2_GPU_HOLDER_PYTHON", "/usr/bin/python3")
)
RUNNER = ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v14_multigpu.py"
HOLDER = ROOT / "production_scripts/gpu_memory_holder.py"
RUNTIME_LOCK = (
    ROOT / "locks/stage2_motion_7x4_activeonly_v14r4_resilient_runtime.sha256"
)
CROSSHAIR_OVERLAY = ROOT / "configs/capture_client_stage2_v14_no_crosshair.cfg"
CATEGORIES = ("exit_reacquire", "exit_hold", "always_visible")
STOP = threading.Event()
CHILDREN: set[subprocess.Popen[bytes]] = set()
CHILDREN_LOCK = threading.Lock()


def integer_env(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    if not raw.isdigit():
        raise RuntimeError(f"{name} must be a non-negative integer: {raw!r}")
    return int(raw)


def register(process: subprocess.Popen[bytes]) -> subprocess.Popen[bytes]:
    with CHILDREN_LOCK:
        CHILDREN.add(process)
    return process


def unregister(process: subprocess.Popen[bytes]) -> None:
    with CHILDREN_LOCK:
        CHILDREN.discard(process)


def terminate(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def on_signal(signum: int, _frame: object) -> None:
    print(f"stage2_v14_node_signal signal={signum}", flush=True)
    STOP.set()
    with CHILDREN_LOCK:
        children = list(CHILDREN)
    for process in children:
        terminate(process)


def gpu_rows() -> list[tuple[int, str, str]]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,name",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rows: list[tuple[int, str, str]] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split(",", 2)]
        if len(fields) != 3:
            raise RuntimeError(f"unexpected GPU row: {line}")
        rows.append((int(fields[0]), fields[1], fields[2]))
    return rows


def start_holder(
    gpu_uuid: str, log_path: Path, heartbeat_seconds: int
) -> subprocess.Popen[bytes]:
    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = gpu_uuid
    handle = log_path.open("ab", buffering=0)
    process = register(
        subprocess.Popen(
            [
                str(HOLDER_PYTHON),
                "-u",
                str(HOLDER),
                "--target-used-gib",
                os.environ.get("STAGE2_GPU_HOLDER_TARGET_GIB", "166.5"),
                "--min-free-gib",
                os.environ.get("STAGE2_GPU_HOLDER_MIN_FREE_GIB", "96"),
                "--heartbeat-seconds",
                str(heartbeat_seconds),
            ],
            cwd=ROOT,
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
    )
    handle.close()
    return process


def common_runner_environment(local_gpu: int, gpu_uuid: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONUNBUFFERED": "1",
            "XONOTIC_CAPTURE_ROOT": str(ROOT),
            "XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG": "capture-ee4c0aac65db-aarch64",
            "XONOTIC_STAGE2_MOTION_INTERACTION_SOURCE_COMMIT": "ee4c0aac65dbac689904b320c7db4e43dfd93d20",
            "XONOTIC_BUILD_GLOB": "build/capture-ee4c0aac65db-aarch64",
            "XONOTIC_OFFLINE_ACCELERATE": "1",
            "XONOTIC_LIVE_TIME_SCALE": os.environ.get(
                "XONOTIC_LIVE_TIME_SCALE", "2"
            ),
            "XONOTIC_ALLOW_LIVE_TIME_SCALE_ONE_VALIDATION": "0",
            "XONOTIC_LIVE_CONCURRENCY": os.environ.get(
                "XONOTIC_LIVE_CONCURRENCY", "8"
            ),
            "XONOTIC_RENDER_CONCURRENCY": os.environ.get(
                "XONOTIC_RENDER_CONCURRENCY", "8"
            ),
            "XONOTIC_SDL_CONCURRENCY": os.environ.get(
                "XONOTIC_SDL_CONCURRENCY", "8"
            ),
            "XONOTIC_ENCODE_CONCURRENCY": os.environ.get(
                "XONOTIC_ENCODE_CONCURRENCY", "8"
            ),
            "XONOTIC_X264_THREADS": os.environ.get("XONOTIC_X264_THREADS", "4"),
            "XONOTIC_LIVE_TIMEOUT_SECONDS": os.environ.get(
                "XONOTIC_LIVE_TIMEOUT_SECONDS", "240"
            ),
            "XONOTIC_RENDER_TIMEOUT_SECONDS": os.environ.get(
                "XONOTIC_RENDER_TIMEOUT_SECONDS", "240"
            ),
            "XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS": os.environ.get(
                "XONOTIC_RESIDENT_CONTROL_TIMEOUT_SECONDS", "240"
            ),
            "XONOTIC_RENDER_STARTUP_STALL_SECONDS": os.environ.get(
                "XONOTIC_RENDER_STARTUP_STALL_SECONDS", "90"
            ),
            "XONOTIC_PILOT_RENDER_ATTEMPTS": os.environ.get(
                "XONOTIC_PILOT_RENDER_ATTEMPTS", "1"
            ),
            "SDL_VIDEODRIVER": "offscreen",
            "SDL_AUDIODRIVER": "dummy",
            "SDL_RENDER_DRIVER": "opengl",
            "STAGE2_SELECTED_GPU_INDEX": str(local_gpu),
            "SDL_HINT_EGL_DEVICE": str(local_gpu),
            "CUDA_VISIBLE_DEVICES": gpu_uuid,
            "XONOTIC_CAPTURE_CLIENT_OVERLAY": str(CROSSHAIR_OVERLAY),
        }
    )
    return environment


def supervise_gpu(
    *,
    local_gpu: int,
    logical_shard: int,
    gpu_uuid: str,
    cpu_set: str,
    manifest_root: Path,
    output_root: Path,
    scratch_base: Path,
    log_root: Path,
    workers: int,
    logical_world: int,
    heartbeat_seconds: int,
) -> None:
    holder: subprocess.Popen[bytes] | None = None
    runner: subprocess.Popen[bytes] | None = None
    try:
        holder_log = log_root / "gpu_memory_holder.log"
        holder = start_holder(gpu_uuid, holder_log, heartbeat_seconds)
        print(
            f"stage2_v14_gpu_holder_start shard={logical_shard} "
            f"local_gpu={local_gpu} pid={holder.pid}",
            flush=True,
        )
        environment = common_runner_environment(local_gpu, gpu_uuid)
        for category_index, category in enumerate(CATEGORIES):
            attempt = 0
            while not STOP.is_set():
                if holder.poll() is not None:
                    unregister(holder)
                    holder = start_holder(gpu_uuid, holder_log, heartbeat_seconds)
                    print(
                        f"stage2_v14_gpu_holder_restart shard={logical_shard} "
                        f"pid={holder.pid}",
                        flush=True,
                    )
                rank_tag = f"{logical_shard:03d}"
                manifest = (
                    manifest_root
                    / "categories"
                    / category
                    / "shards-028"
                    / f"shard-{rank_tag}-of-028.jsonl"
                )
                category_output = output_root / category
                category_scratch = (
                    scratch_base
                    / output_root.name
                    / category
                    / f"shard_{rank_tag}"
                )
                category_scratch.mkdir(parents=True, exist_ok=True)
                run_log = log_root / f"run_{category}.log"
                attempt += 1
                command = [
                    "taskset",
                    "-c",
                    cpu_set,
                    str(PYTHON),
                    "-u",
                    str(RUNNER),
                    "--manifest",
                    str(manifest),
                    "--metadata",
                    str(manifest_root / "MANIFEST_METADATA.json"),
                    "--output-root",
                    str(category_output),
                    "--scratch-root",
                    str(category_scratch),
                    "--shard-index",
                    str(logical_shard),
                    "--shard-count",
                    str(logical_world),
                    "--workers",
                    str(workers),
                    "--live-concurrency",
                    environment["XONOTIC_LIVE_CONCURRENCY"],
                    "--render-concurrency",
                    environment["XONOTIC_RENDER_CONCURRENCY"],
                    "--encode-concurrency",
                    environment["XONOTIC_ENCODE_CONCURRENCY"],
                    "--x264-threads",
                    environment["XONOTIC_X264_THREADS"],
                    "--port-base",
                    str(26000 + logical_shard * 100),
                    "--max-operational-attempts",
                    "2",
                    "--fail-on-incomplete",
                ]
                print(
                    f"stage2_v14_category_attempt shard={logical_shard}/{logical_world} "
                    f"category={category} attempt={attempt}",
                    flush=True,
                )
                handle = run_log.open("ab", buffering=0)
                runner = register(
                    subprocess.Popen(
                        command,
                        cwd=ROOT,
                        env=environment,
                        stdout=handle,
                        stderr=subprocess.STDOUT,
                    )
                )
                handle.close()
                while not STOP.wait(5):
                    if runner.poll() is not None:
                        break
                    if holder.poll() is not None:
                        unregister(holder)
                        holder = start_holder(gpu_uuid, holder_log, heartbeat_seconds)
                        print(
                            f"stage2_v14_gpu_holder_restart shard={logical_shard} "
                            f"pid={holder.pid}",
                            flush=True,
                        )
                if STOP.is_set():
                    terminate(runner)
                    unregister(runner)
                    return
                return_code = runner.wait()
                unregister(runner)
                runner = None
                if return_code == 0:
                    print(
                        f"stage2_v14_category_complete shard={logical_shard} "
                        f"category={category}",
                        flush=True,
                    )
                    break
                delay = min(300, 30 * attempt)
                print(
                    f"stage2_v14_category_retry shard={logical_shard} "
                    f"category={category} rc={return_code} delay={delay}",
                    flush=True,
                )
                STOP.wait(delay)
        while not STOP.wait(heartbeat_seconds):
            if holder.poll() is not None:
                unregister(holder)
                holder = start_holder(gpu_uuid, holder_log, heartbeat_seconds)
            print(
                f"stage2_v14_shard_idle_heartbeat shard={logical_shard} "
                "reason=all_categories_complete",
                flush=True,
            )
    except Exception as exc:
        print(
            f"stage2_v14_supervisor_error shard={logical_shard} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )
        while not STOP.wait(heartbeat_seconds):
            print(
                f"stage2_v14_supervisor_hold shard={logical_shard} "
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
    finally:
        terminate(runner)
        if runner is not None:
            unregister(runner)
        terminate(holder)
        if holder is not None:
            unregister(holder)


def main() -> int:
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    run_id = os.environ.get(
        "RUN_ID",
        "stage2_motion_temporal_visibility_42k_v14r4_near_exit_90_5_5_nocrosshair_28gpu_20260820_01",
    )
    if not run_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in run_id):
        raise RuntimeError(f"invalid RUN_ID: {run_id!r}")
    expected_nodes = integer_env("STAGE2_EXPECTED_NODES", 7)
    gpus_per_node = integer_env("STAGE2_GPUS_PER_NODE", 4)
    workers = integer_env("STAGE2_WORKERS_PER_GPU", 8)
    physical_world = integer_env("WORLD_SIZE", -1)
    physical_rank = integer_env("RANK", -1)
    if physical_world != expected_nodes or gpus_per_node != 4:
        raise RuntimeError(
            f"topology mismatch world={physical_world}/{expected_nodes} "
            f"gpus_per_node={gpus_per_node}"
        )
    if not 0 <= physical_rank < physical_world:
        raise RuntimeError(f"invalid rank: {physical_rank}/{physical_world}")
    if not 1 <= workers <= 16:
        raise RuntimeError(f"invalid workers: {workers}")
    for path in (
        PYTHON,
        HOLDER_PYTHON,
        RUNNER,
        HOLDER,
        RUNTIME_LOCK,
        CROSSHAIR_OVERLAY,
    ):
        if not path.is_file():
            raise RuntimeError(f"missing runtime file: {path}")
    subprocess.run(
        ["sha256sum", "-c", str(RUNTIME_LOCK), "--quiet"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [str(HOLDER_PYTHON), "-c", "import torch; assert torch.version.cuda"],
        check=True,
    )

    rows = gpu_rows()
    if len(rows) != gpus_per_node or any(row[0] != index for index, row in enumerate(rows)):
        raise RuntimeError(f"unexpected GPU topology: {rows}")
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) < gpus_per_node * 8:
        raise RuntimeError(f"insufficient CPUs: {len(cpus)}")
    cpu_sets = [
        ",".join(str(cpu) for cpu in cpus[index::gpus_per_node])
        for index in range(gpus_per_node)
    ]
    manifest_root = Path(
        os.environ.get(
            "STAGE2_MANIFEST_ROOT",
            str(
                ROOT
                / "manifests/stage2_motion_temporal_visibility_42k_v14_near_exit_90_5_5_nocrosshair_28shard_20260820_r4"
            ),
        )
    ).resolve()
    output_root = Path(
        os.environ.get(
            "STAGE2_OUTPUT_ROOT", str(ROOT / "production_runs" / run_id)
        )
    ).resolve()
    scratch_base = Path(
        os.environ.get("STAGE2_SCRATCH_BASE", "./tmp/xonotic-stage2-motion-v14-7x4")
    )
    logical_world = expected_nodes * gpus_per_node
    heartbeat_seconds = integer_env("STAGE2_HEARTBEAT_SECONDS", 60)
    for local_gpu in range(gpus_per_node):
        logical_shard = physical_rank * gpus_per_node + local_gpu
        for category in CATEGORIES:
            manifest = (
                manifest_root
                / "categories"
                / category
                / "shards-028"
                / f"shard-{logical_shard:03d}-of-028.jsonl"
            )
            if not manifest.is_file():
                raise RuntimeError(f"missing manifest: {manifest}")

    node_log_root = ROOT / "logs" / run_id / f"node_{physical_rank:02d}"
    node_log_root.mkdir(parents=True, exist_ok=True)
    print(
        f"stage2_v14_node_start run_id={run_id} rank={physical_rank}/{physical_world} "
        f"logical_world={logical_world} output_root={output_root}",
        flush=True,
    )
    threads: list[threading.Thread] = []
    for local_gpu, (_, gpu_uuid, gpu_name) in enumerate(rows):
        logical_shard = physical_rank * gpus_per_node + local_gpu
        shard_log_root = ROOT / "logs" / run_id / f"shard_{logical_shard:03d}"
        shard_log_root.mkdir(parents=True, exist_ok=True)
        print(
            f"stage2_v14_gpu_binding local_gpu={local_gpu} "
            f"logical_shard={logical_shard} uuid={gpu_uuid} name={gpu_name} "
            f"cpuset={cpu_sets[local_gpu]}",
            flush=True,
        )
        thread = threading.Thread(
            target=supervise_gpu,
            kwargs={
                "local_gpu": local_gpu,
                "logical_shard": logical_shard,
                "gpu_uuid": gpu_uuid,
                "cpu_set": cpu_sets[local_gpu],
                "manifest_root": manifest_root,
                "output_root": output_root,
                "scratch_base": scratch_base,
                "log_root": shard_log_root,
                "workers": workers,
                "logical_world": logical_world,
                "heartbeat_seconds": heartbeat_seconds,
            },
            name=f"stage2-v14-gpu-{local_gpu}",
            daemon=False,
        )
        thread.start()
        threads.append(thread)
    try:
        while not STOP.wait(heartbeat_seconds):
            alive = sum(thread.is_alive() for thread in threads)
            print(
                f"stage2_v14_node_heartbeat rank={physical_rank} "
                f"supervisors_alive={alive}/{len(threads)}",
                flush=True,
            )
            if alive != len(threads):
                raise RuntimeError(f"supervisor thread exited: {alive}/{len(threads)}")
    finally:
        STOP.set()
        with CHILDREN_LOCK:
            children = list(CHILDREN)
        for process in children:
            terminate(process)
        for thread in threads:
            thread.join(timeout=30)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"stage2_v14_node_fatal {type(exc).__name__}: {exc}", flush=True)
        while not STOP.wait(60):
            print(
                f"stage2_v14_node_hold {type(exc).__name__}: {exc}",
                flush=True,
            )
