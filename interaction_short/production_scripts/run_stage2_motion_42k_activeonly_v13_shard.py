                      
"""Run one v13 shard with the proven v12r6 resilient quota engine."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "production_scripts"))

import run_stage2_motion_42k_activeonly_v12r6_shard as quota              
from pilot_scripts import build_samples_v13 as pilot              


quota.pilot = pilot
quota.paired.pilot = pilot
_v12_training_candidate_record = quota.training_candidate_record


def validate_manifest(
    manifest_path: Path,
    metadata_path: Path,
    shard_index: int,
    shard_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate the v13r3 42k target plus its expanded fail-closed reserve."""
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    declared_locks = metadata.get("runtime_dependency_locks") or {}
    dependency_checks: dict[str, bool] = {}
    for relative, digest in declared_locks.items():
        lock = quota.ROOT / relative
        hash_matches = lock.is_file() and pilot.sha256_file(lock) == digest
        contents_match = False
        if hash_matches:
            completed = subprocess.run(
                ["sha256sum", "-c", str(lock)],
                cwd=quota.ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            contents_match = completed.returncode == 0
        dependency_checks[relative] = hash_matches and contents_match
    declared = next(
        (
            row
            for row in metadata.get("shards", [])
            if int(row.get("shard_index", -1)) == shard_index
        ),
        None,
    )
    runtime_files = metadata.get("runtime_files") or {}
    checks = {
        "schema_v12_activeonly": metadata.get("schema_version")
        == "xonotic-stage2-motion-near5-combo-manifest-metadata-v12-replenish",
        "semantic_revision_v13": metadata.get("semantic_revision")
        == "v13_temporal_visibility",
        "capture_mode_active_only": metadata.get("capture_mode") == "active_only",
        "rendered_episode_rows_42000": int(
            metadata.get("rendered_episode_rows", -1)
        )
        == 42_000,
        "candidate_rows_63000": int(metadata.get("candidate_rows", -1))
        == 63_000,
        "counterfactual_qa_rows_zero": int(
            metadata.get("counterfactual_qa_rows", -1)
        )
        == 0,
        "formal_collection_authorized": metadata.get(
            "formal_collection_authorized"
        )
        is True,
        "training_admitted_false": metadata.get("training_admitted") is False,
        "source_commit": metadata.get("source_commit") == quota.SOURCE_COMMIT,
        "build_tag": metadata.get("build_tag") == quota.BUILD_TAG,
        "live_time_scale_matches_runtime": int(
            metadata.get("live_time_scale", -1)
        )
        == quota.reusable.configured_live_time_scale(),
        "shard_count": int(metadata.get("shard_count", -1)) == shard_count,
        "shard_declared": declared is not None,
        "build_lock_hash": metadata.get("build_lock_sha256")
        == pilot.sha256_file(quota.BUILD_LOCK),
        "runtime_files": bool(runtime_files)
        and all(
            (quota.ROOT / relative).is_file()
            and pilot.sha256_file(quota.ROOT / relative) == digest
            for relative, digest in runtime_files.items()
        ),
        "runtime_dependency_locks": set(declared_locks)
        == quota.REQUIRED_DEPENDENCY_LOCKS
        and all(dependency_checks.values()),
    }
    if declared is not None:
        checks.update(
            {
                "shard_path": Path(declared["path"]).name == manifest_path.name,
                "shard_hash": declared["sha256"]
                == pilot.sha256_file(manifest_path),
                "shard_candidate_rows_2250": int(declared["rows"]) == 2_250,
                "shard_target_accepted_rows_1500": int(
                    declared["target_accepted_rows"]
                )
                == 1_500,
            }
        )
    if not all(checks.values()):
        raise RuntimeError(f"v13 manifest metadata checks failed: {checks}")
    rows = quota.load_jsonl(manifest_path)
    keys = [str(row.get("sample_key", "")) for row in rows]
    families = {
        "stationary",
        "single_direction",
        "move_stop",
        "one_direction_change",
        "two_nonperiodic_changes",
        "repeated_back_and_forth",
    }
    visibility_classes = {"always_visible", "exit_hold", "exit_reacquire"}
    row_checks = {
        "rows_declared": declared is not None
        and len(rows) == int(declared["rows"]),
        "primary_rows_1500": sum(
            row.get("candidate_role") == "primary" for row in rows
        )
        == 1_500,
        "reserve_rows_750": sum(
            row.get("candidate_role") == "reserve" for row in rows
        )
        == 750,
        "row_schema_v12": all(
            row.get("schema_version")
            == "xonotic-stage2-motion-near5-combo-production-active-v12-replenish"
            for row in rows
        ),
        "semantic_revision_v13": all(
            row.get("semantic_revision") == "v13_temporal_visibility"
            for row in rows
        ),
        "capture_mode_active_only": all(
            row.get("capture_mode") == "active_only" for row in rows
        ),
        "no_frozen_scenario": all("frozen_scenario" not in row for row in rows),
        "sample_keys_present": all(keys),
        "sample_keys_unique": len(keys) == len(set(keys)),
        "assigned_shard": all(
            int(row.get("assigned_shard", -1)) == shard_index for row in rows
        ),
        "shard_count": all(
            int(row.get("shard_count", -1)) == shard_count for row in rows
        ),
        "candidate_role": all(
            row.get("candidate_role") in {"primary", "reserve"} for row in rows
        ),
        "active_authorized": all(
            row["active_scenario"].get("formal_collection_authorized") is True
            and row["active_scenario"].get("training_admitted") is False
            and row["active_scenario"].get("source_commit_required")
            == quota.SOURCE_COMMIT
            for row in rows
        ),
        "moving_trace_recertification_declared": all(
            row["active_scenario"]
            .get("prefrozen_trace_source", {})
            .get("runtime_recertification", {})
            .get("live_fail_closed")
            is True
            for row in rows
            if row["budget_token"]["player_motion_class"]
            == "certified_prefrozen_trace_replay"
        ),
        "prefrozen_seed_relation_declared": all(
            isinstance(
                row["active_scenario"]
                .get("prefrozen_trace_source", {})
                .get("source_action_seed"),
                int,
            )
            and row["active_scenario"]
            .get("prefrozen_trace_source", {})
            .get("scenario_seed_relation")
            == (
                "matches_source_action_seed"
                if row["candidate_role"] == "primary"
                else "independent_replenishment_scenario_seed"
            )
            for row in rows
            if row["budget_token"]["player_motion_class"]
            == "certified_prefrozen_trace_replay"
        ),
        "enemy_motion_basis_no_live_reads": all(
            row["active_scenario"]
            .get("enemy_motion_basis", {})
            .get("reads_camera")
            is False
            and row["active_scenario"]
            .get("enemy_motion_basis", {})
            .get("reads_live_player_state")
            is False
            for row in rows
        ),
        "postdeath_lock_required": all(
            row["active_scenario"].get("postdeath_motion_lock_required") is True
            for row in rows
        ),
        "jump_program_is_exogenous": all(
            (row["active_scenario"].get("enemy_jump_program") or {}).get(
                "reads_camera"
            )
            is False
            and (row["active_scenario"].get("enemy_jump_program") or {}).get(
                "reads_crosshair"
            )
            is False
            and (row["active_scenario"].get("enemy_jump_program") or {}).get(
                "reads_live_player_state"
            )
            is False
            for row in rows
        ),
        "temporal_family_valid": all(
            row["active_scenario"]["motion_sequence_design"]["family"]
            in families
            for row in rows
        ),
        "visibility_class_valid": all(
            row["active_scenario"]["visibility_design"]["class"]
            in visibility_classes
            and row["active_scenario"]["visibility_design"]["occlusion_allowed"]
            is False
            for row in rows
        ),
        "five_prompt_blocks_fixed_speed": all(
            len(row["active_scenario"]["enemy_motion_program"]["direction_codes"])
            == 5
            and float(
                row["active_scenario"]["enemy_motion_program"]
                ["speed_units_per_second"]
            )
            == (
                64.0
                if any(
                    row["active_scenario"]["enemy_motion_program"]
                    ["direction_codes"]
                )
                else 0.0
            )
            for row in rows
        ),
    }
    if not all(row_checks.values()):
        raise RuntimeError(f"v13 manifest row checks failed: {row_checks}")
    return rows, {
        "metadata_checks": checks,
        "runtime_dependency_checks": dependency_checks,
        "row_checks": row_checks,
        "target_accepted_rows": int(declared["target_accepted_rows"]),
        "candidate_rows": int(declared["rows"]),
    }


quota.validate_manifest = validate_manifest


def training_candidate_record(
    row: dict[str, Any], active: dict[str, Any]
) -> dict[str, Any]:
    record = _v12_training_candidate_record(row, active)
    scenario = active["scenario"]
    sequence = scenario["motion_sequence_design"]
    visibility = scenario["visibility_design"]
    record.update(
        {
            "semantic_revision": "v13_temporal_visibility",
            "motion_sequence_family": sequence["family"],
            "motion_direction_codes": sequence["direction_codes"],
            "motion_direction_labels": sequence["direction_labels"],
            "motion_direction_change_count": sequence[
                "direction_change_count"
            ],
            "visibility_class": visibility["class"],
            "visibility_qa": active["qa"]["visibility_design"],
        }
    )
    return record


quota.training_candidate_record = training_candidate_record


if __name__ == "__main__":
    raise SystemExit(quota.main())
