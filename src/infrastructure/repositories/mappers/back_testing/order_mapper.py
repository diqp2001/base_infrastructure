"""
Mappers for order domain entities.
Handles bidirectional conversion between domain entities and ORM models.
"""
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from src.domain.entities.back_testing.orders import (
    Order as DomainOrderBase, MarketOrder, LimitOrder, StopMarketOrder, 
    StopLimitOrder, MarketOnOpenOrder, MarketOnCloseOrder,
    OrderFill as DomainOrderFill, OrderEvent as DomainOrderEvent
)
from src.domain.entities.back_testing.enums import OrderType, OrderStatus, OrderDirection
from src.domain.entities.back_testing.symbol import Symbol as DomainSymbol
from src.infrastructure.models.back_testing.order_model import (
    Order as ORMOrder, OrderFill as ORMOrderFill, OrderEvent as ORMOrderEvent
)


class OrderMapper:
    """Mapper for Order domain entities ↔ ORM model conversion."""
    
    @staticmethod
    def to_domain(orm_order: ORMOrder, symbol: DomainSymbol) -> DomainOrderBase:
        """Convert ORM Order to domain Order (returns appropriate subclass)."""
        try:
            order_type = OrderType(orm_order.order_type)
            direction = OrderDirection(orm_order.direction)
            
            # Create appropriate order subclass
            if order_type == OrderType.MARKET:
                order = MarketOrder(symbol, orm_order.quantity, direction, orm_order.tag, orm_order.time)
            elif order_type == OrderType.LIMIT:
                limit_price = Decimal(str(orm_order.limit_price)) if orm_order.limit_price else Decimal('0')
                order = LimitOrder(symbol, orm_order.quantity, direction, limit_price, orm_order.tag, orm_order.time)
            elif order_type == OrderType.STOP_MARKET:
                stop_price = Decimal(str(orm_order.stop_price)) if orm_order.stop_price else Decimal('0')
                order = StopMarketOrder(symbol, orm_order.quantity, direction, stop_price, orm_order.tag, orm_order.time)
            elif order_type == OrderType.STOP_LIMIT:
                stop_price = Decimal(str(orm_order.stop_price)) if orm_order.stop_price else Decimal('0')
                limit_price = Decimal(str(orm_order.limit_price)) if orm_order.limit_price else Decimal('0')
                order = StopLimitOrder(symbol, orm_order.quantity, direction, stop_price, limit_price, orm_order.tag, orm_order.time)
            elif order_type == OrderType.MARKET_ON_OPEN:
                order = MarketOnOpenOrder(symbol, orm_order.quantity, direction, orm_order.tag, orm_order.time)
            elif order_type == OrderType.MARKET_ON_CLOSE:
                order = MarketOnCloseOrder(symbol, orm_order.quantity, direction, orm_order.tag, orm_order.time)
            else:
                # Default to market order for unknown types
                order = MarketOrder(symbol, orm_order.quantity, direction, orm_order.tag, orm_order.time)
            
            # Set order ID and status
            order.id = orm_order.id
            order.status = OrderStatus(orm_order.status) if orm_order.status else OrderStatus.NEW
            order.filled_quantity = orm_order.filled_quantity or 0
            order.remaining_quantity = orm_order.remaining_quantity or orm_order.quantity
            order.commission = Decimal(str(orm_order.commission)) if orm_order.commission else Decimal('0')
            order.fees = Decimal(str(orm_order.fees)) if orm_order.fees else Decimal('0')
            
            # Handle stop trigger state for stop orders
            if hasattr(order, 'stop_triggered'):
                order.stop_triggered = orm_order.stop_triggered or False
            
            return order
            
        except (ValueError, TypeError) as e:
            # Handle invalid enum values gracefully - create basic market order
            order = MarketOrder(symbol, orm_order.quantity or 1, OrderDirection.BUY, orm_order.tag or "", orm_order.time or datetime.now())
            order.id = orm_order.id
            return order
    
    @staticmethod
    def to_orm(domain_order: DomainOrderBase) -> ORMOrder:
        """Convert domain Order to ORM Order."""
        orm_order = ORMOrder(
            id=domain_order.id,
            symbol_id=domain_order.symbol.id,
            quantity=domain_order.quantity,
            direction=domain_order.direction.value,
            order_type=domain_order.order_type.value,
            status=domain_order.status.value,
            tag=domain_order.tag,
            time=domain_order.time,
            filled_quantity=domain_order.filled_quantity,
            remaining_quantity=domain_order.remaining_quantity,
            commission=float(domain_order.commission),
            fees=float(domain_order.fees)
        )
        
        # Set order-type specific fields
        if hasattr(domain_order, 'limit_price'):
            orm_order.limit_price = float(domain_order.limit_price)
        if hasattr(domain_order, 'stop_price'):
            orm_order.stop_price = float(domain_order.stop_price)
        if hasattr(domain_order, 'stop_triggered'):
            orm_order.stop_triggered = domain_order.stop_triggered
        
        return orm_order
    
    @staticmethod
    def update_orm(orm_order: ORMOrder, domain_order: DomainOrderBase) -> ORMOrder:
        """Update ORM Order with domain Order data."""
        orm_order.quantity = domain_order.quantity
        orm_order.direction = domain_order.direction.value
        orm_order.status = domain_order.status.value
        orm_order.tag = domain_order.tag
        orm_order.filled_quantity = domain_order.filled_quantity
        orm_order.remaining_quantity = domain_order.remaining_quantity
        orm_order.commission = float(domain_order.commission)
        orm_order.fees = float(domain_order.fees)
        
        # Update order-type specific fields
        if hasattr(domain_order, 'limit_price'):
            orm_order.limit_price = float(domain_order.limit_price)
        if hasattr(domain_order, 'stop_price'):
            orm_order.stop_price = float(domain_order.stop_price)
        if hasattr(domain_order, 'stop_triggered'):
            orm_order.stop_triggered = domain_order.stop_triggered
        
        return orm_order


class OrderFillMapper:
    """Mapper for OrderFill domain entity ↔ ORM model conversion."""
    
    @staticmethod
    def to_domain(orm_fill: ORMOrderFill) -> DomainOrderFill:
        """Convert ORM OrderFill to domain OrderFill."""
        return DomainOrderFill(
            fill_id=orm_fill.id,
            order_id=orm_fill.order_id,
            fill_time=orm_fill.fill_time,
            fill_price=Decimal(str(orm_fill.fill_price)) if orm_fill.fill_price else Decimal('0'),
            fill_quantity=orm_fill.fill_quantity or 0,
            commission=Decimal(str(orm_fill.commission)) if orm_fill.commission else Decimal('0'),
            fees=Decimal(str(orm_fill.fees)) if orm_fill.fees else Decimal('0')
        )
    
    @staticmethod
    def to_orm(domain_fill: DomainOrderFill) -> ORMOrderFill:
        """Convert domain OrderFill to ORM OrderFill."""
        return ORMOrderFill(
            id=domain_fill.fill_id,
            order_id=domain_fill.order_id,
            fill_time=domain_fill.fill_time,
            fill_price=float(domain_fill.fill_price),
            fill_quantity=domain_fill.fill_quantity,
            commission=float(domain_fill.commission),
            fees=float(domain_fill.fees)
        )


class OrderEventMapper:
    """Mapper for OrderEvent domain entity ↔ ORM model conversion."""
    
    @staticmethod
    def to_domain(orm_event: ORMOrderEvent) -> DomainOrderEvent:
        """Convert ORM OrderEvent to domain OrderEvent."""
        try:
            status = OrderStatus(orm_event.status) if orm_event.status else OrderStatus.NEW
        except ValueError:
            status = OrderStatus.NEW
        
        return DomainOrderEvent(
            event_id=orm_event.id,
            order_id=orm_event.order_id,
            status=status,
            quantity=orm_event.quantity or 0,
            fill_price=Decimal(str(orm_event.fill_price)) if orm_event.fill_price else None,
            message=orm_event.message or "",
            timestamp=orm_event.timestamp
        )
    
    @staticmethod
    def to_orm(domain_event: DomainOrderEvent) -> ORMOrderEvent:
        """Convert domain OrderEvent to ORM OrderEvent."""
        return ORMOrderEvent(
            id=domain_event.event_id,
            order_id=domain_event.order_id,
            status=domain_event.status.value,
            quantity=domain_event.quantity,
            fill_price=float(domain_event.fill_price) if domain_event.fill_price else None,
            message=domain_event.message,
            timestamp=domain_event.timestamp
        )