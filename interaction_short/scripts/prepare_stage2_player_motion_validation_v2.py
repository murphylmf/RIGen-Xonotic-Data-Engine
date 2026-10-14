                      
"""Build v3 moving/jumping groups from certified path encounters."""

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
    ROOT / "manifests/stage2_path_encounter_certification_v1/input.jsonl"
)
CERTIFICATE_INDEX = (
    ROOT
    / "stage2_path_encounter_certification_v1_output/review/"
    "PATH_ENCOUNTER_CERTIFICATES.jsonl"
)
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_player_motion_validation_v2"
)


MOVING_SCHEDULES: dict[str, dict[str, Any]] = {
    "visible_no_response": causal.default_aim_schedule(
        "visible_no_response"
    ),
    "delayed_acquisition": {
        **causal.default_aim_schedule("delayed_acquisition"),
        "response_start_output_tick": 32,
        "acquisition_end_output_tick": 64,
    },
    "pass_offset": {
        **causal.default_aim_schedule("pass_offset"),
        "response_start_output_tick": 16,
        "pass_end_output_tick": 48,
        "depart_end_output_tick": 64,
    },
    "track_loss_reacquire": {
        **causal.default_aim_schedule("track_loss_reacquire"),
        "response_start_output_tick": 8,
        "acquisition_end_output_tick": 40,
        "centered_hold_end_output_tick": 64,
        "loss_end_output_tick": 80,
        "lost_hold_end_output_tick": 104,
        "reacquisition_end_output_tick": 136,
    },
    "sustained_tracking": {
        **causal.default_aim_schedule("sustained_tracking"),
        "response_start_output_tick": 8,
        "acquisition_end_output_tick": 40,
        "minimum_visible_tracking_frames": 128,
    },
}

JUMPING_SCHEDULES: dict[str, dict[str, Any]] = {
    "visible_no_response": causal.default_aim_schedule(
        "visible_no_response"
    ),
    "delayed_acquisition": {
        **causal.default_aim_schedule("delayed_acquisition"),
        "response_start_output_tick": 8,
        "acquisition_end_output_tick": 20,
    },
    "pass_offset": {
        **causal.default_aim_schedule("pass_offset"),
        "response_start_output_tick": 4,
        "pass_end_output_tick": 12,
        "depart_end_output_tick": 20,
    },
    "track_loss_reacquire": {
        **causal.default_aim_schedule("track_loss_reacquire"),
        "response_start_output_tick": 2,
        "acquisition_end_output_tick": 10,
        "centered_hold_end_output_tick": 18,
        "loss_end_output_tick": 24,
        "lost_hold_end_output_tick": 30,
        "reacquisition_end_output_tick": 38,
    },
    "sustained_tracking": {
        **causal.default_aim_schedule("sustained_tracking"),
        "response_start_output_tick": 2,
        "acquisition_end_output_tick": 10,
        "minimum_visible_tracking_frames": 40,
    },
}

MOVING_FIRE = {
    "visible_no_response": [],
    "delayed_acquisition": [80, 144],
    "pass_offset": [80, 144],
    "track_loss_reacquire": [144, 176],
    "sustained_tracking": [64, 128, 192],
}
JUMPING_FIRE = {
    "visible_no_response": [],
    "delayed_acquisition": [28, 44],
    "pass_offset": [28, 44],
    "track_loss_reacquire": [44, 56],
    "sustained_tracking": [20, 36, 52],
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


def materialize() -> list[dict[str, Any]]:
    scenarios = {
        row["episode_id"]: row
        for row in capture.load_jsonl(SOURCE_MANIFEST)
    }
    certificates = capture.load_jsonl(CERTIFICATE_INDEX)
    if {
        row["player_motion_class"] for row in certificates
    } != {"moving", "jumping"}:
        raise capture.CaptureFailure(
            "stage2_motion_certificate_classes_missing"
        )
    index_sha = capture.sha256_file(CERTIFICATE_INDEX)
    rows: list[dict[str, Any]] = []
    ordered = sorted(
        certificates,
        key=lambda item: (
            item["player_motion_class"] != "moving",
            item["certificate_id"],
        ),
    )
    for group_ordinal, certificate in enumerate(ordered, 1):
        source = scenarios[certificate["source_episode_id"]]
        motion_class = certificate["player_motion_class"]
        schedules = (
            MOVING_SCHEDULES
            if motion_class == "moving"
            else JUMPING_SCHEDULES
        )
        fire_programs = (
            MOVING_FIRE
            if motion_class == "moving"
            else JUMPING_FIRE
        )
        group_id = f"s2playermotionv3_g{group_ordinal:02d}"
        reference = {
            "schema_version": (
                "xonotic-stage2-encounter-certificate-reference-v1"
            ),
            "index_path": str(CERTIFICATE_INDEX.relative_to(ROOT)),
            "index_sha256": index_sha,
            "certificate_id": certificate["certificate_id"],
            "record_sha256": hashlib.sha256(
                capture.canonical_json(certificate).encode("utf-8")
            ).hexdigest(),
        }
        for policy_ordinal, policy in enumerate(
            causal.AIM_POLICIES, 1
        ):
            row = copy.deepcopy(source)
            row.update(
                {
                    "episode_id": (
                        f"{group_id}_p{policy_ordinal:02d}_{policy}"
                    ),
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "category": f"stage2_v3_{policy}",
                    "candidate_kind": (
                        "player_motion_causal_validation_v3"
                    ),
                    "candidate_status": (
                        "certified_encounter_policy_candidate"
                    ),
                    "training_stage": (
                        "stage2_bounded_player_motion_validation_v3_only"
                    ),
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "encounter_certificate": reference,
                    "supersedes_cohort": (
                        "stage2_player_motion_validation_v1"
                    ),
                    "supersession_reason": (
                        "relative_baseline_aim_qa_and_"
                        "certificate_bounded_policy_windows"
                    ),
                    "canary_role": (
                        f"stage2_player_motion_v3_{policy}"
                    ),
                }
            )
            design = row["causal_design"]
            design.update(
                {
                    "aim_policy": policy,
                    "aim_schedule": copy.deepcopy(
                        schedules[policy]
                    ),
                    "acquisition_start_output_tick": int(
                        schedules[policy].get(
                            "response_start_output_tick"
                        )
                        or 0
                    ),
                    "fire_output_ticks": list(
                        fire_programs[policy]
                    ),
                }
            )
            row["policy_labels"]["aim_policy"] = policy
            row["acceptance"]["actual_outcome"] = None
            row["exogenous_contract_sha256"] = (
                causal.exogenous_contract_sha256(row)
            )
            causal.validate_scenario_contract(row)
            capture.validate_scenario_assets(row)
            causal.causal_action_rows(row)
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
            len(members) != len(causal.AIM_POLICIES)
            or len(
                {
                    row["exogenous_contract_sha256"]
                    for row in members
                }
            )
            != 1
        ):
            raise capture.CaptureFailure(
                "stage2_v3_counterfactual_group_invalid",
                group_id,
            )

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-player-motion-validation-manifest-v2"
        ),
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "encounter_certificate_index": str(CERTIFICATE_INDEX),
        "encounter_certificate_index_sha256": index_sha,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(ordered),
            "motion_classes": [
                row["player_motion_class"] for row in ordered
            ],
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard_path),
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
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
