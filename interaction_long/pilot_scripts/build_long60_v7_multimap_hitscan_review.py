                      
"""Build a self-contained browser review for accepted long60 v7 renders.

The page intentionally admits only episodes whose published ``qa.json`` passes.
It does not weaken QA to make the review matrix look complete.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


CAPTURE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_ROOT = CAPTURE_ROOT / "manifests" / (
    "stage2_long60_multi_enemy_ref42_multimap_hitscan_30h_20260828_v7"
)
DEFAULT_REVIEW_ROOT = Path(
    "./rigen_data/reviews/"
    "stage2_long60_v7_multimap_hitscan_review24_20260828"
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def interaction_text(prompt: str) -> str:
    marker = "[CURRENT OPPONENT MOTION, VISIBILITY, AND INTERACTION]"
    return prompt.split(marker, 1)[-1].strip() if marker in prompt else prompt.strip()


def load_samples(review_root: Path, manifest_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record_path in sorted((review_root / "episodes" / "train").glob("*/record.json")):
        episode_dir = record_path.parent
        qa_path = episode_dir / "qa.json"
        video_path = episode_dir / "video.mp4"
        if not qa_path.is_file() or not video_path.is_file():
            continue
        record = read_json(record_path)
        qa = read_json(qa_path)
        if not bool(qa.get("passed")):
            continue
        episode_id = str(record["episode_id"])
        scenario_path = manifest_root / "episodes" / episode_id / "scenario.json"
        if not scenario_path.is_file():
            raise FileNotFoundError(scenario_path)
        scenario = read_json(scenario_path)
        schedule = []
        for block in scenario["prompt_schedule"]:
            schedule.append(
                {
                    "i": int(block["block_index"]),
                    "s": float(block["start_seconds"]),
                    "e": float(block["end_seconds"]),
                    "phase": str(block["visibility_phase"]),
                    "actor": block.get("actor_id"),
                    "appearance": block.get("appearance_id"),
                    "ref": block.get("ref_set_id"),
                    "text": interaction_text(str(block["prompt"])),
                }
            )
        player_motion = qa["player_motion"]
        distribution = scenario["distribution"]
        rows.append(
            {
                "episode": episode_id,
                "map": str(record["map"]),
                "weapon": str(record["weapon"]),
                "template": str(record["template"]),
                "kills": int(record["kill_count"]),
                "jumps": int(distribution["enemy_jump_count"]),
                "appearances": list(record["appearance_order"]),
                "duration": float(record["video_duration_seconds"]),
                "frames": int(record["video_frames"]),
                "path_length": float(player_motion["horizontal_path_length_units"]),
                "motion_duty": float(player_motion["realized_player_motion_duty_fraction"]),
                "camera_duty": float(player_motion["realized_camera_motion_duty_fraction"]),
                "max_idle": float(player_motion["longest_realized_player_idle_seconds"]),
                "render_span": float(qa["render_server_time_span_seconds"]),
                "video": f"episodes/train/{episode_id}/video.mp4",
                "poster": f"episodes/train/{episode_id}/poster.jpg",
                "qa": f"episodes/train/{episode_id}/qa.json",
                "record": f"episodes/train/{episode_id}/record.json",
                "schedule": schedule,
            }
        )
    rows.sort(key=lambda row: (row["map"], row["template"], row["weapon"], row["episode"]))
    return rows


def card(sample: dict[str, Any], index: int) -> str:
    tags = " ".join(
        [
            f"<span>{html.escape(sample['map'])}</span>",
            f"<span>{html.escape(sample['weapon'])}</span>",
            f"<span>{html.escape(sample['template'])}</span>",
            f"<span>{sample['kills']} kill</span>",
            f"<span>{sample['jumps']} jump</span>",
        ]
    )
    appearance_text = " · ".join(html.escape(x) for x in sample["appearances"])
    return f"""
    <article class="card" data-index="{index}" data-map="{html.escape(sample['map'])}"
      data-weapon="{html.escape(sample['weapon'])}" data-template="{html.escape(sample['template'])}">
      <div class="card-head">
        <div><div class="episode">{html.escape(sample['episode'])}</div>
          <h2>{html.escape(sample['map'])} <i>/</i> {html.escape(sample['weapon'])}</h2></div>
        <b class="pass">QA PASS</b>
      </div>
      <div class="tags">{tags}</div>
      <video controls muted playsinline preload="metadata" poster="{html.escape(sample['poster'])}"
        src="{html.escape(sample['video'])}"></video>
      <div class="now"><b>当前 prompt</b><span class="now-time">00:00.0</span>
        <span class="now-actor">no active enemy</span><p class="now-text">加载时间轴…</p></div>
      <div class="timeline" aria-label="60 second prompt timeline"></div>
      <div class="facts">
        <span>角色移动 <b>{sample['motion_duty']:.1%}</b></span>
        <span>镜头移动 <b>{sample['camera_duty']:.1%}</b></span>
        <span>最长 idle <b>{sample['max_idle']:.2f}s</b></span>
        <span>位移路径 <b>{sample['path_length']:.0f}u</b></span>
        <span>server span <b>{sample['render_span']:.2f}s</b></span>
        <span>视频 <b>{sample['frames']}f / {sample['duration']:.2f}s</b></span>
      </div>
      <details><summary>本条四个敌人外观与审计文件</summary>
        <p class="appearances">{appearance_text}</p>
        <p><a href="{html.escape(sample['qa'])}">qa.json</a>
          <a href="{html.escape(sample['record'])}">record.json</a></p>
      </details>
    </article>"""


def build(review_root: Path, manifest_root: Path) -> tuple[str, dict[str, Any]]:
    samples = load_samples(review_root, manifest_root)
    if not samples:
        raise RuntimeError("no accepted episodes found")
    maps = sorted({row["map"] for row in samples})
    weapons = sorted({row["weapon"] for row in samples})
    templates = sorted({row["template"] for row in samples})
    counts = {
        "samples": len(samples),
        "maps": Counter(row["map"] for row in samples),
        "weapons": Counter(row["weapon"] for row in samples),
        "templates": Counter(row["template"] for row in samples),
        "kills": Counter(str(row["kills"]) for row in samples),
    }
    buttons = ["<button class='active' data-filter='all' data-value='all'>全部</button>"]
    for kind, values in (("map", maps), ("weapon", weapons), ("template", templates)):
        for value in values:
            buttons.append(
                f"<button data-filter='{kind}' data-value='{html.escape(value)}'>{html.escape(value)}</button>"
            )
    data = json.dumps(samples, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    cards = "".join(card(sample, index) for index, sample in enumerate(samples))
    page = PAGE.replace("__FILTERS__", "".join(buttons)).replace("__CARDS__", cards)
    page = page.replace("__SAMPLES__", str(len(samples))).replace("__MAPS__", str(len(maps)))
    page = page.replace("__WEAPONS__", str(len(weapons))).replace("__TEMPLATES__", str(len(templates)))
    page = page.replace("__DATA__", data)
    summary = {"schema_version": "xonotic-long60-v7-browser-review-v1", **counts}
    return page, summary


PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 Long60 v7 Review</title>
<style>
:root{color-scheme:dark;--bg:#071015;--panel:#0f1b23;--line:#263944;--text:#eaf7fa;--muted:#91aab3;--cyan:#56e8e0;--green:#68e89b;--amber:#ffc66e;--red:#ff7282}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 12% -10%,#17404a 0,var(--bg) 38%);color:var(--text);font:14px/1.45 Inter,system-ui,sans-serif}main{width:min(1500px,calc(100% - 28px));margin:auto;padding-bottom:80px}header{padding:44px 0 22px}.eyebrow{font:700 11px ui-monospace,monospace;letter-spacing:.14em;color:var(--cyan)}h1{margin:7px 0 4px;font-size:clamp(31px,5vw,58px);letter-spacing:-.045em}.lead{max-width:940px;color:var(--muted);font-size:16px}.warning{margin:18px 0;padding:12px 15px;border:1px solid #765d2c;background:#2c2513;border-radius:11px;color:#ffe5ae}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}.stat{padding:14px;background:#0f1b23cc;border:1px solid var(--line);border-radius:12px}.stat b{display:block;font-size:25px}.stat span{color:var(--muted)}.toolbar{position:sticky;top:0;z-index:5;display:flex;gap:7px;flex-wrap:wrap;padding:11px 0;background:#071015e8;backdrop-filter:blur(10px)}button{border:1px solid var(--line);background:#12232c;color:var(--muted);padding:7px 10px;border-radius:999px;cursor:pointer}button.active{color:#071015;background:var(--cyan);border-color:var(--cyan);font-weight:800}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.card{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:17px;padding:16px;box-shadow:0 18px 45px #0005}.card-head{display:flex;justify-content:space-between;gap:12px}.episode{color:var(--cyan);font:11px ui-monospace,monospace}h2{margin:3px 0 8px;font-size:23px}h2 i{color:#52717d;font-style:normal}.pass{align-self:start;color:#07120c;background:var(--green);padding:5px 9px;border-radius:999px;font-size:10px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.tags span{padding:3px 7px;border:1px solid #314753;border-radius:6px;color:#b7cbd2;font-size:11px}video{display:block;width:100%;aspect-ratio:16/9;background:#000;border:1px solid #31414a;border-radius:10px}.now{position:relative;min-height:93px;margin-top:10px;padding:10px 12px;background:#091319;border:1px solid #21343e;border-radius:9px}.now>b{color:var(--cyan)}.now-time,.now-actor{margin-left:9px;color:var(--muted);font:11px ui-monospace,monospace}.now p{margin:7px 0 0}.timeline{display:grid;grid-template-columns:repeat(75,1fr);height:31px;gap:1px;margin:8px 0}.block{min-width:0;border:0;padding:0;border-radius:2px;background:#40505b}.block:hover,.block.current{outline:2px solid white;z-index:2}.phase-no_enemy,.phase-despawned{background:#384650}.phase-enter,.phase-reenter{background:#55a8f0}.phase-in_view{background:#5cc8be}.phase-exit,.phase-offscreen{background:#8667d8}.phase-killed{background:#ff6c79}.phase-dead{background:#c48551}.facts{display:flex;gap:7px 16px;flex-wrap:wrap;color:var(--muted);font-size:12px}.facts b{color:var(--text)}details{border-top:1px solid var(--line);margin-top:10px;padding-top:9px;color:var(--muted)}summary{cursor:pointer}.appearances{font:12px ui-monospace,monospace;overflow-wrap:anywhere}a{color:var(--cyan);margin-right:12px}.legend{display:flex;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin:5px 0 16px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}.hidden{display:none!important}@media(max-width:880px){.grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}main{width:min(100% - 18px,720px)}header{padding-top:28px}}
</style></head><body><main>
<header><div class="eyebrow">STAGE-2 · LONG-HORIZON · REVIEW-ONLY</div><h1>60 秒多敌人交互 v7</h1>
<p class="lead">检查四张地图中的角色移动、镜头运动、多敌人分时进入、敌人外观切换、跳跃、命中/击杀、尸体静止与消失，以及 0.8 秒 causal prompt 是否与画面一致。只展示完整通过硬 QA 的实际渲染。</p>
<div class="warning"><b>已知阻塞：</b>Shotgun 的 live 采集正常，但 demo 离线渲染会在第一枪冻结 server time，因此本页暂不展示 Shotgun，也不能据此把三武器正式 manifest 判为 capture-ready；这里先 review 已验证的 MachineGun / Rifle。</div>
<div class="stats"><div class="stat"><b>__SAMPLES__</b><span>QA PASS 视频</span></div><div class="stat"><b>__MAPS__</b><span>地图</span></div><div class="stat"><b>__WEAPONS__</b><span>当前可验证武器</span></div><div class="stat"><b>__TEMPLATES__</b><span>长程模板</span></div></div></header>
<div class="toolbar">__FILTERS__</div>
<div class="legend"><span><i class="phase-no_enemy"></i>无敌人</span><span><i class="phase-enter"></i>进入</span><span><i class="phase-in_view"></i>视野内</span><span><i class="phase-exit"></i>离屏</span><span><i class="phase-killed"></i>击杀</span><span><i class="phase-dead"></i>尸体</span></div>
<section class="grid">__CARDS__</section>
</main><script>const samples=__DATA__;
const fmt=t=>{const m=Math.floor(t/60),s=(t%60).toFixed(1).padStart(4,'0');return `${String(m).padStart(2,'0')}:${s}`};
document.querySelectorAll('.card').forEach(card=>{const s=samples[+card.dataset.index],video=card.querySelector('video'),line=card.querySelector('.timeline'),text=card.querySelector('.now-text'),time=card.querySelector('.now-time'),actor=card.querySelector('.now-actor');s.schedule.forEach(b=>{const el=document.createElement('button');el.className=`block phase-${b.phase}`;el.title=`${b.s.toFixed(1)}–${b.e.toFixed(1)}s · ${b.phase}\n${b.text}`;el.addEventListener('click',()=>{video.currentTime=b.s+.02;video.play()});line.appendChild(el)});function update(){const t=video.currentTime,b=s.schedule[Math.min(s.schedule.length-1,Math.max(0,Math.floor(t/.8)))];time.textContent=fmt(t);actor.textContent=b.actor?`${b.actor} · ${b.appearance}`:'no active enemy';text.textContent=b.text;line.querySelectorAll('.current').forEach(x=>x.classList.remove('current'));line.children[b.i]?.classList.add('current')}video.addEventListener('timeupdate',update);video.addEventListener('loadedmetadata',update);update()});
let active=null;document.querySelectorAll('.toolbar button').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.toolbar button').forEach(x=>x.classList.remove('active'));btn.classList.add('active');const kind=btn.dataset.filter,value=btn.dataset.value;document.querySelectorAll('.card').forEach(c=>c.classList.toggle('hidden',kind!=='all'&&c.dataset[kind]!==value))}));
</script></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    args = parser.parse_args()
    page, summary = build(args.review_root.resolve(), args.manifest_root.resolve())
    (args.review_root / "index.html").write_text(page, encoding="utf-8")
    (args.review_root / "review_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
