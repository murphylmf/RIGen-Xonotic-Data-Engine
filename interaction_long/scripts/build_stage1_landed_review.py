                      
"""Build a fixed-seed uniform review of already accepted Stage-1 data."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import html
import json
import os
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("./xonotic_capture")
DEFAULT_MANIFEST_ROOT = (
    ROOT / "manifests/stage1_foundation_v5_formal_56x1_runtime_r2"
)
DEFAULT_OUTPUT_ROOT = ROOT / "stage1_foundation_v5_output_56x1"
DEFAULT_REVIEW_ROOT = ROOT / "stage1_landed_review_100_20260729"
DEFAULT_SEED = "stage1-landed-accepted-uniform-review-20260729-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def stream_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"expected object: {path}:{line_number}")
            yield value


def load_accepted(
    output_root: Path, shard_count: int
) -> dict[str, dict[str, Any]]:
    accepted: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for shard_index in range(shard_count):
        tag = f"shard-{shard_index:03d}-of-{shard_count:03d}"
        path = (
            output_root
            / "manifests/shards/primary"
            / tag
            / "accepted_candidates.jsonl"
        )
        if not path.is_file():
            continue
        for row in stream_jsonl(path):
            episode_id = str(row["episode_id"])
            if episode_id in accepted:
                duplicate_ids.append(episode_id)
            accepted[episode_id] = row
    if duplicate_ids:
        raise RuntimeError(
            "duplicate accepted episode IDs: "
            + ", ".join(sorted(set(duplicate_ids))[:20])
        )
    return accepted


def selection_key(seed: str, episode_id: str) -> str:
    return hashlib.sha256(
        f"{seed}\0{episode_id}".encode("utf-8")
    ).hexdigest()


def normalize(value: Any) -> str:
    if value is None or value == "":
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


DIMENSIONS = (
    "dataset_role",
    "primary_bucket",
    "enemy_present",
    "map",
    "gametype",
    "weapon",
    "weapon_action",
    "locomotion_direction",
    "movement_profile",
    "view_direction",
    "jump",
    "zoom",
    "target_net_displacement_bin",
    "actual_net_displacement_bin",
    "target_yaw_range_bin",
    "actual_yaw_range_bin",
    "target_pitch_range_bin",
    "actual_pitch_range_bin",
    "target_relation",
    "actual_target_relation",
    "distance_bin",
    "role_eligible",
    "actual_fire",
    "actual_damage",
    "collision_intent",
    "renderer",
)


def project(
    plan: dict[str, Any], accepted: dict[str, Any]
) -> dict[str, Any]:
    action = plan.get("action_design") or {}
    targets = plan.get("scheduler_targets") or {}
    actual = accepted.get("actual") or {}
    actual_motion = actual.get("motion") or {}
    actual_relation = actual.get("target_relation") or {}
    qa = accepted.get("qa") or {}
    certificate = (
        plan.get("player_path_certificate")
        or plan.get("player_route_certificate")
        or {}
    )
    blockage = (
        certificate.get("movement_blockage")
        or plan.get("certified_collision")
        or {}
    )
    return {
        "episode_id": str(plan["episode_id"]),
        "candidate_ordinal": plan.get("candidate_ordinal"),
        "assigned_shard": accepted.get("assigned_shard"),
        "dataset_role": plan.get("dataset_role"),
        "primary_bucket": plan.get("primary_bucket"),
        "enemy_present": bool(plan.get("enemy_present")),
        "map": plan.get("map"),
        "gametype": plan.get("gametype"),
        "weapon": plan.get("weapon"),
        "weapon_action": action.get("weapon_action"),
        "locomotion_direction": action.get("locomotion_direction"),
        "movement_profile": action.get("movement_profile"),
        "movement_xy_magnitude": action.get("movement_xy_magnitude"),
        "movement_speed": action.get("movement_speed"),
        "view_direction": action.get("view_direction"),
        "view_profile": action.get("view_profile"),
        "yaw_amplitude": action.get("yaw_amplitude"),
        "pitch_amplitude": action.get("pitch_amplitude"),
        "jump": bool(action.get("jump")),
        "zoom": bool(action.get("zoom")),
        "target_net_displacement_bin": targets.get(
            "net_displacement_bin"
        ),
        "actual_net_displacement_bin": actual_motion.get(
            "net_displacement_bin"
        ),
        "actual_path_length_3d": actual_motion.get("path_length_3d"),
        "actual_net_displacement_3d": actual_motion.get(
            "net_displacement_3d"
        ),
        "target_yaw_range_bin": targets.get("yaw_range_bin"),
        "actual_yaw_range_bin": actual_motion.get("yaw_range_bin"),
        "actual_yaw_range_deg": actual_motion.get("yaw_range_deg"),
        "target_pitch_range_bin": targets.get("pitch_range_bin"),
        "actual_pitch_range_bin": actual_motion.get("pitch_range_bin"),
        "actual_pitch_range_deg": actual_motion.get("pitch_range_deg"),
        "target_relation": targets.get("target_relation"),
        "actual_target_relation": actual_relation.get(
            "actual_target_relation"
        ),
        "distance_bin": targets.get("distance_bin"),
        "role_eligible": accepted.get("role_eligible"),
        "actual_fire": int(qa.get("fire_count") or 0) > 0,
        "fire_count": int(qa.get("fire_count") or 0),
        "actual_damage": int(qa.get("damage_count") or 0) > 0,
        "damage_count": int(qa.get("damage_count") or 0),
        "collision_intent": blockage.get("collision_intent", "none"),
        "blocked_fraction": blockage.get(
            "blocked_fraction_of_commanded", 0.0
        ),
        "visible_collision_qualified": blockage.get(
            "visible_collision_qualified", False
        ),
        "renderer": qa.get("renderer"),
        "episode_path": accepted.get("episode_path"),
        "published_utc": accepted.get("published_utc"),
        "training_admitted": accepted.get("training_admitted"),
    }


def counters(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    result = {name: Counter() for name in DIMENSIONS}
    for row in rows:
        for name in DIMENSIONS:
            result[name][normalize(row.get(name))] += 1
    return {
        name: dict(
            sorted(
                values.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )
        for name, values in result.items()
    }


def ffprobe_contract(video: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            (
                "stream=codec_name,codec_type,width,height,avg_frame_rate,"
                "nb_read_frames,sample_rate,channels"
            ),
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "passed": False,
            "error": completed.stderr[-2000:],
        }
    payload = json.loads(completed.stdout)
    streams = payload.get("streams") or []
    video_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
        ),
        {},
    )
    audio_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "audio"
        ),
        {},
    )
    duration = float((payload.get("format") or {}).get("duration", 0))
    checks = {
        "h264": video_stream.get("codec_name") == "h264",
        "width_1280": int(video_stream.get("width") or 0) == 1280,
        "height_720": int(video_stream.get("height") or 0) == 720,
        "frames_320": int(
            video_stream.get("nb_read_frames") or 0
        )
        == 320,
        "fps_64": video_stream.get("avg_frame_rate") == "64/1",
        "flac": audio_stream.get("codec_name") == "flac",
        "sample_rate_48000": int(
            audio_stream.get("sample_rate") or 0
        )
        == 48_000,
        "stereo": int(audio_stream.get("channels") or 0) == 2,
        "duration_5": abs(duration - 5.0) <= 0.001,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "duration": duration,
        "video": video_stream,
        "audio": audio_stream,
    }


def make_thumbnail(video: Path, destination: Path) -> str | None:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vf",
            "fps=3/5,scale=320:180,tile=3x1:padding=2",
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(destination),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        return completed.stderr[-2000:]
    return None


def verify_one(
    row: dict[str, Any],
    accepted: dict[str, Any],
    review_root: Path,
) -> dict[str, Any]:
    episode_id = row["episode_id"]
    episode_path = Path(str(accepted["episode_path"]))
    episode_json_path = episode_path / "episode.json"
    qa_path = episode_path / "qa.json"
    ready_path = episode_path / "PUBLICATION_READY.json"
    video = episode_path / "video.mkv"
    errors: list[str] = []
    episode: dict[str, Any] = {}
    qa: dict[str, Any] = {}
    ready: dict[str, Any] = {}
    for name, path in (
        ("episode", episode_json_path),
        ("qa", qa_path),
        ("publication_ready", ready_path),
    ):
        try:
            value = load_json(path)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            value = {}
        if name == "episode":
            episode = value
        elif name == "qa":
            qa = value
        else:
            ready = value

    hash_mismatches: list[str] = []
    for relative, expected in sorted(
        (accepted.get("package_sha256") or {}).items()
    ):
        path = episode_path / relative
        actual = sha256_file(path) if path.is_file() else None
        if actual != expected:
            hash_mismatches.append(relative)

    hard_gates = qa.get("hard_gates") or {}
    failed_hard_gates = [
        name for name, passed in hard_gates.items() if passed is not True
    ]
    audio = qa.get("audio") or {}
    mapping = qa.get("mapping") or {}
    mode = qa.get("mode") or {}
    hud = qa.get("hud") or {}
    video_qa = qa.get("video") or {}
    checks = {
        "publication_ready": (
            ready.get("episode_id") == episode_id
            and ready.get("kind") == "candidate"
        ),
        "episode_id_exact": episode.get("episode_id") == episode_id,
        "capture_accepted": qa.get("accepted") is True,
        "all_hard_gates": bool(hard_gates) and not failed_hard_gates,
        "frames_320": int(video_qa.get("frames") or 0) == 320,
        "audio_240000": int(
            audio.get("samples_per_channel") or 0
        )
        == 240_000,
        "mapping_1": float(mapping.get("success_rate") or 0) == 1.0,
        "gametype_exact": (
            mode.get("requested_gametype")
            == mode.get("realized_gametype")
        ),
        "hud_policy": (
            hud.get("cl_hidewaypoints") == 2
            and hud.get("g_ctf_flag_waypoint") == 0
            and hud.get("hud_panel_modicons") == 0
        ),
        "hardware_renderer": str(
            (qa.get("runtime") or {}).get("renderer")
            or episode.get("renderer")
            or ""
        ).startswith("NVIDIA "),
        "formal_authorized": (
            episode.get("formal_collection_authorized") is True
        ),
        "training_not_admitted": (
            episode.get("training_admitted") is False
        ),
        "package_hashes": not hash_mismatches,
    }
    probe = ffprobe_contract(video) if video.is_file() else {
        "passed": False,
        "error": "video_missing",
    }
    checks["ffprobe_contract"] = probe.get("passed") is True

    thumbnail = review_root / "thumbnails" / f"{episode_id}.jpg"
    thumbnail_error = (
        make_thumbnail(video, thumbnail)
        if video.is_file()
        else "video_missing"
    )
    checks["thumbnail"] = thumbnail_error is None
    if thumbnail_error:
        errors.append(f"thumbnail: {thumbnail_error}")

    action = episode.get("action_design") or {}
    acceptance = episode.get("acceptance") or {}
    result = {
        **row,
        "audio_peak_s16": audio.get("peak_s16"),
        "audio_rms_s16": audio.get("rms_s16"),
        "audio_nonzero_fraction": audio.get("nonzero_fraction"),
        "reload_success": acceptance.get("reload_success"),
        "actual_outcome": (
            (episode.get("actual_outcome") or {}).get(
                "actual_outcome_bin"
            )
        ),
        "action_design": action,
        "checks": checks,
        "passed": all(checks.values()),
        "failed_checks": [
            name for name, passed in checks.items() if not passed
        ],
        "failed_hard_gates": failed_hard_gates,
        "hash_mismatches": hash_mismatches,
        "ffprobe": probe,
        "errors": errors,
    }
    return result


def option_html(
    rows: list[dict[str, Any]], field: str
) -> str:
    values = Counter(normalize(row.get(field)) for row in rows)
    return "".join(
        f'<option value="{html.escape(value, quote=True)}">'
        f"{html.escape(value)} ({count})</option>"
        for value, count in sorted(
            values.items(), key=lambda item: (-item[1], item[0])
        )
    )


def write_html(
    path: Path,
    snapshot: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    cards: list[str] = []
    for row in rows:
        episode_id = html.escape(row["episode_id"])
        video = (
            "../stage1_foundation_v5_output_56x1/candidates/"
            f"{episode_id}/video.mkv"
        )
        fields = {
            name: normalize(row.get(name))
            for name in (
                "dataset_role",
                "enemy_present",
                "gametype",
                "weapon_action",
                "locomotion_direction",
                "view_direction",
                "role_eligible",
                "actual_fire",
            )
        }
        data = " ".join(
            f'data-{name.replace("_", "-")}='
            f'"{html.escape(value, quote=True)}"'
            for name, value in fields.items()
        )
        status_class = "pass" if row["passed"] else "fail"
        cards.append(
            f"""
<article class="card {status_class}" {data}>
  <video controls playsinline preload="none"
    poster="thumbnails/{episode_id}.jpg"
    src="{video}"></video>
  <h2>#{row['sample_index']:03d} · {episode_id}</h2>
  <p><b>{html.escape(str(row['map']))} / {html.escape(str(row['gametype']))}</b>
    · {html.escape(str(row['dataset_role']))}
    · {html.escape(str(row['primary_bucket']))}</p>
  <p>weapon <b>{html.escape(str(row['weapon']))}</b>;
    action <b>{html.escape(str(row['weapon_action']))}</b>;
    fire {row['fire_count']}; reload success
    {html.escape(str(row.get('reload_success')))}</p>
  <p>move <b>{html.escape(str(row['locomotion_direction']))}</b>
    ({html.escape(str(row.get('movement_xy_magnitude')))});
    view <b>{html.escape(str(row['view_direction']))}</b>;
    yaw {html.escape(str(row.get('yaw_amplitude')))}°;
    pitch {html.escape(str(row.get('pitch_amplitude')))}°</p>
  <p>actual motion: net
    {html.escape(str(row['actual_net_displacement_bin']))},
    path {float(row.get('actual_path_length_3d') or 0):.1f};
    yaw {float(row.get('actual_yaw_range_deg') or 0):.1f}°;
    pitch {float(row.get('actual_pitch_range_deg') or 0):.1f}°</p>
  <p>enemy {str(row['enemy_present']).lower()};
    relation {html.escape(str(row['actual_target_relation']))};
    collision {html.escape(str(row['collision_intent']))};
    blocked {float(row.get('blocked_fraction') or 0):.3f}</p>
  <p>audio peak {row.get('audio_peak_s16')};
    RMS {float(row.get('audio_rms_s16') or 0):.2f};
    role eligible {str(row['role_eligible']).lower()};
    verify <b>{status_class.upper()}</b></p>
  <details><summary>verification / action JSON</summary><pre>{html.escape(json.dumps({
      'checks': row['checks'],
      'failed_checks': row['failed_checks'],
      'action_design': row['action_design'],
  }, indent=2, ensure_ascii=False))}</pre></details>
</article>"""
        )

    selectors = (
        ("datasetRole", "dataset_role", "role"),
        ("enemyPresent", "enemy_present", "enemy"),
        ("gametype", "gametype", "mode"),
        ("weaponAction", "weapon_action", "weapon action"),
        ("locomotionDirection", "locomotion_direction", "move"),
        ("viewDirection", "view_direction", "view"),
        ("roleEligible", "role_eligible", "eligible"),
        ("actualFire", "actual_fire", "actual fire"),
    )
    controls = "".join(
        f"""<label>{label}<select data-filter="{data_name}">
  <option value="">all ({len(rows)})</option>{option_html(rows, field)}
</select></label>"""
        for data_name, field, label in selectors
    )
    full = snapshot["landed_distribution"]
    sample = snapshot["sample_distribution"]
    distribution = html.escape(
        json.dumps(
            {
                "full_landed_accepted": full,
                "uniform_sample": sample,
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    verification = snapshot["verification"]
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage-1 landed accepted uniform review</title>
<style>
body{{margin:24px;font:14px/1.45 system-ui,sans-serif;color:#e8edf2;background:#10151b}}
a{{color:#89bdff}} h1{{margin-bottom:4px}} .summary{{display:flex;gap:12px;flex-wrap:wrap}}
.metric{{padding:10px 14px;border:1px solid #354351;border-radius:9px;background:#182129}}
.toolbar{{position:sticky;top:0;z-index:3;margin:16px 0;padding:12px;background:#10151bee;
 border:1px solid #354351;border-radius:10px;backdrop-filter:blur(8px)}}
label{{display:inline-flex;flex-direction:column;margin:0 9px 8px 0;color:#9eafbf}}
select{{min-width:135px;padding:5px;color:#e8edf2;background:#182129;border:1px solid #526170}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:16px}}
.card{{padding:12px;border:1px solid #354351;border-radius:10px;background:#182129}}
.card.fail{{border-color:#ff6868}} video{{display:block;width:100%;aspect-ratio:16/9;background:#000}}
h2{{font-size:15px;overflow-wrap:anywhere}} p{{margin:6px 0;color:#c4ced8}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:#b8c9d9}} details{{margin-top:8px}}
</style></head><body>
<h1>Stage-1 已落地 accepted 数据 · 固定种子均匀随机 100 条</h1>
<p>snapshot {html.escape(snapshot['created_utc'])}；不是人工分层拼样本。
population fingerprint <code>{snapshot['population_sha256']}</code></p>
<div class="summary">
 <div class="metric">landed accepted <b>{snapshot['accepted_population']}</b></div>
 <div class="metric">data hours <b>{snapshot['accepted_data_hours']:.2f}</b></div>
 <div class="metric">sample <b>{len(rows)}</b></div>
 <div class="metric">verified <b>{verification['passed']} / {len(rows)}</b></div>
 <div class="metric">enemy <b>{sample['enemy_present'].get('true', 0)}</b></div>
 <div class="metric">actual fire <b>{sample['actual_fire'].get('true', 0)}</b></div>
</div>
<p><a href="REVIEW.json">REVIEW.json</a> ·
<a href="SAMPLE_MANIFEST.jsonl">sample manifest</a> ·
<a href="SAMPLE_EPISODES.csv">CSV</a> ·
<a href="REPORT.md">report</a></p>
<details><summary>完整 landed 与 random-100 分布</summary>
<pre>{distribution}</pre></details>
<div class="toolbar">{controls}<span id="visible">{len(rows)} visible</span></div>
<div class="grid">{''.join(cards)}</div>
<script>
const filters=[...document.querySelectorAll('[data-filter]')];
const cards=[...document.querySelectorAll('.card')];
function applyFilters(){{
 let visible=0;
 for(const card of cards){{
  const show=filters.every(s=>!s.value||
   card.dataset[s.dataset.filter]===s.value);
  card.hidden=!show;if(show)visible++;
 }}
 document.querySelector('#visible').textContent=`${{visible}} visible`;
}}
for(const select of filters)select.addEventListener('change',applyFilters);
</script></body></html>
"""
    atomic_text(path, document)


def markdown_distribution(
    name: str,
    full: dict[str, int],
    sample: dict[str, int],
) -> str:
    keys = sorted(set(full) | set(sample))
    full_total = sum(full.values())
    sample_total = sum(sample.values())
    lines = [
        f"### {name}",
        "",
        "| value | landed accepted | random 100 |",
        "|---|---:|---:|",
    ]
    for key in keys:
        full_count = full.get(key, 0)
        sample_count = sample.get(key, 0)
        lines.append(
            f"| `{key}` | {full_count} "
            f"({100 * full_count / full_total:.1f}%) | "
            f"{sample_count} "
            f"({100 * sample_count / sample_total:.1f}%) |"
        )
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "sample_index",
        "episode_id",
        "selection_key",
        "map",
        "gametype",
        "dataset_role",
        "primary_bucket",
        "enemy_present",
        "weapon",
        "weapon_action",
        "locomotion_direction",
        "movement_xy_magnitude",
        "view_direction",
        "yaw_amplitude",
        "pitch_amplitude",
        "actual_net_displacement_bin",
        "actual_path_length_3d",
        "actual_yaw_range_deg",
        "actual_pitch_range_deg",
        "actual_target_relation",
        "fire_count",
        "reload_success",
        "collision_intent",
        "blocked_fraction",
        "audio_peak_s16",
        "audio_rms_s16",
        "role_eligible",
        "passed",
        "episode_path",
    ]
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT
    )
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument(
        "--review-root", type=Path, default=DEFAULT_REVIEW_ROOT
    )
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--shard-count", type=int, default=56)
    parser.add_argument("--verify-workers", type=int, default=8)
    args = parser.parse_args()

    manifest_root = args.manifest_root.resolve()
    output_root = args.output_root.resolve()
    review_root = args.review_root.resolve()
    if review_root.exists():
        raise RuntimeError(f"review root already exists: {review_root}")
    if args.sample_size <= 0:
        raise RuntimeError("sample size must be positive")
    accepted = load_accepted(output_root, args.shard_count)
    if len(accepted) < args.sample_size:
        raise RuntimeError(
            f"sample {args.sample_size} exceeds accepted {len(accepted)}"
        )
    episode_ids = sorted(accepted)
    population_sha256 = hashlib.sha256(
        ("\n".join(episode_ids) + "\n").encode("utf-8")
    ).hexdigest()
    ranked = sorted(
        (
            selection_key(args.seed, episode_id),
            episode_id,
        )
        for episode_id in episode_ids
    )
    selected = ranked[: args.sample_size]
    selected_ids = {episode_id for _, episode_id in selected}

    plan_projections: dict[str, dict[str, Any]] = {}
    joined_ids: set[str] = set()
    landed_rows: list[dict[str, Any]] = []
    input_manifest = manifest_root / "input.jsonl"
    for plan in stream_jsonl(input_manifest):
        episode_id = str(plan["episode_id"])
        record = accepted.get(episode_id)
        if record is None:
            continue
        row = project(plan, record)
        landed_rows.append(row)
        joined_ids.add(episode_id)
        if episode_id in selected_ids:
            plan_projections[episode_id] = row
    if len(landed_rows) != len(accepted):
        missing = sorted(set(accepted) - joined_ids)
        raise RuntimeError(
            f"accepted/manifest join incomplete: "
            f"{len(landed_rows)}/{len(accepted)} sample_missing={missing[:5]}"
        )
    if len(plan_projections) != args.sample_size:
        raise RuntimeError(
            f"sample plan join incomplete: "
            f"{len(plan_projections)}/{args.sample_size}"
        )

    review_root.mkdir(parents=True)
    (review_root / "thumbnails").mkdir()
    sample_rows = []
    for sample_index, (key, episode_id) in enumerate(selected, 1):
        sample_rows.append(
            {
                **plan_projections[episode_id],
                "sample_index": sample_index,
                "selection_key": key,
            }
        )

    verified_by_id: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.verify_workers
    ) as executor:
        futures = {
            executor.submit(
                verify_one,
                row,
                accepted[row["episode_id"]],
                review_root,
            ): row["episode_id"]
            for row in sample_rows
        }
        for future in concurrent.futures.as_completed(futures):
            episode_id = futures[future]
            verified_by_id[episode_id] = future.result()
            print(
                f"verified {len(verified_by_id)}/{len(sample_rows)} "
                f"episode={episode_id} "
                f"passed={verified_by_id[episode_id]['passed']}",
                flush=True,
            )
    verified = [
        verified_by_id[row["episode_id"]] for row in sample_rows
    ]
    landed_distribution = counters(landed_rows)
    sample_distribution = counters(verified)
    failed = [
        {
            "episode_id": row["episode_id"],
            "failed_checks": row["failed_checks"],
            "hash_mismatches": row["hash_mismatches"],
            "errors": row["errors"],
        }
        for row in verified
        if not row["passed"]
    ]
    snapshot = {
        "schema_version": "xonotic-stage1-landed-uniform-review-v1",
        "created_utc": utc_now(),
        "seed": args.seed,
        "selection_method": (
            "sort accepted episode IDs by "
            "sha256(seed + NUL + episode_id); take first N"
        ),
        "population_sha256": population_sha256,
        "accepted_population": len(accepted),
        "accepted_data_hours": len(accepted) * 5 / 3600,
        "sample_size": args.sample_size,
        "manifest_root": str(manifest_root),
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": sha256_file(input_manifest),
        "output_root": str(output_root),
        "landed_distribution": landed_distribution,
        "sample_distribution": sample_distribution,
        "verification": {
            "passed": len(verified) - len(failed),
            "failed": len(failed),
            "failures": failed,
            "full_package_sha256_checked": True,
            "ffprobe_checked": True,
            "thumbnail_checked": True,
        },
        "sample": verified,
    }
    atomic_text(
        review_root / "REVIEW.json",
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
    )
    atomic_text(
        review_root / "SAMPLE_MANIFEST.jsonl",
        "".join(
            json.dumps(
                {
                    "sample_index": row["sample_index"],
                    "selection_key": row["selection_key"],
                    "episode_id": row["episode_id"],
                    "episode_path": row["episode_path"],
                    "passed": row["passed"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for row in verified
        ),
    )
    write_csv(review_root / "SAMPLE_EPISODES.csv", verified)
    report = [
        "# Stage-1 已落地 accepted 数据固定种子随机审查",
        "",
        f"- 创建时间：`{snapshot['created_utc']}`",
        f"- accepted population：`{len(accepted)}`（"
        f"`{snapshot['accepted_data_hours']:.2f}` 小时数据）",
        f"- population SHA256：`{population_sha256}`",
        f"- seed：`{args.seed}`",
        f"- sample：`{args.sample_size}`，验证通过："
        f"`{snapshot['verification']['passed']}`，失败：`{len(failed)}`",
        "- 抽样是当前 accepted 集合上的均匀 hash-rank，不做分层或人工补样。",
        "- 全部 sample 校验完整 package SHA256、ffprobe、320 帧、"
        "240000 音频采样、mapping、HUD、gametype 和全部 hard gates。",
        "",
        "## 分布",
        "",
    ]
    for dimension in DIMENSIONS:
        report.extend(
            [
                markdown_distribution(
                    dimension,
                    landed_distribution[dimension],
                    sample_distribution[dimension],
                ),
                "",
            ]
        )
    atomic_text(review_root / "REPORT.md", "\n".join(report))
    write_html(review_root / "index.html", snapshot, verified)
    print(
        json.dumps(
            {
                "review_root": str(review_root),
                "accepted_population": len(accepted),
                "sample_size": len(verified),
                "passed": snapshot["verification"]["passed"],
                "failed": len(failed),
                "population_sha256": population_sha256,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
