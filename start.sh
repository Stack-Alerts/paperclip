#!/usr/bin/env bash
# start.sh (DEPRECATED) — use ./start-dev.sh or ./start-test.sh instead
#
# This launcher has been split into two clear, distinct entry points:
#
#   ./start-dev.sh                 ← RECOMMENDED: supervised, production-like
#      • Runs on :3010 (matches btc-dev-server.service)
#      • Inherits systemd gating, health surveillance, restart policy
#      • Best for: the board, QA, running against supervised infrastructure
#
#   ./start-test.sh [--branch X]   ← ephemeral testing
#      • Runs on :3000 (separate, sandboxed)
#      • Not under systemd; no persistent state
#      • Best for: quick branch-specific iteration, ad-hoc testing
#
# See AGENTS.md and the issue BTCAAAAA-31132 for background.

set -euo pipefail

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  DEPRECATION NOTICE                        ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  ./start.sh is deprecated and has been split into:         ║"
echo "║                                                            ║"
echo "║  1. ./start-dev.sh                                         ║"
echo "║     Supervised, production-like dev server on :3010        ║"
echo "║     Inherits systemd health checks and branch gating       ║"
echo "║     → RECOMMENDED for the board and QA                     ║"
echo "║                                                            ║"
echo "║  2. ./start-test.sh [--branch <name>]                      ║"
echo "║     Ephemeral, sandboxed test instance on :3000            ║"
echo "║     For quick iteration and branch-specific testing        ║"
echo "║                                                            ║"
echo "║  See AGENTS.md and BTCAAAAA-31132 for details.             ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

exit 1
