                      
"""Generate lightweight Cursor/browser MP4 previews for accepted episodes."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path("./xonotic_capture")
ACCEPTED = ROOT / "manifests/accepted.jsonl"
PREVIEWS = ROOT / "previews"
INDEX = PREVIEWS / "PREVIEW_INDEX.md"


def load_accepted() -> list[dict[str, object]]:
    if not ACCEPTED.is_file():
        return []
    rows: list[dict[str, object]] = []
    for line in ACCEPTED.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def preview_contract(path: Path) -> dict[str, object]:
    probe = subprocess.run(
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
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    metadata = json.loads(probe.stdout)
    video = next(
        stream
        for stream in metadata["streams"]
        if stream["codec_type"] == "video"
    )
    audio = next(
        stream
        for stream in metadata["streams"]
        if stream["codec_type"] == "audio"
    )
    duration = float(metadata["format"]["duration"])
    valid = (
        video["codec_name"] == "h264"
        and int(video["width"]) == 1280
        and int(video["height"]) == 720
        and int(video["nb_read_frames"]) == 320
        and audio["codec_name"] == "aac"
        and int(audio["sample_rate"]) == 48_000
        and int(audio["channels"]) == 2
        and abs(duration - 5.0) <= 0.001
    )
    return {
        "valid": valid,
        "video": video,
        "audio": audio,
        "duration": duration,
    }


def make_preview(row: dict[str, object]) -> Path:
    episode_id = str(row["episode_id"])
    source = ROOT / "pilot/episodes" / episode_id / "video.mkv"
    output = PREVIEWS / f"{episode_id}_preview.mp4"
    if output.is_file():
        contract = preview_contract(output)
        if not contract["valid"]:
            raise RuntimeError(
                f"existing preview contract failed episode={episode_id} "
                f"metadata={contract}"
            )
        return output
    if not source.is_file():
        raise FileNotFoundError(source)
    temporary = PREVIEWS / f".{episode_id}_preview.tmp.mp4"
    temporary.unlink(missing_ok=True)
    command = [
        "nice",
        "-n",
        "10",
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-threads",
        "1",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"preview encode failed episode={episode_id} "
            f"returncode={completed.returncode}"
        )
    contract = preview_contract(temporary)
    if not contract["valid"]:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"preview contract failed episode={episode_id} metadata={contract}"
        )
    os.replace(temporary, output)
    return output


def write_index(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Xonotic Pilot MP4 previews",
        "",
        (
            f"Snapshot contains {len(rows)} accepted episodes. These MP4 files "
            "are preview-only: the canonical MKV and raw artifacts are unchanged."
        ),
        "",
        (
            "| Episode | Category | Map | Anchor | Player origin | Weapon | "
            "Actual result | Hit rate | Preview |"
        ),
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        episode_id = str(row["episode_id"])
        preview = PREVIEWS / f"{episode_id}_preview.mp4"
        hit_rate = row.get("hit_rate")
        hit_rate_text = (
            f"{float(hit_rate):.3f}" if hit_rate is not None else "-"
        )
        player_origin = row.get("player_origin", [])
        player_origin_text = (
            ", ".join(f"{float(value):.2f}" for value in player_origin)
            if isinstance(player_origin, list)
            else "-"
        )
        lines.append(
            "| {episode} | {category} | {map_name} | {anchor} | "
            "{player_origin} | {weapon} | {outcome} | "
            "{hit_rate} | [play]({preview}) |".format(
                episode=episode_id,
                category=row.get("target_bin", ""),
                map_name=row.get("map", ""),
                anchor=row.get("anchor_id", ""),
                player_origin=player_origin_text,
                weapon=row.get("weapon", ""),
                outcome=row.get("actual_outcome_bin", ""),
                hit_rate=hit_rate_text,
                preview=preview,
            )
        )
    temporary = INDEX.with_suffix(".md.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, INDEX)


def main() -> int:
    if not os.environ.get("CONDA_PREFIX"):
        raise RuntimeError("run inside the xonotic-capture conda environment")
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    rows = load_accepted()
    for index, row in enumerate(rows, 1):
        output = make_preview(row)
        print(
            f"preview {index}/{len(rows)} episode={row['episode_id']} "
            f"path={output}",
            flush=True,
        )
    write_index(rows)
    print(f"preview_complete count={len(rows)}")
    print(f"index={INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
