# Quick Resume Guide - Building Blocks Construction

**Purpose:** Use this to quickly resume work after context window reset

---

## CURRENT STATUS

**Last Updated:** 2025-12-31 09:43 UTC  
**Blocks Completed:** 0/66  
**Current Block:** None (awaiting start)

---

## QUICK START COMMANDS

### To Resume Work:
1. Read tracker: `docs/v3/building_blocks/BLOCK_BUILD_TRACKER.md`
2. Read master spec: `docs/v3/building_blocks/0_Building_Blocks_Master.md`
3. Check current block status in tracker
4. Continue with next step in workflow

### Construction Workflow (for each block):
```
1. Create implementation file
2. Create unit test file  
3. Run tests: pytest tests/building_blocks/test_[block_name].py -v
4. EXPERT MODE validation
5. Tune parameters
6. Document results
7. Update tracker
8. Move to next block
```

---

## FILE STRUCTURE

```
src/detectors/building_blocks/
├── moving_averages/
│   ├── ema_50_vector_break.py
│   ├── ema_200_vector_break.py
│   ├── ema_55_vector_break.py
│   ├── ema_255_vector_break.py
│   ├── ema_800_vector_break.py
│   └── ema_crossover.py
├── oscillators/
│   ├── macd_signal.py
│   ├── rsi_divergence.py
│   └── stochastic_rsi_cross.py
├── price_levels/
│   ├── hod.py
│   ├── lod.py
│   ├── how.py
│   ├── low.py
│   ├── us_settlement.py
│   └── asia_session_50_percent.py
├── sessions/
│   ├── session_time.py
│   └── kill_zones.py
├── volatility/
│   ├── atr.py
│   ├── adr.py
│   └── bollinger_bands.py
├── price_action/
│   ├── order_block.py
│   ├── fair_value_gap.py
│   ├── volume_profile.py
│   └── pivot_points.py
├── smc/
│   ├── liquidity_sweep.py
│   ├── breaker_block.py
│   ├── optimal_trade_entry.py
│   ├── market_structure_shift.py
│   ├── break_of_structure.py
│   ├── change_of_character.py
│   ├── displacement.py
│   ├── liquidity_pool.py
│   ├── swing_points.py
│   └── premium_discount_zones.py
├── elliott/
│   ├── elliott_wave_count.py
│   └── elliott_wave_oscillator.py
├── wyckoff/
│   ├── accumulation_phase.py
│   ├── distribution_phase.py
│   └── reaccumulation_phase.py
├── market_structure/
│   └── range_liquidity.py
├── patterns/
│   ├── head_and_shoulders.py
│   ├── inverse_head_and_shoulders.py
│   ├── double_top.py
│   ├── double_bottom.py
│   ├── triple_top.py
│   ├── triple_bottom.py
│   ├── ascending_triangle.py
│   ├── descending_triangle.py
│   ├── symmetrical_triangle.py
│   ├── flag_pattern.py
│   ├── pennant_pattern.py
│   ├── wedge_patterns.py
│   ├── cup_and_handle.py
│   ├── rounding_bottom_top.py
│   └── diamond_pattern.py
├── institutional/
│   ├── vwap.py
│   ├── anchored_vwap.py
│   ├── order_flow_imbalance.py
│   └── market_depth.py
├── supply_demand/
│   └── supply_demand_zones.py
├── fibonacci/
│   └── fibonacci_retracements.py
├── harmonic/
│   └── harmonic_patterns.py
└── trend/
    ├── adx.py
    └── ichimoku_cloud.py

tests/building_blocks/
├── test_ema_50_vector_break.py
├── test_ema_200_vector_break.py
... (mirrors src structure)
```

---

## STANDARD BLOCK TEMPLATE

```python
"""
[Block Name] Building Block
Category: [Category Name]
Purpose: [Brief description]
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class [BlockName]:
    """
    [Detailed description]
    
    Parameters:
        param1: Description
        param2: Description
    
    Returns:
        Standardized dict with signal, confidence, metadata
    """
    
    def __init__(self, **kwargs):
        """Initialize block with parameters"""
        self.param1 = kwargs.get('param1', default_value)
        self.param2 = kwargs.get('param2', default_value)
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters
        
        Returns:
            {
                'signal': str,  # Main signal output
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # Additional context
                'timestamp': datetime,
                'timeframe': str,
                'confluence_factors': list
            }
        """
        # Implementation here
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate input data"""
        required_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        return all(col in df.columns for col in required_cols)


# Usage example
if __name__ == "__main__":
    # Test with sample data
    pass
```

---

## STANDARD TEST TEMPLATE

```python
"""
Unit tests for [Block Name]
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.detectors.building_blocks.[category].[block_file] import [BlockClass]


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    data = {
        'timestamp': dates,
        'open': np.random.uniform(40000, 45000, 100),
        'high': np.random.uniform(40000, 45000, 100),
        'low': np.random.uniform(40000, 45000, 100),
        'close': np.random.uniform(40000, 45000, 100),
        'volume': np.random.uniform(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    return df


class Test[BlockName]:
    """Test suite for [BlockName] block"""
    
    def test_initialization(self):
        """Test block can be instantiated"""
        block = [BlockClass]()
        assert block is not None
    
    def test_analyze_returns_standardized_format(self, sample_data):
        """Test analyze returns standard format"""
        block = [BlockClass]()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert 'timestamp' in result
        assert 'timeframe' in result
        assert isinstance(result['confidence'], (int, float))
        assert 0 <= result['confidence'] <= 100
    
    def test_data_validation(self, sample_data):
        """Test data validation works"""
        block = [BlockClass]()
        assert block.validate_data(sample_data) == True
    
    def test_invalid_data_handling(self):
        """Test handling of invalid data"""
        block = [BlockClass]()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        assert block.validate_data(invalid_df) == False
    
    # Add specific tests for block logic
    def test_specific_scenario_1(self, sample_data):
        """Test specific scenario"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
```

---

## EXPERT MODE VALIDATION TEMPLATE

When completing a block, use this EXPERT MODE prompt:

```
EXPERT MODE: Validate [Block Name] building block

I've implemented the [Block Name] building block. Please provide institutional-grade validation:

1. CODE QUALITY VERIFICATION
   - Is the logic correct per the specification?
   - Are all edge cases handled?
   - Is the code institutional-grade (no shortcuts)?
   
2. OUTPUT VALIDATION
   - Does it return standardized format?
   - Are confidence scores reasonable?
   - Is metadata complete and useful?
   
3. BITCOIN-SPECIFIC OPTIMIZATION
   - Are BTC market characteristics considered?
   - Is it optimized for 24/7 crypto markets?
   - Does it handle Bitcoin volatility correctly?
   
4. TESTING ASSESSMENT
   - Are unit tests comprehensive?
   - Do tests cover edge cases?
   - Are test assertions meaningful?
   
5. TUNING RECOMMENDATIONS
   - What parameters need tuning?
   - What are optimal default values for Bitcoin?
   - Any suggested improvements?

Files to review:
- Implementation: src/detectors/building_blocks/[path]/[file].py
- Tests: tests/building_blocks/test_[file].py
```

---

## CRITICAL REMINDERS

⚠️ **THIS IS BLOCK BUILDING, NOT STRATEGY BUILDING**
- Build reusable, standardized components
- Each block is independently testable
- No strategy logic - only building blocks
- Blocks will be combined later for strategies

⚠️ **ONE BLOCK AT A TIME**
- Complete workflow for ONE block
- Test thoroughly
- Expert validate
- Tune parameters
- THEN move to next

⚠️ **INSTITUTIONAL GRADE ONLY**
- No approximations
- No shortcuts
- Full validation
- Comprehensive tests
- Real money is at risk

---

## PROGRESS TRACKING

Update tracker after EACH block completion:
1. Open: `docs/v3/building_blocks/BLOCK_BUILD_TRACKER.md`
2. Find block section
3. Update status to ✅ DONE
4. Add completion date
5. Add key notes/findings
6. Update progress summary
7. Save

---

## RESUMPTION CHECKLIST

When resuming after context reset:
- [ ] Read BLOCK_BUILD_TRACKER.md (check current status)
- [ ] Identify last completed block
- [ ] Identify next block to build
- [ ] Read block specification from 0_Building_Blocks_Master.md
- [ ] Follow workflow:
  - [ ] Create implementation
  - [ ] Create tests
  - [ ] Run tests
  - [ ] Expert validate
  - [ ] Tune
  - [ ] Document
  - [ ] Update tracker
  - [ ] Move to next

---

**Last Updated:** 2025-12-31  
**Next Review:** After each block completion
