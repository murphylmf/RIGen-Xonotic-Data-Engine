                      
"""Audit the Stage-1 v2 audio expectation against formal rows and journals."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xonotic_capture as capture              


def parse_qa_failure(detail: str) -> list[str]:
    value = detail
    if value.startswith("qa_gate_failed: "):
        value = value.split(": ", 1)[1]
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    failed = payload.get("failed") or payload.get("failed_gates") or []
    return sorted(str(item) for item in failed)


def load_formal_rows(
    manifest_root: Path,
) -> tuple[dict[str, dict[str, Any]], Counter[tuple[str, bool, bool]]]:
    rows: dict[str, dict[str, Any]] = {}
    transitions: Counter[tuple[str, bool, bool]] = Counter()
    for wave in ("primary", "replenishment"):
        for path in sorted(
            (manifest_root / "shards" / wave).glob("*.jsonl")
        ):
            for row in capture.load_jsonl(path):
                episode_id = str(row["episode_id"])
                if episode_id in rows:
                    raise capture.CaptureFailure(
                        "audio_revision_duplicate_episode_id", episode_id
                    )
                policy = capture.stage1_audio_expectation(row)
                row["_audio_revision_policy"] = policy
                rows[episode_id] = row
                transitions[
                    (
                        wave,
                        bool(row.get("expects_sound")),
                        bool(policy["expects_sound"]),
                    )
                ] += 1
    return rows, transitions


def accepted_records(output_root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    journal_root = output_root / "manifests/shards/primary"
    for path in sorted(journal_root.glob("shard-*/accepted_candidates.jsonl")):
        for row in capture.load_jsonl(path):
            records.setdefault(str(row["episode_id"]), row)
    return records


def direct_audio_only_failures(output_root: Path) -> set[str]:
    result: set[str] = set()
    journal_root = output_root / "manifests/shards/primary"
    for path in sorted(journal_root.glob("shard-*/rejects.jsonl")):
        for row in capture.load_jsonl(path):
            if (
                row.get("terminal") is True
                and row.get("reason") == "qa_gate_failed"
                and parse_qa_failure(str(row.get("detail", "")))
                == ["expected_audio_non_silent"]
            ):
                result.add(str(row["episode_id"]))
    return result


def qa_peak(record: dict[str, Any]) -> dict[str, Any]:
    qa_path = Path(str(record["episode_path"])) / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    return {
        "episode_id": str(record["episode_id"]),
        "qa_path": str(qa_path),
        "peak": int((qa.get("audio") or {}).get("peak_s16", 0)),
        "samples_per_channel": int(
            (qa.get("audio") or {}).get("samples_per_channel", 0)
        ),
        "hard_gates_pass": all(
            bool(value)
            for value in (qa.get("hard_gates") or {}).values()
        ),
    }


def deterministic_sample(
    episode_ids: list[str], count: int
) -> list[str]:
    return sorted(
        episode_ids,
        key=lambda value: (
            hashlib.sha256(value.encode()).hexdigest(),
            value,
        ),
    )[:count]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-root",
        default=str(
            capture.ROOT
            / "manifests/stage1_foundation_v5_formal_56x1"
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(
            capture.ROOT / "stage1_foundation_v5_output_56x1"
        ),
    )
    parser.add_argument("--accepted-stricter-sample", type=int, default=100)
    args = parser.parse_args()
    manifest_root = Path(args.manifest_root).resolve()
    output_root = Path(args.output_root).resolve()

    rows, transitions = load_formal_rows(manifest_root)
    primary_rows = {
        episode_id: row
        for episode_id, row in rows.items()
        if row.get("candidate_wave") == "primary"
    }
    explicit_sound_violations = []
    for episode_id, row in rows.items():
        policy = row["_audio_revision_policy"]
        action = row.get("action_design") or {}
        explicit = bool(
            str(action.get("weapon_action", "none")) != "none"
            or action.get("jump")
            or (
                policy["enemy_present"]
                and policy["enemy_motion_mode"] != 0
            )
        )
        if explicit and not policy["expects_sound"]:
            explicit_sound_violations.append(episode_id)

    failures = direct_audio_only_failures(output_root)
    missing_failure_rows = sorted(failures - primary_rows.keys())
    failure_still_expected = sorted(
        episode_id
        for episode_id in failures & primary_rows.keys()
        if primary_rows[episode_id]["_audio_revision_policy"][
            "expects_sound"
        ]
    )

    accepted = accepted_records(output_root)
    stricter_ids = [
        episode_id
        for episode_id, row in primary_rows.items()
        if not bool(row.get("expects_sound"))
        and row["_audio_revision_policy"]["expects_sound"]
        and episode_id in accepted
    ]
    sampled_ids = deterministic_sample(
        stricter_ids, args.accepted_stricter_sample
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        sampled_audio = list(
            executor.map(
                qa_peak, (accepted[episode_id] for episode_id in sampled_ids)
            )
        )
    sampled_silent = [
        row["episode_id"] for row in sampled_audio if row["peak"] <= 0
    ]
    checks = {
        "formal_rows_72000": len(rows) == 72_000,
        "primary_rows_60000": len(primary_rows) == 60_000,
        "explicit_sound_never_relaxed": not explicit_sound_violations,
        "direct_audio_only_failure_rows_joined": not missing_failure_rows,
        "direct_audio_only_failures_now_allow_natural_silence": (
            not failure_still_expected
        ),
        "stricter_accepted_sample_non_silent": not sampled_silent,
        "stricter_accepted_sample_audio_240000": all(
            row["samples_per_channel"] == capture.AUDIO_SAMPLES
            for row in sampled_audio
        ),
        "stricter_accepted_sample_hard_gates_pass": all(
            row["hard_gates_pass"] for row in sampled_audio
        ),
        "native_threshold_216": (
            capture.STAGE1_PLAYER_FOOTSTEP_SPEED_THRESHOLD == 216.0
        ),
    }
    report = {
        "schema_version": "xonotic-stage1-audio-expectation-audit-v1",
        "created_utc": capture.utc_now(),
        "manifest_root": str(manifest_root),
        "output_root": str(output_root),
        "policy_schema_version": (
            capture.STAGE1_AUDIO_EXPECTATION_POLICY_SCHEMA
        ),
        "player_footstep_speed_threshold": (
            capture.STAGE1_PLAYER_FOOTSTEP_SPEED_THRESHOLD
        ),
        "transitions": [
            {
                "wave": wave,
                "manifest_expects_sound": old,
                "runtime_expects_sound": new,
                "rows": count,
            }
            for (wave, old, new), count in sorted(transitions.items())
        ],
        "direct_audio_only_terminal_failures": len(failures),
        "direct_audio_only_failure_still_expected": (
            failure_still_expected
        ),
        "explicit_sound_violations": explicit_sound_violations,
        "accepted_stricter_population": len(stricter_ids),
        "accepted_stricter_sample": sampled_audio,
        "accepted_stricter_sample_silent": sampled_silent,
        "checks": checks,
        "passed": all(checks.values()),
    }
    print(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
