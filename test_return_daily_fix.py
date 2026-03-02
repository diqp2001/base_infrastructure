#!/usr/bin/env python3
"""
Test script to verify the IndexPriceReturnFactor calculation fix.

This script tests that the return_daily factor can now properly resolve
its dependencies from the factor library configuration.
"""

from datetime import datetime, timedelta
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository

def test_config_dependency_resolution():
    """Test that config dependencies are properly resolved."""
    
    # Create a return_daily factor instance
    return_daily_factor = IndexPriceReturnFactor(
        factor_id=14,
        name='return_daily',
        group='return',
        subgroup='daily',
        data_type='numeric',
        source='config',
        definition='Factor return_daily from config'
    )
    
    # Create a mock IBKRFactorValueRepository instance
    repo = IBKRFactorValueRepository(
        ibkr_client=None,
        factory=None
    )
    
    # Test the config-based dependency resolution
    print("Testing config-based dependency resolution...")
    dependencies = repo._get_factor_dependencies_from_config(return_daily_factor)
    
    if dependencies:
        print(f"✅ Found {len(dependencies)} dependencies from config:")
        for dep in dependencies:
            print(f"  - Parameter: {dep['parameter_name']}, Factor: {dep['factor_name']}, Lag: {dep['lag']}")
    else:
        print("❌ No dependencies found from config")
        return False
    
    # Test the calculation with proper parameters
    print("\nTesting factor calculation...")
    try:
        # Test with sample values
        start_price = 4000.0
        end_price = 4050.0
        
        result = return_daily_factor.calculate(start_price=start_price, end_price=end_price)
        expected = (end_price / start_price) - 1  # Default geometric return
        
        print(f"✅ Calculation successful:")
        print(f"  Start price: {start_price}")
        print(f"  End price: {end_price}")
        print(f"  Result: {result}")
        print(f"  Expected: {expected}")
        
        if abs(result - expected) < 0.0001:
            print("✅ Calculation result matches expected value")
            return True
        else:
            print("❌ Calculation result doesn't match expected value")
            return False
            
    except Exception as e:
        print(f"❌ Calculation failed: {e}")
        return False

def test_mock_dependency_handling():
    """Test dependency handling with mock bar data."""
    
    # Create mock bar data
    mock_bar_data = {
        'date': '20260302',
        'open': 4000.0,
        'high': 4100.0,
        'low': 3950.0,
        'close': 4050.0,
        'volume': 1000000,
        'barCount': 500
    }
    
    return_daily_factor = IndexPriceReturnFactor(
        factor_id=14,
        name='return_daily',
        group='return',
        subgroup='daily',
        data_type='numeric',
        source='config',
        definition='Factor return_daily from config'
    )
    
    repo = IBKRFactorValueRepository(
        ibkr_client=None,
        factory=None
    )
    
    print("\nTesting mock dependency handling...")
    
    # Test extracting values by factor name
    close_value = repo._extract_value_by_factor_name(mock_bar_data, 'close')
    open_value = repo._extract_value_by_factor_name(mock_bar_data, 'open')
    
    print(f"Extracted close value: {close_value}")
    print(f"Extracted open value: {open_value}")
    
    if close_value == 4050.0 and open_value == 4000.0:
        print("✅ Value extraction working correctly")
        
        # Test calculation with extracted values
        result = return_daily_factor.calculate(start_price=open_value, end_price=close_value)
        print(f"✅ Daily return calculation: {result}")
        return True
    else:
        print("❌ Value extraction failed")
        return False

if __name__ == "__main__":
    print("🧪 Testing IndexPriceReturnFactor dependency resolution fix...")
    print("=" * 60)
    
    test1_result = test_config_dependency_resolution()
    test2_result = test_mock_dependency_handling()
    
    print("\n" + "=" * 60)
    if test1_result and test2_result:
        print("✅ All tests passed! The fix should work correctly.")
    else:
        print("❌ Some tests failed. The fix needs more work.")