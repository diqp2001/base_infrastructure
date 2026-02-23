"""
Mapper for IndexFuture domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

# from datetime import datetime
# from decimal import Decimal
from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture as DomainIndexFuture
from src.infrastructure.models.finance.financial_assets.derivative.future.index_future import IndexFutureModel as ORMIndexFuture


class IndexFutureMapper:
    """Mapper for IndexFuture domain entity and ORM model."""
    
    @property
    def entity_class(self):
        return DomainIndexFuture
    
    @property
    def model_class(self):
        return ORMIndexFuture
    
    @staticmethod
    def to_domain(orm_obj: ORMIndexFuture) -> Optional[DomainIndexFuture]:
        """Convert ORM IndexFuture model to domain IndexFuture entity."""
        if not orm_obj:
            return None

        # Create the domain entity 
        domain_entity = DomainIndexFuture(
            id=orm_obj.id,
            name=orm_obj.name if hasattr(orm_obj, 'name') else None,
            symbol=orm_obj.symbol,
            currency_id=orm_obj.currency_id if hasattr(orm_obj, 'currency_id') else None,
            exchange_id=orm_obj.exchange_id if hasattr(orm_obj, 'exchange_id') else None,
            underlying_asset_id=orm_obj.underlying_asset_id if hasattr(orm_obj, 'underlying_asset_id') else None,
            start_date=orm_obj.start_date if hasattr(orm_obj, 'start_date') else None,
            end_date=orm_obj.end_date if hasattr(orm_obj, 'end_date') else None,
            contract_size=orm_obj.contract_size if hasattr(orm_obj, 'contract_size') else None,
            underlying_index=orm_obj.underlying if hasattr(orm_obj, 'underlying') else None,
        )

        # Optional market data - removed last_price access to match FutureMapper corrections
        # if orm_obj.last_price is not None:
        #     domain_entity._price = Decimal(str(orm_obj.last_price))

        # if orm_obj.last_update:
        #     domain_entity._last_update = orm_obj.last_update

        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainIndexFuture) -> ORMIndexFuture:
        """Convert domain IndexFuture entity to ORM model."""
        
        orm_obj = ORMIndexFuture()

        # Identification
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.currency_id = domain_obj.currency_id if hasattr(domain_obj, 'currency_id') else None
        orm_obj.exchange_id = domain_obj.exchange_id if hasattr(domain_obj, 'exchange_id') else None
        orm_obj.underlying_asset_id = domain_obj.underlying_asset_id if hasattr(domain_obj, 'underlying_asset_id') else None
        orm_obj.start_date = domain_obj.start_date if hasattr(domain_obj, 'start_date') else None
        orm_obj.end_date = domain_obj.end_date if hasattr(domain_obj, 'end_date') else None
        orm_obj.contract_size = domain_obj.contract_size if hasattr(domain_obj, 'contract_size') else None
        

        return orm_obj

        

    @staticmethod
    def to_infrastructure(domain_obj: DomainIndexFuture) -> ORMIndexFuture:
        """Legacy method name for backward compatibility."""
        return IndexFutureMapper.to_orm(domain_obj)