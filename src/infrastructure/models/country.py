from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base

from src.domain.entities.country import Country as DomainCountry


class Country(Base):
    __tablename__ = 'countries'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    iso_code = Column(String(3), nullable=False, unique=True)  # e.g., 'USA', 'CAN'
    region = Column(String, nullable=True)  # Optional region classification (e.g., 'North America')
    continent_id = Column(Integer, ForeignKey("continents.id"), nullable=True)
    
    # Relationships
    companies = relationship("Company", back_populates="countries")
    exchanges = relationship("Exchange", back_populates="countries")
    continents = relationship("Continent", back_populates="countries")
    currencies = relationship("Currency", back_populates="country")
    def __init__(self, name, iso_code, region=None):
        self.name = name
        self.iso_code = iso_code
        self.region = region
    
    def __repr__(self):
        return f"<Country(name={self.name}, iso_code={self.iso_code}, region={self.region})>"
