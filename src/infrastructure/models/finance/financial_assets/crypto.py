"""
ORM model for Crypto - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, BigInteger
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Crypto(Base):
    """
    SQLAlchemy ORM model for Crypto.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'crypto'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, unique=True)
    name = Column(String(100), nullable=False)
    
    # Crypto-specific fields
    total_supply = Column(BigInteger, nullable=True)
    max_supply = Column(BigInteger, nullable=True)
    circulating_supply = Column(BigInteger, nullable=True)
    blockchain = Column(String(50), nullable=True)
    consensus_algorithm = Column(String(50), nullable=True)
    
    # Staking fields
    is_stakeable = Column(Boolean, default=False)
    staking_rewards_rate = Column(Numeric(5, 4), nullable=True)
    minimum_stake_amount = Column(Numeric(20, 8), nullable=True)
    unbonding_period_days = Column(Integer, nullable=True)
    
    # Market data fields
    current_price = Column(Numeric(20, 8), default=0)
    market_cap = Column(Numeric(20, 2), nullable=True)
    volume_24h = Column(Numeric(20, 2), nullable=True)
    price_change_24h = Column(Numeric(10, 4), nullable=True)
    volatility_30d = Column(Numeric(10, 4), nullable=True)
    last_update = Column(DateTime, nullable=True)
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    listing_date = Column(Date, nullable=True)

    def __repr__(self):
        return f"<Crypto(id={self.id}, symbol={self.symbol}, name={self.name})>"