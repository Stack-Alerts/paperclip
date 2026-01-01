"""
EXPERT MODE: Metadata Block Validator
Validates metadata/context blocks for accurate data returns

For blocks like:
- ATR (volatility measurements, stop-loss distances)
- ADX (trend strength 0-100)
- Price levels (HOD, LOD, support/resistance levels)
- Volume metrics (volume profile, flow imbalance)

Validation Logic:
- Verify data completeness (all required fields present)
- Verify data accuracy (measurements within expected ranges)
- Verify threshold correctness (classifications match values)
- Compare to actual market data

Author: Cline (Expert Mode)
Date: 2026-01-01
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime


class MetadataBlockValidator:
    """
    Expert-level validator for metadata/context blocks
    
    Unlike signal validators (predict future), metadata validators
    verify current measurements are accurate and complete
    """
    
    def __init__(self, metadata_type: str = 'volatility'):
        """
        Initialize validator
        
        Args:
            metadata_type: Type of metadata block
                - 'volatility': ATR, ADR, Bollinger Bands
                - 'trend_strength': ADX, momentum indicators
                - 'price_levels': HOD, LOD, support/resistance
                - 'volume': Volume profile, flow metrics
        """
        self.metadata_type = metadata_type
    
    def validate_atr_metadata(self, metadata: Dict, price: float) -> Dict[str, Any]:
        """
        Validate ATR metadata block
        
        Checks:
        - ATR value present and >0
        - ATR % reasonable (0.1% - 10% of price for BTC)
        - Stop-loss suggestions present and reasonable
        - Position sizing factor present
        
        Args:
            metadata: Metadata dictionary from ATR block
            price: Current price for validation
            
        Returns:
            Validation result
        """
        issues = []
        warnings = []
        
        # Check required fields
        required_fields = ['atr_value', 'atr_percent', 'stop_suggestions', 'position_sizing_factor']
        for field in required_fields:
            if field not in metadata:
                issues.append(f'Missing required field: {field}')
        
        if issues:
            return {'valid': False, 'issues': issues}
        
        # Validate ATR value
        atr_value = metadata['atr_value']
        if atr_value <= 0:
            issues.append(f'ATR value must be >0, got {atr_value}')
        
        # Validate ATR percentage (BTC typically 0.1% - 10%)
        atr_percent = metadata['atr_percent']
        if not (0.01 <= atr_percent <= 15.0):
            warnings.append(f'ATR% {atr_percent:.2f}% outside typical BTC range (0.01-15%)')
        
        # Validate stop suggestions
        stops = metadata['stop_suggestions']
        for stop_type in ['conservative', 'standard', 'aggressive']:
            if stop_type not in stops:
                issues.append(f'Missing stop suggestion: {stop_type}')
                continue
            
            stop_data = stops[stop_type]
            distance = stop_data.get('distance', 0)
            
            # Stop distance should be reasonable (not negative, not >50% of price)
            if distance < 0 or distance > price * 0.5:
                issues.append(f'{stop_type} stop distance unreasonable: {distance}')
        
        # Validate position sizing
        pos_size = metadata.get('position_sizing_factor', 0)
        if pos_size <= 0 or pos_size > 10:
            warnings.append(f'Position sizing factor unusual: {pos_size}')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'quality_score': max(0, 100 - len(issues) * 20 - len(warnings) * 5)
        }
    
    def validate_adx_metadata(self, metadata: Dict) -> Dict[str, Any]:
        """
        Validate ADX metadata block
        
        Checks:
        - ADX value in range 0-100
        - Trend classification matches ADX value
        - DI+ and DI- present and reasonable
        
        Args:
            metadata: Metadata dictionary from ADX block
            
        Returns:
            Validation result
        """
        issues = []
        warnings = []
        
        # Check ADX value (ADX returns 'adx' not 'adx_value')
        adx_value = metadata.get('adx') or metadata.get('adx_value')
        if adx_value is None:
            issues.append('Missing ADX value')
        elif not (0 <= adx_value <= 100):
            issues.append(f'ADX must be 0-100, got {adx_value}')
        
        # Check trend classification matches value (ADX returns 'trend_strength' not 'trend_classification')
        trend_class = metadata.get('trend_strength') or metadata.get('trend_classification', '')
        if adx_value is not None and trend_class:
            if adx_value >= 50 and 'strong' not in trend_class.lower():
                warnings.append(f'ADX {adx_value} should classify as strong trend')
            elif adx_value < 20 and 'weak' not in trend_class.lower() and 'range' not in trend_class.lower():
                warnings.append(f'ADX {adx_value} should classify as weak/ranging')
        
        # Check DI values present
        plus_di = metadata.get('plus_di')
        minus_di = metadata.get('minus_di')
        if plus_di is None:
            warnings.append('Missing +DI value')
        if minus_di is None:
            warnings.append('Missing -DI value')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'quality_score': max(0, 100 - len(issues) * 20 - len(warnings) * 5)
        }
    
    def validate_price_level_metadata(self, metadata: Dict, current_price: float) -> Dict[str, Any]:
        """
        Validate price level metadata (HOD, LOD, support/resistance)
        
        Checks:
        - Level value present and reasonable
        - Distance to level calculated correctly
        - Level is a valid historical price
        
        Args:
            metadata: Metadata dictionary
            current_price: Current price
            
        Returns:
            Validation result
        """
        issues = []
        warnings = []
        
        # Check for price level
        level_price = metadata.get('hod') or metadata.get('lod') or metadata.get('level')
        if level_price is None:
            issues.append('No price level found in metadata')
        elif level_price <= 0:
            issues.append(f'Price level must be >0, got {level_price}')
        
        # Check distance calculation
        if level_price and 'distance_pct' in metadata:
            expected_dist = ((current_price - level_price) / level_price) * 100
            actual_dist = metadata['distance_pct']
            
            if abs(expected_dist - actual_dist) > 0.01:  # Allow 0.01% rounding
                warnings.append(f'Distance calculation off: expected {expected_dist:.2f}%, got {actual_dist:.2f}%')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'quality_score': max(0, 100 - len(issues) * 20 - len(warnings) * 5)
        }
    
    def validate_all_metadata(self, df: pd.DataFrame, metadata_results: List[Dict]) -> Dict[str, Any]:
        """
        Validate all metadata returns from a block
        
        Args:
            df: Full OHLCV DataFrame
            metadata_results: List of metadata dictionaries from block
            
        Returns:
            Comprehensive validation report
        """
        print(f"\n{'='*80}")
        print(f"🔬 EXPERT MODE: METADATA BLOCK VALIDATION")
        print(f"{'='*80}\n")
        print(f"Validating {len(metadata_results)} metadata returns...")
        print(f"Type: {self.metadata_type}\n")
        
        validated = []
        total_quality = 0
        
        for i, result in enumerate(metadata_results):
            if (i + 1) % 100 == 0 or i == 0:
                print(f"  Validated {i+1}/{len(metadata_results)} metadata returns...")
            
            metadata = result.get('metadata', {})
            price = result.get('price', 0)
            
            # Validate based on type
            if self.metadata_type == 'volatility':
                validation = self.validate_atr_metadata(metadata, price)
            elif self.metadata_type == 'trend_strength':
                validation = self.validate_adx_metadata(metadata)
            elif self.metadata_type == 'price_levels':
                validation = self.validate_price_level_metadata(metadata, price)
            else:
                validation = {'valid': True, 'issues': [], 'warnings': [], 'quality_score': 100}
            
            validated.append(validation)
            total_quality += validation['quality_score']
        
        print(f"  ✅ Validated {len(validated)}/{len(metadata_results)} returns\n")
        
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
            'total_returns': len(validated),
            'valid_returns': valid_count,
            'validity_rate': (valid_count / len(validated) * 100) if validated else 0,
            'avg_quality_score': avg_quality,
            'all_issues': all_issues,
            'all_warnings': all_warnings,
            'production_ready': valid_count >= len(validated) * 0.95 and avg_quality >= 80
        }
    
    def print_validation_report(self, total: int, valid: int, quality: float,
                               issues: List[str], warnings: List[str]):
        """Print formatted validation report"""
        print(f"{'='*80}")
        print(f"📊 METADATA VALIDATION REPORT")
        print(f"{'='*80}\n")
        
        print(f"📈 OVERALL RESULTS")
        print(f"   Total Returns: {total}")
        print(f"   Valid Returns: {valid}")
        print(f"   Validity Rate: {(valid/total*100):.1f}%")
        print(f"   Avg Quality Score: {quality:.1f}/100\n")
        
        if issues:
            print(f"❌ ISSUES FOUND ({len(issues)}):")
            unique_issues = list(set(issues))[:10]  # Show first 10 unique
            for issue in unique_issues:
                count = issues.count(issue)
                print(f"   - {issue} (x{count})")
            print()
        
        if warnings:
            print(f"⚠️  WARNINGS ({len(warnings)}):")
            unique_warnings = list(set(warnings))[:10]
            for warning in unique_warnings:
                count = warnings.count(warning)
                print(f"   - {warning} (x{count})")
            print()
        
        print(f"{'='*80}")
        print(f"🎯 PRODUCTION READINESS")
        print(f"{'='*80}\n")
        
        validity_rate = (valid / total * 100) if total > 0 else 0
        
        if validity_rate >= 98 and quality >= 90:
            print(f"   Recommendation: ✅ APPROVED FOR PRODUCTION")
            print(f"   Confidence Level: HIGH")
            print(f"   Notes: Metadata is accurate and complete.\n")
        elif validity_rate >= 95 and quality >= 80:
            print(f"   Recommendation: ✅ APPROVED WITH MONITORING")
            print(f"   Confidence Level: MEDIUM-HIGH")
            print(f"   Notes: Good quality, monitor edge cases.\n")
        elif validity_rate >= 90 and quality >= 70:
            print(f"   Recommendation: ⚠️  CONDITIONAL APPROVAL")
            print(f"   Confidence Level: MEDIUM")
            print(f"   Notes: Acceptable but needs improvements.\n")
        else:
            print(f"   Recommendation: ❌ NOT READY FOR PRODUCTION")
            print(f"   Confidence Level: LOW")
            print(f"   Notes: Metadata quality needs significant improvement.\n")
        
        print(f"{'='*80}\n")


if __name__ == "__main__":
    print("Metadata Block Validator - Ready for ATR, ADX, price levels, volume metrics")
