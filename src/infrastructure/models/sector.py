from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
class SectorModel(Base):
    __tablename__ = 'sectors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(1000))

    
    # Relationships
    industries = relationship("src.infrastructure.models.industry.IndustryModel", back_populates="sectors")

 
    
    def __repr__(self):
        return f"<Sector(name={self.name}, description={self.description})>"
