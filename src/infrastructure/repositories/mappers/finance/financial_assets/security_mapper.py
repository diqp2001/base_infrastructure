"""
Mapper for Security domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
import json

from src.domain.entities.finance.financial_assets.security import Security as DomainSecurity, Symbol, SecurityType
from src.infrastructure.models.finance.financial_assets.security import Security as ORMSecurity


class SecurityMapper:
    """Mapper for Security domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMSecurity) -> DomainSecurity:
        """Convert ORM model to domain entity."""
        # Create symbol object
        symbol = Symbol(
            ticker=orm_obj.ticker,
            exchange=orm_obj.exchange,
            security_type=SecurityType(orm_obj.security_type)
        )
        
        # Create domain entity
        domain_entity = DomainSecurity(symbol)
        
        # Set current price and update timestamp
        if orm_obj.current_price:
            domain_entity._price = Decimal(str(orm_obj.current_price))
        
        if orm_obj.last_update:
            domain_entity._last_update = orm_obj.last_update
        
        # Set holdings if available
        if orm_obj.holdings_quantity is not None:
            from src.domain.entities.finance.financial_assets.security import Holdings
            holdings = Holdings(
                quantity=Decimal(str(orm_obj.holdings_quantity)),
                average_cost=Decimal(str(orm_obj.holdings_average_cost or 0)),
                market_value=Decimal(str(orm_obj.holdings_market_value or 0)),
                unrealized_pnl=Decimal(str(orm_obj.holdings_unrealized_pnl or 0))
            )
            domain_entity._holdings = holdings
        
        # Set trading status
        domain_entity._is_tradeable = orm_obj.is_tradeable
        
        # Load price history from JSON if available
        if orm_obj.price_history:
            try:
                price_data = json.loads(orm_obj.price_history)
                # Convert to MarketData objects
                from src.domain.entities.finance.financial_assets.security import MarketData
                domain_entity._price_history = [
                    MarketData(
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        price=Decimal(str(item['price'])),
                        volume=item.get('volume')
                    )
                    for item in price_data[-100:]  # Keep last 100 entries
                ]
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainSecurity, orm_obj: Optional[ORMSecurity] = None) -> ORMSecurity:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMSecurity()
        
        # Map symbol information
        orm_obj.ticker = domain_obj.symbol.ticker
        orm_obj.exchange = domain_obj.symbol.exchange
        orm_obj.security_type = domain_obj.symbol.security_type.value
        
        # Map pricing
        orm_obj.current_price = domain_obj.price
        orm_obj.last_update = domain_obj.last_update
        
        # Map holdings
        orm_obj.holdings_quantity = domain_obj.holdings.quantity
        orm_obj.holdings_average_cost = domain_obj.holdings.average_cost
        orm_obj.holdings_market_value = domain_obj.holdings.market_value
        orm_obj.holdings_unrealized_pnl = domain_obj.holdings.unrealized_pnl
        
        # Map trading status
        orm_obj.is_tradeable = domain_obj.is_tradeable
        
        # Map contract multiplier
        if hasattr(domain_obj, 'get_contract_multiplier'):
            orm_obj.contract_multiplier = domain_obj.get_contract_multiplier()
        
        # Convert price history to JSON
        if domain_obj._price_history:
            price_history_data = [
                {
                    'timestamp': data.timestamp.isoformat(),
                    'price': str(data.price),
                    'volume': data.volume,
                    'bid': str(data.bid) if data.bid else None,
                    'ask': str(data.ask) if data.ask else None
                }
                for data in domain_obj._price_history[-100:]  # Keep last 100 entries
            ]
            orm_obj.price_history = json.dumps(price_history_data)
        
        # Calculate volatility if we have enough price history
        if hasattr(domain_obj, 'calculate_volatility'):
            try:
                orm_obj.volatility_20d = domain_obj.calculate_volatility(20)
                orm_obj.volatility_30d = domain_obj.calculate_volatility(30)
            except:
                pass
        
        # Set timestamps
        if not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        orm_obj.updated_at = datetime.now()
        
        # Set active status
        if orm_obj.is_active is None:
            orm_obj.is_active = True
        
        return orm_obj