#!/usr/bin/env bash
# Tovu Calibre Themes launcher for macOS. Double-click it, or run: bash install-mac.command
set -euo pipefail
TOVU_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

CALIBRE_DEBUG="${CALIBRE_DEBUG:-}"
if [[ -z "$CALIBRE_DEBUG" ]]; then
    for candidate in "$(command -v calibre-debug 2>/dev/null || true)" \
                     "/Applications/calibre.app/Contents/MacOS/calibre-debug" \
                     "$HOME/Applications/calibre.app/Contents/MacOS/calibre-debug"; do
        if [[ -n "$candidate" && -x "$candidate" ]]; then CALIBRE_DEBUG="$candidate"; break; fi
    done
fi
if [[ -z "$CALIBRE_DEBUG" ]]; then
    printf '%s\n' 'Calibre was not found. Install it from https://calibre-ebook.com/download and run this file again.' >&2
    exit 1
fi

# Configure the profile before calibre-debug imports Calibre's constants.
previous=''
for arg in "$@"; do
    case "$arg" in --config-dir=*) export CALIBRE_CONFIG_DIRECTORY="${arg#--config-dir=}" ;; esac
    if [[ "$previous" == --config-dir ]]; then export CALIBRE_CONFIG_DIRECTORY="$arg"; fi
    previous="$arg"
done
exec "$CALIBRE_DEBUG" -e "$TOVU_DIR/installer.py" -- "$@"
