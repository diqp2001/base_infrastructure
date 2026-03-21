"""
Mapper for Order domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.order.order import Order as DomainOrder
from src.infrastructure.models.finance.order.order import OrderModel as ORMOrder


class OrderMapper:
    """Mapper for Order domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMOrder) -> DomainOrder:
        """Convert ORM model to domain entity."""
        domain_entity = DomainOrder(
            id=orm_obj.id,
            portfolio_id=orm_obj.portfolio_id,
            holding_id=orm_obj.holding_id,
            order_type=orm_obj.order_type,
            side=orm_obj.side,
            quantity=orm_obj.quantity,
            created_at=orm_obj.created_at,
            status=orm_obj.status,
            account_id=orm_obj.account_id,
            price=orm_obj.price,
            stop_price=orm_obj.stop_price,
            filled_quantity=orm_obj.filled_quantity,
            average_fill_price=orm_obj.average_fill_price,
            time_in_force=orm_obj.time_in_force,
            external_order_id=orm_obj.external_order_id
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainOrder, orm_obj: Optional[ORMOrder] = None) -> ORMOrder:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMOrder(
                portfolio_id=domain_obj.portfolio_id,
                holding_id=domain_obj.holding_id,
                order_type=domain_obj.order_type,
                side=domain_obj.side,
                quantity=domain_obj.quantity,
                created_at=domain_obj.created_at,
                status=domain_obj.status,
                account_id=domain_obj.account_id,
                price=domain_obj.price,
                stop_price=domain_obj.stop_price,
                filled_quantity=domain_obj.filled_quantity,
                average_fill_price=domain_obj.average_fill_price,
                time_in_force=domain_obj.time_in_force,
                external_order_id=domain_obj.external_order_id
            )
        
        # Map basic fields
        if domain_obj.id is not None:
            orm_obj.id = domain_obj.id
        orm_obj.portfolio_id = domain_obj.portfolio_id
        orm_obj.holding_id = domain_obj.holding_id
        orm_obj.order_type = domain_obj.order_type
        orm_obj.side = domain_obj.side
        orm_obj.quantity = domain_obj.quantity
        orm_obj.created_at = domain_obj.created_at
        orm_obj.status = domain_obj.status
        orm_obj.account_id = domain_obj.account_id
        orm_obj.price = domain_obj.price
        orm_obj.stop_price = domain_obj.stop_price
        orm_obj.filled_quantity = domain_obj.filled_quantity
        orm_obj.average_fill_price = domain_obj.average_fill_price
        orm_obj.time_in_force = domain_obj.time_in_force
        orm_obj.external_order_id = domain_obj.external_order_id
        
        return orm_obj