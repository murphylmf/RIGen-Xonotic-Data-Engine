                      
"""Reference-addressable 42-appearance variant of the validated long60 run.

The capture mechanics, QA, acceleration, retry policy, and storage behavior are
inherited from ``long60_production_v1.py``.  This isolated release changes only
the actor identity distribution and its metadata contract:

* every episode binds four neutral actor slots to four distinct appearances;
* all 42 official Stage-2 model/skin/color combinations are balanced;
* every 0.8 s prompt block identifies the active appearance/ref set;
* appearance prose is removed from prompts so a future model cannot ignore the
  visual reference and recover identity from text;
* raw AVI remains node-local and is deleted after each attempt.

Clean reference pixels are a separate immutable asset release.  This script
records the exact ref-set key needed by training but deliberately does not mark
the collection training-ready before those assets and their hashes exist.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name("long60_production_v1.py")
SPEC = importlib.util.spec_from_file_location("long60_production_ref42_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import base production module: {BASE_PATH}")
prod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prod
SPEC.loader.exec_module(prod)


RELEASE_ID = "stage2_long60_multi_enemy_ref42_30h_20260828_v3"
SCHEMA_VERSION = "xonotic-stage2-long60-ref42-production-manifest-v1"
IDENTITY_LIBRARY = Path(
    "./configs/"
    "xonotic_stage2_enemy_motion_appearance_manual_v2.jsonl"
)
IDENTITY_LIBRARY_SHA256 = (
    "0376fd4b0c9fc22f0136210deee4460c31b1e5d12b5efba44aa46cf1b63cdce2"
)
REF_ASSET_RELEASE_ID = "xonotic_enemy_ref42_clean_v1"
REF_VIEWS = ("front", "left_3q", "right_3q", "side", "back_3q")
NEUTRAL_ACTOR_IDS = ("enemy_0", "enemy_1", "enemy_2", "enemy_3")
GENERIC_REF_DESCRIPTION = "the character shown in the current reference image"
ASSIGNMENT_SEED = 2608284201
APPEARANCE_PATTERN = re.compile(r"(.+)_skin([0-9]+)_color([0-9]+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Appearance:
    appearance_id: str
    model: str
    skin: int
    color: int
    description: str

    @property
    def ref_set_id(self) -> str:
        return f"{self.appearance_id}_refset_v1"


def load_appearances() -> dict[str, Appearance]:
    if not IDENTITY_LIBRARY.is_file():
        raise RuntimeError(f"appearance library missing: {IDENTITY_LIBRARY}")
    actual_hash = sha256(IDENTITY_LIBRARY)
    if actual_hash != IDENTITY_LIBRARY_SHA256:
        raise RuntimeError(
            "appearance library hash mismatch: "
            f"{actual_hash} != {IDENTITY_LIBRARY_SHA256}"
        )
    result: dict[str, Appearance] = {}
    with IDENTITY_LIBRARY.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("unit_type") != "enemy_visual":
                continue
            appearance_id = str(row["unit_id"])
            match = APPEARANCE_PATTERN.fullmatch(appearance_id)
            if match is None:
                raise RuntimeError(f"invalid appearance id: {appearance_id}")
            annotation = row.get("result") or {}
            description = str(annotation.get("appearance_phrase") or "").strip()
            if not description:
                raise RuntimeError(f"appearance description missing: {appearance_id}")
            result[appearance_id] = Appearance(
                appearance_id=appearance_id,
                model=match.group(1),
                skin=int(match.group(2)),
                color=int(match.group(3)),
                description=description,
            )
    if len(result) != 42:
        raise RuntimeError(f"expected 42 appearances, found {len(result)}")
    if Counter(item.model for item in result.values()) != {
        "erebus": 6,
        "gakmasked": 6,
        "ignis": 6,
        "nyx": 6,
        "pyria": 6,
        "seraphina": 6,
        "umbra": 6,
    }:
        raise RuntimeError("unexpected 42-appearance model distribution")
    return dict(sorted(result.items()))


APPEARANCES = load_appearances()
APPEARANCE_IDS = tuple(APPEARANCES)

                                                                    
_base_actor_ids = prod.ACTOR_IDS
_base_distribution_rows = prod.distribution_rows
_base_build_episode_scenario = prod.build_episode_scenario
_base_prepare = prod.prepare
_base_validate_manifest = prod.validate_manifest
_base_run_attempt = prod.run_attempt
_base_already_accepted = prod.already_accepted
_base_finalize = prod.finalize

                                                             
prod.RELEASE_ID = RELEASE_ID
prod.SCHEMA_VERSION = SCHEMA_VERSION
prod.DEFAULT_MANIFEST_ROOT = ROOT / "manifests" / RELEASE_ID
prod.DEFAULT_OUTPUT_ROOT = Path("./rigen_data") / RELEASE_ID


def appearance_orders() -> list[list[str]]:
    """Build deterministic, slot-balanced, distinct four-appearance casts."""
    ordered = list(APPEARANCE_IDS)
    random.Random(ASSIGNMENT_SEED).shuffle(ordered)
    full_cycles, remainder = divmod(prod.EPISODE_COUNT, len(ordered))
    result: list[list[str]] = []
    for index in range(prod.EPISODE_COUNT):
        cycle, position = divmod(index, len(ordered))
        if cycle < full_cycles:
            offsets = random.Random(ASSIGNMENT_SEED + 1009 * cycle).sample(
                range(len(ordered)), len(NEUTRAL_ACTOR_IDS)
            )
        else:
                                                                            
                                                                       
            if remainder != 36:
                raise RuntimeError(f"unexpected partial cycle: {remainder}")
            offsets = [0, 6, 12, 18]
        cast = [ordered[(position + offset) % len(ordered)] for offset in offsets]
        if len(set(cast)) != len(NEUTRAL_ACTOR_IDS):
            raise RuntimeError(f"duplicate appearance in episode {index}: {cast}")
        result.append(cast)
    return result


def distribution_rows() -> list[dict[str, Any]]:
                                                                             
                                                                              
                                
    saved_actor_ids = prod.ACTOR_IDS
    prod.ACTOR_IDS = _base_actor_ids
    try:
        rows = _base_distribution_rows()
    finally:
        prod.ACTOR_IDS = saved_actor_ids
    orders = appearance_orders()
    for index, (row, order) in enumerate(zip(rows, orders, strict=True)):
        row.update(
            {
                "schema_version": SCHEMA_VERSION,
                "release_id": RELEASE_ID,
                "episode_id": f"s2l60ref42_v3_{index:06d}",
                "distribution_seed": ASSIGNMENT_SEED + index,
                "actor_order": list(NEUTRAL_ACTOR_IDS),
                "appearance_order": order,
                "actor_bindings": [
                    {
                        "actor_id": actor_id,
                        "appearance_id": appearance_id,
                        "ref_set_id": APPEARANCES[appearance_id].ref_set_id,
                    }
                    for actor_id, appearance_id in zip(
                        NEUTRAL_ACTOR_IDS, order, strict=True
                    )
                ],
                "reference_conditioning_schema_version": (
                    "xonotic-current-enemy-ref-schedule-v1"
                ),
                "ref_asset_release_id": REF_ASSET_RELEASE_ID,
                "raw_avi_retained": False,
            }
        )
    return rows


def actors_for_row(row: dict[str, Any]) -> tuple[Any, ...]:
    kill_slots = {int(value) for value in row["kill_slots"]}
    result = []
    for slot, (actor_id, appearance_id) in enumerate(
        zip(row["actor_order"], row["appearance_order"], strict=True), 1
    ):
        appearance = APPEARANCES[appearance_id]
        health = 999.0
        if slot in kill_slots:
            if row["template"] == "controlled_return" and slot == 1:
                health = 60.0
            elif row["template"] == "controlled_return" and slot == 2:
                health = 25.0
            else:
                health = 15.0
        result.append(
            prod.base.Actor(
                slot,
                actor_id,
                appearance.model,
                appearance.skin,
                appearance.color,
                health,
                0.0,
                GENERIC_REF_DESCRIPTION,
            )
        )
    return tuple(result)


def normalize_reference_prompt(text: str) -> str:
    return text.replace(
        "The active opponent has this appearance: "
        f"{GENERIC_REF_DESCRIPTION}",
        "The active opponent has the appearance shown in the current "
        "reference image.",
    ).replace(
        f"The previous opponent was {GENERIC_REF_DESCRIPTION}",
        "The previous opponent had the appearance shown in its reference image.",
    )


def build_episode_scenario(
    row: dict[str, Any], manifest_root: Path, shared_actions: Path
) -> tuple[Path, Path]:
    scenario_path, timeline = _base_build_episode_scenario(
        row, manifest_root, shared_actions
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    binding_by_actor = {
        item["actor_id"]: item for item in row["actor_bindings"]
    }
    ref_index_by_actor = {
        actor_id: index for index, actor_id in enumerate(row["actor_order"])
    }
    for actor in scenario["actors"]:
        binding = binding_by_actor[actor["actor_id"]]
        appearance = APPEARANCES[binding["appearance_id"]]
        actor.update(
            {
                "appearance_id": appearance.appearance_id,
                "appearance_description": appearance.description,
                "ref_set_id": appearance.ref_set_id,
                "ref_asset_release_id": REF_ASSET_RELEASE_ID,
                "description": GENERIC_REF_DESCRIPTION,
            }
        )

    active_ref_schedule: list[dict[str, Any]] = []
    for prompt_row in scenario["prompt_schedule"]:
        actor_id = prompt_row.get("actor_id")
        binding = binding_by_actor.get(actor_id)
        despawned_actor_id = prompt_row.get("despawned_actor_id")
        despawned_binding = binding_by_actor.get(despawned_actor_id)
        prompt_row.update(
            {
                "appearance_id": (
                    binding["appearance_id"] if binding is not None else None
                ),
                "ref_set_id": (
                    binding["ref_set_id"] if binding is not None else None
                ),
                "ref_bank_index": (
                    ref_index_by_actor[actor_id] if binding is not None else -1
                ),
                "despawned_appearance_id": (
                    despawned_binding["appearance_id"]
                    if despawned_binding is not None
                    else None
                ),
                "prompt": normalize_reference_prompt(prompt_row["prompt"]),
            }
        )
        active_ref_schedule.append(
            {
                "block_index": prompt_row["block_index"],
                "actor_id": actor_id,
                "appearance_id": prompt_row["appearance_id"],
                "ref_set_id": prompt_row["ref_set_id"],
                "ref_bank_index": prompt_row["ref_bank_index"],
                "valid": binding is not None,
            }
        )

    scenario["schema_version"] = (
        "xonotic-stage2-long60-ref42-production-scenario-v1"
    )
    scenario["dataset_role"] = (
        "stage2_long_horizon_multi_enemy_reference_conditioning_production"
    )
    scenario["appearance_order"] = row["appearance_order"]
    scenario["actor_bindings"] = row["actor_bindings"]
    scenario["appearance_library"] = {
        "path": str(IDENTITY_LIBRARY),
        "sha256": IDENTITY_LIBRARY_SHA256,
        "annotation_method": "direct_manual_visual_review_no_vlm",
    }
    scenario["reference_conditioning_contract"] = {
        "schema_version": "xonotic-current-enemy-ref-schedule-v1",
        "mode": "blockwise_current_actor",
        "block_seconds": prod.base.PROMPT_BLOCK_SECONDS,
        "no_active_enemy_ref_index": -1,
        "stable_ref_within_actor_episode": True,
        "future_ref_visibility": False,
        "appearance_text_in_prompt": False,
        "ref_asset_release_id": REF_ASSET_RELEASE_ID,
        "ref_assets_ready": False,
    }
    scenario["active_ref_schedule"] = active_ref_schedule
    scenario["prompt_schedule_schema_version"] = (
        "xonotic-stage2-long60-75x0p8-current-ref-v1"
    )
    scenario["distribution"]["appearance_order"] = row["appearance_order"]
    scenario["distribution"]["appearance_assignment_seed"] = ASSIGNMENT_SEED
    prod.write_json_atomic(scenario_path, scenario)
    return scenario_path, timeline


def identity_registry_rows() -> list[dict[str, Any]]:
    return [
        {
            "schema_version": "xonotic-enemy-appearance-identity-registry-v1",
            "appearance_id": item.appearance_id,
            "model": item.model,
            "skin": item.skin,
            "color": item.color,
            "description": item.description,
            "ref_set_id": item.ref_set_id,
            "ref_asset_release_id": REF_ASSET_RELEASE_ID,
            "required_views": list(REF_VIEWS),
            "ref_asset_status": "pending_clean_capture",
            "source_library_path": str(IDENTITY_LIBRARY),
            "source_library_sha256": IDENTITY_LIBRARY_SHA256,
        }
        for item in APPEARANCES.values()
    ]


def greedy_canary_indices(rows: list[dict[str, Any]]) -> list[int]:
    selected = [0, 1, 2, 3]
    covered = {
        appearance
        for index in selected
        for appearance in rows[index]["appearance_order"]
    }
    remaining = set(APPEARANCE_IDS) - covered
    while remaining:
        candidates = [
            (len(set(row["appearance_order"]) & remaining), index)
            for index, row in enumerate(rows)
            if index not in selected
        ]
        gain, index = max(candidates)
        if gain <= 0:
            raise RuntimeError(f"cannot cover appearances in canary: {remaining}")
        selected.append(index)
        remaining -= set(rows[index]["appearance_order"])
    return selected


def deep_appearance_audit(
    manifest_root: Path, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    slot_counts = [Counter() for _ in NEUTRAL_ACTOR_IDS]
    checks = Counter()
    errors: list[str] = []
    for row in rows:
        order = row.get("appearance_order") or []
        counts.update(order)
        for index, appearance_id in enumerate(order):
            slot_counts[index][appearance_id] += 1
        scenario_path = ROOT / row["scenario_path"]
        if prod.base.sha256(scenario_path) != row["scenario_sha256"]:
            errors.append(f"{row['episode_id']}:scenario_hash")
            continue
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        actor_map = {item["actor_id"]: item for item in scenario["actors"]}
        expected = {
            item["actor_id"]: item for item in row["actor_bindings"]
        }
        if set(actor_map) != set(expected):
            errors.append(f"{row['episode_id']}:actor_ids")
        for actor_id, binding in expected.items():
            actor = actor_map.get(actor_id) or {}
            if actor.get("appearance_id") != binding["appearance_id"]:
                errors.append(f"{row['episode_id']}:{actor_id}:appearance")
            if actor.get("ref_set_id") != binding["ref_set_id"]:
                errors.append(f"{row['episode_id']}:{actor_id}:ref_set")
        prompts = scenario.get("prompt_schedule") or []
        refs = scenario.get("active_ref_schedule") or []
        if len(prompts) != 75 or len(refs) != 75:
            errors.append(f"{row['episode_id']}:schedule_length")
        for prompt_row, ref_row in zip(prompts, refs, strict=False):
            actor_id = prompt_row.get("actor_id")
            binding = expected.get(actor_id)
            expected_appearance = (
                binding["appearance_id"] if binding is not None else None
            )
            expected_ref_set = binding["ref_set_id"] if binding is not None else None
            if prompt_row.get("appearance_id") != expected_appearance:
                errors.append(
                    f"{row['episode_id']}:block{prompt_row.get('block_index')}:prompt_appearance"
                )
            if ref_row.get("appearance_id") != expected_appearance:
                errors.append(
                    f"{row['episode_id']}:block{prompt_row.get('block_index')}:ref_appearance"
                )
            if ref_row.get("ref_set_id") != expected_ref_set:
                errors.append(
                    f"{row['episode_id']}:block{prompt_row.get('block_index')}:ref_set"
                )
            if any(
                appearance.description in prompt_row["prompt"]
                for appearance in APPEARANCES.values()
            ):
                errors.append(
                    f"{row['episode_id']}:block{prompt_row.get('block_index')}:appearance_text_leak"
                )
        checks["scenarios"] += 1
        if len(errors) >= 100:
            break

    canaries = greedy_canary_indices(rows)
    distribution_checks = {
        "all_42_appearances": set(counts) == set(APPEARANCE_IDS),
        "four_distinct_per_episode": all(
            len(row["appearance_order"]) == 4
            and len(set(row["appearance_order"])) == 4
            for row in rows
        ),
        "neutral_actor_ids": all(
            row["actor_order"] == list(NEUTRAL_ACTOR_IDS) for row in rows
        ),
        "aggregate_count_range_171_172": (
            min(counts.values()) == 171 and max(counts.values()) == 172
        ),
        "slot_count_range_42_43": all(
            min(counter.values()) == 42 and max(counter.values()) == 43
            for counter in slot_counts
        ),
        "canary_covers_all_42": {
            appearance
            for index in canaries
            for appearance in rows[index]["appearance_order"]
        }
        == set(APPEARANCE_IDS),
        "scenario_checks_complete": checks["scenarios"] == len(rows),
        "no_errors": not errors,
    }
    return {
        "schema_version": "xonotic-stage2-long60-ref42-static-validation-v1",
        "created_utc": prod.utc_now(),
        "release_id": RELEASE_ID,
        "all_pass": all(distribution_checks.values()),
        "checks": distribution_checks,
        "errors": errors,
        "episode_count": len(rows),
        "appearance_count": len(counts),
        "appearance_usage_min": min(counts.values()),
        "appearance_usage_max": max(counts.values()),
        "appearance_usage_counts": dict(sorted(counts.items())),
        "slot_usage_minmax": [
            [min(counter.values()), max(counter.values())]
            for counter in slot_counts
        ],
        "canary_manifest_indices": canaries,
        "canary_episode_count": len(canaries),
        "appearance_library_sha256": IDENTITY_LIBRARY_SHA256,
        "ref_assets_ready": False,
    }


def prepare(manifest_root: Path) -> None:
    _base_prepare(manifest_root)
    manifest_root = manifest_root.resolve()
    rows = prod.load_jsonl(manifest_root / "manifest.jsonl")
    registry_path = manifest_root / "appearance_registry.jsonl"
    prod.write_jsonl_atomic(registry_path, identity_registry_rows())
    validation = deep_appearance_audit(manifest_root, rows)
    validation_path = manifest_root / "APPEARANCE_VALIDATION.json"
    prod.write_json_atomic(validation_path, validation)
    if not validation["all_pass"]:
        raise RuntimeError(f"appearance validation failed: {validation['checks']}")

    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "schema_version": "xonotic-stage2-long60-ref42-production-metadata-v1",
            "appearance_count": 42,
            "appearance_assignment_seed": ASSIGNMENT_SEED,
            "appearance_usage_min": validation["appearance_usage_min"],
            "appearance_usage_max": validation["appearance_usage_max"],
            "appearance_library_path": str(IDENTITY_LIBRARY),
            "appearance_library_sha256": IDENTITY_LIBRARY_SHA256,
            "appearance_registry_path": prod.relative_to_root(registry_path),
            "appearance_registry_sha256": prod.base.sha256(registry_path),
            "appearance_validation_path": prod.relative_to_root(validation_path),
            "appearance_validation_sha256": prod.base.sha256(validation_path),
            "canary_manifest_indices": validation["canary_manifest_indices"],
            "reference_conditioning": {
                "schema_version": "xonotic-current-enemy-ref-schedule-v1",
                "mode": "blockwise_current_actor",
                "ref_asset_release_id": REF_ASSET_RELEASE_ID,
                "required_views": list(REF_VIEWS),
                "ref_assets_ready": False,
                "appearance_text_in_prompt": False,
                "training_ready": False,
            },
        }
    )
    prod.write_json_atomic(metadata_path, metadata)
    prepared_path = manifest_root / "PREPARED.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared.update(
        {
            "capture_ready": True,
            "training_ready": False,
            "appearance_registry_sha256": metadata["appearance_registry_sha256"],
            "appearance_validation_sha256": metadata["appearance_validation_sha256"],
            "ref_assets_ready": False,
        }
    )
    prod.write_json_atomic(prepared_path, prepared)
    print(json.dumps(metadata, sort_keys=True), flush=True)


def validate_manifest(
    manifest_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, metadata = _base_validate_manifest(manifest_root)
    registry_path = ROOT / metadata.get("appearance_registry_path", "")
    validation_path = ROOT / metadata.get("appearance_validation_path", "")
    validation = (
        json.loads(validation_path.read_text(encoding="utf-8"))
        if validation_path.is_file()
        else {}
    )
    counts = Counter(
        appearance
        for row in rows
        for appearance in row.get("appearance_order", [])
    )
    checks = {
        "appearance_count": set(counts) == set(APPEARANCE_IDS),
        "appearance_balance": (
            bool(counts)
            and min(counts.values()) == 171
            and max(counts.values()) == 172
        ),
        "appearance_library": (
            metadata.get("appearance_library_sha256") == IDENTITY_LIBRARY_SHA256
        ),
        "registry_hash": (
            registry_path.is_file()
            and prod.base.sha256(registry_path)
            == metadata.get("appearance_registry_sha256")
        ),
        "validation_hash": (
            validation_path.is_file()
            and prod.base.sha256(validation_path)
            == metadata.get("appearance_validation_sha256")
        ),
        "validation_pass": validation.get("all_pass") is True,
        "capture_ready_training_not_claimed": (
            metadata.get("reference_conditioning", {}).get("training_ready")
            is False
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"ref42 manifest validation failed: {checks}")
    return rows, metadata


def already_accepted(output_root: Path, row: dict[str, Any]) -> bool:
    if not _base_already_accepted(output_root, row):
        return False
    record_path = prod.accepted_paths(output_root, row)["record"]
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    return (
        record.get("release_id") == RELEASE_ID
        and record.get("appearance_order") == row["appearance_order"]
        and record.get("actor_bindings") == row["actor_bindings"]
        and record.get("appearance_library_sha256") == IDENTITY_LIBRARY_SHA256
    )


def run_attempt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    row = args[1] if len(args) >= 2 else kwargs["row"]
    output_root = args[3] if len(args) >= 4 else kwargs["output_root"]
    record = _base_run_attempt(*args, **kwargs)
    record.update(
        {
            "appearance_order": row["appearance_order"],
            "actor_bindings": row["actor_bindings"],
            "appearance_library_sha256": IDENTITY_LIBRARY_SHA256,
            "ref_asset_release_id": REF_ASSET_RELEASE_ID,
            "reference_conditioning_schema_version": (
                "xonotic-current-enemy-ref-schedule-v1"
            ),
        }
    )
    paths = prod.accepted_paths(output_root, row)
    prod.write_json_atomic(paths["record"], record)
    prod.write_json_atomic(paths["accepted"], record)
    return record


def finalize(manifest_root: Path, output_root: Path) -> None:
    _base_finalize(manifest_root, output_root)
    accepted_path = output_root / "accepted.jsonl"
    accepted = prod.load_jsonl(accepted_path)
    for row in accepted:
        scenario_path = ROOT / row["scenario_path"]
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        row.update(
            {
                "appearance_order": scenario["appearance_order"],
                "actor_bindings": scenario["actor_bindings"],
                "active_ref_schedule": scenario["active_ref_schedule"],
                "reference_conditioning_contract": scenario[
                    "reference_conditioning_contract"
                ],
                "appearance_library_sha256": IDENTITY_LIBRARY_SHA256,
                "ref_asset_release_id": REF_ASSET_RELEASE_ID,
            }
        )
    prod.write_jsonl_atomic(accepted_path, accepted)
    accepted_sha256 = prod.base.sha256(accepted_path)
    for name in ("COLLECTION_STATUS.json", "COLLECTION_COMPLETE.json"):
        path = output_root / name
        report = json.loads(path.read_text(encoding="utf-8"))
        report.update(
            {
                "accepted_manifest_path": str(accepted_path),
                "accepted_manifest_sha256": accepted_sha256,
                "appearance_count": 42,
                "appearance_library_sha256": IDENTITY_LIBRARY_SHA256,
                "ref_asset_release_id": REF_ASSET_RELEASE_ID,
                "ref_assets_ready": False,
                "training_admitted": False,
            }
        )
        prod.write_json_atomic(path, report)


prod.distribution_rows = distribution_rows
prod.actors_for_row = actors_for_row
prod.build_episode_scenario = build_episode_scenario
prod.prepare = prepare
prod.validate_manifest = validate_manifest
prod.already_accepted = already_accepted
prod.run_attempt = run_attempt
prod.finalize = finalize


def main() -> int:
                                                                               
                                      
    return prod.main()


if __name__ == "__main__":
    raise SystemExit(main())
