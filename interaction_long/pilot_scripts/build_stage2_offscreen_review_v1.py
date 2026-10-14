                      
"""Build a small, isolated Stage-2 review for screen-boundary motion.

This pilot deliberately reuses the accepted v12 runtime without modifying it.
Unlike the production v12 sampler, it does not force an opposite motion every
0.8 seconds and it evaluates visibility against a category-specific contract.
All samples remain review-only and training_admitted=false.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import html
import json
import math
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

import build_samples_v12 as base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_NAME = "stage2_offscreen_motion_review_v1_20260820"
VISIBLE_STATES = {"visible", "edge_tolerant_visible"}

CATEGORY_ORDER = (
    "continuous_visible",
    "partial_edge_only",
    "exit_and_stay",
    "enter_from_offscreen",
    "exit_pause_reenter",
)

CATEGORY_ZH = {
    "continuous_visible": "持续单向、始终可见",
    "partial_edge_only": "部分越过画面边缘",
    "exit_and_stay": "完全离屏并保持离屏",
    "enter_from_offscreen": "从屏幕外单向进入",
    "exit_pause_reenter": "离屏、停留、延迟再进入",
}

CATEGORY_DESCRIPTION = {
    "continuous_visible": "全程保持同一方向，不折返，敌人始终在精确视锥内。",
    "partial_edge_only": "继续单向移动，身体进入扩大视锥容错带，但不完全消失。",
    "exit_and_stay": "单向走出扩大视锥，随后至少停留一个 prompt block，不自动折返。",
    "enter_from_offscreen": "开头位于扩大视锥外，沿单一方向进入画面后停住。",
    "exit_pause_reenter": "少量真实折返对照：先离屏、在屏外停留，再延迟反向进入；不在触边瞬间反向。",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wrap_angle(value: float) -> float:
    return (float(value) + 180.0) % 360.0 - 180.0


def make_cells(samples_per_category: int) -> list[dict[str, Any]]:
                                                                             
                                                                    
    category_maps = {
        "continuous_visible": "geoplanetary",
        "partial_edge_only": "geoplanetary",
        "exit_and_stay": "bromine",
        "enter_from_offscreen": "geoplanetary",
        "exit_pause_reenter": "bromine",
    }
    appearances = base.APPEARANCES
    weapons = base.WEAPONS
    cells: list[dict[str, Any]] = []
    ordinal = 0
    for category_index, category in enumerate(CATEGORY_ORDER):
        for variant in range(samples_per_category):
            direction_code = 1 if variant % 2 == 0 else 2
            opposite = base.OPPOSITE_MOTION_CODE[direction_code]
            same_edge_sign = -1.0 if direction_code == 1 else 1.0
            if category == "continuous_visible":
                program = (direction_code,) * 4 + (0,)
                target_units = 380.0
                distance_tier = "d5"
                yaw_offset = 0.0
            elif category == "partial_edge_only":
                program = (
                    (direction_code,) * 5
                    if direction_code == 1
                    else (direction_code,) * 4 + (0,)
                )
                target_units = 380.0
                distance_tier = "d5"
                yaw_offset = 0.0 if direction_code == 1 else 6.0
            elif category == "exit_and_stay":
                program = (direction_code, direction_code, 0, 0, 0)
                target_units = 270.0
                distance_tier = "d3"
                yaw_offset = same_edge_sign * (
                    30.0 if direction_code == 1 else 35.0
                )
            elif category == "enter_from_offscreen":
                program = (direction_code, direction_code, direction_code, 0, 0)
                target_units = 270.0
                distance_tier = "d3"
                                                                             
                                                                  
                yaw_offset = -same_edge_sign * 67.0
            elif category == "exit_pause_reenter":
                program = (
                    direction_code,
                    direction_code,
                    0,
                    opposite,
                    opposite,
                )
                target_units = 270.0
                distance_tier = "d3"
                yaw_offset = same_edge_sign * 30.0
            else:
                raise AssertionError(category)

            model, skin = appearances[
                (ordinal * 5 + category_index) % len(appearances)
            ]
            cells.append(
                {
                    "index": ordinal,
                    "group_id": f"o{ordinal + 1:03d}",
                    "repeat": variant,
                    "visibility_category": category,
                    "motion_label": base.CODE_LABEL[direction_code],
                    "motion_code": direction_code,
                    "desired_outcome": "no_fire",
                    "desired_model": model,
                    "desired_skin": skin,
                    "desired_weapon": weapons[
                        (ordinal * 4 + category_index) % len(weapons)
                    ],
                    "desired_map": (
                        category_maps[category]
                        if direction_code == 1
                        else "opium"
                    ),
                    "distance_tier": distance_tier,
                    "target_initial_distance_units": target_units,
                    "view_yaw_offset_deg": yaw_offset,
                    "program": program,
                }
            )
            ordinal += 1
    return cells


def select_designs(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outcomes = base.corrected_outcomes()
    candidates: list[tuple[dict[str, Any], int]] = []
    with base.DESIGN_MANIFEST.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            source = json.loads(line)
            episode_id = str(source.get("episode_id", ""))
            formal_design = source.get("formal_design") or {}
            if (
                outcomes.get(episode_id) != "no_fire"
                or formal_design.get("outcome_recipe") != "no_fire"
                or formal_design.get("player_motion_class")
                != "certified_stationary_preflight_pair"
                or int((source.get("enemy") or {}).get("motion", -1)) != 0
                or formal_design.get("distance_bin") != "near"
            ):
                continue
            candidates.append((source, line_number))

                                                                             
                                                                           
    used: set[tuple[str, str]] = set()
    selected: list[dict[str, Any]] = []
    for cell in cells:
        eligible = []
        for source, line_number in candidates:
            source_key = (
                str(cell["visibility_category"]),
                str(source["episode_id"]),
            )
            if source_key in used:
                continue
            if source["map"] != cell["desired_map"]:
                continue
            player = source["player"]["origin"]
            enemy = source["enemy"]["origin"]
            source_distance = math.dist(player, enemy)
            if source_distance + 1e-6 < cell["target_initial_distance_units"]:
                continue
            eligible.append((source, line_number))
        if not eligible:
            raise RuntimeError(f"no source for category cell: {cell}")
        eligible.sort(
            key=lambda item: (
                base.aim_policy_rank(item[0]),
                0 if item[0]["weapon"] == cell["desired_weapon"] else 1,
                item[0]["episode_id"],
            )
        )
        source, line_number = eligible[0]
        used.add(
            (
                str(cell["visibility_category"]),
                str(source["episode_id"]),
            )
        )
        selected.append(
            {**cell, "source": source, "source_line_number": line_number}
        )
    return selected


def build_scenario(design: dict[str, Any]) -> dict[str, Any]:
    scenario = base.build_scenario(design["source"], design, frozen=False)
    category = str(design["visibility_category"])
    episode_id = (
        f"s2offv1_{CATEGORY_ORDER.index(category):02d}_"
        f"{design['index']:03d}_{category}"
    )
    scenario.update(
        {
            "schema_version": "xonotic-stage2-offscreen-review-scenario-v1",
            "episode_id": episode_id,
            "dataset_role": "stage2_offscreen_motion_review_only_v1",
            "visibility_program": {
                "schema_version": "xonotic-stage2-visibility-program-v1",
                "category": category,
                "category_description": CATEGORY_DESCRIPTION[category],
                "frustum_tolerance_scale": base.FRUSTUM_TOLERANCE_SCALE,
                "occlusion_allowed": False,
                "view_yaw_offset_deg": design["view_yaw_offset_deg"],
            },
            "training_admitted": False,
            "formal_collection_authorized": False,
        }
    )
    scenario["enemy"]["health"] = 999.0
    scenario["enemy"]["armor"] = 0.0

    player = scenario["player"]["origin"]
    enemy = scenario["enemy"]["origin"]
    target_bearing = math.degrees(
        math.atan2(enemy[1] - player[1], enemy[0] - player[0])
    )
    yaw_offset = float(design["view_yaw_offset_deg"])
    scenario["player"]["yaw"] = wrap_angle(target_bearing + yaw_offset)
    scenario["initial_screen_design"] = {
        "schema_version": "xonotic-stage2-offscreen-initial-screen-design-v1",
        "expected_visible_at_output_start": category
        != "enter_from_offscreen",
        "view_yaw_offset_deg": yaw_offset,
        "screen_horizontal": "not_encoded_in_prompt",
        "screen_vertical": str(
            (design["source"].get("initial_screen_design") or {}).get(
                "screen_vertical", "center"
            )
        ),
    }

                                                                               
                                                                            
                                                      
    reference = copy.deepcopy(scenario["action_reference_motion_program"])
    reference.update(
        {
            "speed_units_per_second": 0.0,
            "direction_codes": [0, 0, 0, 0, 0],
            "primary_motion": "stationary",
        }
    )
    scenario["action_reference_motion_program"] = reference
    scenario["enemy_motion_program"]["direction_codes"] = list(
        design["program"]
    )
    scenario["enemy_motion_program"]["primary_motion"] = str(
        design["motion_label"]
    )
    return scenario


def run_lengths(states: list[str], value: str) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, state in enumerate(states + ["__sentinel__"]):
        if state == value and start is None:
            start = index
        elif state != value and start is not None:
            runs.append((start, index))
            start = None
    return runs


def visibility_metrics(visibility: pd.DataFrame) -> dict[str, Any]:
    alive = visibility[
        visibility["enemy_present"].astype(bool)
        & (pd.to_numeric(visibility["enemy_health"], errors="raise") > 0)
    ].copy()
    states = alive["visibility_state"].astype(str).tolist()
    offscreen = [state == "offscreen" for state in states]
    offscreen_runs = run_lengths(states, "offscreen")
    first_offscreen = next((i for i, value in enumerate(offscreen) if value), None)
    first_visible = next(
        (i for i, state in enumerate(states) if state in VISIBLE_STATES), None
    )
    reentry_after_offscreen = None
    if first_offscreen is not None:
        reentry_after_offscreen = next(
            (
                i
                for i in range(first_offscreen + 1, len(states))
                if states[i] in VISIBLE_STATES
            ),
            None,
        )
    x = pd.to_numeric(alive["enemy_screen_x_norm"], errors="raise")
    counts = Counter(states)
    return {
        "alive_frames": len(states),
        "counts": dict(sorted(counts.items())),
        "initial_state": states[0] if states else None,
        "final_state": states[-1] if states else None,
        "first_offscreen_frame": first_offscreen,
        "first_visible_frame": first_visible,
        "reentry_after_offscreen_frame": reentry_after_offscreen,
        "offscreen_runs": [
            {"start_frame": start, "end_frame_exclusive": end, "frames": end - start}
            for start, end in offscreen_runs
        ],
        "longest_offscreen_run_frames": max(
            (end - start for start, end in offscreen_runs), default=0
        ),
        "initial_x_norm": float(x.iloc[0]) if len(x) else None,
        "final_x_norm": float(x.iloc[-1]) if len(x) else None,
        "minimum_x_norm": float(x.min()) if len(x) else None,
        "maximum_x_norm": float(x.max()) if len(x) else None,
    }


def category_contract(category: str, metrics: dict[str, Any]) -> dict[str, Any]:
    counts = metrics["counts"]
    offscreen = int(counts.get("offscreen", 0))
    partial = int(counts.get("edge_tolerant_visible", 0))
    first_offscreen = metrics["first_offscreen_frame"]
    first_visible = metrics["first_visible_frame"]
    reentry = metrics["reentry_after_offscreen_frame"]
    final_visible = metrics["final_state"] in VISIBLE_STATES
    initial_visible = metrics["initial_state"] in VISIBLE_STATES
    final_32_offscreen = metrics["final_state"] == "offscreen" and any(
        run["end_frame_exclusive"] == metrics["alive_frames"]
        and run["frames"] >= 32
        for run in metrics["offscreen_runs"]
    )
    checks: dict[str, bool] = {
        "enemy_alive_for_prompt_window": metrics["alive_frames"] == 256,
        "no_occlusion": int(counts.get("occluded", 0)) == 0,
    }
    if category == "continuous_visible":
        checks.update(
            {
                "starts_visible": initial_visible,
                "no_partial_edge_frames": partial == 0,
                "no_offscreen_frames": offscreen == 0,
            }
        )
    elif category == "partial_edge_only":
        checks.update(
            {
                "starts_visible": initial_visible,
                "has_partial_edge_frames": partial >= 8,
                "no_offscreen_frames": offscreen == 0,
            }
        )
    elif category == "exit_and_stay":
        checks.update(
            {
                "starts_visible": initial_visible,
                "exits_after_start": first_offscreen is not None
                and first_offscreen >= 16,
                "stays_offscreen_at_end_for_32_frames": final_32_offscreen,
                "does_not_reenter": reentry is None,
            }
        )
    elif category == "enter_from_offscreen":
        checks.update(
            {
                "starts_offscreen": metrics["initial_state"] == "offscreen",
                "initial_offscreen_run_at_least_16_frames": bool(
                    metrics["offscreen_runs"]
                    and metrics["offscreen_runs"][0]["start_frame"] == 0
                    and metrics["offscreen_runs"][0]["frames"] >= 16
                ),
                "enters_after_start": first_visible is not None
                and first_visible >= 16,
                "ends_visible": final_visible,
                "no_second_offscreen_run": len(metrics["offscreen_runs"]) == 1,
            }
        )
    elif category == "exit_pause_reenter":
        checks.update(
            {
                "starts_visible": initial_visible,
                "has_offscreen_run_at_least_16_frames": (
                    metrics["longest_offscreen_run_frames"] >= 16
                ),
                "reenters_after_offscreen": reentry is not None,
                "ends_visible": final_visible,
            }
        )
    else:
        raise AssertionError(category)
    return {"checks": checks, "passed": all(checks.values())}


def movement_sentence(label: str) -> str:
    return base.PROMPT_SENTENCE[label]


def render_prompt(
    scenario: dict[str, Any],
    visibility: pd.DataFrame,
    interaction: dict[str, Any],
) -> dict[str, Any]:
    states = visibility.iloc[: base.PROMPT_TICKS]["visibility_state"].astype(str)
    blocks = []
    lines = ["[ENEMY MOTION, VISIBILITY, AND OUTCOME]"]
    program = scenario["enemy_motion_program"]["direction_codes"]
    for block_index, code in enumerate(program):
        start_frame = int(round(block_index * base.BLOCK_SECONDS * base.TICK_HZ))
        end_frame = int(
            round((block_index + 1) * base.BLOCK_SECONDS * base.TICK_HZ)
        )
        block_states = states.iloc[start_frame:end_frame].tolist()
        first_state = block_states[0]
        last_state = block_states[-1]
        label = base.CODE_LABEL[int(code)]
        if all(state == "offscreen" for state in block_states):
            if label == "stationary":
                sentence = "The opponent remains out of view."
            else:
                movement = movement_sentence(label).removeprefix(
                    "The opponent "
                ).rstrip(".")
                if movement.startswith("moves "):
                    movement = "moving " + movement.removeprefix("moves ")
                sentence = f"The opponent remains out of view while {movement}."
        else:
            sentence = movement_sentence(label)
            if first_state != "offscreen" and last_state == "offscreen":
                sentence = sentence.rstrip(".") + " and moves out of view."
            elif first_state == "offscreen" and last_state in VISIBLE_STATES:
                sentence = sentence.rstrip(".") + " and enters the view."
            elif "edge_tolerant_visible" in block_states:
                sentence = (
                    sentence.rstrip(".")
                    + " and becomes partly cropped by the edge of the view."
                )
        combat = base.combat_label_for_block(interaction, block_index)
        sentence = sentence + " " + base.COMBAT_SENTENCE[combat]
        start_seconds = block_index * base.BLOCK_SECONDS
        end_seconds = (block_index + 1) * base.BLOCK_SECONDS
        blocks.append(
            {
                "block_index": block_index,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "motion_label": label,
                "visibility_start": first_state,
                "visibility_end": last_state,
                "combat_outcome": combat,
                "text": sentence,
            }
        )
        lines.append(f"{start_seconds:.1f}-{end_seconds:.1f}s: {sentence}")
    return {
        "schema_version": "xonotic-stage2-offscreen-motion-prompt-v1",
        "provenance": "rendered_from_64hz_motion_visibility_and_events",
        "visibility_category": scenario["visibility_program"]["category"],
        "desired_outcome": scenario["intent_outcome"],
        "actual_outcome": interaction["actual_outcome"],
        "camera_action_described_in_text": False,
        "uses_absolute_screen_region": False,
        "uses_distance_magnitude_adjective": False,
        "uses_percentage": False,
        "blocks": blocks,
        "prompt_text": "\n".join(lines),
    }


def finalize_episode(record: dict[str, Any]) -> dict[str, Any]:
    episode = Path(record["episode_path"])
    scenario = json.loads((episode / "scenario.json").read_text())
    qa = json.loads((episode / "qa.json").read_text())
    interaction = json.loads(
        (episode / "telemetry/interaction.json").read_text()
    )
    visibility = pd.read_parquet(
        episode / "telemetry/visibility_64hz.parquet"
    )
    category = str(scenario["visibility_program"]["category"])
    metrics = visibility_metrics(visibility)
    contract = category_contract(category, metrics)
    prompt = render_prompt(scenario, visibility, interaction)

    legacy_checks = dict(qa["checks"])
    checks = {
        key: value
        for key, value in legacy_checks.items()
        if key != "no_true_offscreen_after_tolerance"
    }
    checks["visibility_category_contract"] = bool(contract["passed"])
    qa.update(
        {
            "schema_version": "xonotic-stage2-offscreen-review-episode-qa-v1",
            "checks": checks,
            "legacy_v12_visibility_check": {
                "no_true_offscreen_after_tolerance": legacy_checks.get(
                    "no_true_offscreen_after_tolerance"
                )
            },
            "visibility_category": category,
            "visibility_category_metrics": metrics,
            "visibility_category_contract": contract,
            "review_passed": all(checks.values()),
            "pre_pair_passed": all(checks.values()),
            "training_admitted": False,
        }
    )
    write_json(episode / "prompt.json", prompt)
    write_json(episode / "qa.json", qa)
    record["prompt"] = prompt
    record["qa"] = qa
    return record


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_review_page(output_root: Path, rows: list[dict[str, Any]]) -> str:
    by_category = {category: [] for category in CATEGORY_ORDER}
    for row in rows:
        by_category[row["visibility_category"]].append(row)
    sections = []
    for category in CATEGORY_ORDER:
        cards = []
        for row in by_category[category]:
            episode_id = row["sample_id"]
            prompt = row["prompt"]
            timeline = "".join(
                f"<div class='block'><small>{b['start_seconds']:.1f}–{b['end_seconds']:.1f}s"
                f" · {esc(b['visibility_start'])}→{esc(b['visibility_end'])}</small>"
                f"<b>{esc(b['text'])}</b></div>"
                for b in prompt["blocks"]
            )
            metrics = row["visibility_metrics"]
            state = "PASS" if row["review_passed"] else "CHECK"
            state_class = "pass" if row["review_passed"] else "check"
            failed = ", ".join(row["failed_checks"]) or "none"
            cards.append(
                f"""
                <article class="card {state_class}">
                  <div class="head"><div><code>{esc(episode_id)}</code><h3>{esc(row['map'])} · {esc(row['weapon'])}</h3></div><span>{state}</span></div>
                  <video controls muted playsinline preload="metadata" src="../episodes/{esc(episode_id)}/media/review_20hz_81f.mp4"></video>
                  <div class="facts">
                    <span>program <b>{esc(row['direction_codes'])}</b></span>
                    <span>x <b>{metrics['initial_x_norm']:.2f} → {metrics['final_x_norm']:.2f}</b></span>
                    <span>visible <b>{metrics['counts'].get('visible', 0)}f</b></span>
                    <span>partial <b>{metrics['counts'].get('edge_tolerant_visible', 0)}f</b></span>
                    <span>offscreen <b>{metrics['counts'].get('offscreen', 0)}f</b></span>
                    <span>enemy <b>{esc(row['enemy'])}</b></span>
                  </div>
                  <div class="timeline">{timeline}</div>
                  <details><summary>Prompt / QA</summary><pre>{esc(prompt['prompt_text'])}</pre><p>failed: {esc(failed)}</p><p><a href="../episodes/{esc(episode_id)}/qa.json">qa.json</a> · <a href="../episodes/{esc(episode_id)}/scenario.json">scenario.json</a> · <a href="../episodes/{esc(episode_id)}/telemetry/visibility_64hz.parquet">visibility parquet</a></p></details>
                </article>
                """
            )
        passed = sum(int(row["review_passed"]) for row in by_category[category])
        sections.append(
            f"<section><h2>{esc(CATEGORY_ZH[category])} <em>{passed}/{len(by_category[category])}</em></h2><p class='desc'>{esc(CATEGORY_DESCRIPTION[category])}</p>{''.join(cards)}</section>"
        )
    total_passed = sum(int(row["review_passed"]) for row in rows)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 offscreen motion review v1</title>
<style>
:root{{color-scheme:dark;--bg:#070a10;--panel:#111722;--line:#2a3548;--text:#eef5ff;--muted:#96a5bb;--cyan:#55dffc;--green:#55e6a5;--amber:#ffc05b}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 20% 0,#17243b,var(--bg) 45%);color:var(--text);font:14px/1.5 Inter,system-ui,sans-serif}}main{{width:min(1460px,calc(100% - 32px));margin:auto;padding:42px 0 80px}}h1{{font-size:clamp(32px,5vw,58px);margin:5px 0}}header p,.desc{{color:var(--muted);max-width:980px}}.summary{{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0 36px}}.metric{{padding:12px 16px;border:1px solid var(--line);background:#111722;border-radius:12px}}section{{margin:38px 0}}h2{{border-bottom:1px solid var(--line);padding-bottom:10px}}h2 em{{font-style:normal;color:var(--cyan);font-size:14px}}.card{{background:rgba(17,23,34,.96);border:1px solid var(--line);border-radius:16px;padding:16px;margin:14px 0}}.card.check{{border-color:#856326}}.head{{display:flex;justify-content:space-between;align-items:start}}.head h3{{margin:5px 0 12px}}.head span{{padding:5px 10px;border-radius:99px;background:var(--green);color:#04110b;font-weight:800}}.check .head span{{background:var(--amber);color:#191000}}video{{display:block;width:min(100%,960px);aspect-ratio:16/9;background:#000;border-radius:10px;border:1px solid var(--line)}}.facts{{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--muted);margin:12px 0}}.facts b{{color:var(--text)}}.timeline{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}}.block{{padding:9px;background:#090e16;border:1px solid var(--line);border-top:3px solid var(--cyan);border-radius:8px;min-height:90px}}.block small{{display:block;color:var(--muted)}}.block b{{display:block;margin-top:5px;font-size:12px}}details{{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}}pre{{white-space:pre-wrap;background:#080c12;padding:12px;border-radius:8px}}a{{color:var(--cyan)}}code{{color:var(--cyan)}}@media(max-width:850px){{.timeline{{grid-template-columns:1fr}}}}
</style></head><body><main><header><code>XONOTIC · STAGE-2 · OFFSCREEN PILOT V1</code><h1>敌人进出画面分类 Review</h1><p>固定 96 u/s、5 × 0.8s、镜头 action 不追踪敌人。扩大视锥仍为 1.12×；部分身体出边不算离屏，只有全部身体采样点越过扩大视锥才标记 offscreen。障碍遮挡继续拒绝。</p><div class="summary"><div class="metric">样例 <b>{len(rows)}</b></div><div class="metric">自动类别门通过 <b>{total_passed}/{len(rows)}</b></div><div class="metric">training_admitted <b>false</b></div><div class="metric">旧 Stage-1/2 <b>未修改</b></div></div></header>{''.join(sections)}</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME)
    parser.add_argument("--samples-per-category", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--port-base", type=int, default=24100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse already packaged episodes in an incomplete review output",
    )
    args = parser.parse_args()
    if not 1 <= args.samples_per_category <= 8:
        parser.error("--samples-per-category must be between 1 and 8")
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    if "PENDING" in base.BUILD_TAG or "PENDING" in base.SOURCE_COMMIT:
        raise RuntimeError(
            "set XONOTIC_STAGE2_MOTION_INTERACTION_BUILD_TAG and source commit"
        )

    cells = make_cells(args.samples_per_category)
    designs = select_designs(cells)
    if args.dry_run:
        print(json.dumps(designs, indent=2, sort_keys=True))
        return 0

    output_root = ROOT / "outputs" / args.output_name
    if output_root.exists() and not args.resume:
        raise RuntimeError(f"refusing to overwrite output: {output_root}")
    output_root.mkdir(parents=True, exist_ok=args.resume)
    scratch_root = Path(os.environ["XONOTIC_CAPTURE_TMP"]) / args.output_name
    scratch_root.mkdir(parents=True, exist_ok=args.resume)
    base.run_protection_check(output_root / "STAGE12_PRECHECK.txt")

    def capture_one(local_index: int, design: dict[str, Any]) -> dict[str, Any]:
        scenario = build_scenario(design)
        destination = output_root / "episodes" / scenario["episode_id"]
        if args.resume and (destination / "qa.json").is_file():
            record = base.load_packaged_episode(output_root, scenario["episode_id"])
        else:
            record = base.capture_episode(
                scenario,
                output_root,
                scratch_root,
                port=args.port_base + local_index,
                retain_raw_avi=False,
            )
        return finalize_episode(record)

    completed: dict[int, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(capture_one, index, design): index
            for index, design in enumerate(designs)
        }
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            completed[index] = future.result()
            print(
                f"completed {index + 1}/{len(designs)} "
                f"{completed[index]['episode_id']}",
                flush=True,
            )

    records = [completed[index] for index in range(len(designs))]
    base.run_protection_check(output_root / "STAGE12_POSTCHECK.txt")
    rows: list[dict[str, Any]] = []
    for design, record in zip(designs, records):
        qa = record["qa"]
        scenario = record["scenario"]
        rows.append(
            {
                "schema_version": "xonotic-stage2-offscreen-review-row-v1",
                "sample_id": record["episode_id"],
                "visibility_category": design["visibility_category"],
                "review_passed": bool(qa["review_passed"]),
                "training_admitted": False,
                "video_path": record["review_video"],
                "prompt": record["prompt"],
                "visibility_metrics": qa["visibility_category_metrics"],
                "failed_checks": [
                    key for key, value in qa["checks"].items() if not value
                ],
                "direction_codes": scenario["enemy_motion_program"][
                    "direction_codes"
                ],
                "map": scenario["map"],
                "weapon": scenario["weapon"],
                "enemy": (
                    f"{scenario['enemy_model']}:skin{scenario['enemy_skin']}:"
                    f"color{scenario['enemy_color']}"
                ),
                "source_formal_episode_id": scenario[
                    "source_formal_episode_id"
                ],
            }
        )

    manifest = output_root / "review_manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")
    summary = {
        "schema_version": "xonotic-stage2-offscreen-review-summary-v1",
        "output_root": str(output_root),
        "runtime_build_tag": base.BUILD_TAG,
        "runtime_source_commit": base.SOURCE_COMMIT,
        "samples": len(rows),
        "review_passed": sum(int(row["review_passed"]) for row in rows),
        "category_counts": dict(
            Counter(row["visibility_category"] for row in rows)
        ),
        "category_passed": {
            category: sum(
                int(row["review_passed"])
                for row in rows
                if row["visibility_category"] == category
            )
            for category in CATEGORY_ORDER
        },
        "training_admitted": False,
        "capture_policy": {
            "speed_units_per_second": base.SPEED_UNITS_PER_SECOND,
            "prompt_blocks": 5,
            "block_seconds": base.BLOCK_SECONDS,
            "camera_target_motion_reference": "stationary_open_loop",
            "occlusion_allowed": False,
            "frustum_tolerance_scale": base.FRUSTUM_TOLERANCE_SCALE,
            "periodic_every_block_reversal": False,
        },
        "stage1_stage2_protection_precheck_passed": True,
        "stage1_stage2_protection_postcheck_passed": True,
    }
    write_json(output_root / "SUMMARY.json", summary)
    review_dir = output_root / "review"
    review_dir.mkdir(exist_ok=args.resume)
    (review_dir / "index.html").write_text(
        render_review_page(output_root, rows), encoding="utf-8"
    )
    artifacts = {
        str(path.relative_to(output_root)): sha256_file(path)
        for path in sorted(output_root.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS"
    }
    with (output_root / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for relative, digest in artifacts.items():
            handle.write(f"{digest}  {relative}\n")
    shutil.rmtree(scratch_root, ignore_errors=True)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(review_dir / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
