"""
Enumerations used throughout the QuantConnect Lean Python implementation.
"""

from enum import Enum, IntEnum


class Resolution(Enum):
    """Data resolution enumeration."""
    TICK = "tick"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAILY = "daily"


class SecurityType(Enum):
    """Security type enumeration."""
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
    """Market enumeration."""
    USA = "usa"
    EUROPE = "europe"
    ASIA = "asia"
    FXCM = "fxcm"
    OANDA = "oanda"
    DUKASCOPY = "dukascopy"
    BITFINEX = "bitfinex"
    BINANCE = "binance"
    COINBASE = "coinbase"
    FTXUS = "ftxus"
    KRAKEN = "kraken"
    BITSTAMP = "bitstamp"
    BYBIT = "bybit"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    MARKET_ON_OPEN = "market_on_open"
    MARKET_ON_CLOSE = "market_on_close"
    OPTION_EXERCISE = "option_exercise"
    LIMIT_IF_TOUCHED = "limit_if_touched"


class OrderStatus(Enum):
    """Order status enumeration."""
    NEW = "new"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    NONE = "none"
    INVALID = "invalid"
    CANCELED_BY_USER = "canceled_by_user"
    UPDATE_SUBMITTED = "update_submitted"


class OrderDirection(Enum):
    """Order direction enumeration."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class OrderEvent(Enum):
    """Order event types."""
    NEW = "new"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    UPDATE_SUBMITTED = "update_submitted"


class DataNormalizationMode(Enum):
    """Data normalization mode enumeration."""
    RAW = "raw"
    ADJUSTED = "adjusted"
    SPLIT_ADJUSTED = "split_adjusted"
    TOTAL_RETURN = "total_return"


class LogLevel(IntEnum):
    """Logging level enumeration."""
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


class OptionRight(Enum):
    """Option right enumeration."""
    CALL = "call"
    PUT = "put"


class OptionStyle(Enum):
    """Option style enumeration."""
    AMERICAN = "american"
    EUROPEAN = "european"


class TickType(Enum):
    """Tick type enumeration."""
    TRADE = "trade"
    QUOTE = "quote"
    OPEN_INTEREST = "open_interest"


class DataMappingMode(Enum):
    """Data mapping mode enumeration."""
    LAST_TRADING_DAY = "last_trading_day"
    FIRST_DAY_MONTH = "first_day_month"
    OPEN_INTEREST = "open_interest"


class ExtendedMarketHours(Enum):
    """Extended market hours enumeration."""
    PRE_MARKET = "pre_market"
    REGULAR_MARKET = "regular_market"
    POST_MARKET = "post_market"


class Language(Enum):
    """Algorithm language enumeration."""
    CSHARP = "csharp"
    PYTHON = "python"
    FSHARP = "fsharp"
    VB = "vb"
    JAVA = "java"


class AlgorithmStatus(Enum):
    """Algorithm status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    LIQUIDATED = "liquidated"
    DELETED = "deleted"
    COMPLETED = "completed"
    RUNTIME_ERROR = "runtime_error"
    INVALID = "invalid"
    LOGGING_IN = "logging_in"
    INITIALIZING = "initializing"
    HISTORY = "history"


class AccountType(Enum):
    """Account type enumeration."""
    CASH = "cash"
    MARGIN = "margin"


class BrokerageEnvironment(Enum):
    """Brokerage environment enumeration."""
    PAPER = "paper"
    LIVE = "live"


class InsightType(Enum):
    """Insight type enumeration."""
    PRICE = "price"
    VOLATILITY = "volatility"
    DIRECTION = "direction"


class InsightDirection(Enum):
    """Insight direction enumeration."""
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class FillPolicy(Enum):
    """Fill policy enumeration."""
    IMMEDIATE = "immediate"
    PARTIAL = "partial"
    WAIT = "wait"


class RiskFreeInterestRateModel(Enum):
    """Risk-free interest rate model enumeration."""
    CONSTANT = "constant"
    YIELD_CURVE = "yield_curve"
    FED_FUNDS = "fed_funds"


class QuantBookType(Enum):
    """QuantBook type enumeration."""
    RESEARCH = "research"
    BACKTEST = "backtest"


class DataType(Enum):
    """Data type enumeration."""
    TRADE_BAR = "trade_bar"
    QUOTE_BAR = "quote_bar"
    TICK = "tick"
    OPTION_CHAIN = "option_chain"
    FUTURES_CHAIN = "futures_chain"
    SPLIT = "split"
    DIVIDEND = "dividend"
    DELISTING = "delisting"
    SYMBOL_CHANGED_EVENT = "symbol_changed_event"