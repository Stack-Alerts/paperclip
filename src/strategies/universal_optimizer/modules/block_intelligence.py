"""
Block Intelligence System

Tracks optimization iterations, identifies weak blocks, recommends replacements.
Builds historical performance database across all strategies.
"""

import json
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from .data_classes import StrategyIteration, BlockPerformance, ConfigPerformance
from .catalog import BUILDING_BLOCK_CATALOG


def load_strategy_iterations(strategy_id: str) -> StrategyIteration:
    """Load iteration history for strategy"""
    # Need 5 parents to get to project root from modules/
    project_root = Path(__file__).parent.parent.parent.parent.parent
    path = project_root / 'data' / 'optimization_history' / f'{strategy_id}_iterations.json'
    
    if path.exists():
        with open(path) as f:
            data = json.load(f)
            # Reconstruct BlockPerformance objects
            if 'block_performance' in data:
                block_perf = {}
                for name, perf_data in data['block_performance'].items():
                    block_perf[name] = BlockPerformance(**perf_data)
                data['block_performance'] = block_perf
            return StrategyIteration(**data)
    
    return StrategyIteration(strategy_id=strategy_id)


def save_strategy_iterations(iteration: StrategyIteration):
    """Save iteration history"""
    # Need 5 parents to get to project root from modules/
    project_root = Path(__file__).parent.parent.parent.parent.parent
    path = project_root / 'data' / 'optimization_history' / f'{iteration.strategy_id}_iterations.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(iteration.to_dict(), f, indent=2)
    
    # Update global block performance database
    update_global_block_db(iteration)


def identify_weakest_block(iteration: StrategyIteration) -> Optional[str]:
    """Identify weakest performing block (after 5 iterations)"""
    if iteration.iteration_count < 5:
        return None
    
    return iteration.get_weakest_block()


def recommend_replacement_block(
    weak_block: str,
    strategy_blocks: Dict,
    iteration: StrategyIteration
) -> List[Tuple[str, float]]:
    """Recommend replacement blocks based on historical performance"""
    recommendations = []
    
    # Load global block performance
    global_perf = load_global_block_performance()
    
    # Get weak block metadata
    weak_meta = BUILDING_BLOCK_CATALOG.get(weak_block, {})
    weak_category = weak_meta.get('category')
    weak_type = weak_meta.get('type')
    
    # Score all blocks
    for block_name, perf_data in global_perf.items():
        if block_name in strategy_blocks:
            continue  # Already in strategy
        
        score = 0
        block_meta = BUILDING_BLOCK_CATALOG.get(block_name, {})
        
        # Same category bonus
        if block_meta.get('category') == weak_category:
            score += 10
        
        # Same type bonus
        if block_meta.get('type') == weak_type:
            score += 20
        
        # High success rate bonus
        success_rate = perf_data.get('success_rate', 0)
        score += min(success_rate / 100 * 30, 30)
        
        # New block bonus
        score += 40
        
        recommendations.append((block_name, score))
    
    # Sort by score
    recommendations.sort(key=lambda x: x[1], reverse=True)
    
    return recommendations[:5]


def update_global_block_db(iteration: StrategyIteration):
    """Update global block performance database"""
    # Need 5 parents to get to project root from modules/
    project_root = Path(__file__).parent.parent.parent.parent.parent
    db_path = project_root / 'data' / 'optimization_history' / 'block_performance_db.json'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing
    if db_path.exists():
        with open(db_path) as f:
            global_db = json.load(f)
    else:
        global_db = {}
    
    # Update from this iteration
    for block_name, block_perf in iteration.block_performance.items():
        if block_name not in global_db:
            global_db[block_name] = block_perf.to_dict()
        else:
            # Merge performance data (simple average for now)
            existing = global_db[block_name]
            new_data = block_perf.to_dict()
            
            total_uses = existing['total_uses'] + new_data['total_uses']
            existing['total_uses'] = total_uses
            existing['successful_uses'] += new_data['successful_uses']
            existing['success_rate'] = (existing['successful_uses'] / total_uses * 100) if total_uses > 0 else 0
            
            # Running averages
            existing['avg_contribution'] = (
                (existing['avg_contribution'] * existing['total_uses'] + 
                 new_data['avg_contribution'] * new_data['total_uses']) / total_uses
            )
            existing['avg_weight'] = (
                (existing['avg_weight'] * existing['total_uses'] + 
                 new_data['avg_weight'] * new_data['total_uses']) / total_uses
            )
    
    # Save
    with open(db_path, 'w') as f:
        json.dump(global_db, f, indent=2)


def load_global_block_performance() -> Dict:
    """Load global block performance database"""
    # Need 5 parents to get to project root from modules/
    project_root = Path(__file__).parent.parent.parent.parent.parent
    db_path = project_root / 'data' / 'optimization_history' / 'block_performance_db.json'
    
    if db_path.exists():
        with open(db_path) as f:
            return json.load(f)
    
    return {}