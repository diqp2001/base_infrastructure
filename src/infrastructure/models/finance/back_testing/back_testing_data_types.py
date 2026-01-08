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


class Bar(Base):
    __tablename__ = 'bars'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    open = Column(DECIMAL(precision=18, scale=8), nullable=False)
    high = Column(DECIMAL(precision=18, scale=8), nullable=False)
    low = Column(DECIMAL(precision=18, scale=8), nullable=False)
    close = Column(DECIMAL(precision=18, scale=8), nullable=False)
    
    def __init__(self, open_price: Decimal, high: Decimal, low: Decimal, close: Decimal):
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close


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
    
    def __init__(self, symbol_id: int, time: datetime, data_type_id: int, open_price: Decimal, 
                 high: Decimal, low: Decimal, close: Decimal, volume: int, period: timedelta = None):
        self.symbol_id = symbol_id
        self.time = time
        self.data_type_id = data_type_id
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.period = period or timedelta(minutes=1)


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
    
    def __init__(self, symbol_id: int, time: datetime, data_type_id: int, bid_id: int = None, 
                 ask_id: int = None, last_bid_size: int = 0, last_ask_size: int = 0, 
                 period: timedelta = None):
        self.symbol_id = symbol_id
        self.time = time
        self.data_type_id = data_type_id
        self.bid_id = bid_id
        self.ask_id = ask_id
        self.last_bid_size = last_bid_size
        self.last_ask_size = last_ask_size
        self.period = period or timedelta(minutes=1)


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
    
    def __init__(self, symbol_id: int, time: datetime, data_type_id: int, tick_type_id: int,
                 quantity: int = 0, exchange: str = "", sale_condition: str = "", 
                 suspicious: bool = False, bid_price: Decimal = None, ask_price: Decimal = None,
                 bid_size: int = 0, ask_size: int = 0, value: Decimal = None):
        self.symbol_id = symbol_id
        self.time = time
        self.data_type_id = data_type_id
        self.tick_type_id = tick_type_id
        self.value = value
        self.quantity = quantity
        self.exchange = exchange
        self.sale_condition = sale_condition
        self.suspicious = suspicious
        self.bid_price = bid_price
        self.ask_price = ask_price
        self.bid_size = bid_size
        self.ask_size = ask_size


class Slice(Base):
    __tablename__ = 'slices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, nullable=False)
    data = Column(JSON, nullable=True)  # Serialized data dictionary
    
    def __init__(self, time: datetime, data: dict = None):
        self.time = time
        self.data = data or {}


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
    
    def __init__(self, symbol_id: int, data_type_id: int, resolution: str, time_zone: str,
                 market: str, fill_forward: bool = True, extended_market_hours: bool = False,
                 is_custom_data: bool = False, data_normalization_mode: str = "Adjusted"):
        self.symbol_id = symbol_id
        self.data_type_id = data_type_id
        self.resolution = resolution
        self.time_zone = time_zone
        self.market = market
        self.fill_forward = fill_forward
        self.extended_market_hours = extended_market_hours
        self.is_custom_data = is_custom_data
        self.data_normalization_mode = data_normalization_mode


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
    
    def __init__(self, symbol_id: int, time: datetime, data_type_id: int, price: Decimal,
                 volume: int = None, bid: Decimal = None, ask: Decimal = None):
        self.symbol_id = symbol_id
        self.time = time
        self.data_type_id = data_type_id
        self.price = price
        self.volume = volume
        self.bid = bid
        self.ask = ask