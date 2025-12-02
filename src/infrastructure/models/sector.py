from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
class Sector(Base):
    __tablename__ = 'sectors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(1000))

    
    # Relationships
    industries = relationship("Industry", back_populates="sectors")

    def __init__(self, name, description=None):
        self.name = name
        self.description = description
    
    def __repr__(self):
        return f"<Sector(name={self.name}, description={self.description})>"
