"""
ORM model for CompanyShareOptions - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.infrastructure.models.finance.financial_assets.derivative.option.options import OptionsModel


class CompanyShareOptionModel(OptionsModel):
    """
    SQLAlchemy ORM model for Company Share Options.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'company_share_options'

    id = Column(Integer, ForeignKey("options.id"), primary_key=True)
    
    # Additional fields specific to company share options can be added here
    # For example: strike_price, expiration_date, contract_size, etc.
    
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option",
    }
    
    def __repr__(self):
        return f"<CompanyShareOption(id={self.id}, symbol={self.symbol})>"