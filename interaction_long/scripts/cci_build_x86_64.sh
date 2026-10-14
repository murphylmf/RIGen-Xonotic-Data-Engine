#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
worktree="$root/source/release-src-0.8.6/Xonotic"
jobs=${XONOTIC_BUILD_JOBS:-16}
sdl_version=2.30.0
sdl_archive="$root/assets/upstream/SDL2-$sdl_version.tar.gz"
sdl_sha256=36e2e41557e0fa4a1519315c0f5958a87ccb27e25c51776beb6f1239526447b0

[[ $(uname -m) == x86_64 ]] || {
  echo "native architecture gate failed: $(uname -m)" >&2
  exit 78
}
[[ -d "$worktree/.git" || -f "$worktree/.git" ]] || {
  echo "source worktree missing: $worktree" >&2
  exit 66
}
[[ -r "$sdl_archive" ]] || {
  echo "SDL source archive missing: $sdl_archive" >&2
  exit 66
}
printf '%s  %s\n' "$sdl_sha256" "$sdl_archive" | sha256sum -c -
git -C "$worktree" diff --quiet
git -C "$worktree" diff --cached --quiet

commit=$(git -C "$worktree" rev-parse HEAD)
short_commit=${commit:0:12}
final_install_root="$root/build/capture-$short_commit-x86_64"
if [[ -e "$final_install_root" ]]; then
  if [[ ${XONOTIC_REPLACE_BUILD:-0} != 1 ]]; then
    echo "build already exists: $final_install_root" >&2
    echo "set XONOTIC_REPLACE_BUILD=1 to move it aside and rebuild" >&2
    exit 73
  fi
  backup="$root/build/runtime-backups/capture-$short_commit-x86_64.$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$(dirname "$backup")"
  mv "$final_install_root" "$backup"
  echo "previous_build=$backup"
fi

work_root=$(mktemp -d "${TMPDIR:-./tmp}/xonotic-x86-build.XXXXXXXX")
cleanup() {
  case "$work_root" in
    "${TMPDIR:-./tmp}"/xonotic-x86-build.*) rm -rf -- "$work_root" ;;
  esac
  if [[ -n ${shared_staging:-} && -e ${shared_staging:-} ]]; then
    case "$shared_staging" in
      "$root"/build/.capture-"$short_commit"-x86_64.partial.*)
        rm -rf -- "$shared_staging"
        ;;
    esac
  fi
}
trap cleanup EXIT

source_root="$work_root/Xonotic"
qc_out="$work_root/qc"
qc_work=".capture-qc-work-$short_commit"
sdl_source="$work_root/SDL2-$sdl_version"
sdl_prefix="$work_root/sdl-prefix"
install_root="$work_root/install"

mkdir -p "$source_root" "$qc_out"
git -C "$worktree" archive --format=tar "$commit" | tar -xf - -C "$source_root"

(
  cd "$source_root"
  make -j"$jobs" both \
    CFLAGS='-pipe -march=x86-64-v2 -mtune=generic -flto=auto'
)

make -C "$source_root/source/gmqcc" -j"$jobs" CXX=g++ gmqcc qcvm
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

tar -xzf "$sdl_archive" -C "$work_root"
(
  cd "$sdl_source"
  ./configure \
    --prefix="$sdl_prefix" \
    --enable-shared \
    --disable-static \
    --enable-video-offscreen \
    --enable-video-opengl \
    --disable-video-opengles \
    --disable-video-x11 \
    --disable-video-wayland \
    --disable-video-kmsdrm \
    --disable-video-vulkan \
    --enable-video-dummy \
    --disable-alsa \
    --disable-pulseaudio \
    --disable-pipewire \
    --disable-jack \
    --disable-sndio \
    --disable-libudev \
    --disable-hidapi \
    --disable-joystick \
    --disable-haptic \
    --disable-sensor
  make -j"$jobs"
  make install
)

mkdir -p "$install_root/bin" "$install_root/lib" "$install_root/qc"
install -m 755 "$source_root/xonotic-local-sdl" "$install_root/bin/"
install -m 755 "$source_root/xonotic-local-dedicated" "$install_root/bin/"
install -m 755 "$source_root/source/gmqcc/gmqcc" "$install_root/bin/"
install -m 755 "$source_root/source/gmqcc/qcvm" "$install_root/bin/"
install -m 644 "$qc_out/csprogs.dat" "$qc_out/menu.dat" "$qc_out/progs.dat" \
  "$install_root/qc/"

for soname in libz.so.1 libjpeg.so.8 libgmp.so.10; do
  library=$(ldd "$install_root/bin/xonotic-local-sdl" |
    awk -v name="$soname" '$1 == name {print $3}')
  [[ -r "$library" ]] || {
    echo "runtime library not found: $soname" >&2
    exit 66
  }
  install -m 755 "$library" "$install_root/lib/$soname"
done

install -m 755 "$sdl_prefix/lib/libSDL2-2.0.so.0.3000.0" \
  "$install_root/lib/libSDL2-2.0.so.0"
strip --strip-unneeded "$install_root/lib/libSDL2-2.0.so.0"
printf '%s\n' "$sdl_version" > "$install_root/SDL_VERSION"
printf '%s\n' "$commit" > "$install_root/SOURCE_COMMIT"

for binary in \
  "$install_root/bin/xonotic-local-sdl" \
  "$install_root/bin/xonotic-local-dedicated"; do
  patchelf --set-rpath '$ORIGIN/../lib' "$binary"
done

gcc -O2 -Wall -Wextra -Werror \
  "$root/probes/cci_sdl_offscreen_gl_audio_probe.c" \
  -I"$sdl_prefix/include/SDL2" \
  -D_REENTRANT \
  -L"$install_root/lib" \
  -Wl,-rpath,'$ORIGIN/../lib' \
  -lSDL2 -lm -ldl -lpthread \
  -o "$install_root/bin/cci-sdl-offscreen-probe"
strip --strip-unneeded "$install_root/bin/cci-sdl-offscreen-probe"

shared_staging="$root/build/.capture-$short_commit-x86_64.partial.$$"
[[ ! -e "$shared_staging" ]]
mkdir -p "$shared_staging"
tar -cf - -C "$install_root" . |
  tar --no-same-owner -xf - -C "$shared_staging"
mv "$shared_staging" "$final_install_root"
install_root="$final_install_root"
manifest="$root/locks/capture-$short_commit-x86_64.sha256"
find "$install_root" -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$manifest.partial"
mv "$manifest.partial" "$manifest"
chmod 644 "$manifest"
sha256sum -c "$manifest"

for binary in "$install_root/bin/"*; do
  file "$binary"
  ldd "$binary" 2>&1 || true
done
echo "install_root=$install_root"
echo "source_commit=$commit"
echo "sdl_version=$sdl_version"
