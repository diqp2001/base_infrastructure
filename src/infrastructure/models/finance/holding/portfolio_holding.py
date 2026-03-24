from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.holding.holding import HoldingModel


from src.infrastructure.models import ModelBase as Base

class PortfolioHoldingsModel(HoldingModel):
    """
    SQLAlchemy model for portfolio holdings.
    Maps to domain.entities.finance.holding.portfolio_holding.PortfolioHolding
    """
    __tablename__ = 'portfolio_holdings'
    
    id = Column(Integer, ForeignKey("holdings.id"), primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)

    # Relationships
    portfolio = relationship("src.infrastructure.models.finance.portfolio.portfolio.PortfolioModel", back_populates="portfolio_holdings")
    __mapper_args__ = {
    "polymorphic_identity": "portfolio_holding",}
