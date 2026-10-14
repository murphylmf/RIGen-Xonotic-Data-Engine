                      
"""Audit fixed Stage-1 v5 semantic path-weight smoothness bounds."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_v5_manifests as v5              


OUTPUT = (
    v5.PATH_CERTIFICATE_ROOT
    / "feasibility"
    / "SEMANTIC_WEIGHT_CONSTRAINT_AUDIT.json"
)
DECLARED_BOUNDS = (0.30, 0.35, 0.40, 0.50, 0.75, 1.00, 1.25, 1.50)


def allocation_inputs(
    selected: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[tuple[str, str], dict[str, int]],
]:
    groups = [
        {"prototype": row, "counts": {}, "weapons": {}}
        for row in selected
    ]
    counts: dict[tuple[str, str], int] = {}
    for row in selected:
        cell = (
            str(row["dataset_role"]),
            str(row["primary_bucket"]),
        )
        counts[cell] = counts.get(cell, 0) + 1
    targets = {
        cell: v5.semantic_action_cell_targets(
            cell,
            count * v5.SEMANTIC_VARIANTS_PER_PROTOTYPE,
            replenishment=False,
        )
        for cell, count in counts.items()
    }
    return groups, targets


def main() -> int:
    pool = v5.load_certified_pool()
    primary, selection = v5.select_certified_paths(
        pool,
        count=v5.PRIMARY_PROTOTYPE_COUNT,
        quota_scale=v5.PRIMARY_PROTOTYPE_SCALE,
        label="primary",
    )
    constraints = v5._semantic_distribution_constraints(
        primary, action_scale=1
    )
    tests = []
    first_feasible = None
    for bound in DECLARED_BOUNDS:
        groups, targets = allocation_inputs(primary)
        started = time.monotonic()
        try:
            allocation = v5._allocate_semantic_counts(
                groups,
                cell_targets=targets,
                distribution_constraints=constraints,
                mean_absolute_deviation_maximum=bound,
                seed=v5.PROTOTYPE_SEED + 2_000_000,
            )
            row = {
                "bound": bound,
                "feasible": allocation.get("passed") is True,
                "wall_seconds": time.monotonic() - started,
                "solver_status": allocation.get("solver_status"),
                "solver_message": allocation.get("solver_message"),
                "mean_absolute_deviation_from_ten": allocation.get(
                    "mean_absolute_deviation_from_ten"
                ),
                "weight_counts": allocation.get("weight_counts"),
                "distribution_constraints_passed": all(
                    item.get("passed") is True
                    for item in allocation.get(
                        "distribution_constraints", []
                    )
                ),
            }
        except v5.capture.CaptureFailure as exc:
            row = {
                "bound": bound,
                "feasible": False,
                "wall_seconds": time.monotonic() - started,
                "reason": exc.reason,
                "detail": str(exc),
            }
        tests.append(row)
        print(
            f"{'PASS' if row['feasible'] else 'FAIL'} "
            f"mean_absolute_deviation_bound={bound:.2f}",
            flush=True,
        )
        if row["feasible"] and first_feasible is None:
            first_feasible = bound
            break
    report = {
        "schema_version": (
            "xonotic-stage1-v5-semantic-weight-feasibility-v1"
        ),
        "created_utc": v5.capture.utc_now(),
        "capacity_clamping": False,
        "certificate_index_sha256": v5.capture.sha256_file(
            v5.PATH_CERTIFICATE_INDEX
        ),
        "primary_selection_sha256": hashlib.sha256(
            v5.canonical_lines(
                {
                    "episode_id": row["episode_id"],
                    "certificate_sha256": row[
                        "_player_path_certificate"
                    ]["certificate_sha256"],
                }
                for row in primary
            ).encode()
        ).hexdigest(),
        "primary_selection_solver": selection["solver"],
        "distribution_constraint_count": len(constraints),
        "implementation_sha256": {
            "prepare_stage1_v5_manifests.py": v5.capture.sha256_file(
                Path(v5.__file__).resolve()
            ),
            "audit_stage1_v5_semantic_weight_feasibility.py": (
                v5.capture.sha256_file(Path(__file__).resolve())
            ),
        },
        "declared_bounds": list(DECLARED_BOUNDS),
        "first_feasible_bound": first_feasible,
        "tests": tests,
        "passed": first_feasible is not None,
    }
    v5.atomic_json(OUTPUT, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
