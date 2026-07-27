#!/usr/bin/env bash
# Verification for BTCAAAAA-41519 — auto-discovery of Paperclip plugins in
# backup-to-drive.sh. Sets up a fixture tree with valid plugins, non-plugins,
# malformed metadata, and missing artifacts; extracts the staging block from
# backup-to-drive.sh; runs it under BACKUP_PLUGIN_DISCOVERY_DIRS override; and
# asserts the staged output matches the discovery rule.
#
# Discovery rule under test:
#   A directory under packages/plugins/*/ whose package.json declares a
#   `paperclipPlugin` OBJECT (with required `manifest` and `worker` path
#   fields that resolve to existing files) is an eligible Paperclip plugin.
#   Non-plugins (no field, or `paperclipPlugin: null`) are silently skipped.
#   A package that declares `paperclipPlugin` but has malformed metadata must
#   fail the run loudly — we never silently drop a recoverable plugin.
#
# Exits 0 if all assertions pass, non-zero on the first failure.

set -uo pipefail

SCRIPT="/home/sirrus/.paperclip/scripts/backup-to-drive.sh"
STAGING_START=$(grep -n '^# 3) Paperclip plugin source' "$SCRIPT" | head -1 | cut -d: -f1)
STAGING_END=$(awk -v s="$STAGING_START" 'NR>=s && /^echo "  Plugin sources shipped:/{print NR; exit}' "$SCRIPT")
if [ -z "$STAGING_START" ] || [ -z "$STAGING_END" ]; then
    echo "FAIL: could not locate plugin staging block in $SCRIPT" >&2
    exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkpkg() {
    # mkpkg <relpath> <package.json contents>
    local rel="$1" body="$2"
    mkdir -p "$WORK/$rel"
    printf '%s\n' "$body" > "$WORK/$rel/package.json"
}

# Valid plugin A — manifest + worker + ui, all on disk
mkdir -p "$WORK/proj/packages/plugins/paperclip-fixture-a/dist/ui"
mkdir -p "$WORK/proj/packages/plugins/paperclip-fixture-a/src"
mkpkg "proj/packages/plugins/paperclip-fixture-a" \
    '{"name":"paperclip-fixture-a","paperclipPlugin":{"manifest":"./dist/manifest.js","worker":"./dist/worker.js","ui":"./dist/ui/"}}'
echo m > "$WORK/proj/packages/plugins/paperclip-fixture-a/dist/manifest.js"
echo w > "$WORK/proj/packages/plugins/paperclip-fixture-a/dist/worker.js"
echo "export const a = 1;" > "$WORK/proj/packages/plugins/paperclip-fixture-a/src/index.ts"

# Valid plugin B — manifest + worker, no ui (ui is optional)
mkdir -p "$WORK/proj/packages/plugins/paperclip-fixture-b/dist"
mkpkg "proj/packages/plugins/paperclip-fixture-b" \
    '{"name":"paperclip-fixture-b","paperclipPlugin":{"manifest":"./dist/manifest.js","worker":"./dist/worker.js"}}'
echo m > "$WORK/proj/packages/plugins/paperclip-fixture-b/dist/manifest.js"
echo w > "$WORK/proj/packages/plugins/paperclip-fixture-b/dist/worker.js"

# Non-plugin: SDK (no paperclipPlugin field) — must be silently skipped
mkpkg "proj/packages/plugins/some-sdk" '{"name":"some-sdk"}'

# Non-plugin: CLI tool with explicit null — must be silently skipped
mkpkg "proj/packages/plugins/create-foo" '{"name":"create-foo","paperclipPlugin":null}'

# node_modules entry — must be excluded by the find filter
mkdir -p "$WORK/proj/node_modules/some-pkg/packages/plugins/should-skip/dist"
mkpkg "proj/node_modules/some-pkg/packages/plugins/should-skip" \
    '{"name":"should-skip","paperclipPlugin":{"manifest":"./dist/manifest.js","worker":"./dist/worker.js"}}'
echo m > "$WORK/proj/node_modules/some-pkg/packages/plugins/should-skip/dist/manifest.js"
echo w > "$WORK/proj/node_modules/some-pkg/packages/plugins/should-skip/dist/worker.js"

# examples entry — must be excluded by the find filter
mkdir -p "$WORK/proj/packages/plugins/examples/some-example/dist"
mkpkg "proj/packages/plugins/examples/some-example" \
    '{"name":"some-example","paperclipPlugin":{"manifest":"./dist/manifest.js","worker":"./dist/worker.js"}}'
echo m > "$WORK/proj/packages/plugins/examples/some-example/dist/manifest.js"
echo w > "$WORK/proj/packages/plugins/examples/some-example/dist/worker.js"

# Extract the staging block to a runnable script.
sed -n "${STAGING_START},${STAGING_END}p" "$SCRIPT" > "$WORK/staging.sh"

EXTRAS_DIR="$WORK/extras"
mkdir -p "$EXTRAS_DIR/plugins"

assert_eq() {
    # assert_eq <label> <expected> <actual>
    if [ "$2" != "$3" ]; then
        echo "FAIL [$1]: expected '$2', got '$3'" >&2
        exit 1
    fi
    echo "  ok  [$1]"
}

echo "=== auto-discover (BACKUP_PLUGIN_NAMES unset, BACKUP_PLUGIN_DISCOVERY_DIRS=fixture) ==="
BACKUP_PLUGIN_DISCOVERY_DIRS="$WORK/proj" \
    EXTRAS_SUMMARY="" EXTRAS_DIR="$EXTRAS_DIR" \
    bash "$WORK/staging.sh" > "$WORK/run1.out" 2> "$WORK/run1.err"
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "FAIL [auto-discover exit code]: expected 0, got $rc" >&2
    sed 's/^/  /' "$WORK/run1.err" >&2
    exit 1
fi

shipped="$(ls "$EXTRAS_DIR/plugins" | sort | tr '\n' ' ' | sed 's/ $//')"
assert_eq "shipped set" "proj__paperclip-fixture-a proj__paperclip-fixture-b" "$shipped"

# Must NOT have copied the non-plugins, node_modules, or examples fixtures.
for forbidden in \
    "$EXTRAS_DIR/plugins/proj__some-sdk" \
    "$EXTRAS_DIR/plugins/proj__create-foo" \
    "$EXTRAS_DIR/plugins/some-pkg__should-skip" \
    "$EXTRAS_DIR/plugins/some-example" \
    "$EXTRAS_DIR/plugins/proj__some-example" ; do
    if [ -e "$forbidden" ]; then
        echo "FAIL: forbidden fixture was staged: $forbidden" >&2
        exit 1
    fi
done
echo "  ok  [non-plugins + node_modules + examples all skipped]"

# Must have copied source + package.json for each valid plugin.
for f in src/index.ts package.json dist/manifest.js dist/worker.js ; do
    [ -f "$EXTRAS_DIR/plugins/proj__paperclip-fixture-a/$f" ] || {
        echo "FAIL: missing staged file proj__paperclip-fixture-a/$f" >&2
        exit 1
    }
done
echo "  ok  [fixture-a has src/, package.json, dist/ staged]"

[ -f "$EXTRAS_DIR/plugins/proj__paperclip-fixture-b/dist/manifest.js" ] || {
    echo "FAIL: missing dist/manifest.js for fixture-b" >&2
    exit 1
}
echo "  ok  [fixture-b has dist/ staged]"

echo ""
echo "=== allowlist override (BACKUP_PLUGIN_NAMES=fixture-a) ==="
rm -rf "$EXTRAS_DIR/plugins"; mkdir -p "$EXTRAS_DIR/plugins"
BACKUP_PLUGIN_DISCOVERY_DIRS="$WORK/proj" \
    BACKUP_PLUGIN_NAMES="paperclip-fixture-a" \
    EXTRAS_SUMMARY="" EXTRAS_DIR="$EXTRAS_DIR" \
    bash "$WORK/staging.sh" > "$WORK/run2.out" 2> "$WORK/run2.err" || {
    echo "FAIL [allowlist exit code]: $?" >&2
    sed 's/^/  /' "$WORK/run2.err" >&2
    exit 1
}
shipped="$(ls "$EXTRAS_DIR/plugins" | sort | tr '\n' ' ' | sed 's/ $//')"
assert_eq "allowlist shipped set" "proj__paperclip-fixture-a" "$shipped"

echo ""
echo "=== malformed (manifest field missing) aborts with rc=2 ==="
mkdir -p "$WORK/proj/packages/plugins/broken-no-manifest/dist"
mkpkg "proj/packages/plugins/broken-no-manifest" \
    '{"name":"broken-no-manifest","paperclipPlugin":{"worker":"./dist/worker.js"}}'
echo w > "$WORK/proj/packages/plugins/broken-no-manifest/dist/worker.js"
set +e
BACKUP_PLUGIN_DISCOVERY_DIRS="$WORK/proj" \
    EXTRAS_SUMMARY="" EXTRAS_DIR="$EXTRAS_DIR" \
    bash "$WORK/staging.sh" > "$WORK/run3.out" 2> "$WORK/run3.err"
rc=$?
set -e
assert_eq "malformed rc" 2 "$rc"
grep -q "missing required field(s): manifest" "$WORK/run3.err" || {
    echo "FAIL: stderr did not name the missing manifest field" >&2
    sed 's/^/  /' "$WORK/run3.err" >&2
    exit 1
}
echo "  ok  [stderr names the missing manifest field]"

echo ""
echo "=== malformed (declared artifact missing on disk) aborts with rc=3 ==="
rm -rf "$WORK/proj/packages/plugins/broken-no-manifest"
mkdir -p "$WORK/proj/packages/plugins/broken-missing-artifact/dist"
mkpkg "proj/packages/plugins/broken-missing-artifact" \
    '{"name":"broken-missing-artifact","paperclipPlugin":{"manifest":"./dist/manifest.js","worker":"./dist/worker.js"}}'
echo w > "$WORK/proj/packages/plugins/broken-missing-artifact/dist/worker.js"
set +e
BACKUP_PLUGIN_DISCOVERY_DIRS="$WORK/proj" \
    EXTRAS_SUMMARY="" EXTRAS_DIR="$EXTRAS_DIR" \
    bash "$WORK/staging.sh" > "$WORK/run4.out" 2> "$WORK/run4.err"
rc=$?
set -e
assert_eq "missing-artifact rc" 3 "$rc"
grep -q "paperclipPlugin.manifest=./dist/manifest.js does not exist" "$WORK/run4.err" || {
    echo "FAIL: stderr did not name the missing artifact path" >&2
    sed 's/^/  /' "$WORK/run4.err" >&2
    exit 1
}
echo "  ok  [stderr names the missing artifact path]"

echo ""
echo "=== malformed (paperclipPlugin is array) aborts with rc=2 ==="
rm -rf "$WORK/proj/packages/plugins/broken-missing-artifact"
mkpkg "proj/packages/plugins/broken-array" \
    '{"name":"broken-array","paperclipPlugin":["not","an","object"]}'
set +e
BACKUP_PLUGIN_DISCOVERY_DIRS="$WORK/proj" \
    EXTRAS_SUMMARY="" EXTRAS_DIR="$EXTRAS_DIR" \
    bash "$WORK/staging.sh" > "$WORK/run5.out" 2> "$WORK/run5.err"
rc=$?
set -e
assert_eq "wrong-type rc" 2 "$rc"
grep -q "must be an object, got list" "$WORK/run5.err" || {
    echo "FAIL: stderr did not call out the wrong type" >&2
    sed 's/^/  /' "$WORK/run5.err" >&2
    exit 1
}
echo "  ok  [stderr names the wrong type]"

echo ""
echo "=== auto-recovers once malformed fixtures are removed ==="
rm -rf "$WORK/proj/packages/plugins/broken-array"
rm -rf "$EXTRAS_DIR/plugins"; mkdir -p "$EXTRAS_DIR/plugins"
BACKUP_PLUGIN_DISCOVERY_DIRS="$WORK/proj" \
    EXTRAS_SUMMARY="" EXTRAS_DIR="$EXTRAS_DIR" \
    bash "$WORK/staging.sh" > "$WORK/run6.out" 2> "$WORK/run6.err"
shipped="$(ls "$EXTRAS_DIR/plugins" | sort | tr '\n' ' ' | sed 's/ $//')"
assert_eq "post-recovery shipped set" "proj__paperclip-fixture-a proj__paperclip-fixture-b" "$shipped"

echo ""
echo "ALL DISCOVERY ASSERTIONS PASSED"
