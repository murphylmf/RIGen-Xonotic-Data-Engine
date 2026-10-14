                      
"""Build an eight-weapon, non-training Stage-1 v4 reload validation shard."""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_manifests as stage1              
import xonotic_capture as capture              


ROOT = capture.ROOT
OUTPUT_ROOT = ROOT / "manifests/stage1_v4_reload_validation"
OUTPUT_MANIFEST = OUTPUT_ROOT / "input.jsonl"
OUTPUT_METADATA = OUTPUT_ROOT / "MANIFEST_METADATA.json"
OUTPUT_AUDIT = OUTPUT_ROOT / "VALIDATION_AUDIT.json"
SPLIT = "v4_stage1_reload_validation"

                                                                              
                                                                                 
MAP_PREFERENCE = {
    name: index
    for index, name in enumerate(
        (
            "xoylent",
            "bromine",
            "runningman",
            "stormkeep",
            "glowplant",
            "solarium",
            "darkzone",
            "afterslime",
            "go",
            "warfare",
        )
    )
}


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_reload_validation_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def candidate_key(row: dict[str, Any]) -> tuple[int, str, str]:
    return (
        MAP_PREFERENCE.get(str(row["map"]), len(MAP_PREFERENCE)),
        str(row.get("gametype", "")),
        str(row["episode_id"]),
    )


def diagnostic_row(source: dict[str, Any], index: int) -> dict[str, Any]:
    row = copy.deepcopy(source)
    source_episode_id = str(source["episode_id"])
    row.update(
        {
            "episode_id": (
                f"s1v4_reloadcheck_{index:02d}_"
                f"{str(source['weapon_netname'])}"
            ),
            "source_episode_id": source_episode_id,
            "source_manifest": str(
                stage1.INPUT_PATH.relative_to(ROOT)
            ),
            "source_manifest_sha256": capture.sha256_file(
                stage1.INPUT_PATH
            ),
            "split": SPLIT,
            "formal_collection_authorized": False,
            "formal_authorization_basis": (
                "targeted_nontraining_reload_mechanics_validation"
            ),
            "training_admitted": False,
            "assigned_shard": 0,
            "shard_count": 1,
            "diagnostic_only": True,
            "diagnostic_purpose": (
                "isolate one linked successful reload for this weapon"
            ),
            "expects_sound": True,
        }
    )
    design = row["action_design"]
    design.update(
        {
            "locomotion_direction": "idle",
            "movement_profile": "full_clip_sustained",
            "movement_xy_magnitude": 0.0,
            "movement_speed": 0.0,
            "view_direction": "stationary",
            "view_profile": "full_clip_sustained",
            "yaw_amplitude": 0.0,
            "pitch_amplitude": 0.0,
            "jump": False,
            "weapon_action": "reload",
            "action_arity": "atomic",
            "zoom": False,
            "weapon_select": False,
        }
    )
    targets = row["scheduler_targets"]
    targets.update(
        {
            "net_displacement_bin": "lt64",
            "yaw_range_bin": "lt15",
            "pitch_range_bin": "lt5",
            "path_length_floor": 0,
        }
    )
    return row


def generate() -> dict[str, Any]:
    if not stage1.INPUT_PATH.is_file():
        raise capture.CaptureFailure(
            "stage1_v4_source_manifest_missing",
            str(stage1.INPUT_PATH),
        )
    population = capture.load_jsonl(stage1.INPUT_PATH)
    eligible = [
        row
        for row in population
        if row.get("dataset_role") == "foundation_no_enemy"
        and not row.get("enemy_present")
        and not row.get("route_request")
        and (row.get("action_design") or {}).get("weapon_action")
        == "reload"
    ]
    rows: list[dict[str, Any]] = []
    for index, weapon in enumerate(stage1.RELOAD_WEAPONS, 1):
        choices = sorted(
            (
                row
                for row in eligible
                if row.get("weapon") == weapon
            ),
            key=candidate_key,
        )
        if not choices:
            raise capture.CaptureFailure(
                "reload_validation_weapon_candidate_missing", weapon
            )
        rows.append(diagnostic_row(choices[0], index))

    manifest_text = canonical_lines(rows)
    write_once_or_verify(OUTPUT_MANIFEST, manifest_text)
    manifest_sha256 = capture.sha256_file(OUTPUT_MANIFEST)
    created_utc = (
        json.loads(OUTPUT_METADATA.read_text(encoding="utf-8"))[
            "created_utc"
        ]
        if OUTPUT_METADATA.is_file()
        else capture.utc_now()
    )
    metadata = {
        "schema_version": (
            "xonotic-stage1-v4-reload-validation-manifest-v1"
        ),
        "created_utc": created_utc,
        "source_commit": stage1.SOURCE_COMMIT,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "diagnostic_only": True,
        "review": {
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "rows": len(rows),
                    "path": str(OUTPUT_MANIFEST.relative_to(ROOT)),
                    "sha256": manifest_sha256,
                }
            ],
        },
    }
    write_once_or_verify(
        OUTPUT_METADATA,
        json.dumps(
            metadata, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    )
    checks = {
        "rows": len(rows) == len(stage1.RELOAD_WEAPONS),
        "weapons": {row["weapon"] for row in rows}
        == set(stage1.RELOAD_WEAPONS),
        "episode_ids_unique": len(
            {row["episode_id"] for row in rows}
        )
        == len(rows),
        "nontraining": all(
            row["split"] == SPLIT
            and row["formal_collection_authorized"] is False
            and row["training_admitted"] is False
            and capture.output_split_authorized(row)
            for row in rows
        ),
        "reload_contract": all(
            row["action_design"]["weapon_action"] == "reload"
            and row["acceptance"]["reload_success"] is True
            and row["acceptance"]["reload_weapon"]
            == row["weapon_netname"]
            and row["acceptance"]["reload_start_server_tick"]
            == (
                capture.WARMUP_TICKS
                + capture.STAGE1_RELOAD_START_OUTPUT_TICK
            )
            and row["acceptance"]["reload_duration_ticks"]
            == capture.STAGE1_RELOAD_DURATION_TICKS
            for row in rows
        ),
        "mechanics_isolated": all(
            row["action_design"]["locomotion_direction"] == "idle"
            and row["action_design"]["view_direction"] == "stationary"
            and row["action_design"]["jump"] is False
            for row in rows
        ),
    }
    audit = {
        "schema_version": (
            "xonotic-stage1-v4-reload-validation-audit-v1"
        ),
        "created_utc": capture.utc_now(),
        "checks": checks,
        "passed": all(checks.values()),
        "manifest": str(OUTPUT_MANIFEST.relative_to(ROOT)),
        "manifest_sha256": manifest_sha256,
        "source_manifest_sha256": capture.sha256_file(
            stage1.INPUT_PATH
        ),
        "selected": [
            {
                "episode_id": row["episode_id"],
                "source_episode_id": row["source_episode_id"],
                "weapon": row["weapon"],
                "map": row["map"],
                "gametype": row["gametype"],
            }
            for row in rows
        ],
    }
    OUTPUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_AUDIT.with_name(
        f".{OUTPUT_AUDIT.name}.tmp.{os.getpid()}"
    )
    temporary.write_text(
        json.dumps(
            audit, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, OUTPUT_AUDIT)
    if not audit["passed"]:
        raise capture.CaptureFailure(
            "reload_validation_manifest_audit_failed",
            capture.canonical_json(checks),
        )
    return {
        "manifest": str(OUTPUT_MANIFEST),
        "metadata": str(OUTPUT_METADATA),
        "audit": str(OUTPUT_AUDIT),
        "rows": len(rows),
        "sha256": manifest_sha256,
    }


def main() -> int:
    capture.require_conda()
    try:
        result = generate()
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
