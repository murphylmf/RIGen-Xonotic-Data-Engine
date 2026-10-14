#!/usr/bin/env bash
set -euo pipefail

workspace=./xonotic_capture
manifest_root="${workspace}/manifests/stage2_causal_secondary_replenishment_v1"
output_root="${workspace}/stage2_causal_secondary_replenishment_v1_output"
tmp_root=./tmp/xonotic_capture/stage2-secondary-replenishment-v1-b40
source_commit=b40e26fd4e33b18b2002bf24beb6a78cef5fac96

cd "${workspace}"
exec scripts/cci_run.sh python scripts/run_capture_manifest_shard.py run \
  --input-manifest \
  "${manifest_root}/shards/shard-000-of-001.jsonl" \
  --manifest-metadata "${manifest_root}/MANIFEST_METADATA.json" \
  --output-root "${output_root}" \
  --shard-index 0 \
  --shard-count 1 \
  --workers 2 \
  --live-concurrency 2 \
  --render-concurrency 2 \
  --sdl-concurrency 2 \
  --encode-concurrency 2 \
  --x264-threads 4 \
  --expected-source-commit "${source_commit}" \
  --raw-audit-percent 100 \
  --port-base 40000 \
  --tmp-root "${tmp_root}" \
  --gpu-index 0 \
  --max-operational-attempts 2
