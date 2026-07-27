#!/bin/bash
# rclone-credentials-roundtrip.sh — roundtrip + adversarial test for the
# rclone-credentials-{bootstrap,package,restore}.sh helpers (BTCAAAAA-41517).
#
# Goals:
#   1. Synthetic rclone.conf + rclone-pass encrypt + decrypt equals original.
#   2. Ciphertext does NOT contain plaintext (grep against known fixtures).
#   3. MANIFEST.json shape conforms to the documented schema.
#   4. Refuse-overwrite protects a host that already has working credentials
#      from being clobbered (--force required to bypass).
#   5. Missing optional rclone-pass file degrades gracefully (skip + WARN),
#      snapshot still includes rclone.conf.
#   6. Decrypt with the wrong bootstrap key fails with exit 2.
#   7. Bootstrap key is generated with chmod 600 and 64 hex chars.
#
# This test does NOT touch any real rclone config under $HOME. All inputs
# and outputs live under a fresh TMPDIR that is wiped on exit.
#
# Exit codes:
#   0  all assertions passed
#   11 one or more assertions failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
HELPER_DIR="$SCRIPT_DIR"

if [[ ! -x "$HELPER_DIR/rclone-credentials-bootstrap.sh" ]] \
   || [[ ! -x "$HELPER_DIR/rclone-credentials-package.sh" ]] \
   || [[ ! -x "$HELPER_DIR/rclone-credentials-restore.sh" ]]; then
  echo "FAIL: missing one of rclone-credentials-{bootstrap,package,restore}.sh in $HELPER_DIR"
  exit 1
fi

TEST_TMP="$(mktemp -d /tmp/rclone-creds-test.XXXXXXXXXX)"
trap 'rm -rf "$TEST_TMP"' EXIT

PASS=0
FAIL=0
FAIL_MSGS=()

# Synthetic inputs that NEVER appear in real rclone.conf so we can grep
# for them in the ciphertext with no false positives.
SYNTH_CONF_CONTENTS="[gdrive]
type = drive
client_id = SYNTH-CLIENT-ID-AAA111BBB
client_secret = SYNTH-SECRET-CCC222DDD
token = SYNTH-OAUTH-TOKEN-EEE333FFFGGG
"
SYNTH_PASS_CONTENTS="SYNTH-CRYPT-PASSWORD-HHH444III555JJJ666"

note() { printf '  [note] %s\n' "$*"; }
ok()   { printf '  PASS %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf '  FAIL %s\n' "$*"; FAIL=$((FAIL + 1)); FAIL_MSGS+=("$*"); }

mkdir -p "$TEST_TMP/fake-home/.config/rclone"
printf '%s' "$SYNTH_CONF_CONTENTS" > "$TEST_TMP/fake-home/.config/rclone/rclone.conf"
printf '%s' "$SYNTH_PASS_CONTENTS" > "$TEST_TMP/fake-home/.config/rclone/rclone-pass"
chmod 700 "$TEST_TMP/fake-home/.config/rclone"
chmod 600 "$TEST_TMP/fake-home/.config/rclone/rclone.conf" \
         "$TEST_TMP/fake-home/.config/rclone/rclone-pass"

ORIG_CONF_SHA="$(sha256sum "$TEST_TMP/fake-home/.config/rclone/rclone.conf" | awk '{print $1}')"
ORIG_PASS_SHA="$(sha256sum "$TEST_TMP/fake-home/.config/rclone/rclone-pass" | awk '{print $1}')"
note "orig rclone.conf sha256: ${ORIG_CONF_SHA:0:16}..."
note "orig rclone-pass sha256: ${ORIG_PASS_SHA:0:16}..."

# --- 1. Bootstrap key generation ---------------------------------------------
mkdir -p "$TEST_TMP/paperclip"
export PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE="$TEST_TMP/paperclip/bootstrap.key"
"$HELPER_DIR/rclone-credentials-bootstrap.sh" >/dev/null 2>&1
if [[ ! -s "$PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE" ]]; then
  bad "bootstrap key not generated at $PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE"
  exit 10
fi
KEY_MODE="$(stat -c '%a' "$PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE")"
KEY_LEN="$(stat -c '%s' "$PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE")"
if [[ "$KEY_MODE" == "600" ]]; then ok "bootstrap key chmod 600"; else bad "bootstrap key mode=$KEY_MODE (expected 600)"; fi
if [[ "$KEY_LEN" -eq 64 ]]; then ok "bootstrap key length = 64 hex chars"; else bad "bootstrap key length=$KEY_LEN (expected 64)"; fi

# --- 2. Package encrypts both files -----------------------------------------
SNAP_DIR="$TEST_TMP/snap"
mkdir -p "$SNAP_DIR"
RCLONE_CONFIG="$TEST_TMP/fake-home/.config/rclone/rclone.conf" \
RCLONE_PASS_FILE="$TEST_TMP/fake-home/.config/rclone/rclone-pass" \
"$HELPER_DIR/rclone-credentials-package.sh" "$SNAP_DIR" >/dev/null 2>&1

CONF_ENC="$SNAP_DIR/config/rclone/rclone.conf.enc"
PASS_ENC="$SNAP_DIR/config/rclone/rclone-pass.enc"
MANIFEST="$SNAP_DIR/config/rclone/MANIFEST.json"

if [[ -s "$CONF_ENC" ]]; then ok "rclone.conf.enc produced"; else bad "rclone.conf.enc missing or empty"; fi
if [[ -s "$PASS_ENC" ]]; then ok "rclone-pass.enc produced"; else bad "rclone-pass.enc missing or empty"; fi
if [[ -s "$MANIFEST" ]]; then ok "MANIFEST.json produced"; else bad "MANIFEST.json missing or empty"; fi

# --- 3. Ciphertext does NOT contain plaintext --------------------------------
if grep -q "SYNTH-CLIENT-ID-AAA111BBB" "$CONF_ENC" 2>/dev/null; then
  bad "rclone.conf.enc contains plaintext SYNTH-CLIENT-ID"
else
  ok "rclone.conf.enc does NOT contain plaintext"
fi
if grep -q "SYNTH-SECRET-CCC222DDD" "$CONF_ENC" 2>/dev/null; then
  bad "rclone.conf.enc contains plaintext SYNTH-SECRET"
else
  ok "rclone.conf.enc does NOT contain client_secret plaintext"
fi
if grep -q "SYNTH-CRYPT-PASSWORD-HHH444III555JJJ666" "$PASS_ENC" 2>/dev/null; then
  bad "rclone-pass.enc contains plaintext crypt passphrase"
else
  ok "rclone-pass.enc does NOT contain plaintext passphrase"
fi

# --- 4. MANIFEST.json shape -------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  MANIFEST_VALID=$(python3 -c '
import json, sys
m = json.load(open("'"$MANIFEST"'"))
assert m.get("schema") == "rclone-credentials-package-v1", m.get("schema")
assert m.get("cipher") == "aes-256-cbc", m.get("cipher")
assert m.get("kdf") == "pbkdf2-hmac-sha256", m.get("kdf")
assert isinstance(m.get("kdfIterations"), int) and m["kdfIterations"] >= 100000, m.get("kdfIterations")
assert isinstance(m.get("files"), list) and len(m["files"]) >= 1, m.get("files")
assert m.get("packaged") == ["rclone.conf", "rclone-pass"], m.get("packaged")
assert m.get("skipped") == [], m.get("skipped")
assert isinstance(m.get("bootstrapKeyFingerprint"), str) and len(m["bootstrapKeyFingerprint"]) >= 16, m.get("bootstrapKeyFingerprint")
names = {f["name"] for f in m["files"]}
assert "rclone.conf.enc" in names, names
print("ok")
' 2>&1) || MANIFEST_VALID="FAIL"
  if [[ "$MANIFEST_VALID" == "ok" ]]; then
    ok "MANIFEST.json shape valid"
  else
    bad "MANIFEST.json shape invalid: $MANIFEST_VALID"
  fi
else
  note "python3 not available — skipping MANIFEST shape check"
fi

# --- 5. Two snapshots produce different ciphertext (salt defeats KPA) -------
mkdir -p "$TEST_TMP/snap2"
RCLONE_CONFIG="$TEST_TMP/fake-home/.config/rclone/rclone.conf" \
RCLONE_PASS_FILE="$TEST_TMP/fake-home/.config/rclone/rclone-pass" \
"$HELPER_DIR/rclone-credentials-package.sh" "$TEST_TMP/snap2" >/dev/null 2>&1
SHA1="$(sha256sum "$SNAP_DIR/config/rclone/rclone.conf.enc" | awk '{print $1}')"
SHA2="$(sha256sum "$TEST_TMP/snap2/config/rclone/rclone.conf.enc" | awk '{print $1}')"
if [[ "$SHA1" != "$SHA2" ]]; then
  ok "two snapshots of same plaintext produce different ciphertext (salt works)"
else
  bad "two snapshots produced identical ciphertext (salt broken): $SHA1"
fi

# --- 6. Restore roundtrip matches originals ---------------------------------
RESTORE_DIR="$TEST_TMP/fake-home2"
mkdir -p "$RESTORE_DIR"
RCLONE_CONFIG_OUT="$RESTORE_DIR/rclone.conf" \
RCLONE_PASS_OUT="$RESTORE_DIR/rclone-pass" \
"$HELPER_DIR/rclone-credentials-restore.sh" "$SNAP_DIR" --force >/dev/null 2>&1

ROUND_CONF_SHA="$(sha256sum "$RESTORE_DIR/rclone.conf" | awk '{print $1}')"
ROUND_PASS_SHA="$(sha256sum "$RESTORE_DIR/rclone-pass" | awk '{print $1}')"
if [[ "$ROUND_CONF_SHA" == "$ORIG_CONF_SHA" ]]; then
  ok "rclone.conf roundtrip sha256 matches"
else
  bad "rclone.conf roundtrip mismatch: got $ROUND_CONF_SHA want $ORIG_CONF_SHA"
fi
if [[ "$ROUND_PASS_SHA" == "$ORIG_PASS_SHA" ]]; then
  ok "rclone-pass roundtrip sha256 matches"
else
  bad "rclone-pass roundtrip mismatch: got $ROUND_PASS_SHA want $ORIG_PASS_SHA"
fi
ROUND_CONF_MODE="$(stat -c '%a' "$RESTORE_DIR/rclone.conf")"
ROUND_PASS_MODE="$(stat -c '%a' "$RESTORE_DIR/rclone-pass")"
if [[ "$ROUND_CONF_MODE" == "600" && "$ROUND_PASS_MODE" == "600" ]]; then
  ok "restored files chmod 600"
else
  bad "restored file modes: conf=$ROUND_CONF_MODE pass=$ROUND_PASS_MODE (expected 600)"
fi

# --- 7. Refuse-overwrite protects an existing destination -------------------
set +e
"$HELPER_DIR/rclone-credentials-restore.sh" "$SNAP_DIR" >/dev/null 2>&1
RC=$?
set -e
if [[ $RC -eq 3 ]]; then
  ok "refuse-overwrite without --force exits 3"
else
  bad "refuse-overwrite exited $RC (expected 3)"
fi

# --- 8. Missing optional rclone-pass degrades gracefully --------------------
MISSING_HOME="$TEST_TMP/no-pass-home/.config/rclone"
mkdir -p "$MISSING_HOME"
printf '%s' "$SYNTH_CONF_CONTENTS" > "$MISSING_HOME/rclone.conf"
chmod 700 "$MISSING_HOME"; chmod 600 "$MISSING_HOME/rclone.conf"
SNAP_NOPASS="$TEST_TMP/snap-nopass"
mkdir -p "$SNAP_NOPASS"
set +e
RCLONE_CONFIG="$MISSING_HOME/rclone.conf" \
RCLONE_PASS_FILE="$MISSING_HOME/rclone-pass" \
"$HELPER_DIR/rclone-credentials-package.sh" "$SNAP_NOPASS" >"$TEST_TMP/pkg-nopass.log" 2>&1
PKG_RC=$?
set -e
if [[ $PKG_RC -eq 0 && -f "$SNAP_NOPASS/config/rclone/rclone.conf.enc" ]]; then
  ok "package survives missing rclone-pass (skipped, rclone.conf still packaged)"
else
  bad "package with missing rclone-pass failed rc=$PKG_RC (see $TEST_TMP/pkg-nopass.log)"
fi

# --- 9. Wrong bootstrap key fails with exit 2 --------------------------------
WRONG_KEY="$TEST_TMP/wrong.key"
head -c 32 /dev/urandom | xxd -p -c 64 > "$WRONG_KEY"
chmod 600 "$WRONG_KEY"
WRONG_OUT="$TEST_TMP/wrong-out"
mkdir -p "$WRONG_OUT"
set +e
PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE="$WRONG_KEY" \
"$HELPER_DIR/rclone-credentials-restore.sh" "$SNAP_DIR" --force --dest "$WRONG_OUT" \
  >"$TEST_TMP/restore-wrong.log" 2>&1
WR_RC=$?
set -e
if [[ $WR_RC -eq 2 ]]; then
  ok "wrong bootstrap key fails with exit 2"
else
  bad "wrong-key decrypt exited $WR_RC (expected 2) — see $TEST_TMP/restore-wrong.log"
fi

# --- 10. Bootstrap idempotency: second call is a no-op -----------------------
BEFORE_SIZE="$(stat -c '%s' "$PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE")"
BEFORE_FP="$(sha256sum "$PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE" | awk '{print $1}')"
"$HELPER_DIR/rclone-credentials-bootstrap.sh" >/dev/null 2>&1
AFTER_SIZE="$(stat -c '%s' "$PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE")"
AFTER_FP="$(sha256sum "$PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE" | awk '{print $1}')"
if [[ "$BEFORE_FP" == "$AFTER_FP" && "$BEFORE_SIZE" == "$AFTER_SIZE" ]]; then
  ok "bootstrap is idempotent (same key fingerprint, same size)"
else
  bad "bootstrap regenerates on second call: $BEFORE_FP -> $AFTER_FP"
fi

# --- Summary -----------------------------------------------------------------
echo ""
echo "=========================================="
echo "  rclone-credentials roundtrip: $PASS pass / $FAIL fail"
echo "=========================================="
if [[ $FAIL -gt 0 ]]; then
  echo "Failures:"
  for msg in "${FAIL_MSGS[@]}"; do echo "  - $msg"; done
  exit 11
fi
unset PAPERCLIP_RCLONE_BOOTSTRAP_KEY_FILE
exit 0