                      
"""Prepare explicit replacements for failed Stage-2 validation candidates.

The failed candidates remain immutable evidence.  Every row here has a new
episode/group/seed and names the independent source geometry selected for the
replacement.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage2_causal_manifests as bootstrap              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
OUTPUT_ROOT = ROOT / "manifests/stage2_causal_replenishment_v1"


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


def pair_by_id(
    pairs: list[dict[str, Any]], episode_id: str
) -> dict[str, Any]:
    matches = [row for row in pairs if row["episode_id"] == episode_id]
    if len(matches) != 1:
        raise capture.CaptureFailure(
            "stage2_replenishment_pair_missing", episode_id
        )
    return matches[0]


def materialize() -> list[dict[str, Any]]:
    pairs, appearances = bootstrap.load_inputs()
    source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()

    designs = (
        {
            "episode_id": "s2repl_approach_techassault_001",
            "group_id": "s2repl_approach_techassault",
            "pair_id": (
                "preflight_pair_techassault_extreme_r0_wp0032_wp0033"
            ),
            "appearance": appearances[0],
            "weapon": "Blaster",
            "policy": "visible_no_response",
            "seed": 15_300_001,
            "motion_name": "approach_retreat",
            "motion_mode": 2,
            "motion_distance": 32.0,
            "replacement_for": "s2enc_001_m2_cert",
            "basis": (
                "independent whole-path-certified radial geometry from "
                "APPROACH_ANCHOR_SCAN.json"
            ),
        },
        {
            "episode_id": "s2repl_crylink_dm_close_001",
            "group_id": "s2repl_crylink_dm_close",
            "pair_id": (
                "preflight_pair_afterslime_close_r0_wp0086_wp0101"
            ),
            "appearance": appearances[5],
            "weapon": "Crylink",
            "policy": "sustained_tracking",
            "seed": 15_300_002,
            "motion_name": "stationary",
            "motion_mode": 0,
            "motion_distance": 0.0,
            "replacement_for": (
                "s2review_g006_p05_sustained_tracking"
            ),
            "basis": (
                "ordinary DM weapon state and independently selected "
                "close visible geometry"
            ),
        },
        {
            "episode_id": "s2repl_devastator_dm_near_001",
            "group_id": "s2repl_devastator_dm_near",
            "pair_id": "preflight_pair_boil_near_r0_wp0012_wp0014",
            "appearance": appearances[8],
            "weapon": "Devastator",
            "policy": "sustained_tracking",
            "seed": 15_300_003,
            "motion_name": "stationary",
            "motion_mode": 0,
            "motion_distance": 0.0,
            "replacement_for": (
                "s2review_g009_p05_sustained_tracking"
            ),
            "basis": (
                "ordinary DM weapon state; NB weapon replacement excluded"
            ),
        },
    )

    rows: list[dict[str, Any]] = []
    for ordinal, design in enumerate(designs):
        row = bootstrap.scenario_row(
            episode_id=design["episode_id"],
            group_id=design["group_id"],
            pair=pair_by_id(pairs, design["pair_id"]),
            appearance=design["appearance"],
            weapon=design["weapon"],
            policy=design["policy"],
            seed=design["seed"],
            motion_name=design["motion_name"],
            motion_mode=design["motion_mode"],
            motion_distance=design["motion_distance"],
            assigned_shard=0,
            shard_count=1,
            source_commit=source_commit,
            candidate_kind="explicit_validation_replenishment",
            weapon_mechanism_mode_eligible=True,
        )
        row["validation_ordinal"] = ordinal
        row["training_stage"] = "stage2_bounded_validation_only"
        row["replacement_contract"] = {
            "schema_version": "xonotic-stage2-replacement-v1",
            "replacement_for_rejected_episode": design[
                "replacement_for"
            ],
            "selection_basis": design["basis"],
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
        "schema_version": "xonotic-stage2-replenishment-manifest-v1",
        "source_commit": source_commit,
        "data_spec_sha256": capture.sha256_file(bootstrap.DATA_SPEC),
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
                "formal_collection_authorized": False,
                "training_admitted": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
