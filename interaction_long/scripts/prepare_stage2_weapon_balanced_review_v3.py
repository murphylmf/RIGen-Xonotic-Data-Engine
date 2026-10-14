                      
"""Materialize the open-geometry Stage-2 weapon-balanced review v3."""

from __future__ import annotations

import os


os.environ["STAGE2_WEAPON_BALANCED_COHORT_VERSION"] = "v3"

import prepare_stage2_weapon_balanced_review_v1 as review              


if __name__ == "__main__":
    raise SystemExit(review.main())
