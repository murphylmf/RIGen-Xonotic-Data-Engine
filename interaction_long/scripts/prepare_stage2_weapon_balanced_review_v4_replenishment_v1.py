                      
"""Create operational replacements for fail-closed V4 review slots.

Only terminal QA failures are eligible.  Weapon, aim arm, exogenous geometry,
and logical slot stay fixed.  A replacement receives a new episode ID, new
manifest-frozen motor/random seed, and fire windows shifted by eight ticks.
Realized target hit/miss is never read by this generator.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_weapon_balanced_review_v4 as v4              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


BASE_ROOT = ROOT / "manifests/stage2_weapon_balanced_review_v4"
BASE_MANIFEST = BASE_ROOT / "input.jsonl"
BASE_METADATA = BASE_ROOT / "MANIFEST_METADATA.json"
BASE_OUTPUT = ROOT / "stage2_weapon_balanced_review_v4_output"
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v4_replenishment_v1"
)
SHARD_COUNT = 4
MANIFEST_SCHEMA = (
    "xonotic-stage2-weapon-balanced-review-v4-operational-"
    "replenishment-manifest-v1"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-weapon-balanced-review-v4-operational-"
    "replenishment-design-v1"
)


def terminal_rejections() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(
        (BASE_OUTPUT / "manifests/shards").glob(
            "shard-*-of-*/rejects.jsonl"
        )
    ):
        for row in capture.load_jsonl(path):
            if row.get("terminal") is not True:
                continue
            episode_id = str(row["episode_id"])
            if episode_id in records:
                raise capture.CaptureFailure(
                    "stage2_v4_duplicate_terminal_reject", episode_id
                )
            records[episode_id] = row
    return records


def accepted_ids() -> set[str]:
    result: set[str] = set()
    for path in sorted(
        (BASE_OUTPUT / "manifests/shards").glob(
            "shard-*-of-*/accepted.jsonl"
        )
    ):
        for row in capture.load_jsonl(path):
            episode_id = str(row["episode_id"])
            if episode_id in result:
                raise capture.CaptureFailure(
                    "stage2_v4_duplicate_accepted", episode_id
                )
            result.add(episode_id)
    return result


def shifted_fire_program(
    base: dict[str, Any],
) -> tuple[dict[str, Any], list[int]]:
    program = copy.deepcopy(base)
    if program["name"] == "none":
        return program, []
    for window in program["windows"]:
        window["start_output_tick"] = (
            int(window["start_output_tick"]) + 8
        )
    ticks = [
        int(window["start_output_tick"])
        for window in program["windows"]
    ]
    return program, ticks


def replacement_aim_program(
    base: dict[str, Any],
    *,
    seed: int,
    weapon: str,
    fire_ticks: list[int],
) -> dict[str, Any]:
    program = copy.deepcopy(base)
    arm = str(program["arm"])
    program["seed"] = seed
    if arm in causal.WEAPON_BALANCED_HUMANIZED_ARMS:
        style = str(program["motor_profile"]["style"])
        program["motor_profile"] = causal.humanized_aim_motor_profile(
            seed, style
        )
    else:
        program["random_aim_program"] = v4.random_aim_program(
            seed,
            arm,
            weapon,
            set(fire_ticks),
        )
    causal.validate_weapon_balanced_aim_program(program)
    return program


def materialize() -> list[dict[str, Any]]:
    base_rows = {
        str(row["episode_id"]): row
        for row in capture.load_jsonl(BASE_MANIFEST)
    }
    rejected = terminal_rejections()
    accepted = accepted_ids()
    missing = set(base_rows) - accepted
    if set(rejected) != missing:
        raise capture.CaptureFailure(
            "stage2_v4_replenishment_terminal_accounting",
            capture.canonical_json(
                {
                    "terminal_only": sorted(set(rejected) - missing),
                    "missing_without_terminal": sorted(
                        missing - set(rejected)
                    ),
                }
            ),
        )
    if not rejected:
        raise capture.CaptureFailure(
            "stage2_v4_replenishment_not_needed",
            "base review has no terminal rejects",
        )

    base_metadata = json.loads(
        BASE_METADATA.read_text(encoding="utf-8")
    )
    for path, digest in base_metadata["runtime_code"].items():
        if capture.sha256_file(ROOT / path) != digest:
            raise capture.CaptureFailure(
                "stage2_v4_replenishment_runtime_drift", path
            )

    rows: list[dict[str, Any]] = []
    for ordinal, base_episode_id in enumerate(sorted(rejected)):
        base = base_rows[base_episode_id]
        rejection = rejected[base_episode_id]
        row = copy.deepcopy(base)
        design = row["causal_design"]
        fire_program, fire_ticks = shifted_fire_program(
            design["fire_program"]
        )
        aim_seed = 15_650_000 + ordinal + 1
        fire_seed = 15_750_000 + ordinal + 1
        design["fire_program"] = fire_program
        design["fire_output_ticks"] = fire_ticks
        design["fire_seed"] = fire_seed
        design["weapon_balanced_aim_program"] = (
            replacement_aim_program(
                design["weapon_balanced_aim_program"],
                seed=aim_seed,
                weapon=str(row["weapon"]),
                fire_ticks=fire_ticks,
            )
        )
        base_aim = base["causal_design"][
            "weapon_balanced_aim_program"
        ]
        replacement_aim = design["weapon_balanced_aim_program"]
        for field in (
            "arm",
            "family",
            "offset_direction_deg",
            "offset_radius_kind",
            "projectile_lead",
            "response_start_output_tick",
            "settle_output_tick",
            "target_offset_scale",
            "target_radius_model",
        ):
            if replacement_aim[field] != base_aim[field]:
                raise capture.CaptureFailure(
                    "stage2_v4_replenishment_aim_stratum_drift",
                    f"{base_episode_id}:{field}",
                )
        row.update(
            {
                "episode_id": f"{base_episode_id}_oprep01",
                "candidate_kind": (
                    "stage2_weapon_balanced_review_v4_"
                    "operational_replenishment_v1"
                ),
                "candidate_status": (
                    "static_certified_operational_replacement_pending_"
                    "live_capture"
                ),
                "training_stage": (
                    "stage2_weapon_balanced_review_v4_"
                    "operational_replenishment_v1_only"
                ),
                "canary_role": (
                    f"{row['canary_role']}_operational_replacement_v1"
                ),
                "assigned_shard": ordinal % SHARD_COUNT,
                "shard_count": SHARD_COUNT,
                "target_ordinal": 20_000 + ordinal,
            }
        )
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        if (
            row["exogenous_contract_sha256"]
            != base["exogenous_contract_sha256"]
        ):
            raise capture.CaptureFailure(
                "stage2_v4_replenishment_exogenous_drift",
                base_episode_id,
            )
        certificate = v4.v3_builder.static_action_certificate(row)
        certificate["schema_version"] = (
            "xonotic-stage2-weapon-balanced-v4-operational-"
            "replenishment-static-action-certificate-v1"
        )
        if not certificate["passed"]:
            raise capture.CaptureFailure(
                "stage2_v4_replenishment_static_action_failed",
                row["episode_id"],
            )
        row["weapon_balanced_review_design"].update(
            {
                "schema_version": DESIGN_SCHEMA,
                "replacement_for_episode_id": base_episode_id,
                "replacement_scope": "terminal_qa_failure_only",
                "base_row_sha256": hashlib.sha256(
                    capture.canonical_json(base).encode("utf-8")
                ).hexdigest(),
                "terminal_rejection_sha256": hashlib.sha256(
                    capture.canonical_json(rejection).encode("utf-8")
                ).hexdigest(),
                "terminal_rejection_reason": rejection["reason"],
                "aim_seed": aim_seed,
                "fire_seed": fire_seed,
                "fire_window_shift_ticks": 8,
                "aim_arm_and_direction_preserved": True,
                "static_action_certificate": certificate,
                "outcome_used_for_individual_admission": False,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
                "runtime_outcome_fallback": False,
                "formal_collection_authorized": False,
            }
        )
        causal.validate_scenario_contract(row)
        rows.append(row)

    input_text = v4.canonical_lines(rows)
    v4.write_once_or_verify(OUTPUT_ROOT / "input.jsonl", input_text)
    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = v4.canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        v4.write_once_or_verify(shard_path, shard_text)
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
        "source_commit": base_metadata["source_commit"],
        "data_spec_sha256": base_metadata["data_spec_sha256"],
        "base_manifest": {
            "path": str(BASE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(BASE_MANIFEST),
        },
        "base_metadata": {
            "path": str(BASE_METADATA.relative_to(ROOT)),
            "sha256": capture.sha256_file(BASE_METADATA),
        },
        "rows": len(rows),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "replacement_scope": "terminal_qa_failure_only",
        "realized_outcome_read_by_generator": False,
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "arm_distribution": dict(
            Counter(
                row["causal_design"]["aim_policy"] for row in rows
            )
        ),
        "replacement_for_episode_ids": sorted(rejected),
        "runtime_code": {
            **base_metadata["runtime_code"],
            str(
                Path(__file__).resolve().relative_to(ROOT)
            ): capture.sha256_file(Path(__file__).resolve()),
        },
    }
    v4.write_once_or_verify(
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
                "weapons": dict(
                    Counter(row["weapon"] for row in rows)
                ),
                "arms": dict(
                    Counter(
                        row["causal_design"]["aim_policy"]
                        for row in rows
                    )
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
