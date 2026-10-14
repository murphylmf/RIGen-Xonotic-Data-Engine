#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/../.." && pwd -P)
qc_root="$duel_root/source_variants/duel-v11-visibility-v2/qcsrc"
qcc=${XONOTIC_DUEL_QCC:-./xonotic_workspace}
output=${XONOTIC_DUEL_VISIBILITY_QC_OUTPUT:-$duel_root/build/duel-v11-visibility-v2-qc}
watermark=xonotic-v0.8.6-duel-v11-visibility-v2

[[ -x "$qcc" ]] || { printf 'missing executable gmqcc: %s\n' "$qcc" >&2; exit 66; }
[[ -f "$qc_root/Makefile" ]] || { printf 'missing visibility QC source: %s\n' "$qc_root" >&2; exit 66; }
mkdir -p "$output"

make -C "$qc_root" -j"${XONOTIC_DUEL_QC_JOBS:-8}" sv \
  QCC="$qcc" \
  PROGS_OUT="$output" \
  WORKDIR=.tmp-duel-v11-visibility-v2 \
  QCCFLAGS_WATERMARK="$watermark"

for artifact in progs.dat csprogs.dat; do
  [[ -s "$output/$artifact" ]] || { printf 'missing QC artifact: %s\n' "$output/$artifact" >&2; exit 70; }
  grep -Fqa "$watermark" "$output/$artifact" || {
    printf 'QC artifact has wrong watermark: %s\n' "$output/$artifact" >&2
    exit 70
  }
done

sha256sum "$output/progs.dat" "$output/csprogs.dat"
