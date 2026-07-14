from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel


class CompanySharePortfolioOptionPortfolioModel(PortfolioModel):
    """
    SQLAlchemy model for company share portfolio option portfolio.
    Maps to domain.entities.finance.portfolio.company_share_portfolio_option_portfolio.CompanySharePortfolioOptionPortfolio
    """
    __tablename__ = 'company_share_portfolio_option_portfolios'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)
    
    # ONE company_share_portfolio_option_portfolio → MANY company_share_portfolio_option_portfolio_holdings
    company_share_portfolio_option_portfolio_holdings = relationship(
        "src.infrastructure.models.finance.holding.company_share_portfolio_option_portfolio_holding.CompanySharePortfolioOptionPortfolioHoldingModel", 
        back_populates="company_share_portfolio_option_portfolios"
    )
    
    __mapper_args__ = {
        "polymorphic_identity": "CompanySharePortfolioOptionPortfolio",
    }