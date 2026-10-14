#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)

if (($# != 4)); then
  printf 'usage: %s RUN_ID TOTAL_EPISODES GLOBAL_RANK GLOBAL_WORLD\n' "$0" >&2
  exit 64
fi

run_id=$1
total_episodes=$2
global_rank=$3
global_world=$4
duration=60




lanes_per_gpu=${XONOTIC_DUEL_LANES_PER_GPU:-2}
max_attempts=${XONOTIC_DUEL_MAX_BATCH_ATTEMPTS:-5}
schedule_seed=${XONOTIC_DUEL_SCHEDULE_SEED:-11}
production_base=${XONOTIC_DUEL_PRODUCTION_ROOT:-$duel_root/outputs/production_2x4}
scratch_base=${XONOTIC_DUEL_SCRATCH_BASE:-./tmp/xonotic-duel-v11-production}
preflight_only=${XONOTIC_DUEL_PREFLIGHT_ONLY:-0}

[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || {
  printf 'RUN_ID contains unsupported characters: %s\n' "$run_id" >&2
  exit 64
}
for value_name in total_episodes global_rank global_world max_attempts schedule_seed; do
  value=${!value_name}
  [[ "$value" =~ ^[0-9]+$ ]] || {
    printf '%s must be a non-negative integer, got: %s\n' "$value_name" "$value" >&2
    exit 64
  }
done
total_episodes=$((10#$total_episodes))
global_rank=$((10#$global_rank))
global_world=$((10#$global_world))
max_attempts=$((10#$max_attempts))
schedule_seed=$((10#$schedule_seed))
((total_episodes >= 1)) || { printf 'TOTAL_EPISODES must be positive\n' >&2; exit 64; }
((global_world >= 1)) || { printf 'GLOBAL_WORLD must be positive\n' >&2; exit 64; }
((global_rank >= 0 && global_rank < global_world)) || {
  printf 'GLOBAL_RANK=%s is outside [0,%s)\n' "$global_rank" "$global_world" >&2
  exit 64
}
((max_attempts >= 1)) || { printf 'XONOTIC_DUEL_MAX_BATCH_ATTEMPTS must be positive\n' >&2; exit 64; }
case "$lanes_per_gpu" in
  1|2|4|8) ;;
  *) printf 'XONOTIC_DUEL_LANES_PER_GPU must be one of 1, 2, 4, 8\n' >&2; exit 64 ;;
esac
lanes_per_gpu=$((10#$lanes_per_gpu))
[[ "$production_base" == /* && "$scratch_base" == /* ]] || {
  printf 'production and scratch roots must be absolute\n' >&2
  exit 64
}

if ((global_rank < total_episodes)); then
  rank_target_episodes=$(((total_episodes - 1 - global_rank) / global_world + 1))
else
  rank_target_episodes=0
fi
rank_tag=$(printf '%03d' "$global_rank")
rank_root="$production_base/$run_id/ranks/rank_$rank_tag"
output_root="$rank_root/data"
scratch_root="$scratch_base/$run_id/rank_$rank_tag"

for command in awk ffmpeg ffprobe flock jq nvidia-smi python setsid sha256sum; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$command" >&2
    exit 69
  }
done
python - <<'PY'
import numpy
import pandas
import pyarrow
PY
for required in \
  "$duel_root/scripts/record_demo_only.sh" \
  "$duel_root/scripts/process_recorded_episode.sh" \
  "$duel_root/protected/STAGE12_BEFORE.sha256" \
  "$duel_root/protected/EXISTING_PIPELINES_BEFORE.sha256" \
  "$duel_root/protected/DUEL_V5_V6_V7_BEFORE.sha256"; do
  [[ -s "$required" ]] || { printf 'missing required input: %s\n' "$required" >&2; exit 66; }
done

if [[ "$preflight_only" == 1 ]]; then
  jq -n \
    --arg run_id "$run_id" \
    --arg rank_root "$rank_root" \
    --arg scratch_root "$scratch_root" \
    --argjson total_episodes "$total_episodes" \
    --argjson global_rank "$global_rank" \
    --argjson global_world "$global_world" \
    --argjson rank_target_episodes "$rank_target_episodes" \
    --argjson lanes_per_gpu "$lanes_per_gpu" \
    '{preflight:true,run_id:$run_id,total_episodes:$total_episodes,global_rank:$global_rank,global_world:$global_world,rank_target_episodes:$rank_target_episodes,lanes_per_gpu:$lanes_per_gpu,rank_root:$rank_root,scratch_root:$scratch_root}'
  exit 0
fi

mkdir -p \
  "$rank_root/batches" "$rank_root/batch_logs" "$rank_root/accepted_shards" \
  "$output_root" "$scratch_root/record" "$scratch_root/render" "$scratch_root/visibility"

exec 9>"$rank_root/production.lock"
if ! flock -n 9; then
  printf 'another runner already owns rank lock: %s\n' "$rank_root/production.lock" >&2
  exit 75
fi

plan="$rank_root/PLAN.json"
completed_batches="$rank_root/completed_batches.jsonl"
failed_attempts="$rank_root/failed_attempts.jsonl"
progress="$rank_root/progress.json"
started_at=$(date -u +%FT%TZ)
started_epoch=$(date +%s)

if [[ ! -s "$plan" ]]; then
  plan_tmp="$rank_root/.PLAN.$$.tmp"
  jq -n \
    --arg schema_version xonotic-duel-v11-rank-production-plan-v1 \
    --arg run_id "$run_id" \
    --arg created_at "$started_at" \
    --arg rank_root "$rank_root" \
    --arg output_root "$output_root" \
    --arg scratch_root "$scratch_root" \
    --argjson total_episodes "$total_episodes" \
    --argjson global_rank "$global_rank" \
    --argjson global_world "$global_world" \
    --argjson rank_target_episodes "$rank_target_episodes" \
    --argjson duration "$duration" \
    --argjson lanes_per_gpu "$lanes_per_gpu" \
    --argjson schedule_seed "$schedule_seed" \
    '{
      schema_version:$schema_version,run_id:$run_id,created_at:$created_at,
      topology:{global_rank:$global_rank,global_world:$global_world,lanes_per_gpu:$lanes_per_gpu},
      target:{total_episodes:$total_episodes,rank_episodes:$rank_target_episodes,seconds_per_episode:$duration},
      schedule:{type:"deterministic_balanced_unequal_levels_and_alternating_pov",seed:$schedule_seed},
      paths:{rank_root:$rank_root,output_root:$output_root,scratch_root:$scratch_root},
      merge_scope:"rank-local only; global merge is intentionally deferred"
    }' >"$plan_tmp"
  mv "$plan_tmp" "$plan"
else
  jq -e \
    --arg run_id "$run_id" \
    --argjson total_episodes "$total_episodes" \
    --argjson global_rank "$global_rank" \
    --argjson global_world "$global_world" \
    --argjson lanes_per_gpu "$lanes_per_gpu" \
    '.run_id==$run_id and .target.total_episodes==$total_episodes and .topology.global_rank==$global_rank and .topology.global_world==$global_world and .topology.lanes_per_gpu==$lanes_per_gpu' \
    "$plan" >/dev/null || {
      printf 'existing rank plan does not match this invocation: %s\n' "$plan" >&2
      exit 78
    }
  started_at=$(jq -r '.created_at' "$plan")
  started_epoch=$(date -u -d "$started_at" +%s)
fi

completed_count() {
  if [[ -s "$completed_batches" ]]; then
    jq -s '[.[].accepted_episodes] | add // 0' "$completed_batches"
  else
    printf '0\n'
  fi
}

completed_batch_count() {
  if [[ -s "$completed_batches" ]]; then
    jq -s 'length' "$completed_batches"
  else
    printf '0\n'
  fi
}

rank_complete="$rank_root/RANK_COMPLETE.json"
if [[ -s "$rank_complete" && -s "$rank_root/MANIFEST_SHA256SUMS" ]] \
  && jq -e \
    --arg run_id "$run_id" \
    --argjson rank "$global_rank" \
    --argjson world "$global_world" \
    --argjson episodes "$rank_target_episodes" \
    '.run_id==$run_id and .rank.index==$rank and .rank.world==$world and .accepted.episodes==$episodes and (.gates|all)' \
    "$rank_complete" >/dev/null \
  && sha256sum -c "$rank_root/MANIFEST_SHA256SUMS" >/dev/null \
  && [[ "$(completed_count)" == "$rank_target_episodes" ]]; then
  printf 'rank_already_complete run_id=%s rank=%s/%s episodes=%s\n' \
    "$run_id" "$global_rank" "$global_world" "$rank_target_episodes"
  exit 0
fi

write_progress() {
  local status=$1
  local current_batch=${2:-}
  local message=${3:-}
  local completed elapsed remaining accepted_seconds rate eta_seconds progress_tmp
  completed=$(completed_count)
  elapsed=$(( $(date +%s) - started_epoch ))
  remaining=$((rank_target_episodes - completed))
  accepted_seconds=$((completed * duration))
  rate=$(awk -v data="$accepted_seconds" -v wall="$elapsed" 'BEGIN {if(wall>0) printf "%.6f",data/wall; else print "0.000000"}')
  eta_seconds=$(awk -v remaining="$remaining" -v duration="$duration" -v rate="$rate" 'BEGIN {if(rate>0) printf "%d",remaining*duration/rate+0.5; else print 0}')
  progress_tmp="$rank_root/.progress.$$.tmp"
  jq -n \
    --arg schema_version xonotic-duel-v11-rank-production-progress-v1 \
    --arg run_id "$run_id" \
    --arg status "$status" \
    --arg updated_at "$(date -u +%FT%TZ)" \
    --arg current_batch "$current_batch" \
    --arg message "$message" \
    --arg rate "$rate" \
    --argjson global_rank "$global_rank" \
    --argjson global_world "$global_world" \
    --argjson completed "$completed" \
    --argjson target "$rank_target_episodes" \
    --argjson remaining "$remaining" \
    --argjson completed_batches "$(completed_batch_count)" \
    --argjson elapsed "$elapsed" \
    --argjson eta_seconds "$eta_seconds" \
    '{
      schema_version:$schema_version,run_id:$run_id,status:$status,updated_at:$updated_at,
      rank:{index:$global_rank,world:$global_world},
      progress:{completed_episodes:$completed,target_episodes:$target,remaining_episodes:$remaining,completed_batches:$completed_batches},
      timing:{elapsed_seconds:$elapsed,observed_video_hours_per_wall_hour:($rate|tonumber),eta_seconds:$eta_seconds},
      current:{batch:(if $current_batch=="" then null else $current_batch end),message:(if $message=="" then null else $message end)}
    }' >"$progress_tmp"
  mv "$progress_tmp" "$progress"
}

active_pids=()
active_sids=()
final_status=running
last_message=

remember_child_session() {
  local pid=$1
  local sid=
  local runner_sid
  runner_sid=$(ps -o sid= -p $$ | tr -d ' ')
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sid=$(ps -o sid= -p "$pid" 2>/dev/null | tr -d ' ')
    if [[ "$sid" =~ ^[0-9]+$ && "$sid" != "$runner_sid" ]]; then
      active_sids+=("$sid")
      return 0
    fi
    sleep 0.05
  done
  printf 'failed to resolve isolated child session for pid=%s\n' "$pid" >&2
  return 1
}

stop_active_children() {
  local pid sid
  local -a members=()
  for sid in "${active_sids[@]:-}"; do
    [[ "$sid" =~ ^[0-9]+$ ]] || continue
    mapfile -t members < <(ps -eo pid=,sid= | awk -v target="$sid" '$2==target {print $1}')
    if ((${#members[@]})); then
      kill -TERM "${members[@]}" 2>/dev/null || true
    fi
  done
  for _ in 1 2 3 4 5; do
    members=()
    for sid in "${active_sids[@]:-}"; do
      [[ "$sid" =~ ^[0-9]+$ ]] || continue
      while IFS= read -r pid; do [[ -n "$pid" ]] && members+=("$pid"); done \
        < <(ps -eo pid=,sid= | awk -v target="$sid" '$2==target {print $1}')
    done
    ((${#members[@]} == 0)) && break
    sleep 1
  done
  if ((${#members[@]})); then
    kill -KILL "${members[@]}" 2>/dev/null || true
  fi
  for pid in "${active_pids[@]:-}"; do
    [[ -n "$pid" ]] || continue
    wait "$pid" 2>/dev/null || true
  done
  active_pids=()
  active_sids=()
}

on_signal() {
  last_message="rank runner received termination signal"
  stop_active_children
  write_progress stopped "" "$last_message" || true
  exit 143
}
trap on_signal TERM INT

on_exit() {
  local rc=$?
  stop_active_children
  if [[ "$final_status" != complete && "$rc" != 143 ]]; then
    write_progress failed "" "${last_message:-rank runner exited with code $rc}" || true
  fi
}
trap on_exit EXIT

skills_a=(3 3 3 4 4 4 5 5 5 6 6 6)
skills_b=(4 5 6 3 5 6 3 4 6 3 4 5)

choose_batch_size() {
  local remaining=$1
  local candidate
  for candidate in 8 4 2 1; do
    if ((candidate <= lanes_per_gpu && candidate <= remaining)); then
      printf '%s\n' "$candidate"
      return
    fi
  done
  return 1
}

validate_ready_batch() {
  local batch_ready=$1
  local expected_size=$2
  local release
  [[ -s "$batch_ready" ]] || return 1
  jq -e --argjson expected "$expected_size" \
    '.accepted_episodes==$expected and (.episodes|length)==$expected and all(.episodes[];.training_ready==true)' \
    "$batch_ready" >/dev/null || return 1
  while IFS= read -r release; do
    [[ -s "$release/TRAINING_READY.json" ]] || return 1
    jq -e '.training_ready==true and (.gates|all)' "$release/TRAINING_READY.json" >/dev/null || return 1
  done < <(jq -r '.episodes[].release_dir' "$batch_ready")
}

write_progress running "" "rank runner initialized"
printf 'rank_start run_id=%s rank=%s/%s target_episodes=%s lanes=%s utc=%s\n' \
  "$run_id" "$global_rank" "$global_world" "$rank_target_episodes" "$lanes_per_gpu" "$(date -u +%FT%TZ)"

while (( $(completed_count) < rank_target_episodes )); do
  completed=$(completed_count)
  batch_index=$(completed_batch_count)
  remaining=$((rank_target_episodes - completed))
  batch_size=$(choose_batch_size "$remaining")
  batch_base=$(printf '%s_r%s_b%05d_c%d' "$run_id" "$rank_tag" "$batch_index" "$batch_size")
  success=0
  successful_batch_id=
  successful_batch_ready=
  successful_shard=

  for ((attempt=1; attempt<=max_attempts; ++attempt)); do
    batch_id=$(printf '%s_a%02d' "$batch_base" "$attempt")
    batch_dir="$rank_root/batches/$batch_id"
    batch_ready="$batch_dir/BATCH_READY.json"
    accepted_shard="$rank_root/accepted_shards/$batch_id.jsonl"

    if validate_ready_batch "$batch_ready" "$batch_size" && [[ -s "$accepted_shard" ]]; then
      success=1
      successful_batch_id=$batch_id
      successful_batch_ready=$batch_ready
      successful_shard=$accepted_shard
      break
    fi
    if [[ -e "$batch_dir" ]]; then
      printf 'skip_incomplete_attempt batch=%s attempt=%s\n' "$batch_id" "$attempt" >&2
      continue
    fi

    mkdir -p "$batch_dir" "$rank_root/batch_logs/$batch_id"
    plan_jsonl="$batch_dir/episode_plan.jsonl"
    : >"$plan_jsonl"
    demo_ids=()
    render_ids=()
    release_dirs=()
    batch_skill_a=()
    batch_skill_b=()
    batch_pov=()
    batch_global_index=()

    for ((index=0; index<batch_size; ++index)); do
      assigned_offset=$((completed + index))
      episode_index=$((global_rank + assigned_offset * global_world))
      pair_index=$(((episode_index * 7 + schedule_seed) % 12))
      skill_a=${skills_a[$pair_index]}
      skill_b=${skills_b[$pair_index]}
      if ((((episode_index * 5 + episode_index / 12 + schedule_seed) % 2) == 0)); then
        pov_policy=AggressiveClose
      else
        pov_policy=LongRangeEvasive
      fi
      episode_tag=$(printf 'g%06d' "$episode_index")
      demo_id="${batch_id}_${episode_tag}_demo"
      render_id="${batch_id}_${episode_tag}_render"
      demo_ids+=("$demo_id")
      render_ids+=("$render_id")
      release_dirs+=("$output_root/releases/$render_id")
      batch_skill_a+=("$skill_a")
      batch_skill_b+=("$skill_b")
      batch_pov+=("$pov_policy")
      batch_global_index+=("$episode_index")
      jq -c -n \
        --arg demo_id "$demo_id" \
        --arg render_id "$render_id" \
        --arg pov_policy "$pov_policy" \
        --argjson global_episode_index "$episode_index" \
        --argjson skill_a "$skill_a" \
        --argjson skill_b "$skill_b" \
        '{global_episode_index:$global_episode_index,demo_id:$demo_id,render_id:$render_id,skill_a:$skill_a,skill_b:$skill_b,pov_policy:$pov_policy}' \
        >>"$plan_jsonl"
    done
    jq -s \
      --arg schema_version xonotic-duel-v11-production-batch-plan-v1 \
      --arg batch_id "$batch_id" \
      --arg created_at "$(date -u +%FT%TZ)" \
      --argjson global_rank "$global_rank" \
      '{schema_version:$schema_version,batch_id:$batch_id,created_at:$created_at,global_rank:$global_rank,episodes:.}' \
      "$plan_jsonl" >"$batch_dir/PLAN.json"

    write_progress running "$batch_id" "recording concurrent 60-second authoritative rollouts"
    record_start_ns=$(date +%s%N)
    active_pids=()
    active_sids=()
    for ((index=0; index<batch_size; ++index)); do
      log="$rank_root/batch_logs/$batch_id/${demo_ids[$index]}.log"
      setsid env \
        XONOTIC_DUEL_OUTPUT_ROOT="$output_root" \
        XONOTIC_DUEL_RECORD_SCRATCH_ROOT="$scratch_root/record" \
        XONOTIC_DUEL_SETUP_SECONDS=20 \
        bash "$duel_root/scripts/record_demo_only.sh" \
          "$duration" "${demo_ids[$index]}" \
          "${batch_skill_a[$index]}" "${batch_skill_b[$index]}" "${batch_pov[$index]}" \
          >"$log" 2>&1 &
      active_pids+=("$!")
      remember_child_session "$!" || { last_message="record worker session isolation failed"; exit 70; }
    done
    failed=0
    for pid in "${active_pids[@]}"; do
      if ! wait "$pid"; then failed=1; fi
    done
    active_pids=()
    active_sids=()
    record_stop_ns=$(date +%s%N)
    if ((failed)); then
      failure_reason="one or more record workers failed"
    else
      write_progress running "$batch_id" "rendering, labeling visibility, and packaging clips plus 60-second rollouts"
      process_start_ns=$(date +%s%N)
      active_pids=()
      active_sids=()
      for ((index=0; index<batch_size; ++index)); do
        log="$rank_root/batch_logs/$batch_id/${render_ids[$index]}.log"
        setsid env \
          XONOTIC_DUEL_OUTPUT_ROOT="$output_root" \
          XONOTIC_DUEL_SCRATCH_ROOT="$scratch_root/render" \
          XONOTIC_DUEL_VISIBILITY_SCRATCH_ROOT="$scratch_root/visibility" \
          bash "$duel_root/scripts/process_recorded_episode.sh" \
            "${demo_ids[$index]}" "${render_ids[$index]}" \
            >"$log" 2>&1 &
        active_pids+=("$!")
        remember_child_session "$!" || { last_message="processing worker session isolation failed"; exit 70; }
      done
      failed=0
      for pid in "${active_pids[@]}"; do
        if ! wait "$pid"; then failed=1; fi
      done
      active_pids=()
      active_sids=()
      process_stop_ns=$(date +%s%N)
      if ((failed)); then
        failure_reason="one or more full-chain processing workers failed"
      else
        failure_reason=
      fi
    fi

    if [[ -z "$failure_reason" ]]; then
      validation_failed=0
      for release_dir in "${release_dirs[@]}"; do
        if ! jq -e '.training_ready==true and (.gates|all)' "$release_dir/TRAINING_READY.json" >/dev/null; then
          validation_failed=1
        fi
      done
      if ((validation_failed)); then
        failure_reason="one or more releases failed TRAINING_READY gates"
      fi
    fi

    if [[ -n "$failure_reason" ]]; then
      jq -c -n \
        --arg batch_id "$batch_id" \
        --arg failed_at "$(date -u +%FT%TZ)" \
        --arg reason "$failure_reason" \
        --argjson batch_index "$batch_index" \
        --argjson attempt "$attempt" \
        '{batch_index:$batch_index,batch_id:$batch_id,attempt:$attempt,failed_at:$failed_at,reason:$reason}' \
        >>"$failed_attempts"
      printf 'batch_retry batch=%s reason=%s\n' "$batch_id" "$failure_reason" >&2
      continue
    fi

    shard_tmp="$rank_root/accepted_shards/.${batch_id}.$$.tmp"
    : >"$shard_tmp"
    for ((index=0; index<batch_size; ++index)); do
      release_dir=${release_dirs[$index]}
      training_ready="$release_dir/TRAINING_READY.json"
      demo_manifest="$output_root/demos/${demo_ids[$index]}/manifest.json"
      ready_sha=$(sha256sum "$training_ready" | awk '{print $1}')
      jq -c -n \
        --arg schema_version xonotic-duel-v11-production-episode-v1 \
        --arg production_run_id "$run_id" \
        --arg batch_id "$batch_id" \
        --arg demo_id "${demo_ids[$index]}" \
        --arg render_id "${render_ids[$index]}" \
        --arg pov_policy "${batch_pov[$index]}" \
        --arg release_dir "$release_dir" \
        --arg training_ready "$training_ready" \
        --arg training_ready_sha256 "$ready_sha" \
        --arg demo_manifest "$demo_manifest" \
        --arg ar_manifest "$release_dir/ar_training_manifest.jsonl" \
        --arg bidirectional_manifest "$release_dir/bidirectional_training_manifest.jsonl" \
        --argjson global_rank "$global_rank" \
        --argjson global_world "$global_world" \
        --argjson global_episode_index "${batch_global_index[$index]}" \
        --argjson skill_a "${batch_skill_a[$index]}" \
        --argjson skill_b "${batch_skill_b[$index]}" \
        '{
          schema_version:$schema_version,production_run_id:$production_run_id,
          global_rank:$global_rank,global_world:$global_world,global_episode_index:$global_episode_index,
          batch_id:$batch_id,demo_id:$demo_id,render_id:$render_id,
          bots:{aggressive_close_level:$skill_a,long_range_evasive_level:$skill_b,pov_policy:$pov_policy},
          release_dir:$release_dir,training_ready_path:$training_ready,training_ready_sha256:$training_ready_sha256,
          demo_manifest:$demo_manifest,ar_manifest:$ar_manifest,bidirectional_manifest:$bidirectional_manifest,
          training_ready:true
        }' >>"$shard_tmp"
    done
    mv "$shard_tmp" "$accepted_shard"

    record_seconds=$(awk -v a="$record_start_ns" -v b="$record_stop_ns" 'BEGIN {printf "%.6f",(b-a)/1000000000}')
    process_seconds=$(awk -v a="$process_start_ns" -v b="$process_stop_ns" 'BEGIN {printf "%.6f",(b-a)/1000000000}')
    batch_ready_tmp="$batch_dir/.BATCH_READY.$$.tmp"
    jq -s \
      --arg schema_version xonotic-duel-v11-production-batch-ready-v1 \
      --arg batch_id "$batch_id" \
      --arg completed_at "$(date -u +%FT%TZ)" \
      --arg accepted_shard "$accepted_shard" \
      --arg record_seconds "$record_seconds" \
      --arg process_seconds "$process_seconds" \
      --argjson accepted_episodes "$batch_size" \
      '{
        schema_version:$schema_version,batch_id:$batch_id,completed_at:$completed_at,
        accepted_episodes:$accepted_episodes,accepted_shard:$accepted_shard,
        wall_seconds:{record:($record_seconds|tonumber),process_and_package:($process_seconds|tonumber)},
        episodes:.
      }' "$accepted_shard" >"$batch_ready_tmp"
    mv "$batch_ready_tmp" "$batch_ready"
    validate_ready_batch "$batch_ready" "$batch_size" || {
      printf 'newly built batch failed self-validation: %s\n' "$batch_ready" >&2
      exit 70
    }
    success=1
    successful_batch_id=$batch_id
    successful_batch_ready=$batch_ready
    successful_shard=$accepted_shard
    break
  done

  if ((success == 0)); then
    last_message="batch $batch_base exhausted $max_attempts attempts"
    printf '%s\n' "$last_message" >&2
    exit 70
  fi

  jq -c -n \
    --arg batch_id "$successful_batch_id" \
    --arg batch_ready "$successful_batch_ready" \
    --arg accepted_shard "$successful_shard" \
    --arg completed_at "$(date -u +%FT%TZ)" \
    --argjson batch_index "$batch_index" \
    --argjson accepted_episodes "$batch_size" \
    '{batch_index:$batch_index,batch_id:$batch_id,accepted_episodes:$accepted_episodes,batch_ready:$batch_ready,accepted_shard:$accepted_shard,completed_at:$completed_at}' \
    >>"$completed_batches"
  write_progress running "$successful_batch_id" "batch accepted"
  printf 'batch_complete batch=%s accepted=%s rank_completed=%s/%s utc=%s\n' \
    "$successful_batch_id" "$batch_size" "$(completed_count)" "$rank_target_episodes" "$(date -u +%FT%TZ)"
done

accepted_manifest="$rank_root/accepted_episodes.jsonl"
ar_manifest="$rank_root/ar_training_manifest.jsonl"
bidirectional_manifest="$rank_root/bidirectional_training_manifest.jsonl"
accepted_tmp="$rank_root/.accepted_episodes.$$.tmp"
ar_tmp="$rank_root/.ar_training_manifest.$$.tmp"
bidirectional_tmp="$rank_root/.bidirectional_training_manifest.$$.tmp"
: >"$accepted_tmp"
: >"$ar_tmp"
: >"$bidirectional_tmp"

if [[ -s "$completed_batches" ]]; then
  while IFS=$'\t' read -r shard; do
    cat "$shard" >>"$accepted_tmp"
  done < <(jq -r '.accepted_shard' "$completed_batches")
fi

jq -s -e \
  --argjson target "$rank_target_episodes" \
  --argjson rank "$global_rank" \
  --argjson world "$global_world" \
  'length==$target and ([.[].global_episode_index]|unique|length)==$target and all(.[];.global_rank==$rank and .global_world==$world and (.global_episode_index % $world)==$rank and .training_ready==true)' \
  "$accepted_tmp" >/dev/null

while IFS=$'\t' read -r release_dir; do
  jq -e '.training_ready==true and (.gates|all)' "$release_dir/TRAINING_READY.json" >/dev/null
  cat "$release_dir/ar_training_manifest.jsonl" >>"$ar_tmp"
  cat "$release_dir/bidirectional_training_manifest.jsonl" >>"$bidirectional_tmp"
done < <(jq -r '.release_dir' "$accepted_tmp")

expected_training_rows=$((rank_target_episodes * 15))
[[ "$(wc -l <"$ar_tmp")" == "$expected_training_rows" ]] || { printf 'AR row-count mismatch\n' >&2; exit 70; }
[[ "$(wc -l <"$bidirectional_tmp")" == "$expected_training_rows" ]] || { printf 'bidirectional row-count mismatch\n' >&2; exit 70; }
mv "$accepted_tmp" "$accepted_manifest"
mv "$ar_tmp" "$ar_manifest"
mv "$bidirectional_tmp" "$bidirectional_manifest"

sha256sum "$accepted_manifest" "$ar_manifest" "$bidirectional_manifest" >"$rank_root/MANIFEST_SHA256SUMS"
sha256sum -c "$duel_root/protected/STAGE12_BEFORE.sha256" >"$rank_root/stage12_final_check.txt"
sha256sum -c "$duel_root/protected/EXISTING_PIPELINES_BEFORE.sha256" >"$rank_root/existing_pipelines_final_check.txt"
sha256sum -c "$duel_root/protected/DUEL_V5_V6_V7_BEFORE.sha256" >"$rank_root/prior_duel_final_check.txt"

complete_tmp="$rank_root/.RANK_COMPLETE.$$.tmp"
jq -n \
  --arg schema_version xonotic-duel-v11-rank-complete-v1 \
  --arg run_id "$run_id" \
  --arg completed_at "$(date -u +%FT%TZ)" \
  --arg accepted_manifest "$accepted_manifest" \
  --arg ar_manifest "$ar_manifest" \
  --arg bidirectional_manifest "$bidirectional_manifest" \
  --arg checksums "$rank_root/MANIFEST_SHA256SUMS" \
  --argjson global_rank "$global_rank" \
  --argjson global_world "$global_world" \
  --argjson episodes "$rank_target_episodes" \
  --argjson training_rows "$expected_training_rows" \
  '{
    schema_version:$schema_version,run_id:$run_id,completed_at:$completed_at,
    rank:{index:$global_rank,world:$global_world},
    accepted:{episodes:$episodes,seconds:($episodes*60),clips:($episodes*15),ar_rows:$training_rows,bidirectional_rows:$training_rows},
    manifests:{accepted_episodes:$accepted_manifest,ar:$ar_manifest,bidirectional:$bidirectional_manifest,sha256sums:$checksums},
    gates:{all_episode_releases_training_ready:true,rank_local_manifest_only:true,global_merge_deferred:true,stage1_stage2_unchanged:true}
  }' >"$complete_tmp"
mv "$complete_tmp" "$rank_root/RANK_COMPLETE.json"

final_status=complete
write_progress complete "" "rank complete; supervisor must keep the DLC allocation alive"
printf 'rank_complete run_id=%s rank=%s/%s episodes=%s utc=%s\n' \
  "$run_id" "$global_rank" "$global_world" "$rank_target_episodes" "$(date -u +%FT%TZ)"
