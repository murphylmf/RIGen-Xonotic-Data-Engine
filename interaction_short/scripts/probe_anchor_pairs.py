                      
"""Run the authoritative reset/trace gate for candidate official spawn pairs.

This intentionally stops after the live demo pass.  It is a selection probe,
not an accepted episode: no offline render, encode, package, or manifest row is
produced.  Every probe's live artifacts are copied to persistent storage.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = Path("./xonotic_capture")


def yaw_towards(source: list[float], target: list[float]) -> float:
    return math.degrees(
        math.atan2(target[1] - source[1], target[0] - source[0])
    )


def parse_pair(value: str) -> tuple[int, int]:
    try:
        player, enemy = value.split(":", 1)
        return int(player), int(enemy)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            f"pair must be PLAYER_INDEX:ENEMY_INDEX, got {value!r}"
        ) from exc


def append_result(path: Path, row: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        )
        handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map_name", choices=("stormkeep", "solarium", "xoylent"))
    parser.add_argument("pairs", nargs="+", type=parse_pair)
    args = parser.parse_args()

    capture.require_conda()
    capture.validate_fixed_assets()
    catalog = json.loads(
        capture.ANCHOR_CATALOG_PATH.read_text(encoding="utf-8")
    )
    map_spec = catalog["maps"][args.map_name]
    with zipfile.ZipFile(catalog["source"]["archive"]) as package:
        spawns = capture.parse_official_bsp_spawns(
            package.read(map_spec["bsp_path"])
        )

    template = capture.find_scenario("pilot_009")
    probe_id = capture.utc_now().replace("-", "").replace(":", "")
    destination_root = ROOT / "probes" / f"anchor_pair_probe_{probe_id}"
    destination_root.mkdir(parents=True)
    results_path = destination_root / "results.jsonl"
    summary: list[dict[str, object]] = []

    for ordinal, (player_index, enemy_index) in enumerate(args.pairs, 1):
        if player_index == enemy_index:
            raise ValueError("player and enemy spawn indexes must differ")
        player_origin = spawns[player_index]
        enemy_origin = spawns[enemy_index]
        anchor_id = (
            f"{args.map_name}_dm{player_index:02d}_dm{enemy_index:02d}"
        )
        episode_id = f"probe_{ordinal:02d}_{anchor_id}"
        scenario = copy.deepcopy(template)
        scenario.update(
            {
                "episode_id": episode_id,
                "map": args.map_name,
                "anchor_id": anchor_id,
                "seed": 986000 + ordinal,
            }
        )
        scenario["player"]["origin"] = player_origin
        scenario["enemy"]["origin"] = enemy_origin
        scenario["player"]["yaw"] = yaw_towards(
            player_origin, enemy_origin
        )
        scenario["enemy"]["yaw"] = yaw_towards(
            enemy_origin, player_origin
        )
        scenario["enemy"]["motion"] = 0
        scenario["enemy"]["motion_distance"] = 0.0
        scenario["anchor"] = {
            "catalog": str(capture.ANCHOR_CATALOG_PATH),
            "player_spawn_index": player_index,
            "enemy_spawn_index": enemy_index,
            "player_xy_jitter": [0.0, 0.0],
            "enemy_xy_jitter": [0.0, 0.0],
        }

        stage = capture.TMP_ROOT / "raw" / episode_id
        if stage.exists():
            capture.clean_stage(stage)
        stage.mkdir(parents=True)
        print(
            f"probe {ordinal}/{len(args.pairs)} {anchor_id}",
            flush=True,
        )
        try:
            live = capture.run_live_attempt(
                stage, scenario, capture.build_root(), retry=0
            )
            rows = capture.load_jsonl(Path(live["server_telemetry"]))
            reset_rows = [row for row in rows if row.get("kind") == "reset"]
            if len(reset_rows) != 1:
                raise capture.CaptureFailure(
                    "anchor_reset_singleton",
                    f"actual={len(reset_rows)}",
                )
            anchor = reset_rows[0]["anchor"]
            passed = (
                anchor.get("id") == anchor_id
                and bool(anchor.get("player_clear", 0))
                and bool(anchor.get("enemy_clear", 0))
                and bool(anchor.get("player_ground", 0))
                and bool(anchor.get("enemy_ground", 0))
                and float(anchor.get("los_fraction", -1)) >= 0.999999
            )
            row: dict[str, object] = {
                "anchor_id": anchor_id,
                "map": args.map_name,
                "player_spawn_index": player_index,
                "player_origin": player_origin,
                "enemy_spawn_index": enemy_index,
                "enemy_origin": enemy_origin,
                "anchor_telemetry": anchor,
                "pass": passed,
            }
        except Exception as exc:
            row = {
                "anchor_id": anchor_id,
                "map": args.map_name,
                "player_spawn_index": player_index,
                "player_origin": player_origin,
                "enemy_spawn_index": enemy_index,
                "enemy_origin": enemy_origin,
                "pass": False,
                "error": f"{type(exc).__name__}:{exc}",
            }

        destination = destination_root / episode_id
        shutil.copytree(stage, destination)
        row["artifacts_path"] = str(destination)
        append_result(results_path, row)
        summary.append(row)
        print(
            f"result {anchor_id} pass={row['pass']} "
            f"telemetry={json.dumps(row.get('anchor_telemetry', {}), sort_keys=True)}",
            flush=True,
        )
        capture.clean_stage(stage)

    summary_path = destination_root / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema_version": "xonotic-anchor-pair-probe-v1",
                "created_utc": capture.utc_now(),
                "source_commit": (
                    capture.build_root() / "SOURCE_COMMIT"
                ).read_text(encoding="utf-8").strip(),
                "asset_archive_sha256": catalog["source"]["archive_sha256"],
                "results": summary,
                "pass_count": sum(bool(row["pass"]) for row in summary),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"summary={summary_path}")
    return 0 if any(bool(row["pass"]) for row in summary) else 2


if __name__ == "__main__":
    raise SystemExit(main())
