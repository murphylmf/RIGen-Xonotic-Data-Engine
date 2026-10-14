#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
port=${STAGE2_BIAS_GALLERY_PORT:-18083}
root="${workspace}/stage2_bias_correction_v3_selected_output"
log="${workspace}/logs/stage2_bias_correction_v2/gallery-${port}.log"

cd "$workspace"
exec > >(tee -a "$log") 2>&1
exec python -m http.server "$port" \
  --bind 0.0.0.0 \
  --directory "$root"
