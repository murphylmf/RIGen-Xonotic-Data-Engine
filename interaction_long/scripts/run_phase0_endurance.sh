#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
duration=${1:-}
case "$duration" in
  60|600) ;;
  *) printf 'usage: %s 60|600\n' "$0" >&2; exit 64 ;;
esac

run_id="phase0-${duration}s"
run_root="$root/raw/phase0/$run_id"
result_root="$root/phase0/av-tests/$run_id"
userdir="$run_root/client_user"
server_user="$run_root/server_user"
video_dir="$userdir/data/video"
telemetry_dir="$run_root/telemetry"
expected_frames=$((duration * 64))
expected_samples=$((duration * 48000))

if [[ -e "$run_root" || -e "$result_root" ]]; then
  printf 'refusing to overwrite existing endurance run: %s or %s\n' \
    "$run_root" "$result_root" >&2
  exit 73
fi

build=$(find "$root/build" -maxdepth 1 -type d -name 'capture-*-aarch64' \
  -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-)
binary="$build/bin/xonotic-local-sdl"
dedicated="$build/bin/xonotic-local-dedicated"
[[ -x "$binary" ]] || {
  printf 'missing capture client under build %s\n' "$build" >&2
  exit 66
}
[[ -x "$dedicated" ]] || {
  printf 'missing dedicated server under build %s\n' "$build" >&2
  exit 66
}

mkdir -p "$video_dir" "$server_user/data" "$telemetry_dir" "$result_root"
cp "$root/configs/capture_client.cfg" "$userdir/data/capture_client.cfg"
cp "$root/configs/capture_server.cfg" "$server_user/data/capture_server.cfg"
for target in "$userdir/data" "$server_user/data"; do
  cp "$build/qc/progs.dat" "$build/qc/csprogs.dat" "$build/qc/menu.dat" \
    "$target/"
done

engine_log="$result_root/engine.log"
server_log="$result_root/server.log"
metrics="$result_root/runtime_metrics.csv"
printf '%s\n' \
  'timestamp_utc,gpu_util_pct,gpu_memory_util_pct,gpu_memory_mib,power_w,engine_cpu_pct,engine_rss_kib,raw_bytes' \
  > "$metrics"

export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export LC_ALL=C

engine_pid=
server_pid=
cleanup() {
  if [[ -n "$engine_pid" ]] && kill -0 "$engine_pid" 2>/dev/null; then
    kill "$engine_pid" 2>/dev/null || true
    wait "$engine_pid" 2>/dev/null || true
  fi
  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

port=$(
  ./environment -c \
    'import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()'
)
"$dedicated" \
  -xonotic -nocdaudio \
  -basedir "$root/assets/release-0.8.6/Xonotic" \
  -userdir "$server_user" \
  +exec capture_server.cfg \
  +set port "$port" \
  +set g_use_ammunition 0 \
  +map stormkeep \
  > "$server_log" 2>&1 &
server_pid=$!
server_ready=0
for _ in $(seq 1 300); do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    printf 'dedicated server exited before readiness: %s\n' "$server_log" >&2
    exit 70
  fi
  if grep -Eq 'Server listening|IP address|Loaded maps/' "$server_log"; then
    server_ready=1
    break
  fi
  sleep 0.1
done
if ((server_ready == 0)); then
  printf 'dedicated server readiness timeout: %s\n' "$server_log" >&2
  exit 70
fi

"$binary" \
  -xonotic -nocdaudio \
  -basedir "$root/assets/release-0.8.6/Xonotic" \
  -userdir "$userdir" \
  -window -width 1280 -height 720 \
  -sndspeed 48000 -sndbits 16 -sndstereo \
  +exec capture_client.cfg \
  +capture_enable 1 \
  +capture_mode 1 \
  +capture_log_dir "$telemetry_dir" \
  +capture_expected_frames "$expected_frames" \
  +capture_quit_on_end 1 \
  +cl_capturevideo_nameformat "${run_id}_" \
  +connect "127.0.0.1:$port" \
  +defer 25 "cmd join; cmd god; -forward; -back; -moveleft; -moveright; +attack; capture_episode_reset $run_id; capture_output_begin" \
  > "$engine_log" 2>&1 &
engine_pid=$!

(
  while kill -0 "$engine_pid" 2>/dev/null; do
    gpu=$(nvidia-smi \
      --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,power.draw \
      --format=csv,noheader,nounits 2>/dev/null | head -n 1 || true)
    cpu=$(ps -p "$engine_pid" -o %cpu=,rss= 2>/dev/null | xargs || true)
    raw_bytes=$(find "$video_dir" -maxdepth 1 -type f -printf '%s\n' \
      2>/dev/null | awk '{sum += $1} END {print sum + 0}')
    printf '%s,%s,%s\n' "$gpu" "${cpu// /,}" "$raw_bytes"
    sleep 1
  done
) >> "$metrics" &
monitor_pid=$!

deadline=$((duration * 10 + 600))
elapsed=0
while kill -0 "$engine_pid" 2>/dev/null; do
  if ((elapsed >= deadline)); then
    printf 'endurance engine exceeded deadline %d seconds\n' "$deadline" >&2
    exit 124
  fi
  sleep 1
  ((elapsed += 1))
done
set +e
wait "$engine_pid"
engine_rc=$?
set -e
wait "$monitor_pid" 2>/dev/null || true
if kill -0 "$server_pid" 2>/dev/null; then
  kill "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
fi
trap - EXIT
if ((engine_rc != 0)); then
  printf 'endurance engine failed: exit=%d log=%s\n' "$engine_rc" "$engine_log" >&2
  exit "$engine_rc"
fi

mapfile -t avis < <(
  find "$video_dir" -maxdepth 1 -type f -name "${run_id}_*.avi" -print | sort
)
if ((${#avis[@]} != 1)); then
  printf 'expected one raw AVI, found %d under %s\n' \
    "${#avis[@]}" "$video_dir" >&2
  exit 65
fi
raw_avi=${avis[0]}
frames_csv="$telemetry_dir/frames_engine.csv"
audio_csv="$telemetry_dir/audio_events_engine.csv"
actual_frame_rows=$(( $(wc -l < "$frames_csv") - 1 ))
if ((actual_frame_rows != expected_frames)); then
  printf 'frame telemetry mismatch expected=%d actual=%d\n' \
    "$expected_frames" "$actual_frame_rows" >&2
  exit 74
fi
audio_start=$(awk -F, 'NR == 2 {print $5; exit}' "$frames_csv")
encoded="$result_root/${run_id}.mkv"
encode_log="$result_root/ffmpeg_encode.log"

started_epoch=$(date +%s.%N)
ffmpeg -hide_banner -y -nostdin \
  -i "$raw_avi" \
  -map 0:v:0 -map 0:a:0 \
  -c:v libx264 -preset medium -profile:v high -crf 16 \
  -pix_fmt yuv420p -r 64 -fps_mode cfr \
  -g 64 -keyint_min 64 -sc_threshold 0 \
  -c:a flac \
  -af "atrim=start_sample=${audio_start}:end_sample=$((audio_start + expected_samples)),asetpts=PTS-STARTPTS" \
  -ar 48000 -ac 2 \
  "$encoded" > "$encode_log" 2>&1
finished_epoch=$(date +%s.%N)

ffprobe -v error -count_frames -show_streams -show_format -of json \
  "$raw_avi" > "$result_root/raw_ffprobe.json"
ffprobe -v error -count_frames -show_streams -show_format -of json \
  "$encoded" > "$result_root/encoded_ffprobe.json"

./environment \
  "$root/scripts/qa_phase0_endurance.py" \
  "$encoded" "$expected_frames" "$expected_samples" \
  "$started_epoch" "$finished_epoch" "$metrics" "$audio_csv" \
  "$result_root/qa.json" "$run_id" <<'PY'
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

(
    encoded_text,
    expected_frames_text,
    expected_samples_text,
    started_text,
    finished_text,
    metrics_text,
    audio_csv_text,
    root_text,
    run_id,
) = sys.argv[1:]
encoded = Path(encoded_text)
expected_frames = int(expected_frames_text)
expected_samples = int(expected_samples_text)
probe = json.loads(
    subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames",
            "-show_streams", "-show_format", "-of", "json", str(encoded),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
)
video = next(row for row in probe["streams"] if row["codec_type"] == "video")
audio = next(row for row in probe["streams"] if row["codec_type"] == "audio")
pcm = subprocess.run(
    [
        "ffmpeg", "-v", "error", "-nostdin", "-i", str(encoded),
        "-map", "0:a:0", "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "48000", "-ac", "2", "-",
    ],
    capture_output=True, check=True,
).stdout
samples = len(pcm) // 4
pcm_s16 = np.frombuffer(pcm, dtype="<i2")
peak_s16 = int(np.abs(pcm_s16.astype(np.int32)).max()) if pcm_s16.size else 0
metrics_rows = list(csv.DictReader(Path(metrics_text).open()))
raw_sizes = [int(float(row["raw_bytes"])) for row in metrics_rows if row["raw_bytes"]]
wall = float(finished_text) - float(started_text)
duration = expected_frames / 64.0
audio_duration = samples / 48000.0
forbidden_patterns = (
    "announcer/", "cdtracks/", "music/",
    "misc/itemrespawncountdown.wav", "misc/talk",
)
audio_rows = list(csv.DictReader(Path(audio_csv_text).open()))
forbidden = sorted(
    {
        row["sample_name"]
        for row in audio_rows
        if any(pattern in row["sample_name"].lower() for pattern in forbidden_patterns)
    }
)
qa = {
    "schema_version": "xonotic-phase0-endurance-v1",
    "run_id": run_id,
    "renderer_required": "NVIDIA hardware (exact device recorded at runtime)",
    "video_frames": int(video["nb_read_frames"]),
    "video_fps": video["avg_frame_rate"],
    "video_duration_seconds": duration,
    "audio_samples_per_channel": samples,
    "audio_duration_seconds": audio_duration,
    "audio_peak_s16": peak_s16,
    "av_drift_ms": abs(duration - audio_duration) * 1000.0,
    "encoded": {
        "video_codec": video["codec_name"],
        "profile": video["profile"],
        "pixel_format": video["pix_fmt"],
        "audio_codec": audio["codec_name"],
        "audio_sample_format": audio["sample_fmt"],
        "audio_sample_rate": int(audio["sample_rate"]),
        "audio_channels": int(audio["channels"]),
    },
    "audio_events": len(audio_rows),
    "forbidden_audio_samples": forbidden,
    "raw_bytes_final": max(raw_sizes) if raw_sizes else 0,
    "x264_wall_seconds": wall,
    "x264_video_seconds_per_wall_second": duration / wall,
    "gates": {
        "frames_exact": int(video["nb_read_frames"]) == expected_frames,
        "audio_samples_exact": samples == expected_samples,
        "av_drift_zero": abs(duration - audio_duration) < 1e-9,
        "h264_high_yuv420p_cfr64": (
            video["codec_name"] == "h264"
            and video["profile"] == "High"
            and video["pix_fmt"] == "yuv420p"
            and video["avg_frame_rate"] == "64/1"
        ),
        "flac_s16_stereo_48khz": (
            audio["codec_name"] == "flac"
            and audio["sample_fmt"] == "s16"
            and int(audio["sample_rate"]) == 48000
            and int(audio["channels"]) == 2
        ),
        "audio_policy": not forbidden,
        "interactive_audio_non_silent": peak_s16 > 0 and len(audio_rows) > 0,
    },
}
if not all(qa["gates"].values()):
    raise SystemExit("endurance QA failed: " + json.dumps(qa, sort_keys=True))
output = Path(root_text) / "phase0" / "av-tests" / run_id / "qa.json"
output.write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n")
print(json.dumps(qa, indent=2, sort_keys=True))
PY

sha256sum \
  "$raw_avi" "$frames_csv" "$audio_csv" "$metrics" "$encoded" \
  "$result_root/qa.json" > "$result_root/SHA256SUMS"

if ! grep -Eq 'GL_RENDERER:.*NVIDIA' "$engine_log"; then
  printf 'hardware renderer gate failed: %s\n' "$engine_log" >&2
  exit 78
fi
if grep -Eqi 'llvmpipe|softpipe' "$engine_log"; then
  printf 'software renderer forbidden: %s\n' "$engine_log" >&2
  exit 78
fi
if find "$run_root" -type f \
  \( -path '*/dlcache/*' -o -name '*.pk3' -o -name '*.pk3dir' \) \
  -print -quit | grep -q .; then
  printf 'unexpected downloaded/user package under %s\n' "$run_root" >&2
  exit 79
fi

printf 'run_id=%s\n' "$run_id"
printf 'raw_avi=%s\n' "$raw_avi"
printf 'encoded_mkv=%s\n' "$encoded"
printf 'qa=%s\n' "$result_root/qa.json"
