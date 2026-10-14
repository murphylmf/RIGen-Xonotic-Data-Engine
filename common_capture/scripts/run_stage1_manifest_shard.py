                      
"""Run one formal Stage-1 manifest shard with route locks and exactly-once publish."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import os
import queue
import shutil
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_capture_manifest_shard as common              
import xonotic_capture as capture              
import xonotic_capture_v2 as v2              
import xonotic_motion_distance_pilot as motion              
import xonotic_stage1_review as review                   
import xonotic_stage1_reusable as reusable              
import xonotic_stage1_routes as routes              


EXPECTED_SOURCE_COMMIT = (
    "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
)
EXPECTED_CERTIFICATE_SOURCE_COMMIT = (
    "b40e26fd4e33b18b2002bf24beb6a78cef5fac96"
)
EXPECTED_ENEMY_PREFLIGHT_SOURCE_COMMIT = (
    "c68e111dff4c80c91d84526b27cc54053072ae52"
)
EXPECTED_ACTION_DESIGN_SCHEMA = "xonotic-stage1-action-design-v4"
FORMAL_SPLITS = capture.FORMAL_STAGE1_SPLITS
RAW_AUDIT_PERCENT = 2
MAX_RESIDENT_WARMUP_EVIDENCE_SEQUENCE = 1_000_000


def shard_paths(
    output_root: Path,
    index: int,
    count: int,
    wave: str = "primary",
) -> dict[str, Path]:
    if wave not in {"primary", "replenishment"}:
        raise capture.CaptureFailure(
            "invalid_candidate_wave", wave
        )
    root = (
        output_root
        / "manifests/shards"
        / wave
        / common.shard_tag(index, count)
    )
    return {
        "root": root,
        "accepted": root / "accepted_candidates.jsonl",
        "rejects": root / "rejects.jsonl",
        "queue": root / "queue_events.jsonl",
        "lock": root / "worker.lock",
    }


def queue_event(
    paths: dict[str, Path],
    episode_id: str,
    state: str,
    *,
    attempt_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    common.append_locked(
        paths["queue"],
        {
            "schema_version": "xonotic-stage1-queue-event-v1",
            "episode_id": episode_id,
            "attempt_id": attempt_id,
            "state": state,
            "detail": detail or {},
            "created_utc": capture.utc_now(),
        },
    )


def validate_manifest(
    path: Path, shard_index: int, shard_count: int
) -> list[dict[str, Any]]:
    if not path.is_file():
        raise capture.CaptureFailure(
            "input_manifest_missing", str(path)
        )
    rows = capture.load_jsonl(path)
    ids = [str(row.get("episode_id", "")) for row in rows]
    if not rows or any(not episode_id for episode_id in ids):
        raise capture.CaptureFailure(
            "input_manifest_empty_or_invalid", str(path)
        )
    if len(ids) != len(set(ids)):
        raise capture.CaptureFailure(
            "duplicate_episode_id", str(path)
        )
    for row in rows:
        player_path_reference = row.get("player_path_certificate")
        runtime_compatibility = row.get(
            "player_path_runtime_compatibility"
        ) or {}
        if player_path_reference:
            capture.load_player_path_certificate(row)
        policy_name = (
            row.get("enemy_policy", {}).get("name")
            if row.get("enemy_present")
            else None
        )
        expected_axis = {
            "idle": "anchor",
            "approach_retreat": "radial",
            "lateral_patrol": "lateral",
            "stop_and_go": "lateral",
        }.get(policy_name)
        certification = row.get("enemy_path_certification") or {}
        geometry = row.get("selected_geometry") or {}
        expected_pair_key = (
            f"{geometry.get('source_pair')}::{geometry.get('variant')}"
            if row.get("enemy_present")
            else None
        )
        checks = {
            "formal_split": row.get("split") in FORMAL_SPLITS,
            "role_matches_split": row.get("dataset_role")
            == row.get("split"),
            "stage1": row.get("training_stage") == "stage1",
            "formal_authorized": row.get(
                "formal_collection_authorized"
            )
            is True,
            "authorization_basis": bool(
                row.get("formal_authorization_basis")
            ),
            "input_not_preadmitted": row.get("training_admitted")
            is False,
            "source_commit": row.get("source_commit_required")
            == EXPECTED_SOURCE_COMMIT,
            "assigned_shard": int(
                row.get("assigned_shard", -1)
            )
            == shard_index,
            "shard_count": int(row.get("shard_count", -1))
            == shard_count,
            "candidate_wave": row.get("candidate_wave")
            in {"primary", "replenishment"},
            "action_design_schema": (
                (row.get("action_design") or {}).get(
                    "schema_version"
                )
                == EXPECTED_ACTION_DESIGN_SCHEMA
            ),
            "secondary_action_absent": (
                (row.get("action_design") or {}).get(
                    "weapon_action"
                )
                != "environmental_secondary"
            ),
            "player_path_certified": (
                not player_path_reference
                or (
                    player_path_reference.get("schema_version")
                    == capture.PLAYER_PATH_REFERENCE_SCHEMA
                    and player_path_reference.get("certified") is True
                    and player_path_reference.get("source_commit")
                    == EXPECTED_CERTIFICATE_SOURCE_COMMIT
                    and bool(
                        player_path_reference.get(
                            "path_contract_sha256"
                        )
                    )
                )
            ),
            "player_path_runtime_compatibility": (
                not player_path_reference
                or (
                    runtime_compatibility.get("schema_version")
                    == capture.PLAYER_PATH_RUNTIME_COMPATIBILITY_REFERENCE_SCHEMA
                    and runtime_compatibility.get(
                        "certificate_source_commit"
                    )
                    == EXPECTED_CERTIFICATE_SOURCE_COMMIT
                    and runtime_compatibility.get(
                        "runtime_source_commit"
                    )
                    == EXPECTED_SOURCE_COMMIT
                    and bool(runtime_compatibility.get("audit_sha256"))
                    and bool(
                        runtime_compatibility.get(
                            "certificate_index_sha256"
                        )
                    )
                )
            ),
            "enemy_path_certified": (
                not row.get("enemy_present")
                or (
                    certification.get("certified") is True
                    and certification.get("axis") == expected_axis
                    and certification.get("pair_key")
                    == expected_pair_key
                    and bool(
                        certification.get("preflight_sha256")
                    )
                )
            ),
        }
        if not all(checks.values()):
            raise capture.CaptureFailure(
                "formal_input_policy_failed",
                capture.canonical_json(
                    {
                        "episode_id": row.get("episode_id"),
                        "checks": checks,
                    }
                ),
            )
    return rows


def select_rows(
    rows: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    if limit < 0:
        raise capture.CaptureFailure(
            "invalid_episode_limit", str(limit)
        )
    return rows if limit == 0 else rows[:limit]


def validate_candidate_wave(
    rows: list[dict[str, Any]], wave: str, manifest: Path
) -> None:
    row_waves = {
        str(row.get("candidate_wave")) for row in rows
    }
    if row_waves != {wave}:
        raise capture.CaptureFailure(
            "manifest_candidate_wave_mismatch",
            capture.canonical_json(
                {
                    "manifest": str(manifest),
                    "resolved_wave": wave,
                    "row_waves": sorted(row_waves),
                }
            ),
        )


def verify_runtime_code_lock(path: Path) -> int:
    rows = path.read_text(encoding="utf-8").splitlines()
    if not rows:
        raise capture.CaptureFailure(
            "runtime_code_lock_empty", str(path)
        )
    for line_number, line in enumerate(rows, 1):
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            raise capture.CaptureFailure(
                "runtime_code_lock_invalid",
                f"{path}:{line_number}",
            )
        digest, relative = fields
        relative = relative.strip()
        relative_path = Path(relative)
        valid_digest = (
            len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest)
        )
        if (
            not valid_digest
            or relative_path.is_absolute()
            or ".." in relative_path.parts
        ):
            raise capture.CaptureFailure(
                "runtime_code_lock_invalid",
                f"{path}:{line_number}",
            )
        artifact = capture.ROOT / relative_path
        if (
            not artifact.is_file()
            or capture.sha256_file(artifact) != digest
        ):
            raise capture.CaptureFailure(
                "runtime_code_lock_mismatch", relative
            )
    return len(rows)


def verify_formal_audit(
    audit_path: Path, metadata_path: Path
) -> str:
    """Require the immutable formal audit before any worker may capture."""
    if not audit_path.is_file():
        raise capture.CaptureFailure(
            "formal_manifest_audit_missing", str(audit_path)
        )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    checks = {
        "schema": audit.get("schema_version")
        == "xonotic-stage1-v5-formal-audit-v1",
        "passed": audit.get("passed") is True,
        "metadata_sha256": audit.get("metadata_sha256")
        == capture.sha256_file(metadata_path),
        "primary_sha256": audit.get("primary_sha256")
        == (metadata.get("primary") or {}).get("sha256"),
        "replenishment_sha256": audit.get("replenishment_sha256")
        == (metadata.get("replenishment") or {}).get("sha256"),
        "runtime_code_lock_sha256": audit.get(
            "runtime_code_lock_sha256"
        )
        == (metadata.get("runtime_code_lock") or {}).get("sha256"),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "formal_manifest_audit_failed",
            capture.canonical_json(checks),
        )
    return capture.sha256_file(audit_path)


def verify_metadata(
    metadata_path: Path,
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
) -> tuple[str, str, str, str]:
    if not metadata_path.is_file():
        raise capture.CaptureFailure(
            "manifest_metadata_missing", str(metadata_path)
        )
    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )
    data_spec_sha256 = str(
        metadata.get("data_spec_sha256", "")
    )
    enemy_preflight = metadata.get("enemy_path_preflight") or {}
    wave = next(
        (
            name
            for name in ("primary", "replenishment")
            if Path(metadata[name]["path"]).name
            != input_manifest.name
            and any(
                Path(shard["path"]).name == input_manifest.name
                for shard in metadata[name]["shards"]
            )
        ),
        None,
    )
                                                                             
    if input_manifest.parent.name in {"primary", "replenishment"}:
        wave = input_manifest.parent.name
    if wave is None:
        raise capture.CaptureFailure(
            "manifest_wave_unresolved", str(input_manifest)
        )
    expected = next(
        (
            row
            for row in metadata[wave]["shards"]
            if int(row["shard_index"]) == shard_index
        ),
        None,
    )
    checks = {
        "schema": metadata.get("schema_version")
        in {
            "xonotic-stage1-formal-manifest-v1",
            "xonotic-stage1-formal-manifest-v2",
        },
        "source_commit": metadata.get("source_commit")
        == EXPECTED_SOURCE_COMMIT,
        "formal_authorized": metadata.get(
            "formal_collection_authorized"
        )
        is True,
        "data_spec_sha256": (
            data_spec_sha256
            == capture.sha256_file(
                capture.ROOT / "XONOTIC_DATA_SPEC_V2.md"
            )
        ),
        "shard_count": int(metadata.get("shard_count", -1))
        == shard_count,
        "shard_declared": expected is not None,
        "shard_sha256": expected is not None
        and expected.get("sha256") == input_sha256,
        "shard_filename": expected is not None
        and Path(expected.get("path", "")).name
        == input_manifest.name,
        "enemy_path_preflight_source": enemy_preflight.get(
            "source_commit"
        )
        == EXPECTED_ENEMY_PREFLIGHT_SOURCE_COMMIT,
        "enemy_path_preflight_runtime": enemy_preflight.get(
            "runtime_source_commit"
        )
        == EXPECTED_SOURCE_COMMIT,
        "enemy_path_preflight_sha256": bool(
            enemy_preflight.get("sha256")
        ),
    }
    if (
        metadata.get("schema_version")
        == "xonotic-stage1-formal-manifest-v2"
    ):
        path_certification = (
            metadata.get("path_certification") or {}
        )
        runtime_code_lock = (
            metadata.get("runtime_code_lock") or {}
        )
        replenishment_feasibility = (
            (metadata.get("replenishment") or {}).get(
                "feasibility"
            )
            or {}
        )
        semantic_weight_feasibility = (
            metadata.get("semantic_weight_feasibility") or {}
        )
        checks.update(
            {
                "player_path_index_declared": bool(
                    path_certification.get("index_path")
                    and path_certification.get("index_sha256")
                ),
                "player_path_certificate_source": (
                    path_certification.get(
                        "certificate_source_commit"
                    )
                    == EXPECTED_CERTIFICATE_SOURCE_COMMIT
                ),
                "player_path_runtime_source": (
                    path_certification.get("runtime_source_commit")
                    == EXPECTED_SOURCE_COMMIT
                ),
                "player_path_runtime_compatibility": (
                    (
                        path_certification.get(
                            "runtime_compatibility"
                        )
                        or {}
                    ).get("schema_version")
                    == capture.PLAYER_PATH_RUNTIME_COMPATIBILITY_REFERENCE_SCHEMA
                ),
                "player_path_runtime_policy": (
                    "no geometry/action fallback"
                    in str(
                        path_certification.get(
                            "runtime_policy", ""
                        )
                    )
                ),
                "runtime_code_lock_declared": bool(
                    runtime_code_lock.get("path")
                    and runtime_code_lock.get("sha256")
                    and int(
                        runtime_code_lock.get("entries", 0)
                    )
                    > 0
                ),
                "replenishment_feasibility_declared": (
                    replenishment_feasibility.get("schema_version")
                    == "xonotic-stage1-v5-replenishment-feasibility-reference-v1"
                    and replenishment_feasibility.get(
                        "capacity_clamping"
                    )
                    is False
                    and bool(
                        replenishment_feasibility.get("audit_path")
                        and replenishment_feasibility.get(
                            "audit_sha256"
                        )
                    )
                ),
                "semantic_weight_feasibility_declared": (
                    semantic_weight_feasibility.get(
                        "schema_version"
                    )
                    == (
                        "xonotic-stage1-v5-semantic-weight-"
                        "feasibility-reference-v1"
                    )
                    and semantic_weight_feasibility.get(
                        "capacity_clamping"
                    )
                    is False
                    and float(
                        semantic_weight_feasibility.get(
                            "mean_absolute_deviation_maximum",
                            -1,
                        )
                    )
                    == 0.50
                    and bool(
                        semantic_weight_feasibility.get("audit_path")
                        and semantic_weight_feasibility.get(
                            "audit_sha256"
                        )
                        and semantic_weight_feasibility.get(
                            "primary_selection_sha256"
                        )
                    )
                ),
            }
        )
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "manifest_metadata_mismatch",
            capture.canonical_json(checks),
        )
    capture.locked_root_artifact(
        enemy_preflight["path"],
        enemy_preflight["sha256"],
        "enemy_path_preflight",
    )
    if (
        metadata.get("schema_version")
        == "xonotic-stage1-formal-manifest-v2"
    ):
        path_certification = metadata["path_certification"]
        capture.locked_root_artifact(
            path_certification["index_path"],
            path_certification["index_sha256"],
            "player_path_certificate_index",
        )
        compatibility = path_certification[
            "runtime_compatibility"
        ]
        capture.locked_root_artifact(
            compatibility["audit_path"],
            compatibility["audit_sha256"],
            "player_path_runtime_compatibility_audit",
        )
        replenishment_feasibility = metadata["replenishment"][
            "feasibility"
        ]
        capture.locked_root_artifact(
            replenishment_feasibility["audit_path"],
            replenishment_feasibility["audit_sha256"],
            "replenishment_feasibility_audit",
        )
        semantic_weight_feasibility = metadata[
            "semantic_weight_feasibility"
        ]
        capture.locked_root_artifact(
            semantic_weight_feasibility["audit_path"],
            semantic_weight_feasibility["audit_sha256"],
            "semantic_weight_feasibility_audit",
        )
        runtime_code_lock = metadata["runtime_code_lock"]
        runtime_lock_path = capture.locked_root_artifact(
            runtime_code_lock["path"],
            runtime_code_lock["sha256"],
            "runtime_code_lock",
        )
        entries = verify_runtime_code_lock(runtime_lock_path)
        if entries != int(runtime_code_lock["entries"]):
            raise capture.CaptureFailure(
                "runtime_code_lock_entry_count",
                f"declared={runtime_code_lock['entries']} actual={entries}",
            )
    return (
        capture.sha256_file(metadata_path),
        wave,
        str(enemy_preflight["sha256"]),
        data_spec_sha256,
    )


def deterministic_raw_audit(episode_id: str) -> bool:
    return (
        int(capture.hashlib.sha256(episode_id.encode()).hexdigest()[:8], 16)
        % 100
        < RAW_AUDIT_PERCENT
    )


def prepare_route(
    row: dict[str, Any],
    output_root: Path,
    port: int,
) -> dict[str, Any]:
    scenario = copy.deepcopy(row)
    audio_expectation = capture.stage1_audio_expectation(scenario)
    scenario["expects_sound"] = audio_expectation["expects_sound"]
    scenario["audio_expectation_policy"] = audio_expectation
    player_path_certificate = (
        capture.load_player_path_certificate(scenario)
        if scenario.get("player_path_certificate")
        else None
    )
    request = row.get("route_request")
    if not request:
        if player_path_certificate is not None:
            scenario["frozen_actions_path"] = (
                player_path_certificate["actions_path"]
            )
            scenario["frozen_actions_sha256"] = (
                player_path_certificate["actions_sha256"]
            )
        return scenario
    route_id = str(request["route_id"])
    lock_path = (
        output_root / "route_locks" / f"{route_id}.lock"
    )
    with common.exclusive_lock(lock_path):
        plan_path = capture.locked_root_artifact(
            request["route_plan_path"],
            request["route_plan_sha256"],
            "route_plan",
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if plan.get("route_id") != route_id:
            raise capture.CaptureFailure(
                "route_plan_id_mismatch", route_id
            )
        capture.locked_root_artifact(
            request["route_csv_path"],
            request["route_csv_sha256"],
            "route_csv",
        )
        if player_path_certificate is not None:
                                                                             
                                                                       
                                                                            
                                                                           
                                                                      
            mode = str(
                (scenario.get("player_path_generation") or {}).get(
                    "mode", ""
                )
            )
            scenario["capture_route_calibration"] = False
            if mode == "declared_route_replay":
                scenario["route_plan"] = plan
            elif mode == "declared_certified_route_support":
                scenario.pop("route_plan", None)
            else:
                raise capture.CaptureFailure(
                    "formal_player_path_route_mode_invalid", mode
                )
            scenario["frozen_actions_path"] = (
                player_path_certificate["actions_path"]
            )
            scenario["frozen_actions_sha256"] = (
                player_path_certificate["actions_sha256"]
            )
            return scenario
        effective = routes.effective_plan(route_id)
        if effective.get("calibration_status") != "passed":
            if player_path_certificate is not None:
                raise capture.CaptureFailure(
                    "certified_path_support_route_not_current",
                    route_id,
                )
            queue_note = {
                "route_id": route_id,
                "state": "calibrating",
            }
            print(capture.canonical_json(queue_note), flush=True)
            routes.calibrate(route_id, port=port)
            effective = routes.effective_plan(route_id)
        if effective.get("calibration_status") != "passed":
            raise capture.CaptureFailure(
                "route_calibration_not_passed", route_id
            )
    scenario["capture_route_calibration"] = False
    if player_path_certificate is not None:
        mode = str(
            (scenario.get("player_path_generation") or {}).get(
                "mode", ""
            )
        )
        if mode == "declared_route_replay":
            scenario["route_plan"] = effective
        elif mode == "declared_certified_route_support":
            scenario.pop("route_plan", None)
        else:
            raise capture.CaptureFailure(
                "formal_player_path_route_mode_invalid", mode
            )
        scenario["frozen_actions_path"] = player_path_certificate[
            "actions_path"
        ]
        scenario["frozen_actions_sha256"] = player_path_certificate[
            "actions_sha256"
        ]
    else:
        scenario["route_plan"] = effective
        scenario["frozen_actions_path"] = effective[
            "frozen_actions_path"
        ]
        scenario["frozen_actions_sha256"] = effective[
            "frozen_actions_sha256"
        ]
    return scenario


def complete_formal_artifacts(
    result: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    package = Path(result["stage"]) / "package"
    relation = v2.relation_metrics(
        package, bool(row["enemy_present"])
    )
    motion_metrics = motion.motion_metrics(package)
    qa_path = package / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa["target_relation"] = relation
    qa["motion"] = motion_metrics
    role_eligible = capture.stage1_role_eligible(
        row, qa, relation, motion_metrics
    )
    qa["formal_candidate"] = {
        "capture_accepted": True,
        "role_eligible": role_eligible,
        "quota_assignment": "pending_global_realized_quota_audit",
        "training_admitted": False,
    }
    qa["training_admitted"] = False
    common.atomic_json(qa_path, qa)
    episode_path = package / "episode.json"
    episode = json.loads(
        episode_path.read_text(encoding="utf-8")
    )
    episode["actual_target_relation"] = relation
    episode["actual_motion"] = motion_metrics
    episode["formal_collection_authorized"] = True
    episode["training_admitted"] = False
    episode["quota_assignment"] = (
        "pending_global_realized_quota_audit"
    )
    common.atomic_json(episode_path, episode)
    result["qa"] = qa
    result["target_relation"] = relation
    result["motion"] = motion_metrics
    result["role_eligible"] = role_eligible
    return result


def candidate_record(
    row: dict[str, Any],
    scenario: dict[str, Any],
    result: dict[str, Any],
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    port: int,
    gpu: dict[str, Any],
) -> dict[str, Any]:
    qa = result["qa"]
    return {
        "schema_version": "xonotic-stage1-formal-candidate-v1",
        "episode_id": row["episode_id"],
        "attempt_id": result["attempt_id"],
        "candidate_wave": row["candidate_wave"],
        "split": row["split"],
        "dataset_role": row["dataset_role"],
        "primary_bucket": row["primary_bucket"],
        "formal_collection_authorized": True,
        "training_admitted": False,
        "quota_assignment": "pending_global_realized_quota_audit",
        "role_eligible": result["role_eligible"],
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": input_sha256,
        "input_scenario_sha256": capture.hashlib.sha256(
            capture.canonical_json(row).encode()
        ).hexdigest(),
        "runtime_scenario_sha256": capture.hashlib.sha256(
            capture.canonical_json(scenario).encode()
        ).hexdigest(),
        "assigned_shard": shard_index,
        "shard_count": shard_count,
        "capture_port": port,
        "gpu": gpu,
        "map": row["map"],
        "gametype": row["gametype"],
        "map_region_id": row["map_region_id"],
        "route_group_id": row.get("route_group_id"),
        "source_prototype_id": row.get("source_prototype_id"),
        "player_path_certificate": row.get(
            "player_path_certificate"
        ),
        "weapon": row["weapon"],
        "enemy_present": row["enemy_present"],
        "audio_expectation_policy": scenario[
            "audio_expectation_policy"
        ],
        "scheduler_targets": row["scheduler_targets"],
        "actual": {
            "motion": result["motion"],
            "target_relation": result["target_relation"],
        },
        "qa": {
            "hard_gates_pass": all(qa["hard_gates"].values()),
            "frames": qa["video"]["frames"],
            "audio_samples_per_channel": qa["audio"][
                "samples_per_channel"
            ],
            "mapping_rate": qa["mapping"]["success_rate"],
            "renderer": qa["runtime"]["renderer"],
            "fire_count": qa["events"]["fire_count"],
            "damage_count": qa["events"]["damage_count"],
            "route_passed": qa["route"]["passed"],
            "player_path_certificate_passed": (
                qa.get("player_path_certificate", {}).get(
                    "passed", True
                )
            ),
            "enemy_path_trace_passed": qa["enemy_policy"][
                "whole_path_trace"
            ]["passed"],
            "hud": qa["hud"],
            "requested_gametype": qa["mode"][
                "requested_gametype"
            ],
            "realized_gametype": qa["mode"][
                "realized_gametype"
            ],
        },
        "runtime": qa["runtime"],
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "raw_audit_selected": deterministic_raw_audit(
            row["episode_id"]
        ),
        "published_utc": capture.utc_now(),
    }


def provenance_files(stage: Path) -> list[tuple[Path, Path]]:
    return [
        (source, Path("capture_provenance") / relative)
        for source, relative in common.raw_files(stage)
        if relative.name != "raw_capture.avi"
    ]


def publish(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
    scenario: dict[str, Any],
    result: dict[str, Any],
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    port: int,
    gpu: dict[str, Any],
) -> dict[str, Any]:
    stage = Path(result["stage"])
    package = stage / "package"
    record = candidate_record(
        row,
        scenario,
        result,
        input_manifest,
        input_sha256,
        shard_index,
        shard_count,
        port,
        gpu,
    )
    common.atomic_json(package / "formal_candidate_record.json", record)
    episode_destination = (
        output_root / "candidates" / row["episode_id"]
    )
    episode_destination.parent.mkdir(parents=True, exist_ok=True)
    files = common.tree_files(package) + provenance_files(stage)
    (
        episode_temporary,
        package_hashes,
        package_bytes,
        package_seconds,
    ) = common.stage_files(
        files, episode_destination, result["attempt_id"]
    )
    package_ready = episode_temporary / "PUBLICATION_READY.json"
    common.atomic_json(
        package_ready,
        {
            "schema_version": "xonotic-stage1-publication-ready-v1",
            "kind": "candidate",
            "episode_id": row["episode_id"],
            "attempt_id": result["attempt_id"],
        },
    )
    package_hashes["PUBLICATION_READY.json"] = (
        capture.sha256_file(package_ready)
    )
    package_bytes += package_ready.stat().st_size
    raw_destination: Path | None = None
    raw_hashes: dict[str, str] = {}
    raw_bytes = 0
    if record["raw_audit_selected"]:
        raw_destination = (
            output_root / "raw_audit" / result["attempt_id"]
        )
        raw_source = [
            item
            for item in common.raw_files(stage)
            if item[1].name == "raw_capture.avi"
        ]
        (
            raw_temporary,
            raw_hashes,
            raw_bytes,
            _,
        ) = common.stage_files(
            raw_source, raw_destination, result["attempt_id"]
        )
        raw_ready = raw_temporary / "PUBLICATION_READY.json"
        common.atomic_json(
            raw_ready,
            {
                "schema_version": (
                    "xonotic-stage1-publication-ready-v1"
                ),
                "kind": "raw_audit",
                "episode_id": row["episode_id"],
                "attempt_id": result["attempt_id"],
            },
        )
        raw_hashes["PUBLICATION_READY.json"] = (
            capture.sha256_file(raw_ready)
        )
        raw_bytes += raw_ready.stat().st_size
        os.rename(raw_temporary, raw_destination)
    os.rename(episode_temporary, episode_destination)
    manifest = {
        **record,
        "episode_path": str(episode_destination),
        "raw_audit_path": (
            str(raw_destination) if raw_destination else None
        ),
        "package_sha256": package_hashes,
        "raw_audit_sha256": raw_hashes,
        "publication": {
            "strategy": (
                "exclusive-create-hash-fsync-atomic-rename"
            ),
            "package_bytes": package_bytes,
            "raw_audit_bytes": raw_bytes,
            "package_copy_seconds": package_seconds,
        },
    }
    if not common.append_locked(
        paths["accepted"], manifest, unique_field="episode_id"
    ):
        raise capture.CaptureFailure(
            "duplicate_manifest_publication", row["episode_id"]
        )
    queue_event(
        paths,
        row["episode_id"],
        "candidate_accepted",
        attempt_id=result["attempt_id"],
        detail={
            "episode_path": str(episode_destination),
            "role_eligible": result["role_eligible"],
        },
    )
    capture.clean_stage(stage)
    return manifest


def recover_episode(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
) -> dict[str, Any] | None:
    existing = next(
        (
            item
            for item in common.load_jsonl_locked(paths["accepted"])
            if item.get("episode_id") == row["episode_id"]
        ),
        None,
    )
    if existing is not None:
        episode = Path(str(existing.get("episode_path", "")))
        record_path = episode / "formal_candidate_record.json"
        if (
            not episode.is_dir()
            or not record_path.is_file()
            or json.loads(
                record_path.read_text(encoding="utf-8")
            ).get("episode_id")
            != row["episode_id"]
        ):
            raise capture.CaptureFailure(
                "accepted_manifest_artifact_missing",
                row["episode_id"],
            )
        if existing.get("raw_audit_selected") and not Path(
            str(existing.get("raw_audit_path", ""))
        ).is_dir():
            raise capture.CaptureFailure(
                "accepted_manifest_raw_audit_missing",
                row["episode_id"],
            )
        return existing
    episode = output_root / "candidates" / row["episode_id"]
    if not episode.exists():
        recover_staged_publication(output_root, row)
    if not episode.exists():
        return None
    record_path = episode / "formal_candidate_record.json"
    if not record_path.is_file():
        raise capture.CaptureFailure(
            "unrecoverable_published_episode", str(episode)
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    raw = (
        output_root / "raw_audit" / record["attempt_id"]
        if record["raw_audit_selected"]
        else None
    )
    if raw is not None and not raw.is_dir():
        raise capture.CaptureFailure(
            "published_raw_audit_missing", str(raw)
        )
    manifest = {
        **record,
        "episode_path": str(episode),
        "raw_audit_path": str(raw) if raw else None,
        "package_sha256": common.hash_tree(episode),
        "raw_audit_sha256": (
            common.hash_tree(raw) if raw else {}
        ),
        "publication": {
            "strategy": "recovered_after_atomic_publish"
        },
        "recovered_utc": capture.utc_now(),
    }
    common.append_locked(
        paths["accepted"], manifest, unique_field="episode_id"
    )
    queue_event(
        paths,
        row["episode_id"],
        "publication_recovered",
        attempt_id=record["attempt_id"],
    )
    return manifest


def quarantine_partial(
    output_root: Path,
    path: Path,
) -> None:
    if not path.exists():
        return
    root = output_root / "publication_recovery_quarantine"
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{path.name}.{time.time_ns()}"
    os.rename(path, destination)


def recover_staged_publication(
    output_root: Path,
    row: dict[str, Any],
) -> None:
    """Finish or quarantine an interrupted atomic publication."""
    episode = output_root / "candidates" / row["episode_id"]
    if episode.exists():
        return
    episode.parent.mkdir(parents=True, exist_ok=True)
    temporaries = sorted(
        episode.parent.glob(f".{episode.name}.tmp.*")
    )
    for temporary in temporaries:
        ready_path = temporary / "PUBLICATION_READY.json"
        record_path = temporary / "formal_candidate_record.json"
        if not ready_path.is_file() or not record_path.is_file():
            quarantine_partial(output_root, temporary)
            continue
        try:
            ready = json.loads(
                ready_path.read_text(encoding="utf-8")
            )
            record = json.loads(
                record_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            quarantine_partial(output_root, temporary)
            continue
        checks = {
            "ready_kind": ready.get("kind") == "candidate",
            "ready_episode": ready.get("episode_id")
            == row["episode_id"],
            "record_episode": record.get("episode_id")
            == row["episode_id"],
            "attempt_matches": ready.get("attempt_id")
            == record.get("attempt_id"),
        }
        if not all(checks.values()):
            quarantine_partial(output_root, temporary)
            continue
        attempt_id = str(record["attempt_id"])
        if record.get("raw_audit_selected"):
            raw = output_root / "raw_audit" / attempt_id
            if not raw.exists():
                raw_temporary = raw.parent / (
                    f".{raw.name}.tmp.{attempt_id}"
                )
                raw_ready_path = (
                    raw_temporary / "PUBLICATION_READY.json"
                )
                if not raw_ready_path.is_file():
                    quarantine_partial(
                        output_root, raw_temporary
                    )
                    quarantine_partial(output_root, temporary)
                    continue
                raw_ready = json.loads(
                    raw_ready_path.read_text(encoding="utf-8")
                )
                if (
                    raw_ready.get("kind") != "raw_audit"
                    or raw_ready.get("episode_id")
                    != row["episode_id"]
                    or raw_ready.get("attempt_id") != attempt_id
                ):
                    quarantine_partial(
                        output_root, raw_temporary
                    )
                    quarantine_partial(output_root, temporary)
                    continue
                os.rename(raw_temporary, raw)
        os.rename(temporary, episode)
        return


def recover_terminal_reject(
    paths: dict[str, Path],
    row: dict[str, Any],
) -> dict[str, Any] | None:
    """Return a completed hard reject without re-running the episode.

    Operational failures that exhausted a local retry budget and unexpected
    Python exceptions deliberately remain resumable by a scheduler retry.
    """
    matches = [
        item
        for item in common.load_jsonl_locked(paths["rejects"])
        if item.get("episode_id") == row["episode_id"]
        and item.get("terminal") is True
        and item.get("retryable") is False
        and item.get("failure_class", "capture_failure")
        == "capture_failure"
    ]
    return matches[-1] if matches else None


def next_attempt_index(
    paths: dict[str, Path], episode_id: str
) -> int:
    indexes: list[int] = []
    for source in (
        paths["accepted"],
        paths["rejects"],
        paths["queue"],
    ):
        for row in common.load_jsonl_locked(source):
            if row.get("episode_id") != episode_id:
                continue
            try:
                indexes.append(
                    int(str(row["attempt_id"]).rsplit("_a", 1)[1])
                )
            except (KeyError, ValueError, IndexError):
                pass
    for stage in (capture.TMP_ROOT / "raw").glob(
        f"{episode_id}_a*"
    ):
        try:
            indexes.append(int(stage.name.rsplit("_a", 1)[1]))
        except (ValueError, IndexError):
            pass
    return max(indexes, default=0)


def preserve_reject(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
    attempt_id: str,
    stage: Path,
    exc: Exception,
    terminal: bool,
) -> dict[str, Any]:
    reason = (
        exc.reason
        if isinstance(exc, capture.CaptureFailure)
        else type(exc).__name__
    )
    destination = (
        output_root / "rejects" / attempt_id
    )
    hashes: dict[str, str] = {}
    if stage.is_dir() and not destination.exists():
        temporary, hashes, _, _ = common.stage_files(
            common.tree_files(stage), destination, attempt_id
        )
        os.rename(temporary, destination)
    rejection = {
        "schema_version": "xonotic-stage1-formal-reject-v1",
        "episode_id": row["episode_id"],
        "attempt_id": attempt_id,
        "candidate_wave": row["candidate_wave"],
        "dataset_role": row["dataset_role"],
        "primary_bucket": row["primary_bucket"],
        "scheduler_targets": row["scheduler_targets"],
        "reason": reason,
        "detail": str(exc),
        "failure_class": (
            "capture_failure"
            if isinstance(exc, capture.CaptureFailure)
            else "unexpected_exception"
        ),
        "retryable": common.retryable_failure(exc),
        "terminal": terminal,
        "preserved_path": (
            str(destination) if destination.exists() else None
        ),
        "preserved_sha256": hashes,
        "rejected_utc": capture.utc_now(),
    }
    common.append_locked(paths["rejects"], rejection)
    queue_event(
        paths,
        row["episode_id"],
        "hard_reject_terminal" if terminal else "operational_retry",
        attempt_id=attempt_id,
        detail={"reason": reason},
    )
    if stage.is_dir():
        capture.clean_stage(stage)
    return rejection


class ResidentLaneController:
    """Own one fail-closed resident lane for one exact world group."""

    def __init__(
        self,
        *,
        lane_index: int,
        group_index: int,
        world_group: tuple[str, str],
        port: int,
        build: Path,
        warmup_root: Path,
    ) -> None:
        self.lane_index = lane_index
        self.group_index = group_index
        self.world_group = world_group
        self.port = port
        self.build = build
        self.warmup_root = warmup_root
        self.generation = 0
        self.lane: reusable.ReusableStage1Lane | None = None
        self.lane_root: Path | None = None
        self.warmed = False

    def _safe_remove_lane_root(self) -> None:
        if self.lane_root is None or not self.lane_root.exists():
            return
        resolved = self.lane_root.resolve()
        tmp = capture.TMP_ROOT.resolve()
        if resolved == tmp or tmp not in resolved.parents:
            raise capture.CaptureFailure(
                "resident_lane_cleanup_outside_tmp", str(resolved)
            )
        shutil.rmtree(resolved)

    def _start(self) -> reusable.ReusableStage1Lane:
        self.generation += 1
        map_name, gametype = self.world_group
        token = (
            f"lane-{self.lane_index:02d}"
            f"-group-{self.group_index:03d}"
            f"-gen-{self.generation:02d}"
            f"-{map_name}-{gametype}"
        )
        self.lane_root = (
            capture.TMP_ROOT / "resident" / token
        )
        self._safe_remove_lane_root()
        self.lane_root.parent.mkdir(parents=True, exist_ok=True)
        self.lane = reusable.ReusableStage1Lane(
            self.lane_root,
            build=self.build,
            port=self.port,
        )
        self.warmed = False
        return self.lane

    @staticmethod
    def _safe_remove_warmup_stage(stage: Path) -> None:
        if not stage.exists():
            return
        resolved = stage.resolve()
        allowed_parent = (
            capture.TMP_ROOT / "resident_warmups"
        ).resolve()
        if resolved.parent != allowed_parent:
            raise capture.CaptureFailure(
                "resident_warmup_cleanup_outside_tmp",
                str(resolved),
            )
        shutil.rmtree(resolved)

    def _allocate_warmup_evidence(
        self,
        map_name: str,
        gametype: str,
    ) -> tuple[str, Path, int, str]:
        """Reserve a persistent warm-up evidence path without reuse.

        Container PIDs and controller generations restart from the same
        values on every scheduler retry.  The legacy identifier is therefore
        only a base name.  Atomic ``mkdir`` chooses the first free monotonic
        suffix while preserving every older success, failure, or
        crash-interrupted directory for audit.
        """

        base_id = (
            f"resident_warmup_s{self.lane_index:02d}"
            f"_g{self.group_index:03d}"
            f"_r{self.generation:02d}"
            f"_p{os.getpid()}"
        )
        parent = (
            self.warmup_root / f"{map_name}__{gametype}"
        )
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise capture.CaptureFailure(
                "resident_warmup_failed",
                capture.canonical_json(
                    {
                        "phase": "evidence_parent_allocation",
                        "path": str(parent),
                        "error": str(exc),
                    }
                ),
            ) from exc
        for sequence in range(
            MAX_RESIDENT_WARMUP_EVIDENCE_SEQUENCE
        ):
            warmup_id = (
                base_id
                if sequence == 0
                else f"{base_id}_u{sequence:06d}"
            )
            evidence = parent / warmup_id
            try:
                evidence.mkdir(exist_ok=False)
            except FileExistsError:
                continue
            except OSError as exc:
                raise capture.CaptureFailure(
                    "resident_warmup_failed",
                    capture.canonical_json(
                        {
                            "phase": "evidence_atomic_allocation",
                            "path": str(evidence),
                            "error": str(exc),
                        }
                    ),
                ) from exc
            return warmup_id, evidence, sequence, base_id
        raise capture.CaptureFailure(
            "resident_warmup_failed",
            capture.canonical_json(
                {
                    "phase": "evidence_namespace_exhausted",
                    "base_id": base_id,
                    "maximum": (
                        MAX_RESIDENT_WARMUP_EVIDENCE_SEQUENCE
                    ),
                }
            ),
        )

    def _warmup(
        self,
        lane: reusable.ReusableStage1Lane,
        scenario: dict[str, Any],
    ) -> None:
        map_name, gametype = self.world_group
        (
            warmup_id,
            evidence,
            evidence_sequence,
            warmup_base_id,
        ) = self._allocate_warmup_evidence(
            map_name,
            gametype,
        )
        warmup_scenario = copy.deepcopy(scenario)
        warmup_scenario["episode_id"] = warmup_id
        warmup_scenario["split"] = (
            "v2_stage1_production_preflight"
        )
        warmup_scenario["formal_collection_authorized"] = False
        warmup_scenario["formal_authorization_basis"] = (
            "discarded_resident_process_warmup"
        )
        warmup_scenario["training_admitted"] = False
        stage = (
            capture.TMP_ROOT / "resident_warmups" / warmup_id
        )
        if stage.exists():
            self._safe_remove_warmup_stage(stage)
        started = time.monotonic()
        try:
            common.atomic_json(
                evidence / "ALLOCATION.json",
                {
                    "schema_version": (
                        "xonotic-stage1-resident-warmup-allocation-v1"
                    ),
                    "episode_id": warmup_id,
                    "warmup_base_id": warmup_base_id,
                    "evidence_sequence": evidence_sequence,
                    "allocation_policy": (
                        "atomic_mkdir_legacy_base_then_monotonic_suffix"
                    ),
                    "source_episode_id": scenario["episode_id"],
                    "lane_index": self.lane_index,
                    "group_index": self.group_index,
                    "generation": self.generation,
                    "map": map_name,
                    "gametype": gametype,
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "created_utc": capture.utc_now(),
                },
            )
            result = lane.execute(
                stage, warmup_scenario, retry=0
            )
            qa = result["qa"]
            checks = {
                "all_hard_gates": all(
                    qa["hard_gates"].values()
                ),
                "frames_320": qa["video"]["frames"]
                == capture.OUTPUT_TICKS,
                "audio_240000": qa["audio"][
                    "samples_per_channel"
                ]
                == capture.AUDIO_SAMPLES,
                "mapping_exact": qa["mapping"]["success_rate"]
                == 1.0,
                "presentation_phase": qa["hard_gates"].get(
                    "render_snapshot_presentation_phase"
                )
                is True,
                "training_excluded": (
                    warmup_scenario["training_admitted"] is False
                    and warmup_scenario[
                        "formal_collection_authorized"
                    ]
                    is False
                ),
            }
            record = {
                "schema_version": (
                    "xonotic-stage1-resident-warmup-v1"
                ),
                "episode_id": warmup_id,
                "source_episode_id": scenario["episode_id"],
                "lane_index": self.lane_index,
                "group_index": self.group_index,
                "generation": self.generation,
                "warmup_base_id": warmup_base_id,
                "evidence_sequence": evidence_sequence,
                "evidence_allocation_policy": (
                    "atomic_mkdir_legacy_base_then_monotonic_suffix"
                ),
                "map": map_name,
                "gametype": gametype,
                "passed": all(checks.values()),
                "checks": checks,
                "qa_sha256": capture.sha256_file(
                    Path(result["package_stage"]) / "qa.json"
                ),
                "wall_seconds": time.monotonic() - started,
                "formal_collection_authorized": False,
                "training_admitted": False,
                "created_utc": capture.utc_now(),
            }
            common.atomic_json(evidence / "RESULT.json", record)
            for name in (
                "server_console.log",
                "client_live_console.log",
                "client_render_console.log",
            ):
                source = stage / name
                if source.is_file():
                    shutil.copy2(source, evidence / name)
            if not record["passed"]:
                raise capture.CaptureFailure(
                    "resident_warmup_qa_failed",
                    capture.canonical_json(checks),
                )
            self.warmed = True
        except Exception as exc:
            common.atomic_json(
                evidence / "FAILURE.json",
                {
                    "schema_version": (
                        "xonotic-stage1-resident-warmup-failure-v1"
                    ),
                    "episode_id": warmup_id,
                    "warmup_base_id": warmup_base_id,
                    "evidence_sequence": evidence_sequence,
                    "evidence_allocation_policy": (
                        "atomic_mkdir_legacy_base_then_monotonic_suffix"
                    ),
                    "source_episode_id": scenario["episode_id"],
                    "reason": (
                        exc.reason
                        if isinstance(exc, capture.CaptureFailure)
                        else type(exc).__name__
                    ),
                    "detail": str(exc),
                    "wall_seconds": time.monotonic() - started,
                    "formal_collection_authorized": False,
                    "training_admitted": False,
                    "created_utc": capture.utc_now(),
                },
            )
            for name in (
                "server_console.log",
                "client_live_console.log",
                "client_render_console.log",
            ):
                source = stage / name
                if source.is_file():
                    shutil.copy2(source, evidence / name)
            raise capture.CaptureFailure(
                "resident_warmup_failed",
                capture.canonical_json(
                    {
                        "reason": (
                            exc.reason
                            if isinstance(
                                exc, capture.CaptureFailure
                            )
                            else type(exc).__name__
                        ),
                        "detail": str(exc),
                        "evidence": str(evidence),
                    }
                ),
            ) from exc
        finally:
            if stage.is_dir():
                self._safe_remove_warmup_stage(stage)

    def execute(
        self,
        stage: Path,
        scenario: dict[str, Any],
        *,
        retry: int,
    ) -> dict[str, Any]:
        requested_group = (
            str(scenario["map"]),
            str(scenario["gametype"]).lower(),
        )
        if requested_group != self.world_group:
            raise capture.CaptureFailure(
                "resident_scheduler_world_group_mismatch",
                f"expected={self.world_group} actual={requested_group}",
            )
        lane = self.lane if self.lane is not None else self._start()
        if not self.warmed:
            self._warmup(lane, scenario)
        return lane.execute(stage, scenario, retry=retry)

    def invalidate(self) -> None:
        lane = self.lane
                                                                           
                                                                     
        self.lane = None
        if lane is not None:
            try:
                lane.close()
            except Exception as exc:
                                                                         
                                                                            
                                                                    
                print(
                    "resident_lane_cleanup_warning "
                    f"lane={self.lane_index} "
                    f"group={self.group_index} "
                    f"error={type(exc).__name__} "
                    f"detail={json.dumps(str(exc))}",
                    file=sys.stderr,
                    flush=True,
                )
        try:
            self._safe_remove_lane_root()
        finally:
            self.lane_root = None
            self.warmed = False

    def close(self) -> None:
        self.invalidate()


def _capture_one_on_port(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
    port: int,
    max_attempts: int,
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    gpu: dict[str, Any],
    resident_lane: ResidentLaneController | None = None,
) -> dict[str, Any]:
    episode_lock = (
        output_root / "episode_locks" / f"{row['episode_id']}.lock"
    )
    with common.exclusive_lock(episode_lock):
        recovered = recover_episode(output_root, paths, row)
        if recovered is not None:
            print(f"resume accepted {row['episode_id']}", flush=True)
            return recovered
        rejected = recover_terminal_reject(paths, row)
        if rejected is not None:
            print(
                f"resume hard reject {row['episode_id']} "
                f"reason={rejected['reason']}",
                flush=True,
            )
            return rejected
        start_index = next_attempt_index(paths, row["episode_id"])
        for local_attempt in range(max_attempts):
            retry_index = start_index + local_attempt
            attempt_id = (
                f"{row['episode_id']}_a{retry_index + 1:02d}"
            )
            stage = capture.TMP_ROOT / "raw" / attempt_id
            queue_event(
                paths,
                row["episode_id"],
                "capturing",
                attempt_id=attempt_id,
                detail={"port": port},
            )
            try:
                scenario = prepare_route(
                    row, output_root, port
                )
                if resident_lane is None:
                    result = capture.execute_attempt(
                        scenario,
                        retry=retry_index,
                        publish=False,
                        port=port,
                    )
                else:
                    result = resident_lane.execute(
                        stage,
                        scenario,
                        retry=retry_index,
                    )
                result = complete_formal_artifacts(result, row)
                manifest = publish(
                    output_root,
                    paths,
                    row,
                    scenario,
                    result,
                    input_manifest,
                    input_sha256,
                    shard_index,
                    shard_count,
                    port,
                    gpu,
                )
                print(
                    f"accepted {row['episode_id']} "
                    f"renderer={manifest['qa']['renderer']}",
                    flush=True,
                )
                return manifest
            except Exception as exc:
                                                                          
                                                                          
                                                                       
                           
                if resident_lane is not None:
                    resident_lane.invalidate()
                retryable = common.retryable_failure(exc)
                terminal = (
                    not retryable
                    or local_attempt + 1 >= max_attempts
                )
                rejection = preserve_reject(
                    output_root,
                    paths,
                    row,
                    attempt_id,
                    stage,
                    exc,
                    terminal,
                )
                print(
                    f"reject {attempt_id} reason="
                    f"{rejection['reason']} retryable={retryable} "
                    f"terminal={terminal}",
                    flush=True,
                )
                if terminal:
                    return rejection
    raise AssertionError("unreachable")


def capture_one(
    output_root: Path,
    paths: dict[str, Path],
    row: dict[str, Any],
    port_pool: queue.Queue[int],
    max_attempts: int,
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    gpu: dict[str, Any],
) -> dict[str, Any]:
    port = port_pool.get()
    try:
        return _capture_one_on_port(
            output_root,
            paths,
            row,
            port,
            max_attempts,
            input_manifest,
            input_sha256,
            shard_index,
            shard_count,
            gpu,
        )
    finally:
        port_pool.put(port)


def resident_lane_plans(
    rows: list[dict[str, Any]], workers: int
) -> list[list[tuple[tuple[str, str], list[dict[str, Any]]]]]:
    """Deterministically balance isolated world-group chunks over lanes.

    Reuse never crosses a ``(map, gametype)`` boundary.  A world group larger
    than the ideal per-lane row count may, however, be split across multiple
    independent process groups.  This removes a single-map makespan tail
    without sharing any server/client state between chunks.
    """
    if workers <= 0:
        raise ValueError("workers must be positive")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["map"]), str(row["gametype"]).lower())
        grouped.setdefault(key, []).append(row)
    ideal_rows_per_lane = max(
        1, (len(rows) + workers - 1) // workers
    )
    groups: list[
        tuple[tuple[str, str], list[dict[str, Any]]]
    ] = []
    for key, values in sorted(grouped.items()):
        ordered = sorted(
            values,
            key=lambda row: (
                int(row.get("candidate_ordinal", 0)),
                str(row["episode_id"]),
            ),
        )
        chunk_count = max(
            1,
            (
                len(ordered)
                + ideal_rows_per_lane
                - 1
            )
            // ideal_rows_per_lane,
        )
        for chunk_index in range(chunk_count):
            start = chunk_index * len(ordered) // chunk_count
            end = (
                (chunk_index + 1)
                * len(ordered)
                // chunk_count
            )
            groups.append((key, ordered[start:end]))
    groups.sort(
        key=lambda item: (
            -len(item[1]),
            item[0],
            int(item[1][0].get("candidate_ordinal", 0)),
            str(item[1][0]["episode_id"]),
        )
    )
    plans: list[
        list[tuple[tuple[str, str], list[dict[str, Any]]]]
    ] = [[] for _ in range(workers)]
    loads = [0] * workers
    for group in groups:
        lane_index = min(
            range(workers), key=lambda index: (loads[index], index)
        )
        plans[lane_index].append(group)
        loads[lane_index] += len(group[1])
    return plans


def run_resident_lane_plan(
    *,
    lane_index: int,
    groups: list[
        tuple[tuple[str, str], list[dict[str, Any]]]
    ],
    port: int,
    build: Path,
    output_root: Path,
    paths: dict[str, Path],
    max_attempts: int,
    input_manifest: Path,
    input_sha256: str,
    shard_index: int,
    shard_count: int,
    gpu: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for group_index, (world_group, group_rows) in enumerate(
        groups, 1
    ):
        lane = ResidentLaneController(
            lane_index=lane_index,
            group_index=group_index,
            world_group=world_group,
            port=port,
            build=build,
            warmup_root=(
                paths["root"] / "resident_warmups"
            ),
        )
        try:
            for row in group_rows:
                results.append(
                    _capture_one_on_port(
                        output_root,
                        paths,
                        row,
                        port,
                        max_attempts,
                        input_manifest,
                        input_sha256,
                        shard_index,
                        shard_count,
                        gpu,
                        resident_lane=lane,
                    )
                )
        finally:
            lane.close()
    return results


def command_run(args: argparse.Namespace) -> int:
    capture.require_conda()
    input_manifest = Path(args.input_manifest).resolve()
    metadata_path = Path(args.manifest_metadata).resolve()
    audit_path = Path(args.manifest_audit).resolve()
    output_root = Path(args.output_root).resolve()
    capture.TMP_ROOT = Path(args.tmp_root).resolve()
    os.environ["XONOTIC_CAPTURE_TMP"] = str(capture.TMP_ROOT)
    os.environ["XONOTIC_X264_THREADS"] = str(args.x264_threads)
    os.environ["XONOTIC_X264_CPUSET"] = args.x264_cpuset
    os.environ["XONOTIC_LIVE_CONCURRENCY"] = str(
        args.live_concurrency
    )
    os.environ["XONOTIC_RENDER_CONCURRENCY"] = str(
        args.render_concurrency
    )
    os.environ["XONOTIC_RENDER_TIMEOUT_SECONDS"] = str(
        args.render_timeout_seconds
    )
    os.environ["XONOTIC_SDL_CONCURRENCY"] = str(
        args.sdl_concurrency
    )
    os.environ["XONOTIC_ENCODE_CONCURRENCY"] = str(
        args.encode_concurrency
    )
    capture.TMP_ROOT.mkdir(parents=True, exist_ok=True)
    input_rows = validate_manifest(
        input_manifest, args.shard_index, args.shard_count
    )
    build = capture.build_root()
    source_commit = (build / "SOURCE_COMMIT").read_text(
        encoding="utf-8"
    ).strip()
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise capture.CaptureFailure(
            "source_commit_mismatch",
            f"expected={EXPECTED_SOURCE_COMMIT} actual={source_commit}",
        )
    gpu = common.gpu_inventory(
        not args.allow_multiple_visible_gpus, args.gpu_index
    )
    input_sha256 = capture.sha256_file(input_manifest)
    (
        metadata_sha256,
        wave,
        enemy_preflight_sha256,
        data_spec_sha256,
    ) = verify_metadata(
        metadata_path,
        input_manifest,
        input_sha256,
        args.shard_index,
        args.shard_count,
    )
    audit_sha256 = verify_formal_audit(
        audit_path, metadata_path
    )
    validate_candidate_wave(input_rows, wave, input_manifest)
    if any(
        row.get("data_spec_sha256") != data_spec_sha256
        for row in input_rows
    ):
        raise capture.CaptureFailure(
            "manifest_data_spec_reference_mismatch",
            str(input_manifest),
        )
    if any(
        row.get("enemy_present")
        and row["enemy_path_certification"][
            "preflight_sha256"
        ]
        != enemy_preflight_sha256
        for row in input_rows
    ):
        raise capture.CaptureFailure(
            "manifest_enemy_path_preflight_mismatch",
            str(input_manifest),
        )
    rows = select_rows(input_rows, args.limit)
    selection_limited = len(rows) < len(input_rows)
    paths = shard_paths(
        output_root, args.shard_index, args.shard_count, wave
    )
    port_base = args.port_base + args.shard_index * args.port_stride
    lane_plans = (
        resident_lane_plans(rows, args.workers)
        if args.execution_mode == "resident"
        else None
    )
    resident_chunk_labels: dict[
        tuple[tuple[str, str], str], tuple[int, int]
    ] = {}
    if lane_plans is not None:
        chunks_by_world: dict[
            tuple[str, str], list[list[dict[str, Any]]]
        ] = {}
        for groups in lane_plans:
            for world_group, group_rows in groups:
                chunks_by_world.setdefault(
                    world_group, []
                ).append(group_rows)
        for world_group, chunks in chunks_by_world.items():
            ordered_chunks = sorted(
                chunks,
                key=lambda group_rows: (
                    int(
                        group_rows[0].get(
                            "candidate_ordinal", 0
                        )
                    ),
                    str(group_rows[0]["episode_id"]),
                ),
            )
            for chunk_index, group_rows in enumerate(
                ordered_chunks
            ):
                resident_chunk_labels[
                    (world_group, str(group_rows[0]["episode_id"]))
                ] = (chunk_index, len(ordered_chunks))
    resident_schedule = (
        [
            {
                "lane_index": lane_index,
                "port": port_base + lane_index,
                "rows": sum(
                    len(group_rows)
                    for _, group_rows in groups
                ),
                "groups": [
                    {
                        "map": world_group[0],
                        "gametype": world_group[1],
                        "rows": len(group_rows),
                        "world_group_chunk_index": (
                            resident_chunk_labels[
                                (
                                    world_group,
                                    str(
                                        group_rows[0][
                                            "episode_id"
                                        ]
                                    ),
                                )
                            ][0]
                        ),
                        "world_group_chunk_count": (
                            resident_chunk_labels[
                                (
                                    world_group,
                                    str(
                                        group_rows[0][
                                            "episode_id"
                                        ]
                                    ),
                                )
                            ][1]
                        ),
                        "first_candidate_ordinal": int(
                            group_rows[0].get(
                                "candidate_ordinal", 0
                            )
                        ),
                        "last_candidate_ordinal": int(
                            group_rows[-1].get(
                                "candidate_ordinal", 0
                            )
                        ),
                        "first_episode_id": str(
                            group_rows[0]["episode_id"]
                        ),
                        "last_episode_id": str(
                            group_rows[-1]["episode_id"]
                        ),
                    }
                    for world_group, group_rows in groups
                ],
            }
            for lane_index, groups in enumerate(lane_plans or [])
        ]
        if lane_plans is not None
        else None
    )
    run_metadata = {
        "schema_version": "xonotic-stage1-formal-worker-v1",
        "started_utc": capture.utc_now(),
        "candidate_wave": wave,
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": input_sha256,
        "manifest_metadata": str(metadata_path),
        "manifest_metadata_sha256": metadata_sha256,
        "manifest_audit": str(audit_path),
        "manifest_audit_sha256": audit_sha256,
        "enemy_path_preflight_sha256": (
            enemy_preflight_sha256
        ),
        "output_root": str(output_root),
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "planned_rows": len(rows),
        "input_manifest_rows": len(input_rows),
        "episode_limit": args.limit,
        "selection_limited": selection_limited,
        "workers": args.workers,
        "execution_mode": args.execution_mode,
        "resident_reuse_policy": (
            "exact_map_gametype_group_only; discarded nontraining "
            "full-QA warmup per process generation; fresh server world "
            "per published episode; destroy lane on group change or "
            "any failure; oversized world groups may be deterministically "
            "split across isolated process groups"
            if args.execution_mode == "resident"
            else None
        ),
        "resident_schedule": resident_schedule,
        "resident_schedule_policy": (
            {
                "method": (
                    "deterministic_lpt_over_isolated_world_group_chunks"
                ),
                "ideal_rows_per_lane": max(
                    1,
                    (len(rows) + args.workers - 1)
                    // args.workers,
                ),
                "world_group_chunks": sum(
                    len(groups) for groups in (lane_plans or [])
                ),
                "oversized_world_group_split_only": True,
            }
            if lane_plans is not None
            else None
        ),
        "live_concurrency": args.live_concurrency,
        "render_concurrency": args.render_concurrency,
        "render_timeout_seconds": (
            capture.configured_render_timeout_seconds()
        ),
        "sdl_concurrency": args.sdl_concurrency,
        "encode_concurrency": args.encode_concurrency,
        "x264_threads": args.x264_threads,
        "x264_cpuset": capture.configured_x264_cpuset(),
        "x264_cpuset_cpu_count": (
            capture.configured_x264_cpuset_cpu_count()
        ),
        "port_base": port_base,
        "tmp_root": str(capture.TMP_ROOT),
        "build": str(build),
        "source_commit": source_commit,
        "gpu": gpu,
        "audio_expectation_policy": {
            "schema_version": (
                capture.STAGE1_AUDIO_EXPECTATION_POLICY_SCHEMA
            ),
            "player_footstep_speed_threshold": (
                capture.STAGE1_PLAYER_FOOTSTEP_SPEED_THRESHOLD
            ),
            "manifest_rows_immutable": True,
            "synthetic_audio_fallback": False,
        },
        "incomplete_exit_code": args.incomplete_exit_code,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    with common.exclusive_lock(paths["lock"], nonblocking=True):
        common.atomic_json(
            paths["root"] / "RUN_METADATA.json", run_metadata
        )
        results: list[dict[str, Any]] = []
        if args.execution_mode == "resident":
            if lane_plans is None:
                raise AssertionError("resident plans missing")
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=args.workers
            ) as executor:
                futures = [
                    executor.submit(
                        run_resident_lane_plan,
                        lane_index=lane_index,
                        groups=groups,
                        port=port_base + lane_index,
                        build=build,
                        output_root=output_root,
                        paths=paths,
                        max_attempts=args.max_operational_attempts,
                        input_manifest=input_manifest,
                        input_sha256=input_sha256,
                        shard_index=args.shard_index,
                        shard_count=args.shard_count,
                        gpu=gpu,
                    )
                    for lane_index, groups in enumerate(lane_plans)
                    if groups
                ]
                completed = 0
                for future in concurrent.futures.as_completed(
                    futures
                ):
                    lane_results = future.result()
                    results.extend(lane_results)
                    completed += len(lane_results)
                    print(
                        f"progress {completed}/{len(rows)} "
                        "resident_lane_complete",
                        flush=True,
                    )
        else:
            port_pool: queue.Queue[int] = queue.Queue()
            for port in range(
                port_base, port_base + args.workers
            ):
                port_pool.put(port)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=args.workers
            ) as executor:
                futures = {
                    executor.submit(
                        capture_one,
                        output_root,
                        paths,
                        row,
                        port_pool,
                        args.max_operational_attempts,
                        input_manifest,
                        input_sha256,
                        args.shard_index,
                        args.shard_count,
                        gpu,
                    ): row
                    for row in rows
                }
                for completed, future in enumerate(
                    concurrent.futures.as_completed(futures), 1
                ):
                    result = future.result()
                    results.append(result)
                    print(
                        f"progress {completed}/{len(rows)} "
                        f"{result['episode_id']}",
                        flush=True,
                    )
        accepted = [
            row for row in results if "episode_path" in row
        ]
        role_eligible = [
            row
            for row in accepted
            if row.get("role_eligible") is True
        ]
        terminal = [
            row for row in results if row.get("terminal") is True
        ]
        incomplete = [
            row
            for row in terminal
            if row.get("retryable") is True
            or row.get("failure_class") == "unexpected_exception"
        ]
        completed_hard_rejects = [
            row for row in terminal if row not in incomplete
        ]
        selection_complete = (
            len(accepted) + len(completed_hard_rejects)
            == len(rows)
        )
        shard_passed = selection_complete and not incomplete
        worker_exit_code = (
            0 if shard_passed else args.incomplete_exit_code
        )
        finished = {
            **run_metadata,
            "finished_utc": capture.utc_now(),
            "accepted_candidates": len(accepted),
            "role_eligible_candidates": len(role_eligible),
            "terminal_rejects": len(terminal),
            "completed_hard_rejects": len(
                completed_hard_rejects
            ),
            "incomplete_operational_or_unexpected": len(incomplete),
            "selection_complete": selection_complete,
            "complete": selection_complete
            and not selection_limited,
            "quota_ready": False,
            "quota_state": (
                "pending_global_realized_quota_audit"
            ),
            "pass": shard_passed,
            "worker_exit_code": worker_exit_code,
            "worker_exit_disposition": (
                "complete"
                if shard_passed
                else "retryable_shard_incomplete"
            ),
        }
        common.atomic_json(
            paths["root"] / "RUN_RESULT.json", finished
        )
    print(json.dumps(finished, indent=2, sort_keys=True))
    return int(finished["worker_exit_code"])


def command_status(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root).resolve()
    paths = shard_paths(
        output_root,
        args.shard_index,
        args.shard_count,
        args.candidate_wave,
    )
    accepted = common.load_jsonl_locked(paths["accepted"])
    rejects = common.load_jsonl_locked(paths["rejects"])
    terminal = [row for row in rejects if row.get("terminal")]
    report = {
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "accepted_candidates": len(
            {row["episode_id"] for row in accepted}
        ),
        "reject_attempts": len(rejects),
        "terminal_rejects": len(terminal),
        "run_result": (
            json.loads(
                (paths["root"] / "RUN_RESULT.json").read_text(
                    encoding="utf-8"
                )
            )
            if (paths["root"] / "RUN_RESULT.json").is_file()
            else None
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--input-manifest", required=True)
    run.add_argument("--manifest-metadata", required=True)
    run.add_argument("--manifest-audit", required=True)
    run.add_argument("--output-root", required=True)
    run.add_argument("--tmp-root", required=True)
    run.add_argument("--shard-index", required=True, type=int)
    run.add_argument("--shard-count", type=int, default=32)
    run.add_argument("--gpu-index", type=int, default=0)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument(
        "--execution-mode",
        choices=("resident", "oneshot"),
        default="resident",
        help=(
            "resident reuses process resources only within an exact "
            "(map, gametype) group; oneshot is a diagnostic cold-start "
            "mode and is never selected automatically"
        ),
    )
    run.add_argument("--live-concurrency", type=int, default=4)
    run.add_argument("--render-concurrency", type=int, default=4)
    run.add_argument(
        "--render-timeout-seconds",
        type=float,
        default=240,
    )
    run.add_argument("--sdl-concurrency", type=int, default=4)
    run.add_argument("--encode-concurrency", type=int, default=4)
    run.add_argument("--x264-threads", type=int, default=16)
    run.add_argument("--x264-cpuset", default="")
    run.add_argument("--port-base", type=int, default=24_000)
    run.add_argument("--port-stride", type=int, default=64)
    run.add_argument("--max-operational-attempts", type=int, default=2)
    run.add_argument(
        "--incomplete-exit-code",
        type=int,
        choices=(0, 2, 3),
        default=2,
        help=(
            "exit code after a clean worker pass that still has retryable "
            "episodes; fatal initialization/runtime errors remain exit 2"
        ),
    )
    run.add_argument("--limit", type=int, default=0)
    run.add_argument(
        "--allow-multiple-visible-gpus", action="store_true"
    )
    run.set_defaults(func=command_run)
    status = commands.add_parser("status")
    status.add_argument("--output-root", required=True)
    status.add_argument("--shard-index", required=True, type=int)
    status.add_argument("--shard-count", type=int, default=32)
    status.add_argument(
        "--candidate-wave",
        choices=("primary", "replenishment"),
        default="primary",
    )
    status.set_defaults(func=command_status)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
