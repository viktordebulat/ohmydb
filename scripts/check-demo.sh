#!/usr/bin/env bash
# Fails if app/web/ (the frontend source) changed more recently than
# docs/demo/ (its static GitHub Pages snapshot) — see ARCHITECTURE.md /
# `task demo:build`. Compares the latest commit touching each path, not file
# contents, since docs/demo/ also bakes in DB data that content-diffing
# can't reproduce without a live ClickHouse.
set -euo pipefail
cd "$(dirname "$0")/.."

web_commit=$(git log -1 --format=%H -- app/web)
demo_commit=$(git log -1 --format=%H -- docs/demo)

if [ -z "$web_commit" ]; then
  echo "demo:check OK: app/web has no history yet."
  exit 0
fi

if [ -z "$demo_commit" ] || ! git merge-base --is-ancestor "$web_commit" "$demo_commit"; then
  echo "docs/demo:check FAILED: app/web changed at $web_commit but docs/demo/ wasn't regenerated after that." >&2
  echo "Run 'task demo:build' and commit docs/demo/." >&2
  exit 1
fi

echo "demo:check OK: docs/demo/ is at or after the latest app/web change ($web_commit)."
