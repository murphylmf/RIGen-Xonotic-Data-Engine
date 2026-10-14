                      
"""Run the shared duel action builder with the isolated speed-100 QA limit."""

from __future__ import annotations

import importlib.util
from pathlib import Path


COMMON_BUILDER = Path(__file__).resolve().parents[1] / "build_authoritative_actions.py"
SPEC = importlib.util.spec_from_file_location(
    "xonotic_duel_shared_action_builder", COMMON_BUILDER
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load shared action builder: {COMMON_BUILDER}")

builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
builder.DUEL_MOVEMENT_INPUT_LIMIT = 100.0


if __name__ == "__main__":
    raise SystemExit(builder.main())
