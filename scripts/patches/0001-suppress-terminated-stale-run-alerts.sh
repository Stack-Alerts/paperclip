#!/usr/bin/env bash
# 0001-suppress-terminated-stale-run-alerts.sh
#
# Suppress duplicate stale-run alerts for terminated runs in the opencode_local
# adapter. Patches the Paperclip server's recovery service to skip creating
# stale-run evaluation issues when the source issue is already in a terminal
# state (done/cancelled).
#
# Without this fix, the stale-run watchdog creates a new evaluation issue every
# time a run for a completed issue is detected as silent. The evaluation cannot
# be actioned (the source work is done) and generates infinite duplicate noise.
#
# USAGE:
#   scripts/patches/0001-suppress-terminated-stale-run-alerts.sh
#
# Apply after every `npx paperclipai@latest` cache update or reinstall.
# Safe to reapply idempotently.
#
# EXIT CODES:
#   0 -- patch applied or already present
#   1 -- target file not found

set -euo pipefail

NPX_CACHE_BASE="${HOME}/.npm/_npx"
PATCH_MARKER='Skip stale-run evaluation when the source issue is already terminated'
MATCH_LINE='const sourceIssue = await resolveStaleRunSourceIssue(input.run);'

patched_count=0
not_found_count=0
already_patched_count=0

for cache_dir in "$NPX_CACHE_BASE"/*/; do
    target="${cache_dir}node_modules/@paperclipai/server/dist/services/recovery/service.js"
    if [[ ! -f "$target" ]]; then
        continue
    fi

    if grep -qF "$PATCH_MARKER" "$target" 2>/dev/null; then
        echo "ALREADY PATCHED: $target"
        already_patched_count=$((already_patched_count + 1))
        continue
    fi

    line_num=$(grep -nF "$MATCH_LINE" "$target" | head -1 | cut -d: -f1)
    if [[ -z "$line_num" ]]; then
        echo "PATTERN NOT FOUND: $target (unexpected file structure)"
        not_found_count=$((not_found_count + 1))
        continue
    fi

    # Insert after the matched line
    tmpfile=$(mktemp)
    sed "${line_num}a\\
        // Skip stale-run evaluation when the source issue is already terminated:\\
        // the work is no longer relevant, and creating alerts for terminated issues\\
        // produces duplicate noise that cannot be actioned.\\
        if (sourceIssue \&\& [\"done\", \"cancelled\"].includes(sourceIssue.status)) {\
            return { kind: \"skipped\" };\
        }" "$target" > "$tmpfile"
    mv "$tmpfile" "$target"
    echo "PATCHED: $target (inserted after line $line_num)"
    patched_count=$((patched_count + 1))
done

echo ""
echo "--- Summary ---"
echo "Patched:        $patched_count"
echo "Already fixed:  $already_patched_count"
echo "Not found:      $not_found_count"
echo ""

if [[ $not_found_count -gt 0 && $patched_count -eq 0 && $already_patched_count -eq 0 ]]; then
    exit 1
fi

# If anything was changed, suggest restart
if [[ $patched_count -gt 0 ]]; then
    echo "RESTART REQUIRED: The Paperclip server must be restarted for the change to take effect."
    echo "  pkill -f 'paperclipai run' || true"
    echo "  cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip"
    echo "  nohup npx paperclipai@latest run > /dev/null 2>&1 &"
fi

exit 0
