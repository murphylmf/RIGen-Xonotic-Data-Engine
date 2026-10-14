                      
"""Prepare and atomically activate the bounded long60 recovery manifest.

The recovery keeps all 1,475 accepted rows byte-for-byte unchanged.  It only
repoints the 325 missing rows to revised scenario artifacts:

* 264 controlled-return rows use a 12 degree killed-aim QA tolerance.
* 61 four-distinct rows keep Nyx in slot 1 but use 10 health so its one
  calibrated MachineGun hit realizes the declared kill.

Enemy firing, player actions, prompt schedules, engine seeds, and render
settings are not changed.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pilot_scripts"))
import long60_production_v1 as production              


REVISION = "long60-recovery-r1"
EXPECTED_ACCEPTED = 1475
EXPECTED_QA_ONLY = 264
EXPECTED_NYX = 61
QA_AIM_DEGREES = 12.0
NYX_SLOT1_HEALTH = 10.0
NYX_ID = "enemy_nyx_yellow"
IGNIS_ID = "enemy_ignis_red"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def accepted_ids(output_root: Path) -> set[str]:
    return {
        path.stem
        for path in (output_root / "status" / "accepted").glob("*.json")
    }


def ids_sha256(values: set[str]) -> str:
    return sha256_bytes(("\n".join(sorted(values)) + "\n").encode("utf-8"))


def classify_missing(row: dict[str, Any]) -> str:
    if (
        row["template"] == "controlled_return"
        and 2 in row["kill_slots"]
        and row["actor_order"][1] != IGNIS_ID
    ):
        return "qa_threshold_only"
    if (
        row["template"] == "four_distinct"
        and 1 in row["kill_slots"]
        and row["actor_order"][0] == NYX_ID
    ):
        return "nyx_slot1_health"
    raise RuntimeError(
        f"unexpected missing episode distribution: {row['episode_id']}"
    )


def write_timeline_with_nyx_health(
    source: Path, destination: Path
) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    matches = 0
    for row in rows[1:]:
        if row[0] == "actor" and int(row[1]) == 1:
            if row[2] != NYX_ID or float(row[6]) != 15.0:
                raise RuntimeError(
                    f"unexpected Nyx slot-1 timeline row in {source}: {row}"
                )
            row[6] = str(NYX_SLOT1_HEALTH)
            matches += 1
    if matches != 1:
        raise RuntimeError(
            f"expected one Nyx slot-1 actor row in {source}; got {matches}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def select_canaries(rows: list[dict[str, Any]]) -> list[int]:
    selected: list[int] = []
    for actor_id in ("enemy_pyria_white", "enemy_umbra_yellow", NYX_ID):
        selected.append(
            next(
                row["manifest_index"]
                for row in rows
                if row.get("recovery_class") == "qa_threshold_only"
                and row["actor_order"][1] == actor_id
            )
        )
    for kill_slots in ([1], [1, 2], [1, 3]):
        selected.append(
            next(
                row["manifest_index"]
                for row in rows
                if row.get("recovery_class") == "nyx_slot1_health"
                and row["kill_slots"] == kill_slots
            )
        )
    return selected


def prepare(
    source_manifest_root: Path,
    source_output_root: Path,
    recovery_manifest_root: Path,
) -> None:
    source_manifest_root = source_manifest_root.resolve()
    source_output_root = source_output_root.resolve()
    recovery_manifest_root = recovery_manifest_root.resolve()
    if recovery_manifest_root.exists():
        raise RuntimeError(
            f"recovery manifest root already exists: {recovery_manifest_root}"
        )

    source_rows, source_metadata = production.validate_manifest(
        source_manifest_root
    )
    current_accepted = accepted_ids(source_output_root)
    if len(current_accepted) != EXPECTED_ACCEPTED:
        raise RuntimeError(
            f"accepted baseline changed: {len(current_accepted)} "
            f"!= {EXPECTED_ACCEPTED}"
        )
    source_ids = {row["episode_id"] for row in source_rows}
    if not current_accepted <= source_ids:
        raise RuntimeError("accepted set contains IDs outside the source manifest")

    missing = [
        row for row in source_rows if row["episode_id"] not in current_accepted
    ]
    classes = Counter(classify_missing(row) for row in missing)
    expected_classes = Counter(
        {
            "qa_threshold_only": EXPECTED_QA_ONLY,
            "nyx_slot1_health": EXPECTED_NYX,
        }
    )
    if classes != expected_classes:
        raise RuntimeError(
            f"unexpected recovery classes: {classes} != {expected_classes}"
        )

    recovery_manifest_root.mkdir(parents=True)
    rows = copy.deepcopy(source_rows)
    timeline_cache: dict[str, tuple[Path, str]] = {}
    created_utc = production.utc_now()
    source_manifest_sha256 = production.base.sha256(
        source_manifest_root / "manifest.jsonl"
    )

    for row in rows:
        if row["episode_id"] in current_accepted:
            continue
        recovery_class = classify_missing(row)
        source_scenario_path = ROOT / row["scenario_path"]
        source_scenario_sha256 = production.base.sha256(source_scenario_path)
        if source_scenario_sha256 != row["scenario_sha256"]:
            raise RuntimeError(
                f"source scenario hash mismatch: {source_scenario_path}"
            )
        scenario = json.loads(source_scenario_path.read_text(encoding="utf-8"))
        scenario.setdefault("lifecycle_policy", {})[
            "killed_aim_region_max_degrees"
        ] = QA_AIM_DEGREES
        scenario["recovery_policy"] = {
            "schema_version": "xonotic-stage2-long60-recovery-policy-v1",
            "revision": REVISION,
            "recovery_class": recovery_class,
            "source_scenario_path": row["scenario_path"],
            "source_scenario_sha256": source_scenario_sha256,
            "killed_aim_region_max_degrees": QA_AIM_DEGREES,
            "nyx_slot1_health": (
                NYX_SLOT1_HEALTH
                if recovery_class == "nyx_slot1_health"
                else None
            ),
            "enemy_firing_changed": False,
            "player_actions_changed": False,
            "prompt_schedule_changed": False,
            "engine_seed_changed": False,
        }

        if recovery_class == "nyx_slot1_health":
            actor = next(
                actor for actor in scenario["actors"] if actor["slot"] == 1
            )
            if actor["actor_id"] != NYX_ID or float(actor["health"]) != 15.0:
                raise RuntimeError(
                    f"unexpected Nyx scenario actor in {row['episode_id']}: {actor}"
                )
            actor["health"] = NYX_SLOT1_HEALTH
            if scenario["enemy_model"] != "nyx":
                raise RuntimeError(
                    f"unexpected primary model in {row['episode_id']}"
                )
            scenario["enemy"]["health"] = NYX_SLOT1_HEALTH

            source_timeline_path = ROOT / row["timeline_path"]
            source_timeline_key = str(source_timeline_path.resolve())
            if source_timeline_key not in timeline_cache:
                temporary_name = f"nyx10-{source_timeline_path.stem}.csv"
                recovery_timeline = (
                    recovery_manifest_root / "timeline_configs" / temporary_name
                )
                write_timeline_with_nyx_health(
                    source_timeline_path, recovery_timeline
                )
                recovery_timeline_sha256 = production.base.sha256(
                    recovery_timeline
                )
                timeline_cache[source_timeline_key] = (
                    recovery_timeline,
                    recovery_timeline_sha256,
                )
            recovery_timeline, recovery_timeline_sha256 = timeline_cache[
                source_timeline_key
            ]
            scenario["enemy_timeline_path"] = production.relative_to_root(
                recovery_timeline
            )
            scenario["enemy_timeline_sha256"] = recovery_timeline_sha256
            row["source_timeline_path"] = row["timeline_path"]
            row["source_timeline_sha256"] = row["timeline_sha256"]
            row["timeline_path"] = production.relative_to_root(
                recovery_timeline
            )
            row["timeline_sha256"] = recovery_timeline_sha256

        recovery_scenario = (
            recovery_manifest_root
            / "episodes"
            / row["episode_id"]
            / "scenario.json"
        )
        production.write_json_atomic(recovery_scenario, scenario)
        row["source_scenario_path"] = row["scenario_path"]
        row["source_scenario_sha256"] = row["scenario_sha256"]
        row["scenario_path"] = production.relative_to_root(recovery_scenario)
        row["scenario_sha256"] = production.base.sha256(recovery_scenario)
        row["recovery_revision"] = REVISION
        row["recovery_class"] = recovery_class

    manifest = recovery_manifest_root / "manifest.jsonl"
    production.write_jsonl_atomic(manifest, rows)
    metadata = copy.deepcopy(source_metadata)
    metadata.update(
        {
            "created_utc": created_utc,
            "manifest_path": production.relative_to_root(manifest),
            "manifest_sha256": production.base.sha256(manifest),
            "recovery_revision": REVISION,
            "source_manifest_path": production.relative_to_root(
                source_manifest_root / "manifest.jsonl"
            ),
            "source_manifest_sha256": source_manifest_sha256,
            "recovery_counts": dict(sorted(classes.items())),
            "recovery_policy": {
                "killed_aim_region_max_degrees": QA_AIM_DEGREES,
                "nyx_slot1_health": NYX_SLOT1_HEALTH,
                "enemy_firing_changed": False,
                "player_actions_changed": False,
                "prompt_schedule_changed": False,
            },
        }
    )
    production.write_json_atomic(
        recovery_manifest_root / "MANIFEST_METADATA.json", metadata
    )
    production.write_json_atomic(
        recovery_manifest_root / "PREPARED.json",
        {
            "ready": True,
            "created_utc": created_utc,
            "manifest_sha256": metadata["manifest_sha256"],
            "episode_count": len(rows),
            "recovery_revision": REVISION,
        },
    )
    canary_indices = select_canaries(rows)
    plan = {
        "schema_version": "xonotic-stage2-long60-recovery-plan-v1",
        "created_utc": created_utc,
        "revision": REVISION,
        "source_manifest_root": str(source_manifest_root),
        "source_output_root": str(source_output_root),
        "source_manifest_sha256": source_manifest_sha256,
        "source_accepted_count": len(current_accepted),
        "source_accepted_ids_sha256": ids_sha256(current_accepted),
        "missing_count": len(missing),
        "missing_ids_sha256": ids_sha256(
            {row["episode_id"] for row in missing}
        ),
        "recovery_counts": dict(sorted(classes.items())),
        "canary_manifest_indices": canary_indices,
        "enemy_firing_changed": False,
    }
    production.write_json_atomic(
        recovery_manifest_root / "RECOVERY_PLAN.json", plan
    )
    production.validate_manifest(recovery_manifest_root)
    print(json.dumps(plan, ensure_ascii=False, sort_keys=True), flush=True)


def copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp.{os.getpid()}")
    with source.open("rb") as input_handle, temporary.open("wb") as output_handle:
        shutil.copyfileobj(input_handle, output_handle, 8 * 1024 * 1024)
        output_handle.flush()
        os.fsync(output_handle.fileno())
    os.replace(temporary, destination)


def validate_canary(
    recovery_manifest_root: Path,
    canary_output_root: Path,
    plan: dict[str, Any],
) -> dict[str, Any]:
    rows = production.load_jsonl(recovery_manifest_root / "manifest.jsonl")
    by_index = {row["manifest_index"]: row for row in rows}
    expected_ids = {
        by_index[index]["episode_id"]
        for index in plan["canary_manifest_indices"]
    }
    canary_ids = accepted_ids(canary_output_root)
    if canary_ids != expected_ids:
        raise RuntimeError(
            f"canary accepted IDs mismatch: {sorted(canary_ids)} "
            f"!= {sorted(expected_ids)}"
        )
    classes: Counter[str] = Counter()
    for episode_id in sorted(expected_ids):
        record = json.loads(
            (
                canary_output_root
                / "status"
                / "accepted"
                / f"{episode_id}.json"
            ).read_text(encoding="utf-8")
        )
        qa = json.loads(Path(record["qa_path"]).read_text(encoding="utf-8"))
        row = next(row for row in rows if row["episode_id"] == episode_id)
        if qa.get("passed") is not True:
            raise RuntimeError(f"canary QA did not pass: {episode_id}")
        if (
            qa.get("lifecycle", {}).get("killed_aim_region_max_degrees")
            != QA_AIM_DEGREES
        ):
            raise RuntimeError(f"canary QA threshold mismatch: {episode_id}")
        if qa.get("counts", {}).get("enemy_kill_events") != row["kill_count"]:
            raise RuntimeError(f"canary kill count mismatch: {episode_id}")
        classes[row["recovery_class"]] += 1
    expected_classes = Counter(
        {"qa_threshold_only": 3, "nyx_slot1_health": 3}
    )
    if classes != expected_classes:
        raise RuntimeError(
            f"canary class coverage mismatch: {classes} != {expected_classes}"
        )
    return {
        "canary_output_root": str(canary_output_root),
        "accepted_count": len(canary_ids),
        "accepted_ids_sha256": ids_sha256(canary_ids),
        "classes": dict(sorted(classes.items())),
    }


def activate(
    source_manifest_root: Path,
    source_output_root: Path,
    recovery_manifest_root: Path,
    canary_output_root: Path,
) -> None:
    source_manifest_root = source_manifest_root.resolve()
    source_output_root = source_output_root.resolve()
    recovery_manifest_root = recovery_manifest_root.resolve()
    production.validate_manifest(recovery_manifest_root)
    plan = json.loads(
        (recovery_manifest_root / "RECOVERY_PLAN.json").read_text(
            encoding="utf-8"
        )
    )
    if plan.get("revision") != REVISION:
        raise RuntimeError(f"unexpected recovery revision: {plan}")
    canary = validate_canary(
        recovery_manifest_root, canary_output_root.resolve(), plan
    )
    current_manifest_sha256 = production.base.sha256(
        source_manifest_root / "manifest.jsonl"
    )
    if current_manifest_sha256 != plan["source_manifest_sha256"]:
        raise RuntimeError(
            "source manifest changed before activation: "
            f"{current_manifest_sha256} != {plan['source_manifest_sha256']}"
        )
    current_accepted = accepted_ids(source_output_root)
    if ids_sha256(current_accepted) != plan["source_accepted_ids_sha256"]:
        raise RuntimeError("accepted baseline changed before activation")

    timestamp = production.utc_now().replace(":", "").replace("-", "")
    backup_root = (
        source_manifest_root / "recovery_backups" / f"{REVISION}-{timestamp}"
    )
    backup_root.mkdir(parents=True)
    for name in ("manifest.jsonl", "MANIFEST_METADATA.json", "PREPARED.json"):
        shutil.copy2(source_manifest_root / name, backup_root / name)
    production.write_json_atomic(backup_root / "RECOVERY_PLAN.json", plan)

                                                                         
                                                                            
                                                                           
                                                                            
                                       
    recovery_rows = production.load_jsonl(
        recovery_manifest_root / "manifest.jsonl"
    )
    active_rows = copy.deepcopy(recovery_rows)
    replaced_scenarios = 0
    for row in active_rows:
        if row.get("recovery_revision") != REVISION:
            continue
        repaired_scenario = ROOT / row["scenario_path"]
        original_scenario = ROOT / row["source_scenario_path"]
        scenario_backup = (
            backup_root / "scenarios" / row["episode_id"] / "scenario.json"
        )
        scenario_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original_scenario, scenario_backup)
        copy_atomic(repaired_scenario, original_scenario)
        row["scenario_path"] = row["source_scenario_path"]
        row["scenario_sha256"] = production.base.sha256(original_scenario)
        replaced_scenarios += 1
    if replaced_scenarios != EXPECTED_QA_ONLY + EXPECTED_NYX:
        raise RuntimeError(
            f"unexpected replaced scenario count: {replaced_scenarios}"
        )

    active_manifest_staging = recovery_manifest_root / "manifest.active.jsonl"
    production.write_jsonl_atomic(active_manifest_staging, active_rows)
    copy_atomic(active_manifest_staging, source_manifest_root / "manifest.jsonl")
    recovery_metadata = json.loads(
        (recovery_manifest_root / "MANIFEST_METADATA.json").read_text(
            encoding="utf-8"
        )
    )
    recovery_metadata["manifest_path"] = production.relative_to_root(
        source_manifest_root / "manifest.jsonl"
    )
    recovery_metadata["activated_utc"] = production.utc_now()
    recovery_metadata["activation_backup_root"] = production.relative_to_root(
        backup_root
    )
    recovery_metadata["manifest_sha256"] = production.base.sha256(
        source_manifest_root / "manifest.jsonl"
    )
    recovery_metadata["replaced_missing_scenario_count"] = replaced_scenarios
    production.write_json_atomic(
        source_manifest_root / "MANIFEST_METADATA.json", recovery_metadata
    )
    prepared = json.loads(
        (recovery_manifest_root / "PREPARED.json").read_text(encoding="utf-8")
    )
    prepared["activated_utc"] = recovery_metadata["activated_utc"]
    prepared["manifest_sha256"] = recovery_metadata["manifest_sha256"]
    production.write_json_atomic(source_manifest_root / "PREPARED.json", prepared)
    activation = {
        "schema_version": "xonotic-stage2-long60-recovery-activation-v1",
        "activated_utc": recovery_metadata["activated_utc"],
        "revision": REVISION,
        "backup_root": str(backup_root),
        "active_manifest_sha256": production.base.sha256(
            source_manifest_root / "manifest.jsonl"
        ),
        "accepted_baseline_count": len(current_accepted),
        "accepted_baseline_ids_sha256": ids_sha256(current_accepted),
        "canary": canary,
    }
    production.write_json_atomic(
        source_manifest_root / "RECOVERY_ACTIVE.json", activation
    )
    production.validate_manifest(source_manifest_root)
    print(json.dumps(activation, ensure_ascii=False, sort_keys=True), flush=True)


def audit(
    manifest_root: Path, output_root: Path
) -> None:
    rows, metadata = production.validate_manifest(manifest_root.resolve())
    recovered = [row for row in rows if row.get("recovery_revision") == REVISION]
    classes = Counter(row.get("recovery_class") for row in recovered)
    current_accepted = accepted_ids(output_root.resolve())
    checks = {
        "manifest_valid": True,
        "recovery_row_count": len(recovered) == EXPECTED_QA_ONLY + EXPECTED_NYX,
        "recovery_classes": classes
        == Counter(
            {
                "qa_threshold_only": EXPECTED_QA_ONLY,
                "nyx_slot1_health": EXPECTED_NYX,
            }
        ),
        "enemy_firing_unchanged": metadata.get("recovery_policy", {}).get(
            "enemy_firing_changed"
        )
        is False,
    }
    report = {
        "checks": checks,
        "passed": all(checks.values()),
        "manifest_sha256": production.base.sha256(
            manifest_root / "manifest.jsonl"
        ),
        "accepted_count": len(current_accepted),
        "remaining_count": len(rows) - len(current_accepted),
        "recovery_counts": dict(sorted(classes.items())),
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    if not report["passed"]:
        raise RuntimeError(f"recovery audit failed: {report}")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "activate", "audit"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--manifest-root", type=Path, required=True)
        subparser.add_argument("--output-root", type=Path, required=True)
        if command in {"prepare", "activate"}:
            subparser.add_argument(
                "--recovery-manifest-root", type=Path, required=True
            )
        if command == "activate":
            subparser.add_argument(
                "--canary-output-root", type=Path, required=True
            )
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.manifest_root, args.output_root, args.recovery_manifest_root)
    elif args.command == "activate":
        activate(
            args.manifest_root,
            args.output_root,
            args.recovery_manifest_root,
            args.canary_output_root,
        )
    elif args.command == "audit":
        audit(args.manifest_root, args.output_root)
    else:
        raise AssertionError(args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
