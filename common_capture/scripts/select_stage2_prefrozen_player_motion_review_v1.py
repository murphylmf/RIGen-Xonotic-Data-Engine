                      
"""Apply the preregistered Stage-2 player-motion group selector."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_stage2_prefrozen_player_motion_review_v1 as prep              
import xonotic_capture as capture              


DEFAULT_MANIFEST = prep.OUTPUT_ROOT / "input.jsonl"
DEFAULT_METADATA = prep.OUTPUT_ROOT / "MANIFEST_METADATA.json"
DEFAULT_OUTPUT = ROOT / "stage2_prefrozen_player_motion_review_v1_output"
DEFAULT_BASELINE_OUTPUT = ROOT / "stage2_stochastic_review_v1_output"


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def published_rows(
    output_root: Path, filename: str
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            f"shard-*-of-*/{filename}"
        )
    ):
        result.extend(capture.load_jsonl(path))
    return result


def enemy_hit_fire_ids(
    events: pd.DataFrame, enemy_entity: int
) -> set[int]:
    """Return fire roots with authoritative damage to the target enemy."""
    indexed = {
        int(row["event_id"]): row.to_dict()
        for _, row in events.dropna(subset=["event_id"]).iterrows()
    }
    result: set[int] = set()
    for _, damage in events[events["event"] == "damage"].iterrows():
        target = damage.get("target")
        if pd.isna(target) or int(target) != enemy_entity:
            continue
        parent = damage.get("parent_event_id")
        visited: set[int] = set()
        while pd.notna(parent):
            event_id = int(parent)
            if event_id in visited or event_id not in indexed:
                break
            visited.add(event_id)
            ancestor = indexed[event_id]
            if str(ancestor.get("event")) == "fire":
                result.add(event_id)
                break
            parent = ancestor.get("parent_event_id")
    return result


def artifact_stats(episode_path: Path) -> dict[str, Any]:
    qa = json.loads(
        (episode_path / "qa.json").read_text(encoding="utf-8")
    )
    causal = json.loads(
        (episode_path / "causal_interaction.json").read_text(
            encoding="utf-8"
        )
    )
    shots = pd.read_parquet(episode_path / "shot_outcomes.parquet")
    events = pd.read_parquet(episode_path / "events.parquet")
    enemy_entity = int(
        qa["enemy_policy"]["movement_audio"]["enemy_entity"]
    )
    target_hit_ids = enemy_hit_fire_ids(events, enemy_entity)
    generic_hit_ids = set(
        pd.to_numeric(
            shots.loc[
                shots["hit"].astype(bool), "fire_event_id"
            ],
            errors="raise",
        ).astype(int)
    )
    hits = len(target_hit_ids)
    player_path = causal.get("player_path") or {}
    checks = {
        "accepted": qa.get("accepted") is True,
        "stage2_passed": causal.get("passed") is True,
        "player_motion_passed": (
            (causal.get("player_path") or {}).get("passed") is True
        ),
        "player_motion_class": (
            (causal.get("player_path") or {}).get("motion_class")
            == "prefrozen_continuous_movement"
        ),
        "video_frames": qa.get("video", {}).get("frames")
        == capture.OUTPUT_TICKS,
        "audio_samples": qa.get("audio", {}).get(
            "samples_per_channel"
        )
        == capture.AUDIO_SAMPLES,
        "frame_tick_mapping": qa.get("mapping", {}).get(
            "mapped_frames"
        )
        == capture.OUTPUT_TICKS,
        "shot_rows_exact": len(shots)
        == int(qa.get("events", {}).get("fire_count", -1)),
        "confirmed_hits_exact": hits
        == int(qa.get("events", {}).get("hit_fire_count", -1))
        and target_hit_ids == generic_hit_ids,
        "outcome_not_episode_admission": (
            (json.loads(
                (episode_path / "episode.json").read_text(
                    encoding="utf-8"
                )
            ).get("acceptance") or {}).get("actual_outcome")
            is None
        ),
    }
    return {
        "shots": len(shots),
        "confirmed_hits": hits,
        "generic_damage_hits": len(generic_hit_ids),
        "enemy_entity": enemy_entity,
        "confirmed_hit_rate": hits / len(shots) if len(shots) else 0.0,
        "player_motion": {
            "profile": (
                (player_path.get("program") or {}).get("profile")
                if isinstance(player_path.get("program"), dict)
                else player_path.get("motion_class")
            ),
            "active_frames": player_path.get("active_frames"),
            "horizontal_path_length": player_path.get(
                "horizontal_path_length"
            ),
            "maximum_horizontal_displacement": player_path.get(
                "maximum_horizontal_displacement"
            ),
            "final_horizontal_displacement": player_path.get(
                "final_horizontal_displacement"
            ),
            "longest_ungrounded_ticks": player_path.get(
                "longest_ungrounded_ticks"
            ),
            "maximum_airborne_drop": player_path.get(
                "maximum_airborne_drop"
            ),
            "blocked_ticks": (
                player_path.get("movement_blockage") or {}
            ).get("blocked_ticks"),
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def baseline_stats(output_root: Path) -> dict[str, Any]:
    episodes = sorted((output_root / "episodes").glob("s2stochv1_*"))
    hits = 0
    shots = 0
    weapon_hits: dict[str, int] = defaultdict(int)
    for episode_path in episodes:
        episode = json.loads(
            (episode_path / "episode.json").read_text(
                encoding="utf-8"
            )
        )
        frame = pd.read_parquet(
            episode_path / "shot_outcomes.parquet"
        )
        events = pd.read_parquet(episode_path / "events.parquet")
        qa = json.loads(
            (episode_path / "qa.json").read_text(encoding="utf-8")
        )
        enemy_entity = int(
            qa["enemy_policy"]["movement_audio"]["enemy_entity"]
        )
        episode_hits = len(
            enemy_hit_fire_ids(events, enemy_entity)
        )
        hits += episode_hits
        shots += len(frame)
        weapon_hits[str(episode["weapon"])] += episode_hits
    return {
        "episodes": len(episodes),
        "shots": shots,
        "confirmed_hits": hits,
        "confirmed_hit_rate": hits / shots if shots else 0.0,
        "weapons_with_confirmed_hit": sum(
            value > 0 for value in weapon_hits.values()
        ),
        "matches_preregistered_baseline": (
            len(episodes) == 27
            and shots == prep.BASELINE_SHOTS
            and hits == prep.BASELINE_HITS
            and sum(value > 0 for value in weapon_hits.values())
            == prep.BASELINE_WEAPONS_WITH_HIT
        ),
    }


def select(
    manifest_path: Path,
    metadata_path: Path,
    output_root: Path,
    baseline_output: Path,
    additional_sources: tuple[tuple[Path, Path], ...] = (),
) -> dict[str, Any]:
    planned = capture.load_jsonl(manifest_path)
    candidate_manifests = [
        {
            "manifest": str(manifest_path),
            "manifest_sha256": capture.sha256_file(manifest_path),
            "output_root": str(output_root),
        }
    ]
    accepted = published_rows(output_root, "accepted.jsonl")
    for additional_manifest, additional_output in additional_sources:
        planned.extend(capture.load_jsonl(additional_manifest))
        accepted.extend(
            published_rows(additional_output, "accepted.jsonl")
        )
        candidate_manifests.append(
            {
                "manifest": str(additional_manifest),
                "manifest_sha256": capture.sha256_file(
                    additional_manifest
                ),
                "output_root": str(additional_output),
            }
        )
    planned_by_id = {
        str(row["episode_id"]): row for row in planned
    }
    if len(planned_by_id) != len(planned):
        raise capture.CaptureFailure(
            "combined_candidate_episode_id_duplicate"
        )
    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )
    contract = prep.selection_contract()
    contract_sha256 = hashlib.sha256(
        capture.canonical_json(contract).encode("utf-8")
    ).hexdigest()
    accepted_by_id = {
        str(row["episode_id"]): Path(row["episode_path"])
        for row in accepted
        if str(row["episode_id"]) in planned_by_id
    }
    episode_stats: dict[str, dict[str, Any]] = {}
    for episode_id, episode_path in accepted_by_id.items():
        episode_stats[episode_id] = artifact_stats(episode_path)

    group_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in planned:
        group_rows[str(row["counterfactual_group_id"])].append(row)
    groups: dict[str, dict[str, Any]] = {}
    for group_id, rows in sorted(group_rows.items()):
        weapon = str(rows[0]["weapon"])
        review_design = (
            rows[0].get("prefrozen_player_motion_review_design")
            or rows[0].get(
                "prefrozen_player_motion_replenishment_design"
            )
            or {}
        )
        profile = str(
            review_design["motion_profile"]
        )
        expected_variants = set(prep.stochastic_v1.VARIANTS)
        actual_variants = {
            str(row["policy_labels"]["random_aim_variant"])
            for row in rows
        }
        stats = [
            episode_stats.get(str(row["episode_id"]))
            for row in rows
        ]
        eligible = (
            len(rows) == 3
            and actual_variants == expected_variants
            and all(value is not None for value in stats)
            and all(value["passed"] for value in stats if value)
        )
        groups[group_id] = {
            "counterfactual_group_id": group_id,
            "weapon": weapon,
            "motion_profile": profile,
            "episode_ids": sorted(
                str(row["episode_id"]) for row in rows
            ),
            "episodes_accepted": sum(
                value is not None for value in stats
            ),
            "all_live_qa_passed": bool(eligible),
            "shots": sum(
                int(value["shots"]) for value in stats if value
            ),
            "confirmed_hits": sum(
                int(value["confirmed_hits"])
                for value in stats
                if value
            ),
            "eligible": bool(eligible),
        }

    by_weapon: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups.values():
        if group["eligible"]:
            by_weapon[group["weapon"]].append(group)
    weapons = list(prep.stochastic_v1.human_v2.WEAPONS)
    choices = [by_weapon.get(weapon, []) for weapon in weapons]
    combinations: list[dict[str, Any]] = []
    if all(choices):
        for selected in itertools.product(*choices):
            profiles = [
                str(group["motion_profile"]) for group in selected
            ]
            lateral = profiles.count("lateral_weave")
            approach = profiles.count("approach_retreat")
            if sorted((lateral, approach)) != [4, 5]:
                continue
            hits = sum(
                int(group["confirmed_hits"]) for group in selected
            )
            shots = sum(int(group["shots"]) for group in selected)
            weapons_with_hit = sum(
                int(group["confirmed_hits"]) > 0
                for group in selected
            )
            combinations.append(
                {
                    "groups": selected,
                    "group_ids": tuple(
                        str(group["counterfactual_group_id"])
                        for group in selected
                    ),
                    "confirmed_hits": hits,
                    "shots": shots,
                    "confirmed_hit_rate": (
                        hits / shots if shots else 0.0
                    ),
                    "weapons_with_confirmed_hit": weapons_with_hit,
                }
            )
    combinations.sort(
        key=lambda value: (
            -int(value["weapons_with_confirmed_hit"]),
            -int(value["confirmed_hits"]),
            -float(value["confirmed_hit_rate"]),
            value["group_ids"],
        )
    )
    winner = combinations[0] if combinations else None
    baseline = baseline_stats(baseline_output)
    hard_checks = {
        "selection_contract_hash": metadata.get(
            "selection_contract_sha256"
        )
        == contract_sha256,
        "baseline_exact": baseline[
            "matches_preregistered_baseline"
        ],
        "all_weapons_have_eligible_group": all(choices),
        "profile_balanced_combination_exists": winner is not None,
        "minimum_confirmed_hits": bool(winner)
        and int(winner["confirmed_hits"])
        >= prep.HARD_MINIMUM_HITS,
        "minimum_confirmed_hit_rate": bool(winner)
        and float(winner["confirmed_hit_rate"])
        >= prep.HARD_MINIMUM_HIT_RATE,
        "minimum_weapons_with_confirmed_hit": bool(winner)
        and int(winner["weapons_with_confirmed_hit"])
        >= prep.HARD_MINIMUM_WEAPONS_WITH_HIT,
    }
    passed = all(hard_checks.values())
    target_checks = {
        "target_confirmed_hits": bool(winner)
        and int(winner["confirmed_hits"])
        >= prep.TARGET_MINIMUM_HITS,
        "target_confirmed_hit_rate": bool(winner)
        and float(winner["confirmed_hit_rate"])
        >= prep.TARGET_MINIMUM_HIT_RATE,
    }
    selected_group_ids = (
        set(winner["group_ids"]) if winner and passed else set()
    )
    selected_rows = [
        row
        for row in planned
        if row["counterfactual_group_id"] in selected_group_ids
    ]
    report = {
        "schema_version": (
            "xonotic-stage2-prefrozen-player-motion-selection-audit-v1"
        ),
        "manifest": str(manifest_path),
        "manifest_sha256": capture.sha256_file(manifest_path),
        "output_root": str(output_root),
        "candidate_manifests": candidate_manifests,
        "additional_candidate_cohorts": len(additional_sources),
        "selection_contract": contract,
        "selection_contract_sha256": contract_sha256,
        "planned_candidates": len(planned),
        "accepted_candidates": len(accepted_by_id),
        "accepted_candidate_per_shot": {
            "shots": sum(
                int(value["shots"])
                for value in episode_stats.values()
            ),
            "confirmed_hits": sum(
                int(value["confirmed_hits"])
                for value in episode_stats.values()
            ),
        },
        "episodes": [
            {
                "episode_id": episode_id,
                **stats,
            }
            for episode_id, stats in sorted(episode_stats.items())
        ],
        "eligible_groups": sum(
            group["eligible"] for group in groups.values()
        ),
        "groups": list(groups.values()),
        "baseline": baseline,
        "winner": (
            {
                **{
                    key: value
                    for key, value in winner.items()
                    if key != "groups"
                },
                "selected_groups": [
                    {
                        "counterfactual_group_id": group[
                            "counterfactual_group_id"
                        ],
                        "weapon": group["weapon"],
                        "motion_profile": group["motion_profile"],
                        "shots": group["shots"],
                        "confirmed_hits": group[
                            "confirmed_hits"
                        ],
                    }
                    for group in winner["groups"]
                ],
            }
            if winner
            else None
        ),
        "selected_rows": len(selected_rows),
        "hard_checks": hard_checks,
        "target_checks": target_checks,
        "hard_floor_passed": passed,
        "target_90_percent_met": all(target_checks.values()),
        "candidate_outcomes_used_only_by_preregistered_group_selector": True,
        "runtime_fallback_used": False,
        "passed": passed,
    }
    atomic_json(output_root / "SELECTION_AUDIT.json", report)
    if passed:
        text = "".join(
            capture.canonical_json(row) + "\n"
            for row in selected_rows
        )
        selected_path = prep.OUTPUT_ROOT / "selected_input.jsonl"
        prep.write_once_or_verify(selected_path, text)
        report["selected_manifest"] = str(selected_path)
        report["selected_manifest_sha256"] = capture.sha256_file(
            selected_path
        )
        atomic_json(output_root / "SELECTION_AUDIT.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--baseline-output",
        type=Path,
        default=DEFAULT_BASELINE_OUTPUT,
    )
    parser.add_argument(
        "--additional-manifest",
        type=Path,
        action="append",
        default=[],
    )
    parser.add_argument(
        "--additional-output-root",
        type=Path,
        action="append",
        default=[],
    )
    args = parser.parse_args()
    if len(args.additional_manifest) != len(
        args.additional_output_root
    ):
        parser.error(
            "--additional-manifest and --additional-output-root "
            "must be supplied in pairs"
        )
    report = select(
        args.manifest.resolve(),
        args.metadata.resolve(),
        args.output_root.resolve(),
        args.baseline_output.resolve(),
        tuple(
            (
                manifest.resolve(),
                output.resolve(),
            )
            for manifest, output in zip(
                args.additional_manifest,
                args.additional_output_root,
            )
        ),
    )
    print(
        capture.canonical_json(
            {
                key: report[key]
                for key in (
                    "planned_candidates",
                    "accepted_candidates",
                    "eligible_groups",
                    "winner",
                    "hard_floor_passed",
                    "target_90_percent_met",
                    "passed",
                )
            }
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
