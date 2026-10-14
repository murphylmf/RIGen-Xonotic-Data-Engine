                      
"""Create frozen non-training representative and 32-way canary manifests."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


ROOT = capture.ROOT
CANARY_SPLIT = "h200_pipeline_canary"
CANARY_COUNT = 256
CANARY_SHARDS = 32
SOURCE_FILES = (
    ROOT / "configs/v2_coverage_pilot_scenarios.jsonl",
    ROOT / "configs/v2_stage1_enemy_policy_audio_preflight_v2_scenarios.jsonl",
)
TEMPLATES = (
    ("dm_no_enemy", "v2_foundation_solo_01"),
    ("dm_enemy", "v2_foundation_enemy_01"),
    ("dm_enemy_shooting", "v2_causal_02"),
    ("ctf_enemy", "s1polaudfix_002"),
    ("race_enemy", "s1polaudfix_001"),
)
CTF_SUPPLEMENT_TEMPLATES = (
    ("ctf_enemy_alternative_a", "s1polaudfix_003"),
    ("ctf_enemy_alternative_b", "s1polaudfix_004"),
)
FINAL_TEMPLATES = (
    ("dm_no_enemy", "v2_foundation_solo_01"),
    ("dm_enemy", "v2_foundation_enemy_01"),
    ("dm_enemy_shooting", "v2_causal_02"),
    ("ctf_enemy", "s1polaudfix_003"),
    ("race_enemy", "s1polaudfix_001"),
)


def canonical_lines(rows: list[dict[str, Any]]) -> str:
    return "".join(capture.canonical_json(row) + "\n" for row in rows)


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_once_or_verify(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        observed = path.read_text(encoding="utf-8")
        if observed != text:
            raise capture.CaptureFailure(
                "refuse_overwrite_manifest_drift", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(temporary, path)


def load_templates() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in SOURCE_FILES:
        for row in capture.load_jsonl(path):
            rows[row["episode_id"]] = row
    missing = [
        episode_id
        for _, episode_id in (
            TEMPLATES + CTF_SUPPLEMENT_TEMPLATES + FINAL_TEMPLATES
        )
        if episode_id not in rows
    ]
    if missing:
        raise capture.CaptureFailure(
            "canary_source_missing", ",".join(missing)
        )
    return rows


def clone_template(
    source: dict[str, Any],
    episode_id: str,
    role: str,
    assigned_shard: int,
    shard_count: int,
    ordinal: int,
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    old_id = row["episode_id"]
    row.update(
        {
            "episode_id": episode_id,
            "source_episode_id": old_id,
            "source_split": row["split"],
            "split": CANARY_SPLIT,
            "training_stage": "pipeline_canary_only",
            "acceptance_policy": capture.TIERED_REVIEW_POLICY,
            "formal_collection_authorized": False,
            "human_review_required_before_training": True,
            "training_admitted": False,
            "canary_role": role,
            "canary_ordinal": ordinal,
            "assigned_shard": assigned_shard,
            "shard_count": shard_count,
        }
    )
    row["anchor_id"] = str(row["anchor_id"]).replace(old_id, episode_id)
    return row


def representative_rows(
    templates: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        clone_template(
            templates[source_id],
            f"h200rep_{ordinal:03d}",
            role,
            0,
            1,
            ordinal,
        )
        for ordinal, (role, source_id) in enumerate(TEMPLATES, 1)
    ]


def canary_rows(
    templates: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ordinal in range(1, CANARY_COUNT + 1):
        role, source_id = TEMPLATES[(ordinal - 1) % len(TEMPLATES)]
        rows.append(
            clone_template(
                templates[source_id],
                f"h200canary_{ordinal:04d}",
                role,
                (ordinal - 1) % CANARY_SHARDS,
                CANARY_SHARDS,
                ordinal,
            )
        )
    return rows


def materialize() -> dict[str, Any]:
    templates = load_templates()
    representative = representative_rows(templates)
    canary = canary_rows(templates)

    representative_path = (
        ROOT / "manifests/h200_representative/input.jsonl"
    )
    canary_root = ROOT / "manifests/h200_pipeline_canary"
    canary_path = canary_root / "input.jsonl"
    representative_text = canonical_lines(representative)
    canary_text = canonical_lines(canary)
    write_once_or_verify(representative_path, representative_text)
    write_once_or_verify(canary_path, canary_text)
    supplement = [
        clone_template(
            templates[source_id],
            f"h200ctf_{ordinal:03d}",
            role,
            0,
            1,
            ordinal,
        )
        for ordinal, (role, source_id) in enumerate(
            CTF_SUPPLEMENT_TEMPLATES, 1
        )
    ]
    supplement_path = (
        ROOT / "manifests/h200_representative_ctf_supplement/input.jsonl"
    )
    supplement_text = canonical_lines(supplement)
    write_once_or_verify(supplement_path, supplement_text)
    write_once_or_verify(
        ROOT
        / "manifests/h200_representative_ctf_supplement/MANIFEST_METADATA.json",
        json.dumps(
            {
                "schema_version": "xonotic-h200-ctf-supplement-manifest-v1",
                "source_commit": (
                    capture.build_root() / "SOURCE_COMMIT"
                ).read_text(encoding="utf-8").strip(),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "path": str(supplement_path),
                "rows": len(supplement),
                "sha256": digest_text(supplement_text),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    final_rows = [
        clone_template(
            templates[source_id],
            f"h200final_{ordinal:03d}",
            role,
            0,
            1,
            ordinal,
        )
        for ordinal, (role, source_id) in enumerate(FINAL_TEMPLATES, 1)
    ]
    final_root = ROOT / "manifests/h200_representative_final"
    final_path = final_root / "input.jsonl"
    final_text = canonical_lines(final_rows)
    write_once_or_verify(final_path, final_text)
    write_once_or_verify(
        final_root / "MANIFEST_METADATA.json",
        json.dumps(
            {
                "schema_version": "xonotic-h200-final-representative-v1",
                "source_commit": (
                    capture.build_root() / "SOURCE_COMMIT"
                ).read_text(encoding="utf-8").strip(),
                "formal_collection_authorized": False,
                "training_admitted": False,
                "path": str(final_path),
                "rows": len(final_rows),
                "sha256": digest_text(final_text),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    canary_v2: list[dict[str, Any]] = []
    for ordinal in range(1, CANARY_COUNT + 1):
        role, source_id = FINAL_TEMPLATES[
            (ordinal - 1) % len(FINAL_TEMPLATES)
        ]
        canary_v2.append(
            clone_template(
                templates[source_id],
                f"h200canaryv2_{ordinal:04d}",
                role,
                (ordinal - 1) % CANARY_SHARDS,
                CANARY_SHARDS,
                ordinal,
            )
        )
    canary_v2_root = ROOT / "manifests/h200_pipeline_canary_v2"
    canary_v2_path = canary_v2_root / "input.jsonl"
    canary_v2_text = canonical_lines(canary_v2)
    write_once_or_verify(canary_v2_path, canary_v2_text)
    canary_v2_shards: list[dict[str, Any]] = []
    for shard_index in range(CANARY_SHARDS):
        rows = [
            row
            for row in canary_v2
            if row["assigned_shard"] == shard_index
        ]
        path = (
            canary_v2_root
            / "shards"
            / f"shard-{shard_index:03d}-of-{CANARY_SHARDS:03d}.jsonl"
        )
        text = canonical_lines(rows)
        write_once_or_verify(path, text)
        canary_v2_shards.append(
            {
                "shard_index": shard_index,
                "rows": len(rows),
                "path": str(path),
                "sha256": digest_text(text),
            }
        )
    canary_v2_metadata_path = (
        canary_v2_root / "MANIFEST_METADATA.json"
    )
    if canary_v2_metadata_path.exists():
        canary_v2_created = json.loads(
            canary_v2_metadata_path.read_text(encoding="utf-8")
        )["created_utc"]
    else:
        canary_v2_created = capture.utc_now()
    write_once_or_verify(
        canary_v2_metadata_path,
        json.dumps(
            {
                "schema_version": "xonotic-h200-canary-manifest-v2",
                "created_utc": canary_v2_created,
                "source_commit": (
                    capture.build_root() / "SOURCE_COMMIT"
                ).read_text(encoding="utf-8").strip(),
                "split": CANARY_SPLIT,
                "formal_collection_authorized": False,
                "training_admitted": False,
                "canary": {
                    "path": str(canary_v2_path),
                    "rows": len(canary_v2),
                    "sha256": digest_text(canary_v2_text),
                    "shard_method": (
                        "canonical manifest order round-robin: "
                        "(canary_ordinal - 1) mod 32"
                    ),
                    "shard_count": CANARY_SHARDS,
                    "rows_per_shard": CANARY_COUNT // CANARY_SHARDS,
                    "shards": canary_v2_shards,
                },
                "template_roles": [
                    {"role": role, "source_episode_id": source_id}
                    for role, source_id in FINAL_TEMPLATES
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    shard_records: list[dict[str, Any]] = []
    for shard_index in range(CANARY_SHARDS):
        shard_rows = [
            row for row in canary if row["assigned_shard"] == shard_index
        ]
        shard_path = (
            canary_root
            / "shards"
            / f"shard-{shard_index:03d}-of-{CANARY_SHARDS:03d}.jsonl"
        )
        shard_text = canonical_lines(shard_rows)
        write_once_or_verify(shard_path, shard_text)
        shard_records.append(
            {
                "shard_index": shard_index,
                "rows": len(shard_rows),
                "path": str(shard_path),
                "sha256": digest_text(shard_text),
            }
        )

    metadata_path = canary_root / "MANIFEST_METADATA.json"
    if metadata_path.exists():
        created_utc = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )["created_utc"]
    else:
        created_utc = capture.utc_now()
    metadata = {
        "schema_version": "xonotic-h200-canary-manifest-v1",
        "created_utc": created_utc,
        "source_commit": (
            capture.build_root() / "SOURCE_COMMIT"
        ).read_text(encoding="utf-8").strip(),
        "split": CANARY_SPLIT,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "representative": {
            "path": str(representative_path),
            "rows": len(representative),
            "sha256": digest_text(representative_text),
        },
        "canary": {
            "path": str(canary_path),
            "rows": len(canary),
            "sha256": digest_text(canary_text),
            "shard_method": (
                "canonical manifest order round-robin: "
                "(canary_ordinal - 1) mod 32"
            ),
            "shard_count": CANARY_SHARDS,
            "rows_per_shard": CANARY_COUNT // CANARY_SHARDS,
            "shards": shard_records,
        },
        "template_roles": [
            {"role": role, "source_episode_id": source_id}
            for role, source_id in TEMPLATES
        ],
    }
    metadata_text = json.dumps(
        metadata, indent=2, sort_keys=True, ensure_ascii=False
    ) + "\n"
    write_once_or_verify(metadata_path, metadata_text)
    write_once_or_verify(
        ROOT / "manifests/h200_representative/MANIFEST_METADATA.json",
        json.dumps(
            {
                **metadata,
                "canary": None,
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    capture.require_conda()
    metadata = materialize()
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
