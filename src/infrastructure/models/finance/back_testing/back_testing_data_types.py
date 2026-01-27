"""
Infrastructure models for back testing data types.
SQLAlchemy models for domain back testing data entities.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Interval
from sqlalchemy.dialects.postgresql import DECIMAL
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class BarModel(Base):
    __tablename__ = 'bars'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    open = Column(DECIMAL(precision=18, scale=8), nullable=False)
    high = Column(DECIMAL(precision=18, scale=8), nullable=False)
    low = Column(DECIMAL(precision=18, scale=8), nullable=False)
    close = Column(DECIMAL(precision=18, scale=8), nullable=False)
    
    


class TradeBar(Base):
    __tablename__ = 'trade_bars'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    time = Column(DateTime, nullable=False)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    open = Column(DECIMAL(precision=18, scale=8), nullable=False)
    high = Column(DECIMAL(precision=18, scale=8), nullable=False)
    low = Column(DECIMAL(precision=18, scale=8), nullable=False)
    close = Column(DECIMAL(precision=18, scale=8), nullable=False)
    volume = Column(Integer, nullable=False)
    period = Column(Interval, nullable=True)
    
    # Relationships
    symbol = relationship("Symbol")
    data_type = relationship("DataTypeModel")
    
    
class QuoteBar(Base):
    __tablename__ = 'quote_bars'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    time = Column(DateTime, nullable=False)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    bid_id = Column(Integer, ForeignKey("bars.id"), nullable=True)
    ask_id = Column(Integer, ForeignKey("bars.id"), nullable=True)
    last_bid_size = Column(Integer, default=0)
    last_ask_size = Column(Integer, default=0)
    period = Column(Interval, nullable=True)
    
    # Relationships
    symbol = relationship("Symbol")
    data_type = relationship("DataTypeModel")
    bid = relationship("Bar", foreign_keys=[bid_id])
    ask = relationship("Bar", foreign_keys=[ask_id])
    
    

class Tick(Base):
    __tablename__ = 'ticks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    time = Column(DateTime, nullable=False)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    tick_type_id = Column(Integer, ForeignKey("tick_types.id"), nullable=False)
    value = Column(DECIMAL(precision=18, scale=8), nullable=True)
    quantity = Column(Integer, default=0)
    exchange = Column(String(100), nullable=True)
    sale_condition = Column(String(100), nullable=True)
    suspicious = Column(Boolean, default=False)
    bid_price = Column(DECIMAL(precision=18, scale=8), nullable=True)
    ask_price = Column(DECIMAL(precision=18, scale=8), nullable=True)
    bid_size = Column(Integer, default=0)
    ask_size = Column(Integer, default=0)
    
    # Relationships
    symbol = relationship("Symbol")
    data_type = relationship("DataTypeModel")
    tick_type = relationship("TickTypeModel")
    
    

class Slice(Base):
    __tablename__ = 'slices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, nullable=False)
    data = Column(JSON, nullable=True)  # Serialized data dictionary
    
   


class SubscriptionDataConfig(Base):
    __tablename__ = 'subscription_data_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    resolution = Column(String(50), nullable=False)
    time_zone = Column(String(100), nullable=False)
    market = Column(String(100), nullable=False)
    fill_forward = Column(Boolean, default=True)
    extended_market_hours = Column(Boolean, default=False)
    is_custom_data = Column(Boolean, default=False)
    data_normalization_mode = Column(String(50), default="Adjusted")
    
    # Relationships
    symbol = relationship("Symbol")
    data_type = relationship("DataTypeModel")
    
    

class MarketDataPoint(Base):
    __tablename__ = 'market_data_points'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    time = Column(DateTime, nullable=False)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    price = Column(DECIMAL(precision=18, scale=8), nullable=False)
    volume = Column(Integer, nullable=True)
    bid = Column(DECIMAL(precision=18, scale=8), nullable=True)
    ask = Column(DECIMAL(precision=18, scale=8), nullable=True)
    
    # Relationships
    symbol = relationship("Symbol")
    data_type = relationship("DataTypeModel")
    
    