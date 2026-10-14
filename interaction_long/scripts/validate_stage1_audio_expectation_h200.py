                      
"""Run one silent and one audible formal row through a resident H200 lane."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_stage1_manifest_shard as worker              
import xonotic_capture as capture              


DEFAULT_SILENT_EPISODE = "s1v5f_s1v5p_003896_v03"
DEFAULT_AUDIBLE_EPISODE = "s1v5f_s1v5p_000286_v00"


def find_rows(
    manifest_root: Path, episode_ids: set[str]
) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(
        (manifest_root / "shards/primary").glob("*.jsonl")
    ):
        for row in capture.load_jsonl(path):
            episode_id = str(row["episode_id"])
            if episode_id in episode_ids:
                found[episode_id] = row
        if found.keys() == episode_ids:
            break
    if found.keys() != episode_ids:
        raise capture.CaptureFailure(
            "audio_h200_validation_row_missing",
            capture.canonical_json(
                {
                    "requested": sorted(episode_ids),
                    "found": sorted(found),
                }
            ),
        )
    return found


def preserve_case(
    output_root: Path,
    episode_id: str,
    result: dict[str, Any],
) -> Path:
    destination = output_root / "cases" / episode_id
    if destination.exists():
        raise capture.CaptureFailure(
            "audio_h200_validation_destination_exists",
            str(destination),
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(result["package_stage"]), destination)
    stage = Path(result["stage"])
    console_root = destination / "capture_consoles"
    console_root.mkdir()
    for name in (
        "server_console.log",
        "client_live_console.log",
        "client_render_console.log",
    ):
        source = stage / name
        if source.is_file():
            shutil.copy2(source, console_root / name)
    return destination


def case_report(
    row: dict[str, Any],
    scenario: dict[str, Any],
    result: dict[str, Any],
    destination: Path,
) -> dict[str, Any]:
    qa = result["qa"]
    audio = qa["audio"]
    policy = scenario["audio_expectation_policy"]
    return {
        "episode_id": row["episode_id"],
        "map": row["map"],
        "gametype": row["gametype"],
        "weapon_action": (
            row.get("action_design") or {}
        ).get("weapon_action"),
        "manifest_declared_expects_sound": row["expects_sound"],
        "runtime_expects_sound": scenario["expects_sound"],
        "audio_expectation_policy": policy,
        "audio_peak_s16": audio["peak_s16"],
        "audio_rms_s16": audio["rms_s16"],
        "audio_samples_per_channel": audio["samples_per_channel"],
        "frames": qa["video"]["frames"],
        "mapping_rate": qa["mapping"]["success_rate"],
        "renderer": qa["runtime"]["renderer"],
        "realized_gametype": qa["mode"]["realized_gametype"],
        "resident_lane": qa["runtime"]["resident_lane"],
        "failed_hard_gates": sorted(
            name
            for name, passed in qa["hard_gates"].items()
            if not passed
        ),
        "package": str(destination),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-root",
        default=str(
            capture.ROOT
            / (
                "manifests/"
                "stage1_foundation_v5_formal_56x1_runtime_r2"
            )
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(
            capture.ROOT
            / "stage1_audio_expectation_h200_validation_20260729"
        ),
    )
    parser.add_argument(
        "--tmp-root",
        default="./tmp/xonotic-stage1-audio-fix-validation-20260729",
    )
    parser.add_argument("--port", type=int, default=28_500)
    parser.add_argument(
        "--silent-episode", default=DEFAULT_SILENT_EPISODE
    )
    parser.add_argument(
        "--audible-episode", default=DEFAULT_AUDIBLE_EPISODE
    )
    args = parser.parse_args()
    capture.require_conda()
    manifest_root = Path(args.manifest_root).resolve()
    output_root = Path(args.output_root).resolve()
    if output_root.exists():
        raise capture.CaptureFailure(
            "audio_h200_validation_output_exists", str(output_root)
        )
    output_root.mkdir(parents=True)
    capture.TMP_ROOT = Path(args.tmp_root).resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)

    requested = {args.silent_episode, args.audible_episode}
    rows = find_rows(manifest_root, requested)
    ordered = [
        ("silent", rows[args.silent_episode]),
        ("audible", rows[args.audible_episode]),
    ]
    world_groups = {
        (str(row["map"]), str(row["gametype"]).lower())
        for _, row in ordered
    }
    if len(world_groups) != 1:
        raise capture.CaptureFailure(
            "audio_h200_validation_world_group_mismatch",
            capture.canonical_json(sorted(world_groups)),
        )
    world_group = next(iter(world_groups))
    build = capture.build_root()
    lane = worker.ResidentLaneController(
        lane_index=0,
        group_index=1,
        world_group=world_group,
        port=args.port,
        build=build,
        warmup_root=output_root / "resident_warmups",
    )
    cases = []
    try:
        for case_index, (label, row) in enumerate(ordered, 1):
            scenario = worker.prepare_route(
                row, output_root, args.port
            )
            stage = (
                capture.TMP_ROOT
                / "audio_fix_validation"
                / f"{row['episode_id']}_audiofix_a{case_index:02d}"
            )
            result = lane.execute(
                stage, scenario, retry=100 + case_index
            )
            result = worker.complete_formal_artifacts(result, row)
            destination = preserve_case(
                output_root, str(row["episode_id"]), result
            )
            case = case_report(row, scenario, result, destination)
            case["label"] = label
            cases.append(case)
    finally:
        lane.close()

    silent = next(row for row in cases if row["label"] == "silent")
    audible = next(row for row in cases if row["label"] == "audible")
    warmup_results = []
    for path in sorted(
        (output_root / "resident_warmups").glob("**/RESULT.json")
    ):
        warmup_results.append(
            json.loads(path.read_text(encoding="utf-8"))
        )
    checks = {
        "silent_manifest_was_true": (
            silent["manifest_declared_expects_sound"] is True
        ),
        "silent_runtime_corrected_false": (
            silent["runtime_expects_sound"] is False
        ),
        "silent_all_hard_gates": not silent["failed_hard_gates"],
        "audible_runtime_true": (
            audible["runtime_expects_sound"] is True
        ),
        "audible_real_waveform": audible["audio_peak_s16"] > 0,
        "audible_all_hard_gates": not audible["failed_hard_gates"],
        "frames_320": all(row["frames"] == 320 for row in cases),
        "audio_240000": all(
            row["audio_samples_per_channel"] == 240_000
            for row in cases
        ),
        "mapping_exact": all(
            row["mapping_rate"] == 1.0 for row in cases
        ),
        "hardware_renderer": all(
            capture.is_nvidia_hardware_renderer(row["renderer"])
            for row in cases
        ),
        "gametype_exact": all(
            row["realized_gametype"] == row["gametype"]
            for row in cases
        ),
        "resident_warmup_passed": (
            len(warmup_results) == 1
            and warmup_results[0].get("passed") is True
        ),
        "resident_process_reused": all(
            row["resident_lane"]["process_reused"] is True
            for row in cases
        ),
        "training_admitted_false": all(
            rows[row["episode_id"]]["training_admitted"] is False
            for row in cases
        ),
    }
    report = {
        "schema_version": (
            "xonotic-stage1-audio-expectation-h200-validation-v1"
        ),
        "created_utc": capture.utc_now(),
        "manifest_root": str(manifest_root),
        "output_root": str(output_root),
        "tmp_root": str(capture.TMP_ROOT),
        "world_group": list(world_group),
        "cases": cases,
        "resident_warmups": warmup_results,
        "checks": checks,
        "passed": all(checks.values()),
        "training_admitted": False,
    }
    report_path = output_root / "VALIDATION_REPORT.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
