from sqlalchemy import Column, ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import relationship
from src.domain.entities.finance.financial_assets.stock import Stock as DomainStock
from infrastructure.database.base_factory import Base

class Stock(DomainStock, Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, unique=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    # Relationships
    exchanges = relationship("Exchange", back_populates="stocks")
    
    def __init__(self, ticker,start_date=None,end_date=None):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return f"<Stock(ticker={self.ticker})>"
