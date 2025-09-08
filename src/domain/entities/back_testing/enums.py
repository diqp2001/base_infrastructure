"""
Domain enums for back testing system.
Pure domain entities following DDD principles.
"""
from enum import Enum, auto
from typing import Any


class Resolution(Enum):
    """Represents the resolution of market data."""
    TICK = "tick"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAILY = "daily"


class SecurityType(Enum):
    """Represents different types of securities."""
    BASE = "base"
    EQUITY = "equity"
    OPTION = "option"
    COMMODITY = "commodity"
    FOREX = "forex"
    FUTURE = "future"
    CFD = "cfd"
    CRYPTO = "crypto"
    FUND = "fund"
    INDEX = "index"


class Market(Enum):
    """Represents different markets/exchanges."""
    USA = "usa"
    EUROPE = "europe"
    ASIA = "asia"
    FXCM = "fxcm"
    OANDA = "oanda"
    DUKASCOPY = "dukascopy"
    BITFINEX = "bitfinex"
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    NASDAQ = "nasdaq"
    NYSE = "nyse"
    LSE = "lse"  # London Stock Exchange
    TSE = "tse"  # Tokyo Stock Exchange


class OrderType(Enum):
    """Represents different types of orders."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    MARKET_ON_OPEN = "market_on_open"
    MARKET_ON_CLOSE = "market_on_close"


class OrderStatus(Enum):
    """Represents the status of an order."""
    NEW = "new"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    INVALID = "invalid"
    REJECTED = "rejected"
    NONE = "none"


class OrderDirection(Enum):
    """Represents the direction of an order."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class TickType(Enum):
    """Represents the type of tick data."""
    TRADE = "trade"
    QUOTE = "quote"
    OPEN_INTEREST = "open_interest"


class DataType(Enum):
    """Represents different types of market data."""
    TRADE_BAR = "trade_bar"
    QUOTE_BAR = "quote_bar"
    TICK = "tick"
    OPTION_CHAIN = "option_chain"
    FUTURES_CHAIN = "futures_chain"
    FUNDAMENTAL = "fundamental"
    NEWS = "news"
    SPLIT = "split"
    DIVIDEND = "dividend"


class OptionRight(Enum):
    """Represents the right of an option."""
    CALL = "call"
    PUT = "put"


class OptionStyle(Enum):
    """Represents the exercise style of an option."""
    AMERICAN = "american"
    EUROPEAN = "european"


class DataNormalizationMode(Enum):
    """Represents how market data should be normalized."""
    RAW = "raw"
    ADJUSTED = "adjusted"
    SPLIT_ADJUSTED = "split_adjusted"
    TOTAL_RETURN = "total_return"


class AlgorithmStatus(Enum):
    """Represents the status of a trading algorithm."""
    RUNNING = "running"
    STOPPED = "stopped"
    LIQUIDATED = "liquidated"
    DELETED = "deleted"
    COMPLETED = "completed"
    ERROR = "error"
    HISTORY = "history"
    INITIALIZING = "initializing"


class InsightType(Enum):
    """Represents different types of trading insights."""
    PRICE = "price"
    VOLATILITY = "volatility"
    DIRECTION = "direction"


class AccountType(Enum):
    """Represents different types of trading accounts."""
    CASH = "cash"
    MARGIN = "margin"


class Language(Enum):
    """Represents programming languages for algorithms."""
    PYTHON = "python"
    CSHARP = "csharp"


class ServerType(Enum):
    """Represents server deployment types."""
    SERVER512 = "server512"
    SERVER1024 = "server1024"
    SERVER2048 = "server2048"


class PacketType(Enum):
    """Represents different packet types for communication."""
    ALGORITHM_MANAGER = "algorithm_manager"
    BACKTEST_RESULT = "backtest_result"
    LIVE_RESULT = "live_result"
    DEBUG = "debug"
    LOG = "log"
    RUNTIME_ERROR = "runtime_error"
    HANDLED_ERROR = "handled_error"
    ORDER_EVENT = "order_event"
    ALGORITHM_STATUS = "algorithm_status"