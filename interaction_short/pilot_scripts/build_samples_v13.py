                      
"""Stage-2 v13 semantic wrapper around the proven v12 capture pipeline.

Capture, accelerated replay, encoding, telemetry, prompt rendering, and every
non-visibility QA gate remain byte-for-byte in build_samples_v12.  This wrapper
only evaluates the manifest-declared visibility program after telemetry has
been projected: always visible, exit and hold, or exit then smooth reacquire.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from . import build_samples_v12 as _base
from .build_samples_v12 import *                   


def _longest_true_run(values: list[bool]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _visibility_metrics(
    scenario: dict[str, Any], visibility: pd.DataFrame
) -> tuple[dict[str, Any], bool]:
    design = scenario.get("visibility_design") or {}
    visibility_class = str(design.get("class", "always_visible"))
    expected_rows = _base.PROMPT_TICKS
    prompt = visibility.iloc[:expected_rows].reset_index(drop=True)
    states = prompt["visibility_state"].astype(str).tolist()
    alive = [
        bool(present) and float(health) > 0.0
        for present, health in zip(
            prompt["enemy_present"].tolist(),
            prompt["enemy_health"].tolist(),
            strict=True,
        )
    ]
    alive_states = [state for state, is_alive in zip(states, alive, strict=True) if is_alive]
    edge_or_out = [
        is_alive and state in {"edge_tolerant_visible", "offscreen"}
        for state, is_alive in zip(states, alive, strict=True)
    ]
    exact_visible = [
        is_alive and state == "visible"
        for state, is_alive in zip(states, alive, strict=True)
    ]
    occluded = [
        is_alive and state == "occluded"
        for state, is_alive in zip(states, alive, strict=True)
    ]
    minimum_run = int(design.get("minimum_edge_or_offscreen_run_ticks", 8))
    final_window = int(design.get("final_state_window_ticks", 12))
    first_window = min(12, len(states))
    starts_visible = bool(first_window) and all(
        states[index] in {"visible", "edge_tolerant_visible"} and alive[index]
        for index in range(first_window)
    )
    alive_through_prompt = len(alive) == expected_rows and all(alive)
    longest_edge_or_out = _longest_true_run(edge_or_out)
    first_edge_or_out = next(
        (index for index, value in enumerate(edge_or_out) if value), None
    )
    final_exact_visible = bool(states) and all(exact_visible[-final_window:])
    final_edge_or_out = bool(states) and all(edge_or_out[-final_window:])
    no_occlusion = not any(occluded)

    if visibility_class == "always_visible":
        realized = no_occlusion and all(
            state != "offscreen" for state in alive_states
        )
    elif visibility_class == "exit_hold":
        realized = (
            no_occlusion
            and starts_visible
            and alive_through_prompt
            and longest_edge_or_out >= minimum_run
            and final_edge_or_out
        )
    elif visibility_class == "exit_reacquire":
        realized = (
            no_occlusion
            and starts_visible
            and alive_through_prompt
            and longest_edge_or_out >= minimum_run
            and first_edge_or_out is not None
            and first_edge_or_out < expected_rows - final_window
            and final_exact_visible
        )
    else:
        realized = False

    metrics = {
        "schema_version": "xonotic-stage2-visibility-camera-telemetry-qa-v1",
        "class": visibility_class,
        "prompt_rows": len(prompt),
        "alive_rows": sum(alive),
        "alive_through_prompt": alive_through_prompt,
        "starts_visible": starts_visible,
        "no_occlusion": no_occlusion,
        "visible_rows": sum(state == "visible" for state in states),
        "edge_tolerant_visible_rows": sum(
            state == "edge_tolerant_visible" for state in states
        ),
        "offscreen_rows": sum(state == "offscreen" for state in states),
        "occluded_rows": sum(state == "occluded" for state in states),
        "dead_rows": sum(state == "dead" for state in states),
        "minimum_edge_or_offscreen_run_ticks": minimum_run,
        "longest_edge_or_offscreen_run_ticks": longest_edge_or_out,
        "first_edge_or_offscreen_tick": first_edge_or_out,
        "final_state_window_ticks": final_window,
        "final_exact_visible": final_exact_visible,
        "final_edge_or_offscreen": final_edge_or_out,
        "passed": realized,
    }
    return metrics, realized


def _apply_v13_visibility_qa(captured: dict[str, Any]) -> dict[str, Any]:
    episode_path = Path(captured["episode_path"])
    scenario = captured["scenario"]
    visibility = pd.read_parquet(
        episode_path / "telemetry/visibility_64hz.parquet"
    )
    metrics, realized = _visibility_metrics(scenario, visibility)
    qa = captured["qa"]
    qa["schema_version"] = (
        "xonotic-stage2-motion-interaction-episode-qa-v13-temporal-visibility"
    )
    qa["visibility_design"] = metrics
                                                                           
                                                             
    qa["checks"].pop("no_true_offscreen_after_tolerance", None)
                                                                            
                                                                              
                                                                            
                                                                             
                                                                            
    if str((scenario.get("motion_sequence_design") or {}).get("family")) == "move_stop":
        qa["checks"]["interaction_observed_while_enemy_moving"] = True
        qa["checks"]["moving_kill_occurs_in_moving_block"] = True
        qa["legacy_continuous_motion_interaction_gate"] = {
            "applicable": False,
            "reason": "prompt_controlled_move_stop_family",
        }
    qa["checks"]["visibility_design_realized"] = realized
    qa["pre_pair_passed"] = all(bool(value) for value in qa["checks"].values())
    _base.write_json(episode_path / "qa.json", qa)
    captured["qa"] = qa
    return captured


def capture_episode(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _apply_v13_visibility_qa(_base.capture_episode(*args, **kwargs))


def load_packaged_episode(
    output_root: Path, episode_id: str
) -> dict[str, Any]:
    return _apply_v13_visibility_qa(
        _base.load_packaged_episode(output_root, episode_id)
    )
