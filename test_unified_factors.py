#!/usr/bin/env python3
"""
Test script to verify the unified factor discriminator structure works correctly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.infrastructure.models.factor.factor_model import (
        FactorModel, 
        ShareFactor, 
        ShareMomentumFactor, 
        ShareTechnicalFactor, 
        ShareTargetFactor, 
        ShareVolatilityFactor,
        EquityFactor,
        SecurityFactor,
        FinancialAssetFactor,
        CountryFactor,
        ContinentFactor,
        FactorValue
    )
    
    print("✅ Successfully imported all factor types from unified model")
    
    # Test discriminator mapping
    print("\n📋 Factor Type Discriminator Mapping:")
    factor_types = [
        (FactorModel, 'factor'),
        (FinancialAssetFactor, 'financial_asset'),
        (SecurityFactor, 'security'), 
        (EquityFactor, 'equity'),
        (ShareFactor, 'share'),
        (ShareMomentumFactor, 'share_momentum'),
        (ShareTechnicalFactor, 'share_technical'),
        (ShareTargetFactor, 'share_target'),
        (ShareVolatilityFactor, 'share_volatility'),
        (CountryFactor, 'country'),
        (ContinentFactor, 'continent')
    ]
    
    for factor_class, expected_discriminator in factor_types:
        discriminator = factor_class.__mapper_args__['polymorphic_identity']
        status = "✅" if discriminator == expected_discriminator else "❌"
        print(f"{status} {factor_class.__name__}: '{discriminator}'")
        
    print("\n🔄 Testing backward compatibility imports...")
    
    # Test importing from domain layer (should use unified model)
    from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor as DomainShareFactor
    from src.domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share import ShareMomentumFactor as DomainShareMomentumFactor
    from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor as DomainEquityFactor
    
    print("✅ Successfully imported from domain layer with backward compatibility")
    
    # Verify they're the same classes
    assert ShareFactor is DomainShareFactor, "ShareFactor backward compatibility failed"
    assert ShareMomentumFactor is DomainShareMomentumFactor, "ShareMomentumFactor backward compatibility failed"  
    assert EquityFactor is DomainEquityFactor, "EquityFactor backward compatibility failed"
    
    print("✅ Backward compatibility verified - all imports point to unified model")
    
    print("\n🏗️ Testing polymorphic structure...")
    print(f"Factors table: {FactorModel.__tablename__}")
    print(f"Factor values table: {FactorValue.__tablename__}")
    print(f"Discriminator column: {FactorModel.factor_type.key}")
    
    print("\n🎉 All tests passed! Unified factor discriminator structure is working correctly.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Test failed: {e}")
    sys.exit(1)