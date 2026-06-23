from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class CurrencyPortfolioPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for a CurrencyPortfolio held inside a Portfolio.

    DB layout (3-level joined inheritance: holdings → portfolio_holdings → this table):
      holdings.asset_id           → plain integer set to currency_portfolio FK value
      holdings.container_id       → FK portfolios.id (parent portfolio)
      portfolio_holdings.portfolio_id → FK portfolios.id (parent portfolio)
      this table's asset_id       → FK currency_portfolios.id (sub-portfolio being held)
      this table's container_id   → FK portfolios.id (parent portfolio)

    No column_property merging here: asset_id (base) and currency_portfolio_id (child)
    are set independently in to_model() to avoid circular attribute-listener recursion
    that arises when multiple subclasses share a column_property on HoldingModel.asset_id.
    """
    __tablename__ = 'currency_portfolio_portfolio_holdings'

    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)

    currency_portfolio_id = Column(
        'asset_id', Integer, ForeignKey('currency_portfolios.id'), nullable=False
    )
    currency_portfolio_portfolio_id = Column(
        'container_id', Integer, ForeignKey('portfolios.id'), nullable=False
    )

    currency_portfolio = relationship(
        "src.infrastructure.models.finance.portfolio.currency_portfolio.CurrencyPortfolioModel",
        foreign_keys=[currency_portfolio_id],
        back_populates="currency_portfolio_portfolio_holdings",
    )

    __mapper_args__ = {
        "polymorphic_identity": "CurrencyPortfolioPortfolioHoldings",
    }
