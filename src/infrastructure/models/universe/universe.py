"""
src/infrastructure/models/universe/universe.py

SQLAlchemy ORM model for Universe.
Table: investment_universes  (separate from backtests.universes)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from src.infrastructure.models import ModelBase as Base


class UniverseModel(Base):
    __tablename__ = "investment_universes"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    entity_type = Column(String(100), nullable=True)
    currency_id = Column(Integer, nullable=True)
    created_at  = Column(DateTime, nullable=True)
    updated_at  = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<UniverseModel(id={self.id}, name={self.name})>"
