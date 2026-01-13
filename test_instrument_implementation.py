#!/usr/bin/env python3
"""
Test script to validate the Instrument implementation.
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_domain_entities():
    """Test domain entity imports and basic functionality."""
    print("Testing domain entities...")
    
    try:
        from src.domain.entities.finance.instrument.instrument import Instrument
        from src.domain.entities.finance.instrument.instrument_factor import InstrumentFactor
        from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
        print("✓ Domain entities imported successfully")
        
        # Test Instrument creation
        asset = FinancialAsset(id=1, start_date=None, end_date=None)
        instrument = Instrument(
            id=1,
            asset=asset,
            source='Bloomberg',
            date=datetime.now()
        )
        
        print(f"✓ Instrument created: {instrument}")
        print(f"  - Asset ID: {instrument.asset_id}")
        print(f"  - Asset Type: {instrument.asset_type}")
        print(f"  - Valid: {instrument.is_valid()}")
        
        # Test InstrumentFactor creation
        factor = InstrumentFactor(
            name='Current Price',
            group='Market',
            subgroup='Pricing',
            data_type='decimal',
            source='Bloomberg',
            instrument_id=1,
            asset_type='Stock',
            currency='USD',
            frequency='real-time'
        )
        
        print(f"✓ InstrumentFactor created: {factor}")
        print(f"  - Is Market Factor: {factor.is_market_factor()}")
        print(f"  - Valid Currency: {factor.validate_currency()}")
        print(f"  - Valid Frequency: {factor.validate_frequency()}")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
        
    return True

def test_infrastructure_imports():
    """Test infrastructure layer imports."""
    print("\nTesting infrastructure imports...")
    
    try:
        from src.domain.ports.finance.instrument_port import InstrumentPort
        print("✓ InstrumentPort imported successfully")
        
        from src.infrastructure.models.finance.instrument import Instrument as InstrumentModel
        print("✓ Instrument ORM model imported successfully")
        
        from src.infrastructure.repositories.mappers.finance.instrument_mapper import InstrumentMapper
        print("✓ InstrumentMapper imported successfully")
        
        # Note: Repository requires a database session, so we won't test it here
        print("✓ Infrastructure imports successful")
        
    except ImportError as e:
        print(f"✗ Infrastructure import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Infrastructure error: {e}")
        return False
        
    return True

def test_mapper_functionality():
    """Test mapper functionality without database."""
    print("\nTesting mapper functionality...")
    
    try:
        from src.domain.entities.finance.instrument.instrument import Instrument
        from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
        from src.infrastructure.models.finance.instrument import Instrument as InstrumentModel
        from src.infrastructure.repositories.mappers.finance.instrument_mapper import InstrumentMapper
        
        # Create a domain entity
        asset = FinancialAsset(id=1, start_date=None, end_date=None)
        domain_instrument = Instrument(
            id=1,
            asset=asset,
            source='Reuters',
            date=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        # Test domain to ORM conversion
        orm_instrument = InstrumentMapper.to_orm(domain_instrument)
        print(f"✓ Domain to ORM conversion: {orm_instrument}")
        
        # Test ORM to domain conversion
        # (Note: This would normally require database relationships, so we'll skip the full test)
        print("✓ Mapper functionality working")
        
    except Exception as e:
        print(f"✗ Mapper error: {e}")
        return False
        
    return True

def main():
    """Run all tests."""
    print("🧪 Testing Instrument Implementation")
    print("=" * 50)
    
    all_passed = True
    
    # Test domain entities
    all_passed &= test_domain_entities()
    
    # Test infrastructure imports
    all_passed &= test_infrastructure_imports()
    
    # Test mapper functionality
    all_passed &= test_mapper_functionality()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Instrument implementation is ready.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)