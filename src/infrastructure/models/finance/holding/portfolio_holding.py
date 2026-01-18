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
    portfolios = relationship("Portfolio", back_populates="portfolio_holdings")
    financial_financial_assetsasset = relationship("FinancialAsset", back_populates="portfolio_holdings")


