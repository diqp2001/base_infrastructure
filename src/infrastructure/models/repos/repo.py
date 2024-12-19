from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base

class Repo(Base):
    __tablename__ = 'repo'

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Integer, nullable=False)
    

    # Relationship with CompanyStock
    key_company_stock = relationship("KeyCompanyStock", back_populates="repo")

    def __repr__(self):
        return f"<Repo(repo_id={self.id}, repo={self.name})>"
