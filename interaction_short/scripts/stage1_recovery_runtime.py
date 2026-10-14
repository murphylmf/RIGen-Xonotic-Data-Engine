                      
"""Run one Stage-1 recovery shard with isolated journals and safe warm-up.

This module intentionally wraps the frozen r5 worker instead of modifying it.
The running r5 job can therefore finish or be stopped without importing
partially changed source files.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_stage1_manifest_shard as worker              
import xonotic_capture as capture              
import xonotic_stage1_reusable as reusable              


NAMESPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_INSTALLED = False


def recovery_retryable_failure(
    exc: Exception,
    base_classifier: Callable[[Exception], bool],
) -> bool:
    """Preserve deterministic QA semantics hidden by warm-up wrapping.

    The resident controller wraps every warm-up exception as
    ``resident_warmup_failed`` so bootstrap faults remain retryable.  That
    wrapper also used to turn a deterministic ``live_precheck_failed`` or
    ``qa_gate_failed`` into an operational retry forever.  Only unwrap those
    two structured QA failures; malformed payloads and every other warm-up
    failure retain the conservative retryable behavior.
    """

    if not (
        isinstance(exc, capture.CaptureFailure)
        and exc.reason == "resident_warmup_failed"
    ):
        return base_classifier(exc)
    try:
        payload = json.loads(str(exc.detail))
    except (json.JSONDecodeError, TypeError, ValueError):
        return base_classifier(exc)
    nested_reason = str(payload.get("reason", ""))
    if nested_reason not in {
        "live_precheck_failed",
        "qa_gate_failed",
    }:
        return base_classifier(exc)
    nested_detail = str(payload.get("detail", ""))
    prefix = f"{nested_reason}: "
    if nested_detail.startswith(prefix):
        nested_detail = nested_detail[len(prefix) :]
    nested = capture.CaptureFailure(nested_reason, nested_detail)
    return base_classifier(nested)


def _load_contract() -> tuple[dict[str, Any], dict[str, int]]:
    metadata_value = os.environ.get("STAGE1_RECOVERY_METADATA", "")
    if not metadata_value:
        raise capture.CaptureFailure(
            "recovery_metadata_env_missing",
            "STAGE1_RECOVERY_METADATA",
        )
    metadata_path = Path(metadata_value).resolve()
    if not metadata_path.is_file():
        raise capture.CaptureFailure(
            "recovery_metadata_missing", str(metadata_path)
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    recovery = metadata.get("recovery") or {}
    namespace = str(recovery.get("namespace", ""))
    configured_namespace = os.environ.get(
        "STAGE1_RECOVERY_NAMESPACE", namespace
    )
    checks = {
        "schema": recovery.get("schema_version")
        == "xonotic-stage1-recovery-rebalance-v1",
        "namespace": bool(NAMESPACE_PATTERN.fullmatch(namespace)),
        "namespace_matches_env": configured_namespace == namespace,
        "source_job_stopped": recovery.get("source_job_stopped") is True,
        "terminal_snapshot_sealed": recovery.get(
            "terminal_snapshot_sealed"
        )
        is True,
        "only_nonterminal_candidates": recovery.get(
            "only_nonterminal_candidates"
        )
        is True,
        "warmup_nested_qa_retry_semantics_preserved": recovery.get(
            "warmup_nested_qa_retry_semantics_preserved"
        )
        is True,
        "exactly_once_output_root_reused": recovery.get(
            "exactly_once_output_root_reused"
        )
        is True,
        "output_root_declared": bool(
            recovery.get("output_root")
            and Path(str(recovery["output_root"])).is_absolute()
        ),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "recovery_contract_failed",
            capture.canonical_json(checks),
        )
    attempt_reference = recovery.get("attempt_base") or {}
    attempt_path = capture.locked_root_artifact(
        str(attempt_reference.get("path", "")),
        str(attempt_reference.get("sha256", "")),
        "stage1_recovery_attempt_base",
    )
    attempt_document = json.loads(
        attempt_path.read_text(encoding="utf-8")
    )
    if (
        attempt_document.get("schema_version")
        != "xonotic-stage1-recovery-attempt-base-v1"
        or attempt_document.get("namespace") != namespace
    ):
        raise capture.CaptureFailure(
            "recovery_attempt_base_contract_failed",
            str(attempt_path),
        )
    raw_attempts = attempt_document.get("attempt_base") or {}
    attempt_base: dict[str, int] = {}
    for episode_id, value in raw_attempts.items():
        if not isinstance(episode_id, str) or not episode_id:
            raise capture.CaptureFailure(
                "recovery_attempt_base_invalid_episode",
                repr(episode_id),
            )
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise capture.CaptureFailure(
                "recovery_attempt_base_invalid_value",
                f"{episode_id}={value!r}",
            ) from exc
        if parsed < 0:
            raise capture.CaptureFailure(
                "recovery_attempt_base_invalid_value",
                f"{episode_id}={parsed}",
            )
        attempt_base[episode_id] = parsed
    expected_rows = int(recovery.get("pending_candidates", -1))
    if len(attempt_base) != expected_rows:
        raise capture.CaptureFailure(
            "recovery_attempt_base_row_count",
            f"expected={expected_rows} actual={len(attempt_base)}",
        )
    os.environ["STAGE1_RECOVERY_NAMESPACE"] = namespace
    return recovery, attempt_base


def install() -> None:
    """Install the recovery-only runtime adaptations once."""

    global _INSTALLED
    if _INSTALLED:
        return
    recovery, attempt_base = _load_contract()
    namespace = str(recovery["namespace"])
    warmup_concurrency = int(
        os.environ.get(
            "XONOTIC_RESIDENT_WARMUP_CONCURRENCY",
            recovery.get("warmup_concurrency", 4),
        )
    )
    if not 1 <= warmup_concurrency <= 12:
        raise capture.CaptureFailure(
            "recovery_warmup_concurrency_invalid",
            str(warmup_concurrency),
        )
    if warmup_concurrency != int(
        recovery.get("warmup_concurrency", -1)
    ):
        raise capture.CaptureFailure(
            "recovery_warmup_concurrency_drift",
            (
                f"metadata={recovery.get('warmup_concurrency')} "
                f"runtime={warmup_concurrency}"
            ),
        )
    warmup_admission = threading.BoundedSemaphore(warmup_concurrency)

    original_start_server = reusable.ReusableStage1Lane._start_server

    def start_server_ready(
        self: reusable.ReusableStage1Lane,
        scenario: dict[str, Any],
        values: dict[str, Any],
        map_name: str,
        exec_name: str,
    ) -> int:
        started = time.monotonic()
        result = original_start_server(
            self, scenario, values, map_name, exec_name
        )
        if self.server is None:
            raise capture.CaptureFailure(
                "resident_server_missing_after_start", map_name
            )
        self.server.wait_for(
            "Server spawned.",
            start=0,
            timeout_seconds=(
                capture.configured_resident_control_timeout_seconds()
            ),
        )
        self.process_startup_seconds["server_network_ready"] = (
            time.monotonic() - started
        )
        return result

    reusable.ReusableStage1Lane._start_server = start_server_ready

    original_warmup = worker.ResidentLaneController._warmup

    def admitted_warmup(
        self: worker.ResidentLaneController,
        lane: reusable.ReusableStage1Lane,
        scenario: dict[str, Any],
    ) -> None:
        queued = time.monotonic()
        with warmup_admission:
            lane.process_startup_seconds[
                "warmup_admission_wait"
            ] = time.monotonic() - queued
            return original_warmup(self, lane, scenario)

    worker.ResidentLaneController._warmup = admitted_warmup

    def recovery_shard_paths(
        output_root: Path,
        index: int,
        count: int,
        wave: str = "primary",
    ) -> dict[str, Path]:
        if wave not in {"primary", "replenishment"}:
            raise capture.CaptureFailure(
                "invalid_candidate_wave", wave
            )
        root = (
            Path(output_root)
            / "manifests"
            / "recovery_runs"
            / namespace
            / "shards"
            / wave
            / worker.common.shard_tag(index, count)
        )
        return {
            "root": root,
            "accepted": root / "accepted_candidates.jsonl",
            "rejects": root / "rejects.jsonl",
            "queue": root / "queue_events.jsonl",
            "lock": root / "worker.lock",
        }

    worker.shard_paths = recovery_shard_paths

    original_retryable_failure = worker.common.retryable_failure

    def classify_recovery_failure(exc: Exception) -> bool:
        return recovery_retryable_failure(
            exc, original_retryable_failure
        )

    worker.common.retryable_failure = classify_recovery_failure

    original_next_attempt_index = worker.next_attempt_index

    def recovery_next_attempt_index(
        paths: dict[str, Path], episode_id: str
    ) -> int:
        if episode_id not in attempt_base:
            raise capture.CaptureFailure(
                "episode_absent_from_recovery_attempt_base",
                episode_id,
            )
        return max(
            attempt_base[episode_id],
            original_next_attempt_index(paths, episode_id),
        )

    worker.next_attempt_index = recovery_next_attempt_index

    original_command_run = worker.command_run

    def recovery_command_run(args: Any) -> int:
        declared_output_root = Path(
            str(recovery["output_root"])
        ).resolve()
        actual_output_root = Path(args.output_root).resolve()
        if actual_output_root != declared_output_root:
            raise capture.CaptureFailure(
                "recovery_output_root_mismatch",
                (
                    f"declared={declared_output_root} "
                    f"actual={actual_output_root}"
                ),
            )
        runtime_checks = {
            "workers": int(args.workers)
            == int(recovery["steady_lane_limit"]),
            "execution_mode": args.execution_mode == "resident",
            "live_concurrency": int(args.live_concurrency)
            == int(recovery["live_concurrency"]),
            "render_concurrency": int(args.render_concurrency)
            == int(recovery["render_concurrency"]),
            "sdl_concurrency": int(args.sdl_concurrency)
            == int(recovery["sdl_concurrency"]),
            "encode_concurrency": int(args.encode_concurrency)
            == int(recovery["encode_concurrency"]),
            "x264_threads": int(args.x264_threads)
            == int(recovery["x264_threads"]),
            "render_timeout_seconds": float(
                args.render_timeout_seconds
            )
            == 240.0,
            "max_operational_attempts": int(
                args.max_operational_attempts
            )
            == 2,
        }
        if not all(runtime_checks.values()):
            raise capture.CaptureFailure(
                "recovery_runtime_configuration_drift",
                capture.canonical_json(runtime_checks),
            )
        input_rows = capture.load_jsonl(
            Path(args.input_manifest).resolve()
        )
        missing_attempt_base = sorted(
            str(row["episode_id"])
            for row in input_rows
            if str(row["episode_id"]) not in attempt_base
        )
        if missing_attempt_base:
            raise capture.CaptureFailure(
                "recovery_manifest_attempt_base_mismatch",
                capture.canonical_json(missing_attempt_base[:20]),
            )
        result = int(original_command_run(args))
        paths = recovery_shard_paths(
            Path(args.output_root).resolve(),
            int(args.shard_index),
            int(args.shard_count),
            "primary",
        )
        recovery_runtime = {
            "namespace": namespace,
            "server_initial_ready_marker": "Server spawned.",
            "server_ready_before_client_start": True,
            "warmup_concurrency": warmup_concurrency,
            "steady_lane_limit": int(args.workers),
            "journal_namespace_isolated": True,
            "attempt_numbers_continue_from_snapshot": True,
            "warmup_nested_qa_retry_semantics_preserved": True,
            "terminal_snapshot_sha256": recovery.get(
                "terminal_snapshot_sha256"
            ),
            "declared_output_root": str(declared_output_root),
        }
        for name in ("RUN_METADATA.json", "RUN_RESULT.json"):
            path = paths["root"] / name
            if not path.is_file():
                continue
            document = json.loads(path.read_text(encoding="utf-8"))
            document["recovery_runtime"] = recovery_runtime
            worker.common.atomic_json(path, document)
        return result

    worker.command_run = recovery_command_run
    _INSTALLED = True


def main() -> int:
    try:
        install()
        return worker.main()
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
