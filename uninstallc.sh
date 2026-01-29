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
    say "wiremec uninstall: sudo not found (need root to remove ${BIN_DIR}/wiremec and ${LIB_DIR})"
    exit 1
  fi
fi

if [[ -x "${BIN_DIR}/wireme" ]]; then
  say ""
  say "============================================================"
  say "WARNING: wireme is installed on this host."
  say "To avoid breaking wireme, this will only remove wiremec."
  say "============================================================"
  say ""
  $SUDO rm -f "${BIN_DIR}/wiremec"
  say "Removed: ${BIN_DIR}/wiremec"
  exit 0
fi

say "Uninstalling:"
say "  - ${BIN_DIR}/wiremec"
say "  - ${LIB_DIR}"

$SUDO rm -f "${BIN_DIR}/wiremec"
$SUDO rm -rf "${LIB_DIR}"

say ""
say "Uninstalled."
