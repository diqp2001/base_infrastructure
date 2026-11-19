"""
src/infrastructure/models/universe/universe_factor.py

SQLAlchemy ORM model for UniverseFactor. Table: universe_factors. Membership only (no weight / rank).
"""

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base


class UniverseFactorModel(Base):
    __tablename__ = "universe_factors"
    __table_args__ = (UniqueConstraint("universe_id", "factor_id", name="uq_universe_factor"),)

    id          = Column(Integer, primary_key=True, autoincrement=True)
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False, index=True)
    factor_id   = Column(Integer, ForeignKey("factors.id"), nullable=False, index=True)

    universe = relationship("src.infrastructure.models.universe.universe.UniverseModel", back_populates="factors")

    def __repr__(self) -> str:
        return f"<UniverseFactorModel(id={self.id}, universe_id={self.universe_id}, factor_id={self.factor_id})>"
