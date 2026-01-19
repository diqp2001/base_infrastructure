"""
ORM model for Currency - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Date, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class CurrencyModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Currency.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    Enhanced with country relationship and exchange rate management.
    """
    __tablename__ = 'currencies'
    
   
    
    # Country relationship
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=True, index=True)
    
    # Exchange rate data
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    
    __mapper_args__ = {
        "polymorphic_identity": "currency",
    }

    # Relationships
    country = relationship("src.infrastructure.models.country.CountryModel", back_populates="currencies")
    
    def __repr__(self):
        return f"<Currency(id={self.id}, iso_code={self.iso_code}, name={self.name}, country_id={self.country_id})>"


