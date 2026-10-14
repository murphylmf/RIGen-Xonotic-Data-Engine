#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)
radar_root=${XONOTIC_DUEL_RADAR_ROOT:-./xonotic_workspace}
map_root=${XONOTIC_DUEL_MAP_ROOT:-./xonotic_workspace}
offline_root=${XONOTIC_DUEL_OFFLINE_ROOT:-./xonotic_workspace}
assets_root=${XONOTIC_DUEL_ASSETS:-./xonotic_workspace}
output_root=${XONOTIC_DUEL_OUTPUT_ROOT:-$duel_root/outputs}
binary="$offline_root/build/offline-accelerated-0.8.6-aarch64/bin/xonotic-local-sdl"
custom_progs="$duel_root/build/duel-v11-stage2-prompt-qc/progs.dat"
custom_csprogs="$duel_root/build/duel-v11-stage2-prompt-qc/csprogs.dat"
stage_manifest="$duel_root/protected/STAGE12_BEFORE.sha256"
existing_manifest="$duel_root/protected/EXISTING_PIPELINES_BEFORE.sha256"
prior_duel_manifest="$duel_root/protected/DUEL_V5_V6_V7_BEFORE.sha256"
map_name=duel_box_space

if (($# < 2)); then
  printf 'usage: %s SOURCE_DEMO RUN_ID [ACCEPTED_DURATION_SECONDS]\n' "$0" >&2
  exit 64
fi
source_demo=$1
run_id=$2
accepted_duration=${3:-}
width=${XONOTIC_DUEL_WIDTH:-960}
height=${XONOTIC_DUEL_HEIGHT:-540}
fps=${XONOTIC_DUEL_FPS:-48}
x264_threads=${XONOTIC_DUEL_X264_THREADS:-4}
scratch_root=${XONOTIC_DUEL_SCRATCH_ROOT:-./tmp}

source_manifest="$(dirname -- "$source_demo")/manifest.json"
[[ -s "$source_manifest" ]] || { printf 'authoritative source manifest is required: %s\n' "$source_manifest" >&2; exit 66; }
jq -e '.schema_version == "xonotic-duel-v11-authoritative-action-demo-source-v1" and .action_artifacts_admitted == true' "$source_manifest" >/dev/null || {
  printf 'source manifest is not admitted by the duel-v11 action contract\n' >&2; exit 70;
}
source_action_raw=$(jq -r '.action_contract.raw_telemetry.path' "$source_manifest")
source_actions=$(jq -r '.action_contract.engine_audit.path' "$source_manifest")
source_model_actions=$(jq -r '.action_contract.model_actions_64hz.path' "$source_manifest")
source_action_qa=$(jq -r '.action_contract.qa.path' "$source_manifest")
for action_input in "$source_action_raw" "$source_actions" "$source_model_actions" "$source_action_qa"; do
  [[ -s "$action_input" ]] || { printf 'missing source action input: %s\n' "$action_input" >&2; exit 66; }
done
for action_pair in \
  "$source_action_raw|$(jq -r '.action_contract.raw_telemetry.sha256' "$source_manifest")" \
  "$source_actions|$(jq -r '.action_contract.engine_audit.sha256' "$source_manifest")" \
  "$source_model_actions|$(jq -r '.action_contract.model_actions_64hz.sha256' "$source_manifest")"; do
  action_path=${action_pair%%|*}
  expected_sha=${action_pair#*|}
  actual_sha=$(sha256sum "$action_path" | awk '{print $1}')
  [[ "$actual_sha" == "$expected_sha" ]] || { printf 'source action hash mismatch: %s\n' "$action_path" >&2; exit 70; }
done
source_action_qa_sha=$(sha256sum "$source_action_qa" | awk '{print $1}')
[[ "$source_action_qa_sha" == "$(jq -r '.action_contract.qa.sha256' "$source_manifest")" ]] || {
  printf 'source action QA hash mismatch: %s\n' "$source_action_qa" >&2; exit 70;
}
if [[ -z "$accepted_duration" && -s "$source_manifest" ]]; then
  accepted_duration=$(jq -r '.rollout.accepted_window_seconds // empty' "$source_manifest")
fi
if [[ -z "$accepted_duration" ]]; then
  printf 'accepted duration is required when the source manifest is unavailable\n' >&2
  exit 64
fi
for value in "$width" "$height" "$fps" "$x264_threads" "$accepted_duration"; do
  [[ "$value" =~ ^[0-9]+$ ]] || { printf 'render dimensions, fps, threads, and duration must be positive integers\n' >&2; exit 64; }
done
if ((accepted_duration < 20 || accepted_duration > 600)); then
  printf 'accepted duration must be between 20 and 600 seconds\n' >&2
  exit 64
fi
if [[ ! "$run_id" =~ ^[A-Za-z0-9._-]+$ ]]; then
  printf 'run_id contains unsupported characters: %s\n' "$run_id" >&2
  exit 64
fi
[[ "$(uname -m)" == aarch64 ]] || { printf 'runtime requires aarch64\n' >&2; exit 78; }
[[ "$output_root" == /* ]] || { printf 'output root must be absolute: %s\n' "$output_root" >&2; exit 64; }
[[ -d "$scratch_root" && -w "$scratch_root" ]] || { printf 'scratch root must be an existing writable directory: %s\n' "$scratch_root" >&2; exit 66; }
mkdir -p "$output_root"
output_root=$(cd -- "$output_root" && pwd -P)
scratch_root=$(cd -- "$scratch_root" && pwd -P)

for required in \
  "$source_demo" "$binary" "$custom_progs" "$custom_csprogs" \
  "$duel_root/configs/clean_client.cfg" "$duel_root/configs/offline_render.cfg" \
  "$stage_manifest" "$existing_manifest" "$prior_duel_manifest" \
  "$map_root/map_src/$map_name.map" \
  "$map_root/map_pk3dir/maps/$map_name.bsp" \
  "$map_root/map_pk3dir/maps/$map_name.mapinfo" \
  "$map_root/map_pk3dir/maps/$map_name.waypoints" \
  "$map_root/map_pk3dir/maps/$map_name.waypoints.cache" \
  "$map_root/map_pk3dir/maps/$map_name.jpg" \
  "$map_root/map_pk3dir/gfx/${map_name}_mini.jpg" \
  "$map_root/map_pk3dir/gfx/${map_name}_radar.jpg"; do
  [[ -s "$required" ]] || { printf 'missing required input: %s\n' "$required" >&2; exit 66; }
done
[[ -x "$binary" ]] || { printf 'runtime is not executable: %s\n' "$binary" >&2; exit 66; }

run_root="$output_root/renders/$run_id"
if [[ -e "$run_root" ]]; then
  printf 'refusing to overwrite existing render: %s\n' "$run_root" >&2
  exit 73
fi
mkdir -p "$run_root/configs" "$run_root/runtime" "$run_root/map" "$run_root/inspection" "$run_root/actions"
sha256sum -c "$stage_manifest" > "$run_root/stage12_precheck.txt"
sha256sum -c "$existing_manifest" > "$run_root/existing_pipelines_precheck.txt"
sha256sum -c "$prior_duel_manifest" > "$run_root/prior_duel_precheck.txt"

work_tmp=$(mktemp -d "$scratch_root/xonotic-duel-v11-render.XXXXXX")
cleanup() {
  if [[ "$work_tmp" == "$scratch_root"/xonotic-duel-v11-render.* ]]; then
    rm -rf -- "$work_tmp"
  else
    printf 'refusing unexpected temporary cleanup target: %s\n' "$work_tmp" >&2
  fi
}
trap cleanup EXIT

render_user="$work_tmp/user"
mkdir -p "$render_user/data/demos" "$render_user/data/video" "$render_user/data/maps" "$render_user/data/gfx"
install -m 644 "$source_demo" "$render_user/data/demos/source.dem"
install -m 644 "$duel_root/configs/clean_client.cfg" "$render_user/data/clean_client.cfg"
install -m 644 "$duel_root/configs/offline_render.cfg" "$render_user/data/offline_render.cfg"
install -m 644 "$custom_progs" "$render_user/data/progs.dat"
install -m 644 "$custom_csprogs" "$render_user/data/csprogs.dat"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.bsp" "$render_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.mapinfo" "$render_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.waypoints" "$render_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.waypoints.cache" "$render_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.jpg" "$render_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_mini.jpg" "$render_user/data/gfx/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_radar.jpg" "$render_user/data/gfx/"

install -m 644 "$duel_root/configs/clean_client.cfg" "$run_root/configs/"
install -m 644 "$duel_root/configs/offline_render.cfg" "$run_root/configs/"
install -m 644 "$custom_progs" "$run_root/runtime/"
install -m 644 "$custom_csprogs" "$run_root/runtime/"
install -m 644 "$map_root/map_src/$map_name.map" "$run_root/map/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.bsp" "$run_root/map/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_radar.jpg" "$run_root/map/"
install -m 644 "$source_manifest" "$run_root/source_demo_manifest.json"
render_action_raw="$run_root/actions/server_bot_actions.tsv"
render_actions="$run_root/actions/actions.parquet"
render_model_actions="$run_root/actions/model_actions_64hz.parquet"
render_action_qa="$run_root/actions/action_qa.json"
install -m 644 "$source_action_raw" "$render_action_raw"
install -m 644 "$source_actions" "$render_actions"
install -m 644 "$source_model_actions" "$render_model_actions"
install -m 644 "$source_action_qa" "$render_action_qa"

engine_log="$run_root/offline_render_engine.log"
raw_probe="$run_root/raw_ffprobe.json"
video="$run_root/$run_id.mp4"
encode_log="$run_root/ffmpeg_encode.log"
full_probe="$run_root/ffprobe.json"

export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export LC_ALL=C

render_start_ns=$(date +%s%N)
timeout --signal=TERM --kill-after=15 900 \
  "$binary" \
  -xonotic -nocdaudio \
  -basedir "$assets_root" \
  -userdir "$render_user" \
  -window -width "$width" -height "$height" \
  -sndspeed 48000 -sndbits 16 -sndstereo \
  +exec clean_client.cfg \
  +exec offline_render.cfg \
  +cl_capturevideo_width "$width" \
  +cl_capturevideo_height "$height" \
  +cl_capturevideo_fps "$fps" \
  +cl_capturevideo_framestep 1 \
  +cl_capturevideo_realtime 0 \
  +cl_capturevideo_offline_accelerate 1 \
  +cl_capturevideo_demo_stop 1 \
  +cl_capturevideo_ogg 0 \
  +cl_capturevideo_printfps 1 \
  +cl_capturevideo_number 0 \
  +cl_capturevideo_nameformat "${run_id}_raw_" \
  +csqc_usedemoprogs \
  +crosshair_enabled \
  +duel_force_spectator_crosshair \
  +hud_panel_radar \
  +hud_panel_radar_rotation \
  +duel_radar_self_scale \
  +hud_panel_weapons \
  +hud_panel_ammo \
  +hud_panel_healtharmor \
  +hud_panel_notify \
  +hud_panel_centerprint \
  +hud_panel_infomessages \
  +hud_panel_pickup \
  +cl_capturevideo_realtime \
  +cl_capturevideo_offline_accelerate \
  -capturedemo demos/source \
  > "$engine_log" 2>&1
render_stop_ns=$(date +%s%N)
render_wall_seconds=$(awk -v ns="$((render_stop_ns - render_start_ns))" 'BEGIN {printf "%.6f", ns / 1000000000}')

mapfile -t raw_videos < <(find "$render_user/data/video" -maxdepth 1 -type f -name "${run_id}_raw_*.avi" -print | sort)
if ((${#raw_videos[@]} != 1)); then
  printf 'expected one raw AVI, found %d\n' "${#raw_videos[@]}" >&2; exit 70
fi
raw_video=${raw_videos[0]}
grep -aFq 'Playing demo demos/source.dem' "$engine_log" || { printf 'demo playback did not start\n' >&2; exit 70; }
grep -aFq 'Finishing capture of video/' "$engine_log" || { printf 'offline capture did not finish\n' >&2; exit 70; }
grep -aEq 'CSQC Build information: .*xonotic-v0\.8\.6-duel-v11-stage2-prompt' "$engine_log" || { printf 'custom duel-v11 CSQC was not loaded\n' >&2; exit 70; }
for cvar_gate in \
	'"csqc_usedemoprogs" is "0"' \
  '"crosshair_enabled" is "1"' \
  '"duel_force_spectator_crosshair" is "1"' \
	'"hud_panel_radar" is "0"' \
  '"hud_panel_weapons" is "0"' \
  '"hud_panel_ammo" is "0"' \
  '"hud_panel_healtharmor" is "0"' \
  '"hud_panel_notify" is "0"' \
  '"hud_panel_centerprint" is "0"' \
  '"hud_panel_infomessages" is "0"' \
  '"hud_panel_pickup" is "0"' \
  '"cl_capturevideo_realtime" is "0"' \
  '"cl_capturevideo_offline_accelerate" is "1"'; do
  grep -aFq "$cvar_gate" "$engine_log" || { printf 'offline cvar gate failed: %s\n' "$cvar_gate" >&2; exit 70; }
done

ffprobe -v error -count_frames -show_streams -show_format -of json "$raw_video" > "$raw_probe"
raw_frames=$(jq -r '[.streams[] | select(.codec_type == "video")][0].nb_read_frames' "$raw_probe")
raw_duration=$(jq -r '.format.duration' "$raw_probe")
awk -v raw="$raw_duration" -v accepted="$accepted_duration" 'BEGIN {if (raw + 0.05 < accepted) exit 1}' || {
  printf 'raw demo is shorter than accepted window: raw=%s accepted=%s\n' "$raw_duration" "$accepted_duration" >&2; exit 70;
}
trim_start=$(awk -v raw="$raw_duration" -v accepted="$accepted_duration" 'BEGIN {printf "%.6f", raw - accepted}')

encode_start_ns=$(date +%s%N)
ffmpeg -hide_banner -y -nostdin \
  -sseof "-$accepted_duration" -i "$raw_video" -t "$accepted_duration" \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset medium -profile:v high -crf 18 -threads "$x264_threads" \
  -pix_fmt yuv420p -r "$fps" -fps_mode cfr \
  -g "$fps" -keyint_min "$fps" -sc_threshold 0 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart \
  "$video" > "$encode_log" 2>&1
encode_stop_ns=$(date +%s%N)
encode_wall_seconds=$(awk -v ns="$((encode_stop_ns - encode_start_ns))" 'BEGIN {printf "%.6f", ns / 1000000000}')

probe_start_ns=$(date +%s%N)
ffprobe -v error -count_frames -show_streams -show_format -of json "$video" > "$full_probe"
probe_stop_ns=$(date +%s%N)
probe_wall_seconds=$(awk -v ns="$((probe_stop_ns - probe_start_ns))" 'BEGIN {printf "%.6f", ns / 1000000000}')
video_frames=$(jq -r '[.streams[] | select(.codec_type == "video")][0].nb_read_frames' "$full_probe")
video_duration=$(jq -r '.format.duration' "$full_probe")
video_width=$(jq -r '[.streams[] | select(.codec_type == "video")][0].width' "$full_probe")
video_height=$(jq -r '[.streams[] | select(.codec_type == "video")][0].height' "$full_probe")
video_fps=$(jq -r '[.streams[] | select(.codec_type == "video")][0].r_frame_rate' "$full_probe")
audio_streams=$(jq '[.streams[] | select(.codec_type == "audio")] | length' "$full_probe")
expected_frames=$((accepted_duration * fps))
frame_delta=$((video_frames - expected_frames))
if ((frame_delta < -2 || frame_delta > 2)); then
  printf 'frame-count gate failed: got=%s expected=%s\n' "$video_frames" "$expected_frames" >&2; exit 70
fi
[[ "$video_width" == "$width" && "$video_height" == "$height" && "$video_fps" == "$fps/1" ]] || {
  printf 'target spec gate failed\n' >&2; exit 70;
}
((audio_streams == 1)) || { printf 'expected one audio stream\n' >&2; exit 70; }
awk -v got="$video_duration" -v want="$accepted_duration" 'BEGIN {d=got-want; if(d<0)d=-d; if(d>0.10)exit 1}' || {
  printf 'duration gate failed: got=%s expected=%s\n' "$video_duration" "$accepted_duration" >&2; exit 70;
}
action_duration=$(jq -r '.alignment.duration_seconds' "$render_action_qa")
video_action_duration_error=$(awk -v video="$video_duration" -v action="$action_duration" 'BEGIN {d=video-action; if(d<0)d=-d; printf "%.6f", d}')
awk -v error="$video_action_duration_error" 'BEGIN {if(error > 0.10) exit 1}' || {
  printf 'video/action duration alignment gate failed: video=%s action=%s error=%s\n' "$video_duration" "$action_duration" "$video_action_duration_error" >&2; exit 70;
}

ffmpeg -hide_banner -y -nostdin -i "$video" \
  -vf "fps=4/$accepted_duration,scale=480:-2,tile=2x2" -frames:v 1 \
  "$run_root/inspection/contact_sheet.jpg" > "$run_root/inspection/contact_sheet.log" 2>&1

sha256sum -c "$stage_manifest" > "$run_root/stage12_postcheck.txt"
sha256sum -c "$existing_manifest" > "$run_root/existing_pipelines_postcheck.txt"
sha256sum -c "$prior_duel_manifest" > "$run_root/prior_duel_postcheck.txt"

source_demo_sha=$(sha256sum "$source_demo" | awk '{print $1}')
video_sha=$(sha256sum "$video" | awk '{print $1}')
render_action_raw_sha=$(sha256sum "$render_action_raw" | awk '{print $1}')
render_actions_sha=$(sha256sum "$render_actions" | awk '{print $1}')
render_model_actions_sha=$(sha256sum "$render_model_actions" | awk '{print $1}')
render_action_qa_sha=$(sha256sum "$render_action_qa" | awk '{print $1}')
render_speed=$(awk -v d="$raw_duration" -v w="$render_wall_seconds" 'BEGIN {printf "%.6f", d / w}')
accepted_render_speed=$(awk -v d="$accepted_duration" -v w="$render_wall_seconds" 'BEGIN {printf "%.6f", d / w}')
encode_speed=$(awk -v d="$video_duration" -v w="$encode_wall_seconds" 'BEGIN {printf "%.6f", d / w}')
total_wall_seconds=$(awk -v a="$render_wall_seconds" -v b="$encode_wall_seconds" -v c="$probe_wall_seconds" 'BEGIN {printf "%.6f", a+b+c}')
end_to_end_speed=$(awk -v d="$video_duration" -v w="$total_wall_seconds" 'BEGIN {printf "%.6f", d / w}')

jq -n \
  --arg run_id "$run_id" \
  --arg source_demo "$source_demo" \
  --arg source_demo_sha256 "$source_demo_sha" \
  --arg video "$video" \
  --arg video_sha256 "$video_sha" \
  --arg action_raw "$render_action_raw" \
  --arg action_raw_sha256 "$render_action_raw_sha" \
  --arg actions "$render_actions" \
  --arg actions_sha256 "$render_actions_sha" \
  --arg model_actions "$render_model_actions" \
  --arg model_actions_sha256 "$render_model_actions_sha" \
  --arg action_qa "$render_action_qa" \
  --arg action_qa_sha256 "$render_action_qa_sha" \
  --arg video_action_duration_error "$video_action_duration_error" \
  --slurpfile source_manifest "$source_manifest" \
  --slurpfile action_qa_json "$render_action_qa" \
  --arg scratch_root "$scratch_root" \
  --arg raw_duration "$raw_duration" \
  --arg video_duration "$video_duration" \
  --arg trim_start "$trim_start" \
  --arg render_wall_seconds "$render_wall_seconds" \
  --arg encode_wall_seconds "$encode_wall_seconds" \
  --arg probe_wall_seconds "$probe_wall_seconds" \
  --arg total_wall_seconds "$total_wall_seconds" \
  --arg render_speed "$render_speed" \
  --arg accepted_render_speed "$accepted_render_speed" \
  --arg encode_speed "$encode_speed" \
  --arg end_to_end_speed "$end_to_end_speed" \
  --argjson accepted_duration "$accepted_duration" \
  --argjson width "$width" \
  --argjson height "$height" \
  --argjson fps "$fps" \
  --argjson x264_threads "$x264_threads" \
  --argjson raw_frames "$raw_frames" \
  --argjson video_frames "$video_frames" \
  '{
    schema_version: "xonotic-duel-v11-authoritative-action-offline-render-v1",
    training_admitted: false,
    action_artifacts_admitted: true,
    stage1_stage2_unchanged: true,
    previous_duel_pipelines_unchanged: true,
    run_id: $run_id,
    source_demo: {path: $source_demo, sha256: $source_demo_sha256},
    accepted_window: {
      policy: "last N seconds of source demo after observer setup",
      trim_start_seconds: ($trim_start | tonumber),
      requested_seconds: $accepted_duration
    },
    video: {
      path: $video,
      sha256: $video_sha256,
      width: $width,
      height: $height,
      fps: $fps,
      frames: $video_frames,
      duration_seconds: ($video_duration | tonumber),
      audio: true
    },
    action_contract: {
      provenance: $source_manifest[0].action_contract.provenance,
      tick_hz: $source_manifest[0].action_contract.tick_hz,
      standard_fps: $source_manifest[0].action_contract.standard_fps,
      channels: $source_manifest[0].action_contract.channels,
      raw_telemetry: {path: $action_raw, sha256: $action_raw_sha256},
      engine_audit: {path: $actions, sha256: $actions_sha256},
      model_actions_64hz: {path: $model_actions, sha256: $model_actions_sha256},
      qa: {path: $action_qa, sha256: $action_qa_sha256, report: $action_qa_json[0]},
      video_alignment: {
        video_start_policy: "last accepted duration ending at the shared telemetry-disable/demo-stop boundary",
        shared_end_boundary: "duel_action_telemetry 0 and stop execute in the same deferred engine command",
        action_start_server_seconds: $action_qa_json[0].alignment.observed_server_start_seconds,
        measured_video_trim_start_seconds: ($trim_start | tonumber),
        video_action_duration_error_seconds: ($video_action_duration_error | tonumber),
        duration_gate_seconds: 0.10,
        shared_boundary_design_bound_seconds: 0.015625
      }
    },
    observation_contract: {
      only_ui: ["crosshair"],
      all_other_hud_panels_disabled: true,
      radar_present: false,
      replay_csqc_policy: "isolated_local_build_matching_recorder",
      visual_canary_review_required_before_bulk_launch: true
    },
    timing: {
      scratch_root: $scratch_root,
      raw_demo_seconds: ($raw_duration | tonumber),
      raw_demo_frames: $raw_frames,
      render_wall_seconds: ($render_wall_seconds | tonumber),
      encode_wall_seconds: ($encode_wall_seconds | tonumber),
      probe_wall_seconds: ($probe_wall_seconds | tonumber),
      total_wall_seconds: ($total_wall_seconds | tonumber),
      raw_video_seconds_per_render_wall_second: ($render_speed | tonumber),
      accepted_video_seconds_per_render_wall_second: ($accepted_render_speed | tonumber),
      encode_video_seconds_per_wall_second: ($encode_speed | tonumber),
      end_to_end_video_seconds_per_wall_second: ($end_to_end_speed | tonumber),
      x264_threads: $x264_threads
    }
  }' > "$run_root/manifest.json"

sha256sum "$video" "$run_root/manifest.json" "$run_root/inspection/contact_sheet.jpg" \
  "$render_action_raw" "$render_actions" "$render_model_actions" "$render_action_qa" \
  > "$run_root/SHA256SUMS"
printf 'run_root=%s\n' "$run_root"
printf 'video=%s\n' "$video"
printf 'manifest=%s\n' "$run_root/manifest.json"
printf 'contact_sheet=%s\n' "$run_root/inspection/contact_sheet.jpg"
printf 'raw_duration_seconds=%s\n' "$raw_duration"
printf 'accepted_duration_seconds=%s\n' "$video_duration"
printf 'render_wall_seconds=%s\n' "$render_wall_seconds"
printf 'encode_wall_seconds=%s\n' "$encode_wall_seconds"
printf 'total_wall_seconds=%s\n' "$total_wall_seconds"
