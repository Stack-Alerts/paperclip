# RECHECK ON DELAYED BARS - DESIGN SPECIFICATION

**Document Type:** UI/UX Design Specification  
**Feature:** Recheck On Delayed Bars  
**Priority:** High  
**Status:** Design  
**Last Updated:** 2026-01-19  

## 1. FEATURE OVERVIEW

### 1.1 Purpose

The "Recheck On Delayed Bars" feature adds signal validation capabilities to building blocks by creating a dependency that requires the same signal type to occur twice within a specified timeframe (number of bars). This enhances strategy creation by allowing for confirmation patterns that reduce false positives.

### 1.2 Business Value

- **Improved Signal Quality:** Reduces false positives by requiring signal confirmation
- **Enhanced Strategy Flexibility:** Allows traders to create more sophisticated validation rules
- **Institutional-Grade Verification:** Implements proper confirmation methodologies required in professional trading environments
- **Risk Reduction:** Decreases the likelihood of entering trades based on isolated, potentially misleading signals

### 1.3 User Story

As a trader, I want to ensure that a signal is valid only if it recurs within a specified number of bars, so that I can reduce false positives and create more reliable trading strategies.

## 2. UI DESIGN SPECIFICATION

### 2.1 Component Location

The "Recheck On Delayed Bars" button will be positioned as follows:

- **Parent Container:** Signal item in building block configuration panel
- **Position:** Right-aligned within the signal item row
- **Visibility:** Always visible for all signal types

### 2.2 Visual Design

#### 2.2.1 Button Design

Following the UI styling guidelines from `src/strategy_builder/ui/styles.py`:

- **Text:** "Recheck On Delayed Candles"
- **Styling:** Uses `BUTTON_SECONDARY_STYLE` from central stylesheet
- **Size:** Standard button height (BUTTON_HEIGHT constant)
- **Spacing:** Right margin of SPACING_UNIT * 2

#### 2.2.2 Activated State

When activated, the feature creates an indented child signal beneath the original:

- **Indentation:** SPACING_UNIT * 3 from left edge
- **Format:** "-----> SIGNAL_NAME [RECHECK] in __ Bars"
- **Input Field:** Numeric input field for bar count (mandatory)
- **Remove Button:** Standard remove button (RED_BUTTON_STYLE) aligned right

### 2.3 Interaction Flow

1. **Initial State:** Signal displayed with "Recheck On Delayed Bars" button
2. **Activation:** User clicks button
3. **Creation:** System creates indented child signal with placeholder for bar count
4. **Configuration:** User enters number of bars for validation
5. **Validation:** System ensures numeric value is provided (required field)
6. **Removal:** User can click "Remove" button to cancel the recheck configuration

## 3. NAUTILUS INTEGRATION APPROACH

### 3.1 Signal Processing Model

The Recheck feature will leverage NautilusTrader's event processing system by:

1. **Event Registration:** Register original signal detection events
2. **History Tracking:** Maintain a rolling window of recent signals based on maximum specified delay 
3. **Validation Logic:** When signal fires, check if previous instance occurred within specified bar count
4. **Decision Engine:** Only trigger strategy actions when validation criteria met

### 3.2 Technical Implementation

```python
# Implementation will utilize NautilusTrader's recommended patterns:
from nautilus_trader.model.data import BarType
from nautilus_trader.model.events import Event
from nautilus_trader.core.correctness import PyCondition

class SignalRecheckConfig:
    """
    Configuration for recheck validation on delayed bars.
    """
    def __init__(
        self,
        signal_type: str,
        bar_delay: int,
    ):
        PyCondition.positive_int(bar_delay, "bar_delay")
        self.signal_type = signal_type
        self.bar_delay = bar_delay
```

### 3.3 Performance Considerations

- **Memory Usage:** Efficient rolling window implementation to minimize memory footprint
- **Processing Overhead:** Minimal additional computation required
- **Backtest Compatibility:** Full support for backtesting with delayed validation
- **Real-Time Support:** Designed for both real-time and historical data processing

## 4. VALIDATION LOGIC

### 4.1 Signal Validation Process

The validation logic follows this sequence:

1. Original signal is detected according to its standard rules
2. If recheck is configured, the signal is temporarily stored with timestamp and bar index
3. On detection of second occurrence of same signal type:
   - Calculate bars elapsed since previous signal
   - If elapsed bars <= configured bar_delay:
     - Original signal is validated and triggers strategy actions
   - Else:
     - Reset and store new occurrence as potential first signal

### 4.2 Edge Cases

| Edge Case | Handling Approach |
|-----------|-------------------|
| Multiple occurrences within delay window | First occurrence is used as reference point |
| No recurrence within delay window | Signal is not validated and won't trigger actions |
| Bar delay set to 0 or negative | UI validation prevents this invalid input |
| Signal triggers at end of backtest period | Properly handled with partial validation window |

### 4.3 Pseudocode Algorithm

```
function processSignal(signal_type, current_bar_index):
    # Check if signal occurred before
    if signal_type in recent_signals:
        last_occurrence = recent_signals[signal_type]
        bars_elapsed = current_bar_index - last_occurrence.bar_index
        
        # Check if within configured delay window
        if bars_elapsed <= signal_recheck_config[signal_type].bar_delay:
            # Validation successful
            return SIGNAL_VALIDATED
        else:
            # Outside window, store current as new first occurrence
            recent_signals[signal_type] = SignalOccurrence(current_bar_index)
            return SIGNAL_PENDING_VALIDATION
    else:
        # First occurrence
        recent_signals[signal_type] = SignalOccurrence(current_bar_index)
        return SIGNAL_PENDING_VALIDATION
```

## 5. CONFIGURATION PERSISTENCE

### 5.1 Data Model Additions

The strategy configuration JSON will need to store recheck configurations:

```json
{
  "building_blocks": [
    {
      "id": "hod_rejection_block",
      "signals": [
        {
          "type": "HOD_REJECTION",
          "recheck_config": {
            "enabled": true,
            "bar_delay": 25
          }
        }
      ]
    }
  ]
}
```

### 5.2 Migration Considerations

- Existing strategies without recheck configurations will continue to function normally
- Default state for all signals will be recheck disabled (`"enabled": false`)
- Configuration UI will properly handle loading strategies created before this feature

## 6. VISUAL IMPLEMENTATION DETAILS

### 6.1 Style References

All UI components will follow the centralized style guidelines from `src/strategy_builder/ui/styles.py`:

```python
# Button styling (referenced, not duplicated)
from src.strategy_builder.ui.styles import (
    BUTTON_SECONDARY_STYLE,
    RED_BUTTON_STYLE,
    SPACING_UNIT,
    TEXT_FIELD_STYLE,
    FONT_SIZE_BASE,
    PRIMARY_COLOR,
    SIGNAL_ITEM_STYLE
)
```

### 6.2 Layout Specifications

Signal item with recheck button:
```
[Signal Name (e.g. "HOD_REJECTION [AND]")] ..................... [Recheck On Delayed Candles]
```

Activated recheck configuration:
```
[Signal Name (e.g. "HOD_REJECTION [AND]")] ..................... [Recheck On Delayed Candles]
[----> HOD_REJECTION [RECHECK] in [25] Bars] ................... [Remove]
```

## 7. IMPLEMENTATION TASK LIST

### 7.1 UI Components

- [ ] Add "Recheck On Delayed Bars" button to signal items
- [ ] Create indented child signal component with input field
- [ ] Implement validation for numeric bar count input
- [ ] Add remove functionality to cancel recheck configuration
- [ ] Update styling to match design specifications

### 7.2 Core Logic

- [ ] Implement SignalRecheckConfig class
- [ ] Create rolling window mechanism for signal tracking
- [ ] Develop validation logic for signal confirmation
- [ ] Integrate with existing signal processing pipeline
- [ ] Update strategy execution to respect recheck validation

### 7.3 Configuration Management

- [ ] Extend strategy configuration data model
- [ ] Update serialization/deserialization logic
- [ ] Ensure backward compatibility with existing strategies
- [ ] Implement proper configuration validation

### 7.4 Testing

- [ ] Unit tests for recheck validation logic
- [ ] Integration tests with full strategy execution
- [ ] UI component tests for proper interaction
- [ ] Backward compatibility tests with existing strategies
- [ ] Performance benchmarks for memory and processing overhead

## 8. NAUTILUS TRADER CONSIDERATIONS

### 8.1 Alignment with NautilusTrader Architecture

The implementation will follow NautilusTrader best practices:

- Using appropriate types (Quantity, Price, Money) instead of primitives
- Properly handling events through the event system
- Maintaining immutability where appropriate
- Using enums instead of string literals
- Following NautilusTrader's risk management protocols

### 8.2 Code Organization

New components will be organized as follows:

```
src/
  strategy_builder/
    ui/
      components/
        signal_recheck_button.py  # Button component
        signal_recheck_config.py  # Configuration UI
    models/
      signal_recheck.py  # Core logic implementation
    validators/
      signal_validation.py  # Extended with recheck logic
```

## 9. CONCLUSION

The "Recheck On Delayed Bars" feature enhances the BTC Engine's signal validation capabilities by allowing traders to require confirmation of signals within a specified timeframe. This institutional-grade approach to signal validation aligns with professional trading practices and will reduce false positives in trading strategies.

Implementation follows all UI styling guidelines with central stylesheet enforcement, and properly integrates with the NautilusTrader framework for robust, type-safe trading operations.
