                      
"""Build fresh complete groups for incomplete outcome-calibration groups.

The original candidates and terminal rejects are immutable.  This script
materializes a separate, preregistered manifest with a new group, anchor,
scenario seed, and enemy-policy seed for every member of each incomplete
counterfactual group.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_outcome_calibration_v1/input.jsonl"
)
SOURCE_OUTPUT = ROOT / "stage2_outcome_calibration_v1_output"
SOURCE_ACCEPTED = (
    SOURCE_OUTPUT
    / "manifests/shards/shard-000-of-001/accepted.jsonl"
)
SOURCE_REJECTS = (
    SOURCE_OUTPUT
    / "manifests/shards/shard-000-of-001/rejects.jsonl"
)
SOURCE_AUDIT = (
    SOURCE_OUTPUT
    / "review/STAGE2_OUTCOME_CALIBRATION_AUDIT.json"
)
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_outcome_calibration_replenishment_v1"
)
POLICIES = {
    "visible_no_response",
    "pass_offset",
    "delayed_acquisition",
    "sustained_tracking",
}
EXPECTED_INCOMPLETE_GROUPS = {
    "s2outcomev1_g02_shotgun",
    "s2outcomev1_g03_machinegun",
    "s2outcomev1_g07_vortex",
}
EXPECTED_MISSING_EPISODES = {
    "s2outcomev1_g02_shotgun_p03_delayed_acquisition",
    "s2outcomev1_g03_machinegun_p04_sustained_tracking",
    "s2outcomev1_g07_vortex_p04_sustained_tracking",
}


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_manifest_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def terminal_rows() -> dict[str, dict[str, Any]]:
    rows = [
        row
        for row in capture.load_jsonl(SOURCE_REJECTS)
        if row.get("terminal") is True
    ]
    return {row["episode_id"]: row for row in rows}


def incomplete_groups(
    planned: list[dict[str, Any]],
    accepted: list[dict[str, Any]],
) -> tuple[set[str], set[str]]:
    accepted_ids = {row["episode_id"] for row in accepted}
    missing = {
        row["episode_id"]
        for row in planned
        if row["episode_id"] not in accepted_ids
    }
    groups = {
        row["counterfactual_group_id"]
        for row in planned
        if row["episode_id"] in missing
    }
    return groups, missing


def materialize() -> list[dict[str, Any]]:
    planned = capture.load_jsonl(SOURCE_MANIFEST)
    accepted = capture.load_jsonl(SOURCE_ACCEPTED)
    terminal = terminal_rows()
    groups, missing = incomplete_groups(planned, accepted)
    if groups != EXPECTED_INCOMPLETE_GROUPS:
        raise capture.CaptureFailure(
            "stage2_outcome_replenishment_group_drift",
            capture.canonical_json(
                {
                    "expected": sorted(EXPECTED_INCOMPLETE_GROUPS),
                    "actual": sorted(groups),
                }
            ),
        )
    if missing != EXPECTED_MISSING_EPISODES:
        raise capture.CaptureFailure(
            "stage2_outcome_replenishment_missing_episode_drift",
            capture.canonical_json(
                {
                    "expected": sorted(EXPECTED_MISSING_EPISODES),
                    "actual": sorted(missing),
                }
            ),
        )
    if set(terminal) != EXPECTED_MISSING_EPISODES:
        raise capture.CaptureFailure(
            "stage2_outcome_replenishment_terminal_drift",
            capture.canonical_json(sorted(terminal)),
        )

    source_groups = {
        group: [
            row
            for row in planned
            if row["counterfactual_group_id"] == group
        ]
        for group in sorted(groups)
    }
    rows: list[dict[str, Any]] = []
    for group_ordinal, (old_group, members) in enumerate(
        source_groups.items(), 1
    ):
        weapon = members[0]["weapon"]
        new_group = (
            f"s2outcomerepl1_g{group_ordinal:02d}_"
            f"{weapon.lower()}"
        )
        new_seed = 16_100_000 + group_ordinal
        new_enemy_policy_seed = 15_200_000 + group_ordinal
        for source in members:
            row = copy.deepcopy(source)
            policy = row["causal_design"]["aim_policy"]
            policy_ordinal = (
                1
                + (
                    "visible_no_response",
                    "pass_offset",
                    "delayed_acquisition",
                    "sustained_tracking",
                ).index(policy)
            )
            row.update(
                {
                    "episode_id": (
                        f"{new_group}_p{policy_ordinal:02d}_{policy}"
                    ),
                    "counterfactual_group_id": new_group,
                    "anchor_id": f"{new_group}_pair",
                    "seed": new_seed,
                    "candidate_kind": (
                        "stage2_primary_outcome_calibration_"
                        "replenishment_v1"
                    ),
                    "candidate_status": (
                        "fresh_seed_complete_group_replacement"
                    ),
                    "training_stage": (
                        "stage2_bounded_outcome_calibration_"
                        "replenishment_v1_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "canary_role": (
                        "stage2_outcome_calibration_replenishment_"
                        f"{weapon.lower()}_{policy}"
                    ),
                }
            )
            row["enemy_policy"]["policy_seed"] = (
                new_enemy_policy_seed
            )
            row["outcome_calibration_design"].update(
                {
                    "schema_version": (
                        "xonotic-stage2-outcome-calibration-design-v2"
                    ),
                    "replacement_group": True,
                    "source_group_id": old_group,
                    "source_manifest": str(
                        SOURCE_MANIFEST.relative_to(ROOT)
                    ),
                    "source_manifest_sha256": (
                        capture.sha256_file(SOURCE_MANIFEST)
                    ),
                    "replacement_reason": (
                        "complete_group_replacement_after_terminal_"
                        "candidate"
                    ),
                    "post_damage_state_divergence_semantics": (
                        "endogenous_after_first_linked_player_damage"
                    ),
                }
            )
            row["replenishment_contract"] = {
                "schema_version": (
                    "xonotic-stage2-outcome-replenishment-contract-v1"
                ),
                "source_group_id": old_group,
                "source_episode_id": source["episode_id"],
                "source_group_terminal_episode_ids": sorted(
                    episode_id
                    for episode_id in terminal
                    if episode_id.startswith(f"{old_group}_")
                ),
                "source_terminal_reasons": sorted(
                    {
                        terminal[episode_id]["reason"]
                        for episode_id in terminal
                        if episode_id.startswith(f"{old_group}_")
                    }
                ),
                "new_group_id": new_group,
                "new_seed": new_seed,
                "new_enemy_policy_seed": new_enemy_policy_seed,
                "geometry_weapon_policy_mutated": False,
                "runtime_fallback": False,
                "source_candidates_immutable": True,
                "whole_counterfactual_group_replaced": True,
            }
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            causal.validate_scenario_contract(row)
            capture.validate_scenario_assets(row)
            rows.append(row)

    for group_id in {
        row["counterfactual_group_id"] for row in rows
    }:
        members = [
            row
            for row in rows
            if row["counterfactual_group_id"] == group_id
        ]
        if (
            len(members) != len(POLICIES)
            or {
                row["causal_design"]["aim_policy"]
                for row in members
            }
            != POLICIES
            or len(
                {
                    row["exogenous_contract_sha256"]
                    for row in members
                }
            )
            != 1
        ):
            raise capture.CaptureFailure(
                "stage2_outcome_replenishment_group_contract",
                group_id,
            )

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-outcome-calibration-"
            "replenishment-manifest-v1"
        ),
        "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "source_manifest_sha256": capture.sha256_file(
            SOURCE_MANIFEST
        ),
        "source_accepted_manifest": str(
            SOURCE_ACCEPTED.relative_to(ROOT)
        ),
        "source_accepted_manifest_sha256": capture.sha256_file(
            SOURCE_ACCEPTED
        ),
        "source_reject_manifest": str(
            SOURCE_REJECTS.relative_to(ROOT)
        ),
        "source_reject_manifest_sha256": capture.sha256_file(
            SOURCE_REJECTS
        ),
        "source_audit": str(SOURCE_AUDIT.relative_to(ROOT)),
        "source_audit_sha256": capture.sha256_file(SOURCE_AUDIT),
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "source_candidates_immutable": True,
        "actual_outcome_used_for_episode_acceptance": False,
        "actual_outcome_source": "authoritative_telemetry_only",
        "expected_incomplete_source_groups": sorted(
            EXPECTED_INCOMPLETE_GROUPS
        ),
        "expected_terminal_source_episode_ids": sorted(
            EXPECTED_MISSING_EPISODES
        ),
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(source_groups),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard_path.relative_to(ROOT)),
                    "rows": len(rows),
                    "sha256": hashlib.sha256(
                        text.encode("utf-8")
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
        json.dumps(
            {
                "rows": len(rows),
                "groups": len(
                    {
                        row["counterfactual_group_id"]
                        for row in rows
                    }
                ),
                "seeds": sorted({row["seed"] for row in rows}),
                "weapons": sorted({row["weapon"] for row in rows}),
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
