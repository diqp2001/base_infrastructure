from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class PortfolioCompanyShareHoldingModel(Base):
    """
    SQLAlchemy model for company share holdings within a portfolio.
    Maps to domain.entities.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHolding
    """
    __tablename__ = 'portfolio_company_share_holdings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey('company_shares.id'), nullable=False)
    portfolio_company_share_id = Column(Integer, ForeignKey('portfolio_company_shares.id'), nullable=False)

    # Relationships
    portfolio_company_shares = relationship("PortfolioCompanyShare", back_populates="portfolio_company_share_holdings")
    company_shares = relationship("CompanyShare", back_populates="portfolio_company_share_holdings")