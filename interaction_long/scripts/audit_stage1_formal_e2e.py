                      
"""Independently audit a completed formal Stage-1 shard run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def gpu_metrics(
    path: Path | None,
    started_utc: str,
    finished_utc: str,
) -> dict[str, Any] | None:
    if path is None:
        return None
    started = parse_utc(started_utc)
    finished = parse_utc(finished_utc)
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            observed = datetime.strptime(
                row["timestamp"].strip(), "%Y/%m/%d %H:%M:%S.%f"
            ).replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            observed_utc = observed.astimezone(started.tzinfo)
            if not (started <= observed_utc <= finished):
                continue
            rows.append(
                {
                    "gpu_percent": float(
                        row[" utilization.gpu [%]"].replace("%", "")
                    ),
                    "memory_mib": float(
                        row[" memory.used [MiB]"].replace("MiB", "")
                    ),
                    "power_watts": float(
                        row[" power.draw [W]"].replace("W", "")
                    ),
                }
            )
    if not rows:
        return {
            "path": str(path),
            "samples_in_worker_window": 0,
        }
    gpu = [row["gpu_percent"] for row in rows]
    memory = [row["memory_mib"] for row in rows]
    power = [row["power_watts"] for row in rows]
    return {
        "path": str(path),
        "samples_in_worker_window": len(rows),
        "gpu_percent_mean": sum(gpu) / len(gpu),
        "gpu_percent_max": max(gpu),
        "gpu_samples_ge_90_percent": sum(value >= 90 for value in gpu),
        "gpu_fraction_ge_90_percent": (
            sum(value >= 90 for value in gpu) / len(gpu)
        ),
        "memory_mib_max": max(memory),
        "power_watts_max": max(power),
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root).resolve()
    shard_tag = (
        f"shard-{args.shard_index:03d}-of-{args.shard_count:03d}"
    )
    shard_root = (
        output_root
        / "manifests"
        / "shards"
        / args.candidate_wave
        / shard_tag
    )
    run_result_path = shard_root / "RUN_RESULT.json"
    accepted_path = shard_root / "accepted_candidates.jsonl"
    queue_path = shard_root / "queue_events.jsonl"
    rejects_path = shard_root / "rejects.jsonl"
    run = load_json(run_result_path)
    accepted = load_jsonl(accepted_path)
    queue_rows = load_jsonl(queue_path)
    rejects = load_jsonl(rejects_path)
    warmup_paths = sorted(
        (shard_root / "resident_warmups").glob("*/*/RESULT.json")
    )
    warmups = [load_json(path) for path in warmup_paths]

    failures: list[dict[str, Any]] = []

    def require(condition: bool, name: str, detail: Any = None) -> None:
        if not condition:
            failures.append({"check": name, "detail": detail})

    expected_rows = int(run["planned_rows"])
    require(run.get("pass") is True, "run_result_pass", run.get("pass"))
    require(
        run.get("selection_complete") is True,
        "selection_complete",
        run.get("selection_complete"),
    )
    require(
        int(run.get("accepted_candidates", -1)) == expected_rows,
        "run_accepted_count",
        run.get("accepted_candidates"),
    )
    require(
        int(run.get("completed_hard_rejects", -1)) == 0,
        "no_completed_hard_rejects",
        run.get("completed_hard_rejects"),
    )
    require(
        int(run.get("incomplete_operational_or_unexpected", -1)) == 0,
        "no_incomplete_attempts",
        run.get("incomplete_operational_or_unexpected"),
    )
    require(len(accepted) == expected_rows, "accepted_jsonl_count", len(accepted))
    episode_ids = [str(row.get("episode_id", "")) for row in accepted]
    require(
        len(set(episode_ids)) == len(episode_ids),
        "accepted_episode_ids_unique",
    )
    require(not rejects, "reject_manifest_empty", len(rejects))

    queue_states = Counter(str(row.get("state")) for row in queue_rows)
    require(
        queue_states
        == {
            "capturing": expected_rows,
            "candidate_accepted": expected_rows,
        },
        "queue_state_counts",
        dict(queue_states),
    )

    data_spec_path = Path(args.data_spec).resolve()
    data_spec_sha256 = sha256_file(data_spec_path)
    qa_passed = 0
    package_hash_files = 0
    package_bytes = 0
    demo_files = 0
    demo_bytes = 0
    raw_selected = 0
    raw_hash_files = 0
    raw_bytes = 0
    modes: Counter[str] = Counter()
    maps: Counter[str] = Counter()
    action_buckets: Counter[str] = Counter()
    renderers: Counter[str] = Counter()
    runtime_configs: Counter[str] = Counter()
    for row in accepted:
        episode_id = str(row["episode_id"])
        episode_path = Path(row["episode_path"]).resolve()
        require(
            episode_path == output_root / "candidates" / episode_id,
            "episode_path_scoped",
            {"episode_id": episode_id, "path": str(episode_path)},
        )
        require(episode_path.is_dir(), "episode_directory_exists", episode_id)
        for relative, expected_hash in row.get("package_sha256", {}).items():
            artifact = episode_path / relative
            require(
                artifact.is_file(),
                "package_artifact_exists",
                {"episode_id": episode_id, "artifact": relative},
            )
            if artifact.is_file():
                actual_hash = sha256_file(artifact)
                require(
                    actual_hash == expected_hash,
                    "package_artifact_sha256",
                    {
                        "episode_id": episode_id,
                        "artifact": relative,
                        "expected": expected_hash,
                        "actual": actual_hash,
                    },
                )
                package_hash_files += 1
                package_bytes += artifact.stat().st_size

        demo = episode_path / "capture_provenance" / "demo.dem"
        require(
            "capture_provenance/demo.dem"
            in row.get("package_sha256", {}),
            "demo_in_package_hash_manifest",
            episode_id,
        )
        require(
            demo.is_file() and demo.stat().st_size > 0,
            "demo_retained_nonempty",
            episode_id,
        )
        if demo.is_file():
            demo_files += 1
            demo_bytes += demo.stat().st_size

        qa_path = episode_path / "qa.json"
        episode_json_path = episode_path / "episode.json"
        if not qa_path.is_file() or not episode_json_path.is_file():
            require(False, "qa_and_episode_json_exist", episode_id)
            continue
        qa = load_json(qa_path)
        episode = load_json(episode_json_path)
        mode = qa.get("mode", {})
        runtime = qa.get("runtime", {})
        mapping = qa.get("mapping", {})
        audio = qa.get("audio", {})
        video = qa.get("video", {})
        hud = qa.get("hud", {})
        hard_gates = qa.get("hard_gates", {})
        checks = {
            "accepted": qa.get("accepted") is True,
            "capture_valid": qa.get("capture_valid") is True,
            "hard_failures_empty": qa.get("hard_failures") == [],
            "all_hard_gates_true": bool(hard_gates)
            and all(hard_gates.values()),
            "frames_320": video.get("frames") == 320,
            "fps_64": video.get("fps") == 64,
            "audio_240000": audio.get("samples_per_channel") == 240_000,
            "audio_48khz_stereo": audio.get("sample_rate") == 48_000
            and audio.get("channels") == 2,
            "audio_non_silent": float(audio.get("peak_s16", 0)) > 0,
            "mapping_rows_320": mapping.get("mapped_frames") == 320
            and mapping.get("total_frames") == 320,
            "mapping_tick_span": mapping.get("episode_tick_first") == 64
            and mapping.get("episode_tick_last") == 383,
            "mapping_rate_one": mapping.get("success_rate") == 1.0,
            "presentation_phase": (
                mapping.get("presentation_phase", {}).get("passed") is True
            ),
            "mode_exact": mode.get("requested_gametype")
            == mode.get("realized_gametype"),
            "mode_no_fallback": mode.get("fallback_detected") is False,
            "nvidia_renderer": str(runtime.get("renderer", "")).startswith(
                "NVIDIA "
            ),
            "hud_exact": hud.get("cl_hidewaypoints") == 2
            and hud.get("g_ctf_flag_waypoint") == 0
            and hud.get("hud_panel_modicons") == 0,
            "resident_reuse": (
                runtime.get("resident_lane", {}).get("enabled") is True
                and runtime.get("resident_lane", {}).get("process_reused")
                is True
            ),
            "x264_config": runtime.get("x264_preset") == "medium"
            and runtime.get("x264_threads") == 16
            and runtime.get("x264_cpuset") == "0-15"
            and runtime.get("encode_concurrency") == 4,
            "source_commit": episode.get("source_commit")
            == run.get("source_commit"),
            "data_spec_sha256": episode.get("data_spec_sha256")
            == data_spec_sha256,
            "not_training_admitted": episode.get("training_admitted") is False
            and qa.get("training_admitted") is False,
        }
        require(
            all(checks.values()),
            "episode_qa_contract",
            {
                "episode_id": episode_id,
                "failed": [
                    name for name, passed in checks.items() if not passed
                ],
            },
        )
        if all(checks.values()):
            qa_passed += 1
        modes[str(mode.get("realized_gametype"))] += 1
        maps[str(episode.get("map"))] += 1
        action_buckets[str(episode.get("primary_bucket"))] += 1
        renderers[str(runtime.get("renderer"))] += 1
        runtime_configs[
            json.dumps(
                {
                    "resident_lanes": runtime.get("live_concurrency"),
                    "active_sdl": runtime.get("sdl_concurrency"),
                    "encode_concurrency": runtime.get("encode_concurrency"),
                    "x264_threads": runtime.get("x264_threads"),
                    "x264_cpuset": runtime.get("x264_cpuset"),
                    "x264_preset": runtime.get("x264_preset"),
                },
                sort_keys=True,
            )
        ] += 1

        if row.get("raw_audit_selected") is True:
            raw_selected += 1
            raw_path = Path(str(row.get("raw_audit_path", ""))).resolve()
            require(
                raw_path.is_dir(),
                "raw_audit_directory_exists",
                episode_id,
            )
            require(
                "raw_capture.avi" in row.get("raw_audit_sha256", {}),
                "raw_avi_in_hash_manifest",
                episode_id,
            )
            for relative, expected_hash in row.get(
                "raw_audit_sha256", {}
            ).items():
                artifact = raw_path / relative
                require(
                    artifact.is_file(),
                    "raw_audit_artifact_exists",
                    {"episode_id": episode_id, "artifact": relative},
                )
                if artifact.is_file():
                    actual_hash = sha256_file(artifact)
                    require(
                        actual_hash == expected_hash,
                        "raw_audit_artifact_sha256",
                        {
                            "episode_id": episode_id,
                            "artifact": relative,
                            "expected": expected_hash,
                            "actual": actual_hash,
                        },
                    )
                    raw_hash_files += 1
                    raw_bytes += artifact.stat().st_size

    require(
        len(warmups) == int(
            run.get("resident_schedule_policy", {}).get(
                "world_group_chunks", -1
            )
        ),
        "one_warmup_per_world_group_chunk",
        len(warmups),
    )
    for path, result in zip(warmup_paths, warmups):
        checks = result.get("checks", {})
        require(
            result.get("passed") is True
            and bool(checks)
            and all(checks.values())
            and result.get("formal_collection_authorized") is False
            and result.get("training_admitted") is False,
            "warmup_full_qa_and_excluded",
            str(path),
        )

    started = parse_utc(run["started_utc"])
    finished = parse_utc(run["finished_utc"])
    wall_seconds = (finished - started).total_seconds()
    report = {
        "schema_version": "xonotic-stage1-formal-e2e-audit-v1",
        "created_utc": datetime.now(tz=started.tzinfo)
        .isoformat()
        .replace("+00:00", "Z"),
        "pass": not failures,
        "training_admitted": False,
        "output_root": str(output_root),
        "shard_root": str(shard_root),
        "run_result": str(run_result_path),
        "source_commit": run.get("source_commit"),
        "data_spec": {
            "path": str(data_spec_path),
            "sha256": data_spec_sha256,
        },
        "first_pass": {
            "started_utc": run["started_utc"],
            "finished_utc": run["finished_utc"],
            "wall_seconds": wall_seconds,
            "published_episodes": len(accepted),
            "end_to_end_episodes_per_hour_including_warmups": (
                len(accepted) * 3600.0 / wall_seconds
            ),
            "hard_rejects": run.get("completed_hard_rejects"),
            "operational_incomplete": run.get(
                "incomplete_operational_or_unexpected"
            ),
        },
        "accepted_manifest": {
            "path": str(accepted_path),
            "sha256": sha256_file(accepted_path),
            "rows": len(accepted),
            "unique_episode_ids": len(set(episode_ids)),
        },
        "queue_journal": {
            "path": str(queue_path),
            "sha256": sha256_file(queue_path),
            "rows": len(queue_rows),
            "states": dict(queue_states),
        },
        "qa": {
            "passed": qa_passed,
            "expected": len(accepted),
            "package_hash_files_verified": package_hash_files,
            "package_bytes_hashed": package_bytes,
            "demo_files": demo_files,
            "demo_bytes": demo_bytes,
            "raw_selected": raw_selected,
            "raw_hash_files_verified": raw_hash_files,
            "raw_bytes_hashed": raw_bytes,
            "resident_warmups_passed": sum(
                result.get("passed") is True for result in warmups
            ),
            "resident_warmups_expected": len(warmups),
        },
        "coverage": {
            "modes": dict(sorted(modes.items())),
            "maps": dict(sorted(maps.items())),
            "primary_buckets": dict(sorted(action_buckets.items())),
            "renderers": dict(sorted(renderers.items())),
            "runtime_configurations": dict(runtime_configs),
        },
        "gpu": gpu_metrics(
            Path(args.gpu_log).resolve() if args.gpu_log else None,
            run["started_utc"],
            run["finished_utc"],
        ),
        "failures": failures,
    }
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", required=True)
    result.add_argument(
        "--candidate-wave",
        choices=("primary", "replenishment"),
        default="primary",
    )
    result.add_argument("--shard-index", type=int, default=0)
    result.add_argument("--shard-count", type=int, default=32)
    result.add_argument(
        "--data-spec",
        default=str(ROOT / "XONOTIC_DATA_SPEC_V2.md"),
    )
    result.add_argument("--gpu-log")
    result.add_argument("--audit-output", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    report = audit(args)
    output = Path(args.audit_output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
