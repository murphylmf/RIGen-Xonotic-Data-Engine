#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
tmp_root=${XONOTIC_CAPTURE_TMP:-./tmp/xonotic_capture}
source_root="$tmp_root/build/release-source/Xonotic"
sysroot="$tmp_root/build/sysroot"
install_root="$root/build/baseline-0.8.6-aarch64"
qc_out="$tmp_root/build/qc-baseline-0.8.6"


qc_work=.capture-qc-work-baseline-0.8.6
jobs=${XONOTIC_BUILD_JOBS:-32}

if [[ "$(uname -m)" != "aarch64" ]]; then
  printf 'native architecture gate failed: %s\n' "$(uname -m)" >&2
  exit 78
fi

if [[ ! -d "$source_root/source/darkplaces" ]]; then
  printf 'missing extracted release source: %s\n' "$source_root" >&2
  exit 66
fi

export XONOTIC_SYSROOT="$sysroot"
export SDL_CONFIG="$root/scripts/sdl2-config-local.sh"
export CXX=g++

(
  cd "$source_root"



  make -j"$jobs" both \
    CFLAGS='-pipe -march=native -mtune=native -flto=auto'
)

make -C "$source_root/source/gmqcc" -j"$jobs" CXX=g++ gmqcc qcvm

mkdir -p "$qc_out" "$qc_work"
make -C "$source_root/source/qcsrc" \
  -j"$jobs" \
  QCC="$source_root/source/gmqcc/gmqcc" \
  QCCFLAGS_WATERMARK=xonotic-v0.8.6 \
  PROGS_OUT="$qc_out" \
  WORKDIR="$qc_work" \
  clean qc

mkdir -p "$install_root/bin" "$install_root/qc"
cp -f "$source_root/xonotic-local-sdl" "$install_root/bin/"
cp -f "$source_root/xonotic-local-dedicated" "$install_root/bin/"
cp -f "$source_root/source/gmqcc/gmqcc" "$install_root/bin/"
cp -f "$source_root/source/gmqcc/qcvm" "$install_root/bin/"
cp -f "$qc_out/csprogs.dat" "$qc_out/menu.dat" "$qc_out/progs.dat" \
  "$install_root/qc/"

find "$install_root" -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$root/locks/baseline-0.8.6-aarch64.sha256"

for binary in "$install_root/bin/"*; do
  file "$binary"
  ldd "$binary" 2>&1 || true
done
cat "$root/locks/baseline-0.8.6-aarch64.sha256"
