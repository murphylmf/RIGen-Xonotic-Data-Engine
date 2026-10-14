                      
"""Explicit replacements for the two terminal secondary-mechanism rejects."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
SOURCE = (
    ROOT
    / "manifests/stage2_causal_secondary_validation_v1/input.jsonl"
)
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_causal_secondary_replenishment_v1"
)
REPLACEMENTS = {
    "MachineGun": (
        "s2secondary_repl_01_machinegun",
        15_410_001,
        "stock mode=1 LT burst emits three fire events with the "
        "primary deathtype bit; QA now proves LT input and 3:1 burst ratio",
    ),
    "Hagar": (
        "s2secondary_repl_02_hagar",
        15_410_002,
        "stock load consumes clip before release; QA now links each "
        "authoritative -1 clip transition under LT to a secondary release",
    ),
}


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_manifest_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def materialize() -> list[dict[str, Any]]:
    source_rows = capture.load_jsonl(SOURCE)
    rows: list[dict[str, Any]] = []
    for ordinal, weapon in enumerate(REPLACEMENTS):
        matches = [row for row in source_rows if row["weapon"] == weapon]
        if len(matches) != 1:
            raise capture.CaptureFailure(
                "stage2_secondary_replacement_source", weapon
            )
        episode_id, seed, basis = REPLACEMENTS[weapon]
        row = copy.deepcopy(matches[0])
        rejected_episode = row["episode_id"]
        row.update(
            {
                "episode_id": episode_id,
                "anchor_id": f"{episode_id}_pair",
                "counterfactual_group_id": episode_id,
                "seed": seed,
                "candidate_kind": (
                    "explicit_secondary_validation_replenishment"
                ),
                "canary_role": f"stage2_secondary_replenishment_{weapon.lower()}",
                "validation_ordinal": ordinal,
                "formal_collection_authorized": False,
                "training_admitted": False,
            }
        )
        row["enemy_policy"]["policy_seed"] = seed
        row["replacement_contract"] = {
            "schema_version": "xonotic-stage2-replacement-v1",
            "replacement_for_rejected_episode": rejected_episode,
            "selection_basis": basis,
            "runtime_fallback": False,
            "mutates_rejected_candidate": False,
        }
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        causal.validate_scenario_contract(row)
        capture.validate_scenario_assets(row)
        rows.append(row)

    text = canonical_lines(rows)
    input_path = OUTPUT_ROOT / "input.jsonl"
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(input_path, text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": (
            "xonotic-stage2-secondary-replenishment-manifest-v1"
        ),
        "source_commit": rows[0]["source_commit_required"],
        "data_spec_sha256": capture.sha256_file(
            ROOT / "XONOTIC_DATA_SPEC_V2.md"
        ),
        "formal_collection_authorized": False,
        "training_admitted": False,
        "replacement_policy": {
            "runtime_fallback": False,
            "original_rejects_preserved": True,
            "new_candidate_identity_required": True,
        },
        "review": {
            "rows": len(rows),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "path": str(shard_path),
                    "rows": len(rows),
                    "sha256": hashlib.sha256(
                        text.encode("utf-8")
                    ).hexdigest(),
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
        json.dumps(
            {
                "rows": len(rows),
                "episode_ids": [row["episode_id"] for row in rows],
                "output_root": str(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
