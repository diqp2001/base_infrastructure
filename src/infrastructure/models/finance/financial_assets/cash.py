"""
ORM model for Cash - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class CashModel(Base):
    """
    SQLAlchemy ORM model for Cash.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'cash'

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    
    # Cash-specific fields
    amount = Column(Numeric(20, 4), nullable=False, default=0)
    currency = Column(String(3), nullable=False)  # ISO currency code
    
    # Account information
    account_type = Column(String(50), nullable=True)  # e.g., 'checking', 'savings', 'money_market'
    bank_name = Column(String(100), nullable=True)
    account_number_hash = Column(String(64), nullable=True)  # Hashed account number for security
    
    # Interest and fees
    interest_rate = Column(Numeric(5, 4), nullable=True)  # Annual interest rate
    maintenance_fee = Column(Numeric(10, 2), nullable=True, default=0)
    
    # Status fields
    is_available = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)  # For escrow or locked funds
    last_updated = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Cash(id={self.id}, asset_id={self.asset_id}, amount={self.amount}, currency={self.currency})>"