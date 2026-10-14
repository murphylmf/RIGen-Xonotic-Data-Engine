                      
"""Lock the official Xonotic 0.8.6 v2 map/weapon/appearance catalog.

This is a read-only inspection of the pinned PK3 files and source tree.  It
does not download content.  The generated catalog contains more waypoint
candidates than the collection will use so live collision/ground probes can
reject unsafe positions without silently dropping a map.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path("./xonotic_capture")
MAP_ARCHIVE = (
    ROOT
    / "assets/release-0.8.6/Xonotic/data/xonotic-20230620-maps.pk3"
)
DATA_ARCHIVE = (
    ROOT
    / "assets/release-0.8.6/Xonotic/data/xonotic-20230620-data.pk3"
)
SOURCE = ROOT / "source/release-src-0.8.6/Xonotic"
ALLOWLIST = ROOT / "assets/OFFICIAL_ASSET_ALLOWLIST.json"
OUTPUT = ROOT / "configs/OFFICIAL_V2_CONTENT_CATALOG.json"

WEAPONS = {
    "Blaster": "blaster",
    "Shotgun": "shotgun",
    "MachineGun": "machinegun",
    "Mortar": "mortar",
    "Electro": "electro",
    "Crylink": "crylink",
    "Vortex": "vortex",
    "Hagar": "hagar",
    "Devastator": "devastator",
}
MODELS = (
    "erebus",
    "gakmasked",
    "ignis",
    "nyx",
    "pyria",
    "seraphina",
    "umbra",
)
GAMETYPE_PRIORITY = (
    "dm",
    "tdm",
    "ctf",
    "ft",
    "ca",
    "dom",
    "kh",
    "ka",
    "lms",
    "duel",
    "race",
    "rc",
    "nb",
    "as",
)
DISTANCE_BINS = {
    "close": (64.0, 256.0),
    "near": (256.0, 512.0),
    "medium": (512.0, 768.0),
    "far": (768.0, 1024.0),
    "very_far": (1024.0, 1536.0),
    "extreme": (1536.0, math.inf),
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_waypoints(payload: bytes) -> list[list[float]]:
    lines = [
        line.strip()
        for line in payload.decode("utf-8", errors="strict").splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]
    if len(lines) % 3:
        raise RuntimeError(f"waypoint row count is not divisible by 3: {len(lines)}")
    points: list[list[float]] = []
    for index in range(0, len(lines), 3):
        match = re.fullmatch(r"'([^']+)'", lines[index])
        duplicate = re.fullmatch(r"'([^']+)'", lines[index + 1])
        if not match or not duplicate:
            raise RuntimeError(f"invalid waypoint triple at row {index}")
        values = [float(value) for value in match.group(1).split()]
        if len(values) != 3 or not all(math.isfinite(value) for value in values):
            raise RuntimeError(f"invalid waypoint coordinate at row {index}")
        points.append([round(value, 6) for value in values])
    return points


def farthest_point_candidates(
    points: list[list[float]], count: int = 12
) -> list[dict[str, Any]]:
    if not points:
        return []
    selected = [
        min(
            range(len(points)),
            key=lambda index: (
                points[index][0],
                points[index][1],
                points[index][2],
                index,
            ),
        )
    ]
    while len(selected) < min(count, len(points)):
        remaining = [
            index for index in range(len(points)) if index not in selected
        ]
        next_index = max(
            remaining,
            key=lambda index: (
                min(
                    sum(
                        (points[index][axis] - points[chosen][axis]) ** 2
                        for axis in range(3)
                    )
                    for chosen in selected
                ),
                -index,
            ),
        )
        selected.append(next_index)
    return [
        {
            "candidate_id": f"wp{index:04d}",
            "waypoint_index": index,
            "origin": points[index],
        }
        for index in selected
    ]


def distance_pair_candidates(
    points: list[list[float]],
) -> list[dict[str, Any]]:
    """Select two geometry-only candidates per distance bin.

    Live server traces, not this Euclidean preselection, decide admission.
    Distinct endpoints are preferred for the second candidate so a single bad
    waypoint does not eliminate the bin.
    """
    result: list[dict[str, Any]] = []
    for bin_name, (lower, upper) in DISTANCE_BINS.items():
        target = lower * 1.25 if math.isinf(upper) else (lower + upper) / 2
        ranked: list[tuple[float, int, int, float]] = []
        for first in range(len(points)):
            for second in range(first + 1, len(points)):
                distance = math.dist(points[first], points[second])
                if distance < lower or distance >= upper:
                    continue
                ranked.append(
                    (abs(distance - target), first, second, distance)
                )
        ranked.sort()
        chosen: list[tuple[float, int, int, float]] = []
        for row in ranked:
            if not chosen or not {
                row[1],
                row[2],
            }.intersection({chosen[0][1], chosen[0][2]}):
                chosen.append(row)
            if len(chosen) == 2:
                break
        for rank, (_, first, second, distance) in enumerate(chosen):
            result.append(
                {
                    "pair_id": (
                        f"{bin_name}_r{rank}_wp{first:04d}_wp{second:04d}"
                    ),
                    "distance_bin": bin_name,
                    "rank": rank,
                    "player_waypoint_index": first,
                    "player_origin": points[first],
                    "enemy_waypoint_index": second,
                    "enemy_origin": points[second],
                    "euclidean_distance": round(distance, 6),
                }
            )
    return result


def map_gametypes(text: str) -> list[str]:
    values = [
        match.group(1)
        for line in text.splitlines()
        if (match := re.match(r"^\s*gametype\s+([a-z0-9_]+)\b", line))
    ]
    if not values:
        raise RuntimeError("mapinfo has no gametype")
    return values


def main() -> int:
    allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    expected_maps = set(allowlist["maps"])
    maps: dict[str, Any] = {}
    with zipfile.ZipFile(MAP_ARCHIVE) as package:
        names = set(package.namelist())
        observed_maps = {
            Path(name).stem
            for name in names
            if re.fullmatch(r"maps/[^/]+\.bsp", name)
            and name != "maps/_hudsetup.bsp"
        }
        if observed_maps != expected_maps:
            raise RuntimeError(
                f"map allowlist mismatch expected={sorted(expected_maps)} "
                f"observed={sorted(observed_maps)}"
            )
        for map_name in sorted(observed_maps):
            bsp_path = f"maps/{map_name}.bsp"
            mapinfo_path = f"maps/{map_name}.mapinfo"
            waypoint_path = f"maps/{map_name}.waypoints"
            required = {bsp_path, mapinfo_path, waypoint_path}
            missing = required - names
            if missing:
                raise RuntimeError(f"{map_name}: missing {sorted(missing)}")
            bsp = package.read(bsp_path)
            mapinfo = package.read(mapinfo_path)
            waypoints_payload = package.read(waypoint_path)
            gametypes = map_gametypes(mapinfo.decode("utf-8", errors="strict"))
            selected_gametype = next(
                mode for mode in GAMETYPE_PRIORITY if mode in gametypes
            )
            points = parse_waypoints(waypoints_payload)
            maps[map_name] = {
                "bsp_path": bsp_path,
                "bsp_sha256": sha256_bytes(bsp),
                "mapinfo_path": mapinfo_path,
                "mapinfo_sha256": sha256_bytes(mapinfo),
                "waypoint_path": waypoint_path,
                "waypoint_sha256": sha256_bytes(waypoints_payload),
                "waypoint_count": len(points),
                "gametypes": gametypes,
                "preflight_gametype": selected_gametype,
                "position_candidates": farthest_point_candidates(points),
                "enemy_pair_candidates": distance_pair_candidates(points),
            }

    appearances: list[dict[str, Any]] = []
    with zipfile.ZipFile(DATA_ARCHIVE) as package:
        names = set(package.namelist())
        for model in MODELS:
            iqm = f"models/player/{model}.iqm"
            if iqm not in names:
                raise RuntimeError(f"missing model {iqm}")
            for skin in (0, 1):
                skin_path = f"models/player/{model}.iqm_{skin}.skin"
                if skin_path not in names:
                    raise RuntimeError(f"missing skin {skin_path}")
                appearances.append(
                    {
                        "model": model,
                        "skin": skin,
                        "model_path": iqm,
                        "model_sha256": sha256_bytes(package.read(iqm)),
                        "skin_path": skin_path,
                        "skin_sha256": sha256_bytes(package.read(skin_path)),
                    }
                )

    weapon_rows: list[dict[str, Any]] = []
    for display_name, netname in WEAPONS.items():
        path = SOURCE / f"source/qcsrc/common/weapons/weapon/{netname}.qh"
        text = path.read_text(encoding="utf-8")
        checks = {
            "registered": f"REGISTER_WEAPON({display_name.upper()}," in text,
            "normal_flag": "WEP_FLAG_NORMAL" in text,
        }
        if not all(checks.values()):
            raise RuntimeError(f"{display_name}: registry checks failed {checks}")
        weapon_rows.append(
            {
                "display_name": display_name,
                "netname": netname,
                "source_path": str(path.relative_to(SOURCE)),
                "source_sha256": sha256_file(path),
                "checks": checks,
            }
        )

    result = {
        "schema_version": "xonotic-official-v2-content-catalog-v1",
        "release": "xonotic-v0.8.6",
        "asset_policy": allowlist["asset_policy"],
        "automatic_downloads": False,
        "map_archive": {
            "path": str(MAP_ARCHIVE),
            "sha256": sha256_file(MAP_ARCHIVE),
        },
        "data_archive": {
            "path": str(DATA_ARCHIVE),
            "sha256": sha256_file(DATA_ARCHIVE),
        },
        "maps": maps,
        "weapons": weapon_rows,
        "enemy_appearances": appearances,
        "counts": {
            "maps": len(maps),
            "weapons": len(weapon_rows),
            "enemy_models": len(MODELS),
            "enemy_appearances": len(appearances),
            "waypoints": sum(row["waypoint_count"] for row in maps.values()),
        },
    }
    if result["counts"] != {
        "maps": 29,
        "weapons": 9,
        "enemy_models": 7,
        "enemy_appearances": 14,
        "waypoints": 3241,
    }:
        raise RuntimeError(f"unexpected catalog counts {result['counts']}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT)
    print(json.dumps(result["counts"], sort_keys=True))
    print(f"catalog={OUTPUT}")
    print(f"sha256={sha256_file(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
