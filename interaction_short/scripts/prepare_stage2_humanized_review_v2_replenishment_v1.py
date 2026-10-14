                      
"""Build the immutable Stage-2 humanized-review v2 replenishment cohort.

The original v2 manifest and its seven fail-closed semantic rejects remain
untouched.  This manifest contains only preregistered replacement candidates
with larger static-certification margins.  Crylink uses separated primary
press/release windows because its stock primary attack is wait-release gated.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage2_humanized_review_v2 as review_v2              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
BASE_MANIFEST = ROOT / "manifests/stage2_humanized_review_v2/input.jsonl"
OUTPUT_ROOT = (
    ROOT
    / "manifests/stage2_humanized_review_v2_replenishment_v1"
)
SOURCE_COMMIT = review_v2.SOURCE_COMMIT
SHARD_COUNT = 2
MANIFEST_SCHEMA = (
    "xonotic-stage2-humanized-review-replenishment-manifest-v1"
)
DESIGN_SCHEMA = (
    "xonotic-stage2-humanized-review-replenishment-design-v1"
)
SELECTION_RULE = (
    "replace_only_v2_fail_closed_semantic_rejects_with_"
    "preregistered_high_margin_static_candidates_v1"
)

                                                                          
                                                                            
                         
CORRECTIONS: dict[str, dict[str, Any]] = {
    "s2humanv2_g01_blaster_pass_offset_b": {
        "reason": "increase_near_edge_fire_margin",
        "motor_seed": 20_000_051,
        "schedule": {
            "fire_yaw_offset_deg": 6.4,
            "fire_pitch_offset_deg": 1.2,
            "minimum_fire_error_deg": 3.75,
            "miss_magnitude_bin": "medium",
        },
    },
    "s2humanv2_g02_shotgun_sustained_tracking": {
        "reason": "increase_prefire_tracking_margin",
        "motor_seed": 20_100_300,
    },
    "s2humanv2_g06_crylink_delayed_acquisition": {
        "reason": "stock_crylink_primary_requires_release",
        "motor_seed": 20_200_133,
        "fire_ticks": [184, 236],
    },
    "s2humanv2_g06_crylink_pass_offset_b": {
        "reason": "increase_live_direction_and_offset_margin",
        "motor_seed": 20_300_247,
        "schedule": {
            "fire_yaw_offset_deg": 7.6,
            "fire_pitch_offset_deg": -7.8,
            "minimum_fire_error_deg": 5.5,
            "miss_magnitude_bin": "medium",
        },
    },
    "s2humanv2_g06_crylink_sustained_tracking": {
        "reason": (
            "increase_prefire_tracking_margin_and_use_release_taps"
        ),
        "motor_seed": 20_400_298,
        "fire_ticks": [168, 220, 272],
    },
    "s2humanv2_g06_crylink_track_loss_reacquire": {
        "reason": (
            "increase_pre_loss_acquisition_margin_and_use_release_taps"
        ),
        "motor_seed": 20_500_180,
        "fire_ticks": [264, 316],
    },
    "s2humanv2_g09_devastator_sustained_tracking": {
        "reason": "increase_prefire_tracking_margin",
        "motor_seed": 20_600_296,
    },
}


def crylink_multi_tap(ticks: list[int]) -> dict[str, Any]:
    return {
        "schema_version": causal.FIRE_PROGRAM_SCHEMA,
        "name": "multi_tap",
        "weapon_fire_family": "spaced_tap",
        "windows": [
            {
                "start_output_tick": tick,
                "duration_ticks": 2,
            }
            for tick in ticks
        ],
        "expected_min_fire_events": len(ticks),
        "expected_max_fire_events": len(ticks),
        "requires_multiple_fire_events": True,
        "selection_uses_authoritative_events": True,
    }


def assert_safety_margin(
    row: dict[str, Any], certificate: dict[str, Any]
) -> None:
    policy = row["causal_design"]["aim_policy"]
    details = certificate["details"]
    checks: dict[str, bool] = {
        "static_certificate_passed": certificate["passed"] is True,
        "direct_smooth_motor": (
            row["causal_design"]["aim_motor_profile"]["style"]
            == "direct_smooth"
        ),
    }
    if policy == "pass_offset":
        vector = details["first_requested_fire_screen_vector_deg"]
        checks.update(
            {
                "fire_error_margin": (
                    details["requested_fire_error_min_deg"] >= 5.0
                ),
                "direction_margin": (
                    vector["direction_error_deg"] <= 20.0
                ),
            }
        )
    elif policy == "sustained_tracking":
        checks["prefire_tracking_margin"] = (
            details["centered_prefire_tracking_fraction"] >= 0.95
        )
    elif policy == "track_loss_reacquire":
        checks.update(
            {
                "pre_loss_acquisition_margin": (
                    details["acquired_frames_before_pause"] >= 24
                ),
                "natural_loss_margin": (
                    details["natural_loss_frames"] >= 12
                ),
                "reacquisition_margin": (
                    details["first_reacquisition_output_tick"] <= 230
                ),
            }
        )
    elif policy == "delayed_acquisition":
        checks["delayed_acquisition_margin"] = (
            details["first_centered_output_tick"] <= 140
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "stage2_humanized_replenishment_margin_failed",
            capture.canonical_json(
                {"episode_id": row["episode_id"], "checks": checks}
            ),
        )


def materialize() -> list[dict[str, Any]]:
    base_rows = {
        row["episode_id"]: row
        for row in capture.load_jsonl(BASE_MANIFEST)
    }
    if set(CORRECTIONS) - set(base_rows):
        raise capture.CaptureFailure(
            "stage2_humanized_replenishment_base_rows_missing",
            capture.canonical_json(
                sorted(set(CORRECTIONS) - set(base_rows))
            ),
        )

    rows: list[dict[str, Any]] = []
    remediation_distribution: Counter[str] = Counter()
    for ordinal, (base_episode_id, correction) in enumerate(
        CORRECTIONS.items()
    ):
        base = base_rows[base_episode_id]
        row = copy.deepcopy(base)
        row.update(
            {
                "episode_id": f"{base_episode_id}_r1",
                "category": (
                    "stage2_humanized_review_v2_replenishment_v1_"
                    f"{row['causal_design']['aim_policy']}"
                ),
                "candidate_kind": (
                    "stage2_humanized_burst_miss_review_v2_"
                    "replenishment_v1"
                ),
                "candidate_status": (
                    "high_margin_static_certified_pending_live_capture"
                ),
                "training_stage": (
                    "stage2_humanized_review_v2_replenishment_v1_only"
                ),
                "canary_role": (
                    f"{row['canary_role']}_replenishment_r1"
                ),
                "assigned_shard": ordinal % SHARD_COUNT,
                "shard_count": SHARD_COUNT,
                "target_ordinal": 10_000 + ordinal,
            }
        )
        design = row["causal_design"]
        original_exogenous_sha256 = row["exogenous_contract_sha256"]
        schedule_updates = correction.get("schedule") or {}
        design["aim_schedule"].update(schedule_updates)
        if row["causal_design"]["aim_policy"] == "pass_offset":
            miss = row["humanized_review_design"]["miss_treatment"]
            for name in (
                "fire_yaw_offset_deg",
                "fire_pitch_offset_deg",
                "minimum_fire_error_deg",
                "miss_magnitude_bin",
            ):
                if name in schedule_updates:
                    miss[name] = schedule_updates[name]
            row["policy_labels"]["miss_magnitude_bin"] = design[
                "aim_schedule"
            ]["miss_magnitude_bin"]

        fire_ticks = correction.get("fire_ticks")
        if fire_ticks is not None:
            if row["weapon"] != "Crylink":
                raise AssertionError(row["episode_id"])
            design["fire_program"] = crylink_multi_tap(fire_ticks)
            design["fire_output_ticks"] = list(fire_ticks)
            row["humanized_review_design"][
                "firing_program_category"
            ] = "complex"
            row["policy_labels"]["fire_program_category"] = "complex"

        motor_seed = int(correction["motor_seed"])
        design["aim_motor_profile"] = (
            causal.humanized_aim_motor_profile(
                motor_seed, "direct_smooth"
            )
        )
        row["policy_labels"]["aim_motor_style"] = "direct_smooth"
        row["exogenous_contract_sha256"] = (
            causal.exogenous_contract_sha256(row)
        )
        if row["exogenous_contract_sha256"] != original_exogenous_sha256:
            raise capture.CaptureFailure(
                "stage2_humanized_replenishment_exogenous_drift",
                row["episode_id"],
            )

        certificate = review_v2.static_action_certificate(row)
        assert_safety_margin(row, certificate)
        row["humanized_review_design"].update(
            {
                "schema_version": DESIGN_SCHEMA,
                "selection_rule": SELECTION_RULE,
                "base_episode_id": base_episode_id,
                "base_row_sha256": hashlib.sha256(
                    capture.canonical_json(base).encode("utf-8")
                ).hexdigest(),
                "remediation_reason": correction["reason"],
                "motor_style": "direct_smooth",
                "motor_candidate_attempt": None,
                "static_action_certificate": certificate,
                "runtime_action_fallback": False,
                "runtime_geometry_fallback": False,
                "live_state_used_during_action_generation": False,
                "formal_collection_authorized": False,
            }
        )
        causal.validate_scenario_contract(row)
        remediation_distribution[correction["reason"]] += 1
        rows.append(row)

    input_text = review_v2.canonical_lines(rows)
    review_v2.write_once_or_verify(
        OUTPUT_ROOT / "input.jsonl", input_text
    )
    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(SHARD_COUNT):
        shard_rows = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        shard_text = review_v2.canonical_lines(shard_rows)
        shard_path = (
            OUTPUT_ROOT
            / "shards"
            / f"shard-{shard_index:03d}-of-{SHARD_COUNT:03d}.jsonl"
        )
        review_v2.write_once_or_verify(shard_path, shard_text)
        shard_metadata.append(
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
        "schema_version": MANIFEST_SCHEMA,
        "selection_rule": SELECTION_RULE,
        "source_commit": SOURCE_COMMIT,
        "data_spec_sha256": rows[0]["data_spec_sha256"],
        "base_manifest": {
            "path": str(BASE_MANIFEST.relative_to(ROOT)),
            "sha256": capture.sha256_file(BASE_MANIFEST),
        },
        "rows": len(rows),
        "shard_count": SHARD_COUNT,
        "shards": shard_metadata,
        "review": {
            "rows": len(rows),
            "shard_count": SHARD_COUNT,
            "shards": shard_metadata,
        },
        "weapon_distribution": dict(
            Counter(row["weapon"] for row in rows)
        ),
        "policy_distribution": dict(
            Counter(
                row["causal_design"]["aim_policy"] for row in rows
            )
        ),
        "remediation_distribution": dict(
            remediation_distribution
        ),
        "crylink_primary_semantics": {
            "source_behavior": "waitrelease",
            "input_program": "separated_press_release_press_windows",
            "authoritative_event_count_required": True,
        },
        "formal_collection_authorized": False,
        "training_admitted": False,
        "runtime_action_fallback": False,
        "runtime_geometry_fallback": False,
    }
    review_v2.write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        json.dumps(
            {
                "output_root": str(OUTPUT_ROOT),
                "rows": len(rows),
                "weapons": dict(
                    Counter(row["weapon"] for row in rows)
                ),
                "policies": dict(
                    Counter(
                        row["causal_design"]["aim_policy"]
                        for row in rows
                    )
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
