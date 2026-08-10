from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, column_property, declared_attr
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel
from src.infrastructure.models.finance.holding.holding import HoldingModel


class CurrencyPortfolioPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for a CurrencyPortfolio held inside a Portfolio.

    HoldingModel.asset_id (FK → financial_entities.id) stores the CurrencyPortfolio ID.
    The child table only adds the container_id FK for referential integrity on portfolios.
    """
    __tablename__ = 'currency_portfolio_portfolio_holdings'

    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)

    currency_portfolio_portfolio_id = Column(
        'container_id', Integer, ForeignKey('portfolios.id'), nullable=False
    )

    # asset_id is inherited from HoldingModel (FK → financial_entities.id).
    currency_portfolio = relationship(
        "src.infrastructure.models.finance.portfolio.currency_portfolio.CurrencyPortfolioModel",
        primaryjoin="CurrencyPortfolioPortfolioHoldingModel.asset_id == CurrencyPortfolioModel.id",
        foreign_keys="[HoldingModel.asset_id]",
        back_populates="currency_portfolio_portfolio_holdings",
        viewonly=True,
    )

    @declared_attr
    def __mapper_args__(cls):
        return {
            "polymorphic_identity": "CurrencyPortfolioPortfolioHoldings",
            "properties": {
                "container_id": column_property(
                    cls.__table__.c.container_id,
                    HoldingModel.__table__.c.container_id,
                ),
            }
        }
