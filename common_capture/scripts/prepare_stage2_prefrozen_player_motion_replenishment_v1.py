                      
"""Create the immutable mild-motion replenishment for Stage-2 review v1."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_prefrozen_player_motion_review_v1 as parent              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_stochastic_review_v1/input.jsonl"
)
PARENT_MANIFEST = parent.OUTPUT_ROOT / "input.jsonl"
PARENT_FAILED_AUDIT = (
    ROOT
    / "stage2_prefrozen_player_motion_review_v1_output"
    / "SELECTION_AUDIT.json"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_prefrozen_player_motion_replenishment_v1"
)
SHARD_COUNT = 4
MANIFEST_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-replenishment-manifest-v1"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-prefrozen-player-motion-replenishment-design-v1"
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
    return "".join(
        capture.canonical_json(row) + "\n" for row in rows
    )


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_prefrozen_motion_replenishment_drift",
                str(path),
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def mild_player_movement_program(
    seed: int, profile: str
) -> dict[str, Any]:
    """Scale a two-axis weave to low displacement while keeping reversals."""
    program = copy.deepcopy(
        parent.player_movement_program(seed, profile)
    )
    rng = random.Random(seed + 911_731)
    if profile == "lateral_weave":
        target_x_span = rng.uniform(0.235, 0.255)
        target_y_span = rng.uniform(0.135, 0.150)
    else:
        target_x_span = rng.uniform(0.135, 0.150)
        target_y_span = rng.uniform(0.235, 0.255)

    def scale_span(values: list[float], target: float) -> list[float]:
        span = max(values) - min(values)
        return [
            round(float(value) * target / span, 6)
            for value in values
        ]

    program["j_left_x"] = scale_span(
        program["j_left_x"], target_x_span
    )
    program["j_left_y"] = scale_span(
        program["j_left_y"], target_y_span
    )
    program["max_abs_axis_value"] = max(
        0.12,
        round(
            max(
                abs(value)
                for value in program["j_left_x"]
                + program["j_left_y"]
            ),
            6,
        ),
    )
    causal.validate_player_movement_program(program)
    return program


def source_groups() -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for row in capture.load_jsonl(SOURCE_MANIFEST):
        weapon = str(row["weapon"])
        variant = str(
            row["stochastic_review_design"]["random_aim_variant"]
        )
        result.setdefault(weapon, {})[variant] = row
    for weapon in parent.stochastic_v1.human_v2.WEAPONS:
        if set(result.get(weapon, {})) != set(
            parent.stochastic_v1.VARIANTS
        ):
            raise capture.CaptureFailure(
                "stage2_motion_replenishment_source_shape", weapon
            )
    return result


def materialize() -> list[dict[str, Any]]:
    if not PARENT_FAILED_AUDIT.is_file():
        raise capture.CaptureFailure(
            "parent_failed_selection_audit_missing",
            str(PARENT_FAILED_AUDIT),
        )
    parent_audit = json.loads(
        PARENT_FAILED_AUDIT.read_text(encoding="utf-8")
    )
    if parent_audit.get("passed") is not False:
        raise capture.CaptureFailure(
            "parent_selection_did_not_fail_closed",
            capture.canonical_json(
                {"passed": parent_audit.get("passed")}
            ),
        )
    locked_parent_audit_text = (
        json.dumps(parent_audit, indent=2, sort_keys=True) + "\n"
    )
    write_once_or_verify(
        OUTPUT_ROOT / "PARENT_FAILED_SELECTION_AUDIT.json",
        locked_parent_audit_text,
    )
    commit = source_commit()
    sources = source_groups()
    data_spec_sha256 = capture.sha256_file(
        ROOT / "XONOTIC_DATA_SPEC_V2.md"
    )
    rows: list[dict[str, Any]] = []
    weapons = parent.stochastic_v1.human_v2.WEAPONS
    for weapon_index, weapon in enumerate(weapons):
                                                                              
                                                                      
        profile = (
            "lateral_weave"
            if weapon_index % 2 == 0
            else "approach_retreat"
        )
        group_id = (
            f"s2pmr1_g{weapon_index + 1:02d}_"
            f"{capture.WEAPON_NETNAME[weapon]}"
        )
        movement_seed = 16_100_000 + weapon_index + 1
        movement = mild_player_movement_program(
            movement_seed, profile
        )
        for variant in parent.stochastic_v1.VARIANTS:
            row_ordinal = len(rows)
            row = copy.deepcopy(sources[weapon][variant])
            row.pop("stochastic_review_design", None)
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V8,
                    "action_program": causal.ACTION_PROGRAM_V8,
                    "episode_id": f"{group_id}_{variant}",
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "source_commit_required": commit,
                    "category": (
                        "stage2_prefrozen_player_motion_mild_"
                        "replenishment"
                    ),
                    "candidate_kind": (
                        "stage2_prefrozen_player_motion_"
                        "replenishment_v1"
                    ),
                    "candidate_status": (
                        "static_certified_pending_live_capture_and_"
                        "combined_group_selection"
                    ),
                    "training_stage": (
                        "stage2_prefrozen_player_motion_"
                        "replenishment_v1_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "human_review_required_before_training": True,
                    "canary_role": (
                        f"stage2_prefrozen_motion_replenishment_"
                        f"{weapon.lower()}_{profile}_{variant}"
                    ),
                    "data_spec_sha256": data_spec_sha256,
                    "shard_count": SHARD_COUNT,
                    "assigned_shard": row_ordinal % SHARD_COUNT,
                    "target_ordinal": row_ordinal,
                    "split": (
                        "stage2_prefrozen_player_motion_replenishment_"
                        "nontraining_review_candidates"
                    ),
                }
            )
            design = row["causal_design"]
            design.update(
                {
                    "schema_version": causal.CAUSAL_DESIGN_SCHEMA_V8,
                    "base_player_program": (
                        "manifest_frozen_continuous_movement"
                    ),
                    "player_movement_program": movement,
                    "player_health_policy": "player_alive",
                }
            )
            row["acceptance"].update(
                {
                    "actual_outcome": None,
                    "actual_outcome_rebucket_required": True,
                    "player_motion_qa_required": True,
                    "player_self_damage_allowed": True,
                    "player_death_allowed": False,
                }
            )
            row["policy_labels"].update(
                {
                    "player_motion_class": (
                        "prefrozen_continuous_movement"
                    ),
                    "player_motion_profile": profile,
                    "player_motion_candidate": "replenishment_c",
                    "player_motion_amplitude_class": (
                        "hit_preserving_mild"
                    ),
                }
            )
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            certificate = parent.static_action_certificate(row)
            if not certificate["passed"]:
                raise capture.CaptureFailure(
                    "stage2_motion_replenishment_static_action_failed",
                    capture.canonical_json(
                        {
                            "episode_id": row["episode_id"],
                            "certificate": certificate,
                        }
                    ),
                )
            row["prefrozen_player_motion_replenishment_design"] = {
                "schema_version": DESIGN_SCHEMA,
                "source_manifest": str(
                    SOURCE_MANIFEST.relative_to(ROOT)
                ),
                "source_episode_id": sources[weapon][variant][
                    "episode_id"
                ],
                "parent_candidate_manifest": str(
                    PARENT_MANIFEST.relative_to(ROOT)
                ),
                "parent_failed_selection_audit": str(
                    (
                        OUTPUT_ROOT
                        / "PARENT_FAILED_SELECTION_AUDIT.json"
                    ).relative_to(ROOT)
                ),
                "replenishment_reason": (
                    "restore_missing_weapon_group_and_confirmed_enemy_"
                    "hit_volume_after_fail_closed_v1"
                ),
                "motion_profile": profile,
                "motion_amplitude_class": "hit_preserving_mild",
                "movement_seed": movement_seed,
                "player_health_policy": "player_alive",
                "self_damage_counts_as_enemy_hit": False,
                "enemy_hit_source": (
                    "authoritative_enemy_target_damage_parent_graph"
                ),
                "static_action_certificate": certificate,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
                "runtime_outcome_fallback": False,
                "formal_collection_authorized": False,
            }
            causal.validate_scenario_contract(row)
            rows.append(row)

    for group_id in sorted(
        {row["counterfactual_group_id"] for row in rows}
    ):
        members = [
            row
            for row in rows
            if row["counterfactual_group_id"] == group_id
        ]
        if len(members) != len(parent.stochastic_v1.VARIANTS):
            raise capture.CaptureFailure(
                "stage2_motion_replenishment_group_shape", group_id
            )
        if len(
            {
                row["exogenous_contract_sha256"]
                for row in members
            }
        ) != 1:
            raise capture.CaptureFailure(
                "stage2_motion_replenishment_group_exogenous_drift",
                group_id,
            )

    input_text = canonical_lines(rows)
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", input_text)
    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        write_once_or_verify(shard_path, shard_text)
        shard_metadata.append(
            {
                "shard_index": shard_index,
                "path": str(shard_path.relative_to(ROOT)),
                "rows": len(shard_rows),
                "sha256": hashlib.sha256(
                    shard_text.encode("utf-8")
                ).hexdigest(),
            }
        )
    metadata = {
        "schema_version": MANIFEST_SCHEMA,
        "source_manifest": {
            "path": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(SOURCE_MANIFEST),
        },
        "parent_candidate_manifest": {
            "path": str(PARENT_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(PARENT_MANIFEST),
        },
        "parent_failed_selection_audit": {
            "path": str(
                (
                    OUTPUT_ROOT
                    / "PARENT_FAILED_SELECTION_AUDIT.json"
                ).relative_to(ROOT)
            ),
            "sha256": capture.sha256_file(
                OUTPUT_ROOT / "PARENT_FAILED_SELECTION_AUDIT.json"
            ),
        },
        "source_commit": commit,
        "data_spec_sha256": data_spec_sha256,
        "rows": len(rows),
        "counterfactual_groups": len(weapons),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "replenishment_policy": {
            "groups_per_weapon": 1,
            "group_selection_unit": "whole_three_arm_group",
            "player_health_policy": "player_alive",
            "self_damage_counts_as_enemy_hit": False,
            "enemy_hit_source": (
                "authoritative_enemy_target_damage_parent_graph"
            ),
            "runtime_fallback": False,
        },
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_prefrozen_player_motion_replenishment_v1.py",
            )
        },
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "motion_profile_distribution": dict(
            Counter(
                row[
                    "prefrozen_player_motion_replenishment_design"
                ]["motion_profile"]
                for row in rows
            )
        ),
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
                "groups": len(
                    {
                        row["counterfactual_group_id"]
                        for row in rows
                    }
                ),
                "source_commit": source_commit(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
