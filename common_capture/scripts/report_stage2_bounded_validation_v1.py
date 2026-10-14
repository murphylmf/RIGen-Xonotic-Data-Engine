                      
"""Aggregate the current non-training Stage-2 validation evidence."""

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
REPORT_ROOT = ROOT / "stage2_bounded_validation_v1/review"
EXPECTED_COUNTS = {
    "outcome_calibration": 36,
    "target_motion": 30,
    "player_motion_moving": 5,
    "player_motion_jumping": 5,
    "secondary_initial": 5,
    "secondary_replenishment": 2,
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def accepted_paths(
    output_root: Path,
    *,
    group_id: str | None = None,
    exclude_group_id: str | None = None,
) -> list[Path]:
    rows = bundle.accepted_rows(output_root)
    if group_id is not None or exclude_group_id is not None:
        rows_with_group = []
        for row in rows:
            episode = json.loads(
                (
                    Path(row["episode_path"]) / "episode.json"
                ).read_text(encoding="utf-8")
            )
            rows_with_group.append(
                (row, episode["counterfactual_group_id"])
            )
    else:
        rows_with_group = [(row, None) for row in rows]
    if group_id is not None:
        rows = [
            row
            for row, actual_group_id in rows_with_group
            if actual_group_id == group_id
        ]
        rows_with_group = [(row, group_id) for row in rows]
    if exclude_group_id is not None:
        rows = [
            row
            for row, actual_group_id in rows_with_group
            if actual_group_id != exclude_group_id
        ]
    return [Path(row["episode_path"]) for row in rows]


def selections() -> list[dict[str, Any]]:
    campaign = json.loads(
        (
            ROOT
            / "stage2_outcome_calibration_campaign_v1/review/"
            "STAGE2_OUTCOME_CALIBRATION_CAMPAIGN_AUDIT.json"
        ).read_text(encoding="utf-8")
    )
    selected: list[dict[str, Any]] = [
        {
            "cohort": "outcome_calibration",
            "episode_path": Path(row["episode_path"]),
        }
        for row in campaign["episodes"]
    ]
    selected.extend(
        {
            "cohort": "target_motion",
            "episode_path": path,
        }
        for path in accepted_paths(
            ROOT / "stage2_target_motion_review_v1_output",
            exclude_group_id=(
                "s2targetreviewv1_g02_close_approach_retreat"
            ),
        )
    )
    selected.extend(
        {
            "cohort": "target_motion",
            "episode_path": path,
        }
        for path in accepted_paths(
            ROOT
            / "stage2_target_motion_replenishment_v1_output"
        )
    )
    selected.extend(
        {
            "cohort": "player_motion_moving",
            "episode_path": path,
        }
        for path in accepted_paths(
            ROOT / "stage2_player_motion_replenishment_v1_output",
            group_id="s2playermotion_repl_g01",
        )
    )
    selected.extend(
        {
            "cohort": "player_motion_jumping",
            "episode_path": path,
        }
        for path in accepted_paths(
            ROOT / "stage2_player_motion_replenishment_v2_output"
        )
    )
    selected.extend(
        {
            "cohort": "secondary_initial",
            "episode_path": path,
        }
        for path in accepted_paths(
            ROOT / "stage2_causal_secondary_validation_v1_output"
        )
    )
    selected.extend(
        {
            "cohort": "secondary_replenishment",
            "episode_path": path,
        }
        for path in accepted_paths(
            ROOT
            / "stage2_causal_secondary_replenishment_v1_output"
        )
    )
    return selected


def audit() -> dict[str, Any]:
    selected = selections()
    count_by_cohort = Counter(row["cohort"] for row in selected)
    selection_checks = {
        f"{cohort}_count": count_by_cohort.get(cohort, 0)
        == expected
        for cohort, expected in EXPECTED_COUNTS.items()
    }
    selection_checks["episode_ids_unique"] = len(
        {
            row["episode_path"].name for row in selected
        }
    ) == len(selected)

    episodes: list[dict[str, Any]] = []
    trajectories: dict[str, list[np.ndarray]] = {}
    for selected_row in selected:
        path = selected_row["episode_path"]
        episode = json.loads(
            (path / "episode.json").read_text(encoding="utf-8")
        )
        qa = json.loads(
            (path / "qa.json").read_text(encoding="utf-8")
        )
        causal_qa = json.loads(
            (path / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        outcome = causal.actual_outcome_bin(qa)
        checks = bundle.media_checks(path, qa)
        checks.update(
            {
                "all_hard_gates": all(
                    qa["hard_gates"].values()
                ),
                "role_eligible": qa.get("role_eligible") is True,
                "causal_artifact_passed": (
                    causal_qa["passed"] is True
                ),
                "outcome_matches_artifact": (
                    outcome == causal_qa["actual_outcome"]
                ),
                "not_training_admitted": (
                    episode["training_admitted"] is False
                ),
                "formal_collection_not_authorized": (
                    episode["formal_collection_authorized"] is False
                ),
            }
        )
        design = episode["causal_design"]
        policy_labels = episode["policy_labels"]
        player_motion = (
            design.get("player_motion_class")
            or policy_labels.get("player_motion_class")
            or (
                "stationary"
                if design["base_player_program"] == "stationary"
                else design["base_player_program"]
            )
        )
        record = {
            "cohort": selected_row["cohort"],
            "episode_id": episode["episode_id"],
            "episode_path": str(path),
            "counterfactual_group_id": episode[
                "counterfactual_group_id"
            ],
            "map": episode["map"],
            "gametype": episode["gametype"],
            "weapon": episode["weapon"],
            "aim_policy": design["aim_policy"],
            "interaction_channel": design["interaction_channel"],
            "secondary_mechanism": design.get(
                "secondary_mechanism"
            ),
            "target_motion": episode["enemy_policy"]["name"],
            "player_motion": player_motion,
            "actual_outcome": outcome,
            "actual_distance_bin": causal_qa[
                "actual_distance_bin"
            ],
            "hit_rate_bin": qa["events"]["hit_rate_bin"],
            "fire_count": qa["events"]["fire_count"],
            "damage_count": qa["events"]["damage_count"],
            "death_count": qa["events"]["death_count"],
            "renderer": qa["runtime"]["renderer"],
            "checks": checks,
            "passed": all(checks.values()),
        }
        episodes.append(record)
        trajectories.setdefault(
            episode["counterfactual_group_id"], []
        ).append(bundle.enemy_trajectory(path))

    complete_group_specs = {
        "outcome_calibration": {
            "visible_no_response",
            "pass_offset",
            "delayed_acquisition",
            "sustained_tracking",
        },
        "target_motion": set(causal.AIM_POLICIES),
        "player_motion_moving": set(causal.AIM_POLICIES),
        "player_motion_jumping": set(causal.AIM_POLICIES),
    }
    groups: list[dict[str, Any]] = []
    for group_id in sorted(trajectories):
        members = [
            row
            for row in episodes
            if row["counterfactual_group_id"] == group_id
        ]
        cohort = members[0]["cohort"]
        if cohort not in complete_group_specs:
            continue
        arrays = trajectories[group_id]
        reference = arrays[0]
        error = max(
            float(
                np.max(
                    np.abs(array - reference), initial=0.0
                )
            )
            for array in arrays[1:]
        )
        checks = {
            "expected_policies": {
                row["aim_policy"] for row in members
            }
            == complete_group_specs[cohort],
            "all_episode_checks": all(
                row["passed"] for row in members
            ),
            "prescribed_enemy_trajectory_invariant": (
                error <= 1e-6
            ),
        }
        groups.append(
            {
                "cohort": cohort,
                "counterfactual_group_id": group_id,
                "rows": len(members),
                "enemy_exogenous_trajectory_max_abs_error": error,
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    distributions = {
        name: dict(Counter(row[key] for row in episodes))
        for name, key in (
            ("cohorts", "cohort"),
            ("weapons", "weapon"),
            ("aim_policies", "aim_policy"),
            ("interaction_channels", "interaction_channel"),
            ("target_motion", "target_motion"),
            ("player_motion", "player_motion"),
            ("actual_outcomes", "actual_outcome"),
            ("distance_bins", "actual_distance_bin"),
            ("hit_rate_bins", "hit_rate_bin"),
            ("maps", "map"),
            ("gametypes", "gametype"),
            ("renderers", "renderer"),
        )
    }
    pass_value = (
        all(selection_checks.values())
        and len(episodes) == sum(EXPECTED_COUNTS.values())
        and all(row["passed"] for row in episodes)
        and all(row["passed"] for row in groups)
    )
    return {
        "schema_version": (
            "xonotic-stage2-bounded-validation-ledger-v1"
        ),
        "pass": pass_value,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "distribution_interpretation": (
            "bounded_validation_evidence_not_formal_dataset_quota"
        ),
        "selected_rows": len(episodes),
        "complete_counterfactual_groups": len(groups),
        "selection_checks": selection_checks,
        "distributions": distributions,
        "groups": groups,
        "episodes": episodes,
    }


def markdown(result: dict[str, Any]) -> str:
    d = result["distributions"]
    lines = [
        "# Stage-2 bounded validation ledger v1",
        "",
        f"- Overall: **{'PASS' if result['pass'] else 'FAIL'}**",
        f"- Selected episodes: {result['selected_rows']}",
        f"- Complete counterfactual groups: "
        f"{result['complete_counterfactual_groups']}",
        "- This ledger is non-training validation evidence, not the "
        "formal 40k quota distribution.",
        f"- Cohorts: `{json.dumps(d['cohorts'], sort_keys=True)}`",
        f"- Aim policies: "
        f"`{json.dumps(d['aim_policies'], sort_keys=True)}`",
        f"- Target motion: "
        f"`{json.dumps(d['target_motion'], sort_keys=True)}`",
        f"- Player motion: "
        f"`{json.dumps(d['player_motion'], sort_keys=True)}`",
        f"- Channels: "
        f"`{json.dumps(d['interaction_channels'], sort_keys=True)}`",
        f"- Outcomes: "
        f"`{json.dumps(d['actual_outcomes'], sort_keys=True)}`",
        f"- Distances: "
        f"`{json.dumps(d['distance_bins'], sort_keys=True)}`",
        "",
        "| cohort | episode | weapon | policy | target/player motion | "
        "channel | outcome |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in sorted(
        result["episodes"],
        key=lambda item: (item["cohort"], item["episode_id"]),
    ):
        lines.append(
            f"| {row['cohort']} | {row['episode_id']} | "
            f"{row['weapon']} | {row['aim_policy']} | "
            f"{row['target_motion']} / {row['player_motion']} | "
            f"{row['interaction_channel']} | "
            f"{row['actual_outcome']} |"
        )
    return "\n".join(lines) + "\n"


def gallery(result: dict[str, Any]) -> str:
    cards: list[str] = []
    summary: list[dict[str, Any]] = []
    for row in sorted(
        result["episodes"],
        key=lambda item: (item["cohort"], item["episode_id"]),
    ):
        video = os.path.relpath(
            Path(row["episode_path"]) / "video.mkv",
            REPORT_ROOT,
        )
        cards.append(
            f"""
<article data-cohort="{html.escape(row['cohort'])}">
  <h2>{html.escape(row["weapon"])} ·
    {html.escape(row["aim_policy"])}</h2>
  <video controls playsinline preload="metadata"
    src="{html.escape(video)}"></video>
  <dl>
    <dt>cohort</dt><dd>{html.escape(row["cohort"])}</dd>
    <dt>episode</dt><dd>{html.escape(row["episode_id"])}</dd>
    <dt>target/player</dt><dd>{html.escape(row["target_motion"])} /
      {html.escape(row["player_motion"])}</dd>
    <dt>channel</dt><dd>{html.escape(row["interaction_channel"])}</dd>
    <dt>outcome</dt><dd>{html.escape(row["actual_outcome"])}</dd>
    <dt>distance</dt><dd>{html.escape(str(row["actual_distance_bin"]))}</dd>
  </dl>
</article>"""
        )
        summary.append(
            {
                key: row[key]
                for key in (
                    "cohort",
                    "episode_id",
                    "episode_path",
                    "weapon",
                    "aim_policy",
                    "target_motion",
                    "player_motion",
                    "interaction_channel",
                    "actual_outcome",
                    "actual_distance_bin",
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
<title>Stage-2 bounded validation</title>
<style>
body {{ margin: 24px; font: 14px/1.45 system-ui,sans-serif;
  color: #e8edf2; background: #11161c; }}
.grid {{ display: grid; grid-template-columns:
  repeat(auto-fit,minmax(420px,1fr)); gap: 18px; }}
article {{ padding: 14px; border: 1px solid #35404c; border-radius: 10px;
  background: #182029; }}
h2 {{ font-size: 16px; }} video {{ width: 100%; background: #000; }}
dl {{ display: grid; grid-template-columns: 130px 1fr; gap: 4px 10px; }}
dt {{ color: #9eb0c2; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>Stage-2 bounded validation ledger v1</h1>
<p>{len(summary)} non-training artifacts; this is validation evidence,
not the formal 40k distribution.</p>
<div class="grid">{''.join(cards)}</div>
</body>
</html>
"""


def main() -> int:
    result = audit()
    bundle.atomic_json(
        REPORT_ROOT / "STAGE2_BOUNDED_VALIDATION_AUDIT.json",
        result,
    )
    atomic_text(
        REPORT_ROOT / "STAGE2_BOUNDED_VALIDATION_REPORT.md",
        markdown(result),
    )
    atomic_text(REPORT_ROOT / "index.html", gallery(result))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
