"""
Mapper for Index domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from src.domain.entities.finance.financial_assets.index.index import Index as DomainIndex
from src.infrastructure.models.finance.financial_assets.index import Index as ORMIndex


class IndexMapper:
    """Mapper for Index domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMIndex) -> Optional[DomainIndex]:
        """Convert ORM Index model to domain Index entity."""
        if not orm_obj:
            return None

        domain_entity = DomainIndex(
            symbol=orm_obj.symbol,
            name=orm_obj.name,
            currency=orm_obj.currency,
            base_value=Decimal(str(orm_obj.base_value))
            if orm_obj.base_value is not None
            else None,
            base_date=orm_obj.base_date
        )

        # Optional / derived values (kept out of constructor)
        if orm_obj.current_level is not None:
            domain_entity._level = Decimal(str(orm_obj.current_level))

        if orm_obj.last_update:
            domain_entity._last_update = orm_obj.last_update

        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainIndex, orm_obj: Optional[ORMIndex] = None) -> ORMIndex:
        """Convert domain Index entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMIndex()

        # Identification
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.currency = domain_obj.currency or "USD"

        # Base normalization
        orm_obj.base_value = domain_obj.base_value
        orm_obj.base_date = domain_obj.base_date or date.today()

        # Market data (optional)
        if hasattr(domain_obj, "_level") and domain_obj._level is not None:
            orm_obj.current_level = domain_obj._level

        orm_obj.last_update = datetime.now()
        orm_obj.is_tradeable = False  # Index itself is not tradable

        return orm_obj

    @staticmethod
    def to_infrastructure(domain_obj: DomainIndex) -> ORMIndex:
        """Legacy method name for backward compatibility."""
        return IndexMapper.to_orm(domain_obj)
