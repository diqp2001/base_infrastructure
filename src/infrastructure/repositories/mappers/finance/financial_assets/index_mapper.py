"""
Mapper for Index domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from src.domain.entities.finance.financial_assets.index.index import Index as DomainIndex
from src.infrastructure.models.finance.financial_assets.index import IndexModel as ORMIndex


class IndexMapper:
    """Mapper for Index domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMIndex) -> Optional[DomainIndex]:
        """Convert ORM Index model to domain Index entity."""
        if not orm_obj:
            return None

        domain_entity = DomainIndex(
            id=orm_obj.id,
            symbol=orm_obj.symbol,
            name=orm_obj.name,
            currency_id = orm_obj.currency_id
            
            
        )

        

        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainIndex, orm_obj: Optional[ORMIndex] = None) -> ORMIndex:
        """Convert domain Index entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMIndex()

        # Core identification
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.currency_id = domain_obj.currency_id

        return orm_obj

    @staticmethod
    def to_infrastructure(domain_obj: DomainIndex) -> ORMIndex:
        """Legacy method name for backward compatibility."""
        return IndexMapper.to_orm(domain_obj)
