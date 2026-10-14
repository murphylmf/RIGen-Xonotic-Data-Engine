                      
"""Build a dependency-free review page for the Stage-2 motion pilot."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def video_path(episode_id: str) -> str:
    return (
        f"../episodes/{episode_id}/media/review_20hz_81f.mp4"
    )


def data_link(episode_id: str, name: str) -> str:
    return f"../episodes/{episode_id}/{name}"


def render_timeline(prompt: dict[str, Any]) -> str:
    return "".join(
        f"""
        <div class="block motion-{esc(block['motion_label'])}"
             data-block="{int(block['block_index'])}">
          <span>{float(block['start_seconds']):.1f}–{float(block['end_seconds']):.1f}s</span>
          <strong>{esc(block['text'])}</strong>
        </div>
        """
        for block in prompt["blocks"]
    )


def render_card(
    root: Path,
    row: dict[str, Any],
    pair_by_active: dict[str, dict[str, Any]],
) -> str:
    active_id = str(row["sample_id"])
    frozen_id = str(row["counterfactual_episode_id"])
    episode = root / "episodes" / active_id
    qa = read_json(episode / "qa.json")
    prompt = read_json(episode / "prompt.json")
    scenario = read_json(episode / "scenario.json")
    pair = pair_by_active[active_id]
    admitted = bool(row["review_admitted"]) and bool(pair["passed"])
    failed = [
        key for key, value in qa["checks"].items() if not value
    ]
    if not pair["passed"]:
        failed.extend(
            f"pair:{key}"
            for key, value in pair["checks"].items()
            if not value
        )
    state = "PASS" if admitted else "REJECTED"
    state_class = "pass" if admitted else "reject"
    visibility = ", ".join(
        f"{key} {value}f"
        for key, value in qa["visibility_counts"].items()
    )
    speed = float(
        qa["motion"].get("moving_block_median_speed_units_per_second", 0.0)
    )
    independent = pair.get("independent_screen_space_motion") or {}
    independent_label = independent.get("realized_label", "stationary")
    partial_frames = int(qa["visibility_counts"].get("edge_tolerant_visible", 0))
    distance_tier = str(row.get("distance_tier", "legacy"))
    target_distance = row.get("target_initial_distance_units")
    actual_distance = row.get("actual_initial_distance_units")
    minimum_height_pixels = row.get("minimum_enemy_screen_height_pixels")
    distance_fact = (
        f"{distance_tier} · target {float(target_distance):.0f}u · "
        f"actual {float(actual_distance):.1f}u · min {float(minimum_height_pixels):.1f}px"
        if target_distance is not None
        and actual_distance is not None
        and minimum_height_pixels is not None
        else distance_tier
    )
    appearance = (
        f"{scenario['enemy_model']} / skin {scenario['enemy_skin']} "
        f"/ color {scenario['enemy_color']}"
    )
    failures = (
        ""
        if admitted
        else f"<p class='failure'>拒收原因：{esc(', '.join(failed))}</p>"
    )
    return f"""
    <article class="sample-card {state_class}" data-sample="{esc(active_id)}">
      <div class="sample-head">
        <div>
          <div class="eyebrow">{esc(active_id)}</div>
          <h2>{esc(scenario['map'])} · {esc(scenario['camera_program'])}</h2>
        </div>
        <span class="status {state_class}">{state}</span>
      </div>
      <div class="video-grid">
        <div>
          <div class="video-label"><b>ACTIVE</b> 敌人按 prompt 移动</div>
          <video controls muted playsinline preload="metadata"
                 src="{video_path(active_id)}"></video>
        </div>
        <div>
          <div class="video-label"><b>FROZEN</b> 同一条镜头 action</div>
          <video controls muted playsinline preload="metadata"
                 src="{video_path(frozen_id)}"></video>
        </div>
      </div>
      <div class="sync-row">
        <button class="sync-play" type="button">同步从头播放</button>
        <span>camera trace max error: <b>{float(pair['maximum_camera_trace_error']):.6f}</b></span>
        <span>独立方向复核: <b>{esc(independent_label)}</b></span>
      </div>
      <div class="timeline">{render_timeline(prompt)}</div>
      <div class="facts">
        <span>固定速度 <b>{speed:.3f} u/s</b></span>
        <span>可见性 <b>{esc(visibility)}</b></span>
        <span>部分出镜帧 <b>{partial_frames}</b></span>
        <span>距离档 <b>{esc(distance_fact)}</b></span>
        <span>武器 <b>{esc(scenario['weapon'])}</b></span>
        <span>敌人 <b>{esc(appearance)}</b></span>
        <span>交互 <b>{esc(row['desired_outcome'])} → {esc(row['actual_outcome'])}</b></span>
      </div>
      {failures}
      <details>
        <summary>prompt / QA / raw provenance</summary>
        <pre>{esc(prompt['prompt_text'])}</pre>
        <div class="links">
          <a href="{data_link(active_id, 'prompt.json')}">prompt.json</a>
          <a href="{data_link(active_id, 'qa.json')}">qa.json</a>
          <a href="{data_link(active_id, 'pair_qa.json')}">pair_qa.json</a>
          <a href="{data_link(active_id, 'scenario.json')}">scenario.json</a>
          <a href="{data_link(active_id, 'media/source_64hz.mkv')}">64 Hz source</a>
        </div>
      </details>
    </article>
    """


def build_page(root: Path) -> str:
    summary = read_json(root / "SUMMARY.json")
    rows = [
        json.loads(line)
        for line in (root / "review_manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    pair_by_active = {
        str(pair["active_episode_id"]): pair
        for pair in summary["pairs"]
    }
    cards = "".join(
        render_card(root, row, pair_by_active) for row in rows
    )
    accepted = sum(int(row["review_admitted"]) for row in rows)
    partial_total = sum(
        int(
            read_json(root / "episodes" / str(row["sample_id"]) / "qa.json")[
                "visibility_counts"
            ].get("edge_tolerant_visible", 0)
        )
        for row in rows
    )
    ratio = float(summary["speed_ratio_to_one_v_one_moving_median"])
    arena = float(
        summary["one_v_one_speed_reference"][
            "moving_speed_median_units_per_second"
        ]
    )
    speed = float(summary["fixed_speed_units_per_second"])
    visibility_policy = summary["visibility_policy"]
    page_data = json.dumps(
        {"blockSeconds": 0.8, "blockCount": 5},
        separators=(",", ":"),
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Stage-2 enemy-motion pilot v2</title>
  <style>
    :root {{ color-scheme: dark; --bg:#080b11; --panel:#111722;
      --line:#283142; --muted:#95a1b5; --text:#eef4ff;
      --cyan:#4ee3ff; --green:#53e39b; --red:#ff647c; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(circle at 15% 0,#182236 0,
      var(--bg) 42%); color:var(--text); font:14px/1.5 Inter,system-ui,sans-serif; }}
    main {{ width:min(1480px,calc(100% - 32px)); margin:0 auto 80px; }}
    header {{ padding:52px 0 28px; }}
    .eyebrow {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.12em;
      font:700 11px/1.2 ui-monospace,monospace; }}
    h1 {{ margin:8px 0 6px; font-size:clamp(30px,5vw,58px); letter-spacing:-.04em; }}
    h2 {{ margin:5px 0 0; font-size:22px; }}
    .lead {{ max-width:900px; color:var(--muted); font-size:16px; }}
    .summary {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px;
      margin:24px 0 32px; }}
    .metric {{ background:rgba(17,23,34,.88); border:1px solid var(--line);
      border-radius:14px; padding:16px; }}
    .metric span {{ display:block; color:var(--muted); }}
    .metric b {{ display:block; margin-top:3px; font-size:25px; }}
    .speed-bars {{ grid-column:span 2; }}
    .bar-row {{ display:grid; grid-template-columns:80px 1fr 70px; gap:10px;
      align-items:center; margin-top:8px; }}
    .bar {{ height:8px; background:#222b3b; border-radius:8px; overflow:hidden; }}
    .bar i {{ display:block; height:100%; background:linear-gradient(90deg,#3d75ff,var(--cyan)); }}
    .sample-card {{ margin:18px 0; padding:20px; background:rgba(17,23,34,.93);
      border:1px solid var(--line); border-radius:18px; box-shadow:0 20px 45px #0006; }}
    .sample-card.reject {{ border-color:#753342; }}
    .policy {{ margin:0 0 28px; padding:14px 16px; border:1px solid #315b6d;
      border-radius:12px; background:#10222c; color:#cbeffc; }}
    .policy b {{ color:white; }}
    .sample-head {{ display:flex; align-items:start; justify-content:space-between; gap:12px; }}
    .status {{ border-radius:999px; padding:5px 10px; font-weight:800; font-size:11px; }}
    .status.pass {{ color:#06130d; background:var(--green); }}
    .status.reject {{ color:white; background:var(--red); }}
    .video-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px; }}
    video {{ display:block; width:100%; aspect-ratio:16/9; background:#000;
      border:1px solid #303a4d; border-radius:10px; }}
    .video-label {{ color:var(--muted); margin:0 0 6px; }}
    .video-label b {{ color:var(--text); }}
    .sync-row {{ display:flex; align-items:center; gap:14px; color:var(--muted); margin:12px 0; }}
    button {{ border:0; border-radius:8px; padding:8px 12px; background:#2a76ff;
      color:white; font-weight:700; cursor:pointer; }}
    .timeline {{ display:grid; grid-template-columns:repeat(5,1fr); gap:6px; }}
    .block {{ min-height:74px; padding:9px; border:1px solid var(--line);
      border-top:3px solid #567; border-radius:8px; background:#0c111a; }}
    .block span {{ display:block; color:var(--muted); font:11px ui-monospace,monospace; }}
    .block strong {{ display:block; margin-top:4px; font-size:12px; }}
    .block.active {{ outline:2px solid var(--cyan); outline-offset:1px; }}
    .motion-player_left {{ border-top-color:#8b7dff; }}
    .motion-player_right {{ border-top-color:#4ee3ff; }}
    .motion-toward_player {{ border-top-color:#53e39b; }}
    .motion-away_from_player {{ border-top-color:#ffba5c; }}
    .motion-player_left_toward,.motion-player_right_toward {{ border-top-color:#72eea8; }}
    .motion-player_left_away,.motion-player_right_away {{ border-top-color:#ff9f69; }}
    .motion-stationary {{ border-top-color:#8893a7; }}
    .facts {{ display:flex; flex-wrap:wrap; gap:8px 18px; margin:14px 0;
      color:var(--muted); }}
    .facts b {{ color:var(--text); }}
    .failure {{ padding:9px; background:#401a22; color:#ffbcc7; border-radius:8px; }}
    details {{ border-top:1px solid var(--line); padding-top:12px; }}
    summary {{ cursor:pointer; color:var(--muted); }}
    pre {{ white-space:pre-wrap; padding:12px; background:#080c13; border-radius:8px; }}
    .links {{ display:flex; flex-wrap:wrap; gap:12px; }}
    a {{ color:var(--cyan); }}
    footer {{ color:var(--muted); padding:24px 0; }}
    @media (max-width:850px) {{ .summary,.video-grid {{ grid-template-columns:1fr; }}
      .speed-bars {{ grid-column:span 1; }} .timeline {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body><main>
  <header>
    <div class="eyebrow">XONOTIC · STAGE-2 · NEAR-5 + COMBO PILOT</div>
    <h1>Enemy motion prompt v3</h1>
    <p class="lead">固定慢速、5 × 0.8s、5 档近距离与 9 类相对运动，包含左/右和靠近/远离的组合；保留原 Stage-2 的开火、命中和击杀交互。距离档仅用于采样与 QA，不写进 prompt。</p>
  </header>
  <section class="summary">
    <div class="metric"><span>review admitted</span><b>{accepted} / {len(rows)}</b></div>
    <div class="metric"><span>fixed enemy speed</span><b>{speed:.0f} u/s</b></div>
    <div class="metric speed-bars">
      <span>vs. 1v1 arena moving median</span>
      <div class="bar-row"><label>pilot</label><div class="bar"><i style="width:{ratio*100:.1f}%"></i></div><b>{speed:.0f}</b></div>
      <div class="bar-row"><label>arena</label><div class="bar"><i style="width:100%"></i></div><b>{arena:.0f}</b></div>
    </div>
  </section>
  <div class="policy">
    <b>视野策略：</b>允许敌人部分走出画面；至少一个身体采样点仍在
    {float(visibility_policy['frustum_tolerance_scale']):.2f}× 容错视锥内即可接收。
    完全走出容错视锥或被场景遮挡仍拒收。本批累计部分出镜帧为
    <b>{partial_total}</b>；这不影响接收，只要没有完整走出容错视锥。
  </div>
  <section>{cards}</section>
  <footer>Raw demo / AVI / 64 Hz telemetry 均保留；本页样例仍标记 training_admitted=false，等待人工 review。</footer>
</main>
<script>
const cfg={page_data};
document.querySelectorAll('.sample-card').forEach(card=>{{
  const videos=[...card.querySelectorAll('video')];
  const blocks=[...card.querySelectorAll('.block')];
  card.querySelector('.sync-play').addEventListener('click',()=>{{
    videos.forEach(v=>{{v.pause();v.currentTime=0;}});
    Promise.all(videos.map(v=>v.play().catch(()=>null)));
  }});
  const update=()=>{{
    const t=videos[0].currentTime;
    const index=Math.min(cfg.blockCount-1,Math.floor(t/cfg.blockSeconds));
    blocks.forEach((b,i)=>b.classList.toggle('active',i===index));
    requestAnimationFrame(update);
  }};
  update();
}});
</script></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()
    review = root / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "index.html").write_text(
        build_page(root), encoding="utf-8"
    )
    print(review / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
