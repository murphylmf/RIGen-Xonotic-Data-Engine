                      
"""Audit accepted v3 path encounters and emit immutable certificates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              
import xonotic_stage2_causal as causal              


ROOT = capture.ROOT
MANIFEST = (
    ROOT / "manifests/stage2_path_encounter_certification_v1/input.jsonl"
)
OUTPUT_ROOT = ROOT / "stage2_path_encounter_certification_v1_output"
REVIEW_ROOT = OUTPUT_ROOT / "review"
INDEX = REVIEW_ROOT / "PATH_ENCOUNTER_CERTIFICATES.jsonl"
REPORT = REVIEW_ROOT / "PATH_ENCOUNTER_CERTIFICATION_REPORT.md"


def segments(mask: np.ndarray) -> list[list[int]]:
    result: list[list[int]] = []
    start: int | None = None
    for index, active in enumerate(
        np.concatenate((mask.astype(bool), [False]))
    ):
        if active and start is None:
            start = index
        elif not active and start is not None:
            result.append([start, index - 1])
            start = None
    return result


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def build(
    manifest: Path = MANIFEST,
    output_root: Path = OUTPUT_ROOT,
) -> list[dict[str, Any]]:
    scenarios = {
        row["episode_id"]: row for row in capture.load_jsonl(manifest)
    }
    accepted_path = (
        output_root
        / "manifests/shards/shard-000-of-001/accepted.jsonl"
    )
    accepted = capture.load_jsonl(accepted_path)
    records: list[dict[str, Any]] = []
    for accepted_row in accepted:
        episode_id = accepted_row["episode_id"]
        scenario = scenarios[episode_id]
        package = output_root / "episodes" / episode_id
        qa = json.loads(
            (package / "qa.json").read_text(encoding="utf-8")
        )
        causal_qa = json.loads(
            (package / "causal_interaction.json").read_text(
                encoding="utf-8"
            )
        )
        relations = pd.read_parquet(
            package / "target_relations.parquet"
        ).sort_values("frame_index")
        los = (
            pd.to_numeric(
                relations["los_fraction"], errors="coerce"
            )
            .fillna(0.0)
            .to_numpy(np.float64)
            >= 0.999999
        )
        visible = (
            relations["render_visible_proxy"]
            .fillna(False)
            .to_numpy(bool)
        )
        distance = pd.to_numeric(
            relations["distance_3d"], errors="coerce"
        ).to_numpy(np.float64)
        source = scenario["player_path_source"]
        required_artifacts = (
            "qa.json",
            "states.parquet",
            "target_relations.parquet",
            "route_trace.parquet",
            "base_actions.parquet",
            "aim_overlay.parquet",
            "model_actions.parquet",
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
            "path_pass": (
                causal_qa.get("player_path") or {}
            ).get("passed")
            is True,
            "route_pass": (qa.get("route") or {}).get("passed")
            is True,
            "player_enemy_clearance": (
                source.get("player_enemy_clearance_passed") is True
                and float(
                    source["minimum_player_enemy_clearance"]
                )
                >= causal.PLAYER_ENEMY_CLEARANCE_MINIMUM
            ),
            "output_rows": len(relations)
            == capture.OUTPUT_TICKS,
            "visible_support": int(visible.sum()) >= 16,
            "artifacts": all(
                (package / name).is_file()
                for name in required_artifacts
            ),
        }
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "stage2_path_encounter_certificate_failed",
                capture.canonical_json(
                    {"episode_id": episode_id, "checks": checks}
                ),
            )
        encounter_hash = causal.encounter_contract_sha256(
            scenario
        )
        record = {
            "schema_version": causal.ENCOUNTER_CERTIFICATE_SCHEMA,
            "certificate_id": (
                f"pathenc_{source['route_id']}_"
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
            "route_id": source["route_id"],
            "player_motion_class": scenario["causal_design"][
                "player_motion_class"
            ],
            "map": scenario["map"],
            "gametype": scenario["gametype"],
            "distance": {
                "minimum": float(np.nanmin(distance)),
                "maximum": float(np.nanmax(distance)),
                "reset_bin": scenario["policy_labels"][
                    "expected_distance_bin"
                ],
            },
            "player_enemy_clearance": {
                "metric": source["player_enemy_clearance_metric"],
                "threshold": source[
                    "player_enemy_clearance_threshold"
                ],
                "minimum": source[
                    "minimum_player_enemy_clearance"
                ],
                "minimum_server_tick": source[
                    "minimum_player_enemy_clearance_server_tick"
                ],
            },
            "authoritative_los": {
                "frames": int(los.sum()),
                "fraction": float(los.mean()),
                "segments_inclusive": segments(los),
                "mask_sha256": hashlib.sha256(
                    los.astype(np.uint8).tobytes()
                ).hexdigest(),
            },
            "baseline_render_visibility": {
                "frames": int(visible.sum()),
                "fraction": float(visible.mean()),
                "segments_inclusive": segments(visible),
                "mask_sha256": hashlib.sha256(
                    visible.astype(np.uint8).tobytes()
                ).hexdigest(),
            },
            "player_path": causal_qa["player_path"],
            "authoritative_telemetry_sha256": (
                qa["telemetry"]["authoritative_sha256"]
            ),
            "artifacts_sha256": {
                name: capture.sha256_file(package / name)
                for name in required_artifacts
            },
            "checks": checks,
        }
        records.append(record)
    records.sort(key=lambda row: row["certificate_id"])
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--review-root", type=Path, default=REVIEW_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = args.input_manifest.resolve()
    output_root = args.output_root.resolve()
    review_root = args.review_root.resolve()
    index = review_root / INDEX.name
    report = review_root / REPORT.name
    records = build(manifest, output_root)
    review_root.mkdir(parents=True, exist_ok=True)
    atomic_write(index, canonical_lines(records))
    lines = [
        "# Stage-2 path encounter certification",
        "",
        f"- Accepted certificates: {len(records)}",
        "- Training admission: false",
        "- Runtime action/geometry fallback: none",
        "- Certification covers manifest-declared route replay "
        "tolerance, player-enemy clearance, authoritative LOS, "
        "baseline visibility, media, action, route, HUD, audio, and "
        "causal no-response QA.",
        "",
        "| Certificate | Motion | Map/mode | LOS frames | "
        "Visible frames | Min clearance |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in records:
        lines.append(
            f"| `{row['certificate_id']}` | "
            f"{row['player_motion_class']} | "
            f"{row['map']}/{row['gametype']} | "
            f"{row['authoritative_los']['frames']} | "
            f"{row['baseline_render_visibility']['frames']} | "
            f"{row['player_enemy_clearance']['minimum']:.2f} |"
        )
    lines.extend(
        [
            "",
            f"- Certificate index SHA256: "
            f"`{capture.sha256_file(index)}`",
        ]
    )
    atomic_write(report, "\n".join(lines) + "\n")
    print(
        json.dumps(
            {
                "certificates": len(records),
                "index": str(index),
                "index_sha256": capture.sha256_file(index),
                "report": str(report),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
