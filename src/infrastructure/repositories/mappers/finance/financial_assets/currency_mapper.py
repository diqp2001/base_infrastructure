"""
Mapper for Currency domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with country relationships, historical rates, and factor integration.
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.currency import Currency as DomainCurrency
from src.infrastructure.models.finance.financial_assets.currency import Currency as ORMCurrency
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository


class CurrencyMapper:
    """Mapper for Currency domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCurrency) -> DomainCurrency:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCurrency(
            asset_id=orm_obj.id,
            name=orm_obj.name,
            iso_code=orm_obj.iso_code,
            country_id=orm_obj.country_id
        )
        
        # Set exchange rate data
        if orm_obj.exchange_rate_to_usd:
            domain_entity.current_rate_to_usd = orm_obj.exchange_rate_to_usd
            domain_entity.last_rate_update = orm_obj.last_rate_update
        
        # Set currency properties
        domain_entity.is_major_currency = orm_obj.is_major_currency
        domain_entity.decimal_places = orm_obj.decimal_places
        domain_entity.is_active = orm_obj.is_active
        domain_entity.is_tradeable = orm_obj.is_tradeable
        
        
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCurrency, orm_obj: Optional[ORMCurrency] = None) -> ORMCurrency:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCurrency()
        
        # Map basic fields
        orm_obj.name = domain_obj.name
        orm_obj.iso_code = domain_obj.iso_code
        orm_obj.country_id = domain_obj.country_id
        
        
        
        # Map currency properties
        orm_obj.is_major_currency = domain_obj.is_major_currency
        orm_obj.decimal_places = domain_obj.decimal_places
        orm_obj.is_active = domain_obj.is_active
        orm_obj.is_tradeable = domain_obj.is_tradeable
        
        return orm_obj

    

    

    