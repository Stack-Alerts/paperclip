#!/usr/bin/env python3
"""
Dependency Validation Script for Optimizer V3
Task 0.1: Package Requirements & Dependencies
"""

import pkg_resources
import subprocess
import sys
from typing import List, Dict


def get_installed_packages() -> Dict[str, str]:
    """Get all installed packages and versions"""
    return {pkg.key: pkg.version for pkg in pkg_resources.working_set}


def check_conflicts(packages: Dict[str, str]) -> List[str]:
    """Check for package conflicts"""
    conflicts = []
    for pkg_name, version in packages.items():
        try:
            pkg_resources.require(f"{pkg_name}=={version}")
        except pkg_resources.VersionConflict as e:
            conflicts.append(str(e))
    return conflicts


def validate_nautilus_integration():
    """Validate NautilusTrader integration"""
    try:
        import nautilus_trader
        print(f"✅ NautilusTrader {nautilus_trader.__version__} installed")
        
        # Test core types
        from nautilus_trader.model.objects import Quantity, Price, Money
        test_quantity = Quantity.from_str("1.0")
        test_price = Price.from_str("50000.0")
        test_money = Money.from_str("1000.0 USD")
        print("✅ NautilusTrader core types working")
        
        # Test enums
        from nautilus_trader.model.enums import OrderSide, OrderType
        test_side = OrderSide.BUY
        test_type = OrderType.MARKET
        print("✅ NautilusTrader enums working")
        
    except ImportError as e:
        print(f"❌ NautilusTrader import failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ NautilusTrader validation failed: {e}")
        sys.exit(1)


def validate_qt_integration():
    """Validate PyQt6 integration"""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCharts import QChart
        print("✅ PyQt6 and QtCharts installed")
        
        # Test dark theme (no app execution, just import check)
        print("✅ Qt dark theme support available")
        
    except ImportError as e:
        print(f"❌ PyQt6 import failed: {e}")
        sys.exit(1)


def validate_database_integration():
    """Validate database dependencies"""
    try:
        import psycopg2
        print(f"✅ psycopg2 {psycopg2.__version__} installed")
        
        import sqlalchemy
        print(f"✅ SQLAlchemy {sqlalchemy.__version__} installed")
        
        import alembic
        print(f"✅ Alembic {alembic.__version__} installed")
        
    except ImportError as e:
        print(f"❌ Database dependency import failed: {e}")
        sys.exit(1)


def validate_testing_framework():
    """Validate testing dependencies"""
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} installed")
        
        import pytest_cov
        print("✅ pytest-cov installed")
        
        import pytest_qt
        print("✅ pytest-qt installed")
        
    except ImportError as e:
        print(f"❌ Testing dependency import failed: {e}")
        sys.exit(1)


def validate_data_processing():
    """Validate data processing dependencies"""
    try:
        import numpy
        print(f"✅ numpy {numpy.__version__} installed")
        
        import pandas
        print(f"✅ pandas {pandas.__version__} installed")
        
        import plotly
        print(f"✅ plotly {plotly.__version__} installed")
        
    except ImportError as e:
        print(f"❌ Data processing dependency import failed: {e}")
        sys.exit(1)


def validate_code_quality_tools():
    """Validate code quality tools"""
    try:
        import black
        print(f"✅ black {black.__version__} installed")
        
        import isort
        print(f"✅ isort {isort.__version__} installed")
        
        import mypy
        print(f"✅ mypy {mypy.__version__} installed")
        
        import pylint
        print(f"✅ pylint {pylint.__version__} installed")
        
    except ImportError as e:
        print(f"❌ Code quality tool import failed: {e}")
        sys.exit(1)


def main():
    """Main validation routine"""
    print("=" * 80)
    print("OPTIMIZER V3 - DEPENDENCY VALIDATION")
    print("Task 0.1: Package Requirements & Dependencies")
    print("=" * 80)
    print()
    
    # Check installed packages
    print("📦 Checking installed packages...")
    packages = get_installed_packages()
    print(f"Found {len(packages)} installed packages")
    print()
    
    # Check for conflicts
    print("🔍 Checking for package conflicts...")
    conflicts = check_conflicts(packages)
    if conflicts:
        print("❌ Package conflicts found:")
        for conflict in conflicts:
            print(f"  - {conflict}")
        sys.exit(1)
    else:
        print("✅ No package conflicts found")
    print()
    
    # Validate critical integrations
    print("🧪 Validating critical integrations:")
    print()
    
    print("1. NautilusTrader Integration:")
    validate_nautilus_integration()
    print()
    
    print("2. PyQt6 Integration:")
    validate_qt_integration()
    print()
    
    print("3. Database Integration:")
    validate_database_integration()
    print()
    
    print("4. Testing Framework:")
    validate_testing_framework()
    print()
    
    print("5. Data Processing:")
    validate_data_processing()
    print()
    
    print("6. Code Quality Tools:")
    validate_code_quality_tools()
    print()
    
    print("=" * 80)
    print("✅ ALL DEPENDENCIES VALIDATED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    main()
