"""
Enums for the backtesting framework.
Based on QuantConnect's enum definitions.
"""

from enum import Enum, IntEnum


class Resolution(Enum):
    """
    Data resolution for market data subscriptions.
    """
    TICK = "Tick"
    SECOND = "Second"
    MINUTE = "Minute"
    HOUR = "Hour"
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


class SecurityType(Enum):
    """
    Types of securities that can be traded.
    """
    BASE = "Base"
    EQUITY = "Equity"
    OPTION = "Option"
    COMMODITY = "Commodity"
    FOREX = "Forex"
    FUTURE = "Future"
    CFD = "Cfd"
    CRYPTO = "Crypto"
    BOND = "Bond"
    INDEX = "Index"


class Market(Enum):
    """
    Market identifiers.
    """
    USA = "USA"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    BATS = "BATS"
    ARCA = "ARCA"
    FXCM = "FXCM"
    OANDA = "OANDA"
    BINANCE = "Binance"
    BITFINEX = "Bitfinex"
    COINBASE = "Coinbase"
    NYMEX = "NYMEX"
    CBOT = "CBOT"
    ICE = "ICE"
    CME = "CME"


class OrderType(Enum):
    """
    Types of orders that can be submitted.
    """
    MARKET = "Market"
    LIMIT = "Limit"
    STOP_MARKET = "StopMarket"
    STOP_LIMIT = "StopLimit"
    MARKET_ON_OPEN = "MarketOnOpen"
    MARKET_ON_CLOSE = "MarketOnClose"
    OPTION_EXERCISE = "OptionExercise"


class OrderDirection(Enum):
    """
    Direction of orders (buy/sell).
    """
    BUY = "Buy"
    SELL = "Sell"
    HOLD = "Hold"


class OrderStatus(Enum):
    """
    Status of orders during their lifecycle.
    """
    NEW = "New"
    SUBMITTED = "Submitted"
    PARTIAL_FILLED = "PartiallyFilled"
    FILLED = "Filled"
    CANCELED = "Canceled"
    NONE = "None"
    INVALID = "Invalid"
    CANCEL_PENDING = "CancelPending"
    UPDATE_SUBMITTED = "UpdateSubmitted"


class OrderFillStatus(Enum):
    """
    Status of order fills.
    """
    NONE = "None"
    PARTIAL = "Partial" 
    FILLED = "Filled"


class MarketDataType(Enum):
    """
    Types of market data.
    """
    BASE = "Base"
    TRADE_BAR = "TradeBar"
    QUOTE_BAR = "QuoteBar"
    TICK = "Tick"
    AUXILIARY = "Auxiliary"


class TickType(Enum):
    """
    Types of tick data.
    """
    TRADE = "Trade"
    QUOTE = "Quote"
    OPEN_INTEREST = "OpenInterest"


class DataNormalizationMode(Enum):
    """
    Modes for normalizing market data.
    """
    RAW = "Raw"
    ADJUSTED = "Adjusted"
    SPLIT_ADJUSTED = "SplitAdjusted"
    DIVIDEND_ADJUSTED = "DividendAdjusted"
    TOTAL_RETURN = "TotalReturn"


class LogLevel(Enum):
    """
    Logging levels.
    """
    TRACE = "Trace"
    DEBUG = "Debug"
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"
    CRITICAL = "Critical"


class AlgorithmStatus(Enum):
    """
    Status of algorithm execution.
    """
    INITIALIZING = "Initializing"
    WARMING_UP = "WarmingUp"
    RUNNING = "Running"
    STOPPED = "Stopped"
    LIQUIDATED = "Liquidated"
    DELETED = "Deleted"
    COMPLETED = "Completed"
    ERROR = "RuntimeError"
    HISTORY_REQUEST = "HistoryRequestType"


class BrokerageMessageType(Enum):
    """
    Types of brokerage messages.
    """
    INFORMATION = "Information"
    WARNING = "Warning"
    ERROR = "Error"
    DISCONNECT = "Disconnect"
    RECONNECT = "Reconnect"


class InsightType(Enum):
    """
    Types of alpha insights.
    """
    PRICE = "Price"
    VOLATILITY = "Volatility"


class InsightDirection(Enum):
    """
    Direction of alpha insights.
    """
    UP = "Up"
    DOWN = "Down"
    FLAT = "Flat"


class UniverseSelectionType(Enum):
    """
    Types of universe selection.
    """
    MANUAL = "Manual"
    FUNDAMENTAL = "Fundamental"
    COARSE = "Coarse"
    FINE = "Fine"
    ETF_CONSTITUENTS = "EtfConstituents"
    OPTION_CHAIN = "OptionChain"


class ScheduleFrequency(Enum):
    """
    Frequency for scheduled events.
    """
    ONCE = "Once"
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    YEARLY = "Yearly"


class DayOfWeek(IntEnum):
    """
    Days of the week for scheduling.
    """
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class OptionRight(Enum):
    """
    Option rights (call/put).
    """
    CALL = "Call"
    PUT = "Put"


class OptionStyle(Enum):
    """
    Option exercise styles.
    """
    AMERICAN = "American"
    EUROPEAN = "European"