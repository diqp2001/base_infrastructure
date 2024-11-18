from sqlalchemy import Column, ForeignKey, Integer, Float, Date
from sqlalchemy.orm import relationship
from src.infrastructure.database.base import Base

class StockMarketInformation(Base):
    __tablename__ = 'stock_market_information'

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    date = Column(Date, nullable=False)
    price = Column(Float, nullable=False)
    dividend = Column(Float, nullable=True)
    num_of_shares = Column(Integer, nullable=False)
    floating_shares = Column(Integer, nullable=True)

    # Relationship
    stock = relationship("Stock", back_populates="market_information")

    def __init__(self, stock_id, date, price, dividend=None, num_of_shares=0, floating_shares=None):
        self.stock_id = stock_id
        self.date = date
        self.price = price
        self.dividend = dividend
        self.num_of_shares = num_of_shares
        self.floating_shares = floating_shares
        self.market_cap = self.price * self.num_of_shares

    @property
    def market_cap(self):
        """
        Calculate the market capitalization as price * num_of_shares.
        """
        return self.price * self.num_of_shares

    def __repr__(self):
        return (
            f"<StockMarketInformation(stock_id={self.stock_id}, date={self.date}, "
            f"price={self.price}, dividend={self.dividend}, "
            f"num_of_shares={self.num_of_shares}, floating_shares={self.floating_shares}, "
            f"market_cap={self.market_cap})>"
        )