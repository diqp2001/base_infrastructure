from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, column_property, declared_attr
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel
from src.infrastructure.models.finance.holding.holding import HoldingModel


class CompanySharePortfolioPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for CompanySharePortfolio holdings within a Portfolio.
    Maps to domain.entities.finance.holding.company_share_portfolio_portfolio_holding.CompanySharePortfolioPortfolioHolding

    Represents a holding where a Portfolio (container) holds a CompanySharePortfolio (asset).
    """
    __tablename__ = 'company_share_portfolio_portfolio_holdings'

    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)
    company_share_portfolio_id = Column(
        'asset_id', Integer, ForeignKey('company_share_portfolios.id'), nullable=False
    )
    company_share_portfolio_portfolio_id = Column(
        'container_id', Integer, ForeignKey('portfolios.id'), nullable=False
    )
    # Relationships
    company_share_portfolio = relationship(
        "src.infrastructure.models.finance.portfolio.company_share_portfolio.CompanySharePortfolioModel",
        foreign_keys=[company_share_portfolio_id],
        back_populates="company_share_portfolio_portfolio_holdings"
    )

    @declared_attr
    def __mapper_args__(cls):
        return {
            "polymorphic_identity": "CompanySharePortfolioPortfolioHoldings",
            "properties": {
                # Explicitly combine both tables' asset_id column under one
                # attribute to suppress the "Implicitly combining column" SAWarning.
                # Both columns receive the same value on INSERT/UPDATE; SELECTs
                # read from the subclass column (first argument).
                "asset_id": column_property(
                    cls.__table__.c.asset_id,
                    HoldingModel.__table__.c.asset_id,
                ),
                "container_id": column_property(
                    cls.__table__.c.container_id,
                    HoldingModel.__table__.c.container_id,
                ),
            }
        }
