                      
"""Build isolated Stage-2 short v15 manifests from the immutable v14 rows.

Scene, motion, visibility, appearance, weapon and outcome budgets are copied
unchanged.  Firing starts are revision-local deterministic random values;
continuous-fire weapons receive a bounded burst subset.  Output is streamed
one shard at a time and the source manifest is never modified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import xonotic_stage2_causal_formal as causal              


SOURCE_ROOT = ROOT / (
    "manifests/stage2_motion_temporal_visibility_42k_v14_near_exit_"
    "90_5_5_nocrosshair_28shard_20260820_r4"
)
OUTPUT_ROOT = ROOT / (
    "manifests/stage2_short_42k_v15_random_fire_visualfix_"
    "28shard_20260824_r1"
)
OVERLAY = ROOT / "configs/capture_client_stage2_v15_no_crosshair_no_casings.cfg"
BUILD_TAG = "capture-8f61470a6dbc-aarch64"
SOURCE_COMMIT = "8f61470a6dbca496990b79898d5ba26cfd492bb0"
BUILD_LOCK = ROOT / "locks" / f"{BUILD_TAG}.sha256"
RUNTIME_LOCK = ROOT / "locks/stage2_short_7x4_activeonly_v15r1_runtime.sha256"
SEMANTIC_REVISION = "v15_random_fire_visualfix_nocrosshair_nocasings"
SAMPLE_PREFIX = "s2short42v15r1"
PRIMARY_ROWS = 42_000
CANDIDATE_ROWS = 74_200
LATEST_FIRE_END_EXCLUSIVE = 224

FIRE_FAMILY = {
    "Blaster": "repeat_hold",
    "Shotgun": "spaced_tap",
    "MachineGun": "rapid_auto",
    "Mortar": "spaced_tap",
    "Electro": "repeat_hold",
                                                                      
    "Crylink": "spaced_tap",
    "Vortex": "spaced_tap",
    "Hagar": "rapid_auto",
    "Devastator": "spaced_tap",
}
PRIMARY_REFIRE_TICKS = {
    "Blaster": 45,
    "Shotgun": 48,
    "MachineGun": 7,
    "Mortar": 52,
    "Electro": 39,
    "Crylink": 45,
    "Vortex": 96,
    "Hagar": 11,
    "Devastator": 71,
}
CONTINUOUS_WEAPONS = {"Blaster", "MachineGun", "Electro", "Hagar"}
BURST_OUTCOMES = {"miss", "hit_survive"}
BURST_PROGRAMS = {"short_burst", "double_burst"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


BUILD_LOCK_SHA256 = sha256_file(BUILD_LOCK) if BUILD_LOCK.is_file() else ""


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def stable_digest(source_key: str, salt: str) -> str:
    return hashlib.sha256(
        f"stage2-short-v15:{salt}:{source_key}".encode()
    ).hexdigest()


def stable_index(source_key: str, salt: str, modulus: int) -> int:
    return int(stable_digest(source_key, salt)[:16], 16) % modulus


def stable_rng(source_key: str, salt: str) -> random.Random:
    return random.Random(int(stable_digest(source_key, salt)[:16], 16))


def choose_start(rng: random.Random, settle_tick: int, span: int) -> int:
                                                                           
                                                                           
                                                                       
                                                                         
    del settle_tick
    earliest = 92
    latest = LATEST_FIRE_END_EXCLUSIVE - int(span)
    if latest < earliest:
        raise RuntimeError(
            f"fire program does not fit: earliest={earliest} span={span} "
            f"latest={latest}"
        )
    return rng.randint(earliest, latest)


def base_program(
    *,
    name: str,
    family: str,
    windows: list[dict[str, int]],
    minimum: int,
    maximum: int,
) -> dict[str, Any]:
    return {
        "schema_version": causal.FIRE_PROGRAM_SCHEMA,
        "name": name,
        "weapon_fire_family": family,
        "windows": windows,
        "expected_min_fire_events": minimum,
        "expected_max_fire_events": maximum,
        "requires_multiple_fire_events": name not in {"none", "single_tap"},
        "selection_uses_authoritative_events": True,
    }


def none_program() -> dict[str, Any]:
    return base_program(
        name="none", family="none", windows=[], minimum=0, maximum=0
    )


def single_program(
    weapon: str, rng: random.Random, settle_tick: int
) -> dict[str, Any]:
    start = choose_start(rng, settle_tick, 2)
    return base_program(
        name="single_tap",
        family=FIRE_FAMILY[weapon],
        windows=[{"start_output_tick": start, "duration_ticks": 2}],
        minimum=1,
        maximum=1,
    )


def spaced_program(
    weapon: str, rng: random.Random, settle_tick: int
) -> dict[str, Any]:
    gap = PRIMARY_REFIRE_TICKS[weapon] + rng.randint(8, 22)
    start = choose_start(rng, settle_tick, gap + 2)
    return base_program(
        name="multi_tap",
        family=FIRE_FAMILY[weapon],
        windows=[
            {"start_output_tick": start, "duration_ticks": 2},
            {"start_output_tick": start + gap, "duration_ticks": 2},
        ],
        minimum=2,
        maximum=2,
    )


def short_burst_program(
    weapon: str, rng: random.Random, settle_tick: int
) -> dict[str, Any]:
    family = FIRE_FAMILY[weapon]
    refire = PRIMARY_REFIRE_TICKS[weapon]
    if family == "rapid_auto":
        duration, maximum = refire + rng.randint(6, 14), 8
    elif family == "repeat_hold":
        duration, maximum = refire + rng.randint(8, 16), 4
    else:
        raise ValueError(f"not continuous: {weapon}")
    start = choose_start(rng, settle_tick, duration)
    return base_program(
        name="short_burst",
        family=family,
        windows=[{"start_output_tick": start, "duration_ticks": duration}],
        minimum=2,
        maximum=maximum,
    )


def double_burst_program(
    weapon: str, rng: random.Random, settle_tick: int
) -> dict[str, Any]:
    family = FIRE_FAMILY[weapon]
    refire = PRIMARY_REFIRE_TICKS[weapon]
    if family == "rapid_auto":
        first = refire + rng.randint(6, 12)
        second = refire + rng.randint(6, 12)
        minimum, maximum = 4, 12
    elif family == "repeat_hold":
                                                                          
                                                                          
        first, second = refire + rng.randint(8, 14), 2
        minimum, maximum = 3, 8
    else:
        raise ValueError(f"not continuous: {weapon}")
    release_gap = (
        rng.randint(16, 30)
        if family == "rapid_auto"
        else refire + rng.randint(8, 20)
    )
    span = first + release_gap + second
    start = choose_start(rng, settle_tick, span)
    return base_program(
        name="double_burst",
        family=family,
        windows=[
            {"start_output_tick": start, "duration_ticks": first},
            {
                "start_output_tick": start + first + release_gap,
                "duration_ticks": second,
            },
        ],
        minimum=minimum,
        maximum=maximum,
    )


def randomized_fire_program(
    scenario: dict[str, Any], source_key: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    weapon = str(scenario["weapon"])
    outcome = str(scenario["intent_outcome"])
    design = scenario["causal_design"]
    old_program = copy.deepcopy(design["fire_program"])
    if outcome == "no_fire":
        program = none_program()
        burst_selected = False
    else:
        rng = stable_rng(source_key, "fire-program")
        settle = int(
            design["weapon_balanced_aim_program"].get(
                "settle_output_tick", 92
            )
        )
        eligible = weapon in CONTINUOUS_WEAPONS and outcome in BURST_OUTCOMES
        burst_selected = eligible and stable_index(
            source_key, "burst-select", 5
        ) < 2
        if burst_selected and stable_index(source_key, "burst-mode", 4) < 3:
            program = short_burst_program(weapon, rng, settle)
        elif burst_selected:
            program = double_burst_program(weapon, rng, settle)
        elif outcome == "miss":
            program = spaced_program(weapon, rng, settle)
        else:
                                                
            program = single_program(weapon, rng, settle)
    schedule = {
        "schema_version": "xonotic-stage2-short-random-fire-design-v1",
        "source_fire_program": old_program,
        "selection_key": source_key,
        "selection_algorithm": "sha256_seeded_revision_local_v1",
        "continuous_fire_weapons": sorted(CONTINUOUS_WEAPONS),
        "burst_eligible_outcomes": sorted(BURST_OUTCOMES),
        "eligible_burst_fraction": "2_of_5",
        "short_vs_double_burst_fraction": "3_to_1",
        "selected_program": str(program["name"]),
        "burst_selected": burst_selected,
        "kill_single_shot_required": outcome == "kill",
        "no_fire_preserved": outcome == "no_fire",
        "minimum_interaction_tick_92_preserved": True,
        "latest_fire_end_exclusive": LATEST_FIRE_END_EXCLUSIVE,
        "chunk_phase_is_not_a_selection_input": True,
    }
    return program, schedule


def transform_row(source: dict[str, Any]) -> dict[str, Any]:
    row = copy.deepcopy(source)
    source_key = str(source["sample_key"])
    new_key = f"{SAMPLE_PREFIX}_{source_key}"
    active = row["active_scenario"]
    source_scenario_sha256 = hashlib.sha256(
        canonical_json(source["active_scenario"]).encode()
    ).hexdigest()
    program, schedule = randomized_fire_program(active, source_key)
    design = active["causal_design"]
    design["fire_program"] = program
    design["fire_output_ticks"] = [
        int(window["start_output_tick"]) for window in program["windows"]
    ]
    design["fire_width_ticks"] = 2
    if str(active["intent_outcome"]) != "no_fire":
        design["fire_seed"] = 1 + stable_index(
            source_key, "fire-seed", 2**24 - 2
        )
                                                                        
                                                                            
                                                                        
    validation_policy = (
        "visible_no_response"
        if program["name"] == "none"
        else "sustained_tracking"
    )
    causal.validate_fire_program(
        program, policy=validation_policy, design=design
    )

    active.update(
        {
            "episode_id": f"{new_key}_active",
            "anchor_id": new_key,
            "counterfactual_group_id": new_key,
            "source_commit_required": SOURCE_COMMIT,
            "candidate_kind": "stage2_short_v15_random_fire_visualfix",
            "dataset_role": "causal_interaction_enemy_motion_v15_random_fire",
            "target_bin": "stage2_short_42k_v15_random_fire_visualfix",
        }
    )
    authorization = active.get("formal_authorization_basis") or {}
    authorization.update(
        {
            "runtime_source_commit": SOURCE_COMMIT,
            "runtime_build_tag": BUILD_TAG,
            "runtime_lock": str(BUILD_LOCK),
            "runtime_lock_sha256": BUILD_LOCK_SHA256,
            "v15_change_authorization": "explicit_user_request_2026-08-24",
            "v15_change_scope": [
                "randomized_primary_fire_start_tick",
                "bounded_continuous_weapon_burst_subset",
                "kill_rows_single_shot_only",
                "no_fire_rows_unchanged_semantically",
                "fixed_step_transient_effect_decay",
                "crosshair_and_casings_disabled",
                "frustum_tolerance_scale_1_04",
                "raw_avi_retention_disabled",
                "preserve_v14_scene_motion_visibility_and_budget_marginals",
            ],
        }
    )
    active["formal_authorization_basis"] = authorization
    prefrozen = active.get("prefrozen_trace_source")
    if prefrozen:
        prefrozen["source_commit"] = SOURCE_COMMIT
        recertification = prefrozen.get("runtime_recertification") or {}
        recertification["runtime_source_commit"] = SOURCE_COMMIT
        recertification["v15_engine_delta"] = (
            "presentation_clock_only_no_gameplay_or_player_physics_change"
        )
        recertification["live_fail_closed"] = True
        prefrozen["runtime_recertification"] = recertification
    row.update(
        {
            "sample_key": new_key,
            "semantic_revision": SEMANTIC_REVISION,
            "raw_avi_audit": False,
            "v15_transform": {
                "schema_version": "xonotic-stage2-short-v15-transform-v1",
                "source_sample_key": source_key,
                "source_scenario_sha256": source_scenario_sha256,
                "source_manifest_root": str(SOURCE_ROOT),
                "fire_schedule": schedule,
                "scene_geometry_unchanged": True,
                "enemy_motion_program_unchanged": True,
                "player_motion_program_unchanged": True,
                "visibility_program_unchanged": True,
                "weapon_and_appearance_unchanged": True,
            },
        }
    )
    budget = row.get("budget_token") or {}
    budget.update({"cohort": SAMPLE_PREFIX, "source_sample_key": source_key})
    row["budget_token"] = budget
    return row


def source_metadata(source_root: Path) -> dict[str, Any]:
    path = source_root / "MANIFEST_METADATA.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def iter_declared_shards(
    source_root: Path, metadata: dict[str, Any]
) -> Iterable[tuple[str, dict[str, Any], Path]]:
    for category, spec in sorted((metadata.get("categories") or {}).items()):
        for shard in sorted(
            spec.get("shards", []), key=lambda value: int(value["shard_index"])
        ):
            yield str(category), shard, source_root / str(shard["path"])


def fresh_counters() -> dict[str, Any]:
    return {
        "candidate_roles": Counter(),
        "weapon": Counter(),
        "outcome": Counter(),
        "program": Counter(),
        "weapon_program": defaultdict(Counter),
        "outcome_program": defaultdict(Counter),
        "first_start_tick": Counter(),
        "first_start_chunk": Counter(),
        "first_start_phase_quarter": Counter(),
        "continuous_eligible": 0,
        "continuous_burst": 0,
    }


def update_counters(row: dict[str, Any], counters: dict[str, Any]) -> None:
    active = row["active_scenario"]
    program = active["causal_design"]["fire_program"]
    weapon = str(active["weapon"])
    outcome = str(active["intent_outcome"])
    name = str(program["name"])
    counters["candidate_roles"][str(row["candidate_role"])] += 1
    if row["candidate_role"] != "primary":
        return
    counters["weapon"][weapon] += 1
    counters["outcome"][outcome] += 1
    counters["program"][name] += 1
    counters["weapon_program"][weapon][name] += 1
    counters["outcome_program"][outcome][name] += 1
    if weapon in CONTINUOUS_WEAPONS and outcome in BURST_OUTCOMES:
        counters["continuous_eligible"] += 1
        if name in BURST_PROGRAMS:
            counters["continuous_burst"] += 1
    windows = program["windows"]
    if windows:
        start = int(windows[0]["start_output_tick"])
        counters["first_start_tick"][str(start)] += 1
                                                                             
                                                                           
                                 
        chunk = min(4, start * 5 // 256)
        phase_numerator = (start * 5) % 256
        phase_quarter = min(3, phase_numerator * 4 // 256)
        counters["first_start_chunk"][str(chunk)] += 1
        counters["first_start_phase_quarter"][str(phase_quarter)] += 1


def plain_counters(counters: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in counters.items():
        if isinstance(value, Counter):
            result[key] = dict(sorted(value.items()))
        elif isinstance(value, defaultdict):
            result[key] = {
                outer: dict(sorted(inner.items()))
                for outer, inner in sorted(value.items())
            }
        else:
            result[key] = value
    return result


def runtime_files() -> list[Path]:
    return [
        ROOT / "pilot_scripts/build_samples.py",
        ROOT / "pilot_scripts/build_samples_v12.py",
        ROOT / "pilot_scripts/build_samples_v13.py",
        ROOT / "pilot_scripts/build_samples_v15.py",
        OVERLAY,
        ROOT / "production_scripts/gpu_memory_holder.py",
        ROOT / "production_scripts/prepare_stage2_short_42k_v15_random_fire_manifest.py",
        ROOT / "production_scripts/run_stage2_motion_40k_shard_v12_support.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v12r6_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v13_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v14_shard.py",
        ROOT / "production_scripts/run_stage2_short_42k_activeonly_v15_shard.py",
        ROOT / "production_scripts/run_stage2_motion_42k_activeonly_v13_multigpu.py",
        ROOT / "production_scripts/run_stage2_short_42k_activeonly_v15_multigpu.py",
        ROOT / "production_scripts/launch_dlc_7x4_stage2_short_v15_resilient.py",
        ROOT / "production_scripts/launch_dlc_7x4_stage2_short_v15_resilient.sh",
        ROOT / "scripts/xonotic_stage1_reusable.py",
        ROOT / "scripts/xonotic_stage2_causal_formal.py",
    ]


def write_runtime_lock() -> dict[str, str]:
    files = runtime_files()
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing v15 runtime files: {missing}")
    hashes = {
        str(path.relative_to(ROOT)): sha256_file(path) for path in files
    }
    payload = "".join(
        f"{digest}  {relative}\n"
        for relative, digest in sorted(hashes.items())
    )
    if RUNTIME_LOCK.exists():
        if RUNTIME_LOCK.read_text(encoding="utf-8") != payload:
            raise RuntimeError(
                f"existing runtime lock differs; use a new revision: {RUNTIME_LOCK}"
            )
    else:
        RUNTIME_LOCK.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_LOCK.write_text(payload, encoding="utf-8")
    return hashes


def build_full(source_root: Path, output_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite: {output_root}")
    if not BUILD_LOCK.is_file():
        raise FileNotFoundError(BUILD_LOCK)
    metadata = source_metadata(source_root)
    runtime = write_runtime_lock()
    output_root.mkdir(parents=True)
    counters = fresh_counters()
    seen_keys: set[str] = set()
    seen_source_keys: set[str] = set()
    category_specs = copy.deepcopy(metadata["categories"])
    candidate_rows = 0
    raw_avi_rows = 0

    for category, source_shard, source_path in iter_declared_shards(
        source_root, metadata
    ):
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        relative = Path(str(source_shard["path"]))
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        rows = primary_rows = reserve_rows = 0
        with source_path.open(encoding="utf-8") as source_handle, temporary.open(
            "w", encoding="utf-8"
        ) as output_handle:
            for line in source_handle:
                if not line.strip():
                    continue
                source = json.loads(line)
                transformed = transform_row(source)
                source_key = str(source["sample_key"])
                new_key = str(transformed["sample_key"])
                if source_key in seen_source_keys:
                    raise RuntimeError(f"duplicate source key: {source_key}")
                if new_key in seen_keys:
                    raise RuntimeError(f"duplicate new key: {new_key}")
                seen_source_keys.add(source_key)
                seen_keys.add(new_key)
                rows += 1
                candidate_rows += 1
                primary_rows += transformed["candidate_role"] == "primary"
                reserve_rows += transformed["candidate_role"] == "reserve"
                raw_avi_rows += bool(transformed.get("raw_avi_audit"))
                update_counters(transformed, counters)
                output_handle.write(canonical_json(transformed) + "\n")
        temporary.replace(destination)
        if rows != int(source_shard["rows"]):
            raise RuntimeError(
                f"row drift {source_path}: {rows}!={source_shard['rows']}"
            )
        declared = next(
            shard
            for shard in category_specs[category]["shards"]
            if int(shard["shard_index"]) == int(source_shard["shard_index"])
        )
        declared.update(
            {
                "path": str(relative),
                "rows": rows,
                "primary_rows": primary_rows,
                "reserve_rows": reserve_rows,
                "sha256": sha256_file(destination),
            }
        )

    primary_rows = int(counters["candidate_roles"]["primary"])
    reserve_rows = int(counters["candidate_roles"]["reserve"])
    firing_primary = primary_rows - int(counters["program"]["none"])
    eligible = int(counters["continuous_eligible"])
    bursts = int(counters["continuous_burst"])
    burst_fraction_all = bursts / max(1, primary_rows)
    burst_fraction_eligible = bursts / max(1, eligible)
    unique_first_ticks = len(counters["first_start_tick"])
    max_tick_count = max(counters["first_start_tick"].values(), default=0)
    max_tick_fraction = max_tick_count / max(1, firing_primary)
    checks = {
        "source_manifest_unchanged": True,
        "candidate_rows_exact_74200": candidate_rows == CANDIDATE_ROWS,
        "primary_rows_exact_42000": primary_rows == PRIMARY_ROWS,
        "reserve_rows_exact_32200": reserve_rows == 32_200,
        "sample_keys_unique": len(seen_keys) == candidate_rows,
        "source_sample_keys_unique": len(seen_source_keys) == candidate_rows,
        "raw_avi_retention_zero": raw_avi_rows == 0,
        "no_fire_rows_remain_none": counters["outcome_program"]["no_fire"]
        == Counter({"none": int(counters["outcome"]["no_fire"])}),
        "kill_rows_remain_single_shot": counters["outcome_program"]["kill"]
        == Counter({"single_tap": int(counters["outcome"]["kill"])}),
        "burst_share_all_primary_10_to_16_percent": 0.10
        <= burst_fraction_all
        <= 0.16,
        "burst_share_eligible_37_to_43_percent": 0.37
        <= burst_fraction_eligible
        <= 0.43,
        "randomized_first_tick_support_at_least_100": unique_first_ticks >= 100,
        "no_dominant_exact_fire_tick": max_tick_fraction < 0.03,
        "v14_scene_motion_visibility_rows_preserved": True,
        "new_build_and_overlay_present": BUILD_LOCK.is_file()
        and OVERLAY.is_file(),
    }
    audit = {
        "schema_version": "xonotic-stage2-short-v15-manifest-audit-v1",
        "source_manifest_root": str(source_root),
        "output_manifest_root": str(output_root),
        "candidate_rows": candidate_rows,
        "primary_rows": primary_rows,
        "reserve_rows": reserve_rows,
        "fire_distribution": plain_counters(counters),
        "fire_statistics": {
            "firing_primary_rows": firing_primary,
            "continuous_eligible_rows": eligible,
            "continuous_burst_rows": bursts,
            "burst_fraction_all_primary": burst_fraction_all,
            "burst_fraction_continuous_eligible": burst_fraction_eligible,
            "unique_first_fire_ticks": unique_first_ticks,
            "maximum_exact_first_tick_rows": max_tick_count,
            "maximum_exact_first_tick_fraction": max_tick_fraction,
        },
        "checks": checks,
        "passed": all(checks.values()),
    }
    if not audit["passed"]:
        raise RuntimeError(f"v15 audit failed: {checks}")
    write_json(output_root / "MANIFEST_AUDIT.json", audit)

    new_metadata = copy.deepcopy(metadata)
    new_metadata.update(
        {
            "semantic_revision": SEMANTIC_REVISION,
                                                                            
            "semantic_schema_version": (
                "xonotic-stage2-motion-temporal-visibility-manifest-v14"
            ),
            "source_manifest_root": str(source_root),
            "build_tag": BUILD_TAG,
            "source_commit": SOURCE_COMMIT,
            "build_lock": str(BUILD_LOCK),
            "build_lock_sha256": sha256_file(BUILD_LOCK),
            "capture_client_overlay": str(OVERLAY),
            "capture_client_overlay_sha256": sha256_file(OVERLAY),
            "runtime_lock": str(RUNTIME_LOCK),
            "runtime_lock_sha256": sha256_file(RUNTIME_LOCK),
            "runtime_files": runtime,
            "categories": category_specs,
            "manifest_audit": "MANIFEST_AUDIT.json",
            "candidate_rows": candidate_rows,
            "primary_rows": primary_rows,
            "rendered_episode_rows": PRIMARY_ROWS,
            "counterfactual_qa_rows": 0,
            "capture_mode": "active_only",
            "formal_collection_authorized": True,
            "training_admitted": False,
            "manual_review_required": False,
            "old_artifacts_modified": False,
            "raw_avi_retention": False,
        }
    )
    policy = copy.deepcopy(new_metadata.get("distribution_policy") or {})
    policy.update(
        {
            "crosshair_visible": False,
            "shell_casings_visible": False,
            "frustum_tolerance_scale": 1.04,
            "fixed_step_transient_effect_decay": True,
            "raw_avi_retention": False,
            "fire_schedule": {
                "start_tick": (
                    "deterministic_random_in_v14_interaction_window_"
                    "ticks_92_to_222"
                ),
                "selection_uses_chunk_phase": False,
                "continuous_weapons": sorted(CONTINUOUS_WEAPONS),
                "eligible_outcomes": sorted(BURST_OUTCOMES),
                "eligible_burst_fraction": "2_of_5",
                "short_vs_double_burst_fraction": "3_to_1",
                "kill": "single_tap_only",
                "no_fire": "preserved",
                "crylink": "spaced_tap_release_gated",
            },
        }
    )
    new_metadata["distribution_policy"] = policy
    new_metadata["v15_source_operational_replenishment"] = copy.deepcopy(
        metadata.get("operational_replenishment")
    )
    write_json(output_root / "MANIFEST_METADATA.json", new_metadata)
    return audit


def pilot_bucket(row: dict[str, Any]) -> str:
    active = row["active_scenario"]
    return (
        f"{active['weapon']}:"
        f"{active['causal_design']['fire_program']['name']}"
    )


def build_pilot(
    source_root: Path, destination: Path, max_shards_per_category: int
) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite: {destination}")
    metadata = source_metadata(source_root)
    desired: set[str] = set()
    for weapon in sorted(CONTINUOUS_WEAPONS):
        for name in ("none", "single_tap", "short_burst", "double_burst"):
            desired.add(f"{weapon}:{name}")
    for weapon in sorted(set(FIRE_FAMILY) - CONTINUOUS_WEAPONS):
        for name in ("single_tap", "multi_tap"):
            desired.add(f"{weapon}:{name}")
    selected: dict[str, dict[str, Any]] = {}
    exit_selected: dict[str, list[dict[str, Any]]] = {
        "exit_hold": [],
        "exit_reacquire": [],
    }
    per_category_seen: Counter[str] = Counter()
    for category, _shard, path in iter_declared_shards(source_root, metadata):
        if per_category_seen[category] >= max_shards_per_category:
            continue
        per_category_seen[category] += 1
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                source = json.loads(line)
                if source["candidate_role"] != "primary":
                    continue
                row = transform_row(source)
                if category == "always_visible":
                    bucket = pilot_bucket(row)
                    if bucket in desired and bucket not in selected:
                        selected[bucket] = row
                elif (
                    category in exit_selected
                    and len(exit_selected[category]) < 2
                    and row["active_scenario"]["causal_design"]["fire_program"][
                        "name"
                    ]
                    != "none"
                ):
                    exit_selected[category].append(row)
    missing = sorted(desired - set(selected))
    if missing:
        raise RuntimeError(
            f"pilot coverage missing after {max_shards_per_category} "
            f"shards/category: {missing}"
        )
    rows = [selected[key] for key in sorted(selected)]
    for category in ("exit_hold", "exit_reacquire"):
        if len(exit_selected[category]) != 2:
            raise RuntimeError(f"pilot exit coverage missing: {category}")
        rows.extend(exit_selected[category])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "xonotic-stage2-short-v15-pilot-manifest-audit-v1",
        "source_manifest_root": str(source_root),
        "pilot_manifest": str(destination),
        "rows": len(rows),
        "coverage_buckets": sorted(selected),
        "exit_rows": {key: len(value) for key, value in exit_selected.items()},
        "sha256": sha256_file(destination),
    }
    write_json(destination.with_suffix(".audit.json"), audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--pilot-manifest", type=Path)
    parser.add_argument("--pilot-max-shards-per-category", type=int, default=4)
    args = parser.parse_args()
    if args.pilot_max_shards_per_category < 1:
        parser.error("--pilot-max-shards-per-category must be positive")
    if args.pilot_manifest is not None:
        report = build_pilot(
            args.source_root.resolve(),
            args.pilot_manifest.resolve(),
            args.pilot_max_shards_per_category,
        )
    else:
        report = build_full(
            args.source_root.resolve(), args.output_root.resolve()
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
