#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
tmp_root=${XONOTIC_CAPTURE_TMP:-./tmp/xonotic_capture}
duration=${1:-20}
map=${2:-stormkeep}
run_id=${3:-baseline-smoke}

case "$duration" in
  ''|*[!0-9]*) printf 'duration must be an integer number of seconds\n' >&2; exit 64 ;;
esac

binary="$root/build/baseline-0.8.6-aarch64/bin/xonotic-local-sdl"
basedir="$root/assets/release-0.8.6/Xonotic"
run_dir="$tmp_root/runs/$run_id"
userdir="$run_dir/user"
metrics="$run_dir/nvidia-smi.csv"

[[ -x "$binary" ]] || { printf 'missing baseline client: %s\n' "$binary" >&2; exit 66; }
[[ -f "$basedir/data/xonotic-20230620-data.pk3" ]] || {
  printf 'missing official 0.8.6 data pk3 under %s\n' "$basedir" >&2
  exit 66
}

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
    nvidia-smi --query-gpu=timestamp,index,name,utilization.gpu,utilization.memory,memory.used,power.draw \
      --format=csv,noheader,nounits >> "$metrics" 2>&1 || true
    sleep 1
  done
) &
monitor_pid=$!

export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl


timeout --signal=TERM --kill-after=10 "$((duration + 120))" \
  "$binary" \
  -xonotic \
  -basedir "$basedir" \
  -userdir "$userdir" \
  -window -width 1280 -height 720 \
  -sndspeed 48000 -sndbits 16 -sndstereo \
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
  +volume 1 \
  +map "$map" \
  +defer "$duration" quit

if find "$userdir" -type f \( -path '*/dlcache/*' -o -name '*.pk3' -o -name '*.pk3dir' \) -print -quit | grep -q .; then
  printf 'asset isolation gate failed; unexpected downloaded/user package:\n' >&2
  find "$userdir" -type f \( -path '*/dlcache/*' -o -name '*.pk3' -o -name '*.pk3dir' \) -print >&2
  exit 79
fi

printf 'run_dir=%s\n' "$run_dir"
printf 'map=%s\n' "$map"
printf 'duration_seconds=%s\n' "$duration"
printf 'unexpected_user_packages=0\n'
