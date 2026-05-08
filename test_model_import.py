#!/usr/bin/env python3
"""
Simple test script to check if SQLAlchemy models are being imported correctly.
"""
import sys
sys.path.append('src')

try:
    # Import the holding model
    from infrastructure.models.finance.holding.derivative.derivative_portfolio_holding import DerivativePortfolioHoldingModel
    print("✅ PortfolioDerivativeHoldingModel imported successfully")
    
    # Import the portfolio model
    from infrastructure.models.finance.portfolio.derivative_portfolio import DerivativePortfolioModel
    print("✅ DerivativePortfolioModel imported successfully")
    
    # Check the relationship string
    holding_model = DerivativePortfolioHoldingModel
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