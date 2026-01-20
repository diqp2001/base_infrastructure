"""
Mappers for all backtesting enum domain entities and ORM models.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.back_testing.enums import (
    Resolution, SecurityType, Market, OrderType, OrderStatus, OrderDirection,
    TickType, DataType
)
from src.infrastructure.models.finance.back_testing.enums import (
    ResolutionModel, SecurityTypeModel, MarketModel, OrderTypeModel, 
    OrderStatusModel, OrderDirectionModel, TickTypeModel, DataTypeModel
)


class ResolutionMapper:
    """Mapper for Resolution domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ResolutionModel) -> Resolution:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: Resolution, orm_obj: Optional[ResolutionModel] = None) -> ResolutionModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ResolutionModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj


class SecurityTypeMapper:
    """Mapper for SecurityType domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: SecurityTypeModel) -> SecurityType:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: SecurityType, orm_obj: Optional[SecurityTypeModel] = None) -> SecurityTypeModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = SecurityTypeModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj


class MarketMapper:
    """Mapper for Market domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: MarketModel) -> Market:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: Market, orm_obj: Optional[MarketModel] = None) -> MarketModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = MarketModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj


class OrderTypeMapper:
    """Mapper for OrderType domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: OrderTypeModel) -> OrderType:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: OrderType, orm_obj: Optional[OrderTypeModel] = None) -> OrderTypeModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = OrderTypeModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj


class OrderStatusMapper:
    """Mapper for OrderStatus domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: OrderStatusModel) -> OrderStatus:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: OrderStatus, orm_obj: Optional[OrderStatusModel] = None) -> OrderStatusModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = OrderStatusModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj


class OrderDirectionMapper:
    """Mapper for OrderDirection domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: OrderDirectionModel) -> OrderDirection:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: OrderDirection, orm_obj: Optional[OrderDirectionModel] = None) -> OrderDirectionModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = OrderDirectionModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj


class TickTypeMapper:
    """Mapper for TickType domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: TickTypeModel) -> TickType:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: TickType, orm_obj: Optional[TickTypeModel] = None) -> TickTypeModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = TickTypeModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj


class DataTypeMapper:
    """Mapper for DataType domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: DataTypeModel) -> DataType:
        """Convert ORM model to domain entity."""
        return orm_obj.value

    @staticmethod
    def to_orm(domain_obj: DataType, orm_obj: Optional[DataTypeModel] = None) -> DataTypeModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = DataTypeModel(value=domain_obj)
        
        orm_obj.value = domain_obj
        orm_obj.name = domain_obj.value
        
        return orm_obj