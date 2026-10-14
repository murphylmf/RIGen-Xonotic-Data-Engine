                      
"""Build an evidence-backed snapshot of the currently collected Xonotic data.

The dashboard intentionally separates:
  * immutable legacy/bounded evidence;
  * the current Stage-1 production-preflight selection pool;
  * the latest enemy-policy/audio review batch; and
  * future formal collection targets.

It never treats a preflight candidate as formally admitted training data.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT_DEFAULT = Path("./xonotic_capture")
MAP_MODE_FALLBACK_RE = re.compile(
    r"can't play the selected map in the given game mode "
    r"\(([^)]+)\)\. Falling back to a supported mode \(([^)]+)\)\."
)

STAGE1_TARGETS = {
    "roles": {
        "foundation_no_enemy": 75.0,
        "foundation_enemy_distractor": 25.0,
    },
    "buckets": {
        "node_atomic": 26000 / 600,
        "mixed_action": 20000 / 600,
        "high_motion_special": 8000 / 600,
        "weapon_environment": 6000 / 600,
    },
    "net_displacement": {
        "lt64": 15.0,
        "64_256": 20.0,
        "256_512": 25.0,
        "512_1024": 25.0,
        "gt1024": 15.0,
    },
    "yaw_range": {
        "lt15": 30.0,
        "15_45": 25.0,
        "45_90": 15.0,
        "90_180": 20.0,
        "ge180": 10.0,
    },
    "pitch_range": {
        "lt5": 45.0,
        "5_15": 25.0,
        "15_30": 20.0,
        "ge30": 10.0,
    },
    "enemy_relation": {
        "offscreen_or_occluded": 25.0,
        "visible_far": 30.0,
        "near_crosshair": 20.0,
        "brief_center_pass": 15.0,
        "center_linger": 7.0,
        "nearly_continuous_center": 3.0,
    },
    "enemy_distance": {
        "close": 25.0,
        "near": 30.0,
        "medium": 25.0,
        "far": 12.0,
        "very_far": 6.0,
        "extreme": 2.0,
    },
}

STAGE2_TARGETS = {
    "aim_policy": {
        "visible_no_response": {"count": 6000, "percent": 15.0},
        "delayed_acquisition": {"count": 8000, "percent": 20.0},
        "pass_over_offset_or_no_fire": {"count": 8000, "percent": 20.0},
        "track_lose_reacquire": {"count": 8000, "percent": 20.0},
        "sustained_tracking": {"count": 10000, "percent": 25.0},
    },
    "outcome": {
        "no_fire": {"count": 6000, "percent": 15.0},
        "miss": {"count": 10000, "percent": 25.0},
        "hit_survive": {"count": 14000, "percent": 35.0},
        "kill": {"count": 10000, "percent": 25.0},
    },
    "distance": {
        key: {"count": round(40000 * pct / 100), "percent": pct}
        for key, pct in STAGE1_TARGETS["enemy_distance"].items()
    },
}

LABELS = {
    "foundation_no_enemy": "无敌人基础动力学",
    "foundation_enemy_distractor": "含敌人 distractor 动力学",
    "causal_interaction": "因果交互",
    "node_atomic": "原子 / node action",
    "mixed_action": "路线 / action 组合",
    "high_motion_special": "大运动 / 特殊 traversal",
    "weapon_environment": "武器状态 / 环境交互",
    "lt64": "<64",
    "64_256": "64–256",
    "256_512": "256–512",
    "512_1024": "512–1024",
    "gt1024": ">1024",
    "lt15": "<15°",
    "15_45": "15–45°",
    "45_90": "45–90°",
    "90_180": "90–180°",
    "ge180": "≥180°",
    "lt5": "<5°",
    "5_15": "5–15°",
    "15_30": "15–30°",
    "ge30": "≥30°",
    "offscreen_or_occluded": "不在画面 / 完全遮挡",
    "visible_far": "可见、远离准星",
    "near_crosshair": "准星附近",
    "brief_center_pass": "短暂过中心",
    "center_linger": "中心停留",
    "nearly_continuous_center": "近乎持续居中",
    "contact_lt64": "接触边界 <64（taxonomy edge）",
    "close": "close 64–256",
    "near": "near 256–512",
    "medium": "medium 512–768",
    "far": "far 768–1024",
    "very_far": "very far 1024–1536",
    "extreme": "extreme >1536",
    "auto_keep_candidate": "自动保留候选",
    "needs_review": "待人工 review",
    "training_excluded": "训练排除",
    "hard_invalidated": "硬失效",
    "idle": "静止",
    "lateral_patrol": "横移巡逻",
    "approach_retreat": "接近 / 远离",
    "stop_and_go": "走停交替",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_number}: {exc}") from exc
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def counts(
    rows: Iterable[dict[str, Any]],
    getter: Callable[[dict[str, Any]], Any],
    *,
    omit_empty: bool = True,
) -> dict[str, int]:
    result: Counter[str] = Counter()
    for row in rows:
        value = getter(row)
        if value is None or value == "":
            if omit_empty:
                continue
            value = "null"
        if isinstance(value, bool):
            value = str(value).lower()
        result[str(value)] += 1
    return dict(sorted(result.items(), key=lambda item: (-item[1], item[0])))


def distance_bin(distance: float) -> str:
    if distance < 64:
        return "contact_lt64"
    if distance <= 256:
        return "close"
    if distance <= 512:
        return "near"
    if distance <= 768:
        return "medium"
    if distance <= 1024:
        return "far"
    if distance <= 1536:
        return "very_far"
    return "extreme"


def realized_gametype_from_legacy_log(
    console: str, requested: str
) -> tuple[str, list[dict[str, str]]]:
    fallbacks = [
        {"requested": source, "realized": destination}
        for source, destination in MAP_MODE_FALLBACK_RE.findall(console)
    ]
    realized = fallbacks[-1]["realized"] if fallbacks else requested
    return realized.lower(), fallbacks


def human_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def derive_snapshot(root: Path) -> dict[str, Any]:
    spec_path = root / "XONOTIC_DATA_SPEC_V2.md"
    prod_dir = root / "v2_stage1_production_preflight"
    prod_candidates_path = prod_dir / "manifests/candidates.jsonl"
    prod_annotations_path = prod_dir / "manifests/posthoc_annotations.jsonl"
    prod_summary_path = prod_dir / "PREFLIGHT_SUMMARY.json"
    prod_audit_path = prod_dir / "AUDIT.json"
    prod_hard_rejects_path = prod_dir / "manifests/hard_rejects.jsonl"
    policy_dir = root / "v2_stage1_enemy_policy_audio_preflight_v2"
    policy_candidates_path = policy_dir / "manifests/candidates.jsonl"
    policy_audit_path = policy_dir / "POLICY_PREFLIGHT_AUDIT.json"
    policy_scenarios_path = (
        root
        / "configs/v2_stage1_enemy_policy_audio_preflight_v2_scenarios.jsonl"
    )

    source_paths = [
        spec_path,
        prod_candidates_path,
        prod_annotations_path,
        prod_summary_path,
        prod_audit_path,
        prod_hard_rejects_path,
        policy_candidates_path,
        policy_audit_path,
        policy_scenarios_path,
        root / "manifests/accepted.jsonl",
        root / "v2_coverage_pilot/manifests/accepted.jsonl",
        root / "v2_motion_distance_pilot/manifests/accepted.jsonl",
        root / "v2_stage1_review_fov90/manifests/accepted.jsonl",
    ]
    missing = [str(path) for path in source_paths if not path.exists()]
    if missing:
        raise RuntimeError(f"missing required evidence: {missing}")

    prod_candidates = load_jsonl(prod_candidates_path)
    annotations = {
        row["episode_id"]: row for row in load_jsonl(prod_annotations_path)
    }
    prod_summary = load_json(prod_summary_path)
    prod_audit = load_json(prod_audit_path)
    hard_rejects = load_jsonl(prod_hard_rejects_path)

    production_rows: list[dict[str, Any]] = []
    for candidate in prod_candidates:
        episode_id = candidate["episode_id"]
        annotation = annotations.get(episode_id)
        if annotation is None:
            raise RuntimeError(f"missing post-hoc annotation for {episode_id}")
        episode_path = Path(candidate["episode_path"])
        raw_path = Path(candidate["raw_path"])
        episode_metadata = load_json(episode_path / "episode.json")
        server_console_path = raw_path / "server_console.log"
        render_console_path = raw_path / "client_render_console.log"
        server_console = server_console_path.read_text(
            encoding="utf-8", errors="replace"
        )
        realized_gametype, mode_fallbacks = (
            realized_gametype_from_legacy_log(
                server_console,
                str(episode_metadata.get("gametype", "dm")),
            )
        )
        ctf_waypoint_hud_contaminated = realized_gametype == "ctf"
        hard_invalidation_reasons = list(
            annotation.get("hard_invalidation_reasons", [])
        )
        if ctf_waypoint_hud_contaminated:
            hard_invalidation_reasons.append(
                "hud:legacy_ctf_flag_waypoint_policy"
            )
        if annotation["hard_invalidated"] or ctf_waypoint_hud_contaminated:
            disposition = "hard_invalidated"
        elif annotation["training_excluded"]:
            disposition = "training_excluded"
        else:
            disposition = candidate["status"]
        production_rows.append(
            {
                "episode_id": episode_id,
                "map": candidate["map"],
                "weapon": candidate["weapon"],
                "role": candidate["dataset_role"],
                "bucket": candidate["primary_bucket"],
                "category": candidate["category"],
                "enemy_present": bool(candidate["enemy_present"]),
                "enemy_model": candidate["enemy_model"] or None,
                "enemy_skin": (
                    candidate["enemy_skin"] if candidate["enemy_present"] else None
                ),
                "target_relation": candidate["realized_labels"].get(
                    "target_relation"
                ),
                "distance_bin": candidate["realized_labels"].get("distance_bin"),
                "net_displacement_bin": candidate["motion"][
                    "net_displacement_bin"
                ],
                "net_displacement": candidate["motion"]["net_displacement_3d"],
                "path_length": candidate["motion"]["path_length_3d"],
                "yaw_range_bin": candidate["motion"]["yaw_range_bin"],
                "yaw_range_deg": candidate["motion"]["yaw_range_deg"],
                "pitch_range_bin": candidate["motion"]["pitch_range_bin"],
                "pitch_range_deg": candidate["motion"]["pitch_range_deg"],
                "disposition": disposition,
                "selection_eligible": disposition
                in {"auto_keep_candidate", "needs_review"},
                "soft_flag_codes": [
                    flag["code"] for flag in candidate.get("soft_flags", [])
                ]
                + annotation.get("soft_flag_codes", []),
                "hard_invalidation_reasons": hard_invalidation_reasons,
                "training_exclusion_reasons": annotation.get(
                    "training_exclusion_reasons", []
                ),
                "blocked_seconds": annotation["movement_blockage"][
                    "longest_blocked_seconds"
                ],
                "video_url": (
                    f"../stage1_production_preflight/media/{episode_id}.mp4"
                ),
                "episode_path": candidate["episode_path"],
                "requested_gametype": str(
                    episode_metadata.get("gametype", "dm")
                ).lower(),
                "realized_gametype": realized_gametype,
                "mode_fallbacks": mode_fallbacks,
                "waypoint_hud_contract": "legacy_unverified",
                "ctf_waypoint_hud_contaminated": (
                    ctf_waypoint_hud_contaminated
                ),
                "server_console_sha256": sha256(server_console_path),
                "render_console_sha256": sha256(render_console_path),
            }
        )

    eligible = [row for row in production_rows if row["selection_eligible"]]
    enemy_eligible = [row for row in eligible if row["enemy_present"]]

    def dist(field: str, rows: list[dict[str, Any]] = eligible) -> dict[str, int]:
        return counts(rows, lambda row: row.get(field))

    production = {
        "funnel": {
            "manifest_candidates": len(production_rows),
            "capture_valid": sum(
                row["disposition"] != "hard_invalidated" for row in production_rows
            ),
            "selection_eligible": len(eligible),
            "auto_keep_candidate": sum(
                row["disposition"] == "auto_keep_candidate" for row in production_rows
            ),
            "needs_review": sum(
                row["disposition"] == "needs_review" for row in production_rows
            ),
            "training_excluded": sum(
                row["disposition"] == "training_excluded" for row in production_rows
            ),
            "hard_invalidated": sum(
                row["disposition"] == "hard_invalidated" for row in production_rows
            ),
            "formal_training_admitted": 0,
        },
        "selection_pool": {
            "count": len(eligible),
            "duration_seconds": len(eligible) * 5,
            "roles": dist("role"),
            "buckets": dist("bucket"),
            "categories": dist("category"),
            "maps": dist("map"),
            "weapons": dist("weapon"),
            "net_displacement": dist("net_displacement_bin"),
            "yaw_range": dist("yaw_range_bin"),
            "pitch_range": dist("pitch_range_bin"),
            "enemy_relation": dist("target_relation", enemy_eligible),
            "enemy_distance": dist("distance_bin", enemy_eligible),
            "enemy_models": dist("enemy_model", enemy_eligible),
            "enemy_appearances": counts(
                enemy_eligible,
                lambda row: f"{row['enemy_model']}/skin{row['enemy_skin']}",
            ),
            "path_ge_1000": sum(row["path_length"] >= 1000 for row in eligible),
            "path_ge_2000": sum(row["path_length"] >= 2000 for row in eligible),
            "joint_net_ge512_yaw_ge90": sum(
                row["net_displacement_bin"] in {"512_1024", "gt1024"}
                and row["yaw_range_bin"] in {"90_180", "ge180"}
                for row in eligible
            ),
            "unique_maps": len({row["map"] for row in eligible}),
            "unique_weapons": len({row["weapon"] for row in eligible}),
            "unique_enemy_models": len(
                {row["enemy_model"] for row in enemy_eligible}
            ),
            "unique_enemy_appearances": len(
                {(row["enemy_model"], row["enemy_skin"]) for row in enemy_eligible}
            ),
        },
        "soft_flags": prod_summary["soft_flag_counts"],
        "hard_reject_attempts": len(hard_rejects),
        "terminal_hard_reject_attempts": sum(
            bool(row.get("terminal")) for row in hard_rejects
        ),
        "confirmed_rule_rejection_rate": prod_audit[
            "confirmed_rule_rejection_rate"
        ],
        "mode_hud_audit": {
            "policy": (
                "realized CTF under the legacy client policy is hard-invalid: "
                "cl_hidewaypoints=2 was not enforced and the server created "
                "flag-base waypoint sprites"
            ),
            "legacy_rows_checked": len(production_rows),
            "fallback_rows": sum(
                bool(row["mode_fallbacks"]) for row in production_rows
            ),
            "realized_gametypes": counts(
                production_rows,
                lambda row: row["realized_gametype"],
            ),
            "ctf_contaminated_count": sum(
                row["ctf_waypoint_hud_contaminated"]
                for row in production_rows
            ),
            "ctf_contaminated_episode_ids": [
                row["episode_id"]
                for row in production_rows
                if row["ctf_waypoint_hud_contaminated"]
            ],
            "rows": [
                {
                    "episode_id": row["episode_id"],
                    "map": row["map"],
                    "requested_gametype": row[
                        "requested_gametype"
                    ],
                    "realized_gametype": row["realized_gametype"],
                    "fallbacks": row["mode_fallbacks"],
                    "ctf_waypoint_hud_contaminated": row[
                        "ctf_waypoint_hud_contaminated"
                    ],
                    "server_console_sha256": row[
                        "server_console_sha256"
                    ],
                    "render_console_sha256": row[
                        "render_console_sha256"
                    ],
                }
                for row in production_rows
            ],
            "corrected_contract": {
                "client_cl_hidewaypoints": 2,
                "client_hud_panel_modicons": 0,
                "server_g_ctf_flag_waypoint": 0,
                "mode_fallback_forbidden": True,
            },
        },
        "rows": production_rows,
    }

    policy_candidates = load_jsonl(policy_candidates_path)
    policy_audit = load_json(policy_audit_path)
    policy_scenarios = {
        row["episode_id"]: row for row in load_jsonl(policy_scenarios_path)
    }
    policy_rows: list[dict[str, Any]] = []
    for candidate in policy_candidates:
        episode_id = candidate["episode_id"]
        scenario = policy_scenarios[episode_id]
        motion = policy_audit["motion"][episode_id]
        audio = policy_audit["enemy_motion_audio"][episode_id]
        visible_fraction = motion["visible_fraction"]
        if visible_fraction == 0:
            visibility_class = "offscreen"
        elif visible_fraction >= 0.8:
            visibility_class = "continuous_visible"
        else:
            visibility_class = "intermittent_visible"
        minimum_distance = motion["minimum_player_enemy_distance"]
        policy_rows.append(
            {
                "episode_id": episode_id,
                "context": scenario["audio_review_context"],
                "map": candidate["map"],
                "weapon": candidate["weapon"],
                "enemy_model": candidate["enemy_model"],
                "enemy_skin": scenario["enemy_skin"],
                "policy": candidate["enemy_policy"]["name"],
                "initial_distance": candidate["enemy_policy"][
                    "initial_player_distance"
                ],
                "minimum_distance": minimum_distance,
                "minimum_distance_bin": distance_bin(minimum_distance),
                "visibility_class": visibility_class,
                "visible_fraction": visible_fraction,
                "within_15_deg_fraction": motion["within_15_deg_fraction"],
                "enemy_step_events": audio["event_count"],
                "mixer_linkage_rate": audio["event_mixer_linkage_rate"],
                "waveform_linkage_rate": audio["event_waveform_linkage_rate"],
                "video_url": (
                    f"../stage1_enemy_policy_audio_preflight_v2/media/{episode_id}.mp4"
                ),
                "episode_path": candidate["episode_path"],
            }
        )

    policy = {
        "count": len(policy_rows),
        "contexts": counts(policy_rows, lambda row: row["context"]),
        "policies": counts(policy_rows, lambda row: row["policy"]),
        "maps": counts(policy_rows, lambda row: row["map"]),
        "weapons": counts(policy_rows, lambda row: row["weapon"]),
        "enemy_models": counts(policy_rows, lambda row: row["enemy_model"]),
        "distance": counts(policy_rows, lambda row: row["minimum_distance_bin"]),
        "visibility": counts(policy_rows, lambda row: row["visibility_class"]),
        "enemy_step_events": sum(row["enemy_step_events"] for row in policy_rows),
        "mixer_linked_events": sum(
            round(row["enemy_step_events"] * row["mixer_linkage_rate"])
            for row in policy_rows
        ),
        "waveform_linked_events": sum(
            round(row["enemy_step_events"] * row["waveform_linkage_rate"])
            for row in policy_rows
        ),
        "max_mixer_to_waveform_onset_error_ms": max(
            (
                policy_audit["enemy_motion_audio"][row["episode_id"]][
                    "max_waveform_onset_error_ms"
                ]
                for row in policy_rows
            ),
            default=0.0,
        ),
        "formal_blockers": policy_audit["formal_collection_blockers"],
        "rows": policy_rows,
    }

    batch_specs = [
        {
            "key": "legacy_pilot",
            "label": "旧版 100 条 Pilot",
            "manifest": root / "manifests/accepted.jsonl",
            "rejects": root / "manifests/rejects.jsonl",
            "scope": "旧 spec：3 图 / 4 武器 / 5 类任务",
            "state": "冻结 pipeline 验证；split=pilot",
            "training": "否",
            "preview": None,
            "historical_iteration": False,
        },
        {
            "key": "v2_coverage_pilot",
            "label": "v2 coverage pilot",
            "manifest": root / "v2_coverage_pilot/manifests/accepted.jsonl",
            "rejects": root / "v2_coverage_pilot/manifests/rejects.jsonl",
            "scope": "Stage 1/2 类别、9 武器、14 appearance 覆盖证明",
            "state": "冻结 bounded evidence",
            "training": "否",
            "preview": "../v2/index.html",
            "historical_iteration": False,
        },
        {
            "key": "v2_motion_distance_pilot",
            "label": "v2 motion / distance pilot",
            "manifest": root / "v2_motion_distance_pilot/manifests/accepted.jsonl",
            "rejects": root / "v2_motion_distance_pilot/manifests/rejects.jsonl",
            "scope": "大位移 / 大转角 / 近距敌人补充证明",
            "state": "冻结 bounded evidence",
            "training": "否",
            "preview": "../v2_motion_distance/index.html",
            "historical_iteration": False,
        },
        {
            "key": "v2_stage1_review_fov90",
            "label": "Stage 1 FOV90 review",
            "manifest": root / "v2_stage1_review_fov90/manifests/accepted.jsonl",
            "rejects": root / "v2_stage1_review_fov90/manifests/rejects.jsonl",
            "scope": "60 条计划中的 46 条；旧严格逐 cell 筛法",
            "state": "部分 bounded review evidence",
            "training": "否",
            "preview": None,
            "historical_iteration": False,
        },
        {
            "key": "v2_stage1_production_preflight",
            "label": "Stage 1 production preflight",
            "manifest": prod_candidates_path,
            "rejects": prod_hard_rejects_path,
            "scope": "当前主生产链路；旧 CTF waypoint 污染已硬失效",
            "state": "当前主选择池",
            "training": "否；待正式授权",
            "preview": "../stage1_production_preflight/index.html",
            "historical_iteration": False,
        },
        {
            "key": "v2_stage1_enemy_policy_preflight",
            "label": "enemy-policy v1",
            "manifest": root
            / "v2_stage1_enemy_policy_preflight/manifests/candidates.jsonl",
            "rejects": None,
            "scope": "最初 4 policy 机制验证",
            "state": "历史迭代；已被后续修正版取代",
            "training": "否",
            "preview": "../stage1_enemy_policy_preflight/index.html",
            "historical_iteration": True,
        },
        {
            "key": "v2_stage1_enemy_policy_preflight_v2",
            "label": "enemy-policy v2",
            "manifest": root
            / "v2_stage1_enemy_policy_preflight_v2/manifests/candidates.jsonl",
            "rejects": None,
            "scope": "修正后的 4 policy 机制验证",
            "state": "历史迭代；已被音频版取代",
            "training": "否",
            "preview": None,
            "historical_iteration": True,
        },
        {
            "key": "v2_stage1_enemy_policy_visual_preflight",
            "label": "enemy-policy visual",
            "manifest": root
            / "v2_stage1_enemy_policy_visual_preflight/manifests/candidates.jsonl",
            "rejects": None,
            "scope": "4 条视觉 close / center review",
            "state": "历史迭代；音频修复前",
            "training": "否",
            "preview": "../stage1_enemy_policy_visual_preflight/index.html",
            "historical_iteration": True,
        },
        {
            "key": "v2_stage1_enemy_policy_audio_preflight",
            "label": "enemy-policy + audio legacy",
            "manifest": root
            / "v2_stage1_enemy_policy_audio_preflight/manifests/candidates.jsonl",
            "rejects": root
            / "v2_stage1_enemy_policy_audio_preflight/manifests/rejects.jsonl",
            "scope": "旧 8 条；包含未关闭的模式 waypoint HUD",
            "state": "历史迭代；已被 waypoint-clean v2 取代",
            "training": "否；hull-trace gate 未过",
            "preview": "../stage1_enemy_policy_audio_preflight/index.html",
            "historical_iteration": True,
        },
        {
            "key": "v2_stage1_enemy_policy_audio_preflight_v2",
            "label": "enemy-policy + audio waypoint-clean",
            "manifest": policy_candidates_path,
            "rejects": policy_dir / "manifests/rejects.jsonl",
            "scope": "最新 8 条：显式模式 + 双端 waypoint 关闭",
            "state": "最新人工 review evidence",
            "training": "否；hull-trace gate 未过",
            "preview": "../stage1_enemy_policy_audio_preflight_v2/index.html",
            "historical_iteration": False,
        },
    ]

    inventory: list[dict[str, Any]] = []
    for item in batch_specs:
        manifest_rows = load_jsonl(item["manifest"])
        reject_rows = load_jsonl(item["rejects"]) if item["rejects"] else []
        inventory.append(
            {
                **{
                    key: value
                    for key, value in item.items()
                    if key not in {"manifest", "rejects"}
                },
                "published": len(manifest_rows),
                "duration_seconds": len(manifest_rows) * 5,
                "reject_attempts": len(reject_rows),
                "manifest_path": str(item["manifest"]),
                "rejects_path": str(item["rejects"]) if item["rejects"] else None,
            }
        )

    legacy_rows = load_jsonl(root / "manifests/accepted.jsonl")
    coverage_rows = load_jsonl(
        root / "v2_coverage_pilot/manifests/accepted.jsonl"
    )
    motion_rows = load_jsonl(
        root / "v2_motion_distance_pilot/manifests/accepted.jsonl"
    )
    fov_rows = load_jsonl(
        root / "v2_stage1_review_fov90/manifests/accepted.jsonl"
    )

    evidence_distributions = {
        "legacy_pilot": {
            "count": len(legacy_rows),
            "maps": counts(legacy_rows, lambda row: row["map"]),
            "weapons": counts(legacy_rows, lambda row: row["weapon"]),
            "categories": counts(legacy_rows, lambda row: row["target_bin"]),
            "outcomes": counts(legacy_rows, lambda row: row["actual_outcome_bin"]),
            "enemy_models": counts(legacy_rows, lambda row: row["enemy_model"]),
        },
        "v2_coverage_pilot": {
            "count": len(coverage_rows),
            "roles": counts(coverage_rows, lambda row: row["dataset_role"]),
            "maps": counts(coverage_rows, lambda row: row["map"]),
            "weapons": counts(coverage_rows, lambda row: row["weapon"]),
        },
        "v2_motion_distance_pilot": {
            "count": len(motion_rows),
            "roles": counts(motion_rows, lambda row: row["dataset_role"]),
            "maps": counts(motion_rows, lambda row: row["map"]),
            "weapons": counts(motion_rows, lambda row: row["weapon"]),
            "net_displacement": counts(
                motion_rows, lambda row: row["motion"]["net_displacement_bin"]
            ),
            "yaw_range": counts(
                motion_rows, lambda row: row["motion"]["yaw_range_bin"]
            ),
        },
        "v2_stage1_review_fov90": {
            "count": len(fov_rows),
            "planned": 60,
            "roles": counts(fov_rows, lambda row: row["dataset_role"]),
            "maps": counts(fov_rows, lambda row: row["map"]),
            "weapons": counts(fov_rows, lambda row: row["weapon"]),
            "net_displacement": counts(
                fov_rows, lambda row: row["motion"]["net_displacement_bin"]
            ),
            "yaw_range": counts(
                fov_rows, lambda row: row["motion"]["yaw_range_bin"]
            ),
        },
    }

    published_total = sum(item["published"] for item in inventory)
    historical_policy_total = sum(
        item["published"] for item in inventory if item["historical_iteration"]
    )
    current_v2_evidence_total = sum(
        item["published"]
        for item in inventory
        if item["key"] != "legacy_pilot" and not item["historical_iteration"]
    )

    snapshot = {
        "schema_version": "xonotic-current-data-distribution-v1",
        "generated_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "boundary": {
            "formal_stage1_admitted": 0,
            "formal_stage2_admitted": 0,
            "formal_collection_authorized": False,
            "top_level_published_media_entries": published_total,
            "top_level_published_duration_seconds": published_total * 5,
            "historical_policy_iteration_entries": historical_policy_total,
            "current_v2_nonhistorical_evidence_entries": current_v2_evidence_total,
            "latest_review_entries": len(production_rows) + len(policy_rows),
            "current_stage1_selection_eligible": len(eligible),
        },
        "inventory": inventory,
        "production_preflight": production,
        "latest_enemy_policy_audio": policy,
        "bounded_evidence_distributions": evidence_distributions,
        "formal_targets": {
            "stage1_total": 60000,
            "stage1_duration_hours": 83.3333333333,
            "stage1_roles": {
                "foundation_no_enemy": 45000,
                "foundation_enemy_distractor": 15000,
            },
            "stage1_targets_percent": STAGE1_TARGETS,
            "stage2_total": 40000,
            "stage2_duration_hours": 55.5555555556,
            "stage2_targets": STAGE2_TARGETS,
            "total": 100000,
            "duration_hours": 138.8888888889,
            "maps_potential": 29,
            "core_weapons": 9,
            "core_enemy_models": 7,
            "core_enemy_appearances": 14,
        },
        "source_evidence": {
            str(path): {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "human_bytes": human_bytes(path.stat().st_size),
            }
            for path in source_paths
        },
        "notes": [
            "No current row is formally admitted to Stage 1 or Stage 2 training.",
            f"The {published_total} top-level entries are physical published media rows across incompatible pilot/preflight generations, not one trainable dataset.",
            f"Distribution comparisons use only the {len(eligible)} selection-eligible rows in the current Stage-1 production preflight.",
            f"The {len(policy_rows)} latest enemy-policy/audio rows are review-only and are not added to the {len(eligible)}-row selection pool.",
            "Seven legacy CTF production-preflight rows are hard-invalid under the corrected waypoint HUD contract; six had previously been selection-eligible.",
            "The 88 FOV90 reject rows are attempts from the superseded strict per-cell retry policy; they are not representative of the tiered-review production policy.",
        ],
    }
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    boundary = snapshot["boundary"]
    funnel = snapshot["production_preflight"]["funnel"]
    pool = snapshot["production_preflight"]["selection_pool"]
    policy = snapshot["latest_enemy_policy_audio"]
    assert boundary["top_level_published_media_entries"] == 255
    assert boundary["current_v2_nonhistorical_evidence_entries"] == 135
    assert funnel == {
        "manifest_candidates": 33,
        "capture_valid": 25,
        "selection_eligible": 23,
        "auto_keep_candidate": 16,
        "needs_review": 7,
        "training_excluded": 2,
        "hard_invalidated": 8,
        "formal_training_admitted": 0,
    }
    assert sum(pool["roles"].values()) == 23
    assert pool["roles"] == {
        "foundation_no_enemy": 18,
        "foundation_enemy_distractor": 5,
    }
    assert pool["unique_maps"] == 18
    assert pool["unique_weapons"] == 9
    assert policy["count"] == 8
    assert policy["policies"] == {
        "approach_retreat": 2,
        "idle": 2,
        "lateral_patrol": 2,
        "stop_and_go": 2,
    }
    assert policy["enemy_step_events"] == 56
    assert policy["mixer_linked_events"] == 56
    assert policy["waveform_linked_events"] == 56
    assert boundary["formal_stage1_admitted"] == 0
    assert boundary["formal_stage2_admitted"] == 0


def render_report(snapshot: dict[str, Any]) -> str:
    boundary = snapshot["boundary"]
    funnel = snapshot["production_preflight"]["funnel"]
    pool = snapshot["production_preflight"]["selection_pool"]
    policy = snapshot["latest_enemy_policy_audio"]

    def pct(value: int, total: int) -> str:
        return f"{100 * value / total:.1f}%"

    lines = [
        "# Xonotic 当前数据分布快照",
        "",
        f"生成时间：`{snapshot['generated_utc']}`",
        "",
        "## 结论边界",
        "",
        "- 正式 Stage 1 / Stage 2 训练数据：**0 / 0 条**。",
        f"- 顶层 manifest 已发布媒体：**{boundary['top_level_published_media_entries']} 条**，"
        f"合计 {boundary['top_level_published_duration_seconds'] / 60:.2f} 分钟；"
        "它们跨越互不兼容的 Pilot/preflight 代际，不能合并为训练集。",
        f"- 当前 Stage 1 主生产 preflight：33 条 published，{funnel['capture_valid']} 条 capture-valid，"
        f"**{funnel['selection_eligible']} 条 selection-eligible**。",
        f"- selection-eligible 中 {funnel['auto_keep_candidate']} 条 auto-keep，"
        f"{funnel['needs_review']} 条待人工 review；另有 {funnel['training_excluded']} 条训练排除、"
        f"{funnel['hard_invalidated']} 条硬失效。",
        f"- 旧 production-preflight 中 7 条 realized CTF 样本违反新的 waypoint HUD 硬门；"
        "其中 6 条原本在选择池，现已硬失效。",
        f"- 最新 enemy-policy/audio review：{policy['count']} 条；单独保留，不加入 "
        f"{pool['count']} 条主池。",
        "",
        f"## 当前 Stage 1 主选择池（{pool['count']} 条）",
        "",
        "| 维度 | 实际 | 占比 / 覆盖 |",
        "|---|---:|---:|",
        f"| 无敌人基础动力学 | {pool['roles']['foundation_no_enemy']} | "
        f"{pct(pool['roles']['foundation_no_enemy'], pool['count'])} |",
        f"| 含敌人 distractor | {pool['roles']['foundation_enemy_distractor']} | "
        f"{pct(pool['roles']['foundation_enemy_distractor'], pool['count'])} |",
        f"| 地图 | {pool['unique_maps']} | 29 张 potential official gameplay maps 中的 "
        f"{pool['unique_maps']} 张 |",
        f"| 武器 | {pool['unique_weapons']} | 9/9 core weapons |",
        f"| 敌人模型 | {pool['unique_enemy_models']} | 7 个 core models 中的 "
        f"{pool['unique_enemy_models']} 个 |",
        f"| 敌人 appearance | {pool['unique_enemy_appearances']} | 14 个 core appearances 中的 "
        f"{pool['unique_enemy_appearances']} 个 |",
        f"| path length ≥1000u | {pool['path_ge_1000']} | "
        f"{pct(pool['path_ge_1000'], pool['count'])}（正式目标 ≥30%） |",
        f"| path length ≥2000u | {pool['path_ge_2000']} | "
        f"{pct(pool['path_ge_2000'], pool['count'])}（正式目标 ≥10%） |",
        f"| net ≥512u 且 yaw ≥90° | {pool['joint_net_ge512_yaw_ge90']} | "
        f"{pct(pool['joint_net_ge512_yaw_ge90'], pool['count'])}（正式目标 ≥10%） |",
        "",
        f"注意：{pool['count']} 条只用于验证调度形状和人工筛选，不是正式配额进度。"
        "正式 60k 的当前进度仍为 0。",
        "",
        "## 最新敌人 policy / 音频 review（8 条）",
        "",
        f"- policy：`{json.dumps(policy['policies'], ensure_ascii=False)}`",
        f"- 实际最小距离分桶：`{json.dumps(policy['distance'], ensure_ascii=False)}`",
        f"- 可见性：`{json.dumps(policy['visibility'], ensure_ascii=False)}`",
        f"- 敌人脚步事件：{policy['enemy_step_events']}；mixer 链接 "
        f"{policy['mixer_linked_events']}/{policy['enemy_step_events']}；waveform onset 链接 "
        f"{policy['waveform_linked_events']}/{policy['enemy_step_events']}。",
        f"- 最大 mixer→waveform onset 误差：{policy['max_mixer_to_waveform_onset_error_ms']:.4f} ms。",
        f"- 正式阻塞：`{json.dumps(policy['formal_blockers'], ensure_ascii=False)}`。",
        "",
        "## 物理媒体 inventory",
        "",
        "| 批次 | Published | 时长 | Reject attempts | 状态 | 训练资格 |",
        "|---|---:|---:|---:|---|---|",
    ]
    for item in snapshot["inventory"]:
        lines.append(
            f"| {item['label']} | {item['published']} | "
            f"{item['duration_seconds'] / 60:.2f} min | {item['reject_attempts']} | "
            f"{item['state']} | {item['training']} |"
        )
    lines.extend(
        [
            "",
            "## 正式目标（尚未开始）",
            "",
            "- Stage 1：60,000 条 / 83.33 h，其中 45,000 无敌人、15,000 敌人 distractor。",
            "- Stage 2：40,000 条 / 55.56 h causal interaction。",
            "- 总计：100,000 条 / 138.89 h；超过该规模必须由 scaling benefit 决定。",
            "",
            "## 证据",
            "",
        ]
    )
    for path, evidence in snapshot["source_evidence"].items():
        lines.append(
            f"- `{path}` — `{evidence['sha256']}` ({evidence['human_bytes']})"
        )
    lines.append("")
    return "\n".join(lines)


def render_html(snapshot: dict[str, Any]) -> str:
    data_json = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    labels_json = json.dumps(LABELS, ensure_ascii=False, separators=(",", ":"))
    generated = html.escape(snapshot["generated_utc"])
    boundary = snapshot["boundary"]
    funnel = snapshot["production_preflight"]["funnel"]
    pool = snapshot["production_preflight"]["selection_pool"]
    policy = snapshot["latest_enemy_policy_audio"]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Xonotic 当前数据分布</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071017;
      --panel: #0d1b24;
      --panel2: #10242f;
      --text: #e8f1f5;
      --muted: #8fa5af;
      --line: #213743;
      --cyan: #58d7d5;
      --blue: #69a7ff;
      --green: #69db9a;
      --amber: #f2bd62;
      --red: #ff7c74;
      --purple: #b89cff;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at 10% -10%, rgba(88,215,213,.12), transparent 32rem),
        radial-gradient(circle at 100% 0%, rgba(105,167,255,.10), transparent 38rem),
        var(--bg);
      color: var(--text);
      font: 14px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    a {{ color: var(--cyan); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1500px; margin: 0 auto; padding: 28px 28px 80px; }}
    header {{ display: flex; gap: 24px; justify-content: space-between; align-items: flex-start; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 50px); letter-spacing: -.035em; line-height: 1.05; }}
    h2 {{ margin: 48px 0 16px; font-size: 25px; letter-spacing: -.02em; }}
    h3 {{ margin: 0 0 12px; font-size: 16px; }}
    .eyebrow {{ color: var(--cyan); text-transform: uppercase; letter-spacing: .16em; font-size: 11px; font-weight: 800; }}
    .subtitle {{ max-width: 880px; margin: 14px 0 0; color: var(--muted); font-size: 16px; }}
    .stamp {{ white-space: nowrap; color: var(--muted); font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; }}
    nav {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px; }}
    nav a {{ padding: 7px 11px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); background: rgba(13,27,36,.7); }}
    nav a:hover {{ color: var(--text); border-color: var(--cyan); text-decoration: none; }}
    .warning {{
      margin: 26px 0;
      padding: 16px 18px;
      border: 1px solid rgba(242,189,98,.45);
      border-left: 4px solid var(--amber);
      border-radius: 10px;
      background: rgba(242,189,98,.07);
    }}
    .warning strong {{ color: var(--amber); }}
    .metrics {{ display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 12px; }}
    .metric, .panel {{
      background: linear-gradient(155deg, rgba(16,36,47,.92), rgba(10,24,32,.94));
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: 0 16px 44px rgba(0,0,0,.12);
    }}
    .metric {{ min-height: 122px; padding: 16px; }}
    .metric .value {{ margin-top: 8px; font-size: 32px; font-weight: 800; letter-spacing: -.04em; }}
    .metric .label {{ color: var(--muted); font-size: 12px; }}
    .metric .detail {{ margin-top: 7px; color: var(--muted); font-size: 12px; }}
    .metric.emphasis .value {{ color: var(--cyan); }}
    .metric.zero .value {{ color: var(--red); }}
    .grid2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .grid3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .panel {{ padding: 18px; overflow: hidden; }}
    .panel .note {{ color: var(--muted); font-size: 12px; margin: -6px 0 12px; }}
    .funnel {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 8px; }}
    .fstep {{ border: 1px solid var(--line); border-radius: 10px; padding: 12px; background: rgba(7,16,23,.45); }}
    .fstep b {{ display: block; font-size: 24px; color: var(--cyan); }}
    .fstep span {{ color: var(--muted); font-size: 11px; }}
    .dist-row {{ display: grid; grid-template-columns: minmax(130px, 1.2fr) minmax(110px, 2.5fr) 120px; gap: 10px; align-items: center; margin: 9px 0; }}
    .dist-label {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar {{ height: 10px; position: relative; border-radius: 999px; background: #07131a; border: 1px solid #18303c; overflow: visible; }}
    .bar span {{ position: absolute; inset: 0 auto 0 0; border-radius: inherit; background: linear-gradient(90deg, var(--blue), var(--cyan)); min-width: 2px; }}
    .bar i {{ position: absolute; top: -4px; width: 2px; height: 16px; background: var(--amber); box-shadow: 0 0 0 1px #071017; }}
    .dist-value {{ text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; font-size: 12px; white-space: nowrap; }}
    .legend {{ display: flex; gap: 16px; color: var(--muted); font-size: 11px; margin-top: 12px; }}
    .swatch {{ display: inline-block; width: 16px; height: 6px; border-radius: 9px; margin-right: 5px; vertical-align: 1px; background: var(--cyan); }}
    .swatch.target {{ width: 2px; height: 11px; border-radius: 0; background: var(--amber); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
    th, td {{ padding: 10px 9px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    tbody tr:hover {{ background: rgba(88,215,213,.035); }}
    .table-wrap {{ overflow-x: auto; }}
    .badge {{ display: inline-flex; align-items: center; padding: 3px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; background: rgba(105,167,255,.12); color: var(--blue); border: 1px solid rgba(105,167,255,.25); }}
    .badge.good {{ color: var(--green); background: rgba(105,219,154,.10); border-color: rgba(105,219,154,.25); }}
    .badge.warn {{ color: var(--amber); background: rgba(242,189,98,.10); border-color: rgba(242,189,98,.25); }}
    .badge.bad {{ color: var(--red); background: rgba(255,124,116,.10); border-color: rgba(255,124,116,.25); }}
    .filters {{ display: grid; grid-template-columns: 1.4fr repeat(4, 1fr); gap: 8px; margin: 14px 0; }}
    input, select {{
      width: 100%;
      background: #08151d;
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
    }}
    .muted {{ color: var(--muted); }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .play {{
      cursor: pointer; border: 1px solid rgba(88,215,213,.3); color: var(--cyan);
      background: rgba(88,215,213,.07); border-radius: 7px; padding: 5px 8px;
    }}
    .video-drawer {{ display: none; padding: 12px 8px 18px; background: #07131a; }}
    .video-drawer.open {{ display: table-row; }}
    .video-drawer video {{ width: min(820px, 100%); border-radius: 9px; background: #000; }}
    .smallcards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    .smallcard {{ padding: 12px; border-radius: 9px; border: 1px solid var(--line); background: rgba(7,16,23,.5); }}
    .smallcard b {{ font-size: 22px; display: block; }}
    .smallcard span {{ color: var(--muted); font-size: 11px; }}
    details {{ border: 1px solid var(--line); border-radius: 10px; padding: 11px 13px; background: rgba(7,16,23,.35); }}
    summary {{ cursor: pointer; font-weight: 700; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; font-size: 11px; color: var(--muted); }}
    footer {{ margin-top: 54px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }}
    @media (max-width: 1050px) {{
      .metrics {{ grid-template-columns: repeat(2, 1fr); }}
      .grid3 {{ grid-template-columns: 1fr 1fr; }}
      .smallcards {{ grid-template-columns: repeat(2, 1fr); }}
      .filters {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (max-width: 700px) {{
      .wrap {{ padding: 20px 14px 60px; }}
      header {{ display: block; }}
      .stamp {{ margin-top: 12px; }}
      .metrics, .grid2, .grid3, .smallcards {{ grid-template-columns: 1fr; }}
      .funnel {{ grid-template-columns: 1fr 1fr; }}
      .filters {{ grid-template-columns: 1fr; }}
      .dist-row {{ grid-template-columns: minmax(100px, 1fr) minmax(80px, 1.2fr) 96px; }}
    }}
  </style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <div class="eyebrow">Xonotic 0.8.6 · Evidence snapshot</div>
      <h1>当前整体数据分布</h1>
      <p class="subtitle">把“已经落盘的物理媒体”“当前可选择的 Stage 1 preflight 池”“最新 enemy-policy/audio review”和“未来正式目标”分开统计。所有数字直接来自当前 manifest、post-hoc annotation 和 audit。</p>
    </div>
    <div class="stamp">snapshot<br>{generated}</div>
  </header>

  <nav>
    <a href="#overview">总览</a>
    <a href="#stage1">Stage 1 当前主池</a>
    <a href="#enemy">敌人分布</a>
    <a href="#policy">敌人 policy / 音频</a>
    <a href="#inventory">全部批次</a>
    <a href="#episodes">逐条查看</a>
    <a href="#target">正式目标</a>
  </nav>

  <div class="warning">
    <strong>最重要的口径：</strong>
    目前正式 Stage 1 / Stage 2 训练 manifest 都是 0 条。{boundary['top_level_published_media_entries']} 是跨旧 Pilot 与多代 preflight 的物理媒体条目数，不能合并成训练集；真正用于观察当前 Stage 1 调度形状的是 {pool['count']} 条 selection-eligible preflight。旧批次中 7 条 CTF waypoint HUD 污染样本已硬失效。
  </div>

  <section id="overview">
    <div class="metrics">
      <div class="metric zero"><div class="label">正式训练数据</div><div class="value">0</div><div class="detail">Stage 1 = 0 · Stage 2 = 0</div></div>
      <div class="metric emphasis"><div class="label">当前 Stage 1 主选择池</div><div class="value">{pool['count']}</div><div class="detail">{funnel['auto_keep_candidate']} auto-keep · {funnel['needs_review']} 待人工 review</div></div>
      <div class="metric"><div class="label">最新可 review 条目</div><div class="value">{boundary['latest_review_entries']}</div><div class="detail">33 production-preflight + {policy['count']} policy/audio</div></div>
      <div class="metric"><div class="label">顶层已发布媒体</div><div class="value">{boundary['top_level_published_media_entries']}</div><div class="detail">{boundary['top_level_published_duration_seconds'] / 60:.2f} min · 含 {boundary['historical_policy_iteration_entries']} 条历史 policy 迭代</div></div>
      <div class="metric"><div class="label">当前非历史 v2 evidence</div><div class="value">{boundary['current_v2_nonhistorical_evidence_entries']}</div><div class="detail">coverage / motion / FOV / production / audio</div></div>
    </div>
  </section>

  <section id="stage1">
    <h2>Stage 1 当前主选择池</h2>
    <div class="grid2">
      <div class="panel">
        <h3>{funnel['manifest_candidates']} 条 published 的筛选漏斗</h3>
        <p class="note">“selection-eligible”仍不等于正式训练 admitted。</p>
        <div class="funnel">
          <div class="fstep"><b>{funnel['manifest_candidates']}</b><span>published candidates</span></div>
          <div class="fstep"><b>{funnel['capture_valid']}</b><span>capture-valid</span></div>
          <div class="fstep"><b>{funnel['selection_eligible']}</b><span>selection-eligible</span></div>
          <div class="fstep"><b>0</b><span>formal admitted</span></div>
        </div>
        <div class="smallcards" style="margin-top:10px">
          <div class="smallcard"><b style="color:var(--green)">{funnel['auto_keep_candidate']}</b><span>auto-keep candidate</span></div>
          <div class="smallcard"><b style="color:var(--amber)">{funnel['needs_review']}</b><span>待人工 review</span></div>
          <div class="smallcard"><b style="color:var(--red)">{funnel['training_excluded']}</b><span>侧/后向持续阻塞排除</span></div>
          <div class="smallcard"><b style="color:var(--red)">{funnel['hard_invalidated']}</b><span>第三人称 / HUD 硬失效</span></div>
        </div>
      </div>
      <div class="panel">
        <h3>Stage 1 role：当前 vs 正式目标</h3>
        <p class="note">当前 {pool['count']} 条仅比较形状；黄线为 60k 的目标百分比。</p>
        <div id="rolesChart"></div>
        <div class="legend"><span><i class="swatch"></i>当前实际</span><span><i class="swatch target"></i>正式目标</span></div>
      </div>
    </div>

    <div class="grid2" style="margin-top:14px">
      <div class="panel"><h3>一级 action bucket</h3><div id="bucketsChart"></div><div class="legend"><span><i class="swatch"></i>当前实际</span><span><i class="swatch target"></i>正式目标</span></div></div>
      <div class="panel"><h3>地图覆盖</h3><p class="note">{pool['unique_maps']} 张当前 eligible 地图；正式上限是通过 gate 的 29 张 potential gameplay maps。</p><div id="mapsChart"></div></div>
      <div class="panel"><h3>武器覆盖</h3><p class="note">9/9 core weapons 已在当前小池中出现；正式集不做 action↔weapon 确定性绑定。</p><div id="weaponsChart"></div></div>
      <div class="panel">
        <h3>大运动硬指标</h3>
        <div class="smallcards">
          <div class="smallcard"><b id="path1000"></b><span>path ≥1000u，目标 ≥30%</span></div>
          <div class="smallcard"><b id="path2000"></b><span>path ≥2000u，目标 ≥10%</span></div>
          <div class="smallcard"><b id="jointMotion"></b><span>net ≥512u 且 yaw ≥90°，目标 ≥10%</span></div>
          <div class="smallcard"><b>{pool['unique_maps']}</b><span>eligible maps / 29 potential</span></div>
        </div>
      </div>
    </div>

    <div class="grid3" style="margin-top:14px">
      <div class="panel"><h3>实际 net displacement</h3><div id="netChart"></div></div>
      <div class="panel"><h3>实际 yaw range</h3><div id="yawChart"></div></div>
      <div class="panel"><h3>实际 pitch range</h3><div id="pitchChart"></div></div>
    </div>
  </section>

  <section id="enemy">
    <h2>当前主池中的敌人分布</h2>
    <p class="muted">{pool['count']} 条 eligible 中有 {pool['roles'].get('foundation_enemy_distractor', 0)} 条 enemy-distractor。样本很小，因此这里主要检查轴是否缺失，不把百分比当作配额达成。</p>
    <div class="grid2">
      <div class="panel"><h3>屏幕 / 准星关系</h3><div id="relationChart"></div></div>
      <div class="panel"><h3>实际物理距离</h3><div id="distanceChart"></div><p class="note">`contact_lt64` 是 1 条待 review 的 taxonomy edge，不计入正式 close quota。</p></div>
      <div class="panel"><h3>敌人模型</h3><div id="enemyModelsChart"></div></div>
      <div class="panel"><h3>model × skin appearance</h3><div id="appearancesChart"></div><p class="note">当前主池覆盖 {pool['unique_enemy_models']}/7 models、{pool['unique_enemy_appearances']}/14 appearances；最新 audio review 单独统计，不并入此池。</p></div>
    </div>
  </section>

  <section id="policy">
    <h2>最新 enemy-policy / 音频 review</h2>
    <div class="grid2">
      <div class="panel">
        <h3>8 条均衡 policy 抽样</h3>
        <div id="policyChart"></div>
        <p class="note">每个 policy 1 条 distribution + 1 条 visible-close；敌人轨迹不读取相机、准星或 live player state。</p>
      </div>
      <div class="panel">
        <h3>距离与可见性</h3>
        <div class="grid2">
          <div><div id="policyDistanceChart"></div></div>
          <div><div id="visibilityChart"></div></div>
        </div>
      </div>
      <div class="panel">
        <h3>敌人移动音频闭环</h3>
        <div class="smallcards">
          <div class="smallcard"><b>{policy['enemy_step_events']}</b><span>输出窗 authoritative footsteps</span></div>
          <div class="smallcard"><b>{policy['mixer_linked_events']}/{policy['enemy_step_events']}</b><span>enemy-entity mixer linkage</span></div>
          <div class="smallcard"><b>{policy['waveform_linked_events']}/{policy['enemy_step_events']}</b><span>waveform onset linkage</span></div>
          <div class="smallcard"><b>{policy['max_mixer_to_waveform_onset_error_ms']:.4f} ms</b><span>最大 mixer→waveform onset 误差</span></div>
        </div>
      </div>
      <div class="panel">
        <h3>当前仍未通过的正式 gate</h3>
        <p><span class="badge bad">whole_path_enemy_hull_trace_not_instrumented</span></p>
        <p class="muted">当前运动 policy 与音频链路已通过 bounded QA，但还缺整条敌人轨迹的 hull trace/contact instrumentation；所以 8 条仍是 review-only。</p>
        <p><a href="../stage1_enemy_policy_audio_preflight_v2/index.html">打开 {policy['count']} 条 waypoint-clean 完整音画 review 页面 →</a></p>
      </div>
    </div>
  </section>

  <section id="inventory">
    <h2>全部顶层批次 inventory</h2>
    <div class="panel table-wrap">
      <table>
        <thead><tr><th>批次</th><th>Published</th><th>时长</th><th>Reject attempts</th><th>范围</th><th>状态</th><th>训练资格</th><th>Review</th></tr></thead>
        <tbody id="inventoryBody"></tbody>
      </table>
    </div>
    <p class="muted">FOV90 的 88 条是旧版严格逐-cell mismatch 重试产生的 attempt，不代表当前 tiered-review 策略。旧 production-preflight 另有 7 条 realized CTF 样本因 waypoint HUD 污染被追溯硬失效。</p>
  </section>

  <section id="episodes">
    <h2>逐条查看当前 {funnel['manifest_candidates']} 条 production-preflight</h2>
    <div class="panel">
      <p class="note">默认只显示 {pool['count']} 条 selection-eligible；可切换查看阻塞排除、第三人称和旧 CTF HUD 硬失效。点击“播放”才加载 MP4。</p>
      <div class="filters">
        <input id="searchInput" placeholder="搜索 episode / map / category">
        <select id="statusFilter"><option value="eligible">selection-eligible（默认）</option><option value="">全部状态</option></select>
        <select id="roleFilter"><option value="">全部 role</option></select>
        <select id="mapFilter"><option value="">全部地图</option></select>
        <select id="weaponFilter"><option value="">全部武器</option></select>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Episode</th><th>状态</th><th>Role / bucket</th><th>Map</th><th>Weapon</th><th>Enemy</th><th>Motion</th><th>Flags</th><th>Video</th></tr></thead>
          <tbody id="episodeBody"></tbody>
        </table>
      </div>
      <p class="muted" id="episodeCount"></p>
      <p><a href="../stage1_production_preflight/index.html">打开原始 {funnel['manifest_candidates']} 条 production-preflight review 页面 →</a></p>
    </div>
  </section>

  <section id="policyRows">
    <h2>逐条查看最新 {policy['count']} 条 enemy-policy/audio</h2>
    <div class="panel table-wrap">
      <table>
        <thead><tr><th>Episode</th><th>Context</th><th>Map</th><th>Policy</th><th>Enemy</th><th>Min distance</th><th>Visibility</th><th>Footsteps</th><th>Video</th></tr></thead>
        <tbody id="policyBody"></tbody>
      </table>
    </div>
  </section>

  <section id="target">
    <h2>正式数据目标（本轮没有开始）</h2>
    <div class="metrics">
      <div class="metric"><div class="label">Stage 1 no-enemy</div><div class="value">45k</div><div class="detail">62.50 h</div></div>
      <div class="metric"><div class="label">Stage 1 enemy distractor</div><div class="value">15k</div><div class="detail">20.83 h</div></div>
      <div class="metric"><div class="label">Stage 1 合计</div><div class="value">60k</div><div class="detail">83.33 h · 30k/60k scaling gates</div></div>
      <div class="metric"><div class="label">Stage 2 causal</div><div class="value">40k</div><div class="detail">55.56 h · 20k/40k scaling gates</div></div>
      <div class="metric"><div class="label">第一版上限</div><div class="value">100k</div><div class="detail">138.89 h · 再扩需 scaling benefit</div></div>
    </div>
    <div class="grid2" style="margin-top:14px">
      <div class="panel"><h3>Stage 2 authoritative outcome</h3><div id="stage2OutcomeChart"></div></div>
      <div class="panel"><h3>Stage 2 aim policy</h3><div id="stage2AimChart"></div></div>
    </div>
  </section>

  <section>
    <h2>来源与可复核性</h2>
    <details>
      <summary>查看输入文件 SHA256</summary>
      <pre id="sources"></pre>
    </details>
  </section>

  <footer>
    Canonical JSON snapshot: <a href="CURRENT_DATA_DISTRIBUTION.json">CURRENT_DATA_DISTRIBUTION.json</a>
    · Markdown report: <a href="CURRENT_DATA_DISTRIBUTION_REPORT.md">CURRENT_DATA_DISTRIBUTION_REPORT.md</a>
    · 本页不授权正式批采。
  </footer>
</div>

<script>
const DATA = {data_json};
const LABELS = {labels_json};
const label = key => LABELS[key] || key || "—";
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
const pct = (n, d) => d ? 100*n/d : 0;

function orderedKeys(current, target, explicit=[]) {{
  const seen = new Set();
  const out = [];
  [...explicit, ...Object.keys(target || {{}}), ...Object.keys(current || {{}})].forEach(k => {{
    if (!seen.has(k)) {{ seen.add(k); out.push(k); }}
  }});
  return out;
}}

function renderDist(id, current, options={{}}) {{
  const target = options.target || {{}};
  const total = options.total ?? Object.values(current).reduce((a,b)=>a+b,0);
  const keys = orderedKeys(current, target, options.order || []);
  const maxPercent = Math.max(1, ...keys.map(k => pct(current[k]||0,total)), ...keys.map(k => target[k]||0));
  const node = document.getElementById(id);
  node.innerHTML = keys.map(k => {{
    const n = current[k] || 0;
    const actual = pct(n,total);
    const targetPct = target[k];
    const width = Math.min(100, actual / maxPercent * 100);
    const marker = targetPct == null ? "" : `<i style="left:${{Math.min(100,targetPct/maxPercent*100)}}%"></i>`;
    const targetText = targetPct == null ? "" : ` · 目标 ${{targetPct.toFixed(1)}}%`;
    return `<div class="dist-row"><div class="dist-label" title="${{esc(label(k))}}">${{esc(label(k))}}</div><div class="bar"><span style="width:${{width}}%"></span>${{marker}}</div><div class="dist-value">${{n}} · ${{actual.toFixed(1)}}%${{targetText}}</div></div>`;
  }}).join("");
}}

function renderSimple(id, current, order=[]) {{
  const total = Object.values(current).reduce((a,b)=>a+b,0);
  const keys = orderedKeys(current, {{}}, order);
  const max = Math.max(1, ...Object.values(current));
  document.getElementById(id).innerHTML = keys.map(k => {{
    const n = current[k] || 0;
    return `<div class="dist-row"><div class="dist-label" title="${{esc(label(k))}}">${{esc(label(k))}}</div><div class="bar"><span style="width:${{100*n/max}}%"></span></div><div class="dist-value">${{n}} · ${{pct(n,total).toFixed(1)}}%</div></div>`;
  }}).join("");
}}

const pool = DATA.production_preflight.selection_pool;
const target = DATA.formal_targets.stage1_targets_percent;
renderDist("rolesChart", pool.roles, {{target:target.roles,total:pool.count,order:["foundation_no_enemy","foundation_enemy_distractor"]}});
renderDist("bucketsChart", pool.buckets, {{target:target.buckets,total:pool.count,order:["node_atomic","mixed_action","high_motion_special","weapon_environment"]}});
renderSimple("mapsChart", pool.maps);
renderSimple("weaponsChart", pool.weapons, ["Blaster","Shotgun","MachineGun","Mortar","Electro","Crylink","Vortex","Hagar","Devastator"]);
renderDist("netChart", pool.net_displacement, {{target:target.net_displacement,total:pool.count,order:["lt64","64_256","256_512","512_1024","gt1024"]}});
renderDist("yawChart", pool.yaw_range, {{target:target.yaw_range,total:pool.count,order:["lt15","15_45","45_90","90_180","ge180"]}});
renderDist("pitchChart", pool.pitch_range, {{target:target.pitch_range,total:pool.count,order:["lt5","5_15","15_30","ge30"]}});
const enemyTotal = pool.roles.foundation_enemy_distractor || 0;
renderDist("relationChart", pool.enemy_relation, {{target:target.enemy_relation,total:enemyTotal,order:["offscreen_or_occluded","visible_far","near_crosshair","brief_center_pass","center_linger","nearly_continuous_center"]}});
renderDist("distanceChart", pool.enemy_distance, {{target:{{contact_lt64:0,...target.enemy_distance}},total:enemyTotal,order:["contact_lt64","close","near","medium","far","very_far","extreme"]}});
renderSimple("enemyModelsChart", pool.enemy_models);
renderSimple("appearancesChart", pool.enemy_appearances);

document.getElementById("path1000").textContent = `${{pool.path_ge_1000}} / ${{pool.count}} (${{pct(pool.path_ge_1000,pool.count).toFixed(1)}}%)`;
document.getElementById("path2000").textContent = `${{pool.path_ge_2000}} / ${{pool.count}} (${{pct(pool.path_ge_2000,pool.count).toFixed(1)}}%)`;
document.getElementById("jointMotion").textContent = `${{pool.joint_net_ge512_yaw_ge90}} / ${{pool.count}} (${{pct(pool.joint_net_ge512_yaw_ge90,pool.count).toFixed(1)}}%)`;

const policy = DATA.latest_enemy_policy_audio;
renderSimple("policyChart", policy.policies, ["idle","lateral_patrol","approach_retreat","stop_and_go"]);
renderSimple("policyDistanceChart", policy.distance, ["contact_lt64","close","near","medium","far","very_far","extreme"]);
renderSimple("visibilityChart", policy.visibility, ["offscreen","intermittent_visible","continuous_visible"]);

const s2out = Object.fromEntries(Object.entries(DATA.formal_targets.stage2_targets.outcome).map(([k,v])=>[k,v.count]));
const s2aim = Object.fromEntries(Object.entries(DATA.formal_targets.stage2_targets.aim_policy).map(([k,v])=>[k,v.count]));
renderSimple("stage2OutcomeChart", s2out);
renderSimple("stage2AimChart", s2aim);

document.getElementById("inventoryBody").innerHTML = DATA.inventory.map(row => `
  <tr>
    <td><b>${{esc(row.label)}}</b></td>
    <td>${{row.published}}</td>
    <td>${{(row.duration_seconds/60).toFixed(2)}} min</td>
    <td>${{row.reject_attempts}}</td>
    <td>${{esc(row.scope)}}</td>
    <td>${{esc(row.state)}}</td>
    <td>${{esc(row.training)}}</td>
    <td>${{row.preview ? `<a href="${{esc(row.preview)}}">打开</a>` : "—"}}</td>
  </tr>`).join("");

function badgeClass(status) {{
  if (status === "auto_keep_candidate") return "good";
  if (status === "needs_review") return "warn";
  return "bad";
}}
function populateSelect(id, values) {{
  const select = document.getElementById(id);
  [...new Set(values)].sort().forEach(value => select.insertAdjacentHTML("beforeend", `<option value="${{esc(value)}}">${{esc(label(value))}}</option>`));
}}
const rows = DATA.production_preflight.rows;
populateSelect("statusFilter", rows.map(r=>r.disposition));
populateSelect("roleFilter", rows.map(r=>r.role));
populateSelect("mapFilter", rows.map(r=>r.map));
populateSelect("weaponFilter", rows.map(r=>r.weapon));

function renderEpisodes() {{
  const query = document.getElementById("searchInput").value.toLowerCase();
  const status = document.getElementById("statusFilter").value;
  const role = document.getElementById("roleFilter").value;
  const map = document.getElementById("mapFilter").value;
  const weapon = document.getElementById("weaponFilter").value;
  const filtered = rows.filter(r => {{
    const haystack = `${{r.episode_id}} ${{r.map}} ${{r.category}} ${{r.weapon}}`.toLowerCase();
    const statusOk = status === "eligible" ? r.selection_eligible : (!status || r.disposition === status);
    return statusOk && (!role || r.role===role) && (!map || r.map===map) && (!weapon || r.weapon===weapon) && (!query || haystack.includes(query));
  }});
  const body = document.getElementById("episodeBody");
  body.innerHTML = filtered.map(r => {{
    const enemy = r.enemy_present ? `${{r.enemy_model}}/skin${{r.enemy_skin}}<br><span class="muted">${{label(r.distance_bin)}} · ${{label(r.target_relation)}}</span>` : "无";
    const flags = [...r.soft_flag_codes, ...r.training_exclusion_reasons, ...r.hard_invalidation_reasons];
    return `
      <tr>
        <td class="mono">${{esc(r.episode_id)}}</td>
        <td><span class="badge ${{badgeClass(r.disposition)}}">${{esc(label(r.disposition))}}</span></td>
        <td>${{esc(label(r.role))}}<br><span class="muted">${{esc(label(r.bucket))}} · ${{esc(r.category)}}</span></td>
        <td>${{esc(r.map)}}<br><span class="muted">${{esc(r.requested_gametype)}}→${{esc(r.realized_gametype)}}</span></td>
        <td>${{esc(r.weapon)}}</td>
        <td>${{enemy}}</td>
        <td>net ${{label(r.net_displacement_bin)}}<br><span class="muted">yaw ${{label(r.yaw_range_bin)}} · pitch ${{label(r.pitch_range_bin)}}</span></td>
        <td class="muted">${{flags.length ? esc(flags.join(", ")) : "—"}}</td>
        <td><button class="play" data-video="${{esc(r.video_url)}}" data-id="${{esc(r.episode_id)}}">播放</button> · <a href="${{esc(r.video_url)}}" target="_blank">单独打开</a></td>
      </tr>
      <tr class="video-drawer" id="video-${{esc(r.episode_id)}}"><td colspan="9"></td></tr>`;
  }}).join("");
  document.getElementById("episodeCount").textContent = `显示 ${{filtered.length}} / ${{rows.length}} 条`;
  body.querySelectorAll(".play").forEach(button => button.addEventListener("click", () => {{
    const drawer = document.getElementById(`video-${{button.dataset.id}}`);
    const cell = drawer.firstElementChild;
    if (drawer.classList.toggle("open")) {{
      if (!cell.firstElementChild) cell.innerHTML = `<video controls preload="metadata" src="${{esc(button.dataset.video)}}"></video>`;
      button.textContent = "收起";
    }} else {{
      const video = cell.querySelector("video");
      if (video) video.pause();
      button.textContent = "播放";
    }}
  }}));
}}
["searchInput","statusFilter","roleFilter","mapFilter","weaponFilter"].forEach(id => document.getElementById(id).addEventListener("input", renderEpisodes));
renderEpisodes();

document.getElementById("policyBody").innerHTML = policy.rows.map(r => `
  <tr>
    <td class="mono">${{esc(r.episode_id)}}</td>
    <td>${{esc(r.context)}}</td>
    <td>${{esc(r.map)}}</td>
    <td>${{esc(label(r.policy))}}</td>
    <td>${{esc(r.enemy_model)}}/skin${{r.enemy_skin}}</td>
    <td>${{r.minimum_distance.toFixed(1)}}u<br><span class="muted">${{esc(label(r.minimum_distance_bin))}}</span></td>
    <td>${{esc(r.visibility_class)}}<br><span class="muted">${{(100*r.visible_fraction).toFixed(1)}}%</span></td>
    <td>${{r.enemy_step_events}} · mixer ${{(100*r.mixer_linkage_rate).toFixed(0)}}% · wave ${{(100*r.waveform_linkage_rate).toFixed(0)}}%</td>
    <td><a href="${{esc(r.video_url)}}" target="_blank">播放 MP4</a></td>
  </tr>`).join("");

document.getElementById("sources").textContent = Object.entries(DATA.source_evidence).map(([path,e]) => `${{e.sha256}}  ${{path}}  (${{e.human_bytes}})`).join("\\n");
</script>
</body>
</html>
"""


def write_outputs(root: Path, snapshot: dict[str, Any]) -> list[Path]:
    data_dir = root / "current_data_distribution"
    preview_dir = root / "previews/current_data_distribution"
    data_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    json_path = data_dir / "CURRENT_DATA_DISTRIBUTION.json"
    report_path = data_dir / "CURRENT_DATA_DISTRIBUTION_REPORT.md"
    mode_hud_audit_path = data_dir / "LEGACY_MODE_HUD_AUDIT.json"
    html_path = preview_dir / "index.html"
    checksum_path = data_dir / "CURRENT_DATA_DISTRIBUTION_SHA256SUMS"

    json_text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    mode_hud_audit_text = json.dumps(
        snapshot["production_preflight"]["mode_hud_audit"],
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    report_text = render_report(snapshot)
    json_path.write_text(json_text, encoding="utf-8")
    mode_hud_audit_path.write_text(
        mode_hud_audit_text, encoding="utf-8"
    )
    report_path.write_text(report_text, encoding="utf-8")
    html_path.write_text(render_html(snapshot), encoding="utf-8")
    preview_json_path = preview_dir / json_path.name
    preview_report_path = preview_dir / report_path.name
    preview_json_path.write_text(json_text, encoding="utf-8")
    preview_report_path.write_text(report_text, encoding="utf-8")

    files_to_hash = [
        json_path,
        report_path,
        mode_hud_audit_path,
        html_path,
        preview_json_path,
        preview_report_path,
        root / "scripts/generate_current_data_distribution.py",
    ]
    checksum_path.write_text(
        "".join(f"{sha256(path)}  {path}\n" for path in files_to_hash),
        encoding="utf-8",
    )
    for path in [*files_to_hash, checksum_path]:
        path.chmod(0o644)
    return [
        json_path,
        report_path,
        mode_hud_audit_path,
        html_path,
        preview_json_path,
        preview_report_path,
        checksum_path,
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = derive_snapshot(args.root)
    outputs = write_outputs(args.root, snapshot)
    summary = {
        "generated_utc": snapshot["generated_utc"],
        "formal_training_rows": 0,
        "top_level_published_rows": snapshot["boundary"][
            "top_level_published_media_entries"
        ],
        "stage1_selection_eligible": snapshot["boundary"][
            "current_stage1_selection_eligible"
        ],
        "latest_policy_audio_rows": snapshot["latest_enemy_policy_audio"]["count"],
        "outputs": [str(path) for path in outputs],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
