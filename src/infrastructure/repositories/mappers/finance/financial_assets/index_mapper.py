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
            id=orm_obj.id,
            symbol=orm_obj.symbol,
            name=orm_obj.name,
            currency=orm_obj.currency or "USD",
            description=orm_obj.description,
            base_value=Decimal(str(orm_obj.base_value)) if orm_obj.base_value is not None else None,
            base_date=orm_obj.base_date,
            index_type=orm_obj.index_type or "EQUITY",
            weighting_method=orm_obj.weighting_method or "MARKET_CAP",
            calculation_method=orm_obj.calculation_method or "CAPITALIZATION_WEIGHTED",
            ibkr_contract_id=orm_obj.ibkr_contract_id,
            ibkr_local_symbol=orm_obj.ibkr_local_symbol or "",
            ibkr_exchange=orm_obj.ibkr_exchange or "",
            ibkr_min_tick=Decimal(str(orm_obj.ibkr_min_tick)) if orm_obj.ibkr_min_tick is not None else None
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

        # Core identification
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.currency = domain_obj.currency or "USD"
        orm_obj.description = domain_obj.description

        # Index properties
        orm_obj.index_type = domain_obj.index_type or "EQUITY"
        orm_obj.base_value = domain_obj.base_value
        orm_obj.base_date = domain_obj.base_date or date.today()
        orm_obj.weighting_method = domain_obj.weighting_method or "MARKET_CAP"
        orm_obj.calculation_method = domain_obj.calculation_method or "CAPITALIZATION_WEIGHTED"

        # IBKR-specific fields
        orm_obj.ibkr_contract_id = domain_obj.ibkr_contract_id
        orm_obj.ibkr_local_symbol = domain_obj.ibkr_local_symbol
        orm_obj.ibkr_exchange = domain_obj.ibkr_exchange
        orm_obj.ibkr_min_tick = domain_obj.ibkr_min_tick

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
