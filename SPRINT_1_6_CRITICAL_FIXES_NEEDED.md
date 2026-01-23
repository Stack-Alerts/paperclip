# Sprint 1.6 - CRITICAL FIXES NEEDED

## Issues Identified (User Feedback)

### ❌ CRITICAL Issue #1: UI Freezes During AI Query
**Problem**: When AI generates recommendations, entire UI freezes for 30-40 seconds
**Root Cause**: `_generate_batch_recommendations()` runs on MAIN THREAD
**Location**: `src/optimizer_v3/ui/metrics_display_panel.py` line 1055
**Impact**: UNACCEPTABLE user experience - Python appears frozen

**Required Fix**:
```python
# Create QThread worker for AI generation
class RecommendationWorker(QThread):
    recommendations_ready = pyqtSignal(list)
    
    def __init__(self, engine, strategy_config, metrics, backtest_results):
        super().__init__()
        self.engine = engine
        self.strategy_config = strategy_config
        self.metrics = metrics
        self.backtest_results = backtest_results
    
    def run(self):
        # Run AI in background
        recommendations = self.engine.generate_recommendations(
            strategy_config=self.strategy_config,
            backtest_results=self.backtest_results,
            metrics=self.metrics,
            lookback_days=180
        )
        self.recommendations_ready.emit(recommendations)

# In update_metrics():
if backtest_complete:
    self.worker = RecommendationWorker(...)
    self.worker.recommendations_ready.connect(self._on_recommendations_ready)
    self.worker.start()
    # Show loading indicator
```

### ❌ Issue #2: No Checkboxes Visible
**Problem**: AI recommendations appear but checkboxes don't show
**Root Cause**: `_is_intelligent_recommendation()` logic  broken
**Location**: Line 734 in `metrics_display_panel.py`
**Current Logic**: Checks if text starts with "Add '" (wrong!)

**Required Fix**:
```python
def _is_intelligent_recommendation(self, rec_text: str) -> bool:
    """Check if recommendation is intelligent vs generic"""
    # AI recommendations contain "AI-ENHANCED:" prefix
    return "AI-ENHANCED:" in rec_text or "Add '" in rec_text
```

### ❌ Issue #3: Recommendations Not Detailed
**Problem**: Showing "🤖 AI-ENHANCED: Adjust parameter..." instead of full text
**Root Cause**: `format_recommendation_text()` truncates output
**Location**: `intelligent_recommendation_engine.py` line
