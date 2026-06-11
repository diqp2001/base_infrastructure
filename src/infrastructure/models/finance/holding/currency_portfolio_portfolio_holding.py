from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class CurrencyPortfolioPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for a CurrencyPortfolio held inside a Portfolio.
    Mirrors CompanySharePortfolioPortfolioHoldingModel.

    asset_id overrides HoldingModel.asset_id to point at currency_portfolios.id
    instead of financial_assets.id — the same FK-override pattern used by the
    CompanyShare variant.
    """
    __tablename__ = 'currency_portfolio_portfolio_holdings'

    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)
    asset_id = Column(Integer, ForeignKey('currency_portfolios.id'), nullable=False)

    currency_portfolio = relationship(
        "src.infrastructure.models.finance.portfolio.currency_portfolio.CurrencyPortfolioModel",
        foreign_keys=[asset_id],
        back_populates="currency_portfolio_portfolio_holdings",
    )

    __mapper_args__ = {
        "polymorphic_identity": "currency_portfolio_portfolio_holdings",
    }
