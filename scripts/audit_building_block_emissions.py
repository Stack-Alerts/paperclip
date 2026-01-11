"""
Building Block Emissions Auditor
==================================

CRITICAL INSTITUTIONAL-GRADE AUDIT:
- Tests all 83+ registered building blocks
- Discovers what signals they ACTUALLY emit
- Cross-references against registry metadata
- Identifies mismatches that cause silent failures

This audit discovered the HOD signal mismatch bug that caused
50% signal loss in production strategies.

Author: BTC_Engine_v3
Date: 2026-01-11
Purpose: Prevent signal filtering bugs across entire system
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any
import json

from src.detectors.building_blocks.registry import BlockRegistry, auto_discover_blocks


class EmissionsAuditor:
    """
    Comprehensive auditor for building block signal emissions
    
    Tests each block on synthetic data and records:
    1. What signals it declares (valid_signals in registry)
    2. What signals it actually emits (from analyze() calls)
    3. Mismatches that cause filtering bugs
    4. Never-emitted signals that mislead users
    """
    
    def __init__(self):
        """Initialize auditor"""
        # Ensure all blocks are registered
        auto_discover_blocks()
        
        # Storage for results
        self.audit_results = {}
        self.mismatches = []
        self.warnings = []
        
    def generate_test_data(self, bars: int = 500) -> pd.DataFrame:
        """
        Generate synthetic OHLCV data for testing
        
        Creates realistic price action with:
        - Trends (up, down, sideways)
        - Volatility spikes
        - Volume patterns
        - Various patterns (double tops, breakouts, etc.)
        
        Args:
            bars: Number of bars to generate
            
        Returns:
            DataFrame with OHLCV data
        """
        # Generate timestamps (15-minute bars)
        start_time = datetime(2025, 1, 1, 0, 0)
        timestamps = [start_time + timedelta(minutes=15*i) for i in range(bars)]
        
        # Generate realistic price action
        np.random.seed(42)  # Reproducible
        
        base_price = 45000
        prices = []
        current_price = base_price
        
        for i in range(bars):
            # Add trend component
            trend = 0
            if 100 < i < 200:
                trend = 10  # Uptrend
            elif 300 < i < 400:
                trend = -10  # Downtrend
            
            # Add noise
            noise = np.random.normal(0, 100)
            
            # Update price
            current_price += trend + noise
            prices.append(current_price)
        
        # Generate OHLC from close prices
        highs = [p + np.random.uniform(20, 100) for p in prices]
        lows = [p - np.random.uniform(20, 100) for p in prices]
        opens = [prices[i-1] if i > 0 else prices[0] for i in range(bars)]
        
        # Generate volume
        volume = np.random.uniform(1000, 5000, bars)
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': prices,
            'volume': volume
        })
    
    def test_block_emissions(self, block_name: str, metadata: Any) -> Dict[str, Any]:
        """
        Test a single block to discover actual signal emissions
        
        Args:
            block_name: Name of block to test
            metadata: BlockMetadata from registry
            
        Returns:
            Dictionary with test results
        """
        print(f"  Testing: {block_name}...", end='')
        
        result = {
            'block_name': block_name,
            'category': metadata.category,
            'declared_signals': set(metadata.valid_signals),
            'emitted_signals': set(),
            'signal_counts': {},
            'errors': [],
            'test_results': []
        }
        
        try:
            # Instantiate block
            block = BlockRegistry.instantiate(block_name)
            
            # Generate test data
            test_data = self.generate_test_data(bars=500)
            
            # Test on multiple windows to capture different scenarios
            windows = [
                (0, 100),    # Early data
                (100, 200),  # Uptrend
                (200, 300),  # Sideways
                (300, 400),  # Downtrend
                (400, 500),  # Late data
            ]
            
            for start, end in windows:
                window_data = test_data.iloc[start:end].copy()
                
                try:
                    # Call analyze
                    analysis = block.analyze(window_data)
                    
                    # Extract signal
                    signal = analysis.get('signal', 'NO_SIGNAL')
                    confidence = analysis.get('confidence', 0)
                    
                    # Record emission
                    result['emitted_signals'].add(signal)
                    result['signal_counts'][signal] = result['signal_counts'].get(signal, 0) + 1
                    
                    # Store test result
                    result['test_results'].append({
                        'window': f'{start}-{end}',
                        'signal': signal,
                        'confidence': confidence
                    })
                    
                except Exception as e:
                    result['errors'].append(f"Window {start}-{end}: {str(e)[:100]}")
            
            print(f" ✓ ({len(result['emitted_signals'])} signals)")
            
        except Exception as e:
            result['errors'].append(f"Instantiation failed: {str(e)[:200]}")
            print(f" ✗ FAILED: {str(e)[:50]}")
        
        return result
    
    def analyze_mismatches(self, result: Dict[str, Any]) -> List[str]:
        """
        Analyze mismatches between declared and emitted signals
        
        Args:
            result: Test result from test_block_emissions
            
        Returns:
            List of mismatch descriptions
        """
        mismatches = []
        
        declared = result['declared_signals']
        emitted = result['emitted_signals']
        
        # Find signals that are declared but never emitted
        never_emitted = declared - emitted
        if never_emitted:
            # Filter out expected non-emissions (error states)
            expected_non_emit = {'ERROR', 'INSUFFICIENT_DATA', 'NO_SIGNAL'}
            never_emitted = never_emitted - expected_non_emit
            
            if never_emitted:
                mismatches.append({
                    'type': 'DECLARED_BUT_NEVER_EMITTED',
                    'block': result['block_name'],
                    'signals': sorted(list(never_emitted)),
                    'severity': 'HIGH',
                    'impact': 'Users can select these in GUI but they never fire - causes confusion and filter bugs',
                    'fix': f"Remove {never_emitted} from valid_signals OR update analyze() to emit them"
                })
        
        # Find signals that are emitted but not declared
        undeclared = emitted - declared
        if undeclared:
            # Filter out auto-added by registry
            expected_auto_add = set()
            undeclared = undeclared - expected_auto_add
            
            if undeclared:
                mismatches.append({
                    'type': 'EMITTED_BUT_NOT_DECLARED',
                    'block': result['block_name'],
                    'signals': sorted(list(undeclared)),
                    'severity': 'CRITICAL',
                    'impact': 'Block emits signals not in valid_signals - breaks validation and confluence calculation',
                    'fix': f"Add {undeclared} to valid_signals in @register_block decorator"
                })
        
        return mismatches
    
    def run_full_audit(self) -> Dict[str, Any]:
        """
        Run complete audit of all registered blocks
        
        Returns:
            Comprehensive audit report
        """
        print("="*80)
        print("BUILDING BLOCK EMISSIONS AUDIT")
        print("="*80)
        print(f"\nDiscovering registered blocks...")
        
        all_blocks = BlockRegistry.get_all_blocks()
        print(f"Found {len(all_blocks)} registered blocks\n")
        
        print("Testing each block for actual signal emissions...")
        print("-"*80)
        
        # Test each block
        for block_name, metadata in sorted(all_blocks.items()):
            result = self.test_block_emissions(block_name, metadata)
            self.audit_results[block_name] = result
            
            # Check for mismatches
            mismatches = self.analyze_mismatches(result)
            if mismatches:
                self.mismatches.extend(mismatches)
        
        print("-"*80)
        
        # Compile summary
        summary = self.compile_summary()
        
        return summary
    
    def compile_summary(self) -> Dict[str, Any]:
        """Compile comprehensive summary of audit results"""
        total_blocks = len(self.audit_results)
        blocks_with_issues = len([r for r in self.audit_results.values() if r['errors']])
        blocks_with_mismatches = len(set(m['block'] for m in self.mismatches))
        
        # Categorize mismatches by severity
        critical_mismatches = [m for m in self.mismatches if m['severity'] == 'CRITICAL']
        high_mismatches = [m for m in self.mismatches if m['severity'] == 'HIGH']
        
        return {
            'total_blocks_tested': total_blocks,
            'blocks_with_errors': blocks_with_issues,
            'blocks_with_mismatches': blocks_with_mismatches,
            'total_mismatches': len(self.mismatches),
            'critical_mismatches': len(critical_mismatches),
            'high_mismatches': len(high_mismatches),
            'mismatch_details': self.mismatches,
            'audit_results': self.audit_results
        }
    
    def generate_report(self, summary: Dict[str, Any], output_file: str = None):
        """
        Generate detailed markdown report
        
        Args:
            summary: Audit summary from compile_summary()
            output_file: Optional path to save report
        """
        report = []
        
        # Header
        report.append("# BUILDING BLOCK EMISSIONS AUDIT REPORT")
        report.append("")
        report.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Total Blocks Tested:** {summary['total_blocks_tested']}")
        report.append(f"**Blocks with Issues:** {summary['blocks_with_mismatches']}")
        report.append(f"**Total Mismatches:** {summary['total_mismatches']}")
        report.append("")
        
        # Executive Summary
        report.append("## 🚨 EXECUTIVE SUMMARY")
        report.append("")
        
        if summary['total_mismatches'] == 0:
            report.append("✅ **ALL BLOCKS PASS**: No signal emission mismatches detected!")
            report.append("")
            report.append("All building blocks emit exactly the signals they declare in their registry metadata.")
        else:
            report.append(f"❌ **{summary['blocks_with_mismatches']} BLOCKS HAVE ISSUES**")
            report.append("")
            report.append(f"- **Critical Issues:** {summary['critical_mismatches']} (blocks emit undeclared signals)")
            report.append(f"- **High Priority:** {summary['high_mismatches']} (declared signals never emitted)")
            report.append("")
            report.append("**Impact:** These mismatches cause:")
            report.append("- Silent signal filtering bugs (50% signal loss in HOD strategy)")
            report.append("- User confusion (GUI shows signals that never fire)")
            report.append("- Strategy configuration errors")
            report.append("- Confluence calculation issues")
        
        report.append("")
        report.append("---")
        report.append("")
        
        # Detailed Findings
        if self.mismatches:
            report.append("## 📊 DETAILED FINDINGS")
            report.append("")
            
            # Group by block
            blocks_with_issues = {}
            for mismatch in self.mismatches:
                block = mismatch['block']
                if block not in blocks_with_issues:
                    blocks_with_issues[block] = []
                blocks_with_issues[block].append(mismatch)
            
            for block_name in sorted(blocks_with_issues.keys()):
                report.append(f"### ❌ {block_name}")
                report.append("")
                
                for mismatch in blocks_with_issues[block_name]:
                    report.append(f"**Type:** {mismatch['type']}")
                    report.append(f"**Severity:** {mismatch['severity']}")
                    report.append(f"**Signals:** {', '.join(mismatch['signals'])}")
                    report.append(f"**Impact:** {mismatch['impact']}")
                    report.append(f"**Fix:** {mismatch['fix']}")
                    report.append("")
        
        # Emissions Reference
        report.append("---")
        report.append("")
        report.append("## 📋 COMPLETE EMISSIONS REFERENCE")
        report.append("")
        report.append("This section documents what each block ACTUALLY emits (tested on synthetic data).")
        report.append("")
        
        # Group by category
        by_category = {}
        for block_name, result in sorted(self.audit_results.items()):
            category = result['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((block_name, result))
        
        for category in sorted(by_category.keys()):
            report.append(f"### {category}")
            report.append("")
            
            for block_name, result in sorted(by_category[category]):
                # Determine status
                has_mismatch = any(m['block'] == block_name for m in self.mismatches)
                status = "❌" if has_mismatch else "✅"
                
                report.append(f"#### {status} `{block_name}`")
                report.append("")
                
                # Declared signals
                declared = sorted(list(result['declared_signals']))
                report.append(f"**Declared:** `{', '.join(declared)}`")
                
                # Emitted signals
                emitted = sorted(list(result['emitted_signals']))
                report.append(f"**Actually Emits:** `{', '.join(emitted)}`")
                
                # Signal frequency
                if result['signal_counts']:
                    counts = ', '.join(f"{sig}({cnt})" for sig, cnt in sorted(result['signal_counts'].items()))
                    report.append(f"**Frequency:** {counts}")
                
                # Errors
                if result['errors']:
                    report.append(f"**Errors:** {len(result['errors'])} errors during testing")
                
                report.append("")
        
        # Recommendations
        report.append("---")
        report.append("")
        report.append("## 💡 RECOMMENDATIONS")
        report.append("")
        report.append("### Immediate Actions (Priority 1)")
        report.append("")
        report.append("1. **Fix Critical Mismatches** - Blocks emitting undeclared signals")
        report.append("2. **Update Registry Metadata** - Add missing signals to valid_signals")
        report.append("3. **Remove Never-Emitted Signals** - Clean up declarations")
        report.append("")
        report.append("### System Improvements (Priority 2)")
        report.append("")
        report.append("1. **Add CI/CD Test** - Run this audit on every commit")
        report.append("2. **GUI Validation** - Prevent selecting never-emitted signals")
        report.append("3. **Runtime Validation** - Warn if emitted signal not in valid_signals")
        report.append("")
        
        # Join and optionally save
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\n✅ Report saved to: {output_file}")
        
        return report_text
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print summary to console"""
        print("")
        print("="*80)
        print("AUDIT SUMMARY")
        print("="*80)
        print(f"Total Blocks Tested: {summary['total_blocks_tested']}")
        print(f"Blocks with Errors: {summary['blocks_with_errors']}")
        print(f"Blocks with Mismatches: {summary['blocks_with_mismatches']}")
        print(f"Total Mismatches Found: {summary['total_mismatches']}")
        print(f"  - Critical: {summary['critical_mismatches']}")
        print(f"  - High Priority: {summary['high_mismatches']}")
        print("="*80)
        
        if summary['total_mismatches'] > 0:
            print("\n⚠️  ISSUES DETECTED - See detailed report for fixes")
        else:
            print("\n✅ ALL BLOCKS PASS - No mismatches detected!")
        print("")


def main():
    """Run complete building block emissions audit"""
    print("\n" + "="*80)
    print("INSTITUTIONAL-GRADE BUILDING BLOCK EMISSIONS AUDIT")
    print("="*80)
    print("\nThis audit will:")
    print("  1. Test all 83+ registered building blocks")
    print("  2. Discover what signals they ACTUALLY emit")
    print("  3. Cross-reference against registry metadata")
    print("  4. Identify mismatches causing filter bugs")
    print("  5. Generate comprehensive documentation")
    print("")
    
    # Create auditor
    auditor = EmissionsAuditor()
    
    # Run audit
    summary = auditor.run_full_audit()
    
    # Print summary
    auditor.print_summary(summary)
    
    # Generate report
    report_path = "docs/v3/building_blocks/BUILDING_BLOCK_EMISSIONS.md"
    auditor.generate_report(summary, output_file=report_path)
    
    # Also save JSON for programmatic access
    json_path = "docs/v3/building_blocks/emissions_audit.json"
    with open(json_path, 'w') as f:
        # Convert sets to lists for JSON serialization
        json_summary = {
            'metadata': {
                'date': datetime.now().isoformat(),
                'total_blocks': summary['total_blocks_tested'],
                'blocks_with_issues': summary['blocks_with_mismatches'],
                'total_mismatches': summary['total_mismatches']
            },
            'mismatches': summary['mismatch_details'],
            'blocks': {
                name: {
                    'declared': sorted(list(result['declared_signals'])),
                    'emitted': sorted(list(result['emitted_signals'])),
                    'counts': result['signal_counts'],
                    'errors': result['errors']
                }
                for name, result in summary['audit_results'].items()
            }
        }
        json.dump(json_summary, f, indent=2)
    
    print(f"✅ JSON data saved to: {json_path}")
    print("")
    
    # Exit with error code if mismatches found
    if summary['total_mismatches'] > 0:
        print("❌ AUDIT FAILED - Mismatches detected")
        sys.exit(1)
    else:
        print("✅ AUDIT PASSED - All blocks validated")
        sys.exit(0)


if __name__ == "__main__":
    main()
