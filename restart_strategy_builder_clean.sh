#!/bin/bash
# Complete clean restart of Strategy Builder
# Kills processes, clears cache, and restarts fresh

echo "🔄 Restarting Strategy Builder (clean)..."

# 1. Kill any running Strategy Builder processes
echo "1️⃣ Killing existing processes..."
pkill -f "strategy_builder" 2>/dev/null
pkill -f "launch_strategy_builder" 2>/dev/null
sleep 1

# 2. Clear Python cache
echo "2️⃣ Clearing Python __pycache__..."
find ~/projects/BTC_Engine_v3 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find ~/projects/BTC_Engine_v3 -name "*.pyc" -delete 2>/dev/null

# 3. Navigate to project
cd ~/projects/BTC_Engine_v3

# 4. Launch fresh
echo "3️⃣ Launching Strategy Builder..."
python scripts/launch_strategy_builder.py

echo "✅ Done!"
