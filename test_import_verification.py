#!/usr/bin/env python3
"""
Test script to verify all domain entities and infrastructure models import correctly
and that no mock objects are being imported.
"""

def test_domain_entities_import():
    """Test that all domain entities can be imported without error."""
    try:
        # Test basic domain imports
        from src.domain.entities.finance.back_testing import (
            Portfolio, PortfolioHoldings, PortfolioStatistics, 
            SecurityHoldings, Security, MarketData, Symbol, SecurityType
        )
        print("✓ Domain entities imported successfully")
        
        # Test infrastructure model imports
        from src.infrastructure.models.finance import (
            Portfolio as PortfolioModel,
            PortfolioHoldingsModel,
            SecurityHoldingModel, 
            PortfolioStatisticsModel,
            MarketDataModel
        )
        print("✓ Infrastructure models imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_domain_entity_creation():
    """Test creating domain entities."""
    try:
        from src.domain.entities.finance.back_testing import Portfolio, SecurityType, Symbol
        from decimal import Decimal
        
        # Create a simple portfolio
        portfolio = Portfolio(
            name="Test Portfolio", 
            initial_cash=Decimal('100000')
        )
        
        print(f"✓ Portfolio created: {portfolio.name} with ${portfolio.initial_cash}")
        print(f"✓ Current cash balance: ${portfolio.cash_balance}")
        print(f"✓ Portfolio statistics: {portfolio.statistics}")
        
        # Create a symbol
        symbol = Symbol(
            ticker="AAPL",
            exchange="NASDAQ", 
            security_type=SecurityType.EQUITY
        )
        print(f"✓ Symbol created: {symbol}")
        
        return True
    except Exception as e:
        print(f"✗ Entity creation failed: {e}")
        return False

def test_no_mock_imports():
    """Verify that mock objects are not imported anywhere."""
    try:
        # These should fail if mock objects still exist
        from src.domain.entities.back_testing import MockPortfolio
        print("✗ MockPortfolio still exists!")
        return False
    except ImportError:
        print("✓ Mock objects properly removed")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Domain Entity and Infrastructure Model Integration")
    print("=" * 60)
    
    tests = [
        ("Domain Entities Import", test_domain_entities_import),
        ("Domain Entity Creation", test_domain_entity_creation),
        ("Mock Objects Removed", test_no_mock_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactoring was successful.")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    main()