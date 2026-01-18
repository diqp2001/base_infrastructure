"""
Infrastructure model for portfolio company share options - SQLAlchemy model matching domain entity
"""
from datetime import date
from typing import Optional

from sqlalchemy import Column, Integer, Date, String, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base


class PortfolioCompanyShareOptionModel(Base):
    """
    SQLAlchemy model for portfolio company share options.
    Maps to domain.entities.finance.financial_assets.derivatives.option.portfolio_company_share_option.PortfolioCompanyShareOption
    
    Contains only basic identification and date parameters as requested.
    """
    __tablename__ = 'portfolio_company_share_options'

    id = Column(Integer, primary_key=True)
    
    name = Column(String(200), nullable=False, index=True)