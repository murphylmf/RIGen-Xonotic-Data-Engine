#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
tmp_root=${XONOTIC_CAPTURE_TMP:-./tmp/xonotic_capture}
sysroot="$tmp_root/build/sysroot"
output="$tmp_root/build/sdl_offscreen_gl_audio_probe"
libdir="$sysroot/usr/lib/aarch64-linux-gnu"

gcc -O2 -Wall -Wextra -Werror \
  -I"$sysroot/usr/include/SDL2" \
  -I"$sysroot/usr/include" \
  -I"$sysroot/usr/include/aarch64-linux-gnu" \
  "$root/probes/sdl_offscreen_gl_audio_probe.c" \
  -L"$libdir" -Wl,-rpath,/usr/lib/aarch64-linux-gnu \
  -lSDL2 -lm -ldl -lpthread \
  -o "$output"

file "$output"
ldd "$output"

SDL_VIDEODRIVER=offscreen \
SDL_AUDIODRIVER=dummy \
SDL_RENDER_DRIVER=opengl \
"$output"
