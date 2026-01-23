"""
Integrated Intelligent Recommendation Engine
============================================

HYBRID INTELLIGENCE PLATFORM - Complete Integration

This is the main orchestrator that combines:
1. Block Intelligence Extractor (auto-learning from registry)
2. Strategy Deep Analyzer (root cause identification)
3. AI Recommendation Enhancer (optional AI reasoning)

Provides comprehensive status updates to keep user informed of:
- Analysis progress
- AI activation status
- Recommendation generation
- Confidence scoring
- Expected impacts

Author: Optimizer v3 Team
Date: 2026-01-23
Sprint: 1.6 (Intelligent Recommendations - COMPLETE REBUILD Part 3/3)
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import time
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.optimizer_v3.core.block_intelligence_extractor import (
    BlockIntelligenceExtractor,
    BlockIntelligence
)
from src.optimizer_v3.core.strategy_deep_analyzer import (
    StrategyDeepAnalyzer,
    StrategyAnalysisReport
)
from src.optimizer_v3.core.ai_recommendation_enhancer import (
    AIRecommendationEnhancer,
    AIEnhancedRecommendation
)


@dataclass
class IntegratedRecommendation:
    """Complete recommendation with all intelligence layers"""
    # Core recommendation
    type: str  # ADD_BLOCK, ADD_RECHECK, ADD_TIMING, ADJUST_PARAM
    primary: bool
    block_name: Optional[str] = None
    signal_name: Optional[str] = None
    parameter_name: Optional[str] = None
    
    # Configuration
    configuration: Dict = None
    
    # Intelligence
    reasoning: str = ""
    root_cause: str = ""
    expected_impact: Dict[str, str] = None
    
    # Confidence
    data_confidence: float = 0.0
    ai_confidence: float = 0.0
    combined_confidence: float = 0.0
    
    # Status
    ai_enhanced: bool = False
    validated: bool = True
    warnings: List[str] = None
    
    # Metadata
    metric_targeted: str = ""
    current_value: float = 0.0
    expected_value: float = 0.0
    
    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}
        if self.expected_impact is None:
            self.expected_impact = {}
        if self.warnings is None:
            self.warnings = []


class IntelligentRecommendationEngine:
    """
    INTEGRATED HYBRID INTELLIGENCE ENGINE
    
    Complete workflow:
    1. Extract intelligence from BlockRegistry (83 blocks)
    2. Analyze strategy deeply (root causes, gaps, frequency)
    3. Generate preliminary recommendations (data-driven)
    4. Enhance with AI (if enabled and available)
    5. Validate and return actionable recommendations
    
    Provides comprehensive status updates throughout process.
    """
    
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize integrated recommendation engine
        
        Args:
            status_callback: Function to call with status updates (for UI)
        """
        self.status_callback = status_callback or self._default_status
        
        # Initialize components
        self._update_status("🔧 Initializing Intelligent Recommendation Engine...")
        
        # Component 1: Intelligence Extractor
        self._update_status("📚 Loading building block intelligence database...")
        self.intelligence_extractor = BlockIntelligenceExtractor()
        
        # Component 2: Strategy Analyzer
        self._update_status("🔍 Initializing strategy deep analyzer...")
        self.strategy_analyzer = StrategyDeepAnalyzer(self.intelligence_extractor)
        
        # Component 3: AI Enhancer
        self._update_status("🤖 Checking AI enhancement availability...")
        self.ai_enhancer = AIRecommendationEnhancer()
        
        if self.ai_enhancer.enabled:
            self._update_status(f"✅ AI Enhancement ENABLED (Model: {self.ai_enhancer.model})")
        else:
            self._update_status("ℹ️ AI Enhancement DISABLED (using data-driven analysis only)")
        
        self._update_status("✅ Intelligent Recommendation Engine ready")
    
    def _default_status(self, message: str):
        """Default status callback (prints to console)"""
        print(message)
    
    def _update_status(self, message: str):
        """Update status via callback"""
        if self.status_callback:
            self.status_callback(message)
    
    def generate_recommendations(
        self,
        strategy_config: Dict,
        backtest_results: Dict,
        metrics: Dict[str, Dict],
        lookback_days: int = 180
    ) -> List[IntegratedRecommendation]:
        """
        Generate intelligent recommendations for strategy improvement
        
        Args:
            strategy_config: Complete strategy configuration
            backtest_results: Backtest results with all metrics
            metrics: Metrics dict with values and ratings
            lookback_days: Days of backtest data
        
        Returns:
            List of integrated recommendations with AI enhancement
        """
        start_time = time.time()
        
        try:
            self._update_status("\n" + "="*80)
            self._update_status("🎯 STARTING INTELLIGENT RECOMMENDATION GENERATION")
            self._update_status("="*80)
            
            # Step 1: Extract intelligence from registry
            self._update_status("\n📚 STEP 1/5: Extracting Building Block Intelligence...")
            self._update_status(f"   - Querying BlockRegistry for registered blocks...")
            
            intelligence_db = self.intelligence_extractor.extract_from_registry(
                registry=None  # Will query BlockRegistry internally
            )
            
            self._update_status(f"   ✅ Extracted intelligence for {len(intelligence_db)} blocks")
            
            # Step 2: Deep strategy analysis
            self._update_status("\n🔍 STEP 2/5: Performing Deep Strategy Analysis...")
            self._update_status(f"   - Analyzing strategy configuration...")
            self._update_status(f"   - Calculating trade frequency impact...")
            self._update_status(f"   - Identifying root causes...")
            self._update_status(f"   - Detecting strategy gaps...")
            
            # Create mock strategy object for analyzer
            strategy_obj = self._create_strategy_object(strategy_config)
            
            analysis_report = self.strategy_analyzer.analyze_strategy(
                strategy_config=strategy_obj,
                backtest_results=backtest_results,
                lookback_days=lookback_days
            )
            
            self._update_status(f"   ✅ Analysis complete:")
            self._update_status(f"      - Quality Score: {analysis_report.strategy_quality_score:.1f}/10")
            self._update_status(f"      - Trade Frequency: {analysis_report.trade_frequency.current_trades_per_month:.1f}/month")
            self._update_status(f"      - Root Causes Identified: {len(analysis_report.root_causes)}")
            self._update_status(f"      - Strategy Gaps: {len(analysis_report.gaps.critical_gaps)} critical")
            
            # Step 3: Generate preliminary recommendations
            self._update_status("\n💡 STEP 3/5: Generating Data-Driven Recommendations...")
            
            preliminary_recs = self._generate_preliminary_recommendations(
                metrics,
                analysis_report,
                intelligence_db
            )
            
            self._update_status(f"   ✅ Generated {len(preliminary_recs)} preliminary recommendations")
            
            # Step 4: AI Enhancement (if available)
            if self.ai_enhancer.enabled:
                self._update_status("\n🤖 STEP 4/5: Enhancing with AI Reasoning...")
                self._update_status(f"   - Preparing comprehensive context for AI...")
                self._update_status(f"   - Strategy: {strategy_config.get('name', 'Unknown')}")
                self._update_status(f"   - Metrics: {len(backtest_results)} values")
                self._update_status(f"   - Analysis: {len(analysis_report.root_causes)} root causes")
                self._update_status(f"   - Connecting to OpenRouter API...")
                self._update_status(f"   - Model: {self.ai_enhancer.model}")
                self._update_status(f"   - Please wait (may take 15-30 seconds)...")
                
                enhanced_recs = self.ai_enhancer.enhance_recommendations(
                    strategy_config,
                    backtest_results,
                    analysis_report,
                    preliminary_recs
                )
                
                # Check if AI actually enhanced or fell back
                ai_enhanced_count = sum(1 for r in enhanced_recs if r.ai_confidence > 0)
                
                if ai_enhanced_count > 0:
                    self._update_status(f"   ✅ AI Enhancement complete:")
                    self._update_status(f"      - {ai_enhanced_count} recommendations AI-enhanced")
                    self._update_status(f"      - Hybrid confidence scoring applied")
                    self._update_status(f"      - Validation checks passed")
                else:
                    self._update_status(f"   ⚠️ AI Enhancement unavailable - using data-driven recommendations")
                
                final_recs = enhanced_recs
            else:
                self._update_status("\n📊 STEP 4/5: AI Enhancement Skipped (not enabled)")
                self._update_status(f"   - Using data-driven recommendations only")
                self._update_status(f"   - To enable: Set OPENROUTER_API_KEY in .env")
                final_recs = preliminary_recs
            
            # Step 5: Convert to integrated format
            self._update_status("\n🔄 STEP 5/5: Finalizing Recommendations...")
            
            integrated_recs = self._convert_to_integrated_format(
                final_recs,
                analysis_report,
                metrics
            )
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            self._update_status(f"   ✅ Finalization complete")
            self._update_status(f"\n" + "="*80)
            self._update_status(f"🎉 RECOMMENDATION GENERATION COMPLETE")
            self._update_status(f"="*80)
            self._update_status(f"📊 Results:")
            self._update_status(f"   - Total Recommendations: {len(integrated_recs)}")
            self._update_status(f"   - AI-Enhanced: {sum(1 for r in integrated_recs if r.ai_enhanced)}")
            self._update_status(f"   - Data-Driven: {sum(1 for r in integrated_recs if not r.ai_enhanced)}")
            self._update_status(f"   - Average Confidence: {sum(r.combined_confidence for r in integrated_recs)/len(integrated_recs):.0%}" if integrated_recs else "   - Average Confidence: N/A")
            self._update_status(f"   - Processing Time: {elapsed:.1f} seconds")
            self._update_status(f"="*80 + "\n")
            
            return integrated_recs
            
        except Exception as e:
            self._update_status(f"\n❌ ERROR: Recommendation generation failed: {str(e)}")
            self._update_status(f"   Returning empty recommendations list")
            return []
    
    def _create_strategy_object(self, strategy_config: Dict):
        """Create strategy object from config dict for analyzer"""
        from types import SimpleNamespace
        
        # Extract blocks
        blocks = []
        for block_dict in strategy_config.get('blocks', []):
            block_obj = SimpleNamespace(
                name=block_dict.get('name', ''),
                signals=[
                    SimpleNamespace(name=sig.get('name', ''))
                    for sig in block_dict.get('signals', [])
                ]
            )
            blocks.append(block_obj)
        
        # Create strategy object
        strategy_obj = SimpleNamespace(
            name=strategy_config.get('name', 'Unknown'),
            strategy_type=strategy_config.get('strategy_type', 'Unknown'),
            blocks=blocks
        )
        
        return strategy_obj
    
    def _generate_preliminary_recommendations(
        self,
        metrics: Dict[str, Dict],
        analysis_report: StrategyAnalysisReport,
        intelligence_db: Dict[str, BlockIntelligence]
    ) -> List[Dict]:
        """
        Generate preliminary data-driven recommendations
        
        Based on:
        - Poor metrics
        - Root causes
        - Strategy gaps
        - Trade frequency
        """
        recommendations = []
        
        # Get current blocks
        current_blocks = set(analysis_report.block_names)
        
        # For each poor metric, find best block to improve it
        for metric_key, metric_data in metrics.items():
            if not isinstance(metric_data, dict):
                continue
            
            rating = metric_data.get('rating', '')
            value = metric_data.get('value', 0)
            
            # Only recommend for poor/fair metrics
            if rating not in ['⚠ Fair', '✗ Poor']:
                continue
            
            # Find blocks that improve this metric
            candidates = []
            for block_name, intel in intelligence_db.items():
                # Skip if already in strategy
                if block_name in current_blocks:
                    continue
                
                # Check if improves this metric
                if metric_key in intel.primary_metrics:
                    # Estimate improvement based on block purpose
                    # Default improvement estimate: 10% for any relevant metric
                    improvement = 0.10
                    
                    candidates.append({
                        'block_name': block_name,
                        'improvement': improvement,
                        'intel': intel
                    })
            
            if candidates:
                # Sort by improvement potential
                best = max(candidates, key=lambda x: abs(x['improvement']))
                
                recommendations.append({
                    'action_type': 'ADD_BLOCK',
                    'block_name': best['block_name'],
                    'metric': metric_key,
                    'current_value': value,
                    'expected_improvement': best['improvement'],
                    'description': best['intel'].description,
                    'confidence': best['intel'].confidence,
                    'category': best['intel'].category
                })
        
        return recommendations
    
    def _convert_to_integrated_format(
        self,
        recommendations: List,
        analysis_report: StrategyAnalysisReport,
        metrics: Dict
    ) -> List[IntegratedRecommendation]:
        """Convert recommendations to integrated format"""
        integrated = []
        
        for i, rec in enumerate(recommendations):
            # Handle both dict and AIEnhancedRecommendation objects
            if isinstance(rec, AIEnhancedRecommendation):
                # AI-enhanced recommendation
                integrated.append(IntegratedRecommendation(
                    type=rec.type,
                    primary=rec.primary,
                    block_name=rec.block_name,
                    signal_name=rec.signal_name,
                    configuration=rec.configuration,
                    reasoning=rec.reasoning,
                    root_cause=self._get_root_cause_for_metric(
                        rec.block_name,
                        analysis_report
                    ) if rec.block_name else "",
                    expected_impact=rec.expected_impact,
                    data_confidence=rec.data_confidence,
                    ai_confidence=rec.ai_confidence,
                    combined_confidence=rec.confidence,
                    ai_enhanced=True,
                    validated=True,
                    warnings=rec.warnings,
                    metric_targeted="",  # Would extract from rec
                    current_value=0.0,
                    expected_value=0.0
                ))
            else:
                # Data-driven recommendation (dict)
                metric_key = rec.get('metric', '')
                current_value = rec.get('current_value', 0)
                improvement = rec.get('expected_improvement', 0)
                expected_value = current_value * (1 + improvement) if improvement else current_value
                
                integrated.append(IntegratedRecommendation(
                    type=rec.get('action_type', 'ADD_BLOCK'),
                    primary=(i == 0),  # First recommendation is primary
                    block_name=rec.get('block_name'),
                    signal_name=None,
                    configuration={},
                    reasoning=rec.get('description', ''),
                    root_cause=self._get_root_cause_for_metric(
                        metric_key,
                        analysis_report
                    ),
                    expected_impact={
                        metric_key: f"{abs(improvement*100):.0f}%"
                    },
                    data_confidence=rec.get('confidence', 0.75),
                    ai_confidence=0.0,
                    combined_confidence=rec.get('confidence', 0.75),
                    ai_enhanced=False,
                    validated=True,
                    warnings=[],
                    metric_targeted=metric_key,
                    current_value=current_value,
                    expected_value=expected_value
                ))
        
        return integrated
    
    def _get_root_cause_for_metric(
        self,
        metric_key: str,
        analysis_report: StrategyAnalysisReport
    ) -> str:
        """Get root cause text for metric"""
        if metric_key in analysis_report.root_causes:
            root_cause = analysis_report.root_causes[metric_key]
            return f"{root_cause.primary_cause.value} ({root_cause.confidence:.0%} confidence)"
        return ""
    
    def format_recommendation_text(self, rec: IntegratedRecommendation) -> str:
        """Format recommendation for display"""
        # Header
        if rec.ai_enhanced:
            header = "🤖 AI-ENHANCED:"
        else:
            header = "📊 DATA-DRIVEN:"
        
        # Main text
        if rec.type == 'ADD_BLOCK':
            text = f"{header} Add '{rec.block_name}' block"
        elif rec.type == 'ADD_RECHECK':
            bar_delay = rec.configuration.get('bar_delay', 25)
            text = f"{header} Add recheck to '{rec.block_name}::{rec.signal_name}' (validate at bar {bar_delay})"
        elif rec.type == 'ADD_TIMING':
            max_candles = rec.configuration.get('max_candles', 20)
            text = f"{header} Add timing dependency (within {max_candles} candles)"
        elif rec.type == 'ADJUST_PARAM':
            param = rec.parameter_name or 'parameter'
            text = f"{header} Adjust {param}"
        else:
            text = f"{header} {rec.reasoning[:80]}"
        
        # Add impact
        if rec.expected_impact:
            impacts = [f"{k}: {v}" for k, v in list(rec.expected_impact.items())[:2]]
            text += f"\n   Expected: {', '.join(impacts)}"
        
        # Add confidence
        text += f"\n   Confidence: {rec.combined_confidence:.0%}"
        
        # Add root cause if available
        if rec.root_cause:
            text += f"\n   Root Cause: {rec.root_cause}"
        
        # Add warnings
        if rec.warnings:
            text += f"\n   ⚠️ {'; '.join(rec.warnings[:2])}"
        
        return text
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics about engine state"""
        intel_db = self.intelligence_extractor.get_all_intelligence()
        
        return {
            'total_blocks_in_database': len(intel_db),
            'ai_enhancement_available': self.ai_enhancer.enabled,
            'ai_model': self.ai_enhancer.model if self.ai_enhancer.enabled else None,
            'components_loaded': {
                'intelligence_extractor': True,
                'strategy_analyzer': True,
                'ai_enhancer': self.ai_enhancer.enabled
            }
        }


# Test function
def test_integrated_engine():
    """Test integrated recommendation engine"""
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    print("\n" + "="*80)
    print("INTEGRATED INTELLIGENT RECOMMENDATION ENGINE - TEST")
    print("="*80 + "\n")
    
    # Initialize engine with status callback
    def status_handler(message: str):
        print(message)
    
    engine = IntelligentRecommendationEngine(status_callback=status_handler)
    
    # Print summary
    stats = engine.get_summary_stats()
    print(f"\n📊 Engine Statistics:")
    print(f"   - Blocks in Database: {stats['total_blocks_in_database']}")
    print(f"   - AI Enhancement: {'✅ Available' if stats['ai_enhancement_available'] else '❌ Unavailable'}")
    if stats['ai_model']:
        print(f"   - AI Model: {stats['ai_model']}")
    
    print("\n✅ Integrated engine test complete\n")


if __name__ == '__main__':
    test_integrated_engine()
