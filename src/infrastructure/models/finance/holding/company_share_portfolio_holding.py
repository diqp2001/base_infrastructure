from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship, column_property, declared_attr
from src.infrastructure.models.finance.holding.holding import HoldingModel
from src.infrastructure.models import ModelBase as Base


class CompanySharePortfolioHoldingModel(HoldingModel):
    """
    SQLAlchemy model for company share holdings within a portfolio.
    Maps to domain.entities.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHolding
    """
    __tablename__ = 'company_share_portfolio_holdings'

    id = Column(Integer, ForeignKey("holdings.id"), primary_key=True)
    asset_id = Column(Integer, ForeignKey('company_shares.id'), nullable=False)
    company_share_portfolio_id = Column(Integer, ForeignKey('company_share_portfolios.id'), nullable=False)

    # Relationships
    company_share_portfolios = relationship("src.infrastructure.models.finance.portfolio.company_share_portfolio.CompanySharePortfolioModel", back_populates="company_share_portfolio_holdings")
    company_shares = relationship("src.infrastructure.models.finance.financial_assets.company_share.CompanyShareModel", back_populates="company_share_portfolio_holdings")

    @declared_attr
    def __mapper_args__(cls):
        return {
            "polymorphic_identity": "CompanySharePortfolioHoldings",
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
