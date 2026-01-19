"""
ORM model for Index - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.models import ModelBase as Base


class IndexModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Index.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'indices'

    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    __mapper_args__ = {
    "polymorphic_identity": "index",
}
    def __repr__(self):
        return f"<Index(id={self.id}, symbol={self.symbol}, name={self.name})>"