"""
Unit Tests for SignalDependencyResolver
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/03_COMPONENT_SPECS.md, docs/v3/UI-UX/07_TIMING_CONSTRAINTS.md
"""

import pytest
from src.strategy_builder.core.signal_dependency_resolver import (
    SignalDependencyResolver,
    DependencyGraph,
    SignalNode,
    TimingViolation
)
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    TimingConstraint
)


class TestSignalDependencyResolver:
    """Test suite for SignalDependencyResolver"""
    
    def test_resolver_initialization(self):
        """Test resolver initializes correctly"""
        resolver = SignalDependencyResolver()
        assert resolver is not None
        
    def test_build_graph_simple_strategy(self):
        """Test building dependency graph for simple strategy"""
        resolver = SignalDependencyResolver()
        
        # Create simple strategy config
        config = StrategyConfig()
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        block1.signals.append(signal1)
        config.blocks.append(block1)
        
        # Build graph
        graph = resolver.build_graph(config)
        assert graph is not None
        assert len(graph.nodes) == 1
        assert graph.nodes[0].signal_name == "SIGNAL1"
        
    def test_build_graph_with_timing_constraints(self):
        """Test graph building handles timing constraints"""
        resolver = SignalDependencyResolver()
        
        config = StrategyConfig()
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        
        # Add first signal
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        block1.signals.append(signal1)
        
        # Add second signal with timing constraint
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint)
        block1.signals.append(signal2)
        
        config.blocks.append(block1)
        
        # Build graph
        graph = resolver.build_graph(config)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1  # SIGNAL2 depends on SIGNAL1
        
    def test_validate_timing_no_constraint(self):
        """Test timing validation passes when no constraint"""
        resolver = SignalDependencyResolver()
        
        signal = SignalConfig(name="SIGNAL1", logic="AND")
        result = resolver.validate_timing(signal, fired_at_candle=100, current_candle=120)
        assert result is True
        
    def test_validate_timing_within_window(self):
        """Test timing validation passes within window"""
        resolver = SignalDependencyResolver()
        
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint)
        
        # Reference fired at candle 100, current is 115 (within 20 candles)
        result = resolver.validate_timing(
            signal,
            fired_at_candle=100,
            current_candle=115,
            reference_candle=100
        )
        assert result is True
        
    def test_validate_timing_outside_window(self):
        """Test timing validation fails outside window"""
        resolver = SignalDependencyResolver()
        
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint)
        
        # Reference fired at candle 100, current is 125 (outside 20 candles)
        result = resolver.validate_timing(
            signal,
            fired_at_candle=122,
            current_candle=125,
            reference_candle=100
        )
        assert result is False
        
    def test_should_reset_strategy_timing_violation(self):
        """Test strategy reset on timing violation"""
        resolver = SignalDependencyResolver()
        
        config = StrategyConfig()
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        block1.signals.append(signal1)
        
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint)
        block1.signals.append(signal2)
        
        config.blocks.append(block1)
        
        # Build graph
        graph = resolver.build_graph(config)
        
        # Check if should reset (outside timing window)
        signal_state = {
            "Block1.SIGNAL1": 100,  # Fired at candle 100
            # SIGNAL2 not fired yet, but we're at candle 130 (past window)
        }
        
        result = resolver.should_reset_strategy(
            config=config,
            graph=graph,
            signal_state=signal_state,
            current_candle=130
        )
        assert result is True
        
    def test_should_not_reset_within_window(self):
        """Test strategy doesn't reset within timing window"""
        resolver = SignalDependencyResolver()
        
        config = StrategyConfig()
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        block1.signals.append(signal1)
        
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint)
        block1.signals.append(signal2)
        
        config.blocks.append(block1)
        
        graph = resolver.build_graph(config)
        
        # Within window
        signal_state = {
            "Block1.SIGNAL1": 100,
        }
        
        result = resolver.should_reset_strategy(
            config=config,
            graph=graph,
            signal_state=signal_state,
            current_candle=115  # Within 20 candles
        )
        assert result is False
        
    def test_get_dependencies(self):
        """Test getting signal dependencies"""
        resolver = SignalDependencyResolver()
        
        config = StrategyConfig()
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint)
        
        block1.signals.extend([signal1, signal2])
        config.blocks.append(block1)
        
        graph = resolver.build_graph(config)
        
        # Get dependencies for SIGNAL2
        deps = resolver.get_dependencies(graph, "Block1.SIGNAL2")
        assert len(deps) == 1
        assert "Block1.SIGNAL1" in deps
        
    def test_detect_circular_dependencies(self):
        """Test detection of circular dependencies"""
        resolver = SignalDependencyResolver()
        
        # This would be an invalid config, but we should detect it
        config = StrategyConfig()
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        
        # Signal1 depends on Signal2, Signal2 depends on Signal1 (circular)
        constraint1 = TimingConstraint(max_candles=20, reference="SIGNAL2")
        signal1 = SignalConfig(name="SIGNAL1", logic="AND", timing_constraint=constraint1)
        
        constraint2 = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint2)
        
        block1.signals.extend([signal1, signal2])
        config.blocks.append(block1)
        
        # Should detect circular dependency
        with pytest.raises(ValueError, match="[Cc]ircular"):
            resolver.build_graph(config)


class TestDependencyGraph:
    """Test DependencyGraph data structure"""
    
    def test_graph_initialization(self):
        """Test graph initializes empty"""
        graph = DependencyGraph()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        
    def test_add_node(self):
        """Test adding nodes to graph"""
        graph = DependencyGraph()
        node = SignalNode(
            block_name="Block1",
            signal_name="SIGNAL1",
            logic="AND",
            timing_constraint=None
        )
        graph.add_node(node)
        assert len(graph.nodes) == 1
        
    def test_add_edge(self):
        """Test adding edges (dependencies)"""
        graph = DependencyGraph()
        
        node1 = SignalNode("Block1", "SIGNAL1", "AND")
        node2 = SignalNode("Block1", "SIGNAL2", "AND")
        
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(from_signal="Block1.SIGNAL2", to_signal="Block1.SIGNAL1")
        
        assert len(graph.edges) == 1
        
    def test_get_node(self):
        """Test retrieving node by full name"""
        graph = DependencyGraph()
        node = SignalNode("Block1", "SIGNAL1", "AND")
        graph.add_node(node)
        
        retrieved = graph.get_node("Block1.SIGNAL1")
        assert retrieved is not None
        assert retrieved.signal_name == "SIGNAL1"


class TestSignalNode:
    """Test SignalNode data class"""
    
    def test_node_creation(self):
        """Test creating signal node"""
        node = SignalNode(
            block_name="Block1",
            signal_name="SIGNAL1",
            logic="AND",
            timing_constraint=None
        )
        assert node.block_name == "Block1"
        assert node.signal_name == "SIGNAL1"
        assert node.logic == "AND"
        
    def test_node_full_name(self):
        """Test full name property"""
        node = SignalNode("Block1", "SIGNAL1", "AND")
        assert node.full_name == "Block1.SIGNAL1"
        
    def test_node_with_timing_constraint(self):
        """Test node with timing constraint"""
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        node = SignalNode("Block1", "SIGNAL2", "AND", timing_constraint=constraint)
        assert node.timing_constraint is not None
        assert node.timing_constraint.max_candles == 20


class TestTimingViolation:
    """Test TimingViolation exception"""
    
    def test_timing_violation_creation(self):
        """Test creating timing violation"""
        violation = TimingViolation(
            signal="Block1.SIGNAL2",
            reference="Block1.SIGNAL1",
            max_candles=20,
            actual_candles=25
        )
        assert "Block1.SIGNAL2" in str(violation)
        assert "20" in str(violation)


class TestSignalDependencyIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_multi_signal_strategy(self):
        """Test complete workflow with multiple signals and timing"""
        resolver = SignalDependencyResolver()
        
        # Build complex strategy
        config = StrategyConfig()
        
        # Block 1: Multiple signals with constraints
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        
        constraint2 = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint2)
        
        constraint3 = TimingConstraint(max_candles=10, reference="SIGNAL2")
        signal3 = SignalConfig(name="SIGNAL3", logic="AND", timing_constraint=constraint3)
        
        block1.signals.extend([signal1, signal2, signal3])
        config.blocks.append(block1)
        
        # Build graph
        graph = resolver.build_graph(config)
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2  # SIGNAL2→SIGNAL1, SIGNAL3→SIGNAL2
        
        # Test timing validation
        signal_state = {
            "Block1.SIGNAL1": 100,
            "Block1.SIGNAL2": 115,  # Within 20 of SIGNAL1
            # SIGNAL3 not fired yet, checking at candle 120
        }
        
        # Should not reset (SIGNAL3 has 10 candles from 115, we're at 120, still has 5 left)
        result = resolver.should_reset_strategy(config, graph, signal_state, current_candle=120)
        assert result is False
        
        # Should reset at candle 130 (past SIGNAL3 window)
        result = resolver.should_reset_strategy(config, graph, signal_state, current_candle=130)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
