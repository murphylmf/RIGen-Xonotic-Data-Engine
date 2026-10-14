#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/../.." && pwd -P)
map_root=${XONOTIC_DUEL_MAP_ROOT:-./xonotic_workspace}
offline_root=${XONOTIC_DUEL_OFFLINE_ROOT:-./xonotic_workspace}
assets_root=${XONOTIC_DUEL_ASSETS:-./xonotic_workspace}
binary="$offline_root/build/offline-accelerated-0.8.6-aarch64/bin/xonotic-local-sdl"
custom_progs="$duel_root/build/duel-v11-visibility-v2-qc/progs.dat"
custom_csprogs="$duel_root/build/duel-v11-visibility-v2-qc/csprogs.dat"
map_name=duel_box_space

if (($# < 2 || $# > 3)); then
  printf 'usage: %s SOURCE_DEMO OUTPUT_DIR [REPLAY_FPS]\n' "$0" >&2
  exit 64
fi
source_demo=$1
output_dir=$2
replay_fps=${3:-64}
source_manifest="$(dirname -- "$source_demo")/manifest.json"
scratch_root=${XONOTIC_DUEL_VISIBILITY_SCRATCH_ROOT:-./tmp}

[[ "$output_dir" == /* ]] || { printf 'output dir must be absolute\n' >&2; exit 64; }
[[ "$replay_fps" =~ ^[1-9][0-9]*$ ]] || { printf 'replay fps must be a positive integer\n' >&2; exit 64; }
[[ ! -e "$output_dir" ]] || { printf 'refusing to overwrite output: %s\n' "$output_dir" >&2; exit 73; }
for required in \
  "$source_demo" "$source_manifest" "$binary" "$custom_progs" "$custom_csprogs" \
  "$duel_root/configs/clean_client.cfg" "$duel_root/configs/offline_render.cfg" \
  "$map_root/map_pk3dir/maps/$map_name.bsp" \
  "$map_root/map_pk3dir/maps/$map_name.mapinfo" \
  "$map_root/map_pk3dir/maps/$map_name.waypoints" \
  "$map_root/map_pk3dir/maps/$map_name.waypoints.cache" \
  "$map_root/map_pk3dir/maps/$map_name.jpg" \
  "$map_root/map_pk3dir/gfx/${map_name}_mini.jpg" \
  "$map_root/map_pk3dir/gfx/${map_name}_radar.jpg"; do
  [[ -s "$required" ]] || { printf 'missing required input: %s\n' "$required" >&2; exit 66; }
done
[[ -x "$binary" ]] || { printf 'runtime is not executable: %s\n' "$binary" >&2; exit 66; }
[[ -d "$scratch_root" && -w "$scratch_root" ]] || { printf 'scratch root is not writable: %s\n' "$scratch_root" >&2; exit 66; }

mkdir -p "$output_dir/runtime" "$output_dir/configs"
work_tmp=$(mktemp -d "$scratch_root/xonotic-duel-v11-visibility.XXXXXX")
cleanup() {
  if [[ "$work_tmp" == "$scratch_root"/xonotic-duel-v11-visibility.* ]]; then
    rm -rf -- "$work_tmp"
  else
    printf 'refusing unexpected temporary cleanup: %s\n' "$work_tmp" >&2
  fi
}
trap cleanup EXIT

userdir="$work_tmp/user"
mkdir -p "$userdir/data/demos" "$userdir/data/video" "$userdir/data/maps" \
  "$userdir/data/gfx" "$userdir/data/duel_visibility"
install -m 644 "$source_demo" "$userdir/data/demos/source.dem"
install -m 644 "$duel_root/configs/clean_client.cfg" "$userdir/data/clean_client.cfg"
install -m 644 "$duel_root/configs/offline_render.cfg" "$userdir/data/offline_render.cfg"
install -m 644 "$custom_progs" "$userdir/data/progs.dat"
install -m 644 "$custom_csprogs" "$userdir/data/csprogs.dat"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.bsp" "$userdir/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.mapinfo" "$userdir/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.waypoints" "$userdir/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.waypoints.cache" "$userdir/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.jpg" "$userdir/data/maps/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_mini.jpg" "$userdir/data/gfx/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_radar.jpg" "$userdir/data/gfx/"

install -m 644 "$custom_progs" "$output_dir/runtime/"
install -m 644 "$custom_csprogs" "$output_dir/runtime/"
install -m 644 "$duel_root/configs/clean_client.cfg" "$output_dir/configs/"
install -m 644 "$duel_root/configs/offline_render.cfg" "$output_dir/configs/"
install -m 644 "$source_manifest" "$output_dir/source_demo_manifest.json"

export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export LC_ALL=C

start_ns=$(date +%s%N)
timeout --signal=TERM --kill-after=15 900 \
  "$binary" \
  -xonotic -nocdaudio -nosound \
  -basedir "$assets_root" \
  -userdir "$userdir" \
  -window -width 960 -height 540 \
  +exec clean_client.cfg \
  +exec offline_render.cfg \
  +csqc_usedemoprogs 0 \
  +set duel_visibility_telemetry 1 \
  +set duel_visibility_telemetry_file duel_visibility/labels.tsv \
  +cl_capturevideo_width 160 \
  +cl_capturevideo_height 90 \
  +cl_capturevideo_fps "$replay_fps" \
  +cl_capturevideo_framestep 1 \
  +cl_capturevideo_realtime 0 \
  +cl_capturevideo_offline_accelerate 1 \
  +cl_capturevideo_demo_stop 1 \
  +cl_capturevideo_ogg 1 \
  +cl_capturevideo_ogg_theora_quality 8 \
  +cl_capturevideo_number 0 \
  +cl_capturevideo_nameformat visibility_probe_ \
  -capturedemo demos/source \
  > "$output_dir/engine.log" 2>&1
stop_ns=$(date +%s%N)

labels="$userdir/data/duel_visibility/labels.tsv"
if [[ ! -s "$labels" ]]; then
  mapfile -t discovered_labels < <(find "$userdir" -type f -name labels.tsv -print | sort)
  if ((${#discovered_labels[@]} == 1)); then
    labels=${discovered_labels[0]}
  else
    printf 'visibility labels were not generated; userdir files:\n' >&2
    find "$userdir" -maxdepth 6 -type f -printf '%P\n' | sort >&2
    exit 70
  fi
fi
grep -aFq 'xonotic-v0.8.6-duel-v11-visibility-v2' "$output_dir/engine.log" || {
  printf 'visibility CSQC watermark was not loaded\n' >&2; exit 70;
}
grep -aFq 'duel_visibility_telemetry:opened' "$output_dir/engine.log" || {
  printf 'visibility telemetry did not open\n' >&2; exit 70;
}
grep -aFq 'duel_visibility_telemetry:closed' "$output_dir/engine.log" || {
  printf 'visibility telemetry did not close cleanly\n' >&2; exit 70;
}
visibility_output="$output_dir/visibility_raw_${replay_fps}hz.tsv"
install -m 644 "$labels" "$visibility_output"

mapfile -t probe_videos < <(find "$userdir/data/video" -maxdepth 1 -type f \
  \( -name 'visibility_probe_*.ogv' -o -name 'visibility_probe_*.avi' \) -print | sort)
if ((${#probe_videos[@]} == 1)); then
  ffprobe -v error -count_frames -show_streams -show_format -of json \
    "${probe_videos[0]}" > "$output_dir/capture_probe_ffprobe.json"
fi

wall_seconds=$(awk -v ns="$((stop_ns - start_ns))" 'BEGIN {printf "%.6f", ns / 1000000000}')
printf 'wall_seconds=%s\n' "$wall_seconds"
printf 'labels=%s\n' "$visibility_output"
