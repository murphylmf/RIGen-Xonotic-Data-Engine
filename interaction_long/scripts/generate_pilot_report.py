                      
"""Generate the final Pilot report from locked, measured artifacts."""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = Path("./xonotic_capture")
REPORT = ROOT / "PILOT_REPORT.md"


def fmt_seconds(seconds: float) -> str:
    hours = seconds / 3600
    days = hours / 24
    return f"{hours:.2f} h ({days:.2f} d)"


def stats(values: list[float]) -> str:
    return (
        f"min {min(values):.6g}, mean {mean(values):.6g}, "
        f"max {max(values):.6g}"
    )


def numeric_stats(values: list[float]) -> dict[str, float]:
    return {
        "min": min(values),
        "mean": mean(values),
        "max": max(values),
    }


def parse_pilot_log() -> tuple[Path | None, float | None, Counter[str]]:
    candidates = sorted(
        ROOT.glob("logs/*pilot100_rng_boundary_final.log"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        candidates = sorted(
            ROOT.glob("logs/*pilot_100.log"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    if not candidates:
        return None, None, Counter()
    path = candidates[0]
    text = path.read_text(errors="replace")
    started_match = re.search(r"^started_utc=(.+)$", text, re.MULTILINE)
    finished_match = re.search(r"^finished_utc=(.+)$", text, re.MULTILINE)
    wall: float | None = None
    if started_match and finished_match:
        started = datetime.fromisoformat(
            started_match.group(1).replace("Z", "+00:00")
        )
        finished = datetime.fromisoformat(
            finished_match.group(1).replace("Z", "+00:00")
        )
        wall = (finished - started).total_seconds()
    reasons = Counter(
        re.findall(r"^reject pilot_[0-9]+ reason=([^ ]+)", text, re.MULTILINE)
    )
    return path, wall, reasons


def main() -> int:
    capture.require_conda()
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite final report: {REPORT}")
    accepted_path = ROOT / "manifests/accepted.jsonl"
    rejects_path = ROOT / "manifests/rejects.jsonl"
    lock_path = ROOT / "locks/SOURCE_ASSET_LOCK.json"
    benchmark_path = ROOT / "benchmarks/renderers/renderer_scaling.json"
    determinism_path = ROOT / "qa/determinism.json"
    final_verification_path = ROOT / "qa/final_pilot_verification.json"
    phase0_60_path = ROOT / "phase0/av-tests/phase0-60s/qa.json"
    phase0_600_path = ROOT / "phase0/av-tests/phase0-600s/qa.json"
    preview_index_path = ROOT / "previews/PREVIEW_INDEX.md"
    required = (
        accepted_path,
        rejects_path,
        lock_path,
        benchmark_path,
        determinism_path,
        final_verification_path,
        phase0_60_path,
        phase0_600_path,
        preview_index_path,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"report prerequisites missing: {missing}")

    accepted = sorted(
        capture.load_jsonl(accepted_path), key=lambda row: row["episode_id"]
    )
    if len(accepted) != 100 or len({row["episode_id"] for row in accepted}) != 100:
        raise RuntimeError(f"expected exactly 100 accepted rows, found {len(accepted)}")
    if Counter(row["target_bin"] for row in accepted) != Counter(
        capture.TARGET_COUNTS
    ):
        raise RuntimeError("accepted Pilot quota mismatch")
    if any(row["split"] != "pilot" for row in accepted):
        raise RuntimeError("non-pilot split in accepted manifest")

    qas: list[dict[str, Any]] = []
    episode_metadata: list[dict[str, Any]] = []
    for row in accepted:
        qa_path = Path(row["episode_path"]) / "qa.json"
        qa = json.loads(qa_path.read_text())
        if not qa["accepted"] or not all(qa["gates"].values()):
            raise RuntimeError(f"accepted QA gate failure: {qa_path}")
        qas.append(qa)
        metadata = json.loads(
            (Path(row["episode_path"]) / "episode.json").read_text()
        )
        episode_metadata.append(metadata)

    rejected = capture.load_jsonl(rejects_path)
    reject_reasons = Counter(row["reason"] for row in rejected)
    pilot_log, pilot_wall, pilot_run_rejects = parse_pilot_log()
    lock = json.loads(lock_path.read_text())
    benchmarks = json.loads(benchmark_path.read_text())["results"]
    determinism = json.loads(determinism_path.read_text())
    final_verification = json.loads(final_verification_path.read_text())
    if (
        final_verification.get("result") != "pass"
        or int(final_verification.get("accepted", 0)) != 100
    ):
        raise RuntimeError(
            f"final independent verification failed: {final_verification_path}"
        )
    phase0_60 = json.loads(phase0_60_path.read_text())
    phase0_600 = json.loads(phase0_600_path.read_text())
    preview_paths = sorted((ROOT / "previews").glob("pilot_*_preview.mp4"))
    if len(preview_paths) != 100:
        raise RuntimeError(
            f"expected 100 canonical MP4 previews, found {len(preview_paths)}"
        )
    source_commits = {
        str(metadata["source_commit"]) for metadata in episode_metadata
    }
    if source_commits != {str(lock["capture"]["head_commit"])}:
        raise RuntimeError(
            f"episode/source-lock commit mismatch: {sorted(source_commits)}"
        )
    player_positions = {
        tuple(float(value) for value in row["player_origin"]) for row in accepted
    }
    enemy_positions = {
        tuple(float(value) for value in row["enemy_origin"]) for row in accepted
    }
    position_pairs = {
        (
            tuple(float(value) for value in row["player_origin"]),
            tuple(float(value) for value in row["enemy_origin"]),
        )
        for row in accepted
    }
    anchor_ids = Counter(str(row["anchor_id"]) for row in accepted)
    if (
        len(anchor_ids) != 12
        or len(player_positions) != 100
        or len(enemy_positions) != 100
        or len(position_pairs) != 100
    ):
        raise RuntimeError(
            "position diversity contract failed: "
            f"anchors={len(anchor_ids)} player={len(player_positions)} "
            f"enemy={len(enemy_positions)} pairs={len(position_pairs)}"
        )

    gate_counts: Counter[str] = Counter()
    for qa in qas:
        gate_counts.update(name for name, value in qa["gates"].items() if value)
    actual_outcomes = Counter(row["actual_outcome_bin"] for row in accepted)
    hit_rate_bins = Counter(row["hit_rate_bin"] for row in accepted)
    renderers = sorted({qa["runtime"]["renderer"] for qa in qas})
    mappings = [float(qa["mapping"]["success_rate"]) for qa in qas]
    onset_ms = [float(qa["audio"]["max_onset_error_ms"]) for qa in qas]
    linkage = [float(qa["events"]["linkage_rate"]) for qa in qas]
    action_error = [
        float(qa["telemetry"]["action_schedule_max_error"]) for qa in qas
    ]
    live_seconds = [float(qa["runtime"]["live_wall_seconds"]) for qa in qas]
    render_seconds = [float(qa["runtime"]["render_wall_seconds"]) for qa in qas]
    encode_seconds = [float(qa["runtime"]["encode_wall_seconds"]) for qa in qas]
    cpfs_seconds = [float(row["cpfs_copy_seconds"]) for row in accepted]
    cpfs_rates = [float(row["cpfs_copy_mib_s"]) for row in accepted]
    raw_bytes = [sum(Path(row["raw_path"], name).stat().st_size for name in row["raw_artifacts_sha256"]) for row in accepted]
    formal_bytes = [
        sum(Path(row["episode_path"], name).stat().st_size for name in row["artifacts_sha256"])
        for row in accepted
    ]
    total_resource_changes = sum(
        int(qa["telemetry"]["resource_changes"]) for qa in qas
    )
    total_resource_explained = sum(
        int(qa["telemetry"]["resource_changes_explained"]) for qa in qas
    )
    total_link_required = sum(int(qa["events"]["link_required"]) for qa in qas)
    total_linked = sum(int(qa["events"]["linked"]) for qa in qas)
    reload_qas = [
        qa
        for row, qa in zip(accepted, qas, strict=True)
        if row["target_bin"] == "machinegun_reload"
    ]

    if pilot_wall is None:
        observed_per_accept = mean(
            live + render + encode + copy
            for live, render, encode, copy in zip(
                live_seconds, render_seconds, encode_seconds, cpfs_seconds, strict=True
            )
        )
        pilot_wall_source = "sum of per-episode measured stages"
    else:
        observed_per_accept = pilot_wall / 100
        pilot_wall_source = str(pilot_log)
    final_run_rejected = sum(pilot_run_rejects.values())
    final_run_attempts = 100 + final_run_rejected
    final_run_acceptance_rate = 100 / final_run_attempts
    attempt_multiplier = final_run_attempts / 100
    production_episodes = 15_804
    production_video_seconds = production_episodes * 5
    serial_eta_seconds = (
        observed_per_accept * production_episodes * attempt_multiplier
    )
    best_render = max(
        benchmarks, key=lambda row: row["render_video_seconds_per_wall_second"]
    )
    best_encode = max(
        benchmarks, key=lambda row: row["x264_video_seconds_per_wall_second"]
    )
    renderer_lower_bound = production_video_seconds / float(
        best_render["render_video_seconds_per_wall_second"]
    )
    encode_lower_bound = production_video_seconds / float(
        best_encode["x264_video_seconds_per_wall_second"]
    )
    measured_media_lower_bound = max(renderer_lower_bound, encode_lower_bound)
    storage_tib = (
        (mean(raw_bytes) + mean(formal_bytes)) * production_episodes / 1024**4
    )
    aggregate_path = ROOT / "qa/pilot_aggregate.json"
    if aggregate_path.exists():
        raise RuntimeError(f"refusing to overwrite aggregate QA: {aggregate_path}")
    aggregate = {
        "schema_version": "xonotic-pilot-aggregate-qa-v1",
        "created_utc": capture.utc_now(),
        "accepted": 100,
        "unique_episode_ids": 100,
        "split": "pilot",
        "target_distribution": dict(
            sorted(Counter(row["target_bin"] for row in accepted).items())
        ),
        "actual_outcome_distribution": dict(sorted(actual_outcomes.items())),
        "hit_rate_bin_distribution": dict(sorted(hit_rate_bins.items())),
        "rejected_attempts_recorded": len(rejected),
        "rejection_reasons": dict(sorted(reject_reasons.items())),
        "final_pilot_run": {
            "accepted": 100,
            "rejected": final_run_rejected,
            "acceptance_rate": final_run_acceptance_rate,
        },
        "final_pilot_run_rejection_reasons": dict(
            sorted(pilot_run_rejects.items())
        ),
        "video": {
            "frames_total": 32_000,
            "frames_per_episode": 320,
            "fps": 64,
            "resolution": [1280, 720],
        },
        "audio": {
            "samples_per_channel_total": 24_000_000,
            "samples_per_channel_per_episode": 240_000,
            "sample_rate": 48_000,
            "channels": 2,
            "samples_per_frame": 750,
            "max_onset_error_ms": numeric_stats(onset_ms),
        },
        "frame_tick_mapping_success_rate": numeric_stats(mappings),
        "event_linkage": {
            "linked": total_linked,
            "required": total_link_required,
            "per_episode_rate": numeric_stats(linkage),
        },
        "resource_changes": {
            "explained": total_resource_explained,
            "total": total_resource_changes,
        },
        "action_schedule_max_error": numeric_stats(action_error),
        "successful_machinegun_reload_episodes": len(reload_qas),
        "renderer": renderers,
        "source_commits": sorted(source_commits),
        "position_diversity": {
            "anchor_pairs": len(anchor_ids),
            "anchor_id_counts": dict(sorted(anchor_ids.items())),
            "unique_player_origins": len(player_positions),
            "unique_enemy_origins": len(enemy_positions),
            "unique_player_enemy_pairs": len(position_pairs),
            "xy_jitter_bound_units": 4.0,
        },
        "visual_policy": {
            "damage_text": False,
            "hit_indication": False,
            "health_armor_hud": False,
            "ammo_hud": False,
            "weapon_model": True,
            "crosshair": True,
        },
        "canonical_mp4_previews": len(preview_paths),
        "determinism": determinism,
        "independent_final_verification": {
            "path": str(final_verification_path),
            "sha256": capture.sha256_file(final_verification_path),
            "formal_hashes_verified": final_verification[
                "formal_hashes_verified"
            ],
            "raw_hashes_verified": final_verification[
                "raw_hashes_verified"
            ],
            "result": final_verification["result"],
        },
        "gate_pass_counts": dict(sorted(gate_counts.items())),
        "gate_fail_count": 0,
        "runtime_seconds": {
            "live": numeric_stats(live_seconds),
            "offline_render": numeric_stats(render_seconds),
            "cpu_x264": numeric_stats(encode_seconds),
        },
        "cpfs_publish_mib_s": numeric_stats(cpfs_rates),
    }
    aggregate_path.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines: list[str] = []
    add = lines.append
    add("# Xonotic 0.8.6 World-Model Capture Pilot Report")
    add("")
    add(f"Generated UTC: `{capture.utc_now()}`")
    add("")
    add("## Verdict")
    add("")
    add(
        "**GO for the completed Phase 0, minimum capture chain, and exactly "
        "100 accepted Pilot episodes. STOP before the formal 15,804-episode "
        "batch.**"
    )
    add("")
    add(
        "The passing graphics path is SDL2 `offscreen` -> GLVND/NVIDIA EGL -> "
        "OpenGL 4.6, with renderer `NVIDIA GB300/PCIe`; the locked GPU/driver "
        f"identity is `{lock['platform']['gpu']}`. No DISPLAY, Xorg, "
        "`/dev/dri`, llvmpipe, NVENC, Docker, "
        "or real-time desktop capture was used. Audio used "
        "`SDL_AUDIODRIVER=dummy` while the DarkPlaces sound engine remained "
        "enabled; CPU `libx264` plus FLAC produced the final MKVs."
    )
    add("")
    add("## Phase 0 evidence")
    add("")
    add("| Run | Frames | Samples/channel | Audio events | A/V drift | Max onset error | GPU mean/max | Raw MiB/s | x264 x |")
    add("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for label, row in (("60 s", phase0_60), ("600 s", phase0_600)):
        add(
            f"| {label} | {row['video_frames']} | "
            f"{row['audio_samples_per_channel']} | {row['audio_events']} | "
            f"{row['av_drift_ms']:.3f} ms | "
            f"{row['max_audio_onset_error_ms']:.3f} ms | "
            f"{row['gpu_util_pct_mean']:.2f}% / {row['gpu_util_pct_max']:.2f}% | "
            f"{row['raw_write_mib_s']:.2f} | "
            f"{row['x264_video_seconds_per_wall_second']:.2f} |"
        )
    add("")
    add(
        "Evidence roots: "
        f"`{phase0_60_path.parent}` and `{phase0_600_path.parent}`. "
        "The 60-second visual QA sampled frames at 10 s and 55 s and found "
        "only the scene, first-person weapon, and crosshair."
    )
    add("")
    add("## Source, assets, and implementation lock")
    add("")
    add(f"- Official release: `Xonotic {lock['release']['version']}`")
    add(
        f"- Official release archive SHA256: `{lock['release']['archive_sha256']}`"
    )
    add(
        f"- Official source archive SHA256: `{lock['release']['source_archive_sha256']}`"
    )
    for repo in lock["repositories"]:
        add(
            f"- `{repo['name']}` tag `{repo['tag']}` commit `{repo['commit']}`"
        )
    add(
        f"- Local capture branch `{lock['capture']['branch']}` at "
        f"`{lock['capture']['head_commit']}`; base "
        f"`{lock['capture']['base_commit']}`"
    )
    add(f"- Native ARM64 build: `{lock['capture']['build_path']}`")
    add(f"- Patch series: `{ROOT / 'patches'}`")
    add(f"- Official asset allowlist: `{ROOT / 'assets/OFFICIAL_ASSET_ALLOWLIST.json'}`")
    add(f"- Source/asset lock: `{lock_path}`")
    add(f"- Licenses/COPYING: `{ROOT / 'licenses/upstream-0.8.6'}`")
    add(
        f"- Final SHA256 manifest: `{ROOT / 'manifests/FORMAL_SHA256SUMS.txt'}` "
        "(generated immediately after this report so the report itself is "
        "included), with `.sha256` sidecar."
    )
    add("")
    add("Official runtime packages:")
    add("")
    add("| Package | Bytes | SHA256 |")
    add("|---|---:|---|")
    for package in lock["asset_packages"]:
        add(
            f"| `{package['filename']}` | {package['size_bytes']} | "
            f"`{package['sha256']}` |"
        )
    add("")
    add("## Pilot dataset")
    add("")
    add(f"- Accepted manifest: `{accepted_path}`")
    add(f"- Reject manifest: `{rejects_path}`")
    add(f"- Aggregate QA: `{aggregate_path}`")
    add(f"- Independent full verification: `{final_verification_path}`")
    add(f"- Episode root: `{ROOT / 'pilot/episodes'}`")
    add(f"- Preserved raw root: `{ROOT / 'pilot/raw'}`")
    add(f"- Cursor/browser MP4 preview index: `{preview_index_path}`")
    add("- Split: `pilot` for all 100 rows; no row is train/val/test.")
    add(
        "- Position diversity: 12 official-map anchor pairs with deterministic "
        "bounded XY jitter; 100/100 unique player origins, enemy origins, and "
        "player/enemy position pairs."
    )
    add(
        "- Visual policy: only first-person weapon and crosshair remain. "
        "Damage text (`cl_damagetext=0`), hit indication, health/armor, ammo, "
        "score, timer, kill feed, and chat are disabled and gated from the "
        "render log."
    )
    add(
        "- Target quotas: "
        + ", ".join(
            f"`{name}`={count}" for name, count in capture.TARGET_COUNTS.items()
        )
        + "."
    )
    add(
        "- Actual outcome bins: "
        + ", ".join(f"`{name}`={count}" for name, count in sorted(actual_outcomes.items()))
        + "."
    )
    add(
        "- Telemetry-derived hit-rate bins: "
        + ", ".join(f"`{name}`={count}" for name, count in sorted(hit_rate_bins.items()))
        + "."
    )
    add("")
    add("Every accepted episode contains `episode.json`, `video.mkv`, "
        "`actions.parquet`, `states.parquet`, `events.parquet`, "
        "`frames.parquet`, `audio_events.parquet`, and `qa.json`; the accepted "
        "manifest records SHA256 for formal and raw artifacts.")
    add("")
    add("## Aggregate QA")
    add("")
    add("| Check | Result |")
    add("|---|---|")
    add("| Accepted count / unique IDs | 100 / 100 |")
    add(
        f"| Final collection accepted / rejected | 100 / "
        f"{final_run_rejected}; acceptance "
        f"{100 * final_run_acceptance_rate:.3f}% |"
    )
    add(
        f"| All current-campaign rejects recorded | {len(rejected)} "
        f"(including calibration attempts) |"
    )
    add("| Frames | 32,000 total; exactly 320 for every episode |")
    add("| Audio | 24,000,000 samples/channel total; exactly 240,000 per episode |")
    add("| Frame/audio ratio | exactly 750 samples/frame for every episode |")
    add(f"| Frame -> authoritative tick mapping | {stats(mappings)} |")
    add(f"| Audio onset error | {stats(onset_ms)} ms |")
    add(
        f"| Event linkage | {total_linked}/{total_link_required} linked; "
        f"per episode {stats(linkage)} |"
    )
    add(
        f"| Resource deltas explained | {total_resource_explained}/"
        f"{total_resource_changes} |"
    )
    add(f"| Desired/applied action max error | {stats(action_error)} |")
    add(f"| Renderer identities | `{', '.join(renderers)}` |")
    add(
        "| Spawn diversity | 12 anchor pairs; 100 unique player origins, "
        "100 unique enemy origins, 100 unique pairs |"
    )
    add(
        "| Minimal HUD | 100/100 render-log gates; damage text and hit "
        "indication off |"
    )
    add("| Cursor/browser MP4 previews | 100/100 generated and probed |")
    add(
        f"| Independent SHA256 recheck | "
        f"{final_verification['formal_hashes_verified']} formal + "
        f"{final_verification['raw_hashes_verified']} raw files; pass |"
    )
    add(
        f"| MachineGun successful reload | {len(reload_qas)}/10, each with "
        "`reload_complete`, clip increase, reserve decrease |"
    )
    add(
        f"| Determinism | `{determinism['result']}`; authoritative SHA256 "
        f"`{determinism['authoritative_sha256']}` |"
    )
    add(
        "| Weapon spread determinism | private capture RNG is seeded from the "
        "bound action-file seed header; seed-match gates pass for every episode |"
    )
    add(f"| All per-episode QA gates | {sum(gate_counts.values())} passes, 0 failures |")
    add(f"| Live wall time | {stats(live_seconds)} s |")
    add(f"| Offline render wall time | {stats(render_seconds)} s |")
    add(f"| CPU x264 wall time | {stats(encode_seconds)} s |")
    add(f"| CPFS publish throughput | {stats(cpfs_rates)} MiB/s |")
    add("")
    add("Rejected engineering/Pilot attempts were never placed in the accepted "
        "manifest. All recorded rejection reasons:")
    add("")
    add("| Reason | Count |")
    add("|---|---:|")
    if reject_reasons:
        for reason, count in sorted(reject_reasons.items()):
            add(f"| `{reason}` | {count} |")
    else:
        add("| none | 0 |")
    superseded_roots = sorted((ROOT / "pilot/superseded").glob("*"))
    if superseded_roots:
        add("")
        add(
            "Earlier engineering datasets are preserved for audit but excluded "
            "from the accepted manifest. Superseded roots: "
            + ", ".join(f"`{path}`" for path in superseded_roots)
            + "."
        )
    add("")
    add("## Renderer and pipeline benchmarks")
    add("")
    add("| Renderers | Aggregate FPS | Video s / wall s | GPU mean/max | CPU mean/max | Raw MiB/s | x264 x | CPFS MiB/s | Max A/V drift |")
    add("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in benchmarks:
        add(
            f"| {row['renderer_count']} | {row['aggregate_capture_fps']:.2f} | "
            f"{row['render_video_seconds_per_wall_second']:.3f} | "
            f"{row['gpu_util_pct_mean']:.1f}% / {row['gpu_util_pct_max']:.1f}% | "
            f"{row['render_process_cpu_pct_mean']:.1f}% / "
            f"{row['render_process_cpu_pct_max']:.1f}% | "
            f"{row['raw_write_mib_s']:.2f} | "
            f"{row['x264_video_seconds_per_wall_second']:.3f} | "
            f"{row['cpfs_upload_mib_s']:.2f} | "
            f"{row['av_drift_ms_max']:.3f} ms |"
        )
    add("")
    add(f"Benchmark evidence: `{benchmark_path}`.")
    add("")
    add("## Re-estimated formal-batch ETA")
    add("")
    add(
        f"The planning-only formal workload remains 15,804 episodes, "
        f"{production_video_seconds:,} output seconds = 21.95 output hours. "
        f"No formal episode was generated."
    )
    add("")
    add(
        f"- Measured current serial orchestrator: {observed_per_accept:.2f} "
        f"wall seconds per accepted Pilot episode from `{pilot_wall_source}`. "
        f"With the measured final-run rejection multiplier "
        f"{attempt_multiplier:.4f} ({final_run_rejected} rejected attempts), "
        f"the conservative ETA is **{fmt_seconds(serial_eta_seconds)}**."
    )
    add(
        f"- Best measured renderer-only lower bound: "
        f"{fmt_seconds(renderer_lower_bound)} using "
        f"{best_render['renderer_count']} renderers."
    )
    add(
        f"- Best measured CPU-x264-only lower bound: "
        f"{fmt_seconds(encode_lower_bound)}."
    )
    add(
        f"- Measured media-stage lower bound (slower of render/encode): "
        f"{fmt_seconds(measured_media_lower_bound)}. This is not an "
        "end-to-end promise because dedicated-server/live-demo concurrency "
        "was not benchmarked."
    )
    add(
        f"- Estimated retained raw + formal output at Pilot mean sizes: "
        f"approximately {storage_tib:.2f} TiB before extra logs/checksums."
    )
    add("")
    add("For scheduling, use the conservative serial ETA until a separate "
        "bounded full-pipeline concurrency test proves dedicated-server, "
        "renderer, x264, `./tmp`, and CPFS overlap without changing telemetry "
        "or rejection behavior.")
    add("")
    add("## Remaining risks and next steps")
    add("")
    add("- The 1/2/4/8 test scales offline renderer and encoder work from fixed "
        "Pilot demos; it does not yet prove equivalent scaling for concurrent "
        "authoritative dedicated servers.")
    add("- RGB is not required to be bit-identical across different NVIDIA "
        "driver versions; authoritative telemetry determinism is the locked "
        "reproducibility criterion.")
    add("- Public/commercial release still needs a human legal review of the "
        "official Xonotic asset licenses and redistribution scope, despite "
        "the preserved allowlist, COPYING files, commits, patches, and hashes.")
    add("- The official music PK3 remains present because it is part of the "
        "pinned release archive, but runtime policy disables CD audio, BGM, "
        "announcer, voice/chat/menu/global-notification channels; QA found no "
        "forbidden logged samples.")
    add("- Before formal collection, run a bounded full-pipeline concurrency "
        "gate, reserve CPFS capacity from the measured size estimate, and "
        "freeze driver/build/config hashes. Do not merge `split=pilot` into "
        "future train/val/test.")
    add("")
    add("## Episode paths")
    add("")
    add("| ID | Accepted episode | Preserved raw |")
    add("|---|---|---|")
    for row in accepted:
        add(
            f"| `{row['episode_id']}` | `{row['episode_path']}` | "
            f"`{row['raw_path']}` |"
        )
    add("")
    add("## Stop condition")
    add("")
    add("`PILOT_REPORT.md` is the terminal artifact for this run. The formal "
        "15,804-episode batch and custom-image creation were not started.")
    add("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
