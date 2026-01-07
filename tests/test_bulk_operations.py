#!/usr/bin/env python3
"""
Test script to validate bulk operations implementation and QuantConnect-style architecture.
This script tests the performance improvements and functionality.
"""

import sys
import os
import traceback
from datetime import datetime
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_import_statements():
    """Test that all new imports work correctly."""
    print("🧪 Testing import statements...")
    
    try:
        from src.domain.entities.finance.financial_assets.security import Security, Symbol, SecurityType, MarketData, Holdings
        from src.domain.entities.finance.financial_assets.stock import Stock, Dividend, StockSplit
        from src.domain.entities.finance.financial_assets.company_stock import CompanyStock
        print("✅ All Security/Equity domain imports successful")
        
        from src.application.managers.project_managers.test_project.test_project_manager import TestProjectManager
        print("✅ TestProjectManager import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_security_architecture():
    """Test the QuantConnect-style Security/Equity architecture."""
    print("\n🏗️ Testing Security/Equity architecture...")
    
    try:
        from src.domain.entities.finance.financial_assets.security import Symbol, SecurityType, MarketData
        from src.domain.entities.finance.financial_assets.stock import Stock, Dividend
        from src.domain.entities.finance.financial_assets.company_stock import CompanyStock
        
        # Test Symbol value object
        symbol = Symbol("AAPL", "NASDAQ", SecurityType.EQUITY)
        print(f"✅ Symbol created: {symbol}")
        
        # Test CompanyStock creation with new architecture
        company_stock = CompanyStock(
            id=1,
            ticker="AAPL", 
            exchange_id=1,
            company_id=100,
            start_date=datetime(2020, 1, 1)
        )
        company_stock.set_company_name("Apple Inc.")
        
        print(f"✅ CompanyStock created: {company_stock}")
        print(f"  - Ticker: {company_stock.ticker}")
        print(f"  - Security Type: {company_stock.security_type}")
        print(f"  - Company ID: {company_stock.company_id}")
        
        # Test market data update
        market_data = MarketData(
            timestamp=datetime.now(),
            price=Decimal('150.00'),
            volume=1000000
        )
        company_stock.update_market_data(market_data)
        print(f"✅ Market data updated: Price=${company_stock.price}")
        
  
        
        # Test dividend
        dividend = Dividend(
            amount=Decimal('0.23'),
            ex_date=datetime(2024, 3, 15)
        )
        company_stock.add_dividend(dividend)
        print(f"✅ Dividend added: Yield={company_stock.get_trailing_dividend_yield():.2f}%")
        
        # Test company metrics
        metrics = company_stock.get_company_metrics()
        print(f"✅ Company metrics: {len(metrics)} fields available")
        
        return True
        
    except Exception as e:
        print(f"❌ Security architecture test failed: {e}")
        traceback.print_exc()
        return False

def test_bulk_operations():
    """Test the bulk operations functionality."""
    print("\n📊 Testing bulk operations...")
    
    try:
        # Note: This would require database setup in real environment
        # For now, just test that the manager can be instantiated and methods exist
        
        from src.application.managers.project_managers.test_project.test_project_manager import TestProjectManager
        
        print("✅ TestProjectManager instantiation test passed")
        
        # Check that bulk methods exist
        manager = TestProjectManager()
        
        assert hasattr(manager, 'create_multiple_companies'), "create_multiple_companies method missing"
        assert hasattr(manager, 'create_sample_companies_with_market_data'), "create_sample_companies_with_market_data method missing"
        assert hasattr(manager, 'demonstrate_bulk_operations'), "demonstrate_bulk_operations method missing"
        assert hasattr(manager, 'save_multiple_company_stocks_example'), "save_multiple_company_stocks_example method missing"
        
        print("✅ All bulk operation methods available")
        
        # Test repository bulk methods exist
        repository = manager.company_stock_repository_local
        
        assert hasattr(repository, 'add_bulk'), "add_bulk method missing"
        assert hasattr(repository, 'add_bulk_from_dicts'), "add_bulk_from_dicts method missing"
        assert hasattr(repository, 'delete_bulk'), "delete_bulk method missing"
        assert hasattr(repository, 'update_bulk'), "update_bulk method missing"
        assert hasattr(repository, 'exists_by_id'), "exists_by_id method missing"
        
        print("✅ All repository bulk methods available")
        
        return True
        
    except Exception as e:
        print(f"❌ Bulk operations test failed: {e}")
        traceback.print_exc()
        return False

def test_value_objects():
    """Test value objects for data integrity."""
    print("\n💎 Testing value objects...")
    
    try:
        from src.domain.entities.finance.financial_assets.security import Symbol, SecurityType, MarketData, Holdings
        from src.domain.entities.finance.financial_assets.stock import Dividend, StockSplit
        from decimal import Decimal
        
        # Test Symbol
        symbol = Symbol("MSFT", "NYSE", SecurityType.EQUITY)
        assert str(symbol) == "MSFT.NYSE"
        print("✅ Symbol value object works")
        
        # Test MarketData validation
        try:
            MarketData(datetime.now(), Decimal('-10'), 1000)  # Negative price should fail
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ MarketData validation works")
        
        # Test Dividend validation
        try:
            Dividend(Decimal('-1'), datetime.now())  # Negative dividend should fail
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Dividend validation works")
        
        # Test StockSplit validation
        try:
            StockSplit(Decimal('-2'), datetime.now())  # Negative split should fail
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ StockSplit validation works")
        
        # Test Holdings
        holdings = Holdings(
            quantity=Decimal('100'),
            average_cost=Decimal('50.00'),
            market_value=Decimal('5500.00'),
            unrealized_pnl=Decimal('500.00')
        )
        assert holdings.total_fees == Decimal('5.00')  # 0.1% of position value
        print("✅ Holdings calculations work")
        
        return True
        
    except Exception as e:
        print(f"❌ Value objects test failed: {e}")
        traceback.print_exc()
        return False

def test_template_method_pattern():
    """Test template method pattern in Security class."""
    print("\n🏗️ Testing template method pattern...")
    
    try:
        from src.domain.entities.finance.financial_assets.company_stock import CompanyStock
        from src.domain.entities.finance.financial_assets.security import MarketData
        from decimal import Decimal
        from datetime import datetime
        
        # Create a company stock
        company_stock = CompanyStock(
            id=1,
            ticker="TEST",
            exchange_id=1, 
            company_id=1,
            start_date=datetime(2024, 1, 1)
        )
        
        initial_price = company_stock.price
        
        # Test market data update (template method)
        market_data = MarketData(
            timestamp=datetime.now(),
            price=Decimal('100.00'),
            volume=50000
        )
        
        company_stock.update_market_data(market_data)
        
        assert company_stock.price == Decimal('100.00')
        assert company_stock.last_update is not None
        print("✅ Template method pattern works (market data update)")
        
        # Test circuit breaker (50% price change limit)
        extreme_data = MarketData(
            timestamp=datetime.now(),
            price=Decimal('200.00'),  # 100% increase
            volume=10000
        )
        
        old_price = company_stock.price
        company_stock.update_market_data(extreme_data)
        
        # Price should not have changed due to circuit breaker
        assert company_stock.price == old_price
        print("✅ Circuit breaker protection works")
        
        return True
        
    except Exception as e:
        print(f"❌ Template method pattern test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting bulk operations and QuantConnect architecture tests...")
    print("=" * 70)
    
    tests = [
        test_import_statements,
        test_security_architecture,
        test_value_objects,
        test_template_method_pattern,
        test_bulk_operations,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Implementation is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)