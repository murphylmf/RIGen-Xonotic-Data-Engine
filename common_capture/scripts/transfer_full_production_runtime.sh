#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/.." && pwd -P)
destination=${1:-}

[[ -n "$destination" ]] || {
  echo "usage: $0 LOCAL_OR_RSYNC_DESTINATION_ROOT" >&2
  echo "example: $0 local-xonotic-workspace" >&2
  exit 64
}
command -v rsync >/dev/null || {
  echo "rsync is required" >&2
  exit 69
}

items=(
  assets/OFFICIAL_ASSET_ALLOWLIST.json
  build/capture-7e8310b0d0c1-x86_64
  build/capture-82bf40a4ddee-x86_64
  env/xonotic-capture-linux-x86_64-20260727.tar.gz.sha256
  scripts
  configs
  locks
  qa
  licenses
  tests
  patches
  probes
  migration
  preflight_v2/PREFLIGHT_REPORT.json
  preflight_v2/PREFLIGHT_REPORT.md
  manifests/stage1_foundation_v5_formal_56x1_runtime_r5
  manifests/stage1_foundation_v5_formal_56x1_recovery_r6
  manifests/stage1_foundation_v4/ENEMY_PATH_PREFLIGHT.json
  stage1_path_certification_v5
  stage1_routes/plans
  manifests/stage2_formal_40k_v1
  manifests/stage2_causal_bootstrap_v5/encounter_certification/input.jsonl
  manifests/stage2_weapon_balanced_review_v3/base_traces
  stage2_prefrozen_player_motion_review_v1_output/episodes/s2pmv1_g04a_mortar_broad_sparse/states.parquet
  stage2_prefrozen_player_motion_replenishment_v1_output/episodes/s2pmr1_g07_vortex_broad_sparse/states.parquet
  stage2_prefrozen_player_motion_replenishment_v1_output/episodes/s2pmr1_g03_machinegun_broad_sparse/states.parquet
  stage2_prefrozen_player_motion_replenishment_v2_output/episodes/s2pmr2_g02_shotgun_approach_broad_sparse/states.parquet
  stage2_formal_canary_v1_output/FORMAL_CANARY_EFFECTIVE_AUDIT.json
  stage2_stationary_pair_certification_v1_r2_output/STATIONARY_PAIR_CERTIFICATION_AUDIT.json
)

if [[ ${XONOTIC_TRANSFER_REDOWNLOADABLES:-1} == 1 ]]; then
  items+=(
    assets/release-0.8.6
    runtime/nvidia/580.95.05
    env/xonotic-capture-linux-x86_64-20260727.tar.gz
  )
elif [[ ${XONOTIC_TRANSFER_REDOWNLOADABLES:-1} != 0 ]]; then
  echo "XONOTIC_TRANSFER_REDOWNLOADABLES must be 0 or 1" >&2
  exit 64
fi

for document in "$root"/*.md; do
  items+=("$(basename -- "$document")")
done

sources=()
for item in "${items[@]}"; do
  [[ -e "$root/$item" ]] || {
    echo "required runtime item missing: $root/$item" >&2
    exit 66
  }
  sources+=("$root/./$item")
done

rsync_args=(
  --archive \
  --hard-links \
  --relative \
  --partial \
)
if [[ ${XONOTIC_TRANSFER_DRY_RUN:-0} == 1 ]]; then
  rsync_args+=(--dry-run --stats)
else
  rsync_args+=(--info=progress2)
fi

rsync "${rsync_args[@]}" "${sources[@]}" "$destination"
