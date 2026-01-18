from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship


from src.infrastructure.models import ModelBase as Base

class PortfolioCompanyShareModel(Base):
    """
    SQLAlchemy model for portfolio holdings.
    Maps to domain.entities.finance.holding.portfolio_holding.PortfolioHolding
    """
    __tablename__ = 'portfolio_company_shares'
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Portfolio identification
    name = Column(String(200), nullable=False, index=True)
    