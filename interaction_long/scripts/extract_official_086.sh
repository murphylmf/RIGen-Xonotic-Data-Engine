#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
archive="$root/assets/upstream/xonotic-0.8.6.zip"
destination="$root/assets/release-0.8.6"
entry_manifest="$root/locks/upstream/xonotic-0.8.6.zip.entries"
pk3_manifest="$root/locks/upstream/xonotic-0.8.6.pk3.sha256"

if [[ ! -f "$archive" ]]; then
  printf 'missing archive: %s\n' "$archive" >&2
  exit 66
fi

unzip -Z -1 "$archive" > "$entry_manifest"

if awk '
  /^\// { bad=1 }
  /(^|\/)\.\.(\/|$)/ { bad=1 }
  END { exit bad ? 0 : 1 }
' "$entry_manifest"; then
  printf 'unsafe archive entry detected\n' >&2
  exit 65
fi

if [[ -e "$destination" && ! -f "$destination/.extract-complete" ]]; then
  printf 'refusing incomplete/nonempty destination: %s\n' "$destination" >&2
  exit 73
fi

if [[ ! -f "$destination/.extract-complete" ]]; then
  mkdir -p "$destination"
  unzip -q "$archive" -d "$destination"
  touch "$destination/.extract-complete"
fi

release_root="$destination/Xonotic"
for required in \
  "$release_root/COPYING" \
  "$release_root/GPL-2" \
  "$release_root/GPL-3" \
  "$release_root/data/xonotic-20230620-data.pk3" \
  "$release_root/data/xonotic-20230620-maps.pk3"; do
  if [[ ! -f "$required" ]]; then
    printf 'missing required release file: %s\n' "$required" >&2
    exit 66
  fi
done

mkdir -p "$root/licenses/upstream-0.8.6"
cp -f "$release_root/COPYING" "$release_root/GPL-2" "$release_root/GPL-3" \
  "$root/licenses/upstream-0.8.6/"
(
  cd "$release_root"
  find source -maxdepth 3 -type f \
    \( -iname 'COPYING*' -o -iname 'LICENSE*' -o -iname 'GPL*' \) \
    -exec cp -f --parents -t "$root/licenses/upstream-0.8.6" {} +
)

find "$release_root/data" -maxdepth 1 -type f -name '*.pk3' -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$pk3_manifest"

printf 'release_root=%s\n' "$release_root"
printf 'archive_entries=%s\n' "$(wc -l < "$entry_manifest")"
printf 'pk3_count=%s\n' "$(wc -l < "$pk3_manifest")"
du -sh "$release_root"
printf 'official_extract_complete_utc=%s\n' "$(date -u +%FT%TZ)"
