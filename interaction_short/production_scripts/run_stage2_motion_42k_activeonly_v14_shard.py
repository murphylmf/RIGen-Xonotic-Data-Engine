                      
"""Run one v14 category shard with the proven v12r6 quota engine."""

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

import run_stage2_motion_42k_activeonly_v13_shard as v13              


quota = v13.quota
pilot = v13.pilot
quota.pilot = pilot
quota.paired.pilot = pilot
_v13_training_candidate_record = v13.training_candidate_record
SEMANTIC_REVISION = "v14_near_exit_90_5_5_nocrosshair"
CROSSHAIR_OVERLAY = ROOT / "configs/capture_client_stage2_v14_no_crosshair.cfg"
VISIBILITY_CLASSES = {"always_visible", "exit_hold", "exit_reacquire"}


def validate_manifest(
    manifest_path: Path,
    metadata_path: Path,
    shard_index: int,
    shard_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata_root = metadata_path.parent.resolve()
    declared_category = None
    declared_shard = None
    for category, spec in (metadata.get("categories") or {}).items():
        for shard in spec.get("shards", []):
            candidate = (metadata_root / str(shard["path"])).resolve()
            if candidate == manifest_path.resolve():
                declared_category = str(category)
                declared_shard = shard
                break
        if declared_shard is not None:
            break

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

    runtime_files = metadata.get("runtime_files") or {}
    checks = {
        "schema_v12_activeonly": metadata.get("schema_version")
        == "xonotic-stage2-motion-near5-combo-manifest-metadata-v12-replenish",
        "semantic_revision_v14": metadata.get("semantic_revision")
        == SEMANTIC_REVISION,
        "semantic_schema_v14": metadata.get("semantic_schema_version")
        == "xonotic-stage2-motion-temporal-visibility-manifest-v14",
        "capture_mode_active_only": metadata.get("capture_mode") == "active_only",
        "rendered_episode_rows_42000": int(
            metadata.get("rendered_episode_rows", -1)
        )
        == 42_000,
        "candidate_rows_74200": int(metadata.get("candidate_rows", -1))
        == 74_200,
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
        "category_declared": declared_category in VISIBILITY_CLASSES,
        "shard_declared": declared_shard is not None,
        "declared_shard_index": declared_shard is not None
        and int(declared_shard.get("shard_index", -1)) == shard_index,
        "build_lock_hash": metadata.get("build_lock_sha256")
        == pilot.sha256_file(quota.BUILD_LOCK),
        "runtime_files": bool(runtime_files)
        and all(
            (quota.ROOT / relative).is_file()
            and pilot.sha256_file(quota.ROOT / relative) == digest
            for relative, digest in runtime_files.items()
        ),
        "crosshair_overlay": metadata.get("capture_client_overlay")
        == str(CROSSHAIR_OVERLAY)
        and CROSSHAIR_OVERLAY.is_file()
        and metadata.get("capture_client_overlay_sha256")
        == pilot.sha256_file(CROSSHAIR_OVERLAY),
        "runtime_dependency_locks": set(declared_locks)
        == quota.REQUIRED_DEPENDENCY_LOCKS
        and all(dependency_checks.values()),
    }
    if declared_shard is not None:
        checks.update(
            {
                "shard_hash": declared_shard["sha256"]
                == pilot.sha256_file(manifest_path),
                "shard_rows": int(declared_shard["rows"])
                == int(declared_shard["primary_rows"])
                + int(declared_shard["reserve_rows"]),
                "target_matches_primary": int(
                    declared_shard["target_accepted_rows"]
                )
                == int(declared_shard["primary_rows"]),
            }
        )
    if not all(checks.values()):
        raise RuntimeError(f"v14 manifest metadata checks failed: {checks}")

    rows = quota.load_jsonl(manifest_path)
    keys = [str(row.get("sample_key", "")) for row in rows]
    row_checks = {
        "rows_declared": len(rows) == int(declared_shard["rows"]),
        "primary_rows_declared": sum(
            row.get("candidate_role") == "primary" for row in rows
        )
        == int(declared_shard["primary_rows"]),
        "reserve_rows_declared": sum(
            row.get("candidate_role") == "reserve" for row in rows
        )
        == int(declared_shard["reserve_rows"]),
        "row_schema_v12": all(
            row.get("schema_version")
            == "xonotic-stage2-motion-near5-combo-production-active-v12-replenish"
            for row in rows
        ),
        "semantic_revision_v14": all(
            row.get("semantic_revision") == SEMANTIC_REVISION for row in rows
        ),
        "sample_keys_present": all(keys),
        "sample_keys_unique": len(keys) == len(set(keys)),
        "assigned_shard": all(
            int(row.get("assigned_shard", -1)) == shard_index for row in rows
        ),
        "shard_count": all(
            int(row.get("shard_count", -1)) == shard_count for row in rows
        ),
        "category_exact": all(
            row["active_scenario"]["visibility_design"]["class"]
            == declared_category
            for row in rows
        ),
        "no_frozen_scenario": all("frozen_scenario" not in row for row in rows),
        "active_authorized": all(
            row["active_scenario"].get("formal_collection_authorized") is True
            and row["active_scenario"].get("training_admitted") is False
            and row["active_scenario"].get("source_commit_required")
            == quota.SOURCE_COMMIT
            for row in rows
        ),
        "exit_near_pure_lateral": all(
            row["active_scenario"]["distance_tier"] in {"d1", "d2"}
            and set(
                row["active_scenario"]["enemy_motion_program"]["direction_codes"]
            )
            <= {1, 2}
            for row in rows
        )
        if declared_category in {"exit_hold", "exit_reacquire"}
        else True,
        "occlusion_rejected": all(
            row["active_scenario"]["visibility_design"]["occlusion_allowed"]
            is False
            for row in rows
        ),
        "postdeath_lock_required": all(
            row["active_scenario"].get("postdeath_motion_lock_required") is True
            for row in rows
        ),
        "five_prompt_blocks": all(
            len(
                row["active_scenario"]["enemy_motion_program"]["direction_codes"]
            )
            == 5
            for row in rows
        ),
        "exit_hold_five_same_direction_blocks": all(
            len(
                set(
                    row["active_scenario"]["enemy_motion_program"][
                        "direction_codes"
                    ]
                )
            )
            == 1
            and row["active_scenario"]["enemy_motion_program"][
                "direction_codes"
            ][0]
            in {1, 2}
            for row in rows
        )
        if declared_category == "exit_hold"
        else True,
    }
    if not all(row_checks.values()):
        raise RuntimeError(f"v14 manifest row checks failed: {row_checks}")
    return rows, {
        "metadata_checks": checks,
        "runtime_dependency_checks": dependency_checks,
        "row_checks": row_checks,
        "visibility_category": declared_category,
        "target_accepted_rows": int(declared_shard["target_accepted_rows"]),
        "candidate_rows": int(declared_shard["rows"]),
    }


quota.validate_manifest = validate_manifest


def training_candidate_record(
    row: dict[str, Any], active: dict[str, Any]
) -> dict[str, Any]:
    record = _v13_training_candidate_record(row, active)
    record["semantic_revision"] = SEMANTIC_REVISION
    record["accepted_visibility_target"] = row["active_scenario"][
        "visibility_design"
    ]["class"]
    record["crosshair_visible"] = False
    return record


quota.training_candidate_record = training_candidate_record


if __name__ == "__main__":
    raise SystemExit(quota.main())
