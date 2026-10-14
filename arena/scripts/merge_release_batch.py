                      
"""Validate and merge isolated duel-v11 episode releases into one batch index."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("release_dirs", type=Path, nargs="+")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output: {output_dir}")
    output_dir.mkdir(parents=True)

    ar_rows: list[dict[str, Any]] = []
    bidir_rows: list[dict[str, Any]] = []
    rollout_rows: list[dict[str, Any]] = []
    release_reports: list[dict[str, Any]] = []
    motion = Counter()
    visibility = Counter()

    for release_arg in args.release_dirs:
        release = release_arg.resolve()
        ready_path = release / "TRAINING_READY.json"
        ready = read_json(ready_path)
        if not ready.get("training_ready") or not all(ready.get("gates", {}).values()):
            raise ValueError(f"release is not training ready: {release}")
        episode_id = str(ready["episode_id"])
        episode_ar = read_jsonl(release / "ar_training_manifest.jsonl")
        episode_bidir = read_jsonl(release / "bidirectional_training_manifest.jsonl")
        if len(episode_ar) != 15 or len(episode_bidir) != 15:
            raise ValueError(f"release does not contain 15 clips in both manifests: {release}")
        ar_rows.extend(episode_ar)
        bidir_rows.extend(episode_bidir)
        motion.update(ready["motion_label_distribution"])
        visibility.update(ready["visibility_phase_distribution"])

        rollout_video = Path(ready["rollout_media"]["path"]).resolve()
        rollout_dir = release / "rollout_60s"
        rollout_prompt = rollout_dir / "prompt_bundle.json"
        rollout_actions = rollout_dir / "model_actions_64hz.parquet"
        rollout_visibility = rollout_dir / "visibility_64hz.parquet"
        for artifact in (rollout_video, rollout_prompt, rollout_actions, rollout_visibility):
            if not artifact.is_file() or artifact.stat().st_size == 0:
                raise FileNotFoundError(f"missing rollout artifact: {artifact}")
        rollout_rows.append(
            {
                "schema_version": "xonotic-duel-v11-stage2-rollout-row-v1",
                "batch_id": args.batch_id,
                "episode_id": episode_id,
                "duration_seconds": 60.0,
                "video_path": str(rollout_video),
                "video_sha256": sha256(rollout_video),
                "video_frames": int(ready["rollout_media"]["frames"]),
                "video_fps": ready["rollout_media"]["fps"],
                "prompt_bundle_path": str(rollout_prompt),
                "prompt_bundle_sha256": sha256(rollout_prompt),
                "action_path": str(rollout_actions),
                "action_sha256": sha256(rollout_actions),
                "visibility_path": str(rollout_visibility),
                "visibility_sha256": sha256(rollout_visibility),
                "prompt_blocks": int(ready["counts"]["rollout_blocks"]),
                "training_admitted": True,
            }
        )
        release_reports.append(
            {
                "episode_id": episode_id,
                "release_dir": str(release),
                "training_ready_sha256": sha256(ready_path),
                "counts": ready["counts"],
                "motion_label_distribution": ready["motion_label_distribution"],
                "visibility_phase_distribution": ready["visibility_phase_distribution"],
            }
        )

    sample_ids = [str(row["sample_id"]) for row in ar_rows]
    bidir_sample_ids = [str(row["sample_id"]) for row in bidir_rows]
    all_blocks = [
        block
        for row in ar_rows
        for block in ((row.get("prompt_structured") or {}).get("blocks") or [])
    ]
    offscreen_text = "The opponent is outside the player's view during this block."
    outside_blocks = [block for block in all_blocks if block.get("fully_outside_view")]
    moving_visible_blocks = [
        block
        for block in all_blocks
        if block.get("motion_label") not in {"stationary", "unobserved"}
    ]
    referenced_paths_exist = all(
        Path(row[key]).is_file()
        for row in ar_rows + bidir_rows
        for key in ("video_path", "action_path", "visibility_path", "prompt_bundle_path")
    )
    expected_clips = 15 * len(release_reports)
    gates = {
        "all_source_releases_training_ready": True,
        "four_60s_rollouts": len(rollout_rows) == 4
        and all(row["video_frames"] == 1201 for row in rollout_rows),
        "sixty_ar_clips": len(ar_rows) == expected_clips == 60,
        "sixty_bidirectional_clips": len(bidir_rows) == expected_clips == 60,
        "ar_sample_ids_unique": len(sample_ids) == len(set(sample_ids)),
        "bidirectional_sample_ids_unique": len(bidir_sample_ids) == len(set(bidir_sample_ids)),
        "all_referenced_artifacts_exist": referenced_paths_exist,
        "offscreen_prompt_contract_passed_in_every_release": all(
            report["counts"]["offscreen_enemy_fire_ticks"] == 0 for report in release_reports
        ),
        "all_300_prompt_blocks_present": len(all_blocks) == 300,
        "fully_outside_blocks_use_exact_sentence_only": bool(outside_blocks)
        and all(block.get("text") == offscreen_text for block in outside_blocks),
        "every_observed_moving_block_has_screen_destination": bool(moving_visible_blocks)
        and all(block.get("screen_destination") for block in moving_visible_blocks),
        "wounded_language_absent": all(
            "wounded" not in prompt.lower()
            for row in ar_rows
            for prompt in row.get("prompt_schedule") or []
        ),
    }
    write_jsonl(output_dir / "rollout_60s_manifest.jsonl", rollout_rows)
    write_jsonl(output_dir / "ar_training_manifest.jsonl", ar_rows)
    write_jsonl(output_dir / "bidirectional_training_manifest.jsonl", bidir_rows)
    audio_ids_path = output_dir / "audio_loss_eligible_ids.txt"
    audio_ids_path.write_text("".join(f"{sample_id}\n" for sample_id in sample_ids), encoding="utf-8")
    gates["audio_loss_ids_cover_all_clips"] = len(sample_ids) == len(set(sample_ids)) == 60
    report = {
        "schema_version": "xonotic-duel-v11-stage2-batch-ready-v1",
        "batch_id": args.batch_id,
        "training_ready": bool(all(gates.values())),
        "unique_source_duration_seconds": 60 * len(rollout_rows),
        "alternate_clip_packaging_duration_seconds": 4 * len(ar_rows),
        "counts": {
            "source_releases": len(release_reports),
            "rollouts_60s": len(rollout_rows),
            "clips_4s_81frames": len(ar_rows),
            "ar_rows": len(ar_rows),
            "bidirectional_rows": len(bidir_rows),
            "prompt_blocks": sum(row["prompt_blocks"] for row in rollout_rows),
        },
        "motion_label_distribution": dict(sorted(motion.items())),
        "visibility_phase_distribution": dict(sorted(visibility.items())),
        "gates": gates,
        "releases": release_reports,
        "manifests": {
            "rollout_60s": str(output_dir / "rollout_60s_manifest.jsonl"),
            "ar": str(output_dir / "ar_training_manifest.jsonl"),
            "bidirectional": str(output_dir / "bidirectional_training_manifest.jsonl"),
            "audio_loss_eligible_ids": str(audio_ids_path),
        },
    }
    write_json(output_dir / "BATCH_READY.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["training_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
