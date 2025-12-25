from sqlalchemy import Column, ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from src.domain.entities.finance.company import Company as DomainCompany
from src.infrastructure.database.base_factory import Base  # Import Base from the infrastructure layer

class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    legal_name = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)
    industry_id = Column(Integer, ForeignKey('industries.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationships
    countries = relationship("Country", back_populates="companies")
    industries = relationship("Industry", back_populates="companies")
    company_shares = relationship("CompanyShare", back_populates="companies")
    
    def __init__(self, name, legal_name, country_id, industry_id, start_date, end_date=None):
        self.name = name
        self.legal_name = legal_name
        self.country_id = country_id
        self.industry_id = industry_id
        self.start_date = start_date
        self.end_date = end_date or datetime.max  # Default to datetime.max if no end_date is provided
    
    def __repr__(self):
        return f"<Company(name={self.name}, legal_name={self.legal_name}, start_date={self.start_date}, end_date={self.end_date})>"
