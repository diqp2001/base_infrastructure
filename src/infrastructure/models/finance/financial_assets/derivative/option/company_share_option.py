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
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    
    # Index future option specific fields
    strike_price = Column(Numeric(precision=15, scale=6), nullable=True)
    multiplier = Column(Numeric(precision=10, scale=2), nullable=True, default=1.0)
    expiry = Column(String(20), nullable=True)
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="company_share_options") 
    
    
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option",
    }
    
    def __repr__(self):
        return f"<CompanyShareOption(id={self.id}, symbol={self.symbol})>"