#!/usr/bin/env bash
# Restores the icon theme you had before installing Tovu Calibre Themes (macOS).
set -euo pipefail
TOVU_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$TOVU_DIR/install-mac.command" --uninstall "$@"
