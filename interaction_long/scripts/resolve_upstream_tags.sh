#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
tag=xonotic-v0.8.6
output="$root/locks/upstream/xonotic-v0.8.6-git-tags.tsv"
temporary="${output}.tmp"

repositories=(
  "xonotic|https://gitlab.com/xonotic/xonotic.git"
  "darkplaces|https://gitlab.com/xonotic/darkplaces.git"
  "xonotic-data.pk3dir|https://gitlab.com/xonotic/xonotic-data.pk3dir.git"
  "d0_blind_id|https://gitlab.com/xonotic/d0_blind_id.git"
  "gmqcc|https://gitlab.com/xonotic/gmqcc.git"
)

printf 'repository\turl\ttag\ttag_object_or_commit\tpeeled_commit\n' > "$temporary"

for record in "${repositories[@]}"; do
  repository=${record%%|*}
  url=${record#*|}
  refs=$(git ls-remote "$url" \
    "refs/tags/$tag" "refs/tags/$tag^{}")
  tag_hash=$(awk -v ref="refs/tags/$tag" '$2 == ref {print $1}' <<<"$refs")
  peeled_hash=$(awk -v ref="refs/tags/$tag^{}" '$2 == ref {print $1}' <<<"$refs")
  if [[ -z "$tag_hash" ]]; then
    printf 'missing tag %s in %s\n' "$tag" "$url" >&2
    exit 65
  fi
  if [[ -z "$peeled_hash" ]]; then
    peeled_hash=$tag_hash
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$repository" "$url" "$tag" "$tag_hash" "$peeled_hash" \
    >> "$temporary"
done

mv "$temporary" "$output"
cat "$output"
sha256sum "$output"

