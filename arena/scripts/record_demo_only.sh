#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)
radar_root=${XONOTIC_DUEL_RADAR_ROOT:-./xonotic_workspace}
map_root=${XONOTIC_DUEL_MAP_ROOT:-./xonotic_workspace}
assets_root=${XONOTIC_DUEL_ASSETS:-./xonotic_workspace}
output_root=${XONOTIC_DUEL_OUTPUT_ROOT:-$duel_root/outputs}
record_scratch_root=${XONOTIC_DUEL_RECORD_SCRATCH_ROOT:-./tmp}
binary="$radar_root/build/baseline-0.8.6-aarch64/bin/xonotic-local-sdl"
custom_progs="$duel_root/build/duel-v11-stage2-prompt-qc/progs.dat"
custom_csprogs="$duel_root/build/duel-v11-stage2-prompt-qc/csprogs.dat"
stage_manifest="$duel_root/protected/STAGE12_BEFORE.sha256"
existing_manifest="$duel_root/protected/EXISTING_PIPELINES_BEFORE.sha256"
prior_duel_manifest="$duel_root/protected/DUEL_V5_V6_V7_BEFORE.sha256"
map_name=duel_box_space

duration=${1:-60}
run_id=${2:-duel_v11_demo_$(date -u +%Y%m%dT%H%M%SZ)}
skill_a=${3:-}
skill_b=${4:-}
pov_policy=${5:-}
setup_seconds=${XONOTIC_DUEL_SETUP_SECONDS:-20}
base_skill=5
weapon=machinegun

case "$duration" in
  ''|*[!0-9]*) printf 'duration must be an integer number of seconds\n' >&2; exit 64 ;;
esac
if ((duration < 20 || duration > 600)); then
  printf 'duration must be between 20 and 600 seconds\n' >&2
  exit 64
fi
if [[ ! "$run_id" =~ ^[A-Za-z0-9._-]+$ ]]; then
  printf 'run_id contains unsupported characters: %s\n' "$run_id" >&2
  exit 64
fi
case "$setup_seconds" in
  ''|*[!0-9]*) printf 'setup seconds must be an integer\n' >&2; exit 64 ;;
esac
if ((setup_seconds < 18)); then
  printf 'setup seconds must be at least 18\n' >&2
  exit 64
fi

random_level() {
  local random_value
  random_value=$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')
  printf '%d\n' "$((3 + random_value % 4))"
}

if [[ -z "$skill_a" ]]; then skill_a=$(random_level); fi
if [[ -z "$skill_b" ]]; then
  skill_b=$(random_level)
  while ((skill_b == skill_a)); do skill_b=$(random_level); done
fi
for level in "$skill_a" "$skill_b"; do
  case "$level" in
    3|4|5|6) ;;
    *) printf 'nominal bot levels must be one of 3, 4, 5, 6\n' >&2; exit 64 ;;
  esac
done
if ((skill_a == skill_b)); then
  printf 'the two nominal bot levels must differ\n' >&2
  exit 64
fi

if [[ -z "$pov_policy" ]]; then
  if (( $(random_level) % 2 == 0 )); then
    pov_policy=AggressiveClose
  else
    pov_policy=LongRangeEvasive
  fi
fi
case "$pov_policy" in
  AggressiveClose) pov_bot="AggressiveClose_L${skill_a}" ;;
  LongRangeEvasive) pov_bot="LongRangeEvasive_L${skill_b}" ;;
  *) printf 'POV policy must be AggressiveClose or LongRangeEvasive\n' >&2; exit 64 ;;
esac

[[ "$(uname -m)" == aarch64 ]] || { printf 'runtime requires aarch64\n' >&2; exit 78; }
[[ "$output_root" == /* ]] || { printf 'output root must be absolute: %s\n' "$output_root" >&2; exit 64; }
[[ -d "$record_scratch_root" && -w "$record_scratch_root" ]] || {
  printf 'record scratch root must be an existing writable directory: %s\n' "$record_scratch_root" >&2
  exit 66
}
mkdir -p "$output_root"
output_root=$(cd -- "$output_root" && pwd -P)
record_scratch_root=$(cd -- "$record_scratch_root" && pwd -P)
for required in \
  "$binary" "$custom_progs" "$custom_csprogs" \
  "$duel_root/configs/clean_server.cfg" "$duel_root/configs/clean_client.cfg" \
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

run_root="$output_root/demos/$run_id"
demo_rel="demos/$run_id"
demo_path="$run_root/$run_id.dem"
engine_log="$run_root/record_engine.log"
capture_window_log="$run_root/capture_window.log"
events="$run_root/eventlog.txt"
manifest="$run_root/manifest.json"
if [[ -e "$run_root" ]]; then
  printf 'refusing to overwrite existing demo run: %s\n' "$run_root" >&2
  exit 73
fi
mkdir -p "$run_root/configs" "$run_root/runtime" "$run_root/map" "$run_root/actions"

sha256sum -c "$stage_manifest" > "$run_root/stage12_precheck.txt"
sha256sum -c "$existing_manifest" > "$run_root/existing_pipelines_precheck.txt"
sha256sum -c "$prior_duel_manifest" > "$run_root/prior_duel_precheck.txt"

work_tmp=$(mktemp -d "$record_scratch_root/xonotic-duel-v11-record.XXXXXX")
cleanup() {
  if [[ "$work_tmp" == "$record_scratch_root"/xonotic-duel-v11-record.* ]]; then
    rm -rf -- "$work_tmp"
  else
    printf 'refusing unexpected temporary cleanup target: %s\n' "$work_tmp" >&2
  fi
}
trap cleanup EXIT

record_user="$work_tmp/user"
generated_bots="$record_user/data/clean_bots.txt"
working_demo_path="$record_user/data/$demo_rel.dem"
action_rel="duel_actions/${run_id}.tsv"
working_action_path="$record_user/data/$action_rel"
action_raw="$run_root/actions/server_bot_actions.tsv"
action_output_dir="$run_root/actions/processed"
mkdir -p "$record_user/data/demos" "$record_user/data/duel_actions" "$record_user/data/maps" "$record_user/data/gfx"

profile_row() {
  local policy=$1
  local level=$2
  awk -v policy="$policy" -v level="$level" 'BEGIN {
    d = level - 5
    if (policy == "AggressiveClose") {
      name = policy "_L" level
      keyboard = 0.5 + 2*d; moving = 1 + d/2; dodging = 0.5 + d/2
      ping = 2*d; weapon = 1 + d/2; aggression = 2 + d; range = -1
      aiming = 0.5 + d/2; calmhand = 0.5 + d/2; mouse = 1 + d
      fightthink = 1 + d; aithink = 1 + d/2
    } else {
      name = policy "_L" level
      keyboard = 1 + 2*d; moving = 1.5 + d/2; dodging = 2 + d/2
      ping = 2*d; weapon = 1 + d/2; aggression = -0.5 + d; range = 1
      aiming = 1 + d/2; calmhand = 1 + d/2; mouse = 0.5 + d
      fightthink = 1 + d; aithink = 1 + d/2
    }
    printf "%s\tseraphina\t1\t0\t0\t0\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\n", \
      name, keyboard, moving, dodging, ping, weapon, aggression, range, aiming, calmhand, mouse, fightthink, aithink
  }'
}

printf '%s\n' '// name\tmodel\tskin\tshirt\tpants\tteam\tkeyboard use\tmoving\tdodging\tping\tweapon use\taggressivity\trange\taiming\tcalmhand\tmouse\tfightthink\taithink' > "$generated_bots"
profile_row AggressiveClose "$skill_a" >> "$generated_bots"
profile_row LongRangeEvasive "$skill_b" >> "$generated_bots"

install -m 644 "$duel_root/configs/clean_server.cfg" "$record_user/data/clean_server.cfg"
install -m 644 "$duel_root/configs/clean_client.cfg" "$record_user/data/clean_client.cfg"
install -m 644 "$custom_progs" "$record_user/data/progs.dat"
install -m 644 "$custom_csprogs" "$record_user/data/csprogs.dat"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.bsp" "$record_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.mapinfo" "$record_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.waypoints" "$record_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.waypoints.cache" "$record_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.jpg" "$record_user/data/maps/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_mini.jpg" "$record_user/data/gfx/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_radar.jpg" "$record_user/data/gfx/"

install -m 644 "$duel_root/configs/clean_server.cfg" "$run_root/configs/"
install -m 644 "$duel_root/configs/clean_client.cfg" "$run_root/configs/"
install -m 644 "$generated_bots" "$run_root/configs/"
install -m 644 "$custom_progs" "$run_root/runtime/"
install -m 644 "$custom_csprogs" "$run_root/runtime/"
install -m 644 "$map_root/map_src/$map_name.map" "$run_root/map/"
install -m 644 "$map_root/map_pk3dir/maps/$map_name.bsp" "$run_root/map/"
install -m 644 "$map_root/map_pk3dir/gfx/${map_name}_radar.jpg" "$run_root/map/"

export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export LC_ALL=C

capture_start_at=$setup_seconds
capture_slack_seconds=$(((duration + 3) / 4))
if ((capture_slack_seconds < 8)); then capture_slack_seconds=8; fi


capture_slack_seconds=$((((capture_slack_seconds + 3) / 4) * 4))
capture_stop_at=$((setup_seconds + duration + capture_slack_seconds))
quit_at=$((capture_stop_at + 1))
record_timeout=$((quit_at + 180))
record_start_ns=$(date +%s%N)



timeout --signal=TERM --kill-after=15 "$record_timeout" \
  "$binary" \
  -xonotic -nocdaudio \
  -basedir "$assets_root" \
  -userdir "$record_user" \
  -window -width 160 -height 90 \
  -sndspeed 48000 -sndbits 16 -sndstereo \
  +exec clean_server.cfg \
  +exec clean_client.cfg \
  +r_renderview 0 \
  +sys_ticrate 0.015625 \
  +maxplayers 4 \
  +gametype dm \
  +g_weaponarena "$weapon" \
  +g_pickup_items 0 \
  +g_powerups 0 \
  +g_use_ammunition 0 \
  +g_balance_health_regen 0 \
  +g_balance_health_regenlinear 0 \
  +duel_mutual_fov_fire 1 \
  +duel_fire_visibility_debug 1 \
  +duel_primary_fire_only 1 \
  +duel_clean_bot_controls 1 \
  +duel_max_turn_speed 120 \
  +duel_max_turn_accel 480 \
  +duel_move_input_scale 0.177777778 \
  +duel_move_input_limit 64 \
  +duel_respawn_block_seconds 0.8 \
  +duel_respawn_out_of_view 1 \
  +duel_respawn_out_of_view_degrees 120 \
  +duel_action_telemetry 0 \
  +duel_action_telemetry_file "$action_rel" \
  +duel_action_telemetry_start "$capture_start_at" \
  +duel_action_telemetry_stop "$capture_stop_at" \
  +duel_force_pov_bot "$pov_bot" \
  +record "$demo_rel" "$map_name" \
  +defer 10 "status; bot_number; bot_config_file; skill; bot_ai_thinkinterval; g_weaponarena; g_pickup_items; g_powerups; g_use_ammunition; g_balance_health_regen; duel_mutual_fov_fire; duel_clean_bot_controls; duel_action_telemetry; duel_action_telemetry_file; duel_action_telemetry_start; duel_action_telemetry_stop; duel_force_pov_bot; duel_max_turn_speed; duel_max_turn_accel; duel_move_input_scale; duel_move_input_limit; duel_respawn_block_seconds; duel_respawn_out_of_view; crosshair_enabled; duel_force_spectator_crosshair; hud_panel_radar; hud_panel_weapons; hud_panel_ammo; hud_panel_healtharmor; hud_panel_notify; hud_panel_centerprint" \
  +defer 14 "cmd spectate" \
  +defer "$capture_start_at" "duel_action_telemetry 1; echo duel_v11_capture_window:start" \
  +defer "$capture_stop_at" "duel_action_telemetry 0; echo duel_v11_capture_window:stop; stop" \
  +defer "$quit_at" quit \
  > "$engine_log" 2>&1
record_stop_ns=$(date +%s%N)
record_wall_seconds=$(awk -v ns="$((record_stop_ns - record_start_ns))" 'BEGIN {printf "%.6f", ns / 1000000000}')

[[ -s "$working_demo_path" ]] || { printf 'demo was not produced\n' >&2; exit 70; }
capture_marker_count=$(grep -aEc '^duel_v11_capture_window:(start|stop)[[:space:]]*$' "$engine_log" || true)
[[ "$capture_marker_count" == 2 ]] || {
  printf 'capture-window markers are incomplete: got=%s expected=2\n' "$capture_marker_count" >&2
  exit 70
}
awk '
  /^duel_v11_capture_window:start[[:space:]]*$/ { in_capture = 1; next }
  /^duel_v11_capture_window:stop[[:space:]]*$/ { in_capture = 0; next }
  in_capture { print }
' "$engine_log" > "$capture_window_log"

grep -aFq 'loaded 12 waypoints and 0 wayboxes from maps/duel_box_space.waypoints' "$engine_log" || { printf 'waypoint file was not loaded\n' >&2; exit 70; }
grep -aFq 'loaded 28 waypoint links from maps/duel_box_space.waypoints.cache' "$engine_log" || { printf 'waypoint cache was not loaded\n' >&2; exit 70; }
grep -aEq 'CSQC Build information: .*xonotic-v0\.8\.6-duel-v11-stage2-prompt' "$engine_log" || { printf 'custom duel-v11 CSQC was not loaded\n' >&2; exit 70; }
grep -aFq "duel_pov_lock:active observer=DuelObserver target=$pov_bot" "$engine_log" || { printf 'server-side POV lock did not activate\n' >&2; exit 70; }
for bot_name in "AggressiveClose_L${skill_a}" "LongRangeEvasive_L${skill_b}"; do
  grep -aFq "$bot_name" "$engine_log" || { printf 'missing bot: %s\n' "$bot_name" >&2; exit 70; }
done
for cvar_gate in \
  '"g_weaponarena" is "machinegun"' \
  '"g_pickup_items" is "0"' \
  '"g_powerups" is "0"' \
  '"g_use_ammunition" is "0"' \
  '"g_balance_health_regen" is "0"' \
  '"duel_mutual_fov_fire" is "1"' \
  '"duel_clean_bot_controls" is "1"' \
  '"duel_action_telemetry" is "0"' \
  '"crosshair_enabled" is "1"' \
  '"duel_force_spectator_crosshair" is "1"' \
  '"duel_max_turn_speed" is "120"' \
  '"duel_max_turn_accel" is "480"' \
  '"duel_move_input_limit" is "64"' \
  '"duel_respawn_block_seconds" is "0.8"' \
  '"duel_respawn_out_of_view" is "1"' \
  '"hud_panel_radar" is "0"' \
  '"hud_panel_weapons" is "0"' \
  '"hud_panel_ammo" is "0"' \
  '"hud_panel_healtharmor" is "0"' \
  '"hud_panel_notify" is "0"' \
  '"hud_panel_centerprint" is "0"'; do
  grep -aFq "$cvar_gate" "$engine_log" || { printf 'runtime cvar gate failed: %s\n' "$cvar_gate" >&2; exit 70; }
done
if grep -aEqi 'got stuck|navigation stuck|waypoint stuck' "$capture_window_log"; then
  printf 'navigation-stuck signal observed\n' >&2; exit 70
fi

mapfile -t eventlogs < <(find "$record_user/data" -maxdepth 3 -type f -name 'duel_event_*.log' -print | sort)
if ((${#eventlogs[@]} != 1)); then
  printf 'expected one event log, found %d\n' "${#eventlogs[@]}" >&2; exit 70
fi
install -m 644 "${eventlogs[0]}" "$events"
install -m 644 "$working_demo_path" "$demo_path"
if [[ ! -s "$working_action_path" ]]; then
  mapfile -t discovered_action_files < <(find "$record_user" -type f -name "${run_id}.tsv" -print | sort)
  if ((${#discovered_action_files[@]} == 1)); then
    working_action_path=${discovered_action_files[0]}
  fi
fi
[[ -s "$working_action_path" ]] || {
  printf 'authoritative action telemetry was not produced; files under isolated userdir:\n' >&2
  find "$record_user" -maxdepth 4 -type f -printf '%P\n' | sort >&2
  exit 70
}
install -m 644 "$working_action_path" "$action_raw"
expected_action_frames=$((duration * 64))
recorded_action_frames=$(sed -n 's/.*duel_action_telemetry:closed reason=disabled frames=\([0-9][0-9]*\).*/\1/p' "$engine_log" | tail -n 1)
[[ "$recorded_action_frames" =~ ^[0-9]+$ ]] && ((recorded_action_frames >= expected_action_frames)) || {
  printf 'authoritative action telemetry is too short: got=%s required=%s\n' "${recorded_action_frames:-missing}" "$expected_action_frames" >&2
  exit 70
}
python3 "$script_dir/build_authoritative_actions.py" \
  --telemetry "$action_raw" \
  --output-dir "$action_output_dir" \
  --episode-id "$run_id" \
  --pov-bot "$pov_bot" \
  --duration "$duration" \
  > "$run_root/action_build.log"
action_qa_path="$action_output_dir/action_qa.json"
actions_path="$action_output_dir/actions.parquet"
model_actions_path="$action_output_dir/model_actions_64hz.parquet"
for action_artifact in "$action_qa_path" "$actions_path" "$model_actions_path"; do
  [[ -s "$action_artifact" ]] || { printf 'missing authoritative action artifact: %s\n' "$action_artifact" >&2; exit 70; }
done
jq -e '.action_artifacts_admitted == true and .gates.pov_locked_entire_window == true and .gates.unrepresented_controls_zero == true and .gates.selected_window_has_primary_fire == true and .gates.has_trainable_window == true' "$action_qa_path" >/dev/null || {
  printf 'authoritative action QA did not admit the episode\n' >&2; exit 70;
}
grep -aFq ':no_use_ammunition:no_pickup_items:machinegun arena' "$events" || { printf 'fixed machinegun/no-pickup event gate failed\n' >&2; exit 70; }
if [[ "$(awk -F '\t' '!/^\/\// && NF {print $2 FS $3 FS $4 FS $5}' "$generated_bots" | sort -u | wc -l)" != 1 ]]; then
  printf 'bot appearance is not fixed\n' >&2; exit 70
fi

accident_events=$(grep -aFc ':kill:accident:' "$events" || true)
capture_kill_events=$(grep -aFc 'was riddled full of holes by' "$capture_window_log" || true)
fire_visibility_samples=$(grep -aFc 'duel_fire_visibility:' "$capture_window_log" || true)
outside_view_fire_samples=$(grep -aEc 'duel_fire_visibility:.*outside_view=1' "$capture_window_log" || true)
behind_fire_samples=$(grep -aEc 'duel_fire_visibility:.*behind=1' "$capture_window_log" || true)
accident_events=${accident_events:-0}
capture_kill_events=${capture_kill_events:-0}
fire_visibility_samples=${fire_visibility_samples:-0}
outside_view_fire_samples=${outside_view_fire_samples:-0}
behind_fire_samples=${behind_fire_samples:-0}
((accident_events == 0)) || { printf 'environmental/accidental death observed\n' >&2; exit 70; }
accepted_kill_events=$(jq -r '.metrics.combat_death_transitions' "$action_qa_path")

sha256sum -c "$stage_manifest" > "$run_root/stage12_postcheck.txt"
sha256sum -c "$existing_manifest" > "$run_root/existing_pipelines_postcheck.txt"
sha256sum -c "$prior_duel_manifest" > "$run_root/prior_duel_postcheck.txt"

demo_sha=$(sha256sum "$demo_path" | awk '{print $1}')
bot_config_sha=$(sha256sum "$run_root/configs/clean_bots.txt" | awk '{print $1}')
map_sha=$(sha256sum "$map_root/map_pk3dir/maps/$map_name.bsp" | awk '{print $1}')
action_raw_sha=$(sha256sum "$action_raw" | awk '{print $1}')
actions_sha=$(sha256sum "$actions_path" | awk '{print $1}')
model_actions_sha=$(sha256sum "$model_actions_path" | awk '{print $1}')
action_qa_sha=$(sha256sum "$action_qa_path" | awk '{print $1}')
jq -n \
  --arg run_id "$run_id" \
  --arg demo_path "$demo_path" \
  --arg demo_sha256 "$demo_sha" \
  --arg bot_config_sha256 "$bot_config_sha" \
  --arg map_sha256 "$map_sha" \
  --arg action_raw "$action_raw" \
  --arg action_raw_sha256 "$action_raw_sha" \
  --arg actions_path "$actions_path" \
  --arg actions_sha256 "$actions_sha" \
  --arg model_actions_path "$model_actions_path" \
  --arg model_actions_sha256 "$model_actions_sha" \
  --arg action_qa_path "$action_qa_path" \
  --arg action_qa_sha256 "$action_qa_sha" \
  --slurpfile action_qa "$action_qa_path" \
  --arg pov_policy "$pov_policy" \
  --arg pov_bot "$pov_bot" \
  --arg fixed_model seraphina \
  --arg fixed_skin 1 \
  --arg fixed_shirt 0 \
  --arg fixed_pants 0 \
  --arg record_scratch_root "$record_scratch_root" \
  --arg record_wall_seconds "$record_wall_seconds" \
  --argjson duration "$duration" \
  --argjson setup_seconds "$setup_seconds" \
  --argjson capture_slack_seconds "$capture_slack_seconds" \
  --argjson recorded_action_frames "$recorded_action_frames" \
  --argjson base_skill "$base_skill" \
  --argjson skill_a "$skill_a" \
  --argjson skill_b "$skill_b" \
  --argjson capture_kill_events "$capture_kill_events" \
  --argjson accepted_kill_events "$accepted_kill_events" \
  --argjson fire_visibility_samples "$fire_visibility_samples" \
  --argjson outside_view_fire_samples "$outside_view_fire_samples" \
  --argjson behind_fire_samples "$behind_fire_samples" \
  '{
    schema_version: "xonotic-duel-v11-authoritative-action-demo-source-v1",
    training_admitted: false,
    action_artifacts_admitted: true,
    stage1_stage2_unchanged: true,
    previous_duel_pipelines_unchanged: true,
    run_id: $run_id,
    map: {name: "duel_box_space", visual_variant: "showcase_v9", bsp_sha256: $map_sha256},
    rollout: {
      accepted_window_seconds: $duration,
      setup_seconds_before_window: $setup_seconds,
      recorder_slack_seconds: $capture_slack_seconds,
      fixed_weapon: "machinegun",
      pickups: false,
      ammunition_consumption: false,
      primary_fire_only: true,
      movement_speed_target_units_per_second: 64,
      camera_turn_speed_limit_degrees_per_second: 120,
      camera_turn_acceleration_limit_degrees_per_second_squared: 480,
      offscreen_fire_blocked: true,
      respawn_aligned_to_prompt_block_seconds: 0.8,
      respawn_selected_outside_opponent_view: true,
      pov_policy: $pov_policy,
      pov_bot: $pov_bot
    },
    bots: {
      global_skill: $base_skill,
      per_bot_level_implementation: "native profile skill offsets",
      aggressive_close_nominal_level: $skill_a,
      long_range_evasive_nominal_level: $skill_b,
      nominal_levels_are_different: true,
      policies_are_different: true,
      fixed_appearance: {model: $fixed_model, skin: $fixed_skin, shirt: $fixed_shirt, pants: $fixed_pants},
      config_sha256: $bot_config_sha256
    },
    action_contract: {
      provenance: "authoritative server-side bot controls sampled after bot AI and before snapshot",
      tick_hz: 64,
      standard_fps: 20,
      channels: {
        j_left_x: "strafe / 400",
        j_left_y: "-forward / 400",
        j_right_x: "-yaw_delta_degrees / 12",
        j_right_y: "pitch_delta_degrees / 12",
        south: "jump",
        right_trigger: "primary fire",
        left_trigger: "secondary fire, forced zero",
        west: "reload, forced zero"
      },
      raw_telemetry: {path: $action_raw, sha256: $action_raw_sha256},
      engine_audit: {path: $actions_path, sha256: $actions_sha256},
      model_actions_64hz: {path: $model_actions_path, sha256: $model_actions_sha256},
      qa: {path: $action_qa_path, sha256: $action_qa_sha256, report: $action_qa[0]}
    },
    telemetry: {
      recorded_frames: $recorded_action_frames,
      selected_tail_frames: ($duration * 64),
      recorded_window_kills: $capture_kill_events,
      accepted_window_kills: $accepted_kill_events,
      fire_visibility_samples: $fire_visibility_samples,
      outside_view_fire_samples: $outside_view_fire_samples,
      behind_fire_samples: $behind_fire_samples
    },
    observation_contract: {
      only_ui: ["crosshair"],
      radar_present: false,
      all_other_hud_panels_disabled: true
    },
    demo: {path: $demo_path, sha256: $demo_sha256},
    timing: {
      record_scratch_root: $record_scratch_root,
      demo_generation_wall_seconds: ($record_wall_seconds | tonumber)
    }
  }' > "$manifest"

sha256sum "$demo_path" "$manifest" "$run_root/configs/clean_bots.txt" \
  "$action_raw" "$action_qa_path" "$actions_path" "$model_actions_path" > "$run_root/SHA256SUMS"
printf 'run_root=%s\n' "$run_root"
printf 'demo=%s\n' "$demo_path"
printf 'manifest=%s\n' "$manifest"
printf 'model_actions=%s\n' "$model_actions_path"
printf 'action_qa=%s\n' "$action_qa_path"
printf 'skill_a=%s\n' "$skill_a"
printf 'skill_b=%s\n' "$skill_b"
printf 'pov_policy=%s\n' "$pov_policy"
printf 'capture_kill_events=%s\n' "$capture_kill_events"
printf 'accepted_kill_events=%s\n' "$accepted_kill_events"
printf 'recorded_action_frames=%s\n' "$recorded_action_frames"
printf 'record_wall_seconds=%s\n' "$record_wall_seconds"
