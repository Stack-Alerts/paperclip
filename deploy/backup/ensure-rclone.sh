#!/bin/bash
# ensure-rclone.sh — deterministically ensure a pinned rclone binary is on PATH.
#
# Designed for hosts without sudo where the systemd unit's PATH already
# includes ~/.local/bin (see deploy/systemd/paperclip-backup.service).
#
# Behaviour:
#   1. If `rclone` resolves on PATH and matches the pinned version, exit 0.
#   2. Otherwise, download the pinned release archive from rclone.org,
#      verify the SHA-256 against the value pinned below, extract the
#      `rclone` binary to $HOME/.local/bin/rclone (or
#      $RCLONE_INSTALL_DIR), chmod +x, and exit 0.
#   3. On any failure, print a clear diagnostic and exit non-zero so the
#      caller (bootstrap, systemd unit, GH Actions step) fails fast with
#      something better than "rclone: command not found".
#
# Bumping the pin:
#   - Update RCLONE_VERSION below.
#   - Fetch the matching SHA-256SUMS:
#       curl -sSL https://downloads.rclone.org/v<VERSION>/SHA256SUMS \
#         | grep -E 'linux-(amd64|arm64)\.zip$'
#   - Update RCLONE_SHA256_AMD64 / RCLONE_SHA256_ARM64.

set -euo pipefail

RCLONE_VERSION="${RCLONE_VERSION:-1.72.1}"
RCLONE_INSTALL_DIR="${RCLONE_INSTALL_DIR:-$HOME/.local/bin}"
RCLONE_INSTALL_BIN="${RCLONE_INSTALL_DIR}/rclone"

# Pinned SHA-256 of the upstream release archives. Update together with
# RCLONE_VERSION. Source: https://downloads.rclone.org/v${RCLONE_VERSION}/SHA256SUMS
RCLONE_SHA256_AMD64="b5c9b2fb6ada8a400c5fc5d48cd112dc1adea21a3b73b03857059374dd8a78d0"
RCLONE_SHA256_ARM64="66ce9c7fbdf6ba38991fa2ac193ed051bd6d04aeec693900c848154bf549484f"

log()  { printf '[ensure-rclone] %s\n' "$*"; }
fail() { printf '[ensure-rclone] ERROR: %s\n' "$*" >&2; exit 1; }

detect_arch() {
    local raw
    raw="$(uname -m)"
    case "$raw" in
        x86_64|amd64) echo "amd64" ;;
        aarch64|arm64) echo "arm64" ;;
        *) fail "unsupported architecture: ${raw}" ;;
    esac
}

current_version() {
    # Prints the version string (e.g. "1.72.1") of the rclone on PATH, or
    # empty if none is resolvable / parseable.
    command -v rclone >/dev/null 2>&1 || { echo ""; return; }
    rclone version 2>/dev/null | awk 'NR==1 { sub(/^v/, "", $2); print $2; exit }'
}

needs_install() {
    local have
    have="$(current_version)"
    if [ -z "$have" ]; then
        return 0
    fi
    if [ "$have" != "$RCLONE_VERSION" ]; then
        log "found rclone ${have}, want ${RCLONE_VERSION}; will reinstall."
        return 0
    fi
    return 1
}

install_pinned() {
    local arch sha url tmpdir zip
    arch="$(detect_arch)"
    case "$arch" in
        amd64) sha="$RCLONE_SHA256_AMD64" ;;
        arm64) sha="$RCLONE_SHA256_ARM64" ;;
    esac
    [ -n "$sha" ] || fail "no pinned SHA-256 for arch ${arch}"

    url="https://downloads.rclone.org/v${RCLONE_VERSION}/rclone-v${RCLONE_VERSION}-linux-${arch}.zip"
    tmpdir="$(mktemp -d -t rclone-install.XXXXXX)"
    # Use parameter expansion default so the trap is safe under `set -u`
    # after `install_pinned` returns and `tmpdir`'s local scope is gone.
    trap 'rm -rf "${tmpdir:-}"' EXIT
    zip="${tmpdir}/rclone.zip"

    log "downloading ${url}"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --retry 3 --retry-delay 2 --max-time 120 -o "$zip" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$zip" "$url"
    else
        fail "neither curl nor wget is available to fetch rclone"
    fi

    log "verifying SHA-256 (expect ${sha})"
    local actual
    actual="$(sha256sum "$zip" | awk '{print $1}')"
    if [ "$actual" != "$sha" ]; then
        fail "SHA-256 mismatch: got ${actual}, want ${sha}"
    fi

    command -v unzip >/dev/null 2>&1 || fail "unzip is required but not installed"
    unzip -q "$zip" -d "$tmpdir"

    local extracted
    extracted="$(find "$tmpdir" -type f -name rclone -perm -u+x | head -n 1)"
    [ -n "$extracted" ] || fail "rclone binary not found inside archive"

    mkdir -p "$RCLONE_INSTALL_DIR"
    install -m 0755 "$extracted" "$RCLONE_INSTALL_BIN"
    log "installed ${RCLONE_INSTALL_BIN}"
}

main() {
    if ! needs_install; then
        log "rclone $(current_version) already present at $(command -v rclone)"
        return 0
    fi

    if ! [[ ":${PATH}:" == *":${RCLONE_INSTALL_DIR}:"* ]]; then
        log "WARNING: ${RCLONE_INSTALL_DIR} is not on PATH; installing anyway."
        log "         Callers must ensure the binary is on PATH (systemd Environment=PATH=…)."
    fi

    install_pinned

    # Re-resolve to confirm.
    local have
    have="$(current_version)"
    if [ "$have" != "$RCLONE_VERSION" ]; then
        # PATH may not include the install dir for this shell. Verify the
        # absolute install path directly so callers still get a useful exit.
        if "$RCLONE_INSTALL_BIN" version >/dev/null 2>&1; then
            log "installed ${RCLONE_VERSION} at ${RCLONE_INSTALL_BIN} (not on this shell's PATH)"
            return 0
        fi
        fail "post-install verification failed (have='${have}')"
    fi
    log "rclone ${have} ready at $(command -v rclone)"
}

main "$@"
