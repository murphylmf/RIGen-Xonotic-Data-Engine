                      
"""Appearance-locked long60 production with robust single-pass kill timing.

V4 made the requested model/skin/color real.  That exposed a calibration that
had been hidden by the former default-model reuse: in the four-distinct
template, a 15-health target sometimes received the second 10-damage
machinegun hit in the next prompt block, or received only one hit.  V5 keeps
all schedules and distributions unchanged and gives only four-distinct actors
declared for a kill 10 health.  Exact telemetry hits, kills, moving-target
gates, corpse locking, and despawn gates remain mandatory.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V4_PATH = Path(__file__).with_name("long60_production_ref42_v4.py")
SPEC = importlib.util.spec_from_file_location("long60_production_ref42_v4_base", V4_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import ref42 v4 module: {V4_PATH}")
v4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v4
SPEC.loader.exec_module(v4)


RELEASE_ID = "stage2_long60_multi_enemy_ref42_30h_20260828_v5"
SCHEMA_VERSION = "xonotic-stage2-long60-ref42-production-manifest-v3"
EPISODE_PREFIX = "s2l60ref42_v5"
FOUR_DISTINCT_KILL_HEALTH = 10.0
BUILD_TAG = "capture-9efed7e5733b-aarch64"
BUILD_COMMIT = "9efed7e5733bf6062865044060d4be390309958a"

_v4_distribution_rows = v4.distribution_rows
_v3_actors_for_row = v4.v3.actors_for_row
_v4_build_episode_scenario = v4.build_episode_scenario
_v4_deep_appearance_audit = v4.deep_appearance_audit
_v4_prepare = v4.prepare
_v4_validate_manifest = v4.validate_manifest
_v4_run_attempt = v4.run_attempt
_v3_finalize = v4.v3.finalize

REF_RELEASE_ROOT = Path(
    "./rigen_data/reference_assets/xonotic_enemy_ref42_clean_v1"
)

                                                             
v4.RELEASE_ID = RELEASE_ID
v4.SCHEMA_VERSION = SCHEMA_VERSION
v4.EPISODE_PREFIX = EPISODE_PREFIX
v4.v3.RELEASE_ID = RELEASE_ID
v4.v3.SCHEMA_VERSION = SCHEMA_VERSION
v4.v3.prod.RELEASE_ID = RELEASE_ID
v4.v3.prod.SCHEMA_VERSION = SCHEMA_VERSION
v4.v3.prod.BUILD_TAG = BUILD_TAG
v4.v3.prod.BUILD_COMMIT = BUILD_COMMIT
v4.v3.prod.DEFAULT_MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
v4.v3.prod.DEFAULT_OUTPUT_ROOT = Path("./rigen_data") / RELEASE_ID


def distribution_rows() -> list[dict[str, Any]]:
    rows = _v4_distribution_rows()
    for index, row in enumerate(rows):
        row["schema_version"] = SCHEMA_VERSION
        row["release_id"] = RELEASE_ID
        row["episode_id"] = f"{EPISODE_PREFIX}_{index:06d}"
        row["four_distinct_kill_health"] = FOUR_DISTINCT_KILL_HEALTH
    return rows


def actors_for_row(row: dict[str, Any]) -> tuple[Any, ...]:
    actors = list(_v3_actors_for_row(row))
    if row["template"] == "four_distinct":
        kill_slots = {int(slot) for slot in row["kill_slots"]}
        actors = [
            replace(actor, health=FOUR_DISTINCT_KILL_HEALTH)
            if actor.slot in kill_slots
            else actor
            for actor in actors
        ]
    return tuple(actors)


def build_episode_scenario(
    row: dict[str, Any], manifest_root: Path, shared_actions: Path
) -> tuple[Path, Path]:
    scenario_path, timeline = _v4_build_episode_scenario(
        row, manifest_root, shared_actions
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    scenario["schema_version"] = (
        "xonotic-stage2-long60-ref42-production-scenario-v3"
    )
    scenario["release_id"] = RELEASE_ID
    scenario.setdefault("lifecycle_policy", {}).update(
        {
            "four_distinct_kill_health": FOUR_DISTINCT_KILL_HEALTH,
            "four_distinct_kill_health_scope": "declared_kill_actors_only",
            "exact_telemetry_kill_still_required": True,
        }
    )
    v4.v3.prod.write_json_atomic(scenario_path, scenario)
    return scenario_path, timeline


def deep_appearance_audit(
    manifest_root: Path, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    report = _v4_deep_appearance_audit(manifest_root, rows)
    health_ok = True
    errors = list(report.get("errors") or [])
    for row in rows:
        if row["template"] != "four_distinct":
            continue
        scenario = json.loads((ROOT / row["scenario_path"]).read_text())
        kill_actor_ids = {
            encounter["actor_id"]
            for encounter in scenario["encounters"]
            if encounter["intent_outcome"] == "kill"
        }
        for actor in scenario["actors"]:
            expected = (
                FOUR_DISTINCT_KILL_HEALTH
                if actor["actor_id"] in kill_actor_ids
                else 999.0
            )
            if abs(float(actor["health"]) - expected) > 1e-6:
                health_ok = False
                if len(errors) < 100:
                    errors.append(
                        f"{row['episode_id']}:{actor['actor_id']}:kill_health"
                    )
    report["schema_version"] = "xonotic-stage2-long60-ref42-static-validation-v3"
    report["errors"] = errors
    report["checks"]["four_distinct_kill_health_calibrated"] = health_ok
    report["four_distinct_kill_health"] = FOUR_DISTINCT_KILL_HEALTH
    report["all_pass"] = all(report["checks"].values()) and not errors
    return report


def prepare(manifest_root: Path) -> None:
    _v4_prepare(manifest_root)
    metadata_path = manifest_root.resolve() / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "release_id": RELEASE_ID,
            "four_distinct_kill_health": FOUR_DISTINCT_KILL_HEALTH,
            "four_distinct_kill_health_scope": "declared_kill_actors_only",
            "v4_capture_reuse_allowed": False,
        }
    )
    v4.v3.prod.write_json_atomic(metadata_path, metadata)
    prepared_path = manifest_root.resolve() / "PREPARED.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared.update(
        {
            "release_id": RELEASE_ID,
            "four_distinct_kill_health": FOUR_DISTINCT_KILL_HEALTH,
        }
    )
    v4.v3.prod.write_json_atomic(prepared_path, prepared)


def validate_manifest(
    manifest_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, metadata = _v4_validate_manifest(manifest_root)
    checks = {
        "release_id": metadata.get("release_id") == RELEASE_ID,
        "kill_health": (
            metadata.get("four_distinct_kill_health")
            == FOUR_DISTINCT_KILL_HEALTH
        ),
        "episode_ids": all(
            row["episode_id"] == f"{EPISODE_PREFIX}_{index:06d}"
            for index, row in enumerate(rows)
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"v5 manifest validation failed: {checks}")
    return rows, metadata


def run_attempt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    row = args[1] if len(args) >= 2 else kwargs["row"]
    output_root = args[3] if len(args) >= 4 else kwargs["output_root"]
    record = _v4_run_attempt(*args, **kwargs)
    record.update(
        {
            "four_distinct_kill_health": FOUR_DISTINCT_KILL_HEALTH,
            "four_distinct_kill_health_scope": "declared_kill_actors_only",
        }
    )
    paths = v4.v3.prod.accepted_paths(output_root, row)
    v4.v3.prod.write_json_atomic(paths["record"], record)
    v4.v3.prod.write_json_atomic(paths["accepted"], record)
    return record


def finalize(manifest_root: Path, output_root: Path) -> None:
    """Finalize only when the matching 42-appearance reference bank is ready."""
    _v3_finalize(manifest_root, output_root)
    release_path = REF_RELEASE_ROOT / "RELEASE.json"
    if not release_path.is_file():
        raise RuntimeError(f"reference release is not ready: {release_path}")
    reference_release = json.loads(release_path.read_text(encoding="utf-8"))
    reference_manifest = Path(reference_release["reference_manifest_path"])
    reference_rows = v4.v3.prod.load_jsonl(reference_manifest)
    reference_appearances = {
        row["appearance_id"] for row in reference_rows
    }
    checks = {
        "reference_ready": reference_release.get("reference_ready") is True,
        "target_release": reference_release.get("target_release_id") == RELEASE_ID,
        "appearance_count": len(reference_appearances) == 42,
        "image_count": len(reference_rows) == 210,
        "five_views_each": all(
            sum(row["appearance_id"] == appearance for row in reference_rows) == 5
            for appearance in reference_appearances
        ),
        "runtime_build": (
            Path(reference_release.get("runtime_build", "")).name == BUILD_TAG
        ),
        "runtime_commit": (
            reference_release.get("runtime_source_commit") == BUILD_COMMIT
        ),
        "manifest_hash": (
            reference_manifest.is_file()
            and v4.v3.prod.base.sha256(reference_manifest)
            == reference_release.get("reference_manifest_sha256")
        ),
        "raw_avi_absent": not any(REF_RELEASE_ROOT.rglob("*.avi")),
    }
    if not all(checks.values()):
        raise RuntimeError(f"reference release validation failed: {checks}")

    accepted_path = output_root / "accepted.jsonl"
    accepted = v4.v3.prod.load_jsonl(accepted_path)
    bound_appearances = {
        binding["appearance_id"]
        for row in accepted
        for binding in row["actor_bindings"]
    }
    if bound_appearances != reference_appearances:
        raise RuntimeError(
            "accepted/reference appearance mismatch: "
            f"accepted={len(bound_appearances)} refs={len(reference_appearances)}"
        )
    for row in accepted:
        row.update(
            {
                "ref_assets_ready": True,
                "reference_release_path": str(release_path),
                "reference_manifest_path": str(reference_manifest),
                "reference_manifest_sha256": reference_release[
                    "reference_manifest_sha256"
                ],
            }
        )
    v4.v3.prod.write_jsonl_atomic(accepted_path, accepted)
    accepted_sha256 = v4.v3.prod.base.sha256(accepted_path)
    binding_report = {
        "schema_version": "xonotic-current-enemy-ref-release-binding-v1",
        "created_utc": v4.v3.prod.utc_now(),
        "release_id": RELEASE_ID,
        "ready": True,
        "checks": checks,
        "accepted_count": len(accepted),
        "appearance_count": len(reference_appearances),
        "reference_image_count": len(reference_rows),
        "reference_release_path": str(release_path),
        "reference_manifest_path": str(reference_manifest),
        "reference_manifest_sha256": reference_release[
            "reference_manifest_sha256"
        ],
        "training_admitted": False,
    }
    v4.v3.prod.write_json_atomic(
        output_root / "REFERENCE_CONDITIONING_READY.json", binding_report
    )
    for name in ("COLLECTION_STATUS.json", "COLLECTION_COMPLETE.json"):
        path = output_root / name
        report = json.loads(path.read_text(encoding="utf-8"))
        report.update(
            {
                "accepted_manifest_sha256": accepted_sha256,
                "ref_assets_ready": True,
                "reference_release_path": str(release_path),
                "reference_manifest_path": str(reference_manifest),
                "reference_manifest_sha256": reference_release[
                    "reference_manifest_sha256"
                ],
            }
        )
        v4.v3.prod.write_json_atomic(path, report)


v4.v3.deep_appearance_audit = deep_appearance_audit
v4.v3.prod.distribution_rows = distribution_rows
v4.v3.prod.actors_for_row = actors_for_row
v4.v3.prod.build_episode_scenario = build_episode_scenario
v4.v3.prod.prepare = prepare
v4.v3.prod.validate_manifest = validate_manifest
v4.v3.prod.run_attempt = run_attempt
v4.v3.prod.finalize = finalize


def main() -> int:
    return v4.v3.prod.main()


if __name__ == "__main__":
    raise SystemExit(main())
