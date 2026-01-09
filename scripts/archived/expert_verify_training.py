"""
EXPERT MODE: Pattern Statistics Verification

Thorough analysis of training results to verify:
1. Pattern distribution across all 64 combinations
2. Data quality and completeness
3. Statistical validity
4. Production readiness

Author: BTC_Engine_v3
Date: December 30, 2025
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from pathlib import Path

from src.detectors.pattern_statistics import PatternStatistics
from src.detectors.pattern_encoder import PatternEncoder

print("="*80)
print("EXPERT MODE: PATTERN STATISTICS VERIFICATION")
print("="*80)

# Load trained statistics
print("\n1. Loading trained database...")
try:
    m_stats = PatternStatistics.load('data/pattern_statistics/m_pattern_stats.pkl')
    w_stats = PatternStatistics.load('data/pattern_statistics/w_pattern_stats.pkl')
    print("   ✅ Databases loaded successfully")
except Exception as e:
    print(f"   ❌ Error loading database: {e}")
    sys.exit(1)

# Analyze M-pattern statistics
print("\n2. Analyzing M-Pattern Statistics (Pivot Highs)...")
print("="*80)

encoder = PatternEncoder()

# Check all 64 patterns
patterns_with_data = []
patterns_without_data = []

for idx in range(64):
    total = m_stats.pivot_high_stats[idx, 2]
    if total > 0:
        patterns_with_data.append(idx)
    else:
        patterns_without_data.append(idx)

print(f"\nPattern Coverage:")
print(f"   Patterns WITH data: {len(patterns_with_data)}/64 ({len(patterns_with_data)/64*100:.1f}%)")
print(f"   Patterns WITHOUT data: {len(patterns_without_data)}/64 ({len(patterns_without_data)/64*100:.1f}%)")

# Detailed analysis of patterns with data
if len(patterns_with_data) > 0:
    print(f"\n   Detailed Breakdown of {len(patterns_with_data)} Patterns WITH Data:")
    print("   " + "-"*76)
    print(f"   {'Idx':<5} {'Total':<8} {'HH%':<8} {'LH%':<8} {'Fib':<8} {'Bars':<8} Description")
    print("   " + "-"*76)
    
    for idx in sorted(patterns_with_data, key=lambda x: m_stats.pivot_high_stats[x, 2], reverse=True):
        pred = m_stats.predict(idx, is_high=True)
        desc = encoder.get_pattern_description(idx)
        print(f"   {idx:<5} {pred.sample_count:<8} {pred.hh_probability:<8.1%} "
              f"{pred.lh_probability:<8.1%} {pred.avg_fib_ratio:<8.2f} "
              f"{pred.expected_bars:<8} {desc[:35]}")

# Show some patterns without data
if len(patterns_without_data) > 0:
    print(f"\n   Sample of Patterns WITHOUT Data (showing first 10):")
    print("   " + "-"*76)
    for idx in patterns_without_data[:10]:
        desc = encoder.get_pattern_description(idx)
        print(f"   {idx:<5} {0:<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {desc[:35]}")

# Statistical Analysis
print("\n3. Statistical Analysis:")
print("="*80)

total_patterns = m_stats.total_patterns_tracked
print(f"\nTotal patterns tracked: {total_patterns}")

if len(patterns_with_data) > 0:
    # Distribution analysis
    totals = [m_stats.pivot_high_stats[idx, 2] for idx in patterns_with_data]
    print(f"\nPattern Distribution:")
    print(f"   Mean per pattern: {np.mean(totals):.1f}")
    print(f"   Median per pattern: {np.median(totals):.1f}")
    print(f"   Std Dev: {np.std(totals):.1f}")
    print(f"   Min: {np.min(totals)}")
    print(f"   Max: {np.max(totals)}")
    
    # Concentration check
    top_pattern_count = m_stats.pivot_high_stats[patterns_with_data[0], 2]
    concentration = (top_pattern_count / total_patterns) * 100
    print(f"\nConcentration Check:")
    print(f"   Top pattern has: {top_pattern_count} samples ({concentration:.1f}% of total)")
    
    if concentration > 50:
        print(f"   ⚠️  WARNING: High concentration in single pattern!")
        print(f"   This suggests limited pattern diversity")

# Check prediction quality
print("\n4. Prediction Quality Check:")
print("="*80)

for idx in patterns_with_data[:5]:  # Check top 5 patterns
    pred = m_stats.predict(idx, is_high=True)
    desc = encoder.get_pattern_description(idx)
    
    print(f"\nPattern {idx}: {desc}")
    print(f"   Samples: {pred.sample_count}")
    print(f"   HH probability: {pred.hh_probability:.1%}")
    print(f"   LH probability: {pred.lh_probability:.1%}")
    print(f"   Confidence: {pred.confidence}")
    print(f"   Should enter: {pred.should_enter()} (LH >= 55%)")
    print(f"   Should skip: {pred.should_skip()} (HH >= 60%)")
    
    # Quality checks
    if pred.sample_count < 10:
        print(f"   ⚠️  WARNING: Low sample count ({pred.sample_count})")
    
    if abs(pred.hh_probability - 0.5) < 0.05:
        print(f"   ℹ️  NOTE: Nearly balanced outcome (no clear edge)")
    
    if pred.hh_probability > 0.60 or pred.lh_probability > 0.60:
        print(f"   ✅ GOOD: Strong directional bias detected!")

# Expert Assessment
print("\n5. EXPERT ASSESSMENT:")
print("="*80)

issues = []
warnings = []
good_signs = []

# Check 1: Pattern coverage
if len(patterns_with_data) < 10:
    issues.append(f"Very low pattern coverage ({len(patterns_with_data)}/64)")
    issues.append("Most patterns have zero samples - this is CRITICAL")
elif len(patterns_with_data) < 30:
    warnings.append(f"Moderate pattern coverage ({len(patterns_with_data)}/64)")
else:
    good_signs.append(f"Good pattern coverage ({len(patterns_with_data)}/64)")

# Check 2: Sample sizes
if len(patterns_with_data) > 0:
    avg_samples = np.mean([m_stats.pivot_high_stats[idx, 2] for idx in patterns_with_data])
    if avg_samples < 10:
        warnings.append(f"Low average samples per pattern ({avg_samples:.1f})")
    elif avg_samples > 50:
        good_signs.append(f"Good sample size ({avg_samples:.1f} per pattern)")

# Check 3: Total patterns
if total_patterns < 100:
    issues.append(f"Very low total patterns ({total_patterns})")
elif total_patterns < 500:
    warnings.append(f"Moderate total patterns ({total_patterns})")
else:
    good_signs.append(f"Good total patterns ({total_patterns})")

# Report
print("\n✅ GOOD SIGNS:")
if good_signs:
    for sign in good_signs:
        print(f"   • {sign}")
else:
    print("   None identified")

print("\n⚠️  WARNINGS:")
if warnings:
    for warning in warnings:
        print(f"   • {warning}")
else:
    print("   None")

print("\n❌ CRITICAL ISSUES:")
if issues:
    for issue in issues:
        print(f"   • {issue}")
else:
    print("   None")

# Overall verdict
print("\n" + "="*80)
print("VERDICT:")
print("="*80)

if issues:
    print("\n❌ NOT PRODUCTION-READY")
    print("\nThe pattern encoder or training logic needs investigation.")
    print("Only 2 patterns out of 64 have data - this is incorrect.")
    print("\nLikely causes:")
    print("1. Pattern encoding logic may be too restrictive")
    print("2. Pivot validation may be filtering too much")
    print("3. Need to verify encoder.encode() is working correctly")
    print("\nRECOMMENDED ACTIONS:")
    print("1. Debug pattern encoder with manual examples")
    print("2. Verify pivot validation logic")
    print("3. Check if oscillator values are properly set")
    print("4. Review encoding formula (trend_bit * 4 + price_bit * 2 + osc_bit)")
elif warnings:
    print("\n⚠️  CONDITIONAL APPROVAL")
    print("\nReady for testing but needs improvement")
    print("Some concerns about pattern diversity")
else:
    print("\n✅ PRODUCTION-READY")
    print("\nStatistics are valid and ready for deployment")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
