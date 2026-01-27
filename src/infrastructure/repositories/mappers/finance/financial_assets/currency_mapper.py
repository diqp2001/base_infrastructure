"""
Mapper for Currency domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with country relationships, historical rates, and factor integration.
Enhanced with get_or_create functionality for related models.
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.currency import Currency as DomainCurrency
from src.infrastructure.models.finance.financial_assets.currency import CurrencyModel as ORMCurrency
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository


class CurrencyMapper:
    """Mapper for Currency domain entity and ORM model."""
    @property
    def entity_class(self):
        """Return the domain entity class for Currency."""
        return DomainCurrency
    @property
    def model_class(self):
        """Return the domain entity class for Currency."""
        return ORMCurrency
    @staticmethod
    def to_domain(orm_obj: ORMCurrency) -> DomainCurrency:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCurrency(
            id=orm_obj.id,
            name=orm_obj.name,
            symbol=orm_obj.symbol,
            country_id=orm_obj.country_id
        )
        
        
        
        
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCurrency, orm_obj: Optional[ORMCurrency] = None) -> ORMCurrency:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCurrency()
        
        # Map basic fields
        orm_obj.name = domain_obj.name
        orm_obj.symbol = domain_obj.symbol
        orm_obj.country_id = domain_obj.country_id
        
        
        
        
        return orm_obj
    

    

    

    