"""
Signal Accumulator - Registry-Powered Sequential Confluence Builder

Accumulates signals across multiple bars until confluence threshold is met.
This enables strategies like:

Example:
    Bar 1: HOD_REJECTION fires → 20 pts → Monitoring
    Bar 5: RSI_BEARISH fires → 35 pts → Monitoring  
    Bar 11: MACD_OVERBOUGHT fires → 47 pts → ENTRY! ✅

Architecture:
- Registry-based (uses ConfluenceCalculator for points)
- ITM-compatible API (future-proof)
- Memory-efficient (auto-cleanup expired signals)
- Configurable accumulation windows

Usage:
    accumulator = SignalAccumulator(min_confluence=40, window_bars=20)
    
    for bar in bars:
        results = analyze_blocks(bar)
        should_enter, confluence, signals = accumulator.on_bar(
            bar_number=idx,
            block_results=results,
            block_configs=configs
        )
        
        if should_enter:
            enter_trade()

Author: BTC_Engine_v3
Date: 2026-01-10
Status: Production-Ready
"""

from typing import Dict, List, Tuple, Any
from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator


class SignalAccumulator:
    """
    Sequential signal accumulation with registry-based scoring
    
    Key Features:
    - Accumulates signals across multiple bars
    - Uses ConfluenceCalculator for consistent scoring
    - Auto-expires old signals (rolling window)
    - Tracks signal history for analysis
    - ITM-compatible architecture
    """
    
    def __init__(self, min_confluence: int = 40, window_bars: int = 20):
        """
        Initialize signal accumulator
        
        Args:
            min_confluence: Minimum points needed to trigger entry
            window_bars: Number of bars to keep signals active
        """
        self.min_confluence = min_confluence
        self.window_bars = window_bars
        
        # Signal memory: {unique_key: signal_data}
        self.signal_memory: Dict[str, Dict[str, Any]] = {}
        
        # Current bar tracking
        self.current_bar = 0
        
        # History tracking (for analysis/debugging)
        self.history = []
        
    def on_bar(self, 
               bar_number: int, 
               block_results: Dict[str, Dict[str, Any]], 
               block_configs: Dict[str, Dict[str, Any]]) -> Tuple[bool, int, List[str]]:
        """
        Process new bar and update signal accumulation
        
        Args:
            bar_number: Current bar index
            block_results: Dict of {block_name: {'signal': str, 'confidence': float, ...}}
            block_configs: Dict of {block_name: {'weight': int, 'enabled': bool}}
            
        Returns:
            Tuple of:
            - should_enter (bool): True if confluence threshold met
            - total_confluence (int): Current accumulated points
            - active_signals (List[str]): List of active signal descriptions
            
        Example:
            should_enter, conf, sigs = accumulator.on_bar(15, results, configs)
            if should_enter:
                print(f"Entry triggered! {conf} points from {len(sigs)} signals")
        """
        self.current_bar = bar_number
        
        # Process new signals from this bar
        new_signals_added = self._process_new_signals(bar_number, block_results, block_configs)
        
        # Cleanup expired signals (outside window)
        expired_count = self._cleanup_expired_signals()
        
        # Calculate current total confluence
        total_confluence = sum(s['points'] for s in self.signal_memory.values())
        
        # Build active signal descriptions
        active_signals = self._build_signal_descriptions()
        
        # Check if threshold met
        should_enter = total_confluence >= self.min_confluence
        
        # Track history (for debugging/analysis)
        self.history.append({
            'bar': bar_number,
            'new_signals': new_signals_added,
            'expired': expired_count,
            'total_confluence': total_confluence,
            'active_count': len(self.signal_memory),
            'threshold_met': should_enter
        })
        
        return should_enter, total_confluence, active_signals
    
    def _process_new_signals(self, 
                            bar_number: int,
                            block_results: Dict[str, Dict[str, Any]],
                            block_configs: Dict[str, Dict[str, Any]]) -> int:
        """
        Add new signals from current bar to memory
        
        Returns:
            Number of new signals added
        """
        added_count = 0
        
        for block_name, result in block_results.items():
            # Skip if block not in configs or disabled
            if block_name not in block_configs:
                continue
            
            if not block_configs[block_name].get('enabled', True):
                continue
            
            # Extract signal info
            signal = result.get('signal', '')
            confidence = result.get('confidence', 0)
            
            # Skip non-signals
            if signal in ['NO_SIGNAL', 'ERROR', 'NEUTRAL', 'INSUFFICIENT_DATA', '']:
                continue
            
            # Calculate points using ConfluenceCalculator (registry-based!)
            weight = block_configs[block_name].get('weight', 20)
            
            try:
                points = ConfluenceCalculator.calculate_points(
                    block_name=block_name,
                    signal=signal,
                    confidence=confidence,
                    weight=weight
                )
            except Exception as e:
                # If ConfluenceCalculator fails, log but don't crash
                # (defensive programming)
                print(f"Warning: Failed to calculate points for {block_name}: {e}")
                points = 0
            
            # Only add if points > 0
            if points > 0:
                # Create unique key (allows same block to fire multiple times)
                unique_key = f"{block_name}_{signal}_{bar_number}"
                
                self.signal_memory[unique_key] = {
                    'block': block_name,
                    'signal': signal,
                    'confidence': confidence,
                    'points': points,
                    'bar': bar_number,
                    'weight': weight
                }
                
                added_count += 1
        
        return added_count
    
    def _cleanup_expired_signals(self) -> int:
        """
        Remove signals outside accumulation window
        
        Returns:
            Number of signals removed
        """
        cutoff_bar = self.current_bar - self.window_bars
        
        # Find expired signal keys
        expired_keys = [
            key for key, data in self.signal_memory.items()
            if data['bar'] < cutoff_bar
        ]
        
        # Remove them
        for key in expired_keys:
            del self.signal_memory[key]
        
        return len(expired_keys)
    
    def _build_signal_descriptions(self) -> List[str]:
        """
        Build human-readable descriptions of active signals
        
        Returns:
            List of signal descriptions
            
        Example:
            [
                "hod_0: HOD_REJECTION (95% → +20 pts) [Bar 1]",
                "rsi: BEARISH_DIVERGENCE (85% → +15 pts) [Bar 5]"
            ]
        """
        descriptions = []
        
        # Sort by bar number (oldest first)
        sorted_signals = sorted(
            self.signal_memory.items(),
            key=lambda x: x[1]['bar']
        )
        
        for key, data in sorted_signals:
            desc = (
                f"{data['block']}: {data['signal']} "
                f"({data['confidence']}% → +{data['points']} pts) "
                f"[Bar {data['bar']}]"
            )
            descriptions.append(desc)
        
        return descriptions
    
    def reset(self):
        """
        Clear all accumulated signals and history
        
        Use this when:
        - Trade is entered (start fresh for next setup)
        - Strategy is restarted
        - Testing new configuration
        """
        self.signal_memory.clear()
        self.history.clear()
    
    def get_active_signals(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current active signals
        
        Returns:
            Dictionary of active signals
        """
        return self.signal_memory.copy()
    
    def get_confluence_breakdown(self) -> Dict[str, int]:
        """
        Get confluence points by block
        
        Returns:
            Dict of {block_name: total_points}
            
        Useful for analysis/debugging
        """
        breakdown = {}
        
        for data in self.signal_memory.values():
            block = data['block']
            points = data['points']
            
            if block in breakdown:
                breakdown[block] += points
            else:
                breakdown[block] = points
        
        return breakdown
    
    def get_history_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics from history
        
        Returns:
            Dict with stats like max_confluence, bars_active, etc.
        """
        if not self.history:
            return {
                'total_bars': 0,
                'max_confluence': 0,
                'threshold_met_count': 0,
                'signals_added': 0,
                'signals_expired': 0
            }
        
        return {
            'total_bars': len(self.history),
            'max_confluence': max(h['total_confluence'] for h in self.history),
            'threshold_met_count': sum(1 for h in self.history if h['threshold_met']),
            'signals_added': sum(h['new_signals'] for h in self.history),
            'signals_expired': sum(h['expired'] for h in self.history),
            'avg_active_signals': sum(h['active_count'] for h in self.history) / len(self.history)
        }
    
    def __repr__(self):
        """String representation for debugging"""
        total = sum(s['points'] for s in self.signal_memory.values())
        active = len(self.signal_memory)
        
        return (
            f"SignalAccumulator(confluence={total}/{self.min_confluence}, "
            f"active_signals={active}, window={self.window_bars})"
        )
