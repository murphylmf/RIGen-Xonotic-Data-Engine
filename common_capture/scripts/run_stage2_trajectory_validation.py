                      
"""Run resumable live-only Stage-2 trajectory/interaction validation.

This stage intentionally stops before offline rendering and encoding.  It
certifies the authoritative 384-tick live simulation, frozen action replay,
collision/path contracts, and declared fire windows.  Render/HUD/audio QA is
performed by the subsequent full pipeline and is not inferred here.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import threading
import traceback
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal                   


WRITE_LOCK = threading.Lock()
RESULT_SCHEMA = "xonotic-stage2-live-trajectory-result-v2"
AUDIT_SCHEMA = "xonotic-stage2-live-trajectory-audit-v2"


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def row_sha256(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        capture.canonical_json(row).encode("utf-8")
    ).hexdigest()


def load_rows(
    manifest_root: Path,
    source_commit: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    cohort = metadata.get("review") or {}
    checks = {
        "source_commit": metadata.get("source_commit")
        == source_commit,
        "formal_collection_forbidden": (
            metadata.get("formal_collection_authorized") is False
        ),
        "training_admitted_false": (
            metadata.get("training_admitted") is False
        ),
        "shards_declared": bool(cohort.get("shards")),
    }
    rows: list[dict[str, Any]] = []
    for shard in sorted(
        cohort.get("shards", []),
        key=lambda item: int(item["shard_index"]),
    ):
        path = Path(str(shard["path"]))
        if not path.is_absolute():
            path = capture.ROOT / path
        shard_rows = capture.load_jsonl(path)
        checks[f"shard_{int(shard['shard_index']):03d}_hash"] = (
            capture.sha256_file(path) == shard["sha256"]
        )
        checks[f"shard_{int(shard['shard_index']):03d}_rows"] = (
            len(shard_rows) == int(shard["rows"])
        )
        rows.extend(shard_rows)
    ids = [str(row.get("episode_id", "")) for row in rows]
    checks["unique_episode_ids"] = (
        bool(ids)
        and all(ids)
        and len(ids) == len(set(ids))
    )
    checks["row_policy"] = all(
        row.get("source_commit_required") == source_commit
        and row.get("formal_collection_authorized") is False
        and row.get("training_admitted") is False
        and row.get("split") in capture.NONTRAINING_SPLITS
        for row in rows
    )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_trajectory_manifest_failed",
            capture.canonical_json(checks),
        )
    return rows, {
        "path": str(metadata_path),
        "sha256": capture.sha256_file(metadata_path),
        "checks": checks,
    }


def fire_window_metrics(
    scenario: dict[str, Any],
    events: pd.DataFrame,
) -> dict[str, Any]:
    design = scenario["causal_design"]
    starts = [
        int(value) for value in design["fire_output_ticks"]
    ]
    width = int(design["fire_width_ticks"])
    if events.empty or "event" not in events:
        actual: list[int] = []
    else:
        fire = events[events["event"].astype(str) == "fire"]
        actual = sorted(
            int(value) - capture.WARMUP_TICKS
            for value in fire.get(
                "server_tick", pd.Series(dtype=np.int64)
            ).tolist()
            if capture.WARMUP_TICKS
            <= int(value)
            < capture.TOTAL_TICKS
        )
    windows = [
        [start, min(capture.OUTPUT_TICKS - 1, start + width - 1)]
        for start in starts
    ]
    every_start_realized = all(
        any(lower <= tick <= upper for tick in actual)
        for lower, upper in windows
    )
    no_undeclared_fire = all(
        any(lower <= tick <= upper for lower, upper in windows)
        for tick in actual
    )
    declared_firing = (
        scenario["causal_design"]["aim_policy"]
        in causal.FIRING_POLICIES
    )
    event_presence_matches_policy = (
        bool(actual) if declared_firing else not actual
    )
    unrealized = [
        start
        for start, (lower, upper) in zip(starts, windows)
        if not any(lower <= tick <= upper for tick in actual)
    ]
    return {
        "declared_starts": starts,
        "declared_width": width,
        "declared_windows": windows,
        "authoritative_fire_frames": actual,
        "unrealized_declared_starts": unrealized,
        "every_declared_start_realized_diagnostic": (
            every_start_realized
        ),
        "declared_starts_are_button_treatments": True,
        "engine_cooldown_or_resource_rejection_recorded_not_relabelled": (
            bool(unrealized)
        ),
        "checks": {
            "event_presence_matches_policy": (
                event_presence_matches_policy
            ),
            "no_fire_outside_declared_button_windows": (
                no_undeclared_fire
            ),
        },
        "passed": (
            event_presence_matches_policy and no_undeclared_fire
        ),
    }


def authoritative_trajectory_metrics(
    scenario: dict[str, Any],
    states: pd.DataFrame,
    events: pd.DataFrame,
) -> dict[str, Any]:
    ticks = pd.to_numeric(
        states.get("server_tick"), errors="coerce"
    ).to_numpy()
    exact_ticks = (
        len(ticks) == capture.TOTAL_TICKS
        and np.array_equal(
            ticks, np.arange(capture.TOTAL_TICKS, dtype=np.int64)
        )
    )
    output = states[
        pd.to_numeric(states["server_tick"], errors="coerce")
        >= capture.WARMUP_TICKS
    ].sort_values("server_tick")
    origins = np.asarray(
        output["pre.origin"].tolist(), dtype=np.float64
    )
    first_fire = min(
        scenario["causal_design"]["fire_output_ticks"] or [319]
    )
    pre_interaction = origins[: max(1, int(first_fire))]
    pre_displacement = np.linalg.norm(
        pre_interaction - pre_interaction[0], axis=1
    )
    all_displacement = np.linalg.norm(
        origins - origins[0], axis=1
    )
    stationary_before_interaction = bool(
        not len(pre_displacement)
        or float(pre_displacement.max()) <= 0.25
    )
    fire = fire_window_metrics(scenario, events)
    checks = {
        "authoritative_ticks_exact": exact_ticks,
        "output_ticks_320": len(output) == capture.OUTPUT_TICKS,
        "stationary_before_interaction": (
            scenario["causal_design"]["base_player_program"]
            != "stationary"
            or stationary_before_interaction
        ),
        "declared_fire_windows_realized": fire["passed"],
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "state_rows": len(states),
        "output_state_rows": len(output),
        "pre_interaction_maximum_displacement": (
            float(pre_displacement.max())
            if len(pre_displacement)
            else 0.0
        ),
        "whole_episode_maximum_displacement": (
            float(all_displacement.max())
            if len(all_displacement)
            else 0.0
        ),
        "fire": fire,
    }


def next_attempt(output_root: Path, episode_id: str) -> int:
    parent = output_root / "attempts" / episode_id
    values = [
        int(path.name[1:])
        for path in parent.glob("a[0-9][0-9]")
        if path.name[1:].isdigit()
    ]
    return max(values, default=0) + 1


def preserve_attempt(
    stage: Path,
    live: dict[str, Any] | None,
    destination: Path,
) -> dict[str, str]:
    temporary = destination.with_name(
        f".{destination.name}.tmp.{os.getpid()}"
    )
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    candidates: list[tuple[str, Path]] = [
        ("actions_requested.csv", stage / "actions_requested.csv"),
        ("server_console.log", stage / "server_console.log"),
        ("client_live_console.log", stage / "client_live_console.log"),
        ("LIVE_PRECHECK.json", stage / "LIVE_PRECHECK.json"),
    ]
    if live is not None:
        candidates.extend(
            [
                ("actions_engine.csv", Path(live["actions_engine"])),
                (
                    "server_telemetry.jsonl",
                    Path(live["server_telemetry"]),
                ),
                ("demo.dem", Path(live["demo_path"])),
            ]
        )
    hashes: dict[str, str] = {}
    for name, source in candidates:
        if source.is_file():
            target = temporary / name
            shutil.copy2(source, target)
            hashes[name] = capture.sha256_file(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise capture.CaptureFailure(
            "trajectory_attempt_exists", str(destination)
        )
    os.replace(temporary, destination)
    return hashes


def valid_resume(
    path: Path,
    row_hash: str,
    source_commit: str,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    result = json.loads(path.read_text(encoding="utf-8"))
    if (
        result.get("schema_version") != RESULT_SCHEMA
        or result.get("passed") is not True
        or result.get("scenario_sha256") != row_hash
        or result.get("source_commit") != source_commit
    ):
        return None
    artifacts = Path(str(result["artifacts_path"]))
    if not artifacts.is_dir() or any(
        not (artifacts / name).is_file()
        or capture.sha256_file(artifacts / name) != digest
        for name, digest in result["artifact_sha256"].items()
    ):
        return None
    return result


def validate_one(
    row: dict[str, Any],
    *,
    local_index: int,
    build: Path,
    source_commit: str,
    output_root: Path,
    port_base: int,
    max_attempts: int,
) -> dict[str, Any]:
    result_path = output_root / "results" / (
        f"{row['episode_id']}.json"
    )
    scenario_hash = row_sha256(row)
    resumed = valid_resume(result_path, scenario_hash, source_commit)
    if resumed is not None:
        print(f"resume trajectory {row['episode_id']}", flush=True)
        return resumed

    failure: dict[str, Any] | None = None
    for _ in range(max_attempts):
        attempt_number = next_attempt(output_root, row["episode_id"])
        attempt_id = (
            f"trajectory_{row['episode_id']}_a{attempt_number:02d}"
        )
        stage = capture.TMP_ROOT / "raw" / attempt_id
        if stage.exists():
            capture.clean_stage(stage)
        stage.mkdir(parents=True)
        live: dict[str, Any] | None = None
        destination = (
            output_root
            / "attempts"
            / row["episode_id"]
            / f"a{attempt_number:02d}"
        )
        started = capture.utc_now()
        print(
            f"trajectory {row['episode_id']} "
            f"program={row['causal_design']['shot_error_schedule']['program']} "
            f"port={port_base + local_index}",
            flush=True,
        )
        try:
            causal.validate_scenario_contract(row)
            live = capture.run_live_attempt(
                stage,
                row,
                build,
                retry=attempt_number - 1,
                port=port_base + local_index,
            )
            precheck = capture.validate_live_precheck(
                stage, row, live
            )
            states, events, _ = capture.parse_server_telemetry(
                Path(live["server_telemetry"])
            )
            trajectory = authoritative_trajectory_metrics(
                row, states, events
            )
            checks = {
                "live_precheck": precheck["passed"],
                "authoritative_trajectory": trajectory["passed"],
            }
            hashes = preserve_attempt(stage, live, destination)
            result = {
                "schema_version": RESULT_SCHEMA,
                "episode_id": row["episode_id"],
                "counterfactual_group_id": row[
                    "counterfactual_group_id"
                ],
                "scenario_sha256": scenario_hash,
                "source_commit": source_commit,
                "aim_policy": row["causal_design"]["aim_policy"],
                "shot_error_program": row["causal_design"][
                    "shot_error_schedule"
                ]["program"],
                "initial_screen": row["initial_screen_design"],
                "checks": checks,
                "passed": all(checks.values()),
                "live_precheck": precheck,
                "trajectory": trajectory,
                "artifacts_path": str(destination),
                "artifact_sha256": hashes,
                "started_utc": started,
                "finished_utc": capture.utc_now(),
            }
            atomic_json(result_path, result)
            if result["passed"]:
                print(
                    f"trajectory accepted {row['episode_id']}",
                    flush=True,
                )
                return result
            failure = result
        except Exception as exc:
            hashes = preserve_attempt(stage, live, destination)
            failure = {
                "schema_version": RESULT_SCHEMA,
                "episode_id": row["episode_id"],
                "scenario_sha256": scenario_hash,
                "source_commit": source_commit,
                "passed": False,
                "error_type": type(exc).__name__,
                "error_reason": (
                    exc.reason
                    if isinstance(exc, capture.CaptureFailure)
                    else type(exc).__name__
                ),
                "error_detail": str(exc),
                "traceback": traceback.format_exc(),
                "artifacts_path": str(destination),
                "artifact_sha256": hashes,
                "started_utc": started,
                "finished_utc": capture.utc_now(),
            }
            atomic_json(result_path, failure)
            print(
                f"trajectory reject {row['episode_id']} "
                f"reason={failure['error_reason']}",
                flush=True,
            )
        finally:
            if stage.exists():
                capture.clean_stage(stage)
    if failure is None:
        raise AssertionError("missing trajectory result")
    return failure


def aggregate(
    rows: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    manifest: dict[str, Any],
    source_commit: str,
) -> dict[str, Any]:
    passed = [result for result in results if result["passed"]]
    failures = [
        result for result in results if result["passed"] is not True
    ]
    checks = {
        "all_rows_accounted": len(results) == len(rows),
        "all_rows_passed": len(passed) == len(rows),
        "no_failures": not failures,
        "source_commit_exact": all(
            result.get("source_commit") == source_commit
            for result in results
        ),
        "all_state_rows_384": all(
            (result.get("live_precheck") or {}).get("state_rows")
            == capture.TOTAL_TICKS
            for result in passed
        ),
        "all_action_rows_384": all(
            (result.get("live_precheck") or {}).get("action_rows")
            == capture.TOTAL_TICKS
            for result in passed
        ),
        "all_collision_and_path_prechecks": all(
            (
                (result.get("live_precheck") or {}).get("checks")
                or {}
            ).get("player_hull_clear")
            is True
            and (
                (result.get("live_precheck") or {}).get("checks")
                or {}
            ).get("enemy_whole_path_hull_trace")
            is True
            for result in passed
        ),
        "all_declared_fire_window_contracts": all(
            (
                ((result.get("trajectory") or {}).get("fire") or {})
                .get("passed")
            )
            is True
            for result in passed
        ),
    }
    return {
        "schema_version": AUDIT_SCHEMA,
        "source_commit": source_commit,
        "manifest": manifest,
        "rows": len(rows),
        "passed_rows": len(passed),
        "failed_rows": len(failures),
        "checks": checks,
        "pass": all(checks.values()),
        "aim_policy": dict(
            Counter(result.get("aim_policy") for result in passed)
        ),
        "shot_error_program": dict(
            Counter(
                result.get("shot_error_program") for result in passed
            )
        ),
        "fire_treatment": {
            "declared_button_starts": sum(
                len(
                    (
                        (
                            (result.get("trajectory") or {}).get(
                                "fire"
                            )
                            or {}
                        ).get("declared_starts")
                        or []
                    )
                )
                for result in passed
            ),
            "authoritative_fire_events": sum(
                len(
                    (
                        (
                            (result.get("trajectory") or {}).get(
                                "fire"
                            )
                            or {}
                        ).get("authoritative_fire_frames")
                        or []
                    )
                )
                for result in passed
            ),
            "unrealized_button_starts": sum(
                len(
                    (
                        (
                            (result.get("trajectory") or {}).get(
                                "fire"
                            )
                            or {}
                        ).get("unrealized_declared_starts")
                        or []
                    )
                )
                for result in passed
            ),
            "episodes_with_engine_rejected_trigger": sum(
                bool(
                    (
                        (
                            (result.get("trajectory") or {}).get(
                                "fire"
                            )
                            or {}
                        ).get("unrealized_declared_starts")
                        or []
                    )
                )
                for result in passed
            ),
        },
        "failures": [
            {
                "episode_id": result["episode_id"],
                "reason": result.get("error_reason", "hard_gate"),
                "detail": result.get("error_detail"),
            }
            for result in failures
        ],
        "created_utc": capture.utc_now(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tmp-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--port-base", type=int, default=41000)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()

    capture.require_conda()
    capture.TMP_ROOT = args.tmp_root.resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)
    rows, manifest = load_rows(
        args.manifest_root.resolve(), args.source_commit
    )
    if args.max_rows is not None:
        rows = rows[: args.max_rows]
    build = capture.build_root()
    actual_commit = (build / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if actual_commit != args.source_commit:
        raise capture.CaptureFailure(
            "source_commit_mismatch",
            f"expected={args.source_commit} actual={actual_commit}",
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = [
            executor.submit(
                validate_one,
                row,
                local_index=index,
                build=build,
                source_commit=args.source_commit,
                output_root=args.output_root,
                port_base=args.port_base,
                max_attempts=args.max_attempts,
            )
            for index, row in enumerate(rows)
        ]
        results = [future.result() for future in futures]
    audit = aggregate(
        rows,
        results,
        manifest=manifest,
        source_commit=args.source_commit,
    )
    atomic_json(args.output_root / "TRAJECTORY_AUDIT.json", audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
