#!/usr/bin/env python3
"""
Simple test script to check if SQLAlchemy models are being imported correctly.
"""
import sys
sys.path.append('src')

try:
    # Import the holding model
    from src.infrastructure.models.finance.holding.derivative.portfolio_derivative_holding import PortfolioDerivativeHoldingModel
    print("✅ PortfolioDerivativeHoldingModel imported successfully")
    
    # Import the portfolio model
    from src.infrastructure.models.finance.portfolio.portfolio_derivative import DerivativePortfolioModel
    print("✅ DerivativePortfolioModel imported successfully")
    
    # Check the relationship string
    holding_model = PortfolioDerivativeHoldingModel
    rel_property = holding_model.portfolio_derivative.property
    print(f"📝 Relationship string: {rel_property.argument}")
    
    # Try to resolve the string
    from sqlalchemy.orm import configure_mappers
    
    print("🔄 Configuring mappers...")
    configure_mappers()
    print("✅ Mappers configured successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()