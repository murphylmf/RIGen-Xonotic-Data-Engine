#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
source_commit=7e8310b0d0c135774f5cfbdb08122eec1f12c99b
manifest_root="${workspace}/manifests/stage2_bias_correction_v2_replenishment_v1"
output_root=${STAGE2_REPLENISHMENT_TRAJECTORY_OUTPUT_ROOT:-"${workspace}/stage2_bias_correction_v2_replenishment_v1_trajectory"}
tmp_root=${STAGE2_REPLENISHMENT_TRAJECTORY_TMP_ROOT:-"./tmp/xonotic-stage2-bias-v2-replenishment-v1-trajectory"}
log_root="${workspace}/logs/stage2_bias_correction_v2"
log_path=${STAGE2_REPLENISHMENT_TRAJECTORY_LOG:-"${log_root}/replenishment-v1-trajectory.log"}
mkdir -p "$log_root" "$tmp_root"

export XONOTIC_BUILD_GLOB=build/capture-7e8310b0d0c1-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

cd "$workspace"
exec > >(tee -a "$log_path") 2>&1
exec scripts/cci_run.sh python scripts/run_stage2_trajectory_validation.py \
  --manifest-root "$manifest_root" \
  --output-root "$output_root" \
  --tmp-root "$tmp_root" \
  --source-commit "$source_commit" \
  --workers 1 \
  --port-base 43800 \
  --max-attempts 3
