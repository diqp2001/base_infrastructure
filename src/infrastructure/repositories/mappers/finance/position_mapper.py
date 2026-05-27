"""
Mapper for Position domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.holding.position import Position as DomainPosition
from src.infrastructure.models.finance.position import PositionModel as ORMPosition


class PositionMapper:
    """Mapper for Position domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMPosition) -> DomainPosition:
        """Convert ORM model to domain entity."""
        domain_entity = DomainPosition(
            id=orm_obj.id,
            quantity=orm_obj.quantity,
            position_type=orm_obj.position_type,
        )
        # Attach DB-only fields as attributes (not in Position.__init__)
        domain_entity.portfolio_id = orm_obj.portfolio_id
        domain_entity.holding_id = getattr(orm_obj, 'holding_id', None)
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainPosition, orm_obj: Optional[ORMPosition] = None) -> ORMPosition:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMPosition(
                quantity=domain_obj.quantity,
                position_type=domain_obj.position_type,
            )

        orm_obj.id = domain_obj.id
        orm_obj.portfolio_id = getattr(domain_obj, 'portfolio_id', None)
        orm_obj.quantity = domain_obj.quantity
        orm_obj.position_type = domain_obj.position_type
        orm_obj.holding_id = getattr(domain_obj, 'holding_id', None)

        return orm_obj
