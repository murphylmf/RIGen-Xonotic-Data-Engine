#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
source_root=$(cd -- "$script_dir/.." && pwd -P)
view_root=${1:-"$(dirname -- "$source_root")/xonotic_capture_stage1_r5_runtime"}
view_parent=$(dirname -- "$view_root")
view_name=$(basename -- "$view_root")

[[ "$view_root" == /* ]] || {
  echo "Stage-1 runtime view must be an absolute path: $view_root" >&2
  exit 64
}
[[ "$view_root" != "$source_root" &&
   "$view_root" != "$source_root/"* ]] || {
  echo "Stage-1 runtime view must be outside the canonical tree" >&2
  exit 64
}
[[ ! -e "$view_root" ]] || {
  echo "refusing to overwrite existing runtime view: $view_root" >&2
  exit 73
}
[[ "$(readlink -f ./xonotic_capture)" == "$source_root" ]] || {
  echo "mount the transferred tree at ./xonotic_capture before materializing Stage-1" >&2
  exit 66
}
command -v patch >/dev/null || {
  echo "GNU patch is required" >&2
  exit 69
}

base_checks=(
  "2b397b021b5100f7a81dadb5e0f7eb83c3fa99e9eda99edd1b3cf9e46baf60d7  $source_root/XONOTIC_DATA_SPEC_V2.md"
  "a11f428114a1b7a8810123ab598eb39ab2791dbd234336f0af64764763d160da  $source_root/scripts/xonotic_capture.py"
)
printf '%s\n' "${base_checks[@]}" | sha256sum -c - >/dev/null

overlay="$source_root/migration/stage1_runtime_r5_overlay.patch"
runtime_lock="$source_root/manifests/stage1_foundation_v5_formal_56x1_runtime_r5/RUNTIME_CODE_LOCK.sha256"
[[ -r "$overlay" && -r "$runtime_lock" ]] || {
  echo "Stage-1 overlay or runtime lock is missing" >&2
  exit 66
}

mkdir -p "$view_parent"
stage_root=$(mktemp -d "$view_parent/.${view_name}.staging.XXXXXX")

shopt -s nullglob
for entry in "$source_root"/*; do
  name=$(basename -- "$entry")
  case "$name" in
    XONOTIC_DATA_SPEC_V2.md|scripts) continue ;;
  esac
  ln -s "$entry" "$stage_root/$name"
done

mkdir "$stage_root/scripts"
for entry in "$source_root/scripts"/*; do
  name=$(basename -- "$entry")
  if [[ "$name" == xonotic_capture.py ]]; then
    cp -p "$entry" "$stage_root/scripts/$name"
  else
    ln -s "$entry" "$stage_root/scripts/$name"
  fi
done
cp -p "$source_root/XONOTIC_DATA_SPEC_V2.md" \
  "$stage_root/XONOTIC_DATA_SPEC_V2.md"

patch --batch --forward -p1 -d "$stage_root" < "$overlay"

(
  cd "$stage_root"
  sha256sum -c "$runtime_lock"
)
sha256sum -c - >/dev/null <<EOF
8d56ba269e78214fcbabebf4100c228c4871136387a916fdeeb48732789e98e9  $stage_root/XONOTIC_DATA_SPEC_V2.md
f78e997510f4cf4f2f3ebbd5d8499c24579862a88c3bdc20bf3070cf5f3345c8  $stage_root/scripts/xonotic_capture.py
EOF

mv "$stage_root" "$view_root"
printf 'stage1_runtime_view=%s\n' "$view_root"
printf 'stage1_runtime_lock=pass\n'
printf 'canonical_data_root=%s\n' "$source_root"
