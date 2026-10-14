                      
"""Materialize the immutable Stage-2 40k manifest and 12.5% reserve.

The design is assigned entirely before capture.  Realized target outcome is
telemetry only and is never used to admit, replace, or resample an episode.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage2_formal_design as design              
import xonotic_capture as capture              


DEFAULT_OUTPUT_ROOT = ROOT / "manifests/stage2_formal_40k_v1"
CANARY_AUDIT = (
    ROOT
    / "stage2_formal_canary_v1_output"
    / "FORMAL_CANARY_EFFECTIVE_AUDIT.json"
)
PAIR_AUDIT = (
    ROOT
    / "stage2_stationary_pair_certification_v1_r2_output"
    / "STATIONARY_PAIR_CERTIFICATION_AUDIT.json"
)
SCHEMA = "xonotic-stage2-formal-40k-manifest-v1"
SHARD_COUNTS = (32, 56)
PRIMARY_ROWS = 40_000
RESERVE_ROWS = 5_000
PRIMARY_MOVING_ROWS = 12_000
RESERVE_MOVING_ROWS = 1_500
DISTANCE_COUNTS = {
    "primary": {
        "close": 10_000,
        "near": 12_000,
        "medium": 10_000,
        "far": 4_800,
        "very_far": 2_400,
        "extreme": 800,
    },
    "reserve": {
        "close": 1_250,
        "near": 1_500,
        "medium": 1_250,
        "far": 600,
        "very_far": 300,
        "extreme": 100,
    },
}
FAMILY_RECIPE_COUNTS = {
    "primary": {
        ("visible_no_fire", "no_fire"): 6_000,
        ("precise_tracking", "hit_survive"): 8_000,
        ("precise_tracking", "kill"): 4_000,
        ("humanized_offset_tracking", "miss"): 8_000,
        ("humanized_offset_tracking", "hit_survive"): 4_000,
        ("stochastic_aim_and_fire", "miss"): 8_000,
        ("stochastic_aim_and_fire", "hit_survive"): 2_000,
    },
    "reserve": {
        ("visible_no_fire", "no_fire"): 750,
        ("precise_tracking", "hit_survive"): 1_000,
        ("precise_tracking", "kill"): 500,
        ("humanized_offset_tracking", "miss"): 1_000,
        ("humanized_offset_tracking", "hit_survive"): 500,
        ("stochastic_aim_and_fire", "miss"): 1_000,
        ("stochastic_aim_and_fire", "hit_survive"): 250,
    },
}
ARMS_BY_FAMILY = {
    "visible_no_fire": ("visible_no_fire",),
    "precise_tracking": design.PRECISE_ARMS,
    "humanized_offset_tracking": design.HUMANIZED_MISS_ARMS,
    "stochastic_aim_and_fire": design.STOCHASTIC_ARMS,
}
                                                                         
                                                                           
                                                                         
ARM_WEIGHTS_BY_WEAPON_FAMILY = {
    weapon: {
        "visible_no_fire": (("visible_no_fire", 1),),
        "precise_tracking": (
            ("stable_track", 1),
            ("overshoot_correct", 1),
            ("predictive_track", 1),
        ),
        "humanized_offset_tracking": (
            (("edge_graze", 2), ("near_miss", 1))
            if weapon == "Shotgun"
            else (
                (("edge_graze", 1), ("near_miss", 4))
                if weapon == "Vortex"
                else (("edge_graze", 1), ("near_miss", 1))
            )
        ),
        "stochastic_aim_and_fire": (
            (("stochastic_local", 1), ("stochastic_broad", 1))
            if weapon == "Vortex"
            else (("stochastic_local", 1), ("stochastic_broad", 2))
        ),
    }
    for weapon in design.WEAPONS
}


def require_passed_audit(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("passed") is not True:
        raise capture.CaptureFailure(
            "stage2_formal_authorization_audit_failed", str(path)
        )
    return payload


def authorization_basis() -> dict[str, Any]:
    canary = require_passed_audit(CANARY_AUDIT)
    pairs = require_passed_audit(PAIR_AUDIT)
    return {
        "schema_version": "xonotic-stage2-formal-authorization-v1",
        "canary_audit": str(CANARY_AUDIT.relative_to(ROOT)),
        "canary_audit_sha256": capture.sha256_file(CANARY_AUDIT),
        "canary_passed": True,
        "locked_lanes_per_gpu": int(canary["recommended_lanes_per_gpu"]),
        "pair_certification_audit": str(PAIR_AUDIT.relative_to(ROOT)),
        "pair_certification_audit_sha256": capture.sha256_file(PAIR_AUDIT),
        "pair_certification_passed": True,
        "formal_runtime": "scripts/xonotic_stage2_causal_formal.py",
        "formal_runtime_sha256": capture.sha256_file(
            ROOT / "scripts/xonotic_stage2_causal_formal.py"
        ),
        "historical_v4_runtime_sha256": capture.sha256_file(
            ROOT / "scripts/xonotic_stage2_causal.py"
        ),
        "source_commit": design.source_commit(),
    }


def balanced_values(
    values: tuple[Any, ...] | list[Any], count: int, seed: int
) -> list[Any]:
    result = [values[index % len(values)] for index in range(count)]
    random.Random(seed).shuffle(result)
    return result


def weighted_values(
    weighted: tuple[tuple[str, int], ...],
    count: int,
    seed: int,
) -> list[str]:
    cycle = [
        value
        for value, weight in weighted
        for _ in range(int(weight))
    ]
    if not cycle or any(weight <= 0 for _, weight in weighted):
        raise ValueError(weighted)
    result = [cycle[index % len(cycle)] for index in range(count)]
    random.Random(seed).shuffle(result)
    return result


def token_plan(cohort: str) -> list[dict[str, str]]:
    """Build a pre-capture joint weapon/outcome/aim allocation.

    Balancing weapon inside every family/outcome stratum prevents the formal
    kill quota (and every other planned outcome) from depending on an
    incidental global shuffle.  Arm weights are then applied independently
    inside each weapon stratum.
    """
    tokens: list[dict[str, str]] = []
    cohort_seed = (
        202_607_310_401 if cohort == "primary" else 202_607_310_402
    )
    for stratum_index, ((family, outcome), count) in enumerate(
        FAMILY_RECIPE_COUNTS[cohort].items()
    ):
        weapons = balanced_values(
            list(design.WEAPONS),
            count,
            cohort_seed + 100 + stratum_index,
        )
        indices_by_weapon: defaultdict[str, list[int]] = defaultdict(list)
        for index, weapon in enumerate(weapons):
            indices_by_weapon[weapon].append(index)
        arms_by_index: dict[int, str] = {}
        for weapon_index, weapon in enumerate(design.WEAPONS):
            indices = indices_by_weapon[weapon]
            arms = weighted_values(
                ARM_WEIGHTS_BY_WEAPON_FAMILY[weapon][family],
                len(indices),
                cohort_seed
                + 1_000
                + stratum_index * 100
                + weapon_index,
            )
            arms_by_index.update(zip(indices, arms, strict=True))
        for index, weapon in enumerate(weapons):
            tokens.append(
                {
                    "aim_family_bucket": family,
                    "outcome_recipe": outcome,
                    "weapon": weapon,
                    "arm": arms_by_index[index],
                }
            )
    random.Random(cohort_seed).shuffle(tokens)
    return tokens


def certified_pairs() -> list[dict[str, Any]]:
    audit = require_passed_audit(PAIR_AUDIT)
    accepted_ids = set(audit["certified_source_pair_episode_ids"])
    pairs = [
        row
        for row in design.preflight_pairs()
        if row["episode_id"] in accepted_ids
    ]
    if {row["episode_id"] for row in pairs} != accepted_ids:
        raise capture.CaptureFailure(
            "stage2_formal_certified_pair_identity_mismatch",
            capture.canonical_json(
                {
                    "audit": len(accepted_ids),
                    "resolved": len(pairs),
                }
            ),
        )
    if set(DISTANCE_COUNTS["primary"]) - {
        row["distance_bin"] for row in pairs
    }:
        raise capture.CaptureFailure(
            "stage2_formal_certified_pair_distance_missing",
            capture.canonical_json(
                Counter(row["distance_bin"] for row in pairs)
            ),
        )
    return pairs


def build_rows(
    *,
    cohort: str,
    count: int,
    moving_count: int,
    ordinal_offset: int,
    authorization: dict[str, Any],
    pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tokens = token_plan(cohort)
    if len(tokens) != count:
        raise capture.CaptureFailure(
            "stage2_formal_token_count", f"{cohort}:{len(tokens)}"
        )
    appearances = balanced_values(
        design.official_appearances(),
        count,
        202_607_310_421 if cohort == "primary" else 202_607_310_422,
    )
    moving_flags = [True] * moving_count + [False] * (count - moving_count)
    random.Random(
        202_607_310_431 if cohort == "primary" else 202_607_310_432
    ).shuffle(moving_flags)

    moving_distances: Counter[str] = Counter()
    for index, moving in enumerate(moving_flags):
        if not moving:
            continue
        source = design.weapon_templates()[
            (tokens[index]["weapon"], tokens[index]["arm"])
        ]
        moving_distances[
            str(source["encounter_source"]["source_pair_distance_bin"])
        ] += 1
    stationary_distance_counts = {
        distance_bin: target - moving_distances[distance_bin]
        for distance_bin, target in DISTANCE_COUNTS[cohort].items()
    }
    if any(value < 0 for value in stationary_distance_counts.values()):
        raise capture.CaptureFailure(
            "stage2_formal_moving_distance_overflow",
            capture.canonical_json(
                {
                    "cohort": cohort,
                    "moving": moving_distances,
                    "target": DISTANCE_COUNTS[cohort],
                }
            ),
        )
    stationary_distances: list[str] = [
        distance_bin
        for distance_bin, value in stationary_distance_counts.items()
        for _ in range(value)
    ]
    if len(stationary_distances) != count - moving_count:
        raise capture.CaptureFailure(
            "stage2_formal_stationary_distance_count",
            f"{cohort}:{len(stationary_distances)}",
        )
    random.Random(
        202_607_310_441 if cohort == "primary" else 202_607_310_442
    ).shuffle(stationary_distances)
    pair_pools: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        pair_pools[str(pair["distance_bin"])].append(pair)
    for index, pool in enumerate(pair_pools.values()):
        random.Random(202_607_310_450 + index).shuffle(pool)
    pair_cursors: Counter[str] = Counter()
    stationary_cursor = 0
    rows: list[dict[str, Any]] = []
    id_prefix = "s2f40v1p" if cohort == "primary" else "s2f40v1r"
    for index in range(count):
        ordinal = ordinal_offset + index
        token = tokens[index]
        kwargs = {
            "cohort": id_prefix,
            "ordinal": ordinal,
            "weapon": token["weapon"],
            "outcome_recipe": token["outcome_recipe"],
            "arm": token["arm"],
            "appearance": appearances[index],
            "formal_collection": True,
            "canary_authorization": authorization,
        }
        if moving_flags[index]:
            row = design.moving_scenario(**kwargs)
        else:
            distance_bin = stationary_distances[stationary_cursor]
            stationary_cursor += 1
            pool = pair_pools[distance_bin]
            pair = pool[pair_cursors[distance_bin] % len(pool)]
            pair_cursors[distance_bin] += 1
            row = design.stationary_scenario(pair=pair, **kwargs)
        row.pop("assigned_shard", None)
        row.pop("shard_count", None)
        row["formal_design"]["cohort_role"] = cohort
        row["formal_design"]["operational_reserve"] = cohort == "reserve"
        rows.append(row)
    return rows


def atomic_generated_file(
    destination: Path, writer: Any
) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.tmp.{os.getpid()}"
    )
    digest = hashlib.sha256()
    rows = 0
    with temporary.open("wb") as handle:
        for line in writer():
            payload = line.encode("utf-8")
            handle.write(payload)
            digest.update(payload)
            rows += 1
        handle.flush()
        os.fsync(handle.fileno())
    hexdigest = digest.hexdigest()
    if destination.exists():
        if capture.sha256_file(destination) != hexdigest:
            temporary.unlink()
            raise capture.CaptureFailure(
                "immutable_manifest_conflict", str(destination)
            )
        temporary.unlink()
    else:
        os.replace(temporary, destination)
    return hexdigest, rows


def canonical_variant(
    row: dict[str, Any], shard_index: int, shard_count: int
) -> str:
    variant = copy.deepcopy(row)
    variant["assigned_shard"] = shard_index
    variant["shard_count"] = shard_count
    return capture.canonical_json(variant) + "\n"


def write_design(
    cohort_root: Path, rows: list[dict[str, Any]]
) -> tuple[str, int]:
    return atomic_generated_file(
        cohort_root / "design.jsonl",
        lambda: (
            capture.canonical_json(row) + "\n" for row in rows
        ),
    )


def write_shards(
    cohort_root: Path,
    rows: list[dict[str, Any]],
    shard_count: int,
) -> dict[str, Any]:
    shard_root = cohort_root / f"shards-{shard_count:03d}"
    paths = [
        shard_root
        / f"shard-{index:03d}-of-{shard_count:03d}.jsonl"
        for index in range(shard_count)
    ]
    result: list[dict[str, Any]] = []
    for shard_index, path in enumerate(paths):
        digest, count = atomic_generated_file(
            path,
            lambda shard_index=shard_index: (
                canonical_variant(row, shard_index, shard_count)
                for index, row in enumerate(rows)
                if index % shard_count == shard_index
            ),
        )
        result.append(
            {
                "shard_index": shard_index,
                "rows": count,
                "path": str(path.relative_to(ROOT)),
                "sha256": digest,
            }
        )
    return {
        "shard_count": shard_count,
        "assignment": "zero_based_design_ordinal_mod_shard_count",
        "rows": len(rows),
        "shards": result,
    }


def distribution(rows: Iterable[dict[str, Any]], key: Any) -> dict[str, int]:
    return dict(Counter(str(key(row)) for row in rows))


def nested_distribution(
    rows: Iterable[dict[str, Any]], outer: Any, inner: Any
) -> dict[str, dict[str, int]]:
    result: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        result[str(outer(row))][str(inner(row))] += 1
    return {
        key: dict(value)
        for key, value in sorted(result.items())
    }


def write_metadata(
    cohort: str,
    cohort_root: Path,
    rows: list[dict[str, Any]],
    design_sha256: str,
    shard_sets: dict[str, Any],
    authorization: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "schema_version": SCHEMA,
        "cohort": cohort,
        "source_commit": design.source_commit(),
        "data_spec_sha256": design.data_spec_sha256(),
        "rows": len(rows),
        "formal_collection_authorized": True,
        "training_admitted": False,
        "operational_reserve": cohort == "reserve",
        "outcome_recipe_is_individual_admission_gate": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
        "formal_authorization_basis": authorization,
        "design_path": str((cohort_root / "design.jsonl").relative_to(ROOT)),
        "design_sha256": design_sha256,
        "planned_outcome_distribution": distribution(
            rows, lambda row: row["formal_design"]["outcome_recipe"]
        ),
        "aim_family_distribution": distribution(
            rows, lambda row: row["formal_design"]["aim_family_bucket"]
        ),
        "aim_arm_distribution": distribution(
            rows, lambda row: row["formal_design"]["arm"]
        ),
        "outcome_by_weapon": nested_distribution(
            rows,
            lambda row: row["formal_design"]["outcome_recipe"],
            lambda row: row["weapon"],
        ),
        "arm_by_weapon": nested_distribution(
            rows,
            lambda row: row["weapon"],
            lambda row: row["formal_design"]["arm"],
        ),
        "weapon_distribution": distribution(rows, lambda row: row["weapon"]),
        "appearance_distribution": distribution(
            rows,
            lambda row: f"{row['enemy_model']}:{row['enemy_skin']}",
        ),
        "distance_distribution": distribution(
            rows, lambda row: row["formal_design"]["distance_bin"]
        ),
        "map_distribution": distribution(rows, lambda row: row["map"]),
        "gametype_distribution": distribution(
            rows, lambda row: row["gametype"]
        ),
        "player_motion_distribution": distribution(
            rows,
            lambda row: row["formal_design"]["player_motion_class"],
        ),
        "enemy_motion_distribution": distribution(
            rows,
            lambda row: row["formal_design"].get(
                "enemy_motion_class",
                "seeded_piecewise_smooth_wander_v1",
            ),
        ),
        "kill_health_by_weapon": design.KILL_HEALTH_BY_WEAPON,
        "kill_design_contract": {
            "planned_fraction": 0.10,
            "target_health": 1.0,
            "aim_family": "precise_tracking",
            "actual_outcome_is_admission_gate": False,
            "true_miss_is_retained": True,
        },
        "shard_sets": shard_sets,
    }
    text = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    destination = cohort_root / "MANIFEST_METADATA.json"
    if destination.exists():
        if json.loads(destination.read_text(encoding="utf-8")) != metadata:
            raise capture.CaptureFailure(
                "immutable_manifest_conflict", str(destination)
            )
    else:
        destination.write_text(text, encoding="utf-8")
    return metadata


def audit_design(
    primary: list[dict[str, Any]], reserve: list[dict[str, Any]]
) -> dict[str, Any]:
    primary_kill = [
        row
        for row in primary
        if row["formal_design"]["outcome_recipe"] == "kill"
    ]
    reserve_kill = [
        row
        for row in reserve
        if row["formal_design"]["outcome_recipe"] == "kill"
    ]
    primary_kill_by_weapon = Counter(row["weapon"] for row in primary_kill)
    reserve_kill_by_weapon = Counter(row["weapon"] for row in reserve_kill)

    def balanced_across_weapons(counts: Counter[str]) -> bool:
        values = [counts[weapon] for weapon in design.WEAPONS]
        return max(values) - min(values) <= 1

    def kill_contract(rows: list[dict[str, Any]]) -> bool:
        return all(
            row["formal_design"]["aim_family_bucket"]
            == "precise_tracking"
            and row["formal_design"]["arm"] in design.PRECISE_ARMS
            and float(row["enemy"]["health"]) == 1.0
            and float(row["formal_design"]["enemy_health"]) == 1.0
            and row["formal_design"][
                "outcome_recipe_is_individual_admission_gate"
            ]
            is False
            and row["acceptance"]["actual_outcome"] is None
            for row in rows
        )

    checks = {
        "primary_rows_40000": len(primary) == PRIMARY_ROWS,
        "reserve_rows_5000": len(reserve) == RESERVE_ROWS,
        "episode_ids_unique": len(
            {row["episode_id"] for row in primary + reserve}
        )
        == PRIMARY_ROWS + RESERVE_ROWS,
        "primary_outcomes_exact": Counter(
            row["formal_design"]["outcome_recipe"] for row in primary
        )
        == Counter(
            {
                "no_fire": 6_000,
                "miss": 16_000,
                "hit_survive": 14_000,
                "kill": 4_000,
            }
        ),
        "reserve_outcomes_exact": Counter(
            row["formal_design"]["outcome_recipe"] for row in reserve
        )
        == Counter(
            {
                "no_fire": 750,
                "miss": 2_000,
                "hit_survive": 1_750,
                "kill": 500,
            }
        ),
        "primary_distance_exact": Counter(
            row["formal_design"]["distance_bin"] for row in primary
        )
        == Counter(DISTANCE_COUNTS["primary"]),
        "reserve_distance_exact": Counter(
            row["formal_design"]["distance_bin"] for row in reserve
        )
        == Counter(DISTANCE_COUNTS["reserve"]),
        "all_formal_pending_admission": all(
            row["formal_collection_authorized"] is True
            and row["training_admitted"] is False
            and row["acceptance"]["actual_outcome"] is None
            and row["formal_design"][
                "outcome_recipe_is_individual_admission_gate"
            ]
            is False
            for row in primary + reserve
        ),
        "no_runtime_fallback": all(
            not row["formal_design"][name]
            for row in primary + reserve
            for name in (
                "runtime_action_fallback",
                "runtime_geometry_fallback",
                "runtime_outcome_fallback",
            )
        ),
        "all_weapons_have_kill": all(
            any(
                row["weapon"] == weapon
                and row["formal_design"]["outcome_recipe"] == "kill"
                for row in primary
            )
            for weapon in design.WEAPONS
        ),
        "primary_kill_exact_4000": len(primary_kill) == 4_000,
        "reserve_kill_exact_500": len(reserve_kill) == 500,
        "primary_kill_weapon_balanced": balanced_across_weapons(
            primary_kill_by_weapon
        ),
        "reserve_kill_weapon_balanced": balanced_across_weapons(
            reserve_kill_by_weapon
        ),
        "kill_precise_one_hp_no_outcome_admission": kill_contract(
            primary_kill + reserve_kill
        ),
    }
    return {
        "schema_version": "xonotic-stage2-formal-40k-design-audit-v1",
        "checks": checks,
        "primary_kill_by_weapon": dict(primary_kill_by_weapon),
        "reserve_kill_by_weapon": dict(reserve_kill_by_weapon),
        "passed": all(checks.values()),
    }


def materialize(output_root: Path) -> dict[str, Any]:
    authorization = authorization_basis()
    pairs = certified_pairs()
    primary = build_rows(
        cohort="primary",
        count=PRIMARY_ROWS,
        moving_count=PRIMARY_MOVING_ROWS,
        ordinal_offset=0,
        authorization=authorization,
        pairs=pairs,
    )
    reserve = build_rows(
        cohort="reserve",
        count=RESERVE_ROWS,
        moving_count=RESERVE_MOVING_ROWS,
        ordinal_offset=PRIMARY_ROWS,
        authorization=authorization,
        pairs=pairs,
    )
    audit = audit_design(primary, reserve)
    if not audit["passed"]:
        raise capture.CaptureFailure(
            "stage2_formal_40k_design_audit_failed",
            capture.canonical_json(audit["checks"]),
        )
    metadata_by_cohort: dict[str, Any] = {}
    for cohort, rows in (("primary", primary), ("reserve", reserve)):
        cohort_root = output_root / cohort
        design_sha256, design_rows = write_design(cohort_root, rows)
        if design_rows != len(rows):
            raise capture.CaptureFailure(
                "stage2_formal_design_write_count", cohort
            )
        shard_sets = {
            str(shard_count): write_shards(
                cohort_root, rows, shard_count
            )
            for shard_count in SHARD_COUNTS
        }
        metadata_by_cohort[cohort] = write_metadata(
            cohort,
            cohort_root,
            rows,
            design_sha256,
            shard_sets,
            authorization,
        )
    audit.update(
        {
            "primary_metadata": str(
                output_root / "primary/MANIFEST_METADATA.json"
            ),
            "reserve_metadata": str(
                output_root / "reserve/MANIFEST_METADATA.json"
            ),
            "formal_authorization_basis": authorization,
            "certified_pair_count": len(pairs),
            "certified_map_count": len({row["map"] for row in pairs}),
        }
    )
    audit_path = output_root / "DESIGN_AUDIT.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    args = parser.parse_args()
    audit = materialize(args.output_root.resolve())
    print(
        capture.canonical_json(
            {
                "output_root": str(args.output_root.resolve()),
                "primary_rows": PRIMARY_ROWS,
                "reserve_rows": RESERVE_ROWS,
                "recommended_lanes": audit[
                    "formal_authorization_basis"
                ]["locked_lanes_per_gpu"],
                "passed": audit["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
