                      
"""Audit the manifest-policy-corrected Vortex V5r2 artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_stage2_vortex_calibration_review_v5 as v5              
import xonotic_capture as capture              


MANIFEST_ROOT = (
    ROOT / "manifests/stage2_vortex_calibration_review_v5r2"
)
OUTPUT_ROOT = ROOT / "stage2_vortex_calibration_review_v5r2_output"
AUDIT_PATH = OUTPUT_ROOT / "VORTEX_CALIBRATION_AUDIT.json"


def audit(require_complete: bool) -> dict:
    v5.MANIFEST_ROOT = MANIFEST_ROOT
    v5.MANIFEST = MANIFEST_ROOT / "input.jsonl"
    v5.OUTPUT_ROOT = OUTPUT_ROOT
    v5.AUDIT_PATH = AUDIT_PATH
    result = v5.audit(False)
    result["schema_version"] = (
        "xonotic-stage2-vortex-calibration-artifact-audit-v5r2"
    )
    result["manifest_policy_correction_only"] = True
    v5.base.atomic_text(
        AUDIT_PATH,
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    if require_complete and not result["passed"]:
        raise capture.CaptureFailure(
            "stage2_vortex_calibration_v5r2_audit_failed",
            capture.canonical_json(result["v5_checks"]),
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.require_complete)
    vortex = result["weapon_summary"].get("Vortex") or {}
    print(
        capture.canonical_json(
            {
                "audit": str(AUDIT_PATH),
                "accepted": result["accepted_episodes"],
                "planned": result["planned_episodes"],
                "rejects": result["terminal_rejects"],
                "fire_events": vortex.get("fire_events"),
                "target_hit_fire_events": vortex.get(
                    "target_hit_fire_events"
                ),
                "target_hit_rate": vortex.get("target_hit_rate"),
                "complete": result["complete"],
                "passed": result["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
