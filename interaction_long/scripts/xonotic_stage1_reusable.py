                      
"""Resident Stage-1 capture lane with hard per-episode world resets.

Only safe process-level resources are reused.  Every episode receives:

* a fresh server VM/world through ``restart`` or ``map``;
* a fresh live network connection and demo recording;
* a fresh demo playback client when accelerated live time is enabled;
* unique action, telemetry, frame, audio, and raw-video paths.

The formal worker may use this lane only through its fail-closed scheduler:
one exact ``(map, gametype)`` group per lane lifetime, a fresh server
VM/world reset for every episode, and full lane destruction on any failure or
group change.  The dedicated server and live client remain resident.  At
``XONOTIC_LIVE_TIME_SCALE > 1`` the render client is deliberately recycled
after every demo: demo movevars carry the accelerated server timescale, and a
fresh playback process is the reliable boundary for the reciprocal local
timescale used by the offline renderer.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import xonotic_capture as capture
import xonotic_capture_v2 as capture_v2              
import xonotic_stage1_review as stage1_review              


IDLE_CLIENT_MAXFPS = 8
IDLE_SERVER_TICRATE = 0.05
IDLE_SERVER_SLOWMO = 1
                                                                            
                                                                           
                                          
LIVE_PROCESS_NICE: int | None = None
LIVE_RESERVED_CPUSET_ENV = "XONOTIC_LIVE_RESERVED_CPUSET"
BACKGROUND_CPUSET_ENV = "XONOTIC_BACKGROUND_CPUSET"
LIVE_CAPTURE_WIDTH = 160
LIVE_CAPTURE_HEIGHT = 90
AUTHORITATIVE_TICKS_PER_SECOND = 64
                                                                           
                                                                             
                                                                          
                                                                        
RENDER_EPISODE_SEED_MASK = (1 << 24) - 1
                                                                     
                                                                            
                                                                         
                                                     
RENDER_PREROLL_SEMANTIC_TIME_SCALE = 4.0
FRONTEND_MENU_CLOSE_COMMANDS = (
    "scr_menuforcewhiledisconnected 0",
    "togglemenu 0",
)


class ResidentProcess:
    """A DarkPlaces process controlled through its stdin console."""

    def __init__(
        self,
        command: list[str],
        log_path: Path,
        *,
        label: str,
        cpu_affinity: set[int] | None = None,
        nice_value: int | None = None,
    ) -> None:
        self.command = command
        self.log_path = log_path
        self.label = label
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_handle = self.log_path.open("wb")
        self._log_handle.write(
            (
                f"started_utc={capture.utc_now()}\n"
                f"label={label}\n"
                f"command={json.dumps(command, ensure_ascii=False)}\n"
            ).encode()
        )
        self._log_handle.flush()
        self._closed = False
        self.started_monotonic = time.monotonic()
        launch_command = list(command)
        if cpu_affinity is not None:
            if not cpu_affinity:
                raise capture.CaptureFailure(
                    "resident_process_empty_cpu_affinity", label
                )
            launch_command = [
                "taskset",
                "--cpu-list",
                _format_cpu_set(cpu_affinity),
                *launch_command,
            ]
        self.launch_command = launch_command
        self.process = subprocess.Popen(
            launch_command,
            stdin=subprocess.PIPE,
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            env=capture.process_environment(),
            start_new_session=True,
        )
        try:
            if cpu_affinity is not None:
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline:
                    if self.process.poll() is not None:
                        break
                    if set(os.sched_getaffinity(self.process.pid)) == cpu_affinity:
                        break
                    time.sleep(0.005)
            if nice_value is not None:
                os.setpriority(
                    os.PRIO_PROCESS, self.process.pid, nice_value
                )
            self.cpu_affinity = set(
                os.sched_getaffinity(self.process.pid)
            )
            self.nice_value = os.getpriority(
                os.PRIO_PROCESS, self.process.pid
            )
            if (
                cpu_affinity is not None
                and self.cpu_affinity != cpu_affinity
            ):
                raise RuntimeError(
                    f"affinity expected={sorted(cpu_affinity)} "
                    f"realized={sorted(self.cpu_affinity)}"
                )
            if nice_value is not None and self.nice_value != nice_value:
                raise RuntimeError(
                    f"nice expected={nice_value} realized={self.nice_value}"
                )
        except Exception as exc:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=5)
            except Exception:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except OSError:
                    pass
            raise capture.CaptureFailure(
                "resident_process_scheduling_isolation_failed",
                f"label={label} error={type(exc).__name__}: {exc}",
            ) from exc
        self._log_handle.write(
            (
                f"cpu_affinity={','.join(str(v) for v in sorted(self.cpu_affinity))}\n"
                f"nice_value={self.nice_value}\n"
            ).encode()
        )
        self._log_handle.flush()

    def scheduling_snapshot(self) -> dict[str, Any]:
        """Return and verify every engine thread's realized CPU partition."""
        task_root = Path(f"/proc/{self.process.pid}/task")
        thread_affinities: list[set[int]] = []
        for task in sorted(task_root.iterdir(), key=lambda path: int(path.name)):
            try:
                thread_affinities.append(
                    set(os.sched_getaffinity(int(task.name)))
                )
            except (FileNotFoundError, ProcessLookupError):
                continue
        if not thread_affinities:
            raise capture.CaptureFailure(
                "resident_process_thread_affinity_missing", self.label
            )
        unique = sorted(
            {tuple(sorted(affinity)) for affinity in thread_affinities}
        )
        expected = self.cpu_affinity
        all_threads_match = all(
            affinity == expected for affinity in thread_affinities
        )
        return {
            "label": self.label,
            "pid": self.process.pid,
            "expected_cpu_affinity": sorted(expected),
            "realized_thread_affinities": [list(row) for row in unique],
            "thread_count": len(thread_affinities),
            "all_threads_match": all_threads_match,
            "nice_value": os.getpriority(
                os.PRIO_PROCESS, self.process.pid
            ),
        }

    def offset(self) -> int:
        self._log_handle.flush()
        try:
            return self.log_path.stat().st_size
        except FileNotFoundError:
            return 0

    def send(self, commands: str | Iterable[str]) -> None:
        if self.process.poll() is not None:
            raise capture.CaptureFailure(
                "resident_process_not_running",
                f"{self.label} returncode={self.process.returncode}",
            )
        if self.process.stdin is None:
            raise capture.CaptureFailure(
                "resident_process_stdin_missing", self.label
            )
        rows = [commands] if isinstance(commands, str) else list(commands)
        for row in rows:
            command = row[:-1] if row.endswith("\n") else row
            if "\n" in command or "\r" in command:
                raise capture.CaptureFailure(
                    "resident_console_command_multiline",
                    f"{self.label} command={command!r}",
                )
            payload = (command + "\n\n").encode()
            try:
                                                                             
                                                                          
                                                                           
                                                                           
                                                                        
                                                                       
                                                   
                self.process.stdin.write(payload)
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise capture.CaptureFailure(
                    "resident_process_broken_pipe", self.label
                ) from exc

    def send_confirmed(
        self,
        commands: str | Iterable[str],
        marker: str,
        *,
        start: int | None = None,
        timeout_seconds: float = 60,
    ) -> int:
        if re.fullmatch(r"[A-Za-z0-9_.-]+", marker) is None:
            raise ValueError(f"unsafe resident marker: {marker!r}")
        cursor = self.offset() if start is None else start
        self.send(commands)
        self.send(f"echo {marker}")
        return self.wait_for(
            marker,
            start=cursor,
            timeout_seconds=timeout_seconds,
        )

    def wait_for(
        self,
        marker: str | bytes,
        *,
        start: int,
        timeout_seconds: float,
        periodic_command: str | Iterable[str] | None = None,
        periodic_interval_seconds: float = 2.0,
    ) -> int:
        if periodic_command is not None and periodic_interval_seconds <= 0:
            raise ValueError("periodic_interval_seconds must be positive")
        expected = marker.encode() if isinstance(marker, str) else marker
        deadline = time.monotonic() + timeout_seconds
        next_periodic_command = time.monotonic()
        cursor = start
        tail = b""
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise capture.CaptureFailure(
                    "resident_process_exited",
                    f"{self.label} returncode={self.process.returncode} "
                    f"marker={expected!r} log={self.log_path}",
                )
            try:
                with self.log_path.open("rb") as handle:
                    handle.seek(cursor)
                    chunk = handle.read()
            except FileNotFoundError:
                chunk = b""
            if chunk:
                combined = tail + chunk
                if expected in combined:
                    return self.offset()
                cursor += len(chunk)
                keep = max(0, len(expected) - 1)
                tail = combined[-keep:] if keep else b""
            now = time.monotonic()
            if (
                periodic_command is not None
                and now >= next_periodic_command
            ):
                self.send(periodic_command)
                next_periodic_command = now + periodic_interval_seconds
            time.sleep(0.05)
        raise capture.CaptureFailure(
            "resident_process_marker_timeout",
            f"{self.label} marker={expected!r} "
            f"timeout={timeout_seconds} log={self.log_path}",
        )

    def write_slice(
        self,
        start: int,
        destination: Path,
        *,
        include_startup: bool = False,
    ) -> None:
        end = self.offset()
        with self.log_path.open("rb") as source:
            source.seek(0 if include_startup else start)
            payload = source.read(max(0, end - (0 if include_startup else start)))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            (
                f"resident_process={self.label}\n"
                f"resident_log={self.log_path}\n"
                f"resident_slice_start={0 if include_startup else start}\n"
                f"resident_slice_end={end}\n"
            ).encode()
            + payload
        )

    def close(self) -> None:
                                                                       
                                                                          
                                                                         
                                                                        
                                              
        if getattr(self, "_closed", False):
            return
        self._closed = True
        cleanup_status = "already_exited"
        cleanup_detail = ""
        try:
            if self.process.poll() is None:
                cleanup_status = "graceful_quit"
                try:
                    self.send("quit")
                    self.process.wait(timeout=10)
                except (
                    BrokenPipeError,
                    OSError,
                    subprocess.TimeoutExpired,
                    capture.CaptureFailure,
                ) as exc:
                    cleanup_detail = (
                        f"{type(exc).__name__}: {exc}"
                    )
                if self.process.poll() is None:
                    cleanup_status = "sigterm"
                    try:
                        os.killpg(self.process.pid, signal.SIGTERM)
                    except OSError as exc:
                        cleanup_detail = (
                            f"{type(exc).__name__}: {exc}"
                        )
                    try:
                        self.process.wait(timeout=5)
                    except (
                        OSError,
                        subprocess.TimeoutExpired,
                    ) as exc:
                        cleanup_detail = (
                            f"{type(exc).__name__}: {exc}"
                        )
                    if self.process.poll() is None:
                        cleanup_status = "sigkill"
                        try:
                            os.killpg(self.process.pid, signal.SIGKILL)
                        except OSError as exc:
                            cleanup_detail = (
                                f"{type(exc).__name__}: {exc}"
                            )
                        try:
                            self.process.wait(timeout=5)
                        except (
                            OSError,
                            subprocess.TimeoutExpired,
                        ) as exc:
                            cleanup_status = "sigkill_wait_timeout"
                            cleanup_detail = (
                                f"{type(exc).__name__}: {exc}"
                            )
        except Exception as exc:
                                                                    
                                                                         
                                                                          
            cleanup_status = (
                f"cleanup_exception_{type(exc).__name__}"
            )
            cleanup_detail = str(exc)
            try:
                if self.process.poll() is None:
                    os.killpg(self.process.pid, signal.SIGKILL)
            except OSError:
                pass
        finally:
            stdin = getattr(self.process, "stdin", None)
            if stdin is not None:
                try:
                    stdin.close()
                except (OSError, ValueError):
                    pass
            handle = getattr(self, "_log_handle", None)
            if handle is not None:
                try:
                    if not getattr(handle, "closed", False):
                        handle.write(
                            (
                                "cleanup_status="
                                f"{cleanup_status}\n"
                                "cleanup_detail_json="
                                f"{json.dumps(cleanup_detail)}\n"
                                "returncode="
                                f"{self.process.returncode}\n"
                                f"finished_utc={capture.utc_now()}\n"
                            ).encode()
                        )
                        handle.flush()
                except (OSError, ValueError):
                    pass
                finally:
                    try:
                        if not getattr(handle, "closed", False):
                            handle.close()
                    except (OSError, ValueError):
                        pass


def _console_quote(value: Any) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    if not token or token in {".", ".."}:
        raise capture.CaptureFailure("resident_episode_token_invalid", value)
    return token


def _format_cpu_set(cpus: Iterable[int]) -> str:
    ordered = sorted(set(int(cpu) for cpu in cpus))
    if not ordered:
        return ""
    ranges: list[str] = []
    start = previous = ordered[0]
    for cpu in ordered[1:]:
        if cpu == previous + 1:
            previous = cpu
            continue
        ranges.append(
            str(start) if start == previous else f"{start}-{previous}"
        )
        start = previous = cpu
    ranges.append(
        str(start) if start == previous else f"{start}-{previous}"
    )
    return ",".join(ranges)


def _parse_cpu_set(value: str, *, field: str) -> set[int]:
    cpus: set[int] = set()
    for part in value.strip().split(",") if value.strip() else ():
        if re.fullmatch(r"\d+", part):
            cpus.add(int(part))
            continue
        match = re.fullmatch(r"(\d+)-(\d+)", part)
        if match is None:
            raise capture.CaptureFailure(
                "invalid_resident_cpu_set", f"{field}={value!r}"
            )
        start, end = (int(item) for item in match.groups())
        if start > end:
            raise capture.CaptureFailure(
                "invalid_resident_cpu_set", f"{field}={value!r}"
            )
        cpus.update(range(start, end + 1))
    return cpus


def configured_live_reserved_cpus() -> tuple[int, ...]:
    cpus = _parse_cpu_set(
        os.environ.get(LIVE_RESERVED_CPUSET_ENV, ""),
        field=LIVE_RESERVED_CPUSET_ENV,
    )
    return tuple(sorted(cpus))


def configured_background_cpus() -> tuple[int, ...]:
    cpus = _parse_cpu_set(
        os.environ.get(BACKGROUND_CPUSET_ENV, ""),
        field=BACKGROUND_CPUSET_ENV,
    )
    return tuple(sorted(cpus))


def configure_resident_cpu_isolation(
    lane_count: int,
    *,
    requested_x264_cpuset: str = "",
) -> dict[str, Any]:
    """Reserve two cores per resident live pair and exclude all bulk work.

    The server and headless live client each receive their own exclusive core.
    The Python scheduler, offline renderers, and x264 are confined to the
    complementary CPU set.  This is configured before worker threads are
    created so all subsequently launched background work inherits it.
    """
    if lane_count <= 0:
        raise capture.CaptureFailure(
            "invalid_resident_cpu_lane_count", str(lane_count)
        )
    if shutil.which("taskset") is None:
        raise capture.CaptureFailure(
            "resident_cpu_isolation_taskset_missing", "taskset"
        )
    available = tuple(sorted(os.sched_getaffinity(0)))
    required_live_cpus = lane_count * 2
    if len(available) <= required_live_cpus:
        raise capture.CaptureFailure(
            "resident_cpu_isolation_insufficient_cpus",
            f"available={list(available)} lane_count={lane_count} "
            f"required_live_cpus={required_live_cpus}",
        )
    reserved = tuple(available[:required_live_cpus])
    background = tuple(available[required_live_cpus:])
    background_set = set(background)

                                                                         
                                                                            
    realized_tasks: list[int] = []
    for _ in range(3):
        before = sorted(
            int(path.name)
            for path in Path("/proc/self/task").iterdir()
        )
        for task_id in before:
            os.sched_setaffinity(task_id, background_set)
        after = sorted(
            int(path.name)
            for path in Path("/proc/self/task").iterdir()
        )
        if before == after:
            realized_tasks = after
            break
    if not realized_tasks or any(
        set(os.sched_getaffinity(task_id)) != background_set
        for task_id in realized_tasks
    ):
        raise capture.CaptureFailure(
            "resident_background_cpu_isolation_unverified",
            f"background={list(background)}",
        )

    requested_x264 = _parse_cpu_set(
        requested_x264_cpuset,
        field="XONOTIC_X264_CPUSET",
    )
    x264_cpus = requested_x264 or background_set
    if not x264_cpus or not x264_cpus <= background_set:
        raise capture.CaptureFailure(
            "x264_cpuset_overlaps_live_reserved_cpus",
            f"requested={sorted(x264_cpus)} "
            f"background={list(background)}",
        )

    os.environ[LIVE_RESERVED_CPUSET_ENV] = _format_cpu_set(reserved)
    os.environ[BACKGROUND_CPUSET_ENV] = _format_cpu_set(background)
    os.environ["XONOTIC_X264_CPUSET"] = _format_cpu_set(x264_cpus)
    return {
        "enabled": True,
        "available_cpus_before_partition": list(available),
        "reserved_live_cpus": list(reserved),
        "background_cpus": list(background),
        "x264_cpus": sorted(x264_cpus),
        "live_cores_per_lane": 2,
        "server_and_live_client_share_lane_core": False,
        "background_task_count_at_partition": len(realized_tasks),
        "background_threads_verified": True,
        "negative_nice_requested": False,
        "cap_sys_nice_required": False,
    }


def configured_live_time_scale() -> int:
    """Return the authoritative demo clock multiplier.

    The duel-v8 production accelerator records authoritative demos at the
    native 64 Hz clock and obtains throughput from c8 batching plus offline
    replay.  The isolated Stage-2 motion extension additionally uses the
    manifest-locked live multiplier; production currently selects 2x because
    4x cannot preserve every CTF demo snapshot on this runtime.
    """
    raw = os.environ.get("XONOTIC_LIVE_TIME_SCALE", "1")
    try:
        value = int(raw)
    except ValueError as exc:
        raise capture.CaptureFailure(
            "invalid_live_time_scale", raw
        ) from exc
    if value not in {1, 2, 4, 8}:
        raise capture.CaptureFailure(
            "invalid_live_time_scale",
            f"expected one of 1,2,4,8; actual={raw}",
        )
    return value


class ReusableStage1Lane:
    """One resident dedicated/live lane with an isolated render generation."""

    def __init__(
        self,
        lane_root: Path,
        *,
        build: Path,
        port: int,
        live_cpu_slot: int | None = None,
    ) -> None:
        self.lane_root = lane_root.resolve()
        self.build = build.resolve()
        self.port = capture.choose_port(port)
        self.lane_root.mkdir(parents=True, exist_ok=False)
        self.server_user, self.live_user = capture.prepare_userdirs(
            self.lane_root / "live_pair", self.build
        )
        _, self.render_user = capture.prepare_userdirs(
            self.lane_root / "render_pair", self.build
        )
        self.server: ResidentProcess | None = None
        self.live_client: ResidentProcess | None = None
        self.render_client: ResidentProcess | None = None
        self.current_map: str | None = None
        self.current_gametype: str | None = None
        self.sequence = 0
        self.process_startup_seconds: dict[str, float] = {}
        self.renderer = ""
        self.render_generation = 0
        self.render_recycle_count = 0
        self.live_cpu_slot = live_cpu_slot
        self.server_cpu_affinity: set[int] | None = None
        self.live_client_cpu_affinity: set[int] | None = None
        self.background_cpu_affinity: set[int] | None = None
        if live_cpu_slot is not None:
            reserved = configured_live_reserved_cpus()
            background = configured_background_cpus()
            server_cpu_index = live_cpu_slot * 2
            live_client_cpu_index = server_cpu_index + 1
            if not 0 <= live_cpu_slot or live_client_cpu_index >= len(reserved):
                raise capture.CaptureFailure(
                    "resident_live_cpu_slot_out_of_range",
                    f"slot={live_cpu_slot} reserved={list(reserved)}",
                )
            if not background or set(reserved) & set(background):
                raise capture.CaptureFailure(
                    "resident_cpu_partition_invalid",
                    f"reserved={list(reserved)} "
                    f"background={list(background)}",
                )
            self.server_cpu_affinity = {reserved[server_cpu_index]}
            self.live_client_cpu_affinity = {
                reserved[live_client_cpu_index]
            }
            self.background_cpu_affinity = set(background)
        self._active_server_slice_start: int | None = None
        self._active_live_slice_start: int | None = None
        self._active_render_slice_start: int | None = None
        self.live_time_scale = configured_live_time_scale()
        self.live_server_ticrate = 1.0 / (
            AUTHORITATIVE_TICKS_PER_SECOND * self.live_time_scale
        )
        self.live_netfps = (
            AUTHORITATIVE_TICKS_PER_SECOND * self.live_time_scale
        )
        self.live_maxfps = 2 * self.live_netfps

    def __enter__(self) -> "ReusableStage1Lane":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        for attribute in (
            "render_client",
            "live_client",
            "server",
        ):
            process = getattr(self, attribute, None)
                                                                           
                                                                  
            setattr(self, attribute, None)
            if process is not None:
                try:
                    process.close()
                except Exception as exc:
                    print(
                        "resident_process_cleanup_warning "
                        f"label={getattr(process, 'label', attribute)} "
                        f"error={type(exc).__name__} "
                        f"detail={json.dumps(str(exc))}",
                        file=sys.stderr,
                        flush=True,
                    )

    def _close_render_client(self) -> float:
        """Close only the playback process and keep the live world resident."""
        process = self.render_client
        self.render_client = None
        if process is None:
            return 0.0
        started = time.monotonic()
        process.close()
        return time.monotonic() - started

    def snapshot_failure_logs(self, stage: Path) -> None:
        """Best-effort per-episode slices before a failed lane is destroyed."""
        stage = Path(stage)
        stage.mkdir(parents=True, exist_ok=True)
        rows = (
            (
                self.server,
                self._active_server_slice_start,
                stage / "server_console.log",
            ),
            (
                self.live_client,
                self._active_live_slice_start,
                stage / "client_live_console.log",
            ),
            (
                self.render_client,
                self._active_render_slice_start,
                stage / "client_render_console.log",
            ),
        )
        for process, start, destination in rows:
            if process is None or start is None:
                continue
            target = destination
            if target.exists():
                target = target.with_name(
                    f"{target.stem}_failure_tail{target.suffix}"
                )
            try:
                process.write_slice(start, target)
            except Exception as exc:
                print(
                    "resident_failure_log_snapshot_warning "
                    f"label={process.label} "
                    f"error={type(exc).__name__} "
                    f"detail={json.dumps(str(exc))}",
                    file=sys.stderr,
                    flush=True,
                )

    def _start_server(
        self,
        scenario: dict[str, Any],
        values: dict[str, Any],
        map_name: str,
        exec_name: str,
    ) -> int:
        engine_net_timeout = (
            capture.configured_engine_net_timeout_seconds()
        )
        dedicated = self.build / "bin/xonotic-local-dedicated"
        command = (
            capture.command_base(dedicated, self.server_user)
            + ["+exec", exec_name]
            + ["+exec", "capture_mode.cfg"]
            + capture.cvar_set_args(
                {
                    "net_connecttimeout": engine_net_timeout,
                    "net_messagetimeout": engine_net_timeout,
                                                                           
                                                                            
                                                                         
                    "sys_ticrate": self.live_server_ticrate,
                    "slowmo": self.live_time_scale,
                }
            )
            + ["+set", "port", str(self.port)]
            + ["+set", "sv_random_seed", str(scenario["seed"])]
            + [
                "+set",
                "bot_number",
                "1",
            ]
            + ["+map", map_name]
            + ["+exec", "capture_episode.cfg"]
            + ["+sys_ticrate", "+slowmo"]
        )
        started = time.monotonic()
        self.server = ResidentProcess(
            command,
            self.lane_root / "server_resident.log",
            label="stage1-resident-server",
            cpu_affinity=self.server_cpu_affinity,
            nice_value=LIVE_PROCESS_NICE,
        )
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
        )
        self.server.wait_for(
            "execing capture_episode.cfg",
            start=0,
            timeout_seconds=control_timeout,
        )
        self.process_startup_seconds["server"] = (
            time.monotonic() - started
        )
        return 0

    def _start_clients(self, *, require_render: bool) -> None:
        if self.live_client is not None and (
            self.render_client is not None or not require_render
        ):
            return
        engine_net_timeout = (
            capture.configured_engine_net_timeout_seconds()
        )
        client = self.build / "bin/xonotic-local-sdl"
        audio = [
            "-sndspeed",
            str(capture.AUDIO_RATE),
            "-sndbits",
            "16",
            "-sndstereo",
        ]
        live_geometry = [
            "-window",
            "-width",
            str(LIVE_CAPTURE_WIDTH),
            "-height",
            str(LIVE_CAPTURE_HEIGHT),
        ]
        render_geometry = [
            "-window",
            "-width",
            str(capture.WIDTH),
            "-height",
            str(capture.HEIGHT),
        ]
        live_values = {
            "exec": "capture_client.cfg",
            "net_connecttimeout": engine_net_timeout,
            "net_messagetimeout": engine_net_timeout,
            "cl_maxfps": IDLE_CLIENT_MAXFPS,
            "cl_netfps": self.live_netfps,
            "slowmo": self.live_time_scale,
            "cl_damagetext": 0,
            "capture_enable": 1,
            "capture_mode": 0,
            "capture_expected_frames": capture.OUTPUT_TICKS,
            "capture_quit_on_end": 0,
                                                                          
                                                                            
                                                                         
                                                                           
            "r_renderview": 0,
                                                               
                                                                            
                                                                            
                                                                          
                                             
            "scr_refresh": 0,
        }
        render_slowmo = 1.0 / self.live_time_scale
        render_preroll_slowmo = (
            RENDER_PREROLL_SEMANTIC_TIME_SCALE / self.live_time_scale
        )
        render_values = {
            "exec": "capture_client.cfg",
            "cl_maxfps": IDLE_CLIENT_MAXFPS,
            "cl_damagetext": 0,
            "capture_enable": 1,
            "capture_mode": 1,
            "capture_expected_frames": capture.OUTPUT_TICKS,
            "capture_quit_on_end": 0,
            "scr_menuforcewhiledisconnected": 0,
            "r_renderview": 1,
            "scr_refresh": 1,
            "cl_capturevideo_realtime": 0,
            "cl_capturevideo_offline_accelerate": (
                capture.configured_offline_acceleration()
            ),
                                                                          
                                                                             
                                                                   
            "slowmo": render_preroll_slowmo,
            "capture_demo_episode_slowmo": render_slowmo,
        }
        started = time.monotonic()
        started_live = self.live_client is None
        started_render = require_render and self.render_client is None
        if started_live:
            self.live_client = ResidentProcess(
                capture.command_base(client, self.live_user)
                + live_geometry
                + audio
                + capture.cvar_args(live_values),
                self.lane_root / "live_client_resident.log",
                label="stage1-resident-live-client",
                cpu_affinity=self.live_client_cpu_affinity,
                nice_value=LIVE_PROCESS_NICE,
            )
        if started_render:
            self.render_generation += 1
            self.render_client = ResidentProcess(
                capture.command_base(client, self.render_user)
                + render_geometry
                + audio
                + capture.cvar_args(render_values),
                self.lane_root
                / f"render_client_generation_{self.render_generation:04d}.log",
                label=(
                    "stage1-resident-render-client-"
                    f"g{self.render_generation:04d}"
                ),
                cpu_affinity=self.background_cpu_affinity,
            )
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
        )
        if self.live_client is None or (
            require_render and self.render_client is None
        ):
            raise AssertionError("resident client startup incomplete")
        if started_live:
            self.live_client.wait_for(
                "GL_RENDERER:",
                start=0,
                timeout_seconds=control_timeout,
            )
        if started_render:
            self.render_client.wait_for(
                "GL_RENDERER:",
                start=0,
                timeout_seconds=control_timeout,
            )
        startup_seconds = time.monotonic() - started
        if started_live and started_render:
            self.process_startup_seconds["clients_parallel_initial"] = (
                startup_seconds
            )
        elif started_render:
            self.process_startup_seconds["render_generation_last"] = (
                startup_seconds
            )
            self.process_startup_seconds["render_generation_count"] = (
                float(self.render_generation)
            )
        elif started_live:
            self.process_startup_seconds["live_generation_last"] = (
                startup_seconds
            )
        if started_render:
            if self.render_client is None:
                raise AssertionError("render client startup incomplete")
            render_console = self.render_client.log_path.read_text(
                errors="replace"
            )
            match = re.search(r"GL_RENDERER:?\s*(.+)", render_console)
            self.renderer = match.group(1).strip() if match else ""
            if not capture.is_nvidia_hardware_renderer(
                self.renderer, render_console
            ):
                raise capture.CaptureFailure(
                    "hardware_renderer_gate",
                    self.renderer or str(self.render_client.log_path),
                )

    def _prepare_server_episode(
        self,
        stage: Path,
        scenario: dict[str, Any],
        retry: int,
        token: str,
    ) -> tuple[dict[str, Any], str, str, Path, Path | None]:
        action_path = stage / "actions_requested.csv"
        capture.write_action_csv(action_path, scenario, retry=retry)
        episode_rel = Path("capture/resident") / token
        episode_data = self.server_user / "data" / episode_rel
        episode_data.mkdir(parents=True, exist_ok=False)
        server_action_rel = episode_rel / "actions.csv"
        server_log_rel = episode_rel / "server.jsonl"
        shutil.copy2(
            action_path,
            self.server_user / "data" / server_action_rel,
        )
        route_source: Path | None = None
        route_plan = scenario.get("route_plan") or {}
        route_rel = episode_rel / "route.csv"
        if route_plan:
            route_source = capture.locked_root_artifact(
                route_plan.get("route_csv_path", ""),
                route_plan.get("route_csv_sha256"),
                "route_csv",
            )
            shutil.copy2(
                route_source,
                self.server_user / "data" / route_rel,
            )
        timeline_source: Path | None = None
        timeline_rel = episode_rel / "enemy_timeline.csv"
        if scenario.get("enemy_timeline_path"):
            timeline_source = capture.locked_root_artifact(
                scenario["enemy_timeline_path"],
                scenario.get("enemy_timeline_sha256"),
                "enemy_timeline",
            )
            shutil.copy2(
                timeline_source,
                self.server_user / "data" / timeline_rel,
            )
        values = capture.server_cvars(scenario, self.port)
        exec_name = str(values.pop("exec"))
        map_name = str(values.pop("map"))
        values["capture_server_action_file"] = str(server_action_rel)
        values["capture_server_log"] = str(server_log_rel)
        if route_plan:
            values["capture_route_file"] = str(route_rel)
        if timeline_source is not None:
            values["capture_enemy_timeline_file"] = str(timeline_rel)
        expected_gametype = str(
            scenario.get("gametype", "dm")
        ).lower()
        capture.write_server_mode_config(
            self.server_user / "data/capture_mode.cfg",
            expected_gametype,
        )
        capture.write_server_episode_config(
            self.server_user / "data/capture_episode.cfg",
            values,
            expected_gametype,
        )
        telemetry_path = (
            self.server_user
            / "data/data"
            / server_log_rel
        )
        return (
            values,
            exec_name,
            map_name,
            telemetry_path,
            route_source,
        )

    def _reset_server(
        self,
        scenario: dict[str, Any],
        map_name: str,
        gametype: str,
        token: str,
    ) -> tuple[int, str]:
        if self.server is None:
            raise AssertionError("server must be started first")
        same_world = (
            self.current_map == map_name
            and self.current_gametype == gametype
        )
        if not same_world:
            raise capture.CaptureFailure(
                "resident_lane_world_group_changed",
                "resident reuse is admitted only within one exact "
                f"(map, gametype) group; current="
                f"({self.current_map!r}, {self.current_gametype!r}) "
                f"requested=({map_name!r}, {gametype!r})",
            )
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
        )
        start = self.server.offset()
        self.server.send_confirmed(
            [
                "exec capture_mode.cfg",
                "exec capture_episode.cfg",
                f"set sv_random_seed {int(scenario['seed'])}",
                "set bot_number 1",
                f"sys_ticrate {self.live_server_ticrate:.12f}",
                f"slowmo {self.live_time_scale}",
                "sys_ticrate",
                "slowmo",
            ],
            f"resident_server_configured_{token}",
            start=start,
            timeout_seconds=control_timeout,
        )
        reset_start = self.server.offset()
        self.server.send("restart")
        self.server.wait_for(
            "Server spawned.",
            start=reset_start,
            timeout_seconds=control_timeout,
        )
        return start, "restart"

    def _throttle_server_idle(self, token: str) -> dict[str, Any]:
        """Drop an unused resident world to 20 Hz before releasing its slot.

        The next episode restores the accelerated clock and performs a full
        world restart, so idle world time never enters captured telemetry.
        """
        if self.server is None:
            raise AssertionError("server must be running before idle throttle")
        started = time.monotonic()
        control_timeout = capture.configured_resident_control_timeout_seconds()
        slice_start = self.server.offset()
        self.server.send_confirmed(
            [
                f"sys_ticrate {IDLE_SERVER_TICRATE:.12g}",
                f"slowmo {IDLE_SERVER_SLOWMO}",
                "sys_ticrate",
                "slowmo",
            ],
            f"resident_server_idle_{token}",
            start=slice_start,
            timeout_seconds=control_timeout,
        )
        slice_end = self.server.offset()
        with self.server.log_path.open("rb") as handle:
            handle.seek(slice_start)
            console = handle.read(max(0, slice_end - slice_start)).decode(
                errors="replace"
            )
        realized_ticrate = capture.logged_cvar_value(console, "sys_ticrate")
        realized_slowmo = capture.logged_cvar_value(console, "slowmo")
        try:
            verified = (
                abs(float(realized_ticrate) - IDLE_SERVER_TICRATE) <= 1e-12
                and float(realized_slowmo) == IDLE_SERVER_SLOWMO
            )
        except (TypeError, ValueError):
            verified = False
        if not verified:
            raise capture.CaptureFailure(
                "resident_server_idle_throttle_unverified",
                f"expected_ticrate={IDLE_SERVER_TICRATE} "
                f"realized_ticrate={realized_ticrate!r} "
                f"expected_slowmo={IDLE_SERVER_SLOWMO} "
                f"realized_slowmo={realized_slowmo!r}",
            )
        return {
            "resident_server_idle_ticrate": IDLE_SERVER_TICRATE,
            "resident_server_idle_slowmo": IDLE_SERVER_SLOWMO,
            "resident_server_idle_throttle_verified": True,
            "resident_server_idle_throttle_wall_seconds": (
                time.monotonic() - started
            ),
        }

    def run_live(
        self,
        stage: Path,
        scenario: dict[str, Any],
        retry: int = 0,
    ) -> dict[str, Any]:
        capture.validate_fixed_assets()
        capture.validate_scenario_assets(scenario)
        stage.mkdir(parents=True, exist_ok=False)
        (stage / "live").mkdir()
        self._active_server_slice_start = None
        self._active_live_slice_start = None
        self._active_render_slice_start = None
        self.sequence += 1
        token = _safe_token(
            f"{self.sequence:04d}_{scenario['episode_id']}"
        )
        (
            values,
            exec_name,
            map_name,
            telemetry_path,
            route_source,
        ) = self._prepare_server_episode(
            stage, scenario, retry, token
        )
        gametype = str(scenario.get("gametype", "dm")).lower()
        episode_started = time.monotonic()
        if self.server is None:
            server_slice_start = self._start_server(
                scenario, values, map_name, exec_name
            )
            reset_kind = "initial_map"
        else:
            server_slice_start, reset_kind = self._reset_server(
                scenario, map_name, gametype, token
            )
        self._active_server_slice_start = server_slice_start
                                                                         
                                                                         
                                                                           
                                                            
        self._start_clients(require_render=False)
        if self.live_client is None or self.server is None:
            raise AssertionError("resident processes missing")
        self.current_map = map_name
        self.current_gametype = gametype
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
        )

        live_slice_start = self.live_client.offset()
        self._active_live_slice_start = live_slice_start
        live_dir = stage / "live"
        demo_name = token
        action_path = stage / "actions_requested.csv"
        self.live_client.send_confirmed(
            [
                f"cl_maxfps {self.live_maxfps}",
                f"cl_netfps {self.live_netfps}",
                f"slowmo {self.live_time_scale}",
                "capture_enable 1",
                "capture_mode 0",
                f"capture_action_file {_console_quote(action_path)}",
                f"capture_log_dir {_console_quote(live_dir)}",
                "capture_initial_yaw "
                f"{float(scenario['player']['yaw']):.9f}",
                "capture_initial_pitch "
                f"{float(scenario['player'].get('pitch', 0)):.9f}",
                f"capture_expected_frames {capture.OUTPUT_TICKS}",
                "capture_quit_on_end 0",
                "r_renderview 0",
                "scr_refresh 0",
                "cl_maxfps",
                "cl_netfps",
                "slowmo",
                "scr_refresh",
            ],
            f"resident_live_configured_{token}",
            start=live_slice_start,
            timeout_seconds=control_timeout,
        )
        recording_at = self.live_client.send_confirmed(
            f"record demos/{demo_name}",
            f"resident_live_recording_{token}",
            timeout_seconds=control_timeout,
        )
        self.live_client.send(f"connect 127.0.0.1:{self.port}")
        connected_at = self.live_client.wait_for(
            "CL_SignonReply: 4",
            start=recording_at,
            timeout_seconds=control_timeout,
        )
        self.live_client.wait_for(
            f"capture: episode reset id={scenario['episode_id']} "
            "mode=0 demo=0",
            start=connected_at,
            timeout_seconds=control_timeout,
            periodic_command="cmd join",
            periodic_interval_seconds=2,
        )
        self.live_client.wait_for(
            f"capture: output end id={scenario['episode_id']}",
            start=connected_at,
            timeout_seconds=capture.configured_live_timeout_seconds(),
        )
        completed_start = self.live_client.offset()
        self.live_client.send("stop")
        self.live_client.wait_for(
            "Completed demo",
            start=completed_start,
            timeout_seconds=control_timeout,
        )
        disconnect_start = self.live_client.offset()
        self.live_client.send("disconnect")
        self.live_client.wait_for(
            "CL_Disconnect",
            start=disconnect_start,
            timeout_seconds=control_timeout,
        )
        self.live_client.wait_for(
            "unloaded",
            start=disconnect_start,
            timeout_seconds=control_timeout,
        )
        self.live_client.send_confirmed(
            [
                "capture_enable 0",
                f"capture_action_file {_console_quote('')}",
                f"capture_log_dir {_console_quote('')}",
                f"cl_maxfps {IDLE_CLIENT_MAXFPS}",
            ],
            f"resident_live_detached_{token}",
            timeout_seconds=control_timeout,
        )
        self.server.write_slice(
            server_slice_start,
            stage / "server_console.log",
            include_startup=(reset_kind == "initial_map"),
        )
        self.live_client.write_slice(
            live_slice_start,
            stage / "client_live_console.log",
            include_startup=(self.sequence == 1),
        )
        server_console = (
            stage / "server_console.log"
        ).read_text(errors="replace")
        realized_gametype = capture.validate_realized_gametype(
            server_console,
            gametype,
            stage / "server_console.log",
        )
        mode_cvar = capture.GAMETYPE_CVARS[gametype]
        active_mode = capture.logged_cvar_value(
            server_console, mode_cvar
        )
        if active_mode != "1":
            raise capture.CaptureFailure(
                "realized_gametype_cvar_inactive",
                f"gametype={gametype} {mode_cvar}={active_mode!r}",
            )
        flag_waypoint = capture.logged_cvar_value(
            server_console, "g_ctf_flag_waypoint"
        )
        if flag_waypoint != "0":
            raise capture.CaptureFailure(
                "server_objective_waypoint_policy_failed",
                f"g_ctf_flag_waypoint={flag_waypoint!r}",
            )
        max_physics_frames = capture.logged_cvar_value(
            server_console, "cl_maxphysicsframesperserverframe"
        )
        if max_physics_frames != str(
            capture.SERVER_MAX_PHYSICS_FRAMES_PER_HOST_FRAME
        ):
            raise capture.CaptureFailure(
                "server_snapshot_tick_delivery_policy_failed",
                "cl_maxphysicsframesperserverframe="
                f"{max_physics_frames!r}",
            )
        realized_server_ticrate = capture.logged_cvar_value(
            server_console, "sys_ticrate"
        )
        realized_server_slowmo = capture.logged_cvar_value(
            server_console, "slowmo"
        )
        try:
            server_ticrate_matches = (
                abs(
                    float(realized_server_ticrate)
                    - self.live_server_ticrate
                )
                <= 1e-12
            )
            server_slowmo_matches = (
                float(realized_server_slowmo) == self.live_time_scale
            )
        except (TypeError, ValueError):
            server_ticrate_matches = False
            server_slowmo_matches = False
        if not server_ticrate_matches or not server_slowmo_matches:
            raise capture.CaptureFailure(
                "live_time_scale_server_unverified",
                "expected_ticrate="
                f"{self.live_server_ticrate:.12f} "
                f"realized_ticrate={realized_server_ticrate!r} "
                f"expected_slowmo={self.live_time_scale} "
                f"realized_slowmo={realized_server_slowmo!r}",
            )
        demo_path = (
            self.live_user / "data/demos" / f"{demo_name}.dem"
        )
        actions_engine = live_dir / "actions_engine.csv"
        for required in (
            demo_path,
            telemetry_path,
            actions_engine,
        ):
            if not required.is_file() or required.stat().st_size == 0:
                raise capture.CaptureFailure(
                    "resident_live_artifact_missing", str(required)
                )
        live_console = (
            stage / "client_live_console.log"
        ).read_text(errors="replace")
        realized_live_maxfps = capture.logged_cvar_value(
            live_console, "cl_maxfps"
        )
        realized_live_netfps = capture.logged_cvar_value(
            live_console, "cl_netfps"
        )
        realized_live_slowmo = capture.logged_cvar_value(
            live_console, "slowmo"
        )
        realized_live_scr_refresh = capture.logged_cvar_value(
            live_console, "scr_refresh"
        )
        expected_live_values = {
            "cl_maxfps": str(self.live_maxfps),
            "cl_netfps": str(self.live_netfps),
            "slowmo": str(self.live_time_scale),
            "scr_refresh": "0",
        }
        realized_live_values = {
            "cl_maxfps": realized_live_maxfps,
            "cl_netfps": realized_live_netfps,
            "slowmo": realized_live_slowmo,
            "scr_refresh": realized_live_scr_refresh,
        }
        if realized_live_values != expected_live_values:
            raise capture.CaptureFailure(
                "live_time_scale_client_unverified",
                f"expected={expected_live_values} "
                f"realized={realized_live_values}",
            )
        if f"loaded {capture.TOTAL_TICKS} actions" not in live_console:
            raise capture.CaptureFailure(
                "action_schedule_not_loaded",
                str(stage / "client_live_console.log"),
            )
        if "Completed demo" not in live_console:
            raise capture.CaptureFailure(
                "demo_not_completed",
                str(stage / "client_live_console.log"),
            )
        staged_demo = stage / "demo.dem"
        shutil.copy2(demo_path, staged_demo)
        if (
            not staged_demo.is_file()
            or staged_demo.stat().st_size != demo_path.stat().st_size
        ):
            raise capture.CaptureFailure(
                "resident_demo_staging_failed", str(staged_demo)
            )
        idle_throttle = self._throttle_server_idle(token)
        cpu_isolation_enabled = (
            self.server_cpu_affinity is not None
            and self.live_client_cpu_affinity is not None
        )
        server_scheduling = self.server.scheduling_snapshot()
        live_scheduling = self.live_client.scheduling_snapshot()
        if cpu_isolation_enabled and not (
            server_scheduling["all_threads_match"]
            and live_scheduling["all_threads_match"]
            and server_scheduling["expected_cpu_affinity"]
            == sorted(self.server_cpu_affinity or ())
            and live_scheduling["expected_cpu_affinity"]
            == sorted(self.live_client_cpu_affinity or ())
        ):
            raise capture.CaptureFailure(
                "resident_live_cpu_isolation_unverified",
                f"server={server_scheduling} live={live_scheduling}",
            )
        live_wall_seconds = time.monotonic() - episode_started
        return {
            "server_user": self.server_user,
            "client_user": self.live_user,
            "demo_path": demo_path,
            "staged_demo_path": staged_demo,
            "demo_name": demo_name,
            "server_telemetry": telemetry_path,
            "actions_engine": actions_engine,
            "live_wall_seconds": live_wall_seconds,
            "port": self.port,
            "realized_gametype": realized_gametype,
            "realized_gametype_cvar": mode_cvar,
            "realized_gametype_cvar_value": int(active_mode),
            "g_ctf_flag_waypoint": int(flag_waypoint),
            "server_max_physics_frames_per_host_frame": int(
                max_physics_frames
            ),
            "route_source": (
                str(route_source) if route_source else None
            ),
            "resident_process_reused": self.sequence > 1,
            "resident_server_reset": reset_kind,
            "resident_sequence": self.sequence,
            "resident_token": token,
            "live_time_scale": self.live_time_scale,
            "live_server_ticrate": self.live_server_ticrate,
            "live_netfps": self.live_netfps,
            "live_maxfps": self.live_maxfps,
            "live_scr_refresh": False,
            "resident_cpu_isolation_enabled": cpu_isolation_enabled,
            "resident_live_cpu_slot": self.live_cpu_slot,
            "resident_reserved_live_cpus": list(
                configured_live_reserved_cpus()
            ),
            "resident_background_cpus": list(
                configured_background_cpus()
            ),
            "resident_server_cpu_scheduling": server_scheduling,
            "resident_live_client_cpu_scheduling": live_scheduling,
            **idle_throttle,
        }

    def run_render(
        self,
        stage: Path,
        scenario: dict[str, Any],
        live: dict[str, Any],
    ) -> dict[str, Any]:
        self._start_clients(require_render=True)
        if self.render_client is None:
            raise AssertionError("render client must be running")
        render_dir = stage / "render"
        render_dir.mkdir(parents=True, exist_ok=False)
        demo_name = str(live["demo_name"])
        render_demo = (
            self.render_user / "data/demos" / f"{demo_name}.dem"
        )
        shutil.copy2(Path(live["demo_path"]), render_demo)
        video_dir = self.render_user / "data/video"
        prefix = f"{demo_name}_"
        for old in video_dir.glob(f"{prefix}*.avi"):
            old.unlink()
        render_slice_start = self.render_client.offset()
        self._active_render_slice_start = render_slice_start
        render_generation = self.render_generation
        started = time.monotonic()
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
        )
        offline_accelerate = capture.configured_offline_acceleration()
        render_slowmo = 1.0 / self.live_time_scale
        scenario_seed = int(scenario["seed"]) & 0x7FFFFFFF
        render_episode_seed = scenario_seed & RENDER_EPISODE_SEED_MASK
        render_preroll_slowmo = (
            RENDER_PREROLL_SEMANTIC_TIME_SCALE / self.live_time_scale
        )
        self.render_client.send_confirmed(
            [
                "capture_enable 1",
                "capture_mode 1",
                "capture_demo_fixedstep 1",
                f"capture_log_dir {_console_quote(render_dir)}",
                f"capture_expected_frames {capture.OUTPUT_TICKS}",
                "capture_quit_on_end 0",
                "scr_menuforcewhiledisconnected 0",
                "cl_maxfps 64",
                "cl_damagetext 0",
                "r_renderview 1",
                "scr_refresh 1",
                "cl_capturevideo_realtime 0",
                "cl_capturevideo_offline_accelerate "
                f"{offline_accelerate}",
                f"slowmo {render_preroll_slowmo:.12g}",
                f"capture_demo_episode_slowmo {render_slowmo:.12g}",
                f"capture_demo_episode_seed {render_episode_seed}",
                f"cl_capturevideo_nameformat {_console_quote(prefix)}",
                                                                           
                                                                            
                                                                        
                "cl_capturevideo_realtime",
                "cl_capturevideo_offline_accelerate",
                "slowmo",
                "capture_demo_episode_slowmo",
                "capture_demo_episode_seed",
                "scr_refresh",
            ],
            f"resident_render_configured_{live['resident_token']}",
            start=render_slice_start,
            timeout_seconds=control_timeout,
        )
        frontend_menu_close_marker = (
            f"resident_render_frontend_closed_{live['resident_token']}"
        )
        self.render_client.send_confirmed(
            FRONTEND_MENU_CLOSE_COMMANDS,
            frontend_menu_close_marker,
            timeout_seconds=control_timeout,
        )
        playback_start = self.render_client.offset()
        self.render_client.send(f"timedemo demos/{demo_name}")
        self.render_client.wait_for(
            f"capture: output begin id={scenario['episode_id']}",
            start=playback_start,
            timeout_seconds=max(
                control_timeout,
                capture.configured_render_startup_stall_seconds(),
            ),
        )
        self.render_client.wait_for(
            f"capture: output end id={scenario['episode_id']}",
            start=render_slice_start,
            timeout_seconds=capture.configured_render_timeout_seconds(),
        )
        self.render_client.wait_for(
            "Server disconnected",
            start=render_slice_start,
            timeout_seconds=control_timeout,
        )
        self.render_client.wait_for(
            "CL_Disconnect",
            start=render_slice_start,
            timeout_seconds=control_timeout,
        )
        self.render_client.wait_for(
            "unloaded",
            start=render_slice_start,
            timeout_seconds=control_timeout,
        )
        self.render_client.send_confirmed(
            [
                "capture_enable 0",
                f"capture_log_dir {_console_quote('')}",
                f"cl_maxfps {IDLE_CLIENT_MAXFPS}",
            ],
            f"resident_render_detached_{live['resident_token']}",
            timeout_seconds=control_timeout,
        )
        render_wall_seconds = time.monotonic() - started
        self.render_client.write_slice(
            render_slice_start,
            stage / "client_render_console.log",
            include_startup=(self.sequence == 1),
        )
        avis = sorted(video_dir.glob(f"{prefix}*.avi"))
        if len(avis) != 1:
            raise capture.CaptureFailure(
                "raw_video_count",
                f"expected=1 actual={len(avis)} path={video_dir}",
            )
        raw_avi = stage / "raw_capture.avi"
        shutil.move(str(avis[0]), raw_avi)
                                                                          
                                                                        
                                                                           
        render_demo.unlink(missing_ok=True)
        for required in (
            render_dir / "frames_engine.csv",
            render_dir / "audio_events_engine.csv",
        ):
            if not required.is_file() or required.stat().st_size == 0:
                raise capture.CaptureFailure(
                    "resident_render_artifact_missing", str(required)
                )
        console = (
            stage / "client_render_console.log"
        ).read_text(errors="replace")
        realized_realtime = capture.logged_cvar_value(
            console, "cl_capturevideo_realtime"
        )
        realized_acceleration = capture.logged_cvar_value(
            console, "cl_capturevideo_offline_accelerate"
        )
        realized_preroll_slowmo = capture.logged_cvar_value(
            console, "slowmo"
        )
        realized_render_slowmo = capture.logged_cvar_value(
            console, "capture_demo_episode_slowmo"
        )
        realized_render_episode_seed = capture.logged_cvar_value(
            console, "capture_demo_episode_seed"
        )
        realized_render_scr_refresh = capture.logged_cvar_value(
            console, "scr_refresh"
        )
        if realized_realtime != "0":
            raise capture.CaptureFailure(
                "offline_capture_realtime_unverified",
                f"expected=0 realized={realized_realtime!r} "
                f"log={stage / 'client_render_console.log'}",
            )
        if realized_acceleration != str(offline_accelerate):
            raise capture.CaptureFailure(
                "offline_acceleration_unverified",
                f"expected={offline_accelerate} "
                f"realized={realized_acceleration!r} "
                f"log={stage / 'client_render_console.log'}",
            )
        try:
            render_slowmo_matches = (
                abs(float(realized_render_slowmo) - render_slowmo)
                <= 1e-12
            )
            preroll_slowmo_matches = (
                abs(
                    float(realized_preroll_slowmo)
                    - render_preroll_slowmo
                )
                <= 1e-12
            )
        except (TypeError, ValueError):
            render_slowmo_matches = False
            preroll_slowmo_matches = False
        output_timing_marker = (
            f"capture: output timing id={scenario['episode_id']} "
            f"slowmo={render_slowmo:.12g}"
        )
        preroll_end_marker = (
            f"capture: preroll end id={scenario['episode_id']} "
            f"mode=timedemo slowmo={render_slowmo:.12g} "
            f"seed={render_episode_seed}"
        )
        if not render_slowmo_matches or output_timing_marker not in console:
            raise capture.CaptureFailure(
                "render_simulation_timescale_unverified",
                f"expected={render_slowmo:.12g} "
                f"realized={realized_render_slowmo!r} "
                f"output_timing_marker={output_timing_marker in console} "
                f"log={stage / 'client_render_console.log'}",
            )
                                          
                                                                            
                                                                             
                                                                            
        if preroll_end_marker not in console:
            raise capture.CaptureFailure(
                "render_episode_seed_unverified",
                f"expected_seed={render_episode_seed} "
                f"queried_cvar={realized_render_episode_seed!r} "
                f"expected_marker={preroll_end_marker!r} "
                f"log={stage / 'client_render_console.log'}",
            )
        if not preroll_slowmo_matches:
            raise capture.CaptureFailure(
                "render_preroll_timescale_unverified",
                f"expected={render_preroll_slowmo:.12g} "
                f"realized={realized_preroll_slowmo!r} "
                f"log={stage / 'client_render_console.log'}",
            )
        if realized_render_scr_refresh != "1":
            raise capture.CaptureFailure(
                "render_screen_refresh_unverified",
                f"expected=1 realized={realized_render_scr_refresh!r} "
                f"log={stage / 'client_render_console.log'}",
            )
        if capture.HUD_POLICY_LINE not in console:
            raise capture.CaptureFailure(
                "minimal_hud_policy_failed",
                str(stage / "client_render_console.log"),
            )
        fixedstep_marker = (
            f"capture: episode reset id={scenario['episode_id']} "
            "mode=1 demo=1 demo_fixedstep=1"
        )
        if fixedstep_marker not in console:
            raise capture.CaptureFailure(
                "render_demo_preroll_fixedstep_failed",
                str(stage / "client_render_console.log"),
            )
        render_scheduling = self.render_client.scheduling_snapshot()
        if self.background_cpu_affinity is not None and not (
            render_scheduling["all_threads_match"]
            and render_scheduling["expected_cpu_affinity"]
            == sorted(self.background_cpu_affinity)
        ):
            raise capture.CaptureFailure(
                "resident_render_cpu_isolation_unverified",
                str(render_scheduling),
            )
        result = {
            "raw_avi": raw_avi,
            "frames_engine": render_dir / "frames_engine.csv",
            "audio_events_engine": (
                render_dir / "audio_events_engine.csv"
            ),
            "render_wall_seconds": render_wall_seconds,
            "render_timeout_seconds": (
                capture.configured_render_timeout_seconds()
            ),
            "render_startup_stall_seconds": (
                capture.configured_render_startup_stall_seconds()
            ),
            "offline_accelerate": bool(offline_accelerate),
            "capturevideo_realtime": bool(int(realized_realtime)),
            "render_local_slowmo": float(realized_render_slowmo),
            "render_preroll_local_slowmo": float(
                realized_preroll_slowmo
            ),
            "render_preroll_mode": "timedemo_until_episode_reset",
            "render_episode_slowmo_boundary_atomic": True,
            "render_episode_random_seed": render_episode_seed,
            "render_episode_random_seed_source": scenario_seed,
            "render_episode_random_seed_projection": (
                "unsigned_low24_exact_float_cvar_v1"
            ),
            "render_episode_rng_boundary_atomic": True,
            "render_preroll_excludes_episode_context": True,
            "effective_demo_timescale": (
                float(realized_render_slowmo) * self.live_time_scale
            ),
            "live_capture_geometry": {
                "width": LIVE_CAPTURE_WIDTH,
                "height": LIVE_CAPTURE_HEIGHT,
                "r_renderview": False,
                "scr_refresh": False,
            },
            "render_scr_refresh": True,
            "renderer": self.renderer,
            "hud_policy": capture.HUD_POLICY_LINE,
            "demo_preroll_fixedstep": (
                capture.RENDER_DEMO_PREROLL_FIXEDSTEP
            ),
            "frontend_menu_close_barrier": True,
            "frontend_menu_close_commands": list(
                FRONTEND_MENU_CLOSE_COMMANDS
            ),
            "frontend_menu_close_marker": (
                frontend_menu_close_marker
            ),
            "resident_process_reused": self.sequence > 1,
            "resident_sequence": self.sequence,
            "render_generation": render_generation,
            "render_process_recycled_after_episode": False,
            "render_process_recycle_wall_seconds": 0.0,
            "render_client_cpu_scheduling": render_scheduling,
        }
                                                                             
                                                                            
                                                                              
        recycle_seconds = self._close_render_client()
        self.render_recycle_count += 1
        result["render_process_recycled_after_episode"] = True
        result["render_process_recycle_wall_seconds"] = recycle_seconds
        result["render_recycle_count"] = self.render_recycle_count
        return result

    def execute(
        self,
        stage: Path,
        scenario: dict[str, Any],
        *,
        retry: int = 0,
    ) -> dict[str, Any]:
        attempt_id = stage.name
        live = self.run_live(stage, scenario, retry=retry)
        live["precheck"] = capture.validate_live_precheck(
            stage, scenario, live
        )
        render = self.run_render(stage, scenario, live)
        qa, package_stage = capture.qa_and_package(
            stage,
            scenario,
            live,
            render,
            attempt_id,
        )
        qa["runtime"]["resident_lane"] = {
            "enabled": True,
            "sequence": self.sequence,
            "server_reset": live["resident_server_reset"],
            "process_reused": live["resident_process_reused"],
            "process_startup_seconds": self.process_startup_seconds,
            "control_timeout_seconds": (
                capture.configured_resident_control_timeout_seconds()
            ),
        }
        (package_stage / "qa.json").write_text(
            json.dumps(qa, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "episode_id": scenario["episode_id"],
            "attempt_id": attempt_id,
            "stage": str(stage),
            "package_stage": str(package_stage),
            "qa": qa,
            "live": live,
            "render": render,
        }
