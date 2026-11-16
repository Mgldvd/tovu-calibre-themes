#!/usr/bin/env bash
# Tovu Calibre Themes launcher for Linux. Run it from a terminal or double-click it.
set -euo pipefail
TOVU_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v calibre-debug >/dev/null 2>&1; then
    printf '%s\n' 'Calibre was not found. Install it from https://calibre-ebook.com/download and run this file again.' >&2
    exit 1
fi

# Keep a desktop shortcut next to this file that points to the folder's current
# location. Desktop files cannot use relative paths, so it is written here.
tovu_shortcut() {
    local file="$TOVU_DIR/Install Tovu Calibre Themes.desktop" exec_path icon_path content
    # Exec values: backslash-escape \ " ` $ inside quotes, then escape the backslashes again.
    exec_path="$(printf '%s' "$TOVU_DIR/install-linux.sh" | sed -e 's/\\/\\\\\\\\/g' -e 's/["`$]/\\\\&/g')"
    icon_path="$(printf '%s' "$TOVU_DIR/themes/stickers/theme/library.png" | sed -e 's/\\/\\\\/g')"
    content="[Desktop Entry]
Version=1.0
Type=Application
Name=Install Tovu Calibre Themes
Comment=Install or restore Tovu icon themes for Calibre
Exec=\"$exec_path\"
Icon=$icon_path
Terminal=false
Categories=Utility;
StartupNotify=true"
    if [[ ! -f "$file" || "$(cat -- "$file")" != "$content" ]]; then
        printf '%s\n' "$content" > "$file"
        chmod +x "$file"
        gio set "$file" metadata::trusted true >/dev/null 2>&1 || true
    fi
}
tovu_shortcut 2>/dev/null || true

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
