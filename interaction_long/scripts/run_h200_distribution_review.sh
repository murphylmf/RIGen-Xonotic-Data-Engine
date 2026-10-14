#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
benchmark_summary=${H200_BENCHMARK_SUMMARY:-"$root/benchmarks/h200_staged_20260727/BENCHMARK_SUMMARY.json"}
manifest_root=${H200_REVIEW_MANIFEST_ROOT:-"$root/manifests/stage1_distribution_review_63bfb795"}
input_manifest=${H200_REVIEW_INPUT_MANIFEST:-"$manifest_root/shard-000-of-001.jsonl"}
manifest_metadata=${H200_REVIEW_MANIFEST_METADATA:-"$manifest_root/MANIFEST_METADATA.json"}
output_root=${H200_REVIEW_OUTPUT_ROOT:-"$root/stage1_distribution_review_63bfb795_output"}
tmp_root=${H200_REVIEW_TMP_ROOT:-"./tmp/xonotic_capture/stage1-distribution-review-63bfb795"}
log_path=${H200_REVIEW_LOG:-"$root/logs/h200_distribution_review_20260727.log"}
source_commit=${H200_REVIEW_SOURCE_COMMIT:-"63bfb795faca21ad3db6dff7632171a13223cd76"}
port_base=${H200_REVIEW_PORT_BASE:-38000}
raw_audit_percent=${H200_REVIEW_RAW_AUDIT_PERCENT:-2}
render_timeout_seconds=${H200_REVIEW_RENDER_TIMEOUT_SECONDS:-240}
build_name=capture-63bfb795faca-x86_64
build_lock=${H200_REVIEW_BUILD_LOCK:-"$root/locks/${build_name}.sha256"}
min_afs_free_bytes=${H200_REVIEW_MIN_AFS_FREE_BYTES:-2000000000000}

verify_relocated_build_lock() {
  local digest locked_path relative
  while read -r digest locked_path; do
    [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || return 65
    relative=${locked_path#*"$build_name"/}
    [[ "$relative" != "$locked_path" &&
       "$relative" != /* &&
       "$relative" != *..* ]] || return 65
    printf '%s  %s/build/%s/%s\n' \
      "$digest" "$root" "$build_name" "$relative"
  done < "$build_lock"
}

[[ -f "$benchmark_summary" ]] || {
  echo "benchmark summary missing: $benchmark_summary" >&2
  exit 66
}
[[ -f "$input_manifest" && -f "$manifest_metadata" ]] || {
  echo "review manifest or metadata missing" >&2
  exit 66
}
[[ -r "$build_lock" ]] || {
  echo "build lock missing: $build_lock" >&2
  exit 66
}
[[ "$min_afs_free_bytes" =~ ^[0-9]+$ ]] || {
  echo "invalid H200_REVIEW_MIN_AFS_FREE_BYTES" >&2
  exit 64
}
afs_free_bytes=$(df -PB1 "$root" | awk 'NR==2 {print $4}')
(( afs_free_bytes >= min_afs_free_bytes )) || {
  echo "insufficient AFS space: have=$afs_free_bytes require=$min_afs_free_bytes" >&2
  exit 75
}
verify_relocated_build_lock | sha256sum -c - >/dev/null

mapfile -t schedule < <(
  jq -r '
    .recommended |
    .pipelines,
    .live_concurrency,
    .render_concurrency,
    .sdl_concurrency,
    .encode_concurrency,
    .x264_threads,
    (.x264_cpuset // "")
  ' "$benchmark_summary"
)
(( ${#schedule[@]} == 7 )) || {
  echo "invalid scheduling summary" >&2
  exit 65
}
pipelines=${schedule[0]}
live=${schedule[1]}
render=${schedule[2]}
sdl=${schedule[3]}
encode=${schedule[4]}
threads=${schedule[5]}
cpuset=${schedule[6]}
for value in \
  "$pipelines" "$live" "$render" "$sdl" "$encode" "$threads" \
  "$port_base" "$raw_audit_percent"; do
  [[ "$value" =~ ^[0-9]+$ ]] || {
    echo "invalid numeric scheduling value: $value" >&2
    exit 64
  }
done

mkdir -p "$(dirname -- "$log_path")"
exec > >(tee -a "$log_path") 2>&1

echo "__H200_DISTRIBUTION_REVIEW_START__:$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "input_manifest=$input_manifest"
echo "input_manifest_sha256=$(sha256sum "$input_manifest" | awk '{print $1}')"
echo "output_root=$output_root"
echo "pipelines=$pipelines live=$live render=$render render_timeout_seconds=$render_timeout_seconds sdl=$sdl encode=$encode threads=$threads cpuset=${cpuset:-unbound}"
echo "raw_audit_percent=$raw_audit_percent"

export XONOTIC_CAPTURE_ROOT="$root"
export XONOTIC_BUILD_GLOB="build/$build_name"
set +e
bash "$script_dir/cci_run.sh" python \
  "$script_dir/run_capture_manifest_shard.py" run \
  --input-manifest "$input_manifest" \
  --manifest-metadata "$manifest_metadata" \
  --output-root "$output_root" \
  --shard-index 0 \
  --shard-count 1 \
  --workers "$pipelines" \
  --live-concurrency "$live" \
  --render-concurrency "$render" \
  --render-timeout-seconds "$render_timeout_seconds" \
  --sdl-concurrency "$sdl" \
  --encode-concurrency "$encode" \
  --x264-threads "$threads" \
  --x264-cpuset "$cpuset" \
  --expected-source-commit "$source_commit" \
  --raw-audit-percent "$raw_audit_percent" \
  --port-base "$port_base" \
  --tmp-root "$tmp_root" \
  --max-operational-attempts 2
capture_rc=$?
set -e
set +e
bash "$script_dir/cci_run.sh" python \
  "$script_dir/analyze_h200_distribution_review.py" \
  --input-manifest "$input_manifest" \
  --output-root "$output_root" \
  --make-thumbnails
analysis_rc=$?
set -e

echo "__H200_DISTRIBUTION_REVIEW_DONE__:capture_rc=${capture_rc}:analysis_rc=${analysis_rc}:$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if (( analysis_rc != 0 )); then
  exit "$analysis_rc"
fi
exit "$capture_rc"
