                      
"""Audit the 81-row Stage-2 formal-shaped canary v1."""

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

import prepare_stage2_formal_canary_v1 as design              
import xonotic_capture as capture              


MANIFEST = ROOT / "manifests/stage2_formal_canary_v1/input.jsonl"
OUTPUT_ROOT = ROOT / "stage2_formal_canary_v1_output"
AUDIT_PATH = OUTPUT_ROOT / "FORMAL_CANARY_AUDIT.json"
EXPECTED_ROWS = 81


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def journal_rows(name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (OUTPUT_ROOT / "manifests/shards").glob(
            f"shard-*-of-*/{name}.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def package_hashes_pass(
    accepted: dict[str, Any], package: Path
) -> bool:
    expected = accepted.get("package_sha256") or {}
    return bool(expected) and all(
        (package / name).is_file()
        and capture.sha256_file(package / name) == digest
        for name, digest in expected.items()
    )


def actual_target_outcome(shots: pd.DataFrame) -> str:
    if shots.empty:
        return "no_fire"
    if shots["target_killed"].astype(bool).any():
        return "kill"
    if shots["target_hit"].astype(bool).any():
        return "hit_survive"
    return "miss"


def audit(require_complete: bool) -> dict[str, Any]:
    planned = capture.load_jsonl(MANIFEST)
    planned_by_id = {str(row["episode_id"]): row for row in planned}
    accepted_journal = journal_rows("accepted")
    reject_journal = journal_rows("rejects")
    terminal = [
        row
        for row in reject_journal
        if row.get("terminal") is True
        and row.get("retryable") is not True
    ]
    accepted_counts = Counter(
        str(row["episode_id"]) for row in accepted_journal
    )
    terminal_counts = Counter(str(row["episode_id"]) for row in terminal)
    accepted_by_id = {
        str(row["episode_id"]): row for row in accepted_journal
    }
    duplicate_accepted = sorted(
        episode_id
        for episode_id, count in accepted_counts.items()
        if count != 1
    )
    duplicate_terminal = sorted(
        episode_id
        for episode_id, count in terminal_counts.items()
        if count != 1
    )
    conflicts = sorted(set(accepted_counts) & set(terminal_counts))
    missing = sorted(set(planned_by_id) - set(accepted_by_id))
    unknown = sorted(set(accepted_by_id) - set(planned_by_id))

    results: list[dict[str, Any]] = []
    actual_outcomes: Counter[str] = Counter()
    planned_outcomes: Counter[str] = Counter()
    weapon_shots: defaultdict[str, Counter[str]] = defaultdict(Counter)
    recipe_matrix: defaultdict[str, Counter[str]] = defaultdict(Counter)

    for episode_id in sorted(set(planned_by_id) & set(accepted_by_id)):
        scenario = planned_by_id[episode_id]
        accepted = accepted_by_id[episode_id]
        package = Path(str(accepted["episode_path"]))
        episode = json.loads(
            (package / "episode.json").read_text(encoding="utf-8")
        )
        qa = json.loads(
            (package / "qa.json").read_text(encoding="utf-8")
        )
        causal = json.loads(
            (package / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        frames = pd.read_parquet(package / "frames.parquet")
        actions = pd.read_parquet(package / "model_actions.parquet")
        states = pd.read_parquet(package / "states.parquet")
        events = pd.read_parquet(package / "events.parquet")
        shots = pd.read_parquet(package / "shot_outcomes.parquet")
        recipe = str(
            scenario["formal_canary_design"]["outcome_recipe"]
        )
        actual = actual_target_outcome(shots)
        planned_outcomes[recipe] += 1
        actual_outcomes[actual] += 1
        recipe_matrix[recipe][actual] += 1
        weapon = str(scenario["weapon"])
        hit_count = int(shots["target_hit"].astype(bool).sum())
        kill_count = int(shots["target_killed"].astype(bool).sum())
        weapon_shots[weapon]["fires"] += len(shots)
        weapon_shots[weapon]["hits"] += hit_count
        weapon_shots[weapon]["kills"] += kill_count
        gates = qa.get("gates") or {}
        hard_gates = qa.get("hard_gates") or {}
        audio = qa.get("audio") or {}
        player_checks = (
            (causal.get("player_path") or {}).get("checks") or {}
        )
        target_columns = {
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
        target_columns_present = target_columns <= set(shots.columns)
        target_entity = int(causal["per_shot"]["target_entity"])
        target_entity_exact = bool(
            shots.empty
            or (
                pd.to_numeric(
                    shots["target_entity"], errors="raise"
                ).astype(int)
                == target_entity
            ).all()
        )
        linked_target_deaths = events[
            (events["event"] == "damage")
            & (
                pd.to_numeric(events["target"], errors="coerce")
                == target_entity
            )
            & (
                pd.to_numeric(events["killed"], errors="coerce")
                == 1
            )
        ]
        checks = {
            "identity": episode.get("episode_id") == episode_id,
            "package_hashes": package_hashes_pass(accepted, package),
            "accepted": qa.get("accepted") is True,
            "capture_valid": qa.get("capture_valid") is True,
            "all_hard_gates": bool(hard_gates)
            and all(bool(value) for value in hard_gates.values()),
            "video_320": qa.get("video", {}).get("frames")
            == capture.OUTPUT_TICKS
            and len(frames) == capture.OUTPUT_TICKS,
            "audio_240000": audio.get("samples_per_channel")
            == capture.AUDIO_SAMPLES,
            "audio_non_silent": float(
                audio.get("nonzero_fraction", 0.0)
            )
            > 0.0,
            "mapping_exact": qa.get("mapping", {}).get("mapped_frames")
            == capture.OUTPUT_TICKS
            and frames["episode_server_tick"].astype(int).tolist()
            == list(range(capture.WARMUP_TICKS, capture.TOTAL_TICKS)),
            "actions_320": len(actions) == capture.OUTPUT_TICKS,
            "states_384": len(states) == capture.TOTAL_TICKS,
            "renderer_h200": str(
                qa.get("runtime", {}).get("renderer", "")
            ).startswith("NVIDIA H200"),
            "cpu_x264_medium_16_flac": all(
                gates.get(name) is True
                for name in (
                    "encoded_flac_s16_stereo_48khz",
                    "encoded_h264_high",
                    "encoded_yuv420p",
                )
            )
            and qa.get("runtime", {}).get("x264_preset") == "medium"
            and int(qa.get("runtime", {}).get("x264_threads", -1)) == 16,
            "hud_and_gametype": all(
                gates.get(name) is True
                for name in (
                    "minimal_hud_policy",
                    "server_objective_waypoints_disabled",
                    "gametype_exact",
                )
            ),
            "trace_and_collision": all(
                player_checks.get(name) is True
                for name in (
                    "trace_rows_exact",
                    "trace_position_error_p95",
                    "trace_position_error_max",
                    "collision_policy_passed",
                    "ordinary_movement_clear",
                    "no_unintended_fall",
                )
            ),
            "causal_v9": causal.get("passed") is True,
            "target_columns": target_columns_present,
            "target_entity_exact": target_entity_exact,
            "one_shot_row_per_fire": len(shots)
            == int(
                causal["fire_program"][
                    "authoritative_fire_event_count"
                ]
            ),
            "target_observation_complete": bool(
                shots.empty
                or shots["target_observation_complete"].astype(bool).all()
            ),
            "not_right_censored": bool(
                shots.empty
                or not shots["right_censored"].astype(bool).any()
            ),
            "target_kill_linked_death": (
                len(linked_target_deaths) >= 1
                if actual == "kill"
                else len(linked_target_deaths) == 0
            ),
            "outcome_not_admission": scenario["acceptance"][
                "actual_outcome"
            ]
            is None
            and scenario["formal_canary_design"][
                "outcome_recipe_is_individual_admission_gate"
            ]
            is False,
            "no_runtime_fallback": all(
                scenario["formal_canary_design"][name] is False
                for name in (
                    "runtime_action_fallback",
                    "runtime_geometry_fallback",
                    "runtime_outcome_fallback",
                )
            ),
        }
        results.append(
            {
                "episode_id": episode_id,
                "episode_path": str(package),
                "weapon": weapon,
                "arm": scenario["causal_design"]["aim_policy"],
                "planned_outcome_recipe": recipe,
                "actual_target_outcome": actual,
                "fire_events": len(shots),
                "target_hits": hit_count,
                "target_kills": kill_count,
                "recipe_realized": recipe == actual,
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    weapon_summary: dict[str, Any] = {}
    for weapon in design.WEAPONS:
        counts = weapon_shots[weapon]
        fires = int(counts["fires"])
        hits = int(counts["hits"])
        minimum, maximum = design.v4.TARGET_HIT_RATE_BANDS[weapon]
        rate = hits / fires if fires else None
        weapon_summary[weapon] = {
            "fire_events": fires,
            "target_hits": hits,
            "target_kills": int(counts["kills"]),
            "target_hit_rate": rate,
            "target_band_minimum": minimum,
            "target_band_maximum": maximum,
            "approximate_band_passed": bool(
                rate is not None
                and minimum - 0.05 <= rate <= maximum + 0.05
            ),
        }
    kill_results = [
        row for row in results if row["planned_outcome_recipe"] == "kill"
    ]
    checks = {
        "planned_81": len(planned) == EXPECTED_ROWS,
        "accepted_81": len(accepted_by_id) == EXPECTED_ROWS,
        "complete": not missing and not terminal,
        "exactly_once": not duplicate_accepted
        and not duplicate_terminal
        and not conflicts
        and not unknown,
        "all_artifact_qa": len(results) == EXPECTED_ROWS
        and all(row["passed"] for row in results),
        "all_nine_kill_recipes_realized": len(kill_results) == 9
        and all(
            row["actual_target_outcome"] == "kill"
            and row["target_kills"] == 1
            for row in kill_results
        ),
        "no_kill_outside_kill_recipe": all(
            row["target_kills"] == 0
            for row in results
            if row["planned_outcome_recipe"] != "kill"
        ),
        "all_no_fire_recipes_realized": all(
            row["actual_target_outcome"] == "no_fire"
            for row in results
            if row["planned_outcome_recipe"] == "no_fire"
        ),
        "outcome_not_used_for_admission": all(
            row["checks"]["outcome_not_admission"] for row in results
        ),
    }
    result = {
        "schema_version": "xonotic-stage2-formal-canary-audit-v1",
        "manifest": str(MANIFEST),
        "manifest_sha256": capture.sha256_file(MANIFEST),
        "planned_episodes": len(planned),
        "accepted_episodes": len(accepted_by_id),
        "terminal_rejects": len(terminal),
        "missing_episode_ids": missing,
        "duplicate_accepted_episode_ids": duplicate_accepted,
        "duplicate_terminal_episode_ids": duplicate_terminal,
        "accepted_terminal_conflicts": conflicts,
        "planned_outcome_distribution": dict(planned_outcomes),
        "actual_outcome_distribution": dict(actual_outcomes),
        "recipe_actual_matrix": {
            recipe: dict(values)
            for recipe, values in sorted(recipe_matrix.items())
        },
        "weapon_summary": weapon_summary,
        "episode_results": results,
        "checks": checks,
        "complete": checks["complete"],
        "passed": all(checks.values()),
    }
    atomic_text(
        AUDIT_PATH, json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    if require_complete and not result["passed"]:
        raise capture.CaptureFailure(
            "stage2_formal_canary_v1_audit_failed",
            capture.canonical_json(
                {
                    "checks": checks,
                    "missing": missing,
                    "terminal_rejects": len(terminal),
                }
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
                "audit": str(AUDIT_PATH),
                "accepted": result["accepted_episodes"],
                "planned": result["planned_episodes"],
                "terminal_rejects": result["terminal_rejects"],
                "actual_outcomes": result["actual_outcome_distribution"],
                "kill_recipe": result["recipe_actual_matrix"].get("kill", {}),
                "complete": result["complete"],
                "passed": result["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
