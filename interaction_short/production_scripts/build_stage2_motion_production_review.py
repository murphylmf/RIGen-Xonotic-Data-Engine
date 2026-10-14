                      
"""Build a read-only, stratified review snapshot from live Stage-2 production.

The production journals are snapshotted at process start.  The output contains
only small JSON manifests, HTML, and symlinks back to selected immutable episode
artifacts; the production tree is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MOTIONS = [
    "stationary",
    "player_left",
    "player_right",
    "toward_player",
    "away_from_player",
    "player_left_toward",
    "player_right_toward",
    "player_left_away",
    "player_right_away",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_journal_lines(path: Path) -> list[bytes]:
    """Read only newline-terminated rows, ignoring a concurrent partial append."""
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        data = data.rsplit(b"\n", 1)[0] + b"\n" if b"\n" in data else b""
    return [line for line in data.splitlines() if line.strip()]


def load_journals(run_root: Path, name: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    sizes: dict[str, int] = {}
    for path in sorted(run_root.glob(f"shard_*/manifests/{name}.jsonl")):
        lines = atomic_journal_lines(path)
        sizes[str(path.relative_to(run_root))] = len(lines)
        for line in lines:
            rows.append(json.loads(line))
    return rows, sizes


def distribution(rows: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(row.get(key, "<missing>")) for row in rows)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def balanced_targets(values: list[str], total: int) -> dict[str, int]:
    base, remainder = divmod(total, len(values))
    return {value: base + int(index < remainder) for index, value in enumerate(values)}


def stable_tie(pair_id: str) -> int:
    return int(hashlib.sha256(pair_id.encode("utf-8")).hexdigest()[:16], 16)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = fraction * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    alpha = position - low
    return ordered[low] * (1.0 - alpha) + ordered[high] * alpha


def select_rows(records: list[dict[str, Any]], count: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if count % len(MOTIONS):
        raise ValueError(f"--count must be divisible by {len(MOTIONS)}")
    by_motion: dict[str, list[dict[str, Any]]] = defaultdict(list)
    heights = [float(row["minimum_enemy_screen_height_pixels"]) for row in records]
    low_height = percentile(heights, 0.05)
    high_height = percentile(heights, 0.95)
    for row in records:
        height = float(row["minimum_enemy_screen_height_pixels"])
        row["_screen_size_band"] = (
            "low_edge" if height <= low_height else "high_edge" if height >= high_height else "middle"
        )
        row["_intent_actual_mismatch"] = str(row["intent_outcome"] != row["actual_outcome"]).lower()
        by_motion[str(row["enemy_motion"])].append(row)

    for motion in MOTIONS:
        if len(by_motion[motion]) < count // len(MOTIONS):
            raise RuntimeError(f"not enough accepted rows for motion={motion}")

    features = {
        "distance_tier": sorted({str(row["distance_tier"]) for row in records}),
        "map": sorted({str(row["map"]) for row in records}),
        "enemy_model": sorted({str(row["enemy_model"]) for row in records}),
        "weapon": sorted({str(row["weapon"]) for row in records}),
        "actual_outcome": sorted({str(row["actual_outcome"]) for row in records}),
        "player_motion_class": sorted({str(row["player_motion_class"]) for row in records}),
    }
    targets = {key: balanced_targets(values, count) for key, values in features.items()}
    targets["_intent_actual_mismatch"] = {"true": min(8, count // 4), "false": count - min(8, count // 4)}
    targets["_screen_size_band"] = {"low_edge": 3, "high_edge": 3, "middle": count - 6}
    weights = {
        "distance_tier": 7.0,
        "map": 5.0,
        "enemy_model": 4.0,
        "weapon": 4.0,
        "actual_outcome": 8.0,
        "player_motion_class": 7.0,
        "_intent_actual_mismatch": 4.0,
        "_screen_size_band": 2.0,
    }
    selected: list[dict[str, Any]] = []
    chosen_ids: set[str] = set()
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    rounds = count // len(MOTIONS)
    for _round in range(rounds):
        for motion in MOTIONS:
            candidates = [row for row in by_motion[motion] if str(row["pair_id"]) not in chosen_ids]

            def score(row: dict[str, Any]) -> tuple[float, int]:
                value = 0.0
                for key, feature_targets in targets.items():
                    item = str(row[key])
                    target = feature_targets.get(item, 0)
                    deficit = max(0, target - counts[key][item])
                    value += weights[key] * (deficit / target if target else 0.0)
                return value, stable_tie(str(row["pair_id"]))

            winner = max(candidates, key=score)
            selected.append(winner)
            chosen_ids.add(str(winner["pair_id"]))
            for key in targets:
                counts[key][str(winner[key])] += 1

    diagnostics = {
        "height_percentile_05_pixels": low_height,
        "height_percentile_95_pixels": high_height,
        "selection_targets": targets,
    }
    return selected, diagnostics


def ffprobe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,nb_read_frames,sample_rate,channels:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    video = next(stream for stream in payload["streams"] if stream["codec_type"] == "video")
    audio = next((stream for stream in payload["streams"] if stream["codec_type"] == "audio"), {})
    return {
        "video_codec": video.get("codec_name"),
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "frame_rate": video.get("r_frame_rate"),
        "frames": next(
            (
                int(value)
                for value in (video.get("nb_frames"), video.get("nb_read_frames"))
                if str(value).isdigit()
            ),
            None,
        ),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": int(audio.get("sample_rate", 0)) if str(audio.get("sample_rate", "")).isdigit() else None,
        "audio_channels": int(audio.get("channels", 0)) if audio.get("channels") is not None else None,
        "duration_seconds": float(payload.get("format", {}).get("duration", 0.0)),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_selected(row: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    record_path = Path(journal["record_path"])
    active_episode = Path(row["prompt_path"]).parent
    frozen_episode = active_episode.parent / str(row["counterfactual_episode_id"])
    active_qa = read_json(active_episode / "qa.json")
    frozen_qa = read_json(frozen_episode / "qa.json")
    prompt = read_json(Path(row["prompt_path"]))
    pair_qa = read_json(Path(row["pair_qa_path"]))

    required_active = [
        Path(row["video_path"]),
        Path(row["source_video_path"]),
        Path(row["action_path"]),
        Path(row["state_path"]),
        Path(row["visibility_path"]),
        Path(row["prompt_path"]),
        Path(row["pair_qa_path"]),
        active_episode / "qa.json",
        active_episode / "scenario.json",
        active_episode / "raw/source.dem",
        active_episode / "telemetry/events_64hz.parquet",
    ]
    required_frozen = [
        frozen_episode / "media/review_20hz_81f.mp4",
        frozen_episode / "media/source_64hz.mkv",
        frozen_episode / "prompt.json",
        frozen_episode / "qa.json",
        frozen_episode / "scenario.json",
        frozen_episode / "raw/source.dem",
        frozen_episode / "telemetry/actions_requested_64hz.parquet",
        frozen_episode / "telemetry/states_64hz.parquet",
        frozen_episode / "telemetry/visibility_64hz.parquet",
    ]
    missing = [str(path) for path in required_active + required_frozen if not path.is_file()]
    if missing:
        errors.extend(f"missing:{path}" for path in missing)
    if sha256(record_path) != journal["record_sha256"]:
        errors.append("record_sha256_mismatch")
    if not row.get("capture_qa_passed"):
        errors.append("record_capture_qa_not_passed")
    if not all(bool(value) for value in row.get("pair_checks", {}).values()):
        errors.append("record_pair_check_failed")
    if not all(bool(value) for value in active_qa.get("checks", {}).values()):
        errors.append("active_qa_check_failed")
    if not all(bool(value) for value in frozen_qa.get("checks", {}).values()):
        errors.append("frozen_qa_check_failed")
    if not pair_qa.get("passed") or not all(bool(value) for value in pair_qa.get("checks", {}).values()):
        errors.append("pair_qa_failed")
    blocks = prompt.get("blocks", [])
    if len(blocks) != 5:
        errors.append("prompt_block_count_not_5")
    for index, block in enumerate(blocks):
        if int(block.get("block_index", -1)) != index:
            errors.append(f"prompt_block_index_{index}_bad")
        if abs(float(block.get("start_seconds", -1)) - 0.8 * index) > 1e-6:
            errors.append(f"prompt_block_{index}_start_bad")
        if abs(float(block.get("end_seconds", -1)) - 0.8 * (index + 1)) > 1e-6:
            errors.append(f"prompt_block_{index}_end_bad")
    if prompt.get("camera_action_described_in_text") is not False:
        errors.append("camera_action_in_prompt")
    for field in ("uses_absolute_screen_region", "uses_distance_magnitude_adjective", "uses_percentage"):
        if prompt.get(field) is not False:
            errors.append(field)
    fixed_speed = float(active_qa.get("motion", {}).get("fixed_speed_target_units_per_second", -1))
    expected_speed = 0.0 if row["enemy_motion"] == "stationary" else 96.0
    if abs(fixed_speed - expected_speed) > 1e-6:
        errors.append(f"fixed_speed_not_{expected_speed:g}")
    if not active_qa.get("checks", {}).get("no_occlusion"):
        errors.append("occlusion_present")
    if not active_qa.get("checks", {}).get("no_true_offscreen_after_tolerance"):
        errors.append("true_offscreen_present")
    if str(prompt.get("actual_outcome")) != str(row["actual_outcome"]):
        errors.append("prompt_record_outcome_mismatch")

    probes: dict[str, dict[str, Any]] = {}
    media_paths = {
        "active_review": Path(row["video_path"]),
        "frozen_review": frozen_episode / "media/review_20hz_81f.mp4",
        "active_source": Path(row["source_video_path"]),
        "frozen_source": frozen_episode / "media/source_64hz.mkv",
    }
    if not missing:
        for role, path in media_paths.items():
            probes[role] = ffprobe(path)
        for role in ("active_review", "frozen_review"):
            probe = probes[role]
            if not (
                probe["video_codec"] == "h264"
                and probe["width"] == 1280
                and probe["height"] == 720
                and probe["frame_rate"] == "20/1"
                and probe["frames"] == 81
                and abs(probe["duration_seconds"] - 4.05) < 0.02
            ):
                errors.append(f"{role}_contract_failed")
        for role in ("active_source", "frozen_source"):
            probe = probes[role]
            if not (
                probe["video_codec"] == "h264"
                and probe["width"] == 1280
                and probe["height"] == 720
                and probe["frame_rate"] == "64/1"
                and probe["frames"] == 320
                and abs(probe["duration_seconds"] - 5.0) < 0.02
            ):
                errors.append(f"{role}_contract_failed")

    return {
        "pair_id": row["pair_id"],
        "sample_id": row["sample_id"],
        "passed": not errors,
        "errors": errors,
        "active_qa_checks": active_qa["checks"],
        "frozen_qa_checks": frozen_qa["checks"],
        "pair_checks": pair_qa["checks"],
        "maximum_camera_trace_error": pair_qa["maximum_camera_trace_error"],
        "maximum_requested_action_trace_error": pair_qa["maximum_requested_action_trace_error"],
        "independent_realized_label": pair_qa["independent_screen_space_motion"]["realized_label"],
        "visibility_counts": active_qa["visibility_counts"],
        "interaction": active_qa["interaction"],
        "media_probes": probes,
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_distribution(title: str, values: dict[str, int]) -> str:
    chips = "".join(f"<span>{esc(key)} <b>{value}</b></span>" for key, value in values.items())
    return f"<div class='dist'><strong>{esc(title)}</strong><div>{chips}</div></div>"


def render_timeline(prompt: dict[str, Any]) -> str:
    return "".join(
        f"<div class='block motion-{esc(block['motion_label'])}' data-block='{int(block['block_index'])}'>"
        f"<small>{float(block['start_seconds']):.1f}-{float(block['end_seconds']):.1f}s</small>"
        f"<b>{esc(block['motion_label'])}</b><span>{esc(block['text'])}</span></div>"
        for block in prompt["blocks"]
    )


def render_card(row: dict[str, Any], validation: dict[str, Any]) -> str:
    active_id = str(row["sample_id"])
    frozen_id = str(row["counterfactual_episode_id"])
    prompt = read_json(Path(row["prompt_path"]))
    active_qa = read_json(Path(row["prompt_path"]).parent / "qa.json")
    pair_qa = read_json(Path(row["pair_qa_path"]))
    interaction = active_qa["interaction"]
    visibility = ", ".join(f"{key}: {value}f" for key, value in active_qa["visibility_counts"].items())
    mismatch = row["intent_outcome"] != row["actual_outcome"]
    mismatch_badge = "<span class='badge warn'>intent re-bucket</span>" if mismatch else ""
    status = "PASS" if validation["passed"] else "FAIL"
    status_class = "pass" if validation["passed"] else "fail"
    errors = "" if validation["passed"] else f"<p class='errors'>{esc(', '.join(validation['errors']))}</p>"
    return f"""
    <article class="card {status_class}" data-motion="{esc(row['enemy_motion'])}"
      data-distance="{esc(row['distance_tier'])}" data-map="{esc(row['map'])}"
      data-model="{esc(row['enemy_model'])}" data-weapon="{esc(row['weapon'])}"
      data-outcome="{esc(row['actual_outcome'])}" data-player="{esc(row['player_motion_class'])}">
      <div class="head"><div><div class="eyebrow">{esc(row['pair_id'])}</div>
      <h2>{esc(row['map'])} · {esc(row['enemy_motion'])} · {esc(row['distance_tier'])}</h2></div>
      <div><span class="badge {status_class}">{status}</span>{mismatch_badge}</div></div>
      <div class="videos">
        <div><label>ACTIVE · prompt-driven enemy</label><video controls muted playsinline preload="metadata"
          src="episodes/{esc(active_id)}/media/review_20hz_81f.mp4"></video></div>
        <div><label>FROZEN · same player/camera trace</label><video controls muted playsinline preload="metadata"
          src="episodes/{esc(frozen_id)}/media/review_20hz_81f.mp4"></video></div>
      </div>
      <div class="sync"><button type="button" class="sync-play">同步从头播放</button>
        <span>camera max error <b>{float(pair_qa['maximum_camera_trace_error']):.6f}</b></span>
        <span>independent label <b>{esc(pair_qa['independent_screen_space_motion']['realized_label'])}</b></span></div>
      <div class="timeline">{render_timeline(prompt)}</div>
      <div class="facts">
        <span>enemy <b>{esc(row['enemy_model'])}</b> / color {esc(row['enemy_color'])}</span>
        <span>weapon <b>{esc(row['weapon'])}</b></span>
        <span>screen min <b>{float(row['minimum_enemy_screen_height_pixels']):.1f}px</b></span>
        <span>distance target/actual <b>{float(row['target_initial_distance_units']):.0f}/{float(row['actual_initial_distance_units']):.1f}u</b></span>
        <span>intent → actual <b>{esc(row['intent_outcome'])} → {esc(row['actual_outcome'])}</b></span>
        <span>fire/damage/kill <b>{interaction['fire_count']}/{interaction['damage_count']}/{interaction['kill_count']}</b></span>
        <span>visibility <b>{esc(visibility)}</b></span>
        <span>player trace <b>{esc(row['player_motion_class'])}</b></span>
      </div>{errors}
      <details><summary>Prompt / QA / provenance</summary><pre>{esc(prompt['prompt_text'])}</pre>
        <div class="links">
          <a href="records/{esc(row['pair_id'])}.json">record.json</a>
          <a href="episodes/{esc(active_id)}/prompt.json">prompt.json</a>
          <a href="episodes/{esc(active_id)}/qa.json">active qa</a>
          <a href="episodes/{esc(active_id)}/pair_qa.json">pair qa</a>
          <a href="episodes/{esc(active_id)}/scenario.json">scenario</a>
          <a href="episodes/{esc(active_id)}/media/source_64hz.mkv">active 64 Hz</a>
          <a href="episodes/{esc(active_id)}/telemetry/actions_requested_64hz.parquet">actions</a>
          <a href="episodes/{esc(active_id)}/telemetry/states_64hz.parquet">states</a>
          <a href="episodes/{esc(active_id)}/telemetry/visibility_64hz.parquet">visibility</a>
          <a href="episodes/{esc(frozen_id)}/media/source_64hz.mkv">frozen 64 Hz</a>
        </div></details>
    </article>"""


def build_page(audit: dict[str, Any], rows: list[dict[str, Any]], validations: list[dict[str, Any]]) -> str:
    validation_by_pair = {str(item["pair_id"]): item for item in validations}
    cards = "".join(render_card(row, validation_by_pair[str(row["pair_id"])]) for row in rows)
    selected_dist = audit["selected_distributions"]
    distributions = "".join(
        render_distribution(label, selected_dist[key])
        for key, label in (
            ("enemy_motion", "motion"),
            ("distance_tier", "distance"),
            ("map", "map"),
            ("enemy_model", "enemy model"),
            ("weapon", "weapon"),
            ("actual_outcome", "actual outcome"),
            ("player_motion_class", "player trace"),
        )
    )
    filter_values = {
        "motion": list(selected_dist["enemy_motion"]),
        "distance": list(selected_dist["distance_tier"]),
        "map": list(selected_dist["map"]),
        "model": list(selected_dist["enemy_model"]),
        "weapon": list(selected_dist["weapon"]),
        "outcome": list(selected_dist["actual_outcome"]),
        "player": list(selected_dist["player_motion_class"]),
    }
    filter_html = "".join(
        f"<label>{esc(key)}<select data-filter='{esc(key)}'><option value=''>all</option>"
        + "".join(f"<option value='{esc(value)}'>{esc(value)}</option>" for value in values)
        + "</select></label>"
        for key, values in filter_values.items()
    )
    rejected_top = audit["rejected_snapshot"]["failed_checks"]
    rejected_text = ", ".join(f"{key} {value}" for key, value in list(rejected_top.items())[:8])
    captured = esc(audit["snapshot"]["captured_utc"])
    manifest_max = esc(audit["snapshot"]["maximum_accepted_utc"])
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-2 production stratified review</title><style>
:root{{color-scheme:dark;--bg:#070a10;--panel:#111722;--line:#293346;--muted:#94a1b6;--text:#eef4ff;--cyan:#4ee3ff;--green:#55e69c;--red:#ff647c;--amber:#ffbf69}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 12% 0,#18243b 0,var(--bg) 43%);color:var(--text);font:14px/1.5 Inter,system-ui,sans-serif}}
main{{width:min(1500px,calc(100% - 32px));margin:auto;padding:42px 0 80px}} .eyebrow{{color:var(--cyan);text-transform:uppercase;letter-spacing:.11em;font:700 11px ui-monospace,monospace}}
h1{{font-size:clamp(32px,5vw,58px);letter-spacing:-.04em;margin:8px 0}} h2{{font-size:21px;margin:5px 0}} .lead{{max-width:1000px;color:var(--muted);font-size:16px}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}} .metric,.dist,.filters{{background:#111722e8;border:1px solid var(--line);border-radius:13px;padding:14px}}
.metric span,.dist>strong{{display:block;color:var(--muted)}} .metric b{{font-size:25px}} .dist-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:18px 0}}
.dist div{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}} .dist span{{background:#0a0f17;border:1px solid #253044;border-radius:999px;padding:3px 8px}}
.notice{{border:1px solid #806324;background:#2a210f;color:#ffe1a3;border-radius:12px;padding:12px 15px;margin:18px 0}} .filters{{position:sticky;top:0;z-index:4;display:flex;flex-wrap:wrap;gap:10px 16px;margin:18px 0;box-shadow:0 8px 30px #000a}}
.filters label{{color:var(--muted)}} select{{display:block;margin-top:3px;max-width:220px;background:#080d15;color:var(--text);border:1px solid #344057;border-radius:7px;padding:6px}}
.card{{background:#111722ed;border:1px solid var(--line);border-radius:18px;padding:20px;margin:18px 0;box-shadow:0 20px 48px #0006}} .card.fail{{border-color:#7c3443}} .head{{display:flex;justify-content:space-between;gap:12px;align-items:start}}
.badge{{display:inline-block;border-radius:999px;padding:5px 9px;margin-left:5px;font-weight:800;font-size:11px}} .badge.pass{{background:var(--green);color:#06120c}} .badge.fail{{background:var(--red)}} .badge.warn{{background:var(--amber);color:#221500}}
.videos{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:15px}} .videos label{{display:block;color:var(--muted);margin-bottom:5px}} video{{width:100%;aspect-ratio:16/9;background:#000;border:1px solid #303b50;border-radius:10px}}
.sync{{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;color:var(--muted);margin:11px 0}} button{{background:#2877ff;color:#fff;border:0;border-radius:8px;padding:8px 12px;font-weight:750;cursor:pointer}}
.timeline{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}} .block{{min-height:106px;background:#090e16;border:1px solid #2a3448;border-top:3px solid #637087;border-radius:8px;padding:8px}}
.block small,.block b,.block span{{display:block}} .block small{{color:var(--muted)}} .block b{{margin:3px 0;color:var(--cyan)}} .block span{{font-size:12px}} .block.active{{outline:2px solid var(--cyan);outline-offset:1px}}
.motion-player_left{{border-top-color:#8c7dff}} .motion-player_right{{border-top-color:#4ee3ff}} .motion-toward_player{{border-top-color:#53e39b}} .motion-away_from_player{{border-top-color:#ffba5c}} .motion-player_left_toward,.motion-player_right_toward{{border-top-color:#72eea8}} .motion-player_left_away,.motion-player_right_away{{border-top-color:#ff9069}}
.facts{{display:flex;flex-wrap:wrap;gap:7px 18px;color:var(--muted);margin:13px 0}} .facts b{{color:var(--text)}} details{{border-top:1px solid var(--line);padding-top:11px}} summary{{cursor:pointer;color:var(--muted)}} pre{{white-space:pre-wrap;background:#080c13;border-radius:8px;padding:12px}} .links{{display:flex;flex-wrap:wrap;gap:12px}} a{{color:var(--cyan)}} .errors{{background:#421921;color:#ffbbc6;padding:8px;border-radius:7px}}
@media(max-width:900px){{.metrics,.dist-grid,.videos{{grid-template-columns:1fr}}.timeline{{overflow-x:auto;grid-template-columns:repeat(5,230px)}}}}
</style></head><body><main>
<header><div class="eyebrow">production snapshot · accepted only</div><h1>Stage-2 enemy motion 抽检</h1>
<p class="lead">36 条分层样本，每个 primary motion 4 条；ACTIVE 与 FROZEN 使用完全相同的 player/camera requested-action trace。快照建立于 {captured}，accepted journal 最新条目 {manifest_max}。</p></header>
<section class="metrics"><div class="metric"><span>accepted snapshot</span><b>{audit['accepted_snapshot']['records_loaded']:,}</b></div>
<div class="metric"><span>selected</span><b>{len(rows)}</b></div><div class="metric"><span>validation</span><b>{audit['selected_validation']['passed']}/{len(rows)}</b></div>
<div class="metric"><span>rejected snapshot</span><b>{audit['rejected_snapshot']['rows']:,}</b></div></section>
<div class="notice"><b>注意：</b>这些 accepted capture 当前仍全部是 <code>training_admitted=false</code>；这是 production schema 的人工放行门，不等于 capture QA 失败。本页不会改这个字段。拒收边界 top checks：{esc(rejected_text)}。</div>
<section class="dist-grid">{distributions}</section>
<section class="filters"><b>筛选（当前显示 <span id="visible-count">{len(rows)}</span> 条）</b>{filter_html}<button id="reset" type="button">reset</button><a href="audit.json">audit.json</a><a href="selected_manifest.jsonl">selected manifest</a></section>
<section id="cards">{cards}</section>
</main><script>
const cards=[...document.querySelectorAll('.card')]; const selects=[...document.querySelectorAll('select[data-filter]')];
function applyFilters(){{let visible=0;for(const card of cards){{const ok=selects.every(s=>!s.value||card.dataset[s.dataset.filter]===s.value);card.hidden=!ok;if(ok)visible++}}document.querySelector('#visible-count').textContent=visible}}
selects.forEach(s=>s.addEventListener('change',applyFilters));document.querySelector('#reset').addEventListener('click',()=>{{selects.forEach(s=>s.value='');applyFilters()}});
document.querySelectorAll('.sync-play').forEach(button=>button.addEventListener('click',()=>{{const card=button.closest('.card');const videos=[...card.querySelectorAll('video')];videos.forEach(v=>{{v.pause();v.currentTime=0}});Promise.all(videos.map(v=>v.play())).catch(()=>{{}})}}));
document.querySelectorAll('video').forEach(video=>video.addEventListener('timeupdate',()=>{{const card=video.closest('.card');const index=Math.min(4,Math.floor(video.currentTime/.8));card.querySelectorAll('.block').forEach((b,i)=>b.classList.toggle('active',i===index))}}));
</script></body></html>"""


def symlink(path: Path, target: Path) -> None:
    path.symlink_to(target, target_is_directory=target.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--count", type=int, default=36)
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_root}")

    accepted_rows, accepted_sizes = load_journals(run_root, "accepted")
    rejected_rows, rejected_sizes = load_journals(run_root, "rejected")
    accepted_by_pair: dict[str, dict[str, Any]] = {}
    duplicate_accepted = 0
    for journal in accepted_rows:
        pair_id = str(journal["pair_id"])
        if pair_id in accepted_by_pair:
            duplicate_accepted += 1
        accepted_by_pair[pair_id] = journal

    records: list[dict[str, Any]] = []
    record_errors: list[str] = []
    for pair_id, journal in accepted_by_pair.items():
        try:
            record = read_json(Path(journal["record_path"]))
            if str(record["pair_id"]) != pair_id:
                record_errors.append(f"{pair_id}:record_pair_id_mismatch")
                continue
            records.append(record)
        except Exception as exc:                                                        
            record_errors.append(f"{pair_id}:{type(exc).__name__}:{exc}")
    if record_errors:
        raise RuntimeError(f"accepted record load errors: {record_errors[:10]}")

    selected, selection_diagnostics = select_rows(records, args.count)
    validations = [validate_selected(row, accepted_by_pair[str(row["pair_id"])]) for row in selected]

    population_keys = [
        "enemy_motion", "distance_tier", "map", "enemy_model", "weapon",
        "actual_outcome", "intent_outcome", "player_motion_class", "training_admitted",
    ]
    selected_keys = [
        "enemy_motion", "distance_tier", "map", "enemy_model", "weapon",
        "actual_outcome", "intent_outcome", "player_motion_class", "_screen_size_band",
        "_intent_actual_mismatch", "training_admitted",
    ]
    rejected_reason = distribution(rejected_rows, "reason")
    failed_checks = Counter(
        str(check)
        for row in rejected_rows
        for check in row.get("failed_checks", [])
    )
    snapshot_times = [str(row.get("accepted_utc", "")) for row in accepted_rows if row.get("accepted_utc")]
    audit = {
        "schema_version": "xonotic-stage2-production-stratified-review-v1",
        "snapshot": {
            "captured_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "run_root": str(run_root),
            "maximum_accepted_utc": max(snapshot_times) if snapshot_times else None,
            "journal_reads_ignore_partial_trailing_line": True,
        },
        "accepted_snapshot": {
            "journal_rows": len(accepted_rows),
            "unique_pairs": len(accepted_by_pair),
            "duplicate_rows": duplicate_accepted,
            "records_loaded": len(records),
            "record_load_errors": record_errors,
            "per_shard_rows": accepted_sizes,
            "distributions": {key: distribution(records, key) for key in population_keys},
        },
        "rejected_snapshot": {
            "rows": len(rejected_rows),
            "per_shard_rows": rejected_sizes,
            "reasons": rejected_reason,
            "failed_checks": dict(sorted(failed_checks.items(), key=lambda item: (-item[1], item[0]))),
        },
        "selection": selection_diagnostics,
        "selected_distributions": {key: distribution(selected, key) for key in selected_keys},
        "selected_validation": {
            "passed": sum(int(item["passed"]) for item in validations),
            "failed": sum(int(not item["passed"]) for item in validations),
            "items": validations,
        },
        "training_release": {
            "all_selected_training_admitted_false": all(row.get("training_admitted") is False for row in selected),
            "review_page_mutates_training_admission": False,
        },
    }

    output_root.mkdir(parents=True)
    (output_root / "episodes").mkdir()
    (output_root / "records").mkdir()
    for row in selected:
        active_episode = Path(row["prompt_path"]).parent
        frozen_episode = active_episode.parent / str(row["counterfactual_episode_id"])
        symlink(output_root / "episodes" / str(row["sample_id"]), active_episode)
        symlink(output_root / "episodes" / str(row["counterfactual_episode_id"]), frozen_episode)
        symlink(output_root / "records" / f"{row['pair_id']}.json", Path(accepted_by_pair[str(row["pair_id"])]["record_path"]))

    clean_rows = [{key: value for key, value in row.items() if not key.startswith("_")} for row in selected]
    (output_root / "selected_manifest.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in clean_rows), encoding="utf-8"
    )
    (output_root / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / "index.html").write_text(build_page(audit, selected, validations), encoding="utf-8")
    print(json.dumps({
        "output_root": str(output_root),
        "accepted_snapshot": len(records),
        "rejected_snapshot": len(rejected_rows),
        "selected": len(selected),
        "validation_passed": audit["selected_validation"]["passed"],
        "selected_distributions": audit["selected_distributions"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
