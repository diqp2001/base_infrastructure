"""
Mapper for Currency domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with country relationships and historical rates.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from src.domain.entities.finance.financial_assets.currency import Currency as DomainCurrency, CurrencyRate as DomainCurrencyRate
from src.infrastructure.models.finance.financial_assets.currency import Currency as ORMCurrency, CurrencyRate as ORMCurrencyRate


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
        
        # Load historical rates if available
        if hasattr(orm_obj, 'historical_rates') and orm_obj.historical_rates:
            for orm_rate in orm_obj.historical_rates:
                domain_rate = DomainCurrencyRate(
                    rate=orm_rate.rate,
                    timestamp=orm_rate.timestamp,
                    target_currency=orm_rate.target_currency
                )
                domain_entity.historical_rates.append(domain_rate)
        
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
        
        # Map exchange rate data
        if domain_obj.current_rate_to_usd:
            orm_obj.exchange_rate_to_usd = domain_obj.current_rate_to_usd
            orm_obj.last_rate_update = domain_obj.last_rate_update or datetime.now()
        
        # Map currency properties
        orm_obj.is_major_currency = domain_obj.is_major_currency
        orm_obj.decimal_places = domain_obj.decimal_places
        orm_obj.is_active = domain_obj.is_active
        orm_obj.is_tradeable = domain_obj.is_tradeable
        
        return orm_obj

    @staticmethod
    def create_historical_rates_orm(domain_obj: DomainCurrency, currency_id: int) -> List[ORMCurrencyRate]:
        """
        Create ORM models for historical currency rates.
        
        :param domain_obj: Domain currency entity
        :param currency_id: Database ID of the currency
        :return: List of ORM CurrencyRate objects
        """
        orm_rates = []
        
        for domain_rate in domain_obj.historical_rates:
            orm_rate = ORMCurrencyRate(
                currency_id=currency_id,
                rate=domain_rate.rate,
                timestamp=domain_rate.timestamp,
                target_currency=domain_rate.target_currency
            )
            orm_rates.append(orm_rate)
        
        return orm_rates