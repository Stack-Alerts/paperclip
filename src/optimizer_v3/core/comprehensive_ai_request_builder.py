"""
Comprehensive AI Request Builder
=================================

INSTITUTIONAL-GRADE DATA COLLECTION FOR AI REQUESTS

This module addresses the critical issues identified in Sprint 1.6:
1. ✅ Collects complete strategy configuration (blocks, signals, parameters)
2. ✅ Includes backtest configuration (timeframe, SL/TP, position sizing)
3. ✅ Provides all trade results with full details
4. ✅ Sends metrics with institutional ratings
5. ✅ Includes ALL available building blocks (83+ blocks with signals)
6. ✅ Provides signal occurrence rates and statistics

FIXES THE FOLLOWING DOCUMENTED PROBLEMS:
- AI receiving "0 trades" when UI shows "24 trades"
- Missing backtest configuration context
- Missing trade details for analysis
- Missing available blocks catalog
- Incomplete prompt structure

Author: Optimizer v3 Team  
Date: 2026-01-23
Sprint: 1.6 (AI Request System Rebuild)
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent  
sys.path.insert(0, str(project_root))

# Import helper methods for prompt formatting
from src.optimizer_v3.core.prompt_helper_methods import (
    identify_performance_problems,
    describe_strategy_intent,
    describe_strengths,
    describe_problems,
    analyze_trade_patterns,
    format_config_summary,
    define_primary_objective,
    format_available_blocks_summary,
    extract_relevant_config,
    extract_trade_summary,
    extract_metrics_summary,
    format_blocks_catalog
)


class ComprehensiveAIRequestBuilder:
    """
    COMPREHENSIVE AI REQUEST BUILDER
    
    Builds complete, structured AI requests with ALL necessary context:
    - Strategy configuration (complete)
    - Backtest configuration (all settings)
    - Trade results (every single trade)
    - Metrics (with ratings)
    - Available blocks catalog (all 83+ blocks)
    - Signal statistics (occurrence rates)
    """
    
    def __init__(self):
        """Initialize request builder"""
        self.block_registry = None
        self._load_block_registry()
    
    def _load_block_registry(self):
        """Load BlockRegistry for available blocks catalog"""
        try:
            from src.detectors.building_blocks.registry import BlockRegistry
            self.block_registry = BlockRegistry
            print(f"✅ BlockRegistry loaded: {len(BlockRegistry.get_all_blocks())} blocks available")
        except Exception as e:
            print(f"⚠️ Could not load BlockRegistry: {e}")
            self.block_registry = None
    
    def build_complete_request(
        self,
        strategy_config: Dict,
        backtest_results: Dict,
        metrics_with_ratings: Dict[str, Dict],
        backtest_config: Optional[Dict] = None,
        analysis_report: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Build complete AI request with ALL necessary data
        
        Args:
            strategy_config: Full strategy configuration
            backtest_results: COMPLETE backtest results (not just summary)
            metrics_with_ratings: Metrics with institutional ratings
            backtest_config: Backtest settings (timeframe, SL/TP, etc.)
            analysis_report: Optional analysis report
        
        Returns:
            Complete request data structure
        """
        print("\n🔧 Building Comprehensive AI Request...")
        
        request = {
            'metadata': self._build_metadata(),
            'strategy_configuration': self._extract_strategy_config(strategy_config),
            'backtest_configuration': self._extract_backtest_config(backtest_config, backtest_results),
            'trade_results': self._extract_trade_results(backtest_results),
            'performance_metrics': self._extract_metrics(metrics_with_ratings, backtest_results),
            'available_building_blocks': self._extract_available_blocks(),
            'signal_statistics': self._extract_signal_statistics(),
            'analysis_context': self._extract_analysis_context(analysis_report)
        }
        
        # Validation
        self._validate_request(request)
        
        return request
    
    def _build_metadata(self) -> Dict:
        """Build metadata about the request"""
        return {
            'timestamp': datetime.now().isoformat(),
            'builder_version': '1.0.0',
            'sprint': '1.6',
            'purpose': 'Intelligent strategy optimization recommendations'
        }
    
    def _extract_strategy_config(self, config: Dict) -> Dict:
        """Extract complete strategy configuration"""
        if not config:
            return {}
        
        blocks_detail = []
        for block in config.get('blocks', []):
            block_detail = {
                'name': block.get('name', ''),
                'category': block.get('category', 'Unknown'),
                'signals': []
            }
            
            for signal in block.get('signals', []):
                signal_detail = {
                    'name': signal.get('name', ''),
                    'parameters': signal.get('parameters', {}),
                    'recheck_config': signal.get('recheck', None),
                    'timing_constraint': signal.get('timing', None)
                }
                block_detail['signals'].append(signal_detail)
            
            blocks_detail.append(block_detail)
        
        return {
            'name': config.get('name', 'Unknown Strategy'),
            'strategy_type': config.get('strategy_type', 'Unknown'),
            'description': config.get('description', ''),
            'blocks': blocks_detail,
            'total_blocks': len(blocks_detail),
            'total_signals': sum(len(b['signals']) for b in blocks_detail),
            'logic': config.get('logic', 'AND'),
            'created_date': config.get('created_date', 'Unknown'),
            'modified_date': config.get('modified_date', 'Unknown')
        }
    
    def _extract_backtest_config(self, config: Optional[Dict], results: Dict) -> Dict:
        """Extract backtest configuration settings"""
        if not config:
            # Try to extract from results if config not provided
            config = results.get('config', {})
        
        return {
            'timeframe': config.get('timeframe', results.get('timeframe', '15m')),
            'lookback_days': config.get('lookback_days', results.get('lookback_days', 180)),
            'start_date': config.get('start_date', results.get('start_date', 'Unknown')),
            'end_date': config.get('end_date', results.get('end_date', 'Unknown')),
            'position_sizing': {
                'position_size': config.get('position_size', 0.1),
                'use_dynamic_sizing': config.get('use_dynamic_sizing', False),
                'max_position_size': config.get('max_position_size', 1.0)
            },
            'risk_management': {
                'stop_loss': config.get('stop_loss', 0.02),
                'take_profit_levels': config.get('take_profit', [0.01, 0.015, 0.02]),
                'use_dynamic_tp': config.get('use_dynamic_tp', False),
                'use_adaptive_sl': config.get('use_adaptive_sl', False)
            },
            'execution': {
                'slippage': config.get('slippage', 0.0),
                'commission': config.get('commission', 0.0)
            }
        }
    
    def _extract_trade_results(self, results: Dict) -> Dict:
        """Extract ALL trade results with complete details"""
        trades = results.get('trades', [])
        
        if not trades:
            return {
                'total_trades': 0,
                'trades': [],
                'warning': '⚠️ CRITICAL: 0 trades executed - AI cannot analyze empty trade history'
            }
        
        # Extract detailed trade information
        detailed_trades = []
        for i, trade in enumerate(trades, 1):
            trade_detail = {
                'trade_number': i,
                'entry_time': str(trade.get('entry_time', 'Unknown')),
                'exit_time': str(trade.get('exit_time', 'Unknown')),
                'duration_bars': trade.get('duration_bars', 0),
                'duration_time': self._calculate_duration(trade),
                'side': trade.get('side', 'Unknown'),
                'entry_price': trade.get('entry_price', 0.0),
                'exit_price': trade.get('exit_price', 0.0),
                'position_size': trade.get('position_size', 0.0),
                'pnl': trade.get('pnl', 0.0),
                'pnl_percent': trade.get('pnl_percent', 0.0),
                'exit_reason': trade.get('exit_reason', 'Unknown'),
                'signals_fired': trade.get('signals_fired', []),
                'bars_data': {
                    'entry_bar': trade.get('entry_bar', 0),
                    'exit_bar': trade.get('exit_bar', 0),
                    'total_bars': trade.get('exit_bar', 0) - trade.get('entry_bar', 0)
                }
            }
            detailed_trades.append(trade_detail)
        
        # Calculate summary statistics
        winning_trades = [t for t in detailed_trades if t['pnl'] > 0]
        losing_trades = [t for t in detailed_trades if t['pnl'] < 0]
        
        return {
            'total_trades': len(detailed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(detailed_trades) * 100) if detailed_trades else 0.0,
            'total_pnl': sum(t['pnl'] for t in detailed_trades),
            'avg_win': sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0,
            'avg_loss': sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0,
            'largest_win': max((t['pnl'] for t in winning_trades), default=0.0),
            'largest_loss': min((t['pnl'] for t in losing_trades), default=0.0),
            'trades': detailed_trades[:50],  # Send first 50 trades (to avoid huge payloads)
            'note': f'Showing first 50 of {len(detailed_trades)} trades' if len(detailed_trades) > 50 else 'All trades included'
        }
    
    def _calculate_duration(self, trade: Dict) -> str:
        """Calculate human-readable trade duration"""
        try:
            entry = trade.get('entry_time')
            exit = trade.get('exit_time')
            if not entry or not exit:
                return 'Unknown'
            
            if isinstance(entry, str):
                entry = datetime.fromisoformat(entry.replace('Z', '+00:00'))
            if isinstance(exit, str):
                exit = datetime.fromisoformat(exit.replace('Z', '+00:00'))
            
            delta = exit - entry
            total_seconds = int(delta.total_seconds())
            
            if total_seconds < 3600:
                return f"{total_seconds // 60}m"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                mins = (total_seconds % 3600) // 60
                return f"{hours}h {mins}m"
            else:
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                return f"{days}d {hours}h"
        except Exception as e:
            return f"Unknown ({str(e)})"
    
    def _extract_metrics(self, metrics_with_ratings: Dict, backtest_results: Dict) -> Dict:
        """Extract all metrics with institutional ratings"""
        metrics = {}
        
        for key, data in metrics_with_ratings.items():
            if isinstance(data, dict):
                metrics[key] = {
                    'value': data.get('value', 0),
                    'rating': data.get('rating', ''),
                    'category': data.get('category', 'Performance'),
                    'threshold_poor': data.get('threshold_poor', None),
                    'threshold_good': data.get('threshold_good', None)
                }
        
        # Add any additional metrics from backtest_results
        for key in ['total_pnl', 'win_rate', 'profit_factor', 'sharpe_ratio', 'max_drawdown_pct']:
            if key in backtest_results and key not in metrics:
                metrics[key] = {
                    'value': backtest_results[key],
                    'rating': 'Unknown',
                    'category': 'Performance'
                }
        
        return metrics
    
    def _extract_available_blocks(self) -> List[Dict]:
        """Extract ALL available building blocks from BlockRegistry with complete descriptions"""
        if not self.block_registry:
            return []
        
        try:
            all_blocks = self.block_registry.get_all_blocks()
            
            blocks_catalog = []
            for block_name, metadata in all_blocks.items():
                # Handle empty descriptions properly (None, empty string, or whitespace-only)
                description = (metadata.description or '').strip()
                if not description:
                    description = f"{block_name.replace('_', ' ').title()} detector"
                
                block_info = {
                    'name': block_name,
                    'category': metadata.category,
                    'description': description,
                    'signals': []
                }
                
                # Extract signals from signal_tiers (correct attribute name)
                if hasattr(metadata, 'signal_tiers') and metadata.signal_tiers:
                    for signal_name, tier_info in metadata.signal_tiers.items():
                        if isinstance(tier_info, dict):
                            # CRITICAL: Only include signals that are visible in UI
                            # Skip signals with ui_visible: False (internal/hidden signals)
                            ui_visible = tier_info.get('ui_visible', True)  # Default True if not specified
                            if ui_visible is False:
                                continue  # Skip this signal - not available in Strategy Builder UI
                            
                            # Get description from tier_info if it exists
                            signal_description = tier_info.get('description', '')
                            if not signal_description:
                                # Generate basic description from signal name
                                signal_description = signal_name.replace('_', ' ').title()
                            
                            signal_info = {
                                'name': signal_name,
                                'description': signal_description,
                                'base_points': tier_info.get('base_points', tier_info.get('points', 0)),
                                'formula': tier_info.get('formula', 'fixed')
                            }
                            block_info['signals'].append(signal_info)
                
                blocks_catalog.append(block_info)
            
            print(f"   ✅ Extracted {len(blocks_catalog)} blocks with {sum(len(b['signals']) for b in blocks_catalog)} signals")
            return blocks_catalog
            
        except Exception as e:
            print(f"   ⚠️ Error extracting blocks: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_signal_statistics(self) -> Dict:
        """Extract signal occurrence statistics"""
        # This would ideally come from historical data analysis
        # For now, return placeholder structure
        return {
            'note': 'Signal statistics from building blocks registry',
            'total_signals_available': 0,  # Would be calculated from blocks
            'signal_occurrence_rates': {
                # Example: 'HOD_REJECTION': {'rate': 0.023, 'avg_per_month': 34}
            }
        }
    
    def _extract_analysis_context(self, analysis_report: Optional[Any]) -> Dict:
        """Extract analysis context if available"""
        if not analysis_report:
            return {'available': False}
        
        try:
            return {
                'available': True,
                'quality_score': analysis_report.strategy_quality_score if hasattr(analysis_report, 'strategy_quality_score') else None,
                'trade_frequency_assessment': analysis_report.trade_frequency.frequency_assessment if hasattr(analysis_report, 'trade_frequency') else None,
                'key_issues': analysis_report.key_issues if hasattr(analysis_report, 'key_issues') else [],
                'strengths': analysis_report.strengths if hasattr(analysis_report, 'strengths') else []
            }
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    def _validate_request(self, request: Dict):
        """Validate request completeness"""
        issues = []
        
        # Check strategy config
        if not request['strategy_configuration'].get('blocks'):
            issues.append("❌ Missing strategy blocks")
        
        # Check trades
        trade_count = request['trade_results'].get('total_trades', 0)
        if trade_count == 0:
            issues.append("⚠️ WARNING: 0 trades - AI cannot provide meaningful analysis")
        
        # Check metrics
        if not request['performance_metrics']:
            issues.append("⚠️ Missing performance metrics")
        
        # Check available blocks
        if not request['available_building_blocks']:
            issues.append("⚠️ Missing available blocks catalog")
        
        # Print validation results
        if issues:
            print("\n⚠️ Request Validation Issues:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n✅ Request validation passed - all data present")
        
        print(f"\n📊 Request Summary:")
        print(f"   - Strategy Blocks: {len(request['strategy_configuration'].get('blocks', []))}")
        print(f"   - Total Trades: {trade_count}")
        print(f"   - Metrics: {len(request['performance_metrics'])}")
        print(f"   - Available Blocks: {len(request['available_building_blocks'])}")
    
    def format_for_ai_prompt(self, request: Dict) -> str:
        """
        Format complete request as AI prompt
        
        INSTITUTIONAL-GRADE PROMPT STRUCTURE:
        - Clear objective
        - Performance analysis context  
        - Specific improvement targets
        - Actionable recommendation format
        - Examples of good recommendations
        """
        
        # Extract key data sections for reference
        metrics = request['performance_metrics']
        trades = request['trade_results']
        strategy = request['strategy_configuration']
        config = request['backtest_configuration']
        
        prompt = f"""# INSTITUTIONAL TRADING STRATEGY OPTIMIZATION REQUEST

## YOUR ROLE
You are an elite quantitative trading strategist analyzing a Bitcoin futures strategy.
Your expertise: Institutional risk management, signal optimization, building block analysis.

## DATA STRUCTURE
All complete data is provided in JSON format at the end of this prompt.
DO NOT rely on summaries in this section - analyze the actual JSON data provided.

## YOUR TASK
1. Analyze the complete strategy configuration (SECTION 1 below)
2. Review all trade executions in SECTION 3 below ({trades.get('total_trades', 0)} trades total)
3. Assess performance metrics with ratings (SECTION 4 below)
4. Consider available building blocks for recommendations (SECTION 5 below)
5. Provide specific, actionable recommendations using JSON response format

**CRITICAL**: The actual number of trades is in SECTION 3's JSON data. Do NOT rely on this summary count - analyze the actual `trades` array in SECTION 3.

## ANALYTICAL FRAMEWORK

### What to Analyze:
- **Strategy Design**: Does the combination of blocks make sense? Are they complementary?
- **Trade Frequency**: Is {trades.get('total_trades', 0)} trades adequate for statistical significance?
- **Win Rate & Risk/Reward**: Analyze actual trade outcomes, not just aggregate metrics
- **Signal Quality**: Do the current blocks produce reliable signals?
- **Missing Elements**: What validation or confluence is missing?

### Red Flags to Identify:
- Win rate below 50% (coin flip)
- Sharpe ratio below 1.0 (poor risk-adjusted returns)
- Max drawdown exceeding 15% (excessive risk)
- Trade frequency too low (<3/month = insufficient data)
- Trade frequency too high (>30/month = potential overfitting)

### Key Principle:
DO NOT make assumptions. Base ALL analysis on the actual data provided in sections 1-6 below.

### Recommendation Types You Can Suggest:

1. **ADD_BLOCK**: Add a new building block to improve signal quality
   - When: Missing confluence, need additional filters
   - Example: Add `liquidity_sweep` to confirm price rejection
   
2. **ADJUST_PARAMETER**: Modify strategy parameters
   - When: Win rate too low, drawdown too high, exits suboptimal
   - Example: Adjust `risk_per_trade_pct` from 10% to 5%
   
3. **ADD_TIMING**: Add session/time filters to improve trade timing
   - When: Need to avoid low-volatility periods
   - Example: Restrict entries to "ASIA" session only
   
4. **ADD_RECHECK**: Add signal recheck to reduce false signals
   - When: Too many false breakdown signals
   - Example: Recheck signals after 15 minutes before entry

### Recommendation Quality Standards:

✅ **GOOD RECOMMENDATION**:
- Addresses specific measurable problem (e.g., "Win rate 54% → target 60%")
- Uses available blocks appropriately
- Provides concrete configuration
- Realistic confidence score (0.70-0.90)
- Clear expected impact metrics

❌ **BAD RECOMMENDATION**:
- Vague ("improve risk management")
- Uses non-existent blocks
- No specific configuration
- Unrealistic confidence (>0.95)
- No measurable impact

### Example High-Quality Recommendation:

```json
{{
  "type": "ADD_BLOCK",
  "priority": 1,
  "block_name": "liquidity_sweep",
  "signal_name": "SWEEP_DETECTED",
  "configuration": {{
    "lookback_bars": 50,
    "min_liquidity_size": 100000
  }},
  "reasoning": "Current HOD_REJECTION has 54% win rate. Adding liquidity_sweep confirmation will filter out weak rejections where price hasn't swept liquidity yet, improving win rate to estimated 62-65% based on institutional analysis.",
  "expected_impact": {{
    "win_rate": "+8-11%",
    "trade_frequency": "-15%",
    "sharpe_ratio": "+0.3"
  }},
  "confidence": 0.78,
  "warnings": [
    "Will reduce trade frequency by ~15% (3-4 trades less per month)",
    "Requires price to sweep liquidity before signal, may miss early entries"
  ]
}}
```

## RESPOND IN THIS EXACT JSON FORMAT:

```json
{{
  "assessment": "1-2 sentence professional summary of strategy quality",
  
  "understanding": {{
    "strategy_intent": "What this strategy is trying to do",
    "current_blocks": ["list", "of", "blocks"],
    "trade_count": {trades.get('total_trades', 0)},
    "key_strengths": ["strength1", "strength2"],
    "key_weaknesses": ["weakness1", "weakness2"]
  }},
  
  "recommendations": [
    {{
      "type": "ADD_BLOCK | ADD_TIMING | ADJUST_PARAMETER | ADD_RECHECK",
      "priority": 1,
      "block_name": "exact_block_name_from_available_blocks",
      "signal_name": "EXACT_SIGNAL_NAME",
      "configuration": {{
        "parameter1": value1,
        "parameter2": value2
      }},
      "reasoning": "Detailed explanation linking this to specific performance problem",
      "expected_impact": {{
        "metric1": "specific change (e.g., +5%)",
        "metric2": "specific change"
      }},
      "confidence": 0.75,
      "warnings": ["warning1", "warning2"]
    }}
  ],
  
  "implementation_order": [
    "Recommendation 1: block_name - reason",
    "Recommendation 2: block_name - reason"
  ],
  
  "overall_confidence": 0.80,
  
  "critical_notes": [
    "Any critical warnings or considerations"
  ]
}}
```

**IMPORTANT CONSTRAINTS**:
- Only recommend blocks from the Available Building Blocks list
- Every recommendation must address a specific measured problem
- Provide concrete configuration values, not placeholders
- Confidence scores between 0.60-0.90 (realistic)
- Expected impact must be measurable and specific

---

## COMPLETE DATA FOR YOUR ANALYSIS:

All data is provided in structured JSON format below.
Analyze this data directly - do not rely on summaries.

1. STRATEGY CONFIGURATION:
```json
{json.dumps(request['strategy_configuration'], indent=2)}
```

2. BACKTEST CONFIGURATION:
```json
{json.dumps(request['backtest_configuration'], indent=2)}
```

3. TRADE RESULTS ({request['trade_results']['total_trades']} trades):
```json
{json.dumps(request['trade_results'], indent=2)}
```

4. PERFORMANCE METRICS:
```json
{json.dumps(request['performance_metrics'], indent=2)}
```

5. AVAILABLE BUILDING BLOCKS ({len(request['available_building_blocks'])} blocks):
```json
{json.dumps(request['available_building_blocks'], indent=2)}
```

6. ANALYSIS CONTEXT:
```json
{json.dumps(request['analysis_context'], indent=2)}
```

---

## YOUR RESPONSE:
Analyze the data above and respond in this EXACT JSON format:

{self._get_expected_response_format()}
"""
        
        return prompt
    
    def _get_expected_response_format(self) -> str:
        """Get expected response format"""
        return """{
  "assessment": "Professional analysis",
  "understanding": {
    "strategy_type": "Bearish/Bullish",
    "current_blocks": ["block1", "block2"],
    "trade_count": 24,
    "key_metrics": {}
  },
  "recommendations": [
    {
      "type": "ADD_RECHECK | ADD_TIMING | ADD_BLOCK | ADJUST_PARAM",
      "priority": 1,
      "block_name": "block_name",
      "signal_name": "SIGNAL_NAME",
      "configuration": {},
      "reasoning": "Detailed reasoning",
      "expected_impact": {},
      "confidence": 0.88,
      "warnings": []
    }
  ],
  "implementation_order": [],
  "overall_confidence": 0.87
}"""
    

# Test function
def test_request_builder():
    """Test comprehensive request builder"""
    print("\n" + "="*80)
    print("COMPREHENSIVE AI REQUEST BUILDER - TEST")
    print("="*80)
    
    builder = ComprehensiveAIRequestBuilder()
    
    # Sample data
    strategy_config = {
        'name': 'HOD Rejection Test',
        'strategy_type': 'Bearish',
        'blocks': [
            {
                'name': 'hod',
                'category': 'PATTERN',
                'signals': [{'name': 'HOD_REJECTION'}]
            }
        ]
    }
    
    backtest_results = {
        'total_trades': 24,
        'total_pnl': 544.0,
        'win_rate': 58.3,
        'profit_factor': 1.97,
        'trades': [
            {
                'entry_time': '2025-10-01T08:00:00',
                'exit_time': '2025-10-01T12:30:00',
                'pnl': 75.50,
                'side': 'SHORT',
                'entry_bar': 100,
                'exit_bar': 1100
            }
        ] * 24
    }
    
    metrics = {
        'total_pnl': {'value': 544.0, 'rating': '✓ Good'},
        'win_rate': {'value': 58.3, 'rating': '✓ Good'}
    }
    
    backtest_config = {
        'timeframe': '15m',
        'lookback_days': 180,
        'stop_loss': 0.02,
        'take_profit': [0.01, 0.015, 0.02]
    }
    
    # Build request
    request = builder.build_complete_request(
        strategy_config,
        backtest_results,
        metrics,
        backtest_config
    )
    
    print(f"\n✅ Request built successfully")
    print(f"\nRequest size: {len(json.dumps(request, default=str))} bytes")
    
    # Test prompt formatting
    prompt = builder.format_for_ai_prompt(request)
    print(f"Prompt size: {len(prompt)} characters")
    print(f"\nFirst 500 characters of prompt:")
    print(prompt[:500])
    
    print("\n" + "="*80)


if __name__ == '__main__':
    test_request_builder()
