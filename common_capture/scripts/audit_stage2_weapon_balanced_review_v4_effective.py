                      
"""Audit the effective 108-slot Stage-2 weapon-balanced V4 review.

The base manifest remains immutable.  A base slot is represented by its base
episode when that episode passed QA, otherwise by the one pre-declared
operational replacement for the terminal QA failure.  Realized target outcome
is never used to choose between artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_stage2_weapon_balanced_review_v3 as base              
import audit_stage2_weapon_balanced_review_v4 as v4              
import prepare_stage2_weapon_balanced_review_v4 as design              
import xonotic_capture as capture              


BASE_MANIFEST_ROOT = (
    ROOT / "manifests/stage2_weapon_balanced_review_v4"
)
BASE_MANIFEST = BASE_MANIFEST_ROOT / "input.jsonl"
BASE_METADATA = BASE_MANIFEST_ROOT / "MANIFEST_METADATA.json"
BASE_OUTPUT = ROOT / "stage2_weapon_balanced_review_v4_output"
REP_MANIFEST_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v1"
)
REP_MANIFEST = REP_MANIFEST_ROOT / "input.jsonl"
REP_OUTPUT = (
    ROOT / "stage2_weapon_balanced_review_v4_replenishment_v1_output"
)
REP2_MANIFEST_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v2"
)
REP2_MANIFEST = REP2_MANIFEST_ROOT / "input.jsonl"
REP2_OUTPUT = (
    ROOT / "stage2_weapon_balanced_review_v4_replenishment_v2_output"
)
REP3_MANIFEST_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v3"
)
REP3_MANIFEST = REP3_MANIFEST_ROOT / "input.jsonl"
REP3_OUTPUT = (
    ROOT / "stage2_weapon_balanced_review_v4_replenishment_v3_output"
)
AUDIT_PATH = BASE_OUTPUT / "WEAPON_BALANCED_EFFECTIVE_AUDIT.json"
EPISODE_CSV = BASE_OUTPUT / "WEAPON_ARM_EFFECTIVE_OUTCOMES.csv"
WEAPON_CSV = BASE_OUTPUT / "WEAPON_EFFECTIVE_SUMMARY.csv"
EXPECTED_LOGICAL_SLOTS = 108


def journal_rows(
    output_root: Path, journal_name: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            f"shard-*-of-*/{journal_name}.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def aim_direction_sector(angle: float) -> str:
    normalized = ((float(angle) + 180.0) % 360.0) - 180.0
    if abs(normalized) >= 135.0:
        return "left"
    if abs(normalized) <= 45.0:
        return "right"
    return "vertical"


def audit_replacements(
    manifest: Path,
    output_root: Path,
    *,
    audit_stem: str,
) -> dict[str, Any] | None:
    if not manifest.is_file():
        return None
    rows = capture.load_jsonl(manifest)
    if not rows:
        return None
    base.MANIFEST = manifest
                                                                             
                                                                              
                                            
    base.METADATA = BASE_METADATA
    base.OUTPUT_ROOT = output_root
    base.AUDIT_PATH = output_root / f"{audit_stem}_AUDIT.json"
    base.EPISODE_CSV = output_root / f"{audit_stem}_OUTCOMES.csv"
    base.WEAPON_CSV = output_root / f"{audit_stem}_SUMMARY.csv"
    base.EXPECTED_ROWS = len(rows)
    base.REQUIRE_TARGET_SHOT_COLUMNS = True
    return base.audit(False)


def summarize(
    effective_rows: list[dict[str, Any]],
    bands: dict[str, dict[str, float]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    weapons: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "episodes": 0,
            "firing_episodes": 0,
            "fire_events": 0,
            "target_hit_fire_events": 0,
            "direct_hit_fire_events": 0,
            "splash_hit_fire_events": 0,
            "pellet_hit_fire_events": 0,
            "target_damage_events": 0,
            "target_damage_amount": 0.0,
            "arms": {},
        }
    )
    arms: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "episodes": 0,
            "fire_events": 0,
            "target_hit_fire_events": 0,
        }
    )
    for row in effective_rows:
        weapon = str(row["weapon"])
        arm = str(row["arm"])
        no_fire = arm == "visible_no_fire"
        aggregate = weapons[weapon]
        aggregate["episodes"] += 1
        aggregate["firing_episodes"] += int(not no_fire)
        for key in (
            "fire_events",
            "target_hit_fire_events",
            "direct_hit_fire_events",
            "splash_hit_fire_events",
            "pellet_hit_fire_events",
            "target_damage_events",
        ):
            aggregate[key] += int(row[key])
        aggregate["target_damage_amount"] += float(
            row["target_damage_amount"]
        )
        arm_aggregate = aggregate["arms"].setdefault(
            arm,
            {
                "episodes": 0,
                "fire_events": 0,
                "target_hit_fire_events": 0,
            },
        )
        arm_aggregate["episodes"] += 1
        arm_aggregate["fire_events"] += int(row["fire_events"])
        arm_aggregate["target_hit_fire_events"] += int(
            row["target_hit_fire_events"]
        )
        arms[arm]["episodes"] += 1
        arms[arm]["fire_events"] += int(row["fire_events"])
        arms[arm]["target_hit_fire_events"] += int(
            row["target_hit_fire_events"]
        )

    weapon_summary: dict[str, dict[str, Any]] = {}
    for weapon, aggregate in sorted(weapons.items()):
        for values in aggregate["arms"].values():
            fires = int(values["fire_events"])
            values["target_hit_rate"] = (
                int(values["target_hit_fire_events"]) / fires
                if fires
                else None
            )
        fires = int(aggregate["fire_events"])
        hits = int(aggregate["target_hit_fire_events"])
        rate = hits / fires if fires else math.nan
        lower = float(bands[weapon]["minimum"])
        upper = float(bands[weapon]["maximum"])
        weapon_summary[weapon] = {
            **aggregate,
            "target_hit_rate": rate,
            "target_band_minimum": lower,
            "target_band_maximum": upper,
            "strict_band_passed": lower <= rate <= upper,
            "approximate_band_passed": (
                lower - 0.05 <= rate <= upper + 0.05
            ),
        }

    arm_summary = {
        arm: values
        | {
            "target_hit_rate": (
                values["target_hit_fire_events"]
                / values["fire_events"]
                if values["fire_events"]
                else None
            )
        }
        for arm, values in sorted(arms.items())
    }
    total_fires = sum(
        int(row["fire_events"]) for row in effective_rows
    )
    total_hits = sum(
        int(row["target_hit_fire_events"]) for row in effective_rows
    )
    overall = {
        "fire_events": total_fires,
        "target_hit_fire_events": total_hits,
        "target_miss_fire_events": total_fires - total_hits,
        "target_hit_rate": (
            total_hits / total_fires if total_fires else None
        ),
    }
    return weapon_summary, arm_summary, overall


def audit(require_complete: bool) -> dict[str, Any]:
    base_rows = capture.load_jsonl(BASE_MANIFEST)
    base_by_id = {
        str(row["episode_id"]): row for row in base_rows
    }
    base_result = v4.audit(False)
    base_results = {
        str(row["episode_id"]): row
        for row in base_result["episode_results"]
    }
    terminal_base = {
        str(row["episode_id"]): row
        for row in journal_rows(BASE_OUTPUT, "rejects")
        if row.get("terminal") is True
    }

    generation_specs = (
        (
            "operational_replenishment_v1",
            REP_MANIFEST,
            REP_OUTPUT,
        ),
        (
            "operational_replenishment_v2",
            REP2_MANIFEST,
            REP2_OUTPUT,
        ),
        (
            "operational_replenishment_v3",
            REP3_MANIFEST,
            REP3_OUTPUT,
        ),
    )
    manifests_by_generation: dict[
        str, list[dict[str, Any]]
    ] = {}
    replacements_by_generation: dict[
        str, dict[str, dict[str, Any]]
    ] = {}
    results_by_generation: dict[
        str, dict[str, dict[str, Any]]
    ] = {}
    terminal_ids_by_generation: dict[str, set[str]] = {}
    duplicate_replacement_slots: list[str] = []
    for generation, manifest, output_root in generation_specs:
        manifest_rows = (
            capture.load_jsonl(manifest)
            if manifest.is_file()
            else []
        )
        manifests_by_generation[generation] = manifest_rows
        by_base: dict[str, dict[str, Any]] = {}
        for row in manifest_rows:
            base_id = str(
                row["weapon_balanced_review_design"][
                    "replacement_for_episode_id"
                ]
            )
            if base_id in by_base:
                duplicate_replacement_slots.append(
                    f"{generation}:{base_id}"
                )
            by_base[base_id] = row
        replacements_by_generation[generation] = by_base
        replacement_result = audit_replacements(
            manifest,
            output_root,
            audit_stem=generation.upper(),
        )
        results_by_generation[generation] = (
            {
                str(row["episode_id"]): row
                for row in replacement_result["episode_results"]
            }
            if replacement_result is not None
            else {}
        )
        terminal_ids_by_generation[generation] = {
            str(row["episode_id"])
            for row in journal_rows(output_root, "rejects")
            if row.get("terminal") is True
        }

    rep1_by_base = replacements_by_generation[
        "operational_replenishment_v1"
    ]
    rep2_by_base = replacements_by_generation[
        "operational_replenishment_v2"
    ]
    rep3_by_base = replacements_by_generation[
        "operational_replenishment_v3"
    ]
    rep1_id_to_base = {
        str(row["episode_id"]): logical_id
        for logical_id, row in rep1_by_base.items()
    }
    terminal_rep1_logical = {
        rep1_id_to_base[episode_id]
        for episode_id in terminal_ids_by_generation[
            "operational_replenishment_v1"
        ]
        if episode_id in rep1_id_to_base
    }
    terminal_rep2_ids = terminal_ids_by_generation[
        "operational_replenishment_v2"
    ]
    rep2_id_to_base = {
        str(row["episode_id"]): logical_id
        for logical_id, row in rep2_by_base.items()
    }
    terminal_rep2_logical = {
        rep2_id_to_base[episode_id]
        for episode_id in terminal_rep2_ids
        if episode_id in rep2_id_to_base
    }
    terminal_rep3_ids = terminal_ids_by_generation[
        "operational_replenishment_v3"
    ]

    effective_rows: list[dict[str, Any]] = []
    unresolved_slots: list[str] = []
    invalid_lineage_slots: list[str] = []
    replacement_for_accepted_slots: list[str] = []
    for logical_id, planned in sorted(base_by_id.items()):
        if logical_id in base_results:
            if any(
                logical_id in replacements
                for replacements in replacements_by_generation.values()
            ):
                replacement_for_accepted_slots.append(logical_id)
            artifact = dict(base_results[logical_id])
            artifact.update(
                {
                    "logical_slot_episode_id": logical_id,
                    "artifact_episode_id": logical_id,
                    "artifact_source": "base",
                }
            )
            effective_rows.append(artifact)
            continue
        selected: tuple[
            str, dict[str, Any], dict[str, Any]
        ] | None = None
        for generation, _, _ in generation_specs:
            replacement = replacements_by_generation[
                generation
            ].get(logical_id)
            if replacement is None:
                continue
            replacement_id = str(replacement["episode_id"])
            planned_aim = planned["causal_design"][
                "weapon_balanced_aim_program"
            ]
            replacement_aim = replacement["causal_design"][
                "weapon_balanced_aim_program"
            ]
            if generation == "operational_replenishment_v1":
                direction_ok = (
                    replacement_aim["offset_direction_deg"]
                    == planned_aim["offset_direction_deg"]
                )
            elif generation == "operational_replenishment_v2":
                direction_ok = (
                    aim_direction_sector(
                    replacement_aim["offset_direction_deg"]
                    )
                    == aim_direction_sector(
                        planned_aim["offset_direction_deg"]
                    )
                    and replacement[
                        "weapon_balanced_review_design"
                    ].get("aim_direction_sector_preserved")
                    is True
                )
            else:
                direction_ok = (
                    replacement[
                        "weapon_balanced_review_design"
                    ].get("aim_arm_preserved")
                    is True
                    and replacement[
                        "weapon_balanced_review_design"
                    ].get(
                        "aim_direction_changed_for_technical_qa"
                    )
                    is True
                    and replacement[
                        "weapon_balanced_review_design"
                    ].get("direction_change_outcome_conditioned")
                    is False
                )
            if (
                logical_id not in terminal_base
                or replacement["weapon"] != planned["weapon"]
                or replacement["causal_design"]["aim_policy"]
                != planned["causal_design"]["aim_policy"]
                or not direction_ok
                or replacement_aim["target_offset_scale"]
                != planned_aim["target_offset_scale"]
                or replacement["exogenous_contract_sha256"]
                != planned["exogenous_contract_sha256"]
                or replacement["weapon_balanced_review_design"][
                    "outcome_used_for_individual_admission"
                ]
                is not False
            ):
                invalid_lineage_slots.append(
                    f"{generation}:{logical_id}"
                )
            artifact_result = results_by_generation[
                generation
            ].get(replacement_id)
            if artifact_result is not None:
                selected = (
                    generation,
                    replacement,
                    artifact_result,
                )
                break
        if selected is None:
            unresolved_slots.append(logical_id)
            continue
        generation, replacement, artifact_result = selected
        artifact = dict(artifact_result)
        artifact.update(
            {
                "logical_slot_episode_id": logical_id,
                "artifact_episode_id": replacement["episode_id"],
                "artifact_source": generation,
            }
        )
        effective_rows.append(artifact)

    metadata = json.loads(
        BASE_METADATA.read_text(encoding="utf-8")
    )
    bands = metadata["selection_contract"][
        "target_hit_rate_bands"
    ]
    weapon_summary, arm_summary, overall = summarize(
        effective_rows, bands
    )
    expected_recipe = {
        weapon: Counter(
            (
                *design.FIRING_RECIPE_BY_WEAPON[weapon],
                "visible_no_fire",
                "visible_no_fire",
            )
        )
        for weapon in design.WEAPONS
    }
    actual_recipe = {
        weapon: Counter(
            row["arm"]
            for row in effective_rows
            if row["weapon"] == weapon
        )
        for weapon in design.WEAPONS
    }
    approximate_band_failures = sorted(
        weapon
        for weapon, values in weapon_summary.items()
        if not values["approximate_band_passed"]
    )
    checks = {
        "base_manifest_108_slots": (
            len(base_rows) == EXPECTED_LOGICAL_SLOTS
        ),
        "all_logical_slots_resolved_exactly_once": (
            len(effective_rows) == EXPECTED_LOGICAL_SLOTS
            and len(
                {
                    row["logical_slot_episode_id"]
                    for row in effective_rows
                }
            )
            == EXPECTED_LOGICAL_SLOTS
            and not unresolved_slots
        ),
        "replacement_only_for_terminal_base_qa_failure": (
            not invalid_lineage_slots
            and not replacement_for_accepted_slots
            and not duplicate_replacement_slots
            and set(rep1_by_base) == set(terminal_base)
            and set(rep2_by_base) == terminal_rep1_logical
            and set(rep3_by_base) == terminal_rep2_logical
        ),
        "no_unresolved_final_replacement_rejects": (
            not terminal_rep3_ids
            and not (
                terminal_rep2_logical - set(rep3_by_base)
            )
        ),
        "all_effective_artifact_qa": bool(effective_rows)
        and all(row["passed"] for row in effective_rows),
        "all_target_shot_labels_exact": bool(effective_rows)
        and all(
            all(row["target_shot_checks"].values())
            for row in effective_rows
        ),
        "weapon_arm_recipe_exact": actual_recipe == expected_recipe,
        "all_nine_weapons_present": (
            set(weapon_summary) == set(design.WEAPONS)
        ),
        "all_weapon_rates_in_approximate_band": (
            len(effective_rows) == EXPECTED_LOGICAL_SLOTS
            and not approximate_band_failures
        ),
        "no_outcome_based_individual_admission": all(
            row["acceptance"]["actual_outcome"] is None
            and row["weapon_balanced_review_design"][
                "outcome_used_for_individual_admission"
            ]
            is False
            for row in (
                base_rows
                + manifests_by_generation[
                    "operational_replenishment_v1"
                ]
                + manifests_by_generation[
                    "operational_replenishment_v2"
                ]
                + manifests_by_generation[
                    "operational_replenishment_v3"
                ]
            )
        ),
    }
    passed = all(checks.values())
    result = {
        "schema_version": (
            "xonotic-stage2-weapon-balanced-v4-effective-"
            "artifact-audit-v1"
        ),
        "base_manifest": str(BASE_MANIFEST),
        "base_manifest_sha256": capture.sha256_file(BASE_MANIFEST),
        "base_metadata": str(BASE_METADATA),
        "base_metadata_sha256": capture.sha256_file(BASE_METADATA),
        "replenishment_manifest": (
            str(REP_MANIFEST) if REP_MANIFEST.is_file() else None
        ),
        "replenishment_manifest_sha256": (
            capture.sha256_file(REP_MANIFEST)
            if REP_MANIFEST.is_file()
            else None
        ),
        "replenishment_v2_manifest": (
            str(REP2_MANIFEST)
            if REP2_MANIFEST.is_file()
            else None
        ),
        "replenishment_v2_manifest_sha256": (
            capture.sha256_file(REP2_MANIFEST)
            if REP2_MANIFEST.is_file()
            else None
        ),
        "replenishment_v3_manifest": (
            str(REP3_MANIFEST)
            if REP3_MANIFEST.is_file()
            else None
        ),
        "replenishment_v3_manifest_sha256": (
            capture.sha256_file(REP3_MANIFEST)
            if REP3_MANIFEST.is_file()
            else None
        ),
        "planned_logical_slots": len(base_rows),
        "effective_episodes": len(effective_rows),
        "base_artifact_count": sum(
            row["artifact_source"] == "base"
            for row in effective_rows
        ),
        "replacement_artifact_count": sum(
            row["artifact_source"].startswith(
                "operational_replenishment_"
            )
            for row in effective_rows
        ),
        "replacement_artifact_count_by_generation": dict(
            Counter(
                row["artifact_source"]
                for row in effective_rows
                if row["artifact_source"] != "base"
            )
        ),
        "terminal_base_reject_episode_ids": sorted(terminal_base),
        "terminal_replacement_episode_ids_by_generation": {
            generation: sorted(values)
            for generation, values in (
                terminal_ids_by_generation.items()
            )
        },
        "unresolved_logical_slot_episode_ids": unresolved_slots,
        "invalid_lineage_logical_slot_episode_ids": sorted(
            invalid_lineage_slots
        ),
        "replacement_for_accepted_slot_episode_ids": sorted(
            replacement_for_accepted_slots
        ),
        "duplicate_replacement_logical_slot_episode_ids": sorted(
            duplicate_replacement_slots
        ),
        "overall": overall,
        "weapon_summary": weapon_summary,
        "arm_summary": arm_summary,
        "approximate_band_failure_weapons": (
            approximate_band_failures
        ),
        "effective_episode_results": effective_rows,
        "checks": checks,
        "complete": (
            len(effective_rows) == EXPECTED_LOGICAL_SLOTS
            and not unresolved_slots
        ),
        "passed": passed,
    }
    base.atomic_text(
        AUDIT_PATH,
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    episode_csv_rows = [
        {
            key: (
                json.dumps(value, separators=(",", ":"))
                if isinstance(value, (list, dict))
                else value
            )
            for key, value in row.items()
            if key != "checks"
        }
        for row in effective_rows
    ]
    base.atomic_text(
        EPISODE_CSV, base.csv_text(episode_csv_rows)
    )
    weapon_csv_rows = [
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
    base.atomic_text(
        WEAPON_CSV, base.csv_text(weapon_csv_rows)
    )
    if require_complete and not passed:
        raise capture.CaptureFailure(
            "stage2_weapon_balanced_v4_effective_audit_failed",
            capture.canonical_json(
                {
                    "checks": checks,
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
                "audit": str(AUDIT_PATH),
                "logical_slots": result["planned_logical_slots"],
                "effective": result["effective_episodes"],
                "base": result["base_artifact_count"],
                "replacements": result["replacement_artifact_count"],
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
