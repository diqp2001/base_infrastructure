from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
class IndustryModel(Base):
    __tablename__ = 'industries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(String(1000), nullable=True)  # Optional description for the industry
    sector_id = Column(Integer, ForeignKey('sectors.id'), nullable=False)  # Foreign key for related Sector
    
    # Relationships
    companies = relationship("src.infrastructure.models.finance.company.CompanyModel", back_populates="industries")
    sectors = relationship("src.infrastructure.models.sector.SectorModel", back_populates="industries")
    
    def __init__(self, name, sector_id, description=None):
        self.name = name
        self.sector_id = sector_id
        self.description = description
    
    def __repr__(self):
        return f"<Industry(name={self.name}, sector_id={self.sector_id}, description={self.description})>"
