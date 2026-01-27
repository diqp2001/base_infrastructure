"""
Infrastructure models for symbol system.
SQLAlchemy models for domain symbol entities.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import DECIMAL
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.back_testing.enums import SecurityType, Market


class SymbolModel(Base):
    __tablename__ = 'symbols'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(255), nullable=False)
    symbol_id = Column(String(255), nullable=False, unique=True)
    security_type_id = Column(Integer, ForeignKey("security_types.id"), nullable=False)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    
    # Relationships
    security_type = relationship("SecurityTypeModel")
    market = relationship("MarketModel")
    properties = relationship("SymbolProperties", back_populates="symbol", uselist=False)
    mappings = relationship("SymbolMapping", foreign_keys="SymbolMapping.original_symbol_id", back_populates="original_symbol")
    
   
    def __repr__(self):
        return f"<Symbol(value={self.value}, symbol_id={self.symbol_id})>"


class SymbolProperties(Base):
    __tablename__ = 'symbol_properties'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    time_zone = Column(String(100), default="America/New_York")
    exchange_hours = Column(JSON, nullable=True)
    lot_size = Column(Integer, default=1)
    tick_size = Column(DECIMAL(precision=18, scale=8), default=Decimal('0.01'))
    minimum_price_variation = Column(DECIMAL(precision=18, scale=8), default=Decimal('0.01'))
    contract_multiplier = Column(Integer, default=1)
    minimum_order_size = Column(Integer, default=1)
    maximum_order_size = Column(Integer, nullable=True)
    price_scaling = Column(DECIMAL(precision=18, scale=8), default=Decimal('1'))
    margin_requirement = Column(DECIMAL(precision=18, scale=8), default=Decimal('0.25'))
    short_able = Column(Boolean, default=True)
    
    # Relationships
    symbol = relationship("Symbol", back_populates="properties")
    
    

class SymbolMapping(Base):
    __tablename__ = 'symbol_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    mapped_symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    data_provider = Column(String(255), nullable=False)
    mapping_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    original_symbol = relationship("Symbol", foreign_keys=[original_symbol_id])
    mapped_symbol = relationship("Symbol", foreign_keys=[mapped_symbol_id])
    
    


class SymbolSecurityDatabase(Base):
    __tablename__ = 'symbol_security_databases'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    