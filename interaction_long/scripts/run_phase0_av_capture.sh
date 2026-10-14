#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
tmp_root=${XONOTIC_CAPTURE_TMP:-./tmp/xonotic_capture}
duration=${1:-5}
map=${2:-stormkeep}
run_id=${3:-phase0-calibration}
storage=${4:-tmp}
warmup=${XONOTIC_CAPTURE_WARMUP_SECONDS:-30}

case "$duration" in
  ''|*[!0-9]*) printf 'duration must be an integer number of seconds\n' >&2; exit 64 ;;
esac
case "$storage" in
  tmp) run_root="$tmp_root/raw/phase0/$run_id" ;;
  persistent) run_root="$root/raw/phase0/$run_id" ;;
  *) printf 'storage must be tmp or persistent\n' >&2; exit 64 ;;
esac

binary="$root/build/baseline-0.8.6-aarch64/bin/xonotic-local-sdl"
basedir="$root/assets/release-0.8.6/Xonotic"
userdir="$run_root/user"
video_dir="$userdir/data/video"
encoded_dir="$root/phase0/av-tests/$run_id"
metrics="$encoded_dir/runtime_metrics.csv"
ffmpeg_log="$encoded_dir/ffmpeg.log"
prefix="${run_id}_"
stop_at=$((warmup + duration))
quit_at=$((stop_at + 5))

[[ -x "$binary" ]] || { printf 'missing baseline client: %s\n' "$binary" >&2; exit 66; }
mkdir -p "$video_dir" "$encoded_dir"
: > "$metrics"

monitor_pid=
engine_pid=
cleanup() {
  if [[ -n "$monitor_pid" ]]; then
    kill "$monitor_pid" 2>/dev/null || true
    wait "$monitor_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

timeout --signal=TERM --kill-after=15 "$((quit_at + 180))" \
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
  +g_playerstats_uri "" \
  +g_playerstats_gamereport_uri "" \
  +music_playlist_index -1 \
  +bgmvolume 0 \
  +volume 1 \
  +cl_capturevideo_width 1280 \
  +cl_capturevideo_height 720 \
  +cl_capturevideo_fps 64 \
  +cl_capturevideo_framestep 1 \
  +cl_capturevideo_realtime 0 \
  +cl_capturevideo_ogg 0 \
  +cl_capturevideo_printfps 1 \
  +cl_capturevideo_number 0 \
  +cl_capturevideo_nameformat "$prefix" \
  +map "$map" \
  +defer "$warmup" "+forward; +attack; cl_capturevideo 1" \
  +defer "$stop_at" "cl_capturevideo 0; -attack; -forward" \
  +defer "$quit_at" quit &
engine_pid=$!

printf 'timestamp_utc,gpu_util_pct,gpu_memory_util_pct,gpu_memory_mib,power_w,engine_cpu_pct,engine_rss_kib,raw_bytes\n' > "$metrics"
(
  while kill -0 "$engine_pid" 2>/dev/null; do
    gpu=$(nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,power.draw \
      --format=csv,noheader,nounits 2>/dev/null | head -1 || true)
    sample_pid=$(pgrep -P "$engine_pid" 2>/dev/null | head -1 || true)
    if [[ -z "$sample_pid" ]]; then
      sample_pid=$engine_pid
    fi
    cpu=$(ps -p "$sample_pid" -o %cpu=,rss= 2>/dev/null | xargs || true)
    raw_bytes=$(find "$video_dir" -maxdepth 1 -type f -printf '%s\n' 2>/dev/null | awk '{s += $1} END {print s + 0}')
    printf '%s,%s,%s\n' "$gpu" "${cpu// /,}" "$raw_bytes"
    sleep 1
  done
) >> "$metrics" &
monitor_pid=$!

set +e
wait "$engine_pid"
engine_rc=$?
set -e
cleanup
monitor_pid=

[[ "$engine_rc" -eq 0 ]] || {
  printf 'engine capture failed with exit code %d\n' "$engine_rc" >&2
  exit "$engine_rc"
}

mapfile -t avis < <(find "$video_dir" -maxdepth 1 -type f -name "${prefix}*.avi" -print | sort)
if ((${#avis[@]} != 1)); then
  printf 'expected exactly one raw AVI, found %d under %s\n' "${#avis[@]}" "$video_dir" >&2
  exit 65
fi
raw_avi=${avis[0]}
encoded="$encoded_dir/${run_id}.mkv"

ffprobe -v error -show_streams -show_format -of json "$raw_avi" \
  > "$encoded_dir/raw_ffprobe.json"

{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'command=ffmpeg libx264 High CRF16 CFR64 GOP64 plus FLAC\n'
  time ffmpeg -hide_banner -y -nostdin \
    -i "$raw_avi" \
    -map 0:v:0 -map 0:a:0 \
    -c:v libx264 -preset medium -profile:v high -crf 16 \
    -pix_fmt yuv420p -r 64 -fps_mode cfr \
    -g 64 -keyint_min 64 -sc_threshold 0 \
    -c:a flac -ar 48000 -ac 2 \
    "$encoded"
  printf 'finished_utc=%s\n' "$(date -u +%FT%TZ)"
} > "$ffmpeg_log" 2>&1

ffprobe -v error -show_streams -show_format -of json "$encoded" \
  > "$encoded_dir/encoded_ffprobe.json"
sha256sum "$raw_avi" "$encoded" "$metrics" \
  > "$encoded_dir/SHA256SUMS"

if find "$userdir" -type f \( -path '*/dlcache/*' -o -name '*.pk3' -o -name '*.pk3dir' \) -print -quit | grep -q .; then
  printf 'asset isolation gate failed; unexpected downloaded/user package\n' >&2
  exit 79
fi

printf 'raw_avi=%s\n' "$raw_avi"
printf 'encoded_mkv=%s\n' "$encoded"
printf 'duration_requested_seconds=%s\n' "$duration"
printf 'storage=%s\n' "$storage"
printf 'unexpected_user_packages=0\n'
