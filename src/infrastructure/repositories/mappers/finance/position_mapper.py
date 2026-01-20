"""
Mapper for Position domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.holding.position import Position as DomainPosition
from src.infrastructure.models.finance.position import PositionModel as ORMPosition


class PositionMapper:
    """Mapper for Position domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMPosition) -> DomainPosition:
        """Convert ORM model to domain entity."""
        domain_entity = DomainPosition(
            id=orm_obj.id,
            portfolio_id=orm_obj.portfolio_id,
            quantity=orm_obj.quantity,
            position_type=orm_obj.position_type
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainPosition, orm_obj: Optional[ORMPosition] = None) -> ORMPosition:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMPosition(
                quantity=domain_obj.quantity,
                position_type=domain_obj.position_type
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.portfolio_id = domain_obj.portfolio_id
        orm_obj.quantity = domain_obj.quantity
        orm_obj.position_type = domain_obj.position_type
        
        return orm_obj