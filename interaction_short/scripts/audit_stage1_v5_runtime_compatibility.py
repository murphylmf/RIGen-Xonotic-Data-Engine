                      
"""Audit an exact Stage-1 v5 certificate/runtime commit pair.

The original player-path certificates remain immutable.  This audit selects a
deterministic, stratified subset, replays the exact certified physical action
CSV on the final runtime build, and requires tick-for-tick authoritative state
identity.  Visible-wall-contact cases additionally run the NVIDIA offline
renderer.  The resulting audit authorizes only the exact certificate index,
certificate source commit, runtime source commit, runtime config, and engine
diff recorded in the report.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import math
import os
import queue
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import certify_stage1_v5_paths as certification              
import prepare_stage1_v5_manifests as v5              
import xonotic_capture as capture              


ROOT = capture.ROOT
CERTIFICATE_SOURCE_COMMIT = v5.EXPECTED_SOURCE_COMMIT
RUNTIME_SOURCE_COMMIT = "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "stage1_path_certification_v5/compatibility"
    / (
        f"{CERTIFICATE_SOURCE_COMMIT[:12]}_to_"
        f"{RUNTIME_SOURCE_COMMIT[:12]}"
    )
)
ENGINE_REPOSITORY = (
    ROOT / "source/release-src-0.8.6/Xonotic"
)
EXPECTED_ENGINE_DIFF_PATHS = (
    "source/darkplaces/capture_telemetry.c",
    "source/darkplaces/capture_telemetry.h",
    "source/darkplaces/cl_demo.c",
    "source/darkplaces/cl_parse.c",
    "source/darkplaces/host.c",
)
MINIMUM_FORMAL_SAMPLE_ROWS = 128
VISIBLE_COLLISION_SAMPLE_ROWS = 8
STATE_FLOAT_DECIMALS = 6


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(
            value, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_once_or_verify(path: Path, text: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "compatibility_immutable_artifact_conflict", str(path)
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    try:
        os.rename(temporary, path)
    except FileExistsError:
        temporary.unlink(missing_ok=True)
        if path.read_text(encoding="utf-8") != text:
            raise capture.CaptureFailure(
                "compatibility_immutable_artifact_conflict", str(path)
            )


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def certified_inputs() -> list[dict[str, Any]]:
    prototypes = v5.load_prototype_catalog()
    result: list[dict[str, Any]] = []
    for reference in capture.load_jsonl(v5.PATH_CERTIFICATE_INDEX):
        if reference.get("status") != "certified":
            continue
        prototype_id = str(reference["prototype_id"])
        prototype = prototypes.get(prototype_id)
        if prototype is None:
            raise capture.CaptureFailure(
                "compatibility_prototype_missing", prototype_id
            )
        certificate_path = capture.locked_root_artifact(
            reference["certificate_path"],
            reference["certificate_sha256"],
            "compatibility_certificate",
        )
        certificate = json.loads(
            certificate_path.read_text(encoding="utf-8")
        )
        checks = {
            "reference_source": reference.get("source_commit")
            == CERTIFICATE_SOURCE_COMMIT,
            "certificate_source": certificate.get("source_commit")
            == CERTIFICATE_SOURCE_COMMIT,
            "certificate_passed": certificate.get("passed") is True,
            "prototype_id": certificate.get("prototype_id")
            == prototype_id,
            "actions_hash": reference.get("actions_sha256")
            == certificate.get("actions_sha256"),
            "states_hash": reference.get("states_sha256")
            == certificate.get("states_sha256"),
            "path_contract": reference.get("path_contract_sha256")
            == certificate.get("path_contract_sha256"),
        }
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "compatibility_certificate_contract_failed",
                capture.canonical_json(
                    {"prototype_id": prototype_id, "checks": checks}
                ),
            )
        result.append(
            {
                "prototype": prototype,
                "reference": reference,
                "certificate": certificate,
            }
        )
    return result


def categorical_value(
    item: dict[str, Any], axis: str
) -> str:
    row = item["prototype"]
    reference = item["reference"]
    if axis == "candidate_wave":
        return str(reference["candidate_wave"])
    if axis == "generation_mode":
        return str(row["player_path_generation"]["mode"])
    if axis in {"net", "yaw", "pitch"}:
        metric = {
            "net": "net_displacement_bin",
            "yaw": "yaw_range_bin",
            "pitch": "pitch_range_bin",
        }[axis]
        return str(reference["motion"][metric])
    if axis == "collision_intent":
        return str(
            (row.get("collision_design") or {}).get("intent")
            or "ordinary"
        )
    if axis in {
        "locomotion_direction",
        "view_direction",
        "movement_profile",
        "view_profile",
    }:
        return str(row["action_design"][axis])
    return str(row[axis])


def select_sample(
    inputs: list[dict[str, Any]], count: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if count > len(inputs):
        raise capture.CaptureFailure(
            "compatibility_sample_pool_too_small",
            f"have={len(inputs)} need={count}",
        )
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError as exc:
        raise capture.CaptureFailure(
            "compatibility_milp_dependency_missing", str(exc)
        ) from exc

    vectors: list[np.ndarray] = []
    lower: list[float] = []
    upper: list[float] = []
    names: list[str] = []

    def constrain(
        name: str,
        predicate: Any,
        minimum: int,
        maximum: int,
    ) -> None:
        vector = np.fromiter(
            (1.0 if predicate(row) else 0.0 for row in inputs),
            dtype=np.float64,
            count=len(inputs),
        )
        capacity = int(vector.sum())
        if minimum > capacity:
            raise capture.CaptureFailure(
                "compatibility_sample_stratum_capacity",
                capture.canonical_json(
                    {
                        "name": name,
                        "minimum": minimum,
                        "capacity": capacity,
                    }
                ),
            )
        vectors.append(vector)
        lower.append(float(minimum))
        upper.append(float(min(maximum, capacity)))
        names.append(name)

    constrain("total", lambda _: True, count, count)
    axis_minimums = {
        "map": 1,
        "gametype": 4,
        "candidate_wave": 1,
        "generation_mode": 4,
        "dataset_role": 12,
        "primary_bucket": 6,
        "locomotion_direction": 3,
        "view_direction": 3,
        "net": 3,
        "yaw": 3,
        "pitch": 3,
    }
    for axis, minimum in axis_minimums.items():
        values = sorted(
            {categorical_value(item, axis) for item in inputs}
        )
        for value in values:
            axis_minimum = minimum
            if axis == "dataset_role":
                axis_minimum = (
                    24
                    if value == "foundation_enemy_distractor"
                    else 48
                )
            constrain(
                f"{axis}:{value}",
                lambda item, axis=axis, value=value: (
                    categorical_value(item, axis) == value
                ),
                axis_minimum,
                count,
            )
    constrain(
        "visible_collision",
        lambda item: categorical_value(
            item, "collision_intent"
        )
        == capture.VISIBLE_COLLISION_INTENT,
        min(VISIBLE_COLLISION_SAMPLE_ROWS, count),
        min(VISIBLE_COLLISION_SAMPLE_ROWS, count),
    )

    objective = np.asarray(
        [
            int(
                hashlib.sha256(
                    (
                        "stage1-v5-runtime-compatibility:"
                        + str(item["reference"]["prototype_id"])
                    ).encode()
                ).hexdigest()[:15],
                16,
            )
            / float(16**15)
            for item in inputs
        ],
        dtype=np.float64,
    )
    solved = milp(
        objective,
        integrality=np.ones(len(inputs), dtype=np.int8),
        bounds=Bounds(
            np.zeros(len(inputs)), np.ones(len(inputs))
        ),
        constraints=LinearConstraint(
            np.vstack(vectors),
            np.asarray(lower),
            np.asarray(upper),
        ),
        options={"time_limit": 120.0, "mip_rel_gap": 0.0},
    )
    if not solved.success or solved.x is None:
        raise capture.CaptureFailure(
            "compatibility_sample_milp_failed",
            capture.canonical_json(
                {
                    "status": int(solved.status),
                    "message": str(solved.message),
                    "constraints": [
                        {
                            "name": name,
                            "lower": low,
                            "upper": high,
                            "capacity": int(vector.sum()),
                        }
                        for name, low, high, vector in zip(
                            names, lower, upper, vectors
                        )
                    ],
                }
            ),
        )
    selected = [
        item
        for item, value in zip(inputs, solved.x)
        if float(value) >= 0.5
    ]
    selected.sort(
        key=lambda item: str(item["reference"]["prototype_id"])
    )
    if len(selected) != count:
        raise AssertionError((len(selected), count))
    coverage = {
        axis: dict(
            sorted(
                Counter(
                    categorical_value(item, axis)
                    for item in selected
                ).items()
            )
        )
        for axis in (
            *axis_minimums,
            "collision_intent",
            "movement_profile",
            "view_profile",
        )
    }
    return selected, {
        "solver_status": int(solved.status),
        "solver_message": str(solved.message),
        "solver_objective": float(solved.fun),
        "constraints": [
            {
                "name": name,
                "lower": int(low),
                "upper": int(high),
                "selected": int(
                    round(float(vector @ solved.x))
                ),
                "capacity": int(vector.sum()),
            }
            for name, low, high, vector in zip(
                names, lower, upper, vectors
            )
        ],
        "coverage": coverage,
    }


def sample_row(
    item: dict[str, Any], ordinal: int
) -> dict[str, Any]:
    row = item["prototype"]
    reference = item["reference"]
    return {
        "schema_version": (
            "xonotic-stage1-v5-runtime-compatibility-sample-v1"
        ),
        "sample_ordinal": ordinal,
        "prototype_id": reference["prototype_id"],
        "certificate_source_commit": CERTIFICATE_SOURCE_COMMIT,
        "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
        "certificate_path": reference["certificate_path"],
        "certificate_sha256": reference["certificate_sha256"],
        "actions_path": reference["actions_path"],
        "actions_sha256": reference["actions_sha256"],
        "physical_action_sha256": reference[
            "physical_action_sha256"
        ],
        "states_path": reference["states_path"],
        "states_sha256": reference["states_sha256"],
        "path_contract_sha256": reference[
            "path_contract_sha256"
        ],
        "strata": {
            "map": row["map"],
            "gametype": row["gametype"],
            "candidate_wave": reference["candidate_wave"],
            "dataset_role": row["dataset_role"],
            "primary_bucket": row["primary_bucket"],
            "generation_mode": row[
                "player_path_generation"
            ]["mode"],
            "locomotion_direction": row["action_design"][
                "locomotion_direction"
            ],
            "view_direction": row["action_design"][
                "view_direction"
            ],
            "net": reference["motion"][
                "net_displacement_bin"
            ],
            "yaw": reference["motion"]["yaw_range_bin"],
            "pitch": reference["motion"]["pitch_range_bin"],
            "collision_intent": (
                (row.get("collision_design") or {}).get("intent")
                or "ordinary"
            ),
        },
        "formal_collection_authorized": False,
        "training_admitted": False,
    }


def normalized(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [normalized(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {
            str(key): normalized(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [normalized(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        converted = float(value)
        if math.isnan(converted):
            return None
        if math.isinf(converted):
            return str(converted)
        return round(converted, STATE_FLOAT_DECIMALS)
    return value


def state_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    initial_time = float(frame.iloc[0]["server_time"])
    result: list[dict[str, Any]] = []
    for raw in frame.to_dict(orient="records"):
        row = {
            key: normalized(value)
            for key, value in raw.items()
            if key != "server_time"
        }
        row["server_time_from_first"] = normalized(
            float(raw["server_time"]) - initial_time
        )
        result.append(row)
    return result


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        capture.canonical_json(value).encode()
    ).hexdigest()


def prepare_replay_scenario(
    prototype: dict[str, Any], reference: dict[str, Any]
) -> dict[str, Any]:
    scenario = copy.deepcopy(prototype)
                                                                         
                                                              
    scenario["frozen_actions_path"] = reference["actions_path"]
    scenario["frozen_actions_sha256"] = reference[
        "actions_sha256"
    ]
    scenario.pop("route_view_policy", None)
    scenario.pop("route_plan", None)
    scenario["stage1_safe_base_route"] = False
    scenario["player_path_certification_run"] = True
    scenario["runtime_compatibility_audit_run"] = True
    scenario["formal_collection_authorized"] = False
    scenario["training_admitted"] = False
    return scenario


def compare_case(
    item: dict[str, Any],
    output_root: Path,
    port: int,
) -> dict[str, Any]:
    prototype = item["prototype"]
    reference = item["reference"]
    certificate = item["certificate"]
    prototype_id = str(reference["prototype_id"])
    case_root = output_root / "cases" / prototype_id
    result_path = case_root / "RESULT.json"
    if result_path.is_file():
        existing = json.loads(
            result_path.read_text(encoding="utf-8")
        )
        if (
            existing.get("passed") is True
            and existing.get("certificate_source_commit")
            == CERTIFICATE_SOURCE_COMMIT
            and existing.get("runtime_source_commit")
            == RUNTIME_SOURCE_COMMIT
        ):
            return existing

    stage = capture.TMP_ROOT / "raw" / f"compat_{prototype_id}"
    if stage.exists():
        capture.clean_stage(stage)
    stage.mkdir(parents=True)
    scenario = prepare_replay_scenario(prototype, reference)
    started = time.monotonic()
    try:
        with capture.live_slot(), capture.sdl_slot():
            live = capture.run_live_attempt(
                stage,
                scenario,
                capture.build_root(),
                retry=0,
                port=port,
            )
        precheck = capture.validate_live_precheck(
            stage,
            scenario,
            live,
            allow_new_player_path_certificate=True,
        )
        states, events, _ = capture.parse_server_telemetry(
            Path(live["server_telemetry"])
        )
        reference_states = pd.read_parquet(
            capture.locked_root_artifact(
                reference["states_path"],
                reference["states_sha256"],
                "compatibility_reference_states",
            )
        )
        old_records = state_records(reference_states)
        new_records = state_records(states)
        old_state_sha = canonical_sha(old_records)
        new_state_sha = canonical_sha(new_records)
        actions_requested_sha = capture.sha256_file(
            stage / "actions_requested.csv"
        )
        new_motion = v5.live_motion_metrics(states)

        render_evidence: dict[str, Any] | None = None
        if (
            (prototype.get("collision_design") or {}).get(
                "intent"
            )
            == capture.VISIBLE_COLLISION_INTENT
        ):
            (
                new_blockage,
                render_evidence,
                _,
                render_frames,
            ) = certification.certify_visible_collision_render(
                stage, scenario, live, states
            )
            presentation = (
                capture.fixed_demo_presentation_phase_metrics(
                    render_frames
                )
            )
            render_evidence = {
                **render_evidence,
                "presentation_phase": presentation,
            }
        else:
            new_blockage = capture.movement_blockage_metrics(
                states, scenario=scenario
            )

        old_blockage = certificate["movement_blockage"]
        visible = render_evidence is not None
        blockage_checks = {
            "collision_policy": new_blockage.get(
                "collision_policy_passed"
            )
            is True,
            "contact_telemetry": new_blockage.get(
                "contact_telemetry_present"
            )
            is True,
            "blocked_ticks": int(
                new_blockage.get("blocked_ticks", -1)
            )
            == int(old_blockage.get("blocked_ticks", -2)),
            "commanded_ticks": int(
                new_blockage.get("commanded_ticks", -1)
            )
            == int(old_blockage.get("commanded_ticks", -2)),
            "visible_collision": (
                not visible
                or (
                    new_blockage.get(
                        "visible_collision_qualified"
                    )
                    is True
                    and render_evidence.get("passed") is True
                    and render_evidence["presentation_phase"][
                        "passed"
                    ]
                    is True
                )
            ),
        }
        checks = {
            "live_precheck": precheck["passed"] is True,
            "actions_byte_identical": actions_requested_sha
            == reference["actions_sha256"],
            "authoritative_state_rows": len(states)
            == capture.TOTAL_TICKS,
            "authoritative_states_tick_exact": old_state_sha
            == new_state_sha,
            "motion_metrics_exact": normalized(new_motion)
            == normalized(certificate["motion"]),
            "no_damage": certification.event_damage_count(events)
            == int(certificate["damage_count"])
            == 0,
            "blockage_contract": all(blockage_checks.values()),
            "runtime_source_commit": (
                capture.build_root() / "SOURCE_COMMIT"
            ).read_text(encoding="utf-8").strip()
            == RUNTIME_SOURCE_COMMIT,
        }
        result = {
            "schema_version": (
                "xonotic-stage1-v5-runtime-compatibility-case-v1"
            ),
            "prototype_id": prototype_id,
            "certificate_source_commit": (
                CERTIFICATE_SOURCE_COMMIT
            ),
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
            "passed": all(checks.values()),
            "checks": checks,
            "blockage_checks": blockage_checks,
            "reference_state_canonical_sha256": old_state_sha,
            "runtime_state_canonical_sha256": new_state_sha,
            "reference_states_sha256": reference[
                "states_sha256"
            ],
            "reference_actions_sha256": reference[
                "actions_sha256"
            ],
            "runtime_actions_sha256": actions_requested_sha,
            "motion": normalized(new_motion),
            "movement_blockage": normalized(new_blockage),
            "render_evidence": normalized(render_evidence),
            "live_wall_seconds": float(live["live_wall_seconds"]),
            "audit_wall_seconds": time.monotonic() - started,
            "formal_collection_authorized": False,
            "training_admitted": False,
            "created_utc": capture.utc_now(),
        }
        if not result["passed"]:
            raise capture.CaptureFailure(
                "compatibility_case_mismatch",
                capture.canonical_json(
                    {
                        "prototype_id": prototype_id,
                        "checks": checks,
                        "blockage_checks": blockage_checks,
                    }
                ),
            )
        atomic_json(result_path, result)
        capture.clean_stage(stage)
        return result
    except Exception as exc:
        case_root.mkdir(parents=True, exist_ok=True)
        evidence_root = case_root / "failure_artifacts"
        if evidence_root.exists():
            shutil.rmtree(evidence_root)
        if stage.is_dir():
            shutil.copytree(stage, evidence_root)
        failed = {
            "schema_version": (
                "xonotic-stage1-v5-runtime-compatibility-case-v1"
            ),
            "prototype_id": prototype_id,
            "certificate_source_commit": (
                CERTIFICATE_SOURCE_COMMIT
            ),
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
            "passed": False,
            "reason": (
                exc.reason
                if isinstance(exc, capture.CaptureFailure)
                else type(exc).__name__
            ),
            "detail": str(exc),
            "failure_artifacts": (
                relative(evidence_root)
                if evidence_root.is_dir()
                else None
            ),
            "audit_wall_seconds": time.monotonic() - started,
            "formal_collection_authorized": False,
            "training_admitted": False,
            "created_utc": capture.utc_now(),
        }
        atomic_json(result_path, failed)
        if stage.is_dir():
            capture.clean_stage(stage)
        return failed


def engine_diff_evidence() -> dict[str, Any]:
    command = [
        "git",
        "-c",
        f"safe.directory={ENGINE_REPOSITORY}",
        "-C",
        str(ENGINE_REPOSITORY),
        "diff",
        "--binary",
        f"{CERTIFICATE_SOURCE_COMMIT}..{RUNTIME_SOURCE_COMMIT}",
    ]
    patch = subprocess.check_output(command)
    names = subprocess.check_output(
        [
            *command[:-2],
            "--name-only",
            command[-1],
        ],
        text=True,
    ).splitlines()
    return {
        "repository": relative(ENGINE_REPOSITORY),
        "certificate_source_commit": CERTIFICATE_SOURCE_COMMIT,
        "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
        "changed_paths": names,
        "expected_changed_paths": list(EXPECTED_ENGINE_DIFF_PATHS),
        "changed_paths_exact": names
        == list(EXPECTED_ENGINE_DIFF_PATHS),
        "binary_patch_sha256": hashlib.sha256(patch).hexdigest(),
        "reviewed_scope": (
            "offline demo/fixed-step capture and capture telemetry only; "
            "no SV_Physics, collision, map, gamecode, or live action "
            "scheduler change"
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    capture.require_conda()
    build_commit = (
        capture.build_root() / "SOURCE_COMMIT"
    ).read_text(encoding="utf-8").strip()
    if build_commit != RUNTIME_SOURCE_COMMIT:
        raise capture.CaptureFailure(
            "compatibility_runtime_build_mismatch",
            f"expected={RUNTIME_SOURCE_COMMIT} actual={build_commit}",
        )
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    inputs = certified_inputs()
    selected, selection_audit = select_sample(inputs, args.count)
    sample = [
        sample_row(item, ordinal)
        for ordinal, item in enumerate(selected, 1)
    ]
    sample_text = "".join(
        capture.canonical_json(row) + "\n" for row in sample
    )
    sample_path = output_root / "sample_manifest.jsonl"
    write_once_or_verify(sample_path, sample_text)
    selection_path = output_root / "SELECTION_AUDIT.json"
    selection_record = {
        "schema_version": (
            "xonotic-stage1-v5-runtime-compatibility-selection-v1"
        ),
        "certificate_source_commit": CERTIFICATE_SOURCE_COMMIT,
        "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
        "certificate_index_path": relative(
            v5.PATH_CERTIFICATE_INDEX
        ),
        "certificate_index_sha256": capture.sha256_file(
            v5.PATH_CERTIFICATE_INDEX
        ),
        "certified_pool_rows": len(inputs),
        "sample_rows": len(sample),
        "sample_manifest_path": relative(sample_path),
        "sample_manifest_sha256": hashlib.sha256(
            sample_text.encode()
        ).hexdigest(),
        "selection": selection_audit,
        "formal_collection_authorized": False,
        "training_admitted": False,
    }
    atomic_json(selection_path, selection_record)

    ports: queue.Queue[int] = queue.Queue()
    for offset in range(args.workers):
        ports.put(args.port_base + offset)

    def one(item: dict[str, Any]) -> dict[str, Any]:
        port = ports.get()
        try:
            result = compare_case(item, output_root, port)
            print(
                capture.canonical_json(
                    {
                        "prototype_id": result["prototype_id"],
                        "passed": result["passed"],
                        "port": port,
                    }
                ),
                flush=True,
            )
            return result
        finally:
            ports.put(port)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        results = list(executor.map(one, selected))
    results.sort(key=lambda row: str(row["prototype_id"]))
    result_index_text = "".join(
        capture.canonical_json(row) + "\n" for row in results
    )
    result_index = output_root / "case_results.jsonl"
                                                            
    temporary = result_index.with_name(
        f".{result_index.name}.tmp.{os.getpid()}"
    )
    temporary.write_text(result_index_text, encoding="utf-8")
    os.replace(temporary, result_index)

    diff = engine_diff_evidence()
    required_coverage = {
        "all_maps": len(
            selection_audit["coverage"]["map"]
        )
        == len(
            {
                categorical_value(item, "map")
                for item in inputs
            }
        ),
        "all_gametypes": len(
            selection_audit["coverage"]["gametype"]
        )
        == len(
            {
                categorical_value(item, "gametype")
                for item in inputs
            }
        ),
        "all_generation_modes": len(
            selection_audit["coverage"]["generation_mode"]
        )
        == len(
            {
                categorical_value(item, "generation_mode")
                for item in inputs
            }
        ),
        "all_candidate_waves": len(
            selection_audit["coverage"]["candidate_wave"]
        )
        == len(
            {
                categorical_value(item, "candidate_wave")
                for item in inputs
            }
        ),
        "visible_collision_rendered": sum(
            result.get("render_evidence") is not None
            for result in results
        )
        == min(VISIBLE_COLLISION_SAMPLE_ROWS, args.count),
    }
    checks = {
        "minimum_sample_rows": len(results)
        >= MINIMUM_FORMAL_SAMPLE_ROWS,
        "all_cases_passed": all(
            result["passed"] for result in results
        ),
        "required_coverage": all(required_coverage.values()),
        "engine_diff_paths_exact": diff["changed_paths_exact"],
        "runtime_config_locked": (
            ROOT / "configs/capture_server.cfg"
        ).is_file(),
        "final_build_lock_present": (
            ROOT
            / (
                "locks/capture-"
                f"{RUNTIME_SOURCE_COMMIT[:12]}-x86_64.sha256"
            )
        ).is_file(),
    }
    existing_audit = output_root / "AUDIT.json"
    created_utc = (
        json.loads(
            existing_audit.read_text(encoding="utf-8")
        )["created_utc"]
        if existing_audit.is_file()
        else capture.utc_now()
    )
    audit = {
        "schema_version": (
            "xonotic-stage1-v5-player-path-runtime-compatibility-v1"
        ),
        "created_utc": created_utc,
        "passed": all(checks.values()),
        "checks": checks,
        "required_coverage": required_coverage,
        "authorization_scope": {
            "kind": "exact_commit_pair_and_certificate_index",
            "certificate_source_commit": (
                CERTIFICATE_SOURCE_COMMIT
            ),
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
            "certificate_index_path": relative(
                v5.PATH_CERTIFICATE_INDEX
            ),
            "certificate_index_sha256": capture.sha256_file(
                v5.PATH_CERTIFICATE_INDEX
            ),
            "generic_descendant_commits_allowed": False,
            "runtime_fallback_allowed": False,
            "certificates_mutated": False,
        },
        "sample": {
            "rows": len(sample),
            "manifest_path": relative(sample_path),
            "manifest_sha256": capture.sha256_file(sample_path),
            "selection_audit_path": relative(selection_path),
            "selection_audit_sha256": capture.sha256_file(
                selection_path
            ),
            "case_results_path": relative(result_index),
            "case_results_sha256": capture.sha256_file(
                result_index
            ),
            "status": dict(
                Counter(
                    "passed" if row["passed"] else "failed"
                    for row in results
                )
            ),
            "coverage": selection_audit["coverage"],
        },
        "engine_diff": diff,
        "runtime_artifacts": {
            "build": relative(capture.build_root()),
            "build_source_commit": build_commit,
            "build_lock_path": (
                "locks/capture-"
                f"{RUNTIME_SOURCE_COMMIT[:12]}-x86_64.sha256"
            ),
            "build_lock_sha256": capture.sha256_file(
                ROOT
                / (
                    "locks/capture-"
                    f"{RUNTIME_SOURCE_COMMIT[:12]}-x86_64.sha256"
                )
            ),
            "capture_server_config_path": (
                "configs/capture_server.cfg"
            ),
            "capture_server_config_sha256": capture.sha256_file(
                ROOT / "configs/capture_server.cfg"
            ),
        },
        "formal_collection_authorized": False,
        "training_admitted": False,
    }
    atomic_json(existing_audit, audit)
    if not audit["passed"]:
        raise capture.CaptureFailure(
            "compatibility_audit_failed",
            capture.canonical_json(checks),
        )
    return audit


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--count", type=int, default=128)
    result.add_argument("--workers", type=int, default=8)
    result.add_argument("--port-base", type=int, default=39_200)
    result.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    return result


def main() -> int:
    args = parser().parse_args()
    if args.count < VISIBLE_COLLISION_SAMPLE_ROWS:
        raise SystemExit(
            f"--count must be at least {VISIBLE_COLLISION_SAMPLE_ROWS}"
        )
    if not 1 <= args.workers <= 16:
        raise SystemExit("--workers must be in 1..16")
    try:
        audit = run(args)
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
