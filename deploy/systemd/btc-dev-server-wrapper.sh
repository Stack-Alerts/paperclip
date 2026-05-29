#!/bin/bash
# btc-dev-server-wrapper.sh — systemd exec wrapper for btc-dev-server.service
#
# This is the actual launcher called by the systemd unit.
# Users should interact with ./start-dev.sh (in the repo root) for manual launch.
# See: BTCAAAAA-31132 for the split between start-dev.sh and start-test.sh.

set -e
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip/packages/web-ui
exec /home/sirrus/.nvm/versions/node/v20.20.2/bin/npm run dev -- -p 3010
