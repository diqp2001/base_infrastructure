"""
Derivatives base class for derivative financial instruments.
Parent class for Options, Futures, Swaps, and Forward Contracts.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass
from .security import Security, Symbol, SecurityType, MarketData


@dataclass
class UnderlyingAsset:
    """Value object representing the underlying asset."""
    symbol: str
    asset_type: str  # "STOCK", "INDEX", "COMMODITY", "BOND", "CRYPTO"
    current_price: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.current_price is not None and self.current_price < 0:
            raise ValueError("Current price cannot be negative")


class Derivative(Security, ABC):
    """
    Base class for all derivative securities.
    Implements common functionality for derivatives like Greeks calculation,
    expiration handling, and underlying asset tracking.
    """
    
    def __init__(self, symbol: Symbol, underlying_asset: UnderlyingAsset,
                 expiration_date: date, contract_size: Decimal = Decimal('1')):
        super().__init__(symbol)
        
        # Derivative-specific attributes
        self.underlying_asset = underlying_asset
        self.expiration_date = expiration_date
        self.contract_size = contract_size
        
        # Common derivative metrics
        self._days_to_expiry: Optional[int] = None
        self._time_value: Optional[Decimal] = None
        self._intrinsic_value: Optional[Decimal] = None
        
        # Update days to expiry
        self._update_days_to_expiry()
    
    @property
    def days_to_expiry(self) -> Optional[int]:
        """Get days until expiration."""
        return self._days_to_expiry
    
    @property
    def time_value(self) -> Optional[Decimal]:
        """Get time value component of derivative price."""
        return self._time_value
    
    @property
    def intrinsic_value(self) -> Optional[Decimal]:
        """Get intrinsic value of derivative."""
        return self._intrinsic_value
    
    def _post_process_data(self, data: MarketData) -> None:
        """Derivative-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Update time-related metrics
        self._update_days_to_expiry()
        self._calculate_intrinsic_value()
        self._calculate_time_value()
        
        # Check for expiration
        self._check_expiration()
    
    def _update_days_to_expiry(self) -> None:
        """Update days until expiration."""
        today = date.today()
        if self.expiration_date >= today:
            self._days_to_expiry = (self.expiration_date - today).days
        else:
            self._days_to_expiry = 0
    
    @abstractmethod
    def _calculate_intrinsic_value(self) -> None:
        """Calculate intrinsic value - must be implemented by subclasses."""
        pass
    
    def _calculate_time_value(self) -> None:
        """Calculate time value as difference between market price and intrinsic value."""
        if self._intrinsic_value is not None and self.price > 0:
            self._time_value = self.price - self._intrinsic_value
        else:
            self._time_value = None
    
    def _check_expiration(self) -> None:
        """Check if derivative has expired and handle accordingly."""
        if self._days_to_expiry is not None and self._days_to_expiry <= 0:
            self._handle_expiration()
    
    def _handle_expiration(self) -> None:
        """Handle derivative expiration."""
        # Set time value to zero
        self._time_value = Decimal('0')
        
        # Price should equal intrinsic value at expiration
        if self._intrinsic_value is not None:
            self._price = self._intrinsic_value
        
        # Mark as non-tradeable
        self._is_tradeable = False
    
    def is_expired(self) -> bool:
        """Check if derivative is expired."""
        return self._days_to_expiry is not None and self._days_to_expiry <= 0
    
    def update_underlying_price(self, new_price: Decimal) -> None:
        """Update the underlying asset price."""
        self.underlying_asset.current_price = new_price
        
        # Recalculate derivative values
        self._calculate_intrinsic_value()
        self._calculate_time_value()
    
    def get_moneyness(self) -> Optional[str]:
        """Get moneyness classification (ITM, OTM, ATM) - to be overridden."""
        return None
    
    def calculate_leverage(self) -> Optional[Decimal]:
        """Calculate leverage of derivative position."""
        if (self.price <= 0 or not self.underlying_asset.current_price 
            or self.underlying_asset.current_price <= 0):
            return None
        
        # Simple leverage calculation: (underlying_price / derivative_price)
        leverage = self.underlying_asset.current_price / self.price
        return leverage * self.contract_size
    
    def get_contract_multiplier(self) -> Decimal:
        """Get contract size multiplier."""
        return self.contract_size
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Base margin calculation for derivatives.
        Typically higher margin due to leverage - to be overridden by subclasses.
        """
        position_value = abs(quantity * self.price * self.contract_size)
        return position_value * Decimal('0.2')  # 20% base margin
    
    def get_derivative_metrics(self) -> dict:
        """Get common derivative metrics."""
        return {
            'underlying_symbol': self.underlying_asset.symbol,
            'underlying_type': self.underlying_asset.asset_type,
            'underlying_price': self.underlying_asset.current_price,
            'expiration_date': self.expiration_date,
            'days_to_expiry': self.days_to_expiry,
            'current_price': self.price,
            'intrinsic_value': self.intrinsic_value,
            'time_value': self.time_value,
            'contract_size': self.contract_size,
            'is_expired': self.is_expired(),
            'leverage': self.calculate_leverage(),
            'moneyness': self.get_moneyness(),
        }
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Derivative"
    
    def __str__(self) -> str:
        return f"Derivative({self.symbol.ticker}, ${self.price}, exp:{self.expiration_date})"
    
    def __repr__(self) -> str:
        return (f"Derivative(symbol={self.symbol.ticker}, "
                f"underlying={self.underlying_asset.symbol}, "
                f"price=${self.price}, expiry={self.expiration_date})")