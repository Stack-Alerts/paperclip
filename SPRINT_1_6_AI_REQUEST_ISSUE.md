# Sprint 1.6 - AI Request Issue Investigation

**Date**: 2026-01-23  
**Status**: 🔴 CRITICAL ISSUE IDENTIFIED  
**Investigator**: Cline (NAUTILUS EXPERT)

---

## Problem Statement

The **Preview AI Request** window shows the comprehensive institutional-grade prompt with complete JSON data sections (strategy config, backtest config, trade results, metrics, available blocks), BUT the actual API request sent to OpenRouter uses a different, much simpler prompt format.

### Evidence from Logs

**Log File**: `logs/ai_recommendations.log` (line containing `OPENROUTER_REQUEST_SENT`)

```
'prompt_length': 4574
'prompt_preview': 'You are an elite quantitative trading strategist...'
```

**Expected**: ~50,000+ characters with complete JSON sections  
**Actual**: 4,574 characters with simple text format

---

## Root Cause Analysis

### Architecture Flow

```
1. Backtest completes
   ↓
2. MetricsDisplayPanel._show_ai_request_preview()
   ↓
3. ComprehensiveAIRequestBuilder.build_complete_request()  ← BUILDS COMPREHENSIVE REQUEST
   ↓
4. AIRequestPreviewWindow displays preview  ← USER SEES COMPREHENSIVE FORMAT
   ↓
5. User clicks "Approve & Send"
   ↓
6. _on_ai_request_approved() → _generate_batch_recommendations()
   ↓
7. intelligent_recommendation_engine.generate_recommendations()
   ↓
8. ai_enhancer.enhance_recommendations()
   ↓
9. ai_enhancer._build_analysis_prompt()  ← **USES OLD SIMPLE FORMAT**
   ↓
10. OpenRouter API receives OLD PROMPT (not the comprehensive one)
```

### The Disconnect

**File**: `src/optimizer_v3/core/ai_recommendation_enhancer.py`  
**Method**: `_build_analysis_prompt()` (starts at line ~165)

This method builds its OWN prompt from scratch using simple string formatting:

```python
prompt = f"""You are an elite quantitative trading strategist...

CURRENT STRATEGY CONFIGURATION:
================================
Name: {strategy_config.get('name', 'Unknown')}
Type: {strategy_config.get('strategy_type', 'Unknown')}
Blocks: {', '.join([b.get('name', '') for b in strategy_config.get('blocks', [])])}
...
"""
```

**This is NOT using `ComprehensiveAIRequestBuilder.format_for_ai_prompt()`!**

---

## What's Missing

The OLD prompt format (`_build_analysis_prompt`) is missing:

1. ❌ **Complete Strategy Configuration with Signal Details**
   - Missing: Signal-level parameters, recheck configs, timing constraints
   - Shows: Only block names and total signal count

2. ❌ **Complete Backtest Configuration**
   - Missing: Adaptive SL settings, risk management rules, position sizing
   - Shows: Only basic summary metrics

3. ❌ **Individual Trade Results**
   - Missing: All 24 trade details with entry/exit times, PnL, exit reasons
   - Shows: Only summary stats (total PnL, win rate, etc.)

4. ❌ **Complete Metrics with Institutional Ratings**
   - Missing: Threshold values, rating explanations, category classifications
   - Shows: Only raw metric values

5. ❌ **Complete Available Blocks Catalog**
   - Missing: All 83 blocks with 478 signals and descriptions
   - Shows: None

6. ❌ **Structured JSON Format**
   - Missing: Parseable JSON sections for each data category
   - Shows: Plain text summary format

---

## The Fix (Required)

### Option 1: Replace `_build_analysis_prompt()` (RECOMMENDED)

**File**: `src/optimizer_v3/core/ai_recommendation_enhancer.py`

**Change**: Make `_build_analysis_prompt()` use the `ComprehensiveAIRequestBuilder`:

```python
def _build_analysis_prompt(
    self,
    strategy_config: Dict,
    backtest_results: Dict,
    analysis_report,
    preliminary_recommendations: List
) -> str:
    """Build comprehensive prompt using ComprehensiveAIRequestBuilder"""
    
    # Import builder
    from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder
    
    # Build complete request
    builder = ComprehensiveAIRequestBuilder()
    
    # Prepare metrics with ratings
    metrics_with_ratings = self._extract_metrics_with_ratings(backtest_results, analysis_report)
    
    # Build comprehensive request
    request = builder.build_complete_request(
        strategy_config=strategy_config,
        backtest_results=backtest_results,  # Must include 'trades' list!
        metrics_with_ratings=metrics_with_ratings,
        backtest_config=backtest_results.get('config', {}),  # Extract config if available
        analysis_report=analysis_report
    )
    
    # Format as AI prompt
    prompt = builder.format_for_ai_prompt(request)
    
    return prompt
```

### Option 2: Pass Preview Data Through

Alternative: Pass the preview window's request data directly to the AI enhancer.

**Pros**: Guarantees same data in preview and actual request  
**Cons**: Requires signature changes through multiple layers

---

## Impact Assessment

**Current State**:
- ❌ AI receives incomplete context
- ❌ AI cannot see trade-level patterns
- ❌ AI doesn't know which blocks are available
- ❌ AI can't provide specific block/signal recommendations
- ❌ Preview window misleading (shows data AI won't receive)

**After Fix**:
- ✅ AI receives ALL strategy configuration details
- ✅ AI sees complete trade history with patterns
- ✅ AI knows all 478 available signals
- ✅ AI can recommend specific blocks from catalog
- ✅ Preview window accurate (shows actual AI request)

---

## Testing Required

1. **Verify Prompt Length**: Should be 50,000+ characters (not 4,574)
2. **Verify JSON Sections**: Log should show all 6 sections
3. **Verify Trade Count**: Should show all 24 trades (not "Number of Trades: 0")
4. **Verify Available Blocks**: Should show 83 blocks with 478 signals
5. **Verify AI Response Quality**: Recommendations should be more specific

---

## Priority: 🔴 CRITICAL

**Reason**: The entire AI recommendation system is based on comprehensive data analysis, but the AI is receiving only summary statistics. This defeats the purpose of Sprint 1.6's institutional-grade AI enhancement.

**Recommendation**: Implement Option 1 (replace `_build_analysis_prompt()`) as soon as possible.

---

## Files Affected

- [x] **Investigation Complete**
- [ ] `src/optimizer_v3/core/ai_recommendation_enhancer.py` (needs fix)
- [ ] Test file: `test_ai_full_request.py` (needs creation)
- [ ] Verify in logs: `logs/ai_recommendations.log`

---

## Workaround (Temporary)

Until fixed, users should be aware that:
- Preview window shows IDEAL request format
- Actual AI receives simplified format
- AI recommendations based on limited context
- Manual review of AI recommendations essential

---

**End of Investigation Report**
