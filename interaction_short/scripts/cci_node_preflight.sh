#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
source "$script_dir/cci_node_bootstrap.sh"
build="$XONOTIC_CAPTURE_ROOT/$XONOTIC_BUILD_GLOB"
python -c 'import numpy,pandas,pyarrow,scipy,soundfile,psutil,yaml,jsonschema; print("python_stack=ok")'
[[ -f "$build/SDL_VERSION" ]] || {
  echo "capture_build_sdl_version=missing" >&2
  exit 78
}
echo "capture_build_sdl_version=$(<"$build/SDL_VERSION")"
if [[ -r "$build/lib/libSDL2-2.0.so.0" ]]; then
  sdl_strings=$(strings "$build/lib/libSDL2-2.0.so.0")
  grep -F 'SDL offscreen video driver' <<<"$sdl_strings" >/dev/null || {
    echo "bundled_sdl_offscreen=missing" >&2
    exit 78
  }
  unset sdl_strings
  echo "sdl_runtime=bundled_offscreen"
else
  echo "sdl_runtime=host"
fi
ldd_report="$XONOTIC_CAPTURE_TMP/ldd-preflight.txt"
ldd "$build/bin/xonotic-local-sdl" | tee "$ldd_report"
! grep -q 'not found' "$ldd_report" || { echo "binary_dependency=missing" >&2; exit 78; }
unset ldd_report
ffmpeg_encoders=$(ffmpeg -hide_banner -encoders 2>/dev/null)
grep -F 'libx264' <<<"$ffmpeg_encoders" >/dev/null || { echo "ffmpeg_libx264=missing" >&2; exit 78; }
grep -F ' flac ' <<<"$ffmpeg_encoders" >/dev/null || { echo "ffmpeg_flac=missing" >&2; exit 78; }
unset ffmpeg_encoders
gpu_rows=$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader)
echo "$gpu_rows"
driver_versions=$(cut -d, -f2 <<<"$gpu_rows" | sed 's/^ *//' | sort -u)
[[ -n "$driver_versions" ]] || {
  echo "nvidia_driver_version=missing" >&2
  exit 78
}
[[ ${XONOTIC_NVIDIA_RUNTIME_STATUS:-} == ready ||
   ${XONOTIC_NVIDIA_RUNTIME_STATUS:-} == host ]] || {
  echo "nvidia_egl_runtime=unavailable" >&2
  exit 78
}
if [[ ${XONOTIC_NVIDIA_RUNTIME_STATUS:-} == ready ]]; then
  nvidia_runtime=${XONOTIC_NVIDIA_DRIVER_RUNTIME:?}
  [[ -r "$nvidia_runtime/lib/libEGL.so.1" ]] || {
    echo "glvnd_egl_loader=missing" >&2
    exit 78
  }
  [[ -r "$nvidia_runtime/lib/libGLdispatch.so.0" ]] || {
    echo "glvnd_dispatch_library=missing" >&2
    exit 78
  }
  [[ -r "$nvidia_runtime/lib/libEGL_nvidia.so.0" ]] || {
    echo "nvidia_egl_library=missing" >&2
    exit 78
  }
  [[ -r "$nvidia_runtime/egl_vendor.d/10_nvidia.json" ]] || {
    echo "nvidia_egl_vendor_manifest=missing" >&2
    exit 78
  }
  if [[ ${XONOTIC_VERIFY_NVIDIA_RUNTIME:-0} == 1 ]]; then
    sha256sum -c "$nvidia_runtime/MANIFEST.sha256"
  fi
  egl_loader_dependencies=$(ldd "$nvidia_runtime/lib/libEGL.so.1")
  echo "$egl_loader_dependencies"
  ! grep -q 'not found' <<<"$egl_loader_dependencies" || {
    echo "glvnd_egl_loader_dependencies=missing" >&2
    exit 78
  }
  unset egl_loader_dependencies
  echo "egl_client_loader=$SDL_VIDEO_EGL_DRIVER"
  echo "nvidia_egl_source=shared-driver-runtime"
else
  echo "nvidia_egl_source=host-driver-runtime"
fi
SDL_VIDEODRIVER=offscreen \
SDL_AUDIODRIVER=dummy \
SDL_RENDER_DRIVER=opengl \
  "$build/bin/cci-sdl-offscreen-probe" || {
    echo "hardware_sdl_egl_probe=failed" >&2
    exit 78
  }
echo "node_preflight=pass"
