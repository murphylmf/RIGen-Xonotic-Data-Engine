                      
"""Audit the immutable Vortex whole-stratum calibration review V5."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_stage2_weapon_balanced_review_v3 as base              
import prepare_stage2_vortex_calibration_review_v5 as design              
import xonotic_capture as capture              


MANIFEST_ROOT = (
    ROOT / "manifests/stage2_vortex_calibration_review_v5"
)
MANIFEST = MANIFEST_ROOT / "input.jsonl"
BASE_METADATA = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4"
    / "MANIFEST_METADATA.json"
)
OUTPUT_ROOT = ROOT / "stage2_vortex_calibration_review_v5_output"
AUDIT_PATH = OUTPUT_ROOT / "VORTEX_CALIBRATION_AUDIT.json"


def audit(require_complete: bool) -> dict:
    base.MANIFEST = MANIFEST
    base.METADATA = BASE_METADATA
    base.OUTPUT_ROOT = OUTPUT_ROOT
    base.AUDIT_PATH = (
        OUTPUT_ROOT / "WEAPON_BALANCED_AUDIT.json"
    )
    base.EPISODE_CSV = (
        OUTPUT_ROOT / "WEAPON_ARM_OUTCOMES.csv"
    )
    base.WEAPON_CSV = OUTPUT_ROOT / "WEAPON_SUMMARY.csv"
    base.EXPECTED_ROWS = 12
    base.REQUIRE_TARGET_SHOT_COLUMNS = True
    result = base.audit(False)

    planned = capture.load_jsonl(MANIFEST)
    metadata = json.loads(
        (MANIFEST_ROOT / "MANIFEST_METADATA.json").read_text(
            encoding="utf-8"
        )
    )
    vortex = result["weapon_summary"].get("Vortex") or {}
    checks = {
        "manifest_has_twelve_vortex_slots": (
            len(planned) == 12
            and {row["weapon"] for row in planned}
            == {"Vortex"}
        ),
        "recipe_exact": Counter(
            row["causal_design"]["aim_policy"]
            for row in planned
        )
        == Counter(design.ALL_ARMS),
        "all_slots_accepted_exactly_once": result["complete"],
        "no_terminal_rejects": (
            result["terminal_rejects"] == 0
        ),
        "all_episode_qa": bool(result["episode_results"])
        and all(row["passed"] for row in result["episode_results"]),
        "all_target_shot_labels_exact": bool(
            result["episode_results"]
        )
        and all(
            all(row["target_shot_checks"].values())
            for row in result["episode_results"]
        ),
        "vortex_rate_in_approximate_band": bool(
            vortex.get("approximate_band_passed")
        ),
        "source_is_aggregate_only": (
            metadata["aggregate_calibration_evidence"][
                "individual_episode_results_read"
            ]
            is False
            and metadata["selection_contract"][
                "source_aggregate_only"
            ]
            is True
        ),
        "no_outcome_based_individual_admission": all(
            row["acceptance"]["actual_outcome"] is None
            and row["weapon_balanced_review_design"][
                "individual_source_episode_outcomes_read"
            ]
            is False
            and row["weapon_balanced_review_design"][
                "outcome_used_for_individual_admission"
            ]
            is False
            for row in planned
        ),
    }
    result.update(
        {
            "schema_version": (
                "xonotic-stage2-vortex-calibration-artifact-"
                "audit-v5"
            ),
            "v5_checks": checks,
            "passed": all(checks.values()),
        }
    )
    base.atomic_text(
        AUDIT_PATH,
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    if require_complete and not result["passed"]:
        raise capture.CaptureFailure(
            "stage2_vortex_calibration_v5_audit_failed",
            capture.canonical_json(checks),
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.require_complete)
    vortex = result["weapon_summary"].get("Vortex") or {}
    print(
        capture.canonical_json(
            {
                "audit": str(AUDIT_PATH),
                "accepted": result["accepted_episodes"],
                "planned": result["planned_episodes"],
                "rejects": result["terminal_rejects"],
                "fire_events": vortex.get("fire_events"),
                "target_hit_fire_events": vortex.get(
                    "target_hit_fire_events"
                ),
                "target_hit_rate": vortex.get("target_hit_rate"),
                "complete": result["complete"],
                "passed": result["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
