from sqlalchemy import Column, Integer, ForeignKey, Date
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel


class CompanyShareOptionPortfolioModel(PortfolioModel):
    """
    SQLAlchemy model for portfolio company share option.
    Maps to domain.entities.finance.portfolio.company_share_option_portfolio.CompanyShareOptionPortfolio
    """
    __tablename__ = 'company_share_option_portfolios'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)
    
    

    # ONE portfolio_company_share_option → MANY portfolio_company_share_option_holdings
    company_share_option_portfolio_holdings = relationship(
        "src.infrastructure.models.finance.holding.company_share_option_portfolio_holding.CompanyShareOptionPortfolioHoldingModel", 
        back_populates="company_share_option_portfolios"
    )
    
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_portfolios",
    }