# NAUTILUS EXECUTION MODES INTEGRATION
**Integration of Different Execution Modes and Non-Optimizer Usage with Optimizer V3**

## 📋 OVERVIEW

This document outlines how different execution modes (Historical Backtest vs Live Replay) and non-optimizer usage are integrated with Optimizer V3, ensuring proper handling of all execution scenarios.

## 🔧 IMPLEMENTATION

### 1. Mode Handler

```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio

class ExecutionMode(Enum):
    """Execution mode types"""
    HISTORICAL_BACKTEST = "historical"  # Mode 1
    LIVE_REPLAY = "live_replay"         # Mode 2
    NON_OPTIMIZER = "no_optimizer"      # Direct test run

class NautilusExecutionHandler:
    """Handle different execution modes"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self._mode = None
        self._config = None
        self._running = False
        self._pause_event = asyncio.Event()
        self._stop_event = asyncio.Event()
    
    def set_mode(self, mode: ExecutionMode):
        """Set execution mode"""
        self._mode = mode
    
    def load_config(self, config: dict) -> dict:
        """Load and validate configuration"""
        try:
            self._config = {
                'mode': self._mode,
                'strategy': self._process_strategy(config['strategy']),
                'execution': self._process_execution_settings(
                    config.get('execution', {})
                ),
                'data_feed': self._process_data_feed(
                    config.get('data_feed', {})
                )
            }
            
            return self._config
            
        except Exception as e:
            self.logger.error(f"Config load failed: {str(e)}")
            raise
    
    def _process_strategy(self, strategy: dict) -> dict:
        """Process strategy configuration"""
        return {
            'name': strategy['name'],
            'blocks': strategy['blocks'],
            'risk_management': strategy['risk_management'],
            'optimizer_enabled': strategy.get('optimizer_enabled', False)
        }
    
    def _process_execution_settings(self, settings: dict) -> dict:
        """Process execution settings"""
        return {
            'mode': self._mode,
            'candle_interval': settings.get('candle_interval', '1m'),
            'warmup_bars': int(settings.get('warmup_bars', 100)),
            'max_bars': (
                int(settings['max_bars']) 
                if self._mode == ExecutionMode.HISTORICAL_BACKTEST
                else None
            ),
            'wait_for_candle': (
                True if self._mode == ExecutionMode.LIVE_REPLAY
                else False
            )
        }
    
    def _process_data_feed(self, feed: dict) -> dict:
        """Process data feed settings"""
        return {
            'type': feed.get('type', 'historical'),
            'instrument_id': InstrumentId(feed['instrument']),
            'start_time': (
                datetime.strptime(feed['start_time'], '%Y-%m-%d %H:%M:%S')
                if 'start_time' in feed else None
            ),
            'end_time': (
                datetime.strptime(feed['end_time'], '%Y-%m-%d %H:%M:%S')
                if 'end_time' in feed else None
            )
        }
    
    async def run(self):
        """Run strategy execution"""
        if not self._config:
            raise ValueError("No configuration loaded")
            
        try:
            self._running = True
            self._pause_event.clear()
            self._stop_event.clear()
            
            # Initialize engine based on mode
            if self._mode == ExecutionMode.HISTORICAL_BACKTEST:
                engine = self._create_backtest_engine()
            elif self._mode == ExecutionMode.LIVE_REPLAY:
                engine = self._create_live_replay_engine()
            else:  # NON_OPTIMIZER
                engine = self._create_direct_engine()
            
            # Run based on mode
            if self._mode == ExecutionMode.HISTORICAL_BACKTEST:
                await self._run_historical(engine)
            elif self._mode == ExecutionMode.LIVE_REPLAY:
                await self._run_live_replay(engine)
            else:  # NON_OPTIMIZER
                await self._run_direct(engine)
                
        except Exception as e:
            self.logger.error(f"Execution failed: {str(e)}")
            raise
        finally:
            self._running = False
    
    def _create_backtest_engine(self) -> BacktestEngine:
        """Create historical backtest engine"""
        return BacktestEngine(
            instrument_id=self._config['data_feed']['instrument_id'],
            start_time=self._config['data_feed']['start_time'],
            end_time=self._config['data_feed']['end_time'],
            optimizer_enabled=self._config['strategy']['optimizer_enabled']
        )
    
    def _create_live_replay_engine(self) -> LiveReplayEngine:
        """Create live replay engine"""
        return LiveReplayEngine(
            instrument_id=self._config['data_feed']['instrument_id'],
            start_time=self._config['data_feed']['start_time'],
            candle_interval=self._config['execution']['candle_interval'],
            optimizer_enabled=self._config['strategy']['optimizer_enabled']
        )
    
    def _create_direct_engine(self) -> DirectEngine:
        """Create direct execution engine"""
        return DirectEngine(
            instrument_id=self._config['data_feed']['instrument_id'],
            optimizer_enabled=False  # Always false for direct execution
        )
    
    async def _run_historical(self, engine: BacktestEngine):
        """Run historical backtest"""
        max_bars = self._config['execution']['max_bars']
        bars_processed = 0
        
        while bars_processed < max_bars and not self._stop_event.is_set():
            # Process next bar
            if await engine.process_next_bar():
                bars_processed += 1
                
                # Handle pause if needed
                await self._handle_pause()
            else:
                break
    
    async def _run_live_replay(self, engine: LiveReplayEngine):
        """Run live replay"""
        while not self._stop_event.is_set():
            # Wait for next candle
            if await engine.wait_for_candle():
                # Process the candle
                await engine.process_candle()
                
                # Handle pause if needed
                await self._handle_pause()
            else:
                # No more candles available
                await asyncio.sleep(1)  # Wait before checking again
    
    async def _run_direct(self, engine: DirectEngine):
        """Run direct execution"""
        while not self._stop_event.is_set():
            # Process next available data
            if await engine.process_next():
                # Handle pause if needed
                await self._handle_pause()
            else:
                break
    
    async def _handle_pause(self):
        """Handle execution pause"""
        if self._pause_event.is_set():
            await self._pause_event.wait()
    
    def pause(self):
        """Pause execution"""
        if self._running:
            self._pause_event.set()
    
    def resume(self):
        """Resume execution"""
        if self._running:
            self._pause_event.clear()
    
    def stop(self):
        """Stop execution"""
        if self._running:
            self._stop_event.set()
            self._pause_event.clear()
```

### 2. Mode-Specific Engines

```python
class BacktestEngine:
    """Historical backtest engine"""
    
    def __init__(self,
                 instrument_id: InstrumentId,
                 start_time: datetime,
                 end_time: datetime,
                 optimizer_enabled: bool):
        self.instrument_id = instrument_id
        self.start_time = start_time
        self.end_time = end_time
        self.optimizer_enabled = optimizer_enabled
        self._data_provider = self._create_data_provider()
    
    async def process_next_bar(self) -> bool:
        """Process next historical bar"""
        try:
            bar = await self._data_provider.get_next_bar()
            if not bar:
                return False
            
            # Process the bar
            if self.optimizer_enabled:
                await self._process_with_optimizer(bar)
            else:
                await self._process_without_optimizer(bar)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Bar processing failed: {str(e)}")
            return False

class LiveReplayEngine:
    """Live replay engine"""
    
    def __init__(self,
                 instrument_id: InstrumentId,
                 start_time: datetime,
                 candle_interval: str,
                 optimizer_enabled: bool):
        self.instrument_id = instrument_id
        self.start_time = start_time
        self.candle_interval = candle_interval
        self.optimizer_enabled = optimizer_enabled
        self._data_provider = self._create_data_provider()
        self._last_candle_time = None
    
    async def wait_for_candle(self) -> bool:
        """Wait for next candle"""
        try:
            while True:
                current_time = await self._data_provider.get_current_time()
                
                if not self._last_candle_time:
                    self._last_candle_time = current_time
                    return True
                
                # Check if new candle should be available
                if self._is_new_candle_due(current_time):
                    self._last_candle_time = current_time
                    return True
                
                # Wait before checking again
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Candle wait failed: {str(e)}")
            return False
    
    async def process_candle(self):
        """Process current candle"""
        try:
            candle = await self._data_provider.get_current_candle()
            
            # Process the candle
            if self.optimizer_enabled:
                await self._process_with_optimizer(candle)
            else:
                await self._process_without_optimizer(candle)
                
        except Exception as e:
            self.logger.error(f"Candle processing failed: {str(e)}")

class DirectEngine:
    """Direct execution engine"""
    
    def __init__(self,
                 instrument_id: InstrumentId,
                 optimizer_enabled: bool = False):
        self.instrument_id = instrument_id
        self.optimizer_enabled = optimizer_enabled
        self._data_provider = self._create_data_provider()
    
    async def process_next(self) -> bool:
        """Process next available data"""
        try:
            data = await self._data_provider.get_next()
            if not data:
                return False
            
            # Process the data
            await self._process_without_optimizer(data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data processing failed: {str(e)}")
            return False
```

### 3. Integration Tests

```python
async def test_execution_modes():
    """Test different execution modes"""
    handler = NautilusExecutionHandler(OptimizerLogger('test'))
    
    # Test historical backtest
    handler.set_mode(ExecutionMode.HISTORICAL_BACKTEST)
    config = {
        'strategy': {
            'name': 'Test Strategy',
            'blocks': [],
            'risk_management': {},
            'optimizer_enabled': True
        },
        'execution': {
            'max_bars': 1000,
            'warmup_bars': 100
        },
        'data_feed': {
            'instrument': 'BTC-USD',
            'start_time': '2025-01-01 00:00:00',
            'end_time': '2025-01-31 00:00:00'
        }
    }
    
    # Load config
    loaded_config = handler.load_config(config)
    assert loaded_config['mode'] == ExecutionMode.HISTORICAL_BACKTEST
    assert loaded_config['execution']['max_bars'] == 1000
    
    # Start execution
    execution_task = asyncio.create_task(handler.run())
    
    # Test pause/resume
    await asyncio.sleep(1)
    handler.pause()
    await asyncio.sleep(1)
    handler.resume()
    
    # Test stop
    await asyncio.sleep(1)
    handler.stop()
    
    await execution_task
    
    # Test live replay
    handler.set_mode(ExecutionMode.LIVE_REPLAY)
    config['execution']['max_bars'] = None  # Not used in live replay
    
    # Load config
    loaded_config = handler.load_config(config)
    assert loaded_config['mode'] == ExecutionMode.LIVE_REPLAY
    assert loaded_config['execution']['wait_for_candle'] == True
    
    # Start execution
    execution_task = asyncio.create_task(handler.run())
    
    # Let it run for a bit
    await asyncio.sleep(5)
    
    # Stop execution
    handler.stop()
    await execution_task
    
    # Test non-optimizer mode
    handler.set_mode(ExecutionMode.NON_OPTIMIZER)
    config['strategy']['optimizer_enabled'] = False
    
    # Load config
    loaded_config = handler.load_config(config)
    assert loaded_config['mode'] == ExecutionMode.NON_OPTIMIZER
    assert loaded_config['strategy']['optimizer_enabled'] == False
    
    # Start execution
    execution_task = asyncio.create_task(handler.run())
    
    # Let it run for a bit
    await asyncio.sleep(5)
    
    # Stop execution
    handler.stop()
    await execution_task
```

## 🔍 KEY CONSIDERATIONS

1. **Mode Differences**
   - Historical Backtest (Mode 1)
     * Fixed number of bars
     * Processes bars sequentially
     * No waiting between bars
   
   - Live Replay (Mode 2)
     * Continuous execution
     * Waits for new candles
     * Real-time processing
   
   - Non-Optimizer Mode
     * Uses optimizer system
     * Optimizer features disabled
     * Direct execution

2. **Execution Control**
   - Pause/Resume capability
   - Clean stop handling
   - Error recovery
   - Progress tracking

3. **Data Handling**
   - Historical data loading
   - Live data streaming
   - Candle interval management
   - Data validation

4. **Integration Points**
   - Strategy execution
   - Optimizer integration
   - Results reporting
   - UI updates

## 📈 IMPLEMENTATION STEPS

1. **Setup**
   - [ ] Implement NautilusExecutionHandler
   - [ ] Add mode-specific engines
   - [ ] Create execution controls
   - [ ] Add progress tracking

2. **Testing**
   - [ ] Mode switching tests
   - [ ] Execution control tests
   - [ ] Data handling tests
   - [ ] Integration tests

3. **Validation**
   - [ ] Test all execution modes
   - [ ] Verify control functions
   - [ ] Check error handling
   - [ ] Validate results

4. **Documentation**
   - [ ] Update user guide
   - [ ] Document mode differences
   - [ ] Add usage examples

## 🎯 EXPECTED OUTCOMES

1. **Mode Support**
   - Historical backtest working
   - Live replay functioning
   - Non-optimizer mode available

2. **Control Features**
   - Pause/Resume working
   - Clean stop handling
   - Error recovery functioning

3. **Data Management**
   - Proper data loading
   - Correct streaming
   - Valid processing

## 📝 MONITORING

Monitor these aspects:
- Mode switching accuracy
- Execution control reliability
- Data processing integrity
- Error handling effectiveness
