"""
ORM model for Options - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey, Enum as SQLEnum
from src.infrastructure.models import ModelBase as Base
import enum
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class OptionType(enum.Enum):
    CALL = "call"
    PUT = "put"


class OptionsModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Options.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'options'

    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    option_type = Column(SQLEnum(OptionType), nullable=False)
    
    __mapper_args__ = {
    "polymorphic_identity": "option",
}
    def __repr__(self):
        return f"<Options(id={self.id}, symbol={self.symbol})>"