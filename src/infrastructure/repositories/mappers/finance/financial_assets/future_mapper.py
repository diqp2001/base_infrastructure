"""
Mapper for Future domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.future.future import Future as DomainFuture
from src.infrastructure.models.finance.financial_assets.derivative.future.future import FutureModel as ORMFuture
from src.infrastructure.repositories.mappers.finance.financial_assets.index_mapper import IndexMapper


class FutureMapper:
    """Mapper for Future domain entity and ORM model."""
    @property
    def entity_class(self):
        return DomainFuture
    @property
    def model_class(self):
        return ORMFuture
    @staticmethod
    def to_domain(orm_obj: ORMFuture) -> Optional[DomainFuture]:
        """Convert ORM Future model to domain Future entity."""
        if not orm_obj:
            return None

        

        domain_entity = DomainFuture(
            symbol=orm_obj.symbol,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date,
            contract_size=orm_obj.contract_size,
            
        )

        
        if orm_obj.last_update:
            domain_entity._last_update = orm_obj.last_update

        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainFuture, orm_obj: Optional[ORMFuture] = None) -> ORMFuture:
        """Convert domain Future entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMFuture()

        # Identification
        orm_obj.symbol = domain_obj.symbol
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date

        # Contract specs
        orm_obj.contract_size = domain_obj.contract_size
        

        

        

        return orm_obj

    @staticmethod
    def to_infrastructure(domain_obj: DomainFuture) -> ORMFuture:
        """Legacy method name for backward compatibility."""
        return FutureMapper.to_orm(domain_obj)
