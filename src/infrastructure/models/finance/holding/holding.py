"""
Infrastructure models for holdings - SQLAlchemy models matching domain entities
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base


class HoldingModel(Base):
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
    asset = relationship("src.infrastructure.models.finance.financial_assets.financial_asset.FinancialAssetModel",
                         foreign_keys=[asset_id],
                          back_populates="holdings")
    orders = relationship("src.infrastructure.models.finance.order.order.OrderModel", foreign_keys="OrderModel.holding_id", back_populates="holdings")
    __mapper_args__ = {
    "polymorphic_identity": "holding",}

