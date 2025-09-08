"""
Infrastructure models for symbol system.
SQLAlchemy ORM models.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Numeric, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.infrastructure.models import ModelBase as Base


class Symbol(Base):
    """SQLAlchemy model for Symbol domain entity."""
    __tablename__ = 'bt_symbols'
    
    id = Column(String(255), primary_key=True)
    value = Column(String(100), nullable=False, index=True)
    security_type = Column(String(50), nullable=False, index=True)
    market = Column(String(50), nullable=False, index=True)
    
    # Relationships
    symbol_properties = relationship("SymbolProperties", back_populates="symbol", uselist=False)
    securities = relationship("Security", back_populates="symbol")
    orders = relationship("Order", back_populates="symbol")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SymbolProperties(Base):
    """SQLAlchemy model for SymbolProperties domain entity."""
    __tablename__ = 'bt_symbol_properties'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(String(255), nullable=False, index=True, unique=True)
    
    time_zone = Column(String(100), default="America/New_York")
    exchange_hours = Column(JSON)
    lot_size = Column(Integer, default=1)
    tick_size = Column(Numeric(precision=18, scale=8), default=0.01)
    minimum_price_variation = Column(Numeric(precision=18, scale=8), default=0.01)
    contract_multiplier = Column(Integer, default=1)
    minimum_order_size = Column(Integer, default=1)
    maximum_order_size = Column(Integer)
    price_scaling = Column(Numeric(precision=18, scale=8), default=1)
    margin_requirement = Column(Numeric(precision=18, scale=8), default=0.25)
    short_able = Column(Boolean, default=True)
    
    # Relationships
    symbol = relationship("Symbol", back_populates="symbol_properties")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SymbolMapping(Base):
    """SQLAlchemy model for SymbolMapping domain entity."""
    __tablename__ = 'bt_symbol_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_symbol_id = Column(String(255), nullable=False, index=True)
    mapped_symbol_id = Column(String(255), nullable=False, index=True)
    data_provider = Column(String(100), nullable=False)
    mapping_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))