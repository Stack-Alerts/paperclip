#!/bin/bash
# rclone-credentials-restore.sh — Decrypt rclone.conf.enc + rclone-pass.enc
# from a snapshot's config/rclone/ subtree back into the live credential
# locations on a fresh host.
#
# Usage:
#   ./scripts/rclone-credentials-restore.sh <snap_dir> [--dry-run]
#   ./scripts/rclone-credentials-restore.sh <snap_dir> --dest /custom/path
#
# Source:
#   <snap_dir>/config/rclone/{rclone.conf.enc,rclone-pass.enc,MANIFEST.json}
#
# Destination (defaults match recovery.sh constants):
#   RCLONE_CONFIG_OUT default: $HOME/.config/rclone/rclone.conf
#   RCLONE_PASS_OUT   default: $HOME/.config/rclone/rclone-pass
#
# Required on the restore host:
#   - bootstrap key file at $PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE
#     (default ~/.paperclip/rclone-creds-bootstrap.key)
#     If absent, run: scripts/rclone-credentials-bootstrap.sh --reset
#     and re-bootstrap from your offline backup.
#
# Safety:
#   - If destination files already exist, this script refuses to overwrite
#     unless --force is passed. Refusing protects a host that already has
#     working credentials from being clobbered by a stale snapshot.
#   - Decrypted plaintext is written chmod 600 to match the live layout.
#   - Never logs plaintext contents; only sizes and sha256 fingerprints.
#
# Exit codes:
#   0  success — credentials decrypted and installed
#   1  bad args / missing bootstrap key / missing ciphertext
#   2  decrypt failed (wrong key, corrupted ciphertext)
#   3  destination collision (without --force)

set -euo pipefail

: "${HOME:=$(eval echo "~$(id -un 2>/dev/null || echo root)")}"

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

log()  { printf '[rclone-creds-restore] %s\n' "$*"; }
die()  { log "ERROR: $*" >&2; exit "${2:-1}"; }

dry_run=0
force=0
custom_dest=""
SNAP_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run=1 ;;
    --force)   force=1 ;;
    --dest)    custom_dest="${2:-}"; [[ -n "$custom_dest" ]] || die "--dest requires a directory" 1; shift ;;
    -h|--help)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    -*) die "unknown option: $1" 1 ;;
    *)
      if [[ -n "$SNAP_DIR" ]]; then
        die "unexpected argument: $1" 1
      fi
      SNAP_DIR="$1"
      ;;
  esac
  shift
done

if [[ -z "$SNAP_DIR" ]]; then
  die "usage: $0 <snap_dir> [--dry-run] [--force] [--dest <dir>]" 1
fi
SRC_DIR="$SNAP_DIR/config/rclone"

RCLONE_CONFIG_OUT="${RCLONE_CONFIG_OUT:-$HOME/.config/rclone/rclone.conf}"
RCLONE_PASS_OUT="${RCLONE_PASS_OUT:-$HOME/.config/rclone/rclone-pass}"

if [[ -n "$custom_dest" ]]; then
  RCLONE_CONFIG_OUT="$custom_dest/rclone.conf"
  RCLONE_PASS_OUT="$custom_dest/rclone-pass"
fi

KEY_FILE="${PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE:-$HOME/.paperclip/rclone-creds-bootstrap.key}"

command -v openssl >/dev/null 2>&1 || die "missing dependency: openssl" 1

if [[ ! -s "$KEY_FILE" ]]; then
  die "bootstrap key missing at $KEY_FILE — install from offline backup or re-bootstrap (scripts/rclone-credentials-bootstrap.sh --reset)" 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  die "snapshot has no config/rclone/ at $SRC_DIR — not a credentials-bearing snapshot, or wrong path" 1
fi

if [[ -f "$SRC_DIR/MANIFEST.json" ]]; then
  log "manifest:"
  sed 's/^/  /' "$SRC_DIR/MANIFEST.json" | head -20 || true
fi

decrypt_one() {
  local label="$1" src="$2" dst="$3"
  local size_ct sha_ct

  if [[ ! -f "$src" ]]; then
    log "  SKIP $label: no ciphertext at $src"
    return 0
  fi

  size_ct="$(stat -c '%s' "$src" 2>/dev/null || echo 0)"
  sha_ct="$(sha256sum "$src" | awk '{print $1}')"
  log "  decrypting $label: ${size_ct}B ciphertext (sha256=${sha_ct:0:16}...)"

  if [[ -f "$dst" && $force -eq 0 ]]; then
    die "destination $dst already exists — refusing to overwrite without --force (refusing protects a host that already has working credentials from being clobbered by a stale snapshot)" 3
  fi

  if [[ $dry_run -eq 1 ]]; then
    log "  DRY-RUN: would write $dst (mode 600)"
    return 0
  fi

  mkdir -p "$(dirname "$dst")"
  chmod 700 "$(dirname "$dst")"

  local tmp="${dst}.decrypt.$$"
  if ! openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
        -pass "file:$KEY_FILE" \
        -in "$src" \
        -out "$tmp" 2>/tmp/rclone-creds-restore.err; then
    log "  ERROR decrypting $label — openssl decrypt failed (likely wrong bootstrap key or corrupted ciphertext)"
    cat /tmp/rclone-creds-restore.err >&2 || true
    rm -f /tmp/rclone-creds-restore.err "$tmp"
    exit 2
  fi
  rm -f /tmp/rclone-creds-restore.err
  chmod 600 "$tmp"
  mv -f "$tmp" "$dst"

  local size_pt sha_pt
  size_pt="$(stat -c '%s' "$dst" 2>/dev/null || echo 0)"
  sha_pt="$(sha256sum "$dst" | awk '{print $1}')"
  log "  restored $label: ${size_pt}B plaintext (sha256=${sha_pt:0:16}...)"
}

log "restoring rclone credentials from $SRC_DIR"
decrypt_one "rclone.conf" "$SRC_DIR/rclone.conf.enc" "$RCLONE_CONFIG_OUT"
decrypt_one "rclone-pass" "$SRC_DIR/rclone-pass.enc" "$RCLONE_PASS_OUT"

if [[ $dry_run -eq 1 ]]; then
  log "DRY-RUN complete — no files were written"
else
  log "credentials restored. Verify with:"
  log "  rclone config show   (should list your remote)"
  log "  ls -la $RCLONE_CONFIG_OUT $RCLONE_PASS_OUT"
fi

unset PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE

exit 0
