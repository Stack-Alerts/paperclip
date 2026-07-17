#!/usr/bin/env bash
# bump-version.sh — BTC version-control auto-bumper.
#
# Reads paths changed since the last version bump commit (or the last
# 100 commits if no bump commit exists yet), and bumps the appropriate
# version component:
#
#   1) BTC-Paperclip VERSION at worktree root
#      - bumps BUILD if any BTC customizations path changed (server/src,
#        ui/src, packages/plugins/<ours>/src, scripts/, AGENTS.md, etc.)
#      - never bumps MAJOR/MINOR/PATCH (those are manual — see --manual)
#
#   2) Each custom plugin's VERSION under packages/plugins/<plugin>/
#      - bumps BUILD only if THAT plugin's src/ was touched
#
# Reads paths to monitor from .bump-paths.json at the worktree root.
# That file lists which globs count as "BTC customization" changes.
#
# Exit codes:
#   0 — bump was performed and committed (or nothing to bump)
#   1 — invalid invocation
#   2 — git error
#   3 — version file unreadable / unwritable
#
# Usage:
#   scripts/bump-version.sh                  # auto-detect from HEAD..HEAD~ range
#   scripts/bump-version.sh --manual patch   # manual bump (patch component)
#   scripts/bump-version.sh --manual minor
#   scripts/bump-version.sh --manual major
#   scripts/bump-version.sh --dry-run        # show what would change, no edits
#   scripts/bump-version.sh --no-commit      # bump files but skip the commit
#   scripts/bump-version.sh --since REF      # compare against REF instead of last bump
#
# Designed to be called from a post-commit hook; safe to run multiple
# times (idempotent within a single commit window).

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKTREE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
BTC_VERSION_FILE="${WORKTREE_ROOT}/VERSION"
BUMP_PATHS_FILE="${WORKTREE_ROOT}/.bump-paths.json"
PLUGINS_DIR="${WORKTREE_ROOT}/packages/plugins"

# ---------------------------------------------------------------------------
# Defaults / arg parsing
# ---------------------------------------------------------------------------

DRY_RUN="false"
NO_COMMIT="false"
MANUAL_LEVEL=""
SINCE_REF=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)    DRY_RUN="true"; shift ;;
    --no-commit)  NO_COMMIT="true"; shift ;;
    --manual)     MANUAL_LEVEL="${2:-}"; shift 2 ;;
    --since)      SINCE_REF="${2:-}"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed -e 's/^# //; s/^#//'; exit 0 ;;
    *)
      echo "bump-version.sh: unknown arg: $1" >&2
      exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Bump math
# ---------------------------------------------------------------------------

bump_version() {
  local current="$1"
  local component="$2"   # major | minor | patch | build
  local IFS='.'
  read -r -a parts <<< "$current"
  while [[ ${#parts[@]} -lt 4 ]]; do parts+=(0); done

  case "$component" in
    major) parts[0]=$((parts[0] + 1)); parts[1]=0; parts[2]=0; parts[3]=0 ;;
    minor) parts[1]=$((parts[1] + 1)); parts[2]=0; parts[3]=0 ;;
    patch) parts[2]=$((parts[2] + 1)); parts[3]=0 ;;
    build) parts[3]=$((parts[3] + 1)) ;;
    *) echo "bump-version.sh: unknown component: $component" >&2; return 2 ;;
  esac
  local IFS='.'
  echo "${parts[*]}"
}

read_version() {
  local f="$1"
  if [[ ! -f "$f" ]]; then echo "0.0.0.0"; return; fi
  tr -d '[:space:]' < "$f"
}

write_version() {
  local f="$1"
  local v="$2"
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[dry-run] would write $v to $f"
  else
    printf '%s\n' "$v" > "$f"
  fi
}

# ---------------------------------------------------------------------------
# Path classification — which paths count as BTC customizations?
#
# Read from .bump-paths.json if present; otherwise use a sensible default.
# Custom plugin paths under packages/plugins/<plugin>/<src>/ also bump
# that plugin's own VERSION.
# ---------------------------------------------------------------------------

BTC_DEFAULT_PATHS=(
  "server/src"
  "ui/src"
  "scripts"
  "AGENTS.md"
  ".paperclip"
)

custom_plugin_paths() {
  local plugin="$1"
  printf '%s\n' \
    "packages/plugins/$plugin/src" \
    "packages/plugins/$plugin/dist" \
    "packages/plugins/$plugin/manifest" \
    "packages/plugins/$plugin/package.json"
}

list_btc_paths() {
  if [[ -f "$BUMP_PATHS_FILE" ]]; then
    # Tiny JSON-ish parser: extract "path": "..." entries from the file.
    # Avoids pulling in jq for a 5-line config.
    grep -oE '"path"[[:space:]]*:[[:space:]]*"[^"]+"' "$BUMP_PATHS_FILE" \
      | sed -E 's/.*"path"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/'
  else
    printf '%s\n' "${BTC_DEFAULT_PATHS[@]}"
  fi
}

list_custom_plugins() {
  # A "custom plugin" is any plugin under packages/plugins/ that has a
  # VERSION file. (Plugins we don't own won't have one yet.)
  #
  # IMPORTANT: the last statement must always succeed (return 0). With
  # `set -e`, a failed `[[ -f ... ]] && basename` short-circuits and the
  # function returns 1 — which would then kill the parent script the moment
  # it's invoked via `$(list_custom_plugins)` (command substitution does NOT
  # suppress set -e on the calling context). The trailing `|| true` keeps
  # the function returning 0 even when no plugins match.
  if [[ ! -d "$PLUGINS_DIR" ]]; then return 0; fi
  local d out=()
  for d in "$PLUGINS_DIR"/*/; do
    if [[ -f "$d/VERSION" ]]; then
      out+=( "$(basename "$d")" )
    fi
  done
  printf '%s\n' "${out[@]}"
  return 0
}

# ---------------------------------------------------------------------------
# Diff vs last bump
# ---------------------------------------------------------------------------

LAST_BUMP_SHA="$SINCE_REF"
if [[ -z "$LAST_BUMP_SHA" ]]; then
  # The most recent commit on this branch that touched the BTC VERSION
  # file is the previous bump commit. Use its parent as the diff base.
  LAST_BUMP_SHA="$(git log -n 1 --format=%H -- "$BTC_VERSION_FILE" 2>/dev/null || echo "")"
fi

if [[ -n "$LAST_BUMP_SHA" ]]; then
  DIFF_RANGE="${LAST_BUMP_SHA}..HEAD"
else
  # No prior bump — diff against the last 100 commits as a sensible
  # bootstrap default.
  DIFF_RANGE="HEAD~100..HEAD"
fi

# `git diff` returns paths relative to the worktree root.
changed_files() {
  git diff --name-only --diff-filter=ACMRT "$DIFF_RANGE" 2>/dev/null || \
    git log --name-only --pretty=format: "$DIFF_RANGE" 2>/dev/null | sort -u
}

changed_files_count() {
  changed_files | grep -cvE '^\s*$' || true
}

matches_any_path() {
  local file="$1"
  shift
  local p
  for p in "$@"; do
    # Strip trailing slashes for the comparison.
    p="${p%/}"
    if [[ "$file" == "$p" || "$file" == "$p/"* ]]; then
      return 0
    fi
  done
  return 1
}

# ---------------------------------------------------------------------------
# Decide what to bump
# ---------------------------------------------------------------------------

btc_changed="false"
plugin_changes=()

files="$(changed_files)"
btc_paths=( $(list_btc_paths) )
custom_plugins=( $(list_custom_plugins) )

for f in $files; do
  if matches_any_path "$f" "${btc_paths[@]}"; then
    btc_changed="true"
  fi
  for plugin in "${custom_plugins[@]}"; do
    plugin_paths=( $(custom_plugin_paths "$plugin") )
    if matches_any_path "$f" "${plugin_paths[@]}"; then
      # Add plugin to bump list if not already there.
      found="false"
      for pc in "${plugin_changes[@]+"${plugin_changes[@]}"}"; do
        [[ "$pc" == "$plugin" ]] && found="true"
      done
      [[ "$found" == "true" ]] || plugin_changes+=( "$plugin" )
    fi
  done
done

# ---------------------------------------------------------------------------
# Apply bumps
# ---------------------------------------------------------------------------

current_btc="$(read_version "$BTC_VERSION_FILE")"
new_btc="$current_btc"

# ---------------------------------------------------------------------------
# Pre-commit integrity gate
#
# Refuse to commit a version bump while any plugin UI bundle is unbalanced
# (i.e. it would fail `node --check`). This catches the class of bug
# that produced the empty BackupManagerPage on 2026-07-16 (extra `)` in
# the dist/ui/index.js text edit broke parsing, page rendered empty even
# though data endpoints returned 200). Run after the bump files are
# written so we test the FINAL state; abort before `git commit` if any
# bundle is malformed so a half-broken state can't end up in the tree.
# ---------------------------------------------------------------------------
run_parse_gate() {
  local errors=0
  # Gate 1: every plugin with a VERSION must have a parseable dist/ui bundle.
  for plugin in "${custom_plugins[@]}"; do
    local ui="${PLUGINS_DIR}/${plugin}/dist/ui/index.js"
    [[ -f "$ui" ]] || continue
    if ! node --check "$ui" >/dev/null 2>&1; then
      echo "bump-version.sh: GUARD FAIL — ${plugin} UI bundle fails to parse:" >&2
      node --check "$ui" 2>&1 | head -3 >&2
      errors=$((errors + 1))
    fi
  done
  # Gate 2: the BTC server bundle itself (catches app.ts / routes / etc).
  local server_dist="${WORKTREE_ROOT}/server/dist/index.js"
  [[ -f "$server_dist" ]] || server_dist="${WORKTREE_ROOT}/dist/index.js"
  if [[ -f "$server_dist" ]]; then
    if ! node --check "$server_dist" >/dev/null 2>&1; then
      echo "bump-version.sh: GUARD FAIL — BTC server bundle fails to parse:" >&2
      node --check "$server_dist" 2>&1 | head -3 >&2
      errors=$((errors + 1))
    fi
  fi
  return "$errors"
}

# Only run the gate if we're about to commit. --dry-run and --no-commit
# stay side-effect-free.
if [[ "$NO_COMMIT" != "true" && "$DRY_RUN" != "true" ]]; then
  if ! run_parse_gate; then
    echo "bump-version.sh: refusing to commit — fix the parse error(s) above and re-run" >&2
    exit 4
  fi
fi

if [[ -n "$MANUAL_LEVEL" ]]; then
  new_btc="$(bump_version "$current_btc" "$MANUAL_LEVEL")"
  echo "manual bump: $current_btc -> $new_btc (component=$MANUAL_LEVEL)"
elif [[ "$btc_changed" == "true" ]]; then
  new_btc="$(bump_version "$current_btc" build)"
  echo "auto bump: $current_btc -> $new_btc (component=build, BTC customization paths changed)"
fi

plugin_versions_after=()
for plugin in "${custom_plugins[@]}"; do
  plugin_file="${PLUGINS_DIR}/${plugin}/VERSION"
  current="$(read_version "$plugin_file")"
  if [[ " ${plugin_changes[@]+"${plugin_changes[@]}"} " == *" $plugin "* ]]; then
    new="$(bump_version "$current" build)"
    echo "auto bump: ${plugin}/VERSION $current -> $new (component=build, plugin src changed)"
  else
    new="$current"
    [[ "$DRY_RUN" == "true" || -n "$MANUAL_LEVEL" ]] || true # silence
  fi
  if [[ "$new" != "$current" ]]; then
    write_version "$plugin_file" "$new"
  fi
  plugin_versions_after+=( "$plugin=$new" )
done

if [[ "$new_btc" != "$current_btc" ]]; then
  write_version "$BTC_VERSION_FILE" "$new_btc"
fi

# ---------------------------------------------------------------------------
# Commit (unless --no-commit or --dry-run)
# ---------------------------------------------------------------------------

if [[ "$NO_COMMIT" == "true" || "$DRY_RUN" == "true" ]]; then
  exit 0
fi

# Only commit if we actually changed something.
changed_any="false"
[[ "$new_btc" != "$current_btc" ]] && changed_any="true"
for plugin in "${custom_plugins[@]}"; do
  current="$(read_version "${PLUGINS_DIR}/${plugin}/VERSION")"
  [[ "$current" != "${plugin_versions_after[0]}" ]] && changed_any="true"
done

if [[ "$changed_any" == "false" ]]; then
  echo "nothing to bump (BTC unchanged, no plugin src touched)"
  exit 0
fi

# Stage the changed VERSION files explicitly (no `git add -A` to avoid
# accidentally sweeping in unrelated dirty-tree changes).
git add "$BTC_VERSION_FILE"
for plugin in "${custom_plugins[@]}"; do
  git add "${PLUGINS_DIR}/${plugin}/VERSION"
done

git commit -m "chore(version): bump $( [[ "$MANUAL_LEVEL" ]] && echo "$MANUAL_LEVEL" || echo "build" )

- BTC-Paperclip: ${current_btc} -> ${new_btc}$(printf '\n'; for plugin in "${custom_plugins[@]}"; do
  current="$(read_version "${PLUGINS_DIR}/${plugin}/VERSION")"
  [[ "$current" != "${plugin_versions_after[0]}" ]] && echo "- ${plugin}: ${current} -> ${plugin_versions_after[0]}"
done | sed 's/^/  /')" --no-verify || {
  echo "bump-version.sh: git commit failed (likely nothing staged)" >&2
  exit 0   # don't fail the post-commit hook
}

echo "bump committed"