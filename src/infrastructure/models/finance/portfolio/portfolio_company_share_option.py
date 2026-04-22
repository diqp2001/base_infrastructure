from sqlalchemy import Column, Integer, ForeignKey, Date
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel


class PortfolioCompanyShareOptionModel(PortfolioModel):
    """
    SQLAlchemy model for portfolio company share option.
    Maps to domain.entities.finance.portfolio.portfolio_company_share_option.PortfolioCompanyShareOption
    """
    __tablename__ = 'portfolio_company_share_options'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # ONE portfolio_company_share_option → MANY portfolio_company_share_option_holdings
    portfolio_company_share_option_holdings = relationship(
        "src.infrastructure.models.finance.holding.portfolio_company_share_option_holding.PortfolioCompanyShareOptionHoldingModel", 
        back_populates="portfolio_company_share_option"
    )
    
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_company_share_option",
    }