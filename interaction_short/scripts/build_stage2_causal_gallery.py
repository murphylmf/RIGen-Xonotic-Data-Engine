                      
"""Build a compact browser review page for Stage-2 causal artifacts."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import stage2_target_outcome_labels as target_labels              


def accepted_rows(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/accepted.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return target_labels.apply_current_labels(output_root.resolve(), rows)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def build(
    output_root: Path,
    additional_output_roots: tuple[Path, ...] = (),
    *,
    episode_manifest: Path | None = None,
    review_directory: str = "review",
) -> Path:
    cards: list[str] = []
    summary: list[dict[str, Any]] = []
    manifests = accepted_rows(output_root)
    for additional_root in additional_output_roots:
        manifests.extend(accepted_rows(additional_root))
    if episode_manifest is not None:
        allowed_episode_ids = {
            str(row["episode_id"])
            for row in capture.load_jsonl(episode_manifest)
        }
        manifests = [
            row
            for row in manifests
            if str(row["episode_id"]) in allowed_episode_ids
        ]
    for manifest in sorted(
        manifests, key=lambda row: row["episode_id"]
    ):
        episode_id = manifest["episode_id"]
        episode = Path(manifest["episode_path"])
        causal = json.loads(
            (episode / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        episode_record = json.loads(
            (episode / "episode.json").read_text(encoding="utf-8")
        )
        qa = json.loads((episode / "qa.json").read_text(encoding="utf-8"))
        relative_video = os.path.relpath(
            episode / "video.mkv",
            output_root / review_directory,
        )
        shot_program = str(
            causal.get("shot_error_program", "legacy")
        )
        initial_screen = causal.get("initial_screen") or {}
        initial_planned = initial_screen.get("planned") or {}
        initial_actual = initial_screen.get("actual") or {}
        initial_cell = "/".join(
            str(value)
            for value in (
                initial_planned.get("screen_horizontal", "legacy"),
                initial_planned.get("screen_vertical", "legacy"),
            )
        )
        initial_horizontal = str(
            initial_planned.get("screen_horizontal", "legacy")
        )
        initial_vertical = str(
            initial_planned.get("screen_vertical", "legacy")
        )
        actual_outcome = str(causal["actual_outcome"])
        weapon = str(episode_record.get("weapon", "unknown"))
        design = episode_record.get("causal_design") or {}
        schedule = design.get("aim_schedule") or {}
        review_design = (
            episode_record.get("humanized_review_design")
            or episode_record.get("stochastic_review_design")
            or episode_record.get(
                "prefrozen_player_motion_review_design"
            )
            or episode_record.get(
                "prefrozen_player_motion_replenishment_design"
            )
            or episode_record.get(
                "weapon_balanced_review_design"
            )
            or {}
        )
        replaces_episode = str(
            review_design.get(
                "replacement_for_episode_id",
                review_design.get(
                    "base_episode_id", "not_applicable"
                ),
            )
        )
        remediation_reason = str(
            review_design.get(
                "remediation_reason",
                review_design.get(
                    "terminal_rejection_reason",
                    "not_applicable",
                ),
            )
        )
        fire_metrics = causal.get("fire_program") or {}
        planned_fire = fire_metrics.get("program") or {}
        fire_program = str(planned_fire.get("name", "legacy"))
        fire_category = str(
            review_design.get(
                "firing_program_category",
                review_design.get("arm", "legacy"),
            )
        )
        fire_event_count = fire_metrics.get(
            "authoritative_fire_event_count",
            (causal.get("event_counts") or {}).get("fire_count"),
        )
        miss_sector = str(
            schedule.get("miss_direction_sector", "not_applicable")
        )
        miss_magnitude = str(
            schedule.get("miss_magnitude_bin", "not_applicable")
        )
        miss_trajectory = str(
            schedule.get(
                "miss_trajectory_style", "not_applicable"
            )
        )
        realized_miss_vectors = causal.get(
            "realized_miss_vectors_at_fire", []
        )
        motor = causal.get("aim_motor") or {}
        random_aim = causal.get("random_aim") or {}
        balanced_program = random_aim.get("program") or {}
        motor_profile = (
            motor.get("profile")
            or balanced_program.get("motor_profile")
            or {}
        )
        motor_style = str(
            motor_profile.get(
                "style",
                balanced_program.get("family", "legacy"),
            )
        )
        exact_lock_fraction = motor.get("exact_lock_fraction")
        enemy_policy = str(
            (episode_record.get("enemy_policy") or {}).get(
                "name", "unknown"
            )
        )
        enemy_random = causal.get("enemy_random_policy") or {}
        per_shot = causal.get("per_shot") or {}
        player_path = causal.get("player_path") or {}
        movement_program = player_path.get("program")
        movement_profile = (
            str(movement_program.get("profile", "unknown"))
            if isinstance(movement_program, dict)
            else str(player_path.get("motion_class", "unknown"))
        )
        policy_check_source = (
            causal.get("policy_checks")
            or random_aim.get("checks")
            or {}
        )
        policy_checks = ", ".join(
            name
            for name, passed in policy_check_source.items()
            if passed
        )
        cards.append(
            f"""
<article data-policy="{html.escape(causal["aim_policy"], quote=True)}"
  data-program="{html.escape(shot_program, quote=True)}"
  data-horizontal="{html.escape(initial_horizontal, quote=True)}"
  data-vertical="{html.escape(initial_vertical, quote=True)}"
  data-motor="{html.escape(motor_style, quote=True)}"
  data-enemy-policy="{html.escape(enemy_policy, quote=True)}"
  data-player-motion="{html.escape(movement_profile, quote=True)}"
  data-weapon="{html.escape(weapon, quote=True)}"
  data-fire-program="{html.escape(fire_program, quote=True)}"
  data-fire-category="{html.escape(fire_category, quote=True)}"
  data-fire-count="{html.escape(str(fire_event_count), quote=True)}"
  data-miss-sector="{html.escape(miss_sector, quote=True)}"
  data-miss-magnitude="{html.escape(miss_magnitude, quote=True)}"
  data-miss-trajectory="{html.escape(miss_trajectory, quote=True)}"
  data-outcome="{html.escape(actual_outcome, quote=True)}">
  <h2>{html.escape(episode_id)}</h2>
  <video controls playsinline preload="metadata"
    src="{html.escape(relative_video)}"></video>
  <dl>
    <dt>policy</dt><dd>{html.escape(causal["aim_policy"])}</dd>
    <dt>aim motor</dt><dd>{html.escape(motor_style)}</dd>
    <dt>exact-lock fraction</dt>
      <dd>{html.escape(str(exact_lock_fraction))}</dd>
    <dt>enemy policy</dt><dd>{html.escape(enemy_policy)}</dd>
    <dt>player motion</dt><dd>{html.escape(movement_profile)}</dd>
    <dt>player path / max displacement / final displacement</dt>
      <dd>{html.escape(str(player_path.get("horizontal_path_length")))}
      / {html.escape(str(player_path.get("maximum_horizontal_displacement")))}
      / {html.escape(str(player_path.get("final_horizontal_displacement")))}</dd>
    <dt>blocked ticks / longest airborne / airborne drop</dt>
      <dd>{html.escape(str((player_path.get("movement_blockage") or {}).get("blocked_ticks")))}
      / {html.escape(str(player_path.get("longest_ungrounded_ticks")))}
      / {html.escape(str(player_path.get("maximum_airborne_drop")))}</dd>
    <dt>weapon</dt><dd>{html.escape(weapon)}</dd>
    <dt>replaces / remediation</dt>
      <dd>{html.escape(replaces_episode)} /
      {html.escape(remediation_reason)}</dd>
    <dt>shot-error program</dt><dd>{html.escape(shot_program)}</dd>
    <dt>fire program/category</dt>
      <dd>{html.escape(fire_program)} / {html.escape(fire_category)}</dd>
    <dt>planned fire-event bounds</dt>
      <dd>{html.escape(str(planned_fire.get("expected_min_fire_events")))}
      .. {html.escape(str(planned_fire.get("expected_max_fire_events")))}</dd>
    <dt>actual fire-event count</dt>
      <dd>{html.escape(str(fire_event_count))}</dd>
    <dt>planned miss sector/magnitude</dt>
      <dd>{html.escape(miss_sector)} / {html.escape(miss_magnitude)}</dd>
    <dt>planned miss trajectory</dt>
      <dd>{html.escape(miss_trajectory)}</dd>
    <dt>realized miss vectors at fire</dt>
      <dd>{html.escape(str(realized_miss_vectors))}</dd>
    <dt>initial screen</dt><dd>{html.escape(initial_cell)}</dd>
    <dt>initial realized x / y</dt>
      <dd>{html.escape(str(initial_actual.get("screen_x_normalized")))}
      / {html.escape(str(initial_actual.get("screen_y_normalized")))}</dd>
    <dt>actual outcome</dt><dd>{html.escape(actual_outcome)}</dd>
    <dt>per-shot hit / miss</dt>
      <dd>{html.escape(str(per_shot.get("hit_count")))} /
      {html.escape(str(per_shot.get("miss_count")))}</dd>
    <dt>declared-target hit / miss</dt>
      <dd>{html.escape(str(per_shot.get("target_hit_count")))} /
      {html.escape(str(per_shot.get("target_miss_count")))}</dd>
    <dt>enemy segments / hold frames / hop frames</dt>
      <dd>{html.escape(str(enemy_random.get("segment_count")))} /
      {html.escape(str(enemy_random.get("hold_frames")))} /
      {html.escape(str(enemy_random.get("hop_frames")))}</dd>
    <dt>distance</dt><dd>{html.escape(str(causal["actual_distance_bin"]))}
      ({html.escape(str(causal["reference_distance"]))})</dd>
    <dt>visible / centered</dt>
      <dd>{causal["visible_frames"]} / {causal["centered_frames"]}</dd>
    <dt>first response / acquire / reacquire</dt>
      <dd>{causal.get("first_aim_response_frame")} /
      {causal.get("first_acquisition_frame")} /
      {causal.get("first_reacquisition_frame")}</dd>
    <dt>fire frames</dt><dd>{html.escape(str(causal["fire_frames"]))}</dd>
    <dt>error at fire</dt>
      <dd>{html.escape(str(causal["angular_error_at_fire_deg"]))}</dd>
    <dt>renderer</dt>
      <dd>{html.escape(qa["runtime"]["renderer"])}</dd>
    <dt>policy proof</dt><dd>{html.escape(policy_checks)}</dd>
  </dl>
</article>"""
        )
        summary.append(
            {
                "episode_id": episode_id,
                "counterfactual_group_id": causal[
                    "counterfactual_group_id"
                ],
                "aim_policy": causal["aim_policy"],
                "aim_motor_style": motor_style,
                "exact_lock_fraction": exact_lock_fraction,
                "enemy_policy": enemy_policy,
                "player_motion_profile": movement_profile,
                "player_path": player_path,
                "weapon": weapon,
                "replaces_episode_id": replaces_episode,
                "remediation_reason": remediation_reason,
                "shot_error_program": shot_program,
                "fire_program": fire_program,
                "fire_program_category": fire_category,
                "authoritative_fire_event_count": fire_event_count,
                "per_shot_hit_count": per_shot.get("hit_count"),
                "per_shot_miss_count": per_shot.get("miss_count"),
                "target_hit_count": per_shot.get(
                    "target_hit_count"
                ),
                "target_miss_count": per_shot.get(
                    "target_miss_count"
                ),
                "enemy_segment_count": enemy_random.get(
                    "segment_count"
                ),
                "enemy_hold_frames": enemy_random.get("hold_frames"),
                "enemy_hop_frames": enemy_random.get("hop_frames"),
                "planned_miss_direction_sector": miss_sector,
                "planned_miss_magnitude_bin": miss_magnitude,
                "planned_miss_trajectory_style": miss_trajectory,
                "realized_miss_vectors_at_fire": (
                    realized_miss_vectors
                ),
                "initial_screen_horizontal": initial_planned.get(
                    "screen_horizontal"
                ),
                "initial_screen_vertical": initial_planned.get(
                    "screen_vertical"
                ),
                "initial_screen_actual": initial_actual,
                "actual_outcome": causal["actual_outcome"],
                "actual_distance_bin": causal["actual_distance_bin"],
                "video": str(episode / "video.mkv"),
                "passed": causal["passed"],
            }
        )
    dimensions = {
        "policy": Counter(row["aim_policy"] for row in summary),
        "program": Counter(
            row["shot_error_program"] for row in summary
        ),
        "motor": Counter(
            row["aim_motor_style"] for row in summary
        ),
        "enemy_policy": Counter(
            row["enemy_policy"] for row in summary
        ),
        "player_motion": Counter(
            row["player_motion_profile"] for row in summary
        ),
        "weapon": Counter(row["weapon"] for row in summary),
        "fire_program": Counter(
            row["fire_program"] for row in summary
        ),
        "fire_category": Counter(
            row["fire_program_category"] for row in summary
        ),
        "fire_count": Counter(
            row["authoritative_fire_event_count"] for row in summary
        ),
        "miss_sector": Counter(
            row["planned_miss_direction_sector"] for row in summary
        ),
        "miss_magnitude": Counter(
            row["planned_miss_magnitude_bin"] for row in summary
        ),
        "miss_trajectory": Counter(
            row["planned_miss_trajectory_style"] for row in summary
        ),
        "horizontal": Counter(
            row["initial_screen_horizontal"] for row in summary
        ),
        "vertical": Counter(
            row["initial_screen_vertical"] for row in summary
        ),
        "outcome": Counter(
            row["actual_outcome"] for row in summary
        ),
    }

    def options(name: str) -> str:
        return "".join(
            f'<option value="{html.escape(str(value), quote=True)}">'
            f"{html.escape(str(value))} ({count})</option>"
            for value, count in sorted(dimensions[name].items())
        )

    distribution_text = html.escape(
        json.dumps(
            {
                name: dict(values)
                for name, values in dimensions.items()
            },
            indent=2,
            sort_keys=True,
        )
    )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 causal review</title>
<style>
body {{ margin: 24px; font: 14px/1.45 system-ui, sans-serif;
  color: #e8edf2; background: #11161c; }}
h1 {{ margin-bottom: 4px; }}
.toolbar {{ position: sticky; top: 0; z-index: 2; padding: 12px;
  margin: 14px 0; border: 1px solid #35404c; border-radius: 10px;
  background: #11161cee; backdrop-filter: blur(8px); }}
.toolbar label {{ display: inline-flex; flex-direction: column;
  margin: 0 10px 8px 0; color: #9eb0c2; }}
select {{ min-width: 150px; padding: 5px; color: #e8edf2;
  background: #182029; border: 1px solid #4b5b6c; }}
pre {{ white-space: pre-wrap; color: #b8c8d8; }}
.grid {{ display: grid; grid-template-columns:
  repeat(auto-fit,minmax(420px,1fr)); gap: 18px; }}
article {{ padding: 14px; border: 1px solid #35404c; border-radius: 10px;
  background: #182029; }}
h2 {{ font-size: 16px; overflow-wrap: anywhere; }}
video {{ display: block; width: 100%; background: #000; }}
dl {{ display: grid; grid-template-columns: 150px 1fr; gap: 4px 10px; }}
dt {{ color: #9eb0c2; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
code {{ color: #9fd3ff; }}
</style>
</head>
<body>
<h1>Stage-2 causal interaction review</h1>
<p>{len(summary)} accepted non-training artifacts. Labels below are realized
from authoritative telemetry.</p>
<details><summary>distribution counts</summary>
<pre>{distribution_text}</pre></details>
<div class="toolbar">
  <label>policy<select data-filter="policy">
    <option value="">all ({len(summary)})</option>{options("policy")}
  </select></label>
  <label>shot program<select data-filter="program">
    <option value="">all ({len(summary)})</option>{options("program")}
  </select></label>
  <label>aim motor<select data-filter="motor">
    <option value="">all ({len(summary)})</option>{options("motor")}
  </select></label>
  <label>enemy policy<select data-filter="enemyPolicy">
    <option value="">all ({len(summary)})</option>{options("enemy_policy")}
  </select></label>
  <label>player motion<select data-filter="playerMotion">
    <option value="">all ({len(summary)})</option>{options("player_motion")}
  </select></label>
  <label>weapon<select data-filter="weapon">
    <option value="">all ({len(summary)})</option>{options("weapon")}
  </select></label>
  <label>fire program<select data-filter="fireProgram">
    <option value="">all ({len(summary)})</option>{options("fire_program")}
  </select></label>
  <label>fire category<select data-filter="fireCategory">
    <option value="">all ({len(summary)})</option>{options("fire_category")}
  </select></label>
  <label>actual fire count<select data-filter="fireCount">
    <option value="">all ({len(summary)})</option>{options("fire_count")}
  </select></label>
  <label>miss direction<select data-filter="missSector">
    <option value="">all ({len(summary)})</option>{options("miss_sector")}
  </select></label>
  <label>miss magnitude<select data-filter="missMagnitude">
    <option value="">all ({len(summary)})</option>{options("miss_magnitude")}
  </select></label>
  <label>miss trajectory<select data-filter="missTrajectory">
    <option value="">all ({len(summary)})</option>{options("miss_trajectory")}
  </select></label>
  <label>initial horizontal<select data-filter="horizontal">
    <option value="">all ({len(summary)})</option>{options("horizontal")}
  </select></label>
  <label>initial vertical<select data-filter="vertical">
    <option value="">all ({len(summary)})</option>{options("vertical")}
  </select></label>
  <label>actual outcome<select data-filter="outcome">
    <option value="">all ({len(summary)})</option>{options("outcome")}
  </select></label>
  <span id="visible-count">{len(summary)} visible</span>
</div>
<div class="grid">{''.join(cards)}</div>
<script>
const filters = [...document.querySelectorAll("[data-filter]")];
const cards = [...document.querySelectorAll("article")];
function applyFilters() {{
  let visible = 0;
  for (const card of cards) {{
    const show = filters.every(select =>
      !select.value || card.dataset[select.dataset.filter] === select.value);
    card.hidden = !show;
    if (show) visible += 1;
  }}
  document.querySelector("#visible-count").textContent =
    `${{visible}} visible`;
}}
for (const select of filters) select.addEventListener("change", applyFilters);
</script>
</body>
</html>
"""
    review = output_root / review_directory
    atomic_text(review / "index.html", document)
    atomic_text(
        review / "gallery.json",
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
    )
    return review / "index.html"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--additional-output-root",
        type=Path,
        action="append",
        default=[],
    )
    parser.add_argument("--episode-manifest", type=Path)
    parser.add_argument(
        "--review-directory", default="review"
    )
    args = parser.parse_args()
    print(
        build(
            args.output_root.resolve(),
            tuple(
                path.resolve()
                for path in args.additional_output_root
            ),
            episode_manifest=(
                args.episode_manifest.resolve()
                if args.episode_manifest
                else None
            ),
            review_directory=args.review_directory,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
