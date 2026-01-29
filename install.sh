#!/usr/bin/env bash
set -euo pipefail

REPO="${WIREME_REPO:-dbilgin/wireme}"
BRANCH="${WIREME_BRANCH:-master}"
BIN_DIR="${WIREME_BIN_DIR:-/usr/local/bin}"
LIB_DIR="${WIREME_LIB_DIR:-/usr/local/lib/wireme}"

say() { printf '%s\n' "$*"; }
die() { say "wireme install: $*"; exit 1; }

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || die "sudo not found (need root to write to ${BIN_DIR} and ${LIB_DIR})"
  SUDO="sudo"
fi

command -v tar >/dev/null 2>&1 || die "tar not found"

DOWNLOADER=""
if command -v curl >/dev/null 2>&1; then
  DOWNLOADER="curl"
elif command -v wget >/dev/null 2>&1; then
  DOWNLOADER="wget"
else
  die "need curl or wget"
fi

tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

archive="${tmp}/wireme.tar.gz"
url="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz"

say "Downloading ${REPO}@${BRANCH} ..."
if [[ "$DOWNLOADER" == "curl" ]]; then
  curl -fsSL "$url" -o "$archive" || die "download failed: ${url}"
else
  wget -qO "$archive" "$url" || die "download failed: ${url}"
fi

say "Extracting ..."
tar -xzf "$archive" -C "$tmp"

repo_name="${REPO##*/}"
topdir="$(tar -tzf "$archive" | awk -F/ 'NR==1{print $1}')"
src_root="${tmp}/${topdir}"

[[ -d "$src_root/wireme" ]] || die "archive missing wireme/ package"
[[ -f "$src_root/scripts/wireme" ]] || die "archive missing scripts/wireme launcher"

say "Installing to:"
say "  - ${BIN_DIR}/wireme"
say "  - ${LIB_DIR}/wireme/"

$SUDO install -d "$BIN_DIR"
$SUDO install -d "$LIB_DIR"

# Replace installed package/launcher.
$SUDO rm -rf "${LIB_DIR}/wireme"
$SUDO install -m 0755 "$src_root/scripts/wireme" "${BIN_DIR}/wireme"
$SUDO cp -R "$src_root/wireme" "$LIB_DIR/"

say ""
say "Installed. Run: wireme"
