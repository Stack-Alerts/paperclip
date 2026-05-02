"""
Test Scenarios for Backtest Configuration Coverage

NAUTILUS EXPERT: Defines test scenarios using orthogonal array testing
to achieve comprehensive coverage with minimal test count.

Uses pairwise coverage to ensure every parameter combination is tested
at least once, while avoiding exhaustive testing of all permutations.

Author: BTC_Engine_v3
Date: February 2026
"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class BacktestScenario:
    """
    Single backtest configuration scenario
    
    Attributes:
        id: Unique scenario identifier
        description: Human-readable description
        config: Configuration parameters for backtest
        expected_behavior: Expected results to validate
    """
    id: str
    description: str
    config: Dict[str, Any]
    expected_behavior: Dict[str, Any]


# ============================================================================
# CRITICAL PATH SCENARIOS
# ============================================================================
# These test the most important combinations used in production

CRITICAL_SCENARIOS = [
    BacktestScenario(
        id="CRITICAL_001",
        description="Fibonacci + Adaptive Balanced (Default Production Config)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': True,  # Adaptive should update SL
        }
    ),
    
    BacktestScenario(
        id="CRITICAL_002",
        description="Hybrid + Adaptive Balanced",
        config={
            'tpsl_mode': 'Hybrid',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': True,
        }
    ),
    
    BacktestScenario(
        id="CRITICAL_003",
        description="Fixed % + Adaptive Balanced",
        config={
            'tpsl_mode': 'Fixed',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': True,
        }
    ),
    
    BacktestScenario(
        id="CRITICAL_004",
        description="Fibonacci + Static SL (No Adaptation)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Static',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': False,  # Static = no SL updates
        }
    ),
    
    BacktestScenario(
        id="CRITICAL_005",
        description="Fibonacci + Adaptive Conservative (Wider SLs)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Conservative',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'sl_delay': 3,  # Longer delay
            'emergency_sl': 3,  # Wider emergency
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': True,
        }
    ),
    
    BacktestScenario(
        id="CRITICAL_006",
        description="Fibonacci + Adaptive Aggressive (Tighter SLs)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Aggressive',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'sl_delay': 1,  # Minimal delay
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': True,
            'higher_sl_exits': True,  # Aggressive = more SL hits
        }
    ),
    
    BacktestScenario(
        id="CRITICAL_007",
        description="Hybrid + Static SL",
        config={
            'tpsl_mode': 'Hybrid',
            'sl_adjustment': 'Static',
            'risk_pct': 5,  # Lower risk
            'leverage': 5,  # Lower leverage
            'max_bars_held': 200,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': False,
        }
    ),
    
    BacktestScenario(
        id="CRITICAL_008",
        description="Fixed % + Static SL (Simplest Config)",
        config={
            'tpsl_mode': 'Fixed',
            'sl_adjustment': 'Static',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
            'no_stuck_trades': True,
            'sl_adjustments': False,
        }
    ),
]


# ============================================================================
# EDGE CASE SCENARIOS
# ============================================================================
# These test boundary conditions and unusual configurations

EDGE_SCENARIOS = [
    BacktestScenario(
        id="EDGE_001",
        description="Max Bars Held Hit (Very Short Time Limit)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Static',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 5,  # Very short - should hit time limit
        },
        expected_behavior={
            'min_trades': 5,
            'time_limit_exits': True,  # Should have MAX_BARS exits
        }
    ),
    
    BacktestScenario(
        id="EDGE_002",
        description="Aggressive Preset with Minimal Delay",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Aggressive',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'sl_delay': 1,  # Minimal delay - SL activates fast
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'higher_sl_exits': True,  # Tighter SL = more SL hits
        }
    ),
    
    BacktestScenario(
        id="EDGE_003",
        description="Conservative Preset with Maximum Delay",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Conservative',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'sl_delay': 3,  # Maximum delay
            'emergency_sl': 3,  # Widest emergency
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
        }
    ),
    
    BacktestScenario(
        id="EDGE_004",
        description="Low Risk + Low Leverage (Conservative Risk Profile)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 5,  # Low risk
            'leverage': 5,  # Low leverage
            'max_bars_held': 200,
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
        }
    ),
    
    BacktestScenario(
        id="EDGE_005",
        description="High Risk + High Leverage (Aggressive Risk Profile)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,  # High risk
            'leverage': 10,  # High leverage
            'max_bars_held': 200,
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
        }
    ),
]


# ============================================================================
# PARAMETER VARIATION SCENARIOS - INSTITUTIONAL GRADE
# ============================================================================
# These test EACH parameter with at least 2 values to verify parameters
# are properly passed through the system and affect results.
# CRITICAL: Ensures parameter wiring is correct.

PARAMETER_VARIATION_SCENARIOS = [
    # VOLATILITY LOOKBACK (10 vs 30 bars)
    BacktestScenario(
        id="PARAM_VOL_LB_LOW",
        description="Volatility Lookback = 10 bars",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'adaptive_sl': {
                'enabled': True,
                'delay_enabled': True,
                'delay_bars': 2,
                'emergency_sl_pct': 2,
                'volatility_lookback': 10,  # TEST
                'volatility_multiplier': 1.2,
                'min_sl_pct': 0.7,
                'max_sl_pct': 2.0,
            }
        },
        expected_behavior={'min_trades': 10, 'tp_exits': True, 'sl_exits': True}
    ),
    BacktestScenario(
        id="PARAM_VOL_LB_HIGH",
        description="Volatility Lookback = 30 bars",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'adaptive_sl': {
                'enabled': True,
                'delay_enabled': True,
                'delay_bars': 2,
                'emergency_sl_pct': 2,
                'volatility_lookback': 30,  # TEST
                'volatility_multiplier': 1.2,
                'min_sl_pct': 0.7,
                'max_sl_pct': 2.0,
            }
        },
        expected_behavior={'min_trades': 10, 'tp_exits': True, 'sl_exits': True}
    ),
    
    # VOLATILITY MULTIPLIER (1.0x vs 1.8x)
    BacktestScenario(
        id="PARAM_VOL_MULTI_TIGHT",
        description="Volatility Multiplier = 1.0x (Tight SL)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'adaptive_sl': {
                'enabled': True,
                'delay_enabled': True,
                'delay_bars': 2,
                'emergency_sl_pct': 2,
                'volatility_lookback': 20,
                'volatility_multiplier': 1.0,  # TEST
                'min_sl_pct': 0.7,
                'max_sl_pct': 2.0,
            }
        },
        expected_behavior={'min_trades': 10, 'higher_sl_exits': True}
    ),
    BacktestScenario(
        id="PARAM_VOL_MULTI_LOOSE",
        description="Volatility Multiplier = 1.8x (Loose SL)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'adaptive_sl': {
                'enabled': True,
                'delay_enabled': True,
                'delay_bars': 2,
                'emergency_sl_pct': 2,
                'volatility_lookback': 20,
                'volatility_multiplier': 1.8,  # TEST
                'min_sl_pct': 0.7,
                'max_sl_pct': 2.0,
            }
        },
        expected_behavior={'min_trades': 10, 'tp_exits': True, 'sl_exits': True}
    ),
    
    # MIN/MAX STOP LOSS (0.6%/1.2% and 1.0%/2.5%)
    BacktestScenario(
        id="PARAM_SL_RANGE_TIGHT",
        description="SL Range: Min=0.6%, Max=1.0% (Tight)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'adaptive_sl': {
                'enabled': True,
                'delay_enabled': True,
                'delay_bars': 2,
                'emergency_sl_pct': 2,
                'volatility_lookback': 20,
                'volatility_multiplier': 1.2,
                'min_sl_pct': 0.6,  # TEST
                'max_sl_pct': 1.0,  # TEST
            }
        },
        expected_behavior={'min_trades': 10, 'higher_sl_exits': True}
    ),
    BacktestScenario(
        id="PARAM_SL_RANGE_LOOSE",
        description="SL Range: Min=1.2%, Max=2.5% (Loose)",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'adaptive_sl': {
                'enabled': True,
                'delay_enabled': True,
                'delay_bars': 2,
                'emergency_sl_pct': 2,
                'volatility_lookback': 20,
                'volatility_multiplier': 1.2,
                'min_sl_pct': 1.2,  # TEST
                'max_sl_pct': 2.5,  # TEST
            }
        },
        expected_behavior={'min_trades': 10, 'tp_exits': True, 'sl_exits': True}
    ),
    
    # MIN RISK:REWARD (1.5 vs 2.5)
    BacktestScenario(
        id="PARAM_MIN_RR_LOW",
        description="Min Risk:Reward = 1.5",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'min_risk_reward': 1.5,  # TEST
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={'min_trades': 5, 'tp_exits': True}
    ),
    BacktestScenario(
        id="PARAM_MIN_RR_HIGH",
        description="Min Risk:Reward = 2.5",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'min_risk_reward': 2.5,  # TEST
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={'min_trades': 3, 'tp_exits': True}
    ),
    
    # STARTING CAPITAL ($5k vs $25k)
    BacktestScenario(
        id="PARAM_CAPITAL_LOW",
        description="Starting Capital = $5,000",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'starting_capital': 5000,  # TEST
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={'min_trades': 10, 'tp_exits': True}
    ),
    BacktestScenario(
        id="PARAM_CAPITAL_HIGH",
        description="Starting Capital = $25,000",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 10,
            'leverage': 10,
            'max_bars_held': 200,
            'starting_capital': 25000,  # TEST
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={'min_trades': 10, 'tp_exits': True}
    ),
]


# ============================================================================
# PAIRWISE SCENARIO GENERATION
# ============================================================================

def generate_pairwise_scenarios() -> List[BacktestScenario]:
    """
    Generate additional scenarios using pairwise testing
    
    Ensures every pair of parameters is tested at least once,
    providing comprehensive coverage without exhaustive testing.
    
    Uses allpairspy library for pairwise combination generation.
    
    Returns:
        List of BacktestScenario objects
    """
    try:
        from allpairspy import AllPairs
    except ImportError:
        # If allpairspy not installed, return minimal pairwise scenarios manually
        print("Warning: allpairspy not installed. Using manual pairwise scenarios.")
        return _generate_manual_pairwise()
    
    # Define parameter space for pairwise testing
    parameters = [
        ['Fibonacci', 'Hybrid', 'Fixed'],  # TP/SL mode
        ['Adaptive v2.0', 'Static'],  # SL adjustment
        [5, 10],  # Risk %
        [5, 10],  # Leverage
        [50, 200],  # Max bars
    ]
    
    scenarios = []
    
    for i, combination in enumerate(AllPairs(parameters)):
        tpsl_mode = combination[0]
        sl_adj = combination[1]
        risk = combination[2]
        leverage = combination[3]
        max_bars = combination[4]
        
        # Determine adaptive preset if Adaptive enabled
        adaptive_preset = None
        sl_delay = 2
        emergency_sl = 2
        
        if sl_adj == 'Adaptive v2.0':
            # Cycle through presets for variety
            presets = ['Conservative', 'Balanced', 'Aggressive']
            adaptive_preset = presets[i % len(presets)]
            
            # Vary delay and emergency based on preset
            if adaptive_preset == 'Conservative':
                sl_delay = 3
                emergency_sl = 3
            elif adaptive_preset == 'Aggressive':
                sl_delay = 1
                emergency_sl = 2
            else:  # Balanced
                sl_delay = 2
                emergency_sl = 2
        
        # Build config
        config = {
            'tpsl_mode': tpsl_mode,
            'sl_adjustment': sl_adj,
            'risk_pct': risk,
            'leverage': leverage,
            'max_bars_held': max_bars,
        }
        
        if adaptive_preset:
            config['adaptive_preset'] = adaptive_preset
            config['sl_delay'] = sl_delay
            config['emergency_sl'] = emergency_sl
        
        # Create scenario
        scenarios.append(BacktestScenario(
            id=f"PAIRWISE_{i+1:03d}",
            description=f"Pairwise: {tpsl_mode}/{sl_adj}/{risk}%/{leverage}x/{max_bars}bars",
            config=config,
            expected_behavior={
                'min_trades': 5,  # Lower threshold for pairwise tests
                'tp_exits': True,
                'sl_exits': True,
                'no_stuck_trades': True,
            }
        ))
    
    return scenarios


def _generate_manual_pairwise() -> List[BacktestScenario]:
    """
    Manual pairwise scenarios when allpairspy is not available
    
    Returns minimal set that covers key combinations.
    """
    return [
        BacktestScenario(
            id="PAIRWISE_001",
            description="Fibonacci/Adaptive/10%/10x/200bars",
            config={
                'tpsl_mode': 'Fibonacci',
                'sl_adjustment': 'Adaptive v2.0',
                'adaptive_preset': 'Balanced',
                'risk_pct': 10,
                'leverage': 10,
                'max_bars_held': 200,
                'sl_delay': 2,
                'emergency_sl': 2,
            },
            expected_behavior={'min_trades': 5, 'tp_exits': True, 'sl_exits': True}
        ),
        BacktestScenario(
            id="PAIRWISE_002",
            description="Hybrid/Static/5%/5x/50bars",
            config={
                'tpsl_mode': 'Hybrid',
                'sl_adjustment': 'Static',
                'risk_pct': 5,
                'leverage': 5,
                'max_bars_held': 50,
            },
            expected_behavior={'min_trades': 5, 'tp_exits': True, 'sl_exits': True}
        ),
        BacktestScenario(
            id="PAIRWISE_003",
            description="Fixed/Adaptive/5%/10x/200bars",
            config={
                'tpsl_mode': 'Fixed',
                'sl_adjustment': 'Adaptive v2.0',
                'adaptive_preset': 'Aggressive',
                'risk_pct': 5,
                'leverage': 10,
                'max_bars_held': 200,
                'sl_delay': 1,
                'emergency_sl': 2,
            },
            expected_behavior={'min_trades': 5, 'tp_exits': True, 'sl_exits': True}
        ),
        BacktestScenario(
            id="PAIRWISE_004",
            description="Fibonacci/Static/10%/5x/50bars",
            config={
                'tpsl_mode': 'Fibonacci',
                'sl_adjustment': 'Static',
                'risk_pct': 10,
                'leverage': 5,
                'max_bars_held': 50,
            },
            expected_behavior={'min_trades': 5, 'tp_exits': True, 'sl_exits': True}
        ),
        BacktestScenario(
            id="PAIRWISE_005",
            description="Hybrid/Adaptive/10%/5x/200bars",
            config={
                'tpsl_mode': 'Hybrid',
                'sl_adjustment': 'Adaptive v2.0',
                'adaptive_preset': 'Conservative',
                'risk_pct': 10,
                'leverage': 5,
                'max_bars_held': 200,
                'sl_delay': 3,
                'emergency_sl': 3,
            },
            expected_behavior={'min_trades': 5, 'tp_exits': True, 'sl_exits': True}
        ),
        BacktestScenario(
            id="PAIRWISE_006",
            description="Fixed/Static/5%/10x/50bars",
            config={
                'tpsl_mode': 'Fixed',
                'sl_adjustment': 'Static',
                'risk_pct': 5,
                'leverage': 10,
                'max_bars_held': 50,
            },
            expected_behavior={'min_trades': 5, 'tp_exits': True, 'sl_exits': True}
        ),
    ]
