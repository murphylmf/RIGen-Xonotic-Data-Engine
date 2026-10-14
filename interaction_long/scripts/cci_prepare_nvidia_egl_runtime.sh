#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
driver_version=580.95.05
archive_name="NVIDIA-Linux-x86_64-$driver_version-no-compat32.run"
archive="$root/assets/upstream/$archive_name"
archive_sha256=482130b27454864f3873729debbffa9e317badd1c56271dd811219c2385da575
source_url="https://download.nvidia.com/XFree86/Linux-x86_64/$driver_version/$archive_name"
runtime_root="$root/runtime/nvidia/$driver_version"
glvnd_asset_root="$root/assets/upstream/glvnd-ubuntu22.04-x86_64-1.4.0-1"
glvnd_egl_sha256=69816a7062d7d624144472f5ef71f5b23732b9003df7472662920602e62805db
glvnd_dispatch_sha256=a4f2642498fba54d2f39e90ca3daa94340cdd52198473185a5285608ae318cb6

[[ $(uname -m) == x86_64 ]] || {
  echo "native architecture gate failed: $(uname -m)" >&2
  exit 78
}
host_driver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader |
  sort -u)
[[ "$host_driver" == "$driver_version" ]] || {
  echo "host_driver=$host_driver" >&2
  echo "expected_driver=$driver_version" >&2
  exit 78
}

nvidia_files=(
  libEGL_nvidia.so.580.95.05
  libGLX_nvidia.so.580.95.05
  libnvidia-allocator.so.580.95.05
  libnvidia-eglcore.so.580.95.05
  libnvidia-glcore.so.580.95.05
  libnvidia-glsi.so.580.95.05
  libnvidia-glvkspirv.so.580.95.05
  libnvidia-gpucomp.so.580.95.05
  libnvidia-tls.so.580.95.05
  libnvidia-egl-gbm.so.1.1.2
  libnvidia-egl-wayland.so.1.1.20
  libnvidia-egl-xcb.so.1.0.3
  libnvidia-egl-xlib.so.1.0.3
)
glvnd_files=(
  libEGL.so.1.1.0
  libGLdispatch.so.0.0.0
)
required_files=("${nvidia_files[@]}" "${glvnd_files[@]}")
printf '%s  %s\n' "$glvnd_egl_sha256" \
  "$glvnd_asset_root/libEGL.so.1.1.0" | sha256sum -c -
printf '%s  %s\n' "$glvnd_dispatch_sha256" \
  "$glvnd_asset_root/libGLdispatch.so.0.0.0" | sha256sum -c -
[[ -r "$glvnd_asset_root/COPYRIGHT" &&
   -r "$glvnd_asset_root/PROVENANCE.txt" ]] || {
  echo "portable GLVND provenance is missing" >&2
  exit 66
}

if [[ -f "$runtime_root/DRIVER_VERSION" ]] &&
   [[ $(<"$runtime_root/DRIVER_VERSION") == "$driver_version" ]]; then
  for file in "${required_files[@]}"; do
    [[ -r "$runtime_root/lib/$file" ]] || {
      echo "existing runtime is incomplete: $runtime_root/lib/$file" >&2
      exit 73
    }
  done
  [[ -r "$runtime_root/GLVND_COPYRIGHT" &&
     -r "$runtime_root/GLVND_PROVENANCE.txt" ]] || {
    echo "existing runtime is missing GLVND provenance" >&2
    exit 73
  }
  echo "nvidia_egl_runtime=already_ready"
  echo "runtime_root=$runtime_root"
  exit 0
fi
[[ ! -e "$runtime_root" ]] || {
  echo "refusing to overwrite incomplete runtime: $runtime_root" >&2
  exit 73
}

if [[ -r ./ ]]; then

  source ./
fi
mkdir -p "$root/assets/upstream" "$root/runtime/nvidia"
if [[ ! -f "$archive" ]] ||
   ! printf '%s  %s\n' "$archive_sha256" "$archive" |
     sha256sum -c - >/dev/null 2>&1; then
  curl -fL --retry 5 --retry-all-errors \
    -o "$archive.partial" "$source_url"
  mv "$archive.partial" "$archive"
fi
printf '%s  %s\n' "$archive_sha256" "$archive" | sha256sum -c -
chmod 644 "$archive"

work_root=$(mktemp -d "${TMPDIR:-./tmp}/nvidia-egl-runtime.XXXXXXXX")
staging="$root/runtime/nvidia/.$driver_version.partial.$$"
cleanup() {
  case "$work_root" in
    "${TMPDIR:-./tmp}"/nvidia-egl-runtime.*) rm -rf -- "$work_root" ;;
  esac
  case "$staging" in
    "$root"/runtime/nvidia/."$driver_version".partial.*)
      [[ ! -e "$staging" ]] || rm -rf -- "$staging"
      ;;
  esac
  if [[ -n ${manifest_tmp:-} && -e ${manifest_tmp:-} ]]; then
    case "$manifest_tmp" in
      "$root"/runtime/nvidia/."$driver_version".manifest.*)
        rm -f -- "$manifest_tmp"
        ;;
    esac
  fi
}
trap cleanup EXIT

extract="$work_root/extracted"
sh "$archive" --extract-only --target "$extract"
mkdir -p "$staging/lib" "$staging/egl_vendor.d"
for file in "${nvidia_files[@]}"; do
  install -m 755 "$extract/$file" "$staging/lib/$file"
done
for file in "${glvnd_files[@]}"; do
  install -m 755 "$glvnd_asset_root/$file" "$staging/lib/$file"
done
install -m 644 "$extract/10_nvidia.json" \
  "$staging/egl_vendor.d/10_nvidia.json"
install -m 644 "$extract/LICENSE" "$staging/LICENSE"
install -m 644 "$extract/.manifest" "$staging/NVIDIA_INSTALLER_MANIFEST"
install -m 644 "$glvnd_asset_root/COPYRIGHT" \
  "$staging/GLVND_COPYRIGHT"
install -m 644 "$glvnd_asset_root/PROVENANCE.txt" \
  "$staging/GLVND_PROVENANCE.txt"

(
  cd "$staging/lib"
  ln -s libEGL.so.1.1.0 libEGL.so.1
  ln -s libEGL.so.1 libEGL.so
  ln -s libGLdispatch.so.0.0.0 libGLdispatch.so.0
  ln -s libEGL_nvidia.so.580.95.05 libEGL_nvidia.so.0
  ln -s libGLX_nvidia.so.580.95.05 libGLX_nvidia.so.0
  ln -s libGLX_nvidia.so.580.95.05 libGLX_indirect.so.0
  ln -s libnvidia-allocator.so.580.95.05 libnvidia-allocator.so.1
  ln -s libnvidia-allocator.so.1 libnvidia-allocator.so
  ln -s libnvidia-egl-gbm.so.1.1.2 libnvidia-egl-gbm.so.1
  ln -s libnvidia-egl-wayland.so.1.1.20 libnvidia-egl-wayland.so.1
  ln -s libnvidia-egl-xcb.so.1.0.3 libnvidia-egl-xcb.so.1
  ln -s libnvidia-egl-xlib.so.1.0.3 libnvidia-egl-xlib.so.1
)
printf '%s\n' "$driver_version" > "$staging/DRIVER_VERSION"
printf '%s\n' "$source_url" > "$staging/SOURCE_URL"
printf '%s\n' "$archive_sha256" > "$staging/SOURCE_SHA256"
chmod 644 "$staging/DRIVER_VERSION" "$staging/SOURCE_URL" \
  "$staging/SOURCE_SHA256"

mv "$staging" "$runtime_root"
manifest_tmp="$root/runtime/nvidia/.$driver_version.manifest.$$"
find "$runtime_root" -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$manifest_tmp"
mv "$manifest_tmp" "$runtime_root/MANIFEST.sha256"
chmod 644 "$runtime_root/MANIFEST.sha256"
sha256sum -c "$runtime_root/MANIFEST.sha256"
echo "nvidia_egl_runtime=ready"
echo "runtime_root=$runtime_root"
