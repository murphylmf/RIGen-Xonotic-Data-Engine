                      
"""Audit and render the complete Stage-2 outcome-calibration campaign."""

from __future__ import annotations

import html
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_stage2_causal_bundle as bundle              
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
REPORT_ROOT = (
    ROOT / "stage2_outcome_calibration_campaign_v1/review"
)
COHORTS = (
    {
        "name": "initial_v1",
        "manifest": (
            ROOT / "manifests/stage2_outcome_calibration_v1/input.jsonl"
        ),
        "output": ROOT / "stage2_outcome_calibration_v1_output",
    },
    {
        "name": "complete_group_replenishment_v1",
        "manifest": (
            ROOT
            / "manifests/stage2_outcome_calibration_replenishment_v1/"
            "input.jsonl"
        ),
        "output": (
            ROOT
            / "stage2_outcome_calibration_replenishment_v1_output"
        ),
    },
)
EXPECTED_WEAPONS = {
    "Blaster",
    "Shotgun",
    "MachineGun",
    "Mortar",
    "Electro",
    "Crylink",
    "Vortex",
    "Hagar",
    "Devastator",
}
EXPECTED_POLICIES = {
    "visible_no_response",
    "pass_offset",
    "delayed_acquisition",
    "sustained_tracking",
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def terminal_rows(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/rejects.jsonl"
        )
    ):
        rows.extend(
            row
            for row in capture.load_jsonl(path)
            if row.get("terminal") is True
        )
    return rows


def group_inventory() -> tuple[
    list[dict[str, Any]],
    dict[str, list[dict[str, Any]]],
]:
    inventory: list[dict[str, Any]] = []
    complete_by_weapon: dict[str, list[dict[str, Any]]] = {}
    for cohort in COHORTS:
        planned = capture.load_jsonl(cohort["manifest"])
        accepted = bundle.accepted_rows(cohort["output"])
        accepted_by_id = {
            row["episode_id"]: row for row in accepted
        }
        for group_id in sorted(
            {
                row["counterfactual_group_id"]
                for row in planned
            }
        ):
            members = [
                row
                for row in planned
                if row["counterfactual_group_id"] == group_id
            ]
            published = [
                accepted_by_id[row["episode_id"]]
                for row in members
                if row["episode_id"] in accepted_by_id
            ]
            policies = {
                row["causal_design"]["aim_policy"]
                for row in members
            }
            complete = (
                len(members) == len(EXPECTED_POLICIES)
                and len(published) == len(members)
                and policies == EXPECTED_POLICIES
                and len(
                    {
                        row["exogenous_contract_sha256"]
                        for row in members
                    }
                )
                == 1
            )
            entry = {
                "cohort": cohort["name"],
                "manifest": str(cohort["manifest"]),
                "output_root": str(cohort["output"]),
                "counterfactual_group_id": group_id,
                "weapon": members[0]["weapon"],
                "planned_rows": len(members),
                "accepted_rows": len(published),
                "complete": complete,
                "planned": members,
                "published_by_id": {
                    row["episode_id"]: row for row in published
                },
            }
            inventory.append(entry)
            if complete:
                complete_by_weapon.setdefault(
                    members[0]["weapon"], []
                ).append(entry)
    return inventory, complete_by_weapon


def audit() -> dict[str, Any]:
    inventory, complete_by_weapon = group_inventory()
    selected_groups: list[dict[str, Any]] = []
    selection_checks = {
        "all_nine_weapons_have_complete_group": (
            set(complete_by_weapon) == EXPECTED_WEAPONS
        ),
        "exactly_one_complete_group_per_weapon": all(
            len(complete_by_weapon.get(weapon, [])) == 1
            for weapon in EXPECTED_WEAPONS
        ),
    }
    if all(selection_checks.values()):
        selected_groups = [
            complete_by_weapon[weapon][0]
            for weapon in sorted(EXPECTED_WEAPONS)
        ]

    episodes: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for group in selected_groups:
        trajectories: list[np.ndarray] = []
        group_episode_records: list[dict[str, Any]] = []
        for row in group["planned"]:
            published = group["published_by_id"][row["episode_id"]]
            episode_path = Path(published["episode_path"])
            qa = json.loads(
                (episode_path / "qa.json").read_text(
                    encoding="utf-8"
                )
            )
            causal_qa = json.loads(
                (episode_path / "causal_interaction.json").read_text(
                    encoding="utf-8"
                )
            )
            outcome = causal.actual_outcome_bin(qa)
            path_metrics = (
                qa.get("live_precheck", {}).get(
                    "enemy_path_trace", {}
                )
            )
            checks = bundle.media_checks(episode_path, qa)
            checks.update(
                {
                    "all_hard_gates": all(
                        qa["hard_gates"].values()
                    ),
                    "causal_artifact_passed": (
                        causal_qa["passed"] is True
                    ),
                    "telemetry_outcome_matches_artifact": (
                        outcome == causal_qa["actual_outcome"]
                    ),
                    "planned_group_matches": (
                        causal_qa["counterfactual_group_id"]
                        == row["counterfactual_group_id"]
                    ),
                    "planned_policy_matches": (
                        causal_qa["aim_policy"]
                        == row["causal_design"]["aim_policy"]
                    ),
                    "planned_exogenous_hash_matches": (
                        causal_qa["exogenous_contract_sha256"]
                        == row["exogenous_contract_sha256"]
                    ),
                    "enemy_path_trace_passed": (
                        path_metrics.get("passed") is True
                    ),
                    "outcome_not_manifest_acceptance_label": (
                        row["acceptance"]["actual_outcome"] is None
                    ),
                }
            )
            record = {
                "cohort": group["cohort"],
                "counterfactual_group_id": group[
                    "counterfactual_group_id"
                ],
                "episode_id": row["episode_id"],
                "episode_path": str(episode_path),
                "weapon": row["weapon"],
                "aim_policy": row["causal_design"]["aim_policy"],
                "actual_outcome": outcome,
                "engine_mechanism_bin": qa["events"][
                    "actual_outcome_bin"
                ],
                "actual_distance_bin": causal_qa[
                    "actual_distance_bin"
                ],
                "hit_rate_bin": qa["events"]["hit_rate_bin"],
                "fire_count": qa["events"]["fire_count"],
                "damage_count": qa["events"]["damage_count"],
                "death_count": qa["events"]["death_count"],
                "renderer": qa["runtime"]["renderer"],
                "first_player_damage_tick": path_metrics.get(
                    "first_player_damage_tick"
                ),
                "pre_interaction_mismatch_tick_count": (
                    path_metrics.get(
                        "pre_interaction_mismatch_tick_count"
                    )
                ),
                "endogenous_deviation_tick_count": (
                    path_metrics.get(
                        "endogenous_deviation_tick_count"
                    )
                ),
                "checks": checks,
                "passed": all(checks.values()),
            }
            episodes.append(record)
            group_episode_records.append(record)
            trajectories.append(
                bundle.enemy_trajectory(episode_path)
            )
        reference = trajectories[0]
        trajectory_error = max(
            float(
                np.max(
                    np.abs(trajectory - reference), initial=0.0
                )
            )
            for trajectory in trajectories[1:]
        )
        group_checks = {
            "four_policies": (
                {
                    row["aim_policy"]
                    for row in group_episode_records
                }
                == EXPECTED_POLICIES
            ),
            "all_episode_checks": all(
                row["passed"] for row in group_episode_records
            ),
            "prescribed_enemy_trajectory_invariant": (
                trajectory_error <= 1e-6
            ),
        }
        groups.append(
            {
                "cohort": group["cohort"],
                "counterfactual_group_id": group[
                    "counterfactual_group_id"
                ],
                "weapon": group["weapon"],
                "enemy_exogenous_trajectory_max_abs_error": (
                    trajectory_error
                ),
                "checks": group_checks,
                "passed": all(group_checks.values()),
            }
        )

    selected_ids = {
        row["episode_id"] for row in episodes
    }
    preserved_unselected: list[dict[str, Any]] = []
    terminal: list[dict[str, Any]] = []
    cohort_records: list[dict[str, Any]] = []
    for cohort in COHORTS:
        planned = capture.load_jsonl(cohort["manifest"])
        accepted = bundle.accepted_rows(cohort["output"])
        terminal_cohort = terminal_rows(cohort["output"])
        preserved_unselected.extend(
            {
                "cohort": cohort["name"],
                "episode_id": row["episode_id"],
                "episode_path": row["episode_path"],
                "reason": (
                    "member_of_incomplete_superseded_"
                    "counterfactual_group"
                ),
            }
            for row in accepted
            if row["episode_id"] not in selected_ids
        )
        terminal.extend(
            {
                "cohort": cohort["name"],
                "episode_id": row["episode_id"],
                "attempt_id": row["attempt_id"],
                "reason": row["reason"],
                "diagnostic_path": row["diagnostic_path"],
            }
            for row in terminal_cohort
        )
        cohort_records.append(
            {
                "name": cohort["name"],
                "manifest": str(cohort["manifest"]),
                "manifest_sha256": capture.sha256_file(
                    cohort["manifest"]
                ),
                "output_root": str(cohort["output"]),
                "planned_rows": len(planned),
                "accepted_rows": len(accepted),
                "terminal_reject_rows": len(terminal_cohort),
            }
        )

    outcome_counts = Counter(
        row["actual_outcome"] for row in episodes
    )
    distance_counts = Counter(
        row["actual_distance_bin"] for row in episodes
    )
    hit_rate_counts = Counter(
        row["hit_rate_bin"] for row in episodes
    )
    policy_counts = Counter(row["aim_policy"] for row in episodes)
    weapon_counts = Counter(row["weapon"] for row in episodes)
    pass_value = (
        all(selection_checks.values())
        and len(episodes) == 36
        and len(groups) == 9
        and all(row["passed"] for row in episodes)
        and all(row["passed"] for row in groups)
    )
    return {
        "schema_version": (
            "xonotic-stage2-outcome-calibration-campaign-audit-v1"
        ),
        "pass": pass_value,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "outcome_assignment": "authoritative_telemetry_only",
        "runtime_fallback": False,
        "cohorts": cohort_records,
        "selection_checks": selection_checks,
        "selected_rows": len(episodes),
        "selected_complete_groups": len(groups),
        "distributions": {
            "actual_outcomes": dict(outcome_counts),
            "distance_bins": dict(distance_counts),
            "hit_rate_bins": dict(hit_rate_counts),
            "aim_policies": dict(policy_counts),
            "weapons": dict(weapon_counts),
        },
        "groups": groups,
        "episodes": episodes,
        "preserved_unselected_accepted": preserved_unselected,
        "preserved_terminal_rejects": terminal,
    }


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Stage-2 outcome calibration campaign v1",
        "",
        f"- Overall: **{'PASS' if result['pass'] else 'FAIL'}**",
        f"- Selected complete groups / episodes: "
        f"{result['selected_complete_groups']} / "
        f"{result['selected_rows']}",
        "- Outcomes are assigned only from authoritative telemetry; "
        "candidate intent is never an acceptance label.",
        "- Incomplete source groups and terminal candidates remain "
        "preserved and are not spliced into replacement groups.",
        f"- Actual outcomes: "
        f"`{json.dumps(result['distributions']['actual_outcomes'], sort_keys=True)}`",
        f"- Distance bins: "
        f"`{json.dumps(result['distributions']['distance_bins'], sort_keys=True)}`",
        "",
        "| Weapon | policy | outcome | distance | fire/damage/death | "
        "cohort |",
        "|---|---|---|---|---:|---|",
    ]
    for row in sorted(
        result["episodes"],
        key=lambda item: (item["weapon"], item["aim_policy"]),
    ):
        lines.append(
            f"| {row['weapon']} | {row['aim_policy']} | "
            f"{row['actual_outcome']} | {row['actual_distance_bin']} | "
            f"{row['fire_count']}/{row['damage_count']}/"
            f"{row['death_count']} | {row['cohort']} |"
        )
    return "\n".join(lines) + "\n"


def gallery(result: dict[str, Any]) -> str:
    cards: list[str] = []
    summary: list[dict[str, Any]] = []
    for row in sorted(
        result["episodes"],
        key=lambda item: (item["weapon"], item["aim_policy"]),
    ):
        episode_path = Path(row["episode_path"])
        video = os.path.relpath(
            episode_path / "video.mkv", REPORT_ROOT
        )
        cards.append(
            f"""
<article>
  <h2>{html.escape(row["weapon"])} ·
    {html.escape(row["aim_policy"])}</h2>
  <video controls playsinline preload="metadata"
    src="{html.escape(video)}"></video>
  <dl>
    <dt>episode</dt><dd>{html.escape(row["episode_id"])}</dd>
    <dt>outcome</dt><dd>{html.escape(row["actual_outcome"])}</dd>
    <dt>distance</dt><dd>{html.escape(str(row["actual_distance_bin"]))}</dd>
    <dt>fire/damage/death</dt>
      <dd>{row["fire_count"]}/{row["damage_count"]}/{row["death_count"]}</dd>
    <dt>mechanism</dt>
      <dd>{html.escape(row["engine_mechanism_bin"])}</dd>
    <dt>cohort</dt><dd>{html.escape(row["cohort"])}</dd>
  </dl>
</article>"""
        )
        summary.append(
            {
                key: row[key]
                for key in (
                    "episode_id",
                    "episode_path",
                    "weapon",
                    "aim_policy",
                    "actual_outcome",
                    "actual_distance_bin",
                    "cohort",
                    "passed",
                )
            }
        )
    atomic_text(
        REPORT_ROOT / "gallery.json",
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 outcome calibration campaign</title>
<style>
body {{ margin: 24px; font: 14px/1.45 system-ui,sans-serif;
  color: #e8edf2; background: #11161c; }}
.grid {{ display: grid; grid-template-columns:
  repeat(auto-fit,minmax(420px,1fr)); gap: 18px; }}
article {{ padding: 14px; border: 1px solid #35404c; border-radius: 10px;
  background: #182029; }}
h2 {{ font-size: 16px; }}
video {{ display: block; width: 100%; background: #000; }}
dl {{ display: grid; grid-template-columns: 145px 1fr; gap: 4px 10px; }}
dt {{ color: #9eb0c2; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>Stage-2 outcome calibration campaign v1</h1>
<p>{len(summary)} selected non-training episodes in nine complete
counterfactual groups. Outcomes below are realized from telemetry.</p>
<div class="grid">{''.join(cards)}</div>
</body>
</html>
"""


def main() -> int:
    result = audit()
    bundle.atomic_json(
        REPORT_ROOT / "STAGE2_OUTCOME_CALIBRATION_CAMPAIGN_AUDIT.json",
        result,
    )
    atomic_text(
        REPORT_ROOT / "STAGE2_OUTCOME_CALIBRATION_CAMPAIGN_REPORT.md",
        markdown(result),
    )
    atomic_text(REPORT_ROOT / "index.html", gallery(result))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
