from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, column_property, declared_attr
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel
from src.infrastructure.models.finance.holding.holding import HoldingModel


class CompanySharePortfolioPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for CompanySharePortfolio holdings within a Portfolio.
    Maps to domain.entities.finance.holding.company_share_portfolio_portfolio_holding.CompanySharePortfolioPortfolioHolding

    Represents a holding where a Portfolio (container) holds a CompanySharePortfolio (asset).
    HoldingModel.asset_id (FK → financial_entities.id) stores the CompanySharePortfolio ID.
    """
    __tablename__ = 'company_share_portfolio_portfolio_holdings'

    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)
    company_share_portfolio_portfolio_id = Column(
        'container_id', Integer, ForeignKey('portfolios.id'), nullable=False
    )

    # asset_id is inherited from HoldingModel (FK → financial_entities.id).
    # The join condition goes through the joined-table PK chain:
    #   holdings.asset_id == financial_entities.id == portfolios.id == company_share_portfolios.id
    company_share_portfolio = relationship(
        "src.infrastructure.models.finance.portfolio.company_share_portfolio.CompanySharePortfolioModel",
        primaryjoin="CompanySharePortfolioPortfolioHoldingModel.asset_id == CompanySharePortfolioModel.id",
        foreign_keys="[HoldingModel.asset_id]",
        back_populates="company_share_portfolio_portfolio_holdings",
        viewonly=True,
    )

    @declared_attr
    def __mapper_args__(cls):
        return {
            "polymorphic_identity": "CompanySharePortfolioPortfolioHoldings",
            "properties": {
                # container_id exists in both holdings and this child table —
                # merge them so both receive the value on INSERT.
                "container_id": column_property(
                    cls.__table__.c.container_id,
                    HoldingModel.__table__.c.container_id,
                ),
            }
        }
