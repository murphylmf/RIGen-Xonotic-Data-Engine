#!/usr/bin/env bash

set -euo pipefail
_script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
_root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$_script_dir/.." && pwd -P)}
_machine_arch=$(uname -m)
case "$_machine_arch" in
  amd64) _machine_arch=x86_64 ;;
  arm64) _machine_arch=aarch64 ;;
  x86_64|aarch64) ;;
  *)
    echo "unsupported architecture: $_machine_arch" >&2
    return 78 2>/dev/null || exit 78
    ;;
esac




_archive=${XONOTIC_ENV_ARCHIVE:-}
if [[ -z "$_archive" ]]; then
  _archive=$(find "$_root/env" -maxdepth 1 -type f \
    -name "xonotic-capture-linux-${_machine_arch}-*.tar.gz" \
    -printf '%T@ %p\n' 2>/dev/null |
    sort -nr | awk 'NR==1 {$1=""; sub(/^ /,""); print}')
fi
_env_source=
if [[ -n "$_archive" && -r "$_archive" && -r "${_archive}.sha256" ]]; then
  _sha_file="${_archive}.sha256"
  _expected=$(awk 'NR==1 {print $1}' "$_sha_file")
  [[ $_expected =~ ^[0-9a-f]{64}$ ]] || {
    echo "invalid environment digest" >&2
    return 65 2>/dev/null || exit 65
  }
  _cache_root=${XONOTIC_NODE_CACHE_ROOT:-./tmp/xonotic-node-cache-$(id -u)}
  _env_dir="$_cache_root/env-$_expected"
  _lock="$_cache_root/env-$_expected.lock"
  mkdir -p -m 700 "$_cache_root"
  exec 9>"$_lock"
  flock 9
  if [[ ! -f "$_env_dir/.xonotic-env-ready" ]] ||
     [[ $(<"$_env_dir/.xonotic-env-ready") != "$_expected" ]]; then
    case "$_env_dir" in
      "$_cache_root"/env-*) ;;
      *)
        echo "unsafe cache target" >&2
        return 70 2>/dev/null || exit 70
        ;;
    esac
    [[ ! -e "$_env_dir" ]] || rm -rf -- "$_env_dir"
    _staging="$_env_dir.partial.$$"
    rm -rf -- "$_staging"
    mkdir -p "$_staging"
    printf '%s  %s\n' "$_expected" "$_archive" | sha256sum -c -
    tar -xzf "$_archive" -C "$_staging"
    "$_staging/bin/conda-unpack"
    printf '%s\n' "$_expected" > "$_staging/.xonotic-env-ready"
    mv "$_staging" "$_env_dir"
  fi
  flock -u 9
  exec 9>&-
  _env_source=portable_archive
else
  _env_dir=${XONOTIC_CONDA_PREFIX_REQUIRED:-$(dirname "$_root")/miniconda3/envs/xonotic-capture}
  [[ -x "$_env_dir/bin/python" ]] || {
    echo "no ${_machine_arch} portable archive and existing conda environment missing: $_env_dir" >&2
    return 66 2>/dev/null || exit 66
  }
  _env_source=existing_conda
fi
_requested_build=${XONOTIC_BUILD_GLOB:-}
if [[ -n "$_requested_build" && "$_requested_build" != *'*'* &&
      "$_requested_build" != *'?'* &&
      "$_requested_build" != /* &&
      "$_requested_build" != *'..'* ]]; then
  _build="$_root/$_requested_build"
else
  _build=$(find "$_root/build" -maxdepth 1 -type d \
    -name "capture-*-${_machine_arch}" -printf '%T@ %p\n' |
    sort -nr | awk 'NR==1 {$1=""; sub(/^ /,""); print}')
fi
[[ -n "$_build" && -x "$_build/bin/xonotic-local-sdl" ]] || {
  echo "${_machine_arch} capture build missing" >&2
  return 66 2>/dev/null || exit 66
}
_driver_version=580.95.05
_nvidia_runtime="$_root/runtime/nvidia/$_driver_version"
_host_driver=
if command -v nvidia-smi >/dev/null 2>&1; then
  _host_driver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | sort -u || true)
fi
_runtime_ld=
export XONOTIC_NVIDIA_RUNTIME_STATUS=unavailable
if [[ $_machine_arch == x86_64 &&
   $_host_driver == "$_driver_version" ]] &&
   [[ -r "$_nvidia_runtime/lib/libEGL.so.1" ]] &&
   [[ -r "$_nvidia_runtime/lib/libGLdispatch.so.0" ]] &&
   [[ -r "$_nvidia_runtime/lib/libEGL_nvidia.so.0" ]] &&
   [[ -r "$_nvidia_runtime/egl_vendor.d/10_nvidia.json" ]]; then
  _runtime_ld="$_nvidia_runtime/lib:"
  export XONOTIC_NVIDIA_DRIVER_RUNTIME="$_nvidia_runtime"
  export XONOTIC_NVIDIA_RUNTIME_STATUS=ready
  export __EGL_VENDOR_LIBRARY_FILENAMES="$_nvidia_runtime/egl_vendor.d/10_nvidia.json"
  export __GLX_VENDOR_LIBRARY_NAME=nvidia
  export SDL_VIDEO_EGL_DRIVER="$_nvidia_runtime/lib/libEGL.so.1"
elif [[ -n "$_host_driver" ]]; then


  export XONOTIC_NVIDIA_RUNTIME_STATUS=host
fi
export XONOTIC_CAPTURE_ROOT="$_root"
export XONOTIC_CAPTURE_TMP=${XONOTIC_CAPTURE_TMP:-${TMPDIR:-./tmp}/xonotic_capture/${SLURM_JOB_ID:-${JOB_ID:-manual}}-$$}
export XONOTIC_BUILD_GLOB="build/$(basename "$_build")"
export XONOTIC_CONDA_PREFIX_REQUIRED="$_env_dir"
export CONDA_PREFIX="$_env_dir"
export CONDA_DEFAULT_ENV=xonotic-capture
export PATH="$_env_dir/bin:$PATH"
export LD_LIBRARY_PATH="${_runtime_ld}$_build/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER=${SDL_VIDEODRIVER:-offscreen}
export SDL_AUDIODRIVER=${SDL_AUDIODRIVER:-dummy}
export SDL_RENDER_DRIVER=${SDL_RENDER_DRIVER:-opengl}
export PYTHONNOUSERSITE=1
mkdir -p "$XONOTIC_CAPTURE_TMP"
unset _script_dir _root _archive _sha_file _expected _cache_root _env_dir _lock _staging _build _requested_build
unset _driver_version _nvidia_runtime _host_driver _runtime_ld
if [[ ${XONOTIC_BOOTSTRAP_QUIET:-0} != 1 ]]; then
  echo "xonotic_node_environment=ready"
  echo "xonotic_node_architecture=$_machine_arch"
  echo "xonotic_environment_source=$_env_source"
  echo "nvidia_egl_runtime=$XONOTIC_NVIDIA_RUNTIME_STATUS"
  echo "xonotic_tmp=$XONOTIC_CAPTURE_TMP"
fi
unset _machine_arch _env_source
