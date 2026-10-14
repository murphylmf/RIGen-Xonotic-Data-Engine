#!/usr/bin/env bash
set -euo pipefail

sysroot=${XONOTIC_SYSROOT:-./tmp/xonotic_capture/build/sysroot}
libdir="$sysroot/usr/lib/aarch64-linux-gnu"

if (($# == 0)); then
  printf 'usage: %s [--prefix|--exec-prefix|--version|--cflags|--libs|--static-libs]\n' "$0" >&2
  exit 64
fi

for argument in "$@"; do
  case "$argument" in
    --prefix|--exec-prefix)
      printf '%s\n' "$sysroot/usr"
      ;;
    --version)
      dpkg-query -W -f='${Version}\n' libsdl2-2.0-0:arm64
      ;;
    --cflags)
      printf '%s\n' "-I$sysroot/usr/include/SDL2 -I$sysroot/usr/include/aarch64-linux-gnu -D_REENTRANT"
      ;;
    --libs)
      printf '%s\n' "-L$libdir -Wl,-rpath,/usr/lib/aarch64-linux-gnu -lSDL2"
      ;;
    --static-libs)
      printf '%s\n' "-L$libdir -Wl,-rpath,/usr/lib/aarch64-linux-gnu -lSDL2 -ldl -lpthread -lm"
      ;;
    *)
      printf 'unsupported argument: %s\n' "$argument" >&2
      exit 64
      ;;
  esac
done
