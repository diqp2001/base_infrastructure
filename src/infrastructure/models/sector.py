from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.sector import Sector as DomainSector
class Sector(DomainSector,Base):
    __tablename__ = 'sectors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)  
    
    # Relationships
    industries = relationship("Industry", back_populates="sectors")

    def __init__(self, name, sector_id, description=None):
        self.name = name
        self.sector_id = sector_id
        self.description = description
    
    def __repr__(self):
        return f"<Sector(name={self.name}, sector_id={self.sector_id}, description={self.description})>"
