from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class CompanySharePortfolioPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for CompanySharePortfolio holdings within a Portfolio.
    Maps to domain.entities.finance.holding.company_share_portfolio_portfolio_holding.CompanySharePortfolioPortfolioHolding
    
    Represents a holding where a Portfolio (container) holds a CompanySharePortfolio (asset).
    """
    __tablename__ = 'company_share_portfolio_portfolio_holdings'
    
    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)
    asset_id = Column(Integer, ForeignKey('company_share_portfolios.id'), nullable=False)

    # Relationships
    company_share_portfolio = relationship(
        "src.infrastructure.models.finance.portfolio.company_share_portfolio.CompanySharePortfolioModel", 
        foreign_keys=[asset_id],
        back_populates="company_share_portfolio_portfolio_holdings"
    )

    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_portfolio_holdings",
    }