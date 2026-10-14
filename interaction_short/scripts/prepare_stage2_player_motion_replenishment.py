                      
"""Build fresh-seed v3 motion groups from the latest certificates."""

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
GROUP_PREFIX = "s2playermotion_repl"
CANDIDATE_KIND = "player_motion_causal_replenishment_v1"
TRAINING_STAGE = (
    "stage2_bounded_player_motion_replenishment_only"
)
SUPERSEDES_COHORT = "stage2_player_motion_validation_v2"
SUPERSESSION_REASON = "new_route_seed_after_terminal_writer_bypass"
MANIFEST_SCHEMA = (
    "xonotic-stage2-player-motion-replenishment-manifest-v1"
)
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_player_motion_replenishment_v1"
)
SOURCES = (
    {
        "motion_class": "moving",
        "manifest": (
            ROOT
            / "manifests/stage2_path_encounter_certification_v2/"
            "input.jsonl"
        ),
        "episode_id": "s2pathcertv2_01_s1route_12587",
        "certificate_index": (
            ROOT
            / "stage2_path_encounter_certification_v2_output/"
            "review/PATH_ENCOUNTER_CERTIFICATES.jsonl"
        ),
    },
    {
        "motion_class": "jumping",
        "manifest": (
            ROOT
            / "manifests/stage2_path_encounter_certification_v4/"
            "input.jsonl"
        ),
        "episode_id": "s2pathcertv4_01_s1route_11563",
        "certificate_index": (
            ROOT
            / "stage2_path_encounter_certification_v4_output/"
            "review/PATH_ENCOUNTER_CERTIFICATES.jsonl"
        ),
    },
)

DEFAULT_FIRE = {
    "visible_no_response": [],
    "delayed_acquisition": [176, 256],
    "pass_offset": [176, 256],
    "track_loss_reacquire": [248, 296],
    "sustained_tracking": [88, 176, 264],
}
JUMPING_SCHEDULES = {
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
JUMPING_FIRE = {
    "visible_no_response": [],
    "delayed_acquisition": [80, 144],
    "pass_offset": [80, 144],
    "track_loss_reacquire": [144, 176],
    "sustained_tracking": [64, 128, 176],
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
    rows: list[dict[str, Any]] = []
    for group_ordinal, source_spec in enumerate(SOURCES, 1):
        source_rows = {
            row["episode_id"]: row
            for row in capture.load_jsonl(source_spec["manifest"])
        }
        source = source_rows[source_spec["episode_id"]]
        certificate_index = source_spec["certificate_index"]
        certificates = capture.load_jsonl(certificate_index)
        if len(certificates) != 1:
            raise capture.CaptureFailure(
                "stage2_replenishment_certificate_count",
                str(certificate_index),
            )
        certificate = certificates[0]
        if (
            certificate["source_episode_id"]
            != source["episode_id"]
            or certificate["player_motion_class"]
            != source_spec["motion_class"]
        ):
            raise capture.CaptureFailure(
                "stage2_replenishment_certificate_identity"
            )
        certificate_reference = {
            "schema_version": (
                "xonotic-stage2-encounter-certificate-reference-v1"
            ),
            "index_path": str(certificate_index.relative_to(ROOT)),
            "index_sha256": capture.sha256_file(
                certificate_index
            ),
            "certificate_id": certificate["certificate_id"],
            "record_sha256": hashlib.sha256(
                capture.canonical_json(certificate).encode("utf-8")
            ).hexdigest(),
        }
        group_id = f"{GROUP_PREFIX}_g{group_ordinal:02d}"
        for policy_ordinal, policy in enumerate(
            causal.AIM_POLICIES, 1
        ):
            row = copy.deepcopy(source)
            schedules = (
                JUMPING_SCHEDULES
                if source_spec["motion_class"] == "jumping"
                else {
                    name: causal.default_aim_schedule(name)
                    for name in causal.AIM_POLICIES
                }
            )
            fire_programs = (
                JUMPING_FIRE
                if source_spec["motion_class"] == "jumping"
                else DEFAULT_FIRE
            )
            row.update(
                {
                    "episode_id": (
                        f"{group_id}_p{policy_ordinal:02d}_{policy}"
                    ),
                    "counterfactual_group_id": group_id,
                    "anchor_id": f"{group_id}_pair",
                    "category": f"stage2_v3_{policy}",
                    "candidate_kind": CANDIDATE_KIND,
                    "candidate_status": (
                        "certified_encounter_policy_candidate"
                    ),
                    "training_stage": TRAINING_STAGE,
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "encounter_certificate": (
                        certificate_reference
                    ),
                    "supersedes_cohort": SUPERSEDES_COHORT,
                    "supersession_reason": SUPERSESSION_REASON,
                    "canary_role": (
                        f"stage2_player_motion_replenishment_{policy}"
                    ),
                    "expects_sound": policy
                    != "visible_no_response",
                }
            )
            row["encounter_source"].update(
                {
                    "current_trajectory_requires_recertification": (
                        False
                    ),
                    "path_encounter_certificate_id": certificate[
                        "certificate_id"
                    ],
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
            actions = causal.causal_action_rows(row)
            expected_fire = policy != "visible_no_response"
            if bool(sum(action["primary"] for action in actions)) != (
                expected_fire
            ):
                raise capture.CaptureFailure(
                    "stage2_replenishment_fire_program_invalid",
                    row["episode_id"],
                )
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
                "stage2_replenishment_group_invalid", group_id
            )

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": MANIFEST_SCHEMA,
        "source_commit": rows[0]["source_commit_required"],
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "seeds": sorted({row["seed"] for row in rows}),
        "route_ids": sorted(
            {
                row["player_path_source"]["route_id"]
                for row in rows
            }
        ),
        "review": {
            "rows": len(rows),
            "counterfactual_groups": len(SOURCES),
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
                "seeds": sorted({row["seed"] for row in rows}),
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
