from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import column_property, declared_attr
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel
from src.infrastructure.models.finance.holding.holding import HoldingModel


class CompanyShareOptionPortfolioPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for CompanyShareOptionPortfolio holdings within a Portfolio.

    Represents a holding where a Portfolio (container) holds a
    CompanyShareOptionPortfolio (asset), linking the option sub-portfolio
    into the main portfolio tree.

    HoldingModel.asset_id (FK → financial_entities.id) stores the
    CompanyShareOptionPortfolio ID.
    """
    __tablename__ = 'company_share_option_portfolio_portfolio_holdings'

    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)
    company_share_option_portfolio_portfolio_id = Column(
        'container_id', Integer, ForeignKey('portfolios.id'), nullable=False
    )

    @declared_attr
    def __mapper_args__(cls):
        return {
            "polymorphic_identity": "CompanyShareOptionPortfolioPortfolioHoldings",
            "properties": {
                "container_id": column_property(
                    cls.__table__.c.container_id,
                    HoldingModel.__table__.c.container_id,
                ),
            }
        }
