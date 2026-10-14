                      
"""Build a stratified, hardlink-only HTML review of the 30 h duel-v11 release."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd


RANK_RE = re.compile(r"_r(?P<rank>\d{3})_")
OBSERVABLE = {"visible", "partially_visible"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def rows(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def stable_score(sample_id: str) -> int:
    return int(hashlib.sha256(sample_id.encode()).hexdigest(), 16)


def rank_of(episode_id: str) -> int:
    match = RANK_RE.search(episode_id)
    if match is None:
        raise ValueError(f"cannot parse rank: {episode_id}")
    return int(match.group("rank"))


def categories(blocks: list[dict[str, Any]]) -> set[str]:
    phases = {str(block.get("visibility_phase")) for block in blocks}
    motions = {str(block.get("motion_label")) for block in blocks}
    outside = sum(bool(block.get("fully_outside_view")) for block in blocks)
    result: set[str] = set()
    if outside == len(blocks):
        result.add("fully_offscreen")
    elif outside:
        result.add("mixed_visibility")
    else:
        result.add("fully_observed")
    if phases.intersection({"enter", "exit", "enter_and_exit", "exit_and_enter"}):
        result.add("visibility_transition")
    if "enter" in phases or "enter_and_exit" in phases or "exit_and_enter" in phases:
        result.add("enter_view")
    if "exit" in phases or "enter_and_exit" in phases or "exit_and_enter" in phases:
        result.add("exit_view")
    if any(int(block.get("enemy_fire_ticks", 0)) > 0 for block in blocks):
        result.add("enemy_fire")
    if any(bool(block.get("enemy_killed")) for block in blocks):
        result.add("enemy_killed")
    if any(bool(block.get("player_killed")) for block in blocks):
        result.add("player_killed")
    if any(bool(block.get("enemy_respawned")) for block in blocks):
        result.add("enemy_respawn")
    if any(label.startswith("player_left") for label in motions):
        result.add("move_left")
    if any(label.startswith("player_right") for label in motions):
        result.add("move_right")
    if "toward_player" in motions or any(label.endswith("_toward") for label in motions):
        result.add("move_toward")
    if "away_from_player" in motions or any(label.endswith("_away") for label in motions):
        result.add("move_away")
    if "stationary" in motions:
        result.add("stationary")
    return result


def compact_candidate(
    row: dict[str, Any], episode_meta: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    episode_id = str(row["episode_id"])
    meta = episode_meta[episode_id]
    blocks = list((row.get("prompt_structured") or {}).get("blocks") or [])
    require(len(blocks) == 5, f"{row.get('sample_id')}: expected five blocks")
    prompt_schedule = list(row.get("prompt_schedule") or [])
    require(len(prompt_schedule) == 5, f"{row.get('sample_id')}: expected five AR prompts")
    motion_labels = [str(block.get("motion_label")) for block in blocks]
    visibility_phases = [str(block.get("visibility_phase")) for block in blocks]
    return {
        "sample_id": str(row["sample_id"]),
        "episode_id": episode_id,
        "rank": rank_of(episode_id),
        "policy": str(meta["bots"]["pov_policy"]),
        "skill_a": int(meta["bots"]["aggressive_close_level"]),
        "skill_b": int(meta["bots"]["long_range_evasive_level"]),
        "offset_seconds": float(row["source_rollout_offset_sec"]),
        "video_path": str(row["video_path"]),
        "visibility_path": str(row["visibility_path"]),
        "categories": sorted(categories(blocks)),
        "motion_labels": motion_labels,
        "visibility_phases": visibility_phases,
        "ar_prompt_schedule": [str(value) for value in prompt_schedule],
        "ar_prompt_schema_version": str(row["prompt_schedule_schema_version"]),
        "semantic_revision": str(row["semantic_revision"]),
        "prompt_renderer_version": str(row["prompt_renderer_version"]),
        "enemy_fire_blocks": sum(int(block.get("enemy_fire_ticks", 0)) > 0 for block in blocks),
        "enemy_killed_blocks": sum(bool(block.get("enemy_killed")) for block in blocks),
        "player_killed_blocks": sum(bool(block.get("player_killed")) for block in blocks),
        "enemy_respawn_blocks": sum(bool(block.get("enemy_respawned")) for block in blocks),
        "stable_score": stable_score(str(row["sample_id"])),
    }


def select(candidates: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    require(len(candidates) >= count, "not enough candidates")
    coverage: Counter[str] = Counter()
    episodes: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    remaining = {item["sample_id"]: item for item in candidates}

    def keys(item: dict[str, Any]) -> list[tuple[str, float]]:
        result: list[tuple[str, float]] = [
            (f"rank:{item['rank']}", 2.0),
            (f"policy:{item['policy']}", 1.5),
            (f"rank_policy:{item['rank']}:{item['policy']}", 3.0),
            (f"skill:{item['skill_a']}-{item['skill_b']}", 1.0),
        ]
        result.extend((f"category:{name}", 4.0) for name in item["categories"])
        return result

    while len(selected) < count:
        def value(item: dict[str, Any]) -> tuple[float, int]:
            novelty = sum(weight / (1.0 + coverage[key]) for key, weight in keys(item))
            if episodes[item["episode_id"]] == 0:
                novelty += 5.0
            else:
                novelty -= 3.0 * episodes[item["episode_id"]]
            return novelty, -item["stable_score"]

        best = max(remaining.values(), key=value)
        selected.append(best)
        remaining.pop(best["sample_id"])
        episodes[best["episode_id"]] += 1
        for key, _weight in keys(best):
            coverage[key] += 1
    return sorted(selected, key=lambda item: (item["rank"], item["policy"], item["stable_score"]))


def telemetry_summary(path: Path) -> dict[str, Any]:
    frame = pd.read_parquet(
        path,
        columns=[
            "player_is_dead",
            "enemy_is_dead",
            "player_velocity_x",
            "player_velocity_y",
            "enemy_velocity_x",
            "enemy_velocity_y",
            "camera_yaw",
            "enemy_visibility_state",
        ],
    )
    speeds: list[np.ndarray] = []
    for actor in ("player", "enemy"):
        alive = ~frame[f"{actor}_is_dead"].to_numpy(dtype=bool)
        speed = np.hypot(
            frame[f"{actor}_velocity_x"].to_numpy(dtype=float),
            frame[f"{actor}_velocity_y"].to_numpy(dtype=float),
        )
        speeds.append(speed[alive & (speed > 1.0) & (speed < 150.0)])
    moving = np.concatenate(speeds) if any(len(value) for value in speeds) else np.asarray([])
    yaw = frame["camera_yaw"].to_numpy(dtype=float)
    delta = (np.diff(yaw) + 180.0) % 360.0 - 180.0
    yaw_speed = np.abs(delta) * 64.0
    yaw_speed = yaw_speed[np.isfinite(yaw_speed) & (yaw_speed < 500.0)]
    visible = frame["enemy_visibility_state"].astype(str).isin(OBSERVABLE).mean()
    return {
        "moving_speed_median": round(float(np.median(moving)), 2) if len(moving) else None,
        "moving_speed_p90": round(float(np.percentile(moving, 90)), 2) if len(moving) else None,
        "camera_yaw_speed_p95": round(float(np.percentile(yaw_speed, 95)), 2) if len(yaw_speed) else None,
        "enemy_visible_percent": round(float(visible * 100.0), 1),
    }


def make_link(source: Path, target: Path) -> None:
    require(source.is_file() and source.stat().st_size > 0, f"missing media: {source}")
    os.link(source, target)


def render_html(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>duel-v11 30h data review</title>
<style>
:root{{--bg:#09101b;--panel:#111b2b;--panel2:#162338;--line:#2a3b55;--text:#eef5ff;--muted:#9fb1c8;--cyan:#57d9ff;--green:#69e6a6;--red:#ff7d8d;--amber:#ffc76b}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(135deg,#08101b,#0e1624 60%,#0b1320);color:var(--text);font:14px/1.45 Inter,system-ui,sans-serif}}
header{{position:sticky;top:0;z-index:5;padding:18px 24px;background:rgba(9,16,27,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}
h1{{font-size:22px;margin:0 0 6px}} .sub{{color:var(--muted)}} .summary{{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}}
.metric,.chip{{border:1px solid var(--line);background:var(--panel2);border-radius:999px;padding:5px 10px}} .metric b{{color:var(--cyan)}}
.toolbar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}} select,input{{background:#101a2a;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px 10px}}
main{{padding:20px 24px 50px}} .notice{{padding:12px 14px;border:1px solid #3a5070;background:#12223a;border-radius:10px;margin-bottom:18px;color:#cfe4ff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(410px,1fr));gap:16px}} .card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:0 12px 34px rgba(0,0,0,.22)}}
video{{display:block;width:100%;aspect-ratio:832/480;background:#000}} .body{{padding:12px}} .title{{font-weight:700;font-size:15px;word-break:break-all}} .meta{{color:var(--muted);margin:5px 0 9px}}
.chips{{display:flex;flex-wrap:wrap;gap:5px;margin:7px 0}} .chip{{font-size:12px;padding:3px 7px}} .event{{border-color:#6f4050;color:#ffb5c0}} .motion{{border-color:#2d5f6c;color:#89eaff}}
.kv{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 12px;color:var(--muted);font-size:12px}} .kv b{{color:var(--text)}}
details{{margin-top:9px}} pre{{white-space:pre-wrap;word-break:break-word;background:#0a1320;padding:9px;border-radius:8px;color:#bcd0e9;font-size:11px;max-height:420px;overflow:auto}} .prompt-block{{margin:10px 0}} .prompt-time{{color:var(--cyan);font-size:12px;font-weight:700}}
h2{{margin:28px 0 12px}} .rollouts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(500px,1fr));gap:16px}}
.hidden{{display:none!important}} @media(max-width:650px){{main,header{{padding-left:12px;padding-right:12px}}.grid,.rollouts{{grid-template-columns:1fr}}}}
</style></head>
<body><header><h1>duel-v11 · 30h production data review</h1><div class="sub">分层抽样自 1,800 × 60s rollout；视频/动作/telemetry 均来自冻结生产数据。</div>
<div class="summary" id="summary"></div><div class="toolbar"><select id="category"><option value="">全部类型</option></select><select id="policy"><option value="">全部 policy</option></select><input id="search" placeholder="搜索 sample / rank / skill"></div></header>
<main><div class="notice">本页用于视觉、时序与 prompt 联合抽检。文本来自 <b>stage2canonical_v2</b>：每个 4s clip 展示 5 个 AR prompt 和一个完整 bidirectional prompt；当前视频保留白色固定准星，已移除 radar 和其他 HUD。</div>
<div class="grid" id="grid"></div><h2>60s 完整 rollout（每个 rank 一条）</h2><div class="rollouts" id="rollouts"></div></main>
<script>const DATA={data};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const summary=document.querySelector('#summary');
summary.innerHTML=[['clips',DATA.samples.length],['rollouts',DATA.rollouts.length],['policies',new Set(DATA.samples.map(x=>x.policy)).size],['ranks',new Set(DATA.samples.map(x=>x.rank)).size],['prompt','stage2canonical_v2'],['median speed','64 units/s'],['UI','crosshair only']].map(x=>`<span class="metric">${{esc(x[0])}}: <b>${{esc(x[1])}}</b></span>`).join('');
const cats=[...new Set(DATA.samples.flatMap(x=>x.categories))].sort(),pols=[...new Set(DATA.samples.map(x=>x.policy))].sort();
for(const x of cats)category.insertAdjacentHTML('beforeend',`<option>${{esc(x)}}</option>`); for(const x of pols)policy.insertAdjacentHTML('beforeend',`<option>${{esc(x)}}</option>`);
function promptBlocks(x){{return x.ar_prompt_schedule.map((p,i)=>`<div class="prompt-block"><div class="prompt-time">${{(i*.8).toFixed(1)}}–${{((i+1)*.8).toFixed(1)}}s</div><pre>${{esc(p)}}</pre></div>`).join('')}}
function card(x){{const events=x.categories.filter(c=>c.includes('killed')||c.includes('fire')||c.includes('respawn'));return `<article class="card" data-cats="${{esc(x.categories.join(' '))}}" data-policy="${{esc(x.policy)}}" data-search="${{esc((x.sample_id+' rank '+x.rank+' '+x.skill_a+'-'+x.skill_b).toLowerCase())}}"><video controls muted preload="metadata" src="${{esc(x.media)}}"></video><div class="body"><div class="title">${{esc(x.sample_id)}}</div><div class="meta">rank ${{x.rank}} · ${{esc(x.policy)}} · skill ${{x.skill_a}} vs ${{x.skill_b}} · ${{x.offset_seconds.toFixed(0)}}–${{(x.offset_seconds+4).toFixed(0)}}s</div><div class="chips">${{x.categories.map(c=>`<span class="chip ${{events.includes(c)?'event':''}}">${{esc(c)}}</span>`).join('')}}</div><div class="kv"><span>移动中位数 <b>${{x.telemetry.moving_speed_median??'—'}}</b></span><span>移动 p90 <b>${{x.telemetry.moving_speed_p90??'—'}}</b></span><span>视角转速 p95 <b>${{x.telemetry.camera_yaw_speed_p95??'—'}}°/s</b></span><span>敌人可见 <b>${{x.telemetry.enemy_visible_percent}}%</b></span></div><details open><summary>新 AR prompt · 5 × 0.8s</summary>${{promptBlocks(x)}}</details><details><summary>新 bidirectional prompt · full 4s</summary><pre>${{esc(x.bidirectional_prompt)}}</pre></details><details><summary>结构化 labels</summary><pre>motion: ${{esc(x.motion_labels.join(' | '))}}\nvisibility: ${{esc(x.visibility_phases.join(' | '))}}\nschema: ${{esc(x.ar_prompt_schema_version)}}\nrevision: ${{esc(x.semantic_revision)}}</pre></details></div></article>`}}
grid.innerHTML=DATA.samples.map(card).join('');
rollouts.innerHTML=DATA.rollouts.map(x=>`<article class="card"><video controls muted preload="metadata" src="${{esc(x.media)}}"></video><div class="body"><div class="title">rank ${{x.rank}} · ${{esc(x.policy)}}</div><div class="meta">skill ${{x.skill_a}} vs ${{x.skill_b}} · full 60s · ${{esc(x.episode_id)}}</div><details><summary>新 bidirectional prompt · 75 × 0.8s</summary><pre>${{esc(x.bidirectional_prompt)}}</pre></details></div></article>`).join('');
function filter(){{const c=category.value,p=policy.value,q=search.value.trim().toLowerCase();for(const el of grid.children)el.classList.toggle('hidden',!!((c&&!el.dataset.cats.split(' ').includes(c))||(p&&el.dataset.policy!==p)||(q&&!el.dataset.search.includes(q))))}} category.onchange=policy.onchange=search.oninput=filter;
document.addEventListener('play',e=>{{if(e.target.tagName==='VIDEO')for(const v of document.querySelectorAll('video'))if(v!==e.target)v.pause()}},true);
</script></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=32)
    args = parser.parse_args()
    release = args.release_dir.resolve()
    output = args.output_dir.resolve()
    require(not output.exists(), f"refusing to overwrite: {output}")
    output.mkdir(parents=True)
    media_dir = output / "media"
    media_dir.mkdir()

    episode_meta = {
        str(row["render_id"]): row for row in rows(release / "accepted_episodes.jsonl")
    }
    require(len(episode_meta) == 1_800, f"episode metadata count: {len(episode_meta)}")
    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(rows(release / "ar_training_manifest.jsonl"), 1):
        candidates.append(compact_candidate(row, episode_meta))
        if index % 5_000 == 0:
            print(f"manifest_scan progress={index}/27000", flush=True)
    require(len(candidates) == 27_000, f"candidate rows: {len(candidates)}")
    chosen = select(candidates, args.sample_count)

    chosen_by_id = {str(item["sample_id"]): item for item in chosen}
    found_bidirectional: set[str] = set()
    for row in rows(release / "bidirectional_training_manifest.jsonl"):
        sample_id = str(row["sample_id"])
        if sample_id not in chosen_by_id:
            continue
        item = chosen_by_id[sample_id]
        item["bidirectional_prompt"] = str(row["prompt_text"])
        item["bidirectional_prompt_schema_version"] = str(row["prompt_schema_version"])
        require(
            str(row["semantic_revision"]) == item["semantic_revision"],
            f"{sample_id}: AR/bidirectional semantic revision mismatch",
        )
        found_bidirectional.add(sample_id)
    require(found_bidirectional == set(chosen_by_id), "missing bidirectional prompts")

    for index, item in enumerate(chosen):
        media_name = f"clip_{index:02d}.mp4"
        make_link(Path(item["video_path"]), media_dir / media_name)
        item["media"] = f"media/{media_name}"
        item["telemetry"] = telemetry_summary(Path(item["visibility_path"]))
        item.pop("stable_score", None)
        item.pop("video_path", None)
        item.pop("visibility_path", None)

    rollout_rows = {
        str(row["episode_id"]): row for row in rows(release / "rollout_60s_manifest.jsonl")
    }
    rollout_review: list[dict[str, Any]] = []
    for rank in range(8):
        item = next(value for value in chosen if int(value["rank"]) == rank)
        episode_id = str(item["episode_id"])
        source = Path(rollout_rows[episode_id]["video_path"])
        prompt_bundle = json.loads(Path(rollout_rows[episode_id]["prompt_bundle_path"]).read_text())
        require(int(prompt_bundle["block_count"]) == 75, f"{episode_id}: rollout prompt block count")
        media_name = f"rollout_rank_{rank:02d}.mp4"
        make_link(source, media_dir / media_name)
        rollout_review.append(
            {
                "rank": rank,
                "episode_id": episode_id,
                "policy": item["policy"],
                "skill_a": item["skill_a"],
                "skill_b": item["skill_b"],
                "media": f"media/{media_name}",
                "bidirectional_prompt": str(prompt_bundle["bidirectional_prompt"]),
                "bidirectional_prompt_schema_version": str(
                    prompt_bundle["bidirectional_prompt_schema_version"]
                ),
            }
        )

    payload = {
        "schema_version": "xonotic-duel-v11-data-review-v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_release": str(release),
        "selection": "deterministic greedy stratification over rank, policy, skill pair, visibility, motion, and combat events",
        "samples": chosen,
        "rollouts": rollout_review,
    }
    (output / "selection.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "index.html").write_text(render_html(payload), encoding="utf-8")
    print(json.dumps({"output": str(output), "clips": len(chosen), "rollouts": len(rollout_review)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
