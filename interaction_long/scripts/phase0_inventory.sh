#!/usr/bin/env bash
set -uo pipefail

section() {
  printf '\n[%s]\n' "$1"
}

run_optional() {
  local label=$1
  shift
  section "$label"
  "$@" 2>&1
  local rc=$?
  printf 'exit_code=%d\n' "$rc"
  return 0
}

printf 'inventory_utc=%s\n' "$(date -u +%FT%TZ)"
printf 'hostname=%s\n' "local"

run_optional identity id
run_optional os_release sh -c 'test -r /etc/os-release && sed -n "1,200p" /etc/os-release'
run_optional kernel uname -a
run_optional architecture uname -m
run_optional cpu lscpu
run_optional memory free -h
run_optional numa numactl --hardware
run_optional filesystems df -hT / ./tmp .
run_optional mounts findmnt -T . -o TARGET,SOURCE,FSTYPE,OPTIONS
run_optional tmp_mount findmnt -T ./tmp -o TARGET,SOURCE,FSTYPE,OPTIONS

run_optional gpu_summary nvidia-smi
run_optional gpu_query nvidia-smi --query-gpu=index,uuid,name,pci.bus_id,memory.total,memory.free,driver_version,pstate,utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv
run_optional gpu_full nvidia-smi -q
run_optional nvidia_devices sh -c 'find /dev -maxdepth 2 \( -name "nvidia*" -o -name "dri" -o -path "/dev/dri/*" \) -printf "%M %u %g %t:%T %p\n" | sort'
run_optional nvidia_modules sh -c 'lsmod | rg "^(nvidia|drm)" || true'
run_optional nvidia_proc_driver sh -c 'find /proc/driver/nvidia -maxdepth 3 -type f -print -exec sed -n "1,120p" {} \; 2>/dev/null'

section graphics_environment
printf 'DISPLAY=%q\n' "${DISPLAY-}"
printf 'WAYLAND_DISPLAY=%q\n' "${WAYLAND_DISPLAY-}"
printf 'XDG_RUNTIME_DIR=%q\n' "${XDG_RUNTIME_DIR-}"
printf 'SDL_VIDEODRIVER=%q\n' "${SDL_VIDEODRIVER-}"
printf 'SDL_AUDIODRIVER=%q\n' "${SDL_AUDIODRIVER-}"
printf '__GLX_VENDOR_LIBRARY_NAME=%q\n' "${__GLX_VENDOR_LIBRARY_NAME-}"
printf '__EGL_VENDOR_LIBRARY_FILENAMES=%q\n' "${__EGL_VENDOR_LIBRARY_FILENAMES-}"
printf 'LD_LIBRARY_PATH=%q\n' "${LD_LIBRARY_PATH-}"

run_optional display_processes sh -c 'ps -eo pid,ppid,user,stat,comm,args | rg "(Xorg|Xwayland|weston|wayland|pulseaudio|pipewire)" || true'
run_optional ldconfig_gl_egl sh -c 'ldconfig -p | rg -i "(libGLX|libOpenGL|libEGL|libGLES|libGL\\.so|libnvidia-egl|libnvidia-gl|libSDL2|libasound|libpulse|libvorbis|libogg)" || true'
run_optional glvnd_egl_vendor_files sh -c 'find /usr/share/glvnd /etc/glvnd -maxdepth 4 -type f -print -exec sed -n "1,160p" {} \; 2>/dev/null'
run_optional eglinfo_client_extensions eglinfo
run_optional glxinfo glxinfo -B
run_optional vulkaninfo_summary vulkaninfo --summary

run_optional audio_devices sh -c 'find /dev/snd -maxdepth 2 -printf "%M %u %g %t:%T %p\n" 2>/dev/null | sort'
run_optional alsa_cards sh -c 'test -r /proc/asound/cards && sed -n "1,160p" /proc/asound/cards'
run_optional sdl2_version sdl2-config --version
run_optional sdl2_drivers sh -c 'command -v SDL2 >/dev/null && SDL2 2>&1 || true'

run_optional ffmpeg_version ffmpeg -version
run_optional ffmpeg_h264_flac sh -c 'ffmpeg -hide_banner -encoders 2>&1 | rg -i "(libx264|nvenc|flac)" || true'
run_optional ffmpeg_buildconf ffmpeg -buildconf
run_optional x264_version x264 --version
run_optional flac_version flac --version

run_optional gcc_version gcc --version
run_optional gxx_version g++ --version
run_optional clang_version clang --version
run_optional make_version make --version
run_optional cmake_version cmake --version
run_optional ninja_version ninja --version
run_optional binutils_version ld --version
run_optional pkg_config_version pkg-config --version
run_optional git_version git --version
run_optional python_system python3 --version
run_optional conda_version ./environment --version

run_optional dpkg_packages sh -c 'command -v dpkg-query >/dev/null && dpkg-query -W -f="${binary:Package}\t${Version}\n" | sort'
run_optional rpm_packages sh -c 'command -v rpm >/dev/null && rpm -qa --qf "%{NAME}\t%{VERSION}-%{RELEASE}.%{ARCH}\n" | sort'
run_optional limits sh -c 'ulimit -a'
run_optional processes ps -eo pid,ppid,user,stat,etimes,%cpu,%mem,comm,args --sort=-%cpu

printf '\ninventory_complete_utc=%s\n' "$(date -u +%FT%TZ)"

