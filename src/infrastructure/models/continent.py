"""
ORM model for Continent - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class ContinentModel(Base):
    """
    SQLAlchemy ORM model for Continent.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'continents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    
    
    # Status fields
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships (assuming countries belong to continents)
    countries = relationship("src.infrastructure.models.country.CountryModel", back_populates="continent")

    def __repr__(self):
        return f"<Continent(id={self.id}, name={self.name}, abbreviation={self.abbreviation})>"