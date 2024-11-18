from sqlalchemy import Column, ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import relationship
from src.domain.entities.finance.financial_assets.stock import Stock as DomainStock
from src.infrastructure.database.base import Base

class Stock(DomainStock, Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, unique=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="stocks")
    exchange = relationship("Exchange", back_populates="stocks")

    def __init__(self, ticker, company_id,start_date=None,end_date=None):
        self.ticker = ticker
        self.company_id = company_id
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return f"<Stock(ticker={self.ticker}, company_id={self.company_id},  ipo_date={self.ipo_date})>"
