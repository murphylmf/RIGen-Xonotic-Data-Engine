                      
"""Audit the effective 96-row Stage-2 formal canary and replacement lineage."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xonotic_capture as capture              


MOVING_MANIFEST = ROOT / "manifests/stage2_formal_canary_v1/input.jsonl"
EXTENSION_MANIFEST = (
    ROOT / "manifests/stage2_formal_stationary_extension_v1/input.jsonl"
)
RECOVERY_V1_MANIFEST = (
    ROOT / "manifests/stage2_formal_canary_recovery_v1/input.jsonl"
)
RECOVERY_V2_MANIFEST = (
    ROOT / "manifests/stage2_formal_canary_recovery_v2/input.jsonl"
)
RECOVERY_V3_MANIFEST = (
    ROOT / "manifests/stage2_formal_canary_recovery_v3/input.jsonl"
)
OUTPUTS = {
    "moving_12lane": ROOT / "stage2_formal_canary_v1_output",
    "recovery_v1_8lane": ROOT / "stage2_formal_canary_recovery_v1_output",
    "recovery_v2_8lane": ROOT / "stage2_formal_canary_recovery_v2_output",
    "recovery_v3_8lane": ROOT / "stage2_formal_canary_recovery_v3_output",
}
AUDIT_PATH = (
    ROOT
    / "stage2_formal_canary_v1_output"
    / "FORMAL_CANARY_EFFECTIVE_AUDIT.json"
)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def journals(root: Path, name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (root / "manifests/shards").glob(
            f"shard-*-of-*/{name}.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def accepted_index() -> tuple[dict[str, dict], list[str]]:
    index: dict[str, dict] = {}
    duplicates: list[str] = []
    for run_name, root in OUTPUTS.items():
        for row in journals(root, "accepted"):
            episode_id = row["episode_id"]
            if episode_id in index:
                duplicates.append(episode_id)
            index[episode_id] = {**row, "run_name": run_name}
    return index, sorted(duplicates)


def replacement_index(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in capture.load_jsonl(path):
        replacement = row.get("operational_replacement") or {}
        old_id = replacement.get("replacement_for")
        if old_id:
            result[str(old_id)] = row
    return result


def package_hashes_pass(accepted: dict, package: Path) -> bool:
    hashes = accepted.get("package_sha256") or {}
    return bool(hashes) and all(
        (package / name).is_file()
        and capture.sha256_file(package / name) == digest
        for name, digest in hashes.items()
    )


def actual_outcome(shots: pd.DataFrame) -> str:
    if shots.empty:
        return "no_fire"
    if shots["target_killed"].astype(bool).any():
        return "kill"
    if shots["target_hit"].astype(bool).any():
        return "hit_survive"
    return "miss"


def inspect_episode(
    logical: dict,
    artifact_scenario: dict,
    accepted: dict,
) -> dict[str, Any]:
    package = Path(accepted["episode_path"])
    qa = json.loads((package / "qa.json").read_text())
    causal = json.loads(
        (package / "causal_interaction.json").read_text()
    )
    frames = pd.read_parquet(package / "frames.parquet")
    actions = pd.read_parquet(package / "model_actions.parquet")
    states = pd.read_parquet(package / "states.parquet")
    shots = pd.read_parquet(package / "shot_outcomes.parquet")
    events = pd.read_parquet(package / "events.parquet")
    recipe_design = (
        logical.get("formal_canary_design")
        or logical.get("formal_design")
        or {}
    )
    recipe = recipe_design["outcome_recipe"]
    actual = actual_outcome(shots)
    gates = qa.get("gates") or {}
    player_checks = causal["player_path"]["checks"]
    enemy_checks = causal["enemy_random_policy"]["checks"]
    required_shot_columns = {
        "target_entity",
        "target_hit",
        "target_outcome",
        "target_damage_count",
        "target_damage_amount",
        "target_killed",
        "target_direct",
        "target_splash",
        "target_pellet",
        "target_observation_complete",
        "right_censored",
    }
    target_entity = int(causal["per_shot"]["target_entity"])
    events = events.reindex(
        columns=list(
            dict.fromkeys(
                [*events.columns, "event", "target", "killed"]
            )
        )
    )
    if events.empty:
        linked_deaths = pd.DataFrame()
    else:
        linked_deaths = events[
            (events["event"] == "damage")
            & (
                pd.to_numeric(events["target"], errors="coerce")
                == target_entity
            )
            & (
                pd.to_numeric(events["killed"], errors="coerce") == 1
            )
        ]
    artifact_design = (
        artifact_scenario.get("formal_canary_design")
        or artifact_scenario.get("formal_design")
        or {}
    )
    checks = {
        "package_hashes": package_hashes_pass(accepted, package),
        "accepted": qa.get("accepted") is True,
        "all_hard_gates": bool(qa.get("hard_gates"))
        and all(qa["hard_gates"].values()),
        "video_320": qa["video"]["frames"] == 320
        and len(frames) == 320,
        "audio_240000": qa["audio"]["samples_per_channel"] == 240_000,
        "mapping_exact": qa["mapping"]["mapped_frames"] == 320
        and frames["episode_server_tick"].astype(int).tolist()
        == list(range(64, 384)),
        "actions_320_states_384": len(actions) == 320
        and len(states) == 384,
        "renderer_h200": str(
            qa["runtime"].get("renderer", "")
        ).startswith("NVIDIA H200"),
        "x264_medium_16_flac": qa["runtime"].get("x264_preset")
        == "medium"
        and int(qa["runtime"].get("x264_threads", -1)) == 16
        and gates.get("encoded_flac_s16_stereo_48khz") is True,
        "hud_gametype": all(
            gates.get(name) is True
            for name in (
                "minimal_hud_policy",
                "server_objective_waypoints_disabled",
                "gametype_exact",
            )
        ),
        "causal_passed": causal.get("passed") is True,
        "player_path_safe": all(player_checks.values()),
        "enemy_path_safe": all(enemy_checks.values()),
        "shot_columns": required_shot_columns <= set(shots.columns),
        "one_shot_row_per_fire": len(shots)
        == causal["fire_program"]["authoritative_fire_event_count"],
        "observation_complete": bool(
            shots.empty
            or shots["target_observation_complete"].astype(bool).all()
        ),
        "not_right_censored": bool(
            shots.empty
            or not shots["right_censored"].astype(bool).any()
        ),
        "kill_linked_death": (
            len(linked_deaths) >= 1
            if actual == "kill"
            else len(linked_deaths) == 0
        ),
        "outcome_not_admission": logical["acceptance"][
            "actual_outcome"
        ]
        is None
        and recipe_design[
            "outcome_recipe_is_individual_admission_gate"
        ]
        is False,
        "no_runtime_fallback": all(
            artifact_design[name] is False
            for name in (
                "runtime_action_fallback",
                "runtime_geometry_fallback",
                "runtime_outcome_fallback",
            )
        ),
    }
    return {
        "logical_episode_id": logical["episode_id"],
        "artifact_episode_id": artifact_scenario["episode_id"],
        "run_name": accepted["run_name"],
        "weapon": logical["weapon"],
        "planned_outcome_recipe": recipe,
        "actual_target_outcome": actual,
        "target_hits": (
            int(shots["target_hit"].astype(bool).sum())
            if not shots.empty
            else 0
        ),
        "target_kills": (
            int(shots["target_killed"].astype(bool).sum())
            if not shots.empty
            else 0
        ),
        "checks": checks,
        "passed": all(checks.values()),
    }


def audit(require_complete: bool) -> dict[str, Any]:
    moving = capture.load_jsonl(MOVING_MANIFEST)
    extension = capture.load_jsonl(EXTENSION_MANIFEST)
    recovery_v1 = capture.load_jsonl(RECOVERY_V1_MANIFEST)
    recovery_v2 = capture.load_jsonl(RECOVERY_V2_MANIFEST)
    recovery_v3 = capture.load_jsonl(RECOVERY_V3_MANIFEST)
    accepted, duplicate_artifacts = accepted_index()
    replacements_v1 = replacement_index(RECOVERY_V1_MANIFEST)
    replacements_v2 = replacement_index(RECOVERY_V2_MANIFEST)
    replacements_v3 = replacement_index(RECOVERY_V3_MANIFEST)
    artifact_scenarios = {
        row["episode_id"]: row
        for row in moving
        + extension
        + recovery_v1
        + recovery_v2
        + recovery_v3
    }
    lineage: list[tuple[dict, dict, dict]] = []
    missing: list[str] = []
    for logical in moving:
        artifact = logical
        if logical["episode_id"] not in accepted:
            artifact = replacements_v1.get(logical["episode_id"])
        if artifact is None or artifact["episode_id"] not in accepted:
            missing.append(logical["episode_id"])
            continue
        lineage.append(
            (logical, artifact, accepted[artifact["episode_id"]])
        )
    for logical in extension:
        artifact = logical
        if logical["episode_id"] not in accepted:
            artifact = replacements_v2.get(logical["episode_id"])
        if artifact is None or artifact["episode_id"] not in accepted:
            artifact = replacements_v3.get(logical["episode_id"])
        if artifact is None or artifact["episode_id"] not in accepted:
            missing.append(logical["episode_id"])
            continue
        lineage.append(
            (logical, artifact, accepted[artifact["episode_id"]])
        )
    results = [
        inspect_episode(logical, artifact, accepted_row)
        for logical, artifact, accepted_row in lineage
    ]
    planned = moving + extension
    planned_outcomes = Counter(
        (
            row.get("formal_canary_design")
            or row.get("formal_design")
        )["outcome_recipe"]
        for row in planned
    )
    actual_outcomes = Counter(
        row["actual_target_outcome"] for row in results
    )
    recipe_matrix: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in results:
        recipe_matrix[row["planned_outcome_recipe"]][
            row["actual_target_outcome"]
        ] += 1
    kill_rows = [
        row
        for row in results
        if row["planned_outcome_recipe"] == "kill"
    ]
    moving_kill_rows = [
        row
        for row in kill_rows
        if row["logical_episode_id"].startswith("s2fcv1_g")
    ]
    checks = {
        "logical_96": len(planned) == 96,
        "effective_96": len(results) == 96 and not missing,
        "exactly_once_lineage": len(
            {row["logical_episode_id"] for row in results}
        )
        == len(results)
        and len({row["artifact_episode_id"] for row in results})
        == len(results)
        and not duplicate_artifacts,
        "all_artifact_qa": len(results) == 96
        and all(row["passed"] for row in results),
        "moving_kill_recipes_9_of_9": len(moving_kill_rows) == 9
        and all(
            row["actual_target_outcome"] == "kill"
            and row["target_kills"] == 1
            for row in moving_kill_rows
        ),
        "stationary_kill_calibration_retained_without_selection": (
            len(kill_rows) == 11
            and sum(
                row["actual_target_outcome"] == "kill"
                for row in kill_rows
            )
            >= 9
        ),
        "no_kill_outside_kill_recipe": all(
            row["target_kills"] == 0
            for row in results
            if row["planned_outcome_recipe"] != "kill"
        ),
        "no_fire_recipes_realized": all(
            row["actual_target_outcome"] == "no_fire"
            for row in results
            if row["planned_outcome_recipe"] == "no_fire"
        ),
        "outcome_not_used_for_admission": all(
            row["checks"]["outcome_not_admission"] for row in results
        ),
        "twelve_lane_failed_then_eight": any(
            row["run_name"]
            in {"recovery_v2_8lane", "recovery_v3_8lane"}
            for row in results
        ),
    }
    result = {
        "schema_version": "xonotic-stage2-formal-canary-effective-audit-v1",
        "moving_manifest": str(MOVING_MANIFEST),
        "stationary_extension_manifest": str(EXTENSION_MANIFEST),
        "logical_episodes": len(planned),
        "effective_episodes": len(results),
        "missing_logical_episode_ids": missing,
        "duplicate_artifact_episode_ids": duplicate_artifacts,
        "planned_outcome_distribution": dict(planned_outcomes),
        "actual_outcome_distribution": dict(actual_outcomes),
        "recipe_actual_matrix": {
            key: dict(value)
            for key, value in sorted(recipe_matrix.items())
        },
        "kill_recipe_actual": dict(recipe_matrix["kill"]),
        "recommended_lanes_per_gpu": 8,
        "x264_preset": "medium",
        "x264_threads": 16,
        "encode_concurrency": 4,
        "formal_runtime_sha256": capture.sha256_file(
            ROOT / "scripts/xonotic_stage2_causal_formal.py"
        ),
        "historical_v4_runtime_sha256": capture.sha256_file(
            ROOT / "scripts/xonotic_stage2_causal.py"
        ),
        "episode_results": results,
        "checks": checks,
        "complete": checks["effective_96"],
        "passed": all(checks.values()),
    }
    atomic_json(AUDIT_PATH, result)
    if require_complete and not result["passed"]:
        raise capture.CaptureFailure(
            "stage2_formal_canary_effective_audit_failed",
            capture.canonical_json(
                {"checks": checks, "missing": missing}
            ),
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.require_complete)
    print(
        capture.canonical_json(
            {
                "logical": result["logical_episodes"],
                "effective": result["effective_episodes"],
                "actual_outcomes": result["actual_outcome_distribution"],
                "kill_recipe_actual": result["kill_recipe_actual"],
                "recommended_lanes": result["recommended_lanes_per_gpu"],
                "complete": result["complete"],
                "passed": result["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
