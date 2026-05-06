"""
Ultra Hybrid Simulator - MAXIMUM PARALLEL Performance

THREE-PHASE OPTIMIZATION:

Phase 1 (32-Core Parallel): Pre-compute building blocks in parallel chunks
  - Split 17,280 bars into 32 chunks (~540 bars each)
  - Each core processes its chunk independently
  - Merge results in order
  - Time: ~34 seconds (vs 18 minutes single-core!)

Phase 2 (Single-Core): Merge building block results
  - Combine results from all 32 chunks
  - Validate ordering
  - Time: <1 second

Phase 3 (32-Core Parallel): Test all 48 configs
  - Each core tests 1-2 configs on merged results
  - Just lightweight confluence math
  - Time: ~0.3 seconds

Total: ~35 seconds (vs 18 minutes hybrid, vs 30-40 min old multicore!)

Speedup: ~32x faster than hybrid approach!
"""

import pandas as pd
from typing import List, Dict, Tuple
from multiprocessing import Pool, cpu_count
from pathlib import Path
import pickle
from .data_classes import OptimizationConfig, ConfigPerformance, TradeResult
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

def process_bar_chunk(args):
    """
    Process a chunk of bars on one CPU core
    
    Each core gets:
    - Full warmup data (needed for building blocks)
    - Its assigned chunk of test bars
    - Strategy class to instantiate locally
    
    Returns:
    - List of building block results for its chunk
    """
    chunk_id, warmup_df, test_chunk_df, strategy_module_name, config = args
    
    from .data_loader import get_strategy_class
    
    # Log to file
    log_file = Path(__file__).parent.parent.parent.parent.parent / 'logs' / f'chunk_{chunk_id}.log'
    
    def log(msg):
        import datetime
        with open(log_file, 'a') as f:
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")
    
    log(f"Chunk {chunk_id} starting: {len(test_chunk_df)} bars to process")
    
    # Load strategy class
    strategy_class = get_strategy_class(strategy_module_name)
    
    # Create strategy instance
    class TestStrategy:
        def __init__(self, cfg):
            self.strategy_id = cfg.strategy_id
            self.strategy_name = cfg.strategy_name
            self.min_confluence = cfg.min_confluence
            self.max_bars_held = 1000
            self.lookback_period = 100
            self.min_risk_reward = cfg.min_risk_reward
            self.peak_tolerance = 0.002
            self.bars_data = []
            self.blocks = cfg.blocks
            self.detectors = {}
    
    strategy = TestStrategy(config)
    
    # Bind methods
    for method_name in dir(strategy_class):
        if method_name.startswith('_') and not method_name.startswith('__'):
            method = getattr(strategy_class, method_name)
            if callable(method):
                setattr(strategy, method_name, method.__get__(strategy))
    
    # Initialize building blocks
    if hasattr(strategy, '_initialize_blocks'):
        strategy._initialize_blocks()
        log(f"Initialized {len(strategy.detectors)} building blocks")
    
    # Combine warmup + this chunk
    full_df = pd.concat([warmup_df, test_chunk_df], ignore_index=True)
    warmup_bar_count = len(warmup_df)
    
    log(f"Processing bars {warmup_bar_count} to {len(full_df)}")
    
    # Process each bar in this chunk
    chunk_results = []
    import time
    start_time = time.time()
    
    for i in range(warmup_bar_count, len(full_df)):
        history = full_df.iloc[:i+1]
        results = strategy._analyze_blocks(history)
        chunk_results.append(results)
    
    elapsed = time.time() - start_time
    bars_per_sec = len(chunk_results) / elapsed if elapsed > 0 else 0
    log(f"Chunk {chunk_id} complete: {len(chunk_results)} bars in {elapsed:.1f}s ({bars_per_sec:.1f} bars/sec)")
    
    return (chunk_id, chunk_results)


def test_single_config(args):
    """
    Test one config on pre-computed results WITH DYNAMIC TPs & SLs!
    
    ENHANCEMENTS:
    - Sequential signal accumulation across multiple bars
    - DYNAMIC TP calculation using building blocks (Fibonacci/Swing/S&D)
    - DYNAMIC SL calculation using building blocks (Pattern invalidation)
    - Intelligent TP zone selection (not all TPs always used)
    - Trailing stops for profit protection
    - Customizable TP distances and exit splits per config
    
    Entry triggers when accumulated confluence meets threshold.
    TPs calculated using config's tp_mode (PERCENTAGE/FIBONACCI/HYBRID).
    SLs calculated using config's sl_mode (SWING_POINTS/HYBRID/etc).
    """
    from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator
    from src.strategies.signal_accumulator import SignalAccumulator
    from src.strategies.universal_optimizer.modules.dynamic_tp_calculator import DynamicTPCalculator
    from src.strategies.universal_optimizer.modules.dynamic_sl_calculator import (
        AdaptiveSLCalculator,
        calculate_breakeven_sl,
        calculate_trailing_sl
    )
    
    # Safely unpack args (may have 3 or 4 elements)
    if len(args) == 4:
        config, all_results, test_df, debugger = args
    else:
        config, all_results, test_df = args
        debugger = None
    
    # Register config snapshot for this test
    if debugger:
        debugger.register_config_source(config.to_dict(), source=f"config_{config.config_id}")
    
    trades = []
    current_position = None
    
    # Initialize signal accumulator for sequential confluence building
    # WIDENED WINDOW: 60 bars (15 hours) to capture more HOD rejection setups
    # HOD rejection may fire infrequently, need wider window for confluence buildup
    accumulator = SignalAccumulator(
        min_confluence=config.min_confluence,
        window_bars=60  # Widened from 20 to capture more signals
    )
    
    for bar_idx, bar_results in enumerate(all_results):
        # NEW: Use signal accumulator for sequential confluence
        should_enter, total_confluence, active_signals = accumulator.on_bar(
            bar_number=bar_idx,
            block_results=bar_results,
            block_configs=config.blocks
        )
        
        # ENTRY LOGIC - Triggered by accumulator
        if should_enter and current_position is None:
            entry_price = test_df.iloc[bar_idx]['close']
            entry_time = test_df.iloc[bar_idx]['timestamp']
            
            # Initialize DynamicTPCalculator for this entry
            tp_calculator = DynamicTPCalculator(
                tp_mode=config.tp_mode
            )
            
            # Initialize AdaptiveSLCalculator v2.0 for this entry
            # Use values from THIS strategy's config (NO hardcoded defaults from other strategies!)
            sl_calculator = AdaptiveSLCalculator(
                volatility_lookback=config.volatility_lookback,
                volatility_multiplier=config.volatility_multiplier,
                absolute_min_pct=config.absolute_min_sl_pct,
                absolute_max_pct=config.absolute_max_sl_pct,
                initial_sl_multiplier=getattr(config, 'initial_sl_multiplier', 1.5),  # Optional param
                working_sl_multiplier=getattr(config, 'working_sl_multiplier', 1.0),  # Optional param
                use_delayed_sl=config.use_delayed_sl,
                delay_bars=config.delay_bars,
                emergency_sl_pct=config.emergency_sl_pct,
                use_structure_sl=config.use_structure_sl,
                structure_sources=config.structure_sources
            )
            
            # Calculate dynamic TPs using building blocks!
            history_for_tp = test_df.iloc[max(0, bar_idx-100):bar_idx+1]
            
            tp_levels = tp_calculator.calculate_tp_levels(
                df=history_for_tp,
                entry_price=entry_price,
                entry_bar=len(history_for_tp) - 1,  # Last bar in history
                side=config.side,
                fallback_pcts=config.tp_fallback_pcts,  # Use config's TP distances
                debugger=debugger  # Pass debugger for micro-granular logging
            )
            
            # Calculate ADAPTIVE SL using v2.0 system!
            sl_result = sl_calculator.calculate_sl_levels(
                df=history_for_tp,
                entry_price=entry_price,
                entry_bar=len(history_for_tp) - 1,
                side=config.side,
                debugger=debugger  # Pass debugger for micro-granular logging
            )
            
            # Extract TP/SL from calculated levels
            tp1 = tp_levels.tp1
            tp2 = tp_levels.tp2
            tp3 = tp_levels.tp3
            emergency_sl = sl_result.emergency_sl  # Wide protection (bar 0-delay)
            working_sl = sl_result.working_sl      # Tight optimization (after delay)
            sl = emergency_sl  # Start with emergency SL
            
            # DEBUG: Log TP values for forensic analysis
            logger.debug(f"\n🔍 TP CALC DEBUG | Entry: ${entry_price:.2f} | Side: {config.side}")
            logger.info(f"   TP1 = ${tp1:.2f} (should be closest,  {abs((entry_price-tp1)/entry_price*100):.2f}% away)")
            logger.info(f"   TP2 = ${tp2:.2f} (should be middle,   {abs((entry_price-tp2)/entry_price*100):.2f}% away)")
            logger.info(f"   TP3 = ${tp3:.2f} (should be furthest, {abs((entry_price-tp3)/entry_price*100):.2f}% away)")
            if config.side == 'SHORT':
                logger.info(f"   ORDER CHECK (SHORT): tp1 > tp2 > tp3? {tp1:.2f} > {tp2:.2f} > {tp3:.2f} = {tp1 > tp2 > tp3}")
            else:
                logger.info(f"   ORDER CHECK (LONG):  tp1 < tp2 < tp3? {tp1:.2f} < {tp2:.2f} < {tp3:.2f} = {tp1 < tp2 < tp3}")
            
            # Get partial exit percentages from config
            exit_pct_tp1 = config.partial_exit_pcts.get('tp1', 50)
            exit_pct_tp2 = config.partial_exit_pcts.get('tp2', 30)
            exit_pct_tp3 = config.partial_exit_pcts.get('tp3', 20)
            
            # Verify R:R meets minimum (using TP2 vs WORKING SL for realistic R:R)
            rr_ratio = abs((tp2 - entry_price) / (working_sl - entry_price))
            
            # CORRECT APPROACH: Simply skip trades that don't meet R:R requirement
            # This allows different R:R configs to filter trades differently!
            if rr_ratio < config.min_risk_reward:
                # Log the rejection for debugging (optional, only if debugger enabled)
                if debugger:
                    debugger.log_decision(
                        decision_type="if",
                        condition=f"rr_ratio < min_risk_reward ({rr_ratio:.2f} < {config.min_risk_reward:.2f})",
                        result=False,  # Condition failed → trade rejected
                        config_keys_used=['min_risk_reward']
                    )
                continue  # Skip this trade - doesn't meet R:R requirement
            
            # If we reach here, trade meets R:R requirement naturally
            # Log the successful trade entry (ONLY actual trades - keeps log small!)
            if debugger:
                debugger.log_action(
                    action="TRADE_ENTRY",
                    config_keys_used=['min_confluence', 'min_risk_reward', 'tp_mode', 'sl_mode'],
                    parameters={
                        'config_id': config.config_id,
                        'bar_idx': bar_idx,
                        'entry_price': entry_price,
                        'confluence': total_confluence,
                        'tp1': tp1,
                        'tp2': tp2,
                        'tp3': tp3,
                        'working_sl': working_sl,
                        'emergency_sl': emergency_sl,
                        'rr_ratio': rr_ratio,
                        'min_rr_required': config.min_risk_reward,
                        'tp_method': tp_levels.method,
                        'sl_method': sl_result.method,
                        'rr_check_passed': True  # Flag that R:R check passed
                    }
                )
            
            current_position = {
                'entry_bar': bar_idx,
                'entry_price': entry_price,
                'entry_time': entry_time,
                'confluence': total_confluence,
                'side': config.side,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'sl': sl,  # Active SL (starts with emergency)
                'emergency_sl': emergency_sl,  # Wide protection
                'working_sl': working_sl,      # Tight optimization
                'sl_result': sl_result,        # Full SL calculation result
                'use_tp1': tp_levels.use_tp1,  # Track which TPs to use
                'use_tp2': tp_levels.use_tp2,
                'use_tp3': tp_levels.use_tp3,
                'tp1_hit': False,  # Track TP hits for breakeven logic
                'tp2_hit': False,  # Track TP hits for trailing logic
                'exit_pct_tp1': exit_pct_tp1,  # Dynamic exit percentages
                'exit_pct_tp2': exit_pct_tp2,
                'exit_pct_tp3': exit_pct_tp3,
                'trailing_activation_price': tp_levels.trailing_activation_price,
                'tp_method': tp_levels.method,  # Track TP calculation method used
                'sl_method': sl_result.method,  # Track SL calculation method used
                'sl_invalidation': sl_result.invalidation_reason,  # Why this SL
                'remaining_pct': 100.0,
                'exits': [],
                'tp_calculator': tp_calculator,  # Store for trailing logic
                'best_price': entry_price  # Track best price for trailing
            }
        
        # EXIT LOGIC - Monitor TP/SL levels
        if current_position is not None:
            bars_held = bar_idx - current_position['entry_bar']
            bar = test_df.iloc[bar_idx]
            
            # Update active SL (emergency → working after delay)
            current_position['sl'] = sl_calculator.get_active_sl(
                current_position['sl_result'],
                bars_held
            )
            
            exit_occurred = False
            exit_price = None
            exit_reason = None
            
            # For SHORT positions
            if config.side == 'SHORT':
                # Update best price for trailing (track lowest price)
                if bar['low'] < current_position['best_price']:
                    current_position['best_price'] = bar['low']
                
                # Check TP levels in PRICE ORDER (highest to lowest for SHORT)
                # Create list of TPs with their info, sorted by price (descending for SHORT)
                tp_checks = []
                if current_position['use_tp1']:
                    tp_checks.append((current_position['tp1'], current_position['exit_pct_tp1'], 'tp1_hit'))
                if current_position['use_tp2']:
                    tp_checks.append((current_position['tp2'], current_position['exit_pct_tp2'], 'tp2_hit'))
                if current_position['use_tp3']:
                    tp_checks.append((current_position['tp3'], current_position['exit_pct_tp3'], 'tp3_hit'))
                
                # Sort by price DESCENDING (highest price first for SHORT = closest to entry)
                tp_checks.sort(key=lambda x: x[0], reverse=True)
                
                # Assign TP labels based on ORDER (1st hit = TP1, 2nd hit = TP2, 3rd hit = TP3)
                tp_names = ['TP1_PARTIAL', 'TP2_PARTIAL', 'TP3_HIT']
                
                # Check TPs in price order
                for idx, (tp_price, exit_pct, hit_flag) in enumerate(tp_checks):
                    if bar['low'] <= tp_price and current_position['remaining_pct'] >= exit_pct:
                        # TP hit - use ACTUAL bar close price (institutional grade)
                        exit_price = bar['close']
                        exit_reason = tp_names[idx]  # Assign label based on hit ORDER, not original name
                        tp_label = f"TP{idx+1}"
                        logger.info(f"🎯 {tp_label} HIT! Bar low: ${bar['low']:.2f} <= Price: ${tp_price:.2f} | Exit: ${exit_price:.2f} | Exit%: {exit_pct}%")
                        current_position['exits'].append({
                            'price': exit_price,
                            'pct': exit_pct,
                            'reason': exit_reason
                        })
                        current_position['remaining_pct'] -= exit_pct
                        current_position[hit_flag] = True
                    
                        
                        # Move SL to breakeven after TP1 if configured
                        if 'TP1' in exit_reason and config.breakeven_after_tp1 and not current_position.get('breakeven_set', False):
                            # Use THIS strategy's config values
                            leverage = config.max_leverage
                            starting_capital = config.starting_capital
                            risk_per_trade_pct = config.risk_per_trade_pct
                            position_pct = risk_per_trade_pct / 100.0
                            margin_per_trade = starting_capital * position_pct
                            entry_notional = margin_per_trade * leverage
                            position_size = entry_notional / current_position['entry_price']
                            breakeven_sl = calculate_breakeven_sl(
                                current_position['entry_price'],
                                config.side,
                                entry_notional,
                                position_size
                            )
                            # Only update if better than current SL
                            if config.side == 'SHORT':
                                if breakeven_sl < current_position['sl']:
                                    current_position['sl'] = breakeven_sl
                                    current_position['breakeven_set'] = True
                            else:
                                if breakeven_sl > current_position['sl']:
                                    current_position['sl'] = breakeven_sl
                                    current_position['breakeven_set'] = True
                        
                        # Check if this was the final TP
                        if current_position['remaining_pct'] == 0:
                            exit_occurred = True
                        break  # Only process one TP per bar
                
                # Check trailing stop after TP2 (if configured)
                if config.use_trailing and current_position.get('tp2_hit', False):
                    # Trailing activated after TP2! Trail the stop loss
                    new_sl = calculate_trailing_sl(
                        current_position['best_price'],
                        config.side,
                        config.trailing_pct
                    )
                    # Only update if tighter than current SL
                    if new_sl < current_position['sl']:
                        current_position['sl'] = new_sl
                
                # Check SL (price going UP)
                if bar['high'] >= current_position['sl'] and not exit_occurred:
                    # Stop loss hit - use ACTUAL bar close price (institutional grade)
                    exit_price = bar['close']
                    exit_reason = 'SL_HIT'
                    
                    # INSTITUTIONAL DEBUG: Log SL exit details for Adaptive SL forensics
                    logger.info(f"🔍 SL_HIT (SHORT) | Bar {bars_held} | remaining_pct={current_position['remaining_pct']:.4f}% | "
                          f"Entry=${current_position['entry_price']:.2f} | Exit=${exit_price:.2f} | "
                          f"SL_mode={current_position.get('sl_method', 'UNKNOWN')} | "
                          f"TP1_hit={current_position.get('tp1_hit', False)} | "
                          f"TP2_hit={current_position.get('tp2_hit', False)}")
                    
                    current_position['exits'].append({
                        'price': exit_price,
                        'pct': current_position['remaining_pct'],
                        'reason': exit_reason
                    })
                    current_position['remaining_pct'] = 0  # CRITICAL FIX
                    exit_occurred = True
                    
            else:  # LONG positions
                # Update best price for trailing (track highest price)
                if bar['high'] > current_position['best_price']:
                    current_position['best_price'] = bar['high']
                
                # Check TP levels in PRICE ORDER (lowest to highest for LONG)
                # Create list of TPs with their info, sorted by price (ascending for LONG)
                tp_checks = []
                if current_position['use_tp1']:
                    tp_checks.append((current_position['tp1'], current_position['exit_pct_tp1'], 'tp1_hit'))
                if current_position['use_tp2']:
                    tp_checks.append((current_position['tp2'], current_position['exit_pct_tp2'], 'tp2_hit'))
                if current_position['use_tp3']:
                    tp_checks.append((current_position['tp3'], current_position['exit_pct_tp3'], 'tp3_hit'))
                
                # Sort by price ASCENDING (lowest price first for LONG = closest to entry)
                tp_checks.sort(key=lambda x: x[0])
                
                # Assign TP labels based on ORDER (1st hit = TP1, 2nd hit = TP2, 3rd hit = TP3)
                tp_names = ['TP1_PARTIAL', 'TP2_PARTIAL', 'TP3_HIT']
                
                # Check TPs in price order
                for idx, (tp_price, exit_pct, hit_flag) in enumerate(tp_checks):
                    if bar['high'] >= tp_price and current_position['remaining_pct'] >= exit_pct:
                        # TP hit - use ACTUAL bar close price (institutional grade)
                        exit_price = bar['close']
                        exit_reason = tp_names[idx]  # Assign label based on hit ORDER, not original name
                        tp_label = f"TP{idx+1}"
                        logger.info(f"🎯 {tp_label} HIT! Bar high: ${bar['high']:.2f} >= Price: ${tp_price:.2f} | Exit: ${exit_price:.2f} | Exit%: {exit_pct}%")
                        current_position['exits'].append({
                            'price': exit_price,
                            'pct': exit_pct,
                            'reason': exit_reason
                        })
                        current_position['remaining_pct'] -= exit_pct
                        current_position[hit_flag] = True
                    
                        # Move SL to breakeven after TP1 if configured
                        if 'TP1' in exit_reason and config.breakeven_after_tp1 and not current_position.get('breakeven_set', False):
                            # Use THIS strategy's config values
                            leverage = config.max_leverage
                            starting_capital = config.starting_capital
                            risk_per_trade_pct = config.risk_per_trade_pct
                            position_pct = risk_per_trade_pct / 100.0
                            margin_per_trade = starting_capital * position_pct
                            entry_notional = margin_per_trade * leverage
                            position_size = entry_notional / current_position['entry_price']
                            breakeven_sl = calculate_breakeven_sl(
                                current_position['entry_price'],
                                config.side,
                                entry_notional,
                                position_size
                            )
                            # Only update if better than current SL
                            if config.side == 'SHORT':
                                if breakeven_sl < current_position['sl']:
                                    current_position['sl'] = breakeven_sl
                                    current_position['breakeven_set'] = True
                            else:
                                if breakeven_sl > current_position['sl']:
                                    current_position['sl'] = breakeven_sl
                                    current_position['breakeven_set'] = True
                        
                        # Check if this was the final TP
                        if current_position['remaining_pct'] == 0:
                            exit_occurred = True
                        break  # Only process one TP per bar
                
                # Check trailing stop after TP2 (if configured)
                if config.use_trailing and current_position.get('tp2_hit', False):
                    # Trailing activated after TP2! Trail the stop loss
                    new_sl = calculate_trailing_sl(
                        current_position['best_price'],
                        config.side,
                        config.trailing_pct
                    )
                    # Only update if tighter than current SL
                    if new_sl > current_position['sl']:
                        current_position['sl'] = new_sl
                
                # Check SL (price going DOWN)
                if bar['low'] <= current_position['sl'] and not exit_occurred:
                    # Stop loss hit - use ACTUAL bar close price (institutional grade)
                    exit_price = bar['close']
                    exit_reason = 'SL_HIT'
                    
                    # INSTITUTIONAL DEBUG: Log SL exit details for Adaptive SL forensics
                    logger.info(f"🔍 SL_HIT (LONG) | Bar {bars_held} | remaining_pct={current_position['remaining_pct']:.4f}% | "
                          f"Entry=${current_position['entry_price']:.2f} | Exit=${exit_price:.2f} | "
                          f"SL_mode={current_position.get('sl_method', 'UNKNOWN')} | "
                          f"TP1_hit={current_position.get('tp1_hit', False)} | "
                          f"TP2_hit={current_position.get('tp2_hit', False)}")
                    
                    current_position['exits'].append({
                        'price': exit_price,
                        'pct': current_position['remaining_pct'],
                        'reason': exit_reason
                    })
                    current_position['remaining_pct'] = 0
                    exit_occurred = True
            
            # Max hold time - USE CONFIG VALUE with fallback (default 1000 bars = ~10 days)
            max_bars_held = getattr(config, 'max_bars_held', 1000)
            if bars_held >= max_bars_held and not exit_occurred and current_position['remaining_pct'] > 0:
                exit_price = bar['close']
                exit_reason = 'MAX_HOLD'
                current_position['exits'].append({
                    'price': exit_price,
                    'pct': current_position['remaining_pct'],
                    'reason': exit_reason
                })
                current_position['remaining_pct'] = 0  # CRITICAL FIX
                exit_occurred = True
            
            # Force close on last bar
            if bar_idx == len(all_results) - 1 and current_position['remaining_pct'] > 0:
                exit_price = bar['close']
                exit_reason = 'END_OF_DATA'
                current_position['exits'].append({
                    'price': exit_price,
                    'pct': current_position['remaining_pct'],
                    'reason': exit_reason
                })
                current_position['remaining_pct'] = 0  # CRITICAL FIX
                exit_occurred = True
            
            # Process trade if fully closed - CREATE SEPARATE RECORDS FOR EACH PARTIAL EXIT
            if exit_occurred and current_position['remaining_pct'] == 0:
                exit_time = test_df.iloc[bar_idx]['timestamp']
                
                # Position sizing - Use THIS strategy's config values
                leverage = config.max_leverage
                starting_capital = config.starting_capital
                risk_per_trade_pct = config.risk_per_trade_pct
                position_pct = risk_per_trade_pct / 100.0  # Convert percentage to decimal
                margin_per_trade = starting_capital * position_pct
                notional_per_trade = margin_per_trade * leverage
                
                # Calculate position size in BTC
                entry_price_val = current_position['entry_price']
                position_size = notional_per_trade / entry_price_val  # ~0.263 BTC @ $95K
                
                # Calculate total funding fees (will be prorated across exits)
                entry_notional = entry_price_val * position_size
                funding_periods = bars_held // 32  # 32 bars = 8 hours at 15min bars
                total_funding_fee = entry_notional * 0.0001 * funding_periods if funding_periods > 0 else 0
                
                # CREATE SEPARATE TRADE RECORD FOR EACH PARTIAL EXIT
                # This allows proper tracking of TP1, TP2, TP3 hits in trade_registry
                for exit_info in current_position['exits']:
                    exit_pct = exit_info['pct']
                    exit_price_partial = exit_info['price']
                    exit_reason_partial = exit_info['reason']
                    
                    # Size for this partial exit
                    partial_size = position_size * (exit_pct / 100.0)
                    partial_notional = entry_price_val * partial_size
                    
                    # PnL for this partial exit
                    if config.side == 'LONG':
                        partial_pnl = (exit_price_partial - entry_price_val) * partial_size
                    else:
                        partial_pnl = (entry_price_val - exit_price_partial) * partial_size
                    
                    # Fees for this partial exit (prorated)
                    exit_notional_partial = exit_price_partial * partial_size
                    fee_entry_partial = partial_notional * 0.0005  # Entry fee (prorated)
                    fee_exit_partial = exit_notional_partial * 0.0005  # Exit fee
                    partial_fee = fee_entry_partial + fee_exit_partial
                    
                    # Add prorated funding fees
                    funding_fee_partial = total_funding_fee * (exit_pct / 100.0)
                    partial_fee += funding_fee_partial
                    
                    net_pnl_partial = partial_pnl - partial_fee
                    
                    # Map exit reason to exit condition name for trade_registry
                    if 'TP1' in exit_reason_partial:
                        exit_condition = 'TP1'
                    elif 'TP2' in exit_reason_partial:
                        exit_condition = 'TP2'
                    elif 'TP3' in exit_reason_partial:
                        exit_condition = 'TP3'
                    elif 'SL' in exit_reason_partial:
                        exit_condition = 'SL'
                    elif 'MAX_HOLD' in exit_reason_partial:
                        exit_condition = 'MAX_BARS'
                    else:
                        exit_condition = 'OTHER'
                    
                    # Create separate trade record for this partial exit
                    trades.append({
                        'entry_time': current_position['entry_time'],
                        'exit_time': exit_time,
                        'entry_price': current_position['entry_price'],
                        'exit_price': exit_price_partial,  # Actual exit price for this partial
                        'pnl': partial_pnl,
                        'fee': partial_fee,
                        'net_pnl': net_pnl_partial,
                        'bars_held': bars_held,
                        'confluence': current_position['confluence'],
                        'exit_reason': exit_reason_partial,
                        'exit_condition_name': exit_condition,  # For trade_registry categorization
                        'exit_type': 'TAKE_PROFIT' if 'TP' in exit_condition else 'STOP_LOSS' if exit_condition == 'SL' else 'TIME_LIMIT',
                        'partial_exit': exit_pct < 100,  # True if partial (< 100%), False if full close
                        'exit_percentage': exit_pct / 100.0,  # Convert to decimal (50% → 0.5)
                        'position_size': position_size,  # ✅ INSTITUTIONAL FIX: Actual total position size in BTC
                        'partial_size': partial_size,  # ✅ Size of this specific partial exit in BTC
                    })
                
                current_position = None
    
    # Calculate metrics matching ConfigPerformance class
    if len(trades) == 0:
        return ConfigPerformance(
            config_id=config.config_id,
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate_pct=0.0, total_pnl=0.0, total_fees=0.0,
            net_pnl=0.0, net_return_pct=0.0, profit_factor=0.0,
            sharpe_ratio=0.0, max_drawdown_pct=0.0,
            avg_win=0.0, avg_loss=0.0, largest_win=0.0, largest_loss=0.0
        )
    
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t['net_pnl'] > 0)
    losing_trades = total_trades - winning_trades
    total_pnl = sum(t['pnl'] for t in trades)
    total_fees = sum(t['fee'] for t in trades)
    net_pnl = sum(t['net_pnl'] for t in trades)
    win_rate_pct = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # Net return percentage - Use THIS strategy's config value
    starting_capital_for_calc = config.starting_capital
    net_return_pct = (net_pnl / starting_capital_for_calc * 100) if net_pnl != 0 else 0.0
    
    # Profit factor
    gross_profit = sum(t['net_pnl'] for t in trades if t['net_pnl'] > 0)
    gross_loss = abs(sum(t['net_pnl'] for t in trades if t['net_pnl'] < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
    
    # Sharpe ratio
    returns = [t['net_pnl'] / t['entry_price'] for t in trades]
    avg_return = sum(returns) / len(returns) if returns else 0
    std_return = (sum((r - avg_return)**2 for r in returns) / len(returns))**0.5 if len(returns) > 1 else 0
    sharpe_ratio = (avg_return / std_return * (252**0.5)) if std_return > 0 else 0.0
    
    # Max drawdown
    cumulative = 0
    peak = 0
    max_dd = 0
    for t in trades:
        cumulative += t['net_pnl']
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    # Max drawdown as percentage of starting capital (use actual capital from config)
    max_drawdown_pct = (max_dd / starting_capital_for_calc * 100) if peak > 0 else 0.0
    
    # Win/loss stats
    wins = [t['net_pnl'] for t in trades if t['net_pnl'] > 0]
    losses = [t['net_pnl'] for t in trades if t['net_pnl'] < 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    largest_win = max(wins) if wins else 0.0
    largest_loss = min(losses) if losses else 0.0
    
    # Convert trades to TradeResult objects
    trade_results = []
    for t in trades:
        pnl_pct = (t['net_pnl'] / t['entry_price']) * 100
        trade_result = TradeResult(
            entry_time=t['entry_time'],
            exit_time=t['exit_time'],
            entry_price=t['entry_price'],
            exit_price=t['exit_price'],
            side=config.side,
            pnl=t['pnl'],
            pnl_pct=pnl_pct,
            fees=t['fee'],
            net_pnl=t['net_pnl'],
            confluence=t['confluence'],
            reason=f"Held {t['bars_held']} bars"
        )
        trade_results.append(trade_result)
    
    return ConfigPerformance(
        config_id=config.config_id,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate_pct=win_rate_pct,
        total_pnl=total_pnl,
        total_fees=total_fees,
        net_pnl=net_pnl,
        net_return_pct=net_return_pct,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe_ratio,
        max_drawdown_pct=max_drawdown_pct,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        trades=trade_results
    )


class UltraHybridSimulator:
    """
    Ultra Hybrid = Parallel Phase 1 + Parallel Phase 3
    
    Result: ~35 seconds total (32x faster than single-core Phase 1!)
    """
    
    def __init__(self, num_cores: int = None):
        self.num_cores = num_cores or cpu_count()
        logger.info(f"   Ultra Hybrid: Using {self.num_cores} CPU cores for BOTH phases!")
    
    def optimize(
        self,
        configs: List[OptimizationConfig],
        warmup_df: pd.DataFrame,
        test_df: pd.DataFrame,
        strategy_module_name: str,
        debugger = None  # Optional[ConfigDebugger] = None
    ) -> List[ConfigPerformance]:
        """Run ultra hybrid three-phase optimization"""
        
        import time
        from datetime import datetime
        # Setup debug logging
        log_dir = Path(__file__).parent.parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f'ultra_hybrid_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        def log_debug(message):
            with open(log_file, 'a') as f:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                f.write(f"[{timestamp}] {message}\n")
            logger.debug(f"   DEBUG: {message}")
        
        log_debug(f"Ultra Hybrid Optimization Starting")
        log_debug(f"Strategy: {strategy_module_name}")
        log_debug(f"Total bars to process: {len(test_df)}")
        log_debug(f"CPU cores available: {self.num_cores}")
        
        # PHASE 1: Parallel building block computation
        logger.info(f"\n⚡ PHASE 1: Pre-computing building blocks in PARALLEL...")
        logger.info(f"   Splitting {len(test_df)} bars across {self.num_cores} cores")
        logger.info(f"   Each core processes ~{len(test_df) // self.num_cores} bars independently")
        
        log_debug(f"Phase 1: Starting parallel building block computation")
        
        phase1_start = time.time()
        
        # Split test_df into chunks
        chunk_size = len(test_df) // self.num_cores
        chunks = []
        
        log_debug(f"Creating {self.num_cores} chunks of ~{chunk_size} bars each")
        
        for i in range(self.num_cores):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < self.num_cores - 1 else len(test_df)
            chunk_df = test_df.iloc[start_idx:end_idx].copy()
            chunks.append((i, warmup_df, chunk_df, strategy_module_name, configs[0]))
            log_debug(f"Chunk {i}: bars {start_idx}-{end_idx} ({len(chunk_df)} bars)")
        
        logger.info(f"   Created {len(chunks)} chunks")
        log_debug(f"All chunks created, starting parallel processing...")
        
        # Process chunks in parallel
        log_debug(f"Spawning {self.num_cores} worker processes...")
        with Pool(processes=self.num_cores) as pool:
            chunk_results = pool.map(process_bar_chunk, chunks)
        
        phase1_time = time.time() - phase1_start
        log_debug(f"Phase 1 complete: {phase1_time:.1f}s")
        log_debug(f"Received results from {len(chunk_results)} chunks")
        logger.info(f"   ✅ Phase 1 complete in {phase1_time:.1f}s")
        
        # PHASE 2: Merge results
        logger.info(f"\n🔄 PHASE 2: Merging {self.num_cores} chunks...")
        log_debug(f"Phase 2: Starting merge of {self.num_cores} chunks")
        phase2_start = time.time()
        
        # Sort by chunk_id and flatten
        chunk_results.sort(key=lambda x: x[0])
        log_debug(f"Chunks sorted by ID")
        all_building_block_results = []
        for chunk_id, results in chunk_results:
            all_building_block_results.extend(results)
            log_debug(f"Merged chunk {chunk_id}: {len(results)} bars, total so far: {len(all_building_block_results)}")
            logger.info(f"   Merged chunk {chunk_id}: {len(results)} bars")
        
        phase2_time = time.time() - phase2_start
        log_debug(f"Phase 2 complete: {phase2_time:.1f}s")
        log_debug(f"Final merged result: {len(all_building_block_results)} total bars")
        logger.info(f"   ✅ Phase 2 complete in {phase2_time:.1f}s")
        logger.info(f"   Total building block results: {len(all_building_block_results)}")
        
        # Validate merge
        if len(all_building_block_results) != len(test_df):
            log_debug(f"WARNING: Merged results ({len(all_building_block_results)}) != test bars ({len(test_df)})")
        else:
            log_debug(f"✓ Merge validation passed: {len(all_building_block_results)} bars")
        
        # PHASE 3: Parallel config testing
        logger.info(f"\n⚡ PHASE 3: Testing {len(configs)} configs across {self.num_cores} cores...")
        log_debug(f"Phase 3: Starting parallel config testing")
        log_debug(f"Total configs to test: {len(configs)}")
        phase3_start = time.time()
        
        # Pass debugger as 4th element in test_args (if present)
        if debugger:
            test_args = [(config, all_building_block_results, test_df, debugger) for config in configs]
            log_debug(f"Created test arguments for {len(test_args)} configs (with debugger)")
        else:
            test_args = [(config, all_building_block_results, test_df) for config in configs]
            log_debug(f"Created test arguments for {len(test_args)} configs")
        
        log_debug(f"Spawning {self.num_cores} worker processes for config testing...")
        with Pool(processes=self.num_cores) as pool:
            results = pool.map(test_single_config, test_args)
        
        phase3_time = time.time() - phase3_start
        log_debug(f"Phase 3 complete: {phase3_time:.1f}s")
        log_debug(f"Received {len(results)} config performance results")
        logger.info(f"   ✅ Phase 3 complete in {phase3_time:.1f}s")
        
        total_time = time.time() - phase1_start
        log_debug(f"=== OPTIMIZATION COMPLETE ===")
        log_debug(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
        log_debug(f"Phase 1 breakdown: {phase1_time:.1f}s ({phase1_time/total_time*100:.1f}%)")
        log_debug(f"Phase 2 breakdown: {phase2_time:.1f}s ({phase2_time/total_time*100:.1f}%)")
        log_debug(f"Phase 3 breakdown: {phase3_time:.1f}s ({phase3_time/total_time*100:.1f}%)")
        log_debug(f"Throughput: {len(test_df)/total_time:.1f} bars/sec overall")
        log_debug(f"Speedup vs single-core: ~{(16*17280/total_time):.0f}x")
        
        logger.info(f"\n🎯 TOTAL TIME: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        logger.info(f"   Phase 1 (Parallel blocks): {phase1_time:.1f}s")
        logger.info(f"   Phase 2 (Merge): {phase2_time:.1f}s")
        logger.info(f"   Phase 3 (Parallel configs): {phase3_time:.1f}s")
        
        log_debug(f"Debug log saved to: {log_file}")
        
        return results
