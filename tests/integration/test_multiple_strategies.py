"""
Task 1.5.1: Test with 10+ Strategies
Integration tests for multiple strategy optimization
Sprint 1.5 - Testing & Polish
"""
import pytest
import json
import os
from pathlib import Path
from typing import Dict, Any, List


# List of all test strategies
STRATEGIES = [
    'hod_rejection.json',
    'lod_rejection.json',
    'rsi_vwap_50_asia_rejection.json',
    'wyckoff_spring.json',
    'fibonacci_zones.json',
    'market_structure.json',
    'divergence_strategy.json',
    'liquidity_sweep.json',
    'breakout_retest.json',
    'reversal_m_pattern.json'
]


@pytest.fixture
def test_strategies_path() -> Path:
    """Get path to test strategies directory"""
    return Path(__file__).parent.parent / 'strategies'


@pytest.fixture
def strategy_loader(test_strategies_path: Path):
    """Load strategy from file"""
    def _load(filename: str) -> Dict[str, Any]:
        filepath = test_strategies_path / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Strategy file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            return json.load(f)
    return _load


class TestMultipleStrategies:
    """Test optimizer with multiple different strategies"""
    
    def test_all_strategies_exist(self, test_strategies_path: Path):
        """Verify all test strategy files exist"""
        for strategy_file in STRATEGIES:
            filepath = test_strategies_path / strategy_file
            assert filepath.exists(), f"Strategy file missing: {strategy_file}"
    
    def test_all_strategies_valid_json(self, test_strategies_path: Path):
        """Verify all strategies are valid JSON"""
        for strategy_file in STRATEGIES:
            filepath = test_strategies_path / strategy_file
            with open(filepath, 'r') as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {strategy_file}: {e}")
    
    def test_all_strategies_have_required_fields(self, strategy_loader):
        """Verify all strategies have required fields"""
        required_fields = ['name', 'description', 'blocks', 'version', 
                          'strategy_type', 'validation_status', 'generation_status']
        
        for strategy_file in STRATEGIES:
            strategy = strategy_loader(strategy_file)
            
            for field in required_fields:
                assert field in strategy, \
                    f"{strategy_file} missing required field: {field}"
    
    def test_all_strategies_have_blocks(self, strategy_loader):
        """Verify all strategies have at least one block"""
        for strategy_file in STRATEGIES:
            strategy = strategy_loader(strategy_file)
            assert len(strategy['blocks']) > 0, \
                f"{strategy_file} has no building blocks"
    
    def test_all_strategies_have_signals(self, strategy_loader):
        """Verify all strategy blocks have signals"""
        for strategy_file in STRATEGIES:
            strategy = strategy_loader(strategy_file)
            
            for block in strategy['blocks']:
                assert 'signals' in block, \
                    f"{strategy_file} block '{block['name']}' has no signals"
                assert len(block['signals']) > 0, \
                    f"{strategy_file} block '{block['name']}' has empty signals list"
    
    def test_all_strategies_have_valid_types(self, strategy_loader):
        """Verify all strategies have valid strategy types"""
        valid_types = ['Bullish', 'Bearish']
        
        for strategy_file in STRATEGIES:
            strategy = strategy_loader(strategy_file)
            assert strategy['strategy_type'] in valid_types, \
                f"{strategy_file} has invalid strategy_type: {strategy['strategy_type']}"
    
    def test_all_strategies_have_valid_logic(self, strategy_loader):
        """Verify all blocks and signals have valid logic operators"""
        valid_logic = ['AND', 'OR']
        
        for strategy_file in STRATEGIES:
            strategy = strategy_loader(strategy_file)
            
            for block in strategy['blocks']:
                assert block['logic'] in valid_logic, \
                    f"{strategy_file} block '{block['name']}' has invalid logic: {block['logic']}"
                
                for signal in block['signals']:
                    assert signal['logic'] in valid_logic, \
                        f"{strategy_file} signal '{signal['name']}' has invalid logic: {signal['logic']}"
    
    @pytest.mark.parametrize("strategy_file", STRATEGIES)
    def test_strategy_optimization(self, strategy_file: str, strategy_loader):
        """
        Test optimizer with each strategy
        Note: This test requires OptimizerV3 to be implemented
        Placeholder for now - will be enhanced when optimizer is ready
        """
        strategy = strategy_loader(strategy_file)
        
        # Verify strategy can be loaded
        assert strategy is not None
        assert 'name' in strategy
        
        # TODO: When OptimizerV3 is ready, uncomment and complete:
        # from src.optimizer_v3.core.optimizer import OptimizerV3
        # 
        # optimizer = OptimizerV3(strategy)
        # optimizer.set_max_configs(10)
        # results = optimizer.optimize()
        # 
        # assert len(results) > 0, f"No results for {strategy_file}"
        # assert all('sharpe_ratio' in r for r in results), "Missing sharpe_ratio"
        # assert all('win_rate' in r for r in results), "Missing win_rate"
        # assert all('max_drawdown' in r for r in results), "Missing max_drawdown"
        # assert all('total_pnl' in r for r in results), "Missing total_pnl"
    
    def test_strategy_diversity(self, strategy_loader):
        """Verify strategies have diverse configurations"""
        strategy_types = set()
        unique_blocks = set()
        
        for strategy_file in STRATEGIES:
            strategy = strategy_loader(strategy_file)
            strategy_types.add(strategy['strategy_type'])
            
            for block in strategy['blocks']:
                unique_blocks.add(block['name'])
        
        # Should have both bullish and bearish strategies
        assert len(strategy_types) >= 2, "Need both Bullish and Bearish strategies"
        
        # Should use diverse building blocks
        assert len(unique_blocks) >= 5, f"Only {len(unique_blocks)} unique blocks used"
    
    def test_count_strategies(self):
        """Verify we have 10+ strategies as required"""
        assert len(STRATEGIES) >= 10, \
            f"Task 1.5.1 requires 10+ strategies, only have {len(STRATEGIES)}"


@pytest.mark.integration
class TestStrategyOptimizationIntegration:
    """
    Integration tests for strategy optimization
    These tests will be completed when OptimizerV3 core is ready
    """
    
    @pytest.mark.skip(reason="OptimizerV3 core not yet implemented")
    def test_parallel_optimization(self, strategy_loader):
        """Test running multiple strategies in parallel"""
        # from src.optimizer_v3.core.optimizer import OptimizerV3
        # from concurrent.futures import ProcessPoolExecutor
        # 
        # with ProcessPoolExecutor(max_workers=4) as executor:
        #     futures = []
        #     for strategy_file in STRATEGIES[:5]:  # Test first 5
        #         strategy = strategy_loader(strategy_file)
        #         future = executor.submit(run_optimization, strategy)
        #         futures.append(future)
        #     
        #     results = [f.result() for f in futures]
        #     assert len(results) == 5
        pass
    
    @pytest.mark.skip(reason="OptimizerV3 core not yet implemented")
    def test_memory_usage_across_strategies(self, strategy_loader):
        """Test memory usage stays within limits across multiple strategies"""
        # import psutil
        # process = psutil.Process()
        # 
        # initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        # 
        # for strategy_file in STRATEGIES:
        #     strategy = strategy_loader(strategy_file)
        #     optimizer = OptimizerV3(strategy)
        #     optimizer.set_max_configs(5)
        #     results = optimizer.optimize()
        #     
        #     current_memory = process.memory_info().rss / 1024 / 1024
        #     memory_growth = current_memory - initial_memory
        #     
        #     assert memory_growth < 2048, f"Memory grew by {memory_growth}MB"
        pass
    
    @pytest.mark.skip(reason="OptimizerV3 core not yet implemented")
    def test_performance_consistency(self, strategy_loader):
        """Test performance is consistent across strategy runs"""
        # Test that running same strategy twice gives similar performance metrics
        pass


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
