                      
"""Build an isolated HTML review for the close-range no-crosshair pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


OBSERVABLE = {"visible", "partially_visible"}
NEW_RENDER_IDS = [
    "duel_v12_close_review_smoke_e00_render_v2",
    *[f"duel_v12_close_review_e{index:02d}_render" for index in range(1, 8)],
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def media_link(source: Path, target: Path) -> None:
    require(source.is_file() and source.stat().st_size > 0, f"missing media: {source}")
    os.link(source, target)


def visible_arrays(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    frame = pd.read_parquet(
        path,
        columns=[
            "enemy_is_dead",
            "enemy_visibility_state",
            "enemy_distance",
            "fov_y",
            "player_is_dead",
            "player_velocity_x",
            "player_velocity_y",
            "enemy_velocity_x",
            "enemy_velocity_y",
        ],
    )
    visible = (
        ~frame["enemy_is_dead"].astype(bool)
        & frame["enemy_visibility_state"].astype(str).isin(OBSERVABLE)
        & np.isfinite(frame["enemy_distance"])
        & (frame["enemy_distance"] > 0)
    )
    distance = frame.loc[visible, "enemy_distance"].to_numpy(dtype=float)
    fov_y = frame.loc[visible, "fov_y"].to_numpy(dtype=float)
                                                                   
                                                                             
    height = 69.0 * 480.0 / (2.0 * distance * np.tan(np.deg2rad(fov_y) / 2.0))
    speeds: list[np.ndarray] = []
    for actor in ("player", "enemy"):
        speed = np.hypot(
            frame[f"{actor}_velocity_x"].to_numpy(dtype=float),
            frame[f"{actor}_velocity_y"].to_numpy(dtype=float),
        )
        alive = ~frame[f"{actor}_is_dead"].to_numpy(dtype=bool)
        speeds.append(speed[alive & (speed > 1.0) & (speed < 150.0)])
    return distance, height, np.concatenate(speeds), len(frame)


def summarize_arrays(
    distances: Iterable[np.ndarray],
    heights: Iterable[np.ndarray],
    speeds: Iterable[np.ndarray],
    total_ticks: int,
) -> dict[str, Any]:
    distance = np.concatenate(list(distances))
    height = np.concatenate(list(heights))
    speed = np.concatenate(list(speeds))
    return {
        "rollouts": None,
        "visible_ticks": int(len(distance)),
        "visible_percent": round(float(len(distance) / total_ticks * 100.0), 1),
        "distance_p25": round(float(np.percentile(distance, 25)), 1),
        "distance_p50": round(float(np.percentile(distance, 50)), 1),
        "distance_p75": round(float(np.percentile(distance, 75)), 1),
        "height_px_p25": round(float(np.percentile(height, 25)), 1),
        "height_px_p50": round(float(np.percentile(height, 50)), 1),
        "height_px_p75": round(float(np.percentile(height, 75)), 1),
        "height_under_50_percent": round(float((height < 50).mean() * 100.0), 1),
        "height_50_to_80_percent": round(
            float(((height >= 50) & (height < 80)).mean() * 100.0), 1
        ),
        "height_at_least_80_percent": round(float((height >= 80).mean() * 100.0), 1),
        "moving_speed_p50": round(float(np.percentile(speed, 50)), 2),
        "moving_speed_p90": round(float(np.percentile(speed, 90)), 2),
    }


def one_stats(path: Path) -> dict[str, Any]:
    distance, height, speed, ticks = visible_arrays(path)
    value = summarize_arrays([distance], [height], [speed], ticks)
    value.pop("rollouts")
    return value


def block_categories(blocks: list[dict[str, Any]]) -> list[str]:
    result: set[str] = set()
    outside = sum(bool(block["fully_outside_view"]) for block in blocks)
    result.add("offscreen" if outside == len(blocks) else "mixed" if outside else "in_view")
    for block in blocks:
        phase = str(block["visibility_phase"])
        if phase in {"enter", "exit", "enter_and_exit", "exit_and_enter"}:
            result.add(phase)
        motion = str(block["motion_label"])
        if motion != "unobserved":
            result.add(motion)
        if int(block["enemy_fire_ticks"]) > 0:
            result.add("enemy_fire")
        if bool(block["enemy_killed"]):
            result.add("enemy_killed")
        if bool(block["player_killed"]):
            result.add("player_killed")
        if bool(block["enemy_respawned"]):
            result.add("enemy_respawn")
    return sorted(result)


def choose_two(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    event_weights = {
        "enemy_killed": 8,
        "player_killed": 8,
        "enemy_respawn": 7,
        "enemy_fire": 5,
        "enter": 4,
        "exit": 4,
        "enter_and_exit": 5,
        "exit_and_enter": 5,
        "mixed": 3,
    }

    def stable(row: dict[str, Any]) -> int:
        return int(hashlib.sha256(str(row["sample_id"]).encode()).hexdigest(), 16)

    def base(row: dict[str, Any]) -> int:
        return sum(event_weights.get(value, 1) for value in row["categories"])

    first = max(rows, key=lambda row: (base(row), -stable(row)))
    covered = set(first["categories"])
    remaining = [row for row in rows if row is not first]
    second = max(
        remaining,
        key=lambda row: (
            6 * len(set(row["categories"]) - covered) + base(row),
            -stable(row),
        ),
    )
    return sorted([first, second], key=lambda row: float(row["offset_seconds"]))


def render_html(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>duel-v12 close-range no-crosshair review</title>
<style>
:root{{--bg:#071018;--panel:#101b27;--panel2:#152536;--line:#29435a;--text:#edf7ff;--muted:#9ab1c5;--cyan:#5ce0ff;--green:#6ce5a3;--amber:#ffd078;--red:#ff8b9d}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 80% 0,#14283b 0,transparent 35%),var(--bg);color:var(--text);font:14px/1.48 Inter,system-ui,sans-serif}}
header{{position:sticky;top:0;z-index:5;padding:17px 22px;background:rgba(7,16,24,.95);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}h1{{margin:0 0 5px;font-size:22px}}.sub,.muted{{color:var(--muted)}}
main{{padding:20px 22px 55px}}.notice{{padding:12px 14px;border:1px solid #38627d;background:#10293a;border-radius:10px;margin-bottom:16px}}.chips,.metrics{{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}}.chip{{padding:4px 8px;border:1px solid var(--line);background:var(--panel2);border-radius:999px;font-size:12px}}
.compare{{display:grid;grid-template-columns:repeat(4,minmax(170px,1fr));gap:10px;margin:15px 0 24px}}.metric{{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:13px}}.metric .v{{font-size:24px;color:var(--green);font-weight:750}}.metric .old{{color:var(--muted)}}
h2{{margin:27px 0 12px}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:15px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:0 10px 28px rgba(0,0,0,.22)}}video{{display:block;width:100%;aspect-ratio:832/480;background:#000}}.body{{padding:12px}}.title{{font-weight:700;word-break:break-all}}.meta{{color:var(--muted);margin:4px 0 8px}}.kv{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 10px;font-size:12px;color:var(--muted)}}.kv b{{color:var(--text)}}
details{{margin-top:9px}}summary{{cursor:pointer;color:#d7edff}}pre{{white-space:pre-wrap;word-break:break-word;background:#07121c;border-radius:8px;padding:9px;color:#bdd3e5;font-size:11px;max-height:420px;overflow:auto}}.ptime{{color:var(--cyan);font-weight:700;margin-top:10px}}.baseline{{opacity:.88}}.baseline .card{{border-color:#4b3d48}}
@media(max-width:850px){{.compare{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}}}@media(max-width:520px){{main,header{{padding-left:11px;padding-right:11px}}.compare{{grid-template-columns:1fr}}}}
</style></head><body>
<header><h1>duel-v12 · close-range / no-crosshair review</h1><div class="sub">8 × 60s pilot · 4 AggressiveClose POV + 4 MidRangeEvasive POV · canonical Stage-2 motion/visibility prompts</div></header>
<main><div class="notice"><b>隔离试验，不修改现有 30h release。</b> 移动仍限速 64；隐藏出生优先 300–450 units；距离超过 550 时柔性接近，回到 420 后恢复原 policy；无准星、无 radar、无其他 HUD。</div>
<div class="compare" id="compare"></div>
<h2>新方案 · 60s 完整 rollout</h2><div class="grid" id="rollouts"></div>
<h2>新方案 · 4s clip + 精确 prompt</h2><div class="grid" id="clips"></div>
<section class="baseline"><h2>旧 30h 方案 · 视觉对照</h2><div class="muted">这里只放 4 条旧 rollout 供肉眼对比；页首旧分布来自分层抽取的 320 条 rollout（5.33h）。</div><div class="grid" id="baseline"></div></section>
</main><script>const DATA={data};
const $=s=>document.querySelector(s),esc=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const n=DATA.new_summary,o=DATA.baseline_summary;
const metrics=[['可见距离 p50',n.distance_p50+' units',o.distance_p50+' units'],['人物高度代理 p50',n.height_px_p50+' px',o.height_px_p50+' px'],['可见 tick',n.visible_percent+'%',o.visible_percent+'%'],['低于 50px',n.height_under_50_percent+'%',o.height_under_50_percent+'%']];
$('#compare').innerHTML=metrics.map(x=>`<div class="metric"><div>${{esc(x[0])}}</div><div class="v">${{esc(x[1])}}</div><div class="old">旧方案 ${{esc(x[2])}}</div></div>`).join('');
const kv=s=>`<div class="kv"><span>distance p50 <b>${{s.distance_p50}}</b></span><span>height proxy p50 <b>${{s.height_px_p50}}px</b></span><span>visible <b>${{s.visible_percent}}%</b></span><span>move p50 <b>${{s.moving_speed_p50}}</b></span></div>`;
const chips=x=>`<div class="chips">${{x.map(v=>`<span class="chip">${{esc(v)}}</span>`).join('')}}</div>`;
$('#rollouts').innerHTML=DATA.rollouts.map(x=>`<article class="card"><video controls muted preload="metadata" src="${{esc(x.media)}}"></video><div class="body"><div class="title">${{esc(x.id)}}</div><div class="meta">${{esc(x.policy)}} · skill ${{x.skill_a}} vs ${{x.skill_b}} · 60s</div>${{kv(x.stats)}}${{chips(['no crosshair','spawn 300–450','leash 550→420'])}}<details><summary>75 × 0.8s bidirectional prompt</summary><pre>${{esc(x.bidirectional_prompt)}}</pre></details></div></article>`).join('');
function arPrompts(x){{return x.ar_prompts.map((p,i)=>`<div class="ptime">${{(i*.8).toFixed(1)}}–${{((i+1)*.8).toFixed(1)}}s</div><pre>${{esc(p)}}</pre>`).join('')}}
$('#clips').innerHTML=DATA.clips.map(x=>`<article class="card"><video controls muted preload="metadata" src="${{esc(x.media)}}"></video><div class="body"><div class="title">${{esc(x.id)}}</div><div class="meta">${{esc(x.policy)}} · ${{x.offset_seconds}}–${{x.offset_seconds+4}}s</div>${{chips(x.categories)}}${{kv(x.stats)}}<details open><summary>5 × 0.8s AR prompts</summary>${{arPrompts(x)}}</details><details><summary>4s bidirectional prompt</summary><pre>${{esc(x.bidirectional_prompt)}}</pre></details></div></article>`).join('');
$('#baseline').innerHTML=DATA.baseline_examples.map(x=>`<article class="card"><video controls muted preload="metadata" src="${{esc(x.media)}}"></video><div class="body"><div class="title">旧方案 · ${{esc(x.policy)}}</div><div class="meta">skill ${{x.skill_a}} vs ${{x.skill_b}} · crosshair retained</div>${{kv(x.stats)}}</div></article>`).join('');
document.addEventListener('play',e=>{{if(e.target.tagName==='VIDEO')for(const v of document.querySelectorAll('video'))if(v!==e.target)v.pause()}},true);
</script></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--baseline-release", type=Path, required=True)
    parser.add_argument("--baseline-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    new_root = args.new_root.resolve()
    baseline_release = args.baseline_release.resolve()
    baseline_review = args.baseline_review.resolve()
    output = args.output_dir.resolve()
    require(not output.exists(), f"refusing to overwrite: {output}")
    output.mkdir(parents=True)
    media = output / "media"
    media.mkdir()

    rollout_review: list[dict[str, Any]] = []
    clip_review: list[dict[str, Any]] = []
    new_distances: list[np.ndarray] = []
    new_heights: list[np.ndarray] = []
    new_speeds: list[np.ndarray] = []
    new_ticks = 0

    for episode_index, render_id in enumerate(NEW_RENDER_IDS):
        release = new_root / "releases" / render_id
        qa = json.loads((release / "TRAINING_READY.json").read_text())
        require(bool(qa["training_ready"]) and all(qa["gates"].values()), f"not ready: {render_id}")
        render_manifest = json.loads((new_root / "renders" / render_id / "manifest.json").read_text())
        require(render_manifest["observation_contract"]["only_ui"] == [], f"UI leak: {render_id}")
        source_manifest = json.loads(Path(render_manifest["source_demo"]["path"]).parent.joinpath("manifest.json").read_text())
        policy = str(source_manifest["rollout"]["pov_policy"])
        skill_a = int(source_manifest["bots"]["aggressive_close_nominal_level"])
        skill_b = int(source_manifest["bots"]["mid_range_evasive_nominal_level"])

        rollout_visibility = release / "rollout_60s" / "visibility_64hz.parquet"
        distance, height, speed, ticks = visible_arrays(rollout_visibility)
        new_distances.append(distance)
        new_heights.append(height)
        new_speeds.append(speed)
        new_ticks += ticks
        stats = summarize_arrays([distance], [height], [speed], ticks)
        stats.pop("rollouts")
        bundle = json.loads((release / "rollout_60s" / "prompt_bundle.json").read_text())
        require("No crosshair, radar, or other HUD is visible." in bundle["bidirectional_prompt"], f"prompt UI drift: {render_id}")
        video = Path(json.loads((release / "TRAINING_READY.json").read_text())["rollout_media"]["path"])
        media_name = f"new_rollout_{episode_index:02d}.mp4"
        media_link(video, media / media_name)
        rollout_review.append(
            {
                "id": render_id,
                "policy": policy,
                "skill_a": skill_a,
                "skill_b": skill_b,
                "stats": stats,
                "media": f"media/{media_name}",
                "bidirectional_prompt": bundle["bidirectional_prompt"],
            }
        )

        bidirectional = {
            row["sample_id"]: row for row in jsonl(release / "bidirectional_training_manifest.jsonl")
        }
        candidates: list[dict[str, Any]] = []
        for row in jsonl(release / "ar_training_manifest.jsonl"):
            blocks = list(row["prompt_structured"]["blocks"])
            candidates.append(
                {
                    "sample_id": row["sample_id"],
                    "id": row["sample_id"],
                    "policy": policy,
                    "skill_a": skill_a,
                    "skill_b": skill_b,
                    "offset_seconds": int(row["source_rollout_offset_sec"]),
                    "video_path": row["video_path"],
                    "visibility_path": row["visibility_path"],
                    "categories": block_categories(blocks),
                    "ar_prompts": row["prompt_schedule"],
                    "bidirectional_prompt": bidirectional[row["sample_id"]]["prompt_text"],
                }
            )
        for selected in choose_two(candidates):
            media_name = f"new_clip_{len(clip_review):02d}.mp4"
            media_link(Path(selected.pop("video_path")), media / media_name)
            selected["media"] = f"media/{media_name}"
            selected["stats"] = one_stats(Path(selected.pop("visibility_path")))
            selected.pop("sample_id", None)
            clip_review.append(selected)

    new_summary = summarize_arrays(new_distances, new_heights, new_speeds, new_ticks)
    new_summary["rollouts"] = len(NEW_RENDER_IDS)

    baseline_meta = {
        row["render_id"]: row for row in jsonl(baseline_release / "accepted_episodes.jsonl")
    }
    baseline_rollouts = jsonl(baseline_release / "rollout_60s_manifest.jsonl")
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in baseline_rollouts:
        meta = baseline_meta[row["episode_id"]]
        grouped[(int(row["global_rank"]), str(meta["bots"]["pov_policy"]))].append(row)
    baseline_audit: list[dict[str, Any]] = []
    for key in sorted(grouped):
        baseline_audit.extend(sorted(grouped[key], key=lambda row: row["episode_id"])[:20])
    require(len(baseline_audit) == 320, f"baseline audit count: {len(baseline_audit)}")
    old_distances: list[np.ndarray] = []
    old_heights: list[np.ndarray] = []
    old_speeds: list[np.ndarray] = []
    old_ticks = 0
    for row in baseline_audit:
        distance, height, speed, ticks = visible_arrays(Path(row["visibility_path"]))
        old_distances.append(distance)
        old_heights.append(height)
        old_speeds.append(speed)
        old_ticks += ticks
    baseline_summary = summarize_arrays(old_distances, old_heights, old_speeds, old_ticks)
    baseline_summary["rollouts"] = len(baseline_audit)

    baseline_selection = json.loads((baseline_review / "selection.json").read_text())
    baseline_by_id = {row["episode_id"]: row for row in baseline_rollouts}
    baseline_examples: list[dict[str, Any]] = []
    for index, item in enumerate(baseline_selection["rollouts"][:4]):
        row = baseline_by_id[item["episode_id"]]
        media_name = f"baseline_rollout_{index:02d}.mp4"
        media_link(Path(row["video_path"]), media / media_name)
        baseline_examples.append(
            {
                "policy": item["policy"],
                "skill_a": item["skill_a"],
                "skill_b": item["skill_b"],
                "media": f"media/{media_name}",
                "stats": one_stats(Path(row["visibility_path"])),
            }
        )

    payload = {
        "schema_version": "xonotic-duel-v12-close-range-nocrosshair-review-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "movement_limit_units_per_second": 64,
            "fov": 90,
            "respawn_distance_band_units": [300, 450],
            "close_leash_hysteresis_units": [550, 420],
            "crosshair": False,
            "radar": False,
            "policies": ["AggressiveClose", "MidRangeEvasive"],
        },
        "new_summary": new_summary,
        "baseline_summary": baseline_summary,
        "rollouts": rollout_review,
        "clips": clip_review,
        "baseline_examples": baseline_examples,
    }
    (output / "selection.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "index.html").write_text(render_html(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "new_rollouts": len(rollout_review),
                "new_clips": len(clip_review),
                "baseline_examples": len(baseline_examples),
                "new_summary": new_summary,
                "baseline_summary": baseline_summary,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
