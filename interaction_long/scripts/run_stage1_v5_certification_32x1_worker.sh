#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
worker_started_epoch=$(date +%s)
shard_count=${XONOTIC_CERTIFICATION_SHARD_COUNT:-32}
shard_index=
shard_index_source=
if (( $# > 0 )); then
  shard_index=$1
  shard_index_source=argument
elif [[ -n ${SHARD_INDEX:-} ]]; then
  shard_index=$SHARD_INDEX
  shard_index_source=SHARD_INDEX
elif [[ -n ${SENSECORE_PYTORCH_NODE_RANK:-} ]]; then
  shard_index=$SENSECORE_PYTORCH_NODE_RANK
  shard_index_source=SENSECORE_PYTORCH_NODE_RANK
elif [[ -n ${JOB_COMPLETION_INDEX:-} ]]; then
  shard_index=$JOB_COMPLETION_INDEX
  shard_index_source=JOB_COMPLETION_INDEX
elif [[ -n ${RANK:-} ]]; then
  shard_index=$RANK
  shard_index_source=RANK
fi

task_id=${XONOTIC_DISTRIBUTED_TASK_ID:-${SENSECORE_JOB_NAME:-${JOB_ID:-manual}}}
rank_hint=${shard_index:-unknown-host-$$}
safe_task_id=$(printf '%s' "$task_id" | LC_ALL=C tr -c 'A-Za-z0-9._-' '_')
safe_rank_hint=$(printf '%s' "$rank_hint" | LC_ALL=C tr -c 'A-Za-z0-9._-' '_')
[[ -n "$safe_task_id" ]] || safe_task_id=manual
[[ -n "$safe_rank_hint" ]] || safe_rank_hint=unknown
bootstrap_log_root="$root/logs/stage1_v5_certification_32x1/bootstrap/$safe_task_id"
mkdir -p "$bootstrap_log_root" || {
  echo "cannot create persistent worker log directory: $bootstrap_log_root" >&2
  exit 73
}
bootstrap_log="$bootstrap_log_root/rank-${safe_rank_hint}.log"
exec > >(tee -a "$bootstrap_log") 2>&1

echo "stage1_v5_worker_bootstrap_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "bootstrap_log=$bootstrap_log"
echo "hostname=local"
echo "pid=$$"
echo "uid_gid=$(id -u):$(id -g)"
echo "pwd=$PWD"
echo "root=$root"
echo "rank_hint=$rank_hint"
echo "shard_index_source=${shard_index_source:-unset}"
echo "distributed_task_id=$task_id"
echo "sensecore_job_name=${SENSECORE_JOB_NAME:-unset}"
echo "sensecore_pytorch_node_rank=${SENSECORE_PYTORCH_NODE_RANK:-unset}"
echo "sensecore_pytorch_nnodes=${SENSECORE_PYTORCH_NNODES:-unset}"
echo "sensecore_accelerate_device_count=${SENSECORE_ACCELERATE_DEVICE_COUNT:-unset}"
echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
cpu_nproc=$(nproc 2>/dev/null || true)
cpu_affinity=$(
  awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status 2>/dev/null ||
    true
)
echo "cpu_nproc=${cpu_nproc:-unavailable}"
echo "cpu_affinity=${cpu_affinity:-unavailable}"
log_resource_file() {
  local key=$1
  local path=$2
  local value
  if [[ -r "$path" ]]; then
    value=$(tr '\n' ' ' < "$path")
    echo "$key=$value"
  fi
}
log_resource_file cgroup_cpu_max /sys/fs/cgroup/cpu.max
log_resource_file cgroup_cpu_stat /sys/fs/cgroup/cpu.stat
log_resource_file \
  cgroup_cpuset_effective /sys/fs/cgroup/cpuset.cpus.effective
log_resource_file cgroup_memory_max /sys/fs/cgroup/memory.max
log_resource_file cgroup_pids_max /sys/fs/cgroup/pids.max
log_resource_file \
  cgroup_v1_cpu_quota /sys/fs/cgroup/cpu/cpu.cfs_quota_us
log_resource_file \
  cgroup_v1_cpu_period /sys/fs/cgroup/cpu/cpu.cfs_period_us
log_resource_file \
  cgroup_v1_cpuset /sys/fs/cgroup/cpuset/cpuset.cpus

[[ "$shard_count" =~ ^[1-9][0-9]*$ ]] &&
  (( shard_count <= 999 )) || {
  echo "XONOTIC_CERTIFICATION_SHARD_COUNT must be in 1..999" >&2
  exit 64
}
[[ "$shard_index" =~ ^[0-9]+$ ]] || {
  echo "missing or invalid certification shard index" >&2
  exit 64
}
(( shard_index >= 0 && shard_index < shard_count )) || {
  echo "certification shard index out of range: $shard_index" >&2
  exit 64
}
if [[ -n ${SENSECORE_ACCELERATE_DEVICE_COUNT:-} &&
      ${SENSECORE_ACCELERATE_DEVICE_COUNT} != 1 ]]; then
  echo "each certification worker must request exactly one GPU" >&2
  exit 64
fi
if [[ -n ${SENSECORE_PYTORCH_NNODES:-} &&
      ${SENSECORE_PYTORCH_NNODES} != "$shard_count" ]]; then
  echo "certification job must have $shard_count workers" >&2
  exit 64
fi

build_tag=${XONOTIC_BUILD_TAG:-capture-b40e26fd4e33-x86_64}
build_lock="$root/locks/$build_tag.sha256"
env_archive=${XONOTIC_ENV_ARCHIVE:-"$root/env/xonotic-capture-linux-x86_64-20260727.tar.gz"}
path_workers=${XONOTIC_PATH_CERT_WORKERS:-1}
collision_workers=${XONOTIC_COLLISION_CERT_WORKERS:-1}
live_concurrency=${XONOTIC_LIVE_CONCURRENCY:-1}
sdl_concurrency=${XONOTIC_SDL_CONCURRENCY:-1}
live_timeout_seconds=${XONOTIC_LIVE_TIMEOUT_SECONDS:-180}
engine_net_timeout_seconds=${XONOTIC_ENGINE_NET_TIMEOUT_SECONDS:-600}
client_config_overlay=${XONOTIC_CAPTURE_CLIENT_OVERLAY:-}
allow_parallel=${XONOTIC_ALLOW_UNVALIDATED_CERT_CONCURRENCY:-0}
retry_delay_seconds=${STAGE1_V5_OPERATIONAL_RETRY_DELAY_SECONDS:-10}
wait_timeout_seconds=${STAGE1_V5_DISTRIBUTED_WAIT_TIMEOUT_SECONDS:-0}
[[ "$path_workers" =~ ^[1-9][0-9]*$ ]] &&
  (( path_workers <= 32 )) || {
  echo "XONOTIC_PATH_CERT_WORKERS must be in 1..32" >&2
  exit 64
}
[[ "$collision_workers" =~ ^[1-9][0-9]*$ ]] &&
  (( collision_workers <= 12 )) || {
  echo "XONOTIC_COLLISION_CERT_WORKERS must be in 1..12" >&2
  exit 64
}
[[ "$live_concurrency" =~ ^[1-9][0-9]*$ ]] || {
  echo "XONOTIC_LIVE_CONCURRENCY must be a positive integer" >&2
  exit 64
}
[[ "$sdl_concurrency" =~ ^[1-9][0-9]*$ ]] || {
  echo "XONOTIC_SDL_CONCURRENCY must be a positive integer" >&2
  exit 64
}
[[ "$live_timeout_seconds" =~ ^[1-9][0-9]*$ ]] &&
  (( live_timeout_seconds >= 30 && live_timeout_seconds <= 3600 )) || {
  echo "XONOTIC_LIVE_TIMEOUT_SECONDS must be in 30..3600" >&2
  exit 64
}
[[ "$engine_net_timeout_seconds" =~ ^[1-9][0-9]*$ ]] &&
  (( engine_net_timeout_seconds >= 60 &&
     engine_net_timeout_seconds <= 7200 &&
     engine_net_timeout_seconds > live_timeout_seconds )) || {
  echo "XONOTIC_ENGINE_NET_TIMEOUT_SECONDS must be in 60..7200 and greater than XONOTIC_LIVE_TIMEOUT_SECONDS" >&2
  exit 64
}
if [[ -n "$client_config_overlay" ]]; then
  [[ "$client_config_overlay" != /* &&
     "$client_config_overlay" != *".."* &&
     -r "$root/$client_config_overlay" ]] || {
    echo "XONOTIC_CAPTURE_CLIENT_OVERLAY must be a readable root-relative path without '..'" >&2
    exit 64
  }
fi
[[ "$retry_delay_seconds" =~ ^[1-9][0-9]*$ ]] &&
  (( retry_delay_seconds <= 300 )) || {
  echo "STAGE1_V5_OPERATIONAL_RETRY_DELAY_SECONDS must be in 1..300" >&2
  exit 64
}
[[ "$allow_parallel" == 0 || "$allow_parallel" == 1 ]] || {
  echo "XONOTIC_ALLOW_UNVALIDATED_CERT_CONCURRENCY must be 0 or 1" >&2
  exit 64
}
if [[ "$allow_parallel" != 1 ]] &&
   (( path_workers != 1 || collision_workers != 1 ||
      live_concurrency != 1 || sdl_concurrency != 1 )); then
  echo "SenseCore certification is validated only at one SDL client per GPU; set XONOTIC_ALLOW_UNVALIDATED_CERT_CONCURRENCY=1 only for bounded benchmarks" >&2
  exit 64
fi
[[ "$wait_timeout_seconds" =~ ^[0-9]+$ ]] || {
  echo "STAGE1_V5_DISTRIBUTED_WAIT_TIMEOUT_SECONDS must be zero (unlimited) or a positive integer" >&2
  exit 64
}
[[ -r "$build_lock" && -r "$env_archive" &&
   -r "${env_archive}.sha256" ]] || {
  echo "locked build or portable environment is missing" >&2
  exit 66
}

fingerprint_files=(
  XONOTIC_DATA_SPEC_V2.md
  scripts/cci_node_bootstrap.sh
  scripts/cci_node_preflight.sh
  scripts/cci_prepare_nvidia_egl_runtime.sh
  scripts/certify_stage1_v5_paths.py
  scripts/xonotic_capture.py
  scripts/merge_stage1_v5_certificate_shards.py
  scripts/prepare_stage1_v5_manifests.py
  scripts/launch_stage1_v5_certification_worker_logged.sh
  scripts/run_stage1_v5_certification_32x1_worker.sh
  scripts/finalize_stage1_v5_production_readiness.sh
  configs/capture_client.cfg
  configs/capture_server.cfg
  manifests/stage1_foundation_v5_certification/PROTOTYPE_METADATA.json
  manifests/stage1_foundation_v5_certification/CERTIFICATION_SPARE_PROTOTYPE_METADATA.json
  manifests/stage1_foundation_v5_certification/TARGETED_PROTOTYPE_METADATA.json
  manifests/stage1_foundation_v5_certification/FAST_TRAVERSAL_WORLD_PROTOTYPE_METADATA.json
  manifests/stage1_foundation_v5_certification/path_prototypes_primary.jsonl
  manifests/stage1_foundation_v5_certification/path_prototypes_replenishment.jsonl
  manifests/stage1_foundation_v5_certification/path_prototypes_certification_spare.jsonl
  manifests/stage1_foundation_v5_certification/path_prototypes_targeted_visible_collision.jsonl
  manifests/stage1_foundation_v5_certification/path_prototypes_targeted_fast_traversal_world_balanced.jsonl
  runtime/nvidia/580.95.05/MANIFEST.sha256
  "locks/$build_tag.sha256"
)
if [[ -n "$client_config_overlay" ]]; then
  fingerprint_files+=("$client_config_overlay")
fi
for relative in "${fingerprint_files[@]}"; do
  [[ -r "$root/$relative" ]] || {
    echo "certification fingerprint input missing: $relative" >&2
    exit 66
  }
done
run_fingerprint=$(
  (
    cd "$root"
    sha256sum "${fingerprint_files[@]}" | awk '{print $1}'
    sha256sum "$env_archive" "${env_archive}.sha256" | awk '{print $1}'
  ) | sha256sum | awk '{print $1}'
)
run_id=${run_fingerprint:0:20}
run_root="$root/stage1_path_certification_v5/distributed_runs/$run_id/tasks/$safe_task_id"
completion_root="$run_root/completed"
journal_root="$run_root/journals"
event_root="$run_root/events"
ready_marker="$run_root/FORMAL_READY.json"
failed_marker="$run_root/FORMAL_FAILED.json"
tag=$(printf 'shard-%03d-of-%03d' "$shard_index" "$shard_count")
tmp_root=${XONOTIC_CAPTURE_TMP:-${TMPDIR:-./tmp}/xonotic-stage1-v5-certification/${safe_task_id}-${tag}}
log_root="$root/logs/stage1_v5_certification_32x1/$run_id/tasks/$safe_task_id"
log="$log_root/$tag.log"
mkdir -p \
  "$completion_root" "$journal_root" "$event_root" "$log_root" "$tmp_root"
if [[ ! -e "$log" && ! -L "$log" ]]; then
  ln -s "$bootstrap_log" "$log" || {
    echo "warning: could not create run-log link: $log" >&2
  }
fi
export XONOTIC_CAPTURE_ROOT="$root"
export XONOTIC_CAPTURE_TMP="$tmp_root"
export XONOTIC_BUILD_GLOB="build/$build_tag"
export XONOTIC_BUILD_TAG="$build_tag"
export XONOTIC_ENV_ARCHIVE="$env_archive"
export XONOTIC_LIVE_CONCURRENCY="$live_concurrency"
export XONOTIC_SDL_CONCURRENCY="$sdl_concurrency"
export XONOTIC_LIVE_TIMEOUT_SECONDS="$live_timeout_seconds"
export XONOTIC_ENGINE_NET_TIMEOUT_SECONDS="$engine_net_timeout_seconds"
export XONOTIC_CAPTURE_CLIENT_OVERLAY="$client_config_overlay"
export SDL_VIDEODRIVER=offscreen
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=opengl

echo "stage1_v5_distributed_certification_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "run_log=$log"
echo "shard_index=$shard_index"
echo "shard_index_source=$shard_index_source"
echo "shard_count=$shard_count"
echo "run_id=$run_id"
echo "run_fingerprint=$run_fingerprint"
echo "run_root=$run_root"
echo "journal_root=$journal_root"
echo "tmp_root=$tmp_root"
echo "path_workers=$path_workers"
echo "collision_workers=$collision_workers"
echo "live_concurrency=$live_concurrency"
echo "sdl_concurrency=$sdl_concurrency"
echo "live_timeout_seconds=$live_timeout_seconds"
echo "engine_net_timeout_seconds=$engine_net_timeout_seconds"
echo "capture_client_overlay=${client_config_overlay:-none}"
echo "operational_retry_delay_seconds=$retry_delay_seconds"
echo "distributed_wait_timeout_seconds=$wait_timeout_seconds"
echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"

sha256sum -c "$build_lock" >/dev/null
echo "build_integrity=pass"
"$script_dir/cci_node_preflight.sh"

run_wave_once() {
  local wave=$1
  local workers=$2
  local ordinal_end=${3:-0}
  local status
  local -a command=(
    "$script_dir/cci_run.sh"
    python "$script_dir/certify_stage1_v5_paths.py"
    --wave "$wave"
    --workers "$workers"
    --port-base 32000
    --max-attempts 1
    --shard-index "$shard_index"
    --shard-count "$shard_count"
    --terminal-journal "$journal_root/$tag.jsonl"
    --event-journal "$event_root/$tag.$wave.jsonl"
  )
  if (( ordinal_end > 0 )); then
    command+=(--ordinal-end "$ordinal_end")
  fi
  set +e
  "${command[@]}"
  status=$?
  set -e
  return "$status"
}

waves=(
  targeted_fast_world
  certification_spare
  primary
  replenishment
  targeted_collision
)
wave_workers=(
  "$path_workers"
  "$path_workers"
  "$path_workers"
  "$path_workers"
  "$collision_workers"
)

wave_ordinal_ends=(1024 0 0 0 0)
wave_done=(0 0 0 0 0)




for wave_index in "${!waves[@]}"; do
  wave=${waves[$wave_index]}
  echo "certification_wave=$wave phase=initial"
  if run_wave_once \
      "$wave" \
      "${wave_workers[$wave_index]}" \
      "${wave_ordinal_ends[$wave_index]}"; then
    wave_done[$wave_index]=1
    continue
  else
    status=$?
  fi
  echo "certification_wave=$wave phase=initial status=$status"
  if (( status != 2 )); then
    echo "certification wave structural failure: $wave status=$status" >&2
    exit "$status"
  fi
done

retry_cycle=0
while true; do
  pending_waves=0
  for wave_index in "${!waves[@]}"; do
    if (( wave_done[$wave_index] == 0 )); then
      ((pending_waves += 1))
    fi
  done
  (( pending_waves == 0 )) && break

  ((retry_cycle += 1))
  echo "operational_retry_cycle=$retry_cycle pending_waves=$pending_waves"
  for wave_index in "${!waves[@]}"; do
    (( wave_done[$wave_index] == 0 )) || continue
    wave=${waves[$wave_index]}
    echo "certification_wave=$wave phase=drain retry_cycle=$retry_cycle"
    if run_wave_once \
        "$wave" \
        "${wave_workers[$wave_index]}" \
        "${wave_ordinal_ends[$wave_index]}"; then
      wave_done[$wave_index]=1
      echo "certification_wave=$wave phase=drain complete=true"
      continue
    else
      status=$?
    fi
    echo "certification_wave=$wave phase=drain status=$status"
    if (( status != 2 )); then
      echo "certification wave structural failure: $wave status=$status" >&2
      exit "$status"
    fi
  done

  pending_waves=0
  for wave_index in "${!waves[@]}"; do
    if (( wave_done[$wave_index] == 0 )); then
      ((pending_waves += 1))
    fi
  done
  if (( pending_waves > 0 )); then
    echo "operational_retry_sleep_seconds=$retry_delay_seconds pending_waves=$pending_waves"
    sleep "$retry_delay_seconds"
  fi
done

marker="$completion_root/$tag.json"
"$script_dir/cci_run.sh" python - \
  "$root" "$marker" "$journal_root/$tag.jsonl" \
  "$shard_index" "$shard_count" \
  "$run_id" "$run_fingerprint" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1])
marker = Path(sys.argv[2])
journal_path = Path(sys.argv[3])
shard_index = int(sys.argv[4])
shard_count = int(sys.argv[5])
run_id = sys.argv[6]
fingerprint = sys.argv[7]
specs = (
    ("targeted_fast_world", "path_prototypes_targeted_fast_traversal_world_balanced.jsonl", 1024),
    ("certification_spare", "path_prototypes_certification_spare.jsonl", 0),
    ("primary", "path_prototypes_primary.jsonl", 0),
    ("replenishment", "path_prototypes_replenishment.jsonl", 0),
    ("targeted_collision", "path_prototypes_targeted_visible_collision.jsonl", 0),
)
candidate_root = root / "manifests/stage1_foundation_v5_certification"
indexed: dict[str, dict] = {}
for line_number, line in enumerate(
    journal_path.read_text(encoding="utf-8").splitlines(), start=1
):
    row = json.loads(line)
    prototype_id = str(row["prototype_id"])
    if prototype_id in indexed:
        raise SystemExit(
            f"duplicate terminal journal row: "
            f"{journal_path}:{line_number}:{prototype_id}"
        )
    indexed[prototype_id] = row
wave_status: dict[str, dict[str, int]] = {}
expected_total = 0
expected_ids: set[str] = set()
for wave, filename, ordinal_end in specs:
    rows = [
        json.loads(line)
        for line in (candidate_root / filename).read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    selected = [
        row
        for row in rows
        if (int(row["candidate_ordinal"]) - 1) % shard_count
        == shard_index
        and (not ordinal_end or int(row["candidate_ordinal"]) <= ordinal_end)
    ]
    missing = []
    for row in selected:
        prototype_id = str(row["episode_id"])
        expected_ids.add(prototype_id)
        indexed_row = indexed.get(prototype_id)
        certificate_path = (
            root
            / "stage1_path_certification_v5/certificates"
            / prototype_id
            / "CERTIFICATE.json"
        )
        rejection_path = (
            root
            / "stage1_path_certification_v5/rejects"
            / prototype_id
            / "REJECTION.json"
        )
        terminals = [
            path
            for path in (certificate_path, rejection_path)
            if path.is_file()
        ]
        if indexed_row is None or len(terminals) != 1:
            missing.append(prototype_id)
            continue
        if indexed_row.get("status") == "certified":
            if terminals[0] != certificate_path:
                raise SystemExit(
                    f"journal/artifact terminal mismatch: {prototype_id}"
                )
            digest = hashlib.sha256(
                certificate_path.read_bytes()
            ).hexdigest()
            if indexed_row.get("certificate_sha256") != digest:
                raise SystemExit(
                    f"journal/certificate hash mismatch: {prototype_id}"
                )
        elif indexed_row.get("status") == "rejected":
            if terminals[0] != rejection_path:
                raise SystemExit(
                    f"journal/artifact terminal mismatch: {prototype_id}"
                )
            if indexed_row != json.loads(
                rejection_path.read_text(encoding="utf-8")
            ):
                raise SystemExit(
                    f"journal/rejection mismatch: {prototype_id}"
                )
        else:
            missing.append(prototype_id)
    if missing:
        raise SystemExit(
            f"{wave}: {len(missing)} nonterminal prototypes; first={missing[:3]}"
        )
    counts = Counter(indexed[row["episode_id"]]["status"] for row in selected)
    wave_status[wave] = dict(sorted(counts.items()))
    expected_total += len(selected)
unexpected = sorted(set(indexed) - expected_ids)
if unexpected:
    raise SystemExit(
        f"unexpected rows in shard journal: {unexpected[:3]}"
    )
digest = hashlib.sha256(journal_path.read_bytes()).hexdigest()
report = {
    "schema_version": "xonotic-stage1-v5-distributed-certification-worker-v1",
    "run_id": run_id,
    "run_fingerprint": fingerprint,
    "shard_index": shard_index,
    "shard_count": shard_count,
    "expected_terminal_prototypes": expected_total,
    "wave_status": wave_status,
    "terminal_journal": str(journal_path.resolve().relative_to(root.resolve())),
    "terminal_journal_sha256": digest,
}
payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
marker.parent.mkdir(parents=True, exist_ok=True)
temporary = marker.with_name(f".{marker.name}.tmp.{os.getpid()}")
temporary.write_text(payload, encoding="utf-8")
os.replace(temporary, marker)
print(payload, end="")
PY

echo "certification_worker_marker=$marker"
deadline=0
if (( wait_timeout_seconds > 0 )); then
  deadline=$(( $(date +%s) + wait_timeout_seconds ))
fi
if (( shard_index == 0 )); then
  while true; do
    complete_count=$(
      python3 - \
        "$completion_root" "$run_fingerprint" "$shard_count" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
fingerprint = sys.argv[2]
shard_count = int(sys.argv[3])
valid = set()
for path in root.glob(f"shard-*-of-{shard_count:03d}.json"):
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    if (
        row.get("run_fingerprint") == fingerprint
        and row.get("shard_count") == shard_count
        and isinstance(row.get("shard_index"), int)
        and 0 <= row["shard_index"] < shard_count
    ):
        valid.add(row["shard_index"])
print(len(valid))
PY
    )
    echo "distributed_completion=$complete_count/$shard_count"
    (( complete_count == shard_count )) && break
    if (( deadline > 0 && $(date +%s) >= deadline )); then
      echo "timed out waiting for $shard_count certification workers" >&2
      exit 75
    fi
    sleep 10
  done

  exec 8>"$run_root/formalize.lock"
  flock 8
  if [[ ! -r "$ready_marker" ]]; then
    if [[ -r "$failed_marker" ]]; then
      mv "$failed_marker" \
        "$run_root/FORMAL_FAILED.previous.$(date -u +%Y%m%dT%H%M%SZ).json"
    fi
    trap 'status=$?; if (( status != 0 )); then python3 - "$failed_marker" "$run_id" "$run_fingerprint" "$status" <<'"'"'PY'"'"'
import json
import os
import sys
from pathlib import Path
path = Path(sys.argv[1])
payload = {
    "schema_version": "xonotic-stage1-v5-distributed-formal-failure-v1",
    "run_id": sys.argv[2],
    "run_fingerprint": sys.argv[3],
    "exit_status": int(sys.argv[4]),
}
temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
os.replace(temporary, path)
PY
fi; exit "$status"' EXIT
    merge_report="$run_root/CERTIFICATE_INDEX_MERGE.json"
    "$script_dir/cci_run.sh" \
      python "$script_dir/merge_stage1_v5_certificate_shards.py" \
      --root "$root" \
      --journal-root "$journal_root" \
      --shard-count "$shard_count" \
      --run-id "$run_id" \
      --run-fingerprint "$run_fingerprint" \
      --report "$merge_report"
    STAGE1_V5_DISTRIBUTED_COMPLETION_ROOT="$completion_root" \
    STAGE1_V5_DISTRIBUTED_RUN_FINGERPRINT="$run_fingerprint" \
    STAGE1_V5_DISTRIBUTED_INDEX_MERGE_REPORT="$merge_report" \
    STAGE1_V5_DISTRIBUTED_SHARD_COUNT="$shard_count" \
      "$script_dir/finalize_stage1_v5_production_readiness.sh"
    "$script_dir/cci_run.sh" python - \
      "$ready_marker" "$root" "$run_id" "$run_fingerprint" \
      "$merge_report" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
root = Path(sys.argv[2])
metadata = root / "manifests/stage1_foundation_v5_formal/MANIFEST_METADATA.json"
audit = root / "manifests/stage1_foundation_v5_formal/MANIFEST_AUDIT.json"
digest = lambda value: hashlib.sha256(value.read_bytes()).hexdigest()
payload = {
    "schema_version": "xonotic-stage1-v5-distributed-formal-ready-v1",
    "run_id": sys.argv[3],
    "run_fingerprint": sys.argv[4],
    "metadata_sha256": digest(metadata),
    "audit_sha256": digest(audit),
    "certificate_index_merge_sha256": digest(Path(sys.argv[5])),
}
temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
os.replace(temporary, path)
print(json.dumps(payload, indent=2, sort_keys=True))
PY
    trap - EXIT
  fi
  flock -u 8
fi

while [[ ! -r "$ready_marker" ]]; do
  if [[ -r "$failed_marker" ]] &&
     (( $(stat -c %Y "$failed_marker") >= worker_started_epoch )); then
    echo "rank 0 formalization failed: $failed_marker" >&2
    exit 2
  fi
  if (( deadline > 0 && $(date +%s) >= deadline )); then
    echo "timed out waiting for formal readiness marker" >&2
    exit 75
  fi
  sleep 10
done
python3 - "$ready_marker" "$run_fingerprint" <<'PY'
import json
import sys
row = json.load(open(sys.argv[1], encoding="utf-8"))
if row.get("run_fingerprint") != sys.argv[2]:
    raise SystemExit("formal readiness fingerprint mismatch")
print(json.dumps(row, indent=2, sort_keys=True))
PY
echo "stage1_v5_distributed_certification_completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
