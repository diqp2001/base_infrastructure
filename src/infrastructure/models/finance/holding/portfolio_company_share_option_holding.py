from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class CompanyShareOptionPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for portfolio company share option holding.
    """
    __tablename__ = 'company_share_option_portfolio_holdings'
    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)

    # Foreign key to portfolio company share option
    portfolio_company_share_option_id = Column(Integer, ForeignKey("portfolio_company_share_options.id"), nullable=False)

    # Foreign key to company share option asset
    company_share_option_id = Column(Integer, ForeignKey("company_share_options.id"), nullable=False)

    # Relationships
    portfolio_company_share_option = relationship(
        "src.infrastructure.models.finance.portfolio.portfolio_company_share_option.CompanyShareOptionPortfolioModel",
        back_populates="company_share_option_portfolio_holdings"
    )

    company_share_option = relationship(
        "src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option.CompanyShareOptionModel",
        back_populates="company_share_option_portfolio_holdings"
    )

    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_portfolio_holdings",
    }