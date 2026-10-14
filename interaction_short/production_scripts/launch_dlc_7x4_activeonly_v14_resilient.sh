#!/usr/bin/env bash
set -uo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/.." && pwd -P)
python_bin=${STAGE2_PYTHON:-./environment}
cd "$root"
exec "$python_bin" -u production_scripts/launch_dlc_7x4_activeonly_v14_resilient.py
