"""
Mapper for IndexFutureOption domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption as DomainIndexFutureOption
from src.infrastructure.models.finance.financial_assets.derivative.option.index_future_option import IndexFutureOptionModel as ORMIndexFutureOption


class IndexFutureOptionMapper:
    """Mapper for IndexFutureOption domain entity and ORM model."""
    
    @property
    def discriminator(self):
        return 'index_future_option'
    
    @property
    def entity_class(self):
        return DomainIndexFutureOption
    
    @property
    def model_class(self):
        return ORMIndexFutureOption
    
    
    def to_domain(self,orm_obj: ORMIndexFutureOption) -> Optional[DomainIndexFutureOption]:
        """Convert ORM IndexFutureOption model to domain IndexFutureOption entity."""
        if not orm_obj:
            return None

        # Create the domain entity 
        domain_entity = DomainIndexFutureOption(
            id=orm_obj.id,
            name=orm_obj.name if hasattr(orm_obj, 'name') else None,
            symbol=orm_obj.symbol,
            option_type=orm_obj.option_type if hasattr(orm_obj, 'option_type') else None,
            strike_price=float(orm_obj.strike_price) if orm_obj.strike_price is not None else None,
            multiplier=float(orm_obj.multiplier) if orm_obj.multiplier is not None else 1.0,
            index_symbol=orm_obj.index_symbol,
            currency_id=orm_obj.currency_id if hasattr(orm_obj, 'currency_id') else None,
            exchange_id=orm_obj.exchange_id if hasattr(orm_obj, 'exchange_id') else None,
            underlying_asset_id=orm_obj.underlying_asset_id if hasattr(orm_obj, 'underlying_asset_id') else None,
            )

        return domain_entity

    
    def to_orm(self,domain_obj: DomainIndexFutureOption) -> ORMIndexFutureOption:
        """Convert domain IndexFutureOption entity to ORM model."""
        
        orm_obj = ORMIndexFutureOption()

        # Basic identification
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        
        # Option-specific fields
        if hasattr(domain_obj, 'option_type') and domain_obj.option_type:
            # Convert string to enum if needed
            if isinstance(domain_obj.option_type, str):
                orm_obj.option_type = domain_obj.option_type
            
        
        # Index future option specific fields
        orm_obj.strike_price = Decimal(str(domain_obj.strike_price)) if domain_obj.strike_price is not None else None
        orm_obj.multiplier = Decimal(str(domain_obj.multiplier)) if domain_obj.multiplier is not None else Decimal('1.0')
        orm_obj.index_symbol = domain_obj.index_symbol
        
        # Additional fields
        orm_obj.currency_id = domain_obj.currency_id if hasattr(domain_obj, 'currency_id') else None
        orm_obj.exchange_id = domain_obj.exchange_id if hasattr(domain_obj, 'exchange_id') else None
        orm_obj.underlying_asset_id = domain_obj.underlying_asset_id if hasattr(domain_obj, 'underlying_asset_id') else None
        
        return orm_obj

    @staticmethod
    def to_infrastructure(domain_obj: DomainIndexFutureOption) -> ORMIndexFutureOption:
        """Legacy method name for backward compatibility."""
        return IndexFutureOptionMapper.to_orm(domain_obj)