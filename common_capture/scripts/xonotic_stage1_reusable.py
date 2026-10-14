                      
"""Resident Stage-1 capture lane with hard per-episode world resets.

Only process-level resources are reused.  Every episode receives:

* a fresh server VM/world through ``restart`` or ``map``;
* a fresh live network connection and demo recording;
* a fresh demo playback / client-state reset;
* unique action, telemetry, frame, audio, and raw-video paths.

The formal worker may use this lane only through its fail-closed scheduler:
one exact ``(map, gametype)`` group per lane lifetime, a fresh server
VM/world reset for every episode, and full lane destruction on any failure or
group change.
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
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            env=capture.process_environment(),
            start_new_session=True,
        )

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


class ReusableStage1Lane:
    """One resident dedicated/live/render process triplet."""

    def __init__(
        self,
        lane_root: Path,
        *,
        build: Path,
        port: int,
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
                }
            )
            + ["+set", "port", str(self.port)]
            + ["+set", "sv_random_seed", str(scenario["seed"])]
            + ["+set", "bot_number", "1"]
            + ["+map", map_name]
            + ["+exec", "capture_episode.cfg"]
        )
        started = time.monotonic()
        self.server = ResidentProcess(
            command,
            self.lane_root / "server_resident.log",
            label="stage1-resident-server",
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

    def _start_clients(self) -> None:
        if self.live_client is not None or self.render_client is not None:
            return
        engine_net_timeout = (
            capture.configured_engine_net_timeout_seconds()
        )
        client = self.build / "bin/xonotic-local-sdl"
        common = [
            "-window",
            "-width",
            str(capture.WIDTH),
            "-height",
            str(capture.HEIGHT),
            "-sndspeed",
            str(capture.AUDIO_RATE),
            "-sndbits",
            "16",
            "-sndstereo",
        ]
        live_values = {
            "exec": "capture_client.cfg",
            "net_connecttimeout": engine_net_timeout,
            "net_messagetimeout": engine_net_timeout,
            "cl_maxfps": IDLE_CLIENT_MAXFPS,
            "cl_netfps": 64,
            "cl_damagetext": 0,
            "capture_enable": 1,
            "capture_mode": 0,
            "capture_expected_frames": capture.OUTPUT_TICKS,
            "capture_quit_on_end": 0,
        }
        render_values = {
            "exec": "capture_client.cfg",
            "cl_maxfps": IDLE_CLIENT_MAXFPS,
            "cl_damagetext": 0,
            "capture_enable": 1,
            "capture_mode": 1,
            "capture_expected_frames": capture.OUTPUT_TICKS,
            "capture_quit_on_end": 0,
            "scr_menuforcewhiledisconnected": 0,
        }
        started = time.monotonic()
        self.live_client = ResidentProcess(
            capture.command_base(client, self.live_user)
            + common
            + capture.cvar_args(live_values),
            self.lane_root / "live_client_resident.log",
            label="stage1-resident-live-client",
        )
        self.render_client = ResidentProcess(
            capture.command_base(client, self.render_user)
            + common
            + capture.cvar_args(render_values),
            self.lane_root / "render_client_resident.log",
            label="stage1-resident-render-client",
        )
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
        )
        self.live_client.wait_for(
            "GL_RENDERER:",
            start=0,
            timeout_seconds=control_timeout,
        )
        self.render_client.wait_for(
            "GL_RENDERER:",
            start=0,
            timeout_seconds=control_timeout,
        )
        self.process_startup_seconds["clients_parallel"] = (
            time.monotonic() - started
        )
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
        values = capture.server_cvars(scenario, self.port)
        exec_name = str(values.pop("exec"))
        map_name = str(values.pop("map"))
        values["capture_server_action_file"] = str(server_action_rel)
        values["capture_server_log"] = str(server_log_rel)
        if route_plan:
            values["capture_route_file"] = str(route_rel)
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
        self._start_clients()
        if self.live_client is None or self.server is None:
            raise AssertionError("resident processes missing")
        self.current_map = map_name
        self.current_gametype = gametype
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
        )

        live_slice_start = self.live_client.offset()
        live_dir = stage / "live"
        demo_name = token
        action_path = stage / "actions_requested.csv"
        self.live_client.send_confirmed(
            [
                "cl_maxfps 128",
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
        self.live_client.send(
            f"cl_maxfps {IDLE_CLIENT_MAXFPS}"
        )
        live_wall_seconds = time.monotonic() - episode_started

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
        if "loaded 384 actions" not in live_console:
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
        }

    def run_render(
        self,
        stage: Path,
        scenario: dict[str, Any],
        live: dict[str, Any],
    ) -> dict[str, Any]:
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
        started = time.monotonic()
        control_timeout = (
            capture.configured_resident_control_timeout_seconds()
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
                f"cl_capturevideo_nameformat {_console_quote(prefix)}",
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
        self.render_client.send(f"playdemo demos/{demo_name}")
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
        self.render_client.send(
            f"cl_maxfps {IDLE_CLIENT_MAXFPS}"
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
        return {
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
        }

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
