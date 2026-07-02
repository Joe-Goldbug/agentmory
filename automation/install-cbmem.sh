#!/usr/bin/env bash
# Idempotent installer for the codebase-memory-mcp (cbmem) binary.
#
# - Downloads v0.8.1 tarball into ~/bin/ if not already present.
# - Ensures ~/bin/cbmem symlinks to ~/bin/codebase-memory-mcp.
# - Ad-hoc signs the binary with the local keychain so macOS Gatekeeper
#   does not SIGKILL it on first run.
# - Works on macOS arm64 / x86_64. Linux/Windows users must adjust URL/arch.
#
# Usage:  bash automation/install-cbmem.sh
# Verify: lwm cbmem doctor

set -euo pipefail

VERSION="0.8.1"
ARCH="$(uname -m)"
case "${ARCH}" in
  arm64|aarch64) PLATFORM="darwin-arm64" ;;
  x86_64)        PLATFORM="darwin-amd64" ;;
  *)             echo "Unsupported arch: ${ARCH}" >&2; exit 2 ;;
esac

URL="https://github.com/DeusData/codebase-memory-mcp/releases/download/v${VERSION}/codebase-memory-mcp-${PLATFORM}.tar.gz"
BIN_DIR="${HOME}/bin"
BIN="${BIN_DIR}/codebase-memory-mcp"
LINK="${BIN_DIR}/cbmem"

mkdir -p "${BIN_DIR}"

if [[ ! -f "${BIN}" ]]; then
  echo "Downloading ${URL}"
  curl -sSL -o /tmp/cbmem.tar.gz "${URL}"
  tar -xzf /tmp/cbmem.tar.gz -C "${BIN_DIR}/"
  rm /tmp/cbmem.tar.gz
  chmod +x "${BIN}"
  echo "Installed ${BIN}"
else
  echo "${BIN} already present; skipping download"
fi

if [[ ! -L "${LINK}" ]] || [[ "$(readlink "${LINK}")" != "${BIN}" ]]; then
  ln -sf "${BIN}" "${LINK}"
  echo "Linked ${LINK} -> ${BIN}"
fi

if command -v codesign >/dev/null 2>&1; then
  codesign --force --sign - "${BIN}" >/dev/null 2>&1 || true
  echo "Ad-hoc signed ${BIN}"
fi

echo "OK. Verify with: lwm cbmem doctor"
