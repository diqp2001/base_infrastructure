"""
Mapper for SecurityHolding domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from src.domain.entities.finance.holding.security_holding import SecurityHolding as DomainSecurityHolding
from src.infrastructure.models.finance.holding.security_holding import SecurityHoldingModel as ORMSecurityHolding


class SecurityHoldingMapper:
    """Mapper for SecurityHolding domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMSecurityHolding) -> DomainSecurityHolding:
        """Convert ORM model to domain entity."""
        domain_entity = DomainSecurityHolding(
            id=orm_obj.id,
            portfolio_id=orm_obj.portfolio_id,
            symbol_ticker=orm_obj.symbol_ticker,
            symbol_exchange=orm_obj.symbol_exchange,
            security_type=orm_obj.security_type,
            quantity=Decimal(str(orm_obj.quantity)) if orm_obj.quantity else Decimal('0'),
            average_cost=Decimal(str(orm_obj.average_cost)) if orm_obj.average_cost else Decimal('0'),
            market_value=Decimal(str(orm_obj.market_value)) if orm_obj.market_value else Decimal('0'),
            unrealized_pnl=Decimal(str(orm_obj.unrealized_pnl)) if orm_obj.unrealized_pnl else Decimal('0'),
            realized_pnl=Decimal(str(orm_obj.realized_pnl)) if orm_obj.realized_pnl else Decimal('0')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainSecurityHolding, orm_obj: Optional[ORMSecurityHolding] = None) -> ORMSecurityHolding:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMSecurityHolding()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.portfolio_id = domain_obj.portfolio_id
        orm_obj.symbol_ticker = domain_obj.symbol_ticker
        orm_obj.symbol_exchange = domain_obj.symbol_exchange
        orm_obj.security_type = domain_obj.security_type
        orm_obj.quantity = float(domain_obj.quantity) if domain_obj.quantity else 0.0
        orm_obj.average_cost = float(domain_obj.average_cost) if domain_obj.average_cost else 0.0
        orm_obj.market_value = float(domain_obj.market_value) if domain_obj.market_value else 0.0
        orm_obj.unrealized_pnl = float(domain_obj.unrealized_pnl) if domain_obj.unrealized_pnl else 0.0
        orm_obj.realized_pnl = float(domain_obj.realized_pnl) if domain_obj.realized_pnl else 0.0
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj