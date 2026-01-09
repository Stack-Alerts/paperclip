"""
Building Blocks Catalog

Complete catalog of all 80 building blocks with metadata.
Used for validation and intelligent weight optimization.
"""

BUILDING_BLOCK_CATALOG = {
    # Moving Averages (7)
    'ema_20_50_cross': {'category': 'moving_averages', 'type': 'SIGNAL', 'weight_range': (15, 30)},
    'ema_20_50_trend': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (10, 20)},
    'ema_50_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'ema_55_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'ema_200_trend': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'ema_255_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (5, 12)},
    'ema_800_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (5, 10)},
    
    # Oscillators (3)
    'macd_signal': {'category': 'oscillators', 'type': 'SIGNAL', 'weight_range': (15, 25)},
    'rsi_divergence': {'category': 'oscillators', 'type': 'EVENT', 'weight_range': (20, 30)},
    'stochastic_rsi': {'category': 'oscillators', 'type': 'SIGNAL', 'weight_range': (12, 22)},
    
    # Price Action (4)
    'order_block': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (18, 25)},
    'fair_value_gap': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (15, 22)},
    'liquidity_sweep': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (18, 25)},
    'breaker_block': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (15, 22)},
    
    # Patterns (20)
    'double_top': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 35)},
    'double_bottom': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 35)},
    'triple_top': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (18, 30)},
    'triple_bottom': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (18, 30)},
    'head_shoulders': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 32)},
    'inverse_head_shoulders': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 32)},
    'cup_handle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (15, 25)},
    'rounding_bottom': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (15, 25)},
    'flag_pattern': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
    'pennant_pattern': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
    'symmetrical_triangle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (14, 24)},
    'ascending_triangle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (14, 24)},
    'descending_triangle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (14, 24)},
    'falling_wedge': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
    'rising_wedge': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
    'three_bar_reversal': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (10, 18)},
    'candle_2_close': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (8, 15)},
    'internal_pivot': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (10, 18)},
    'swing_breakout': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 20)},
    'initial_balance_breakout': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 20)},
    
    # Price Levels (6)
    'hod': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (15, 25)},
    'how': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (12, 22)},
    'lod': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (15, 25)},
    'low': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (12, 22)},
    'asia_50': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (12, 22)},
    'us_settlement': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    
    # SMC/ICT (9)
    'break_of_structure': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (18, 25)},
    'market_structure_shift': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (20, 28)},
    'displacement': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (12, 20)},
    'inducement': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (15, 22)},
    'optimal_trade_entry': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (18, 25)},
    'swing_failure_pattern': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (15, 22)},
    'change_of_character': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (12, 20)},
    'mitigation_block': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (12, 18)},
    'balanced_price_range': {'category': 'smc_ict', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    
    # Institutional (5)
    'vwap': {'category': 'institutional', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'anchored_vwap': {'category': 'institutional', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'ema_crossover': {'category': 'institutional', 'type': 'SIGNAL', 'weight_range': (12, 20)},
    'market_depth': {'category': 'institutional', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'order_flow_imbalance': {'category': 'institutional', 'type': 'EVENT', 'weight_range': (10, 18)},
    
    # Sessions (2)
    'kill_zones': {'category': 'sessions', 'type': 'CONTEXT', 'weight_range': (12, 20)},
    'session_time': {'category': 'sessions', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    
    # Market Structure (6)
    'premium_discount_zones': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'range_liquidity': {'category': 'market_structure', 'type': 'EVENT', 'weight_range': (10, 18)},
    'swing_points': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (12, 18)},
    'liquidity': {'category': 'market_structure', 'type': 'EVENT', 'weight_range': (12, 18)},
    'power_hour_trends': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'wave_consolidation': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    
    # Supply/Demand (1)
    'supply_demand_zones': {'category': 'supply_demand', 'type': 'EVENT', 'weight_range': (12, 20)},
    
    # Fibonacci (1)
    'fibonacci_retracements': {'category': 'fibonacci', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    
    # Signals (4)
    'macd_price_forecasting': {'category': 'signals', 'type': 'HYBRID', 'weight_range': (10, 18)},
    'adaptive_momentum_oscillator': {'category': 'signals', 'type': 'HYBRID', 'weight_range': (10, 18)},
    'ict_silver_bullet': {'category': 'signals', 'type': 'EVENT', 'weight_range': (15, 22)},
    'asfx_a2_vwap': {'category': 'signals', 'type': 'SIGNAL', 'weight_range': (10, 18)},
    
    # Trend/Momentum (2)
    'ichimoku_cloud': {'category': 'trend_momentum', 'type': 'HYBRID', 'weight_range': (12, 20)},
    'adx': {'category': 'trend_momentum', 'type': 'HYBRID', 'weight_range': (15, 22)},
    
    # Volatility (3)
    'atr': {'category': 'volatility', 'type': 'CONTEXT', 'weight_range': (0, 0)},
    'adr': {'category': 'volatility', 'type': 'CONTEXT', 'weight_range': (5, 12)},
    'bollinger_bands': {'category': 'volatility', 'type': 'SIGNAL', 'weight_range': (10, 18)},
    
    # Risk Management (1)
    'trailing_stop': {'category': 'risk_management', 'type': 'CONTEXT', 'weight_range': (0, 0)},
}


def get_weight_presets_for_blocks(block_keys: list) -> list:
    """
    Generate optimized weight presets based on block types
    
    Args:
        block_keys: List of block keys used in strategy
    
    Returns:
        List of weight configurations to test
    """
    presets = []
    
    # Categorize blocks
    event_blocks = []
    signal_blocks = []
    context_blocks = []
    
    for key in block_keys:
        if key in BUILDING_BLOCK_CATALOG:
            block_type = BUILDING_BLOCK_CATALOG[key]['type']
            if block_type == 'EVENT':
                event_blocks.append(key)
            elif block_type == 'SIGNAL':
                signal_blocks.append(key)
            else:
                context_blocks.append(key)
    
    # Preset 1: Balanced
    balanced = {}
    for key in block_keys:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            balanced[key] = (min_w + max_w) // 2
        else:
            balanced[key] = 15
    presets.append(balanced)
    
    # Preset 2: Event-Heavy
    event_heavy = balanced.copy()
    for key in event_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            _, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            event_heavy[key] = max_w
    for key in context_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, _ = BUILDING_BLOCK_CATALOG[key]['weight_range']
            event_heavy[key] = min_w
    presets.append(event_heavy)
    
    # Preset 3: Context-Heavy
    context_heavy = balanced.copy()
    for key in context_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            _, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            context_heavy[key] = max_w
    for key in event_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, _ = BUILDING_BLOCK_CATALOG[key]['weight_range']
            context_heavy[key] = min_w
    presets.append(context_heavy)
    
    # Preset 4: Conservative
    conservative = {}
    for key in block_keys:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            conservative[key] = min_w + (max_w - min_w) // 3
        else:
            conservative[key] = 12
    presets.append(conservative)
    
    return presets