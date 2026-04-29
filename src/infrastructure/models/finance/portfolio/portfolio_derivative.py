from sqlalchemy import Column, Integer, ForeignKey, Date
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel


class DerivativePortfolioModel(PortfolioModel):
    """
    SQLAlchemy model for portfolio derivative.
    Maps to domain.entities.finance.portfolio.derivative_portfolio.DerivativePortfolio
    """
    __tablename__ = 'portfolio_derivatives'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)
    
    

    # ONE portfolio_derivative → MANY portfolio_derivative_holdings
    portfolio_derivative_holdings = relationship(
        "src.infrastructure.models.finance.holding.derivative.portfolio_derivative_holding.PortfolioDerivativeHoldingModel", 
        back_populates="portfolio_derivative"
    )
    
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_derivative",
    }