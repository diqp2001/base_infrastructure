"""
Mapper for Symbol domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.back_testing.symbol import Symbol as DomainSymbol
from src.infrastructure.models.finance.back_testing.financial_assets.symbol import SymbolModel as ORMSymbol


class SymbolMapper:
    """Mapper for Symbol domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMSymbol) -> DomainSymbol:
        """Convert ORM model to domain entity."""
        domain_entity = DomainSymbol(
            id=orm_obj.id,
            value=orm_obj.value,
            symbol_id=orm_obj.symbol_id,
            security_type_id=orm_obj.security_type_id,
            market_id=orm_obj.market_id
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainSymbol, orm_obj: Optional[ORMSymbol] = None) -> ORMSymbol:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMSymbol(
                value=domain_obj.value,
                symbol_id=domain_obj.symbol_id,
                security_type_id=domain_obj.security_type_id,
                market_id=domain_obj.market_id
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.value = domain_obj.value
        orm_obj.symbol_id = domain_obj.symbol_id
        orm_obj.security_type_id = domain_obj.security_type_id
        orm_obj.market_id = domain_obj.market_id
        
        return orm_obj