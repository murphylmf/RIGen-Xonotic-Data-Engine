                      
"""Bind one v14 category shard to one selected GPU."""

from __future__ import annotations

import run_stage2_motion_42k_activeonly_v13_multigpu as gpu_binding
import run_stage2_motion_42k_activeonly_v14_shard as shard_runner


gpu_binding.shard_runner = shard_runner


if __name__ == "__main__":
    raise SystemExit(gpu_binding.main())
