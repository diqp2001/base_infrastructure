"""
SQLAlchemy ORM model for PortfolioCompanyShareOption.
Represents options written on portfolio company shares.
"""

from sqlalchemy import (
    Column, Integer, String, Date, Numeric, Boolean, DateTime, ForeignKey, 
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.infrastructure.models.finance.financial_assets.options import OptionType


class PortfolioCompanyShareOptionModel(Base):
    """
    SQLAlchemy ORM model for PortfolioCompanyShareOption.
    Options contracts written on company shares within portfolios.
    """
    __tablename__ = 'portfolio_company_share_options'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Option identification
    symbol = Column(String(50), nullable=False, index=True)
    underlying_symbol = Column(String(20), nullable=False, index=True)
    option_type = Column(SQLEnum(OptionType), nullable=False)
    
    # Portfolio relationship
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    
    # Contract details
    strike_price = Column(Numeric(15, 4), nullable=False)
    expiration_date = Column(Date, nullable=False)
    contract_size = Column(Integer, nullable=False, default=100)
    exercise_style = Column(String(20), nullable=False, default='American')
    
    # Market data
    current_price = Column(Numeric(15, 4), default=0)
    bid_price = Column(Numeric(15, 4), nullable=True)
    ask_price = Column(Numeric(15, 4), nullable=True)
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)
    
    # Greeks
    delta = Column(Numeric(8, 6), nullable=True)
    gamma = Column(Numeric(8, 6), nullable=True)
    theta = Column(Numeric(8, 6), nullable=True)
    vega = Column(Numeric(8, 6), nullable=True)
    rho = Column(Numeric(8, 6), nullable=True)
    
    # Volatility and valuation
    implied_volatility = Column(Numeric(8, 4), nullable=True)
    theoretical_value = Column(Numeric(15, 4), nullable=True)
    intrinsic_value = Column(Numeric(15, 4), nullable=True)
    time_value = Column(Numeric(15, 4), nullable=True)
    
    # Position information
    position_quantity = Column(Numeric(15, 4), nullable=True, default=0)
    average_cost = Column(Numeric(15, 4), nullable=True)
    unrealized_pnl = Column(Numeric(15, 4), nullable=True, default=0)
    realized_pnl = Column(Numeric(15, 4), nullable=True, default=0)
    
    # Status and lifecycle
    is_tradeable = Column(Boolean, default=True)
    is_american = Column(Boolean, default=True)
    days_to_expiration = Column(Integer, nullable=True)
    is_in_the_money = Column(Boolean, nullable=True)
    moneyness = Column(Numeric(8, 4), nullable=True)
    
    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    last_trade_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_update = Column(DateTime, nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="option_holdings")
    
    def __repr__(self):
        return (
            f"<PortfolioCompanyShareOptionModel(id={self.id}, symbol={self.symbol}, "
            f"type={self.option_type}, strike={self.strike_price}, exp={self.expiration_date})>"
        )