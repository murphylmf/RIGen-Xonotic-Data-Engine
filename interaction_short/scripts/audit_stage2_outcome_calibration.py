                      
"""Audit the bounded Stage-2 telemetry outcome calibration matrix."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_stage2_causal_bundle as bundle              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


EXPECTED_POLICIES = {
    "visible_no_response",
    "pass_offset",
    "delayed_acquisition",
    "sustained_tracking",
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def distribution(
    result: dict[str, Any], planned: list[dict[str, Any]]
) -> dict[str, Any]:
    planned_by_id = {row["episode_id"]: row for row in planned}
    records: list[dict[str, Any]] = []
    cross = Counter()
    for episode in result["episodes"]:
        if not episode.get("episode_path"):
            continue
        row = planned_by_id[episode["episode_id"]]
        package = Path(episode["episode_path"])
        qa = json.loads(
            (package / "qa.json").read_text(encoding="utf-8")
        )
        causal_qa = json.loads(
            (package / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        telemetry_outcome = causal.actual_outcome_bin(qa)
        engine_mechanism_bin = qa["events"]["actual_outcome_bin"]
        checks = {
            "manifest_acceptance_label_absent": (
                row["acceptance"]["actual_outcome"] is None
            ),
            "calibration_not_acceptance_gated": (
                row["outcome_calibration_design"][
                    "actual_outcome_used_for_episode_acceptance"
                ]
                is False
            ),
            "telemetry_outcome_matches_causal_artifact": (
                telemetry_outcome == causal_qa["actual_outcome"]
            ),
            "telemetry_outcome_valid": telemetry_outcome
            in {"no_fire", "miss", "hit_survive", "kill"},
        }
        record = {
            "episode_id": row["episode_id"],
            "counterfactual_group_id": row[
                "counterfactual_group_id"
            ],
            "weapon": row["weapon"],
            "aim_policy": row["causal_design"]["aim_policy"],
            "enemy_health_prior": row["enemy"]["health"],
            "actual_outcome": telemetry_outcome,
            "engine_mechanism_bin": engine_mechanism_bin,
            "actual_distance_bin": causal_qa["actual_distance_bin"],
            "hit_rate_bin": qa["events"]["hit_rate_bin"],
            "fire_count": qa["events"]["fire_count"],
            "damage_count": qa["events"]["damage_count"],
            "death_count": qa["events"]["death_count"],
            "direct_count": qa["events"]["direct_count"],
            "splash_count": qa["events"]["splash_count"],
            "pellet_count": qa["events"]["pellet_count"],
            "checks": checks,
            "passed": all(checks.values()),
        }
        records.append(record)
        cross[
            (
                record["weapon"],
                record["aim_policy"],
                record["actual_outcome"],
            )
        ] += 1
    return {
        "actual_outcomes": dict(
            Counter(row["actual_outcome"] for row in records)
        ),
        "aim_policies": dict(
            Counter(row["aim_policy"] for row in records)
        ),
        "weapons": dict(Counter(row["weapon"] for row in records)),
        "distance_bins": dict(
            Counter(row["actual_distance_bin"] for row in records)
        ),
        "hit_rate_bins": dict(
            Counter(row["hit_rate_bin"] for row in records)
        ),
        "weapon_policy_outcome": [
            {
                "weapon": weapon,
                "aim_policy": policy,
                "actual_outcome": outcome,
                "count": count,
            }
            for (weapon, policy, outcome), count in sorted(
                cross.items()
            )
        ],
        "episodes": records,
        "passed": all(row["passed"] for row in records),
    }


def markdown(result: dict[str, Any]) -> str:
    distribution_result = result["distribution"]
    lines = [
        "# Stage-2 authoritative outcome calibration",
        "",
        f"- Overall: **{'PASS' if result['pass'] else 'FAIL'}**",
        f"- Planned / accepted / terminal reject: "
        f"{result['planned_rows']} / {result['accepted_rows']} / "
        f"{result['terminal_reject_rows']}",
        "- Outcome assignment: authoritative telemetry only; no "
        "candidate outcome is an episode acceptance label.",
        f"- Actual outcomes: "
        f"`{json.dumps(distribution_result['actual_outcomes'], sort_keys=True)}`",
        f"- Distance bins: "
        f"`{json.dumps(distribution_result['distance_bins'], sort_keys=True)}`",
        f"- Hit-rate bins: "
        f"`{json.dumps(distribution_result['hit_rate_bins'], sort_keys=True)}`",
        "",
        "| Weapon | policy | health prior | actual outcome | "
        "fire/damage/death | mechanism D/S/P |",
        "|---|---|---:|---|---:|---:|",
    ]
    for row in distribution_result["episodes"]:
        lines.append(
            f"| {row['weapon']} | {row['aim_policy']} | "
            f"{row['enemy_health_prior']} | {row['actual_outcome']} | "
            f"{row['fire_count']}/{row['damage_count']}/"
            f"{row['death_count']} | {row['direct_count']}/"
            f"{row['splash_count']}/{row['pellet_count']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path)
    args = parser.parse_args()
    input_manifest = args.input_manifest.resolve()
    output_root = args.output_root.resolve()
    report_root = (
        args.report_root.resolve()
        if args.report_root
        else output_root / "review"
    )
    result = bundle.audit(
        input_manifest,
        output_root,
        expected_policies=EXPECTED_POLICIES,
    )
    result["schema_version"] = (
        "xonotic-stage2-outcome-calibration-audit-v1"
    )
    result["distribution"] = distribution(
        result, capture.load_jsonl(input_manifest)
    )
    result["pass"] = (
        result["pass"] and result["distribution"]["passed"]
    )
    bundle.atomic_json(
        report_root / "STAGE2_OUTCOME_CALIBRATION_AUDIT.json",
        result,
    )
    atomic_text(
        report_root / "STAGE2_OUTCOME_CALIBRATION_REPORT.md",
        markdown(result),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
