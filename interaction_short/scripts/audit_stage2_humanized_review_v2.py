                      
"""Audit the realized Stage-2 burst/miss review v2."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = capture.ROOT
DEFAULT_MANIFEST = (
    ROOT / "manifests/stage2_humanized_review_v2/input.jsonl"
)
DEFAULT_OUTPUT = ROOT / "stage2_humanized_review_v2_output"


def journal_rows(
    output_root: Path, filename: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            f"shard-*-of-*/{filename}"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def audit(
    input_manifest: Path, output_root: Path
) -> dict[str, Any]:
    planned = capture.load_jsonl(input_manifest)
    planned_by_id = {row["episode_id"]: row for row in planned}
    accepted = journal_rows(output_root, "accepted.jsonl")
    accepted_by_id = {row["episode_id"]: row for row in accepted}
    terminal = [
        row
        for row in journal_rows(output_root, "rejects.jsonl")
        if row.get("terminal") is True
    ]
    terminal_by_id = {row["episode_id"]: row for row in terminal}
    accepted_results: list[dict[str, Any]] = []
    actual_fire_counts: Counter[int] = Counter()
    actual_multi_by_weapon: Counter[str] = Counter()
    accepted_fire_categories: Counter[str] = Counter()
    planned_pass_sectors: Counter[str] = Counter()
    planned_pass_magnitudes: Counter[str] = Counter()
    planned_pass_trajectories: Counter[str] = Counter()
    realized_first_sectors: Counter[str] = Counter()
    realized_first_magnitudes: Counter[str] = Counter()
    weapon_program_counts: dict[str, Counter[str]] = defaultdict(
        Counter
    )

    for episode_id, published in sorted(accepted_by_id.items()):
        row = planned_by_id[episode_id]
        episode_path = Path(published["episode_path"])
        qa = json.loads(
            (episode_path / "qa.json").read_text(encoding="utf-8")
        )
        causal = json.loads(
            (episode_path / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        episode = json.loads(
            (episode_path / "episode.json").read_text(
                encoding="utf-8"
            )
        )
        fire = causal["fire_program"]
        program = fire.get("program") or {}
        fire_count = int(
            fire.get("authoritative_fire_event_count", 0)
        )
        category = str(
            (
                episode.get("humanized_review_design") or {}
            ).get("firing_program_category", "none")
        )
        weapon = str(row["weapon"])
        actual_fire_counts[fire_count] += 1
        weapon_program_counts[weapon][
            str(program.get("name", "legacy"))
        ] += 1
        if category != "none":
            accepted_fire_categories[category] += 1
        if fire_count >= 2:
            actual_multi_by_weapon[weapon] += 1

        if row["causal_design"]["aim_policy"] == "pass_offset":
            schedule = row["causal_design"]["aim_schedule"]
            planned_pass_sectors[
                str(schedule["miss_direction_sector"])
            ] += 1
            planned_pass_magnitudes[
                str(schedule["miss_magnitude_bin"])
            ] += 1
            planned_pass_trajectories[
                str(schedule["miss_trajectory_style"])
            ] += 1
            vectors = causal.get(
                "realized_miss_vectors_at_fire", []
            )
            if vectors:
                realized_first_sectors[
                    str(vectors[0]["direction_sector"])
                ] += 1
                realized_first_magnitudes[
                    str(vectors[0]["magnitude_bin"])
                ] += 1

        checks = {
            "frames_320": int(qa["video"]["frames"])
            == capture.OUTPUT_TICKS,
            "audio_240000": int(
                qa["audio"]["samples_per_channel"]
            )
            == capture.AUDIO_SAMPLES,
            "frame_tick_mapping": float(
                qa["mapping"]["success_rate"]
            )
            >= 0.999,
            "model_actions_320": len(
                pd.read_parquet(
                    episode_path / "model_actions.parquet"
                )
            )
            == capture.OUTPUT_TICKS,
            "nvidia_hardware_renderer": (
                capture.is_nvidia_hardware_renderer(
                    qa["runtime"]["renderer"]
                )
            ),
            "hud_contract": (
                qa["hud"]["cl_hidewaypoints"] == 2
                and qa["hud"]["hud_panel_modicons"] == 0
                and qa["hud"]["g_ctf_flag_waypoint"] == 0
            ),
            "gametype_contract": (
                qa["mode"]["requested_gametype"]
                == qa["mode"]["realized_gametype"]
            ),
            "all_hard_gates": all(qa["hard_gates"].values()),
            "causal_passed": causal["passed"] is True,
            "fire_program_passed": fire["passed"] is True,
            "training_forbidden": (
                qa.get("training_admitted") is False
                and episode.get("training_admitted") is False
            ),
        }
        accepted_results.append(
            {
                "episode_id": episode_id,
                "weapon": weapon,
                "aim_policy": row["causal_design"]["aim_policy"],
                "fire_program_category": category,
                "fire_program_name": program.get("name"),
                "authoritative_fire_event_count": fire_count,
                "realized_miss_vectors_at_fire": causal.get(
                    "realized_miss_vectors_at_fire", []
                ),
                "actual_outcome": causal["actual_outcome"],
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    accounted_ids = set(accepted_by_id) | set(terminal_by_id)
    accepted_weapons = {
        planned_by_id[episode_id]["weapon"]
        for episode_id in accepted_by_id
    }
    review_ready_checks = {
        "all_rows_accounted": accounted_ids == set(planned_by_id),
        "accepted_unique": len(accepted) == len(accepted_by_id),
        "terminal_unique": len(terminal) == len(terminal_by_id),
        "all_accepted_artifacts_pass": all(
            row["passed"] for row in accepted_results
        ),
        "at_least_45_accepted": len(accepted_by_id) >= 45,
        "all_nine_weapons_accepted": accepted_weapons
        == set(row["weapon"] for row in planned),
        "all_nine_weapons_have_realized_multi_fire": set(
            actual_multi_by_weapon
        )
        == set(row["weapon"] for row in planned),
        "nontraining_only": all(
            row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
            for row in planned
        ),
    }
    result = {
        "schema_version": "xonotic-stage2-humanized-review-audit-v2",
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": capture.sha256_file(input_manifest),
        "output_root": str(output_root),
        "planned_rows": len(planned),
        "accepted_rows": len(accepted_by_id),
        "terminal_reject_rows": len(terminal_by_id),
        "unaccounted_rows": sorted(
            set(planned_by_id) - accounted_ids
        ),
        "cohort_all_accepted": len(accepted_by_id) == len(planned),
        "review_ready_checks": review_ready_checks,
        "review_ready": all(review_ready_checks.values()),
        "production_authorized": False,
        "distributions": {
            "accepted_weapon": dict(
                Counter(
                    planned_by_id[episode_id]["weapon"]
                    for episode_id in accepted_by_id
                )
            ),
            "accepted_fire_category": dict(
                accepted_fire_categories
            ),
            "authoritative_fire_event_count": {
                str(key): value
                for key, value in sorted(actual_fire_counts.items())
            },
            "realized_multi_fire_by_weapon": dict(
                actual_multi_by_weapon
            ),
            "weapon_fire_program": {
                weapon: dict(counts)
                for weapon, counts in sorted(
                    weapon_program_counts.items()
                )
            },
            "accepted_planned_pass_sector": dict(
                planned_pass_sectors
            ),
            "accepted_planned_pass_magnitude": dict(
                planned_pass_magnitudes
            ),
            "accepted_planned_pass_trajectory": dict(
                planned_pass_trajectories
            ),
            "realized_first_fire_miss_sector": dict(
                realized_first_sectors
            ),
            "realized_first_fire_miss_magnitude": dict(
                realized_first_magnitudes
            ),
        },
        "terminal_rejects": [
            {
                "episode_id": row["episode_id"],
                "reason": row["reason"],
                "detail": row["detail"],
                "diagnostic_path": row.get("diagnostic_path"),
            }
            for row in sorted(
                terminal_by_id.values(),
                key=lambda item: item["episode_id"],
            )
        ],
        "accepted_results": accepted_results,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-manifest", type=Path, default=DEFAULT_MANIFEST
    )
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    report = (
        args.report.resolve()
        if args.report
        else output_root / "review/AUDIT.json"
    )
    result = audit(args.input_manifest.resolve(), output_root)
    atomic_json(report, result)
    print(
        json.dumps(
            {
                "report": str(report),
                "planned": result["planned_rows"],
                "accepted": result["accepted_rows"],
                "terminal": result["terminal_reject_rows"],
                "unaccounted": len(result["unaccounted_rows"]),
                "review_ready": result["review_ready"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
