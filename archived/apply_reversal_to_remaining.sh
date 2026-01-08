#!/bin/bash
# Apply reversal logic to LOW and US Settlement

echo "================================================================"
echo "APPLYING REVERSAL LOGIC TO LOW AND US SETTLEMENT"
echo "================================================================"

# LOW - Support level (bullish reversals like LOD)
echo ""
echo "1. Applying to LOW (Low of Week - support)..."
cp src/detectors/building_blocks/price_levels/low.py src/detectors/building_blocks/price_levels/low.py.bak

# Replace old tracking with reversal tracking in LOW
sed -i 's/self\.confirmation_candles = 2  # Require 2 consecutive bars (more realistic)/self.reversal_candles = 5  # Monitor 5 candles after test for reversal pattern/' src/detectors/building_blocks/price_levels/low.py
sed -i 's/self\.bounce_test_bars = \[\]  # Track bars testing support/self.last_low_test_bar = None  # Bar that tested LOW/' src/detectors/building_blocks/price_levels/low.py
sed -i 's/self\.breakdown_bars = \[\]  # Track bars breaking below/self.bars_since_test = []  # Track bars after LOW test for reversal detection/' src/detectors/building_blocks/price_levels/low.py

echo "   ✓ LOW variables updated"

# US Settlement - Can act as both support and resistance
echo ""
echo "2. Applying to US Settlement (institutional level)..."
cp src/detectors/building_blocks/price_levels/us_settlement.py src/detectors/building_blocks/price_levels/us_settlement.py.bak

sed -i 's/self\.confirmation_candles = 2  # Require 2 consecutive bars/self.reversal_candles = 5  # Monitor 5 candles after test for reversal pattern/' src/detectors/building_blocks/price_levels/us_settlement.py
sed -i 's/self\.rejection_test_bars = \[\]  # Track bars testing resistance/self.last_settlement_test_bar = None  # Bar that tested settlement/' src/detectors/building_blocks/price_levels/us_settlement.py
sed -i 's/self\.breakthrough_bars = \[\]  # Track bars breaking above/self.bars_since_test = []  # Track bars after settlement test/' src/detectors/building_blocks/price_levels/us_settlement.py

echo "   ✓ US Settlement variables updated"

echo ""
echo "================================================================"
echo "NOTE: Manual reversal logic still needs to be applied"
echo "Variables updated, but full reversal detection code needs copying"
echo "from HOD/LOD blocks. Due to complexity, will apply manually."
echo "================================================================"

