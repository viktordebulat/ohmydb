#!/usr/bin/env bash
# Fails if a real module under app/ isn't named in ARCHITECTURE.md's module
# table. This is what keeps the architecture map honest — see ARCHITECTURE.md.
set -euo pipefail
cd "$(dirname "$0")/.."

ARCH=ARCHITECTURE.md
modules=()

# Subpackages: any immediate app/* dir that is itself a package.
while IFS= read -r pkg; do
  modules+=("app/$(basename "$pkg")")
done < <(find app -mindepth 1 -maxdepth 1 -type d -exec test -f '{}/__init__.py' \; -print | sort)

# Top-level modules: *.py directly under app/, excluding __init__.py.
while IFS= read -r f; do
  modules+=("app/$(basename "$f")")
done < <(find app -maxdepth 1 -type f -name '*.py' ! -name '__init__.py' | sort)

missing=()
for m in "${modules[@]}"; do
  grep -qF "$m" "$ARCH" || missing+=("$m")
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo "docs:verify FAILED: $ARCH is missing these modules:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  echo "Add a row to the module table in $ARCH, then re-run." >&2
  exit 1
fi

echo "docs:verify OK: ${#modules[@]} module(s) documented in $ARCH."
