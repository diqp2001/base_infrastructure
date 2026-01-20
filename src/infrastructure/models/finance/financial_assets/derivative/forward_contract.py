"""
ORM model for Forward Contract - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.models.finance.financial_assets.derivative.derivatives import DerivativeModel

class ForwardContractModel(DerivativeModel):
    """
    SQLAlchemy ORM model for Forward Contract.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'forward_contracts'

    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    

    __mapper_args__ = {
    "polymorphic_identity": "forward_contract",
}

    def __repr__(self):
        return f"<ForwardContract(id={self.id}, ticker={self.ticker}, forward_price={self.forward_price}, delivery={self.delivery_date})>"


