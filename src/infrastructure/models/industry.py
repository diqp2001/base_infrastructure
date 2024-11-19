from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from infrastructure.database.base_factory import Base
from src.domain.entities.industry import Industry as DomainIndustry
class Industry(DomainIndustry,Base):
    __tablename__ = 'industries'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)  # Optional description for the industry
    sector_id = Column(Integer, ForeignKey('sectors.id'), nullable=False)  # Foreign key for related Sector
    
    # Relationship to companies
    companies = relationship("Company", back_populates="industry")
    
    # Relationship to Sector (assuming a Sector model exists)
    sector = relationship("Sector", back_populates="industries")  # Add this only if Sector exists
    
    def __init__(self, name, sector_id, description=None):
        self.name = name
        self.sector_id = sector_id
        self.description = description
    
    def __repr__(self):
        return f"<Industry(name={self.name}, sector_id={self.sector_id}, description={self.description})>"
