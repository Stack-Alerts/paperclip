# Child Task for StrategyResearcher

**Parent**: BTCAAAAA-2173
**Priority**: Critical
**Assigned to**: StrategyResearcher (e3fcab65-c9a3-45bd-97e8-5145d3d6db5e)

## Objective

Evaluate and address HOD Rejection (v11) viability issues identified in EXPERT_MODE 5-report.

## Findings

### HOD Rejection (v11) — Critical Issues

1. **Only 4 trades across all configurations**: 
   - All 5 optimizer configs (135, 136, 183, 184, 189) produce exactly 4 trades each
   - On BTC 15min data over ~4 months, this is ~1 trade/month
   - This is not a viable intraday trading frequency
   - Statistically meaningless sample (N=4)

2. **All configs produce identical results**:
   - Every metric is identical across all 5 configurations
   - Net PnL: $660.64, Sharpe: 5.10, Max DD: 2.05%, Win Rate: 50%
   - This indicates either parameter insensitivity (the config changes don't matter) or a calculation bug

3. **Fee burden**: $1,253.42 in fees vs $1,914.05 gross PnL = **65% fee-to-gross ratio**
   - Net PnL: only $660.64 (35% of gross)
   - This makes the strategy economically questionable at current trade frequency

4. **Sharpe 5.10 on 4 trades**: Mathematical artifact, not meaningful

5. **Max DD 2.05%**: Unrealistically low for BTC short selling

### 50% Asia Rejection Simple (v27) — Secondary Issue

- **Bearish-only**: Zero long-side entries across all trades
- Consider adding long-side signals to capture both market directions

## Deliverables

### Option A: Redesign HOD Rejection
- Increase trade frequency to minimum 50+ trades per backtest period
- Address the duplicate/redundant config issue
- Consider whether HOD Rejection signal logic is fundamentally viable
- Add long-side signal support

### Option B: Retire HOD Rejection
- If the strategy cannot produce viable trade frequency after redesign
- Document retirement decision with rationale

## Verification

After redesign:
- [ ] Minimum 50 trades per backtest run
- [ ] Config variations produce distinguishable results
- [ ] Fee-to-gross ratio < 30%
- [ ] Sharpe < 3.0
- [ ] Max DD > 10%

## Next Owner

After completion, route back to BacktestAnalyst (79beb038) for EXPERT_MODE re-assessment.
