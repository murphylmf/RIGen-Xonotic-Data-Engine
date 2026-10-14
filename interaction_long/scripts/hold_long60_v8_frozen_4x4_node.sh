#!/usr/bin/env bash

set -euo pipefail

collection_root=${LONG60_COLLECTION_ROOT:?LONG60_COLLECTION_ROOT is required}
run_id=${LONG60_HOLD_RUN_ID:-${JOB_ID:-${DLC_JOB_ID:-long60-frozen-hold}}}
expected_accepted=${LONG60_EXPECTED_ACCEPTED:-1791}
marker="$collection_root/control/FROZEN.json"

resolve_node_rank() {
  local candidate name
  for candidate in \
    "${NODE_RANK:-}" \
    "${PET_NODE_RANK:-}" \
    "${RANK:-}" \
    "${WORKER_RANK:-}" \
    "${SENSECORE_PYTORCH_NODE_RANK:-}"; do
    if [[ "$candidate" =~ ^[0-9]+$ ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  name=${POD_NAME:-}
  if [[ "$name" =~ -master-([0-9]+)$ ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "$name" =~ -worker-([0-9]+)$ ]]; then
    printf '%s\n' "$((BASH_REMATCH[1] + 1))"
    return 0
  fi
  return 1
}

node_rank=$(resolve_node_rank) || {
  echo "unable to resolve DLC node rank" >&2
  exit 64
}
visible_gpus=$(nvidia-smi -L | wc -l)
(( visible_gpus == 4 )) || {
  echo "whole-node hold requires 4 visible GPUs; got $visible_gpus" >&2
  exit 69
}
[[ -r "$marker" ]] || {
  echo "freeze marker missing: $marker" >&2
  exit 66
}

marker_summary=$(
  ./environment - "$marker" "$expected_accepted" <<'PY'
import hashlib
import json
import pathlib
import sys

marker_path = pathlib.Path(sys.argv[1])
expected = int(sys.argv[2])
marker = json.loads(marker_path.read_text(encoding="utf-8"))
if marker.get("frozen") is not True or int(marker.get("accepted_count", -1)) != expected:
    raise SystemExit("invalid freeze marker")
snapshot = pathlib.Path(marker["accepted_snapshot"])
digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
if digest != marker["accepted_snapshot_sha256"]:
    raise SystemExit("frozen accepted snapshot hash mismatch")
print(f"accepted={expected} snapshot_sha256={digest}")
PY
)

echo "long60_frozen_hold_start utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) run_id=$run_id node_rank=$node_rank visible_gpus=$visible_gpus $marker_summary"
while :; do
  echo "long60_frozen_hold_heartbeat utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) run_id=$run_id node_rank=$node_rank $marker_summary"
  sleep 300
done
