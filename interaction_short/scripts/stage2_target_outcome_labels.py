                      
"""Build and apply a fail-closed Stage-2 target-outcome label overlay."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


CURRENT_POINTER = "LABEL_CORRECTION_CURRENT.json"
LABEL_SCHEMA = "xonotic-stage2-target-outcome-label-v1"
POINTER_SCHEMA = "xonotic-stage2-label-correction-pointer-v1"
AUDIT_SCHEMA = "xonotic-stage2-target-outcome-correction-audit-v1"
ALLOWED_OUTCOMES = {"no_fire", "miss", "hit_survive", "kill"}
REQUIRED_SHOT_COLUMNS = {
    "fire_event_id",
    "target_entity",
    "target_hit",
    "target_killed",
    "target_outcome",
    "target_observation_complete",
    "right_censored",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"invalid JSONL at {path}:{line_number}: {exc}"
                    ) from exc
    return rows


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def target_outcome_from_flags(
    target_hit: pd.Series, target_killed: pd.Series
) -> str:
    if len(target_hit) == 0:
        return "no_fire"
    if target_killed.astype(bool).any():
        return "kill"
    if target_hit.astype(bool).any():
        return "hit_survive"
    return "miss"


def global_outcome_from_counts(counts: dict[str, Any]) -> str:
    if int(counts.get("fire_count", 0)) == 0:
        return "no_fire"
    if int(counts.get("death_count", 0)) > 0:
        return "kill"
    if int(counts.get("damage_count", 0)) > 0:
        return "hit_survive"
    return "miss"


def current_pointer(output_root: Path) -> dict[str, Any] | None:
    path = output_root / CURRENT_POINTER
    if not path.is_file():
        return None
    pointer = json.loads(path.read_text(encoding="utf-8"))
    if pointer.get("schema_version") != POINTER_SCHEMA:
        raise RuntimeError(f"unsupported label correction pointer: {path}")
    if pointer.get("required_for_downstream") is not True:
        raise RuntimeError(f"non-authoritative label correction pointer: {path}")
    return pointer


def load_current_labels(output_root: Path) -> dict[str, dict[str, Any]]:
    pointer = current_pointer(output_root)
    if pointer is None:
        return {}
    labels_meta = pointer.get("labels") or {}
    labels_path = output_root / str(labels_meta.get("path", ""))
    expected_sha256 = str(labels_meta.get("sha256", ""))
    if not labels_path.is_file():
        raise RuntimeError(f"label overlay missing: {labels_path}")
    actual_sha256 = sha256_file(labels_path)
    if not expected_sha256 or actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"label overlay hash mismatch: {labels_path}: "
            f"{actual_sha256} != {expected_sha256}"
        )
    rows = load_jsonl(labels_path)
    if len(rows) != int(labels_meta.get("rows", -1)):
        raise RuntimeError(
            f"label overlay row-count mismatch: {len(rows)} != "
            f"{labels_meta.get('rows')}"
        )
    labels: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("schema_version") != LABEL_SCHEMA:
            raise RuntimeError(
                f"unsupported label row schema for {row.get('episode_id')}"
            )
        episode_id = str(row["episode_id"])
        if episode_id in labels:
            raise RuntimeError(f"duplicate label row: {episode_id}")
        labels[episode_id] = row
    return labels


def apply_current_labels(
    output_root: Path, accepted_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply the current complete overlay without rewriting source journals."""
    labels = load_current_labels(output_root)
    if not labels:
        return accepted_rows
    accepted_ids = {str(row["episode_id"]) for row in accepted_rows}
    if accepted_ids != set(labels):
        missing = sorted(accepted_ids - set(labels))[:20]
        extra = sorted(set(labels) - accepted_ids)[:20]
        raise RuntimeError(
            "label overlay does not exactly cover accepted snapshot: "
            f"missing={missing}, extra={extra}"
        )
    corrected_rows: list[dict[str, Any]] = []
    for source in accepted_rows:
        episode_id = str(source["episode_id"])
        label = labels[episode_id]
        source_causal = source.get("stage2_causal") or {}
        source_outcome = str(source_causal.get("actual_outcome"))
        if source_outcome != label["source_actual_outcome"]:
            raise RuntimeError(
                f"source outcome drift for {episode_id}: "
                f"{source_outcome} != {label['source_actual_outcome']}"
            )
        source_shot_hash = (source.get("package_sha256") or {}).get(
            "shot_outcomes.parquet"
        )
        if source_shot_hash != label["source_package_sha256"][
            "shot_outcomes.parquet"
        ]:
            raise RuntimeError(f"source package drift for {episode_id}")
        corrected = copy.deepcopy(source)
        causal = corrected.setdefault("stage2_causal", {})
        causal["actual_outcome"] = label["corrected_actual_outcome"]
        causal["actual_outcome_source"] = (
            "declared_target_shot_outcomes"
        )
        causal["global_event_outcome"] = label["global_event_outcome"]
        causal.setdefault("per_shot", {})["target_kill_count"] = label[
            "target_kill_count"
        ]
        corrected["episode_path"] = str(
            output_root / label["episode_relative_path"]
        )
        corrected["source_episode_path"] = source.get("episode_path")
        corrected["label_correction"] = {
            "schema_version": LABEL_SCHEMA,
            "correction_id": label["correction_id"],
            "changed": label["changed"],
            "source_actual_outcome": label["source_actual_outcome"],
            "corrected_actual_outcome": label[
                "corrected_actual_outcome"
            ],
        }
        corrected_rows.append(corrected)
    return corrected_rows


def load_accepted_snapshot(
    output_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    journals: list[dict[str, Any]] = []
    paths = sorted(
        (output_root / "manifests/shards").glob(
            "shard-*-of-*/accepted.jsonl"
        )
    )
    if not paths:
        raise RuntimeError(f"no accepted journals under {output_root}")
    seen: set[str] = set()
    for path in paths:
        journal_rows = load_jsonl(path)
        relative = str(path.relative_to(output_root))
        journals.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "rows": len(journal_rows),
            }
        )
        for line_number, row in enumerate(journal_rows, start=1):
            episode_id = str(row["episode_id"])
            if episode_id in seen:
                raise RuntimeError(f"duplicate accepted episode: {episode_id}")
            seen.add(episode_id)
            causal = row.get("stage2_causal") or {}
            records.append(
                {
                    "episode_id": episode_id,
                    "source_journal": relative,
                    "source_journal_line": line_number,
                    "source_episode_path": row.get("episode_path"),
                    "weapon": row.get("weapon"),
                    "map": row.get("map"),
                    "gametype": row.get("gametype"),
                    "package_sha256": row.get("package_sha256") or {},
                    "source_causal": {
                        "schema_version": causal.get("schema_version"),
                        "actual_outcome": causal.get("actual_outcome"),
                        "event_counts": causal.get("event_counts") or {},
                        "per_shot": causal.get("per_shot") or {},
                    },
                }
            )
    return sorted(records, key=lambda row: row["episode_id"]), journals


def inspect_record(
    output_root: Path, correction_id: str, record: dict[str, Any]
) -> dict[str, Any]:
    episode_id = record["episode_id"]
    package = output_root / "episodes" / episode_id
    shots_path = package / "shot_outcomes.parquet"
    causal_path = package / "causal_interaction.json"
    expected_hashes = record["package_sha256"]
    if not shots_path.is_file() or not causal_path.is_file():
        raise RuntimeError(f"package incomplete for {episode_id}: {package}")
    actual_hashes = {
        "shot_outcomes.parquet": sha256_file(shots_path),
        "causal_interaction.json": sha256_file(causal_path),
    }
    for name, digest in actual_hashes.items():
        if expected_hashes.get(name) != digest:
            raise RuntimeError(
                f"source package hash mismatch for {episode_id}/{name}"
            )
    causal = json.loads(causal_path.read_text(encoding="utf-8"))
    source_causal = record["source_causal"]
    if causal.get("schema_version") != "xonotic-stage2-causal-qa-v9":
        raise RuntimeError(f"non-V9 episode in snapshot: {episode_id}")
    source_outcome = str(source_causal.get("actual_outcome"))
    if source_outcome not in ALLOWED_OUTCOMES:
        raise RuntimeError(f"invalid source outcome for {episode_id}")
    if causal.get("actual_outcome") != source_outcome:
        raise RuntimeError(f"journal/package outcome drift for {episode_id}")
    global_outcome = global_outcome_from_counts(
        source_causal["event_counts"]
    )
    if global_outcome != source_outcome:
        raise RuntimeError(f"source outcome provenance drift for {episode_id}")

    shots = pd.read_parquet(shots_path)
    missing = REQUIRED_SHOT_COLUMNS - set(shots.columns)
    if missing:
        raise RuntimeError(
            f"shot label columns missing for {episode_id}: {sorted(missing)}"
        )
    if shots[list(REQUIRED_SHOT_COLUMNS)].isnull().any().any():
        raise RuntimeError(f"null target labels for {episode_id}")
    if not shots["fire_event_id"].is_unique:
        raise RuntimeError(f"duplicate fire IDs for {episode_id}")
    target_hit = shots["target_hit"].astype(bool)
    target_killed = shots["target_killed"].astype(bool)
    if (target_killed & ~target_hit).any():
        raise RuntimeError(f"target kill without target hit for {episode_id}")
    expected_per_shot = pd.Series(
        [
            "kill" if killed else "hit" if hit else "miss"
            for hit, killed in zip(target_hit, target_killed)
        ],
        index=shots.index,
        dtype="object",
    )
    if not shots["target_outcome"].astype(str).equals(expected_per_shot):
        raise RuntimeError(f"inconsistent target outcome for {episode_id}")
    if not shots["target_observation_complete"].astype(bool).all():
        raise RuntimeError(f"incomplete target observation for {episode_id}")
    if shots["right_censored"].astype(bool).any():
        raise RuntimeError(f"right-censored target outcome for {episode_id}")

    per_shot = source_causal["per_shot"]
    target_hit_count = int(target_hit.sum())
    target_kill_count = int(target_killed.sum())
    target_miss_count = int((~target_hit).sum())
    if len(shots) != int(per_shot.get("rows", -1)):
        raise RuntimeError(f"shot row count drift for {episode_id}")
    if target_hit_count != int(per_shot.get("target_hit_count", -1)):
        raise RuntimeError(f"target hit count drift for {episode_id}")
    if target_miss_count != int(per_shot.get("target_miss_count", -1)):
        raise RuntimeError(f"target miss count drift for {episode_id}")
    entities = sorted(
        {int(value) for value in shots["target_entity"].tolist()}
    )
    declared_entity = int(per_shot.get("target_entity", -1))
    if entities and entities != [declared_entity]:
        raise RuntimeError(f"target entity drift for {episode_id}")

    corrected_outcome = target_outcome_from_flags(
        target_hit, target_killed
    )
    return {
        "schema_version": LABEL_SCHEMA,
        "correction_id": correction_id,
        "episode_id": episode_id,
        "episode_relative_path": f"episodes/{episode_id}",
        "source_journal": record["source_journal"],
        "source_journal_line": record["source_journal_line"],
        "source_episode_path": record["source_episode_path"],
        "source_package_sha256": actual_hashes,
        "weapon": record["weapon"],
        "map": record["map"],
        "gametype": record["gametype"],
        "target_entity": declared_entity,
        "fire_count": len(shots),
        "target_hit_count": target_hit_count,
        "target_kill_count": target_kill_count,
        "target_miss_count": target_miss_count,
        "target_observation_complete": True,
        "right_censored": False,
        "global_event_outcome": global_outcome,
        "source_actual_outcome": source_outcome,
        "corrected_actual_outcome": corrected_outcome,
        "actual_outcome_source": "declared_target_shot_outcomes",
        "changed": source_outcome != corrected_outcome,
        "correction_reason": (
            "global_event_counts_included_non_target_damage_or_death"
            if source_outcome != corrected_outcome
            else None
        ),
        "training_admitted": False,
    }


def distribution(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def build_overlay(
    output_root: Path,
    correction_id: str,
    workers: int,
    expected_accepted: int | None,
    expected_changed: int | None,
) -> dict[str, Any]:
    records, journals = load_accepted_snapshot(output_root)
    if expected_accepted is not None and len(records) != expected_accepted:
        raise RuntimeError(
            f"accepted snapshot mismatch: {len(records)} != {expected_accepted}"
        )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        labels = list(
            executor.map(
                lambda record: inspect_record(
                    output_root, correction_id, record
                ),
                records,
            )
        )
    labels.sort(key=lambda row: row["episode_id"])
    changed = [row for row in labels if row["changed"]]
    if expected_changed is not None and len(changed) != expected_changed:
        raise RuntimeError(
            f"changed-label mismatch: {len(changed)} != {expected_changed}"
        )

    correction_parent = output_root / "label-corrections"
    final_root = correction_parent / correction_id
    if final_root.exists():
        raise RuntimeError(f"correction output already exists: {final_root}")
    correction_parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{correction_id}.tmp.", dir=correction_parent
        )
    )
    created_utc = utc_now()
    try:
        labels_path = temporary / "labels.jsonl"
        mismatches_path = temporary / "mismatches.jsonl"
        write_jsonl(labels_path, labels)
        write_jsonl(mismatches_path, changed)
        transitions: defaultdict[str, Counter[str]] = defaultdict(Counter)
        weapon_changes: Counter[str] = Counter()
        for row in changed:
            transitions[row["source_actual_outcome"]][
                row["corrected_actual_outcome"]
            ] += 1
            weapon_changes[str(row["weapon"])] += 1
        snapshot_digest = hashlib.sha256()
        for row in labels:
            snapshot_digest.update(
                (
                    row["episode_id"]
                    + "\0"
                    + row["source_package_sha256"][
                        "shot_outcomes.parquet"
                    ]
                    + "\n"
                ).encode("utf-8")
            )
        audit = {
            "schema_version": AUDIT_SCHEMA,
            "created_utc": created_utc,
            "correction_id": correction_id,
            "output_root": str(output_root),
            "source": {
                "accepted_journals": journals,
                "accepted_snapshot_sha256": snapshot_digest.hexdigest(),
                "accepted_rows": len(labels),
                "duplicate_episode_ids": [],
                "episode_schema": "xonotic-stage2-causal-qa-v9",
            },
            "contract": {
                "episode_actual_outcome": (
                    "kill if any declared-target shot killed; otherwise "
                    "hit_survive if any declared-target shot hit; otherwise "
                    "miss; empty shot table means no_fire"
                ),
                "source_fields": ["target_hit", "target_killed"],
                "source_artifact": "shot_outcomes.parquet",
                "global_event_outcome_is_diagnostic_only": True,
                "source_packages_modified": False,
                "source_journals_modified": False,
                "training_admitted": False,
            },
            "integrity": {
                "shot_outcomes_sha256_verified": len(labels),
                "causal_interaction_sha256_verified": len(labels),
                "target_observation_complete": len(labels),
                "right_censored": 0,
                "per_shot_labels_exact": len(labels),
                "complete_overlay": True,
            },
            "labels": {
                "rows": len(labels),
                "changed": len(changed),
                "unchanged": len(labels) - len(changed),
                "changed_fraction": len(changed) / len(labels),
                "source_distribution": distribution(
                    labels, "source_actual_outcome"
                ),
                "corrected_distribution": distribution(
                    labels, "corrected_actual_outcome"
                ),
                "transitions": {
                    source: dict(sorted(targets.items()))
                    for source, targets in sorted(transitions.items())
                },
                "changed_by_weapon": dict(sorted(weapon_changes.items())),
            },
            "outputs": {
                "labels": {
                    "path": "labels.jsonl",
                    "rows": len(labels),
                    "sha256": sha256_file(labels_path),
                },
                "mismatches": {
                    "path": "mismatches.jsonl",
                    "rows": len(changed),
                    "sha256": sha256_file(mismatches_path),
                },
            },
            "passed": True,
        }
        audit_path = temporary / "AUDIT.json"
        audit_path.write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        readme_path = temporary / "README.md"
        readme_path.write_text(
            "# Stage-2 target-outcome correction\n\n"
            f"Correction ID: `{correction_id}`\n\n"
            f"This complete overlay covers {len(labels):,} accepted V9 "
            f"episodes and changes {len(changed):,} episode-level labels. "
            "It derives `actual_outcome` only from the declared enemy's "
            "per-shot `target_hit` and `target_killed` fields.\n\n"
            "The source episode packages and accepted journals are immutable "
            "and were not modified. Consumers must apply `labels.jsonl` by "
            "`episode_id`; `LABEL_CORRECTION_CURRENT.json` at the output root "
            "is the authoritative pointer. `training_admitted` remains false.\n",
            encoding="utf-8",
        )
        checksum_names = (
            "labels.jsonl",
            "mismatches.jsonl",
            "AUDIT.json",
            "README.md",
        )
        (temporary / "SHA256SUMS").write_text(
            "".join(
                f"{sha256_file(temporary / name)}  {name}\n"
                for name in checksum_names
            ),
            encoding="utf-8",
        )
        os.replace(temporary, final_root)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise

    relative_root = final_root.relative_to(output_root)
    pointer = {
        "schema_version": POINTER_SCHEMA,
        "created_utc": created_utc,
        "correction_id": correction_id,
        "required_for_downstream": True,
        "complete_accepted_snapshot": True,
        "training_admitted": False,
        "labels": {
            "path": str(relative_root / "labels.jsonl"),
            "rows": len(labels),
            "sha256": sha256_file(final_root / "labels.jsonl"),
        },
        "mismatches": {
            "path": str(relative_root / "mismatches.jsonl"),
            "rows": len(changed),
            "sha256": sha256_file(final_root / "mismatches.jsonl"),
        },
        "audit": {
            "path": str(relative_root / "AUDIT.json"),
            "sha256": sha256_file(final_root / "AUDIT.json"),
        },
    }
    atomic_json(output_root / CURRENT_POINTER, pointer)
    return pointer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--correction-id", default="target-outcome-v1-20260803"
    )
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--expected-accepted", type=int)
    parser.add_argument("--expected-changed", type=int)
    args = parser.parse_args()
    if args.workers <= 0:
        raise RuntimeError("workers must be positive")
    pointer = build_overlay(
        args.output_root.resolve(),
        args.correction_id,
        args.workers,
        args.expected_accepted,
        args.expected_changed,
    )
    print(canonical_json(pointer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
