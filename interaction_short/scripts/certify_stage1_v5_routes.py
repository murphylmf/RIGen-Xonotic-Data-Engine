                      
"""Calibrate and certify the immutable Stage-1 v5 route library in parallel.

This is a server/live-client pre-certification pass, not training collection.
Each route keeps its own authoritative artifacts under ``stage1_routes``.
The append-only event stream makes the pass resumable, while the current
commit's ``CALIBRATION.json`` remains the canonical exactly-once record.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import json
import os
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage1_routes as routes              


ROOT = capture.ROOT
EXPECTED_SOURCE_COMMIT = "b40e26fd4e33b18b2002bf24beb6a78cef5fac96"
STATE_ROOT = ROOT / "manifests/stage1_foundation_v5_certification"
EVENTS_PATH = STATE_ROOT / "ROUTE_CERTIFICATION_EVENTS.jsonl"
SUMMARY_PATH = STATE_ROOT / "ROUTE_CERTIFICATION_SUMMARY.json"
RUN_LOCK_PATH = STATE_ROOT / "route_certification.lock"
EVENT_LOCK = threading.Lock()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def append_event(value: dict[str, Any]) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
                                                                              
                                                                           
                                                                       
    with EVENT_LOCK:
        with EVENTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(capture.canonical_json(value) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def route_ids() -> list[str]:
    expected = set(
        f"s1route_{index:05d}" for index in range(10_000, 14_000)
    )
    present = {
        path.parent.name
        for path in routes.PLAN_ROOT.glob("s1route_*/route_plan.json")
    }
    missing = sorted(expected - present)
    if missing:
        raise capture.CaptureFailure(
            "v5_route_plan_library_incomplete",
            capture.canonical_json(
                {"missing_count": len(missing), "first": missing[:20]}
            ),
        )
    return sorted(expected)


def calibration_record(route_id: str) -> dict[str, Any] | None:
    path = routes.CALIBRATION_ROOT / route_id / "CALIBRATION.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def classify(route_id: str) -> str:
    record = calibration_record(route_id)
    if record is None:
        return "pending"
    if record.get("source_commit") != EXPECTED_SOURCE_COMMIT:
        return "stale"
    if record.get("metrics", {}).get("passed") is True:
        return "passed"
    return "failed"


def certify_one(route_id: str, port: int) -> dict[str, Any]:
    started = time.monotonic()
    prior = classify(route_id)
    if prior == "passed":
        effective = routes.effective_plan(route_id)
        result = {
            "route_id": route_id,
            "status": "resumed_pass",
            "source_commit": EXPECTED_SOURCE_COMMIT,
            "port": port,
            "wall_seconds": 0.0,
            "metrics": effective.get("calibration_metrics", {}),
            "created_utc": capture.utc_now(),
        }
        append_event(
            {
                "schema_version": "xonotic-stage1-v5-route-event-v1",
                **result,
            }
        )
        return result
    if prior == "failed":
        record = calibration_record(route_id) or {}
        result = {
            "route_id": route_id,
            "status": "resumed_terminal_failure",
            "source_commit": EXPECTED_SOURCE_COMMIT,
            "port": port,
            "wall_seconds": 0.0,
            "metrics": record.get("metrics", {}),
            "created_utc": capture.utc_now(),
        }
        append_event(
            {
                "schema_version": "xonotic-stage1-v5-route-event-v1",
                **result,
            }
        )
        return result
    try:
        routes.calibrate(route_id, port=port)
        record = calibration_record(route_id) or {}
        status = (
            "calibrated_pass"
            if record.get("metrics", {}).get("passed") is True
            else "calibrated_failure"
        )
        detail = None
    except capture.CaptureFailure as exc:
        record = calibration_record(route_id) or {}
                                                                              
                                                                           
                                           
        status = (
            "calibrated_failure"
            if record.get("source_commit") == EXPECTED_SOURCE_COMMIT
            and record.get("metrics", {}).get("passed") is False
            else "operational_failure"
        )
        detail = {"reason": exc.reason, "detail": exc.detail}
    except Exception as exc:                                              
        record = calibration_record(route_id) or {}
        status = "operational_failure"
        detail = {
            "reason": type(exc).__name__,
            "detail": str(exc),
        }
    result = {
        "route_id": route_id,
        "status": status,
        "prior_status": prior,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "port": port,
        "wall_seconds": time.monotonic() - started,
        "metrics": record.get("metrics", {}),
        "detail": detail,
        "created_utc": capture.utc_now(),
    }
    append_event(
        {
            "schema_version": "xonotic-stage1-v5-route-event-v1",
            **result,
        }
    )
    return result


def summarize(all_ids: list[str], run_results: list[dict[str, Any]]) -> dict[str, Any]:
    current = Counter(classify(route_id) for route_id in all_ids)
    run_status = Counter(row["status"] for row in run_results)
    wall_values = [
        float(row["wall_seconds"])
        for row in run_results
        if float(row["wall_seconds"]) > 0
    ]
    report = {
        "schema_version": "xonotic-stage1-v5-route-summary-v1",
        "created_utc": capture.utc_now(),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "route_count": len(all_ids),
        "current_status": dict(sorted(current.items())),
        "this_run": {
            "rows": len(run_results),
            "status": dict(sorted(run_status.items())),
            "wall_seconds_sum": sum(wall_values),
            "wall_seconds_mean": (
                sum(wall_values) / len(wall_values)
                if wall_values
                else 0.0
            ),
        },
        "complete": current["pending"] == 0 and current["stale"] == 0,
        "passed": current["passed"],
        "failed": current["failed"],
        "events_path": str(EVENTS_PATH.relative_to(ROOT)),
    }
    atomic_json(SUMMARY_PATH, report)
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workers", type=int, default=12)
    result.add_argument("--port-base", type=int, default=28_000)
    result.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most this many non-passed routes; 0 means all.",
    )
    result.add_argument(
        "--include-passed",
        action="store_true",
        help="Also emit resume events for already-passed routes.",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    if args.workers < 1 or args.workers > 32:
        raise SystemExit("--workers must be in 1..32")
    build_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    if build_commit != EXPECTED_SOURCE_COMMIT:
        raise SystemExit(
            f"build source mismatch: expected={EXPECTED_SOURCE_COMMIT} "
            f"actual={build_commit}"
        )
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    with RUN_LOCK_PATH.open("a+", encoding="utf-8") as run_lock:
        try:
            fcntl.flock(
                run_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
            )
        except BlockingIOError:
            raise SystemExit("another v5 route certification run is active")
        all_ids = route_ids()
        selected = [
            route_id
            for route_id in all_ids
            if (
                args.include_passed
                or classify(route_id) in {"pending", "stale"}
            )
        ]
        if args.limit:
            selected = selected[: args.limit]
        indexed = [
            (route_id, args.port_base + all_ids.index(route_id))
            for route_id in selected
        ]
        print(
            capture.canonical_json(
                {
                    "event": "v5_route_certification_start",
                    "selected": len(indexed),
                    "workers": args.workers,
                    "port_base": args.port_base,
                    "created_utc": capture.utc_now(),
                }
            ),
            flush=True,
        )
        run_results: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.workers
        ) as executor:
            futures = {
                executor.submit(certify_one, route_id, port): route_id
                for route_id, port in indexed
            }
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                run_results.append(row)
                print(capture.canonical_json(row), flush=True)
        report = summarize(all_ids, run_results)
        print(json.dumps(report, indent=2, sort_keys=True), flush=True)
        return 0 if not any(
            row["status"] == "operational_failure"
            for row in run_results
        ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
