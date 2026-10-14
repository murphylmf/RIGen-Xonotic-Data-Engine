                      
"""Decode a stratified duel-v11 subset through the current Stage-2 loader."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


LTX_ROOT = Path(".")
DEFAULT_REFERENCE_CONFIG = LTX_ROOT / (
    "configs/ltx2_ar_teacher_xonotic_stage2_s2step8k_camera_neutral_"
    "chunk2_20fps_3x4_12gpu.yaml"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def choose_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_episode: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_episode.setdefault(str(row["episode_id"]), []).append(row)
    selected: list[dict[str, Any]] = []
    for episode_id in sorted(by_episode):
        episode_rows = by_episode[episode_id]

        def outside_count(row: dict[str, Any]) -> int:
            blocks = (row.get("prompt_structured") or {}).get("blocks") or []
            return sum(bool(block.get("fully_outside_view")) for block in blocks)

        selected.append(min(episode_rows, key=lambda row: (outside_count(row), str(row["sample_id"]))))
        selected.append(max(episode_rows, key=lambda row: (outside_count(row), str(row["sample_id"]))))
    if len(selected) != 8 or len({str(row["sample_id"]) for row in selected}) != 8:
        raise ValueError("expected exactly two distinct validation clips from each of four episodes")
    return selected


def validate_manifest(
    manifest_path: Path,
    selected_rows: list[dict[str, Any]],
    output_dir: Path,
    reference_config: Path,
    *,
    ar_mode: bool,
) -> dict[str, Any]:
    import torch
    import yaml

    for source_path in reversed(
        (
            LTX_ROOT / "packages/ltx-trainer/src",
            LTX_ROOT / "packages/ltx-core/src",
            LTX_ROOT / "packages/ltx-pipelines/src",
        )
    ):
        sys.path.insert(0, str(source_path))
    from ltx_trainer.config import LtxTrainerConfig
    from ltx_trainer.datasets_online import CrossFPSAudioActionDataset

    subset_name = "ar_loader_subset.jsonl" if ar_mode else "bidirectional_loader_subset.jsonl"
    subset_path = output_dir / subset_name
    audio_ids_path = output_dir / f"{subset_name}.audio_ids.txt"
    write_jsonl(subset_path, selected_rows)
    audio_ids_path.write_text(
        "".join(f"{row['sample_id']}\n" for row in selected_rows), encoding="utf-8"
    )

    raw_config = yaml.safe_load(reference_config.read_text(encoding="utf-8")) or {}
    config = LtxTrainerConfig(**raw_config)
    source = config.data.sources[0]
    dataset = CrossFPSAudioActionDataset(
        Path("./rigen_data"),
        manifest_path=subset_path,
        audio_loss_eligible_ids_path=audio_ids_path,
        target_width=832,
        target_height=480,
        target_num_frames=81,
        target_fps=20.0,
        target_audio_sample_rate=16000,
        random_temporal_crop=False,
        require_audio=True,
        source_name="xonotic_duel_v11_stage2_prompt",
        action_binding_config=config.action_binding,
        action_binding_training=False,
        joystick_normalization=source.joystick_normalization,
    )
    if len(dataset) != len(selected_rows):
        raise ValueError(f"loader discovered {len(dataset)}/{len(selected_rows)} rows")
    expected = {str(row["sample_id"]): row for row in selected_rows}
    by_id = {str(entry["sample_id"]): index for index, entry in enumerate(dataset._samples)}
    results: list[dict[str, Any]] = []
    for sample_id in sorted(expected):
        sample = dataset[by_id[sample_id]]
        row = expected[sample_id]
        expected_prompt = dataset._clean_prompt_text(row["prompt_text"])
        expected_schedule = [
            dataset._clean_prompt_text(value) for value in row.get("prompt_schedule") or []
        ]
        checks = {
            "video_81_frames": int(sample["video_pixels"].shape[0]) == 81,
            "video_832x480": list(sample["video_pixels"].shape[-2:]) == [480, 832],
            "audio_16khz": int(sample["audio_sample_rate"]) == 16_000,
            "audio_present": int(sample["audio_waveform"].numel()) > 0,
            "actions_81x10": list(sample["actions"].shape) == [81, 10],
            "joystick_81x4": list(sample["action_joystick"].shape) == [81, 4],
            "buttons_81x6": list(sample["action_buttons"].shape) == [81, 6],
            "finite_actions": bool(torch.isfinite(sample["actions"]).all().item()),
            "actions_in_range": bool((sample["actions"].abs() <= 1.000001).all().item()),
            "audio_loss_eligible": sample.get("audio_loss_eligible") is True,
            "prompt_text_preserved_after_canonical_cleaning": str(sample["prompt_text"])
            == str(expected_prompt),
        }
        if ar_mode:
            checks["five_prompt_schedule_blocks"] = len(sample.get("prompt_schedule") or []) == 5
            checks["prompt_schedule_preserved_after_canonical_cleaning"] = list(
                sample.get("prompt_schedule") or []
            ) == expected_schedule
        if not all(checks.values()):
            raise ValueError(f"loader failed {sample_id}: {checks}")
        results.append(
            {
                "sample_id": sample_id,
                "video_shape": list(sample["video_pixels"].shape),
                "audio_shape": list(sample["audio_waveform"].shape),
                "actions_shape": list(sample["actions"].shape),
                "checks": checks,
            }
        )
        del sample
        gc.collect()
    return {
        "manifest": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "subset_manifest": str(subset_path),
        "dataset_rows": len(dataset),
        "results": results,
        "all_pass": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ar-manifest", type=Path, required=True)
    parser.add_argument("--bidirectional-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference-config", type=Path, default=DEFAULT_REFERENCE_CONFIG)
    parser.add_argument("--batch-ready", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output: {output_dir}")
    output_dir.mkdir(parents=True)
    ar_manifest = args.ar_manifest.resolve()
    bidir_manifest = args.bidirectional_manifest.resolve()
    reference_config = args.reference_config.resolve()
    ar_rows = read_jsonl(ar_manifest)
    bidir_rows = read_jsonl(bidir_manifest)
    selected_ar = choose_rows(ar_rows)
    wanted = {str(row["sample_id"]) for row in selected_ar}
    selected_bidir = [row for row in bidir_rows if str(row["sample_id"]) in wanted]
    if len(selected_bidir) != len(selected_ar):
        raise ValueError("AR/bidirectional validation subsets do not match")

    report = {
        "schema_version": "xonotic-duel-v11-stage2-real-loader-validation-v1",
        "reference_config": str(reference_config),
        "reference_config_sha256": sha256(reference_config),
        "ar": validate_manifest(
            ar_manifest, selected_ar, output_dir, reference_config, ar_mode=True
        ),
        "bidirectional": validate_manifest(
            bidir_manifest, selected_bidir, output_dir, reference_config, ar_mode=False
        ),
    }
    report["all_pass"] = bool(report["ar"]["all_pass"] and report["bidirectional"]["all_pass"])
    (output_dir / "LOADER_VALIDATION.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if args.batch_ready is not None:
        batch_ready_path = args.batch_ready.resolve()
        batch_ready = json.loads(batch_ready_path.read_text(encoding="utf-8"))
        gates = {
            "batch_static_gates_all_pass": bool(batch_ready.get("training_ready"))
            and bool(all((batch_ready.get("gates") or {}).values())),
            "real_loader_ar_stratified_8_all_pass": bool(report["ar"]["all_pass"])
            and int(report["ar"]["dataset_rows"]) == 8,
            "real_loader_bidirectional_stratified_8_all_pass": bool(
                report["bidirectional"]["all_pass"]
            )
            and int(report["bidirectional"]["dataset_rows"]) == 8,
        }
        final_ready = {
            "schema_version": "xonotic-duel-v11-stage2-training-ready-v1",
            "training_ready": bool(all(gates.values())),
            "batch_id": batch_ready["batch_id"],
            "counts": batch_ready["counts"],
            "gates": gates,
            "batch_ready": {
                "path": str(batch_ready_path),
                "sha256": sha256(batch_ready_path),
            },
            "loader_validation": {
                "path": str(output_dir / "LOADER_VALIDATION.json"),
                "sha256": sha256(output_dir / "LOADER_VALIDATION.json"),
            },
            "manifests": batch_ready["manifests"],
        }
        (batch_ready_path.parent / "TRAINING_READY.json").write_text(
            json.dumps(final_ready, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if not final_ready["training_ready"]:
            raise ValueError(f"final training readiness failed: {gates}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
