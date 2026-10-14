                      
"""Audit the naturally weapon-balanced Stage-2 review v4."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_stage2_weapon_balanced_review_v3 as base              
import prepare_stage2_weapon_balanced_review_v4 as design              
import xonotic_capture as capture              


MANIFEST_ROOT = ROOT / "manifests/stage2_weapon_balanced_review_v4"
OUTPUT_ROOT = ROOT / "stage2_weapon_balanced_review_v4_output"


def configure_base() -> None:
    base.MANIFEST = MANIFEST_ROOT / "input.jsonl"
    base.METADATA = MANIFEST_ROOT / "MANIFEST_METADATA.json"
    base.OUTPUT_ROOT = OUTPUT_ROOT
    base.AUDIT_PATH = OUTPUT_ROOT / "WEAPON_BALANCED_AUDIT.json"
    base.EPISODE_CSV = OUTPUT_ROOT / "WEAPON_ARM_OUTCOMES.csv"
    base.WEAPON_CSV = OUTPUT_ROOT / "WEAPON_SUMMARY.csv"
    base.EXPECTED_ROWS = 108
    base.REQUIRE_TARGET_SHOT_COLUMNS = True


def audit(require_complete: bool) -> dict:
    configure_base()
    result = base.audit(False)
    rows = capture.load_jsonl(base.MANIFEST)
    expected_arm_distribution = {
        weapon: Counter(
            (
                *design.FIRING_RECIPE_BY_WEAPON[weapon],
                "visible_no_fire",
                "visible_no_fire",
            )
        )
        for weapon in design.WEAPONS
    }
    actual_arm_distribution = {
        weapon: Counter(
            row["causal_design"]["aim_policy"]
            for row in rows
            if row["weapon"] == weapon
        )
        for weapon in design.WEAPONS
    }
    approximate_band_failures = sorted(
        weapon
        for weapon, summary in result["weapon_summary"].items()
        if not summary["approximate_band_passed"]
    )
    v4_checks = {
        "pre_capture_recipe_exact": actual_arm_distribution
        == expected_arm_distribution,
        "twelve_slots_per_weapon": all(
            sum(values.values()) == 12
            for values in actual_arm_distribution.values()
        ),
        "all_target_shot_labels_exact": bool(
            result["episode_results"]
        )
        and all(
            all(row["target_shot_checks"].values())
            for row in result["episode_results"]
        ),
        "all_weapon_rates_in_approximate_band": (
            result["complete"] and not approximate_band_failures
        ),
        "outcome_not_used_for_individual_admission": all(
            row["acceptance"]["actual_outcome"] is None
            and row["weapon_balanced_review_design"][
                "outcome_used_for_individual_admission"
            ]
            is False
            for row in rows
        ),
    }
    result["v4_summary_checks"] = v4_checks
    result["approximate_band_failure_weapons"] = (
        approximate_band_failures
    )
    result["passed"] = bool(
        all(result["summary_checks"].values())
        and all(v4_checks.values())
    )
    base.atomic_text(
        base.AUDIT_PATH,
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    if require_complete and not result["passed"]:
        raise capture.CaptureFailure(
            "stage2_weapon_balanced_v4_audit_failed",
            capture.canonical_json(
                {
                    "base": result["summary_checks"],
                    "v4": v4_checks,
                    "rate_failures": approximate_band_failures,
                }
            ),
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.require_complete)
    print(
        capture.canonical_json(
            {
                "audit": str(base.AUDIT_PATH),
                "accepted": result["accepted_episodes"],
                "planned": result["planned_episodes"],
                "rejects": result["terminal_rejects"],
                "overall": result["overall"],
                "rate_failures": result[
                    "approximate_band_failure_weapons"
                ],
                "complete": result["complete"],
                "passed": result["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
