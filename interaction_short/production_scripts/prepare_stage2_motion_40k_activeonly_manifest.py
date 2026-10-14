                      
"""Derive the Stage-2 40k active-only v10 manifest and carryover records.

The v9 source has 40,000 rows, each containing one active scenario and one
rendered frozen QA scenario.  This migration preserves the active scenario
byte-for-byte, removes the frozen scenario from the production manifest, and
seeds a fresh output root with already accepted v9 active captures.  It never
modifies the v9 manifest or production output.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BUILD_TAG = "capture-e1b6fef45bc3-aarch64"
SOURCE_COMMIT = "e1b6fef45bc370d36b1f5e3ba04cd1de1d211403"
BUILD_LOCK = ROOT / "locks" / f"{BUILD_TAG}.sha256"
DEFAULT_SOURCE_MANIFEST = (
    ROOT
    / "manifests/stage2_motion_near5_combo_40k_v9_accel_28shard_20260817"
)
DEFAULT_OUTPUT_MANIFEST = (
    ROOT
    / "manifests/stage2_motion_near5_combo_40k_v10_activeonly_28shard_20260818"
)
DEFAULT_LEGACY_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_40k_v9_accel_28gpu_20260817_01"
)
DEFAULT_OUTPUT_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_40k_v10_activeonly_28gpu_20260818_01"
)
SHARD_COUNT = 28
PRIMARY_ROWS = 40_000


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def distribution(rows: Iterable[dict[str, Any]], key) -> dict[str, int]:
    counts = Counter(str(key(row)) for row in rows)
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def runtime_files() -> list[Path]:
    return [
        ROOT / "pilot_scripts/build_samples.py",
        ROOT / "production_scripts/run_stage2_motion_40k_shard.py",
        ROOT / "production_scripts/run_stage2_motion_40k_activeonly_shard.py",
        ROOT / "production_scripts/run_stage2_motion_40k_activeonly_multigpu.py",
        ROOT / "production_scripts/launch_dlc_7x4_activeonly_resilient.sh",
        ROOT / "scripts/xonotic_stage1_reusable.py",
    ]


def transform_manifests(
    source_root: Path,
    output_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite manifest root: {output_root}")
    source_metadata_path = source_root / "MANIFEST_METADATA.json"
    source_audit_path = source_root / "MANIFEST_AUDIT.json"
    source_metadata = json.loads(source_metadata_path.read_text(encoding="utf-8"))
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    if int(source_metadata.get("primary_rows", -1)) != PRIMARY_ROWS:
        raise RuntimeError("source primary_rows is not 40000")
    if int(source_metadata.get("counterfactual_qa_rows", -1)) != PRIMARY_ROWS:
        raise RuntimeError("source counterfactual_qa_rows is not 40000")

    source_shards = sorted((source_root / "shards-028").glob("shard-*-of-028.jsonl"))
    if len(source_shards) != SHARD_COUNT:
        raise RuntimeError(f"expected 28 source shards, found {len(source_shards)}")
    all_rows: list[dict[str, Any]] = []
    source_shard_hashes: dict[str, str] = {}
    for path in source_shards:
        source_shard_hashes[str(path.relative_to(source_root))] = sha256_file(path)
        for row in read_jsonl(path):
            if "active_scenario" not in row or "frozen_scenario" not in row:
                raise RuntimeError(f"source row is not a complete v9 pair: {path}")
            all_rows.append(row)
    if len(all_rows) != PRIMARY_ROWS:
        raise RuntimeError(f"expected 40000 source rows, found {len(all_rows)}")
    ordinals = [int(row["ordinal"]) for row in all_rows]
    if sorted(ordinals) != list(range(PRIMARY_ROWS)):
        raise RuntimeError("source ordinals are not exactly 0..39999")

    output_shards = output_root / "shards-028"
    output_shards.mkdir(parents=True)
    handles: dict[int, Any] = {}
    shard_records: list[dict[str, Any]] = []
    transformed: list[dict[str, Any]] = []
    try:
        for shard_index in range(SHARD_COUNT):
            path = output_shards / f"shard-{shard_index:03d}-of-028.jsonl"
            handles[shard_index] = path.open("w", encoding="utf-8")
        for source in sorted(all_rows, key=lambda row: int(row["ordinal"])):
            ordinal = int(source["ordinal"])
            sample_key = str(source["pair_id"])
            active = source["active_scenario"]
            row = {
                "schema_version": "xonotic-stage2-motion-near5-combo-production-active-v10",
                "capture_mode": "active_only",
                "qa_mode": "single_episode_authoritative",
                "ordinal": ordinal,
                "sample_key": sample_key,
                "assigned_shard": ordinal % SHARD_COUNT,
                "shard_count": SHARD_COUNT,
                "source_formal_episode_id": source["source_formal_episode_id"],
                "source_formal_scenario_sha256": source[
                    "source_formal_scenario_sha256"
                ],
                "budget_token": source["budget_token"],
                "requested_arm": source["requested_arm"],
                "realized_manifest_arm": source["realized_manifest_arm"],
                "arm_fallback": source["arm_fallback"],
                "active_scenario": active,
                "raw_avi_audit": bool(source["raw_avi_audit"]),
            }
            if "frozen_scenario" in row:
                raise AssertionError("active-only row unexpectedly contains frozen_scenario")
            handles[row["assigned_shard"]].write(canonical_json(row) + "\n")
            transformed.append(row)
    finally:
        for handle in handles.values():
            handle.close()

    for shard_index in range(SHARD_COUNT):
        path = output_shards / f"shard-{shard_index:03d}-of-028.jsonl"
        rows = read_jsonl(path)
        shard_records.append(
            {
                "shard_index": shard_index,
                "rows": len(rows),
                "path": str(path.relative_to(output_root)),
                "sha256": sha256_file(path),
            }
        )

    counters = {
        "intent_outcome": distribution(transformed, lambda row: row["active_scenario"]["intent_outcome"]),
        "weapon": distribution(transformed, lambda row: row["active_scenario"]["weapon"]),
        "map": distribution(transformed, lambda row: row["active_scenario"]["map"]),
        "enemy_model": distribution(transformed, lambda row: row["active_scenario"]["enemy_model"]),
        "enemy_motion": distribution(
            transformed,
            lambda row: row["active_scenario"]["formal_design"]["target_motion_name"],
        ),
        "distance_tier": distribution(transformed, lambda row: row["active_scenario"]["distance_tier"]),
        "player_motion_class": distribution(
            transformed,
            lambda row: row["active_scenario"]["formal_design"]["player_motion_class"],
        ),
    }
    checks = {
        "rows_40000": len(transformed) == PRIMARY_ROWS,
        "one_rendered_episode_per_row": len(transformed) == PRIMARY_ROWS,
        "no_frozen_scenario_field": all("frozen_scenario" not in row for row in transformed),
        "capture_mode_active_only": all(row["capture_mode"] == "active_only" for row in transformed),
        "active_authorized": all(
            row["active_scenario"].get("formal_collection_authorized") is True
            and row["active_scenario"].get("training_admitted") is False
            for row in transformed
        ),
        "sample_keys_unique": len({row["sample_key"] for row in transformed}) == PRIMARY_ROWS,
        "shards_complete": sum(row["rows"] for row in shard_records) == PRIMARY_ROWS,
        "source_distribution_preserved": counters == {
            "intent_outcome": dict(sorted(source_audit["distributions"]["outcome"].items())),
            "weapon": dict(sorted(source_audit["distributions"]["weapon"].items())),
            "map": dict(sorted(source_audit["distributions"]["map"].items())),
            "enemy_model": dict(
                sorted(
                    Counter(
                        key.split(":", 1)[0]
                        for key, count in source_audit["distributions"]["appearance"].items()
                        for _ in range(int(count))
                    ).items()
                )
            ),
            "enemy_motion": dict(sorted(source_audit["distributions"]["enemy_motion"].items())),
            "distance_tier": dict(sorted(source_audit["distributions"]["distance_tier"].items())),
            "player_motion_class": dict(sorted(source_audit["distributions"]["player_motion"].items())),
        },
    }
    audit = {
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-audit-v10-activeonly",
        "passed": all(checks.values()),
        "checks": checks,
        "primary_rows": PRIMARY_ROWS,
        "rendered_episode_rows": PRIMARY_ROWS,
        "counterfactual_qa_rows": 0,
        "source_video_seconds": PRIMARY_ROWS * 5,
        "source_video_hours": PRIMARY_ROWS * 5 / 3600.0,
        "distributions": counters,
        "source_manifest_root": str(source_root),
        "source_manifest_metadata_sha256": sha256_file(source_metadata_path),
        "source_manifest_audit_sha256": sha256_file(source_audit_path),
        "source_shard_hashes": source_shard_hashes,
        "shards": shard_records,
    }
    audit_path = output_root / "MANIFEST_AUDIT.json"
    write_json(audit_path, audit)
    files = runtime_files()
    missing_runtime = [str(path) for path in files if not path.is_file()]
    if missing_runtime:
        raise RuntimeError(f"active-only runtime files missing: {missing_runtime}")
    metadata = {
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-metadata-v10-activeonly",
        "capture_mode": "active_only",
        "qa_mode": "single_episode_authoritative",
        "formal_collection_authorized": True,
        "training_admitted": False,
        "manual_review_required": False,
        "primary_rows": PRIMARY_ROWS,
        "rendered_episode_rows": PRIMARY_ROWS,
        "active_training_hours": PRIMARY_ROWS * 5 / 3600.0,
        "counterfactual_qa_rows": 0,
        "source_commit": SOURCE_COMMIT,
        "build_tag": BUILD_TAG,
        "build_lock": str(BUILD_LOCK),
        "build_lock_sha256": sha256_file(BUILD_LOCK),
        "runtime_dependency_locks": source_metadata["runtime_dependency_locks"],
        "runtime_files": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in files
        },
        "shard_count": SHARD_COUNT,
        "shards": shard_records,
        "manifest_audit": str(audit_path.relative_to(output_root)),
        "manifest_audit_sha256": sha256_file(audit_path),
        "source_pair_manifest_root": str(source_root),
        "source_pair_manifest_metadata_sha256": sha256_file(source_metadata_path),
        "distribution_policy": {
            **source_metadata["distribution_policy"],
            "rendered_counterfactual_required": False,
            "admission_uses_pair_qa": False,
            "admission_uses_active_authoritative_qa": True,
        },
    }
    metadata_path = output_root / "MANIFEST_METADATA.json"
    write_json(metadata_path, metadata)
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(f"{sha256_file(path)}  {path.relative_to(output_root)}\n")
    if not audit["passed"]:
        raise RuntimeError(f"active-only manifest audit failed: {checks}")
    return transformed, metadata


def active_record_from_v9(
    old: dict[str, Any],
    source_record_path: Path,
    source_record_sha256: str,
) -> dict[str, Any]:
    forbidden = {
        "counterfactual_episode_id",
        "frozen_artifact_hashes",
        "pair_qa_path",
        "pair_qa_sha256",
        "pair_checks",
    }
    missing = [
        key
        for key in (
            "sample_id",
            "video_path",
            "source_video_path",
            "action_path",
            "state_path",
            "visibility_path",
            "prompt_path",
            "active_artifact_hashes",
        )
        if key not in old
    ]
    if missing:
        raise RuntimeError(f"legacy accepted record missing fields: {missing}")
    required_paths = [
        Path(old["video_path"]),
        Path(old["source_video_path"]),
        Path(old["action_path"]),
        Path(old["state_path"]),
        Path(old["visibility_path"]),
        Path(old["prompt_path"]),
    ]
    missing_paths = [str(path) for path in required_paths if not path.is_file()]
    if missing_paths:
        raise RuntimeError(f"legacy accepted active artifacts missing: {missing_paths}")
    record = {
        key: value for key, value in old.items() if key not in forbidden
    }
    record.pop("schema_version", None)
    legacy_pair_id = record.pop("pair_id", None)
    record["schema_version"] = (
        "xonotic-stage2-motion-near5-combo-captured-sample-v10-activeonly"
    )
    record["sample_key"] = str(legacy_pair_id)
    record["capture_mode"] = "active_only_carryover"
    record["qa_mode"] = "single_episode_authoritative"
    record["admission_uses_pair_qa"] = False
    record["active_artifact_hashes"] = {
        key: value
        for key, value in old["active_artifact_hashes"].items()
        if key != "pair_qa.json"
    }
    record["carryover_provenance"] = {
        "source_schema_version": old.get("schema_version"),
        "source_record_path": str(source_record_path),
        "source_record_sha256": source_record_sha256,
        "legacy_pair_id": legacy_pair_id,
        "legacy_active_capture_qa_passed": old.get("capture_qa_passed") is True,
        "legacy_pair_qa_passed": all(old.get("pair_checks", {}).values()),
    }
    if forbidden & set(record):
        raise AssertionError("active-only carryover record contains frozen/pair QA fields")
    return record


def active_record_from_episode(
    manifest_row: dict[str, Any], episode_path: Path
) -> dict[str, Any] | None:
    required_relatives = (
        "scenario.json",
        "prompt.json",
        "qa.json",
        "media/source_64hz.mkv",
        "media/review_20hz_81f.mp4",
        "telemetry/actions_requested_64hz.parquet",
        "telemetry/actions_engine_64hz.parquet",
        "telemetry/states_64hz.parquet",
        "telemetry/events_64hz.parquet",
        "telemetry/frames_64hz.parquet",
        "telemetry/visibility_64hz.parquet",
        "raw/source.dem",
        "raw/server.jsonl",
    )
    if any(not (episode_path / relative).is_file() for relative in required_relatives):
        return None
    scenario = json.loads((episode_path / "scenario.json").read_text(encoding="utf-8"))
    prompt = json.loads((episode_path / "prompt.json").read_text(encoding="utf-8"))
    qa = json.loads((episode_path / "qa.json").read_text(encoding="utf-8"))
    expected = manifest_row["active_scenario"]
    if scenario.get("episode_id") != expected.get("episode_id"):
        return None
    if qa.get("pre_pair_passed") is not True:
        return None
    if not qa.get("checks") or not all(bool(value) for value in qa["checks"].values()):
        return None
    if scenario.get("formal_collection_authorized") is not True:
        return None
    hashes = {
        relative: sha256_file(episode_path / relative)
        for relative in required_relatives
    }
    return {
        "schema_version": "xonotic-stage2-motion-near5-combo-captured-sample-v10-activeonly",
        "capture_mode": "active_only_carryover",
        "qa_mode": "single_episode_authoritative",
        "admission_uses_pair_qa": False,
        "sample_id": scenario["episode_id"],
        "sample_key": manifest_row["sample_key"],
        "ordinal": int(manifest_row["ordinal"]),
        "training_admitted": False,
        "capture_qa_passed": True,
        "video_path": str(episode_path / "media/review_20hz_81f.mp4"),
        "source_video_path": str(episode_path / "media/source_64hz.mkv"),
        "action_path": str(episode_path / "telemetry/actions_requested_64hz.parquet"),
        "state_path": str(episode_path / "telemetry/states_64hz.parquet"),
        "visibility_path": str(episode_path / "telemetry/visibility_64hz.parquet"),
        "prompt_path": str(episode_path / "prompt.json"),
        "prompt_text": prompt["prompt_text"],
        "actual_outcome": qa["interaction"]["actual_outcome"],
        "intent_outcome": scenario["intent_outcome"],
        "outcome_recipe_is_individual_admission_gate": False,
        "weapon": scenario["weapon"],
        "map": scenario["map"],
        "enemy_model": scenario["enemy_model"],
        "enemy_skin": int(scenario["enemy_skin"]),
        "enemy_color": int(scenario["enemy_color"]),
        "player_motion_class": scenario["formal_design"]["player_motion_class"],
        "enemy_motion": scenario["formal_design"]["target_motion_name"],
        "distance_tier": scenario["distance_tier"],
        "target_initial_distance_units": scenario["target_initial_distance_units"],
        "actual_initial_distance_units": qa["screen_distance"]["initial_distance_world"],
        "minimum_enemy_screen_height_pixels": qa["screen_distance"]["minimum_height_pixels"],
        "active_artifact_hashes": hashes,
        "source_formal_episode_id": manifest_row["source_formal_episode_id"],
        "carryover_provenance": {
            "source_episode_path": str(episode_path),
            "legacy_active_capture_qa_passed": True,
            "legacy_pair_qa_required_for_admission": False,
            "salvaged_without_recapture": True,
        },
    }


def seed_carryover(
    legacy_run: Path,
    output_run: Path,
    manifest_rows: list[dict[str, Any]],
    workers: int,
) -> dict[str, Any]:
    if output_run.exists():
        raise FileExistsError(f"refusing to overwrite output run: {output_run}")
    output_run.mkdir(parents=True)
    manifest_by_key = {str(row["sample_key"]): row for row in manifest_rows}
    accepted: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    duplicates = 0
    for journal_path in sorted(legacy_run.glob("shard_*/manifests/accepted.jsonl")):
        for journal in read_jsonl(journal_path):
            key = str(journal["pair_id"])
            if key in accepted:
                duplicates += 1
            accepted[key] = (journal, manifest_by_key[key])
    if duplicates:
        raise RuntimeError(f"legacy accepted journals contain {duplicates} duplicate rows")

    def prepare_legacy(
        item: tuple[str, tuple[dict[str, Any], dict[str, Any]]]
    ) -> tuple[str, int, dict[str, Any], dict[str, Any]]:
        sample_key, (journal, manifest_row) = item
        record_path = Path(journal["record_path"])
        if sha256_file(record_path) != journal["record_sha256"]:
            raise RuntimeError(f"legacy record SHA mismatch: {sample_key}")
        old = json.loads(record_path.read_text(encoding="utf-8"))
        if old.get("capture_qa_passed") is not True:
            raise RuntimeError(f"legacy record capture QA not passed: {sample_key}")
        record = active_record_from_v9(
            old, record_path, str(journal["record_sha256"])
        )
        shard_index = int(manifest_row["assigned_shard"])
        shard_root = output_run / f"shard_{shard_index:02d}"
        new_record_path = shard_root / "records" / f"{sample_key}.json"
        write_json(new_record_path, record)
        accepted_row = {
            "schema_version": "xonotic-stage2-motion-near5-combo-accepted-v10-activeonly",
            "sample_key": sample_key,
            "ordinal": int(journal["ordinal"]),
            "record_path": str(new_record_path),
            "record_sha256": sha256_file(new_record_path),
            "actual_outcome": record["actual_outcome"],
            "accepted_utc": journal["accepted_utc"],
            "acceptance_source": "v9_active_capture_carryover",
        }
        return sample_key, shard_index, record, accepted_row

    per_shard = Counter()
    outcomes = Counter()
    accepted_keys: set[str] = set()
    legacy_items = sorted(
        accepted.items(), key=lambda item: int(item[1][0]["ordinal"])
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for migrated_count, prepared in enumerate(
            executor.map(prepare_legacy, legacy_items), 1
        ):
            sample_key, shard_index, record, accepted_row = prepared
            shard_root = output_run / f"shard_{shard_index:02d}"
            journal_out = shard_root / "manifests/accepted.jsonl"
            journal_out.parent.mkdir(parents=True, exist_ok=True)
            with journal_out.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(accepted_row) + "\n")
            per_shard[shard_index] += 1
            outcomes[str(record["actual_outcome"])] += 1
            accepted_keys.add(sample_key)
            if migrated_count % 1000 == 0 or migrated_count == len(legacy_items):
                print(
                    canonical_json(
                        {
                            "event": "activeonly_carryover_progress",
                            "migrated_legacy_accepted": migrated_count,
                            "legacy_accepted_total": len(legacy_items),
                        }
                    ),
                    flush=True,
                )

        salvage_candidates = [
            row
            for row in sorted(manifest_rows, key=lambda row: int(row["ordinal"]))
            if str(row["sample_key"]) not in accepted_keys
        ]

        def prepare_salvage(
            manifest_row: dict[str, Any],
        ) -> tuple[int, dict[str, Any], dict[str, Any]] | None:
            shard_index = int(manifest_row["assigned_shard"])
            episode_id = str(manifest_row["active_scenario"]["episode_id"])
            episode_path = (
                legacy_run
                / f"shard_{shard_index:02d}"
                / "episodes"
                / episode_id
            )
            record = active_record_from_episode(manifest_row, episode_path)
            if record is None:
                return None
            sample_key = str(manifest_row["sample_key"])
            shard_root = output_run / f"shard_{shard_index:02d}"
            new_record_path = shard_root / "records" / f"{sample_key}.json"
            write_json(new_record_path, record)
            accepted_row = {
                "schema_version": "xonotic-stage2-motion-near5-combo-accepted-v10-activeonly",
                "sample_key": sample_key,
                "ordinal": int(manifest_row["ordinal"]),
                "record_path": str(new_record_path),
                "record_sha256": sha256_file(new_record_path),
                "actual_outcome": record["actual_outcome"],
                "accepted_utc": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "acceptance_source": "v9_valid_active_package_salvage",
            }
            return shard_index, record, accepted_row

        salvaged_active_packages = 0
        checked_salvage_candidates = 0
        for prepared in executor.map(prepare_salvage, salvage_candidates):
            checked_salvage_candidates += 1
            if prepared is None:
                continue
            shard_index, record, accepted_row = prepared
            shard_root = output_run / f"shard_{shard_index:02d}"
            journal_out = shard_root / "manifests/accepted.jsonl"
            journal_out.parent.mkdir(parents=True, exist_ok=True)
            with journal_out.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(accepted_row) + "\n")
            per_shard[shard_index] += 1
            outcomes[str(record["actual_outcome"])] += 1
            accepted_keys.add(str(accepted_row["sample_key"]))
            salvaged_active_packages += 1

    print(
        canonical_json(
            {
                "event": "activeonly_salvage_complete",
                "checked_candidates": checked_salvage_candidates,
                "salvaged_valid_active_packages": salvaged_active_packages,
            }
        ),
        flush=True,
    )

    summary = {
        "schema_version": "xonotic-stage2-motion-near5-combo-carryover-v10-activeonly",
        "legacy_run_root": str(legacy_run),
        "output_run_root": str(output_run),
        "legacy_accepted_active_records": len(accepted),
        "salvaged_valid_active_packages": salvaged_active_packages,
        "accepted_active_records": len(accepted_keys),
        "duplicates": duplicates,
        "per_shard": {str(key): value for key, value in sorted(per_shard.items())},
        "actual_outcome_distribution": dict(sorted(outcomes.items())),
        "old_frozen_artifacts_modified": False,
        "old_active_artifacts_modified": False,
        "new_records_contain_frozen_fields": False,
        "carryover_workers": workers,
    }
    write_json(output_run / "CARRYOVER_SUMMARY.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest-root", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--output-manifest-root", type=Path, default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument("--legacy-run-root", type=Path, default=DEFAULT_LEGACY_RUN)
    parser.add_argument("--output-run-root", type=Path, default=DEFAULT_OUTPUT_RUN)
    parser.add_argument("--carryover-only", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--carryover-workers", type=int, default=32)
    args = parser.parse_args()
    if args.carryover_only and args.manifest_only:
        parser.error("--carryover-only and --manifest-only are mutually exclusive")
    if not 1 <= args.carryover_workers <= 128:
        parser.error("--carryover-workers must be between 1 and 128")
    output_manifest_root = args.output_manifest_root.resolve()
    if args.carryover_only:
        metadata = json.loads(
            (output_manifest_root / "MANIFEST_METADATA.json").read_text(
                encoding="utf-8"
            )
        )
        rows = []
        for shard_path in sorted(
            (output_manifest_root / "shards-028").glob(
                "shard-*-of-028.jsonl"
            )
        ):
            rows.extend(read_jsonl(shard_path))
        if (
            len(rows) != PRIMARY_ROWS
            or metadata.get("capture_mode") != "active_only"
            or int(metadata.get("counterfactual_qa_rows", -1)) != 0
        ):
            raise RuntimeError("existing active-only manifest failed carryover preflight")
    else:
        rows, metadata = transform_manifests(
            args.source_manifest_root.resolve(),
            output_manifest_root,
        )
    if args.manifest_only:
        print(
            json.dumps(
                {
                    "manifest_root": str(output_manifest_root),
                    "manifest_rows": len(rows),
                    "rendered_episode_rows": metadata["rendered_episode_rows"],
                    "counterfactual_qa_rows": metadata["counterfactual_qa_rows"],
                    "carryover": "skipped_manifest_only",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    carryover = seed_carryover(
        args.legacy_run_root.resolve(),
        args.output_run_root.resolve(),
        rows,
        workers=args.carryover_workers,
    )
    print(
        json.dumps(
            {
                "manifest_root": str(args.output_manifest_root.resolve()),
                "manifest_rows": len(rows),
                "rendered_episode_rows": metadata["rendered_episode_rows"],
                "counterfactual_qa_rows": metadata["counterfactual_qa_rows"],
                "output_run_root": str(args.output_run_root.resolve()),
                "carryover": carryover,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
