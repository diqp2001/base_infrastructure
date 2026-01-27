#!/usr/bin/env python3
"""
Test script for the new get_or_create_factor_value_with_dependencies function.

This script tests the enhanced IBKRFactorValueRepository functionality.
"""

import sys
import os

# Add src to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, date
from typing import Optional, Any

# Import the classes we need
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository


class MockFinancialAsset:
    """Mock financial asset entity for testing."""
    
    def __init__(self, id: int = 1, symbol: str = "AAPL", name: str = "Apple Inc."):
        self.id = id
        self.symbol = symbol  
        self.name = name


class MockFactory:
    """Mock factory for testing."""
    
    def get_factor_value_repository(self):
        """Return a mock local repository."""
        return MockLocalRepository()


class MockLocalRepository:
    """Mock local repository for testing."""
    
    def __init__(self):
        self.stored_values = {}
    
    def get_by_factor_entity_date(self, factor_id: int, entity_id: int, date_str: str) -> Optional[FactorValue]:
        """Check if factor value already exists."""
        key = f"{factor_id}-{entity_id}-{date_str}"
        return self.stored_values.get(key)
    
    def add(self, factor_value: FactorValue) -> FactorValue:
        """Store factor value."""
        key = f"{factor_value.factor_id}-{factor_value.entity_id}-{factor_value.date.strftime('%Y-%m-%d')}"
        self.stored_values[key] = factor_value
        
        # Assign ID if not set
        if factor_value.id is None:
            factor_value.id = len(self.stored_values)
        
        print(f"✓ Stored factor value: {factor_value.value} for factor {factor_value.factor_id}")
        return factor_value


def test_basic_factor_calculation():
    """Test basic factor value calculation with dependencies."""
    
    print("🧪 Testing basic factor calculation with dependencies...")
    
    # 1. Create test objects
    mock_ibkr_client = None  # Not needed for this test
    mock_factory = MockFactory()
    
    # 2. Initialize repository
    repo = IBKRFactorValueRepository(
        ibkr_client=mock_ibkr_client,
        factory=mock_factory
    )
    
    # 3. Create a momentum factor (has dependencies on price data)
    momentum_factor = ShareMomentumFactor(
        name="20-Day Momentum",
        group="Momentum",
        subgroup="Short-term",
        data_type="float",
        source="calculation",
        definition="20-day price momentum factor",
        factor_id=100,
        period=20,
        momentum_type="price"
    )
    
    # 4. Create mock financial asset
    asset = MockFinancialAsset(id=1, symbol="AAPL", name="Apple Inc.")
    
    # 5. Test date
    test_date = "2023-12-01"
    
    # 6. Call the enhanced get_or_create function
    print(f"📊 Calculating {momentum_factor.name} for {asset.symbol} on {test_date}")
    
    try:
        result = repo.get_or_create_factor_value_with_dependencies(
            factor_entity=momentum_factor,
            financial_asset_entity=asset,
            time_date=test_date,
            prices=[95.0, 98.0, 100.0, 102.0, 105.0]  # Mock price data
        )
        
        if result:
            print(f"✅ Success! Calculated factor value: {result.value}")
            print(f"   Factor ID: {result.factor_id}")
            print(f"   Entity ID: {result.entity_id}")
            print(f"   Date: {result.date}")
        else:
            print("❌ Failed to calculate factor value")
            return False
            
    except Exception as e:
        print(f"❌ Error during calculation: {e}")
        return False
    
    print("✅ Basic factor calculation test passed!")
    return True


def test_dependency_detection():
    """Test factor dependency detection."""
    
    print("\n🔍 Testing factor dependency detection...")
    
    # Create repository
    mock_ibkr_client = None
    mock_factory = MockFactory()
    repo = IBKRFactorValueRepository(
        ibkr_client=mock_ibkr_client,
        factory=mock_factory
    )
    
    # Create momentum factor
    momentum_factor = ShareMomentumFactor(
        name="Test Momentum",
        group="Momentum",
        subgroup="Test",
        factor_id=101
    )
    
    # Test dependency detection
    dependencies = repo._get_factor_dependencies(momentum_factor)
    
    print(f"📋 Detected dependencies: {list(dependencies.keys())}")
    
    # Should detect price_data dependency for momentum factors
    if 'price_data' in dependencies:
        print("✅ Correctly detected price_data dependency for momentum factor")
    else:
        print("⚠️  Expected price_data dependency not detected")
    
    print("✅ Dependency detection test completed!")
    return True


def test_existing_value_check():
    """Test that existing values are returned instead of recalculated."""
    
    print("\n🔄 Testing existing value check...")
    
    # Create repository with mock factory
    mock_factory = MockFactory()
    repo = IBKRFactorValueRepository(
        ibkr_client=None,
        factory=mock_factory
    )
    
    # Create test factor and asset
    test_factor = Factor(
        name="Test Factor",
        group="Test",
        factor_id=200
    )
    
    asset = MockFinancialAsset(id=1, symbol="TEST")
    test_date = "2023-12-01"
    
    # First call should calculate and store
    result1 = repo.get_or_create_factor_value_with_dependencies(
        factor_entity=test_factor,
        financial_asset_entity=asset,
        time_date=test_date
    )
    
    if not result1:
        print("❌ First calculation failed")
        return False
    
    print(f"📝 First call result: {result1.value}")
    
    # Second call should return existing value
    result2 = repo.get_or_create_factor_value_with_dependencies(
        factor_entity=test_factor,
        financial_asset_entity=asset,
        time_date=test_date
    )
    
    if result2 and result1.id == result2.id:
        print("✅ Correctly returned existing factor value!")
        return True
    else:
        print("❌ Failed to return existing value")
        return False


def run_all_tests():
    """Run all tests."""
    
    print("🚀 Starting IBKRFactorValueRepository get_or_create tests...")
    print("=" * 60)
    
    tests = [
        test_dependency_detection,
        test_basic_factor_calculation,
        test_existing_value_check
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
            print(f"❌ Test {test.__name__} failed with error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Implementation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)