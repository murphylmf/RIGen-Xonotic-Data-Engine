                      
"""Bounded four-policy Stage 1 enemy-motion preflight.

This split is review-only. It validates one deterministic example of each
named distractor policy and never authorizes formal Stage 1 collection.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              
import xonotic_stage1_production_preflight as production              
import xonotic_stage1_review as review              


SPLIT = "v2_stage1_enemy_policy_preflight_v2"
ROOT = capture.ROOT
PREFLIGHT_ROOT = ROOT / SPLIT
SCENARIOS_PATH = ROOT / f"configs/{SPLIT}_scenarios.jsonl"
CANDIDATES_PATH = PREFLIGHT_ROOT / "manifests/candidates.jsonl"
REJECTS_PATH = PREFLIGHT_ROOT / "manifests/rejects.jsonl"
AUDIT_PATH = PREFLIGHT_ROOT / "POLICY_PREFLIGHT_AUDIT.json"
REPORT_PATH = PREFLIGHT_ROOT / "POLICY_PREFLIGHT_REPORT.md"
PREVIEW_ROOT = ROOT / "previews/stage1_enemy_policy_preflight"
PROFILE_NAME = "trajectory_distribution"
REQUIRE_VISIBILITY = False
REQUIRE_ENEMY_AUDIO = False

POLICY_SOURCES = (
    ("idle", "s1review_034"),
    ("lateral_patrol", "s1review_021"),
    ("approach_retreat", "s1review_030"),
    ("stop_and_go", "s1review_032"),
)
MAX_POLICY_TICK_DISPLACEMENT = 4.0
MIN_STOP_AND_GO_STATIONARY_FRACTION = 0.15
MIN_PLAYER_ENEMY_CENTER_DISTANCE = 64.0
MIN_VISUAL_VISIBLE_FRACTION = 0.90
MIN_VISUAL_WITHIN_15_DEG_FRACTION = 0.50


def scenario_rows() -> list[dict[str, Any]]:
    source = {
        row["episode_id"]: row for row in review.build_scenarios()
    }
    rows: list[dict[str, Any]] = []
    for ordinal, (policy_name, source_id) in enumerate(
        POLICY_SOURCES, 1
    ):
        row = copy.deepcopy(source[source_id])
        if row["enemy_policy"]["name"] != policy_name:
            raise capture.CaptureFailure(
                "enemy_policy_source_drift",
                f"{source_id}:{row['enemy_policy']['name']}!={policy_name}",
            )
        old_id = row["episode_id"]
        episode_id = f"s1polpfv2_{ordinal:03d}"
        row.update(
            {
                "episode_id": episode_id,
                "source_episode_id": old_id,
                "source_split": row["split"],
                "split": SPLIT,
                "seed": 13_100_000 + ordinal,
                "training_stage": "stage1_enemy_policy_preflight_only",
                "acceptance_policy": capture.TIERED_REVIEW_POLICY,
                "fixed_variant_index": 0,
                "formal_collection_authorized": False,
                "human_review_required_before_training": True,
            }
        )
        row["anchor_id"] = str(row["anchor_id"]).replace(
            old_id, episode_id
        )
        policy_seed = 13_200_000 + ordinal
        row["enemy_policy"]["policy_seed"] = policy_seed
        row["enemy_policy"]["motion_start_tick"] = (
            0
            if policy_name == "idle"
            else policy_seed % capture.WARMUP_TICKS
        )
        row = review.apply_variant(row, 0)
        if not review.stage1_render_map_allowed(row["map"]):
            raise capture.CaptureFailure(
                "enemy_policy_map_excluded", row["map"]
            )
        rows.append(row)
    return rows


def command_generate(_: argparse.Namespace) -> int:
    rows = scenario_rows()
    if SCENARIOS_PATH.is_file():
        existing = capture.load_jsonl(SCENARIOS_PATH)
        if existing != rows:
            raise capture.CaptureFailure(
                "refuse_overwrite_enemy_policy_plan",
                str(SCENARIOS_PATH),
            )
    else:
        production.write_jsonl(SCENARIOS_PATH, rows)
    production.atomic_json(
        PREFLIGHT_ROOT / "SAMPLING_PLAN.json",
        {
            "schema_version": "xonotic-stage1-enemy-policy-plan-v2",
            "created_utc": capture.utc_now(),
            "split": SPLIT,
            "formal_collection_authorized": False,
            "count": len(rows),
            "policies": dict(
                Counter(
                    row["enemy_policy"]["name"] for row in rows
                )
            ),
            "maps": dict(Counter(row["map"] for row in rows)),
        },
    )
    print(str(SCENARIOS_PATH))
    return 0


def publish(
    row: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    stage = Path(result["stage"])
    package = stage / "package"
    qa = json.loads((package / "qa.json").read_text(encoding="utf-8"))
    attempt_id = result["attempt_id"]
    episode_destination = (
        PREFLIGHT_ROOT / "episodes" / row["episode_id"]
    )
    raw_destination = PREFLIGHT_ROOT / "raw" / attempt_id
    record = {
        "schema_version": "xonotic-stage1-enemy-policy-candidate-v2",
        "episode_id": row["episode_id"],
        "source_episode_id": row["source_episode_id"],
        "attempt_id": attempt_id,
        "split": SPLIT,
        "formal_collection_authorized": False,
        "map": row["map"],
        "weapon": row["weapon"],
        "enemy_model": row["enemy_model"],
        "enemy_policy": row["enemy_policy"],
        "training_admitted": False,
        "qa": {
            "hard_gates_pass": all(qa["hard_gates"].values()),
            "renderer": qa["runtime"]["renderer"],
            "frames": qa["video"]["frames"],
            "audio_samples": qa["audio"]["samples_per_channel"],
            "authoritative_sha256": qa["telemetry"][
                "authoritative_sha256"
            ],
            "enemy_policy": qa["enemy_policy"],
        },
        "captured_utc": capture.utc_now(),
    }
    production.atomic_json(package / "policy_candidate.json", record)
    (
        package_temporary,
        package_hashes,
        package_bytes,
        package_seconds,
    ) = production.stage_mapping_hashed_once(
        production.tree_files(package), episode_destination
    )
    raw_temporary, raw_hashes, raw_bytes, raw_seconds = (
        production.stage_mapping_hashed_once(
            production.raw_artifacts(stage), raw_destination
        )
    )
    os.rename(raw_temporary, raw_destination)
    os.rename(package_temporary, episode_destination)
    manifest = {
        **record,
        "episode_path": str(episode_destination),
        "raw_path": str(raw_destination),
        "package_sha256": package_hashes,
        "raw_sha256": raw_hashes,
        "publication": {
            "package_bytes": package_bytes,
            "raw_bytes": raw_bytes,
            "package_copy_seconds": package_seconds,
            "raw_copy_seconds": raw_seconds,
        },
        "published_utc": capture.utc_now(),
    }
    production.append_locked(
        CANDIDATES_PATH, manifest, unique_field="episode_id"
    )
    capture.clean_stage(stage)
    return manifest


def preserve_failure(
    row: dict[str, Any],
    retry: int,
    exc: Exception,
) -> None:
    attempt_id = f"{row['episode_id']}_a{retry + 1:02d}"
    stage = capture.TMP_ROOT / "raw" / attempt_id
    diagnostic = PREFLIGHT_ROOT / "diagnostics" / attempt_id
    hashes: dict[str, str] = {}
    if stage.is_dir() and not diagnostic.exists():
        files = production.diagnostic_files(stage)
        if files:
            temporary, hashes, _, _ = (
                production.stage_mapping_hashed_once(
                    files, diagnostic
                )
            )
            os.rename(temporary, diagnostic)
    production.append_locked(
        REJECTS_PATH,
        {
            "schema_version": "xonotic-stage1-enemy-policy-reject-v2",
            "episode_id": row["episode_id"],
            "attempt_id": attempt_id,
            "reason": (
                exc.reason
                if isinstance(exc, capture.CaptureFailure)
                else type(exc).__name__
            ),
            "detail": (
                exc.detail
                if isinstance(exc, capture.CaptureFailure)
                else str(exc)
            ),
            "diagnostic_path": (
                str(diagnostic) if diagnostic.exists() else None
            ),
            "diagnostic_sha256": hashes,
            "created_utc": capture.utc_now(),
        },
    )
    if stage.is_dir():
        capture.clean_stage(stage)


def command_collect(args: argparse.Namespace) -> int:
    capture.require_conda()
    if not SCENARIOS_PATH.is_file():
        command_generate(args)
    requested = set(args.episode_id or [])
    planned_ids = {
        row["episode_id"]
        for row in capture.load_jsonl(SCENARIOS_PATH)
    }
    unknown = requested - planned_ids
    if unknown:
        raise capture.CaptureFailure(
            "enemy_policy_episode_not_planned",
            capture.canonical_json(sorted(unknown)),
        )
    completed = {
        row["episode_id"]
        for row in capture.load_jsonl(CANDIDATES_PATH)
    }
    prior_rejects = Counter(
        row["episode_id"]
        for row in capture.load_jsonl(REJECTS_PATH)
    )
    rows = [
        row
        for row in capture.load_jsonl(SCENARIOS_PATH)
        if row["episode_id"] not in completed
        and (not requested or row["episode_id"] in requested)
    ]
    for row in rows:
        accepted = False
        for attempt_offset in range(args.max_attempts):
            retry = prior_rejects[row["episode_id"]] + attempt_offset
            try:
                print(
                    f"capture {row['episode_id']} "
                    f"{row['enemy_policy']['name']}",
                    flush=True,
                )
                result = capture.execute_attempt(
                    row, retry=retry, publish=False
                )
                publish(row, result)
                accepted = True
                break
            except Exception as exc:
                preserve_failure(row, retry, exc)
                print(
                    f"reject {row['episode_id']} retry={retry} "
                    f"{type(exc).__name__}:{exc}",
                    flush=True,
                )
        if not accepted:
            raise capture.CaptureFailure(
                "enemy_policy_preflight_exhausted", row["episode_id"]
            )
    return 0 if requested else command_audit(args)


def candidate_motion(row: dict[str, Any]) -> dict[str, Any]:
    package = Path(row["episode_path"])
    states = pd.read_parquet(package / "states.parquet")
    all_origins = np.stack(
        states["enemy.origin"].map(
            lambda value: np.asarray(value, dtype=np.float64)
        )
    )
    output = states[
        (states["server_tick"] >= capture.WARMUP_TICKS)
        & (states["server_tick"] < capture.TOTAL_TICKS)
    ]
    origins = np.stack(
        output["enemy.origin"].map(
            lambda value: np.asarray(value, dtype=np.float64)
        )
    )
    player_origins = np.stack(
        output["post.origin"].map(
            lambda value: np.asarray(value, dtype=np.float64)
        )
    )
    displacement = np.linalg.norm(origins - origins[0], axis=1)
    tick_displacement = np.linalg.norm(
        np.diff(all_origins, axis=0), axis=1
    )
    relation = v2.target_relation_table(package, enemy_present=True)
    return {
        "max_displacement_from_output_start": float(
            displacement.max()
        ),
        "net_displacement": float(
            np.linalg.norm(origins[-1] - origins[0])
        ),
        "max_tick_displacement": float(tick_displacement.max()),
        "stationary_tick_fraction": float(
            np.mean(tick_displacement <= 0.01)
        ),
        "minimum_player_enemy_distance": float(
            np.linalg.norm(origins - player_origins, axis=1).min()
        ),
        "visible_fraction": float(
            relation["render_visible_proxy"].mean()
        ),
        "within_15_deg_fraction": float(
            (relation["angular_error_deg"] <= 15.0).mean()
        ),
    }


def policy_motion_failures(
    policy_name: str,
    metrics: dict[str, Any],
    require_visibility: bool = False,
) -> list[str]:
    failures: list[str] = []
    moving = policy_name != "idle"
    if moving == (
        metrics["max_displacement_from_output_start"] < 1.0
    ):
        failures.append("motion_realization")
    if (
        metrics["max_tick_displacement"]
        > MAX_POLICY_TICK_DISPLACEMENT
    ):
        failures.append("position_discontinuity")
    if (
        policy_name == "stop_and_go"
        and metrics["stationary_tick_fraction"]
        < MIN_STOP_AND_GO_STATIONARY_FRACTION
    ):
        failures.append("stop_phase_missing")
    if (
        metrics["minimum_player_enemy_distance"]
        < MIN_PLAYER_ENEMY_CENTER_DISTANCE
    ):
        failures.append("player_enemy_contact_risk")
    if (
        require_visibility
        and metrics["visible_fraction"]
        < MIN_VISUAL_VISIBLE_FRACTION
    ):
        failures.append("visual_review_visibility")
    if (
        require_visibility
        and metrics["within_15_deg_fraction"]
        < MIN_VISUAL_WITHIN_15_DEG_FRACTION
    ):
        failures.append("visual_review_center_proximity")
    return failures


def command_audit(_: argparse.Namespace) -> int:
    rows = capture.load_jsonl(CANDIDATES_PATH)
    failures: list[str] = []
    hashes_checked = 0
    motion: dict[str, dict[str, Any]] = {}
    enemy_motion_audio: dict[str, dict[str, Any]] = {}
    source_commits: set[str] = set()
    expected_source_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    if len(rows) != len(POLICY_SOURCES):
        failures.append(f"candidate_count:{len(rows)}")
    if Counter(
        row["enemy_policy"]["name"] for row in rows
    ) != Counter(name for name, _ in POLICY_SOURCES):
        failures.append("policy_coverage")
    for row in rows:
        if not row["qa"]["hard_gates_pass"]:
            failures.append(f"{row['episode_id']}:hard_qa")
        logged = row["qa"]["enemy_policy"]["authoritative_log"]
        if logged.get("policy") != row["enemy_policy"]["name"]:
            failures.append(f"{row['episode_id']}:policy_log")
        episode = json.loads(
            (Path(row["episode_path"]) / "episode.json").read_text(
                encoding="utf-8"
            )
        )
        source_commit = str(episode.get("source_commit", ""))
        source_commits.add(source_commit)
        if source_commit != expected_source_commit:
            failures.append(f"{row['episode_id']}:source_commit")
        enemy_entity = int(
            episode["pair_candidates"][0]["reset"]["enemy_entity"]
        )
        audio_events = pd.read_parquet(
            Path(row["episode_path"]) / "audio_events.parquet"
        )
        from_enemy = audio_events[
            (audio_events["source_entity"] == enemy_entity)
            & audio_events["sample_name"].fillna("").str.contains(
                r"(?:^|/)(?:metal)?footstep0[1-6]\.wav$",
                regex=True,
            )
        ]
        qa_payload = json.loads(
            (Path(row["episode_path"]) / "qa.json").read_text(
                encoding="utf-8"
            )
        )
        movement_audio = qa_payload["audio"]["enemy_movement"]
        enemy_motion_audio[row["episode_id"]] = {
            "enemy_entity": enemy_entity,
            "event_count": int(len(from_enemy)),
            "sample_names": sorted(
                str(value)
                for value in from_enemy["sample_name"].unique()
            ),
            "authoritative_event_count_output": movement_audio[
                "authoritative_event_count_output"
            ],
            "mixer_matched_count": movement_audio[
                "mixer_matched_count"
            ],
            "waveform_onset_matched_count": movement_audio[
                "waveform_onset_matched_count"
            ],
            "event_mixer_linkage_rate": movement_audio[
                "event_mixer_linkage_rate"
            ],
            "event_waveform_linkage_rate": movement_audio[
                "event_waveform_linkage_rate"
            ],
            "max_waveform_onset_error_ms": movement_audio[
                "max_waveform_onset_error_ms"
            ],
        }
        moving = row["enemy_policy"]["name"] != "idle"
        if REQUIRE_ENEMY_AUDIO and moving:
            if (
                movement_audio["authoritative_event_count_output"] <= 0
                or movement_audio["event_mixer_linkage_rate"] < 0.999
                or movement_audio["event_waveform_linkage_rate"] < 0.999
                or movement_audio["max_waveform_onset_error_ms"] > 2.0
            ):
                failures.append(
                    f"{row['episode_id']}:enemy_movement_audio"
                )
        if (
            REQUIRE_ENEMY_AUDIO
            and not moving
            and (
                movement_audio["authoritative_event_count_total"] != 0
                or movement_audio["mixer_event_count_output"] != 0
            )
        ):
            failures.append(
                f"{row['episode_id']}:idle_enemy_footstep"
            )
        for root_key, hash_key in (
            ("episode_path", "package_sha256"),
            ("raw_path", "raw_sha256"),
        ):
            root = Path(row[root_key])
            for relative, expected in row[hash_key].items():
                hashes_checked += 1
                path = root / relative
                if (
                    not path.is_file()
                    or capture.sha256_file(path) != expected
                ):
                    failures.append(
                        f"{row['episode_id']}:{root_key}:{relative}"
                    )
        metrics = candidate_motion(row)
        motion[row["episode_id"]] = metrics
        for failure in policy_motion_failures(
            row["enemy_policy"]["name"],
            metrics,
            require_visibility=REQUIRE_VISIBILITY,
        ):
            failures.append(f"{row['episode_id']}:{failure}")
    moving_without_audio = [
        row["episode_id"]
        for row in rows
        if row["enemy_policy"]["name"] != "idle"
        and enemy_motion_audio[row["episode_id"]]["event_count"] == 0
    ]
    formal_blockers = [
        "whole_path_enemy_hull_trace_not_instrumented"
    ]
    if moving_without_audio:
        formal_blockers.append(
            "moving_enemy_audio_not_observed"
        )
    audit = {
        "schema_version": "xonotic-stage1-enemy-policy-audit-v2",
        "created_utc": capture.utc_now(),
        "profile": PROFILE_NAME,
        "passed": not failures,
        "candidate_count": len(rows),
        "policy_counts": dict(
            Counter(row["enemy_policy"]["name"] for row in rows)
        ),
        "hashes_checked": hashes_checked,
        "source_commits": sorted(source_commits),
        "motion": motion,
        "enemy_motion_audio": enemy_motion_audio,
        "moving_policies_without_enemy_audio": moving_without_audio,
        "formal_collection_blockers": formal_blockers,
        "reject_attempts": len(capture.load_jsonl(REJECTS_PATH)),
        "failures": failures,
    }
    production.atomic_json(AUDIT_PATH, audit)
    if failures:
        raise capture.CaptureFailure(
            "enemy_policy_audit_failed",
            capture.canonical_json(failures),
        )
    print(capture.canonical_json(audit))
    return 0


def command_html(_: argparse.Namespace) -> int:
    rows = sorted(
        capture.load_jsonl(CANDIDATES_PATH),
        key=lambda row: row["episode_id"],
    )
    media = PREVIEW_ROOT / "media"
    media.mkdir(parents=True, exist_ok=True)
    cards = []
    for row in rows:
        destination = media / f"{row['episode_id']}.mp4"
        if not destination.is_file():
            temporary = media / f".{row['episode_id']}.tmp.mp4"
            completed = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-i",
                    str(Path(row["episode_path"]) / "video.mkv"),
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    "-movflags",
                    "+faststart",
                    str(temporary),
                ],
                check=False,
            )
            if completed.returncode:
                raise capture.CaptureFailure(
                    "enemy_policy_preview_failed", row["episode_id"]
                )
            os.replace(temporary, destination)
        metrics = candidate_motion(row)
        qa_payload = json.loads(
            (Path(row["episode_path"]) / "qa.json").read_text(
                encoding="utf-8"
            )
        )
        enemy_audio = qa_payload["audio"]["enemy_movement"]
        cards.append(
            "<article><video controls playsinline preload=\"metadata\" "
            f"src=\"media/{row['episode_id']}.mp4\"></video>"
            f"<h2>{row['episode_id']} · "
            f"{row['enemy_policy']['name']} · "
            f"{row.get('audio_review_context', PROFILE_NAME)}</h2>"
            f"<p>{row['map']} · {row['weapon']} · "
            f"start tick {row['enemy_policy']['motion_start_tick']} · "
            f"amplitude {row['enemy_policy']['motion_amplitude_units']}u · "
            f"realized max {metrics['max_displacement_from_output_start']:.1f}u · "
            f"max/tick {metrics['max_tick_displacement']:.2f}u · "
            f"visible {metrics['visible_fraction']:.1%} · "
            f"within 15° {metrics['within_15_deg_fraction']:.1%} · "
            f"enemy footsteps "
            f"{enemy_audio['authoritative_event_count_output']} · "
            f"mixer link "
            f"{enemy_audio['event_mixer_linkage_rate']:.1%} · "
            f"onset link "
            f"{enemy_audio['event_waveform_linkage_rate']:.1%}"
            "</p>"
            f"<p><a href=\"media/{row['episode_id']}.mp4\" download>"
            "下载浏览器版 MP4</a></p></article>"
        )
    contexts = {
        row.get("audio_review_context") for row in rows
        if row.get("audio_review_context")
    }
    if contexts == {"distribution", "visible_close"}:
        profile_note = (
            "每种 policy 各有一条分布型样本和一条近距离可见样本；"
            "后者只用于人工听看，不代表训练时的敌人屏幕位置分布。"
        )
    elif REQUIRE_VISIBILITY:
        profile_note = (
            "这些样本故意使用固定、非反应式相机并过采样近中心敌人，"
            "仅用于人工看清 policy；不得作为 Stage 1 敌人屏幕位置分布。"
        )
    else:
        profile_note = (
            "这些样本用于轨迹与反耦合验证，包含离屏样本，不保证每条"
            "都适合肉眼观察敌人运动。"
        )
    document = f"""<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Stage 1 Enemy Policy Preflight</title><style>
body{{background:#091018;color:#eaf2fb;font-family:system-ui;margin:20px}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}}
article{{background:#121d2a;border:1px solid #33485d;border-radius:10px;overflow:hidden;padding-bottom:10px}}
video{{width:100%;aspect-ratio:16/9;background:#000}}h2,p{{margin:10px 14px}}
a{{color:#74c7ff}}
</style></head><body><h1>Stage 1 简单敌人 Policy Preflight</h1>
<p>Profile: {PROFILE_NAME}。{len(rows)} 条均为 review-only；policy 不读取相机、准星或实时玩家状态。</p>
<p>{profile_note}</p>
<p>请打开播放器音量；移动 policy 的脚步来自敌人实体，idle 不应有敌人脚步。</p>
<main>{''.join(cards)}</main></body></html>"""
    production.atomic_text(PREVIEW_ROOT / "index.html", document)
    print(str(PREVIEW_ROOT / "index.html"))
    return 0


def command_report(_: argparse.Namespace) -> int:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    candidates = sorted(
        capture.load_jsonl(CANDIDATES_PATH),
        key=lambda row: row["episode_id"],
    )
    rejects = capture.load_jsonl(REJECTS_PATH)
    table_rows: list[str] = []
    total_enemy_steps = 0
    total_mixer_matches = 0
    total_onset_matches = 0
    max_onset_error_ms = 0.0
    for row in candidates:
        qa = json.loads(
            (Path(row["episode_path"]) / "qa.json").read_text(
                encoding="utf-8"
            )
        )
        episode = json.loads(
            (Path(row["episode_path"]) / "episode.json").read_text(
                encoding="utf-8"
            )
        )
        enemy_audio = qa["audio"]["enemy_movement"]
        total_enemy_steps += int(
            enemy_audio["authoritative_event_count_output"]
        )
        total_mixer_matches += int(
            enemy_audio["mixer_matched_count"]
        )
        total_onset_matches += int(
            enemy_audio["waveform_onset_matched_count"]
        )
        max_onset_error_ms = max(
            max_onset_error_ms,
            float(qa["audio"]["max_onset_error_ms"]),
        )
        motion = audit["motion"][row["episode_id"]]
        table_rows.append(
            f"| `{row['episode_id']}` | "
            f"`{episode.get('audio_review_context', PROFILE_NAME)}` | "
            f"`{row['map']}` | `{row['enemy_policy']['name']}` | "
            f"{motion['minimum_player_enemy_distance']:.1f} | "
            f"{enemy_audio['authoritative_event_count_output']} | "
            f"{enemy_audio['event_mixer_linkage_rate']:.3f} | "
            f"{enemy_audio['event_waveform_linkage_rate']:.3f} |"
        )
    reject_reasons = dict(
        Counter(str(row["reason"]) for row in rejects)
    )
    interrupted_root = PREFLIGHT_ROOT / "interrupted"
    interrupted_attempts = sorted(
        path.name
        for path in interrupted_root.glob("*")
        if path.is_dir()
    )
    text = f"""# Stage 1 Enemy Policy Preflight

Updated: `{audit['created_utc']}`

- Formal collection authorized: **no**
- Profile: `{audit['profile']}`
- Centered visual-review oversample: `{REQUIRE_VISIBILITY}`
- Enemy movement audio required: `{REQUIRE_ENEMY_AUDIO}`
- Passed: `{audit['passed']}`
- Candidates: `{audit['candidate_count']}`
- Policy counts: `{json.dumps(audit['policy_counts'], sort_keys=True)}`
- Rejected attempts: `{audit['reject_attempts']}`
- Rejection reasons: `{json.dumps(reject_reasons, sort_keys=True)}`
- Interrupted attempts retained outside the reject manifest: `{json.dumps(interrupted_attempts)}`
- Artifact hashes checked: `{audit['hashes_checked']}`
- Source commits: `{json.dumps(audit['source_commits'])}`
- Maximum realized one-tick displacement: `{max(row['max_tick_displacement'] for row in audit['motion'].values()):.6f}u`
- Stop-and-go stationary-tick fraction: `{next(row['stationary_tick_fraction'] for episode_id, row in audit['motion'].items() if episode_id.endswith('004')):.6f}`
- Minimum visible fraction: `{min(row['visible_fraction'] for row in audit['motion'].values()):.6f}`
- Minimum within-15-degree fraction: `{min(row['within_15_deg_fraction'] for row in audit['motion'].values()):.6f}`
- Moving policies without enemy-source audio: `{json.dumps(audit['moving_policies_without_enemy_audio'])}`
- Output-window enemy footsteps: `{total_enemy_steps}`
- Enemy footsteps linked to mixer: `{total_mixer_matches}/{total_enemy_steps}`
- Enemy footsteps linked to waveform onset: `{total_onset_matches}/{total_enemy_steps}`
- Maximum mixer-to-waveform onset error across each episode: `{max_onset_error_ms:.6f} ms`
- Formal blockers: `{json.dumps(audit['formal_collection_blockers'])}`
- Active build: `{capture.build_root().name}`
- HTML: `{PREVIEW_ROOT / 'index.html'}`
- Audit: `{AUDIT_PATH}`

| Episode | Review context | Map | Policy | Min distance (u) | Enemy steps | Mixer link | Waveform link |
|---|---|---|---|---:|---:|---:|---:|
{chr(10).join(table_rows)}

All policies are deterministic and fixed before replay. They do not read the
camera, crosshair, player view actions, or live player state, and never fire or
jump. This bounded preflight does not authorize formal Stage 1 collection.
Enemy footsteps, when required by this profile, are linked from authoritative
server events through enemy-entity mixer events to measured waveform onsets.
Every accepted episode contains exactly 320 frames and 240,000 samples per
channel. Browser MP4 files are review derivatives; canonical packages retain
the required H.264 High plus FLAC MKV, and all raw captures remain under the
split's `raw/` directory.
Rejected attempts and their diagnostics are retained under the split and are
never counted as accepted candidates.
Whole-trajectory hull tracing remains a separate formal-collection blocker.
"""
    production.atomic_text(REPORT_PATH, text)
    print(str(REPORT_PATH))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.set_defaults(func=command_generate)
    collect = commands.add_parser("collect")
    collect.add_argument("--max-attempts", type=int, default=2)
    collect.add_argument(
        "--episode-id",
        action="append",
        help="collect only this planned episode; may be repeated",
    )
    collect.set_defaults(func=command_collect)
    audit = commands.add_parser("audit")
    audit.set_defaults(func=command_audit)
    html_parser = commands.add_parser("html")
    html_parser.set_defaults(func=command_html)
    report = commands.add_parser("report")
    report.set_defaults(func=command_report)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
