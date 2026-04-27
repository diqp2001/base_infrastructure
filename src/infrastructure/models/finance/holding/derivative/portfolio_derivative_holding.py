from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class PortfolioDerivativeHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for portfolio derivative holding.
    Maps to domain.entities.finance.holding.derivative.portfolio_derivative_holding.PortfolioDerivativeHolding
    """
    __tablename__ = 'portfolio_derivative_holdings'
    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)

    # Foreign key to portfolio derivative
    portfolio_derivative_id = Column(Integer, ForeignKey("portfolio_derivatives.id"), nullable=False)

    # Foreign key to derivative asset
    derivative_id = Column(Integer, ForeignKey("derivatives.id"), nullable=False)

    # Relationships
    portfolio_derivative = relationship(
        "src.infrastructure.models.finance.portfolio.portfolio_derivative.PortfolioDerivativeModel",
        back_populates="portfolio_derivative_holdings"
    )

    derivative = relationship(
        "src.infrastructure.models.finance.financial_assets.derivative.derivatives.DerivativeModel",
        back_populates="portfolio_derivative_holdings"
    )

    __mapper_args__ = {
        "polymorphic_identity": "portfolio_derivative_holding",
    }