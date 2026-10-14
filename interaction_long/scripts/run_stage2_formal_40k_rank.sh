#!/usr/bin/env bash
set -euo pipefail

workspace=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
shard_count=${STAGE2_SHARD_COUNT:?set STAGE2_SHARD_COUNT to 32 or 56}
cohort=${STAGE2_COHORT:-primary}
rank=${STAGE2_RANK:-${SENSECORE_PYTORCH_NODE_RANK:-${JOB_COMPLETION_INDEX:-${RANK:-}}}}
job_id=${STAGE2_JOB_ID:-${SENSECORE_JOB_NAME:-${JOB_ID:-"stage2_formal_40k_v1_${shard_count}x1"}}}
source_commit=82bf40a4ddeebefefb97feb58afa85766a27f58e
lanes=8
gang_nonfatal_incomplete=${STAGE2_GANG_NONFATAL_INCOMPLETE:-1}

if [[ "$shard_count" != 32 && "$shard_count" != 56 ]]; then
  echo "STAGE2_SHARD_COUNT must be 32 or 56" >&2
  exit 64
fi
if [[ "$cohort" != primary && "$cohort" != reserve ]]; then
  echo "STAGE2_COHORT must be primary or reserve" >&2
  exit 64
fi
if [[ ! "$rank" =~ ^[0-9]+$ ]] || (( rank < 0 || rank >= shard_count )); then
  echo "rank must come from SENSECORE_PYTORCH_NODE_RANK, JOB_COMPLETION_INDEX, RANK, or STAGE2_RANK in [0,$((shard_count - 1))]" >&2
  exit 64
fi
if [[ "$gang_nonfatal_incomplete" != 0 &&
      "$gang_nonfatal_incomplete" != 1 ]]; then
  echo "STAGE2_GANG_NONFATAL_INCOMPLETE must be 0 or 1" >&2
  exit 64
fi

rank_padded=$(printf '%03d' "$rank")
count_padded=$(printf '%03d' "$shard_count")
manifest_root="${workspace}/manifests/stage2_formal_40k_v1/${cohort}"
input_manifest="${manifest_root}/shards-${count_padded}/shard-${rank_padded}-of-${count_padded}.jsonl"
metadata="${manifest_root}/MANIFEST_METADATA.json"
output_root=${STAGE2_OUTPUT_ROOT:-"${workspace}/stage2_formal_40k_v1_output/${shard_count}x1/${cohort}"}
tmp_root=${STAGE2_TMP_ROOT:-"./tmp/xonotic-stage2-formal-40k-v1-${job_id}-${cohort}-rank${rank_padded}"}
log_root="${workspace}/logs/stage2_formal_40k_v1/${job_id}/${cohort}/rank-${rank_padded}"
port_offset=0
if [[ "$cohort" == reserve ]]; then
  port_offset=50
fi
port_base=$((20000 + rank * 100 + port_offset))
allowed_cpus=$(awk '/^Cpus_allowed_list:/{print $2}' /proc/self/status)

if [[ ! -s "$input_manifest" || ! -s "$metadata" ]]; then
  echo "missing immutable manifest or metadata: $input_manifest $metadata" >&2
  exit 66
fi
if [[ -z "$allowed_cpus" ]]; then
  echo "could not resolve container CPU affinity" >&2
  exit 70
fi

mkdir -p "$log_root" "$tmp_root"
export XONOTIC_BUILD_GLOB=build/capture-82bf40a4ddee-x86_64
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl
export XONOTIC_LIVE_TIMEOUT_SECONDS=${STAGE2_LIVE_TIMEOUT_SECONDS:-360}

cd "$workspace"
exec > >(tee -a "${log_root}/run.log") 2>&1
echo "stage2_rank_start job_id=${job_id} cohort=${cohort} rank=${rank}/${shard_count} gpu_visible=${CUDA_VISIBLE_DEVICES:-unset} cpus=${allowed_cpus} manifest=${input_manifest} gang_nonfatal_incomplete=${gang_nonfatal_incomplete}"
set +e
scripts/cci_run.sh python scripts/run_capture_manifest_shard_formal.py run \
  --input-manifest "$input_manifest" \
  --manifest-metadata "$metadata" \
  --output-root "$output_root" \
  --shard-index "$rank" \
  --shard-count "$shard_count" \
  --workers "$lanes" \
  --live-concurrency "$lanes" \
  --render-concurrency "$lanes" \
  --render-timeout-seconds 240 \
  --sdl-concurrency "$lanes" \
  --encode-concurrency 4 \
  --x264-threads 16 \
  --x264-cpuset "$allowed_cpus" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent 5 \
  --port-base "$port_base" \
  --tmp-root "$tmp_root" \
  --gpu-index 0 \
  --max-operational-attempts 3
run_rc=$?
set -e

if (( run_rc == 0 )); then
  echo "stage2_rank_disposition=complete"
  exit 0
fi

result_path="${output_root}/manifests/shards/shard-${rank_padded}-of-${count_padded}/RUN_RESULT.json"
if [[ "$gang_nonfatal_incomplete" == 1 && "$run_rc" == 2 &&
      -s "$result_path" ]]; then
  set +e
  scripts/cci_run.sh python -c \
    'import json,sys; value=json.load(open(sys.argv[1])); raise SystemExit(0 if value.get("pass") is False and value.get("finished_utc") else 1)' \
    "$result_path"
  result_is_incomplete=$?
  set -e
  if (( result_is_incomplete == 0 )); then
    echo "stage2_rank_disposition=incomplete_preserved"
    echo "stage2_rank_recovery=monitor_then_select_operational_reserve"
    echo "stage2_rank_gang_exit=0"
    exit 0
  fi
fi

echo "stage2_rank_disposition=fatal run_rc=${run_rc}" >&2
exit "$run_rc"
