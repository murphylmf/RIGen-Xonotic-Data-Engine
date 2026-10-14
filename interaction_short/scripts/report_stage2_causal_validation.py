                      
"""Summarize bounded Stage-2 motion and primary-weapon validation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


def manifest_rows(output_root: Path, filename: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            f"shard-*-of-*/{filename}"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def report(input_manifest: Path, output_root: Path) -> dict[str, Any]:
    planned = capture.load_jsonl(input_manifest)
    accepted = manifest_rows(output_root, "accepted.jsonl")
    rejects = [
        row
        for row in manifest_rows(output_root, "rejects.jsonl")
        if row.get("terminal") is True
    ]
    accepted_by_id = {row["episode_id"]: row for row in accepted}
    reject_by_id = {row["episode_id"]: row for row in rejects}
    results: list[dict[str, Any]] = []
    for row in planned:
        episode_id = row["episode_id"]
        published = accepted_by_id.get(episode_id)
        if published is None:
            rejection = reject_by_id.get(episode_id)
            results.append(
                {
                    "episode_id": episode_id,
                    "candidate_kind": row["candidate_kind"],
                    "weapon": row["weapon"],
                    "enemy_motion": row["enemy_policy"]["name"],
                    "accepted": False,
                    "reason": (
                        rejection.get("reason")
                        if rejection
                        else "unaccounted"
                    ),
                    "detail": (
                        rejection.get("detail") if rejection else None
                    ),
                }
            )
            continue
        episode = Path(published["episode_path"])
        qa = json.loads((episode / "qa.json").read_text(encoding="utf-8"))
        causal = qa["stage2_causal"]
        results.append(
            {
                "episode_id": episode_id,
                "candidate_kind": row["candidate_kind"],
                "weapon": row["weapon"],
                "enemy_motion": row["enemy_policy"]["name"],
                "accepted": True,
                "actual_outcome": causal["actual_outcome"],
                "actual_distance_bin": causal[
                    "actual_distance_bin"
                ],
                "fire_count": causal["event_counts"]["fire_count"],
                "impact_count": causal["event_counts"]["impact_count"],
                "damage_count": causal["event_counts"]["damage_count"],
                "death_count": causal["event_counts"]["death_count"],
                "direct_count": causal["event_counts"]["direct_count"],
                "splash_count": causal["event_counts"]["splash_count"],
                "pellet_count": causal["event_counts"]["pellet_count"],
                "minimum_angular_error_deg": causal[
                    "minimum_angular_error_deg"
                ],
                "renderer": qa["runtime"]["renderer"],
                "frames": qa["video"]["frames"],
                "audio_samples": qa["audio"]["samples_per_channel"],
                "mapping_rate": qa["mapping"]["success_rate"],
                "all_hard_gates": all(qa["hard_gates"].values()),
                "episode_path": str(episode),
            }
        )
    motion = [
        row
        for row in results
        if row["candidate_kind"]
        == "encounter_prototype_certification"
    ]
    weapons = [
        row
        for row in results
        if row["candidate_kind"]
        == "primary_weapon_mechanism_smoke"
    ]
    accounting_pass = (
        len(accepted) + len(rejects) == len(planned)
        and all(
            row["all_hard_gates"]
            for row in results
            if row["accepted"]
        )
    )
    validation_pass = (
        accounting_pass
        and all(row["accepted"] for row in motion)
        and all(row["accepted"] for row in weapons)
    )
    return {
        "schema_version": "xonotic-stage2-causal-validation-report-v1",
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": capture.sha256_file(input_manifest),
        "output_root": str(output_root),
        "planned": len(planned),
        "accepted": len(accepted),
        "terminal_rejects": len(rejects),
        "accounted": len(accepted) + len(rejects),
        "motion": {
            "planned": len(motion),
            "accepted": sum(row["accepted"] for row in motion),
            "by_policy": {
                name: {
                    "accepted": sum(
                        row["accepted"]
                        for row in motion
                        if row["enemy_motion"] == name
                    ),
                    "planned": sum(
                        row["enemy_motion"] == name for row in motion
                    ),
                }
                for name in sorted(
                    {row["enemy_motion"] for row in motion}
                )
            },
        },
        "primary_weapons": {
            "planned": len(weapons),
            "accepted": sum(row["accepted"] for row in weapons),
            "accepted_weapon_names": sorted(
                row["weapon"] for row in weapons if row["accepted"]
            ),
            "rejected_weapon_names": sorted(
                row["weapon"] for row in weapons if not row["accepted"]
            ),
            "actual_outcomes": dict(
                Counter(
                    row["actual_outcome"]
                    for row in weapons
                    if row["accepted"]
                )
            ),
        },
        "results": results,
        "accounting_pass": accounting_pass,
        "pass": validation_pass,
    }


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Stage-2 causal bounded validation",
        "",
        f"- Accounted: {result['accounted']}/{result['planned']}",
        f"- Accepted / terminal reject: "
        f"{result['accepted']} / {result['terminal_rejects']}",
        f"- Motion certificates: {result['motion']['accepted']}/"
        f"{result['motion']['planned']}",
        f"- Primary weapons: {result['primary_weapons']['accepted']}/"
        f"{result['primary_weapons']['planned']}",
        f"- Accounting pass: `{str(result['accounting_pass']).lower()}`",
        f"- Validation pass: `{str(result['pass']).lower()}`",
        "- All artifacts remain `training_admitted=false`.",
        "",
        "| Candidate | kind | weapon | enemy motion | outcome / reject | "
        "fire / impact / damage |",
        "|---|---|---|---|---|---:|",
    ]
    for row in result["results"]:
        outcome = (
            row["actual_outcome"]
            if row["accepted"]
            else f"REJECT: {row['reason']}"
        )
        counts = (
            f"{row['fire_count']} / {row['impact_count']} / "
            f"{row['damage_count']}"
            if row["accepted"]
            else "-"
        )
        lines.append(
            f"| {row['episode_id']} | {row['candidate_kind']} | "
            f"{row['weapon']} | {row['enemy_motion']} | {outcome} | "
            f"{counts} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    value = report(args.input_manifest.resolve(), output_root)
    review = output_root / "review"
    atomic_text(
        review / "STAGE2_CAUSAL_VALIDATION_REPORT.json",
        json.dumps(value, indent=2, sort_keys=True) + "\n",
    )
    atomic_text(
        review / "STAGE2_CAUSAL_VALIDATION_REPORT.md",
        markdown(value),
    )
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
