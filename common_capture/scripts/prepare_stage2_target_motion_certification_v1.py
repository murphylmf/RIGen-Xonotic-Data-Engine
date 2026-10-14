                      
"""Prepare a bounded, preregistered target-motion certification matrix."""

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
SOURCE = (
    ROOT
    / "manifests/stage2_causal_bootstrap_v5/"
    "encounter_certification/input.jsonl"
)
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_target_motion_certification_v1"
)
PAIR_IDS = (
    "preflight_pair_afterslime_close_r0_wp0086_wp0101",
    "preflight_pair_atelier_close_r0_wp0002_wp0019",
    "preflight_pair_catharsis_close_r0_wp0129_wp0141",
    "preflight_pair_bromine_near_r0_wp0054_wp0056",
    "preflight_pair_geoplanetary_near_r0_wp0010_wp0012",
    "preflight_pair_techassault_near_r0_wp0000_wp0001",
)
MOTIONS = (
    ("lateral_patrol", 1),
    ("approach_retreat", 2),
    ("stop_and_go", 3),
)


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


def materialize() -> list[dict[str, Any]]:
    source_rows = capture.load_jsonl(SOURCE)
    rows: list[dict[str, Any]] = []
    for pair_ordinal, pair_id in enumerate(PAIR_IDS, 1):
        for motion_ordinal, (motion_name, motion_mode) in enumerate(
            MOTIONS, 1
        ):
            matches = [
                row
                for row in source_rows
                if row["encounter_source"][
                    "source_pair_episode_id"
                ]
                == pair_id
                and row["enemy_policy"]["name"] == motion_name
                and int(row["enemy"]["motion"]) == motion_mode
            ]
            if len(matches) != 1:
                raise capture.CaptureFailure(
                    "stage2_target_motion_source_invalid",
                    f"{pair_id}:{motion_name}:{len(matches)}",
                )
            row = copy.deepcopy(matches[0])
            group_id = (
                f"s2targetcertv1_p{pair_ordinal:02d}_"
                f"m{motion_mode}"
            )
            seed = (
                16_200_000
                + (pair_ordinal - 1) * len(MOTIONS)
                + motion_ordinal
            )
            row.update(
                {
                    "schema_version": causal.SCENARIO_SCHEMA_V3,
                    "action_program": causal.ACTION_PROGRAM_V3,
                    "episode_id": f"{group_id}_{motion_name}",
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "seed": seed,
                    "candidate_kind": (
                        "stage2_target_motion_certification_v1"
                    ),
                    "candidate_status": (
                        "preregistered_uncertified_geometry"
                    ),
                    "category": (
                        f"stage2_target_motion_cert_{motion_name}"
                    ),
                    "training_stage": (
                        "stage2_bounded_target_motion_"
                        "certification_v1_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "canary_role": (
                        f"stage2_target_motion_cert_{motion_name}"
                    ),
                    "assigned_shard": 0,
                    "shard_count": 1,
                    "expects_sound": True,
                }
            )
            row["enemy_policy"]["policy_seed"] = (
                15_300_000
                + (pair_ordinal - 1) * len(MOTIONS)
                + motion_ordinal
            )
            design = row["causal_design"]
            design.update(
                {
                    "schema_version": (
                        causal.CAUSAL_DESIGN_SCHEMA_V3
                    ),
                    "aim_policy": "visible_no_response",
                    "aim_schedule": causal.default_aim_schedule(
                        "visible_no_response"
                    ),
                    "acquisition_start_output_tick": 0,
                    "fire_output_ticks": [],
                    "interaction_channel": "primary",
                    "secondary_mechanism": None,
                    "base_player_program": "stationary",
                    "actual_outcome_source": (
                        "authoritative_telemetry_only"
                    ),
                    "intended_outcome_is_acceptance_gate": False,
                }
            )
            row["policy_labels"].update(
                {
                    "aim_policy": "visible_no_response",
                    "interaction_channel": "primary",
                    "outcome_assignment": (
                        "post_capture_authoritative_telemetry_rebucket"
                    ),
                }
            )
            row["acceptance"]["actual_outcome"] = None
            row["acceptance"][
                "actual_outcome_rebucket_required"
            ] = True
            row["encounter_source"][
                "current_trajectory_requires_recertification"
            ] = True
            row["target_motion_certification_design"] = {
                "schema_version": (
                    "xonotic-stage2-target-motion-"
                    "certification-design-v1"
                ),
                "source_manifest": str(SOURCE.relative_to(ROOT)),
                "source_manifest_sha256": capture.sha256_file(
                    SOURCE
                ),
                "source_pair_episode_id": pair_id,
                "selection_preregistered_before_capture": True,
                "motion_name": motion_name,
                "motion_mode": motion_mode,
                "expected_distance_bin": row["policy_labels"][
                    "expected_distance_bin"
                ],
                "runtime_geometry_fallback": False,
                "runtime_action_fallback": False,
                "accepted_geometry_only_enters_certificate_pool": True,
            }
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            causal.validate_scenario_contract(row)
            capture.validate_scenario_assets(row)
            actions = causal.causal_action_rows(row)
            if any(
                action["primary"] or action["secondary"]
                for action in actions
            ):
                raise capture.CaptureFailure(
                    "stage2_target_motion_certification_fire_present",
                    row["episode_id"],
                )
            rows.append(row)

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-target-motion-"
            "certification-manifest-v1"
        ),
        "source_manifest": str(SOURCE.relative_to(ROOT)),
        "source_manifest_sha256": capture.sha256_file(SOURCE),
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "candidate_selection_preregistered_before_capture": True,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "pair_ids": list(PAIR_IDS),
        "motion_modes": [
            {"name": name, "mode": mode}
            for name, mode in MOTIONS
        ],
        "review": {
            "rows": len(rows),
            "pairs": len(PAIR_IDS),
            "motion_modes": len(MOTIONS),
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
                "pairs": len(
                    {
                        row["target_motion_certification_design"][
                            "source_pair_episode_id"
                        ]
                        for row in rows
                    }
                ),
                "motions": sorted(
                    {row["enemy_policy"]["name"] for row in rows}
                ),
                "distance_bins": sorted(
                    {
                        row["policy_labels"][
                            "expected_distance_bin"
                        ]
                        for row in rows
                    }
                ),
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
