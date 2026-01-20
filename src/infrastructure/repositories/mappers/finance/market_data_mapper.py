"""
Mapper for MarketData domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from src.domain.entities.finance.market_data import MarketData as DomainMarketData
from src.infrastructure.models.finance.market_data import MarketDataModel as ORMMarketData


class MarketDataMapper:
    """Mapper for MarketData domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMMarketData) -> DomainMarketData:
        """Convert ORM model to domain entity."""
        domain_entity = DomainMarketData(
            id=orm_obj.id,
            symbol_ticker=orm_obj.symbol_ticker,
            symbol_exchange=orm_obj.symbol_exchange,
            security_type=orm_obj.security_type,
            timestamp=orm_obj.timestamp,
            price=Decimal(str(orm_obj.price)) if orm_obj.price else Decimal('0'),
            volume=orm_obj.volume
        )
        
        # Set optional OHLC data
        if hasattr(orm_obj, 'open') and orm_obj.open:
            domain_entity.set_open(Decimal(str(orm_obj.open)))
        if hasattr(orm_obj, 'high') and orm_obj.high:
            domain_entity.set_high(Decimal(str(orm_obj.high)))
        if hasattr(orm_obj, 'low') and orm_obj.low:
            domain_entity.set_low(Decimal(str(orm_obj.low)))
        if hasattr(orm_obj, 'close') and orm_obj.close:
            domain_entity.set_close(Decimal(str(orm_obj.close)))
        
        # Set bid/ask data
        if hasattr(orm_obj, 'bid') and orm_obj.bid:
            domain_entity.set_bid(Decimal(str(orm_obj.bid)))
        if hasattr(orm_obj, 'ask') and orm_obj.ask:
            domain_entity.set_ask(Decimal(str(orm_obj.ask)))
        if hasattr(orm_obj, 'bid_size') and orm_obj.bid_size:
            domain_entity.set_bid_size(orm_obj.bid_size)
        if hasattr(orm_obj, 'ask_size') and orm_obj.ask_size:
            domain_entity.set_ask_size(orm_obj.ask_size)
        
        # Set additional metadata
        if hasattr(orm_obj, 'exchange') and orm_obj.exchange:
            domain_entity.set_exchange(orm_obj.exchange)
        if hasattr(orm_obj, 'last_trade_time') and orm_obj.last_trade_time:
            domain_entity.set_last_trade_time(orm_obj.last_trade_time)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainMarketData, orm_obj: Optional[ORMMarketData] = None) -> ORMMarketData:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMMarketData()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.symbol_ticker = domain_obj.symbol_ticker
        orm_obj.symbol_exchange = domain_obj.symbol_exchange
        orm_obj.security_type = domain_obj.security_type
        orm_obj.timestamp = domain_obj.timestamp
        orm_obj.price = float(domain_obj.price) if domain_obj.price else 0.0
        orm_obj.volume = domain_obj.volume
        
        # Map optional OHLC data
        if hasattr(domain_obj, 'open'):
            orm_obj.open = float(domain_obj.open) if domain_obj.open else None
        if hasattr(domain_obj, 'high'):
            orm_obj.high = float(domain_obj.high) if domain_obj.high else None
        if hasattr(domain_obj, 'low'):
            orm_obj.low = float(domain_obj.low) if domain_obj.low else None
        if hasattr(domain_obj, 'close'):
            orm_obj.close = float(domain_obj.close) if domain_obj.close else None
        
        # Map bid/ask data
        if hasattr(domain_obj, 'bid'):
            orm_obj.bid = float(domain_obj.bid) if domain_obj.bid else None
        if hasattr(domain_obj, 'ask'):
            orm_obj.ask = float(domain_obj.ask) if domain_obj.ask else None
        if hasattr(domain_obj, 'bid_size'):
            orm_obj.bid_size = domain_obj.bid_size
        if hasattr(domain_obj, 'ask_size'):
            orm_obj.ask_size = domain_obj.ask_size
        
        # Map additional metadata
        if hasattr(domain_obj, 'exchange'):
            orm_obj.exchange = domain_obj.exchange
        if hasattr(domain_obj, 'last_trade_time'):
            orm_obj.last_trade_time = domain_obj.last_trade_time
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        
        return orm_obj