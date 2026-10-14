#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
conda_bin=./environment
environment=xonotic-capture
explicit_lock="$root/locks/conda-xonotic-capture-explicit.txt"

"$conda_bin" run --no-capture-output -n "$environment" python - <<'PY'
import json
import platform

import jsonschema
import numpy
import pandas
import psutil
import pyarrow
import scipy
import soundfile
import yaml

versions = {
    "python": platform.python_version(),
    "numpy": numpy.__version__,
    "pandas": pandas.__version__,
    "pyarrow": pyarrow.__version__,
    "scipy": scipy.__version__,
    "soundfile": soundfile.__version__,
    "psutil": psutil.__version__,
    "pyyaml": yaml.__version__,
    "jsonschema": jsonschema.__version__,
}
print(json.dumps(versions, indent=2, sort_keys=True))
PY

"$conda_bin" list -n "$environment" --explicit > "$explicit_lock"
sha256sum "$explicit_lock"
