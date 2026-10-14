                      
"""Materialize an audited Stage-1 v5 topology from a locked formal manifest.

Only ``assigned_shard`` and ``shard_count`` may change.  Episode IDs,
actions, certificates, semantic targets, and every other row field must stay
byte-equivalent under canonical JSON.  The source formal root is never
modified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_stage1_manifests as v4              
import prepare_stage1_v5_manifests as stage1              
import xonotic_capture as capture              


TOPOLOGY_ONLY_FIELDS = frozenset({"assigned_shard", "shard_count"})
ADDITIONAL_RUNTIME_LOCK_PATHS = (
    "scripts/reshard_stage1_v5_formal.py",
    "scripts/run_stage1_56x1_worker.sh",
    "scripts/submit_stage1_sensecore_56x1.sh",
    "scripts/print_stage1_56x1_commands.sh",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_once_or_verify_hash(path: Path, text: str) -> None:
    if path.exists():
        if (
            not path.is_file()
            or capture.sha256_file(path) != sha256_text(text)
        ):
            raise capture.CaptureFailure(
                "refuse_overwrite_v5_manifest_drift", str(path)
            )
        return
    stage1.write_once_or_verify(path, text)


def safe_relative(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError as exc:
        raise capture.CaptureFailure(
            "formal_topology_path_outside_workspace", str(path)
        ) from exc


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise capture.CaptureFailure(
            "formal_topology_artifact_missing", str(path)
        )
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise capture.CaptureFailure(
            "formal_topology_json_not_object", str(path)
        )
    return value


def parse_runtime_lock(path: Path) -> list[str]:
    if not path.is_file():
        raise capture.CaptureFailure(
            "formal_topology_runtime_lock_missing", str(path)
        )
    relative_paths: list[str] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        parts = line.split()
        if (
            len(parts) != 2
            or len(parts[0]) != 64
            or any(char not in "0123456789abcdef" for char in parts[0])
        ):
            raise capture.CaptureFailure(
                "formal_topology_runtime_lock_invalid",
                f"{path}:{line_number}",
            )
        digest, relative = parts
        relative_path = Path(relative)
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative in relative_paths
        ):
            raise capture.CaptureFailure(
                "formal_topology_runtime_lock_path_invalid", relative
            )
        artifact = capture.ROOT / relative_path
        if (
            not artifact.is_file()
            or capture.sha256_file(artifact) != digest
        ):
            raise capture.CaptureFailure(
                "formal_topology_runtime_lock_mismatch", relative
            )
        relative_paths.append(relative)
    if not relative_paths:
        raise capture.CaptureFailure(
            "formal_topology_runtime_lock_empty", str(path)
        )
    return relative_paths


def runtime_lock_text(source_paths: list[str]) -> str:
    paths = list(source_paths)
    for relative in ADDITIONAL_RUNTIME_LOCK_PATHS:
        if relative not in paths:
            paths.append(relative)
    rows = []
    for relative in paths:
        artifact = capture.ROOT / relative
        if not artifact.is_file():
            raise capture.CaptureFailure(
                "formal_topology_runtime_artifact_missing", relative
            )
        rows.append(f"{capture.sha256_file(artifact)}  {relative}\n")
    return "".join(rows)


def verify_source_formal(
    source_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    metadata_path = source_root / "MANIFEST_METADATA.json"
    audit_path = source_root / "MANIFEST_AUDIT.json"
    metadata = load_json(metadata_path)
    audit = load_json(audit_path)
    runtime = metadata.get("runtime_code_lock") or {}
    checks = {
        "schema": metadata.get("schema_version")
        == "xonotic-stage1-formal-manifest-v2",
        "source_commit": metadata.get("source_commit")
        == stage1.RUNTIME_SOURCE_COMMIT,
        "formal_authorized": metadata.get(
            "formal_collection_authorized"
        )
        is True,
        "not_training_admitted": metadata.get("training_admitted")
        is False,
        "source_shard_count": int(metadata.get("shard_count", -1))
        == 32,
        "audit_schema": audit.get("schema_version")
        == "xonotic-stage1-v5-formal-audit-v1",
        "audit_passed": audit.get("passed") is True,
        "metadata_sha256": audit.get("metadata_sha256")
        == capture.sha256_file(metadata_path),
        "primary_sha256": audit.get("primary_sha256")
        == (metadata.get("primary") or {}).get("sha256"),
        "replenishment_sha256": audit.get("replenishment_sha256")
        == (metadata.get("replenishment") or {}).get("sha256"),
        "runtime_lock_sha256": audit.get("runtime_code_lock_sha256")
        == runtime.get("sha256"),
    }
    if not all(checks.values()):
        raise capture.CaptureFailure(
            "formal_topology_source_audit_failed",
            capture.canonical_json(checks),
        )
    runtime_path = capture.ROOT / str(runtime.get("path", ""))
    if (
        not runtime_path.is_file()
        or capture.sha256_file(runtime_path) != runtime.get("sha256")
    ):
        raise capture.CaptureFailure(
            "formal_topology_source_runtime_lock_mismatch",
            str(runtime_path),
        )
    source_runtime_paths = parse_runtime_lock(runtime_path)
    if len(source_runtime_paths) != int(runtime.get("entries", -1)):
        raise capture.CaptureFailure(
            "formal_topology_source_runtime_lock_count",
            str(runtime_path),
        )
    for wave, filename, expected_rows in (
        ("primary", "input.jsonl", 60_000),
        ("replenishment", "replenishment.jsonl", 12_000),
    ):
        declared = metadata.get(wave) or {}
        path = source_root / filename
        declared_path = capture.ROOT / str(
            declared.get("path", "")
        )
        wave_checks = {
            "rows": int(declared.get("rows", -1))
            == expected_rows,
            "path": declared_path.resolve() == path.resolve(),
            "sha256": declared.get("sha256")
            == capture.sha256_file(path),
            "audit": declared.get("audit")
            == audit.get(wave),
            "shards": len(declared.get("shards") or []) == 32,
        }
        if not all(wave_checks.values()):
            raise capture.CaptureFailure(
                "formal_topology_source_wave_failed",
                capture.canonical_json(
                    {"wave": wave, "checks": wave_checks}
                ),
            )
    return metadata, audit, source_runtime_paths


def semantic_fingerprint(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        semantic = {
            key: value
            for key, value in row.items()
            if key not in TOPOLOGY_ONLY_FIELDS
        }
        digest.update(capture.canonical_json(semantic).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def episode_id_fingerprint(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(str(row["episode_id"]).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def reshard_rows(
    source_rows: list[dict[str, Any]],
    *,
    source_shard_count: int,
    target_shard_count: int,
    expected_rows: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(source_rows) != expected_rows:
        raise capture.CaptureFailure(
            "formal_topology_source_row_count",
            f"expected={expected_rows} actual={len(source_rows)}",
        )
    ordinals = [int(row.get("candidate_ordinal", -1)) for row in source_rows]
    episode_ids = [str(row.get("episode_id", "")) for row in source_rows]
    source_checks = {
        "ordinals": ordinals == list(range(1, expected_rows + 1)),
        "episode_ids": all(episode_ids)
        and len(episode_ids) == len(set(episode_ids)),
        "source_assignments": all(
            int(row.get("assigned_shard", -1))
            == (int(row["candidate_ordinal"]) - 1)
            % source_shard_count
            and int(row.get("shard_count", -1))
            == source_shard_count
            for row in source_rows
        ),
        "not_training_admitted": all(
            row.get("training_admitted") is False
            for row in source_rows
        ),
    }
    if not all(source_checks.values()):
        raise capture.CaptureFailure(
            "formal_topology_source_rows_invalid",
            capture.canonical_json(source_checks),
        )
    source_semantic_sha = semantic_fingerprint(source_rows)
    source_ids_sha = episode_id_fingerprint(source_rows)
    target_rows = source_rows
    for row in target_rows:
        ordinal = int(row["candidate_ordinal"])
        row["assigned_shard"] = (ordinal - 1) % target_shard_count
        row["shard_count"] = target_shard_count
    target_semantic_sha = semantic_fingerprint(target_rows)
    target_ids_sha = episode_id_fingerprint(target_rows)
    counts = Counter(
        int(row["assigned_shard"]) for row in target_rows
    )
    target_checks = {
        "semantic_payload_unchanged": (
            target_semantic_sha == source_semantic_sha
        ),
        "episode_order_and_ids_unchanged": (
            target_ids_sha == source_ids_sha
        ),
        "target_assignments": all(
            int(row["assigned_shard"])
            == (int(row["candidate_ordinal"]) - 1)
            % target_shard_count
            and int(row["shard_count"]) == target_shard_count
            for row in target_rows
        ),
        "all_target_shards_nonempty": set(counts)
        == set(range(target_shard_count)),
        "balanced": max(counts.values()) - min(counts.values()) <= 1,
    }
    if not all(target_checks.values()):
        raise capture.CaptureFailure(
            "formal_topology_target_rows_invalid",
            capture.canonical_json(target_checks),
        )
    return target_rows, {
        "source_semantic_sha256": source_semantic_sha,
        "target_semantic_sha256": target_semantic_sha,
        "source_episode_ids_sha256": source_ids_sha,
        "target_episode_ids_sha256": target_ids_sha,
        "shard_rows_min": min(counts.values()),
        "shard_rows_max": max(counts.values()),
        "shard_row_counts": {
            str(index): counts[index]
            for index in range(target_shard_count)
        },
        "checks": {**source_checks, **target_checks},
    }


def write_wave(
    *,
    target_root: Path,
    wave: str,
    filename: str,
    rows: list[dict[str, Any]],
    shard_count: int,
) -> tuple[str, list[dict[str, Any]]]:
    text = stage1.canonical_lines(rows)
    path = target_root / filename
    write_once_or_verify_hash(path, text)
    shards = []
    expected_names = set()
    for shard_index in range(shard_count):
        selected = [
            row
            for row in rows
            if int(row["assigned_shard"]) == shard_index
        ]
        name = f"shard-{shard_index:03d}-of-{shard_count:03d}.jsonl"
        expected_names.add(name)
        shard_path = target_root / "shards" / wave / name
        shard_text = stage1.canonical_lines(selected)
        write_once_or_verify_hash(shard_path, shard_text)
        shards.append(
            {
                "shard_index": shard_index,
                "rows": len(selected),
                "path": safe_relative(capture.ROOT, shard_path),
                "sha256": sha256_text(shard_text),
            }
        )
    actual_names = {
        path.name
        for path in (target_root / "shards" / wave).glob(
            "shard-*-of-*.jsonl"
        )
    }
    if actual_names != expected_names:
        raise capture.CaptureFailure(
            "formal_topology_unexpected_shard_files",
            capture.canonical_json(
                {
                    "wave": wave,
                    "expected": sorted(expected_names),
                    "actual": sorted(actual_names),
                }
            ),
        )
    return sha256_text(text), shards


def rerun_semantic_audit(
    *,
    rows: list[dict[str, Any]],
    wave: str,
    source_audit: dict[str, Any],
    shard_count: int,
) -> dict[str, Any]:
    original_shard_count = stage1.SHARD_COUNT
    try:
        stage1.SHARD_COUNT = shard_count
        audit = stage1.audit_formal_rows(
            rows,
            60_000 if wave == "primary" else 12_000,
            1 if wave == "primary" else v4.REPLENISHMENT_SCALE,
        )
    finally:
        stage1.SHARD_COUNT = original_shard_count
    audit["semantic_count_allocation"] = copy.deepcopy(
        source_audit["semantic_count_allocation"]
    )
    normalized_audit = json.loads(
        json.dumps(audit, sort_keys=True, ensure_ascii=False)
    )
    normalized_source = json.loads(
        json.dumps(source_audit, sort_keys=True, ensure_ascii=False)
    )
    if normalized_audit != normalized_source:
        changed = sorted(
            key
            for key in set(normalized_audit) | set(normalized_source)
            if normalized_audit.get(key) != normalized_source.get(key)
        )
        raise capture.CaptureFailure(
            "formal_topology_semantic_audit_drift",
            capture.canonical_json(
                {"wave": wave, "changed_top_level_keys": changed}
            ),
        )
    return normalized_audit


def materialize(
    *,
    source_root: Path,
    target_root: Path,
    target_shard_count: int,
) -> dict[str, Any]:
    if target_shard_count <= 0:
        raise capture.CaptureFailure(
            "formal_topology_invalid_shard_count",
            str(target_shard_count),
        )
    if source_root.resolve() == target_root.resolve():
        raise capture.CaptureFailure(
            "formal_topology_refuse_in_place", str(source_root)
        )
    safe_relative(capture.ROOT, source_root)
    safe_relative(capture.ROOT, target_root)
    source_metadata, source_audit, source_runtime_paths = (
        verify_source_formal(source_root)
    )
    created_utc = stage1.created_utc_for(
        target_root / "MANIFEST_METADATA.json"
    )
    wave_results: dict[str, dict[str, Any]] = {}
    for wave, filename, expected_rows in (
        ("primary", "input.jsonl", 60_000),
        ("replenishment", "replenishment.jsonl", 12_000),
    ):
        source_rows = capture.load_jsonl(source_root / filename)
        target_rows, equivalence = reshard_rows(
            source_rows,
            source_shard_count=int(source_metadata["shard_count"]),
            target_shard_count=target_shard_count,
            expected_rows=expected_rows,
        )
        semantic_audit = rerun_semantic_audit(
            rows=target_rows,
            wave=wave,
            source_audit=source_metadata[wave]["audit"],
            shard_count=target_shard_count,
        )
        target_sha, shards = write_wave(
            target_root=target_root,
            wave=wave,
            filename=filename,
            rows=target_rows,
            shard_count=target_shard_count,
        )
        wave_results[wave] = {
            "filename": filename,
            "rows": expected_rows,
            "source_sha256": source_metadata[wave]["sha256"],
            "target_sha256": target_sha,
            "semantic_audit": semantic_audit,
            "shards": shards,
            "equivalence": equivalence,
        }
    runtime_text = runtime_lock_text(source_runtime_paths)
    runtime_path = target_root / "RUNTIME_CODE_LOCK.sha256"
    write_once_or_verify_hash(runtime_path, runtime_text)
    runtime_sha = sha256_text(runtime_text)
    topology_audit_path = target_root / "TOPOLOGY_RESHARD_AUDIT.json"
    topology_audit = {
        "schema_version": "xonotic-stage1-formal-topology-reshard-v1",
        "created_utc": stage1.created_utc_for(topology_audit_path),
        "pass": True,
        "training_admitted": False,
        "source_root": str(source_root),
        "source_metadata_sha256": capture.sha256_file(
            source_root / "MANIFEST_METADATA.json"
        ),
        "source_audit_sha256": capture.sha256_file(
            source_root / "MANIFEST_AUDIT.json"
        ),
        "source_runtime_lock_sha256": source_metadata[
            "runtime_code_lock"
        ]["sha256"],
        "source_shard_count": int(source_metadata["shard_count"]),
        "target_root": str(target_root),
        "target_shard_count": target_shard_count,
        "topology_only_fields": sorted(TOPOLOGY_ONLY_FIELDS),
        "runtime_code_lock": {
            "path": safe_relative(capture.ROOT, runtime_path),
            "sha256": runtime_sha,
            "entries": len(runtime_text.splitlines()),
        },
        "waves": {
            wave: {
                "rows": result["rows"],
                "source_sha256": result["source_sha256"],
                "target_sha256": result["target_sha256"],
                "equivalence": result["equivalence"],
                "semantic_audit_checks": result[
                    "semantic_audit"
                ]["checks"],
            }
            for wave, result in wave_results.items()
        },
        "checks": {
            "source_formal_audit_passed": True,
            "source_runtime_lock_verified": True,
            "only_topology_fields_changed": all(
                result["equivalence"]["checks"][
                    "semantic_payload_unchanged"
                ]
                for result in wave_results.values()
            ),
            "episode_order_and_ids_unchanged": all(
                result["equivalence"]["checks"][
                    "episode_order_and_ids_unchanged"
                ]
                for result in wave_results.values()
            ),
            "all_semantic_audits_passed": all(
                all(result["semantic_audit"]["checks"].values())
                for result in wave_results.values()
            ),
            "all_shards_balanced": all(
                result["equivalence"]["checks"]["balanced"]
                for result in wave_results.values()
            ),
            "runtime_code_lock_extended": (
                len(runtime_text.splitlines())
                == len(source_runtime_paths)
                + len(
                    [
                        path
                        for path in ADDITIONAL_RUNTIME_LOCK_PATHS
                        if path not in source_runtime_paths
                    ]
                )
            ),
        },
    }
    if not all(topology_audit["checks"].values()):
        raise capture.CaptureFailure(
            "formal_topology_audit_failed",
            capture.canonical_json(topology_audit["checks"]),
        )
    topology_text = (
        json.dumps(
            topology_audit,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    write_once_or_verify_hash(topology_audit_path, topology_text)
    topology_sha = sha256_text(topology_text)
    metadata = copy.deepcopy(source_metadata)
    metadata.update(
        {
            "created_utc": created_utc,
            "shard_count": target_shard_count,
            "shard_method": (
                "canonical formal ordinal round-robin: "
                f"(candidate_ordinal - 1) mod {target_shard_count}"
            ),
            "topology": (
                f"{target_shard_count} independent one-GPU workers"
            ),
            "runtime_code_lock": {
                "path": safe_relative(capture.ROOT, runtime_path),
                "sha256": runtime_sha,
                "entries": len(runtime_text.splitlines()),
            },
            "topology_reshard": {
                "path": safe_relative(
                    capture.ROOT, topology_audit_path
                ),
                "sha256": topology_sha,
                "source_root": safe_relative(
                    capture.ROOT, source_root
                ),
                "source_shard_count": int(
                    source_metadata["shard_count"]
                ),
                "target_shard_count": target_shard_count,
                "policy": (
                    "assigned_shard and shard_count only; all semantic "
                    "payload, episode IDs, actions, and certificates "
                    "must remain canonical-byte-equivalent"
                ),
            },
        }
    )
    for wave, result in wave_results.items():
        target_filename = result["filename"]
        metadata[wave].update(
            {
                "rows": result["rows"],
                "path": safe_relative(
                    capture.ROOT, target_root / target_filename
                ),
                "sha256": result["target_sha256"],
                "shards": result["shards"],
                "audit": result["semantic_audit"],
            }
        )
    metadata_path = target_root / "MANIFEST_METADATA.json"
    metadata_text = (
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    write_once_or_verify_hash(metadata_path, metadata_text)
    formal_audit_path = target_root / "MANIFEST_AUDIT.json"
    formal_audit = {
        "schema_version": "xonotic-stage1-v5-formal-audit-v1",
        "created_utc": stage1.created_utc_for(formal_audit_path),
        "passed": True,
        "primary": wave_results["primary"]["semantic_audit"],
        "replenishment": wave_results[
            "replenishment"
        ]["semantic_audit"],
        "metadata_sha256": sha256_text(metadata_text),
        "primary_sha256": wave_results["primary"]["target_sha256"],
        "replenishment_sha256": wave_results[
            "replenishment"
        ]["target_sha256"],
        "runtime_code_lock_sha256": runtime_sha,
        "topology_reshard_sha256": topology_sha,
    }
    formal_audit_text = (
        json.dumps(
            formal_audit,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    write_once_or_verify_hash(formal_audit_path, formal_audit_text)
                                                                         
    if (
        capture.sha256_file(metadata_path)
        != formal_audit["metadata_sha256"]
        or capture.sha256_file(runtime_path)
        != formal_audit["runtime_code_lock_sha256"]
        or capture.sha256_file(topology_audit_path)
        != formal_audit["topology_reshard_sha256"]
    ):
        raise capture.CaptureFailure(
            "formal_topology_final_hash_mismatch", str(target_root)
        )
    return {
        "pass": True,
        "training_admitted": False,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "source_shard_count": int(source_metadata["shard_count"]),
        "target_shard_count": target_shard_count,
        "primary_rows": wave_results["primary"]["rows"],
        "replenishment_rows": wave_results["replenishment"]["rows"],
        "primary_sha256": wave_results["primary"]["target_sha256"],
        "replenishment_sha256": wave_results[
            "replenishment"
        ]["target_sha256"],
        "metadata_sha256": formal_audit["metadata_sha256"],
        "manifest_audit_sha256": sha256_text(formal_audit_text),
        "runtime_code_lock_sha256": runtime_sha,
        "topology_reshard_sha256": topology_sha,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--source-root",
        default=str(
            capture.ROOT / "manifests/stage1_foundation_v5_formal"
        ),
    )
    result.add_argument(
        "--target-root",
        default=str(
            capture.ROOT
            / "manifests/stage1_foundation_v5_formal_56x1"
        ),
    )
    result.add_argument("--target-shard-count", type=int, default=56)
    return result


def main() -> int:
    args = parser().parse_args()
    capture.require_conda()
    try:
        output = materialize(
            source_root=Path(args.source_root).resolve(),
            target_root=Path(args.target_root).resolve(),
            target_shard_count=args.target_shard_count,
        )
    except capture.CaptureFailure as exc:
        print(
            f"FATAL reason={exc.reason} detail={exc.detail}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
