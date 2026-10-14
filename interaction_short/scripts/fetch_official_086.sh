#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
release_url=https://dl.xonotic.org/xonotic-0.8.6.zip
source_url=https://dl.xonotic.org/xonotic-0.8.6-source.zip
sha_url=https://dl.xonotic.org/xonotic-0.8.6.sha512
release_sha512=cb39879e96f19abb2877588c2d50c5d3e64dd68153bec3dd1bebedf4d765e506afa419c28381d7005aed664cb1a042571c132b5b319e4308cab67745d996c2a6
source_sha512=88aa9cf35aa8e4b067dcc313037414fbc3a3769d60e88097ae8a3fbd2343369e2e4eff454b19d8a59b9c0bcbe183ec6eb289f35fa9f36564a300a3664c0e9498

mkdir -p "$root/assets/upstream" "$root/source/upstream" "$root/locks/upstream"

fetch_one() {
  local url=$1
  local output=$2
  local expected=$3
  local partial="${output}.part"

  if [[ -f "$output" ]]; then
    printf '%s  %s\n' "$expected" "$output" | sha512sum --check -
    return
  fi

  curl --fail --location --retry 8 --retry-all-errors --continue-at - \
    --output "$partial" "$url"
  printf '%s  %s\n' "$expected" "$partial" | sha512sum --check -
  mv "$partial" "$output"
}

curl --fail --location --retry 8 --retry-all-errors \
  --output "$root/locks/upstream/xonotic-0.8.6.sha512" "$sha_url"

rg "^${release_sha512}[[:space:]]+xonotic-0\\.8\\.6\\.zip$" "$root/locks/upstream/xonotic-0.8.6.sha512"
rg "^${source_sha512}[[:space:]]+xonotic-0\\.8\\.6-source\\.zip$" "$root/locks/upstream/xonotic-0.8.6.sha512"

fetch_one "$source_url" "$root/source/upstream/xonotic-0.8.6-source.zip" "$source_sha512"
fetch_one "$release_url" "$root/assets/upstream/xonotic-0.8.6.zip" "$release_sha512"

sha512sum \
  "$root/source/upstream/xonotic-0.8.6-source.zip" \
  "$root/assets/upstream/xonotic-0.8.6.zip"
sha256sum \
  "$root/source/upstream/xonotic-0.8.6-source.zip" \
  "$root/assets/upstream/xonotic-0.8.6.zip" \
  "$root/locks/upstream/xonotic-0.8.6.sha512"

printf 'official_fetch_complete_utc=%s\n' "$(date -u +%FT%TZ)"
