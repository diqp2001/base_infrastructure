"""
ORM model for Continent - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Continent(Base):
    """
    SQLAlchemy ORM model for Continent.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'continents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    
    # Additional continent properties
    abbreviation = Column(String(2), nullable=True, unique=True)  # e.g., 'AS', 'EU', 'NA'
    code = Column(String(3), nullable=True, unique=True)  # ISO continent code if available
    
    # Geographic information
    area_km2 = Column(Integer, nullable=True)  # Area in square kilometers
    population = Column(Integer, nullable=True)  # Estimated population
    
    # Status fields
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships (assuming countries belong to continents)
    countries = relationship("Country", back_populates="continent")

    def __repr__(self):
        return f"<Continent(id={self.id}, name={self.name}, abbreviation={self.abbreviation})>"