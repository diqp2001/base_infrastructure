"""
IBKR Tick Type Mapping for Factor Value Creation

This module provides mapping between IBKR tick types and factor definitions
based on the official IBKR TWS API documentation:
https://interactivebrokers.github.io/tws-api/tick_types.html

Each tick type represents a specific market data field that can be converted
to a factor value for an instrument.
"""

from enum import IntEnum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class IBKRTickType(IntEnum):
    """
    IBKR Tick Types enumeration based on official TWS API documentation.
    These correspond to the tick types returned by reqMktData() calls.
    """
    # Price Ticks
    BID_SIZE = 0
    BID_PRICE = 1
    ASK_PRICE = 2
    ASK_SIZE = 3
    LAST_PRICE = 4
    LAST_SIZE = 5
    HIGH = 6
    LOW = 7
    VOLUME = 8
    CLOSE_PRICE = 9
    
    # Option-related Ticks
    BID_OPTION_COMPUTATION = 10
    ASK_OPTION_COMPUTATION = 11
    LAST_OPTION_COMPUTATION = 12
    MODEL_OPTION_COMPUTATION = 13
    
    # Extended Price Ticks
    OPEN_TICK = 14
    LOW_13_WEEK = 15
    HIGH_13_WEEK = 16
    LOW_26_WEEK = 17
    HIGH_26_WEEK = 18
    LOW_52_WEEK = 19
    HIGH_52_WEEK = 20
    AVG_VOLUME = 21
    
    # Option Greeks and Metrics
    OPEN_INTEREST = 22
    OPTION_HISTORICAL_VOL = 23
    OPTION_IMPLIED_VOL = 24
    OPTION_BID_EXCH = 25
    OPTION_ASK_EXCH = 26
    OPTION_CALL_OPEN_INTEREST = 27
    OPTION_PUT_OPEN_INTEREST = 28
    OPTION_CALL_VOLUME = 29
    OPTION_PUT_VOLUME = 30
    INDEX_FUTURE_PREMIUM = 31
    
    # Bid/Ask Exchanges
    BID_EXCH = 32
    ASK_EXCH = 33
    AUCTION_VOLUME = 34
    AUCTION_PRICE = 35
    AUCTION_IMBALANCE = 36
    
    # Mark Price
    MARK_PRICE = 37
    
    # Bid/Ask/Last Tick Attribs
    BID_EFP_COMPUTATION = 38
    ASK_EFP_COMPUTATION = 39
    LAST_EFP_COMPUTATION = 40
    OPEN_EFP_COMPUTATION = 41
    HIGH_EFP_COMPUTATION = 42
    LOW_EFP_COMPUTATION = 43
    CLOSE_EFP_COMPUTATION = 44
    LAST_TIMESTAMP = 45
    
    # Shortable
    SHORTABLE = 46
    
    # Fundamental Data
    FUNDAMENTAL_RATIOS = 47
    
    # Real-Time Volume
    RT_VOLUME = 48
    
    # Halted
    HALTED = 49
    
    # Trade Count
    TRADE_COUNT = 50
    TRADE_RATE = 51
    VOLUME_RATE = 52
    
    # Last RTH Trade
    LAST_RTH_TRADE = 53
    
    # Extended hours data
    RT_HISTORICAL_VOL = 54
    
    # IB Dividends
    IB_DIVIDENDS = 55
    
    # Bond analytics
    BOND_FACTOR_MULTIPLIER = 56
    
    # Additional market data
    REGULATORY_IMBALANCE = 61
    NEWS_TICK = 62
    SHORT_TERM_VOLUME_3_MIN = 63
    SHORT_TERM_VOLUME_5_MIN = 64
    SHORT_TERM_VOLUME_10_MIN = 65
    DELAYED_BID = 66
    DELAYED_ASK = 67
    DELAYED_LAST = 68
    DELAYED_BID_SIZE = 69
    DELAYED_ASK_SIZE = 70
    DELAYED_LAST_SIZE = 71
    DELAYED_HIGH = 72
    DELAYED_LOW = 73
    DELAYED_VOLUME = 74
    DELAYED_CLOSE = 75
    DELAYED_OPEN = 76
    
    # Credit rate
    CREDITMAN_SLOW_MARK_PRICE = 77
    
    # Pre-open data
    NOT_SET = 78


@dataclass
class FactorMapping:
    """Mapping configuration for converting IBKR tick data to factor values."""
    factor_name: str
    factor_group: str
    factor_subgroup: Optional[str]
    data_type: str
    description: str
    unit: Optional[str] = None
    frequency: str = "real-time"
    is_price: bool = False
    is_volume: bool = False
    is_derived: bool = False


class IBKRTickFactorMapper:
    """
    Maps IBKR tick types to factor definitions for instrument factor value creation.
    """
    
    # Mapping from IBKR tick types to factor configurations
    TICK_TO_FACTOR_MAP: Dict[IBKRTickType, FactorMapping] = {
        # Core Price Data
        IBKRTickType.BID_PRICE: FactorMapping(
            factor_name="Bid Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Current bid price",
            unit="currency",
            is_price=True
        ),
        IBKRTickType.ASK_PRICE: FactorMapping(
            factor_name="Ask Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Current ask price",
            unit="currency",
            is_price=True
        ),
        IBKRTickType.LAST_PRICE: FactorMapping(
            factor_name="Last Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Last traded price",
            unit="currency",
            is_price=True
        ),
        IBKRTickType.CLOSE_PRICE: FactorMapping(
            factor_name="Close Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Previous close price",
            unit="currency",
            is_price=True
        ),
        IBKRTickType.OPEN_TICK: FactorMapping(
            factor_name="Open Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Opening price",
            unit="currency",
            is_price=True
        ),
        IBKRTickType.HIGH: FactorMapping(
            factor_name="High Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Daily high price",
            unit="currency",
            is_price=True
        ),
        IBKRTickType.LOW: FactorMapping(
            factor_name="Low Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Daily low price",
            unit="currency",
            is_price=True
        ),
        IBKRTickType.MARK_PRICE: FactorMapping(
            factor_name="Mark Price",
            factor_group="Market",
            factor_subgroup="Price",
            data_type="decimal",
            description="Current mark price",
            unit="currency",
            is_price=True
        ),
        
        # Volume Data
        IBKRTickType.BID_SIZE: FactorMapping(
            factor_name="Bid Size",
            factor_group="Market",
            factor_subgroup="Volume",
            data_type="integer",
            description="Current bid size",
            unit="shares",
            is_volume=True
        ),
        IBKRTickType.ASK_SIZE: FactorMapping(
            factor_name="Ask Size",
            factor_group="Market",
            factor_subgroup="Volume",
            data_type="integer",
            description="Current ask size",
            unit="shares",
            is_volume=True
        ),
        IBKRTickType.LAST_SIZE: FactorMapping(
            factor_name="Last Size",
            factor_group="Market",
            factor_subgroup="Volume",
            data_type="integer",
            description="Last trade size",
            unit="shares",
            is_volume=True
        ),
        IBKRTickType.VOLUME: FactorMapping(
            factor_name="Volume",
            factor_group="Market",
            factor_subgroup="Volume",
            data_type="integer",
            description="Daily volume",
            unit="shares",
            is_volume=True
        ),
        IBKRTickType.AVG_VOLUME: FactorMapping(
            factor_name="Average Volume",
            factor_group="Market",
            factor_subgroup="Volume",
            data_type="decimal",
            description="Average daily volume",
            unit="shares",
            is_volume=True,
            is_derived=True
        ),
        
        # Historical Price Ranges
        IBKRTickType.HIGH_52_WEEK: FactorMapping(
            factor_name="52 Week High",
            factor_group="Market",
            factor_subgroup="Historical",
            data_type="decimal",
            description="52-week high price",
            unit="currency",
            frequency="daily",
            is_price=True
        ),
        IBKRTickType.LOW_52_WEEK: FactorMapping(
            factor_name="52 Week Low",
            factor_group="Market",
            factor_subgroup="Historical",
            data_type="decimal",
            description="52-week low price",
            unit="currency",
            frequency="daily",
            is_price=True
        ),
        IBKRTickType.HIGH_26_WEEK: FactorMapping(
            factor_name="26 Week High",
            factor_group="Market",
            factor_subgroup="Historical",
            data_type="decimal",
            description="26-week high price",
            unit="currency",
            frequency="daily",
            is_price=True
        ),
        IBKRTickType.LOW_26_WEEK: FactorMapping(
            factor_name="26 Week Low",
            factor_group="Market",
            factor_subgroup="Historical",
            data_type="decimal",
            description="26-week low price",
            unit="currency",
            frequency="daily",
            is_price=True
        ),
        IBKRTickType.HIGH_13_WEEK: FactorMapping(
            factor_name="13 Week High",
            factor_group="Market",
            factor_subgroup="Historical",
            data_type="decimal",
            description="13-week high price",
            unit="currency",
            frequency="daily",
            is_price=True
        ),
        IBKRTickType.LOW_13_WEEK: FactorMapping(
            factor_name="13 Week Low",
            factor_group="Market",
            factor_subgroup="Historical",
            data_type="decimal",
            description="13-week low price",
            unit="currency",
            frequency="daily",
            is_price=True
        ),
        
        # Options Data
        IBKRTickType.OPTION_IMPLIED_VOL: FactorMapping(
            factor_name="Implied Volatility",
            factor_group="Options",
            factor_subgroup="Greeks",
            data_type="decimal",
            description="Implied volatility",
            unit="percentage",
            is_derived=True
        ),
        IBKRTickType.OPTION_HISTORICAL_VOL: FactorMapping(
            factor_name="Historical Volatility",
            factor_group="Options",
            factor_subgroup="Greeks",
            data_type="decimal",
            description="Historical volatility",
            unit="percentage",
            is_derived=True
        ),
        IBKRTickType.OPEN_INTEREST: FactorMapping(
            factor_name="Open Interest",
            factor_group="Options",
            factor_subgroup="Volume",
            data_type="integer",
            description="Open interest",
            unit="contracts",
            frequency="daily"
        ),
        
        # Trading Metrics
        IBKRTickType.TRADE_COUNT: FactorMapping(
            factor_name="Trade Count",
            factor_group="Market",
            factor_subgroup="Trading",
            data_type="integer",
            description="Number of trades",
            unit="count"
        ),
        IBKRTickType.TRADE_RATE: FactorMapping(
            factor_name="Trade Rate",
            factor_group="Market",
            factor_subgroup="Trading",
            data_type="decimal",
            description="Trade frequency rate",
            unit="trades_per_minute",
            is_derived=True
        ),
        IBKRTickType.VOLUME_RATE: FactorMapping(
            factor_name="Volume Rate",
            factor_group="Market",
            factor_subgroup="Trading",
            data_type="decimal",
            description="Volume rate",
            unit="shares_per_minute",
            is_derived=True
        ),
        
        # Market Status
        IBKRTickType.HALTED: FactorMapping(
            factor_name="Halted Status",
            factor_group="Market",
            factor_subgroup="Status",
            data_type="boolean",
            description="Trading halt status",
            unit="boolean"
        ),
        IBKRTickType.SHORTABLE: FactorMapping(
            factor_name="Shortable",
            factor_group="Market",
            factor_subgroup="Status",
            data_type="decimal",
            description="Shortable shares available",
            unit="shares"
        ),
        
        # Timing Information
        IBKRTickType.LAST_TIMESTAMP: FactorMapping(
            factor_name="Last Trade Time",
            factor_group="Market",
            factor_subgroup="Timing",
            data_type="timestamp",
            description="Last trade timestamp",
            unit="datetime"
        ),
        
        # Real-time Composite Volume
        IBKRTickType.RT_VOLUME: FactorMapping(
            factor_name="Real Time Volume",
            factor_group="Market",
            factor_subgroup="Volume",
            data_type="string",
            description="Real-time composite volume data",
            unit="composite"
        ),
        
        # Exchange Information
        IBKRTickType.BID_EXCH: FactorMapping(
            factor_name="Bid Exchange",
            factor_group="Market",
            factor_subgroup="Exchange",
            data_type="string",
            description="Exchange showing bid",
            unit="exchange_code"
        ),
        IBKRTickType.ASK_EXCH: FactorMapping(
            factor_name="Ask Exchange",
            factor_group="Market",
            factor_subgroup="Exchange",
            data_type="string",
            description="Exchange showing ask",
            unit="exchange_code"
        )
    }

    @classmethod
    def get_factor_mapping(cls, tick_type: IBKRTickType) -> Optional[FactorMapping]:
        """
        Get factor mapping configuration for an IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum value
            
        Returns:
            FactorMapping configuration or None if not mapped
        """
        return cls.TICK_TO_FACTOR_MAP.get(tick_type)

    @classmethod
    def get_all_price_factors(cls) -> Dict[IBKRTickType, FactorMapping]:
        """Get all price-related factor mappings."""
        return {k: v for k, v in cls.TICK_TO_FACTOR_MAP.items() if v.is_price}

    @classmethod
    def get_all_volume_factors(cls) -> Dict[IBKRTickType, FactorMapping]:
        """Get all volume-related factor mappings."""
        return {k: v for k, v in cls.TICK_TO_FACTOR_MAP.items() if v.is_volume}

    @classmethod
    def get_factors_by_group(cls, group: str) -> Dict[IBKRTickType, FactorMapping]:
        """Get all factor mappings for a specific group."""
        return {k: v for k, v in cls.TICK_TO_FACTOR_MAP.items() if v.factor_group == group}

    @classmethod
    def is_tick_type_supported(cls, tick_type: IBKRTickType) -> bool:
        """Check if a tick type is supported for factor mapping."""
        return tick_type in cls.TICK_TO_FACTOR_MAP

    @classmethod
    def get_supported_tick_types(cls) -> List[IBKRTickType]:
        """Get list of all supported tick types."""
        return list(cls.TICK_TO_FACTOR_MAP.keys())

    @classmethod
    def format_tick_value(cls, tick_type: IBKRTickType, raw_value: Any) -> str:
        """
        Format tick value according to its data type.
        
        Args:
            tick_type: IBKR tick type
            raw_value: Raw value from IBKR API
            
        Returns:
            Formatted string value suitable for factor storage
        """
        mapping = cls.get_factor_mapping(tick_type)
        if not mapping:
            return str(raw_value)
        
        try:
            if mapping.data_type == "decimal":
                return str(float(raw_value))
            elif mapping.data_type == "integer":
                return str(int(raw_value))
            elif mapping.data_type == "boolean":
                return str(bool(raw_value)).lower()
            elif mapping.data_type == "timestamp":
                # Handle timestamp conversion if needed
                return str(raw_value)
            else:
                return str(raw_value)
        except (ValueError, TypeError):
            return str(raw_value)