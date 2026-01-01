"""
Advanced Signal Validator
For Elliott Wave and Wyckoff signals

These methods have different characteristics than simple patterns:
- Elliott Wave: Wave counts, oscillator values
- Wyckoff: Phase identification (accumulation, distribution, reaccumulation)

More flexible validation than pattern validator
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from typing import Dict, Any, List


class AdvancedSignalValidator:
    """
    Validator for advanced technical analysis signals
    - Elliott Wave
    - Wyckoff Method
    """
    
    def __init__(self, signal_type: str = 'elliott_wave'):
        """
        Args:
            signal_type: 'elliott_wave' or 'wyckoff'
        """
        self.signal_type = signal_type
    
    def validate_signal(self, signal_data: Dict) -> Dict[str, Any]:
        """Validate a single signal"""
        issues = []
        warnings = []
        
        # Check basic requirements
        if not signal_data.get('signal'):
            issues.append('No signal field')
            return {
                'valid': False,
                'issues': issues,
                'warnings': warnings,
                'quality_score': 0
            }
        
        signal = signal_data['signal']
        
        # Skip ERROR and INSUFFICIENT_DATA
        if signal in ['ERROR', 'INSUFFICIENT_DATA']:
            issues.append(f'Signal is {signal}')
            return {
                'valid': False,
                'issues': issues,
                'warnings': warnings,
                'quality_score': 0
            }
        
        # Check confidence (if present)
        confidence = signal_data.get('confidence', 70)  # Default 70 if not present
        if confidence < 50:  # Flexible threshold
            warnings.append(f'Low confidence: {confidence}')
        
        # If signal has metadata, that's good
        metadata = signal_data.get('metadata', {})
        if not metadata:
            warnings.append('No metadata provided')
        
        # Valid - has signal, not an error
        return {
            'valid': True,
            'issues': issues,
            'warnings': warnings,
            'quality_score': max(0, 100 - len(issues) * 20 - len(warnings) * 5)
        }
    
    def validate_all_signals(self, signals: List[Dict]) -> Dict[str, Any]:
        """Validate all signals from a block"""
        print(f"\n{'='*80}")
        print(f"🔬 ADVANCED SIGNAL VALIDATION: {self.signal_type.upper()}")
        print(f"{'='*80}\n")
        print(f"Validating {len(signals)} signals...\n")
        
        validated = []
        total_quality = 0
        
        for i, signal_data in enumerate(signals):
            if (i + 1) % 100 == 0 or i == 0:
                print(f"  Validated {i+1}/{len(signals)} signals...")
            
            validation = self.validate_signal(signal_data)
            validated.append(validation)
            total_quality += validation['quality_score']
        
        print(f"  ✅ Validated {len(validated)}/{len(signals)} signals\n")
        
        # Calculate statistics
        valid_count = sum(1 for v in validated if v['valid'])
        avg_quality = total_quality / len(validated) if validated else 0
        
        all_issues = []
        all_warnings = []
        for v in validated:
            all_issues.extend(v.get('issues', []))
            all_warnings.extend(v.get('warnings', []))
        
        # Print report
        self.print_validation_report(
            len(validated),
            valid_count,
            avg_quality,
            all_issues,
            all_warnings
        )
        
        return {
            'total_signals': len(validated),
            'valid_signals': valid_count,
            'validity_rate': (valid_count / len(validated) * 100) if validated else 0,
            'avg_quality_score': avg_quality,
            'all_issues': all_issues,
            'all_warnings': all_warnings,
            'production_ready': valid_count >= len(validated) * 0.70 and avg_quality >= 70
        }
    
    def print_validation_report(self, total: int, valid: int, quality: float,
                               issues: List[str], warnings: List[str]):
        """Print formatted validation report"""
        print(f"{'='*80}")
        print(f"📊 VALIDATION REPORT")
        print(f"{'='*80}\n")
        
        print(f"📈 OVERALL RESULTS")
        print(f"   Total Signals: {total}")
        print(f"   Valid Signals: {valid}")
        print(f"   Validity Rate: {(valid/total*100):.1f}%")
        print(f"   Avg Quality Score: {quality:.1f}/100\n")
        
        if issues:
            from collections import Counter
            issue_counts = Counter(issues)
            print(f"❌ ISSUES FOUND ({len(issues)}):")
            for issue, count in issue_counts.most_common(5):
                print(f"   - {issue} (x{count})")
            print()
        
        if warnings:
            from collections import Counter
            warning_counts = Counter(warnings)
            print(f"⚠️  WARNINGS ({len(warnings)}):")
            for warning, count in warning_counts.most_common(5):
                print(f"   - {warning} (x{count})")
            print()
        
        validity_rate = (valid / total * 100) if total > 0 else 0
        
        if validity_rate >= 90 and quality >= 85:
            print(f"🎯 ✅ PRODUCTION READY")
            print(f"   High quality signals with excellent validity\n")
        elif validity_rate >= 70 and quality >= 70:
            print(f"🎯 ✅ PRODUCTION READY (with monitoring)")
            print(f"   Good quality signals, acceptable for production\n")
        elif validity_rate >= 50 and quality >= 60:
            print(f"🎯 ⚠️  CONDITIONAL APPROVAL")
            print(f"   Moderate quality, needs improvements\n")
        else:
            print(f"🎯 ❌ NOT READY")
            print(f"   Quality needs significant improvement\n")
        
        print(f"{'='*80}\n")


if __name__ == "__main__":
    print("Advanced Signal Validator - Ready for Elliott Wave and Wyckoff signals")
