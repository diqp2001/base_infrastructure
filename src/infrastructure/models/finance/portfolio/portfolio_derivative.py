from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel

class PortfolioDerivativeModel(PortfolioModel):
    """
    SQLAlchemy model for portfolio holdings.
    Maps to domain.entities.finance.holding.portfolio_holding.PortfolioHolding
    """
    __tablename__ = 'portfolio_derivatives'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)

    
    __mapper_args__ = {
    "polymorphic_identity": "portfolio_derivative",}