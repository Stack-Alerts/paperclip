#!/usr/bin/env bash
# Shorthand for agents to report Hindsight memory quality.
# Auto-detects agent identity from Paperclip environment.
#
# Usage from within a Paperclip heartbeat:
#   source scripts/hindsight_feedback_agent.sh
#   hindsight_feedback 4 "Recall was accurate and timely"
#
#   # Or with explicit ratings:
#   hindsight_feedback --recall 5 --retain 4 --helpfulness 5 "Perfect recall this run"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_hf_py() {
    python3 "$SCRIPT_DIR/hindsight_feedback_collector.py" "$@"
}

hindsight_feedback() {
    local agent="${PAPERCLIP_AGENT_NAME:-unknown}"
    local run_id="${PAPERCLIP_RUN_ID:-}"
    local issue_id="${PAPERCLIP_ISSUE_ID:-}"
    local recall=""
    local retain=""
    local help=""
    local notes=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --recall) recall="$2"; shift 2 ;;
            --retain) retain="$2"; shift 2 ;;
            --helpfulness) help="$2"; shift 2 ;;
            --agent) agent="$2"; shift 2 ;;
            -*) shift ;;
            [1-5]) help="$1"; shift ;;
            *)
                notes="$*"
                break
                ;;
        esac
    done

    local args=(
        --agent "$agent"
    )
    [[ -n "$run_id" ]] && args+=(--run-id "$run_id")
    [[ -n "$issue_id" ]] && args+=(--issue-id "$issue_id")
    [[ -n "$recall" ]] && args+=(--recall-quality "$recall")
    [[ -n "$retain" ]] && args+=(--retain-relevance "$retain")
    [[ -n "$help" ]] && args+=(--helpfulness "$help")
    [[ -n "$notes" ]] && args+=(--notes "$notes")

    _hf_py submit "${args[@]}"
}
