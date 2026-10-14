                      
"""Audit V3 Stage-2 weapon balance using authoritative target damage."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


MANIFEST = (
    ROOT / "manifests/stage2_weapon_balanced_review_v3/input.jsonl"
)
METADATA = (
    ROOT
    / "manifests/stage2_weapon_balanced_review_v3"
    / "MANIFEST_METADATA.json"
)
OUTPUT_ROOT = ROOT / "stage2_weapon_balanced_review_v3_output"
AUDIT_PATH = OUTPUT_ROOT / "WEAPON_BALANCED_AUDIT.json"
EPISODE_CSV = OUTPUT_ROOT / "WEAPON_ARM_OUTCOMES.csv"
WEAPON_CSV = OUTPUT_ROOT / "WEAPON_SUMMARY.csv"
EXPECTED_ROWS = 72
REQUIRE_TARGET_SHOT_COLUMNS = False
TARGET_SHOT_COLUMNS = {
    "target_entity",
    "target_hit",
    "target_outcome",
    "target_damage_count",
    "target_damage_amount",
    "target_killed",
    "target_direct",
    "target_splash",
    "target_pellet",
    "target_first_damage_server_tick",
    "target_observation_complete",
    "right_censored",
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def accepted_rows() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(
        (OUTPUT_ROOT / "manifests/shards").glob(
            "shard-*-of-*/accepted.jsonl"
        )
    ):
        result.extend(capture.load_jsonl(path))
    return result


def rejected_rows() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(
        (OUTPUT_ROOT / "manifests/shards").glob(
            "shard-*-of-*/rejects.jsonl"
        )
    ):
        result.extend(capture.load_jsonl(path))
    return result


def fire_root_and_mechanisms(
    event_id: int, indexed: dict[int, dict[str, Any]]
) -> tuple[int | None, set[str]]:
    current = event_id
    visited: set[int] = set()
    mechanisms: set[str] = set()
    while current in indexed and current not in visited:
        visited.add(current)
        event = indexed[current]
        if str(event.get("event")) == "impact":
            for name in ("direct", "splash", "pellet"):
                value = event.get(name)
                if pd.notna(value) and bool(int(value)):
                    mechanisms.add(name)
        if str(event.get("event")) == "fire":
            return current, mechanisms
        parent = event.get("parent_event_id")
        if pd.isna(parent):
            break
        current = int(parent)
    return None, mechanisms


def target_mechanism_metrics(
    events: pd.DataFrame, enemy_entity: int
) -> dict[str, Any]:
    indexed = {
        int(row["event_id"]): row.to_dict()
        for _, row in events.dropna(subset=["event_id"]).iterrows()
    }
    roots_by_mechanism: dict[str, set[int]] = {
        name: set() for name in ("direct", "splash", "pellet")
    }
    target_hit_roots: set[int] = set()
    target_damage_events = 0
    target_damage_amount = 0.0
    for _, row in events[events["event"] == "damage"].iterrows():
        target = row.get("target")
        if pd.isna(target) or int(target) != int(enemy_entity):
            continue
        target_damage_events += 1
        amount = row.get("amount")
        if pd.notna(amount):
            target_damage_amount += float(amount)
        root, mechanisms = fire_root_and_mechanisms(
            int(row["event_id"]), indexed
        )
        if root is None:
            continue
        target_hit_roots.add(root)
        for mechanism in mechanisms:
            roots_by_mechanism[mechanism].add(root)
    return {
        "target_hit_fire_event_ids": sorted(target_hit_roots),
        "target_damage_event_count": target_damage_events,
        "target_damage_amount": target_damage_amount,
        "direct_hit_fire_event_ids": sorted(
            roots_by_mechanism["direct"]
        ),
        "splash_hit_fire_event_ids": sorted(
            roots_by_mechanism["splash"]
        ),
        "pellet_hit_fire_event_ids": sorted(
            roots_by_mechanism["pellet"]
        ),
    }


def verify_package_hashes(
    accepted: dict[str, Any], package: Path
) -> bool:
    expected = accepted.get("package_sha256") or {}
    return bool(expected) and all(
        (package / name).is_file()
        and capture.sha256_file(package / name) == digest
        for name, digest in expected.items()
    )


def csv_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=list(rows[0]), lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def audit(require_complete: bool) -> dict[str, Any]:
    planned = capture.load_jsonl(MANIFEST)
    planned_by_id = {
        str(row["episode_id"]): row for row in planned
    }
    accepted_journal = accepted_rows()
    rejected_journal = rejected_rows()
    terminal_rejections = [
        row
        for row in rejected_journal
        if row.get("terminal") is True
    ]
    accepted_counts = Counter(
        str(row["episode_id"]) for row in accepted_journal
    )
    accepted_by_id = {
        str(row["episode_id"]): row for row in accepted_journal
    }
    rejected_counts = Counter(
        str(row["episode_id"]) for row in terminal_rejections
    )
    duplicate_accepted = sorted(
        episode_id
        for episode_id, count in accepted_counts.items()
        if count != 1
    )
    unknown_accepted = sorted(
        set(accepted_by_id) - set(planned_by_id)
    )
    missing = sorted(set(planned_by_id) - set(accepted_by_id))

    episode_results: list[dict[str, Any]] = []
    episode_csv_rows: list[dict[str, Any]] = []
    weapon_accumulator: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "episodes": 0,
            "firing_episodes": 0,
            "fire_events": 0,
            "target_hit_fire_events": 0,
            "direct_hit_fire_events": 0,
            "splash_hit_fire_events": 0,
            "pellet_hit_fire_events": 0,
            "target_damage_events": 0,
            "target_damage_amount": 0.0,
            "arms": {},
        }
    )
    arm_accumulator: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "episodes": 0,
            "fire_events": 0,
            "target_hit_fire_events": 0,
        }
    )

    for episode_id in sorted(set(planned_by_id) & set(accepted_by_id)):
        planned_row = planned_by_id[episode_id]
        accepted = accepted_by_id[episode_id]
        package = Path(str(accepted["episode_path"]))
        episode = json.loads(
            (package / "episode.json").read_text(encoding="utf-8")
        )
        qa = json.loads(
            (package / "qa.json").read_text(encoding="utf-8")
        )
        metrics = json.loads(
            (package / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        frames = pd.read_parquet(package / "frames.parquet")
        states = pd.read_parquet(package / "states.parquet")
        actions = pd.read_parquet(package / "model_actions.parquet")
        events = pd.read_parquet(package / "events.parquet")
        shots = pd.read_parquet(package / "shot_outcomes.parquet")
        enemy_entity = int(
            metrics["per_shot"]["target_entity"]
        )
        mechanisms = target_mechanism_metrics(
            events, enemy_entity
        )
        target_hit_ids = set(
            mechanisms["target_hit_fire_event_ids"]
        )
        declared_target_ids = set(
            metrics["per_shot"][
                "target_hit_fire_event_ids"
            ]
        )
        arm = str(metrics["aim_policy"])
        weapon = str(episode["weapon"])
        fire_events = int(
            metrics["fire_program"][
                "authoritative_fire_event_count"
            ]
        )
        target_hits = len(target_hit_ids)
        target_columns_present = TARGET_SHOT_COLUMNS <= set(shots.columns)
        target_shot_checks = {
            "columns_present": target_columns_present,
            "entity_exact": False,
            "hit_ids_exact": False,
            "observation_complete": False,
            "not_right_censored": False,
        }
        if target_columns_present:
            target_shot_checks.update(
                {
                    "entity_exact": bool(
                        len(shots) == 0
                        or (
                            pd.to_numeric(
                                shots["target_entity"], errors="raise"
                            ).astype(int)
                            == enemy_entity
                        ).all()
                    ),
                    "hit_ids_exact": set(
                        pd.to_numeric(
                            shots.loc[
                                shots["target_hit"].astype(bool),
                                "fire_event_id",
                            ],
                            errors="raise",
                        ).astype(int)
                    )
                    == target_hit_ids,
                    "observation_complete": bool(
                        shots["target_observation_complete"]
                        .astype(bool)
                        .all()
                    ),
                    "not_right_censored": bool(
                        not shots["right_censored"].astype(bool).any()
                    ),
                }
            )
        no_fire = arm == "visible_no_fire"
        audio = qa.get("audio") or {}
        gates = qa.get("gates") or {}
        hard_gates = qa.get("hard_gates") or {}
        player_checks = (
            (metrics.get("player_path") or {}).get("checks") or {}
        )
        checks = {
            "identity": episode.get("episode_id") == episode_id,
            "manifest_identity": planned_row["episode_id"]
            == episode_id,
            "package_hashes": verify_package_hashes(
                accepted, package
            ),
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
            "mapping_exact": qa.get("mapping", {}).get(
                "mapped_frames"
            )
            == capture.OUTPUT_TICKS
            and frames["episode_server_tick"].astype(int).tolist()
            == list(
                range(
                    capture.WARMUP_TICKS,
                    capture.TOTAL_TICKS,
                )
            ),
            "state_rows": len(states) == capture.TOTAL_TICKS,
            "model_action_rows": len(actions)
            == capture.OUTPUT_TICKS,
            "renderer_h200": str(
                qa.get("runtime", {}).get("renderer", "")
            ).startswith("NVIDIA H200"),
            "cpu_x264_flac": all(
                gates.get(name) is True
                for name in (
                    "encoded_flac_s16_stereo_48khz",
                    "encoded_h264_high",
                    "encoded_yuv420p",
                )
            )
            and qa.get("runtime", {}).get("x264_preset")
            == "medium"
            and int(
                qa.get("runtime", {}).get("x264_threads", -1)
            )
            == 12,
            "hud_and_mode": all(
                gates.get(name) is True
                for name in (
                    "minimal_hud_policy",
                    "server_objective_waypoints_disabled",
                    "gametype_exact",
                )
            ),
            "v9_passed": metrics.get("passed") is True
            and all(
                bool(value)
                for value in (
                    metrics.get("hard_gates") or {}
                ).values()
            ),
            "target_hit_ids_exact": target_hit_ids
            == declared_target_ids,
            "target_shot_columns": (
                all(target_shot_checks.values())
                if REQUIRE_TARGET_SHOT_COLUMNS
                else True
            ),
            "one_shot_row_per_fire": len(shots) == fire_events,
            "projectile_outcome_complete": not metrics[
                "per_shot"
            ]["unresolved_target_fire_event_ids"],
            "trace_replay_passed": all(
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
            "no_fire_contract": (
                fire_events == 0 and target_hits == 0
                if no_fire
                else fire_events == 2
            ),
            "nontraining": episode.get(
                "formal_collection_authorized"
            )
            is False
            and episode.get("training_admitted") is False,
        }
        passed = all(checks.values())
        result = {
            "episode_id": episode_id,
            "episode_path": str(package),
            "weapon": weapon,
            "arm": arm,
            "aim_family": (
                episode["causal_design"][
                    "weapon_balanced_aim_program"
                ]["family"]
            ),
            "fire_events": fire_events,
            "target_hit_fire_events": target_hits,
            "target_miss_fire_events": fire_events - target_hits,
            "target_hit_rate": (
                target_hits / fire_events if fire_events else None
            ),
            "direct_hit_fire_events": len(
                mechanisms["direct_hit_fire_event_ids"]
            ),
            "splash_hit_fire_events": len(
                mechanisms["splash_hit_fire_event_ids"]
            ),
            "pellet_hit_fire_events": len(
                mechanisms["pellet_hit_fire_event_ids"]
            ),
            "target_damage_events": mechanisms[
                "target_damage_event_count"
            ],
            "target_damage_amount": mechanisms[
                "target_damage_amount"
            ],
            "angular_error_at_fire_deg": metrics[
                "angular_error_at_fire_deg"
            ],
            "trace_position_error_p95": (
                metrics["player_path"]["trace_replay"] or {}
            ).get("position_error_p95"),
            "trace_position_error_max": (
                metrics["player_path"]["trace_replay"] or {}
            ).get("position_error_max"),
            "checks": checks,
            "target_shot_checks": target_shot_checks,
            "passed": passed,
        }
        episode_results.append(result)
        episode_csv_rows.append(
            {
                key: (
                    json.dumps(value, separators=(",", ":"))
                    if isinstance(value, (list, dict))
                    else value
                )
                for key, value in result.items()
                if key not in {"checks"}
            }
        )
        aggregate = weapon_accumulator[weapon]
        aggregate["episodes"] += 1
        aggregate["firing_episodes"] += int(not no_fire)
        aggregate["fire_events"] += fire_events
        aggregate["target_hit_fire_events"] += target_hits
        aggregate["direct_hit_fire_events"] += len(
            mechanisms["direct_hit_fire_event_ids"]
        )
        aggregate["splash_hit_fire_events"] += len(
            mechanisms["splash_hit_fire_event_ids"]
        )
        aggregate["pellet_hit_fire_events"] += len(
            mechanisms["pellet_hit_fire_event_ids"]
        )
        aggregate["target_damage_events"] += mechanisms[
            "target_damage_event_count"
        ]
        aggregate["target_damage_amount"] += mechanisms[
            "target_damage_amount"
        ]
        arm_aggregate = aggregate["arms"].setdefault(
            arm,
            {
                "episodes": 0,
                "fire_events": 0,
                "target_hit_fire_events": 0,
            },
        )
        arm_aggregate["episodes"] += 1
        arm_aggregate["fire_events"] += fire_events
        arm_aggregate["target_hit_fire_events"] += target_hits
        arm_accumulator[arm]["episodes"] += 1
        arm_accumulator[arm]["fire_events"] += fire_events
        arm_accumulator[arm][
            "target_hit_fire_events"
        ] += target_hits

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    bands = metadata["selection_contract"][
        "target_hit_rate_bands"
    ]
    weapon_summary: dict[str, dict[str, Any]] = {}
    weapon_csv_rows: list[dict[str, Any]] = []
    for weapon in sorted(weapon_accumulator):
        aggregate = weapon_accumulator[weapon]
        for arm_values in aggregate["arms"].values():
            arm_fires = int(arm_values["fire_events"])
            arm_hits = int(arm_values["target_hit_fire_events"])
            arm_values["target_hit_rate"] = (
                arm_hits / arm_fires if arm_fires else None
            )
        fires = int(aggregate["fire_events"])
        hits = int(aggregate["target_hit_fire_events"])
        rate = hits / fires if fires else math.nan
        lower = float(bands[weapon]["minimum"])
        upper = float(bands[weapon]["maximum"])
        summary = {
            **aggregate,
            "target_hit_rate": rate,
            "target_band_minimum": lower,
            "target_band_maximum": upper,
            "strict_band_passed": lower <= rate <= upper,
            "approximate_band_passed": (
                lower - 0.05 <= rate <= upper + 0.05
            ),
        }
        weapon_summary[weapon] = summary
        weapon_csv_rows.append(
            {
                key: (
                    json.dumps(value, separators=(",", ":"))
                    if isinstance(value, dict)
                    else value
                )
                for key, value in summary.items()
            }
            | {"weapon": weapon}
        )

    total_fires = sum(
        int(row["fire_events"])
        for row in weapon_accumulator.values()
    )
    total_hits = sum(
        int(row["target_hit_fire_events"])
        for row in weapon_accumulator.values()
    )
    complete = (
        len(accepted_by_id) == len(planned_by_id)
        and not duplicate_accepted
        and not unknown_accepted
        and not missing
    )
    summary_checks = {
        "manifest_rows_expected": len(planned) == EXPECTED_ROWS,
        "all_planned_accepted_exactly_once": complete,
        "no_terminal_rejects": not terminal_rejections,
        "all_episode_qa": bool(episode_results)
        and all(row["passed"] for row in episode_results),
        "all_nine_weapons_present": set(weapon_summary)
        == set(bands),
        "all_arms_present_when_complete": (
            not complete
            or set(arm_accumulator)
            == set(causal.WEAPON_BALANCED_AIM_ARMS)
        ),
        "no_runtime_fallback": all(
            row["prefrozen_trace_source"][
                "runtime_action_fallback"
            ]
            is False
            and row["prefrozen_trace_source"][
                "runtime_geometry_fallback"
            ]
            is False
            and row["weapon_balanced_review_design"][
                "runtime_outcome_fallback"
            ]
            is False
            for row in planned
        ),
    }
    if require_complete and not all(summary_checks.values()):
        raise capture.CaptureFailure(
            "stage2_weapon_balanced_audit_failed",
            capture.canonical_json(summary_checks),
        )
    result = {
        "schema_version": (
            "xonotic-stage2-weapon-balanced-artifact-audit-v3"
        ),
        "manifest": str(MANIFEST),
        "manifest_sha256": capture.sha256_file(MANIFEST),
        "metadata": str(METADATA),
        "metadata_sha256": capture.sha256_file(METADATA),
        "planned_episodes": len(planned),
        "accepted_episodes": len(accepted_by_id),
        "terminal_rejects": len(terminal_rejections),
        "retryable_rejected_attempts": (
            len(rejected_journal) - len(terminal_rejections)
        ),
        "missing_episode_ids": missing,
        "duplicate_accepted_episode_ids": duplicate_accepted,
        "unknown_accepted_episode_ids": unknown_accepted,
        "rejected_episode_ids": sorted(rejected_counts),
        "overall": {
            "fire_events": total_fires,
            "target_hit_fire_events": total_hits,
            "target_miss_fire_events": total_fires - total_hits,
            "target_hit_rate": (
                total_hits / total_fires if total_fires else None
            ),
        },
        "weapon_summary": weapon_summary,
        "arm_summary": {
            arm: values
            | {
                "target_hit_rate": (
                    values["target_hit_fire_events"]
                    / values["fire_events"]
                    if values["fire_events"]
                    else None
                )
            }
            for arm, values in sorted(arm_accumulator.items())
        },
        "episode_results": episode_results,
        "summary_checks": summary_checks,
        "complete": complete,
        "passed": all(summary_checks.values()),
    }
    atomic_text(
        AUDIT_PATH,
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    atomic_text(EPISODE_CSV, csv_text(episode_csv_rows))
    atomic_text(WEAPON_CSV, csv_text(weapon_csv_rows))
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
                "rejects": result["terminal_rejects"],
                "overall": result["overall"],
                "complete": result["complete"],
                "passed": result["passed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
