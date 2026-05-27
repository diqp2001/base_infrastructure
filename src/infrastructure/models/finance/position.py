"""
Infrastructure model for position.
SQLAlchemy model for domain position entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.holding.position import PositionType


class PositionModel(Base):
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    position_type = Column(SQLEnum(PositionType), nullable=False)

    # Direct back-link to the holding this position belongs to.
    holding_id = Column(
        Integer,
        ForeignKey('holdings.id', name='fk_positions_holding_id'),
        nullable=True,
    )

    # Relationships
    portfolios = relationship(
        "src.infrastructure.models.finance.portfolio.portfolio.PortfolioModel",
        back_populates="positions",
    )
    holding = relationship(
        "src.infrastructure.models.finance.holding.holding.HoldingModel",
        foreign_keys=[holding_id],
        uselist=False,
    )
