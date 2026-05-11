#!/usr/bin/env python3
"""
Simple test script to verify the new entities work correctly
"""

def test_imports():
    """Test that all new components can be imported without errors"""
    try:
        # Test domain entities
        from src.domain.entities.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolio
        from src.domain.entities.finance.holding.company_share_portfolio_option_portfolio_holding import CompanySharePortfolioOptionPortfolioHolding
        
        # Test infrastructure models
        from src.infrastructure.models.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolioModel
        from src.infrastructure.models.finance.holding.company_share_portfolio_option_portfolio_holding import CompanySharePortfolioOptionPortfolioHoldingModel
        
        # Test ports
        from src.domain.ports.finance.portfolio.company_share_portfolio_option_portfolio_port import CompanySharePortfolioOptionPortfolioPort
        from src.domain.ports.finance.holding.company_share_portfolio_option_portfolio_holding_port import CompanySharePortfolioOptionPortfolioHoldingPort
        
        # Test mappers
        from src.infrastructure.repositories.mappers.finance.portfolio.company_share_portfolio_option_portfolio_mapper import CompanySharePortfolioOptionPortfolioMapper
        from src.infrastructure.repositories.mappers.finance.holding.company_share_portfolio_option_portfolio_holding_mapper import CompanySharePortfolioOptionPortfolioHoldingMapper
        
        # Test repositories
        from src.infrastructure.repositories.local_repo.finance.portfolio.company_share_portfolio_option_portfolio_repository import CompanySharePortfolioOptionPortfolioRepository
        from src.infrastructure.repositories.local_repo.finance.holding.company_share_portfolio_option_portfolio_holding_repository import CompanySharePortfolioOptionPortfolioHoldingRepository
        
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
        from datetime import date
        from src.domain.entities.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolio
        
        # Create a basic portfolio entity
        portfolio = CompanySharePortfolioOptionPortfolio(
            id=1,
            name="Test Portfolio",
            start_date=date.today()
        )
        
        assert portfolio.id == 1
        assert portfolio.name == "Test Portfolio"
        assert portfolio.start_date == date.today()
        
        print("✅ Entity creation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Entity creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mapper_functionality():
    """Test basic mapper functionality"""
    try:
        from datetime import date
        from src.domain.entities.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolio
        from src.infrastructure.repositories.mappers.finance.portfolio.company_share_portfolio_option_portfolio_mapper import CompanySharePortfolioOptionPortfolioMapper
        
        # Create a domain entity
        portfolio = CompanySharePortfolioOptionPortfolio(
            id=1,
            name="Test Portfolio",
            start_date=date.today()
        )
        
        # Test mapper
        mapper = CompanySharePortfolioOptionPortfolioMapper()
        assert mapper.discriminator == "company_share_portfolio_option_portfolio"
        assert mapper.entity_class == CompanySharePortfolioOptionPortfolio
        
        print("✅ Mapper functionality successful!")
        return True
        
    except Exception as e:
        print(f"❌ Mapper error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing new CompanySharePortfolioOptionPortfolio entities...")
    
    success = True
    success &= test_imports()
    success &= test_entity_creation()
    success &= test_mapper_functionality()
    
    if success:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed!")
    
    exit(0 if success else 1)