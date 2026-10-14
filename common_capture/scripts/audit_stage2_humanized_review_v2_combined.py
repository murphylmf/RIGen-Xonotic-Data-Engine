                      
"""Audit base v2 plus its immutable fail-closed replenishment cohort."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_stage2_humanized_review_v2 as base_audit              
import prepare_stage2_humanized_review_v2 as review_v2              
import prepare_stage2_humanized_review_v2_replenishment_v1 as replenishment              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
DEFAULT_BASE_OUTPUT = ROOT / "stage2_humanized_review_v2_output"
DEFAULT_REPLENISHMENT_OUTPUT = (
    ROOT / "stage2_humanized_review_v2_replenishment_v1_output"
)


def combined_audit(
    base_output: Path, replenishment_output: Path
) -> dict[str, Any]:
    base_manifest = capture.load_jsonl(review_v2.OUTPUT_ROOT / "input.jsonl")
    replenishment_manifest = capture.load_jsonl(
        replenishment.OUTPUT_ROOT / "input.jsonl"
    )
    base_by_id = {row["episode_id"]: row for row in base_manifest}
    replacement_by_base = {
        row["humanized_review_design"]["base_episode_id"]: row
        for row in replenishment_manifest
    }

    base_result = base_audit.audit(
        review_v2.OUTPUT_ROOT / "input.jsonl", base_output
    )
    replenishment_result = base_audit.audit(
        replenishment.OUTPUT_ROOT / "input.jsonl",
        replenishment_output,
    )
    base_accepted = {
        row["episode_id"]: row
        for row in base_result["accepted_results"]
    }
    replacement_accepted = {
        row["episode_id"]: row
        for row in replenishment_result["accepted_results"]
    }
    base_terminal_ids = {
        row["episode_id"] for row in base_result["terminal_rejects"]
    }

    effective: list[
        tuple[str, dict[str, Any], dict[str, Any]]
    ] = []
    missing_effective: list[str] = []
    for logical_id, base_row in sorted(base_by_id.items()):
        if logical_id in base_accepted:
            effective.append(
                (logical_id, base_row, base_accepted[logical_id])
            )
            continue
        replacement = replacement_by_base.get(logical_id)
        result = (
            replacement_accepted.get(replacement["episode_id"])
            if replacement is not None
            else None
        )
        if replacement is None or result is None:
            missing_effective.append(logical_id)
            continue
        effective.append((logical_id, replacement, result))

    weapon_multi: Counter[str] = Counter()
    weapon_programs: dict[str, Counter[str]] = defaultdict(Counter)
    weapon_fire_counts: dict[str, list[int]] = defaultdict(list)
    event_count_distribution: Counter[int] = Counter()
    fire_categories: Counter[str] = Counter()
    fire_programs: Counter[str] = Counter()
    policies: Counter[str] = Counter()
    weapons: Counter[str] = Counter()
    planned_pass_sectors: Counter[str] = Counter()
    planned_pass_magnitudes: Counter[str] = Counter()
    planned_pass_trajectories: Counter[str] = Counter()
    realized_pass_sectors: Counter[str] = Counter()
    realized_pass_magnitudes: Counter[str] = Counter()

    for _, planned, result in effective:
        weapon = str(planned["weapon"])
        policy = str(planned["causal_design"]["aim_policy"])
        category = str(
            planned["humanized_review_design"][
                "firing_program_category"
            ]
        )
        program = str(result["fire_program_name"])
        fire_count = int(result["authoritative_fire_event_count"])
        weapons[weapon] += 1
        policies[policy] += 1
        event_count_distribution[fire_count] += 1
        weapon_programs[weapon][program] += 1
        weapon_fire_counts[weapon].append(fire_count)
        if category != "none":
            fire_categories[category] += 1
        fire_programs[program] += 1
        if fire_count >= 2:
            weapon_multi[weapon] += 1
        if policy == "pass_offset":
            schedule = planned["causal_design"]["aim_schedule"]
            planned_pass_sectors[
                str(schedule["miss_direction_sector"])
            ] += 1
            planned_pass_magnitudes[
                str(schedule["miss_magnitude_bin"])
            ] += 1
            planned_pass_trajectories[
                str(schedule["miss_trajectory_style"])
            ] += 1
            vectors = result["realized_miss_vectors_at_fire"]
            if vectors:
                realized_pass_sectors[
                    str(vectors[0]["direction_sector"])
                ] += 1
                realized_pass_magnitudes[
                    str(vectors[0]["magnitude_bin"])
                ] += 1

    replacement_ids = set(replacement_by_base)
    effective_ids = {logical_id for logical_id, _, _ in effective}
    all_results = [
        result for _, _, result in effective
    ]
    checks = {
        "base_all_rows_accounted": not base_result[
            "unaccounted_rows"
        ],
        "base_reject_history_exactly_replenished": (
            base_terminal_ids == replacement_ids
        ),
        "replenishment_all_rows_accounted": not (
            replenishment_result["unaccounted_rows"]
        ),
        "replenishment_all_accepted": (
            replenishment_result["accepted_rows"]
            == replenishment_result["planned_rows"]
            == len(replenishment_manifest)
            and replenishment_result["terminal_reject_rows"] == 0
        ),
        "all_54_logical_slots_accepted": (
            not missing_effective
            and effective_ids == set(base_by_id)
            and len(effective) == 54
        ),
        "all_effective_artifacts_pass": all(
            result["passed"] is True for result in all_results
        ),
        "all_nine_weapons_present": set(weapons)
        == set(review_v2.WEAPONS),
        "all_nine_weapons_have_realized_multi_fire": set(
            weapon_multi
        )
        == set(review_v2.WEAPONS),
        "all_eight_planned_miss_directions_present": set(
            planned_pass_sectors
        )
        == set(causal.MISS_DIRECTION_SECTORS),
        "nontraining_only": all(
            row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
            for row in base_manifest + replenishment_manifest
        ),
        "no_runtime_fallback": all(
            row["humanized_review_design"][
                "runtime_action_fallback"
            ]
            is False
            and row["humanized_review_design"][
                "runtime_geometry_fallback"
            ]
            is False
            for row in base_manifest + replenishment_manifest
        ),
    }
    replacement_results = []
    for base_id, replacement_row in sorted(
        replacement_by_base.items()
    ):
        result = replacement_accepted.get(
            replacement_row["episode_id"]
        )
        replacement_results.append(
            {
                "base_episode_id": base_id,
                "replacement_episode_id": replacement_row[
                    "episode_id"
                ],
                "remediation_reason": replacement_row[
                    "humanized_review_design"
                ]["remediation_reason"],
                "accepted": result is not None,
                "authoritative_fire_event_count": (
                    result["authoritative_fire_event_count"]
                    if result is not None
                    else None
                ),
                "fire_program_name": (
                    result["fire_program_name"]
                    if result is not None
                    else None
                ),
            }
        )

    return {
        "schema_version": (
            "xonotic-stage2-humanized-review-combined-audit-v1"
        ),
        "base": {
            "manifest": str(review_v2.OUTPUT_ROOT / "input.jsonl"),
            "manifest_sha256": capture.sha256_file(
                review_v2.OUTPUT_ROOT / "input.jsonl"
            ),
            "output_root": str(base_output),
            "planned_rows": base_result["planned_rows"],
            "accepted_rows": base_result["accepted_rows"],
            "terminal_reject_rows": base_result[
                "terminal_reject_rows"
            ],
        },
        "replenishment": {
            "manifest": str(
                replenishment.OUTPUT_ROOT / "input.jsonl"
            ),
            "manifest_sha256": capture.sha256_file(
                replenishment.OUTPUT_ROOT / "input.jsonl"
            ),
            "output_root": str(replenishment_output),
            "planned_rows": replenishment_result["planned_rows"],
            "accepted_rows": replenishment_result["accepted_rows"],
            "terminal_reject_rows": replenishment_result[
                "terminal_reject_rows"
            ],
        },
        "effective_rows": len(effective),
        "missing_effective_rows": missing_effective,
        "review_ready_checks": checks,
        "review_ready": all(checks.values()),
        "production_authorized": False,
        "distributions": {
            "weapon": dict(weapons),
            "policy": dict(policies),
            "fire_category": dict(fire_categories),
            "fire_program": dict(fire_programs),
            "authoritative_fire_event_count": {
                str(key): value
                for key, value in sorted(
                    event_count_distribution.items()
                )
            },
            "realized_multi_fire_by_weapon": dict(weapon_multi),
            "weapon_fire_program": {
                weapon: dict(programs)
                for weapon, programs in sorted(
                    weapon_programs.items()
                )
            },
            "weapon_authoritative_fire_counts": {
                weapon: sorted(counts)
                for weapon, counts in sorted(
                    weapon_fire_counts.items()
                )
            },
            "planned_pass_sector": dict(planned_pass_sectors),
            "planned_pass_magnitude": dict(
                planned_pass_magnitudes
            ),
            "planned_pass_trajectory": dict(
                planned_pass_trajectories
            ),
            "realized_first_fire_miss_sector": dict(
                realized_pass_sectors
            ),
            "realized_first_fire_miss_magnitude": dict(
                realized_pass_magnitudes
            ),
        },
        "base_terminal_rejects_retained": base_result[
            "terminal_rejects"
        ],
        "replacement_results": replacement_results,
        "effective_results": [
            {
                "logical_episode_id": logical_id,
                "physical_episode_id": result["episode_id"],
                **{
                    key: value
                    for key, value in result.items()
                    if key != "episode_id"
                },
            }
            for logical_id, _, result in effective
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-output", type=Path, default=DEFAULT_BASE_OUTPUT
    )
    parser.add_argument(
        "--replenishment-output",
        type=Path,
        default=DEFAULT_REPLENISHMENT_OUTPUT,
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    base_output = args.base_output.resolve()
    replenishment_output = args.replenishment_output.resolve()
    report = (
        args.report.resolve()
        if args.report
        else base_output / "review/COMBINED_AUDIT.json"
    )
    result = combined_audit(base_output, replenishment_output)
    base_audit.atomic_json(report, result)
    print(
        json.dumps(
            {
                "report": str(report),
                "effective_rows": result["effective_rows"],
                "missing": len(result["missing_effective_rows"]),
                "review_ready": result["review_ready"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
