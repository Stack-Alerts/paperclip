#!/bin/bash
# Setup script for Phase 4a: Merge-Dispatch Routine
# Creates Paperclip routine to run merge_dispatch_routine.py every 5 minutes

set -euo pipefail

# Paperclip environment — must be set by caller or operator
PAPERCLIP_API_URL="${PAPERCLIP_API_URL:-https://stack-alerts.paperclipai.com}"
PAPERCLIP_API_KEY="${PAPERCLIP_API_KEY:-}"
PAPERCLIP_COMPANY_ID="${PAPERCLIP_COMPANY_ID:-}"

# Agent and project identifiers
AUTOMATION_ENGINEER_ID="2b9152a6-07f6-4ae9-87fa-c824012c9ff6"
TRACKING_ISSUE="BTCAAAAA-30048"

if [[ -z "$PAPERCLIP_API_KEY" ]]; then
  echo "ERROR: PAPERCLIP_API_KEY not set"
  exit 1
fi

if [[ -z "$PAPERCLIP_COMPANY_ID" ]]; then
  echo "ERROR: PAPERCLIP_COMPANY_ID not set"
  exit 1
fi

echo "Creating Phase 4a Merge-Dispatch routine..."
echo "  API: $PAPERCLIP_API_URL"
echo "  Company: $PAPERCLIP_COMPANY_ID"
echo "  Agent: $AUTOMATION_ENGINEER_ID"

# Step 1: Get projects to find the right one for infrastructure tasks
echo -e "\n[1/3] Fetching projects..."
PROJECTS=$(curl -s "$PAPERCLIP_API_URL/api/companies/$PAPERCLIP_COMPANY_ID/projects" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json")

# Try to find infrastructure or automation project
PROJECT_ID=$(echo "$PROJECTS" | jq -r '.[] | select(.title | test("Infrastructure|Automation|DevOps"; "i")) | .id' | head -1)

if [[ -z "$PROJECT_ID" ]]; then
  # Fallback: use first project
  PROJECT_ID=$(echo "$PROJECTS" | jq -r '.[0].id')
fi

echo "  Using project: $PROJECT_ID"

# Step 2: Create the routine
echo -e "\n[2/3] Creating routine..."
ROUTINE_RESPONSE=$(curl -s -X POST "$PAPERCLIP_API_URL/api/companies/$PAPERCLIP_COMPANY_ID/routines" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Phase 4a: Merge-Dispatch Routine",
    "description": "Automatically open and merge PRs for in_review issues with valid Fix-SHA and recent merge_request interactions. Cadence: every 5 minutes.",
    "assigneeAgentId": "'"$AUTOMATION_ENGINEER_ID"'",
    "projectId": "'"$PROJECT_ID"'",
    "priority": "high",
    "status": "active",
    "concurrencyPolicy": "coalesce_if_active",
    "catchUpPolicy": "skip_missed"
  }')

ROUTINE_ID=$(echo "$ROUTINE_RESPONSE" | jq -r '.routine.id // .id // empty')

if [[ -z "$ROUTINE_ID" ]]; then
  echo "ERROR: Failed to create routine"
  echo "Response: $ROUTINE_RESPONSE"
  exit 1
fi

echo "  Created routine: $ROUTINE_ID"

# Step 3: Add cron schedule trigger
echo -e "\n[3/3] Adding cron trigger (every 5 minutes)..."
TRIGGER_RESPONSE=$(curl -s -X POST "$PAPERCLIP_API_URL/api/routines/$ROUTINE_ID/triggers" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "schedule",
    "cronExpression": "*/5 * * * *",
    "timezone": "UTC",
    "label": "Every 5 minutes"
  }')

TRIGGER_ID=$(echo "$TRIGGER_RESPONSE" | jq -r '.trigger.id // .id // empty')

if [[ -z "$TRIGGER_ID" ]]; then
  echo "ERROR: Failed to add trigger"
  echo "Response: $TRIGGER_RESPONSE"
  exit 1
fi

echo "  Created trigger: $TRIGGER_ID"

# Summary
echo -e "\n✅ Phase 4a Merge-Dispatch routine setup complete!"
echo ""
echo "Routine details:"
echo "  ID: $ROUTINE_ID"
echo "  Title: Phase 4a: Merge-Dispatch Routine"
echo "  Assigned to: AutomationEngineer"
echo "  Schedule: Every 5 minutes (*/5 * * * *)"
echo "  Concurrency: Coalesce if active"
echo "  Catch-up: Skip missed"
echo ""
echo "Next steps:"
echo "  1. Configure the routine's execution workspace to run: python3 scripts/merge_dispatch_routine.py"
echo "  2. Ensure GH_TOKEN (CEO GitHub token) is set in routine environment"
echo "  3. Test with a manual run via POST /api/routines/$ROUTINE_ID/run"
echo "  4. Monitor in Paperclip dashboard"
echo ""
echo "Issue: [$TRACKING_ISSUE](/BTCAAAAA/issues/$TRACKING_ISSUE)"
