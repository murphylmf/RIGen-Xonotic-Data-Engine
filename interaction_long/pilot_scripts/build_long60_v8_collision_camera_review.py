                      
"""Build the browser review for the isolated long60 v8 qualification set."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


CAPTURE_ROOT = Path(__file__).resolve().parents[1]
PILOT_ID = "stage2_long60_v8_collision_camera_review12_v11_20260829"
DEFAULT_MANIFEST_ROOT = CAPTURE_ROOT / "manifests" / PILOT_ID
DEFAULT_REVIEW_ROOT = Path("./rigen_data/reviews") / PILOT_ID


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def interaction_text(prompt: str) -> str:
    marker = "[CURRENT OPPONENT MOTION, VISIBILITY, AND INTERACTION]"
    return prompt.split(marker, 1)[-1].strip() if marker in prompt else prompt.strip()


def load_samples(review_root: Path, manifest_root: Path) -> list[dict[str, Any]]:
    manifest_rows = {
        row["episode_id"]: row
        for row in (
            json.loads(line)
            for line in (manifest_root / "pilot_manifest.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    }
    samples: list[dict[str, Any]] = []
    for record_path in sorted(
        (review_root / "episodes" / "train").glob("*/record.json")
    ):
        episode_dir = record_path.parent
        qa_path = episode_dir / "qa.json"
        video_path = episode_dir / "video.mp4"
        if not qa_path.is_file() or not video_path.is_file():
            continue
        record = read_json(record_path)
        qa = read_json(qa_path)
        if qa.get("passed") is not True:
            continue
        episode_id = str(record["episode_id"])
        manifest_row = manifest_rows[episode_id]
        scenario = read_json(CAPTURE_ROOT / manifest_row["scenario_path"])
        camera = qa["camera_motion_v8"]
        collision = qa["collision_v8"]
        checks = qa["checks"]
        if collision.get("fatal_reasons"):
            raise RuntimeError(f"collision fatal admitted for {episode_id}")
        schedule = [
            {
                "i": int(block["block_index"]),
                "s": float(block["start_seconds"]),
                "e": float(block["end_seconds"]),
                "phase": str(block["visibility_phase"]),
                "actor": block.get("actor_id"),
                "appearance": block.get("appearance_id"),
                "text": interaction_text(str(block["prompt"])),
            }
            for block in scenario["prompt_schedule"]
        ]
        player_motion = qa["player_motion"]
        samples.append(
            {
                "episode": episode_id,
                "map": str(record["map"]),
                "weapon": str(record["weapon"]),
                "template": str(record["template"]),
                "kills": int(record["kill_count"]),
                "camera_profile": int(record["camera_profile"]),
                "appearances": list(record["appearance_order"]),
                "duration": float(record["video_duration_seconds"]),
                "frames": int(record["video_frames"]),
                "path_length": float(player_motion["horizontal_path_length_units"]),
                "player_duty": float(
                    player_motion["realized_player_motion_duty_fraction"]
                ),
                "camera_duty": float(camera["motion_duty_fraction"]),
                "yaw_range": float(camera["yaw_range_degrees"]),
                "pitch_range": float(camera["pitch_range_degrees"]),
                "max_yaw_step": float(camera["maximum_abs_yaw_step_degrees"]),
                "max_pitch_step": float(camera["maximum_abs_pitch_step_degrees"]),
                "render_span": float(qa["render_server_time_span_seconds"]),
                "tail_span": float(qa["render_tail_server_time_span_seconds"]),
                "collision_pass": bool(
                    checks["enemy_world_collision_absent"]
                    and checks["enemy_ground_support_missing_absent"]
                    and checks["enemy_ground_discontinuity_absent"]
                    and checks["canonical_collision_hull_declared"]
                ),
                "video": f"episodes/train/{episode_id}/video.mp4",
                "qa": f"episodes/train/{episode_id}/qa.json",
                "record": f"episodes/train/{episode_id}/record.json",
                "schedule": schedule,
            }
        )
    samples.sort(
        key=lambda row: (row["map"], row["weapon"], row["template"], row["episode"])
    )
    return samples


def card(sample: dict[str, Any], index: int) -> str:
    tags = " ".join(
        f"<span>{html.escape(str(value))}</span>"
        for value in (
            sample["map"],
            sample["weapon"],
            sample["template"],
            f"camera p{sample['camera_profile']}",
            f"{sample['kills']} kill",
        )
    )
    appearance_text = " · ".join(html.escape(x) for x in sample["appearances"])
    return f"""
    <article class="card" data-index="{index}" data-map="{html.escape(sample['map'])}"
      data-weapon="{html.escape(sample['weapon'])}" data-template="{html.escape(sample['template'])}">
      <div class="head"><div><small>{html.escape(sample['episode'])}</small>
        <h2>{html.escape(sample['map'])} <i>/</i> {html.escape(sample['weapon'])}</h2></div>
        <b class="pass">QA PASS</b></div>
      <div class="tags">{tags}</div>
      <video controls muted playsinline preload="metadata" src="{html.escape(sample['video'])}"></video>
      <div class="now"><b>当前 prompt</b><span class="now-time">00:00.0</span>
        <span class="now-actor">no active enemy</span><p class="now-text">加载时间轴…</p></div>
      <div class="timeline"></div>
      <div class="facts">
        <span>镜头 yaw <b>{sample['yaw_range']:.1f}°</b></span>
        <span>pitch <b>{sample['pitch_range']:.1f}°</b></span>
        <span>镜头 duty <b>{sample['camera_duty']:.1%}</b></span>
        <span>最大步进 <b>{sample['max_yaw_step']:.3f}° / {sample['max_pitch_step']:.3f}°</b></span>
        <span>角色 duty <b>{sample['player_duty']:.1%}</b></span>
        <span>路径 <b>{sample['path_length']:.0f}u</b></span>
        <span>碰撞 <b>{'PASS' if sample['collision_pass'] else 'FAIL'}</b></span>
        <span>server / tail <b>{sample['render_span']:.2f}s / {sample['tail_span']:.2f}s</b></span>
        <span>视频 <b>{sample['frames']}f / {sample['duration']:.2f}s</b></span>
      </div>
      <details><summary>外观与审计文件</summary><p class="appearances">{appearance_text}</p>
        <p><a href="{html.escape(sample['qa'])}">qa.json</a>
          <a href="{html.escape(sample['record'])}">record.json</a></p></details>
    </article>"""


def build(review_root: Path, manifest_root: Path) -> tuple[str, dict[str, Any]]:
    samples = load_samples(review_root, manifest_root)
    if not samples:
        raise RuntimeError("no accepted v8 review episodes found")
    maps = sorted({row["map"] for row in samples})
    weapons = sorted({row["weapon"] for row in samples})
    templates = sorted({row["template"] for row in samples})
    filters = ["<button class='active' data-filter='all' data-value='all'>全部</button>"]
    for kind, values in (("map", maps), ("weapon", weapons), ("template", templates)):
        filters.extend(
            f"<button data-filter='{kind}' data-value='{html.escape(value)}'>{html.escape(value)}</button>"
            for value in values
        )
    payload = json.dumps(samples, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    summary = {
        "schema_version": "xonotic-long60-v8-browser-review-v1",
        "samples": len(samples),
        "maps": Counter(row["map"] for row in samples),
        "weapons": Counter(row["weapon"] for row in samples),
        "templates": Counter(row["template"] for row in samples),
        "collision_pass": all(row["collision_pass"] for row in samples),
        "minimum_yaw_range_degrees": min(row["yaw_range"] for row in samples),
        "minimum_pitch_range_degrees": min(row["pitch_range"] for row in samples),
        "minimum_shotgun_tail_span_seconds": min(
            row["tail_span"] for row in samples if row["weapon"] == "Shotgun"
        ),
    }
    page = PAGE
    replacements = {
        "__FILTERS__": "".join(filters),
        "__CARDS__": "".join(card(row, i) for i, row in enumerate(samples)),
        "__DATA__": payload,
        "__SAMPLES__": str(len(samples)),
        "__MAPS__": str(len(maps)),
        "__WEAPONS__": str(len(weapons)),
        "__YAW_MIN__": f"{summary['minimum_yaw_range_degrees']:.1f}°",
    }
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    return page, summary


PAGE = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 Long60 v8 Collision + Camera Review</title><style>
:root{color-scheme:dark;--bg:#070c12;--panel:#101923;--line:#273847;--text:#edf7fb;--muted:#93aab5;--cyan:#55e5df;--green:#6fea9e}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 10% -5%,#173947,var(--bg) 38%);color:var(--text);font:14px/1.45 system-ui,sans-serif}main{width:min(1500px,calc(100% - 28px));margin:auto;padding-bottom:70px}header{padding:40px 0 20px}.eyebrow{color:var(--cyan);font:700 11px ui-monospace,monospace;letter-spacing:.15em}h1{font-size:clamp(30px,5vw,55px);letter-spacing:-.045em;margin:6px 0}.lead{max-width:1000px;color:var(--muted);font-size:16px}.fixes{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}.fix{border:1px solid var(--line);background:#0e1b23cc;border-radius:12px;padding:13px}.fix b{display:block;color:var(--green);margin-bottom:4px}.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{min-width:150px;padding:11px 14px;border:1px solid var(--line);border-radius:10px}.stat b{display:block;font-size:23px}.stat span{color:var(--muted)}.toolbar{position:sticky;top:0;z-index:5;display:flex;gap:7px;flex-wrap:wrap;padding:10px 0;background:#070c12e8;backdrop-filter:blur(10px)}button{border:1px solid var(--line);background:#12232c;color:var(--muted);padding:7px 10px;border-radius:999px;cursor:pointer}button.active{background:var(--cyan);border-color:var(--cyan);color:#071015;font-weight:800}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.card{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:15px}.head{display:flex;justify-content:space-between;gap:10px}.head small{color:var(--cyan);font:11px ui-monospace,monospace}h2{margin:3px 0 8px;font-size:22px}h2 i{color:#526d78;font-style:normal}.pass{align-self:start;background:var(--green);color:#07130c;border-radius:999px;padding:5px 9px;font-size:10px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:9px}.tags span{border:1px solid #314653;border-radius:6px;padding:3px 7px;color:#b7cbd2;font-size:11px}video{display:block;width:100%;aspect-ratio:16/9;background:#000;border-radius:9px}.now{min-height:90px;margin-top:9px;padding:9px 11px;background:#09131a;border:1px solid #21343e;border-radius:9px}.now>b{color:var(--cyan)}.now-time,.now-actor{margin-left:9px;color:var(--muted);font:11px ui-monospace,monospace}.now p{margin:6px 0 0}.timeline{display:grid;grid-template-columns:repeat(75,1fr);height:28px;gap:1px;margin:8px 0}.block{min-width:0;border:0;padding:0;border-radius:2px;background:#40505b}.block:hover,.block.current{outline:2px solid white;z-index:2}.phase-no_enemy,.phase-despawned{background:#384650}.phase-enter,.phase-reenter,.phase-appear{background:#55a8f0}.phase-in_view{background:#5cc8be}.phase-exit,.phase-offscreen,.phase-disappear_after_block{background:#8667d8}.phase-killed{background:#ff6c79}.phase-dead{background:#c48551}.facts{display:flex;gap:7px 16px;flex-wrap:wrap;color:var(--muted);font-size:12px}.facts b{color:var(--text)}details{border-top:1px solid var(--line);margin-top:10px;padding-top:9px;color:var(--muted)}a{color:var(--cyan);margin-right:12px}.appearances{font:12px ui-monospace,monospace;overflow-wrap:anywhere}.hidden{display:none!important}@media(max-width:880px){.grid{grid-template-columns:1fr}.fixes{grid-template-columns:1fr}main{width:min(100% - 18px,720px)}}
</style></head><body><main><header><div class="eyebrow">REVIEW ONLY · ISOLATED V8</div><h1>碰撞、Shotgun 回放、镜头运动</h1>
<p class="lead">12 条真实渲染覆盖 4 地图 × 3 hitscan 武器，并交错覆盖两种长程模板。只展示完整通过语义 QA 的视频；本页数据不进入训练。</p>
<div class="fixes"><div class="fix"><b>1 · 敌人碰撞</b>固定标准玩家 hull；逐 tick 做地面支撑与 BSP sweep，碰墙、悬空或台阶突变均 fail-closed。</div><div class="fix"><b>2 · Shotgun 回放</b>保留跨合并 snapshot 的 presentation accumulator；尾部 64 帧必须继续推进。</div><div class="fix"><b>3 · 镜头运动</b>开放式平滑扫描、5 个非交互短停，交互窗口回到校准瞄准；不读取敌人实时状态。</div></div>
<div class="stats"><div class="stat"><b>__SAMPLES__</b><span>QA PASS</span></div><div class="stat"><b>__MAPS__</b><span>地图</span></div><div class="stat"><b>__WEAPONS__</b><span>武器</span></div><div class="stat"><b>≥ __YAW_MIN__</b><span>每条 yaw 范围</span></div></div></header>
<div class="toolbar">__FILTERS__</div><section class="grid">__CARDS__</section></main>
<script>const samples=__DATA__;const fmt=t=>{const m=Math.floor(t/60),s=(t%60).toFixed(1).padStart(4,'0');return `${String(m).padStart(2,'0')}:${s}`};document.querySelectorAll('.card').forEach(card=>{const s=samples[+card.dataset.index],v=card.querySelector('video'),line=card.querySelector('.timeline'),txt=card.querySelector('.now-text'),tm=card.querySelector('.now-time'),actor=card.querySelector('.now-actor');s.schedule.forEach(b=>{const el=document.createElement('button');el.className=`block phase-${b.phase}`;el.title=`${b.s.toFixed(1)}–${b.e.toFixed(1)}s · ${b.phase}\n${b.text}`;el.onclick=()=>{v.currentTime=b.s+.02;v.play()};line.appendChild(el)});function update(){const t=v.currentTime,b=s.schedule[Math.min(s.schedule.length-1,Math.max(0,Math.floor(t/.8)))];tm.textContent=fmt(t);actor.textContent=b.actor?`${b.actor} · ${b.appearance}`:'no active enemy';txt.textContent=b.text;line.querySelectorAll('.current').forEach(x=>x.classList.remove('current'));line.children[b.i]?.classList.add('current')}v.addEventListener('timeupdate',update);v.addEventListener('loadedmetadata',update);update()});document.querySelectorAll('.toolbar button').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('.toolbar button').forEach(x=>x.classList.remove('active'));btn.classList.add('active');const kind=btn.dataset.filter,value=btn.dataset.value;document.querySelectorAll('.card').forEach(c=>c.classList.toggle('hidden',kind!=='all'&&c.dataset[kind]!==value))});</script></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    args = parser.parse_args()
    review_root = args.review_root.resolve()
    page, summary = build(review_root, args.manifest_root.resolve())
    (review_root / "index.html").write_text(page, encoding="utf-8")
    (review_root / "review_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
