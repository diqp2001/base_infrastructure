from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel


class CompanySharePortfolioOptionPortfolioHoldingModel(PortfolioHoldingsModel):
    """
    SQLAlchemy model for company share portfolio option portfolio holding.
    Maps to domain.entities.finance.holding.company_share_portfolio_option_portfolio_holding.CompanySharePortfolioOptionPortfolioHolding
    """
    __tablename__ = 'company_share_portfolio_option_portfolio_holdings'
    id = Column(Integer, ForeignKey("portfolio_holdings.id"), primary_key=True)

    # Foreign key to company share portfolio option portfolio
    company_share_portfolio_option_portfolio_id = Column(Integer, ForeignKey("company_share_portfolio_option_portfolios.id"), nullable=False)

    # Foreign key to company share portfolio option asset
    company_share_portfolio_option_id = Column(Integer, ForeignKey("company_share_portfolio_options.id"), nullable=False)

    # Relationships
    company_share_portfolio_option_portfolios = relationship(
        "src.infrastructure.models.finance.portfolio.company_share_portfolio_option_portfolio.CompanySharePortfolioOptionPortfolioModel",
        back_populates="company_share_portfolio_option_portfolio_holdings"
    )

    company_share_portfolio_options = relationship(
        "src.infrastructure.models.finance.financial_assets.derivative.option.company_share_portfolio_option.CompanySharePortfolioOptionModel",
        back_populates="company_share_portfolio_option_portfolio_holdings"
    )

    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_portfolio_holdings",
    }