                      
"""Replace only structurally failed stationary canary slots after pair audit."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage2_formal_design as design              
import xonotic_capture as capture              


SOURCE_MANIFEST = (
    ROOT / "manifests/stage2_formal_stationary_extension_v1/input.jsonl"
)
SOURCE_REJECTS = (
    ROOT
    / "stage2_formal_canary_recovery_v1_output/manifests/shards"
    / "shard-000-of-001/rejects.jsonl"
)
PAIR_AUDIT = (
    ROOT
    / "stage2_stationary_pair_certification_v1_r2_output"
    / "STATIONARY_PAIR_CERTIFICATION_AUDIT.json"
)
OUTPUT_ROOT = ROOT / "manifests/stage2_formal_canary_recovery_v2"
SCHEMA = "xonotic-stage2-formal-canary-recovery-manifest-v2"


def write_once_or_verify(path: Path, text: str) -> None:
    payload = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise capture.CaptureFailure(
                "immutable_manifest_conflict", str(path)
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def materialize() -> list[dict]:
    audit = json.loads(PAIR_AUDIT.read_text(encoding="utf-8"))
    if audit.get("passed") is not True:
        raise capture.CaptureFailure(
            "stationary_pair_certification_not_passed", str(PAIR_AUDIT)
        )
    certified_ids = set(audit["certified_source_pair_episode_ids"])
    pairs_by_id = {
        row["episode_id"]: row for row in design.preflight_pairs()
    }
    certified_by_bin: defaultdict[str, list[dict]] = defaultdict(list)
    for pair_id in sorted(certified_ids):
        pair = pairs_by_id[pair_id]
        certified_by_bin[pair["distance_bin"]].append(pair)
    terminal_ids = {
        row["episode_id"]
        for row in capture.load_jsonl(SOURCE_REJECTS)
        if row.get("terminal") is True
    }
    source_rows = [
        row
        for row in capture.load_jsonl(SOURCE_MANIFEST)
        if row["episode_id"] in terminal_ids
    ]
    if len(source_rows) != len(terminal_ids):
        raise capture.CaptureFailure(
            "stationary_canary_terminal_source_mismatch",
            capture.canonical_json(
                {
                    "terminal": len(terminal_ids),
                    "source": len(source_rows),
                }
            ),
        )
    cursors: Counter[str] = Counter()
    rows: list[dict] = []
    for source in sorted(source_rows, key=lambda row: row["episode_id"]):
        source_design = source["formal_design"]
        distance_bin = source_design["distance_bin"]
        source_pair_id = source_design["source_pair_episode_id"]
        if source_pair_id in certified_ids:
            pair = pairs_by_id[source_pair_id]
        else:
            pool = certified_by_bin[distance_bin]
            pair = pool[cursors[distance_bin] % len(pool)]
            cursors[distance_bin] += 1
        appearance = {
            "model": source["enemy_model"],
            "skin": source["enemy_skin"],
        }
        ordinal = int(source_design["ordinal"])
        row = design.stationary_scenario(
            cohort="s2fcv1x2",
            ordinal=ordinal,
            weapon=source["weapon"],
            outcome_recipe=source_design["outcome_recipe"],
            arm=source_design["arm"],
            pair=pair,
            appearance=appearance,
            formal_collection=False,
            canary_authorization=None,
        )
        row["operational_replacement"] = {
            "schema_version": "xonotic-operational-replacement-v1",
            "replacement_for": source["episode_id"],
            "reason": "failed_full_trajectory_or_artifact_qa",
            "source_pair_certification_required": True,
            "source_pair_changed": pair["episode_id"] != source_pair_id,
            "outcome_used_for_replacement": False,
            "runtime_action_fallback": False,
            "runtime_geometry_fallback": False,
        }
        row["assigned_shard"] = 0
        row["shard_count"] = 1
        rows.append(row)
    text = design.canonical_lines(rows)
    digest = design.sha256_text(text)
    shard_path = OUTPUT_ROOT / "shards/shard-000-of-001.jsonl"
    write_once_or_verify(OUTPUT_ROOT / "input.jsonl", text)
    write_once_or_verify(shard_path, text)
    metadata = {
        "schema_version": SCHEMA,
        "source_commit": design.source_commit(),
        "data_spec_sha256": design.data_spec_sha256(),
        "rows": len(rows),
        "shard_count": 1,
        "formal_collection_authorized": False,
        "training_admitted": False,
        "logical_canary_total": 96,
        "recovery_lanes": 8,
        "pair_certification_audit": str(PAIR_AUDIT.relative_to(ROOT)),
        "pair_certification_audit_sha256": capture.sha256_file(PAIR_AUDIT),
        "outcome_used_for_replacement": False,
        "planned_outcome_distribution": dict(
            Counter(row["formal_design"]["outcome_recipe"] for row in rows)
        ),
        "input_sha256": digest,
        "review": {
            "rows": len(rows),
            "shard_count": 1,
            "shards": [
                {
                    "shard_index": 0,
                    "rows": len(rows),
                    "path": str(shard_path.relative_to(ROOT)),
                    "sha256": digest,
                }
            ],
        },
    }
    write_once_or_verify(
        OUTPUT_ROOT / "MANIFEST_METADATA.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return rows


def main() -> int:
    rows = materialize()
    print(
        capture.canonical_json(
            {
                "manifest": str(OUTPUT_ROOT / "input.jsonl"),
                "rows": len(rows),
                "outcomes": dict(
                    Counter(
                        row["formal_design"]["outcome_recipe"]
                        for row in rows
                    )
                ),
                "changed_pairs": sum(
                    row["operational_replacement"]["source_pair_changed"]
                    for row in rows
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
