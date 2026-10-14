#!/usr/bin/env bash
set -euo pipefail

if (($# < 3)); then
  printf 'usage: %s LOG_DIR LABEL COMMAND [ARG ...]\n' "$0" >&2
  exit 64
fi

log_dir=$1
label=$2
shift 2
mkdir -p "$log_dir"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
log_path="$log_dir/${timestamp}_${label}.log"
status_path="$log_dir/${timestamp}_${label}.status"
rc_path=$(mktemp "${TMPDIR:-./tmp}/xonotic-run-logged.XXXXXX")
trap 'rm -f "$rc_path"' EXIT

{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'cwd=%q\n' "$PWD"
  printf 'command='
  printf '%q ' "$@"
  printf '\n'
  set +e
  "$@"
  rc=$?
  set -e
  printf 'exit_code=%d\n' "$rc"
  printf 'finished_utc=%s\n' "$(date -u +%FT%TZ)"
  printf '%d\n' "$rc" > "$rc_path"
} > >(tee "$log_path") 2>&1
rc=$(<"$rc_path")

{
  printf 'log=%s\n' "$log_path"
  printf 'exit_code=%d\n' "$rc"
} > "$status_path"

exit "$rc"
