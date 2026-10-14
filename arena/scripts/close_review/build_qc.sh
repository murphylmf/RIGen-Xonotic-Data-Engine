#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/../.." && pwd -P)
qc_root="$duel_root/source_variants/duel-v12-close-review/qcsrc"
qcc=${XONOTIC_DUEL_QCC:-./xonotic_workspace}
output=${XONOTIC_DUEL_CLOSE_QC_OUTPUT:-$duel_root/build/duel-v12-close-review-qc}
watermark=xonotic-v0.8.6-duel-v12-close-review

[[ -x "$qcc" ]] || { printf 'missing executable gmqcc: %s\n' "$qcc" >&2; exit 66; }
[[ -f "$qc_root/Makefile" ]] || { printf 'missing QC source tree: %s\n' "$qc_root" >&2; exit 66; }
mkdir -p "$output"

make -C "$qc_root" -j"${XONOTIC_DUEL_QC_JOBS:-8}" sv \
  QCC="$qcc" \
  PROGS_OUT="$output" \
  WORKDIR=.tmp-duel-v12-close-review \
  QCCFLAGS_WATERMARK="$watermark"

for artifact in progs.dat csprogs.dat; do
  [[ -s "$output/$artifact" ]] || { printf 'missing QC artifact: %s\n' "$output/$artifact" >&2; exit 70; }
  grep -Fqa "$watermark" "$output/$artifact" || {
    printf 'QC artifact has wrong watermark: %s\n' "$output/$artifact" >&2
    exit 70
  }
done

sha256sum "$output/progs.dat" "$output/csprogs.dat"
