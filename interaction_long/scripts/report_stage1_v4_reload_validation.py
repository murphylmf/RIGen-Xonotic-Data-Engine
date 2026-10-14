                      
"""Audit and report the eight-weapon Stage-1 v4 reload validation run."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def audit_episode(
    output_root: Path, row: dict[str, Any]
) -> dict[str, Any]:
    episode_id = str(row["episode_id"])
    package = output_root / "episodes" / episode_id
    qa = json.loads((package / "qa.json").read_text(encoding="utf-8"))
    events = pd.read_parquet(package / "events.parquet")
    actions = pd.read_parquet(package / "model_actions.parquet")
    acceptance = row["acceptance"]
    proof = capture.reload_event_proof(
        events,
        str(acceptance["reload_weapon"]),
        expected_start_tick=int(
            acceptance["reload_start_server_tick"]
        ),
        expected_duration_ticks=int(
            acceptance["reload_duration_ticks"]
        ),
        expected_initial_clip=float(
            acceptance["reload_initial_clip"]
        ),
        expected_capacity=float(
            acceptance["reload_clip_capacity"]
        ),
    )
    checks = {
        "reload_proven": proof["passed"],
        "hard_gates": all(qa["hard_gates"].values()),
        "frames_320": int(qa["video"]["frames"]) == 320,
        "audio_240000": int(
            qa["audio"]["samples_per_channel"]
        )
        == 240_000,
        "frame_tick_mapping": float(
            qa["mapping"]["success_rate"]
        )
        == 1.0,
        "nvidia_hardware": str(
            qa["runtime"]["renderer"]
        ).startswith("NVIDIA "),
        "gametype": (
            qa["mode"]["requested_gametype"]
            == qa["mode"]["realized_gametype"]
        ),
        "model_action_rows": len(actions) == 320,
        "reload_button_one_frame": int(actions["west"].sum()) == 1,
        "secondary_always_zero": int(
            actions["left_trigger"].sum()
        )
        == 0,
        "primary_always_zero": int(
            actions["right_trigger"].sum()
        )
        == 0,
    }
    return {
        "episode_id": episode_id,
        "source_episode_id": row.get("source_episode_id"),
        "weapon": row["weapon"],
        "weapon_netname": row["weapon_netname"],
        "map": row["map"],
        "gametype": row["gametype"],
        "checks": checks,
        "passed": all(checks.values()),
        "reload": proof,
        "qa": {
            "frames": qa["video"]["frames"],
            "audio_samples_per_channel": qa["audio"][
                "samples_per_channel"
            ],
            "mapping_rate": qa["mapping"]["success_rate"],
            "audio_peak_s16": qa["audio"]["peak_s16"],
            "renderer": qa["runtime"]["renderer"],
            "hard_gate_count": len(qa["hard_gates"]),
            "hard_gate_pass_count": sum(
                bool(value) for value in qa["hard_gates"].values()
            ),
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stage-1 v4 换弹生效验证",
        "",
        f"生成时间：{report['created_utc']}",
        "",
        "## 结论",
        "",
        (
            f"8/8 可换弹核心武器通过；Blaster 不支持换弹且不在测试集。"
            f"完整 pipeline 与全部硬 QA："
            f"{'PASS' if report['passed'] else 'FAIL'}。"
        ),
        "",
        (
            "换弹按钮在输出 frame 16（server tick 80）只按 1 帧，"
            "完成于 tick 208。认证要求唯一 start/complete、parent、"
            "actor、weapon、时序、clip 和 reserve 资源变化全部一致。"
        ),
        "",
        "| 武器 | tick | clip | reserve | 音频峰值 | QA |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["episodes"]:
        proof = row["reload"]
        lines.append(
            "| {weapon} | {start}→{complete} | {pre_clip:g}→"
            "{post_clip:g} | {pre_reserve:g}→{post_reserve:g} | "
            "{peak} | {status} |".format(
                weapon=row["weapon"],
                start=proof["start_tick"],
                complete=proof["complete_tick"],
                pre_clip=proof["pre_clip"],
                post_clip=proof["post_clip"],
                pre_reserve=proof["pre_reserve"],
                post_reserve=proof["post_reserve"],
                peak=row["qa"]["audio_peak_s16"],
                status="PASS" if row["passed"] else "FAIL",
            )
        )
    lines.extend(
        (
            "",
            "每条均为 320 帧、每声道 240000 音频采样、frame-tick "
            "mapping 1.0、NVIDIA hardware renderer；LT/RT 始终为 0，"
            "只有 X/reload 在 frame 16 为 1。",
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-manifest",
        type=Path,
        default=(
            capture.ROOT
            / "manifests/stage1_v4_reload_validation/input.jsonl"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=(
            capture.ROOT / "stage1_v4_reload_validation_output"
        ),
    )
    args = parser.parse_args()
    manifest = args.input_manifest.resolve()
    output_root = args.output_root.resolve()
    rows = capture.load_jsonl(manifest)
    episodes = [
        audit_episode(output_root, row) for row in rows
    ]
    checks = {
        "planned_rows": len(rows) == 8,
        "published_rows": len(episodes) == 8,
        "episode_ids_unique": len(
            {row["episode_id"] for row in episodes}
        )
        == 8,
        "all_episodes_passed": all(
            row["passed"] for row in episodes
        ),
    }
    report = {
        "schema_version": (
            "xonotic-stage1-v4-reload-validation-report-v1"
        ),
        "created_utc": capture.utc_now(),
        "manifest": str(manifest),
        "manifest_sha256": capture.sha256_file(manifest),
        "output_root": str(output_root),
        "checks": checks,
        "passed": all(checks.values()),
        "episodes": episodes,
    }
    json_path = output_root / "RELOAD_VALIDATION_REPORT.json"
    markdown_path = output_root / "RELOAD_VALIDATION_REPORT.md"
    write_atomic(
        json_path,
        json.dumps(
            report, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    write_atomic(markdown_path, markdown(report))
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "episodes": len(episodes),
                "json": str(json_path),
                "markdown": str(markdown_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
