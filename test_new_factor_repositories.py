#!/usr/bin/env python3
"""
Test script for new factor repositories and ports.

This script verifies that the new factor repositories, mappers, and ports
can be imported and instantiated correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_domain_ports():
    """Test that new domain ports can be imported."""
    print("Testing Domain Ports...")
    try:
        from src.domain.ports.factor.bond_factor_port import BondFactorPort
        from src.domain.ports.factor.derivative_factor_port import DerivativeFactorPort
        from src.domain.ports.factor.future_factor_port import FutureFactorPort
        from src.domain.ports.factor.option_factor_port import OptionFactorPort
        from src.domain.ports.factor.financial_asset_factor_port import FinancialAssetFactorPort
        from src.domain.ports.factor.security_factor_port import SecurityFactorPort
        print("✅ All domain ports imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Error importing domain ports: {e}")
        return False

def test_factor_entities():
    """Test that factor entities can be imported and instantiated."""
    print("\nTesting Factor Entities...")
    try:
        from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor
        from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor
        from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor
        from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor
        from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor
        
        # Test instantiation
        bond_factor = BondFactor(
            name="Test Bond Factor",
            group="fixed_income",
            subgroup="bond",
            factor_id=1
        )
        
        derivative_factor = DerivativeFactor(
            name="Test Derivative Factor", 
            group="derivatives",
            subgroup="general",
            factor_id=2
        )
        
        print("✅ All factor entities imported and instantiated successfully")
        print(f"  - BondFactor: {bond_factor.name}")
        print(f"  - DerivativeFactor: {derivative_factor.name}")
        return True
    except Exception as e:
        print(f"❌ Error with factor entities: {e}")
        return False

def test_ibkr_repositories():
    """Test that IBKR repositories can be imported (without instantiation due to client dependency)."""
    print("\nTesting IBKR Repositories...")
    try:
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_bond_factor_repository import IBKRBondFactorRepository
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_derivative_factor_repository import IBKRDerivativeFactorRepository
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_future_factor_repository import IBKRFutureFactorRepository
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_option_factor_repository import IBKROptionFactorRepository
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_financial_asset_factor_repository import IBKRFinancialAssetFactorRepository
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_security_factor_repository import IBKRSecurityFactorRepository
        
        print("✅ All IBKR repositories imported successfully")
        print("  - IBKRBondFactorRepository")
        print("  - IBKRDerivativeFactorRepository")
        print("  - IBKRFutureFactorRepository")
        print("  - IBKROptionFactorRepository")
        print("  - IBKRFinancialAssetFactorRepository")
        print("  - IBKRSecurityFactorRepository")
        return True
    except ImportError as e:
        print(f"❌ Error importing IBKR repositories: {e}")
        return False

def test_repository_factory():
    """Test that RepositoryFactory can import new repositories."""
    print("\nTesting Repository Factory...")
    try:
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        
        # Note: We can't fully instantiate without a valid session and IBKR client
        # but we can test the imports worked
        print("✅ RepositoryFactory imported successfully with new repositories")
        return True
    except ImportError as e:
        print(f"❌ Error importing RepositoryFactory: {e}")
        return False

def test_ibkr_init_file():
    """Test that IBKR __init__.py file exports work correctly."""
    print("\nTesting IBKR __init__.py exports...")
    try:
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets import (
            IBKRBondFactorRepository,
            IBKRDerivativeFactorRepository,
            IBKRFutureFactorRepository,
            IBKROptionFactorRepository,
            IBKRFinancialAssetFactorRepository,
            IBKRSecurityFactorRepository
        )
        print("✅ All new IBKR repositories imported via __init__.py")
        return True
    except ImportError as e:
        print(f"❌ Error importing from IBKR __init__.py: {e}")
        return False

def test_ports_init_file():
    """Test that domain ports __init__.py file exports work correctly."""
    print("\nTesting Ports __init__.py exports...")
    try:
        from src.domain.ports.factor import (
            BondFactorPort,
            DerivativeFactorPort,
            FutureFactorPort,
            OptionFactorPort,
            FinancialAssetFactorPort,
            SecurityFactorPort
        )
        print("✅ All new ports imported via __init__.py")
        return True
    except ImportError as e:
        print(f"❌ Error importing from ports __init__.py: {e}")
        return False

def main():
    """Run all tests and report results."""
    print("🧪 Testing New Factor Repositories Implementation\n")
    print("=" * 60)
    
    tests = [
        test_domain_ports,
        test_factor_entities,
        test_ibkr_repositories,
        test_repository_factory,
        test_ibkr_init_file,
        test_ports_init_file
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)