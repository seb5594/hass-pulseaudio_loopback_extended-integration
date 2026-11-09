#!/usr/bin/env bash
# Copy the files prepared for the next Home Assistant Core pull request into a
# checkout of a home-assistant/core fork.
#
# Usage: core/sync.sh <path-to-core-checkout>
#
# The files below core/ mirror the layout of home-assistant/core. BASE_COMMIT
# records the upstream commit they were written against; if upstream changed
# the integration since then, the copy is refused so nothing gets overwritten
# silently.
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:?Usage: $0 <path-to-core-checkout>}"
INTEGRATION_PATHS=(
  homeassistant/components/pulseaudio_loopback
  tests/components/pulseaudio_loopback
)

if [[ ! -f "$TARGET/homeassistant/const.py" ]]; then
  echo "error: $TARGET does not look like a home-assistant/core checkout" >&2
  exit 1
fi

base="$(<"$SOURCE/BASE_COMMIT")"
if git -C "$TARGET" cat-file -e "$base^{commit}" 2>/dev/null; then
  if ! git -C "$TARGET" diff --quiet "$base" HEAD -- "${INTEGRATION_PATHS[@]}"; then
    echo "error: upstream changed the integration since $base:" >&2
    git -C "$TARGET" log --oneline "$base"..HEAD -- "${INTEGRATION_PATHS[@]}" >&2
    echo "Port those changes into core/ and update BASE_COMMIT first." >&2
    exit 1
  fi
else
  echo "warning: $base is not in $TARGET, skipping the upstream change check" >&2
fi

for path in "${INTEGRATION_PATHS[@]}"; do
  mkdir -p "$TARGET/$path"
  cp -R "$SOURCE/$path/." "$TARGET/$path/"
done

git -C "$TARGET" status --short -- "${INTEGRATION_PATHS[@]}"
