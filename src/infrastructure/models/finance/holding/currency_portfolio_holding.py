from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.holding.holding import HoldingModel


class CurrencyPortfolioHoldingModel(HoldingModel):
    """
    SQLAlchemy model for a Currency held inside a CurrencyPortfolio.
    Mirrors CompanySharePortfolioHoldingModel.

    FK layout:
      asset_id               → currencies.id          (the currency being held)
      currency_portfolio_id  → currency_portfolios.id  (the owning sub-portfolio)
    """
    __tablename__ = 'currency_portfolio_holdings'

    id = Column(Integer, ForeignKey("holdings.id"), primary_key=True)
    asset_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    currency_portfolio_id = Column(Integer, ForeignKey('currency_portfolios.id'), nullable=False)

    currency_portfolios = relationship(
        "src.infrastructure.models.finance.portfolio.currency_portfolio.CurrencyPortfolioModel",
        back_populates="currency_portfolio_holdings",
    )
    currencies = relationship(
        "src.infrastructure.models.finance.financial_assets.currency.CurrencyModel",
    )

    __mapper_args__ = {
        "polymorphic_identity": "currency_portfolio_holdings",
    }
