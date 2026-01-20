"""
Mapper for ForwardContract domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.forward_contract import ForwardContract as DomainForwardContract
from src.infrastructure.models.finance.financial_assets.derivative.forward_contract import ForwardContractModel as ORMForwardContract


class ForwardContractMapper:
    """Mapper for ForwardContract domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMForwardContract) -> DomainForwardContract:
        """Convert ORM model to domain entity."""
        domain_entity = DomainForwardContract(
            id=orm_obj.id,
            ticker=getattr(orm_obj, 'ticker', None),
            name=getattr(orm_obj, 'name', None),
            symbol=getattr(orm_obj, 'symbol', None),
            isin=getattr(orm_obj, 'isin', None)
        )
        
        # Set additional properties if available
        if hasattr(orm_obj, 'forward_price'):
            domain_entity.set_forward_price(orm_obj.forward_price)
        if hasattr(orm_obj, 'delivery_date'):
            domain_entity.set_delivery_date(orm_obj.delivery_date)
        if hasattr(orm_obj, 'current_price') and orm_obj.current_price:
            domain_entity.set_current_price(orm_obj.current_price)
        if hasattr(orm_obj, 'last_update') and orm_obj.last_update:
            domain_entity.set_last_update(orm_obj.last_update)
        if hasattr(orm_obj, 'is_tradeable') and orm_obj.is_tradeable is not None:
            domain_entity.set_is_tradeable(orm_obj.is_tradeable)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainForwardContract, orm_obj: Optional[ORMForwardContract] = None) -> ORMForwardContract:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMForwardContract()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        
        # Map optional financial asset attributes
        if hasattr(domain_obj, 'ticker'):
            orm_obj.ticker = domain_obj.ticker
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'symbol'):
            orm_obj.symbol = domain_obj.symbol
        if hasattr(domain_obj, 'isin'):
            orm_obj.isin = domain_obj.isin
        if hasattr(domain_obj, 'forward_price'):
            orm_obj.forward_price = domain_obj.forward_price
        if hasattr(domain_obj, 'delivery_date'):
            orm_obj.delivery_date = domain_obj.delivery_date
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