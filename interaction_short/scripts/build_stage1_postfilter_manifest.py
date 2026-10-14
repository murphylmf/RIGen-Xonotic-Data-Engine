                      
"""Build an auditable Stage-1 manifest after fall/camera-jump screening."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq


ROOT = Path("./xonotic_capture")
DEFAULT_MANIFEST_ROOT = (
    ROOT / "manifests/stage1_foundation_v5_formal_56x1_recovery_r6"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT / "stage1_foundation_v5_output_56x1_menu_clean_r3"
)
DEFAULT_DESTINATION = (
    ROOT
    / "manifests/stage1_foundation_v5_accepted_postfiltered_r1_20260730"
)

OUTPUT_TICK_FIRST = 64
OUTPUT_TICK_COUNT = 320
PHYSICS_HZ = 64

KNOWN_CAMERA_JUMP = "s1v5f_s1v5p_001436_v04"
KNOWN_BACKWARD_FALL = "s1v5f_s1v5w_000351_v05"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def stream_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"{path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise RuntimeError(
                    f"expected JSON object: {path}:{line_number}"
                )
            yield value


def glob_paths(pattern: Path) -> list[Path]:
    return [Path(value) for value in sorted(glob.glob(str(pattern)))]


def hard_reject_ids(path: Path) -> set[str]:
    result: set[str] = set()
    for row in stream_jsonl(path):
        if (
            row.get("terminal") is True
            and row.get("retryable") is False
            and row.get("failure_class", "capture_failure")
            == "capture_failure"
        ):
            result.add(str(row["episode_id"]))
    return result


def valid_candidate(output_root: Path, episode_id: str) -> bool:
    record_path = (
        output_root
        / "candidates"
        / episode_id
        / "formal_candidate_record.json"
    )
    if not record_path.is_file():
        return False
    try:
        return load_json(record_path).get("episode_id") == episode_id
    except (OSError, ValueError, RuntimeError):
        return False


def load_accepted_universe(
    manifest_root: Path,
    output_root: Path,
) -> tuple[
    set[str],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    metadata_path = manifest_root / "MANIFEST_METADATA.json"
    metadata = load_json(metadata_path)
    recovery = metadata.get("recovery") or {}
    namespace = str(recovery["namespace"])

    snapshot_reference = recovery["terminal_snapshot"]
    snapshot_path = ROOT / str(snapshot_reference["path"])
    observed_snapshot_sha = sha256_file(snapshot_path)
    expected_snapshot_sha = str(snapshot_reference["sha256"])
    if observed_snapshot_sha != expected_snapshot_sha:
        raise RuntimeError(
            "terminal snapshot hash mismatch: "
            f"{observed_snapshot_sha} != {expected_snapshot_sha}"
        )
    snapshot = load_json(snapshot_path)
    snapshot_accepted = {
        str(value) for value in snapshot["accepted_episode_ids"]
    }
    snapshot_hard = {
        str(value) for value in snapshot["hard_reject_episode_ids"]
    }
    pending_snapshot = {
        str(value) for value in snapshot["pending_episode_ids"]
    }
    if snapshot_accepted & snapshot_hard:
        raise RuntimeError("terminal snapshot accepted/hard overlap")

    current_recovery_accepted: set[str] = set()
    current_recovery_hard: set[str] = set()
    current_journal_root = (
        output_root
        / "manifests/recovery_runs"
        / namespace
        / "shards/primary"
    )
    recovery_manifest_paths = glob_paths(
        manifest_root / "shards/primary/shard-*.jsonl"
    )
    for manifest_path in recovery_manifest_paths:
        tag = manifest_path.stem
        shard_ids = {
            str(row["episode_id"])
            for row in stream_jsonl(manifest_path)
        }
        shard_root = current_journal_root / tag
        accepted_ids = {
            str(row["episode_id"])
            for row in stream_jsonl(
                shard_root / "accepted_candidates.jsonl"
            )
        }
        hard_ids = hard_reject_ids(shard_root / "rejects.jsonl")
        for episode_id in shard_ids - accepted_ids - hard_ids:
            if valid_candidate(output_root, episode_id):
                accepted_ids.add(episode_id)
        unexpected = (accepted_ids | hard_ids) - shard_ids
        if unexpected:
            raise RuntimeError(
                f"{tag}: unexpected recovery IDs: "
                + ", ".join(sorted(unexpected)[:20])
            )
        if accepted_ids & hard_ids:
            raise RuntimeError(f"{tag}: accepted/hard overlap")
        current_recovery_accepted.update(accepted_ids)
        current_recovery_hard.update(hard_ids)

    recovery_terminal = (
        current_recovery_accepted | current_recovery_hard
    )
    if not recovery_terminal <= pending_snapshot:
        unexpected = recovery_terminal - pending_snapshot
        raise RuntimeError(
            "recovery terminal IDs not in snapshot pending set: "
            + ", ".join(sorted(unexpected)[:20])
        )

    accepted_ids = snapshot_accepted | current_recovery_accepted
    hard_ids = snapshot_hard | current_recovery_hard
    if accepted_ids & hard_ids:
        raise RuntimeError("global accepted/hard overlap")

    initial_namespace = (
        namespace[: -len("-v2")]
        if namespace.endswith("-v2")
        else None
    )
    record_paths = glob_paths(
        output_root
        / "manifests/shards/primary/shard-*-of-*/accepted_candidates.jsonl"
    )
    namespaces = [
        value
        for value in (initial_namespace, namespace)
        if value
    ]
    for value in namespaces:
        record_paths.extend(
            glob_paths(
                output_root
                / "manifests/recovery_runs"
                / value
                / "shards/primary/shard-*-of-*"
                / "accepted_candidates.jsonl"
            )
        )

    records: dict[str, dict[str, Any]] = {}
    record_source: dict[str, str] = {}
    for path in sorted(set(record_paths)):
        for row in stream_jsonl(path):
            episode_id = str(row["episode_id"])
            if episode_id not in accepted_ids:
                continue
            previous = records.get(episode_id)
            if previous is not None:
                previous_package = previous.get("package_sha256")
                current_package = row.get("package_sha256")
                if (
                    previous_package
                    and current_package
                    and previous_package != current_package
                ):
                    raise RuntimeError(
                        f"conflicting accepted record for {episode_id}: "
                        f"{record_source[episode_id]} vs {path}"
                    )
            records[episode_id] = row
            record_source[episode_id] = str(path)

    missing_records = accepted_ids - records.keys()
    if missing_records:
        raise RuntimeError(
            "accepted IDs missing journal records: "
            + ", ".join(sorted(missing_records)[:20])
        )

    audit = {
        "manifest_metadata_path": str(metadata_path),
        "manifest_metadata_sha256": sha256_file(metadata_path),
        "terminal_snapshot_path": str(snapshot_path),
        "terminal_snapshot_sha256": observed_snapshot_sha,
        "recovery_namespace": namespace,
        "record_journals": [str(path) for path in sorted(set(record_paths))],
        "snapshot_accepted": len(snapshot_accepted),
        "snapshot_hard_rejects": len(snapshot_hard),
        "snapshot_pending": len(pending_snapshot),
        "recovery_accepted": len(current_recovery_accepted),
        "recovery_hard_rejects": len(current_recovery_hard),
        "recovery_unfinished_ignored": len(
            pending_snapshot - recovery_terminal
        ),
        "accepted_total": len(accepted_ids),
        "hard_reject_total": len(hard_ids),
    }
    return accepted_ids, records, audit


def output_state_rows(package: Path) -> dict[str, list[Any]]:
    columns = [
        "server_tick",
        "post.origin",
        "post.velocity",
        "post.onground",
        "applied_action.forward",
        "applied_action.jump",
    ]
    values = pq.read_table(
        package / "states.parquet",
        columns=columns,
    ).to_pydict()
    order = sorted(
        (
            index
            for index, tick in enumerate(values["server_tick"])
            if OUTPUT_TICK_FIRST
            <= int(tick)
            < OUTPUT_TICK_FIRST + OUTPUT_TICK_COUNT
        ),
        key=lambda index: int(values["server_tick"][index]),
    )
    ticks = [int(values["server_tick"][index]) for index in order]
    expected_ticks = list(
        range(OUTPUT_TICK_FIRST, OUTPUT_TICK_FIRST + OUTPUT_TICK_COUNT)
    )
    if ticks != expected_ticks:
        raise RuntimeError(
            f"{package.name}: output state ticks are not exact"
        )
    return {
        name: [values[name][index] for index in order]
        for name in columns
    }


def ungrounded_runs(grounded: list[bool]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(grounded):
        if not value and start is None:
            start = index
        elif value and start is not None:
            result.append((start, index - 1))
            start = None
    if start is not None:
        result.append((start, len(grounded) - 1))
    return result


def evaluate_backward_fall(
    package: Path,
    prototype_id: str,
    *,
    minimum_drop: float,
    minimum_ungrounded_ticks: int,
    backward_threshold: float,
) -> dict[str, Any]:
    states = output_state_rows(package)
    ticks = [int(value) for value in states["server_tick"]]
    origins = states["post.origin"]
    velocities = states["post.velocity"]
    grounded = [
        bool(value) for value in states["post.onground"]
    ]
    forward = [
        float(value) for value in states["applied_action.forward"]
    ]
    jump = [
        int(value) for value in states["applied_action.jump"]
    ]
    z = [float(value[2]) for value in origins]
    vz = [float(value[2]) for value in velocities]
    candidates: list[dict[str, Any]] = []
    for start, end in ungrounded_runs(grounded):
        baseline_index = max(0, start - 1)
        minimum_index = min(
            range(start, end + 1),
            key=lambda index: z[index],
        )
        drop = z[baseline_index] - z[minimum_index]
        onset_start = max(0, start - 3)
        onset_end = min(len(forward), start + 4)
        onset_min_forward = min(
            forward[onset_start:onset_end],
            default=0.0,
        )
        candidates.append(
            {
                "start_tick": ticks[start],
                "end_tick": ticks[end],
                "duration_ticks": end - start + 1,
                "duration_seconds": (
                    (end - start + 1) / PHYSICS_HZ
                ),
                "baseline_z": z[baseline_index],
                "minimum_z": z[minimum_index],
                "vertical_drop": drop,
                "minimum_vertical_velocity": min(vz[start : end + 1]),
                "onset_min_forward_command": onset_min_forward,
                "backward_at_onset": (
                    onset_min_forward < -backward_threshold
                ),
            }
        )

    qualifying = [
        value
        for value in candidates
        if value["duration_ticks"] >= minimum_ungrounded_ticks
        and value["vertical_drop"] >= minimum_drop
        and value["backward_at_onset"]
    ]
    qualifying.sort(
        key=lambda value: (
            value["vertical_drop"],
            value["duration_ticks"],
        ),
        reverse=True,
    )
    evidence = qualifying[0] if qualifying else None
    return {
        "source_prototype_id": prototype_id,
        "evidence_episode_id": package.name,
        "output_tick_first": OUTPUT_TICK_FIRST,
        "output_tick_count": OUTPUT_TICK_COUNT,
        "jump_active_ticks": sum(int(value != 0) for value in jump),
        "backward_active_ticks": sum(
            int(value < -backward_threshold) for value in forward
        ),
        "origin_z_start": z[0],
        "origin_z_end": z[-1],
        "origin_z_minimum": min(z),
        "net_downward_displacement": z[0] - z[-1],
        "maximum_vertical_drawdown": max(
            max(z[: index + 1]) - z[index]
            for index in range(len(z))
        ),
        "longest_ungrounded_ticks": max(
            (end - start + 1)
            for start, end in ungrounded_runs(grounded)
        )
        if not all(grounded)
        else 0,
        "qualifying_fall": evidence,
        "excluded": bool(evidence is not None and not any(jump)),
    }


def motion(record: dict[str, Any]) -> dict[str, Any]:
    value = (
        (record.get("actual") or {}).get("motion") or {}
    )
    if not isinstance(value, dict):
        raise RuntimeError(
            f"{record.get('episode_id')}: invalid motion metrics"
        )
    return value


def numeric_metric(
    record: dict[str, Any],
    name: str,
) -> float:
    value = motion(record).get(name)
    if value is None:
        raise RuntimeError(
            f"{record.get('episode_id')}: missing motion metric {name}"
        )
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(
            f"{record.get('episode_id')}: non-finite metric {name}"
        )
    return result


def normalize_counter_value(value: Any) -> str:
    if value is None or value == "":
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def dimensions(
    episode_ids: Iterable[str],
    records: dict[str, dict[str, Any]],
) -> dict[str, dict[str, int]]:
    fields = (
        "dataset_role",
        "primary_bucket",
        "enemy_present",
        "map",
        "gametype",
        "weapon",
        "split",
    )
    counters = {field: Counter() for field in fields}
    for episode_id in episode_ids:
        row = records[episode_id]
        for field in fields:
            counters[field][
                normalize_counter_value(row.get(field))
            ] += 1
    return {
        field: dict(
            sorted(
                counter.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )
        for field, counter in counters.items()
    }


def write_jsonl(
    path: Path,
    episode_ids: Iterable[str],
    records: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    ruleset_sha256: str,
) -> int:
    count = 0
    with path.open("x", encoding="utf-8") as handle:
        for episode_id in episode_ids:
            row = dict(records[episode_id])
            row["post_collection_screening"] = {
                "schema_version": (
                    "xonotic-stage1-post-collection-screening-v1"
                ),
                "ruleset_sha256": ruleset_sha256,
                **decisions[episode_id],
            }
            handle.write(canonical_json(row) + "\n")
            count += 1
        handle.flush()
        os.fsync(handle.fileno())
    return count


def write_lines(path: Path, values: Iterable[str]) -> int:
    count = 0
    with path.open("x", encoding="utf-8") as handle:
        for value in values:
            handle.write(value + "\n")
            count += 1
        handle.flush()
        os.fsync(handle.fileno())
    return count


def report_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    reasons = counts["excluded_by_reason"]
    known = report["known_regression_examples"]
    return f"""# Stage-1 post-collection screening report

Created: `{report["created_utc"]}`

This manifest starts from the landed, formally accepted Stage-1 union. The
unfinished tail is intentionally ignored. Existing packages are not modified
or deleted.

## Result

- Accepted input: **{counts["accepted_input"]}**
- Kept: **{counts["kept"]}**
- Excluded: **{counts["excluded"]}**
- Backward unintentional fall: **{reasons["backward_unintentional_fall_v1"]}**
- Single-frame camera angular jump: **{reasons["camera_single_frame_angular_jump_v1"]}**
- Multi-reason overlap: **{counts["multi_reason_excluded"]}**

## Rules

1. Backward unintentional fall: no jump anywhere in the 320 output ticks,
   backward input at fall onset, at least
   `{report["rules"]["backward_unintentional_fall_v1"]["minimum_ungrounded_ticks"]}`
   consecutive ungrounded ticks, and at least
   `{report["rules"]["backward_unintentional_fall_v1"]["minimum_vertical_drop_units"]}`
   units of downward travel.
2. Camera angular jump: yaw or pitch changes by more than
   `{report["rules"]["camera_single_frame_angular_jump_v1"]["maximum_frame_step_deg"]}`
   degrees in one rendered frame.

The camera rule uses engine camera truth. It does not use image-difference,
optical-flow, menu, or other pixel heuristics.

## Regression anchors

- `{KNOWN_BACKWARD_FALL}`: `{known[KNOWN_BACKWARD_FALL]["decision"]}`
  (`{", ".join(known[KNOWN_BACKWARD_FALL]["reasons"])}`)
- `{KNOWN_CAMERA_JUMP}`: `{known[KNOWN_CAMERA_JUMP]["decision"]}`
  (`{", ".join(known[KNOWN_CAMERA_JUMP]["reasons"])}`)

## Artifacts

- Main manifest: `accepted_filtered.jsonl`
- Exclusion audit: `excluded.jsonl`
- ID lists: `accepted_episode_ids.txt`, `excluded_episode_ids.txt`
- Machine-readable report: `FILTER_REPORT.json`
- Checksums: `SHA256SUMS`
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-root",
        default=str(DEFAULT_MANIFEST_ROOT),
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--destination",
        default=str(DEFAULT_DESTINATION),
    )
    parser.add_argument(
        "--camera-max-frame-step-deg",
        type=float,
        default=8.0,
    )
    parser.add_argument(
        "--fall-minimum-drop",
        type=float,
        default=128.0,
    )
    parser.add_argument(
        "--fall-minimum-ungrounded-ticks",
        type=int,
        default=24,
    )
    parser.add_argument(
        "--backward-command-threshold",
        type=float,
        default=1.0,
    )
    args = parser.parse_args()

    manifest_root = Path(args.manifest_root).resolve()
    output_root = Path(args.output_root).resolve()
    destination = Path(args.destination).resolve()
    if destination.exists():
        raise RuntimeError(f"destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.tmp.{os.getpid()}"
    )
    if temporary.exists():
        raise RuntimeError(f"temporary path already exists: {temporary}")
    temporary.mkdir()

    rules = {
        "backward_unintentional_fall_v1": {
            "scope": (
                "source_prototype physical trajectory; output ticks 64..383"
            ),
            "minimum_vertical_drop_units": args.fall_minimum_drop,
            "minimum_ungrounded_ticks": (
                args.fall_minimum_ungrounded_ticks
            ),
            "minimum_ungrounded_seconds": (
                args.fall_minimum_ungrounded_ticks / PHYSICS_HZ
            ),
            "backward_command_threshold": (
                args.backward_command_threshold
            ),
            "backward_onset_window_ticks": [-3, 3],
            "requires_no_jump_in_output_window": True,
        },
        "camera_single_frame_angular_jump_v1": {
            "scope": "per rendered episode",
            "maximum_frame_step_deg": (
                args.camera_max_frame_step_deg
            ),
            "comparison": "strictly_greater_than",
            "signals": [
                "actual.motion.yaw_max_frame_step_deg",
                "actual.motion.pitch_max_frame_step_deg",
            ],
            "pixel_heuristics_used": False,
        },
    }
    ruleset_sha256 = sha256_bytes(
        canonical_json(rules).encode("utf-8")
    )

    try:
        print("loading accepted universe", flush=True)
        accepted_ids, records, source_audit = load_accepted_universe(
            manifest_root,
            output_root,
        )
        sorted_accepted = sorted(accepted_ids)

        for episode_id in sorted_accepted:
            expected = output_root / "candidates" / episode_id
            observed = Path(str(records[episode_id]["episode_path"]))
            if observed.resolve() != expected.resolve():
                raise RuntimeError(
                    f"{episode_id}: unexpected episode_path {observed}"
                )
            if not expected.is_dir():
                raise RuntimeError(
                    f"{episode_id}: candidate directory missing"
                )

        print(
            f"accepted episodes={len(sorted_accepted)}; "
            "evaluating fall prototypes",
            flush=True,
        )
        high_vertical_prototypes: dict[str, str] = {}
        for episode_id in sorted_accepted:
            record = records[episode_id]
            if (
                numeric_metric(record, "vertical_range")
                < args.fall_minimum_drop
            ):
                continue
            prototype_id = str(record.get("source_prototype_id") or "")
            if not prototype_id:
                raise RuntimeError(
                    f"{episode_id}: missing source_prototype_id"
                )
            high_vertical_prototypes.setdefault(
                prototype_id,
                episode_id,
            )

        fall_evidence: dict[str, dict[str, Any]] = {}
        fall_prototypes: set[str] = set()
        for index, (prototype_id, episode_id) in enumerate(
            sorted(high_vertical_prototypes.items()),
            1,
        ):
            evidence = evaluate_backward_fall(
                output_root / "candidates" / episode_id,
                prototype_id,
                minimum_drop=args.fall_minimum_drop,
                minimum_ungrounded_ticks=(
                    args.fall_minimum_ungrounded_ticks
                ),
                backward_threshold=args.backward_command_threshold,
            )
            fall_evidence[prototype_id] = evidence
            if evidence["excluded"]:
                fall_prototypes.add(prototype_id)
            if index % 100 == 0:
                print(
                    f"fall prototypes evaluated={index}/"
                    f"{len(high_vertical_prototypes)}",
                    flush=True,
                )

        decisions: dict[str, dict[str, Any]] = {}
        kept_ids: list[str] = []
        excluded_ids: list[str] = []
        reason_counts: Counter[str] = Counter()
        multi_reason_count = 0
        for episode_id in sorted_accepted:
            record = records[episode_id]
            reasons: list[str] = []
            evidence: dict[str, Any] = {}
            prototype_id = str(record["source_prototype_id"])
            if prototype_id in fall_prototypes:
                reason = "backward_unintentional_fall_v1"
                reasons.append(reason)
                evidence[reason] = fall_evidence[prototype_id]

            yaw_step = numeric_metric(
                record,
                "yaw_max_frame_step_deg",
            )
            pitch_step = numeric_metric(
                record,
                "pitch_max_frame_step_deg",
            )
            if max(yaw_step, pitch_step) > (
                args.camera_max_frame_step_deg
            ):
                reason = "camera_single_frame_angular_jump_v1"
                reasons.append(reason)
                evidence[reason] = {
                    "yaw_max_frame_step_deg": yaw_step,
                    "pitch_max_frame_step_deg": pitch_step,
                    "maximum_allowed_frame_step_deg": (
                        args.camera_max_frame_step_deg
                    ),
                }

            if reasons:
                excluded_ids.append(episode_id)
                reason_counts.update(reasons)
                multi_reason_count += int(len(reasons) > 1)
                decisions[episode_id] = {
                    "decision": "exclude",
                    "reasons": reasons,
                    "evidence": evidence,
                }
            else:
                kept_ids.append(episode_id)
                decisions[episode_id] = {
                    "decision": "keep",
                    "reasons": [],
                }

        for episode_id, expected_reason in (
            (
                KNOWN_BACKWARD_FALL,
                "backward_unintentional_fall_v1",
            ),
            (
                KNOWN_CAMERA_JUMP,
                "camera_single_frame_angular_jump_v1",
            ),
        ):
            if episode_id not in accepted_ids:
                raise RuntimeError(
                    f"known regression episode not accepted: {episode_id}"
                )
            decision = decisions[episode_id]
            if (
                decision["decision"] != "exclude"
                or expected_reason not in decision["reasons"]
            ):
                raise RuntimeError(
                    f"regression screening failed for {episode_id}"
                )

        print(
            f"screened kept={len(kept_ids)} "
            f"excluded={len(excluded_ids)}",
            flush=True,
        )
        written_kept = write_jsonl(
            temporary / "accepted_filtered.jsonl",
            kept_ids,
            records,
            decisions,
            ruleset_sha256,
        )
        written_excluded = write_jsonl(
            temporary / "excluded.jsonl",
            excluded_ids,
            records,
            decisions,
            ruleset_sha256,
        )
        write_lines(
            temporary / "accepted_episode_ids.txt",
            kept_ids,
        )
        write_lines(
            temporary / "excluded_episode_ids.txt",
            excluded_ids,
        )
        if written_kept != len(kept_ids):
            raise RuntimeError("kept manifest write count mismatch")
        if written_excluded != len(excluded_ids):
            raise RuntimeError("excluded manifest write count mismatch")
        if set(kept_ids) & set(excluded_ids):
            raise RuntimeError("kept/excluded overlap")
        if set(kept_ids) | set(excluded_ids) != accepted_ids:
            raise RuntimeError("kept/excluded union mismatch")

        accepted_set_sha = sha256_bytes(
            ("\n".join(sorted_accepted) + "\n").encode("utf-8")
        )
        source_record_sha = sha256_bytes(
            (
                "\n".join(
                    (
                        f"{episode_id}\0"
                        f"{records[episode_id].get('package_sha256', '')}"
                    )
                    for episode_id in sorted_accepted
                )
                + "\n"
            ).encode("utf-8")
        )
        report = {
            "schema_version": (
                "xonotic-stage1-post-collection-filter-report-v1"
            ),
            "created_utc": utc_now(),
            "source": {
                **source_audit,
                "accepted_episode_set_sha256": accepted_set_sha,
                "accepted_record_identity_sha256": source_record_sha,
                "unfinished_tail_policy": (
                    "ignored_by_user_instruction_2026-07-30"
                ),
            },
            "rules": rules,
            "ruleset_sha256": ruleset_sha256,
            "counts": {
                "accepted_input": len(sorted_accepted),
                "kept": len(kept_ids),
                "excluded": len(excluded_ids),
                "excluded_by_reason": {
                    name: int(reason_counts.get(name, 0))
                    for name in rules
                },
                "multi_reason_excluded": multi_reason_count,
                "high_vertical_prototypes_evaluated": len(
                    high_vertical_prototypes
                ),
                "backward_fall_prototypes_excluded": len(
                    fall_prototypes
                ),
            },
            "known_regression_examples": {
                episode_id: decisions[episode_id]
                for episode_id in (
                    KNOWN_BACKWARD_FALL,
                    KNOWN_CAMERA_JUMP,
                )
            },
            "distribution": {
                "accepted_input": dimensions(
                    sorted_accepted,
                    records,
                ),
                "kept": dimensions(kept_ids, records),
                "excluded": dimensions(excluded_ids, records),
            },
            "artifacts": {
                "accepted_filtered": "accepted_filtered.jsonl",
                "excluded": "excluded.jsonl",
                "accepted_episode_ids": "accepted_episode_ids.txt",
                "excluded_episode_ids": "excluded_episode_ids.txt",
            },
            "integrity": {
                "unique_input_ids": (
                    len(sorted_accepted) == len(accepted_ids)
                ),
                "unique_kept_ids": (
                    len(kept_ids) == len(set(kept_ids))
                ),
                "unique_excluded_ids": (
                    len(excluded_ids) == len(set(excluded_ids))
                ),
                "kept_excluded_disjoint": not (
                    set(kept_ids) & set(excluded_ids)
                ),
                "kept_excluded_exact_union": (
                    set(kept_ids) | set(excluded_ids)
                    == accepted_ids
                ),
                "known_regressions_passed": True,
            },
        }
        report["artifacts"]["accepted_filtered_sha256"] = sha256_file(
            temporary / "accepted_filtered.jsonl"
        )
        report["artifacts"]["excluded_sha256"] = sha256_file(
            temporary / "excluded.jsonl"
        )
        (temporary / "FILTER_REPORT.json").write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (temporary / "README.md").write_text(
            report_markdown(report),
            encoding="utf-8",
        )
        artifact_names = (
            "accepted_filtered.jsonl",
            "excluded.jsonl",
            "accepted_episode_ids.txt",
            "excluded_episode_ids.txt",
            "FILTER_REPORT.json",
            "README.md",
        )
        (temporary / "SHA256SUMS").write_text(
            "".join(
                f"{sha256_file(temporary / name)}  {name}\n"
                for name in artifact_names
            ),
            encoding="utf-8",
        )
        os.rename(temporary, destination)
        print(f"destination={destination}", flush=True)
        print(
            f"manifest={destination / 'accepted_filtered.jsonl'}",
            flush=True,
        )
        print(
            f"report={destination / 'FILTER_REPORT.json'}",
            flush=True,
        )
        return 0
    except BaseException:
        if temporary.is_dir():
            shutil.rmtree(temporary)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
