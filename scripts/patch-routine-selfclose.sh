#!/usr/bin/env bash
# patch-routine-selfclose.sh
#
# Patches the running Paperclip server instance to fix the routine self-close
# bug: when a routine execution run completes successfully, the issue status
# is never transitioned to "done", leaving a growing tail of stuck in_progress
# routine instances.
#
# Root cause:
#   releaseIssueExecutionAndPromote() in heartbeat.js clears the execution
#   lock but never calls issuesSvc.update() with status:"done" when the run
#   status is "succeeded" and the issue originKind is "routine_execution".
#
# This script applies the fix to the currently-running npx cache instance.
# Run it after every `paperclipai run` server restart.
#
# Usage:
#   bash scripts/patch-routine-selfclose.sh
#
# Idempotent: safe to run multiple times — the sentinel comment ensures
# the patch is only applied once.

set -euo pipefail

SERVER_PID=$(pgrep -f "paperclipai run" 2>/dev/null | head -1)
if [[ -z "$SERVER_PID" ]]; then
  echo "ERROR: No running paperclipai server found." >&2
  echo "Start the server first, then run this patch." >&2
  exit 1
fi

HEARTBEAT_FILE=$(find /home/sirrus/.npm/_npx -path "*/@paperclipai/server/dist/services/heartbeat.js" -type f 2>/dev/null | head -1)

if [[ -z "$HEARTBEAT_FILE" ]]; then
  echo "ERROR: Could not find heartbeat.js in npx cache." >&2
  exit 1
fi

echo "Found heartbeat.js at: $HEARTBEAT_FILE"

if grep -q "self-close routine" "$HEARTBEAT_FILE" 2>/dev/null; then
  echo "Fix already applied — nothing to do."
  exit 0
fi

# Apply the patch
python3 <<PYEOF
with open("$HEARTBEAT_FILE", 'r') as f:
    content = f.read()

old = '''            if (issue.executionRunId === run.id) {
                await tx
                    .update(issues)
                    .set({
                    executionRunId: null,
                    executionAgentNameKey: null,
                    executionLockedAt: null,
                    updatedAt: new Date(),
                })
                    .where(eq(issues.id, issue.id));
            }
            while (true) {'''

new = '''            if (issue.executionRunId === run.id) {
                await tx
                    .update(issues)
                    .set({
                    executionRunId: null,
                    executionAgentNameKey: null,
                    executionLockedAt: null,
                    updatedAt: new Date(),
                })
                    .where(eq(issues.id, issue.id));
            }
            // Fix: self-close routine execution issues when the run succeeds
            if (run.status === 'succeeded' && issue.originKind === 'routine_execution' && issue.status !== 'done' && issue.status !== 'cancelled') {
                await issuesSvc.update(issue.id, { status: 'done' }, tx);
            }
            while (true) {'''

if old in content:
    content = content.replace(old, new, 1)
    with open("$HEARTBEAT_FILE", 'w') as f:
        f.write(content)
    print("Fix applied successfully")
else:
    print("Could not find the exact text to replace - server version may have changed")
PYEOF

echo ""
echo "Done. The fix is now active for subsequent routine runs."
