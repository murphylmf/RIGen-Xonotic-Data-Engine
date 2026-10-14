#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
source "$script_dir/cci_node_bootstrap.sh"
root=$XONOTIC_CAPTURE_ROOT
duration=${1:-5}
map=${2:-stormkeep}
case "$duration" in
  ''|*[!0-9]*) echo "duration must be an integer" >&2; exit 64 ;;
esac

build="$root/$XONOTIC_BUILD_GLOB"
basedir="$root/assets/release-0.8.6/Xonotic"
run_dir="$XONOTIC_CAPTURE_TMP/gpu-smoke-$map-$(date -u +%Y%m%dT%H%M%SZ)-$$"
userdir="$run_dir/user"
log="$run_dir/client.log"
metrics="$run_dir/nvidia-smi.csv"
mkdir -p "$userdir/data"
: > "$metrics"

monitor_pid=
cleanup() {
  if [[ -n "$monitor_pid" ]]; then
    kill "$monitor_pid" 2>/dev/null || true
    wait "$monitor_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
(
  while :; do
    nvidia-smi \
      --query-gpu=utilization.gpu,memory.used \
      --format=csv,noheader,nounits >> "$metrics" 2>/dev/null || true
    sleep 1
  done
) &
monitor_pid=$!

timeout --signal=TERM --kill-after=10 180 \
  "$build/bin/xonotic-local-sdl" \
  -xonotic \
  -nocdaudio \
  -basedir "$basedir" \
  -userdir "$userdir" \
  -window -width 640 -height 360 \
  +developer 1 \
  +vid_vsync 0 \
  +cl_maxfps 64 \
  +cl_netfps 64 \
  +sys_ticrate 0.015625 \
  +sv_public 0 \
  +cl_curl_enabled 0 \
  +sv_curl_defaulturl "" \
  +sv_curl_serverpackages "" \
  +music_playlist_index -1 \
  +bgmvolume 0 \
  +volume 0 \
  +map "$map" \
  +defer "$duration" quit > "$log" 2>&1

cleanup
monitor_pid=
grep -F 'GL_VENDOR: NVIDIA' "$log" >/dev/null
grep -F 'GL_RENDERER: NVIDIA' "$log" >/dev/null
grep -F "SpawnServer: $map" "$log" >/dev/null
grep -F 'OpenGL backend started.' "$log" >/dev/null
if find "$userdir" -type f \
  \( -path '*/dlcache/*' -o -name '*.pk3' -o -name '*.pk3dir' \) \
  -print -quit | grep -q .; then
  echo "asset isolation gate failed" >&2
  exit 79
fi

grep -E '^(GL_VENDOR|GL_RENDERER|GL_VERSION):|^SpawnServer:' "$log"
awk -F, '
  {
    util=$1+0
    memory=$2+0
    if (util > max_util) max_util=util
    if (memory > max_memory) max_memory=memory
  }
  END {
    printf "max_gpu_utilization_percent=%d\n", max_util
    printf "max_gpu_memory_mib=%d\n", max_memory
  }
' "$metrics"
echo "hardware_engine_smoke=pass"
echo "run_dir=$run_dir"
