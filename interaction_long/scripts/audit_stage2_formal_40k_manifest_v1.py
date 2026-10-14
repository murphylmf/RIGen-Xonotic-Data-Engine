                      
"""Independent distribution, immutability, and shard audit for Stage-2 40k."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage2_formal_design as design              
import xonotic_capture as capture              


MANIFEST_ROOT = ROOT / "manifests/stage2_formal_40k_v1"
OUTPUT = MANIFEST_ROOT / "MANIFEST_AUDIT.json"
EXPECTED = {
    "primary": {
        "rows": 40_000,
        "outcomes": {
            "no_fire": 6_000,
            "miss": 16_000,
            "hit_survive": 14_000,
            "kill": 4_000,
        },
        "families": {
            "visible_no_fire": 6_000,
            "precise_tracking": 12_000,
            "humanized_offset_tracking": 12_000,
            "stochastic_aim_and_fire": 10_000,
        },
        "distances": {
            "close": 10_000,
            "near": 12_000,
            "medium": 10_000,
            "far": 4_800,
            "very_far": 2_400,
            "extreme": 800,
        },
        "moving": 12_000,
    },
    "reserve": {
        "rows": 5_000,
        "outcomes": {
            "no_fire": 750,
            "miss": 2_000,
            "hit_survive": 1_750,
            "kill": 500,
        },
        "families": {
            "visible_no_fire": 750,
            "precise_tracking": 1_500,
            "humanized_offset_tracking": 1_500,
            "stochastic_aim_and_fire": 1_250,
        },
        "distances": {
            "close": 1_250,
            "near": 1_500,
            "medium": 1_250,
            "far": 600,
            "very_far": 300,
            "extreme": 100,
        },
        "moving": 1_500,
    },
}


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def stream_rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def audit_cohort(cohort: str) -> tuple[dict[str, Any], set[str]]:
    expected = EXPECTED[cohort]
    root = MANIFEST_ROOT / cohort
    metadata_path = root / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    design_path = root / "design.jsonl"
    ids: set[str] = set()
    outcomes: Counter[str] = Counter()
    families: Counter[str] = Counter()
    distances: Counter[str] = Counter()
    weapons: Counter[str] = Counter()
    maps: Counter[str] = Counter()
    appearances: Counter[str] = Counter()
    motion: Counter[str] = Counter()
    kill_weapons: Counter[str] = Counter()
    rows = 0
    row_contract = True
    for row in stream_rows(design_path):
        rows += 1
        episode_id = str(row["episode_id"])
        if episode_id in ids:
            row_contract = False
        ids.add(episode_id)
        formal = row["formal_design"]
        outcome = str(formal["outcome_recipe"])
        family = str(formal["aim_family_bucket"])
        outcomes[outcome] += 1
        families[family] += 1
        distances[str(formal["distance_bin"])] += 1
        weapons[str(row["weapon"])] += 1
        maps[str(row["map"])] += 1
        appearances[f"{row['enemy_model']}:{row['enemy_skin']}"] += 1
        motion[str(formal["player_motion_class"])] += 1
        row_contract = row_contract and (
            row["formal_collection_authorized"] is True
            and row["training_admitted"] is False
            and row["acceptance"]["actual_outcome"] is None
            and formal["outcome_recipe_is_individual_admission_gate"]
            is False
            and not formal["runtime_action_fallback"]
            and not formal["runtime_geometry_fallback"]
            and not formal["runtime_outcome_fallback"]
        )
        if outcome == "kill":
            kill_weapons[str(row["weapon"])] += 1
            row_contract = row_contract and (
                family == "precise_tracking"
                and formal["arm"] in design.PRECISE_ARMS
                and float(row["enemy"]["health"]) == 1.0
                and float(formal["enemy_health"]) == 1.0
            )
    authorization = metadata["formal_authorization_basis"]
    checks = {
        "metadata_rows": metadata["rows"] == expected["rows"],
        "design_sha256": (
            capture.sha256_file(design_path) == metadata["design_sha256"]
        ),
        "rows_exact": rows == expected["rows"] == len(ids),
        "outcomes_exact": outcomes == Counter(expected["outcomes"]),
        "aim_families_exact": families == Counter(expected["families"]),
        "distances_exact": distances == Counter(expected["distances"]),
        "weapons_complete": set(weapons) == set(design.WEAPONS),
        "appearances_14": len(appearances) == 14,
        "maps_27": len(maps) == 27,
        "moving_exact": motion["certified_prefrozen_trace_replay"]
        == expected["moving"],
        "kill_weapon_balanced": set(kill_weapons)
        == set(design.WEAPONS)
        and max(kill_weapons.values()) - min(kill_weapons.values()) <= 1,
        "row_contract": row_contract,
        "authorization_current": (
            authorization["canary_passed"] is True
            and authorization["pair_certification_passed"] is True
            and authorization["locked_lanes_per_gpu"] == 8
            and capture.sha256_file(
                ROOT / authorization["canary_audit"]
            )
            == authorization["canary_audit_sha256"]
            and capture.sha256_file(
                ROOT / authorization["pair_certification_audit"]
            )
            == authorization["pair_certification_audit_sha256"]
            and capture.sha256_file(
                ROOT / authorization["formal_runtime"]
            )
            == authorization["formal_runtime_sha256"]
        ),
    }
    shard_audits: dict[str, Any] = {}
    for shard_count in (32, 56):
        declared = metadata["shard_sets"][str(shard_count)]
        shard_ids: set[str] = set()
        shard_rows: list[int] = []
        shard_checks = True
        for entry in declared["shards"]:
            path = ROOT / entry["path"]
            index = int(entry["shard_index"])
            count = 0
            if capture.sha256_file(path) != entry["sha256"]:
                shard_checks = False
            for row in stream_rows(path):
                count += 1
                episode_id = str(row["episode_id"])
                if (
                    episode_id in shard_ids
                    or int(row["assigned_shard"]) != index
                    or int(row["shard_count"]) != shard_count
                ):
                    shard_checks = False
                shard_ids.add(episode_id)
            shard_checks = shard_checks and count == int(entry["rows"])
            shard_rows.append(count)
        shard_checks = (
            shard_checks
            and shard_ids == ids
            and sum(shard_rows) == rows
            and max(shard_rows) - min(shard_rows) <= 1
        )
        checks[f"shards_{shard_count}_exact"] = shard_checks
        shard_audits[str(shard_count)] = {
            "rows": sum(shard_rows),
            "minimum_rows_per_shard": min(shard_rows),
            "maximum_rows_per_shard": max(shard_rows),
            "passed": shard_checks,
        }
    return (
        {
            "rows": rows,
            "design_sha256": capture.sha256_file(design_path),
            "outcomes": dict(outcomes),
            "aim_families": dict(families),
            "distances": dict(distances),
            "weapons": dict(weapons),
            "kill_by_weapon": dict(kill_weapons),
            "maps": dict(maps),
            "appearances": dict(appearances),
            "player_motion": dict(motion),
            "shards": shard_audits,
            "checks": checks,
            "passed": all(checks.values()),
        },
        ids,
    )


def main() -> int:
    cohorts: dict[str, Any] = {}
    all_ids: dict[str, set[str]] = {}
    for cohort in ("primary", "reserve"):
        cohorts[cohort], all_ids[cohort] = audit_cohort(cohort)
    checks = {
        "generator_design_audit": json.loads(
            (MANIFEST_ROOT / "DESIGN_AUDIT.json").read_text()
        )["passed"]
        is True,
        "primary_passed": cohorts["primary"]["passed"],
        "reserve_passed": cohorts["reserve"]["passed"],
        "cohorts_disjoint": not (
            all_ids["primary"] & all_ids["reserve"]
        ),
    }
    result = {
        "schema_version": "xonotic-stage2-formal-40k-manifest-audit-v1",
        "manifest_root": str(MANIFEST_ROOT),
        "cohorts": cohorts,
        "checks": checks,
        "passed": all(checks.values()),
    }
    atomic_json(OUTPUT, result)
    print(
        capture.canonical_json(
            {
                "primary": cohorts["primary"]["rows"],
                "reserve": cohorts["reserve"]["rows"],
                "passed": result["passed"],
                "audit": str(OUTPUT),
            }
        )
    )
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
