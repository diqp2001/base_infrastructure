"""
Mapper for Currency domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.currency import Currency as DomainCurrency
from src.infrastructure.models.finance.financial_assets.currency import Currency as ORMCurrency


class CurrencyMapper:
    """Mapper for Currency domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCurrency) -> DomainCurrency:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCurrency(
            asset_id=orm_obj.id,
            name=orm_obj.name,
            iso_code=orm_obj.iso_code
        )
        
        # Set additional properties if they exist in the domain entity
        if hasattr(domain_entity, 'exchange_rate_to_usd') and orm_obj.exchange_rate_to_usd:
            domain_entity.exchange_rate_to_usd = orm_obj.exchange_rate_to_usd
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCurrency, orm_obj: Optional[ORMCurrency] = None) -> ORMCurrency:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCurrency()
        
        # Map basic fields
        orm_obj.name = domain_obj.name
        orm_obj.iso_code = domain_obj.iso_code
        
        # Map additional fields if they exist
        if hasattr(domain_obj, 'exchange_rate_to_usd'):
            orm_obj.exchange_rate_to_usd = domain_obj.exchange_rate_to_usd
        
        # Set defaults for ORM-specific fields
        if not orm_obj.last_rate_update:
            orm_obj.last_rate_update = datetime.now()
        
        # Determine if it's a major currency based on common ISO codes
        major_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD'}
        orm_obj.is_major_currency = orm_obj.iso_code in major_currencies
        
        # Set default decimal places based on currency
        if orm_obj.iso_code in {'JPY', 'KRW', 'VND'}:  # Currencies with no decimal places
            orm_obj.decimal_places = 0
        else:
            orm_obj.decimal_places = 2
        
        return orm_obj