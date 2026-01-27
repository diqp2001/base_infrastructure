"""
Infrastructure model for position.
SQLAlchemy model for domain position entity.
"""
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.holding.position import PositionType

class PositionModel(Base):
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    position_type = Column(SQLEnum(PositionType), nullable=False)

    # # MANY positions → ONE portfolio
    portfolios = relationship(
        "src.infrastructure.models.finance.portfolio.portfolio.PortfolioModel",
        back_populates="positions"
    )

 