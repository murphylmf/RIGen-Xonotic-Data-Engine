                      
"""Run a frozen 24-lane Stage-2 short v15 tail plan on 6 x 4 GPUs."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Any

import launch_dlc_7x4_stage2_short_v15_resilient as v15


base = v15.base
ROOT = v15.ROOT
RUNNER = ROOT / "production_scripts/run_stage2_short_42k_activeonly_v15_rebalance_lane.py"
LAUNCH_LOCK = ROOT / "locks/stage2_short_v15_rebalance_6x4_runtime.sha256"
PHYSICAL_NODES = 6
GPUS_PER_NODE = 4
PHYSICAL_LANES = PHYSICAL_NODES * GPUS_PER_NODE
PLAN_SCHEMA = "xonotic-stage2-short-v15-rebalance-plan-v1"
DEFAULT_RUN_ID = "stage2_short_42k_v15_random_fire_visualfix_24gpu_rebalance_20260825_01"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_holder(
    holder: subprocess.Popen[bytes] | None,
    gpu_uuid: str,
    log_path: Path,
    heartbeat_seconds: int,
) -> subprocess.Popen[bytes]:
    if holder is not None and holder.poll() is None:
        return holder
    if holder is not None:
        base.unregister(holder)
    replacement = base.start_holder(gpu_uuid, log_path, heartbeat_seconds)
    print(f"stage2_v15_rebalance_holder_start pid={replacement.pid}", flush=True)
    return replacement


def supervise_lane(
    *,
    local_gpu: int,
    lane: dict[str, Any],
    gpu_uuid: str,
    cpu_set: str,
    metadata_path: Path,
    output_root: Path,
    scratch_base: Path,
    log_root: Path,
    workers: int,
    heartbeat_seconds: int,
) -> None:
    lane_id = int(lane["lane_id"])
    original_shard = int(lane["original_shard"])
    holder: subprocess.Popen[bytes] | None = None
    runner: subprocess.Popen[bytes] | None = None
    try:
        holder_log = log_root / "gpu_memory_holder.log"
        holder = ensure_holder(holder, gpu_uuid, holder_log, heartbeat_seconds)
        environment = v15.common_runner_environment(local_gpu, gpu_uuid)
        environment.update(
            {
                "STAGE2_REBALANCE_LANE_FILE": str(Path(lane["path"]).resolve()),
                "STAGE2_REBALANCE_LANE_SHA256": str(lane["sha256"]),
                "STAGE2_REBALANCE_LANE_ID": str(lane_id),
            }
        )
        lane_output = output_root / "lanes" / f"lane_{lane_id:03d}"
        lane_scratch = scratch_base / output_root.name / f"lane_{lane_id:03d}"
        lane_scratch.mkdir(parents=True, exist_ok=True)
        run_log = log_root / "run_always_visible.log"
        attempt = 0
        while not base.STOP.is_set():
            holder = ensure_holder(holder, gpu_uuid, holder_log, heartbeat_seconds)
            attempt += 1
            command = [
                "taskset",
                "-c",
                cpu_set,
                str(base.PYTHON),
                "-u",
                str(RUNNER),
                "--manifest",
                str(Path(lane["source_manifest"]).resolve()),
                "--metadata",
                str(metadata_path),
                "--output-root",
                str(lane_output),
                "--scratch-root",
                str(lane_scratch),
                "--shard-index",
                str(original_shard),
                "--shard-count",
                "28",
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
                "stage2_v15_rebalance_lane_attempt "
                f"lane={lane_id}/{PHYSICAL_LANES} shard={original_shard} "
                f"target={lane['target_accepted_rows']} "
                f"candidates={lane['candidate_rows']} attempt={attempt}",
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
                holder = ensure_holder(holder, gpu_uuid, holder_log, heartbeat_seconds)
            if base.STOP.is_set():
                base.terminate(runner)
                base.unregister(runner)
                runner = None
                return
            return_code = runner.wait()
            base.unregister(runner)
            runner = None
            if return_code == 0:
                print(
                    f"stage2_v15_rebalance_lane_complete lane={lane_id} "
                    f"shard={original_shard}",
                    flush=True,
                )
                break
            delay = min(300, 30 * attempt)
            print(
                f"stage2_v15_rebalance_lane_retry lane={lane_id} "
                f"shard={original_shard} rc={return_code} delay={delay}",
                flush=True,
            )
            base.STOP.wait(delay)
        while not base.STOP.wait(heartbeat_seconds):
            holder = ensure_holder(holder, gpu_uuid, holder_log, heartbeat_seconds)
            print(
                f"stage2_v15_rebalance_lane_idle lane={lane_id} "
                "reason=accepted_target_complete",
                flush=True,
            )
    except Exception as exc:
        print(
            f"stage2_v15_rebalance_lane_error lane={lane_id} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )
        while not base.STOP.wait(heartbeat_seconds):
            print(
                f"stage2_v15_rebalance_lane_hold lane={lane_id} "
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
    finally:
        base.terminate(runner)
        if runner is not None:
            base.unregister(runner)
        base.terminate(holder)
        if holder is not None:
            base.unregister(holder)


def main() -> int:
    signal.signal(signal.SIGTERM, base.on_signal)
    signal.signal(signal.SIGINT, base.on_signal)
    run_id = os.environ.get("RUN_ID", DEFAULT_RUN_ID)
    if not run_id or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for char in run_id
    ):
        raise RuntimeError(f"invalid RUN_ID: {run_id!r}")
    expected_nodes = base.integer_env("STAGE2_EXPECTED_NODES", PHYSICAL_NODES)
    gpus_per_node = base.integer_env("STAGE2_GPUS_PER_NODE", GPUS_PER_NODE)
    workers = base.integer_env("STAGE2_WORKERS_PER_GPU", 8)
    physical_world = base.integer_env("WORLD_SIZE", -1)
    physical_rank = base.integer_env("RANK", -1)
    if (
        expected_nodes != PHYSICAL_NODES
        or physical_world != PHYSICAL_NODES
        or gpus_per_node != GPUS_PER_NODE
    ):
        raise RuntimeError(
            f"topology mismatch world={physical_world}/{PHYSICAL_NODES} "
            f"nodes={expected_nodes}/{PHYSICAL_NODES} "
            f"gpus={gpus_per_node}/{GPUS_PER_NODE}"
        )
    if not 0 <= physical_rank < physical_world:
        raise RuntimeError(f"invalid rank: {physical_rank}/{physical_world}")
    if not 1 <= workers <= 16:
        raise RuntimeError(f"invalid workers: {workers}")

    plan_root = Path(os.environ.get("STAGE2_REBALANCE_PLAN_ROOT", "")).resolve()
    plan_path = plan_root / "PLAN.json"
    expected_plan_sha256 = os.environ.get("STAGE2_REBALANCE_PLAN_SHA256", "")
    if not plan_path.is_file() or not expected_plan_sha256:
        raise RuntimeError(f"missing frozen rebalance plan or hash: {plan_path}")
    if sha256_file(plan_path) != expected_plan_sha256:
        raise RuntimeError("rebalance plan hash mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if (
        plan.get("schema_version") != PLAN_SCHEMA
        or int(plan.get("physical_lanes", -1)) != PHYSICAL_LANES
        or len(plan.get("lanes", [])) != PHYSICAL_LANES
        or int(plan.get("source_accepted_total", -1))
        + int(plan.get("remaining_target_total", -1))
        != 42_000
    ):
        raise RuntimeError("invalid rebalance plan contract")
    lanes = sorted(plan["lanes"], key=lambda value: int(value["lane_id"]))
    if [int(lane["lane_id"]) for lane in lanes] != list(range(PHYSICAL_LANES)):
        raise RuntimeError("rebalance lane ids are not contiguous")
    for lane in lanes:
        lane_path = Path(lane["path"]).resolve()
        if not lane_path.is_file() or sha256_file(lane_path) != lane["sha256"]:
            raise RuntimeError(f"rebalance lane drift: {lane_path}")
    metadata_path = Path(plan["manifest_metadata"]).resolve()
    if (
        not metadata_path.is_file()
        or sha256_file(metadata_path) != plan["manifest_metadata_sha256"]
    ):
        raise RuntimeError(f"rebalance manifest metadata drift: {metadata_path}")
    for snapshot in plan.get("source_journal_snapshots", []):
        for journal_name in ("accepted", "rejected"):
            journal = snapshot[journal_name]
            path = Path(journal["path"]).resolve()
            if bool(journal["exists"]) != path.is_file():
                raise RuntimeError(f"source journal existence drift: {path}")
            if journal["exists"] and sha256_file(path) != journal["sha256"]:
                raise RuntimeError(f"source journal hash drift: {path}")

    for path in (
        base.PYTHON,
        base.HOLDER_PYTHON,
        base.HOLDER,
        RUNNER,
        v15.base.RUNTIME_LOCK,
        LAUNCH_LOCK,
        v15.OVERLAY,
    ):
        if not path.is_file():
            raise RuntimeError(f"missing runtime file: {path}")
    subprocess.run(
        ["sha256sum", "-c", str(v15.base.RUNTIME_LOCK), "--quiet"],
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

    gpu_rows = base.gpu_rows()
    if len(gpu_rows) != GPUS_PER_NODE or any(
        row[0] != index for index, row in enumerate(gpu_rows)
    ):
        raise RuntimeError(f"unexpected GPU topology: {gpu_rows}")
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) < GPUS_PER_NODE * 8:
        raise RuntimeError(f"insufficient CPUs: {len(cpus)}")
    cpu_sets = [
        ",".join(str(cpu) for cpu in cpus[index::GPUS_PER_NODE])
        for index in range(GPUS_PER_NODE)
    ]
    output_root = Path(
        os.environ.get(
            "STAGE2_REBALANCE_OUTPUT_ROOT",
            str(ROOT / "production_runs" / run_id),
        )
    ).resolve()
    scratch_base = Path(
        os.environ.get(
            "STAGE2_SCRATCH_BASE", "./tmp/xonotic-stage2-short-v15-6x4-rebalance"
        )
    )
    heartbeat_seconds = base.integer_env("STAGE2_HEARTBEAT_SECONDS", 60)

    node_log_root = ROOT / "logs" / run_id / f"node_{physical_rank:02d}"
    node_log_root.mkdir(parents=True, exist_ok=True)
    print(
        "stage2_v15_rebalance_node_start "
        f"run_id={run_id} rank={physical_rank}/{physical_world} "
        f"plan={plan_path} output_root={output_root}",
        flush=True,
    )
    threads: list[threading.Thread] = []
    for local_gpu, (_, gpu_uuid, gpu_name) in enumerate(gpu_rows):
        lane_id = physical_rank * GPUS_PER_NODE + local_gpu
        lane = lanes[lane_id]
        log_root = ROOT / "logs" / run_id / f"lane_{lane_id:03d}"
        log_root.mkdir(parents=True, exist_ok=True)
        print(
            "stage2_v15_rebalance_gpu_binding "
            f"local_gpu={local_gpu} lane={lane_id} "
            f"original_shard={lane['original_shard']} "
            f"target={lane['target_accepted_rows']} "
            f"uuid={gpu_uuid} name={gpu_name} cpuset={cpu_sets[local_gpu]}",
            flush=True,
        )
        thread = threading.Thread(
            target=supervise_lane,
            kwargs={
                "local_gpu": local_gpu,
                "lane": lane,
                "gpu_uuid": gpu_uuid,
                "cpu_set": cpu_sets[local_gpu],
                "metadata_path": metadata_path,
                "output_root": output_root,
                "scratch_base": scratch_base,
                "log_root": log_root,
                "workers": workers,
                "heartbeat_seconds": heartbeat_seconds,
            },
            name=f"stage2-v15-rebalance-lane-{lane_id:03d}",
            daemon=False,
        )
        thread.start()
        threads.append(thread)
    try:
        while not base.STOP.wait(heartbeat_seconds):
            alive = sum(thread.is_alive() for thread in threads)
            print(
                f"stage2_v15_rebalance_node_heartbeat rank={physical_rank} "
                f"supervisors_alive={alive}/{len(threads)}",
                flush=True,
            )
            if alive != len(threads):
                raise RuntimeError(f"supervisor thread exited: {alive}/{len(threads)}")
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
            f"stage2_v15_rebalance_node_fatal {type(exc).__name__}: {exc}",
            flush=True,
        )
        while not base.STOP.wait(60):
            print(
                f"stage2_v15_rebalance_node_hold {type(exc).__name__}: {exc}",
                flush=True,
            )
