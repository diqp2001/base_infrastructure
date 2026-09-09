"""
src/infrastructure/models/universe/universe_constituent.py

SQLAlchemy ORM model for UniverseConstituent.
Table: universe_constituents
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class UniverseConstituentModel(Base):
    __tablename__ = "universe_constituents"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    universe_id = Column(Integer, ForeignKey("investment_universes.id"), nullable=False, index=True)
    entity_id   = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=True)
    weight      = Column(Float, nullable=True)
    created_at  = Column(DateTime, nullable=True)
    updated_at  = Column(DateTime, nullable=True)

    universe = relationship(
        "src.infrastructure.models.universe.universe.UniverseModel",
        foreign_keys=[universe_id],
    )

    def __repr__(self) -> str:
        return (
            f"<UniverseConstituentModel(id={self.id}, universe_id={self.universe_id}, "
            f"entity_id={self.entity_id}, entity_type={self.entity_type})>"
        )
