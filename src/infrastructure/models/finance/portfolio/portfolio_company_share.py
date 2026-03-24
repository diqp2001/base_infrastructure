from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship


from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
from src.infrastructure.models import ModelBase as Base

class PortfolioCompanyShareModel(PortfolioModel):
    """
    SQLAlchemy model for portfolio holdings.
    Maps to domain.entities.finance.holding.portfolio_holding.PortfolioHolding
    """
    __tablename__ = 'portfolio_company_shares'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)

    
    portfolio_company_share_holdings = relationship("src.infrastructure.models.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHoldingModel", back_populates="portfolio_company_shares")
    __mapper_args__ = {
    "polymorphic_identity": "portfolio_company_shares",}