                      
"""Prepare the isolated Stage-2 v12 exact-quota replenishment release."""

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
    / "manifests/stage2_motion_near5_combo_42k_v11_deathjump_28shard_20260818_r1"
)
SOURCE_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_42k_v11_deathjump_28gpu_20260818_01"
)
OUTPUT_MANIFEST = (
    ROOT
    / "manifests/stage2_motion_near5_combo_42k_v12_replenish_28shard_20260818_r1"
)
OUTPUT_RUN = (
    ROOT
    / "production_runs/stage2_motion_near5_combo_42k_v12_replenish_28gpu_20260818_01"
)
SHARD_COUNT = 28
TARGET_ROWS_PER_SHARD = 1_500
RESERVE_ROWS_PER_SHARD = 375
PRIMARY_ROWS = SHARD_COUNT * TARGET_ROWS_PER_SHARD
RESERVE_ROWS = SHARD_COUNT * RESERVE_ROWS_PER_SHARD
CANDIDATE_ROWS = PRIMARY_ROWS + RESERVE_ROWS
JUMP_ROWS = 2_000
INVERSE_MOTION_CODE = {
    0: 0,
    1: 2,
    2: 1,
    3: 4,
    4: 3,
    5: 8,
    8: 5,
    6: 7,
    7: 6,
}
_PREFROZEN_ACTION_SEED_CACHE: dict[str, int] = {}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prefrozen_action_seed(scenario: dict[str, Any]) -> int | None:
    source = scenario.get("prefrozen_trace_source") or {}
    relative = str(source.get("actions_path", ""))
    if not relative:
        return None
    cached = _PREFROZEN_ACTION_SEED_CACHE.get(relative)
    if cached is not None:
        return cached
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(
            f"prefrozen actions path escapes capture root: {relative}"
        ) from exc
    if not path.is_file() or sha256_file(path) != source.get("actions_sha256"):
        raise RuntimeError(f"prefrozen actions lock mismatch: {relative}")
    first = path.read_text(encoding="utf-8").splitlines()[0]
    if not first.startswith("#seed,"):
        raise RuntimeError(f"prefrozen actions seed header missing: {relative}")
    seed = int(first.split(",", 1)[1])
    _PREFROZEN_ACTION_SEED_CACHE[relative] = seed
    return seed


def distribution(rows: Iterable[dict[str, Any]], key) -> dict[str, int]:
    return dict(sorted(Counter(str(key(row)) for row in rows).items()))


def load_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "shards-028").glob("shard-*-of-028.jsonl")):
        rows.extend(read_jsonl(path))
    rows.sort(key=lambda row: int(row["ordinal"]))
    return rows


def load_source_rows(source_root: Path) -> list[dict[str, Any]]:
    rows = load_rows(source_root)
    if len(rows) != PRIMARY_ROWS:
        raise RuntimeError(
            f"expected {PRIMARY_ROWS} v11 source rows, found {len(rows)}"
        )
    if [int(row["ordinal"]) for row in rows] != list(range(PRIMARY_ROWS)):
        raise RuntimeError("v11 source ordinals are not exactly 0..41999")
    return rows


def upgrade_scenario(source: dict[str, Any]) -> dict[str, Any]:
    scenario = copy.deepcopy(source)
    source_action_seed = prefrozen_action_seed(scenario)
    if source_action_seed is not None:
        if int(scenario["seed"]) != source_action_seed:
            raise RuntimeError(
                "primary prefrozen scenario seed does not match its locked "
                f"trace: episode={scenario['episode_id']}"
            )
        scenario["prefrozen_trace_source"][
            "source_action_seed"
        ] = source_action_seed
        scenario["prefrozen_trace_source"][
            "scenario_seed_relation"
        ] = "matches_source_action_seed"
    authorization = scenario["formal_authorization_basis"]
    authorization.update(
        {
            "runtime_build_tag": BUILD_TAG,
            "runtime_source_commit": SOURCE_COMMIT,
            "runtime_lock": str(BUILD_LOCK),
            "runtime_lock_sha256": sha256_file(BUILD_LOCK),
            "v12_change_authorization": "explicit_user_request_2026-08-18",
            "v12_change_scope": [
                "infrastructure_only_resident_warmup",
                "postdeath_velocity_audit_begins_after_death_tick",
                "exact_accepted_quota_with_manifest_reserve_candidates",
                "validated_live_time_scale_two",
                "explicit_prefrozen_source_and_scenario_seed_relation",
                "render_episode_seed_verified_at_reset_marker",
                "render_rng_seed_projected_to_exact_low24_cvar_domain",
            ],
        }
    )
    scenario["schema_version"] = (
        "xonotic-stage2-motion-interaction-scenario-v12-replenish"
    )
    scenario["candidate_kind"] = (
        "stage2_motion_near5_combo_formal_v12_replenish"
    )
    scenario["postdeath_motion_lock_policy"]["qa_window"] = (
        "death_tick_position_and_subsequent_tick_velocity_through_output_end"
    )
    return scenario


def appearance_pool(rows: list[dict[str, Any]]) -> list[tuple[str, int, int, str]]:
    return sorted(
        {
            (
                str(row["active_scenario"]["enemy_model"]),
                int(row["active_scenario"]["enemy_skin"]),
                int(row["active_scenario"]["enemy_color"]),
                str(row["active_scenario"]["appearance_id"]),
            )
            for row in rows
        }
    )


def primary_row(source: dict[str, Any]) -> dict[str, Any]:
    row = copy.deepcopy(source)
    row["schema_version"] = (
        "xonotic-stage2-motion-near5-combo-production-active-v12-replenish"
    )
    row["candidate_role"] = "primary"
    row["active_scenario"] = upgrade_scenario(source["active_scenario"])
    row["assigned_shard"] = int(source["assigned_shard"])
    row["shard_count"] = SHARD_COUNT
    return row


def reserve_row(
    source: dict[str, Any],
    *,
    reserve_index: int,
    appearances: list[tuple[str, int, int, str]],
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    ordinal = PRIMARY_ROWS + reserve_index
    sample_key = f"s2mn5c42v12r_g{reserve_index:06d}"
    scenario = row["active_scenario"]
    old_key = str(source["sample_key"])
    old_codes = [
        int(value)
        for value in scenario["enemy_motion_program"]["direction_codes"]
    ]
    new_codes = [INVERSE_MOTION_CODE[value] for value in old_codes]
    meanings = scenario["enemy_motion_program"]["code_meanings"]
    new_motion_name = str(meanings[str(new_codes[0])])

    scenario["episode_id"] = f"s2mn5c42v12r_{reserve_index:06d}_active"
    scenario["anchor_id"] = sample_key
    scenario["counterfactual_group_id"] = sample_key
    scenario["candidate_kind"] = "stage2_motion_near5_replenishment_reserve_v12"
    scenario["dataset_role"] = "causal_interaction_replenishment_reserve_v12"
    scenario["target_ordinal"] = ordinal
    scenario["seed"] = int(scenario["seed"]) + 20_000_000 + reserve_index
    scenario["enemy_policy"]["policy_seed"] = int(scenario["seed"]) + 1_000_000
    if scenario.get("prefrozen_trace_source"):
        scenario["prefrozen_trace_source"][
            "scenario_seed_relation"
        ] = "independent_replenishment_scenario_seed"
    scenario["enemy_motion_program"]["direction_codes"] = new_codes
    scenario["enemy_motion_program"]["primary_motion"] = new_motion_name
    scenario["formal_design"]["target_motion_name"] = new_motion_name
    scenario["formal_design"]["cohort"] = "s2mn5c42v12r"
    scenario["formal_design"]["cohort_role"] = "replenishment_reserve"
    scenario["formal_design"]["ordinal"] = ordinal
    scenario["formal_design"]["operational_reserve"] = True
    scenario["policy_labels"]["target_motion_name"] = new_motion_name

    model, skin, color, appearance_id = appearances[
        (reserve_index + int(source["ordinal"]) + 1) % len(appearances)
    ]
    scenario["enemy_model"] = model
    scenario["enemy_skin"] = skin
    scenario["enemy_color"] = color
    scenario["appearance_id"] = appearance_id
    scenario["reserve_transform"] = {
        "schema_version": "xonotic-stage2-replenishment-transform-v1",
        "source_sample_key": old_key,
        "source_scenario_sha256": hashlib.sha256(
            canonical_json(source["active_scenario"]).encode()
        ).hexdigest(),
        "motion_transform": "fixed_inverse_relative_direction_codes",
        "old_direction_codes": old_codes,
        "new_direction_codes": new_codes,
        "appearance_transform": "rotate_among_manifest_valid_appearances",
        "camera_and_player_action_program_unchanged": True,
        "reads_camera": False,
        "reads_live_player_state": False,
    }
    budget = copy.deepcopy(row["budget_token"])
    budget.update(
        {
            "cohort": "s2mn5c42v12r",
            "cohort_role": "replenishment_reserve",
            "source_sample_key": old_key,
        }
    )
    row.update(
        {
            "schema_version": (
                "xonotic-stage2-motion-near5-combo-production-active-v12-replenish"
            ),
            "candidate_role": "reserve",
            "ordinal": ordinal,
            "sample_key": sample_key,
            "budget_token": budget,
            "active_scenario": scenario,
            "reserve_source_sample_key": old_key,
            "reserve_source_ordinal": int(source["ordinal"]),
            "assigned_shard": int(source["assigned_shard"]),
            "shard_count": SHARD_COUNT,
        }
    )
    return row


def build_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [primary_row(row) for row in source_rows]
    appearances = appearance_pool(primary)
    reserve: list[dict[str, Any]] = []
    reserve_index = 0
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row for row in primary if int(row["assigned_shard"]) == shard_index
        ]
        selected = sorted(
            shard_rows,
            key=lambda row: hashlib.sha256(
                ("stage2-v12-reserve:" + str(row["sample_key"])).encode()
            ).hexdigest(),
        )[:RESERVE_ROWS_PER_SHARD]
        if len(selected) != RESERVE_ROWS_PER_SHARD:
            raise AssertionError(f"reserve source shortage in shard {shard_index}")
        for source in selected:
            reserve.append(
                reserve_row(
                    source,
                    reserve_index=reserve_index,
                    appearances=appearances,
                )
            )
            reserve_index += 1
    rows = primary + reserve
    rows.sort(key=lambda row: int(row["ordinal"]))
    if len(rows) != CANDIDATE_ROWS:
        raise AssertionError("v12 candidate row count mismatch")
    return rows


def idle_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        scenario = row["active_scenario"]
        enemy_idle = not any(
            int(value)
            for value in scenario["enemy_motion_program"]["direction_codes"]
        ) and not bool(scenario["enemy_jump_program"]["enabled"])
        player_idle = (
            scenario["formal_design"]["player_motion_class"]
            == "certified_stationary_preflight_pair"
        )
        if enemy_idle:
            counts["enemy_idle"] += 1
        if player_idle:
            counts["player_locomotion_idle"] += 1
        if enemy_idle and player_idle:
            counts["both_locomotion_idle"] += 1
        if enemy_idle and not player_idle:
            counts["enemy_idle_player_moving"] += 1
        if player_idle and not enemy_idle:
            counts["player_idle_enemy_active"] += 1
        if not enemy_idle and not player_idle:
            counts["both_active"] += 1
    return dict(sorted(counts.items()))


def runtime_files() -> list[Path]:
    return [
        ROOT / "pilot_scripts/build_samples.py",
        ROOT / "pilot_scripts/build_samples_v12.py",
        ROOT / "production_scripts/run_stage2_motion_40k_shard_v12_support.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v12_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v12_multigpu.py",
        ROOT / "production_scripts/launch_dlc_7x4_activeonly_v12_resilient.sh",
        ROOT / "production_scripts/gpu_memory_holder.py",
        ROOT / "production_scripts/prepare_stage2_motion_42k_v12_replenish_manifest.py",
        ROOT / "scripts/xonotic_stage1_reusable.py",
        ROOT / "scripts/xonotic_stage2_causal_formal.py",
    ]


def write_manifest(rows: list[dict[str, Any]], output_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite manifest root: {output_root}")
    shard_root = output_root / "shards-028"
    shard_root.mkdir(parents=True)
    shards = []
    for shard_index in range(SHARD_COUNT):
        selected = [
            row for row in rows if int(row["assigned_shard"]) == shard_index
        ]
        path = shard_root / f"shard-{shard_index:03d}-of-028.jsonl"
        path.write_text(
            "".join(canonical_json(row) + "\n" for row in selected),
            encoding="utf-8",
        )
        shards.append(
            {
                "shard_index": shard_index,
                "rows": len(selected),
                "target_accepted_rows": TARGET_ROWS_PER_SHARD,
                "primary_rows": sum(
                    row["candidate_role"] == "primary" for row in selected
                ),
                "reserve_rows": sum(
                    row["candidate_role"] == "reserve" for row in selected
                ),
                "path": str(path.relative_to(output_root)),
                "sha256": sha256_file(path),
            }
        )
    primary = [row for row in rows if row["candidate_role"] == "primary"]
    reserve = [row for row in rows if row["candidate_role"] == "reserve"]
    primary_jump = [
        row
        for row in primary
        if row["active_scenario"]["enemy_jump_program"]["enabled"]
    ]
    audit = {
        "schema_version": (
            "xonotic-stage2-motion-near5-combo-manifest-audit-v12-replenish"
        ),
        "passed": True,
        "target_accepted_rows": PRIMARY_ROWS,
        "primary_candidate_rows": len(primary),
        "reserve_candidate_rows": len(reserve),
        "candidate_rows": len(rows),
        "rendered_episode_budget_rows": PRIMARY_ROWS,
        "counterfactual_qa_rows": 0,
        "source_video_seconds": PRIMARY_ROWS * 5,
        "source_video_hours": PRIMARY_ROWS * 5 / 3600.0,
        "idle_distribution_primary": idle_distribution(primary),
        "idle_distribution_reserve": idle_distribution(reserve),
        "primary_distributions": {
            "intent_outcome": distribution(
                primary, lambda row: row["active_scenario"]["intent_outcome"]
            ),
            "weapon": distribution(
                primary, lambda row: row["active_scenario"]["weapon"]
            ),
            "map": distribution(
                primary, lambda row: row["active_scenario"]["map"]
            ),
            "enemy_model": distribution(
                primary, lambda row: row["active_scenario"]["enemy_model"]
            ),
            "enemy_motion": distribution(
                primary,
                lambda row: row["active_scenario"]["formal_design"][
                    "target_motion_name"
                ],
            ),
            "distance_tier": distribution(
                primary, lambda row: row["active_scenario"]["distance_tier"]
            ),
            "enemy_jumps": distribution(
                primary,
                lambda row: row["active_scenario"]["enemy_jump_program"][
                    "enabled"
                ],
            ),
        },
        "checks": {
            "target_rows_42000": len(primary) == PRIMARY_ROWS,
            "reserve_rows_10500": len(reserve) == RESERVE_ROWS,
            "candidate_rows_52500": len(rows) == CANDIDATE_ROWS,
            "primary_jump_rows_2000": len(primary_jump) == JUMP_ROWS,
            "ordinals_complete": [int(row["ordinal"]) for row in rows]
            == list(range(CANDIDATE_ROWS)),
            "sample_keys_unique": len({row["sample_key"] for row in rows})
            == CANDIDATE_ROWS,
            "all_postdeath_lock_required": all(
                row["active_scenario"]["postdeath_motion_lock_required"]
                for row in rows
            ),
            "no_frozen_scenario": all(
                "frozen_scenario" not in row for row in rows
            ),
            "shards_exactly_1875_candidates": all(
                shard["rows"] == TARGET_ROWS_PER_SHARD + RESERVE_ROWS_PER_SHARD
                for shard in shards
            ),
            "shards_exactly_1500_primary": all(
                shard["primary_rows"] == TARGET_ROWS_PER_SHARD for shard in shards
            ),
            "shards_exactly_375_reserve": all(
                shard["reserve_rows"] == RESERVE_ROWS_PER_SHARD for shard in shards
            ),
            "reserve_reads_no_live_state": all(
                row["active_scenario"]["reserve_transform"]["reads_camera"]
                is False
                and row["active_scenario"]["reserve_transform"][
                    "reads_live_player_state"
                ]
                is False
                for row in reserve
            ),
            "prefrozen_source_seed_contract": all(
                (
                    int(
                        row["active_scenario"]["prefrozen_trace_source"][
                            "source_action_seed"
                        ]
                    )
                    == prefrozen_action_seed(row["active_scenario"])
                    and (
                        (
                            row["candidate_role"] == "primary"
                            and row["active_scenario"]["prefrozen_trace_source"][
                                "scenario_seed_relation"
                            ]
                            == "matches_source_action_seed"
                            and int(row["active_scenario"]["seed"])
                            == int(
                                row["active_scenario"]["prefrozen_trace_source"][
                                    "source_action_seed"
                                ]
                            )
                        )
                        or (
                            row["candidate_role"] == "reserve"
                            and row["active_scenario"]["prefrozen_trace_source"][
                                "scenario_seed_relation"
                            ]
                            == "independent_replenishment_scenario_seed"
                            and int(row["active_scenario"]["seed"])
                            != int(
                                row["active_scenario"]["prefrozen_trace_source"][
                                    "source_action_seed"
                                ]
                            )
                        )
                    )
                )
                for row in rows
                if row["active_scenario"].get("prefrozen_trace_source")
            ),
        },
        "shards": shards,
    }
    audit["passed"] = all(audit["checks"].values())
    audit_path = output_root / "MANIFEST_AUDIT.json"
    write_json(audit_path, audit)
    files = runtime_files()
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing v12 runtime files: {missing}")
    source_metadata = json.loads(
        (SOURCE_MANIFEST / "MANIFEST_METADATA.json").read_text(encoding="utf-8")
    )
    metadata = {
        "schema_version": (
            "xonotic-stage2-motion-near5-combo-manifest-metadata-v12-replenish"
        ),
        "capture_mode": "active_only",
        "qa_mode": "single_episode_authoritative",
        "formal_collection_authorized": True,
        "training_admitted": False,
        "manual_review_required": False,
        "primary_rows": PRIMARY_ROWS,
        "rendered_episode_rows": PRIMARY_ROWS,
        "target_accepted_rows": PRIMARY_ROWS,
        "reserve_candidate_rows": RESERVE_ROWS,
        "candidate_rows": CANDIDATE_ROWS,
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
        "live_time_scale": 2,
        "shard_count": SHARD_COUNT,
        "shards": shards,
        "manifest_audit": str(audit_path.relative_to(output_root)),
        "manifest_audit_sha256": sha256_file(audit_path),
        "source_manifest_root": str(SOURCE_MANIFEST),
        "source_manifest_metadata_sha256": sha256_file(
            SOURCE_MANIFEST / "MANIFEST_METADATA.json"
        ),
    }
    write_json(output_root / "MANIFEST_METADATA.json", metadata)
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                handle.write(
                    f"{sha256_file(path)}  {path.relative_to(output_root)}\n"
                )
    if not audit["passed"]:
        raise RuntimeError(f"v12 manifest audit failed: {audit['checks']}")
    return metadata


def seed_carryover(
    rows: list[dict[str, Any]], source_run: Path, output_run: Path
) -> dict[str, Any]:
    if output_run.exists():
        raise FileExistsError(f"refusing to overwrite output run: {output_run}")
    output_run.mkdir(parents=True)
    row_by_key = {str(row["sample_key"]): row for row in rows}
    accepted: dict[str, dict[str, Any]] = {}
    for journal_path in sorted(source_run.glob("shard_*/manifests/accepted.jsonl")):
        for journal in read_jsonl(journal_path):
            sample_key = str(journal["sample_key"])
            if sample_key in accepted:
                raise RuntimeError(f"duplicate source accepted row: {sample_key}")
            accepted[sample_key] = journal
    carried = Counter()
    for sample_key, journal in sorted(
        accepted.items(), key=lambda item: int(item[1]["ordinal"])
    ):
        if sample_key not in row_by_key:
            raise RuntimeError(f"source accepted row outside v12 primary set: {sample_key}")
        manifest_row = row_by_key[sample_key]
        old_record_path = Path(journal["record_path"])
        if sha256_file(old_record_path) != journal["record_sha256"]:
            raise RuntimeError(f"source record hash mismatch: {sample_key}")
        record = json.loads(old_record_path.read_text(encoding="utf-8"))
        if record.get("capture_qa_passed") is not True:
            raise RuntimeError(f"source capture QA not passed: {sample_key}")
        record["schema_version"] = (
            "xonotic-stage2-motion-near5-combo-captured-sample-v12-replenish"
        )
        record["capture_mode"] = "active_only_v12_compatible_carryover"
        record["v12_carryover_provenance"] = {
            "source_record_path": str(old_record_path),
            "source_record_sha256": journal["record_sha256"],
            "source_acceptance_source": journal.get("acceptance_source"),
            "compatibility_basis": (
                "v12 changes lane warmup admission, postdeath QA boundary, and "
                "quota replenishment; the r3 source-seed declaration and "
                "render cvar validation fixes do not change accepted episode "
                "artifacts"
            ),
        }
        shard_index = int(manifest_row["assigned_shard"])
        shard_root = output_run / f"shard_{shard_index:02d}"
        record_path = shard_root / "records" / f"{sample_key}.json"
        write_json(record_path, record)
        out = {
            "schema_version": (
                "xonotic-stage2-motion-near5-combo-accepted-v12-replenish"
            ),
            "sample_key": sample_key,
            "ordinal": int(manifest_row["ordinal"]),
            "record_path": str(record_path),
            "record_sha256": sha256_file(record_path),
            "actual_outcome": record["actual_outcome"],
            "accepted_utc": journal["accepted_utc"],
            "acceptance_source": "v11_accepted_compatible_carryover",
        }
        output_journal = shard_root / "manifests/accepted.jsonl"
        output_journal.parent.mkdir(parents=True, exist_ok=True)
        with output_journal.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(out) + "\n")
        carried[str(record["actual_outcome"])] += 1
        carried[f"candidate_role:{manifest_row['candidate_role']}"] += 1
    summary = {
        "schema_version": (
            "xonotic-stage2-motion-near5-combo-carryover-v12-replenish"
        ),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_run_root": str(source_run),
        "output_run_root": str(output_run),
        "source_accepted_records": len(accepted),
        "carried_accepted_records": len(accepted),
        "carried_actual_outcome_distribution": {
            key: value
            for key, value in sorted(carried.items())
            if not key.startswith("candidate_role:")
        },
        "primary_records_carried": carried["candidate_role:primary"],
        "reserve_records_carried": carried["candidate_role:reserve"],
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
    parser.add_argument("--carryover-only", action="store_true")
    args = parser.parse_args()
    if args.manifest_only and args.carryover_only:
        parser.error("--manifest-only and --carryover-only are mutually exclusive")
    if not BUILD_LOCK.is_file():
        raise RuntimeError(f"v12 build lock missing: {BUILD_LOCK}")

    output_manifest = args.output_manifest_root.resolve()
    if args.carryover_only:
        rows = load_rows(output_manifest)
        if len(rows) != CANDIDATE_ROWS:
            raise RuntimeError("existing v12 candidate manifest is incomplete")
        carryover = seed_carryover(
            rows,
            args.source_run_root.resolve(),
            args.output_run_root.resolve(),
        )
        print(json.dumps({"carryover": carryover}, indent=2, sort_keys=True))
        return 0

    source_rows = load_source_rows(args.source_manifest_root.resolve())
    rows = build_rows(source_rows)
    metadata = write_manifest(rows, output_manifest)
    carryover = None
    if not args.manifest_only:
        carryover = seed_carryover(
            rows,
            args.source_run_root.resolve(),
            args.output_run_root.resolve(),
        )
    print(
        json.dumps(
            {
                "manifest_root": str(output_manifest),
                "target_accepted_rows": PRIMARY_ROWS,
                "candidate_rows": CANDIDATE_ROWS,
                "reserve_candidate_rows": RESERVE_ROWS,
                "training_hours": metadata["active_training_hours"],
                "output_run_root": (
                    None
                    if args.manifest_only
                    else str(args.output_run_root.resolve())
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
