#!/usr/bin/env bash
# packages/web-ui/__tests__/predev-gate.smoke.sh
#
# BTCAAAAA-31217 — smoke test for the predev branch-gate.
#
# Builds a throwaway git repo, copies in the gate script, then exercises
# every documented exit path:
#   1. HEAD == origin/main                     -> exit 0
#   2. HEAD != origin/main, no override        -> exit 1, refusal banner
#   3. HEAD != origin/main, FORCE_NON_MAIN_DEV  -> exit 0, loud banner
#   4. HEAD != origin/main, BTE_BRANCH_GATE_OK  -> exit 0, silent
#   5. HEAD != origin/main, BTE_SKIP_BRANCH_GATE -> exit 0, loud banner
#   6. cwd not a git repo                       -> exit 0, silent
#
# Also verifies (when a real npm is available) that `npm run dev` aborts
# before next-server boots when the gate refuses — i.e. the `predev` hook
# is wired correctly in package.json.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GATE_SCRIPT="$REPO_ROOT/packages/web-ui/scripts/gate-main-branch.sh"
PKG_JSON="$REPO_ROOT/packages/web-ui/package.json"

if [[ ! -x "$GATE_SCRIPT" ]]; then
  echo "FAIL: $GATE_SCRIPT missing or not executable" >&2
  exit 1
fi

# --- Wiring assertion (package.json) ----------------------------------------
if ! grep -q '"predev"' "$PKG_JSON"; then
  echo "FAIL: packages/web-ui/package.json has no predev hook" >&2
  exit 1
fi
if ! grep -q 'gate-main-branch' "$PKG_JSON"; then
  echo "FAIL: packages/web-ui/package.json predev does not reference gate-main-branch" >&2
  exit 1
fi

WORK="$(mktemp -d -t btc-31217-gate-smoke.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

ORIGIN="$WORK/origin.git"
CLONE="$WORK/clone"

# --- Build a deterministic origin --------------------------------------------
git init --quiet --bare "$ORIGIN"
git -c init.defaultBranch=main clone --quiet "$ORIGIN" "$CLONE"
cd "$CLONE"
git config user.email "smoke@example.com"
git config user.name "Smoke"
git checkout --quiet -b main
mkdir -p packages/web-ui/scripts
cp "$GATE_SCRIPT" packages/web-ui/scripts/gate-main-branch.sh
chmod +x packages/web-ui/scripts/gate-main-branch.sh
echo "v1" > marker.txt
git add -A
git commit --quiet -m "initial"
echo "v2" > marker.txt
git add -A
git commit --quiet -m "second"
MAIN_SHA="$(git rev-parse HEAD)"
git push --quiet origin main
git checkout --quiet -b stale HEAD~1
STALE_SHA="$(git rev-parse HEAD)"

RUN_GATE() {
  cd "$CLONE/packages/web-ui"
  bash scripts/gate-main-branch.sh
}

pass=0
fail=0
assert() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  PASS: $desc"
    pass=$((pass + 1))
  else
    echo "  FAIL: $desc — expected $expected, got $actual" >&2
    fail=$((fail + 1))
  fi
}

echo "=== Case 1: HEAD == origin/main ==="
git -C "$CLONE" checkout --quiet main
set +e
out="$(RUN_GATE 2>&1)"; rc=$?
set -e
assert "exit 0" 0 "$rc"
[[ "$out" == *"HEAD is origin/main"* ]] || { echo "FAIL: expected OK banner, got: $out" >&2; fail=$((fail + 1)); }

echo "=== Case 2: stale HEAD, no override -> refused ==="
git -C "$CLONE" checkout --quiet stale
set +e
out="$(RUN_GATE 2>&1)"; rc=$?
set -e
assert "exit 1" 1 "$rc"
[[ "$out" == *"REFUSED"* ]] || { echo "FAIL: expected REFUSED banner, got: $out" >&2; fail=$((fail + 1)); }
[[ "$out" == *"$STALE_SHA"* ]] || { echo "FAIL: refusal must cite HEAD sha" >&2; fail=$((fail + 1)); }
[[ "$out" == *"$MAIN_SHA"* ]] || { echo "FAIL: refusal must cite origin/main sha" >&2; fail=$((fail + 1)); }

echo "=== Case 3: stale HEAD + FORCE_NON_MAIN_DEV=1 ==="
set +e
out="$(cd "$CLONE/packages/web-ui" && FORCE_NON_MAIN_DEV=1 bash scripts/gate-main-branch.sh 2>&1)"; rc=$?
set -e
assert "exit 0" 0 "$rc"
[[ "$out" == *"BRANCH-GATE BYPASS ACTIVE"* ]] || { echo "FAIL: expected loud banner" >&2; fail=$((fail + 1)); }
[[ "$out" == *"FORCE_NON_MAIN_DEV=1"* ]] || { echo "FAIL: banner must name the override" >&2; fail=$((fail + 1)); }

echo "=== Case 4: stale HEAD + BTE_BRANCH_GATE_OK=1 (start.sh signal, silent) ==="
set +e
out="$(cd "$CLONE/packages/web-ui" && BTE_BRANCH_GATE_OK=1 bash scripts/gate-main-branch.sh 2>&1)"; rc=$?
set -e
assert "exit 0" 0 "$rc"
[[ -z "$out" ]] || { echo "FAIL: start.sh path must be silent, got: $out" >&2; fail=$((fail + 1)); }

echo "=== Case 5: stale HEAD + BTE_SKIP_BRANCH_GATE=1 ==="
set +e
out="$(cd "$CLONE/packages/web-ui" && BTE_SKIP_BRANCH_GATE=1 bash scripts/gate-main-branch.sh 2>&1)"; rc=$?
set -e
assert "exit 0" 0 "$rc"
[[ "$out" == *"BRANCH-GATE BYPASS ACTIVE"* ]] || { echo "FAIL: expected loud banner" >&2; fail=$((fail + 1)); }
[[ "$out" == *"BTE_SKIP_BRANCH_GATE=1"* ]] || { echo "FAIL: banner must name the override" >&2; fail=$((fail + 1)); }

echo "=== Case 6: cwd not a git repo -> silent allow ==="
NON_GIT="$WORK/non-git"
mkdir -p "$NON_GIT"
cp "$GATE_SCRIPT" "$NON_GIT/gate-main-branch.sh"
chmod +x "$NON_GIT/gate-main-branch.sh"
set +e
out="$(cd "$NON_GIT" && bash gate-main-branch.sh 2>&1)"; rc=$?
set -e
assert "exit 0" 0 "$rc"

# --- Case 7: `npm run dev` honours the predev hook ---------------------------
#
# Skipped when npm is unavailable, when the repo is too lightweight for an
# install (CI smoke runs without node_modules), or under CI=1 where we just
# rely on `predev` script wiring already asserted above. We still assert the
# behaviour can be reproduced when run interactively against the real repo.
if command -v npm >/dev/null 2>&1; then
  WEB_UI_DIR="$REPO_ROOT/packages/web-ui"
  if [[ -d "$WEB_UI_DIR/node_modules" ]]; then
    echo "=== Case 7: npm run dev aborts when gate refuses (real repo, stale HEAD simulation) ==="
    # Use the env-variable refusal path: temporarily clear BTE_BRANCH_GATE_OK
    # and inject a stub `git` that lies about origin/main so the gate refuses
    # without actually moving HEAD on the shared worktree.
    STUB_BIN="$WORK/stubbin"
    mkdir -p "$STUB_BIN"
    REAL_GIT="$(command -v git)"
    cat > "$STUB_BIN/git" <<EOF
#!/usr/bin/env bash
# Stub git: every rev-parse origin/main reports a synthetic SHA so the gate
# sees HEAD != origin/main. Everything else delegates to the real git.
if [[ "\$*" == *"rev-parse origin/main"* ]]; then
  echo "0000000000000000000000000000000000000000"
  exit 0
fi
exec "$REAL_GIT" "\$@"
EOF
    chmod +x "$STUB_BIN/git"
    set +e
    out="$(cd "$WEB_UI_DIR" && PATH="$STUB_BIN:$PATH" \
      env -u BTE_BRANCH_GATE_OK -u FORCE_NON_MAIN_DEV -u BTE_SKIP_BRANCH_GATE \
      npm run dev --silent 2>&1)"; rc=$?
    set -e
    if [[ "$rc" -eq 0 ]]; then
      echo "FAIL: npm run dev must abort when predev refuses (rc=0)" >&2
      fail=$((fail + 1))
    else
      echo "  PASS: npm run dev refused (rc=$rc)"
      pass=$((pass + 1))
    fi
    [[ "$out" == *"REFUSED"* ]] || { echo "FAIL: predev refusal banner missing from npm output" >&2; fail=$((fail + 1)); }
  else
    echo "=== Case 7 skipped (no node_modules in $WEB_UI_DIR) ==="
  fi
else
  echo "=== Case 7 skipped (npm unavailable) ==="
fi

echo
echo "Summary: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]] || exit 1
