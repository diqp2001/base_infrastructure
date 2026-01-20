"""
Mapper for Exchange domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.exchange import Exchange as DomainExchange
from src.infrastructure.models.finance.exchange import ExchangeModel as ORMExchange


class ExchangeMapper:
    """Mapper for Exchange domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMExchange) -> DomainExchange:
        """Convert ORM model to domain entity."""
        return DomainExchange(
            id=orm_obj.id,
            name=orm_obj.name,
            legal_name=orm_obj.legal_name,
            country_id=orm_obj.country_id,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )

    @staticmethod
    def to_orm(domain_obj: DomainExchange, orm_obj: Optional[ORMExchange] = None) -> ORMExchange:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMExchange(
                name=domain_obj.name,
                legal_name=domain_obj.legal_name,
                country_id=domain_obj.country_id,
                start_date=domain_obj.start_date,
                end_date=domain_obj.end_date
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.legal_name = domain_obj.legal_name
        orm_obj.country_id = domain_obj.country_id
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        return orm_obj