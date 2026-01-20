"""
Mapper for Bar domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from decimal import Decimal

from src.domain.entities.finance.back_testing.bar import Bar as DomainBar
from src.infrastructure.models.finance.back_testing.back_testing_data_types import BarModel as ORMBar


class BarMapper:
    """Mapper for Bar domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMBar) -> DomainBar:
        """Convert ORM model to domain entity."""
        domain_entity = DomainBar(
            id=orm_obj.id,
            open=Decimal(str(orm_obj.open)) if orm_obj.open else Decimal('0'),
            high=Decimal(str(orm_obj.high)) if orm_obj.high else Decimal('0'),
            low=Decimal(str(orm_obj.low)) if orm_obj.low else Decimal('0'),
            close=Decimal(str(orm_obj.close)) if orm_obj.close else Decimal('0')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainBar, orm_obj: Optional[ORMBar] = None) -> ORMBar:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMBar(
                open_price=domain_obj.open,
                high=domain_obj.high,
                low=domain_obj.low,
                close=domain_obj.close
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.open = domain_obj.open
        orm_obj.high = domain_obj.high
        orm_obj.low = domain_obj.low
        orm_obj.close = domain_obj.close
        
        return orm_obj