from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class DerivativePortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for portfolio derivative holding.
    Maps to domain.entities.finance.holding.derivative.portfolio_derivative_holding.PortfolioDerivativeHolding
    """
    __tablename__ = 'derivative_portfolio_holdings'
    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)

    # Foreign key to portfolio derivative
    portfolio_derivative_id = Column(Integer, ForeignKey("derivative_portfolios.id"), nullable=False)

    # Foreign key to derivative asset
    derivative_id = Column(Integer, ForeignKey("derivatives.id"), nullable=False)

    # Relationships
    derivative_portfolios = relationship(
        "src.infrastructure.models.finance.portfolio.derivative_portfolio.DerivativePortfolioModel",
        back_populates="derivative_portfolio_holdings"
    )

    derivatives = relationship(
        "src.infrastructure.models.finance.financial_assets.derivative.derivatives.DerivativeModel",
        back_populates="derivative_portfolio_holdings"
    )

    __mapper_args__ = {
        "polymorphic_identity": "derivative_portfolio_holdings",
    }