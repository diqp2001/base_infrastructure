"""
Common module for QuantConnect-style backtesting framework.
Contains core interfaces, data types, shared classes, and utilities.
"""

from .interfaces import IAlgorithm, IDataReader  # Added IDataReader
from .data_types import (
    BaseData, TradeBar, QuoteBar, Tick, Slice, TradeBars, QuoteBars, Ticks,
    SubscriptionDataConfig, Bar  # Added SubscriptionDataConfig and Bar
)
from .symbol import Symbol, SymbolProperties
from .enums import (
    Resolution, SecurityType, OrderType, OrderDirection, OrderStatus,
    MarketDataType, TickType, Market, DataType  # Added DataType
)
from .securities import Security, Securities, SecurityHolding, Portfolio
from .orders import Order, OrderTicket, OrderEvent, OrderFill
from .time_utils import Time  # Time class with utility methods
from .time_orders import TimeOrder  # Time class with utility methods

__all__ = [
    # Interfaces
    'IAlgorithm', 'IDataReader',
    
    # Data types
    'BaseData', 'TradeBar', 'QuoteBar', 'Tick', 'Slice',
    'TradeBars', 'QuoteBars', 'Ticks',
    'SubscriptionDataConfig', 'Bar',
    
    # Symbol system
    'Symbol', 'SymbolProperties',
    
    # Enums
    'Resolution', 'SecurityType', 'OrderType', 'OrderDirection', 'OrderStatus',
    'MarketDataType', 'TickType', 'Market', 'DataType',
    
    # Securities
    'Security', 'Securities', 'SecurityHolding', 'Portfolio',

    # Time Utils
    'Time',
    # Time Orders
    'TimeOrder',

    # Orders
    'Order', 'OrderTicket', 'OrderEvent', 'OrderFill'
]
