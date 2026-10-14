                      
"""Materialize the 15-row stationary extension of the 96-row formal canary.

Together with the immutable 81-row moving canary, these rows exercise every
distance bin and the formal-only stationary-preflight runtime.  Outcome recipes
are assigned before capture and are never individual admission gates.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage2_formal_design as design              
import xonotic_capture as capture              


OUTPUT_ROOT = ROOT / "manifests/stage2_formal_stationary_extension_v1"
SCHEMA = "xonotic-stage2-formal-stationary-extension-manifest-v1"
DISTANCE_PLAN = (
    "close",
    "near",
    "medium",
    "far",
    "very_far",
    "extreme",
) * 2 + ("close", "near", "medium")
RECIPE_PLAN = (
    ("no_fire", "visible_no_fire"),
    ("miss", "edge_graze"),
    ("hit_survive", "stable_track"),
    ("miss", "stochastic_local"),
    ("hit_survive", "overshoot_correct"),
    ("kill", "stable_track"),
    ("miss", "near_miss"),
    ("hit_survive", "predictive_track"),
    ("miss", "stochastic_broad"),
    ("no_fire", "visible_no_fire"),
    ("hit_survive", "stable_track"),
    ("miss", "edge_graze"),
    ("hit_survive", "overshoot_correct"),
    ("miss", "near_miss"),
    ("kill", "stable_track"),
)
WEAPON_PLAN = (
    "Blaster",
    "Shotgun",
    "MachineGun",
    "Mortar",
    "Electro",
    "MachineGun",
    "Crylink",
    "Vortex",
    "Hagar",
    "Devastator",
    "Blaster",
    "Shotgun",
    "Mortar",
    "Electro",
    "Devastator",
)


def write_once_or_verify(path: Path, text: str) -> None:
    payload = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise capture.CaptureFailure(
                "immutable_manifest_conflict", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def select_pairs() -> list[dict[str, Any]]:
    by_bin: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in design.preflight_pairs():
        by_bin[str(row["distance_bin"])].append(row)
    cursors: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    for distance_bin in DISTANCE_PLAN:
        pool = by_bin[distance_bin]
        index = cursors[distance_bin] % len(pool)
        selected.append(pool[index])
        cursors[distance_bin] += 1
    return selected


def materialize() -> list[dict[str, Any]]:
    appearances = design.official_appearances()
    rows: list[dict[str, Any]] = []
    for ordinal, (pair, weapon, recipe_arm) in enumerate(
        zip(select_pairs(), WEAPON_PLAN, RECIPE_PLAN, strict=True)
    ):
        recipe, arm = recipe_arm
        row = design.stationary_scenario(
            cohort="s2fcv1x",
            ordinal=ordinal,
            weapon=weapon,
            outcome_recipe=recipe,
            arm=arm,
            pair=pair,
            appearance=appearances[ordinal % len(appearances)],
            formal_collection=False,
            canary_authorization=None,
        )
        row["assigned_shard"] = 0
        row["shard_count"] = 1
        rows.append(row)

    input_text = design.canonical_lines(rows)
    input_sha256 = design.sha256_text(input_text)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, input_text)
    write_once_or_verify(shard_path, input_text)
    metadata = {
        "schema_version": SCHEMA,
        "source_commit": design.source_commit(),
        "data_spec_sha256": capture.sha256_file(design.DATA_SPEC),
        "rows": len(rows),
        "shard_count": 1,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "nontraining_formal_shaped_canary": True,
        "logical_canary_total_with_moving_v1": 96,
        "outcome_recipe_is_individual_admission_gate": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
        "runtime_outcome_fallback": False,
        "weapon_distribution": dict(Counter(row["weapon"] for row in rows)),
        "planned_outcome_distribution": dict(
            Counter(row["formal_design"]["outcome_recipe"] for row in rows)
        ),
        "distance_distribution": dict(
            Counter(row["formal_design"]["distance_bin"] for row in rows)
        ),
        "map_distribution": dict(Counter(row["map"] for row in rows)),
        "input_sha256": input_sha256,
        "review": {
            "rows": len(rows),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "rows": len(rows),
                    "path": str(shard_path.relative_to(ROOT)),
                    "sha256": input_sha256,
                }
            ],
        },
    }
    write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        capture.canonical_json(
            {
                "manifest": str(OUTPUT_ROOT / "input.jsonl"),
                "rows": len(rows),
                "outcomes": dict(
                    Counter(
                        row["formal_design"]["outcome_recipe"]
                        for row in rows
                    )
                ),
                "distances": dict(
                    Counter(
                        row["formal_design"]["distance_bin"] for row in rows
                    )
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
