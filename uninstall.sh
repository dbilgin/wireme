#!/usr/bin/env bash
set -euo pipefail

BIN_DIR="${WIREME_BIN_DIR:-/usr/local/bin}"
LIB_DIR="${WIREME_LIB_DIR:-/usr/local/lib/wireme}"

say() { printf '%s\n' "$*"; }

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    say "wireme uninstall: sudo not found (need root to remove ${BIN_DIR}/wireme and ${LIB_DIR})"
    exit 1
  fi
fi

say "Uninstalling:"
say "  - ${BIN_DIR}/wireme"
say "  - ${LIB_DIR}"

$SUDO rm -f "${BIN_DIR}/wireme"
$SUDO rm -rf "${LIB_DIR}"

say ""
say "Uninstalled."
