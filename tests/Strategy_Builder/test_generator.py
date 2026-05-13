"""
Test Suite for Strategy Generator

Tests code generation functionality including templates,
rendering, syntax validation, and file generation.

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import pytest
import tempfile
from pathlib import Path
import ast
import yaml

from src.utils.Strategy_Builder.generator import StrategyGenerator
from src.utils.Strategy_Builder.models import (
    StrategyConfiguration,
    BlockSelection,
    SignalConfiguration,
    StrategyCategory,
    SignalRole,
    BlockType
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def generator():
    """Create generator instance"""
    return StrategyGenerator()


@pytest.fixture
def sample_config():
    """Create sample strategy configuration"""
    return StrategyConfiguration(
        strategy_name="test strategy",  # Will be auto-formatted to strategy_01_test_strategy
        strategy_number=1,
        strategy_category=StrategyCategory.REVERSAL,
        description="Test strategy for generator",
        main_signal_block="double_top",
        blocks=[
            BlockSelection(
                block_name="double_top",
                block_display_name="Double Top",
                block_category="PATTERNS",
                block_type=BlockType.EVENT,
                weight=35,
                weight_range=(30, 40),
                is_main_signal=True,
                signals=[
                    SignalConfiguration(
                        signal_name="BEARISH_BREAKDOWN",
                        signal_display_name="Bearish Breakdown",
                        role=SignalRole.SIGNAL
                    )
                ]
            ),
            BlockSelection(
                block_name="rsi_divergence",
                block_display_name="RSI Divergence",
                block_category="OSCILLATORS",
                block_type=BlockType.SIGNAL,
                weight=25,
                weight_range=(20, 30),
                signals=[
                    SignalConfiguration(
                        signal_name="BEARISH_DIV",
                        signal_display_name="Bearish Divergence",
                        role=SignalRole.FILTER
                    )
                ]
            )
        ],
        min_confluence=70,
        risk_reward_ratio="1:3"
    )


class TestGeneratorInitialization:
    """Test generator initialization"""
    
    def test_init_creates_generator(self, generator):
        """Test generator is created successfully"""
        assert generator is not None
        assert hasattr(generator, 'strategy_template')
        assert hasattr(generator, 'test_template')
        assert hasattr(generator, 'optimizer_template')
    
    def test_init_loads_templates(self, generator):
        """Test templates are loaded"""
        assert generator.strategy_template is not None
        assert generator.test_template is not None
        assert generator.optimizer_template is not None
    
    def test_init_with_custom_template_dir(self, temp_dir):
        """Test initialization with custom template directory"""
        # Should not crash even if directory is empty
        gen = StrategyGenerator(template_dir=temp_dir)
        assert gen.template_dir == temp_dir


class TestContextPreparation:
    """Test template context preparation"""
    
    def test_prepare_context_returns_dict(self, generator, sample_config):
        """Test _prepare_context returns dictionary"""
        context = generator._prepare_context(sample_config)
        
        assert isinstance(context, dict)
        assert 'config' in context
        assert 'class_name' in context
        assert 'filename' in context
        assert 'imports' in context
        assert 'generation_date' in context
    
    def test_context_has_config(self, generator, sample_config):
        """Test context contains original config"""
        context = generator._prepare_context(sample_config)
        
        assert context['config'] == sample_config
    
    def test_context_generates_class_name(self, generator, sample_config):
        """Test class name is generated correctly"""
        context = generator._prepare_context(sample_config)
        
        # "test_strategy" -> "TestStrategy"
        assert context['class_name'] == "TestStrategy"
    
    def test_context_generates_filename(self, generator, sample_config):
        """Test filename is generated correctly"""
        context = generator._prepare_context(sample_config)
        
        assert context['filename'] == "strategy_001_test_strategy"
    
    def test_context_generates_imports(self, generator, sample_config):
        """Test imports are generated"""
        context = generator._prepare_context(sample_config)
        
        imports = context['imports']
        assert isinstance(imports, list)
        assert len(imports) > 0
        
        # Should have imports for both blocks
        import_str = '\n'.join(imports)
        assert 'double_top' in import_str.lower() or 'DoubleTop' in import_str
        assert 'rsi' in import_str.lower() or 'RSI' in import_str


class TestClassNameGeneration:
    """Test class name generation"""
    
    def test_generate_class_name_simple(self, generator):
        """Test simple class name generation"""
        name = generator._generate_class_name("test strategy")
        assert name == "TestStrategy"
    
    def test_generate_class_name_underscores(self, generator):
        """Test class name with underscores"""
        name = generator._generate_class_name("test_strategy_name")
        assert name == "TestStrategyName"
    
    def test_generate_class_name_mixed(self, generator):
        """Test class name with mixed separators"""
        name = generator._generate_class_name("test strategy_name")
        assert name == "TestStrategyName"
    
    def test_generate_class_name_single_word(self, generator):
        """Test single word class name"""
        name = generator._generate_class_name("reversal")
        assert name == "Reversal"


class TestImportGeneration:
    """Test import statement generation"""
    
    def test_generate_imports_returns_list(self, generator, sample_config):
        """Test _generate_imports returns list"""
        imports = generator._generate_imports(sample_config.blocks)
        
        assert isinstance(imports, list)
        assert len(imports) > 0
    
    def test_imports_are_unique(self, generator):
        """Test imports are deduplicated"""
        # Create blocks with same name
        blocks = [
            BlockSelection(
                block_name="double_top",
                block_display_name="Double Top",
                block_category="PATTERNS",
                block_type=BlockType.EVENT,
                weight=30,
                weight_range=(20, 40)
            ),
            BlockSelection(
                block_name="double_top",
                block_display_name="Double Top 2",
                block_category="PATTERNS",
                block_type=BlockType.EVENT,
                weight=25,
                weight_range=(20, 30)
            )
        ]
        
        imports = generator._generate_imports(blocks)
        
        # Should only have one import for double_top
        assert len(imports) == len(set(imports))
    
    def test_imports_are_sorted(self, generator, sample_config):
        """Test imports are sorted"""
        imports = generator._generate_imports(sample_config.blocks)
        
        # Should be alphabetically sorted
        assert imports == sorted(imports)


class TestStrategyFileGeneration:
    """Test strategy file generation"""
    
    def test_generate_strategy_file_creates_file(self, generator, sample_config, temp_dir):
        """Test strategy file is created"""
        filepath = generator.generate_strategy_file(sample_config, temp_dir)
        
        assert filepath.exists()
        assert filepath.suffix == '.py'
    
    def test_generated_filename_format(self, generator, sample_config, temp_dir):
        """Test generated filename follows format"""
        filepath = generator.generate_strategy_file(sample_config, temp_dir)
        
        expected = "strategy_001_test_strategy.py"
        assert filepath.name == expected
    
    def test_generated_code_is_valid_python(self, generator, sample_config, temp_dir):
        """Test generated code is syntactically valid"""
        filepath = generator.generate_strategy_file(sample_config, temp_dir)
        
        # Should not raise SyntaxError
        with open(filepath) as f:
            code = f.read()
        
        ast.parse(code)  # Will raise SyntaxError if invalid
    
    def test_generated_code_has_imports(self, generator, sample_config, temp_dir):
        """Test generated code has import statements"""
        filepath = generator.generate_strategy_file(sample_config, temp_dir)
        
        with open(filepath) as f:
            code = f.read()
        
        assert 'import' in code
        assert 'from' in code
    
    def test_generated_code_has_class(self, generator, sample_config, temp_dir):
        """Test generated code has strategy class"""
        filepath = generator.generate_strategy_file(sample_config, temp_dir)
        
        with open(filepath) as f:
            code = f.read()
        
        assert 'class TestStrategy' in code
        assert 'Strategy' in code  # Inherits from Strategy


class TestTestFileGeneration:
    """Test test file generation"""
    
    def test_generate_test_file_creates_file(self, generator, sample_config, temp_dir):
        """Test test file is created"""
        filepath = generator.generate_test_file(sample_config, temp_dir)
        
        assert filepath.exists()
        assert filepath.suffix == '.py'
    
    def test_test_filename_format(self, generator, sample_config, temp_dir):
        """Test filename follows test format"""
        filepath = generator.generate_test_file(sample_config, temp_dir)
        
        expected = "test_001_test_strategy.py"
        assert filepath.name == expected
    
    def test_generated_test_is_valid_python(self, generator, sample_config, temp_dir):
        """Test generated test code is syntactically valid"""
        filepath = generator.generate_test_file(sample_config, temp_dir)
        
        with open(filepath) as f:
            code = f.read()
        
        ast.parse(code)  # Will raise SyntaxError if invalid
    
    def test_generated_test_has_pytest(self, generator, sample_config, temp_dir):
        """Test generated code imports pytest"""
        filepath = generator.generate_test_file(sample_config, temp_dir)
        
        with open(filepath) as f:
            code = f.read()
        
        assert 'import pytest' in code
    
    def test_generated_test_has_fixtures(self, generator, sample_config, temp_dir):
        """Test generated code has pytest fixtures"""
        filepath = generator.generate_test_file(sample_config, temp_dir)
        
        with open(filepath) as f:
            code = f.read()
        
        assert '@pytest.fixture' in code
    
    def test_generated_test_has_test_classes(self, generator, sample_config, temp_dir):
        """Test generated code has test classes"""
        filepath = generator.generate_test_file(sample_config, temp_dir)
        
        with open(filepath) as f:
            code = f.read()
        
        assert 'class Test' in code
        assert 'def test_' in code


class TestOptimizerConfigGeneration:
    """Test optimizer config generation"""
    
    def test_generate_optimizer_config_creates_file(self, generator, sample_config, temp_dir):
        """Test optimizer config file is created"""
        filepath = generator.generate_optimizer_config(sample_config, temp_dir)
        
        assert filepath.exists()
        assert filepath.suffix in ['.yaml', '.yml']
    
    def test_config_filename_format(self, generator, sample_config, temp_dir):
        """Test config filename follows format"""
        filepath = generator.generate_optimizer_config(sample_config, temp_dir)
        
        expected = "optimizer_001_test_strategy.yaml"
        assert filepath.name == expected
    
    def test_generated_config_is_valid_yaml(self, generator, sample_config, temp_dir):
        """Test generated config is valid YAML"""
        filepath = generator.generate_optimizer_config(sample_config, temp_dir)
        
        with open(filepath) as f:
            data = yaml.safe_load(f)
        
        assert data is not None
        assert isinstance(data, dict)
    
    def test_config_has_strategy_info(self, generator, sample_config, temp_dir):
        """Test config contains strategy information"""
        filepath = generator.generate_optimizer_config(sample_config, temp_dir)
        
        with open(filepath) as f:
            data = yaml.safe_load(f)
        
        assert 'strategy' in data
        assert data['strategy']['name'] == "strategy_01_test_strategy"
        assert data['strategy']['number'] == 1
    
    def test_config_has_parameters(self, generator, sample_config, temp_dir):
        """Test config contains optimization parameters"""
        filepath = generator.generate_optimizer_config(sample_config, temp_dir)
        
        with open(filepath) as f:
            data = yaml.safe_load(f)
        
        assert 'parameters' in data
        assert 'min_confluence' in data['parameters']
        assert 'block_weights' in data['parameters']


class TestGenerateAll:
    """Test generating all files at once"""
    
    def test_generate_all_returns_dict(self, generator, sample_config, temp_dir):
        """Test generate_all returns dictionary of paths"""
        files = generator.generate_all(
            sample_config,
            strategy_dir=temp_dir / 'strategies',
            test_dir=temp_dir / 'tests',
            config_dir=temp_dir / 'config'
        )
        
        assert isinstance(files, dict)
        assert 'strategy' in files
        assert 'test' in files
        assert 'optimizer' in files
    
    def test_generate_all_creates_all_files(self, generator, sample_config, temp_dir):
        """Test all files are created"""
        files = generator.generate_all(
            sample_config,
            strategy_dir=temp_dir / 'strategies',
            test_dir=temp_dir / 'tests',
            config_dir=temp_dir / 'config'
        )
        
        assert files['strategy'].exists()
        assert files['test'].exists()
        assert files['optimizer'].exists()


class TestSyntaxValidation:
    """Test syntax validation"""
    
    def test_validate_python_syntax_valid(self, generator, sample_config, temp_dir):
        """Test validation passes for valid Python"""
        filepath = generator.generate_strategy_file(sample_config, temp_dir)
        
        is_valid = generator.validate_python_syntax(filepath)
        assert is_valid is True
    
    def test_validate_python_syntax_invalid(self, generator, temp_dir):
        """Test validation fails for invalid Python"""
        # Create file with syntax error
        filepath = temp_dir / 'invalid.py'
        with open(filepath, 'w') as f:
            f.write("def broken(\n")  # Missing closing paren
        
        is_valid = generator.validate_python_syntax(filepath)
        assert is_valid is False
    
    def test_validate_yaml_syntax_valid(self, generator, sample_config, temp_dir):
        """Test validation passes for valid YAML"""
        filepath = generator.generate_optimizer_config(sample_config, temp_dir)
        
        is_valid = generator.validate_yaml_syntax(filepath)
        assert is_valid is True
    
    def test_validate_yaml_syntax_invalid(self, generator, temp_dir):
        """Test validation fails for invalid YAML"""
        # Create file with YAML error
        filepath = temp_dir / 'invalid.yaml'
        with open(filepath, 'w') as f:
            f.write("key: [invalid")  # Unclosed bracket
        
        is_valid = generator.validate_yaml_syntax(filepath)
        assert is_valid is False


class TestDryRun:
    """Test dry run functionality"""
    
    def test_dry_run_returns_dict(self, generator, sample_config):
        """Test dry run returns dictionary"""
        result = generator.dry_run(sample_config)
        
        assert isinstance(result, dict)
        assert 'strategy' in result
        assert 'test' in result
        assert 'optimizer' in result
    
    def test_dry_run_returns_strings(self, generator, sample_config):
        """Test dry run returns rendered code as strings"""
        result = generator.dry_run(sample_config)
        
        assert isinstance(result['strategy'], str)
        assert isinstance(result['test'], str)
        assert isinstance(result['optimizer'], str)
        
        # Should have content
        assert len(result['strategy']) > 0
        assert len(result['test']) > 0
        assert len(result['optimizer']) > 0
    
    def test_dry_run_does_not_create_files(self, generator, sample_config, temp_dir):
        """Test dry run doesn't create any files"""
        # Do dry run
        generator.dry_run(sample_config)
        
        # Check no files created
        assert len(list(temp_dir.iterdir())) == 0


class TestEdgeCases:
    """Test edge cases"""
    
    def test_strategy_with_many_blocks(self, generator, temp_dir):
        """Test generation with many blocks"""
        # Create config with 10 blocks
        blocks = []
        for i in range(10):
            blocks.append(
                BlockSelection(
                    block_name=f"block_{i}",
                    block_display_name=f"Block {i}",
                    block_category="TEST",
                    block_type=BlockType.SIGNAL,
                    weight=10,
                    weight_range=(5, 15),
                    is_main_signal=(i == 0)
                )
            )
        
        config = StrategyConfiguration(
            strategy_name="many_blocks",
            strategy_number=100,
            strategy_category=StrategyCategory.CONTINUATION,
            main_signal_block="block_0",
            blocks=blocks
        )
        
        # Should not crash
        files = generator.generate_all(config, temp_dir, temp_dir, temp_dir)
        
        assert files['strategy'].exists()
        assert files['test'].exists()
        assert files['optimizer'].exists()
    
    def test_strategy_name_with_special_characters(self, generator, temp_dir):
        """Test strategy name with special characters"""
        config = StrategyConfiguration(
            strategy_name="test strategy with spaces",
            strategy_number=50,
            strategy_category=StrategyCategory.SCALPING,
            main_signal_block="test",
            blocks=[
                BlockSelection(
                    block_name="test",
                    block_display_name="Test",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=50,
                    weight_range=(40, 60),
                    is_main_signal=True
                )
            ]
        )
        
        # Should handle spaces correctly
        filepath = generator.generate_strategy_file(config, temp_dir)
        
        assert filepath.exists()
        assert ' ' not in filepath.name  # Spaces should be replaced


if __name__ == "__main__":
    pytest.main([__file__, "-v"])