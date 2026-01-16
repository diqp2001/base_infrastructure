#!/usr/bin/env python3
"""
Simple test script to verify the consolidated FactorService works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.application.services.data.entities.factor_service import FactorService
from src.application.services.database_service.database_service import DatabaseService

def test_factor_service():
    """Test basic FactorService functionality."""
    print("🧪 Testing FactorService...")
    
    try:
        # Initialize service
        db_service = DatabaseService('sqlite')
        factor_service = FactorService(db_service)
        print("✅ FactorService initialized successfully")
        
        # Test factor creation
        momentum_factor = factor_service.create_share_momentum_factor(
            name="Test_Momentum_20",
            period=20,
            momentum_type="price_momentum"
        )
        print(f"✅ Created momentum factor: {momentum_factor.name}")
        
        # Test technical factor creation
        technical_factor = factor_service.create_share_technical_factor(
            name="Test_SMA_50",
            indicator_type="SMA",
            period=50
        )
        print(f"✅ Created technical factor: {technical_factor.name}")
        
        # Test factor creation from config
        config = {
            'factor_type': 'share_volatility',
            'name': 'Test_Volatility_30',
            'volatility_type': 'historical',
            'period': 30
        }
        volatility_factor = factor_service.create_factor_from_config(config)
        print(f"✅ Created volatility factor from config: {volatility_factor.name}")
        
        # Test repository access through inheritance
        factor_service.create_local_repositories()
        print("✅ Local repositories created successfully")
        
        # Test convenience methods
        price_factors = factor_service.get_price_factors()
        print(f"✅ Retrieved {len(price_factors)} price factors")
        
        print("\n🎉 All tests passed! FactorService is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_factor_service()
    sys.exit(0 if success else 1)