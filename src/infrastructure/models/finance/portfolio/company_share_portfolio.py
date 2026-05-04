from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship


from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
from src.infrastructure.models import ModelBase as Base

class CompanySharePortfolioModel(PortfolioModel):
    """
    SQLAlchemy model for portfolio holdings.
    Maps to domain.entities.finance.holding.portfolio_holding.PortfolioHolding
    """
    __tablename__ = 'company_share_portfolios'
    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)

    
    portfolio_company_share_holdings = relationship("src.infrastructure.models.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHoldingModel", back_populates="company_share_portfolios")
    __mapper_args__ = {
    "polymorphic_identity": "company_share_portfolios",}