"""
Mapper for Order domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.order.order import Order as DomainOrder
from src.infrastructure.models.finance.order.order import OrderModel as ORMOrder


class OrderMapper:
    """Mapper for Order domain entity and ORM model."""

    @property
    def discriminator(self):
        return "order"

    @property
    def model_class(self):
        return ORMOrder

    def get_entity(self):
        return DomainOrder

    def to_domain(self, orm_model: Optional[ORMOrder]) -> Optional[DomainOrder]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
            
        return DomainOrder(
            id=orm_model.id,
            portfolio_id=0,  # TODO: Resolve from holding relationship
            holding_id=orm_model.holding_id,
            order_type=orm_model.order_type,
            side=orm_model.side,
            quantity=orm_model.quantity,
            created_at=orm_model.created_at,
            status=orm_model.status,
            account_id=orm_model.account_id,
            price=orm_model.price,
            stop_price=orm_model.stop_price,
            filled_quantity=orm_model.filled_quantity,
            average_fill_price=orm_model.average_fill_price,
            time_in_force=orm_model.time_in_force,
            external_order_id=orm_model.external_order_id
        )

    def to_orm(self, entity: DomainOrder) -> ORMOrder:
        """Convert domain entity to ORM model."""
        return ORMOrder(
            id=entity.id,
            holding_id=entity.holding_id,
            order_type=entity.order_type,
            side=entity.side,
            quantity=entity.quantity,
            created_at=entity.created_at,
            status=entity.status,
            account_id=entity.account_id,
            price=entity.price,
            stop_price=entity.stop_price,
            filled_quantity=entity.filled_quantity,
            average_fill_price=entity.average_fill_price,
            time_in_force=entity.time_in_force,
            external_order_id=entity.external_order_id
        )