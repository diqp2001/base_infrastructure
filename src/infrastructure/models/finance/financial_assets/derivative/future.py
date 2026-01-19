"""
ORM model for Futures - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey, Enum as SQLEnum
import enum
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class FutureType(enum.Enum):
    COMMODITY = "commodity"
    BOND = "bond"
    INDEX = "index"
    CURRENCY = "currency"


class FutureModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Futures.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'futures'

    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    

    __mapper_args__ = {
    "polymorphic_identity": "future",
}

    def __repr__(self):
        return f"<Futures(id={self.id}, symbol={self.symbol}, type={self.future_type})>"