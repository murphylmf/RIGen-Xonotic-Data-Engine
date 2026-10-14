#!/usr/bin/env bash
set -euo pipefail

root=${XONOTIC_CAPTURE_ROOT:-./xonotic_workspace}
archive="$root/source/upstream/xonotic-0.8.6-source.zip"
destination="$root/source/release-src-0.8.6"
worktree="$destination/Xonotic"
entries="$root/locks/upstream/xonotic-0.8.6-source.zip.entries"

unzip -Z -1 "$archive" > "$entries"
if awk '
  /^\// { bad=1 }
  /(^|\/)\.\.(\/|$)/ { bad=1 }
  END { exit bad ? 0 : 1 }
' "$entries"; then
  printf 'unsafe source archive entry detected\n' >&2
  exit 65
fi

if [[ ! -f "$destination/.extract-complete" ]]; then
  if [[ -e "$destination" ]]; then
    printf 'refusing incomplete/nonempty destination: %s\n' "$destination" >&2
    exit 73
  fi
  mkdir -p "$destination"
  unzip -q "$archive" -d "$destination"
  touch "$destination/.extract-complete"
fi

if [[ ! -d "$worktree/.git" ]]; then
  git -C "$worktree" init -b upstream/xonotic-v0.8.6-archive
  git -C "$worktree" config user.name "Xonotic Capture Local"
  git -C "$worktree" config user.email "rigen-local"
  git -C "$worktree" add --all
  git -C "$worktree" commit -m \
    "Import official xonotic-0.8.6-source.zip"
  git -C "$worktree" tag archive/xonotic-0.8.6
  git -C "$worktree" switch -c capture/pilot-v0.8.6
fi

branch=$(git -C "$worktree" branch --show-current)
if [[ "$branch" != "capture/pilot-v0.8.6" ]]; then
  printf 'unexpected worktree branch: %s\n' "$branch" >&2
  exit 65
fi

printf 'worktree=%s\n' "$worktree"
git -C "$worktree" status --short --branch
git -C "$worktree" log -1 --format=fuller
sha256sum "$entries"

