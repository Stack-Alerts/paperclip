#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-false}"
TMP_DIR="${TMP_DIR:-/tmp}"
LOG_DIR="${LOG_DIR:-$HOME/.paperclip/instances/default/logs}"
LOG_FILE="${LOG_DIR}/tmp-cleanup.log"
LOCK_FILE="${TMP_DIR}/tmp-cleanup.lock"
STATE_FILE="${LOG_DIR}/tmp-cleanup-state.json"

SO_STALE_HOURS="${SO_STALE_HOURS:-24}"
CONFIG_STALE_HOURS="${CONFIG_STALE_HOURS:-24}"
MISC_STALE_HOURS="${MISC_STALE_HOURS:-168}"
EMERGENCY_THRESHOLD_PCT="${EMERGENCY_THRESHOLD_PCT:-80}"
EMERGENCY_REDUCED_HOURS="${EMERGENCY_REDUCED_HOURS:-6}"
ALERT_THRESHOLD_PCT="${ALERT_THRESHOLD_PCT:-70}"

mkdir -p "$LOG_DIR"

log() {
    local level="$1"; shift
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[$ts] [$level] $*" | tee -a "$LOG_FILE"
}

tmp_usage_pct() {
    local line used total
    line=$(df --output=pcent "$TMP_DIR" 2>/dev/null | tail -1 | tr -d ' %')
    echo "${line:-0}"
}

tmp_used_kb() {
    df --output=used "$TMP_DIR" 2>/dev/null | tail -1 | tr -d ' '
}

human_size() {
    local bytes="$1"
    if [[ -z "$bytes" || "$bytes" -eq 0 ]]; then
        echo "0B"
    elif ((bytes > 1073741824)); then
        awk "BEGIN {printf \"%.1fG\", $bytes/1073741824}"
    elif ((bytes > 1048576)); then
        awk "BEGIN {printf \"%.1fM\", $bytes/1048576}"
    elif ((bytes > 1024)); then
        awk "BEGIN {printf \"%.1fK\", $bytes/1024}"
    else
        echo "${bytes}B"
    fi
}

remove_file() {
    local f="$1"
    local sz
    sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
    if [[ "$DRY_RUN" == "true" ]]; then
        log DRY_RUN "Would remove: $f ($(human_size "$sz"))"
    else
        if rm -f "$f"; then
            log INFO "Removed: $f ($(human_size "$sz"))"
        else
            log WARN "Failed to remove: $f"
        fi
    fi
}

remove_dir() {
    local d="$1"
    local sz
    sz=$(du -sb "$d" 2>/dev/null | cut -f1 || echo 0)
    if [[ "$DRY_RUN" == "true" ]]; then
        log DRY_RUN "Would remove dir: $d ($(human_size "$sz"))"
    else
        if rm -rf "$d"; then
            log INFO "Removed dir: $d ($(human_size "$sz"))"
        else
            log WARN "Failed to remove dir: $d"
        fi
    fi
}

cleanup_hidden_so() {
    local stale_hours="$1"
    local stale_seconds=$((stale_hours * 3600))
    local now
    now=$(date +%s)

    log INFO "Scanning hidden JIT .so artifacts (older than ${stale_hours}h)..."

    local files=()
    while IFS= read -r -d '' f; do
        local mtime
        mtime=$(stat -c %Y "$f" 2>/dev/null || echo 0)
        local age=$((now - mtime))
        if ((age > stale_seconds)); then
            files+=("$f")
        fi
    done < <(find "$TMP_DIR" -maxdepth 1 -name '.*.so' -type f -print0 2>/dev/null)

    if [[ ${#files[@]} -eq 0 ]]; then
        log INFO "No stale hidden .so files found."
        return
    fi

    log INFO "Found ${#files[@]} stale hidden .so file(s)"
    for f in "${files[@]}"; do
        remove_file "$f"
    done
}

cleanup_by_mmin() {
    local desc="$1" pattern="$2" type="$3" stale_hours="$4"

    log INFO "Scanning $desc (older than ${stale_hours}h)..."

    if [[ "$type" == "f" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            find "$TMP_DIR" -maxdepth 1 -name "$pattern" -type f -mmin +"$((stale_hours * 60))" 2>/dev/null | while IFS= read -r f; do
                log DRY_RUN "Would remove: $f ($(human_size "$(stat -c %s "$f" 2>/dev/null || echo 0)"))"
            done
        else
            find "$TMP_DIR" -maxdepth 1 -name "$pattern" -type f -mmin +"$((stale_hours * 60))" -delete 2>/dev/null && \
                log INFO "Cleaned files: $pattern"
        fi
    elif [[ "$type" == "d" ]]; then
        local dirs=()
        while IFS= read -r -d '' d; do
            dirs+=("$d")
        done < <(find "$TMP_DIR" -maxdepth 1 -name "$pattern" -type d -mmin +"$((stale_hours * 60))" -print0 2>/dev/null)

        if [[ ${#dirs[@]} -eq 0 ]]; then
            log INFO "No stale $desc found."
            return
        fi

        log INFO "Found ${#dirs[@]} stale $desc"
        for d in "${dirs[@]}"; do
            remove_dir "$d"
        done
    fi
}

write_state() {
    local usage_pct="$1" last_run="$2"
    cat > "$STATE_FILE" <<EOF
{"lastRun": "$last_run", "usagePct": $usage_pct, "dryRun": $DRY_RUN}
EOF
}

main() {
    log INFO "=== TMP cleanup started ==="

    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        log WARN "Another cleanup instance is running (lock held on $LOCK_FILE). Exiting."
        exit 0
    fi

    local before_kb
    before_kb=$(tmp_used_kb)
    before_kb="${before_kb:-0}"

    local usage_pct
    usage_pct=$(tmp_usage_pct)
    log INFO "Pre-cleanup /tmp usage: ${usage_pct}% ($(human_size "$((before_kb * 1024))"))"

    local so_hours="$SO_STALE_HOURS"
    local config_hours="$CONFIG_STALE_HOURS"
    local misc_hours="$MISC_STALE_HOURS"

    if ((usage_pct >= EMERGENCY_THRESHOLD_PCT)); then
        log WARN "EMERGENCY MODE: /tmp at ${usage_pct}% >= ${EMERGENCY_THRESHOLD_PCT}%"
        log WARN "Reducing all thresholds to ${EMERGENCY_REDUCED_HOURS}h"
        so_hours="$EMERGENCY_REDUCED_HOURS"
        config_hours="$EMERGENCY_REDUCED_HOURS"
        misc_hours="$EMERGENCY_REDUCED_HOURS"
    fi

    cleanup_hidden_so "$so_hours"
    cleanup_by_mmin "libpeershim .so files" "libpeershim*.so" "f" "$so_hours"
    cleanup_by_mmin "paperclip-opencode-config dirs" "paperclip-opencode-config-*" "d" "$config_hours"
    cleanup_by_mmin "stale markdown artifacts" "*.md" "f" "$misc_hours"
    cleanup_by_mmin "stale python temp scripts" "_*.py" "f" "$misc_hours"
    cleanup_by_mmin "stale patch files" "*.patch.py" "f" "$misc_hours"
    cleanup_by_mmin "stale result text files" "*_result.txt" "f" "$misc_hours"

    if [[ "$DRY_RUN" != "true" ]]; then
        find "$TMP_DIR/opencode" -maxdepth 2 -type d -empty -delete 2>/dev/null || true
    fi

    local after_kb
    after_kb=$(tmp_used_kb)
    after_kb="${after_kb:-0}"
    local freed_kb=$((before_kb - after_kb))
    if ((freed_kb < 0)); then freed_kb=0; fi

    local after_pct
    after_pct=$(tmp_usage_pct)

    local now_ts
    now_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    write_state "$after_pct" "$now_ts"

    log INFO "Post-cleanup /tmp usage: ${after_pct}% (freed: $(human_size "$((freed_kb * 1024))"))"

    if ((after_pct >= ALERT_THRESHOLD_PCT)); then
        log WARN "ALERT: /tmp usage still at ${after_pct}% after cleanup. Manual investigation needed."
    fi

    log INFO "=== TMP cleanup complete ==="
}

main "$@"
