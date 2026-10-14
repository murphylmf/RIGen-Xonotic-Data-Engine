                      
"""Persist all engineering/preflight raw attempts before freeing ./tmp."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = Path("./xonotic_capture")
TMP_RAW = Path("./tmp/xonotic_capture/raw")
DESTINATION_ROOT = ROOT / "pilot/preflight"
MANIFEST = ROOT / "manifests/preflight.jsonl"
EVIDENCE_WITH_STAGE_PATHS = (
    ROOT / "qa/determinism.json",
    ROOT / "qa/representative_validation.json",
    ROOT / "qa/representative_validation_final.json",
    ROOT / "qa/shotgun_kill_validation_final.json",
    ROOT / "qa/shotgun_long_range_kill_final.json",
    ROOT / "qa/anchor_validation.json",
    ROOT / "qa/hud_validation.json",
)


def rewrite_archived_stage_paths() -> None:
    """Keep final evidence references valid after verified ./tmp cleanup."""

    temporary_prefix = str(TMP_RAW) + "/"

    def rewrite(value: object) -> object:
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, str) and value.startswith(temporary_prefix):
            relative = Path(value).relative_to(TMP_RAW)
            archived = DESTINATION_ROOT / relative
            attempt_destination = DESTINATION_ROOT / relative.parts[0]
            if attempt_destination.is_dir():
                return str(archived)
        return value

    for evidence_path in EVIDENCE_WITH_STAGE_PATHS:
        if not evidence_path.is_file():
            continue
        original = json.loads(evidence_path.read_text(encoding="utf-8"))
        updated = rewrite(original)
        if updated == original:
            continue
        temporary = evidence_path.with_suffix(evidence_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(updated, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, evidence_path)


def main() -> int:
    capture.require_conda()
    running = subprocess.run(
        ["pgrep", "-f", r"xonotic-local-(sdl|dedicated)"],
        capture_output=True,
        text=True,
        check=False,
    )
    if running.returncode == 0 and running.stdout.strip():
        raise RuntimeError(
            f"refusing to archive while Xonotic is running: "
            f"{running.stdout.strip()}"
        )
    stages = sorted(
        path
        for path in TMP_RAW.glob("pilot_*")
        if path.is_dir()
    )
    if not stages:
        print("preflight_archive_complete stages=0")
        return 0
    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)
    for index, stage in enumerate(stages, 1):
        destination = DESTINATION_ROOT / stage.name
        temporary = DESTINATION_ROOT / f".{stage.name}.tmp"
        if destination.exists() or temporary.exists():
            raise RuntimeError(
                f"refusing to overwrite preflight archive: "
                f"{destination} or {temporary}"
            )
        print(
            f"archive {index}/{len(stages)} stage={stage.name}",
            flush=True,
        )
        started = time.monotonic()
        shutil.copytree(stage, temporary)
        hashes: dict[str, str] = {}
        copied_bytes = 0
        for source in sorted(path for path in stage.rglob("*") if path.is_file()):
            relative = source.relative_to(stage)
            destination_file = temporary / relative
            digest = capture.sha256_file(source)
            if digest != capture.sha256_file(destination_file):
                raise RuntimeError(
                    f"preflight archive hash mismatch: {destination_file}"
                )
            hashes[str(relative)] = digest
            copied_bytes += source.stat().st_size
        os.rename(temporary, destination)
        (destination / "ARCHIVE_SHA256.json").write_text(
            json.dumps(hashes, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        elapsed = time.monotonic() - started
        capture.append_jsonl(
            MANIFEST,
            {
                "schema_version": "xonotic-preflight-archive-v1",
                "attempt_id": stage.name,
                "path": str(destination),
                "files": len(hashes),
                "bytes": copied_bytes,
                "copy_and_verify_seconds": elapsed,
                "copy_and_verify_mib_s": (
                    copied_bytes / (1024 * 1024) / elapsed if elapsed else 0
                ),
                "artifacts_sha256_path": str(
                    destination / "ARCHIVE_SHA256.json"
                ),
                "archived_utc": capture.utc_now(),
            },
        )
        resolved = stage.resolve()
        if resolved.parent != TMP_RAW.resolve():
            raise RuntimeError(f"unsafe preflight cleanup target: {resolved}")
        shutil.rmtree(resolved)
    rewrite_archived_stage_paths()
    print(f"preflight_archive_complete stages={len(stages)}")
    print(f"manifest={MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
