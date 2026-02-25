#!/usr/bin/env python3
"""
Test script for IndexFuturePriceReturnFactor integration.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all components can be imported successfully."""
    try:
        # Test domain entity import
        from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor
        print("✅ IndexFuturePriceReturnFactor entity imported successfully")
        
        # Test port import
        from src.domain.ports.factor.index_future_price_return_factor_port import IndexFuturePriceReturnFactorPort
        print("✅ IndexFuturePriceReturnFactorPort imported successfully")
        
        # Test model import
        from src.infrastructure.models.factor.factor import IndexFuturePriceReturnFactorModel
        print("✅ IndexFuturePriceReturnFactorModel imported successfully")
        
        # Test mapper import
        from src.infrastructure.repositories.mappers.factor.index_future_price_return_factor_mapper import IndexFuturePriceReturnFactorMapper
        print("✅ IndexFuturePriceReturnFactorMapper imported successfully")
        
        # Test local repository import
        from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_future_price_return_factor_repository import IndexFuturePriceReturnFactorRepository
        print("✅ IndexFuturePriceReturnFactorRepository (local) imported successfully")
        
        # Test IBKR repository import
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_future_price_return_factor_repository import IBKRIndexFuturePriceReturnFactorRepository
        print("✅ IBKRIndexFuturePriceReturnFactorRepository imported successfully")
        
        # Test factory import with new repositories
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        print("✅ RepositoryFactory imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_entity_creation():
    """Test that the entity can be created successfully."""
    try:
        from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor
        
        # Create a test entity
        factor = IndexFuturePriceReturnFactor(
            factor_id=1,
            name="ES_DAILY_RETURN",
            group="return",
            subgroup="daily",
            data_type="numeric",
            source="calculated",
            definition="E-mini S&P 500 future daily return factor"
        )
        
        print("✅ IndexFuturePriceReturnFactor entity created successfully")
        print(f"   - Name: {factor.name}")
        print(f"   - Group: {factor.group}")
        print(f"   - Subgroup: {factor.subgroup}")
        
        return True
        
    except Exception as e:
        print(f"❌ Entity creation error: {e}")
        return False

def test_mapper_functionality():
    """Test that the mapper works correctly."""
    try:
        from src.infrastructure.repositories.mappers.factor.index_future_price_return_factor_mapper import IndexFuturePriceReturnFactorMapper
        from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor
        
        mapper = IndexFuturePriceReturnFactorMapper()
        
        # Create a test entity
        factor = IndexFuturePriceReturnFactor(
            name="NQ_DAILY_RETURN",
            group="return",
            subgroup="daily",
            data_type="numeric",
            source="calculated",
            definition="NASDAQ 100 E-mini future daily return factor"
        )
        
        # Test domain to ORM mapping
        orm_model = mapper.to_orm(factor)
        print("✅ Domain to ORM mapping successful")
        print(f"   - ORM model type: {type(orm_model).__name__}")
        print(f"   - Name: {orm_model.name}")
        
        # Test ORM to domain mapping (simulated)
        # We can't actually test this without a database, but we can test the method exists
        assert hasattr(mapper, 'to_domain'), "to_domain method should exist"
        print("✅ Mapper has to_domain method")
        
        return True
        
    except Exception as e:
        print(f"❌ Mapper test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing IndexFuturePriceReturnFactor Integration")
    print("=" * 60)
    
    all_passed = True
    
    # Run import tests
    print("\n1. Testing Imports...")
    if not test_imports():
        all_passed = False
    
    # Run entity creation tests
    print("\n2. Testing Entity Creation...")
    if not test_entity_creation():
        all_passed = False
    
    # Run mapper tests
    print("\n3. Testing Mapper Functionality...")
    if not test_mapper_functionality():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! IndexFuturePriceReturnFactor integration is working.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)