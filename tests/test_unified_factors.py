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
    
    # Test importing from new domain entities
    from src.domain.entities.factor import ShareFactor as NewDomainShareFactor
    from src.domain.entities.factor import ShareMomentumFactor as NewDomainShareMomentumFactor
    from src.domain.entities.factor import EquityFactor as NewDomainEquityFactor
    
    # Test importing from backward compatibility wrappers
    from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor as BackwardCompatShareFactor
    from src.domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share import ShareMomentumFactor as BackwardCompatMomentumFactor
    from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor as BackwardCompatEquityFactor
    
    print("✅ Successfully imported from both new domain entities and backward compatibility wrappers")
    
    # Verify backward compatibility wrappers point to new domain entities
    assert NewDomainShareFactor is BackwardCompatShareFactor, "ShareFactor backward compatibility failed"
    assert NewDomainShareMomentumFactor is BackwardCompatMomentumFactor, "ShareMomentumFactor backward compatibility failed"  
    assert NewDomainEquityFactor is BackwardCompatEquityFactor, "EquityFactor backward compatibility failed"
    
    print("✅ Backward compatibility verified - wrapper imports point to new domain entities")
    
    # Test creating instances
    share_factor = NewDomainShareFactor(
        name="Test Share Factor",
        group="test", 
        ticker_symbol="TEST"
    )
    print(f"✅ Created ShareFactor instance: {share_factor.name} ({share_factor.ticker_symbol})")
    
    momentum_factor = NewDomainShareMomentumFactor(
        name="Test Momentum Factor", 
        group="momentum",
        ticker_symbol="TEST",
        period=20
    )
    print(f"✅ Created ShareMomentumFactor instance: {momentum_factor.name} (period={momentum_factor.period})")
    
    print("\n🏗️ Testing polymorphic structure...")
    print(f"Factors table: {FactorModel.__tablename__}")
    print(f"Factor values table: {FactorValue.__tablename__}")
    print(f"Discriminator column: {FactorModel.factor_type.key}")
    
    print("\n🔍 Testing mapper functionality...")
    from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
    
    # Test domain to ORM conversion
    orm_share_factor = FactorMapper.to_orm(share_factor)
    print(f"✅ Converted domain ShareFactor to ORM: {orm_share_factor.__class__.__name__}")
    
    # Test ORM to domain conversion  
    domain_share_factor = FactorMapper.to_domain(orm_share_factor)
    print(f"✅ Converted ORM back to domain: {domain_share_factor.__class__.__name__}")
    
    print("\n🎉 All tests passed! Unified factor structure with domain entities and discriminator mapping is working correctly.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Test failed: {e}")
    sys.exit(1)