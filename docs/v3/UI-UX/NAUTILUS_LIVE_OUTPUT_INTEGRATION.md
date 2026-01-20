# NAUTILUS LIVE OUTPUT INTEGRATION
**Integration of Live Output Streaming for Window 2 Tab 2**

## 📋 OVERVIEW

This document outlines how the Live Output streaming system is integrated with Window 2 Tab 2, ensuring real-time visibility of decisions and actions during test runs across all execution modes.

## 🔧 IMPLEMENTATION

### 1. Live Output Handler

```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import asyncio
import json

class OutputLevel(Enum):
    """Output message levels"""
    INFO = "info"
    DECISION = "decision"
    ACTION = "action"
    WARNING = "warning"
    ERROR = "error"

class OutputCategory(Enum):
    """Output message categories"""
    SIGNAL = "signal"
    TRADE = "trade"
    RISK = "risk"
    SYSTEM = "system"
    OPTIMIZER = "optimizer"

@dataclass
class LiveOutputMessage:
    """Live output message structure"""
    timestamp: datetime
    level: OutputLevel
    category: OutputCategory
    message: str
    details: dict
    source: str

class NautilusLiveOutput:
    """Handle live output streaming"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self._subscribers = []
        self._message_queue = asyncio.Queue()
        self._running = False
        self._processor_task = None
    
    async def start(self):
        """Start output processing"""
        if self._running:
            return
            
        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
    
    async def stop(self):
        """Stop output processing"""
        if not self._running:
            return
            
        self._running = False
        if self._processor_task:
            await self._processor_task
            self._processor_task = None
    
    def subscribe(self, callback):
        """Subscribe to output messages"""
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback):
        """Unsubscribe from output messages"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    async def send_message(self,
                          level: OutputLevel,
                          category: OutputCategory,
                          message: str,
                          details: dict = None,
                          source: str = None):
        """Send output message"""
        msg = LiveOutputMessage(
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=message,
            details=details or {},
            source=source or "system"
        )
        
        await self._message_queue.put(msg)
    
    async def _process_messages(self):
        """Process output messages"""
        while self._running:
            try:
                # Get message from queue
                msg = await self._message_queue.get()
                
                # Format message
                formatted = self._format_message(msg)
                
                # Send to subscribers
                for callback in self._subscribers:
                    try:
                        await callback(formatted)
                    except Exception as e:
                        self.logger.error(
                            f"Subscriber callback failed: {str(e)}"
                        )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Message processing failed: {str(e)}")
    
    def _format_message(self, msg: LiveOutputMessage) -> dict:
        """Format message for output"""
        return {
            'timestamp': msg.timestamp.isoformat(),
            'level': msg.level.value,
            'category': msg.category.value,
            'message': msg.message,
            'details': msg.details,
            'source': msg.source
        }

class NautilusLiveOutputUI:
    """Handle live output UI integration"""
    
    def __init__(self, output_handler: NautilusLiveOutput):
        self.output_handler = output_handler
        self._window = None
        self._text_widget = None
        self._filter_settings = {
            'levels': set(OutputLevel),
            'categories': set(OutputCategory)
        }
    
    def initialize_ui(self, window, text_widget):
        """Initialize UI components"""
        self._window = window
        self._text_widget = text_widget
        
        # Subscribe to output
        self.output_handler.subscribe(self._handle_message)
    
    def set_filters(self,
                   levels: List[OutputLevel] = None,
                   categories: List[OutputCategory] = None):
        """Set output filters"""
        if levels is not None:
            self._filter_settings['levels'] = set(levels)
        if categories is not None:
            self._filter_settings['categories'] = set(categories)
    
    async def _handle_message(self, message: dict):
        """Handle output message"""
        # Check filters
        if (OutputLevel(message['level']) not in self._filter_settings['levels'] or
            OutputCategory(message['category']) not in self._filter_settings['categories']):
            return
        
        # Format for display
        display_text = self._format_for_display(message)
        
        # Update UI
        await self._update_ui(display_text, message)
    
    def _format_for_display(self, message: dict) -> str:
        """Format message for display"""
        timestamp = datetime.fromisoformat(message['timestamp'])
        time_str = timestamp.strftime('%H:%M:%S.%f')[:-3]
        
        # Color coding based on level
        level_colors = {
            'info': 'black',
            'decision': 'blue',
            'action': 'green',
            'warning': 'orange',
            'error': 'red'
        }
        
        color = level_colors.get(message['level'], 'black')
        
        # Format details if present
        details_str = ''
        if message['details']:
            details_str = '\n  ' + json.dumps(message['details'], indent=2)
        
        return (
            f"[{time_str}] [{message['category'].upper()}] "
            f"<font color='{color}'>{message['message']}</font>"
            f"{details_str}\n"
        )
    
    async def _update_ui(self, display_text: str, raw_message: dict):
        """Update UI with message"""
        if not self._text_widget:
            return
            
        # Add text to widget
        self._text_widget.append(display_text)
        
        # Scroll to bottom
        scrollbar = self._text_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Update any related UI elements
        await self._update_related_ui(raw_message)
    
    async def _update_related_ui(self, message: dict):
        """Update related UI elements"""
        category = message['category']
        
        if category == 'trade':
            # Update trade-related displays
            await self._update_trade_displays(message['details'])
        elif category == 'signal':
            # Update signal-related displays
            await self._update_signal_displays(message['details'])
        elif category == 'risk':
            # Update risk-related displays
            await self._update_risk_displays(message['details'])
```

### 2. Integration with Execution Modes

```python
class NautilusExecutionHandler:
    """Handle different execution modes with live output"""
    
    def __init__(self,
                 logger: OptimizerLogger,
                 live_output: NautilusLiveOutput):
        self.logger = logger
        self.live_output = live_output
        self._mode = None
        self._config = None
        self._running = False
    
    async def _run_historical(self, engine: BacktestEngine):
        """Run historical backtest with live output"""
        max_bars = self._config['execution']['max_bars']
        bars_processed = 0
        
        await self.live_output.send_message(
            level=OutputLevel.INFO,
            category=OutputCategory.SYSTEM,
            message=f"Starting historical backtest",
            details={
                'max_bars': max_bars,
                'start_time': self._config['data_feed']['start_time'].isoformat(),
                'end_time': self._config['data_feed']['end_time'].isoformat()
            }
        )
        
        while bars_processed < max_bars and not self._stop_event.is_set():
            # Process next bar
            if await engine.process_next_bar():
                bars_processed += 1
                
                # Send progress update every 100 bars
                if bars_processed % 100 == 0:
                    await self.live_output.send_message(
                        level=OutputLevel.INFO,
                        category=OutputCategory.SYSTEM,
                        message=f"Processed {bars_processed} bars",
                        details={'progress': bars_processed / max_bars}
                    )
                
                # Handle pause if needed
                await self._handle_pause()
            else:
                break
    
    async def _run_live_replay(self, engine: LiveReplayEngine):
        """Run live replay with live output"""
        await self.live_output.send_message(
            level=OutputLevel.INFO,
            category=OutputCategory.SYSTEM,
            message="Starting live replay",
            details={
                'start_time': self._config['data_feed']['start_time'].isoformat(),
                'candle_interval': self._config['execution']['candle_interval']
            }
        )
        
        while not self._stop_event.is_set():
            # Wait for next candle
            if await engine.wait_for_candle():
                # Send candle received message
                await self.live_output.send_message(
                    level=OutputLevel.INFO,
                    category=OutputCategory.SYSTEM,
                    message="New candle received",
                    details={'time': datetime.now().isoformat()}
                )
                
                # Process the candle
                await engine.process_candle()
                
                # Handle pause if needed
                await self._handle_pause()
            else:
                # No more candles available
                await asyncio.sleep(1)
```

### 3. Signal and Trade Output

```python
class NautilusSignalOutput:
    """Handle signal-related output"""
    
    def __init__(self, live_output: NautilusLiveOutput):
        self.live_output = live_output
    
    async def signal_detected(self,
                            signal_name: str,
                            block_name: str,
                            details: dict):
        """Output signal detection"""
        await self.live_output.send_message(
            level=OutputLevel.DECISION,
            category=OutputCategory.SIGNAL,
            message=f"Signal detected: {signal_name}",
            details={
                'block': block_name,
                'signal': signal_name,
                **details
            },
            source=block_name
        )
    
    async def signal_confirmed(self,
                             signal_name: str,
                             block_name: str,
                             details: dict):
        """Output signal confirmation"""
        await self.live_output.send_message(
            level=OutputLevel.ACTION,
            category=OutputCategory.SIGNAL,
            message=f"Signal confirmed: {signal_name}",
            details={
                'block': block_name,
                'signal': signal_name,
                **details
            },
            source=block_name
        )
    
    async def signal_rejected(self,
                            signal_name: str,
                            block_name: str,
                            reason: str,
                            details: dict):
        """Output signal rejection"""
        await self.live_output.send_message(
            level=OutputLevel.WARNING,
            category=OutputCategory.SIGNAL,
            message=f"Signal rejected: {signal_name}",
            details={
                'block': block_name,
                'signal': signal_name,
                'reason': reason,
                **details
            },
            source=block_name
        )

class NautilusTradeOutput:
    """Handle trade-related output"""
    
    def __init__(self, live_output: NautilusLiveOutput):
        self.live_output = live_output
    
    async def trade_initiated(self,
                            side: str,
                            quantity: Quantity,
                            price: Price,
                            details: dict):
        """Output trade initiation"""
        await self.live_output.send_message(
            level=OutputLevel.ACTION,
            category=OutputCategory.TRADE,
            message=f"Trade initiated: {side}",
            details={
                'side': side,
                'quantity': quantity.to_string(),
                'price': price.to_string(),
                **details
            }
        )
    
    async def trade_completed(self,
                            side: str,
                            quantity: Quantity,
                            price: Price,
                            pnl: Money,
                            details: dict):
        """Output trade completion"""
        await self.live_output.send_message(
            level=OutputLevel.ACTION,
            category=OutputCategory.TRADE,
            message=f"Trade completed: {side}",
            details={
                'side': side,
                'quantity': quantity.to_string(),
                'price': price.to_string(),
                'pnl': pnl.to_string(),
                **details
            }
        )
```

### 4. Integration Tests

```python
async def test_live_output():
    """Test live output system"""
    logger = OptimizerLogger('test')
    live_output = NautilusLiveOutput(logger)
    
    # Test message handling
    messages_received = []
    
    async def test_callback(message):
        messages_received.append(message)
    
    # Start output processing
    await live_output.start()
    
    # Subscribe to output
    live_output.subscribe(test_callback)
    
    # Send test messages
    await live_output.send_message(
        level=OutputLevel.INFO,
        category=OutputCategory.SYSTEM,
        message="Test message",
        details={'test': True}
    )
    
    await live_output.send_message(
        level=OutputLevel.ACTION,
        category=OutputCategory.TRADE,
        message="Test trade",
        details={
            'side': 'BUY',
            'quantity': '1.0',
            'price': '50000'
        }
    )
    
    # Wait for processing
    await asyncio.sleep(1)
    
    # Verify messages
    assert len(messages_received) == 2
    assert messages_received[0]['level'] == 'info'
    assert messages_received[1]['category'] == 'trade'
    
    # Test UI integration
    ui_handler = NautilusLiveOutputUI(live_output)
    
    # Mock UI components
    class MockTextWidget:
        def __init__(self):
            self.text = []
            self.scrollbar = MockScrollbar()
        
        def append(self, text):
            self.text.append(text)
        
        def verticalScrollBar(self):
            return self.scrollbar
    
    class MockScrollbar:
        def setValue(self, value):
            self.value = value
        
        def maximum(self):
            return 100
    
    # Initialize UI
    text_widget = MockTextWidget()
    ui_handler.initialize_ui(None, text_widget)
    
    # Send test message
    await live_output.send_message(
        level=OutputLevel.DECISION,
        category=OutputCategory.SIGNAL,
        message="Test signal",
        details={'signal': 'TEST'}
    )
    
    # Wait for processing
    await asyncio.sleep(1)
    
    # Verify UI update
    assert len(text_widget.text) == 1
    assert 'Test signal' in text_widget.text[0]
    
    # Stop output processing
    await live_output.stop()
```

## 🔍 KEY CONSIDERATIONS

1. **Output Structure**
   - Message levels
   - Categories
   - Timestamps
   - Details
   - Source tracking

2. **Real-time Updates**
   - Async processing
   - Queue management
   - UI updates
   - Scrolling behavior

3. **Integration Points**
   - Execution modes
   - Signal processing
   - Trade execution
   - Risk management

4. **UI Features**
   - Filtering options
   - Color coding
   - Auto-scrolling
   - Detail expansion

## 📈 IMPLEMENTATION STEPS

1. **Setup**
   - [ ] Implement NautilusLiveOutput
   - [ ] Add UI integration
   - [ ] Create output handlers
   - [ ] Add filtering system

2. **Testing**
   - [ ] Message processing tests
   - [ ] UI update tests
   - [ ] Integration tests
   - [ ] Performance tests

3. **Validation**
   - [ ] Test all message types
   - [ ] Verify UI updates
   - [ ] Check filtering
   - [ ] Validate formatting

4. **Documentation**
   - [ ] Update user guide
   - [ ] Document message types
   - [ ] Add usage examples

## 🎯 EXPECTED OUTCOMES

1. **Real-time Updates**
   - Immediate message display
   - Proper formatting
   - Accurate timestamps
   - Correct categorization

2. **UI Features**
   - Message filtering
   - Color coding
   - Auto-scrolling
   - Detail viewing

3. **Integration**
   - Mode-specific output
   - Signal tracking
   - Trade monitoring
   - System status updates

## 📝 MONITORING

Monitor these aspects:
- Message processing speed
- UI responsiveness
- Memory usage
- Queue management
