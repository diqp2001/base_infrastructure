#!/usr/bin/env python3
"""
Quick test to verify imports work
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Test new domain entities
    from src.domain.entities.factor.share_momentum_factor import ShareMomentumFactor
    print("✅ ShareMomentumFactor imported successfully")
    
    # Test backward compatibility wrapper
    from src.domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share import ShareMomentumFactor as BackwardCompatMomentumFactor  
    print("✅ Backward compatibility wrapper imported successfully")
    
    # Test they're the same
    print(f"Same class: {ShareMomentumFactor is BackwardCompatMomentumFactor}")
    
    # Test creation
    factor = ShareMomentumFactor(
        name="Test Momentum",
        group="momentum",
        ticker_symbol="TEST", 
        period=20
    )
    print(f"✅ Created instance: {factor.name} - {factor.ticker_symbol} (period: {factor.period})")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()