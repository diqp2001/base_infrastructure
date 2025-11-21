from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
class Sector(Base):
    __tablename__ = 'sectors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)  
    
    # Relationships
    industries = relationship("Industry", back_populates="sectors")

    def __init__(self, name, description=None):
        self.name = name
        self.description = description
    
    def __repr__(self):
        return f"<Sector(name={self.name}, description={self.description})>"
