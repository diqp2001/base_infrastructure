"""
Infrastructure models for order system.
SQLAlchemy ORM models.
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.infrastructure.models import ModelBase as Base


class Order(Base):
    """SQLAlchemy model for Order domain entity."""
    __tablename__ = 'bt_orders'
    
    id = Column(String(255), primary_key=True)  # UUID
    symbol_id = Column(String(255), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    direction = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    order_type = Column(String(20), nullable=False)  # MARKET, LIMIT, etc.
    status = Column(String(20), nullable=False, index=True)  # NEW, FILLED, etc.
    tag = Column(String(255), default="")
    
    # Order type specific fields
    limit_price = Column(Numeric(precision=18, scale=8))
    stop_price = Column(Numeric(precision=18, scale=8))
    stop_triggered = Column(Boolean, default=False)
    
    # Fill tracking
    filled_quantity = Column(Integer, default=0)
    remaining_quantity = Column(Integer)
    commission = Column(Numeric(precision=18, scale=8), default=0)
    fees = Column(Numeric(precision=18, scale=8), default=0)
    
    # Timestamps
    time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    symbol = relationship("Symbol", back_populates="orders")
    fills = relationship("OrderFill", back_populates="order", cascade="all, delete-orphan")
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")


class OrderFill(Base):
    """SQLAlchemy model for OrderFill domain entity."""
    __tablename__ = 'bt_order_fills'
    
    id = Column(String(255), primary_key=True)  # UUID
    order_id = Column(String(255), ForeignKey('bt_orders.id'), nullable=False, index=True)
    fill_time = Column(DateTime, nullable=False)
    fill_price = Column(Numeric(precision=18, scale=8), nullable=False)
    fill_quantity = Column(Integer, nullable=False)
    commission = Column(Numeric(precision=18, scale=8), default=0)
    fees = Column(Numeric(precision=18, scale=8), default=0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    order = relationship("Order", back_populates="fills")


class OrderEvent(Base):
    """SQLAlchemy model for OrderEvent domain entity."""
    __tablename__ = 'bt_order_events'
    
    id = Column(String(255), primary_key=True)  # UUID
    order_id = Column(String(255), ForeignKey('bt_orders.id'), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    quantity = Column(Integer, default=0)
    fill_price = Column(Numeric(precision=18, scale=8))
    message = Column(Text, default="")
    timestamp = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    order = relationship("Order", back_populates="events")