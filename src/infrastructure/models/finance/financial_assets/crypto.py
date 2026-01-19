"""
ORM model for Crypto - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, BigInteger, Text
from sqlalchemy import ForeignKey
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class CryptoModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Crypto.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'crypto'

    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    __mapper_args__ = {
    "polymorphic_identity": "crypto",
}
    def __repr__(self):
        return f"<Crypto(id={self.id}, symbol={self.symbol}, name={self.name})>"