"""
Infrastructure models for holdings - SQLAlchemy models matching domain entities
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base


class Holding(Base):
    """
    Base SQLAlchemy model for holdings.
    Maps to domain.entities.finance.holding.holding.Holding
    """
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey('financial_assets.id'), nullable=False)
    container_id = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)

    # Relationships
    asset = relationship("FinancialAsset", back_populates="holdings")


