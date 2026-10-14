#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
tmp_root=${XONOTIC_CAPTURE_TMP:-./tmp/xonotic_capture}
worktree="$root/source/release-src-0.8.6/Xonotic"
sysroot="$tmp_root/build/sysroot"
jobs=${XONOTIC_BUILD_JOBS:-32}

git -C "$worktree" diff --quiet
git -C "$worktree" diff --cached --quiet
commit=$(git -C "$worktree" rev-parse HEAD)
short_commit=${commit:0:12}
source_parent="$tmp_root/build/capture-source-$short_commit"
source_root="$source_parent/Xonotic"
install_root="$root/build/capture-$short_commit-aarch64"
qc_out="$tmp_root/build/qc-capture-$short_commit"
qc_work=".capture-qc-work-$short_commit"

if [[ "$(uname -m)" != "aarch64" ]]; then
  printf 'native architecture gate failed: %s\n' "$(uname -m)" >&2
  exit 78
fi

if [[ ! -d "$source_root/source/darkplaces" ]]; then
  mkdir -p "$source_root"
  git -C "$worktree" archive --format=tar "$commit" |
    tar -xf - -C "$source_root"
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
mkdir -p "$qc_out"
make -C "$source_root/source/qcsrc" \
  QCC="$source_root/source/gmqcc/gmqcc" \
  QCCFLAGS_WATERMARK="xonotic-v0.8.6-capture-$short_commit" \
  PROGS_OUT="$qc_out" \
  WORKDIR="$qc_work" \
  clean
make -C "$source_root/source/qcsrc" \
  -j"$jobs" \
  QCC="$source_root/source/gmqcc/gmqcc" \
  QCCFLAGS_WATERMARK="xonotic-v0.8.6-capture-$short_commit" \
  PROGS_OUT="$qc_out" \
  WORKDIR="$qc_work" \
  qc

mkdir -p "$install_root/bin" "$install_root/qc"
cp -f "$source_root/xonotic-local-sdl" "$install_root/bin/"
cp -f "$source_root/xonotic-local-dedicated" "$install_root/bin/"
cp -f "$source_root/source/gmqcc/gmqcc" "$install_root/bin/"
cp -f "$source_root/source/gmqcc/qcvm" "$install_root/bin/"
cp -f "$qc_out/csprogs.dat" "$qc_out/menu.dat" "$qc_out/progs.dat" \
  "$install_root/qc/"
printf '%s\n' "$commit" > "$install_root/SOURCE_COMMIT"

sdl_version=$("$SDL_CONFIG" --version)
printf '%s\n' "$sdl_version" > "$install_root/SDL_VERSION"
read -r -a sdl_cflags <<<"$("$SDL_CONFIG" --cflags)"
read -r -a sdl_libs <<<"$("$SDL_CONFIG" --libs)"
gcc -O2 -Wall -Wextra -Werror \
  "$root/probes/cci_sdl_offscreen_gl_audio_probe.c" \
  "${sdl_cflags[@]}" "${sdl_libs[@]}" \
  -lm -ldl -lpthread \
  -o "$install_root/bin/cci-sdl-offscreen-probe"
strip --strip-unneeded "$install_root/bin/cci-sdl-offscreen-probe"

find "$install_root" -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$root/locks/capture-$short_commit-aarch64.sha256"

for binary in "$install_root/bin/"*; do
  file "$binary"
  ldd "$binary" 2>&1 || true
done
cat "$root/locks/capture-$short_commit-aarch64.sha256"
printf 'install_root=%s\n' "$install_root"
printf 'source_commit=%s\n' "$commit"
