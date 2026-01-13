"""
src/domain/entities/finance/instrument/ibkr_instrument.py

IBKR-specific Instrument domain entity - extends base Instrument with IBKR contract details.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from .instrument import Instrument
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class IBKRInstrument(Instrument):
    """
    IBKR-specific instrument domain entity.
    
    This entity represents a financial instrument as defined by an IBKR contract,
    including all IBKR-specific metadata and contract details.
    """

    def __init__(
        self,
        id: Optional[int],
        asset: FinancialAsset,
        source: str,
        date: datetime,
        
        # IBKR Contract Details
        contract_id: Optional[int] = None,
        symbol: str = "",
        security_type: str = "",
        exchange: str = "",
        currency: str = "",
        local_symbol: str = "",
        trading_class: str = "",
        
        # Contract Details Metadata
        market_name: str = "",
        min_tick: Optional[Decimal] = None,
        price_magnifier: int = 1,
        order_types: str = "",
        valid_exchanges: str = "",
        long_name: str = "",
        contract_month: str = "",
        industry: str = "",
        category: str = "",
        subcategory: str = "",
        
        # Trading Rules
        min_size: Optional[Decimal] = None,
        size_increment: Optional[Decimal] = None,
        suggested_size_increment: Optional[Decimal] = None,
        
        # Risk Management
        margin_requirements: Optional[Dict[str, Any]] = None,
        
        # Liquidity Information
        liquid_hours: str = "",
        time_zone_id: str = "",
        
        # Additional IBKR-specific fields
        custom_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an IBKRInstrument entity.
        
        Args:
            id: Unique identifier for the instrument
            asset: The underlying FinancialAsset
            source: Data source (should be 'IBKR')
            date: Date when the instrument data was recorded
            contract_id: IBKR contract ID (conId)
            symbol: Contract symbol
            security_type: Security type (STK, OPT, FUT, etc.)
            exchange: Primary exchange
            currency: Contract currency
            local_symbol: Local symbol on exchange
            trading_class: Trading class
            market_name: Market name
            min_tick: Minimum price increment
            price_magnifier: Price magnifier
            order_types: Supported order types
            valid_exchanges: Valid exchanges for routing
            long_name: Full company/instrument name
            contract_month: Contract month (for derivatives)
            industry: Industry classification
            category: Category classification
            subcategory: Subcategory classification
            min_size: Minimum order size
            size_increment: Size increment
            suggested_size_increment: Suggested size increment
            margin_requirements: Margin requirements dictionary
            liquid_hours: Liquid trading hours
            time_zone_id: Timezone ID
            custom_metadata: Additional custom metadata
        """
        super().__init__(id, asset, source, date)
        
        # IBKR Contract Details
        self.contract_id = contract_id
        self.symbol = symbol
        self.security_type = security_type
        self.exchange = exchange
        self.currency = currency
        self.local_symbol = local_symbol
        self.trading_class = trading_class
        
        # Contract Details Metadata
        self.market_name = market_name
        self.min_tick = min_tick
        self.price_magnifier = price_magnifier
        self.order_types = order_types
        self.valid_exchanges = valid_exchanges
        self.long_name = long_name
        self.contract_month = contract_month
        self.industry = industry
        self.category = category
        self.subcategory = subcategory
        
        # Trading Rules
        self.min_size = min_size
        self.size_increment = size_increment
        self.suggested_size_increment = suggested_size_increment
        
        # Risk Management
        self.margin_requirements = margin_requirements or {}
        
        # Liquidity Information
        self.liquid_hours = liquid_hours
        self.time_zone_id = time_zone_id
        
        # Additional metadata
        self.custom_metadata = custom_metadata or {}

    def is_stock(self) -> bool:
        """Check if this is a stock instrument."""
        return self.security_type.upper() == "STK"

    def is_option(self) -> bool:
        """Check if this is an option instrument."""
        return self.security_type.upper() == "OPT"

    def is_future(self) -> bool:
        """Check if this is a future instrument."""
        return self.security_type.upper() in ("FUT", "FOP")

    def is_forex(self) -> bool:
        """Check if this is a forex instrument."""
        return self.security_type.upper() == "CASH"

    def is_derivative(self) -> bool:
        """Check if this is a derivative instrument."""
        return self.security_type.upper() in ("OPT", "FUT", "FOP", "WAR")

    def get_display_symbol(self) -> str:
        """Get the most appropriate symbol for display."""
        return self.local_symbol or self.symbol

    def get_full_symbol(self) -> str:
        """Get full symbol with exchange if needed."""
        if self.exchange and self.exchange != "SMART":
            return f"{self.get_display_symbol()}.{self.exchange}"
        return self.get_display_symbol()

    def supports_order_type(self, order_type: str) -> bool:
        """Check if the instrument supports a specific order type."""
        return order_type.upper() in self.order_types.upper()

    def get_tick_value(self) -> Decimal:
        """Get the value of one tick movement."""
        if self.min_tick is not None:
            return self.min_tick * Decimal(self.price_magnifier)
        return Decimal('0.01')  # Default for stocks

    def is_valid(self) -> bool:
        """
        Validate that the IBKR instrument has required data.
        
        Returns:
            True if instrument is valid, False otherwise
        """
        base_valid = super().is_valid()
        ibkr_valid = (
            self.symbol is not None and
            len(self.symbol.strip()) > 0 and
            self.security_type is not None and
            len(self.security_type.strip()) > 0 and
            self.currency is not None and
            len(self.currency.strip()) > 0
        )
        return base_valid and ibkr_valid

    def to_contract_dict(self) -> Dict[str, Any]:
        """
        Convert instrument to IBKR contract dictionary format.
        
        Returns:
            Dictionary representation suitable for IBKR contract creation
        """
        return {
            'conId': self.contract_id,
            'symbol': self.symbol,
            'secType': self.security_type,
            'exchange': self.exchange,
            'currency': self.currency,
            'localSymbol': self.local_symbol,
            'tradingClass': self.trading_class,
        }

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get a value from custom metadata."""
        return self.custom_metadata.get(key, default)

    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set a value in custom metadata."""
        self.custom_metadata[key] = value

    def __repr__(self):
        return (
            f"IBKRInstrument(id={self.id}, symbol={self.symbol}, "
            f"secType={self.security_type}, exchange={self.exchange}, "
            f"currency={self.currency}, contract_id={self.contract_id})"
        )

    def __eq__(self, other):
        if not isinstance(other, IBKRInstrument):
            return False
        base_equal = super().__eq__(other)
        ibkr_equal = (
            self.contract_id == other.contract_id and
            self.symbol == other.symbol and
            self.security_type == other.security_type and
            self.exchange == other.exchange and
            self.currency == other.currency
        )
        return base_equal and ibkr_equal

    def __hash__(self):
        return hash((
            super().__hash__(),
            self.contract_id,
            self.symbol,
            self.security_type,
            self.exchange,
            self.currency
        ))