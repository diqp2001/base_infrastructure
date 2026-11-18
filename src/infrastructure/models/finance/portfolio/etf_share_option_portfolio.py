from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel


class ETFShareOptionPortfolioModel(PortfolioModel):
    """
    SQLAlchemy model for portfolio ETF share option.
    Maps to domain.entities.finance.portfolio.etf_share_option_portfolio.ETFShareOptionPortfolio
    """
    __tablename__ = 'etf_share_option_portfolios'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)
    
    

    # ONE portfolio_etf_share_option → MANY portfolio_etf_share_option_holdings
    etf_share_option_portfolio_holdings = relationship(
        "src.infrastructure.models.finance.holding.etf_share_option_portfolio_holding.ETFShareOptionPortfolioHoldingModel", 
        back_populates="etf_share_option_portfolios"
    )
    
    __mapper_args__ = {
        "polymorphic_identity": "ETFShareOptionPortfolio",
    }