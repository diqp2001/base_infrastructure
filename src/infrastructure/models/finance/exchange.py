from sqlalchemy import Column, ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from src.domain.entities.finance.exchange import Exchange as DomainExchange
from src.infrastructure.database.base import Base  # Import Base from the infrastructure layer

class Exchange(DomainExchange, Base):
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    legal_name = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationships to the Country and Industry tables
    country = relationship("Country", back_populates="exchanges")
    stock = relationship("Stock", back_populates="exchanges")
    
    def __init__(self, name, legal_name, country_id, start_date, end_date=None):
        self.name = name
        self.legal_name = legal_name
        self.country_id = country_id
        self.start_date = start_date
        self.end_date = end_date or datetime.max  # Default to datetime.max if no end_date is provided
    
    def __repr__(self):
        return f"<Company(name={self.name}, legal_name={self.legal_name}, start_date={self.start_date}, end_date={self.end_date})>"
