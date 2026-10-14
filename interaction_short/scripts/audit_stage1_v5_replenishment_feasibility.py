                      
"""Audit fixed Stage-1 v5 replenishment-reserve constraint groups.

This is a design-time feasibility audit.  It always derives the residual pool
from the deterministic primary MILP, then tests declared groups without
changing a bound to match observed capacity.
"""

from __future__ import annotations

import hashlib
import json
import itertools
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_v5_manifests as v5              


OUTPUT = (
    v5.PATH_CERTIFICATE_ROOT
    / "feasibility"
    / "REPLENISHMENT_CONSTRAINT_GROUP_AUDIT.json"
)


def main() -> int:
    pool = v5.load_certified_pool()
    primary, primary_audit = v5.select_certified_paths(
        pool,
        count=v5.PRIMARY_PROTOTYPE_COUNT,
        quota_scale=v5.PRIMARY_PROTOTYPE_SCALE,
        label="primary",
    )
    primary_ids = {str(row["episode_id"]) for row in primary}
    rows = [
        row
        for row in pool
        if str(row["episode_id"]) not in primary_ids
    ]

    def semantic_allocation_report(
        selected: list[dict[str, Any]],
        *,
        replenishment: bool,
        seed: int,
    ) -> dict[str, Any]:
        groups: list[dict[str, Any]] = []
        targets_by_cell: dict[
            tuple[str, str], dict[str, int]
        ] = {}
        cell_counts: dict[tuple[str, str], int] = {}
        for row in selected:
            cell = (
                str(row["dataset_role"]),
                str(row["primary_bucket"]),
            )
            cell_counts[cell] = cell_counts.get(cell, 0) + 1
            groups.append(
                {"prototype": row, "counts": {}, "weapons": {}}
            )
        for cell, path_count in cell_counts.items():
            targets_by_cell[cell] = (
                v5.semantic_action_cell_targets(
                    cell,
                    path_count * v5.SEMANTIC_VARIANTS_PER_PROTOTYPE,
                    replenishment=replenishment,
                )
            )
        error: dict[str, Any] | None = None
        allocation: dict[str, Any] = {
            "passed": False,
            "cells": [],
            "distribution_constraints": [],
        }
        try:
            action_scale = (
                v5.v4.REPLENISHMENT_SCALE
                if replenishment
                else 1
            )
            allocation = v5._allocate_semantic_counts(
                groups,
                cell_targets=targets_by_cell,
                distribution_constraints=(
                    v5._semantic_distribution_constraints(
                        selected, action_scale=action_scale
                    )
                ),
                seed=seed,
            )
        except v5.capture.CaptureFailure as exc:
            error = {
                "reason": exc.reason,
                "detail": str(exc),
            }
        feasible = (
            allocation.get("passed") is True
            and len(allocation.get("cells", []))
            == len(v5.REPLENISHMENT_FIXED_CELL_PATH_COUNTS)
            and error is None
            and all(
                item.get("passed") is True
                for item in allocation.get(
                    "distribution_constraints", []
                )
            )
        )
        return {
            "method": "joint_integer_allocation",
            "capacity_clamping": False,
            **allocation,
            "feasible": feasible,
            "error": error,
        }

    primary_semantic_allocation = semantic_allocation_report(
        primary,
        replenishment=False,
        seed=v5.PROTOTYPE_SEED + 2_000_000,
    )

    grouped: dict[
        str, list[tuple[str, np.ndarray, int, int]]
    ] = {}

    def add(
        group: str,
        name: str,
        predicate: Any,
        lower: int,
        upper: int,
    ) -> None:
        vector = np.fromiter(
            (1.0 if predicate(row) else 0.0 for row in rows),
            dtype=np.float64,
            count=len(rows),
        )
        grouped.setdefault(group, []).append(
            (name, vector, lower, upper)
        )

    count = v5.REPLENISHMENT_PROTOTYPE_COUNT
    add("base", "total", lambda _: True, count, count)
    for cell, target in sorted(
        v5.REPLENISHMENT_FIXED_CELL_PATH_COUNTS.items()
    ):
        role, bucket = cell
        add(
            "base",
            f"cell:{role}:{bucket}",
            lambda row, role=role, bucket=bucket: (
                row["dataset_role"] == role
                and row["primary_bucket"] == bucket
            ),
            target,
            target,
        )
        semantic_targets = v5.semantic_action_cell_targets(
            cell,
            target * v5.SEMANTIC_VARIANTS_PER_PROTOTYPE,
            replenishment=True,
        )
        add(
            "semantic_capacity",
            f"semantic_primary_capacity:{role}:{bucket}",
            lambda row, role=role, bucket=bucket: (
                row["dataset_role"] == role
                and row["primary_bucket"] == bucket
                and v5.physical_arity(row) <= 2
                and not row["_certified_blockage"].get(
                    "visible_collision_qualified", False
                )
                and (
                    not row["enemy_present"]
                    or row["scheduler_targets"]["target_relation"]
                    in v5.SAFE_PRIMARY_FIRE_RELATIONS
                )
            ),
            math.ceil(
                semantic_targets["environmental_primary"]
                / len(v5.v4.WEAPONS)
            ),
            target,
        )
        add(
            "semantic_capacity",
            f"semantic_reload_capacity:{role}:{bucket}",
            lambda row, role=role, bucket=bucket: (
                row["dataset_role"] == role
                and row["primary_bucket"] == bucket
                and v5.physical_arity(row) <= 2
            ),
            math.ceil(
                semantic_targets["reload"]
                / len(v5.v4.RELOAD_WEAPONS)
            ),
            target,
        )
        add(
            "semantic_capacity",
            f"semantic_variant_weight_capacity:{role}:{bucket}",
            lambda row, role=role, bucket=bucket: (
                row["dataset_role"] == role
                and row["primary_bucket"] == bucket
                and v5.physical_arity(row) <= 2
            ),
            math.ceil(
                target
                / (
                    v5.FORMAL_SEMANTIC_VARIANTS_MAX
                    - v5.FORMAL_SEMANTIC_VARIANTS_MIN
                )
            ),
            target,
        )
    planned = (
        (
            "target_relation",
            lambda row: (row.get("scheduler_targets") or {}).get(
                "target_relation"
            ),
        ),
        (
            "distance",
            lambda row: (row.get("scheduler_targets") or {}).get(
                "distance_bin"
            ),
        ),
        (
            "enemy_policy",
            lambda row: (row.get("enemy_policy") or {}).get("name"),
        ),
    )
    for axis, getter in planned:
        for value, target in (
            v5.REPLENISHMENT_FIXED_PLANNED_TARGETS[axis].items()
        ):
            add(
                f"planned_{axis}_exact",
                f"planned:{axis}:{value}",
                lambda row, value=value, getter=getter: (
                    getter(row) == value
                ),
                target,
                target,
            )
            for tolerance_percent in (5, 10, 15, 25):
                tolerance = math.ceil(
                    target * tolerance_percent / 100
                )
                add(
                    f"planned_all_{tolerance_percent:02d}pct",
                    f"planned:{axis}:{value}",
                    lambda row, value=value, getter=getter: (
                        getter(row) == value
                    ),
                    max(0, target - tolerance),
                    target + tolerance,
                )

    for field, baseline in v5.PHYSICAL_MARGINAL_BASELINE.items():
        group = (
            "physical_directions"
            if field in {"locomotion_direction", "view_direction"}
            else "physical_profiles"
        )
        for value, full_count in baseline.items():
            target = round(
                full_count / v5.REPLENISHMENT_PROTOTYPE_SCALE
            )
            tolerance = max(
                1,
                math.ceil(
                    target * v5.PHYSICAL_MARGINAL_TOLERANCE
                ),
            )
            add(
                group,
                f"physical:{field}:{value}",
                lambda row, field=field, value=value: (
                    row["action_design"].get(field) == value
                ),
                max(0, target - tolerance),
                target + tolerance,
            )
            add(
                "physical_coverage",
                f"coverage:physical:{field}:{value}",
                lambda row, field=field, value=value: (
                    row["action_design"].get(field) == value
                ),
                1,
                count,
            )

    for group, targets, metric_name in (
        (
            "realized_net",
            v5.REPLENISHMENT_FIXED_NET_TARGETS,
            "net_displacement_bin",
        ),
        ("realized_yaw", v5.v4.YAW_COUNTS, "yaw_range_bin"),
        ("realized_pitch", v5.v4.PITCH_COUNTS, "pitch_range_bin"),
    ):
        for name, full_count in targets.items():
            target = (
                full_count
                if group == "realized_net"
                else full_count // v5.REPLENISHMENT_PROTOTYPE_SCALE
            )
            tolerance = math.ceil(
                target * v5.REALIZED_MARGINAL_TOLERANCE
            )
            add(
                group,
                f"{group}:{name}",
                lambda row, metric_name=metric_name, name=name: (
                    row["_certified_motion"][metric_name] == name
                ),
                max(0, target - tolerance),
                target + tolerance,
            )
            if group == "realized_net":
                add(
                    "realized_net_coverage",
                    f"coverage:net:{name}",
                    lambda row, metric_name=metric_name, name=name: (
                        row["_certified_motion"][metric_name] == name
                    ),
                    1,
                    count,
                )

    add(
        "long_motion",
        "path_ge1000",
        lambda row: row["_certified_motion"]["path_length_3d"]
        >= 1_000,
        math.ceil(count * v5.PATH_GE1000_MIN_FRACTION),
        count,
    )
    add(
        "long_motion",
        "path_ge2000",
        lambda row: row["_certified_motion"]["path_length_3d"]
        >= 2_000,
        math.ceil(count * v5.PATH_GE2000_MIN_FRACTION),
        count,
    )
    add(
        "long_motion",
        "joint_net512_yaw90",
        lambda row: (
            row["_certified_motion"]["net_displacement_3d"] >= 512
            and row["_certified_motion"]["yaw_range_deg"] >= 90
        ),
        math.ceil(
            count * v5.JOINT_NET512_YAW90_MIN_FRACTION
        ),
        count,
    )
    add(
        "collision",
        "visible_wall_contact",
        lambda row: (
            row["_certified_blockage"].get(
                "visible_collision_qualified"
            )
            is True
            and v5.physical_arity(row) <= 2
        ),
        math.ceil(count * 0.01),
        math.floor(count * 0.03),
    )
    add(
        "collision",
        "visible_wall_contact_arity_gt2_excluded",
        lambda row: (
            row["_certified_blockage"].get(
                "visible_collision_qualified"
            )
            is True
            and v5.physical_arity(row) > 2
        ),
        0,
        0,
    )
    for map_name in sorted({str(row["map"]) for row in rows}):
        add(
            "maps",
            f"map:{map_name}",
            lambda row, map_name=map_name: row["map"] == map_name,
            1,
            count,
        )

    def solve(
        groups: list[str], *, detail: bool = False
    ) -> dict[str, Any]:
        constraints = [
            constraint
            for group in groups
            for constraint in grouped[group]
        ]
        matrix = np.vstack(
            [constraint[1] for constraint in constraints]
        )
        result = milp(
            np.zeros(len(rows), dtype=np.float64),
            integrality=np.ones(len(rows), dtype=np.int8),
            bounds=Bounds(
                np.zeros(len(rows)), np.ones(len(rows))
            ),
            constraints=LinearConstraint(
                matrix,
                np.asarray(
                    [constraint[2] for constraint in constraints]
                ),
                np.asarray(
                    [constraint[3] for constraint in constraints]
                ),
            ),
            options={"time_limit": 30.0, "mip_rel_gap": 0.0},
        )
        audit = {
            "groups": groups,
            "feasible": bool(result.success and result.x is not None),
            "solver_status": int(result.status),
            "solver_message": str(result.message),
        }
        if audit["feasible"] and detail:
            selected = [
                row
                for row, value in zip(rows, result.x)
                if float(value) >= 0.5
            ]
            audit["selected_distribution"] = (
                v5.selection_capacity_report(selected)
            )
        print(
            f"{'PASS' if audit['feasible'] else 'FAIL'} "
            + ",".join(groups),
            flush=True,
        )
        return audit

    optional = [
        "physical_directions",
        "physical_profiles",
        "realized_net",
        "realized_yaw",
        "realized_pitch",
        "long_motion",
        "collision",
        "maps",
    ]
    tests: list[dict[str, Any]] = []
    tests.append(solve(["base"]))
    exact_planned_groups = [
        "planned_target_relation_exact",
        "planned_distance_exact",
        "planned_enemy_policy_exact",
    ]
    for group in exact_planned_groups:
        tests.append(solve(["base", group]))
    tests.append(solve(["base", *exact_planned_groups]))
    for tolerance_percent in (5, 10, 15, 25):
        tests.append(
            solve(
                [
                    "base",
                    f"planned_all_{tolerance_percent:02d}pct",
                ]
            )
        )
    for group in optional:
        tests.append(solve(["base", group]))
                                                                           
                                                                          
                                                                          
                                 
    enumerated = [
        group for group in optional if group != "realized_net"
    ]
    subset_tests: list[dict[str, Any]] = []
    for size in range(len(enumerated) + 1):
        for subset in itertools.combinations(enumerated, size):
            result = solve(
                ["base", "planned_all_05pct", *subset]
            )
            result["optional_subset"] = list(subset)
            subset_tests.append(result)
    maximum_size = max(
        (
            len(test["optional_subset"])
            for test in subset_tests
            if test["feasible"]
        ),
        default=-1,
    )
    maximal_feasible = [
        solve(test["groups"], detail=True)
        for test in subset_tests
        if test["feasible"]
        and len(test["optional_subset"]) == maximum_size
    ]

                                                                             
                                                                             
                                                                          
                                                                     
    recommended_hard_groups = [
        "base",
        "semantic_capacity",
        "planned_all_05pct",
        "physical_coverage",
        "realized_net_coverage",
        "realized_yaw",
        "realized_pitch",
        "long_motion",
        "collision",
        "maps",
    ]
    hard_constraints = [
        constraint
        for group in recommended_hard_groups
        for constraint in grouped[group]
    ]
    soft: list[tuple[str, np.ndarray, int, float]] = []
    for name, full_count in v5.v4.NET_COUNTS.items():
        target = full_count // v5.REPLENISHMENT_PROTOTYPE_SCALE
        soft.append(
            (
                f"net:{name}",
                np.fromiter(
                    (
                        1.0
                        if row["_certified_motion"][
                            "net_displacement_bin"
                        ]
                        == name
                        else 0.0
                        for row in rows
                    ),
                    dtype=np.float64,
                    count=len(rows),
                ),
                target,
                4.0 / target,
            )
        )
    for field, baseline in v5.PHYSICAL_MARGINAL_BASELINE.items():
        for value, full_count in baseline.items():
            target = round(
                full_count / v5.REPLENISHMENT_PROTOTYPE_SCALE
            )
            soft.append(
                (
                    f"physical:{field}:{value}",
                    np.fromiter(
                        (
                            1.0
                            if row["action_design"].get(field) == value
                            else 0.0
                            for row in rows
                        ),
                        dtype=np.float64,
                        count=len(rows),
                    ),
                    target,
                    1.0 / target,
                )
            )
    variable_count = len(rows) + 2 * len(soft)
    objective = np.zeros(variable_count, dtype=np.float64)
    for index, row in enumerate(rows):
        objective[index] = (
            int(
                hashlib.sha256(
                    (
                        "replenishment-policy:"
                        f"{row['episode_id']}"
                    ).encode()
                ).hexdigest()[:12],
                16,
            )
            / float(16**12)
            * 1e-7
        )
    hard_matrix = np.zeros(
        (len(hard_constraints), variable_count),
        dtype=np.float64,
    )
    for index, (_, vector, _, _) in enumerate(hard_constraints):
        hard_matrix[index, : len(rows)] = vector
    soft_matrix = np.zeros(
        (len(soft), variable_count), dtype=np.float64
    )
    for index, (_, vector, target, weight) in enumerate(soft):
        soft_matrix[index, : len(rows)] = vector
        soft_matrix[index, len(rows) + index * 2] = -1.0
        soft_matrix[index, len(rows) + index * 2 + 1] = 1.0
        objective[len(rows) + index * 2] = weight
        objective[len(rows) + index * 2 + 1] = weight
    matrix = np.vstack((hard_matrix, soft_matrix))
    lower = np.asarray(
        [constraint[2] for constraint in hard_constraints]
        + [target for _, _, target, _ in soft],
        dtype=np.float64,
    )
    upper = np.asarray(
        [constraint[3] for constraint in hard_constraints]
        + [target for _, _, target, _ in soft],
        dtype=np.float64,
    )
    optimized = milp(
        objective,
        integrality=np.concatenate(
            (
                np.ones(len(rows), dtype=np.int8),
                np.zeros(2 * len(soft), dtype=np.int8),
            )
        ),
        bounds=Bounds(
            np.zeros(variable_count),
            np.concatenate(
                (
                    np.ones(len(rows)),
                    np.full(2 * len(soft), count, dtype=np.float64),
                )
            ),
        ),
        constraints=LinearConstraint(matrix, lower, upper),
        options={"time_limit": 120.0, "mip_rel_gap": 0.0},
    )
    optimized_selected = (
        [
            row
            for row, value in zip(rows, optimized.x[: len(rows)])
            if float(value) >= 0.5
        ]
        if optimized.success and optimized.x is not None
        else []
    )
    optimized_physical = {
        field: {
            str(value): sum(
                row["action_design"].get(field) == value
                for row in optimized_selected
            )
            for value in baseline
        }
        for field, baseline in v5.PHYSICAL_MARGINAL_BASELINE.items()
    }
    optimized_distribution = (
        v5.selection_capacity_report(optimized_selected)
        if optimized_selected
        else None
    )
    replenishment_semantic_allocation = (
        semantic_allocation_report(
            optimized_selected,
            replenishment=True,
            seed=v5.PROTOTYPE_SEED + 3_000_000,
        )
    )
    semantic_allocation_feasible = (
        replenishment_semantic_allocation["feasible"] is True
    )
    optimized_feasible = bool(
        optimized.success
        and optimized.x is not None
        and semantic_allocation_feasible
    )
    overall_feasible = bool(
        primary_semantic_allocation["feasible"] is True
        and optimized_feasible
    )

    report = {
        "schema_version": (
            "xonotic-stage1-v5-replenishment-constraint-audit-v1"
        ),
        "created_utc": v5.capture.utc_now(),
        "capacity_clamping": False,
        "certificate_index_sha256": v5.capture.sha256_file(
            v5.PATH_CERTIFICATE_INDEX
        ),
        "passed": overall_feasible,
        "primary_rows": len(primary),
        "primary_solver": primary_audit["solver"],
        "primary_semantic_allocation": (
            primary_semantic_allocation
        ),
        "residual_rows": len(rows),
        "fixed_policy": {
            "cell_path_counts": {
                f"{role}:{bucket}": value
                for (role, bucket), value in sorted(
                    v5.REPLENISHMENT_FIXED_CELL_PATH_COUNTS.items()
                )
            },
            "planned_targets": (
                v5.REPLENISHMENT_FIXED_PLANNED_TARGETS
            ),
            "net_targets": v5.REPLENISHMENT_FIXED_NET_TARGETS,
            "physical_targets": {
                field: {
                    str(value): target
                    for value, target in targets.items()
                }
                for field, targets in (
                    v5.REPLENISHMENT_FIXED_PHYSICAL_TARGETS.items()
                )
            },
            "action_cell_targets": {
                f"{role}:{bucket}": targets
                for (role, bucket), targets in sorted(
                    v5.REPLENISHMENT_FIXED_ACTION_CELL_COUNTS.items()
                )
            },
            "semantic_variant_weight_bounds": {
                "minimum": v5.FORMAL_SEMANTIC_VARIANTS_MIN,
                "maximum": v5.FORMAL_SEMANTIC_VARIANTS_MAX,
                "mean_absolute_deviation_maximum": (
                    v5.FORMAL_SEMANTIC_MEAN_ABSOLUTE_DEVIATION_MAX
                ),
            },
        },
        "constraint_groups": {
            group: [
                {
                    "name": name,
                    "lower": lower,
                    "upper": upper,
                    "capacity": int(vector.sum()),
                }
                for name, vector, lower, upper in constraints
            ]
            for group, constraints in grouped.items()
        },
        "tests": tests,
        "subset_enumeration": {
            "planned_group": "planned_all_05pct",
            "optional_groups": enumerated,
            "maximum_feasible_optional_groups": maximum_size,
            "tests": subset_tests,
            "maximal_feasible": maximal_feasible,
        },
        "recommended_policy_optimization": {
            "hard_groups": recommended_hard_groups,
            "capacity_clamping": False,
            "soft_objective": (
                "minimum weighted absolute relative deviation from the "
                "nominal net and physical marginals; net weight 4, "
                "physical weight 1"
            ),
            "solver_status": int(optimized.status),
            "solver_message": str(optimized.message),
            "solver_feasible": bool(
                optimized.success and optimized.x is not None
            ),
            "semantic_allocation_feasible": (
                semantic_allocation_feasible
            ),
            "semantic_allocation": {
                **replenishment_semantic_allocation,
            },
            "feasible": optimized_feasible,
            "objective": (
                float(optimized.fun)
                if optimized.fun is not None
                else None
            ),
            "selected_distribution": optimized_distribution,
            "selected_physical_marginals": optimized_physical,
        },
    }
    v5.atomic_json(OUTPUT, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if overall_feasible else 2


if __name__ == "__main__":
    raise SystemExit(main())
