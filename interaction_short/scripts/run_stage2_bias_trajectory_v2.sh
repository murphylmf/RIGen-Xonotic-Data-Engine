#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
source_commit=7e8310b0d0c135774f5cfbdb08122eec1f12c99b
output_root=${STAGE2_TRAJECTORY_OUTPUT_ROOT:-"${workspace}/stage2_bias_correction_v2_trajectory"}
tmp_root=${STAGE2_TRAJECTORY_TMP_ROOT:-"./tmp/xonotic-stage2-bias-v2-trajectory"}
log_root="${workspace}/logs/stage2_bias_correction_v2"
mkdir -p "$log_root" "$tmp_root"
log_path=${STAGE2_TRAJECTORY_LOG:-"${log_root}/trajectory.log"}

export XONOTIC_BUILD_GLOB=build/capture-7e8310b0d0c1-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

cd "$workspace"
exec > >(tee -a "$log_path") 2>&1
exec scripts/cci_run.sh python scripts/run_stage2_trajectory_validation.py \
  --manifest-root "${workspace}/manifests/stage2_bias_correction_v2" \
  --output-root "$output_root" \
  --tmp-root "$tmp_root" \
  --source-commit "$source_commit" \
  --workers "${STAGE2_TRAJECTORY_WORKERS:-8}" \
  --port-base "${STAGE2_TRAJECTORY_PORT_BASE:-41000}" \
  --max-attempts "${STAGE2_TRAJECTORY_MAX_ATTEMPTS:-2}" \
  "$@"
