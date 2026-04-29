from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.holding.holding import HoldingModel
from src.infrastructure.models import ModelBase as Base


class PortfolioCompanyShareHoldingModel(HoldingModel):
    """
    SQLAlchemy model for company share holdings within a portfolio.
    Maps to domain.entities.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHolding
    """
    __tablename__ = 'portfolio_company_share_holdings'
    
    id = Column(Integer, ForeignKey("holdings.id"), primary_key=True)
    asset_id = Column(Integer, ForeignKey('company_shares.id'), nullable=False)
    portfolio_company_share_id = Column(Integer, ForeignKey('portfolio_company_shares.id'), nullable=False)

    # Relationships
    portfolio_company_shares = relationship("src.infrastructure.models.finance.portfolio.portfolio_company_share.CompanySharePortfolioModel", back_populates="portfolio_company_share_holdings")
    company_shares = relationship("src.infrastructure.models.finance.financial_assets.company_share.CompanyShareModel", back_populates="portfolio_company_share_holdings")

    __mapper_args__ = {
    "polymorphic_identity": "portfolio_company_share_holding",}