"""
Mapper for Position domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.holding.position import Position as DomainPosition, PositionType
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
        # portfolio_id is a DB-only FK not present in the domain constructor
        domain_entity.portfolio_id = orm_obj.portfolio_id
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainPosition, orm_obj: Optional[ORMPosition] = None) -> ORMPosition:
        """Convert domain entity to ORM model."""
        # Normalise position_type: accept enum instance or string name
        pt = domain_obj.position_type
        if isinstance(pt, PositionType):
            pt = pt.name  # 'LONG' / 'SHORT' — string avoids SQLEnum .upper() error

        if orm_obj is None:
            orm_obj = ORMPosition(
                quantity=domain_obj.quantity,
                position_type=pt,
            )

        orm_obj.id = domain_obj.id
        orm_obj.portfolio_id = getattr(domain_obj, 'portfolio_id', None)
        orm_obj.quantity = domain_obj.quantity
        orm_obj.position_type = pt

        return orm_obj
