                      
"""Run the immutable 28-shard Stage-2 short v15 release on 4 x 4 GPUs.

The manifest remains byte-for-byte identical to the audited 7 x 4 release.
Sixteen physical GPU supervisors consume the 28 logical shards in a static
strided assignment; twelve GPUs process two shards and four process one.  All
GPUs stay reserved after their assigned work finishes.
"""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import launch_dlc_7x4_stage2_short_v15_resilient as v15


base = v15.base
ROOT = v15.ROOT
MANIFEST_ROOT = v15.MANIFEST_ROOT
PHYSICAL_NODES = 4
GPUS_PER_NODE = 4
PHYSICAL_GPUS = PHYSICAL_NODES * GPUS_PER_NODE
LOGICAL_SHARDS = 28
DEFAULT_RUN_ID = "stage2_short_42k_v15_random_fire_visualfix_16gpu_20260824_01"
LAUNCH_LOCK = ROOT / "locks/stage2_short_4x4_v15r1_launcher.sha256"


def assigned_shards(physical_slot: int) -> list[int]:
    if not 0 <= physical_slot < PHYSICAL_GPUS:
        raise RuntimeError(f"invalid physical slot: {physical_slot}")
    return list(range(physical_slot, LOGICAL_SHARDS, PHYSICAL_GPUS))


def ensure_holder(
    holder: subprocess.Popen[bytes] | None,
    gpu_uuid: str,
    holder_log: Path,
    heartbeat_seconds: int,
) -> subprocess.Popen[bytes]:
    if holder is not None and holder.poll() is None:
        return holder
    if holder is not None:
        base.unregister(holder)
    replacement = base.start_holder(gpu_uuid, holder_log, heartbeat_seconds)
    print(f"stage2_v15_4x4_gpu_holder_start pid={replacement.pid}", flush=True)
    return replacement


def run_category(
    *,
    local_gpu: int,
    physical_slot: int,
    logical_shard: int,
    category: str,
    gpu_uuid: str,
    cpu_set: str,
    manifest_root: Path,
    output_root: Path,
    scratch_base: Path,
    log_root: Path,
    workers: int,
    heartbeat_seconds: int,
    holder: subprocess.Popen[bytes],
) -> subprocess.Popen[bytes]:
    environment = base.common_runner_environment(local_gpu, gpu_uuid)
    manifest = (
        manifest_root
        / "categories"
        / category
        / "shards-028"
        / f"shard-{logical_shard:03d}-of-028.jsonl"
    )
    category_output = output_root / category
    category_scratch = (
        scratch_base
        / output_root.name
        / category
        / f"shard_{logical_shard:03d}"
    )
    category_scratch.mkdir(parents=True, exist_ok=True)
    run_log = log_root / f"run_{category}.log"
    attempt = 0
    while not base.STOP.is_set():
        runner: subprocess.Popen[bytes] | None = None
        try:
            holder = ensure_holder(
                holder,
                gpu_uuid,
                log_root / "gpu_memory_holder.log",
                heartbeat_seconds,
            )
            attempt += 1
            command = [
                "taskset",
                "-c",
                cpu_set,
                str(base.PYTHON),
                "-u",
                str(base.RUNNER),
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
                str(LOGICAL_SHARDS),
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
                str(26000 + local_gpu * 100),
                "--max-operational-attempts",
                "2",
                "--fail-on-incomplete",
            ]
            print(
                "stage2_v15_4x4_category_attempt "
                f"slot={physical_slot}/{PHYSICAL_GPUS} "
                f"shard={logical_shard}/{LOGICAL_SHARDS} "
                f"category={category} attempt={attempt}",
                flush=True,
            )
            handle = run_log.open("ab", buffering=0)
            try:
                runner = base.register(
                    subprocess.Popen(
                        command,
                        cwd=ROOT,
                        env=environment,
                        stdout=handle,
                        stderr=subprocess.STDOUT,
                    )
                )
            finally:
                handle.close()
            while not base.STOP.wait(5):
                if runner.poll() is not None:
                    break
                holder = ensure_holder(
                    holder,
                    gpu_uuid,
                    log_root / "gpu_memory_holder.log",
                    heartbeat_seconds,
                )
            if base.STOP.is_set():
                base.terminate(runner)
                base.unregister(runner)
                runner = None
                return holder
            return_code = runner.wait()
            base.unregister(runner)
            runner = None
            if return_code == 0:
                print(
                    "stage2_v15_4x4_category_complete "
                    f"shard={logical_shard} category={category}",
                    flush=True,
                )
                return holder
            delay = min(300, 30 * attempt)
            print(
                "stage2_v15_4x4_category_retry "
                f"shard={logical_shard} category={category} "
                f"rc={return_code} delay={delay}",
                flush=True,
            )
            base.STOP.wait(delay)
        except BaseException:
            base.terminate(runner)
            if runner is not None:
                base.unregister(runner)
            raise
    return holder


def supervise_gpu_queue(
    *,
    local_gpu: int,
    physical_slot: int,
    logical_shards: list[int],
    gpu_uuid: str,
    cpu_set: str,
    manifest_root: Path,
    output_root: Path,
    scratch_base: Path,
    workers: int,
    heartbeat_seconds: int,
    run_id: str,
) -> None:
    holder: subprocess.Popen[bytes] | None = None
    runner_log_root: Path | None = None
    try:
        first_log_root = ROOT / "logs" / run_id / f"shard_{logical_shards[0]:03d}"
        first_log_root.mkdir(parents=True, exist_ok=True)
        holder = ensure_holder(
            holder,
            gpu_uuid,
            first_log_root / "gpu_memory_holder.log",
            heartbeat_seconds,
        )
        for logical_shard in logical_shards:
            runner_log_root = ROOT / "logs" / run_id / f"shard_{logical_shard:03d}"
            runner_log_root.mkdir(parents=True, exist_ok=True)
            print(
                "stage2_v15_4x4_shard_start "
                f"slot={physical_slot} shard={logical_shard} "
                f"queue={logical_shards}",
                flush=True,
            )
            for category in base.CATEGORIES:
                holder = run_category(
                    local_gpu=local_gpu,
                    physical_slot=physical_slot,
                    logical_shard=logical_shard,
                    category=category,
                    gpu_uuid=gpu_uuid,
                    cpu_set=cpu_set,
                    manifest_root=manifest_root,
                    output_root=output_root,
                    scratch_base=scratch_base,
                    log_root=runner_log_root,
                    workers=workers,
                    heartbeat_seconds=heartbeat_seconds,
                    holder=holder,
                )
                if base.STOP.is_set():
                    return
            print(
                f"stage2_v15_4x4_shard_complete shard={logical_shard}",
                flush=True,
            )
        while not base.STOP.wait(heartbeat_seconds):
            holder = ensure_holder(
                holder,
                gpu_uuid,
                (runner_log_root or first_log_root) / "gpu_memory_holder.log",
                heartbeat_seconds,
            )
            print(
                "stage2_v15_4x4_slot_idle_heartbeat "
                f"slot={physical_slot} shards={logical_shards} "
                "reason=all_assigned_shards_complete",
                flush=True,
            )
    except Exception as exc:
        print(
            "stage2_v15_4x4_supervisor_error "
            f"slot={physical_slot} error={type(exc).__name__}:{exc}",
            flush=True,
        )
        while not base.STOP.wait(heartbeat_seconds):
            print(
                "stage2_v15_4x4_supervisor_hold "
                f"slot={physical_slot} error={type(exc).__name__}:{exc}",
                flush=True,
            )
    finally:
        base.terminate(holder)
        if holder is not None:
            base.unregister(holder)


def main() -> int:
    import signal

    signal.signal(signal.SIGTERM, base.on_signal)
    signal.signal(signal.SIGINT, base.on_signal)
    run_id = os.environ.get("RUN_ID", DEFAULT_RUN_ID)
    if not run_id or any(
        char
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for char in run_id
    ):
        raise RuntimeError(f"invalid RUN_ID: {run_id!r}")
    expected_nodes = base.integer_env("STAGE2_EXPECTED_NODES", PHYSICAL_NODES)
    gpus_per_node = base.integer_env("STAGE2_GPUS_PER_NODE", GPUS_PER_NODE)
    workers = base.integer_env("STAGE2_WORKERS_PER_GPU", 8)
    physical_world = base.integer_env("WORLD_SIZE", -1)
    physical_rank = base.integer_env("RANK", -1)
    logical_shards = base.integer_env("STAGE2_LOGICAL_SHARDS", LOGICAL_SHARDS)
    if (
        expected_nodes != PHYSICAL_NODES
        or physical_world != PHYSICAL_NODES
        or gpus_per_node != GPUS_PER_NODE
        or logical_shards != LOGICAL_SHARDS
    ):
        raise RuntimeError(
            "topology mismatch "
            f"world={physical_world}/{PHYSICAL_NODES} "
            f"gpus={gpus_per_node}/{GPUS_PER_NODE} "
            f"logical={logical_shards}/{LOGICAL_SHARDS}"
        )
    if not 0 <= physical_rank < physical_world:
        raise RuntimeError(f"invalid rank: {physical_rank}/{physical_world}")
    if not 1 <= workers <= 16:
        raise RuntimeError(f"invalid workers: {workers}")
    for path in (
        base.PYTHON,
        base.HOLDER_PYTHON,
        base.RUNNER,
        base.HOLDER,
        base.RUNTIME_LOCK,
        base.CROSSHAIR_OVERLAY,
        LAUNCH_LOCK,
    ):
        if not path.is_file():
            raise RuntimeError(f"missing runtime file: {path}")
    subprocess.run(
        ["sha256sum", "-c", str(base.RUNTIME_LOCK), "--quiet"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["sha256sum", "-c", str(LAUNCH_LOCK), "--quiet"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [str(base.HOLDER_PYTHON), "-c", "import torch; assert torch.version.cuda"],
        check=True,
    )

    rows = base.gpu_rows()
    if len(rows) != GPUS_PER_NODE or any(
        row[0] != index for index, row in enumerate(rows)
    ):
        raise RuntimeError(f"unexpected GPU topology: {rows}")
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) < GPUS_PER_NODE * 8:
        raise RuntimeError(f"insufficient CPUs: {len(cpus)}")
    cpu_sets = [
        ",".join(str(cpu) for cpu in cpus[index::GPUS_PER_NODE])
        for index in range(GPUS_PER_NODE)
    ]
    manifest_root = Path(
        os.environ.get("STAGE2_MANIFEST_ROOT", str(MANIFEST_ROOT))
    ).resolve()
    output_root = Path(
        os.environ.get(
            "STAGE2_OUTPUT_ROOT", str(ROOT / "production_runs" / run_id)
        )
    ).resolve()
    scratch_base = Path(
        os.environ.get("STAGE2_SCRATCH_BASE", "./tmp/xonotic-stage2-short-v15-4x4")
    )
    heartbeat_seconds = base.integer_env("STAGE2_HEARTBEAT_SECONDS", 60)

    node_assignments: dict[int, list[int]] = {}
    for local_gpu in range(GPUS_PER_NODE):
        physical_slot = physical_rank * GPUS_PER_NODE + local_gpu
        queue = assigned_shards(physical_slot)
        node_assignments[local_gpu] = queue
        for logical_shard in queue:
            for category in base.CATEGORIES:
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
        "stage2_v15_4x4_node_start "
        f"run_id={run_id} rank={physical_rank}/{physical_world} "
        f"assignments={node_assignments} output_root={output_root}",
        flush=True,
    )
    threads: list[threading.Thread] = []
    for local_gpu, (_, gpu_uuid, gpu_name) in enumerate(rows):
        physical_slot = physical_rank * GPUS_PER_NODE + local_gpu
        queue = node_assignments[local_gpu]
        print(
            "stage2_v15_4x4_gpu_binding "
            f"local_gpu={local_gpu} physical_slot={physical_slot} "
            f"logical_shards={queue} uuid={gpu_uuid} name={gpu_name} "
            f"cpuset={cpu_sets[local_gpu]}",
            flush=True,
        )
        thread = threading.Thread(
            target=supervise_gpu_queue,
            kwargs={
                "local_gpu": local_gpu,
                "physical_slot": physical_slot,
                "logical_shards": queue,
                "gpu_uuid": gpu_uuid,
                "cpu_set": cpu_sets[local_gpu],
                "manifest_root": manifest_root,
                "output_root": output_root,
                "scratch_base": scratch_base,
                "workers": workers,
                "heartbeat_seconds": heartbeat_seconds,
                "run_id": run_id,
            },
            name=f"stage2-v15-4x4-gpu-{local_gpu}",
            daemon=False,
        )
        thread.start()
        threads.append(thread)
    try:
        while not base.STOP.wait(heartbeat_seconds):
            alive = sum(thread.is_alive() for thread in threads)
            print(
                "stage2_v15_4x4_node_heartbeat "
                f"rank={physical_rank} supervisors_alive={alive}/{len(threads)}",
                flush=True,
            )
            if alive != len(threads):
                raise RuntimeError(
                    f"supervisor thread exited: {alive}/{len(threads)}"
                )
    finally:
        base.STOP.set()
        with base.CHILDREN_LOCK:
            children = list(base.CHILDREN)
        for process in children:
            base.terminate(process)
        for thread in threads:
            thread.join(timeout=30)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"stage2_v15_4x4_node_fatal {type(exc).__name__}: {exc}",
            flush=True,
        )
        while not base.STOP.wait(60):
            print(
                f"stage2_v15_4x4_node_hold {type(exc).__name__}: {exc}",
                flush=True,
            )
