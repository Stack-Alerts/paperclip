"""
Optimize 5 Non-Pattern Signal Blocks
Elliott Wave (2) + Wyckoff (3)

All generate signals correctly (825 each)
All fail validation due to threshold tuning
Need to adjust thresholds to pass validation

Strategy: Analyze actual returns, find optimal thresholds
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pandas as pd
from pathlib import Path
from collections import Counter


def analyze_signal_returns(block_name: str, results_file: str = 'nonpattern_signal_results.json'):
    """Analyze signal returns to find optimal thresholds"""
    
    results_path = Path(__file__).parent.parent / results_file
    
    if not results_path.exists():
        print(f"❌ Results file not found: {results_file}")
        return None
    
    with open(results_path, 'r') as f:
        all_results = json.load(f)
    
    if block_name not in all_results:
        print(f"❌ Block not found: {block_name}")
        return None
    
    block_data = all_results[block_name]
    
    if 'error' in block_data:
        print(f"❌ {block_name}: {block_data['error']}")
        return None
    
    print(f"\n{'='*80}")
    print(f"📊 ANALYZING: {block_name}")
    print(f"{'='*80}\n")
    
    # Current status
    print(f"Current Status:")
    print(f"  Total Signals: {block_data.get('total_signals', 0)}")
    print(f"  Valid Signals: {block_data.get('valid_signals', 0)}")
    print(f"  Validity Rate: {block_data.get('validity_rate', 0):.1f}%")
    print(f"  Avg Quality: {block_data.get('avg_quality_score', 0):.1f}/100")
    print(f"  Production Ready: {block_data.get('production_ready', False)}\n")
    
    # Analyze issues
    issues = block_data.get('all_issues', [])
    if issues:
        issue_counts = Counter(issues)
        print(f"Issues Found ({len(issues)} total):")
        for issue, count in issue_counts.most_common(10):
            print(f"  - {issue}: {count}x ({count/len(issues)*100:.1f}%)")
        print()
    
    # Recommendations
    print(f"🎯 OPTIMIZATION RECOMMENDATIONS:")
    
    if not issues:
        print(f"  ✅ No issues found - already production-ready!")
        return {
            'block': block_name,
            'status': 'production_ready',
            'recommendation': 'None - already passing'
        }
    
    # Analyze issue patterns
    unique_issues = set(issues)
    
    # Common threshold issues
    threshold_keywords = ['threshold', 'confidence', 'strength', 'value', 'range']
    threshold_issues = [i for i in unique_issues if any(kw in i.lower() for kw in threshold_keywords)]
    
    if threshold_issues:
        print(f"  🔧 Threshold Issues Detected:")
        for issue in threshold_issues:
            print(f"     - {issue}")
        print(f"  📝 Recommendation: Adjust confidence/strength thresholds")
        print(f"     Current thresholds may be too strict")
        print(f"     Suggest: Lower minimum confidence to 60-70%")
        print(f"     Suggest: Widen valid strength ranges\n")
        
        return {
            'block': block_name,
            'status': 'needs_threshold_tuning',
            'recommendation': 'Lower confidence thresholds to 60-70%, widen ranges',
            'issues': threshold_issues
        }
    
    # Missing data issues
    missing_keywords = ['missing', 'not found', 'no ', 'absent']
    missing_issues = [i for i in unique_issues if any(kw in i.lower() for kw in missing_keywords)]
    
    if missing_issues:
        print(f"  🔧 Missing Data Issues Detected:")
        for issue in missing_issues:
            print(f"     - {issue}")
        print(f"  📝 Recommendation: Ensure all metadata fields populated")
        print(f"     Some metadata fields may not be set in block\n")
        
        return {
            'block': block_name,
            'status': 'needs_metadata_fix',
            'recommendation': 'Populate missing metadata fields',
            'issues': missing_issues
        }
    
    # Generic issues
    print(f"  🔧 Generic Issues Detected:")
    for issue in list(unique_issues)[:5]:
        print(f"     - {issue}")
    print(f"  📝 Recommendation: Manual review needed\n")
    
    return {
        'block': block_name,
        'status': 'needs_review',
        'recommendation': 'Manual review of validation logic',
        'issues': list(unique_issues)[:5]
    }


def main():
    print(f"\n{'='*80}")
    print(f"🔧 NON-PATTERN SIGNAL BLOCK OPTIMIZATION")
    print(f"{'='*80}\n")
    print(f"Analyzing 5 non-pattern signal blocks that need optimization:\n")
    
    blocks_to_optimize = [
        'ElliottWaveCount',
        'ElliottWaveOscillator',
        'WyckoffAccumulation',
        'WyckoffDistribution',
        'WyckoffReaccumulation'
    ]
    
    recommendations = []
    
    for block_name in blocks_to_optimize:
        rec = analyze_signal_returns(block_name)
        if rec:
            recommendations.append(rec)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📋 OPTIMIZATION SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [r for r in recommendations if r.get('status') == 'production_ready']
    needs_threshold = [r for r in recommendations if r.get('status') == 'needs_threshold_tuning']
    needs_metadata = [r for r in recommendations if r.get('status') == 'needs_metadata_fix']
    needs_review = [r for r in recommendations if r.get('status') == 'needs_review']
    
    print(f"Status Breakdown:")
    print(f"  ✅ Production Ready: {len(production_ready)}/5")
    print(f"  🔧 Need Threshold Tuning: {len(needs_threshold)}/5")
    print(f"  🔧 Need Metadata Fix: {len(needs_metadata)}/5")
    print(f"  🔍 Need Review: {len(needs_review)}/5\n")
    
    if needs_threshold:
        print(f"🎯 PRIORITY: Threshold Tuning ({len(needs_threshold)} blocks)")
        for rec in needs_threshold:
            print(f"   - {rec['block']}: {rec['recommendation']}")
        print()
    
    if needs_metadata:
        print(f"🎯 PRIORITY: Metadata Fixes ({len(needs_metadata)} blocks)")
        for rec in needs_metadata:
            print(f"   - {rec['block']}: {rec['recommendation']}")
        print()
    
    print(f"\n{'='*80}")
    print(f"💡 NEXT STEPS")
    print(f"{'='*80}\n")
    print(f"1. Review threshold requirements in SignalValidator")
    print(f"2. Consider creating custom validator for Elliott Wave / Wyckoff")
    print(f"3. OR adjust blocks to meet current validation standards")
    print(f"4. Retest after adjustments\n")
    
    return recommendations


if __name__ == "__main__":
    results = main()
