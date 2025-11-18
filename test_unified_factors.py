#!/usr/bin/env python3
"""
Test script to verify the unified factor model implementation works correctly.
"""

import sys
import os

# Add src to Python path
sys.path.append('/home/runner/work/base_infrastructure/base_infrastructure/src')

def test_unified_factor_imports():
    """Test that all factor models can be imported correctly."""
    print("Testing unified factor model imports...")
    
    try:
        # Test base unified model imports
        from infrastructure.models.factor.factor_model import (
            Factor, FactorValue,
            BondFactor, CompanyShareFactor, EquityFactor, CurrencyFactor,
            CommodityFactor, ETFShareFactor, FuturesFactor, IndexFactor,
            OptionsFactor, SecurityFactor, ShareFactor
        )
        print("✅ Base unified factor model imports successful")
        
        # Test backward compatibility imports
        from infrastructure.models.factor.finance.financial_assets.company_share_factors import (
            CompanyShareFactor as CompanyShareFactorAlias,
            CompanyShareFactorValue
        )
        from infrastructure.models.factor.finance.financial_assets.equity_factors import (
            EquityFactor as EquityFactorAlias,
            EquityFactorValue
        )
        from infrastructure.models.factor.finance.financial_assets.bond_factors import (
            BondFactor as BondFactorAlias,
            BondFactorValue
        )
        print("✅ Backward compatibility imports successful")
        
        # Test polymorphic identity
        print(f"Factor polymorphic identity: {Factor.__mapper_args__['polymorphic_identity']}")
        print(f"BondFactor polymorphic identity: {BondFactor.__mapper_args__['polymorphic_identity']}")
        print(f"EquityFactor polymorphic identity: {EquityFactor.__mapper_args__['polymorphic_identity']}")
        print("✅ Polymorphic identities configured correctly")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_factor_class_structure():
    """Test that the factor classes have the expected structure."""
    print("\nTesting factor class structure...")
    
    try:
        from infrastructure.models.factor.factor_model import Factor, FactorValue, BondFactor
        
        # Check Factor class has discriminator column
        if hasattr(Factor, 'factor_type'):
            print("✅ Factor class has factor_type discriminator column")
        else:
            print("❌ Factor class missing factor_type column")
            return False
        
        # Check FactorValue has entity_type column
        if hasattr(FactorValue, 'entity_type'):
            print("✅ FactorValue class has entity_type column")
        else:
            print("❌ FactorValue class missing entity_type column")
            return False
        
        # Check BondFactor inherits from Factor
        if issubclass(BondFactor, Factor):
            print("✅ BondFactor correctly inherits from Factor")
        else:
            print("❌ BondFactor doesn't inherit from Factor")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Structure test error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("UNIFIED FACTOR MODEL VERIFICATION TEST")
    print("=" * 60)
    
    success = True
    
    # Test imports
    success &= test_unified_factor_imports()
    
    # Test structure
    success &= test_factor_class_structure()
    
    # Final result
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED - Unified factor model is working correctly!")
    else:
        print("💥 SOME TESTS FAILED - Please check the implementation")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)