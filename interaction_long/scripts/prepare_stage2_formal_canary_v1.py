                      
"""Prepare the immutable 81-row Stage-2 formal-shaped canary v1.

The canary is a deterministic nine-row stratum for every core weapon:

* one visible no-fire episode;
* four miss-oriented episodes with two primary fires each;
* three hit-survive-oriented episodes with one primary fire each; and
* one kill-oriented episode with one primary fire and a weapon-specific,
  manifest-frozen target health.

Outcome recipes are assigned before capture.  They are calibration labels, not
episode-admission labels: authoritative target outcomes are always measured
after capture, and an individual episode is never selected or replaced because
it hit, missed, or killed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_weapon_balanced_review_v1 as v3_builder              
import prepare_stage2_weapon_balanced_review_v4 as v4              
import prepare_stage2_stochastic_review_v1 as stochastic_v1              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


OUTPUT_ROOT = ROOT / "manifests/stage2_formal_canary_v1"
SOURCE_AUDIT = (
    ROOT
    / "stage2_weapon_balanced_review_v4_output"
    / "WEAPON_BALANCED_RECOMMENDED_STRATA_AUDIT.json"
)
SOURCE_MANIFESTS = (
    ROOT / "manifests/stage2_weapon_balanced_review_v4/input.jsonl",
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v1"
    / "input.jsonl",
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v2"
    / "input.jsonl",
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v3"
    / "input.jsonl",
    ROOT / "manifests/stage2_vortex_calibration_review_v5r2/input.jsonl",
)
CONTENT_CATALOG = ROOT / "configs/OFFICIAL_V2_CONTENT_CATALOG.json"
DATA_SPEC = ROOT / "XONOTIC_DATA_SPEC_V2.md"
MANIFEST_SCHEMA = "xonotic-stage2-formal-shaped-canary-manifest-v1"
DESIGN_SCHEMA = "xonotic-stage2-formal-shaped-canary-design-v1"
STATIC_CERTIFICATE_SCHEMA = (
    "xonotic-stage2-formal-shaped-canary-static-certificate-v1"
)
SHARD_COUNT = 1
WEAPONS = v4.WEAPONS

                                                                            
                                                                          
                                                        
KILL_HEALTH_BY_WEAPON = {
    "Blaster": 15.0,
    "Shotgun": 36.0,
    "MachineGun": 8.0,
    "Mortar": 40.0,
    "Electro": 30.0,
    "Crylink": 40.0,
    "Vortex": 60.0,
    "Hagar": 18.0,
    "Devastator": 60.0,
}
SURVIVE_HEALTH = 999.0
MISS_ARMS = (
    "edge_graze",
    "near_miss",
    "stochastic_local",
    "stochastic_broad",
)
HIT_SURVIVE_ARMS = (
    "stable_track",
    "overshoot_correct",
    "predictive_track",
)
OUTCOME_RECIPES = (
    ("no_fire", "visible_no_fire"),
    *(("miss", arm) for arm in MISS_ARMS),
    *(("hit_survive", arm) for arm in HIT_SURVIVE_ARMS),
    ("kill", "stable_track"),
)


def source_commit() -> str:
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT / "source/release-src-0.8.6/Xonotic"),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = text.encode("utf-8")
    if path.exists():
        if path.read_bytes() != payload:
            if (
                path.name == "MANIFEST_METADATA.json"
                and json.loads(path.read_text(encoding="utf-8"))
                == json.loads(text)
            ):
                return
            raise capture.CaptureFailure(
                "refuse_overwrite_stage2_formal_canary_v1_drift",
                str(path),
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def source_rows() -> dict[tuple[str, str], dict[str, Any]]:
    audit = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    if audit.get("passed") is not True:
        raise capture.CaptureFailure(
            "stage2_formal_canary_source_audit_failed", str(SOURCE_AUDIT)
        )
    source_index: dict[str, dict[str, Any]] = {}
    for path in SOURCE_MANIFESTS:
        for row in capture.load_jsonl(path):
            episode_id = str(row["episode_id"])
            previous = source_index.setdefault(episode_id, row)
            if previous != row:
                raise capture.CaptureFailure(
                    "stage2_formal_canary_source_episode_conflict",
                    episode_id,
                )
    candidates: defaultdict[tuple[str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for result in audit["recommended_episode_results"]:
        episode_id = str(result["artifact_episode_id"])
        row = source_index.get(episode_id)
        if row is None:
            raise capture.CaptureFailure(
                "stage2_formal_canary_source_episode_missing", episode_id
            )
        key = (str(result["weapon"]), str(result["arm"]))
        candidates[key].append(row)
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for weapon in WEAPONS:
        for _, arm in OUTCOME_RECIPES:
            key = (weapon, arm)
            matches = sorted(
                candidates.get(key, []), key=lambda row: row["episode_id"]
            )
            if not matches:
                raise capture.CaptureFailure(
                    "stage2_formal_canary_source_arm_missing",
                    capture.canonical_json({"weapon": weapon, "arm": arm}),
                )
            selected[key] = matches[0]
    return selected


def appearances() -> list[dict[str, Any]]:
    catalog = json.loads(CONTENT_CATALOG.read_text(encoding="utf-8"))
    result = list(catalog["enemy_appearances"])
    if len(result) != 14:
        raise capture.CaptureFailure(
            "stage2_formal_canary_appearance_catalog_shape", str(len(result))
        )
    return result


def single_tap_program(weapon: str) -> tuple[dict[str, Any], list[int]]:
    start = 96 if weapon == "Vortex" else 104
    return (
        {
            "schema_version": causal.FIRE_PROGRAM_SCHEMA,
            "name": "single_tap",
            "weapon_fire_family": stochastic_v1.FIRE_FAMILY[weapon],
            "windows": [
                {"start_output_tick": start, "duration_ticks": 2}
            ],
            "expected_min_fire_events": 1,
            "expected_max_fire_events": 1,
            "requires_multiple_fire_events": False,
            "selection_uses_authoritative_events": True,
        },
        [start],
    )


def materialize() -> list[dict[str, Any]]:
    commit = source_commit()
    data_spec_sha256 = capture.sha256_file(DATA_SPEC)
    sources = source_rows()
    appearance_rows = appearances()
    rows: list[dict[str, Any]] = []
    for weapon_index, weapon in enumerate(WEAPONS):
        for recipe_index, (outcome_recipe, arm) in enumerate(
            OUTCOME_RECIPES
        ):
            ordinal = len(rows)
            source = sources[(weapon, arm)]
            row = copy.deepcopy(source)
            row.pop("weapon_balanced_review_design", None)
            if outcome_recipe in {"hit_survive", "kill"}:
                fire_program, fire_ticks = single_tap_program(weapon)
                row["causal_design"]["fire_program"] = fire_program
                row["causal_design"]["fire_output_ticks"] = fire_ticks
            appearance = appearance_rows[ordinal % len(appearance_rows)]
            row["enemy_model"] = appearance["model"]
            row["enemy_skin"] = int(appearance["skin"])
            row["enemy_color"] = (0, 68, 204)[ordinal % 3]
            row["enemy"]["health"] = (
                KILL_HEALTH_BY_WEAPON[weapon]
                if outcome_recipe == "kill"
                else SURVIVE_HEALTH
            )
            episode_id = (
                f"s2fcv1_g{weapon_index + 1:02d}_"
                f"{capture.WEAPON_NETNAME[weapon]}_"
                f"{outcome_recipe}_{arm}"
            )
            row.update(
                {
                    "episode_id": episode_id,
                    "counterfactual_group_id": (
                        f"s2fcv1_g{weapon_index + 1:02d}_"
                        f"{capture.WEAPON_NETNAME[weapon]}"
                    ),
                    "anchor_id": (
                        f"s2fcv1_g{weapon_index + 1:02d}_"
                        f"{capture.WEAPON_NETNAME[weapon]}_nine_recipe"
                    ),
                    "source_commit_required": commit,
                    "data_spec_sha256": data_spec_sha256,
                    "category": "stage2_formal_shaped_primary_interaction",
                    "candidate_kind": "stage2_formal_canary_v1",
                    "candidate_status": (
                        "static_certified_pending_live_capture_and_"
                        "aggregate_recipe_audit"
                    ),
                    "training_stage": "stage2_formal_canary_v1_only",
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "human_review_required_before_training": True,
                    "split": "stage2_weapon_balanced_nontraining_review",
                    "canary_role": (
                        f"stage2_formal_canary_{weapon.lower()}_"
                        f"{outcome_recipe}_{arm}"
                    ),
                    "assigned_shard": 0,
                    "shard_count": SHARD_COUNT,
                    "target_ordinal": ordinal,
                }
            )
            row["causal_design"]["intended_outcome_is_acceptance_gate"] = False
            row["acceptance"] = {
                "actual_outcome": None,
                "actual_outcome_rebucket_required": True,
                "fire_required": outcome_recipe != "no_fire",
                "reload_success": False,
                "player_motion_qa_required": True,
                "player_self_damage_allowed": True,
                "player_death_allowed": False,
            }
            row["policy_labels"] = {
                **row["policy_labels"],
                "outcome_recipe": outcome_recipe,
                "outcome_assignment": (
                    "post_capture_authoritative_target_damage_per_shot"
                ),
                "distribution_assignment": (
                    "pre_capture_weapon_outcome_aim_recipe"
                ),
            }
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            certificate = v3_builder.static_action_certificate(row)
            certificate["schema_version"] = STATIC_CERTIFICATE_SCHEMA
            if not certificate["passed"]:
                raise capture.CaptureFailure(
                    "stage2_formal_canary_static_action_failed",
                    capture.canonical_json(
                        {
                            "episode_id": episode_id,
                            "certificate": certificate,
                        }
                    ),
                )
            row["formal_canary_design"] = {
                "schema_version": DESIGN_SCHEMA,
                "source_episode_id": source["episode_id"],
                "source_manifest_sha256": capture.sha256_file(
                    next(
                        path
                        for path in SOURCE_MANIFESTS
                        if any(
                            source["episode_id"] == candidate["episode_id"]
                            for candidate in capture.load_jsonl(path)
                        )
                    )
                ),
                "weapon_index": weapon_index,
                "recipe_index": recipe_index,
                "outcome_recipe": outcome_recipe,
                "outcome_recipe_is_individual_admission_gate": False,
                "arm": arm,
                "enemy_health": float(row["enemy"]["health"]),
                "kill_health_source": (
                    "below_v4_v5r2_stable_track_minimum_direct_damage"
                    if outcome_recipe == "kill"
                    else None
                ),
                "fire_event_target": (
                    0
                    if outcome_recipe == "no_fire"
                    else 1
                    if outcome_recipe in {"hit_survive", "kill"}
                    else 2
                ),
                "static_action_certificate": certificate,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
                "runtime_outcome_fallback": False,
            }
            causal.validate_scenario_contract(row)
            capture.validate_scenario_assets(row)
            rows.append(row)

    input_text = canonical_lines(rows)
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", input_text)
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(shard_path, input_text)
    metadata = {
        "schema_version": MANIFEST_SCHEMA,
        "source_commit": commit,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "shard_count": SHARD_COUNT,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "nontraining_formal_shaped_canary": True,
        "outcome_recipe_is_individual_admission_gate": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
        "weapon_distribution": dict(Counter(row["weapon"] for row in rows)),
        "planned_outcome_distribution": dict(
            Counter(
                row["formal_canary_design"]["outcome_recipe"] for row in rows
            )
        ),
        "aim_arm_distribution": dict(
            Counter(row["causal_design"]["aim_policy"] for row in rows)
        ),
        "appearance_distribution": dict(
            Counter(
                f"{row['enemy_model']}:{row['enemy_skin']}" for row in rows
            )
        ),
        "map_distribution": dict(Counter(row["map"] for row in rows)),
        "gametype_distribution": dict(
            Counter(row["gametype"] for row in rows)
        ),
        "kill_health_by_weapon": KILL_HEALTH_BY_WEAPON,
        "input_sha256": hashlib.sha256(
            input_text.encode("utf-8")
        ).hexdigest(),
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": [
                {
                    "shard_index": 0,
                    "rows": len(rows),
                    "path": str(shard_path.relative_to(ROOT)),
                    "sha256": hashlib.sha256(
                        input_text.encode("utf-8")
                    ).hexdigest(),
                }
            ],
        },
    }
    write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        capture.canonical_json(
            {
                "output": str(OUTPUT_ROOT),
                "rows": len(rows),
                "planned_outcomes": dict(
                    Counter(
                        row["formal_canary_design"]["outcome_recipe"]
                        for row in rows
                    )
                ),
                "source_commit": source_commit(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
