from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, column_property, declared_attr
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

    @declared_attr
    def __mapper_args__(cls):
        return {
            "polymorphic_identity": "CurrencyPortfolioHoldings",
            "properties": {
                # Explicitly combine both tables' asset_id column under one
                # attribute to suppress the "Implicitly combining column" SAWarning.
                # Both columns receive the same value on INSERT/UPDATE; SELECTs
                # read from the subclass column (first argument).
                "asset_id": column_property(
                    cls.__table__.c.asset_id,
                    HoldingModel.__table__.c.asset_id,
                )
            }
        }
