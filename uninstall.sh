#!/usr/bin/env bash
set -euo pipefail
TOVU_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$TOVU_DIR/install.sh" --uninstall "$@"
