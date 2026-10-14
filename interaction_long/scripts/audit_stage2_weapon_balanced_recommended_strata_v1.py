                      
"""Audit the recommended nine-weapon review strata.

Eight complete weapon strata come from V4's effective QA lineage.  Vortex is
replaced as one whole stratum by V5r2 after V4's aggregate Vortex rate failed.
No individual hit/miss outcome is used for artifact selection.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_stage2_vortex_calibration_review_v5r2 as vortex_audit              
import audit_stage2_weapon_balanced_review_v3 as base              
import audit_stage2_weapon_balanced_review_v4_effective as effective              
import prepare_stage2_vortex_calibration_review_v5 as vortex_design              
import prepare_stage2_weapon_balanced_review_v4 as v4_design              
import xonotic_capture as capture              


OUTPUT_ROOT = effective.BASE_OUTPUT
AUDIT_PATH = (
    OUTPUT_ROOT / "WEAPON_BALANCED_RECOMMENDED_STRATA_AUDIT.json"
)
EPISODE_CSV = (
    OUTPUT_ROOT / "WEAPON_ARM_RECOMMENDED_OUTCOMES.csv"
)
WEAPON_CSV = OUTPUT_ROOT / "WEAPON_RECOMMENDED_SUMMARY.csv"
REVIEW_MANIFEST_ROOT = (
    ROOT / "manifests/stage2_weapon_balanced_recommended_review_v1"
)
REVIEW_MANIFEST = REVIEW_MANIFEST_ROOT / "input.jsonl"


def audit(require_complete: bool) -> dict:
    v4_result = effective.audit(False)
    vortex_result = vortex_audit.audit(False)
    v4_rows = [
        dict(row)
        for row in v4_result["effective_episode_results"]
        if row["weapon"] != "Vortex"
    ]
    vortex_rows = []
    for row in vortex_result["episode_results"]:
        artifact = dict(row)
        artifact.update(
            {
                "logical_slot_episode_id": row["episode_id"],
                "artifact_episode_id": row["episode_id"],
                "artifact_source": (
                    "vortex_calibration_v5r2_whole_stratum"
                ),
            }
        )
        vortex_rows.append(artifact)
    recommended = v4_rows + vortex_rows

    metadata = json.loads(
        effective.BASE_METADATA.read_text(encoding="utf-8")
    )
    bands = metadata["selection_contract"][
        "target_hit_rate_bands"
    ]
    weapon_summary, arm_summary, overall = effective.summarize(
        recommended, bands
    )
    expected_recipe = {
        weapon: Counter(
            (
                *v4_design.FIRING_RECIPE_BY_WEAPON[weapon],
                "visible_no_fire",
                "visible_no_fire",
            )
        )
        for weapon in v4_design.WEAPONS
        if weapon != "Vortex"
    }
    expected_recipe["Vortex"] = Counter(
        vortex_design.ALL_ARMS
    )
    actual_recipe = {
        weapon: Counter(
            row["arm"]
            for row in recommended
            if row["weapon"] == weapon
        )
        for weapon in v4_design.WEAPONS
    }
    rate_failures = sorted(
        weapon
        for weapon, values in weapon_summary.items()
        if not values["approximate_band_passed"]
    )
    checks = {
        "v4_effective_108_logical_slots": (
            v4_result["complete"]
            and v4_result["effective_episodes"] == 108
        ),
        "v4_effective_artifacts_all_qa": (
            v4_result["checks"]["all_effective_artifact_qa"]
            and v4_result["checks"][
                "all_target_shot_labels_exact"
            ]
        ),
        "vortex_v5r2_whole_stratum_passed": (
            vortex_result["passed"]
            and vortex_result["complete"]
            and vortex_result["accepted_episodes"] == 12
        ),
        "eight_v4_strata_plus_one_vortex_v5r2": (
            len(v4_rows) == 96
            and len(vortex_rows) == 12
            and len(recommended) == 108
        ),
        "all_artifact_episode_ids_unique": (
            len(
                {
                    row["artifact_episode_id"]
                    for row in recommended
                }
            )
            == 108
        ),
        "all_artifact_qa": all(
            row["passed"] for row in recommended
        ),
        "all_target_shot_labels_exact": all(
            all(row["target_shot_checks"].values())
            for row in recommended
        ),
        "weapon_arm_recipe_exact": (
            actual_recipe == expected_recipe
        ),
        "all_weapon_rates_in_approximate_band": (
            not rate_failures
        ),
        "no_individual_outcome_selection": (
            v4_result["checks"][
                "no_outcome_based_individual_admission"
            ]
            and vortex_result["v5_checks"][
                "no_outcome_based_individual_admission"
            ]
            and vortex_result["v5_checks"][
                "source_is_aggregate_only"
            ]
        ),
        "nontraining_review_only": all(
            json.loads(
                (
                    Path(row["episode_path"]) / "episode.json"
                ).read_text(encoding="utf-8")
            ).get("training_admitted")
            is False
            for row in recommended
        ),
    }
    passed = all(checks.values())
    review_manifest_rows = [
        {
            "episode_id": row["artifact_episode_id"],
            "episode_path": row["episode_path"],
            "weapon": row["weapon"],
            "arm": row["arm"],
            "artifact_source": row["artifact_source"],
            "formal_collection_authorized": False,
            "training_admitted": False,
            "selection_unit": (
                "whole_weapon_stratum_for_vortex_"
                "qa_lineage_for_other_weapons"
            ),
            "individual_outcome_used_for_selection": False,
        }
        for row in sorted(
            recommended,
            key=lambda value: (
                value["weapon"],
                value["artifact_episode_id"],
            ),
        )
    ]
    review_manifest_text = "".join(
        capture.canonical_json(row) + "\n"
        for row in review_manifest_rows
    )
    base.atomic_text(REVIEW_MANIFEST, review_manifest_text)
    result = {
        "schema_version": (
            "xonotic-stage2-weapon-balanced-recommended-"
            "strata-artifact-audit-v1"
        ),
        "selection_policy": (
            "eight_complete_v4_weapon_strata_plus_complete_"
            "vortex_v5r2_whole_stratum"
        ),
        "individual_outcome_used_for_selection": False,
        "recommended_episodes": len(recommended),
        "v4_effective_episode_count": len(v4_rows),
        "vortex_v5r2_episode_count": len(vortex_rows),
        "review_manifest": str(REVIEW_MANIFEST),
        "review_manifest_sha256": hashlib_sha256_text(
            review_manifest_text
        ),
        "overall": overall,
        "weapon_summary": weapon_summary,
        "arm_summary": arm_summary,
        "approximate_band_failure_weapons": rate_failures,
        "recommended_episode_results": recommended,
        "checks": checks,
        "complete": len(recommended) == 108,
        "passed": passed,
    }
    base.atomic_text(
        AUDIT_PATH,
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    episode_rows = [
        {
            key: (
                json.dumps(value, separators=(",", ":"))
                if isinstance(value, (list, dict))
                else value
            )
            for key, value in row.items()
            if key != "checks"
        }
        for row in recommended
    ]
    base.atomic_text(EPISODE_CSV, base.csv_text(episode_rows))
    weapon_rows = [
        {
            key: (
                json.dumps(value, separators=(",", ":"))
                if isinstance(value, dict)
                else value
            )
            for key, value in values.items()
        }
        | {"weapon": weapon}
        for weapon, values in sorted(weapon_summary.items())
    ]
    base.atomic_text(WEAPON_CSV, base.csv_text(weapon_rows))
    if require_complete and not passed:
        raise capture.CaptureFailure(
            "stage2_weapon_balanced_recommended_strata_audit_failed",
            capture.canonical_json(
                {
                    "checks": checks,
                    "rate_failures": rate_failures,
                }
            ),
        )
    return result


def hashlib_sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.require_complete)
    print(
        capture.canonical_json(
            {
                "audit": str(AUDIT_PATH),
                "review_manifest": str(REVIEW_MANIFEST),
                "episodes": result["recommended_episodes"],
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
