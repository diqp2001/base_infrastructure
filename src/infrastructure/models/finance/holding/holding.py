"""
Infrastructure models for holdings - SQLAlchemy models matching domain entities
"""
from datetime import datetime

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

    # Direct link to the position that tracks quantity for this holding.
    # use_alter defers the FK constraint so the circular positions↔holdings
    # dependency does not block table creation.
    position_id = Column(
        Integer,
        ForeignKey('positions.id', use_alter=True, name='fk_holdings_position_id'),
        nullable=True,
    )

    # Relationships
    asset = relationship(
        "src.infrastructure.models.finance.financial_assets.financial_asset.FinancialAssetModel",
        foreign_keys=[asset_id],
        back_populates="holdings",
    )
    orders = relationship(
        "src.infrastructure.models.finance.order.order.OrderModel",
        foreign_keys="OrderModel.holding_id",
        back_populates="holdings",
    )
    # position_rel: the one Position row that belongs to this holding.
    # post_update=True handles the circular INSERT/UPDATE with positions.holding_id.
    position_rel = relationship(
        "src.infrastructure.models.finance.position.PositionModel",
        foreign_keys=[position_id],
        uselist=False,
        post_update=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": "holding",
    }
