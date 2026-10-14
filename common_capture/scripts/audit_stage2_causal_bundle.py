                      
"""Audit complete Stage-2 counterfactual bundles after publication."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


def accepted_rows(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/accepted.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


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
            and row.get("retryable") is not True
        )
    return rows


def enemy_trajectory(path: Path) -> np.ndarray:
    """Read the prescribed exogenous path, not post-hit realized state."""
    traces = pd.read_parquet(
        path / "enemy_path_trace.parquet"
    ).sort_values(
        "server_tick"
    )
    values = traces["target"].tolist()
    return np.asarray(values, dtype=np.float64)


def media_checks(path: Path, qa: dict[str, Any]) -> dict[str, bool]:
    return {
        "frames_320": int(qa["video"]["frames"])
        == capture.OUTPUT_TICKS,
        "audio_240000": int(qa["audio"]["samples_per_channel"])
        == capture.AUDIO_SAMPLES,
        "frame_tick_mapping": float(qa["mapping"]["success_rate"])
        >= 0.999,
        "hardware_renderer": capture.is_nvidia_hardware_renderer(
            qa["runtime"]["renderer"]
        ),
        "hud": (
            qa["hud"]["cl_hidewaypoints"] == 2
            and qa["hud"]["hud_panel_modicons"] == 0
            and qa["hud"]["g_ctf_flag_waypoint"] == 0
        ),
        "gametype": qa["mode"]["requested_gametype"]
        == qa["mode"]["realized_gametype"],
        "actions_320": len(
            pd.read_parquet(path / "model_actions.parquet")
        )
        == capture.OUTPUT_TICKS,
        "causal_artifact": (
            path / "causal_interaction.json"
        ).is_file(),
        "training_forbidden": qa.get("training_admitted") is False,
    }


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def audit(
    input_manifest: Path,
    output_root: Path,
    *,
    expected_policies: set[str] | None = None,
) -> dict[str, Any]:
    expected_policy_set = (
        set(causal.AIM_POLICIES)
        if expected_policies is None
        else set(expected_policies)
    )
    policy_design_gate = (
        "five_policy_design"
        if expected_policy_set == set(causal.AIM_POLICIES)
        else "expected_policy_design"
    )
    planned = capture.load_jsonl(input_manifest)
    accepted = accepted_rows(output_root)
    terminal = terminal_rows(output_root)
    planned_by_id = {row["episode_id"]: row for row in planned}
    accepted_by_id = {row["episode_id"]: row for row in accepted}
    terminal_by_id = {row["episode_id"]: row for row in terminal}
    episode_results: list[dict[str, Any]] = []
    for episode_id, row in planned_by_id.items():
        published = accepted_by_id.get(episode_id)
        if published is None:
            episode_results.append(
                {
                    "episode_id": episode_id,
                    "counterfactual_group_id": row[
                        "counterfactual_group_id"
                    ],
                    "aim_policy": row["causal_design"]["aim_policy"],
                    "passed": False,
                    "terminal_reject": terminal_by_id.get(episode_id),
                }
            )
            continue
        path = Path(published["episode_path"])
        qa = json.loads((path / "qa.json").read_text(encoding="utf-8"))
        causal_qa = json.loads(
            (path / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        checks = media_checks(path, qa)
        checks.update(
            {
                "all_original_hard_gates": all(
                    qa["hard_gates"].values()
                ),
                "causal_passed": causal_qa["passed"] is True,
                "planned_group": causal_qa[
                    "counterfactual_group_id"
                ]
                == row["counterfactual_group_id"],
                "planned_policy": causal_qa["aim_policy"]
                == row["causal_design"]["aim_policy"],
                "planned_exogenous_hash": causal_qa[
                    "exogenous_contract_sha256"
                ]
                == row["exogenous_contract_sha256"],
            }
        )
        episode_results.append(
            {
                "episode_id": episode_id,
                "counterfactual_group_id": row[
                    "counterfactual_group_id"
                ],
                "aim_policy": row["causal_design"]["aim_policy"],
                "shot_error_program": causal_qa.get(
                    "shot_error_program", "legacy"
                ),
                "candidate_generation_outcome_arm": (
                    (row.get("policy_labels") or {}).get(
                        "candidate_generation_outcome_arm"
                    )
                ),
                "initial_screen": causal_qa.get("initial_screen"),
                "actual_outcome": causal_qa["actual_outcome"],
                "actual_distance_bin": causal_qa[
                    "actual_distance_bin"
                ],
                "episode_path": str(path),
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    group_results: list[dict[str, Any]] = []
    groups = sorted(
        {row["counterfactual_group_id"] for row in planned}
    )
    for group in groups:
        planned_members = [
            row
            for row in planned
            if row["counterfactual_group_id"] == group
        ]
        result_members = [
            row
            for row in episode_results
            if row["counterfactual_group_id"] == group
        ]
        published_members = [
            row for row in result_members if row.get("episode_path")
        ]
        trajectory_error = math.inf
        if len(published_members) == len(planned_members):
            trajectories = [
                enemy_trajectory(Path(row["episode_path"]))
                for row in published_members
            ]
            reference = trajectories[0]
            trajectory_error = max(
                float(np.max(np.abs(values - reference), initial=0.0))
                for values in trajectories[1:]
            )
        checks = {
            policy_design_gate: {
                row["causal_design"]["aim_policy"]
                for row in planned_members
            }
            == expected_policy_set,
            "single_exogenous_hash": len(
                {
                    row["exogenous_contract_sha256"]
                    for row in planned_members
                }
            )
            == 1,
            "all_members_accounted": len(result_members)
            == len(planned_members),
            "all_members_accepted": len(published_members)
            == len(planned_members),
            "all_episode_checks": all(
                row["passed"] for row in result_members
            ),
            "enemy_exogenous_trajectory_invariant": (
                trajectory_error <= 1e-6
            ),
        }
        group_results.append(
            {
                "counterfactual_group_id": group,
                "planned_rows": len(planned_members),
                "accepted_rows": len(published_members),
                "enemy_exogenous_trajectory_max_abs_error": (
                    trajectory_error
                ),
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    outcome_counts = Counter(
        row["actual_outcome"]
        for row in episode_results
        if row.get("actual_outcome")
    )
    policy_counts = Counter(
        row["aim_policy"]
        for row in episode_results
        if row.get("episode_path")
    )
    shot_program_counts = Counter(
        row["shot_error_program"]
        for row in episode_results
        if row.get("episode_path")
    )
    initial_horizontal = Counter(
        ((row.get("initial_screen") or {}).get("planned") or {}).get(
            "screen_horizontal", "legacy"
        )
        for row in episode_results
        if row.get("episode_path")
    )
    initial_vertical = Counter(
        ((row.get("initial_screen") or {}).get("planned") or {}).get(
            "screen_vertical", "legacy"
        )
        for row in episode_results
        if row.get("episode_path")
    )
    outcome_by_generation_arm: dict[str, dict[str, int]] = {}
    for row in episode_results:
        arm = row.get("candidate_generation_outcome_arm")
        outcome = row.get("actual_outcome")
        if arm is None or outcome is None:
            continue
        outcome_by_generation_arm.setdefault(str(arm), {})
        outcome_by_generation_arm[str(arm)][str(outcome)] = (
            outcome_by_generation_arm[str(arm)].get(str(outcome), 0)
            + 1
        )
    result = {
        "schema_version": "xonotic-stage2-causal-bundle-audit-v1",
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": capture.sha256_file(
            input_manifest
        ),
        "output_root": str(output_root),
        "planned_rows": len(planned),
        "accepted_rows": len(accepted),
        "terminal_reject_rows": len(terminal),
        "actual_outcomes": dict(outcome_counts),
        "aim_policy": dict(policy_counts),
        "shot_error_program": dict(shot_program_counts),
        "initial_screen_horizontal": dict(initial_horizontal),
        "initial_screen_vertical": dict(initial_vertical),
        "actual_outcome_by_generation_arm": (
            outcome_by_generation_arm
        ),
        "episodes": episode_results,
        "groups": group_results,
        "complete_groups": sum(row["passed"] for row in group_results),
        "pass": (
            len(accepted) == len(planned)
            and not terminal
            and all(row["passed"] for row in episode_results)
            and all(row["passed"] for row in group_results)
        ),
    }
    return result


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Stage-2 causal bundle audit",
        "",
        f"- Overall: **{'PASS' if result['pass'] else 'FAIL'}**",
        f"- Planned / accepted / terminal reject: "
        f"{result['planned_rows']} / {result['accepted_rows']} / "
        f"{result['terminal_reject_rows']}",
        f"- Complete counterfactual groups: "
        f"{result['complete_groups']}/{len(result['groups'])}",
        f"- Actual telemetry outcomes: "
        f"`{json.dumps(result['actual_outcomes'], sort_keys=True)}`",
        f"- Aim policy: "
        f"`{json.dumps(result['aim_policy'], sort_keys=True)}`",
        f"- Shot-error program: "
        f"`{json.dumps(result['shot_error_program'], sort_keys=True)}`",
        f"- Initial horizontal: "
        f"`{json.dumps(result['initial_screen_horizontal'], sort_keys=True)}`",
        f"- Initial vertical: "
        f"`{json.dumps(result['initial_screen_vertical'], sort_keys=True)}`",
        f"- Actual outcome by generation arm: "
        f"`{json.dumps(result['actual_outcome_by_generation_arm'], sort_keys=True)}`",
        "",
        "| Group | accepted | prescribed enemy trajectory max error | pass |",
        "|---|---:|---:|---:|",
    ]
    for row in result["groups"]:
        error = row["enemy_exogenous_trajectory_max_abs_error"]
        error_text = f"{error:.3g}" if math.isfinite(error) else "inf"
        lines.append(
            f"| {row['counterfactual_group_id']} | "
            f"{row['accepted_rows']}/{row['planned_rows']} | "
            f"{error_text} | {'yes' if row['passed'] else 'no'} |"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    report_root = (
        args.report_root.resolve()
        if args.report_root
        else output_root / "review"
    )
    result = audit(args.input_manifest.resolve(), output_root)
    atomic_json(report_root / "STAGE2_CAUSAL_BUNDLE_AUDIT.json", result)
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "STAGE2_CAUSAL_BUNDLE_AUDIT.md").write_text(
        markdown(result), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
