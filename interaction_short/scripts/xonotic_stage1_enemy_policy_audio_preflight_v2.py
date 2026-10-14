                      
"""Waypoint-clean successor to the immutable enemy-policy audio preflight."""

from __future__ import annotations

import xonotic_capture as capture
import xonotic_stage1_enemy_policy_audio_preflight as implementation


SPLIT = "v2_stage1_enemy_policy_audio_preflight_v2"
PREFLIGHT_ROOT = capture.ROOT / SPLIT
SCENARIOS_PATH = capture.ROOT / f"configs/{SPLIT}_scenarios.jsonl"
PREVIEW_ROOT = (
    capture.ROOT / "previews/stage1_enemy_policy_audio_preflight_v2"
)


def configure_version() -> None:
    implementation.SPLIT = SPLIT
    implementation.PREFLIGHT_ROOT = PREFLIGHT_ROOT
    implementation.SCENARIOS_PATH = SCENARIOS_PATH
    implementation.CANDIDATES_PATH = (
        PREFLIGHT_ROOT / "manifests/candidates.jsonl"
    )
    implementation.REJECTS_PATH = (
        PREFLIGHT_ROOT / "manifests/rejects.jsonl"
    )
    implementation.AUDIT_PATH = (
        PREFLIGHT_ROOT / "POLICY_PREFLIGHT_AUDIT.json"
    )
    implementation.REPORT_PATH = (
        PREFLIGHT_ROOT / "POLICY_PREFLIGHT_REPORT.md"
    )
    implementation.PREVIEW_ROOT = PREVIEW_ROOT
    implementation.EPISODE_PREFIX = "s1polaudfix"


def main() -> int:
    configure_version()
    return implementation.main()


if __name__ == "__main__":
    raise SystemExit(main())
