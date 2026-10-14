                      
"""Qualify compact, same-height anchors for long60 multi-enemy motion.

This is a non-training calibration matrix.  It keeps the accepted v5 runtime
and lifecycle contract, uses MachineGun as the timing reference, and tests
both long60 templates on each candidate anchor.  Non-geoplanetary trajectories
are scaled in both radial and lateral axes so their screen-space paths remain
unchanged while fitting smaller clear areas.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V6_PATH = Path(__file__).with_name(
    "long60_production_ref42_v6_multimap_hitscan.py"
)
SPEC = importlib.util.spec_from_file_location("long60_anchor_calibration_v1_base", V6_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import v6 module: {V6_PATH}")
v6 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v6
SPEC.loader.exec_module(v6)


CALIBRATION_ID = "long60_multimap_anchor_calibration_v1_20260828"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / CALIBRATION_ID
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / CALIBRATION_ID
ORIGINAL_TEMPLATES = v6.prod.TEMPLATES


CANDIDATES: dict[str, dict[str, Any]] = {
    "geoplanetary": {
        "gametype": "ctf",
        "anchor_id": "geoplanetary_long60_open_608_1429",
        "player_origin": [608.4, 1429.2, -104.0],
        "enemy_reference_origin": [874.9525038849215, 1472.2088673726576, -104.0],
        "trajectory_scale": 1.0,
        "environment_text": v6.MAPS["geoplanetary"]["environment_text"],
        "prompt_provenance_sample_id": v6.MAPS["geoplanetary"]["prompt_provenance_sample_id"],
    },
    "bromine": {
        "gametype": "dm",
        "anchor_id": "bromine_close_flat_wp0061_wp0104_scale055",
        "player_origin": [-2317.7, 2169.5, 424.0],
        "enemy_reference_origin": [-2372.5, 2022.1, 424.0],
        "trajectory_scale": 0.55,
        "environment_text": v6.MAPS["bromine"]["environment_text"],
        "prompt_provenance_sample_id": v6.MAPS["bromine"]["prompt_provenance_sample_id"],
    },
    "courtfun": {
        "gametype": "ctf",
        "anchor_id": "courtfun_close_flat_wp0161_wp0163_scale055",
        "player_origin": [706.8, -799.7, 24.0],
        "enemy_reference_origin": [639.0, -648.4, 24.0],
        "trajectory_scale": 0.55,
        "environment_text": v6.MAPS["courtfun"]["environment_text"],
        "prompt_provenance_sample_id": v6.MAPS["courtfun"]["prompt_provenance_sample_id"],
    },
    "catharsis": {
        "gametype": "ctf",
        "anchor_id": "catharsis_close_flat_wp0129_wp0141_scale055",
        "player_origin": [-734.9, 3015.9, -91.2],
        "enemy_reference_origin": [-740.3, 3174.8, -91.2],
        "trajectory_scale": 0.55,
        "environment_text": "An industrial cavern built from concrete, brushed metal, raw rock, and glowing energy panels, with cool blue and warm red light strips, suspended walkways, stairs, jagged stone, and dark angular structures.",
        "prompt_provenance_sample_id": "s2short42v15r1_s2mtv42v14r4_000007",
    },
    "implosion": {
        "gametype": "dm",
        "anchor_id": "implosion_close_flat_wp0064_wp0077_scale055",
        "player_origin": [3661.1, -2017.6, 152.0],
        "enemy_reference_origin": [3759.1, -2146.9, 152.0],
        "trajectory_scale": 0.55,
        "environment_text": "A space station built from brushed metal, steel plating, concrete, and glowing panels, with dark grey and metallic surfaces, red and blue lights, machinery, grid-patterned floors, and elevated platforms.",
        "prompt_provenance_sample_id": "s2short42v15r1_s2mtv42v14r4_000002",
    },
}


def scaled_templates(scale: float) -> dict[str, tuple[Any, ...]]:
    return {
        template: tuple(
            replace(
                segment,
                lateral_start=segment.lateral_start * scale,
                lateral_end=segment.lateral_end * scale,
                distance_start=segment.distance_start * scale,
                distance_end=segment.distance_end * scale,
            )
            for segment in segments
        )
        for template, segments in ORIGINAL_TEMPLATES.items()
    }


def configure_candidate(row: dict[str, Any]) -> None:
    candidate = CANDIDATES[str(row["map"])]
    v6.MAPS = CANDIDATES
    v6.prod.TEMPLATES = scaled_templates(float(candidate["trajectory_scale"]))
    v6.configure_geometry_and_weapon(row)


def choose_rows() -> list[dict[str, Any]]:
    source = v6.distribution_rows()
    rows: list[dict[str, Any]] = []
    for map_name in sorted(CANDIDATES):
        for template in ("four_distinct", "controlled_return"):
            row = next(
                dict(item)
                for item in source
                if item["template"] == template
                and int(item["kill_count"]) == 2
                and (template != "controlled_return" or set(item["kill_slots"]) == {1, 2})
            )
            index = len(rows)
            row.update(
                {
                    "manifest_index": index,
                    "pilot_index": index,
                    "episode_id": f"l60anchor_v1_{map_name}_{template}",
                    "map": map_name,
                    "gametype": CANDIDATES[map_name]["gametype"],
                    "anchor_id": CANDIDATES[map_name]["anchor_id"],
                    "weapon": "MachineGun",
                    "weapon_netname": "machinegun",
                    "instant_hit_weapon": True,
                    "trajectory_scale": CANDIDATES[map_name]["trajectory_scale"],
                }
            )
            rows.append(row)
    return rows


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    rows = choose_rows()
    for row in rows:
        configure_candidate(row)
        actions = artifact_root / "actions" / row["map"] / row["template"] / "actions.csv"
        v6.base.write_actions(
            actions,
            row["episode_id"],
            int(row["engine_seed"]),
            v6.prod.TEMPLATES[row["template"]],
        )
        scenario_path, timeline = v6.build_episode_scenario(row, artifact_root, actions)
        row.update(
            {
                "scenario_path": v6.prod.relative_to_root(scenario_path),
                "scenario_sha256": v6.prod.base.sha256(scenario_path),
                "actions_path": v6.prod.relative_to_root(actions),
                "actions_sha256": v6.prod.base.sha256(actions),
                "timeline_path": v6.prod.relative_to_root(timeline),
                "timeline_sha256": v6.prod.base.sha256(timeline),
            }
        )
    manifest = artifact_root / "pilot_manifest.jsonl"
    v6.prod.write_jsonl_atomic(manifest, rows)
    v6.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-multimap-anchor-calibration-v1",
            "calibration_id": CALIBRATION_ID,
            "episode_count": len(rows),
            "maps": sorted(CANDIDATES),
            "templates": sorted(ORIGINAL_TEMPLATES),
            "weapon": "MachineGun",
            "training_admitted": False,
            "manifest_sha256": v6.prod.base.sha256(manifest),
        },
    )


def worker(
    artifact_root: Path,
    output_root: Path,
    scratch_root: Path,
    lane_id: int,
    lane_count: int,
    port: int,
) -> None:
    rows = v6.prod.load_jsonl(artifact_root.resolve() / "pilot_manifest.jsonl")
    selected = [row for row in rows if int(row["pilot_index"]) % lane_count == lane_id]
    build = ROOT / "build" / v6.BUILD_TAG
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    lane: Any | None = None
    generation = 0
    failures: list[dict[str, Any]] = []
    completed = 0
    started = time.monotonic()
    try:
        for sequence, row in enumerate(selected, 1):
            configure_candidate(row)
            scenario_path = ROOT / row["scenario_path"]
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            if lane is None:
                generation += 1
                lane = v6.base.reusable.ReusableStage1Lane(
                    scratch_root / f"resident-generation-{generation:03d}",
                    build=build,
                    port=port,
                )
            try:
                record = v6.run_attempt(lane, row, scenario, output_root, scratch_root, 1)
                completed += 1
                print(
                    f"anchor_accepted lane={lane_id} map={row['map']} "
                    f"template={row['template']} wall={record['wall_seconds']:.3f} "
                    f"progress={sequence}/{len(selected)}",
                    flush=True,
                )
            except Exception as exc:
                failures.append(
                    {
                        "episode_id": row["episode_id"],
                        "map": row["map"],
                        "template": row["template"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                traceback.print_exc()
                lane.close()
                lane = None
    finally:
        if lane is not None:
            lane.close()
    v6.prod.write_json_atomic(
        output_root / "status" / "lanes" / f"lane-{lane_id:02d}.json",
        {
            "schema_version": "xonotic-long60-anchor-calibration-lane-v1",
            "lane_id": lane_id,
            "selected": len(selected),
            "completed": completed,
            "failures": failures,
            "wall_seconds": time.monotonic() - started,
            "raw_avi_retained": False,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    worker_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    worker_parser.add_argument("--scratch-root", type=Path, required=True)
    worker_parser.add_argument("--lane-id", type=int, required=True)
    worker_parser.add_argument("--lane-count", type=int, default=2)
    worker_parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.artifact_root)
    else:
        worker(
            args.artifact_root,
            args.output_root.resolve(),
            args.scratch_root.resolve(),
            args.lane_id,
            args.lane_count,
            args.port,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
