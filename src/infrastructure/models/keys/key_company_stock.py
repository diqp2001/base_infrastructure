from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base

class KeyCompanyStock(Base):
    __tablename__ = 'key_company_stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_stock_id = Column(Integer, ForeignKey('company_stocks.id'), nullable=False)
    key_id = Column(String, nullable=False)  # e.g., 'AFL_sedol', 'AFL_gvkey'
    key_value = Column(String, nullable=False)  # e.g., '989898'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationship with CompanyStock
    company_stock = relationship("CompanyStock", back_populates="key_company_stocks")

    def __repr__(self):
        return f"<KeyCompanyStock(key_id={self.key_id}, key_value={self.key_value})>"
