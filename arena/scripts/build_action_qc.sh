#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
duel_root=$(cd -- "$script_dir/.." && pwd)
qc_root="$duel_root/source/qcsrc"
qcc=${XONOTIC_DUEL_QCC:-./xonotic_workspace}
output=${XONOTIC_DUEL_QC_OUTPUT:-$duel_root/build/duel-v11-stage2-prompt-qc}
workdir=${XONOTIC_DUEL_QC_WORKDIR:-.tmp-duel-v11-stage2-prompt}
watermark=xonotic-v0.8.6-duel-v11-stage2-prompt

[[ -x "$qcc" ]] || { printf 'missing executable gmqcc: %s\n' "$qcc" >&2; exit 66; }
[[ -f "$qc_root/Makefile" ]] || { printf 'missing QC source tree: %s\n' "$qc_root" >&2; exit 66; }
mkdir -p "$output"

make -C "$qc_root" -j"$(nproc)" sv \
  QCC="$qcc" \
  PROGS_OUT="$output" \
  WORKDIR="$workdir" \
  QCCFLAGS_WATERMARK="$watermark"

for artifact in progs.dat csprogs.dat; do
  [[ -s "$output/$artifact" ]] || { printf 'missing QC artifact: %s\n' "$output/$artifact" >&2; exit 70; }
  grep -Fqa "$watermark" "$output/$artifact" || {
    printf 'QC artifact has wrong watermark: %s\n' "$output/$artifact" >&2
    exit 70
  }
done

sha256sum "$output/progs.dat" "$output/csprogs.dat"
