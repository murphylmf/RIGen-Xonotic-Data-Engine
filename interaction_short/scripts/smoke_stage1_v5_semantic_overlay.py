                      
"""Run a non-training semantic overlay against one certified v5 path."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_manifests as v4              
import prepare_stage1_v5_manifests as v5              
import xonotic_capture as capture              


def prototype_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (
            v5.PRIMARY_PROTOTYPES_PATH,
            v5.REPLENISHMENT_PROTOTYPES_PATH,
            v5.TARGETED_HIGH_PROTOTYPES_PATH,
            v5.TARGETED_COLLISION_PROTOTYPES_PATH,
            v5.FAST_TRAVERSAL_PROTOTYPES_PATH,
        )
        if path.is_file()
    )


def load_prototype(prototype_id: str) -> dict[str, Any]:
    matches = [
        row
        for path in prototype_paths()
        for row in capture.load_jsonl(path)
        if row.get("episode_id") == prototype_id
    ]
    if len(matches) != 1:
        raise capture.CaptureFailure(
            "v5_overlay_prototype_not_singleton",
            f"id={prototype_id} matches={len(matches)}",
        )
    return matches[0]


def load_reference(prototype_id: str) -> dict[str, Any]:
    matches = [
        row
        for row in capture.load_jsonl(v5.PATH_CERTIFICATE_INDEX)
        if row.get("prototype_id") == prototype_id
        and row.get("status") == "certified"
    ]
    if len(matches) != 1:
        raise capture.CaptureFailure(
            "v5_overlay_certificate_not_singleton",
            f"id={prototype_id} matches={len(matches)}",
        )
    return matches[0]


def semantic_scenario(
    prototype: dict[str, Any],
    reference: dict[str, Any],
    weapon: str,
    mode: str,
    episode_id: str,
) -> dict[str, Any]:
    scenario = copy.deepcopy(prototype)
    scenario["source_prototype_id"] = prototype["episode_id"]
    scenario["episode_id"] = episode_id
                                                                            
                                                                         
    scenario["split"] = "pilot"
    scenario["anchor_id"] = (
        f"{scenario['map']}_{episode_id}_pair"
        if scenario["enemy_present"]
        else f"{scenario['map']}_{episode_id}_solo"
    )
    scenario["candidate_wave"] = "semantic_overlay_validation"
    scenario["formal_collection_authorized"] = False
    scenario["training_admitted"] = False
    scenario["weapon"] = weapon
    scenario["weapon_netname"] = capture.WEAPON_NETNAME[weapon]
    scenario["player"]["clip"] = 60.0
    scenario["action_design"]["weapon_action"] = mode
    arity = v5.physical_arity(scenario) + int(mode != "none")
    if arity > 3:
        raise capture.CaptureFailure(
            "v5_overlay_action_arity_exceeded",
            f"prototype={prototype['episode_id']} arity={arity}",
        )
    scenario["action_design"]["action_arity"] = {
        0: "idle",
        1: "atomic",
        2: "pairwise",
        3: "three_way",
    }[arity]
    scenario["acceptance"] = {
        "actual_outcome": None,
        "fire_required": mode == "environmental_primary",
        "reload_success": mode == "reload",
    }
    if mode == "reload":
        if weapon not in v4.RELOAD_WEAPONS:
            raise capture.CaptureFailure(
                "v5_overlay_reload_weapon_unsupported", weapon
            )
        scenario["player"]["clip"] = v4.RELOAD_INITIAL_CLIP[weapon]
        scenario["acceptance"].update(
            {
                "reload_weapon": capture.WEAPON_NETNAME[weapon],
                "reload_initial_clip": v4.RELOAD_INITIAL_CLIP[weapon],
                "reload_clip_capacity": v4.RELOAD_CAPACITY[weapon],
                "reload_start_server_tick": (
                    capture.WARMUP_TICKS
                    + capture.STAGE1_RELOAD_START_OUTPUT_TICK
                ),
                "reload_duration_ticks": (
                    capture.STAGE1_RELOAD_DURATION_TICKS
                ),
            }
        )
    scenario["player_path_certificate"] = copy.deepcopy(reference)
    certificate = capture.load_player_path_certificate(scenario)
    if certificate is None:
        raise AssertionError(prototype["episode_id"])
    scenario["frozen_actions_path"] = certificate["actions_path"]
    scenario["frozen_actions_sha256"] = certificate["actions_sha256"]
    return scenario


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--prototype-id", required=True)
    result.add_argument(
        "--weapon",
        choices=tuple(capture.WEAPON_NETNAME),
        required=True,
    )
    result.add_argument(
        "--mode",
        choices=("none", "environmental_primary", "reload"),
        required=True,
    )
    result.add_argument("--episode-id")
    result.add_argument("--port", type=int, default=34_200)
    result.add_argument(
        "--live-only",
        action="store_true",
        help="Skip offline render, x264/FLAC, and package QA.",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    episode_id = args.episode_id or re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        (
            f"v5overlay_{args.prototype_id}_"
            f"{args.weapon}_{args.mode}"
        ),
    )
    prototype = load_prototype(args.prototype_id)
    reference = load_reference(args.prototype_id)
    scenario = semantic_scenario(
        prototype,
        reference,
        args.weapon,
        args.mode,
        episode_id,
    )
    if not args.live_only:
        result = capture.execute_attempt(
            scenario,
            retry=0,
            publish=False,
            port=args.port,
        )
        qa = result["qa"]
        summary = {
            "schema_version": (
                "xonotic-stage1-v5-semantic-overlay-smoke-v1"
            ),
            "episode_id": episode_id,
            "prototype_id": args.prototype_id,
            "weapon": args.weapon,
            "mode": args.mode,
            "full_pipeline": True,
            "passed": True,
            "stage": result["stage"],
            "frames": qa["video"]["frames"],
            "audio_samples_per_channel": qa["audio"][
                "samples_per_channel"
            ],
            "frame_tick_mapping": qa["mapping"],
            "renderer": qa["runtime"]["renderer"],
            "hud": qa["hud"],
            "requested_gametype": qa["mode"]["requested_gametype"],
            "realized_gametype": qa["mode"]["realized_gametype"],
            "player_path_certificate": qa[
                "player_path_certificate"
            ],
            "fire_count": qa["events"]["fire_count"],
            "reload": qa["events"].get("reload"),
        }
    else:
        attempt_id = f"{episode_id}_a01"
        stage = capture.TMP_ROOT / "raw" / attempt_id
        if stage.exists():
            capture.clean_stage(stage)
        stage.mkdir(parents=True)
        live = capture.run_live_attempt(
            stage,
            scenario,
            capture.build_root(),
            retry=0,
            port=args.port,
        )
        precheck = capture.validate_live_precheck(
            stage, scenario, live
        )
        states, events, _ = capture.parse_server_telemetry(
            Path(live["server_telemetry"])
        )
        path_metrics = capture.player_path_certificate_metrics(
            states, scenario
        )
        summary = {
            "schema_version": (
                "xonotic-stage1-v5-semantic-overlay-smoke-v1"
            ),
            "episode_id": episode_id,
            "prototype_id": args.prototype_id,
            "weapon": args.weapon,
            "mode": args.mode,
            "full_pipeline": False,
            "passed": bool(
                precheck["passed"] and path_metrics["passed"]
            ),
            "stage": str(stage),
            "player_path_certificate": path_metrics,
            "event_counts": (
                events["event"].value_counts().to_dict()
                if "event" in events
                else {}
            ),
        }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
