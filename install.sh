#!/usr/bin/env bash
set -euo pipefail
TOVU_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v calibre-debug >/dev/null 2>&1; then
    printf '%s\n' 'Calibre was not found. Install it from https://calibre-ebook.com/download and run this file again.' >&2
    exit 1
fi
# Configure the profile before calibre-debug imports Calibre's constants.
TOVU_ARGS=("$@")
for (( TOVU_INDEX=0; TOVU_INDEX<${#TOVU_ARGS[@]}; TOVU_INDEX++ )); do
    if [[ "${TOVU_ARGS[TOVU_INDEX]}" == --config-dir && $((TOVU_INDEX+1)) -lt ${#TOVU_ARGS[@]} ]]; then
        export CALIBRE_CONFIG_DIRECTORY="${TOVU_ARGS[TOVU_INDEX+1]}"
    elif [[ "${TOVU_ARGS[TOVU_INDEX]}" == --config-dir=* ]]; then
        export CALIBRE_CONFIG_DIRECTORY="${TOVU_ARGS[TOVU_INDEX]#--config-dir=}"
    fi
done
exec calibre-debug -e "$TOVU_DIR/installer.py" -- "$@"
