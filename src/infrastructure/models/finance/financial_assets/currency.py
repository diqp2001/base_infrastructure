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
    country = relationship("src.infrastructure.models.country.CountryModel", back_populates="currency")
    indices = relationship("src.infrastructure.models.finance.financial_assets.index.IndexModel", foreign_keys="IndexModel.currency_id",back_populates="currency")
    derivatives = relationship("src.infrastructure.models.finance.financial_assets.derivative.derivatives.DerivativeModel",foreign_keys="DerivativeModel.currency_id", back_populates="currency")
    def __repr__(self):
        return f"<Currency(id={self.id}, name={self.name}, country_id={self.country_id})>"


