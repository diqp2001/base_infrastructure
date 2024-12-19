from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base

class Key(Base):
    __tablename__ = 'key'

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Integer, nullable=False)
    

    # Relationship with CompanyStock
    key_company_stock = relationship("KeyCompanyStock", back_populates="key")

    def __repr__(self):
        return f"<Key(key_id={self.id}, key_value={self.name})>"
