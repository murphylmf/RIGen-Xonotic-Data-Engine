                      
"""Summarize a bounded formal Stage-1 review capture without admitting training data."""

from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT_DEFAULT = Path("./xonotic_capture")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_jsonl(path: Path, limit: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
                if limit and len(rows) >= limit:
                    break
    return rows


def rejection_failure_labels(
    rejection: dict[str, Any],
) -> list[str]:
    """Extract stable labels from dict, list, or plain-text reject details."""
    reason = str(rejection.get("reason") or "unknown")
    detail = str(rejection.get("detail", ""))
    payload_text = detail.partition(": ")[2]
    try:
        payload = json.loads(payload_text)
    except (json.JSONDecodeError, TypeError):
        payload = None

    labels: list[str] = []
    if isinstance(payload, dict):
        failed = payload.get("failed") or []
        if isinstance(failed, str):
            labels.append(failed)
        elif isinstance(failed, list):
            labels.extend(str(value) for value in failed)
        checks = payload.get("checks") or {}
        if isinstance(checks, dict):
            labels.extend(
                str(name)
                for name, passed in checks.items()
                if passed is not True
            )
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                labels.append(item)
            elif isinstance(item, dict):
                label = (
                    item.get("reason")
                    or item.get("label")
                    or item.get("gate")
                )
                if label:
                    labels.append(str(label))

    return list(dict.fromkeys(labels)) or [reason]


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {
        key: counter[key]
        for key in sorted(counter, key=lambda item: (-counter[item], item))
    }


def label(value: Any) -> str:
    if value is None or value == "":
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


SCENARIO_FIELDS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "dataset_role": lambda row: row.get("dataset_role"),
    "primary_bucket": lambda row: row.get("primary_bucket"),
    "category": lambda row: row.get("category"),
    "enemy_present": lambda row: row.get("enemy_present"),
    "map": lambda row: row.get("map"),
    "gametype": lambda row: row.get("gametype"),
    "map_gametype": lambda row: (
        f"{row.get('map')}::{row.get('gametype')}"
    ),
    "weapon": lambda row: row.get("weapon"),
    "action_program": lambda row: row.get("action_program"),
    "fire_required": lambda row: (
        (row.get("acceptance") or {}).get("fire_required")
    ),
    "route_present": lambda row: bool(row.get("route_request")),
    "enemy_policy": lambda row: (
        (row.get("enemy_policy") or {}).get("name")
    ),
    "enemy_model": lambda row: (
        row.get("enemy_model") if row.get("enemy_present") else None
    ),
    "enemy_color": lambda row: (
        row.get("enemy_color") if row.get("enemy_present") else None
    ),
    "fire_weapon": lambda row: (
        row.get("weapon")
        if (row.get("acceptance") or {}).get("fire_required")
        else None
    ),
    "route_view_policy": lambda row: row.get("route_view_policy"),
    "net_displacement_bin": lambda row: (
        (row.get("scheduler_targets") or {}).get(
            "net_displacement_bin"
        )
    ),
    "yaw_range_bin": lambda row: (
        (row.get("scheduler_targets") or {}).get("yaw_range_bin")
    ),
    "pitch_range_bin": lambda row: (
        (row.get("scheduler_targets") or {}).get("pitch_range_bin")
    ),
    "target_relation": lambda row: (
        (row.get("scheduler_targets") or {}).get("target_relation")
    ),
    "distance_bin": lambda row: (
        (row.get("scheduler_targets") or {}).get("distance_bin")
    ),
}


def summarize_scenarios(
    rows: Iterable[dict[str, Any]],
) -> tuple[int, dict[str, dict[str, int]]]:
    counters = {name: Counter() for name in SCENARIO_FIELDS}
    total = 0
    for row in rows:
        total += 1
        for name, getter in SCENARIO_FIELDS.items():
            value = getter(row)
            if value is not None and value != "":
                counters[name][label(value)] += 1
    return total, {
        name: counter_dict(counter) for name, counter in counters.items()
    }


def stream_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def qa_details(record: dict[str, Any]) -> dict[str, Any]:
    episode = Path(record["episode_path"])
    qa_path = episode / "qa.json"
    if not qa_path.is_file():
        return {"qa_file_present": False, "qa_path": str(qa_path)}
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    hard_gates = qa.get("hard_gates") or qa.get("gates") or {}
    audio = qa.get("audio") or {}
    motion = qa.get("motion") or {}
    blockage = motion.get("blockage") or {}
    failures = [
        key for key, passed in hard_gates.items() if passed is not True
    ]
    return {
        "qa_file_present": True,
        "qa_path": str(qa_path),
        "all_hard_gates_pass": bool(hard_gates)
        and not failures,
        "hard_gate_failures": failures,
        "audio_peak_s16": audio.get("peak_s16"),
        "audio_nonzero_fraction": audio.get("nonzero_fraction"),
        "audio_rms_s16": audio.get("rms_s16"),
        "blockage_training_exclusion_recommended": blockage.get(
            "training_exclusion_recommended", False
        ),
    }


def summarize_realized(
    joined: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    qa_failures: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    alignment_keys = {
        "net_displacement_bin": (
            lambda record: record["actual"]["motion"].get(
                "net_displacement_bin"
            )
        ),
        "yaw_range_bin": (
            lambda record: record["actual"]["motion"].get("yaw_range_bin")
        ),
        "pitch_range_bin": (
            lambda record: record["actual"]["motion"].get(
                "pitch_range_bin"
            )
        ),
        "target_relation": (
            lambda record: record["actual"]["target_relation"].get(
                "actual_target_relation"
            )
        ),
        "distance_bin": (
            lambda record: record["actual"]["target_relation"].get(
                "actual_distance_bin"
            )
        ),
    }
    alignment = {
        key: {"matched": 0, "compared": 0, "cross_tab": defaultdict(Counter)}
        for key in alignment_keys
    }
    aggregate_checks: Counter[str] = Counter()
    role_ineligible_reasons: Counter[str] = Counter()

    for item in joined:
        plan = item["plan"]
        record = item["record"]
        qa = record["qa"]
        actual_motion = record["actual"]["motion"]
        actual_relation = record["actual"]["target_relation"]
        details = qa_details(record)

        values = {
            "dataset_role": record.get("dataset_role"),
            "primary_bucket": record.get("primary_bucket"),
            "category": plan.get("category"),
            "enemy_present": record.get("enemy_present"),
            "map": record.get("map"),
            "gametype": record.get("gametype"),
            "map_gametype": (
                f"{record.get('map')}::{record.get('gametype')}"
            ),
            "weapon": record.get("weapon"),
            "action_program": plan.get("action_program"),
            "fire_required": (
                (plan.get("acceptance") or {}).get("fire_required")
            ),
            "route_present": bool(plan.get("route_request")),
            "enemy_policy": (
                (plan.get("enemy_policy") or {}).get("name")
            ),
            "enemy_model": (
                plan.get("enemy_model")
                if record.get("enemy_present")
                else None
            ),
            "enemy_color": (
                plan.get("enemy_color")
                if record.get("enemy_present")
                else None
            ),
            "fire_weapon": (
                record.get("weapon")
                if (plan.get("acceptance") or {}).get("fire_required")
                else None
            ),
            "route_view_policy": plan.get("route_view_policy"),
            "net_displacement_bin": actual_motion.get(
                "net_displacement_bin"
            ),
            "yaw_range_bin": actual_motion.get("yaw_range_bin"),
            "pitch_range_bin": actual_motion.get("pitch_range_bin"),
            "target_relation": actual_relation.get(
                "actual_target_relation"
            ),
            "distance_bin": actual_relation.get("actual_distance_bin"),
            "role_eligible": record.get("role_eligible"),
            "actual_fire": int(qa.get("fire_count", 0)) > 0,
            "renderer": qa.get("renderer"),
            "realized_gametype": qa.get("realized_gametype"),
            "x264_threads": (
                (record.get("runtime") or {}).get("x264_threads")
            ),
            "x264_preset": (
                (record.get("runtime") or {}).get("x264_preset")
            ),
            "encode_concurrency": (
                (record.get("runtime") or {}).get("encode_concurrency")
            ),
        }
        for name, value in values.items():
            if name == "target_relation" and not record.get(
                "enemy_present"
            ):
                continue
            if value is not None and value != "":
                counters[name][label(value)] += 1

        checks = {
            "formal_collection_authorized": (
                record.get("formal_collection_authorized") is True
            ),
            "training_admitted_false": (
                record.get("training_admitted") is False
            ),
            "hard_gates_pass": qa.get("hard_gates_pass") is True,
            "frames_320": qa.get("frames") == 320,
            "audio_samples_240000": (
                qa.get("audio_samples_per_channel") == 240_000
            ),
            "mapping_rate_1": qa.get("mapping_rate") == 1,
            "nvidia_hardware_renderer": str(
                qa.get("renderer", "")
            ).startswith("NVIDIA "),
            "route_passed": qa.get("route_passed") is True,
            "enemy_path_trace_passed": (
                qa.get("enemy_path_trace_passed") is True
            ),
            "gametype_exact": (
                qa.get("requested_gametype")
                == qa.get("realized_gametype")
            ),
            "hud_waypoints_hidden": (
                (qa.get("hud") or {}).get("cl_hidewaypoints") == 2
                and (qa.get("hud") or {}).get("g_ctf_flag_waypoint") == 0
                and (qa.get("hud") or {}).get("hud_panel_modicons") == 0
            ),
            "qa_file_present": details.get("qa_file_present") is True,
            "all_full_qa_hard_gates_pass": (
                details.get("all_hard_gates_pass") is True
            ),
            "expected_audio_nonzero": (
                not bool(plan.get("expects_sound"))
                or float(details.get("audio_peak_s16") or 0) > 0
            ),
        }
        failed = [name for name, passed in checks.items() if not passed]
        for name, passed in checks.items():
            if passed:
                aggregate_checks[name] += 1
        if failed:
            qa_failures.append(
                {
                    "episode_id": record["episode_id"],
                    "failed_checks": failed,
                    "hard_gate_failures": details.get(
                        "hard_gate_failures", []
                    ),
                }
            )
        if record.get("role_eligible") is not True:
            ineligible = []
            if int(qa.get("damage_count", 0)) > 0:
                ineligible.append("damage_count_gt_0")
            if (
                record.get("dataset_role")
                == "foundation_enemy_distractor"
                and int(qa.get("fire_count", 0)) > 0
            ):
                ineligible.append("enemy_distractor_fire_count_gt_0")
            if details.get(
                "blockage_training_exclusion_recommended"
            ):
                ineligible.append("motion_blockage")
            if qa.get("route_passed") is not True:
                ineligible.append("route_failed")
            if qa.get("enemy_path_trace_passed") is not True:
                ineligible.append("enemy_path_trace_failed")
            if not ineligible:
                ineligible.append("unclassified")
            role_ineligible_reasons.update(ineligible)

        for key, actual_getter in alignment_keys.items():
            expected = (plan.get("scheduler_targets") or {}).get(key)
            actual = actual_getter(record)
            if expected is None or actual is None:
                continue
            alignment[key]["compared"] += 1
            alignment[key]["matched"] += expected == actual
            alignment[key]["cross_tab"][str(expected)][str(actual)] += 1

        episode_rows.append(
            {
                "episode_id": record["episode_id"],
                "candidate_ordinal": plan.get("candidate_ordinal"),
                "assigned_shard": record.get("assigned_shard"),
                "map": record.get("map"),
                "gametype": record.get("gametype"),
                "weapon": record.get("weapon"),
                "dataset_role": record.get("dataset_role"),
                "primary_bucket": record.get("primary_bucket"),
                "category": plan.get("category"),
                "enemy_present": record.get("enemy_present"),
                "enemy_policy": values["enemy_policy"],
                "fire_required": values["fire_required"],
                "fire_count": qa.get("fire_count"),
                "damage_count": qa.get("damage_count"),
                "role_eligible": record.get("role_eligible"),
                "target_net": (
                    plan["scheduler_targets"]["net_displacement_bin"]
                ),
                "actual_net": values["net_displacement_bin"],
                "target_yaw": plan["scheduler_targets"]["yaw_range_bin"],
                "actual_yaw": values["yaw_range_bin"],
                "target_pitch": (
                    plan["scheduler_targets"]["pitch_range_bin"]
                ),
                "actual_pitch": values["pitch_range_bin"],
                "target_relation": (
                    plan["scheduler_targets"].get("target_relation")
                ),
                "actual_relation": values["target_relation"],
                "target_distance": (
                    plan["scheduler_targets"].get("distance_bin")
                ),
                "actual_distance": values["distance_bin"],
                "frames": qa.get("frames"),
                "audio_samples_per_channel": qa.get(
                    "audio_samples_per_channel"
                ),
                "audio_peak_s16": details.get("audio_peak_s16"),
                "mapping_rate": qa.get("mapping_rate"),
                "renderer": qa.get("renderer"),
                "qa_pass": not failed,
                "episode_path": record.get("episode_path"),
            }
        )

    serialized_alignment: dict[str, Any] = {}
    for key, item in alignment.items():
        compared = int(item["compared"])
        serialized_alignment[key] = {
            "matched": int(item["matched"]),
            "compared": compared,
            "match_rate": (
                float(item["matched"]) / compared if compared else None
            ),
            "cross_tab": {
                expected: counter_dict(actuals)
                for expected, actuals in sorted(
                    item["cross_tab"].items()
                )
            },
        }

    return (
        {
            "rows": len(joined),
            "distributions": {
                name: counter_dict(counter)
                for name, counter in sorted(counters.items())
            },
            "qa_pass_rows": len(joined) - len(qa_failures),
            "qa_failures": qa_failures,
            "qa_check_pass_counts": counter_dict(aggregate_checks),
            "role_ineligible_reasons": counter_dict(
                role_ineligible_reasons
            ),
            "alignment": serialized_alignment,
            "joint_large_net_large_yaw": sum(
                row["actual_net"] in {"512_1024", "gt1024"}
                and row["actual_yaw"] in {"90_180", "ge180"}
                for row in episode_rows
            ),
            "path_length_ge_1000": sum(
                record["record"]["actual"]["motion"]["path_length_3d"]
                >= 1000
                for record in joined
            ),
            "path_length_ge_2000": sum(
                record["record"]["actual"]["motion"]["path_length_3d"]
                >= 2000
                for record in joined
            ),
        },
        sorted(
            episode_rows,
            key=lambda row: (
                int(row["candidate_ordinal"] or 0),
                row["episode_id"],
            ),
        ),
    )


def markdown_table(
    name: str,
    full: dict[str, int],
    selected: dict[str, int],
    realized: dict[str, int],
) -> str:
    keys = sorted(
        set(full) | set(selected) | set(realized),
        key=lambda key: (-selected.get(key, 0), key),
    )
    full_total = sum(full.values())
    selected_total = sum(selected.values())
    realized_total = sum(realized.values())
    lines = [
        f"### {name}",
        "",
        "| 值 | 全量 manifest | 本批计划 | 本批实际接受 |",
        "|---|---:|---:|---:|",
    ]
    for key in keys:
        def cell(count: int, total: int) -> str:
            pct = 100 * count / total if total else 0
            return f"{count} ({pct:.1f}%)"

        lines.append(
            f"| `{key}` | {cell(full.get(key, 0), full_total)} | "
            f"{cell(selected.get(key, 0), selected_total)} | "
            f"{cell(realized.get(key, 0), realized_total)} |"
        )
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["episode_id"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_thumbnails(
    rows: list[dict[str, Any]], review_root: Path
) -> list[dict[str, str]]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return [{"episode_id": "*", "error": "ffmpeg_not_found"}]
    destination = review_root / "thumbnails"
    destination.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    for row in rows:
        output = destination / f"{row['episode_id']}.jpg"
        if output.is_file():
            continue
        video = Path(str(row["episode_path"])) / "video.mkv"
        completed = subprocess.run(
            [
                ffmpeg,
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
                str(output),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            errors.append(
                {
                    "episode_id": row["episode_id"],
                    "error": completed.stderr[-1000:],
                }
            )
    return errors


def write_html(
    path: Path,
    snapshot: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    cards: list[str] = []
    for row in rows:
        episode_id = html.escape(str(row["episode_id"]))
        classes = [
            "card",
            "qa-pass" if row["qa_pass"] else "qa-fail",
            "enemy" if row["enemy_present"] else "no-enemy",
            "shooting" if int(row["fire_count"] or 0) > 0 else "no-shot",
        ]
        cards.append(
            f"""
<article class="{' '.join(classes)}" data-mode="{html.escape(str(row['gametype']))}">
  <img loading="lazy" src="thumbnails/{episode_id}.jpg" alt="{episode_id}">
  <h3>{episode_id} · {html.escape(str(row['map']))} / {html.escape(str(row['gametype']))}</h3>
  <p>{html.escape(str(row['dataset_role']))} · {html.escape(str(row['primary_bucket']))} · {html.escape(str(row['weapon']))}</p>
  <p>motion {html.escape(str(row['target_net']))} → {html.escape(str(row['actual_net']))};
     yaw {html.escape(str(row['target_yaw']))} → {html.escape(str(row['actual_yaw']))};
     pitch {html.escape(str(row['target_pitch']))} → {html.escape(str(row['actual_pitch']))}</p>
  <p>relation {html.escape(str(row['target_relation']))} → {html.escape(str(row['actual_relation']))};
     fire {row['fire_count']}; eligible {str(row['role_eligible']).lower()}</p>
  <a href="../candidates/{episode_id}/video.mkv">打开 5 秒视频</a>
</article>"""
        )
    status = snapshot["status"]
    path.write_text(
        f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>Stage-1 数据分布检查</title>
<style>
body{{font-family:system-ui,sans-serif;background:#10131a;color:#e9edf5;margin:24px}}
a{{color:#82b7ff}} .summary{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.metric{{background:#1b2230;padding:12px 16px;border-radius:10px}}
.controls button{{margin:0 6px 12px 0;padding:7px 10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}}
.card{{background:#1b2230;border:1px solid #364258;border-radius:10px;padding:10px}}
.card.qa-fail{{border-color:#ff6b6b}} .card img{{width:100%;height:auto;background:#080a0e}}
.card h3{{font-size:15px;margin:8px 0}} .card p{{font-size:12px;color:#bdc7d8;margin:5px 0}}
.hidden{{display:none}}
</style></head><body>
<h1>Stage-1 数据分布检查</h1>
<p>生成时间 {html.escape(snapshot['generated_utc'])}；所有条目 training_admitted=false。</p>
<div class="summary">
 <div class="metric">计划 <b>{status['planned_rows']}</b></div>
 <div class="metric">接受 <b>{status['accepted_rows']}</b></div>
 <div class="metric">role eligible <b>{status['role_eligible_rows']}</b></div>
 <div class="metric">QA PASS <b>{snapshot['realized']['qa_pass_rows']}</b></div>
 <div class="metric">缺失 <b>{status['missing_rows']}</b></div>
</div>
<div class="controls">
 <button onclick="filterCards('all')">全部</button>
 <button onclick="filterCards('enemy')">含敌人</button>
 <button onclick="filterCards('no-enemy')">无敌人</button>
 <button onclick="filterCards('shooting')">实际射击</button>
 <button onclick="filterCards('dm')">DM</button>
 <button onclick="filterCards('ctf')">CTF</button>
 <button onclick="filterCards('rc')">Race</button>
</div>
<div class="grid">{''.join(cards)}</div>
<script>
function filterCards(kind) {{
 document.querySelectorAll('.card').forEach(c => {{
   const show = kind === 'all' || c.classList.contains(kind) || c.dataset.mode === kind;
   c.classList.toggle('hidden', !show);
 }});
}}
</script></body></html>
""",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--episodes-per-shard", type=int, default=4)
    parser.add_argument("--shard-count", type=int, default=32)
    parser.add_argument("--make-thumbnails", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    manifest_root = root / "manifests/stage1_foundation_v1"
    output_root = root / "stage1_foundation_v1_output"
    review_root = output_root / "review"
    review_root.mkdir(parents=True, exist_ok=True)

    selected: list[dict[str, Any]] = []
    for shard_index in range(args.shard_count):
        tag = f"shard-{shard_index:03d}-of-{args.shard_count:03d}"
        path = manifest_root / "shards/primary" / f"{tag}.jsonl"
        selected.extend(load_jsonl(path, args.episodes_per_shard))
    selected_by_id = {row["episode_id"]: row for row in selected}

    accepted_by_id: dict[str, dict[str, Any]] = {}
    rejects: list[dict[str, Any]] = []
    run_results: list[dict[str, Any]] = []
    for shard_index in range(args.shard_count):
        tag = f"shard-{shard_index:03d}-of-{args.shard_count:03d}"
        shard_root = output_root / "manifests/shards" / tag
        for row in load_jsonl(shard_root / "accepted_candidates.jsonl"):
            if row["episode_id"] in selected_by_id:
                accepted_by_id[row["episode_id"]] = row
        rejects.extend(
            row
            for row in load_jsonl(shard_root / "rejects.jsonl")
            if row["episode_id"] in selected_by_id
        )
        result_path = shard_root / "RUN_RESULT.json"
        if result_path.is_file():
            run_results.append(
                json.loads(result_path.read_text(encoding="utf-8"))
            )

    hard_rejected_ids = {
        row["episode_id"]
        for row in rejects
        if row.get("terminal") is True
        and row.get("retryable") is False
        and row.get("failure_class", "capture_failure")
        == "capture_failure"
    }
    missing = sorted(
        set(selected_by_id) - set(accepted_by_id) - hard_rejected_ids
    )
    joined = [
        {"plan": selected_by_id[episode_id], "record": record}
        for episode_id, record in accepted_by_id.items()
    ]
    full_rows, full_distribution = summarize_scenarios(
        stream_jsonl(manifest_root / "input.jsonl")
    )
    selected_rows, selected_distribution = summarize_scenarios(selected)
    realized, episode_rows = summarize_realized(joined)
    reject_failure_labels: Counter[str] = Counter()
    for rejection in rejects:
        reject_failure_labels.update(
            rejection_failure_labels(rejection)
        )

    status = {
        "planned_rows": selected_rows,
        "accepted_rows": len(accepted_by_id),
        "role_eligible_rows": sum(
            row.get("role_eligible") is True
            for row in accepted_by_id.values()
        ),
        "hard_rejected_rows": len(hard_rejected_ids),
        "reject_attempts": len(rejects),
        "missing_rows": len(missing),
        "missing_episode_ids": missing,
        "completed_shards": sum(
            result.get("selection_complete") is True
            for result in run_results
        ),
        "all_selected_accounted": not missing,
        "training_admitted_rows": sum(
            row.get("training_admitted") is True
            for row in accepted_by_id.values()
        ),
    }
    snapshot = {
        "schema_version": "xonotic-stage1-distribution-review-v1",
        "generated_utc": utc_now(),
        "input": {
            "full_manifest": str(manifest_root / "input.jsonl"),
            "full_manifest_rows": full_rows,
            "selected_shards": args.shard_count,
            "episodes_per_shard": args.episodes_per_shard,
            "output_root": str(output_root),
        },
        "status": status,
        "full_manifest_planned": {
            "rows": full_rows,
            "distributions": full_distribution,
        },
        "selected_planned": {
            "rows": selected_rows,
            "distributions": selected_distribution,
        },
        "realized": realized,
        "reject_reasons": counter_dict(
            Counter(str(row.get("reason")) for row in rejects)
        ),
        "reject_failure_labels": counter_dict(reject_failure_labels),
    }

    thumbnail_errors: list[dict[str, str]] = []
    if args.make_thumbnails:
        thumbnail_errors = make_thumbnails(episode_rows, review_root)
    snapshot["thumbnail_errors"] = thumbnail_errors

    json_path = review_root / "STAGE1_DISTRIBUTION_REVIEW.json"
    csv_path = review_root / "STAGE1_DISTRIBUTION_REVIEW_EPISODES.csv"
    markdown_path = review_root / "STAGE1_DISTRIBUTION_REVIEW_REPORT.md"
    html_path = review_root / "index.html"
    json_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    write_csv(csv_path, episode_rows)

    lines = [
        "# Stage-1 数据分布检查",
        "",
        f"- 生成时间：`{snapshot['generated_utc']}`",
        f"- 计划 / 接受 / role eligible："
        f"`{status['planned_rows']} / {status['accepted_rows']} / "
        f"{status['role_eligible_rows']}`",
        f"- 完成分片：`{status['completed_shards']} / {args.shard_count}`；"
        f"缺失：`{status['missing_rows']}`；hard reject："
        f"`{status['hard_rejected_rows']}`。",
        f"- QA 全通过：`{realized['qa_pass_rows']} / "
        f"{realized['rows']}`；training admitted："
        f"`{status['training_admitted_rows']}`。",
        f"- role ineligible 原因："
        f"`{json.dumps(realized['role_ineligible_reasons'], ensure_ascii=False)}`。",
        f"- hard reject 原因："
        f"`{json.dumps(snapshot['reject_reasons'], ensure_ascii=False)}`；"
        f"失败 gate："
        f"`{json.dumps(snapshot['reject_failure_labels'], ensure_ascii=False)}`。",
        "",
        "## QA 与目标实现",
        "",
        f"- 实际射击：`{realized['distributions'].get('actual_fire', {}).get('true', 0)}`；"
        f"含敌人：`{realized['distributions'].get('enemy_present', {}).get('true', 0)}`；"
        f"无敌人：`{realized['distributions'].get('enemy_present', {}).get('false', 0)}`。",
        f"- 大位移 + 大 yaw 联合覆盖："
        f"`{realized['joint_large_net_large_yaw']}`；"
        f"path ≥1000 / ≥2000：`{realized['path_length_ge_1000']} / "
        f"{realized['path_length_ge_2000']}`。",
    ]
    for key, item in realized["alignment"].items():
        rate = item["match_rate"]
        rate_text = "n/a" if rate is None else f"{100 * rate:.1f}%"
        lines.append(
            f"- `{key}` 目标命中：`{item['matched']} / "
            f"{item['compared']}`（{rate_text}）。"
        )
    lines.extend(["", "## 分布对比", ""])
    dimensions = [
        "dataset_role",
        "primary_bucket",
        "category",
        "enemy_present",
        "gametype",
        "map",
        "weapon",
        "fire_required",
        "route_present",
        "enemy_policy",
        "enemy_model",
        "enemy_color",
        "fire_weapon",
        "net_displacement_bin",
        "yaw_range_bin",
        "pitch_range_bin",
        "target_relation",
        "distance_bin",
    ]
    for dimension in dimensions:
        lines.extend(
            [
                markdown_table(
                    dimension,
                    full_distribution.get(dimension, {}),
                    selected_distribution.get(dimension, {}),
                    realized["distributions"].get(dimension, {}),
                ),
                "",
            ]
        )
    if realized["qa_failures"]:
        lines.extend(
            [
                "## QA failures",
                "",
                "```json",
                json.dumps(
                    realized["qa_failures"],
                    indent=2,
                    ensure_ascii=False,
                ),
                "```",
                "",
            ]
        )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    write_html(html_path, snapshot, episode_rows)

    print(
        json.dumps(
            {
                "status": status,
                "outputs": [
                    str(json_path),
                    str(csv_path),
                    str(markdown_path),
                    str(html_path),
                ],
                "thumbnail_errors": thumbnail_errors,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not thumbnail_errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
