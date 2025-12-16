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
    underlying_id = Column(Integer, ForeignKey('portfolio_company_shares.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    expiration_date = Column(Date, nullable=False)
    option_type = Column(String(10), nullable=False)  # 'CALL' or 'PUT'
    exercise_style = Column(String(20), nullable=False)
    strike_id = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationships
    underlying = relationship("PortfolioCompanyShareModel")
    company = relationship("CompanyModel")