                      
"""Freeze local source provenance and formal artifact checksums."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = Path("./xonotic_capture")
SOURCE = ROOT / "source/release-src-0.8.6/Xonotic"
PATCHES = ROOT / "patches"
LOCK = ROOT / "locks/SOURCE_ASSET_LOCK.json"
FORMAL_SUMS = ROOT / "manifests/FORMAL_SHA256SUMS.txt"
BASE_COMMIT = "ad060a7"


def command_output(command: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def hash_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        rows.append(
            {
                "path": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": capture.sha256_file(path),
            }
        )
    return rows


def source_lock() -> int:
    capture.require_conda()
    if LOCK.exists():
        raise RuntimeError(f"refusing to overwrite source lock: {LOCK}")
    status = command_output(["git", "status", "--porcelain"], cwd=SOURCE)
    if status:
        raise RuntimeError(f"source worktree is dirty:\n{status}")
    head = command_output(["git", "rev-parse", "HEAD"], cwd=SOURCE)
    base = command_output(["git", "rev-parse", BASE_COMMIT], cwd=SOURCE)
    branch = command_output(["git", "branch", "--show-current"], cwd=SOURCE)
    build = capture.build_root()
    build_commit = (build / "SOURCE_COMMIT").read_text().strip()
    if build_commit != head:
        raise RuntimeError(f"build/source mismatch: {build_commit} != {head}")
    if any(PATCHES.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty patch dir: {PATCHES}")
    completed = subprocess.run(
        [
            "git",
            "format-patch",
            "--no-signature",
            "--output-directory",
            str(PATCHES),
            f"{base}..{head}",
        ],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        check=True,
    )
    patch_paths = [
        Path(line.strip())
        for line in completed.stdout.splitlines()
        if line.strip()
    ]
    if not patch_paths:
        raise RuntimeError("git format-patch produced no patches")
    (PATCHES / "series").write_text(
        "".join(f"{path.name}\n" for path in patch_paths),
        encoding="utf-8",
    )

    repositories: list[dict[str, str]] = []
    with (ROOT / "locks/upstream/xonotic-v0.8.6-git-tags.tsv").open(
        newline="", encoding="utf-8"
    ) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            repositories.append(
                {
                    "name": row["repository"],
                    "url": row["url"],
                    "tag": row["tag"],
                    "tag_object_or_commit": row["tag_object_or_commit"],
                    "commit": row["peeled_commit"],
                }
            )
    allowlist = json.loads(
        (ROOT / "assets/OFFICIAL_ASSET_ALLOWLIST.json").read_text()
    )
    license_paths = list((ROOT / "licenses/upstream-0.8.6").glob("*"))
    config_paths = list((ROOT / "configs").glob("*"))
    config_paths += list((ROOT / "configs/actions").glob("*.csv"))
    script_paths = list((ROOT / "scripts").glob("*"))
    build_paths = [
        build / "bin/xonotic-local-dedicated",
        build / "bin/xonotic-local-sdl",
        build / "qc/progs.dat",
        build / "qc/csprogs.dat",
        build / "qc/menu.dat",
        build / "SOURCE_COMMIT",
    ]
    value = {
        "schema_version": "xonotic-source-asset-lock-v1",
        "created_utc": capture.utc_now(),
        "release": {
            "version": allowlist["release"]["version"],
            "archive": allowlist["release"]["archive"],
            "archive_sha256": allowlist["release"]["sha256"],
            "official_archive_sha512": allowlist["release"]["official_sha512"],
            "source_archive": allowlist["source_archive"]["archive"],
            "source_archive_sha256": allowlist["source_archive"]["sha256"],
            "official_source_archive_sha512": allowlist["source_archive"][
                "official_sha512"
            ],
        },
        "repositories": repositories,
        "capture": {
            "branch": branch,
            "base_commit": base,
            "head_commit": head,
            "build_path": str(build),
            "build_commit": build_commit,
            "external_push": False,
        },
        "asset_policy": {
            "allowlist": str(ROOT / "assets/OFFICIAL_ASSET_ALLOWLIST.json"),
            "automatic_downloads": False,
            "dlcache_allowed": False,
            "community_maps": False,
            "maps": allowlist["maps"],
            "enemy_models": allowlist["enemy_models"],
            "weapons": allowlist["weapons"],
        },
        "asset_packages": allowlist["packages"],
        "platform": {
            "architecture": platform.machine(),
            "kernel": platform.release(),
            "os_release": Path("/etc/os-release").read_text(),
            "gpu": command_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ]
            ),
            "opengl_renderer": os.environ.get(
                "XONOTIC_OPENGL_RENDERER",
                "runtime-verified-and-recorded-per-episode",
            ),
            "opengl_renderer_policy": (
                "NVIDIA hardware; exact generation is not fixed; "
                "software renderers are forbidden"
            ),
            "graphics_path": "SDL2 offscreen -> GLVND/NVIDIA EGL -> OpenGL 4.6",
            "audio_path": "SDL_AUDIODRIVER=dummy with DarkPlaces sound engine enabled",
            "video_encoder": "CPU libx264; NVENC forbidden and unused",
        },
        "toolchain": {
            "gcc": command_output(["gcc", "--version"]).splitlines()[0],
            "ld": command_output(["ld", "--version"]).splitlines()[0],
            "make": command_output(["make", "--version"]).splitlines()[0],
            "python": command_output([sys.executable, "--version"]),
            "ffmpeg": command_output(["ffmpeg", "-version"]).splitlines()[0],
            "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
            "conda_explicit_lock": hash_rows(
                [ROOT / "locks/conda-xonotic-capture-explicit.txt"]
            ),
        },
        "licenses_sha256": hash_rows(license_paths),
        "build_sha256": hash_rows(build_paths),
        "configs_sha256": hash_rows(config_paths),
        "scripts_sha256": hash_rows(script_paths),
        "patches_sha256": hash_rows(list(PATCHES.glob("*"))),
    }
    LOCK.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"source_lock={LOCK}")
    print(f"patches={len(patch_paths)}")
    return 0


def formal_paths() -> list[Path]:
    paths: list[Path] = []
    patterns = (
        "pilot/episodes/*/*",
        "manifests/*.jsonl",
        "licenses/upstream-0.8.6/*",
        "locks/SOURCE_ASSET_LOCK.json",
        "locks/conda-xonotic-capture-explicit.txt",
        "locks/upstream/*",
        "configs/*",
        "configs/actions/*",
        "patches/*",
        "qa/*",
        "benchmarks/renderers/**/*",
        "previews/*",
        "phase0/av-tests/phase0-60s/*",
        "phase0/av-tests/phase0-600s/*",
        "scripts/*",
        "assets/OFFICIAL_ASSET_ALLOWLIST.json",
        "XONOTIC_DATA_AND_DEV_PLAN.md",
        "PILOT_REPORT.md",
    )
    for pattern in patterns:
        paths.extend(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(set(paths))


def formal_checksums() -> int:
    capture.require_conda()
    if FORMAL_SUMS.exists() or FORMAL_SUMS.with_suffix(
        FORMAL_SUMS.suffix + ".sha256"
    ).exists():
        raise RuntimeError(f"refusing to overwrite checksum manifest: {FORMAL_SUMS}")
    if not (ROOT / "PILOT_REPORT.md").is_file():
        raise RuntimeError("PILOT_REPORT.md must exist before final checksums")
    paths = formal_paths()
    if not paths:
        raise RuntimeError("no formal files selected")
    with FORMAL_SUMS.open("w", encoding="utf-8") as handle:
        for path in paths:
            digest = capture.sha256_file(path)
            handle.write(f"{digest}  {path.relative_to(ROOT)}\n")
    manifest_hash = capture.sha256_file(FORMAL_SUMS)
    sidecar = FORMAL_SUMS.with_suffix(FORMAL_SUMS.suffix + ".sha256")
    sidecar.write_text(
        f"{manifest_hash}  {FORMAL_SUMS.name}\n",
        encoding="utf-8",
    )
    print(f"formal_files={len(paths)}")
    print(f"manifest={FORMAL_SUMS}")
    print(f"manifest_sha256={manifest_hash}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("command", choices=("source-lock", "formal-checksums"))
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "source-lock":
        return source_lock()
    return formal_checksums()


if __name__ == "__main__":
    raise SystemExit(main())
