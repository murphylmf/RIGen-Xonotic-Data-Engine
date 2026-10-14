                      
"""Prepare the isolated Stage-2 v11 base-repair plus jump extension cohort."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BUILD_TAG = "capture-ee4c0aac65db-aarch64"
SOURCE_COMMIT = "ee4c0aac65dbac689904b320c7db4e43dfd93d20"
BUILD_LOCK = ROOT / "locks" / f"{BUILD_TAG}.sha256"
SOURCE_MANIFEST = (
    ROOT
    / "manifests/stage2_motion_near5_combo_40k_v10_activeonly_28shard_20260818_r1"
)
SOURCE_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_40k_v10_activeonly_28gpu_20260818_01"
)
POSTDEATH_AUDIT = ROOT / "audits/postdeath_motion_v10_stop_20260818_r2"
OUTPUT_MANIFEST = (
    ROOT
    / "manifests/stage2_motion_near5_combo_42k_v11_deathjump_28shard_20260818_r1"
)
OUTPUT_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_42k_v11_deathjump_28gpu_20260818_01"
)
SHARD_COUNT = 28
BASE_ROWS = 40_000
JUMP_ROWS = 2_000
TOTAL_ROWS = BASE_ROWS + JUMP_ROWS
JUMP_HEIGHT_UNITS = 40.0
JUMP_DURATION_TICKS = 40
JUMP_START_TICK_IN_BLOCK = 5
JUMP_PATTERNS = (
    (True, False, False, False, False),
    (False, True, False, False, False),
    (False, False, True, False, False),
    (False, False, False, True, False),
    (False, False, False, False, True),
    (True, False, True, False, False),
    (False, True, False, True, False),
    (False, False, True, False, True),
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def distribution(rows: Iterable[dict[str, Any]], key) -> dict[str, int]:
    return dict(sorted(Counter(str(key(row)) for row in rows).items()))


def load_source_rows(source_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((source_root / "shards-028").glob("shard-*-of-028.jsonl")):
        rows.extend(read_jsonl(path))
    rows.sort(key=lambda row: int(row["ordinal"]))
    if len(rows) != BASE_ROWS:
        raise RuntimeError(f"expected {BASE_ROWS} source rows, found {len(rows)}")
    if [int(row["ordinal"]) for row in rows] != list(range(BASE_ROWS)):
        raise RuntimeError("source ordinals are not exactly 0..39999")
    return rows


def upgrade_scenario(
    source: dict[str, Any], *, jump_pattern: tuple[bool, ...] | None
) -> dict[str, Any]:
    scenario = copy.deepcopy(source)
    authorization = scenario["formal_authorization_basis"]
    authorization.update(
        {
            "runtime_build_tag": BUILD_TAG,
            "runtime_source_commit": SOURCE_COMMIT,
            "runtime_lock": str(BUILD_LOCK),
            "runtime_lock_sha256": sha256_file(BUILD_LOCK),
            "v11_change_authorization": "explicit_user_request_2026-08-18",
            "v11_change_scope": [
                "freeze_enemy_world_motion_after_authoritative_death",
                "optional_manifest_frozen_enemy_jump_arc",
            ],
        }
    )
    scenario["source_commit_required"] = SOURCE_COMMIT
    if "prefrozen_trace_source" in scenario:
        scenario["prefrozen_trace_source"]["source_commit"] = SOURCE_COMMIT
        scenario["prefrozen_trace_source"]["runtime_recertification"][
            "runtime_source_commit"
        ] = SOURCE_COMMIT
        scenario["prefrozen_trace_runtime_recertification"][
            "runtime_source_commit"
        ] = SOURCE_COMMIT
    scenario["schema_version"] = "xonotic-stage2-motion-interaction-scenario-v11-deathjump"
    scenario["candidate_kind"] = "stage2_motion_near5_combo_formal_v11_deathjump"
    scenario["dataset_role"] = "causal_interaction_enemy_motion_near5_combo_v11"
    scenario["postdeath_motion_lock_required"] = True
    scenario["postdeath_motion_lock_policy"] = {
        "schema_version": "xonotic-stage2-postdeath-motion-lock-policy-v1",
        "trigger": "authoritative_enemy_health_below_one",
        "world_position_tolerance_units": 0.10,
        "world_speed_tolerance_units_per_second": 0.10,
        "qa_window": "death_tick_through_output_end",
    }
    enabled = jump_pattern is not None
    pattern = list(jump_pattern or (False,) * 5)
    scenario["enemy_jump_program"] = {
        "schema_version": "xonotic-stage2-enemy-jump-program-v1",
        "enabled": enabled,
        "jump_blocks": pattern,
        "height_units": JUMP_HEIGHT_UNITS if enabled else 0.0,
        "duration_ticks": JUMP_DURATION_TICKS,
        "start_tick_in_block": JUMP_START_TICK_IN_BLOCK,
        "trajectory": "manifest_frozen_symmetric_parabolic_arc",
        "horizontal_motion_remains_independent": True,
        "reads_camera": False,
        "reads_crosshair": False,
        "reads_live_player_state": False,
    }
    scenario["enemy_policy"]["jumps"] = enabled
    scenario["enemy_policy"]["schema_version"] = (
        "xonotic-stage2-enemy-policy-v5-deathjump"
    )
    scenario["formal_design"]["enemy_jumps"] = enabled
    scenario["formal_design"]["jump_blocks"] = pattern
    return scenario


def jump_source_order(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [
        row
        for row in rows
        if row["active_scenario"]["intent_outcome"] != "kill"
    ]
    return sorted(
        eligible,
        key=lambda row: hashlib.sha256(
            ("stage2-v11-jump-selection:" + str(row["sample_key"])).encode()
        ).hexdigest(),
    )[:JUMP_ROWS]


def build_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        row = copy.deepcopy(source)
        row["schema_version"] = (
            "xonotic-stage2-motion-near5-combo-production-active-v11-deathjump"
        )
        row["active_scenario"] = upgrade_scenario(
            source["active_scenario"], jump_pattern=None
        )
        row["assigned_shard"] = int(row["ordinal"]) % SHARD_COUNT
        row["shard_count"] = SHARD_COUNT
        rows.append(row)

    for jump_index, source in enumerate(jump_source_order(source_rows)):
        ordinal = BASE_ROWS + jump_index
        sample_key = f"s2mn5c42v11j_g{jump_index:06d}"
        pattern = JUMP_PATTERNS[jump_index % len(JUMP_PATTERNS)]
        scenario = upgrade_scenario(
            source["active_scenario"], jump_pattern=pattern
        )
        scenario["episode_id"] = f"s2mn5c42v11j_{jump_index:06d}_active"
        scenario["anchor_id"] = sample_key
        scenario["counterfactual_group_id"] = sample_key
        scenario["candidate_kind"] = "stage2_motion_near5_jump_extension_v11"
        scenario["dataset_role"] = "causal_interaction_enemy_jump_extension_v11"
        scenario["extension_source_sample_key"] = str(source["sample_key"])
        scenario["extension_source_scenario_sha256"] = hashlib.sha256(
            canonical_json(source["active_scenario"]).encode()
        ).hexdigest()
        scenario["formal_design"]["cohort"] = "s2mn5c42v11j"
        scenario["formal_design"]["cohort_role"] = "jump_extension"
        scenario["formal_design"]["ordinal"] = ordinal
        scenario["target_ordinal"] = ordinal
        scenario["human_review_required_before_training"] = False
        budget = copy.deepcopy(source["budget_token"])
        budget.update(
            {
                "cohort": "s2mn5c42v11j",
                "cohort_role": "jump_extension",
                "enemy_jumps": True,
                "jump_pattern": list(pattern),
            }
        )
        rows.append(
            {
                "schema_version": "xonotic-stage2-motion-near5-combo-production-active-v11-deathjump",
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
                "budget_token": budget,
                "requested_arm": source["requested_arm"],
                "realized_manifest_arm": source["realized_manifest_arm"],
                "arm_fallback": source["arm_fallback"],
                "active_scenario": scenario,
                "raw_avi_audit": bool(source["raw_avi_audit"]),
            }
        )
    rows.sort(key=lambda row: int(row["ordinal"]))
    if len(rows) != TOTAL_ROWS:
        raise AssertionError("v11 row count mismatch")
    return rows


def idle_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        scenario = row["active_scenario"]
        horizontal_stationary = not any(
            int(value)
            for value in scenario["enemy_motion_program"]["direction_codes"]
        )
        enemy_behavior_idle = horizontal_stationary and not bool(
            scenario["enemy_jump_program"]["enabled"]
        )
        player_locomotion_idle = (
            scenario["formal_design"]["player_motion_class"]
            == "certified_stationary_preflight_pair"
        )
        if enemy_behavior_idle:
            counts["enemy_idle"] += 1
        if player_locomotion_idle:
            counts["player_locomotion_idle"] += 1
        if enemy_behavior_idle and player_locomotion_idle:
            counts["both_locomotion_idle"] += 1
        if enemy_behavior_idle and not player_locomotion_idle:
            counts["enemy_idle_player_moving"] += 1
        if player_locomotion_idle and not enemy_behavior_idle:
            counts["player_idle_enemy_active"] += 1
        if not enemy_behavior_idle and not player_locomotion_idle:
            counts["both_active"] += 1
    return dict(sorted(counts.items()))


def runtime_files() -> list[Path]:
    return [
        ROOT / "pilot_scripts/build_samples_v11.py",
        ROOT / "production_scripts/run_stage2_motion_40k_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v11_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v11_multigpu.py",
        ROOT / "production_scripts/launch_dlc_7x4_activeonly_v11_resilient.sh",
        ROOT / "scripts/xonotic_stage1_reusable.py",
    ]


def write_manifest(rows: list[dict[str, Any]], output_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite manifest root: {output_root}")
    shard_root = output_root / "shards-028"
    shard_root.mkdir(parents=True)
    shards = []
    for shard_index in range(SHARD_COUNT):
        selected = [row for row in rows if int(row["assigned_shard"]) == shard_index]
        path = shard_root / f"shard-{shard_index:03d}-of-028.jsonl"
        path.write_text(
            "".join(canonical_json(row) + "\n" for row in selected),
            encoding="utf-8",
        )
        shards.append(
            {
                "shard_index": shard_index,
                "rows": len(selected),
                "path": str(path.relative_to(output_root)),
                "sha256": sha256_file(path),
            }
        )
    jump_rows = [
        row
        for row in rows
        if row["active_scenario"]["enemy_jump_program"]["enabled"]
    ]
    audit = {
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-audit-v11-deathjump",
        "passed": True,
        "primary_rows": len(rows),
        "base_rows": BASE_ROWS,
        "jump_extension_rows": len(jump_rows),
        "rendered_episode_rows": len(rows),
        "counterfactual_qa_rows": 0,
        "source_video_seconds": len(rows) * 5,
        "source_video_hours": len(rows) * 5 / 3600.0,
        "idle_semantics": {
            "enemy_idle": "no horizontal motion and no jump",
            "player_locomotion_idle": "certified stationary player position; camera aim or firing may still occur",
            "both_locomotion_idle": "enemy idle and player locomotion idle; not necessarily zero camera/fire input",
        },
        "idle_distribution": idle_distribution(rows),
        "distributions": {
            "intent_outcome": distribution(rows, lambda row: row["active_scenario"]["intent_outcome"]),
            "weapon": distribution(rows, lambda row: row["active_scenario"]["weapon"]),
            "map": distribution(rows, lambda row: row["active_scenario"]["map"]),
            "enemy_model": distribution(rows, lambda row: row["active_scenario"]["enemy_model"]),
            "enemy_motion": distribution(rows, lambda row: row["active_scenario"]["formal_design"]["target_motion_name"]),
            "distance_tier": distribution(rows, lambda row: row["active_scenario"]["distance_tier"]),
            "player_motion_class": distribution(rows, lambda row: row["active_scenario"]["formal_design"]["player_motion_class"]),
            "enemy_jumps": distribution(rows, lambda row: row["active_scenario"]["enemy_jump_program"]["enabled"]),
            "jump_pattern": distribution(jump_rows, lambda row: row["active_scenario"]["enemy_jump_program"]["jump_blocks"]),
        },
        "checks": {
            "rows_42000": len(rows) == TOTAL_ROWS,
            "base_rows_40000": len(rows) - len(jump_rows) == BASE_ROWS,
            "jump_rows_2000": len(jump_rows) == JUMP_ROWS,
            "ordinals_complete": [int(row["ordinal"]) for row in rows] == list(range(TOTAL_ROWS)),
            "sample_keys_unique": len({row["sample_key"] for row in rows}) == TOTAL_ROWS,
            "all_postdeath_lock_required": all(row["active_scenario"]["postdeath_motion_lock_required"] for row in rows),
            "no_frozen_scenario": all("frozen_scenario" not in row for row in rows),
            "jump_rows_exclude_kill_intent": all(row["active_scenario"]["intent_outcome"] != "kill" for row in jump_rows),
            "shards_exactly_1500": all(shard["rows"] == 1500 for shard in shards),
        },
        "shards": shards,
    }
    audit["passed"] = all(audit["checks"].values())
    audit_path = output_root / "MANIFEST_AUDIT.json"
    write_json(audit_path, audit)
    files = runtime_files()
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing v11 runtime files: {missing}")
    metadata = {
        "schema_version": "xonotic-stage2-motion-near5-combo-manifest-metadata-v11-deathjump",
        "capture_mode": "active_only",
        "qa_mode": "single_episode_authoritative",
        "formal_collection_authorized": True,
        "training_admitted": False,
        "manual_review_required": False,
        "primary_rows": len(rows),
        "rendered_episode_rows": len(rows),
        "active_training_hours": len(rows) * 5 / 3600.0,
        "counterfactual_qa_rows": 0,
        "base_rows": BASE_ROWS,
        "jump_extension_rows": JUMP_ROWS,
        "source_commit": SOURCE_COMMIT,
        "build_tag": BUILD_TAG,
        "build_lock": str(BUILD_LOCK),
        "build_lock_sha256": sha256_file(BUILD_LOCK),
        "runtime_dependency_locks": json.loads(
            (SOURCE_MANIFEST / "MANIFEST_METADATA.json").read_text(encoding="utf-8")
        )["runtime_dependency_locks"],
        "runtime_files": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in files
        },
        "shard_count": SHARD_COUNT,
        "shards": shards,
        "manifest_audit": str(audit_path.relative_to(output_root)),
        "manifest_audit_sha256": sha256_file(audit_path),
        "source_manifest_root": str(SOURCE_MANIFEST),
        "source_manifest_metadata_sha256": sha256_file(SOURCE_MANIFEST / "MANIFEST_METADATA.json"),
        "postdeath_defect_audit": str(POSTDEATH_AUDIT / "SUMMARY.json"),
        "postdeath_defect_audit_sha256": sha256_file(POSTDEATH_AUDIT / "SUMMARY.json"),
    }
    write_json(output_root / "MANIFEST_METADATA.json", metadata)
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(f"{sha256_file(path)}  {path.relative_to(output_root)}\n")
    if not audit["passed"]:
        raise RuntimeError(f"v11 manifest audit failed: {audit['checks']}")
    return metadata


def seed_carryover(
    rows: list[dict[str, Any]], source_run: Path, output_run: Path
) -> dict[str, Any]:
    if output_run.exists():
        raise FileExistsError(f"refusing to overwrite output run: {output_run}")
    output_run.mkdir(parents=True)
    row_by_key = {str(row["sample_key"]): row for row in rows[:BASE_ROWS]}
    defect_keys = set(
        (POSTDEATH_AUDIT / "affected_sample_keys.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    kill_audit = {
        row["sample_key"]: row
        for row in read_jsonl(POSTDEATH_AUDIT / "kill_cases.jsonl")
    }
    accepted: dict[str, dict[str, Any]] = {}
    for journal_path in sorted(source_run.glob("shard_*/manifests/accepted.jsonl")):
        for journal in read_jsonl(journal_path):
            accepted[str(journal["sample_key"])] = journal
    carried = Counter()
    excluded = Counter()
    for sample_key, journal in sorted(
        accepted.items(), key=lambda item: int(item[1]["ordinal"])
    ):
        if sample_key in defect_keys:
            excluded[str(journal["actual_outcome"])] += 1
            continue
        manifest_row = row_by_key[sample_key]
        old_record_path = Path(journal["record_path"])
        if sha256_file(old_record_path) != journal["record_sha256"]:
            raise RuntimeError(f"source record hash mismatch: {sample_key}")
        record = json.loads(old_record_path.read_text(encoding="utf-8"))
        if record.get("capture_qa_passed") is not True:
            raise RuntimeError(f"source capture QA not passed: {sample_key}")
        if record["actual_outcome"] == "kill":
            audit = kill_audit[sample_key]
            if audit["status"] != "postdeath_locked":
                raise RuntimeError(f"nondefective kill did not pass lock audit: {sample_key}")
            postdeath = audit
        else:
            postdeath = {
                "sample_key": sample_key,
                "applicable": False,
                "status": "no_enemy_death_in_accepted_episode",
                "affected": False,
            }
        record["schema_version"] = (
            "xonotic-stage2-motion-near5-combo-captured-sample-v11-deathjump"
        )
        record["capture_mode"] = "active_only_v11_compatible_carryover"
        record["enemy_jumps"] = False
        record["enemy_jump_program"] = manifest_row["active_scenario"][
            "enemy_jump_program"
        ]
        record["postdeath_motion_lock_required"] = True
        record["postdeath_motion_audit"] = postdeath
        record["v11_carryover_provenance"] = {
            "source_record_path": str(old_record_path),
            "source_record_sha256": journal["record_sha256"],
            "source_acceptance_source": journal.get("acceptance_source"),
            "compatibility_basis": (
                "v11 changes only postdeath behavior and opt-in jumps; this episode "
                "has no defective postdeath motion and has jumps disabled"
            ),
        }
        shard_index = int(manifest_row["assigned_shard"])
        shard_root = output_run / f"shard_{shard_index:02d}"
        record_path = shard_root / "records" / f"{sample_key}.json"
        write_json(record_path, record)
        out = {
            "schema_version": "xonotic-stage2-motion-near5-combo-accepted-v11-deathjump",
            "sample_key": sample_key,
            "ordinal": int(manifest_row["ordinal"]),
            "record_path": str(record_path),
            "record_sha256": sha256_file(record_path),
            "actual_outcome": record["actual_outcome"],
            "accepted_utc": journal["accepted_utc"],
            "acceptance_source": "v10_nondefective_compatible_carryover",
        }
        journal_path = shard_root / "manifests/accepted.jsonl"
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        with journal_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(out) + "\n")
        carried[str(record["actual_outcome"])] += 1
    summary = {
        "schema_version": "xonotic-stage2-motion-near5-combo-carryover-v11-deathjump",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_run_root": str(source_run),
        "output_run_root": str(output_run),
        "source_accepted_records": len(accepted),
        "carried_nondefective_records": sum(carried.values()),
        "excluded_defective_records_for_recapture": sum(excluded.values()),
        "defect_key_count": len(defect_keys),
        "carried_actual_outcome_distribution": dict(sorted(carried.items())),
        "excluded_actual_outcome_distribution": dict(sorted(excluded.items())),
        "jump_extension_records_carried": 0,
        "old_artifacts_modified": False,
    }
    write_json(output_run / "CARRYOVER_SUMMARY.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest-root", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--source-run-root", type=Path, default=SOURCE_RUN)
    parser.add_argument("--output-manifest-root", type=Path, default=OUTPUT_MANIFEST)
    parser.add_argument("--output-run-root", type=Path, default=OUTPUT_RUN)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    if not BUILD_LOCK.is_file():
        raise RuntimeError(f"v11 build lock missing: {BUILD_LOCK}")
    source_rows = load_source_rows(args.source_manifest_root.resolve())
    rows = build_rows(source_rows)
    metadata = write_manifest(rows, args.output_manifest_root.resolve())
    carryover = None
    if not args.manifest_only:
        carryover = seed_carryover(
            rows, args.source_run_root.resolve(), args.output_run_root.resolve()
        )
    print(
        json.dumps(
            {
                "manifest_root": str(args.output_manifest_root.resolve()),
                "manifest_rows": len(rows),
                "jump_extension_rows": JUMP_ROWS,
                "training_hours": metadata["active_training_hours"],
                "output_run_root": (
                    None if args.manifest_only else str(args.output_run_root.resolve())
                ),
                "carryover": carryover,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
