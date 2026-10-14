                      
"""Live-only controlled-return qualification for selected map anchors."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = Path(__file__).with_name("scan_long60_map_anchor_angles_live_v1.py")
SPEC = importlib.util.spec_from_file_location("long60_selected_controlled_scan_base", SCAN_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import scan module: {SCAN_PATH}")
scan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scan
SPEC.loader.exec_module(scan)


SCAN_ID = "long60_selected_anchors_controlled_live_v1_20260828"
DEFAULT_ARTIFACT_ROOT = ROOT / "manifests" / SCAN_ID
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / SCAN_ID


SELECTED = {
    "geoplanetary": {
        "gametype": "ctf",
        "player_origin": [608.4, 1429.2, -104.0],
        "trajectory_scale": 1.0,
        "angle_degrees": 9.165809654015861,
        "environment_text": scan.v6.MAPS["geoplanetary"]["environment_text"],
        "prompt_provenance_sample_id": scan.v6.MAPS["geoplanetary"]["prompt_provenance_sample_id"],
    },
    "bromine": {
        **scan.MAP_ANCHORS["bromine"],
        "angle_degrees": 225.0,
    },
    "catharsis": {
        **scan.MAP_ANCHORS["catharsis"],
        "angle_degrees": 180.0,
    },
    "courtfun": {
        **scan.MAP_ANCHORS["courtfun"],
        "angle_degrees": 315.0,
    },
    "implosion": {
        **scan.MAP_ANCHORS["implosion"],
        "angle_degrees": 135.0,
    },
}
scan.SCAN_ID = SCAN_ID
scan.MAP_ANCHORS = SELECTED


def prepare(artifact_root: Path) -> None:
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(artifact_root)
    artifact_root.mkdir(parents=True)
    source_rows = scan.v6.distribution_rows()
    source = next(
        dict(row)
        for row in source_rows
        if row["template"] == "controlled_return" and int(row["kill_count"]) == 0
    )
    rows = []
    for index, map_name in enumerate(sorted(SELECTED)):
        config = SELECTED[map_name]
        angle = float(config["angle_degrees"])
        row = dict(source)
        row.update(
            {
                "manifest_index": index,
                "scan_index": index,
                "episode_id": f"l60ctrlscan_v1_{map_name}",
                "map": map_name,
                "gametype": config["gametype"],
                "anchor_id": f"{map_name}_selected_a{round(angle):03d}_scale{int(100*config['trajectory_scale']):03d}",
                "player_origin": config["player_origin"],
                "trajectory_scale": config["trajectory_scale"],
                "angle_degrees": angle,
                "weapon": "MachineGun",
                "weapon_netname": "machinegun",
                "instant_hit_weapon": True,
                "kill_count": 0,
                "kill_slots": [],
            }
        )
        scan.configure_row(row)
        actions = artifact_root / "actions" / map_name / "controlled_return.csv"
        scan.v6.base.write_actions(
            actions,
            row["episode_id"],
            int(row["engine_seed"]),
            scan.v6.prod.TEMPLATES["controlled_return"],
        )
        scenario_path, timeline = scan.v6.build_episode_scenario(row, artifact_root, actions)
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["training_admitted"] = False
        scenario["anchor_angle_scan"] = {
            "scan_id": SCAN_ID,
            "angle_degrees": angle,
            "live_only": True,
            "template": "controlled_return",
        }
        scan.v6.prod.write_json_atomic(scenario_path, scenario)
        row.update(
            {
                "scenario_path": scan.v6.prod.relative_to_root(scenario_path),
                "scenario_sha256": scan.v6.prod.base.sha256(scenario_path),
                "actions_path": scan.v6.prod.relative_to_root(actions),
                "actions_sha256": scan.v6.prod.base.sha256(actions),
                "timeline_path": scan.v6.prod.relative_to_root(timeline),
                "timeline_sha256": scan.v6.prod.base.sha256(timeline),
            }
        )
        rows.append(row)
    manifest = artifact_root / "scan_manifest.jsonl"
    scan.v6.prod.write_jsonl_atomic(manifest, rows)
    scan.v6.prod.write_json_atomic(
        artifact_root / "PREPARED.json",
        {
            "schema_version": "xonotic-long60-selected-controlled-live-scan-v1",
            "scan_id": SCAN_ID,
            "case_count": len(rows),
            "maps": sorted(SELECTED),
            "template": "controlled_return",
            "live_only": True,
            "training_admitted": False,
            "manifest_sha256": scan.v6.prod.base.sha256(manifest),
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
    worker_parser.add_argument("--lane-count", type=int, default=5)
    worker_parser.add_argument("--port", type=int, required=True)
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    report_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.artifact_root)
    elif args.command == "worker":
        scan.worker(
            args.artifact_root,
            args.output_root.resolve(),
            args.scratch_root.resolve(),
            args.lane_id,
            args.lane_count,
            args.port,
        )
    else:
        scan.report(args.artifact_root, args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
