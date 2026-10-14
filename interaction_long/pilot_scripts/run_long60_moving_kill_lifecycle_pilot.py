                      
"""Run an isolated 60 s multi-enemy moving-kill lifecycle pilot.

This wrapper reuses the validated long60 capture/render path but changes only
the pilot manifest and QA contract.  Two opponents must be killed while both
the opponent and player are moving; each corpse must remain motionless, then
despawn on the frozen timeline before a distinct opponent appears.
"""

from __future__ import annotations

import html
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


BASE_PATH = Path(__file__).with_name("run_long60_multi_pilot.py")
SPEC = importlib.util.spec_from_file_location("long60_multi_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import base pilot: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


def actor_with_health(actor: Any, health: float) -> Any:
    return base.Actor(
        actor.slot,
        actor.actor_id,
        actor.model,
        actor.skin,
        actor.color,
        health,
        actor.armor,
        actor.description,
    )


                                                                             
                                                                              
                                                                 
LIFECYCLE_ACTORS = (
    actor_with_health(base.ACTORS[0], 15.0),
    actor_with_health(base.ACTORS[1], 999.0),
    actor_with_health(base.ACTORS[2], 15.0),
    actor_with_health(base.ACTORS[3], 999.0),
)
ORIGINAL_VARIANTS = dict(base.VARIANTS)
LIFECYCLE_SEGMENTS = base.VARIANTS["four_distinct"]
KILL_BLOCK_BY_SLOT = {1: 9, 3: 49}
EXPECTED_KILL_ACTOR_IDS = {
    LIFECYCLE_ACTORS[slot - 1].actor_id for slot in KILL_BLOCK_BY_SLOT
}

                                                                            
                                                                           
base.ACTORS = LIFECYCLE_ACTORS
base.VARIANTS = {"moving_kill_lifecycle": LIFECYCLE_SEGMENTS}


def lifecycle_prompt_schedule(
    segments: tuple[Any, ...],
) -> list[dict[str, Any]]:
    actor_by_slot = {actor.slot: actor for actor in LIFECYCLE_ACTORS}
    killed_segment_by_end = {
        segment.end_block: segment
        for segment in segments
        if segment.slot in KILL_BLOCK_BY_SLOT
        and segment.start_block
        <= KILL_BLOCK_BY_SLOT[segment.slot]
        < segment.end_block
    }
    rows: list[dict[str, Any]] = []
    for block in range(base.PROMPT_BLOCKS):
        segment = next(
            (
                item
                for item in segments
                if item.start_block <= block < item.end_block
            ),
            None,
        )
        previous_killed = killed_segment_by_end.get(block)
        if segment is None:
            actor_id = None
            if previous_killed is not None:
                previous_actor = actor_by_slot[previous_killed.slot]
                identity = (
                    "The previous opponent was "
                    f"{previous_actor.description}"
                )
                motion = (
                    "The previous opponent's motionless corpse disappears at "
                    "the start of this block. No opponent remains visible."
                )
                phase = "despawn"
                despawned_actor_id = previous_actor.actor_id
            else:
                identity = "No opponent is active during this block."
                motion = "No enemy is visible during this block."
                phase = "no_enemy"
                despawned_actor_id = None
        else:
            actor = actor_by_slot[segment.slot]
            actor_id = actor.actor_id
            despawned_actor_id = None
            identity = (
                "The active opponent has this appearance: "
                f"{actor.description}"
            )
            kill_block = KILL_BLOCK_BY_SLOT.get(segment.slot)
            first = block == segment.start_block
            last = block == segment.end_block - 1
            if kill_block is not None and block > kill_block:
                motion = (
                    "The opponent starts this block dead and remains a "
                    "motionless corpse throughout the block."
                )
                phase = "dead"
            elif kill_block is not None and block == kill_block:
                motion = (
                    f"The opponent {segment.motion_text}. The player fires the "
                    "MachineGun while moving. The opponent is killed while "
                    "still moving during this block, falls, and remains dead "
                    "through the end of the block."
                )
                phase = "killed"
            else:
                if first:
                    qualifier = "The same" if segment.returning else "A new"
                    motion = (
                        f"{qualifier} opponent enters from the "
                        f"{segment.entry_side} and {segment.motion_text}."
                    )
                    phase = "enter"
                elif last:
                    motion = (
                        f"The opponent {segment.motion_text} and leaves the "
                        f"view through the {segment.exit_side}."
                    )
                    phase = "exit"
                else:
                    motion = f"The opponent {segment.motion_text}."
                    phase = "in_view"
                if segment.jump_block == block:
                    motion += (
                        " The opponent jumps once while preserving that "
                        "horizontal motion."
                    )
                if block in segment.fire_blocks:
                    motion += (
                        " The player fires the MachineGun while moving, hits "
                        "the opponent, and the opponent remains alive."
                    )
        text = (
            f"{base.ENVIRONMENT_TEXT}\n"
            "[ACTIVE OPPONENT IDENTITY]\n"
            f"{identity}\n"
            "[CURRENT OPPONENT MOTION, VISIBILITY, AND INTERACTION]\n"
            f"{motion}"
        )
        rows.append(
            {
                "block_index": block,
                "start_seconds": round(block * base.PROMPT_BLOCK_SECONDS, 1),
                "end_seconds": round(
                    (block + 1) * base.PROMPT_BLOCK_SECONDS, 1
                ),
                "actor_id": actor_id,
                "despawned_actor_id": despawned_actor_id,
                "visibility_phase": phase,
                "prompt": text,
            }
        )
    return rows


original_build_scenario = base.build_scenario


def lifecycle_build_scenario(*args: Any, **kwargs: Any) -> dict[str, Any]:
    scenario = original_build_scenario(*args, **kwargs)
    scenario["schema_version"] = (
        "xonotic-stage2-long60-multi-enemy-moving-kill-pilot-v1"
    )
    scenario["dataset_role"] = (
        "stage2_long_horizon_multi_enemy_moving_kill_lifecycle_pilot"
    )
    scenario["lifecycle_policy"] = {
        "schema_version": "xonotic-stage2-long60-lifecycle-v1",
        "expected_kill_count": len(EXPECTED_KILL_ACTOR_IDS),
        "expected_kill_actor_ids": sorted(EXPECTED_KILL_ACTOR_IDS),
        "kill_block_by_actor_id": {
            LIFECYCLE_ACTORS[slot - 1].actor_id: block
            for slot, block in KILL_BLOCK_BY_SLOT.items()
        },
        "kill_requires_enemy_moving": True,
        "kill_requires_player_moving": True,
        "postdeath_motion_lock_required": True,
        "corpse_visible_until_segment_end": True,
        "despawn_at_segment_end": True,
        "respawn_same_actor_after_death": False,
    }
    for encounter in scenario["encounters"]:
        slot = next(
            actor.slot
            for actor in LIFECYCLE_ACTORS
            if actor.actor_id == encounter["actor_id"]
        )
        encounter["intent_outcome"] = (
            "kill" if slot in KILL_BLOCK_BY_SLOT else "hit_survive"
        )
        encounter["kill_block"] = KILL_BLOCK_BY_SLOT.get(slot)
        encounter["despawn_block"] = (
            encounter["end_block"] if slot in KILL_BLOCK_BY_SLOT else None
        )
    scenario["formal_collection_authorized"] = False
    scenario["training_admitted"] = False
    return scenario


original_validate_episode = base.validate_episode


def horizontal_speed(vector: list[float]) -> float:
    return math.hypot(float(vector[0]), float(vector[1]))


def lifecycle_validate_episode(*args: Any, **kwargs: Any) -> dict[str, Any]:
    scenario = args[0] if args else kwargs["scenario"]
    live = args[2] if len(args) >= 3 else kwargs["live"]
    lifecycle_policy = scenario.get("lifecycle_policy") or {}
    killed_aim_region_max_degrees = float(
        lifecycle_policy.get("killed_aim_region_max_degrees", 8.0)
    )
    if not (
        math.isfinite(killed_aim_region_max_degrees)
        and 0.0 < killed_aim_region_max_degrees <= 20.0
    ):
        raise RuntimeError(
            "invalid killed aim-region threshold: "
            f"{killed_aim_region_max_degrees}"
        )
    qa = original_validate_episode(*args, **kwargs)
    telemetry = base.load_jsonl(Path(live["server_telemetry"]))
    states = [row for row in telemetry if row.get("kind") == "state"]
    switches = [row for row in telemetry if row.get("kind") == "actor_switch"]
    damage_events = [
        row
        for row in telemetry
        if row.get("kind") == "event"
        and row.get("event") == "damage"
        and int(row.get("killed", 0))
    ]
    state_by_tick = {int(row["server_tick"]): row for row in states}
    encounter_by_actor = {
        row["actor_id"]: row for row in scenario["encounters"]
    }
    kill_records: list[dict[str, Any]] = []
    for event in damage_events:
        kill_tick = int(event["server_tick"])
        state = state_by_tick.get(kill_tick)
        enemy = state.get("enemy") if state else None
        actor_id = enemy.get("actor_id") if isinstance(enemy, dict) else None
        encounter = encounter_by_actor.get(actor_id)
        if encounter is None:
            continue
        start_tick = base.capture.WARMUP_TICKS + int(
            encounter["start_block"] * base.PROMPT_BLOCK_SECONDS * 64
        )
                                                                            
                                                                             
        despawn_tick = base.capture.WARMUP_TICKS + math.ceil(
            encounter["end_block"] * base.PROMPT_BLOCK_SECONDS * 64
        )
        prior_alive = [
            row
            for row in states
            if max(start_tick, kill_tick - 8) <= int(row["server_tick"]) <= kill_tick
            and isinstance(row.get("enemy"), dict)
            and row["enemy"].get("actor_id") == actor_id
            and float(row["enemy"].get("health", 0.0)) >= 1.0
        ]
        enemy_predeath_speed = max(
            (
                horizontal_speed(row["enemy"]["velocity"])
                for row in prior_alive
            ),
            default=0.0,
        )
        player_speed = horizontal_speed(state["post"]["velocity"])
        player_command = math.hypot(
            float(state["applied_action"]["forward"]),
            float(state["applied_action"]["strafe"]),
        )
        dead_states = [
            row
            for row in states
            if kill_tick + 1 <= int(row["server_tick"]) < despawn_tick
            and isinstance(row.get("enemy"), dict)
            and row["enemy"].get("actor_id") == actor_id
        ]
        death_origin = (
            dead_states[0]["enemy"]["origin"] if dead_states else [0.0, 0.0, 0.0]
        )
        maximum_postdeath_displacement = max(
            (
                math.dist(row["enemy"]["origin"], death_origin)
                for row in dead_states
            ),
            default=float("inf"),
        )
        maximum_postdeath_speed = max(
            (
                math.sqrt(
                    sum(float(value) ** 2 for value in row["enemy"]["velocity"])
                )
                for row in dead_states
            ),
            default=float("inf"),
        )
        despawn_state = state_by_tick.get(despawn_tick)
        despawn_switch = next(
            (
                row
                for row in switches
                if int(row["server_tick"]) == despawn_tick
                and int(row["active_slot"]) == 0
                and row.get("previous_actor_id") == actor_id
            ),
            None,
        )
        next_switch = next(
            (
                row
                for row in switches
                if int(row["server_tick"]) > despawn_tick
                and int(row["active_slot"]) > 0
            ),
            None,
        )
        realized_block = int(
            (kill_tick - base.capture.WARMUP_TICKS)
            // int(base.PROMPT_BLOCK_SECONDS * 64)
        )
        kill_records.append(
            {
                "actor_id": actor_id,
                "kill_server_tick": kill_tick,
                "kill_seconds": (
                    kill_tick - base.capture.WARMUP_TICKS
                )
                / 64.0,
                "declared_kill_block": encounter["kill_block"],
                "realized_kill_block": realized_block,
                "enemy_predeath_horizontal_speed": enemy_predeath_speed,
                "player_horizontal_speed_at_kill": player_speed,
                "player_command_magnitude_at_kill": player_command,
                "postdeath_state_rows": len(dead_states),
                "maximum_postdeath_displacement_units": (
                    maximum_postdeath_displacement
                ),
                "maximum_postdeath_speed_units_per_second": (
                    maximum_postdeath_speed
                ),
                "corpse_visible_seconds": (despawn_tick - kill_tick) / 64.0,
                "despawn_server_tick": despawn_tick,
                "despawn_state_enemy_is_null": bool(despawn_state)
                and despawn_state.get("enemy") is None,
                "despawn_switch_realized": despawn_switch is not None,
                "next_actor_id": (
                    next_switch.get("active_actor_id") if next_switch else None
                ),
                "next_actor_is_distinct": bool(next_switch)
                and next_switch.get("active_actor_id") != actor_id,
            }
        )

    observed_kill_ids = {row["actor_id"] for row in kill_records}
    killed_crossings = [
        row
        for row in qa["encounter_crossings"]
        if row["actor_id"] in EXPECTED_KILL_ACTOR_IDS
    ]
    survivor_crossings = [
        row
        for row in qa["encounter_crossings"]
        if row["actor_id"] not in EXPECTED_KILL_ACTOR_IDS
    ]
    checks = qa["checks"]
    checks.pop("enemy_not_killed", None)
    checks.pop("every_encounter_crosses_expanded_view", None)
    checks["exact_expected_moving_kills"] = (
        len(kill_records) == len(EXPECTED_KILL_ACTOR_IDS)
        and observed_kill_ids == EXPECTED_KILL_ACTOR_IDS
        and all(
            row["realized_kill_block"] == row["declared_kill_block"]
            for row in kill_records
        )
    )
    expected_kills = bool(EXPECTED_KILL_ACTOR_IDS)
    checks["enemy_moving_immediately_before_every_kill"] = (
        not expected_kills
        or bool(kill_records)
        and all(
            row["enemy_predeath_horizontal_speed"] >= 79.0
            for row in kill_records
        )
    )
    checks["player_moving_during_every_kill"] = (
        not expected_kills
        or bool(kill_records)
        and all(
            row["player_horizontal_speed_at_kill"] >= 20.0
            and row["player_command_magnitude_at_kill"] >= 20.0
            for row in kill_records
        )
    )
    checks["postdeath_motion_locked_for_every_kill"] = (
        not expected_kills
        or bool(kill_records)
        and all(
            row["postdeath_state_rows"] >= 64
            and row["maximum_postdeath_displacement_units"] <= 0.1
            and row["maximum_postdeath_speed_units_per_second"] <= 0.1
            for row in kill_records
        )
    )
    checks["corpse_despawn_realized_for_every_kill"] = (
        not expected_kills
        or bool(kill_records)
        and all(
            row["corpse_visible_seconds"] >= 1.5
            and row["despawn_state_enemy_is_null"]
            and row["despawn_switch_realized"]
            for row in kill_records
        )
    )
    checks["distinct_next_actor_after_every_kill"] = (
        not expected_kills
        or bool(kill_records)
        and all(row["next_actor_is_distinct"] for row in kill_records)
    )
    checks["killed_encounters_enter_and_reach_aim_region"] = (
        not expected_kills
        or bool(killed_crossings)
        and all(
            row["start_relative_yaw_degrees"]
            >= base.EXPANDED_VIEW_HALF_YAW_DEGREES
            and row["minimum_relative_yaw_degrees"]
            <= killed_aim_region_max_degrees
            for row in killed_crossings
        )
    )
    checks["surviving_encounters_cross_expanded_view"] = bool(survivor_crossings) and all(
        row["crosses_expanded_view"] for row in survivor_crossings
    )
    checks["lifecycle_prompt_has_kill_dead_and_despawn"] = (
        sum(
            row["visibility_phase"] == "killed"
            for row in scenario["prompt_schedule"]
        )
        == len(EXPECTED_KILL_ACTOR_IDS)
        and sum(
            row["visibility_phase"] == "despawn"
            for row in scenario["prompt_schedule"]
        )
        == len(EXPECTED_KILL_ACTOR_IDS)
        and (
            any(
                row["visibility_phase"] == "dead"
                for row in scenario["prompt_schedule"]
            )
            if expected_kills
            else not any(
                row["visibility_phase"] in {"killed", "dead", "despawn"}
                for row in scenario["prompt_schedule"]
            )
        )
    )
    qa["schema_version"] = (
        "xonotic-stage2-long60-multi-enemy-moving-kill-pilot-qa-v1"
    )
    qa["lifecycle"] = {
        "expected_kill_actor_ids": sorted(EXPECTED_KILL_ACTOR_IDS),
        "kill_records": kill_records,
        "killed_aim_region_max_degrees": killed_aim_region_max_degrees,
    }
    qa["passed"] = all(checks.values())
    return qa


original_write_review = base.write_review


def lifecycle_write_review(
    output_root: Path, results: list[dict[str, Any]]
) -> Path:
    page = original_write_review(output_root, results)
    document = page.read_text(encoding="utf-8")
    document = document.replace(
        "The player uses open-loop, human-like movement bursts with distributed "
        "short pauses, while the camera keeps scanning with occasional brief aim "
        "holds. MachineGun interactions remain verified.",
        "The player uses open-loop, human-like movement bursts while the camera "
        "keeps scanning. Two opponents must be killed while both sides are moving; "
        "each corpse is held motionless, then despawned before a distinct opponent "
        "appears.",
    )
    for result in results:
        qa = result["qa"]
        needle = (
            f"{qa['counts']['enemy_damage_events']} hits / "
            f"{qa['interaction']['total_enemy_damage']:.0f} damage"
        )
        replacement = (
            f"{qa['counts']['enemy_damage_events']} hits / "
            f"{qa['counts']['enemy_kill_events']} moving kills / "
            f"{qa['interaction']['total_enemy_damage']:.0f} damage"
        )
        document = document.replace(needle, replacement, 1)
    page.write_text(document, encoding="utf-8")
    return page


base.prompt_schedule = lifecycle_prompt_schedule
base.build_scenario = lifecycle_build_scenario
base.validate_episode = lifecycle_validate_episode
base.write_review = lifecycle_write_review


if __name__ == "__main__":
    raise SystemExit(base.main())
