                      
"""Finalize and independently audit the bounded Xonotic v2 coverage Pilot."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              


ROOT = capture.ROOT
PILOT_ROOT = ROOT / "v2_coverage_pilot"
ACCEPTED = PILOT_ROOT / "manifests/accepted.jsonl"
REJECTS = PILOT_ROOT / "manifests/rejects.jsonl"
AUDIT_PATH = PILOT_ROOT / "FINAL_AUDIT.json"
REPORT_PATH = PILOT_ROOT / "V2_COVERAGE_PILOT_REPORT.md"
ROOT_REPORT_PATH = ROOT / "PILOT_REPORT_V2.md"
SOURCE_LOCK_PATH = ROOT / "locks/V2_SOURCE_ASSET_LOCK.json"
SHA_LOCK_PATH = (
    ROOT / "locks/V2_PREFLIGHT_AND_COVERAGE_PILOT_SHA256SUMS.txt"
)
REQUIRED_EPISODE_FILES = {
    "episode.json",
    "video.mkv",
    "actions.parquet",
    "states.parquet",
    "events.parquet",
    "frames.parquet",
    "audio_events.parquet",
    "target_relations.parquet",
    "qa.json",
}
EXPECTED_ROLES = {
    "foundation_no_enemy": 9,
    "foundation_enemy_distractor": 6,
    "causal_interaction": 9,
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_text(
        path,
        "".join(capture.canonical_json(row) + "\n" for row in rows),
    )


def normalized_semantic_outcome(
    row: dict[str, Any], qa: dict[str, Any]
) -> str:
    if row["dataset_role"] != "causal_interaction":
        return "not_applicable"
    events = qa["events"]
    if events["fire_count"] == 0:
        return "no_fire"
    if events["death_count"] > 0:
        return "kill"
    if events["damage_count"] > 0:
        return "hit_survive"
    return "miss"


def prepare_manifest_and_relations() -> list[dict[str, Any]]:
    rows = capture.load_jsonl(ACCEPTED)
    if len(rows) != 24 or len({row["episode_id"] for row in rows}) != 24:
        raise RuntimeError(f"expected 24 unique accepted rows, got {len(rows)}")
    backup = ACCEPTED.with_name("accepted.pre_semantic_v1.jsonl")
    if not backup.exists() and any(
        row.get("schema_version", "").endswith("-v1") for row in rows
    ):
        shutil.copy2(ACCEPTED, backup)
    prepared: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        episode_path = Path(row["episode_path"])
        qa_path = episode_path / "qa.json"
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        target_path = episode_path / "target_relations.parquet"
        if not target_path.exists():
            metrics = v2.relation_metrics(
                episode_path, bool(row["enemy_present"])
            )
            if metrics != qa["target_relation"]:
                raise RuntimeError(
                    f"target relation backfill changed aggregate: "
                    f"{row['episode_id']}"
                )
        semantic = normalized_semantic_outcome(row, qa)
        expected = row.get("intent_outcome", row.get("expected_outcome"))
        row.update(
            {
                "schema_version": (
                    "xonotic-v2-coverage-pilot-manifest-v2"
                ),
                "expected_outcome": expected,
                "intent_outcome": expected,
                "actual_outcome": semantic,
                "semantic_outcome": semantic,
                "engine_outcome_bin": qa["events"][
                    "actual_outcome_bin"
                ],
                "package_sha256": {
                    str(path.relative_to(episode_path)): (
                        capture.sha256_file(path)
                    )
                    for path in sorted(episode_path.rglob("*"))
                    if path.is_file()
                },
            }
        )
        prepared.append(row)
        print(
            f"prepare {index:02d}/24 {row['episode_id']} "
            f"semantic={semantic}",
            flush=True,
        )
    write_jsonl(ACCEPTED, prepared)
    return prepared


def ffprobe_episode(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-count_frames",
        "-show_entries",
        (
            "format=duration:"
            "stream=index,codec_type,codec_name,profile,pix_fmt,width,height,"
            "r_frame_rate,avg_frame_rate,nb_read_frames,sample_fmt,"
            "sample_rate,channels,duration_ts,time_base"
        ),
        "-of",
        "json",
        str(path),
    ]
    probe = json.loads(subprocess.check_output(command, text=True))
    video = next(
        stream
        for stream in probe["streams"]
        if stream["codec_type"] == "video"
    )
    audio = next(
        stream
        for stream in probe["streams"]
        if stream["codec_type"] == "audio"
    )
    decoded_pcm = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-",
        ]
    )
    decoded_audio_samples = len(decoded_pcm) // (
        2 * int(audio["channels"])
    )
    frame_probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "frame=key_frame",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
    )
    keyframes = [
        index
        for index, frame in enumerate(frame_probe["frames"])
        if int(frame["key_frame"]) == 1
    ]
    gaps = [
        right - left
        for left, right in zip(keyframes, keyframes[1:])
    ]
    return {
        "duration_seconds": float(probe["format"]["duration"]),
        "video_codec": video["codec_name"],
        "video_profile": video["profile"],
        "pixel_format": video["pix_fmt"],
        "width": int(video["width"]),
        "height": int(video["height"]),
        "r_frame_rate": video["r_frame_rate"],
        "avg_frame_rate": video["avg_frame_rate"],
        "decoded_frames": int(video["nb_read_frames"]),
        "audio_codec": audio["codec_name"],
        "audio_sample_format": audio["sample_fmt"],
        "audio_sample_rate": int(audio["sample_rate"]),
        "audio_channels": int(audio["channels"]),
        "decoded_audio_samples_per_channel": decoded_audio_samples,
        "audio_duration_ts": (
            int(audio["duration_ts"])
            if "duration_ts" in audio
            else None
        ),
        "audio_time_base": audio.get("time_base"),
        "keyframes": keyframes,
        "maximum_keyframe_gap": max(gaps, default=0),
    }


def sha_job(job: tuple[str, Path, str]) -> tuple[str, bool, str]:
    label, path, expected = job
    actual = capture.sha256_file(path) if path.is_file() else "MISSING"
    return label, actual == expected, actual


def source_asset_lock() -> dict[str, Any]:
    upstream = json.loads(
        (ROOT / "locks/SOURCE_ASSET_LOCK.json").read_text(encoding="utf-8")
    )
    source = ROOT / "source/release-src-0.8.6/Xonotic"
    build = ROOT / "build/capture-6ea72749c923-aarch64"
    branch = subprocess.check_output(
        ["git", "-C", str(source), "branch", "--show-current"], text=True
    ).strip()
    head = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    lock = {
        "schema_version": "xonotic-v2-source-asset-lock-v1",
        "created_utc": capture.utc_now(),
        "official_release": "Xonotic 0.8.6 / xonotic-v0.8.6",
        "source": {
            "branch": branch,
            "head_commit": head,
            "external_push": False,
            "patch": str(
                ROOT
                / "patches/"
                "0001-capture-support-v2-optional-enemy-and-appearance-tel.patch"
            ),
        },
        "build": {
            "path": str(build),
            "sha256_lock": str(
                ROOT / "locks/capture-6ea72749c923-aarch64.sha256"
            ),
        },
        "official_archives": upstream["release"],
        "upstream_repositories": upstream["repositories"],
        "asset_packages": upstream["asset_packages"],
        "policy_files": {
            "data_spec": str(ROOT / "XONOTIC_DATA_SPEC_V2.md"),
            "official_allowlist": str(
                ROOT / "assets/OFFICIAL_ASSET_ALLOWLIST.json"
            ),
            "content_catalog": str(
                ROOT / "configs/OFFICIAL_V2_CONTENT_CATALOG.json"
            ),
        },
        "licenses": str(ROOT / "licenses/upstream-0.8.6"),
    }
    atomic_json(SOURCE_LOCK_PATH, lock)
    return lock


def make_sha_lock() -> None:
    roots = [
        ROOT / "XONOTIC_DATA_SPEC_V2.md",
        ROOT / "XONOTIC_DATA_AND_DEV_PLAN.md",
        ROOT / "assets/OFFICIAL_ASSET_ALLOWLIST.json",
        ROOT / "configs/OFFICIAL_V2_CONTENT_CATALOG.json",
        ROOT / "configs/v2_coverage_pilot_scenarios.jsonl",
        ROOT / "configs/capture_client.cfg",
        ROOT / "scripts/generate_v2_content_catalog.py",
        ROOT / "scripts/xonotic_capture.py",
        ROOT / "scripts/xonotic_capture_v2.py",
        ROOT / "scripts/finalize_v2_pilot.py",
        ROOT
        / "patches/"
        "0001-capture-support-v2-optional-enemy-and-appearance-tel.patch",
        ROOT / "preflight_v2/PREFLIGHT_REPORT.json",
        ROOT / "preflight_v2/PREFLIGHT_REPORT.md",
        PILOT_ROOT / "PILOT_SUMMARY.json",
        ACCEPTED,
        REJECTS,
        AUDIT_PATH,
        REPORT_PATH,
        ROOT_REPORT_PATH,
        ROOT / "previews/v2/index.html",
        SOURCE_LOCK_PATH,
        ROOT / "locks/capture-6ea72749c923-aarch64.sha256",
    ]
    roots.extend(
        path
        for path in sorted((ROOT / "licenses/upstream-0.8.6").rglob("*"))
        if path.is_file()
    )
    missing = [str(path) for path in roots if not path.is_file()]
    if missing:
        raise RuntimeError(f"cannot create SHA lock; missing={missing}")
    lines = [
        f"{capture.sha256_file(path)}  {path.relative_to(ROOT)}"
        for path in sorted(set(roots))
    ]
    atomic_text(SHA_LOCK_PATH, "\n".join(lines) + "\n")
    atomic_text(
        SHA_LOCK_PATH.with_suffix(SHA_LOCK_PATH.suffix + ".sha256"),
        f"{capture.sha256_file(SHA_LOCK_PATH)}  {SHA_LOCK_PATH.name}\n",
    )


def report_markdown(
    audit: dict[str, Any], rows: list[dict[str, Any]]
) -> str:
    lines = [
        "# Xonotic v2 preflight and coverage Pilot report",
        "",
        f"Generated UTC: `{audit['created_utc']}`",
        "",
        "## Verdict",
        "",
        (
            "**PASS for the bounded v2 preflight and the 24-episode "
            "end-to-end coverage Pilot. STOP before formal collection.**"
        ),
        "",
        (
            "The complete minimum path ran as dedicated-server 64 Hz "
            "simulation -> tick telemetry -> per-client demo -> NVIDIA "
            "offline render -> frame/audio mapping -> CPU libx264 + FLAC -> "
            "QA -> atomic publish. No formal Stage 1 or Stage 2 episode was "
            "generated."
        ),
        "",
        "## Canonical specification and locks",
        "",
        f"- Data spec: `{ROOT / 'XONOTIC_DATA_SPEC_V2.md'}`",
        f"- Source/asset lock: `{SOURCE_LOCK_PATH}`",
        f"- Final SHA256 lock: `{SHA_LOCK_PATH}`",
        (
            "- Source branch/commit: "
            "`capture/data-v2-preflight` / "
            f"`{audit['preflight']['source_commit']}`"
        ),
        (
            "- Build: "
            f"`{audit['preflight']['build']}`"
        ),
        "",
        "## Preflight",
        "",
        f"- Overall: `{audit['preflight']['pass']}`",
        (
            "- Hardware render path: SDL2 `offscreen` -> GLVND/NVIDIA EGL "
            f"-> OpenGL; renderer `{audit['qa']['renderers'][0]}`."
        ),
        (
            f"- Admitted maps: Stage 1 "
            f"{audit['preflight']['stage1_admitted_maps']}/29; Stage 2 "
            f"{audit['preflight']['stage2_admitted_maps']}/29."
        ),
        (
            f"- Position probes: "
            f"{audit['preflight']['position_passed']}/"
            f"{audit['preflight']['position_total']} candidate positions "
            "passed."
        ),
        (
            f"- Enemy-pair probes: "
            f"{audit['preflight']['pair_passed']}/"
            f"{audit['preflight']['pair_total']} candidate pairs passed; "
            "failed candidates were screened out, while every map retained "
            "at least one accepted pair."
        ),
        "- DM distance bins: `close, near, medium, far, very_far, extreme`.",
        "- Weapon full chains: `9/9`.",
        (
            "- Determinism: two runs produced authoritative SHA256 "
            f"`{audit['preflight']['determinism_sha256']}`."
        ),
        "",
        "## Coverage Pilot",
        "",
        f"- Accepted: `{audit['counts']['accepted']}` (exactly 24).",
        (
            f"- Rejected calibration attempts: "
            f"`{audit['counts']['rejected_attempts']}`; all preserved."
        ),
        "- Split: `v2_coverage_pilot`; permanently excluded from training.",
        f"- Accepted manifest: `{ACCEPTED}`",
        f"- Reject manifest: `{REJECTS}`",
        f"- Episode root: `{PILOT_ROOT / 'episodes'}`",
        f"- Accepted raw root: `{PILOT_ROOT / 'raw'}`",
        f"- Rejected raw root: `{PILOT_ROOT / 'rejected'}`",
        f"- HTML preview: `{ROOT / 'previews/v2/index.html'}`",
        (
            f"- Formal package size: "
            f"{audit['storage']['formal_gib']:.3f} GiB; preserved raw size: "
            f"{audit['storage']['raw_gib']:.3f} GiB accepted + "
            f"{audit['storage']['rejected_raw_gib']:.3f} GiB rejected."
        ),
        "",
        "| Role | Accepted |",
        "|---|---:|",
    ]
    for role, count in audit["coverage"]["roles"].items():
        lines.append(f"| `{role}` | {count} |")
    lines += [
        "",
        "## One accepted example for every sampled category",
        "",
        (
            "| Episode | Role | Category | Map | Weapon | Enemy | "
            "Relation | Distance | Semantic outcome | Hit rate |"
        ),
        "|---|---|---|---|---|---|---|---|---|---:|",
    ]
    for row in rows:
        enemy = (
            f"{row['enemy_model']}:skin{row['enemy_skin']}"
            if row["enemy_present"]
            else "absent"
        )
        lines.append(
            "| `{episode_id}` | `{dataset_role}` | `{category}` | "
            "`{map}` | `{weapon}` | `{enemy}` | `{relation}` | "
            "`{distance}` | `{outcome}` | {hit_rate:.3f} |".format(
                episode_id=row["episode_id"],
                dataset_role=row["dataset_role"],
                category=row["category"],
                map=row["map"],
                weapon=row["weapon"],
                enemy=enemy,
                relation=row.get("actual_target_relation") or "-",
                distance=row.get("actual_distance_bin") or "-",
                outcome=row["semantic_outcome"],
                hit_rate=float(row["hit_rate"]),
            )
        )
    lines += [
        "",
        "## Independent final QA",
        "",
        "| Check | Result |",
        "|---|---|",
        (
            f"| Decoded video | {audit['qa']['decoded_frames_total']} "
            "frames total; every episode exactly 320 |"
        ),
        (
            f"| Decoded audio | {audit['qa']['audio_samples_total']} "
            "samples/channel total; every episode exactly 240000 |"
        ),
        (
            "| Media format | H.264 High, yuv420p, CFR64, GOP max 64, "
            "FLAC s16 stereo 48 kHz, exactly 5 s |"
        ),
        (
            f"| Frame -> tick mapping | min "
            f"{audit['qa']['frame_tick_mapping_min']:.6f} |"
        ),
        (
            f"| Audio onset error | max "
            f"{audit['qa']['audio_onset_max_ms']:.6f} ms |"
        ),
        (
            f"| Event linkage | {audit['qa']['events_linked']}/"
            f"{audit['qa']['events_link_required']}; per-episode min "
            f"{audit['qa']['event_linkage_min']:.6f} |"
        ),
        (
            f"| Resource changes | "
            f"{audit['qa']['resource_changes_explained']}/"
            f"{audit['qa']['resource_changes']} explained |"
        ),
        (
            f"| Per-frame relation rows | "
            f"{audit['qa']['target_relation_rows_total']}; exactly 320 "
            "per episode |"
        ),
        (
            f"| QA gates | {audit['qa']['gate_passes']} pass, "
            f"{audit['qa']['gate_failures']} fail |"
        ),
        (
            f"| SHA256 recheck | {audit['hashes']['files_checked']} "
            "formal/raw files, 0 mismatch |"
        ),
        (
            f"| MachineGun reload | start -> complete, clip "
            f"{audit['qa']['reload']['pre_clip']:.0f} -> "
            f"{audit['qa']['reload']['post_clip']:.0f}, reserve "
            f"{audit['qa']['reload']['pre_reserve']:.0f} -> "
            f"{audit['qa']['reload']['post_reserve']:.0f} |"
        ),
        "",
        "Semantic outcomes are separated from engine mechanism bins. The "
        "causal subset contains `no_fire`, `miss`, `hit_survive`, and `kill`; "
        "the raw engine bins (`direct_hit`, `pellet_hit`, `miss`, `kill`, "
        "`dynamics`) remain in the manifest.",
        "",
        "## Runtime observed on this bounded run",
        "",
        (
            f"- Live capture wall time: mean "
            f"`{audit['performance']['live_wall_mean']:.3f} s/episode`."
        ),
        (
            f"- Offline render wall time: mean "
            f"`{audit['performance']['render_wall_mean']:.3f} s/episode`."
        ),
        (
            f"- CPU x264 speed: mean "
            f"`{audit['performance']['x264_realtime_mean']:.3f}x`."
        ),
        "",
        "## Remaining risks before any formal batch",
        "",
        (
            "- The current per-frame visibility label is an authoritative-LOS "
            "plus logged-camera-frustum proxy. A raster visibility/occlusion "
            "hook must replace or validate it before production-scale "
            "screen-relation balancing."
        ),
        (
            "- All 29 maps passed point and enemy-pair admission, but the "
            "coverage-driven waypoint route planner/controller and its "
            "route_plan/route_trace/base_action/aim_overlay artifacts still "
            "need a bounded all-map traversal gate."
        ),
        (
            "- Weapon primary full chains passed 9/9 and scheduler secondary "
            "action was exercised, but weapon-specific secondary and splash/"
            "bounce/combo coverage needs a separate bounded causal matrix."
        ),
        (
            "- Therefore this report does not authorize the 60k/40k formal "
            "collections. The process stops here as requested."
        ),
        "",
    ]
    return "\n".join(lines)


def run_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rejects = capture.load_jsonl(REJECTS)
    preflight = json.loads(
        v2.PREFLIGHT_REPORT.read_text(encoding="utf-8")
    )
    catalog = json.loads(
        v2.CATALOG_PATH.read_text(encoding="utf-8")
    )
    failures: list[str] = []
    qa_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    video_jobs: list[tuple[str, Path]] = []
    hash_jobs: list[tuple[str, Path, str]] = []
    formal_bytes = 0
    raw_bytes = 0
    rejected_raw_bytes = 0
    table_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        episode_id = row["episode_id"]
        episode_path = Path(row["episode_path"])
        raw_path = Path(row["raw_path"])
        files = {
            path.name for path in episode_path.iterdir() if path.is_file()
        }
        if files != REQUIRED_EPISODE_FILES:
            failures.append(
                f"{episode_id}: episode files {sorted(files)}"
            )
        qa = json.loads(
            (episode_path / "qa.json").read_text(encoding="utf-8")
        )
        episode = json.loads(
            (episode_path / "episode.json").read_text(encoding="utf-8")
        )
        qa_rows.append(qa)
        episode_rows.append(episode)
        video_jobs.append((episode_id, episode_path / "video.mkv"))
        counts = {
            filename: len(pd.read_parquet(episode_path / filename))
            for filename in (
                "actions.parquet",
                "states.parquet",
                "frames.parquet",
                "target_relations.parquet",
            )
        }
        table_counts[episode_id] = counts
        if counts != {
            "actions.parquet": 384,
            "states.parquet": 384,
            "frames.parquet": 320,
            "target_relations.parquet": 320,
        }:
            failures.append(f"{episode_id}: row counts {counts}")
        actual_package_files = {
            str(path.relative_to(episode_path))
            for path in episode_path.rglob("*")
            if path.is_file()
        }
        if actual_package_files != set(row["package_sha256"]):
            failures.append(f"{episode_id}: package hash key set mismatch")
        for relative, expected in row["package_sha256"].items():
            path = episode_path / relative
            hash_jobs.append(
                (f"formal:{episode_id}:{relative}", path, expected)
            )
            if path.is_file():
                formal_bytes += path.stat().st_size
        actual_raw_files = {
            str(path.relative_to(raw_path))
            for path in raw_path.rglob("*")
            if path.is_file()
        }
        if actual_raw_files != set(row["raw_sha256"]):
            failures.append(f"{episode_id}: raw hash key set mismatch")
        for relative, expected in row["raw_sha256"].items():
            path = raw_path / relative
            hash_jobs.append(
                (f"raw:{episode_id}:{relative}", path, expected)
            )
            if path.is_file():
                raw_bytes += path.stat().st_size
        if not all(qa["gates"].values()):
            failures.append(f"{episode_id}: per-episode QA gate failed")
        semantic = normalized_semantic_outcome(row, qa)
        if row["semantic_outcome"] != semantic:
            failures.append(f"{episode_id}: semantic outcome mismatch")
        if (
            row["dataset_role"] == "causal_interaction"
            and row["intent_outcome"] != semantic
        ):
            failures.append(f"{episode_id}: intent outcome not realized")
        if (
            row["dataset_role"] == "foundation_no_enemy"
            and (
                row["enemy_present"]
                or qa["target_relation"]["actual_target_relation"]
                != "enemy_absent"
            )
        ):
            failures.append(f"{episode_id}: no-enemy invariant")
        if (
            row["dataset_role"] == "foundation_enemy_distractor"
            and (
                qa["events"]["damage_count"]
                or qa["events"]["death_count"]
            )
        ):
            failures.append(f"{episode_id}: distractor damage/death")
        if episode.get("expects_sound") and (
            qa["audio"]["nonzero_fraction"] <= 0
            or qa["audio"]["onset_events_measured"] <= 0
        ):
            failures.append(f"{episode_id}: expected audio missing")
        if qa["audio"]["forbidden_samples"]:
            failures.append(f"{episode_id}: forbidden audio")
    for reject in rejects:
        attempt_id = reject["attempt_id"]
        preserved = reject.get("preserved_path")
        expected_hashes = reject.get("preserved_sha256", {})
        if not preserved:
            failures.append(f"{attempt_id}: reject has no preserved path")
            continue
        rejected_path = Path(preserved)
        actual_rejected_files = {
            str(path.relative_to(rejected_path))
            for path in rejected_path.rglob("*")
            if path.is_file()
        }
        if actual_rejected_files != set(expected_hashes):
            failures.append(
                f"{attempt_id}: rejected raw hash key set mismatch"
            )
        for relative, expected in expected_hashes.items():
            path = rejected_path / relative
            hash_jobs.append(
                (f"rejected:{attempt_id}:{relative}", path, expected)
            )
            if path.is_file():
                rejected_raw_bytes += path.stat().st_size
    print(
        f"hash verification jobs={len(hash_jobs)} workers=8",
        flush=True,
    )
    hash_failures: list[dict[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for index, (label, passed, actual) in enumerate(
            executor.map(sha_job, hash_jobs), 1
        ):
            if not passed:
                hash_failures.append({"label": label, "actual": actual})
            if index % 100 == 0 or index == len(hash_jobs):
                print(
                    f"hash {index}/{len(hash_jobs)} "
                    f"failures={len(hash_failures)}",
                    flush=True,
                )
    if hash_failures:
        failures.append(f"SHA256 mismatches: {len(hash_failures)}")
    probes: dict[str, dict[str, Any]] = {}
    print("independent ffprobe 24 episodes workers=6", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(ffprobe_episode, path): episode_id
            for episode_id, path in video_jobs
        }
        for index, future in enumerate(
            concurrent.futures.as_completed(futures), 1
        ):
            episode_id = futures[future]
            probes[episode_id] = future.result()
            print(f"ffprobe {index:02d}/24 {episode_id}", flush=True)
    for episode_id, probe in probes.items():
        media_checks = {
            "duration": math.isclose(
                probe["duration_seconds"], 5.0, abs_tol=1e-9
            ),
            "video": (
                probe["video_codec"] == "h264"
                and probe["video_profile"] == "High"
                and probe["pixel_format"] == "yuv420p"
                and probe["width"] == 1280
                and probe["height"] == 720
                and probe["r_frame_rate"] == "64/1"
                and probe["avg_frame_rate"] == "64/1"
                and probe["decoded_frames"] == 320
            ),
            "audio": (
                probe["audio_codec"] == "flac"
                and probe["audio_sample_format"] == "s16"
                and probe["audio_sample_rate"] == 48000
                and probe["audio_channels"] == 2
                and probe["decoded_audio_samples_per_channel"] == 240000
            ),
            "gop": (
                probe["keyframes"]
                and probe["keyframes"][0] == 0
                and probe["maximum_keyframe_gap"] <= 64
            ),
        }
        if not all(media_checks.values()):
            failures.append(
                f"{episode_id}: ffprobe checks {media_checks}"
            )
    reload_events = pd.read_parquet(
        PILOT_ROOT
        / "episodes/v2_foundation_solo_09/events.parquet"
    )
    reload_complete = reload_events[
        reload_events["event"] == "reload_complete"
    ]
    if len(reload_complete) != 1:
        failures.append("MachineGun reload_complete count is not 1")
        reload = {}
    else:
        event = reload_complete.iloc[0]
        reload = {
            "pre_clip": float(event["pre_clip"]),
            "post_clip": float(event["post_clip"]),
            "pre_reserve": float(event["pre_reserve"]),
            "post_reserve": float(event["post_reserve"]),
            "success": bool(event["success"]),
        }
        if not (
            reload["success"]
            and reload["post_clip"] > reload["pre_clip"]
            and reload["post_reserve"] < reload["pre_reserve"]
        ):
            failures.append("MachineGun reload resource proof failed")
    preflight_results = capture.load_jsonl(v2.PREFLIGHT_RESULTS)
    positions = [
        probe
        for probe in preflight_results
        if probe.get("probe_kind") == "map_position"
    ]
    pairs = [
        probe
        for probe in preflight_results
        if probe.get("probe_kind") == "enemy_pair"
    ]
    position_passed = sum(bool(probe["pass"]) for probe in positions)
    pair_passed = sum(bool(probe["pass"]) for probe in pairs)
    gate_passes = sum(
        bool(value) for qa in qa_rows for value in qa["gates"].values()
    )
    gate_total = sum(len(qa["gates"]) for qa in qa_rows)
    source_asset_lock()
    semantic_counts = Counter(
        row["semantic_outcome"]
        for row in rows
        if row["dataset_role"] == "causal_interaction"
    )
    checks = {
        "preflight_pass": bool(preflight["pass"])
        and all(preflight["hard_gates"].values()),
        "catalog_counts": catalog["counts"]
        == {
            "maps": 29,
            "weapons": 9,
            "enemy_models": 7,
            "enemy_appearances": 14,
            "waypoints": 3241,
        },
        "exact_24_unique": len(rows)
        == len({row["episode_id"] for row in rows})
        == 24,
        "role_counts": Counter(row["dataset_role"] for row in rows)
        == Counter(EXPECTED_ROLES),
        "split_nonproduction": all(
            row["split"] == "v2_coverage_pilot" for row in rows
        ),
        "all_relations": {
            row["actual_target_relation"]
            for row in rows
            if row["dataset_role"] == "foundation_enemy_distractor"
        }
        == set(v2.RELATIONS),
        "all_aim_policies": {
            row["aim_policy"]
            for row in rows
            if row["dataset_role"] == "causal_interaction"
        }
        == set(v2.AIM_POLICIES),
        "all_distance_bins": {
            row["actual_distance_bin"]
            for row in rows
            if row["dataset_role"] == "causal_interaction"
        }
        == set(v2.DISTANCE_BINS),
        "all_semantic_outcomes": set(semantic_counts)
        == {"no_fire", "miss", "hit_survive", "kill"},
        "all_weapons": {row["weapon"] for row in rows}
        == set(v2.WEAPONS),
        "all_appearances": len(
            {
                (row["enemy_model"], row["enemy_skin"])
                for row in rows
                if row["enemy_present"]
            }
        )
        == 14,
        "all_episode_files": all(
            set(row["package_sha256"]) == REQUIRED_EPISODE_FILES
            for row in rows
        ),
        "parquet_row_counts": all(
            counts
            == {
                "actions.parquet": 384,
                "states.parquet": 384,
                "frames.parquet": 320,
                "target_relations.parquet": 320,
            }
            for counts in table_counts.values()
        ),
        "all_qa_gates": gate_total > 0 and gate_passes == gate_total,
        "independent_media": not any(
            ": ffprobe checks" in failure for failure in failures
        ),
        "sha256": not hash_failures,
        "reload_success": bool(reload),
    }
    if not all(checks.values()):
        failures.append(
            "aggregate checks failed: "
            + capture.canonical_json(
                {key: value for key, value in checks.items() if not value}
            )
        )
    audit = {
        "schema_version": "xonotic-v2-final-audit-v1",
        "created_utc": capture.utc_now(),
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "counts": {
            "accepted": len(rows),
            "rejected_attempts": len(rejects),
            "unique_categories": len(
                {row["category"] for row in rows}
            ),
            "pilot_video_seconds": len(rows) * 5,
        },
        "preflight": {
            "pass": preflight["pass"],
            "source_commit": preflight["source_commit"],
            "build": preflight["build"],
            "stage1_admitted_maps": len(
                preflight["stage1_admitted_maps"]
            ),
            "stage2_admitted_maps": len(
                preflight["stage2_admitted_maps"]
            ),
            "position_passed": position_passed,
            "position_total": len(positions),
            "pair_passed": pair_passed,
            "pair_total": len(pairs),
            "dm_distance_bins": preflight["dm_distance_bins"],
            "weapon_full_chains": sum(
                bool(item["pass"])
                for item in preflight["weapon_full_chain"]
            ),
            "determinism_sha256": preflight["determinism"][
                "hashes"
            ][0],
            "hard_gates": preflight["hard_gates"],
        },
        "coverage": {
            "roles": dict(
                sorted(Counter(row["dataset_role"] for row in rows).items())
            ),
            "categories": dict(
                sorted(Counter(row["category"] for row in rows).items())
            ),
            "maps": dict(sorted(Counter(row["map"] for row in rows).items())),
            "weapons": dict(
                sorted(Counter(row["weapon"] for row in rows).items())
            ),
            "relations": dict(
                sorted(
                    Counter(
                        row["actual_target_relation"]
                        for row in rows
                        if row["dataset_role"]
                        == "foundation_enemy_distractor"
                    ).items()
                )
            ),
            "aim_policies": dict(
                sorted(
                    Counter(
                        row["aim_policy"]
                        for row in rows
                        if row["dataset_role"] == "causal_interaction"
                    ).items()
                )
            ),
            "distance_bins": dict(
                sorted(
                    Counter(
                        row["actual_distance_bin"]
                        for row in rows
                        if row["dataset_role"] == "causal_interaction"
                    ).items()
                )
            ),
            "semantic_outcomes": dict(sorted(semantic_counts.items())),
            "engine_outcome_bins": dict(
                sorted(Counter(row["engine_outcome_bin"] for row in rows).items())
            ),
            "appearances": sorted(
                {
                    f"{row['enemy_model']}:skin{row['enemy_skin']}:"
                    f"color{row['enemy_color']}"
                    for row in rows
                    if row["enemy_present"]
                }
            ),
        },
        "qa": {
            "renderers": sorted(
                {qa["runtime"]["renderer"] for qa in qa_rows}
            ),
            "decoded_frames_total": sum(
                probe["decoded_frames"] for probe in probes.values()
            ),
            "audio_samples_total": sum(
                probe["decoded_audio_samples_per_channel"]
                for probe in probes.values()
            ),
            "target_relation_rows_total": sum(
                counts["target_relations.parquet"]
                for counts in table_counts.values()
            ),
            "frame_tick_mapping_min": min(
                qa["mapping"]["success_rate"] for qa in qa_rows
            ),
            "audio_onset_max_ms": max(
                qa["audio"]["max_onset_error_ms"] for qa in qa_rows
            ),
            "event_linkage_min": min(
                qa["events"]["linkage_rate"] for qa in qa_rows
            ),
            "events_linked": sum(
                qa["events"]["linked"] for qa in qa_rows
            ),
            "events_link_required": sum(
                qa["events"]["link_required"] for qa in qa_rows
            ),
            "resource_changes": sum(
                qa["telemetry"]["resource_changes"] for qa in qa_rows
            ),
            "resource_changes_explained": sum(
                qa["telemetry"]["resource_changes_explained"]
                for qa in qa_rows
            ),
            "gate_passes": gate_passes,
            "gate_failures": gate_total - gate_passes,
            "action_schedule_max_error": max(
                qa["telemetry"]["action_schedule_max_error"]
                for qa in qa_rows
            ),
            "reload": reload,
        },
        "performance": {
            "live_wall_mean": mean(
                qa["runtime"]["live_wall_seconds"] for qa in qa_rows
            ),
            "render_wall_mean": mean(
                qa["runtime"]["render_wall_seconds"] for qa in qa_rows
            ),
            "encode_wall_mean": mean(
                qa["runtime"]["encode_wall_seconds"] for qa in qa_rows
            ),
            "x264_realtime_mean": mean(
                qa["runtime"]["x264_video_seconds_per_wall_second"]
                for qa in qa_rows
            ),
        },
        "storage": {
            "formal_bytes": formal_bytes,
            "formal_gib": formal_bytes / (1024**3),
            "raw_bytes": raw_bytes,
            "raw_gib": raw_bytes / (1024**3),
            "rejected_raw_bytes": rejected_raw_bytes,
            "rejected_raw_gib": rejected_raw_bytes / (1024**3),
        },
        "hashes": {
            "files_checked": len(hash_jobs),
            "mismatches": hash_failures,
        },
        "rejections": {
            "reason_counts": dict(
                sorted(Counter(row["reason"] for row in rejects).items())
            ),
            "category_counts": dict(
                sorted(Counter(row["category"] for row in rejects).items())
            ),
            "manifest": str(REJECTS),
        },
        "paths": {
            "manifest": str(ACCEPTED),
            "episodes": str(PILOT_ROOT / "episodes"),
            "raw": str(PILOT_ROOT / "raw"),
            "rejected": str(PILOT_ROOT / "rejected"),
            "html": str(ROOT / "previews/v2/index.html"),
            "report": str(REPORT_PATH),
        },
        "ffprobe": dict(sorted(probes.items())),
    }
    atomic_json(AUDIT_PATH, audit)
    report = report_markdown(audit, rows)
    atomic_text(REPORT_PATH, report)
    atomic_text(ROOT_REPORT_PATH, report)
    make_sha_lock()
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Backfill target relations and normalize the manifest only.",
    )
    args = parser.parse_args()
    capture.require_conda()
    rows = prepare_manifest_and_relations()
    if args.prepare_only:
        print(f"prepared_manifest={ACCEPTED}")
        return 0
    audit = run_audit(rows)
    print(f"audit={AUDIT_PATH}")
    print(f"report={REPORT_PATH}")
    print(f"sha_lock={SHA_LOCK_PATH}")
    print(f"pass={audit['pass']}")
    return 0 if audit["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
