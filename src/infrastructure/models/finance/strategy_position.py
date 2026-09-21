"""ORM model for strategy-level spread positions.

Stores the full strategy position dict (greeks, strikes, entry metadata) as JSON
alongside a lifecycle flag so manage_existing_positions can load positions from the
DB instead of an in-memory dict.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

from src.infrastructure.models import ModelBase as Base


class StrategyPositionModel(Base):
    __tablename__ = 'strategy_positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(String(200), nullable=False, unique=True)
    portfolio_id = Column(Integer, nullable=True)
    data_json = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"<StrategyPosition(position_id={self.position_id}, active={self.is_active})>"
