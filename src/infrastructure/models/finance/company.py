from sqlalchemy import Column, ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from src.domain.entities.finance.company import Company as DomainCompany
from infrastructure.database.base_factory import Base  # Import Base from the infrastructure layer

class Company(DomainCompany, Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    legal_name = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)
    industry_id = Column(Integer, ForeignKey('industries.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationships to the Country and Industry tables
    country = relationship("Country", back_populates="companies")
    industry = relationship("Industry", back_populates="companies")
    
    def __init__(self, name, legal_name, country_id, industry_id, start_date, end_date=None):
        self.name = name
        self.legal_name = legal_name
        self.country_id = country_id
        self.industry_id = industry_id
        self.start_date = start_date
        self.end_date = end_date or datetime.max  # Default to datetime.max if no end_date is provided
    
    def __repr__(self):
        return f"<Company(name={self.name}, legal_name={self.legal_name}, start_date={self.start_date}, end_date={self.end_date})>"
