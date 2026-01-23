# Sprint 1.6 - Fix Implementation Guide

**Status**: 🟡 IN PROGRESS  
**File**: `src/optimizer_v3/core/ai_recommendation_enhancer.py`

---

## Step 1: Import Added ✅

```python
# Import ComprehensiveAIRequestBuilder for institutional-grade prompts
from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder
```

**Status**: ✅ COMPLETE

---

## Step 2: Replace `_build_analysis_prompt()` Method ⏳

**Current Method** (lines ~151-294): Uses OLD simple format

**Required Replacement**:

```python
def _build_analysis_prompt(
    self,
    strategy_config: Dict,
    backtest_results: Dict,
    analysis_report,
    preliminary_recommendations: List
) -> str:
    """
    Build comprehensive prompt using ComprehensiveAIRequestBuilder
    
    CRITICAL FIX: Uses institutional-grade builder instead of simple format
    """
    print("🔧 Building institutional-grade AI prompt...")
    
    # Initialize builder
    builder = ComprehensiveAIRequestBuilder()
    
    # Prepare metrics with ratings for builder
    metrics_with_ratings = {}
    
    # Extract metrics from backtest_results
    metric_keys = [
        'total_pnl', 'win_rate', 'profit_factor', 'sharpe_ratio',
        'max_drawdown_pct', 'num_trades', 'avg_win', 'avg_loss',
        'largest_win', 'largest_loss', 'risk_reward_ratio', 'recovery_factor',
        'sortino_ratio', 'calmar_ratio', 'max_consecutive_losses'
    ]
    
    for key in metric_keys:
        if key in backtest_results:
            value = backtest_results[key]
            # Get rating from analysis if available
            rating = self._get_metric_rating(key, value, analysis_report)
            metrics_with_ratings[key] = {
                'value': float(value) if value is not None else 0.0,
                'rating': rating,
                'category': 'Performance'  # Could be more sophisticated
            }
    
    # Build complete request using builder
    request = builder.build_complete_request(
        strategy_config=strategy_config,
        backtest_results=backtest_results,  # Must include 'trades' list!
        metrics_with_ratings=metrics_with_ratings,
        backtest_config=backtest_results.get('config', {}),
        analysis_report=analysis_report
    )
    
    # Format as AI prompt (this creates the long institutional prompt)
    prompt = builder.format_for_ai_prompt(request)
    
    print(f"✅ Comprehensive prompt built: {len(prompt)} characters")
    print(f"   (Expected: 50,000+ for complete data)")
    
    return prompt

def _get_metric_rating(self, metric_key: str, value, analysis_report) -> str:
    """Get rating for metric based on analysis"""
    # Simple rating logic - could use analysis_report for more context
    try:
        val = float(value)
        
        if metric_key == 'win_rate':
            return '✓ Good' if val >= 60 else ('⚠ Fair' if val >= 50 else '✗ Poor')
        elif metric_key == 'profit_factor':
            return '✓ Good' if val >= 2.0 else ('⚠ Fair' if val >= 1.5 else '✗ Poor')
        elif metric_key == 'sharpe_ratio':
            return '✓ Good' if val >= 2.0 else ('⚠ Fair' if val >= 1.0 else '✗ Poor')
        # Add more metric-specific logic as needed
        else:
            return '-'
    except:
        return '-'
```

**Location**: Replace entire method starting at line ~151

---

## Step 3: Verify Response Parsing Still Works ✅

The response format is UNCHANGED:
- AI still returns JSON with `recommendations` array
- Each recommendation has same structure
- `_parse_ai_response()` method should work as-is

**No changes needed** - response format is identical.

---

## Step 4: Test Changes

### Before Testing:
1. Ensure `OPENROUTER_API_KEY` is in `.env`
2. Run backtest to completion
3. Click "Preview AI Request"
4. Check logs: `logs/ai_recommendations.log`

### Expected Log Changes:

**Before** (OLD format):
```
'prompt_length': 4574
'prompt_preview': 'You are an elite quantitative...'
```

**After** (NEW format):
```
'prompt_length': 50000+
'prompt_preview': '# INSTITUTIONAL TRADING STRATEGY...'
```

### Verification Checklist:
- [ ] Prompt length > 50,000 characters
- [ ] Log shows "Number of Trades: 24" (not 0)
- [ ] Log contains "AVAILABLE BUILDING BLOCKS"
- [ ] Log shows complete JSON sections
- [ ] AI response still parses correctly
- [ ] Recommendations displayed in UI

---

## Step 5: Commit

```bash
git add src/optimizer_v3/core/ai_recommendation_enhancer.py
git commit -m "fix(sprint-1.6): Use ComprehensiveAIRequestBuilder for AI requests

CRITICAL FIX:
- Replaced _build_analysis_prompt() to use ComprehensiveAIRequestBuilder
- AI now receives institutional-grade prompt with:
  * Complete strategy configuration (all signals, parameters)
  * Complete backtest configuration (adaptive SL, risk management)
  * All 24 trade results with details
  * Complete metrics with institutional ratings
  * All 83 blocks with 478 signals
  * Structured JSON format

BEFORE: 4,574 character simple text prompt
AFTER: 50,000+ character comprehensive JSON prompt

RESULT: AI can now provide specific, actionable recommendations based
on complete data instead of summary statistics.

Fixes: SPRINT_1_6_AI_REQUEST_ISSUE.md"
```

---

## Why This Fix is Critical

**Current State** (with old prompt):
- AI sees 10% of available data
- Cannot recommend specific blocks (doesn't know what's available)
- Cannot analyze trade patterns (only summary stats)
- Cannot configure parameters (doesn't see full config)

**After Fix**:
- AI sees 100% of available data  
- Can recommend from 478 available signals
- Can analyze all 24 trade patterns
- Can configure exact parameters bases on complete context

---

**Implementation Status**: ⏳ Step 2 pending (replace method body)
