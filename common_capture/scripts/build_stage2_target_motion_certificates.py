                      
"""Build immutable certificates from accepted target-motion candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
DEFAULT_MANIFEST = (
    ROOT / "manifests/stage2_target_motion_certification_v1/input.jsonl"
)
DEFAULT_OUTPUT = (
    ROOT / "stage2_target_motion_certification_v1_output"
)
REQUIRED_ARTIFACTS = (
    "qa.json",
    "states.parquet",
    "events.parquet",
    "enemy_path_trace.parquet",
    "target_relations.parquet",
    "model_actions.parquet",
)


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def accepted_rows(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/accepted.jsonl"
        )
    ):
        rows.extend(capture.load_jsonl(path))
    return rows


def terminal_rows(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/rejects.jsonl"
        )
    ):
        rows.extend(
            row
            for row in capture.load_jsonl(path)
            if row.get("terminal") is True
        )
    return rows


def build(
    manifest: Path,
    output_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scenarios = {
        row["episode_id"]: row for row in capture.load_jsonl(manifest)
    }
    accepted = accepted_rows(output_root)
    terminal = terminal_rows(output_root)
    records: list[dict[str, Any]] = []
    for published in accepted:
        episode_id = published["episode_id"]
        scenario = scenarios[episode_id]
        package = Path(published["episode_path"])
        qa = json.loads(
            (package / "qa.json").read_text(encoding="utf-8")
        )
        causal_qa = json.loads(
            (package / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        states = pd.read_parquet(package / "states.parquet")
        trace = pd.read_parquet(
            package / "enemy_path_trace.parquet"
        ).sort_values("server_tick")
        relations = pd.read_parquet(
            package / "target_relations.parquet"
        ).sort_values("frame_index")
        state_enemy = np.stack(
            states.loc[
                states["server_tick"] >= 1, "enemy.origin"
            ].map(lambda value: np.asarray(value, dtype=np.float64))
        )
        prescribed = np.stack(
            trace["target"].map(
                lambda value: np.asarray(value, dtype=np.float64)
            )
        )
        path_error = float(
            np.max(np.abs(state_enemy - prescribed), initial=0.0)
        )
        output_enemy = np.stack(
            relations[
                ["enemy_x", "enemy_y", "enemy_z"]
            ].to_numpy(dtype=np.float64)
        )
        output_step = np.linalg.norm(
            np.diff(output_enemy, axis=0), axis=1
        )
        displacement = np.linalg.norm(
            output_enemy - output_enemy[0], axis=1
        )
        distance = pd.to_numeric(
            relations["distance_3d"], errors="coerce"
        ).to_numpy(dtype=np.float64)
        delta = np.diff(distance)
        los = (
            pd.to_numeric(
                relations["los_fraction"], errors="coerce"
            )
            .fillna(0.0)
            .to_numpy(dtype=np.float64)
            >= 0.999999
        )
        visible = (
            relations["render_visible_proxy"]
            .fillna(False)
            .to_numpy(dtype=bool)
        )
        checks = {
            "role_eligible": qa.get("role_eligible") is True,
            "all_hard_gates": all(
                (qa.get("hard_gates") or {}).values()
            ),
            "causal_pass": causal_qa.get("passed") is True,
            "no_aim_treatment": causal_qa.get(
                "aim_overlay_active_frames"
            )
            == 0,
            "no_fire_outcome": (
                causal_qa.get("actual_outcome") == "no_fire"
                and qa["events"]["fire_count"] == 0
            ),
            "whole_path_trace_pass": (
                qa.get("live_precheck", {})
                .get("enemy_path_trace", {})
                .get("passed")
                is True
            ),
            "realized_matches_prescribed_path": (
                len(state_enemy) == len(prescribed) == 383
                and path_error <= 1e-5
            ),
            "output_rows": len(relations)
            == capture.OUTPUT_TICKS,
            "visible_support": int(visible.sum()) >= 16,
            "artifacts": all(
                (package / name).is_file()
                for name in REQUIRED_ARTIFACTS
            ),
        }
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "stage2_target_motion_certificate_failed",
                capture.canonical_json(
                    {"episode_id": episode_id, "checks": checks}
                ),
            )
        encounter_hash = causal.encounter_contract_sha256(
            scenario
        )
        record = {
            "schema_version": causal.ENCOUNTER_CERTIFICATE_SCHEMA,
            "certificate_kind": (
                "stage2_target_motion_certificate_v1"
            ),
            "certificate_id": (
                f"targetmotion_{scenario['enemy_policy']['name']}_"
                f"{encounter_hash[:12]}"
            ),
            "passed": True,
            "source_episode_id": episode_id,
            "source_scenario_sha256": hashlib.sha256(
                capture.canonical_json(scenario).encode("utf-8")
            ).hexdigest(),
            "source_episode_path": str(package.relative_to(ROOT)),
            "source_commit": scenario["source_commit_required"],
            "encounter_contract_sha256": encounter_hash,
            "route_id": None,
            "map": scenario["map"],
            "gametype": scenario["gametype"],
            "distance": {
                "minimum": float(np.nanmin(distance)),
                "maximum": float(np.nanmax(distance)),
                "reset_bin": scenario["policy_labels"][
                    "expected_distance_bin"
                ],
            },
            "target_motion": {
                "name": scenario["enemy_policy"]["name"],
                "mode": int(scenario["enemy"]["motion"]),
                "declared_distance": float(
                    scenario["enemy"]["motion_distance"]
                ),
                "maximum_displacement": float(
                    np.max(displacement, initial=0.0)
                ),
                "path_length": float(output_step.sum()),
                "closing_transitions": int((delta < -1e-6).sum()),
                "stable_transitions": int(
                    (np.abs(delta) <= 1e-6).sum()
                ),
                "opening_transitions": int((delta > 1e-6).sum()),
                "prescribed_realized_max_abs_error": path_error,
            },
            "authoritative_los": {
                "frames": int(los.sum()),
                "fraction": float(los.mean()),
            },
            "baseline_render_visibility": {
                "frames": int(visible.sum()),
                "fraction": float(visible.mean()),
            },
            "authoritative_telemetry_sha256": qa["telemetry"][
                "authoritative_sha256"
            ],
            "artifacts_sha256": {
                name: capture.sha256_file(package / name)
                for name in REQUIRED_ARTIFACTS
            },
            "checks": checks,
        }
        records.append(record)
    records.sort(key=lambda row: row["certificate_id"])
    summary = {
        "schema_version": (
            "xonotic-stage2-target-motion-"
            "certification-summary-v1"
        ),
        "pass": (
            len(accepted) + len(terminal) == len(scenarios)
            and bool(records)
        ),
        "planned": len(scenarios),
        "accepted_certificates": len(records),
        "terminal_rejects": len(terminal),
        "by_motion": dict(
            Counter(
                row["target_motion"]["name"] for row in records
            )
        ),
        "by_distance": dict(
            Counter(row["distance"]["reset_bin"] for row in records)
        ),
        "by_map": dict(Counter(row["map"] for row in records)),
        "terminal": [
            {
                "episode_id": row["episode_id"],
                "reason": row["reason"],
                "diagnostic_path": row["diagnostic_path"],
            }
            for row in terminal
        ],
    }
    return records, summary


def markdown(
    records: list[dict[str, Any]], summary: dict[str, Any]
) -> str:
    lines = [
        "# Stage-2 target-motion certification v1",
        "",
        f"- Overall accounting: "
        f"**{'PASS' if summary['pass'] else 'FAIL'}**",
        f"- Planned / certified / terminal: "
        f"{summary['planned']} / "
        f"{summary['accepted_certificates']} / "
        f"{summary['terminal_rejects']}",
        f"- Certified by motion: "
        f"`{json.dumps(summary['by_motion'], sort_keys=True)}`",
        f"- Certified by distance: "
        f"`{json.dumps(summary['by_distance'], sort_keys=True)}`",
        "- These are non-training geometry certificates; no runtime "
        "fallback or outcome relabeling is used.",
        "",
        "| certificate | map/mode | distance | displacement/path | "
        "closing/stable/opening |",
        "|---|---|---|---:|---:|",
    ]
    for row in records:
        motion = row["target_motion"]
        lines.append(
            f"| {row['certificate_id']} | {row['map']} / "
            f"{motion['name']} | {row['distance']['reset_bin']} | "
            f"{motion['maximum_displacement']:.2f}/"
            f"{motion['path_length']:.2f} | "
            f"{motion['closing_transitions']}/"
            f"{motion['stable_transitions']}/"
            f"{motion['opening_transitions']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-manifest", type=Path, default=DEFAULT_MANIFEST
    )
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT
    )
    parser.add_argument("--review-root", type=Path)
    args = parser.parse_args()
    manifest = args.input_manifest.resolve()
    output_root = args.output_root.resolve()
    review = (
        args.review_root.resolve()
        if args.review_root
        else output_root / "review"
    )
    records, summary = build(manifest, output_root)
    atomic_text(
        review / "TARGET_MOTION_CERTIFICATES.jsonl",
        canonical_lines(records),
    )
    atomic_text(
        review / "TARGET_MOTION_CERTIFICATION_SUMMARY.json",
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
    )
    atomic_text(
        review / "TARGET_MOTION_CERTIFICATION_REPORT.md",
        markdown(records, summary),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
