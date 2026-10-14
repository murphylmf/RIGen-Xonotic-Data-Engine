#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
shard_count=${STAGE2_SHARD_COUNT:?set STAGE2_SHARD_COUNT to 32 or 56}
cohort=${STAGE2_COHORT:-primary}
rank=${STAGE2_RANK:-${SENSECORE_PYTORCH_NODE_RANK:-${JOB_COMPLETION_INDEX:-${RANK:-}}}}

if [[ "$shard_count" != 32 && "$shard_count" != 56 ]]; then
  echo "STAGE2_SHARD_COUNT must be 32 or 56" >&2
  exit 64
fi
if [[ "$cohort" != primary && "$cohort" != reserve ]]; then
  echo "STAGE2_COHORT must be primary or reserve" >&2
  exit 64
fi
if [[ ! "$rank" =~ ^[0-9]+$ ]] || (( rank < 0 || rank >= shard_count )); then
  echo "rank must come from SENSECORE_PYTORCH_NODE_RANK, JOB_COMPLETION_INDEX, RANK, or STAGE2_RANK in [0,$((shard_count - 1))]" >&2
  exit 64
fi

rank_padded=$(printf '%03d' "$rank")
count_padded=$(printf '%03d' "$shard_count")

cd "$workspace"
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard_formal.py status \
  --input-manifest "${workspace}/manifests/stage2_formal_40k_v1/${cohort}/shards-${count_padded}/shard-${rank_padded}-of-${count_padded}.jsonl" \
  --output-root "${STAGE2_OUTPUT_ROOT:-${workspace}/stage2_formal_40k_v1_output/${shard_count}x1/${cohort}}"
