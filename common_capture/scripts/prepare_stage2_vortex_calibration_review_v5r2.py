                      
"""Policy-name correction for the preflight-rejected Vortex V5 manifest."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_weapon_balanced_review_v4 as v4              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


SOURCE_ROOT = (
    ROOT / "manifests/stage2_vortex_calibration_review_v5"
)
SOURCE_MANIFEST = SOURCE_ROOT / "input.jsonl"
SOURCE_METADATA = SOURCE_ROOT / "MANIFEST_METADATA.json"
OUTPUT_ROOT = (
    ROOT / "manifests/stage2_vortex_calibration_review_v5r2"
)
SHARD_COUNT = 4
KNOWN_NONTRAINING_SPLIT = (
    "stage2_weapon_balanced_nontraining_review"
)


def materialize() -> list[dict[str, Any]]:
    source_rows = capture.load_jsonl(SOURCE_MANIFEST)
    source_metadata = json.loads(
        SOURCE_METADATA.read_text(encoding="utf-8")
    )
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        row = copy.deepcopy(source)
        old_id = str(row["episode_id"])
        new_id = old_id.replace("s2v5_g07_", "s2v5r2_g07_", 1)
        row.update(
            {
                "episode_id": new_id,
                "counterfactual_group_id": (
                    "s2v5r2_g07_vortex"
                ),
                "anchor_id": (
                    "s2v5r2_g07_vortex_twelve_slot"
                ),
                "candidate_kind": (
                    "stage2_vortex_calibration_review_v5r2"
                ),
                "candidate_status": (
                    "static_certified_manifest_policy_corrected_"
                    "pending_live_capture_and_aggregate_rate_audit"
                ),
                "training_stage": (
                    "stage2_vortex_calibration_review_v5r2_only"
                ),
                "canary_role": str(row["canary_role"]).replace(
                    "stage2_vortex_calibration_v5_",
                    "stage2_vortex_calibration_v5r2_",
                    1,
                ),
                "split": KNOWN_NONTRAINING_SPLIT,
            }
        )
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        row["weapon_balanced_review_design"].update(
            {
                "schema_version": (
                    "xonotic-stage2-vortex-calibration-review-"
                    "design-v5r2"
                ),
                "preflight_rejected_source_episode_id": old_id,
                "manifest_policy_correction_only": True,
                "source_split": source["split"],
                "corrected_split": KNOWN_NONTRAINING_SPLIT,
                "outcome_used_for_individual_admission": False,
            }
        )
        causal.validate_scenario_contract(row)
        if causal.causal_action_rows(
            source, retry=0
        ) != causal.causal_action_rows(row, retry=0):
            raise capture.CaptureFailure(
                "stage2_vortex_v5r2_action_drift", new_id
            )
        rows.append(row)

    input_text = v4.canonical_lines(rows)
    v4.write_once_or_verify(
        OUTPUT_ROOT / "input.jsonl", input_text
    )
    shards: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = v4.canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        v4.write_once_or_verify(shard_path, shard_text)
        shards.append(
            {
                "shard_index": shard_index,
                "path": str(shard_path.relative_to(ROOT)),
                "rows": len(shard_rows),
                "sha256": hashlib.sha256(
                    shard_text.encode("utf-8")
                ).hexdigest(),
            }
        )
    metadata = {
        **source_metadata,
        "schema_version": (
            "xonotic-stage2-vortex-calibration-review-"
            "manifest-v5r2"
        ),
        "source_preflight_rejected_manifest": {
            "path": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(SOURCE_MANIFEST),
            "captured_episode_count": 0,
            "rejection_reason": "unknown_nontraining_split_name",
        },
        "manifest_policy_correction_only": True,
        "corrected_split": KNOWN_NONTRAINING_SPLIT,
        "rows": len(rows),
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shards,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "arm_distribution": dict(
            Counter(
                row["causal_design"]["aim_policy"]
                for row in rows
            )
        ),
        "runtime_code": {
            path: capture.sha256_file(ROOT / path)
            for path in (
                "scripts/xonotic_capture.py",
                "scripts/xonotic_stage2_causal.py",
                "scripts/prepare_stage2_vortex_calibration_review_v5r2.py",
            )
        },
    }
    v4.write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        capture.canonical_json(
            {
                "output": str(OUTPUT_ROOT),
                "rows": len(rows),
                "split": KNOWN_NONTRAINING_SPLIT,
                "policy_correction_only": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
