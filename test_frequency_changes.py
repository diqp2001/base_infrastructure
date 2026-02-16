#!/usr/bin/env python3
"""
Test script to verify that the frequency parameter changes work correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from src.domain.entities.factor.factor import Factor
    from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor
    from src.infrastructure.models.factor.factor import FactorModel
    from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_frequency_validation():
    """Test that frequency validation works in Factor entity"""
    print("\n🔍 Testing frequency validation...")
    
    # Test valid frequency
    try:
        factor = ShareFactor(
            name="Test Factor",
            group="test",
            frequency="1d"  # Valid frequency
        )
        print(f"✅ Valid frequency accepted: {factor.frequency}")
    except ValueError as e:
        print(f"❌ Valid frequency rejected: {e}")
        return False
    
    # Test invalid frequency
    try:
        factor = ShareFactor(
            name="Test Factor",
            group="test", 
            frequency="invalid"  # Invalid frequency
        )
        print("❌ Invalid frequency was accepted (should have been rejected)")
        return False
    except ValueError as e:
        print(f"✅ Invalid frequency properly rejected: {e}")
    
    return True

def test_model_attributes():
    """Test that FactorModel has frequency attribute"""
    print("\n🏗️ Testing FactorModel attributes...")
    
    # Check if frequency column exists in model
    model_attrs = dir(FactorModel)
    if 'frequency' in model_attrs:
        print("✅ FactorModel has frequency attribute")
        return True
    else:
        print("❌ FactorModel missing frequency attribute")
        return False

def test_mapper_conversion():
    """Test that mapper handles frequency field"""
    print("\n🔄 Testing mapper conversion...")
    
    try:
        # Create a ShareFactor with frequency
        factor = ShareFactor(
            name="Test Mapper Factor",
            group="test",
            subgroup="mapper",
            frequency="5m",
            data_type="numeric",
            source="test",
            definition="Test factor for mapper"
        )
        
        # Convert to ORM
        orm_model = FactorMapper.to_orm(factor)
        print(f"✅ Domain → ORM conversion: frequency = {orm_model.frequency}")
        
        # Convert back to domain
        domain_entity = FactorMapper.to_domain(orm_model)
        print(f"✅ ORM → Domain conversion: frequency = {domain_entity.frequency}")
        
        # Check round-trip integrity
        if factor.frequency == domain_entity.frequency:
            print("✅ Round-trip conversion preserves frequency")
            return True
        else:
            print("❌ Round-trip conversion lost frequency")
            return False
            
    except Exception as e:
        print(f"❌ Mapper conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Testing frequency parameter implementation...\n")
    
    all_passed = True
    
    all_passed &= test_frequency_validation()
    all_passed &= test_model_attributes()  
    all_passed &= test_mapper_conversion()
    
    if all_passed:
        print("\n✅ All tests passed! Frequency parameter implementation is working.")
        return 0
    else:
        print("\n❌ Some tests failed. Check output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())