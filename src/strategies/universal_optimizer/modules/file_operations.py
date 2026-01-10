"""
File Operations

Extract blocks from strategy files, validate against catalog, apply configurations.
Enables zero-manual-editing workflow.
"""

import re
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from .catalog import BUILDING_BLOCK_CATALOG
from .data_classes import OptimizationConfig, ConfigPerformance


def extract_blocks_from_strategy(strategy_module_name: str) -> Optional[Dict]:
    """Extract building blocks from strategy file"""
    # __file__ is in: src/strategies/universal_optimizer/modules/file_operations.py
    # parent = modules, parent.parent = universal_optimizer, parent.parent.parent = strategies
    strategy_path = Path(__file__).parent.parent.parent / f'{strategy_module_name}.py'
    
    if not strategy_path.exists():
        return None
    
    blocks = {}
    
    with open(strategy_path) as f:
        content = f.read()
    
    # Pattern: self.blocks['key'] = {...}
    pattern = r"self\.blocks\['(\w+)'\]\s*=\s*\{([^}]+)\}"
    matches = re.findall(pattern, content, re.DOTALL)
    
    for block_key, block_content in matches:
        name = re.search(r"'name':\s*'([^']+)'", block_content)
        weight = re.search(r"'weight':\s*(\d+)", block_content)
        enabled = re.search(r"'enabled':\s*(True|False)", block_content)
        
        if name and weight and enabled:
            blocks[block_key] = {
                'name': name.group(1),
                'weight': int(weight.group(1)),
                'enabled': enabled.group(1) == 'True'
            }
    
    return blocks if blocks else None


def validate_blocks_against_catalog(blocks: Dict, strategy_name: str) -> bool:
    """
    Validate blocks exist in catalog (ERROR and HALT if not)
    
    UPDATED: Strips numeric suffixes (_0, _1, _2) before catalog lookup
    to support multiple instances of same block type (from Strategy Builder fix).
    
    Example:
        hod_0 -> checks 'hod' in catalog ✅
        hod_1 -> checks 'hod' in catalog ✅
        fvg_0 -> checks 'fvg' in catalog ✅
    """
    
    def strip_numeric_suffix(block_key: str) -> str:
        """Strip _0, _1, _2, etc. from block key to get base name"""
        # Pattern: _\d+$ (underscore followed by digits at end)
        return re.sub(r'_\d+$', '', block_key)
    
    # Check blocks against catalog using base names
    unknown_blocks = []
    for key in blocks:
        base_name = strip_numeric_suffix(key)
        if base_name not in BUILDING_BLOCK_CATALOG:
            unknown_blocks.append((key, base_name))
    
    if unknown_blocks:
        print("\n" + "="*80)
        print("❌ ERROR: UNIVERSAL OPTIMIZER BLOCKS MISMATCH")
        print("="*80)
        print(f"\nStrategy: {strategy_name}")
        print(f"Found {len(unknown_blocks)} unknown block(s):\n")
        
        for block_key, base_name in unknown_blocks:
            print(f"   ❌ '{block_key}' (base: '{base_name}') - NOT IN CATALOG")
            print(f"      Name: {blocks[block_key].get('name', 'N/A')}")
            print(f"      Weight: {blocks[block_key].get('weight', 'N/A')}")
            print(f"      Enabled: {blocks[block_key].get('enabled', 'N/A')}\n")
        
        print("REQUIRED ACTION:")
        print("1. Add blocks to BUILDING_BLOCK_CATALOG in catalog.py")
        print("2. Specify: category, type, weight_range")
        print("3. Re-run optimizer")
        print("="*80 + "\n")
        
        return False
    
    return True


def apply_config_to_strategy_file(
    strategy_module_name: str,
    config: OptimizationConfig,
    performance: ConfigPerformance
) -> bool:
    """Auto-apply optimized configuration to strategy file"""
    # __file__ is in: src/strategies/universal_optimizer/modules/file_operations.py
    # parent = modules, parent.parent = universal_optimizer, parent.parent.parent = strategies
    strategy_path = Path(__file__).parent.parent.parent / f'{strategy_module_name}.py'
    
    if not strategy_path.exists():
        return False
    
    with open(strategy_path) as f:
        content = f.read()
    
    # Update min_confluence
    content = re.sub(
        r"self\.min_confluence\s*=\s*\d+",
        f"self.min_confluence = {config.min_confluence}",
        content
    )
    
    # Update min_risk_reward
    content = re.sub(
        r"self\.min_risk_reward\s*=\s*[\d.]+",
        f"self.min_risk_reward = {config.min_risk_reward}",
        content
    )
    
    # Update block weights
    for block_name, block_config in config.blocks.items():
        pattern = rf"(self\.blocks\['{block_name}'\]\s*=\s*\{{[^}}]*'weight':\s*)\d+"
        replacement = rf"\g<1>{block_config['weight']}"
        content = re.sub(pattern, replacement, content)
    
    # Write back
    with open(strategy_path, 'w') as f:
        f.write(content)
    
    # Add optimization comment
    add_optimization_comment(strategy_path, config, performance)
    
    return True


def add_optimization_comment(path: Path, config: OptimizationConfig, perf: ConfigPerformance):
    """Add comment block with optimization results"""
    with open(path) as f:
        content = f.read()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    comment = f"""
# ============================================================================
# OPTIMIZED: {timestamp}
# Trades: {perf.total_trades}, Win Rate: {perf.win_rate_pct:.1f}%, PF: {perf.profit_factor:.2f}
# Net PnL: ${perf.net_pnl:.2f} ({perf.net_return_pct:+.2f}%)
# Fees: ${perf.total_fees:.2f}
# Sharpe: {perf.sharpe_ratio:.2f}, Max DD: {perf.max_drawdown_pct:.2f}%
# ============================================================================
"""
    
    # Insert after class definition
    if 'class ' in content:
        lines = content.split('\n')
        insert_idx = None
        
        for i, line in enumerate(lines):
            if line.strip().startswith('class '):
                # Find end of docstring
                for j in range(i+1, len(lines)):
                    if '"""' in lines[j] and j > i+1:
                        insert_idx = j + 1
                        break
                break
        
        if insert_idx:
            lines.insert(insert_idx, comment)
            content = '\n'.join(lines)
    
    with open(path, 'w') as f:
        f.write(content)
