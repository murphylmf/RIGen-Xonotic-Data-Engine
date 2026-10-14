#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
tmp_root=${XONOTIC_CAPTURE_TMP:-./tmp/xonotic_capture}
deb_cache="$root/source/build-debs"
sysroot="$tmp_root/build/sysroot"

packages=(
  libsdl2-2.0-0
  libsdl2-dev
  libegl-dev
  libgl-dev
  libgles-dev
  libglvnd-core-dev
  libglvnd-dev
  libglx-dev
  libopengl-dev
  mesa-utils-bin
)

mkdir -p "$deb_cache" "$sysroot"

for package in "${packages[@]}"; do
  version=$(apt-cache policy "$package" | awk '/Candidate:/ {print $2; exit}')
  if [[ -z "$version" || "$version" == "(none)" ]]; then
    printf 'missing_candidate package=%s\n' "$package" >&2
    exit 65
  fi
  printf 'package=%s candidate=%s\n' "$package" "$version"
  if ! compgen -G "$deb_cache/${package}_*.deb" >/dev/null; then
    (
      cd "$deb_cache"
      apt-get download "${package}=${version}"
    )
  fi
done

for deb in "$deb_cache"/*.deb; do
  printf 'extract=%s\n' "$deb"
  dpkg-deb --extract "$deb" "$sysroot"
done

libdir="$sysroot/usr/lib/aarch64-linux-gnu"
mkdir -p "$libdir"
ln -sfn /usr/lib/aarch64-linux-gnu/libSDL2-2.0.so.0 "$libdir/libSDL2.so"
ln -sfn /usr/lib/aarch64-linux-gnu/libEGL.so.1 "$libdir/libEGL.so"
ln -sfn /usr/lib/aarch64-linux-gnu/libGL.so.1 "$libdir/libGL.so"
ln -sfn /usr/lib/aarch64-linux-gnu/libGLX.so.0 "$libdir/libGLX.so"

sha256sum "$deb_cache"/*.deb
printf 'sysroot=%s\n' "$sysroot"
printf 'sysroot_ready_utc=%s\n' "$(date -u +%FT%TZ)"
