#!/bin/bash
# rclone-credentials-bootstrap.sh — Generate or load the bootstrap key that
# protects the encrypted rclone credentials subtree inside backups.
#
# The bootstrap key is the OUT-OF-BAND secret that wraps rclone.conf and
# rclone-pass inside the backup payload. It is intentionally independent
# from those same credentials — using them to protect themselves would be
# a chicken-and-egg loop: a fresh host cannot read the credentials until
# it has authenticated to GDrive, but it cannot authenticate to GDrive
# until it has the credentials.
#
# Storage:
#   - $PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE
#     default: ~/.paperclip/rclone-creds-bootstrap.key
#     32-byte hex (64 chars), chmod 600, owner-only readable
#
# Recovery (operator):
#   - Lost host + lost key:   re-bootstrap blank key (this script --reset),
#     document the loss, plan a fresh rclone OAuth on the new host.
#   - Lost host + kept key:  copy the key onto the new host, then run
#     rclone-credentials-restore.sh against any snapshot.
#   - Lost key + kept host:  you cannot decrypt past backups. Run
#     rclone-bootstrap.sh to redo rclone OAuth, then continue with the
#     new key going forward.
#
# Usage:
#   ./scripts/rclone-credentials-bootstrap.sh                # idempotent: create-if-missing
#   ./scripts/rclone-credentials-bootstrap.sh --print        # print fingerprint + path
#   ./scripts/rclone-credentials-bootstrap.sh --reset        # delete + regenerate (DESTRUCTIVE)
#   ./scripts/rclone-credentials-bootstrap.sh --rotate       # create new key, retain old key
#   PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE=/path/to/key bootstrap
#
# Environment:
#   PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE   override key location (default ~/.paperclip/rclone-creds-bootstrap.key)

set -euo pipefail

# Defensive HOME handling: plugin workers under paperclip sometimes strip env
: "${HOME:=$(eval echo "~$(id -un 2>/dev/null || echo root)")}"

KEY_FILE="${PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE:-$HOME/.paperclip/rclone-creds-bootstrap.key}"

# Package callers source this file only to resolve the configured key path.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return 0
fi

log()  { printf '[rclone-creds-bootstrap] %s\n' "$*"; }
die()  { log "ERROR: $*" >&2; exit 1; }

print=0
reset=0
rotate=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --print) print=1 ;;
    --reset) reset=1 ;;
    --rotate) rotate=1 ;;
    -h|--help)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    *) die "unknown arg: $1" ;;
  esac
  shift
done

ensure_dir() {
  local d
  d="$(dirname "$KEY_FILE")"
  mkdir -p "$d"
  chmod 700 "$d"
}

generate_key() {
  head -c 32 /dev/urandom | xxd -p -c 64
}

fingerprint() {
  if [[ -s "$KEY_FILE" ]]; then
    sha256sum "$KEY_FILE" | awk '{print substr($1,1,16)}'
  else
    echo "missing"
  fi
}

if [[ -s "$KEY_FILE" && $reset -eq 0 && $rotate -eq 0 ]]; then
  log "key already present at $KEY_FILE (fingerprint: $(fingerprint))"
  if [[ $print -eq 1 ]]; then
    log "  path:        $KEY_FILE"
    log "  size:        $(stat -c '%s' "$KEY_FILE" 2>/dev/null) bytes"
    log "  perms:       $(stat -c '%a' "$KEY_FILE" 2>/dev/null)"
    log "  fingerprint: $(fingerprint)"
    log "  (secret value intentionally never printed)"
  fi
  exit 0
fi

if [[ $reset -eq 1 && -e "$KEY_FILE" ]]; then
  log "RESET: shredding existing key at $KEY_FILE"
  if command -v shred >/dev/null 2>&1; then
    shred -u "$KEY_FILE" 2>/dev/null || rm -f "$KEY_FILE"
  else
    head -c 4096 /dev/urandom > "$KEY_FILE" 2>/dev/null || true
    rm -f "$KEY_FILE"
  fi
fi

if [[ $rotate -eq 1 && -e "$KEY_FILE" ]]; then
  rotate_ts="$(date -u +%Y%m%dT%H%M%SZ)"
  rotate_archive="${KEY_FILE%.key}-${rotate_ts}.key"
  cp -p "$KEY_FILE" "$rotate_archive"
  chmod 600 "$rotate_archive"
  log "ROTATE: archived old key to $rotate_archive (old backups remain decryptable)"
fi

ensure_dir
NEW_KEY="$(generate_key)"
printf '%s' "$NEW_KEY" > "$KEY_FILE"
chmod 600 "$KEY_FILE"
unset NEW_KEY

log "generated new bootstrap key at $KEY_FILE (fingerprint: $(fingerprint))"
log ""
log "  *** STORE THIS OFFLINE ***"
log "  path: $KEY_FILE"
log "  fingerprint: $(fingerprint)"
log ""
log "  The key value is NOT printed to stdout. To back it up, copy the"
log "  file to an offline location (password manager, USB drive, paper"
log "  in a safe). Without it, snapshots containing encrypted rclone"
log "  credentials become unreadable."
log ""
log "  After backup, verify key perms:  stat -c '%a %n' $KEY_FILE"
log "  Expected: '600 $KEY_FILE'"
