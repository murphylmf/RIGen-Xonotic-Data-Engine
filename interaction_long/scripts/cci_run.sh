#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
source "$script_dir/cci_node_bootstrap.sh"
[[ $# -gt 0 ]] || { echo "usage: cci_run.sh COMMAND [ARG ...]" >&2; exit 64; }
exec "$@"
