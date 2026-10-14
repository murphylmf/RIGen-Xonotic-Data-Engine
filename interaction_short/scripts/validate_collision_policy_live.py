                      
"""Run one non-training scenario through the live collision QA gate.

This is a focused regression entrypoint.  It never publishes an episode and
leaves the raw attempt directory in XONOTIC_CAPTURE_TMP for inspection.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import xonotic_capture as capture
import xonotic_stage1_review as review              


def load_scenario(manifest: Path, episode_id: str) -> dict[str, Any]:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("episode_id") == episode_id:
            if row.get("formal_collection_authorized") is True:
                raise SystemExit(
                    "refusing formal/training scenario in collision regression"
                )
            return row
    raise SystemExit(f"episode not found: {episode_id}")


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument(
        "--expect",
        required=True,
        choices=("pass", "collision_reject"),
    )
    parser.add_argument(
        "--planned-visible-collision",
        action="store_true",
        help=(
            "Predeclare a visible-wall-contact positive control. "
            "This is diagnostic-only and never changes the source manifest."
        ),
    )
    parser.add_argument(
        "--movement-profile",
        choices=tuple(sorted(capture.STAGE1_TEMPORAL_PROFILES)),
        help="Diagnostic action-profile override for the live positive control.",
    )
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    scenario = load_scenario(args.manifest, args.episode_id)
    overrides: dict[str, Any] = {}
    if args.movement_profile:
        scenario["action_design"]["movement_profile"] = args.movement_profile
        overrides["action_design.movement_profile"] = args.movement_profile
    if args.planned_visible_collision:
        scenario["collision_design"] = {
            "schema_version": "xonotic-stage1-collision-design-v1",
            "intent": capture.VISIBLE_COLLISION_INTENT,
        }
        overrides["collision_design.intent"] = (
            capture.VISIBLE_COLLISION_INTENT
        )
    attempt_id = f"{args.episode_id}_a01"
    stage = capture.TMP_ROOT / "raw" / attempt_id
    report: dict[str, Any] = {
        "schema_version": "xonotic-collision-live-regression-v1",
        "episode_id": args.episode_id,
        "expected_result": args.expect,
        "manifest": str(args.manifest.resolve()),
        "build": str(capture.build_root()),
        "source_commit": (
            capture.build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip(),
        "stage": str(stage),
        "port": args.port,
        "created_utc": capture.utc_now(),
        "diagnostic_overrides": overrides,
    }
    exit_code = 1
    try:
        result = capture.execute_attempt(
            scenario,
            retry=0,
            publish=False,
            port=args.port,
        )
        blockage = result["qa"]["telemetry"]["movement_blockage"]
        report.update(
            {
                "observed_result": "pass",
                "passed": args.expect == "pass",
                "qa_path": str(Path(result["stage"]) / "package/qa.json"),
                "collision": blockage,
                "hard_gates": {
                    name: result["qa"]["hard_gates"][name]
                    for name in (
                        "player_movement_contact_telemetry",
                        "player_collision_policy",
                    )
                },
            }
        )
        exit_code = 0 if report["passed"] else 1
    except capture.CaptureFailure as exc:
        detail: Any = exc.detail
        if exc.reason == "qa_gate_failed":
            try:
                detail = json.loads(exc.detail)
            except json.JSONDecodeError:
                pass
        failed = detail.get("failed", []) if isinstance(detail, dict) else []
        collision = (
            detail.get("movement_blockage")
            if isinstance(detail, dict)
            else None
        )
        expected_reject = (
            args.expect == "collision_reject"
            and exc.reason == "qa_gate_failed"
            and "player_collision_policy" in failed
            and "player_movement_contact_telemetry" not in failed
        )
        report.update(
            {
                "observed_result": "reject",
                "passed": expected_reject,
                "failure_reason": exc.reason,
                "failure_detail": detail,
                "collision": collision,
            }
        )
        exit_code = 0 if expected_reject else 1

    write_json_atomic(args.report, report)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
