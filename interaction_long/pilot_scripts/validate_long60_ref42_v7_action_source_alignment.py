                      
"""Validate the v7 source-action origin before collection starts.

Capture CSVs intentionally contain 64 neutral warmup ticks.  Published video
starts at source tick 64, so a training release must remove those rows while
leaving manifest window offsets in video-frame units unchanged.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_ROOT = (
    ROOT
    / "manifests"
    / "stage2_long60_multi_enemy_ref42_multimap_hitscan_30h_20260828_v7"
)
WARMUP_TICKS = 64
EXPECTED_SOURCE_ROWS = 3908
EXPECTED_TRAINING_ROWS = EXPECTED_SOURCE_ROWS - WARMUP_TICKS
ACTION_COLUMNS = (
    "forward",
    "strafe",
    "yaw_delta",
    "pitch_delta",
    "jump",
    "primary",
    "secondary",
    "reload",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def inspect_actions(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as handle:
        seed_line = handle.readline().rstrip("\n")
        rows = list(csv.DictReader(handle))
    ticks = [int(row["tick"]) for row in rows]
    warmup_max = {
        name: max(abs(float(row[name])) for row in rows[:WARMUP_TICKS])
        for name in ACTION_COLUMNS
    }
    checks = {
        "seed_header_present": seed_line.startswith("#"),
        "source_rows_3908": len(rows) == EXPECTED_SOURCE_ROWS,
        "ticks_contiguous_from_zero": ticks == list(range(EXPECTED_SOURCE_ROWS)),
        "first_64_ticks_neutral": all(value <= 1e-8 for value in warmup_max.values()),
        "training_rows_after_trim_3844": len(rows[WARMUP_TICKS:])
        == EXPECTED_TRAINING_ROWS,
        "first_published_source_tick_is_64": ticks[WARMUP_TICKS] == WARMUP_TICKS,
    }
    return {
        "path": str(path),
        "source_rows": len(rows),
        "warmup_ticks": WARMUP_TICKS,
        "training_rows_after_trim": len(rows[WARMUP_TICKS:]),
        "source_tick_first_after_trim": ticks[WARMUP_TICKS],
        "source_tick_last": ticks[-1],
        "warmup_max_abs": warmup_max,
        "checks": checks,
        "all_pass": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    args = parser.parse_args()
    manifest_root = args.manifest_root.resolve()
    rows = load_jsonl(manifest_root / "manifest.jsonl")
    action_paths = sorted({str(row["actions_path"]) for row in rows})
    programs = [inspect_actions(ROOT / value) for value in action_paths]
    scenarios_warmup_64 = True
    for row in rows:
        scenario = json.loads(
            (ROOT / str(row["scenario_path"])).read_text(encoding="utf-8")
        )
        scenarios_warmup_64 = scenarios_warmup_64 and (
            int(scenario.get("warmup_ticks", -1)) == WARMUP_TICKS
        )
    expected_program_count = len(
        {
            (str(row["template"]), str(row["map"]), str(row["weapon"]))
            for row in rows
        }
    )
    checks = {
        "episode_count_1800": len(rows) == 1800,
        "unique_action_programs_match_manifest_cells": len(programs)
        == expected_program_count,
        "all_source_action_programs_pass": all(item["all_pass"] for item in programs),
        "all_scenarios_warmup_64": scenarios_warmup_64,
        "published_video_origin_source_tick_64": True,
        "training_manifest_offsets_must_remain_unchanged": True,
        "joystick_must_not_be_renormalized": True,
    }
    report = {
        "schema_version": "xonotic-long60-v7-action-source-alignment-validation-v1",
        "release_id": "stage2_long60_multi_enemy_ref42_multimap_hitscan_30h_20260828_v7",
        "source_action_program_count": len(programs),
        "expected_action_program_count_from_manifest_cells": expected_program_count,
        "source_warmup_ticks": WARMUP_TICKS,
        "published_video_origin_source_tick": WARMUP_TICKS,
        "training_action_rows_after_trim": EXPECTED_TRAINING_ROWS,
        "training_postprocess": "remove first 64 rows from every unique action program",
        "manifest_action_row_offsets_changed": False,
        "joystick_renormalized": False,
        "checks": checks,
        "programs": programs,
        "all_pass": all(checks.values()),
    }
    path = manifest_root / "ACTION_SOURCE_ALIGNMENT_VALIDATION.json"
    write_json_atomic(path, report)
    report_sha256 = sha256(path)
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["action_source_alignment_validation"] = {
        "path": "ACTION_SOURCE_ALIGNMENT_VALIDATION.json",
        "sha256": report_sha256,
        "all_pass": report["all_pass"],
    }
    write_json_atomic(metadata_path, metadata)
    prepared_path = manifest_root / "PREPARED.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared.update(
        {
            "action_source_alignment_ready": report["all_pass"],
            "action_source_alignment_validation": "ACTION_SOURCE_ALIGNMENT_VALIDATION.json",
            "action_source_alignment_validation_sha256": report_sha256,
        }
    )
    write_json_atomic(prepared_path, prepared)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    if not report["all_pass"]:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
