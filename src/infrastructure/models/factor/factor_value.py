"""
Infrastructure model for factor value.
SQLAlchemy model for domain factor value entity.
"""
from datetime import date
import math

from sqlalchemy import Column, DateTime, Float, Integer, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from src.infrastructure.models import ModelBase as Base


class FactorValueModel(Base):
    __tablename__ = 'factor_values'
    # One value per (factor, entity, entity type, date): the resolver checks then inserts, so without
    # this two concurrent writers stored two rows. Existing databases get the index from
    # BaseFactory._migrate_schema once duplicates are removed (src/infrastructure/database/factor_value_dedup.py).
    NATURAL_KEY = ("factor_id", "entity_id", "entity_type", "date")
    __table_args__ = (UniqueConstraint(*NATURAL_KEY, name="uq_factor_values_natural_key"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey("factors.id"), nullable=False)
    entity_id = Column(Integer, nullable=False)   # Generic entity reference
    entity_type = Column(String(100), nullable=False, index=True)  # Entity class name discriminator
    date = Column(DateTime(timezone=True), nullable=False)
    value = Column(String(255), nullable=False)
    # Numeric copy of `value` (NULL when it is not a finite number), kept in step on every ORM write; existing rows
    # are backfilled by BaseFactory._migrate_schema. `value` stays the authoritative column for now.
    value_numeric = Column(Float, nullable=True)
    currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=True)
    
    # Relationships
    factors = relationship("src.infrastructure.models.factor.factor.FactorModel",back_populates="factor_values")
    
    

    
    @validates("value")
    def _sync_numeric(self, key, value):
        try:
            number = float(value)
            self.value_numeric = number if math.isfinite(number) else None
        except (TypeError, ValueError):
            self.value_numeric = None
        return value

    def __repr__(self):
        return f"<FactorValue(id={self.id}, factor_id={self.factor_id}, entity_type={self.entity_type}, entity_id={self.entity_id}, date={self.date})>"