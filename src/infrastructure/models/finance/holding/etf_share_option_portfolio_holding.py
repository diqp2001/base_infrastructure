from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class ETFShareOptionPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for portfolio ETF share option holding.
    """
    __tablename__ = 'etf_share_option_portfolio_holdings'
    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)

    # Foreign key to portfolio ETF share option
    etf_share_option_portfolio_id = Column(Integer, ForeignKey("etf_share_option_portfolios.id"), nullable=False)

    # Foreign key to ETF share option asset
    etf_share_option_id = Column(Integer, ForeignKey("etf_share_options.id"), nullable=False)

    # Relationships
    etf_share_option_portfolios = relationship(
        "src.infrastructure.models.finance.portfolio.etf_share_option_portfolio.ETFShareOptionPortfolioModel",
        back_populates="etf_share_option_portfolio_holdings"
    )

    etf_share_options = relationship(
        "src.infrastructure.models.finance.financial_assets.derivative.option.etf_share_option.ETFShareOptionModel",
        back_populates="etf_share_option_portfolio_holdings"
    )

    __mapper_args__ = {
        "polymorphic_identity": "ETFShareOptionPortfolioHoldings",
    }