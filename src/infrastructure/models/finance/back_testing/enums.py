"""
Infrastructure models for back testing enums.
SQLAlchemy models for domain enums.
"""
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.back_testing.enums import (
    Resolution, SecurityType, Market, OrderType, OrderStatus, OrderDirection,
    TickType, DataType, OptionRight, OptionStyle, DataNormalizationMode,
    AlgorithmStatus, InsightType, AccountType, Language, ServerType, PacketType
)


class ResolutionModel(Base):
    __tablename__ = 'resolutions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(Resolution), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: Resolution):
        self.value = value
        self.name = value.value


class SecurityTypeModel(Base):
    __tablename__ = 'security_types'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(SecurityType), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: SecurityType):
        self.value = value
        self.name = value.value


class MarketModel(Base):
    __tablename__ = 'markets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(Market), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: Market):
        self.value = value
        self.name = value.value


class OrderTypeModel(Base):
    __tablename__ = 'order_types'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(OrderType), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: OrderType):
        self.value = value
        self.name = value.value


class OrderStatusModel(Base):
    __tablename__ = 'order_statuses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(OrderStatus), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: OrderStatus):
        self.value = value
        self.name = value.value


class OrderDirectionModel(Base):
    __tablename__ = 'order_directions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(OrderDirection), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: OrderDirection):
        self.value = value
        self.name = value.value


class TickTypeModel(Base):
    __tablename__ = 'tick_types'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(TickType), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: TickType):
        self.value = value
        self.name = value.value


class DataTypeModel(Base):
    __tablename__ = 'data_types'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(SQLEnum(DataType), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    
    def __init__(self, value: DataType):
        self.value = value
        self.name = value.value