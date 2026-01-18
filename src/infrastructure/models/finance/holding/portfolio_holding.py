from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship


from src.infrastructure.models import ModelBase as Base

class PortfolioHoldingsModel(Base):
    """
    SQLAlchemy model for portfolio holdings.
    Maps to domain.entities.finance.holding.portfolio_holding.PortfolioHolding
    """
    __tablename__ = 'portfolio_holdings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey('financial_assets.id'), nullable=False)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)

    # Relationships
    portfolio = relationship("src.infrastructure.models.finance.portfolio.portfolio.PortfolioModel", back_populates="portfolio_holdings")
    financial_asset = relationship("src.infrastructure.models.finance.financial_assets.financial_asset.FinancialAssetModel", back_populates="portfolio_holdings")


