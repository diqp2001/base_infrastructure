#!/usr/bin/env python3
"""
Simple test script to verify the new CompanySharePortfolioPortfolioHolding entities work correctly
"""

def test_imports():
    """Test that all new components can be imported without errors"""
    try:
        # Test domain entities
        from src.domain.entities.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHolding
        from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
        from src.domain.entities.finance.portfolio.portfolio import Portfolio
        from src.domain.entities.finance.holding.position import Position
        
        # Test infrastructure models
        from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHoldingModel
        from src.infrastructure.models.finance.portfolio.company_share_portfolio import CompanySharePortfolioModel
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_entity_creation():
    """Test basic entity creation"""
    try:
        from datetime import date, datetime
        from src.domain.entities.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHolding
        from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
        from src.domain.entities.finance.portfolio.portfolio import Portfolio
        from src.domain.entities.finance.holding.position import Position
        
        # Create basic entities for testing
        portfolio = Portfolio(
            id=1,
            name="Main Portfolio",
            start_date=date.today()
        )
        
        company_share_portfolio = CompanySharePortfolio(
            id=2,
            name="Tech Stocks Portfolio",
            start_date=date.today()
        )
        
        position = Position(id=1, quantity=100)  # Assuming Position takes these params
        
        # Create the holding
        holding = CompanySharePortfolioPortfolioHolding(
            id=1,
            portfolio=portfolio,
            company_share_portfolio=company_share_portfolio,
            position=position,
            start_date=datetime.now()
        )
        
        assert holding.id == 1
        assert holding.container == portfolio
        assert holding.asset == company_share_portfolio
        assert holding.company_share_portfolio == company_share_portfolio
        
        print("✅ Entity creation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Entity creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing new CompanySharePortfolioPortfolioHolding entities...")
    
    success = True
    success &= test_imports()
    success &= test_entity_creation()
    
    if success:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed!")
    
    exit(0 if success else 1)