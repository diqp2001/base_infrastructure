from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base

class KeyCompanyStock(Base):
    __tablename__ = 'key_company_stocks'
    __table_args__ = {'extend_existing': True}


    id = Column(Integer, primary_key=True, nullable=False)
    company_stock_id = Column(Integer, ForeignKey('company_stocks.id'), nullable=False)
    repo_id = Column(Integer,  ForeignKey('repo.id'),nullable=False)
    key_id = Column(Integer, ForeignKey('key.id'), nullable=False)
    key_value = Column(Integer, nullable=False)  # e.g., '989898'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    extend_existing = True

    # Relationship with CompanyStock
    company_stock = relationship("CompanyStock", back_populates="key_company_stocks")
    key = relationship("Key", back_populates="key_company_stocks")
    repo = relationship("Repo", back_populates="key_company_stocks")
    
    def __repr__(self):
        return f"<KeyCompanyStock(key_id={self.key_id}, key_value={self.key_value})>"
