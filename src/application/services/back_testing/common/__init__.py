"""
Common module for QuantConnect-style backtesting framework.
Contains core interfaces, data types, and shared classes.
"""

from .interfaces import IAlgorithm
from .data_types import BaseData, TradeBar, QuoteBar, Tick, Slice, TradeBars, QuoteBars, Ticks
from .symbol import Symbol, SymbolProperties
from .enums import (
    Resolution, SecurityType, OrderType, OrderDirection, OrderStatus,
    MarketDataType, TickType, Market
)
from .securities import Security, Securities, SecurityHolding, Portfolio
from .orders import Order, OrderTicket, OrderEvent, OrderFill

__all__ = [
    # Interfaces
    'IAlgorithm',
    
    # Data types
    'BaseData', 'TradeBar', 'QuoteBar', 'Tick', 'Slice',
    'TradeBars', 'QuoteBars', 'Ticks',
    
    # Symbol system
    'Symbol', 'SymbolProperties',
    
    # Enums
    'Resolution', 'SecurityType', 'OrderType', 'OrderDirection', 'OrderStatus',
    'MarketDataType', 'TickType', 'Market',
    
    # Securities
    'Security', 'Securities', 'SecurityHolding', 'Portfolio',
    
    # Orders
    'Order', 'OrderTicket', 'OrderEvent', 'OrderFill'
]