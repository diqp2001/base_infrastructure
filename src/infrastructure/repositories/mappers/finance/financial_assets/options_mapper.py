"""
Mapper for Options domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with get_or_create functionality for related models.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.options import Options as DomainOptions
from src.infrastructure.models.finance.financial_assets.derivative.options import OptionsModel as ORMOptions


class OptionsMapper:
    """Mapper for Options domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMOptions) -> DomainOptions:
        """Convert ORM model to domain entity."""
        domain_entity = DomainOptions(
            id=orm_obj.id,
            ticker=getattr(orm_obj, 'ticker', None),
            name=getattr(orm_obj, 'name', None),
            symbol=getattr(orm_obj, 'symbol', None),
            isin=getattr(orm_obj, 'isin', None),
            option_type=getattr(orm_obj, 'option_type', None)
        )
        
        # Set additional properties if available
        if hasattr(orm_obj, 'current_price') and orm_obj.current_price:
            domain_entity.set_current_price(orm_obj.current_price)
        if hasattr(orm_obj, 'last_update') and orm_obj.last_update:
            domain_entity.set_last_update(orm_obj.last_update)
        if hasattr(orm_obj, 'is_tradeable') and orm_obj.is_tradeable is not None:
            domain_entity.set_is_tradeable(orm_obj.is_tradeable)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainOptions, orm_obj: Optional[ORMOptions] = None) -> ORMOptions:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMOptions()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        
        # Map options-specific fields
        if hasattr(domain_obj, 'option_type'):
            orm_obj.option_type = domain_obj.option_type
        
        # Map optional financial asset attributes
        if hasattr(domain_obj, 'ticker'):
            orm_obj.ticker = domain_obj.ticker
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'symbol'):
            orm_obj.symbol = domain_obj.symbol
        if hasattr(domain_obj, 'isin'):
            orm_obj.isin = domain_obj.isin
        if hasattr(domain_obj, 'current_price'):
            orm_obj.current_price = domain_obj.current_price
        if hasattr(domain_obj, 'last_update'):
            orm_obj.last_update = domain_obj.last_update
        if hasattr(domain_obj, 'is_tradeable'):
            orm_obj.is_tradeable = domain_obj.is_tradeable
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj
    
    @staticmethod
    def to_orm_with_dependencies(domain_obj: DomainOptions, session, orm_obj: Optional[ORMOptions] = None) -> ORMOptions:
        """
        Convert domain entity to ORM model with get_or_create for dependencies.
        
        Args:
            domain_obj: Domain options entity
            session: SQLAlchemy session for database operations
            orm_obj: Optional existing ORM object to update
            
        Returns:
            ORMOptions: ORM model with resolved dependencies
        """
        if orm_obj is None:
            orm_obj = ORMOptions()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        
        # Map options-specific fields
        if hasattr(domain_obj, 'option_type'):
            orm_obj.option_type = domain_obj.option_type
        
        # Get or create currency dependency if currency_id is specified
        if hasattr(domain_obj, 'currency_id') and domain_obj.currency_id:
            from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
            currency_repo = CurrencyRepository(session)
            
            # Try to get existing currency
            currency = currency_repo.get_by_id(domain_obj.currency_id)
            if not currency:
                # If currency doesn't exist, we have a problem - options need a valid currency
                # For now, create a default USD currency
                from src.domain.entities.finance.financial_assets.currency import Currency as DomainCurrency
                default_currency = DomainCurrency(
                    name="US Dollar",
                    iso_code="USD",
                    country_id=1,  # Assume US country exists
                    is_major_currency=True,
                    decimal_places=2,
                    is_active=True,
                    is_tradeable=True
                )
                currency = currency_repo.add(default_currency)
                
            # Set currency_id in ORM object (financial assets inherit from base)
            if hasattr(orm_obj, 'currency_id'):
                orm_obj.currency_id = currency.asset_id if currency else None
        
        # Map optional financial asset attributes
        if hasattr(domain_obj, 'ticker'):
            orm_obj.ticker = domain_obj.ticker
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'symbol'):
            orm_obj.symbol = domain_obj.symbol
        if hasattr(domain_obj, 'isin'):
            orm_obj.isin = domain_obj.isin
        if hasattr(domain_obj, 'current_price'):
            orm_obj.current_price = domain_obj.current_price
        if hasattr(domain_obj, 'last_update'):
            orm_obj.last_update = domain_obj.last_update
        if hasattr(domain_obj, 'is_tradeable'):
            orm_obj.is_tradeable = domain_obj.is_tradeable
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj