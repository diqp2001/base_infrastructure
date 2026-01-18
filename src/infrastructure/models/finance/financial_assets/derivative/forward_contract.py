"""
ORM model for Forward Contract - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class ForwardContractModel(Base):
    """
    SQLAlchemy ORM model for Forward Contract.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'forward_contracts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Contract identification
    ticker = Column(String(50), nullable=False, index=True)
    underlying_asset_id = Column(Integer, nullable=False)
    underlying_symbol = Column(String(20), nullable=False)
    
    # Forward contract specifics
    forward_price = Column(Numeric(20, 8), nullable=False)
    contract_size = Column(Numeric(15, 4), nullable=False, default=1)
    delivery_date = Column(Date, nullable=False)
    
    # Settlement details
    settlement_type = Column(String(20), nullable=False, default='cash')  # 'cash' or 'physical'
    
    # Pricing and valuation
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    theoretical_forward_price = Column(Numeric(20, 8), nullable=True)
    basis = Column(Numeric(20, 8), nullable=True)  # Spot - Forward price
    mark_to_market_value = Column(Numeric(20, 8), nullable=True, default=0)
    intrinsic_value = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Cost of carry components
    risk_free_rate = Column(Numeric(10, 6), nullable=True)
    dividend_yield = Column(Numeric(10, 6), nullable=True)
    storage_cost = Column(Numeric(10, 6), nullable=True)
    convenience_yield = Column(Numeric(10, 6), nullable=True)
    
    # Contract status
    days_to_expiry = Column(Integer, nullable=True)
    is_expired = Column(Boolean, default=False)
    is_tradeable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Settlement information
    settlement_amount = Column(Numeric(20, 8), nullable=True, default=0)
    is_settled = Column(Boolean, default=False)
    settlement_date = Column(Date, nullable=True)
    
    # Margin and risk management
    initial_margin = Column(Numeric(20, 2), nullable=True)
    maintenance_margin = Column(Numeric(20, 2), nullable=True)
    margin_requirement_rate = Column(Numeric(5, 4), nullable=True, default=0.1)  # 10%
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_valuation_date = Column(DateTime, nullable=True)

    # Relationship

    def __repr__(self):
        return f"<ForwardContract(id={self.id}, ticker={self.ticker}, forward_price={self.forward_price}, delivery={self.delivery_date})>"


